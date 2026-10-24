#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Reports behind doc/mining/mining-pools.md, from the TSV files of scan.py (and RPC for forks, tags, expiry).

  analyze.py underclaim COINBASE                      under-claimed coinbases by payout address and height range
  analyze.py candidates COINBASE OUT                  heights for "scan.py fees": blocks with transactions claiming <= subsidy
  analyze.py fees       FEES COINBASE GAP_ZER         split the measured supply gap into subsidy, fees, remainder
  analyze.py setups     COINBASE [FROM]               payout setups: blocks, outputs, splits, empty share (default FROM 2400000)
  analyze.py eras       COINBASE TIMES OUT.csv [FORKS.json]   per pool and era (split at 2400000): empty, intervals, bursts, runs
  analyze.py bands      COINBASE TIMES [FROM]         empty share by interval since the previous block, per pool
  analyze.py bursts     COINBASE TIMES                runs of 10+ blocks from one pool at under 60 s average; longest runs
  analyze.py timestamps COINBASE TIMES [FROM]         timestamps earlier than the previous block, near median-time-past
  analyze.py arrival    COINBASE FROM LOG...          arrival (debug.log UpdateTip, UTC) minus block time; batched arrivals
  analyze.py forks      OUT.json                      stale branches from getchaintips with the pool of each stale and replacing block
  analyze.py tags       HEIGHT...                     printable text in the coinbase input
  analyze.py expiry     TIMES [SAMPLE]                expiry and locktime of sampled transactions per era
