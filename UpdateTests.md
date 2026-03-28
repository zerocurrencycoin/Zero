# UpdateTests

Maintainer test planning: **why** suites are excluded or skipped, **what** “green” really means, **backlog**, CSV rules, rescan/reindex notes. Not a runbook.

**[TEST_ZERO.md](TEST_ZERO.md)** owns **how to run**: harness roles, **`contrib/run-tests.sh`** modes (including **`--jobs`** scope: Tier A RPC only, serial default; parallel best-effort—see **TEST_ZERO.md** Reference → **Parallel Tier A**), pass-only filter strings, Tier A allowlist (mirror of **`PYTHON_PASSING`**), **`full_test_suite.py`** behavior, extended-RPC risks. **Tier B/C basenames** live only in **`qa/pull-tester/rpc-tests.sh`** (**`testScripts`**, **`testScriptsExt`**). **Sibling maintainer docs:** **UpdateZero.md** §1.3.

**Consolidation:** Old **§** numbering is gone. Exclusion write-ups, gap table, prioritized phases, CSV rules, rescan inventory, and debug notes below were **not** dropped—**TEST_ZERO.md** never carried that material.

**GTest** pin: **BUILD_ZERO.md** §4.1 (`googletest.mk`, C++14). **Python / platform:** **TEST_ZERO.md**, **BUILD_ZERO.md** §1.1. **Infra:** no in-tree fuzz; legacy **`qa/rpc-tests`**.

## Exclusions and root causes

Fork-level picture: **CachedWitnesses\*** excluded (harness / **`EXPECT_DEATH`**). **CDB::Rewrite** hang → **`WriteCryptedSaplingZkey*`** (GTest) and **`rpc_wallet_encrypted_wallet_sapzkeys`** (Boost) excluded. **`run-tests.sh --full`** skips **sec-hard** / **no-dot-so** on Darwin (ELF / depends layout): **TEST_ZERO.md** Reference → **`full_test_suite.py`**.

Exact counts, Tier A names, and filter strings drift—**[TEST_ZERO.md](TEST_ZERO.md)** is authoritative. Below: **IDs** for triage. **RPC Python** explains when **exit 0** is still weak coverage.

### Util through univalue

No known fork-specific failures.

### GTest (suite 4.x)

**Limitations**: Harness lacks pcoinsTip, ReadBlockFromDisk; BuildWitnessCache assumes disk-backed chain. CreateValidBlock inserts into mapBlockIndex/chainActive; callers must clean up.

| ID | Type | Name |
|----|------|------|
| 4.1 | Excl | CachedWitnesses* (→ Debug notes) |
| 4.2 | Excl | WriteCryptedSaplingZkeyDirectToDb (→ Debug notes) |
| 4.3 | Fix | UpdatedSaplingNoteData |
| 4.4 | Fix | NavigateFromSaplingNullifierToNote |
| 4.5 | Fix | SpentSaplingNoteIsFromMe |
| 4.6 | Fix | PoW.MinDifficultyRules |
| 4.7 | Fix | DeprecationTest.AlertNotify |
| 4.8 | Fix | equihash check_optimised_solver_cancelled |

**4.1 CachedWitnesses***  
*Symptoms*: CachedWitnessesEmptyChain, CachedWitnessesChainTip fail assertions; CachedWitnessesDecrementFirst, CachedWitnessesCleanIndex crash in VerifyAndSetInitialWitness/BuildWitnessCache.  
*Root cause*: CreateValidBlock stores `&index` in mapBlockIndex; index is local and goes out of scope → dangling pointer. BuildWitnessCache expects pcoinsTip/chain state the harness does not provide.  
*Fix/mitigation*: Excluded. **Partial fix applied**: (1) CachedWitnessesChainTip and CachedWitnessesDecrementFirst keep index1 in outer scope (no dangling pointer crash). (2) `wallet.cpp` VerifyAndSetInitialWitness: when pcoinsTip is null but pblockIn is provided, continue to build witnesses from block (test-harness path). (3) CachedWitnessesEmptyChain: index.nHeight = 0 set for chainActive consistency.  
*Still failing*: CachedWitnessesEmptyChain fails at first EXPECT_FALSE (witnesses present before AddToWallet) or at EXPECT_DEATH (DecrementNoteWitnesses has no assert in current code). Env-dependent: some runs show witnesses pre-add (test-order pollution?). EXPECT_DEATH expects `.*nWitnessCacheSize > 0.*` but DecrementNoteWitnesses does not assert.  
*Next steps*: (1) Isolate test order: run CachedWitnessesEmptyChain first in fresh process; verify BuildWitnessCache path. (2) Replace EXPECT_DEATH with benign check or skip until #1302 adds assert. (3) Manual witness build (4.3/4.4 pattern) as fallback if pblockIn path insufficient.  
*Debug*: `./src/zero-gtest --gtest_filter='WalletTests.CachedWitnessesEmptyChain' --gtest_break_on_failure`; lldb `bt` at crash. **Debug notes → CachedWitnesses\***.

