# Benchmarking and profiling `zerod`

How to measure this node and how to read what comes back. `Perf.md` is the
investigation narrative and `Measures.md` is the numbers inventory; neither
teaches the workflow, so this does.

Two kinds of question, two kinds of tool, and they are not interchangeable:

- **"How fast?"** -- throughput campaigns, in blocks/sec and wall seconds.
- **"Why that fast?"** -- CPU profiling, in % of a thread and per function.

A throughput run proves a change helped; it cannot say where time went. A
profile says where time goes; it cannot say whether a change is worth shipping.
**Profile when you do not know the bottleneck; benchmark when you do and want
to prove a delta.** The FDCACHE buffer A/B measured four conditions and found
no difference; profiling the same workload afterwards showed one thread at 100%
CPU with disk syscalls under 5%, so an IO knob had nothing to act on. Run the
profile first and the A/B need not have been run at all.

---

# Part 1 -- Use cases

Each case below has been run. Commands are copy-pasteable from the repo root.

## 1.1 Profile a reindex (the default case)

```bash
SCRATCH=/tmp/zero-lab-reindex
rm -rf $SCRATCH && mkdir -p $SCRATCH
tar -xzf "$HOME/Library/Application Support/zero/chainblocks-tiny.tgz" -C $SCRATCH blocks
printf 'listen=0\nmaxconnections=0\nserver=1\nrpcuser=rt\nrpcpassword=rt\nrpcport=23970\ndisablewallet=1\n' > $SCRATCH/zero.conf

./src/zerod -datadir=$SCRATCH -reindex -daemon
sleep 20
contrib/perf/profile_run.sh S1-reindex-none $SCRATCH 60

./src/zero-cli -datadir=$SCRATCH -rpcport=23970 stop
rm -rf $SCRATCH
```

`profile_run.sh` does capture -> export -> thermal -> bucket -> collate and
derives the height window from `debug.log`. Expect (pre-Sapling):
groth16 ~43%, blake2b ~20%, tree ~13%, disk_decode ~10%, equihash ~8%,
disk_syscall ~5%.

**Gotcha:** the tiny snap tops out at h187417 and the short snap at **h245992**
-- both pre-Sapling. Neither reaches Sapling activation (492850). A run
labelled "post-Sapling" from those snaps is mislabelled.

## 1.2 Profile post-Sapling without the 8.5G archive

Block data is `blocks/blk*.dat`, written sequentially in 42 files of ~128 MB,
so a file prefix is a valid chain prefix. Twelve files reach h583699+.

```bash
tar -xzf "$HOME/Library/Application Support/zero/chainblocks-postsap12.tgz" \
    -C $SCRATCH blocks          # 1.65G, ~15 min to post-Sapling
```

To rebuild that archive from the live datadir:

```bash
mkdir -p /tmp/trim/blocks
B="$HOME/Library/Application Support/zero/blocks"
for i in $(seq -w 0 11); do cp "$B/blk000$i.dat" /tmp/trim/blocks/; done
(cd /tmp/trim && COPYFILE_DISABLE=1 tar -czf out.tgz blocks)
```

`COPYFILE_DISABLE=1` matters: macOS `tar` otherwise writes AppleDouble `._*`
entries into the archive.

Expect post-Sapling: **groth16 88-91%**, everything else collapsing. Leaf
frames shift from `Fr::mul_assign` (Sprout scalar field) to `Fq::mul/sqr/add`
and `G1::CurveProjective` (Sapling base field).

## 1.3 Profile a wallet rescan

```bash
cp "$HOME/Library/Application Support/zero/wallet.zeroP0" $SCRATCH/wallet.zero
./src/zerod -datadir=$SCRATCH -rescan -daemon
sleep 12
contrib/perf/profile_run.sh S5-rescan-fat $SCRATCH 60 "Main Thread"
```

**The thread filter is mandatory here.** The wallet walk runs on `Main Thread`,
not `zcash-loadblk`; the default filter returns "no samples on thread".

**Gotcha:** a p0 wallet (106KB) rescans in **2 ms**. There is nothing to
profile -- any capture taken shows concurrent block connection instead. Only
the fat wallet (749MB, 801619 tx) produces a rescan worth measuring.

## 1.4 Profile bootstrap import

```bash
cp ~/Work/ZK/linearize/bootstrap.dat $SCRATCH/bootstrap.dat   # a COPY, always
./src/zerod -datadir=$SCRATCH -loadblock=$SCRATCH/bootstrap.dat -daemon
sleep 30
contrib/perf/profile_run.sh S4-bootstrap-none $SCRATCH 60
```

