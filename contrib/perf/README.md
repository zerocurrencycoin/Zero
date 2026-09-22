# contrib/perf

**New here? Read `docs/HOWTO.md` first.** It teaches the
workflow -- how to take a profile, how to read the three views, which traps
have produced wrong numbers before. This file is a per-tool reference and
assumes you already know why you are running something.

Quickest useful thing:

```bash
contrib/perf/profile_run.sh <scenario> <datadir> 60   # capture -> bucket -> collate
contrib/perf/profile_collate.py report                # everything accumulated so far
```

Data produced 2026-08-19/20 and its provenance: `test-logs/DATA_INDEX.md`.

## Routing

This file is the **per-tool reference**: invocation, environment variables and
per-tool caveats. It is deliberately the only place those live in long form.

| Looking for | Read |
|-------------|------|
| How to take a profile and read it | `docs/HOWTO.md` |
| One-line index of every tool | `docs/HOWTO.md` S4.1 |
| Findings and method | `docs/Perf.md` |
| Numbers bound to `M-*` | `docs/Measures.md` |
| Work items and what to do next | `docs/PLAN.md` |
| Rules, ownership, placement, lab discipline | `docs/POLICY.md` |
| Recording results so they compare | `recbench/RecBench.md` |
| Measuring across projects; uniblake practice | `docs/CROSSPROJECT.md` |
| Which library computes which hash | `docs/HASHLIBS.md` |
| libsodium versions, peers, .21 vs .22 | `docs/SODIUM_SURVEY.md` |

`docs/HOWTO.md` S4.1 lists every tool as a one-line index; the detail
below is not repeated there. When adding a tool, add the row there and the
section here.

**Numbers inventory:** `M-*` campaign IDs, metric tokens (`height_per_s`,
`wall_s`, `cpu_pct`, ...), comparability rules, extraction schema, and the
ledger `CAMPAIGN=` map live in **`docs/Measures.md`** (§8 for bindings). **Plans /
specs** (BENCH-*, FIX-*, IMP-*, L0-L7, Stages) and **lab materials**:
**`docs/Perf.md`** (in this directory, not the repo root). Prefer Measures tokens in new TSV/JSONL columns when extending
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
Insight flags matching the copied index, append-only ledger. Product runtime check (RPC before sync, then warm snap):
`contrib/ops-validate.sh` -- copy to Zero400 as the same path. Long import
(`bootstrap`, `reindex`) defaults to height **100000** and `-disablewallet`.
`reindex all` goes to snap tip (tiny 187417). `rescan` keeps indexes and waits
for Done loading. Wallet: `p0` / `p1` / `fat` / `none` or `--wallet=PATH`
(`contrib/ops-validate.sh wallets` lists paths). Product ops
catalog and conf templates: Zero400 **TEST_ZERO.md** §8 and
`contrib/conf-templates/`. Do not copy this campaign set into a GA ship tree.

**Long trials:** lab discipline, including the restartability rule, is
`docs/POLICY.md` S4.
**ConnectBlock vs wallet-on:** `capture_sequence` / `bench_matrix` target import
CPU on `zcash-loadblk`. Wallet-on fat reindex is a separate track
(`wallet_sync_profile.sh`, M-WAL-SYNC-FAT / M-CPU-WAL-FAT) -- bottleneck is
`VerifyAndSetInitialWitness`, not `OrderedTxItems` (see **docs/Perf.md** §0.14).

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
now add `-walletwitness=rebuild` for that start only. See **docs/Perf.md** §0.14.

## tiny_baseline.sh

Unpack tiny (or short) snap into `/tmp`, `-reindex -disablewallet`, then
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

Plans/specs: **docs/Perf.md** §0.13 (BENCH-BOOT / FIX-*).
Lab materials / density banding: **docs/Perf.md** §0.9 / §1.

## mine_bench.sh

BENCH-MINE. Equihash **solve** lab env (not ConnectBlock rematch). Modes:

