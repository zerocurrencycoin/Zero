# Plan

The single register of perf work. Sections 1-3 are what to do now and what
needs a decision; sections 4-12 hold every item by subject, each row with
its schedule state, so a subject can be reviewed in one place. Analysis
lives in the subject document a row points to; this file carries one-line
state, order, and detail no subject document owns.

Columns: **When** is the schedule -- *Baseline* (in section 2), *Next*
(ready, ranked first), *Ready*, *Waits: X*, *Postponed*, *Aside*. **Kanban**
(ToDo, InProgress, InTest, Finished) and **Disp** (Open, Blocked, Fixed,
Postponed, Aside) follow `POLICY.md` "Status". A card is not Finished until
its result is recorded where the subject lives. `P` ids are node code owned
by Zero; every other id is lab, harness or documentation work in this tree.
Items keep their id when they move; decisions are per item.

---

## 1. Start here

State: Boost (incl. the six P13 tests), `lint-perf.sh`, `perflib_selftest.sh`
and `validate.sh` green. Baseline 1 steps 1-2 done except committing; uncommitted: P13 tests, the A8
pin, C7, C8, documents, `lint_backlog.json` removal; commands in
`test-logs/commit-steps-20261006.md`.

Session rules: start at the worktree root, the `ZeroPerf` checkout, and use
paths, never `cd`; work in Zero's tree from a session opened in the
`Zero401` checkout. Benchmarks only on an idle host: no build, test run or
other `zerod`. Keep lab inputs out of `/tmp`, whose lab directories this
host moves into `/tmp/zero_old` at midnight.

Restart prompt:

```
cd /Users/walter/Work/ZK/ZeroPerf && claude
ZeroPerf, branch perf_b1b2, worktree root; never cd. Read
contrib/perf/docs/PLAN.md sections 1-3 and contrib/perf/docs/POLICY.md.
If test-logs/commit-steps-20261006.md has not run, run it first; then the
first open step of PLAN.md section 2. Gates before and after a change:
contrib/perf/lint-perf.sh, contrib/perf/validate.sh. Root and Zero-owned
files are read-only except src/ changes listed in reporoot/MAINTREE_CHANGES.md.
```

Harness rules: rebuild clean after `./configure` -- it regenerates makefiles
without invalidating objects, so an incremental build carries new flags only
in recompiled units; check with `nm src/zerod` and the binary timestamp.
Never compare debug and release timings. Run the test suites sequentially.
`validate.sh` fails `buildconfig` while a debug binary is in the tree.

---

## 2. Baseline 1

The next consistent point: one commit and one build in which every item is
implemented, set aside or dropped, its results collected, analysed and
recorded, and the next phase laid out. Exit when every step is done.

| # | Step | Items | Done when |
|---|------|-------|-----------|
| 1 | Commit the remaining working-tree changes; fast-forward `perf-402`; push | -- | `git status` clean, both branches pushed |
| 2 | Close what only needs confirming: done | A2, P10, D2, D11, N17, N21 | closed (section 15) |
| 3 | Hand-off batches 1 and 2 to Zero, one commit per subject: postponed, batches recorded in `reporoot/MAINTREE_CHANGES.md` "Hand-off batches" | Z6 | when review resumes |
| 4 | Bring Zero's result back here, so this line differs from Zero only by perf-only code and `contrib/perf`: postponed with step 3 | Z7 | after step 3 |
| 5 | Clean release build of that commit; full gates: Boost, GTest, `contrib/run-tests.sh --all`, `lint-perf.sh`, `validate.sh` | -- | all green, logs in `test-logs/` |
| 6 | Measure that build on an idle host | K8, K11, N15 (original archive, n>=6) | rows recorded, `M-*` ids bound |
| 7 | Analyse and record: `SYNC.md` "Where the time goes" against the new profile; supersede what it replaces | K8, K11 | subject documents cite only current ids |
| 8 | Every remaining InTest item closed, or carried with a stated reason | A1, P1, P4, N1, D6 | no InTest row without a reason |
| 9 | Lay out the next phase: section 3 answered, `Next` rows ranked | -- | this file reviewed |
| 10 | Delete the session documents in `test-logs/` that this file now covers | -- | done |

---

## 3. Needs your call

| # | Question | Options | Default if unanswered |
|---|----------|---------|-----------------------|
| 1 | B4: note selection in `z_sendmany` | explicit note locking; or a documented single-worker constraint | documented constraint |
| 2 | C5: gated RPC entry points | one shared in-flight slot keyed by RPC name; or per-method slots | shared slot (`PRODUCT.md` recommends) |
| 3 | P1: `nTimeVerify` reporting | relabel cumulative; report exclusive; both | both |
| 4 | P20: script-check thread cap | keep 16; cap at 7; cap at 4 (needs one idle-host `-par=4` rerun) | keep 16 |
| 5 | F5: propose the workflow change to Zero | now; later | later (Postponed) |

---

## 4. A -- Wallet: witnesses, rescan, note selection

Analysis: `WITNESS.md`; wallet code changes: `PRODUCT.md`.

