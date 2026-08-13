# perf

Scripts supporting the `zerod` sync performance investigation documented in
`Perf.md` at the repo root. Read that file first -- it has the methodology
and the reasoning these scripts implement; this README is just usage.

**Numbers inventory:** `M-*` campaign IDs, metric tokens (`height_per_s`,
`wall_s`, `cpu_pct`, ...), comparability rules, extraction schema, and the
ledger `CAMPAIGN=` map live in **`Measures.md`** (§8 for bindings). **Plans /
specs** (BENCH-*, FIX-*, IMP-*, L0-L7, Stages) and **lab materials**:
**`Perf.md`**. Prefer Measures tokens in new TSV/JSONL columns when extending
these scripts.

**Datadir rule:** never use the default `~/Library/Application Support/zero`
(or `~/.zero`) as a writable lab datadir. Scripts refuse that path.
Archives may be read-only sources via `ZERO_PERF_SRC_DATADIR` /
`ZERO_PERF_ARCHIVE_DIR`.

**Long trials:** do not batch runs where each trial is expected to exceed
~20 minutes unless each trial can be restarted individually (separate
invocation or resume-from-trial). See `AGENTS.md` and `Perf.md` §0.13.
**ConnectBlock vs wallet-on:** `capture_sequence` / `bench_matrix` target import
CPU on `zcash-loadblk`. Wallet-on fat reindex is a separate track
(`run_wallet_sync_profile.sh`, M-WAL-SYNC-FAT / M-CPU-WAL-FAT) -- bottleneck is
`VerifyAndSetInitialWitness`, not `OrderedTxItems` (see **Perf.md** §0.14).

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

## run_postsapling_baseline.sh

Post-Sapling window rematch (default warmup 600000, measure 300000).
**Current mix:** stock `-reindex` only (`CONDITIONS=stock`, `N_TRIALS=4`).
FDCACHE A/B is optional later, not the default. Each trial appends to the
durable ledger.

`MODE=reindex` (default) or `MODE=bootstrap` with `LOADBLOCK=/path/to/bootstrap.dat`
(use a copy or softlink; do not modify the Zero400 original). Bootstrap reset
excludes `blocks/` so `-loadblock` starts on an empty chain.

```bash
ZERO_PERF_SRC_DATADIR="$HOME/Library/Application Support/zero" \
  contrib/perf/run_postsapling_baseline.sh
# override: N_TRIALS=4 CONDITIONS=stock CAMPAIGN=postsapling
# util samples (default on): SAMPLE_UTIL=1 UTIL_PERIOD_S=30
#   -> per-trial util.tsv (ps %cpu/%mem/rss + vmmap Physical footprint at milestones)
# bootstrap smoke (example):
#   MODE=bootstrap LOADBLOCK=reindex-profile/bootstrap-src/bootstrap.dat \
#   CAMPAIGN=bootstrap-smoke WARMUP_HEIGHT=50000 MEASURE_BLOCKS=25000 N_TRIALS=1 \
#   contrib/perf/run_postsapling_baseline.sh
```

Plans/specs: **Perf.md** §0.13 (BENCH-BOOT / FIX-*).
Lab materials / density banding: **Perf.md** §0.9 / §1.

## run_mine_bench.sh (BENCH-MINE)

Equihash **solve** lab env (not ConnectBlock rematch). Modes:

```bash
contrib/perf/run_mine_bench.sh regtest          # generate N blocks (48,5); util.tsv
contrib/perf/run_mine_bench.sh mainnet-template # (192,7) env + notes; opt-in solve
contrib/perf/run_mine_bench.sh neon-probe       # arch / NEON / blake2b symbol probe
```

Env: `MINE_BLOCKS`, `MINE_TIMEOUT_S`, `ZERO_PERF_NEON_ZEROD` (NEON A/B binary;
**G7 postponed** -- probe-only until a NEON `zerod` exists),
`CAMPAIGN=mine-equihash-*`. Stock arm64 still links `blake2b_compress_ref`.
**Done:** regtest smoke (M-MINE-REGTEST-SMOKE), neon probe (M-MINE-NEON-PROBE).
**Not done:** mainnet (192,7) timed solve -- needs Instruments + `MINE_MAINNET_SOLVE=1` (**G5**);
`mainnet-template` mode alone only writes an env stub.

KATs: **`kats/`** (`1927EQ.txt`, `1927EQ_h1.hex`; see `kats/README.md`). TST-05 green;
further test adaptation **postponed (G9)**.

