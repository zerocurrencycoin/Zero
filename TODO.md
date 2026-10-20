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
- **Docs pilot** -- BUILD_ZERO, TEST_ZERO, ZERO_COIN, and README are rewritten; next a documentation lint (duplicates, links, ASCII, runnable commands) and facts generated from the code.
- **Comment rules** -- Adopt the documentation and comment rules into the contributor instruction file. Postponed: retitle maintainer-document items to these titles and retire their IDs.

---

## Pending

After v4.1.0 unless noted.

### Contributor-ready

Wallet:

- **Const wallet reads** -- Continue const conversion on wallet-tx read paths.

Build:

- **Toolchain versions** -- Verify GCC, Rust, Python, and autotools versions per supported build OS, record them in BUILD_ZERO "Requirements", and check them in `zcutil/check-setup.sh`. Rust: Linux builds use the pinned 1.32.0 unless `RUST_USE_SYSTEM=1`, macOS the system Rust; decide the Linux default and the minimum Rust for `librustzcash`.
- **Windows hardening** -- Pass `--enable-hardening` in `build-win.sh`; needs the MXE build host.

Tests:

- **Zero RPC depth** -- Test shielded outputs and filter types for the zs_* RPCs, `getsupply` values against the emission schedule (its help says "coin supply"; it returns the scheduled mint, not the measured supply), Sapling witness RPCs, and mined-transaction History in `getalldata`.
- **Fuzz harness** -- Add libFuzzer targets under `src/fuzz/`.
- **Python cleanup** -- Adopt a format and lint check for Zero's Python files, share helpers in `contrib/stats` and `contrib/tools`, and unify script names and headers; postponed.
- **Log microseconds** -- Port `-logtimemicros` from Bitcoin Core: read it in `init.cpp`, list it in `-help-debug`, and append the microseconds of `GetTimeMicros` in `LogTimestampStr` (`src/util.cpp`); only the unused flag `fLogTimeMicros` exists; postponed.
- **Test filters** -- Unify test tiers, filters, and their names across the runners.
- **Test conversion** -- Convert the held scripts of TEST_ZERO "Held scripts" except the Obsolete, Retired Sprout, and GTest rows, and promote each after five clean serial runs: the scripts of the height and maturity rows with the helpers in TEST_ZERO "Writing tests for Zero"; the Python-solved-block scripts by solving with the `ZERO_PoW` personalization in `test_framework/equihash.py`; then `getblocktemplate_proposals`, `smartfees`, `hardforkdetection`, and `forknotify`. Postponed.

### Maintainer

Zeronodes:

- **Zeronode legacy** -- Review doc/zeronodes.md; postponed.

RPC:

- **getalldata cost** -- Measure poll cost on a large wallet first, then the follow-up steps.
- **RPC removal** -- Remove the code of RPCs that leave Zero, starting with the compiled-out Sprout raw JoinSplit RPCs; postponed; follows RPC dispositions.

Node operation:

