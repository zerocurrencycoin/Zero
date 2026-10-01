#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""
Replay block timestamps through zerod's block-rate warning and fast-block checks.
--help for options.

For every block in the range, from a synced node over JSON-RPC (batched):

- Block-rate warning (PartitionCheck): count blocks with timestamps in the
  4 hours ending at each block's time, at most one warning per 24 hours, and
  report when the count is at or below the low threshold or at or above the high
  threshold (Poisson pdf at most 1 in 109,500, as in src/main.cpp).
- Fast-block runs: runs of consecutive timestamp gaps under --gap seconds, of
  length --run or more; with --miners, only runs by the same coinbase payout.
- Coinbase-only blocks.

Timestamps are miner-set; the replay measures what the chain records, not
arrival times at a node.
"""

import argparse
import base64
import bisect
import http.client
import json
import math
import os
import sys
from datetime import datetime, timezone

SPACING = 120               # seconds per block (Blossom not active)
SPAN = 4 * 3600             # PartitionCheck window
FIFTY_YEARS = 50 * 365 * 24 * 3600
THRESHOLD = 1.0 / (FIFTY_YEARS // SPAN)
ALERT_INTERVAL = 24 * 3600  # PartitionCheck warns at most once per day
BLOCKS_PER_DAY = 86400 // SPACING


def poisson_bounds(expected):
    def pdf(n):
        return math.exp(n * math.log(expected) - expected - math.lgamma(n + 1))
    low = max(n for n in range(0, expected) if pdf(n) <= THRESHOLD)
    high = min(n for n in range(expected, expected * 4) if pdf(n) <= THRESHOLD)
    return low, high


def read_conf(path):
    conf = {}
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip()
    return conf


class Rpc:
    def __init__(self, args):
        datadir = os.path.expanduser(args.datadir)
        conf = read_conf(args.conf or os.path.join(datadir, "zero.conf"))
        user = args.rpcuser or conf.get("rpcuser", "")
        password = args.rpcpassword or conf.get("rpcpassword", "")
        if not user:
            cookie = os.path.join(datadir, "regtest" if args.regtest else "", ".cookie")
            if os.path.exists(cookie):
                user, password = open(cookie).read().strip().split(":", 1)
        self.port = args.rpcport or int(conf.get("rpcport", 23811))
        self.host = args.rpchost
        self.auth = "Basic " + base64.b64encode(("%s:%s" % (user, password)).encode()).decode()
        self.next_id = 0

    def batch(self, calls, allow_errors=False):
        reqs = []
        for method, params in calls:
            self.next_id += 1
            reqs.append({"jsonrpc": "1.0", "id": self.next_id, "method": method, "params": params})
        conn = http.client.HTTPConnection(self.host, self.port, timeout=600)
        conn.request("POST", "/", json.dumps(reqs), {"Authorization": self.auth, "Content-Type": "application/json"})
        resp = conn.getresponse()
        body = resp.read()
        if resp.status != 200:
            sys.exit("rpc: HTTP %d: %s" % (resp.status, body[:200]))
        out = sorted(json.loads(body), key=lambda r: r["id"])
        for r in out:
            if r.get("error") and not allow_errors:
                sys.exit("rpc: %s" % r["error"])
        return [None if r.get("error") else r["result"] for r in out]

    def call(self, method, *params):
        return self.batch([(method, list(params))])[0]


def fetch_blocks(rpc, start, end, batch, miners):
    """Yield (height, time, ntx, difficulty, miner) for start..end inclusive."""
    for lo in range(start, end + 1, batch):
        hi = min(end, lo + batch - 1)
        hashes = rpc.batch([("getblockhash", [h]) for h in range(lo, hi + 1)])
        blocks = rpc.batch([("getblock", [hsh, 1]) for hsh in hashes])
        payouts = [None] * len(blocks)
        if miners:
            # The genesis coinbase is not indexed; such errors leave the miner unknown.
            coinbases = rpc.batch([("getrawtransaction", [b["tx"][0], 1]) for b in blocks], allow_errors=True)
            for i, cb in enumerate(coinbases):
                if cb is None:
                    continue
                addrs = []
                for out in cb.get("vout", []):
                    addrs += out.get("scriptPubKey", {}).get("addresses", [])
                payouts[i] = addrs[-1] if addrs else None
        for i, b in enumerate(blocks):
            yield b["height"], b["time"], len(b["tx"]), b.get("difficulty"), payouts[i]
        print("  fetched %d..%d" % (lo, hi), file=sys.stderr)


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M")


def main():
    p = argparse.ArgumentParser(description="Replay block timestamps through zerod's block-rate and fast-block checks.")
    rng = p.add_mutually_exclusive_group(required=True)
    rng.add_argument("--first-year", action="store_true", help="heights 0 .. 365 days of blocks")
    rng.add_argument("--last-days", type=int, metavar="N", help="the last N days of blocks up to the tip")
    rng.add_argument("--range", nargs=2, type=int, metavar=("FROM", "TO"), help="explicit heights")
    rng.add_argument("--all", action="store_true", help="genesis to tip")
    p.add_argument("--gap", type=int, default=2, help="fast-block gap in seconds (default 2)")
    p.add_argument("--run", type=int, default=2, help="consecutive fast gaps to report (default 2)")
    p.add_argument("--miners", action="store_true", help="count a run only within one coinbase payout (needs txindex; slower)")
    p.add_argument("--csv", metavar="FILE", help="write height,time,gap,ntx,difficulty,miner per block")
    p.add_argument("--max-events", type=int, default=20, help="events listed per check (default 20)")
    p.add_argument("--batch", type=int, default=500, help="RPC batch size (default 500)")
    p.add_argument("--datadir", default="~/.zero", help="data directory for zero.conf (default ~/.zero)")
    p.add_argument("--conf", help="zero.conf path")
    p.add_argument("--regtest", action="store_true", help="regtest cookie location")
    p.add_argument("--rpchost", default="127.0.0.1")
    p.add_argument("--rpcport", type=int)
    p.add_argument("--rpcuser")
    p.add_argument("--rpcpassword")
    args = p.parse_args()

    rpc = Rpc(args)
    tip = rpc.call("getblockcount")
    if args.first_year:
        start, end = 0, min(tip, 365 * BLOCKS_PER_DAY)
    elif args.last_days:
        start, end = max(0, tip - args.last_days * BLOCKS_PER_DAY), tip
    elif args.range:
        start, end = max(0, args.range[0]), min(tip, args.range[1])
    else:
        start, end = 0, tip

    expected = SPAN // SPACING
    low, high = poisson_bounds(expected)
    print("range %d..%d (tip %d); block-rate thresholds: <= %d or >= %d of %d expected in 4 h"
          % (start, end, tip, low, high, expected))

    csv = open(args.csv, "w") if args.csv else None
    if csv:
        csv.write("height,time,gap,ntx,difficulty,miner\n")

    window = []            # timestamps in the current 4-hour window
    last_alert = None
    rate_events = []
    fast_events = []
    run_len, run_start, run_miner = 0, None, None
    prev_time, prev_miner = None, None
    first_time = None
    empty = 0
    blocks = 0

    for height, t, ntx, diff, miner in fetch_blocks(rpc, start, end, args.batch, args.miners):
        blocks += 1
        gap = None if prev_time is None else t - prev_time
        if csv:
            csv.write("%d,%d,%s,%d,%s,%s\n" % (height, t, "" if gap is None else gap, ntx, diff, miner or ""))
        if ntx <= 1:
            empty += 1

        # Fast-block runs.
        fast = gap is not None and gap < args.gap and (not args.miners or (miner and miner == prev_miner))
        if fast:
            if run_len == 0:
                run_start, run_miner = height - 1, miner
            run_len += 1
            if run_len == args.run:
                fast_events.append((run_start, t, run_miner))
        else:
            run_len = 0
        prev_time, prev_miner = t, miner

        # Block-rate warning, evaluated at each block's time.
        bisect.insort(window, t)
        while window and window[0] <= t - SPAN:
            window.pop(0)
        # Like the node: no check while the chain does not reach back past the window
        # ("ran out of chain"), and none in the first window of blocks (initial sync).
        if first_time is None:
            first_time = t
        covered = first_time <= t - SPAN and height - start >= expected
        if covered and (last_alert is None or t - last_alert >= ALERT_INTERVAL):
            n = len(window)
            if n <= low or n >= high:
                rate_events.append((height, t, n, "low" if n <= low else "high"))
                last_alert = t

    if csv:
        csv.close()

    days = max(1, blocks // BLOCKS_PER_DAY)
    print("blocks %d (~%d days); coinbase-only blocks %d (%.2f%%)" % (blocks, days, empty, 100.0 * empty / max(1, blocks)))
    print("block-rate warnings: %d (low %d, high %d)" % (len(rate_events),
          sum(1 for e in rate_events if e[3] == "low"), sum(1 for e in rate_events if e[3] == "high")))
    for h, t, n, kind in rate_events[:args.max_events]:
        print("  %s at %d (%s): %d blocks in 4 h" % (kind, h, iso(t), n))
    print("fast-block runs (%d+ gaps under %d s%s): %d" % (args.run, args.gap, ", same miner" if args.miners else "", len(fast_events)))
    for h, t, m in fast_events[:args.max_events]:
        print("  from %d (%s)%s" % (h, iso(t), " miner %s" % m if m else ""))


if __name__ == "__main__":
    main()
