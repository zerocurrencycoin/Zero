# Changes this tree made outside `contrib/perf/`, for Zero to review

Draft for Zero. Compared against Zero `72e421e41` and its working tree; this
branch diverged from Zero at `198b3b287`. Regenerate the list with
`git diff --stat 198b3b287 HEAD -- src qa`. None of these is in Zero yet.

Effect on a default build: **behaviour** changes what a release does;
**perf-only** compiles only with `--enable-perf` (`ZERO_PERF`) or a debug
lock build; **test** changes tests only.

| Subject | Files | Effect | Register |
|---------|-------|--------|----------|
| Equihash hashing through uniblake instead of libsodium; `EhHashState` | `crypto/eh_hashstate.h`, `crypto/equihash.*`, `pow/tromp/*`, `zcbenchmarks.cpp`, `gtest/test_equihash.cpp`, `Makefile.am`, `depends/packages/uniblake.mk`, `packages.mk` | behaviour, consensus-adjacent: needs the uniblake sibling to build | `SYNC.md` "Shipped changes" |
| Equihash batch list generation (`EQUIHASH_BATCH_HASH`), defined by no build | `crypto/equihash.*` | none; not proposed -- measured slower, kept here as groundwork (`PLAN.md` "Decided") | -- |
| Mining solver default `tromp`, with a fallback to the reference solver off (192,7); help text and reported default match | `miner.cpp`, `init.cpp`, `metrics.cpp`, `test/miner_tests.cpp` | behaviour: every miner's default solver. Needs a release note | Q8 |
| `generate` logs that `-equihashsolver` does not apply to it | `rpc/mining.cpp` | log line | -- |
| tromp driver written once (`EhTrompSolveRounds`); sort comparator fold; `Xc.reserve()` | `pow/tromp/equi_miner.h`, `crypto/equihash.cpp`, `test/equihash_tests.cpp` | solver speed; same solutions (M-EQ-TROMP-PAIRED) | Q3 |
| Skip re-verifying Equihash for a header already at `BLOCK_VALID_TREE`; eight tests in `header_check_tests.cpp` pin the skip, its bounds (merkle check, below `BLOCK_VALID_TREE`) and the checks it relies on | `main.cpp`, `test/header_check_tests.cpp` | behaviour: fewer verifications per block on reindex | P13 |
| `IsInitialBlockDownload` hoisted out of per-block loops; block-index comparator calls `CompareTo` once | `main.cpp` | speed | B2, P23 |
| Missing locks in `getspentinfo` and `getblockdeltas` (upstream `14ec1016b`) | `rpc/misc.cpp`, `rpc/blockchain.cpp` | correctness | P12, P15 |
| Sapling migration refuses a Sprout note with no witness (`Insufficient Sprout witnesses.`) instead of calling `get()` on an empty optional; as Zcash `99e41f36c` | `wallet/asyncrpcoperation_saplingmigration.cpp` | safety: undefined behaviour becomes an RPC error | P4 |
| Script-check threads capped at 4 (`MAX_SCRIPTCHECK_THREADS`); `-par=0` still follows the core count below the cap | `main.h` | behaviour: hosts above 4 cores run 3 workers instead of up to 15. Needs a release note | P20 |
| Witness RPC gate widened: `z_shieldcoinbase` and `z_mergetoaddress` refused while witnesses are unbuilt, as `z_sendmany` and `getalldata` are | `rpc/server.cpp`, `test/rpc_zero_exclusive_tests.cpp` | behaviour; under revision: keep `z_mergetoaddress`, drop `z_shieldcoinbase`, which reads no witnesses (`PRODUCT.md` P28). Not proposed until revised | P28 |
| `depends` release optimisation `-O1` -> `-O2` on darwin, linux and mingw32 | `depends/hosts/*.mk` | build: every `depends` library; timings from this tree and from Zero builds compare only when both use the same level | -- |
| libsodium 1.0.21 -> 1.0.22 | `depends/packages/libsodium.mk` | build | `SODIUM_SURVEY.md` |
| `getzeronodescores` test case | `test/rpc_zeronode_tests.cpp` | test | -- |
| Root files: perf scratch paths in `.gitignore`; stale `depends` stamp check in `zcutil/build-native.sh`; build validation in `zcutil/fzero.sh`; help and filters in `contrib/run-tests.sh`; `-jN` guidance in `BUILD_ZERO.md`; TNT-18 row in `UpdateZero.md` | root | tooling and documents | Z7 |
| Witness cache depth pinned above the reorg bound: `static_assert(WITNESS_CACHE_SIZE > MAX_REORG_LENGTH)` | `wallet/wallet.h` | none; to become a message rather than an assert, later | A8 |
| Fatal stop exits non-zero: `AbortNode` sets a flag (`StartFatalShutdown`) that `zerod` turns into `EXIT_FAILURE` after the orderly shutdown; the first fatal error is reported once, later ones as "Fatal error while stopping" | `main.cpp`, `init.*`, `bitcoind.cpp` | behaviour: supervisors see disk-full and I/O-error stops as failures. Needs a release note | C7 |
| `ReportFatalError`: a fatal reason goes to `debug.log` and stderr, flushed, before `exit()` or `abort()`; used by the wallet null-`pindex` guards and the chainstate read-error abort | `util.*`, `wallet/wallet.cpp`, `init.cpp` | messages only | C9 |
| A message box text that already starts with its caption is not prefixed again ("Error: Error: ..."); two such texts lose their own "Error: " | `noui.cpp`, `main.cpp`, `httprpc.cpp` | messages only | C9 |
| `SelectEquihashSolver`: one function for the solver choice (default `tromp`, fallback off (192,7)), used by the miner and the metrics screen; an unknown `-equihashsolver` is refused at startup instead of hitting an assert in the miner thread | `miner.*`, `init.cpp`, `metrics.cpp` | behaviour: a bad option stops startup with a message. Needs a release note | G4, C9 |
| Tests split by subject: header checks around the Equihash skip in `header_check_tests.cpp` (eight cases), solver choice in `miner_tests.cpp`, shared regtest helpers in `regtest_helpers.h` | `test/*`, `Makefile.test.include` | test | P13, G4 |
| Under `-daemon`, stderr appended to `<datadir>/<network>/stderr.log` | `bitcoind.cpp` | behaviour: new file in the datadir; assert and abort text kept. Needs a release note | C8 |
| Note index invalidated only on membership change | `wallet/wallet.*`, `wallet/gtest/test_wallet.cpp` | wallet speed | A1 |
| Opt-in witness modes `-walletwitness=ibd-defer`, `-walletwitnessnote=1`; incremental Merkle root cached | `wallet/*`, `zcash/IncrementalMerkleTree.*`, `qa/rpc-tests/wallet_witness_defer.py` | none unless the flags are set; root cache always on. Held back: default-on not pursued (`PLAN.md` "Decided") | `WITNESS.md` "Ship state" |
| Explicit arguments at the five `GetFilteredNotes` callers | `wallet/asyncrpcoperation_*.cpp`, `wallet/rpcwallet.cpp` | none | P10 |
| Perf layer: phase timers, proof counters, per-caller Equihash counters, script-check pool utilization, `-perffdcache` | `main.*`, `pow.*`, `checkqueue.h`, `init.cpp` | perf-only | P1, P8 |
| Recursive-lock attribution by lock location | `sync.*` | debug lock builds only | `LOCKS.md` |
| `src/snark/` deleted: in no makefile, no object, no include | `src/snark/` | none | P19 |
| `ops-validate.sh` ledger lines carry the LAB node's runtime, checked against its log; `null` where `contrib/perf/debuglog.py` is absent | `contrib/ops-validate.sh` | ledger field; a node that did not apply its flags fails the command. Not proposed until Zero carries `contrib/perf/debuglog.py`; without it the field is always `null` | N21 |
| Test fixes: Zero constants in `test_framework/util.py`, relative heights, `Decimal` to `int`, tier lists, zeronode script modes | `qa/` | test | `TESTING.md` |

