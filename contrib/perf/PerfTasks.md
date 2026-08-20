# Perf tasks and tracking

Every tracked perf item, its state, and what would move it. Findings live in
`Perf.md`; Groth16 in `PerfGroth.md`; numbers in `Measures.md`; how to run a
measurement in `BENCHMARKING.md`.

States: **Open** (ready to start) | **Blocked** (named blocker) | **Prototype**
(code exists, not integrated) | **Shipped** | **Set aside** (will not fix,
reason given).

---

## 1. Postponed pending developer review

| ID | Item | State |
|----|------|-------|
| **GROTH-DECIDE** | Sapling Groth16 batch verification: Option A hand-port vs Option B `sapling-crypto`, including the cxx-bridge scoping | **Postponed pending developer review.** Evidence and both options are written up and need no further work to be reviewable: `PerfGroth.md` |
| **IMP-GROTH-SPIKE** | Bound Option B migration cost (FFI/`cxx`, `ff`/`group`) | Postponed with the decision it feeds |
| **GROTH-BATCH-POC** | Batch math prototype, passes outside the FFI boundary | Frozen at prototype; do not extend |

**Do not start Groth16 implementation work.** The two options diverge at the
FFI boundary and would waste each other's work, and the choice is a
maintainer's call rather than a measurement: Option A reimplements four years
of upstream work in consensus-critical crypto, Option B is an L-XL migration
across the `ff`/`group` trait split. Reopen when a developer has reviewed
`PerfGroth.md` and picked a side.

What a reviewer needs is already recorded -- do not re-derive it:

- Why it matters: 88-91% of post-Sapling `zcash-loadblk` CPU (`PerfGroth.md` S1).
- The crux question: can batching land behind the existing C ABI? If yes,
  Option A avoids a release-scale migration entirely (`PerfGroth.md` S4 Q4).
- How to measure a change once one lands: `PerfGroth.md` S8, against the
  recorded S3 baselines (88.5% none, 91.5% p1).

Everything in sections 2 and 3 below is chosen to be **independent of this
decision**, so the postponement blocks nothing else.

## 2. Open

Grouped into **tracks** by subject. Within each track, **A** items come before
**B**, and **B** before **C** -- the label is sequencing, not priority. An item
labelled A in one track is independent of A in another, so tracks can run in
parallel.

Cross-track dependencies are named explicitly in the Gate column. Where an
earlier single item bundled several steps, it has been split so each row is one
reviewable change.

**Cross-track ordering that actually matters** (everything else is parallel):

1. **Track S A-items before Track P B-items.** `IMP-PERF-LINUX` produces the
   first non-macOS result; if the stores cannot express platform, that result
   either goes unrecorded or silently contaminates aggregates. Order is
   forced by data integrity, not by convenience.
2. **`IMP-BENCH-PROOF-TIMER` before `IMP-BENCH-ALWAYS`.** A summary without the
   proof counter omits 88-91% of post-Sapling cost while appearing complete.
3. **`FIX-BENCH-VERIFY-OVERLAP` with or before `AUT-BENCH-INGEST-EXISTING`.**
   Otherwise the double-count is frozen into stored data that outlives the
   reader who knew the caveat.
4. **Track M `BENCH-ZCB-ARCHIVE` is time-sensitive** in one direction only: it
   must precede any Groth16 change, so doing it during the postponement is
   strictly better than after.

Nothing in any track depends on **GROTH-DECIDE**.

### Track T -- timers and bench ingest

Spec: `PerfTimers.md`.

| Seq | ID | Item | Gate |
|-----|----|------|------|
| **A** | **AUT-BENCH-INGEST-EXISTING** | Parse the 10 unparsed `-debug=bench` phase lines. `extract_measures.py` has one regex (`- Connect block:`, the total); `zerod` emits 11 | None. Parser-only, works on logs already on disk. `PerfTimers.md` S4 item 1 |
| **A** | **FIX-BENCH-VERIFY-OVERLAP** | `nTimeConnect` and `nTimeVerify` both measure from `nTimeStart`, so verify **includes** connect; summing double-counts and labels do not say so | Must land with or before the parser, or the hazard is frozen into stored data. `PerfTimers.md` S2.2 |
| **B** | **IMP-BENCH-PROOF-TIMER** | Add proof-verification counters. Sprout runs in `CheckBlock` (`main.cpp:2982`) before `nTimeStart` (`3049`); Sapling in `ContextualCheckBlock` during acceptance, outside `ConnectTip`. 88-91% of post-Sapling cost is untimed | Product change (Zero400). Validate post-Sapling, not on tiny. `PerfTimers.md` S2.1, S3.2 |
| **C** | **IMP-BENCH-ALWAYS** | Emit periodic `BenchSummary` (interval + cumulative) at default log level | Product change (Zero400). **Requires IMP-BENCH-PROOF-TIMER** -- without it the summary omits the largest cost while looking complete. `PerfTimers.md` S3.3 |
| **C** | **AUT-BENCH-INGEST-SUMMARY** | Parse `BenchSummary` into Measures tokens, aggregated per height band | Depends on IMP-BENCH-ALWAYS. `PerfTimers.md` S4 item 2 |

