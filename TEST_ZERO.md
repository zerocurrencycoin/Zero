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
| **Ops smoke** | `./contrib/ops-validate.sh smoke` (cold + restart) |
| **Ops short** (RC) | `./contrib/ops-validate.sh short` (equihash + verifyeq + smoke) |
| **Ops mine** | `./contrib/ops-validate.sh mine` (isolated regtest `generate`; default 8) |
| **Ops validate** (live / reindex / bootstrap / copy) | `./contrib/ops-validate.sh cold` (then `live` if SRC `zerod` is up) |

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
| B | pass | 31 | `-B` (`txn_doublespend` x2; 30 unique) | **working** |
| E | pass | 8 | `-E` | **working** |
| **A+B+E** | **pass** | **49** | **`-all`** / `run-tests.sh --all` | **working** |

### Tier A (`testScriptsTierA` / `PYTHON_PASSING`) -- working

blockchain, disablewallet, httpbasics, reindex, decodescript, keypool, paymentdisclosure, getchaintips, rewind_index, p2p_nu_peer_management

`contrib/run-tests.sh` **`PYTHON_PASSING`** (basenames, no `.py`) must match this list for `--jobs=N` only. Serial gate uses `rpc-tests.sh -A`.

### Tier B pass (`testScriptsTierBPass`) -- working

wallet, wallet_anchorfork, wallet_changeindicator, wallet_import_export, wallet_1941, listtransactions, mempool_resurrect_test, mempool_spendcoinbase, mempool_limit, txn_doublespend, txn_doublespend --mineblock, zapwallettxes, proxy_test, signrawtransactions, nodehandling, rescan_startup, getblocktemplate, founders_window, zeronode_coinbase, zeronode_startalias, p2p_txexpiry_dos, p2p_txexpiringsoon, p2p_node_bloom, getrawtransaction_insight, rest, addressindex, spentindex, timestampindex, walletbackup, reindex_shielded, wallet_witness_defer

### Ext pass (`testScriptsExtPass`) -- working

invalidateblock, maxblocksinflight, rpc_coverage_probe, receivedby, rpcbind_test, getblocktemplate_longpoll, rpc_workqueue_full, getalldata_scenario

### C++ working filters (`qa/zcash/test_filters.sh`)

Default gate excludes one GTest still under development (listed in §6). Everything else in GTest/Boost runs under `--strict` / `--no-python`.

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

## 5. Promote and hold

A basename that exits **0** when run alone is **not** in the contributor gate until it is moved into a pass array in `rpc-tests.sh`, CSV regenerated, and §3 updated in the same change set. Hold items stay in Bfail / Efail / `--fail`.

There is **no** requirement for a second (192,7) Equihash solver in Python. `qa/rpc-tests/test_framework/equihash.py` stays for mininode/comptool on **regtest (48,5)** only; it is not authoritative and not performant. C++ `CheckEquihashSolution` / `zcbenchmark` is.

| Hold | Scripts | Blocker |
|------|---------|---------|
| Tip-200 / cache | `wallet_addresses`, `rescan_import`, `reorg_limit`, `wallet_listnotes`, `wallet_sapling`, `wallet_listreceived`, `wallet_persistence` | Hard-coded heights vs warm cache tip; needs `initialize_chain_clean` + `generate(200)` or relative heights |
| Maturity / NU | `shorter_block_times`, `wallet_changeaddresses` | `COINBASE_MATURITY=720`; Blossom / fee-start mine plan |
| Heavy proving | `wallet_shieldcoinbase_sapling`, `wallet_protectcoinbase`, `wallet_nullifiers`, `zkey_import_export` | Multi-GB RSS and long `generate` on `-all`; held from pass tiers by policy, not an unknown crash |
| Tx construction | `rawtransactions`, `fundrawtransaction`, `mergetoaddress_sapling`, `mergetoaddress_mixednotes`, `signrawtransaction_offline`, `key_import_export`, `regtest_signrawtransaction`, `merkle_blocks`, `finalsaplingroot` | Py3 / subsidy / Sapling RPC asserts still fail or un-reverified |
| Pure txindex | `txindex` | Decimal `nValue` and 10 ZER subsidy vs leftover 50-coin asserts |
| Comptool P2P | `bip65-cltv-p2p`, `bipdersig-p2p`, `invalidblockrequest`, `p2p-acceptblock` | Comparison-tool block templates; Python Equihash is (48,5) only |
| Mempool / NU | `mempool_reorg`, `mempool_nu_activation`, `mempool_tx_expiry` | Activation / expiry heights vs Zero NU schedule |
| GBT proposals | `getblocktemplate_proposals` | Proposal path vs Zero coinbase / founders |
| Pruning | `pruning` | Multi-GB disk and long wall; Bitcoin-era size assumptions |
| Fee estimate | `smartfees` | Estimator vs Zero fee-start / founders |
| Retired Sprout | `prioritisetransaction`, `wallet_treestate`, `wallet_overwintertx`, `mergetoaddress_sprout`, `sprout_sapling_migration`, `turnstile` | Sprout-era or manual testnet; not a 4.0.1 gate item |
| GTest | `CachedWitnessesCleanIndex` | Needs reindex-style `pcoinsTip` + disk blocks; run `--fail` |