## Interfaces to reconcile in the 4.1.0 merge

What this tree adds or changes at an interface since `198b3b287`. Each is
checked against Zero's `zero-410` when it is merged.

| Kind | Name | Change | Builds |
|------|------|--------|--------|
| option | `-equihashsolver=tromp\|default` | new; default `tromp`; an unknown value stops startup | all |
| option | `-par` | upper bound 16 -> 4 | all |
| build flags | `depends` `*_release_CFLAGS` | `-O1` -> `-O2` | all |
| package | libsodium | 1.0.21 -> 1.0.22 | all |
| option | `-sendalert` | new, default off, gates the alert thread; Zero removed the alert system, so it goes in the merge | all |
| option | `-mrclogevery=<n>` | new, blocks between perf log lines | `ZERO_PERF` |
| option | `-perffdcache`, `-perfbufsize=<n>` | new, block-file read latch | `ZERO_FDCACHE` |
| configure | `--enable-perf` | new; defines `ZERO_PERF` and `ZERO_FDCACHE` | -- |
| link | `-luniblake` | added to `LIBZCASH_LIBS`; `depends` recipe for the uniblake sibling | all |
| macro | `EQUIHASH_BATCH_HASH` | new, defined by no build | none |
| type | `eh_HashState` -> `EhHashState` | `Equihash::InitialiseState`, `IsValidSolution` take the new type (`crypto/eh_hashstate.h`) | all |
| function | `SelectEquihashSolver(params)` | new (`miner.h`) | all |
| function | `StartFatalShutdown()`, `FatalShutdownRequested()` | new (`init.h`) | all |
| function | `ReportFatalError(where, what)` | new (`util.h`) | all |
| function | `CWallet::HasNoteData(wtx)` | new, static (`wallet.h`) | all |
| function | `CCheckQueue::GetUtilization(...)` | new (`checkqueue.h`) | all |
| function | `InitPerfLogEvery`, `LogPerfProofCounters`, `LogPerfEquihash`, `PerfEqSiteScope`, `GetCachedReadFile`, `InitPerfFdCache`, `LogReadFdCacheStats`, `LogLockStats` | new | perf and debug-lock builds |
| call sites | `GetFilteredNotes` | arguments explicit at five callers; signature unchanged | all |
| output | `<datadir>/<network>/stderr.log` | new under `-daemon` | all |
| output | exit status | 1 after a fatal stop | all |
| environment | `DUMP_1927_SOLVER`, `SOLVE_TIMING_1927`, `SOLVE_TIMING_SOLVER`, `SOLVE_TIMING_DUMP`, `SOLVE_TIMING_TSV` | new, `test_bitcoin` opt-in cases only | tests |
| script | `contrib/ops-validate.sh` | ledger lines carry the node's runtime | -- |

