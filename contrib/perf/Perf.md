# `zerod` sync performance: current understanding, and next steps

**Groth16** now lives in **[PerfGroth.md](PerfGroth.md)**; **task state** in **`docs/TASKS.md`**. This file keeps findings and method.

This document holds the **performance findings for block connection**: where
sync time goes, which of those costs were investigated, and what changing them
did or would do. A subject appears here only where its cost during sync is the
point -- Equihash verification is here because it is 6-28% of ConnectBlock CPU,
while how the solver works belongs to `equ/`. It carries no task state; that is
`docs/TASKS.md`, and placement generally is `docs/POLICY.md` S2.0a.

**New to benchmarking this node?** Read **`docs/HOWTO.md`** first -- this file is the investigation narrative and assumes the workflow is already familiar. Data provenance for every recent number: `test-logs/DATA_INDEX.md`.

**Quantitative inventory** (`M-*` campaigns, vocabulary, comparability, extraction, ledger `CAMPAIGN=` map): **[Measures.md](Measures.md)** -- cite IDs only here; means/stdevs live there. This file keeps optimization narrative, **BENCH-/FIX-/IMP-***, baseline tracks **L0-L7**, Stages 0-6, priorities **G**/**P1-P4**, Groth decision, and **lab materials** (§1). Doc-map, lab discipline, and harness inventory: **`docs/POLICY.md`**.

**Program: recreate the ConnectBlock / import performance baseline** so Groth and other decisions sit on current measured numbers. Already-shipped product work with tests stays in the tree (§3 fd-cache, §4 root latch + anchor index, reindex resume, ExtTests **B1** `reindex_shielded`, founders integer subsidy, FIX-LBI/IMPORT). **Baseline tracks** (§0.13 F **L0-L7**): tiny/short, pre-Sap reindex+bootstrap, post-Sap reindex+bootstrap, era segments, util; then Groth decision inputs. FDCACHE 4x2 postponed. Accounts/W5 pending review.

**ID note:** ExtTests **B1** (`reindex_shielded`) is unrelated to baseline track **L1**. Do not reuse bare B0-B7 for lab tracks.

## 0. Wallet-on reindex: the witness bottleneck

Task state for everything below is `docs/TASKS.md`.

**Settled:** With a large `mapWallet`, IBD/reindex wall is dominated by per-block `BuildWitnessCache(..., witnessOnly=true)` -> `VerifyAndSetInitialWitness` -- **not** by `OrderedTxItems` (WAL-WTXORDERED already incremental). Evidence: M-WAL-SYNC-FAT / M-CPU-WAL-FAT; archive `test-logs/archives/walletsync-fat-g0-20260812.tar.gz`. Genesis `-rescan` on the same Id 3 fat wallet (M-WAL-RESCAN-FAT) is the same Verify path, not ConnectBlock: **finished** 2,518,691 blocks in ~**11.9 h**; cliff at height **1600000** (Halving 2 / founders payee) to ~**19 blk/s** with Select **~98%**; end height-walk **2.0 s**. Next product: **FIX-WAL-WITNESS-NOTEIDX-STALE**.

**Lab flags (opt-in, not default):**
- `-walletwitness=ibd-defer` -- skip per-block IBD `BuildWitnessCache`; rebuild once after `ThreadImport` (M-WAL-WITNESS-IBD-AB ~**35x** to h15k).
- `-walletwitness=rebuild` -- force tip rebuild after import (ungates getalldata).
- `-walletwitnessnote=1` -- **NOTEIDX** (note-bearing tx index): Verify + height walk iterate note txs only (M-WAL-NOTE-DENS **0.175%**; M-WAL-WITNESS-NOTEIDX-AB ~**33x** to h8k without defer).

**Call path (stock):** `ChainTip` IBD branch -> `BuildWitnessCache(pindex, true)` every block -> `VerifyAndSetInitialWitness` over `mapWallet`. With NOTEIDX, Verify walks `vNoteTxHashes` (~1403) after one index build.

**Util sampler:** `wallet_sync_profile.sh` -- `WALLETINFO_TIMEOUT_S` (default 5) so fat `cs_wallet` contention cannot stall `util.tsv`.

#### Mitigation assessment

Effort bands: **S** small, **M** medium, **L** large (no calendar estimates). Impact = expected fraction of the ~50x fat gap closable if the hypothesis holds.

##### FIX-WAL-WITNESS-IBD -- skip/throttle during IBD

| Axis | Assessment |
|------|------------|
| **Idea** | During `IsInitialBlockDownload` (and/or `-reindex` import), do **not** call `BuildWitnessCache` every block; rebuild once when leaving IBD (or every N blocks / at tip). Near-tip path (`BuildWitnessCache(pindex, false)`) unchanged. |
| **Impact** | **High** if almost all of the 97% stack is avoidable until tip -- potential return toward empty-wallet blk/s class for ConnectBlock-bound work (Equihash/disk/tree). Residual: still need one rebuild at tip (cost once, not per block). |
| **Complexity** | **Low-med**. Policy change in `ChainTip` + ensure `initWitnessesBuilt` / spend RPCs stay gated until rebuild completes (existing `initWitnessesBuilt` already gates some paths). |
| **Effort** | **S** for flag prototype; **M** to productize (RPC/docs: z_sendmany unavailable until catch-up; tests). |
| **Risk** | **Med**. Spends/migration during IBD already restricted; must not leave `initWitnessesBuilt` true with empty/wrong witnesses; reorg during deferred rebuild; operators expecting spend-while-syncing. |
| **Status** | **Prototype measured** -- `-walletwitness=ibd-defer` + post-import `RebuildWitnessCacheForChainTip`. |

**Shipped sketch:** `IsIBDWitnessDeferred()` in `ChainTip`; import-end rebuild in `ThreadImport`. Productize: default-or-opt-in, `reindex_shielded` with flag, kill/restart.

##### FIX-WAL-WITNESS-NOTEIDX -- note-bearing tx index

| Axis | Assessment |
|------|------------|
| **Idea** | Maintain note-bearing txid list; `VerifyAndSetInitialWitness` iterates that set, not all `mapWallet`. |
| **Impact** | **High** on golden fat: **1403 / 801619 (0.175%)** note txs (M-WAL-NOTE-DENS). A/B ~**33x** (M-WAL-WITNESS-NOTEIDX-AB). |
| **Complexity** | **Med**. Stale flag + Ensure rebuild. Remaining: stale is too broad (FIX-WAL-WITNESS-NOTEIDX-STALE). |
| **Effort** | Prototype **done**; height walk **done** (shared `SelectWalletTxsForWitnessScan`). Stale narrowing **S**. |
| **Risk** | **Low-med**. Missed invalidate -> skipped note -> spend failure. |
| **Status** | **Shipped in tree** -- Verify + height walk; e2e `wallet_witness_defer.py` green; gtest Select A/B. Stale storm on transparent AddToWallet **open**. |

**What NOTEIDX does** (`-walletwitnessnote=1`):

- `vNoteTxHashes` + `fNoteTxIndexStale`; `EnsureNoteTxIndex()` / `SelectWalletTxsForWitnessScan()`.
- Invalidate on **note-membership** change only (FIX-WAL-WITNESS-NOTEIDX-STALE). **Today** every `AddToWallet` / `EraseFromWallet` invalidates.
- Used by **`VerifyAndSetInitialWitness`** and the **`BuildWitnessCache` height walk** (`witnessOnly=false`).
- Measured IBD: ~33x blk/s (M-WAL-WITNESS-NOTEIDX-AB). Walk logs `BuildWitnessCache height-walk begin/done` with `scan_txs` + `elapsed_ms`.

**Lifecycle and size**

| Event | Index behavior |
|-------|----------------|
| Process start / new `CWallet` | `fNoteTxIndexStale=true`, `vNoteTxHashes` empty |
| `LoadWallet` | Stale stays true from ctor; invalidate only if the loaded tx has notes (STALE). Today every load Add invalidates. |
| First `VerifyAndSetInitialWitness` with flag on | `EnsureNoteTxIndex()`: full `mapWallet` scan once -> fill vector |
| Later Verify while not stale | Walk vector only (O(note_tx)) |
| Transparent `AddToWallet` / `EraseFromWallet` | **STALE:** do not invalidate. Today: invalidate |
| Note insert / note erase / empty-to-nonempty `UpdatedNoteData` | Invalidate; next Ensure rebuilds |
| Restart | Not persisted; rebuild on first Ensure after load |
| Flag off | Vector unused; Verify walks all `mapWallet` |

**Size (RAM, not disk):** `vector<uint256>` ~= `note_tx_count * 32` bytes + vector capacity slack. Golden fat: **1403** note txs -> ~**45 KiB** hashes (negligible vs ~785 MB wallet). `getwalletinfo.note_tx_count` is the live cardinality signal. Cost spike = **one** O(`mapWallet`) Ensure after a real membership change; steady Verify with a hot index is O(note_tx). Unconditional `AddToWallet` invalidate makes that spike **per involving block** (M-WAL-RESCAN-FAT-CPU). `ibd-defer` skips ChainTip Verify, not `-rescan`.

##### FIX-WAL-WITNESS-NOTEIDX-STALE

Narrow when `InvalidateNoteTxIndex` runs. Ready to implement; do not change Select/Ensure/walk algorithms.

**Yes: skipping transparent txs is most of the work.** NOTEIDX already omits transparent txs from Verify and the height walk. The remaining cost is `EnsureNoteTxIndex` rebuilding `vNoteTxHashes` by scanning all of `mapWallet` whenever `fNoteTxIndexStale` is set. On the Id 3 fat wallet that flag is set on every founders coinbase after height **1600000** (Halving 2 / founders slot rotation): about one `AddToWallet` per block, then per-block Verify. Time Profiler in that band: `SelectWalletTxsForWitnessScan` **~98%**, **~19 blk/s** (M-WAL-RESCAN-FAT). Those coinbases have empty note maps. Not invalidating on transparent Add/Erase removes that Ensure. Remaining invalidates are note-bearing inserts, note-bearing erases, and empty-to-nonempty note-map merges -- **1403 / 801619 (0.175%)** on this golden, not per-block. Incremental `push_back`/`erase` on the vector is optional and not required for the win.

**Defect.** `AddToWallet` calls `InvalidateNoteTxIndex()` before insert/merge, including `fFromLoadWallet`, no-op merges (`fInsertedNew` and `fUpdated` both false), and transparent txs. `EraseFromWallet` invalidates for every erased txid. `EnsureNoteTxIndex` is then O(`mapWallet`) on the next `SelectWalletTxsForWitnessScan`. Callers of Select: `VerifyAndSetInitialWitness` (every `BuildWitnessCache`) and the `witnessOnly=false` height walk (once per rebuild, Select once at walk start).

**Note membership.** A txid is a member of `vNoteTxHashes` iff `mapSproutNoteData` or `mapSaplingNoteData` is nonempty (`EnsureNoteTxIndex` loop). Membership **changes** when a note-bearing tx is inserted, a note-bearing tx is erased, or an existing tx goes empty to nonempty via `UpdatedNoteData`. Membership **does not change** for transparent insert/update/erase, merkle/`hashBlock` merge on an existing tx, or note-field merges that stay nonempty. `UpdatedNoteData` treats incoming empty note maps as unchanged and does not clear existing notes, so nonempty-to-empty via merge is not a current path; still treat `hadNotes != hasNotes` after merge as the update rule.

**How to tell the tx is already in `mapWallet`.** `AddToWalletIfInvolvingMe` already has `fExisted = mapWallet.count(tx.GetHash()) != 0`. `AddToWallet` (non-load) uses `mapWallet.insert` -> `fInsertedNew = ret.second` (`false` means already present). That does not skip Ensure by itself. Ensure returns immediately only when `!fNoteTxIndexStale`. Skipping Ensure means **do not set stale** on that call. Do not skip `AddToWallet` entirely on `fExisted` during `-rescan` (`fUpdate=true`); merkle merge still runs. Optional later: skip AddToWallet when `fExisted && !fUpdate`. Not this patch.

**Proposed rule.** Helper (name flexible): `HasNoteData(const CWalletTx&)` true iff either note map is nonempty. Keep `InvalidateNoteTxIndex()` as `fNoteTxIndexStale = true`.

`AddToWallet` `fFromLoadWallet`: invalidate iff `HasNoteData(wtxIn)`. `CWallet` already starts stale; a transparent-only load leaves stale true until the first Ensure (empty vector). A note tx loaded after an Ensure mid-load still invalidates.

`AddToWallet` live path: compute `hadNotes = !fInsertedNew && HasNoteData(wtx)` **before** merge; run existing insert/merge including `UpdatedNoteData`; then `hasNotes = HasNoteData(wtx)`. Invalidate iff `fInsertedNew ? hasNotes : (hadNotes != hasNotes)`.

`EraseFromWallet`: if `it` found, `bool notes = HasNoteData(it->second)` **before** `mapWallet.erase`; invalidate iff `notes`.

Do not invalidate at the top of `AddToWallet`. Flag off (`-walletwitnessnote` unset): Select ignores the vector; stale writes are harmless. Still apply the rule so a later flag-on restart is not required for correctness of in-process toggle (flag is startup-only today).

**Walk logs.** Per-block rescan/IBD uses `BuildWitnessCache(pindex, true)` and returns after Verify -- **no** walk lines. Walk exists only on `witnessOnly=false`:

- `BuildWitnessCache height-walk begin scan_txs=%d mapWallet=%d noteidx=%d startHeight=%d tip=%d`
- `Building Witnesses for block %i %.4f complete` every 100 heights until near tip
- `BuildWitnessCache height-walk done scan_txs=%d elapsed_ms=%d tip=%d`

`-rescan` from genesis calls `BuildWitnessCache(tip, false)` at the **end** of `ScanForWalletTransactions`, still under RPC warmup (`-28 Rescanning...`). Warmup is checked before `fBuildingWitnessCache` (`-33`). Operators will not see `-33` for that inner walk.

`startHeight` is `VerifyAndSetInitialWitness` return + 1. `SaplingWitnessMinimumHeight` only lowers that floor for notes with `GetSaplingSpendDepth <= WITNESS_CACHE_SIZE` (100): unspent (depth 0) or spent in the last 100 blocks. Spent-long-ago notes do not pull the walk, even if they sit in the 1403 note-tx index. Initials are set at birth during the per-block `true` pass; the end walk only increments from that min height to tip.

**Measured (M-WAL-RESCAN-FAT):** end walk `startHeight=2505881` `tip=2518691` (~12.8k blk) `scan_txs=1403` `noteidx=1` **2009 ms**. Not a genesis-to-tip rebuild and not the rescan wall. P2P catch-up `2518692-2518993` **42 ms**. Follow-tip walks **0-1 ms**. `-walletwitness=rebuild` after `Done loading` did not log a second long walk (witnesses already at tip). Contrast M-WAL-WITNESS-TIP-AB (~1441 blk, 220 ms noteidx vs 7659 ms stock). `scan_txs=1403` with `noteidx=1` means the index was hot. `scan_txs=801619` means flag off or Select walked all of `mapWallet`.

**Affected behaviors**

| Path | Today | After patch |
|------|-------|-------------|
| `-rescan` + NOTEIDX + Id 3 fat (founders every block after 1.6M) | Ensure O(mapWallet) per involving block; Select ~98% CPU | Transparent AddToWallet does not stale; Select O(note_tx); one Ensure after load |
| Stock IBD `ChainTip` `witnessOnly=true` + same wallet | Same storm from 1.6M if Verify runs every block | Same win; defer still skips Verify entirely |
| `ibd-defer` IBD | Verify skipped; stale still set; one Ensure at tip rebuild | Stale less often; tip Ensure still once if any note tx arrived |
| Near-tip `ChainTip(..., false)` follow-tip | Founders block: AddToWallet stale + Verify + walk; Ensure O(mapWallet) every block if NOTEIDX on | Transparent coinbase does not stale; walk Select stays O(note_tx) |
| `LoadWallet` | 801k invalidates (already stale) | Invalidate only on the 1403 note txs; first Ensure unchanged |
| `DeleteWalletTransactions` -> `EraseFromWallet` | Invalidate even for transparent deletes (`fDeleteInterval`) | Invalidate only if the erased tx had notes |
| New shielded receive / `z_sendmany` result | Invalidate (correct) | Unchanged: insert has notes |
| `UpdatedNoteData` finds notes on an existing transparent tx | Invalidate already (unconditional) | Invalidate iff empty -> nonempty |
| Zap / `importwallet` / dump rescan | Storm like `-rescan` | Transparent-heavy wallets cheap; note inserts still stale once each |
| Flag off | Vector unused | No Select change |
| Spend / witnesses | Risk = missed stale on a new note tx | Tests below; do not skip invalidate on `HasNoteData` insert |

**Not this patch:** `ibd-defer`; DIRTY; skipping PoW verify/`ReadBlockFromDisk` on rescan; clearing witnesses without `-rescan`; RPC `-28` vs `-33` ordering; `FIX-WIT-WALK-UNLOCK`.

**Tests.** Extend `WalletTests.NoteTxIndexTracksNoteBearingTxs` (or a sibling). After a hot index (`Ensure`, stale false, size 0 or 1). **One gtest, both `AddToWallet` flavors** -- do not split STALE and disconnect-style merge into a later PR.

Connect-style (`pblock` set / live insert-or-merge, same as `ConnectTip` `SyncWithWallets(tx, pblock)`):

1. Live `AddToWallet` transparent (`fFromLoadWallet=false`) -> stale stays false, size unchanged.
2. `EraseFromWallet` that transparent tx -> stale stays false.
3. Live `AddToWallet` with nonempty `mapSaplingNoteData` -> stale true; Ensure size += 1; Select with flag on returns that txid.
4. `EraseFromWallet` that note tx -> stale true; Ensure size -= 1.
5. Existing transparent tx, `AddToWallet` merge with `UpdatedNoteData` adding a Sapling map entry -> stale true.
6. Existing note tx, merge that keeps maps nonempty (merkle/`hashBlock` only) -> stale stays false.

Disconnect-style (`pblock` null, `fUpdate=true`, same as `DisconnectTip` / conflicted / mempool `SyncWithWallets(tx, NULL)`):

7. Existed transparent, incoming `hashBlock` null -> merge no-ops; stale stays false.
8. Existed note tx, same NULL merge -> stale stays false (membership unchanged). Decrement is a separate call; this case only covers `AddToWallet`.

Keep: load-path transparent then Ensure size 0; load-path note then Ensure size 1; Select A/B flag on/off.

Do **not** add skip-`AddToWallet` on `fExisted && fUpdate` in this PR. That skip already exists for `!fUpdate` and is unused on `SyncTransaction`. Skipping merge when `fUpdate` is true is a different product change (breaks `-rescan` merkle and disconnect accounting).

**Third skip -- when it would ever be justified.** Two skips already exist or are specified:

1. `AddToWalletIfInvolvingMe`: `fExisted && !fUpdate` returns without `AddToWallet`. Used by `importwallet` (default `fUpdate=false`). Unused on `SyncTransaction` / `-rescan` (both pass `fUpdate=true`).
2. STALE: do not `InvalidateNoteTxIndex` on transparent Add/Erase. This is the founders-cliff fix (new involving txs still enter `AddToWallet`; they must not rebuild `vNoteTxHashes`).

A third skip -- do not call `AddToWallet` when `fExisted && fUpdate` -- is **almost never justified**. Callers that pass `fUpdate=true` need the merge: `-rescan` merkle/`hashBlock`, `DisconnectTip` `SyncWithWallets(tx, NULL)` (merkle not updated; conflict/depth on the fly), mempool-to-confirm, conflicted. The founders cliff is **first insert** of new transparent involving txs (`fInsertedNew`); skipping existed+update does not touch that path. After STALE, remaining cost inside `AddToWallet` for an already-present transparent tx is `FindMySproutNotes` / `FindMySaplingNotes` (still run when `fUpdate`) plus a no-op merge (`WriteToDisk` only if `fInsertedNew || fUpdated`).

Schedule a third skip **only if** post-STALE Time Profiler in the post-1.6M band still shows `FindMyNotes` / `AddToWallet` as the wall. The candidate then is narrower than "skip AddToWallet": skip repeated `FindMyNotes` on an already-indexed tx when keys have not changed. Do not skip the merge. Do not put either form in Cycle 1.

**Incremental `vNoteTxHashes` -- later.** After STALE, `EnsureNoteTxIndex` runs on real note-membership changes only (insert/erase/empty-to-nonempty), not per founders block. One O(`mapWallet`) scan per new shield is acceptable on this golden (1403 notes over the wallet's life vs millions of Ensures during fat `-rescan`). Incremental `push_back` / erase makes that Ensure O(1) but must stay consistent with load, zap, `EraseFromWallet`, and flag-off. Schedule after Cycle 1 rematch **if** Ensure still appears in follow-tip or `importwallet` profiles. Not required for the 19 blk/s cliff.

Boost/regtest: R8 is this gtest. Fat `-rescan` rematch is a lab measure (M-WAL-RESCAN-FAT), not CI. R5b (1/3/10/20) covers Decrement + spend, not NOTEIDX stale.

**Measure gate.** Repeat M-WAL-RESCAN-FAT-CPU after 1.6M with the patch: Select should fall from ~98% toward the pre-cliff mix (Verify + `GetSaplingSpendDepth` / `GetDepth`, not Ensure). Height rate should leave the ~19 blk/s floor if Ensure was the bound. Do not compare to ConnectBlock ~300 blk/s.

**Campaign conclusions.** M-WAL-RESCAN-FAT, confirmed finished.

- The wall is `ScanForWalletTransactions` (per-block `BuildWitnessCache(pindex, true)` + `AddToWalletIfInvolvingMe`), ~**11.9 h** to height **2518691**. The end `witnessOnly=false` walk is **2.0 s** on this wallet; follow-tip is **0-1 ms**. Do not optimize or productize around a long post-rescan walk for Id 3.
- NOTEIDX already keeps Verify/walk on **1403** note txs. The ~**19 blk/s** floor after height **1600000** is Ensure rebuilding that index because every founders coinbase `AddToWallet` invalidates it. Those coinbases have empty note maps. **FIX-WAL-WITNESS-NOTEIDX-STALE** is the remaining NOTEIDX completeness item.
- `ibd-defer` does not apply to `-rescan`. Stock IBD `ChainTip` with the same wallet hits the same storm unless defer skips Verify or STALE lands.
- `1403` is this wallet's note-bearing txs, not chain-wide Sapling density (M-DENS). Walk `startHeight` is min witness height among unspent/recently-spent notes, not oldest note-tx birth.
- Lab pid still following tip after `Done loading`. Do not copy `wallet.zero` back to the live datadir; do not `z_sendmany` on the lab copy.

**Recommended actions**

1. **Cycle 1:** FIX-WAL-WITNESS-NOTEIDX-STALE + gtest R8 (connect-style and disconnect-style `AddToWallet` in the same suite). Do not fold in skip-`AddToWallet` on `fUpdate`, WALK-UNLOCK, incremental `vNoteTxHashes` `push_back`, or `ibd-defer`.
2. Rematch M-WAL-RESCAN-FAT-CPU in the post-1.6M band (measure gate above). Optional: one full `-rescan` after STALE if the CPU rematch is ambiguous. Same cycle, not a separate product PR.
3. After rematch: flag collapse below (NOTEIDX default; drop `-walletwitnessnote`). Keep `ibd-defer` opt-in until the existing default-on gate.
4. **Cycle 2:** Decrement no `exit(1)` + recovery. **TNT-02** reject-and-stay is not scheduled (keep 99 + exit). Not TENT follow, not Zebra-1000. See §0.16 cycles.

| Axis | Assessment |
|------|------------|
| **Idea** | Invalidate NOTEIDX only on note-membership changes. |
| **Impact** | **High** on founders-dense / any wallet with involving txs in most blocks (M-WAL-RESCAN-FAT). |
| **Complexity** | **Low**. Two call sites + helper; gtest. |
| **Effort** | **S**. |
| **Risk** | **Med** if a note insert path skips invalidate -- spend/witness skip. Gtest required. |
| **Status** | **Specified** -- Cycle 1. |

#### Flag and RPC collapse

Today the witness surface is three flags, three bools, and four RPC codes. Collapse after Cycle 1 rematch, in the same validation window -- not a year of one-flag PRs.

**Flags now**

| Flag | Role |
|------|------|
| `-walletwitness=` empty / `ibd-defer` / `rebuild` | Per-block Verify vs skip-until-tip vs force rebuild |
| `-walletwitnessnote=0/1` | NOTEIDX on Verify + height walk |
| `-walletwitnessstats` | Lab-only CONT counters |

**Proposed**

| Surface | After collapse |
|---------|----------------|
| One flag | `-walletwitness=` `stock` / `defer` / `rebuild`. `stock` = current default (per-block Verify). `defer` = today's `ibd-defer`. `rebuild` unchanged. |
| NOTEIDX | Always on once STALE lands. Drop `-walletwitnessnote`. Without STALE, default-on NOTEIDX re-hits the Ensure storm. |
| Stats | Keep hidden (`-debug=witness` or undocumented). Not a product flag. |
| Wallet bools | One enum `WitnessReady { NotBuilt, Building, Ready }` instead of `initWitnessesBuilt` + `fBuildingWitnessCache`. `fNoteTxIndexStale` stays private; never an RPC field. |
| RPC codes | Keep **-28** (warmup), **-31** (unbuilt), **-32** (zeronodes -- do not steal), **-33** (rebuilding). Do not add a code for rejected-reorg; put it on `getblockchaininfo` `errors` / warnings. Status allowlist stays the five names. Do not copy Pirate freeze-all-RPC. |

Clients already retry `-31` and `-33`. Collapsing those two into one `RPC_WALLET_NOT_READY` would save a code and break Zerowallet if it keys on the number. Keep both.

**Not this collapse:** DIRTY flag, `-maxreorg` (Cycle 3), WALK-UNLOCK.

| Axis | NOTEIDX (Verify + walk) |
|------|-------------------------|
| **Impact** | **High** IBD (~33x); tip rebuild walk no longer O(mapWallet) per height |
| **Effort** | **Done** |
| **Risk** | **Low-med** (invalidate correctness) |

#### Interaction: IBD, defer, NOTEIDX, DIRTY, height walk

```
ChainTip / ThreadImport
|
+-- IsIBD && ibd-defer?
|     yes -> skip BuildWitnessCache this block
|     no  -> BuildWitnessCache(pindex, witnessOnly=true)   # per-block IBD
|              -> VerifyAndSetInitialWitness  [NOTEIDX scan]
|              -> return (no height walk, no -33)
|
+-- !IsIBD (near tip) -> BuildWitnessCache(pindex, false)
|                          -> Verify [NOTEIDX]
|                          -> height walk [NOTEIDX]  # sets -33
|
+-- import end && (ibd-defer|rebuild) -> RebuildWitnessCacheForChainTip()
                                         -> BuildWitnessCache(tip, false)  # full path
```

| Mechanism | Removes work from | Does not remove |
|-----------|-------------------|-----------------|
| **NOTEIDX** | Transparent txs in Verify **and** height walk | Per-block Verify frequency; Ensure O(mapWallet) while stale (FIX-WAL-WITNESS-NOTEIDX-STALE); already-validated note visits |
| **ibd-defer** | Entire per-block Verify during IBD | One tip rebuild (Verify + walk) + `-33` window |
| **DIRTY** (not built) | Would remove validated-note visits inside Verify | Height-walk appends; useless if defer skips Verify |
| **Height walk** | Needed once to advance witnesses from initial height to tip | -- |

**Combinations**

| Flags | IBD cost | Tip / post-import | When `-33` |
|-------|----------|-------------------|------------|
| stock | Verify every block over `mapWallet` | occasional full rebuild | full rebuild only |
| noteidx | Verify every block over note txs (~0.175%) | full rebuild walk over note txs | full rebuild only |
| defer | ~ConnectBlock only | one full rebuild at import end | that rebuild |
| defer+noteidx | ~ConnectBlock only | one full rebuild, NOTEIDX walk | that rebuild (shortest) |

**DIRTY vs defer:** if product default is defer, DIRTY's surface (per-block Verify) is gone -- **park DIRTY**. NOTEIDX walk is the tip-rebuild optimization.

##### FIX-WAL-WITNESS-DIRTY -- differential initial-witness set

**What DIRTY means:** NOTEIDX skips *transparent* txs; DIRTY would skip *already-validated notes* too.

**INV-DIRTY-CONT** (`-walletwitnessstats=1`): logs `WitnessStats ... note_visits= early_continue= full_work=` per Verify. Runner: `contrib/perf/witness_lab.sh dirty-cont`.

**Lab result (tiny, stock+NOTEIDX, to h~11k):** `scan_txs=1403` / `mapWallet=801619` (NOTEIDX live). **`note_visits=0`** -- all golden notes are Sapling (activation 492850); tiny tip 187417 is pre-Sapling, so `GetDepthInMainChain()==0` for every note tx during this band. Early-continue rate **not measurable** on tiny. Meaningful CONT needs a **post-Sapling** height window (full/short past 492850) -- L wall; only if stock per-block Verify remains a product default.

**DIRTY recommendation:** **Park.** Defer product path + pre-Sap CONT null result. Do not prototype unless post-Sap CONT shows high early_continue **and** stock Verify stays default.

**Automation vs one-time**

| Lab | Automation | Cadence |
|-----|------------|---------|
| INV-DIRTY-CONT | `witness_lab.sh dirty-cont` (reusable) | **One-time** decision sample per chain band; not CI |
| BENCH-WIT-REBUILD | `witness_lab.sh rebuild` / `rebuild-noteidx` | **One A/B pair** before default-on; re-run when walk/flags change; not CI |
| e2e R1/R2 | `wallet_witness_defer.py` (Tier B) | **Every** relevant change / Tier B |

#### Recommended order

1. **G0b hygiene** -- **done**.
2. **G0c / NOTEIDX density + A/B** -- **done** (0.175%; ~33x). Walk **done**. **FIX-WAL-WITNESS-NOTEIDX-STALE** Cycle 1 (specified).
3. **G0d IBD defer A/B** -- **done** (~35x).
4. **DIRTY** -- still optional (tip-rebuild asymptotics).
5. **Productize** -- decisions in §0.14; execute §0.15 Tier A (docs -> NOTEIDX walk -> RPC allowlist -> rebuild bench -> regtest -> opt-in ship -> default-on gate).
6. **G0e** fat@tiny getalldata -- **done** (scoped); full-mainnet Idx1 open (Tier B).

#### RPC lockout during witness operations

Two independent mechanisms in `CRPCTable::execute` (`rpc/server.cpp`):

| Gate | When | What is blocked | Error |
|------|------|-----------------|-------|
| `!initWitnessesBuilt` | Witnesses never finished / cleared for full rebuild | **`z_sendmany`**, **`getalldata` only** | **-31** `RPC_DISABLED_BEFORE_WITNESSES` |
| `fBuildingWitnessCache` | Set only in `BuildWitnessCache` **after** Verify, when `witnessOnly=false` (height-walk rebuild) | **All** RPC methods | **-33** `RPC_BUILDING_WITNESS_CACHE` |

**When `-33` actually fires:** not on the per-block IBD `witnessOnly=true` path (Verify returns before `fBuildingWitnessCache=true`). Fires on near-tip full rebuild, `-walletwitness=rebuild`, and post-`ibd-defer` import rebuild. During stock fat IBD the practical stall is **`cs_wallet` held in Verify** (util sampler / wallet RPCs block), not the global `-33` flag.

**Peer comparison** (local sibling trees, out of tree)

| Project | Pref-init / never-built | During full rebuild | Error codes | Notes |
|---------|-------------------------|---------------------|-------------|-------|
| **Zero** | `-31` on **`z_sendmany` + `getalldata`** if `!initWitnessesBuilt` | **All** RPC if `fBuildingWitnessCache` | **-31**, **-33** | Clears `initWitnessesBuilt` for full rebuild; sets building flag only on `witnessOnly=false` path |
| **Pirate** | `-31` on **`z_sendmany` + `z_sendmany_prepare_offline`** if `!fInitWitnessesBuilt` | **All** RPC if `fBuilingWitnessCache` (typo upstream) | **-31**, **-32** | Same global freeze idea; Zero renumbered building to **-33**. PIR-03 source. |
| **Ycash** (`YCASH_WR`) | `-31` on **`z_sendmany` only** | **All** RPC if `fBuildingWitnessCache` | **-31**, **-32** | Same Pirate/WR family shape; no `getalldata` gate |
| **TENT** | `-31` on **`z_sendmany` only** if `!initWitnessesBuilt` | **No** building flag / no all-RPC freeze | **-31** only | `BuildWitnessCache` walks `mapWallet` like Zero but never sets a mid-rebuild lockout; ends by setting `initWitnessesBuilt=true`. Spends can race a long rebuild. |
| **zcashd** (modern) | No `-31`/`-33` in `execute()` | No global witness freeze | N/A | Incremental `IncrementNoteWitnesses` on notify; different wallet model -- not a drop-in policy template for Zero's `BuildWitnessCache` |

**Error codes: do not add witness to `-32`**

| Code | Zero (`protocol.h`) | Pirate / Ycash |
|------|---------------------|----------------|
| **-31** | `RPC_DISABLED_BEFORE_WITNESSES` | same meaning (spend until init) |
| **-32** | **`RPC_ZERONODES_NOT_SYNCED`** (zeronode layer) | `RPC_BUILDING_WITNESS_CACHE` |
| **-33** | `RPC_BUILDING_WITNESS_CACHE` | (unused / different) |
| **-34** | `RPC_DATA_CONTINUE` (getalldata soft) | -- |

Zero already occupies **-32** for zeronodes. Remapping witness rebuild onto `-32` would collide with `RPC_ZERONODES_NOT_SYNCED` and break clients that key on that code. **Keep witness rebuild at `-33`.** When comparing docs/logs to Pirate/Ycash, treat their **-32** as Zero's **-33**. Clients should match on message substring and/or Zero's `-33`, not assume Pirate numbering.

**Recommendation (justified)**

1. **Keep `-31` / `-33` as today** -- do not invent a third witness code; do not steal `-32`.
2. **Keep `-31` for spends + Zero `getalldata`** -- matches Pirate/Ycash spend safety; getalldata is Zero-specific note History.
3. **Do not copy TENT** (no rebuild freeze) -- fat tip rebuild under defer needs mid-flight protection.
4. **Do not copy zcashd's "no lockout"** until incremental witnesses exist.
5. **Diverge from Pirate global freeze:** keep `-33` for wallet/spend/data; **allowlist** `stop`, `help`, `getblockcount`, `getblockchaininfo` (optional net/uptime). Not `getwalletinfo` / `z_*` / `getalldata`.
6. **Shrink the window** with NOTEIDX walk + defer, not by dropping `-33`.

**Implications**

1. **Correctness:** Spend/data gates prevent half-built note use; allowlist must stay non-wallet.
2. **Availability:** Global Pirate freeze makes fat tip rebuild look like a dead node; allowlist fixes monitors/`stop`.
3. **NOTEIDX:** Shortens Verify and (once walk extended) height-walk -- reduces `-33` duration without changing policy.
4. **Clients:** `-33` = retryable soft-outage; `-31` = not ready. Document both.
5. **Self-DoS only:** remote peers cannot set the flag.

**Risk assessment**

| Risk | Severity | Likelihood | Notes |
|------|----------|------------|-------|
| Spend with stale witnesses if freeze removed carelessly | **High** | Low if keep spend gates | Do not adopt TENT "no `-33`" |
| Ops blind during rebuild (all RPC down) | **Med** | **High** on fat rebuild | Allowlist status/ops |
| IBD util/RPC stall via `cs_wallet` (no `-33`) | **Med** | **High** on stock fat sync | Mitigated by ibd-defer / NOTEIDX |
| Comparison.md / PIR prose lag ("z_sendmany only") | **Low** | Certain | Code == Pirate global; docs catch up here |
| Productizing defer without documenting spend delay | **Med** | Med | `initWitnessesBuilt` false until rebuild finishes |

**Product direction:** allowlist as above + NOTEIDX walk + ibd-defer package. **TST-08 done**.

#### Tests

| Test | Covers |
|------|--------|
| `rpc_witness_building_cache_blocks_all_rpc` | `-33` on `z_sendmany`, `getsupply`, `getalldata` (TST-08 + global freeze) |
| `rpc_getalldata_s5_witness_gate` | `-31` on getalldata/z_sendmany |
| `rpc_witness_gate_allows_walletinfo_when_unbuilt` | Monitoring while `-31` |
| `rpc_walletinfo_note_inventory_fields` | NOTEIDX-related counters |
| `wallet_witness_ibd_defer_arg` | `IsIBDWitnessDeferred()` |
| `WalletTests.NoteTxIndexTracksNoteBearingTxs` | NOTEIDX stale/rebuild; extend for STALE (transparent must not stale) |

Lab notes also under gitignored `test-logs/witness-defer-test-plan.md`.

#### Companion hygiene (not FIX-WAL-WITNESS-*)

| Item | Change | Validation |
|------|--------|------------|
| Util sampler | `WALLETINFO_TIMEOUT_S` (default 5) | Fat util.tsv advances |
| `bucket_profile.py` (local `reindex-profile/tools/`) | `witness_cache` before `wallet_add_ordered` | Rebucket ~97% / ~0.03% |

#### What "productize" means here

Lab prototypes prove a speedup under opt-in flags on disposable datadirs. **Productize** = turn that into something operators get without knowing lab knobs -- with defaults, docs, tests, and failure modes that match production use.

| Layer | Lab today | Productize checklist |
|-------|-----------|----------------------|
| **Defaults** | Flags off; stock path still ~50x fat | Choose default on / opt-in / compile-time; document spend-unavailable-until-rebuild |
| **Completeness** | NOTEIDX Verify + height walk done; **stale too broad** | FIX-WAL-WITNESS-NOTEIDX-STALE before calling NOTEIDX done |
| **RPC policy** | Pirate-style global `-33` | Keep vs allowlist status RPCs (`getblockcount`, `stop`, ...) -- §0.14 lockout |
| **Tests** | Boost 46/46 exclusive + NOTEIDX gtest | Add regtest: defer through import -> rebuild -> spend; reorg during defer; kill/restart mid-rebuild |
| **Ops docs** | `contrib/perf/README`, Perf §0.14 | Release notes / help text; Zerowallet retry on `-31`/`-33` |
| **Measure gate** | h~8k / h~15k A/Bs | One fat tiny-to-tip (or agreed band) with product flags; compare tip rebuild wall vs stock |
| **Exit criteria** | Prototype A/B green | Default (or shipped opt-in) + tests in `--strict` + no silent witness skip |

Not productize: leaving `-walletwitness=*` as undocumented lab-only forever; shipping defer without documenting that `initWitnessesBuilt` stays false until post-import rebuild.

#### Productize decisions

Recommended answers (open until you override). Rationale under each.

| Question | Recommendation | Why |
|----------|----------------|-----|
| **Defaults** | **Two-step:** (1) ship **documented opt-in** (`ibd-defer` + `noteidx`); (2) flip **default on** only after regtest + rebuild/tip gate | Spends already `-31` until witnesses built, so defer mostly moves when witnesses appear -- but default-on without tip rebuild wall and kill/restart coverage is the wrong first cut. Empty wallets unchanged either way. |
| **Completeness** | **Require FIX-WAL-WITNESS-NOTEIDX-STALE** so Ensure is not per transparent AddToWallet; walk already uses Select | IBD/rescan/follow-tip on founders-dense wallets otherwise pay O(mapWallet) Ensure every block (M-WAL-RESCAN-FAT) |
| **RPC policy** | **Keep `-33` for wallet/spend/data RPCs; allowlist chain/ops:** `stop`, `help`, `getblockcount`, `getblockchaininfo`, `getnetworkinfo`. **Do not** allowlist `getwalletinfo` / `getalldata` / `z_*` during rebuild. Zero has **no** `uptime` RPC. | Matches correctness need (no half-built note reads) and fixes "node looks dead" for monitors. Pirate global freeze is the wrong ops default once defer concentrates rebuild at tip. |
| **Tests** | Opt-in ship: Boost allowlist + R1/R2/R5a (Tier B). **Default-on:** R5b/R7b + kill/restart. R5c is **FIX-WIT-WALK-UNLOCK** (product), not a missing e2e. | Flag unit tests do not prove ChainTip/import coupling. |
| **Ops docs** | **Always with ship** (PROD-WIT-DOCS): help text, `-31`/`-33` retry, "no spend until rebuild finishes" | Cheap; prevents false "node hung" reports. |
| **Measure gate** | **BENCH-WIT-REBUILD required** before default-on; **BENCH-WIT-TIP optional** (one combined `defer+noteidx` trial, not 4-way) | Rebuild isolates `-33` duration. Partial-height A/Bs already prove IBD; tip is confirmation, not discovery. |
| **DIRTY** | **Park** while productizing defer; run INV-DIRTY-CONT only if stock per-block Verify stays a supported default | Defer removes DIRTY's payoff surface; see DIRTY section. |
| **Exit (opt-in)** | Flags in help + docs + Boost in `--strict` + no silent skip | Shipable without flipping defaults. |
| **Exit (default-on)** | Opt-in exit + PROD-WIT-REGTEST + BENCH-WIT-REBUILD + NOTEIDX walk | Then remove "lab only" language. |

**Combo to ship:** treat `ibd-defer` + NOTEIDX as one product package (docs/tests shared). `-walletwitness=rebuild` stays operator/debug.

### 0.16 Reorg-sharp, opt-in ship, RPC/load, denser lab

#### Reorg-sharp

**Meaning:** Witness cache state is tied to chain tip height (`witnessHeight`, front-of-deque witnesses, `witnessRootValidated`). A reorg disconnects blocks and calls `DecrementNoteWitnesses`, which pops one witness layer when `witnesses.size() > 1` and clears validation flags via other paths. Bugs or incomplete updates here are **sharp** -- wrong root -> spend fail / assert-class failure; missing decrement -> stale witness; over-clear -> forced rebuild. DIRTY sets (if ever built) are especially sharp: must re-dirty notes whose witnesses were popped. With **ibd-defer**, a reorg *during* deferred IBD (witnesses not yet built) is a different mode than a reorg *after* tip rebuild.

**Failure modes to gate**

| Mode | Hazard | Desired recovery |
|------|--------|------------------|
| Reorg while deferred (pre-rebuild) | Spends still `-31`; no half-built cache | Stay unbuilt; rebuild at import end on new tip |
| Reorg during full rebuild (`-33`) | Mid-walk tip moves | Abort/restart rebuild; never `initWitnessesBuilt=true` with partial walk |
| Reorg after built (normal) | `DecrementNoteWitnesses` must match depth | Spends work; optional short rebuild if cache empty |
| Deep reorg / rewind past note birth | Cache may be empty or inconsistent | Clear + `BuildWitnessCache(tip,false)` or refuse with `-31` until rebuild |
| Kill mid-rebuild + reorg on restart | Stale flags on disk | Load: if uncertain, force rebuild before spends |

**Proposed tests** (extend `wallet_witness_defer.py` or sibling; Tier B)

| ID | Group | Priority | Spec | Status / gate |
|----|-------|----------|------|---------------|
| **R5a** | Reorg @ defer window | **P1** (opt-in validated) | Tip restored after reindex+defer; `invalidateblock` tip; remine; wait witnesses; spend | **done** |
| **R5b** | Reorg after built | **P1** (default-on) | Built tip; 1-, 3-, 10-, and 20-block invalidate; remine; spend | **done** (10/20 added) |
| **R5c** | Reorg during `-33` | **P2** | See **FIX-WIT-WALK-UNLOCK** below. Not a reachable e2e on current locks. | **product open** |
| **R5d** | Excessive reorg | **P1** (Cycle 2) | Fork deeper than `MAX_REORG_LENGTH`; node stays up; `getblockcount` unchanged; no `Shutdown: done`; warning in log | **blocked on Cycle 2** |
| **R7b** | Kill mid-rebuild | **P2** (default-on) | SIGKILL during `-walletwitness=rebuild`; restart defer+noteidx; eventually spend | **done** (best-effort race on short tip) |
| **GTest-DEC** | Unit decrement | **P1** | size==1 keep-last (CachedWitnesses*); witnessHeight above disconnect skips pop | **done** (`DecrementNoteWitnessesSkipsAboveHeight`) |

**Groups (reorg-sharp only)**

1. **Defer-window:** R5a -- **done**.
2. **Post-build soft path:** R5b -- **done** (1/3/10/20).
3. **Rebuild-window:** R7b **done** (process death). R5c is not a missing test -- see FIX-WIT-WALK-UNLOCK.
4. **Excessive (not applied):** R5d -- Cycle 2.
5. **Unit edges:** GTest-DEC -- **done**.

**Do not run for confidence:** the known-fail tiers and held gtests, which `qa/zcash/test_filters.sh` excludes by name. Coverage those would have provided for shielded reindex is **B1** `reindex_shielded.py`.

#### FIX-WIT-WALK-UNLOCK

**What R5c wanted that other cases do not assert:** a **concurrent** tip change *while* `BuildWitnessCache(..., false)` is mutating note witnesses -- then prove `initWitnessesBuilt` is not set true on a partial walk, spends stay `-31`/`-33`, and the walk aborts or restarts on the new tip.

R5a is reorg **before** rebuild (defer window). R5b is reorg **after** `initWitnessesBuilt`. R7b is **SIGKILL** mid-rebuild (in-memory flags die with the process; wallet.dat may be partial; restart must not spend until rebuild). GTest-DEC is decrement math with no RPC and no `cs_main` walk. Boost allowlist is dispatch policy with the flag forced, no walk. None of those overlap a live walk racing `InvalidateBlock` / P2P `ProcessNewBlock`.

**Why it is not reachable today:** the height walk holds `LOCK2(cs_main, cs_wallet)` for the whole loop (`wallet.cpp` `BuildWitnessCache`). `invalidateblock` is not allowlisted, so it returns `-33` without taking the lock. P2P connect waits on `cs_main` and runs **after** the walk sets `initWitnessesBuilt=true` -- that is R5b, not mid-walk. Measured walk (M-WAL-WITNESS-TIP-AB): stock **7659 ms** / NOTEIDX **220 ms** of held `cs_main`.

**Why it is not the opt-in ship gate:** opt-in defaults off; the lock **serializes** reorgs to after the walk; R7b covers process death; R5a/R5b cover defer-window and post-build reorg. The remaining hazard is **ops latency** (allowlisted `getblockcount` stalls on `cs_main`) and a future walk that **releases** the lock without abort logic.

**Product work (not a longer lab):** periodically drop `cs_main` in the height walk; poll `ShutdownRequested()`; if `chainActive.Tip()` moved or a disconnect landed, abort the walk, leave `initWitnessesBuilt=false`, restart `RebuildWitnessCacheForChainTip` (recovery mode 2) or hard-clear (mode 3). Then an e2e can `invalidateblock` or wait for P2P reorg **during** `-33`. Until that change, a fat-tip soak only shows `-33` on spends and stalled status RPCs.

**Not addressed meanwhile** (do not confuse with R5c): DIRTY re-dirty on pop; default-on of defer; Idx1 getalldata; P2P/DNS follow-tip; full bootstrap ingest; G5 mining (Track M, scheduled); Bfail/CleanIndex.

**Recovery modes (product)**

1. **Soft:** decrement path only (current) when cache depth sufficient.
2. **Rebuild:** `RebuildWitnessCacheForChainTip` if after reorg any note lacks usable witness (detect: empty witnesses / failed root check).
3. **Hard clear:** `ClearNoteWitnessCache` + rebuild if inconsistency logged (prefer over assert / `exit(1)`).
4. **RPC:** keep `-31` until rebuilt; `-33` while rebuilding; status allowlist for monitors.

**Crash and flush.** Chainstate (`FlushStateToDisk` in `Shutdown`) and wallet (`pwalletMain->Flush(true)`; periodic `ThreadFlushWalletDB`) are **separate** databases. `SetBestChainINTERNAL` is an atomic BDB txn for **note-bearing** txs + `nWitnessCacheSize` + best-block locator only. Transparent `AddToWallet` uses per-tx `WriteToDisk`. There is no cross-DB commit with `chainstate/`. After a crash, startup uses the wallet locator (`ReadBestBlock`) and rescans; `clearWitnessCaches` / `-rescan` rebuilds witnesses. Orderly `StartShutdown` reaches that flush. `DecrementNoteWitnesses` `exit(1)` on null `pindex` and `AbortNode` both skip a clean wallet+chain flush if they do not return through `Shutdown()`. Replace those `exit(1)` paths with log + recovery mode 2/3, then `StartShutdown` only if disk is unwritable (`AbortNode` already does that for consensus abort). Do not add a third flush mechanism; use existing `Shutdown` and `SetBestChain`.

**SIGKILL cannot be caught.** POSIX `SIGKILL` (signal 9) cannot be caught, blocked, or ignored. Neither can `SIGSTOP`. `zerod` has no handler path, no `Shutdown()`, no wallet/chain flush. Lab **R7b** uses Python `proc.kill()` = SIGKILL; recovery is restart + whatever hit disk. `SIGTERM` (15) *can* be caught -- that is why FIX-LBI / FIX-IMPORT-POLL exist. Do not design crash recovery around intercepting SIGKILL.

**Excessive reorg -- reject before mutate (TNT-02).** Today `ActivateBestChainStep` computes `reorgLength` from `chainActive` vs fork, then on `> MAX_REORG_LENGTH` logs, `StartShutdown()`, `return false` **before** `DisconnectTip`. Invariant to keep: no `DisconnectTip` / `ConnectTip` / `SyncWithWallets` / `ChainTip` / insight reverse / wallet `AddToWallet` on that fork. Headers may already sit in `mapBlockIndex` / `setBlockIndexCandidates` (required to measure depth); that is not a tip switch. Change: drop `StartShutdown()`; keep `return false`; warning not fatal modal; persist current tip (already on disk). Do **not** follow the fork (TENT `6f64bb7` code). Same gate in unintended `RewindBlockIndex`. New e2e **R5d** once implemented.

#### Integration cycles

Performance first, then crash/reorg hardening. Each cycle is one reviewable PR plus its validation, not a micro-PR per flag or per test ID. Incremental retest of every neighbor is prudent in principle; the cost of that cadence on this tree is months of idle. Bound it: gtest + the one e2e that the cycle changes; rematch the one measure the cycle claims; do not re-run genesis `-rescan` or post-Sap n=4 unless the rematch is ambiguous.

**Cache vs cap (Cycle 3).** Today `WITNESS_CACHE_SIZE = MAX_REORG_LENGTH + 1` (100 slots, apply bound 99). `IncrementNoteWitnesses` caps the per-note deque at that size; `DecrementNoteWitnesses` pops one layer per disconnected block. Cycle 2 **reject-and-stay** never applies past 99, so a 100-slot deque is always enough for an applied reorg. Cycle 3 is the only place the numbers can diverge.

Do **not** choose a cache shorter than the apply cap. If `WITNESS_CACHE_SIZE < MAX_REORG_LENGTH + 1`, an applied reorg of depth D with `cache <= D <= cap` empties the deque while the node still treats the reorg as legal -- spends fail or hit `exit(1)` / forced rebuild. That is the failure mode TNT-03 exists to prevent, not an option. Raising the cap toward maturity 720 or Zebra 1000 means growing the deque (RAM per note) or accepting rebuild-on-deep-reorg; `keeptxfornblocks` is already floored at `MAX_REORG_LENGTH + 1`. Cycle 2 "rebuild if cache short" is recovery after crash or a legal-depth pop that left no layers -- a different sentence.

**Cycle rematch campaign.** Same wallet x op matrix after each cycle, one restartable trial per invocation: `contrib/perf/ops-campaign.sh`. Ops: sync (caught-up start), rescan, reindex, bootstrap. Wallets: none / p0 / p1 / fat. Collate: `contrib/perf/collate_cycle.py`. Do not batch long trials.

| Cycle | Bundle | Deps | Impact | Effort | Risk | Validation |
|-------|--------|------|--------|--------|------|------------|
| **1 -- witness perf** | Package A: STALE + R8 both `AddToWallet` flavors. After rematch: flag collapse (NOTEIDX default; drop `-walletwitnessnote`). | NOTEIDX prototype in tree | **High** fat `-rescan`/IBD after 1.6M (M-WAL-RESCAN-FAT) | **S** then **S** for flags | **Med** missed note invalidate | R8 gtest; campaign `SET=gate` (fat tiny + optional full rescan); post-1.6M CPU if tiny is ambiguous |
| **2 -- stay up** | Decrement no `exit(1)`; recovery 2/3. **TNT-02** reject-and-stay is **not scheduled** (keep 99 + exit). | None on A | **Med** (crash recovery) | **M** | **Med** | GTest-DEC follow-on for rebuild-if-short |
| **3 -- cap sizing** | Packages F then optional G: move 99 only with `WITNESS_CACHE_SIZE >= cap+1` / `keeptxfornblocks` / rewind; optional `-maxreorg` as reject-bound | Cycle 2 proven | **Med** (memory, rebuild cost) | **M-L** | **High** if deque shallower than apply bound | Memory/rebuild review; rematch campaign + RSS; not Zebra-1000 by default |

**Parallel tracks** (do not wait on Cycle 1; do not batch into Cycle 2):

| Track | Bundle | When | Impact | Effort | Risk | Validation |
|-------|--------|------|--------|--------|------|------------|
| **M -- mining** | **G5** mainnet (192,7) timed solve + Instruments on `zcash-miner` | Scheduled now. One trial; Instruments host when free. Orthogonal to witness. Groth G2/G3 still after G5/G9 | **Med** (solve vs verify) | **M** wall for one solve | **Low** (disposable template; never Application Support) | `MINE_MAINNET_SOLVE=1`; campaign `mine-equihash-*`; compare to verify ~0.25 ms/blk |
| **Z -- zeronode** | **TST-03** / **TNT-12** / **DOC-02** | **A now** (arg validation, existing Boost). **B** founders window with Cycle 1 if the lab node is free. **C** 2-node after A/B. **D** zeronode `invalidateblock` after Cycle 2. Docs steps 1-2 with A | **Med** product (no harness today) | A **S**; C **M** | **Low** A; **Med** C (collateral setup) | Expand `rpc_zeronode_tests`; then scripted `startalias` |

Package **E** (Decrement uses Select) and incremental `vNoteTxHashes`: after Cycle 1 rematch, only if profiles still show those walks. **WALK-UNLOCK** / R5c: after Cycle 2 if mid-rebuild ops latency matters; not a Cycle 1 or 2 gate. Third skip: only if post-STALE `FindMyNotes` is the wall.

#### Work packages vs later items

| Package | IDs | What | Cycle |
|---------|-----|------|-------|
| **A -- STALE** | FIX-WAL-WITNESS-NOTEIDX-STALE, R8 | Narrow invalidate; gtest connect + disconnect `AddToWallet` | **1**. Not skip-`AddToWallet`. |
| **B -- applied reorg depth** | R5b | 1/3/10/20 post-build invalidate+spend | **Done** in `wallet_witness_defer.py`. |
| **C -- reject-and-stay** | TNT-02, DEF-07 (policy half), R5d | Drop live/rewind `StartShutdown`; do not apply; warn; stay up | **2** with D. Not TENT unbounded connect. |
| **D -- crash-safe witness** | recovery 2/3, GTest-DEC follow-on | No `exit(1)` in Decrement; rebuild if cache short; rely on `Shutdown` flush | **2** with C. |
| **E -- Decrement NOTEIDX** | later | `DecrementNoteWitnesses` uses `SelectWalletTxsForWitnessScan` | After 1 rematch if still hot. Independent of 2. |
| **F -- cap vs maturity** | TNT-03, DEF-07 (sizing half) | Change 99 only with `WITNESS_CACHE_SIZE >= cap+1`, `keeptxfornblocks`, rewind | **3**. Not Zebra-1000 unless memory reviewed. |
| **G -- optional `-maxreorg`** | Pirate-like | Operator raise **if** C is default reject-and-stay | **3** after F. Not an apply-unbounded escape. |

**Not Cycle 1:** skip `AddToWallet` when `fExisted && fUpdate`; WALK-UNLOCK; raising cap; G5; TNT-12 Phase C.

#### Opt-in ship checklist

Ship **`-walletwitness=ibd-defer`** + **`-walletwitnessnote=1`** as documented opt-in (defaults off):

1. Help strings + Perf/contrib README (opt-in wording) -- **done**.
2. NOTEIDX walk **done**; Select shared.
3. Boost gates in `--strict` (incl. allowlist) -- **done**.
4. Tier B: R1/R2/R5a/R5b/R7b -- **done** in `wallet_witness_defer.py`.
5. PROTO-RPC-ALLOW under `-33` -- **done** (`stop`/`help`/`getblockcount`/`getblockchaininfo`/`getnetworkinfo`).
6. Post-Sap **WIT-REBUILD** with notes in range -- **done** (M-WAL-WITNESS-TIP-AB).
7. Release note (paste at tag / GA notes) -- **done** (text below).

**Opt-in package: ready to ship** (defaults remain off). Default-on = above + R5b/R7b. **FIX-WIT-WALK-UNLOCK** is separate product work (optional before default-on if mid-rebuild reorg must be a live race).

**Release note text (opt-in witness flags):**

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

#### RPC status allowlist + load tests

**How the list was chosen:** Pirate freezes **all** RPC while rebuilding. Zero keeps `-33` on wallet/spend/data so half-built notes cannot be read or spent, and **allowlists** only methods that do not touch the wallet: `stop` (ops can halt a long rebuild), `help`, `getblockcount`, `getblockchaininfo`, `getnetworkinfo` (monitors / Zerowallet "is the node alive"). Denied by default: any other name, including `getwalletinfo`, `getalldata`, `z_*`, `getsupply`, `invalidateblock`. Zero has no `uptime` RPC. `-32` is zeronodes; do not remap.

**What tests actually prove**

| Test | Proves | Does not prove |
|------|--------|----------------|
| `rpc_witness_building_cache_blocks_all_rpc` | `-33` message on `z_sendmany`, `getsupply`, `getalldata`, `getwalletinfo` when flag forced | Exhaustive RPC inventory; real walk |
| `rpc_witness_building_cache_allows_status_rpc` | `getblockcount` / `getblockchaininfo` / `getnetworkinfo` / `help` execute; `stop` exists at the gate (actor not invoked) | Those calls return **during** a real walk (`getblockcount` takes `cs_main` and **stalls** until the walk drops the lock) |
| `rpc_getalldata_s5_witness_gate` | `-31` on getalldata/z_sendmany when never built | `-33` window |
| `wallet_witness_defer.py` R1/R2 | After import+rebuild, spend works | Mid-walk RPC mix |

Safety of "others are not allowed" is the **deny-by-default** name check in `CRPCTable::execute`, not a per-RPC case. Adding a name to the allowlist is the risky change; leaving a method off is safe. Hidden RPCs (`invalidateblock`) are `-33` today -- required so R5c cannot inject via RPC until FIX-WIT-WALK-UNLOCK.

**Load / soak (lab, not CI)**

| Test | How | Metric |
|------|-----|--------|
| Status poll under rebuild | Loop `getblockcount` while `-walletwitness=rebuild` on fat tip | Expect **stall** for walk duration (cs_main), then success; not a hang forever |
| Spend storm while `-31` | Parallel `z_sendmany` before rebuild done | All `-31`; no crash |
| getalldata after rebuild | datatype 0/1; day 2 vs omit; nCount 50/200 | wall_ms; RSS; resp bytes |
| Concurrent status + getalldata at tip-quiet | 1 status/s + 1 gad | No deadlock; gad latency |

#### More e2e and WIT-REBUILD

| Work | Why |
|------|-----|
| R3 allowlist e2e | Optional; Boost already gates allowlist |
| R5c / FIX-WIT-WALK-UNLOCK | Product: drop `cs_main` in the walk, then e2e mid-`-33` disconnect |
| Promote R1/R2 to pass-tier only after stable wall time / optional shorten maturity | Routine gate later |
| **WIT-REBUILD post-Sap** | Fat wallet + tip **>492850**; time `height-walk done elapsed_ms` stock vs noteidx | Real `-33` window -- see assess below |
| WIT-REBUILD + reorg inject | After FIX-WIT-WALK-UNLOCK | recovery mode 2/3 |

Automation: `ZERO_PERF_CHAIN_SNAP=full` on `witness_lab.sh rebuild|rebuild-noteidx` (or tip-only rebuild once a full template exists); one trial at a time.

#### Disposable full tip -- what and how

**What:** A scratch `-datadir` that holds a **mainnet tip** chain (blocks + chainstate near live tip ~2.5M), used for labs that tiny/short cannot answer: Sapling-note height walk, Idx1 getalldata (~513k UTXO), tip-quiet RPC. **Disposable** = never the default Application Support / `%APPDATA%` path; wipe after the trial; goldens stay read-only.

**Why tiny/short fail for post-Sap walk:** tiny tip **187417**, short tip **245992** -- both **pre-Sapling** (activation **492850**). Fat golden notes are Sapling -> height walk **skipped** on those snaps (M-WAL-WITNESS-REBUILD).

**How (tip transplant -- preferred):**

```bash
# Live datadir stopped. Scratch must not be Application Support/zero.
PROD="$HOME/Library/Application Support/zero"
SCRATCH="$PWD/reindex-profile/fulltip-812-datadir"
rsync -a --delete --exclude='wallet.zero*' --exclude='debug*.log' \
  --exclude='.lock' --exclude='zero.conf' --exclude='chainblocks*.tgz' \
  "$PROD/" "$SCRATCH/"
# REQUIRED if source used Insight indexes (else reindex-from-genesis):
#   experimentalfeatures=1
#   insightexplorer=1
```

Verified: tip **2518018**, no reindex, with those flags. Archive pack: `COPYFILE_DISABLE=1 tar -C "$PROD" -czf chainblocks812-clean.tgz blocks chainstate`.

**How (witness rebuild A/B -- full `-reindex` path):**

```bash
ZERO_PERF_SRC_DATADIR="$HOME/Library/Application Support/zero" \
ZERO_PERF_CHAIN_SNAP=full \
ZERO_PERF_WALLET_FILE=/path/to/golden/fat/wallet.zero \
  contrib/perf/witness_lab.sh rebuild-noteidx
```

`SNAP=full` rsyncs `blocks/` (drops chainstate), copies wallet, `-reindex` + `ibd-defer` -- **L wall**. Prefer tip-only:

```bash
ZERO_PERF_TIP_TEMPLATE=$PWD/reindex-profile/fulltip-812-datadir \
ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
  contrib/perf/witness_lab.sh tip-rebuild-note   # then tip-rebuild
```

**Measured (M-WAL-WITNESS-TIP-AB):** fat @ tip **2518018**; Rescan height-walk (~1441 blk from 2516577): stock **7659 ms** / 801619 txs vs `-walletwitnessnote` **220 ms** / 1403 txs (~**35x**). Rebuild `zerod` after flag renames.

**Idx1:** same full-tip scratch at quiet tip; getalldata datatype matrix (BENCH-GAD-IDX1) still open.

#### Post-Sap WIT-REBUILD -- effort and duration

| Piece | Effort | Duration band | Evidence / bound |
|-------|--------|---------------|------------------|
| Script/docs for `SNAP=full` (exists) or tip-only mode | **S** | -- | `witness_lab.sh` already has `full` |
| Prep disposable full tip (rsync ~10G blocks + `-reindex`) | **M** ops | **L wall** once | Empty full-chain import historically ~**145 min** (bootstrap); wallet-off reindex same class |
| Fat + defer import to full tip (if not tip-only) | **M** ops | **L wall** per trial | Defer IBD ~ConnectBlock-only; tiny defer import ~**333 s** to h187417 (M-WAL-WITNESS-REBUILD) -- full tip scales with chain length, not note walk |
| Tip height-walk A/B (the measurement) | **S** once tip ready | **unknown** until run | Tiny walk **skipped**; NOTEIDX scans **1403** txs; stock would scan **~801k** -- expect large NOTEIDX win; do **not** invent wall_ms |
| Pair of trials (stock vs noteidx) | -- | **2x** tip-walk (or 2x full reindex if no template) | Lab rule: one long trial per invocation |

**Assess:** Coding/docs **S**; ops **M**; wall **L** for first full reindex, then tip-only A/B should be much shorter than reindex (walk-bound). **Blocking input:** disposable full tip (or any tip >492850 with fat notes in range). Not required for opt-in ship; recommended before default-on.

#### Density / L3 and Idx1 tip

**Shielded density + L3 (BENCH-SEG): parked** relative to witness opt-in. Offline `shielded_density.csv` counts Sapling spends/outputs / Sprout JS per height band (fine rematch windows + coarse 400k bands split at activation). **L3** = era-bounded ConnectBlock rematch (onset bootstrap/reindex peers) using those era labels -- wallet-off sync narrative, not witness. Done: density tip-complete; onset n=1 peers. Optional: n=4 if noise warrants. Resume only on deliberate Stage-1 / rematch track switch.

**Idx1 tip getalldata -- remains open.** Same disposable full tip as above. G0e was fat@**tiny** only (~0.75-1.2 s). **BENCH-GAD-IDX1** = quiet full tip + datatype matrix; L wall; not witness-blocking.

#### Dev profile Id 1 retest + inflated wallet library

**Profiles (opaque ids in public docs -- no host paths):**

| Id | Intent | Prior |
|----|--------|-------|
| **0** | Empty / tiny keypool | M-WAL-SYNC-P0 ~950 blk/s |
| **1** | Non-empty mid-size (Dev personal / extracting) | **M-WAL-SYNC-P1** -- ~918 blk/s; wallet 237568 B; txcount 133; note_tx 0 |
| **2** | Extracting / intermediate | §0.11 matrix slot |
| **3** / fat | Golden ~800k tx | G0 / NOTEIDX / defer |

**Id 1 (`M-WAL-SYNC-P1`)**

1. Tiny `-reindex` on disposable scratch -- **done** (`test-logs/walletsync-20260813T055703Z/`).
2. Catalog: wallet **237568** B flat; txcount **133**; note_tx **0**; tip **187417** in **~201 s** (~**918** blk/s); RSS **~103->398 MiB**.
3. CPU Time Profiler -- **skipped**: no notes; throughput in P0 class (witness_cache not the story). Revisit only if a later Id 1 golden gains Sapling notes.
4. A/B defer+note -- low value here (note_tx 0); keep for fat / Id 2+.
5. Tip-quiet getalldata -- optional; not Idx1.

**Inflated wallet library (reuse)**

- Keep **read-only golden copies** outside scratch (ops-local; not git): Id 0/1/2/3 (+ fat). After each trial, **discard** scratch; never mutate goldens.
- Optional: one **pre-inflated scratch template** (chainstate+blocks at tiny/short tip + wallet copy) rsync'd per run to skip tar extract -- still copy wallet from golden each time.
- Document sizes in Measures when measured (`wallet_bytes`, txcount, note_tx); refresh goldens only on deliberate ops snapshot.
- Cleanup rule (post-lab): wipe used scratch datadirs (e.g. `witness-tip-rebuild-datadir`); keep one full-tip **template** (`fulltip-812-datadir`) until P2P/bootstrap labs finish; keep `test-logs/*/SUMMARY` + archives. Never touch Application Support `zero/` or Zero400 trees.

#### Proposed next execution order

1. Opt-in ship -- packaging **done** (tag when maintainer cuts release); defaults off.
2. P2P follow-tip from archive template (DNS, distinct rpcport); full bootstrap ingest later.
3. **FIX-WIT-WALK-UNLOCK** -- product; then mid-`-33` e2e.
4. Idx1 / L3 n=4 -- **parked** until deliberate track switch.


## 1. Scope, method, and reproduction procedure

**Subject:** where `zerod` spends CPU during `-reindex` (rebuild `chainstate` from local `blocks/*.dat`) and `bootstrap.dat` import (bulk-load a pre-staged flat file of blocks) -- the two faster-than-network ways to catch a node up. Both were assumed "fast" but never measured; this investigation measured them, found the dominant costs, and implemented and measured fixes for two of them.

**Working tree:** `ZeroPerf` (branch `perf-401`), built at `-O1` (`-pipe -O1 -g -fwrapv -fno-strict-aliasing`, the repo default). Binary is self-contained (verified via `otool -L`: only system libraries dynamically linked, all third-party dependencies static).

**Terms:**
- **Bucket:** one of a small number of mutually-exclusive CPU-time categories a profiling sample falls into, matched against *any* frame in a sample's call stack (not just the leaf).
- **Latch:** a single-slot memoization -- one stored value (or empty), cleared by the operations that change underlying state, repopulated on next read. Not a cache: no key, no multiple entries, no eviction policy, because there is only ever one live value to remember.
- **Activation height:** the mainnet block height at or after which a network upgrade's rules apply. Sapling: height 492,850 (`chainparams.cpp`).

**Profiling method:** a real mainnet datadir (not synthetic/regtest -- script/tx mix affects where time goes) profiled with Instruments Time Profiler (`xcrun xctrace`, headless CLI) attached to the single worker thread that does the actual reindex/import work (`zcash-loadblk`, running `ThreadImport`). Every other thread (idle script-check-queue workers, RPC/net/**wallet** threads) is filtered out -- unfiltered, all-threads profiles are dominated by idle-thread noise (85%+ of raw samples blocked on a condvar) and say nothing about where real work goes.

**Scope note -- ConnectBlock vs wallet-on:** `capture_sequence.sh` / `bench_matrix.sh` default filter is **ConnectBlock / import** on `zcash-loadblk` (Groth16, Equihash, disk, trees). Fat-wallet reindex is a **separate** track: M-WAL-SYNC-FAT / M-CPU-WAL-FAT / §0.14 -- bottleneck is `VerifyAndSetInitialWitness`, not `OrderedTxItems` (WAL-WTXORDERED done). ZeroStruct §13.4.3 for order-insert history.

**Retarget for wallet-on sync CPU:** attach Time Profiler to live `-reindex` with fat wallet; bucket **ALL** threads (or loadblk -- witness runs on loadblk); use `witness_cache` needles (§0.14 hygiene) plus AddToWallet/OrderedTxItems; record height window. Do not interpret empty-wallet profiles as fat-wallet cost.

**Reproduction procedure** (fresh scratch datadir -> launch -> attach profiler -> export/bucket -> determine the exact height window covered):

1. Fresh scratch datadir (chainstate excluded; `-reindex` rebuilds it -- source `~/Library/Application Support/Zero/` is only ever read, never modified):

   ```bash
   cd <repo root>
   rm -rf reindex-profile/datadir
   rsync -a --exclude='chainstate' "$HOME/Library/Application Support/Zero/" reindex-profile/datadir/
   ```

2. Launch `-reindex`, poll `getblockcount` via `zero-cli` until height has advanced (RPC gives an exact, race-free signal -- don't guess from wall-clock or log-tailing), then attach Time Profiler:

   ```bash
   ./src/zerod -datadir="$PWD/reindex-profile/datadir" -reindex -connect=0 -listen=0 -rpcport=23920 &
   PID=$!
   until h=$(./src/zero-cli -datadir="$PWD/reindex-profile/datadir" -rpcport=23920 getblockcount 2>/dev/null) \
         && [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -gt 3000 ]; do sleep 3; done
   xcrun xctrace record --template 'Time Profiler' --output reindex-profile/timeprofile.trace --time-limit 60s --attach "$PID"
   kill -TERM "$PID"  # once the recording completes
   ```

3. Export and bucket the trace:

   ```bash
   xcrun xctrace export --input reindex-profile/timeprofile.trace \
     --xpath '/trace-toc/run[1]/data[1]/table[@schema="time-profile"]' \
     --output reindex-profile/timeprofile_agg.xml
   python3 reindex-profile/tools/bucket_profile.py reindex-profile/timeprofile_agg.xml
   ```

   `xcrun xctrace export` produces a flat XML table where `<thread>`, `<weight>`, `<tagged-backtrace>`, and `<frame>` elements are each defined in full **only once**, with every later occurrence a bare `ref="N"` backreference -- a naive per-row regex silently undercounts almost everything after the first sample. `reindex-profile/tools/bucket_profile.py` resolves all four backreference types correctly and buckets by call-stack substring match (edit the `BUCKETS` dict to add/adjust categories). Second argument filters to one thread by substring (default `zcash-loadblk`) -- always filter to a specific thread.

4. **Determine the exact block-height range the window covered** -- not from the datadir's *final* height, which is a trap; block/tx mix varies enormously by height, so a bucket breakdown is only interpretable together with its height range:

   1. Get the trace's actual recording start time, in its own stated timezone: `xcrun xctrace export --input some.trace --toc | grep start-date`.
   2. Convert explicitly to whatever timezone `debug.log` uses (Zero's is UTC) -- a background-launched process's wall-clock launch time is not the same as when the recording window actually started, and mixing local time with a UTC log timestamp will silently shift the derived window by hours.
   3. Grep `debug.log` for `UpdateTip` lines whose timestamp falls in `[start, start+60s]`, and read `height=` off the first and last matches -- bound by timestamp, not by searching for a height number as a substring (`height=937` also matches `height=937237`).
   4. For bytes/sec alongside blocks/sec: sample block `size` at a handful of evenly-strided heights via `getblock` RPC (needs a running node -- pointing a plain launch at the already-reindexed scratch datadir works, no need to redo the reindex). Block size varies by two orders of magnitude block-to-block, so treat this as an estimate with real uncertainty, not an exact figure.

**General lesson:** don't trust a bucket percentage, height range, or throughput figure that wasn't cross-checked against a second source of truth (a different trace, a log timestamp, an RPC call) -- every number in §2 that turned out to matter was caught or confirmed this way, and every early mistake (an 86%-other mis-parse, a wrong-timezone height window, a substring-match height search) was a case of trusting one source without a second check.

### Lab materials

Canonical home for lab inputs and scratch locations (not duplicated in Measures). Do not modify originals; copy or softlink into scratch.

| Role | Location | Notes |
|------|----------|-------|
| Original `bootstrap.dat` | Out-of-tree `<linearize>/bootstrap.dat` | Regenerated **2026-08-13** (~5.04 GiB); hashlist heights **0-2468990**; magic ZERO `5a45524f`. Live tip ~2518018 is ahead. Moved out of `Zero400/contrib/linearize/` **2026-08-16** (repo tree keeps only `hashlist.txt` + the `linearize-*.py` scripts). Lab softlink: `reindex-profile/bootstrap-src/bootstrap.dat`. Smoke: **M-BOOT-NEW-20260813**. Read-only / copy only. |
| Full chain snap | macOS Application Support `zero/` | Live tip **2518018** (verified); `blocks/` ~10G + `chainstate` ~619M + `blocks/index` ~4.7G. Live tree may have **xattrs** (`com.apple.provenance`) with **no** on-disk `._*` (`find . -name '._*'` empty) -- macOS `tar` still emits AppleDouble into archives unless `COPYFILE_DISABLE=1`. Prefer **`chainblocks812-clean.tgz`** (~8.5G) or rsync. Older `chainblocks812.tgz` may include `._*`. Tip transplant needs `insightexplorer=1`. |
| Short / tiny snaps | same datadir | `chainblocks-short.tgz` ~342M; `chainblocks-tiny.tgz` ~228M; sha256 sidecar |
| Disposable full tip scratch | `reindex-profile/fulltip-812-datadir` | rsync from live (or clean archive); `zero.conf` must include `experimentalfeatures=1` + `insightexplorer=1` or node **reindexes from genesis** |
| Bench ledger / reports | `reindex-profile/bench-summaries/` | `ledger.*` via RecBench; historical TSV / memprofile |
| Post-Sapling scratch | `reindex-profile/postsapling-datadir` | From `postsapling_reindex.sh` |
| DevFee ops wallets | out-of-tree DevFeeWallets | Fat-address getalldata; not ConnectBlock CPU |

Bootstrap-mode datadir reset must exclude `blocks/` (M-INIT-03 / §3). Current stock campaigns use `-reindex` / `-loadblock` without FDCACHE 4x2. Script usage: **contrib/perf/README.md**. Bound ledger campaigns: **Measures.md** §8.

---

## 2. CPU cost breakdown: what dominates, and why it's height-dependent

**Original measurement** (`-reindex` on two builds, `bootstrap.dat` import, chain heights ~10K-2M; mutually exclusive buckets, `zcash-loadblk` thread only, 0% unaccounted backtraces in every run):

| Bucket | Typical range | Call path (leaf -> root) |
|---|---|---|
| Sapling/Sprout tree update | 57-58% | `Fr::mul_assign`/`Fr::inverse` (BLS12-381 field arith) <- `jubjub::edwards::Point::add` <- `librustzcash_merkle_hash` <- `IncrementalMerkleTree::root()` <- `CCoinsViewCache::AbstractPushAnchor` <- `ConnectBlock` |
| Equihash PoW verification | 24-27% | `blake2b_compress_ref` <- `blake2b_final` <- `Equihash<192,7>::IsValidSolution` <- `CheckEquihashSolution` <- `CheckBlockHeader` |
| Disk I/O | 15-18% | `OpenDiskFile`/`ReadBlockFromDisk`/`UndoWriteToDisk` (`fopen`/`open` syscalls) <- `LoadExternalBlockFile`/`ConnectBlock` |

**This breakdown is identical for `-reindex` and `bootstrap.dat` import** -- both call the same `ConnectBlock`/`CheckEquihashSolution`/`AbstractPushAnchor` validation per block; `bootstrap.dat` only changes how block bytes arrive, not what validation happens once a block is in hand. Measured `bootstrap.dat` import: **145.7 minutes** (8,743,120 ms, self-reported) for 2,468,990 blocks, ~282 blocks/sec average across the entire chain history. **`bootstrap.dat`'s entire benefit is skipping network download time; it cannot reduce the CPU-bound validation cost.**

**`bootstrap.dat` for these measurements** was generated via Zero400 `contrib/linearize` from a synced node's `blocks/` (not a network download). Paths and regenerate notes: §1 Lab materials.

**The idle script-check-queue threads (`zcash-scriptch`, `-par`) cannot help any of this bucket breakdown.** They're wired only to per-transaction signature verification, never to anchor/tree updates, in every codebase checked (Bitcoin Core, zcashd, Zero, Zebra). This is a per-call cost problem in code that has never been parallelized, not a parallelism gap in otherwise-idle threads.

**Correction -- the table above conflates two distinct costs.** Sapling's Groth16 zk-SNARK proof verification (`librustzcash_sapling_check_spend`/`_check_output`, called from `ContextualCheckTransaction`) *also* does elliptic-curve arithmetic over the same `jubjub`/BLS12-381 types used by tree-anchor recomputation, deep inside `bellman::groth16::verifier::verify_proof` -- the original bucket definitions couldn't tell these apart. Re-bucketing with a set that checks for `bellman::groth16::verifier::verify_proof`/`miller_loop`/`final_exponentiation` specifically splits it correctly:

| Bucket | % of CPU (height 610,758-626,806) | Call path |
|---|---|---|
| **Sapling Groth16 proof verification** | **60.9%** | `Fq::mul_assign`/`Fq12::square` (BLS12-381 pairing arith) <- `miller_loop` <- `bellman::groth16::verifier::verify_proof` <- `librustzcash_sapling_check_spend`/`_check_output` <- `ContextualCheckTransaction` |
| Disk I/O | 26.2% | Same syscalls as above |
| Equihash PoW verification | 6.9% | Same call path as above |
| Sapling/Sprout tree/anchor update | 6.1% | Same call path as above -- **this is what the original "57-58%" figure actually measured almost none of** |

Cross-checking against an earlier-build trace spanning the full 0-2.47M height range and re-bucketed with the corrected script gives **0 Groth16 samples**, reproducing the original 58/26/16 split almost exactly -- confirming the corrected script isn't the source of the discrepancy, and that the original figure was measured on a height range with negligible Sapling shielded-tx volume (Sprout-dominated or pre/early-Sapling), so it wasn't wrong about *that window*, only wrong as a general claim about "the" bucket breakdown.

**The bucket breakdown is height-dependent, not a fixed constant** -- any profiling result needs its block-height range reported alongside it to be interpretable. Throughput for the 610,758-626,806 window: 267.5 blocks/sec (exact, from `UpdateTip` timestamps), ~330 KB/sec (estimated from 41 evenly-strided `getblock` samples, individual blocks ranging 685-160,858 bytes) -- consistent with the whole-chain ~282 blocks/sec average.

**Whole-chain confirmation, six 5-minute windows spanning the reindexed range** (`contrib/perf/capture_sequence.sh` drove the repeating capture; `contrib/perf/decode_captures.py` exported/bucketed each one and derived its exact height range from the trace's own timestamp cross-referenced against a `debug.log` snapshot -- see `contrib/perf/README.md`):

| Capture | Height range | blocks/sec | Groth16 | Disk I/O | Tree/anchor | Equihash |
|---|---|---|---|---|---|---|
| 1 | 5,373 -> 336,144 | 1,102.6 | 0% (pre-Sapling) | 16.54% | 54.99%* | 28.46% |
| 2 | 626,078 -> 702,200 | 253.7 | 54.74% | 25.03% | 13.83% | 6.40% |
| 3 | 995,392 -> 1,083,180 | 292.6 | 52.77% | 26.20% | 13.67% | 7.36% |
| 4 | 1,411,397 -> 1,482,630 | 237.4 | 55.23% | 24.94% | 13.94% | 5.88% |
| 5 | 1,693,202 -> 1,777,052 | 279.5 | 53.84% | 25.03% | 14.01% | 7.12% |
| 6 | 2,032,619 -> 2,173,838 | 470.7 | 48.09% | 26.02% | 13.78% | 12.11% |

*Capture 1 is pre-Sapling-activation: its "tree/anchor" share is inflated only because Groth16 doesn't exist yet at these heights.

Post-Sapling (captures 2-6), Groth16 is consistently dominant (48-55%) across five independently-sampled ranges spanning nearly the whole post-activation chain -- the single-window 60.9% figure was directionally correct, though the exact percentage tracks per-window shielded-tx volume rather than being a fixed per-block overhead. Disk I/O (~25-26%) and tree/anchor (~14%) are comparably stable. Equihash's *share* climbs from ~6% to ~12% (captures 4->6) -- a percentage effect, not a cost effect (see per-block table below): capture 6 processed more blocks/sec, spreading a constant per-header cost over less wall-clock time per block.

**Per-block absolute cost, the more informative view:**

| Capture | Groth16 ms/block | Disk I/O ms/block | Tree/anchor ms/block | **Equihash ms/block** |
|---|---|---|---|---|
| 1 (pre-Sapling) | -- | 0.149 | 0.494 | **0.2557** |
| 2 | 2.149 | 0.983 | 0.543 | **0.2513** |
| 3 | 1.788 | 0.888 | 0.463 | **0.2493** |
| 4 | 2.324 | 1.050 | 0.587 | **0.2476** |
| 5 | 1.921 | 0.893 | 0.500 | **0.2541** |
| 6 | 1.005 | 0.543 | 0.288 | **0.2530** |
| **mean / CV** | 1.84ms / **27.7%** | 0.75ms / **45.7%** | 0.48ms / **21.5%** | **0.252ms / 1.2%** |

Groth16, disk I/O, and tree/anchor per-block cost all vary substantially (21-46% CV) -- expected, each scales with shielded-tx volume or block/undo-file size. **Equihash's per-block cost is essentially constant (0.252ms +/- 1.2% CV)** across pre- and post-Sapling heights and blocks/sec ranging 237-1,103 -- the signature of a fixed per-call cost independent of block content (root cause: §5).

**Not yet investigated:** nothing has targeted Groth16 verification cost specifically (§0 item 2) -- the latch (§4) and the proposed root-existence index (§0 item 4) both target the tree/anchor bucket only, ~6-14% of CPU, not the 48-60% Groth16 bucket.

**Memory profiling:** Instruments' Allocations/Leaks templates attach successfully (`task_for_pid`, entitlement + Developer Mode satisfied) but their recorded data is a GUI-only proprietary blob with no `xctrace export` schema in this Instruments version -- headless readout is a dead end via that template. `vmmap`/`heap`/`malloc_history` are CLI-native with no export-format dependency and haven't been tried yet (§0 item 5).

---

## 3. Disk I/O: open-close-per-block mechanism, and the implemented fix

**Parked.** Compiled out of release builds (`ZERO_FDCACHE` `#undef`), off by
default under `--enable-perf`, and no throughput win at either era
(M-CPU-FD-THR). Retained pending Linux/Windows validation; disposition is `docs/TASKS.md` **P8**.

**Mechanism.** `OpenBlockFile`/`OpenUndoFile` both call `OpenDiskFile`, which does a **fresh, unconditional `fopen()` on every call** -- no persistent or cached `FILE*` anywhere in this path. Every call site wraps the fresh `FILE*` in a stack-local `CAutoFile`, whose destructor calls `fclose()` unconditionally the moment the function returns. `ConnectBlock`/`LoadExternalBlockFile` call these once or twice per block (a read, usually an undo-data write) -- a full ~2.5M-block reindex therefore performs on the order of **2.5-5 million `fopen`/`fclose` pairs**, even though the underlying `blkNNNNN.dat`/`revNNNNN.dat` files are ~128MB each holding thousands of consecutive blocks: the overwhelming majority of those pairs reopen a file that was just closed moments earlier for the previous block. Each pair is a full kernel `open`/`close` round-trip, and `fopen` additionally re-initializes stdio's internal buffer from scratch every time -- cost paid once per block instead of once per file, a 100-1000x amplification.

**Direct syscall-level confirmation** (`fs_usage -f filesys -w <pid>`, root-only, always available, no SIP change needed unlike full `dtrace`; Instruments' File Activity template records real data but has no `xcrun xctrace export` schema in this Instruments version -- GUI-only, not usable headlessly): in a 180-second `-reindex` window, `open` alone was 23% of traced filesystem time; `open+close+stat64+fstat64` together came to ~0.048ms/block -- real, but only 6-34% of the disk-I/O bucket depending on capture window, meaning most of that bucket is genuine read/write/transfer time, not open/close overhead.

**The fix, `#ifdef ZERO_FDCACHE`-gated** (a macro separate from `ZERO_PERF`, independently buildable/strippable):

- **`-perffdcache=1`** (default 0): `ReadBlockFromDisk`/`UndoReadFromDisk` use a single-slot read-handle latch per file kind (`BlockFileKind::BLK`/`REV`) instead of `OpenDiskFile`'s fresh-open/close-per-call path -- mirroring `IncrementalMerkleTree::root()`'s latch (§4), not a multi-entry keyed cache. Ownership stays with the latch: `CAutoFile` borrows the handle for the duration of one read and is prevented from closing it on destruction via `ReleaseOnScopeExit`, a small RAII helper that calls `CAutoFile::release()` (an already-existing, pre-`ZERO_FDCACHE` method -- no changes to `CAutoFile`/`streams.h` were needed). Stats (opens/hits, plain counters under the latch's own lock) log periodically as `ReadFdCache: height=N opens=... hits=... hit-rate=...%`. Read-only handles only: write handles are excluded, since `FlushBlockFile`'s truncate/close and `CAutoFile`'s owning-close semantics make caching writable handles a real correctness hazard for a smaller expected benefit.
- **`-perfbufsize=N`** (default 0 = unchanged libc default): `setvbuf`s a freshly-opened handle to an N-byte buffer in `OpenDiskFile`, instead of the libc/filesystem default (commonly 4-8KB).

**Latch, not a multi-slot cache -- checked, not assumed.** An earlier version used a 4-slot LRU on the theory that RPC/reorg access could interleave across multiple files. Measuring real access during a `-reindex` run showed the open count grows strictly monotonically with no repeats for long stretches, then occasionally revisits an earlier file -- traced to `LoadExternalBlockFile`'s "out of order child" handling, which reprocesses an earlier block file when a later block's parent hasn't connected yet. A single-slot latch handles this correctly by design (a miss costs one `fopen`, not a correctness issue) -- measured hit rate stayed **99.9%** even across that access pattern, heights 0 through ~900,000.

**Implementation status: single-reader only.** `CacheOpen` (`main.cpp:4924`) drops `LOCK(latch.cs)` at return, so the caller reads the shared `FILE*` unlocked (`main.cpp:2130`, `:2617`) -- safe under the single-threaded reindex measured here, not under concurrent readers. Enabling it anywhere multi-reader needs an RAII lease across seek+read, or `pread`. Compiles clean with and without `ZERO_FDCACHE`; no unit test coverage. Only `main.cpp`/`main.h` carry changes -- `streams.h` and `init.cpp` ended at zero diff from upstream after an earlier, more invasive draft (a `CAutoFile` ownership flag, an unused `CloseAllCachedReadFiles` shutdown hook) was reviewed back out in favor of the smaller `ReleaseOnScopeExit` approach and removing dead code. Known, accepted gaps: `ReleaseOnScopeExit` is constructed (as an inert no-op) even in normal builds without `ZERO_FDCACHE`; no gtest exists for the latch's hit/miss/stale-reopen behavior, unlike §4's latch which has a dedicated test.

**Measured result: no throughput improvement from either flag, at pre-Sapling heights.** Repeated-trial A/B (`contrib/perf/bench_matrix.sh`: fixed height range warmup=50,000->measured 50,000-350,000, exact elapsed time from `debug.log` `UpdateTip` timestamps, 4 trials per condition, both with `-perffdcache=1`):

| Condition | n | Mean blk/s | Stdev | CV |
|---|---|---|---|---|
| Default buffer | 4 | 1,094.1 | 15.9 | 1.45% |
| 1MB buffer | 4 | 1,075.9 | 29.9 | 2.77% |

Difference: -1.66%, t ~ -1.07 -- not distinguishable from noise at this sample size (would need |t| > ~2.5-2.6 for significance with n=4 each). This establishes the noise floor this methodology resolves at a 300,000-block window: ~1.5-3% CV per condition. Consistent with average block size (~1.3-2KB) being far smaller than either buffer setting.

**Re-measured at post-Sapling heights, with a true no-fdcache baseline added (§0 item 1).** The original A/B above never tested `-perffdcache` against a real off condition (every trial had `-perffdcache=1`), and only covered pre-Sapling heights. `bench_matrix.sh` was extended with a third `nofdcache` condition (`-reindex` with neither flag -- the fd-cache code path entirely inactive) and re-run at warmup=600,000->measured 600,000-900,000 (entirely post-Sapling; activation is 492,850), 4 trials per condition, 3 conditions:

| Condition | n | Mean blk/s | Stdev | CV |
|---|---|---|---|---|
| No fd-cache | 4 | 307.22 | 5.615 | 1.83% |
| Default buffer (fdcache on) | 4 | 310.56 | 0.261 | 0.08% |
| 1MB buffer (fdcache on) | 4 | 309.28 | 0.000 | 0.00% |

`ReadFdCache` log lines confirm the mechanism itself is engaging correctly at these heights: `nofdcache` trials show `opens=0 hits=0` throughout (code path genuinely inactive, not just untuned), while both fdcache-on conditions show **99.9% hit rate** -- identical to the pre-Sapling hit rate found earlier, confirming §3's single-slot-latch design holds at post-Sapling heights and shielded-tx volumes too.

**Result: still no measurable throughput win, now with the isolation this item set out to get.**
- **fd-cache on vs. off** (no-fdcache -> default-buffer): +1.09%, t ~ 1.19 -- not distinguishable from noise (same |t| > ~2.5-2.6 bar as before).
- **Buffer size, fd-cache held on** (default-buffer -> 1MB-buffer): -0.41%, t ~ -9.80 -- a real, statistically clear *difference*, but in the wrong direction (1MB buffer is *slower*) and tiny in absolute terms (1.3 blk/s); most plausibly page-cache/allocation overhead from a 1MB `setvbuf` buffer per open handle outweighing any I/O-batching benefit at these small (~1.3-2KB) block sizes, not a real optimization opportunity.
- **Combined** (no-fdcache -> 1MB-buffer): +0.67%, t ~ 0.73 -- not distinguishable from noise.

This closes §0 item 1's open question: post-Sapling heights behave the same as pre-Sapling did -- the fd-cache mechanism works exactly as designed (99.9% hit rate, confirmed genuinely inactive in the off condition) but produces no measurable reindex throughput improvement, isolated from buffer size, at either pre- or post-Sapling heights. Disk I/O's remaining headroom (§2: ~25-26% of CPU post-Sapling) is dominated by genuine read/write/transfer time, not open/close overhead -- consistent with §3's earlier `fs_usage` finding that open/close/stat together were only 6-34% of the disk-I/O bucket.

**A datadir-reset bug found and fixed while building the bootstrap-import benchmark leg.** `bench_matrix.sh`'s scratch-datadir reset originally used one procedure for both `-reindex` and `-loadblock` trials -- rsync excluding only `chainstate`. Correct for `-reindex` (which rescans existing `blk*.dat`/`rev*.dat` by design), wrong for `-loadblock`: reusing a fully-synced source's `blocks/` directory made `-loadblock` reconcile its import against an already-populated, multi-million-block index instead of starting from an empty chain. Fixed: bootstrap-mode resets now also exclude `blocks/`. Before the fix, `LoadBlockIndexDB` reported an existing index spanning `heights=2440414...2484412` and RPC stayed in `"Loading block index..."` (`getblockcount` returning error -28) for over 50 minutes before any import progress was measurable; after the fix, RPC comes up and warmup height is reached within seconds.

**A narrow-blast-radius interruptibility gap found while diagnosing the above (pre-existing, upstream-inherited -- not introduced by this work).** The stuck process couldn't be stopped by RPC `stop` (not up yet) or `SIGTERM` (no effect for 50+ minutes) -- traced to `LoadBlockIndexDB`'s per-block accounting loop (the `BOOST_FOREACH` over `vSortedByHeight` building `nChainWork`/`nChainTx`/branch-ID data), which has exactly one `interruption_point()` call *before* the loop starts and none inside it. On a multi-million-block index this loop alone can run for tens of minutes with no way to interrupt it short of `SIGKILL`. Only reachable when reconciling a very large pre-existing index (not normal `-reindex`/`-loadblock` usage). `bench_matrix.sh` now bounds every wait loop to 10 minutes and escalates `SIGTERM` then `SIGKILL` automatically.

**Tooling:** `contrib/perf/bench_matrix.sh` -- repeated-trial A/B harness for any `-perffdcache`/`-perfbufsize` combination, against `-reindex` and (given a `bootstrap.dat` path) `-loadblock`. See `contrib/perf/README.md` for usage.

**G6 (accepted queue):** when FDCACHE resumes, add **8192** and **16384** bufsize conditions vs libc default and 1048576 -- 1MB already looked slightly worse; mid-size buffers test the "syscall vs cache pressure" hypothesis without assuming 1MB is optimal.

**Why it is retained, and the two cases that could still pay.** The null above is established for **sequential reindex on macOS/arm64 with a warm page cache** -- one platform, one access pattern. macOS stdio does not predict Linux or Windows, which is the same reasoning that keeps `docs/TASKS.md` B2 open. Two workloads have the opposite access pattern and are unmeasured:

- **Random `getblock` / REST / explorer serving.** Consecutive requests hit *different* `blk*.dat` files, so each read pays the `fopen`+`fclose` the latch would elide. Sequential reindex hits the same file repeatedly, which is why the cache had nothing to save there. Measure by driving `getblock` over a random height sample against a synced node, with and without `-perffdcache`, comparing **RPC latency percentiles**, not throughput.
- **Cold cache / slow storage.** The 4.91% syscall share assumes the page cache already holds the data. On first touch, or on network/spinning storage, the read itself dominates and buffer size becomes relevant. Same reindex window with the page cache dropped between trials -- Linux only (`/proc/sys/vm/drop_caches`), so a B2 item.

**Both are latency questions, not throughput questions**, which is why the existing throughput harness measured nothing: it was the wrong instrument for the case where the mechanism helps. The reindex null stands and neither contradicts it.

**The RPC case is gated on the concurrency fix.** Multiple simultaneous readers are exactly the unsafe condition above, so the lock lifetime must be fixed **before** any multi-client `getblock` measurement -- otherwise the experiment measures an unsafe path. Task state: `docs/TASKS.md` **P8** (postponed).

---

## 4. The Merkle-root latch

**The confirmed inefficiency.** `IncrementalMerkleTree::root()` recomputes fully from `left`/`right`/`parents` on every call -- a real `Hash::combine()` -> `librustzcash_merkle_hash` FFI call per populated tree level. `ConnectBlock` calls `sapling_tree.root()`/`sprout_tree.root()` **twice per block, unconditionally**: once inside `PushAnchor`->`AbstractPushAnchor`, once directly -- computing the identical value both times whenever nothing mutated the tree in between.

**Fix:** a `mutable boost::optional<Hash> cached_root` latch on `IncrementalMerkleTree`, populated on first `root()` call, cleared in the only two places that mutate tree state (`append()`, post-deserialize). Pure memoization of a deterministic function of existing state -- no change to what's hashed, so no consensus or serialization-format risk.

**Why it helps `ConnectBlock` but not `HaveShieldedRequirements` -- value vs. reference.** `AbstractPushAnchor` takes `tree` by const reference, so `ConnectBlock`'s two calls operate on the same object -- the first populates the latch, the second matches it. `CCoinsViewCache::HaveShieldedRequirements`, which validates each Sprout joinsplit's anchor, declares its tree **by value, freshly, inside the per-joinsplit loop** -- a brand-new object every iteration, mutated once and read once before going out of scope. There is structurally no second read on the same object for the latch to ever serve -- every call here is a guaranteed no-match, regardless of implementation.

**Validation.** Existing gtest suite passes unmodified; a new test (`merkletree.RootCacheConsistency`) exercises match/no-match behavior across append and serialize/deserialize round-trips; full regression (Boost `test_bitcoin` 284/284, `zero-gtest` 206/206) clean, with a pre-existing unrelated wallet-key test flake (~1-in-9 runs, present on the unmodified baseline too) ruled out as false attribution. The instrumentation (`libzcash::MerkleRootCacheStats`) is `#ifdef ZERO_PERF`-gated and confirmed to leave zero trace in a normal build via `nm`; full regression on that clean build (Boost 284/284, gtest 207/207) shows no regressions from the removal.

**Measured impact: correct, but flat.** Re-profiled with the same methodology: Sapling-tree bucket 57.9% vs. the pre-fix 58.0% baseline -- no measurable change, despite the latch being demonstrably active. Ground-truth per-block counters (since removed, superseded by coarser periodic logging) explain why:

| Block category | avg `root()` calls/block | match rate |
|---|---|---|
| Idle (no shielded activity) | 5.00 | **100%** |
| Sapling outputs only | 5.00 | 80% |
| Sprout joinsplits only | 8.28 | 48.3% |
| Both | 8.22 | 36.4% |

Idle and Sapling-output-only blocks match perfectly but were already cheap (empty/near-empty tree). **Sprout joinsplits drive both the extra call volume and the low match rate**, since each joinsplit's anchor is checked via `HaveShieldedRequirements`'s fresh-object pattern -- structurally unmatchable. Sapling spends never call `.append()`/`.root()` in that function, so they were never a candidate for this latch either way. **Conclusion: the latch is correct and removes a real, confirmed redundancy, but that redundancy was a small, cheap-skewed slice of the bucket.** The bucket's real cost is (a) genuinely new `append()`/`combine()` work proportional to shielded-output volume -- unavoidable -- and (b) Sprout-joinsplit anchor validation's fresh-object-per-joinsplit pattern, which no per-object latch can help by construction.

**Latch vs. cache -- checked against Zebra directly, not assumed.** Zebra's own Sprout tree type uses the identical single-slot latch pattern (`cached_root: RwLock<Option<Root>>`, cleared on `append()`), confirming a keyed cache isn't the standard answer here either. The real difference: Zebra's Sapling/Orchard anchor validation never constructs a tree object during validation at all -- it checks anchor membership against a `HashSet`/RocksDB key-existence check, populated once at commit time -- a *different technique* (a membership index over previously-seen roots), not a bigger cache. Zebra's Sprout path still pays the same construct/append/read cost for **chained joinsplits within one transaction** as Zero does, by its own source's admission ("this check is expensive, because it updates a note commitment tree for each sprout JoinSplit"). **So a keyed/multi-entry cache would not have helped `HaveShieldedRequirements` either** -- the actual problem isn't insufficient memoization, since Zebra hits the identical wall despite a mature, independent implementation. The membership-index technique is the concrete lead for further work, not a bigger latch.

**Implemented then undone: membership-index `Have*AnchorAt` (§0 item 3).** Zebra-style existence checks (`db.Exists` on the root key, no tree deserialize) were added through the `CCoinsView` chain and wired into `HaveShieldedRequirements` for single-JoinSplit / Sapling-spend cases. Expected win: skip tree loads in the small tree/anchor CPU bucket. **Never measured as a throughput win.** Wiring into `HaveShieldedRequirements` broke ATMP: that path calls the check under tip/mempool, then `SetBackend(dummy)`, then checks again -- `Get*AnchorAt` warms the cache for the second call; existence-only `Have*` does not, so dummy => reject (`JoinSplit requirements not met`). **Removed the `Have*AnchorAt` API** (no caller left that needed it). `HaveShieldedRequirements` stays on `Get*`. Regression: `coins_tests/shielded_survive_dummy`. Revisit only with a non-ATMP caller and a measured win; do not re-plumb into `HaveShieldedRequirements` without that test.

---

## 5. Equihash's CPU share: a libsodium/ARM gap, not an algorithm issue

**The question.** §2 showed Equihash verification taking 6-28% of CPU depending on height, with `blake2b_compress_ref` recurring in every sample. Given Equihash verification is supposed to be cheap by design (asymmetric proof-of-work), is this a real inefficiency? **Answer: the algorithm is correct and minimal; the cost is a missing SIMD backend, specific to this build's architecture.**

**The algorithm itself is correct and lightweight.** `Equihash<N,K>::IsValidSolution` does exactly what the spec requires for mainnet's `Equihash<192,7>`: `2^K = 128` calls to `GenerateHash` (one blake2b invocation each), followed by a 7-round collision/ordering/distinctness check using only `memcmp`/XOR-style comparisons -- no re-solving, no search, no redundant hashing. There is no algorithmic bug here.

**The cost is entirely inside blake2b's compression function, running unaccelerated on this hardware.** Every one of the 128 per-block hash calls goes through libsodium (not the Rust `blake2-rfc` crate also vendored in this tree -- that's for something else). libsodium 1.0.21 dispatches its blake2b compression function at runtime via `blake2b_pick_best_implementation()`, choosing between `avx2`/`sse41`/`ssse3`/`ref` backends -- but **all three accelerated backends are gated behind x86-only intrinsics headers**. On `aarch64-apple-darwin` (Apple Silicon), none of those headers exist, so the dispatcher unconditionally falls through to `blake2b_compress_ref`, the plain scalar C implementation, for every call.

**Checked and ruled out: no fix via upgrading dependencies or Apple's native crypto.** libsodium has released twice since 1.0.21 (1.0.22, 2026-04-09, current) -- its actual `ChangeLog` shows post-increment KEMs and new SHA-3 APIs, no mention of blake2b or ARM vector work anywhere. Across every release checked (1.0.18-1.0.22), ARM/aarch64 wins landed for AES-GCM, AEGIS, and Argon2/SHA3 -- blake2b has never once been included; a version bump is confirmed not to fix this. Apple's CryptoKit has no BLAKE2b support at all (SHA-2/AES/legacy only).


**Resolved 2026-09-02: the recommendation above was implemented, via uniblake.** Option (b) was taken -- `equihash.cpp` no longer calls libsodium's generichash API at all; it calls uniblake (`ub_init_personal` / `ub_update` / `ub_hash_tail`) through `crypto/eh_hashstate.h`. libsodium is retained unchanged for Ed25519, `randombytes_buf` and the seven files that still use `crypto_generichash_blake2b_*` (see **`docs/HASHLIBS.md`** for the full division). Measured 2.03x on the Equihash access pattern, against libsodium 1.0.22 built -O3, harness at -O2.

**One prediction in this section did not hold.** The gain was expected from a vectorised compression function. It came instead from the call structure -- the same prefix is hashed once rather than per call -- which is why the two libraries are within 1-2% on bulk data. Mechanism and measurements: `docs/HASHLIBS.md` S2.

**The vectorisation track for blake2b is closed, on measurement.** The kernel
question belongs to uniblake, which owns the implementation and the benchmark;
ZeroPerf adopts its result rather than restating it. See `docs/HASHLIBS.md` for
the division of labour and the Zero-level effect.

References to a blake2b SIMD backend elsewhere in this document are historical and are not open work.

The version-bump conclusion above is independently confirmed and stronger than stated: blake2b is **byte-identical** between 1.0.21 and 1.0.22 -- the only source difference is `LCOV_EXCL_LINE` comments, and the compress kernel compiles to identical assembly (`docs/SODIUM_SURVEY.md` S5).

**Independent confirmation this is a fixed, hardware-level cost, not something content-dependent:** Equihash's per-block cost held constant at 0.252ms +/- 1.2% CV across six capture windows spanning pre- and post-Sapling heights and blocks/sec ranging 237-1,103 (§2's per-block table) -- versus 21-46% CV for every other bucket, all of which scale with shielded-tx volume or block size. A cost that doesn't move with any chain-content variable is exactly what "fixed per-header hashing cost, paid by an unaccelerated compression function" predicts.

---

### 6.2 Cross-ecosystem status: who else has and has not adopted batch verification

**Question.** §6.1 found `sapling-crypto`'s `BatchValidator` and confirmed Zebra uses it. How widely has this actually propagated across the rest of the Zcash-descended node ecosystem -- is Zero unusually behind, or is unbatched verification still the norm among comparable forks? Checked five real, currently-active repositories directly (fetched each fresh this session, not from memory).

| Project | Relationship to Zero | Status, `pushed_at` (fetched this session) | Sapling proof verification |
|---|---|---|---|
| **`zcash/zcash`** (`zcashd`) | Common ancestor -- Zero and every fork below descend from this codebase | Active but **being sunset**: repo's own README declares `zcashd` deprecated, automatic end-of-life node halt estimated **2026-07-18 at block height 3,417,100** (~10 days out at the time of this check), migration path is to Zebra (full node) or Zallet (wallet-only) | **Batches.** `ContextualCheckShieldedInputs` calls `tx.GetSaplingBundle().QueueAuthValidation(*saplingAuth, dataToBeSigned)` per transaction (`main.cpp:1417-1425`) into one `rust::Box<sapling::BatchValidator>` created per block (`main.cpp:3306-3307`, gated on `fExpensiveChecks`), validated once after the whole block's tx loop (`main.cpp:3847`: `saplingAuth.value()->validate()`) |
| **Zebra** (`ZcashFoundation/zebra`) | Independent Rust reimplementation, not a zcashd fork, but the reference "modern" architecture | Active, primary recommended node going forward per `zcashd`'s own deprecation notice | **Batches**, confirmed in §6.1 -- `zebra-consensus/src/primitives/sapling.rs` wraps `sapling_crypto::BatchValidator` in a `tower_batch_control::Batch` async service, `MAX_BATCH_SIZE=64`/`MAX_BATCH_LATENCY=100ms`. Also confirmed this session: Zebra's `Cargo.toml` enables `sapling-crypto`'s `"multicore"` feature -- it runs the `rayon`-parallel `verify_multicore` path (§6), not just single-threaded batching |
| **Pirate Chain** (`PirateNetwork/pirate`) | zcashd fork, same lineage as Zero | Active, `pushed_at` within 1 day of this check | **Batches** -- a real, complete port: maintains its own vendored `src/rust/` crate wrapping `sapling_proofs::BatchValidator` behind a `cxx` bridge (`src/rust/src/sapling.rs`, `src/rust/src/bridge.rs`), mirroring the modern `zcashd`/Zebra architecture rather than calling out to an external crate directly. Not a stray reference -- real `init_batch_validator`/`validate` wiring matching the same shape as `zcashd`'s. **The one fork checked that has already done the work this investigation is scoping.** |
| **Komodo** (`KomodoPlatform/komodo`) | zcashd fork, same lineage as Zero | Active, `pushed_at` within 2 weeks of this check | **Unbatched** -- still calls `librustzcash_sapling_check_spend` directly (`main.cpp:1328`), the same raw-C FFI, one-proof-at-a-time pattern Zero has today. Zero confirmed `BatchValidator` references anywhere in `src/` |
| **VerusCoin** (`VerusCoin/VerusCoin`) | zcashd fork, same lineage as Zero | Active, `pushed_at` within 1 week of this check | **Unbatched** -- same `librustzcash_sapling_check_spend` call pattern (`main.cpp:1411`), zero `BatchValidator` references |
| **Ycash** (`ycashfoundation/ycash`) | zcashd fork, same lineage as Zero | Active, `pushed_at` within ~2 months of this check | **Unbatched** -- same pattern (`main.cpp:1148`), zero `BatchValidator` references |

**Reading this table.** Batch verification is not a fringe or experimental idea in this ecosystem -- it's the architecture of the two most-current, most-actively-developed implementations (`zcashd` itself, right up to its own end-of-life, and Zebra, its designated successor), and at least one structurally-comparable fork (Pirate Chain) has already done the exact migration Zero is scoping. But it is **not universal** -- three other zcashd-lineage forks checked (Komodo, VerusCoin, Ycash) are all still on the same unbatched, per-proof `librustzcash_sapling_check_spend` pattern Zero has. **Zero is in the majority position among forks, not an outlier** -- most zcashd descendants haven't done this migration either, which is useful context on how much fork-maintenance effort this realistically represents (it isn't something every fork picks up for free; Pirate Chain is the exception, not the rule).

**One architecturally significant difference found in `zcashd`'s current batch-failure handling, relevant to §9.4's Phase 4 design.** §9.4's fallback plan (Phase 4, item 16) was designed to preserve today's exact per-transaction error codes on batch failure, by falling back to per-proof `verify_single` to identify which transaction to reject. **Current `zcashd` does not do this.** Its `saplingAuth.value()->validate()` check at `main.cpp:3847-3851` rejects the *entire block* with one generic error (`"bad-sapling-bundle-authorization"`) on any batch failure -- there is no per-transaction re-verification or attribution anywhere in this path. The code comment there references a real fixed security issue (`GHSA-g4x5-crjh-29ff`, about binding-signature check ordering relative to a chain-supply consistency check) but says nothing about per-tx attribution being a design goal at all. This means §9.4's fallback-for-attribution design is **more conservative than what upstream `zcashd` itself now ships** -- not wrong, but worth an explicit decision: whether Zero's Phase 4 should match upstream's simpler whole-block-reject behavior (less code, matches the reference implementation's current consensus behavior) or keep the more careful per-tx-attributed fallback originally planned (more code, better error messages/ban-scoring granularity, matches Zero's *own* current single-proof behavior exactly). Not decided here.

**Doesn't change the hand-port-vs-adopt fork in the road from §6.1**, but adds real weight to it: the "adopt upstream" option now has two working reference implementations to study (current `zcashd`'s `cxx`-bridge integration and Pirate Chain's, which -- as a same-lineage C++ fork -- is the closest architectural precedent to what Zero would actually need to build, more so than Zebra's from-scratch Rust design).

---

## 7. Memory profiling: `AddToBlockIndex` dominates, Groth16 verification allocates nothing

**The question (§0's memory-profiling item).** Instruments' Allocations/Leaks templates attach successfully but produce a GUI-only proprietary blob with no `xctrace export` schema in this Instruments version (§2) -- a documented dead end for headless use. `vmmap`/`heap`/`malloc_history` are CLI-native with no export-format dependency; this section is their first real use against a live `-reindex`.

**Method.** `vmmap -summary <pid>` gives `Physical footprint` at a point in time -- used here to build a footprint-vs-height timeline via a small driver (`reindex-profile/memprofile/snapshot_at_heights.sh`) that polls `getblockcount` and snapshots at fixed height checkpoints. `heap <pid>` gives a live per-size-class allocation census, no special launch flags needed. `malloc_history <pid> -callTree` gives a full allocation-site call tree attributing every live allocation to the code path that made it -- but only for allocations made *after* `MallocStackLogging=1` is set, so this needed a separate `-reindex` launched with that environment variable (real, non-trivial overhead: stack-logging is not something to leave on for a full multi-hour chain reindex, so this run was capped at a representative window rather than run to chain tip).

**Footprint grows with chain length, not unboundedly -- no leak signature found -- but `vmmap`'s headline `Physical footprint` number is confounded by macOS memory compression over a run this long, and a naive read of it tells a misleading story.** Full-chain sweep, six checkpoints from height 278,072 to chain tip (2,470,587, matching this repo's documented ~2.47M-block chain):

| Height | `Physical footprint` | `Writable regions: Total` (written address space) | Swapped/compressed |
|---|---|---|---|
| 278,072 | 535.3M | 702.0M | 0K (0%) |
| 500,436 | 956.1M | 1.1G | 0K (0%) |
| 901,000 | 1.6G | 1.7G | 1.2G (71%) |
| 1,500,605 | 2.4G | 3.5G | 73.6M (2%) |
| 2,001,804 | 2.9G | 4.2G | 315.5M (7%) |
| 2,470,587 | 3.1G | 4.7G | 1.8G (38%) |

**Reading `Physical footprint` alone produces a spurious "growth rate is slowing down" story: 1.94 -> 1.74 -> 1.40 -> 1.05 -> 0.45 KB/block across the five segments -- a suspiciously clean monotonic decline that doesn't survive a second look.** `Physical footprint` nets out macOS's memory compressor, and the "swapped/compressed" column above shows *why* it can't be trusted alone here: compression kicks in unevenly (0% for the first two checkpoints, a spike to 71% at height 901,000, then 2-38% afterward) as system-wide memory pressure varies over this ~2-hour run -- that's a fact about *this machine's other memory demand during the run*, not about `zerod`'s own allocation behavior. **`Writable regions: Total`** (the total address space actually written to, unaffected by whether pages are later compressed) tells a cleaner story: it grows from 702.0M to 4.7G, monotonically, at a much less dramatically-declining rate (1.83, 1.53, 3.07, 1.43, 1.09 KB/block -- noisier, with one high-swap-affected segment reading anomalously high, but no clean downward trend). **Lesson for any future memory-profiling work here: use `Writable regions: Total`, not the headline `Physical footprint` figure, when comparing checkpoints spread over a long enough run for compression pressure to vary** -- this is the same class of mistake §1's methodology repeatedly warns about (don't trust one source without cross-checking against a second).

**Net conclusion:** see Measures **M-MEM-VMMAP** / **M-MEM-GROWTH** / **M-MEM-ALLOC** / **M-MEM-PARAMS**. Memory grows roughly linearly with chain length (no leak signature), ~1-3KB/block Writable; `AddToBlockIndex` dominates retained heap; Groth16 verify allocates nothing on the heap.

**Allocation-site breakdown (`malloc_history -callTree`, 673-second stack-logged window spanning roughly height 20,198 -> 501,321, i.e. crossing Sapling activation):** ~987MB total tracked allocation across the window, essentially all of it (896MB, >90%) under the single `ThreadImport` worker thread, confirming again (as in §1's profiling methodology) that this is where real work happens. Within that:

| Call path | Allocation | Share of `ThreadImport` |
|---|---|---|
| `AddToBlockIndex` (building the permanent `uint256`->`CBlockIndex*` block-index map + per-header metadata) | ~589MB | ~66% |
| `CCoinsViewCache::Flush`/`BatchWrite` (flushing coins/anchor/nullifier caches to the LevelDB-backed chainstate) | ~160MB+ (multiple call sites) | ~18%+ |
| `CCoinsViewCache::HaveShieldedRequirements` -> `GetNullifier` (nullifier-set cache insertion) | ~37MB (main pass) + ~4.8MB (reprocessing pass) | ~4% |
| `CCoinsViewCache::HaveInputs`/`FetchCoins`/`GetCoins` (transparent UTXO cache population) | ~29.8MB + ~9.5MB | ~4% |

**`AddToBlockIndex` is the single largest identifiable allocation site -- expected, not a bug.** It permanently retains one `CBlockIndex` object (plus a `vector<unsigned char>` for header-adjacent data and a hash-map entry) per block header for the lifetime of the process -- by construction, chain-length-proportional, never freed, never meant to be. At ~589MB for roughly 480,000 headers in this window, that's on the order of ~1.2KB/header of permanent retained memory -- consistent with `CBlockIndex`'s field set (hashes, work, heights, pointers) plus map/allocator overhead. Confirms this is the primary driver of the footprint-vs-height growth measured above, not a separate or surprising cost.

**Confirmed: Sapling Groth16 proof verification allocates essentially nothing on the heap.** Despite dominating CPU (48-55% of chain-wide CPU per §2) and this stack-logging window spanning well past Sapling activation, `librustzcash_sapling_check_spend`/`_check_output`/`verify_proof`/`miller_loop`/`final_exponentiation` appear **zero times** anywhere in the call tree. The only Groth16-adjacent allocation found at all is `librustzcash_init_zksnark_params` (~58MB, ~4.9MB, and a handful of smaller frames) -- one-time proving/verifying-key loading at process startup, not a per-verification or per-block cost. This cleanly decouples §2's CPU-dominant bucket from the memory profile: BLS12-381 field/pairing arithmetic operates on fixed-size stack types, so verifying more proofs costs CPU time but not heap growth -- a useful confirmation that Groth16 verification (and by extension, any future batch-verification work per §6) is not a memory-scaling concern, only a CPU one.

**Full-chain footprint timeline: complete.** The height-checkpoint sweep ran to chain tip (2,470,587); see the table above. Not done: re-running `malloc_history`/`MallocStackLogging` at a window sampled entirely post-Sapling-activation specifically -- the stack-logged window above happens to straddle the Sapling activation boundary but is dominated by pre-activation volume by block count, so its allocation-site percentages likely understate Sapling-Groth16-adjacent bookkeeping (anchor cache writes, nullifier-set growth) relative to a window sampled entirely post-activation. Given §7's headline finding -- Groth16 verification itself allocates nothing, and `AddToBlockIndex` (a cost with no Sapling-specific component at all) dominates -- a second stack-logged window is unlikely to change the qualitative conclusion, so this is left as a documented gap rather than pursued further.

---

## 8. `AddToBlockIndex` per-block allocation detail, and two dead ends chased down

**Motivation.** §7 reported `AddToBlockIndex` as ~66% of tracked allocation and ~1.2KB/header, as an aggregate. This section breaks that aggregate into its actual per-call allocation sites (piece count, size, lifetime) using the same `malloc_history -callTree` raw data §7 summarized, and resolves two follow-up questions: what the `CBlockIndex` "Shieldex" stat fields cost and who uses them, and what was actually behind an unexplained large-average-size Rust allocator (`alloc::raw_vec::finish_grow`) visible in the raw trace.

### 8.1 `AddToBlockIndex` -- 4 heap allocations per block

Site: `main.cpp` around the `AddToBlockIndex` implementation used on the import path.

| # | Site (`main.cpp` offset) | What | Count (stack-logged window) | Avg size | Total | Lifetime |
|---|---|---|---|---|---|---|
| 1 | `+212`: `new CBlockIndex(block)` | the `CBlockIndex` object itself | 423,978 (~1/block) | 344 bytes | 259M | **Permanent** -- owned by `mapBlockIndex`, never freed for the life of the process |
| 2 | `+432`: `nSolution = block.nSolution` (in the `CBlockIndex(const CBlockHeader&)` ctor) | Equihash solution bytes, `vector<unsigned char>` copy | 423,978 | 448 bytes | 181M | Permanent -- lives inside the `CBlockIndex` from (1) |
| 3 | `+476`: `mapBlockIndex.insert(make_pair(hash, pindexNew))` | one node in `boost::unordered_map<uint256, CBlockIndex*, BlockHasher>` (`main.h:136`) | 423,978 | 64 bytes | 25.9M (+ occasional 6M/1.5M rehash bucket-array grows) | Permanent -- the map is never cleared |
| 4 | `+996`: `setDirtyBlockIndex.insert(pindexNew)` | one node in `std::set<CBlockIndex*>` (`main.cpp:252`) | 423,978 | 48 bytes | 19.4M | **Transient** -- cleared each time the dirty set flushes to `CBlockTreeDB` (periodic, not per-block) |

**Per block, steady state: 4 allocations, ~904 bytes**, of which ~856 bytes/block (~95%) is **permanently retained** (the `CBlockIndex` object + its embedded Equihash-solution vector + the map entry) and ~48 bytes/block is transient, reclaimed on the next dirty-set flush. This is the mechanism behind §7's measured ~1.2KB/header figure (the gap between 904 raw bytes and ~1.2KB is allocator bucket-size rounding -- confirmed against `heap`'s own size-class histogram, which shows no exact 904-byte class, the nearest classes being 896 and larger).

Other per-block-scaling (but not literally-every-block; these fire per shielded-tx / per-flush-cycle rather than unconditionally) allocation sites in the same window, for reference: `CCoinsViewCache::BatchWrite`'s `BatchWriteAnchors` (Sprout tree snapshots, ~695 bytes/entry, 104M total) and its Sapling counterpart (~434 bytes/entry, ~1.4M total), nullifier-cache-entry insertion (~64 bytes/entry, ~35M total across three call sites), and UTXO-cache-entry insertion (~96 bytes/entry, ~20M total). All four are **transient** -- evicted from the in-memory `CCoinsViewCache` on the next flush to the LevelDB-backed chainstate, not permanently retained the way `AddToBlockIndex`'s output is. This confirms §7's growth-driver finding at the individual-allocation-site level: only `AddToBlockIndex` explains the linear, unbounded-by-flush-cycle chain-length-proportional growth curve -- the cache-write churn is real but bounded.

### 8.2 The "Shieldex" fields in `CBlockIndex`: reviewed, mostly gated correctly, one dead field found

**What they are.** `CBlockIndex` (`chain.h:164-338`) carries two parallel groups of `int64_t` fields beyond stock zcashd's layout -- one set of 11 per-block counters (`nPayments`, `nShieldedTx`, `nShieldedOutputs`, `nFullyShieldedTx`, `nShieldingPayments`, `nShieldedPayments`, `nFullyShieldedPayments`, `nDeshieldingTx`, `nDeshieldingPayments`, `nShieldingTx`, `nNotarizations`) and a matching set of 11 `nChain*`-prefixed cumulative-from-genesis counters. Populated in `ReceivedBlockTransactions` (`main.cpp:4005-4165`): the per-block counters are computed once per block by walking `block.vtx` and classifying each transaction by shielded-input/output shape (fully-shielded `z->z`, shielding `t->z`, deshielding `z->t`, etc. -- see the heuristic and its own documented caveats at `main.cpp:4043-4105`, which acknowledges this is a best-effort classification, not exact); the `nChain*` counters are running sums, each computed as `pprev->nChain* + this->n*` while walking newly-connectable blocks (`main.cpp:4150-4160`).

**Real consumer confirmed: `getblockchaininfo`-adjacent RPC (`src/rpc/blockchain.cpp`).** `nChainShieldedTx`, `nChainNotarizations`, and the rest feed an RPC endpoint whose own help text says it "will return a large amount of additional data if the shielded index (zindex) is enabled" (`rpc/blockchain.cpp:1238`) -- computing shielded-tx rate, shielding/deshielding/fully-shielded percentages, and an "organic" (non-notarization) tx-rate estimate over a time window (`rpc/blockchain.cpp:1337-1424`). Not dead code, not speculative -- a real, used feature.

**Correctly gated on disk, not gated in memory.** Population is conditional (`if (!fZindex) continue;` at `main.cpp:4036`, and the `nChain*` rollup is behind its own `if (fZindex)` at `main.cpp:4147`), and **disk serialization is correctly gated too** (`chain.h:582-594`: `if ((s.GetType() & SER_DISK) && fZindex) { READWRITE(nShieldedTx); ... }` -- all 11 per-block fields, comment-flagged "Order is important!"). `fZindex` defaults to `false` (`DEFAULT_SHIELDEDINDEX`, `main.h:115`; confirmed via `init.cpp:391`'s help text, `default: 0`) -- most nodes never populate or serialize these. **But the struct layout itself is unconditional**: all 22 `int64_t` fields (11 + 11 `nChain*`) exist in every `CBlockIndex` instance in RAM regardless of `-zindex`, costing ~176 bytes/block of always-present, usually-always-zero memory chain-wide (~176 bytes x 2.47M blocks ~ 435MB at chain tip) -- folded into but not separately broken out in §8.1's 344-byte average `CBlockIndex` size above. This is a real, quantifiable cost of having the feature compiled in, paid by every node whether or not `-zindex` is ever turned on; not a bug, but worth knowing if `CBlockIndex`'s in-memory footprint is ever a target (it is the single largest identified allocation site chain-wide per §7).

**One dead field found: `nNotarizations`.** Declared, zero-initialized, summed chain-wide into `nChainNotarizations`, exposed via RPC (`rpc/blockchain.cpp:1337,1365`) -- but the only code that would ever increment it is a commented-out heuristic (`main.cpp:4044-4049`, with its own inline `TODO` about false-positive risk). It has stayed `0` for the life of this field. Not a correctness bug (RPC will just always report `notarizations: 0`/rate `0`), but it's dead weight: 8 bytes/block in `CBlockIndex` (16 with its `nChain*` counterpart) plus a disk-serialized field when `-zindex` is on, for a value that can never be anything but zero. Worth either implementing the heuristic for real or removing the field -- currently neither.

**Not investigated further (out of scope here): whether shrinking `CBlockIndex`'s in-memory footprint -- e.g. gating the Shieldex fields out of the struct entirely behind a compile-time or even runtime flag, rather than just gating their population/serialization -- is worth pursuing.** Given `AddToBlockIndex` is §7's largest single allocation site and these fields are ~50% of the non-Equihash-solution portion of the object (176 of ~344 bytes), this is a plausible follow-up memory-focused optimization target, but sizing the actual win and the runtime-flag-vs-recompile tradeoff hasn't been done.

### 8.3 `alloc::raw_vec::finish_grow`: resolved -- startup-only Groth16 parameter loading, not a per-block cost

**The question.** A prior pass over the raw `malloc_history` trace flagged `alloc::raw_vec::finish_grow` (Rust's generic `Vec` growth-reallocation routine) as the largest average-allocation-size symbol in the whole trace (reported as "1,062 count, 62.9KB avg, 66.8M total"), with "unidentified specific caller" -- `finish_grow` is a single generic-monomorphized-but-symbol-collapsed function, so a flat grep across the trace merges every distinct call site that ever reallocates a growing `Vec` into one apparent hot spot.

**Resolution: not one caller -- re-attributing each `finish_grow` occurrence to its actual immediate caller in the trace splits it cleanly.**

| Caller | Count | Total bytes | What it is |
|---|---|---|---|
| `bellman::groth16::Parameters<E>::read` | 12 | 62.91M | Deserializing the Sapling proving/verifying-key file |
| `sapling_crypto::jubjub::JubjubBls12::new` | 1,678 | 0.88M | Jubjub curve parameter-table construction |
| `pairing::bls12_381::ec::g2::G2Affine::prepare` | 6 | 0.28M | Precomputing a G2 point for pairing |
| (two single-allocation call sites, <1K each) | 2 | ~0.001M | -- |

**The 62.9MB is `librustzcash_init_zksnark_params`, called exactly once at process startup (`init.cpp:790`), not inside the reindex loop.** This matches and reinforces §7's existing finding almost exactly -- §7 had already identified `librustzcash_init_zksnark_params` as "~58MB, ~4.9MB, and a handful of smaller frames," one-time key loading, not a per-verification cost. The `finish_grow` figure is the same allocation, seen from one layer deeper in the call stack (the generic realloc routine `Parameters::read` calls into while growing its buffers to hold the ~50MB Sapling parameter file), not a separate or previously-unaccounted-for cost. **No new finding here -- confirms §7's conclusion via independent attribution, closes the "unidentified caller" open question from the previous per-block-allocation pass.**

### 8.4 "So many allocations and indexes -- all used in every scenario?"

Reviewed which of §7/§8's allocators are conditional on runtime flags vs. always active:

- **`CCoinsViewCache`'s coins/nullifier/anchor caches (`cacheCoins`, anchor maps, nullifier maps in `coins.h`) are unconditional** -- always instantiated, not gated by wallet, `-txindex`, `-prune`, or `-zindex`. This is correct, not bloat: UTXO/nullifier/anchor tracking is required by consensus validation itself for every node, including pruned ones (pruning discards old block *files* after validation, not the validation-time working set).
- **`fTxIndex` defaults to `true`** (`main.cpp:83`) -- the transaction index is on by default, unlike `-zindex`.
- **`fZindex` defaults to `false`** (`DEFAULT_SHIELDEDINDEX`, `main.h:115`) -- its *disk* and *population* costs are correctly opt-in, but per §8.2 its *in-memory struct layout* cost is not: every node pays ~176 bytes/block for fields most nodes never populate.
- **`AddToBlockIndex`'s core allocations (§8.1, items 1-3) are unconditional and unavoidable for any full validation** (reindex, normal sync, or otherwise) -- there is no flag that turns off block-index tracking; it's the mechanism the whole chainstate is built on.

Net: the allocation pattern isn't over-built for a hypothetical scenario -- most of it is genuinely load-bearing for every node. The one confirmed gap is §8.2's Shieldex struct-layout cost, paid unconditionally despite being conditionally *used*.

---

## 9. Equihash hashing: closed

Replaced at the call site by uniblake (`c9bbe6ad9`, 2026-09-02); measured 2.03x
on the Equihash access pattern. The mechanism is prefix-state reuse, not
vectorisation -- see `docs/HASHLIBS.md` for the division of labour between the
two libraries and `uniblake/docs/PATTERNS.md` for the pattern taxonomy.

The vectorisation track this section previously planned is closed on
measurement; the superseded plan is archived under `ZK/OLD/SAVE/`. Kernel-level
results belong to uniblake, not to this tree (`docs/HASHLIBS.md`).

