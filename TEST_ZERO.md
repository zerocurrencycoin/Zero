# TEST_ZERO

**Audience:** Builders and contributors who **run** tests, **read** harness output, and **narrow** failures (C++, Python RPC, full driver).

**Documentation partitioning:** User-facing guides are self-contained and do **not** reference maintainer **`Update*.md`** files. **This file** is the validation runbook (commands, modes, harness behavior, known failures). Maintainer-only **test porting and harness prescriptions** are kept in the repository **Update** hub (appendix on test/harness changes)—not duplicated here.

**Authoritative lists:** `contrib/run-tests.sh` (**`PYTHON_PASSING`**), `qa/pull-tester/rpc-tests.sh` (**`testScripts`**, **`testScriptsExt`**). If this file disagrees with those scripts, **the scripts win**.

**Related:** [BUILD_ZERO.md](BUILD_ZERO.md) (toolchain, Python **3.10+**, produced binaries).

---

## Quick start by use case

| You want… | Command / next step |
|-----------|---------------------|
| **Default contributor gate** (pass-only C++ + Tier A RPC, serial) | `./contrib/run-tests.sh --strict` after building **`src/zerod`** |
| **Fast smoke** (no GTest/Boost/RPC) | `./contrib/run-tests.sh --quick --strict` |
| **C++ only** (no Python RPC) | `./contrib/run-tests.sh --no-python --strict` |
| **One Tier A RPC script** | `env PYTHON=python3 ./qa/pull-tester/rpc-tests.sh <basename>` |
| **Full multi-stage driver** (Tier B RPC, fail-fast) | `./contrib/run-tests.sh --full` |
| **Extended RPC bulk** (long run; many scripts) | `./contrib/run-tests.sh --fail` or `--all` (see **Reference → modes**—not the default gate) |

**Environment:** Python **3.10+**; **`PYTHON`** and **`BUILDDIR`** for manual **`rpc-tests.sh`**—see **Process → Troubleshooting**.

---

## Harness landscape (what runs, and why it exists)

The tree inherits a **layered** validation stack from the Bitcoin / Zcash lineage. Each layer answers a different question; together they approximate “does this node build, link, and behave plausibly on regtest/mainnet parameters?”

1. **Encoding / util checks** (`src/test/bitcoin-util-test.py`, invoked from **`run-tests.sh`** quick path) — static vectors and RPC-free encoding sanity.
2. **Library self-checks** (`secp256k1`, `univalue` via **`make -C src …`**) — third-party correctness in this build.
3. **Symbol / security policy** (`check-symbols`, `check-security`) — shipping constraints when **`zerod`** exists.
4. **Google Test (`zero-gtest`)** — wallet-heavy and some consensus-adjacent unit scenarios; several cases need richer chain/UTXO fixtures (see **Known failures** for excluded suites).
5. **Boost.Test (`test_bitcoin`)** — large integration surface: RPC, script, PoW (including Zero’s **(192,7)** paths), zeronode RPC smoke. Some upstream suites assume different Equihash parameters or deprecated alert behavior—pass-only filters document what the default gate skips.
6. **Python RPC (`qa/pull-tester/rpc-tests.sh`)** — multi-node regtest scripts; each run spins real **`zerod`** processes, mines Equihash blocks, and tears down. **Tier A** is an allowlist (**`PYTHON_PASSING`**) for the default gate; **Tier B/C** lists live only in **`rpc-tests.sh`**.
7. **`full_test_suite.py`** — ordered stages (Boost, GTest, util, secp, univalue, then bulk RPC); **`--full`**; Darwin may skip ELF-focused stages.

**Categories of checks:** **library/unit** (1–3), **C++ suite** (4–5), **multi-process integration** (6–7). Fork-specific behavior (e.g. **COINBASE_MATURITY 720**, Zero **`-nuparams`** branch ids, regtest **(48,5)** Equihash) mostly affects layers **5–7**.

The sections below follow **operations first** (changelog, snapshot), then **how to read output**, **flags**, **reference tables**, **RPC harness details**, and **known failures**.

---

## Harness changelog (recent)

