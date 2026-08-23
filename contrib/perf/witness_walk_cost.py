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
import contextlib
import io
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


def self_test():
    """Pin the walk pairing and the ms/block arithmetic.

    This tool produced the published NOTEIDX comparison (about 0.153 vs
    5.31-5.72 ms/block). The arithmetic is a division, so an off-by-one in the
    block count moves the headline figure without any error surfacing.
    """
    import os
    import tempfile

    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    def begin(note, start, tip, scan=1403, mapw=801619):
        return (f"BuildWitnessCache height-walk begin scan_txs={scan} "
                f"mapWallet={mapw} noteidx={note} startHeight={start} tip={tip}\n")

    def done(ms, tip, scan=1403):
        return (f"BuildWitnessCache height-walk done scan_txs={scan} "
                f"elapsed_ms={ms} tip={tip}\n")

    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "debug.log")

        # Inclusive block count: start..tip spans (tip - start + 1) blocks.
        with open(f, "w", encoding="utf8") as fh:
            fh.write(begin(1, 100, 199) + done(20, 199))
        rows = list(walks([f]))
        check(len(rows) == 1, "one complete pair yields one walk")
        if rows:
            r = rows[0]
            check(r["blocks"] == 100, "block count is inclusive of both ends")
            check(abs(r["ms_per_block"] - 0.2) < 1e-9, "ms/block = elapsed / blocks")
            check(r["noteidx"] == 1, "noteidx flag carried from the begin line")
            check(r["scan_txs"] == 1403 and r["mapWallet"] == 801619,
                  "scan_txs and mapWallet carried")

        # A single-block walk must not divide by zero.
        with open(f, "w", encoding="utf8") as fh:
            fh.write(begin(0, 500, 500) + done(7, 500))
        rows = list(walks([f]))
        check(len(rows) == 1 and rows[0]["blocks"] == 1,
              "start == tip is one block, not zero")

        # An unpaired begin yields nothing rather than a half-built row.
        with open(f, "w", encoding="utf8") as fh:
            fh.write(begin(1, 100, 199))
        check(list(walks([f])) == [], "begin with no done yields no walk")

        # A done with no begin must not fabricate a walk.
        with open(f, "w", encoding="utf8") as fh:
            fh.write(done(20, 199))
        check(list(walks([f])) == [], "done with no begin yields no walk")

        # Interleaved walks pair in order, and noteidx is not swapped.
        with open(f, "w", encoding="utf8") as fh:
            fh.write(begin(0, 0, 9) + done(90, 9) + begin(1, 10, 19) + done(2, 19))
        rows = list(walks([f]))
        check(len(rows) == 2, "two pairs yield two walks")
        if len(rows) == 2:
            check(rows[0]["noteidx"] == 0 and rows[1]["noteidx"] == 1,
                  "each walk keeps its own noteidx flag")
            check(abs(rows[0]["ms_per_block"] - 9.0) < 1e-9, "stock walk arithmetic")
            check(abs(rows[1]["ms_per_block"] - 0.2) < 1e-9, "noteidx walk arithmetic")

        # A tip BEFORE the start would give a negative span: dropped, not
        # emitted as a nonsense negative rate.
        with open(f, "w", encoding="utf8") as fh:
            fh.write(begin(0, 200, 100) + done(5, 100))
        check(list(walks([f])) == [], "non-positive block span is dropped")

        # A missing file is skipped with a warning, not a crash.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            check(list(walks([os.path.join(d, "nope.log")])) == [],
                  "missing file yields no walks")
        check("skip" in err.getvalue(), "missing file is reported")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
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
