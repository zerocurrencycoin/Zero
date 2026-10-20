#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Shared helpers for the chain-audit scripts: batched JSON-RPC to a local zerod, subsidy schedule, known addresses."""
import base64, json, os, platform, urllib.request

COIN = 10**8
HALVING = 800000
FEE_START = 412300


def conf_path():
    if os.environ.get("ZERO_CONF"):
        return os.environ["ZERO_CONF"]
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Application Support/zero/zero.conf")
    return os.path.expanduser("~/.zero/zero.conf")


def _conf():
    cfg = {}
    for line in open(conf_path()):
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


_CFG = None


def batch(calls, timeout=900):
    """Run [(method, params), ...] in one JSON-RPC batch; return results in order."""
    global _CFG
    if not calls:
        return []
    if _CFG is None:
        _CFG = _conf()
    url = "http://127.0.0.1:%s/" % _CFG.get("rpcport", "23811")
    auth = base64.b64encode(("%s:%s" % (_CFG["rpcuser"], _CFG["rpcpassword"])).encode()).decode()
    body = json.dumps([{"jsonrpc": "1.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]).encode()
    req = urllib.request.Request(url, body, {"Authorization": "Basic " + auth, "Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req, timeout=timeout))
    res.sort(key=lambda r: r["id"])
    for r in res:
        if r.get("error"):
            raise RuntimeError(r["error"])
    return [r["result"] for r in res]


def subsidy(h):
    """GetBlockSubsidy in zatoshis (mainnet, Blossom not active)."""
    s = 10 * COIN if h < FEE_START else 108 * COIN // 10
    hv = h // HALVING
    return 0 if hv >= 64 else s >> hv


def zeronode_tier(h):
    """Zeronode share in percent with sporks 6 and 7 active (GetZeronodePayment)."""
    return [20, 25, 30, 35, 40][min(h // HALVING, 4)]


DEV_FEE_ADDRESSES = {
    "t3hmg6WApjqVFw9oPWTDy4JLEqXcUWthg5v", "t3hrh5M7eaGA5zXCitPXz2pbe146GkVPWHs", "t3aWmHqBGS7watoKQLa7uykeTaYHoYqM361",
    "t3hsi89hPsZzmnbs3pny6cfAxMxV5TJLErj", "t3TdGxPVUdMXd6qDrDCEuJETLadZ9Ki3s9r", "t3cb5ZjKmbGbqDaYk97Auam9kXXikGQBmyY",
    "t3V1YovGUPW9WSBoAHS48FDdUfUTo6LDpZR", "t3KB9n28MVg31oo856t1tQGfJuYq8usTvSi", "t3dqSV4YGj5V3WjQhqFGrKTMUf9Tgc6xnJM",
    "t3aJkYT1i6tyytq8J6khPaDNtgZsBSXgfBf"}

# Payout addresses matched to pools (doc/mining-pools.md "Identities"); unmatched ones keep their address.
POOL_NAMES = {
    "t1aZet5eQegFmDgMiCpfwdZoeJ7geukENG1": "Mining-Dutch",
    "t1MRBMDxW5QTbMteKprtjExPwWZuyitZ13o": "zpool.ca",
    "t1hASctRxWKg5R3Drs4jqoGVjUpszCaJVaR": "ZeroPool.io",
    "t1ZJYNnzoR7C2BxDcxEmq3vBV1fqfBRZS8a": "solo.zeropool.io",
    "t1SJJornJ9nibZKVbVZDCGx7EaHFxPxTbu7": "s-nomp t1SJJ",
    "t1e6nAkZLoXUgwRuJ9qj2CF15qkroWVsVVQ": "s-nomp t1e6n",
    "t1NrRjwieswXAafgphJdptLPEF1Hz3hKXoo": "s-nomp t1NrRj",
    "t1PmYqmnSY4Gc4jngiSRCPsqtSQKocjvSuP": "s-nomp t1PmYq",
    "t1fbDZDZX45uRPaAT42Kb2DLUJAvb7fN9fX": "untagged t1fbD",
}
ZEROPOOL_FEE = "t1WYX21GNdbbvFdbdVBd4ymzuZbmAEKmKaG"


def parse_outputs(field):
    """'addr:zat;addr:zat' from coinbase_scan.py -> [(addr, zat)]."""
    return [(a, int(z)) for a, z in (x.rsplit(":", 1) for x in field.split(";"))]


def miner_outputs(h, outs):
    """Coinbase outputs without the development fee and the zeronode output (the one paying the tier amount)."""
    rest = [x for x in outs if x[0] not in DEV_FEE_ADDRESSES]
    zn = subsidy(h) * zeronode_tier(h) // 100
    for i, (a, z) in enumerate(rest):
        if z == zn and len(rest) > 1:
            rest.pop(i)
            break
    return rest


def pool_of(h, outs):
    """Pool name, or the largest miner output address when unmatched."""
    rest = miner_outputs(h, outs)
    if not rest:
        return "?"
    addrs = {a for a, _ in rest}
    for a in addrs:
        if a in POOL_NAMES:
            return POOL_NAMES[a]
    if ZEROPOOL_FEE in addrs:
        return "ZeroPool.io (other payout)"
    return max(rest, key=lambda x: x[1])[0]