**4.2 WriteCryptedSaplingZkeyDirectToDb**  
*Symptoms*: Hangs.  
*Root cause*: CDB::Rewrite in `src/wallet/db.cpp:389` spins `while (mapFileUseCount[strFile] != 0) { MilliSleep(100); }`. First wallet never closed; wallet2 opens same file → mapFileUseCount > 0. EncryptWallet → Rewrite deadlock. Flush (Zcash 4.5.0) does not close DB when refcount > 0. (libdb: §6.2.)  
*Fix/mitigation*: Excluded. Options tried: scope block, separate file; both hang.  
*Next steps*: Ensure wallet closed before encrypt/rewrite; or add test-only path that avoids rewrite loop.  
*Debug*: Uncomment LogPrintf in `wallet/db.cpp` CDB::Rewrite; gdb break at MilliSleep. **Debug notes → CDB::Rewrite**.

**4.3–4.8 (fixed):** manual Sapling witnesses / nullifier navigation / chain tip cleanup after **`RegtestActivateSapling`** / testnet min-difficulty optional / **"ZERO"** deprecation string / Equihash cancellation try-catch.

**Pass-only / exclusion filter strings:** **TEST_ZERO.md** (same for GTest below).

### Boost (suite 5.x)

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
*Root cause*: alertTests.raw MagicBean/Zcash-specific; Zero uses Gaua. PoWTargetSpacing 120 vs Zcash 150. Alert system deprecated.  
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
*Root cause*: Same CDB::Rewrite deadlock as 4.2. EncryptWallet on Sapling zkeys triggers wallet DB rewrite; first wallet never closed. (libdb: §6.2.)  
*Fix/mitigation*: Excluded in run-tests.sh BOOST_EXCLUDE. **Debug notes → CDB::Rewrite**.

**5.4–5.8 (fixed):** founders split / **`z_getnewaddress`** args / **`zcash-cli`→`zero-cli`** strings / branch IDs + genesis in **`rpc_tests`** / **`rpc_parse_monetary_values`** exception handling — aligned to Zero params and branding.

**Slow tests (Boost, indicative):** **`rpc_wallet_tests`** dominates; several single cases exceed ~1s (async wallet RPC, **`PrevectorTests`**, **`subsidy_limit_test`**, …).

### RPC Python

**Env, flags, Tier A list, maturity (720) taxonomy:** **TEST_ZERO.md**. **Cost:** each script spawns **`zerod`**, mines Equihash, tears down. **`initialize_chain_clean`** paths use **`zero_regtest_subsidy`** where adapted.

**Coverage honesty:** skips for coinbase maturity, peers, clean-chain balance (6.1–6.3) and omission of failing scripts from **`PYTHON_PASSING`** mean **exit 0 ≠ full scenario coverage**. Treat as **not run** for coverage accounting when the skip or omission hides the assertion. **6.5** was historical tip-shape issues; main-path **`getchaintips`** fixes are in-tree (**TEST_ZERO.md** changelog).

| ID | Type | Name |
|----|------|------|
| 6.1 | Skip | get_coinbase_address |
| 6.2 | Skip | protocol version / peers |
| 6.3 | Skip | clean-chain amounts (→ Debug notes) |
| 6.4 | Fix | nuparams, branch IDs |
| 6.5 | Fix | getchaintips (split topology, bootstrap, branch length) |
| 6.6 | Prereq | pyblake2 |
| 6.7 | Open | Parallel Tier A (**`--jobs>1`**) — hang under load |

