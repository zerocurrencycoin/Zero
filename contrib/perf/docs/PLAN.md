# Plan

The single register of perf work, laid out by schedule: what to do now, what
is ready to start, what waits on which input, what is decided, and what is
postponed. Analysis lives in the subject document each row points to; this
file carries one-line state, ordering, and the detail an item needs that no
subject document owns.

Status carries two ratings (`POLICY.md` "Status"):

| Axis | Values | Means |
|------|--------|-------|
| **Kanban** | ToDo, InProgress, InTest, Finished | where the card is |
| **Disposition** | Open, Blocked, Fixed, Postponed, Aside | what happened to the issue |

A card is not Finished until its result is recorded where the subject lives.
`P` ids are node code owned by Zero; every other id is lab, harness or
documentation work in this tree. Items keep their id when they move. A
pending decision is carried by the item it governs: its Disp reads
`decision:` and states the options.

---

## 1. Start here

State: release build; Boost (incl. the six P13 tests), `lint-perf.sh`,
`perflib_selftest.sh` and `validate.sh` green. N21 and the P13 tests are in
the working tree, uncommitted; the commit sequence is written out in
`test-logs/commit-steps-20261005.md`.

Session rules: start at the worktree root, the `ZeroPerf` checkout, and
never `cd` into a subdirectory; work in Zero's tree from a separate session
opened in the `Zero401` checkout. Benchmarks only on an idle host: no build,
test run or other `zerod`. Keep lab inputs out of `/tmp`, whose lab
directories this host moves into `/tmp/zero_old` at midnight.

Restart prompt:

```
cd /Users/walter/Work/ZK/ZeroPerf && claude
ZeroPerf, branch perf_b1b2, worktree root as working directory. Read
contrib/perf/docs/PLAN.md section 1 and 2, then contrib/perf/docs/POLICY.md;
start at the first unfinished step of section 2. Do not cd into
subdirectories. Run contrib/perf/lint-perf.sh and validate.sh before and
after a change. Root and Zero-owned files are read-only; proposals go to
contrib/perf/reporoot/. Writing rules: reporoot/DOC-CONVENTIONS.md.
```

Harness rules: rebuild clean after `./configure` -- it regenerates makefiles
without invalidating objects, so an incremental build carries new flags only
in recompiled units; check with `nm src/zerod` and the binary timestamp.
Never compare debug and release timings. Run the test suites sequentially.
`validate.sh` fails `buildconfig` while a debug binary is in the tree.

---

## 2. Now, in order

1. **Commit** the working tree as five topic commits
   (`test-logs/commit-steps-20261005.md`), fast-forward `perf-402`, push.
2. **Close what only needs confirming** -- read, run where stated, then
   Finished:

   | Id | Item | Kanban | Exit |
   |----|------|--------|------|
   | A2 | Review the note-index specification for redundancy | InTest | Done by the `WITNESS.md` rewrite; confirm on review |
   | P10 | Explicit parameters at defaulted call sites: the five `GetFilteredNotes` callers, values unchanged | InTest | Full gate green; then hand-off batch 1 (`PRODUCT.md` "P10") |
   | D2 | Reorganisation: `SYNC.md` and `WITNESS.md` own their modules; this file is the one register | InTest | Confirm on review |
   | D11 | Reconcile `Stores.md` with this tree; verify the `txindex` default in Zero before stating it for all branches | InTest | Confirm the default in Zero |
   | N17 | `--enable-perf` configuration in a gate: it builds, and Boost and GTest pass with `ZERO_PERF` defined | InTest | One perf build and both suites, recorded |
   | N21 | One `perflib.sh` path for every launcher: lab conf, declared runtime, recording, helpers (`README.md` "Lab conf and recorded rows") | InTest | One wallet and one witness trial on a real wallet record through `record_trial`, and an `ops-campaign.sh` cycle reads their row files |