- **Reindex safeguards** -- Refuse a `reindex=` line in `zero.conf` and an unforced `DB_FLAG` mismatch unless `-reindexforce`; skip the wallet replay below a height.
- **Tor compile-out** -- Add a `--disable-tor` configure option that compiles out Tor control; runtime onion is already off by default; keep it separate from I2P.
- **Address rate limit** -- Port the per-peer `addr` rate limit with its `getpeerinfo` counters from zcashd, as Pirate did, and add an RPC test; feelers and test-before-evict follow from Bitcoin Core; postponed.
- **Refusal analysis** -- Classify transactions refused from peers as timing, coincidence, or attempts, and alert on attempts; postponed.
- **Conf checks** -- Check automatically that every key in `contrib/zero.conf` and `contrib/conf-templates/` is a parsed option and that shown defaults match `zerod -help` and `-help-debug`; add a default column to `doc/Options.csv` generated from the help text; run the check in `contrib/run-tests.sh` and `zcutil/check-release.sh`. `contrib/tools/inventory-check.py` counts commented-out `GetArg` calls as parsed options, so it missed `prune` and `txindex`; parse only live code.
- **Conf templates test** -- Start `zerod` in a lab datadir with each generated template and stop it cleanly, then exercise each template's use case; automate in `contrib/ops-validate.sh`.
- **Lab datadir setup** -- Review and harmonize how test scenarios set up datadirs and configuration (`contrib/ops-validate.sh` labs and templates, the RPC test cache, height-bounded labs), and complete their documentation in TEST_ZERO; performance measurement stays out of scope.
- **Peer monitoring** -- Evaluate the monitoring examples and code of Bitcoin Core (tracepoints, message capture, log rate limit, `logging` RPC), zcashd (`setlogfilter`), and bmon first. Report connections and peer interactions for monitoring: counts by direction, connect, disconnect, and ban events with reasons, per-peer message and byte counters, and address-manager health, through RPC and a periodic summary line; per-event lines stay under `-debug=net`. Keep the `receive version message` line and `-logips` as they are.
- **Coinbase tag** -- Add a `-coinbasetag=<text>` option that the internal miner and the `coinbasetxn` template append after the height (`COINBASE_FLAGS`, `CreateNewBlock` in `src/miner.cpp`), within the 100-byte coinbase input limit, so solo miners and pools that use the template are identifiable; pool outreach in doc/mining-pools.md "Asks".
- **Chain diagnostics** -- Port the diagnostic and recovery tools that Zero lacks, and extend the coinbase audit in `contrib/stats/chain-audit/`; postponed.
- **Mining follow-up** -- Continue the pool review of doc/mining-pools.md: pool identities, the s-nomp recipient fix, and the concerns listed there; postponed.
- **Network assessment** -- Measure block and transaction propagation, peers, address groups, and forks from the project's nodes after time sync; postponed.
- **Difficulty review** -- Model Digishield with Zero's parameters against the measured on-off hashrate and compare the alternatives; postponed.
- **Fee policy** -- Decide on a conventional fee (ZIP 317), on admitting zero-fee and never-expiring transactions (free relay, priority area, a mempool age limit), and on the ZIP 401 eviction constants, which zcashd raised with ZIP 317. Coin age justifies a wait of hours to days, not an unbounded stay: candidates are a mempool age limit (`-mempoolexpiry`, Bitcoin Core), a relay-policy expiry for expiry-0 transactions, or refusing them at relay. The `-limitfreerelay` default of 30 in `AcceptableInputs` never runs: both callers in `src/zeronode/zeronode.cpp` pass `fLimitFree` false. Decide against the current traffic in doc/mining-pools.md "Transactions"; postponed.
- **Block relay** -- Port `sendheaders` (BIP 130), and set up relay nodes for pools, per doc/mining-pools.md "Relay"; postponed.

Build, packaging, and release:

- **Params mirror** -- Make a Zero-controlled copy of the three parameter files the primary source of `fetch-params.sh` (the Cloudflare store that serves the chain archive, with GitHub release assets as a second copy), keeping zcashd's host and IPFS as fallbacks; verify file names and checksums.
- **Chain bootstrap** -- Document the end-user import path (`-loadblock`, auto-import), snapshot sourcing, and verification; linearize in `contrib/linearize/`.
- **Peer discovery** -- Review and improve how a new node finds peers: the DNS seed names in `vSeeds` (`src/chainparams.cpp`) and their records, a crawling seeder that publishes only live nodes, and the fixed-seed fallback (`src/chainparamsseeds.h`, whose mainnet and testnet arrays are empty; `contrib/seeds/nodes_main.txt` lists two AWS addresses, `35.164.216.74` and `35.165.120.254`, that were never compiled in; `contrib/seeds/README.md` still describes Bitcoin Core 0.10 seeds from `bitcoin.sipa.be`) filled from long-running nodes and refreshed each release.
- **CI workflows** -- Replace the `master` workflow with `.github/workflows/tests.yml` and extend it; postponed.
- **Contrib cleanup** -- Remove the inherited tools Zero does not use (`contrib/macdeploy`, `tidy_datadir.sh`, `verifysfbinaries`, `test-patches`, `spendfrom`, `verify-commits`, `qos`, `bitrpc`, and in `contrib/devtools` `github-merge.sh`, `fix-copyright-headers.py`, `optimize-pngs.py`) and their `contrib/README.md` entries; replace `contrib/init/` with one `zerod.service`; rename the bash completions to Zero's binaries and install them from the `.deb`.
- **Base58 vectors** -- Port zcashd's two-byte address prefixes to `contrib/testgen/gen_base58_test_vectors.py`, regenerate `src/test/data/base58_keys_*.json` with it, and confirm `base58_tests` against Zero's prefixes; postponed.
- **AMQP removal** -- Remove AMQP (`src/amqp/`, the Proton recipe in `depends`, `contrib/amqp/`, `proton_test.py`, `--enable-proton`), as zcashd did; ZMQ remains the notification path.
- **Windows ZMQ** -- Review enabling ZMQ in Windows builds (`build-win.sh` passes `--disable-zmq`): features needed, implementation, and tests.
- **Linux package** -- Add man pages, the example `zero.conf`, and bash completions to the `.deb` from `zcutil/release-linux.sh`, and the example `zero.conf` to the macOS and Windows archives.
- **Zerowallet conf** -- Align the `zero.conf` that Zerowallet writes (`rpcworkqueue`, `txindex`, `keeptx*`, `safekey`, macOS directory) with the node, coordinated with the Zerowallet release; under consideration.
- **LevelDB update** -- Update `src/leveldb` to LevelDB 1.22 as in Bitcoin Core and zcashd; restores block-cache usage in `getdbinfo`. Set 32 MiB table files (`max_file_size`, as Bitcoin Core and zcashd `DBWRAPPER_MAX_FILE_SIZE`) so the block index and chain state fit the table cache.
- **OpenSSL 3** -- Long-term preference: move from OpenSSL 1.1.1w to 3.x, or remove OpenSSL as Bitcoin Core did; not scheduled. Call sites: wallet encryption in `src/wallet/crypter.cpp` (`EVP_BytesToKey`, AES-256-CBC through `EVP_*`), `OPENSSL_cleanse` in `src/support/cleanse.cpp`, locking and config setup in `src/util.cpp` (`CRYPTO_set_locking_callback`, `OPENSSL_no_config`, no-ops since 1.1.0), `BN_*` in `src/test/bignum.h`, and includes only in `src/init.cpp` and `src/zeronode/obfuscation.cpp`. RPC has no TLS (`-rpcssl` is refused).

