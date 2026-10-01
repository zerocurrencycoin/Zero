# TEST_ZERO

Validation runbook for the Zero full node.

**Scripts win.** Tier membership and basenames live only in `qa/pull-tester/rpc-tests.sh` arrays. Inventory CSV: `qa/rpc-tests/test_tier_inventory.csv` (regenerate with `-list-csv`). If this file disagrees with those, **the scripts win**.

**Prereqs:** [BUILD_ZERO.md](BUILD_ZERO.md) Quick Start (toolchain, Python **3.10+**, `src/zerod` / test binaries). Python 3.10 is the floor (`hashlib.blake2b`).

---

## 1. Vision and methodology

Use a small set of entry points to validate the node: the contributor merge gate, optional bulk RPC coverage, and focused single-script or single-suite runs when extending the harness.

1. **Working gate.** `./contrib/run-tests.sh --strict` runs the current pass-only C++ suites plus Tier A RPC -- the supported merge check.
2. **Scripts win.** Tier membership lives in `rpc-tests.sh`; regenerate `-list-csv` when promoting a script into a working tier.
3. **Maturity / clean chain.** Regtest `COINBASE_MATURITY = 720`. Prefer `initialize_chain_clean` + explicit mine helpers when porting. Harness helpers `block_subsidy`, `founders_share`, and `mine_until_mature` cover the regtest founders window (heights 1000 to 1500).
4. **Depth by layer.** Exclusive Boost for empty-wallet RPC gates; Ext/B scenarios for populated wallets; GTest for wallet units.
5. **Verify then promote.** When a basename run succeeds, update arrays and section 3 in the same change set.
6. **Platform + ops.** `--strict` is not a full-node soak. Re-run the gate on each OS you ship; add operational checks in section 8 (startup, reindex, bootstrap, sync, attach). Checksums and signatures during release prep. One long trial per invocation.

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
| **Multi-stage / ELF** (`full_test_suite.py`) | `./contrib/run-tests.sh --suite`: filtered C++ suites, util, secp256k1, univalue, the `-all` RPC tiers, and ELF hardening (`sec-hard`) and no-shared-library (`no-dot-so`) checks. A superset of `--all` except `check-symbols`; Darwin skips the ELF stages |
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

**Environment:** Python **3.10+**. The RPC harness cache `<repo>/cache/` is gitignored and safe to delete; Tier A rebuilds it to tip 725. For direct `rpc-tests.sh`, set `PYTHON` / `BUILDDIR` if needed (see harness scripts under `qa/`).

**Exit codes:** Prefer **`--strict`** so a non-zero exit means a specific step did not succeed. Without it, `run-tests.sh` may still exit **0** after a WARNING.

---

## 3. Working inventory

Regenerate after every tier edit:

```bash
./qa/pull-tester/rpc-tests.sh -list-csv qa/rpc-tests/test_tier_inventory.csv
```

| Tier | Group | How to run | Status |
|------|-------|------------|--------|
| A | gate | `-A` / default `run-tests.sh` | **working** |
| B | pass | `-B` (`txn_doublespend` runs twice) | **working** |
| E | pass | `-E` | **working** |
| **A+B+E** | **pass** | **`-all`** / `run-tests.sh --all` | **working** |

Script names per tier: `qa/rpc-tests/test_tier_inventory.csv` (columns `tier`, `group`, `script`), generated from the arrays in `qa/pull-tester/rpc-tests.sh`, which are authoritative. `contrib/run-tests.sh` reads the Tier A names from the same arrays for `--jobs=N`; the serial gate uses `rpc-tests.sh -A`.

### C++ working filters

Default gate excludes one GTest still under development (listed in section 6). Everything else in GTest/Boost runs under `--strict` / `--no-python`.

---

## 4. Harness map

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

A basename that exits **0** when run alone is **not** in the contributor gate until it is moved into a pass array in `rpc-tests.sh` and the CSV is regenerated in the same change set. Hold items stay in Bfail / Efail / `--fail`.

