# TEST_ZERO

Validation runbook for the Zero full node.

**Scripts win.** Tier membership and basenames live only in `qa/pull-tester/rpc-tests.sh` arrays. Inventory CSV: `qa/rpc-tests/test_tier_inventory.csv` (regenerate with `-list-csv`). If this file disagrees with those, **the scripts win**.

**Prereqs:** [BUILD_ZERO.md](BUILD_ZERO.md) Quick Start (toolchain, Python **3.10+**, `src/zerod` / test binaries). Open items: **TODO.md**. Python was not raised to 3.11; 3.10 is the floor (`hashlib.blake2b`).

---

## 1. Vision and methodology

Use a small set of entry points to validate the node: the contributor merge gate, optional bulk RPC coverage, and focused single-script or single-suite runs when extending the harness.

1. **Working gate.** `./contrib/run-tests.sh --strict` runs the current pass-only C++ suites plus Tier A RPC -- the supported merge check.
2. **Scripts win.** Tier membership lives in `rpc-tests.sh`; regenerate `-list-csv` when promoting a script into a working tier.
3. **Maturity / clean chain.** Regtest `COINBASE_MATURITY = 720`. Prefer `initialize_chain_clean` + explicit mine helpers when porting.
4. **Depth by layer.** Exclusive Boost for empty-wallet RPC gates; Ext/B scenarios for populated wallets; GTest for wallet units.
5. **Verify then promote.** When a basename run succeeds, update arrays and §3 in the same change set.
6. **Platform + ops.** `--strict` is not a full-node soak. Re-run the gate on each OS you ship; add operational checks in §8 (startup, reindex, bootstrap, sync, attach). Checksums and signatures during release prep. One long trial per invocation.

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
| **Host / setup receipt** | `./zcutil/check-setup.sh` (toolchain + Sapling params; `--win` for MXE) |
| **Release-tree receipt** | `./zcutil/check-release.sh` (**READY** only on a clean tree; `--allow-dirty` is identity-only; `-v` for full dump) |
| **Receipt + `build.sh`** | `./zcutil/build-release.sh` (setup check, then tree receipt, then `build.sh`; not a test runner) |
| **Ops smoke** (COLD / RESTART / ATTACH) | `./contrib/ops-smoke.sh cold` (then `restart`; `start` then `attach`) |

Tier B scripts (`getblocktemplate`, `disablewallet`, `addressindex`, ...) run as part of `-B` / `--all`. Do not run them one-by-one unless isolating a fail.

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
| **`FAIL: <step>`** | Non-zero; see cited **`.log`** under **`.build/test-logs/`**. |
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

## 8. Platform evidence and operational checks

`--strict` proves the contributor gate on **one** OS. v4.0.1 needs an honest matrix plus a few node-lifecycle soaks. Do not treat a green macOS gate as Linux ELF, Windows, mining, or Zerowallet coverage.

Do **not** copy the ZeroPerf campaign set into this tree. Receipts live in gitignored **`.build/`**. Scratch chain data stays outside the repo.

### 8.1 What has actually been run

| Layer | macOS ARM64 | Linux x86_64 (Ubuntu 24.04 class) | Windows |
|-------|-------------|-----------------------------------|---------|
| Build | **Done** (`./zcutil/build.sh`) | **Partial** -- rebuild at the release tip is still the recommended next gate | **Not run.** MXE cross from Linux is documented in BUILD_ZERO; this program has never produced or executed `zerod.exe` |
| `./contrib/run-tests.sh --strict` | **Done** on an earlier 4.0.1-line tip (2026-06). **Re-run on the tag commit** | **Not run at current tip.** Recommended before tag; maintainer may ship without it | No native or WSL2 `--strict` |
| `--suite` (ELF `check-security` / `no-dot-so`, full `rpcbind`) | **N/A** -- Darwin skips ELF stages | **Not run at current tip.** Recommended | N/A for PE |
| `--all --strict` (Tier A+B+E) | Optional; re-run after tier moves | Optional after `--strict` | Not run |
| Packaging | N/A | `release-linux.sh` not a `--strict` substitute | No signed installer |
| Checksums / signatures | **Missing.** Produce during release prep, not after the GitHub Release is live | Same; GPG over `SHA256SUMS` when Linux artifacts ship | Authenticode if a PE ships |
| Isolated mining RPC (OPS-GBT / Tier B `getblocktemplate`) | Tier B exists in the harness; isolated mainnet template not recorded | Same | Not run |
| Live mining (timed mainnet (192,7) solve, pool, production hash) | **Not confirmed** -- optional observation, not the definition of mining | **Not confirmed** | **Not confirmed** |
| Zerowallet | **Manual only** -- start or attach, watch addresses / History load, spinner, error dialogs. No automated UI. No send/receive, bulk, or mixed-type tx in this program | Same if used | Same if used |

