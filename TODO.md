# TODO

Open follow-ups for the Zero full node (`zerod`).

---

## Tracking rules

**Names.** Each item has a title of one to three words, in bold at the start of its entry, followed by `--` and imperative sentences. Titles carry no ID, prefix, or number.

**One definition.** An item is described in one place: here, as a one-line entry with an optional Full description.

**TODO and TEST_ZERO.** TEST_ZERO describes the tests as they run now: commands, layers, tiers, held scripts with their blockers, the release bar, and operational checks. TODO holds the changes to make. A test item names the TEST_ZERO section or row it changes and does not restate its blockers or commands; when the change lands, TEST_ZERO is updated and the item removed.

**Status is the section.**

- **Release** -- work the v4.1.0 tag waits for, in order. Nothing else belongs here.
- **After release** -- accepted work the release does not wait for, grouped by subject. A short status note (postponed, not scheduled, decide after X) is allowed.
- **Done** -- remove the entry. The outcome lives in the code, the documentation of the behavior, and the release notes; no completed-items lists.

---

## Release

1. **Branch cleanup** -- Before the tags, delete branch `zero-401`; its history stays in tag `archive/zero-401`.
2. **Release candidate** -- Tag `v4.1.0-rc1` on `zero-410` per BUILD_ZERO "Release".
3. **Release platforms** -- Build, test, and package on Linux and Windows at the `v4.1.0-rc1` tag per TEST_ZERO "Release bar".
4. **Release signing** -- Decide after the `v4.1.0-rc1` cross-platform tests, before v4.1.0: the `SHA256SUMS` signature method and key holder; whether macOS archives ship with a Developer ID signature and notarization; whether Windows archives ship with Authenticode. Then add the sign and verify commands to BUILD_ZERO "Release".
5. **Release tag** -- Set the release version, tag `v4.1.0`, and merge into `master`, per BUILD_ZERO "Release". In the same sitting as the v4.1.0 GitHub release, delete the `v4.0.1-RC-18` and `v4.0.1-RC-24` pre-releases with their tags (`gh release delete <tag> --cleanup-tag`); their binaries report v4.0.1 but were built from `fb9efafd1`, which is not on `zero-410`.

---

## After release

Wallet:

- **Const wallet reads** -- Continue const conversion on wallet-tx read paths.

RPC:

- **Sprout RPCs** -- Decide each Sprout RPC's disposition and record test depth per RPC from the harness in `doc/RPCs.csv` (v4.1.0 ships the dispositions recorded now), then remove the code of RPCs that leave Zero, starting with the compiled-out raw JoinSplit RPCs; postponed. The accounts RPCs stay deprecated until Zerowallet lists transparent addresses with `listreceivedbyaddress`.
- **Wallet interface** -- Write the public node-wallet interface contract that Zerowallet links to: RPCs and parameters it uses, error codes and retry rules, `zero.conf` keys, data and parameter paths, and the node-wallet version table. Then align the `zero.conf` Zerowallet writes (`rpcworkqueue`, `txindex`, `keeptx*`, `safekey`, macOS directory) with it in a coordinated Zerowallet release; under consideration. The v4.1.0 changes clients see are in its release notes, "Upgrade actions" and "RPC".
- **getalldata cost** -- Measure poll cost on a large wallet first, then the follow-up steps.
- **Chain statistics** -- Keep `-zindex` and the shielded fields of `getchaintxstats` for shielded-usage statistics, fix their defects, and add test coverage, per Full description "Chain statistics"; postponed.
- **Peer RPC during rebuild** -- Add `getpeerinfo` to the RPCs `src/rpc/server.cpp` serves while `fBuildingWitnessCache` is set (now `stop`, `help`, `getblockcount`, `getblockchaininfo`, `getnetworkinfo`), so monitors and `connect_nodes` do not get -33 during a witness build; it then waits for `cs_main` instead of failing. Needs a release note.

Node operation:

- **Reindex safeguards** -- Refuse a `reindex=` line in `zero.conf` and an unforced `DB_FLAG` mismatch unless `-reindexforce`; skip the wallet replay below a height.
- **Conf checks** -- Check automatically that every key in `contrib/zero.conf` and `contrib/conf-templates/` is a parsed option and that shown defaults match `zerod -help` and `-help-debug`; add a default column to `doc/Options.csv` generated from the help text; run the check in `contrib/run-tests.sh` and `zcutil/check-release.sh`. `contrib/tools/inventory-check.py` counts commented-out `GetArg` calls as parsed options, so it missed `prune` and `txindex`; parse only live code.
- **Lab setup** -- Harmonize datadir and configuration setup across the `ops-validate.sh` labs and templates, the RPC test cache, and height-bounded labs; exercise each template's use case, and replace the two-step Zerowallet check in TEST_ZERO "Release bar" with one run that copies the wallet in and syncs a datadir copy on lab ports.
- **Chain diagnostics** -- Port the diagnostic and recovery tools that Zero lacks; postponed.

