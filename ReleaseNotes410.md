# ReleaseNotes410 -- v4.1.0 release notes draft

**Status:** Draft body for the `v4.1.0` GitHub Release (candidates `v4.1.0-rcN`). Sections 1-2 are instructions; publish section 3 only.

---

## 1. Rules

- **Audience:** node operators, miners and pools, exchanges and integrators; contributors get pointers only.
- **Content:** state at v4.1.0 compared with v4.0.0, the last published release. End result only.
- **Include:** operator actions, user-visible behavior (RPC results, errors, options, conf), known breakage with a one-line workaround.
- **Point, do not copy:** economics -> ZERO_COIN; build, platforms, and download verification -> BUILD_ZERO; tests -> TEST_ZERO; open work -> TODO; documentation set -> README.
- **Never:** commit lists, maintainer documents, host names, tip heights or supply snapshots.
- **Test:** an item that would still be true for v4.1.1 without edits belongs in a standing document.

## 2. Maintenance

- Next release: new `ReleaseNotesNNN.md`; do not extend this file.
- Owner: release manager.

---

## 3. Release body

### Summary

Zero **v4.1.0** full node (`zerod`, `zero-cli`, `zero-tx`): improvement, bug-fix, and performance update to v4.0.0. Applies to upgrades from v4.0.0 and from v4.0.1 branch builds.

### Upgrade actions

- Back up `wallet.zero` before upgrading. Build from the tag per BUILD_ZERO, or use the release archives.
- `-blocknotify`, `-walletnotify`, and `-alertnotify` do not run in release builds; see BUILD_ZERO section 4.6.1.
- `-alerts` is removed with the P2P alert system: Zero never set a valid alert key, so no network alert could validate, and peers relaying alerts were penalized. An `alerts=` line in `zero.conf` is ignored. `-alertnotify` remains for this node's deprecation and long-fork warnings.
- `getalldata` clients: treat error -34 (`RPC_DATA_CONTINUE`) as "retry later". Omitting argument 2 (`transactiontype`) now returns the last 7 days; pass 0 for full history.
- Scripts that match message text: RPC errors and log lines say Zero instead of Zcash; `startalias` and `startzeronode` report "Zeronode list syncing, please wait. Current status: ..." while the zeronode list syncs.
- LevelDB opens up to 256 files per database; raise `ulimit -n` on hosts with a low limit.
- `contrib/zero.conf` has no `addnode=` lines; peers come from DNS seeds.

### RPC

- `getalldata`: argument 2 defaults to 7 days, and 0 returns up to 10 years. Soft error -34 while a call is in flight, or within `-rpcdatacontinue` seconds of the last success (default 20; 0 disables the time gate).
- A full RPC work queue returns HTTP 503 and logs one warning per episode; limit set by `-rpcworkqueue`.
- New `getdbinfo`: `-dbcache` budgets and live cache fill.
- `getrawtransaction` and `decoderawtransaction` help documents the `size` field.
- `zcrawjoinsplit` and `zcrawreceive` (Sprout raw JoinSplit RPCs) are removed, as in zcashd 5.4.0; a build with `-DENABLE_ZCRAW_RPC` restores them.

### Wallet

- Fixed a crash: the zs_* history RPCs and `getalldata`, called during `-reindex` or initial sync, could make the node crash later when it imported the blocks holding archived transactions.
- `getwalletinfo` adds `note_tx_count`, `sprout_note_count`, and `sapling_note_count`.
- Opt-in witness options `-walletwitness=<mode>` (`ibd-defer`, `rebuild`) and `-walletwitnessnote`; debug option `-walletwitnessstats`. Details: `zerod -help`.
- While the witness cache rebuilds, `stop`, `help`, `getblockcount`, `getblockchaininfo`, and `getnetworkinfo` remain available.

### Node startup and configuration

- An interrupted `-reindex` resumes from the last fully scanned `blk` file. A `reindex=` line in `zero.conf` produces a startup warning.
- A shutdown request during block index load at startup takes effect immediately.
- `contrib/zero-conf.sh` writes a `zero.conf` from `contrib/conf-templates/`; `--help` lists the templates.

### Build, release, and tests

- Release archives for Linux, macOS, and Windows with one `SHA256SUMS` file.
- Test gate `./contrib/run-tests.sh --strict` and regtest founders window coverage.

### Compatibility

- Linux binaries run on the build OS or newer.
- Deprecation schedule: `getdeprecationinfo`.

### Verify download

- See BUILD_ZERO, "Verify a download".

### Known limitations

- Release signing is a work in progress; see TODO REL-01.
