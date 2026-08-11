# TEST_ZERO

Validation runbook for the Zero full node.

**Scripts win.** Tier membership and basenames live only in `qa/pull-tester/rpc-tests.sh` arrays. Inventory CSV: `qa/rpc-tests/test_tier_inventory.csv` (regenerate with `-list-csv`). If this file disagrees with those, **the scripts win**.

**Prereqs:** [BUILD_ZERO.md](BUILD_ZERO.md) Quick Start (toolchain, Python **3.10+**, `src/zerod` / test binaries). Open items: **TODO.md**.

---

## 1. Vision and methodology

Use a small set of entry points to validate the node: the contributor merge gate, optional bulk RPC coverage, and focused single-script or single-suite runs when extending the harness.

1. **Working gate.** `./contrib/run-tests.sh --strict` runs the current pass-only C++ suites plus Tier A RPC -- the supported merge check.
2. **Scripts win.** Tier membership lives in `rpc-tests.sh`; regenerate `-list-csv` when promoting a script into a working tier.
3. **Maturity / clean chain.** Regtest `COINBASE_MATURITY = 720`. Prefer `initialize_chain_clean` + explicit mine helpers when porting.
4. **Depth by layer.** Exclusive Boost for empty-wallet RPC gates; Ext/B scenarios for populated wallets; GTest for wallet units.
5. **Verify then promote.** When a basename run succeeds, update arrays and §3 in the same change set.
Language: describe harness areas as **working** or **under development**. Reserve **pass** / **fail** for the outcome of a specific test run or case.

---

## 2. Use cases

| You want | Command |
|----------|---------|
| **Contributor merge gate** (working) | `./contrib/run-tests.sh --strict` |
| **Fast smoke** (util / secp / univalue / symbols) | `./contrib/run-tests.sh --quick --no-python --strict` |
| **Quick + Tier A RPC** | `./contrib/run-tests.sh --quick --strict` |
| **C++ suites only** (working filters) | `./contrib/run-tests.sh --no-python --strict` |
| **One RPC script** | `./qa/pull-tester/rpc-tests.sh <basename>` |
| **Tier A** (working gate RPC) | `./qa/pull-tester/rpc-tests.sh -A` |
| **Tier B pass** (working bulk) | `./qa/pull-tester/rpc-tests.sh -B` |
| **Ext pass** (working extended) | `./qa/pull-tester/rpc-tests.sh -E` |
| **All working RPC tiers (A+B+E)** | `./contrib/run-tests.sh --all --strict` or `./qa/pull-tester/rpc-tests.sh -all` |
| **Under-development RPC inventory** | `./qa/pull-tester/rpc-tests.sh -rpcfail` (or `-Bfail` / `-Efail`) |
| **Under-development C++ suites only** | `./contrib/run-tests.sh --fail` (not a merge gate) |
| **Multi-stage / ELF** (`full_test_suite.py`) | `./contrib/run-tests.sh --suite` (Darwin skips ELF stages) |
| **getalldata empty-wallet gates** (working) | `./src/test/test_bitcoin --run_test=rpc_zero_exclusive_tests` |
| **getalldata populated wallet** (working Ext) | `./qa/pull-tester/rpc-tests.sh getalldata_scenario` |
| **Export tier CSV** | `./qa/pull-tester/rpc-tests.sh -list-csv qa/rpc-tests/test_tier_inventory.csv` |

**Environment:** Python **3.10+**. For direct `rpc-tests.sh`, set `PYTHON` / `BUILDDIR` if needed (see harness scripts under `qa/`).

**Exit codes:** Prefer **`--strict`** so a non-zero exit means a specific step did not succeed. Without it, `run-tests.sh` may still exit **0** after a WARNING.

---

## 3. Working inventory (exact match to `rpc-tests.sh` / `test_tier_inventory.csv`)

Regenerate after every tier edit:

```bash
./qa/pull-tester/rpc-tests.sh -list-csv qa/rpc-tests/test_tier_inventory.csv
```

| Tier | Group | Count | How to run | Status |
|------|-------|------:|------------|--------|
| A | gate | 10 | `-A` / default `run-tests.sh` | **working** |
| B | pass | 29 | `-B` (`txn_doublespend` x2) | **working** |
| E | pass | 8 | `-E` | **working** |
| **A+B+E** | **pass** | **47** | **`-all`** / `run-tests.sh --all` | **working** |

### Tier A (`testScriptsTierA` / `PYTHON_PASSING`) -- working

blockchain, disablewallet, httpbasics, reindex, decodescript, keypool, paymentdisclosure, getchaintips, rewind_index, p2p_nu_peer_management

`contrib/run-tests.sh` **`PYTHON_PASSING`** (basenames, no `.py`) must match this list for `--jobs=N` only. Serial gate uses `rpc-tests.sh -A`.

### Tier B pass (`testScriptsTierBPass`) -- working

