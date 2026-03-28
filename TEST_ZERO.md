# TEST_ZERO

**Audience:** Builders and contributors who **run** tests, **read** harness output, and **narrow** failures (C++, Python RPC, full driver).

**Authoritative lists:** `contrib/run-tests.sh` (**`PYTHON_PASSING`**), `qa/pull-tester/rpc-tests.sh` (**`testScripts`**, **`testScriptsExt`**). If this file disagrees with those scripts, **the scripts win**.

**Related:** [BUILD_ZERO.md](BUILD_ZERO.md) (toolchain, Python **3.10+**, produced binaries). [README.md](README.md) documentation map. Maintainer depth on exclusions, gaps, and phased work: **[UpdateTests.md](UpdateTests.md)**.

---

## Document map

- **Harness changelog (recent)** — Fixes applied to **`getchaintips`**, **`run-tests.sh`**, **`rescan_import`**; open items for parallel RPC.
- **Accounting** — What “run” and “pass” mean; Tier A allowlist; weak C++ “pass” cases.
- **Interpreting results** — Log signals for `run-tests.sh`, GTest, Boost, Equihash.
- **Process** — Wrapper flags, extending tests, troubleshooting.
- **Reference** — Harness roles, `run-tests.sh` modes, `full_test_suite.py`, pass-only filters, how to invoke RPC/C++ suites. **No duplicate copies** of Tier B/C script lists (read `rpc-tests.sh`).
- **RPC harness details** — Coinbase maturity helpers, Tier A skip patterns (chain tip, peers, heights), extended RPC risks.
- **Known failures, hangs, and crashes** — Excluded C++ tests, root causes, disposition, plan.
- **Appendix** — Maturity constants, RPC driver flags, repo CSVs.

---

## Harness changelog (recent)

| Change | Location | Effect |
|--------|----------|--------|
| Split topology when **`split=True`** | **`qa/rpc-tests/getchaintips.py`** **`setup_network`** | Connect only **0–1** and **2–3** during the partition so the two halves actually fork (previously **0–2** / **1–2** bridged the split). |
| Shorter bootstrap | Same | **`CHAIN_BOOTSTRAP = 30`** for initial mining (was 200); **`join_network`** still avoids re-mining when the chain is already long enough. |
| Branch assertions | Same | **`expected_branchlen`** from **`shortTip['height'] - CHAIN_BOOTSTRAP`**; active height matches long chain after rejoin; accepts one or two tips per existing semantics. |
| Background wait / exit codes | **`contrib/run-tests.sh`** **`run_bg`** | Set **`BG_LAST_PID=$!`**; avoid **`$(run_bg …)`** (subshell caused **`wait $pid`** to fail). GTest/Boost and Tier A parallel children wait on real child PIDs. |
| **`rescan_import` executable bit | Git index **`qa/rpc-tests/rescan_import.py`** | **`100755`** so **`rpc-tests.sh`** can execute the script (avoids **`Permission denied`** when checkout mode was **`100644`**). |

**Open (harness):** **`--jobs>1`** Tier A RPC is **best-effort** only—**`paymentdisclosure`** has been observed **hung** under **`--jobs=4`** (macOS). No fix in-tree yet; use **serial** for the contributor gate. See **Parallel Tier A** under Reference.

---

## Verification snapshot (working vs pending)

**Treated as working (serial default gate):**

| Step | Command / scope | Notes |
|------|-------------------|--------|
| Quick + symbols | **`./contrib/run-tests.sh --quick --strict`** | No GTest/Boost/RPC. |
| C++ only | **`./contrib/run-tests.sh --no-python --strict`** | Pass-only GTest + Boost; **~1m20s–1m30s** wall indicative (hardware-dependent). |
| Full default gate | **`./contrib/run-tests.sh --strict`** | Pass-only GTest + Boost + **Tier A serial** (**`PYTHON_PASSING`**). |
| Single Tier A script | **`env PYTHON=python3 ./qa/pull-tester/rpc-tests.sh <basename>`** | Isolates one RPC test. |

