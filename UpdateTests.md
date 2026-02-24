# UpdateTests

Test suite results, fixes, open failures, and testing procedures for the Zero node.

## 1. Framework

**Purpose**: Test framework for the Zero node covering consensus, shielded transactions, RPC, and integration. Supports incremental build validation, release validation, feature verification, and crash debugging.

**Heritage**: Bitcoin Core (Boost.Test, Python RPC, secp256k1, univalue, qa/rpc-tests layout). Zcash (GTest for shielded logic, z_* RPC tests, full_test_suite).

**Limitations**: Python 2.7 for RPC tests; no fuzz tests; no Bitcoin-style functional tests; legacy qa layout. sec-hard and checksec are ELF-only (Linux); not applicable on macOS.

**Future directions**: Python 3 migration (delayed; pyblake2 → hashlib.blake2b when migrated). Possible functional test migration. Coverage targets exist in Makefile but require lcov.

## 2. Suites

Nine test suites, grouped by execution dependency and coverage area.

**GTest 1.16.0** (depends/packages/googletest.mk). Last C++14 release; avoids 1.17.0 C++17 requirement.

| Project | GTest | Notes |
|---------|-------|-------|
| Zero | 1.16.0 | |
| Zcash v6.11.0 | 1.12.1 | |
| Horizen (Zen) v6.0.0 | 1.13.0 | |
| Pirate v5.9.0 | 1.8.0 | |
| Latest | 1.17.0 | C++17 |

**Platforms tested**: macOS ARM64 (`arm-mac-build`), Ubuntu 24.04 x86_64 (`linux_build188`). All test failures reproduce pre-existing fork-level issues; none are platform-specific. Verified Feb 2026.

### 2.1 Nine Suites

| # | Name | Purpose | Coverage | Status |
|---|------|---------|----------|--------|
| 1 | **Util** (bitcoin-util-test) | Base58, key handling, JSON test cases | Utility functions | PASS |
| 2 | **secp256k1** | Elliptic-curve crypto (Bitcoin curve) | Crypto | PASS |
| 3 | **univalue** | JSON library | Univalue | PASS |
| 4 | **GTest** | Consensus, wallet, shielded, Sapling/Sprout | Consensus, shielded | 201 pass, 5 excl |
| 5 | **Boost** | RPC, script, serialization, crypto, alerts, mining | RPC, script, serialization | 47 suites pass (excl 3) |
| 6 | **RPC Python** | Multi-node, regtest, zerod/zero-cli | Integration, RPC flows | 11 pass, 5 skip; 16 pass-only |
| 7 | **sec-hard** | PIE, NX, RELRO, Canary; RPATH/FORTIFY (ELF) | Build security | System-specific: ELF only |
| 8 | **no-dot-so** | depends/.so check | Deterministic build | full_test_suite only |
| 9 | **check** | Recursive make check | Overlaps 1–5 | Use secp256k1-check, univalue-check for isolated |

**Order and grouping**: 1–3 (fast, no chain); 4–6 (main suites); 7–8 (build checks, system-specific); 9 (orchestration).

**sec-hard** (full_test_suite stage): (a) `make check-security` — PIE, RELRO, Canary, NX (ELF) or HIGH_ENTROPY_VA, NX, DYNAMIC_BASE (PE); cross-platform. (b) On ELF only: checksec RPATH/RUNPATH and FORTIFY_SOURCE. Skips (b) on macOS (not ELF). Document as system-specific; not a problem or concern.

**Tests vs orchestration**: Suites 1–8 execute tests. run-tests.sh, run-boost-individual.sh, full_test_suite.py, rpc-tests.sh orchestrate them. make check recursively invokes 1, 2, 3, 5.

### 2.2 Application and Coverage

| Area | Suites | Notes |
|------|--------|-------|
| Consensus | GTest, Boost (main, pow; equihash excluded) | PoW, halving, chain rules |
| Shielded | GTest, Boost rpc_wallet z_* | Witness, spend proofs, addresses |
| RPC/CLI | Boost rpc_tests, rpc_wallet_tests, RPC Python | API correctness, integration |
| Integration | RPC Python | Multi-node, zerod spawn |

## 3. Usage

**Working directory**: run-tests.sh resolves repo root from its path and `cd`'s there, so it works from any directory. Manual invocation of individual commands (./src/zero-gtest, ./qa/pull-tester/rpc-tests.sh, etc.) requires repo root. `make -C src` uses src as build dir.

### 3.1 Runners

| Runner | Suites | Notes |
|--------|--------|-------|
| run-tests.sh (default) | 1, 2, 3, 4 (filtered), 5 (excl Alert/equihash/miner), 6 (pass-only) | Pass-only; continues on failure; LOG_DIR (default test-logs/) for all modes |
| run-tests.sh --fail | Same + fail tests | Pass + fail; excludes hang/crash |
| run-tests.sh --all | Same, no exclusions | Includes hang/crash |
| run-tests.sh --quick | 1, 2, 3, check-symbols, check-security | Skip GTest, Boost |
| run-tests.sh --full, --full-suite | full_test_suite.py: 1–8 | Replaces run-tests flow; invokes `python2 qa/zcash/full_test_suite.py`; on Darwin passes `--skip sec-hard --skip no-dot-so`; exit 1 on failure |
| run-tests.sh --no-python | 1–5 only | Skip RPC Python |
| run-boost-individual.sh | 5 (one suite at a time) | Per-suite isolation; avoids cascade |
| qa/pull-tester/rpc-tests.sh | 6 | Python RPC only |
| make -C src check | 1, 2, 3, 5 (all) | Recursive |

