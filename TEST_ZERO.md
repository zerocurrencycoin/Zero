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

## 8. Platform evidence and operational checks

`--strict` proves the contributor gate on **one** OS. v4.0.1 needs an honest matrix plus a few node-lifecycle soaks. Do not treat a green macOS gate as Linux ELF, Windows, mining, or Zerowallet coverage.

Lab soaks reuse the same fixture rules that the maintainer perf tree already uses: a disposable scratch datadir, packed chain snaps outside git, wallet copies injected by env, and one long trial per invocation. Do **not** copy that perf campaign set into this product tree. A later `contrib/ops-validate.sh` (or equivalent) should implement only the catalog below.

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

Four layers. Implement layer 2 as a later `contrib/ops-validate.sh` that **runs one catalog id per invocation** and appends a JSONL ledger. Do not wrap all scenarios in one overnight script unless each trial can restart alone (separate datadir, append-only status, resume from the next unfinished id).

| Layer | What | Exists |
|-------|------|--------|
| **0 -- merge gate** | `--strict` (C++ working filters + Tier A RPC) | `contrib/run-tests.sh` |
| **1 -- widen** | `--all`, Linux `--suite`, `release-linux.sh` smoke | Same runner; platform-gated |
| **2 -- node lifecycle** | Disposable datadir; start / stop / restart / attach; `-reindex`; `-loadblock`; `-rescan`; P2P catch-up; `-disablewallet`; Insight-flagged copy | **Catalog below.** Driver not in tree yet. Record: scenario id, OS, binary hash, tip height, `wall_s`, exit, last `debug.log` error, conf digest |
| **3 -- clients / mining** | Zerowallet attach + visual; isolated Equihash **solve**; live hash optional | GUI clicks stay in the wallet repo. Node-side attach/reporting is in scope for the layer-2 driver. Mining solve is opt-in (not `--strict`). `z_sendmany` / mixed tx stay out |

**Scratch contract** (same rules whether the driver lives here or in a lab tree):

- Never use the default user datadir as a writable lab (`~/Library/Application Support/zero`, `Application Support/Zero`, `~/.zero`, `%APPDATA%\zero`). Refuse that path. Do not write lab scratch into this product tree.
- Packed snaps (`tiny` / `short` / `full` chain copies) live **outside git**. Unroll only `blocks/` + `chainstate/` (includes `blocks/index/`). Do not disturb the archive original.
- Wallet files enter by env (copy `wallet.zero` in). Profiles: empty, known-small (p0), mid (p1), fat. Same Berkeley DB generation as the binary under test. Never copy a lab wallet back onto a live datadir.
- `bootstrap.dat` / `-loadblock=` uses a copy or softlink. Never mutate the original. Bootstrap mode wipes `chainstate/` (and usually `blocks/`) so the import is the chain, not a leftover index.
- Write a scratch `zero.conf`: `rpcuser` / `rpcpassword` / `rpcport`, `listen=0` for isolated soaks. Never leave sticky `reindex=1` in conf (that forces a reindex on every start). Insight flags in conf must match how `blocks/index/` was built, or `-reindex` fires.
- Params stay in the platform ZcashParams path (`./zcutil/fetch-params.sh`). `-datadir` does not relocate them.
- One trial per invocation for anything expected to exceed ~20 minutes. Append-only ledger; resume by id.

### 8.3 Operational catalog

Run against a **copy** of a known-good datadir (or a short packed snap). Pass: process reaches RPC, `getblockchaininfo` `blocks` matches expectation, `debug.log` has `Done loading` / `Reindexing finished` as applicable, clean `stop`. Fail: hang past the scenario bound, `AbortNode`, unexpected `-reindex` from sticky `reindex=1` in conf, datadir mismatch, Insight flags that do not match the copied index.

| Id | Scenario | Typical bound | Notes |
|----|----------|---------------|-------|
| **OPS-START-COLD** | Fresh `-datadir=SCRATCH` (empty or params-only), `-listen=0 -connect=0`, wait RPC, `stop` | Minutes | Confirms init, params, RPC creds. Not sync. |
| **OPS-START-WARM** | Copy chain+wallet to scratch, start **without** `-reindex`, wait `Done loading`, `getblockcount` | Minutes if already at tip; hours if the copy is behind and P2P is on | Default-off P2P (`-connect=0`) for a bounded load test |
| **OPS-RESTART** | `stop`, start again on the same scratch, tip unchanged | Minutes | Flush / lock / wallet reopen |
| **OPS-NOWALLET** | `-disablewallet` on a chain copy | Minutes | Explorer-style. Pair with Insight flags only when the copied index was built with them |
| **OPS-REINDEX** | `-reindex` on a chain copy (no sticky `reindex=` in conf) | **Long** -- tiny snap is the smoke; full tip is a solo trial | Resume markers `L`/`H`/`R` if interrupted. On this 4.0.1 line, a multi-million-block `LoadBlockIndexDB` may ignore `SIGTERM` until RPC is up -- prefer a height-bounded snap for smoke |
| **OPS-BOOTSTRAP** | Empty chainstate, `-loadblock=` / `bootstrap.dat` copy (never mutate the original) | **Long**; windowed height cap if the importer supports stop-at-height | One file / one trial |
| **OPS-RESCAN** | Indexed chain + existing `wallet.zero`, `-rescan`, no `-reindex` | **Long** on fat wallets | Genesis-to-tip fat rescan is a solo trial |
| **OPS-P2P-CATCHUP** | Chain copy behind live tip, P2P on, wait `blocks` to move | **Long** / unbounded | Separate from `-connect=0` soaks |
| **OPS-GBT** | `getblocktemplate` on regtest or an isolated mainnet template **without** submitting work | Minutes | Proves the mining **RPC**, not a timed Equihash solve |
| **OPS-ATTACH** | Do not spawn `zerod`; poll RPC on an already-running node using that datadir's `zero.conf` | Minutes | Shared by Zerowallet attach and explorer consumers. Record pid, `rpcport`, warmup, `getblockchaininfo` / `getwalletinfo` or the nowallet error |

