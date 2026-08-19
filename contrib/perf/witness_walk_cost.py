#!/usr/bin/env python3
"""Per-block cost of the witness height walk, from debug.log.

Pairs the two lines BuildWitnessCache already emits:

  BuildWitnessCache height-walk begin scan_txs=N mapWallet=N noteidx=0|1 startHeight=H tip=T
  BuildWitnessCache height-walk done  scan_txs=N elapsed_ms=M tip=T

and reports ms/block for each walk, split by the noteidx flag. No node changes
and no new instrumentation: this only reads what is already logged.

Why: the per-block figures used in planning (about 5.32 ms/blk stock,
0.153 ms/blk NOTEIDX) were extrapolated from a single mainnet window
(M-WAL-WITNESS-TIP-AB). This replaces that extrapolation with a measurement
over whatever walks a log actually contains.

Usage:
  contrib/perf/witness_walk_cost.py <debug.log> [more.log ...]
  contrib/perf/witness_walk_cost.py --tsv <debug.log>     # machine-readable

Exit: 0 if at least one complete walk was found, 1 if none.
"""
import re
import sys

BEGIN = re.compile(
    r"BuildWitnessCache height-walk begin "
    r"scan_txs=(?P<scan>\d+) mapWallet=(?P<mapw>\d+) noteidx=(?P<note>[01]) "
    r"startHeight=(?P<start>\d+) tip=(?P<tip>\d+)")
DONE = re.compile(
    r"BuildWitnessCache height-walk done "
    r"scan_txs=(?P<scan>\d+) elapsed_ms=(?P<ms>\d+) tip=(?P<tip>\d+)")


def walks(paths):
    """Yield one dict per completed walk, pairing each begin with the next done."""
    pending = None
    for path in paths:
        try:
            fh = open(path, encoding="utf8", errors="replace")
        except OSError as exc:
            print(f"skip {path}: {exc}", file=sys.stderr)
            continue
        with fh:
            for line in fh:
                m = BEGIN.search(line)
                if m:
                    pending = m.groupdict()
                    continue
                m = DONE.search(line)
                if m and pending:
                    start = int(pending["start"])
                    tip = int(m.group("tip"))
                    blocks = tip - start + 1
                    ms = int(m.group("ms"))
                    if blocks > 0:
                        yield {
                            "noteidx": int(pending["note"]),
                            "scan_txs": int(pending["scan"]),
                            "mapWallet": int(pending["mapw"]),
                            "start": start,
                            "tip": tip,
                            "blocks": blocks,
                            "elapsed_ms": ms,
                            "ms_per_block": ms / blocks,
                        }
                    pending = None


def main(argv):
    tsv = "--tsv" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__)
        return 2

    rows = list(walks(paths))
    if not rows:
        print("no complete height-walk pairs found", file=sys.stderr)
        return 1

    if tsv:
        print("noteidx\tblocks\tscan_txs\tmapWallet\telapsed_ms\tms_per_block")
        for r in rows:
            print(f"{r['noteidx']}\t{r['blocks']}\t{r['scan_txs']}\t{r['mapWallet']}"
                  f"\t{r['elapsed_ms']}\t{r['ms_per_block']:.4f}")
        return 0

    print(f"{'noteidx':>7} {'blocks':>9} {'scan_txs':>9} {'elapsed_ms':>11} {'ms/block':>10}")
    for r in rows:
        print(f"{r['noteidx']:>7} {r['blocks']:>9} {r['scan_txs']:>9} "
              f"{r['elapsed_ms']:>11} {r['ms_per_block']:>10.4f}")

    for flag, label in ((0, "stock"), (1, "NOTEIDX")):
        sel = [r for r in rows if r["noteidx"] == flag]
        if not sel:
            continue
        blocks = sum(r["blocks"] for r in sel)
        ms = sum(r["elapsed_ms"] for r in sel)
        print(f"\n{label}: {len(sel)} walk(s), {blocks} blocks, {ms} ms "
              f"=> {ms / blocks:.4f} ms/block")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