Optional: `--jobs>1` is throughput only; keep serial for gates. Re-record `--all --strict` wall when the working count changes (currently **49** invocations).

---

## 6. Diagnostic and missing coverage

Arrays and filters for scripts still under development. Run via `-Bfail`, `-Efail`, `-rpcfail`, or `--fail`. Outcome of each script is **pass** or **fail** only when you run that script.

| Tier | Group | Count | How to run |
|------|-------|------:|------------|
| Bfail | debug | 28 | `-Bfail` (first) |
| Bfail | retired | 6 | `-Bfail` (second) |
| Efail | fail | 5 | `-Efail` / part of `-rpcfail` |

### Bfail Debug (`testScriptsTierBFailDebug`)

shorter_block_times, wallet_changeaddresses, wallet_addresses, rescan_import, reorg_limit, wallet_listreceived, wallet_persistence, wallet_sapling, wallet_listnotes, mergetoaddress_sapling, mergetoaddress_mixednotes, rawtransactions, mempool_reorg, mempool_nu_activation, mempool_tx_expiry, merkle_blocks, fundrawtransaction, signrawtransaction_offline, key_import_export, bip65-cltv-p2p, bipdersig-p2p, regtest_signrawtransaction, finalsaplingroot, txindex, wallet_shieldcoinbase_sapling, wallet_protectcoinbase, wallet_nullifiers, zkey_import_export

### Bfail Retired (`testScriptsTierBFailRetired`)

prioritisetransaction, wallet_treestate, wallet_overwintertx, mergetoaddress_sprout, sprout_sapling_migration, turnstile

### Efail (`testScriptsExtFail`)

getblocktemplate_proposals, pruning, smartfees, invalidblockrequest, p2p-acceptblock

### C++ suites outside the working gate (`qa/zcash/test_filters.sh`)

| Layer | Working-gate exclude | Run alone via |
|-------|----------------------|---------------|
| GTest | `-WalletTests.CachedWitnessesCleanIndex` | `--fail` or `--gtest_filter=WalletTests.CachedWitnessesCleanIndex` |
---

## 7. Interpreting results

### Exit accounting

- Without **`--strict`**, failures print **`WARNING`** but exit **0**. With **`--strict`**, exit **1** on any failure.
- **Exit 0 after `skip_test`** is a skip, not a pass.

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

- **(192,7)** mainnet genesis (valid + corrupt **`nSolution`**), `validator_testvectors_192_7` / `_h1` (`src/test/data/`).
- **(48,5)** regtest genesis validator + `solver_testvectors_48_5` (`ENABLE_MINING`).
- **CreateNewBlock** in-process: `./src/test/test_bitcoin -t miner_tests` (`CreateNewBlock_regtest_48_5`; `ENABLE_MINING`). No frozen `blockinfo[]`.
- Also: `contrib/ops-validate.sh equihash` (KATs), `verifyeq` / `solveeq` (timed MAIN (192,7)), `mine` (isolated regtest `generate`, not mainnet). Operator CPU miner is `setgenerate` / `gen=1` -- TEST_ZERO §8.5.
- Python Equihash in `qa/` is not authoritative and not performant. C++ `CheckEquihashSolution` / `zcbenchmark` is. No second (192,7) Python solver. Compact index codec matches C++; `gbp_basic` uses ZcashPoW personalization (node is ZERO_PoW), so it does not reproduce node (48,5) solutions unless person is overridden.

Failures in the Zero-specific cases usually mean **`chainparams.cpp`** / **`pow.cpp`** / **`CheckEquihashSolution`** drift. Verbose: **`--log_level=test_suite`** or **`message`**.

---

## 8. Platform evidence and operational checks

`--strict` proves the contributor gate on **one** OS. v4.0.1 needs an honest matrix plus a few node-lifecycle soaks. Do not treat a green macOS gate as Linux ELF, Windows, mining, or Zerowallet coverage.

