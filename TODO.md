# TODO

Open follow-ups for the Zero full node (`zerod`).

---

## Tracking rules

**Names.** Each item has a title of one to three words, in bold at the start of its entry, followed by `--` and imperative sentences. Titles carry no ID, prefix, or number.

**One definition.** An item is described in one place: here, as a one-line entry with an optional Full description.

**TODO and TEST_ZERO.** TEST_ZERO describes the tests as they run now: commands, layers, tiers, held scripts with their blockers, the release bar, and operational checks. TODO holds the changes to make. A test item names the TEST_ZERO section or row it changes and does not restate its blockers or commands; when the change lands, TEST_ZERO is updated and the item removed.

**Status is the section.**

- **Release** -- work the v4.1.0 tag waits for, in order. Nothing else belongs here.
- **After release** -- accepted work the release does not wait for, grouped by subject. An item that needs keys, hosting, data, or a product decision, or that changes node behavior, ends with "Maintainer."; any other item is ready for a contributor. A short status note (postponed, not scheduled, decide after X) is allowed.
- **Done** -- remove the entry. The outcome lives in the code, the documentation of the behavior, and the release notes; no completed-items lists.

---

## Release

1. **Branch cleanup** -- After the release content is complete and before the tags, squash and clean up the old branches, tags, and commits, including the `perf-*` and `zero-401` branches. List each branch with its merge and tag status before deletion.
2. **Release candidate** -- Rebuild at the release commit, run `check-release.sh` before and after the tag, and tag `v4.1.0-rc1` on `zero-410`, per BUILD_ZERO "Release".
3. **Release platforms** -- Build, test, and package on Linux and Windows at the `v4.1.0-rc1` tag per TEST_ZERO "Release bar".
4. **Release signing** -- Decide checksums and signing per platform; method in progress. Decide after the `v4.1.0-rc1` cross-platform tests, before v4.1.0; BUILD_ZERO "Release" then gets the signing and verify commands.
5. **Release tag** -- Set `_CLIENT_VERSION_BUILD` to 50, regenerate the man pages, tag `v4.1.0`, and merge into `master`, per BUILD_ZERO "Release".

---

## After release

Wallet:

- **Const wallet reads** -- Continue const conversion on wallet-tx read paths.

RPC:

- **RPC dispositions** -- Decide the Sprout RPCs and record test depth per RPC from the harness in `doc/RPCs.csv`; v4.1.0 ships the dispositions the file records now. The accounts RPCs stay deprecated until Zerowallet lists transparent addresses with `listreceivedbyaddress`. Maintainer.
- **Wallet interface** -- Write the public node-wallet interface contract: RPCs and parameters Zerowallet uses, error codes and retry rules, `zero.conf` keys, data and parameter paths, and the node-wallet version table; Zerowallet links to it. The v4.1.0 changes that clients see are in its release notes, "Upgrade actions" and "RPC". Maintainer.
- **getalldata cost** -- Measure poll cost on a large wallet first, then the follow-up steps. Maintainer.
- **RPC removal** -- Remove the code of RPCs that leave Zero, starting with the compiled-out Sprout raw JoinSplit RPCs; postponed; follows RPC dispositions. Maintainer.

Node operation:

- **Reindex safeguards** -- Refuse a `reindex=` line in `zero.conf` and an unforced `DB_FLAG` mismatch unless `-reindexforce`; skip the wallet replay below a height. Maintainer.
- **Conf checks** -- Check automatically that every key in `contrib/zero.conf` and `contrib/conf-templates/` is a parsed option and that shown defaults match `zerod -help` and `-help-debug`; add a default column to `doc/Options.csv` generated from the help text; run the check in `contrib/run-tests.sh` and `zcutil/check-release.sh`. `contrib/tools/inventory-check.py` counts commented-out `GetArg` calls as parsed options, so it missed `prune` and `txindex`; parse only live code. Maintainer.
- **Conf templates test** -- Start `zerod` in a lab datadir with each generated template and stop it cleanly, then exercise each template's use case; automate in `contrib/ops-validate.sh`. For `zerowallet`, replace the two-step check in TEST_ZERO "Release bar" with one `ops-validate.sh` run: copy the `--wallet` file in for `cold` and `copy` as `rescan` does, and add a peered mode on lab ports that syncs a datadir copy. Maintainer.
- **Lab datadir setup** -- Review and harmonize how test scenarios set up datadirs and configuration (`contrib/ops-validate.sh` labs and templates, the RPC test cache, height-bounded labs), and complete their documentation in TEST_ZERO; performance measurement stays out of scope. Maintainer.
- **Chain diagnostics** -- Port the diagnostic and recovery tools that Zero lacks; postponed. Maintainer.

