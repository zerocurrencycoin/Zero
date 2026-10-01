# Wallet witnesses

The Sapling/Sprout witness cache in `CWallet`: what it costs during sync and
rescan, the opt-in mechanisms that reduce that cost, the RPC gates that
protect it, and its behaviour under reorg and crash. Work items are
`PLAN.md` group A.

All figures are macOS/arm64, one host. Figures are bound to `M-*` ids in
`Measures.md`.

---

## 1. Cost

With a large wallet, sync and rescan time is dominated by the witness scan,
not by block validation. `ChainTip` calls `BuildWitnessCache(pindex,
witnessOnly=true)` on every block during IBD and reindex, and
`VerifyAndSetInitialWitness` walks all of `mapWallet` each time.

| Wallet | Reindex / rescan | Witness share of CPU | Id |
|--------|------------------|---------------------:|----|
| none, p0, p1 | ~918-1,000 blk/s, tiny snap | 0-0.32% | M-WAL-SYNC-P0, M-WAL-SYNC-P1 |
| fat (749 MB, 801,619 tx, 1,403 note-bearing = 0.175%) | ~19 blk/s, **~50x slower** | 72-99% | M-WAL-SYNC-FAT, M-CPU-WAL-FAT, M-WAL-NOTE-DENS |

`OrderedTxItems` is not the bottleneck; it is already incremental.

**Genesis `-rescan`, fat wallet** (M-WAL-RESCAN-FAT): 2,518,691 blocks in
~11.9 h. Above height 1,600,000 the rate falls to ~19 blk/s with
`SelectWalletTxsForWitnessScan` at ~98% of CPU. Cause: each founders coinbase
entered the wallet through `AddToWallet`, which invalidated the note index
unconditionally, so every block rebuilt it with an O(`mapWallet`) scan. That
figure predates the invalidation fix in section 3 and is due a remeasure
(`PLAN.md` A4). The end-of-rescan height walk is 2.0 s; follow-tip walks are
0-1 ms.

**Unmeasured:** no p1 rescan profile, so the curve between 0.32% and 72% is
unknown; no `many-utxo-few-tx` wallet exists to measure.

---

## 2. Mechanisms

Two opt-in flags, both default off. Each removes a different part of the
work.

| Flag | Removes | Does not remove | Measured |
|------|---------|-----------------|----------|
| `-walletwitness=ibd-defer` | The per-block Verify during IBD/reindex; one rebuild after `ThreadImport` | The tip rebuild and its `-33` window | ~35x to h15k (M-WAL-WITNESS-IBD-AB) |
| `-walletwitnessnote=1` (NOTEIDX) | Transparent txs from Verify and from the height walk | Per-block Verify frequency | ~33x to h8k (M-WAL-WITNESS-NOTEIDX-AB); tip walk 7,659 ms -> 220 ms (M-WAL-WITNESS-TIP-AB) |
| `-walletwitness=rebuild` | -- | -- | Forces a tip rebuild; operator/debug |
| `-walletwitnessstats` | -- | -- | Debug counters for the DIRTY question |

Call path with both off:

```
ChainTip / ThreadImport
+-- IsIBD && ibd-defer?  yes -> skip
|                        no  -> BuildWitnessCache(pindex, true)
|                                 -> VerifyAndSetInitialWitness   [NOTEIDX]
+-- near tip -> BuildWitnessCache(pindex, false)
|                 -> Verify [NOTEIDX] -> height walk [NOTEIDX], sets -33
+-- import end && (ibd-defer | rebuild) -> RebuildWitnessCacheForChainTip()
```

| Flags | IBD cost | Tip | `-33` window |
|-------|----------|-----|--------------|
| stock | Verify over `mapWallet` every block | occasional full rebuild | full rebuild |
| noteidx | Verify over note txs every block | rebuild walk over note txs | full rebuild |
| defer | ConnectBlock only | one rebuild at import end | that rebuild |
| defer + noteidx | ConnectBlock only | one rebuild, NOTEIDX walk | shortest |

**DIRTY** -- skipping already-validated notes inside Verify -- is parked.
Defer removes the surface it would act on, and the one lab sample
(`witness_lab.sh dirty-cont`, tiny snap) had `note_visits=0` because every fat
wallet note is post-Sapling. Reopen only if stock per-block Verify stays a
supported default and a post-Sapling sample shows a high early-continue rate.

---

## 3. The note index

