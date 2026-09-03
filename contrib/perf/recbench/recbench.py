#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""
RecBench writer and collator: append trial rows, dedup, group, report.

System overview, identity model and task list: contrib/perf/recbench/RecBench.md
Row shape: contrib/perf/docs/SCHEMA.md

Durable store (append-only):
  reindex-profile/bench-summaries/ledger.jsonl
  reindex-profile/bench-summaries/ledger.tsv

Usage:
  # Import historical TSV (idempotent by fingerprint):
  python3 contrib/perf/accumulate_bench.py --import-tsv \\
    reindex-profile/bench-summaries/bench_postsapling_results.tsv \\
    --campaign postsapling-historical

  # Append one trial:
  python3 contrib/perf/accumulate_bench.py --append \\
    --campaign postsapling --run-id postsapling-... --mode reindex \\
    --condition defaultbuf --trial 1 --warmup-height 600000 \\
    --end-height 900000 --blocks 300000 --elapsed-s 966 \\
    --blocks-per-sec 310.56

  # Collate (stdout + optional markdown):
  python3 contrib/perf/accumulate_bench.py --report \\
    --campaign postsapling \\
    --md reindex-profile/bench-summaries/REPORT-postsapling.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DIR = REPO / "reindex-profile" / "bench-summaries"
LEDGER_JSONL = "ledger.jsonl"
MERGED_DIR = "merged"
LEDGER_TSV = "ledger.tsv"

TSV_FIELDS = [
    "fingerprint",
    "context_id",
    "platform_id",
    "build_id",
    "config_id",
    "dataset_id",
    "superseded",
    "metric",
    "value",
    "unit",
    "recorded_at",
    "campaign",
    "run_id",
    "mode",
    "condition",
    "trial",
    "warmup_height",
    "end_height",
    "blocks",
    "elapsed_s",
    "blocks_per_sec",
    "binary",
    "notes",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:16]


def platform_id(row: dict) -> str:
    """Same machine class? Excludes hostname and host_id deliberately."""
    p = row.get("platform") or {}
    return _h("|".join(str(p.get(k, "")) for k in
                       ("os", "os_version", "arch", "cpu_model",
                        "cpu_cores", "cpu_threads")))


def build_id(row: dict) -> str:
    """Same binary? Version, commit, dirty flag and compiled features."""
    b = row.get("build") or {}
    f = (row.get("features") or {}).get("build") or {}
    return _h("|".join([str(b.get("version", "")), str(b.get("commit", "")),
                        str(b.get("dirty", "")),
                        "|".join("%s=%s" % (k, f[k]) for k in sorted(f))]))


def config_id(row: dict):
    """Same thing measured? Runtime selection, not compiled state.

    None when nothing is known, and None is stored: an empty hash asserts
    "unconfigured" where None says "unrecorded". A hash of the empty string is
    the same 16 characters on every row and distinguishes nothing.
    """
    f = row.get("features") or {}
    parts = {}
    for block in ("workload", "runtime"):
        for k, v in (f.get(block) or {}).items():
            if v not in (None, "", {}):
                parts["%s.%s" % (block, k)] = v
    if not parts:
        return None
    return _h("|".join("%s=%s" % (k, parts[k]) for k in sorted(parts)))


def dataset_id(row: dict):
    """Same input? Snapshot and height window.

    Separate from campaign, which is a label a person chose and may be renamed
    without changing what was measured. None when nothing identifies the
    input, for the reason in config_id.
    """
    w = (row.get("features") or {}).get("workload") or {}
    parts = {k: w[k] for k in ("snap", "tip_height", "tip_hash",
                               "warmup_height", "end_height")
             if w.get(k) not in (None, "", {})}
    if not parts:
        return None
    return _h("|".join("%s=%s" % (k, parts[k]) for k in sorted(parts)))


def context_id(row: dict) -> str:
    """Composition of the three axes: the quick equality check.

    Axes, tensions and the pending re-evaluation: RecBench.md S4.
    """
    return _h("|".join([platform_id(row), build_id(row),
                        config_id(row) or "", dataset_id(row) or ""]))


def fingerprint(row: dict) -> str:
    """Identity of one measurement, for dedup on append.

    Includes context_id: without it, the same trial run on two machines
    collided and the second was silently dropped as a duplicate -- which is
    exactly the case a cross-platform baseline consists of.
    """
    key = "|".join(
        [
            str(row.get("campaign", "")),
            str(row.get("run_id", "")),
            str(row.get("mode", "")),
            str(row.get("condition", "")),
            str(row.get("trial", "")),
            str(row.get("warmup_height", "")),
            str(row.get("end_height", "")),
            str(row.get("elapsed_s", "")),
            str(row.get("blocks_per_sec", "")),
            str(row.get("context_id", "")),
        ]
    )
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def context_store(store_dir: Path, row: dict) -> Path:
    """Store for ROW's context. One writer per directory.

    Separating at write time rather than read time: a merge across contexts
    then has to be asked for, instead of happening because nobody looked.
    RB_FLAT_STORE=1 keeps the single-file layout for a scratch run.
    """
    if os.environ.get("RB_FLAT_STORE"):
        return store_dir
    ctx = row.get("context_id") or "unknown"
    return store_dir / ctx