Network and P2P:

- **Peer discovery** -- Review how a new node finds peers: the DNS seed names in `vSeeds` (`src/chainparams.cpp`) and their records, a crawling seeder that publishes only live nodes, and the fixed-seed fallback. `src/chainparamsseeds.h` has empty mainnet and testnet arrays, `contrib/seeds/nodes_main.txt` and `nodes_test.txt` list no nodes, and `contrib/seeds/README.md` describes Bitcoin Core 0.10 seeds; fill the fallback from long-running nodes and refresh it each release. Maintainer.
- **Peer defenses** -- Port the peer-management features Bitcoin Core added after 0.12: the per-peer `addr` rate limit with its `getpeerinfo` counters (also in zcashd), feelers and test-before-evict, block-relay-only connections, anchors, and `-asmap`, each with its Bitcoin Core functional test adapted to Zero's harness; postponed. Maintainer.
- **Tor compile-out** -- Add a `--disable-tor` configure option that compiles out Tor control; runtime onion is already off by default; keep it separate from I2P. Maintainer.
- **Block relay** -- Port `sendheaders` (BIP 130); postponed. Maintainer.

Consensus:

- **Time adjustment** -- Port zcashd's `-maxtimeadjustment` (v2.1.1-1) and its warning-only form (v2.1.2): the node uses its own clock, `getpeerinfo` keeps `timeoffset`, and the RPC warnings report a large median offset; add `timedata_tests` cases and a BUILD_ZERO "Clock" note that NTP is required; postponed. Maintainer.
- **Difficulty review** -- Model Digishield with Zero's parameters (ZERO_COIN "Chain") against LWMA and ASERT on recorded chain data, and decide whether to change the algorithm in a network upgrade; postponed. Maintainer.
- **Reorg defenses** -- Publish confirmation guidance for exchanges, then decide whether a consensus defense is needed; checkpoints are item "Checkpoint update"; not scheduled. Maintainer.

Mempool and fees:

- **Fee policy** -- Decide on a conventional fee (ZIP 317) with the matching ZIP 401 constants, on free relay and coin-age priority, and on mempool limits for zero-fee and never-expiring transactions; postponed. Maintainer.
- **Refusal analysis** -- Classify transactions refused from peers by cause and report the counts per class through RPC; postponed. Maintainer.

Mining:

- **Coinbase tag** -- Add a `-coinbasetag=<text>` option that the internal miner and the `coinbasetxn` template append after the height (`COINBASE_FLAGS`, `CreateNewBlock` in `src/miner.cpp`), within the 100-byte coinbase input limit, so solo miners and pools that use the template are identifiable. Maintainer.
- **Stats tools** -- Give `chain_stats.py`, `decode_coinbase.py`, and `block_rate_replay.py` in `contrib/stats/` one shared RPC module in place of their own copies, and run `--help` and `py_compile` of each in `contrib/run-tests.sh`; postponed. Maintainer.

Monitoring:

- **Peer monitoring** -- Evaluate the monitoring examples and code of Bitcoin Core (tracepoints, message capture, log rate limit, `logging` RPC), zcashd (`setlogfilter`), and bmon first. Report connections and peer interactions for monitoring: counts by direction, connect, disconnect, and ban events with reasons, per-peer message and byte counters, and address-manager health, through RPC and a periodic summary line; per-event lines stay under `-debug=net`. Keep the `receive version message` line and `-logips` as they are. Maintainer.

Logging:

- **Log microseconds** -- Port `-logtimemicros` from Bitcoin Core: read it in `init.cpp`, list it in `-help-debug`, and append the microseconds of `GetTimeMicros` in `LogTimestampStr` (`src/util.cpp`); only the unused flag `fLogTimeMicros` exists; postponed.