| Hold | Scripts | Blocker |
|------|---------|---------|
| Tip-200 / cache | `wallet_addresses`, `rescan_import`, `reorg_limit`, `wallet_listnotes`, `wallet_sapling`, `wallet_listreceived`, `wallet_persistence` | Hard-coded heights vs warm cache tip; needs `initialize_chain_clean` + `generate(200)` or relative heights |
| Maturity / NU | `shorter_block_times`, `wallet_changeaddresses` | `COINBASE_MATURITY=720`; Blossom / fee-start mine plan |
| Heavy proving | `wallet_shieldcoinbase_sapling`, `wallet_protectcoinbase`, `zkey_import_export` | Multi-GB RSS and long `generate` on `-all`; held from pass tiers by policy, not an unknown crash |
| Tx construction | `rawtransactions`, `fundrawtransaction`, `mergetoaddress_sapling`, `mergetoaddress_mixednotes`, `signrawtransaction_offline`, `key_import_export`, `regtest_signrawtransaction`, `merkle_blocks`, `finalsaplingroot` | Py3 / subsidy / Sapling RPC asserts still fail or un-reverified |
| Comptool P2P | `bip65-cltv-p2p`, `bipdersig-p2p`, `invalidblockrequest`, `p2p-acceptblock` | Comparison-tool block templates; Python Equihash is (48,5) only |
| GBT proposals | `getblocktemplate_proposals` | Proposal path vs Zero coinbase / founders |
| Pruning | `pruning` | `-prune` is disabled in Zero (option commented out in `init.cpp`; `txindex` is forced on); retire with the option or restore both together |
| Fee estimate | `smartfees` | Estimator vs Zero fee-start / founders |
| Retired Sprout | `prioritisetransaction`, `wallet_treestate`, `wallet_overwintertx`, `mergetoaddress_sprout`, `sprout_sapling_migration`, `turnstile`, `zcjoinsplit`, `zcjoinsplitdoublespend` | `zcjoinsplit*` call the `zcraw*` RPCs, compiled out unless built with `-DENABLE_ZCRAW_RPC`; the others are Sprout-era or manual testnet; not a gate item |
| Fork warnings | `hardforkdetection`, `forknotify` | Mine with `-blockversion=2`, below the minimum block version 4; read `-alertnotify` output, which builds without `ENABLE_SYSTEM_COMMAND` skip; `forknotify` tests a warning on unknown block versions that the node does not have |
| GTest | `CachedWitnessesCleanIndex` | Needs reindex-style `pcoinsTip` + disk blocks; run `--fail` |

Optional: `--jobs>1` is throughput only; keep serial for gates. Re-record the `--all --strict` wall time when scripts move between tiers.

---

## 6. Diagnostic and missing coverage

Arrays and filters for scripts still under development. Run via `-Bfail`, `-Efail`, `-rpcfail`, or `--fail`. Outcome of each script is **pass** or **fail** only when you run that script. Config and CLI option parity has no automated check.

| Tier | Group | How to run |
|------|-------|------------|
| Bfail | debug | `-Bfail` (first) |
| Bfail | retired | `-Bfail` (second) |
| Efail | fail | `-Efail` / part of `-rpcfail` |

Script names: the inventory CSV (section 3); blockers per script: section 5.

### C++ suites outside the working gate

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

### Equihash -- Boost `equihash_tests`

**Source:** **`src/test/equihash_tests.cpp`**. **Run:** **`./src/test/test_bitcoin -t equihash_tests`**.

- **(192,7)** mainnet genesis (valid + corrupt **`nSolution`**), `validator_testvectors_192_7` / `_h1` (`src/test/data/`).
- **(48,5)** regtest genesis validator + `solver_testvectors_48_5` (`ENABLE_MINING`).
- **CreateNewBlock** in-process: `./src/test/test_bitcoin -t miner_tests` (`CreateNewBlock_regtest_48_5`; `ENABLE_MINING`). No frozen `blockinfo[]`.
- Also: `contrib/ops-validate.sh equihash` (KATs), `verifyeq` / `solveeq` (timed MAIN (192,7)), `mine` (isolated regtest `generate`, not mainnet). Operator CPU miner is `setgenerate` / `gen=1` -- TEST_ZERO section 8.5.
- Python Equihash (`qa/rpc-tests/test_framework/equihash.py`) serves mininode and comptool on regtest (48,5) only; it is not authoritative and there is no (192,7) Python solver. C++ `CheckEquihashSolution` and `zcbenchmark` are authoritative. Compact index codec matches C++; `gbp_basic` uses ZcashPoW personalization (node is ZERO_PoW), so it does not reproduce node (48,5) solutions unless person is overridden.

Failures in the Zero-specific cases usually mean **`chainparams.cpp`** / **`pow.cpp`** / **`CheckEquihashSolution`** drift. To stay compatible with the Zero mainnet, do not make a failing vector pass by changing the mainnet Equihash parameters or personalization. The (192,7) vectors are the real mainnet genesis and height-1 headers; a node built with altered parameters rejects the existing chain and forks from it. Fix the code that drifted instead. Verbose: **`--log_level=test_suite`** or **`message`**.

---

## 8. Platform evidence and operational checks

A green test run proves **one** OS. v4.1.0 needs an honest matrix plus a few node-lifecycle soaks. Do not treat a green macOS gate as Linux ELF, Windows, mining, or Zerowallet coverage.

Receipts live in gitignored **`.build/`**. Scratch chain data stays outside the repo.