```bash
contrib/perf/mine_bench.sh regtest          # generate N blocks (48,5); util.tsv
contrib/perf/mine_bench.sh mainnet-template # (192,7) env + notes; opt-in solve
```

Env: `MINE_BLOCKS`, `MINE_TIMEOUT_S`, `CAMPAIGN=mine-equihash-*`.
**Done:** regtest smoke (M-MINE-REGTEST-SMOKE).
**G5 (Track M), mainnet (192,7) timed solve -- the timing half is DONE, the
profiling half is not.** `mainnet-template` mode alone only writes an env stub
and never solves; that is the "G5 problem". The timing was taken instead
through the fixed-nonce harness in `equihash_tests`
(`SOLVE_TIMING_1927` / `SOLVE_TIMING_SOLVER`), which is the better instrument
-- paired nonces, both solver arms in one process, solutions verified in-loop.
Results: M-EQ-SOLVE-1927-FIXED and M-EQ-TROMP-PAIRED.

**What remains of G5:** the Instruments capture, for a per-phase CPU
breakdown of a mainnet solve. `MINE_MAINNET_SOLVE=1` plus an external
`xctrace` attach; not run.

KATs: **`src/test/data/`** (`1927EQ.txt`, `1927EQ_h1.hex`; see `kats/README.md`). TST-05 green;
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
`FINDINGS.md`. Mitigations: **docs/Perf.md** §0.14. Queue: **docs/Perf.md** §0.13 G.

`WALLETINFO_TIMEOUT_S` (default 5; `0` skips txcount). `ZEROD_EXTRA_ARGS` for
**opt-in** witness flags (defaults off; see `zerod -help`):
- `-walletwitness=ibd-defer` -- skip per-block IBD witness build; rebuild after import
- `-walletwitness=rebuild` -- force tip rebuild
- `-walletwitnessnote=1` -- **NOTEIDX** (note-bearing tx index; Verify + height walk)

`getwalletinfo` extras: `note_tx_count`, `sprout_note_count`, `sapling_note_count`.
While rebuilding (`-33`): status allowlist `stop`/`help`/`getblockcount`/`getblockchaininfo`/`getnetworkinfo`
(deny-by-default; `getblockcount` still stalls on `cs_main` until the walk ends).
R5c / **FIX-WIT-WALK-UNLOCK**: product, not a lab e2e -- **docs/Perf.md** §0.16.
Held and known-fail tests are excluded by `qa/zcash/test_filters.sh`; do not re-list them here. B1 `reindex_shielded.py` covers reindex spend.
Witness RPC lockout / peer comparison / risk: **docs/Perf.md** §0.14 / §0.16.

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
`ZERO_PERF_CHAIN_SNAP=full` (disposable full tip; see docs/Perf.md §0.16). E2E:
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

## codequery.sh

Source queries with the flags that make a result trustworthy. Wraps ripgrep;
excludes build artifacts (`.deps/*.Po` list every header a translation unit
touched, so any symbol looks used everywhere); and **reports a no-match
explicitly**, exit 1, instead of printing nothing.

```bash
contrib/perf/codequery.sh files '\bub_[a-z_]+\s*\(' src/   # 12 files
contrib/perf/codequery.sh symbol 'crypto_generichash_blake2b_init' src/
contrib/perf/codequery.sh count 'sodium_' src/
```

Written after two ad-hoc greps gave wrong answers in one session: a
`grep --include=*.cpp` whose glob zsh expanded (and, finding no match,
aborted the whole pipeline) reported "one call site" when there were twelve;
and an `awk -F=` against colon-separated `vmmap` output recorded every memory
value as blank. Both failed silently. Prefer this over a hand-written grep
when the answer will be written down.

## Snapshot archives: the Insight flags are required

**`chainblocks812*.tgz` and any full-tip snap need two flags in `zero.conf`
before the node will use the chainstate they carry:**

```
experimentalfeatures=1
insightexplorer=1
```