Code text:

- **Fee wording** -- Apply CONTRIBUTING "Development fee naming" to text written before it: the `getblocksubsidy` help in `src/rpc/mining.cpp`; the `founders reward missing` log text in `src/main.cpp` (the reject reason stays); Zero-written comments in `src/main.h`, `src/main.cpp`, `src/consensus/params.h`, the regtest section of `src/chainparams.cpp`, `src/zeronode/budget.cpp`, and `src/test/rpc_wallet_tests.cpp`.

Tests:

- **Zero RPC depth** -- Test shielded outputs and filter types for the zs_* RPCs, `getsupply` values against the emission schedule (its help says "coin supply"; it returns the scheduled mint, not the measured supply), Sapling witness RPCs, and mined-transaction History in `getalldata`.
- **Test conversion** -- Convert the scripts of TEST_ZERO "Held scripts" except the Obsolete, Retired Sprout, and GTest rows, and promote each after five clean serial runs: the scripts of the height and maturity rows with the helpers in TEST_ZERO "Writing tests for Zero"; the Python-solved-block scripts by solving with the `ZERO_PoW` personalization in `test_framework/equihash.py`; then `getblocktemplate_proposals` and `smartfees`; then the Fork warnings row, adapted to Zero's block version floor and to warnings checked without `-alertnotify`. Postponed.
- **Witness rebuild coverage** -- Test witness rebuild (`-walletwitness=rebuild`) and bring the GTest row of TEST_ZERO "Held scripts" into the merge gate.
- **Test filters** -- Unify test tiers, filters, and their names across the runners.
- **Fuzz harness** -- Add libFuzzer targets under `src/fuzz/`.
- **Python cleanup** -- Adopt a format and lint check for Zero's Python files, share helpers in `contrib/stats` and `contrib/tools`, and unify script names and headers; postponed.
- **Benchmark clarity** -- Fix the `zcbenchmark` help and defective types, record timing samples, guard miner memory, and validate tromp, per Full description "Benchmark clarity"; postponed.

Build, packaging, and release:

- **Toolchain versions** -- Verify GCC, Rust, Python, and autotools versions per supported build OS, record them in BUILD_ZERO "Requirements", and check them in `zcutil/check-setup.sh`. Rust: Linux builds use the pinned 1.32.0 unless `RUST_USE_SYSTEM=1`, macOS the system Rust; decide the Linux default and the minimum Rust for `librustzcash`.
- **Windows hardening** -- Pass `--enable-hardening` in `build-win.sh`; needs the MXE build host.
- **Checkpoint update** -- Add a mainnet checkpoint and raise `nMinimumChainWork`, per Full description "Release constants"; postponed: needs investigation of the effects, coordination with pools and exchanges, and a validated way to detect and recover a node that is on a branch the checkpoint refuses. Maintainer.
- **Deprecation baseline** -- Decide the deprecation baseline and window, per Full description "Release constants"; postponed. Maintainer.
- **Upstream names** -- Upstream names stay in derived code, per Full description "Release constants"; review the three places where they send users to Zcash: the bug URL in `configure --help`, the security page in `zerod -help` and the man pages, and `doc/man/zcash-fetch-params.1`, which documents the script the release archives ship as `zero-fetch-params`. Maintainer.
- **Params mirror** -- Make a Zero-controlled copy of the three parameter files the primary source of `fetch-params.sh`, with GitHub release assets as a second copy, keeping zcashd's host and IPFS as fallbacks; verify file names and checksums. Maintainer.
- **Chain bootstrap** -- Document the end-user import path (`-loadblock`, auto-import), snapshot sourcing, and verification; linearize in `contrib/linearize/`. Maintainer.
- **CI workflows** -- Replace the `master` workflow with `.github/workflows/tests.yml` and extend it; postponed. Maintainer.
- **Contrib cleanup** -- Remove the inherited tools Zero does not use (`contrib/macdeploy`, `tidy_datadir.sh`, `verifysfbinaries`, `test-patches`, `spendfrom`, `verify-commits`, `qos`, `bitrpc`, and in `contrib/devtools` `github-merge.sh`, `fix-copyright-headers.py`, `optimize-pngs.py`) and their `contrib/README.md` entries; replace `contrib/init/` with one `zerod.service`; rename the bash completions to Zero's binaries and install them from the `.deb`. Maintainer.
- **Base58 vectors** -- Port zcashd's two-byte address prefixes to `contrib/testgen/gen_base58_test_vectors.py`, regenerate `src/test/data/base58_keys_*.json` with it, and confirm `base58_tests` against Zero's prefixes; postponed. Maintainer.
- **AMQP removal** -- Remove AMQP (`src/amqp/`, the Proton recipe in `depends`, `contrib/amqp/`, `proton_test.py`, `--enable-proton`), as zcashd did; ZMQ remains the notification path. Maintainer.
- **Windows ZMQ** -- Review enabling ZMQ in Windows builds (`build-win.sh` passes `--disable-zmq`): features needed, implementation, and tests. Maintainer.
- **Linux package** -- Add man pages, the example `zero.conf`, and bash completions to the `.deb` from `zcutil/release-linux.sh`, and the example `zero.conf` to the macOS and Windows archives. Maintainer.
- **Zerowallet conf** -- Align the `zero.conf` that Zerowallet writes (`rpcworkqueue`, `txindex`, `keeptx*`, `safekey`, macOS directory) with the node, coordinated with the Zerowallet release; under consideration. Maintainer.

