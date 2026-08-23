#!/usr/bin/env python3
# Measure dbcache / UTXO / LevelDB fill and RPC latencies on regtest.
#
# P3: ZERO_MEASURE_MATRIX + ZERO_MEASURE_INSIGHT
# P4: continuous UpdateTip samples; gettxoutsetinfo only when SETINFO_EVERY>0 or at end
# P5: samples getdbinfo (LevelDB block-cache TotalCharge + UTXO fill) when available
#
# Usage:
#   PATH=src:$PATH python3 contrib/perf/measure_dbcache_utxo.py
#   ZERO_MEASURE_MATRIX=800,2048,4096 ZERO_MEASURE_INSIGHT=both \\
#     ZERO_MEASURE_BLOCKS=600 ZERO_MEASURE_SETINFO_EVERY=0 \\
#     PATH=src:$PATH python3 contrib/perf/measure_dbcache_utxo.py
#
# Env:
#   ZERO_MEASURE_DBCACHE          single run (default 800); ignored if MATRIX set
#   ZERO_MEASURE_MATRIX           comma list e.g. 800,2048,4096
#   ZERO_MEASURE_INSIGHT          0 | 1 | both (default 0)
#   ZERO_MEASURE_BLOCKS           blocks to mine (default 600)
#   ZERO_MEASURE_BATCH            generate batch (default 100)
#   ZERO_MEASURE_SETINFO_EVERY    0 = only final gettxoutsetinfo (P4); else every N
#   ZERO_MEASURE_DBINFO_EVERY     sample getdbinfo every N blocks (default = BATCH)
#   ZERO_MEASURE_ADDR_EVERY       insight getaddressbalance every N (default 200; 0=off)

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
BITCOIND = os.environ.get('BITCOIND', os.path.join(REPO, 'src', 'zerod'))
BITCOINCLI = os.environ.get('BITCOINCLI', os.path.join(REPO, 'src', 'zero-cli'))

TOTAL_BLOCKS = int(os.environ.get('ZERO_MEASURE_BLOCKS', '600'))
BATCH = int(os.environ.get('ZERO_MEASURE_BATCH', '100'))
SETINFO_EVERY = int(os.environ.get('ZERO_MEASURE_SETINFO_EVERY', '0'))
DBINFO_EVERY = int(os.environ.get('ZERO_MEASURE_DBINFO_EVERY', str(BATCH)))
ADDR_EVERY = int(os.environ.get('ZERO_MEASURE_ADDR_EVERY', '200'))

TIP_RE = re.compile(
    r'UpdateTip:.*height=(\d+).*cache=([0-9.]+)MiB\((\d+)tx\)'
)
CACHE_CFG_RE = re.compile(
    r'\* Using ([0-9.]+)MiB for (block index database|chain state database|in-memory UTXO set)'
)


def parse_matrix() -> list[int]:
    raw = os.environ.get('ZERO_MEASURE_MATRIX', '').strip()
    if raw:
        return [int(x) for x in raw.split(',') if x.strip()]
    return [int(os.environ.get('ZERO_MEASURE_DBCACHE', '800'))]


def parse_insight_modes() -> list[bool]:
    mode = os.environ.get('ZERO_MEASURE_INSIGHT', '0').strip().lower()
    if mode in ('both', 'all'):
        return [False, True]
    if mode in ('1', 'true', 'yes', 'on'):
        return [True]
    return [False]


