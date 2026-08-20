# Perf tasks and tracking

Every tracked perf item, its state, and what would move it. Findings live in
`Perf.md`; Groth16 in `PerfGroth.md`; numbers in `Measures.md`; how to run a
measurement in `BENCHMARKING.md`.

States: **Open** (ready to start) | **Blocked** (named blocker) | **Prototype**
(code exists, not integrated) | **Shipped** | **Set aside** (will not fix,
reason given).

---

## 1. Blocking decision

| ID | Item | Blocker |
|----|------|---------|
| **GROTH-DECIDE** | Sapling Groth16 batch verification: Option A hand-port vs Option B `sapling-crypto`, including the cxx-bridge scoping | Needs a person. Full pro/con and implementation path: `PerfGroth.md` |

Nothing downstream of this should start: the two options diverge at the FFI
boundary and would waste each other's work.

## 2. Open

| ID | Item | Gate |
|----|------|------|
| **IMP-BOOT-SEG** | Segmented bootstrap + reindex rematch + density CSV | Lab wall time |
| **IMP-GROTH-SPIKE** | Bound Option B migration cost (FFI/`cxx`, `ff`/`group`) | Feeds GROTH-DECIDE |
| **FIX-WAL-WITNESS-NOTEIDX-STALE** | Invalidate NOTEIDX only on note-membership change | Fat-wallet rescan is 97-99% `SelectWalletTxsForWitnessScan` above h1.6M; this is that cost |
| **IMP-BUILD-RECONFIG** | Autotools re-run inherits no `CONFIG_SITE` and dies on a misleading "libdb_cxx headers missing" | Pre-existing in both trees. Options: `BUILD_RECONFIG.md`. Fixes touch Zero400-owned `configure.ac` |
| **IMP-DB-REWRITE-SPIN** | `CDB::Rewrite` spins with no log, timeout or error when a caller holds the file | Upstream code, present in all Zcash-family forks. Cross-project comparison: `~/Work/ZK/ZKs/CDBRewrite.md` |

## 3. Prototype

| ID | Item | State |
|----|------|-------|
| **GROTH-BATCH-POC** | `contrib/perf/groth16-batch-poc/` -- batch math outside the FFI boundary, pinned crates | Passes. Next step gated on GROTH-DECIDE |

## 4. Shipped

| ID | Item |
|----|------|
| **FIX-LBI** | Inner `ShutdownRequested()` + `interruption_point()` in block-index load |
| **FIX-IMPORT-POLL** | `ThreadImport` honors shutdown at file boundaries |
| **FIX-TST09** | Tests for `-blocknotify` / `-walletnotify` |
| **FIX-WAL-WITNESS-IBD** | Skip/throttle `BuildWitnessCache` during IBD (`-walletwitness=ibd-defer`, opt-in) |
| **FIX-WAL-WITNESS-NOTEIDX** | Iterate note-bearing txs only (`-walletwitnessnote`, opt-in). 35x on the witness walk: 0.153 vs 5.31-5.72 ms/block |
| **ROOT-LATCH** | `IncrementalMerkleTree::root()` memoization, invalidated on append and deserialize |
| **ANCHOR-INDEX** | Anchor existence-check index |
| **FDCACHE** | Block-file read latch (`-perffdcache`, requires `--enable-perf`) |

## 5. Set aside -- will not fix

| ID | Item | Reason |
|----|------|--------|
| **FIX-WIT-WALK-UNLOCK** | Drop `cs_main` during the full height walk, abort/restart on tip move | No viable operating point. Abort-and-restart cannot converge once walk time exceeds the 120s block spacing; a full stock walk (~3.7h) gives E[attempts] ~10^48. Faster walks (NOTEIDX) make it unnecessary; slower ones make it impossible |
| **IMP-WITNESS-B2** | CleanIndex gtest harness | Always-fails; needs `pcoinsTip` anchors and disk-backed blocks the gtest harness does not provide. `qa/rpc-tests/reindex_shielded.py` covers the product gap |
| **FDCACHE 8/16KB A/B** | Buffer-size sweep | Prior 1MB A/B measured null. Profiling shows the run is serial-CPU-bound (one thread at 100%, disk syscalls under 5%), so an IO knob cannot help |
| **IMP-SHIELDEX-DEAD** | Remove dead `nNotarizations` | Opportunistic only, when `chain.h` is touched for another reason |
| **G8 Halo/Orchard** | -- | Not Zero consensus |
| **G7 NEON blake2b** | ARM blake2b intrinsics | blake2b is 18-21% pre-Sapling but 3-4% post-Sapling; does not compete with Groth16. Revisit only if an ARM fleet survey justifies it |

## 6. Coverage gaps

Not tasks, but they bound what can be concluded.

| Gap | Effect |
|-----|--------|
| No post-Sapling bootstrap, sync, or fat-wallet-reindex capture | Only reindex has both regions |
| No p1 rescan capture | Wallet-size curve has a hole between p1 (0.32%) and fat (72-99%) |
| Thermal never observed non-Nominal | Every capture is 60s; a multi-hour run has never been checked for throttling |
| `-debug=bench` unused by any campaign | Free per-block phase breakdown, never collected |
| No always-on timing | All instrumentation opt-in; a slow node in the field produces no evidence |

## 7. Where tracking lives

| Item | File |
|------|------|
| This list | `contrib/perf/PerfTasks.md` |
| Groth16 decision and plan | `contrib/perf/PerfGroth.md` |
| Findings and method | `contrib/perf/Perf.md` |
| Numbers, bound to `M-*` | `contrib/perf/Measures.md` |
| CPU shares per capture | `reindex-profile/bench-summaries/cpu_ledger.jsonl` |
| Throughput | `reindex-profile/bench-summaries/ledger.jsonl` |
| Provenance of recent numbers | `test-logs/DATA_INDEX.md` |
| Zero400-owned tasks | Zero400 `TODO.md` -- do not duplicate here |