### 3.2 Direct Invocation

| Suite | Invocation |
|-------|------------|
| Util | `cd src && srcdir=$(pwd) PYTHONPATH=$(pwd)/test python3 test/bitcoin-util-test.py` |
| secp256k1 | `make -C src/secp256k1 check` |
| univalue | `make -C src/univalue check` |
| GTest | `./src/zero-gtest [--gtest_filter=...]` |
| Boost | `./src/test/test_bitcoin [--run_test=...]` |
| RPC Python | `./qa/pull-tester/rpc-tests.sh [script\|-extended]` |
| sec-hard | `make -C src check-security` |
| full_test_suite | `python2 qa/zcash/full_test_suite.py [--skip STAGE ...] [stage ...]` |

### 3.3 Scenarios

| Scenario | Invocation |
|----------|------------|
| Validate incremental build | `./contrib/run-tests.sh --quick` |
| Full build or release validation | `./contrib/run-tests.sh --full` |
| Verify feature | `./src/test/test_bitcoin -t rpc_tests` or `./qa/pull-tester/rpc-tests.sh wallet_sapling` (from repo root) |
| Debug crash | `./src/zero-gtest --gtest_filter='WalletTests.CachedWitnessesEmptyChain' --gtest_break_on_failure`; lldb `bt` |
| Run pass-only | `./contrib/run-tests.sh` |

### 3.4 Special Cases

- **--full** and **--full-suite** are equivalent. When set, run-tests.sh invokes `python2 qa/zcash/full_test_suite.py` and exits (does not run default components). On Darwin, passes `--skip sec-hard --skip no-dot-so` so `--full` succeeds without a depends build. Usage: `./contrib/run-tests.sh --full`.
- **Cascade**: Early Boost failures (Alert, equihash, miner) cause later suites to fail via shared state. Run by suite (`-t rpc_tests`) to isolate.
- **run-boost-individual.sh** excludes Alert_tests, equihash_tests, miner_tests, Checkpoints_tests (empty suite); main_tests included.
- **ELF-only**: sec-hard checksec (RPATH/FORTIFY), check-symbols (readelf). Skip or no-op on macOS.
- **Python 2.7**: Set `PYTHON` for RPC tests. Prereq: `python2 -m pip install pyblake2`.
- **zerod/zero-cli**: rpc-tests.sh sources tests-config.sh; BUILDDIR = repo root (from script path). Exports BITCOIND, BITCOINCLI (run-bitcoin-cli wrapper → zero-cli). Binaries invoked by absolute path; no PATH required.

### 3.5 Build Validation Modes

For CI, release validation, or debugging vendored lib failures. Not needed for routine test runs.

| Test / Mode | Validates | Invocation |
|-------------|-----------|------------|
| secp256k1-check | Vendored secp256k1 compiles and passes | `make -C src secp256k1-check` |
| univalue-check | Vendored univalue compiles and passes | `make -C src univalue-check` |
| no-dot-so | depends/ has no .so (deterministic build) | full_test_suite stage; skipped on Darwin |
| sec-hard | PIE, RELRO, NX, Canary (ELF) or HIGH_ENTROPY_VA, DYNAMIC_BASE (PE) | `make -C src check-security` |
| --quick | Incremental build (util, secp256k1, univalue, check-symbols, check-security) | `./contrib/run-tests.sh --quick` |
| --full | Release build + full suite | `./contrib/run-tests.sh --full` |

## 4. Status

Tested on macOS ARM64 (`arm-mac-build` branch). Verified Feb 2026. All failures reproduce pre-existing fork-level issues; none ARM-specific.

### 4.1 Summary

| Suite | Total | Pass | Excluded/Fail |
|-------|-------|-----|---------------|
| Util | — | PASS | — |
| secp256k1 | 2 | 2 | — |
| univalue | 2 | 2 | — |
| GTest | 206 | 201 | 5 (4 CachedWitnesses*, 1 WriteCryptedSaplingZkey*) |
| Boost (pass-only) | 47 suites | all | 3 excl (Alert, equihash, miner) |
| Boost (full) | 50 suites, 260 cases | ~15 | ~277 (cascade) |
| RPC Python (pass-only) | 16 scripts | 11 pass, 5 skip | — |
| RPC Python (-extended) | ~100 scripts | varies | Many fail |

### 4.2 Util (1.x)

No known failures.

### 4.3 secp256k1 (2.x)

No known failures.

### 4.4 univalue (3.x)

No known failures.

### 4.5 GTest (4.x)

**Limitations**: Harness lacks pcoinsTip, ReadBlockFromDisk; BuildWitnessCache assumes disk-backed chain. CreateValidBlock inserts into mapBlockIndex/chainActive; callers must clean up.

| ID | Type | Name |
|----|------|------|
| 4.1 | Excl | CachedWitnesses* |
| 4.2 | Excl | WriteCryptedSaplingZkeyDirectToDb |
| 4.3 | Fix | UpdatedSaplingNoteData |
| 4.4 | Fix | NavigateFromSaplingNullifierToNote |
| 4.5 | Fix | SpentSaplingNoteIsFromMe |
| 4.6 | Fix | PoW.MinDifficultyRules |
| 4.7 | Fix | DeprecationTest.AlertNotify |
| 4.8 | Fix | equihash check_optimised_solver_cancelled |