## Hand-off batches

Proposed order. Review of the batches is postponed (`PLAN.md` Z6); this
section only groups the rows above.

| Batch | Purpose | Rows |
|-------|---------|------|
| 1 | Correctness and cleanup, nothing users notice | Sapling migration witness guard and missing locks in `getspentinfo` / `getblockdeltas` (offered for v4.1.0, below); `src/snark/` deleted; explicit `GetFilteredNotes` arguments; fatal messages reported and flushed, no doubled "Error:"; test fixes in `qa/` |
| 2 | Speed, on by default | skip re-verifying Equihash at `BLOCK_VALID_TREE` with its tests (`header_check_tests.cpp`); `IsInitialBlockDownload` hoist and single `CompareTo`; merkle-root latch (with the witness row's root cache); note index invalidated only on membership change, once A1 exits |
| 3 | Behaviour users see, each with a release note | script-check threads capped at 4; tromp solver default; uniblake for Equihash hashing (after Zero decides where uniblake lives); fatal stop exits non-zero; stderr kept under `-daemon`; unknown `-equihashsolver` refused at startup |
| Held | Not proposed now | witness RPC gate (P28); witness cache bound as a message; `depends` `-O2` and libsodium 1.0.22 (build-wide; Zero decides); opt-in witness modes; perf layer and lock attribution (perf builds only); Equihash batch list generation; `ops-validate.sh` runtime field |

## Offered for v4.1.0, before rc1

Two fixes from batch 1, one Zero commit each. Both change nothing users see
and apply cleanly to `zero-410` (`git apply --check`, 2026-10-16). Comments
below are cut to the invariant, as Zero's `AGENTS.md` "Code" requires.

**Sapling migration: missing Sprout witness.**
`wallet/asyncrpcoperation_saplingmigration.cpp`, `main_impl`, after
`GetSproutNoteWitnesses` and before `builder.AddSproutInput`:

```cpp
// GetSproutNoteWitnesses leaves an entry unset when a note has no witness;
// get() on an unset optional is undefined behaviour.
if (vInputWitnesses.empty() || !vInputWitnesses[0]) {
    throw JSONRPCError(RPC_WALLET_ERROR, "Insufficient Sprout witnesses.");
}
```

- Found by audit: of the eight `GetS*NoteWitnesses` callers, this is the one
  that does not check. Reached when migration is enabled (`z_setmigration`),
  the wallet holds Sprout notes, and the timer fires (height 499 mod 500)
  while witnesses are unbuilt -- during a rebuild or under
  `-walletwitness=ibd-defer`. The RPC gate does not cover the timer.
- Upstream: Zcash `99e41f36c` (v5.0.0) made the getters return `bool` and
  throws the same error at this site. TENT and Ycash carry the unchecked
  call; Pirate, Hush and Zclassic removed Sprout migration.
- Test: none. Zcash added none for this site; Zero's
  `sprout_sapling_migration.py` is retired. Verification is the build and
  the existing suites.

**Insight RPCs: `LOCK(cs_main)`.** As Zcash `14ec1016b` (v2.1.1):

- `rpc/blockchain.cpp`, `getblockdeltas`: `LOCK(cs_main);` before the
  `mapBlockIndex` lookup. It covers `mapBlockIndex`, `chainActive` and
  `GetSpentIndex` in `blockToDeltasJSON`. Without it the RPC reads index
  structures the import thread modifies -- a data race in every build.
- `rpc/misc.cpp`, `getspentinfo`: the `GetSpentIndex` call inside
  `{ LOCK(cs_main); ... }`. Without it a mempool and index answer can
  disagree for a moment; the mempool has its own lock and the index is a
  thread-safe database.
- Comment for both: `// GetSpentIndex requires cs_main.`
- Only `-insightexplorer` nodes serve these RPCs. `GetSpentIndex` asserts
  the lock, but `AssertLockHeld` compiles only under `DEBUG_LOCKORDER`,
  which is why release builds never showed it.
- Test: `spentindex.py` (Tier B pass) calls both RPCs, and `rpc_tests`
  (Boost) calls `getblockdeltas`. Run both once on a `-DDEBUG_LOCKORDER`
  build: without the locks `AssertLockHeld` aborts, with them they pass. No
  new test needed.

## Review before applying

- Code comments added here carry dates, measured figures and history (for
  example `httpserver.h` on `-rpcthreads` and `-rpcworkqueue`). DOC-CONVENTIONS
  forbids those in inline comments; strip them to the invariant when applying.
- The uniblake dependency resolves to a sibling checkout; its repository is
  on a personal account (`MIGRATION_PLAN.md`).
- Each behaviour change ships with its release note; the solver default is
  the one users see.
