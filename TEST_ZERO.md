# TEST_ZERO

How to run the Zero node test suite: commands, what each layer covers, what the default pass-only run expects, and how to add or extend tests.

---

## Prerequisites

- **Build:** `zerod`, `zero-cli`, and (for C++ unit tests) `src/test/test_bitcoin` and `src/zero-gtest`. Build steps are in [BUILD_ZERO.md](BUILD_ZERO.md).
- **Python 3.6+** for RPC tests, `bitcoin-util-test.py`, and `qa/zcash/full_test_suite.py`. `contrib/run-tests.sh` picks `python3`, or `python` if it reports 3.6+, unless you set **`PYTHON`**.
- **Working directory:** Repo root. `contrib/run-tests.sh` changes to the repo root automatically; manual commands below assume you are at the root unless `cd src` is shown.
- **GTest** is built from the pinned **depends** package (GoogleTest 1.16.x, C++14). Upgrading the dependency may require a C++17 toolchain if you move past that line.
- **Optional:** `python3 -m pip install pyblake2` only if `qa/rpc-tests/test_framework/mininode.py` fails to use `hashlib.blake2b` (Python 3.6+ usually enough).

---

## Quick run

```bash
./contrib/run-tests.sh
```

Runs, in order: **Util** (`bitcoin-util-test.py`), **secp256k1** check, **univalue** check, **GTest** (`zero-gtest` with a pass-only filter), **Boost** (`test_bitcoin` with a pass-only filter), then the **RPC Python** scripts listed in §Pass-only RPC Python scripts. Logs go under **`test-logs/`** with a timestamp prefix. The default mode **continues after failures** so you get a full picture in one run.

---

## How runs are organized

| Layer | Role |
|-------|------|
| **Suites 1–3** | Fast checks with no full node: util JSON/base58, secp256k1, univalue. |
| **Suite 4 — GTest** | Wallet/gtest and consensus-oriented tests in `zero-gtest`. |
| **Suite 5 — Boost** | `test_bitcoin`: RPC, script, serialization, crypto, zeronode RPC tests, etc. |
| **Suite 6 — RPC Python** | `qa/rpc-tests`: spawn `zerod`, multi-node regtest, end-to-end RPC. |
| **Suite 7 — sec-hard** | `make -C src check-security` plus, on ELF Linux, extra hardening checks from `full_test_suite`. |
| **Suite 8 — no-dot-so** | `full_test_suite` stage that inspects `depends/` for stray `.so` files (release/depends workflows). |
| **`make -C src check`** | Recursive check that overlaps util, secp, univalue, and Boost when enabled in the build. |

**Default** `./contrib/run-tests.sh` runs layers 1–6 with pass-only filters and (when binaries exist) optional **check-symbols** / **check-security** during **`--quick`**.

**`./contrib/run-tests.sh --full`** (same as **`--full-suite`**) runs **only** `python3 qa/zcash/full_test_suite.py`. It does **not** also run the default background GTest/Boost jobs. Stages, in order:

`btest` → `gtest` → `sec-hard` → `no-dot-so` → `util-test` → `secp256k1` → `univalue` → `rpc`

- **`btest`** invokes `./src/test/test_bitcoin -p` (all **built** Boost tests, no `run-tests.sh` exclusions).
- **`gtest`** invokes `./src/zero-gtest` with **no** filter.
- **`rpc`** runs `./qa/pull-tester/rpc-tests.sh` (extended RPC set, not the 19-script pass-only list).

On **macOS**, `run-tests.sh` passes **`--skip sec-hard --skip no-dot-so`** into `full_test_suite.py` so the driver can finish without ELF-only stages or a full depends tree.

List stages without running:

```bash
python3 qa/zcash/full_test_suite.py --list-stages
```

Run selected stages:

```bash
python3 qa/zcash/full_test_suite.py util-test secp256k1 univalue
```

---

## Test suites (direct commands)

| Suite | What it tests | Invocation |
|-------|---------------|------------|
| Util | Base58, keys, JSON vectors | `cd src && srcdir=$(pwd) PYTHONPATH=$(pwd)/test python3 test/bitcoin-util-test.py` |
| secp256k1 | secp256k1 library | `make -C src/secp256k1 check` |
| univalue | JSON library | `make -C src/univalue check` |
| GTest | Wallet/gtest, shielded/consensus cases | `./src/zero-gtest [--gtest_filter=...]` |
| Boost | RPC, script, serialization, crypto, zeronode RPC | `./src/test/test_bitcoin [--run_test=...]` |
| RPC Python | Multi-node regtest, `zerod` / `zero-cli` | `./qa/pull-tester/rpc-tests.sh [name \| -extended]` |