| Id | Item | When | Kanban | Disp | Detail |
|----|------|------|--------|------|--------|
| A14a | Rescan detection and reporting: log when `-rescan` comes from `zero.conf`; log a `stop` requested during a rescan with the height reached; rescan progress in `getwalletinfo`; log the end as complete or interrupted | Next | ToDo | Open | section 14, C9 |
| A14b | Rescan operation and recovery: shutdown check every batch, wallet locator at the last scanned block, resume on restart, one rescan at a time, reorg handling, then lock release between batches | Ready | ToDo | Open -- after A14a | `LOCKS.md` "Designs for the open work" 2 |
| A15 | Restart detection and reporting: at startup, log why a reindex, rescan or witness rebuild runs (flag and its source, or the wallet locator's gap) and warn on `reindex=` / `rescan=` in `zero.conf` | Next | ToDo | Open | section 14, C9 |
| A6 | Height walk drops `cs_main` periodically and aborts on tip change; then the R5c e2e. The walk runs at the tip with stock flags too | Next | ToDo | Open | `LOCKS.md` "Designs for the open work" 3 |
| A5 | Replace the null-`pindex` `exit(1)` paths with rebuild-or-clear recovery: unreachable from current callers; the guards report and exit | Postponed | ToDo | Postponed -- decided 2026-10-06 | section 14, C9 |
| A7a | Witness flag surface, parts needing no measurement: `-walletwitness=stock|defer|rebuild` (`ibd-defer` kept as an alias), stats under `-debug=witness`, one `WitnessReady { NotBuilt, Building, Ready }` replacing `initWitnessesBuilt` + `fBuildingWitnessCache`; RPC codes unchanged | Ready | ToDo | Open | `WITNESS.md` "Ship state" |
| A13 | `CDB::Rewrite` spins with no log or timeout; upstream, all Zcash-family forks | Ready | ToDo | Open | `LOCKS.md` "Designs for the open work" 6 |
| P27 | `-salvagewallet` help and some test fixtures say `wallet.dat`; the runtime default is `wallet.zero` | Ready | ToDo | Open | `Stores.md` "Berkeley DB, Wallet Compatibility, And Local DB Direction" |
| P5 | `boost::optional` to `std::optional` | Ready | ToDo | Open | `PRODUCT.md` "P5. Migrate `boost::optional` to `std::optional`" |
| P7 | Coin-selection call clarity -- find existing coverage first | Ready | ToDo | Open | `PRODUCT.md` "P7. Coin-selection call clarity: adopt Ycash's shape, not TENT's" |
| P4 | Witness RPC gate inconsistent | Baseline | InTest | Open | `PRODUCT.md` "P4. The witness RPC gate is inconsistent, and the family disagrees about it" |
| A1 | Invalidate the note index only on membership change | Waits: A4a | InTest | Open | `WITNESS.md` "The note index" |
| A4a | Rescan of the post-1.6M band only: `z_importkey` of one existing fat-wallet key, `rescan=yes`, `startHeight` 50,000 below the tip, profiled. Exits A1, unblocks A7b | Waits: fat wallet, idle hours | ToDo | Open | section 14 |
| A7b | NOTEIDX always on; drop `-walletwitnessnote` | Waits: A4a | ToDo | Open | `WITNESS.md` "Ship state" |
| A4b | Full genesis fat-wallet `-rescan`, overnight, outside the harness; refreshes M-WAL-RESCAN-FAT, gates nothing | Waits: fat wallet, overnight | ToDo | Open | `WITNESS.md` "Cost" |
| A3 | Benchmark both witness bottlenecks post-Sapling, on a disposable tip above height 492,850 with fat-wallet notes in range | Waits: A1, tip, fat wallet | ToDo | Open | `WITNESS.md` "Cost" |
| A9 | `getalldata` datatype matrix at a quiet full tip (BENCH-GAD-IDX1) | Waits: `fulltip-812-datadir` | ToDo | Open | section 14 |
| A12 | Lab soak under rebuild: status polling, spend storm under -31, `getalldata` after rebuild | Waits: `fulltip-812-datadir`, fat wallet | ToDo | Open | section 14 |
| A10 | p1 rescan profile; first confirm by timing that p1 runs long enough to profile | Waits: p1 wallet | ToDo | Open | `WITNESS.md` "Cost" |
| P6 | Anchor depth for shielded spends; subsumes what remains of P4 | Waits: P5 | ToDo | Open | `PRODUCT.md` "P6. Anchor depth for shielded spends" |

---

## 5. B -- Locking and concurrency

Analysis: `LOCKS.md` (findings, designs), `CONCURRENCY.md` (pools, queues).

| Id | Item | When | Kanban | Disp | Detail |
|----|------|------|--------|------|--------|
| B8 | Lock contention per site: count, total and maximum wait, at shutdown and on request, perf builds only | Next | ToDo | Open | `LOCKS.md` "Designs for the open work" 1 |
| B1 | Locking validation: order, balance, races, contention, throughput; try-lock edges in the order map; a concurrent coverage run | Ready | ToDo | Open | `LOCKS.md` "Designs for the open work" 4, 5 |
| B4 | `z_sendmany` does not lock the notes it selects; `z_mergetoaddress` selection can overlap it | Ready | ToDo | Open -- decision: section 3 #1 | `LOCKS.md` "Shielded note selection and the single async worker" |
| P20 | Cap `MAX_SCRIPTCHECK_THREADS`; `-rpcthreads` 4 -> 2; A/B M-PAR-AB-700K | Ready | ToDo | Open -- decision: section 3 #4 | `CONCURRENCY.md` "`-par` sizing: is the default right?" |
| B6 | Async worker experiments: one then several workers, idle and loaded | Waits: B4 | ToDo | Open | `CONCURRENCY.md` "Read-only RPC under concurrency" |

---

## 6. C -- Logging, RPC server, operations

| Id | Item | When | Kanban | Disp | Detail |
|----|------|------|--------|------|--------|
| C7 | Non-zero exit status after an `AbortNode` shutdown, so supervisors see a fatal stop. Implemented (`StartFatalShutdown`); verified on the binary, exit 1 with it and 0 without (`test-logs/crash-items-20261006/`) | Baseline | InTest | Open | section 14, C9 |
| C8 | Under `-daemon`, stderr appended to `stderr.log` in the network datadir, so assert and abort text survives. Implemented; verified on the binary (`test-logs/crash-items-20261006/`) | Baseline | InTest | Open | section 14, C9 |
| C9 | Node termination and crash diagnostics, tracking: A14a, A14b, A15, A5, the runbook | Ready | InProgress | Open | section 14, C9 |
| C6 | Record in `CONCURRENCY.md` the `-rpcthreads` / `-rpcworkqueue` distinction and its effect; put the reason in the 503 body | Ready | ToDo | Open | section 14; `LOCKS.md` "Designs for the open work" 7 |
| C1 | Catalogue log outcomes; propose a disposition per class; inventory from `log_inventory.py --summary`. No owning document yet; C1's output creates one | Ready | ToDo | Open | -- |
| C5 | Gated RPC entry points: one shared guard keyed by RPC name | Ready | ToDo | Open -- decision: section 3 #2 | `PRODUCT.md` "Option B -- one shared gate, keyed by RPC name (recommended)" |
| C2 | Review level and category assignment | Waits: C1 | ToDo | Open | section 14 |
| C4 | Alerting: what an operator must see, and how | Waits: C2 | ToDo | Open | -- |
| P18 | `debug.log` is unbounded: trimmed only at startup, and never with `-debug` | Postponed | ToDo | Postponed | section 14, N29 |

---

## 7. K -- Block validation and import

Analysis: `SYNC.md`.

| Id | Item | When | Kanban | Disp | Detail |
|----|------|------|--------|------|--------|
| P13 | Redundant Equihash verification: skip in `37f3f3459`; per-caller `ZERO_PERF` counters (M-EQ-VERIFY-SITES); six `miner_tests` cases, each failing under its mutation; `getblock` concurrent with reindex not covered | Baseline | InTest | Open | `SYNC.md` "Equihash verifications per block" |
| K8 | Remeasure throughput on the current build: stock reindex h600k-900k, n=4, the before/after for M-RX-POSTSAP-STOCK | Baseline | ToDo | Open | `SYNC.md` "Where the time goes" |
| K11 | CPU profiles regenerated on the current build, across the board; tracking | Baseline | ToDo | Open | section 14, K11 |
| P1 | Proof-verification counters and phase timers that cover proof work | Baseline | InTest | Open -- decision: section 3 #3 | `PerfTimers.md`; `SYNC.md` "Where the time goes" |
| P24 | `getchaintips` is O(chain length) | Ready | ToDo | Open | section 14 |
| K1 | `nNotarizations` can only be 0: implement the heuristic or remove the field | Ready | ToDo | Open | `SYNC.md` "Memory" |
| K2 | Size the ~176 B/block shielded-index layout cost; gate it out of `CBlockIndex` if worthwhile | Ready | ToDo | Open | `SYNC.md` "Memory" |
| K10 | Port `getaddrmaninfo` / `getrawaddrman` from Bitcoin Core before writing a bespoke `peers.dat` parser | Ready | ToDo | Open | `Stores.md` "Peers.dat Decoding And Recovery" |
| K4 | P2P follow-tip from the archive template (DNS seeds, distinct rpcport); full bootstrap ingest later | Ready | ToDo | Open | -- |
| K3 | Thermal state over long runs; the `therm` column in `util.tsv` stays | Postponed | ToDo | Postponed | -- |
| K5 | Era-bounded rematch using shielded density bands (L3) | Postponed | ToDo | Postponed | `Measures.md` M-DENS-* rows |
| P8 | FDCACHE disposition; cold-cache and Linux/Windows measurement | Postponed | ToDo | Postponed | `SYNC.md` "Disk I/O and FDCACHE" |
| K6 | Stack-logged allocation window entirely post-Sapling | Aside | ToDo | Aside -- unlikely to change the conclusion | `SYNC.md` "Memory" |
| K7 | Post-Sapling bootstrap capture | Aside | ToDo | Aside -- bootstrap and reindex agree within ~3 points per bucket | `SYNC.md` "Where the time goes" |

---

## 8. N -- Harness, records, lab inputs, evidence store

Analysis: `HOWTO.md`, `SCHEMA.md`, `recbench/RecBench.md`; lab conf and
recording in `README.md` "Lab conf and recorded rows".

| Id | Item | When | Kanban | Disp | Detail |
|----|------|------|--------|------|--------|
| N15 | Lab inputs located and identified; the layout question needs the height-ordered tiny archive rebuilt with `contrib/linearize` outside `/tmp` | Baseline | InProgress | Open | section 14 |
| N1 | Microbenchmark baseline: the rest of the `zcbenchmark` suite; several need a populated wallet | Baseline | InTest | Open | section 14 |
| N28 | Loose files at the top of `test-logs/` | Ready | ToDo | Open | section 14 |
| N27 | `test-logs/` cleanup, validation and reconciliation | Ready | ToDo | Open | section 14 |
| N29 | `debug.log` handling and size, node and lab | Ready | ToDo | Open | section 14 |
| N12 | Extend `check_citations.py` rules 1-2 from `docs/` to every owned document | Ready | ToDo | Open | `POLICY.md` "Enforcement" |
| N2 | Workload classes: `op` enum validated by RecBench and back-annotated with `era`; then `wallet_shape`, derived `era`, a pooling guard on `op` and `era` | Ready | ToDo | Open | `SCHEMA.md` "4.3 Workload classes" |
| N4 | Row identity: a hash of the `zerod` binary in `build` and `build_id`; fingerprint v2 with platform | Ready | ToDo | Open; the cross-platform guard waits for a second platform | `SCHEMA.md` "2. Version block -- `build`", "6.4 Fingerprint v2" |
| N7 | State the restartability axis beside the run-length heuristic | Ready | ToDo | Open | `POLICY.md` "Lab discipline" |
| F11 | Document the `parse()` input contract in `bucket_profile2.py` | Ready | ToDo | Open | -- |
| N9 | Per-workload utilization profile from the ledger, over checkpoint progress series | Waits: N2 | ToDo | Open | section 14 |

---

## 9. D -- Documentation

Rules: `POLICY.md` "Documents"; writing rules are Zero's DOC-CONVENTIONS.

| Id | Item | When | Kanban | Disp | Detail |
|----|------|------|--------|------|--------|
| D6 | Rules in one place per scope: `POLICY.md` keeps the perf-specific rules; general rules defer to Zero's DOC-CONVENTIONS | Baseline | InTest | Open | section 14 |
| D15 | `M-*` values stated once: in `Measures.md` | Ready | ToDo | Open | section 14 |
| D10 | One manifest per kind of list, read by every script and document that needs it | Ready | ToDo | Open | section 14 |
| D8 | Writing-rules pass per file; done for `PLAN.md` and `POLICY.md` | Ready | InProgress | Open | section 14 |
| D1 | Merge to the target shape, one absorbed file per commit, each net-negative; `TOOLING_FAILURES.md` left as it is | Ready | InProgress | Open | `README.md` documentation map, "Merges into" |
| D3 | Section-number citations to heading titles; `check_citations.py` fails on section numbers, bare file names, a missing cited heading, an `M-*` id with no row, a path or flag the tree lacks | Waits: D1 | ToDo | Open | -- |

---

## 10. G and H -- Tests, build, process

| Id | Item | When | Kanban | Disp | Detail |
|----|------|------|--------|------|--------|
| H2 | A card finishes only with its result recorded; `validate.sh` check | Ready | ToDo | Open | section 14 |
| G1 | Suite plan: maturity constant, `initialize_chain_clean` ratio, 23 failures by mode | Ready | ToDo | Open | `TESTING.md` "Suite plan: constants, tiers, failure modes" |
| G2 | A bare GTest run aborts and prints no summary | Ready | ToDo | Open | `TESTING.md` "`CachedWitnessesCleanIndex` is held failing on purpose" |
| G3 | An autotools re-run inherits no `CONFIG_SITE`; touches Zero-owned `configure.ac` | Ready | ToDo | Open | `BUILD_RECONFIG.md` "Hardening options, not implemented" |
| H3 | Item ids, names and status reconciled with Zero's `TODO.md` | Postponed | ToDo | Postponed | section 14 |
| H4 | Regroup items by module | Postponed | ToDo | Postponed | superseded by this layout; ids remain with H3 |

---

## 11. Z -- Hand-off to Zero

Not performance work. Each proposal is a draft in `reporoot/`, compared
against a stated Zero commit and kept to what is still pending.

| Id | Item | When | Kanban | Disp | Detail |
|----|------|------|--------|------|--------|
| Z6 | `reporoot/MAINTREE_CHANGES.md`: `src/` and `qa/` changes for Zero, with release notes for behaviour changes | Baseline | InProgress | Open | section 14 |
| Z7 | Root documents here are older than Zero's; refresh them from Zero by merge, not by edit | Baseline | ToDo | Open | -- |
| P19 | Delete unbuilt `src/snark/`: done here (`f34332af9`); Zero still carries it | Baseline | InTest | Open | section 14 |
| Q3 | Revalidate the committed sort fold against the 5-solution baseline (V2); gates the solver row of hand-off batch 3 | Ready | ToDo | Open | section 14 |
| Q8 | Release note for the tromp default | Waits: batch 3 | ToDo | Open | -- |
| Z5 | `reporoot/DOC-CONVENTIONS.md`: replacement for the DOC-CONVENTIONS entry, approved | Waits: Zero | ToDo | Open | -- |
| Z8 | `reporoot/TODO.proposals.md`: REL-05 (`contrib/spendfrom/`, `contrib/qos/`), DOC-ROOT-PLANNING, three items out of `TODO.md` | Waits: Zero | ToDo | Open | -- |
| Z2 | Zeronode test track, now Zero ZN-01 and DOC-02: argument validation on existing Boost; founders window; two-node `startalias`; zeronode `invalidateblock` after A5 | Waits: Zero; A5 | ToDo | Open | -- |
| Z10 | `reporoot/MIGRATION_PLAN.md`: `insight` to the organisation when convenient | Postponed | ToDo | Postponed | -- |

---

## 12. Parked groups

Not scheduled; each reopens by decision. Analysis stays in the cited
document.

| Id | Item | When | Detail |
|----|------|------|--------|
| Y1 | Groth16 batch verification: Option A (hand-port) or B (adopt `sapling-crypto`) | Postponed | `PerfGroth.md` "4. The decision: Option A vs Option B" |
| Y2 | Build librustzcash on rustc 1.98.1 | Postponed | `LIBRUSTZCASH.md` "4. Remaining validation, and what it costs" |
| Y3 | Vendor librustzcash in-tree; then decide the base | Postponed | `LIBRUSTZCASH.md` "3. Recommendation" |
| R3 | `CBLAKE2bWriter` on uniblake | Postponed | `HASHLIBS.md` "C. `CBLAKE2bWriter` and the four one-shot sites" |
| Q2 | Measure the threaded tromp solver | Postponed | `equ/PLAN.md` "Queued solver work" |
| Q4 | Per-phase CPU profile of a mainnet (192,7) solve (G5) | Postponed | `README.md` "mine_bench.sh" |
| Q5 | Deployment fleet mix (INV-ARM-MIX) | Postponed | -- |
| Q6 | Solver stages S1-S4 | Postponed | `equ/PLAN.md` "9. Sequencing and honest expectations" |
| Q9 | Stamp variant and UTC into solver dump paths; `eqbench.sh` wrapper; solver variant registry | Postponed | `equ/PLAN.md` "Queued solver work" |
| Q10 | Review `equ/` under the writing rules; move its queue into this register; delete `equ/README.md` | Postponed | section 14 |
| F1 | Linux VPS and Windows/WSL runbook, folding in the platform tool survey | Postponed | `PerfPlatforms.md` "6. Recommendations, ranked" |
| F2 | First non-macOS capture | Postponed | `PerfPlatforms.md` "3.1 CPU profiling -- the direct xctrace equivalent" |
| F4 | Re-validate the consolidated tree on another platform | Postponed | -- |
| F5 | CI: the perf branches in the push trigger; a lint job ahead of the build. Blocked on a Zero proposal, not on settings | Postponed | `TESTING.md` "CI and its components"; section 14 |
| F6 | Port `res_sample.sh` to `psutil` | Postponed | `PerfPlatforms.md` "3.3 Resource sampling" |
| F8 | Retest the `--strict` / `--suite` release track on Linux | Postponed | -- |
| F9 | Windows MXE cross-build, never run here; then hardening and ETW profiling | Postponed | `PerfPlatforms.md` "4. Windows 11" |
| F10 | Release engineering: params archival, branch-id CI, OpenSSL 3, Debian packaging | Postponed | -- |

---

## 13. Decided

One line per direction taken or dropped: status, how it is enabled, what it
binds later. Reasoning lives in the cited document.

| Direction | Status | Enabled | Lasting implication | Reasoning |
|-----------|--------|---------|---------------------|-----------|
| Equihash hashing via uniblake | Adopted | default build | Builds need the uniblake sibling; where it lives is Zero's decision | `HASHLIBS.md` |
| tromp solver as mining default; sort comparator fold; `Xc.reserve()` | Adopted | default, `-equihashsolver` | Falls back to the reference solver off (192,7), pinned by `miner_tests/equihashsolver_default_and_param_guard`; release note Q8 | M-EQ-TROMP-SPEEDUP; `equ/` |
| Skip Equihash re-check at `BLOCK_VALID_TREE` (P13) | Adopted | default | Header trust rests on the index entry and on the `ReadBlockFromDisk` re-check; six tests pin both | `SYNC.md` "Equihash verifications per block" |
| `IsInitialBlockDownload` hoist; single `CompareTo`; merkle-root latch | Adopted | default | -- | `LOCKS.md`; `SYNC.md` "Shipped changes" |
| `-walletwitness=ibd-defer`, `-walletwitnessnote=1` | Adopted, opt-in; default-on not pursued | flags, default off | When on, spends wait for one rebuild after import (`-31`/`-33`) | `WITNESS.md` "Choices" |
| DIRTY | Rejected | not built | -- | `WITNESS.md` "Choices" |
| Reorg bound: 99 blocks, then shutdown (TNT-02, A11) | Settled by Zero | default | A deeper reorg stops the node with a message; the witness cache is one block deeper, pinned by a `static_assert` (A8, TNT-03); TENT's unbounded follow is not ported | Zero `UpdateZero.md` DEF-07; `WITNESS.md` "Reorg and crash" |
| `txindex` always on | Inherited, kept | default; `-txindex` commented out (`fTxIndex = true` in `main.cpp`), in this tree and in Zero | Lookups by txid always work; the index costs disk and write time on every block; turning it off needs code | `Stores.md`; D11 |
| FDCACHE | Compiled out | `ZERO_FDCACHE` build only | Reopens with cold-cache or Linux data (P8) | `SYNC.md` "Disk I/O and FDCACHE" |
| Equihash first-list batch hashing (`EQUIHASH_BATCH_HASH`) | Not selected: lower performance | compile-time macro; code kept | Not proposed to Zero | commit `611e9efb7` |
| Minimal lab conf: no Insight, default `dbcache` | Adopted | harness default; `ZERO_PERF_ARCHIVE_CONF=1` restores an archive's | Compare only rows with equal `features.runtime` | M-RX-TINY-20260930 |
| `reporoot/` stays tracked as it is | Adopted | -- | -- | -- |

Settled, do not re-derive: recursion is six inherited lock-per-function
sites (M-LOCK-ATTR, `LOCKS.md` "What recursion actually exists"); earlier
totals were acquisition counts.

---

## 14. Item detail

Only what no subject document owns, by id.

**A4a.** Exits A1 and gives A7b its evidence. Both ask whether
`SelectWalletTxsForWitnessScan` still dominates in the post-1.6M band, where
each founders coinbase entering the wallet used to rebuild the note index; a
band of 50,000 blocks there answers it. `z_importkey` with an existing key,
`rescan=yes` and a `startHeight` runs `ScanForWalletTransactions` from that
height on a lab node at tip with the fat wallet; the key stays out of every
document. A4b's genesis run only refreshes M-WAL-RESCAN-FAT. NOTEIDX
correctness is covered by the gate tests in `WITNESS.md` "Ship state".

**A9, A12.** Both use `reindex-profile/fulltip-812-datadir`, recreated from
`chainblocks812-clean.tgz` by `prep_lab_datadir.sh`; the tiny-snap result
does not transfer to a full tip. A12 expects `getblockcount` to stall for the
walk's duration on `cs_main` and then succeed; every spend under -31 must
fail cleanly; `getalldata` latency, RSS and response size after rebuild for
datatypes 0 and 1.

**C2.** After gating the two largest sources a tiny reindex still logs about
one line per block (M-LOG-TINY). Bucket them by message prefix; for each
bucket above ~1%, check `LogPrintf` (unconditional) versus `LogPrint`
(categorised) and propose a category for anything that is neither an error
nor a state transition. `UpdateTip` stays: every measurement reads it.

**C6.** `-rpcthreads` is how many requests are served at once,
`-rpcworkqueue` how many may wait. At equal load, depth 4 rejected requests
and depth 16 did not. A rejection reaches the client as HTTP 503 and exit 1,
without the reason ("Work queue depth exceeded"), and the server logs one
line per episode (`test-logs/c3-workqueue-20260930T082448Z/`).

**F5.** What CI runs and what it leaves out: `TESTING.md` "CI and its
components". What F5 solves: perf-branch pushes get the same Linux build and
strict tests that `master` gets, and a lint job runs the perf checks
(`lint-perf.sh`, `validate.sh`) before the 240-minute build. The workflow
already runs on `master`, so Actions is enabled; no setting has to change for
F5. The blocker is ownership: `.github/workflows/tests.yml` is a root file,
so the change is a Zero proposal (`reporoot/`). Settings matter only for an
optional rule on `master` that makes the job a required check, which an
administrator of the Zero repository sets. Steps when reopened: draft the
workflow change (`perf_*` in `on.push.branches`; a `lint` job, conditional on
`contrib/perf/` existing; `linux` `needs: lint`); check it locally
(`actionlint`, `act`); propose it in `reporoot/`; after Zero applies it,
push a `perf_*` branch and confirm both jobs run.

**K11.** Regenerating CPU profiles on the current build, idle host only,
one profile per invocation. Each result goes through `profile_collate.py`
and gets an `M-*` row that names the row it supersedes.

| Profile | Supersedes | Procedure | Needs |
|---------|------------|-----------|-------|
| Reindex, six captures across the chain | M-CPU-SEQ | `capture_sequence.sh` on an rsync of the live `blocks/` (`README.md` "capture_sequence.sh"), then `decode_captures.py` | hours; read-only live `blocks/` |
| Post-Sapling window | M-CPU-CORR | `HOWTO.md` "1.2 Profile post-Sapling without the 8.5G archive" | `postsapling_reindex.sh` window from 600,000 |
| Tiny reindex window | M-CPU-TINY-ORIG | `HOWTO.md` "1.1 Profile a reindex (the default case)" | the tiny archive |
| Wallet-on tiny reindex | M-CPU-WAL0-TINY | `HOWTO.md` "1.1" with `wallet_sync_profile.sh` and `profile_run.sh ... "Main Thread"` | a small wallet |
| Fat wallet sync | M-CPU-WAL-FAT | `HOWTO.md` "1.3 Profile a wallet rescan" | the golden fat wallet |
| Bootstrap import | -- | `HOWTO.md` "1.4 Profile bootstrap import" | a `bootstrap.dat` copy |

M-CPU-LATCH and the FDCACHE profiles (M-CPU-FD, M-CPU-FD-THR, M-CPU-FS)
answered closed questions and are not regenerated; M-CPU-LEGACY is
superseded.

**N15.** Sibling repositories, in test: `ops-validate.sh` finds `linearize/`
beside this tree or the product tree (`LINEARIZE_DIR` overrides) and warns
when the original `bootstrap.dat` is missing; a RecBench project root may
name the build's override variable, and a missing root is an error
(`recbench/RecBench.md` "Roots, and running standalone"). Snapshot archives
are in `zero.save`, beside the default datadir; tiny and short verify
against their recorded sha256, and rows carry the archive's hash. Whether
block-file layout changes reindex speed is open: run-to-run range is 2-2.5%
within a sequence and 4.4% across six runs (M-RX-TINY-SEQ), so the ~5% gap
in M-RX-TINY-ARCHIVE needs both archives interleaved, n>=6 each.

**N1.** Recorded: `verifysaplingspend` / `verifysaplingoutput` and their
`create` counterparts (M-ZCB-SAP-VERIFY, M-ZCB-SAP-CREATE).
`parameterloading` fails with RPC error -3. Several of the rest need a
populated wallet.

**N9.** Columns by class (`SCHEMA.md` "4.3 Workload classes"): A/B -- blk/s,
CPU% of one core, threads, bucket shares, height window; C -- adds witness
share, `mapWallet` size, wallet MB, tx count; D -- s/solve, Sol/s, peak
physical MB. Era and architecture are column splits, never pooled. Unmeasured
cells stay empty and named. Network sync rows (`op: sync`) carry peer count,
tip distance at start, per-region rate, stall events and min/max, n >= 3.
The fat rescan and `many-utxo-few-tx` cannot be filled on demand. Progress
series: a `checkpoint_row()` in `perflib.sh` appends to `progress.tsv`,
`res_sample.sh` gains that output mode, `recbench.py --import-tsv` collates
post-run; one blk/s figure hides the spread across height bands
(M-LAB-BAND-TINY).

**N27.** Rules: `POLICY.md` "Cleaning up". Tool: `retention.py` classifies
and never deletes; its self-test runs in `lint-perf.sh`. Missing: a check,
run from `validate.sh`, that every run `Measures.md` and `PLAN.md` name
exists (M-LAB-REPRO cites a driver log that does not exist); rules for what
a run directory must contain (driver log, measures, recorded rows) before it
counts as complete.

**N28.** `retention.py` classifies directories only, so top-level files
(`validate-*.log`, tiny-baseline `-driver.log` / `.jsonl` / `-progress.tsv`
/ `-util.tsv`, `measures_*`) are never classified. Launchers write each run
into its own directory; existing loose files are grouped by run prefix.

**N29.** One item for every `debug.log` question.

- Node (P18): `ShrinkDebugFile` (`util.cpp`) runs only at startup
  (`init.cpp`) and, above 10 MB, keeps the last 200 KB, losing the startup
  record; `GetBoolArg("-shrinkdebugfile", !fDebug)` disables it whenever a
  `-debug` category is on. Zcash and Ycash comment the call out; Pirate and
  Hush3 gate it as Zero does. On a live node without `-debug` the file is
  dominated by the initial import, one `UpdateTip` per block (M-LOG-LIVE).
  Fix when reopened: rotation on a periodic size check, which covers the
  `-debug` case too; `debuglog.py --rotated` already reads the rotated names
  (`test-logs/p18-shrink-20260922/`).
- Volume: C2, about one line per block after gating.
- Lab: each `postsapling_reindex.sh` trial keeps its whole `debug.log` after
  its rows are recorded; these files are most of `test-logs/` by size.
  Trim per-trial `debug.log` to the lines extraction reads once the run's
  rows are in the ledger, and have `retention.py` report the bytes.

**P1** gates any phase summary: proof verification sits in no timer, so a
summary built today omits most post-Sapling cost while appearing complete.

**P19.** In no makefile, no objects, no includes; entered as a subtree in
`f4d8cd127`. Zcash removed libsnark in `9ce0caf20` (v2.1.0); Pirate, Hush3
and Firo have too. Zero and Zclassic still carry it; Zero does not compile
it.

**P24** (`test-logs/rpc-test-20260917/`). Measure insert and erase
separately before choosing a fix. The ordered set is maintained continuously
by its comparator and only 214 survivors need ordering; not materialising
the full set may remove the cost.

**Q3.** The fold's speedup was taken on a working-tree patch; no recorded
run confirms the committed code still produces the five baseline solutions
(`test-logs/eqvectors/solver_baseline_192_7.txt`, archived and `0444`). One
run is the exit condition.

**Z6.** The batches and what is held back: `reporoot/MAINTREE_CHANGES.md`
"Hand-off batches". Their review is postponed; Baseline 1 steps 3-4 wait
for it.

**C9.** Tracking for node termination. Runbook: `Stores.md` "Node Stops And
Recovery"; inventory and evidence: `test-logs/crash-exit-survey-20261005.md`,
`test-logs/crash-items-20261006/`.

- *Done.* C7 fatal stop exits 1; C8 stderr kept under `-daemon`;
  `ReportFatalError` (`util.cpp`) writes a fatal reason to `debug.log` and
  stderr and flushes both, used by the wallet `exit(1)` guards, the chainstate
  read-error abort and `AbortNode`; `AbortNode` reports the first fatal error
  once and later ones as "Fatal error while stopping"; a message that already
  starts with its caption is no longer shown as "Error: Error:" (`noui.cpp`);
  an unknown `-equihashsolver` is refused at startup instead of stopping the
  miner thread on an assert (`SelectEquihashSolver`, `miner.cpp`).
- *A14a, A15, detection and reporting first.* Log lines or an RPC field, no
  change to what the node does; together they tell an operator whether a
  restart is redoing work and why.
- *A14b, operation and recovery.* `ScanForWalletTransactions` returns a
  count only; its callers then record the tip as scanned, and the final
  witness build runs only at the end, so an early return alone would mark
  unscanned blocks as scanned. Steps and corner cases: `LOCKS.md` "Designs
  for the open work" 2.
- *A5, postponed.* The three guards were added by Zero in `372b2dd39`; no
  current caller can pass null. Reopen when a caller can, or a report shows
  the line.
- *Not proposed.* A SIGABRT handler writing `debug.log`: not
  async-signal-safe. Assert text reaches stderr, and `stderr.log` under
  `-daemon`.

**D6.** The same writing rules are kept in four places: `POLICY.md`
"Documents", Zero's `UpdateZero.md` DOC-CONVENTIONS, Zero's `AGENTS.md`
"Documentation" (copied into this tree), and the `docstruct` skill.
`POLICY.md` keeps what only this tree has: `M-*` citation, run naming,
ratchets, lab discipline, retention. The general rules go to Zero's
DOC-CONVENTIONS (Z5) and are cited from here once adopted.

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
restated value with the row. Overlaps to fold: `Measures.md` "Ledger
campaigns" (one `campaign` column in the catalogue instead); "By application
/ use case" (drop: the subject documents own routing); "Launch and tools
matrix" (D10); `test-logs/DATA_INDEX.md` (frozen, not cited); lines that
restate a value beside its id in `SYNC.md`, `WITNESS.md`, `CONCURRENCY.md`,
`README.md` "Lab wallets".

**H2.** A fix once reached the tree with a correct in-code comment and no
record anywhere; the check makes that fail.

**H3.** Zero labels items by area and name (`WAL-GETALLDATA-W5`, `TST-01`;
prefixes CON, WAL, OPS, REL, EXT, TST, DOC, TNT) and states status by list.
When reopened: area prefix plus number (`WIT-01`), Zero's prefix for items
handed to Zero, old ids mapped once until the next release; one status value
mapped to Zero's lists.

**Q10.** `equ/README.md` goes rather than folding into `equ/METHOD.md`:
figures and "What this analysis established" to `equ/FINDINGS.md`, "Next
actions" to this register, the file table to the documentation map.
`equ/PLAN.md` queue ids D1-D5 collide with group D here.

---

## 15. Closed ids

Finished: G4 solver test now calls `SelectEquihashSolver`, the function the miner uses (a mutation removing the (192,7) fallback fails it), N17 perf build gate (`--enable-perf`: builds; Boost passes; GTest 221/221 with the suite filter, as release; `test-logs/n17-perf-gate-20261006/`; a recurring gate is F5), N21 one launcher path (wallet trial through `ops-campaign.sh` with its row file, witness trial with its row, both on a real wallet; the catalog's witness trials need a snapshot with chainstate, which the tiny archive lacks; `test-logs/n21-exit-20261006/`), A2 note-index specification confirmed, D2 module ownership confirmed, D11 `txindex` stated as always on in `Stores.md`, P10 explicit `GetFilteredNotes` arguments (hand-off via Z6), A8 witness cache pinned above the
reorg bound, B2 `IsInitialBlockDownload` hoist, B3 recursive sites, B5 P25
claim retracted, C3, D12, E2 non-blake2b libsodium surface, H1 presentation
edits checked by `validate.sh`, K9 into K8, N10, N11, N13, N14, N18, P17
out-of-order children (no change needed), P23 comparator single `CompareTo`,
P26 stray `concept` on `README.md` line 1, Z1, Z4.

Settled by Zero: A11 (DEF-07, section 13).

Merged: A7 into A7a and A7b; A4 into A4a and A4b; B7 into B1; D4 into D2;
D5 into F1; D7 into D10; D9 into Q10; D13 and D14 into D8; N3 into N2; N19
into N4; N8 into N9; N5, N6, N16, N20, N22, N23 into N21; N24, N25 into N15;
Z9 into Z8.

Rejected: DIRTY (section 13).
