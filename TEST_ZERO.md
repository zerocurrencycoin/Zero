# TEST_ZERO

Test the Zero full node: the merge gate, the release test run, held scripts, and operational checks on scratch data. Contributors need Run through Held scripts; maintainers also need Release bar and Operational checks. The scripts are authoritative: tier membership lives in the arrays of `qa/pull-tester/rpc-tests.sh`, and `contrib/run-tests.sh --help` and `contrib/ops-validate.sh --help` list every option.

Prerequisite: a build per BUILD_ZERO "Build", with `src/zerod` and the test binaries.

---

## Run

| Use | Command |
|-----|---------|
| Merge gate: C++ gate filters and Tier A | `./contrib/run-tests.sh --strict` |
| Release test run: adds Tiers B and E | `./contrib/run-tests.sh --all --strict` |
| Full suite with the ELF hardening checks (Linux) | `./contrib/run-tests.sh --suite` |
| C++ only | `./contrib/run-tests.sh --no-python --strict` |
| One tier | `./qa/pull-tester/rpc-tests.sh -A` (or `-B`, `-E`, `-L`, `-Bfail`, `-Efail`) |
| One RPC script | `./qa/pull-tester/rpc-tests.sh <basename>` |

Without `--strict`, `run-tests.sh` prints `WARNING` and exits 0 after a failed step; with it, it exits 1. A script that calls `skip_test` exits 0 without running. Logs are in `.build/test-logs/`.

`rpc-tests.sh` runs each script with `$PYTHON`, or with its `python3` shebang. The RPC cache `<repo>/cache/` is gitignored and rebuilt to height 725 when missing. Running a script on its own, with framework options such as `--nocleanup`: `qa/rpc-tests/README.md`.

Each script process takes 8 P2P ports in 24000-26999 and 8 RPC ports in 27000-29999 at offset `8 * pid % 2991` (`p2p_port`, `rpc_port` in `test_framework/util.py`, the Bitcoin Core layout). Scripts whose PIDs differ by less than 373 do not collide, so scripts can run in parallel. Run the gates serially: `--jobs` above 1 can hang `paymentdisclosure`.

---

## Layers

| Layer | Entry | In the merge gate |
|-------|-------|-------------------|
| Utilities, secp256k1, univalue, symbols | `src/test/bitcoin-util-test.py`, `make check`, `check-symbols`, `check-security` | Yes (`--quick` runs only these) |
| GTest | `src/zero-gtest` | Yes, except `WalletTests.CachedWitnessesCleanIndex` |
| Boost | `src/test/test_bitcoin` | Yes |
| Python RPC | `qa/pull-tester/rpc-tests.sh` | Tier A |
| Full suite | `qa/zcash/full_test_suite.py` | No; `--suite` only, ELF stages skipped on macOS |

The C++ gate filters are in `qa/zcash/test_filters.sh`.

---

## Tiers

| Tier | Group | Flag | Runs in |
|------|-------|------|---------|
| A | gate | `-A` | Merge gate and release test run |
| B | pass | `-B` | Release test run (`txn_doublespend` runs twice) |
| E | pass | `-E` | Release test run |
| L | large | `-L` | Only on request: `zerod` peak RSS 3 to 4 GiB, 1 to 4 minutes per script |
| Bfail | debug, retired | `-Bfail` | Diagnostic only: scripts to port, then Sprout-era scripts |
| Efail | fail | `-Efail` | Diagnostic only; `-rpcfail` runs `-Bfail` then `-Efail` |

`qa/rpc-tests/test_tier_inventory.csv` lists the scripts per tier. After every tier change, regenerate it in the same change set:

```bash
./qa/pull-tester/rpc-tests.sh -list-csv qa/rpc-tests/test_tier_inventory.csv
```

A held script moves to a pass tier after five clean serial runs.

---

## Writing tests for Zero

Regtest coinbase matures after `COINBASE_MATURITY` = 720 blocks and the RPC cache tip is `CACHE_TIP` = 725; Zcash tests assume 100 and 200. Write heights relative to `CACHE_TIP` or the current tip, and place upgrade activation relative to `COINBASE_MATURITY`. For spendable coinbase use `mine_until_mature`, `ensure_coinbase_utxos`, and `get_coinbase_address`; for amounts use `block_subsidy`, `miner_share`, and `founders_share` with `REGTEST_HALVING` (they cover the regtest founders window, heights 1000 to 1500). Heights in raw transactions are 4-byte little-endian. All helpers are in `qa/rpc-tests/test_framework/util.py`.

Equihash: Boost `equihash_tests` checks the mainnet (192,7) genesis and height-1 headers and the regtest (48,5) vectors in `src/test/data/`. A failing vector means `chainparams.cpp`, `pow.cpp`, or `CheckEquihashSolution` drifted: fix that code, never the parameters or the `ZERO_PoW` personalization, which would fork the node off mainnet. The Python solver (`test_framework/equihash.py`) solves (48,5) only and uses the `ZcashPoW` personalization, so blocks it solves fail on the node.