**Without them the node reindexes from genesis** -- a multi-hour run -- instead
of loading the tip in seconds. The snapshot's `chainstate/` was built by a node
with Insight indexes enabled; a node started without them does not recognise
that state as usable.

Verified 2026-09-17 on `chainblocks812-clean.tgz`: with the flags, startup
reached **height 2,518,018** with `LoadBlockIndexDB: insight explorer enabled`
and **`block index 19709ms`** -- 20 seconds, no reindex.

Minimal working lab conf (no wallet, no network, no mining):

```
server=1
rpcuser=lab
rpcpassword=lab
rpcport=23991
port=23981
listen=0
connect=0
maxconnections=0
gen=0
experimentalfeatures=1
insightexplorer=1
```

then `./src/zerod -datadir=<LAB> -disablewallet -daemon`.

**`bootstrap.dat` needs neither flag.** It is a flat serialised block stream
with no index and no chainstate, so there is nothing for Insight settings to
be consistent with -- the node builds both from scratch as it imports. The
flags only matter when *transplanting* a prebuilt `chainstate/`.

### Why the snapshot loads in 20 s and the bootstrap takes 2 h

Two different operations, and the log lines name the difference:

| | `chainblocks812-clean.tgz` | `bootstrap.dat` |
|---|---|---|
| What is supplied | `blocks/` **and** a built `chainstate/` + `blocks/index/` | blocks only, as a byte stream |
| Startup work | read an existing LevelDB index | **validate and connect 2,468,990 blocks** |
| `block index` time | **19,709 ms** | **37 ms** (nothing to load) |
| Verification at start | last **288** blocks, level 3 | none -- every block validated during import |
| Total to usable tip | **~20 s** | **7,191 s (2.00 h)** |

The snapshot is not faster at the same work; it **skips the work**, having had
it done once already. The 37 ms bootstrap figure is the tell -- its index load
is instant because the index is empty.

**Consequence for lab design:** use the snapshot when the question is about a
node *at* the tip (RPC behaviour, memory at rest, witness operations), and
`bootstrap.dat` when the question is about *reaching* the tip (validation
throughput, CPU during import). They are not substitutes.

## Lab wallets: where they are and how to use them

**The catalog is `contrib/ops-validate.sh wallets`** -- it prints each id, its
size and its resolved path. That command is the answer to "where are the test
wallets"; this section says what they are, because no document did.

| Id | Default path | What it is |
|----|--------------|------------|
| `p0` | `<datadir>/wallet.zero0` | small personal wallet |
| `p1` | `<datadir>/wallet.zero.personalbak-<date>` | second personal wallet |
| `fat` | `<datadir>/wallet.zero` | the **golden fat wallet**: ~749 MB, **801,619 tx**, 1,403 note-bearing (0.175%) |
| `none` | -- | `-disablewallet` (default for every lab run) |

Select with a positional id, `--wallet=PATH`, or `ZERO_OPS_WALLET` /
`ZERO_PERF_WALLET_FILE`:

```bash
contrib/ops-validate.sh wallets                  # catalog + sizes
contrib/ops-validate.sh reindex all p0           # inject wallet id 0
ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
  contrib/perf/wallet_sync_profile.sh            # fat reindex profile
```

**Why the golden fat wallet is not in this tree, and why that was hard to
discover.** `docs/POLICY.md` S7.2 keeps DevFee wallet material out of the tree
and uses it **by reference only** -- no addresses, no host paths in tracked
documents. That is deliberate and correct. What was missing is any statement
of *what the referenced thing is*, so `fat` appeared in eight `M-*` rows and
several analyses with no definition anywhere. Hence this table.

**On this host:** `p0` and `p1` are **MISSING**, and `fat` resolves to a
110 KB `wallet.zero` -- **not** the golden 749 MB wallet the `M-WAL-*` rows
were taken against. A wallet-on run here produces valid numbers that are
**not comparable** to those rows.