**Tier A scripts (all on allowlist):** **`blockchain`**, **`disablewallet`**, **`httpbasics`**, **`reindex`**, **`rescan_import`**, **`rescan_startup`**, **`decodescript`**, **`keypool`**, **`paymentdisclosure`**, **`prioritisetransaction`**, **`wallet_treestate`**, **`wallet_anchorfork`**, **`getchaintips`**, **`rewind_index`**, **`wallet_overwintertx`**, **`wallet_changeaddresses`**, **`shorter_block_times`**, **`p2p_nu_peer_management`**, **`txn_doublespend`**.

**Indicative wall times (serial RPC, one dev machine, not a SLA):** **`getchaintips`** ~20–25s; **`wallet_overwintertx`** ~43s; **`txn_doublespend`** ~44s; **`paymentdisclosure`** ~30s; **`rescan_import`** ~32s.

**Pending / unreliable:**

| Item | Notes |
|------|--------|
| **`--jobs>1`** for Tier A | Parallel **`rpc-tests.sh`** children; **not** a supported gate—hangs possible (**`paymentdisclosure`** @ **`N=4`** observed). |
| Extended / Tier B+C bulk | **`--fail`** / **`--all`** / **`-extended`** — high cost; not the default allowlist gate. |
| Default-excluded C++ | **`CachedWitnesses*`**, **`WriteCrypted*`**, **`miner_tests`**, **`rpc_wallet_encrypted_wallet_sapzkeys`**, **`Alert_tests`** — see **Known failures**. |

---

## Accounting: run, pass, and skip

- **Run:** The test **executed its intended checks**. Setup-only or early **`skip_test`** paths do **not** count as that scenario having been run.
- **Pass:** Those checks **succeeded**. **Exit 0** after **`skip_test`** is **skipped**, not a pass for coverage reporting.
- **`run-tests.sh`:** Without **`--strict`**, failures set **`OVERALL_FAIL`**, print **`WARNING`**, and the shell still exits **0**—read **`PASS:`** / **`FAIL:`** lines. With **`--strict`**, exit **1** if any selected step failed.
- **Tier A RPC:** **`PYTHON_PASSING`** is an allowlist; other scripts may fail outside that gate.
- **C++ nuance:** Some Boost cases **return early** (e.g. legacy **(96,5)** Equihash vectors when mainnet is **(192,7)**) and still show as passed—they do **not** prove **(96,5)** ran. See **Interpreting results → Equihash**.

---

## Interpreting results

### `contrib/run-tests.sh`

| Signal | Meaning |
|--------|---------|
| **`PASS: <step>`** | Subprocess exited **0**. |
| **`FAIL: <step>`** | Non-zero; see cited **`.log`** under **`test-logs/`**. |
| **`WARNING: one or more steps failed`** | Default: failures occurred; exit **0** unless **`--strict`**. |
| **`FAIL: one or more steps failed (--strict)`** | **`--strict`** and at least one failure → exit **1**. |

**`--strict`:** Implemented at the end of **`contrib/run-tests.sh`** via **`bump_fail`** / **`OVERALL_FAIL`**. CI (e.g. **`.github/workflows/tests.yml`**) uses **`./contrib/run-tests.sh --strict`** after the build. **`--quick --strict`** only stricts the quick steps (no GTest/Boost/RPC unless you drop **`--quick`**).

### GTest (`./src/zero-gtest`)

**`[  PASSED  ] N tests.`** — all executed tests in the run passed. **`YOU HAVE M DISABLED TEST`** — some suites disabled by build/filter. **`FAILED`** or non-zero exit — isolate with **`--gtest_filter=Suite.Case`**.

### Boost (`./src/test/test_bitcoin`)

**`*** No errors detected`** — enabled suites that ran passed. Non-zero exit — find the first **`error:`** / failed assertion above. **`skipped because disabled`** — whole suite off for this build, not a failure.

### Equihash (Boost `equihash_tests`)

**Source:** **`src/test/equihash_tests.cpp`**. **Run:** **`./src/test/test_bitcoin -t equihash_tests`**.

- **(96,5) solver/validator vectors** return early when mainnet **`nEquihashN != 96`** — compatible no-op on Zero, **not** **(96,5)** coverage.
- **Zero-specific cases** exercise **(192,7)** mainnet genesis (valid + corrupt **`nSolution`**) and **(48,5)** regtest genesis.

Failures in the Zero-specific cases usually mean **`chainparams.cpp`** / **`pow.cpp`** / **`CheckEquihashSolution`** drift. Verbose: **`--log_level=test_suite`** or **`message`**.