Network and P2P:

- **Peer discovery** -- Review how a new node finds peers: the DNS seed names in `vSeeds` (`src/chainparams.cpp`) and their records, a crawling seeder that publishes only live nodes, and the fixed-seed fallback. `src/chainparamsseeds.h` has empty mainnet and testnet arrays, `contrib/seeds/nodes_main.txt` and `nodes_test.txt` list no nodes, and `contrib/seeds/README.md` describes Bitcoin Core 0.10 seeds; fill the fallback from long-running nodes and refresh it each release.
- **Peer defenses** -- Port the peer-management features Bitcoin Core added after 0.12: the per-peer `addr` rate limit with its `getpeerinfo` counters (also in zcashd), feelers and test-before-evict, block-relay-only connections, anchors, and `-asmap`, each with its Bitcoin Core functional test adapted to Zero's harness; postponed.
- **Tor compile-out** -- Add a `--disable-tor` configure option that compiles out Tor control; runtime onion is already off by default; keep it separate from I2P.
- **Block relay** -- Port `sendheaders` (BIP 130); postponed.

Consensus:

- **Time adjustment** -- Port zcashd's `-maxtimeadjustment` (v2.1.1-1) and its warning-only form (v2.1.2): the node uses its own clock, `getpeerinfo` keeps `timeoffset`, and the RPC warnings report a large median offset; add `timedata_tests` cases and a BUILD_ZERO "Clock" note that NTP is required; postponed.
- **Difficulty review** -- Model Digishield with Zero's parameters (ZERO_COIN "Chain") against LWMA and ASERT on recorded chain data, and decide whether to change the algorithm in a network upgrade; postponed.
- **Zeronode review** -- Work through doc/zeronodes.md "6. Review" and decide whether the spork, SwiftTX, and budget code stays, is reduced, or is removed; the TODO markers in `src/zeronode/` and `src/rpc/zeronode.cpp`, imported with the TENT masternode code, are resolved by that decision; postponed.
- **Reorg defenses** -- Publish confirmation guidance for exchanges, then decide whether a consensus defense is needed; checkpoints are item "Checkpoint update"; not scheduled.

Mempool and fees:

- **Fee policy** -- Decide on a conventional fee (ZIP 317) with the matching ZIP 401 constants, on free relay and coin-age priority, and on mempool limits for zero-fee and never-expiring transactions; postponed.
- **Refusal analysis** -- Classify transactions refused from peers by cause and report the counts per class through RPC; postponed.

Mining:

- **Coinbase tag** -- Add a `-coinbasetag=<text>` option that the internal miner and the `coinbasetxn` template append after the height (`COINBASE_FLAGS`, `CreateNewBlock` in `src/miner.cpp`), within the 100-byte coinbase input limit, so solo miners and pools that use the template are identifiable.
- **Stats tools** -- Give `chain_stats.py`, `decode_coinbase.py`, and `block_rate_replay.py` in `contrib/stats/` one shared RPC module in place of their own copies, and run `--help` and `py_compile` of each in `contrib/run-tests.sh`; postponed.

Monitoring:

- **Peer monitoring** -- Evaluate the monitoring examples and code of Bitcoin Core (tracepoints, message capture, log rate limit, `logging` RPC), zcashd (`setlogfilter`), and bmon first. Report connections and peer interactions for monitoring: counts by direction, connect, disconnect, and ban events with reasons, per-peer message and byte counters, and address-manager health, through RPC and a periodic summary line; per-event lines stay under `-debug=net`. Keep the `receive version message` line and `-logips` as they are.

Logging:

- **Log microseconds** -- Port `-logtimemicros` from Bitcoin Core: read it in `init.cpp`, list it in `-help-debug`, and append the microseconds of `GetTimeMicros` in `LogTimestampStr` (`src/util.cpp`); only the unused flag `fLogTimeMicros` exists; postponed.

Code text:

- **Fee wording** -- Apply CONTRIBUTING "Development fee naming" to text written before it: the `getblocksubsidy` help in `src/rpc/mining.cpp`; the `founders reward missing` log text in `src/main.cpp` (the reject reason stays); Zero-written comments in `src/main.h`, `src/main.cpp`, `src/consensus/params.h`, the regtest section of `src/chainparams.cpp`, `src/zeronode/budget.cpp`, and `src/test/rpc_wallet_tests.cpp`.

Tests:

