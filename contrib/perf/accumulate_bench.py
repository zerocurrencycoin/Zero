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
            int(r.get("warmup_height", 0)),
            int(r.get("end_height", 0)),
        )
        groups[key].append(float(r["blocks_per_sec"]))
        meta[key] = r
    out = []
    for key, rates in sorted(groups.items()):
        campaign_k, mode, condition, warm, end = key
        out.append(
            {
                "campaign": campaign_k,
                "mode": mode,
                "condition": condition,
                "warmup_height": warm,
                "end_height": end,
                "blocks": end - warm,
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
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
