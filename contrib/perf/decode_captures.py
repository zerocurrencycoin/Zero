#!/usr/bin/env python3
"""Decode a capture_sequence.sh run into a combined report.

For each capture_NNN/ subdirectory under a captures root (produced by
capture_sequence.sh), this:
  1. Exports timeprofile.trace to XML via `xcrun xctrace export` (skipped if
     the export already exists from a prior run of this script).
  2. Buckets CPU time using the same call-stack substring matching as
     reindex-profile/tools/bucket_profile.py (imported directly, not
     reimplemented: the id/ref backreference parsing is subtle and has
     exactly one correct implementation).
  3. Derives the capture's exact block-height range from the trace's own
     <start-date> (in its stated UTC offset) cross-referenced against the
     debug.log snapshot's UpdateTip timestamps. This is more precise than
     capture_meta.txt's
     RPC-polled height_before/height_after, which only bound the *whole*
     capture-plus-idle loop iteration, not the 300s recording window itself.
  4. Optionally samples a handful of blocks in that height range over RPC
     (getblock <hash> 2) for a transparent/Sprout/Sapling tx-type mix --
     skipped by default since it needs a live node; pass --rpc to enable
     against a currently-running zerod on the same datadir.

Usage:
    python3 contrib/perf/decode_captures.py <captures_dir> [--rpc] [--json out.json]

Output: a human-readable report to stdout, and optionally a machine-readable
JSON summary (--json) for further analysis.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "reindex-profile" / "tools"
sys.path.insert(0, str(TOOLS_DIR))
import bucket_profile  # noqa: E402  (reindex-profile/tools/bucket_profile.py)


class UnsupportedTraceError(Exception):
    """Raised when xcrun xctrace export can't read a trace's schema/toc in
    this Instruments version -- known to happen for File Activity,
    Allocations, and Leaks templates ("Document Missing Template Error"),
    which are GUI-only for export in the version this was developed against.
    Open those traces in Instruments.app instead."""


def _run_xctrace(args, cap_dir_hint=""):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        if "Document Missing Template Error" in (r.stdout + r.stderr):
            raise UnsupportedTraceError(
                f"{cap_dir_hint}: this trace's template can't be read by `xcrun xctrace export` "
                "in this Instruments version (likely File Activity/Allocations/Leaks, not Time "
                "Profiler) -- open it in Instruments.app instead."
            )
        raise subprocess.CalledProcessError(r.returncode, args, r.stdout, r.stderr)
    return r.stdout


def export_trace(trace_path, xml_path):
    if xml_path.exists():
        return
    _run_xctrace(
        [
            "xcrun", "xctrace", "export",
            "--input", str(trace_path),
            "--xpath", '/trace-toc/run[1]/data[1]/table[@schema="time-profile"]',
            "--output", str(xml_path),
        ],
        cap_dir_hint=str(trace_path.parent),
    )


def trace_start_end(trace_path, capture_secs):
    toc = _run_xctrace(
        ["xcrun", "xctrace", "export", "--input", str(trace_path), "--toc"],
        cap_dir_hint=str(trace_path.parent),
    )
    m = re.search(r"<start-date>([^<]+)</start-date>", toc)
    if not m:
        return None, None
    start = datetime.fromisoformat(m.group(1))
    end = start + __import__("datetime").timedelta(seconds=capture_secs)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


UPDATETIP_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) UpdateTip:.*?height=(\d+)"
)


def height_range_from_log(debug_log_path, start_utc, end_utc):
    """First/last UpdateTip height whose (UTC) timestamp falls in
    [start_utc, end_utc]. Bound by timestamp, not by searching for a
    height substring: `height=937` also matches `height=937237`."""
    first_h = last_h = None
    with open(debug_log_path, "r", encoding="utf8", errors="replace") as f:
        for line in f:
            m = UPDATETIP_RE.match(line)
            if not m:
                continue
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if start_utc <= ts <= end_utc:
                h = int(m.group(2))
                if first_h is None:
                    first_h = h
                last_h = h
    return first_h, last_h


def bucket_capture(xml_path, thread_filter="zcash-loadblk"):
    """Re-implements bucket_profile.main()'s parse loop but returns data
    instead of printing, so results can be aggregated across captures."""
    with open(xml_path, encoding="utf8") as f:
        content = f.read()
    rows = re.findall(r"<row>.*?</row>", content, re.DOTALL)

    thread_id_to_name = {}
    weight_id_to_ns = {}
    backtrace_id_to_frameids = {}
    frameid_to_name = {}

    row_re = re.compile(
        r'<thread (id="(\d+)"[^>]*fmt="([^"]*)"|ref="(\d+)")[^>]*/?>.*?'
        r'<weight (id="(\d+)"[^>]*fmt="([^"]*)"|ref="(\d+)")[^>]*/?>.*?'
        r'<tagged-backtrace (id="(\d+)"[^>]*fmt="[^"]*"|ref="(\d+)")',
        re.DOTALL,
    )
    frame_tag_re = re.compile(r'<frame (?:id="(\d+)"[^>]*\bname="([^"]*)"|ref="(\d+)")')
    backtrace_block_re = re.compile(r'<backtrace id="(\d+)">(.*?)</backtrace>', re.DOTALL)

    def resolve_frames(bt_content):
        ids = []
        for fid, fname, fref in frame_tag_re.findall(bt_content):
            if fid:
                frameid_to_name[fid] = fname
                ids.append(fid)
            else:
                ids.append(fref)
        return [frameid_to_name.get(i, f"<unresolved:{i}>") for i in ids]

    filtered_weight = 0.0
    filtered_samples = 0
    bucket_weight = Counter()

    for row in rows:
        m = row_re.search(row)
        if not m:
            continue
        thread_id, thread_ref, thread_fmt = m.group(2), m.group(4), m.group(3)
        weight_id, weight_ref, weight_fmt = m.group(6), m.group(8), m.group(7)
        bt_id, bt_ref = m.group(10), m.group(11)

        if thread_id:
            thread_id_to_name[thread_id] = thread_fmt
            tname = thread_fmt
        else:
            tname = thread_id_to_name.get(thread_ref, "")

        if weight_id:
            wns = bucket_profile.parse_weight_fmt(weight_fmt)
            weight_id_to_ns[weight_id] = wns
        else:
            wns = weight_id_to_ns.get(weight_ref, 0.0)

        bm = backtrace_block_re.search(row)
        if bt_id and bm:
            frames = resolve_frames(bm.group(2))
            backtrace_id_to_frameids[bt_id] = frames
        else:
            frames = backtrace_id_to_frameids.get(bt_ref, [])

        if thread_filter not in tname:
            continue

        filtered_samples += 1
        filtered_weight += wns

        matched = None
        for bucket, needles in bucket_profile.BUCKETS.items():
            if any(any(n in f for n in needles) for f in frames):
                matched = bucket
                break
        bucket_weight[matched or "other"] += wns

    return {
        "filtered_samples": filtered_samples,
        "filtered_weight_s": filtered_weight / 1e9,
        "buckets": {k: v / 1e9 for k, v in bucket_weight.items()},
    }


def sample_tx_types(rpc_cli, datadir, rpcport, height_lo, height_hi, n_samples=5):
    """Sample n_samples block heights evenly across [lo, hi] via getblock
    verbosity=2, classify each tx as transparent/sprout/sapling (a tx can be
    more than one at once -- shielding/deshielding txs mix pools)."""
    if height_lo is None or height_hi is None or height_hi < height_lo:
        return None
    span = height_hi - height_lo
    step = max(1, span // max(1, n_samples - 1)) if n_samples > 1 else 1
    heights = sorted(set(min(height_lo + i * step, height_hi) for i in range(n_samples)))

    totals = Counter()
    blocks_sampled = 0
    for h in heights:
        try:
            block_json = subprocess.run(
                [rpc_cli, f"-datadir={datadir}", f"-rpcport={rpcport}", "getblock", str(h), "2"],
                check=True, capture_output=True, text=True,
            ).stdout
            block = json.loads(block_json)
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue

        blocks_sampled += 1
        for tx in block.get("tx", []):
            totals["tx_total"] += 1
            has_transparent = bool(tx.get("vin") or tx.get("vout"))
            has_sprout = bool(tx.get("vjoinsplit"))
            has_sapling = bool(tx.get("vShieldedSpend") or tx.get("vShieldedOutput"))
            if has_transparent:
                totals["tx_transparent"] += 1
            if has_sprout:
                totals["tx_sprout"] += 1
            if has_sapling:
                totals["tx_sapling"] += 1
            if not (has_sprout or has_sapling):
                totals["tx_fully_transparent"] += 1

    return {"blocks_sampled": blocks_sampled, "heights_sampled": heights, **totals}


def decode_one(cap_dir, do_rpc, rpc_cli, rpcport):
    trace_path = cap_dir / "timeprofile.trace"
    xml_path = cap_dir / "timeprofile_agg.xml"
    meta_path = cap_dir / "capture_meta.txt"
    log_snapshot = cap_dir / "debug.log.snapshot"

    if not trace_path.exists():
        return None

    meta = {}
    if meta_path.exists():
        for line in meta_path.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                meta[k] = v

    export_trace(trace_path, xml_path)
    capture_secs = int(meta.get("capture_secs", 300))
    start_utc, end_utc = trace_start_end(trace_path, capture_secs)

    height_lo = height_hi = None
    if log_snapshot.exists() and start_utc and end_utc:
        height_lo, height_hi = height_range_from_log(log_snapshot, start_utc, end_utc)

    bucket_result = bucket_capture(xml_path)

    tx_stats = None
    if do_rpc and height_lo is not None:
        datadir = str(cap_dir.parent.parent / "datadir") if (cap_dir.parent.parent / "datadir").exists() else None
        if datadir:
            tx_stats = sample_tx_types(rpc_cli, datadir, rpcport, height_lo, height_hi)

    return {
        "capture_dir": str(cap_dir),
        "capture_num": meta.get("capture_num"),
        "height_before_loop": meta.get("height_before"),
        "height_after_loop": meta.get("height_after"),
        "trace_start_utc": start_utc.isoformat() if start_utc else None,
        "trace_end_utc": end_utc.isoformat() if end_utc else None,
        "height_lo_exact": height_lo,
        "height_hi_exact": height_hi,
        "blocks_in_window": (height_hi - height_lo) if (height_lo is not None and height_hi is not None) else None,
        "blocks_per_sec": (
            (height_hi - height_lo) / capture_secs
            if (height_lo is not None and height_hi is not None) else None
        ),
        "cpu_buckets": bucket_result,
        "tx_stats": tx_stats,
    }


def self_test():
    """Pin the window derivation and log parsing.

    height_range_from_log decides the height window recorded with every
    capture, and a window is what makes a CPU share comparable at all
    (docs/HOWTO.md S2.4). It is bound by timestamp rather than by substring
    precisely because `height=937` also matches `height=937237` -- that trap is
    pinned below.
    """
    import tempfile

    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    def ts(s):
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

    log = (
        "2026-08-19 10:00:00 UpdateTip: new best=aa height=937 log2_work=1 tx=1\n"
        "2026-08-19 10:00:30 UpdateTip: new best=bb height=937237 log2_work=1 tx=1\n"
        "2026-08-19 10:01:00 UpdateTip: new best=cc height=940000 log2_work=1 tx=1\n"
        "2026-08-19 10:02:00 UpdateTip: new best=dd height=950000 log2_work=1 tx=1\n"
        "2026-08-19 10:01:30 some other line that is not a tip\n"
    )
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "debug.log")
        with open(f, "w", encoding="utf8") as fh:
            fh.write(log)

        lo, hi = height_range_from_log(f, ts("2026-08-19 10:00:00"),
                                       ts("2026-08-19 10:01:00"))
        check((lo, hi) == (937, 940000),
              "window is first/last tip inside the interval, got %r" % ((lo, hi),))

        # The substring trap: a window starting at the 937237 line must not
        # pick up the earlier height=937 row.
        lo, hi = height_range_from_log(f, ts("2026-08-19 10:00:30"),
                                       ts("2026-08-19 10:02:00"))
        check(lo == 937237, "bound by timestamp, not by height substring")

        # Interval with no tips yields (None, None) rather than a bogus window.
        lo, hi = height_range_from_log(f, ts("2026-08-19 09:00:00"),
                                       ts("2026-08-19 09:30:00"))
        check((lo, hi) == (None, None), "empty interval yields no window")

        # Boundaries are inclusive on BOTH ends, tested separately so an
        # exclusive comparison cannot pass by matching some interior tip.
        lo, hi = height_range_from_log(f, ts("2026-08-19 10:02:00"),
                                       ts("2026-08-19 10:02:00"))
        check((lo, hi) == (950000, 950000),
              "a zero-width interval on a tip still selects it")
        # Start bound: the tip exactly at start must be included.
        lo, _ = height_range_from_log(f, ts("2026-08-19 10:01:00"),
                                      ts("2026-08-19 10:02:00"))
        check(lo == 940000, "tip exactly at the start bound is included")
        # End bound: the tip exactly at end must be included.
        _, hi = height_range_from_log(f, ts("2026-08-19 10:00:00"),
                                      ts("2026-08-19 10:00:30"))
        check(hi == 937237, "tip exactly at the end bound is included")

        # A malformed/short file must not raise.
        bad = os.path.join(d, "bad.log")
        with open(bad, "w", encoding="utf8") as fh:
            fh.write("not a log line\n\n")
        check(height_range_from_log(bad, ts("2026-08-19 10:00:00"),
                                    ts("2026-08-19 10:02:00")) == (None, None),
              "unparseable log yields no window, not an exception")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main():
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser()
    ap.add_argument("captures_dir", type=Path)
    ap.add_argument("--rpc", action="store_true", help="sample tx-type mix via zero-cli RPC (needs a live node)")
    ap.add_argument("--rpc-cli", default=None, help="path to zero-cli (default: <repo>/src/zero-cli)")
    ap.add_argument("--rpcport", default="23920")
    ap.add_argument("--json", type=Path, default=None, help="also write machine-readable JSON here")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    rpc_cli = args.rpc_cli or str(repo_root / "src" / "zero-cli")

    cap_dirs = sorted(p for p in args.captures_dir.glob("capture_*") if p.is_dir())
    if not cap_dirs:
        print(f"no capture_* subdirectories found under {args.captures_dir}", file=sys.stderr)
        sys.exit(1)

    results = []
    skipped = []
    for cap_dir in cap_dirs:
        print(f"decoding {cap_dir.name}...", file=sys.stderr)
        try:
            r = decode_one(cap_dir, args.rpc, rpc_cli, args.rpcport)
        except UnsupportedTraceError as e:
            print(f"  skipped: {e}", file=sys.stderr)
            skipped.append(cap_dir.name)
            continue
        if r:
            results.append(r)

    if skipped:
        print(f"\n{len(skipped)} capture(s) skipped (unsupported trace template): {', '.join(skipped)}", file=sys.stderr)

    # --- report ---
    print(f"\n{'='*100}")
    print(f"Capture sequence report: {len(results)} capture(s) in {args.captures_dir}")
    print(f"{'='*100}\n")

    agg_bucket = Counter()
    agg_weight = 0.0
    total_blocks = 0

    for r in results:
        h_lo, h_hi = r["height_lo_exact"], r["height_hi_exact"]
        height_str = f"{h_lo} -> {h_hi} ({r['blocks_in_window']} blocks)" if h_lo is not None else "(height range undetermined)"
        bps = f"{r['blocks_per_sec']:.1f} blk/s" if r["blocks_per_sec"] else "n/a"
        print(f"--- {Path(r['capture_dir']).name} ---")
        print(f"  height range:  {height_str}   ({bps})")
        print(f"  trace window:  {r['trace_start_utc']} -> {r['trace_end_utc']}")
        cb = r["cpu_buckets"]
        print(f"  zcash-loadblk samples: {cb['filtered_samples']}  ({cb['filtered_weight_s']:.2f}s)")
        for bucket, secs in sorted(cb["buckets"].items(), key=lambda kv: -kv[1]):
            pct = 100 * secs / cb["filtered_weight_s"] if cb["filtered_weight_s"] else 0
            print(f"    {bucket:28s} {secs:8.2f}s  {pct:6.2f}%")
            agg_bucket[bucket] += secs
        agg_weight += cb["filtered_weight_s"]
        if r["blocks_in_window"]:
            total_blocks += r["blocks_in_window"]
        if r["tx_stats"]:
            ts = r["tx_stats"]
            print(f"  tx sample ({ts['blocks_sampled']} blocks @ heights {ts['heights_sampled']}):"
                  f" total={ts.get('tx_total', 0)}"
                  f" transparent={ts.get('tx_transparent', 0)}"
                  f" sprout={ts.get('tx_sprout', 0)}"
                  f" sapling={ts.get('tx_sapling', 0)}"
                  f" fully_transparent={ts.get('tx_fully_transparent', 0)}")
        print()

    print(f"{'='*100}")
    print(f"Aggregate across all captures ({total_blocks} blocks, {agg_weight:.1f}s zcash-loadblk CPU):")
    print(f"{'='*100}")
    for bucket, secs in agg_bucket.most_common():
        pct = 100 * secs / agg_weight if agg_weight else 0
        print(f"  {bucket:28s} {secs:8.2f}s  {pct:6.2f}%")

    if args.json:
        args.json.write_text(json.dumps(results, indent=2))
        print(f"\nJSON summary written to {args.json}", file=sys.stderr)


if __name__ == "__main__":
    main()