**The fat-wallet finding, since it is the largest in the tree:** a fat-wallet
reindex of the tiny snap runs at **~19 blk/s against ~1,000 for
`-disablewallet`** -- **~50x slower** (M-WAL-SYNC-FAT, 2.75 h for 187,417
blocks). The bottleneck is `BuildWitnessCache` ->
`VerifyAndSetInitialWitness`, ~97% of CPU (M-CPU-WAL-FAT), not
`OrderedTxItems`. Two opt-in flags recover most of it:
`-walletwitness=ibd-defer` **~35x** (M-WAL-WITNESS-IBD-AB) and
`-walletwitnessnote=1` **~33x** (M-WAL-WITNESS-NOTEIDX-AB).

## codectx.py

Structural source queries that `grep` and `awk` answer wrongly. Tracks brace
depth and function extents, so "is this lock held here" means *in this
function*, not *somewhere earlier in the file*.

```bash
contrib/perf/codectx.py enclosing src/main.cpp 3110    # which function
contrib/perf/codectx.py holds src/rpc/misc.cpp 1104 'LOCK\(cs_main\)'
contrib/perf/codectx.py calls src/main.cpp GetSpentIndex
contrib/perf/codectx.py phrase 'mostly\s+redundant' src/main.cpp
```

Written after three failures in one session: an `awk 'NR<=N'` scan reported a
lock from a *different function* as covering a call site (twice, on the
`FlushStateToDisk` and `getspentinfo` questions); and a comment phrase split
across two lines was reported absent when present. `phrase` folds line breaks
and comment markers before matching. Exit 1 on no match, as `codequery.sh`
does.

## snapshot_data.sh

Copy a data file aside before a run overwrites it. Collated outputs
(`REPORT.md`, `collation.json`, `util.tsv`, `measures_*.csv`) are rewritten in
place, so without a copy the previous revision is gone and "what did this say
before?" is unanswerable. Ledgers are append-only and do not need this.

```bash
contrib/perf/snapshot_data.sh reindex-profile/bench-summaries/REPORT.md
```

Writes `FILE.prev-<utc>` beside each existing FILE. Absent files are skipped,
not created.

## RecBench -- recording results

Benchmark results are recorded by **RecBench**, a separate subsystem with its
own documentation: **`recbench/RecBench.md`**. Store layout, row identity,
invocation and its task list live there, not here.

Launchers in this directory hand rows to it; nothing else in `contrib/perf/`
should reference its internals by path.

## ops-campaign.sh

Rematch the same wallet x op matrix after each integration cycle (docs/Perf.md §0.16).
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

---

## Documentation map

Every markdown file in `contrib/perf`, what it owns, and what it does not
hold. **A file with no inclusion rule accretes** -- nobody can say what does
not belong in it, so everything does; that is how this set reached 43 files,
five of them about the set itself. When two documents could hold something,
the owner takes it and non-owners cite it. Adding a file means adding a row
here and deleting another file (`docs/POLICY.md` S2.0 rule 1).

`lint-perf.sh` `docmap` fails if a tracked `.md` has no row, or a row names a
file that does not exist.