Documentation:

- **Docs lint** -- Automate the documentation checks in `contrib/run-tests.sh`: relative links and section references resolve, ASCII outside README, no parentheticals in headings, named files exist, and documented commands run; then generate stated facts from the code. Maintainer.
- **Recovery guide** -- Add a recovery and maintenance section to BUILD_ZERO (`-reindex`, `-rescan`, witness rebuild, `-zapwallettxes`, transaction deletion, consolidation): when to use each and what it costs, generated in part from `doc/Reindex_Rescan.csv`. Maintainer.
- **Pool guidance** -- Publish a pool-operator section: coinbase rules, identification, relay, transaction policy, and the s-nomp recipient fix; postponed. Maintainer.
- **README claims** -- Back the README feature headings (fast and zero-cost transactions, ASIC resistance, unique algorithm) with facts and sources, or reword them; kept as branding for now. Maintainer.

Long-term, not scheduled:

- **LevelDB update** -- Update `src/leveldb` to LevelDB 1.22 as in Bitcoin Core and zcashd; restores block-cache usage in `getdbinfo`. Set 32 MiB table files (`max_file_size`, as Bitcoin Core and zcashd `DBWRAPPER_MAX_FILE_SIZE`) so the block index and chain state fit the table cache. Maintainer.
- **OpenSSL 3** -- Preference: move from OpenSSL 1.1.1w to 3.x, or remove OpenSSL as Bitcoin Core did; not scheduled. Call sites: wallet encryption in `src/wallet/crypter.cpp` (`EVP_BytesToKey`, AES-256-CBC through `EVP_*`), `OPENSSL_cleanse` in `src/support/cleanse.cpp`, locking and config setup in `src/util.cpp` (`CRYPTO_set_locking_callback`, `OPENSSL_no_config`, no-ops since 1.1.0), `BN_*` in `src/test/bignum.h`, and includes only in `src/init.cpp` and `src/zeronode/obfuscation.cpp`. RPC has no TLS (`-rpcssl` is refused). Maintainer.

---

## Full descriptions

Grouped by area. Each area opens with the state of the code and the decisions that span its items; the items follow.

### Release constants

Values compiled into each release. Once decided, BUILD_ZERO "Release" lists their update as a release step.

**Checkpoint.** Mainnet `checkpointData` in `src/chainparams.cpp` ends at height 700,000 (2019-10-20), with 1,376,076 transactions to that block and an estimate of 1,132 transactions per day after it. Below the last checkpoint `ConnectBlock` skips script checks and `ContextualCheckBlockHeader` refuses forks; `GuessVerificationProgress` extrapolates sync progress past it from the per-day estimate. `-checkpoints=0` turns off the first two. `consensus.nMinimumChainWork` dates from the same release; `IsInitialBlockDownload` stays true while the tip has less work. Update: a block well below the tip, its hash from `getblockhash` on two independently synced nodes, the transaction count and rate from `getchaintxstats`, and `nMinimumChainWork` from the `chainwork` of `getblockheader` at that block.