def ensure_store(store_dir: Path) -> tuple[Path, Path]:
    store_dir.mkdir(parents=True, exist_ok=True)
    jsonl = store_dir / LEDGER_JSONL
    tsv = store_dir / LEDGER_TSV
    if not tsv.exists():
        with tsv.open("w", newline="") as f:
            csv.DictWriter(f, fieldnames=TSV_FIELDS, delimiter="\t").writeheader()
    if not jsonl.exists():
        jsonl.touch()
    return jsonl, tsv


def store_files(store_dir: Path) -> list[Path]:
    """Every ledger under STORE_DIR: its own, plus one per context directory.

    Reading is across contexts by design -- collation groups by context_id, so
    a report over the whole tree still cannot pool them. Writing is what stays
    confined to one directory.
    """
    found = []
    own = store_dir / LEDGER_JSONL
    if own.exists():
        found.append(own)
    if store_dir.is_dir():
        for sub in sorted(store_dir.iterdir()):
            # merged/ holds derived views; reading them back would double
            # every row they contain. Excluded by name, not by filename luck.
            if not sub.is_dir() or sub.name == MERGED_DIR:
                continue
            p = sub / LEDGER_JSONL
            if p.exists():
                found.append(p)
    return found


def store_contexts(store_dir: Path) -> dict:
    """context_id -> rows, for every per-context store under STORE_DIR.

    The merged/ directory is excluded: its files are derived views, and
    re-merging a merge would double-count every row it holds.
    """
    out = {}
    if not store_dir.is_dir():
        return out
    for sub in sorted(store_dir.iterdir()):
        if not sub.is_dir() or sub.name == MERGED_DIR:
            continue
        f = sub / LEDGER_JSONL
        if not f.exists():
            continue
        rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        if rows:
            out[sub.name] = rows
    return out


def index_stores(store_dir: Path) -> list[dict]:
    """One summary line per context store, so a directory of hashes is
    navigable without opening each file."""
    idx = []
    for ctx, rows in store_contexts(store_dir).items():
        p = rows[0].get("platform") or {}
        b = rows[0].get("build") or {}
        idx.append({
            "context_id": ctx,
            "n": len(rows),
            "host": p.get("hostname") or "",
            "platform": "%s/%s" % (p.get("os", "?"), p.get("arch", "?")),
            # "-" not "": an empty build block means the row was recorded
            # without a binary to read, which a reader should see rather than
            # mistake for a formatting gap.
            "build": b.get("raw") or b.get("version") or "-",
            "campaigns": sorted({r.get("campaign", "") for r in rows}),
            "newest": max(r.get("recorded_at", "") for r in rows),
        })
    return sorted(idx, key=lambda x: x["newest"], reverse=True)


def merge_stores(store_dir: Path, name: str, contexts: list = None,
                 across: bool = False) -> tuple:
    """Combine per-context stores into a derived view under merged/.

    Returns (path, rows, warnings). The output is regenerable and is never a
    source: store_contexts() skips merged/, so a later merge cannot read it
    back in.
    """
    have = store_contexts(store_dir)
    pick = {c: r for c, r in have.items() if not contexts or c in contexts}
    warn = []
    for c in (contexts or []):
        if c not in have:
            warn.append("no store for context %s" % c)
    if len(pick) > 1 and not across:
        return (None, [], warn + [
            "refusing to merge %d contexts into one view; they are not "
            "comparable by construction. Pass --across-contexts if that is "
            "what you mean: %s" % (len(pick), ", ".join(sorted(pick)))])
    rows, seen = [], {}
    for ctx, rs in sorted(pick.items()):
        for r in rs:
            fp = r.get("fingerprint")
            if fp in seen:
                # Across stores this is a real duplicate import, not the
                # same row twice: report it rather than drop it silently.
                warn.append("duplicate fingerprint %s in %s and %s"
                            % (fp, seen[fp], ctx))
                continue
            seen[fp] = ctx
            rows.append(r)
    rows.sort(key=lambda r: r.get("recorded_at", ""), reverse=True)
    out = store_dir / MERGED_DIR
    out.mkdir(parents=True, exist_ok=True)
    path = out / ("%s.jsonl" % name)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
                    encoding="utf-8")
    return (path, rows, warn)