`ops-validate.sh bootstrap` refuses the original file by design
(`resolve_file` compares against `$LINEARIZE_DIR/bootstrap.dat`, following
symlinks and `..`). Copy, never point at the original.

**Result to expect:** bootstrap, reindex and sync agree within ~3 points on
every bucket at the same heights. They differ in how blocks are *sourced*, not
in what validation costs -- do not spend capture budget re-proving this.

## 1.5 Measure throughput

```bash
CAMPAIGN=my-experiment contrib/perf/tiny_baseline.sh tiny    # ~3 min
```

Writes `test-logs/measures_<run>.csv` and appends to
`reindex-profile/bench-summaries/ledger.jsonl`.

**Run procedure.** Fixed height window, one condition per invocation, four
trials per condition, same binary and same host for every trial in a
comparison. Record the condition name in `CAMPAIGN=` so the collation groups
correctly. `accumulate_bench.py` writes n, mean, stdev, min and max per
condition into `REPORT.md`; report those fields as produced rather than
summarising them.

A repeat-run pair on an unchanged binary is recorded in the ledger
(`tiny-20260819T234958Z`, `tiny-20260819T235438Z`) and serves as the
same-configuration reference for this host.

## 1.6 Sample system resources during any run

```bash
contrib/perf/res_sample.sh out.tsv 5 $SCRATCH 23970 &
# ... run the workload ...
kill %1
```

Columns: CPU%, RSS, physical footprint, thread count, summed thread CPU, hot
thread %, host disk MB/s, pageins, compressed MB, height.

**Gotcha:** during a reindex the RPC worker is blocked, so `getblockcount`
times out; the sampler falls back to the last `UpdateTip` height in
`debug.log`. Without that fallback every height cell is empty and no row can be
attributed to a block range.

## 1.7 Witness walk cost from logs already on disk

```bash
contrib/perf/witness_walk_cost.py <debug.log> [--tsv]
```

Pairs the `height-walk begin` / `height-walk done` lines `BuildWitnessCache`
already emits. No node change, no new instrumentation. Measured:
**0.1530 ms/block with NOTEIDX** (380 walks) versus **5.31-5.72 ms/block
stock** -- a 35x difference, and the stock figure is a range, not a constant.

## 1.8 Accumulate and report

```bash
contrib/perf/profile_collate.py report
contrib/perf/profile_collate.py report --scenario S3-reindex-none-postsap
```

`profile_run.sh` collates automatically. Entries carry the full bucket map, so
a later bucket rename can be applied at read time without losing resolution.

---

# Part 2 -- Reading the output

`bucket_profile2.py` prints three views of the same samples. Using one alone is
the most common route to a wrong conclusion.

## 2.1 Buckets -- "where would a fix go"

Mutually exclusive, **first match wins on any frame in the stack**, so order is
load-bearing. Current order (`BUCKETS` in `contrib/perf/bucket_profile2.py`):

```
witness_cache -> wallet_add_ordered -> wallet_db -> wallet_other
  -> groth16_proof -> tree_anchor -> blake2b -> equihash
  -> disk_syscall -> disk_decode -> leveldb_db -> sha256_txhash -> connect_block
```

Two orderings are deliberate and must not be "tidied":

- **groth16 before tree_anchor.** `sapling_crypto::jubjub::edwards::Point`
  appears in both paths. Ordering tree first produced the M-CPU-LEGACY
  misbucket: "Tree 57-58%" with Groth16 folded in.
- **witness_cache before wallet_other.** A bare `CWallet::` needle otherwise
  swallows `VerifyAndSetInitialWitness`.

This is also why a bucket can read **0.00% for something plainly running**: a
rescan sample doing bls12_381 arithmetic inside a `CWallet::` call is
attributed to `witness_cache`, so `groth16_proof` reads 0.00% while 10.8% of
the leaves are bls12_381.

## 2.2 Layers -- "what kind of work is this"

Overlapping: a sample counts in **every** layer present, so shares exceed 100%
by design. This is the fix for the blind spot above.

| Capture | wallet | crypto | validation | io |
|---------|-------:|-------:|-----------:|---:|
| rescan fat, post-sap | 100.0 | **19.8** | -- | 13.0 |
| reindex p0 | 0.2 | 76.6 | 91.1 | 100.0 |

**Rule: any bucket reading 0.00% must be checked against layers before you
believe it.**