3. **Hand-off to Zero (Z6),** in a session opened in the `Zero401` checkout,
   branch from `from-perf-401`, one commit per subject, Zero's gates green
   after each. Source and per-change review notes:
   `reporoot/MAINTREE_CHANGES.md`.
   - Batch 1, correctness, nothing users notice: missing locks in
     `getspentinfo` / `getblockdeltas` (upstream `14ec1016b`); `src/snark/`
     deletion (P19); explicit `GetFilteredNotes` arguments (P10); `qa/` test
     fixes.
   - Batch 2, speed, default on: P13 skip with its six tests;
     `IsInitialBlockDownload` hoist; single `CompareTo` comparator;
     merkle-root latch; note-index invalidation (A1) with its GTest, once A1
     exits (section 4).
   - Batch 3, defaults users see, each with a release note: tromp solver
     default (Q8), after Q3's validation run; uniblake for Equihash hashing,
     after Zero decides where uniblake lives (`reporoot/MIGRATION_PLAN.md`).
   - Not handed off: the opt-in witness flags (section 5); perf-only code
     (`ZERO_PERF`, `ZERO_FDCACHE`, lock attribution); the `ops-validate.sh`
     runtime field until Zero carries `contrib/perf/debuglog.py`;
     `EQUIHASH_BATCH_HASH` (section 5).

---

## 3. Ready to start

No external input needed. Ordered by importance within each block.

**Correctness**

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| A5 | Replace the null-`pindex` `exit(1)` paths with rebuild-or-clear recovery | ToDo | Open | `WITNESS.md` "Reorg and crash" |
| A6 | Height walk drops `cs_main` periodically and aborts on tip change; then the R5c e2e. The walk runs at the tip with stock flags too, so this affects defaults | ToDo | Open | `WITNESS.md` "Reorg and crash" |
| A8 | Reorg bound versus witness cache (TNT-03). The bound is settled by Zero (DEF-07, section 5) and `WITNESS_CACHE_SIZE` is defined as `MAX_REORG_LENGTH + 1`, so the cache already covers it; what remains is to pin that relation | ToDo | Open | section 7 |
| Q3 | Revalidate the committed sort fold against the 5-solution baseline (V2); gates the solver row of hand-off batch 3 | ToDo | Open | section 7 |
| P27 | `-salvagewallet` help and some test fixtures say `wallet.dat`; the runtime default is `wallet.zero` | ToDo | Open | `Stores.md` "Berkeley DB, Wallet Compatibility, And Local DB Direction" |
| P4 | Witness RPC gate inconsistent | InTest | Open | `PRODUCT.md` "P4. The witness RPC gate is inconsistent, and the family disagrees about it" |
| A13 | `CDB::Rewrite` spins with no log or timeout; upstream, all Zcash-family forks: report upstream | ToDo | Open | -- |
| P24 | `getchaintips` is O(chain length) | ToDo | Open | section 7 |

**Records and harness**

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| N28 | Loose files at the top of `test-logs/` | ToDo | Open | section 7 |
| N27 | `test-logs/` cleanup, validation and reconciliation | ToDo | Open | section 7 |
| N29 | `debug.log` handling and size, node and lab | ToDo | Open | section 7 |
| N12 | Extend `check_citations.py` rules 1-2 from `docs/` to every owned document | ToDo | Open | `POLICY.md` "Enforcement" |
| N2 | Workload classes: `op` enum validated by RecBench and back-annotated with `era` on existing v2 rows; then `wallet_shape`, derived `era`, and a pooling guard on `op` and `era` | ToDo | Open | `SCHEMA.md` "4.3 Workload classes" |
| N4 | Row identity: a hash of the `zerod` binary in `build` and `build_id`, since two dirty trees on one commit pool as one build; fingerprint v2 with platform | ToDo | Open; the cross-platform pooling guard waits for a second platform | `SCHEMA.md` "2. Version block -- `build`", "6.4 Fingerprint v2" |
| N7 | State the restartability axis beside the run-length heuristic | ToDo | Open | `POLICY.md` "Lab discipline" |
| B8 | Lock contention per site: count and total wait time, reported at shutdown and on request, perf builds only. Extends `DEBUG_LOCKCONTENTION`, which logs each contended acquisition by lock name only | ToDo | Open | `LOCKS.md` "Contention" |
| F11 | Document the `parse()` input contract in `bucket_profile2.py` | ToDo | Open | -- |
| H2 | A card finishes only with its result recorded; `validate.sh` check | ToDo | Open | section 7 |

