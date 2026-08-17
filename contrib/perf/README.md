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
(or `~/.zero`) as a **writable** lab datadir, and never launch `zerod`
`-reindex`/`-rescan`/`-loadblock` against it. Launchers refuse that path and
also refuse **LAB** under the Zero400 product tree. Shared guard:
`contrib/perf/datadir_guard.sh` -> `contrib/perf/debuglog.py --guard-write`.
Override (can destroy the live node): `ZERO_PERF_ALLOW_LIVE_DATADIR=1` or
`python3 contrib/perf/debuglog.py --guard-write --allow-live-datadir PATH`.
Archives may be **read-only sources** via `ZERO_PERF_SRC_DATADIR` /
`ZERO_PERF_ARCHIVE_DIR`.

Read-only log scanners (`extract_measures.py`, `stall_check.py`) use the
path spec below. They do not start `zerod`. Do not cite operator extracts as
lab `M-*` rows unless `--env` is `insight` or `wallet`.

## debug.log path spec

Shared by `extract_measures.py` and `stall_check.py` (`contrib/perf/debuglog.py`).

| Input | What is read |
|-------|----------------|
| `--datadir DIR` | `DIR/debug.log` only |
| `--datadir DIR --rotated` | `debug.log` plus **rotation siblings** in DIR |
| `--log SPEC` (repeatable) | File, directory, or glob |
| positional SPEC | Same as `--log` |
| directory operand | That datadir's `debug.log` (`--rotated` applies) |
| explicit file | That file as-is (name need not be `debug.log`; `debug.log.snapshot` is fine) |
| glob (e.g. `*.log`) | Matching files; directory matches expand like a datadir operand |

**`--rotated` names** (only these, not other `*.log`):

- `debug.log.N` -- Bitcoin / logrotate (`debug.log.1`)
- `debugN.log` -- Zero (`debug10.log`, `debug11.log`, ...)
- `debug.N.log`

Sorted oldest `mtime` first, then name. `notes.log` and `debug.log.snapshot`
are not rotations; pass them with `--log` if needed. A glob `debug*.log` is
**not** `--rotated`: it misses `debug.log.1` and can include extra names.
Concatenating rotations can look like `tip_gap` at file joins; prefer current
`debug.log` unless you need history.

```bash
python3 contrib/perf/debuglog.py --self-test
python3 contrib/perf/debuglog.py --list --datadir "$HOME/Library/Application Support/zero"
python3 contrib/perf/debuglog.py --list --datadir "$HOME/Library/Application Support/zero" --rotated
python3 contrib/perf/debuglog.py --list --log "$HOME/Library/Application Support/zero/*.log"
```

**Reuse outside this tree:** the fixture contract is the reusable part --
refuse protected datadirs, inject wallets by env, packed snaps outside git,
`bootstrap.dat` copies only, scratch `zero.conf` with no sticky `reindex=`,
Insight flags matching the copied index, one long trial per invocation,
append-only ledger. Product runtime check (RPC before sync, then warm snap):
`contrib/ops-validate.sh` -- copy to Zero400 as the same path. Long import
(`bootstrap`, `reindex`) defaults to height **100000** and `-disablewallet`.
`reindex all` goes to snap tip (tiny 187417). `rescan` keeps indexes and waits
for Done loading. Wallet: `p0` / `p1` / `fat` / `none` or `--wallet=PATH`
(`contrib/ops-validate.sh wallets` lists paths). Product ops
catalog and conf templates: Zero400 **TEST_ZERO.md** §8 and
`contrib/conf-templates/`. Do not copy this campaign set into a GA ship tree.

**Long trials:** do not batch runs where each trial is expected to exceed
~20 minutes unless each trial can be restarted individually (separate
invocation or resume-from-trial). See `AGENTS.md` and `Perf.md` §0.13.
**ConnectBlock vs wallet-on:** `capture_sequence` / `bench_matrix` target import
CPU on `zcash-loadblk`. Wallet-on fat reindex is a separate track
(`wallet_sync_profile.sh`, M-WAL-SYNC-FAT / M-CPU-WAL-FAT) -- bottleneck is
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

# Live node (read-only; not a lab campaign unless --env insight|wallet):
python3 contrib/perf/extract_measures.py \
  --datadir "$HOME/Library/Application Support/zero" --env insight \
  --op-class catchup --sample-tip 1

# Explicit file / glob (path spec: debuglog.py):
python3 contrib/perf/extract_measures.py --log /path/to/debug.log.snapshot
python3 contrib/perf/extract_measures.py --rotated --log "$LAB"

