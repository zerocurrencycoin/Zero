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
- **Conf checks** -- Check automatically that every key in `contrib/zero.conf` and `contrib/conf-templates/` is a parsed option and that shown defaults match `zerod -help` and `-help-debug`; add a default column to `doc/Options.csv` generated from the help text; run the check in `contrib/run-tests.sh` and `zcutil/check-release.sh`. `contrib/tools/inventory-check.py` counts commented-out `GetArg` calls as parsed options, so it missed `prune` and `txindex`; parse only live code.
- **Conf templates test** -- Start `zerod` in a lab datadir with each generated template and stop it cleanly, then exercise each template's use case; automate in `contrib/ops-validate.sh`.
- **Lab datadir setup** -- Review and harmonize how test scenarios set up datadirs and configuration (`contrib/ops-validate.sh` labs and templates, the RPC test cache, height-bounded labs), and complete their documentation in TEST_ZERO; performance measurement stays out of scope.
- **Chain diagnostics** -- Port the diagnostic and recovery tools that Zero lacks, and extend the coinbase audit in `contrib/stats/chain-audit/`; postponed.

Network and P2P (Full description "Network and P2P"):

- **Peer discovery** -- Review and improve how a new node finds peers: the DNS seed names in `vSeeds` (`src/chainparams.cpp`) and their records, a crawling seeder that publishes only live nodes, and the fixed-seed fallback (`src/chainparamsseeds.h`, whose mainnet and testnet arrays are empty; `contrib/seeds/nodes_main.txt` lists two AWS addresses, `35.164.216.74` and `35.165.120.254`, that were never compiled in; `contrib/seeds/README.md` still describes Bitcoin Core 0.10 seeds from `bitcoin.sipa.be`) filled from long-running nodes and refreshed each release.
- **Peer defenses** -- Port the per-peer `addr` rate limit with its `getpeerinfo` counters from zcashd, as Pirate did, then the further defenses in the order of the Full description; postponed.
- **Tor compile-out** -- Add a `--disable-tor` configure option that compiles out Tor control; runtime onion is already off by default; keep it separate from I2P.
- **Block relay** -- Port `sendheaders` (BIP 130), which no Zcash-family node has, and set up relay nodes for pools, per doc/mining/mining-pools.md "Relay"; postponed.

Consensus (Full description "Consensus"):

- **Time adjustment** -- Stop adjusting the clock by the peer median (zcashd v2.1.1-1 and v2.1.2), keep the offset as a warning, and review the timestamp rules against timewarp; postponed.
- **Difficulty review** -- Model Digishield with Zero's parameters against on-off hashrate and compare the alternatives; postponed.
- **Reorg defenses** -- Publish confirmation guidance and add a checkpoint in each release, then decide on a consensus defense, per the Full description; not scheduled.

Mempool and fees:

- **Fee policy** -- Decide on a conventional fee (ZIP 317) with the matching ZIP 401 constants, on free relay and coin-age priority, and on how long zero-fee and never-expiring transactions may stay, against the traffic in doc/mining/mining-pools.md "Transactions"; postponed.
- **Refusal analysis** -- Classify transactions refused from peers as timing, coincidence, or attempts; postponed.

Monitoring:

- **Peer monitoring** -- Evaluate the monitoring examples and code of Bitcoin Core (tracepoints, message capture, log rate limit, `logging` RPC), zcashd (`setlogfilter`), and bmon first. Report connections and peer interactions for monitoring: counts by direction, connect, disconnect, and ban events with reasons, per-peer message and byte counters, and address-manager health, through RPC and a periodic summary line; per-event lines stay under `-debug=net`. Keep the `receive version message` line and `-logips` as they are.
- **Network assessment** -- Measure block and transaction propagation, peers, address groups, and forks from the project's nodes after time sync; postponed.

Mining:

- **Coinbase tag** -- Add a `-coinbasetag=<text>` option that the internal miner and the `coinbasetxn` template append after the height (`COINBASE_FLAGS`, `CreateNewBlock` in `src/miner.cpp`), within the 100-byte coinbase input limit, so solo miners and pools that use the template are identifiable; pool outreach in doc/mining/mining-pools.md "Asks".
- **Mining follow-up** -- After the pool review is reviewed and confirmed: pool identities, the s-nomp recipient fix, and listings; postponed.
- **Chain-audit tools** -- Merge the scratch analyses of the pool review into `contrib/stats/chain-audit/` and validate them, per the Full description; postponed.

