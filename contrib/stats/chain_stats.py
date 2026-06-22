#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Emission, dev, and coinbase layout statistics for Zero mainnet.
#
# Usage (from repo root; src/zerod synced for RPC modes):
#   ./contrib/stats/chain_stats.py --cons
#   ./contrib/stats/chain_stats.py --cons --thru 2400000
#   ./contrib/stats/chain_stats.py --cons --dev
#   ./contrib/stats/chain_stats.py --verify
#   ./contrib/stats/chain_stats.py --scan 2471200 200

from __future__ import print_function

import argparse
import json
import os
import subprocess
import sys

COIN = 100_000_000
FEE_START = 412_300
DEV_END = 7_999_999
HALVING_INTERVAL = 800_000
HALVING_4_START = 3_200_000
AMT_WIDTH = 16

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
DEFAULT_CLI = os.path.join(_REPO_ROOT, "src", "zero-cli")

DEV_ADDRS = [
    "t3hmg6WApjqVFw9oPWTDy4JLEqXcUWthg5v",
    "t3hrh5M7eaGA5zXCitPXz2pbe146GkVPWHs",
    "t3aWmHqBGS7watoKQLa7uykeTaYHoYqM361",
    "t3hsi89hPsZzmnbs3pny6cfAxMxV5TJLErj",
    "t3TdGxPVUdMXd6qDrDCEuJETLadZ9Ki3s9r",
    "t3cb5ZjKmbGbqDaYk97Auam9kXXikGQBmyY",
    "t3V1YovGUPW9WSBoAHS48FDdUfUTo6LDpZR",
    "t3KB9n28MVg31oo856t1tQGfJuYq8usTvSi",
    "t3dqSV4YGj5V3WjQhqFGrKTMUf9Tgc6xnJM",
    "t3aJkYT1i6tyytq8J6khPaDNtgZsBSXgfBf",
]

ERA_RANGES = [
    (0, 412_299, "10.0 start"),
    (412_300, 799_999, "10.8 bump"),
    (800_000, 1_599_999, "5.4 halving 1"),
    (1_600_000, 2_399_999, "2.7 halving 2"),
    (2_400_000, 3_199_999, "1.35 halving 3"),
    (3_200_000, None, "0.675 halving 4"),
]


def subsidy_zat(height):
    base = int(10.8 * COIN) if height >= FEE_START else 10 * COIN
    halvings = height // HALVING_INTERVAL
    if halvings >= 64:
        return 0
    return base >> halvings


def dev_zat(height):
    if height < FEE_START or height > DEV_END:
        return 0
    return int(subsidy_zat(height) * 0.075)


def nodes_pct(height):
    if height < HALVING_INTERVAL:
        return 20
    if height < HALVING_INTERVAL * 2:
        return 25
    if height < HALVING_INTERVAL * 3:
        return 30
    if height < HALVING_INTERVAL * 4:
        return 35
    return 40


def nodes_zat(height):
    return subsidy_zat(height) * nodes_pct(height) // 100


def miner_zat(height):
    s = subsidy_zat(height)
    return s - dev_zat(height) - nodes_zat(height)


def zat_to_zer(zat):
    return zat / float(COIN)


def fmt_zer(zat, width=AMT_WIDTH):
    return "{:>{w},.2f}".format(zat_to_zer(zat), w=width)


def fmt_zer_float(zer, width=AMT_WIDTH):
    return "{:>{w},.2f}".format(zer, w=width)


def print_split_table(total_sub, total_miner, total_nodes, total_dev):
    for label, zat in (
        ("Total", total_sub),
        ("Miner", total_miner),
        ("Nodes", total_nodes),
        ("Dev", total_dev),
    ):
        print("{:<6}{} ZER".format(label + ":", fmt_zer(zat)))


def dev_deposited_by_addr(through):
    by_addr = {a: 0 for a in DEV_ADDRS}
    for h in range(FEE_START, min(through, DEV_END) + 1):
        idx = h // HALVING_INTERVAL
        if idx >= len(DEV_ADDRS):
            break
        by_addr[DEV_ADDRS[idx]] += dev_zat(h)
    return by_addr