---

## Process

### `contrib/run-tests.sh` — flags to re-check after parser changes

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

Zeronode RPC coverage: **`rpc_zeronode_tests`**, **`rpc_zeronode_budget_tests`**. Further build/test prerequisites: **[BUILD_ZERO.md](BUILD_ZERO.md)**.

### Troubleshooting

- **Blake2 / imports:** Python **3.10+** and **`hashlib.blake2b`** (see **[BUILD_ZERO.md](BUILD_ZERO.md)** § Python).
- **`PYTHON` unset** when calling **`rpc-tests.sh` by hand:** use **`env PYTHON=python3 ./qa/pull-tester/rpc-tests.sh …`**. **`contrib/run-tests.sh`** sets **`PYTHON`** via **`find_python3`**.
- **RPC binaries not found:** **`qa/pull-tester/tests-config.sh`**, **`BUILDDIR`**.
- **Boost/GTest noise:** one suite at a time, or **`contrib/run-boost-individual.sh`**.
- **Orphaned `zerod`:** after crashes, **`pkill -f "zerod -datadir="`** if needed.
- **Parallel RPC (`--jobs=N`) stuck:** see **Reference → Tier A → Parallel Tier A**; kill stray **`zerod`** / hung **`rpc-tests.sh`** children if needed.

---

## Reference

### Harness roles

| Harness | Entry | Role |
|---------|-------|------|
| Util | `src/test/bitcoin-util-test.py` | Vectors / encoding |
| secp256k1 / univalue | `make -C src/secp256k1 check`, `make -C src/univalue check` | Libraries |
| check-symbols / check-security | `make -C src …` | Policy / hardening |
| GTest | `src/zero-gtest` | Wallet / consensus-oriented cases |
| Boost | `src/test/test_bitcoin` | RPC, script, PoW, zeronode RPC |
| RPC Python | `qa/pull-tester/rpc-tests.sh` | Multi-node regtest |
| full_test_suite | `qa/zcash/full_test_suite.py` | Ordered stages, fail-fast |

### Common commands

```bash
./contrib/run-tests.sh --quick          # smoke: util, secp, univalue (+ optional symbol/security)
./contrib/run-tests.sh --strict         # contributor gate + exit 1 on any failure
./contrib/run-tests.sh                  # pass-only C++ + Tier A RPC (serial)
./contrib/run-tests.sh --full           # full_test_suite.py (see below)
./qa/pull-tester/rpc-tests.sh NAME      # one script (basename or .py)
./qa/pull-tester/rpc-tests.sh -extended # Tier B + Tier C per rpc-tests.sh
./src/zero-gtest '--gtest_filter=Suite.Case'
./src/test/test_bitcoin -t rpc_tests
```

### `contrib/run-tests.sh` modes

| Mode | GTest | Boost | RPC |
|------|-------|-------|-----|
| **Default** | Pass-only filter | Pass-only exclusions | Tier A (**`PYTHON_PASSING`**) |
| **`--quick`** | Skip | Skip | Skip |
| **`--fail`** | Pass-only | Unfiltered | **`-extended`** |
| **`--all`** | Unfiltered | Unfiltered | **`-extended`** |
| **`--full`** | Via full suite only | Via full suite only | Via full suite only |
| **`--no-python`** | Per mode | Per mode | Skip |
| **`--jobs=N`** | — | — | Tier A RPC only; **default pass-only** (see **Parallel Tier A**) |

**`--strict`:** Combine with default, **`--quick`**, **`--fail`**, **`--all`**, or **`--no-python`** (not **`--full`**). **`PYTHON`**, **`LOG_DIR`** (default **`test-logs/`**), **`ZERO_MINE_COINBASE`**: see **`contrib/run-tests.sh`** header and **RPC harness details** below.

### `full_test_suite.py`

**Invoke:** **`python3 qa/zcash/full_test_suite.py`** or **`./contrib/run-tests.sh --full`**. Fails on first failed stage.

**Stage order:** `btest` → `gtest` → `sec-hard` → `no-dot-so` → `util-test` → `secp256k1` → `univalue` → `rpc` (Tier B).