Build, packaging, and release:

- **Params mirror** -- Make a Zero-controlled copy of the three parameter files the primary source of `fetch-params.sh` (the Cloudflare store that serves the chain archive, with GitHub release assets as a second copy), keeping zcashd's host and IPFS as fallbacks; verify file names and checksums.
- **Chain bootstrap** -- Document the end-user import path (`-loadblock`, auto-import), snapshot sourcing, and verification; linearize in `contrib/linearize/`.
- **CI workflows** -- Replace the `master` workflow with `.github/workflows/tests.yml` and extend it; postponed.
- **Contrib cleanup** -- Remove the inherited tools Zero does not use (`contrib/macdeploy`, `tidy_datadir.sh`, `verifysfbinaries`, `test-patches`, `spendfrom`, `verify-commits`, `qos`, `bitrpc`, and in `contrib/devtools` `github-merge.sh`, `fix-copyright-headers.py`, `optimize-pngs.py`) and their `contrib/README.md` entries; replace `contrib/init/` with one `zerod.service`; rename the bash completions to Zero's binaries and install them from the `.deb`.
- **Base58 vectors** -- Port zcashd's two-byte address prefixes to `contrib/testgen/gen_base58_test_vectors.py`, regenerate `src/test/data/base58_keys_*.json` with it, and confirm `base58_tests` against Zero's prefixes; postponed.
- **AMQP removal** -- Remove AMQP (`src/amqp/`, the Proton recipe in `depends`, `contrib/amqp/`, `proton_test.py`, `--enable-proton`), as zcashd did; ZMQ remains the notification path.
- **Windows ZMQ** -- Review enabling ZMQ in Windows builds (`build-win.sh` passes `--disable-zmq`): features needed, implementation, and tests.
- **Linux package** -- Add man pages, the example `zero.conf`, and bash completions to the `.deb` from `zcutil/release-linux.sh`, and the example `zero.conf` to the macOS and Windows archives.
- **Zerowallet conf** -- Align the `zero.conf` that Zerowallet writes (`rpcworkqueue`, `txindex`, `keeptx*`, `safekey`, macOS directory) with the node, coordinated with the Zerowallet release; under consideration.

Long-term, not scheduled:

- **LevelDB update** -- Update `src/leveldb` to LevelDB 1.22 as in Bitcoin Core and zcashd; restores block-cache usage in `getdbinfo`. Set 32 MiB table files (`max_file_size`, as Bitcoin Core and zcashd `DBWRAPPER_MAX_FILE_SIZE`) so the block index and chain state fit the table cache.
- **OpenSSL 3** -- Preference: move from OpenSSL 1.1.1w to 3.x, or remove OpenSSL as Bitcoin Core did; not scheduled. Call sites: wallet encryption in `src/wallet/crypter.cpp` (`EVP_BytesToKey`, AES-256-CBC through `EVP_*`), `OPENSSL_cleanse` in `src/support/cleanse.cpp`, locking and config setup in `src/util.cpp` (`CRYPTO_set_locking_callback`, `OPENSSL_no_config`, no-ops since 1.1.0), `BN_*` in `src/test/bignum.h`, and includes only in `src/init.cpp` and `src/zeronode/obfuscation.cpp`. RPC has no TLS (`-rpcssl` is refused).

Documentation:

- **Recovery guide** -- Add a recovery and maintenance section to BUILD_ZERO (`-reindex`, `-rescan`, witness rebuild, `-zapwallettxes`, transaction deletion, consolidation): when to use each and what it costs, generated in part from `doc/Reindex_Rescan.csv`.
- **Docs split** -- Keep in the public tree the pool guidance (coinbase rules, identification, generic asks, relay, transaction policy, aggregate timing, method, the s-nomp note); move per-address tables, identity guesses, per-operator asks, per-pool forks and arrival, the address CSVs, peer and zeronode address data, and dated statistics to a location outside git, regenerated by `contrib/stats/chain-audit/`; postponed.
- **README claims** -- Back the README feature headings (fast and zero-cost transactions, ASIC resistance, unique algorithm) with facts and sources, or reword them; kept as branding for now.

Tests:

- **TENT test review** -- Adapt the restored fork-warning tests `hardforkdetection.py` and `forknotify.py` (Efail) to Zero's block version floor and to warnings checked without `-alertnotify`; postponed.
- **Witness rebuild coverage** -- Test witness rebuild and `CachedWitnessesCleanIndex`.