- **Zero RPC depth** -- Test shielded outputs and filter types for the zs_* RPCs, `getsupply` values against the emission schedule (its help says "coin supply"; it returns the scheduled mint, not the measured supply), Sapling witness RPCs, and mined-transaction History in `getalldata`.
- **Test conversion** -- Convert the scripts of TEST_ZERO "Held scripts" except the Obsolete, Retired Sprout, and GTest rows, and promote each after five clean serial runs: the scripts of the height and maturity rows with the helpers in TEST_ZERO "Writing tests for Zero"; the Python-solved-block scripts by solving with the `ZERO_PoW` personalization in `test_framework/equihash.py`; then `getblocktemplate_proposals` and `smartfees`; then the Fork warnings row, adapted to Zero's block version floor and to warnings checked without `-alertnotify`. Postponed.
- **Witness rebuild coverage** -- Test witness rebuild (`-walletwitness=rebuild`) and bring the GTest row of TEST_ZERO "Held scripts" into the merge gate.
- **Test filters** -- Unify test tiers, filters, and their names across the runners.
- **Test speed** -- Cut the serial RPC run and the merge gate: shorter waits, fewer iterations, more concurrency, cheaper and precomputed setup, and tier moves, per Full description "Test speed".
- **Fuzz harness** -- Add libFuzzer targets under `src/fuzz/`.
- **Python cleanup** -- Adopt a format and lint check for Zero's Python files, share helpers in `contrib/stats` and `contrib/tools`, and unify script names and headers; postponed.
- **Benchmark clarity** -- Fix the `zcbenchmark` help and defective types, record timing samples, guard miner memory, and validate tromp, per Full description "Benchmark clarity"; postponed.

Build, packaging, and release:

- **Script shebangs** -- Switch `zcutil/fetch-params.sh`, `contrib/tidy_datadir.sh`, `qa/pull-tester/rpc-tests.sh`, `qa/pull-tester/run-bitcoind-for-test.sh`, and `qa/pull-tester/tests-config.sh` from `#!/bin/bash` to `#!/usr/bin/env bash`, and run each under bash 3.2 and 5, per CONTRIBUTING "Shell scripts"; postponed.
- **Toolchain versions** -- Verify GCC, Rust, Python, and autotools versions per supported build OS, record them in BUILD_ZERO "Requirements", and check them in `zcutil/check-setup.sh`. Rust: Linux builds use the pinned 1.32.0 unless `RUST_USE_SYSTEM=1`, macOS the system Rust; decide the Linux default and the minimum Rust for `librustzcash`.
- **Windows hardening** -- Pass `--enable-hardening` in `build-win.sh`; needs the MXE build host.
- **Checkpoint update** -- Add a mainnet checkpoint and raise `nMinimumChainWork`, per Full description "Release constants"; postponed: needs investigation of the effects, coordination with pools and exchanges, and a validated way to detect and recover a node that is on a branch the checkpoint refuses.
- **Deprecation baseline** -- Decide the deprecation baseline and window, per Full description "Release constants"; postponed.
- **Upstream names** -- Review the three places where they send users to Zcash: the bug URL in `configure --help`, the security page in `zerod -help` and the man pages, and `doc/man/zcash-fetch-params.1`, which documents the script the release archives ship as `zero-fetch-params`.
- **Params mirror** -- Make a Zero-controlled copy of the three parameter files the primary source of `fetch-params.sh`, with GitHub release assets as a second copy, keeping zcashd's host and IPFS as fallbacks; verify file names and checksums.
- **Parameter acquisition** -- Decide where proving parameters come from for `zerod` and Zerowallet, per Full description "Parameter acquisition"; postponed.
- **Chain bootstrap** -- Document the end-user import path (`-loadblock`, auto-import), snapshot sourcing, and verification; linearize in `contrib/linearize/`.
- **CI workflows** -- Replace the `master` workflow with `.github/workflows/tests.yml` and extend it; postponed.
- **Contrib cleanup** -- Remove the inherited tools Zero does not use (`contrib/macdeploy`, `tidy_datadir.sh`, `verifysfbinaries`, `test-patches`, `spendfrom`, `verify-commits`, `qos`, `bitrpc`, and in `contrib/devtools` `github-merge.sh`, `fix-copyright-headers.py`, `optimize-pngs.py`) and their `contrib/README.md` entries; replace `contrib/init/` with one `zerod.service`; rename the bash completions to Zero's binaries and install them from the `.deb`.
- **Base58 vectors** -- Port zcashd's two-byte address prefixes to `contrib/testgen/gen_base58_test_vectors.py`, regenerate `src/test/data/base58_keys_*.json` with it, and confirm `base58_tests` against Zero's prefixes; postponed.
- **AMQP removal** -- Remove AMQP (`src/amqp/`, the Proton recipe in `depends`, `contrib/amqp/`, `proton_test.py`, `--enable-proton`), as zcashd did; ZMQ remains the notification path.
- **Windows ZMQ** -- Review enabling ZMQ in Windows builds (`build-win.sh` passes `--disable-zmq`): features needed, implementation, and tests.
- **Linux package** -- Add man pages, the example `zero.conf`, and bash completions to the `.deb` from `zcutil/release-linux.sh`, and the example `zero.conf` to the macOS and Windows archives.
- **Script precedence** -- Decide the precedence between environment variables and command-line options in the build, release, and ops scripts; proposal: the environment overrides the option, each replaced value is printed, and CONTRIBUTING states the rule, per Full description "Script precedence"; postponed: verify on the native, Windows, macOS release, and ops paths.

