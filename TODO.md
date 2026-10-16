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

1. **Linux build** -- Build, test, and package at the release commit on the Ubuntu 24.04 build host; with `python3-zmq` installed, the test run includes `zmq_test.py`, the only check of ZMQ notifications.
2. **Windows build** -- Cross-build and package at the release commit on the Linux build host, then start `zerod.exe` once on Windows. Windows builds have no ZMQ (item "Windows ZMQ").
3. **Release signing** -- Decide checksums and signing per platform; method in progress. Decide after the `v4.1.0-rc1` cross-platform tests, before v4.1.0; BUILD_ZERO section 2.6 then gets the signing and verify commands.
4. **Release tags** -- Tag the release candidate and the release on `zero-410`; merge into `master`.

---

## Active

- **RPC dispositions** -- Decide the Sprout RPCs and record test depth per RPC from the harness in `doc/RPCs.csv`; the accounts RPCs stay deprecated until Zerowallet lists transparent addresses with `listreceivedbyaddress`.
- **Zeronode validation** -- Pass `zeronode_coinbase.py` and `zeronode_startalias.py` at the release commit; after v4.1.0, in order: registration success path on regtest, reorg test, automated `chainActive` checks, mainnet payment scan, public operator section in BUILD_ZERO.
- **Branch cleanup** -- Decide whether to squash commits before the `master` merge; deferred. List each branch with its merge and tag status before deletion.
- **Test conversion** -- Convert the held RPC tests that assume Zcash heights or 100-block maturity, using the helpers in `test_framework/util.py`, and promote the held tests that now pass after five clean runs each. Decide after the `v4.1.0-rc1` cross-platform tests, before v4.1.0: promoting the 10 passing tests and converting `wallet_sapling` and `finalsaplingroot`; the rest after v4.1.0. Details in Full descriptions.
- **Wallet interface** -- Write the public node-wallet interface contract: RPCs and parameters Zerowallet uses, error codes and retry rules, `zero.conf` keys, data and parameter paths, and the node-wallet version table; Zerowallet links to it. Decide after the `v4.1.0-rc1` cross-platform tests, before v4.1.0.
- **Docs pilot** -- Rewrite BUILD_ZERO as the pilot of the documentation rewrite: outline by audience (quick start, operator, builder, release), facts generated from the code, a documentation lint (duplicates, links, ASCII, runnable commands), and review one section at a time. Decide after the `v4.1.0-rc1` cross-platform tests, before v4.1.0.
- **Upgrade test** -- Install v4.1.0 over existing data directories (copies of v3.3.1, v3.4.0, and v4.0.0 mainnet datadirs, with and without a wallet) and confirm it starts without an unwanted reindex or rescan, loads the wallet, accepts the existing `zero.conf`, and keeps the chain tip; on Linux, macOS, and Windows.
- **Conf samples** -- For v4.1.0: `contrib/zero.conf` lists the options an operator sets, each with its `zerod -help` (or `-help-debug`) default and one line of purpose; `contrib/conf-templates/` holds one template per main use case (`prod`, `lab`, `insight`, `zerowallet`) with its recommendations; BUILD_ZERO section 3.2 describes both once for operators, and TEST_ZERO only the test use. Details in Full descriptions.
- **Comment rules** -- Adopt the documentation and comment rules into the contributor instruction file. Postponed: retitle maintainer-document items to these titles and retire their IDs.

---

## Pending

After v4.1.0 unless noted.

### Contributor-ready

Wallet:

- **Const wallet reads** -- Continue const conversion on wallet-tx read paths.

Build:

- **Toolchain versions** -- Verify GCC, Rust, Python, and autotools versions per supported build OS, record them in BUILD_ZERO, and check them in `zcutil/check-setup.sh`.
- **macOS deployment target** -- Export `MACOSX_DEPLOYMENT_TARGET` from the build system (libtool `-bind_at_load` warning).
- **Windows hardening** -- Pass `--enable-hardening` in `build-win.sh`; needs the MXE build host.

Tests:

- **Zero RPC depth** -- Test shielded outputs and filter types for the zs_* RPCs, `getsupply` values against the emission schedule, Sapling witness RPCs, and mined-transaction History in `getalldata`.
- **Fuzz harness** -- Add libFuzzer targets under `src/fuzz/`.
- **Python cleanup** -- Adopt a format and lint check for Zero's Python files, share helpers in `contrib/stats` and `contrib/tools`, and unify script names and headers; postponed.
- **Test filters** -- Unify test tiers, filters, and their names across the runners; details in Full descriptions.

### Maintainer

RPC:

- **getalldata cost** -- Measure poll cost on a large wallet first, then the steps in Full descriptions.
- **RPC removal** -- Remove the code of RPCs that leave Zero, starting with the compiled-out Sprout raw JoinSplit RPCs; postponed; follows RPC dispositions.

Node operation:

- **Reindex safeguards** -- Refuse a `reindex=` line in `zero.conf` and an unforced `DB_FLAG` mismatch unless `-reindexforce`; skip the wallet replay below a height.
- **Tor compile-out** -- Add a `--disable-tor` configure option that compiles out Tor control; runtime onion is already off by default; keep it separate from I2P.
- **Address rate limit** -- Port the per-peer `addr` rate limit with its `getpeerinfo` counters from zcashd, as Pirate did, and add an RPC test; feelers and test-before-evict follow from Bitcoin Core.
- **Refusal analysis** -- Classify transactions refused from peers as timing, coincidence, or attempts, and alert on attempts; postponed. Details in Full descriptions.
- **Conf checks** -- Check automatically that every key in `contrib/zero.conf` and `contrib/conf-templates/` is a parsed option and that shown defaults match `zerod -help` and `-help-debug`; add a default column to `doc/Options.csv` generated from the help text; run the check in `contrib/run-tests.sh` and `zcutil/check-release.sh`.
- **Conf templates test** -- Start `zerod` in a lab datadir with each generated template and stop it cleanly, then exercise each template's use case; automate in `contrib/ops-validate.sh`.
- **Lab datadir setup** -- Review and harmonize how test scenarios set up datadirs and configuration (`contrib/ops-validate.sh` labs and templates, the RPC test cache, height-bounded labs), and complete their documentation in TEST_ZERO; performance measurement stays out of scope.
- **Peer monitoring** -- Evaluate the monitoring examples and code of Bitcoin Core (tracepoints, message capture, log rate limit, `logging` RPC), zcashd (`setlogfilter`), and bmon first. Report connections and peer interactions for monitoring: counts by direction, connect, disconnect, and ban events with reasons, per-peer message and byte counters, and address-manager health, through RPC and a periodic summary line; per-event lines stay under `-debug=net`. Keep the `receive version message` line and `-logips` as they are.

Build, packaging, and release:

- **Params mirror** -- Make a Zero-controlled copy of the three parameter files the primary source of `fetch-params.sh` (the Cloudflare store that serves the chain archive, with GitHub release assets as a second copy), keeping zcashd's host and IPFS as fallbacks; verify file names and checksums.
- **Chain bootstrap** -- Document the end-user import path (`-loadblock`, auto-import), snapshot sourcing, and verification; linearize in `contrib/linearize/`.
- **Peer discovery** -- Review and improve how a new node finds peers: the DNS seed names in `vSeeds` (`src/chainparams.cpp`) and their records, a crawling seeder that publishes only live nodes, and the fixed-seed fallback (`contrib/seeds`, `chainparamsseeds.h`) filled from long-running nodes and refreshed each release.
- **CI workflows** -- Run the CI workflow on the release branch, run the full test set, and add macOS and Windows cross-build jobs; postponed.
- **Contrib cleanup** -- Remove the inherited tools Zero does not use (`contrib/macdeploy`, `tidy_datadir.sh`, `verifysfbinaries`, `test-patches`, `spendfrom`, `verify-commits`, `qos`, `bitrpc`) and their `contrib/README.md` entries; replace `contrib/init/` with one `zerod.service`; rename the bash completions to Zero's binaries and install them from the `.deb`.
- **Base58 vectors** -- Port zcashd's two-byte address prefixes to `contrib/testgen/gen_base58_test_vectors.py`, regenerate `src/test/data/base58_keys_*.json` with it, and confirm `base58_tests` against Zero's prefixes; postponed.
- **AMQP removal** -- Remove AMQP (`src/amqp/`, Qpid Proton in `depends`, `contrib/amqp/`, `proton_test.py`, `--enable-proton`) as zcashd did in 2020; ZMQ remains the notification path.
- **Windows ZMQ** -- Review enabling ZMQ in Windows builds (`build-win.sh` passes `--disable-zmq`): features needed, implementation, and tests.
- **Linux package** -- Add man pages, the example `zero.conf`, and bash completions to the `.deb` from `zcutil/release-linux.sh`, and the example `zero.conf` to the macOS and Windows archives.
- **Zerowallet conf** -- Align the `zero.conf` that Zerowallet writes (`rpcworkqueue`, `txindex`, `keeptx*`, `safekey`, macOS directory) with the node, coordinated with the Zerowallet release; under consideration.
- **LevelDB update** -- Update `src/leveldb` to LevelDB 1.22 as in Bitcoin Core and zcashd; restores block-cache usage in `getdbinfo`. Set 32 MiB table files (`max_file_size`, as Bitcoin Core and zcashd `DBWRAPPER_MAX_FILE_SIZE`) so the block index and chain state fit the table cache.