**Deprecation.** `src/deprecation.h`: `DEPRECATION_HEIGHT` is `APPROX_RELEASE_HEIGHT` plus `WEEKS_UNTIL_DEPRECATION` weeks of 120-second blocks: 1,385,000 + 520 x 5,040 = 4,005,800. `EnforceNodeDeprecation` runs on mainnet only: it warns once 4 weeks (20,160 blocks) before, through the log, `-alertnotify`, and the metrics screen, and shuts the node down at the height, with no option to override. `getdeprecationinfo` returns `deprecationheight`. `signrawtransaction` also takes `APPROX_RELEASE_HEIGHT` as the least height when it selects the consensus branch ID. The baseline 1,385,000 comes from an earlier release, so v4.1.0 inherits that release's shutdown height; blocks left: `getdeprecationinfo` minus `getblockcount`. Decide whether each release sets `APPROX_RELEASE_HEIGHT` to its release height, as zcashd does, and the window length; the comment "Fixing zero day size - was 1,392,080" in `deprecation.h` is change history and goes with the next edit.

**Upstream names.** Code derived from Bitcoin Core and Zcash keeps their names, so a Zero tree compares and merges against upstream with small diffs. `AC_INIT` in `configure.ac` names the package `Zcash`, the bug URL `https://github.com/zcash/zcash/issues`, and the tarname `zcash`; they set `PACKAGE_NAME`, `PACKAGE_BUGREPORT`, `PACKAGE_TARNAME`, the `make dist` archive name, and the default install `docdir`. `_COPYRIGHT_YEAR` is 2022: `LicenseInfo` in `src/util.cpp` prints "2009-2022 The Bitcoin Core Developers" and "2015-2022 The Zcash Developers", with no Zero line, and the man pages copy it; `COPYRIGHT_YEAR` and `COPYRIGHT_STR` in `src/clientversion.h` are the fallbacks for builds without the configure header. `PrivacyInfo` in `src/util.cpp`, the man pages, and README "Security Warnings" point to `https://z.cash/support/security/`. `doc/man/zcash-fetch-params.1` keeps the Zcash name. The package name, tarname, library and header names (`libzcash`, `bitcoin-config.h`), and the upstream copyright lines stay; the license requires the upstream notices, and a Zero holder line is a separate decision. Only text that sends users to Zcash is reviewed.

### getalldata cost

**Problem.** `getalldata` is the wallet client's single refresh call. Argument 1 (datatype) selects the payload: **0** addresses, balances, transactions, and chain info; **1** addresses, balances, and chain info; **2** transactions and chain info. Argument 2 is the day window (default 7 days), argument 3 the transaction count, argument 4 watch-only. Each call walks every wallet address and transaction (`mapWallet` plus the transaction archive), decrypts shielded notes, sorts history, and builds JSON; on wallets with long history that takes seconds, and clients poll every few seconds. In tree: the soft **-34** coalesce, the 7-day default window, const wallet walks, sort-key collision detection, and one parse/filter path for window, count, watch-only, and datatype (`IsGetAllDataTxTooOld`).

- **Poll cost** -- the split itself (balances on a timer, History on user action or every Nth tick) is a client change, outside this repository. The desktop wallet polls every 30 s but calls `getalldata 0 2 50 true` (datatype 0, 7-day window, 50 transactions, watch-only) only when a new block arrives; no other known client uses the RPC, and the node keeps no per-datatype statistics. Node side: measure both datatypes on a wallet with many transactions and archived entries (wall time, `getalldata` -34 rate under a fixed poll interval), then document the cadence. Complements the soft **-34** coalesce. Decides whether the tip cache is needed.
- **Tip cache** -- in-process tip and dirty cache, after poll cost. **Single walk**: merge History key insert into the balance walk. **Decrypt review**: IVK decryption cost.
- **Helpers** -- the remaining shared parse and filter helpers.
- **Address keys** -- key `addressBalances` by destination and encode once at JSON emit.

### Chain diagnostics

Presence per project: `doc/RPCs.csv` and `doc/Options.csv`; the tools Zero has: BUILD_ZERO "Chain diagnostics".