Isolated top-level checks without full `make check`:

```bash
make -C src secp256k1-check
make -C src univalue-check
```

---

## Runners and modes (`contrib/run-tests.sh`)

| Mode | Command | Use case |
|------|---------|----------|
| Default | `./contrib/run-tests.sh` | Pass-only GTest/Boost + 19 RPC scripts; logs under `test-logs/` |
| With failures | `./contrib/run-tests.sh --fail` | Same suites; GTest/Boost without pass-only exclusions for hang-prone cases only where scripted |
| All (risky) | `./contrib/run-tests.sh --all` | Broad GTest/Boost; may hang on known wallet DB / encryption cases |
| Full driver | `./contrib/run-tests.sh --full` | Only `qa/zcash/full_test_suite.py` (see §How runs are organized) |
| Quick | `./contrib/run-tests.sh --quick` | Util, secp, univalue, check-symbols, check-security; skips GTest and Boost |
| No Python | `./contrib/run-tests.sh --no-python` | Skips RPC Python |
| Parallel RPC | `./contrib/run-tests.sh --jobs=4` | Runs pass-only RPC scripts concurrently (cap `N` to machine size) |
| Build checks | `./contrib/run-tests.sh --build-checks` | Runs `make -C src check-security` (needs Python on `PATH` for the script) |

**Environment**

- **`PYTHON`** — Interpreter used for RPC tests and util test when exported by `run-tests.sh`.
- **`ZERO_MINE_COINBASE=1`** — When set, some RPC paths can mine extra blocks for coinbase maturity (slow; not used in the default pass-only list).
- **`LOG_DIR`** — Override log directory (default `test-logs/` under repo root).

---

## Pass-only filters (copy/paste)

These are what **`run-tests.sh`** uses for the default run.

**GTest**

```text
--gtest_filter='-wallet_zkeys_tests.WriteCryptedSaplingZkey*:WalletTests.CachedWitnesses*'
```

**Boost (`test_bitcoin`)**

```text
--run_test='!Alert_tests:!equihash_tests:!miner_tests:!rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys'
```

`Alert_tests` is not compiled into `test_bitcoin` in the current tree; the `!Alert_tests` token is harmless. **equihash_tests** and **miner_tests** are excluded because upstream vectors target a different Equihash parameterization than Zero. **rpc_wallet_encrypted_wallet_sapzkeys** is excluded because it can hang on wallet DB rewrite paths.

**Full example (Boost only)**

```bash
./src/test/test_bitcoin \
  --run_test='!Alert_tests:!equihash_tests:!miner_tests:!rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys' \
  --log_level=test_suite
```

---

## Pass-only RPC Python scripts

Default `run-tests.sh` runs exactly these 19 scripts (names as passed to `rpc-tests.sh`):

`blockchain` · `disablewallet` · `httpbasics` · `reindex` · `rescan_import` · `rescan_startup` · `decodescript` · `keypool` · `paymentdisclosure` · `prioritisetransaction` · `wallet_treestate` · `wallet_anchorfork` · `getchaintips` · `rewind_index` · `wallet_overwintertx` · `wallet_changeaddresses` · `shorter_block_times` · `p2p_nu_peer_management` · `txn_doublespend`

Several of these **skip** parts of their scenario when regtest conditions are not met (coinbase maturity, peer count, chain tips). They still exit **0** when skipped; interpret coverage accordingly.

---

## Expected results (default pass-only)

| Suite | Expectation |
|-------|-------------|
| Util, secp256k1, univalue | All tests pass |
| GTest | **201** tests pass; **5** excluded by the filter above |
| Boost | All **built** tests matching the pass-only filter pass (on the order of **270+** test cases; suite count depends on `--list_content`) |
| RPC Python (19 scripts) | Each listed script completes with exit code **0** |

Counts drift when tests are added or removed; treat the **filters** and **script list** as the source of truth for “what we run by default.”

---

## Scenarios

| Goal | Command |
|------|---------|
| Incremental build smoke | `./contrib/run-tests.sh --quick` |
| Release-style driver (see §How runs are organized) | `./contrib/run-tests.sh --full` |
| Single Boost module | `./src/test/test_bitcoin -t rpc_tests` |
| Zeronode RPC (Boost) | `./src/test/test_bitcoin -t rpc_zeronode_tests` and/or `-t rpc_zeronode_budget_tests` |
| Single RPC script | `./qa/pull-tester/rpc-tests.sh blockchain` |
| Boost suite-by-suite (avoids cross-suite interaction) | `./contrib/run-boost-individual.sh` |
| GTest single case / break | `./src/zero-gtest --gtest_filter='WalletTests.CachedWitnessesEmptyChain' --gtest_break_on_failure` |
| Python syntax check (tree) | `python3 -m compileall -q qa contrib src/test` |

