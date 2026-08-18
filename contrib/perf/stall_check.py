#!/usr/bin/env python3
"""Scan zerod debug.log for follow-tip stalls and related clock/P2P bursts.

Read-only. Does not launch zerod. Log path spec is shared with
extract_measures.py (contrib/perf/debuglog.py): --datadir, --rotated, --log,
positional file/dir/glob. Launchers that write still refuse the live
datadir unless ZERO_PERF_ALLOW_LIVE_DATADIR=1.

Zero PoW target spacing is 120s. Default --gap-s 900 flags an UpdateTip wall
gap of 15 minutes (about 7.5 expected blocks at tip). IBD/reindex emits
UpdateTip far faster, so the same gap is also a stall there.

Usage:
  python3 contrib/perf/stall_check.py --self-test
  python3 contrib/perf/stall_check.py /path/to/debug.log
  python3 contrib/perf/stall_check.py --datadir "$HOME/Library/Application Support/zero"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Optional, TextIO

_PERF_DIR = Path(__file__).resolve().parent
if str(_PERF_DIR) not in sys.path:
    sys.path.insert(0, str(_PERF_DIR))
import debuglog  # noqa: E402

TS_RE = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
TS_PREFIX = re.compile(r"^" + TS_RE)
TIP_RE = re.compile(
    r"^"
    + TS_RE
    + r"\s+UpdateTip:.*?(?:new height=|height=)(\d+)"
    + r".*?date=("
    + TS_RE
    + r")"
)
TIMEOUT_RE = re.compile(
    r"^"
    + TS_RE
    + r"\s+socket (receive|sending) timeout: (\d+)s"
)
PING_RE = re.compile(r"^" + TS_RE + r"\s+ping timeout: ([0-9.]+)s")
VERSION_RE = re.compile(r"^" + TS_RE + r"\s+Zero version ")
CLOCK_WARN_RE = re.compile(
    r"^" + TS_RE + r"\s+\*\*\* Warning: Please check that your computer's date"
)
NTIME_RE = re.compile(r"^" + TS_RE + r"\s+nTimeOffset = ([+-]?\d+)")
EXPIRED_RE = re.compile(r"^" + TS_RE + r"\s+ERROR: ContextualCheckTransaction\(\): transaction is expired")
MISBEHAVE_RE = re.compile(r"^" + TS_RE + r"\s+Misbehaving:")
BAN_RE = re.compile(r"^" + TS_RE + r"\s+Misbehaving:.*BAN THRESHOLD EXCEEDED")
LOGICAL_TS_RE = re.compile(
    r"^" + TS_RE + r"\s+ConnectBlock: Previous logical timestamp is newer"
)

POW_TARGET_S = 120


def parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


@dataclass
class Finding:
    kind: str
    ts: datetime
    detail: str
    wall_s: float = 0.0
    height: Optional[int] = None
    height_prev: Optional[int] = None


@dataclass
class Scan:
    tips: int = 0
    height_first: Optional[int] = None
    height_last: Optional[int] = None
    ts_first: Optional[datetime] = None
    ts_last: Optional[datetime] = None
    tip_ts_last: Optional[datetime] = None
    max_gap_s: float = 0.0
    timeouts: int = 0
    ping_timeouts: int = 0
    timeout_max_s: float = 0.0
    expired_tx: int = 0
    misbehaving: int = 0
    bans: int = 0
    logical_ts_bumps: int = 0
    header_lag_catchup: int = 0
    ntime_offsets: list[int] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    restarts: int = 0


def _open(path: Path) -> TextIO:
    return open(path, encoding="utf-8", errors="replace")


def iter_lines(paths: Iterable[Path]) -> Iterator[str]:
    for path in paths:
        with _open(path) as f:
            for line in f:
                yield line.rstrip("\n")


def scan_lines(
    lines: Iterable[str],
    gap_s: float,
    header_lag_s: float,
    burst_n: int,
) -> Scan:
    s = Scan()
    last_tip_ts: Optional[datetime] = None
    last_tip_h: Optional[int] = None
    burst_ts: Optional[datetime] = None
    burst_count = 0
    last_line_ts: Optional[datetime] = None

    def close_burst() -> None:
        nonlocal burst_ts, burst_count
        if burst_ts is not None and burst_count >= burst_n:
            s.findings.append(
                Finding(
                    kind="timeout_burst",
                    ts=burst_ts,
                    detail=f"{burst_count} socket/ping timeouts in the same second",
                    wall_s=0.0,
                )
            )
        burst_ts = None
        burst_count = 0

    def note_timeout(ts: datetime) -> None:
        nonlocal burst_ts, burst_count
        if burst_ts is not None and ts == burst_ts:
            burst_count += 1
        else:
            close_burst()
            burst_ts = ts
            burst_count = 1

    for line in lines:
        mts = TS_PREFIX.match(line)
        if mts:
            last_line_ts = parse_ts(mts.group(1))
            if s.ts_first is None:
                s.ts_first = last_line_ts
            s.ts_last = last_line_ts

        if VERSION_RE.match(line):
            s.restarts += 1
            last_tip_ts = None
            last_tip_h = None
            close_burst()
            continue

        m = TIP_RE.match(line)
        if m:
            ts = parse_ts(m.group(1))
            height = int(m.group(2))
            header = parse_ts(m.group(3))
            s.tips += 1
            if s.height_first is None:
                s.height_first = height
            s.height_last = height
            s.tip_ts_last = ts
            log_dt = None if last_tip_ts is None else (ts - last_tip_ts).total_seconds()
            if log_dt is not None:
                if log_dt > s.max_gap_s:
                    s.max_gap_s = log_dt
                if log_dt >= gap_s:
                    s.findings.append(
                        Finding(
                            kind="tip_gap",
                            ts=ts,
                            detail=(
                                f"UpdateTip gap {int(log_dt)}s "
                                f"(~{log_dt / POW_TARGET_S:.1f} x {POW_TARGET_S}s spacing) "
                                f"h {last_tip_h} -> {height}"
                            ),
                            wall_s=log_dt,
                            height=height,
                            height_prev=last_tip_h,
                        )
                    )
            lag = (ts - header).total_seconds()
            if lag >= header_lag_s:
                follow = (
                    last_tip_h is not None
                    and height == last_tip_h + 1
                    and log_dt is not None
                    and log_dt >= 30
                )
                if follow:
                    s.findings.append(
                        Finding(
                            kind="header_lag",
                            ts=ts,
                            detail=(
                                f"log {ts.strftime('%Y-%m-%d %H:%M:%S')} vs "
                                f"header date= {header.strftime('%Y-%m-%d %H:%M:%S')} "
                                f"({int(lag)}s)"
                            ),
                            wall_s=lag,
                            height=height,
                        )
                    )
                else:
                    s.header_lag_catchup += 1
            last_tip_ts = ts
            last_tip_h = height
            continue

        m = TIMEOUT_RE.match(line)
        if m:
            ts = parse_ts(m.group(1))
            secs = float(m.group(3))
            s.timeouts += 1
            if secs > s.timeout_max_s:
                s.timeout_max_s = secs
            note_timeout(ts)
            continue

        m = PING_RE.match(line)
        if m:
            ts = parse_ts(m.group(1))
            secs = float(m.group(2))
            s.ping_timeouts += 1
            if secs > s.timeout_max_s:
                s.timeout_max_s = secs
            note_timeout(ts)
            continue

        m = CLOCK_WARN_RE.match(line)
        if m:
            s.findings.append(
                Finding(
                    kind="clock_warn",
                    ts=parse_ts(m.group(1)),
                    detail="peer median clock disagrees with local clock",
                )
            )
            continue

        m = NTIME_RE.match(line)
        if m:
            s.ntime_offsets.append(int(m.group(2)))
            continue

        if EXPIRED_RE.match(line):
            s.expired_tx += 1
            continue
        if BAN_RE.match(line):
            s.bans += 1
            s.misbehaving += 1
            continue
        if MISBEHAVE_RE.match(line):
            s.misbehaving += 1
            continue
        if LOGICAL_TS_RE.match(line):
            s.logical_ts_bumps += 1
            continue

    close_burst()

    if (
        last_line_ts is not None
        and s.tip_ts_last is not None
        and last_line_ts != s.tip_ts_last
    ):
        silent = (last_line_ts - s.tip_ts_last).total_seconds()
        if silent >= gap_s:
            s.findings.append(
                Finding(
                    kind="tip_silent",
                    ts=last_line_ts,
                    detail=(
                        f"no UpdateTip for {int(silent)}s while the log still "
                        f"wrote other lines (last tip h={s.height_last})"
                    ),
                    wall_s=silent,
                    height=s.height_last,
                )
            )
    return s


def format_report(s: Scan, gap_s: float, paths: list[Path]) -> str:
    kinds = Counter(f.kind for f in s.findings)
    stall_kinds = ("tip_gap", "tip_silent", "timeout_burst", "clock_warn")
    n_stall = sum(kinds[k] for k in stall_kinds)
    lines = [
        "stall_check",
        f"  files: {', '.join(str(p) for p in paths) or '-'}",
        f"  window: {s.ts_first} .. {s.ts_last}" if s.ts_first else "  window: (no timestamps)",
        f"  UpdateTip: {s.tips}  height {s.height_first} -> {s.height_last}  "
        f"max_gap_s={int(s.max_gap_s)}  gap_s={int(gap_s)}",
        f"  timeouts: socket={s.timeouts} ping={s.ping_timeouts} "
        f"max_reported_s={int(s.timeout_max_s)}  bursts={kinds['timeout_burst']}",
        f"  notes: expired_tx={s.expired_tx} misbehaving={s.misbehaving} "
        f"bans={s.bans} logical_ts_bump={s.logical_ts_bumps} restarts={s.restarts} "
        f"header_lag_catchup={s.header_lag_catchup}",
    ]
    if s.ntime_offsets:
        last = s.ntime_offsets[-1]
        lines.append(
            f"  nTimeOffset last={last}s ({last // 60:+d} min)  samples={len(s.ntime_offsets)}"
        )
    lines.append(f"  findings: {n_stall} stall-class  {len(s.findings)} total")
    stall_first = [f for f in s.findings if f.kind in stall_kinds]
    rest = [f for f in s.findings if f.kind not in stall_kinds]
    shown = stall_first + rest
    if not shown:
        lines.append("  - none")
    for f in shown:
        h = f" h={f.height}" if f.height is not None else ""
        lines.append(
            f"  - {f.kind}  {f.ts.strftime('%Y-%m-%d %H:%M:%S')}{h}  {f.detail}"
        )
    return "\n".join(lines) + "\n"


def scan_to_json(s: Scan, gap_s: float, paths: list[Path]) -> dict:
    return {
        "files": [str(p) for p in paths],
        "gap_s": gap_s,
        "pow_target_s": POW_TARGET_S,
        "tips": s.tips,
        "height_first": s.height_first,
        "height_last": s.height_last,
        "ts_first": None if s.ts_first is None else s.ts_first.strftime("%Y-%m-%d %H:%M:%S"),
        "ts_last": None if s.ts_last is None else s.ts_last.strftime("%Y-%m-%d %H:%M:%S"),
        "max_gap_s": s.max_gap_s,
        "timeouts": s.timeouts,
        "ping_timeouts": s.ping_timeouts,
        "timeout_max_s": s.timeout_max_s,
        "expired_tx": s.expired_tx,
        "misbehaving": s.misbehaving,
        "bans": s.bans,
        "logical_ts_bumps": s.logical_ts_bumps,
        "header_lag_catchup": s.header_lag_catchup,
        "restarts": s.restarts,
        "ntime_offsets": s.ntime_offsets,
        "findings": [
            {
                "kind": f.kind,
                "ts": f.ts.strftime("%Y-%m-%d %H:%M:%S"),
                "detail": f.detail,
                "wall_s": f.wall_s,
                "height": f.height,
                "height_prev": f.height_prev,
            }
            for f in s.findings
        ],
    }


def _kinds(s: Scan) -> set[str]:
    return {f.kind for f in s.findings}


def run_self_test() -> int:
    gap = 900.0
    lag = 1800.0
    burst = 3

    follow = """\
