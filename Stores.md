# Zero data structures and local stores

Updated: 2026-07-08

## Purpose

This page is the lifecycle and preservation map for Zero local stores. It answers: what is unique, what is regenerable, what should be backed up, and which document owns deeper implementation or operational detail.

Reviewed local documents:

- `Peer.md`
- `Runtime.md`
- `../Zero400/ZeroStruct.md`
- `Perf.md`
- `doc/files.md`
- `../Zero400/doc/files.md`
- `../Zeros/ZEROV.md`

Reviewed online references:

- Zcash data directory file list: https://zcash.readthedocs.io/en/latest/rtd_pages/files.html
- ZIP 400 wallet data format: https://zips.z.cash/zip-0400
- Zcash zcashd deprecation: https://z.cash/support/zcashd-deprecation/
- Zallet wallet: https://zcash.github.io/wallet/
- Bitcoin Core addrman overview: https://bitcoincore.academy/addrman.html
- Bitcoin Core wallet database overview: https://bitcoincore.academy/wallet-database.html
- Bitcoin Core 26.0 wallet migration note: https://bitcoincore.org/en/releases/26.0/
- Zcash issue on BDB 6.2.23 to 6.2.32: https://github.com/zcash/zcash/issues/2413
- Zcash forum SQLite/BDB wallet discussion: https://forum.zcashcommunity.com/t/evaluate-sqlite-as-a-replacement-for-bdb/38321

## Current Accuracy Summary

`doc/files.md` and `../Zero400/doc/files.md` are the most accurate compact inventories for Zero's data directory. They correctly use `wallet.zero`, not `wallet.dat`.

`Runtime.md` is the active structure document for node architecture, cache split, LevelDB key families, Insight index behavior, RPC inventory, and client requirements. It also carries the detailed `getaddrmaninfo` / `getrawaddrman` port candidate because that is an RPC/API concern.

`../Zero400/ZeroStruct.md` is a branch-local copy and should not be treated as the current source of truth unless work is explicitly happening on that branch. It was intentionally left at its branch state after the 2026-07-08 review.

`../Peer.md` is the canonical local note for `peers.dat`, addrman behavior, peer discovery, and practical peer monitoring. `Runtime.md` should not duplicate the whole peer treatment, but it should summarize the lifecycle and link back to `../Peer.md`.

`Perf.md` is the current authority on sync-performance experiments (plans/specs in §0.13). It is performance-oriented, not a data-directory map, but it matters for classifying `blocks/index/`, `chainstate/`, and the optional Insight indexes by lifecycle and rebuild cost.

**Shutdown and stores:** orderly exit runs `Shutdown()` -- wallet `Flush`, `FlushStateToDisk` (chainstate / block index), LevelDB/BDB close, optional zeronode/budget dumps. That work is why stop/Ctrl+C can take seconds to minutes on a large tip or fat wallet. **Windows (operator observation):** Ctrl+C does **not** exit immediately; treat the delay as store update / teardown unless `debug.log` shows an abrupt kill without `Shutdown: In progress...`. SIGHUP `debug.log` reopen is POSIX-only; Windows log rotate = stop/start or copy while stopped (`Perf.md` §0.8).

`../Zeros/ZEROV.md` has been reframed as a superseded transition note. Its old recommendation to target BDB 18.1.40 should not drive current wallet work. The safer current framing is compatibility first, explicit migration second, and no hard dependency upgrade tied to node/index/performance work.

## Document Partition

| Question | Owner | Boundary |
|---|---|---|
| What stores exist, what is unique, what can be regenerated? | `Stores.md` | Lifecycle, preservation, cleanup, cross-store terminology |
| How does `zerod` use stores at runtime? | `Runtime.md` | Flags, cache split, RPCs, client requirements, block-connect/index maintenance |
| How does peer discovery and `peers.dat` really work? | `../Peer.md` | Addrman internals, logs, DNS seeds, recovery procedure, external peer-analysis tools |
| What should be ported or implemented? | `UpdateZero.md` | Work plans, acceptance criteria, task IDs |
| Why not simply upgrade BDB? | `../Zeros/ZEROV.md` plus this file | `ZEROV.md` is the superseded note; `Stores.md` has current wallet-store stance |

## Stores By Lifecycle And Purpose