## 2.3 Leaves -- "which function"

Per-frame attribution near the leaf: `Fr::mul_assign`, `blake2b_compress_ref`,
`SelectWalletTxsForWitnessScan`. Buckets name the subsystem; leaves name the
function to open.

## 2.4 What changes the answer

| Factor | Effect | Evidence |
|--------|--------|----------|
| **Height region** | groth16 43% -> 88-91% across Sapling activation | S1 vs S3 captures |
| **Thread filter** | wrong filter returns nothing usable | loadblk 88.9% vs idle threads |
| **Wallet size** | none/p0/p1 all 0-0.32%; fat 72-99% *during rescan* | S1 p0/p1, S5 fat |
| **Operation type** | reindex/bootstrap/sync agree within ~3 points | S1/S4/S8 at same heights |

---

# Part 3 -- Gotchas and gaps

## 3.1 Traps that produced published wrong numbers

| Trap | What happened | Guard now |
|------|---------------|-----------|
| Bucket ordering | "Tree 57-58%" with Groth16 folded in | groth16 ordered first; comment in `BUCKETS` |
| Bare needle | `CWallet::` swallowed `VerifyAndSetInitialWitness` | narrow needles, specific before generic |
| Merged IO bucket | `disk_io` 14.66% vs 4.91% real syscall leaves | `disk_syscall` / `disk_decode` split |
| blake2b hidden | inside `equihash`, so no blake2b figure existed | own bucket, ordered before equihash |
| Wrong snap assumed | short snap assumed ~520k, actually **245992** | verify the tip a snap reaches |
| Conflated measures | 11.9h *rescan* cited as *witness walk* cost (walk was 2009ms) | read the M-* definition |
| Back-imported rows | 12 ledger rows share one timestamp, seeded from a July TSV | check `run_id` / `recorded_at` |
| Blocked RPC | height columns empty for a whole run | `debug.log` fallback in `res_sample.sh` |

## 3.2 Known gaps

- **No post-Sapling bootstrap, sync, or fat-wallet-reindex capture.** Only
  reindex has both regions.
- **p1 has no rescan capture**; the wallet-size curve has a hole between p1
  (0.32%) and fat (72-99%).
- **Thermal is recorded but never non-Nominal**, because every capture so far
  is 60s. A multi-hour run has never been checked for throttling.
- **No always-on timing.** All instrumentation is opt-in; a slow node in the
  field yields no evidence.
- **`-debug=bench` is unused by any campaign** despite giving a free per-block
  phase breakdown.

---

# Part 4 -- Tool reference

## 4.1 Perf tooling in this directory

| Tool | Invocation | Notes |
|------|-----------|-------|
| `profile_run.sh` | `<scenario> [datadir] [secs] [thread]` | end-to-end; defaults 60s, `zcash-loadblk`. Env: `ZERO_PROFILE_OUT`, `ZERO_PROFILE_NOTE` |
| `bucket_profile2.py` | `<export.xml> [thread] [--json out]` | buckets + layers + pools + leaves |
| `profile_collate.py` | `add <json> --scenario S --window A-B [--note]` / `report [--scenario S]` | CPU ledger |
| `res_sample.sh` | `<out.tsv> [period_s] [datadir] [rpcport]` | env `ZERO_RES_RPC_TIMEOUT` (default 3s) |
| `witness_walk_cost.py` | `<debug.log>... [--tsv]` | reads existing logs only |
| `tiny_baseline.sh` | `tiny\|short` | env `CAMPAIGN`, `LAB` |
| `postsapling_reindex.sh` | `stock\|nofdcache\|defaultbuf\|1mbbuf` | FDCACHE A/B |
| `bench_matrix.sh` | see header | reindex vs bootstrap matrix |
| `capture_sequence.sh` | `<datadir> <out> [period] [secs] [max]` | repeated captures over a long run |
| `mine_bench.sh` | `regtest\|mainnet-template\|neon-probe` | env `MINE_BLOCKS` |
| `witness_lab.sh` | `dirty-cont\|rebuild\|rebuild-noteidx\|tip-rebuild\|tip-rebuild-note\|rescan-noteidx\|catchup-noteidx` | env `ZERO_PERF_WALLET_FILE` required |
| `ops-campaign.sh` | `list\|run` | 11-trial catalog, `cycle_trials.tsv` |
| `prep_lab_datadir.sh` | `create\|unroll` | env `LAB`, `ARCHIVE`, `SRC` |
| `wallet_sync_profile.sh` | `tiny\|short\|full` | env `ZERO_PERF_WALLET_FILE` |
| `shielded_density.py` | see header | note density by height band |
| `extract_measures.py` | `--bench` ingests `-debug=bench` lines | |
| `accumulate_bench.py` | `--store-dir --md --json` | throughput ledger |
| `decode_captures.py` | `<capture dir>` | batch-decode a capture sequence |
| `stall_check.py`, `debuglog.py` | see headers | log analysis |
| `measure_dbcache_utxo.py` | env `ZERO_MEASURE_DBCACHE`, `_MATRIX`, `_BLOCKS`, `_INSIGHT` | dbcache/UTXO matrix (M-CACHE-MATRIX) |
| `performance-measurements.sh` | `<benchmark> [args]`, run from repo root | `zcbenchmark` / valgrind runner (M-ZCB-SUITE); 19 named benchmarks |
| `collate_cycle.py` | `--md <out.md>` | collate an `ops-campaign` cycle |
| `datadir_guard.sh` | sourced, not executed | `refuse_live_datadir`; env `ZERO_PERF_ALLOW_LIVE_DATADIR` to override |
| `check-unicode.py` | `[--fix] [--all] [paths]` | non-ASCII policy |
| `lint-perf.sh` | `[--all] [--summary] [--list]` | gated to `contrib/perf/` |
| `zcash-lint/` | vendored Zcash linters | see `ZEROPERF.md` |