2026-08-17 17:00:00 UpdateTip: new best=aa height=100 log2_work=1 tx=1 date=2026-08-17 17:00:00 progress=1 cache=1.0MiB(1tx)
2026-08-17 17:02:00 UpdateTip: new best=bb height=101 log2_work=1 tx=1 date=2026-08-17 17:02:00 progress=1 cache=1.0MiB(1tx)
2026-08-17 17:04:00 UpdateTip: new best=cc height=102 log2_work=1 tx=1 date=2026-08-17 17:04:00 progress=1 cache=1.0MiB(1tx)
"""
    s = scan_lines(follow.splitlines(), gap, lag, burst)
    assert s.tips == 3 and s.max_gap_s == 120 and not s.findings, s

    stalled = """\
2026-08-17 17:00:00 UpdateTip: new best=aa height=100 log2_work=1 tx=1 date=2026-08-17 17:00:00 progress=1 cache=1.0MiB(1tx)
2026-08-17 17:20:00 UpdateTip: new best=bb height=101 log2_work=1 tx=1 date=2026-08-17 17:20:00 progress=1 cache=1.0MiB(1tx)
"""
    s = scan_lines(stalled.splitlines(), gap, lag, burst)
    assert "tip_gap" in _kinds(s) and abs(s.max_gap_s - 1200) < 1e-6, s.findings

    restart = """\