Documentation:

- **Docs lint** -- Automate the documentation checks in `contrib/run-tests.sh`: relative links and section references resolve, ASCII outside README, no parentheticals in headings, named files exist, and documented commands run; then generate stated facts from the code.
- **Recovery costs** -- Measure the time, disk, and memory of each BUILD_ZERO "Recovery" option on a mainnet datadir copy and on `ops-validate.sh` snapshots, and add them to that section with the tests that cover each option (`doc/Reindex_Rescan.csv`); update the section when an option changes.
- **Pool guidance** -- Publish a pool-operator section: coinbase rules, identification, relay, transaction policy, and the s-nomp recipient fix; postponed.
- **README claims** -- Back the README feature headings (fast and zero-cost transactions, ASIC resistance, unique algorithm) with facts and sources, or reword them; kept as branding for now.

Long-term, not scheduled:

- **LevelDB update** -- Update `src/leveldb` to LevelDB 1.22 as in Bitcoin Core and zcashd; restores block-cache usage in `getdbinfo`. Set 32 MiB table files (`max_file_size`, as Bitcoin Core and zcashd `DBWRAPPER_MAX_FILE_SIZE`) so the block index and chain state fit the table cache. Recheck `max_open_files`, 256 for every database (`GetOptions` in `src/dbwrapper.cpp`): on 64-bit hosts LevelDB 1.18 maps cached tables and closes their descriptors, up to 1000 mappings per process shared by `blocks/index`, `chainstate`, and `sporks`, so 3 x 246 cached tables hold no descriptors, while 1000 per database (Bitcoin Core on 64-bit) would pass the mapping limit and take descriptors from the 150 that `init.cpp` reserves; the comment there cites Pirate's value instead of this reason and says descriptors need `ulimit -n` headroom, which cached tables do not.
- **OpenSSL 3** -- Preference: move from OpenSSL 1.1.1w to 3.x, or remove OpenSSL as Bitcoin Core did; not scheduled. Call sites: wallet encryption in `src/wallet/crypter.cpp` (`EVP_BytesToKey`, AES-256-CBC through `EVP_*`), `OPENSSL_cleanse` in `src/support/cleanse.cpp`, locking and config setup in `src/util.cpp` (`CRYPTO_set_locking_callback`, `OPENSSL_no_config`, no-ops since 1.1.0), `BN_*` in `src/test/bignum.h`, and includes only in `src/init.cpp` and `src/zeronode/obfuscation.cpp`. RPC has no TLS (`-rpcssl` is refused).

---

## Full descriptions

Grouped by area. Each area opens with the state of the code and the decisions that span its items; the items follow.

### Release constants

Values compiled into each release. Once decided, BUILD_ZERO "Release" lists their update as a release step.

**Checkpoint.** Mainnet `checkpointData` in `src/chainparams.cpp` ends at height 700,000 (2019-10-20), with 1,376,076 transactions to that block and an estimate of 1,132 transactions per day after it. Below the last checkpoint `ConnectBlock` skips script checks and `ContextualCheckBlockHeader` refuses forks; `GuessVerificationProgress` extrapolates sync progress past it from the per-day estimate. `-checkpoints=0` turns off the first two. `consensus.nMinimumChainWork` dates from the same release; `IsInitialBlockDownload` stays true while the tip has less work. Update: a block well below the tip, its hash from `getblockhash` on two independently synced nodes, the transaction count and rate from `getchaintxstats`, and `nMinimumChainWork` from the `chainwork` of `getblockheader` at that block.

**Deprecation.** `src/deprecation.h`: `DEPRECATION_HEIGHT` is `APPROX_RELEASE_HEIGHT` plus `WEEKS_UNTIL_DEPRECATION` weeks of 120-second blocks: 1,385,000 + 520 x 5,040 = 4,005,800. `EnforceNodeDeprecation` runs on mainnet only: it warns once 4 weeks (20,160 blocks) before, through the log, `-alertnotify`, and the metrics screen, and shuts the node down at the height, with no option to override. `getdeprecationinfo` returns `deprecationheight`. `signrawtransaction` also takes `APPROX_RELEASE_HEIGHT` as the least height when it selects the consensus branch ID. The baseline 1,385,000 comes from an earlier release, so v4.1.0 inherits that release's shutdown height; blocks left: `getdeprecationinfo` minus `getblockcount`. Decide whether each release sets `APPROX_RELEASE_HEIGHT` to its release height, as zcashd does, and the window length; the comment "Fixing zero day size - was 1,392,080" in `deprecation.h` is change history and goes with the next edit.

