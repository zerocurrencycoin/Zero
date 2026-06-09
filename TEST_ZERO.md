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
| **Bulk RPC pass (A + B + E)** | `./contrib/run-tests.sh --all` or `rpc-tests.sh -all` |
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
| Split topology when **`split=True`** | **`qa/rpc-tests/getchaintips.py`** **`setup_network`** | Connect only **0-1** and **2-3** during the partition so the two halves actually fork (previously **0-2** / **1-2** bridged the split). |
| Shorter bootstrap | Same | **`CHAIN_BOOTSTRAP = 30`** for initial mining (was 200); **`join_network`** still avoids re-mining when the chain is already long enough. |
| Branch assertions | Same | **`expected_branchlen`** from **`shortTip['height'] - CHAIN_BOOTSTRAP`**; active height matches long chain after rejoin; accepts one or two tips per existing semantics. |
| Background wait / exit codes | **`contrib/run-tests.sh`** **`run_bg`** | Set **`BG_LAST_PID=$!`**; avoid **`$(run_bg ...)`** (subshell caused **`wait $pid`** to fail). GTest/Boost and Tier A parallel children wait on real child PIDs. |
| **`rescan_import` / `rescan_startup` executable bit | Git index **`qa/rpc-tests/rescan_*.py`** | **`100755`** (`git update-index --chmod=+x`); was **`100644`** -> **`Permission denied`** under **`rpc-tests.sh`**. |
| **`prioritisetransaction` retired** | **`rpc-tests.sh`** | Moved to **Bfail Retired** (legacy 1121-block Bitcoin priority test; Zcash/Bitcoin upstream replaced). |
| **`wallet_treestate` retired** | **`rpc-tests.sh`** | Moved to **Bfail Retired** (Sprout `z_sendmany` / joinsplit treestate; Zcash upstream uses Sapling-only). |
| **`initialize_chain` maturity** | **`util.py`** | Cache build extends to **`COINBASE_MATURITY + 5`**. |
| **Bfail subgroups** | **`rpc-tests.sh`** | **`testScriptsTierBFailDebug`** / **`Retired`**; **`-list-csv`**. |
| **`wallet_changeaddresses` Zero port | **`qa/rpc-tests/wallet_changeaddresses.py`** | 2 nodes, Overwinter+Sapling at height 1, `-txindex`, `-experimentalfeatures` + `-zmergetoaddress`. Uses `ensure_mature_coinbase_or_skip` for 720-deep maturity. |
| **`wallet_changeindicator` + Sprout VK | **`qa/rpc-tests/wallet_changeindicator.py`**, **`src/wallet/wallet.cpp`** | `mine_until_node_has_mature_coinbase` at `run_test` start. `UpdateSproutNullifierNoteMapWithTx` skips when `GetSproutNoteNullifier` is empty (viewing key only)--avoids `assert(false)`. |
| **`serialize_script_num` (Python 3) | **`qa/rpc-tests/test_framework/blocktools.py`** | **`bytearray.append`** takes an **int** (**0-255**), not **`chr(...)`** (would raise **`TypeError`** on scripts that use **`serialize_script_num`**). |