**Documentation**

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| D15 | `M-*` values stated once: in `Measures.md` | ToDo | Open | section 7 |
| D10 | One manifest per kind of list, read by every script and document that needs it | ToDo | Open | section 7 |
| D8 | Writing-rules pass per file: narration, transient counts, deleted-file mentions, restated values. Done for `PLAN.md` and `POLICY.md` | InProgress | Open | section 7 |
| D1 | Merge to the target shape, one absorbed file per commit, each net-negative; `TOOLING_FAILURES.md` left as it is | InProgress | Open | `README.md` documentation map, "Merges into" |
| C6 | Record in `CONCURRENCY.md` the `-rpcthreads` / `-rpcworkqueue` distinction, its measured effect, and what a rejected client sees | ToDo | Open | section 7 |

**Product cleanups and analysis**

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| A7a | Witness flag surface, the parts that need no measurement: `-walletwitness=stock|defer|rebuild` (keep `ibd-defer` as an alias), witness stats under `-debug=witness` instead of `-walletwitnessstats`, one `WitnessReady { NotBuilt, Building, Ready }` replacing `initWitnessesBuilt` + `fBuildingWitnessCache`. RPC codes unchanged; existing gate tests cover it | ToDo | Open | `WITNESS.md` "Ship state" |
| P5 | `boost::optional` to `std::optional` | ToDo | Open | `PRODUCT.md` "P5. Migrate `boost::optional` to `std::optional`" |
| P7 | Coin-selection call clarity -- find existing coverage first | ToDo | Open | `PRODUCT.md` "P7. Coin-selection call clarity: adopt Ycash's shape, not TENT's" |
| K1 | `nNotarizations` can only be 0: implement the heuristic or remove the field | ToDo | Open | `SYNC.md` "Memory" |
| K2 | Size the ~176 B/block shielded-index layout cost; gate it out of `CBlockIndex` if worthwhile | ToDo | Open | `SYNC.md` "Memory" |
| C1 | Catalogue log outcomes; propose a disposition per class; inventory from `log_inventory.py --summary`. No owning document yet; C1's output creates one | ToDo | Open | -- |
| K10 | Port `getaddrmaninfo` / `getrawaddrman` from Bitcoin Core before writing a bespoke `peers.dat` parser | ToDo | Open | `Stores.md` "Peers.dat Decoding And Recovery" |
| K4 | P2P follow-tip from the archive template (DNS seeds, distinct rpcport); full bootstrap ingest later | ToDo | Open | -- |
| G1 | Suite plan: maturity constant, `initialize_chain_clean` ratio, 23 failures by mode | ToDo | Open | `TESTING.md` "Suite plan: constants, tiers, failure modes" |
| G2 | A bare GTest run aborts and prints no summary | ToDo | Open | `TESTING.md` "`CachedWitnessesCleanIndex` is held failing on purpose" |
| G3 | An autotools re-run inherits no `CONFIG_SITE`; touches Zero-owned `configure.ac` | ToDo | Open | `BUILD_RECONFIG.md` "Hardening options, not implemented" |
| B1 | Locking validation method: order, balance, races, contention, throughput. Known gaps: `TRY_LOCK` paths are uninstrumented, and all lock results come from a single-worker reindex | ToDo | Open | `CONCURRENCY.md` "Validating locking across the codebase"; `LOCKS.md` "Open" |

**Decisions owed** (each item states its options)

| Id | Item | Kanban | Disp | Detail |
|----|------|--------|------|--------|
| B4 | `z_sendmany` does not lock the notes it selects; `z_mergetoaddress` selection can overlap it | ToDo | Open -- decision: explicit locking, or a documented single-worker constraint | `LOCKS.md` "Shielded note selection and the single async worker" |
| C5 | Gated RPC entry points: one shared guard keyed by RPC name | ToDo | Open -- decision: one shared in-flight slot, or per-method slots | `PRODUCT.md` "Option B -- one shared gate, keyed by RPC name (recommended)" |
| P1 | Proof-verification counters and phase timers that cover proof work | InTest | Open -- decision: `nTimeVerify` relabelled cumulative, reported exclusive, or both | `PerfTimers.md`; `SYNC.md` "Where the time goes" |
| P20 | Cap `MAX_SCRIPTCHECK_THREADS`; `-rpcthreads` 4 -> 2; A/B M-PAR-AB-700K | ToDo | Open -- decision: keep 16, cap at 7, or cap at 4; an idle-host `-par=4` rerun settles the cost of 4 | `CONCURRENCY.md` "`-par` sizing: is the default right?" |