def rss_kib(pid: int) -> int | None:
    try:
        out = subprocess.check_output(['ps', '-o', 'rss=', '-p', str(pid)], text=True)
        return int(out.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        return None


def cli(datadir: str, *args, timeout: int = 120) -> tuple[str, float]:
    """Return (stdout, latency_ms)."""
    cmd = [BITCOINCLI, '-datadir=' + datadir, '-rpcwait'] + list(args)
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    ms = (time.perf_counter() - t0) * 1000.0
    if r.returncode != 0:
        raise RuntimeError('cli %s failed: %s' % (args, r.stderr.strip()))
    return r.stdout.strip(), ms


def parse_cache_config(debug_log: str) -> dict:
    out = {}
    with open(debug_log, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = CACHE_CFG_RE.search(line)
            if not m:
                continue
            mib, label = float(m.group(1)), m.group(2)
            if 'block index' in label:
                out['budget_block_index_mib'] = mib
            elif 'chain state' in label:
                out['budget_chainstate_mib'] = mib
            elif 'in-memory UTXO' in label:
                out['budget_utxo_cache_mib'] = mib
    return out


def last_tip_cache(debug_log: str):
    last = None
    with open(debug_log, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            m = TIP_RE.search(line)
            if m:
                last = {
                    'height': int(m.group(1)),
                    'utxo_cache_mib': float(m.group(2)),
                    'utxo_cache_entries': int(m.group(3)),
                }
    return last


def du_mib(path: str) -> float | None:
    if not os.path.isdir(path):
        return None
    r = subprocess.run(['du', '-sk', path], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return int(r.stdout.split()[0]) / 1024.0


def summarize_latencies(samples: list[dict]) -> dict:
    keys = [
        'generate_ms', 'getdbinfo_ms', 'gettxoutsetinfo_ms', 'getaddressbalance_ms',
    ]
    out = {}
    for k in keys:
        vals = [s[k] for s in samples if s.get(k) is not None]
        if not vals:
            continue
        vals = sorted(vals)
        out[k] = {
            'n': len(vals),
            'min_ms': round(vals[0], 3),
            'p50_ms': round(vals[len(vals) // 2], 3),
            'max_ms': round(vals[-1], 3),
            'mean_ms': round(sum(vals) / len(vals), 3),
        }
    return out


def run_one(dbcache: int, insight: bool, stamp: str, run_idx: int) -> dict:
    port = 19000 + (os.getpid() % 1000) + run_idx * 2
    rpcport = port + 1
    tmp = tempfile.mkdtemp(prefix='measure-dbcache-', dir='/tmp')
    datadir = tmp
    with open(os.path.join(datadir, 'zero.conf'), 'w', encoding='utf8') as f:
        f.write('regtest=1\nshowmetrics=0\nrpcuser=rt\nrpcpassword=rt\n')
        f.write('port=%d\nrpcport=%d\nlistenonion=0\n' % (port, rpcport))

    args = [
        BITCOIND, '-datadir=' + datadir, '-regtest',
        '-listen=0', '-discover=0', '-keypool=1', '-dnsseed=0',
        '-dbcache=%d' % dbcache,
        '-checkblockindex=0', '-checkmempool=0', '-checkblocks=1',
        '-nuparams=6f76727a:1', '-nuparams=7361707a:1',
        '-printtoconsole=0',
    ]
    if insight:
        args.extend([
            '-txindex=1',
            '-experimentalfeatures=1',
            '-insightexplorer=1',
        ])

    proc = subprocess.Popen(args)
    debug_log = os.path.join(datadir, 'regtest', 'debug.log')
    samples: list[dict] = []
    mine_addr = None
    has_getdbinfo = None

    try:
        for _ in range(180):
            if proc.poll() is not None:
                raise RuntimeError('zerod exited early code=%s' % proc.returncode)
            if os.path.isfile(debug_log):
                try:
                    cli(datadir, 'getblockcount', timeout=5)
                    break
                except Exception:
                    pass
            time.sleep(0.5)
        else:
            raise RuntimeError('RPC not ready')

        time.sleep(0.5)
        budgets = parse_cache_config(debug_log)

        # Probe getdbinfo once
        try:
            raw, ms = cli(datadir, 'getdbinfo', timeout=30)
            json.loads(raw)
            has_getdbinfo = True
            _ = ms
        except Exception:
            has_getdbinfo = False

        if insight:
            mine_addr, _ = cli(datadir, 'getnewaddress', timeout=30)

        def sample(tag: str, want_setinfo: bool, want_dbinfo: bool, want_addr: bool,
                   generate_ms: float | None = None):
            tip = last_tip_cache(debug_log) or {
                'height': int(cli(datadir, 'getblockcount')[0]),
                'utxo_cache_mib': None,
                'utxo_cache_entries': None,
            }
            row = {
                'tag': tag,
                'height': tip['height'],
                'utxo_cache_mib': tip.get('utxo_cache_mib'),
                'utxo_cache_entries': tip.get('utxo_cache_entries'),
                'rss_mib': None,
                'disk_blocks_index_mib': du_mib(
                    os.path.join(datadir, 'regtest', 'blocks', 'index')),
                'disk_chainstate_mib': du_mib(
                    os.path.join(datadir, 'regtest', 'chainstate')),
                'txouts': None,
                'bytes_serialized': None,
                'set_transactions': None,
                'total_amount': None,
                'utxo_cache_fill_pct': None,
                'generate_ms': generate_ms,
                'getdbinfo_ms': None,
                'gettxoutsetinfo_ms': None,
                'getaddressbalance_ms': None,
                'dbinfo': None,
            }
            rss = rss_kib(proc.pid)
            if rss is not None:
                row['rss_mib'] = round(rss / 1024.0, 2)
            bud = budgets.get('budget_utxo_cache_mib')
            if bud and row['utxo_cache_mib'] is not None:
                row['utxo_cache_fill_pct'] = round(
                    100.0 * row['utxo_cache_mib'] / bud, 4)

            if want_dbinfo and has_getdbinfo:
                raw, ms = cli(datadir, 'getdbinfo', timeout=60)
                row['getdbinfo_ms'] = round(ms, 3)
                info = json.loads(raw)
                # Keep compact fields for CSV/JSON size
                row['dbinfo'] = {
                    'utxo_fill_pct': info.get('utxo_cache', {}).get('fill_pct'),
                    'utxo_bytes': info.get('utxo_cache', {}).get('bytes'),
                    'utxo_entries': info.get('utxo_cache', {}).get('entries'),
                    'bi_cache_fill_pct': info.get('block_index', {}).get(
                        'block_cache_fill_pct'),
                    'bi_cache_usage': info.get('block_index', {}).get(
                        'block_cache_usage_bytes'),
                    'bi_cache_cap': info.get('block_index', {}).get(
                        'block_cache_capacity_bytes'),
                    'cs_cache_fill_pct': info.get('chainstate', {}).get(
                        'block_cache_fill_pct'),
                    'cs_cache_usage': info.get('chainstate', {}).get(
                        'block_cache_usage_bytes'),
                    'cs_cache_cap': info.get('chainstate', {}).get(
                        'block_cache_capacity_bytes'),
                    'bi_l0': info.get('block_index', {}).get('num_files_at_level0'),
                    'cs_l0': info.get('chainstate', {}).get('num_files_at_level0'),
                }

            if want_setinfo:
                raw, ms = cli(datadir, 'gettxoutsetinfo', timeout=300)
                row['gettxoutsetinfo_ms'] = round(ms, 3)
                info = json.loads(raw)
                row['txouts'] = info.get('txouts')
                row['bytes_serialized'] = info.get('bytes_serialized')
                row['set_transactions'] = info.get('transactions')
                row['total_amount'] = info.get('total_amount')

            if want_addr and insight and mine_addr:
                addr_arg = json.dumps({'addresses': [mine_addr]})
                raw, ms = cli(
                    datadir, 'getaddressbalance', addr_arg, timeout=60)
                row['getaddressbalance_ms'] = round(ms, 3)
                try:
                    bal = json.loads(raw)
                    row['address_balance'] = bal.get('balance')
                except json.JSONDecodeError:
                    row['address_balance'] = None

            samples.append(row)
            brief = {k: row[k] for k in (
                'tag', 'height', 'utxo_cache_entries', 'utxo_cache_mib',
                'generate_ms', 'getdbinfo_ms', 'gettxoutsetinfo_ms',
                'getaddressbalance_ms',
            )}
            if row.get('dbinfo'):
                brief['bi_fill'] = row['dbinfo'].get('bi_cache_fill_pct')
                brief['cs_fill'] = row['dbinfo'].get('cs_cache_fill_pct')
                brief['utxo_rpc_fill'] = row['dbinfo'].get('utxo_fill_pct')
            print(json.dumps(brief, sort_keys=True))
            sys.stdout.flush()

        sample('start', want_setinfo=False, want_dbinfo=True, want_addr=False)
        mined = 0
        while mined < TOTAL_BLOCKS:
            n = min(BATCH, TOTAL_BLOCKS - mined)
            _, gen_ms = cli(datadir, 'generate', str(n), timeout=600)
            mined += n
            height = int(cli(datadir, 'getblockcount')[0])
            at_end = mined >= TOTAL_BLOCKS
            want_set = at_end or (
                SETINFO_EVERY > 0 and height % SETINFO_EVERY == 0)
            want_db = at_end or (
                DBINFO_EVERY > 0 and height % DBINFO_EVERY == 0)
            want_addr = (
                insight and ADDR_EVERY > 0 and
                (at_end or height % ADDR_EVERY == 0))
            sample(
                'mine_%d' % height,
                want_setinfo=want_set,
                want_dbinfo=want_db,
                want_addr=want_addr,
                generate_ms=round(gen_ms, 3),
            )

        # Final setinfo if somehow skipped (SETINFO_EVERY=0 path already sets at_end)
        if not any(s.get('txouts') is not None for s in samples):
            sample('final_setinfo', True, True, insight)

        final_dbinfo = None
        if has_getdbinfo:
            raw, ms = cli(datadir, 'getdbinfo', timeout=60)
            final_dbinfo = json.loads(raw)
            final_dbinfo['_getdbinfo_ms'] = round(ms, 3)

        report = {
            'generated_at': stamp,
            'dbcache_arg': dbcache,
            'insightexplorer': insight,
            'total_blocks_mined': TOTAL_BLOCKS,
            'batch': BATCH,
            'setinfo_every': SETINFO_EVERY,
            'dbinfo_every': DBINFO_EVERY,
            'has_getdbinfo': has_getdbinfo,
            'budgets_mib': budgets,
            'latency_summary_ms': summarize_latencies(samples),
            'final_dbinfo': final_dbinfo,
            'samples': samples,
            'notes': [
                'P4: UpdateTip sampled every batch; gettxoutsetinfo only when '
                'SETINFO_EVERY>0 or at end (default SETINFO_EVERY=0)',
                'P5: getdbinfo exposes LevelDB block_cache_usage via Cache::TotalCharge',
                'disk_* are du of LevelDB dirs (file size, not LRU occupancy)',
            ],
        }
        return report
    finally:
        try:
            cli(datadir, 'stop', timeout=30)
        except Exception:
            pass
        try:
            proc.wait(timeout=30)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)


def self_test() -> int:
    """Pin log parsing and the latency summary.

    These functions turn a debug.log into recorded numbers. A parse that
    silently returns nothing produces an empty cell rather than an error, so
    absence is asserted explicitly alongside correctness.
    """
    import tempfile

    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, 'debug.log')
        with open(log, 'w', encoding='utf-8') as fh:
            fh.write(
                # Format matches src/init.cpp LogPrintf exactly: leading
                # "* Using ", no space before MiB.
                "2026-08-19 10:00:00 * Using 2.0MiB for block index database\n"
                "2026-08-19 10:00:00 * Using 8.0MiB for chain state database\n"
                "2026-08-19 10:00:00 * Using 450.0MiB for in-memory UTXO set\n"
                "2026-08-19 10:00:01 UpdateTip: new best=aa height=100 "
                "log2_work=1 tx=1 date=2026-08-19 progress=0.1 "
                "cache=1.5MiB(20tx)\n"
                "2026-08-19 10:00:02 UpdateTip: new best=bb height=200 "
                "log2_work=1 tx=2 date=2026-08-19 progress=0.2 "
                "cache=2.5MiB(40tx)\n"
            )
        cfg = parse_cache_config(log)
        check(cfg.get('budget_block_index_mib') == 2.0, "block index budget parsed")
        check(cfg.get('budget_chainstate_mib') == 8.0, "chainstate budget parsed")
        check(cfg.get('budget_utxo_cache_mib') == 450.0, "UTXO budget parsed")

        tip = last_tip_cache(log)
        check(tip is not None, "tip line parsed")
        if tip:
            # LAST tip, not first: the run's end state is what is recorded.
            check(tip['height'] == 200, "last tip wins, not the first")
            check(tip['utxo_cache_mib'] == 2.5, "cache MiB parsed")
            check(tip['utxo_cache_entries'] == 40, "cache entry count parsed")

        empty = os.path.join(d, 'empty.log')
        open(empty, 'w').close()
        check(parse_cache_config(empty) == {}, "no config lines yields {}")
        check(last_tip_cache(empty) is None, "no tip lines yields None, not 0")

    # Latency summary.
    samples = [{'generate_ms': v} for v in (30.0, 10.0, 20.0)]
    out = summarize_latencies(samples)
    g = out['generate_ms']
    check(g['n'] == 3, "n counts samples")
    check(g['min_ms'] == 10.0 and g['max_ms'] == 30.0, "min/max over sorted values")
    check(g['mean_ms'] == 20.0, "mean computed")
    check(g['p50_ms'] == 20.0, "p50 of an odd count is the middle value")

    # KNOWN BEHAVIOUR: p50 is the upper-middle element, not an interpolated
    # median, so an even count skews high. Pinned so a future change to
    # summarize_latencies is a deliberate one, not an accident.
    even = [{'generate_ms': v} for v in (10.0, 20.0)]
    check(summarize_latencies(even)['generate_ms']['p50_ms'] == 20.0,
          "p50 on an even count takes the upper middle (not interpolated)")

    check(summarize_latencies([]) == {}, "no samples yields {}")
    check(summarize_latencies([{'generate_ms': None}]) == {},
          "all-None samples are dropped, not counted as zero")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if not os.path.isfile(BITCOIND):
        print('missing zerod at %s' % BITCOIND, file=sys.stderr)
        return 2

    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    log_dir = os.path.join(REPO, 'test-logs')
    os.makedirs(log_dir, exist_ok=True)

    matrix = parse_matrix()
    insights = parse_insight_modes()
    runs = []
    run_idx = 0
    for dbcache in matrix:
        for insight in insights:
            label = 'dbcache=%d insight=%s' % (dbcache, insight)
            print('=== RUN %s ===' % label, flush=True)
            report = run_one(dbcache, insight, stamp, run_idx)
            run_idx += 1
            runs.append(report)
            out_json = os.path.join(
                log_dir,
                '%s-dbcache-%d-insight%d.json' % (stamp, dbcache, int(insight)),
            )
            with open(out_json, 'w', encoding='utf8') as f:
                json.dump(report, f, indent=2)
                f.write('\n')
            print('Wrote %s' % out_json, flush=True)

    summary = {
        'generated_at': stamp,
        'matrix': matrix,
        'insight_modes': insights,
        'blocks': TOTAL_BLOCKS,
        'setinfo_every': SETINFO_EVERY,
        'runs': [
            {
                'dbcache_arg': r['dbcache_arg'],
                'insightexplorer': r['insightexplorer'],
                'budgets_mib': r['budgets_mib'],
                'has_getdbinfo': r['has_getdbinfo'],
                'latency_summary_ms': r['latency_summary_ms'],
                'final_tip': {
                    'height': r['samples'][-1]['height'] if r['samples'] else None,
                    'utxo_cache_entries': r['samples'][-1].get('utxo_cache_entries'),
                    'utxo_cache_mib': r['samples'][-1].get('utxo_cache_mib'),
                    'txouts': next(
                        (s['txouts'] for s in reversed(r['samples'])
                         if s.get('txouts') is not None),
                        None,
                    ),
                    'bytes_serialized': next(
                        (s['bytes_serialized'] for s in reversed(r['samples'])
                         if s.get('bytes_serialized') is not None),
                        None,
                    ),
                    'rss_mib': r['samples'][-1].get('rss_mib'),
                    'disk_blocks_index_mib': r['samples'][-1].get(
                        'disk_blocks_index_mib'),
                    'disk_chainstate_mib': r['samples'][-1].get(
                        'disk_chainstate_mib'),
                },
                'final_dbinfo_compact': (
                    {
                        'utxo_fill_pct': r['final_dbinfo'].get(
                            'utxo_cache', {}).get('fill_pct'),
                        'bi_fill_pct': r['final_dbinfo'].get(
                            'block_index', {}).get('block_cache_fill_pct'),
                        'cs_fill_pct': r['final_dbinfo'].get(
                            'chainstate', {}).get('block_cache_fill_pct'),
                        'bi_usage': r['final_dbinfo'].get(
                            'block_index', {}).get('block_cache_usage_bytes'),
                        'cs_usage': r['final_dbinfo'].get(
                            'chainstate', {}).get('block_cache_usage_bytes'),
                        'budgets': r['final_dbinfo'].get('budgets'),
                    } if r.get('final_dbinfo') else None
                ),
            }
            for r in runs
        ],
    }
    out_sum = os.path.join(log_dir, '%s-dbcache-matrix-summary.json' % stamp)
    with open(out_sum, 'w', encoding='utf8') as f:
        json.dump(summary, f, indent=2)
        f.write('\n')
    print('Wrote %s' % out_sum)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