Documentation:

- **Recovery guide** -- Add a recovery and maintenance section to BUILD_ZERO (`-reindex`, `-rescan`, witness rebuild, `-zapwallettxes`, transaction deletion, consolidation): when to use each and what it costs, generated in part from `doc/Reindex_Rescan.csv`.
- **README claims** -- Back the README feature headings (fast and zero-cost transactions, ASIC resistance, unique algorithm) with facts and sources, or reword them; kept as branding for now.

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

**Steps.** In order: run `tests.yml` on the release branch (add the branch to `on.push.branches`, or open the `zero-410` -> `master` pull request); after the `master` merge, `Zero_Linux_CI.yml` is gone and `tests.yml` runs on `master`; cache `depends/built` and the parameters between runs; add an `--all` job; add build and gate jobs on the hosted `ubuntu-22.04` runner and in an `ubuntu:20.04` container (`container:` in the job; hosted Ubuntu 20.04 runners are retired; `actions/checkout` needs glibc 2.28, so an `ubuntu:18.04` container cannot run it); add macOS and Windows cross-build jobs. The Large tier (`rpc-tests.sh -L`) stays out of CI.

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


### Mining follow-up

- **Identities.** Ask the smaller pools listed for Zero (pooly.ca, rockpool.cloud, Kryptex) for their payout addresses or block heights; match `t1SJJ...`, `t1e6n...`, `t1fbD...`, `t1NrRj...`, `t1PmYq...`.
- **s-nomp.** Propose the patch of doc/s-nomp-recipients.md "Fix" to `node-stratum-pool` and an address placeholder for the s-nomp example configurations; send the note to pool operators on Zero; check other s-nomp coins for coinbases short by exact recipient percentages.
- **Listings.** Ask WhatToMine to reactivate ZER (EquihashZero, reported inactive) and miningboard.com to correct its 1 ZER reward and 60 s block time.
- **Clock.** Ask the `t1SJJ...` operator to run NTP; re-measure.
- **Withholding test.** Decide between slow relay and withheld blocks for batched branches with the multi-node arrival data of item "Network assessment".

### Network assessment

Nodes: two VPS (laz24, tor) with inbound P2P, and a laptop behind a NAT cable modem (outbound only). Node-side counters come from item "Peer monitoring"; this item measures from outside with the nodes as probes.

1. **Time.** Every node on NTP (BUILD_ZERO "Clock"), offset recorded with each run; sub-second log times need item "Log microseconds".
2. **Logging.** `-debug=net -logips` on each node: "received block <hash> peer=<id>" and the peer's address give the first relayer of every block.
3. **Propagation.** Per block and node, first arrival minus block time, and the spread between nodes; per pool, the first-relaying peers, which locate pool nodes; batched arrivals seen at all nodes point to the pool, at one node to its path.
4. **Peers.** Periodic `getpeerinfo` per node (version, subversion, ping, start height, direction, `timeoffset`); a P2P crawler (version handshake, `getaddr`) for the reachable network, its size, versions, and address spread; DNS seed answers and liveness.
5. **Address groups.** Group peers, zeronodes (`zeronode list`), seed lists, and first relayers by IPv4 /16 and /24, IPv6 /32 and /48, and AS (RIR whois, not radb); overlaps between the sets locate farms and pool nodes. A sample on 2026-10-19: 57 zeronodes, 16 IPv4 and 41 IPv6, each with its own payout address; 18 in one Contabo US /48, 10 in one Superloop AU /48, 11 in two Contabo DE /32s; 27 of them among tor's peers, 51 in `seeds.txt`; one residential IPv4 address held 14 inbound connections to tor: separate synced nodes (4.0.0 and 3.3.1, different connect times) behind one NAT, scored +34 by the per-address zeronode list request limit (`dseg`) and +10 for relaying expired transactions, never banned.
6. **Forks.** `getchaintips` on every node; stale blocks seen by one node only show slow paths.
7. **Mempool.** `getrawmempool` on every node at each new block (`-zmqpubhashblock`): mempool contents when an empty block arrives (empty template or empty mempool), transaction propagation between nodes, free and never-expiring transactions held.
8. **Output.** Per-node TSV files and reports in `contrib/stats/chain-audit/`.

