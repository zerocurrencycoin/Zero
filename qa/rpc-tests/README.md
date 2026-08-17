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
./qa/pull-tester/rpc-tests.sh getchaintips
./qa/pull-tester/rpc-tests.sh wallet_changeaddresses   # Bfail Debug (clean chain + mature coinbase)
./qa/pull-tester/rpc-tests.sh txindex                  # Bfail Debug (pure -txindex; see TEST_ZERO)
./qa/pull-tester/rpc-tests.sh addressindex             # Tier B pass (insight)
```

Standalone scripts (`rpcbind_test.py`, `keypool.py`) can also be invoked directly. Cache path is **`rpc_cache_root()`** in `util.py` (default **`<repo>/cache/`**); gate scripts export **`ZERO_RPC_CACHE_DIR`**.

```bash
export PATH="$PWD/src:$PATH"
export BITCOIND="$PWD/src/zerod"
export BITCOINCLI="$PWD/src/zero-cli"
PYTHONPATH=qa/rpc-tests python3 qa/rpc-tests/rpcbind_test.py --srcdir src
```

Add `--nocleanup` to keep the temp datadir after a standalone run.

### RPC tiers

See `TEST_ZERO.md`. Script names are authoritative in `qa/pull-tester/rpc-tests.sh` arrays only.

Pass-tier counts (regenerate via **`-list-csv`**): **A=10**, **B pass=29** (28 unique; `txn_doublespend` x2), **E pass=8** (**`-all`** = **47** invocations). **Bfail Debug=25** (includes `txindex.py`), **Bfail Retired=6**, **Efail=5**. Exact lists: **TEST_ZERO.md** §3. B pass includes `reindex_shielded.py` and `wallet_witness_defer.py`.

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

Defined in `test_framework/util.py`. Frozen datadir: **`<repo>/cache/node{0..3}/`** via **`rpc_cache_root()`** (see **`TEST_ZERO.md`**). Only **four** scripts use it: **`blockchain.py`**, **`keypool.py`**, **`httpbasics.py`** (framework default), **`rpcbind_test.py`**.

First build: 200-block distribution, then mine to **`COINBASE_MATURITY` [720] + 5** (tip **725**) on node 0.

```bash
rm -rf cache qa/rpc-tests/cache
killall zerod 2>/dev/null || true
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
