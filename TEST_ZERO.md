# TEST_ZERO

How to run the Zero node test suite: commands, what each layer covers, and how to add or extend tests. **Tier definitions, the 19 pass-only RPC names, expected counts, extended-RPC taxonomy, upstream comparison, and fix / skip / abandon proposals:** [UpdateTests.md](UpdateTests.md) §2.

---

## Prerequisites

- **Build:** `zerod`, `zero-cli`, and (for C++ unit tests) `src/test/test_bitcoin` and `src/zero-gtest`. Build steps and toolchain requirements are in [BUILD_ZERO.md](BUILD_ZERO.md) (§1.1).
- **Python 3.10+** for RPC tests and `qa/zcash/full_test_suite.py` (maintainer runs use **Python 3.12**). `contrib/run-tests.sh` picks `python3`, or `python` if it reports 3.10+, unless you set **`PYTHON`** before invoking the script (exported as `PYTHON` for RPC runs).
- **Working directory:** Repo root. `contrib/run-tests.sh` changes to the repo root automatically; manual commands below assume you are at the root unless `cd src` is shown.
- **GTest** is built from the pinned **depends** package (GoogleTest 1.16.x, C++14). Upgrading the dependency may require a C++17 toolchain if you move past that line.
- **Optional:** `python3 -m pip install pyblake2` only if `qa/rpc-tests/test_framework/mininode.py` fails to use `hashlib.blake2b` (standard library blake2b is sufficient on 3.10+ in normal use).

### Coinbase maturity — verified in code