def load_rows(store_dir: Path) -> list[dict]:
    rows = []
    for jsonl in store_files(store_dir):
        with jsonl.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def existing_fps(store_dir: Path) -> set[str]:
    return {r.get("fingerprint", "") for r in load_rows(store_dir)}


def _stamp(row: dict) -> dict:
    """Attach platform / build / features to ROW if absent.

    Stamped HERE rather than in each launcher (docs/TASKS.md F1b): every row
    reaches a ledger through this function, so an unstamped row becomes
    unrepresentable. Doing it per launcher would be ten chances to forget with
    nothing noticing, and back-filling later records a guess rather than an
    observation.

    Never fatal: a stamp failure must not lose a measurement that already
    cost lab time. An absent block reads as unknown, which is honest.
    """
    if "platform" in row and "build" in row:
        return row
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import stamp as platform_stamp
        row.setdefault("schema", platform_stamp.SCHEMA_VERSION)
        row.setdefault("platform", platform_stamp.platform_block())
        # build.* must describe the binary that RAN, not whatever src/zerod is
        # now: the writer executes after the node exits.
        row.setdefault("build", platform_stamp.build_block(row.get("binary") or None))
        # runtime is what the launcher selected; workload is what it measured.
        # Both are the launcher's knowledge: absent rather than guessed.
        # A height window belongs to the workload: only a chain-sync trial has
        # one, and a digest-rate row would otherwise record two nulls to say
        # so. Promoted here so dataset_id reads it from one place.
        wl = dict(row.get("workload") or {})
        # 0-0 is not a window; a non-chain row records no height fields at all
        # rather than two zeros that would read as a real range.
        if not (row.get("warmup_height") in (0, None, "")
                and row.get("end_height") in (0, None, "")):
            for k in ("warmup_height", "end_height"):
                if row.get(k) not in (None, "") and k not in wl:
                    wl[k] = row[k]
        row["workload"] = wl
        row.setdefault("features", {
            "build": platform_stamp.detect_build_features(),
            "runtime": row.get("runtime", {}),
            "workload": row.get("workload", {}),
        })
    except Exception as exc:  # noqa: BLE001 - never lose a measurement
        print("WARNING: platform stamp unavailable (%s); row recorded unstamped"
              % exc, file=sys.stderr)
    return row


def append_row(store_dir: Path, caller_row: dict) -> bool:
    """Append if fingerprint new. Returns True if written.

    The caller's dict receives the computed ids, so a script can read back the
    fingerprint it needs for a later --superseded.
    """
    row = dict(caller_row)
    row.setdefault("recorded_at", utc_now())
    row.setdefault("binary", "")
    row.setdefault("notes", "")
    row = _stamp(row)
    # Order matters: context_id reads the blocks _stamp just attached, and
    # fingerprint reads context_id.
    row["platform_id"] = platform_id(row)
    row["build_id"] = build_id(row)
    row["config_id"] = config_id(row)
    row["dataset_id"] = dataset_id(row)
    row.update(payload(row))
    row["context_id"] = context_id(row)
    row["fingerprint"] = fingerprint(row)
    store_dir = context_store(store_dir, row)
    jsonl, tsv = ensure_store(store_dir)
    if row["fingerprint"] in existing_fps(store_dir):
        return False
    # Prepend, not append. The newest row is the one a reader wants first, and
    # a store read top-down should show current state without seeking to the
    # end. Rewrites the file, which is fine at this size and is why the store
    # is per-context rather than one global file.
    line = json.dumps(row, sort_keys=True) + "\n"
    prior = jsonl.read_text(encoding="utf-8") if jsonl.exists() else ""
    jsonl.write_text(line + prior, encoding="utf-8")
    # Same newest-first order, but the header stays line 1.
    buf = io.StringIO()
    csv.DictWriter(buf, fieldnames=TSV_FIELDS, delimiter="\t",
                   extrasaction="ignore").writerow(
        {k: row.get(k, "") for k in TSV_FIELDS})
    lines = tsv.read_text(encoding="utf-8").splitlines(keepends=True)
    head, rest = (lines[0], lines[1:]) if lines else ("", [])
    tsv.write_text(head + buf.getvalue() + "".join(rest), encoding="utf-8")
    caller_row.update(row)
    return True


