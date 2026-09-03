#!/usr/bin/env python3
"""Back-annotate existing ledger rows with platform / build / date blocks.

Schema: contrib/perf/docs/SCHEMA.md S8 step 1.

Every row in both ledgers was produced on this machine before any platform
field existed. Stamping them now is trivially correct -- "all macOS/arm64" is
true by inspection today, and becomes archaeology the moment a second platform
appears.

Values that cannot be known are marked, never invented:
  - platform  : this system's values, confidence "assumed_single_host"
  - build     : from the binary if its BUILD_DATE precedes the row, else
                left empty with confidence "unknown"
  - started_at: derived from run_id timestamp where the id carries one,
                else absent; confidence recorded either way

Writes a NEW file (<name>.v2.jsonl) and never touches the original, per
"mark superseded results, do not delete them".

Usage:
  contrib/perf/backannotate_ledger.py --dry-run
  contrib/perf/backannotate_ledger.py --write
  contrib/perf/backannotate_ledger.py --self-test
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stamp as ps  # noqa: E402

import rbpaths
STORE = rbpaths.store_dir()
LEDGERS = ("ledger.jsonl", "cpu_ledger.jsonl")

# run_id shapes seen in the ledgers, e.g. tiny-20260819T234958Z
RUNID_TS = re.compile(r"(\d{8})T(\d{6})Z")


def started_at_from_run_id(run_id):
    """Recover a start time from a run_id that embeds one. Returns None if the
    id carries no timestamp -- absent beats fabricated."""
    if not run_id:
        return None
    m = RUNID_TS.search(str(run_id))
    if not m:
        return None
    d, t = m.group(1), m.group(2)
    return "%s-%s-%sT%s:%s:%sZ" % (d[:4], d[4:6], d[6:8], t[:2], t[2:4], t[4:6])


def annotate(row, plat, build):
    out = dict(row)
    out.setdefault("schema", 1)
    out["platform"] = dict(plat)
    out["platform_confidence"] = "assumed_single_host"

    started = started_at_from_run_id(row.get("run_id"))
    if started:
        out["started_at"] = started
        out["date_confidence"] = "derived_from_run_id"
    elif row.get("recorded_at"):
        out["date_confidence"] = "recorded_at_only"
    else:
        out["date_confidence"] = "unknown"

    # Only claim a build if it cannot be excluded on dates.
    bdate = (build or {}).get("date", "")
    rec = row.get("recorded_at", "")
    if bdate and rec and bdate[:10] <= rec[:10]:
        out["build"] = dict(build)
        out["build_confidence"] = "current_binary_plausible_by_date"
    else:
        out["build"] = {"version": "", "commit": "", "dirty": None,
                        "tag": None, "date": "", "raw": ""}
        out["build_confidence"] = "unknown"
    return out


def process(path, plat, build, write):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            if ln.strip():
                rows.append(json.loads(ln))
    done = [annotate(r, plat, build) for r in rows]
    out_path = path.replace(".jsonl", ".v2.jsonl")
    if write:
        with open(out_path, "w", encoding="utf-8") as fh:
            for r in done:
                fh.write(json.dumps(r, sort_keys=True) + "\n")
    return rows, done, out_path


def self_test():
    ok = True

    def check(c, m):
        nonlocal ok
        if not c:
            print("FAIL: " + m, file=sys.stderr)
            ok = False

    check(started_at_from_run_id("tiny-20260819T234958Z") == "2026-08-19T23:49:58Z",
          "run_id timestamp parse")
    check(started_at_from_run_id("historical-postsapling-202607") is None,
          "run_id without full timestamp yields None, not a guess")
    check(started_at_from_run_id(None) is None, "None run_id tolerated")

    plat = {"os": "macos", "arch": "arm64"}
    r = annotate({"run_id": "x-20260101T000000Z", "recorded_at": "2026-01-01T00:00:00Z"},
                 plat, {"date": "2026-08-19 12:32:25 -0700"})
    check(r["build_confidence"] == "unknown",
          "binary built after the row must not be claimed")
    check(r["date_confidence"] == "derived_from_run_id", "date confidence set")
    check(r["platform_confidence"] == "assumed_single_host", "platform marked assumed")

    r2 = annotate({"run_id": "n", "recorded_at": "2026-08-20T00:00:00Z"},
                  plat, {"date": "2026-08-19 12:32:25 -0700"})
    check(r2["build_confidence"].startswith("current_binary"),
          "plausible build accepted by date")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv[1:])
    if a.self_test:
        return self_test()
    if not (a.write or a.dry_run):
        ap.error("pass --dry-run or --write")

    plat = ps.platform_block()
    build = ps.build_block(rbpaths.target_binary())
    for name in LEDGERS:
        p = os.path.join(STORE, name)
        if not os.path.exists(p):
            print("skip (absent): %s" % name)
            continue
        rows, done, out_path = process(p, plat, build, a.write)
        claimed = sum(1 for r in done if r["build_confidence"] != "unknown")
        dated = sum(1 for r in done if r["date_confidence"] == "derived_from_run_id")
        print("%-18s rows=%d  build_claimed=%d  start_derived=%d  -> %s%s"
              % (name, len(rows), claimed, dated, os.path.basename(out_path),
                 "" if a.write else " (dry run)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
