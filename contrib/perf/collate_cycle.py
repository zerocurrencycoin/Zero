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
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                # One bad line must not abort the whole collation, and must not
                # vanish either: the row is a real trial, and dropping it
                # silently changes every mean computed below.
                print("WARNING: %s:%d: malformed JSON, skipped (%s)"
                      % (path, lineno, exc.msg), file=sys.stderr)
    return rows


def cycle_rows(store_dir: Path) -> list[dict]:
    jsonl = store_dir / "ledger.jsonl"
    return [r for r in load_jsonl(jsonl) if str(r.get("campaign", "")).startswith("cycle-")]


def group_rates(rows: list[dict]) -> dict[tuple[str, str, str], list[float]]:
    g: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for r in rows:
        raw = r.get("blocks_per_sec")
        # A missing or unparseable rate is EXCLUDED, not counted as zero.
        # `float(x or 0)` silently contributed 0.0 to the mean, so one
        # incomplete row could halve a reported rate with no warning.
        if raw is None or raw == "":
            continue
        try:
            bps = float(raw)
        except (TypeError, ValueError):
            continue
        if bps <= 0:
            print("WARNING: skipping non-positive blocks_per_sec %r in %s"
                  % (raw, r.get("run_id", "?")), file=sys.stderr)
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


def self_test() -> int:
    """Pin the collation arithmetic and its handling of bad input.

    This file computes the cross-cycle rate comparison. Both failure modes are
    silent: a malformed ledger line used to abort the run, and a missing rate
    used to be counted as 0.0, dragging a reported mean down with no warning.
    """
    import io
    import contextlib
    import tempfile

    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    def row(camp, cond, bps, mode="reindex", **kw):
        r = {"campaign": camp, "mode": mode, "condition": cond,
             "blocks_per_sec": bps, "run_id": "r-%s-%s" % (camp, cond)}
        r.update(kw)
        return r

    # Grouping: same (campaign, mode, condition) accumulates.
    g = group_rates([row("cycle-1", "p0", 100.0), row("cycle-1", "p0", 200.0),
                     row("cycle-2", "p0", 150.0)])
    check(g[("cycle-1", "reindex", "p0")] == [100.0, 200.0], "rates group by key")
    check(g[("cycle-2", "reindex", "p0")] == [150.0], "separate campaigns stay apart")

    # A missing rate is EXCLUDED, not counted as zero. This is the defect:
    # with `float(x or 0)` the mean below would be 50.0 rather than 100.0.
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        g = group_rates([row("cycle-1", "p0", 100.0),
                         row("cycle-1", "p0", None),
                         row("cycle-1", "p0", ""),
                         row("cycle-1", "p0", "not-a-number")])
    check(g[("cycle-1", "reindex", "p0")] == [100.0],
          "missing/unparseable rates are excluded, not zero-filled")
    check(statistics.mean(g[("cycle-1", "reindex", "p0")]) == 100.0,
          "the mean is not dragged down by absent rows")

    # A non-positive rate is impossible and is reported, not averaged in.
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        g = group_rates([row("cycle-1", "p0", 100.0), row("cycle-1", "p0", 0.0),
                         row("cycle-1", "p0", -5.0)])
    check(g[("cycle-1", "reindex", "p0")] == [100.0], "non-positive rates dropped")
    check("non-positive" in err.getvalue(), "dropping a bad rate warns")

    with tempfile.TemporaryDirectory() as d:
        store = Path(d)
        led = store / "ledger.jsonl"

        # Only cycle-* campaigns are collated.
        with led.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps(row("cycle-1", "p0", 100.0)) + "\n")
            fh.write(json.dumps(row("postsapling", "p0", 999.0)) + "\n")
        rows = cycle_rows(store)
        check(len(rows) == 1 and rows[0]["campaign"] == "cycle-1",
              "non-cycle campaigns are excluded")

        # A malformed line is skipped with a warning; good rows survive.
        with led.open("a", encoding="utf-8") as fh:
            fh.write("{not json\n")
            fh.write(json.dumps(row("cycle-2", "p0", 110.0)) + "\n")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rows = cycle_rows(store)
        check(len(rows) == 2, "a malformed line does not abort the collation")
        check("malformed JSON" in err.getvalue(), "the malformed line is reported")

        # An absent or empty ledger is not an error.
        check(load_jsonl(store / "nope.jsonl") == [], "absent ledger reads empty")
        (store / "empty.jsonl").write_text("", encoding="utf-8")
        check(load_jsonl(store / "empty.jsonl") == [], "empty ledger reads empty")

        # The report renders, and the delta is only shown when both sides exist.
        text = format_report(rows, [])
        check("cycle-1" in text and "cycle-2" in text, "report lists both campaigns")
        check(format_report([], []).find("No cycle-* ledger rows yet.") > 0,
              "an empty ledger produces a clear message, not a broken table")

        # Delta arithmetic: (c2 - c1) / c1, guarded against a zero baseline.
        both = [row("cycle-1", "p1", 100.0), row("cycle-2", "p1", 110.0)]
        text = format_report(both, [])
        check("0.1" in text, "delta is a fraction of the cycle-1 mean")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
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