**RC bar:** macOS `--strict` on the **tag commit**; Linux `--strict` + `--suite` strongly recommended; Windows = first successful MXE build at minimum, then `--strict` when a Win/WSL2 runner exists. **Signing:** `SHA256SUMS` plus platform signatures (BUILD_ZERO §2.6) on every shipped artifact; unsigned CI output is not a release. Record hashes/signatures as present or **explicitly missing**. Maintainer decides which OS gates are hard blocks. Darwin also skips full `rpcbind`; keep serial `--strict` (`--jobs>1` can hang `paymentdisclosure`).

### 8.2 Automating beyond the harness

| Layer | What | Exists |
|-------|------|--------|
| **0 -- merge gate** | `--strict` | `contrib/run-tests.sh` |
| **1 -- widen** | `--all`, Linux `--suite`, `release-linux.sh` smoke | Same runner |
| **2 -- node lifecycle** | COLD / RESTART / ATTACH on a scratch datadir | `contrib/ops-smoke.sh` |
| **3 -- clients / mining** | Zerowallet visual; Equihash **solve** | GUI in the wallet repo. Mining prototype in ZeroPerf |

Receipts: **`.build/`** (`ready-*.txt`, `ready-latest.txt`, build logs, `test-logs/`, `ops-status.jsonl`). Scratch chain data: **`ZERO_OPS_LAB`** (default `$TMPDIR/zero400-ops`), never the default user datadir, never this tree. Conf: `contrib/zero-conf.sh` (default template **prod**, default file `/tmp/zero.conf`). Never sticky `reindex=1`. Sapling params are system setup (`BUILD_ZERO` §3), not this cycle.

### 8.3 Operational catalog

**Zero400 now** (`contrib/ops-smoke.sh`):

| Id | Command | Pass |
|----|---------|------|
| **OPS-START-COLD** | `cold` | RPC up on empty scratch, clean `stop` |
| **OPS-RESTART** | `restart` after `cold` | Tip unchanged |
| **OPS-ATTACH** | `start` then `attach` | `getblockchaininfo` on a running node |

**Not in the Zero400 smoke menu** (ZeroPerf / later, one trial per invocation): START-WARM, NOWALLET+Insight, REINDEX, BOOTSTRAP, RESCAN, P2P-CATCHUP. There is no calendar "same-week" band.

GBT is Tier B `getblocktemplate` (`-B` / `--all`), not a separate OPS id. Mining solve prototypes in ZeroPerf first.

**RC bar:** layer 0 + Zero400 ops smoke + checksums/signatures + wallet visual.

### 8.4 Zerowallet soak

No UI harness in this tree. Node-side: OPS-ATTACH + template `zerowallet`. macOS GUI path may be `Application Support/Zero` (INT-01) vs canonical `zero`. Align `rpcuser` / `rpcpassword` / `rpcport`. Do not send. Visual: addresses, History, spinner, dialogs. Spinner-idle is not a sync proof.

### 8.5 Mining

Tier B `getblocktemplate` is the 400 claim. Isolated (192,7) solve and live hash stay ZeroPerf prototypes. `gen=0` is the operator default.

### 8.6 Explorer consumer

Template `insight`. Flags must match the copied index. Optional `getaddressbalance` / `getaddresstxids` on a disposable copy. No `reindex=` in conf.

### 8.7 Pull from ZeroPerf

Do not merge `perf-401`. One dedicated branch (for example `from-perf-401`) and **one or two increments**, then a full receipt + `--strict` + ops smoke.

| Increment | Take | Leave |
|-----------|------|-------|
| **1 -- product fixes** | FIX-LBI / FIX-IMPORT-POLL, PIR-03 status allowlist, `reindex_shielded.py` + tier line; keep Zero400 `ClearNoteWitnessCache` two-outpoint gtest | `contrib/perf/`, witness default-on, `ZERO_FDCACHE`, STALE, TNT-02/03, Groth poc |
| **2 -- optional** | root latch, anchor Exists, TST-05 if still missing; witness flags **defaults off** only if chosen | Same leave list |

`git fetch <ZeroPerf> perf-401`, path-limited cherry-pick, then `zcutil/check-setup.sh`, `zcutil/check-release.sh`, and `contrib/run-tests.sh --strict`. Compare `.build/setup-latest.txt` and `.build/ready-latest.txt` to copies of the pre-pull receipts (latest is overwritten each run).

---