**Unfiltered:** **`--unfiltered`** or **`ZERO_FULL_SUITE_UNFILTERED=1`** removes GTest/Boost pass-only filters (hang/crash risk on excluded wallet tests).

**Darwin:** **`contrib/run-tests.sh`** passes **`--skip sec-hard --skip no-dot-so`** on Darwin because those stages target **ELF** / **`depends/` `.so`** layout—**release artifact checks**, not a claim that tests behave differently on macOS. Linux runs those stages when not skipped.

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
| GTest | **`WriteCryptedSaplingZkey*`** | **`CDB::Rewrite`** / wallet open → **hang** |
| GTest | **`CachedWitnesses*`** | Harness / **`pcoinsTip`** / death test mismatch → **fail** |
| Boost | **`Alert_tests`** | Not compiled / deprecated alerts |
| Boost | **`miner_tests`** | **(192,7)** vs upstream **(96,5)** assumptions |
| Boost | **`rpc_wallet_encrypted_wallet_sapzkeys`** | Same rewrite **hang** class as GTest encrypt tests |

**`equihash_tests`** stays in pass-only; interpretation: **Interpreting results → Equihash**. List suites: **`./src/zero-gtest --gtest_list_tests`**, **`./src/test/test_bitcoin --list_content`**.

### RPC driver

| Invocation | Scripts |
|------------|---------|
| *(no args)* | All **`testScripts`** (Tier B)—order and names **only** in **`qa/pull-tester/rpc-tests.sh`**. |
| **`-extended`** | Tier B + **`testScriptsExt`**—same file. |
| **`rpc-tests.sh NAME`** | One match from those arrays |

Requires wallet-enabled build (**`ENABLE_BITCOIND`**, **`ENABLE_UTILS`**, **`ENABLE_WALLET`**). Config: **`qa/pull-tester/tests-config.sh`**.

### Tier A (contributor gate)

**Order matches `PYTHON_PASSING` in `contrib/run-tests.sh`:** `blockchain`, `disablewallet`, `httpbasics`, `reindex`, `rescan_import`, `rescan_startup`, `decodescript`, `keypool`, `paymentdisclosure`, `prioritisetransaction`, `wallet_treestate`, `wallet_anchorfork`, `getchaintips`, `rewind_index`, `wallet_overwintertx`, `wallet_changeaddresses`, `shorter_block_times`, `p2p_nu_peer_management`, `txn_doublespend`.

**Per-script skip RCA and IDs (6.x):** **[UpdateTests.md](UpdateTests.md)** § RPC Python. **Common themes:** **720** maturity, **`chaintip`** / NU height vs mining plan, **`getchaintips`** shape after rejoin, P2P **`version`** set.

**Parallel Tier A (`--jobs=N`, `N>1`):** Only when the RPC step is the **default Tier A** list (**`PYTHON_PASSING`**): not with **`--fail`** / **`--all`** (those use **`-extended`**), not with **`--no-python`**, not with **`--full`**. **`N=1`** (serial) is the path **CI and the contributor gate** assume.

**Reliability:** Parallel runs start **many `zerod` processes** (Equihash + RAM). That is **best-effort throughput**, not a supported merge gate: scripts can **hang or flake** under load (e.g. **`paymentdisclosure`** observed stuck with **`--jobs=4`** on one macOS run). If a run stalls, use serial (**omit `--jobs`**) or a **lower `N`**; confirm with **`test-logs/…-rpc-*.log`**. GTest/Boost in **`run-tests.sh`** are **not** parallelized by **`--jobs`** (only the Tier A RPC children).

### Direct one-off invocations

Util / secp / univalue can also run via **`make -C src secp256k1-check`**, **`make -C src univalue-check`**, or paths in **`src/test/bitcoin-util-test.py`** (see script / Makefile).

---

## RPC harness details

### Coinbase maturity and helpers

Zero **regtest** uses **`COINBASE_MATURITY` = 720** (**`src/consensus/consensus.h`**). Upstream Bitcoin/Zcash-style scripts often assume **100**—porting must adjust mining or expectations (**[UpdateTests.md](UpdateTests.md)**).

**`ZERO_MINE_COINBASE=1`:** In **`qa/rpc-tests/test_framework/util.py`**, **`ensure_coinbase_utxos()`** may mine **1000** blocks when no mature coinbase exists. Without it, that helper returns false and callers often **skip**.

