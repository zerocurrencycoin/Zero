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
| Note index invalidated only on membership change | `wallet/wallet.*`, `wallet/gtest/test_wallet.cpp` | wallet speed | A1 |
| Opt-in witness modes `-walletwitness=ibd-defer`, `-walletwitnessnote=1`; incremental Merkle root cached | `wallet/*`, `zcash/IncrementalMerkleTree.*`, `qa/rpc-tests/wallet_witness_defer.py` | none unless the flags are set; root cache always on. Held back: default-on not pursued (`PLAN.md` "Decided") | `WITNESS.md` "Ship state" |
| Explicit arguments at the five `GetFilteredNotes` callers | `wallet/asyncrpcoperation_*.cpp`, `wallet/rpcwallet.cpp` | none | P10 |
| Perf layer: phase timers, proof counters, per-caller Equihash counters, script-check pool utilization, `-perffdcache` | `main.*`, `pow.*`, `checkqueue.h`, `init.cpp` | perf-only | P1, P8 |
| Recursive-lock attribution by lock location | `sync.*` | debug lock builds only | `LOCKS.md` |
| `src/snark/` deleted: in no makefile, no object, no include | `src/snark/` | none | P19 |
| `ops-validate.sh` ledger lines carry the LAB node's runtime, checked against its log; `null` where `contrib/perf/debuglog.py` is absent | `contrib/ops-validate.sh` | ledger field; a node that did not apply its flags fails the command. Not proposed until Zero carries `contrib/perf/debuglog.py`; without it the field is always `null` | N21 |
| Test fixes: Zero constants in `test_framework/util.py`, relative heights, `Decimal` to `int`, tier lists, zeronode script modes | `qa/` | test | `TESTING.md` |

## Review before applying

- Code comments added here carry dates, measured figures and history (for
  example `httpserver.h` on `-rpcthreads` and `-rpcworkqueue`). DOC-CONVENTIONS
  forbids those in inline comments; strip them to the invariant when applying.
- The uniblake dependency resolves to a sibling checkout; its repository is
  on a personal account (`MIGRATION_PLAN.md`).
- Each behaviour change ships with its release note; the solver default is
  the one users see.
