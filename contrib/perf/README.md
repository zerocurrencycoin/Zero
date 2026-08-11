# perf

Scripts supporting the `zerod` sync performance investigation documented in
`Perf.md` at the repo root. Read that file first -- it has the methodology
and the reasoning these scripts implement; this README is just usage.

**Numbers inventory:** campaign IDs, metric tokens (`height_per_s`, `wall_s`,
`cpu_pct`, ...), and contradictions live in **`Measures.md`**. Prefer those
tokens in new TSV/JSONL columns when extending these scripts.

**Datadir rule:** never use the default `~/Library/Application Support/zero`
(or `~/.zero`) as a writable lab datadir. Scripts refuse that path.
Archives may be read-only sources via `ZERO_PERF_SRC_DATADIR` /
`ZERO_PERF_ARCHIVE_DIR`.

**Not wallet:** these tools profile **chain import / ConnectBlock** (`zcash-loadblk`),
not `AddToWallet` / `OrderedTxItems`. For wallet-order CPU, retarget as described
in `Perf.md` (scope note + retarget paragraph) and `ZeroStruct.md` §13.4.3.

## extract_measures.py

Filter-then-process stock `debug.log` markers into Measures vocabulary
(JSONL events + CSV rows + markdown summary). Does **not** launch `zerod`.

```bash
python3 contrib/perf/extract_measures.py --self-test

# After any lab (LAB is disposable):
python3 contrib/perf/extract_measures.py \
  --datadir "$LAB" --run-id tiny-... --op-class reindex --no-wallet --env lab \
  --jsonl test-logs/tiny.jsonl --csv test-logs/measures_tiny.csv

# Shared helper used by bench_matrix.sh:
python3 contrib/perf/extract_measures.py --elapsed-heights "$LAB/debug.log" 50000 350000
```

## run_tiny_baseline.sh

Unpack tiny (or short) snap into `$TMPDIR`, `-reindex -disablewallet`, then
run `extract_measures.py`. Writes `test-logs/<run_id>.*`.

```bash
contrib/perf/run_tiny_baseline.sh        # tiny -> tip ~187417
contrib/perf/run_tiny_baseline.sh short  # tip ~245992
```

## capture_sequence.sh

Runs a long `-reindex` under repeated Instruments Time Profiler captures.

```bash
rm -rf reindex-profile/datadir
rsync -a --exclude='chainstate' \
  "${ZERO_PERF_SRC_DATADIR:-$HOME/Library/Application Support/zero}/" \
  reindex-profile/datadir/
contrib/perf/capture_sequence.sh reindex-profile/datadir reindex-profile/captures 1200 300
```

`capture_sequence.sh` **refuses** if `<datadir>` resolves to the default user datadir.

Arguments: `<datadir> <out_dir> [period_secs=1200] [capture_secs=300] [max_captures=0]`.

## decode_captures.py

```bash
python3 contrib/perf/decode_captures.py reindex-profile/captures --json reindex-profile/captures_report.json
```

## bench_matrix.sh

Repeated-trial A/B for `ZERO_FDCACHE` flags. Tip timing delegates to
`extract_measures.py --elapsed-heights`.

```bash
contrib/perf/bench_matrix.sh reindex-profile/bench 50000 300000 4
```

Env: `ZERO_PERF_SRC_DATADIR` (read-only rsync source), `ZERO_PERF_SCRATCH_DATADIR`
(must not be the default user datadir; default `reindex-profile/datadir`).