Receipts live in gitignored **`.build/`**. Scratch chain data stays outside the repo.

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
| **Live mining** (operator `gen=1` / `setgenerate` on mainnet) | **Optional observation** -- solver activity via `getmininginfo` / `debug.log`; not a found-block requirement | Same | Same |
| Zerowallet | **Manual only** -- start or attach, watch addresses / History load, spinner, error dialogs. No automated UI. No send/receive, bulk, or mixed-type tx in this program | Same if used | Same if used |

**RC bar:** macOS `--strict` on the **tag commit**; Linux `--strict` + `--suite` strongly recommended; Windows = first successful MXE build at minimum, then `--strict` when a Win/WSL2 runner exists. **Signing:** `SHA256SUMS` plus platform signatures (BUILD_ZERO §2.6) on every shipped artifact; unsigned CI output is not a release. Record hashes/signatures as present or **explicitly missing**. Maintainer decides which OS gates are hard blocks. Darwin also skips full `rpcbind`; keep serial `--strict` (`--jobs>1` can hang `paymentdisclosure`).

### 8.1.1 macOS retest at the current tip

Linux is green on `perf_b1b2` at the current tip: build, 218 gtest, 324 boost,
49/49 rpc `-all`. macOS has not been rebuilt there. Run the same three suites on
the Mac and record each as pass, fail, or not run.

```bash
./zcutil/build.sh -j"$(sysctl -n hw.ncpu)"
./src/zerod --version                                   # must NOT end in -dirty

source qa/zcash/test_filters.sh
./src/zero-gtest --gtest_filter="$GTEST_PASS_EXCLUDE"   # expect 218 passed
./src/test/test_bitcoin -p                              # expect 324, no errors
./qa/pull-tester/rpc-tests.sh -all                      # expect 49/49
```

Confirm the rpc run by its own marker rather than an exit code: `Tests
completed:` must be present, and the `--- Success` count must match the reported
successes.

Not macOS defects:

- **Uniblake** resolves to the sibling checkout at `../uniblake` with no
  configuration; its short HEAD is the package version, so a uniblake commit
  rebuilds it on its own.
- **`WalletTests.CachedWitnessesCleanIndex`** is held in
  `qa/zcash/test_filters.sh` and fails unfiltered on every platform. Its reindex
  scenario needs the `pcoinsTip` + `ReadBlockFromDisk` path the gtest harness
  cannot provide.
- **A `Permission denied` test failure is a file mode**, not a port problem.
  `core.fileMode=true` strips a local `+x` on checkout; check `git ls-files -s`
  first.

### 8.2 Automating beyond the harness

| Layer | What | Exists |
|-------|------|--------|
| **0 -- merge gate** | `--strict` | `contrib/run-tests.sh` |
| **1 -- widen** | `--all`, Linux `--suite`, `release-linux.sh` smoke | Same runner |
| **2 -- node lifecycle** | COLD / RESTART / ATTACH on a scratch datadir | `contrib/ops-validate.sh smoke` |
| **3 -- clients / mining** | Zerowallet visual; Equihash verify/solve; regtest mine | GUI in the wallet repo. `verifyeq` / `solveeq` / `mine` here |

Receipts: **`.build/`** (`ready-*.txt`, `ready-latest.txt`, build logs, `test-logs/`, `ops-status.jsonl`). Scratch chain data: **`ZERO_OPS_LAB`** (default `/tmp/zero-ops-validate`), never the default user datadir, never this tree unless `--force`. Conf: `contrib/zero-conf.sh` from `contrib/conf-templates/` (default template **prod**, default file `/tmp/zero.conf`). Never sticky `reindex=1`. Sapling params are system setup (`BUILD_ZERO` §3), not this cycle.

Ports: **23801-23820** are reserved for deployments and tests that use chain defaults (P2P 23801 / RPC 23811 and test/regtest siblings). Isolated ops defaults are RPC **23941** (LAB) and **23951** (`verifyeq` / `solveeq` / `mine`). QA harness uses ephemeral **11000+** / **12000+**. `ops-validate` refuses a LAB rpcport in 23801-23820 unless `--force`. `live` talks to SRC on the operator's configured RPC port.

### 8.3 Operational catalog

`contrib/ops-validate.sh` is the product soak and short RC driver (isolated LAB under `/tmp` by default). Bundles: **`short`** (equihash + verifyeq + smoke), **`smoke`** (cold + restart). One trial per invocation except those bundles. Default load stop is height 100000 and `-disablewallet`. Packed snaps and `bootstrap.dat` stay outside git. `--force` / `ZERO_OPS_FORCE=1` overrides datadir, running-`zerod`, and port gates (WARNING). Python Equihash helpers in `qa/` are not authoritative and not performant; C++ KATs and `zcbenchmark` are.

