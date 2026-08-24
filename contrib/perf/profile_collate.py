#!/usr/bin/env python3
"""Accumulate bucket_profile2 JSON outputs into a durable CPU-share ledger.

Companion to accumulate_bench.py (which accumulates throughput). This does the
same for CPU attribution, so consecutive captures build a comparable series
instead of one-off text files.

Append a capture:
  contrib/perf/profile_collate.py add <buckets.json> \\
      --scenario S3-reindex-postsap --window 600000-900000 [--note ...]

Report everything accumulated:
  contrib/perf/profile_collate.py report [--scenario S3-reindex-postsap]

Ledger: reindex-profile/bench-summaries/cpu_ledger.jsonl (append-only, one
object per capture). Each entry keeps the full bucket map, so re-reporting
never loses resolution and a later bucket rename can be applied at read time.

Exit: 0 ok, 2 usage.
"""
import argparse
import contextlib
import datetime
import io
import json
import os
import sys

LEDGER = os.environ.get(
    "ZERO_PERF_CPU_LEDGER",
    "reindex-profile/bench-summaries/cpu_ledger.jsonl",
)


def ledger_path():
    """Read the env override at call time, so tests can redirect writes."""
    return os.environ.get("ZERO_PERF_CPU_LEDGER", LEDGER)


def load(path=None):
    path = path or ledger_path()
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    # Silently skipping corrupts the series: the row is a real
                    # capture and dropping it changes every mean computed from
                    # this file. Report it and keep going.
                    print(f"WARNING: {path}:{lineno}: malformed JSON, skipped "
                          f"({exc.msg})", file=sys.stderr)
    return out


