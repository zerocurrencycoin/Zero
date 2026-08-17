#!/usr/bin/env python3
"""Filter-then-process zerod debug.log markers into Measures.md vocabulary.

Read-only on logs. Does not launch zerod. Log path spec is shared with
stall_check.py (contrib/perf/debuglog.py): --datadir, --rotated, --log,
positional file/dir/glob. Launchers that write still refuse the live
datadir unless ZERO_PERF_ALLOW_LIVE_DATADIR=1.

Usage:
  python3 contrib/perf/extract_measures.py --datadir "$LAB" \\
      --run-id tiny-... --op-class reindex --no-wallet --env lab \\
      --jsonl test-logs/tiny.jsonl --csv test-logs/measures_tiny.csv

  python3 contrib/perf/extract_measures.py --elapsed-heights LOG H0 H1
  python3 contrib/perf/extract_measures.py --self-test
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

_PERF_DIR = Path(__file__).resolve().parent
if str(_PERF_DIR) not in sys.path:
    sys.path.insert(0, str(_PERF_DIR))
import debuglog  # noqa: E402

TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
TIP_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+UpdateTip:.*"
    r"(?:new height=|height=)(\d+).*?(?:cache=([0-9.]+)MiB\((\d+)tx\))?"
)
INIT_MSG_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+init message:\s*(.*)$"
)
CACHE_CFG_LINE_RE = re.compile(
    r"^(?:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s+)?\*\s+Using\s+([0-9.]+)MiB\s+for\s+"
    r"(block index database|chain state database|in-memory UTXO set)"
)
REINDEX_SOURCE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+Reindex source:\s*(.*)$"
)
REINDEX_PROGRESS_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+Reindex progress:\s*(.*)$"
)
REINDEX_FINISHED_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+Reindexing finished"
)
WITNESS_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+Building Witnesses for block\s+(\d+)"
)
DONE_LOADING_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(?:init message:\s*)?Done loading"
)
READ_FD_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+ReadFdCache:"
)
BENCH_CONNECT_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+- Connect block:\s*([0-9.]+)ms"
)
RPC_WARMUP_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*(?:-28|Loading block index|Verifying wallet)",
    re.IGNORECASE,
)
SEGMENT_START_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(?:"
    r"init message:\s*Initializing|"
    r"Zero\s+version|"
    r"\s*$"  # unused; kept for clarity
    r")"
)

CSV_FIELDS = [
    "run_id",
    "segment",
    "op_class",
    "metric",
    "value",
    "unit",
    "height_start",
    "height_end",
    "wall_s",
    "tools",
    "type",
    "source",
    "wallet",
    "dbcache",
    "env",
    "extra",
]


def parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


@dataclass
class Event:
    ts: datetime
    marker: str
    source: str
    height: Optional[int] = None
    text: str = ""
    cache_mib: Optional[float] = None
    cache_tx: Optional[int] = None
    ms: Optional[float] = None
    keep: bool = True  # False when tip sampled out of JSONL


@dataclass
class Segment:
    index: int
    start_ts: Optional[datetime] = None
    events: list[Event] = field(default_factory=list)
    cache_budgets: dict[str, float] = field(default_factory=dict)


def classify_line(line: str) -> Optional[Event]:
    line = line.rstrip("\n")
    if not line:
        return None

    m = TIP_RE.match(line)
    if m:
        cache_mib = float(m.group(3)) if m.group(3) else None
        cache_tx = int(m.group(4)) if m.group(4) else None
        return Event(
            ts=parse_ts(m.group(1)),
            marker="update_tip" if cache_mib is None else "cache_tip",
            source=line[:200],
            height=int(m.group(2)),
            cache_mib=cache_mib,
            cache_tx=cache_tx,
        )

    m = INIT_MSG_RE.match(line)
    if m:
        msg = m.group(2).strip()
        if msg == "Done loading":
            return Event(ts=parse_ts(m.group(1)), marker="init_done_loading", source=line[:200], text=msg)
        return Event(ts=parse_ts(m.group(1)), marker="init_message", source=line[:200], text=msg)

    m = DONE_LOADING_RE.match(line)
    if m and "init message:" not in line:
        return Event(ts=parse_ts(m.group(1)), marker="init_done_loading", source=line[:200])

    if "Cache configuration:" in line:
        ts_m = TS_RE.match(line)
        if ts_m:
            return Event(ts=parse_ts(ts_m.group(1)), marker="cache_config", source=line[:200])

    m = CACHE_CFG_LINE_RE.match(line.strip())
    if m:
        ts_m = TS_RE.match(line)
        return Event(
            ts=parse_ts(ts_m.group(1)) if ts_m else datetime.min,
            marker="cache_config_budget",
            source=line[:200],
            text=m.group(2),
            cache_mib=float(m.group(1)),
        )

    m = REINDEX_SOURCE_RE.match(line)
    if m:
        return Event(ts=parse_ts(m.group(1)), marker="reindex_source", source=line[:200], text=m.group(2).strip())

    m = REINDEX_PROGRESS_RE.match(line)
    if m:
        return Event(ts=parse_ts(m.group(1)), marker="reindex_progress", source=line[:200], text=m.group(2).strip())

    m = REINDEX_FINISHED_RE.match(line)
    if m:
        return Event(ts=parse_ts(m.group(1)), marker="reindex_finished", source=line[:200])

    m = WITNESS_RE.match(line)
    if m:
        return Event(ts=parse_ts(m.group(1)), marker="building_witnesses", source=line[:200], height=int(m.group(2)))

    m = READ_FD_RE.match(line)
    if m:
        return Event(ts=parse_ts(m.group(1)), marker="read_fd_cache", source=line[:200])

    m = BENCH_CONNECT_RE.match(line)
    if m:
        return Event(ts=parse_ts(m.group(1)), marker="bench_connect", source=line[:200], ms=float(m.group(2)))

    return None


def is_segment_start(line: str) -> bool:
    return bool(
        re.match(
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s+init message:\s*Initializing",
            line,
        )
    ) or bool(
        re.match(
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s+Zero version",
            line,
        )
    )


def iter_log_lines(paths: Iterable[Path]) -> Iterator[tuple[Path, str]]:
    for path in paths:
        with open(path, errors="replace") as f:
            for line in f:
                yield path, line


def parse_logs(
    paths: list[Path],
    sample_tip: int = 100,
    include_bench: bool = False,
) -> list[Segment]:
    segments: list[Segment] = []
    seg = Segment(index=0)
    segments.append(seg)
    last_ts: Optional[datetime] = None
    tip_i = 0

    for _path, line in iter_log_lines(paths):
        if is_segment_start(line):
            if seg.events or seg.start_ts:
                seg = Segment(index=len(segments))
                segments.append(seg)
            ts_m = TS_RE.match(line)
            if ts_m:
                seg.start_ts = parse_ts(ts_m.group(1))
                last_ts = seg.start_ts

        ev = classify_line(line)
        if ev is None:
            continue
        if ev.marker == "bench_connect" and not include_bench:
            continue
        if ev.marker == "cache_config_budget":
            if ev.ts == datetime.min and last_ts is not None:
                ev.ts = last_ts
            elif ev.ts != datetime.min:
                last_ts = ev.ts
            key = {
                "block index database": "block_index_mib",
                "chain state database": "chainstate_mib",
                "in-memory UTXO set": "utxo_mib",
            }.get(ev.text or "", ev.text or "other")
            if ev.cache_mib is not None:
                seg.cache_budgets[key] = ev.cache_mib
            continue
        if ev.ts != datetime.min:
            last_ts = ev.ts
        if not seg.start_ts:
            seg.start_ts = ev.ts

        if ev.marker in ("update_tip", "cache_tip"):
            tip_i += 1
            # Always keep first tip; sample thereafter; always keep for reduce
            # via a parallel full tip list stored lightly
            if sample_tip > 1 and tip_i > 1 and (tip_i % sample_tip) != 0:
                ev.keep = False
            # Normalize marker for vocabulary: both are tip progress; cache_tip
            # is the same UpdateTip line with cache= field.
            if ev.marker == "cache_tip":
                # Emit as update_tip for op timing; cache fields retained
                ev.marker = "update_tip"

        seg.events.append(ev)

    kept = [s for s in segments if s.events]
    for i, s in enumerate(kept):
        s.index = i
    return kept


def tips_in_segment(seg: Segment) -> list[Event]:
    return [e for e in seg.events if e.marker == "update_tip" and e.height is not None]


def measure_row(
    run_id: str,
    segment: int,
    op_class: str,
    metric: str,
    value: float,
    unit: str,
    *,
    height_start: Optional[int] = None,
    height_end: Optional[int] = None,
    wall_s: Optional[float] = None,
    tools: str = "debug_log",
    type_: str = "campaign",
    source: str = "",
    wallet: Optional[bool] = None,
    dbcache: Optional[int] = None,
    env: str = "lab",
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "segment": segment,
        "op_class": op_class,
        "metric": metric,
        "value": round(value, 6) if isinstance(value, float) else value,
        "unit": unit,
        "height_start": height_start,
        "height_end": height_end,
        "wall_s": None if wall_s is None else round(wall_s, 3),
        "tools": tools,
        "type": type_,
        "source": source,
        "wallet": wallet,
        "dbcache": dbcache,
        "env": env,
        "extra": extra or {},
    }


def reduce_segment(
    seg: Segment,
    run_id: str,
    *,
    op_class_hint: Optional[str],
    wallet: Optional[bool],
    dbcache: Optional[int],
    env: str,
    source_label: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    evs = seg.events
    tips = tips_in_segment(seg)

    # Init: first init_message -> init_done_loading
    inits = [e for e in evs if e.marker == "init_message"]
    dones = [e for e in evs if e.marker == "init_done_loading"]
    if inits and dones and dones[0].ts >= inits[0].ts:
        wall = (dones[0].ts - inits[0].ts).total_seconds()
        rows.append(
            measure_row(
                run_id,
                seg.index,
                "init",
                "wall_s",
                wall,
                "s",
                wall_s=wall,
                type_="spot",
                source=source_label,
                wallet=wallet,
                dbcache=dbcache,
                env=env,
                extra={"from": inits[0].text, "to": "Done loading"},
            )
        )

    # Reindex: source -> finished
    sources = [e for e in evs if e.marker == "reindex_source"]
    finished = [e for e in evs if e.marker == "reindex_finished"]
    if sources and finished and finished[0].ts >= sources[0].ts:
        wall = (finished[0].ts - sources[0].ts).total_seconds()
        # Heights from tips between those bounds
        mid = [t for t in tips if sources[0].ts <= t.ts <= finished[0].ts]
        h0 = mid[0].height if mid else None
        h1 = mid[-1].height if mid else None
        rows.append(
            measure_row(
                run_id,
                seg.index,
                "reindex",
                "wall_s",
                wall,
                "s",
                height_start=h0,
                height_end=h1,
                wall_s=wall,
                source=source_label,
                wallet=wallet,
                dbcache=dbcache,
                env=env,
                extra={"reindex_source": sources[0].text},
            )
        )
        if h0 is not None and h1 is not None and wall > 0 and h1 > h0:
            rate = (h1 - h0) / wall
            rows.append(
                measure_row(
                    run_id,
                    seg.index,
                    "reindex",
                    "height_per_s",
                    rate,
                    "h/s",
                    height_start=h0,
                    height_end=h1,
                    wall_s=wall,
                    source=source_label,
                    wallet=wallet,
                    dbcache=dbcache,
                    env=env,
                )
            )

    # Witness rebuild: first -> last building_witnesses
    wits = [e for e in evs if e.marker == "building_witnesses"]
    if len(wits) >= 2:
        wall = (wits[-1].ts - wits[0].ts).total_seconds()
        rows.append(
            measure_row(
                run_id,
                seg.index,
                "witness",
                "wall_s",
                wall,
                "s",
                height_start=wits[0].height,
                height_end=wits[-1].height,
                wall_s=wall,
                type_="spot",
                source=source_label,
                wallet=wallet,
                dbcache=dbcache,
                env=env,
                extra={"n_lines": len(wits)},
            )
        )
    elif len(wits) == 1:
        rows.append(
            measure_row(
                run_id,
                seg.index,
                "witness",
                "wall_s",
                0.0,
                "s",
                height_start=wits[0].height,
                height_end=wits[0].height,
                wall_s=0.0,
                type_="spot",
                source=source_label,
                wallet=wallet,
                dbcache=dbcache,
                env=env,
                extra={"n_lines": 1, "note": "single marker only"},
            )
        )

    # Tip window rate (catchup / connect). Skip when reindex source→finished
    # already produced the authoritative window for this segment.
    if len(tips) >= 2 and not (sources and finished):
        h0, h1 = tips[0].height, tips[-1].height
        wall = (tips[-1].ts - tips[0].ts).total_seconds()
        op = op_class_hint or (
            "catchup"
            if dones
            else "connect"
        )
        if h0 is not None and h1 is not None and wall > 0 and h1 > h0:
            rows.append(
                measure_row(
                    run_id,
                    seg.index,
                    op,
                    "height_per_s",
                    (h1 - h0) / wall,
                    "h/s",
                    height_start=h0,
                    height_end=h1,
                    wall_s=wall,
                    type_="spot",
                    source=source_label,
                    wallet=wallet,
                    dbcache=dbcache,
                    env=env,
                    extra={"window": "first_last_update_tip"},
                )
            )
            rows.append(
                measure_row(
                    run_id,
                    seg.index,
                    op,
                    "wall_s",
                    wall,
                    "s",
                    height_start=h0,
                    height_end=h1,
                    wall_s=wall,
                    type_="spot",
                    source=source_label,
                    wallet=wallet,
                    dbcache=dbcache,
                    env=env,
                    extra={"window": "first_last_update_tip"},
                )
            )
            rows.append(
                measure_row(
                    run_id,
                    seg.index,
                    op,
                    "ms_per_block",
                    1000.0 * wall / (h1 - h0),
                    "ms/blk",
                    height_start=h0,
                    height_end=h1,
                    wall_s=wall,
                    type_="spot",
                    source=source_label,
                    wallet=wallet,
                    dbcache=dbcache,
                    env=env,
                )
            )

    if seg.cache_budgets:
        for k, v in seg.cache_budgets.items():
            rows.append(
                measure_row(
                    run_id,
                    seg.index,
                    "cache",
                    f"{k}",
                    v,
                    "MiB",
                    type_="spot",
                    source=source_label,
                    wallet=wallet,
                    dbcache=dbcache,
                    env=env,
                    extra={"budget": k},
                )
            )

    return rows


def events_to_jsonl_objs(
    segments: list[Segment],
    run_id: str,
    meta: dict[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for seg in segments:
        for ev in seg.events:
            if not ev.keep:
                continue
            out.append(
                {
                    "run_id": run_id,
                    "segment": seg.index,
                    "ts": ev.ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "log_marker": ev.marker,
                    "height": ev.height,
                    "cache_mib": ev.cache_mib,
                    "cache_tx": ev.cache_tx,
                    "ms": ev.ms,
                    "text": ev.text or None,
                    **meta,
                }
            )
    return out


def elapsed_between_heights(log_path: Path, h_start: int, h_end: int) -> Optional[float]:
    """Exact UpdateTip wall seconds between first sightings of h_start and h_end."""
    pat = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+UpdateTip:.*?(?:new height=|height=)(\d+)"
    )
    t_start = t_end = None
    with open(log_path, errors="replace") as f:
        for line in f:
            m = pat.match(line)
            if not m:
                continue
            h = int(m.group(2))
            if h == h_start and t_start is None:
                t_start = parse_ts(m.group(1))
            if h == h_end:
                t_end = parse_ts(m.group(1))
    if t_start is None or t_end is None:
        return None
    return (t_end - t_start).total_seconds()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = dict(r)
            if isinstance(out.get("extra"), dict):
                out["extra"] = json.dumps(out["extra"], sort_keys=True)
            if out.get("wallet") is not None:
                out["wallet"] = "1" if out["wallet"] else "0"
            w.writerow({k: out.get(k, "") for k in CSV_FIELDS})


def write_jsonl(path: Path, objs: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for o in objs:
            f.write(json.dumps(o, sort_keys=True) + "\n")


def markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_No measure rows._\n"
    cols = [
        "run_id",
        "segment",
        "op_class",
        "metric",
        "value",
        "unit",
        "height_start",
        "height_end",
        "wall_s",
        "env",
    ]
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for r in rows:
        lines.append(
            "| "
            + " | ".join(
                "-" if r.get(c) is None else str(r.get(c)) for c in cols
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def run_self_test() -> int:
    sample = """\