**Helpers:** **`has_coinbase_utxos`**, **`mine_until_node_has_mature_coinbase`** (50-block steps), **`ensure_coinbase_utxos`** (bulk path gated by env), **`ensure_mature_coinbase_or_skip`** (incremental then bulk). Scripts that call **`ensure_coinbase_utxos`** (directly or via **`ensure_mature_coinbase_or_skip`**): **`rescan_import`**, **`wallet_changeaddresses`**, **`wallet_overwintertx`**, **`shorter_block_times`** (the last uses **`ensure_coinbase_utxos`** without the incremental wrapper—often needs **`ZERO_MINE_COINBASE`** or skips early).

**`wallet_overwintertx`:** Uses **`-nuparams`** for Overwinter / Sapling / Blossom with **Blossom activation above** the post-maturity tip (**720** + split mining) so **`chaintip`** stays Sapling until the script mines to **`upgrades['2bb40e60'].activationheight`**. **`createrawtransaction`** expiry checks use **`getblockcount() + 1 + 3`**. **`shorter_block_times`:** Without env, skip at maturity gate; with env, may fail on **expiryheight** / activation constants—derive from **`getblockchaininfo`**.

### Chaintip, `getchaintips`, P2P

- **`wallet_overwintertx`:** If **`chaintip`** is not Sapling (**`7361707a`**), the script still **skips** (unexpected NU layout). **`consensus.nextblock`** can match **`chaintip`** when the next height is still Sapling (see **`getblockchaininfo`** in **`src/rpc/blockchain.cpp`**).
- **`getchaintips`:** After **`join_network`**, **`getchaintips`** may return **two** tips (**`valid-fork`** or **`valid-headers`**) or a **single** active tip on the best chain; **`getchaintips.py`** accepts both. **`mininode`** **`MAGIC_BYTES['regtest']`** must match **`pchMessageStart`** in **`chainparams.cpp`** (Zero ≠ Bitcoin). **`setup_network(split=True)`** must **not** connect across the partition (**only 0–1** and **2–3**); otherwise both sides stay on one tip and fork assertions fail. Initial bootstrap uses **`CHAIN_BOOTSTRAP`** (**30** in **`getchaintips.py`**); **`join_network`** avoids re-mining when **`getblockcount() >= CHAIN_BOOTSTRAP`**.
- **`p2p_nu_peer_management`:** Skips when no peers or **`version`** not in the set the test expects—align **`mininode`** with **`src/version.h`** / Zero regtest acceptance.

### Tier B / `-extended` (bulk RPC)

High **wall time**; per-script **`zerod`** processes. Risks: wallet **encrypt/rewrite** hangs if unfiltered Boost runs, **`script_test.py`** disabled in array, maturity/subsidy mismatches vs **720** / **`zero_regtest_subsidy`**. **Promotion to Tier A:** main path runs without **`skip_test`** on defaults; add basename to **`PYTHON_PASSING`**.

### RPC failure signals (index)

| Pattern | Typical cause | Pointer |
|---------|---------------|---------|
| `need 720+`, premature coinbase spend | Maturity | This section + Appendix |
| Balance / mempool mismatch | Subsidy / halving | **`zero_regtest_subsidy`**, **[UpdateTests.md](UpdateTests.md)** |
| Python 2 / import errors | Port drift | Python **3.10+**, **[BUILD_ZERO.md](BUILD_ZERO.md)** |
| `Assertion failed` in **`wallet.cpp`** | Product or ordering | Debug line, GTest/Boost isolate |

---

## Known failures, hangs, and crashes

Default **pass-only** filters exist because of the items below. **Do not** use **`./contrib/run-tests.sh --all`** as a merge gate until the **encrypt/rewrite** class is resolved.

### C++ — excluded by default

| Item | Risk | Notes |
|------|------|-------|
| GTest **`WriteCryptedSaplingZkey*`** | Hang | **`EncryptWallet`** → **`CDB::Rewrite`** waits on **`mapFileUseCount`** while DB still open (**`src/wallet/gtest/test_wallet_zkeys.cpp`**, **`wallet/db.cpp`**) |
| GTest **`CachedWitnesses*`** | Fail / “failed to die” | **`BuildWitnessCache`** no-op when **`pcoinsTip`** null; **`EXPECT_DEATH`** pattern not matched by **`DecrementNoteWitnesses`** |
| Boost **`rpc_wallet_encrypted_wallet_sapzkeys`** | Hang | Same **rewrite** class over RPC |
| Boost **`miner_tests`** | Fail | Block assembly vs **(192,7)** |