2026-08-17 17:00:00 UpdateTip: new best=aa height=100 log2_work=1 tx=1 date=2026-08-17 17:00:00 progress=1 cache=1.0MiB(1tx)
2026-08-17 17:20:00 Zero version v4.0.1 (2026-01-01)
2026-08-17 17:20:05 UpdateTip: new best=bb height=101 log2_work=1 tx=1 date=2026-08-17 17:20:05 progress=1 cache=1.0MiB(1tx)
"""
    s = scan_lines(restart.splitlines(), gap, lag, burst)
    assert s.restarts == 1 and "tip_gap" not in _kinds(s), s.findings

    two_to = """\
2026-08-17 17:52:20 socket receive timeout: 1333s
2026-08-17 17:52:20 socket receive timeout: 1333s
"""
    s = scan_lines(two_to.splitlines(), gap, lag, burst)
    assert s.timeouts == 2 and "timeout_burst" not in _kinds(s), s.findings

    three_to = two_to + "2026-08-17 17:52:20 ping timeout: 1200.0s\n"
    s = scan_lines(three_to.splitlines(), gap, lag, burst)
    assert "timeout_burst" in _kinds(s), s.findings

    hdr = """\
2026-08-17 19:44:50 UpdateTip: new best=aa height=200 log2_work=1 tx=1 date=2026-08-17 19:00:00 progress=1 cache=1.0MiB(1tx)
"""
    s = scan_lines(hdr.splitlines(), gap, lag, burst)
    assert "header_lag" not in _kinds(s) and s.header_lag_catchup == 1, s

    follow_lag = """\
