# TODO

Open follow-ups for the Zero full node (`zerod`).

---

## Tracking rules

**Names.** Each item has a title of one to three words, in bold at the start of its entry, followed by `--` and imperative sentences. Titles carry no ID, prefix, or number.

**One definition.** An item is described in one place: here, as a one-line entry with an optional Full description.

**Status is the section.**

- **Ordered next** -- the next steps, in order; at most five.
- **Active** -- in progress or scheduled.
- **Research** -- needs study, experiments, a documented plan, and validation design before it can be scheduled.
- **Pending** -- accepted, not scheduled. Two parts, each grouped by subject: **Contributor-ready** items have a clear scope and need no keys, hosting, data, or product decision; **Maintainer** items need one of those or change node behavior. A short status note (postponed, does not gate a release, decide after X) is allowed.
- **Done** -- remove the entry. The outcome lives in the code, the documentation of the behavior, and the release notes; no completed-items lists.

---

## Ordered next

1. **Linux build** -- Build, test, and package at the release commit on the Ubuntu 24.04 build host, with `python3-zmq` installed.
2. **Windows build** -- Cross-build and package at the release commit on the Linux build host, then start `zerod.exe` once on Windows. Windows builds have no ZMQ (item "Windows ZMQ").
3. **Release signing** -- Decide checksums and signing per platform; method in progress. Decide after the `v4.1.0-rc1` cross-platform tests, before v4.1.0; BUILD_ZERO "Release" then gets the signing and verify commands.
4. **Release tags** -- Tag the release candidate and the release on `zero-410`; merge into `master`.

---

## Active

- **RPC dispositions** -- Decide the Sprout RPCs and record test depth per RPC from the harness in `doc/RPCs.csv`; the accounts RPCs stay deprecated until Zerowallet lists transparent addresses with `listreceivedbyaddress`.
- **Zeronode validation** -- Pass `zeronode_coinbase.py` and `zeronode_startalias.py` at the release commit; after v4.1.0, in order: registration success path on regtest, reorg test, automated `chainActive` checks, mainnet payment scan, public operator section in BUILD_ZERO.
- **Branch cleanup** -- Decide whether to squash commits before the `master` merge; deferred. List each branch with its merge and tag status before deletion.
- **Wallet interface** -- Write the public node-wallet interface contract: RPCs and parameters Zerowallet uses, error codes and retry rules, `zero.conf` keys, data and parameter paths, and the node-wallet version table; Zerowallet links to it. Decide after the `v4.1.0-rc1` cross-platform tests, before v4.1.0.
- **Docs pilot** -- BUILD_ZERO and TEST_ZERO are rewritten; next a documentation lint (duplicates, links, ASCII, runnable commands) and facts generated from the code, then ZERO_COIN and README.
- **Comment rules** -- Adopt the documentation and comment rules into the contributor instruction file. Postponed: retitle maintainer-document items to these titles and retire their IDs.

---

## Pending

After v4.1.0 unless noted.

### Contributor-ready

Wallet:

- **Const wallet reads** -- Continue const conversion on wallet-tx read paths.

Build:

- **Toolchain versions** -- Verify GCC, Rust, Python, and autotools versions per supported build OS, record them in BUILD_ZERO "Requirements", and check them in `zcutil/check-setup.sh`. Rust: Linux builds use the pinned 1.32.0 unless `RUST_USE_SYSTEM=1`, macOS the system Rust; decide the Linux default and the minimum Rust for `librustzcash`.
- **macOS deployment target** -- Export `MACOSX_DEPLOYMENT_TARGET` from the build system (libtool `-bind_at_load` warning).
- **Windows hardening** -- Pass `--enable-hardening` in `build-win.sh`; needs the MXE build host.

Tests:

- **Zero RPC depth** -- Test shielded outputs and filter types for the zs_* RPCs, `getsupply` values against the emission schedule, Sapling witness RPCs, and mined-transaction History in `getalldata`.
- **Fuzz harness** -- Add libFuzzer targets under `src/fuzz/`.
- **Python cleanup** -- Adopt a format and lint check for Zero's Python files, share helpers in `contrib/stats` and `contrib/tools`, and unify script names and headers; postponed.
- **Test filters** -- Unify test tiers, filters, and their names across the runners; details in Full descriptions.
- **Test conversion** -- Convert the held scripts of TEST_ZERO "Held scripts" except the Obsolete, Retired Sprout, and GTest rows, and promote each after five clean serial runs: the 10 scripts of the height and maturity rows with the section 1 helpers; the 4 Python-solved-block scripts by solving with the `ZERO_PoW` personalization in `test_framework/equihash.py`; then `getblocktemplate_proposals`, `smartfees`, `hardforkdetection`, and `forknotify`. Postponed.