2026-08-11 01:00:00 init message: Initializing...
2026-08-11 01:00:01 Cache configuration:
2026-08-11 01:00:01 * Using 100.0MiB for block index database
2026-08-11 01:00:01 * Using 50.0MiB for chain state database
2026-08-11 01:00:01 * Using 200.0MiB for in-memory UTXO set
2026-08-11 01:00:02 init message: Loading block index...
2026-08-11 01:00:10 init message: Done loading
2026-08-11 01:00:11 Reindex source: -reindex argument
2026-08-11 01:00:12 UpdateTip: new best=abc height=1 log2_work=1 tx=1 date=2026-08-11 01:00:12 progress=0.1 cache=0.1MiB(1tx)
2026-08-11 01:00:22 UpdateTip: new best=def height=101 log2_work=1 tx=101 date=2026-08-11 01:00:22 progress=0.5 cache=0.2MiB(2tx)
2026-08-11 01:01:12 UpdateTip: new best=ghi height=1001 log2_work=1 tx=1001 date=2026-08-11 01:01:12 progress=1.0 cache=0.3MiB(3tx)
2026-08-11 01:01:13 Reindexing finished
2026-08-11 01:01:14 Building Witnesses for block 100
2026-08-11 01:01:24 Building Witnesses for block 200
"""
    with tempfile.TemporaryDirectory(prefix="extract-measures-") as td:
        log = Path(td) / "debug.log"
        log.write_text(sample)
        segs = parse_logs([log], sample_tip=1)
        rows = []
        for seg in segs:
            rows.extend(
                reduce_segment(
                    seg,
                    "selftest",
                    op_class_hint="reindex",
                    wallet=False,
                    dbcache=800,
                    env="lab",
                    source_label=str(log),
                )
            )
        # Expect init wall 10s, reindex wall 62s, height 1->1001, witness 10s
        by = {(r["op_class"], r["metric"]): r for r in rows}
        assert ("init", "wall_s") in by, by.keys()
        assert abs(by[("init", "wall_s")]["value"] - 10.0) < 1e-6
        assert abs(by[("reindex", "wall_s")]["value"] - 62.0) < 1e-6
        assert by[("reindex", "height_per_s")]["height_start"] == 1
        assert by[("reindex", "height_per_s")]["height_end"] == 1001
        assert abs(by[("witness", "wall_s")]["value"] - 10.0) < 1e-6
        elapsed = elapsed_between_heights(log, 1, 1001)
        assert elapsed is not None and abs(elapsed - 60.0) < 1e-6, elapsed
        budgets = [r for r in rows if r["op_class"] == "cache"]
        assert len(budgets) == 3, budgets
    print("self-test OK")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    debuglog.add_log_input_args(p)
    p.add_argument("--run-id", default="", help="Default: UTC stamp")
    p.add_argument(
        "--op-class",
        default="",
        help="Hint when markers ambiguous (reindex|ibd|catchup|init|witness)",
    )
    p.add_argument(
        "--sample-tip",
        type=int,
        default=100,
        help="Keep every Nth UpdateTip in JSONL (1=all); reduce always uses first/last",
    )
    p.add_argument("--wallet", dest="wallet", action="store_true", default=None)
    p.add_argument("--no-wallet", dest="wallet", action="store_false")
    p.add_argument("--dbcache", type=int, default=None)
    p.add_argument("--env", default="lab", help="insight|wallet|lab|...")
    p.add_argument("--jsonl", type=Path, default=None)
    p.add_argument("--csv", type=Path, default=None)
    p.add_argument("--md", action="store_true", default=True)
    p.add_argument("--no-md", action="store_false", dest="md")
    p.add_argument(
        "--bench",
        action="store_true",
        help="Also ingest -debug=bench Connect block lines",
    )
    p.add_argument(
        "--elapsed-heights",
        nargs=3,
        metavar=("LOG", "H0", "H1"),
        help="Print UpdateTip elapsed seconds between heights (or NA)",
    )
    p.add_argument("--self-test", action="store_true")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.self_test:
        return run_self_test()

    if args.elapsed_heights:
        log_s, h0_s, h1_s = args.elapsed_heights
        elapsed = elapsed_between_heights(Path(log_s), int(h0_s), int(h1_s))
        print("NA" if elapsed is None else elapsed)
        return 0

    paths = debuglog.paths_from_args(args)
    if args.datadir and debuglog.is_default_runtime_datadir(args.datadir) and args.env == "lab":
        print(
            "note: default runtime datadir with --env=lab; "
            "set --env insight|wallet before citing Measures rows",
            file=sys.stderr,
        )
    elif any(debuglog.is_default_runtime_datadir(p) for p in paths) and args.env == "lab":
        print(
            "note: log path is under the default runtime datadir with --env=lab; "
            "set --env insight|wallet before citing Measures rows",
            file=sys.stderr,
        )

    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    op_hint = args.op_class or None
    source_label = str(args.datadir) if args.datadir else ",".join(str(p) for p in paths)

    segments = parse_logs(paths, sample_tip=max(1, args.sample_tip), include_bench=args.bench)
    rows: list[dict[str, Any]] = []
    for seg in segments:
        rows.extend(
            reduce_segment(
                seg,
                run_id,
                op_class_hint=op_hint,
                wallet=args.wallet,
                dbcache=args.dbcache,
                env=args.env,
                source_label=source_label,
            )
        )

    meta = {
        "tools": "debug_log",
        "wallet": args.wallet,
        "dbcache": args.dbcache,
        "env": args.env,
        "op_class_hint": op_hint,
    }
    events = events_to_jsonl_objs(segments, run_id, meta)

    if args.jsonl:
        write_jsonl(args.jsonl, events)
        print(f"Wrote {args.jsonl} ({len(events)} events)", file=sys.stderr)
    if args.csv:
        write_csv(args.csv, rows)
        print(f"Wrote {args.csv} ({len(rows)} rows)", file=sys.stderr)
    if args.md:
        print(f"# measures {run_id}")
        print()
        print(f"segments={len(segments)} events_kept={len(events)} rows={len(rows)}")
        print()
        print(markdown_table(rows))

    return 0


if __name__ == "__main__":
    sys.exit(main())