---

## 4. Waiting on an input

| Id | Item | Kanban | Waits on | Detail |
|----|------|--------|----------|--------|
| A4a | Bounded fat-wallet rescan of the post-1.6M band: `z_importkey` of one existing fat-wallet key with `rescan=yes` and a `startHeight` 50,000 below the tip, profiled. Exits A1 and unblocks A7b | ToDo | The golden fat wallet on the host; a few idle hours | section 7 |
| A1 | Invalidate the note index only on membership change | InTest | A4a | `WITNESS.md` "The note index" |
| A7b | NOTEIDX always on; drop `-walletwitnessnote` | ToDo | A4a | `WITNESS.md` "Ship state" |
| A4b | Full genesis fat-wallet `-rescan`, overnight, scripted, outside the harness: remeasures M-WAL-RESCAN-FAT; gates nothing | ToDo | The fat wallet; an overnight slot | `WITNESS.md` "Cost" |
| A3 | Benchmark both witness bottlenecks post-Sapling, on a disposable tip above height 492,850 with fat-wallet notes in range | ToDo | A1; the tip and the fat wallet | `WITNESS.md` "Cost" |
| A9 | `getalldata` datatype matrix at a quiet full tip (BENCH-GAD-IDX1) | ToDo | `fulltip-812-datadir` | section 7 |
| A12 | Lab soak under rebuild: status polling, spend storm under -31, `getalldata` after rebuild | ToDo | `fulltip-812-datadir`; the fat wallet | section 7 |
| A10 | p1 rescan profile; first confirm by timing that p1 runs long enough to profile | ToDo | The p1 wallet | `WITNESS.md` "Cost" |
| P6 | Anchor depth for shielded spends; subsumes what remains of P4 | ToDo | P5 | `PRODUCT.md` "P6. Anchor depth for shielded spends" |
| B6 | Async worker experiments: one then several workers, idle and loaded | ToDo | B4 | `CONCURRENCY.md` "Read-only RPC under concurrency" |
| C2 | Review level and category assignment | ToDo | C1 | section 7 |
| C4 | Alerting: what an operator must see, and how | ToDo | C2 | -- |
| N9 | Per-workload utilization profile generated from the ledger, over checkpoint progress series rather than endpoints | ToDo | N2 | section 7 |
| D3 | Section-number citations to heading titles; `check_citations.py` fails on section numbers, bare file names, a cited heading that does not exist, an `M-*` id with no row, and a path or script flag the tree lacks | ToDo | D1 | -- |
| D6 | Rules in one place per scope: `POLICY.md` keeps the perf-specific rules; general writing rules defer to Zero's DOC-CONVENTIONS | InTest | Z5 | section 7 |
| N15 | Lab inputs located and identified: snapshot archives and sibling repositories | InProgress | A height-ordered tiny archive rebuilt with `contrib/linearize` outside `/tmp` | section 7 |
| K8 | Remeasure on the current build: the six-capture CPU profile (M-CPU-SEQ), which predates uniblake, the Equihash skip and the IBD hoist and overstates Equihash; and stock reindex h600k-900k, n=4, the before/after for M-RX-POSTSAP-STOCK | ToDo | An idle-host slot | `SYNC.md` "Where the time goes"; `README.md` "postsapling_reindex.sh" |
| N1 | Microbenchmark baseline: the rest of the `zcbenchmark` suite | InTest | A populated wallet for several benchmarks | section 7 |
| P13 | Redundant Equihash verification: skip landed in `37f3f3459`; per-caller `ZERO_PERF` counters, M-EQ-VERIFY-SITES; pinned by six `miner_tests` cases, each failing under its mutation (`SYNC.md`; `test-logs/p13-tests-20261005/`). `getblock` concurrent with reindex not covered | InTest | Hand-off batch 2 | `SYNC.md` "Equihash verifications per block" |
| P19 | Delete unbuilt `src/snark/`: done here (`f34332af9`); Zero still carries it | InTest | Hand-off batch 1 | section 7 |
| Q8 | Release note for the tromp default | ToDo | Hand-off batch 3 | -- |
| Z5 | `reporoot/DOC-CONVENTIONS.md`: replacement for the DOC-CONVENTIONS entry, approved | ToDo | Zero applies it | -- |
| Z6 | `reporoot/MAINTREE_CHANGES.md`: `src/` and `qa/` changes for Zero to review and apply, with release notes for behaviour changes | InProgress | Section 2 step 3 | -- |
| Z8 | `reporoot/TODO.proposals.md`: REL-05 (`contrib/spendfrom/`, `contrib/qos/`), DOC-ROOT-PLANNING, three items out of `TODO.md` | ToDo | Zero | -- |
| Z2 | Zeronode test track, now Zero ZN-01 and DOC-02: argument validation on existing Boost; founders window; two-node `startalias`; zeronode `invalidateblock` after A5 | ToDo | Zero; A5 for the last part | -- |
| Z7 | Root documents here are older than Zero's; refresh them from Zero by merge, not by edit | ToDo | Hand-off batch 1 landing | -- |