---

## Full descriptions

Grouped by area. Each area opens with the state of the code and the decisions that span its items; the items follow.

### getalldata cost

**Problem.** `getalldata` is the wallet client's single refresh call. Argument 1 (datatype) selects the payload: **0** addresses, balances, transactions, and chain info; **1** addresses, balances, and chain info; **2** transactions and chain info. Argument 2 is the day window (default 7 days), argument 3 the transaction count, argument 4 watch-only. Each call walks every wallet address and transaction (`mapWallet` plus the transaction archive), decrypts shielded notes, sorts history, and builds JSON; on wallets with long history that takes seconds, and clients poll every few seconds. In tree: the soft **-34** coalesce, the 7-day default window, const wallet walks, sort-key collision detection, and one parse/filter path for window, count, watch-only, and datatype (`IsGetAllDataTxTooOld`).

- **Poll cost** -- the split itself (balances on a timer, History on user action or every Nth tick) is a client change, outside this repository. The desktop wallet polls every 30 s but calls `getalldata 0 2 50 true` (datatype 0, 7-day window, 50 transactions, watch-only) only when a new block arrives; no other known client uses the RPC, and the node keeps no per-datatype statistics. Node side: measure both datatypes on a wallet with many transactions and archived entries (wall time, `getalldata` -34 rate under a fixed poll interval), then document the cadence. Complements the soft **-34** coalesce. Decides whether the tip cache is needed.
- **Tip cache** -- in-process tip and dirty cache, after poll cost. **Single walk**: merge History key insert into the balance walk. **Decrypt review**: IVK decryption cost.
- **Helpers** -- the remaining shared parse and filter helpers.
- **Address keys** -- key `addressBalances` by destination and encode once at JSON emit.

### Network and P2P

**State.** Zero runs the peer code of Bitcoin Core 0.12 on the zcashd base: one outbound connection per IPv4 /16 or IPv6 /32, inbound eviction that protects diverse peers, and address-manager bucketing by source group. Misbehavior is scored per connection, except the zeronode list request (`dseg`), which is limited per IP. It has none of Bitcoin Core's later defenses (the `addr` rate limit, feelers, test-before-evict, block-relay-only connections, anchors, AS-based groups) and no `sendheaders`; the fixed-seed fallback is empty. Family comparison and attack catalogue: `~/Work/ZK/Dir/Comparison.md` ##Peer networking.

**Order.** Discovery first, since a node that finds few honest peers gains little from eviction rules; then the peer defenses in their table order; then block relay.

#### Peer defenses

| Order | Port | For | Against |
|-------|------|-----|---------|
| 1 | `addr` rate limit with `getpeerinfo` counters (zcashd, Pirate) | Bounds address flooding, the first step of an eclipse | Small; zcashd code exists |
| 2 | Feelers and test-before-evict (Bitcoin Core 0.14, 0.17) | The address table keeps live addresses, so it is harder to fill with attacker addresses | Changes `addrman.cpp`; one short extra connection every 2 minutes |
| 3 | Two block-relay-only outbound connections (0.19) | Links that relay no transactions or addresses do not reveal topology | Two more outbound slots |
| 4 | Anchors (0.21) | Reconnects the block-relay peers after a restart, when an eclipse is easiest | Needs step 3; adds `anchors.dat` |
| 5 | AS-based groups, `-asmap` (0.20) | A hosting provider spread over several /16s and /32s counts as one group per AS | A map file built from BGP data, refreshed each release |

**`dseg` per IP.** The +34 score for a second zeronode list request within 3 hours is kept per IP, so honest nodes behind one NAT address collect it, and a client that reconnects in a loop is banned again after each ban expires. Counting per connection would end these bans. It would also let an attacker who opens many connections request the full list on each of them. Decide with item "Zeronode legacy".

**Tests.** Per port, the Bitcoin Core functional test where one exists (`p2p_addr_relay.py`, `p2p_eviction.py`, `feature_anchors.py`, `feature_asmap.py`), adapted to Zero's RPC harness.

### Consensus

**State.** Rules that interact: block timestamps (median-time-past timespans, timespan bounds of 90 to 130%, a 10-minute future limit since Cosmos, no future bound relative to median time past), Digishield over a 17-block window, a reorganization bound of 99 blocks with node exit, coinbase maturity of 720 blocks, and a last checkpoint at 700,000. The node's adjusted time can move by more than the future limit allows ("Time adjustment"). Family comparison: `~/Work/ZK/Dir/Comparison.md` ##Consensus and ##Chain selection.