**Mitigation directions:** Close wallet before rewrite or test-only persistence path (**encrypt** family**). For **CachedWitnesses**:** seed **`CCoinsViewCache`** / manual witnesses / replace death test—see **[UpdateTests.md](UpdateTests.md)** § GTest and Debug notes.

### Tier A Python (skip / weak coverage)

Documented with IDs **6.x** in **[UpdateTests.md](UpdateTests.md)** (coinbase, peers, **`getchaintips`**, branch IDs, **`pyblake2`**). **Coverage honesty:** **exit 0** with **`skip_test`** is not full scenario coverage—**Accounting** above.

### Disposition (summary)

| Item | Disposition |
|------|-------------|
| **`WriteCrypted*`** / **`rpc_wallet_encrypted_wallet_sapzkeys`** | Fix or reimplement; **abandon for default CI** until wallet sequencing fixed |
| **`CachedWitnesses*`** | Reimplement harness / fix **`pcoinsTip`** path—high ROI |
| **`miner_tests`** | Port or gate per case |
| **`wallet_overwintertx`**, **`p2p_nu_peer_management`** | **Addressed** in-tree (NU/maturity, mininode magic / **`ver_send`**) |
| **`getchaintips`** | **Addressed** in-tree (join/reorg semantics, **`CHAIN_BOOTSTRAP`**, split-only topology, branch length vs bootstrap) |
| **`shorter_block_times`** | Reimplement height-sensitive checks vs regtest activations |
| **`--all` / unfiltered GTest on CI** | **Abandon** as gate |
| Tier B/C bulk as gate | **Abandon**; allowlist or fix opportunistically |

### Plan of action (ordering)

1. **P0 — `CachedWitnesses*`:** Fixture / witness build; drop from **`--gtest_filter`** when green (**`contrib/run-tests.sh`**, **`full_test_suite.py`**).
2. **P1 — Tier A:** **`wallet_overwintertx`**, **`p2p_nu_peer_management`**, **`getchaintips`** — **done** for main-path alignment (magic, **`ver_send`**, NU/maturity, split topology, **`CHAIN_BOOTSTRAP`**, rejoin tips). **Open:** stabilize or drop **`--jobs>1`** for Tier A (hang under load—**Parallel Tier A**).
3. **P2 — `shorter_block_times`**, **`miner_tests`:** Derive heights from chain state; port PoW vectors.
4. **P3 — Encrypt / rewrite:** Wallet owner; unblocks GTest + Boost encrypt tests.
5. **P4 — Tier B/C**, **`keypool`**, optional Equihash solver test — process / product.

**Backlog (non-blocking):** **`--strict` + `--full`** semantics; **`miner_tests` (192,7)**; Equihash solver behind **`ENABLE_MINING`**; RPC allowlist for **`full_test_suite` rpc** stage; CI timeouts; **parallel Tier A** (**`--jobs>1`**) reproduction and mitigation—cross-check **[UpdateTests.md](UpdateTests.md)** prioritized table for maintainer scheduling.

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

Build prerequisites and interpreter versions: **[BUILD_ZERO.md](BUILD_ZERO.md)**.

---

## Appendix: Coinbase maturity constants

| Chain | Maturity | Location |
|-------|----------|----------|
| Zero | **720** | `src/consensus/consensus.h` |
| Bitcoin Core | 100 | upstream |
| Zcash | 100 | upstream |

Regtest uses Zero’s **720**.

---

## Appendix: RPC Python options

**`--nocleanup`**, **`--noshutdown`**, **`--tracerpc`**, **`--srcdir`**, **`--tmpdir`** — see **`qa/rpc-tests/*.py`** driver help.

---

## Appendix: Repo CSV inventories

**`RPCs.csv`**, **`RPCs_extended.csv`**, **`Options.csv`**, **`Options_extended.csv`**, **`Reindex_Rescan.csv`** (repo root).