**6.1 get_coinbase_address**  
*Symptoms*: assert(len(set(addrs)) > 0) — no generated utxos.  
*Root cause*: Zero COINBASE_MATURITY=720. listunspent only returns coinbase after 720 confirmations.
Tests generating <720 blocks get no mature coinbase.  
*Fix/mitigation*: Skip via `ensure_coinbase_utxos()`. Affects wallet_changeaddresses, shorter_block_times, wallet_overwintertx, rescan_import. `ZERO_MINE_COINBASE=1` mines 1000 blocks when needed (slow; not used in main run). `has_coinbase_utxos()`, `coinbase_diagnostic()` for skip messages.  

**6.2 protocol version / peers**  
*Symptoms*: (historical) no peers; wrong **`version`** counts.  
*Root cause*: Regtest **network magic** in **`mininode.py`** must match Zero **`pchMessageStart`**; **`NodeConnCB.on_version`** must not cap **`ver_send`** at Sprout (170002). **`p2p_nu_peer_management`** expects **MIN_PEER_PROTO_VERSION** (170007) reject for 170006; Zero does not mass-disconnect 170007/008/009 at NU heights like older Zcash.  
*Fix/mitigation*: **`mininode.py`** magic + **`ver_send`** fix; test rewritten for Zero policy.  

**6.3 clean-chain amounts**  
*Symptoms*: Balance assertions fail in wallet.py, txn_doublespend.  
*Root cause*: Zero subsidy 10 ZER/block, halving every 150. Node0 block 5 reward not maturing (~19 vs 29).  
*Fix/mitigation*: wallet.py skips when node0 balance != 29. `zero_regtest_subsidy(n)` in util.py for node1. **Debug notes → wallet.py node0 balance**.  

**6.4 nuparams, branch IDs**  
*Symptoms*: zerod exits Invalid network upgrade (5ba81b19).  
*Root cause*: Tests passed Zcash branch IDs. Zero uses 6f76727a (Overwinter), 7361707a (Sapling).  
*Fix/mitigation*: Fixed. Replaced in wallet_changeaddresses, shorter_block_times, rewind_index, p2p_nu_peer_management, wallet_overwintertx. mininode.py OVERWINTER=0x6f76727a, SAPLING=0x7361707a. **`wallet_overwintertx`:** Blossom **`-nuparams`** set **above** the tip after **720**-maturity mining; dynamic **`createrawtransaction`** expiry assertion; mine to **`upgrades['2bb40e60'].activationheight`** before post-Blossom checks.  

**6.5 getchaintips**  
*Symptoms*: (historical) wrong tips after join; **`join_network`** re-mined unnecessarily; fork assertions saw **equal** heights (no real split).  
*Root cause*: (1) **`setup_network(split=True)`** must connect **only** **0–1** and **2–3**—extra edges (**0–2**, **1–2**) bridge the partition. (2) Bootstrap height and **`join_network`** must avoid redundant mining.  
*Fix/mitigation*: **`getchaintips.py`** — split-only wiring; **`CHAIN_BOOTSTRAP`** (**30**) with guard **`getblockcount() < CHAIN_BOOTSTRAP`** before initial mine; after join assert active height = long chain; **`expected_branchlen`** vs **`CHAIN_BOOTSTRAP`**; accept **2** tips (**`valid-fork`** / **`valid-headers`**) or **1** active-only tip. **TEST_ZERO.md** (Harness changelog, RPC harness).  

**6.6 pyblake2**  
*Symptoms*: ImportError.  
*Root cause*: **`mininode.py`** tries **`pyblake2`** then **`hashlib.blake2b`**.  
*Fix/mitigation*: **TEST_ZERO.md** prerequisites.