---

## 5. Decided

One line per direction taken or dropped: status, how it is enabled, and what
it binds later. The reasoning lives in the cited document; a rejected line
reopens only on the condition given there.

| Direction | Status | Enabled | Lasting implication | Reasoning |
|-----------|--------|---------|---------------------|-----------|
| Equihash hashing via uniblake | Adopted | default build | Builds need the uniblake sibling; where it lives is Zero's decision | `HASHLIBS.md` |
| tromp solver as mining default; sort comparator fold; `Xc.reserve()` | Adopted | default, `-equihashsolver` | Falls back to the reference solver off (192,7), pinned by `miner_tests/equihashsolver_default_and_param_guard`; release note Q8 | M-EQ-TROMP-SPEEDUP; `equ/` |
| Skip Equihash re-check at `BLOCK_VALID_TREE` (P13) | Adopted | default | Header trust rests on the index entry and on the `ReadBlockFromDisk` re-check; six tests pin both | `SYNC.md` "Equihash verifications per block" |
| `IsInitialBlockDownload` hoist; single `CompareTo`; merkle-root latch | Adopted | default | -- | `LOCKS.md`; `SYNC.md` "Shipped changes" |
| `-walletwitness=ibd-defer`, `-walletwitnessnote=1` | Adopted, opt-in; default-on not pursued | flags, default off | When on, spends wait for one rebuild after import (`-31`/`-33`) | `WITNESS.md` "Choices" |
| DIRTY | Rejected | not built | -- | `WITNESS.md` "Choices" |
| FDCACHE | Compiled out | `ZERO_FDCACHE` build only | Reopens with cold-cache or Linux data (P8) | `SYNC.md` "Disk I/O and FDCACHE" |
| Equihash first-list batch hashing (`EQUIHASH_BATCH_HASH`) | Not selected: lower performance | compile-time macro; code kept | Not proposed to Zero | commit `611e9efb7` |
| Minimal lab conf: no Insight, default `dbcache` | Adopted | harness default; `ZERO_PERF_ARCHIVE_CONF=1` restores an archive's | Compare only rows with equal `features.runtime` | M-RX-TINY-20260930 |
| Reorg bound: 99 blocks, then shutdown (TNT-02, was A11) | Settled by Zero | default | A deeper reorg stops the node with a message; the witness cache is sized to the bound (A8); TENT's unbounded follow is not ported | Zero `UpdateZero.md` DEF-07 |
| `reporoot/` stays tracked as it is | Adopted | -- | -- | -- |

Settled, do not re-derive: recursion is six inherited lock-per-function
sites (M-LOCK-ATTR, `LOCKS.md` "What recursion actually exists"); earlier
totals were acquisition counts.

---

## 6. Postponed and aside

Not scheduled; each reopens by decision. Analysis stays in the cited
document.