---

## Held scripts

Blockers from single serial runs on macOS.

| Hold | Scripts | Blocker |
|------|---------|---------|
| Height 200 | `wallet_addresses`, `rescan_import`, `reorg_limit`, `wallet_listnotes`, `wallet_sapling` | Assert `getblockcount() == 200` on the 725-block cache |
| Absolute heights | `wallet_listreceived` | `generate_and_sync` targets absolute heights at or below the cache tip |
| Clean chain below maturity | `wallet_changeaddresses`, `wallet_persistence`, `finalsaplingroot`, `shorter_block_times` | Mine 0 to 200 blocks on a clean chain, then need a coinbase that matures at 720 |
| Python-solved blocks | `bip65-cltv-p2p`, `bipdersig-p2p`, `invalidblockrequest`, `p2p-acceptblock` | Comptool and mininode blocks fail `CheckEquihashSolution` and `CheckProofOfWork` (personalization, see Writing tests for Zero) |
| GBT proposals | `getblocktemplate_proposals` | `template_to_bytes` builds a block the node rejects with "Block decode failed" |
| Fee estimate | `smartfees` | Pays to Bitcoin P2SH addresses, rejected as "Invalid Zero address" |
| Fork warnings | `hardforkdetection`, `forknotify` | `-blockversion=2` is below the minimum version 4; the node issues no warning for up-version blocks |
| Obsolete | `pruning` | Needs `-prune`, which Zero does not have; kept as the upstream reference |
| Retired Sprout | `prioritisetransaction`, `wallet_treestate`, `wallet_overwintertx`, `mergetoaddress_sprout`, `sprout_sapling_migration`, `turnstile`, `zcjoinsplit`, `zcjoinsplitdoublespend` | Sprout-era or manual testnet; `zcjoinsplit*` need a build with `-DENABLE_ZCRAW_RPC` |
| GTest | `WalletTests.CachedWitnessesCleanIndex` | Needs a reindex-style `pcoinsTip` and blocks on disk; run with `--fail` |

---

## Release bar

A test run proves one OS. On the release commit:

| Check | macOS ARM64 | Linux x86_64 | Windows |
|-------|-------------|--------------|---------|
| Build | `./zcutil/build.sh` | `./zcutil/build.sh` on Ubuntu 24.04 | `./zcutil/build.sh -win` on the Linux host |
| `./contrib/run-tests.sh --all`, summary clean | Required | Required, with `python3-zmq` so `zmq_test.py` runs | No runner; one start of `zerod.exe` instead, or the Windows archives leave the release |
| `--suite` | ELF stages skipped | Optional | -- |
| `./contrib/ops-validate.sh short`; `live` when a node runs on the operator datadir | Required | Required | -- |
| Zerowallet check (Operational checks) | Manual | Manual if used | Manual if used |

Record each artifact's hashes and signatures as present or missing. The maintainer decides which OS gates are hard blocks. Release steps: BUILD_ZERO "Release".

---

## Operational checks

`contrib/ops-validate.sh` starts nodes only on scratch data: `/tmp/zero-ops-validate` (RPC 23941) and `/tmp/zero-ops-eq` (RPC 23951), never the operator datadir unless `--force`. It refuses an RPC port in 23801-23820, which deployments use. `live` only reads the operator node over RPC.

| Commands | Needs | Use when |
|----------|-------|----------|
| `equihash`, `verifyeq`, `solveeq`, `mine` | Built binaries | A change to PoW, mining, or Equihash code; `solveeq` for timing only |
| `smoke`, `short`, `cold`, `restart`, `attach`, `stop` | Built binaries | Every release candidate (`short`); startup or shutdown changes |
| `live` | A node running on the operator datadir | Release candidate check against real data |
| `copy`, `reindex`, `rescan`, `bootstrap` | Source datadir stopped; snapshot archives or a `bootstrap.dat` copy | Changes to reindex, import, rescan, index settings, or wallet sync |

`mine` generates on regtest (48,5) and never mines mainnet; `verifyeq` and `solveeq` time mainnet (192,7) with `zcbenchmark`. Mainnet CPU mining: README "Optional CPU mining".

**Zerowallet.** No UI harness in this tree. Start a node with template `zerowallet` (`cold zerowallet keep`, then `attach`), point the wallet at it with matching `rpcuser`, `rpcpassword`, and `rpcport`, and check addresses, History, the sync spinner, and error dialogs without sending. An idle spinner does not prove sync.

**Explorer.** Template `insight`; its index settings must match the copied datadir, or the node reindexes. `getaddressbalance` and `getaddresstxids` on a disposable copy.
