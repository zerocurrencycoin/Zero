# Changes this tree made outside `contrib/perf/`, for Zero to review

Draft for Zero. Compared against Zero `72e421e41` and its working tree; this
branch diverged from Zero at `198b3b287`. Regenerate the list with
`git diff --stat 198b3b287 HEAD -- src qa`. None of these is in Zero yet.

Effect on a default build: **behaviour** changes what a release does;
**perf-only** compiles only with `--enable-perf` (`ZERO_PERF`) or a debug
lock build; **test** changes tests only.

| Subject | Files | Effect | Register |
|---------|-------|--------|----------|
| Equihash hashing through uniblake instead of libsodium; `EhHashState` | `crypto/eh_hashstate.h`, `crypto/equihash.*`, `pow/tromp/*`, `Makefile.am` | behaviour, consensus-adjacent: needs the uniblake sibling to build | `SYNC.md` "Shipped changes" |
| Equihash batch list generation (`EQUIHASH_BATCH_HASH`), defined by no build | `crypto/equihash.*` | none; not proposed -- measured slower, kept here as groundwork (`PLAN.md` "Decided") | -- |
| Mining solver default `tromp`, with a fallback to the reference solver off (192,7); help text and reported default match | `miner.cpp`, `init.cpp`, `metrics.cpp`, `test/miner_tests.cpp` | behaviour: every miner's default solver. Needs a release note | Q8 |
| `generate` logs that `-equihashsolver` does not apply to it | `rpc/mining.cpp` | log line | -- |
| tromp driver written once (`EhTrompSolveRounds`); sort comparator fold; `Xc.reserve()` | `pow/tromp/equi_miner.h`, `crypto/equihash.cpp`, `test/equihash_tests.cpp` | solver speed; same solutions | Q3 |
| Skip re-verifying Equihash for a header already at `BLOCK_VALID_TREE`; six tests pin the skip, its bounds (merkle check, below `BLOCK_VALID_TREE`) and the checks it relies on | `main.cpp`, `test/miner_tests.cpp` | behaviour: fewer verifications per block on reindex | P13 |
| `IsInitialBlockDownload` hoisted out of per-block loops; block-index comparator calls `CompareTo` once | `main.cpp` | speed | B2, P23 |
| Missing locks in `getspentinfo` and `getblockdeltas` (upstream `14ec1016b`) | `rpc/misc.cpp`, `rpc/blockchain.cpp` | correctness | P12, P15 |
| Witness cache depth pinned above the reorg bound: `static_assert(WITNESS_CACHE_SIZE > MAX_REORG_LENGTH)` | `wallet/wallet.h` | none; fails the build if either constant changes alone | A8 |
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

## Hand-off batches

Proposed order. Review of the batches is postponed (`PLAN.md` Z6); this
section only groups the rows above.

| Batch | Purpose | Rows |
|-------|---------|------|
| 1 | Correctness and cleanup, nothing users notice | missing locks in `getspentinfo` / `getblockdeltas`; `src/snark/` deleted; explicit `GetFilteredNotes` arguments; witness cache pinned above the reorg bound; fatal messages reported and flushed, no doubled "Error:"; test fixes in `qa/` |
| 2 | Speed, on by default | skip re-verifying Equihash at `BLOCK_VALID_TREE` with its tests (`header_check_tests.cpp`); `IsInitialBlockDownload` hoist and single `CompareTo`; merkle-root latch (with the witness row's root cache); note index invalidated only on membership change, once A1 exits |
| 3 | Behaviour users see, each with a release note | tromp solver default (after Q3); uniblake for Equihash hashing (after Zero decides where uniblake lives); fatal stop exits non-zero; stderr kept under `-daemon`; unknown `-equihashsolver` refused at startup |
| Held | Not proposed now | opt-in witness modes; perf layer and lock attribution (perf builds only); Equihash batch list generation; `ops-validate.sh` runtime field |

## Review before applying

- Code comments added here carry dates, measured figures and history (for
  example `httpserver.h` on `-rpcthreads` and `-rpcworkqueue`). DOC-CONVENTIONS
  forbids those in inline comments; strip them to the invariant when applying.
- The uniblake dependency resolves to a sibling checkout; its repository is
  on a personal account (`MIGRATION_PLAN.md`).
- Each behaviour change ships with its release note; the solver default is
  the one users see.