**6.7 Parallel Tier A (`--jobs>1`)**  
*Symptoms*: **`./contrib/run-tests.sh --jobs=N`** can stall (e.g. **`paymentdisclosure`** hung at script start with **`N=4`** on macOS).  
*Root cause*: Many concurrent **`zerod`** processes; resource contention. (Separate bug, **fixed**: **`$(run_bg …)`** subshell caused immediate **`wait`** failure and false **`FAIL`** while logs showed pass—**`BG_LAST_PID`** in **`run-tests.sh`**.)  
*Fix/mitigation*: Serial (**`N=1`**) is the gate. Scope/reliability: **TEST_ZERO.md** → **Parallel Tier A**. **Open:** minimal repro, lower **`N`**, or exclude conflict-prone scripts from the parallel pool.

**script_test.py:** Commented out in **`testScriptsExt`**; fails in **`sync_blocks`** if run — **TEST_ZERO.md** (extended triage).

## Harness and database notes

### GTest / wallet harness patterns

**Global state:** **`CreateValidBlock`** mutates **`mapBlockIndex`** / **`chainActive`** — teardown must restore.

**Manual Sapling witness:** append commitments to **`SaplingMerkleTree`** → capture **`witness()`** at target note → append more → store in **`mapSaplingNoteData`** (bypasses **`BuildWitnessCache`** when pcoinsTip path is absent).

**Branch IDs (Zero regtest):** Overwinter **`0x6f76727a`**, Sapling **`0x7361707a`** (Zcash values differ — see **RPC Python** / fixed scripts above).

### Berkeley DB (wallet)

**Scope:** BDB (**`depends/packages/bdb.mk`**, 6.2.x) **only** for **`wallet.dat`**. LevelDB elsewhere (txindex, spork, etc.).

**Code:** **`wallet/db.*`**, **`wallet/walletdb.cpp`**; wallet RPC and init paths. **`rpc_zeronode_*`** Boost suites do **not** exercise BDB.

**CDB::Rewrite hang:** **`wallet/db.cpp`** waits on **`mapFileUseCount`**; encrypt/rewrite with wallet still open — ties to **GTest 4.2** and **Boost 5.3a** above; **Debug notes → CDB::Rewrite**.

### Deferred infra

Fuzz (**Bitcoin** `src/test/fuzz`), **`make cov`/lcov**, leveldb/libsnark not on top-level check — no schedule here.

## Coverage context, gaps, and work backlog

**Suite presence (peer trees):**

| Suite | Zero | Bitcoin | Zcash | Pirate |
|-------|------|---------|-------|--------|
| Util / secp / univalue | ✓ | ✓ | ✓ | ✓ |
| GTest | ✓ 1.16.x | — | ✓ | ✓ (older) |
| Boost + Python RPC | ✓ | functional Py3 | ✓ | ✓ |
| **full_test_suite** | ✓ | — | ✓ | ✓ |
| Fuzz | ✗ | ✓ | — | — |