def import_tsv(store_dir: Path, path: Path, campaign: str, run_id: str, binary: str, notes: str,
               runtime: dict = None, workload: dict = None, superseded: str = "") -> int:
    added = 0
    with path.open() as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            row = {
                "campaign": campaign,
                "run_id": run_id or f"import-{path.stem}",
                "mode": r.get("mode", "reindex"),
                "condition": r.get("condition", "stock"),
                "trial": int(r.get("trial", 1)),
                "warmup_height": int(float(r["warmup_height"])),
                "end_height": int(float(r["end_height"])),
                "blocks": int(float(r["blocks"])),
                "elapsed_s": float(r["elapsed_s"]),
                "blocks_per_sec": float(r["blocks_per_sec"]),
                "binary": binary,
                "notes": notes or f"imported:{path.name}",
                "runtime": runtime or {},
                "workload": workload or {},
                # Every imported row carries the same retirement, which is
                # right for re-importing a corrected TSV over an earlier one.
                "superseded": superseded or None,
            }
            if append_row(store_dir, row):
                added += 1
    return added


def _height_key(v) -> str:
    """Sortable, collision-free height component for a grouping key.

    Zero-padded so string order matches numeric order; "" for absent, which is
    distinct from a genuine height 0."""
    if v is None or v == "":
        return ""
    try:
        return "%012d" % int(v)
    except (TypeError, ValueError):
        return str(v)


# --- payload -------------------------------------------------------------
# A row is an identity envelope plus one measurement. The envelope is
# project-independent; the payload is not, which is the whole reason to keep
# them apart. Collation reads metric/value/unit, so any project's measurement
# groups the same way. blocks_per_sec remains as the Zero shorthand a launcher
# may pass, and payload() maps it onto the metric.

DEFAULT_METRIC = "blocks_per_sec"
DEFAULT_UNIT = "blk/s"


def payload(row: dict) -> dict:
    """The measurement, normalised. Falls back to the Zero sync metric."""
    m = row.get("metric")
    v = row.get("value")
    if m is None and v is None:
        return {"metric": DEFAULT_METRIC, "value": row.get("blocks_per_sec"),
                "unit": row.get("unit") or DEFAULT_UNIT}
    return {"metric": m or DEFAULT_METRIC, "value": v,
            "unit": row.get("unit") or DEFAULT_UNIT}


def current_rows(rows: list[dict]) -> list[dict]:
    """Rows no other row retires.

    Retirement is explicit: a row names the fingerprint it replaces. Nothing is
    deleted, so a superseded number stays findable for a citation that already
    points at it -- this decides which row to *use*, not which existed.
    """
    retired = {r.get("superseded") for r in rows if r.get("superseded")}
    return [r for r in rows if r.get("fingerprint") not in retired]


def collate(rows: list[dict], campaign: str | None = None) -> list[dict]:
    groups: dict[tuple, list[float]] = defaultdict(list)
    meta: dict[tuple, dict] = {}
    for r in rows:
        if campaign and r.get("campaign") != campaign:
            continue
        key = (
            # context_id leads the key: results from different machines or
            # binaries form separate groups instead of being averaged into one
            # mean. SCHEMA.md S5 requires this; before it, a Linux row and a
            # macOS row with the same campaign/mode/window pooled silently.
            r.get("context_id", ""),
            r.get("campaign", ""),
            r.get("mode", ""),
            r.get("condition", ""),
            # Missing heights group separately rather than colliding with a
            # genuine height-0 window. Normalised to str so the key stays
            # sortable: mixing "" and 0 makes sorted() raise on comparison.
            _height_key(r.get("warmup_height")),
            _height_key(r.get("end_height")),
            # Without these, a ns/digest row and a blk/s row in one context
            # would average together into a number of no unit at all.
            payload(r).get("metric") or DEFAULT_METRIC,
            payload(r).get("unit") or DEFAULT_UNIT,
        )
        # The measurement comes from the payload, so a row carrying any metric
        # collates the same way. A row without a usable value is EXCLUDED, not
        # zero-filled and not fatal: one incomplete row once raised KeyError
        # and no report could be produced at all, and zero-filling would
        # silently drag every mean down.
        pay = payload(r)
        raw = pay.get("value")
        name = pay.get("metric") or DEFAULT_METRIC
        if raw is None or raw == "":
            print("WARNING: no %s in run_id=%s; row excluded"
                  % (name, r.get("run_id", "?")), file=sys.stderr)
            continue
        try:
            bps = float(raw)
        except (TypeError, ValueError):
            print("WARNING: unparseable %s %r in run_id=%s; row excluded"
                  % (name, raw, r.get("run_id", "?")), file=sys.stderr)
            continue
        if bps <= 0:
            print("WARNING: non-positive %s %r in run_id=%s; row excluded"
                  % (name, raw, r.get("run_id", "?")), file=sys.stderr)
            continue
        groups[key].append(bps)
        meta[key] = r
    out = []
    for key, rates in sorted(groups.items()):
        ctx_k, campaign_k, mode, condition, warm_k, end_k, metric_k, unit_k = key
        # Back to numbers for output and arithmetic; the padded strings exist
        # only to keep the grouping key sortable.
        warm = int(warm_k) if warm_k else None
        end = int(end_k) if end_k else None
        blocks = end - warm if (warm is not None and end is not None) else None
        out.append(
            {
                "context_id": ctx_k,
                "campaign": campaign_k,
                "mode": mode,
                "condition": condition,
                "warmup_height": warm,
                "end_height": end,
                "blocks": blocks,
                "metric": metric_k,
                "unit": unit_k,
                "n": len(rates),
                "mean": round(statistics.mean(rates), 4),
                "stdev": round(statistics.pstdev(rates), 4) if len(rates) > 1 else 0.0,
                "min": round(min(rates), 4),
                "max": round(max(rates), 4),
                # The *_bps names are what the existing report and A/B delta
                # read. Kept so this change is not also a reader migration;
                # they carry whatever metric the group holds, not necessarily
                # blocks per second.
                "mean_bps": round(statistics.mean(rates), 4),
                "stdev_bps": round(statistics.pstdev(rates), 4) if len(rates) > 1 else 0.0,
                "min_bps": round(min(rates), 4),
                "max_bps": round(max(rates), 4),
            }
        )
    return out