| Change | Location | Effect |
|--------|----------|--------|
| Split topology when **`split=True`** | **`qa/rpc-tests/getchaintips.py`** **`setup_network`** | Connect only **0–1** and **2–3** during the partition so the two halves actually fork (previously **0–2** / **1–2** bridged the split). |
| Shorter bootstrap | Same | **`CHAIN_BOOTSTRAP = 30`** for initial mining (was 200); **`join_network`** still avoids re-mining when the chain is already long enough. |
| Branch assertions | Same | **`expected_branchlen`** from **`shortTip['height'] - CHAIN_BOOTSTRAP`**; active height matches long chain after rejoin; accepts one or two tips per existing semantics. |
| Background wait / exit codes | **`contrib/run-tests.sh`** **`run_bg`** | Set **`BG_LAST_PID=$!`**; avoid **`$(run_bg …)`** (subshell caused **`wait $pid`** to fail). GTest/Boost and Tier A parallel children wait on real child PIDs. |
| **`rescan_import` executable bit | Git index **`qa/rpc-tests/rescan_import.py`** | **`100755`** so **`rpc-tests.sh`** can execute the script (avoids **`Permission denied`** when checkout mode was **`100644`**). |
| **`wallet_changeaddresses` Zero port | **`qa/rpc-tests/wallet_changeaddresses.py`** | **`initialize_chain_clean`** (2 nodes); **`-nuparams`** Overwinter (**`6f76727a`**) and Sapling (**`7361707a`**) at height **1**; **`-txindex`** (RPC needs tx details); **`-experimentalfeatures`** + **`-zmergetoaddress`**; **`ensure_mature_coinbase_or_skip`** before **`get_coinbase_address`** / **`z_shieldcoinbase`** so **720**-deep maturity is satisfied via incremental mining (optional **`ZERO_MINE_COINBASE`** bulk still applies to other helpers). |
| **`wallet_changeindicator` + Sprout VK | **`qa/rpc-tests/wallet_changeindicator.py`**, **`src/wallet/wallet.cpp`** | Default **200**-block cache: **`mine_until_node_has_mature_coinbase`** at **`run_test`** start. **`z_importviewingkey`**: **`UpdateSproutNullifierNoteMapWithTx`** skips when **`GetSproutNoteNullifier`** is empty (viewing key only; no spending key)—avoids **`assert(false)`** on that path. |
| **`serialize_script_num` (Python 3) | **`qa/rpc-tests/test_framework/blocktools.py`** | **`bytearray.append`** takes an **int** (**0–255**), not **`chr(...)`** (would raise **`TypeError`** on scripts that use **`serialize_script_num`**). |

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

**Tier A scripts (all on allowlist):** **`blockchain`**, **`disablewallet`**, **`httpbasics`**, **`reindex`**, **`rescan_import`**, **`rescan_startup`**, **`decodescript`**, **`keypool`**, **`paymentdisclosure`**, **`prioritisetransaction`**, **`wallet_treestate`**, **`wallet_anchorfork`**, **`getchaintips`**, **`rewind_index`**, **`wallet_overwintertx`**, **`wallet_changeaddresses`**, **`wallet_changeindicator`**, **`shorter_block_times`**, **`p2p_nu_peer_management`**, **`txn_doublespend`**.

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

Zeronode RPC coverage: **`rpc_zeronode_tests`**, **`rpc_zeronode_budget_tests`**.

### Troubleshooting

- **Blake2 / imports:** Python **3.10+** and **`hashlib.blake2b`**
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

**Order matches `PYTHON_PASSING` in `contrib/run-tests.sh`:** `blockchain`, `disablewallet`, `httpbasics`, `reindex`, `rescan_import`, `rescan_startup`, `decodescript`, `keypool`, `paymentdisclosure`, `prioritisetransaction`, `wallet_treestate`, `wallet_anchorfork`, `getchaintips`, `rewind_index`, `wallet_overwintertx`, `wallet_changeaddresses`, `wallet_changeindicator`, `shorter_block_times`, `p2p_nu_peer_management`, `txn_doublespend`.

**Per-script skip RCA and IDs (6.x):** RPC Python. **Common themes:** **720** maturity, **`chaintip`** / NU height vs mining plan, **`getchaintips`** shape after rejoin, P2P **`version`** set.

**Parallel Tier A (`--jobs=N`, `N>1`):** Only when the RPC step is the **default Tier A** list (**`PYTHON_PASSING`**): not with **`--fail`** / **`--all`** (those use **`-extended`**), not with **`--no-python`**, not with **`--full`**. **`N=1`** (serial) is the path **CI and the contributor gate** assume.

**Reliability:** Parallel runs start **many `zerod` processes** (Equihash + RAM). That is **best-effort throughput**, not a supported merge gate: scripts can **hang or flake** under load (e.g. **`paymentdisclosure`** observed stuck with **`--jobs=4`** on one macOS run). If a run stalls, use serial (**omit `--jobs`**) or a **lower `N`**; confirm with **`test-logs/…-rpc-*.log`**. GTest/Boost in **`run-tests.sh`** are **not** parallelized by **`--jobs`** (only the Tier A RPC children).

### Direct one-off invocations