### Maintainer

Zeronodes:

- **Zeronode legacy** -- Review doc/zeronodes.md; postponed.

RPC:

- **getalldata cost** -- Measure poll cost on a large wallet first, then the steps in Full descriptions.
- **RPC removal** -- Remove the code of RPCs that leave Zero, starting with the compiled-out Sprout raw JoinSplit RPCs; postponed; follows RPC dispositions.

Node operation:

- **Reindex safeguards** -- Refuse a `reindex=` line in `zero.conf` and an unforced `DB_FLAG` mismatch unless `-reindexforce`; skip the wallet replay below a height.
- **Tor compile-out** -- Add a `--disable-tor` configure option that compiles out Tor control; runtime onion is already off by default; keep it separate from I2P.
- **Address rate limit** -- Port the per-peer `addr` rate limit with its `getpeerinfo` counters from zcashd, as Pirate did, and add an RPC test; feelers and test-before-evict follow from Bitcoin Core.
- **Refusal analysis** -- Classify transactions refused from peers as timing, coincidence, or attempts, and alert on attempts; postponed. Details in Full descriptions.
- **Conf checks** -- Check automatically that every key in `contrib/zero.conf` and `contrib/conf-templates/` is a parsed option and that shown defaults match `zerod -help` and `-help-debug`; add a default column to `doc/Options.csv` generated from the help text; run the check in `contrib/run-tests.sh` and `zcutil/check-release.sh`. `contrib/tools/inventory-check.py` counts commented-out `GetArg` calls as parsed options, so it missed `prune` and `txindex`; parse only live code.
- **Conf templates test** -- Start `zerod` in a lab datadir with each generated template and stop it cleanly, then exercise each template's use case; automate in `contrib/ops-validate.sh`.
- **Lab datadir setup** -- Review and harmonize how test scenarios set up datadirs and configuration (`contrib/ops-validate.sh` labs and templates, the RPC test cache, height-bounded labs), and complete their documentation in TEST_ZERO; performance measurement stays out of scope.
- **Peer monitoring** -- Evaluate the monitoring examples and code of Bitcoin Core (tracepoints, message capture, log rate limit, `logging` RPC), zcashd (`setlogfilter`), and bmon first. Report connections and peer interactions for monitoring: counts by direction, connect, disconnect, and ban events with reasons, per-peer message and byte counters, and address-manager health, through RPC and a periodic summary line; per-event lines stay under `-debug=net`. Keep the `receive version message` line and `-logips` as they are.

Build, packaging, and release:

- **Params mirror** -- Make a Zero-controlled copy of the three parameter files the primary source of `fetch-params.sh` (the Cloudflare store that serves the chain archive, with GitHub release assets as a second copy), keeping zcashd's host and IPFS as fallbacks; verify file names and checksums.
- **Chain bootstrap** -- Document the end-user import path (`-loadblock`, auto-import), snapshot sourcing, and verification; linearize in `contrib/linearize/`.
- **Peer discovery** -- Review and improve how a new node finds peers: the DNS seed names in `vSeeds` (`src/chainparams.cpp`) and their records, a crawling seeder that publishes only live nodes, and the fixed-seed fallback (`contrib/seeds`, `chainparamsseeds.h`) filled from long-running nodes and refreshed each release.
- **CI workflows** -- Replace the `master` workflow with `.github/workflows/tests.yml` and extend it; postponed. Details in Full descriptions.
- **Contrib cleanup** -- Remove the inherited tools Zero does not use (`contrib/macdeploy`, `tidy_datadir.sh`, `verifysfbinaries`, `test-patches`, `spendfrom`, `verify-commits`, `qos`, `bitrpc`) and their `contrib/README.md` entries; replace `contrib/init/` with one `zerod.service`; rename the bash completions to Zero's binaries and install them from the `.deb`.
- **Base58 vectors** -- Port zcashd's two-byte address prefixes to `contrib/testgen/gen_base58_test_vectors.py`, regenerate `src/test/data/base58_keys_*.json` with it, and confirm `base58_tests` against Zero's prefixes; postponed.
- **AMQP removal** -- Remove AMQP (`src/amqp/`, the Proton recipe in `depends`, `contrib/amqp/`, `proton_test.py`, `--enable-proton`), as zcashd did; ZMQ remains the notification path.
- **Windows ZMQ** -- Review enabling ZMQ in Windows builds (`build-win.sh` passes `--disable-zmq`): features needed, implementation, and tests.
- **Linux package** -- Add man pages, the example `zero.conf`, and bash completions to the `.deb` from `zcutil/release-linux.sh`, and the example `zero.conf` to the macOS and Windows archives.
- **Zerowallet conf** -- Align the `zero.conf` that Zerowallet writes (`rpcworkqueue`, `txindex`, `keeptx*`, `safekey`, macOS directory) with the node, coordinated with the Zerowallet release; under consideration.
- **LevelDB update** -- Update `src/leveldb` to LevelDB 1.22 as in Bitcoin Core and zcashd; restores block-cache usage in `getdbinfo`. Set 32 MiB table files (`max_file_size`, as Bitcoin Core and zcashd `DBWRAPPER_MAX_FILE_SIZE`) so the block index and chain state fit the table cache.
- **OpenSSL 3** -- Long-term preference: move from OpenSSL 1.1.1w to 3.x, or remove OpenSSL as Bitcoin Core did; not scheduled. Call sites: wallet encryption in `src/wallet/crypter.cpp` (`EVP_BytesToKey`, AES-256-CBC through `EVP_*`), `OPENSSL_cleanse` in `src/support/cleanse.cpp`, locking and config setup in `src/util.cpp` (`CRYPTO_set_locking_callback`, `OPENSSL_no_config`, no-ops since 1.1.0), `BN_*` in `src/test/bignum.h`, and includes only in `src/init.cpp` and `src/zeronode/obfuscation.cpp`. RPC has no TLS (`-rpcssl` is refused).