### Track S -- stores, versioning, multi-platform aggregation

Spec: `PerfStores.md`. **Track S A-items gate Track P B-items**: a non-macOS
run must not be recorded before the stores can express platform.

| Seq | ID | Item | Gate |
|-----|----|------|------|
| **A** | **STORE-BACKANNOTATE** | Stamp the 49 existing rows with `schema:1` + the known `platform` block (all macOS/arm64/native) | Cheapest now, while "all macOS" is true by inspection. Write a new file, keep the original. `PerfStores.md` S5 step 1 |
| **A** | **STORE-SCHEMA-V2** | Add `platform` / `build` / `features` blocks to both ledgers. Neither store has any OS, arch, version or feature field today | Additive only; absent means unknown. `PerfStores.md` S3.1-S3.4 |
| **B** | **STORE-STAMP-HELPER** | One shared `platform_stamp.py` emitting the block; call it from every launcher so producers cannot drift | Depends on STORE-SCHEMA-V2. Dominates the effort. `PerfStores.md` S5 step 2 |
| **B** | **STORE-FINGERPRINT-V2** | Extend the dedup key with platform/build/features and store `fingerprint_v`. Today two rows differing only by platform can collide and be silently dropped | Must not recompute v1 keys, or 49 rows re-import as duplicates. `PerfStores.md` S3.6 |
| **B** | **STORE-BUILD-IDENTITY** | Replace `binary` (a host path, 2 distinct values in 35 rows) with version/commit/dirty from `zerod --version` | The string already exists: `v4.0.1-a2ae9583c-dirty`. Current numbers came from a **dirty** build. `PerfStores.md` S2.2 |
| **C** | **STORE-JOIN-RUNID** | Add `run_id` to CPU rows so the two ledgers can be joined | `profile_run.sh` already knows it. `PerfStores.md` S3.5 |
| **C** | **AUT-AGG-GUARD** | Make collators flag or refuse aggregation spanning differing `platform.arch` / `build.commit` | Turns the comparability convention into an enforced check. `PerfStores.md` S4 |
| **C** | **AUT-LEDGER-PROVENANCE** | Flag back-imported rows mechanically (12 share one `recorded_at`) instead of by reader convention | Fits naturally with fingerprint work. `PerfNext.md` S3.4 |

### Track P -- platforms

Survey: `PerfPlatforms.md`.

| Seq | ID | Item | Gate |
|-----|----|------|------|
| **A** | **DOC-PLATFORM-CAVEAT** | State that every published CPU number is macOS/arm64 and no profile has run elsewhere | One sentence per document. GROTH-DECIDE rests on these numbers. `PerfPlatforms.md` S1 |
| **A** | **AUT-PARSE-CONTRACT** | Document the `parse()` input contract in `bucket_profile2.py`; only lines 119-158 are xctrace-specific | Do before a second parser exists. `PerfPlatforms.md` S2 |
| **B** | **IMP-PERF-LINUX** | Linux `perf record` + folded-stack `parse()`, reusing `classify()` / `BUCKETS` unchanged | **Requires Track S A-items** so the result is recordable. `PerfPlatforms.md` S3.1 |
| **B** | **IMP-RES-SAMPLE-PORT** | Port `res_sample.sh` to `psutil`, replacing `footprint` / `vm_stat` / `ps -M` / `iostat` | Collapses the most platform-specific shell code. `PerfPlatforms.md` S5.2 |
| **C** | **BENCH-WSL2-SPOT** | WSL2 spot check | Depends on IMP-PERF-LINUX. Disk numbers characterise WSL2, not Windows. `PerfPlatforms.md` S4.2 |
| **C** | **IMP-PERF-WINDOWS** | Native Windows ETW profiling | **Not recommended yet** -- blocked on MinGW/DWARF vs PDB symbols and an MXE build path never executed in this program. `PerfPlatforms.md` S4.1 |

### Track M -- measurement gaps

| Seq | ID | Item | Gate |
|-----|----|------|------|
| **A** | **BENCH-ZCB-ARCHIVE** | Record the `M-ZCB-SUITE` baseline -- 19 microbenchmarks runnable but unrecorded, including `verifysaplingspend` / `verifysaplingoutput` | Cheap, no decision needed, and **more valuable the longer GROTH-DECIDE stays open**: a batching result needs a per-proof baseline taken beforehand. `PerfNext.md` S3.5 |
| **B** | **BENCH-THERMAL-LONG** | Sample thermal during a long run already planned; every capture so far is 60s, so "Nominal" is near-tautological | Attach to a scheduled run, do not schedule one. `PerfNext.md` S2.2 |
| **B** | **BENCH-P1-RESCAN** | Fill the p1-to-fat hole in the wallet-size curve | First confirm by timing that p1 rescan is long enough to profile; a p0 rescan takes 2 ms. `PerfNext.md` S2.3 |
| **C** | **IMP-BOOT-SEG** | Segmented bootstrap + reindex rematch + density CSV | Lab wall time |