### 8.1 Platform matrix

| Layer | macOS ARM64 | Linux x86_64 (Ubuntu 24.04 class) | Windows |
|-------|-------------|-----------------------------------|---------|
| Build | **Done** (`./zcutil/build.sh`) | **Rebuild at the release tip** (recommended next gate) | **Not run.** MXE cross-build from Linux; this program has never produced or executed `zerod.exe` |
| `./contrib/run-tests.sh --all` (release test run: C++ gate filters, Tier A, B pass, Ext pass) | **Run on the release commit** | **Run on the release commit** | Not run; no Windows runner |
| `--suite` (ELF `check-security` / `no-dot-so`, full `rpcbind`) | **N/A** -- Darwin skips ELF stages | Optional; adds the ELF checks | N/A for PE |
| Packaging | N/A | `release-linux.sh` is not a test run | No signed installer |
| Checksums / signatures | `zcutil/release-macos.sh` writes `SHA256SUMS`; signing needs a Developer ID (`--sign`, `--notarize`) | `zcutil/release-linux.sh` writes `SHA256SUMS`; signing method undecided | `zcutil/release-win.sh` writes `SHA256SUMS`; Authenticode with `--sign-pkcs12` |
| Isolated mining RPC (Tier B `getblocktemplate`) | Tier B exists in the harness; isolated mainnet template not recorded | Same | Not run |
| **Live mining** (operator `gen=1` / `setgenerate` on mainnet) | **Optional observation** -- solver activity via `getmininginfo` / `debug.log`; not a found-block requirement | Same | Same |
| Zerowallet | **Manual only** -- start or attach, watch addresses / History load, spinner, error dialogs. No automated UI. No send/receive, bulk, or mixed-type tx in this program | Same if used | Same if used |

**RC bar:** macOS and Linux: `./contrib/run-tests.sh --all` on the release commit. Without `--strict` the runner exits 0 and prints WARNING when a step fails, so read its summary. Windows: first successful MXE build and one start of `zerod.exe`. **Signing:** `SHA256SUMS` on every shipped artifact; the platform signature method is undecided (BUILD_ZERO section 2.6). Record hashes and signatures as present or **explicitly missing**. Maintainer decides which OS gates are hard blocks. Darwin skips full `rpcbind`; run the RPC tiers serially (`--jobs>1` can hang `paymentdisclosure`).

### 8.2 Automating beyond the harness

| Layer | What | Exists |
|-------|------|--------|
| **0 -- merge gate** | `--strict` | `contrib/run-tests.sh` |
| **1 -- widen** | `--all` (macOS), `--suite` (Linux; includes `--all`), `release-linux.sh` smoke | Same runner |
| **2 -- node lifecycle** | COLD / RESTART / ATTACH on a scratch datadir | `contrib/ops-validate.sh smoke` |
| **3 -- clients / mining** | Zerowallet visual; Equihash verify/solve; regtest mine | GUI in the wallet repo. `verifyeq` / `solveeq` / `mine` here |

Receipts: **`.build/`** (`ready-*.txt`, `ready-latest.txt`, build logs, `test-logs/`, `ops-status.jsonl`). Scratch chain data: **`ZERO_OPS_LAB`** (default `/tmp/zero-ops-validate`), never the default user datadir, never this tree unless `--force`. Conf: `contrib/zero-conf.sh` from `contrib/conf-templates/` (default template **prod**, default file `/tmp/zero.conf`). Never sticky `reindex=1`. Sapling params are system setup, not this cycle.

Ports: **23801-23820** are reserved for deployments and tests that use chain defaults (P2P 23801 / RPC 23811 and test/regtest siblings). Isolated ops defaults are RPC **23941** (LAB) and **23951** (`verifyeq` / `solveeq` / `mine`). QA harness uses ephemeral **11000+** / **12000+**. `ops-validate` refuses a LAB rpcport in 23801-23820 unless `--force`. `live` talks to SRC on the operator's configured RPC port.

### 8.3 Operational catalog

`contrib/ops-validate.sh` is the product soak and short RC driver (isolated LAB under `/tmp` by default). Bundles: **`short`** (equihash + verifyeq + smoke), **`smoke`** (cold + restart). One trial per invocation except those bundles. Default load stop is height 100000 and `-disablewallet`. Packed snaps and `bootstrap.dat` stay outside git. `--force` / `ZERO_OPS_FORCE=1` overrides datadir, running-`zerod`, and port gates (WARNING).