| Id | Command | Pass |
|----|---------|------|
| **OPS-SMOKE** | `smoke` | `cold` then `restart` |
| **OPS-SHORT** | `short` | `equihash` + `verifyeq` + `smoke` |
| **OPS-START-COLD** | `cold` | RPC up on empty scratch, clean `stop` |
| **OPS-RESTART** | `restart` after `cold` | Tip unchanged |
| **OPS-ATTACH** | `keep` on a start cmd, then `attach` | `getblockchaininfo` on LAB |
| **OPS-LIVE** | `live` | RPC to SRC (operator datadir); does not start or stop |
| **OPS-REINDEX** | `reindex` / `reindex all` | `-reindex` from snap; `all` = snap tip |
| **OPS-BOOTSTRAP** | `bootstrap` | `-loadblock` to 100000 (`all` = end of file) |
| **OPS-RESCAN** | `rescan` | keep indexes, `-rescan`, wait Done loading (needs chainstate in snap) |
| **OPS-COPY** | `copy` | rsync SRC blocks+chainstate into LAB, wait stable tip. Stop every `zerod` first |
| **OPS-EQUIHASH** | `equihash` | Boost `equihash_tests` (KATs; no `zerod`) |
| **OPS-VERIFYEQ** | `verifyeq` / `verifyeq N` | isolated `-regtest` + `zcbenchmark verifyequihash` N (default 20; MAIN **(192,7)**); times in ms |
| **OPS-SOLVEEQ** | `solveeq` / `solveeq N` | isolated lab; `zcbenchmark solveequihash` N times (default 1, ~50s each); per-sample seconds plus min/mean/median/stdev when N>1; `rpcservertimeout=3600`; `ENABLE_MINING`; not the RC bar |
| **OPS-MINE** | `mine` / `mine N` | isolated `-regtest` `generate` N (default 8); Equihash **(48,5)**; does **not** mine mainnet |

Wallet ids: `p0` / `p1` / `fat` / `none` or `--wallet=PATH` (`wallets` lists paths). On `verifyeq` / `solveeq` / `mine`, a bare number is the sample or block count, not wallet id `0`/`1`/`3`. `keep` leaves LAB `zerod` up. `stop` always stops LAB.

P2P-CATCHUP is not in this menu. GBT is Tier B `getblocktemplate` (`-B` / `--all`).

**RC bar:** layer 0 + `ops-validate.sh short` + `live` when SRC is up + checksums/signatures + wallet visual. `solveeq` is optional (default one long trial; pass N for repeats).

### 8.4 Zerowallet soak

No UI harness in this tree. Node-side: OPS-ATTACH + template `zerowallet`. macOS GUI path may be `Application Support/Zero` (INT-01) vs canonical `zero`. Align `rpcuser` / `rpcpassword` / `rpcport`. Do not send. Visual: addresses, History, spinner, dialogs. Spinner-idle is not a sync proof.

### 8.5 Mining

Three different things, not one command.

Isolated tests in this tree (scratch LAB, not the operator datadir):

- Boost KATs: `ops-validate.sh equihash` or `./src/test/test_bitcoin -t equihash_tests`
- Timed MAIN **(192,7)** verify / solve: `verifyeq` / `solveeq` (`zcbenchmark`; solve does not submit a block)
- In-process CreateNewBlock: `./src/test/test_bitcoin -t miner_tests`
- Daemon `generate` on **regtest (48,5)**: `ops-validate.sh mine`

Operator CPU miner on **mainnet (192,7)** is `gen=1` / `setgenerate`. Template **prod** ships `gen=0`. Mainnet and testnet set `fMiningRequiresPeers`, so the miner waits until there are peers and the node is not in IBD. Coinbase needs a wallet or `-mineraddress`. `setgenerate` is the RPC for mainnet/testnet; on regtest use `generate` (that is what `mine` calls). One OptimisedSolve is on the order of a minute; finding a mainnet block at current difficulty is not expected. Watch `getmininginfo` (`generate`, `localsolps`) and `debug.log` (`Using Equihash solver`, `Running ZeroMiner`). `setgenerate false` turns it off.

Tier B `getblocktemplate` is the pool/template claim (`-B` / `--all`). Live pool hash is out of scope here.

### 8.6 Explorer consumer

Template `insight`. Flags must match the copied index. Optional `getaddressbalance` / `getaddresstxids` on a disposable copy. No `reindex=` in conf.

### 8.7 After a branch merge

Run `zcutil/check-setup.sh`, `zcutil/check-release.sh`, and `contrib/run-tests.sh --strict`. Compare `.build/setup-latest.txt` and `.build/ready-latest.txt` to copies of the pre-merge receipts (latest is overwritten each run).

---