`vNoteTxHashes` lists txids whose `mapSproutNoteData` or `mapSaplingNoteData`
is non-empty; `fNoteTxIndexStale` marks it for rebuild. `EnsureNoteTxIndex()`
rebuilds by one O(`mapWallet`) scan; `SelectWalletTxsForWitnessScan()` returns
the index when the flag is on and all of `mapWallet` when it is off. RAM cost
is `note_tx_count * 32` bytes (~45 KiB on the fat wallet); it is not persisted
and rebuilds on first use after load. `getwalletinfo.note_tx_count` reports
it.

**Invalidation rule, implemented** (`CWallet::HasNoteData`, `wallet.cpp`
`AddToWallet` / `EraseFromWallet`). The index is invalidated only when note
membership changes:

- load path: iff the loaded tx has notes;
- live insert: iff the new tx has notes;
- merge into an existing tx: iff it crosses empty/non-empty;
- erase: iff the erased tx had notes.

Transparent inserts, merkle/`hashBlock` merges and transparent erases no
longer invalidate. Covered by `WalletTests.NoteTxIndexTracksNoteBearingTxs`,
connect-style and disconnect-style `AddToWallet` in one test. The measure
gate is `PLAN.md` A4: in the post-1.6M band `Select` should fall from ~98%
and the rate leave the ~19 blk/s floor (M-WAL-RESCAN-FAT).

**Conditional follow-ups**, each only if a post-A4 profile shows it:

| Follow-up | Condition |
|-----------|-----------|
| Incremental `vNoteTxHashes` push/erase instead of rebuild | `Ensure` still visible in follow-tip or `importwallet` profiles |
| `DecrementNoteWitnesses` uses `Select` | Decrement walk still hot |
| Skip repeated `FindMyNotes` on an already-indexed tx | `FindMyNotes` / `AddToWallet` is the wall in the post-1.6M band |

Do not skip `AddToWallet` when `fExisted && fUpdate`: `-rescan` merkle updates,
`DisconnectTip` and conflict handling depend on that merge.

---

## 4. Ship state

The opt-in package (`ibd-defer` + `-walletwitnessnote=1`, defaults off) is
ready: help strings, Boost gates in `--strict` including the allowlist,
Tier B `wallet_witness_defer.py` R1/R2/R5a/R5b/R7b, post-Sapling tip rebuild
measured. Release note text:

```
Opt-in wallet witness flags (defaults off):
  -walletwitness=ibd-defer
      Skip per-block witness build during IBD/reindex; rebuild once after import.
  -walletwitnessnote=1
      Witness scan (Verify + height walk) iterates note-bearing txs only.

While witnesses are unbuilt or rebuilding:
  -31  z_sendmany / getalldata until initial witnesses exist
  -33  wallet/spend/data RPCs while a full tip rebuild runs
Status RPCs remain available under -33: stop, help, getblockcount,
getblockchaininfo, getnetworkinfo.

Clients should retry -31/-33. Do not assume spends work until rebuild finishes.
Recommended together for fat wallets: ibd-defer + -walletwitnessnote=1.
```

Tests that gate it:

| Test | Covers |
|------|--------|
| `rpc_witness_building_cache_blocks_all_rpc` | -33 on `z_sendmany`, `getsupply`, `getalldata`, `getwalletinfo` with the flag forced |
| `rpc_witness_building_cache_allows_status_rpc` | Allowlist dispatches; does not prove the calls return during a real walk |
| `rpc_getalldata_s5_witness_gate` | -31 before first build |
| `rpc_witness_gate_allows_walletinfo_when_unbuilt` | Monitoring while -31 |
| `rpc_walletinfo_note_inventory_fields` | NOTEIDX counters |
| `wallet_witness_ibd_defer_arg` | `IsIBDWitnessDeferred()` |
| `WalletTests.NoteTxIndexTracksNoteBearingTxs` | Invalidation rule, section 3 |
| `wallet_witness_defer.py` (Tier B) | R1/R2 spend after import and rebuild; R5a, R5b, R7b |

**Default-on gate:** the opt-in exit above, plus the A4 remeasure, plus the
flag collapse below.

**Flag collapse**, after A4:

| Surface | Proposed |
|---------|----------|
| Flags | One `-walletwitness=stock|defer|rebuild`; drop `-walletwitnessnote`, NOTEIDX always on |
| Stats | Hidden (`-debug=witness`), not a product flag |
| Wallet state | One `WitnessReady { NotBuilt, Building, Ready }` replacing `initWitnessesBuilt` + `fBuildingWitnessCache` |
| RPC codes | Unchanged: -28 warmup, -31 unbuilt, -32 zeronodes, -33 rebuilding |

---

## 5. RPC gates

Two independent gates in `CRPCTable::execute`:

| Gate | Set when | Blocks | Error |
|------|----------|--------|-------|
| `!initWitnessesBuilt` | Witnesses never built, or cleared for a full rebuild | `z_sendmany`, `getalldata` | **-31** |
| `fBuildingWitnessCache` | Height walk only (`witnessOnly=false`), after Verify | Every RPC except the allowlist | **-33** |

`-33` never fires on the per-block IBD path. During stock fat IBD the
practical stall is `cs_wallet` held in Verify, not `-33`. The allowlist under
`-33` is `stop`, `help`, `getblockcount`, `getblockchaininfo`,
`getnetworkinfo`, checked deny-by-default by name; adding a name is the risky
change. `getblockcount` still stalls on `cs_main` for the length of the walk.

**Policy, and why it differs from the siblings.**

| Project | Unbuilt | During rebuild |
|---------|---------|----------------|
| Zero | -31 on `z_sendmany` + `getalldata` | -33 on all but the allowlist |
| Pirate | -31 on `z_sendmany` (+ offline prepare) | all RPC frozen, code -32 |
| Ycash | -31 on `z_sendmany` | all RPC frozen, code -32 |
| TENT | -31 on `z_sendmany` | no freeze; spends can race a rebuild |
| zcashd | none | none; incremental witnesses, different wallet model |

- Keep -33 for rebuild. Zero's -32 is `RPC_ZERONODES_NOT_SYNCED`; Pirate's and
  Ycash's -32 is Zero's -33.
- Do not copy TENT's no-freeze: a deferred tip rebuild needs mid-flight
  protection.
- Do not copy zcashd's no-lockout until witnesses are incremental.
- The allowlist replaces Pirate's global freeze so monitors and `stop` work
  during a long rebuild.

The broader question of one shared RPC gate keyed by name is `PLAN.md` C5;
the `getalldata` gate inconsistency is `PRODUCT.md` "P4. The witness RPC gate
is inconsistent, and the family disagrees about it".

---

## 6. Reorg and crash

Witness state is tied to tip height. A reorg calls `DecrementNoteWitnesses`,
which pops one witness layer per disconnected block.

| Mode | Required behaviour | Test | State |
|------|-------------------|------|-------|
| Reorg in the defer window | Stay unbuilt; rebuild on the new tip | R5a | Covered |
| Reorg after built, depth 1/3/10/20 | Decrement matches depth; spends work | R5b | Covered |
| Process killed mid-rebuild | Restart does not spend until rebuilt | R7b | Covered |
| Decrement unit edges | Keep last layer; skip above disconnect height | GTest `DecrementNoteWitnessesSkipsAboveHeight` | Covered |
| Reorg during the height walk | Walk aborts or restarts; `initWitnessesBuilt` never set on a partial walk | R5c | **Not reachable**: the walk holds `LOCK2(cs_main, cs_wallet)` throughout, so a reorg waits for it. Needs `PLAN.md` A6 first |
| Reorg deeper than `MAX_REORG_LENGTH` | Node stays up, tip unchanged, warning logged | R5d | **Open**: today it calls `StartShutdown()`; reject-and-stay (TNT-02) is not scheduled |

**Crash paths.** Chainstate and wallet are separate databases with no
cross-DB commit. `SetBestChainINTERNAL` writes note-bearing txs,
`nWitnessCacheSize` and the best-block locator in one BDB transaction;
transparent `AddToWallet` writes per tx. After a crash the wallet locator
drives a rescan. A null `pindex` calls `exit(1)` in `DecrementNoteWitnesses`,
`VerifyAndSetInitialWitness` and `BuildWitnessCache` (`wallet.cpp:1263`,
`:1329`, `:1674`), skipping the `Shutdown()` flush; replacing them with
rebuild-or-clear recovery is `PLAN.md` A5. SIGKILL cannot
be caught; recovery after it is restart plus whatever reached disk.

**Recovery modes** for A5: soft (decrement only); rebuild
(`RebuildWitnessCacheForChainTip` when a note lacks a usable witness); hard
clear (`ClearNoteWitnessCache` + rebuild on logged inconsistency, instead of
`exit(1)`); RPC stays -31 until rebuilt and -33 while rebuilding.

**Cache size versus reorg cap.** `WITNESS_CACHE_SIZE = MAX_REORG_LENGTH + 1`
(100 slots, apply bound 99). The cache must never be shorter than the apply
cap: an applied reorg deeper than the cache empties the deque while the node
treats the reorg as legal. Raising the cap toward coinbase maturity (720)
means growing the deque or accepting rebuild on deep reorg; that is `PLAN.md`
A8, after A5.