**Upstream names.** Derived code keeps the upstream names per CONTRIBUTING "Vendored subtrees". `AC_INIT` in `configure.ac` names the package `Zcash`, the bug URL `https://github.com/zcash/zcash/issues`, and the tarname `zcash`; they set `PACKAGE_NAME`, `PACKAGE_BUGREPORT`, `PACKAGE_TARNAME`, the `make dist` archive name, and the default install `docdir`. `_COPYRIGHT_YEAR` is 2022: `LicenseInfo` in `src/util.cpp` prints "2009-2022 The Bitcoin Core Developers" and "2015-2022 The Zcash Developers", with no Zero line, and the man pages copy it; `COPYRIGHT_YEAR` and `COPYRIGHT_STR` in `src/clientversion.h` are the fallbacks for builds without the configure header. `PrivacyInfo` in `src/util.cpp`, the man pages, and README "Security Warnings" point to `https://z.cash/support/security/`. `doc/man/zcash-fetch-params.1` keeps the Zcash name. The package name, tarname, library and header names (`libzcash`, `bitcoin-config.h`), and the upstream copyright lines stay; the license requires the upstream notices, and a Zero holder line is a separate decision. Only text that sends users to Zcash is reviewed.

### getalldata cost

**Problem.** `getalldata` is the wallet client's single refresh call. Argument 1 (datatype) selects the payload: **0** addresses, balances, transactions, and chain info; **1** addresses, balances, and chain info; **2** transactions and chain info. Argument 2 is the day window (default 7 days), argument 3 the transaction count, argument 4 watch-only. Each call walks every wallet address and transaction (`mapWallet` plus the transaction archive), decrypts shielded notes, sorts history, and builds JSON; on wallets with long history that takes seconds, and clients poll every few seconds. In tree: the soft **-34** coalesce, the 7-day default window, const wallet walks, sort-key collision detection, and one parse/filter path for window, count, watch-only, and datatype (`IsGetAllDataTxTooOld`).

- **Poll cost** -- the split itself (balances on a timer, History on user action or every Nth tick) is a client change, outside this repository. The desktop wallet polls every 30 s but calls `getalldata 0 2 50 true` (datatype 0, 7-day window, 50 transactions, watch-only) only when a new block arrives; no other known client uses the RPC, and the node keeps no per-datatype statistics. Node side: measure both datatypes on a wallet with many transactions and archived entries (wall time, `getalldata` -34 rate under a fixed poll interval), then document the cadence. Complements the soft **-34** coalesce. Decides whether the tip cache is needed.
- **Tip cache** -- in-process tip and dirty cache, after poll cost. **Single walk**: merge History key insert into the balance walk. **Decrypt review**: IVK decryption cost.
- **Helpers** -- the remaining shared parse and filter helpers.
- **Address keys** -- key `addressBalances` by destination and encode once at JSON emit.

### Chain statistics

**Origin.** `getchaintxstats` comes from Bitcoin Core: `time`, `txcount`, `window_final_block_hash`, `window_block_count`, `window_tx_count`, `window_interval`, `txrate`. The Hush port adds `-zindex` (off by default; a change needs `-reindex`): eleven per-block shielded counters in `CBlockIndex` (`src/chain.h`), written to `blocks/index` only with `-zindex`, and with it the RPC fields `shielded_txcount`, `fully_shielded_txcount`, `shielding_txcount`, `deshielding_txcount`, the matching `*_payments` and rates, `shielded_outputs`, `nullifiers`, `shielded_pool_size`, `notarizations`, and an `organic` set.

**Use.** Nothing in this tree, Zerowallet, or the explorer calls `getchaintxstats` or enables `-zindex`. `reindex_db_flags.py` and `reindex_tests` cover only the `-zindex` database flag.

**Defects.**

- `notarizations`, `notarization_txrate`, and the notarization term of `organic` count Komodo notarizations, which Zero does not have; the detection in `src/main.cpp` is commented out, so the values are always 0.
- `nullifiers` comes from `CWallet::NullifierCount` through `g_zeronodeWallet`, although it returns the global `pcoinsTip` count; with `-disablewallet` it is 0 and `shielded_pool_size` equals every shielded output created. `shielded_pool_size` counts notes, not value.

**Tests elsewhere.** Bitcoin Core `rpc_blockchain.py` (`_test_getchaintxstats`) checks the base fields and their errors. Hush has none. Pirate checks the field schema only (`qa/pytest_komodo/basic/test_blocks.py`).

**Plan.** The statistics stay: shielded usage measures how much of the chain is private, and its value grows with GUI access to it.