Documentation:

- **Setup runbook** -- Write the operator runbook in BUILD_ZERO: build, `fetch-params`, `zero.conf` RPC credentials, launch, ports.
- **Recovery guide** -- Add a recovery and maintenance section to the runbook (`-reindex`, `-rescan`, witness rebuild, `-zapwallettxes`, transaction deletion, consolidation): when to use each and what it costs, generated in part from `doc/Reindex_Rescan.csv`.

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

### Conf samples

**Authority.** CONTRIBUTING "Options and defaults": the code is the only source of options and defaults; help text, man pages, `doc/Options.csv`, and the samples derive from it or are checked against it.

**For v4.1.0.** The example `contrib/zero.conf` is checked against `zerod -help`: of its 48 keys, three are `-help-debug` options (`rpcworkqueue`, `rpcservertimeout`, `rpcasyncthreads`) and the rest match the help text; `rpcbind=127.0.0.1` is a recommendation, not the default. Each template in `contrib/conf-templates/` is one use case: `prod` (wallet node, the default), `lab` (isolated test runs), `insight` (explorer backend), `zerowallet` (mirror of the file Zerowallet writes, for attach tests). BUILD_ZERO section 3.2 is the operator documentation; TEST_ZERO covers only the test templates.

**After v4.1.0.** Automated key and default checks (item "Conf checks"), a start-and-stop test per template (item "Conf templates test"), and lab setup review (item "Lab datadir setup"). Zerowallet's generated file is the wallet's to change; its fields are tracked with the Zerowallet integration items, not here.

### Test conversion

Held tests and their Zcash assumption (2026-10-14 run on macOS):

- `getblockcount() == 200` against the 725-block cache: `wallet_sapling`, `wallet_listnotes`, `wallet_addresses`, `rescan_import`; `wallet_listreceived` (height check).
- Clean chain mined below the 720-block maturity: `wallet_persistence`, `wallet_changeaddresses`, `finalsaplingroot`.
- `generate(101)` / `(100)` / `(99)`: `shorter_block_times`, `reorg_limit`, `bip65-cltv-p2p`, `bipdersig-p2p`, `invalidblockrequest`.
- Passing in a single run, to promote after five clean runs each: `rawtransactions`, `fundrawtransaction`, `signrawtransaction_offline`, `regtest_signrawtransaction`, `mergetoaddress_sapling`, `mergetoaddress_mixednotes`, `wallet_shieldcoinbase_sapling`, `wallet_protectcoinbase`, `zkey_import_export`, `key_import_export`.

Methods: heights relative to `CACHE_TIP` or the current tip, never 101 or 200; `COINBASE_MATURITY`, `mine_until_mature`, `ensure_coinbase_utxos`, and `get_coinbase_address` for spendable coinbase; `block_subsidy`, `miner_share`, `founders_share` with `REGTEST_HALVING` for amounts; upgrade activation placed relative to `COINBASE_MATURITY`; heights in raw transactions as 4-byte little-endian.

### Test filters

Problems found 2026-10-15, all to resolve after v4.1.0 except `zmq_test` (see "Linux build"):

- Two parallel script lists in `qa/pull-tester/rpc-tests.sh`: the legacy `testScripts` and `testScriptsExt` arrays (87 entries, all also in a tier) and the tier arrays. The ZMQ and Proton conditions add their scripts only to the legacy arrays, so `-all` never runs `zmq_test.py`.
- Names differ across runners: tiers `A`, `B`, `E` with groups `gate`, `pass`, `debug`, `retired`, `fail`; `rpc-tests.sh` flags `-A`, `-B`, `-E`, `-Bfail`, `-Efail`, `-rpcfail`, `-all`; `contrib/run-tests.sh` modes `--all`, `--fail`, `--rpcfail`, `--suite`.
- C++ filter variables in `qa/zcash/test_filters.sh`: `BOOST_PASS_EXCLUDE` is passed as a `--run_test` expression, `GTEST_PASS_EXCLUDE` is a negative GTest filter, and `full_test_suite.py` calls the same value `GTEST_PASS_FILTER`.
- Helper modules (`wallet_shieldcoinbase.py`, `mergetoaddress_helper.py`, `tx_expiry_helper.py`) sit next to tests with no marking; `script_test.py`, `proton_test.py`, and `wallet_shieldcoinbase_sprout.py` are in no tier.
- `qa/rpc-tests/test_tier_inventory.csv` is regenerated by hand; nothing checks it against the runner.
- Retired Sprout scripts and the Boost/GTest exclusion mechanism: review after v4.1.0 whether to keep, rewrite, or remove.