2026-08-17 19:00:00 UpdateTip: new best=aa height=200 log2_work=1 tx=1 date=2026-08-17 19:00:00 progress=1 cache=1.0MiB(1tx)
2026-08-17 19:02:00 UpdateTip: new best=bb height=201 log2_work=1 tx=1 date=2026-08-17 18:20:00 progress=1 cache=1.0MiB(1tx)
"""
    s = scan_lines(follow_lag.splitlines(), gap, lag, burst)
    assert "header_lag" in _kinds(s), s.findings

    catchup = """\
2026-08-17 15:43:40 UpdateTip: new best=aa height=200 log2_work=1 tx=1 date=2026-08-17 14:00:00 progress=1 cache=1.0MiB(1tx)
2026-08-17 15:43:40 UpdateTip: new best=bb height=201 log2_work=1 tx=1 date=2026-08-17 14:02:00 progress=1 cache=1.0MiB(1tx)
2026-08-17 15:43:40 UpdateTip: new best=cc height=202 log2_work=1 tx=1 date=2026-08-17 14:04:00 progress=1 cache=1.0MiB(1tx)
"""
    s = scan_lines(catchup.splitlines(), gap, lag, burst)
    assert "header_lag" not in _kinds(s) and s.header_lag_catchup == 3, s

    silent = """\