Documentation:

- **Recovery guide** -- Add a recovery and maintenance section to BUILD_ZERO (`-reindex`, `-rescan`, witness rebuild, `-zapwallettxes`, transaction deletion, consolidation): when to use each and what it costs, generated in part from `doc/Reindex_Rescan.csv`.

Tests:

- **TENT test review** -- Adapt the restored fork-warning tests `hardforkdetection.py` and `forknotify.py` (Efail) to Zero's block version floor and to warnings checked without `-alertnotify`; postponed.
- **Witness rebuild coverage** -- Test witness rebuild and `CachedWitnessesCleanIndex`.

---

## Full descriptions

### getalldata cost

**Problem.** `getalldata` is the wallet client's single refresh call. Argument 1 (datatype) selects the payload: **0** addresses, balances, transactions, and chain info; **1** addresses, balances, and chain info; **2** transactions and chain info. Argument 2 is the day window (default 7 days), argument 3 the transaction count, argument 4 watch-only. Each call walks every wallet address and transaction (`mapWallet` plus the transaction archive), decrypts shielded notes, sorts history, and builds JSON; on wallets with long history that takes seconds, and clients poll every few seconds. In tree: the soft **-34** coalesce, the 7-day default window, const wallet walks, sort-key collision detection, and one parse/filter path for window, count, watch-only, and datatype (`IsGetAllDataTxTooOld`).

- **Poll cost** -- the split itself (balances on a timer, History on user action or every Nth tick) is a client change, outside this repository. The desktop wallet polls every 30 s but calls `getalldata 0 2 50 true` (datatype 0, 7-day window, 50 transactions, watch-only) only when a new block arrives; no other known client uses the RPC, and the node keeps no per-datatype statistics. Node side: measure both datatypes on a wallet with many transactions and archived entries (wall time, `getalldata` -34 rate under a fixed poll interval), then document the cadence. Complements the soft **-34** coalesce. Decides whether the tip cache is needed.
- **Tip cache** -- in-process tip and dirty cache, after poll cost. **Single walk**: merge History key insert into the balance walk. **Decrypt review**: IVK decryption cost.
- **Helpers** -- the remaining shared parse and filter helpers.
- **Address keys** -- key `addressBalances` by destination and encode once at JSON emit.

### Refusal analysis

**Now.** `AcceptToMemoryPool` refuses relayed transactions whose transparent inputs are spent (`bad-txns-inputs-spent`) or whose shielded spends reuse a nullifier or name an unknown anchor (`bad-txns-shielded-requirements-not-met`). The default log gets one count per reason, written when the first refusal arrives at least 3600 s after the previous summary, so quiet periods give longer windows and refusal-free hours give no line. `-debug=mempool` logs each refusal with txid, peer, and the nullifier or anchor. Both checks run before proof verification, and these refusals carry no misbehavior score, as in zcashd.

**Causes to tell apart.**

