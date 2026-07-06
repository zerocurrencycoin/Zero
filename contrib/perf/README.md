# perf

Scripts supporting the `zerod` sync performance investigation documented in
`Perf.md` at the repo root. Read that file first — it has the methodology
and the reasoning these scripts implement; this README is just usage.

## capture_sequence.sh

Runs a long `-reindex` (or any long-running `zerod` process) under repeated
Instruments Time Profiler captures: capture for N seconds, idle until the
next periodic boundary, repeat until the node exits. Each capture's trace,
XML export, exact debug.log snapshot, and system-state snapshot land in
their own `capture_NNN/` subdirectory.

```bash
rm -rf reindex-profile/datadir
rsync -a --exclude='chainstate' "/Users/walter/Library/Application Support/Zero/" reindex-profile/datadir/
contrib/perf/capture_sequence.sh reindex-profile/datadir reindex-profile/captures 1200 300
```

Arguments: `<datadir> <out_dir> [period_secs=1200] [capture_secs=300] [max_captures=0]`.
`period_secs` is measured from sequence start, not from the end of the
previous capture, so captures land on a fixed schedule (e.g. every 20
minutes) rather than drifting later each cycle as XML export or idle-loop
overhead accumulates.

## decode_captures.py

Decodes a `capture_sequence.sh` output directory into a combined report:
per-capture CPU bucket breakdown (reusing `reindex-profile/tools/bucket_profile.py`'s
xctrace-export parser directly, not a reimplementation), the exact block-height
range each capture covered (derived from the trace's own timestamped
`<start-date>` cross-referenced against the debug.log snapshot — see
`Perf.md` §1 for why this specific method, not wall-clock guessing, is
required), and an aggregate breakdown across the whole run.

```bash
python3 contrib/perf/decode_captures.py reindex-profile/captures --json reindex-profile/captures_report.json
```

Pass `--rpc` to also sample a handful of blocks per capture via `zero-cli
getblock <hash> 2` for a transparent/Sprout/Sapling transaction-type mix —
needs a datadir with a currently-running (or previously fully-reindexed)
node to query; skipped by default since captures are usually decoded after
the node has moved on or exited.

## bench_matrix.sh

Repeated-trial A/B throughput benchmark for `ZERO_FDCACHE` build flags
(`-perffdcache`, `-perfbufsize`) against `-reindex` and, given a
`bootstrap.dat` path, `-loadblock` (bootstrap import). Every trial resets to
a fresh scratch datadir, warms up to a fixed height (unmeasured), then times
a fixed block range using `debug.log`'s exact `UpdateTip` timestamps — not
fixed wall-clock windows, which would measure different chain content
between runs and make throughput incomparable.

```bash
contrib/perf/bench_matrix.sh reindex-profile/bench 50000 300000 4
contrib/perf/bench_matrix.sh reindex-profile/bench 50000 300000 4 /path/to/bootstrap.dat
```

Arguments: `<out_dir> [warmup_height=50000] [measure_blocks=300000] [n_trials=4] [bootstrap_dat_path]`.
Runs `defaultbuf`/`1mbbuf` conditions (both with `-perffdcache=1`) for
`-reindex`, then the same two conditions for bootstrap import if a
`bootstrap.dat` path is given and exists. Results accumulate in
`<out_dir>/results.tsv` (one row per trial: mode, condition, trial, heights,
elapsed seconds, blocks/sec).

**The two modes need different datadir resets, not just different zerod
flags** — this is handled internally, but matters if extending the script:
`-reindex` rescans existing `blk*.dat`/`rev*.dat`, so only `chainstate` is
excluded from the source; `-loadblock` needs a genuinely empty chain, so
`blocks/` is excluded too. Reusing a fully-synced source's `blocks/` for a
bootstrap trial makes `-loadblock` reconcile against a multi-million-block
pre-existing index instead of importing into an empty one — confirmed via
`debug.log` showing a long, misleading RPC `"Loading block index..."` state
that is index reconciliation, not the import being measured. See `Perf.md`
§3 for the full writeup.

Every wait (RPC-up, warmup, target-end) is bounded (10 min) and escalates to
`SIGTERM` then `SIGKILL` if exceeded, rather than hanging indefinitely — a
`zerod` reconciling an unexpectedly large block index can be uninterruptible
by both RPC `stop` (not up yet) and `SIGTERM` (no reachable interruption
point) for as long as that reconciliation runs; see `Perf.md` §3 for why.