# Shared helper used by bench_matrix.sh:
python3 contrib/perf/extract_measures.py --elapsed-heights "$LAB/debug.log" 50000 350000
```

## stall_check.py

Read-only scan of stock `debug.log` for follow-tip stalls: `UpdateTip` wall
gaps, log still writing with no tip (`tip_silent`), same-second socket/ping
timeout bursts, and clock-warn. Expired tx / Misbehaving / Insight logical
timestamp bumps are counted, not stall-class. `--datadir` may be the default
runtime (same read policy as `extract_measures.py`). Does **not** launch
`zerod`. Lab duration/rates stay in `extract_measures.py`.

Zero PoW target spacing is 120s. Default `--gap-s 900` is 15 minutes.

```bash
python3 contrib/perf/stall_check.py --self-test
python3 contrib/perf/stall_check.py --datadir "$HOME/Library/Application Support/zero"
python3 contrib/perf/stall_check.py --log "$HOME/Library/Application Support/zero/debug.log"
python3 contrib/perf/stall_check.py --rotated --datadir "$HOME/Library/Application Support/zero"
```

Exit 1 if any stall-class finding (`tip_gap`, `tip_silent`, `timeout_burst`,
`clock_warn`). `header_lag` (follow-tip only: height +1 and log dt >= 30s,
log time vs `date=`) is reported and does not fail the process. Catch-up
bursts (many tips in one second) are counted as `header_lag_catchup`, not
findings. `--rotated` is defined in **debug.log path spec** above.

## prep_lab_datadir.sh

Create a disposable lab datadir and unroll only `blocks/` + `chainstate/`
(includes `blocks/index/` and `rev*`). Does **not** write `zero.conf` or start
`zerod`. Refuses the default Application Support datadir and Zero400 as **LAB**
unless `ZERO_PERF_ALLOW_LIVE_DATADIR=1`. Default archive is read-only (no writes
there).

```bash
contrib/perf/prep_lab_datadir.sh          # create + unroll
contrib/perf/prep_lab_datadir.sh create
contrib/perf/prep_lab_datadir.sh unroll
```

Defaults: `LAB=reindex-profile/mainnet-p2p-23911`,
`ARCHIVE=$HOME/Library/Application Support/zero/chainblocks812-clean.tgz`.
`ARCHIVE=` (empty) unrolls from `SRC=reindex-profile/fulltip-812-datadir` instead.
Then write `LAB/zero.conf` by hand (`rpcport=23911`, `port=23901`, Insight flags
if the copied index was built with Insight).

Opt-in witness flags (defaults off; wallet required -- do not combine with
`-disablewallet`): `-walletwitness=ibd-defer` `-walletwitnessnote=1`.
Caught-up follow-tip: `ibd-defer` applies on the next IBD/reindex; to rebuild
now add `-walletwitness=rebuild` for that start only. See **Perf.md** §0.14.

## tiny_baseline.sh

Unpack tiny (or short) snap into `$TMPDIR`, `-reindex -disablewallet`, then
run `extract_measures.py`. Writes `test-logs/<run_id>.*`.

```bash
contrib/perf/tiny_baseline.sh        # tiny -> tip ~187417
contrib/perf/tiny_baseline.sh short  # tip ~245992
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

Historical `ZERO_FDCACHE` A/B (`-perffdcache` / `-perfbufsize`) against a
fixed height window. **ZeroPerf only** -- do not copy into a GA Zero400 tree.
Stock ConnectBlock rematch moved to `postsapling_reindex.sh`; product
bootstrap is `contrib/ops-validate.sh bootstrap`. Keep this file for FDCACHE
re-measure if that flag returns to the mix.

```bash
contrib/perf/bench_matrix.sh reindex-profile/bench
contrib/perf/bench_matrix.sh reindex-profile/bench 50000 300000 4
contrib/perf/bench_matrix.sh reindex-profile/bench all 1 /path/to/bootstrap.dat
```

Default stop is height **100000**. `all` imports to end of file.

Env: `ZERO_PERF_SRC_DATADIR` (read-only rsync source), `ZERO_PERF_SCRATCH_DATADIR`
(must not be the default user datadir; default `reindex-profile/datadir`).

## postsapling_reindex.sh

Post-Sapling window rematch (default warmup 600000, measure 300000).
**Current mix:** stock `-reindex` only (`CONDITIONS=stock`, `N_TRIALS=4`),
`-disablewallet`. FDCACHE A/B is optional later, not the default. Each trial
appends to the durable ledger.

