Regression tests of RPC interface
=================================

### [test_framework/test_framework.py](test_framework/test_framework.py)
Base class for RPC regression tests.

### [test_framework/util.py](test_framework/util.py)
Generally useful functions: **`initialize_chain`**, **`initialize_chain_clean`**, **`COINBASE_MATURITY`**, maturity helpers.

Notes
=====

### Run one script on its own

Runner commands, tiers, and the RPC cache: TEST_ZERO "Run" and "Tiers". A script also runs without the runner, from the repository root after a build:

```bash
export PATH="$PWD/src:$PATH"
export BITCOIND="$PWD/src/zerod"
export BITCOINCLI="$PWD/src/zero-cli"
PYTHONPATH=qa/rpc-tests python3 qa/rpc-tests/rpcbind_test.py --srcdir src
```

Scripts that keep the framework's default `setup_chain` copy the cache `<repo>/cache/node{0..3}/` (`rpc_cache_root()` in `test_framework/util.py`; `ZERO_RPC_CACHE_DIR` overrides it). To rebuild it, stop the test nodes and remove `cache/`; the next run recreates it.

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