**Upgrade candidates.** Each consensus change needs a network upgrade: activation height, branch ID, test vectors, and notice to pools and exchanges. Candidates are decided in their items and bundled into one upgrade: a future-time bound relative to median time past (zcashd's 90 minutes), a difficulty algorithm ("Difficulty review"), and a consensus reorg defense ("Reorg defenses"). Node-policy parts of those items (clock use, checkpoints) ship in any release.

#### Time adjustment

**Now.** `GetAdjustedTime` is the local clock plus the median of peer offsets (`AddTimeData`, `src/timedata.cpp`): one sample per peer address from its `version` message, at most 200 samples and never refreshed, applied when there are at least 5 and an odd count, and only while the median is under 70 minutes; at 70 or more the offset is 0 and a one-time warning goes to the RPC warnings and the log when no peer is within 5 minutes. Users: the future-block limit (10 minutes since Cosmos, `CheckBlockHeader`), the miner's block time (`UpdateTime`: later of median time past + 1 and adjusted time), and zeronode broadcasts and pings signed more than 1 hour ahead (`src/zeronode/zeronode.cpp`). The node never stops on a time fault.

**Concerns.**

- Timejacking: peers that hold the median, from many addresses at startup, move the clock by up to 70 minutes. Moved back more than 10 minutes, the node refuses honest new blocks (`time-too-new`) and stalls; moved forward, its miner stamps blocks that other nodes refuse.
- Samples come from the first 200 addresses and are never replaced, so the offset set at startup persists.
- Nodes behind one NAT address count once; a botnet across many addresses counts many times.
- The warning comes only at 70 minutes, far past the 10-minute block limit.

**Timewarp.** Zero's timestamp rules are listed in "Consensus"; the 10-minute future limit came with Cosmos (commit `b0698eeb3`, "Mitigate timewarp attacks"). The peer-median offset accepted (up to 70 minutes) exceeds the 10-minute limit, so on Zero timejacking can stall a node. On chains with Bitcoin's 2-hour limit, the same offset stays inside the window. Cross-project cases (Bitcoin BIP 94 and BIP 54, Verge 2018, LWMA chains): `~/Work/ZK/Dir/Comparison.md` ###Block time and timewarp.

**Steps.**

1. Port `-maxtimeadjustment` (zcashd v2.1.1-1, "Add -maxtimeadjustment with default of 0"; at most 1500 s) and the v2.1.2 warning-only form (`TIMEDATA_WARNING_THRESHOLD`, 10 minutes): the node uses its own clock, `getpeerinfo` keeps `timeoffset`, and the RPC warnings report a median offset over 10 minutes.
2. Release note and BUILD_ZERO "Clock": NTP becomes required for block acceptance and mining.
3. Tests: `src/test/timedata_tests.cpp` for the median and the warning; regtest with `-mocktime` peers offset by 5, 15, and 80 minutes.

#### Difficulty review

**Now.** Parameters: ZERO_COIN "Chain". The pool review suggests on-off hashrate: profit-switching pools mine while the difficulty lags, then leave; its interval statistics are not yet reviewed. With a 17-block window, dampening by 4, and the median-time-past delay, the difficulty follows such a change over tens of blocks.

**Steps.**

1. **Data.** Add a header scan to `contrib/stats/chain-audit/scan.py` (height, time, `bits`, pool) and report per burst: difficulty before, during, and after, interval, and hashrate implied by difficulty over interval.
2. **Model.** Write a simulator in `contrib/stats/chain-audit/` after zawy12's `test_DAs.cpp` (`difficulty-algorithms`, with its on-off mining model: hashrate on below one difficulty, off above another): Zero's Digishield with the 90-130% bounds that `test_DAs.cpp` leaves out, LWMA (TENT, fluxd), and ASERT (Bitcoin Cash); drive it with the measured pattern: baseline hashrate, switch-on multiple, and the difficulties at which bursts start and stop.
3. **Validate.** Recompute `bits` for a chain segment from the scanned headers with the model's Digishield and match the chain exactly before comparing algorithms.
4. **Compare.** Per algorithm: mean interval, share of blocks mined by switching hashrate at low difficulty, longest interval after a switch-off, response to timestamp manipulation (zawy12's timespan and bad-timestamp tests).
5. **Decide.** Change the algorithm as an upgrade candidate ("Consensus"), or keep Digishield with recorded reasons.

#### Reorg defenses

**Now.** Zero shuts the node down on a reorganization deeper than 99 blocks (`MAX_REORG_LENGTH`, `ActivateBestChainStep` in `src/main.cpp`); the coinbase matures after 720 blocks. The last mainnet checkpoint is height 700,000 (2019, `checkpointData` in `src/chainparams.cpp`). Profit-switching pools can hold a temporary majority on a chain of Zero's size; the measured runs are not yet reviewed. Incidents and the defenses of other chains: `~/Work/ZK/Dir/Comparison.md` ###Majority attacks, ###Finality designs, and ###Detection and intervention.

| Option | For | Against |
|--------|-----|---------|
| Confirmation guidance: a recommended count for exchanges and large payments, derived from the longest single-pool runs once reviewed | No code change | Slower deposits; does not stop an attacker who rents for longer |
| Checkpoint each release | Protects history older than the release; cheap | Leaves recent blocks unprotected |
| Lower `MAX_REORG_LENGTH` (Firo uses 5) | Caps loss at the depth | Nodes that saw different branches first split, and recovery is manual |
| Delayed-block penalty (Horizen; `GetBlockDelay` in the zen clone) | Penalizes a chain hidden from the network; no third party | Hard fork; honest delayed blocks are penalized too |
| ChainLocks signed by zeronodes (Dash, Firo) | A reorg past a locked block needs the quorum | Zeronodes are Dash code from before LLMQ: needs distributed key generation and quorums; a quorum hosted with few providers depends on them |

**Order.** The guidance and a checkpoint in each release first; consensus options are upgrade candidates ("Consensus").

### Mempool and fees

**State.** Zero keeps Bitcoin 0.11 relay policy (free relay, coin-age priority, a priority area in the block template) with ZIP 401 eviction at its first constants; expiry follows ZIP 203 and expiry 0 never expires; there is no mempool age limit. zcashd and Zebra moved to ZIP 317 fees. Family comparison: `~/Work/ZK/Dir/Comparison.md` ###Fee and relay rules, ###Mempool limits, and ###ZIP 317 adoption.

#### Fee policy

**Now.** Free relay, the priority area, and expiry in doc/mining/mining-pools.md "Transactions". The waiver lets every transaction under 1,999,000 bytes relay without fee; coin age admits a zero-fee transaction to a block within hours to days of its inputs' confirmation; an expiry-0 transaction then has no bound on its stay. The `-limitfreerelay` default of 30 in `AcceptableInputs` never runs: both callers in `src/zeronode/zeronode.cpp` pass `fLimitFree` false.

**Expiry options.** Relay policy only, no consensus change; checked in `CTxMemPool::removeExpired` at each block, with entry time and height from `CTxMemPoolEntry::GetTime` and `GetHeight`:

| Option | Default | Effect |
|--------|---------|--------|
| `-mempoolexpiry=<hours>` | 336 | Remove any transaction that entered the mempool longer ago (Bitcoin Core's option and default) |
| `-noexpirymaxblocks=<n>` | 2880 | Remove an expiry-0 transaction `n` blocks after its entry height (4 days at 120 s, twice the 1,440 blocks that coin age needs for a 0.1 ZER input); 0 refuses expiry-0 transactions from peers |

Removed transactions enter the eviction memory (`RecentlyEvictedList`, `-mempoolevictionmemoryminutes`) so a rebroadcast does not bring them back at once. Transactions of the node's own wallet carry an expiry (`-txexpirydelta`, default 20) and are unaffected.

**Traffic.** At low traffic they remove nothing, so they act only in a backlog: a spam wave, or zero-fee transactions with young inputs that no pool includes.

**`-blockminsize`.** Default 0. In fee order it is the block space in which `CreateNewBlock` (`src/miner.cpp`) still takes transactions below `-minrelaytxfee`; it does not pad blocks. At the default it changes nothing. Keeping it costs one more option that interacts with `-blockprioritysize`. It stays as a pool tuning option. With a ZIP 317 template, `-blockunpaidactionlimit` takes its role, and it is then deprecated.

**Zcash context.** zcashd halted on 2026-07-18. Since then no Zcash mainnet node relays or templates a transaction below the ZIP 317 conventional fee. Zero's network is separate and unaffected. Zero's fee code no longer has a maintained C++ upstream: zcashd's last version is 6.20.0.

**ZIP 317 by part.** Revision 0 without the Orchard term; zatoshi is 10^-8 ZER as in Zcash.

| Part | Zero now | Proposal | Reason |
|------|----------|----------|--------|
| Wallet fee: `marginal_fee` 5000 x max(2, logical actions); transparent by size (150-byte inputs, 34-byte outputs), Sprout 2 per JoinSplit, Sapling max(spends, outputs) | Flat 10000 (`ASYNC_RPC_OPERATION_DEFAULT_MINERS_FEE`) | Take | A 2-action transaction pays 10000, as today; only larger transactions pay more. The fee is computable from public data and does not reveal the wallet |
| ZIP 401 penalty below the conventional fee of each transaction; constants 10000 and 40000 | Below a flat 10000; 4000 and 16000 | Take, with the wallet fee | Eviction weight follows the fee wallets pay |
| `-blockunpaidactionlimit` (zcashd 50 in v5.5.0, 0 in 6.11; Zebra 0) | No limit; priority area | Take, as an option with a default above 0 | Bounds free and underpaying transactions per block whatever the mempool holds. The default decides how much free traffic Zero keeps: 0 ends it |
| Template by weighted random selection (`weight_ratio`, capped at 4) | Priority area, then fee order | Optional, behind an option | Blocks are not full, so selection order has no effect today; the unpaid-action limit is the part that binds. Random selection would also end coin-age priority, through which zero-fee transactions are mined |
| Relay: drop over `-txunpaidactionlimit` (zcashd v5.6.0, default 50); relay floor 100 zats per 1000 bytes, at most 1000 | Free-relay waiver under 1,999,000 bytes, `-limitfreerelay` 15 kB/min | Optional; default equal to the block limit | A per-transaction bound replaces the byte-rate counter. Large zero-fee transactions that relay today would be refused |
| Remove `-mintxfee`, `-sendfreetransactions`, `estimatepriority`, `prioritisetransaction` priority deltas | Present | Deprecate first, remove after Zerowallet confirms it uses none | Removing RPC options breaks clients without notice |
| Revision 1 (Ironwood actions, NU6.3), revision 2 (memo bundles, ZIP 248) | -- | Avoid | Zero has neither pool nor format |
| Consensus enforcement | -- | Avoid | ZIP 317 is policy; a consensus fee would invalidate blocks with free transactions mined under today's rules |

**Alternatives.** The parts above, all or by row; or keep Bitcoin 0.11 policy with the expiry options above.

**Tests.** Regtest: an expiry-0 transaction leaves the mempool at entry plus `n` blocks and is refused for the eviction memory; `-noexpirymaxblocks=0` refuses it at relay; an old zero-fee transaction is mined through coin age before its limit.

#### Refusal analysis

**Now.** `AcceptToMemoryPool` refuses relayed transactions whose transparent inputs are spent (`bad-txns-inputs-spent`) or whose shielded spends reuse a nullifier or name an unknown anchor (`bad-txns-shielded-requirements-not-met`). The default log gets one count per reason, written when the first refusal arrives at least 3600 s after the previous summary, so quiet periods give longer windows and refusal-free hours give no line. `-debug=mempool` logs each refusal with txid, peer, and the nullifier or anchor. Both checks run before proof verification, and these refusals carry no misbehavior score, as in zcashd.

**Causes to tell apart.**

- Timing: a peer relays a transaction already mined, because it has not yet seen the block. The refused txid is itself in a block connected seconds to minutes earlier.
- Coincidence: two broadcasts of conflicting spends by the same owner, such as a wallet rebroadcast after a restore, a replaced transaction, or a reorg that dropped a transaction. Rare, from one or two peers, not repeated.
- Attempts: double spends aimed at a recipient that accepts unconfirmed transactions, or floods meant to cost relay bandwidth and checks. The conflicting transaction is in the mempool rather than in a block, the outputs differ, the same peer or address group repeats, or the rate rises well above its usual level.

**Signals per refusal.** Whether the refused txid is already in the chain (timing) or a different transaction spent the input (conflict); whether that transaction is in a block or in the mempool, and for how long; the peer and its address group; repeats of the same txid or input; for shielded refusals, nullifier spent in the chain against anchor unknown (a peer on another chain or not synced).

**Suggested work.** Record the class with each refusal; write the summary by class and by top peers from the scheduler at fixed hourly boundaries instead of on the next refusal; add counters to an RPC (`getmempoolinfo` or `getpeerinfo`); keep the refusals non-punitive unless a peer repeats the same conflict. Test with regtest scenarios: relay of a mined transaction, a wallet double spend (`txn_doublespend.py`), and repeated conflicting relays from one peer.

### Monitoring

#### Network assessment

Nodes: one hosted node with inbound P2P that runs continuously; a second hosted machine that can run `zerod` but is not deployed regularly, started for each measurement run; and one node behind NAT (outbound only). Node-side counters come from item "Peer monitoring"; this item measures from outside with the nodes as probes.

1. **Time.** Every node on NTP (BUILD_ZERO "Clock"), offset recorded with each run; sub-second log times need item "Log microseconds".
2. **Logging.** `-debug=net -logips` on each node: "received block <hash> peer=<id>" and the peer's address give the first relayer of every block.
3. **Propagation.** Per block and node, first arrival minus block time, and the spread between nodes; per pool, the first-relaying peers, which locate pool nodes; batched arrivals seen at all nodes point to the pool, at one node to its path.
4. **Peers.** Periodic `getpeerinfo` per node (version, subversion, ping, start height, direction, `timeoffset`); a P2P crawler (version handshake, `getaddr`) for the reachable network, its size, versions, and address spread; DNS seed answers and liveness.
5. **Address groups.** Group peers, zeronodes (`zeronode list`), seed lists, and first relayers by IPv4 /16 and /24, IPv6 /32 and /48, and AS (RIR whois, not radb); overlaps between the sets locate farms and pool nodes.
6. **Misbehavior.** Tally `Misbehaving: <addr> (a -> b)` lines of `debug.log` per address, score delta, and day, with `dropped (banned)` lines; a restart with `-debug=net,zeronode` names the cause of each score. Scores in Zero: +34 for a second zeronode list request (`dseg`) from one IP within 3 hours (`ZERONODES_DSEG_SECONDS`), +20 for a repeated payment-vote request (`znget`) on one connection, +10 for an expired transaction (`ContextualCheckTransaction`); 100 bans for `-bantime` (86400 s).
7. **Forks.** `getchaintips` on every node; stale blocks seen by one node only show slow paths.
8. **Mempool.** `getrawmempool` on every node at each new block (`-zmqpubhashblock`): mempool contents when an empty block arrives (empty template or empty mempool), transaction propagation between nodes, free and never-expiring transactions held.
9. **Output.** Per-node TSV files and reports from `contrib/stats/chain-audit/`, kept outside this tree; `addresses.py` groups zeronodes, peers of several nodes, and address lists by subnet and reports overlaps and multi-connection addresses.

### Mining

#### Mining follow-up

After the pool review (doc/mining/mining-pools.md) is reviewed:

- **Identities.** Ask the smaller pools listed for Zero for their payout addresses or block heights, and match them against the unattributed coinbase addresses.
- **s-nomp.** Propose the patch of doc/mining/s-nomp-recipients.md "Fix" to `node-stratum-pool` and an address placeholder for the s-nomp example configurations; send the note to pool operators on Zero; check other s-nomp coins for coinbases short by exact recipient percentages.
- **Listings.** Ask mining listing sites to correct Zero's algorithm, reward, and block time where they differ from ZERO_COIN.
- **Withholding test.** Decide between slow relay and withheld blocks for batched branches with the multi-node arrival data of item "Network assessment".

#### Chain-audit tools

Kept in `contrib/stats/chain-audit/`: `audit_rpc.py` (batched RPC, subsidy schedule, known addresses), `scan.py` (coinbase, time, and fee scans), `analyze.py` (reports), `addresses.py` (address groups; runs on Python 3.6 and later, tested on Ubuntu 18.04 and 24.04 against a local node or with `--no-node` and saved files). Next to it, `chain_stats.py`, `decode_coinbase.py`, and `block_rate_replay.py` each carry their own RPC code.

Scratch analyses of the pool review, outside the repository until merged:

| Script | Does | Disposition |
|--------|------|-------------|
| `misb.py` | Misbehavior score sequences per connection, bans, and refusals for one address in a `debug.log` | Stage 1 |
| `mempool_age.py` | Mempool age, expiry-0, and fee counts on a live node | Stage 2 |
| `exp_full.py`, `exp_all.py` | Full count of expiry-0 transactions over a range | Stage 3, replacing the sampled `analyze.py expiry` |
| `prio.py`, `prio2.py` | Coin-age priority of mined zero-fee transactions against the free threshold (`COIN * 144 / 250`) | Stage 4 |
| `coinbase_scan.py`, `coinbase_scan2.py`, `fee_scan.py`, `arrival.py`, `pool_stats.py` | Earlier forms of `scan.py coinbase`, `scan.py fees`, `analyze.py arrival`, `eras`, and `bands` | Drop: superseded with the same output |
| `time_scan.py` | Block times plus the earliest creation height of each block's transactions, as expiry height minus 20 | Drop: expiry is 0 for most transactions, so the column is mostly empty |
| `assoc.py` | Address groups and overlaps | Done: `addresses.py` |
| `sntp.py` | One SNTP query (UDP 123) giving the local clock offset to a time server, corrected for round trip; it measured the node clock for doc/mining/mining-pools.md "Timestamps and arrival" | Drop: `sntp` (macOS), `ntpdate -q`, and `chronyc tracking` give the same |

**Stages.** One commit per stage. Each stage reruns `analyze.py underclaim` over a fixed height range and compares the output with the run before the stage, to show that shared code did not change existing reports.

1. `analyze.py misbehavior LOG [ADDR]`, no RPC. Validation: a saved `debug.log` gives the same connections, bans, and refusals as a hand count.
2. `analyze.py mempool`. Validation: the count equals `getmempoolinfo` `size`. On regtest, a zero-fee expiry-0 transaction and a paying one with expiry are counted in their classes.
3. `analyze.py expiry` as a full count to a fixed end height. Validation: the sampled counts per era fall within sampling error of the full ones.
4. `analyze.py priority`. Validation: three transactions computed by hand from `getrawtransaction` inputs; on a live node, mempool transactions match the `startingpriority` of `getrawmempool true`.
5. `decode_coinbase.py` onto `audit_rpc.py`. Validation: output identical before and after for heights 412,300, 800,000, and 2,400,000 and for `--start 2471200 --count 200 --summary`; the new role column matches `analyze.py setups` for the same blocks.
6. `--help` and `py_compile` of every script in `contrib/run-tests.sh`.

**`decode_coinbase.py`.** It prints the coinbase outputs of a few blocks for a person to read (value, type, address, script, vout histogram, `--json`) through `zero-cli`. `scan.py coinbase` writes the same outputs as TSV in bulk. Options:

| Option | For | Against |
|--------|-----|---------|
| Expand it into a full coinbase report: pool, subsidy check, tags, splits | One tool for people | Duplicates `scan.py` and `analyze.py`; two copies of the pool rules diverge |
| Retire it into an `analyze.py block HEIGHT...` report | One code path | `analyze.py` works on TSV files; loses the `zero-cli` path, which needs no `zero.conf` credentials |
| Keep it as the per-block inspector on `audit_rpc.py`, adding a role per output (pool, development fee, zeronode, from `miner_outputs` and `zeronode_tier`), the scheduled subsidy, and the coinbase tag | Reading a few blocks and bulk scanning stay separate; labels come from the rules the reports use | Reads credentials from `zero.conf` (`ZERO_CONF` selects another datadir) |

Recommendation: the third. The missing feature is output roles, and only shared rules keep them consistent with the reports. Bulk use belongs to `scan.py`.

`block_rate_replay.py` (node warning replay) and `chain_stats.py --verify` (schedule check) stay as they are.

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
- `zero-410` has only `.github/workflows/tests.yml`: Ubuntu 24.04, apt packages including `python3-zmq`, `fetch-params.sh`, `build.sh -j2`, then `./contrib/run-tests.sh --strict` (C++ gate and Tier A, not `--all`), timeout 240 min. Triggers: push to `main`, `master`, `develop`; pull requests; `workflow_dispatch`. Pushes to `zero-410` match no trigger, and `workflow_dispatch` needs the file on the default branch, so it has never run.

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

Method: port the runner parts of Bitcoin Core `test/functional/test_runner.py` that answer these problems. `BASE_SCRIPTS` and `EXTENDED_SCRIPTS` as the one list per tier (Zero's pass tiers and Large); `NON_SCRIPTS` for helper modules; `check_script_list`, which fails when a Python file in the test directory is in no list, in place of the hand-regenerated CSV; `check_script_prefixes` for name prefixes (`wallet_`, `rpc_`, `p2p_`, `mempool_`, `feature_`); `--portseed` per job with `--jobs`, `--filter`, `--exclude`, and `--failfast`; per-script run times in the summary.