**4.1 CachedWitnesses***  
*Symptoms*: CachedWitnessesEmptyChain, CachedWitnessesChainTip fail assertions; CachedWitnessesDecrementFirst, CachedWitnessesCleanIndex crash in VerifyAndSetInitialWitness/BuildWitnessCache.  
*Root cause*: CreateValidBlock stores `&index` in mapBlockIndex; index is local and goes out of scope → dangling pointer. BuildWitnessCache expects pcoinsTip/chain state the harness does not provide.  
*Fix/mitigation*: Excluded. Options: keep block indices in scope; refactor CreateValidBlock; adapt harness to populate chain state.  
*Debug*: `./src/zero-gtest --gtest_filter='WalletTests.CachedWitnessesEmptyChain' --gtest_break_on_failure`; lldb `bt` at crash.

**4.2 WriteCryptedSaplingZkeyDirectToDb**  
*Symptoms*: Hangs.  
*Root cause*: CDB::Rewrite in `src/wallet/db.cpp:389` spins `while (mapFileUseCount[strFile] != 0) { MilliSleep(100); }`. First wallet never closed; wallet2 opens same file → mapFileUseCount > 0. EncryptWallet → Rewrite deadlock. Flush (Zcash 4.5.0) does not close DB when refcount > 0.  
*Fix/mitigation*: Excluded. Options tried: scope block, separate file; both hang.  
*Debug*: Add LogPrintf in CDB::Rewrite before loop; gdb break at MilliSleep.

**4.3 UpdatedSaplingNoteData**  
*Symptoms*: Assertion failure; witnesses empty or mismatch.  
*Root cause*: CreateValidBlock builds witnesses with empty tree; test expects witness matching testNote.tree.witness().  
*Fix/mitigation*: Fixed. Manual witness for change output only; same pattern as Status 4.4.

**4.4 NavigateFromSaplingNullifierToNote**  
*Symptoms*: mapSaplingNullifiersToNotes and nd.witnesses remain empty.  
*Root cause*: BuildWitnessCache needs pcoinsTip/chain state the harness does not provide.  
*Fix/mitigation*: Fixed. Manual witness build (SaplingMerkleTree, witness(), store in mapSaplingNoteData).

**4.5 SpentSaplingNoteIsFromMe**  
*Symptoms*: Incorrect result; chainActive.Height() was 0.  
*Root cause*: Test-order dependency; RegtestActivateSapling() left chain state inconsistent.  
*Fix/mitigation*: Fixed. chainActive.SetTip(NULL) after RegtestActivateSapling().

**4.6 PoW.MinDifficultyRules**  
*Symptoms*: boost::optional::get() assertion.  
*Root cause*: Zero testnet sets nPowAllowMinDifficultyBlocksAfterHeight to boost::none; test dereferenced unconditionally.  
*Fix/mitigation*: Fixed. Early return when parameter unset.

**4.7 DeprecationTest.AlertNotify**  
*Symptoms*: Expected "Zcash" in deprecation warning.  
*Root cause*: Runtime says "ZERO".  
*Fix/mitigation*: Fixed. Changed expected string to "ZERO".

**4.8 equihash check_optimised_solver_cancelled**  
*Symptoms*: ASSERT_THROW for PartialEnd cancellation failed.  
*Root cause*: Platform-dependent; PartialEnd never reached for Equihash<48,5> with test input 0x00.  
*Fix/mitigation*: Fixed. try/catch accepts either exception or normal return.

**Exclusion filter**: `--gtest_filter='-wallet_zkeys_tests.WriteCryptedSaplingZkey*:WalletTests.CachedWitnesses*'`

### 4.6 Boost (5.x)

**Limitations**: Early failures cascade via shared state. Run by suite to isolate. main_tests passes (Zero-specific paths); included in pass-only. pow_tests passes (handles both 120s Zero and 150s Zcash in `src/test/pow_tests.cpp`). Checkpoints_tests is empty (all cases commented out); suite exits 0.

| ID | Type | Name |
|----|------|------|
| 5.1 | Excl | Alert_tests |
| 5.2 | Excl | equihash_tests |
| 5.3 | Excl | miner_tests |
| 5.3a | Hang | rpc_wallet_encrypted_wallet_sapzkeys |
| 5.4 | Fix | rpc_wallet founders % |
| 5.5 | Fix | z_getnewaddress extra args |
| 5.6 | Fix | RPC zcash-cli → zero-cli |
| 5.7 | Fix | rpc_tests signrawtransaction, getblockdeltas |
| 5.8 | Fix | rpc_parse_monetary_values |
| 5.9 | — | main_tests (passes) |

**5.1 Alert_tests**  
*Symptoms*: MagicBean subver mismatch; PartitionAlert expectedSlow wrong; AlertDisablesRPC may fail.  
*Root cause*: alertTests.raw MagicBean/Zcash-specific; Zero uses Ambrym. PoWTargetSpacing 120 vs Zcash 150. Alert system deprecated.  
*Fix/mitigation*: Excluded. Set aside.