| Command | Pass |
|---------|------|
| `smoke` | `cold` then `restart` |
| `short` | `equihash` + `verifyeq` + `smoke` |
| `cold` | RPC up on empty scratch, clean `stop` |
| `restart` after `cold` | Tip unchanged |
| `keep` on a start cmd, then `attach` | `getblockchaininfo` on LAB |
| `live` | RPC to SRC (operator datadir); does not start or stop |
| `reindex` / `reindex all` | `-reindex` from snap; `all` = snap tip |
| `bootstrap` | `-loadblock` to 100000 (`all` = end of file) |
| `rescan` | keep indexes, `-rescan`, wait Done loading (needs chainstate in snap) |
| `copy` | rsync SRC blocks+chainstate into LAB, wait stable tip. Stop every `zerod` first |
| `equihash` | Boost `equihash_tests` (KATs; no `zerod`) |
| `verifyeq` / `verifyeq N` | isolated `-regtest` + `zcbenchmark verifyequihash` N (default 20; MAIN **(192,7)**); times in ms |
| `solveeq` / `solveeq N` | isolated lab; `zcbenchmark solveequihash` N times (default 1, ~50s each); per-sample seconds plus min/mean/median/stdev when N>1; `rpcservertimeout=3600`; `ENABLE_MINING`; not the RC bar |
| `mine` / `mine N` | isolated `-regtest` `generate` N (default 8); Equihash **(48,5)**; does **not** mine mainnet |

Defaults when no option is given: lab datadir `/tmp/zero-ops-validate` (isolated commands use `/tmp/zero-ops-eq`), template `lab` (listen off, no peers), no wallet (`-disablewallet`), RPC port 23941 (isolated commands 23951), stop height 100000, snapshot `tiny`, wait 1800 s, source datadir = the node default for the OS.

| Group | Commands | Needs | Use when |
|-------|----------|-------|----------|
| Isolated, no chain | `equihash`, `verifyeq`, `solveeq`, `mine` | Built binaries | Any change to PoW, mining, or Equihash code; `solveeq` only for timing |
| Lab lifecycle | `cold`, `restart`, `smoke`, `short`, `attach`, `stop`, `keep` | Built binaries | Every release candidate (`short`); startup or shutdown changes |
| Operator data, read-only | `live` | A running node on the source datadir | Release candidate check against real data |
| Chain replay | `copy`, `reindex`, `rescan`, `bootstrap` | Source datadir stopped; snapshot archives or a `bootstrap.dat` copy | Changes to reindex, import, rescan, index flags, or wallet sync |

Wallet ids: `p0` / `p1` / `fat` / `none` or `--wallet=PATH` (`wallets` lists paths). On `verifyeq` / `solveeq` / `mine`, a bare number is the sample or block count, not wallet id `0`/`1`/`3`. `keep` leaves LAB `zerod` up. `stop` always stops LAB.

P2P-CATCHUP is not in this menu. GBT is Tier B `getblocktemplate` (`-B` / `--all`).

**RC bar:** layer 0 + `ops-validate.sh short` + `live` when SRC is up + checksums/signatures + wallet visual. `solveeq` is optional (default one long trial; pass N for repeats).

### 8.4 Zerowallet soak

No UI harness in this tree. Node-side: `attach` + template `zerowallet`. macOS GUI path may be `Application Support/Zero` vs canonical `zero`. Align `rpcuser` / `rpcpassword` / `rpcport`. Do not send. Visual: addresses, History, spinner, dialogs. Spinner-idle is not a sync proof.

### 8.5 Mining

Three different things, not one command.

Isolated tests in this tree (scratch LAB, not the operator datadir):

- Boost KATs: `ops-validate.sh equihash` or `./src/test/test_bitcoin -t equihash_tests`
- Timed MAIN **(192,7)** verify / solve: `verifyeq` / `solveeq` (`zcbenchmark`; solve does not submit a block)
- In-process CreateNewBlock: `./src/test/test_bitcoin -t miner_tests`
- Daemon `generate` on **regtest (48,5)**: `ops-validate.sh mine`

Operator CPU miner on **mainnet (192,7)** is `gen=1` / `setgenerate`. Template **prod** ships `gen=0`. Mainnet and testnet set `fMiningRequiresPeers`, so the miner waits until there are peers and the node is not in IBD. Coinbase needs a wallet or `-mineraddress`. `setgenerate` is the RPC for mainnet/testnet; on regtest use `generate` (that is what `mine` calls). One OptimisedSolve is on the order of a minute; finding a mainnet block at current difficulty is not expected. Watch `getmininginfo` (`generate`, `localsolps`) and `debug.log` (`Using Equihash solver`, `Running ZeroMiner`). `setgenerate false` turns it off.

Tier B `getblocktemplate` is the pool/template claim (`-B` / `--all`).

### 8.6 Explorer consumer

Template `insight`. Flags must match the copied index. Optional `getaddressbalance` / `getaddresstxids` on a disposable copy. No `reindex=` in conf.

---

