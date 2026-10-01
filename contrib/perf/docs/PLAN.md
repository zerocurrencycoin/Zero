# Plan

The single register of perf work: what to decide, what to do, and in what
order, grouped by module. Each item names the document section that holds its
analysis, or carries the analysis in a paragraph below its table.

Status carries two independent ratings:

| Axis | Values | Means |
|------|--------|-------|
| **Kanban** | ToDo, InProgress, InTest, Finished | where the card is |
| **Disposition** | Open, Blocked, Fixed, Postponed, Aside | what happened to the issue |

Vocabulary is `POLICY.md` "Status". A card is not Finished until
its result is recorded where the subject lives. `P` ids are node code owned by
Zero; every other id is lab, harness or documentation work in this tree.
Items keep their id when they move. A pending decision is carried by the
item it governs: its Disp reads `decision:` and states the options.

---

## Pick up here

Release build; `zero-gtest`, Boost and `validate.sh` gates green.

**Sequence.** Steps 1-3 approved 2026-09-30. Measurements wait for a fresh
session after these changes are built, committed and released.

1. *Records:* N21 steps 1-2, `runtime_record` in the remaining launchers
   with an audit of their rows; N15 original-archive n=4 (short; runs with
   N21's checks).
2. *Correctness:* P13 two missing tests -- each must fail with the skip
   reverted or the disk re-check removed, and pass now.
3. *Recording coverage:* N21 steps 3-6, witness and wallet runs into
   RecBench and one copy of each launcher helper. N25 and N20 alongside.
4. *Measurements, postponed to a fresh session:* P20 `-par=4` rerun with
   thermal sampling, K8 remeasures -- one idle-host slot, standard lab config.
5. *Needs inputs this host lacks:* A4, A3, A10, A12 need the golden fat and
   p1 wallets; A9 needs `fulltip-812-datadir`, which `prep_lab_datadir.sh`
   recreates from `chainblocks812-clean.tgz`.

Parked: group Q, Y1, group F (no Linux host), P18.

**Needs a scheduled slot:** A4 overnight `-rescan` remeasure, which finishes
A1 -- F2 a first non-macOS capture, which needs a Linux host -- A3's
disposable tip above height 492,850 with notes in range 

**Settled, do not re-derive.** The lock instrument's 2.9M and 4.46M totals
were acquisition counts; the real figure is six recursive sites at 5.92 per
block, all inherited lock-per-function composition (`LOCKS.md` "What
recursion actually exists").

**Harness rules.** Rebuild clean after `./configure` -- it regenerates
makefiles without invalidating objects, so an incremental build carries new
flags only in recompiled units; check with `nm src/zerod` and the binary
timestamp. Never compare debug and release timings. Run the test suites sequentially. `validate.sh` fails
`buildconfig` while a debug binary is in the tree.

---

## A. Wallet: witnesses and note selection

Analysis: `WITNESS.md`; wallet code changes: `PRODUCT.md`.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| A1 | Invalidate the note index only on membership change | InTest | Open | `WITNESS.md` "The note index" |
| A4 | Remeasure fat-wallet `-rescan` after A1; overnight, scripted, outside the harness | ToDo | Open -- needs a slot | `WITNESS.md` "Cost" |
| A7 | Flag collapse: one `-walletwitness` mode, NOTEIDX always on | ToDo | Blocked on A4 | `WITNESS.md` "Ship state" |
| A2 | Review the note-index specification for redundancy | InTest | Open | Done by the `WITNESS.md` rewrite; confirm on review |
| A3 | Benchmark both witness bottlenecks post-Sapling, on a disposable tip above height 492,850 with fat-wallet notes in range | ToDo | Blocked on A1 and the tip | `WITNESS.md` "Cost" |
| A10 | p1 rescan profile; first confirm by timing that p1 runs long enough to profile | ToDo | Open | `WITNESS.md` "Cost" |
| A5 | Replace the null-`pindex` `exit(1)` paths with rebuild-or-clear recovery | ToDo | Open | `WITNESS.md` "Reorg and crash" |
| A6 | Height walk drops `cs_main` periodically and aborts on tip change; then the R5c e2e | ToDo | Open | `WITNESS.md` "Reorg and crash" |
| A8 | Reorg cap versus witness cache size; cache never shorter than the apply cap (TNT-03) | ToDo | Blocked on A5 | `WITNESS.md` "Reorg and crash" |
| A11 | Excessive reorg: reject and stay up instead of `StartShutdown()` (TNT-02); then R5d | ToDo | Postponed | `WITNESS.md` "Reorg and crash" |
| A9 | `getalldata` datatype matrix at a quiet full tip (BENCH-GAD-IDX1) | ToDo | Open | below |
| A12 | Lab soak under rebuild: status polling, spend storm under -31, `getalldata` after rebuild | ToDo | Open | below |
| A13 | `CDB::Rewrite` spins with no log or timeout; upstream, all Zcash-family forks | ToDo | Open | -- |
| P4 | Witness RPC gate inconsistent | InTest | Open | `PRODUCT.md` "P4. The witness RPC gate is inconsistent, and the family disagrees about it" |
| P5 | `boost::optional` to `std::optional` | ToDo | Open | `PRODUCT.md` "P5. Migrate `boost::optional` to `std::optional`" |
| P6 | Anchor depth for shielded spends; subsumes what remains of P4 | ToDo | Blocked on P5 | `PRODUCT.md` "P6. Anchor depth for shielded spends" |
| P7 | Coin-selection call clarity -- find existing coverage first | ToDo | Open | `PRODUCT.md` "P7. Coin-selection call clarity: adopt Ycash's shape, not TENT's" |
| P27 | `-salvagewallet` help and some test fixtures say `wallet.dat`; the runtime default is `wallet.zero` | ToDo | Open | `Stores.md` "Berkeley DB, Wallet Compatibility, And Local DB Direction" |
| P10 | Explicit parameters at defaulted call sites: done at the five `GetFilteredNotes` callers, values unchanged; full gate green | InTest | Open | `PRODUCT.md` "P10. Explicit parameters at defaulted call sites" |

A9 uses `reindex-profile/fulltip-812-datadir`, recreated from `chainblocks812-clean.tgz` by `prep_lab_datadir.sh`; the tiny-snap result
does not transfer to a full tip. A12 expects `getblockcount` to
stall for the walk's duration on `cs_main` and then succeed; every spend under
-31 must fail cleanly; `getalldata` latency, RSS and response size after
rebuild for datatypes 0 and 1.

Finished: DIRTY parked (`WITNESS.md` "Mechanisms"); opt-in package ready to
ship.

---

## B. Locking and concurrency

Analysis: `LOCKS.md`, `CONCURRENCY.md`.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| B4 | `z_sendmany` does not lock the notes it selects; `z_mergetoaddress` selection can overlap it. A code comment was tried and reverted: it was inaccurate and belongs in `LOCKS.md` | ToDo | Open -- decision: explicit locking, or a documented single-worker constraint | `LOCKS.md` "Shielded note selection and the single async worker" |
| B6 | Async worker experiments: one then several workers, idle and loaded | ToDo | Blocked on B4 | `CONCURRENCY.md` "Read-only RPC under concurrency" |
| P20 | Cap `MAX_SCRIPTCHECK_THREADS`; `-rpcthreads` 4 -> 2; A/B M-PAR-AB-700K | ToDo | Open -- decision: keep 16, cap at 7, or cap at 4; the `-par=4` rerun with thermal sampling settles the cost of 4 | `CONCURRENCY.md` "`-par` sizing: is the default right?" |
| B1 | Locking validation method: order, balance, races, contention, throughput. Known gaps: `TRY_LOCK` paths are uninstrumented, and all lock results come from a single-worker reindex | ToDo | Open | `CONCURRENCY.md` "Validating locking across the codebase"; `LOCKS.md` "Open" |

Finished: B2 `IsInitialBlockDownload` hoist, B3 recursive sites, B5 P25 claim
retracted. B7 merged into B1.

---

## C. Logging and RPC server

Inventory: `log_inventory.py --summary`. No owning document yet; C1's output
creates one.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| C1 | Catalogue log outcomes; propose a disposition per class | ToDo | Open | -- |
| C2 | Review level and category assignment | ToDo | Blocked on C1 | below |
| C4 | Alerting: what an operator must see, and how | ToDo | Blocked on C2 | -- |
| P18 | `debug.log` is unbounded: trimmed only at startup, and never with `-debug` (N29) | ToDo | Postponed | below |
| C5 | Gated RPC entry points: one shared guard keyed by RPC name | ToDo | Open -- decision: one shared in-flight slot, or per-method slots | `PRODUCT.md` "Option B -- one shared gate, keyed by RPC name (recommended)" |
| C6 | Record in `CONCURRENCY.md` the `-rpcthreads` / `-rpcworkqueue` distinction, its measured effect, and what a rejected client sees | ToDo | Open | below |

**C2.** After gating the two largest sources a tiny reindex still logs
about one line per block (M-LOG-TINY). Bucket them by message prefix;
for each bucket above ~1%, check `LogPrintf` (unconditional) versus
`LogPrint` (categorised) and propose a category for anything that is neither
an error nor a state transition. `UpdateTip` stays: every measurement reads it.

**P18** (`test-logs/p18-shrink-20260922/`). Mechanics are in N29. Zcash and
Ycash comment the call out; Pirate and Hush3 gate it as Zero does. On a live
node without `-debug` the file is dominated by the initial import, one
`UpdateTip` per block for the whole chain (M-LOG-LIVE), and nothing bounds
it until a restart. Fix: rotation on a periodic size check, which covers the `-debug`
case too; `debuglog.py --rotated` already reads the rotated names.

**C6.** `-rpcthreads` is how many requests are served at once,
`-rpcworkqueue` how many may wait. At equal load, depth 4 rejected requests
and depth 16 did not. A rejection reaches the client as HTTP 503 and exit 1,
without the reason ("Work queue depth exceeded"), and the server logs one line
per episode (`test-logs/c3-workqueue-20260930T082448Z/`).

Finished: C3.

---

## K. Block validation and import

Analysis: `SYNC.md`.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| P1 | Proof-verification counters and phase timers that cover proof work | InTest | Open -- decision: `nTimeVerify` relabelled cumulative, reported exclusive, or both | `PerfTimers.md`; `SYNC.md` "Where the time goes" |
| P13 | Redundant Equihash verification: skip landed in `37f3f3459`; per-caller `ZERO_PERF` counters added (`pow.cpp`, `main.cpp`), M-EQ-VERIFY-SITES; two validation tests missing | InTest | Open | `SYNC.md` "Equihash verifications per block" |
| P24 | `getchaintips` is O(chain length) | ToDo | Open | below |
| K1 | `nNotarizations` can only be 0: implement the heuristic or remove the field | ToDo | Open | `SYNC.md` "Memory" |
| K2 | Size the ~176 B/block shielded-index layout cost; gate it out of `CBlockIndex` if worthwhile | ToDo | Open | `SYNC.md` "Memory" |
| K3 | Thermal state over long runs: `postsapling_reindex.sh` samples `pmset -g therm` into `util.tsv` and `capture_sequence.sh` into each capture snapshot; other launchers not yet. macOS only (`pmset`; `NA` elsewhere) and coarse -- a warning level, not frequency; Linux reads `/sys/class/thermal` and `cpufreq`. One M-PAR-AB-700K trial ran slow in every band at unchanged process CPU with nothing sampled to explain it | InTest | Open | -- |
| K10 | Port `getaddrmaninfo` / `getrawaddrman` from Bitcoin Core before writing a bespoke `peers.dat` parser | ToDo | Open | `Stores.md` "Peers.dat Decoding And Recovery" |
| K4 | P2P follow-tip from the archive template (DNS seeds, distinct rpcport); full bootstrap ingest later | ToDo | Open | -- |
| P8 | FDCACHE disposition; cold-cache (`drop_caches`) and Linux/Windows measurement need F2 | ToDo | Postponed | `SYNC.md` "Disk I/O and FDCACHE" |
| K5 | Era-bounded rematch using shielded density bands (L3) | ToDo | Postponed | `Measures.md` M-DENS-* rows |
| K6 | Stack-logged allocation window entirely post-Sapling | ToDo | Aside -- unlikely to change the conclusion | `SYNC.md` "Memory" |
| K7 | Post-Sapling bootstrap capture | ToDo | Aside -- bootstrap and reindex agree within ~3 points per bucket | `SYNC.md` "Where the time goes" |
| K8 | Remeasure on the current build, one idle-host slot: the six-capture CPU profile (M-CPU-SEQ), which predates uniblake, the Equihash skip and the IBD hoist and overstates Equihash; and stock reindex h600k-900k, n=4, the before/after for M-RX-POSTSAP-STOCK | ToDo | Open | `SYNC.md` "Where the time goes"; `README.md` "postsapling_reindex.sh" |

P1 gates any phase summary: proof verification sits in no timer, so a summary
built today omits most post-Sapling cost while appearing complete.

**P24** (`test-logs/rpc-test-20260917/`). Measure insert and erase separately
before choosing a fix. The ordered set is maintained continuously by its
comparator and only 214 survivors need ordering; not materialising the full
set may remove the cost.

Finished: K9 merged into K8, P17 out-of-order children (no change needed), P23 comparator single
`CompareTo`, Equihash BLAKE2b via uniblake (`SYNC.md` "Shipped changes"), and
E2 non-blake2b libsodium surface (`HASHLIBS.md` "A. The non-blake2b libsodium
surface").

---

## Y. Proof verification

Analysis: `PerfGroth.md`, `LIBRUSTZCASH.md`.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| Y1 | Groth16 batch verification: Option A (hand-port) or B (adopt `sapling-crypto`) | ToDo | Postponed -- decision: Option A or B, deferred by the maintainer until this consolidation is released | `PerfGroth.md` "4. The decision: Option A vs Option B" |
| Y2 | Build librustzcash on rustc 1.98.1 | ToDo | Open | `LIBRUSTZCASH.md` "4. Remaining validation, and what it costs" |
| Y3 | Vendor librustzcash in-tree; then decide the base | ToDo | Open -- decision: stay pinned, or move to a fork's newer base | `LIBRUSTZCASH.md` "3. Recommendation" |
| P19 | Delete unbuilt `src/snark/`: done in this tree (`f34332af9`); Zero still carries it | InTest | Open -- Zero applies it with the other changes in `reporoot/MAINTREE_CHANGES.md` | below |
| R3 | `CBLAKE2bWriter` on uniblake | ToDo | Postponed | `HASHLIBS.md` "C. `CBLAKE2bWriter` and the four one-shot sites" |

**P19.** In no makefile, no objects, no includes; entered as
a subtree in `f4d8cd127`. Zcash removed libsnark in `9ce0caf20` (v2.1.0);
Pirate, Hush3 and Firo have too. Zero and Zclassic still carry it; Zero does
not compile it.

R2 (share of a one-shot digest spent on parameter-block setup) is a property
of the kernel library and is measured in its tree, not here.

---

## Q. Equihash mining solver

Parked. `equ/` is left as is until work resumes; this section is its state.

**What `equ/` holds.** `README.md` (an index, inclusion
rules, figures, next actions and a dated review), `FINDINGS.md` (solve measurements and the size of the gap), `SOLVER.md`
(solver internals), `VENDORED.md` (lineage, tromp versus default, what an
update would buy), `METHOD.md` (how to measure and validate), `PLAN.md`
(stages S1-S4 and a queue whose ids D1-D5 collide with group D here).

**Shipped.** tromp is the default solver (`miner.cpp:544`), with a guard
falling back to the reference solver off (192,7), pinned by
`miner_tests/equihashsolver_default_and_param_guard` (M-EQ-TROMP-SPEEDUP).
The sort comparator fold is committed
(`05cdcefe6`). `Xc.reserve()` removes 5-7 reallocations per round on the
reference solver, which mining no longer selects.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| Q3 | Revalidate the committed sort fold against the 5-solution baseline (V2) | ToDo | Postponed | below |
| Q2 | Measure the threaded tromp solver | ToDo | Postponed | below |
| Q4 | Per-phase CPU profile of a mainnet (192,7) solve (G5) | ToDo | Postponed | `README.md` "mine_bench.sh" |
| Q5 | Deployment fleet mix (INV-ARM-MIX); gates any ARM SIMD work | ToDo | Postponed | -- |
| Q6 | Solver stages S1-S4: memory, SIMD, multi-core, GPU | ToDo | Postponed | `equ/PLAN.md` "9. Sequencing and honest expectations" |
| Q8 | Release note for the tromp default | ToDo | Open | -- |
| Q9 | Stamp variant and UTC into solver dump paths; `eqbench.sh` wrapper; solver variant registry | ToDo | Postponed | below |
| Q10 | Review `equ/` under the writing rules; move its queue into this register; delete `equ/README.md` | ToDo | Postponed with group Q | below |

**Q3.** The fold's speedup was taken on a working-tree patch; no recorded run confirms
the committed code still produces the five baseline solutions
(`test-logs/eqvectors/solver_baseline_192_7.txt`, archived and `0444`). One
run is the exit condition.

**Q2.** `EQUIHASH_TROMP_THREADED` compiles on macOS with the in-tree
`src/pow/tromp/osx_barrier.h`. Both production call sites construct
`equi eq(1)` and run the digit rounds inline; the threaded path needs
`worker()` (`equi_miner.h:769`) with a `thread_ctx` array and round barriers.
Steps: a threaded driver beside `EhTrompSolveRounds`; `SOLVE_TIMING_THREADS`
in the fixed-nonce harness; 1/2/4/8 threads on the same nonces with identical
solution sets at every width; `phys_mb` per width to confirm memory is
constant in N (M-EQ-PEAK-TROMP).

**Q10.** `POLICY.md` "Documents" permits one index, the
`README.md` documentation map, so `equ/README.md` goes rather than folding
into `METHOD.md`, whose subject is method. Each part has an owner: figures
and "What this analysis established" go to `equ/FINDINGS.md` where not already
there, "Next actions" to this register, the file table to the documentation
map. The dated set review is dropped.

**Q9.** `DUMP_1927_SOLVER` writes the same filename each run; the baseline
dump is the V2 oracle, so every write must carry variant and UTC.

---

## N. Measurement harness and recording

Analysis: `HOWTO.md`, `SCHEMA.md`, `recbench/RecBench.md`. Grouped by what
the work changes: the recorded row, the launchers, the lab inputs, the
evidence store, the checks.

### Recorded rows and their identity

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| N2 | Workload classes: `op` enum validated by RecBench and back-annotated with `era` on existing v2 rows; then `wallet_shape`, derived `era`, and a pooling guard on `op` and `era` | ToDo | Open | `SCHEMA.md` "4.3 Workload classes" |
| N4 | Row identity: a hash of the `zerod` binary in `build` and `build_id`, since two dirty trees on one commit now pool as one build; fingerprint v2 with platform; cross-platform pooling guard | ToDo | Open; the guard is blocked on F2 | `SCHEMA.md` "2. Version block -- `build`", "6.4 Fingerprint v2" |
| N9 | Per-workload utilization profile generated from the ledger, over checkpoint progress series rather than endpoints | ToDo | Blocked on N2 | below |

**N9.** Columns by class (`SCHEMA.md` "4.3 Workload classes"): A/B -- blk/s,
CPU% of one core, threads, bucket shares, height window; C -- adds witness
share, `mapWallet` size, wallet MB, tx count; D -- s/solve, Sol/s, peak
physical MB. Era and architecture are column splits, never pooled. Unmeasured
cells stay empty and named. Network sync rows (`op: sync`) carry peer count,
tip distance at start, per-region rate, stall events and min/max, n >= 3.
The fat rescan and `many-utxo-few-tx` cannot be filled on demand. Progress
series: `checkpoint_row()` in `perflib.sh` appends to `progress.tsv`,
`res_sample.sh` gains that output mode, `recbench.py --import-tsv` collates
post-run; one blk/s figure hides the spread across height bands
(M-LAB-BAND-TINY).

### Launchers

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| N21 | One `perflib.sh` path for every launcher: lab conf, declared runtime, recording, helpers | InProgress | Open | below |
| N7 | State the restartability axis beside the run-length heuristic | ToDo | Open | `POLICY.md` "Lab discipline" |

**N21.** Step 1 is in test; the rest in order.

1. Declared runtime: `debuglog.py --check-runtime` derives it from the
   node's `zero.conf` and command line and checks it against the log;
   `perflib.sh runtime_record` is the entry point; `tiny_baseline.sh` and
   `postsapling_reindex.sh` refuse a mismatching row.
2. One lab `zero.conf` writer in `perflib.sh` over `contrib/zero-conf.sh`'s
   `lab` template plus explicit keys; every launcher writes its own conf
   instead of inheriting an archive's. Today the template serves
   `ops-validate.sh` only, the other launchers write inline, and the tiny and
   short archives carry their own. Standard lab config, decided 2026-09-30:
   minimal -- no Insight indexes, no `dbcache`, `txindex` or witness flags
   unless a trial names them as its condition; `ZERO_PERF_ARCHIVE_CONF=1`
   reproduces the archive config.
3. `runtime_record` in `wallet_sync_profile.sh`, `witness_lab.sh`,
   `mine_bench.sh`, `ops-validate.sh`, `bench_matrix.sh`; audit their
   existing rows for undeclared conf keys.
4. One `record_trial` wrapper over `recbench.py --record`, applying
   `runtime_record`, the input hash and the `util.tsv` path. The wallet and
   witness launchers record through it instead of by hand, and
   `witness_lab.sh` hands `ops-campaign.sh` that row instead of
   `SUMMARY.txt` prose parsed by regex.
5. One copy of each launcher helper in `perflib.sh` (`cli`, `stop_node`,
   `height_of`, `sample_util`, `kill_pid_hard`, `wait_done_loading`), with
   `cli()` under `timeout`: an unguarded `getwalletinfo` blocks on
   `cs_wallet`. `prep_lab_datadir.sh` and `datadir_guard.sh` call
   `_perflib_is_protected` instead of their own copies.

### Lab inputs

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| N15 | Lab inputs located and identified: snapshot archives and sibling repositories | InProgress | Open | below |

**N15.** Sibling repositories, in test: `ops-validate.sh` finds `linearize/`
beside this tree or the product tree (`LINEARIZE_DIR` overrides) and warns
when the original `bootstrap.dat` is missing instead of skipping its copy
check; a RecBench project root may name the build's override variable, and a
missing root is an error (`recbench/RecBench.md` "Roots, and running
standalone").

Snapshot archives: they are in `zero.save`, beside the default datadir; tiny
and short verify against their recorded sha256. Launchers still point at the
default datadir. The original tiny archive ran slower than the rebuilt
height-ordered one at the same build, config and tip (M-RX-TINY-20260930);
they differ in block file layout. Take n=4 on the original on an idle host;
if the gap holds, layout matters and snapshots are identified by hash.

### Evidence store: `test-logs/`

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| N27 | `test-logs/` cleanup, validation and reconciliation | ToDo | Open | below |
| N28 | Loose files at the top of `test-logs/` | ToDo | Open | below |
| N29 | `debug.log` handling and size, node and lab | ToDo | Open | below |

**N27.** Rules: `POLICY.md` "Cleaning up". Tool: `retention.py` classifies
and never deletes; its self-test runs in `lint-perf.sh`. Missing:

- Reconciliation: a check, run from `validate.sh`, that every run
  `Measures.md` and `PLAN.md` name exists. M-LAB-REPRO cites a driver log
  that does not exist.
- Rules for the store: what a run directory must contain (driver log,
  measures, recorded rows) before it counts as complete.

**N28.** `retention.py` classifies directories only, so top-level files
(`validate-*.log`, tiny-baseline `-driver.log` / `.jsonl` /
`-progress.tsv`, `measures_*`) are never classified. Launchers write each run
into its own directory; existing loose files are grouped by run prefix.

**N29.** One item for every `debug.log` question.

- Node: P18. `ShrinkDebugFile` (`util.cpp`) runs only at startup
  (`init.cpp`) and, above 10 MB, keeps the last 200 KB, losing the startup
  record; `GetBoolArg("-shrinkdebugfile", !fDebug)` disables it whenever a
  `-debug` category is on.
- Volume: C2, about one line per block after gating.
- Lab: each `postsapling_reindex.sh` trial keeps its whole `debug.log` after
  its rows are recorded; these files are most of `test-logs/` by size.
  `retention.py` reports `.trace`, `.xml` and archives as trimmable, not
  these. Add per-trial `debug.log`, trimmed to the lines extraction reads,
  once the run's rows are in the ledger, and have `retention.py` report the
  bytes so no document needs to.

### Checks and build

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| N12 | Extend `check_citations.py` rules 1-2 from `docs/` to every owned document | ToDo | Open | `POLICY.md` "Enforcement" |
| N17 | `--enable-perf` configuration in a gate: it builds, and Boost and GTest pass with `ZERO_PERF` defined | InTest | Open | -- |
| F11 | Document the `parse()` input contract in `bucket_profile2.py` | ToDo | Open | -- |

### Coverage

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| N1 | Microbenchmark baseline: the rest of the `zcbenchmark` suite | InTest | Open | below |

**N1.** Recorded: `verifysaplingspend` / `verifysaplingoutput` and their
`create` counterparts (M-ZCB-SAP-VERIFY, M-ZCB-SAP-CREATE), the per-proof
baseline Y1 needs. `parameterloading` fails with RPC error -3. Several of
the rest need a populated wallet.

Finished: N10, N11, N13, N14, N18. Merged: N3 into N2; N19 into N4; N8 into
N9; N5, N6, N16, N20, N22, N23 into N21; N24, N25 into N15.

---

## F. Cross-platform

Analysis: `PerfPlatforms.md`. Every measurement is macOS/arm64 on one host.
Linux items are remeasures; Windows items are first builds.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| F1 | Linux VPS and Windows/WSL runbook, folding in the platform tool survey | ToDo | Open | `PerfPlatforms.md` "6. Recommendations, ranked" |
| F2 | First non-macOS capture | ToDo | Blocked on F1, host | `PerfPlatforms.md` "3.1 CPU profiling -- the direct xctrace equivalent" |
| F4 | Re-validate the consolidated tree on another platform | ToDo | Blocked on F2, D1 | -- |
| F5 | CI: add the working branch to the push trigger; lint job ahead of the 240-minute build | ToDo | Postponed -- needs repository settings | -- |
| F6 | Port `res_sample.sh` to `psutil` | ToDo | Blocked on host | `PerfPlatforms.md` "3.3 Resource sampling" |
| F8 | Retest the `--strict` / `--suite` release track on Linux | ToDo | Blocked on host | -- |
| F9 | Windows MXE cross-build, never run here; then hardening and ETW profiling | ToDo | Blocked on host | `PerfPlatforms.md` "4. Windows 11" |
| F10 | Release engineering: params archival, branch-id CI, OpenSSL 3, Debian packaging | ToDo | Postponed | -- |

While F5 is postponed every gate is local: a contributor who does not run
`lint-perf.sh` bypasses all of it.

---

## G. Testing and build

Analysis: `TESTING.md`.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| G1 | Suite plan: maturity constant, `initialize_chain_clean` ratio, 23 failures by mode | ToDo | Open | `TESTING.md` "Suite plan: constants, tiers, failure modes" |
| G2 | A bare GTest run aborts and prints no summary | ToDo | Open | `TESTING.md` "`CachedWitnessesCleanIndex` is held failing on purpose" |
| G3 | An autotools re-run inherits no `CONFIG_SITE`; touches Zero-owned `configure.ac` | ToDo | Open | `BUILD_RECONFIG.md` "Hardening options, not implemented" |

---

## D. Documentation

Rules: `POLICY.md` "Documents"; writing rules are Zero's DOC-CONVENTIONS. Target: about ten
tight documents in `docs/`, each owning one module or subject.

`reporoot/` stays tracked as it is (decided 2026-09-30).

**Target shape** (D1):

| Target | Absorbs |
|--------|---------|
| `SYNC.md` | `PerfTimers.md`, block-storage parts of `Stores.md` |
| `WITNESS.md` | wallet analyses from `PRODUCT.md` (P4-P7, P10) |
| `PerfGroth.md` | `LIBRUSTZCASH.md` |
| `HASHLIBS.md` | `SODIUM_SURVEY.md` |
| `CONCURRENCY.md` | `THREADS.md`, `SCRIPTQUEUE.md`, `LOCKS.md` |
| `METHOD.md` | `HOWTO.md`, `CPU_MEASUREMENT.md`, `TOOLING_FAILURES.md`, `SCHEMA.md`, `RECORDS_READINESS.md`, `CROSSPROJECT.md`, `PerfPlatforms.md` |
| `TESTING.md` | `BUILDCONFIG.md`, `BUILD_RECONFIG.md`, `TSAN.md` |
| `Measures.md` | -- |
| `PLAN.md` | -- |
| `POLICY.md` | -- |

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| D1 | Merge to the target shape, one absorbed file per commit, each net-negative; `TOOLING_FAILURES.md` left as it is | InProgress | Open; `TOOLING_FAILURES.md` postponed 2026-10-01 | -- |
| D2 | Confirm the reorganisation: `SYNC.md` and `WITNESS.md` own their modules; this file is the one register | InTest | Open | -- |
| D6 | Rules in one place per scope: `POLICY.md` keeps the perf-specific rules; general writing rules defer to Zero's DOC-CONVENTIONS once adopted | InTest | Open | below |
| D8 | Writing-rules pass per file: narration, transient counts, deleted-file mentions, restated values. Done for `PLAN.md` | InProgress | Open | below |
| D10 | One manifest per kind of list, read by every script and document that needs it | ToDo | Open | below |
| D15 | `M-*` values stated once: in `Measures.md` | ToDo | Open | below |
| D3 | Section-number citations to heading titles; `check_citations.py` fails on section numbers, bare file names, a cited heading that does not exist, an `M-*` id with no row, and a path or script flag the tree lacks | ToDo | Blocked on D1 | -- |
| D11 | Reconcile `Stores.md` with this tree; verify the `txindex` default in Zero before stating it for all branches | InTest | Open | -- |

**D6.** The same writing rules are kept in four places: `POLICY.md`
"Documents", Zero's `UpdateZero.md` DOC-CONVENTIONS (draft, aimed at
`AGENTS.md` and the shared agent configuration), Zero's `AGENTS.md`
"Documentation" (copied into this tree), and the `docstruct` skill. They
overlap on history, filler, transient values and references, and differ in
detail. `POLICY.md` keeps what only this tree has: `M-*` citation, run
naming, ratchets, lab discipline, retention. The general rules are proposed
to Zero for DOC-CONVENTIONS (Z5) and cited from here once adopted.

**D8.** Keep history only where it records a decision and its reason, why a
check exists, or that a figure is superseded. Order: `PerfGroth.md`,
`PRODUCT.md`, `HOWTO.md`, `Measures.md`, then the rest; `lint-perf.sh`
`runs` lowers as each file loses run citations.

**D10.** Lists kept in more than one place, and the one source each should
have:

| List | Kept in | Source |
|------|---------|--------|
| Owned documents and directory classes | `README.md` map; `check_citations.py`, `fix_ascii.py`, `lint-perf.sh`, `retention.py`, `check_concentration.py` | `README.md` map, strict row format, parsed once in `check_docmap.py` |
| Tools and their invocation | `README.md` per-tool sections; `HOWTO.md` "Perf tooling in this directory"; `Measures.md` "Launch and tools matrix"; each script's header | the script's `--help`; a check that every tracked tool has one README section |
| Subject owners | `README.md` map; `check_concentration.py` `OWNERS` | a column in the map |
| Directory file-count ceilings | not kept | a column in the map, checked by `docmap` |

**D15.** `Measures.md` owns each value. Other documents cite the id, and
restate the value only where the argument uses it; a check compares any
restated value with the row. Overlaps to fold:

- `Measures.md` "Ledger campaigns" binds `CAMPAIGN=` to ids that the
  catalogue rows already carry: one `campaign` column in the catalogue.
- `Measures.md` "By application / use case" restates subject routing that
  the subject documents own: drop it.
- `Measures.md` "Launch and tools matrix": the tools list, D10.
- `test-logs/DATA_INDEX.md`, untracked, a dated index of numbers with
  sources and almost no ids: frozen as a point-in-time record, not cited.
- Subject documents and `README.md`: lines that restate a value beside its
  id, in `SYNC.md`, `WITNESS.md`, `CONCURRENCY.md`, `README.md` "Lab wallets".

Finished: D12. Merged: D4 into D2, D5 into F1, D7 into D10, D9 into Q10,
D13 and D14 into D8.

---

## H. Process

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| H1 | No presentation-only edits to inherited files; `validate.sh` check | Finished | Fixed |
| H2 | A card finishes only with its result recorded; `validate.sh` check | ToDo | Open |
| H3 | Item ids, names and status reconciled with Zero's `TODO.md` | ToDo | Open |
| H4 | Regroup items by module (table below), with H3 | ToDo | Postponed -- decided 2026-10-01 |

H1: formatting changes only inside a hunk already changed for a functional
reason. H2 exists because a fix reached the tree with a correct in-code
comment and no record anywhere.

**H3.** Zero labels items by area and name (`WAL-GETALLDATA-W5`, `TST-01`,
`REL-06`; prefixes CON, WAL, OPS, REL, EXT, TST, DOC, TNT) and states status
by list (Ordered next, Active, Pending). This register uses one letter per
group -- mnemonic for A wallet, B locking, C logging, D documentation, F
platforms, H process, P product, Z handoff; arbitrary for K, N, Q, Y, G --
and two status axes. Proposal:

- Ids: area prefix plus number (`WIT-01`), areas as in H4; items handed to
  Zero take Zero's prefix. Old ids appear once, in a mapping table, until the
  next release.
- Status: one value, mapped to Zero's lists -- Next, Active, InTest, Pending
  (with the condition or decision named), Aside, Finished. Kanban and
  Disposition collapse into it; `POLICY.md` "Status" changes with it.

**H4.** Proposed regrouping, by the module the work changes. Applied with
H3, one group per commit, results moved to owning documents and measured
values to `M-*` citations.

| Area | Subject | Items now |
|------|---------|-----------|
| WIT | Witness cache, note index, reorg and crash recovery | A1-A8, A10, A11, P4, P6 |
| WAL | Wallet RPC, note selection, async worker, product cleanups | A9, A12, A13, B4, B6, C5, P5, P7, P10, P27 |
| CONC | Thread pools, locking method, RPC server sizing | B1, C6, P20 |
| LOG | Log content, volume, trimming, alerting | C1, C2, C4, P18 |
| SYNC | Block validation and import cost | K1, K2, K5-K8, P1, P8, P13, P24 |
| NET | P2P follow-tip, peers | K4, K10 |
| PROOF | Groth16, librustzcash, hash libraries | Y1-Y3, P19, R3 |
| EQU | Mining solver | Q2-Q6, Q9, Q10 |
| LAB | Recorded rows, launchers, lab inputs, coverage | N1, N2, N4, N7, N9, N15, N21, K3 |
| STORE | `test-logs/` and its retention | N27, N28, N29 |
| CHECK | Lint, citation and doc checks, process gates | N12, N17, F11, D10, H1, H2 |
| PLAT | Non-macOS hosts | F1, F2, F4, F6, F8, F9 |
| REL | Release, CI, packaging; Zero's REL | F5, F10, Q8 |
| TST | Test suites and build configuration | G1-G3 |
| DOC | Documentation set | D1-D3, D6, D8, D11, D15 |
| ZERO | Handoff to Zero | Z2, Z5-Z10 |

Moves that change grouping, not only ids: K3 to LAB (a sampling feature of
the launchers), K4 and K10 to NET, B4, B6 and C5 to WAL (wallet RPC
concurrency), C6 to CONC, Q8, F5 and F10 to REL, D10 and H1-H2 to CHECK.
---

## Z. Handoff to Zero

Not performance work. This tree does not edit root or Zero-owned files; each
proposal is a draft in `reporoot/`, compared against a stated Zero commit
and kept to what is still pending.

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| Z6 | `reporoot/MAINTREE_CHANGES.md`: `src/` and `qa/` changes for Zero to review and apply, with release notes for behaviour changes | ToDo | Open |
| Z8 | `reporoot/LAYOUT.md`: `AtHeight.md` and `WitnessReindex.md` to `doc/design/`; stray `concept` on `README.md` line 1; delete `contrib/spendfrom/`; keep and rename `contrib/qos/` | ToDo | Open |
| Z9 | `reporoot/TODO.review.md`: three measurement items from `TODO.md` into this register | ToDo | Open |
| Z5 | `reporoot/DOC-CONVENTIONS.md`: writing rules proposed for DOC-CONVENTIONS | ToDo | Open |
| Z10 | `reporoot/MIGRATION_PLAN.md`: satellite repositories; commit uniblake's cited docs first | ToDo | Open -- decision: owner |
| Z2 | Zeronode test track, now Zero ZN-01 and DOC-02: argument validation on existing Boost; founders window; two-node `startalias`; zeronode `invalidateblock` after A5 | ToDo | Open |
| Z7 | Root documents here are older than Zero's (`UpdateZero.md` has no DOC-CONVENTIONS here); refresh them from Zero by merge, not by edit | ToDo | Open |

Finished: Z1 and Z4, fixed in Zero; P26 merged into Z8.