| Missing tool | From | Use here |
|--------------|------|----------|
| `getblockstats` | Bitcoin Core | Fees, transaction counts, and coinbase totals per block in one call; replaces the spent-output lookups of the coinbase audit |
| `-reindex-chainstate` | Bitcoin Core | Rebuild the chain state from the block files without rebuilding the block index |
| `dumptxoutset`, `loadtxoutset` | Bitcoin Core | Unspent-output snapshot; with item "Chain bootstrap" |
| `scantxoutset` | Bitcoin Core | Find outputs of payout or fee addresses without a wallet or the Insight index |
| `getblockfrompeer` | Bitcoin Core | Fetch a stale block the node did not keep, for fork attribution |
| `-stopatheight` | Bitcoin Core | Stop at a fixed height for reproducible snapshots and `contrib/ops-validate.sh` |
| `-persistmempool`, `savemempool` | Bitcoin Core | Keep the mempool across restarts |
| `logging`, `setlogfilter` | Bitcoin Core, zcashd | Change debug categories at runtime; with item "Peer monitoring" |
| `getindexinfo` | Bitcoin Core | Sync state of the transaction and Insight indexes |
| `uptime`, `getmemoryinfo`, `getrpcinfo` | Bitcoin Core | Node health for operators |

### CI workflows

**Now.** GitHub Actions is enabled on `zerocurrencycoin/Zero` (public, default branch `master`).

- `master` has only `.github/workflows/Zero_Linux_CI.yml`: on push and pull request to `master` and a daily cron (`0 19 * * *`), on `runs-on: ubuntu-18.04`. GitHub has retired that runner image, so jobs wait for a runner and are cancelled.
- `.github/workflows/tests.yml` (CONTRIBUTING "Continuous integration") exists only on `zero-410`, builds with `-j2` under a 240-minute timeout, and has never run: pushes to `zero-410` match none of its triggers, and `workflow_dispatch` needs the file on the default branch.

**Steps.** In order: run `tests.yml` on the release branch (add the branch to `on.push.branches`, or open the `zero-410` -> `master` pull request); after the `master` merge, `Zero_Linux_CI.yml` is gone and `tests.yml` runs on `master`; cache `depends/built` and the parameters between runs; add an `--all` job; add build and gate jobs on the hosted `ubuntu-22.04` runner and in an `ubuntu:20.04` container (`container:` in the job; hosted Ubuntu 20.04 runners are retired; `actions/checkout` needs glibc 2.28, so an `ubuntu:18.04` container cannot run it); add macOS and Windows cross-build jobs. The Large tier (`rpc-tests.sh -L`) stays out of CI.

### Test filters

To resolve after v4.1.0:

- Two parallel script lists in `qa/pull-tester/rpc-tests.sh`: the legacy `testScripts` and `testScriptsExt` arrays (all also in a tier) and the tier arrays.
- Names differ across runners: tiers `A`, `B`, `E` with groups `gate`, `pass`, `debug`, `retired`, `fail`; `rpc-tests.sh` flags `-A`, `-B`, `-E`, `-Bfail`, `-Efail`, `-rpcfail`, `-all`; `contrib/run-tests.sh` modes `--all`, `--fail`, `--rpcfail`, `--suite`.
- C++ filter variables in `qa/zcash/test_filters.sh`: `BOOST_PASS_EXCLUDE` is passed as a `--run_test` expression, `GTEST_PASS_EXCLUDE` is a negative GTest filter, and `full_test_suite.py` calls the same value `GTEST_PASS_FILTER`.
- Helper modules (`wallet_shieldcoinbase.py`, `mergetoaddress_helper.py`, `tx_expiry_helper.py`) sit next to tests with no marking; `script_test.py`, `proton_test.py`, and `wallet_shieldcoinbase_sprout.py` are in no tier.
- `qa/rpc-tests/test_tier_inventory.csv` is regenerated by hand; nothing checks it against the runner.
- Retired Sprout scripts and the Boost/GTest exclusion mechanism: review after v4.1.0 whether to keep, rewrite, or remove.
- `contrib/run-tests.sh` has no mode for the Large tier; only `rpc-tests.sh -L` runs it.
- `paymentdisclosure` can hang when `rpc-tests.sh` runs scripts in parallel (`--jobs` above 1), so the gates run serially.

