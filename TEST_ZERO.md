# TEST_ZERO

Validation runbook for the Zero full node: **use cases first**, deep reference later.

**Scripts win.** Tier membership and basenames live only in `qa/pull-tester/rpc-tests.sh` arrays. Inventory CSV: `qa/rpc-tests/test_tier_inventory.csv` (regenerate with `-list-csv`). If this file disagrees with those, **the scripts win**.

**Prereqs:** [BUILD_ZERO.md -- Quick Start](BUILD_ZERO.md#2-quick-start) (toolchain, Python **3.10+**, `src/zerod` / test binaries). Task status: **TODO.md**.

---

## 1. Vision and methodology

Use a small set of entry points to validate the node: the contributor merge gate, optional bulk RPC coverage, and focused single-script or single-suite runs when extending the harness.

1. **Working gate.** `./contrib/run-tests.sh --strict` runs the current pass-only C++ suites plus Tier A RPC -- the supported merge check.
2. **Scripts win.** Tier membership lives in `rpc-tests.sh`; regenerate `-list-csv` when promoting a script into a working tier.
3. **Maturity / clean chain.** Regtest `COINBASE_MATURITY = 720`. Prefer `initialize_chain_clean` + explicit mine helpers when porting.
4. **Depth by layer.** Exclusive Boost for empty-wallet RPC gates; Ext/B scenarios for populated wallets; GTest for wallet units.
5. **Verify then promote.** When a basename run succeeds, update arrays and §3 in the same change set.
6. **No maintainer-only or DevWallet hrefs** in this public file.

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

**Environment:** Python **3.10+**. For direct `rpc-tests.sh`, set `PYTHON` / `BUILDDIR` if needed (see **Process -> Troubleshooting** below).

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

These tracks extend coverage; they do **not** block the working merge gate. Per-script notes: deep reference.

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

# Deep reference

Prefer **§2 Use cases** and **§3 Working inventory** for day-to-day work. Sections below cover interpretation, process, cache/maturity, per-script notes, and verification history.

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

### Tier engagement: verify is not promote (critique)

**Symptom (2026-07):** Five Insight RPC scripts (`addressindex`, `spentindex`, `timestampindex`, `rest`, `getrawtransaction_insight`) were adapted and documented **PASS** in **ExtTests.md**, yet remained in **`testScriptsTierBFailDebug`**. Default **`--strict`** / **`--all`** never ran them, so the gate looked healthy while explorer-critical coverage stayed optional. Re-run 2026-07-22 confirmed exit **0**; they were then moved to **Tier B pass** (**EXT-INSIGHT-FIXTURES**).

**Root cause (process, not harness bug):**

| Design | Effect |
|--------|--------|
| Pass tiers only in **`--strict`** / **`--all`** | Bfail / Efail / filtered GTest are invisible to the contributor gate by intent |
| **Bfail Debug** = "needs engineering" bin | Easy to leave a script there after it turns green |
| Docs / TODO say "PASS; next: promote" | Verification and array edits are separate steps; the second often slips |

This is not a different test runner and not "tests that cannot run." Individual `rpc-tests.sh <basename>` always works. The failure mode is **documented green + still FailDebug**.

**Rules going forward:**

1. **Same session as a verified PASS:** edit `qa/pull-tester/rpc-tests.sh` (remove from Fail* array, add to the matching pass array). Update tier-count comments and this file's inventory notes. Regenerating **`-list-csv`** is optional but useful.
2. **If not promoting yet:** write an explicit hold reason in the FailDebug list comment or ExtTests/TODO (e.g. "green but founders coverage incomplete -- SUPERSET"). "Next: promote" without a blocker is insufficient.
3. **Periodic check:** run FailDebug scripts that are suspected fixed; or scan for exit **0** while still listed under Bfail. Suggested one-liner inventory: `./qa/pull-tester/rpc-tests.sh -list-csv` then sample basenames under `Bfail,debug`.
4. **GTest quarantine** (`test_filters.sh`) is the same class: a ported/passing case must leave **`GTEST_PASS_EXCLUDE`** in the same change set, or stay documented under a postponed hub (e.g. **WitnessReindex.md** / **TST-WITNESS-REINDEX** for CleanIndex).

**Do not** treat Bfail as a parking lot for finished work. Diagnostic tiers exist so known-broken tests do not fake a green **`-B`**; they are not a substitute for engagement once fixed.

### Release candidate: validation and merge to `master`

Typical order for **`zero-400names`** (or any RC) -> **`master`** (remote default is **`master`**, not `main`):

1. **Clean tree** -- remove temporary paths; `git status` empty.
2. **Build** -- produce `src/zerod`, `zero-gtest`, `test_bitcoin`.
3. **Contributor gate** -- `./contrib/run-tests.sh --strict` (default mode: pass-only C++ + Tier A RPC).
4. **Optional widen** -- `./contrib/run-tests.sh --suite` (Linux: ELF stages); `./contrib/run-tests.sh --all` (bulk RPC); platform release scripts.
5. **Tag on the RC commit** -- `git tag -a v4.0.1 -m "..."`; rebuild on tag for clean `zerod --version` (see prior version-hash notes).
6. **Merge to `master`** -- open PR **`zero-400names` -> `master`** (or fast-forward after review) **after** steps 3--5 pass. **`master` should receive the tagged release commit** (merge then tag on `master`, or tag on branch then merge including tag).
7. **Push** -- `git push origin master` and `git push origin v4.0.1`.

**`--strict` policy:** Strongly recommended before tag/merge; **not an automatic hard block**. Maintainer decides whether to ship with a skipped, partial, or failed gate. Prefer a clean tree for a hash-free version string.

### 4.0.1 handoff (macOS -> Linux)

**Status (2026-06):** macOS ARM64 validated with **`--strict` PASS**. Linux rebuild on lazu is the **recommended** next validation before **`v4.0.1`** tag / merge -- not a process lockout.

| Step | macOS (done) | Linux lazu (`ZeroLinux`) |
|------|--------------|---------------------------|
| Branch | **`zero-400names`** | same; **`git pull --ff-only`** |
| Build | **`./zcutil/build.sh -j4`** | **`./zcutil/build.sh -j2`** (2 cores) |
| Contributor gate | **`./contrib/run-tests.sh --strict`** **PASS** ~211s (2026-06-09) | **Recommended** -- not run at RC tip yet |
| Widen | **`--suite`** skipped on Darwin (ELF stages N/A) | **`./contrib/run-tests.sh --suite`** recommended |
| Bulk RPC | **`--all --strict`** stale (pre tier moves); re-run optional | Optional after **`--strict`** |
| Host constraint | -- | Disk **~97%**, **~4 GB** free on **`/`** |

**macOS scope limits:** **`full_test_suite.py`** skips **`check-security`** / **`no-dot-so`** on Darwin. **`rpcbind_test.py`** uses localhost smoke only. Parallel Tier A (**`--jobs>1`**) can hang (**`paymentdisclosure`**); keep serial for meaningful gates.

**Linux commands** (after disk reclaimed):

```bash
cd /home/ubuntu/Work/ZK/ZeroLinux
git fetch origin && git checkout zero-400names && git pull --ff-only origin zero-400names
killall zerod 2>/dev/null || true
./zcutil/fetch-params.sh    # if needed
./zcutil/build.sh -j2
./contrib/run-tests.sh --strict    # recommended
./contrib/run-tests.sh --suite     # optional ELF + full rpcbind
```

**After Linux validation (or maintainer accept):** tag **`v4.0.1`**, merge to **`master`**, push (**steps 5-7** above). Update **Verification snapshot** Linux row.

### Platform validation beyond `--all`

**`--all`** only widens **pass-tier RPC** (A+B+E). It does **not** cover ELF release checks, Windows, packaging, or Bfail. Expected matrix:

| Layer | Linux (lazu / Ubuntu) | Windows (MXE cross from Linux; run on Win or wine where noted) |
|-------|------------------------|------------------------------------------------------------------|
| Build | `./zcutil/build.sh -j2` | `./zcutil/build-win.sh` (or `HOST=x86_64-w64-mingw32`) -> `zerod.exe` |
| Contributor gate | `./contrib/run-tests.sh --strict` | Prefer native Win or WSL2 Linux tree: same `--strict`. Cross-built `.exe` is compile smoke unless you have a Win runner. |
| ELF / hardening | `./contrib/run-tests.sh --suite` (**`check-security`**, **`no-dot-so`**, full **`rpcbind`**) -- **Darwin skips these** | N/A for PE; optional `checksec` on Linux host against ELF only |
| Extra security | `./contrib/run-tests.sh --build-checks --quick` or `make -C src check-security` | Document Authenticode later (**REL**); not automated |
| Bulk RPC | Optional `--all --strict` after tier moves | Same if harness runs |
| Packaging | `./zcutil/release-linux.sh` -> tarball + `.deb`; smoke `zerod --version` | Stage `.exe` + deps; no signed installer yet |
| Params | `./zcutil/fetch-params.sh` | Same paths under `%AppData%\ZcashParams` |
| Datadir smoke | `zerod -daemon`; `zero-cli getblockchaininfo` | `%AppData%\Roaming\zero` |
| Insight / reindex | Ops host only; not in `--all` | Same |

**RC bar (v4.0.1-style):** macOS `--strict` done; **Linux `--strict` + `--suite` strongly recommended**; Windows = **successful MXE build** at minimum, full `--strict` when a Windows/WSL runner exists. Maintainer may ship without hard-blocking on any layer.

### `nFeeStartBlockHeight` references (22)

Keep the name. All hits are the founders/dev carve height gate or the 10 -> 10.8 subsidy step -- not tx fees:

| Role | Files (count) |
|------|----------------|
| Declared | `consensus/params.h` (1) |
| Per-network constants | `chainparams.cpp` main **412300** / testnet **1** / regtest **`REGTEST_FOUNDERS_START`=1000 / `STOP`=1500** (3) |
| Address/script bounds | `chainparams.cpp` `GetFoundersReward*` (4) |
| Subsidy base 10.8 | `main.cpp` `GetBlockSubsidy` (1); tests `main_tests.cpp` (3) |
| Require founders out | `main.cpp` connect (1); `payments.cpp` / `budget.cpp` (2); `rpc/mining.cpp` `getblocksubsidy` (1); `metrics.cpp` (1) |
| Supply math | `rpczerowallet.cpp` `getsupply` (3) |
| Address fixture at fee-start | `gtest/test_foundersreward.cpp` (2) |

### `contrib/run-tests.sh` -- flags to re-check after parser changes

Same flags as **Reference -> modes** below; this table is the parser smoke checklist.

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

- **Boost:** **`src/test/*_tests.cpp`**; **`./src/test/test_bitcoin --run_test=SuiteName`**. RPC patterns: **`CallRPC`**, **`CheckRPCThrows`** (e.g. **`rpc_zeronode_tests.cpp`**). Prefer **`--run_test=`** (Boost 1.59+); older docs may show **`-t`**.
- **`getalldata` / zero_exclusive (S4–S7):** **`src/test/rpc_zero_exclusive_tests.cpp`**. Run: **`./src/test/test_bitcoin --run_test=rpc_zero_exclusive_tests`**. Populated wallet: **`./qa/pull-tester/rpc-tests.sh getalldata_scenario`** (Ext). Task text: **TODO** TST-01 / WAL-GETALLDATA-*.
- **GTest:** **`src/wallet/gtest/`**; **`./src/zero-gtest --gtest_filter=...`**
- **Python RPC:** **`qa/rpc-tests/*.py`**, **`BitcoinTestFramework`**, **`test_framework/util.py`**. Pull-tester: **`./qa/pull-tester/rpc-tests.sh <basename>`** (or **`-A` / `-B` / `-E` / `-all`**). Coverage probe: **`rpc_coverage_probe`**.

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

Commands and inventory: see **§2 Use cases** and **§3 Inventory** above.

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

**Fixed 2026-06-09 (now in gate):** GTest **`WriteCryptedSaplingZkey*`**, **`CachedWitnessesEmptyChain/ChainTip/DecrementFirst`**; Boost **`rpc_wallet_encrypted_wallet_sapzkeys`**.

**Alerts:** Bitcoin P2P alert tests are not compiled (**`alert_tests.cpp`** omitted from **`BITCOIN_TESTS`**). Product code may still expose **`-alerts`** / **`-alertnotify`** stubs; no harness exclusion needed.

**Shell notify hooks (`ENABLE_SYSTEM_COMMAND`):** Default builds do **not** run **`-blocknotify`**, **`-walletnotify`**, or **`-alertnotify`**. When a hook fires without **`ENABLE_SYSTEM_COMMAND`**, **`zerod`** logs a skip line (e.g. **`Block notification skipped:`**) and continues -- no subprocess, no **`::system()`**.

| Hook | Automated coverage (default build) | Gap |
|------|-----------------------------------|-----|
| **`-alertnotify`** | GTest **`DeprecationTest.AlertNotify`** | Covered: temp notify file **0** lines |
| **`-blocknotify`** | Manual regtest only | **TST-09**: marker file must stay empty after tip change; log must contain skip message |
| **`-walletnotify`** | None | **TST-09**: marker file unchanged after wallet tx; log skip message |

| Build | Command | Pass criterion |
|-------|---------|----------------|
| Default | **`./src/zero-gtest --gtest_filter=DeprecationTest.AlertNotify`** | Notify temp file **0** lines (hook skipped) |
| Opt-in shell | Reconfigure with **`CXXFLAGS="-DENABLE_SYSTEM_COMMAND"`**, rebuild, same filter | Temp file **1** line (sanitized deprecation text) |

**TST-09:** **`-alertnotify` closed** -- **`DeprecationTest.AlertNotify`** (default: 0 side-effect lines). Remaining: **`-blocknotify`** / **`-walletnotify`** marker tests on default builds. Full alert subsystem strip = **OPS-ALERT-STRIP** (postponed; **TODO**).

Manual check (either mode): regtest **`zerod`** with **`-blocknotify='echo %s >> /tmp/zero-block.log'`**, generate one block -- log appended **only** on opt-in build; default logs **"Block notification skipped"** in **`debug.log`**. See **BUILD_ZERO.md** section **4.6.1** (**OPS-SHELL**).

**Witness rebuild lockout (TST-08):** While **`fBuildingWitnessCache`** is true, wallet RPC dispatch must reject **`z_sendmany`** with **`RPC_BUILDING_WITNESS_CACHE` (-33)**, distinct from **-31** (witnesses never built). **Work item TST-08:** GTest that sets the flag and asserts **-33** on **`z_sendmany`**. Regtest mid-**`BuildWitnessCache`** is optional (harness gap same class as **`CachedWitnessesCleanIndex`**). Status: **TODO**. Reorg-length policy is a separate postponed track.

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

**Harness mapping:** default **`run-tests.sh`** -> **`-A`**; **`--all`** and **`-all`** on **`run-tests.sh`** are aliases for the same mode (both call **`rpc-tests.sh -all`**); **`rpc-tests.sh`** itself only accepts **`-all`** (single dash). **`--rpcfail`** -> **`-rpcfail`**; **`--suite`** -> **`full_test_suite.py`** -> no-args (**`-all`**). **`--jobs=N`** runs Tier A via **`PYTHON_PASSING`** list.

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
| **`mature_height(n)`** | `COINBASE_MATURITY + n` (replaces upstream `105` = 100+5) |
| **`mine_to_height`** | Exact tip for NU / doublespend |
| **`mine_until_mature`** | One mature UTXO |
| **`mature_or_skip`** | Tier B optional skip path |

### 720+ block acceleration options

| Approach | Status | Tradeoff |
|----------|--------|----------|
| **`initialize_chain` cache to `COINBASE_MATURITY+5`** | **Implemented** (2026-06-08) | One-time slow cache build; reuse across documented users and implicit default-**`setup_chain`** scripts -- see **`initialize_chain` cache** |
| **`mine_until_mature` at test start** | Implemented | Per-test cost; correct |
| **`initialize_chain_clean` + incremental** | Tier A default | No stale cache |
| **Pre-mined datadir tarball / DB archive** | Not in tree | Fast CI restore; version NU/cache carefully |
| **Port `prioritisetransaction` to ZIP-317 style** | Retired | Zcash upstream replaced 1121-block legacy test |
| **Parallel Tier A `--jobs=N`** | Best-effort | Flake/hang risk |
| **Parallel GTest/Boost + RPC** | Default harness | ~307s vs ~15+ min serial |
| **`ZERO_MINE_COINBASE=1` (1000 blocks)** | Env opt-in | Slow hammer; not gate |
| **Regtest PoW (48,5)** | Consensus | Cannot shrink per-block Equihash solve without fork |

**Policy:** prefer helpers over hardcoded `generate(720)`; replace upstream `generate(100/105)` with `COINBASE_MATURITY` / `mature_height()` in ported scripts. Cache-specific inventory (users, tip-**200** debt, Bfail/Efail exposure): **`initialize_chain` cache** below. Other porting debt: **Obsolete upstream assumptions and porting debt** under **RPC harness details**. Active engineering queue: **§5**.

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

**History:** **`734491cc6`** (2026-06-08) extended the cache to **`COINBASE_MATURITY + 5`**; **`blockchain.py`** still asserted tip **200** until aligned with **`CACHE_CHAIN_TIP`** and **`subsidy_range()`**.

**Default NU on `start_nodes`:** **`NU_TEST_ARGS`** (Overwinter + Sapling at height 1), same as cache build. Per-test **`extra_args`** can override (e.g. `wallet_overwintertx`, `p2p_nu_peer_management`).

### Who uses the cache

**Explicit (documented intent):**

| Script | Tier | How |
|--------|------|-----|
| `blockchain.py` | A | `initialize_chain` in `setup_chain` |
| `keypool.py` | A | `initialize_chain` (standalone `main`) |
| `httpbasics.py` | A | default `BitcoinTestFramework.setup_chain` |
| `rpcbind_test.py` | **Ext pass** | `initialize_chain` (standalone; chain tip irrelevant) |

**Implicit (default `setup_chain` -> `initialize_chain`):** any script that does **not** override **`setup_chain`** copies the warm cache. That is **~25** scripts today, including several Tier B pass scripts and Bfail/Efail diagnostics. They are not listed in **`testScriptsTierA`** as cache users, but they receive tip **725** on every run.

| Tier | Implicit cache (no `setup_chain` override) | Notes |
|------|---------------------------------------------|-------|
| B pass | `wallet_import_export`, `wallet_changeindicator`, `nodehandling`, `proxy_test` | Implicit cache; no tip-**200** assert |
| Bfail Debug | `wallet_addresses`, `rescan_import`, `reorg_limit`, `wallet_listnotes`, `wallet_sapling` | Default cache + tip **200** assert -- see **Tip 200 debt** and per-script debug sections |
| Bfail Debug | `wallet_listnotes`, `wallet_sapling`, `wallet_listreceived`, `mempool_reorg`, `mempool_tx_expiry`, `bip65-cltv-p2p`, `bipdersig-p2p`, `regtest_signrawtransaction` | See **Bfail and Efail cache exposure** below |
| Efail | `getblocktemplate_longpoll`, `getblocktemplate_proposals`, `smartfees`, `invalidblockrequest` | Comptool / long-chain scripts; tip **725** may skew timing assumptions |
| Other | `mempool_reorg`, `script_test`, `zmq_test`, ... | Same default path |

**Explicit clean chain (`initialize_chain_clean` in `setup_chain`):** all other RPC scripts (**~50+**), including every Tier A script except the four cache users above, plus most Bfail scripts that override **`setup_chain`**.

### Recommended future cache adopters

Scripts that today call **`initialize_chain_clean`** then **`generate(720)`** (or equivalent) only to obtain mature coinbase could switch to default **`setup_chain`** after dropping tip-**200** asserts:

| Script | Tier | Today | Benefit |
|--------|------|-------|---------|
| `wallet.py` | **Tier B pass** | clean + maturity mining | Sapling path; fee-aware miner balances (2026-07-24) |
| `listtransactions.py` | B pass | clean + `generate(720)` | Same |
| `p2p_txexpiry_dos.py` | B pass | clean + `generate(720)` | Same |

**Already benefit implicitly:** `wallet_import_export`, `wallet_changeindicator`, `nodehandling`, `proxy_test` (default cache; no tip-**200** assert).

### When not to use cache

Prefer **`initialize_chain_clean`** + **`mine_until_mature`** / **`COINBASE_MATURITY`** helpers when a test needs:

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

They mine to **`mature_height(5)`** (= **725**, same numeric tip as the cache) on a **fresh** chain, then create and index their own transactions.

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
| `blockchain.py` | A | was **`gettxoutsetinfo`** at **200** / **1745 ZER** | **Fixed:** **`CACHE_CHAIN_TIP`** + **`subsidy_range()`** |
| `reorg_limit.py` | Bfail Debug | default cache + **`assert(getblockcount() == 200)`** | **Open:** clean chain + **`generate(200)`** or baseline-relative reorg -- **§5** |
| `rescan_import.py` | Bfail Debug | default cache + **`assert_equal(getblockcount(), 200)`** | **Open:** same; **`mature_or_skip`** removed |
| `wallet_addresses.py` | Bfail Debug | default cache + tip **200** | **Open:** see **height 200/201** and **§5** |
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
| `wallet_persistence`, `mempool_nu_activation`, `rawtransactions`, `fundrawtransaction`, `signrawtransaction_offline`, `merkle_blocks`, `key_import_export`, `finalsaplingroot`, `mergetoaddress_*`, `txindex` | **clean** | Not on cache; failures are maturity/porting/wallet/RPC (see per-script debug). **`txindex`**: Py3 Decimal + subsidy asserts |
| *(promoted out of Bfail)* `addressindex`, `spentindex`, `timestampindex`, `getrawtransaction_insight`, `rest`, `walletbackup`, `mempool_limit` | **clean** | Now **Tier B pass**; still clean-chain only |

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
| **`blockchain.py`** | **`CACHE_CHAIN_TIP`** + **`subsidy_range()`** |
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
| **`mine_until_mature`** | One mature coinbase on one node; no strict tip budget |
| **`mature_or_skip`** | Same as **`mine_until_mature`**, then bulk env path, else skip (not for Tier A gate) |
| **`has_coinbase_utxos`** | Diagnostics only |

Do not use **`mine_until_mature`** when the script checks **`chaintip`** / **`nextblock`** after mining (batch steps can overshoot **`-nuparams`** heights). Use **`mine_to_height`** or explicit **`generate(need)`**.

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

**`COINBASE_MATURITY = 720`**. To spend coinbases at heights **1, 2, 3**, tip must be **>= 723** (coinbase at height *h* matures at *h + 720*). Formula: **`MATURITY_BLOCKS + SPENDABLE_COINBASES`** (e.g. **`p2p_txexpiringsoon.py`**). Prefer **`mine_until_mature`** (50-block batches) over hardcoded **`generate(720)`** when only one mature coinbase is needed.

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

Prefer **`COINBASE_MATURITY`**, **`mature_height(n)`**, or **`mine_until_mature`**. Mechanical unless the test asserts an exact NU height (then **`mine_to_height`**).

| Script | Tier | Current | Target |
|--------|------|---------|--------|
| `wallet.py` | **Tier B pass** | maturity + Sapling | Promoted 2026-07-24 |
| `wallet_overwintertx.py` | Bfail Retired | `generate(720)` + `mature_or_skip` | Retired from B pass; see **Appendix: Retired tests** |
| `wallet_shieldcoinbase.py` | B pass | `generate(720)` (800-UTXO phase) | `COINBASE_MATURITY`; keep **`generate(100)`** at L170 (UTXO count, not maturity) |
| `listtransactions.py` | B pass | `generate(720)` | `COINBASE_MATURITY` |
| `p2p_txexpiry_dos.py` | B pass | `generate(720)` | `COINBASE_MATURITY` or formula in file comments |
| `walletbackup.py` | **B pass** (promoted 2026-07-22) | was `generate(720)` / `721` | Ported to **`COINBASE_MATURITY`**; see **walletbackup** below |

**Already ported (reference):** `receivedby.py`, `mempool_limit.py`, `mempool_nu_activation.py`, `rest.py`, insight scripts (`mature_height(5)`), Tier A maturity paths (`mature_or_skip`, `mine_until_mature`, `txn_doublespend` height plan).

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
| Fix direction | Reschedule Blossom (e.g. **`2bb40e60:820`**), mine to **`mature_height(1)`** on clean chain, then run spacing assertions; or fund from cached mature UTXOs without mining past NU heights |

### `wallet.py` (Tier B pass; was Bfail Debug)

**Outcome 2026-07-24:** fee-aware **`miner_share`/`miner_range`**; Sprout size-limit + joinsplit stanzas replaced with Sapling taddr/zaddr flows; **`assert_raises_message`** for amount parse errors. Promoted to Tier B pass.


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
| Mask removed | **`mature_or_skip`** early **`return`** (could exit **0** after a failed tip check if execution reached it on a variant chain) |
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
| Why not Tier B pass | **`initialize_chain_clean`** only; without mining, **`mature_or_skip`** returned early and the script exited **0** (no shield/spend assertions ran) |
| Failure today | **`get_coinbase_address`** raises if no mature generated UTXO on the clean chain |
| Fix direction | Mine to **`COINBASE_MATURITY + 1`** (or use **`mine_until_mature`**) after **`initialize_chain_clean`**; keep Sapling-at-**1** **`NU_TEST_ARGS`** |

### `walletbackup.py` (Tier B pass; was Bfail Debug)

| Item | Detail |
|------|--------|
| Failure (pre-fix) | `assert_equal(total, 7340)` at end of mining phase; actual **2886.875** ZER |
| Root cause | Upstream assumed maturity **100** and **114 x 10** subsidy math; comment in script said 1140 but assert was **7340**. Zero **720** maturity and regtest subsidy change the aggregate total |
| Real gate | Backup/restore via `wallet.zero` and `importwallet` preserves per-node balances (`balance0`..`balance2`) |
| Fix | `generate(720)` -> **`COINBASE_MATURITY`**; `generate(721)` -> **`COINBASE_MATURITY + 1`**; total check -> **`assert_greater_than(total, 1000)`** + log |
| Promote | **2026-07-22** re-PASS (~80s); moved from `testScriptsTierBFailDebug` to `testScriptsTierBPass` (**TST-07** wallet half) |
| Runtime | ~**80s** on macOS after cache warm (historical note of 15-25 min was overstated for current script) |

### `txindex.py` debug (Bfail Debug)

Orphan Bitcoin-era script: was on disk but **not** in `rpc-tests.sh` until 2026-07-22. Pure **`-txindex`** (no insight). Complements insight suite; not a substitute for `getrawtransaction_insight.py`.

| Item | Detail |
|------|--------|
| Tier | **Bfail Debug** (inventoried); run: `./qa/pull-tester/rpc-tests.sh txindex` or `-Bfail` |
| Setup | `initialize_chain_clean`; node0 no txindex; nodes 1–3 `-txindex`; mines via `mature_height(5)` (**OK** for Zero maturity) |
| Failure (2026-07-22) | After mining: `required argument is not an integer` in `CTxOut.serialize` -- `amount = unspent[0]["amount"] * 100000000` is a **Decimal** under Py3 |
| Second bug (would hit next) | Asserts Bitcoin coinbase **`valueZat == 5000000000`** / **`value == 50`**; Zero regtest base subsidy is **10** ZER (`1000000000` zat) before halvings |
| Suggested fixes | (1) `amount = int(unspent[0]["amount"] * COIN)` or `int(round(...))`. (2) Assert against actual `unspent[0]` value / `regtest_subsidy_at_height`. (3) Prefer `ToMaxMoney`-safe ints; drop hardcoded 50. (4) Optional: assert node0 without `-txindex` cannot `getrawtransaction` while node3 can |
| Promote when | Green under `./qa/pull-tester/rpc-tests.sh txindex` then move to **Tier B pass** (next to insight scripts) |

### `rpcbind_test.py` (Ext pass; promoted 2026-07-24)

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

### Founders window / GBT

- **Zero** development fee is **7.5%** in eligible heights (**`ZERO_COIN.md`**).
- Regtest: **`REGTEST_FOUNDERS_START`/`STOP`** = **1000**/**1500** (`nFeeStartBlockHeight` = START). Maturity **720**.
- Coverage: **`founders_window.py`** (boundaries + Insight founders balance/txids). Cache tip (~725) stays single-vout.
- **`getblocktemplate.py`**: below START; **`coinbasetxn.required`** + **`finalsaplingroothash`** only.
- **`coinbasevalue`**: documented but not exposed (**`coinbasetxn`** path; **`mining.cpp`** TODO).

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

**`addressindex.py`**, **`spentindex.py`**, **`timestampindex.py`**, **`getrawtransaction_insight.py`**, **`rest.py`** are **Tier B pass** (2026-07-22). They use **`initialize_chain_clean`** (not the shared cache) -- see **`initialize_chain` cache -> Insight tests and the cache**. Pure **`txindex.py`** is **Bfail Debug** (see **`txindex.py` debug**).

**`-insightexplorer`:** pass on every node via `start_nodes` `extra_args` (already in each script's `setup_network`). Required bundle:

```text
-debug -txindex -experimentalfeatures -insightexplorer
```

Example from `addressindex.py` `setup_network`: `args = ('-debug', '-txindex', '-experimentalfeatures', '-insightexplorer')` then `start_nodes(3, tmpdir, [args] * 3)`. `-insightexplorer` turns on address/spent/timestamp index RPCs; `-txindex` and `-experimentalfeatures` are prerequisites in this tree.

Maturity: upstream `generate(105)` assumed maturity **100**. Zero scripts use **`mature_height(5)`** (= **725**, same tip as cache build policy) on a fresh chain. Insight indexing does not require 720; **funding transactions** do.

---

## Experimental and insight feature tests

Flag bundles below match **`qa/pull-tester/rpc-tests.sh`** and script `extra_args`. See **Required node flag bundles** and script tables in this section.

### Required node flag bundles

| Feature | Flags | Reindex? |
|---------|-------|----------|
| **Insight addressindex RPCs** | `-debug -txindex -experimentalfeatures -insightexplorer` | Yes on first enable |
| **`z_mergetoaddress`** | `-experimentalfeatures -zmergetoaddress` (+ often `-debug=zrpcunsafe`) | No |
| **REST HTTP** | `-rest` | No |
| **Payment disclosure** | `-experimentalfeatures -paymentdisclosure` | Varies |
| **Wallet encryption (dev)** | `-experimentalfeatures -developerencryptwallet` | N/A |

Insight RPCs require **both** `-experimentalfeatures` and `-insightexplorer` (`fExperimentalMode && fInsightExplorer` in `src/rpc/misc.cpp`).

### Insight RPC scripts (regtest)

All use **`initialize_chain_clean`**, **3 nodes**, maturity **`mature_height(5)`** (= 725). **Not** compatible with shared **`initialize_chain` cache** (indexes built at startup; cache has foreign wallet UTXOs).

| Script | RPCs / behavior exercised |
|--------|---------------------------|
| **`addressindex.py`** | `getaddresstxids`, `getaddressbalance`, `getaddressdeltas`, `getaddressutxos`, `getaddressmempool`; reorg via `invalidateblock`; restart persistence |
| **`spentindex.py`** | `getspentinfo`; enriched `getrawtransaction` vin/vout fields |
| **`timestampindex.py`** | `getblockhashes` (time ranges, logical times) |
| **`getrawtransaction_insight.py`** | Spent-index fields on `getrawtransaction` verbosity 1 |

Also: **`src/test/rpc_tests.cpp`** `rpc_insightexplorer` (disabled/enabled parameter checks).

Tier: **B pass** in `rpc-tests.sh` (promoted 2026-07-22). Run alone:

```bash
./qa/pull-tester/rpc-tests.sh addressindex
```

Pure **`-txindex`** (no insight) is separate: **`txindex.py`** in **Bfail Debug** -- see **`txindex.py` debug**.

### Experimental wallet RPC scripts

| Script | Flags | What it validates |
|--------|-------|-------------------|
| **`wallet_mergetoaddress.py`** | `-experimentalfeatures -zmergetoaddress` | Async merge; `z_getoperationresult`; transparent + shielded paths |
| **`mergetoaddress_sapling.py`** | via `mergetoaddress_helper.py` | Sapling note merge |
| **`mergetoaddress_mixednotes.py`** | `-experimentalfeatures -zmergetoaddress` | Rejects Sprout+Sapling same tx |
| **`wallet_changeaddresses.py`** | `-txindex -experimentalfeatures -zmergetoaddress` | Sapling change addresses with merge enabled |
| **`rescan_import.py`** | `-experimentalfeatures -zmergetoaddress` | Rescan + merge interaction |
| **`wallet_sapling.py`** | `-experimentalfeatures -zmergetoaddress` | Sapling wallet RPCs with merge flag |

`z_mergetoaddress` produces **on-chain** transactions (`CommitTransaction` -> mempool) unless test mode.

### Other experimental-adjacent tests

| Script | Notes |
|--------|-------|
| **`rest.py`** | `-rest`; Core-style `/rest/*` endpoints |
| **`wallet_paymentdisclosure.py`** | `-paymentdisclosure` if present in driver |

### GTest / Boost

| Suite | Case | Feature |
|-------|------|---------|
| `rpc_tests.cpp` | `rpc_insightexplorer` | Insight RPC disabled/enabled |
| `rpc_wallet_tests.cpp` | `rpc_z_mergetoaddress_*` | Merge RPC parameters |

Coverage gap: no RPC test for **auto `-consolidation`** (background `AsyncRPCOperation_saplingconsolidation`); Pirate **`consolidateaddress`** not in tree.

### Version-fork alert (historical)

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
| **`wallet_changeindicator`** | **`mine_until_mature`** | |
| **`txn_doublespend`** | **`generate(need)`** to height **820** (all four 25-block coinbases mature) | **`mine_until_mature`** stops too early; default path submits doublespend to node2 **before** txid1/txid2 (Zero **`AcceptToMemoryPool`** rejects mempool conflicts, empty RPC error if reversed) |
| **`p2p_nu_peer_management`** | minimal chain | NU at 10 / 15 |
| **`shorter_block_times`** | Blossom spacing (Bfail Debug) | NU at 0 / 0 / 106; needs maturity plan -- see debug section |
| **`rewind_index`** | fake NU heights | branch ID regression |
| **`getchaintips`** | **`CHAIN_BOOTSTRAP=30`** | split topology fix |
| Others in Tier A | no coinbase spend | **`initialize_chain_clean`** (see **`initialize_chain` cache**) |

---

## Known failures, hangs, and crashes

Default and **`--all`** share the same C++ exclusions (**Known failures** below). **`--fail`** runs only those suites. Prefer **default + `--strict`** for release validation; **`--all`** is bulk coverage, not a substitute for a focused gate. Tag/merge remains a maintainer decision.

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
| **Wallet / list** | `wallet_changeaddresses`, `wallet_listreceived`, `wallet_persistence`, `wallet_sapling`, `wallet_listnotes` | Balance / maturity / Sapling API drift | **`wallet.py`** promoted; others still Bfail -- see debug sections |
| **NU / Blossom** | `shorter_block_times` | Maturity **720** vs Blossom at **106** | Reschedule NU or mine plan; see **`shorter_block_times.py` debug** |
| **Wallet / merge** | `mergetoaddress_sapling`, `mergetoaddress_mixednotes` | `z_mergetoaddress` async, maturity, note selection | `mine_until_mature`; Sapling-only; check `mergetoaddress_helper.py` |
| **Insight** | *(promoted 2026-07-22)* `addressindex`, `spentindex`, `timestampindex`, `getrawtransaction_insight`, `rest` | -- | Now **Tier B pass**; see ExtTests |
| **txindex only** | `txindex` | Py3 Decimal `CTxOut` + Bitcoin **50**-ZER asserts | See **`txindex.py` debug**; promote to B pass after fix |
| **Experimental wallet** | `wallet_mergetoaddress`, `mergetoaddress_sapling`, `mergetoaddress_mixednotes`, `wallet_changeaddresses`, `rescan_import`, `wallet_sapling` | `-experimentalfeatures` + `-zmergetoaddress` where merge tests apply | See **Experimental and insight feature tests** below |
| **Cache / tip 200** | `wallet_addresses`, `rescan_import`, `reorg_limit`, `wallet_listnotes`, `wallet_sapling` | Default **`setup_chain`** + tip **200** assert | Bfail Debug; **`initialize_chain_clean`** + **`generate(200)`** or baseline-relative reorg -- see **height 200/201** and per-script debug sections |
| **Mempool** | `mempool_reorg`, `mempool_nu_activation`, `mempool_tx_expiry` | Maturity / NU heights | `COINBASE_MATURITY` mining; align `-nuparams`. **`mempool_spendcoinbase`** / **`mempool_limit`** -> B pass |
| **Raw** | `rawtransactions`, `fundrawtransaction`, `signrawtransaction_offline` | Maturity bootstrap | **`generate(COINBASE_MATURITY + 1)`** (2026-06-08) |
| **Comptool P2P** | `bip65-cltv-p2p`, `bipdersig-p2p` | Python **(48,5)** vs node rules | `equihash.py` / comptool; or retire |
| **Other** | `merkle_blocks`, `key_import_export`, `regtest_signrawtransaction`, `finalsaplingroot` | Maturity / constants | **`walletbackup`** promoted B pass 2026-07-22; **`finalsaplingroot`** = **TST-SAPLING-ROOT** |

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
| *(promoted)* **`getblocktemplate_longpoll.py`** | -- | Was Efail: `random_transaction` picked unfunded cache **node1**. Fixed by pinning funded node; Ext pass 2026-07-24. |
| **`p2p-acceptblock.py`** | Comptool block time / PoW | `int(time.time())` fix in tree; verify accept after reorg |
| **`invalidblockrequest.py`** | Comptool invalid block relay | Regtest PoW mismatch class |
| **`getblocktemplate_proposals.py`**, **`pruning.py`** | Long chain / GBT extensions | Runtime + Zero GBT differences |

*(Promoted to Ext pass 2026-07-24: **`receivedby`**, **`rpcbind_test`**, **`getblocktemplate_longpoll`** (funded-node pin).)*

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
| Recommended release validation | **`./contrib/run-tests.sh --strict`** (maintainer decides) |

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
| `--all --strict` | **PASS** (stale) | **~1275s** | macOS 2026-06-08; predates tip-**200** moves + Insight/`walletbackup`/Efail-green promotes; **`-all`** now **47** invocations -- **re-run required** (**§5**) |
| `txindex.py` | **FAIL** / Bfail Debug | **~22s** (2026-07-22) | Inventoried; Decimal `nValue` + Bitcoin 50-ZER asserts -- see **`txindex.py` debug** |
| `--suite` | **PASS** | **~1306s** | `full_test_suite.py`; RPC stage = no-args (`-all`) |
| Bfail `COINBASE_MATURITY+1` ports | **PASS** | see below | macOS 2026-06-08, from repo root |
| `walletbackup.py` (post-fix) | **PASS** / **B pass** | **~80s** (2026-07-22) | total **2886.875**; restore/importwallet equality OK; promoted from Bfail Debug |
| Linux **`zero-400names`** on lazu (`ZeroLinux`) | **pending** | -- | **v4.0.1 RC:** macOS **`--strict`** PASS 2026-06-09; lazu rebuild + **`--strict` recommended, not hard block** (disk **~97%**, **~4 GB** free). See **4.0.1 handoff** |
| **`CachedWitnesses*` (except CleanIndex)** | **in gate** | -- | CleanIndex still excluded (`test_filters.sh`) |

**Bfail `COINBASE_MATURITY + 1` timings:** `rawtransactions` ~34s; `fundrawtransaction` ~54s; `signrawtransaction_offline` ~18s; `mergetoaddress_sapling` ~135s; `mergetoaddress_mixednotes` ~39s (after script-local maturity fix).

Tier inventory: `./qa/pull-tester/rpc-tests.sh -list-csv` or `qa/rpc-tests/test_tier_inventory.csv`

**Stale entries:** **`--all --strict`** row above predates Bfail moves and **`mempool_spendcoinbase`** promotion documented in **§5**. Update result and wall time after **`./contrib/run-tests.sh --all --strict`**.

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

### Untiered files under `qa/rpc-tests/` (not missing coverage)

These `.py` files exist on disk but are **not** in A/B/E pass or fail arrays. They are **not** forgotten greens.

| Kind | Examples | Where documented | Action |
|------|----------|------------------|--------|
| **Helpers / base classes** | `mergetoaddress_helper.py`, `tx_expiry_helper.py`, `wallet_shieldcoinbase.py` (base for sapling/sprout) | Imported by tiered scripts; see merge/shield notes above | Keep out of tier arrays |
| **Removed / Sprout leftovers** | `zcjoinsplit.py`, `zcjoinsplitdoublespend.py`, `wallet_shieldcoinbase_sprout.py` | Appendix Retired (`removed from inventory`) | Do not re-add without a port plan |
| **Experimental alternate** | `wallet_mergetoaddress.py` | Experimental feature tests table (may overlap `mergetoaddress_*`) | Run by basename only until inventoried |
| **Build-flag optional** | `zmq_test.py`, `proton_test.py` | Appended to `testScripts` only if `ENABLE_ZMQ` / `ENABLE_PROTON` + deps | Not a separate fail tier |
| **Commented Ext inventory** | `script_test.py` (~40+ min) | Commented in `testScriptsExt`; basename unknown to driver until uncommented | If revived: **Efail** or slow Ext diagnostic -- **no Edebug tier** today; use Efail + comment, or basename-only |

There is **no** `Edebug` array. Slow or flaky Ext work stays in **`testScriptsExtFail`** (run `-Efail`) or commented out of `testScriptsExt`. Do not invent a third Ext bin without a harness change.

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
| `src/gtest/test_deprecation.cpp` | 126-151 | **`DeprecationTest.AlertNotify`**: **`-alertnotify`**; **`#ifdef ENABLE_SYSTEM_COMMAND`** (0 vs 1 line) |
| `src/test/alert_tests.cpp` | (file) | source only; not default build |
| `src/rpc/net.cpp` | 461, 492 | `warnings` field in network info RPC |

Harness: `forknotify.py` / `hardforkdetection.py` removed; `mininode` alert wire types removed.