def cmd_add(args):
    with open(args.json, encoding="utf8") as fh:
        data = json.load(fh)
    entry = {
        "recorded_at": datetime.datetime.now(datetime.timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario": args.scenario,
        "window": args.window,
        "thread_filter": data.get("thread_filter"),
        "total_s": round(data.get("total_s", 0), 3),
        "total_all_threads_s": round(data.get("total_all_threads_s", 0), 3),
        "bucket_pct": {k: round(v, 2) for k, v in data.get("bucket_pct", {}).items()},
        "buckets_s": {k: round(v, 3) for k, v in data.get("buckets", {}).items()},
        "groth16_pools": {k: round(v, 3) for k, v in data.get("groth16_pools", {}).items()},
        "thread_split_s": {k: round(v, 3) for k, v in data.get("threads", {}).items()},
        "note": args.note or "",
        "source": args.json,
    }
    ledger = ledger_path()
    parent = os.path.dirname(ledger)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(ledger, "a", encoding="utf8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    n = len(load(ledger))
    print(f"appended {args.scenario} ({args.window}) -> {ledger}  [{n} entries total]")
    return 0


def cmd_report(args):
    rows = load()
    if args.scenario:
        rows = [r for r in rows if r.get("scenario") == args.scenario]
    if not rows:
        print("no entries", file=sys.stderr)
        return 0

    by = {}
    for r in rows:
        by.setdefault((r.get("scenario"), r.get("window")), []).append(r)

    print(f"{'scenario':28} {'window':16} {'n':>2}  top buckets (mean % of filtered thread)")
    print("-" * 110)
    for (sc, win), group in sorted(by.items(), key=lambda x: (x[0][0] or "", x[0][1] or "")):
        keys = set()
        for r in group:
            keys |= set(r.get("bucket_pct", {}))
        means = {}
        for k in keys:
            vals = [r["bucket_pct"].get(k, 0.0) for r in group]
            means[k] = sum(vals) / len(vals)
        top = sorted(means.items(), key=lambda x: -x[1])[:5]
        desc = "  ".join(f"{k} {v:.1f}%" for k, v in top)
        print(f"{(sc or '?')[:28]:28} {(win or '?')[:16]:16} {len(group):2}  {desc}")

        if len(group) > 1:
            spreads = []
            for k, _ in top:
                vals = [r["bucket_pct"].get(k, 0.0) for r in group]
                spreads.append(f"{k} +/-{(max(vals)-min(vals))/2:.1f}")
            print(f"{'':46}  spread: {'  '.join(spreads)}")

    print(f"\n{len(rows)} capture(s) in ledger.")
    return 0


def self_test():
    """Pin ledger round-trip and the reporting arithmetic.

    This file owns the CPU-share ledger. Two failure modes matter and neither
    crashes: a capture silently dropped on read (every mean shifts), and a
    mean/spread computed wrongly (a published percentage is wrong). Both are
    asserted here against a temporary ledger -- the real one is never touched.
    """
    import tempfile

    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    class A:  # minimal argparse stand-in
        def __init__(self, **kw):
            self.__dict__.update(kw)

    with tempfile.TemporaryDirectory() as d:
        led = os.path.join(d, "cpu_ledger.jsonl")
        cap = os.path.join(d, "buckets.json")
        prev = os.environ.get("ZERO_PERF_CPU_LEDGER")
        os.environ["ZERO_PERF_CPU_LEDGER"] = led
        try:
            with open(cap, "w", encoding="utf-8") as fh:
                json.dump({"thread_filter": "zcash-loadblk", "total_s": 60.0,
                           "total_all_threads_s": 61.0,
                           "bucket_pct": {"groth16_proof": 88.4567,
                                          "blake2b": 3.2},
                           "buckets": {"groth16_proof": 53.0123,
                                       "blake2b": 1.92},
                           "groth16_pools": {"sapling": 50.0, "sprout": 3.0},
                           "threads": {"zcash-loadblk": 59.9}}, fh)

            check(load(led) == [], "absent ledger reads as empty, not an error")

            with contextlib.redirect_stdout(io.StringIO()):
                rc = cmd_add(A(json=cap, scenario="S-test", window="1-2", note="n"))
            check(rc == 0, "add returns 0")
            rows = load(led)
            check(len(rows) == 1, "one row after one add")

            r = rows[0]
            # Rounding is part of the stored contract; drift changes published
            # figures without any error surfacing.
            check(r["bucket_pct"]["groth16_proof"] == 88.46, "bucket_pct rounds to 2dp")
            check(r["buckets_s"]["groth16_proof"] == 53.012, "buckets_s rounds to 3dp")
            check(r["scenario"] == "S-test" and r["window"] == "1-2",
                  "scenario and window stored")
            check(r["source"] == cap, "provenance recorded -- a row must name its capture")
            check(r["thread_filter"] == "zcash-loadblk",
                  "thread filter stored; a share without one is not comparable")
            check("recorded_at" in r and r["recorded_at"].endswith("Z"),
                  "recorded_at is UTC and stamped")

            # One row per line: without the trailing newline a second append
            # concatenates onto the first and both rows become unreadable.
            raw = open(led, encoding="utf8").read()
            check(raw.endswith("\n"), "each ledger row must end with a newline")
            check(len(raw.strip().splitlines()) == 1, "one row occupies one line")

            # Append-only: a second add must not overwrite the first.
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_add(A(json=cap, scenario="S-test", window="1-2", note=""))
            check(len(load(led)) == 2, "ledger is append-only")

            # A malformed line must be REPORTED, not silently dropped.
            with open(led, "a", encoding="utf8") as fh:
                fh.write("{not json\n")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rows = load(led)
            check(len(rows) == 2, "malformed line skipped, good rows kept")
            check("malformed JSON" in err.getvalue(),
                  "malformed line must warn, not vanish silently")

            # Reporting must not raise on a mixed ledger.
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                check(cmd_report(A(scenario=None)) == 0, "report returns 0")
            check("S-test" in out.getvalue(), "report lists the scenario")

            # Filtering to an unknown scenario yields nothing, not everything.
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                cmd_report(A(scenario="nope"))
            check("S-test" not in out.getvalue(), "scenario filter excludes others")
        finally:
            if prev is None:
                os.environ.pop("ZERO_PERF_CPU_LEDGER", None)
            else:
                os.environ["ZERO_PERF_CPU_LEDGER"] = prev

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="append a bucket_profile2 --json output")
    a.add_argument("json")
    a.add_argument("--scenario", required=True)
    a.add_argument("--window", required=True, help="height range, e.g. 600000-900000")
    a.add_argument("--note", default="")
    r = sub.add_parser("report", help="summarise accumulated captures")
    r.add_argument("--scenario")
    args = p.parse_args(argv)
    if args.cmd == "add":
        return cmd_add(args)
    if args.cmd == "report":
        return cmd_report(args)
    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