| Path | Store kind | Lifecycle | Purpose | Recovery / rebuild | Preserve? |
|---|---|---|---|---|---|
| `blocks/blk*.dat` | Flat block files | Append-only local block archive | Raw block data | Can be redownloaded or imported from bootstrap files; expensive but not unique | Preserve for speed, not uniqueness |
| `blocks/rev*.dat` | Flat undo files | Written with connected blocks | Undo data for disconnect/reorg | Rebuilt by full `-reindex`; not user-unique | Preserve if keeping a synced node |
| `blocks/index/` | LevelDB, `CBlockTreeDB` | Rebuilt by `-reindex` | Block tree, txindex, optional Insight indexes, persisted flags | Rebuild from `blk*.dat`; enabling Insight requires reindex in practice | Regenerable but expensive |
| `chainstate/` | LevelDB, `CCoinsViewDB` | Current validated state | UTXO set plus Sprout/Sapling anchors and nullifiers | Rebuild with `-reindex-chainstate` from indexed blocks or full `-reindex` | Regenerable but expensive |
| `wallet.zero` | Berkeley DB | User/key state | Keys, wallet transactions, note metadata | Keys cannot be reconstructed from chain; use backup/salvage/rescan | Must preserve if it contains value |
| `database/`, `db.log` | BDB environment/logs | Wallet DB runtime environment | BDB environment and logs paired with wallet use | Do not copy a live wallet partially; clean shutdown or wallet backup preferred | Preserve with active wallet until understood |
| `peers.dat` | Custom serialized `CAddrMan` | Periodic peer-cache dump | Known peer addresses and addrman buckets | Delete/rename if corrupt; node recreates from DNS seeds, fixed seeds, gossip, `addnode` | Useful but regenerable |
| `fee_estimates.dat` | Serialized runtime estimates | Runtime policy cache | Fee/priority estimates | Recreated during operation | Regenerable |
| `zncache.dat` | Serialized zeronode cache | Operational cache | Zeronode broadcasts/state | Recreated from network and config, with operational delay | Usually regenerable |
| `.cookie` | Text auth token | Created at startup, removed on shutdown | Local RPC authentication | Ephemeral | Do not preserve |
| `onion_private_key` | Private key file | Stable Tor identity | Tor hidden-service identity for `-listenonion` | Delete only if intentionally changing onion identity | Preserve when Tor identity matters |
| `debug.log` | Text log | Append/truncate by config | Diagnostics and forensic timing | Not required for node operation | Preserve only for investigations |

## Index Families And Write Lifecycle

`blocks/index/` is the block-tree LevelDB. It holds the always-present block index, `txindex` when enabled, persisted index flags, and the optional Insight address/spent/timestamp/hash indexes. The exact key-prefix table belongs in `Runtime.md` section 3 because it is source-level node implementation detail.

`chainstate/` is not an address index. It stores current validation state keyed for consensus checks: UTXOs, Sprout/Sapling anchors, and nullifiers. The current ZeroPerf branch also adds existence-style anchor checks down to LevelDB `Exists()` for the same keys; the performance rationale belongs in `Perf.md`.

The Insight indexes are written during `ConnectBlock` when `-insightexplorer` is enabled. They live in `blocks/index/`, not in a separate explorer database. They support transparent-address explorer RPCs only; they do not provide a chain-wide shielded-address view.

External indexers such as Blockbook or a custom syncer should be treated as separate consumers with their own stores. They can use Zero RPC/ZMQ and generally need `txindex`, but they do not require Zero's embedded Insight indexes unless their API specifically depends on those RPCs.

`wallet.zero` is not a chain-wide index. It is an owner-specific state database. Rescan can reconstruct wallet transaction visibility from keys plus chain data, but rescan cannot reconstruct missing private keys.

`peers.dat` is a P2P bootstrap/cache structure, not an authoritative network database. It accelerates reconnects and improves peer diversity, but a missing or corrupt file is operationally recoverable.

## Peers.dat Decoding And Recovery

Bitcoin and Zero share the same broad addrman model: an in-memory peer address manager with "new" and "tried" buckets, periodically dumped to `peers.dat`. Bitcoin Core documentation describes it as a cache used to avoid bootstrapping from scratch after restart. Zero's `Peer.md` owns the local source layout, serialization wrapper, DNS seed behavior, logging, and recovery details.

Tools found:

| Tool / method | Ecosystem | Usefulness | Fit for Zero/Zcash-family work |
|---|---|---|---|
| `getpeerinfo` | Bitcoin, Zcash-family RPCs | Live connected peers | Available and safe, but does not dump addrman |
| `getrawaddrman`, `getaddrmaninfo` | Newer Bitcoin Core | Full addrman observability | Not present in Zero400/ZeroPerf; good candidate to port |
| addrman.observer | Bitcoin Core | Visualizes `getrawaddrman` output | Useful only after porting/exporting addrman JSON |
| peer-observer | Bitcoin research infra | Monitoring, metrics, anomaly detection | Heavy; not drop-in for Zero |
| Bitcoin-Core-Peer-Map | Bitcoin Core | Geo/ASN peer dashboard | Could inspire a Zero dashboard, but RPC assumptions differ |
| `bitpeers` / Raghav Sood peers.dat work | Bitcoin | Dumps older Bitcoin `peers.dat` formats | Useful as format study, likely brittle for forks/newer formats |
| JaredTate `peersparser` | Bitcoin/DigiByte | Simple binary scan for IP addresses | Exploratory only; not a trustworthy recovery parser |

No maintained Zcash-specific `peers.dat` decoding/recovery tool turned up. Zcash support material treats `peers.dat` failures mostly as operational startup/sync problems: fix permissions, delete or recreate the peer cache, and let the node bootstrap again.