Util / secp / univalue can also run via **`make -C src secp256k1-check`**, **`make -C src univalue-check`**, or paths in **`src/test/bitcoin-util-test.py`** (see script / Makefile).

---

## RPC harness details

### Coinbase maturity and helpers

Zero **regtest** uses **`COINBASE_MATURITY` = 720** (**`src/consensus/consensus.h`**). Upstream Bitcoin/Zcash-style scripts often assume **100**—porting must adjust mining or expectations.

**`ZERO_MINE_COINBASE=1`:** In **`qa/rpc-tests/test_framework/util.py`**, **`ensure_coinbase_utxos()`** may mine **1000** blocks when no mature coinbase exists. Without it, that helper returns false and callers often **skip**.

**Helpers:** **`has_coinbase_utxos`**, **`mine_until_node_has_mature_coinbase`** (50-block steps), **`ensure_coinbase_utxos`** (bulk path gated by env), **`ensure_mature_coinbase_or_skip`** (incremental then bulk). Scripts that call **`ensure_coinbase_utxos`** (directly or via **`ensure_mature_coinbase_or_skip`**): **`rescan_import`**, **`wallet_changeaddresses`**, **`wallet_overwintertx`**, **`shorter_block_times`** (the last uses **`ensure_coinbase_utxos`** without the incremental wrapper—often needs **`ZERO_MINE_COINBASE`** or skips early). **`wallet_changeindicator`** uses **`mine_until_node_has_mature_coinbase`** at **`run_test`** entry because it keeps the default **200**-block **`initialize_chain`** cache.

**`wallet_changeaddresses`:** See **Harness changelog** — clean chain, Zero **`-nuparams`**, **`txindex`**, **`zmergetoaddress`**, maturity gate before shielding from coinbase.

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
| Balance / mempool mismatch | **ZERO_COIN** / halving rules | **`zero_regtest_subsidy`** |
| Python 2 / import errors | Port drift | Python **3.10+**, **[BUILD_ZERO.md](BUILD_ZERO.md)** |
| **`NameError`** (e.g. **`initialize_chain_clean`**) | Used in **`setup_chain`** but not imported from **`test_framework.util`** | Add to import list; **`wallet_nullifiers`**-style scripts |
| **`TypeError`** in **`serialize_script_num`** | **`bytearray.append(chr(...))`** on Python 3 | **`blocktools.py`**: append **int** byte (**Harness changelog**) |
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

**Mitigation directions:** Close wallet before rewrite or test-only persistence path (**encrypt** family**). For **CachedWitnesses**:** seed **`CCoinsViewCache`** / manual witnesses / replace death test

### Tier A Python (skip / weak coverage)

### Disposition

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

### Plan of action

1. **P0 — `CachedWitnesses*`:** Fixture / witness build; drop from **`--gtest_filter`** when green (**`contrib/run-tests.sh`**, **`full_test_suite.py`**).
2. **P1 — Tier A:** **`wallet_overwintertx`**, **`p2p_nu_peer_management`**, **`getchaintips`** — **done** for main-path alignment (magic, **`ver_send`**, NU/maturity, split topology, **`CHAIN_BOOTSTRAP`**, rejoin tips). **Open:** stabilize or drop **`--jobs>1`** for Tier A (hang under load—**Parallel Tier A**).
3. **P2 — `shorter_block_times`**, **`miner_tests`:** Derive heights from chain state; port PoW vectors.
4. **P3 — Encrypt / rewrite:** Wallet owner; unblocks GTest + Boost encrypt tests.
5. **P4 — Tier B/C**, **`keypool`**, optional Equihash solver test — process / product.

**Backlog (non-blocking):** **`--strict` + `--full`** semantics; **`miner_tests` (192,7)**; Equihash solver behind **`ENABLE_MINING`**; RPC allowlist for **`full_test_suite` rpc** stage; CI timeouts; **parallel Tier A** (**`--jobs>1`**) reproduction and mitigation—cross-check.

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

---

## Appendix: Coinbase maturity constants

| Chain | Maturity | Location |
|-------|----------|----------|
| Zero | **720** | `src/consensus/consensus.h` |
| Bitcoin Core | 100 | upstream |
| Zcash | 100 | upstream |

---

## Appendix: RPC Python options

**`--nocleanup`**, **`--noshutdown`**, **`--tracerpc`**, **`--srcdir`**, **`--tmpdir`** — see **`qa/rpc-tests/*.py`** driver help.

---

## Appendix: Repo CSV inventories

**`RPCs.csv`**, **`RPCs_extended.csv`**, **`Options.csv`**, **`Options_extended.csv`**, **`Reindex_Rescan.csv`** (repo root).
