# TEST_ZERO

**Audience:** People who build or install Zero and need to **run** tests, **interpret** results, or **debug** a layer (C++, Python RPC, full driver).

**Authoritative sources for lists:** `contrib/run-tests.sh` (**`PYTHON_PASSING`**), `qa/pull-tester/rpc-tests.sh` (**`testScripts`**, **`testScriptsExt`**). This file mirrors them for reading; if they diverge, the scripts win.

---

## How to read this document

| Section | Purpose |
|---------|---------|
| **Accounting** | What “run” and “pass” mean (and what they do **not** mean). |
| **Interpreting results** | How to read logs and summaries for **`run-tests.sh`**, GTest, Boost, **`equihash_tests`**. |
| **Use cases** | Commands and expectations from smoke → full driver → focused debugging. |
| **Reference** | Harness tables, script lists, flags, filters, one-off commands. |
| **Deep dive** | Excluded C++ tests, RPC failure modes, hang/crash/fix notes. |
| **Disposition** | Fix vs reimplement vs abandon — uses root-cause analysis in this file. |
| **Plan** | Grouped, prioritized fix/rewrite sequence — link in **Internal links** below. |
| **Appendix** | Prerequisites, coinbase maturity, RPC options, repo CSVs. |

Internal links: [Accounting](#accounting-run-pass-and-skip) · [Interpreting results](#interpreting-results) · [Smoke](#use-case-smoke-a-fresh-build) · [Tier A list](#tier-a-rpc-scripts) · [Pass-only filters](#reference-pass-only-c-filters) · [Disposition](#disposition-fix-reimplement-abandon) · [Plan](#plan-fixes-and-rewrites) · [Deep dive RPC](#deep-dive-rpc-python-bulk-and-extended)

---

## Accounting: run, pass, and skip

- **Run:** The test **executed its intended checks** (assertions or explicit pass criteria in the main code path). Setup-only or **early `skip_test`** paths **do not** count as that scenario having been run.
- **Pass:** The run completed and **those checks succeeded**. A process can **exit 0** after **`skip_test`**; that is **not** a pass of the named scenario for reporting or coverage—it is **skipped**.
- **`run-tests.sh` exit code:** Without **`--strict`**, the script runs all steps even after failures, sets **`OVERALL_FAIL`**, prints a **WARNING**, and still exits **0**—use **`PASS:`** / **`FAIL:`** in logs and the warning line. With **`--strict`**, any failed step yields exit **1** after the full run (util → C++ → RPC as applicable).
- **Tier A RPC:** **`PYTHON_PASSING`** is an allowlist. Scripts not on it may fail elsewhere without affecting that gate.
- **C++ early return:** Some Boost/GTest cases **exit the test function** before running assertions (e.g. legacy **(96,5)** Equihash vectors on a **(192,7)** mainnet params check). Boost still reports those cases as **passed**; they are **not** proof that the skipped branch ran. See [Equihash Boost results](#equihash-boost-results).

---

## Interpreting results

### `contrib/run-tests.sh`

| Signal | Meaning |
|--------|---------|
| **`PASS: <step>`** | That subprocess exited **0**. |
| **`FAIL: <step>`** | That subprocess exited non-zero; see the cited **`.log`**. |
| **`WARNING: one or more steps failed`** | Default mode: failures occurred but the script exits **0** unless you used **`--strict`**. |
| **`FAIL: one or more steps failed (--strict)`** | **`--strict`** set and at least one step failed; shell exit **1**. |
| **`test-logs/<timestamp>-*.log`** | One file per step (e.g. **`zero-gtest`**, **`test_bitcoin`**, **`rpc-blockchain`**). |

### Validating `--strict`

- **Mechanism:** Each step records failure via **`bump_fail`** (**`OVERALL_FAIL=1`**). After every selected step finishes, if **`OVERALL_FAIL`** is set and **`--strict`** was passed, the script prints **`FAIL: one or more steps failed (--strict)`** and exits **1**; otherwise it prints **`WARNING`** and exits **0**. Implementation: end of **`contrib/run-tests.sh`**.
- **CI contract:** **`.github/workflows/tests.yml`** runs **`./contrib/run-tests.sh --strict`** after **`zcutil/build.sh`**; a failing job means at least one harness step exited non-zero.
- **Local checks:** (1) Green path: **`./contrib/run-tests.sh --strict`** exits **0** and every expected **`PASS:`** appears. (2) Induced failure: force one step to fail (e.g. temporary edit in **`bitcoin-util-test.py`**) and confirm exit **1** and the corresponding **`FAIL:`** line plus log path. (3) **`--quick --strict`** applies strict only to quick steps (util, secp, univalue, optional symbol/security); it does **not** run GTest, Boost, or RPC unless you omit **`--quick`**.

### GTest

**Command:** `./src/zero-gtest`

| Signal | Meaning |
|--------|---------|
| **`[  PASSED  ] N tests.`** | All selected tests that ran completed successfully. |
| **`YOU HAVE M DISABLED TEST`** | Build or filter disabled some tests; does not affect **`PASSED`** count for executed tests. |
| **`FAILED`** / non-zero exit | At least one test failed; rerun with **`--gtest_filter=Suite.Case`** to isolate. |

### Boost

**Command:** `./src/test/test_bitcoin`

| Signal | Meaning |
|--------|---------|
| **`*** No errors detected`** | All **enabled** suites/cases that ran passed. |
| **`skipped because disabled`** | Entire suite disabled in this build; not a failure. |
| Non-zero exit | At least one failure; scroll up for the first **`error:`** / failed assertion. |

### Equihash Boost results

**Suite:** `equihash_tests` in **`src/test/equihash_tests.cpp`**. **Command:** `./src/test/test_bitcoin -t equihash_tests` (also runs inside pass-only **`test_bitcoin`**).

| Case group | Params | If the log shows **OK** / no failure, what that means |
|------------|--------|--------------------------------------------------------|
| **Legacy solver/validator vectors** | **(96,5)** | Cases **`solver_testvectors`** / **`validator_testvectors`** **return early** when mainnet **`nEquihashN != 96`**. They **do not** re-run **(96,5)** math on Zero; no assertion fires. Treat as **“compatible no-op”**, not **(96,5)** coverage. |
| **`zero_mainnet_genesis_equihash_192_7_valid`** | **(192,7)** | **`CheckEquihashSolution`** accepted the **shipped mainnet genesis** header and **`nSolution`** — real **(192,7)** validation. |
| **`zero_mainnet_genesis_equihash_rejects_corrupt_solution`** | **(192,7)** | A **corrupted** **`nSolution`** is **rejected** — negative check on the same path. |
| **`zero_regtest_genesis_equihash_48_5_valid`** | **(48,5)** | Regtest uses **different** **`N`,`K`** than mainnet; this checks **regtest genesis** only, then restores **MAIN**. |

**Failures in Zero-specific cases** usually indicate: **`chainparams.cpp`** genesis / **`nSolution`** out of sync, wrong **`nEquihashN`/`K`**, or a bug in **`CheckEquihashSolution`** / **`CEquihashInput`** (**`pow.cpp`**).

**Verbose:** `--log_level=test_suite` or **`--log_level=message`** prints early-return messages for the **(96,5)** branches.

---

## Platform expectations: macOS first

| Topic | macOS (`Darwin`) | Linux (typical) |
|-------|------------------|-----------------|
| **Manual `./qa/pull-tester/rpc-tests.sh`** | **`tests-config.sh`** does not set **`PYTHON`**. If your shell leaves **`PYTHON`** empty, the driver can try to execute **`.py`** directly (**`Permission denied`**). Use **`env PYTHON=python3 ./qa/pull-tester/rpc-tests.sh …`** or export **`PYTHON`**. **`contrib/run-tests.sh`** sets **`PYTHON`** via **`find_python3`**. | Same if **`PYTHON`** is unset in the environment. |
| **Default `./contrib/run-tests.sh`** | Same pass-only **GTest** / **Boost** filters as Linux. May **`pkill`** orphaned **`zerod`** under **`/var/folders`** before Tier A RPC. | Same filters; no Darwin orphan cleanup. |
| **`./contrib/run-tests.sh --full`** | Wrapper passes **`--skip sec-hard --skip no-dot-so`** to **`full_test_suite.py`**: no ELF **`checksec.sh`** pass, no **`depends/` `.so`** scan in that invocation. | All default stages unless you add **`--skip`**. |
| **Manual `full_test_suite.py`** | **`sec-hard`**: **`make check-security`** runs; ELF sub-checks run only if **`zerod`** is ELF (usually false for Mach-O). **`no-dot-so`**: needs **`depends/<triplet>/lib`** from a depends build, or the stage may skip with a message. | ELF hardening checks apply when binaries are ELF. |
| **Release parity** | A green **`--full`** on macOS is **not** the same artifact checklist as Linux (stages omitted above). Adjust expectations or run missing stages deliberately. | Closer to “all stages” if **`depends/`** is populated. |

---

## Use case: Smoke a fresh build

**Goal:** Confirm toolchains and small libraries without C++ suite cost.

```bash
./contrib/run-tests.sh --quick
```

**Runs:** util (`bitcoin-util-test.py`), secp256k1, univalue; if **`src/zerod`** exists, **check-symbols** and **check-security**. **Does not** run GTest, Boost, or RPC.

**Counts as run/pass:** Only steps that complete without failure in the log. Same [accounting](#accounting-run-pass-and-skip) rules apply if a step is skipped internally.

---

## Use case: Default contributor gate

**Goal:** Pass-only C++ suites plus Tier A RPC (allowlist in **`PYTHON_PASSING`**).

```bash
./contrib/run-tests.sh
```

CI or gatekeeping: **`./contrib/run-tests.sh --strict`** (exit **1** if any step fails).

Logs: **`test-logs/<timestamp>-*.log`**. Review **`PASS:`** / **`FAIL:`** per step; see [Accounting](#accounting-run-pass-and-skip).

**C++:** Pass-only filters in [Reference: pass-only C++ filters](#reference-pass-only-c-filters).  
**RPC:** [Tier A list](#tier-a-rpc-scripts) — order matches **`PYTHON_PASSING`** in **`contrib/run-tests.sh`**.

**Parallel Tier A RPC:** See [Reference: parallel Tier A RPC](#reference-parallel-tier-a-rpc).

---

## Use case: Release-style or CI full driver

**Goal:** Ordered stages including Boost, GTest, util, secp, univalue, bulk RPC (**Tier B** via **`rpc-tests.sh`** with no args)—fails fast on first stage failure.

```bash
./contrib/run-tests.sh --full
```

See [Platform expectations](#platform-expectations-macos-first) for macOS vs Linux. Stages and **`--unfiltered`** behavior: [Reference: `full_test_suite.py`](#reference-full_test_suitepy).

**Other modes (still `contrib/run-tests.sh`):**

| Mode | RPC | C++ |
|------|-----|-----|
| **`--fail`** | Tier B + C (`rpc-tests.sh -extended`) | GTest pass-only; Boost **unfiltered** |
| **`--all`** | Tier B + C | GTest + Boost **unfiltered** (hang risk on known wallet cases) |
| **`--no-python`** | Skipped | Per **`--fail`** / **`--all`** / default |

Full mode table: [Reference: `run-tests.sh` modes](#reference-contribrun-testssh-modes).

---

## Use case: RPC coinbase maturity

**Related env:** **`ZERO_MINE_COINBASE`**. **What the env var does:** In **`qa/rpc-tests/test_framework/util.py`**, **`ZERO_MINE_COINBASE=1`** allows **`ensure_coinbase_utxos()`** to **mine 1000 blocks** when the node has no mature coinbase UTXOs (Zero **720**-block maturity). If unset, that helper returns false and callers typically **skip** the rest of the scenario.

**Default path without the env var:** **`ensure_mature_coinbase_or_skip()`** (used by several Tier A scripts) first mines in **50-block** steps until **`has_coinbase_utxos`**, then falls back to **`ensure_coinbase_utxos()`** if still empty. Height-bound scripts (e.g. **`shorter_block_times`**) still rely on **`ZERO_MINE_COINBASE`** or skip.

**Empirical (one machine, Darwin, Mar 2026):** With **`ZERO_MINE_COINBASE` unset**, **`rescan_import`** and **`wallet_changeaddresses`** completed the main path (**~32 s** wall, **~70 s** wall respectively) without bulk mining—so mature coinbase via incremental mining is **likely** for those scripts. **`wallet_overwintertx`** can still exit **0** while **skipping** for **`consensus['chaintip']`** mismatch (see [Chaintip and branch-ID skips](#deep-dive-chaintip-branch-ids-and-p2p-version-skips)); **coinbase was not the blocker** there. **`shorter_block_times`** **skipped** without the env (coinbase gate). With **`ZERO_MINE_COINBASE=1`**, the same **`shorter_block_times`** run passed the mining gate then **failed** an assertion on **`expiryheight`** (**expected 105**, **actual 1142**)—**wrong activation-height constants** for Zero regtest, not coinbase maturity.

### Coinbase helpers vs Tier A scripts

**Focus:** what each helper does and what typically breaks per script.

| Python helper | Trigger | Effect |
|---------------|---------|--------|
| **`has_coinbase_utxos`** | **`listunspent()`** with **`generated`** | True iff at least one **mature** coinbase UTXO exists (**720** confs on Zero). |
| **`mine_until_node_has_mature_coinbase`** | 50-block batches, cap **2000** | Extends chain until **`has_coinbase_utxos`** or gives up. |
| **`ensure_coinbase_utxos`** | Only bulk-mines if **`ZERO_MINE_COINBASE=1`** | Without env: returns **false** immediately if no mature coinbase—callers **skip** or fail. |
| **`ensure_mature_coinbase_or_skip`** | Tries incremental path, then **`ensure_coinbase_utxos`** | Prints **`Skipping … (need 720+…)`** and returns **false** if both fail. |

| Script | Coinbase path | What a green run proves | What is broken when it skips/fails (typical) |
|--------|---------------|-------------------------|-----------------------------------------------|
| **`rescan_import`** | **`ensure_mature_coinbase_or_skip`** | Import/rescan + spends work with **720** maturity. | Skip: neither incremental nor env bulk produced mature coinbase. |
| **`wallet_changeaddresses`** | same | Change outputs on **z_sendmany** paths with mature funds. | same |
| **`wallet_overwintertx`** | same | NU-scoped txs at intended **heights** / branch IDs. | **Often skip after coinbase OK:** **`getblockchaininfo()['consensus']['chaintip']`** does not match hard-coded Sapling id—**height / NU schedule**, not **`listunspent`**. |
| **`shorter_block_times`** | **`ensure_coinbase_utxos`** only (no incremental wrapper) | Median time + **expiryheight** near NU boundaries. | **Without env:** skip at coinbase gate (**101** blocks mined in script &lt; **720**). **With env:** can pass gate then **assert wrong block numbers** vs Zero’s real activation heights. |
| **Other Tier A** (e.g. **`wallet_treestate`**, **`paymentdisclosure`**) | Own mining / **`get_coinbase_address`** | Varies. | **`bad-txns-premature-spend-of-coinbase`**, balance drift—usually **insufficient blocks**, not missing **`ZERO_MINE_COINBASE`** unless they use **`ensure_coinbase_utxos`**. |

**Takeaway:** **`ZERO_MINE_COINBASE`** is a **bulk escape hatch** for **`ensure_coinbase_utxos`** when incremental mining is not wired into the script. It does **not** fix **NU height** mismatches (**`wallet_overwintertx`**, **`shorter_block_times`** after mining). **`ensure_mature_coinbase_or_skip`** is what makes **`rescan_import`** / **`wallet_changeaddresses`** **usually pass without** the env on Zero.

**Scripts that call `ensure_coinbase_utxos`** directly or via **`ensure_mature_coinbase_or_skip`** (bulk mine via env applies to the latter’s second phase):

1. `rescan_import.py`
2. `wallet_changeaddresses.py`
3. `wallet_overwintertx.py`
4. `shorter_block_times.py`

**Run all four with bulk mining** (slow; mainly for **`shorter_block_times`** or stressing the **`ensure_coinbase_utxos`** fallback; the first three often pass **without** the env after incremental mining):

```bash
export ZERO_MINE_COINBASE=1
export PYTHON=python3   # if not already set (see [Platform expectations](#platform-expectations-macos-first))
for t in rescan_import wallet_changeaddresses wallet_overwintertx shorter_block_times; do
  ./qa/pull-tester/rpc-tests.sh "$t"
done
```

**Run one** (e.g. **`shorter_block_times`**):

```bash
env PYTHON=python3 ZERO_MINE_COINBASE=1 ./qa/pull-tester/rpc-tests.sh shorter_block_times
```

**Serial timing + logs (optional):** Run each script alone, capture **`/usr/bin/time -p`** output and **`tee`** to a directory under **`test-logs/`** (e.g. **`test-logs/coinbase-serial-<timestamp>/`**).

**Not covered by this flag:** Many other scripts call **`get_coinbase_address()`** without **`ensure_coinbase_utxos()`**. They need enough blocks mined inside the test (or a prepared chain); setting **`ZERO_MINE_COINBASE`** alone does not change them.

---

## Use case: Target a feature or failing script

| Goal | Command |
|------|---------|
| Single RPC script | `./qa/pull-tester/rpc-tests.sh <basename>` |
| Tier B + C | `./qa/pull-tester/rpc-tests.sh -extended` |
| Boost suite | `./src/test/test_bitcoin -t rpc_tests` (replace suite name) |
| Zeronode RPC (Boost) | `./src/test/test_bitcoin -t rpc_zeronode_tests` and/or `-t rpc_zeronode_budget_tests` |
| GTest filter | `./src/zero-gtest --gtest_filter='...'` |
| GTest single case (debug) | `./src/zero-gtest --gtest_filter='WalletTests.CachedWitnessesEmptyChain' --gtest_break_on_failure` |
| Boost suite-by-suite | `./contrib/run-boost-individual.sh` |
| Python syntax (tree) | `python3 -m compileall -q qa contrib src/test` |

RPC subprocess options (**`--tracerpc`**, **`--nocleanup`**, …): [Appendix: RPC Python options](#appendix-rpc-python-options).

Failure signals and mitigations: [Deep dive: failure taxonomy](#deep-dive-failure-taxonomy).

---

## Reference: Harnesses

**Heritage (short):** Bitcoin Core shaped **Boost.Test**, **Python RPC**, secp256k1, univalue, util vectors. Zcash added **GTest** (**`zero-gtest`**), shielded RPC tests, **`full_test_suite.py`**. Zero keeps that stack with **720** coinbase maturity and Equihash **(192,7)**.

| Harness | Entrypoint | Role |
|---------|------------|------|
| **Util** | `src/test/bitcoin-util-test.py` | Base58, keys, JSON vectors |
| **secp256k1** | `make -C src/secp256k1 check` | Library |
| **univalue** | `make -C src/univalue check` | JSON library |
| **check-symbols** | `make -C src check-symbols` | Exported symbol policy |
| **check-security** | `make -C src check-security` | Build hardening script |
| **GTest** | `src/zero-gtest` | Shielded wallet / consensus-oriented cases |
| **Boost** | `src/test/test_bitcoin` | RPC, script, serialization, crypto, zeronode RPC |
| **RPC Python** | `qa/pull-tester/rpc-tests.sh` | Multi-node regtest |
| **full_test_suite** | `qa/zcash/full_test_suite.py` | Ordered stages: btest, gtest, sec-hard, no-dot-so, util-test, secp, univalue, rpc |

---

## Reference: RPC script lists

### Tier A RPC scripts

**Allowlist:** **`PYTHON_PASSING`** in **`contrib/run-tests.sh`**. **Definition:** Default **`./contrib/run-tests.sh`** runs each basename below via **`rpc-tests.sh`**, one process per script (unless **`--jobs=N`**). **Order below matches `PYTHON_PASSING` in `contrib/run-tests.sh`** (1 = first in the array).

1. `blockchain`
2. `disablewallet`
3. `httpbasics`
4. `reindex`
5. `rescan_import`
6. `rescan_startup`
7. `decodescript`
8. `keypool`
9. `paymentdisclosure`
10. `prioritisetransaction`
11. `wallet_treestate`
12. `wallet_anchorfork`
13. `getchaintips`
14. `rewind_index`
15. `wallet_overwintertx`
16. `wallet_changeaddresses`
17. `shorter_block_times`
18. `p2p_nu_peer_management`
19. `txn_doublespend`

### Tier A: design and requirements

**Granularity:** one row per script. **Goal of this table:** What each script is trying to prove, what it needs to run meaningfully, where it may **print `Skipping …` and still exit 0**, and what to change for a **real** pass (see [accounting](#accounting-run-pass-and-skip)).

| # | Script | Intent | Preconditions / harness | Skip or weak path | Hardening (design) |
|---|--------|--------|-------------------------|-------------------|-------------------|
| 1 | `blockchain` | `getblockchaininfo`, chain stats | `initialize_chain_clean`, 1 node | None typical | Keep aligned with Zero RPC field set |
| 2 | `disablewallet` | Node with wallet disabled | `-disablewallet` | None typical | — |
| 3 | `httpbasics` | HTTP auth / RPC transport | 2 nodes | None typical | — |
| 4 | `reindex` | `-reindex` + `checkblockindex` | 1 node, few blocks | None typical | — |
| 5 | `rescan_import` | Import + rescan | Mature coinbase for spends | **`ensure_mature_coinbase_or_skip`** (incremental mine, then env bulk) | Rare skip only if both phases fail |
| 6 | `rescan_startup` | `-rescan` on restart | 5 blocks, 1 node | None typical | — |
| 7 | `decodescript` | `decodescript` RPC | 1 node | None typical | — |
| 8 | `keypool` | Keypool refill / wallet ops | **`initialize_chain`** (pre-seeded chain) | Legacy harness; fails if chain layout wrong | Consider **`initialize_chain_clean`** + explicit mining to match Zero |
| 9 | `paymentdisclosure` | Payment disclosure + shielded ops | Multi-node split mining (721 on node1, etc.), **`get_coinbase_address`** | Fails if heights/balances wrong | Already mines heavily; document exact height budget |
| 10 | `prioritisetransaction` | Mempool feerate / mining priority | Multi-node, mempool | None typical | — |
| 11 | `wallet_treestate` | Wallet / treestate consistency | **`get_coinbase_address`** after chain init | Assert if no mature coinbase | Mine **≥720** before first shield spend |
| 12 | `wallet_anchorfork` | Anchor / fork handling | **`get_coinbase_address`** | Same as above | Same |
| 13 | `getchaintips` | `getchaintips` across reorg | Split network, controlled heights | **Skips** if active tip height ≠ **`getblockcount()`** at a node, or if **`len(getchaintips()) != 2`** after **`join_network`** (script expects **active** + **valid-fork**). Zero may surface **one** active tip if fork metadata differs from Bitcoin Core–style reporting | Compare **`getchaintips`** JSON on Zero vs upstream; relax count check or mine/sync so two entries appear |
| 14 | `rewind_index` | Block file rewind + reindex | `nuparams`, regtest upgrades | None typical | Keep branch IDs aligned with Zero regtest |
| 15 | `wallet_overwintertx` | Overwinter/Sapling tx on regtest | **`-nuparams=2bb40e60:200`**, coinbase + branch checks | After **`ensure_mature_coinbase_or_skip`**, script expects **`consensus['chaintip'] == '7361707a'`** (Sapling); actual best height is **~815** after **`generate(720)`** + **`generate(95)`**, so **`CurrentEpochBranchId`** is **Blossom** → **`chaintip`** **`2bb40e60`**—**skip**. Comment in test (“block 195”) is **stale** vs real height | Rewind/rephase chain near height **200**, or derive expected branch id from **`getblockchaininfo`** at the script’s real height, or add **`nuparams`** that match the intended NU story ([RCA below](#deep-dive-chaintip-branch-ids-and-p2p-version-skips)) |
| 16 | `wallet_changeaddresses` | z_shieldcoinbase / change | **`ensure_mature_coinbase_or_skip`** | Rare skip if mining cap hit | — |
| 17 | `shorter_block_times` | Median time / block times near fixed activation heights | **`ensure_coinbase_utxos`** (bulk mine only with **`ZERO_MINE_COINBASE=1`**) | Skip without env; with env, may pass mining then **fail** on hard-coded heights (e.g. **`expiryheight`** vs Zero activation block numbers) | Restructure phases or replace magic heights with values derived from **`getblockchaininfo`** / **`consensus` |
| 18 | `p2p_nu_peer_management` | Peer versions at NU | Mininode connected | **Skip** if **`getpeerinfo`** empty (handshake rejected) or reported **`version`** values differ from **170007 / 170008 / 170009** (Zcash P2P constants) | Align **`mininode`** **`nVersion` / `strSubVer`** with Zero’s accepted peer versions, or widen the expected set to what **`zerod`** advertises and accepts on regtest |
| 19 | `txn_doublespend` | Double-spend accounting | **4 nodes**, each mines **25+25+25+25+720** for maturity | Balance assumes **10 ZER** subsidy × mature blocks | If balances drift, use **`zero_regtest_subsidy`**-style math in test |

**Cross-cutting:** Python **3.10+**, built **`zerod`** + wallet; **`qa/pull-tester/tests-config.sh`** **`BUILDDIR`** correct. Parallel runs (**`--jobs=N`**) need enough **RAM** and **CPU** for **N** Equihash miners—see below.

### Estimates: Tier A

**Intent:** reduce skips and get real exercise of each script. Rough planning only; actual work varies with failure mode and reviewer load.

| Change class | Scope | Engineering (indicative) | Test cycles |
|--------------|-------|---------------------------|-------------|
| **Coinbase path** | **`ensure_mature_coinbase_or_skip`** on **`rescan_import`**, **`wallet_changeaddresses`**, **`wallet_overwintertx`**; **`shorter_block_times`** still env-gated | ~0.5–1 day for any stragglers | 2–3 full Tier A runs (**`--strict`**) |
| **Peer / P2P skips** | e.g. **`p2p_nu_peer_management`** when no mininode peers | Harness or version negotiation | ~1–2 days | +5–10 single-script reruns |
| **`getchaintips` / split** | Height and tip-count assumptions | ~0.5–1 day | 3–5 runs |
| **Subsidy / balance (txn_doublespend, etc.)** | Align with **`zero_regtest_subsidy`** / maturity | ~1–2 days if entangled | 5+ runs |
| **Whole Tier A “minimal skip” goal** | All 19 scripts exercise main assertions without **`skip_test`** on default path | **~3–7 engineer-days** (sequential-ish) | **~8–20** full Tier A passes on representative Linux + macOS |

**Wall time per Tier A cycle:** Often **~30–90 minutes** serial (Equihash + 19 processes); **`--jobs=N`** cuts wall time roughly toward **longest script** × batches, bounded by CPU (see [parallel](#reference-parallel-tier-a-rpc)).

### Tier B — testScripts

**Driver:** **`rpc-tests.sh`** with no extra args. Same order as **`qa/pull-tester/rpc-tests.sh`** (optional **`zmq_test.py`** / **`proton_test.py`** appended when enabled at build):

- `paymentdisclosure.py`
- `prioritisetransaction.py`
- `wallet_treestate.py`
- `wallet_anchorfork.py`
- `wallet_changeaddresses.py`
- `wallet_changeindicator.py`
- `wallet_import_export.py`
- `wallet_protectcoinbase.py`
- `wallet_shieldcoinbase_sprout.py`
- `wallet_shieldcoinbase_sapling.py`
- `wallet_listreceived.py`
- `wallet.py`
- `wallet_overwintertx.py`
- `wallet_persistence.py`
- `wallet_nullifiers.py`
- `wallet_1941.py`
- `wallet_addresses.py`
- `wallet_sapling.py`
- `wallet_listnotes.py`
- `mergetoaddress_sprout.py`
- `mergetoaddress_sapling.py`
- `mergetoaddress_mixednotes.py`
- `listtransactions.py`
- `mempool_resurrect_test.py`
- `txn_doublespend.py`
- `txn_doublespend.py --mineblock`
- `getchaintips.py`
- `rawtransactions.py`
- `getrawtransaction_insight.py`
- `rest.py`
- `mempool_limit.py`
- `mempool_spendcoinbase.py`
- `mempool_reorg.py`
- `mempool_nu_activation.py`
- `mempool_tx_expiry.py`
- `httpbasics.py`
- `zapwallettxes.py`
- `proxy_test.py`
- `merkle_blocks.py`
- `fundrawtransaction.py`
- `signrawtransactions.py`
- `signrawtransaction_offline.py`
- `walletbackup.py`
- `key_import_export.py`
- `nodehandling.py`
- `reindex.py`
- `rescan_import.py`
- `rescan_startup.py`
- `addressindex.py`
- `spentindex.py`
- `timestampindex.py`
- `decodescript.py`
- `blockchain.py`
- `disablewallet.py`
- `zcjoinsplit.py`
- `zcjoinsplitdoublespend.py`
- `zkey_import_export.py`
- `reorg_limit.py`
- `getblocktemplate.py`
- `bip65-cltv-p2p.py`
- `bipdersig-p2p.py`
- `p2p_nu_peer_management.py`
- `rewind_index.py`
- `p2p_txexpiry_dos.py`
- `p2p_txexpiringsoon.py`
- `p2p_node_bloom.py`
- `regtest_signrawtransaction.py`
- `finalsaplingroot.py`
- `shorter_block_times.py`
- `sprout_sapling_migration.py`
- `turnstile.py`
- `zmq_test.py` (if `ENABLE_ZMQ=1`)
- `proton_test.py` (if `ENABLE_PROTON=1`)

### Tier C — testScriptsExt

**Driver:** **`rpc-tests.sh -extended`** adds the entries below.

- `getblocktemplate_longpoll.py`
- `getblocktemplate_proposals.py`
- `pruning.py`
- `forknotify.py`
- `hardforkdetection.py`
- `invalidateblock.py`
- `keypool.py`
- `receivedby.py`
- `rpcbind_test.py`
- `smartfees.py`
- `maxblocksinflight.py`
- `invalidblockrequest.py`
- `p2p-acceptblock.py`

Commented out in the shell array: `script_test.py`, duplicate `forknotify.py` entry.

---

## Reference: `contrib/run-tests.sh` modes

Unless **`--full`**, the script runs util, secp256k1, univalue, then (if **`src/zerod`** exists) check-symbols and check-security.

| Mode | GTest | Boost | RPC |
|------|-------|-------|-----|
| **Default** | Pass-only `--gtest_filter` | Pass-only `--run_test` exclusions | Tier A (**`PYTHON_PASSING`**) |
| **`--quick`** | Skip | Skip | Skip |
| **`--fail`** | Pass-only | No Boost exclusions | `-extended` (B + C) |
| **`--all`** | Unfiltered | Unfiltered | `-extended` |
| **`--full`** | Via **`full_test_suite`** only | Via **`full_test_suite`** only | Via **`full_test_suite`** only |
| **`--no-python`** | Per mode | Per mode | Skip |
| **`--jobs=N`** | — | — | Tier A parallel only |
| **`--build-checks`** | Extra early **`make -C src check-security`** | | |

**`--strict`:** Combine with **default**, **`--quick`**, **`--fail`**, **`--all`**, or **`--no-python`** (not **`--full`**—the full suite already fails fast on its own). Same steps as without **`--strict`**, then **exit 1** if any step failed. Implemented in **`contrib/run-tests.sh`** (tracks util, secp, univalue, symbol/security checks, GTest, Boost, and RPC paths).

**Environment:** **`PYTHON`** (interpreter for RPC / full suite), **`ZERO_MINE_COINBASE`** ([Use case](#use-case-rpc-coinbase-maturity)), **`LOG_DIR`** (default **`test-logs/`**). Top-of-file comments in **`contrib/run-tests.sh`** duplicate flags.

### Reference: parallel Tier A RPC

**Flag:** **`--jobs=N`**. **What it does:** With **`--jobs=N`** and **default** mode (not **`--fail`** / **`--all`**), each Tier A script is still **`rpc-tests.sh <basename>`**, but up to **`N`** of those subprocesses run **concurrently** as background jobs. Each script starts its own **`zerod`** instance(s) under a temp datadir—**no shared state** between scripts.
- **Why:** Shorten wall clock versus **19** serial RPC runs when the machine has spare CPU/RAM.
- **Requirements:** Enough **CPU** (Equihash), **RAM** (~several GB for multiple **`zerod`**), **free ports** (each harness picks ports), **disk** for temp datadirs. **macOS** and **Linux** both work; avoid **`N`** larger than **cores − 1** if the machine is shared.
- **How to verify it works:** Run **`./contrib/run-tests.sh --jobs=4 --strict`** (or **`--no-python`** omitted) and confirm **19** **`rpc-*`** logs exist and **exit 0**. Induce a failure in one script and confirm **`--strict`** yields **exit 1** and the failing child’s log shows the traceback.
- **Limits:** Equihash mining is heavy; **`N` > logical CPUs** usually **hurts**. Prefer **`N`** in **2–8** and tune.
- **Logs:** **`test-logs/<timestamp>-rpc-<basename>.log`**
- **Failures:** Non-zero child exit is aggregated; the log line names **`rpc-<basename>`**, PID, and log path. **`--strict`** → final **exit 1**.
- **Not parallel:** **`--fail`**, **`--all`**, **`rpc-tests.sh -extended`** remain **serial** in **`run-tests.sh`**.

---

## Reference: `full_test_suite.py`

**Command:** `python3 qa/zcash/full_test_suite.py` (or **`./contrib/run-tests.sh --full`**). **Fails fast** (exit **1** on first failed stage).

**Default stage order:** `btest` → `gtest` → `sec-hard` → `no-dot-so` → `util-test` → `secp256k1` → `univalue` → `rpc`

| Stage | Behavior | With `--unfiltered` or `ZERO_FULL_SUITE_UNFILTERED=1` |
|-------|----------|------------------------------------------------------|
| **btest** | Same Boost exclusions as default **`run-tests.sh`** | No `--run_test` exclusions (hang risk: **`rpc_wallet_encrypted_wallet_sapzkeys`**) |
| **gtest** | Same GTest filter as default **`run-tests.sh`** | No filter (hang/crash risk on excluded wallet tests) |
| **sec-hard** | **`make check-security`**; ELF **`checksec.sh`** when **`zerod`** is ELF | unchanged |
| **no-dot-so** | Fail if stray **`.so`** under **`depends/<triplet>/lib`** | unchanged |
| **util-test**, **secp256k1**, **univalue** | Standard | unchanged |
| **rpc** | **`rpc-tests.sh`** no args (Tier B) | unchanged |

**Flags:** `--list-stages`, `--skip STAGE` (repeatable), positional stage names to restrict order. **`run-tests.sh --full`** on Darwin passes `--skip sec-hard --skip no-dot-so`.

---

## Reference: Pass-only C++ filters

Aligned with **`contrib/run-tests.sh`** default and default **`full_test_suite.py`** btest/gtest.

**GTest**

```text
--gtest_filter='-wallet_zkeys_tests.WriteCryptedSaplingZkey*:WalletTests.CachedWitnesses*'
```

**Boost**

```text
--run_test='!Alert_tests:!miner_tests:!rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys'
```

| Suite | Excluded | Reason |
|-------|----------|--------|
| **GTest** | **`WriteCryptedSaplingZkey*`** | **CDB::Rewrite** / wallet DB hang path (**verified:** **`timeout 30`** → process exit **124**, test stuck in **`[ RUN ]`**) |
| **GTest** | **`CachedWitnesses*`** | Death test / witness assertions (**verified:** **`CachedWitnessesEmptyChain`** — “failed to die”; **`CachedWitnessesChainTip`** — zero anchors / witness booleans, fast **FAIL**) |
| **Boost** | **`Alert_tests`** | Not compiled; token harmless if absent |
| **Boost** | **`miner_tests`** | Block assembly / mining vs **(192,7)** |
| **Boost** | **`rpc_wallet_encrypted_wallet_sapzkeys`** | Can **hang** (**`CDB::Rewrite`** class) |

**Boost pass-only includes:** **`equihash_tests`** ([below](#equihash_tests-suite)).

Lists: `./src/zero-gtest --gtest_list_tests` · `./src/test/test_bitcoin --list_content`

### equihash_tests suite

**Harness:** Boost **`test_bitcoin`**. **File:** `src/test/equihash_tests.cpp`.

**Legacy (96,5) vectors:** Solver tests (**`#ifdef ENABLE_MINING`**) and **`validator_testvectors`** embed Zcash **(96,5)** expectations. On Zero, after **`SelectParams(MAIN)`**, **`nEquihashN` is 192**, so those cases **return immediately** (optional **BOOST_TEST_MESSAGE** “Skipping (96,5) …”). They avoid false failures; they **do not** validate **(96,5)** on this chain.

**Zero-specific cases (real assertions):**

- **`zero_mainnet_genesis_equihash_192_7_valid`** — **N=192, K=7**; **`CheckEquihashSolution`** on **mainnet genesis**.
- **`zero_mainnet_genesis_equihash_rejects_corrupt_solution`** — corrupt **`nSolution`** must fail.
- **`zero_regtest_genesis_equihash_48_5_valid`** — **N=48, K=5**; **regtest genesis**; then **`SelectParams(MAIN)`** again.

**Run only this suite:** `./src/test/test_bitcoin -t equihash_tests`

**How to read the output:** [Equihash Boost results](#equihash-boost-results).

---

## Reference: Direct commands

| Suite | Invocation |
|-------|------------|
| Util | `cd src && srcdir=$(pwd) PYTHONPATH=$(pwd)/test python3 test/bitcoin-util-test.py` |
| secp256k1 | `make -C src/secp256k1 check` |
| univalue | `make -C src/univalue check` |
| GTest | `./src/zero-gtest [--gtest_filter=...]` |
| Boost | `./src/test/test_bitcoin [--run_test=...]` |
| RPC | `./qa/pull-tester/rpc-tests.sh [name \| -extended]` |

```bash
make -C src secp256k1-check
make -C src univalue-check
```

---

## Reference: RPC driver

| Invocation | Scripts |
|------------|---------|
| *(no args)* | Tier B — all **`testScripts`** |
| **`-extended`** | Tier B + Tier C |
| **`rpc-tests.sh NAME`** | One entry matching **`testScripts`** or **`testScriptsExt`** (with or without **`.py`**) |

Requires wallet + utils + bitcoind at build (**`ENABLE_BITCOIND`**, **`ENABLE_UTILS`**, **`ENABLE_WALLET`**). Config: **`qa/pull-tester/tests-config.sh`** (**`BUILDDIR`**, **`BITCOIND`**, **`BITCOINCLI`**).

---

## Deep dive: C++ cases excluded by default

**Typical risks when run unfiltered:** hang or crash.

| Layer | Item | Risk | Status / direction |
|-------|------|------|-------------------|
| **GTest** | **`WriteCryptedSaplingZkey*`** | Hang (**`CDB::Rewrite`** / DB refcount); **2026-03:** **`timeout 30`** → **exit 124**, stuck in **`[ RUN ]`** | **Postponed** — see [Root cause: pass-only GTest exclusions](#root-cause-pass-only-gtest-exclusions) |
| **GTest** | **`CachedWitnesses*`** | Death test **failed to die**; or assertion cascade on empty witnesses | Harness / **`pcoinsTip`** — same section |
| **Boost** | **`rpc_wallet_encrypted_wallet_sapzkeys`** | Hang (same **`CDB::Rewrite`** class as above) | **Postponed** with GTest encryption path |
| **Boost** | **`miner_tests`** | Block assembly / mining assumptions vs **(192,7)** | Port vectors or gate cases |

**Not excluded (pass-only):** **`equihash_tests`** — mainnet **(192,7)** + regtest **(48,5)** genesis validation ([Pass-only filters](#reference-pass-only-c-filters)).

Do **not** run **`./contrib/run-tests.sh --all`** on CI without accepting the wallet hang risk above.

### Root cause: pass-only GTest exclusions

The default filter drops **two families** (four test names): **`wallet_zkeys_tests.WriteCryptedSaplingZkey*`** (2) and **`WalletTests.CachedWitnesses*`** (4). Root causes differ.

**1–2. `WriteCryptedSaplingZkeyDirectToDb` / `WriteCryptedSaplingZkeyDirectToDbSeparateFile`**

- **What the test does:** Build a wallet, add Sapling keys, call **`EncryptWallet`**, then re-open the same file (or a copy in the “SeparateFile” variant) and assert crypted keys round-trip.
- **Mechanism:** **`EncryptWallet`** triggers a **Berkeley DB rewrite** (**`CDB::Rewrite`**) while the wallet still holds the DB environment. The in-tree comment in **`src/wallet/gtest/test_wallet_zkeys.cpp`** documents **hang: `mapFileUseCount` / rewrite waits for file users**.
- **Why SeparateFile still excluded:** It avoids **two wallets on one file** but the **first** wallet still runs **`EncryptWallet`** in-process—the same rewrite path that can wedge. Pass-only excludes both names for CI stability.
- **Fix class:** Serialize **close / flush wallet before rewrite**, test-only mock of encryption persistence, or non-BDB wallet storage—**product / wallet** change, not a one-line test tweak.

**3. `CachedWitnesses*` (four cases)**

- **What they assume:** After synthetic blocks and **`BuildWitnessCache`**, Sprout/Sapling **witnesses** and **anchors** are populated so anchors differ and **`DecrementNoteWitnesses`** behaves as in upstream Zcash.
- **Mechanism:** **`CWallet::BuildWitnessCache`** (**`src/wallet/wallet.cpp`**) **returns immediately** when **`pcoinsTip` is null** (log: **`BuildWitnessCache: pcoinsTip is null`**). The GTest harness sets up **`chainActive`** and in-memory **`CBlockIndex`** entries but **does not** attach a **`CCoinsViewCache`** tip the way a running node does. **`GetWitnessesAndAnchors`** therefore keeps **empty** optional witnesses; later **`EXPECT_NE`** on anchors and **`EXPECT_TRUE`** on witness flags **fail**. **`CachedWitnessesEmptyChain`** additionally uses **`EXPECT_DEATH(..., ".*nWitnessCacheSize > 0.*")`**; **`DecrementNoteWitnesses`** in current code **does not abort** with that pattern (see comment in **`test_wallet.cpp`** around the death test)—so Google Test reports **“failed to die”**.
- **Fix class:** In the test fixture, **seed `pcoinsTip`** (or equivalent **`CCoinsView`**) consistent with the fake chain, **or** build witnesses manually (the file’s commented “partial fix” sketch). Optionally **replace `EXPECT_DEATH`** with behavior-level asserts once semantics are fixed.

**Boost `rpc_wallet_encrypted_wallet_sapzkeys`:** Same **encrypt / rewrite** failure class as **(1)** at the RPC layer—kept excluded for the same reason.

---

## Deep dive: Chaintip, branch IDs, and P2P version skips

Three Tier A scripts often **exit 0** without exercising their main assertions. Below: **symptom → root cause → fix levers**.

### wallet_overwintertx.py — branch ID guard

**Not a coinbase failure** — maturity path can succeed while this guard still skips.

- **Symptom:** **`Skipping wallet_overwintertx: … chaintip 2bb40e60, expected Sapling 7361707a`** after **`ensure_mature_coinbase_or_skip`** succeeds.
- **What `chaintip` is:** **`getblockchaininfo()['consensus']['chaintip']`** is filled from **`CurrentEpochBranchId(tip->nHeight, consensusParams)`** (**`src/rpc/blockchain.cpp`**), which maps the **highest active network upgrade** at the **current chain height** to a branch id (**`src/consensus/upgrades.cpp`**: **`CurrentEpoch`** walks **`NetworkUpgradeActive`** from Blossom downward).
- **Root cause:** The script mines **`generate(720)`** then **`generate(95)`** so the best chain is **~815** blocks, not **~195** as the **comment** in the test suggests. With **`-nuparams=2bb40e60:200`**, **Blossom** is **active** for all heights **≥ 200**, so at **815** the current epoch is **Blossom** → **`chaintip`** is **`2bb40e60`**. The assertion expects **Sapling** (**`7361707a`**) because the **Zcash-origin** scenario assumed a **short** chain near the Blossom activation boundary (**~195–200**) after **100-block** maturity—not **720+** blocks on Zero regtest.
- **What is not wrong:** Default Zero **`CRegTestParams`** leave many upgrades at **`NO_ACTIVATION_HEIGHT`** until **`nuparams`**; the failure is **height vs narrative**, not “Sapling missing from **`chainparams`**” in isolation.
- **Fix levers:** Restructure mining so the chain is near **200** when the Sapling-phase checks run (e.g. separate phases: establish maturity, then **`invalidateblock` / rewind** or new nodes with a shorter chain), **or** replace hard-coded **`7361707a`** with values derived from **`getblockchaininfo`** at the intended height, **or** add **`nuparams`** that recreate Zcash’s NU ordering at the heights the test expects.

### `getchaintips.py` — RPC vs test expectations

- **Symptom:** Skip when **`len(getchaintips) != 2`** after rejoin, or when **active** tip **height** ≠ **`getblockcount()`**.
- **What the RPC does:** **`getchaintips`** builds the set of **`CBlockIndex*`** that are **tips** in **`mapBlockIndex`**, always inserts **`chainActive.Tip()`**, then labels each with **`branchlen`** and **`status`** (**`active`**, **`valid-fork`**, **`headers-only`**, etc.) based on **`chainActive.Contains`**, **`nChainTx`**, and **`BLOCK_VALID_*`** (**`src/rpc/blockchain.cpp`**).
- **Root cause candidates:** (1) After the split/rejoin, the alternate branch is **not fully validated** (**`nChainTx == 0`** or not **`BLOCK_VALID_SCRIPTS`**), so the entry is **`headers-only`** / **`valid-headers`** rather than **`valid-fork`**, or it is pruned from the tip set differently than Bitcoin Core’s test expects. (2) **`sync_all`** / connectivity leaves nodes with **different** active heights so the script’s **`getblockcount()`** vs **`getchaintips`** consistency check fails. (3) Fewer than two **tips** remain in **`setTips`** if one branch’s tip is no longer a leaf in the index map.
- **Fix levers:** Instrument **`getchaintips`** JSON on failure; align mining/sync so **both** forks are **fully connected** and **validated**; relax the test to Zero’s actual fork metadata if behavior is **spec-consistent** but differs from upstream.

### `p2p_nu_peer_management.py` — P2P version set

- **Symptom:** Skip: no peers, or **`version`** not in **{170007, 170008, 170009}**.
- **Root cause:** **`zerod`** rejects the mininode or reports **protocol versions** outside the set the test hard-codes (Zcash NU-era **`PROTOCOL_VERSION`** expectations). Zero may differ on regtest **subver** / **`nVersion`**.
- **Fix levers:** Match **`qa/rpc-tests/test_framework/mininode.py`** (or equivalent) to **`version.h`** / **`PROTOCOL_VERSION`** for Zero regtest; or assert on **observed** allowed versions.

### macOS: harness differences and reproduced outcomes

| Topic | Effect on tests |
|-------|-----------------|
| **`PYTHON` unset** | **`rpc-tests.sh`** evaluates **`${PYTHON} path/to/script.py`**; empty **`PYTHON`** → kernel tries to execute **`.py`** → **`Permission denied`**. **`contrib/run-tests.sh`** avoids this via **`find_python3`**; **manual** runs need **`env PYTHON=python3`**. |
| **Temp datadir** | Nodes use **`/var/folders/...`**; **`run-tests.sh`** may **`pkill`** orphaned **`zerod`** there before Tier A. Does not change **consensus** outcomes versus Linux. |
| **Reproduced (Darwin, Mar 2026)** | Same **skip/fail semantics** as above for **`rescan_import`** (pass), **`wallet_changeaddresses`** (pass), **`wallet_overwintertx`** (skip **`chaintip`**), **`shorter_block_times`** (skip without env; **fail `expiryheight`** with env), **GTest** hang (**exit 124**) and **`CachedWitnesses*`** failures. No macOS-specific **branch id** divergence was isolated—the issues are **height / NU schedule** and **harness null `pcoinsTip`**. |

---

## Deep dive: RPC Python bulk and extended

**Scope:** Tier B bulk and **`-extended`** Tier C. **Cost:** Each script starts **`zerod`**, often mines Equihash, tears down—**`-extended`** is long wall time.

| Risk | Examples | Mitigation |
|------|----------|------------|
| **Hang** | Stuck **`zerod`**; C++ wallet rewrite class if mixed with encryption RPC | macOS orphan cleanup in **`run-tests.sh`**; avoid unfiltered wallet encryption tests |
| **Crash** | **`script_test.py`** (disabled in array); **`Assertion failed`** in **`wallet.cpp`** | Keep disabled until consensus/sync aligned; debug per traceback |
| **Slow** | **`ZERO_MINE_COINBASE=1`** + **`ensure_coinbase_utxos`**; **`pruning.py`**, **`getblocktemplate_longpoll.py`**, large shield flows | Run only needed scripts; mine minimum blocks for the scenario |
| **Fail: maturity** | **`wallet.py`**, **`mempool_spendcoinbase.py`**, **`listtransactions.py`**, many wallet merges — assume ~100-block maturity | Mine **≥720**; adjust expectations |
| **Fail: subsidy** | Balance / mempool totals vs regtest subsidy | **`zero_regtest_subsidy`** in **`test_framework/util.py`** |
| **Fail: GBT / P2P** | **`getblocktemplate*.py`**, **`bip65-cltv-p2p.py`**, **`bipdersig-p2p.py`** | Align to Zero mining / peer rules or skip until specified |
| **Fail: harness** | **`mininode`**: **`hashlib.blake2b`** vs **`pyblake2`** | Python **3.10+**; wrong **`nuparams`** / branch IDs — use Zero regtest IDs (**Overwinter** / **Sapling** in **`mininode.py`**) |
| **Skip-heavy** | Coinbase guard, peer/version, **`getchaintips`** shape, clean-chain balance guards in adapted scripts | Preconditions: **`ensure_coinbase_utxos`** + **`ZERO_MINE_COINBASE`**, **`getblockcount()`**-based heights, peer setup |

**Promotion to Tier A:** Script runs **without** skip of the main scenario on default paths; add basename to **`PYTHON_PASSING`** in **`contrib/run-tests.sh`**.

**Optional process:** allowlist for **`full_test_suite` rpc** stage; document disabled scripts in-repo (product decision).

---

## Deep dive: Failure taxonomy

**Indexed by:** log signals and typical causes.

| Type | Log signal | Typical cause | Mitigation |
|------|------------|---------------|------------|
| **A** | `execfile`, `StringIO`, bad imports | Python 2 leftovers | Python 3 + **`test_framework.*`** imports |
| **B** | `need 720+ for mature coinbase`, `bad-txns-premature-spend-of-coinbase` | **720** maturity | Mine **≥720**; **`ZERO_MINE_COINBASE`** where **`ensure_coinbase_utxos`** exists |
| **C** | Balance / merge / mempool mismatch | Subsidy / halving / founders | **`zero_regtest_subsidy`**; fix expected values |
| **D** | e.g. **`ZERO is not connected!`** on **`getblocktemplate`** | Zero vs Bitcoin mining RPC | Rewrite setup or skip |
| **E** | **`Assertion failed`** in **`wallet.cpp`** | Wallet bug or ordering | Debug cited line |
| **F** | `AttributeError` on test object | Broken harness setup | Fix test wiring |

**Upstream caution:** Bitcoin **functional** tests assume **100** maturity; Zcash **`qa/rpc-tests`** also **100** on upstream—porting must re-check **`consensus.h`** and **`chainparams`**.

---

## Maintenance: verify `contrib/run-tests.sh` flags

When adding or renaming options, complete this checklist once (and after any refactor of the argument parser).

| Flag / input | Expected behavior | Quick check |
|--------------|-------------------|-------------|
| *(none)* | Pass-only GTest + Boost + Tier A serial; exit **0** with **WARNING** if any step failed | `./contrib/run-tests.sh` |
| **`--strict`** | Same as default, then **exit 1** if any step failed | `./contrib/run-tests.sh --strict`; see [Validating `--strict`](#validating-strict) |
| **`--quick`** | No GTest / Boost / RPC | `./contrib/run-tests.sh --quick` |
| **`--no-python`** | Skips RPC only | `./contrib/run-tests.sh --no-python` |
| **`--jobs=N`** | Tier A parallel (**default** mode only) | `./contrib/run-tests.sh --jobs=2 --strict` |
| **`--fail`** | Boost unfiltered; RPC **`-extended`** | Inspect logs for **`rpc-all`** |
| **`--all`** | GTest + Boost unfiltered; RPC **`-extended`** | Confirm unfiltered GTest in log |
| **`--full`** / **`--full-suite`** | Only **`full_test_suite.py`**; Darwin skips **sec-hard** + **no-dot-so** | `./contrib/run-tests.sh --full` |
| **`--build-checks`** | Extra **`make check-security`** at start | `./contrib/run-tests.sh --build-checks --quick` |
| **`PYTHON`** | Interpreter for RPC / full suite | `env PYTHON=$(which python3) ./contrib/run-tests.sh --quick` |
| **`LOG_DIR`** | Log output directory | `LOG_DIR=/tmp/zt ./contrib/run-tests.sh --quick` |
| **`ZERO_MINE_COINBASE=1`** | Enables mining in **`ensure_coinbase_utxos`** callers | [Use case](#use-case-rpc-coinbase-maturity) |

**Source of truth:** Parser loop and **`bump_fail`** / **`OVERALL_FAIL`** in **`contrib/run-tests.sh`**; Boost exclude string must stay aligned with **`qa/zcash/full_test_suite.py`** **`BOOST_PASS_EXCLUDE`**.

---

## Disposition: fix, reimplement, abandon

**Source:** root-cause analysis in this document. **Terms:** **Fix** = change production or test code so the existing case passes. **Reimplement** = replace the scenario (new harness flow or new assertions) while keeping the *intent* (coverage goal). **Abandon (for CI)** = keep excluded or out of default gates; may still run manually for investigation. None of this requires deleting sources unless maintainers choose to.

| Item | Disposition | Why |
|------|-------------|-----|
| **GTest `WriteCryptedSaplingZkey*`** | **Fix** (wallet) *or* **reimplement** (test-only persistence path); **abandon for default CI** until then | Hang is **`CDB::Rewrite` / `mapFileUseCount`** with wallet still open—**product sequencing**, not a flaky test. A **reimplemented** test could persist crypted keys via a **test double** or **closed-wallet** workflow that avoids production **`EncryptWallet`** deadlock. |
| **GTest `CachedWitnesses*`** | **Reimplement** / **fix harness** first; **do not abandon** if witness cache matters | Failures are **`pcoinsTip == nullptr`** → **`BuildWitnessCache` no-op** plus **stale `EXPECT_DEATH`**. **Tractable:** attach a minimal **`CCoinsViewCache`** in the fixture **or** build witnesses manually; **replace death test** with asserts on real invariants. |
| **Boost `rpc_wallet_encrypted_wallet_sapzkeys`** | Same as **`WriteCrypted*`** | Same **encrypt / rewrite** class over RPC. |
| **Boost `miner_tests`** | **Fix** (port or gate per case) | No hang—**wrong assumptions** for **(192,7)** / block template. Worth keeping for regression; gate slow or broken cases behind build flags if needed. |
| **`wallet_overwintertx` (Tier A skip)** | **Reimplement** test phases (preferred) or **fix** mining height | **Test narrative** assumes ~**195** blocks; **actual** height after maturity mining is **~815** → wrong **`chaintip`**. Not a consensus bug by itself—**align chain setup** with assertions ([RCA](#deep-dive-chaintip-branch-ids-and-p2p-version-skips)). |
| **`getchaintips` (Tier A skip)** | **Investigate → fix test** *or* **fix node** if RPC violates intended fork reporting | Often **test sync / validation** state (**`valid-fork`** vs **`headers-only`**). **Abandon only** if Zero **specifies** different fork visibility and the test is upstream-Bitcoin-specific. |
| **`p2p_nu_peer_management` (skip)** | **Fix** (mininode / expected version set) | **Handshake or version mismatch**—localized to P2P test harness vs **`version.h`**. |
| **`shorter_block_times` (skip / fail)** | **Reimplement** height-sensitive checks | **Skip:** coinbase gate without env. **Fail with env:** hard-coded **`expiryheight`** / median-time anchors vs **Zero regtest** activations—**derive expected values** from **`getblockchaininfo`** or **`chainparams`**, do not copy Zcash constants blindly. |
| **`./contrib/run-tests.sh --all` as CI** | **Abandon** | Combines **hang** (**`WriteCrypted*`**) and **Tier B/C** noise—keep **manual** / nightly with acceptance of risk. |
| **Tier B/C bulk (`rpc-tests.sh` no args, `-extended`)** | **Abandon as merge gate**; **fix opportunistically** | Many failures are **maturity / subsidy / upstream Bitcoin**—**allowlist** for release CI ([Backlog](#backlog-proposed-fixes-and-improvements)); fix scripts when a feature needs them. |

**Summary:** **Highest ROI:** **`CachedWitnesses*`** (harness), **Tier A Python** NU/height skips (**`wallet_overwintertx`**, **`shorter_block_times`**, **`p2p_nu_peer_management`**). **Low short-term ROI / needs wallet owner:** **`WriteCrypted*`** + **`rpc_wallet_encrypted_wallet_sapzkeys`** (encryption rewrite path). **Do not enable unfiltered GTest on CI** until the first group is addressed.

---

## Plan: fixes and rewrites

**Organization:** grouped workstreams and priority order. **Goal:** Reduce Tier A **skips** and C++ **excludes** with predictable ordering. **Verify** each merge with **`./contrib/run-tests.sh --strict`** (and targeted filters below).

### Priority tiers

**Order:** P0 first, then P1, and so on.

| Tier | Focus | Outcome |
|------|--------|---------|
| **P0** | **`CachedWitnesses*`** GTest harness | Removes four false failures; enables removing **`WalletTests.CachedWitnesses*`** from **`--gtest_filter`** once green. |
| **P1** | Tier A Python: **`p2p_nu_peer_management`**, **`wallet_overwintertx`**, **`getchaintips`** | Drops **skip** noise; exercises real P2P + NU + fork RPC paths on CI. |
| **P2** | **`shorter_block_times`** + **`miner_tests`** (Boost) | Height/math alignment and PoW regression coverage without hanging tests. |
| **P3** | Wallet **encrypt / rewrite** (**`WriteCrypted*`**, **`rpc_wallet_encrypted_wallet_sapzkeys`**) | Requires **wallet maintainer** or large test redesign; **do not block** P0–P2. |
| **P4** | Tier B/C allowlist, **`keypool`** harness, optional Equihash solver test | Product/process; parallel to P1–P2 if staffing allows. |

### Group A — GTest CachedWitnesses*

**Priority:** P0.

1. **Spike (0.5–1 day):** In **`src/wallet/gtest/test_wallet.cpp`** (and shared fixtures), trace **`BuildWitnessCache`** entry; confirm **`pcoinsTip`** null path (**`wallet.cpp`**).
2. **Choose approach:** (a) Minimal **`CCoinsViewCache`** + load coins matching the synthetic **`CBlock` / `CBlockIndex`** chain, **or** (b) manual witness construction per file comments (~**967–981** pattern), **or** (c) hybrid: stub **`pcoinsTip`** for anchor reads only.
3. **Rewrite `CachedWitnessesEmptyChain`:** Remove **`EXPECT_DEATH`**; assert on **`DecrementNoteWitnesses`** behavior that **current** code guarantees (or skip case with **`GTEST_SKIP`** until invariant is defined).
4. **Run:** `./src/zero-gtest --gtest_filter='WalletTests.CachedWitnesses*'` until all pass; then drop negative filter from **`contrib/run-tests.sh`** and **`full_test_suite.py`** in the same PR.
5. **Risk:** Fixture complexity; if (a) balloons, prefer (b) for **one** test first, then generalize.

### Group B — Tier A Python skips

**Priority:** P1.

| Script | Sequence | Notes |
|--------|----------|--------|
| **`p2p_nu_peer_management`** | 1 | **Fast:** diff **`mininode`** / **`msg_version`** vs **`src/version.h`** and Zero regtest behavior; run single script until no skip. |
| **`wallet_overwintertx`** | 2 | **Design:** Either **rewind** chain to **~195–199** after maturity ( **`invalidateblock`** / fresh nodes ) **or** split setup: mine **720** on a throwaway path then **reset** / new nodes with **`-nuparams`** only for the NU phase. Update assertions to **`getblockchaininfo`**-driven branch ids where fixed hex is brittle. |
| **`getchaintips`** | 3 | **Instrument:** On skip, log full **`getchaintips`** + **`getblockcount`** per node. Fix **sync** / **full validation** of the shorter branch so **`status`** is **`valid-fork`**, or relax assertions if Zero’s fork reporting is intentional (document in TEST_ZERO). |

**Dependency:** **`p2p_*`** is independent. **`wallet_overwintertx`** and **`getchaintips`** are independent; both can follow **`p2p_*`** in parallel by different people.

### Group C — Heights and PoW

**Priority:** P2.

1. **`shorter_block_times`:** Add helper to read **expected activation heights** from **`getblockchaininfo['upgrades']`** (or a small table keyed to Zero **`chainparams`**). Replace magic **105 / 1142** (and similar) with computed expectations. Keep **`ZERO_MINE_COINBASE`** documented for CI if mining cost is high.
2. **`miner_tests`:** List failing **`BOOST_AUTO_TEST_CASE`** entries; for each, either port expected block to **(192,7)** or **`#ifdef` / `skip`** with a ticket reference. Run **`./src/test/test_bitcoin -t miner_tests`** until green; then consider removing **`!miner_tests`** from pass-only Boost exclude if scope is manageable.

### Group D — Encrypt / CDB::Rewrite

**Priority:** P3, deferred until wallet owner or test redesign.

1. **Spec:** Decide “encrypt wallet in test” = **production path** (then **fix `CWallet::EncryptWallet` / flush / close order**) vs **alternate persistence test** (new code path only in **`#ifdef` GTest**).
2. **If product fix:** Profile **`mapFileUseCount`** during **`EncryptWallet`**; align with upstream Bitcoin/Zcash fixes if applicable.
3. **If test-only bypass:** New test that writes crypted Sapling records **without** calling **`EncryptWallet`** mid-open, or uses **separate process** (heavy).
4. **Re-enable order:** GTest **`WriteCrypted*`** first (narrower), then Boost **`rpc_wallet_encrypted_wallet_sapzkeys`**.

### Group E — CI and scope

**Status:** ongoing policy.

- Keep **default CI** on **`./contrib/run-tests.sh --strict`**; do **not** gate merges on **`--all`** or unfiltered GTest until **Group D** is resolved.
- After **Group A** lands, add a **short** note in the PR template or **`CONTRIBUTING.md`**: “GTest filter changes must match **`full_test_suite.py`**.”

### Suggested milestones

**Scheduling:** calendar-agnostic ordering only.

1. **M1:** **`CachedWitnesses*`** green + filter removed.  
2. **M2:** **`p2p_nu_peer_management`** + **`wallet_overwintertx`** run main path without skip on default **`run-tests.sh`**.  
3. **M3:** **`getchaintips`** + **`shorter_block_times`** (with or without env) aligned.  
4. **M4:** **`miner_tests`** ported or gated; Boost exclude reviewed.  
5. **M5:** Encrypt path ( **D** ) scoped and owned.

---

## Backlog: proposed fixes and improvements

| Item | Type | Note |
|------|------|------|
| **`--strict --full`** | Harness | Optionally propagate **`--strict`** into **`full_test_suite`** or document as no-op |
| **`miner_tests` (192,7)** | C++ | Port or gate cases; largest remaining Boost gap for PoW |
| **Tier A skip removal** | Python | Per [Tier A per-script table](#tier-a-design-and-requirements); prioritize **`getchaintips`**, **`wallet_overwintertx`** (**`chaintip`** / **`nuparams`**), **`p2p_nu_peer_management`** |
| **`shorter_block_times` heights** | Python | After **`ZERO_MINE_COINBASE`**, assertions use upstream Zcash block numbers; align **`expiryheight`** and median-time steps with Zero **`chainparams`** |
| **`keypool` + `initialize_chain`** | Python | Migrate to **`initialize_chain_clean`** + explicit mining to reduce legacy drift |
| **Equihash solver @ (192,7)** | C++ | Optional slow test behind **`ENABLE_MINING`** + env gate; not required for CI if genesis validator tests suffice |
| **RPC allowlist for `full_test_suite` rpc** | Product | Tier B bulk often red—allowlist for release green |
| **CI** | Infra | **`.github/workflows/tests.yml`** — Ubuntu build + **`./contrib/run-tests.sh --strict`**; tune **`timeout-minutes`** / triggers if needed |

---

## Adding and extending tests

- **Boost:** `src/test/*_tests.cpp`; register suites; **`./src/test/test_bitcoin -t SuiteName`**. Patterns: **`CallRPC`**, **`CheckRPCThrows`** in **`rpc_zeronode_tests.cpp`**.
- **GTest:** `src/wallet/gtest/`; **`./src/zero-gtest --gtest_filter=...`**
- **RPC Python:** `qa/rpc-tests/*.py` + **`BitcoinTestFramework`**; run **`rpc-tests.sh`** with basename. Helpers: **`test_framework/util.py`**, **`wallet.py`**.

**Zeronode (Boost):** **`rpc_zeronode_tests`**, **`rpc_zeronode_budget_tests`**.

---

## Troubleshooting

- **`ImportError` / blake2:** Use Python **3.10+** and **`hashlib.blake2b`**, or install **`pyblake2`** if mininode falls back incorrectly.
- **`PYTHON` not found:** `env PYTHON=/path/to/python3 ./contrib/run-tests.sh`
- **Boost / GTest cascade:** Single **`-t`** suite or **`contrib/run-boost-individual.sh`**
- **RPC cannot find binaries:** **`qa/pull-tester/tests-config.sh`**, **`BUILDDIR`**
- **macOS `--full`:** [Platform expectations](#platform-expectations-macos-first)
- **Orphaned `zerod`:** `pkill -f "zerod -datadir=/var/folders"` if needed

---

## Appendix: Prerequisites and coinbase maturity

- **Build:** **`zerod`**, **`zero-cli`**, **`src/test/test_bitcoin`**, **`src/zero-gtest`**. Toolchains: [BUILD_ZERO.md](BUILD_ZERO.md).
- **Python:** **3.10+** for RPC and **`full_test_suite`**. **`contrib/run-tests.sh`** prefers **`python3`**, else **`python`** if ≥3.10, else set **`PYTHON`**.
- **Repo root** for wrappers; **`cd src`** only when a command requires it.

### Coinbase maturity

**Reference:** consensus constants in source.

| Chain | `COINBASE_MATURITY` | Location |
|-------|---------------------|----------|
| **Zero** | **720** | `src/consensus/consensus.h` |
| **Bitcoin Core** | **100** | Upstream `consensus.h` |
| **Zcash upstream** | **100** | [Zcash `consensus.h`](https://github.com/zcash/zcash/blob/master/src/consensus/consensus.h) |

Regtest uses Zero’s **720**. Legacy scripts that mine **100–200** blocks need **≥720**, **`ZERO_MINE_COINBASE`** on the four **`ensure_coinbase_utxos`** callers, or a skip path.

---

## Appendix: RPC Python options

- **`--nocleanup`** — Leave **`zerod`** and temp datadir  
- **`--noshutdown`** — Do not stop nodes  
- **`--tracerpc`** — Log RPC calls  
- **`--srcdir`**, **`--tmpdir`** — Paths  

---

## Appendix: Repo CSV inventories

Machine-readable cross-chain lists (repo root): **`RPCs.csv`**, **`RPCs_extended.csv`**, **`Options.csv`**, **`Options_extended.csv`**, **`Reindex_Rescan.csv`**.