- Timing: a peer relays a transaction already mined, because it has not yet seen the block. The refused txid is itself in a block connected seconds to minutes earlier.
- Coincidence: two broadcasts of conflicting spends by the same owner, such as a wallet rebroadcast after a restore, a replaced transaction, or a reorg that dropped a transaction. Rare, from one or two peers, not repeated.
- Attempts: double spends aimed at a recipient that accepts unconfirmed transactions, or floods meant to cost relay bandwidth and checks. The conflicting transaction is in the mempool rather than in a block, the outputs differ, the same peer or address group repeats, or the rate rises well above the normal level of about 10 per hour.

**Signals per refusal.** Whether the refused txid is already in the chain (timing) or a different transaction spent the input (conflict); whether that transaction is in a block or in the mempool, and for how long; the peer and its address group; repeats of the same txid or input; for shielded refusals, nullifier spent in the chain against anchor unknown (a peer on another chain or not synced).

**Suggested work.** Record the class with each refusal; write the summary by class and by top peers from the scheduler at fixed hourly boundaries instead of on the next refusal; add counters to an RPC (`getmempoolinfo` or `getpeerinfo`); raise a warning through the RPC warning fields and `-alertnotify` when conflicts in the mempool from one peer or address group pass a threshold; keep the refusals non-punitive unless a peer repeats the same conflict. Test with regtest scenarios: relay of a mined transaction, a wallet double spend (`txn_doublespend.py`), and repeated conflicting relays from one peer.

### CI workflows

**Now.** GitHub Actions is enabled on `zerocurrencycoin/Zero` (public, default branch `master`).

- `master` has only `.github/workflows/Zero_Linux_CI.yml`: on push and pull request to `master` and a daily cron (`0 19 * * *`), on `runs-on: ubuntu-18.04`. GitHub has retired that runner image, so jobs wait for a runner and are cancelled.
- `zero-410` has only `.github/workflows/tests.yml`: Ubuntu 24.04, apt packages including `python3-zmq`, `fetch-params.sh`, `build.sh -j2`, then `./contrib/run-tests.sh --strict` (C++ gate and Tier A, not `--all`), timeout 240 min. Triggers: push to `main`, `master`, `develop`; pull requests; `workflow_dispatch`. Pushes to `zero-410` match no trigger, and `workflow_dispatch` needs the file on the default branch, so it has never run.

**Steps.** In order: run `tests.yml` on the release branch (add the branch to `on.push.branches`, or open the `zero-410` -> `master` pull request); after the `master` merge, `Zero_Linux_CI.yml` is gone and `tests.yml` runs on `master`; cache `depends/built` and the parameters between runs; add an `--all` job; add macOS and Windows cross-build jobs. The Large tier (`rpc-tests.sh -L`) stays out of CI.

### Test filters

To resolve after v4.1.0:

- Two parallel script lists in `qa/pull-tester/rpc-tests.sh`: the legacy `testScripts` and `testScriptsExt` arrays (87 entries, all also in a tier) and the tier arrays.
- Names differ across runners: tiers `A`, `B`, `E` with groups `gate`, `pass`, `debug`, `retired`, `fail`; `rpc-tests.sh` flags `-A`, `-B`, `-E`, `-Bfail`, `-Efail`, `-rpcfail`, `-all`; `contrib/run-tests.sh` modes `--all`, `--fail`, `--rpcfail`, `--suite`.
- C++ filter variables in `qa/zcash/test_filters.sh`: `BOOST_PASS_EXCLUDE` is passed as a `--run_test` expression, `GTEST_PASS_EXCLUDE` is a negative GTest filter, and `full_test_suite.py` calls the same value `GTEST_PASS_FILTER`.
- Helper modules (`wallet_shieldcoinbase.py`, `mergetoaddress_helper.py`, `tx_expiry_helper.py`) sit next to tests with no marking; `script_test.py`, `proton_test.py`, and `wallet_shieldcoinbase_sprout.py` are in no tier.
- `qa/rpc-tests/test_tier_inventory.csv` is regenerated by hand; nothing checks it against the runner.
- Retired Sprout scripts and the Boost/GTest exclusion mechanism: review after v4.1.0 whether to keep, rewrite, or remove.
- `contrib/run-tests.sh` has no mode for the Large tier; only `rpc-tests.sh -L` runs it.

Method: port the runner parts of Bitcoin Core `test/functional/test_runner.py` that answer these problems. `BASE_SCRIPTS` and `EXTENDED_SCRIPTS` as the one list per tier (Zero's pass tiers and Large); `NON_SCRIPTS` for helper modules; `check_script_list`, which fails when a Python file in the test directory is in no list, in place of the hand-regenerated CSV; `check_script_prefixes` for name prefixes (`wallet_`, `rpc_`, `p2p_`, `mempool_`, `feature_`); `--portseed` per job with `--jobs`, `--filter`, `--exclude`, and `--failfast`; per-script run times in the summary.