1. Remove `notarizations`, `notarization_txrate`, and the notarization term of `organic` from the RPC and its help.
2. Take the nullifier count from `pcoinsTip` instead of `CWallet::NullifierCount`; rename or document `shielded_pool_size` as a note count.
3. Tests: port Bitcoin Core `_test_getchaintxstats` for the base fields; add a regtest script with `-zindex` that mines shielding, fully shielded, and deshielding transactions and checks each counter and rate, with and without `-disablewallet`, and after `-reindex`.
4. Measure the `-reindex` time and block-index size with `-zindex` on a mainnet datadir copy, and record them in BUILD_ZERO "Index settings".

The field changes alter RPC output and go in the release notes.

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

### Parameter acquisition

Zero 4.1.0: `ZC_LoadParams()` (`src/init.cpp`) requires `sapling-spend.params`, `sapling-output.params`, and `sprout-groth16.params` (about 741 MiB) in the parameter directory and loads them at startup with `librustzcash_init_zksnark_params`. `zcutil/fetch-params.sh` downloads each from `download.z.cash` in two parts, `<name>.part.1` and `<name>.part.2`, and joins them; part 2 of the Sapling files is empty. Zerowallet downloads the same files itself before it starts `zerod` (`kParamFiles` in `connection.cpp`), a second copy of the file list and digests. The wallet download stays until this is decided.

| Option | For | Against |
|--------|-----|---------|
| Wallet download, current | Works with Zero 4.1.0; progress in the wallet | Second copy of the file list and digests |
| `zerod` prints a manifest (files, sizes, digests, URLs) | `zerod` owns the facts; no network code in `zerod` | Zerowallet still downloads |
| Zerowallet runs `zero-fetch-params` | No second copy | Not in the Windows package; needs bash and curl or wget; no progress in the wallet |
| `zerod` downloads before `ZC_LoadParams()` | One implementation for all clients | libcurl and network code in node startup |
| Built-in Sapling parameters; Sprout file read only for Sprout proofs | No download for normal use | librustzcash and Rust update; binary about 49 MiB larger; Sprout spends still need 692 MiB |
| Files in the release packages | No download | Packages 741 MiB larger; `zerod` needs a search path |

References:

- `zerod` downloads: Pirate `src/params.cpp`, `checkParams()` and `downloadFiles()`, called before `ZC_LoadParams()`: libcurl transfers with resume, SHA-256, progress through the warmup messages; it hashes all files at every start.
- Built-in: zcashd 5.7.0, commit `dc5e4211a`. Crate `wagyu-zcash-parameters` 0.2.0 (data in `-1` to `-6`) feeds `zksnark_params()` in `src/rust/src/init.rs`; the Sprout Groth16 verifying key `sprout-groth16.vk` (1,828 bytes) is compiled in with `include_bytes!`; `prove()` in `src/rust/src/sprout.rs` opens `sprout-groth16.params` only to create a Sprout proof. Zebra does the same with `zcash_proofs` feature `bundled-prover`. Zero's librustzcash is pinned to commit `06da3b9`, and Linux builds use Rust 1.32.0 unless `RUST_USE_SYSTEM=1`.
- Packages: Hush `src/init.cpp` searches `.`, `/usr/share/hush`, `..`, `./Contents/MacOS/`, then `~/.zcash-params`.

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