### Track F -- product fixes

| Seq | ID | Item | Gate |
|-----|----|------|------|
| **A** | **FIX-WAL-WITNESS-NOTEIDX-STALE** | Invalidate NOTEIDX only on note-membership change. `AddToWallet` (`wallet.cpp:2152`) invalidates unconditionally, including transparent-only txs that can never enter `vNoteTxHashes` | Defect localised to 2 call sites. Fat-wallet rescan is 97-99% `SelectWalletTxsForWitnessScan` above h1.6M |
| **B** | **IMP-BUILD-RECONFIG** | Autotools re-run inherits no `CONFIG_SITE` and dies on a misleading "libdb_cxx headers missing" | Touches Zero400-owned `configure.ac`. Options: `BUILD_RECONFIG.md` |
| **B** | **IMP-DB-REWRITE-SPIN** | `CDB::Rewrite` spins with no log, timeout or error when a caller holds the file | Upstream, present in all Zcash-family forks. `~/Work/ZK/ZKs/CDBRewrite.md` |

### Track D -- documentation and enforcement

Review: `PerfDocReview.md`.

| Seq | ID | Item | Gate |
|-----|----|------|------|
| **A** | **AUT-LINT-DOCS** | Run `check-unicode.py --fix` (693 violations, 498 in `Perf.md`) and add `unicode-docs` to the default `CHECKS` | `--fix` verified safe: 13 in-fence lines, none executable. The gate is the durable half. `PerfNext.md` S3.2 |
| **A** | **AUT-CI-PERF-BRANCH** | CI push trigger is `[main, master, develop]`; the active branch is `perf-402`, so direct pushes run no CI. No lint step in CI at all | Add the branch, and a lint job ahead of the 240-minute build. `PerfNext.md` S3.3 |
| **B** | **AUT-LINT-CITATIONS** | Enforce "numbers live in `Measures.md` under an `M-*` id". The Groth16 share is restated in 5 documents, NOTEIDX 35x in 5 | Extend `lint-perf.sh`. Best after AUT-LINT-DOCS establishes the doc-gate pattern. `PerfDocReview.md` S3.1 |
| **B** | **DOC-RELOCATE-OFFSUBJECT** | 5 documents (1201 lines, 19%) in `contrib/perf/` are not about node perf: 2 are Qt wallet UI, out of scope per `AGENTS.md` | **Needs user confirmation** -- no file moved or deleted without it. Dispositions D1-D5: `PerfDocReview.md` S4 |
| **C** | **DOC-STATUS-SPLIT** | Extract the volatile status layer out of `Perf.md` (72% of it is one section) | The only restructuring safe during the Groth16 postponement; reduces the eventual restructure cost. `PerfNext.md` S4.2 |
| **C** | **DOC-PERFDOC-PRUNE** | Prune `PerfDoc.md` S6-S10, which duplicate `BENCHMARKING.md` Part 4 by its own admission | Blocked on repointing inbound section-number links. `PerfDocReview.md` S2.1 |

## 3. Prototype

| ID | Item | State |
|----|------|-------|
| **GROTH-BATCH-POC** | `contrib/perf/groth16-batch-poc/` -- batch math outside the FFI boundary, pinned crates | Passes. **Frozen** -- next step postponed with GROTH-DECIDE (S1) |

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

Not tasks, but they bound what can be concluded. Ranked by value, with the
one that is **not** worth filling called out: `PerfNext.md` S2.

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
| Next directions (measurement / automation / docs) | `contrib/perf/PerfNext.md` |
| Phase-timer design and spec | `contrib/perf/PerfTimers.md` |
| Cross-platform tooling survey | `contrib/perf/PerfPlatforms.md` |
| Measurement-store schema (platform / version / features) | `contrib/perf/PerfStores.md` |
| Per-document goals, audience and critique | `contrib/perf/PerfDocReview.md` |
| Groth16 decision and plan | `contrib/perf/PerfGroth.md` |
| Findings and method | `contrib/perf/Perf.md` |
| Numbers, bound to `M-*` | `contrib/perf/Measures.md` |
| CPU shares per capture | `reindex-profile/bench-summaries/cpu_ledger.jsonl` |
| Throughput | `reindex-profile/bench-summaries/ledger.jsonl` |
| Provenance of recent numbers | `test-logs/DATA_INDEX.md` |
| Zero400-owned tasks | Zero400 `TODO.md` -- do not duplicate here |