"""
import collections, csv, datetime, gzip, json, random, re, statistics, sys
from audit_rpc import COIN, batch, parse_outputs, pool_of, miner_outputs

H3 = 2400000


def coinbase(path, frm=0):
    for line in open(path):
        h, s, t, ntx, outs = line.rstrip("\n").split("\t")
        h = int(h)
        if h >= frm:
            yield h, int(s), int(t), int(ntx), parse_outputs(outs)


def times(path):
    T = {}
    for line in open(path):
        f = line.split()
        T[int(f[0])] = (int(f[1]), int(f[2]))
    return T


def pools(path, frm=0):
    return {h: pool_of(h, o) for h, s, t, n, o in coinbase(path, frm)}


def era(h):
    return "post-2400000" if h >= H3 else "pre-2400000"


def runs_of(P, T):
    out, prev, start = [], None, None
    for h in sorted(P):
        if P[h] != prev:
            if prev is not None:
                out.append((start, last, prev))
            prev, start = P[h], h
        last = h
    out.append((start, last, prev))
    return out


cmd, args = sys.argv[1], sys.argv[2:]

if cmd == "underclaim":
    by = collections.defaultdict(lambda: [0, 0, None, None, collections.Counter()]); rng = collections.Counter(); n = U = 0
    for h, s, t, ntx, o in coinbase(args[0]):
        if t < s:
            p = pool_of(h, o); b = by[p]; b[0] += 1; b[1] += s - t; b[2] = b[2] or h; b[3] = h
            b[4][round((s - t) * 1000 / s, 3)] += 1; rng[h // 100000 * 100000] += s - t; n += 1; U += s - t
    print(f"under-claimed blocks {n}, subsidy not claimed {U / COIN:.8f} ZER")
    for p, b in sorted(by.items(), key=lambda kv: -kv[1][1]):
        print(f"{p:<36} {b[0]:>7} blocks {b[1] / COIN:>10.3f} ZER heights {b[2]}-{b[3]} per mille {dict(b[4].most_common(3))}")
    print("by 100k heights:", {k: round(v / COIN, 3) for k, v in sorted(rng.items())})

elif cmd == "candidates":
    with open(args[1], "w") as f:
        for h, s, t, ntx, o in coinbase(args[0]):
            if ntx > 1 and t <= s:
                f.write("%d\n" % h)

elif cmd == "fees":
    gap = float(args[2]); U = F_u = F_o = 0
    for line in open(args[0]):
        h, s, cb, f, n = map(int, line.split())
        if cb < s:
            F_u += f
        elif s + f - cb > 0:
            F_o += s + f - cb
    for h, s, t, ntx, o in coinbase(args[1]):
        if t < s:
            U += s - t
    tot = (U + F_u + F_o) / COIN
    print(f"unclaimed subsidy {U / COIN:.8f}, fees in those blocks {F_u / COIN:.8f}, other unclaimed fees {F_o / COIN:.8f}")
    print(f"explained {tot:.8f} of gap {gap:.8f}; remainder {gap - tot:.8f}")

elif cmd == "setups":
    frm = int(args[1]) if len(args) > 1 else H3; tot = 0
    st = collections.defaultdict(lambda: {"n": 0, "lo": None, "hi": None, "outs": collections.Counter(), "split": collections.Counter(), "empty": 0, "under": 0})
    for h, s, t, ntx, o in coinbase(args[0], frm):
        tot += 1; rest = miner_outputs(h, o); k = " + ".join(sorted({a for a, _ in rest})); d = st[k]
        d["n"] += 1; d["lo"] = d["lo"] or h; d["hi"] = h; d["outs"][len(o)] += 1; d["empty"] += ntx == 1; d["under"] += t < s
        if len(rest) > 1:
            T_ = sum(z for _, z in rest); d["split"]["/".join(str(round(z / T_ * 100, 1)) for _, z in sorted(rest, key=lambda x: -x[1]))] += 1
    for k, d in sorted(st.items(), key=lambda kv: -kv[1]["n"]):
        if d["n"] >= 200:
            print(f"{k[:80]:<80} {d['n'] / tot * 100:6.2f}% {d['lo']}-{d['hi']} outputs {dict(d['outs'])} split {dict(d['split'].most_common(1))} empty {d['empty'] / d['n'] * 100:.1f}% under {d['under']}")
    print(f"blocks {tot}; setups {len(st)}")

elif cmd in ("eras", "bands", "bursts", "timestamps"):
    frm = int(args[2]) if cmd in ("bands", "timestamps") and len(args) > 2 else (H3 if cmd in ("bands", "timestamps") else 0)
    P = pools(args[0]); T = times(args[1]); H = max(T)
    if cmd == "bands":
        B = [(0, 30), (30, 120), (120, 300), (300, 10**9)]; S = collections.defaultdict(lambda: [[0, 0] for _ in B])
        for h in range(max(frm, 2), H + 1):
            iv = T[h][0] - T[h - 1][0]; e = T[h][1] == 1
            for i, (lo, hi) in enumerate(B):
                if lo <= iv < hi:
                    for k in (P[h], "ALL"):
                        S[k][i][0] += 1; S[k][i][1] += e
        print("empty share by interval [<30 s | 30-120 s | 120-300 s | >=300 s]")
        for k, v in sorted(S.items(), key=lambda kv: -sum(x[0] for x in kv[1]))[:12]:
            print(f"{k[:24]:<24}", " | ".join(f"{b[1] / b[0] * 100:5.1f}% ({b[0]})" if b[0] else "-" for b in v))
    elif cmd == "bursts":
        R = runs_of(P, T); burst = collections.defaultdict(lambda: [0, 0, 0])
        for a, b, p in R:
            if b - a + 1 >= 10 and (T[b][0] - T[a][0]) / (b - a) < 60:
                x = burst[(era(a), p)]; x[0] += 1; x[1] += b - a + 1; x[2] += sum(1 for y in range(a, b + 1) if T[y][1] == 1)
        for k, v in sorted(burst.items(), key=lambda kv: (kv[0][0], -kv[1][1]))[:20]:
            print(k, "bursts", v[0], "blocks", v[1], "empty %.0f%%" % (v[2] / v[1] * 100))
        for a, b, p in sorted(R, key=lambda r: -(r[1] - r[0]))[:8]:
            L = b - a + 1
            print(f"run {L} {a}-{b} {datetime.datetime.fromtimestamp(T[a][0], datetime.UTC).date()} {p} avg {(T[b][0] - T[a][0]) / max(L - 1, 1):.0f} s")
    elif cmd == "timestamps":
        S = collections.defaultdict(lambda: [0, 0, 0, []])
        for h in range(max(frm, 12), H + 1):
            mtp = sorted(T[h - i][0] for i in range(1, 12))[5]; d = S[P[h]]
            d[0] += 1; d[1] += T[h][0] < T[h - 1][0]; d[2] += T[h][0] - mtp <= 30; d[3].append(T[h][0] - mtp)
        for p, d in sorted(S.items(), key=lambda kv: -kv[1][0])[:10]:
            print(f"{p[:24]:<24} {d[0]:>7} earlier-than-previous {d[1] / d[0] * 100:5.1f}% within-30s-of-MTP {d[2] / d[0] * 100:5.1f}% median ts-MTP {statistics.median(d[3]):.0f} s")
    else:  # eras
        stale = collections.Counter()
        if len(args) > 3:
            for r in json.load(open(args[3])):
                for p in r["stale_pools"]:
                    stale[p] += 1
        burst = collections.Counter()
        for a, b, p in runs_of(P, T):
            if b - a + 1 >= 10 and (T[b][0] - T[a][0]) / (b - a) < 60:
                burst[(era(a), p)] += b - a + 1
        S = collections.defaultdict(lambda: {"n": 0, "e": 0, "ie": [], "ine": [], "q": 0, "late": 0})
        tot = collections.Counter()
        for h in range(2, H + 1):
            e, iv, empty = era(h), T[h][0] - T[h - 1][0], T[h][1] == 1
            tot[e] += 1
            for k in ((e, P[h]), (e, "TOTAL")):
                d = S[k]; d["n"] += 1
                if empty:
                    d["e"] += 1; d["ie"].append(iv); d["q"] += iv < 30; d["late"] += iv >= 120
                else:
                    d["ine"].append(iv)
        maxrun = collections.Counter(); runs3 = collections.Counter()
        for a, b, p in runs_of(P, T):
            k = (era(a), p); maxrun[k] = max(maxrun[k], b - a + 1); runs3[k] += b - a + 1 >= 3
        med = lambda v: int(statistics.median(v)) if v else ""
        rows = []
        for (e, p), d in S.items():
            if p != "TOTAL" and d["n"] < 2000:
                continue
            rows.append({"era": e, "pool": p, "blocks": d["n"], "share_pct": round(d["n"] / tot[e] * 100, 2),
                         "empty_blocks": d["e"], "empty_pct": round(d["e"] / d["n"] * 100, 1),
                         "median_interval_empty_s": med(d["ie"]), "median_interval_nonempty_s": med(d["ine"]),
                         "empty_within_30s_pct": round(d["q"] / d["e"] * 100, 1) if d["e"] else "",
                         "empty_after_120s_pct": round(d["late"] / d["e"] * 100, 1) if d["e"] else "",
                         "burst_blocks": sum(v for (x, _), v in burst.items() if x == e) if p == "TOTAL" else burst.get((e, p), 0),
                         "max_run": maxrun.get((e, p), 0), "runs_of_3_plus": runs3.get((e, p), 0),
                         "stale_blocks_seen": stale.get(p, "") if e == "post-2400000" else ""})
        rows.sort(key=lambda r: (r["era"] != "post-2400000", r["pool"] != "TOTAL", -r["blocks"]))
        w = csv.DictWriter(open(args[2], "w", newline=""), fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(rows)
        print("wrote", args[2], len(rows), "rows")

elif cmd == "arrival":
    frm = int(args[1]); P = pools(args[0], frm)
    R = re.compile(r"^(\S+ \S+) UpdateTip: new best=(\S+)\s+height=(\d+) .* date=(\S+ \S+) progress")
    seen = collections.defaultdict(list); ts = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d %H:%M:%S").timestamp()
    for path in args[2:]:
        f = gzip.open(path, "rt", errors="replace") if path.endswith(".gz") else open(path, errors="replace")
        for line in f:
            m = R.match(line)
            if m and int(m.group(3)) in P:
                seen[int(m.group(3))].append((ts(m.group(1)), ts(m.group(4))))
    last = {h: max(v) for h, v in seen.items() if abs(max(v)[0] - max(v)[1]) < 600}
    lag = collections.defaultdict(list); bat = collections.Counter(); late = collections.Counter()
    for h, (a, b) in last.items():
        p = P[h]; lag[p].append(a - b)
        if h + 1 in last and P.get(h + 1) == p and abs(last[h + 1][0] - a) <= 1:
            bat[p] += 1; late[p] += a - b > 15
    for p, v in sorted(lag.items(), key=lambda kv: -len(kv[1])):
        v.sort()
        print(f"{p[:24]:<24} n={len(v):>5} median {statistics.median(v):>5.0f} s  >30 s {sum(1 for x in v if x > 30) / len(v) * 100:5.1f}%  batched {bat[p]} (first block >15 s old: {late[p]})")

elif cmd == "forks":
    def blk(hh):
        b = batch([("getblock", [hh, 2])])[0]
        outs = [((v["scriptPubKey"].get("addresses") or ["?"])[0], round(v["value"] * COIN)) for v in b["tx"][0]["vout"]]
        return pool_of(b["height"], outs), b["height"], b["time"], b["previousblockhash"]
    rows = []
    for t in batch([("getchaintips", [])])[0]:
        if t["status"] != "valid-fork":
            continue
        chain, hh = [], t["hash"]
        for _ in range(t["branchlen"]):
            p, h, tm, prev = blk(hh); chain.append((p, h, tm)); hh = prev
        chain.reverse()
        win = [blk(batch([("getblockhash", [h])])[0]) for _, h, _ in chain]
        rows.append({"height": chain[0][1], "length": t["branchlen"], "stale_pools": [c[0] for c in chain],
                     "replacing_pools": [w[0] for w in win], "time": chain[0][2]})
    json.dump(rows, open(args[0], "w"), indent=1)
    print("stale:", collections.Counter(p for r in rows for p in r["stale_pools"]))
    print("replacing:", collections.Counter(p for r in rows for p in r["replacing_pools"]))
    print("two-block or longer:", [(r["height"], r["stale_pools"], r["replacing_pools"]) for r in rows if r["length"] > 1])

elif cmd == "tags":
    for h in args:
        b = batch([("getblock", [batch([("getblockhash", [int(h)])])[0], 2])])[0]
        print(h, re.findall(r"[ -~]{4,}", bytes.fromhex(b["tx"][0]["vin"][0]["coinbase"]).decode("latin1")))

elif cmd == "expiry":
    T = times(args[0]); k = int(args[1]) if len(args) > 1 else 300; random.seed(1)
    for lo, hi in [(1, 492849), (492850, 800000), (800000, 1600000), (1600000, 2400000), (2400000, max(T) + 1)]:
        hs = random.sample([h for h in T if lo <= h < hi and T[h][1] > 1], k)
        bl = batch([("getblock", [x, 1]) for x in batch([("getblockhash", [h]) for h in hs])])
        tids = [(b["height"], t) for b in bl for t in b["tx"][1:]][:2 * k]
        c = collections.Counter(); lt = collections.Counter()
        for (h, _), t in zip(tids, batch([("getrawtransaction", [t, 1]) for _, t in tids])):
            ex = t.get("expiryheight", 0)
            c["pre-overwinter" if not t.get("overwintered") else "expiry 0" if ex == 0 else "expiry creation+20" if 0 < ex - h <= 20 else "expiry other"] += 1
            if t.get("overwintered") and ex == 0:
                lt[t["locktime"]] += 1
        print(f"{lo}-{hi}: {dict(c)} expiry-0 locktimes {lt.most_common(3)}")
else:
    sys.exit(__doc__)