## run_wallet_sync_profile.sh

Wallet-on `-reindex` util (CPU / RSS / `wallet.zero` bytes / `txcount`). Pass the
wallet file via env (no ops paths in Measures):

```bash
ZERO_PERF_WALLET_FILE="$HOME/Library/Application Support/zero/wallet.zero0" \
ZERO_PERF_CHAIN_SNAP=tiny \
  contrib/perf/run_wallet_sync_profile.sh
# fat compare (G0): point ZERO_PERF_WALLET_FILE at golden fat wallet.zero
```

`ZERO_PERF_CHAIN_SNAP=tiny|short|full`. `RESUME=1` keeps scratch. Samples ->
`test-logs/walletsync-*/util.tsv`. Bound `M-*`: M-WAL-SYNC-P0, M-WAL-SYNC-FAT,
M-CPU-WAL-FAT (done). **Caveat:** `getwalletinfo` in `sample_row` can block under
fat-wallet `cs_wallet` contention -- tip time then from `debug.log`; hygiene
timeout is queue **G0b**.

Archive: `test-logs/archives/walletsync-fat-g0-20260812.tar.gz` + per-run
`FINDINGS.md`. Mitigations: **Perf.md** §0.14. Queue: **Perf.md** §0.13 G.

`WALLETINFO_TIMEOUT_S` (default 5; `0` skips txcount). `ZEROD_EXTRA_ARGS` for
**opt-in** witness flags (defaults off; see `zerod -help`):
- `-walletwitness=ibd-defer` -- skip per-block IBD witness build; rebuild after import
- `-walletwitness=rebuild` -- force tip rebuild
- `-walletwitnessnote=1` -- **NOTEIDX** (note-bearing tx index; Verify + height walk)

`getwalletinfo` extras: `note_tx_count`, `sprout_note_count`, `sapling_note_count`.
While rebuilding (`-33`): status allowlist `stop`/`help`/`getblockcount`/`getblockchaininfo`/`getnetworkinfo`.
Witness RPC lockout / peer comparison / risk: **Perf.md** §0.14 / §0.16.

## run_witness_lab.sh (DIRTY-CONT / WIT-REBUILD)

```bash
ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
  contrib/perf/run_witness_lab.sh dirty-cont      # stock+NOTEIDX+stats to TARGET_HEIGHT
ZERO_PERF_WALLET_FILE=... contrib/perf/run_witness_lab.sh rebuild
ZERO_PERF_WALLET_FILE=... contrib/perf/run_witness_lab.sh rebuild-noteidx
```

Reusable automation; **one-time** lab samples (not CI). Tiny/short tips are pre-Sapling
(187417 / 245992) -- DIRTY-CONT `note_visits` and tip height-walk need
`ZERO_PERF_CHAIN_SNAP=full` (disposable full tip; see Perf.md §0.16). E2E:
`wallet_witness_defer.py`.

Post-Sap WIT-REBUILD (one trial at a time):

```bash
ZERO_PERF_CHAIN_SNAP=full ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
  contrib/perf/run_witness_lab.sh rebuild-noteidx
```

## shielded_density.py

Build `reindex-profile/shielded-density.csv` (+ `.progress.jsonl`) by walking
heights over RPC (`getblockhash` + `getblock <hash> false`) and counting via
`qa` mininode deserialize. **Do not use `getblock` verbosity 2** -- Zero omits
Sapling/Sprout shield arrays from that JSON.

Requires a running `zerod` (`-connect=0 -listen=0` OK). Fine rematch windows
first; then coarse **400k** bands split at Sapling activation 492850.

```bash
# zerod already up on the datadir:
python3 contrib/perf/shielded_density.py \
  --datadir "$HOME/Library/Application Support/zero" \
  --out-dir reindex-profile \
  --mode all
# --mode fine|coarse|all ; resumes by skipping eras already in the CSV
```

## accumulate_bench.py

Append-only store + collation across campaigns/runs:

- `reindex-profile/bench-summaries/ledger.jsonl` / `ledger.tsv`
- `REPORT.md` / `REPORT-<campaign>.md`

```bash
python3 contrib/perf/accumulate_bench.py --import-tsv \
  reindex-profile/bench-summaries/bench_postsapling_results.tsv \
  --campaign postsapling-historical
python3 contrib/perf/accumulate_bench.py --report \
  --md reindex-profile/bench-summaries/REPORT.md
```
