#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Collate cycle-campaign ledger rows (CAMPAIGN=cycle-1/2/3) into a rematch table.

Usage:
  python3 contrib/perf/collate_cycle.py
  python3 contrib/perf/collate_cycle.py --md reindex-profile/cycle-campaign/REPORT-cycle.md
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_STORE = REPO / "reindex-profile" / "bench-summaries"
DEFAULT_STATUS = REPO / "reindex-profile" / "cycle-campaign" / "status.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    rows = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def cycle_rows(store_dir: Path) -> list[dict]:
    jsonl = store_dir / "ledger.jsonl"
    return [r for r in load_jsonl(jsonl) if str(r.get("campaign", "")).startswith("cycle-")]


def group_rates(rows: list[dict]) -> dict[tuple[str, str, str], list[float]]:
    g: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for r in rows:
        try:
            bps = float(r.get("blocks_per_sec") or 0)
        except (TypeError, ValueError):
            continue
        key = (str(r.get("campaign")), str(r.get("mode")), str(r.get("condition")))
        g[key].append(bps)
    return g


def format_report(rows: list[dict], status: list[dict]) -> str:
    grouped = group_rates(rows)
    conditions = sorted({c for _, _, c in grouped})
    campaigns = sorted({camp for camp, _, _ in grouped})
    lines = [
        "# Cycle campaign collation",
        "",
        "Same trial id (`condition`) rematched across `CAMPAIGN=cycle-N`. Rates are mean blk/s.",
        "",
    ]
    if not conditions:
        lines.append("No cycle-* ledger rows yet.")
        lines.append("")
        return "\n".join(lines)

    header = ["condition", "mode"] + campaigns + ["delta_c2_vs_c1"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")

    def mean_for(camp: str, mode: str, cond: str) -> float | None:
        vals = grouped.get((camp, mode, cond))
        if not vals:
            return None
        return round(statistics.mean(vals), 4)

    modes_by_cond: dict[str, str] = {}
    for camp, mode, cond in grouped:
        modes_by_cond.setdefault(cond, mode)

    for cond in conditions:
        mode = modes_by_cond.get(cond, "")
        cells = [cond, mode]
        c1 = mean_for("cycle-1", mode, cond)
        c2 = mean_for("cycle-2", mode, cond)
        for camp in campaigns:
            v = mean_for(camp, mode, cond)
            cells.append("" if v is None else str(v))
        if c1 and c2 and c1 != 0:
            cells.append(str(round((c2 - c1) / c1, 4)))
        else:
            cells.append("")
        lines.append("| " + " | ".join(cells) + " |")

    lines.extend(["", "## Status log", ""])
    if not status:
        lines.append("No status.jsonl rows.")
    else:
        lines.append("| utc | cycle | id | result | run_id |")
        lines.append("|-----|-------|----|--------|--------|")
        for s in status[-40:]:
            lines.append(
                "| {utc} | {cycle} | {id} | {result} | {run_id} |".format(
                    utc=s.get("utc", ""),
                    cycle=s.get("cycle", ""),
                    id=s.get("id", ""),
                    result=s.get("result", ""),
                    run_id=s.get("run_id", ""),
                )
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    ap.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    ap.add_argument("--md", type=Path)
    args = ap.parse_args()
    text = format_report(cycle_rows(args.store_dir), load_jsonl(args.status))
    print(text)
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(text)
        print("wrote %s" % args.md, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
