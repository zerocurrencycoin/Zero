# TEST_ZERO

Validation runbook: commands, modes, harness behavior, known failures.

**Authoritative lists:** `qa/pull-tester/rpc-tests.sh` (**`testScriptsTierA`**, **`testScripts`**, **`testScriptsExt`**); **`contrib/run-tests.sh`** **`PYTHON_PASSING`** mirrors Tier A for **`--jobs=N`** only. If this file disagrees with those scripts, **the scripts win**.

**Prereqs:** [BUILD_ZERO.md -- Quick Start](BUILD_ZERO.md#2-quick-start) (toolchain, Python **3.10+**, produced binaries).

---

## Quick start by use case

| You want... | Command / next step |
|-----------|---------------------|
| **Default contributor gate** (pass-only C++ + Tier A RPC, serial) | `./contrib/run-tests.sh --strict` after building **`src/zerod`** |
| **Fast smoke** (util / secp / univalue only; no C++, no RPC) | `./contrib/run-tests.sh --quick --no-python --strict` (~11s) |
| **Quick + Tier A RPC** (skips GTest/Boost; still runs Tier A) | `./contrib/run-tests.sh --quick --strict` |
| **C++ only** (no Python RPC) | `./contrib/run-tests.sh --no-python --strict` (~80s C++) |
| **One Tier A RPC script** | `./qa/pull-tester/rpc-tests.sh <basename>` |
| **Multi-stage driver** (Tier B RPC, fail-fast; not default, not `--all`) | `./contrib/run-tests.sh --suite` |
| **Known hang / crash / fail C++ only** | `./contrib/run-tests.sh --fail` (diagnostic; not a merge gate) |
| **Bulk RPC pass (A + B + E)** | `./contrib/run-tests.sh --all` or `rpc-tests.sh -all` (33 invocations; re-validate after tier moves -- **Open work**) |
| **RPC known-fail diagnostic** | `./contrib/run-tests.sh --rpcfail` or `rpc-tests.sh -rpcfail` |

**Environment:** Python **3.10+**; **`PYTHON`** and **`BUILDDIR`** for manual **`rpc-tests.sh`**--see **Process -> Troubleshooting**.

---

## Harness landscape

| Layer | Entry | Scope |
|-------|-------|-------|
| Util / vectors | `src/test/bitcoin-util-test.py` | Encoding, RPC-free |
| Libraries | secp256k1, univalue (`make -C src ... check`) | Third-party correctness |
| Symbols / security | `check-symbols`, `check-security` | Shipping constraints |
| GTest (`zero-gtest`) | Wallet, consensus-adjacent | Excluded suites in **Known failures** |
| Boost (`test_bitcoin`) | RPC, script, PoW (192,7), zeronode | Pass-only filters; `miner_tests` regtest-only pending (48,5) blockinfo |
| Python RPC | `qa/pull-tester/rpc-tests.sh` | Multi-node regtest; **`-A`** = Tier A gate |
| `full_test_suite.py` | Ordered stages, fail-fast | `--suite` only; Darwin skips ELF stages |

---

## Harness changelog (recent)

| Change | Location | Effect |
|--------|----------|--------|
| **Encrypt-hang class fixed** (2026-06-09) | **`src/wallet/crypter.cpp`** `AddCryptedSaplingSpendingKey`, **`src/wallet/wallet.cpp`** `AddSaplingFullViewingKey` | Crypted-key add called the **virtual** `AddSaplingFullViewingKey` (CWallet override writes to wallet DB), re-entering BDB inside `EncryptWallet`'s open transaction / `LoadWallet`'s open cursor -> page-lock deadlock. Now calls `CBasicKeyStore::` explicitly (as upstream); CWallet override also routes through `pwalletdbEncryption` when set. **`WriteCryptedSaplingZkey*`** (GTest) and **`rpc_wallet_encrypted_wallet_sapzkeys`** (Boost) pass and are back in the default gate. |
| **`CachedWitnesses*` ported** (2026-06-09) | **`src/wallet/gtest/test_wallet.cpp`**, **`src/utiltest.cpp`** | `CreateValidBlock` keeps the index header in sync (merkle root, `hashFinalSproutRoot`/`hashFinalSaplingRoot`) so depth checks and witness-root validation work without `pcoinsTip`; decrement expectations rewritten to Zero semantics (last cached witness is never popped); dummy Sapling output gets a random `cm`. `EmptyChain`, `ChainTip`, `DecrementFirst` pass; **`CleanIndex` stays excluded** (reindex scenario needs `pcoinsTip` anchors + `ReadBlockFromDisk`). |
| **`mempool_spendcoinbase` -> B pass** (2026-06-09) | **`qa/rpc-tests/mempool_spendcoinbase.py`**, **`rpc-tests.sh`** | Ported maturity-100 assumptions to **`COINBASE_MATURITY`** [720]; boundary heights derived from cached tip (725); spends actual coinbase value minus fee instead of hardcoded 10. Moved from Bfail Debug to **`testScriptsTierBPass`**. |
| **`blockchain.py` cache-height fix** (2026-06-09) | **`qa/rpc-tests/blockchain.py`** | `gettxoutsetinfo` expectations at **`CACHE_CHAIN_TIP`** (725) via **`regtest_supply_at_height()`** (10 ZER >> floor(h/150), zatoshi math) instead of hardcoded height-200 totals. |
| **`initialize_chain` stale-cache guard** (2026-06-10) | **`qa/rpc-tests/test_framework/util.py`** | Writes **`cache/CACHE_TIP`** on build; auto-deletes and rebuilds when marker missing or tip != **`COINBASE_MATURITY + 5`**. See **Stale cache guards** under **`initialize_chain` cache**. |
| **`proxy_test` IPv6 skip** (2026-06-10) | **`qa/rpc-tests/proxy_test.py`**, **`util.py`** **`ipv6_loopback_available()`** | Skips IPv6 SOCKS leg when **`::1`** bind fails (e.g. lazu IPv6 disabled); IPv4/onion legs still run. |
| Split topology when **`split=True`** | **`qa/rpc-tests/getchaintips.py`** **`setup_network`** | Connect only **0-1** and **2-3** during the partition so the two halves actually fork (previously **0-2** / **1-2** bridged the split). |
| Shorter bootstrap | Same | **`CHAIN_BOOTSTRAP = 30`** for initial mining (was 200); **`join_network`** still avoids re-mining when the chain is already long enough. |
| Branch assertions | Same | **`expected_branchlen`** from **`shortTip['height'] - CHAIN_BOOTSTRAP`**; active height matches long chain after rejoin; accepts one or two tips per existing semantics. |
| Background wait / exit codes | **`contrib/run-tests.sh`** **`run_bg`** | Set **`BG_LAST_PID=$!`**; avoid **`$(run_bg ...)`** (subshell caused **`wait $pid`** to fail). GTest/Boost and Tier A parallel children wait on real child PIDs. |
| **`rescan_import` / `rescan_startup` executable bit | Git index **`qa/rpc-tests/rescan_*.py`** | **`100755`** (`git update-index --chmod=+x`); was **`100644`** -> **`Permission denied`** under **`rpc-tests.sh`**. |
| **`prioritisetransaction` retired** | **`rpc-tests.sh`** | Moved to **Bfail Retired** (legacy 1121-block Bitcoin priority test; Zcash/Bitcoin upstream replaced). |
| **`wallet_treestate` retired** | **`rpc-tests.sh`** | Moved to **Bfail Retired** (Sprout `z_sendmany` / joinsplit treestate; Zcash upstream uses Sapling-only). |
| **`initialize_chain` maturity** | **`util.py`** | Cache tip **725**; **`rpc_cache_root()`**; **`CACHE_TIP`** marker + stale auto-rebuild; **`wait_for_daemon_rpc`** uses **`-rpcwait`**. See **`initialize_chain` cache**. |
| **Bfail subgroups** | **`rpc-tests.sh`** | **`testScriptsTierBFailDebug`** / **`Retired`**; **`-list-csv`**. |
| **`wallet_changeaddresses` Zero port | **`qa/rpc-tests/wallet_changeaddresses.py`** | 2 nodes, Overwinter+Sapling at height 1, `-txindex`, `-experimentalfeatures` + `-zmergetoaddress`. **`initialize_chain_clean`**; **`get_coinbase_address`** fails hard without mature UTXO. |
| **`shorter_block_times` / `wallet.py` -> Bfail Debug** | **`rpc-tests.sh`**, scripts | Removed skip/`return` masks; Blossom@106 vs maturity **720** and node0 block-5 balance bug -- see per-script debug sections |
| **`wallet_changeaddresses` -> Bfail Debug** | **`rpc-tests.sh`**, script | Was vacuous pass: **`ensure_mature_coinbase_or_skip`** exited **0** on empty chain without **`ZERO_MINE_COINBASE=1`** |
| **`wallet_changeindicator` + Sprout VK | **`qa/rpc-tests/wallet_changeindicator.py`**, **`src/wallet/wallet.cpp`** | `mine_until_node_has_mature_coinbase` at `run_test` start. `UpdateSproutNullifierNoteMapWithTx` skips when `GetSproutNoteNullifier` is empty (viewing key only)--avoids `assert(false)`. |
| **`serialize_script_num` (Python 3) | **`qa/rpc-tests/test_framework/blocktools.py`** | **`bytearray.append`** takes an **int** (**0-255**), not **`chr(...)`** (would raise **`TypeError`** on scripts that use **`serialize_script_num`**). |
| **Tip-200 cache scripts -> Bfail Debug** | **`rpc-tests.sh`**, **`rescan_import.py`** | **`wallet_addresses`**, **`rescan_import`**, **`reorg_limit`** moved off Tier B pass; **`rescan_import`** **`ensure_mature_coinbase_or_skip`** removed (was masking failures after a wrong tip) |
| **`wallet_overwintertx` retired** | **`rpc-tests.sh`** | Moved from Tier B pass to **Bfail Retired** (Sprout zaddrs, expiry overlap with Bfail mempool/P2P scripts) |
| **`CachedWitnesses*` gtest port** | **`src/wallet/gtest/test_wallet.cpp`**, **`src/wallet/wallet.cpp`** | Harness sets block merkle + Sprout/Sapling commitment roots on **`CBlockIndex`**; tests match Zero **`DecrementNoteWitnesses`** (never pops last witness). **`AddSaplingFullViewingKey`** avoids BDB self-deadlock during **`EncryptWallet`**. **`CachedWitnessesCleanIndex`** still excluded in **`test_filters.sh`**. |

**Open (harness):** see **Open work** below. **`--jobs>1`** Tier A RPC remains **best-effort** only.

---

## Open work

Outstanding harness and porting tasks after the 2026-06-08 tier moves (tip-**200** scripts, vacuous-pass masks, **`wallet_overwintertx`** retirement). None of these block the **default contributor gate** (**`-A`**); they affect **`-B`** honesty, **`-all`** bulk timing, and C++ diagnostic tiers.

### Tip-**200** Bfail scripts (port to clean chain)

Six Bfail Debug scripts still use default **`setup_chain`** (warm cache tip **725**) while asserting or assuming tip **200**. They were moved off Tier B pass so **`-B`** no longer reports a false pass; they still need engineering fixes before promotion back to pass tiers.

| Script | Failure mode | Fix direction |
|--------|--------------|---------------|
| `wallet_addresses.py` | **`assert_equal(getblockcount(), 200)`** | **`initialize_chain_clean`** + **`generate(200)`**; keep **200/201** Sapling RPC story -- see **height 200/201** |
| `rescan_import.py` | tip **725** vs **200** | Same clean bootstrap; **`get_coinbase_address`** fails hard without mature UTXO |
| `reorg_limit.py` | tip **725** vs **200** on split nodes | **`initialize_chain_clean`** + mine **200** on all nodes before partition, **or** **`BASE = getblockcount()`** and relative reorg depths |
| `wallet_listnotes.py` | tip **200** assert | Clean chain + **`generate(200)`** or drop tip assert |
| `wallet_sapling.py` | tip **200** assert | Same |

**Pattern:** preserve upstream **200-block wallet layout** intent on a **fresh** chain; do **not** warm-cache copy without updating asserts. Insight scripts already follow this (**`initialize_chain_clean`** + **`coinbase_mature_tip(5)`**). Full inventory: **Tip 200 debt** under **`initialize_chain` cache**.

### Wallet / NU Bfail Debug (maturity engineering)

| Script | Blocker | Fix direction |
|--------|---------|---------------|
| `shorter_block_times.py` | Blossom at **106** vs **`COINBASE_MATURITY = 720`**; no mature coinbase at **`generate(101)`** | Reschedule Blossom (e.g. **`2bb40e60:820`**) or mine plan on clean chain; see **`shorter_block_times.py` debug** |
| `wallet.py` | Node0 balance **~19 ZER** vs **29** after node1 mines **720** (block-5 coinbase not fully counted) | **`mine_to_height`** / explicit tip after block-5 maturity; **`zero_regtest_subsidy_range`** not hardcoded **50** |
| `wallet_changeaddresses.py` | **`initialize_chain_clean`** only; no mining phase | **`mine_until_node_has_mature_coinbase`** or **`generate(COINBASE_MATURITY + 1)`** after clean start |

Skip/`return` masks on **`shorter_block_times`** and **`wallet.py`** are removed; failures are visible under **`-Bfail`**.

### Post-merge validation (**`tests-debug`** integrated)

**`tests-debug`** (`4f430f5c5`) is merged into **`tests-harness`**. Landed: C++ encrypt-wallet deadlock fix, **`CachedWitnesses*`** gtest port (except **`CleanIndex`**), **`test_filters.sh`** filter updates, **`mempool_spendcoinbase.py`** -> Tier B pass.

**Retest after merge:**

```bash
./contrib/run-tests.sh --strict
./contrib/run-tests.sh --fail --strict   # CachedWitnessesCleanIndex + miner_tests only
./contrib/run-tests.sh --all --strict    # refresh bulk RPC timing in Verification snapshot
```

### Re-validate bulk RPC (**`-all`**)

The verification table at the end of this file still records **`--all --strict` PASS ~1275s** from **before** recent Bfail moves. Re-run after tier stabilization:

```bash
./contrib/run-tests.sh --all --strict
```

**Expect:** **33** pass-tier invocations (A=10, B=21, E=2). B pass should be more honest (no tip-**200** false passes, no vacuous skips on **`wallet_changeaddresses`**). Wall time may drop slightly (fewer scripts) or rise if latent B-pass failures surface. Also refresh **`--suite`** if **`full_test_suite.py`** RPC stage timing matters (**`-all`** inside the suite).

| If this fails | Likely cause | Next step |
|---------------|--------------|-----------|
| Tier B script | Implicit cache + wrong maturity math, or unported **`generate(720)`** | Run basename; see **Bfail Debug** tables |
| Tier A script | Cache stale after harness pull / tag checkout (old tip **200**) | Auto-rebuild via **`CACHE_TIP`** marker, or **`rm -rf cache`**; see **Stale cache guards** |
| C++ (default/`--all`) | Unmerged encrypt hang or filter drift | Compare **`test_filters.sh`** with **`tests-debug`** |

### Parallel Tier A (**`--jobs>1`**)

**`paymentdisclosure`** has hung under **`--jobs=4`** (macOS). No fix in-tree. Contributor gate stays **serial** (**omit `--jobs`**). See **Parallel Tier A** under Reference.

---

## Verification snapshot

**Tier lists are authoritative in code only** -- do not duplicate script names here.

| Source | Contents |
|--------|----------|
| `qa/pull-tester/rpc-tests.sh` | `testScriptsTierA`, `testScriptsTierBPass`, `testScriptsTierBFailDebug`, `testScriptsTierBFailRetired`, `testScriptsExtPass`, `testScriptsExtFail`, full `testScripts` / `testScriptsExt` |
| `contrib/run-tests.sh` | `PYTHON_PASSING` mirrors Tier A for `--jobs=N` only |
| Export | `./qa/pull-tester/rpc-tests.sh -list-csv [path]` -> `tier,group,script` CSV (one script per line, grouped; arrays in `rpc-tests.sh` are authoritative) |

Regenerate human-review CSV:

```bash
./qa/pull-tester/rpc-tests.sh -list-csv qa/rpc-tests/test_tier_inventory.csv
```

**Pass-tier counts** (from **`test_tier_inventory.csv`**; authoritative arrays in **`rpc-tests.sh`**):

| Tier | Count | Notes |
|------|-------|-------|
| A | 10 | Contributor gate (**`-A`**, **`PYTHON_PASSING`**) |
| B pass | 22 | 21 unique scripts; **`txn_doublespend`** runs twice |
| E pass | 2 | **`invalidateblock`**, **`maxblocksinflight`** |
| **`-all`** | **34** | A + B + E pass invocations |
| Bfail Debug | 31 | **`-Bfail`** first group |
| Bfail Retired | 6 | Sprout / legacy |
| Efail | 8 | Comptool / long-chain diagnostics |

**Validation runs:** see **Verification snapshot** at end of this file (updated after each harness change).

**Not gate-ready:** `--jobs>1` (hangs possible); **`--all`** bulk; excluded C++ suites (see **Known failures**).

---

## Accounting

- Without **`--strict`**, failures print **`WARNING`** but exit **0**. With **`--strict`**, exit **1** on any failure.
- **Exit 0 after `skip_test`** is a skip, not a pass.
- Some Boost cases return early (e.g. **(96,5)** Equihash vectors on **(192,7)** mainnet) -- they pass but do not prove that code path ran.

---

## Interpreting results

### `contrib/run-tests.sh`

| Signal | Meaning |
|--------|---------|
| **`PASS: <step>`** | Subprocess exited **0**. |
| **`FAIL: <step>`** | Non-zero; see cited **`.log`** under **`test-logs/`**. |
| **`WARNING: one or more steps failed`** | Default: failures occurred; exit **0** unless **`--strict`**. |
| **`FAIL: one or more steps failed (--strict)`** | **`--strict`** and at least one failure -> exit **1**. |


### GTest / Boost

GTest: **`[  PASSED  ] N tests.`** means all ran passed; **`FAILED`** or non-zero: isolate with `--gtest_filter=Suite.Case`. Boost: **`*** No errors detected`** means pass; find first **`error:`** on failure.

### Equihash (Boost `equihash_tests`)

**Source:** **`src/test/equihash_tests.cpp`**. **Run:** **`./src/test/test_bitcoin -t equihash_tests`**.

- **(96,5) solver/validator vectors** return early when mainnet **`nEquihashN != 96`** -- compatible no-op on Zero, **not** **(96,5)** coverage.
- **Zero-specific cases** exercise **(192,7)** mainnet genesis (valid + corrupt **`nSolution`**) and **(48,5)** regtest genesis.

Failures in the Zero-specific cases usually mean **`chainparams.cpp`** / **`pow.cpp`** / **`CheckEquihashSolution`** drift. Verbose: **`--log_level=test_suite`** or **`message`**.

---

## Process

### Release candidate: validation and merge to `master`

Typical order for **`zero-400names`** (or any RC) -> **`master`** (remote default is **`master`**, not `main`):

1. **Clean tree** -- remove temporary paths; `git status` empty.
2. **Build** -- produce `src/zerod`, `zero-gtest`, `test_bitcoin`.
3. **Contributor gate** -- `./contrib/run-tests.sh --strict` (default mode: pass-only C++ + Tier A RPC).
4. **Optional widen** -- `./contrib/run-tests.sh --suite` (Linux: ELF stages); `./contrib/run-tests.sh --all` (bulk RPC); platform release scripts.
5. **Tag on the RC commit** -- `git tag -a v4.0.1 -m "..."`; rebuild on tag for clean `zerod --version` (see prior version-hash notes).
6. **Merge to `master`** -- open PR **`zero-400names` -> `master`** (or fast-forward after review) **after** steps 3--5 pass. **`master` should receive the tagged release commit** (merge then tag on `master`, or tag on branch then merge including tag).
7. **Push** -- `git push origin master` and `git push origin v4.0.1`.

Do **not** merge before **`--strict`** passes. Do **not** tag with a dirty tree if you want a hash-free version string.

### `contrib/run-tests.sh` -- flags to re-check after parser changes

| Flag / input | Expected | Quick check |
|--------------|----------|-------------|
| *(default)* | Pass-only GTest + Boost + Tier A serial; **WARNING** if any step failed | `./contrib/run-tests.sh` |
| **`--strict`** | Exit **1** if any step failed | `./contrib/run-tests.sh --strict` |
| **`--quick`** | util, secp, univalue, symbol/security if **`zerod`** exists; **skips GTest/Boost**; **still runs Tier A RPC** unless **`--no-python`** | `./contrib/run-tests.sh --quick --strict` |
| **`--no-python`** | Skips RPC only (combine with **`--quick`** for ~11s smoke) | `./contrib/run-tests.sh --no-python` |
| **`--jobs=N`** | Tier A RPC parallel (**default pass-only only**; see **Parallel Tier A** below) | `./contrib/run-tests.sh --jobs=2 --strict` |
| **`--fail`** | **Only** Known-failures C++ suites; no util, no RPC | may hang; see **Known failures** |
| **`--all`** | Same C++ exclusions as default; RPC **`-all`** (**`-A` `-B` `-E`** pass) | ~20 min RPC; not merge gate |
| **`--rpcfail`** | **RPC only** **`-rpcfail`** (**`-Bfail` `-Efail`**) | diagnostic; expect failures |
| **`--suite`** | **`full_test_suite.py` only** (not default, not `--all`); fails fast | `./contrib/run-tests.sh --suite` |
| **`--build-checks`** | Extra **`make check-security`** at start | `./contrib/run-tests.sh --build-checks --quick` |
| **`PYTHON`**, **`LOG_DIR`**, **`ZERO_MINE_COINBASE`** | See **Reference** | top of **`contrib/run-tests.sh`** |

**Alignment:** C++ pass/fail filters live in **`qa/zcash/test_filters.sh`** (sourced by **`contrib/run-tests.sh`**, read by **`qa/zcash/full_test_suite.py`**). Edit that file only when changing exclusions.

### Adding and extending tests

- **Boost:** **`src/test/*_tests.cpp`**; **`./src/test/test_bitcoin -t SuiteName`**. RPC patterns: **`CallRPC`**, **`CheckRPCThrows`** (e.g. **`rpc_zeronode_tests.cpp`**).
- **GTest:** **`src/wallet/gtest/`**; **`./src/zero-gtest --gtest_filter=...`**
- **Python RPC:** **`qa/rpc-tests/*.py`**, **`BitcoinTestFramework`**, **`test_framework/util.py`**.

Zeronode RPC coverage: **`rpc_zeronode_tests`**, **`rpc_zeronode_budget_tests`**.

### Troubleshooting

- **Blake2 / imports:** Python **3.10+** and **`hashlib.blake2b`**
- **`PYTHON`:** **`contrib/run-tests.sh`** sets it via **`find_python3`**. Direct **`./qa/pull-tester/rpc-tests.sh <basename>`** works when scripts are executable (**`#!/usr/bin/env python3`**).
- **RPC binaries not found:** **`qa/pull-tester/tests-config.sh`**, **`BUILDDIR`**.
- **Boost/GTest noise:** one suite at a time, or **`contrib/run-boost-individual.sh`**.
- **Orphaned `zerod`:** after crashes, **`pkill -f "zerod -datadir="`** if needed.
- **Parallel RPC (`--jobs=N`) stuck:** see **Reference -> Tier A -> Parallel Tier A**; kill stray **`zerod`** / hung **`rpc-tests.sh`** children if needed.

---

## Reference

Harness inventory and commands: see **Harness landscape** and **Quick start** above.

### `contrib/run-tests.sh` modes

| Mode | GTest | Boost | RPC |
|------|-------|-------|-----|
| **Default `(none)`** | Pass-only (exclude known bad suites) | Pass-only exclusions | **`rpc-tests.sh -A`** (Tier A) |
| **`--quick`** | Skip | Skip | **Tier A** (`rpc-tests.sh -A`) unless **`--no-python`** |
| **`--no-python`** | Same as mode (default pass-only) | Same as mode | **Skip** |
| **`--fail`** | **Known failures only** (see table below) | **Known failures only** | **Skip** |
| **`--all`** | Pass-only (excludes **Known failures**) | Pass-only exclusions | **`-all`** (**`-A` `-B` `-E`**) |
| **`--rpcfail`** | **skip** | **skip** | **`-rpcfail`** (**`-Bfail` `-Efail`**) |
| **`--suite`** | `full_test_suite.py` pass-only | same | **`rpc-tests.sh`** (no args = **`-all`**) |
| **`--jobs=N`** | -- | -- | Tier A only; **default** only |

**Default is not `--suite`.** Default runs this script's own quick + filtered C++ + **Tier A** list. **`--suite`** runs only **`full_test_suite.py`**: ordered stages, **Tier B** RPC bulk, optional Linux ELF checks -- a different pipeline with different RPC scope.

**`--quick` skips only GTest and Boost.** Unless **`--no-python`** is also set, **`--quick` still runs Tier A RPC** (same tier as default). That is intentional: a shorter C++ path while keeping the Python contributor gate.

**`--no-python` is orthogonal to `--quick`.** **`--quick --no-python`**: util / secp / univalue / symbol checks only (~11s). **`--no-python`** alone (no **`--quick`**): adds pass-only GTest + Boost (~80s), no RPC.

**`--fail`** runs **only** the C++ suites in **Known failures** below (positive GTest/Boost filters). It does **not** run util-test, secp256k1, univalue, symbol checks, or Python RPC. Use **default** for the contributor gate; use **`--all`** or **`rpc-tests.sh -all`** for bulk RPC pass tiers.

### `full_test_suite.py`

**Invoke:** **`python3 qa/zcash/full_test_suite.py`** or **`./contrib/run-tests.sh --suite`**. Fails on first failed stage.

**Stage order:** `btest` -> `gtest` -> `sec-hard` -> `no-dot-so` -> `util-test` -> `secp256k1` -> `univalue` -> `rpc` (Tier B).

**Unfiltered:** **`--unfiltered`** or **`ZERO_FULL_SUITE_UNFILTERED=1`** removes GTest/Boost pass-only filters (hang/crash risk on excluded wallet tests).

**Darwin:** **`contrib/run-tests.sh`** passes **`--skip sec-hard --skip no-dot-so`** on Darwin because those stages target **ELF** / **`depends/` `.so`** layout--**release artifact checks**, not a claim that tests behave differently on macOS. Linux runs those stages when not skipped.

### Pass-only C++ filters (default + default full suite)

**GTest**

```text
--gtest_filter='-WalletTests.CachedWitnessesCleanIndex'
```

**Boost**

```text
--run_test='!miner_tests'
```

| Layer | Excluded (default) | Reason (summary) |
|-------|-------------------|------------------|
| GTest | **`CachedWitnessesCleanIndex`** | Reindex scenario needs incremental **`BuildWitnessCache`** path (**`pcoinsTip`** anchors + **`ReadBlockFromDisk`**); gtest harness has neither |
| Boost | **`miner_tests`** | **`CreateNewBlock_validity`**: **`blockinfo`** **(96,5)** vs Zero **(192,7)** MAIN -> skip via `nEquihashN != 96`; excluded in **`test_filters.sh`** |

**Fixed 2026-06-09 (now in gate):** GTest **`WriteCryptedSaplingZkey*`**, **`CachedWitnessesEmptyChain/ChainTip/DecrementFirst`**; Boost **`rpc_wallet_encrypted_wallet_sapzkeys`**. See **Harness changelog**.

**Alerts:** Bitcoin P2P alert tests are not compiled (**`alert_tests.cpp`** omitted from **`BITCOIN_TESTS`**). Product code may still expose **`-alerts`** / **`-alertnotify`** stubs; no harness exclusion needed.

**`equihash_tests`** stays in pass-only; interpretation: **Interpreting results -> Equihash**. List suites: **`./src/zero-gtest --gtest_list_tests`**, **`./src/test/test_bitcoin --list_content`**.

### RPC driver (`qa/pull-tester/rpc-tests.sh`)

| Flag | Tier | Array |
|------|------|-------|
| **`-A`** / **`--tier-a`** | **A** (gate) | **`testScriptsTierA`** |
| **`-B`** / **`--tier-b`** | **B pass** | **`testScriptsTierBPass`** |
| **`-Bfail`** | **B fail** | **`testScriptsTierBFail`** = Debug + Retired (diagnostic) |
| **`-list-csv [path]`** | inventory | `tier,group,script` CSV; no tests run |
| **`-E`** / **`--tier-e`** | **Ext pass** | **`testScriptsExtPass`** |
| **`-Efail`** | **Ext fail** | **`testScriptsExtFail`** (diagnostic) |
| **`-all`** | **A + B + E pass** | All pass tiers in order |
| **`-rpcfail`** | **Bfail + Efail** | Known-fail diagnostic |
| *(no args)* | **`-all`** | Used by **`full_test_suite.py`** RPC stage |
| **`<basename>`** | single | Any script in tier or inventory arrays |

**Harness mapping:** default **`run-tests.sh`** -> **`-A`**; **`--all`** -> **`-all`**; **`--rpcfail`** -> **`-rpcfail`**; **`--suite`** -> **`full_test_suite.py`** -> no-args (**`-all`**). **`--jobs=N`** runs Tier A via **`PYTHON_PASSING`** list.

Requires wallet-enabled build (**`ENABLE_BITCOIND`**, **`ENABLE_UTILS`**, **`ENABLE_WALLET`**). Config: **`qa/pull-tester/tests-config.sh`**.

### Tier A (contributor gate)

Tier inventory: **`rpc-tests.sh -list-csv`**. Common porting themes: **`COINBASE_MATURITY` [720]**, chaintip / NU height vs mining plan, `getchaintips` split topology, P2P `version` set.

**Parallel Tier A (`--jobs=N`, `N>1`):** Only when RPC is **default Tier A**: not with **`--fail`**, **`--all`**, **`--no-python`**, or **`--suite`**. **`N=1`** (serial) is the path **CI and the contributor gate** assume.

**Reliability:** Parallel runs start **many `zerod` processes** (Equihash + RAM). That is **best-effort throughput**, not a supported merge gate: scripts can **hang or flake** under load (e.g. **`paymentdisclosure`** observed stuck with **`--jobs=4`** on one macOS run). If a run stalls, use serial (**omit `--jobs`**) or a **lower `N`**; confirm with **`test-logs/...-rpc-*.log`**. GTest/Boost in **`run-tests.sh`** are **not** parallelized by **`--jobs`** (only the Tier A RPC children).

---

## Test network model and encapsulation

No automated test connects to public mainnet or testnet. All harness layers use local or in-process setups.

### Python RPC (`qa/rpc-tests`)

| Aspect | Value |
|--------|-------|
| Chain | **Local regtest** (`regtest=1` in `zero.conf` via `initialize_datadir`) |
| Processes | `zerod` children under `$TMPDIR/node{N}/` |
| Setup | `initialize_chain_clean` (empty), `initialize_chain` (cached regtest), or per-test `generate()` |
| P2P fakes | `mininode.TestNode(net="regtest")`, Zero `pchMessageStart` `5c475451` |
| Comptool | Programmatic blocks: `CBlock.solve()` at regtest **(48,5)** via `equihash.py` |
| NU | `-nuparams=<branchHex>:<height>` on regtest only |
| Exceptions | `turnstile.py` documents **manual testnet** steps (Bfail Retired); not CI |

### C++ Boost (`test_bitcoin`)

| Suite / pattern | Chain params | Encapsulation |
|-----------------|--------------|---------------|
| Fixture default | **MAIN** (`test_bitcoin.cpp` `SelectParams(MAIN)`) | In-process; no network |
| `equihash_tests` | MAIN + REGTEST switch per case | Genesis header vectors **(192,7)** / **(48,5)** |
| `rpc_wallet_tests` | Often **TESTNET** for zaddr HRP checks | `CallRPC` / wallet fixtures |
| `transaction_tests` | REGTEST for Overwinter branch | Temporary `SelectParams` |
| `miner_tests` | MAIN fixture | **`blockinfo`** **(96,5)**; skips when MAIN **`nEquihashN != 96`** (Zero **192**); regtest **(48,5)** vectors not yet authored |
| `pow_tests` | MAIN | `CalculateNextWorkRequired` unit tests |
| `key_tests` | REGTEST | Key derivation |

### C++ GTest (`zero-gtest`)

| Area | Chain | Notes |
|------|-------|-------|
| `test_upgrades`, `test_transaction_builder` | REGTEST | NU / builder |
| `test_wallet_zkeys`, `test_paymentdisclosure` | MAIN / TESTNET | Wallet crypto |
| `test_deprecation` | MAIN + REGTEST | `-alertnotify` stub |
| `test_pow`, `test_miner` | MAIN / TESTNET | PoW helpers |

### Offline / library

| Layer | Network |
|-------|---------|
| `bitcoin-util-test.py` | None (encoding vectors) |
| secp256k1 / univalue | None |
| `check-symbols` / `check-security` | Inspects built binaries only |

---

## RPC-only modes and prioritization

| Mode | C++ | RPC scope | Use |
|------|-----|-----------|-----|
| Default | pass-only GTest+Boost | **`-A`** | Contributor gate |
| **`--quick`** | skip GTest/Boost | **`-A`** unless `--no-python` | Faster gate path |
| **`--no-python`** | per mode | skip | C++ only |
| **`--all`** | pass-only C++ | **`-all`** (pass tiers) | Bulk regression |
| **`--rpcfail`** | skip | **`-rpcfail`** | Diagnostic |
| **`rpc-tests.sh <name>`** | none | one script | Isolate |

**Deprioritized (not gate):** Bfail Debug/Retired, Efail, GTest `CachedWitnessesCleanIndex` (see **Appendix: Retired tests**).

---

## Coinbase maturity and mining acceleration

Authoritative: **`src/consensus/consensus.h`** `COINBASE_MATURITY = 720`; Python **`test_framework/util.py`** (must match).

| Helper | Role |
|--------|------|
| **`COINBASE_MATURITY`** | Constant [720] |
| **`coinbase_mature_tip(n)`** | `COINBASE_MATURITY + n` (replaces upstream `105` = 100+5) |
| **`mine_to_height`** | Exact tip for NU / doublespend |
| **`mine_until_node_has_mature_coinbase`** | One mature UTXO |
| **`ensure_mature_coinbase_or_skip`** | Tier B optional skip path |

### 720+ block acceleration options

| Approach | Status | Tradeoff |
|----------|--------|----------|
| **`initialize_chain` cache to `COINBASE_MATURITY+5`** | **Implemented** (2026-06-08) | One-time slow cache build; reuse across documented users and implicit default-**`setup_chain`** scripts -- see **`initialize_chain` cache** |
| **`mine_until_*` at test start** | Implemented | Per-test cost; correct |
| **`initialize_chain_clean` + incremental** | Tier A default | No stale cache |
| **Pre-mined datadir tarball / DB archive** | Not in tree | Fast CI restore; version NU/cache carefully |
| **Port `prioritisetransaction` to ZIP-317 style** | Retired | Zcash upstream replaced 1121-block legacy test |
| **Parallel Tier A `--jobs=N`** | Best-effort | Flake/hang risk |
| **Parallel GTest/Boost + RPC** | Default harness | ~307s vs ~15+ min serial |
| **`ZERO_MINE_COINBASE=1` (1000 blocks)** | Env opt-in | Slow hammer; not gate |
| **Regtest PoW (48,5)** | Consensus | Cannot shrink per-block Equihash solve without fork |

**Policy:** prefer helpers over hardcoded `generate(720)`; replace upstream `generate(100/105)` with `COINBASE_MATURITY` / `coinbase_mature_tip()` in ported scripts. Cache-specific inventory (users, tip-**200** debt, Bfail/Efail exposure): **`initialize_chain` cache** below. Other porting debt: **Obsolete upstream assumptions and porting debt** under **RPC harness details**. Active engineering queue: **Open work**.

---

## `initialize_chain` cache

Frozen regtest snapshot for fast multi-node wallet tests. **Defined in:** `qa/rpc-tests/test_framework/util.py` (`initialize_chain`, `initialize_chain_clean`, `initialize_datadir`, `rpc_cache_root`, `wait_for_daemon_rpc`, **`NU_TEST_ARGS`**).

Upstream assumed a **200-block** shared cache at **coinbase maturity 100**. Zero extends the snapshot to tip **`COINBASE_MATURITY + 5` = 725** so early coinbases from the 200-block distribution are mature.

### Cache location

**Canonical path:** **`<repo>/cache/node{0..3}/`** (gitignored).

Resolution order in **`rpc_cache_root()`**:

1. **`ZERO_RPC_CACHE_DIR`** if set (explicit override)
2. **`$BUILDDIR/cache`** if **`BUILDDIR`** is set
3. **`<repo>/cache`** derived from `qa/rpc-tests/test_framework/util.py` (works even when cwd is `qa/rpc-tests/`)

**`contrib/run-tests.sh`** and **`qa/pull-tester/rpc-tests.sh`** export **`ZERO_RPC_CACHE_DIR`** and **`BUILDDIR`** to the repo root so gate runs always share one cache.

Legacy **`qa/rpc-tests/cache/`** (from old cwd-relative behavior) is gitignored; safe to delete:

```bash
rm -rf qa/rpc-tests/cache
```

### Build (first time `cache/node0` is missing)

| Step | Detail |
|------|--------|
| Nodes | 4 regtest `zerod` processes |
| NU at build | **`-nuparams=6f76727a:1`** (Overwinter), **`-nuparams=7361707a:1`** (Sapling) -- same as **`NU_TEST_ARGS`** |
| Distribution | 2 rounds x 4 nodes x 25 blocks = **200** (upstream wallet layout; 25 ZER per node per round on regtest) |
| Maturity extension | Node 0 mines until tip **725** |
| Snapshot | Full datadir copied to **`cache/node{0..3}/`** |
| Marker | **`cache/CACHE_TIP`** written with expected tip (**725**) after build |
| Reuse | Each test: `shutil.copytree(cache/node{i} -> $TMPDIR/node{i})`; **`zero.conf`** ports rewritten |

First build is slow (200-block distribution + ~525 extra blocks for maturity). Later runs copy the snapshot and avoid re-mining.

**Not in the cache build:** **`-insightexplorer`**, **`-txindex`**, or other per-test **`extra_args`**. Those indexes are built at node startup when a script requests them.

### What the snapshot freezes

| Frozen state | Why it matters |
|--------------|----------------|
| Chain height (**725**) | **`blockchain.py`** asserts **`gettxoutsetinfo`** at **`CACHE_CHAIN_TIP`**; subsidy **2881.25 ZER** at that tip |
| NU activation heights baked in at build | Stale cache after **`NU_TEST_ARGS`** / **`-nuparams`** policy change |
| Which coinbases are mature | Stale cache after **`COINBASE_MATURITY`** change in C++ |
| Wallet UTXO layout from the 200-block distribution | Tests assuming empty wallets or exact low tips must use **`initialize_chain_clean`** |

**History:** **`734491cc6`** (2026-06-08) extended the cache to **`COINBASE_MATURITY + 5`**; **`blockchain.py`** still asserted tip **200** until aligned with **`CACHE_CHAIN_TIP`** and **`regtest_supply_at_height()`**.

**Default NU on `start_nodes`:** **`NU_TEST_ARGS`** (Overwinter + Sapling at height 1), same as cache build. Per-test **`extra_args`** can override (e.g. `wallet_overwintertx`, `p2p_nu_peer_management`).

### Who uses the cache

**Explicit (documented intent):**

| Script | Tier | How |
|--------|------|-----|
| `blockchain.py` | A | `initialize_chain` in `setup_chain` |
| `keypool.py` | A | `initialize_chain` (standalone `main`) |
| `httpbasics.py` | A | default `BitcoinTestFramework.setup_chain` |
| `rpcbind_test.py` | Efail | `initialize_chain` (standalone; chain tip irrelevant) |

**Implicit (default `setup_chain` -> `initialize_chain`):** any script that does **not** override **`setup_chain`** copies the warm cache. That is **~25** scripts today, including several Tier B pass scripts and Bfail/Efail diagnostics. They are not listed in **`testScriptsTierA`** as cache users, but they receive tip **725** on every run.

| Tier | Implicit cache (no `setup_chain` override) | Notes |
|------|---------------------------------------------|-------|
| B pass | `wallet_import_export`, `wallet_changeindicator`, `nodehandling`, `proxy_test` | Implicit cache; no tip-**200** assert |
| Bfail Debug | `wallet_addresses`, `rescan_import`, `reorg_limit`, `wallet_listnotes`, `wallet_sapling` | Default cache + tip **200** assert -- see **Tip 200 debt** and per-script debug sections |
| Bfail Debug | `wallet_listnotes`, `wallet_sapling`, `wallet_listreceived`, `mempool_reorg`, `mempool_tx_expiry`, `bip65-cltv-p2p`, `bipdersig-p2p`, `regtest_signrawtransaction` | See **Bfail and Efail cache exposure** below |
| Efail | `getblocktemplate_longpoll`, `getblocktemplate_proposals`, `smartfees`, `invalidblockrequest` | Comptool / long-chain scripts; tip **725** may skew timing assumptions |
| Other | `mempool_reorg`, `proton_test`, `script_test`, `zmq_test`, ... | Same default path |

**Explicit clean chain (`initialize_chain_clean` in `setup_chain`):** all other RPC scripts (**~50+**), including every Tier A script except the four cache users above, plus most Bfail scripts that override **`setup_chain`**.

### Recommended future cache adopters

Scripts that today call **`initialize_chain_clean`** then **`generate(720)`** (or equivalent) only to obtain mature coinbase could switch to default **`setup_chain`** after dropping tip-**200** asserts:

| Script | Tier | Today | Benefit |
|--------|------|-------|---------|
| `wallet.py` | Bfail Debug | clean + `generate(720)` x2 | Block-5 maturity bug; see **`wallet.py` debug** before cache adoption |
| `listtransactions.py` | B pass | clean + `generate(720)` | Same |
| `p2p_txexpiry_dos.py` | B pass | clean + `generate(720)` | Same |

**Already benefit implicitly:** `wallet_import_export`, `wallet_changeindicator`, `nodehandling`, `proxy_test` (default cache; no tip-**200** assert).

### When not to use cache

Prefer **`initialize_chain_clean`** + **`mine_until_*`** / **`COINBASE_MATURITY`** helpers when a test needs:

- A specific NU height plan (not default **`-nuparams` at 1**)
- Empty wallets or a low explicit bootstrap (e.g. **`getchaintips`**: **`CHAIN_BOOTSTRAP = 30`**)
- Insight Explorer indexes built only from txs the test creates (see below)
- Exact tip control for comptool or reorg depth

Avoid **`ZERO_MINE_COINBASE=1`** bulk **1000** in the gate.

### Insight tests and the cache

**`addressindex.py`**, **`spentindex.py`**, **`timestampindex.py`**, **`getrawtransaction_insight.py`** all use **`initialize_chain_clean`** and start nodes with:

```text
-debug -txindex -experimentalfeatures -insightexplorer
```

They mine to **`coinbase_mature_tip(5)`** (= **725**, same numeric tip as the cache) on a **fresh** chain, then create and index their own transactions.

**They should not share today's frozen cache:**

| Blocker | Detail |
|---------|--------|
| Index flags at build | Cache is built without **`-insightexplorer`** / **`-txindex`**; copying it would force a full index rebuild at startup or leave indexes empty |
| Wallet / tx layout | Cache carries the 4-node **200-block distribution** UTXO set; insight tests expect only txs they mine and send |
| Node count | Cache is **4** nodes; insight scripts use **3** |

A **separate** insight-enabled cache (built with the flag bundle above) is possible in theory but is not implemented. Until then, insight tests stay on **`initialize_chain_clean`**.

### Tip **200** debt (cache-induced failures)

**`initialize_chain`** leaves tip **725**. Any script that still asserts **200** without mining down fails the same way **`blockchain.py`** did before **`CACHE_CHAIN_TIP`**.

| Script | Tier | Pattern | Status |
|--------|------|---------|--------|
| `blockchain.py` | A | was **`gettxoutsetinfo`** at **200** / **1745 ZER** | **Fixed:** **`CACHE_CHAIN_TIP`** + **`regtest_supply_at_height()`** |
| `reorg_limit.py` | Bfail Debug | default cache + **`assert(getblockcount() == 200)`** | **Open:** clean chain + **`generate(200)`** or baseline-relative reorg -- **Open work** |
| `rescan_import.py` | Bfail Debug | default cache + **`assert_equal(getblockcount(), 200)`** | **Open:** same; **`ensure_mature_coinbase_or_skip`** removed |
| `wallet_addresses.py` | Bfail Debug | default cache + tip **200** | **Open:** see **height 200/201** and **Open work** |
| `wallet_listnotes.py` | Bfail Debug | default cache + **`assert_equal(200, getblockcount())`** | **Open:** clean chain + **`generate(200)`** |
| `wallet_sapling.py` | Bfail Debug | default cache + tip **200** | **Open:** same |
| `mempool_spendcoinbase.py` | B pass | warm cache tip **725** + **`COINBASE_MATURITY`** boundary math | **Fixed 2026-06-09** (merged from **`tests-debug`**) |
| `test_framework.py` | framework | default **`run_test`**: tip **200**, balance **`25*10`** | Dead template for scripts that override **`run_test`** |

**Not the same issue:** scripts that **`generate(200)`** on **`initialize_chain_clean`** (e.g. **`wallet_persistence.py`**, **`finalsaplingroot.py`**) choose tip **200** on purpose.

**Verified safe on cache (no tip assert):** **`blockchain.py`**, **`keypool.py`**, **`httpbasics.py`**, **`rpcbind_test.py`**, and implicit users without tip-**200** checks (e.g. **`wallet_import_export`**, **`wallet_changeindicator`**, **`nodehandling`**, **`proxy_test`**).

### Bfail and Efail cache exposure

Bfail and Efail lists are in **`testScriptsTierBFailDebug`**, **`testScriptsTierBFailRetired`**, and **`testScriptsExt`** in **`rpc-tests.sh`**. Cache affects only scripts on the **default** **`setup_chain`** path (or **`rpcbind_test`**'s explicit **`initialize_chain`**).

#### Bfail Debug -- cache can cause or mask failures

| Script | Cache path? | Cache-related risk |
|--------|-------------|-------------------|
| `wallet_addresses` | default | **Tip 200 assert** -- fails at **725** before address RPCs |
| `rescan_import` | default | **Tip 200 assert**; no maturity skip |
| `reorg_limit` | default | **Tip 200 assert** on split nodes |
| `wallet_listnotes` | default | **Tip 200 assert** -- fails immediately at **725** |
| `wallet_sapling` | default | **Tip 200 assert** -- same |
| `wallet_listreceived` | default | No tip assert; uses relative heights -- may run on cache; failures likely wallet/API, not cache |
| `mempool_reorg` | default | Starts at **725**; mines fresh blocks in **`run_test`** -- cache changes baseline, not necessarily a hard fail |
| `mempool_tx_expiry` | default | Comment assumes tip **199**; no assert -- cache skews expiry height math; failure mode unclear |
| `bip65-cltv-p2p`, `bipdersig-p2p` | default (comptool) | Comptool injects blocks atop existing chain -- **725** deep chain may affect sync; primary failures are PoW/consensus |
| `regtest_signrawtransaction` | default | No tip assert; pre-funded nodes from cache may help or skew balance checks |
| `addressindex`, `spentindex`, `timestampindex`, `getrawtransaction_insight` | **clean** | Not on cache |
| `wallet_persistence`, `rest`, `mempool_limit`, `mempool_nu_activation`, `rawtransactions`, `fundrawtransaction`, `signrawtransaction_offline`, `merkle_blocks`, `walletbackup`, `key_import_export`, `finalsaplingroot`, `mergetoaddress_*` | **clean** | Not on cache; failures are maturity porting, wallet RPC, or runtime |

#### Efail -- cache exposure

| Script | Cache path? | Cache-related risk |
|--------|-------------|-------------------|
| `rpcbind_test` | explicit | Tip irrelevant; cache is intentional |
| `getblocktemplate_longpoll`, `getblocktemplate_proposals` | default | Long tip **725** may change GBT polling timing vs empty chain |
| `smartfees` | default | Fee estimator history starts at **725**; may differ from upstream empty-chain bootstrap |
| `invalidblockrequest` | default (comptool) | Same comptool-on-deep-chain class as Bfail P2P scripts |
| `receivedby`, `pruning`, `p2p-acceptblock` | **clean** | Not on cache |

**Fix pattern for accidental cache users:** add **`setup_chain`** with **`initialize_chain_clean`**, or update assertions to **`CACHE_CHAIN_TIP`** / relative mining and align maturity math with **`COINBASE_MATURITY`**.

### Inspect cache tip (manual)

Frozen cache **cannot** be opened with bare **`zerod -datadir=cache/node0 -daemon`** alone: without **`NU_TEST_ARGS`**, the node may detect a large rewind and exit. Use the same flags as the harness:

```bash
killall zerod 2>/dev/null; sleep 1
src/zerod -datadir=cache/node0 -daemon \
  -nuparams=6f76727a:1 -nuparams=7361707a:1
src/zero-cli -datadir=cache/node0 getblockcount   # expect 725
src/zero-cli -datadir=cache/node0 stop
```

Or rely on **`wait_for_daemon_rpc`** / **`start_node`** -- do not call **`bitcoin-cli -rpcwait`** without a running **`zerod`**.

### Stale cache guards

An old **200-block** snapshot under **`<repo>/cache/`** survives across git tag checkouts and harness merges unless invalidated. Symptoms: **`blockchain.py`** asserts height **725** but **`gettxoutsetinfo`** reports **200**; **`mempool_spendcoinbase.py`** fails **`200 <= 720`**. Root cause: **`initialize_chain`** only rebuilt when **`cache/node0`** was missing; copying a pre-extension cache silently reused tip **200**.

#### Automatic (in harness)

**`initialize_chain`** (`util.py`) before reuse:

1. Reads **`cache/CACHE_TIP`** (written at end of cache build).
2. If **`cache/node0`** exists but marker is missing or value != **`COINBASE_MATURITY + 5`**, prints **`stale cache ... rebuilding`**, **`shutil.rmtree(cache_root)`**, then mines a fresh snapshot.
3. First test after a bad cache is slow (200-block distribution + ~525 extra blocks); later runs copy the warm snapshot.

**Gap (follow-up):** marker tracks tip height only. It does **not** yet invalidate when **`NU_TEST_ARGS`** changes but tip stays **725**. Planned: single **`CACHE_SCHEMA`** string (tip + NU fingerprint); bump when cache semantics change.

| Change | Invalidate cache? |
|--------|-------------------|
| **`COINBASE_MATURITY`** in C++ / **`util.py`** | Yes |
| Post-200 extension target (**`+ 5`**) | Yes |
| **`NU_TEST_ARGS`** / **`-nuparams`** policy | Yes (manual until **`CACHE_SCHEMA`**) |
| Regtest subsidy / founder rules affecting **`blockchain.py`** | Yes |
| Harness tier moves only | No |

#### Manual recovery

Force delete when auto-rebuild is not yet landed, you want a clean rebuild without running a test, or a stray legacy path exists:

```bash
rm -rf cache qa/rpc-tests/cache
killall zerod 2>/dev/null || true
```

Also delete after changing **`COINBASE_MATURITY`**, the post-200 extension target, **`NU_TEST_ARGS`**, or subsidy rules -- until **`CACHE_SCHEMA`** covers NU changes.

#### Release / platform checklist

After **`git checkout v4.0.1`** or **`git pull`** harness changes on a machine that already ran RPC tests (lazu, Windows):

```bash
killall zerod 2>/dev/null || true
# Optional force (auto-rebuild usually enough once CACHE_TIP is in tree):
# rm -rf cache qa/rpc-tests/cache

./qa/pull-tester/rpc-tests.sh blockchain.py   # first initialize_chain rebuilds if stale
```

Confirm tip before a full gate:

```bash
test -f cache/CACHE_TIP && cat cache/CACHE_TIP    # expect 725
```

Or inspect live (see **Inspect cache tip** below): **`getblockcount`** must be **725**.

**Rule:** never assume an existing **`cache/`** matches the checked-out harness. Branch and tag pushes do not clear local cache. **`ZERO_RPC_CACHE_DIR`** / gate scripts point at **`<repo>/cache`**; delete legacy **`qa/rpc-tests/cache/`** if present.

#### Test-side asserts (defense in depth)

Scripts that depend on warm cache should assert the tip they need (clear failure if marker logic regresses):

| Script | Guard |
|--------|-------|
| **`blockchain.py`** | **`CACHE_CHAIN_TIP`** + **`regtest_supply_at_height()`** |
| **`mempool_spendcoinbase.py`** | **`chain_height > COINBASE_MATURITY`** |

Scripts still asserting tip **200** on default **`setup_chain`** stay in **Bfail Debug** until ported to **`initialize_chain_clean`** + **`generate(200)`** or relative baselines.

### Harness RPC and cleanup (cache build and reuse)

| Symptom | Cause | Mitigation |
|---------|-------|------------|
| **`blockchain.py`**: left **725**, right **200**; **`mempool_spendcoinbase`**: **`200 <= 720`** | Stale **`cache/`** (pre-extension tip **200**) | **`rm -rf cache`** or let **`CACHE_TIP`** auto-rebuild; see **Stale cache guards** |
| **`JSONRPC error: Initializing...`** on first real RPC after startup | **`addnode`** / **`stop`** while **`zerod`** still in RPC warmup | **`wait_for_daemon_rpc`** uses **`bitcoin-cli -rpcwait getblockcount`** (300s cap) in **`start_node`** and cache build |
| Hang on **`bitcoin-cli -rpcwait`** with no **`zerod`** | Probe or stale script waiting forever | Start **`zerod`** first; same **`-nuparams`** as **`NU_TEST_ARGS`** |
| **`rewind ... shutting down`** opening frozen cache | Manual **`zerod`** without **`NU_TEST_ARGS`** | Match harness flags; see **Inspect cache tip** above |
| **`stop_nodes`** raises during failed-test cleanup | **`stop`** called while node still warming up | **`stop_nodes`** ignores **`JSONRPCException`** on **`stop`** |
| Flaky port / RPC after aborted run | Stray **`zerod`** or hung **`python3 -c ... -rpcwait`** | **`killall zerod`**; **`pkill -f "python3 -c"`** if needed before re-run |

Set **`PYTHON_DEBUG=1`** for per-node wait logging.

---

## Coin selection and difficulty adjustment (code map)

| Concern | Primary implementation |
|---------|------------------------|
| **Coin selection** | `src/wallet/wallet.cpp`: `CWallet::SelectCoins`, `SelectCoinsMinConf` (~4215-4415); used from `CreateTransaction` |
| **Mature coinbase filter** | `src/txmempool.cpp` (mempool); wallet `AvailableCoins` paths |
| **Difficulty / retarget** | `src/pow.cpp`: `GetNextWorkRequired`, `CalculateNextWorkRequired`; declared in `src/pow.h` |
| **Block header bits** | `src/pow.cpp` `CheckProofOfWork`, Equihash check |
| **RPC difficulty** | `src/rpc/misc.cpp` `getdifficulty` -> `GetDifficulty()` |
| **Tests** | `src/test/pow_tests.cpp`; GTest `test_pow.cpp`, `test_miner.cpp` |

---

## RPC harness details

### Coinbase maturity

Authoritative C++ value: **`src/consensus/consensus.h`** (`static const int COINBASE_MATURITY = 720`). Python tests import **`COINBASE_MATURITY`** from **`test_framework/util.py`** (must stay in sync). Upstream scripts assume 100 -- porting must adjust.

**`ZERO_MINE_COINBASE=1`:** `ensure_coinbase_utxos()` mines 1000 blocks when no mature coinbase exists. Without it, callers skip.

**Helpers:**

| Helper | Use |
|--------|-----|
| **`mine_to_height(node, nodes, target)`** | Exact tip before NU assertions; multi-step plans (e.g. **`4 * 25 + COINBASE_MATURITY`** in **`txn_doublespend`**) |
| **`mine_until_node_has_mature_coinbase`** | One mature coinbase on one node; no strict tip budget |
| **`ensure_mature_coinbase_or_skip`** | Same as **`mine_until_*`**, then bulk env path, else skip (not for Tier A gate) |
| **`has_coinbase_utxos`** | Diagnostics only |

Do not use **`mine_until_*`** when the script checks **`chaintip`** / **`nextblock`** after mining (batch steps can overshoot **`-nuparams`** heights). Use **`mine_to_height`** or explicit **`generate(need)`**.

### Script-specific notes

- **`getchaintips`:** `split=True` must connect only 0-1 and 2-3. `CHAIN_BOOTSTRAP = 30`. `mininode` magic must match `chainparams.cpp`.
- **`wallet_overwintertx`:** Bfail Retired (was Blossom-above-maturity NU walk).
- **`p2p_nu_peer_management`:** `mininode` must match `src/version.h` acceptance.
- **Tier A promotion:** main path runs without `skip_test` on defaults; add to **`testScriptsTierA`** and **`PYTHON_PASSING`** (keep in sync; use **`-list-csv`** to verify).

---

## Provenance and porting reference

### Where tests come from

| Component | Provenance | Zero-specific |
|-----------|------------|---------------|
| **`qa/pull-tester/rpc-tests.sh`** | Zcash/Bitcoin **`qa/pull-tester`** driver | Tier flags **`-A`/`-B`/`-E`/`-rpcfail`**, **`testScriptsTierA`**, pass/fail lists |
| **`qa/rpc-tests/*.py`** | Zcash 2.x RPC framework (upstream **`BitcoinTestFramework`**) | Per-script: **`-nuparams`** branch IDs, **720** maturity, **`zerod`**/**`zero-cli`** |
| **`contrib/run-tests.sh`** | Zero-local harness | Modes, **`test_filters.sh`**, Tier A parallel list |
| **`qa/zcash/full_test_suite.py`** | Zcash upstream stage driver | Reads **`test_filters.sh`**; Darwin skips ELF stages |
| **`qa/rpc-tests/test_framework/`** | Shared upstream + Zero edits | **`util.py`** maturity helpers; **`mininode.py`** Py3 / protocol version fixes |
| C++ **`src/test/*`**, **`src/wallet/gtest/`** | Bitcoin/Zcash unit tests | Equihash **(192,7)**, zeronode suites |

### C++ filter deduplication (item 2)

Single source: **`qa/zcash/test_filters.sh`**. **`contrib/run-tests.sh`** sources it; **`full_test_suite.py`** loads the same values at import. No mirrored string literals elsewhere.

### Network upgrades (NU) and **`NU_ARGS`**

Regtest NUs are not active at genesis unless set. **`-nuparams=<branchHex>:<height>`** schedules activation on regtest (see **`src/chainparams.cpp`** branch IDs).

Zero Tier A / P2P ports use:

```text
-nuparams=6f76727a:1   # Overwinter (Zero branch ID)
-nuparams=7361707a:1   # Sapling (Zero branch ID)
```

Some scripts use later heights (e.g. **`p2p_nu_peer_management`**: Overwinter 10, Sapling 15; **`wallet_overwintertx`**: Blossom via **`2bb40e60`**). Heights must stay **above** the maturity mining plan so the chaintip NU matches assertions.

### **723-block** maturity (example)

**`COINBASE_MATURITY = 720`**. To spend coinbases at heights **1, 2, 3**, tip must be **>= 723** (coinbase at height *h* matures at *h + 720*). Formula: **`MATURITY_BLOCKS + SPENDABLE_COINBASES`** (e.g. **`p2p_txexpiringsoon.py`**). Prefer **`mine_until_node_has_mature_coinbase`** (50-block batches) over hardcoded **`generate(720)`** when only one mature coinbase is needed.

### What **`generate(N)`** produces

**`generatetoaddress` / `generate(N)`** on regtest:

- Appends **N** valid proof-of-work blocks to the node's best chain.
- Each block's coinbase pays the node's mining address (and, on mainnet/testnet in fee range, a **development-fee** output).
- Returns the **N block hashes** (most recent last).
- Coinbase outputs are **immature** until **`COINBASE_MATURITY`** confirmations; **`listunspent`** omits immature generated UTXOs.

Frozen regtest cache: full reference in **`initialize_chain` cache** (location, build, users, implicit exposure, insight compatibility, Bfail/Efail risks, stale recovery). Summary: four explicit users; **~25** implicit via default **`setup_chain`**; **~50+** use **`initialize_chain_clean`**.

### Obsolete upstream assumptions and porting debt

Upstream Zcash/Bitcoin RPC tests assumed **coinbase maturity 100**, **200-block shared cache**, and **Bitcoin subsidy at height 200**. Zero uses **`COINBASE_MATURITY = 720`**, warm cache tip **725**, and regtest halving every **150** blocks. Tip-**200** asserts and cache-induced failures: **`initialize_chain` cache -> Tip 200 debt** and **Bfail and Efail cache exposure**.

#### Hardcoded **`generate(720)`** (maturity depth)

Prefer **`COINBASE_MATURITY`**, **`coinbase_mature_tip(n)`**, or **`mine_until_node_has_mature_coinbase`**. Mechanical unless the test asserts an exact NU height (then **`mine_to_height`**).

| Script | Tier | Current | Target |
|--------|------|---------|--------|
| `wallet.py` | Bfail Debug | `generate(720)` x2 | Fix node0 block-5 maturity first; then `COINBASE_MATURITY` helpers |
| `wallet_overwintertx.py` | Bfail Retired | `generate(720)` + `ensure_mature_*` | Retired from B pass; see **Appendix: Retired tests** |
| `wallet_shieldcoinbase.py` | B pass | `generate(720)` (800-UTXO phase) | `COINBASE_MATURITY`; keep **`generate(100)`** at L170 (UTXO count, not maturity) |
| `listtransactions.py` | B pass | `generate(720)` | `COINBASE_MATURITY` |
| `p2p_txexpiry_dos.py` | B pass | `generate(720)` | `COINBASE_MATURITY` or formula in file comments |
| `walletbackup.py` | Bfail Debug | `generate(720)` / `generate(721)` | **`COINBASE_MATURITY`** / **`COINBASE_MATURITY + 1`**; see **walletbackup debug** below |

**Already ported (reference):** `receivedby.py`, `mempool_limit.py`, `mempool_nu_activation.py`, `rest.py`, insight scripts (`coinbase_mature_tip(5)`), Tier A maturity paths (`ensure_mature_coinbase_or_skip`, `mine_until_*`, `txn_doublespend` height plan).

#### Upstream **`generate(101)`** bootstrap (maturity **100** era)

See **Bfail: upstream `generate(101)` bootstrap** below. **`shorter_block_times.py`** (Bfail Debug) uses **`generate(101)`**; fails without mature coinbase -- see **`shorter_block_times.py` debug**.

Harness RPC warmup and cache open pitfalls: **`initialize_chain` cache -> Harness RPC and cleanup**.

### Bfail: upstream `generate(101)` bootstrap

Upstream assumed coinbase maturity **100**, so **`generate(101)`** matured the first coinbase. On Zero (**720**), use **`generate(COINBASE_MATURITY + 1)`** after the first coinbase block (coinbase at height *h* matures at *h + 720*).

| Script | Bfail group | Status (2026-06-08) |
|--------|-------------|---------------------|
| `rawtransactions.py` | Debug | **Ported:** `generate(COINBASE_MATURITY + 1)` |
| `fundrawtransaction.py` | Debug | **Ported:** `generate(COINBASE_MATURITY + 1)` |
| `signrawtransaction_offline.py` | Debug | **Ported:** `generate(COINBASE_MATURITY + 1)` |
| `mergetoaddress_sapling.py` | Debug | **Ported:** helper `generate(COINBASE_MATURITY + 1)` |
| `mergetoaddress_mixednotes.py` | Debug | **Ported:** script-local `generate(102)` -> `generate(1)` + `generate(COINBASE_MATURITY + 1)` (does not use helper bootstrap) |
| `sprout_sapling_migration.py` | Retired | Still **`generate(101)`** |
| `turnstile.py` | Retired | Still **`generate(101)`** |

**Not the same issue (do not replace with 720):**

| Script | Pattern | Reason |
|--------|---------|--------|
| `bip65-cltv-p2p.py`, `bipdersig-p2p.py` | `generate(100)` | Comptool P2P bootstrap depth, not coinbase maturity |
| `reorg_limit.py` | `generate(100)` / `101` | Reorg depth |
| `wallet_treestate.py` | `generate(100)` then `COINBASE_MATURITY+1` | Immature-balance check; retired |
| `wallet_shieldcoinbase.py` | `generate(100)` at L170 | **100 UTXO count** for 50+50 shield test |

### `shorter_block_times.py` debug (Bfail Debug)

| Item | Detail |
|------|--------|
| Purpose | Regtest **Blossom** block spacing: Overwinter/Sapling at height **0**, Blossom at **106**; checks pre/post-Blossom rewards, `expiryheight`, and `z_sendmany` after activation |
| Why not Tier A | At **`generate(101)`** no coinbase is mature (**`COINBASE_MATURITY = 720`**). Former **`ensure_coinbase_utxos`** skip exited **0** without running assertions -- vacuous pass |
| Failure today | **`assert ensure_coinbase_utxos(...)`** without skip: needs mature coinbase at height **101**, impossible without breaking the Blossom height plan or **`ZERO_MINE_COINBASE=1`** bulk mine |
| Fix direction | Reschedule Blossom (e.g. **`2bb40e60:820`**), mine to **`coinbase_mature_tip(1)`** on clean chain, then run spacing assertions; or fund from cached mature UTXOs without mining past NU heights |

### `wallet.py` debug (Bfail Debug)

| Item | Detail |
|------|--------|
| Purpose | Core wallet RPC: balances, `listunspent` **`generated`**, send/receive, fee limits, `listtransactions`, multi-node sync |
| Failure (observed) | After node1 mines **720** blocks, node0 balance **19.01953125** ZER instead of **29** (50 - 21 sent) |
| Root cause | Node0's block **5** coinbase should be mature at tip **725** but balance math suggests it is not fully counted -- likely immature-coinbase / halving subsidy interaction on Zero regtest (block 5 subsidy still **10 ZER**; missing **~10 ZER** matches one coinbase) |
| Former behavior | Early **`return`** on mismatch skipped **~90%** of the script while reporting pass |
| Fix direction | Use **`mine_to_height`** / explicit tip after node0's fifth coinbase (**`4 + COINBASE_MATURITY + 1`**); assert with **`zero_regtest_subsidy_range`** not hardcoded **50**; verify **`listunspent(1)`** includes block-5 generated UTXO before send phase |

### Height **200** / **201** story (upstream cache bootstrap)

Several Zcash-era RPC tests treat chain height **200** as the standard harness sync point. That number is **not** a Zero NU activation height on today's regtest defaults.

| Concept | Upstream (Zcash/Bitcoin cache era) | Zero today |
|---------|-----------------------------------|------------|
| **How tip 200 is reached** | Shared **`initialize_chain`**: 2 rounds x 4 nodes x 25 blocks = **200**, then stop | Same **200-block distribution**, then node 0 mines to **`COINBASE_MATURITY + 5` = 725** before snapshot |
| **Coinbase maturity** | **100** blocks; coinbases from the distribution are spendable soon after block 200 | **720** blocks; distribution coinbases mature only after the extension to **725** |
| **What height 200 meant in tests** | End of the funded-wallet bootstrap; many scripts assert **`getblockcount() == 200`** as a harness sanity check | Scripts still asserting **200** fail immediately on warm cache (**725**) |
| **Height 201** | Mine **one** more block and re-check wallet RPCs at the next height | Same pattern in **`wallet_addresses.py`**: **200** then **`generate(1)`** -> **201** |

**`wallet_addresses.py` specifically:** comments say "height 200 -> Sapling" and "height 201 -> Sapling". On upstream Zcash regtest, Sapling was often scheduled **at or before** height 200 in the shared cache era, so **200/201** doubled as "post-bootstrap" and "Sapling active" checks. On Zero, default **`-nuparams=7361707a:1`** activates Sapling at block **1**, so **200** and **201** are both Sapling heights -- the test is really "**after the standard 200-block wallet layout**, shielded address RPCs work at two consecutive tips", not a Sprout-to-Sapling transition.

**Fix (preserve story):** **`initialize_chain_clean`**, mine **200**, run existing **`addr_checks('sapling')`** at **200** and **201**. **Do not** rely on warm cache without dropping or updating the tip assert.

### `wallet_addresses.py` debug (Bfail Debug)

| Item | Detail |
|------|--------|
| Purpose | **`z_getnewaddress`** / **`z_validateaddress`** / **`z_listaddresses`** for Sprout and Sapling at harness bootstrap heights **200** and **201** |
| Failure | Default **`setup_chain`** -> tip **725**; **`assert_equal(getblockcount(), 200)`** fails before address checks |
| Mask removed | None in script (hard assert only); tier move stops **`-B`** treating it as pass |
| Fix direction | **`setup_chain` -> `initialize_chain_clean`**, **`generate(200)`**, keep height **200/201** flow -- see **height 200/201** above |

### `rescan_import.py` debug (Bfail Debug)

| Item | Detail |
|------|--------|
| Purpose | **`z_importkey`** with **`rescan=yes`** on a peer updates Sapling balance after shield + mine |
| Failure | Tip **725** vs assert **200** on default cache |
| Mask removed | **`ensure_mature_coinbase_or_skip`** early **`return`** (could exit **0** after a failed tip check if execution reached it on a variant chain) |
| Fix direction | **`initialize_chain_clean`** + **`generate(200)`** (or **`initialize_chain`** only after dropping tip-**200** assert); **`get_coinbase_address`** now fails hard if no mature generated UTXO |

### `reorg_limit.py` debug (Bfail Debug)

| Item | Detail |
|------|--------|
| Purpose | Maximum accepted reorg (**99** vs **100** blocks) and minimum rejected reorg (**100** vs **101**) from a common starting tip |
| Failure | **`assert(getblockcount() == 200)`** on nodes 0 and 2 at tip **725** |
| Mask removed | None; failure was always visible once B pass ran the script |
| Fix direction | **`initialize_chain_clean`** + mine **200** on all nodes before split, **or** record **`BASE = getblockcount()`** and express all later asserts as **`BASE + N`** (reorg depths **99/100/101** stay the same) |

### `wallet_changeaddresses.py` debug (Bfail Debug)

| Item | Detail |
|------|--------|
| Purpose | Sapling **`z_sendmany`** change-address behavior: **`z_listreceivedbyaddress`**, **`z_listunspent`**, **`z_mergetoaddress`** |
| Why not Tier B pass | **`initialize_chain_clean`** only; without mining, **`ensure_mature_coinbase_or_skip`** returned early and the script exited **0** (no shield/spend assertions ran) |
| Failure today | **`get_coinbase_address`** raises if no mature generated UTXO on the clean chain |
| Fix direction | Mine to **`COINBASE_MATURITY + 1`** (or use **`mine_until_node_has_mature_coinbase`**) after **`initialize_chain_clean`**; keep Sapling-at-**1** **`NU_TEST_ARGS`** |

### `walletbackup.py` debug (Bfail Debug)

| Item | Detail |
|------|--------|
| Failure (pre-fix) | `assert_equal(total, 7340)` at end of mining phase; actual **2886.875** ZER |
| Root cause | Upstream assumed maturity **100** and **114 x 10** subsidy math; comment in script said 1140 but assert was **7340**. Zero **720** maturity and regtest subsidy change the aggregate total |
| Real gate | Backup/restore via `wallet.zero` and `importwallet` preserves per-node balances (`balance0`..`balance2`) |
| Fix | `generate(720)` -> **`COINBASE_MATURITY`**; `generate(721)` -> **`COINBASE_MATURITY + 1`**; total check -> **`assert_greater_than(total, 1000)`** + log |
| Runtime | Slow: miner node mines **~720** blocks twice (bootstrap + fee maturity); expect **15-25+ min** on macOS regtest |

### `rpcbind_test.py` (Efail)

Standalone script (not `BitcoinTestFramework`). Uses **`initialize_chain`** (documented cache user; tip irrelevant) then tests **`-rpcbind`** / **`-rpcallowip`**. See **`initialize_chain` cache**.

| Platform | Behavior |
|----------|----------|
| **Linux** (`/proc` present) | Full bind-socket inspection via `get_bind_addrs`; IPv4/IPv6 localhost, alt ports, non-loopback allow/deny |
| **macOS** | Reduced path: localhost RPC smoke only (`-rpcbind=127.0.0.1`, `getblockchaininfo`); skips `/proc` bind enumeration |

**Run alone (recommended, from repo root after build):**

```bash
./qa/pull-tester/rpc-tests.sh rpcbind_test
```

**Direct invoke (same cwd requirement for `cache/`):**

```bash
export PATH="$PWD/src:$PATH"
export BITCOIND="$PWD/src/zerod"
export BITCOINCLI="$PWD/src/zero-cli"
PYTHONPATH=qa/rpc-tests python3 qa/rpc-tests/rpcbind_test.py --srcdir src
```

**Keep datadir for debugging:** add `--nocleanup` (standalone only). Driver always cleans temp dirs.

### Founders reward / GBT / height **5000**

- **Zcash** used **20%** founders; **Zero** (post-Classic lineage) uses **7.5%** as **development fee** on mainnet in eligible heights (**`ZERO_COIN.md`**).
- **Regtest** sets **`nFeeStartBlockHeight = 5000`** so short RPC tests never hit fee-split coinbase logic.
- **`getblocktemplate.py`** checks **`coinbasetxn.required`** and tip **`finalsaplingroothash`** only -- not **`foundersreward`** (would require mining to 5000+).
- **`coinbasevalue`**: legacy GBT capability (total allowed coinbase value in zats). Zero **`getblocktemplate`** documents it but **does not expose** **`coinbasevalue`** ( **`coinbasetxn`** path only; see **`mining.cpp`** TODO).

### **`miner_tests`** and Equihash **(96,5)** vs **(192,7)** vs **(48,5)**

Three different **N,K** pairs appear in C++ tests and params. They are not interchangeable.

| Context | **N, K** | Source |
|---------|----------|--------|
| Zero mainnet | **192, 7** | `src/chainparams.cpp` production PoW |
| Zero regtest | **48, 5** | `src/chainparams.cpp` fast regtest PoW |
| Legacy **`miner_tests` `blockinfo[]`** | **96, 5** | Frozen upstream Bitcoin/Zcash-era vectors (precomputed block hashes + **`nSolution`** hex) |
| Zcash mainnet (historical reference) | **200, 9** | Not Zero; explains why upstream tests rarely matched production |
| Zcash testnet (historical reference) | **96, 5** | Same **N,K** as **`miner_tests` `blockinfo`** |

**`equihash_tests`** (Boost, in default pass filter) exercises Zero correctly:

- **(96,5)** solver/validator cases **return early** when **`Params(MAIN).nEquihashN != 96`** -- on Zero mainnet (**192**) they are a compatible no-op, not **(96,5)** coverage.
- Zero-specific cases validate **(192,7)** mainnet genesis (valid + corrupt **`nSolution`**) and **(48,5)** regtest genesis.

**`miner_tests`** (Boost, **excluded** in pass-only filter via **`qa/zcash/test_filters.sh`**) is a different problem:

| Item | Detail |
|------|--------|
| Suite | **`miner_tests`**, case **`CreateNewBlock_validity`** |
| Fixture | **`TestingSetup`** (in-memory **`CChainParams::MAIN`**) |
| Vectors | **`blockinfo[]`** -- dozens of **(96,5)** blocks with valid Equihash solutions for upstream params |
| Skip guard (current code) | `if (chainparams.GetConsensus().nEquihashN != 96) return;` |
| On Zero today | **`Params(MAIN).nEquihashN == 192`** -> condition true -> **always skips** with message that **`blockinfo`** is **(96,5)** |
| If run unfiltered | Skip is intentional; body would call **`CheckProofOfWork`** / **`CreateNewBlock`** with wrong **N,K** solutions and fail or assert |

**Why not run on mainnet (192,7) or regtest (48,5) as-is:**

- **(192,7)** and **(48,5)** need different solution lengths and validation paths than **(96,5)** **`blockinfo`** entries.
- The test does **not** call **`CBlock::solve()`**; it replays frozen **`nSolution`** blobs. Reusing **(96,5)** blobs on **(192,7)** or **(48,5)** params is invalid.
- Switching the case to **`Params(REGTEST)`** without new vectors still fails: Zero regtest is **(48,5)**, not **(96,5)**.

**Why not repoint Zero to (96,5):** regtest **(48,5)** is consensus in **`chainparams.cpp`** for faster RPC mining; mainnet **(192,7)** is production PoW. **`miner_tests` `blockinfo`** matches neither.

**Harness status:** **`BOOST_PASS_EXCLUDE='!miner_tests:...'`** in **`test_filters.sh`**. Default and **`--all`** never run the suite. **`--fail`** can run it; expect skip/no-op on Zero until new vectors exist.

**Path to enable (regtest target):**

1. Mine a short **(48,5)** regtest chain (or capture from **`generate`** on regtest).
2. Export block hashes + **`nSolution`** hex into a new **`blockinfo`** table for **(48,5)**.
3. Run the case under **`Params(REGTEST)`** (or a dedicated fixture).
4. Remove **`!miner_tests`** from pass-only exclude once the case exercises real code paths.

**`src/Makefile.test.include`:** **`alert_tests.cpp`** is not in **`BITCOIN_TESTS`** (obsolete P2P alert system). No separate Boost exclude for alerts -- suite is simply not linked.

### Comptool P2P tests

**`test_framework/comptool.py`** drives synthetic blocks through **`mininode`** **`TestNode`** instances:

- **`TestManager`** connects fake peers, injects **`TestInstance`** sequences from **`get_tests()`**.
- Blocks are built in Python (**`CBlock.solve()`** uses **`equihash.py`**), not via RPC **`generate`**.
- Failures (**`bip65-cltv-p2p`**, **`invalidblockrequest`**, **`bipdersig-p2p`**) are often **regtest PoW/consensus** mismatch (Python **(48,5)** solve vs node rules), not Tier A gate scripts.

Designed for **regtest**, not public testnet (no DNS seeds / checkpoint semantics).

### Tests aimed at public testnet

Few scripts target live testnet. **`turnstile.py`** (retired from driver) documents manual testnet steps. Most inventory assumes **local regtest** only.

### Insight tests and **720**

**`addressindex.py`**, **`spentindex.py`**, **`timestampindex.py`**, **`getrawtransaction_insight.py`** are in **Bfail Debug**. They use **`initialize_chain_clean`** (not the shared cache) -- see **`initialize_chain` cache -> Insight tests and the cache**.

**`-insightexplorer`:** pass on every node via `start_nodes` `extra_args` (already in each script's `setup_network`). Required bundle:

```text
-debug -txindex -experimentalfeatures -insightexplorer
```

Example from `addressindex.py` `setup_network`: `args = ('-debug', '-txindex', '-experimentalfeatures', '-insightexplorer')` then `start_nodes(3, tmpdir, [args] * 3)`. `-insightexplorer` turns on address/spent/timestamp index RPCs; `-txindex` and `-experimentalfeatures` are prerequisites in this tree.

Maturity: upstream `generate(105)` assumed maturity **100**. Zero scripts use **`coinbase_mature_tip(5)`** (= **725**, same tip as cache build policy) on a fresh chain. Insight indexing does not require 720; **funding transactions** do.

### Version-fork **alert** (historical)

Bitcoin **BIP34-era** mechanism: if a peer mines **51+ blocks** with **`nVersion`** above your **`VERSIONBITS`** threshold, **`-alertnotify=<cmd>`** runs ( **`forknotify.py`** tested this). Deprecated P2P alert system; unrelated to Zero NU activation (**`-nuparams`**).

| Project | Alert P2P tests | **`-alertnotify`** in init |
|---------|-----------------|---------------------------|
| Zero | Removed from RPC driver; **`alert_tests.cpp`** not built | Stub remains in **`init.cpp`** / **`alert.cpp`** |
| Zcash upstream | **`alert_tests.cpp`** | Still documented |
| Bitcoin Core | Alerts removed; fork warnings via other paths | GUI "alerts" are warnings, not P2P alerts |

**`forknotify.py`** / **`hardforkdetection.py`** deleted; alert wire types removed from **`mininode.py`**.

### Sprout retirement

See **Appendix: Retired tests**. Sprout RPC creation disabled since 2019 (**`zcrawkeygen`** table entry commented). **`wallet_treestate`** moved to Bfail Retired (was Tier B pass).

### Assetchain **`COINBASE_MATURITY`** (illustration)

Some external assetchain daemons expose **`extern int COINBASE_MATURITY`** default **100**, overridden at runtime via chain params. Mutable per-chain, unlike Zero's compile-time **720**.

### Tier A porting for **720** + NU

| Script | Maturity | NU / notes |
|--------|----------|------------|
| **`wallet_changeaddresses`** | Bfail Debug: **`get_coinbase_address`** | Sapling at **1**; **`initialize_chain_clean`** -- needs **`generate(COINBASE_MATURITY+1)`** or equivalent mine plan |
| **`wallet_changeindicator`** | **`mine_until_node_has_mature_coinbase`** | |
| **`txn_doublespend`** | **`generate(need)`** to height **820** (all four 25-block coinbases mature) | **`mine_until`** stops too early; default path submits doublespend to node2 **before** txid1/txid2 (Zero **`AcceptToMemoryPool`** rejects mempool conflicts, empty RPC error if reversed) |
| **`p2p_nu_peer_management`** | minimal chain | NU at 10 / 15 |
| **`shorter_block_times`** | Blossom spacing (Bfail Debug) | NU at 0 / 0 / 106; needs maturity plan -- see debug section |
| **`rewind_index`** | fake NU heights | branch ID regression |
| **`getchaintips`** | **`CHAIN_BOOTSTRAP=30`** | split topology fix |
| Others in Tier A | no coinbase spend | **`initialize_chain_clean`** (see **`initialize_chain` cache**) |

---

## Known failures, hangs, and crashes

Default and **`--all`** share the same C++ exclusions (**Known failures** below). **`--fail`** runs only those suites. **Do not** use **`--all`** as a merge gate (full RPC pass tiers and runtime); use **default + `--strict`**.

### C++ -- excluded by default

| Item | Count | Risk | Notes |
|------|-------|------|-------|
| GTest **`CachedWitnessesCleanIndex`** | 1 test | Fail | Reindex scenario needs incremental **`BuildWitnessCache`** (**`pcoinsTip`** anchors + **`ReadBlockFromDisk`**); not available in gtest harness |
| Boost **`miner_tests`** | 1 case (`CreateNewBlock_validity`) | Skip / no-op on Zero | **`blockinfo`** is **(96,5)**; Zero mainnet **(192,7)** -> `nEquihashN != 96` skip; need **(48,5)** regtest **`blockinfo`** to enable |

**Fixed 2026-06-09:** the encrypt-hang class (GTest **`WriteCryptedSaplingZkey*`**, Boost **`rpc_wallet_encrypted_wallet_sapzkeys`**) -- root cause was a wallet-DB re-entry deadlock in `CCryptoKeyStore::AddCryptedSaplingSpendingKey` (virtual `AddSaplingFullViewingKey` persisted during `EncryptWallet`/`LoadWallet`); this also deadlocked the **`encryptwallet`** RPC on any wallet holding Sapling keys. `CachedWitnessesEmptyChain/ChainTip/DecrementFirst` ported to Zero witness semantics.

**Mitigation (remaining):** Zero **(48,5)** **`blockinfo`** for **`miner_tests`**; coins-view harness for **`CachedWitnessesCleanIndex`**.

### RPC Tier Bfail groups

Authoritative arrays: **`testScriptsTierBFailDebug`**, **`testScriptsTierBFailRetired`** in `rpc-tests.sh`. **`-Bfail`** runs Debug then Retired.

#### Bfail Debug (porting / engineering)

| Subgroup | Scripts | Typical failure | Fix direction |
|----------|---------|-----------------|---------------|
| **Wallet / list** | `wallet`, `wallet_changeaddresses`, `wallet_listreceived`, `wallet_persistence`, `wallet_sapling`, `wallet_listnotes` | Balance / maturity / Sapling API drift | **`wallet.py`**: node0 block-5 maturity; **`wallet_changeaddresses`**: empty-chain vacuous pass fixed -- see debug sections |
| **NU / Blossom** | `shorter_block_times` | Maturity **720** vs Blossom at **106** | Reschedule NU or mine plan; see **`shorter_block_times.py` debug** |
| **Wallet / merge** | `mergetoaddress_sapling`, `mergetoaddress_mixednotes` | `z_mergetoaddress` async, maturity, note selection | `mine_until_*`; Sapling-only; check `mergetoaddress_helper.py` |
| **Insight** | `addressindex`, `spentindex`, `timestampindex`, `getrawtransaction_insight` | **`COINBASE_MATURITY` [720]** + `-insightexplorer` | **`initialize_chain_clean`** only (not shared cache); `coinbase_mature_tip(5)` |
| **Cache / tip 200** | `wallet_addresses`, `rescan_import`, `reorg_limit`, `wallet_listnotes`, `wallet_sapling` | Default **`setup_chain`** + tip **200** assert | Bfail Debug; **`initialize_chain_clean`** + **`generate(200)`** or baseline-relative reorg -- see **height 200/201** and per-script debug sections |
| **Mempool** | `mempool_limit`, `mempool_reorg`, `mempool_nu_activation`, `mempool_tx_expiry` | Maturity / NU heights | `COINBASE_MATURITY` mining; align `-nuparams`. **`mempool_spendcoinbase` -> B pass** (2026-06-09) |
| **Raw / REST** | `rawtransactions`, `rest`, `fundrawtransaction`, `signrawtransaction_offline` | Maturity bootstrap | `rawtransactions`, `fundrawtransaction`, `signrawtransaction_offline`: **`generate(COINBASE_MATURITY + 1)`** (2026-06-08); `rest` ported earlier |
| **Comptool P2P** | `bip65-cltv-p2p`, `bipdersig-p2p` | Python **(48,5)** vs node rules | `equihash.py` / comptool; or retire |
| **Other** | `merkle_blocks`, `walletbackup`, `key_import_export`, `regtest_signrawtransaction`, `finalsaplingroot` | Maturity / constants | **`walletbackup`**: wrong upstream total **7340** removed; uses **`COINBASE_MATURITY`**; restore equality is the gate |

**Wallet / merge detail:** `mergetoaddress_*.py` exercise shielded merge RPCs with multi-note inputs; failures are often immature coinbase, wrong note type (Sprout vs Sapling), or async `z_getoperationresult` timing. `mergetoaddress_sprout.py` is in **Retired**.

#### Bfail Retired (Sprout / manual testnet)

| Script | Reason |
|--------|--------|
| `mergetoaddress_sprout.py` | Sprout merge retired |
| `sprout_sapling_migration.py` | Sprout migration manual / deprecated |
| `turnstile.py` | Manual **testnet** procedure in comments; regtest ZIP209 |

#### Efail detail (selected)

| Script | Failure cause | Investigation |
|--------|---------------|---------------|
| **`smartfees.py`** | Fee estimator needs long tx history + mined blocks; upstream P2SH fee loop | Regtest subsidy/halving differs; may need hundreds of txs and mature UTXOs |
| **`receivedby.py`** | `listreceivedbyaddress` / immature balances | Ported: **`COINBASE_MATURITY`** maturing; passes address APIs; skips named-account section (Zero: accounts unsupported) |
| **`rpcbind_test.py`** | `-rpcbind` / `-rpcallowip` socket binding | Linux: full `/proc` bind checks; macOS: localhost RPC smoke only. Run alone: **`./qa/pull-tester/rpc-tests.sh rpcbind_test`** |
| **`p2p-acceptblock.py`** | Comptool block time / PoW | `int(time.time())` fix in tree; verify accept after reorg |
| **`invalidblockrequest.py`** | Comptool invalid block relay | Regtest PoW mismatch class |
| **`getblocktemplate_*`, `pruning.py`** | Long chain / GBT extensions | Runtime + Zero GBT differences |

### Fix and retest procedure

After a change, run the **narrowest** check first, then widen.

| Change area | Retest commands |
|-------------|-----------------|
| GTest wallet (`CachedWitnesses*`, `WriteCrypted*`) | `./src/zero-gtest '--gtest_filter=WalletTests.CachedWitnesses*'` (or zkeys filter); then default **`./contrib/run-tests.sh --strict`** |
| GTest filter in **`contrib/run-tests.sh`** / **`qa/zcash/full_test_suite.py`** | **`./contrib/run-tests.sh --strict`**; if touched **`full_test_suite.py`**, also **`./contrib/run-tests.sh --suite`** when practical |
| Boost pass-only exclusions | **`./src/test/test_bitcoin`** with the same **`--run_test=`** string as **`run-tests.sh`** |
| Single RPC script (any tier) | **`./qa/pull-tester/rpc-tests.sh <basename>`** (e.g. `rpcbind_test`, `receivedby`) |
| **`getchaintips`** (split topology / **`CHAIN_BOOTSTRAP`**) | **`./qa/pull-tester/rpc-tests.sh getchaintips`** |
| **`wallet_overwintertx`** (Bfail Retired) | **`./qa/pull-tester/rpc-tests.sh wallet_overwintertx`** or **`-Bfail`** |
| Tip-**200** Bfail port (`wallet_addresses`, `rescan_import`, `reorg_limit`, ...) | Script basename after **`initialize_chain_clean`** + **`generate(200)`** change; then **`-B`** or **`-all`** |
| **`tests-debug`** C++ merge (encrypt, **`CachedWitnesses*`**) | **`./contrib/run-tests.sh --fail --strict`**; then default **`--strict`** |
| Bulk RPC after tier moves | **`./contrib/run-tests.sh --all --strict`** -- refresh **Verification snapshot** |
| **`run-tests.sh`** background / **`wait`** | **`./contrib/run-tests.sh --no-python --strict`** then full **`./contrib/run-tests.sh --strict`** |
| Release-style gate | **`./contrib/run-tests.sh --strict`** |

---

## Verification snapshot

Record after harness changes (macOS, `./contrib/run-tests.sh --strict` unless noted):

| Run | Result | Wall time | Notes |
|-----|--------|-----------|-------|
| Default `(none) --strict` | **PASS** | **~211s** | macOS 2026-06-09; widened filters (encrypt class + 3 CachedWitnesses in gate); `blockchain.py` vs warm cache fixed |
| `--no-python --strict` | **PASS** | **~84s** | macOS 2026-06-09; GTest 206/206, Boost no errors |
| `mempool_spendcoinbase.py` | **PASS** | **~3s** | macOS 2026-06-09; warm cache; ported to 720 |
| Default `(none) --strict` | **PASS** | **~212s** | macOS 2026-06-08; GTest+Boost parallel with Tier A |
| `--quick --strict` | **PASS** | **~142s** | util/secp/univalue + Tier A RPC |
| `--all --strict` | **PASS** (stale) | **~1275s** | macOS 2026-06-08; **before** tip-**200** / vacuous-pass tier moves; **`-all`** now **33** invocations -- **re-run required** (**Open work**) |
| `--suite` | **PASS** | **~1306s** | `full_test_suite.py`; RPC stage = no-args (`-all`) |
| Bfail `COINBASE_MATURITY+1` ports | **PASS** | see below | macOS 2026-06-08, from repo root |
| `walletbackup.py` (post-fix) | **PASS** | **~85s** | total **2886.875**; restore/importwallet equality OK |
| Linux **`zero-400names`** on lazu (`ZeroLinux`) | **pending** | -- | Branch at **`f66b8b52b`**; rebuild + **`--strict`** not run (disk **~97%**, **~4 GB** free) |
| **`CachedWitnesses*` gtest port** | **WIP** (uncommitted) | -- | Local harness fix; still filtered in default gate |

**Bfail `COINBASE_MATURITY + 1` timings:** `rawtransactions` ~34s; `fundrawtransaction` ~54s; `signrawtransaction_offline` ~18s; `mergetoaddress_sapling` ~135s; `mergetoaddress_mixednotes` ~39s (after script-local maturity fix).

Tier inventory: `./qa/pull-tester/rpc-tests.sh -list-csv` or `qa/rpc-tests/test_tier_inventory.csv`

**Stale entries:** **`--all --strict`** row above predates Bfail moves and **`mempool_spendcoinbase`** promotion documented in **Open work**. Update result and wall time after **`./contrib/run-tests.sh --all --strict`**.

---

Tier A Overwinter/NU tests (**keep**): `rewind_index`, `p2p_nu_peer_management`. **`shorter_block_times`**: Bfail Debug (Blossom spacing vs **720** maturity). **`wallet_overwintertx`**: Bfail Retired (was multi-NU wallet walk with Sprout zaddrs).

---

## Appendix: Retired tests

Scripts remain in `testScripts` inventory but are excluded from pass tiers (`-A`, `-B`, `-E`, `--all`). Run only via **`-rpcfail`** / **`-Bfail`** or by basename.

| Script | Tier | Reason |
|--------|------|--------|
| `prioritisetransaction.py` | Bfail Retired | Legacy Bitcoin-era test: `generate(1121)`, obsolete tx **priority** field, 900-tx loop. Zcash master replaced with ZIP-317 unpaid-action test (`generate(100+n+2)`). Bitcoin Core uses `mining_prioritisetransaction.py` (MiniWallet). Not worth porting 1121 to `COINBASE_MATURITY`. |
| `wallet_treestate.py` | Bfail Retired | Sprout **`z_getnewaddress('sprout')`** / **`z_sendmany`** joinsplit treestate race. Zcash upstream kept the test but moved to Sapling-only (`z_getnewaddress()` without sprout, `-regtestshieldcoinbase`, ZIP-317 fees). Zero should not gate on Sprout treestate; port or drop. |
| `wallet_overwintertx.py` | Bfail Retired | Multi-NU wallet walk (Overwinter@10, Sapling@15, Blossom@850) with Sprout **`z_getnewaddress('sprout')`**, v4 **`overwintered`** / expiry RPCs. Overlap with **`p2p_txexpiringsoon`**, **`mempool_tx_expiry`**; skip paths on wrong chaintip. Run via **`-Bfail`** or basename only. |
| `mergetoaddress_sprout.py` | Bfail Retired | Sprout merge RPC retired |
| `sprout_sapling_migration.py` | Bfail Retired | Sprout migration; still uses upstream **`generate(101)`** bootstrap |
| `turnstile.py` | Bfail Retired | Sprout pool / ZIP209; **`generate(101)`** bootstrap; manual testnet notes in comments |
| `zcjoinsplit*` | removed from inventory | Sprout joinsplit RPC tests removed from driver |
| `wallet_shieldcoinbase_sprout` | removed from inventory | Sprout shieldcoinbase removed from driver |

**C++ deprioritized (not retired):** GTest **`WalletTests.CachedWitnessesCleanIndex`** -- needs coins-view + disk-block harness; excluded in `test_filters.sh`. (Encrypt-hang class fixed 2026-06-09; those tests are back in the gate.)

---

## Appendix: Alerts in product code (left in place)

P2P alert system is obsolete; **`alert_tests.cpp`** is not in default **`BITCOIN_TESTS`** build. Stubs remain for `-alertnotify` warnings and deprecation paths:

| File | Line(s) | Role |
|------|---------|------|
| `src/alert.h` | 21-22 | `mapAlerts`, `cs_mapAlerts` extern |
| `src/alert.cpp` | 26-27 | `mapAlerts` definition |
| `src/alert.cpp` | 173-237 | `CAlert::ProcessAlert` |
| `src/alert.cpp` | 250-252 | `CAlert::Notify` (`-alertnotify`) |
| `src/sendalert.cpp` | 57+ | `ThreadSendAlert` |
| `src/init.cpp` | 87 | `ThreadSendAlert` extern |
| `src/init.cpp` | 357 | `-alertnotify` help |
| `src/init.cpp` | 1151 | `fAlerts = GetBoolArg("-alerts", ...)` |
| `src/init.cpp` | 2197 | alert send thread |
| `src/main.h` | 183 | `extern bool fAlerts` |
| `src/main.cpp` | 98 | `fAlerts` definition |
| `src/main.cpp` | 2219, 2232, 2916 | `CAlert::Notify` for warnings |
| `src/main.cpp` | 5775-5776, 6252-6253 | relay `mapAlerts` to peers |
| `src/main.cpp` | 6901 | P2P `"alert"` message handler |
| `src/chainparams.h` | 71, 123 | `vAlertPubKey` / `AlertKey()` |
| `src/chainparams.cpp` | 138, 309, 463 | `vAlertPubKey = ParseHex("73B0")` |
| `src/deprecation.cpp` | 35, 45 | deprecation -> `CAlert::Notify` |
| `src/gtest/test_deprecation.cpp` | 128-130 | `-alertnotify` in deprecation test |
| `src/test/alert_tests.cpp` | (file) | source only; not default build |
| `src/rpc/net.cpp` | 461, 492 | `warnings` field in network info RPC |

Harness: `forknotify.py` / `hardforkdetection.py` removed; `mininode` alert wire types removed.