def ab_deltas(summary: list[dict]) -> list[str]:
    """Pair conditions within same campaign/mode/window for A/B delta lines."""
    by = defaultdict(list)
    for s in summary:
        by[(s["campaign"], s["mode"], s["warmup_height"], s["end_height"])].append(s)
    lines = []
    for key, items in sorted(by.items()):
        if len(items) < 2:
            continue
        items = sorted(items, key=lambda x: x["condition"])
        base = items[0]
        for other in items[1:]:
            d = other["mean_bps"] - base["mean_bps"]
            pct = (d / base["mean_bps"] * 100.0) if base["mean_bps"] else 0.0
            lines.append(
                "%s/%s window %d-%d: %s mean=%.2f (n=%d) vs %s mean=%.2f (n=%d) -> delta %+.2f %s (%+.2f%%)"
                % (
                    key[0],
                    key[1],
                    key[2],
                    key[3],
                    other["condition"],
                    other["mean_bps"],
                    other["n"],
                    base["condition"],
                    base["mean_bps"],
                    base["n"],
                    d,
                    base.get("unit", DEFAULT_UNIT),
                    pct,
                )
            )
    return lines


def format_report(summary: list[dict], deltas: list[str]) -> str:
    lines = [
        "# Bench ledger collation",
        "",
        "Generated by `contrib/perf/recbench/recbench.py --report`.",
        "",
        "| campaign | mode | condition | window | metric | unit | n | mean | stdev | min | max |",
        "|----------|------|-----------|--------|--------|------|---|------|-------|-----|-----|",
    ]
    for s in summary:
        window = "%d-%d" % (s["warmup_height"], s["end_height"])
        lines.append(
            "| %s | %s | %s | %s | %s | %s | %d | %.2f | %.2f | %.2f | %.2f |"
            % (
                s["campaign"],
                s["mode"],
                s["condition"],
                window,
                s.get("metric", DEFAULT_METRIC),
                s.get("unit", DEFAULT_UNIT),
                s["n"],
                s["mean_bps"],
                s["stdev_bps"],
                s["min_bps"],
                s["max_bps"],
            )
        )
    if deltas:
        lines.extend(["", "## A/B deltas (condition vs first sorted peer)", ""])
        for d in deltas:
            lines.append("- " + d)
    lines.append("")
    return "\n".join(lines)