Bitcoin **functional** tree; Zcash **integration-tests** repo (zebrad / zainod / zallet—not **zcashd**). Links: [GoogleTest](https://github.com/google/googletest), [Zcash integration-tests](https://github.com/zcash/integration-tests).

**Boost / Python focus:** **`rpc_tests`**, **`rpc_wallet_tests`** (BDB); **`rpc_zeronode_*`** read-only / param validation. **Python:** which RPC each script hits = source + logs. **RPC/option enumerations and porting philosophy:** repo-root CSVs (below) + **TEST_ZERO.md** extended triage.

**Gaps by area** (drives backlog):

| Area | Coverage | No Coverage | Limited/Insufficient | Excluded |
|------|----------|-------------|----------------------|----------|
| **zero_exclusive** | 0% | zs_listtransactions, zs_gettransaction, zs_listspentbyaddress, zs_listreceivedbyaddress, zs_listsentbyaddress, getalldata, getsupply | — | — |
| **zero_experimental** | 0% | getsaplingwitness, getsaplingwitnessatheight, getsaplingblocks | — | — |
| **Zeronode logic** | 0% | Payment calc, budget validation, collateral, obfuscation | — | Debug → zeronode logic |
| **SwiftTX** | 0% | Lock conflict, instant tx validation | — | — |
| **Spork** | 0% | Activation, backward compat | — | — |
| **Zeronode integration** | 0% | Multi-node regtest, budget vote flow | — | — |
| **Fuzz** | 0% | All | — | — |
| **Zeronode RPC** | ~25% | — | zeronodecurrent, zeronodedebug, getzeronodeoutputs, startzeronode, getzeronodewinners, getzeronodescores, zeronode/znbudget super, znbudgetrawvote, znfinalbudget, getbudgetvotes, checkbudgets | — |
| **Network/P2P** | 60% | — | Partition, peer misbehavior | — |
| **Mining/PoW** | 75% | — | miner_tests (Zero 192,7 vs 96,5) | miner_tests, equihash_tests |
| **Wallet** | 80% | — | Backup/restore, corruption recovery | CachedWitnesses*, WriteCryptedSaplingZkey*, rpc_wallet_encrypted_wallet_sapzkeys |
| **RPC Python** | 19 pass-only (Tier A) | All pass (exit 0) | Some skip: get_coinbase_address, p2p peers; **`getchaintips`** main path fixed (split topology, **`CHAIN_BOOTSTRAP`**); ZERO_MINE_COINBASE=1 for full coinbase paths | script_test.py; parallel Tier A (**`--jobs>1`**) unreliable (**6.7**) |
| **Consensus harness** | Partial | Indices in scope (ChainTip, DecrementFirst) | pcoinsTip null → BuildWitnessCache returns early; witnesses not built | CachedWitnesses* |
| **Alert** | — | — | MagicBean/Zcash-specific | Alert_tests |

**Groups:** **A**/**B** zeronode read-only + param validation **done** (`rpc_zeronode_tests.cpp`, `rpc_zeronode_budget_tests.cpp`). **C**–**F** pending (logic, SwiftTX/spork, Python integration, **`zero_exclusive`**). Outstanding: **`zeronode super`**, **`znbudget super`**. Wallet/BDB ties to **GTest 4.2**, **Boost 5.3a**, **Berkeley DB** above.

**Prioritized work** (P1 quick → P4 defer):

| Phase | Area | Group | Tasks | Tech | Effort | Rationale |
|-------|------|-------|-------|------|--------|------------|
| **P1** | zero_exclusive | F | Add rpc_zero_exclusive_tests.cpp: param validation for zs_listtransactions, zs_gettransaction, zs_listspentbyaddress, zs_listreceivedbyaddress, zs_listsentbyaddress, getalldata, getsupply | Boost | Low | Zero-specific; no coverage; same pattern as rpc_zeronode_tests |
| **P1** | Zeronode RPC | B | Add zeronode super, znbudget super subcommand validation | Boost | Low | 2 tests; completes Group B |
| **P1** | zero_experimental | — | Param validation for getsaplingwitness, getsaplingwitnessatheight, getsaplingblocks | Boost | Low | May need chain state; try param-only first |
| **P2** | Zeronode logic | C | GTest: payment calculation, budget validation, collateral check. Mock znodeman, budget, zeronodeSync | GTest | Medium | Core zeronode; requires harness |
| **P2** | SwiftTX, Spork | D | GTest: lock conflict, activation, backward compat. Adapt CreateValidBlock | GTest | Medium | Consensus-critical; depends on GTest harness patterns above |
| **P2** | Zeronode integration | E | Python RPC: multi-node regtest, budget vote flow | Python RPC | Medium | End-to-end; follow wallet_sapling.py |
| **P2** | Wallet | — | Fix or bypass CDB::Rewrite deadlock; re-enable WriteCryptedSaplingZkey*, rpc_wallet_encrypted_wallet_sapzkeys | GTest, Boost | Medium | Unblocks 3 excluded tests |
| **P2** | Consensus harness | — | Populate pcoinsTip; or manual witness build; or BuildWitnessCache test path. (Dangling ptr fix applied: indices in scope.) | GTest | Medium | Unblocks 4 excluded tests |
| **P3** | Mining/PoW | — | Add Zero (192,7) Equihash test vectors or conditional skip; re-enable miner_tests | Boost | Medium | Equihash params differ |
| **P3** | Network/P2P | — | Python RPC: partition, misbehavior; or extend mininode | Python RPC | Medium | 60% coverage; gaps documented |
| **P3** | Harness | — | Stabilize Tier A parallel (**`contrib/run-tests.sh --jobs>1`**) or cap/remove parallel pool; see **6.7**, **TEST_ZERO.md** Parallel Tier A | Shell + RPC | Low–Medium | Observed hang (**`paymentdisclosure`**, **`N=4`**) |
| **P3** | Wallet | — | Backup/restore, corruption recovery tests | Boost + Python | Medium | Resilience |
| **P3** | addressindex | — | Error-path tests for getaddressmempool, getaddressutxos, etc. | Boost | Low | rpc_tests only |
| **P4** | Fuzz | — | libFuzzer infra; seed from Bitcoin src/test/fuzz | Fuzz | High | New infra |
| **P4** | Functional | — | See **TEST_ZERO.md** | Python 3.10+ | High | Depends on contrib shebang cleanup |
| **P4** | decodescript | — | Expand beyond rpc_tests | Boost | Low | Minor gap |

**Workflow:** P1 first. P2 in parallel where harness work overlaps. P3 after P2. P4 deferred.

## Inventories and rescan-related coverage

**Repo-root UTF-8 CSV:**

| File | Role |
|------|------|
| **`RPCs.csv`** / **`RPCs_extended.csv`** | One row per compared RPC; **`zero_missing_sources`** (B / Z / P) only on extended. |
| **`Options.csv`** / **`Options_extended.csv`** | One row per **`-option`**; extended adds **`zero_missing_sources`**. |
| **`Reindex_Rescan.csv`** | Reindex / rescan / deletetx / consolidation: options vs RPC, code pointers, test-gap notes. |

When adding or removing a Zero RPC or option, update **both** base and extended CSV so row order and keys stay aligned. Long lists stay in the CSVs, not here.

**Rescan / reindex in code:** **`src/init.cpp`**, **`main.cpp`**; **`wallet/rpcdump.cpp`** (`z_importkey`, `z_importviewingkey`, `importprivkey`, `importaddress` + rescan); **`wallet/wallet.cpp`** (rescan progress, deletetx, consolidation); **`asyncrpcoperation_saplingconsolidation.*`**. **`init.cpp`** help often ahead of **`doc/man/zerod.1`**.

**Tests:** **`reindex.py`**, **`rescan_import.py`**, **`rescan_startup.py`** (Tier A — **TEST_ZERO.md**); skips may track **RPC Python** maturity/skip patterns above. No deletetx / consolidation integration tests in-tree.

## Debug notes

### CachedWitnesses*

**Context:** Partial fixes (index lifetime, `pblockIn` path when `pcoinsTip` null) applied; still fails on pre-add witnesses, missing `BuildWitnessCache` witnesses, or **`EXPECT_DEATH`** vs no assert in **`DecrementNoteWitnesses`**.

**Debug:** `./src/zero-gtest --gtest_filter='WalletTests.CachedWitnessesEmptyChain' --gtest_break_on_failure`; LogPrintf in **`VerifyAndSetInitialWitness`**; isolate test order.

**Next:** Manual witness build from block (**GTest / wallet harness patterns** above); replace or gate **`EXPECT_DEATH`**; per-test datadir to rule out shared wallet state.

### CDB::Rewrite / encrypted Sapling zkeys

**Failure:** **`CDB::Rewrite`** busy-waits on **`mapFileUseCount`** while **`EncryptWallet`** holds the DB open.

**Debug:** LogPrintf before **`MilliSleep`** in **`wallet/db.cpp`**; gdb on **`MilliSleep`**.

**Next:** Close wallet DB before rewrite; test-only rewrite bypass; or copy-then-rename strategy.

### wallet.py node0 balance

**Issue:** Node0 balance ~19 vs expected 29 on clean chain; **`zero_regtest_subsidy`** fixed node1 only. **COINBASE_MATURITY** / subsidy — **TEST_ZERO.md**.

**Debug:** **`--nocleanup`**, **`listunspent`** / **`getblock`** at heights 4–6.

### Zeronode logic GTest

**Blockers:** Mock **`znodeman`**, budget maps, **`zeronodeSync`**; logic in **`zeronode/payments.cpp`**, **`zeronode/budget.cpp`**. **Next:** **`test_zeronode_payments.cpp`**-style fixtures (**Prioritized work** table, P2 Zeronode logic).