**Open (harness):** **`--jobs>1`** Tier A RPC is **best-effort** only--**`paymentdisclosure`** has been observed **hung** under **`--jobs=4`** (macOS). No fix in-tree yet; use **serial** for the contributor gate. See **Parallel Tier A** under Reference.

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
--gtest_filter='-wallet_zkeys_tests.WriteCryptedSaplingZkey*:WalletTests.CachedWitnesses*'
```

**Boost**

```text
--run_test='!miner_tests:!rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys'
```

| Layer | Excluded (default) | Reason (summary) |
|-------|-------------------|------------------|
| GTest | **`WriteCryptedSaplingZkey*`** | **`CDB::Rewrite`** / wallet open -> **hang** |
| GTest | **`CachedWitnesses*`** | Harness / **`pcoinsTip`** / death test mismatch -> **fail** |
| Boost | **`miner_tests`** | **`CreateNewBlock_validity`**: **`blockinfo`** **(96,5)** vs Zero **(192,7)** MAIN -> skip via `nEquihashN != 96`; excluded in **`test_filters.sh`** |
| Boost | **`rpc_wallet_encrypted_wallet_sapzkeys`** | Same rewrite **hang** class as GTest encrypt tests |

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

**Deprioritized (not gate):** Bfail Debug/Retired, Efail, C++ encrypt hang suites (Sapling-era; see **Appendix: Retired tests**).

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
| **`initialize_chain` cache to `COINBASE_MATURITY+5`** | **Implemented** (2026-06-08) | One-time slow cache build; reuse across **3** RPC scripts only -- see **RPC harness -> `initialize_chain` cache** |
| **`mine_until_*` at test start** | Implemented | Per-test cost; correct |
| **`initialize_chain_clean` + incremental** | Tier A default | No stale cache |
| **Pre-mined datadir tarball / DB archive** | Not in tree | Fast CI restore; version NU/cache carefully |
| **Port `prioritisetransaction` to ZIP-317 style** | Retired | Zcash upstream replaced 1121-block legacy test |
| **Parallel Tier A `--jobs=N`** | Best-effort | Flake/hang risk |
| **Parallel GTest/Boost + RPC** | Default harness | ~307s vs ~15+ min serial |
| **`ZERO_MINE_COINBASE=1` (1000 blocks)** | Env opt-in | Slow hammer; not gate |
| **Regtest PoW (48,5)** | Consensus | Cannot shrink per-block Equihash solve without fork |

**Policy:** prefer helpers over hardcoded `generate(720)`; replace upstream `generate(100/105)` with `COINBASE_MATURITY` / `coinbase_mature_tip()` in ported scripts.

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
- **`wallet_overwintertx`:** Blossom activation set above post-maturity tip; chaintip stays Sapling.
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

### **`initialize_chain`** cache

**Defined in:** `qa/rpc-tests/test_framework/util.py` (`initialize_chain`, `initialize_chain_clean`, `initialize_datadir`).

Only **`initialize_chain`** reads/writes the shared frozen datadir. **`initialize_chain_clean`** (used by **~78** other RPC scripts) starts from empty genesis and mines per test -- no shared cache.

#### Path and cwd

Frozen datadir is **relative to process cwd**, not under `qa/rpc-tests/`:

```text
<cwd>/cache/node{0..3}/
```

| Invocation | Typical cache location |
|------------|------------------------|
| `./contrib/run-tests.sh` from repo root | **`<repo>/cache/`** (gitignored at repo root) |
| `./qa/pull-tester/rpc-tests.sh <script>` from repo root | same |
| Script run from another cwd | **`<that-cwd>/cache/`** |

**Verified:** `./qa/pull-tester/rpc-tests.sh keypool` from repo root creates **`<repo>/cache/node{0..3}/`** only; **`qa/rpc-tests/cache/`** is never created.

#### Build (first time `cache/node0` is missing)

| Step | Detail |
|------|--------|
| Nodes | 4 regtest `zerod` processes |
| NU at build | `-nuparams=6f76727a:1` (Overwinter), `-nuparams=7361707a:1` (Sapling) |
| Distribution | 2 rounds x 4 nodes x 25 blocks = **200** (upstream wallet layout; 25 ZER per node per round on regtest) |
| Maturity extension | Node 0 mines until tip **`COINBASE_MATURITY + 5` = 725** |
| Snapshot | Full datadir copied to **`cache/node{0..3}/`** |
| Reuse | Each test: `shutil.copytree(cache/node{i} -> $TMPDIR/node{i})`; **`zero.conf`** ports rewritten |

First build is slow (200-block distribution + ~525 extra blocks for maturity). Later cache users copy the snapshot and avoid re-mining.

#### What the snapshot freezes

| Frozen state | Why it matters |
|--------------|----------------|
| Chain height (**725** after current build policy) | Tests that assert an older tip (e.g. **200**) fail against a warm cache |
| NU activation heights baked in at build | Stale cache after `-nuparams` policy change |
| Which coinbases are mature | Stale cache after **`COINBASE_MATURITY`** change in C++ |
| Wallet UTXO layout from the 200-block distribution | Tests assuming empty wallets must use **`initialize_chain_clean`** |

#### Callers by tier (only three scripts)

| Tier | Script | Uses cache? | Notes |
|------|--------|-------------|-------|
| **A** | `blockchain.py` | Yes | **`gettxoutsetinfo`** asserts height **200**, **1745 ZER**, **200** txouts (Zero subsidy math at block 200). Warm cache tip is **725** -- assertions fail until updated (e.g. `gettxoutsetinfo(200)` or new expected totals at 725). |
| **A** | `keypool.py` | Yes | Standalone harness; wallet keypool over cached chain; tip **725** OK |
| **B pass** | *(none)* | No | All **`initialize_chain_clean`** |
| **Bfail** | *(none)* | No | Same |
| **E pass** | *(none)* | No | Same |
| **Efail** | `rpcbind_test.py` | Yes | Standalone; **`-disablewallet`**; only needs nodes listening -- chain tip irrelevant |

**Default framework hook:** `BitcoinTestFramework.setup_chain()` calls **`initialize_chain`**, but no script in **`rpc-tests.sh`** relies on the default without overriding **`setup_chain`**.

**Default NU on `start_nodes`:** same Overwinter/Sapling at height 1 as cache build (`util.py` **`start_node`**). Per-test **`extra_args`** can override (e.g. `wallet_overwintertx`, `p2p_nu_peer_management`).

#### Stale cache recovery

Delete cache after changing **`COINBASE_MATURITY`**, the post-200 extension target, cache-build **`-nuparams`**, or subsidy/fee rules that affect the 200-block economics **`blockchain.py`** checks.

```bash
rm -rf cache    # from repo root when using run-tests.sh
killall zerod   # if needed
```

#### When not to use cache

Prefer **`initialize_chain_clean`** + **`mine_until_*`** / **`COINBASE_MATURITY`** helpers when a test needs a specific NU height plan, empty wallets, or exact tip control. Avoid **`ZERO_MINE_COINBASE=1`** bulk **1000** in the gate.

### Pending helper migration

Scripts still using hardcoded **`generate(720)`** instead of **`COINBASE_MATURITY`** / helpers. Porting is mechanical unless the test also asserts an exact tip for NU heights (then use **`mine_to_height`**).

| Script | Tier | Current | Target |
|--------|------|---------|--------|
| `wallet.py` | B pass | `generate(720)` x2 | `COINBASE_MATURITY` or `mine_until_node_has_mature_coinbase` |
| `wallet_overwintertx.py` | B pass | `generate(720)` + `ensure_mature_*` | align with Blossom height plan; may need `mine_to_height` not batch mine |
| `wallet_shieldcoinbase.py` | B pass | `generate(720)` (800-UTXO phase) | `COINBASE_MATURITY`; keep **`generate(100)`** at L170 (UTXO count, not maturity) |
| `listtransactions.py` | B pass | `generate(720)` | `COINBASE_MATURITY` |
| `p2p_txexpiry_dos.py` | B pass | `generate(720)` | `COINBASE_MATURITY` or formula in file comments |
| `walletbackup.py` | Bfail Debug | `generate(720)` / `generate(721)` | **`COINBASE_MATURITY`** / **`COINBASE_MATURITY + 1`**; see **walletbackup debug** below |

**Already ported (reference patterns):** `receivedby.py`, `mempool_limit.py`, `mempool_nu_activation.py`, `rest.py`, insight scripts (`coinbase_mature_tip(5)`), Tier A maturity paths (`ensure_mature_coinbase_or_skip`, `mine_until_*`, `txn_doublespend` height plan).

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

**Tier A note:** `shorter_block_times.py` still uses **`generate(101)`** in B pass; may need port if it starts spending coinbase.

### `walletbackup.py` debug (Bfail Debug)

| Item | Detail |
|------|--------|
| Failure (pre-fix) | `assert_equal(total, 7340)` at end of mining phase; actual **2886.875** ZER |
| Root cause | Upstream assumed maturity **100** and **114 x 10** subsidy math; comment in script said 1140 but assert was **7340**. Zero **720** maturity and regtest subsidy change the aggregate total |
| Real gate | Backup/restore via `wallet.zero` and `importwallet` preserves per-node balances (`balance0`..`balance2`) |
| Fix | `generate(720)` -> **`COINBASE_MATURITY`**; `generate(721)` -> **`COINBASE_MATURITY + 1`**; total check -> **`assert_greater_than(total, 1000)`** + log |
| Runtime | Slow: miner node mines **~720** blocks twice (bootstrap + fee maturity); expect **15-25+ min** on macOS regtest |

### `rpcbind_test.py` (Efail)

Standalone script (not `BitcoinTestFramework`). Uses **`initialize_chain`** then tests **`-rpcbind`** / **`-rpcallowip`**.

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

**`addressindex.py`**, **`spentindex.py`**, **`timestampindex.py`**, **`getrawtransaction_insight.py`** are in **Bfail Debug**. They need Insight Explorer enabled at node start and mature coinbase before spend/index assertions.

**`-insightexplorer`:** pass on every node via `start_nodes` `extra_args` (already in each script's `setup_network`). Required bundle:

```text
-debug -txindex -experimentalfeatures -insightexplorer
```

Example from `addressindex.py` `setup_network`: `args = ('-debug', '-txindex', '-experimentalfeatures', '-insightexplorer')` then `start_nodes(3, tmpdir, [args] * 3)`. `-insightexplorer` turns on address/spent/timestamp index RPCs; `-txindex` and `-experimentalfeatures` are prerequisites in this tree.

Maturity: upstream `generate(105)` assumed maturity **100**. Zero scripts use **`coinbase_mature_tip(5)`** or **`COINBASE_MATURITY`** helpers. Insight indexing does not require 720; **funding transactions** do.

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

### Pirate **`COINBASE_MATURITY`** (illustration)

**`ZKs/PirateOcean`**: **`extern int COINBASE_MATURITY`** default **100**, overridden at runtime by asset chain params (**`-ac_cbmaturity`**, **`ASSETCHAINS_CBMATURITY`** in **`komodo_utils.h`**). Same pattern as other Komodo-derived chains -- mutable per-chain, unlike Zero's compile-time **720**.

### Tier A porting for **720** + NU

| Script | Maturity | NU / notes |
|--------|----------|------------|
| **`rescan_import`**, **`wallet_changeaddresses`** | **`ensure_mature_coinbase_or_skip`** | Sapling at **1** |
| **`wallet_changeindicator`** | **`mine_until_node_has_mature_coinbase`** | |
| **`wallet_overwintertx`** | **`ensure_mature_coinbase_or_skip`** | Overwinter/Sapling/Blossom heights scripted |
| **`txn_doublespend`** | **`generate(need)`** to height **820** (all four 25-block coinbases mature) | **`mine_until`** stops too early here |
| **`p2p_nu_peer_management`** | minimal chain | NU at 10 / 15 |
| **`shorter_block_times`** | Blossom spacing | NU at 0 / 0 / 106 |
| **`rewind_index`** | fake NU heights | branch ID regression |
| **`getchaintips`** | **`CHAIN_BOOTSTRAP=30`** | split topology fix |
| Others in Tier A | no coinbase spend | **`initialize_chain_clean`** or cache-free |

---

## Known failures, hangs, and crashes

Default and **`--all`** share the same C++ exclusions (**Known failures** below). **`--fail`** runs only those suites. **Do not** use **`--all`** as a merge gate (full RPC pass tiers and runtime); use **default + `--strict`**.

### C++ -- excluded by default

| Item | Count | Risk | Notes |
|------|-------|------|-------|
| GTest **`WriteCryptedSaplingZkey*`** | **2** tests (`WriteCryptedSaplingZkeyDirectToDb`, `...SeparateFile`) | Hang | **`EncryptWallet`** -> **`CDB::Rewrite`** with DB open (**`test_wallet_zkeys.cpp`**). **Deprioritize:** Sapling encrypt path; not gate. |
| GTest **`CachedWitnesses*`** | 1+ | Fail / "failed to die" | **`pcoinsTip`** null; death test mismatch |
| Boost **`rpc_wallet_encrypted_wallet_sapzkeys`** | 1 suite | Hang | **Same as GTest encrypt:** `EncryptWallet` / **`CDB::Rewrite`** hang class via RPC |
| Boost **`miner_tests`** | 1 case (`CreateNewBlock_validity`) | Skip / no-op on Zero | **`blockinfo`** is **(96,5)**; Zero mainnet **(192,7)** -> `nEquihashN != 96` skip; need **(48,5)** regtest **`blockinfo`** to enable |

**Mitigation:** close wallet before rewrite (encrypt family); seed coins view for CachedWitnesses; Zero **`blockinfo`** for **`miner_tests`**.

### RPC Tier Bfail groups

Authoritative arrays: **`testScriptsTierBFailDebug`**, **`testScriptsTierBFailRetired`** in `rpc-tests.sh`. **`-Bfail`** runs Debug then Retired.

#### Bfail Debug (porting / engineering)

| Subgroup | Scripts | Typical failure | Fix direction |
|----------|---------|-----------------|---------------|
| **Wallet / list** | `wallet_listreceived`, `wallet_persistence`, `wallet_sapling`, `wallet_listnotes` | Sapling API / balance drift | Port to current wallet RPC |
| **Wallet / merge** | `mergetoaddress_sapling`, `mergetoaddress_mixednotes` | `z_mergetoaddress` async, maturity, note selection | `mine_until_*`; Sapling-only; check `mergetoaddress_helper.py` |
| **Insight** | `addressindex`, `spentindex`, `timestampindex`, `getrawtransaction_insight` | **`COINBASE_MATURITY` [720]** + `-insightexplorer` | Ported to `coinbase_mature_tip(5)`; enable experimental flags |
| **Mempool** | `mempool_limit`, `mempool_spendcoinbase`, `mempool_reorg`, `mempool_nu_activation`, `mempool_tx_expiry` | Maturity / NU heights | `COINBASE_MATURITY` mining; align `-nuparams` |
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
| **`wallet_overwintertx`** (NU heights / maturity) | **`./qa/pull-tester/rpc-tests.sh wallet_overwintertx`** |
| **`run-tests.sh`** background / **`wait`** | **`./contrib/run-tests.sh --no-python --strict`** then full **`./contrib/run-tests.sh --strict`** |
| Release-style gate | **`./contrib/run-tests.sh --strict`** |

---

## Verification snapshot

Record after harness changes (macOS, `./contrib/run-tests.sh --strict` unless noted):

| Run | Result | Wall time | Notes |
|-----|--------|-----------|-------|
| Default `(none) --strict` | **PASS** | **~212s** | macOS 2026-06-08; GTest+Boost parallel with Tier A |
| `--quick --strict` | **PASS** | **~142s** | util/secp/univalue + Tier A RPC |
| `--all --strict` | **PASS** (all pass-tier RPC) | **~1275s** | macOS 2026-06-08; `-all` = 40 scripts after retirements |
| `--suite` | **PASS** | **~1306s** | `full_test_suite.py`; RPC stage = no-args (`-all`) |
| Bfail `COINBASE_MATURITY+1` ports | **PASS** | see below | macOS 2026-06-08, from repo root |
| `walletbackup.py` (post-fix) | **PASS** | **~85s** | total **2886.875**; restore/importwallet equality OK |

**Bfail `COINBASE_MATURITY + 1` timings:** `rawtransactions` ~34s; `fundrawtransaction` ~54s; `signrawtransaction_offline` ~18s; `mergetoaddress_sapling` ~135s; `mergetoaddress_mixednotes` ~39s (after script-local maturity fix).

Tier inventory: `./qa/pull-tester/rpc-tests.sh -list-csv` or `qa/rpc-tests/test_tier_inventory.csv`

---

## Appendix: Overwinter retirement candidate

**`wallet_overwintertx.py`** (B pass) -- not retired yet; candidate for **Bfail Retired** or replacement.

| Factor | Detail |
|--------|--------|
| Tier | B pass (`testScriptsTierBPass`) |
| NU schedule | Overwinter@10, Sapling@15, Blossom@850; asserts `chaintip`, `overwintered`, v4 txs, expiry RPCs |
| Sprout debt | Uses **`z_getnewaddress('sprout')`** (same class as retired `wallet_treestate`) |
| Overlap | Expiry / `overwintered` covered by **`p2p_txexpiringsoon`**, **`mempool_tx_expiry`** |
| Fragility | Hardcoded **`generate(720)`**; skip paths if chaintip wrong |
| Keep if | You want one script walking OW -> Sapling -> Blossom on regtest |
| Retire if | Sapling-only expiry tests are enough; Sprout zaddrs should not stay in B pass |

Tier A Overwinter/NU tests (**keep**): `rewind_index`, `p2p_nu_peer_management`, `shorter_block_times`.

---

## Appendix: Retired tests

Scripts remain in `testScripts` inventory but are excluded from pass tiers (`-A`, `-B`, `-E`, `--all`). Run only via **`-rpcfail`** / **`-Bfail`** or by basename.

| Script | Tier | Reason |
|--------|------|--------|
| `prioritisetransaction.py` | Bfail Retired | Legacy Bitcoin-era test: `generate(1121)`, obsolete tx **priority** field, 900-tx loop. Zcash master replaced with ZIP-317 unpaid-action test (`generate(100+n+2)`). Bitcoin Core uses `mining_prioritisetransaction.py` (MiniWallet). Not worth porting 1121 to `COINBASE_MATURITY`. |
| `wallet_treestate.py` | Bfail Retired | Sprout **`z_getnewaddress('sprout')`** / **`z_sendmany`** joinsplit treestate race. Zcash upstream kept the test but moved to Sapling-only (`z_getnewaddress()` without sprout, `-regtestshieldcoinbase`, ZIP-317 fees). Zero should not gate on Sprout treestate; port or drop. |
| `mergetoaddress_sprout.py` | Bfail Retired | Sprout merge RPC retired |
| `sprout_sapling_migration.py` | Bfail Retired | Sprout migration; still uses upstream **`generate(101)`** bootstrap |
| `turnstile.py` | Bfail Retired | Sprout pool / ZIP209; **`generate(101)`** bootstrap; manual testnet notes in comments |
| `zcjoinsplit*` | removed from inventory | Sprout joinsplit RPC tests removed from driver |
| `wallet_shieldcoinbase_sprout` | removed from inventory | Sprout shieldcoinbase removed from driver |

**C++ deprioritized (not retired):** GTest **`WriteCryptedSaplingZkey*`** (2 cases), **`CachedWitnesses*`**, Boost **`rpc_wallet_encrypted_wallet_sapzkeys`** -- Sapling encrypt / `CDB::Rewrite` hang class; excluded in `test_filters.sh`.

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