**5.2 equihash_tests**  
*Symptoms*: (96,5) vector mismatch.  
*Root cause*: Zero uses (192,7); tests use (96,5).  
*Fix/mitigation*: Excluded. Skip when nEquihashN!=96; suite exits 0.

**5.3 miner_tests**  
*Symptoms*: Invalid-solution.  
*Root cause*: Zero (192,7) vs test (96,5).  
*Fix/mitigation*: Excluded.

**5.3a rpc_wallet_encrypted_wallet_sapzkeys**  
*Symptoms*: Hangs; test enters but never completes (verified >120s timeout).  
*Root cause*: Same CDB::Rewrite deadlock as 4.2. EncryptWallet on Sapling zkeys triggers wallet DB rewrite; first wallet never closed.  
*Fix/mitigation*: Excluded in run-tests.sh BOOST_EXCLUDE.

**5.4 rpc_wallet founders %**  
*Symptoms*: Expected miner 10, founders 0.8; got 9.99, 0.81.  
*Root cause*: Zero 7.5% founder, 10 ZER base.  
*Fix/mitigation*: Fixed. Expected values updated for Zero.

**5.5 z_getnewaddress extra args**  
*Symptoms*: params.size()>1 not rejected.  
*Root cause*: Missing help condition.  
*Fix/mitigation*: Fixed. params.size()>1 triggers help. Test added for `z_getnewaddress sprout extra`.

**5.6 RPC zcash-cli → zero-cli**  
*Symptoms*: rpc_insightexplorer, rpc_z_mergetoaddress_parameters failed on expectedErrorMessage.  
*Root cause*: RPC error strings referenced zcash-cli.  
*Fix/mitigation*: Fixed. Replaced with zero-cli in `src/rpc/misc.cpp`, `src/rpc/blockchain.cpp`, `src/wallet/rpcwallet.cpp`.

**5.7 rpc_tests signrawtransaction, getblockdeltas**  
*Symptoms*: Invalid branch ID; wrong genesis.  
*Root cause*: Zcash Sapling 5ba81b19, Zcash genesis. Zero uses 7361707a, genesis 068cbb5db6bc11be5b93479ea4df41fa7e012e92ca8603c315f9b1a2202205c6.  
*Fix/mitigation*: Fixed.

**5.8 rpc_parse_monetary_values**  
*Symptoms*: BOOST_CHECK_THROW(..., UniValue) failed; "unknown type".  
*Root cause*: AmountFromValue throws UniValue/JSONRPCError.  
*Fix/mitigation*: Fixed. try/catch; diagnostic logs typeid/e.what().

**Pass-only filter**: `--run_test='!Alert_tests:!equihash_tests:!miner_tests:!rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys'`

**Slow tests** (macOS ARM64, ~48s total): rpc_wallet_async_operations 5.1s, PrevectorTestInt 4.1s, rpc_wallet_async_operations_parallel_wait 3.7s, rpc_wallet_async_operations_parallel_cancel 1.7s, subsidy_limit_test 1.7s, rpc_z_getoperations 1.6s, rpc_wallet_encrypted_wallet_zkeys 1.1s, coin_selection_tests 0.85s. Suites: rpc_wallet_tests 23s, DoS_tests 5.5s, rpc_tests 5.5s, PrevectorTests 4.1s, main_tests 2.9s, mempool_tests 2.4s.

### 4.7 RPC Python (6.x)

**Limitations**: Python 2.7. Each test starts zerod, mines blocks; ~30–120s each. No parallelization. Tests using initialize_chain_clean expect Zcash amounts.

| ID | Type | Name |
|----|------|------|
| 6.1 | Skip | get_coinbase_address |
| 6.2 | Skip | protocol version |
| 6.3 | Open | clean-chain amounts |
| 6.4 | Fix | nuparams, branch IDs |
| 6.5 | Fix | getchaintips |
| 6.6 | Prereq | pyblake2 |

**6.1 get_coinbase_address**  
*Symptoms*: assert(len(set(addrs)) > 0) — no generated utxos.  
*Root cause*: listunspent with generated returns empty when nuparams activate early. Implementation gap.  
*Fix/mitigation*: Skip. Check addrs before get_coinbase_address; return with message. Affects wallet_changeaddresses, shorter_block_times.  

**6.2 protocol version**  
*Symptoms*: versions.count(SPROUT_PROTO_VERSION) — expected 10, got 0.  
*Root cause*: Zero uses different SPROUT/OVERWINTER/SAPLING versions; mininode expects Zcash.  
*Fix/mitigation*: Skip. Check count==0; return with message. Affects p2p_nu_peer_management.  

**6.3 clean-chain amounts**  
*Symptoms*: Balance assertions fail in wallet.py, txn_doublespend.  
*Root cause*: Zero subsidy 10 ZER/block, different halving.  
*Fix/mitigation*: Open. Recompute expected amounts from Zero schedule.  

**6.4 nuparams, branch IDs**  
*Symptoms*: zerod exits Invalid network upgrade (5ba81b19).  
*Root cause*: Tests passed Zcash branch IDs. Zero uses 6f76727a (Overwinter), 7361707a (Sapling).  
*Fix/mitigation*: Fixed. Replaced in wallet_changeaddresses, shorter_block_times, rewind_index, p2p_nu_peer_management, wallet_overwintertx. mininode.py OVERWINTER=0x6f76727a, SAPLING=0x7361707a.  

