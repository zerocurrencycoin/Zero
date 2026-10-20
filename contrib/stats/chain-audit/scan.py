#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Scan mainnet blocks from a synced local zerod into TSV files for analyze.py.

  scan.py coinbase START END OUT   height, subsidy, coinbase total, tx count, outputs (addr:zat;...)
  scan.py times    START END OUT   height, time, tx count
  scan.py fees     HEIGHTS OUT     height, subsidy, coinbase total, fees, tx count, for heights listed in file HEIGHTS

Output is appended, so an interrupted range resumes from the last height written. Batches of
--step blocks (default 250; lower it when blocks are large: the RPC response of one batch
must fit in memory).
"""
import argparse, sys
from audit_rpc import COIN, batch, subsidy

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("mode", choices=["coinbase", "times", "fees"])
ap.add_argument("args", nargs="+")
ap.add_argument("--step", type=int, default=250)
a = ap.parse_args()


def z(v):
    return round(v * COIN)


def blocks(hs):
    return batch([("getblock", [x, 2]) for x in batch([("getblockhash", [h]) for h in hs])])


if a.mode in ("coinbase", "times"):
    start, end, out = int(a.args[0]), int(a.args[1]), a.args[2]
    with open(out, "a") as f:
        for lo in range(start, end + 1, a.step):
            hs = list(range(lo, min(end, lo + a.step - 1) + 1))
            for h, b in zip(hs, blocks(hs)):
                if a.mode == "times":
                    f.write("%d\t%d\t%d\n" % (h, b["time"], len(b["tx"])))
                    continue
                cb = b["tx"][0]
                outs, tot = [], 0
                for v in cb["vout"]:
                    tot += z(v["value"])
                    addr = (v["scriptPubKey"].get("addresses") or [v["scriptPubKey"].get("type", "?")])[0]
                    outs.append("%s:%d" % (addr, z(v["value"])))
                f.write("%d\t%d\t%d\t%d\t%s\n" % (h, subsidy(h), tot, len(b["tx"]), ";".join(outs)))
            f.flush()
    sys.exit(0)

# fees: getblock omits vjoinsplit for version-2 transactions, so every transaction is read with getrawtransaction
heights = [int(x) for x in open(a.args[0]).read().split()]
step = min(a.step, 100)
with open(a.args[1], "a") as f:
    for i in range(0, len(heights), step):
        hs = heights[i:i + step]
        bl = blocks(hs)
        tids = [t["txid"] for b in bl for t in b["tx"][1:]]
        full = {}
        for j in range(0, len(tids), 500):
            for t in batch([("getrawtransaction", [x, 1]) for x in tids[j:j + 500]]):
                full[t["txid"]] = t
        prev = {vin["txid"]: None for t in full.values() for vin in t["vin"]}
        ids = list(prev)
        for j in range(0, len(ids), 500):
            for t in batch([("getrawtransaction", [x, 1]) for x in ids[j:j + 500]]):
                prev[t["txid"]] = [z(v["value"]) for v in t["vout"]]
        for h, b in zip(hs, bl):
            cb = sum(z(v["value"]) for v in b["tx"][0]["vout"])
            fees = 0
            for tx in (full[t["txid"]] for t in b["tx"][1:]):
                tin = sum(prev[v["txid"]][v["vout"]] for v in tx["vin"])
                tout = sum(z(v["value"]) for v in tx["vout"])
                js = sum(z(j.get("vpub_new", 0)) - z(j.get("vpub_old", 0)) for j in tx.get("vjoinsplit", []))
                fees += tin - tout + z(tx.get("valueBalance", 0)) + js
            f.write("%d\t%d\t%d\t%d\t%d\n" % (h, subsidy(h), cb, fees, len(b["tx"])))
        f.flush()