**When to run** (macOS first; Linux after a rebuild at the tag). Do not batch the long column.

| Band | Ids | Role |
|------|-----|------|
| **Smoke (first session)** | START-COLD, START-WARM, RESTART, NOWALLET, GBT, ATTACH | Minutes each; proves init, conf, RPC, restart, explorer-style start |
| **Same-week bounded** | REINDEX on a **tiny** snap; BOOTSTRAP on a **windowed** `bootstrap.dat` if a copy exists | One id per invocation |
| **Scheduled solo** | REINDEX full tip; RESCAN fat; P2P-CATCHUP; isolated mainnet solve | Not RC-blocking unless the maintainer says so |
| **RC bar** | Layers 0-1 + smoke band + checksums/signatures + wallet visual + explorer RPC smoke | Long soaks remain evidence, not an automatic hard block |

**Not in this catalog:** sending or receiving coins (transparent, Sprout, Sapling, mixed, bulk); pool/GBT production hash; Zerowallet History correctness beyond "did the UI load."

### 8.4 Zerowallet soak

Zerowallet has **no** automated UI tests in this node tree. The wallet repo owns GUI clicks. This catalog covers **node-side** launch, attach, conf alignment, lifetime, and state reporting so the GUI is not the only sensor.

**Conf and datadir.** Canonical macOS folder is `Application Support/zero`; some wallet builds still open `Application Support/Zero` (case collision on APFS). Mainnet RPC default is **23811** (`rpcport` in `zero.conf`). The wallet must use the same `rpcuser` / `rpcpassword` / `rpcport` / datadir as the node it talks to. Wallet-only extras (`txindex`, `deletetx*`, `consolidation*`) are wallet policy, not required for bare `zerod`.

**Modes:**

1. **Launch** -- start `zerod` on a chosen datadir, wait RPC, then start the GUI.
2. **Attach** -- GUI (or a later script) reads `zero.conf` from that datadir and talks to an already-running `zerod` (OPS-ATTACH).
3. **Wallet-spawned** -- GUI starts embedded `zerod`; still poll the same RPC and `debug.log`.

**Track (JSONL, append-only):** pid, start time, `Done loading`, RPC warmup (`-31` / `-33` if used), `getblockchaininfo` (`blocks`, `headers`, `verificationprogress`, `connections`), `getwalletinfo` (`txcount`, and note counts if this binary exposes them), log path, conf digest (rpcport + flags, not the password). Expand later with RSS and wallet file size. Do **not** call send RPCs.

Until a wallet-repo driver exists, 4.0.1 client evidence is still a **manual** pass on macOS:

1. Choose a **non-lab** datadir you accept; resolve `zero` vs `Zero`.
2. Use one of the three modes above.
3. Watch: RPC connect, address list, transaction History populate, spinner stop, error dialogs if any.
4. Do **not** treat spinner-then-idle as a sync or reindex proof -- that is `zerod` logs / `getblockchaininfo`.
5. Do **not** generate, send, or receive transactions for this soak.

Record OS, wallet build, node tag, attach vs launch, and whether History populated without a dialog. That is observation, not a merge gate.

### 8.5 Mining

Mining is a ladder. Live hash is one way to see that a template can become a block; it is **not** the definition of "mining works" and it is not representative of pool or isolated solve time.

| Step | What | Status |
|------|------|--------|
| **A** | Tier B `getblocktemplate` (regtest RPC) | In the harness |
| **B** | OPS-GBT on a disposable node (regtest or isolated mainnet template, no submit) | Catalog; not yet a checked-in driver |
| **C** | Regtest `generate` / (48,5) solve | Lab opt-in; not `--strict` |
| **D** | Isolated mainnet-template **solve** (192,7), no pool, no `submitblock` to public peers unless that is a separate named trial | Not confirmed; the step that would let 4.0.1 claim "mining works" |
| **E** | Live generation | Optional observation only |

Do not list mining as validated for v4.0.1 until step D is recorded. `contrib/zero.conf` `gen=0` stays the operator default.

### 8.6 Explorer consumer

Insight-style soaks are the same layer-2 driver with a different conf profile, not a second harness. Typical flags: `-experimentalfeatures -insightexplorer -txindex`, often `-disablewallet`. The copied `blocks/index/` must have been built with those flags; a stock index plus Insight conf triggers `-reindex`.

Smoke on a disposable copy: RPC alive, `getaddressbalance` / `getaddresstxids` on a known transparent address, clean `stop`. ZMQ and the HTTP Insight API are wiring checks after deploy, not this catalog. Host libc/ABI floors are a packaging concern (BUILD_ZERO: build OS sets the binary floor), not a TEST_ZERO matrix.

OPS-NOWALLET plus OPS-ATTACH covers "zerod already running, explorer talks RPC." Do not put `reindex=1` in the explorer `zero.conf`.

---

