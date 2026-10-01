# Plan

The single register of perf work: what to decide, what to do, and in what
order, grouped by module. Each item names the document section that holds its
analysis, or carries the analysis in a paragraph below its table.

Status carries two independent ratings:

| Axis | Values | Means |
|------|--------|-------|
| **Kanban** | ToDo, InProgress, InTest, Finished | where the card is |
| **Disposition** | Open, Blocked, Fixed, Postponed, Aside | what happened to the issue |

Vocabulary is `POLICY.md` "Status vocabulary". A card is not Finished until
its result is recorded where the subject lives. `P` ids are node code owned by
Zero; every other id is lab, harness or documentation work in this tree.
Items keep their id when they move; a former id is noted as "was".

---

## Pick up here

Release build, gates green: `zero-gtest` 221 (via `qa/zcash/test_filters.sh`),
Boost clean, `validate.sh` PASS.

**Sequence.** Steps 1-3 approved 2026-09-30. Measurements wait for a fresh
session after these changes are built, committed and released.

1. *Records:* N21 `runtime_record` in the remaining launchers, with an audit
   of their rows; N24 original-archive n=4 (short; runs with N21's checks).
2. *Correctness:* P13 two missing tests -- each must fail with the skip
   reverted or the disk re-check removed, and pass now.
3. *Recording coverage:* N23 witness and wallet runs into RecBench, on the
   N21 path. Also N25, N20, N22 as harness cleanups alongside.
4. *Measurements, postponed to a fresh session:* decision 8 `-par=4` rerun
   with thermal sampling, K9 post-Sapling rematch, K8 CPU profile refresh --
   one idle-host slot, standard lab config.
5. *Needs inputs this host lacks:* A4, A3, A10, A12 need the golden fat and
   p1 wallets; A9 needs `fulltip-812-datadir`, which `prep_lab_datadir.sh`
   recreates from `chainblocks812-clean.tgz`.

Parked: group Q, Y1, group F (no Linux host), P18.

**Needs a scheduled slot:** A4 overnight `-rescan` remeasure, which finishes
A1 -- F2 a first non-macOS capture, which needs a Linux host -- F3 a
disposable tip above height 492,850 with notes in range, which gates A3 --
P19 the `src/snark/` delete, which the maintainer runs.

**Settled, do not re-derive.** The lock instrument's 2.9M and 4.46M totals
were acquisition counts; the real figure is six recursive sites at 5.92 per
block, all inherited lock-per-function composition (`LOCKS.md` "What
recursion actually exists"). C3's premise was wrong: `httpserver.cpp` replies
HTTP 503 and `bitcoin-cli.cpp` throws on it.

**Harness rules.** Rebuild clean after `./configure` -- it regenerates
makefiles without invalidating objects, so an incremental build carries new
flags only in recompiled units; check with `nm src/zerod` and the binary
timestamp. Never compare debug and release timings (tiny reindex 131 s
release, 363 s debug). Run the test suites sequentially. `validate.sh` fails
`buildconfig` while a debug binary is in the tree.

---

## Decisions outstanding

| # | Decision | Bearing |
|---|----------|---------|
| 1 | Documentation target shape | Group D |
| 2 | `z_sendmany` note reservation: explicit locking, or a documented single-worker constraint | B4 |
| 3 | Gated RPC: one shared in-flight slot, or per-method slots | C5 |
| 4 | `nTimeVerify`: relabel cumulative, report exclusive, or both | P1 |
| 5 | librustzcash base: stay pinned, or move to a fork's newer base | Y3 |
| 6 | `equ/README.md` and `reporoot/`: fold the index into `equ/METHOD.md`; keep, move out of tree, or delete `reporoot/` under the root-directory rule | D9 |
| 7 | Groth16 batch verification: Option A or B -- deferred by the maintainer until this consolidation is released | Y1 |
| 9 | **Decided 2026-09-30:** the standard lab config is minimal -- no Insight indexes and no other special flags (`dbcache`, `txindex`, witness flags) unless a trial names them as its condition. `tiny_baseline.sh` applies it; `ZERO_PERF_ARCHIVE_CONF=1` reproduces the historical archive config | N20 |
| 8 | `-par` cap: keep 16, cap at 7 (~0.6% slower above the checkpoint), or cap at 4 (1.2-2.9% slower, 10 fewer threads on a 14-core host); a `-par=4` rerun with thermal sampling would narrow that range | P20 |

---

## A. Wallet: witnesses and note selection

Analysis: `WITNESS.md`; wallet code changes: `PRODUCT.md`.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| A1 | Invalidate the note index only on membership change (was P2) | InTest | Open | `WITNESS.md` "The note index" |
| A4 | Remeasure fat-wallet `-rescan` after A1; overnight, scripted, outside the harness | ToDo | Open -- needs a slot | `WITNESS.md` "Cost" |
| A7 | Flag collapse: one `-walletwitness` mode, NOTEIDX always on | ToDo | Blocked on A4 | `WITNESS.md` "Ship state" |
| A2 | Review the note-index specification for redundancy | InTest | Open | Done by the `WITNESS.md` rewrite; confirm on review |
| A3 | Benchmark both witness bottlenecks post-Sapling | ToDo | Blocked on A1, F3 | `WITNESS.md` "Cost" |
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
| P10 | Explicit parameters at defaulted call sites: done at the five `GetFilteredNotes` callers, values unchanged; full gate green | InTest | Open | `PRODUCT.md` "P10. Explicit parameters at defaulted call sites" |

A9 uses `reindex-profile/fulltip-812-datadir`, recreated from `chainblocks812-clean.tgz` by `prep_lab_datadir.sh`; the tiny-snap result
(0.75-1.2 s) does not transfer to ~513k UTXOs. A12 expects `getblockcount` to
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
| B4 | `z_sendmany` does not lock the notes it selects; `z_mergetoaddress` selection can overlap it (was P9). A code comment was tried and reverted: it was inaccurate and belongs in `LOCKS.md` | ToDo | Open -- decision 2 | `LOCKS.md` "Shielded note selection and the single async worker" |
| B6 | Async worker experiments: one then several workers, idle and loaded | ToDo | Blocked on B4 | `CONCURRENCY.md` "Read-only RPC under concurrency" |
| P20 | Cap `MAX_SCRIPTCHECK_THREADS`; `-rpcthreads` 4 -> 2. A/B measured: serial -6.1%, 4 workers -2.9% (n=3; -1.2% without one slow trial), 7 workers -0.6% | ToDo | Open -- decision 8 | `CONCURRENCY.md` "`-par` sizing: is the default right?" |
| B1 | Locking validation method: order, balance, races, contention, throughput | ToDo | Open | `CONCURRENCY.md` "Validating locking across the codebase" |
| B7 | `TRY_LOCK` paths are uninstrumented; all lock results come from a single-worker reindex | ToDo | Open | `LOCKS.md` "Open" |

Finished: B2 `IsInitialBlockDownload` hoist (was P21), B3 recursive sites (was
P14), B5 P25 claim retracted.

---

## C. Logging and RPC server

Inventory: `log_inventory.py`, 1,388 call sites, 590 gated, 798 always-on, 31
categories. No owning document yet; C1's output creates one.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| C1 | Catalogue log outcomes; propose a disposition per class | ToDo | Open | -- |
| C2 | Review level and category assignment (was P16) | ToDo | Blocked on C1 | below |
| C4 | Alerting: what an operator must see, and how | ToDo | Blocked on C2 | -- |
| P18 | `debug.log` is not trimmed in practice: 570 MB on the live node, trimmed only at startup | ToDo | Postponed | below |
| C3 | Confirm whether a queue-full rejection reaches the client | Finished | Fixed -- no change needed | below |
| C5 | Gated RPC entry points: one shared guard keyed by RPC name | ToDo | Open -- decision 3 | `PRODUCT.md` "Option B -- one shared gate, keyed by RPC name (recommended)" |
| C6 | Record the `-rpcthreads` / `-rpcworkqueue` distinction and its measured effect | ToDo | Open | below |

**C2.** After gating the two largest sources a tiny reindex still logs
187,827 lines / 40 MB, about one per block. Bucket them by message prefix;
for each bucket above ~1%, check `LogPrintf` (unconditional) versus
`LogPrint` (categorised) and propose a category for anything that is neither
an error nor a state transition. `UpdateTip` stays: every measurement reads it.

**P18** (`test-logs/p18-shrink-20260922/`). The call is
`GetBoolArg("-shrinkdebugfile", !fDebug)`, so any `-debug` category disables
trimming, and a trim also needs a restart. Zcash and Ycash comment the call
out; Pirate and Hush3 gate it as Zero does. Fix: rotation on a periodic size
check; `debuglog.py --rotated` already reads the rotated names.

Live node, no `-debug`: `debug.log` is 570 MB, of which 2,549,445 lines are
the initial import on one day -- one `UpdateTip` per block for the whole
chain. Follow-tip then adds ~1,000 lines/day. The size comes from a full sync,
and nothing bounds it until the node restarts; a periodic size check with
rotation covers both this and the `-debug` case.

**C3** (`test-logs/c3-workqueue-20260930T082448Z/`). With `-rpcthreads=1
-rpcworkqueue=1`, 12 concurrent `gettxoutsetinfo` calls gave 10 rejections;
every rejected client exited 1 with `error: server returned HTTP error 503`,
and the server logged one line for the episode. The earlier "no
client-visible error" came from a load script that did not check per-request
status. The client does not print the reply body ("Work queue depth
exceeded"), so the 503 carries no reason.

**C6.** One note in `CONCURRENCY.md`: `-rpcthreads` is how many requests are
served at once, `-rpcworkqueue` how many may wait. Measured: 7 "work queue
full" rejections at depth 4, 0 at depth 16, identical load. Deployment values
are the Insight repository's.

---

## K. Block validation and import

Analysis: `SYNC.md`.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| P1 | Proof-verification counters and phase timers that cover proof work | InTest | Open -- decision 4 | `PerfTimers.md`; `SYNC.md` "Where the time goes" |
| P13 | Redundant Equihash verification: skip landed in `37f3f3459`; per-caller `ZERO_PERF` counters added (`pow.cpp`, `main.cpp`) and measured 2.00 calls/block; two validation tests missing | InTest | Open | `SYNC.md` "Equihash verifications per block" |
| P24 | `getchaintips` is O(chain length) | ToDo | Open | below |
| K1 | `nNotarizations` can only be 0: implement the heuristic or remove the field | ToDo | Open | `SYNC.md` "Memory" |
| K2 | Size the ~176 B/block shielded-index layout cost; gate it out of `CBlockIndex` if worthwhile | ToDo | Open | `SYNC.md` "Memory" |
| K3 | Thermal state over long runs: `postsapling_reindex.sh` samples `pmset -g therm` into `util.tsv`; other launchers not yet. macOS only (`pmset`; `NA` elsewhere) and coarse -- a warning level, not frequency; Linux reads `/sys/class/thermal` and `cpufreq`. One M-PAR-AB-700K trial ran 4-8% slow in every band at unchanged process CPU with nothing sampled to explain it | InTest | Open | -- |
| K4 | P2P follow-tip from the archive template (DNS seeds, distinct rpcport); full bootstrap ingest later | ToDo | Open | -- |
| P8 | FDCACHE disposition | ToDo | Postponed | `SYNC.md` "Disk I/O and FDCACHE" |
| K5 | Era-bounded rematch using shielded density bands (L3) | ToDo | Postponed | `Measures.md` M-DENS-* rows |
| K6 | Stack-logged allocation window entirely post-Sapling | ToDo | Aside -- unlikely to change the conclusion | `SYNC.md` "Memory" |
| K7 | Post-Sapling bootstrap capture | ToDo | Aside -- bootstrap and reindex agree within ~3 points per bucket | `SYNC.md` "Where the time goes" |
| K8 | Refresh the six-capture CPU profile (M-CPU-SEQ) on the current build: it predates uniblake, the Equihash skip and the IBD hoist, and still shows Equihash at 0.252 ms/block against 45 us measured now | ToDo | Open | `SYNC.md` "Where the time goes" |
| K9 | Stock reindex h600k-900k, n=4, current release: the before/after for M-RX-POSTSAP-STOCK (298.45 blk/s) across uniblake, the Equihash skip and the IBD hoist | ToDo | Open | `README.md` "postsapling_reindex.sh" |

P1 gates any phase summary: proof verification sits in no timer, so a summary
built today omits most post-Sapling cost while appearing complete.

**P24** (`test-logs/rpc-test-20260917/`). Measure insert and erase separately
before choosing a fix. The ordered set is maintained continuously by its
comparator and only 214 survivors need ordering; not materialising the full
set may remove the cost.

Finished: P17 out-of-order children (no change needed), P23 comparator single
`CompareTo`, Equihash BLAKE2b via uniblake (`SYNC.md` "Shipped changes"), and
E2: the non-blake2b libsodium surface is under 1% of `zcash-loadblk` CPU,
ed25519 the only primitive that registers (`test-logs/sodiumbuckets-20260922/`).

---

## Y. Proof verification

Analysis: `PerfGroth.md`, `LIBRUSTZCASH.md`.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| Y1 | Groth16 batch verification: Option A (hand-port) or B (adopt `sapling-crypto`) | ToDo | Postponed -- decision 7 | `PerfGroth.md` "4. The decision: Option A vs Option B" |
| Y2 | Build librustzcash on rustc 1.98.1 | ToDo | Open | `LIBRUSTZCASH.md` "4. Remaining validation, and what it costs" |
| Y3 | Vendor librustzcash in-tree; then decide the base | ToDo | Open -- decision 5 | `LIBRUSTZCASH.md` "3. Recommendation" |
| P19 | Delete unbuilt `src/snark/` | ToDo | Open -- maintainer runs the delete | below |
| R3 | `CBLAKE2bWriter` on uniblake | ToDo | Postponed | `HASHLIBS.md` "C. `CBLAKE2bWriter` and the four one-shot sites" |

**P19.** 284 KB, 30 files, in no makefile, no objects, no includes; entered as
a subtree in `f4d8cd127`. Zcash removed libsnark in `9ce0caf20` (v2.1.0);
Pirate, Hush3 and Firo have too. Zero and Zclassic still carry it; Zero does
not compile it.

R2 (share of a one-shot digest spent on parameter-block setup) is a property
of the kernel library and is measured in its tree, not here.

---

## Q. Equihash mining solver

Parked. `equ/` is left as is until work resumes; this section is its state.

**What `equ/` holds.** Six files, 4,302 lines: `README.md` (an index, inclusion
rules and a redundancy analysis -- meta-documentation under `POLICY.md` rule
2), `FINDINGS.md` (solve measurements and the size of the gap), `SOLVER.md`
(solver internals), `VENDORED.md` (lineage, tromp versus default, what an
update would buy), `METHOD.md` (how to measure and validate), `PLAN.md`
(stages S1-S4 and a queue carried over from `TASKS.md` whose ids D1-D5
collide with group D here).

**Shipped.** tromp is the default solver (`miner.cpp:544`), with a guard
falling back to the reference solver off (192,7), pinned by
`miner_tests/equihashsolver_default_and_param_guard`; 5.69x
(M-EQ-TROMP-SPEEDUP). The sort comparator fold, 1.22x, is committed
(`05cdcefe6`). `Xc.reserve()` removes 5-7 reallocations per round on the
reference solver, which mining no longer selects.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| Q3 | Revalidate the committed sort fold against the 5-solution baseline (V2) | ToDo | Postponed | below |
| Q2 | Measure the threaded tromp solver (was E4, P22) | ToDo | Postponed | below |
| Q4 | Per-phase CPU profile of a mainnet (192,7) solve (G5) | ToDo | Postponed | `README.md` "mine_bench.sh" |
| Q5 | Deployment fleet mix (INV-ARM-MIX); gates any ARM SIMD work | ToDo | Postponed | -- |
| Q6 | Solver stages S1-S4: memory, SIMD, multi-core, GPU | ToDo | Postponed | `equ/PLAN.md` "9. Sequencing and honest expectations" |
| Q8 | Release note for the tromp default | ToDo | Open | -- |
| Q9 | Stamp variant and UTC into solver dump paths; `eqbench.sh` wrapper; solver variant registry | ToDo | Postponed | below |
| Q10 | Review `equ/` under the writing rules; move its queue into this register; resolve the index file; repoint its citations of `docs/FINDINGS.md`, `docs/TASKS.md` and `Perf.md`, several of which named sections that no longer existed | ToDo | Postponed -- decision 6 | -- |

**Q3.** The 1.22x was taken on a working-tree patch; no recorded run confirms
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
constant in N (~3.3 GB per instance, M-EQ-PEAK-TROMP).

**Q9.** `DUMP_1927_SOLVER` writes the same filename each run; the baseline
dump is the V2 oracle, so every write must carry variant and UTC.

---

## N. Measurement harness and recording

Analysis: `HOWTO.md`, `SCHEMA.md`, `recbench/RecBench.md`.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| N2 | `op` enum validated by RecBench; back-annotate `op` and `era` on the 49 v2 rows | ToDo | Open | `SCHEMA.md` "4.3 Workload classes" |
| N3 | `wallet_shape`, derived `era`, pooling guard on `op` and `era` | ToDo | Blocked on N2 | `SCHEMA.md` "4.3 Workload classes" |
| N4 | Fingerprint v2 and the cross-platform pooling guard | ToDo | Blocked on F2 | `SCHEMA.md` "6.4 Fingerprint v2" |
| N6 | One datadir-protection implementation; timeout-guarded `cli()` in `perflib.sh` | ToDo | Open | below |
| N5 | `witness_lab.sh` passes numbers to `ops-campaign.sh` as prose | ToDo | Open | below |
| N7 | State the restartability axis beside the ~20 min heuristic | ToDo | Open | `POLICY.md` "Lab discipline" |
| N1 | Microbenchmark baseline, 4 of 17 run (was E3, A3) | InTest | Open | below |
| N9 | Per-workload utilization profile, generated from the ledger | ToDo | Blocked on N2 | below |
| N8 | Checkpoint progress series to the ledger; collate the series, not the endpoint | ToDo | Postponed to N9 | below |
| N11 | Move the stray `contrib/perf/test-logs/eqsolve-fixednonce-20260826/` into root `test-logs/` | Finished | Fixed | below |
| N12 | Check that figures in documents carry an `M-*` id, and that tracked documents hold no absolute paths (was A1c) | ToDo | Open | `POLICY.md` "What enforces what" |
| N10 | `profile_run.sh` wrote output relative to the current directory | Finished | Fixed | -- |
| N13 | `postsapling_reindex.sh`: declares its runtime flags to RecBench (rows had read wallet-on); adds `parN` conditions and `INTERLEAVE=1`; skips `bootstrap.dat*` in the scratch rsync. The one misstated row is re-recorded and the original retired | Finished | Fixed | `README.md` "postsapling_reindex.sh" |
| N14 | `recbench.py --superseded` without `--record` or `--import-tsv` now exits 2; self-test asserts it (mutation-tested) | Finished | Fixed | -- |
| N16 | Runtime recorded as run: `debuglog.py --check-runtime` derives it from the node's zero.conf plus command line and checks it against the log (wallet, script threads, dbcache); `perflib.sh runtime_record` is the one entry point; `tiny_baseline.sh` and `postsapling_reindex.sh` use it and refuse a mismatching row. Self-tests mutation-tested. 13 tiny-baseline rows re-recorded with the archive's runtime | InTest | Open | `README.md` "postsapling_reindex.sh" |
| N15 | Snapshot archives were not lost: the previous datadir was renamed to `~/Library/Application Support/zero.save` and holds tiny, short, postsap12, `chainblocks812.tgz` and `-clean.tgz`; tiny and short verify against their recorded sha256. Launchers still point at the default datadir. The tiny archive carries a `zero.conf` with Insight and dbcache=512. Rebuilt copies (now under `/tmp/zero_old`) are not needed | ToDo | Open -- point launchers at the archive location | `README.md` "Snapshot archives: the Insight flags are required" |
| N18 | `tiny_baseline.sh` depended on the archive carrying a `zero.conf`; it now writes a minimal lab one when absent | Finished | Fixed | -- |
| N19 | Build identity: `build_id` is version + commit + dirty flag + compiled features, so two different dirty trees on one commit pool as one build. Record a hash of the `zerod` binary in `build` and include it in `build_id` | ToDo | Open | `SCHEMA.md` "2. Version block -- `build`" |
| N20 | One lab `zero.conf` source: a `perflib.sh` helper over `contrib/zero-conf.sh`'s `lab` template plus explicit keys, used by every launcher, which writes its own conf rather than inheriting an archive's. Three sources today: the template (`ops-validate.sh` only), seven inline writers, and the conf carried inside the tiny/short archives. `runtime_record` already makes whichever was used visible | ToDo | Open | -- |
| N21 | Wire `runtime_record` into `wallet_sync_profile.sh`, `witness_lab.sh`, `mine_bench.sh`, `ops-validate.sh`, `bench_matrix.sh`; audit their existing rows for undeclared conf keys the way tiny-baseline was | ToDo | Open | -- |
| N22 | One copy of each launcher helper in `perflib.sh`: `cli` (5 copies), `stop_node` (4), `height_of` (3), `sample_util`, `kill_pid_hard`, `wait_done_loading` (2 each); and one `record_trial` wrapper around `recbench.py --record` that applies `runtime_record`, the input hash and the `util.tsv` path | ToDo | Open | -- |
| N23 | `wallet_sync_profile.sh` and `witness_lab.sh` do not record to RecBench; their results reach `Measures.md` by hand only | ToDo | Open | -- |
| N24 | Same build, same standard lab config, same tip: the original tiny archive gave 1,544 blk/s (n=1) against 1,590 (n=4) for the rebuilt height-ordered archive. The archives differ in block file layout (P2P order, full 128 MiB files vs height order, truncated file). Take n=4 on the original archive on an idle host; if the gap holds, block layout matters and every snapshot must be identified by hash, not name | ToDo | Open | `Measures.md` M-RX-TINY-20260930 |
| N25 | Sibling-repository locations resolved the way `depends/` finds its local sources: `ops-validate.sh` finds `linearize/` beside this tree or the product tree (`LINEARIZE_DIR` overrides) and warns when the original `bootstrap.dat` cannot be found, instead of silently skipping its copy check; a RecBench project root may name the build's own override variable, and a missing root is an error. Tested: the original is refused via its lab symlink; a missing root names both overrides | InTest | Open | `recbench/RecBench.md` "Roots, and running standalone" |
| N17 | Build and test the `--enable-perf` configuration: builds; Boost no errors, GTest 221/221 with `ZERO_PERF` defined. Not yet part of any gate | InTest | Open | -- |

**N6.** `perflib.sh:147`, `prep_lab_datadir.sh:37` and `datadir_guard.sh:33`
each implement the guard that stops a lab destroying the live datadir; the
latter two should call `_perflib_is_protected`. `res_sample.sh:34` wraps
`cli()` in `timeout` and `witness_lab.sh:78` does not -- the unguarded one is
the `getwalletinfo`/`cs_wallet` blocking hazard. Source `perflib.sh` in the
remaining scripts in the same change.

**N5.** The producer writes `wall_s=$elapsed` into `SUMMARY.txt` and the
consumer recovers it by regex; an integer-only pattern truncated `141.763` to
`141`. Write a `key=value` file the consumer sources, or a RecBench row.

**N1.** `verifysaplingspend` / `verifysaplingoutput` and their `create`
counterparts are recorded (M-ZCB-SAP-VERIFY, M-ZCB-SAP-CREATE) -- the
per-proof baseline Y1 needs. `parameterloading` fails with RPC error -3. The
other thirteen include several that need a populated wallet.
`test-logs/a3-zcbench-20260910/`.

**N9.** Columns by class (`SCHEMA.md` "4.3 Workload classes"): A/B -- blk/s,
CPU% of one core, threads, bucket shares, height window; C -- adds witness
share, `mapWallet` size, wallet MB, tx count; D -- s/solve, Sol/s, peak
physical MB. Era is a column split on A/B rows. Architecture is a column
split, never a pooled mean. Unmeasured cells stay empty and named. Network
sync rows (`op: sync`) carry peer count, tip distance at start, per-region
rate, stall events and min/max, n >= 3. The fat rescan (hours, one indivisible
scan) and `many-utxo-few-tx` (no wallet exists) are the cells that cannot be
filled on demand.

**N8.** `checkpoint_row()` in `perflib.sh` appends to `progress.tsv`;
`res_sample.sh` gains that output mode; `recbench.py --import-tsv` collates
post-run. A single blk/s hides a 28% spread across height bands
(M-LAB-BAND-TINY).

**N11.** Every launcher writes `$REPO_ROOT/test-logs`, `retention.py` and
`DATA_INDEX.md` read it, and the documents cite `test-logs/` from the root.
The one run under `contrib/perf/test-logs/` was written from inside
`contrib/perf/` and is cited from `equ/` as if at the root.

---

## F. Cross-platform

Analysis: `PerfPlatforms.md`. Every measurement is macOS/arm64 on one host.
Linux items are remeasures; Windows items are first builds.

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| F1 | Linux VPS and Windows/WSL runbook (was B2) | ToDo | Open | `PerfPlatforms.md` "6. Recommendations, ranked" |
| F2 | First non-macOS capture | ToDo | Blocked on F1, host | `PerfPlatforms.md` "3.1 CPU profiling -- the direct xctrace equivalent" |
| F3 | Disposable tip above height 492,850 with fat-wallet notes in range | ToDo | Open | -- |
| F4 | Re-validate the consolidated tree on another platform | ToDo | Blocked on F2, D1 | -- |
| F5 | CI: add the working branch to the push trigger; lint job ahead of the 240-minute build | ToDo | Postponed -- needs repository settings | -- |
| F6 | Port `res_sample.sh` to `psutil` | ToDo | Blocked on host | `PerfPlatforms.md` "3.3 Resource sampling" |
| F7 | Cold-cache measurement (`drop_caches`); FDCACHE on Linux and Windows | ToDo | Blocked on F2 | `SYNC.md` "Disk I/O and FDCACHE" |
| F8 | Retest the `--strict` / `--suite` release track on Linux | ToDo | Blocked on host | -- |
| F9 | Windows MXE cross-build, never run here; then hardening and ETW profiling | ToDo | Blocked on host | `PerfPlatforms.md` "4. Windows 11" |
| F10 | Release engineering: params archival, branch-id CI, OpenSSL 3, Debian packaging | ToDo | Postponed | -- |
| F11 | Document the `parse()` input contract in `bucket_profile2.py` | ToDo | Open | -- |

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

Rules: `POLICY.md` "The accretion rule" and "Writing rules". Target: about ten
tight documents in `docs/`, each owning one module or subject.

**State.** `docs/` has 29 files. Work state was split across `TASKS.md`,
`equ/PLAN.md`, `Perf.md` and `RecBench.md`; `TASKS.md` and `Perf.md` are now
absorbed here, `equ/` is parked (group Q), and `RecBench.md` has no open
tasks.

**Target shape** (decision 1):

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

Moved to `retired/`: `TASKS.md`, `FINDINGS.md`, `NOTES.md`. Next once emptied:
`PRODUCT.md`.

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| D6 | Reconcile `POLICY.md`; writing rules; root-directory rule | InTest | Open |
| D2 | `Perf.md` rewritten by module as `SYNC.md` and `WITNESS.md`; `FINDINGS.md` carved up | InTest | Open |
| D4 | One register: `TASKS.md` open items migrated here | InTest | Open |
| D7 | `docmap` ratchet: fail if a directory's file count rises above its recorded value | ToDo | Open |
| D8 | Writing-rules pass per file, starting with `PerfGroth.md`, `PRODUCT.md`, `HOWTO.md`, `Measures.md` | ToDo | Open |
| D1 | Merge to the target shape, one absorbed file per commit, each net-negative | InProgress | Open |
| D3 | Section-number citations to heading titles; `check_citations.py` fails on section numbers and bare file names | ToDo | Blocked on D1 |
| D5 | Fold the platform tool survey into the F1 runbook | ToDo | Blocked on F1 |
| D9 | `equ/README.md` index and `reporoot/` drafts | ToDo | Blocked on decision 6 |
| D12 | Delete `retired/` files whose content is extracted: `TASKS.md`, `FINDINGS.md`, `NOTES.md`, `ZcashV.md` (covered by Zero `ZcashFixes.md`) | ToDo | Open -- needs confirmation |

`retention.py` protects any `test-logs/` run cited from a `.md` file under
`contrib/perf/`, including `retired/`; deleting a retired file can make its
cited runs reclaimable. Check `retention.py --candidates` before and after.

---

## H. Process

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| H1 | No presentation-only edits to inherited files; `validate.sh` check | Finished | Fixed |
| H2 | A card finishes only with its result recorded; `validate.sh` check | ToDo | Open |

H1: formatting changes only inside a hunk already changed for a functional
reason. H2 exists because a fix reached the tree with a correct in-code
comment and no record anywhere.

---

## Z. Handoff to Zero

Not performance work. Recorded here until Zero takes each item; this tree
does not edit root or Zero-owned documents.

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| P26 | Root `README.md` line 1 carries stray text `concept` before the banner image | ToDo | Open |
| Z4 | `AtHeight.md`, `TEST_ZERO.md`, `UpdateZero.md`, `ZcashFixes.md`, `ZeroStruct.md` name the product tree `Zero400`; use the repository name, `Zero` | ToDo | Open |
| Z1 | `TENTZero.md` (TENT-to-Zero zeronode port map) and `TENT.md` (TENT lineage), held in `retired/`, belong in Zero, which cites the map from `UpdateZero.md`, `ZeroNodes.md` and `ZeroNodeDev.md` (11 sites, one by a stale absolute path) | ToDo | Open |
| Z2 | Zeronode test track TST-03 / TNT-12 / DOC-02: argument validation on existing Boost; founders window; two-node `startalias`; zeronode `invalidateblock` after A5 | ToDo | Open |
| Z3 | `Peer.md` (node and RPC operations notes, held in `retired/`); cited by `Measures.md` M-PEER-LOAD and `Stores.md` | ToDo | Open |