Bootstrap `-loadblock` is not this script (it is not a post-Sapling window).
Use `contrib/ops-validate.sh bootstrap`.

```bash
ZERO_PERF_SRC_DATADIR="$HOME/Library/Application Support/zero" \
  contrib/perf/postsapling_reindex.sh
# override: N_TRIALS=4 CONDITIONS=stock CAMPAIGN=postsapling
# util samples (default on): SAMPLE_UTIL=1 UTIL_PERIOD_S=30
#   -> per-trial util.tsv (ps %cpu/%mem/rss + vmmap Physical footprint at milestones)
```

Plans/specs: **Perf.md** §0.13 (BENCH-BOOT / FIX-*).
Lab materials / density banding: **Perf.md** §0.9 / §1.

## mine_bench.sh

BENCH-MINE. Equihash **solve** lab env (not ConnectBlock rematch). Modes:

```bash
contrib/perf/mine_bench.sh regtest          # generate N blocks (48,5); util.tsv
contrib/perf/mine_bench.sh mainnet-template # (192,7) env + notes; opt-in solve
contrib/perf/mine_bench.sh neon-probe       # arch / NEON / blake2b symbol probe
```

Env: `MINE_BLOCKS`, `MINE_TIMEOUT_S`, `ZERO_PERF_NEON_ZEROD` (NEON A/B binary;
**G7 postponed** -- probe-only until a NEON `zerod` exists),
`CAMPAIGN=mine-equihash-*`. Stock arm64 still links `blake2b_compress_ref`.
**Done:** regtest smoke (M-MINE-REGTEST-SMOKE), neon probe (M-MINE-NEON-PROBE).
**Scheduled (Track M / G5):** mainnet (192,7) timed solve -- Instruments + `MINE_MAINNET_SOLVE=1`;
`mainnet-template` mode alone only writes an env stub. Parallel with witness Cycle 1; one trial.

KATs: **`kats/`** (`1927EQ.txt`, `1927EQ_h1.hex`; see `kats/README.md`). TST-05 green;
further test adaptation **postponed (G9)**.

## wallet_sync_profile.sh

Wallet-on `-reindex` util (CPU / RSS / `wallet.zero` bytes / `txcount`). Pass the
wallet file via env (no ops paths in Measures):

```bash
ZERO_PERF_WALLET_FILE="$HOME/Library/Application Support/zero/wallet.zero0" \
ZERO_PERF_CHAIN_SNAP=tiny \
  contrib/perf/wallet_sync_profile.sh
# fat compare (G0): point ZERO_PERF_WALLET_FILE at golden fat wallet.zero
```

`ZERO_PERF_CHAIN_SNAP=tiny|short|full`. `RESUME=1` keeps scratch. Samples ->
`test-logs/walletsync-*/util.tsv` (includes `note_tx_count`). Bound `M-*`:
M-WAL-SYNC-P0, M-WAL-SYNC-P1, M-WAL-SYNC-FAT, M-CPU-WAL-FAT. **Caveat:**
`getwalletinfo` in `sample_row` can block under fat-wallet `cs_wallet` contention
-- tip time then from `debug.log`; hygiene timeout is queue **G0b**.

Archive: `test-logs/archives/walletsync-fat-g0-20260812.tar.gz` + per-run
`FINDINGS.md`. Mitigations: **Perf.md** §0.14. Queue: **Perf.md** §0.13 G.

`WALLETINFO_TIMEOUT_S` (default 5; `0` skips txcount). `ZEROD_EXTRA_ARGS` for
**opt-in** witness flags (defaults off; see `zerod -help`):
- `-walletwitness=ibd-defer` -- skip per-block IBD witness build; rebuild after import
- `-walletwitness=rebuild` -- force tip rebuild
- `-walletwitnessnote=1` -- **NOTEIDX** (note-bearing tx index; Verify + height walk)

`getwalletinfo` extras: `note_tx_count`, `sprout_note_count`, `sapling_note_count`.
While rebuilding (`-33`): status allowlist `stop`/`help`/`getblockcount`/`getblockchaininfo`/`getnetworkinfo`
(deny-by-default; `getblockcount` still stalls on `cs_main` until the walk ends).
R5c / **FIX-WIT-WALK-UNLOCK**: product, not a lab e2e -- **Perf.md** §0.16.
Do not run Bfail or `CachedWitnessesCleanIndex` for witness confidence (B1 `reindex_shielded.py` covers reindex spend).
Witness RPC lockout / peer comparison / risk: **Perf.md** §0.14 / §0.16.