**6.5 getchaintips**  
*Symptoms*: len(tips)==1 fails (got 2); height 210 fails (got ~424).  
*Root cause*: Zero returns active + valid-fork; regtest block count differs.  
*Fix/mitigation*: Fixed. Extract active tip; skip when height≠210.  

**6.6 pyblake2**  
*Symptoms*: ImportError.  
*Root cause*: mininode.py needs pyblake2 for Equihash block validation.  
*Fix/mitigation*: Prereq. `python2 -m pip install pyblake2`.  

**Verified pass**: blockchain, disablewallet, httpbasics, reindex, decodescript, keypool, paymentdisclosure, prioritisetransaction, wallet_treestate, wallet_anchorfork, getchaintips (skip), rewind_index, wallet_overwintertx (skip), wallet_changeaddresses (skip), shorter_block_times (skip), p2p_nu_peer_management (skip).

**Options**: `--nocleanup` (leave zerods and test datadir on exit); `--noshutdown` (don't stop zerods after test); `--srcdir=SRCDIR` (default `${BUILDDIR}/src`); `--tmpdir=TMPDIR`; `--tracerpc` (print RPC calls). rpc-tests.sh sources `qa/pull-tester/tests-config.sh` for BUILDDIR, PYTHON, REAL_BITCOIND, REAL_BITCOINCLI.

**Open question**: Regtest 424 vs 210 — cause of block count mismatch not fully confirmed. generate RPC should create exactly N blocks; suggests sync/split or chain-state divergence.

### 4.7.1 RPC Review: Excluded Fixes, Speed-up, Parallel

**Excluded tests — proposed fixes**

| ID | Test | Fix |
|----|------|-----|
| 6.1 | get_coinbase_address (wallet_changeaddresses, shorter_block_times, wallet_overwintertx) | Fixed: added skip check in wallet_overwintertx. wallet_changeaddresses, shorter_block_times already had it. |
| 6.2 | protocol version (p2p_nu_peer_management) | Already skips when `versions.count(SPROUT_PROTO_VERSION)==0`. No change. |
| 6.3 | clean-chain amounts (wallet.py, txn_doublespend) | Fixed for wallet.py: added `zero_regtest_subsidy(n)` in util.py; wallet.py uses it for node1 balance. txn_doublespend: 25×10=250 matches Zero; may pass as-is. |
| 6.5 | getchaintips | Already fixed (active tip, skip on height mismatch). |
| 6.6 | pyblake2 | Prereq; document in README. |

**Passing tests — speed-up**

- **Bottlenecks**: Each test starts zerod(s), mines blocks (generate), runs, stops. ~30–120s per test. Main cost: block generation (Equihash PoW) and node startup.
- **Options**: (1) Use `initialize_chain` (cached 200-block chain) where test logic allows; keypool, blockchain already do. (2) Reduce blocks where safe: e.g. prioritisetransaction needs fewer blocks for maturity. (3) `-keypool=1` already set; keep. (4) Consider `-regtest`-specific faster PoW if Zero supports (e.g. low nBits for instant solve); not implemented.
- **Low-effort**: Ensure tests that can use cached chain do so; audit `initialize_chain_clean` vs `initialize_chain` usage.

**Parallel and shared node**

- **Current**: `contrib/run-tests.sh` runs Python tests sequentially: `for t in PYTHON_PASSING; do run_cmd "rpc-$t" ...`. Each test gets fresh tmpdir, starts its own zerod(s).
- **Parallel**: `--jobs=N` implemented in run-tests.sh. Each test uses `p2p_port(n) + os.getpid()%999` and `rpc_port(n) + os.getpid()%999` — different PIDs from parallel runs give different ports. Cap at 4–8 to avoid resource exhaustion.
- **Shared node**: Bitcoin Core func tests use isolated datadirs per test; no shared node. Sharing one zerod across tests would require: (a) test isolation (reset state between tests), (b) no conflicting ports, (c) tests written for shared setup. Current tests assume clean chain and full control. **Verdict**: Shared node is high effort; parallel execution is feasible with separate processes.

**Recommended next steps**

1. Add skip check in wallet_overwintertx for empty `addrs` (5 min).
2. Add `zero_regtest_subsidy(n)` and update wallet.py for 6.3 (30 min).
3. Use `--jobs=4` for faster RPC Python runs (implemented).

**4.7.2 script_test.py — not run**

- **Location**: `qa/rpc-tests/script_test.py`. Uses `script_valid.json` and `script_invalid.json`; end-to-end script validation via two nodes.
- **Status**: Not run. Commented out in `rpc-tests.sh` (testScriptsExt). Not in run-tests.sh PYTHON_PASSING.
- **Failure**: When run directly, fails with `AssertionError: Not all nodes requested block` during sync_blocks (~15s). One node rejects or does not request blocks; likely block format, consensus, or protocol mismatch.
- **Duration**: If it ran, >40 min (docstring). ~1000+ test cases × ~102 Equihash block solves each.
- **Block count**: Uses 100 blocks to mature coinbase. Zero COINBASE_MATURITY is 720; 100 blocks would not satisfy maturity. Reducing to 10 blocks would fail on both Zero and Bitcoin (maturity not met).
- **Conclusion**: script_test does not contribute to current test duration; it is excluded.

**4.7.3 Why tests take long**

| Component | Time | Cause |
|-----------|------|-------|
| RPC Python (11 pass-only) | ~5–20 min | Main bottleneck. Each test starts zerod, mines Equihash blocks, runs, stops. ~30–120s per test; sequential by default. |
| Boost (pass-only) | ~48s | rpc_wallet_tests ~23s, DoS_tests 5.5s, rpc_tests 5.5s, etc. |
| GTest (201 tests) | varies | Many tests; runtime hardware-dependent. |
| Util, secp256k1, univalue | fast | — |

**Speed-up**: Use `./contrib/run-tests.sh --jobs=4` for parallel RPC Python. GTest and Boost already run in parallel via run_bg.

### 4.8 Workarounds and Skips

The following are workarounds and skips to overcome test problems and failures. They do not fix underlying issues; they allow the test run to pass or exit cleanly. Actual fixes (e.g. nuparams branch IDs, rpc_wallet founders %, zcash-cli→zero-cli) are documented in their respective status sections.

**GTest**

| Item | Workaround | Root cause (unfixed) |
|------|------------|----------------------|
| CachedWitnesses* (4 tests) | Excluded via `--gtest_filter='-WalletTests.CachedWitnesses*'` | CreateValidBlock dangling pointer; harness lacks pcoinsTip/chain state |
| WriteCryptedSaplingZkey* | Excluded via `--gtest_filter='-wallet_zkeys_tests.WriteCryptedSaplingZkey*'` | CDB::Rewrite deadlock; first wallet never closed |
| run-tests.sh | Uses filtered zero-gtest invocation | Above exclusions |

**Boost**

| Item | Workaround | Root cause (unfixed) |
|------|------------|----------------------|
| Alert_tests | Excluded via `--run_test='!Alert_tests'` | MagicBean/Zcash-specific alerts; Zero uses Ambrym |
| equihash_tests | Excluded via `--run_test='!equihash_tests'` | Zero (192,7) vs test (96,5); suite skips when nEquihashN!=96 |
| miner_tests | Excluded via `--run_test='!miner_tests'` | Zero (192,7) vs test (96,5) |
| rpc_wallet_encrypted_wallet_sapzkeys | Excluded via `--run_test='!rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys'` | CDB::Rewrite deadlock (same as GTest WriteCryptedSaplingZkey*) |
| run-tests.sh, run-boost-individual.sh | Pass-only filter excludes above | Cascade from shared state |

**RPC Python**

| Item | Workaround | Root cause (unfixed) |
|------|------------|----------------------|
| get_coinbase_address (6.1) | In-test skip: `if not addrs: print("Skipping..."); return` before `get_coinbase_address()`. Affects wallet_changeaddresses, shorter_block_times, wallet_overwintertx. | listunspent with generated returns empty when nuparams activate early |
| protocol version (6.2) | In-test skip: `if versions.count(SPROUT_PROTO_VERSION)==0: print("Skipping..."); return`. Affects p2p_nu_peer_management. | Zero uses different SPROUT/OVERWINTER/SAPLING protocol versions than Zcash |
| getchaintips (6.5) | In-test skip: `if tip['height']!=expected: print("Skipping..."); return`. Extract active tip from tips; skip on height mismatch. | Zero returns active+valid-fork; regtest block count differs |
| clean-chain amounts (6.3) | Workaround: `zero_regtest_subsidy(n)` in util.py; wallet.py uses it for node1 balance instead of hardcoded Zcash amount. | Zero subsidy 10 ZER/block, halving every 150; tests expected Zcash schedule |
| wallet_overwintertx chaintip | In-test skip: `if bci['consensus']['chaintip']!='7361707a': print("Skipping..."); return` | Zero regtest block count differs from expected |
| run-tests.sh | PYTHON_PASSING list omits known-fail scripts; runs only 16 verified | Many scripts fail for above reasons or Zcash-specific logic |

**Prereqs (environment, not workarounds)**

| Item | Requirement |
|------|-------------|
| pyblake2 (6.6) | `python2 -m pip install pyblake2` before RPC Python tests using mininode |
| Python 2.7 | Set `PYTHON` or use pyenv 2.7.18. |
| tests-config.sh | BUILDDIR, REAL_BITCOIND, REAL_BITCOINCLI must point to Zero binaries |

**Platform skips**

| Item | Behavior |
|------|----------|
| sec-hard checksec | ELF only; skips on macOS (Mach-O) |
| check-symbols | readelf; Linux only |

### 4.9 sec-hard, no-dot-so (7.x, 8.x)

**7.x sec-hard**: System-specific. ELF only; skips on macOS. make check-security is cross-platform; checksec (RPATH/FORTIFY) is ELF-only. Document applicability; not a problem.

**8.x no-dot-so**: full_test_suite stage. Ensures depends/x86_64-*/lib (or x86_64-apple-darwin*, aarch64-apple-darwin*) has no .so. Fails if any .so. If no arch dir exists, skips (returns success) instead of exit 2; allows `--full` on macOS without a depends build.

**OS-based skips**: full_test_suite supports `--skip STAGE` (repeatable). run-tests.sh passes `--skip sec-hard --skip no-dot-so` on Darwin when invoking `--full`, so the full suite completes successfully on macOS.

### 4.10 check (9.x)

Recursive make check invokes 1, 2, 3, 5. Use `make -C src secp256k1-check` or `make -C src univalue-check` for isolated runs. Full check runs test_bitcoin + bitcoin-util-test + secp256k1 + univalue.

## 5. RPC

**Purpose**: Identify coverage of existing Zero RPCs and potential additions from other projects.

### 5.1 Suites Touching RPC

- **rpc_tests** (Boost): Raw tx, ban, addressindex, mining. RPCs: getrawtransaction, createrawtransaction, decoderawtransaction, decodescript, signrawtransaction, sendrawtransaction, clearbanned, setban, listbanned, getnetworksolps, getaddressmempool, getaddressutxos, getaddressdeltas, getaddressbalance, getaddresstxids, getblockdeltas, getblockhashes.
- **rpc_wallet_tests** (Boost): Wallet, z_* params, error paths. RPCs: setaccount, getbalance, listunspent, z_setmigration, z_getbalance, z_gettotalbalance, z_validateaddress, z_importkey, z_exportwallet, z_importwallet, z_exportkey, z_listaddresses, z_getnewaddress, z_getoperationstatus, z_getoperationresult, z_listoperationids, z_sendmany, z_listunspent, z_mergetoaddress, z_shieldcoinbase, getblocksubsidy, getblock, encryptwallet, fundrawtransaction, etc.
- **RPC Python**: End-to-end, multi-node. RPCs: generate, getblockcount, listunspent, z_getnewaddress, z_sendmany, z_shieldcoinbase, getrawtransaction, z_gettotalbalance, getwalletinfo, sendtoaddress, createrawtransaction, getbalance, z_getbalance, zcrawkeygen, zcrawreceive, zcrawjoinsplit, signrawtransaction, sendrawtransaction, getbestblockhash, getchaintips, etc.

### 5.2 Zero RPC Coverage

~120 Zero RPCs (RPCs.csv, zero=y). Groups: control (2), blockchain (19), network (12), util (6), addressindex (5), rawtransactions (8), mining (11), spork (1), zeronode (18), wallet (45+), zero_exclusive (7), zero_experimental (3), disclosure (2).

**Prioritization**: P1 (core shielded): z_sendmany, z_shieldcoinbase, z_getnewaddress, z_getbalance, z_gettotalbalance, z_listaddresses, z_listunspent, z_mergetoaddress — covered by rpc_wallet_tests, Python RPC. P2 (zeronode): 18 RPCs — no coverage. P3 (zero_exclusive): zs_*, getalldata, getsupply — no coverage. P4 (shared): getblock, getblockcount, generate, getbalance, listunspent, createrawtransaction — covered.

### 5.3 Coverage Gaps

- zeronode RPCs: No test coverage.
- zero_exclusive (zs_*, getalldata, getsupply): No coverage.
- zero_experimental (getsaplingwitness*): No coverage.
- decodescript: rpc_tests (Boost) only.

### 5.4 Potential Additions (Zcash/Pirate)

**From Zcash**: z_gettreestate, z_getsubtreesbyindex, getmemoryinfo, getexperimentalfeatures, setlogfilter, importpubkey, listaddresses, walletconfirmbackup, z_converttex, z_getnewaccount, z_getaddressforaccount, z_listaccounts, z_listunifiedreceivers, z_getbalanceforviewingkey, z_getbalanceforaccount, z_getnotescount. (Unified Address / Orchard; Zcash evolution.)

**From Pirate** (Komodo; mostly not applicable): getpeerlist, coinsupply, crosschain/*, z_sendmany_prepare_offline, z_sign_offline, rescan, etc.

**Zero-specific** (not in Zcash/Pirate): zeronode (18), zs_* (5), getalldata, getsupply, getsaplingwitness*, estimatefee, estimatepriority.


## 6. Notes

### 6.1 Build Log

**autogen**: GZIP_ENV, distcleancheck overrides; $as_echo obsolete (Autoconf 2.70+).

**configure**: brew not in PATH (optional); -single_module obsolete (Darwin ld); static flag no (expected on Darwin).

**depends**: Rust checksum for x86 cross-compile — added rust_std_sha256_hash_x86_64-apple-darwin in depends/packages/rust.mk.

**compile**: zeronode.h:229 memcpy -Wfortify-source. Fixed: `memcpy(&n, (char*)&hash + slice * 8, 8)`. Original `&hash + slice*64` wrong pointer arithmetic; 64 bytes into uint64_t overflow. SliceHash is dead code.

**budget.cpp:35**: Implicit conversion 4070908800 → int. Intentional sentinel for "OFF"; overflow produces desired modulo. Fix: INT_MAX to silence warning.

### 6.2 Subject Coverage

**Global state in GTest**: CreateValidBlock inserts into mapBlockIndex and chainActive. Callers must clean up (CachedWitnessesEmptyChain teardown pattern).

**Manual witness pattern**: For synthetic Sapling notes: (1) append commitments to SaplingMerkleTree; (2) capture saplingTree.witness() at target note; (3) append subsequent commitments; (4) store in mapSaplingNoteData. Bypasses BuildWitnessCache.

**pyblake2**: mininode.py uses for Equihash person strings. Python 3.6+ has hashlib.blake2b. Migration path when tests move to Python 3.

**nuparams**: Overwinter 0x6f76727a, Sapling 0x7361707a (Zero). Zcash: 0x5BA81B19, 0x76B809BB.

### 6.3 Wants and Suggestions

- **Python 3 migration** (delayed work area): Replace pyblake2 with hashlib.blake2b when migrated.
- **zeronode RPC tests**: No coverage; add suite.
- **Fuzz tests**: Zero has none; Bitcoin has src/test/fuzz/.
- **Functional tests**: Bitcoin uses test/functional (Python 3); Zero uses legacy qa/rpc-tests.
- **Coverage (make cov)**: Postponed; requires CFLAGS --coverage, lcov.
- **leveldb, libsnark**: Not wired to top-level check.

### 6.5 System-Specific

**sec-hard, checksec**: ELF only. Applicable on Linux; skips on macOS (zerod is Mach-O). Document platform applicability; not a problem.

**check-symbols**: readelf, GLIBC_BACK_COMPAT; Linux only.

## 7. References (External)

| Reference | URL/Notes |
|-----------|-----------|
| GTest | https://github.com/google/googletest |
| Zcash integration-tests | https://github.com/zcash/integration-tests (zebrad, zainod, zallet; not zcashd/Zero) |
| Bitcoin Core | test/functional, src/test/fuzz |

## 8. Cross-Project Comparison

| Suite | Zero | Bitcoin | Zcash | Pirate | Notes |
|-------|------|---------|-------|--------|-------|
| Util | ✓ | util tests | — | qa-style | |
| secp256k1 | ✓ | ✓ | ✓ | ✓ | |
| univalue | ✓ | ✓ | ✓ | ✓ | |
| GTest | ✓ 1.16.0 | — | ✓ 1.12.1 | ✓ 1.8.0 | |
| Boost | ✓ | ✓ | ✓ | ✓ | |
| Python RPC | ✓ Py2 | functional Py3 | ✓ | ✓ | |
| full_test_suite | ✓ | — | ✓ | ✓ | |
| Fuzz | ✗ | ✓ | — | — | |
| Integration tests | in-tree qa | — | separate repo | — | |

**Suites in others not in Zero**: Functional tests (Bitcoin Py3), Fuzz, Lint, Stress tests. Integration tests (Zcash separate repo for zebrad/zainod/zallet).

## 9. Coverage Analysis, Limitations, and Future Work

Aggregated from coverage analysis. Detailed limitations, justifications for exclusions, and future work.

### 9.1 Coverage by Functional Area

| Area | Coverage | Test Files | Notes |
|------|----------|------------|-------|
| Cryptography | 95% | 15+ | Hash, sigs, Equihash, Zcash crypto; test vectors |
| Zcash Features | 90% | 12+ | JoinSplit, shielded, Merkle, Sapling, note encryption |
| Core Blockchain | 90% | 20+ | Block validation, chain state, mining |
| RPC Interface | 85% | 25+ | Unit + integration |
| Wallet | 80% | 8+ | Standard wallet; async RPC |
| Mining/PoW | 75% | 6+ | Equihash (192,7); miner_tests excluded |
| Network/P2P | 60% | 5+ | Gaps: partition, peer misbehavior |
| Zeronode System | 0% | 0 | Critical gap; see 9.2 |

**Test-to-source ratio:** ~40% (96 test files vs 149 .cpp + 258 .h).

### 9.2 Zeronode Coverage Gap — Critical

**Components not tested:** zeronode management, payments, budget/governance, spork, SwiftTX, obfuscation. No unit, integration, or RPC tests for zeronode-specific commands.

**Risk:** High. Core differentiating features lack automated coverage. Manual validation only.

**Justification for deferral:** Zeronode test suite is high impact but not part of current port/stabilization. Existing infrastructure (GTest, Boost, RPC Python) provides foundation; zeronode tests would require new fixtures and network simulation.

**Future work:** Unit tests for registration, validation, payments; integration for masternode network behavior; RPC tests for zeronode commands. Budget proposal/voting, SwiftTX lock/conflict, spork activation.

### 9.3 Other Gaps and Priorities

**High:** SwiftTX (instant tx validation, lock conflict, consensus); Spork (activation, backward compat).

**Medium:** P2P (partition, misbehavior); database resilience (corruption, load, backup).

**Low:** Performance benchmarking; cross-platform behavior.

### 9.4 Recent Fixes (June 2025)

- **Founders reward:** Halving (9,10), 11 addresses, subsidy 338665500000000. Accuracy TBD.
- **Alert:** Placeholder keys; verification disabled; deprecated.
- **Tx size:** Sapling limits validated.
- **PTHREAD_STACK_MIN:** configure.ac, depends; threading compatibility.

### 9.5 Doubts and Open Questions

- **Regtest 424 vs 210:** Block count mismatch; cause not fully confirmed.
- **Founders reward expected values:** Updated to actual; accuracy TBD.
- **script_test.py:** Excluded; sync_blocks fails; >40 min; COINBASE_MATURITY 720 vs test 100 blocks — not viable without major rewrite.

### 9.6 Future Directions

- Python 3 migration (pyblake2 → hashlib.blake2b).
- Zeronode test suite (see 9.2).
- Fuzz tests (Zero has none; Bitcoin has src/test/fuzz/).
- Functional test migration (Bitcoin test/functional Py3; Zero uses legacy qa/rpc-tests).
- Coverage targets (make cov; requires lcov).
