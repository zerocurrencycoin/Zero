# Zero v4.1.0

## Summary

Zero **v4.1.0** full node (`zerod`, `zero-cli`, `zero-tx`): improvement, bug-fix, and performance update to v4.0.0. Applies to upgrades from v4.0.0, v4.0.1 branch builds, v3.4.0, and v3.3.1: the block index, chain state, and wallet formats are unchanged since v4.0.0, and the index settings in the block index since v3.3.1.

## Upgrade actions

- Back up `wallet.zero` before upgrading. Build from the tag or use the release archives.
- `-blocknotify`, `-walletnotify`, and `-alertnotify` do not run in release builds; see CONTRIBUTING "Shell notify hooks".
- `-alerts` is removed with the P2P alert system: Zero never set a valid alert key, so no network alert could validate, and peers relaying alerts were penalized. An `alerts=` line in `zero.conf` is ignored. `-alertnotify` remains for this node's deprecation and long-fork warnings.
- `getalldata` clients: treat error -34 (`RPC_DATA_CONTINUE`) as "retry later". Omitting argument 2 (`transactiontype`) now returns the last 7 days; pass 0 for full history.
- Scripts that match message text: RPC errors and log lines say Zero instead of Zcash; `startalias` and `startzeronode` report "Zeronode list syncing, please wait. Current status: ..." while the zeronode list syncs.
- LevelDB keeps up to 256 table files per database open (64 before). On 64-bit hosts they are memory-mapped and hold no file descriptors.
- `contrib/zero.conf` has no `addnode=` lines; peers come from DNS seeds.

## RPC

- `getalldata`: argument 2 defaults to 7 days, and 0 returns up to 10 years. Soft error -34 while a call is in flight, or within `-rpcdatacontinue` seconds of the last success (default 20; 0 disables the time gate).
- A full RPC work queue returns HTTP 503 and logs one warning per episode; limit set by `-rpcworkqueue`.
- New `getdbinfo`: `-dbcache` budgets, live fill of the UTXO cache, and LevelDB block-cache capacity and statistics.
- `getrawtransaction` and `decoderawtransaction` help documents the `size` field.
- `zcrawjoinsplit` and `zcrawreceive` (Sprout raw JoinSplit RPCs) are removed, as in zcashd 5.4.0; a build with `-DENABLE_ZCRAW_RPC` restores them.

## Wallet

- Fixed a crash: the zs_* history RPCs and `getalldata`, called during `-reindex` or initial sync, could make the node crash later when it imported the blocks holding archived transactions.
- `getwalletinfo` adds `note_tx_count`, `sprout_note_count`, and `sapling_note_count`.
- Opt-in witness options `-walletwitness=<mode>` (`ibd-defer`, `rebuild`) and `-walletwitnessnote`; debug option `-walletwitnessstats`. Details: `zerod -help`.
- While the witness cache rebuilds, `stop`, `help`, `getblockcount`, `getblockchaininfo`, and `getnetworkinfo` remain available.
- Zeronode collateral lookup (zeronode activation and the zeronode RPCs) takes the chain lock before the wallet lock, the order the rest of the node uses, which removes a possible deadlock.

## Node startup and configuration

- An interrupted `-reindex` resumes from the last fully scanned `blk` file. A `reindex=` line in `zero.conf` produces a startup warning.
- A shutdown request during block index load at startup takes effect immediately.
- `contrib/zero-conf.sh` writes a `zero.conf` from `contrib/conf-templates/`; `--help` lists the templates.
- A new datadir records its index settings without starting a reindex; the settings and their reindex rule are in BUILD_ZERO "Datadir contents".
- Importing `bootstrap.dat` or `-loadblock` files logs blocks the node already has (one line per 1000) only with `-debug=reindex`, as in zcashd and Bitcoin Core.
- Script verification uses at most 4 threads (`-par`; 16 before). The startup line reads "Script verification uses N additional threads", counting worker threads besides the block-connecting thread (3 at the cap, 0 when checks run inline), as in Bitcoin Core.
- Transactions from peers refused by mempool policy (already spent, shielded requirements, fees, standardness) are logged one per line only with `-debug=mempool`, with the txid; the default log gets an hourly count per reason. A wallet transaction that fails to enter the mempool is logged with its txid and reason.

## Build, release, and tests

- Release archives for Linux, macOS, and Windows with one `SHA256SUMS` file.
- Test gate `./contrib/run-tests.sh --strict` and regtest founders window coverage.

## Compatibility

- Linux binaries run on the build OS or newer.
- Deprecation schedule: `getdeprecationinfo`.

## Verify download

- BUILD_ZERO "Release", "Verify a download".
