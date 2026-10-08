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

1. **Linux build** -- Build, test, and package at the release commit on the Ubuntu 24.04 build host.
2. **Windows build** -- Cross-build and package at the release commit on the Linux build host, then start `zerod.exe` once on Windows.
3. **Release signing** -- Decide checksums and signing per platform; method in progress.
4. **Release tags** -- Tag the release candidate and the release on `zero-410`; merge into `master`.

---

## Active

- **RPC dispositions** -- Decide the Sprout RPCs and record test depth per RPC from the harness in `doc/RPCs.csv`; the accounts RPCs stay deprecated until Zerowallet lists transparent addresses with `listreceivedbyaddress`.
- **Zeronode validation** -- Pass `zeronode_coinbase.py` and `zeronode_startalias.py` at the release commit; after v4.1.0, in order: registration success path on regtest, reorg test, automated `chainActive` checks, mainnet payment scan, public operator section in BUILD_ZERO.
- **Branch cleanup** -- Decide whether to squash commits before the `master` merge; deferred. List each branch with its merge and tag status before deletion.
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
- **Sapling root test** -- Fix `finalsaplingroot.py` and promote it from Bfail.

### Maintainer

RPC:

- **getalldata cost** -- Measure poll cost on a large wallet first, then the steps in Full descriptions.
- **RPC removal** -- Remove the code of RPCs that leave Zero, starting with the compiled-out Sprout raw JoinSplit RPCs; postponed; follows RPC dispositions.

Node operation:

- **Reindex safeguards** -- Refuse a `reindex=` line in `zero.conf` and an unforced `DB_FLAG` mismatch unless `-reindexforce`; skip the wallet replay below a height.
- **Tor compile-out** -- Add a `--disable-tor` configure option that compiles out Tor control; runtime onion is already off by default; keep it separate from I2P.
- **Address rate limit** -- Port the per-peer `addr` rate limit with its `getpeerinfo` counters from zcashd, as Pirate did, and add an RPC test; feelers and test-before-evict follow from Bitcoin Core.
- **Peer monitoring** -- Evaluate the monitoring examples and code of Bitcoin Core (tracepoints, message capture, log rate limit, `logging` RPC), zcashd (`setlogfilter`), and bmon first. Report connections and peer interactions for monitoring: counts by direction, connect, disconnect, and ban events with reasons, per-peer message and byte counters, and address-manager health, through RPC and a periodic summary line; per-event lines stay under `-debug=net`. Keep the `receive version message` line and `-logips` as they are.

Build, packaging, and release:

- **Params mirror** -- Verify file names and URLs of `fetch-params.sh`, record checksums, and keep a Zero-controlled copy.
- **Chain bootstrap** -- Document the end-user import path (`-loadblock`, auto-import), snapshot sourcing, and verification; linearize in `contrib/linearize/`.
- **Peer discovery** -- Review and improve how a new node finds peers: the DNS seed names in `vSeeds` (`src/chainparams.cpp`) and their records, a crawling seeder that publishes only live nodes, and the fixed-seed fallback (`contrib/seeds`, `chainparamsseeds.h`) filled from long-running nodes and refreshed each release.
- **CI workflows** -- Run the CI workflow on the release branch, run the full test set, and add macOS and Windows cross-build jobs; postponed.
- **LevelDB update** -- Update `src/leveldb` to LevelDB 1.22 as in Bitcoin Core and zcashd; restores block-cache usage in `getdbinfo`. Set 32 MiB table files (`max_file_size`, as Bitcoin Core and zcashd `DBWRAPPER_MAX_FILE_SIZE`) so the block index and chain state fit the table cache.

Documentation:

- **Setup runbook** -- Write the operator runbook in BUILD_ZERO: build, `fetch-params`, `zero.conf` RPC credentials, launch, ports.

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