Recommended Zero recovery procedure:

1. Stop `zerod`.
2. Move `peers.dat` aside rather than editing it in place.
3. Restart with normal DNS/fixed seeds, or use `addnode` / `seednode` / `forcednsseed` if bootstrap is weak.
4. Preserve the moved file only if diagnosing peer-discovery behavior.

Recommended Zero tooling:

1. Port `getaddrmaninfo` and `getrawaddrman` from Bitcoin Core before writing bespoke binary parsers. The detailed adaptation assessment belongs in `Runtime.md` section 6.4.
2. Add a small offline `zero-peers-dump` only if porting RPCs is too invasive.
3. Keep peer forensics separate from wallet recovery tooling.

## Berkeley DB, Wallet Compatibility, And Local DB Direction

Zero's wallet file is `wallet.zero` by default. Source confirms `-wallet` defaults to `wallet.zero`, wallet load/save messages mostly say `wallet.zero`, and the generated file inventories use `wallet.zero`. A few source help/test strings still say `wallet.dat`, including `-salvagewallet` help and some benchmark/test fixtures. Those are documentation/string drift, not the runtime default.

Upstream Zcash documentation and ZIP 400 describe `wallet.dat` as a Berkeley DB key-value database with wallet records such as keys, scripts, transactions, and note metadata. ZIP 400 also notes that wallet migration generally depends on moving the database through a compatible `zcashd` version and may require reindex/rescan.

Bitcoin Core has moved in a different direction: legacy Berkeley DB wallets remain a compatibility concern, but new descriptor wallets use SQLite, and Bitcoin Core 26 added GUI migration from legacy BDB wallets to descriptor SQLite wallets. The Bitcoin Core wallet database guide describes the bundled BDB version as unmaintained and recommends SQLite for new wallets.

Zcash's current ecosystem direction is also not "upgrade the C++ wallet to newest BDB and continue." zcashd is being deprecated, full-node work is moving toward Zebra, and Zallet is the Rust full-node wallet replacement. The 2021 Zcash discussion around SQLite already framed this as part of a split between wallet logic and storage rather than a simple BDB library bump.

Zcash's BDB 6.2.23 to 6.2.32 issue is useful as a caution: micro-version upgrades inside the same BDB minor line may be less risky than major jumps, but BDB log/recovery behavior and wallet compatibility still need explicit testing.

Practical Zero guidance:

- Do not treat BDB 18.1.40 as the current target simply because it appears in `ZEROV.md`.
- Preserve BDB compatibility for existing `wallet.zero` files before any store modernization.
- Keep wallet-store migration separate from node-performance, block-index, and Insight-index work.
- Add reliable export/import paths before changing wallet storage. Key/seed export and verified restore matter more than database fashion.
- If a new store is introduced, treat it as a wallet architecture change with migration tooling, not a dependency bump.

## Current Sync State

| Area | State |
|---|---|
| `Runtime.md` | Current for ZeroPerf node structure and runtime behavior; uses `wallet.zero`; points here for lifecycle/preservation classification |
| `../Zero400/ZeroStruct.md` | Branch-local copy; not updated by this partitioning pass |
| `Zeros/ZEROV.md` | Superseded transition note; retained only to explain why BDB 18.1.40 is not the current plan |
| Source help strings | Some user-facing strings still say `wallet.dat` where Zero means `wallet.zero`; fix during source cleanup, leave test fixtures alone unless they affect docs |

## Expected Benefits Of The Structured View

This classification prevents three recurring confusions:

1. Wallet state vs. regenerable node state. `wallet.zero` is preservation-critical; `chainstate/`, `blocks/index/`, and `peers.dat` are operationally useful but rebuildable.
2. Embedded indexes vs. external indexers. Zero's Insight keys live in `blocks/index/`; Blockbook-style stores live outside Zero and should be planned separately.
3. Store modernization vs. dependency modernization. Moving away from BDB is not merely a library upgrade; it is a migration and compatibility problem.

It also gives a cleaner lifecycle vocabulary for cleanup and archiving:

- Preserve: user keys, wallet backups, unique experiment notes, source branches.
- Preserve for speed: block files and current indexes when disk allows.
- Regenerate: chainstate, block index, peer cache, fee estimates.
- Rebuild intentionally: Insight indexes, external explorer DBs, performance profiles.
- Delete freely when stale: temp logs, failed scratch datadirs, transient generated caches.

## Open Work

1. Decide whether `../Zero400/ZeroStruct.md` remains an actively maintained copy or should be frozen in favor of `Runtime.md`.
2. Fix the user-facing `-salvagewallet` help string in source if a source cleanup pass is opened.
3. Scope a `getrawaddrman` / `getaddrmaninfo` port for Zero.
4. Verify `txindex` defaults in `Zero400` separately before claiming the ZeroPerf default for all active branches.
5. Consider a small table in cleanup docs distinguishing preservation-critical wallet files from regenerable node stores.
