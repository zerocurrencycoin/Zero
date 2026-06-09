Regression tests of RPC interface
=================================

### [test_framework/test_framework.py](test_framework/test_framework.py)
Base class for RPC regression tests.

### [test_framework/util.py](test_framework/util.py)
Generally useful functions: **`initialize_chain`**, **`initialize_chain_clean`**, **`COINBASE_MATURITY`**, maturity helpers.

Notes
=====

### Run one script

From repo root (after building `src/zerod` / `src/zero-cli`):

```bash
./qa/pull-tester/rpc-tests.sh <basename>
```

Examples:

```bash
./qa/pull-tester/rpc-tests.sh rpcbind_test
./qa/pull-tester/rpc-tests.sh wallet_overwintertx
```

Standalone scripts (`rpcbind_test.py`, `keypool.py`) can also be invoked directly; **`cache/`** is cwd-relative, so run from repo root when using `initialize_chain`:

```bash
export PATH="$PWD/src:$PATH"
export BITCOIND="$PWD/src/zerod"
export BITCOINCLI="$PWD/src/zero-cli"
PYTHONPATH=qa/rpc-tests python3 qa/rpc-tests/rpcbind_test.py --srcdir src
```

Add `--nocleanup` to keep the temp datadir after a standalone run.

### RPC tiers

See `TEST_ZERO.md`. Script names are authoritative in `qa/pull-tester/rpc-tests.sh` arrays only.

- `qa/pull-tester/rpc-tests.sh -A` -- Tier A gate
- `qa/pull-tester/rpc-tests.sh -B` -- Tier B pass
- `qa/pull-tester/rpc-tests.sh -list-csv [path]` -- `tier,group,script` CSV (one script per line, grouped)
- `qa/pull-tester/rpc-tests.sh -Bfail` -- Tier B known fail (Debug then Retired; diagnostic)
- `qa/pull-tester/rpc-tests.sh -E` -- Ext pass
- `qa/pull-tester/rpc-tests.sh -Efail` -- Ext known fail (diagnostic)
- `qa/pull-tester/rpc-tests.sh -all` -- `-A` then `-B` then `-E` (pass tiers)
- `qa/pull-tester/rpc-tests.sh -rpcfail` -- `-Bfail` then `-Efail`
- `qa/pull-tester/rpc-tests.sh` (no args) -- same as `-all`

Regenerate human-review tier inventory:

```bash
./qa/pull-tester/rpc-tests.sh -list-csv qa/rpc-tests/test_tier_inventory.csv
```

### `initialize_chain` cache

Defined in `test_framework/util.py`. Frozen datadir: **`<cwd>/cache/node{0..3}/`**. With `contrib/run-tests.sh` or `./qa/pull-tester/rpc-tests.sh` from repo root, cwd is the repo -> **`<repo>/cache/`** (gitignored), **not** `qa/rpc-tests/cache/`. Verified: `keypool` / `blockchain` / `rpcbind_test` create `<repo>/cache/` only.

First build: 200-block upstream distribution, then mine to **`COINBASE_MATURITY` [720] + 5** on node 0. Only **`blockchain.py`**, **`keypool.py`**, and **`rpcbind_test.py`** copy this cache; other scripts use **`initialize_chain_clean`**.

Delete `cache/` after changing `COINBASE_MATURITY`, post-200 extension, or cache-build `-nuparams` in `util.py`.

```bash
rm -rf cache
killall zerod
```

### Framework options

```
-h, --help       show this help message and exit
  --nocleanup      Leave zerods and test.* datadir on exit or error
  --noshutdown     Don't stop bitcoinds after the test execution
  --srcdir=SRCDIR  Source directory containing zerod/zero-cli (default:
                   ../../src)
  --tmpdir=TMPDIR  Root directory for datadirs
  --tracerpc       Print out all RPC calls as they are made
```

`PYTHON_DEBUG=1` enables verbose framework logging.