| Id | Item | Disp | Detail |
|----|------|------|--------|
| Y1 | Groth16 batch verification: Option A (hand-port) or B (adopt `sapling-crypto`) | Postponed | `PerfGroth.md` "4. The decision: Option A vs Option B" |
| Y2 | Build librustzcash on rustc 1.98.1 | Postponed | `LIBRUSTZCASH.md` "4. Remaining validation, and what it costs" |
| Y3 | Vendor librustzcash in-tree; then decide the base: stay pinned, or a fork's newer base | Postponed | `LIBRUSTZCASH.md` "3. Recommendation" |
| R3 | `CBLAKE2bWriter` on uniblake | Postponed | `HASHLIBS.md` "C. `CBLAKE2bWriter` and the four one-shot sites" |
| Q2 | Measure the threaded tromp solver | Postponed | `equ/PLAN.md` "Queued solver work" |
| Q4 | Per-phase CPU profile of a mainnet (192,7) solve (G5) | Postponed | `README.md` "mine_bench.sh" |
| Q5 | Deployment fleet mix (INV-ARM-MIX) | Postponed | -- |
| Q6 | Solver stages S1-S4 | Postponed | `equ/PLAN.md` "9. Sequencing and honest expectations" |
| Q9 | Stamp variant and UTC into solver dump paths; `eqbench.sh` wrapper; solver variant registry | Postponed | `equ/PLAN.md` "Queued solver work" |
| Q10 | Review `equ/` under the writing rules; move its queue into this register; delete `equ/README.md` | Postponed | section 7 |
| K3 | Thermal state over long runs; the `therm` column in `util.tsv` stays | Postponed | -- |
| K5 | Era-bounded rematch using shielded density bands (L3) | Postponed | `Measures.md` M-DENS-* rows |
| P8 | FDCACHE disposition; cold-cache (`drop_caches`) and Linux/Windows measurement | Postponed | `SYNC.md` "Disk I/O and FDCACHE" |
| P18 | `debug.log` is unbounded: trimmed only at startup, and never with `-debug` | Postponed | section 7, N29 |
| F1 | Linux VPS and Windows/WSL runbook, folding in the platform tool survey | Postponed | `PerfPlatforms.md` "6. Recommendations, ranked" |
| F2 | First non-macOS capture | Postponed | `PerfPlatforms.md` "3.1 CPU profiling -- the direct xctrace equivalent" |
| F4 | Re-validate the consolidated tree on another platform | Postponed | -- |
| F5 | CI: the working branch in the push trigger; a lint job ahead of the 240-minute build | Postponed -- needs repository settings | section 7 |
| F6 | Port `res_sample.sh` to `psutil` | Postponed | `PerfPlatforms.md` "3.3 Resource sampling" |
| F8 | Retest the `--strict` / `--suite` release track on Linux | Postponed | -- |
| F9 | Windows MXE cross-build, never run here; then hardening and ETW profiling | Postponed | `PerfPlatforms.md` "4. Windows 11" |
| F10 | Release engineering: params archival, branch-id CI, OpenSSL 3, Debian packaging | Postponed | -- |
| H3 | Item ids, names and status reconciled with Zero's `TODO.md` | Postponed | section 7 |
| H4 | Regroup items by module, with H3 | Postponed | section 7 |
| Z10 | `reporoot/MIGRATION_PLAN.md`: `insight` to the organisation when convenient | Postponed | -- |
| K6 | Stack-logged allocation window entirely post-Sapling | Aside -- unlikely to change the conclusion | `SYNC.md` "Memory" |
| K7 | Post-Sapling bootstrap capture | Aside -- bootstrap and reindex agree within ~3 points per bucket | `SYNC.md` "Where the time goes" |

---

## 7. Item detail

Only what no subject document owns, by id.

**A8.** Steps: (1) `static_assert(WITNESS_CACHE_SIZE > MAX_REORG_LENGTH)` in
`wallet/wallet.h`, so changing either constant alone fails the build; (2)
every use trims witnesses down to `WITNESS_CACHE_SIZE` and never below
(`wallet.cpp` `DecrementNoteWitnesses`, `BuildWitnessCache`), confirmed;
(3) state the relation in `WITNESS.md` "Reorg and crash", list the change in
`reporoot/MAINTREE_CHANGES.md`, close A8. A5 is not involved: it concerns a
null `pindex`, not reorg depth.

**F5.** `.github/workflows/tests.yml` runs on push to `main`, `master` and
`develop`, on pull requests, and by hand: one Ubuntu 24.04 job, params fetch,
`zcutil/build.sh -j2`, `contrib/run-tests.sh --strict`, 240-minute timeout.
No job runs `lint-perf.sh` or `validate.sh`, and `perf_b1b2` pushes trigger
nothing, so every perf gate is local. F5 adds the working branch to the
trigger and a lint job that fails fast before the build; both are workflow
edits that need repository settings on the Zero repository.

