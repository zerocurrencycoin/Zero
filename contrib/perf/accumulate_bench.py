#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""
Accumulate bench_matrix / postsapling-reindex trial rows and collate A/B reports.

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
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DIR = REPO / "reindex-profile" / "bench-summaries"
LEDGER_JSONL = "ledger.jsonl"
LEDGER_TSV = "ledger.tsv"

TSV_FIELDS = [
    "fingerprint",
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


def fingerprint(row: dict) -> str:
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
        ]
    )
    return hashlib.sha1(key.encode()).hexdigest()[:16]


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


def load_rows(store_dir: Path) -> list[dict]:
    jsonl, _ = ensure_store(store_dir)
    rows = []
    if not jsonl.stat().st_size:
        return rows
    with jsonl.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def existing_fps(store_dir: Path) -> set[str]:
    return {r.get("fingerprint", "") for r in load_rows(store_dir)}


def append_row(store_dir: Path, row: dict) -> bool:
    """Append if fingerprint new. Returns True if written."""
    jsonl, tsv = ensure_store(store_dir)
    row = dict(row)
    row.setdefault("recorded_at", utc_now())
    row.setdefault("binary", "")
    row.setdefault("notes", "")
    row["fingerprint"] = fingerprint(row)
    if row["fingerprint"] in existing_fps(store_dir):
        return False
    with jsonl.open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    with tsv.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TSV_FIELDS, delimiter="\t", extrasaction="ignore")
        w.writerow({k: row.get(k, "") for k in TSV_FIELDS})
    return True


def import_tsv(store_dir: Path, path: Path, campaign: str, run_id: str, binary: str, notes: str) -> int:
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


def collate(rows: list[dict], campaign: str | None = None) -> list[dict]:
    groups: dict[tuple, list[float]] = defaultdict(list)
    meta: dict[tuple, dict] = {}
    for r in rows:
        if campaign and r.get("campaign") != campaign:
            continue
        key = (
            r.get("campaign", ""),
            r.get("mode", ""),
            r.get("condition", ""),
            # Missing heights group separately rather than colliding with a
            # genuine height-0 window. Normalised to str so the key stays
            # sortable: mixing "" and 0 makes sorted() raise on comparison.
            _height_key(r.get("warmup_height")),
            _height_key(r.get("end_height")),
        )
        # A row without a usable rate is EXCLUDED, not zero-filled and not
        # fatal. Before this, one incomplete row raised KeyError and no report
        # could be produced at all; zero-filling instead would silently drag
        # every mean down (see collate_cycle.py for the same defect).
        raw = r.get("blocks_per_sec")
        if raw is None or raw == "":
            print("WARNING: no blocks_per_sec in run_id=%s; row excluded"
                  % r.get("run_id", "?"), file=sys.stderr)
            continue
        try:
            bps = float(raw)
        except (TypeError, ValueError):
            print("WARNING: unparseable blocks_per_sec %r in run_id=%s; row excluded"
                  % (raw, r.get("run_id", "?")), file=sys.stderr)
            continue
        if bps <= 0:
            print("WARNING: non-positive blocks_per_sec %r in run_id=%s; row excluded"
                  % (raw, r.get("run_id", "?")), file=sys.stderr)
            continue
        groups[key].append(bps)
        meta[key] = r
    out = []
    for key, rates in sorted(groups.items()):
        campaign_k, mode, condition, warm_k, end_k = key
        # Back to numbers for output and arithmetic; the padded strings exist
        # only to keep the grouping key sortable.
        warm = int(warm_k) if warm_k else None
        end = int(end_k) if end_k else None
        blocks = end - warm if (warm is not None and end is not None) else None
        out.append(
            {
                "campaign": campaign_k,
                "mode": mode,
                "condition": condition,
                "warmup_height": warm,
                "end_height": end,
                "blocks": blocks,
                "n": len(rates),
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
                "%s/%s window %d-%d: %s mean=%.2f (n=%d) vs %s mean=%.2f (n=%d) -> delta %+.2f blk/s (%+.2f%%)"
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
                    pct,
                )
            )
    return lines


def format_report(summary: list[dict], deltas: list[str]) -> str:
    lines = [
        "# Bench ledger collation",
        "",
        "Generated by `contrib/perf/accumulate_bench.py --report`.",
        "",
        "| campaign | mode | condition | window | n | mean blk/s | stdev | min | max |",
        "|----------|------|-----------|--------|---|------------|-------|-----|-----|",
    ]
    for s in summary:
        window = "%d-%d" % (s["warmup_height"], s["end_height"])
        lines.append(
            "| %s | %s | %s | %s | %d | %.2f | %.2f | %.2f | %.2f |"
            % (
                s["campaign"],
                s["mode"],
                s["condition"],
                window,
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
    a = dict(base); a["blocks_per_sec"] = 10.0; a["warmup_height"] = 0
    b = dict(base); b["blocks_per_sec"] = 20.0; b.pop("warmup_height", None)
    with contextlib.redirect_stderr(io.StringIO()):
        out = collate([a, b])
    check(len(out) == 2,
          "a missing height does not collapse into a genuine height-0 window")

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
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--mode", default="reindex")
    ap.add_argument("--condition", default="stock")
    ap.add_argument("--trial", type=int, default=1)
    ap.add_argument("--warmup-height", type=int)
    ap.add_argument("--end-height", type=int)
    ap.add_argument("--blocks", type=int)
    ap.add_argument("--elapsed-s", type=float)
    ap.add_argument("--blocks-per-sec", type=float)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--md", type=Path, help="Write markdown report path")
    ap.add_argument("--json", type=Path, help="Write collation JSON path")
    args = ap.parse_args()

    store = args.store_dir
    ensure_store(store)

    if args.import_tsv:
        camp = args.campaign or "imported"
        n = import_tsv(store, args.import_tsv, camp, args.run_id, args.binary, args.notes)
        print("imported_added=%d path=%s campaign=%s" % (n, args.import_tsv, camp))

    if args.append:
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
            print("ERROR: --append requires --campaign --run-id --warmup-height "
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
        }
        wrote = append_row(store, row)
        print("append %s fingerprint=%s" % ("ok" if wrote else "duplicate", fingerprint(row)))

    if args.report or args.md or args.json:
        rows = load_rows(store)
        camp = args.campaign or None
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
