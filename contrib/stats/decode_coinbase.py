#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Decode coinbase outputs for subsidy / dev / nodes analysis.
#
# Usage (from repo root; src/zerod must be synced):
#   ./contrib/stats/decode_coinbase.py --start 2400000 --count 10
#   ./contrib/stats/decode_coinbase.py --heights 412300,800000,2400000
#   ./contrib/stats/decode_coinbase.py --start 2471200 --count 200 --summary

from __future__ import print_function

import argparse
import json
import os
import subprocess
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", ".."))
DEFAULT_CLI = os.path.join(_REPO_ROOT, "src", "zero-cli")


def rpc(cli, *args):
    cmd = [cli] + list(args)
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    text = out.decode("utf-8").strip()
    if not text:
        raise ValueError("empty RPC response: {}".format(cmd))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text.strip('"')


def decode_block(cli, height):
    block_hash = rpc(cli, "getblockhash", str(height))
    block = rpc(cli, "getblock", block_hash, "2")
    cb = block["tx"][0]
    rows = []
    for i, vout in enumerate(cb["vout"]):
        spk = vout.get("scriptPubKey", {})
        addrs = spk.get("addresses") or []
        rows.append({
            "index": i,
            "value": vout["value"],
            "type": spk.get("type", "?"),
            "address": addrs[0] if addrs else "",
            "script_hex": spk.get("hex", ""),
        })
    return {
        "height": height,
        "hash": block["hash"],
        "coinbase_txid": cb["txid"],
        "vout_count": len(rows),
        "total": sum(r["value"] for r in rows),
        "vouts": rows,
    }


def main():
    epilog = """
Examples (run from repo root):
  %(prog)s --start 2400000 --count 10
  %(prog)s --heights 412300,800000,2400000
  %(prog)s --start 2471200 --count 200 --summary
  %(prog)s --json --heights 2400000

If neither --heights nor --start is given, decodes the current chain tip.
Default CLI: {cli}
""".format(cli=DEFAULT_CLI)
    p = argparse.ArgumentParser(
        description="Decode Zero coinbase outputs over a height range.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)
    p.add_argument(
        "--cli", default=DEFAULT_CLI, metavar="PATH",
        help="Path to zero-cli (default: %(default)s).")
    p.add_argument(
        "--start", type=int, metavar="HEIGHT",
        help="First block height (use with --count).")
    p.add_argument(
        "--count", type=int, default=1, metavar="N",
        help="Number of consecutive blocks from --start "
             "(default: %(default)s). Ignored when --heights is set.")
    p.add_argument(
        "--heights", metavar="H1,H2,...",
        help="Comma-separated block heights; overrides --start and --count.")
    p.add_argument(
        "--summary", action="store_true",
        help="Print only the vout-count histogram (no per-block detail).")
    p.add_argument(
        "--json", action="store_true",
        help="Emit one JSON object per line (full decode structure).")
    args = p.parse_args()

    if args.heights:
        heights = [int(x.strip()) for x in args.heights.split(",") if x.strip()]
    elif args.start is not None:
        heights = list(range(args.start, args.start + args.count))
    else:
        tip = rpc(args.cli, "getblockchaininfo")["blocks"]
        heights = [tip]

    results = []
    hist = {}
    for h in heights:
        try:
            r = decode_block(args.cli, h)
        except subprocess.CalledProcessError as e:
            print("error height {}: {}".format(h, e), file=sys.stderr)
            continue
        results.append(r)
        hist[r["vout_count"]] = hist.get(r["vout_count"], 0) + 1

    if args.summary:
        print("heights scanned:", len(results))
        print("vout histogram:", dict(sorted(hist.items())))
        return 0

    if args.json:
        for r in results:
            print(json.dumps(r))
        return 0

    for r in results:
        print("height {:,} vouts {} total {:.2f} txid {}...".format(
            r["height"], r["vout_count"], r["total"], r["coinbase_txid"][:16]))
        for v in r["vouts"]:
            print("  [{}] {:>12,.2f} {} {}".format(
                v["index"], v["value"], v["type"], v["address"]))
        print()
    if len(results) > 1:
        print("vout histogram:", dict(sorted(hist.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