def self_test() -> int:
    """Pin fingerprint and dedup behaviour.

    The fingerprint exists for one purpose: import idempotency. A false match
    silently DROPS a real measurement, so the failure mode is data loss with no
    error. These assertions cover both directions, and record the known v1 gap
    (docs/SCHEMA.md S6.3) as an explicit xfail rather than leaving it unstated.
    """
    import tempfile

    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    base = {"campaign": "c", "run_id": "r", "mode": "reindex", "condition": "stock",
            "trial": 1, "warmup_height": 0, "end_height": 1000,
            "elapsed_s": 10.0, "blocks_per_sec": 100.0}

    # Deterministic and stable: the same observation must hash the same way.
    check(fingerprint(base) == fingerprint(dict(base)), "fingerprint is deterministic")
    check(len(fingerprint(base)) == 16, "fingerprint is 16 hex chars")

    # Fields that identify an observation must all change it.
    for field, val in [("campaign", "other"), ("run_id", "r2"), ("mode", "bootstrap"),
                       ("condition", "nofdcache"), ("trial", 2), ("warmup_height", 1),
                       ("end_height", 2000), ("elapsed_s", 11.0),
                       ("blocks_per_sec", 101.0)]:
        row = dict(base); row[field] = val
        check(fingerprint(row) != fingerprint(base),
              "changing %s must change the fingerprint" % field)

    # Fields NOT in the key must not change it -- otherwise a re-import of the
    # same observation looks new and duplicates.
    for field, val in [("recorded_at", "2026-01-01T00:00:00Z"), ("notes", "x"),
                       ("binary", "/some/path")]:
        row = dict(base); row[field] = val
        check(fingerprint(row) == fingerprint(base),
              "%s must not affect the fingerprint" % field)

    # Round trip through the store: append is idempotent.
    with tempfile.TemporaryDirectory() as d:
        store = Path(d)
        check(append_row(store, dict(base)) is True, "first append writes")
        check(append_row(store, dict(base)) is False, "re-append is skipped")
        rows = load_rows(store)
        check(len(rows) == 1, "store holds exactly one row after a duplicate append")
        second = dict(base); second["trial"] = 2
        check(append_row(store, second) is True, "a distinct trial is written")
        check(len(load_rows(store)) == 2, "store holds two distinct rows")

    # collate() must survive an incomplete row. One row without a usable rate
    # used to raise KeyError, so NO report could be produced from the whole
    # ledger; zero-filling instead would drag every mean down silently.
    import contextlib
    import io

    good = dict(base); good["blocks_per_sec"] = 50.0; good["run_id"] = "good"
    bad = dict(base); bad.pop("blocks_per_sec", None); bad["run_id"] = "bad"
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        out = collate([good, bad])
    check(len(out) == 1, "collate produces a group despite an incomplete row")
    check(out[0]["n"] == 1, "the incomplete row is excluded from n, not counted")
    check(out[0]["mean_bps"] == 50.0, "the mean is not dragged down by exclusion")
    check("bad" in err.getvalue(), "the excluded row is named in a warning")

    for junk in ("", None, "not-a-number", 0, -1):
        r = dict(base); r["blocks_per_sec"] = junk; r["run_id"] = "junk"
        with contextlib.redirect_stderr(io.StringIO()):
            out = collate([good, r])
        check(out[0]["n"] == 1, "junk rate %r is excluded" % (junk,))

    # Missing heights must group separately, not collide with a real height 0.
    # Metrics never pool: averaging ns/digest with blk/s yields a number of no
    # unit at all, so metric and unit are part of the grouping key.
    mix = [dict(base, run_id="m1", metric="leaf.blake2b", value=79.2, unit="ns/digest"),
           dict(base, run_id="m2", metric="leaf.blake2b", value=80.8, unit="ns/digest"),
           dict(base, run_id="m3", blocks_per_sec=3000.0)]
    for r in mix:
        r.update(payload(r))
    g = collate(mix)
    by = {x["metric"]: x for x in g}
    check(len(g) == 2, "two metrics collate as two groups, not one")
    check(by["leaf.blake2b"]["n"] == 2, "same-metric rows group together")
    check(abs(by["leaf.blake2b"]["mean"] - 80.0) < 1e-9, "mean is of that metric")
    check(by["leaf.blake2b"]["unit"] == "ns/digest", "unit is carried to the report")

    a = dict(base); a["blocks_per_sec"] = 10.0; a["warmup_height"] = 0
    b = dict(base); b["blocks_per_sec"] = 20.0; b.pop("warmup_height", None)
    with contextlib.redirect_stderr(io.StringIO()):
        out = collate([a, b])
    check(len(out) == 2,
          "a missing height does not collapse into a genuine height-0 window")

    # F1b: an unstamped row must be unrepresentable. Stamping at the writer
    # rather than in each launcher is what makes this an invariant instead of
    # a convention nobody enforces.
    with tempfile.TemporaryDirectory() as d:
        store = Path(d)
        append_row(store, dict(base))
        written = json.loads(store_files(store)[0].read_text(
            encoding="utf-8").strip().splitlines()[0])
        for block in ("platform", "build", "features"):
            check(block in written, "a written row carries a %s block" % block)
        # Writes land under the row's context, not the parent, so two
        # contexts cannot share a file and be pooled by accident.
        # superseded: a corrected row retires its predecessor, and the
        # predecessor stays on disk so an existing citation still resolves.
        first = dict(base, run_id="sup-1", blocks_per_sec=9.0)
        append_row(store, first)
        old_fp = [r for r in load_rows(store) if r["run_id"] == "sup-1"][0]["fingerprint"]
        append_row(store, dict(base, run_id="sup-2", blocks_per_sec=11.0,
                               superseded=old_fp))
        allr = load_rows(store)
        cur = current_rows(allr)
        check(len(allr) == len(cur) + 1, "the retired row is kept on disk")
        check(all(r["fingerprint"] != old_fp for r in cur),
              "the retired row is excluded from current")
        check(any(r["run_id"] == "sup-2" for r in cur), "the replacement is current")

        # Merge: a view, never a source.
        m1 = dict(base, run_id="mg-1", blocks_per_sec=7.0)
        append_row(store, m1)
        before = len(load_rows(store))
        ctxs = list(store_contexts(store))
        path, rows, warn = merge_stores(store, "v", [ctxs[0]])
        check(path is not None and path.parent.name == MERGED_DIR,
              "a merge writes under merged/")
        check(len(load_rows(store)) == before,
              "a merged view is not read back as a source")
        if len(ctxs) > 1:
            p2, r2, w2 = merge_stores(store, "x")
            check(p2 is None and any("refusing" in w for w in w2),
                  "merging differing contexts is refused without --across-contexts")
            p3, r3, w3 = merge_stores(store, "x", across=True)
            check(p3 is not None, "--across-contexts permits it")
        idx = index_stores(store)
        check(len(idx) == len(ctxs) and all(e["n"] > 0 for e in idx),
              "the index lists every context store")

        check((store / written["context_id"]).is_dir(),
              "the row is written to its context directory")
        check(not (store / "ledger.jsonl").exists(),
              "no ledger at the parent: writes are per-context")
        check(written["platform"].get("os") in ("macos", "linux", "windows"),
              "platform.os is a real value, not a placeholder")
        check("version" in written["build"], "build.version is present")
        check(written.get("schema"), "schema version is recorded")

        # An explicit block from the caller wins: a replayed row keeps the
        # platform it was MEASURED on, not the one replaying it.
        pre = dict(base)
        pre["run_id"] = "replayed"
        pre["platform"] = {"os": "linux", "arch": "x86_64"}
        pre["build"] = {"version": "v9.9.9"}
        append_row(store, pre)
        rows = [json.loads(x) for x in
                store_files(store)[0].read_text(encoding="utf-8").splitlines() if x]
        rep = [r for r in rows if r.get("run_id") == "replayed"][0]
        check(rep["platform"]["os"] == "linux",
              "an explicit platform is preserved, not overwritten by the host")
        check(rep["build"]["version"] == "v9.9.9",
              "an explicit build is preserved")

    # KNOWN GAP (v1): platform, arch and build are absent from the key, so two
    # observations differing only by platform collide and one is silently
    # dropped. Asserted as-is so the fix (SCHEMA.md S6.4) has a failing anchor.
    mac = dict(base); mac["platform"] = {"os": "macos", "arch": "arm64"}
    lin = dict(base); lin["platform"] = {"os": "linux", "arch": "x86_64"}
    check(fingerprint(mac) == fingerprint(lin),
          "v1 fingerprint is expected to ignore platform (known gap)")
    if fingerprint(mac) != fingerprint(lin):
        print("NOTE: fingerprint now distinguishes platform -- update this test "
              "and docs/SCHEMA.md S6.4", file=sys.stderr)

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def _kv(pairs):
    """K=V strings to a dict. A pair without '=' is skipped, not guessed."""
    out = {}
    for p in pairs or []:
        k, sep, v = p.partition("=")
        if sep and k:
            out[k.strip()] = v.strip()
    return out


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--store-dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--import-tsv", type=Path)
    ap.add_argument("--campaign", default="")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--binary", default="")
    ap.add_argument("--notes", default="")
    ap.add_argument("--record", action="store_true",
                    help="write one row from the flags below")
    ap.add_argument("--mode", default="reindex")
    ap.add_argument("--condition", default="stock")
    ap.add_argument("--trial", type=int, default=1)
    ap.add_argument("--warmup-height", type=int)
    ap.add_argument("--end-height", type=int)
    ap.add_argument("--blocks", type=int)
    ap.add_argument("--elapsed-s", type=float)
    ap.add_argument("--blocks-per-sec", type=float)
    ap.add_argument("--runtime", action="append", default=[], metavar="K=V",
                    help="runtime selection, repeatable (solver=tromp)")
    ap.add_argument("--workload", action="append", default=[], metavar="K=V",
                    help="what was measured, repeatable (op=solve snap=tiny)")
    ap.add_argument("--metric", default="",
                    help="what was measured (default: blocks_per_sec)")
    ap.add_argument("--value", type=float,
                    help="the measurement; --blocks-per-sec is the Zero shorthand")
    ap.add_argument("--unit", default="", help="unit of --value")
    # Two different operations, so two unrelated names. --superseded writes:
    # it records which row this one replaces. --all-rows reads: it turns off
    # the filter that hides replaced rows. Sharing a stem read as a modifier
    # pair, which they are not.
    ap.add_argument("--superseded", default="", metavar="FINGERPRINT",
                    help="with --record: the row this one replaces")
    ap.add_argument("--all-rows", action="store_true",
                    help="with --report: include replaced rows (default: current only)")
    ap.add_argument("--index", action="store_true",
                    help="one line per context store")
    ap.add_argument("--merge", metavar="NAME",
                    help="combine context stores into merged/NAME.jsonl (a view)")
    ap.add_argument("--context", action="append", default=[], metavar="ID",
                    help="with --merge: limit to this context, repeatable")
    ap.add_argument("--across-contexts", action="store_true",
                    help="with --merge: allow combining differing contexts")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--md", type=Path, help="Write markdown report path")
    ap.add_argument("--json", type=Path, help="Write collation JSON path")
    args = ap.parse_args()

    store = args.store_dir
    ensure_store(store)

    if args.import_tsv:
        camp = args.campaign or "imported"
        n = import_tsv(store, args.import_tsv, camp, args.run_id, args.binary, args.notes,
                       _kv(args.runtime), _kv(args.workload), args.superseded)
        print("imported_added=%d path=%s campaign=%s" % (n, args.import_tsv, camp))

    if args.record:
        if args.metric and args.blocks_per_sec is None and args.value is not None:
            args.blocks_per_sec = args.value
        # A non-chain metric has no height window. Requiring 0/0 to satisfy
        # the chain-sync arguments would record a window that does not exist.
        if args.metric:
            if args.warmup_height is None:
                args.warmup_height = 0
            if args.end_height is None:
                args.end_height = 0
            if args.blocks is None:
                args.blocks = 1
        need = [
            args.campaign,
            args.run_id,
            args.warmup_height,
            args.end_height,
            args.blocks,
            args.elapsed_s,
            args.blocks_per_sec,
        ]
        if any(x is None or x == "" for x in need):
            print("ERROR: --record requires --campaign --run-id --warmup-height "
                  "--end-height --blocks --elapsed-s --blocks-per-sec", file=sys.stderr)
            return 2
        row = {
            "campaign": args.campaign,
            "run_id": args.run_id,
            "mode": args.mode,
            "condition": args.condition,
            "trial": args.trial,
            "warmup_height": args.warmup_height,
            "end_height": args.end_height,
            "blocks": args.blocks,
            "elapsed_s": args.elapsed_s,
            "blocks_per_sec": args.blocks_per_sec,
            "binary": args.binary,
            "notes": args.notes,
            "runtime": _kv(args.runtime),
            "workload": _kv(args.workload),
            "superseded": args.superseded or None,
            "metric": args.metric or None,
            "value": args.value,
            "unit": args.unit or None,
        }
        # append_row stamps the row in place, so the fingerprint is read back
        # from it: computing one here from the unstamped row printed a value
        # that never matched what was stored, which made --superseded unusable
        # from a script.
        if args.superseded:
            # A typo would silently retire nothing, and the report would then
            # show two rows where one was meant to replace the other.
            known = {r.get("fingerprint") for r in load_rows(store)}
            if args.superseded not in known:
                print("ERROR: --superseded %s matches no row in %s"
                      % (args.superseded, store), file=sys.stderr)
                return 2
        wrote = append_row(store, row)
        print("record %s fingerprint=%s context=%s"
              % ("ok" if wrote else "duplicate",
                 row.get("fingerprint", "?"), row.get("context_id", "?")))

    if args.index:
        idx = index_stores(store)
        if not idx:
            print("no context stores under %s" % store)
        for e in idx:
            print("%s  n=%-4d %-14s %-22s %-26s %s"
                  % (e["context_id"], e["n"], e["platform"], e["host"],
                     e["build"], ",".join(e["campaigns"])))

    if args.merge:
        path, rows, warn = merge_stores(store, args.merge,
                                        args.context or None,
                                        args.across_contexts)
        for w in warn:
            print("WARNING: %s" % w, file=sys.stderr)
        if path is None:
            return 2
        print("merged %d rows -> %s" % (len(rows), path))

    if args.report or args.md or args.json:
        rows = load_rows(store)
        camp = args.campaign or None
        if not args.all_rows:
            rows = current_rows(rows)
        summary = collate(rows, camp)
        deltas = ab_deltas(summary)
        text = format_report(summary, deltas)
        print(text)
        if args.md:
            args.md.parent.mkdir(parents=True, exist_ok=True)
            args.md.write_text(text)
            print("wrote %s" % args.md)
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps({"summary": summary, "deltas": deltas}, indent=2) + "\n")
            print("wrote %s" % args.json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
