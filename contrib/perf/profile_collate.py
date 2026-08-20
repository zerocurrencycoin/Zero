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
import datetime
import json
import os
import sys

LEDGER = "reindex-profile/bench-summaries/cpu_ledger.jsonl"


def load(path=LEDGER):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
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
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "a", encoding="utf8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    n = len(load())
    print(f"appended {args.scenario} ({args.window}) -> {LEDGER}  [{n} entries total]")
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


def main(argv):
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