### Difficulty review

**Now.** Parameters: ZERO_COIN "Chain". Since height 2,400,000 the mean interval is 113.2 s against the 120 s target, the median 49 s, the standard deviation 185 s (equal to the mean under constant hashrate), 42% of intervals under 30 s, 2.2% over 600 s, the longest 7,143 s; the 17-block mean interval spans 8 s to 238 s between the 5th and 95th percentiles. This is on-off hashrate: profit-switching pools mine while the difficulty lags, then leave (doc/mining-pools.md "Empty blocks and timing"). With a 17-block window, dampening by 4, and the median-time-past delay, the difficulty follows such a change over tens of blocks.

**Steps.**

1. **Data.** Add a header scan to `contrib/stats/chain-audit/scan.py` (height, time, `bits`, pool) and report per burst: difficulty before, during, and after, interval, and hashrate implied by difficulty over interval.
2. **Model.** Write a simulator in `contrib/stats/chain-audit/` after zawy12's `test_DAs.cpp` (`difficulty-algorithms`, with its on-off mining model: hashrate on below one difficulty, off above another): Zero's Digishield with the 90-130% bounds that `test_DAs.cpp` leaves out, LWMA (TENT, fluxd), and ASERT (Bitcoin Cash); drive it with the measured pattern: baseline hashrate, switch-on multiple, and the difficulties at which bursts start and stop.
3. **Validate.** Recompute `bits` for a chain segment from the scanned headers with the model's Digishield and match the chain exactly before comparing algorithms.
4. **Compare.** Per algorithm: mean interval, share of blocks mined by switching hashrate at low difficulty, longest interval after a switch-off, response to timestamp manipulation (zawy12's timespan and bad-timestamp tests).
5. **Decide.** A change is a hard fork: a network upgrade with an activation height, test vectors, and pool and exchange notice; or keep Digishield with recorded reasons.

### Test filters

To resolve after v4.1.0:

- Two parallel script lists in `qa/pull-tester/rpc-tests.sh`: the legacy `testScripts` and `testScriptsExt` arrays (all also in a tier) and the tier arrays.
- Names differ across runners: tiers `A`, `B`, `E` with groups `gate`, `pass`, `debug`, `retired`, `fail`; `rpc-tests.sh` flags `-A`, `-B`, `-E`, `-Bfail`, `-Efail`, `-rpcfail`, `-all`; `contrib/run-tests.sh` modes `--all`, `--fail`, `--rpcfail`, `--suite`.
- C++ filter variables in `qa/zcash/test_filters.sh`: `BOOST_PASS_EXCLUDE` is passed as a `--run_test` expression, `GTEST_PASS_EXCLUDE` is a negative GTest filter, and `full_test_suite.py` calls the same value `GTEST_PASS_FILTER`.
- Helper modules (`wallet_shieldcoinbase.py`, `mergetoaddress_helper.py`, `tx_expiry_helper.py`) sit next to tests with no marking; `script_test.py`, `proton_test.py`, and `wallet_shieldcoinbase_sprout.py` are in no tier.
- `qa/rpc-tests/test_tier_inventory.csv` is regenerated by hand; nothing checks it against the runner.
- Retired Sprout scripts and the Boost/GTest exclusion mechanism: review after v4.1.0 whether to keep, rewrite, or remove.
- `contrib/run-tests.sh` has no mode for the Large tier; only `rpc-tests.sh -L` runs it.

Method: port the runner parts of Bitcoin Core `test/functional/test_runner.py` that answer these problems. `BASE_SCRIPTS` and `EXTENDED_SCRIPTS` as the one list per tier (Zero's pass tiers and Large); `NON_SCRIPTS` for helper modules; `check_script_list`, which fails when a Python file in the test directory is in no list, in place of the hand-regenerated CSV; `check_script_prefixes` for name prefixes (`wallet_`, `rpc_`, `p2p_`, `mempool_`, `feature_`); `--portseed` per job with `--jobs`, `--filter`, `--exclude`, and `--failfast`; per-script run times in the summary.