## 4.2 Node flags that matter

| Flag | Effect |
|------|--------|
| `-reindex` | rebuild chainstate from `blk*.dat` |
| `-loadblock=<file>` | bootstrap import |
| `-rescan` | wallet re-derive over existing chainstate |
| `-disablewallet` | ConnectBlock control, no wallet cost |
| `-debug=<cat>` | 30 categories; **`bench`** gives per-block phase timing |
| `-walletwitness=ibd-defer` | defer witness build during IBD |
| `-walletwitnessnote` | NOTEIDX; 35x on the witness walk |
| `-perffdcache`, `-perfbufsize` | require `--enable-perf` build |
| `-mrclogevery=N` | root-latch log interval (default 16384) |

Build with instrumentation: `./autogen.sh && ./configure --enable-perf && make`
(defines `ZERO_PERF` and `ZERO_FDCACHE`; default off).

## 4.3 System tools

| Tool | Use | Privilege |
|------|-----|-----------|
| `xcrun xctrace record` | `--template 'Time Profiler' --time-limit Ns --attach PID` | none |
| `xcrun xctrace export` | `--xpath '/trace-toc/run[1]/data[1]/table[@schema="time-profile"]'` | none |
| `xcrun xctrace export --toc` | list all 23 schemas in a trace | none |
| `sample <pid> <secs>` | cheap stack sampler, no Instruments | none |
| `ps -M -p <pid>` | per-thread CPU; **%CPU is field 2 on thread rows, 4 on the process row** | none |
| `footprint -p <pid>` | physical footprint incl. compressed pages | none |
| `vmmap -summary <pid>` | dirty/swapped breakdown | none |
| `iostat -d -w 1 -c 2 disk0` | host disk MB/s | none |
| `vm_stat` | pageins, compressor | none |
| `powermetrics`, `fs_usage` | per-process IO, power | **sudo** (unavailable here) |

## 4.4 Ledgers and where results land

| Path | Contents |
|------|----------|
| `reindex-profile/bench-summaries/cpu_ledger.jsonl` | CPU shares per capture |
| `reindex-profile/bench-summaries/ledger.jsonl` | throughput, 35 rows |
| `reindex-profile/bench-summaries/REPORT.md` | collated throughput with n, stdev, min/max |
| `test-logs/DATA_INDEX.md` | every recent number with its source log |
| `test-logs/<run>/` | per-run artifacts |
| `Measures.md` | published numbers bound to `M-*` ids |

## 4.5 Rules that keep results usable

1. Every number needs a **window and a thread**; a bare percentage is not comparable.
2. **Collate immediately** -- `profile_run.sh` does it; a stray text file will not be found.
3. **Record trial count with every figure.** `REPORT.md` and
   `profile_collate.py report` both emit n; carry it forward when citing.
4. **Check thermal on long runs**; a capture drifting to Serious is two machines.
5. **Mark superseded results, do not delete them** -- M-CPU-LEGACY stays in
   `Measures.md` marked superseded, so nobody re-derives it.
