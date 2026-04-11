# TEST_ZERO

Validation runbook: commands, modes, harness behavior, known failures.

**Authoritative lists:** `contrib/run-tests.sh` (**`PYTHON_PASSING`**), `qa/pull-tester/rpc-tests.sh` (**`testScripts`**, **`testScriptsExt`**). If this file disagrees with those scripts, **the scripts win**.

**Prereqs:** [BUILD_ZERO.md -- Quick Start](BUILD_ZERO.md#2-quick-start) (toolchain, Python **3.10+**, produced binaries).

---

## Quick start by use case

| You want... | Command / next step |
|-----------|---------------------|
| **Default contributor gate** (pass-only C++ + Tier A RPC, serial) | `./contrib/run-tests.sh --strict` after building **`src/zerod`** |
| **Fast smoke** (no GTest/Boost/RPC) | `./contrib/run-tests.sh --quick --strict` |
| **C++ only** (no Python RPC) | `./contrib/run-tests.sh --no-python --strict` |
| **One Tier A RPC script** | `env PYTHON=python3 ./qa/pull-tester/rpc-tests.sh <basename>` |
| **Full multi-stage driver** (Tier B RPC, fail-fast) | `./contrib/run-tests.sh --full` |
| **Extended RPC bulk** (long run; many scripts) | `./contrib/run-tests.sh --fail` or `--all` (see **Reference -> modes**--not the default gate) |

**Environment:** Python **3.10+**; **`PYTHON`** and **`BUILDDIR`** for manual **`rpc-tests.sh`**--see **Process -> Troubleshooting**.

---

## Harness landscape

| Layer | Entry | Scope |
|-------|-------|-------|
| Util / vectors | `src/test/bitcoin-util-test.py` | Encoding, RPC-free |
| Libraries | secp256k1, univalue (`make -C src ... check`) | Third-party correctness |
| Symbols / security | `check-symbols`, `check-security` | Shipping constraints |
| GTest (`zero-gtest`) | Wallet, consensus-adjacent | Excluded suites in **Known failures** |
| Boost (`test_bitcoin`) | RPC, script, PoW (192,7), zeronode | Pass-only filters for (96,5) / alert drift |
| Python RPC | `qa/pull-tester/rpc-tests.sh` | Multi-node regtest; Tier A = `PYTHON_PASSING` |
| `full_test_suite.py` | Ordered stages, fail-fast | `--full`; Darwin skips ELF stages |

---

## Harness changelog (recent)

| Change | Location | Effect |
|--------|----------|--------|
| Split topology when **`split=True`** | **`qa/rpc-tests/getchaintips.py`** **`setup_network`** | Connect only **0-1** and **2-3** during the partition so the two halves actually fork (previously **0-2** / **1-2** bridged the split). |
| Shorter bootstrap | Same | **`CHAIN_BOOTSTRAP = 30`** for initial mining (was 200); **`join_network`** still avoids re-mining when the chain is already long enough. |
| Branch assertions | Same | **`expected_branchlen`** from **`shortTip['height'] - CHAIN_BOOTSTRAP`**; active height matches long chain after rejoin; accepts one or two tips per existing semantics. |
| Background wait / exit codes | **`contrib/run-tests.sh`** **`run_bg`** | Set **`BG_LAST_PID=$!`**; avoid **`$(run_bg ...)`** (subshell caused **`wait $pid`** to fail). GTest/Boost and Tier A parallel children wait on real child PIDs. |
| **`rescan_import` executable bit | Git index **`qa/rpc-tests/rescan_import.py`** | **`100755`** so **`rpc-tests.sh`** can execute the script (avoids **`Permission denied`** when checkout mode was **`100644`**). |
| **`wallet_changeaddresses` Zero port | **`qa/rpc-tests/wallet_changeaddresses.py`** | 2 nodes, Overwinter+Sapling at height 1, `-txindex`, `-experimentalfeatures` + `-zmergetoaddress`. Uses `ensure_mature_coinbase_or_skip` for 720-deep maturity. |
| **`wallet_changeindicator` + Sprout VK | **`qa/rpc-tests/wallet_changeindicator.py`**, **`src/wallet/wallet.cpp`** | `mine_until_node_has_mature_coinbase` at `run_test` start. `UpdateSproutNullifierNoteMapWithTx` skips when `GetSproutNoteNullifier` is empty (viewing key only)--avoids `assert(false)`. |
| **`serialize_script_num` (Python 3) | **`qa/rpc-tests/test_framework/blocktools.py`** | **`bytearray.append`** takes an **int** (**0-255**), not **`chr(...)`** (would raise **`TypeError`** on scripts that use **`serialize_script_num`**). |

**Open (harness):** **`--jobs>1`** Tier A RPC is **best-effort** only--**`paymentdisclosure`** has been observed **hung** under **`--jobs=4`** (macOS). No fix in-tree yet; use **serial** for the contributor gate. See **Parallel Tier A** under Reference.

---

## Verification snapshot

**Tier A scripts (allowlist order per `PYTHON_PASSING`):** `blockchain`, `disablewallet`, `httpbasics`, `reindex`, `rescan_import`, `rescan_startup`, `decodescript`, `keypool`, `paymentdisclosure`, `prioritisetransaction`, `wallet_treestate`, `wallet_anchorfork`, `getchaintips`, `rewind_index`, `wallet_overwintertx`, `wallet_changeaddresses`, `wallet_changeindicator`, `shorter_block_times`, `p2p_nu_peer_management`, `txn_doublespend`.

**Not gate-ready:** `--jobs>1` (hangs possible); extended/Tier B+C bulk; excluded C++ suites (see **Known failures**).

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

### `contrib/run-tests.sh` -- flags to re-check after parser changes

| Flag / input | Expected | Quick check |
|--------------|----------|-------------|
| *(default)* | Pass-only GTest + Boost + Tier A serial; **WARNING** if any step failed | `./contrib/run-tests.sh` |
| **`--strict`** | Exit **1** if any step failed | `./contrib/run-tests.sh --strict` |
| **`--quick`** | util, secp, univalue; optional symbol/security if **`zerod`** exists | `./contrib/run-tests.sh --quick` |
| **`--no-python`** | Skips RPC only | `./contrib/run-tests.sh --no-python` |
| **`--jobs=N`** | Tier A RPC parallel (**default pass-only only**; see **Parallel Tier A** below) | `./contrib/run-tests.sh --jobs=2 --strict` |
| **`--fail`** | Boost unfiltered; RPC **`-extended`** | inspect logs |
| **`--all`** | GTest + Boost unfiltered; RPC **`-extended`** | hang risk on wallet tests |
| **`--full`** | **`full_test_suite.py` only**; fails fast | `./contrib/run-tests.sh --full` |
| **`--build-checks`** | Extra **`make check-security`** at start | `./contrib/run-tests.sh --build-checks --quick` |
| **`PYTHON`**, **`LOG_DIR`**, **`ZERO_MINE_COINBASE`** | See **Reference** | top of **`contrib/run-tests.sh`** |

**Alignment:** Default Boost/GTest exclusions must match **`qa/zcash/full_test_suite.py`** (**`BOOST_PASS_EXCLUDE`**, GTest filter) when you change filters.

### Adding and extending tests

- **Boost:** **`src/test/*_tests.cpp`**; **`./src/test/test_bitcoin -t SuiteName`**. RPC patterns: **`CallRPC`**, **`CheckRPCThrows`** (e.g. **`rpc_zeronode_tests.cpp`**).
- **GTest:** **`src/wallet/gtest/`**; **`./src/zero-gtest --gtest_filter=...`**
- **Python RPC:** **`qa/rpc-tests/*.py`**, **`BitcoinTestFramework`**, **`test_framework/util.py`**.

Zeronode RPC coverage: **`rpc_zeronode_tests`**, **`rpc_zeronode_budget_tests`**.

### Troubleshooting

- **Blake2 / imports:** Python **3.10+** and **`hashlib.blake2b`**
- **`PYTHON` unset** when calling **`rpc-tests.sh` by hand:** use **`env PYTHON=python3 ./qa/pull-tester/rpc-tests.sh ...`**. **`contrib/run-tests.sh`** sets **`PYTHON`** via **`find_python3`**.
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
| **Default** | Pass-only filter | Pass-only exclusions | Tier A (**`PYTHON_PASSING`**) |
| **`--quick`** | Skip | Skip | Skip |
| **`--fail`** | Pass-only | Unfiltered | **`-extended`** |
| **`--all`** | Unfiltered | Unfiltered | **`-extended`** |
| **`--full`** | Via full suite only | Via full suite only | Via full suite only |
| **`--no-python`** | Per mode | Per mode | Skip |
| **`--jobs=N`** | -- | -- | Tier A RPC only; **default pass-only** (see **Parallel Tier A**) |


### `full_test_suite.py`

**Invoke:** **`python3 qa/zcash/full_test_suite.py`** or **`./contrib/run-tests.sh --full`**. Fails on first failed stage.

**Stage order:** `btest` -> `gtest` -> `sec-hard` -> `no-dot-so` -> `util-test` -> `secp256k1` -> `univalue` -> `rpc` (Tier B).

**Unfiltered:** **`--unfiltered`** or **`ZERO_FULL_SUITE_UNFILTERED=1`** removes GTest/Boost pass-only filters (hang/crash risk on excluded wallet tests).

**Darwin:** **`contrib/run-tests.sh`** passes **`--skip sec-hard --skip no-dot-so`** on Darwin because those stages target **ELF** / **`depends/` `.so`** layout--**release artifact checks**, not a claim that tests behave differently on macOS. Linux runs those stages when not skipped.

### Pass-only C++ filters (default + default full suite)

**GTest**

```text
--gtest_filter='-wallet_zkeys_tests.WriteCryptedSaplingZkey*:WalletTests.CachedWitnesses*'
```

**Boost**

```text
--run_test='!Alert_tests:!miner_tests:!rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys'
```

| Layer | Excluded (default) | Reason (summary) |
|-------|-------------------|------------------|
| GTest | **`WriteCryptedSaplingZkey*`** | **`CDB::Rewrite`** / wallet open -> **hang** |
| GTest | **`CachedWitnesses*`** | Harness / **`pcoinsTip`** / death test mismatch -> **fail** |
| Boost | **`Alert_tests`** | Not compiled / deprecated alerts |
| Boost | **`miner_tests`** | **(192,7)** vs upstream **(96,5)** assumptions |
| Boost | **`rpc_wallet_encrypted_wallet_sapzkeys`** | Same rewrite **hang** class as GTest encrypt tests |

**`equihash_tests`** stays in pass-only; interpretation: **Interpreting results -> Equihash**. List suites: **`./src/zero-gtest --gtest_list_tests`**, **`./src/test/test_bitcoin --list_content`**.

### RPC driver

| Invocation | Scripts |
|------------|---------|
| *(no args)* | All **`testScripts`** (Tier B)--order and names **only** in **`qa/pull-tester/rpc-tests.sh`**. |
| **`-extended`** | Tier B + **`testScriptsExt`**--same file. |
| **`rpc-tests.sh NAME`** | One match from those arrays |

Requires wallet-enabled build (**`ENABLE_BITCOIND`**, **`ENABLE_UTILS`**, **`ENABLE_WALLET`**). Config: **`qa/pull-tester/tests-config.sh`**.

### Tier A (contributor gate)

Script list: see **Verification snapshot** above. Common porting themes: **720** maturity, chaintip / NU height vs mining plan, `getchaintips` shape after rejoin, P2P `version` set.

**Parallel Tier A (`--jobs=N`, `N>1`):** Only when the RPC step is the **default Tier A** list (**`PYTHON_PASSING`**): not with **`--fail`** / **`--all`** (those use **`-extended`**), not with **`--no-python`**, not with **`--full`**. **`N=1`** (serial) is the path **CI and the contributor gate** assume.

**Reliability:** Parallel runs start **many `zerod` processes** (Equihash + RAM). That is **best-effort throughput**, not a supported merge gate: scripts can **hang or flake** under load (e.g. **`paymentdisclosure`** observed stuck with **`--jobs=4`** on one macOS run). If a run stalls, use serial (**omit `--jobs`**) or a **lower `N`**; confirm with **`test-logs/...-rpc-*.log`**. GTest/Boost in **`run-tests.sh`** are **not** parallelized by **`--jobs`** (only the Tier A RPC children).

---

## RPC harness details

### Coinbase maturity

Zero regtest: **`COINBASE_MATURITY` = 720** (`src/consensus/consensus.h`). Upstream scripts assume 100 -- porting must adjust.

**`ZERO_MINE_COINBASE=1`:** `ensure_coinbase_utxos()` mines 1000 blocks when no mature coinbase exists. Without it, callers skip.

**Helpers:** `has_coinbase_utxos`, `mine_until_node_has_mature_coinbase` (50-block steps), `ensure_coinbase_utxos` (bulk, env-gated), `ensure_mature_coinbase_or_skip` (incremental then bulk).

### Script-specific notes

- **`getchaintips`:** `split=True` must connect only 0-1 and 2-3. `CHAIN_BOOTSTRAP = 30`. `mininode` magic must match `chainparams.cpp`.
- **`wallet_overwintertx`:** Blossom activation set above post-maturity tip; chaintip stays Sapling.
- **`p2p_nu_peer_management`:** `mininode` must match `src/version.h` acceptance.
- **Tier B promotion:** main path runs without `skip_test` on defaults; add basename to `PYTHON_PASSING`.

---

## Known failures, hangs, and crashes

Default **pass-only** filters exist because of the items below. **Do not** use **`./contrib/run-tests.sh --all`** as a merge gate until the **encrypt/rewrite** class is resolved.

### C++ -- excluded by default

| Item | Risk | Notes |
|------|------|-------|
| GTest **`WriteCryptedSaplingZkey*`** | Hang | **`EncryptWallet`** -> **`CDB::Rewrite`** waits on **`mapFileUseCount`** while DB still open (**`src/wallet/gtest/test_wallet_zkeys.cpp`**, **`wallet/db.cpp`**) |
| GTest **`CachedWitnesses*`** | Fail / "failed to die" | **`BuildWitnessCache`** no-op when **`pcoinsTip`** null; **`EXPECT_DEATH`** pattern not matched by **`DecrementNoteWitnesses`** |
| Boost **`rpc_wallet_encrypted_wallet_sapzkeys`** | Hang | Same **rewrite** class over RPC |
| Boost **`miner_tests`** | Fail | Block assembly vs **(192,7)** |

**Mitigation directions:** Close wallet before rewrite or test-only persistence path (encrypt family). For CachedWitnesses: seed `CCoinsViewCache` / manual witnesses / replace death test.

### Fix and retest procedure

After a change, run the **narrowest** check first, then widen.

| Change area | Retest commands |
|-------------|-----------------|
| GTest wallet (`CachedWitnesses*`, `WriteCrypted*`) | `./src/zero-gtest '--gtest_filter=WalletTests.CachedWitnesses*'` (or zkeys filter); then default **`./contrib/run-tests.sh --strict`** |
| GTest filter in **`contrib/run-tests.sh`** / **`qa/zcash/full_test_suite.py`** | **`./contrib/run-tests.sh --strict`**; if touched **`full_test_suite.py`**, also **`./contrib/run-tests.sh --full`** when practical |
| Boost pass-only exclusions | **`./src/test/test_bitcoin`** with the same **`--run_test=`** string as **`run-tests.sh`** |
| Single Tier A RPC script | **`env PYTHON=python3 ./qa/pull-tester/rpc-tests.sh <basename>`** |
| **`getchaintips`** (split topology / **`CHAIN_BOOTSTRAP`**) | **`env PYTHON=python3 ./qa/pull-tester/rpc-tests.sh getchaintips`** |
| **`wallet_overwintertx`** (NU heights / maturity) | **`env PYTHON=python3 ./qa/pull-tester/rpc-tests.sh wallet_overwintertx`** |
| **`run-tests.sh`** background / **`wait`** | **`./contrib/run-tests.sh --no-python --strict`** then full **`./contrib/run-tests.sh --strict`** |
| Release-style gate | **`./contrib/run-tests.sh --strict`** |