---

## RPC Python options

Passed through `rpc-tests.sh` / per-script argparse where supported:

- **`--nocleanup`** — Leave `zerod` processes and temp datadir on exit  
- **`--noshutdown`** — Do not stop nodes after the test  
- **`--tracerpc`** — Log RPC calls  
- **`--srcdir=SRCDIR`** — Default is `${BUILDDIR}/src`  
- **`--tmpdir=TMPDIR`** — Temp data directory  

**Configuration:** `qa/pull-tester/tests-config.sh` sets **`BUILDDIR`**, **`BITCOIND`**, **`BITCOINCLI`** (via the `run-bitcoin-cli` wrapper to `zero-cli`). RPC tests invoke binaries by absolute path.

---

## Adding and extending tests

### Boost (`test_bitcoin`)

- Add or extend `src/test/*_tests.cpp` (see existing `rpc_tests.cpp`, `rpc_zeronode_tests.cpp`, `rpc_zeronode_budget_tests.cpp`, `rpc_zero_exclusive_tests.cpp`).
- Register suites with the Boost.Test macros used elsewhere in `src/test/`.
- Build `src/test/test_bitcoin`, then run `./src/test/test_bitcoin -t YourSuite` or a single case name.
- For RPC shape checks, follow **`CallRPC` / `CheckRPCThrows`** patterns in `rpc_zeronode_tests.cpp`.

### GTest (`zero-gtest`)

- Primary wallet/consensus tests live under `src/wallet/gtest/` and related includes.
- Build `src/zero-gtest`, run `./src/zero-gtest` or narrow with `--gtest_filter=...`.
- Prefer **isolated** filters when debugging (`--gtest_break_on_failure`, debugger on core).

### RPC Python (`qa/rpc-tests`)

- Add `qa/rpc-tests/your_feature.py` using **`BitcoinTestFramework`** from `test_framework/test_framework.py`.
- Run `./qa/pull-tester/rpc-tests.sh your_feature`.
- To promote a script into the default pass-only set, add its basename (no `.py`) to the **`PYTHON_PASSING`** array in **`contrib/run-tests.sh`** after it is verified stable.
- Reuse **`initialize_chain`** when possible (faster than `initialize_chain_clean`). Regtest subsidy helpers live in **`test_framework/util.py`** (`zero_regtest_subsidy`, etc.).

### Zeronode coverage (already in Boost)

- **`rpc_zeronode_tests`**: read-only and param paths for many zeronode RPCs.  
- **`rpc_zeronode_budget_tests`**: budget-related RPCs.  
- Run with **`-t`** as in §Scenarios.

---

## Coverage overview (high level)

| Area | Automated coverage (typical) |
|------|------------------------------|
| Core blockchain, crypto, Zcash shielded primitives | Strong (GTest + Boost + vectors) |
| RPC and wallet | Strong (Boost `rpc_tests`, `rpc_wallet_tests`, RPC Python) |
| Network / P2P | Moderate (Python + mininode; not every edge case) |
| Zeronode | RPC-level Boost tests; little integration of full zeronode logic in Python |

---

## Troubleshooting

- **`ImportError` / pyblake2:** Install **`pyblake2`** or use Python 3.6+ with **`hashlib.blake2b`** (mininode tries both).
- **`PYTHON=...: No such file or directory`:** Use `env PYTHON=...` or ensure `python3` is on `PATH`; current `run-tests.sh` uses `env` when spawning RPC tests.
- **Boost or GTest “cascade”:** Failures in one module can leave global state for the next; rerun a **single** `-t` suite or use **`contrib/run-boost-individual.sh`**.
- **RPC tests cannot find binaries:** Check **`qa/pull-tester/tests-config.sh`** and that **`zerod` / `zero-cli`** are built where **`BUILDDIR`** points.
- **macOS `--full`:** `sec-hard` and `no-dot-so` are skipped by `run-tests.sh` so the full-suite driver can complete without ELF-only tooling or a full depends layout.
- **Orphaned `zerod` on macOS:** RPC tests use temp dirs under `/var/folders/.../T/`. If a run is killed mid-test, `run-tests.sh` tries to clean known patterns on Darwin; manually: `pkill -f "zerod -datadir=/var/folders"` if needed.