Method: port the runner parts of Bitcoin Core `test/functional/test_runner.py` that answer these problems. `BASE_SCRIPTS` and `EXTENDED_SCRIPTS` as the one list per tier (Zero's pass tiers and Large); `NON_SCRIPTS` for helper modules; `check_script_list`, which fails when a Python file in the test directory is in no list, in place of the hand-regenerated CSV; `check_script_prefixes` for name prefixes (`wallet_`, `rpc_`, `p2p_`, `mempool_`, `feature_`); `--portseed` per job with `--jobs`, `--filter`, `--exclude`, and `--failfast`.

### Test speed

Serial `rpc-tests.sh -all` on ARM64 macOS takes 1,355 s: Tier A 98 s, Tier B 1,128 s, Tier E 129 s, with CPU busy 0.75 of one core, so the run mostly waits. Boost takes 88 s and GTest 47 s, in parallel with each other. Each RPC script prints its seconds, and `contrib/run-tests.sh` writes them to `<log dir>/<stamp>-rpc-times.csv`; measure each step below with a rerun.

**Waits.** Four 1 s waits:

| Wait | Code | Call sites | Change |
|------|------|------------|--------|
| Block and mempool sync | `sync_blocks`, `sync_mempools` (`wait=1`) in `test_framework/util.py` | About 300 | Poll every 0.1 s |
| Async operation | `wait_and_assert_operationid_status_result` (`time.sleep(1)`) | About 70 | Poll every 0.2 s |
| Node start | `wait_for_daemon_rpc` runs `zero-cli -rpcwait`, which retries every 1 s (`MilliSleep(1000)` in `src/bitcoin-cli.cpp`) | About 300 start and stop sites | Poll `getblockcount` from Python every 0.1 s |
| Zeronode sync | `zeronode_startalias` (105 s) waits for sync steps of `ZERONODE_SYNC_TIMEOUT` (5 s), about 25 s per asset (`src/zeronode/zeronode-sync.h`) | 1 script | Regtest-only shorter timers; node code |

**Fewer iterations.** 51 scripts start from an empty chain and mine 721 blocks to a spendable coinbase, then sync them to 2 to 4 nodes; mining takes 4.5 s on one node, the syncs and polls cost more. `mergetoaddress_helper.py` mines `generate(1000)`: check whether fewer blocks test the same input limit. `walletbackup` (62 s), `wallet_archive` (55 s), and `zapwallettxes` (19 s) restart nodes repeatedly and gain from the node-start change. `txn_doublespend` runs twice to cover two paths and stays.

**Concurrency.** `--jobs` in `contrib/run-tests.sh` runs only Tier A in parallel, one `rpc-tests.sh` per script. The stated `paymentdisclosure` hang under `--jobs` has no log or reproduction: run `./contrib/run-tests.sh --jobs=4` three times; keep the restriction only with a captured cause. Port offsets (`8 * pid % 2991`) do not collide for consecutive PIDs, and the script uses its own clean chain. With the CPU mostly idle and scripts under 2 GiB, extend `--jobs` to all pass tiers at 4 to 6 jobs. Shard GTest with `GTEST_TOTAL_SHARDS` and `GTEST_SHARD_INDEX`, and run the Boost RPC suites as separate `test_bitcoin --run_test=<suite>` processes, each with its own temporary directory.

**Cheaper setup.** Boost `TestingSetup` (`src/test/test_bitcoin.cpp`) loads a new wallet per case, and `LoadWallet` fills the keypool with `-keypool` keys (default 100, `TopUpKeyPool`), 0.58 to 0.62 s per case for 85 cases in the RPC suites. Time one case with `-keypool=1` set in the fixture; if it holds, set it. Use one fixture per suite where cases do not change shared state. Sapling proofs are real work and stay.

**Precomputed setup.** Add a second RPC test cache: a matured clean chain (height 721 or more, spendable coinbase) that clean-chain scripts copy as they copy the 725-block cache today.

**Tier moves.** Move `paymentdisclosure` (26 s), which tests an experimental feature that works only on Sprout JoinSplits, from Tier A to Tier B: the gate drops to 72 s. Seven scripts create Sprout notes (`paymentdisclosure`, `wallet_nullifiers`, `wallet_anchorfork`, `mergetoaddress_mixednotes`, `wallet_changeindicator`, `wallet_1941`, `regtest_signrawtransaction`; 177 s), as do the three GTests in `GTEST_SPROUT_PROOF` (`qa/zcash/test_filters.sh`): on ARM64 macOS they take about 178 of 265 CPU seconds and 3 GiB of 3.0 GiB peak RSS, and the rest of GTest runs in 22.5 s at 0.21 GiB beside Boost (83 s, 0.77 GiB). No run mode includes them; review after v4.1.0 whether to run them alone in the release run or drop them with the Sprout RPCs ("Sprout RPCs"); postponed. The scripts stay while wallets can create Sprout notes. Validation of existing Sprout spends stays tested either way.

**Measurement.** `contrib/run-tests.sh` records only RPC script seconds (`<stamp>-rpc-times.csv` in `.build/test-logs`), without the host or the C++ steps, so the 1,380 s serial `--all` RPC run on a small Linux host cannot be tied to its cores and memory. Add `<stamp>-host.txt` (`uname -srm`, core count, total memory, git head) and `<stamp>-steps.csv` (step, wall s, CPU s, peak RSS) from `/usr/bin/time -v` on Linux (package `time`) or `-l` on macOS, wall time only without it; then record one default and one `--all` run on each test host and quote figures with host and command; postponed.

**Order.** 1. Python polling for sync, operations, and node start, then rerun `-all`. 2. The `--jobs` reproduction. 3. The Boost keypool timing. 4. GTest sharding and split Boost suites in `contrib/run-tests.sh`. 5. The tier moves. 6. The matured-chain cache and the zeronode timers, sized from the measured savings.

Fixed costs: `getblocktemplate_longpoll` (71 s) waits out the long-poll timeout by design; `mergetoaddress_sapling` (105 s) builds Sapling proofs.

### Benchmark clarity

`zcbenchmark` (`src/zcbenchmarks.cpp`, help in `src/wallet/rpcwallet.cpp`) and miner limits. Measured on ARM64 macOS.

**Help.** List each type with unit (seconds, microsecond resolution), third parameter, network, and input; `verifyequihash` and `solveequihash` use MAIN (192,7) on every network.

**Defective types.** Fix or remove:

| Type | Defect | Measured |
|------|--------|----------|
| `parameterloading` | Error -3: Sprout parameters removed | -- |
| `validatelargetx` | Default 11,130 inputs is the Zcash 2 MB transaction; Zero's 200,000-byte limit (`MAX_TX_SIZE_COSMOS`) allows about 1,110. Setup grows with the square of the inputs | 1,000 inputs: 28 to 31 ms timed, 0.5 s wall; 11,130: 0.34 s timed, 51 s wall |
| `incnotewitnesses`, `incsaplingnotewitnesses` | The timed `ChainTip` takes the initial-download branch and only walks wallet notes; the Sapling variant times an empty block (second transaction added to `block1`) | 3, 26, 320 us at 100, 1,000, 10,000 transactions |
| `listunspent` | A fresh node has no outputs to list | 1 us |

**Sizing table.** Setup is untimed and can be 150 times the timed operation. After the fixes, generate a table for TEST_ZERO "Operational checks" from recorded samples: per type, the parameter and sample count (10, 100, or 1,000) that give timed samples between 100 ns and 10 s, wall time per sample, and peak RSS. `ops-validate.sh` records only exit code and whole-second duration; record each sample and sub-second times.

**Miner limits.** Warn or refuse in `GenerateBitcoins` (`src/miner.cpp`) when threads times the solver memory in README "Optional CPU mining" exceed physical memory; tromp checks cancellation only between rounds, so an out-of-memory miner does not stop.

**Tromp validation.** Tromp runs only in the miner at (192,7): `zcbenchmark` cannot select it, regtest is (48,5), and mainnet cannot mine in isolation (`nMinimumChainWork`, `fMiningRequiresPeers`). Validate on two connected testnet lab nodes, one mining with one tromp thread for 180 s (24 solver runs, 4 blocks) and one validating, and check every solution, not only those meeting the target. After v4.1.0, run README "Optional CPU mining" on a synced mainnet node with one thread and add it to TEST_ZERO "Release bar".

### Script precedence

Proposal, not decided: an environment variable overrides the matching command-line option, which overrides the default, so an operator can override options that scripts pass. No document states a rule now. Settings read from both sources, with the change the proposal implies:

| Setting | Environment | Option | Wins now | Change under the proposal |
|---------|-------------|--------|----------|--------|
| MXE root, `build-win.sh` | `MXE_ROOT` | `-m`, `--mxe` | environment | None in code; BUILD_ZERO "Windows" says `-m PATH` overrides `MXE_ROOT`, the reverse |
| Make jobs, `makeargs_from_argv` in `zcutil/fzero.sh` | `FZERO_MAX_JOBS` | `-jN` | option; the cap applies only without `-j` | An exported value also caps `-jN`; the built-in default 8 does not |
| C++ flags, `run_configure_native` in `build-native.sh` | `CXXFLAGS` in `CONFIGURE_FLAGS` | script `CXXFLAGS='-g'` after them | script | Pass `-g` before `$CONFIGURE_FLAGS`; update the BUILD_ZERO variable table |
| C++ flags and configure options, `run_configure_win` in `build-win.sh` | `CXXFLAGS`, `CONFIGURE_FLAGS` | script defines | script; both ignored | Append them after the required defines and options |
| Signing identity, `release-macos.sh` | `ZERO_CODESIGN_ID` | `--sign` | option | `SIGN_ID="${ZERO_CODESIGN_ID:-$2}"`; help text |
| Notary profile, `release-macos.sh` | `ZERO_NOTARY_PROFILE` | `--notarize` | option | Same form; help text |
| Snapshot, `contrib/ops-validate.sh` | `ZERO_OPS_SNAP` | `--snap=`, `snap=` | option | `SNAP` from the environment first, both forms |

Settings read from one source only need no change: `CC`, `CXX`, `MAKE`, `HOST`, `BUILD`, `PYTHON`, `MACOSX_DEPLOYMENT_TARGET`, `RUST_USE_SYSTEM`, `ZERO_LOG_KEEP`, the other `ZERO_OPS_*` variables, and the script-internal `VERSION_OVERRIDE`, `EXPECT_REF`, and `LOG_FILE`.

**Risk.** A stale export replaces a value a script or a documented command passes. Release builds: an exported `CXXFLAGS` changes the binaries (visible in `config.log`); an exported `ZERO_CODESIGN_ID` signs with another identity (visible in `codesign --verify`). The printed replacement line covers both.

**Verification.** On Linux: `build.sh -j2` with and without `FZERO_MAX_JOBS=1`, a native configure with `CONFIGURE_FLAGS="CXXFLAGS=-O1"` checked in `config.log`, `ops-validate.sh` with `ZERO_OPS_SNAP` set, and a Windows rebuild with `CXXFLAGS` exported. On macOS: `release-macos.sh` with `ZERO_CODESIGN_ID` and `--sign` both given.