Method: port the runner parts of Bitcoin Core `test/functional/test_runner.py` that answer these problems. `BASE_SCRIPTS` and `EXTENDED_SCRIPTS` as the one list per tier (Zero's pass tiers and Large); `NON_SCRIPTS` for helper modules; `check_script_list`, which fails when a Python file in the test directory is in no list, in place of the hand-regenerated CSV; `check_script_prefixes` for name prefixes (`wallet_`, `rpc_`, `p2p_`, `mempool_`, `feature_`); `--portseed` per job with `--jobs`, `--filter`, `--exclude`, and `--failfast`; per-script run times in the summary.

### Benchmark clarity

`zcbenchmark` (`src/zcbenchmarks.cpp`; help in `zc_benchmark`, `src/wallet/rpcwallet.cpp`), the timing in `contrib/ops-validate.sh`, and miner limits. Values measured on ARM64 macOS.

**Help.** The help lists no types, unit, or third parameter. `runningtime` is seconds at microsecond resolution (`gettimeofday`). `verifyequihash` and `solveequihash` use MAIN (192,7) on every network; `verifyequihash` checks the genesis header in every sample. List each type with unit, parameter, network, and input.

**Defective types.** Fix or remove:

| Type | Defect | Measured |
|------|--------|----------|
| `parameterloading` | Error -3: Sprout parameters removed | -- |
| `validatelargetx` | Default 11,130 inputs is the Zcash 2 MB transaction; `MAX_TX_SIZE_COSMOS` (200,000 bytes) allows about 1,110. Setup signs without precomputed data and grows with the square of the inputs | 1,000 inputs: 28 to 31 ms timed, 0.5 s wall per sample; 11,130: 0.34 s timed, 51 s wall |
| `incnotewitnesses`, `incsaplingnotewitnesses` | The timed `ChainTip` takes the initial-download branch (block time 0); `BuildWitnessCache(pindex, true)` returns after walking wallet notes, so no witness is incremented. The Sapling variant adds its second transaction to `block1`, leaving the timed block empty | 100 / 1,000 / 10,000 transactions: 3 / 26 / 320 us |
| `listunspent` | Times the wallet as found; a fresh node has no outputs | 1 us |

**Sizing table.** Only the operation is timed; per-sample setup can exceed it 150 times, so sample counts and sizes chosen from timed values overrun. After the defective types are fixed, run each type once at its smallest size, choose the parameter and a sample count of 10, 100, or 1,000 so each timed sample is between 100 ns and 10 s, and add a table to TEST_ZERO "Operational checks": type, parameter, sample count, timed value, wall time per sample, and peak RSS. Generate the table from the recorded samples (Recorded samples), not by hand; values measured before the fixes are not reused. Size the tromp validation the same way: one thread (3.25 GiB) and a 180 s window, which on ARM64 macOS gave 24 solver runs and 4 testnet blocks at minimum difficulty; a second thread only to check scaling.

**Recorded samples.** The ledger (`append_ledger`) keeps exit code and whole-second duration; `run_eq_bench` keeps no samples; `cold`, `restart`, and `stop` resolve whole seconds (`date +%s`, the 1 s poll in `wait_rpc`, a 2 s sleep in `restart`). Store each sample and time below one second.

**Miner limits.** Warn or refuse in `GenerateBitcoins` (`src/miner.cpp`) when threads times the solver memory in README "Optional CPU mining" exceeds physical memory; tromp checks cancellation only between rounds, so an out-of-memory miner does not stop.

**Tromp validation.** `zcbenchmark` cannot select tromp, and the tromp build (`WN 192`, `WK 7`) does not solve regtest (48,5). Mainnet cannot mine in isolation (`nMinimumChainWork`, `fMiningRequiresPeers`); testnet has (192,7) and minimum chain work 0. Add an `ops-validate.sh` command that runs two connected testnet lab nodes, one mining with one tromp thread and one validating, and a check of every tromp solution, not only those meeting the target. Mainnet mining is outside the v4.1.0 release bar: after the release, run README "Optional CPU mining" with one tromp thread on a synced mainnet node, then add it to TEST_ZERO "Release bar".