2026-08-17 17:00:00 UpdateTip: new best=aa height=100 log2_work=1 tx=1 date=2026-08-17 17:00:00 progress=1 cache=1.0MiB(1tx)
2026-08-17 17:20:00 receive version message: /Ambrym:3.3.1/: version 170009, blocks=100, us=1.2.3.4:1, peer=1
"""
    s = scan_lines(silent.splitlines(), gap, lag, burst)
    assert "tip_silent" in _kinds(s), s.findings

    clock = """\
2026-08-17 17:00:00 *** Warning: Please check that your computer's date and time are correct! If your clock is wrong Zero will not work properly.
"""
    s = scan_lines(clock.splitlines(), gap, lag, burst)
    assert "clock_warn" in _kinds(s), s.findings

    notes = """\
2026-08-17 17:52:46 ERROR: ContextualCheckTransaction(): transaction is expired
2026-08-17 17:52:46 Misbehaving: 62.171.132.104:23801 (0 -> 10)
2026-08-17 19:44:50 ConnectBlock: Previous logical timestamp is newer Actual[1] prevLogical[2] Logical[3]
"""
    s = scan_lines(notes.splitlines(), gap, lag, burst)
    assert s.expired_tx == 1 and s.misbehaving == 1 and s.logical_ts_bumps == 1
    assert not s.findings, s.findings

    with tempfile.TemporaryDirectory(prefix="stall-check-") as td:
        p = Path(td) / "debug.log"
        p.write_text(follow)
        scanned = scan_lines(iter_lines([p]), gap, lag, burst)
        assert scanned.tips == 3 and not scanned.findings

    print("self-test OK")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    debuglog.add_log_input_args(p)
    p.add_argument(
        "--gap-s",
        type=float,
        default=900,
        help="UpdateTip wall gap / tip-silent threshold (default 900)",
    )
    p.add_argument(
        "--header-lag-s",
        type=float,
        default=1800,
        help="Flag when log time minus header date= exceeds this (default 1800)",
    )
    p.add_argument(
        "--burst",
        type=int,
        default=3,
        help="Same-second socket/ping timeouts that count as a burst (default 3)",
    )
    p.add_argument("--json", action="store_true", help="JSON object on stdout")
    p.add_argument("--self-test", action="store_true")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.self_test:
        return run_self_test()

    paths = debuglog.paths_from_args(args)

    s = scan_lines(iter_lines(paths), args.gap_s, args.header_lag_s, args.burst)
    if args.json:
        print(json.dumps(scan_to_json(s, args.gap_s, paths), sort_keys=True, indent=2))
    else:
        sys.stdout.write(format_report(s, args.gap_s, paths))

    stall = any(
        f.kind in ("tip_gap", "tip_silent", "timeout_burst", "clock_warn")
        for f in s.findings
    )
    return 1 if stall else 0


if __name__ == "__main__":
    sys.exit(main())