| Chain | Constant | Where to verify |
|-------|----------|-----------------|
| **Zero** | **720** | `src/consensus/consensus.h` — `COINBASE_MATURITY` |
| **Bitcoin Core** | **100** | Upstream `src/consensus/consensus.h` — `COINBASE_MATURITY` |
| **Zcash** upstream | **100** | [Zcash `src/consensus/consensus.h`](https://github.com/zcash/zcash/blob/master/src/consensus/consensus.h) — `COINBASE_MATURITY`; ZIPs cover shielded coinbase behavior |

**Zero’s 720** is a **fork-level change** from both Bitcoin **100** and Zcash **100**; regtest uses the same **`consensus.h`** value. Many legacy RPC tests mine **100–200** blocks and assume Bitcoin-like maturity; they fail on Zero unless they mine **≥720**, use **`ZERO_MINE_COINBASE=1`** where supported, or skip. See **`qa/rpc-tests/test_framework/util.py`** and **`wallet.py`** for helpers and comments.

---

## Quick run

```bash
./contrib/run-tests.sh
```

**What runs (default, not `--quick`):**

1. **Util** — `python3 src/test/bitcoin-util-test.py` (script uses `python3` explicitly).
2. **secp256k1-check** and **univalue-check** — `make -C src` targets.
3. If **`src/zerod` is executable:** **check-symbols** and **check-security** (`make -C src`).
4. **GTest** and **Boost** — started **in parallel** (two background jobs): filtered `zero-gtest` and filtered `test_bitcoin`, then the script waits for both.
5. **RPC Python** — the **19** pass-only scripts (names and tier status: [UpdateTests.md](UpdateTests.md) §2.1) (sequential if `--jobs=1`, parallel if `--jobs=N`).

Logs go under **`test-logs/`** with a timestamp prefix. The default mode **continues after failures** (`|| true` on most steps) so one failure does not stop the rest.

---

## How runs are organized

| Layer | Role |
|-------|------|
| **Suites 1–3** | Fast checks with no full node: util JSON/base58, secp256k1, univalue. |
| **Optional (when `zerod` exists)** | **check-symbols**, **check-security** on the default run (not only `--quick`). |
| **Suite 4 — GTest** | Wallet/gtest and consensus-oriented tests in `zero-gtest`. |
| **Suite 5 — Boost** | `test_bitcoin`: RPC, script, serialization, crypto, zeronode RPC tests, etc. |
| **Suite 6 — RPC Python** | `qa/rpc-tests`: spawn `zerod`, multi-node regtest, end-to-end RPC. |
| **Suite 7 — sec-hard** | `make -C src check-security` plus, on ELF Linux, extra hardening checks inside `full_test_suite`. |
| **Suite 8 — no-dot-so** | `full_test_suite` stage that inspects `depends/` for stray `.so` files (release/depends workflows). |
| **`make -C src check`** | Recursive check that overlaps util, secp, univalue, and Boost when enabled in the build. |

**`./contrib/run-tests.sh --quick`** runs steps 1–2 and, if `zerod` exists, step 3; it **skips** GTest, Boost, and RPC Python.

**`./contrib/run-tests.sh --full`** (same as **`--full-suite`**) runs **only** `python3 qa/zcash/full_test_suite.py`. It does **not** run the default util/secp/univalue/GTest/Boost/RPC sequence. Stages, in order:

`btest` → `gtest` → `sec-hard` → `no-dot-so` → `util-test` → `secp256k1` → `univalue` → `rpc`

- **`btest`** — `./src/test/test_bitcoin -p` plus the same pass-only **`--run_test`** exclusions as the default **`run-tests.sh`** run (**Pass-only filters** below). Use **`python3 qa/zcash/full_test_suite.py --unfiltered`** or **`ZERO_FULL_SUITE_UNFILTERED=1`** to run every built Boost test (may **hang** on known wallet cases).
- **`gtest`** — **`zero-gtest`** with the same pass-only **`--gtest_filter`** as default **`run-tests.sh`**, unless **`--unfiltered`** / **`ZERO_FULL_SUITE_UNFILTERED=1`**.
- **`rpc`** — `./qa/pull-tester/rpc-tests.sh` with **no arguments**, which runs every script in the script’s main **`testScripts`** list (plus optional ZMQ/Proton entries when enabled). That is a **large** set—not the 19-script pass-only list and **not** the **`testScriptsExt`** block unless you pass **`-extended`** to `rpc-tests.sh` yourself.

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

## Test suites and direct commands

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

## Runners and modes for contrib/run-tests.sh

| Mode | Command | Behavior (summary) |
|------|---------|-------------------|
| Default | `./contrib/run-tests.sh` | Pass-only **GTest** filter; pass-only **Boost** `--run_test` exclude list; **19** RPC scripts; logs under `test-logs/` |
| `--fail` | `./contrib/run-tests.sh --fail` | **GTest** still uses the pass-only filter (hang-prone cases stay excluded). **Boost** runs **without** `--run_test` exclusions. **RPC** runs **`rpc-tests.sh -extended`**. |
| `--all` | `./contrib/run-tests.sh --all` | **GTest** and **Boost** with **no** filters. **RPC** `-extended`. May hang on known wallet DB / encryption cases. |
| `--full` | `./contrib/run-tests.sh --full` | Only `qa/zcash/full_test_suite.py` (see **How runs are organized**). Exits **1** if any stage fails. |
| `--quick` | `./contrib/run-tests.sh --quick` | Util, secp, univalue, and (if `zerod` exists) check-symbols + check-security; **no** GTest, Boost, or RPC |
| `--no-python` | `./contrib/run-tests.sh --no-python` | Skips RPC Python; still runs util through Boost per other flags |
| `--jobs=N` | `./contrib/run-tests.sh --jobs=4` | Pass-only RPC scripts run concurrently (cap `N` to the machine) |
| `--build-checks` | `./contrib/run-tests.sh --build-checks` | Runs **`make -C src check-security`** once (needs Python on `PATH` for the security-check script) |

**Environment**

- **`PYTHON`** — If set before `run-tests.sh`, used to resolve the interpreter for RPC and `full_test_suite`; also exported as `PYTHON` for RPC subprocesses. The bundled util step still invokes **`python3`** by name in the script.
- **`ZERO_MINE_COINBASE=1`** — When set, some RPC helpers can mine extra blocks for coinbase maturity (slow; not used in the default pass-only list).
- **`LOG_DIR`** — Override log directory (default `test-logs/` under repo root).

---

## Pass-only filters to copy

These are what **`run-tests.sh`** uses for the default run (and for **`--fail`**, only **GTest** keeps this filter).

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

Canonical **19** basenames, expected layer counts, and how to interpret **skip** vs **pass:** [UpdateTests.md](UpdateTests.md) §2.1. The **`PYTHON_PASSING`** array in **`contrib/run-tests.sh`** is the executable source of truth for order and membership.

---

## Scenarios

| Goal | Command |
|------|---------|
| Incremental build smoke | `./contrib/run-tests.sh --quick` |
| Release-style full driver | `./contrib/run-tests.sh --full` |
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

### Boost tests in test_bitcoin

- Add or extend `src/test/*_tests.cpp` (see existing `rpc_tests.cpp`, `rpc_zeronode_tests.cpp`, `rpc_zeronode_budget_tests.cpp`, `rpc_zero_exclusive_tests.cpp`).
- Register suites with the Boost.Test macros used elsewhere in `src/test/`.
- Build `src/test/test_bitcoin`, then run `./src/test/test_bitcoin -t YourSuite` or a single case name.
- For RPC shape checks, follow **`CallRPC` / `CheckRPCThrows`** patterns in `rpc_zeronode_tests.cpp`.

### GTest in zero-gtest

- Primary wallet/consensus tests live under `src/wallet/gtest/` and related includes.
- Build `src/zero-gtest`, run `./src/zero-gtest` or narrow with `--gtest_filter=...`.
- Prefer **isolated** filters when debugging (`--gtest_break_on_failure`, debugger on core).

### RPC Python in qa/rpc-tests

- Add `qa/rpc-tests/your_feature.py` using **`BitcoinTestFramework`** from `test_framework/test_framework.py`.
- Run `./qa/pull-tester/rpc-tests.sh your_feature`.
- To promote a script into the default pass-only set, add its basename (no `.py`) to the **`PYTHON_PASSING`** array in **`contrib/run-tests.sh`** after it is verified stable.
- Reuse **`initialize_chain`** when possible (faster than `initialize_chain_clean`). Regtest subsidy helpers live in **`test_framework/util.py`** (`zero_regtest_subsidy`, etc.).

### Zeronode coverage in Boost

- **`rpc_zeronode_tests`**: read-only and param paths for many zeronode RPCs.  
- **`rpc_zeronode_budget_tests`**: budget-related RPCs.  
- Run with **`-t`** as in the scenarios table above.

---

## Coverage overview

| Area | Automated coverage (typical) |
|------|------------------------------|
| Core blockchain, crypto, Zcash shielded primitives | Strong (GTest + Boost + vectors) |
| RPC and wallet | Strong (Boost `rpc_tests`, `rpc_wallet_tests`, RPC Python) |
| Network / P2P | Moderate (Python + mininode; not every edge case) |
| Zeronode | RPC-level Boost tests; little integration of full zeronode logic in Python |

---

## Troubleshooting

- **`ImportError` / pyblake2:** Install **`pyblake2`** or rely on **`hashlib.blake2b`** on Python 3.10+ (mininode tries both).
- **`PYTHON=...: No such file or directory`:** Use `env PYTHON=...` or ensure `python3` is on `PATH`; RPC invocations use `env PYTHON="$PY3"` when spawned from `run-tests.sh`.
- **Boost or GTest “cascade”:** Failures in one module can leave global state for the next; rerun a **single** `-t` suite or use **`contrib/run-boost-individual.sh`**.
- **RPC tests cannot find binaries:** Check **`qa/pull-tester/tests-config.sh`** and that **`zerod` / `zero-cli`** are built where **`BUILDDIR`** points.
- **macOS `--full`:** `sec-hard` and `no-dot-so` are skipped by `run-tests.sh` so the full-suite driver can complete without ELF-only tooling or a full depends layout.
- **Orphaned `zerod` on macOS:** RPC tests use temp dirs under `/var/folders/.../T/`. If a run is killed mid-test, `run-tests.sh` tries to clean known patterns on Darwin; manually: `pkill -f "zerod -datadir=/var/folders"` if needed.

---

## Extended RPC list versus pass-only

**Summary:** **`qa/pull-tester/rpc-tests.sh`** with **no arguments** runs the long **`testScripts`** list. Default **`contrib/run-tests.sh`** runs only **`PYTHON_PASSING`** (**19** scripts). **`--full`** drives **`full_test_suite.py`**, whose **`rpc`** stage calls **`rpc-tests.sh`** with **no arguments**, so you get the long list—not the 19-script set.

**Tier B/C listings, failure taxonomy (A–F), upstream comparison, skip vs fix vs abandon, and process proposals:** [UpdateTests.md](UpdateTests.md) §2.2–§2.6.