## witness_lab.sh

DIRTY-CONT / WIT-REBUILD.

```bash
ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
  contrib/perf/witness_lab.sh dirty-cont      # stock+NOTEIDX+stats to TARGET_HEIGHT
ZERO_PERF_WALLET_FILE=... contrib/perf/witness_lab.sh rebuild
ZERO_PERF_WALLET_FILE=... contrib/perf/witness_lab.sh rebuild-noteidx
```

Reusable automation; **one-time** lab samples (not CI). Tiny/short tips are pre-Sapling
(187417 / 245992) -- DIRTY-CONT `note_visits` and tip height-walk need
`ZERO_PERF_CHAIN_SNAP=full` (disposable full tip; see Perf.md §0.16). E2E:
`wallet_witness_defer.py`.

Post-Sap WIT-REBUILD (one trial at a time):

```bash
ZERO_PERF_CHAIN_SNAP=full ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
  contrib/perf/witness_lab.sh rebuild-noteidx
```

Disposable full tip: `reindex-profile/fulltip-812-datadir` (or `chainblocks812-clean.tgz`).
Scratch `zero.conf` needs `experimentalfeatures=1` + `insightexplorer=1`.

```bash
ZERO_PERF_TIP_TEMPLATE=$PWD/reindex-profile/fulltip-812-datadir \
ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
  contrib/perf/witness_lab.sh tip-rebuild-note
# pair: tip-rebuild (note off). One trial at a time.
```

Live datadir may show `find . -name '._*'` empty while files still have xattrs;
`COPYFILE_DISABLE=1` when packing. After renaming CLI flags, rebuild `zerod`.

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

## ops-campaign.sh

Rematch the same wallet x op matrix after each integration cycle (Perf.md §0.16).
**ZeroPerf only.** **One trial per invocation.** Do not batch fat/full/long trials.

Catalog: `contrib/perf/cycle_trials.tsv` (`SET=smoke|gate|long`).

```bash
CYCLE=1 SET=smoke contrib/perf/ops-campaign.sh list
CYCLE=1 SET=smoke \
  ZERO_PERF_WALLET_P0=/path/to/wallet.zero0 \
  contrib/perf/ops-campaign.sh next
CYCLE=1 contrib/perf/ops-campaign.sh run p0-reindex-tiny
contrib/perf/ops-campaign.sh report
```

Ledger `CAMPAIGN=cycle-1` (then cycle-2, cycle-3). Status:
`reindex-profile/cycle-campaign/status.jsonl`. Collate:
`python3 contrib/perf/collate_cycle.py`.

### Callee rework

| Script | Campaign role | Plan |
|---|---|---|
| `ops-validate.sh` | product ops | `reindex` / `reindex all` / `rescan p0` / `bootstrap` / wallet ids. Copy to Zero400. |
| `tiny_baseline.sh` | `none` + reindex + tiny/short | Fold: `ZERO_OPS_SNAP=tiny contrib/ops-validate.sh reindex all` plus extract_measures. Then delete or make a one-line wrapper. |
| `wallet_sync_profile.sh` | p0/p1/fat reindex | Keep until ops-validate grows `ZERO_OPS_WALLET` + util.tsv (`WALLETINFO_TIMEOUT_S`). Then dispatch to ops-validate reindex. |
| `witness_lab.sh` | rescan / sync / flag A/B | Split: stock rescan/catchup -> ops-validate rescan (keep chainstate). Remain standalone: `dirty-cont`, `rebuild`, `*-noteidx`, `ibd-defer`, tip-rebuild. Those flags are the witness lab, not product ops. |
| `postsapling_reindex.sh` | not in cycle catalog | Remain standalone. n=4, window 600k-900k, ledger. Not an ops-validate option. |
| `mine_bench.sh` | not in cycle catalog | Remain standalone. Equihash solve, not sync. |
| `bench_matrix.sh` | not in cycle catalog | Remain standalone, historical FDCACHE. ZeroPerf only. |
| `capture_sequence.sh` / `prep_lab_datadir.sh` | Instruments / snap unroll | Remain standalone. |

Do not merge callees into `ops-campaign.sh` itself. It stays a catalog + resume ledger. Do not copy the campaign set into GA Zero400.

`witness_lab.sh` also accepts `rescan`, `rescan-noteidx`, `catchup`,
`catchup-noteidx`, `tip-catchup`, `tip-catchup-note` as single trials.
```