wallet_anchorfork, wallet_changeindicator, wallet_import_export, wallet_protectcoinbase, wallet_shieldcoinbase_sapling, wallet_nullifiers, wallet_1941, listtransactions, mempool_resurrect_test, mempool_spendcoinbase, mempool_limit, txn_doublespend, txn_doublespend --mineblock, zapwallettxes, proxy_test, signrawtransactions, nodehandling, rescan_startup, zkey_import_export, getblocktemplate, p2p_txexpiry_dos, p2p_txexpiringsoon, p2p_node_bloom, getrawtransaction_insight, rest, addressindex, spentindex, timestampindex, walletbackup

### Ext pass (`testScriptsExtPass`) -- working

invalidateblock, maxblocksinflight, rpc_coverage_probe, receivedby, rpcbind_test, getblocktemplate_longpoll, rpc_workqueue_full, getalldata_scenario

### C++ working filters (`qa/zcash/test_filters.sh`)

Default gate excludes two suites still under development (listed in §6). Everything else in GTest/Boost runs under `--strict` / `--no-python`.

---

## 4. Harness map (one screen)

| Layer | Entry | In default gate? |
|-------|-------|------------------|
| Util / vectors | `src/test/bitcoin-util-test.py` | yes (`--quick`) |
| secp256k1 / univalue | `make -C src ... check` | yes (`--quick`) |
| Symbols / security | `check-symbols`, `check-security` | yes if binary present; ELF also in `--suite` (Linux) |
| GTest | `src/zero-gtest` + working filter | yes |
| Boost | `src/test/test_bitcoin` + working filter | yes |
| Python RPC | `qa/pull-tester/rpc-tests.sh` | Tier A |
| Full suite | `qa/zcash/full_test_suite.py` | **`--suite` only** |

---

## 5. Under development (planning)

These tracks extend coverage; they do **not** block the working merge gate.

| Area | Scripts / item | Direction |
|------|----------------|-----------|
| Tip-200 vs warm cache | `wallet_addresses`, `rescan_import`, `reorg_limit`, `wallet_listnotes`, `wallet_sapling` | `initialize_chain_clean` + `generate(200)` or relative heights |
| Maturity / NU | `shorter_block_times`, `wallet`, `wallet_changeaddresses` | Mine plans / Blossom height |
| Pure txindex | `txindex` | Py3 Decimal + subsidy asserts |
| Bulk timing refresh | `--all --strict` | Re-record wall time for **47** working invocations |
| Parallel Tier A | `--jobs>1` | Optional throughput; keep serial for gates |
| GTest | `CachedWitnessesCleanIndex` | Reindex-style harness |
| Boost | `miner_tests` | (48,5) `blockinfo` (TST-05) |

**Promote rule:** when a basename run succeeds, move it into a working array in `rpc-tests.sh`, regenerate CSV, update §3.

---

## 6. Diagnostic and missing coverage (end)

Arrays and filters for scripts still under development. Run via `-Bfail`, `-Efail`, `-rpcfail`, or `--fail`. Outcome of each script is **pass** or **fail** only when you run that script.

| Tier | Group | Count | How to run |
|------|-------|------:|------------|
| Bfail | debug | 25 | `-Bfail` (first) |
| Bfail | retired | 6 | `-Bfail` (second) |
| Efail | fail | 5 | `-Efail` / part of `-rpcfail` |

### Bfail Debug (`testScriptsTierBFailDebug`) -- under development

shorter_block_times, wallet, wallet_changeaddresses, wallet_addresses, rescan_import, reorg_limit, wallet_listreceived, wallet_persistence, wallet_sapling, wallet_listnotes, mergetoaddress_sapling, mergetoaddress_mixednotes, rawtransactions, mempool_reorg, mempool_nu_activation, mempool_tx_expiry, merkle_blocks, fundrawtransaction, signrawtransaction_offline, key_import_export, bip65-cltv-p2p, bipdersig-p2p, regtest_signrawtransaction, finalsaplingroot, txindex

### Bfail Retired (`testScriptsTierBFailRetired`) -- under development / legacy

prioritisetransaction, wallet_treestate, wallet_overwintertx, mergetoaddress_sprout, sprout_sapling_migration, turnstile

### Efail (`testScriptsExtFail`) -- under development

getblocktemplate_proposals, pruning, smartfees, invalidblockrequest, p2p-acceptblock

### C++ suites outside the working gate (`qa/zcash/test_filters.sh`)

| Layer | Working-gate exclude | Run alone via |
|-------|----------------------|---------------|
| GTest | `-WalletTests.CachedWitnessesCleanIndex` | `--fail` or `--gtest_filter=WalletTests.CachedWitnessesCleanIndex` |
| Boost | `!miner_tests` | `--fail` or `--run_test=miner_tests` |

---

---

## 7. Interpreting results

### Exit accounting

- Without **`--strict`**, failures print **`WARNING`** but exit **0**. With **`--strict`**, exit **1** on any failure.
- **Exit 0 after `skip_test`** is a skip, not a pass.
- Some Boost cases return early (e.g. **(96,5)** Equihash vectors on **(192,7)** mainnet) -- they pass but do not prove that code path ran.

---

### Runner signals

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