**A4a.** Exits A1 and gives A7b its evidence. The question both ask is
whether `SelectWalletTxsForWitnessScan` still dominates in the post-1.6M
band, where each founders coinbase entering the wallet used to rebuild the
note index; a band of 50,000 blocks there answers it. `z_importkey` with an
existing key, `rescan=yes` and a `startHeight` runs
`ScanForWalletTransactions` from that height on a lab node at tip with the
fat wallet; the key stays out of every document. A4b's genesis run then only
refreshes M-WAL-RESCAN-FAT. A7b also needs NOTEIDX to produce the same
witnesses as the full scan, which the gate tests in `WITNESS.md` "Ship state"
already cover.

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

**P24** (`test-logs/rpc-test-20260917/`). Measure insert and erase
separately before choosing a fix. The ordered set is maintained continuously
by its comparator and only 214 survivors need ordering; not materialising
the full set may remove the cost.

**P1** gates any phase summary: proof verification sits in no timer, so a
summary built today omits most post-Sapling cost while appearing complete.

**P19.** In no makefile, no objects, no includes; entered as a subtree in
`f4d8cd127`. Zcash removed libsnark in `9ce0caf20` (v2.1.0); Pirate, Hush3
and Firo have too. Zero and Zclassic still carry it; Zero does not compile
it.

**Q3.** The fold's speedup was taken on a working-tree patch; no recorded
run confirms the committed code still produces the five baseline solutions
(`test-logs/eqvectors/solver_baseline_192_7.txt`, archived and `0444`). One
run is the exit condition.

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
and never deletes; its self-test runs in `lint-perf.sh`. Missing:

- Reconciliation: a check, run from `validate.sh`, that every run
  `Measures.md` and `PLAN.md` name exists. M-LAB-REPRO cites a driver log
  that does not exist.
- Rules for the store: what a run directory must contain (driver log,
  measures, recorded rows) before it counts as complete.

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

**N1.** Recorded: `verifysaplingspend` / `verifysaplingoutput` and their
`create` counterparts (M-ZCB-SAP-VERIFY, M-ZCB-SAP-CREATE).
`parameterloading` fails with RPC error -3. Several of the rest need a
populated wallet.

**H1, H2.** H1 (Finished): formatting changes only inside a hunk already
changed for a functional reason; `validate.sh` checks it. H2 exists because a
fix reached the tree with a correct in-code comment and no record anywhere.

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

**H3, H4** (postponed). H4's module regrouping is superseded by this file's
schedule layout; what remains is ids. Zero labels items by area and name (`WAL-GETALLDATA-W5`,
`TST-01`; prefixes CON, WAL, OPS, REL, EXT, TST, DOC, TNT) and states status
by list. The proposal when reopened: area prefix plus number (`WIT-01`),
Zero's prefix for items handed to Zero, old ids mapped once until the next
release; one status value mapped to Zero's lists (Next, Active, InTest,
Pending with its condition, Aside, Finished).

**Q10** (postponed). `equ/` holds `README.md` (an index, figures, next
actions and a dated review), `FINDINGS.md`, `SOLVER.md`, `VENDORED.md`,
`METHOD.md` and `PLAN.md`. `equ/README.md` goes rather than folding into
`METHOD.md`: figures and "What this analysis established" to
`equ/FINDINGS.md`, "Next actions" to this register, the file table to the
documentation map. `equ/PLAN.md` queue ids D1-D5 collide with group D here.

---

## 8. Closed ids

Settled by Zero: A11 (DEF-07, section 5).

Finished: A2 on confirmation (section 2), B2 `IsInitialBlockDownload` hoist,
B3 recursive sites, B5 P25 claim retracted, C3, D12, E2 non-blake2b
libsodium surface, H1, K9 into K8, N10, N11, N13, N14, N18, P17 out-of-order
children (no change needed), P23 comparator single `CompareTo`, P26 stray
`concept` on `README.md` line 1, Z1, Z4.

Merged: A7 into A7a and A7b; A4 into A4a and A4b; B7 into B1; D4 into D2;
D5 into F1; D7 into D10; D9 into Q10; D13 and D14 into D8; N3 into N2; N19
into N4; N8 into N9; N5, N6, N16, N20, N22, N23 into N21; N24, N25 into N15;
Z9 into Z8.

Rejected: DIRTY (section 5).