def emission_report(through, show_dev=False, cli=None):
    total_sub = sum(subsidy_zat(h) for h in range(0, through + 1))
    total_dev = sum(dev_zat(h) for h in range(0, through + 1))
    total_nodes = sum(nodes_zat(h) for h in range(0, through + 1))
    total_miner = sum(miner_zat(h) for h in range(0, through + 1))

    print("=== Zero emission model (consensus) ===")
    print("Through height: {:,}".format(through))
    print()
    print_split_table(total_sub, total_miner, total_nodes, total_dev)

    if show_dev:
        if through >= HALVING_4_START:
            sub_h4 = sum(subsidy_zat(h) for h in range(0, HALVING_4_START + 1))
            dev_h4 = sum(dev_zat(h) for h in range(0, HALVING_4_START + 1))
            nodes_h4 = sum(nodes_zat(h) for h in range(0, HALVING_4_START + 1))
            miner_h4 = sum(miner_zat(h) for h in range(0, HALVING_4_START + 1))

            print()
            print("--- Total by end of halving 4 (height {:,} inclusive) ---".format(
                HALVING_4_START))
            print_split_table(sub_h4, miner_h4, nodes_h4, dev_h4)

        print()
        print("--- Subsidy by halving era (inclusive ranges) ---")
        for lo, hi_fixed, label in ERA_RANGES:
            hi = through if hi_fixed is None else min(hi_fixed, through)
            if lo > through:
                continue
            if hi < lo:
                continue
            n = hi - lo + 1
            sub = sum(subsidy_zat(h) for h in range(lo, hi + 1))
            print("  heights {:>7,}-{:>7,}  blocks {:>7,}  {:>16} ZER  ({})".format(
                lo, hi, n, fmt_zer(sub).strip(), label))

        by_addr = dev_deposited_by_addr(through)
        print()
        print("--- Dev addresses through {:,} ---".format(through))
        print("  idx  deposited       balance  address")
        insight_ok = True
        for i, addr in enumerate(DEV_ADDRS):
            deposited = fmt_zer(by_addr[addr]).strip()
            balance = "n/a"
            if cli:
                try:
                    payload = json.dumps({"addresses": [addr]})
                    resp = rpc(cli, "getaddressbalance", payload)
                    balance = fmt_zer(int(resp["balance"])).strip()
                except subprocess.CalledProcessError:
                    insight_ok = False
            print("  [{:>1}]  {:>16}  {:>16}  {}".format(
                i, deposited, balance, addr))
        if cli and not insight_ok:
            print()
            print("On-chain balance requires zerod with -experimentalfeatures "
                  "-insightexplorer (getaddressbalance).")

        if through >= DEV_END:
            grand = sum(subsidy_zat(h) for h in range(0, DEV_END + 1))
            print()
            print("Grand subsidy through dev end ({:,}): {} ZER".format(
                DEV_END, fmt_zer(grand)))


def rpc(cli, *args):
    cmd = [cli] + list(args)
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    text = out.decode("utf-8").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text.strip('"')


def resolve_through(cli, thru_arg):
    if thru_arg is not None:
        return thru_arg
    try:
        info = rpc(cli, "getblockchaininfo")
        return info["blocks"]
    except (subprocess.CalledProcessError, OSError) as e:
        print("warning: could not read chain tip ({}); using height {:,}".format(
            e, HALVING_4_START), file=sys.stderr)
        return HALVING_4_START


