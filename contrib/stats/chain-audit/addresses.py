#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Group zeronode, peer, and listed addresses by IP version and subnet, and report overlaps.

Usage:
  addresses.py [--no-node] [--peers LABEL=FILE]... [--zeronodes FILE] [--list LABEL=FILE]... [--min N]

Sets:
  zeronodes     `listzeronodes` of the local node, or --zeronodes FILE (saved `listzeronodes` JSON)
  peers         `getpeerinfo` of the local node, plus each --peers LABEL=FILE (saved `getpeerinfo` JSON
                from another node)
  LABEL         each --list LABEL=FILE: any text; every IPv4 address and bracketed IPv6 address in it

Reports: set sizes by IP version; overlaps between sets; subnets holding N or more members of a set
(IPv4 /16 and /24, IPv6 /32 and /48; default N 2); addresses with several connections to one node,
with versions and directions; zeronode payout addresses shared by several zeronodes; peer versions.
--no-node skips RPC and uses only the files.
"""
import argparse, collections, ipaddress, json, re

from audit_rpc import batch


def host(a):
    """Strip the port: '1.2.3.4:23801' -> '1.2.3.4', '[2a02::1]:23801' -> '2a02::1'."""
    a = a.strip()
    if a.startswith("["):
        return a[1:a.index("]")]
    if a.count(":") == 1:
        return a.rsplit(":", 1)[0]
    return a


def nets(ip):
    """(version, wide subnet, narrow subnet): IPv4 /16 and /24, IPv6 /32 and /48."""
    v = ipaddress.ip_address(ip).version
    wide, narrow = (16, 24) if v == 4 else (32, 48)
    return (v, str(ipaddress.ip_network(f"{ip}/{wide}", strict=False)),
            str(ipaddress.ip_network(f"{ip}/{narrow}", strict=False)))


def load_json(path):
    """First JSON value in the file; text after it (a shell prompt, a second command) is ignored."""
    return json.JSONDecoder().raw_decode(open(path).read().lstrip())[0]


def addresses_in(path):
    out = set()
    for m in re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b|\[([0-9a-fA-F:]+)\]", open(path).read()):
        try:
            out.add(str(ipaddress.ip_address(m[0] or m[1])))
        except ValueError:
            pass
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-node", action="store_true")
    ap.add_argument("--peers", action="append", default=[], metavar="LABEL=FILE")
    ap.add_argument("--zeronodes", metavar="FILE")
    ap.add_argument("--list", action="append", default=[], metavar="LABEL=FILE")
    ap.add_argument("--min", type=int, default=2)
    a = ap.parse_args()

    zn, peers = [], {}
    if not a.no_node:
        zn_rpc, local = batch([("listzeronodes", []), ("getpeerinfo", [])])
        zn = zn_rpc if not a.zeronodes else zn
        peers["peers local"] = local
    if a.zeronodes:
        zn = load_json(a.zeronodes)
    for spec in a.peers:
        label, path = spec.split("=", 1)
        peers["peers " + label] = load_json(path)

    sets = {}
    if zn:
        sets["zeronodes"] = {host(z["ip"]) for z in zn if z.get("ip")}
    for label, p in peers.items():
        sets[label] = {host(x["addr"]) for x in p}
    for spec in a.list:
        label, path = spec.split("=", 1)
        sets[label] = addresses_in(path)

    print("Sets:")
    for k, v in sets.items():
        c = collections.Counter(nets(i)[0] for i in v)
        print(f"  {k:<20} {len(v):>5}   IPv4 {c[4]:>5}   IPv6 {c[6]:>5}")

    names = list(sets)
    print("Overlaps:")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            print(f"  {names[i]} & {names[j]}: {len(sets[names[i]] & sets[names[j]])}")

    print(f"Subnets with {a.min} or more members:")
    for k, v in sets.items():
        for pos, label in ((1, "IPv4 /16, IPv6 /32"), (2, "IPv4 /24, IPv6 /48")):
            g = collections.Counter(nets(i)[pos] for i in v)
            big = [(n, c) for n, c in g.most_common() if c >= a.min]
            if big:
                print(f"  {k}, {label}: " + ", ".join(f"{n} {c}" for n, c in big))

    print("Addresses with several connections to one node:")
    for label, p in peers.items():
        by = collections.defaultdict(list)
        for x in p:
            by[host(x["addr"])].append(x)
        for ip, xs in sorted(by.items(), key=lambda t: -len(t[1])):
            if len(xs) < 2:
                break
            vers = collections.Counter(x.get("subver", "") for x in xs)
            inbound = sum(1 for x in xs if x.get("inbound"))
            scores = sorted((x.get("banscore", 0) for x in xs), reverse=True)[:3]
            print(f"  {label}: {ip} {len(xs)} connections, {inbound} inbound, {dict(vers)}, top ban scores {scores}")

    if zn:
        payees = collections.Counter(z.get("addr") for z in zn)
        shared = [(p, n) for p, n in payees.most_common() if n > 1]
        print(f"Zeronode payout addresses: {len(payees)} for {len(zn)} zeronodes; shared: {shared or 'none'}")
        print("Zeronode versions:", dict(collections.Counter(z.get("version") for z in zn)),
              "status:", dict(collections.Counter(z.get("status") for z in zn)))
    for label, p in peers.items():
        print(f"{label}: {sum(1 for x in p if x.get('inbound'))} inbound, {sum(1 for x in p if not x.get('inbound'))} outbound;",
              "versions:", collections.Counter(x.get("subver", "") for x in p).most_common(6))


if __name__ == "__main__":
    main()