| Document | Owns | Does not hold |
|---|---|---|
| `docs/Perf.md` | ConnectBlock CPU, disk I/O and FDCACHE, the Merkle-root latch, memory, `AddToBlockIndex` | Task state. Solver internals. Hashing kernels. Witness mechanics |
| `docs/PerfGroth.md` | Sapling Groth16 cost and batch headroom | Non-Groth findings; scheduling |
| `equ/` | Equihash: solver internals, lineage, method, plans, solve findings | Equihash verification cost during sync, which is a `docs/Perf.md` finding |
| `docs/HASHLIBS.md` | Which library computes which hash, and what that costs | Kernel internals; Equihash solving |
| `docs/SODIUM_SURVEY.md` | Which libsodium version, and why | Hashing performance |
| `docs/CROSSPROJECT.md` | Recording results comparably across projects | Either project's findings |
| `docs/PRODUCT.md` | Node-code changes perf work identified, and the evidence | Their state |
| `docs/PLAN.md` | What to decide and what to do next, one line per item | Any detail whose subject is owned elsewhere |
| `docs/TESTING.md` | Test and validation state: how to run the suites, suite rules, known defects, suite plan | Performance findings |
| `docs/TASKS.md` | Frozen, superseded by `docs/PLAN.md`; retained until migration (PLAN X1) completes | New items -- do not add |
| `README.md` | Per-tool invocation, env vars, per-tool caveats | Findings; task state |
| `docs/HOWTO.md` | How to take a measurement and read it | Per-tool detail |
| `docs/Measures.md` | The `M-*` registry and metric vocabulary | Narrative |
| `docs/SCHEMA.md`, `recbench/RecBench.md` | Row shape, identity, store topology | Results |
| `docs/POLICY.md` | Rules, ownership, lab discipline, retention | Anything specific to one subject |
| `docs/TOOLING_FAILURES.md` | Shell/search invocations that returned wrong answers, and what closes each | Anything not about tooling reliability |
| `docs/LIBSNARK.md` | What `src/snark/` is, where it came from, and whether it is used | Proof-verification findings (`docs/PerfGroth.md`) |
| `docs/LIBRUSTZCASH.md` | The Rust proof dependency: what is validated, what the siblings did, remaining validation | Proof cost and batching (`docs/PerfGroth.md`) |
| `docs/BUILDCONFIG.md` | How to validate that a binary has the build configuration it was meant to have | Findings from any one build |
| `docs/TSAN.md` | How to build and run ThreadSanitizer on Linux, and how to triage its reports | Findings from a run (its own `test-logs/` record) |
| `docs/THREADS.md` | Census of every thread the node launches, with counts and conditions | Sizing logic and locking (`CONCURRENCY.md`) |
| `docs/SCRIPTQUEUE.md` | Why `max_concurrent` misled, and what occupancy actually is | Thread census (`THREADS.md`) |
| `docs/CPU_MEASUREMENT.md` | Which CPU quantity a figure is, and how to sample it without contradiction | Any specific measurement's result |
| `docs/LOCKS.md` | **Every lock finding**: rates, sites, upstream precedent, disposition | Task state (`TASKS.md`); thread census (`THREADS.md`) |
| `docs/CONCURRENCY.md` | Thread pools, their sizing, solver synchronisation, and how to validate locking | Performance findings (`docs/Perf.md`); task state |
| `docs/RECORDS_READINESS.md` | Whether the store can type a given result, and the interim rule | Row shape itself (`SCHEMA.md`); measurement results |
| `docs/FINDINGS.md` | What is known, newest first | Groth16 (its own file); task state |
| `docs/NOTES.md`, `mine/*.md` | Point-in-time records, kept as written | Anything durable |
| `docs/PerfTimers.md` | Spec for the block-processing phase timers (`IMP-BENCH-ALWAYS`) | Measured results; task state |
| `docs/PerfPlatforms.md` | What the harness needs per platform, and the Linux/Windows equivalents | Findings taken on any one platform |
| `docs/Stores.md` | Zero's on-disk data structures and local stores | Performance findings about them |
| `docs/BUILD_RECONFIG.md` | The autotools re-configure trap and its options | Anything not about configure |
| `zcash-lint/ZEROPERF.md` | What the vendored Zcash linters are, and which findings are set aside | Lint results |
| `reporoot/*.md` | Transient drafts and decision papers for Zero400-owned material: root-document reviews, open questions, migration and RPC plans (`docs/POLICY.md` S7.1) | Anything authoritative; disposition is the owner's |
| `keep/*.md` | Archived point-in-time notes, kept as written (S5): `Peer.md` node/RPC ops, `TENT.md` and `TENTZero.md` TENT lineage and port map, `ZcashV.md` 2026 Sprout/Orchard vulnerabilities across zcashd forks, `ZeroWallet_Design.md` Qt wallet design (out of node scope, kept as reference) | Anything durable or maintained; these are not updated |

Rules, ownership, retention and lab discipline: **`docs/POLICY.md`**.