def scan_coinbases(cli, start, count):
    hist = {}
    dual_miner = {}
    dev_recv = {a: 0.0 for a in DEV_ADDRS}
    for h in range(start, start + count):
        try:
            bh = rpc(cli, "getblockhash", str(h))
            block = rpc(cli, "getblock", bh, "2")
        except subprocess.CalledProcessError as e:
            print("RPC error height {}: {}".format(h, e), file=sys.stderr)
            continue
        cb = block["tx"][0]
        nv = len(cb["vout"])
        hist[nv] = hist.get(nv, 0) + 1
        t_addrs = []
        for v in cb["vout"]:
            spk = v.get("scriptPubKey", {})
            addrs = spk.get("addresses") or []
            val = v["value"]
            if addrs:
                a = addrs[0]
                if a in dev_recv:
                    dev_recv[a] += val
                if spk.get("type") == "pubkeyhash":
                    t_addrs.append((a, val))
        if nv == 4 and len(t_addrs) >= 2:
            pair = tuple(sorted(t_addrs[-2:]))
            dual_miner[pair] = dual_miner.get(pair, 0) + 1

    print("=== Coinbase scan heights {:,}-{:,} ===".format(start, start + count - 1))
    print("vout count histogram:", dict(sorted(hist.items())))
    print()
    print("Top dual-miner t-address pairs (4-vout blocks, last 2 P2PKH):")
    for pair, n in sorted(dual_miner.items(), key=lambda x: -x[1])[:10]:
        print("  {}x  {} {:.2f} + {} {:.2f}".format(
            n, pair[0][0], pair[0][1], pair[1][0], pair[1][1]))
    print()
    print("Dev addresses seen in sample (value sum):")
    for a in DEV_ADDRS:
        if dev_recv[a] > 0:
            print("  {} ZER  {}".format(fmt_zer_float(dev_recv[a]), a))


def verify_tip(cli):
    info = rpc(cli, "getblockchaininfo")
    tip = info["blocks"]
    print("Chain tip height: {:,}".format(tip))
    if "valuePools" in info:
        for pool in info["valuePools"]:
            print("  pool {} chainValue {:.2f}".format(
                pool.get("id", "?"), pool.get("chainValue", 0)))
    expected = sum(subsidy_zat(h) for h in range(0, tip + 1))
    print("Model subsidy sum to tip: {} ZER".format(fmt_zer(expected)))
    print("(On-chain total supply includes fees; compare with gettxoutsetinfo if txindex enabled)")


def main():
    epilog = """
Examples (run from repo root; src/zerod must be running for RPC modes):
  %(prog)s --cons
  %(prog)s --cons --thru 2400000
  %(prog)s --cons --dev
  %(prog)s --verify
  %(prog)s --scan 2471200 200

Default CLI: {cli}
""".format(cli=DEFAULT_CLI)
    p = argparse.ArgumentParser(
        description="Zero chain emission and coinbase statistics.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)
    p.add_argument(
        "--cons", action="store_true",
        help="Print consensus emission report from the subsidy model "
             "(default when neither --verify nor --scan is given).")
    p.add_argument(
        "--thru", type=int, nargs="?", const=-1, default=-1, metavar="HEIGHT",
        help="Cumulative through chain tip (default). "
             "Use --thru HEIGHT for a fixed height inclusive.")
    p.add_argument(
        "--dev", action="store_true",
        help="Halving-era breakdown, end-of-halving-4 totals, dev address "
             "deposited/balance (requires RPC; getaddressbalance needs "
             "-experimentalfeatures -insightexplorer). Default: off.")
    p.add_argument(
        "--cli", default=DEFAULT_CLI, metavar="PATH",
        help="Path to zero-cli for RPC modes "
             "(default: %(default)s).")
    p.add_argument(
        "--verify", action="store_true",
        help="Compare model subsidy sum to live chain tip via getblockchaininfo.")
    p.add_argument(
        "--scan", nargs=2, type=int, metavar=("START", "COUNT"),
        help="Scan coinbase vout layout over START .. START+COUNT-1 via RPC.")
    args = p.parse_args()

    run_cons = args.cons or (not args.verify and not args.scan)
    if run_cons:
        if args.thru == -1:
            through = resolve_through(args.cli, None)
        else:
            through = args.thru
        emission_report(through, show_dev=args.dev, cli=args.cli if args.dev else None)
    if args.verify:
        verify_tip(args.cli)
    if args.scan:
        scan_coinbases(args.cli, args.scan[0], args.scan[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
