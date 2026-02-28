# TEST_ZERO

How to run the Zero node test suite. Procedures, commands, and expected results.

---

## Prerequisites

- **Build complete:** `zerod`, `zero-cli` built. See [BUILD_ZERO.md](BUILD_ZERO.md).
- **Python 2.7** (for RPC tests): `python2 -m pip install pyblake2`. Set `PYTHON` or use pyenv 2.7.18; run-tests.sh auto-detects.
- **Working directory:** Run from repo root. `contrib/run-tests.sh` resolves root from its path.

---

## Quick Run

```bash
./contrib/run-tests.sh
```

Runs Util, secp256k1, univalue, GTest (filtered), Boost (pass-only), RPC Python (pass-only). Logs in `test-logs/`. Continues on failure.

---

## Test Suites

| Suite | What it tests | Invocation |
|-------|---------------|------------|
| Util | Base58, keys, JSON | `cd src && srcdir=$(pwd) PYTHONPATH=$(pwd)/test python3 test/bitcoin-util-test.py` |
| secp256k1 | Elliptic-curve crypto | `make -C src/secp256k1 check` |
| univalue | JSON library | `make -C src/univalue check` |
| GTest | Consensus, wallet, shielded | `./src/zero-gtest [--gtest_filter=...]` |
| Boost | RPC, script, serialization, crypto | `./src/test/test_bitcoin [--run_test=...]` |
| RPC Python | Multi-node, zerod/zero-cli | `./qa/pull-tester/rpc-tests.sh [script\|-extended]` |

---

## Runners and Modes

| Mode | Command | Use case |
|------|---------|----------|
| Default | `./contrib/run-tests.sh` | Pass-only; quick validation |
| With failures | `./contrib/run-tests.sh --fail` | See failing tests |
| Full suite | `./contrib/run-tests.sh --full` | Release validation |
| Quick | `./contrib/run-tests.sh --quick` | Incremental build check (no GTest/Boost) |
| No Python | `./contrib/run-tests.sh --no-python` | Skip RPC Python |
| Parallel RPC | `./contrib/run-tests.sh --jobs=4` | Faster RPC Python runs |

---

## Scenarios

| Scenario | Command |
|----------|---------|
| Validate incremental build | `./contrib/run-tests.sh --quick` |
| Full or release validation | `./contrib/run-tests.sh --full` |
| Verify specific feature | `./src/test/test_bitcoin -t rpc_tests` or `./qa/pull-tester/rpc-tests.sh wallet_sapling` |
| Debug GTest crash | `./src/zero-gtest --gtest_filter='WalletTests.CachedWitnessesEmptyChain' --gtest_break_on_failure` |

---

## Expected Results

| Suite | Pass | Excluded / Skip |
|-------|------|-----------------|
| Util, secp256k1, univalue | All | — |
| GTest | 201 | 5 (CachedWitnesses*, WriteCryptedSaplingZkey*) |
| Boost (pass-only) | 47 suites | 3 (Alert, equihash, miner) |
| RPC Python (pass-only) | 19 pass (verified) | — |

---

## RPC Python Options

- `--nocleanup` — Leave zerods and test datadir on exit
- `--noshutdown` — Don't stop zerods after test
- `--tracerpc` — Print RPC calls
- `--srcdir=SRCDIR` — Default `${BUILDDIR}/src`
- `--tmpdir=TMPDIR` — Test data directory

---

## Coverage Overview

| Area | Coverage |
|------|----------|
| Core blockchain, crypto, Zcash shielded | High |
| RPC, wallet | Good |
| Network/P2P | Moderate |
| Zeronode, budget, SwiftTX | Partial (RPC param/read-only); logic/integration none |

---

## Troubleshooting

- **ImportError pyblake2:** `python2 -m pip install pyblake2`
- **"PYTHON=...: No such file or directory":** Fixed in run-tests.sh (uses `env PYTHON=...`). Upgrade if you see this.
- **GTest/Boost cascade:** Run by suite (e.g. `-t rpc_tests`) to isolate
- **RPC tests fail:** Ensure `BUILDDIR`, `BITCOIND`, `BITCOINCLI` point to Zero binaries (tests-config.sh)
- **macOS --full:** Skips sec-hard and no-dot-so; suite completes
