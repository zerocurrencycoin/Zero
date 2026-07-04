# `zerod` sync performance: current understanding, and next steps

## 0. Next tasks

§0's re-profiling run (below) is **done** — see §2a for the corrected result, which supersedes §2's original 58/25/17 breakdown. Current priorities are §5's re-ordered list: item 2 (Sprout root-existence index) is still the best-justified lever for the *tree/anchor* slice, but §2a shows Sapling Groth16 proof verification is the actual dominant cost post-Sapling-activation, and nothing has been scoped against that yet — see §2a's "Not yet investigated" note.

Re-profiling procedure used (kept here for the next time this needs re-running, e.g. after a further code change or `-O2` build — see §6 for how to do this kind of investigation quickly):

1. Fresh scratch datadir (chainstate excluded; `-reindex` rebuilds it):

   ```bash
   cd /Users/walter/Work/ZK/ZeroPerf
   rm -rf reindex-profile/datadir
   rsync -a --exclude='chainstate' "/Users/walter/Library/Application Support/Zero/" reindex-profile/datadir/
   ```

2. Record system state alongside the profile, so the run can be judged against actual conditions rather than assumed idle hardware:

   ```bash
   sysctl -n hw.ncpu hw.physicalcpu hw.memsize
   pmset -g therm
   uptime
   ```

3. Launch `-reindex`, poll `getblockcount` via `zero-cli` until height has advanced (don't guess from wall-clock or log-tailing — RPC gives an exact, race-free signal), then attach Time Profiler for a 60-second window:

   ```bash
   ./src/zerod -datadir="$PWD/reindex-profile/datadir" -reindex -connect=0 -listen=0 -rpcport=23920 &
   PID=$!
   until h=$(./src/zero-cli -datadir="$PWD/reindex-profile/datadir" -rpcport=23920 getblockcount 2>/dev/null) \
         && [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -gt 3000 ]; do sleep 3; done
   xcrun xctrace record --template 'Time Profiler' --output reindex-profile/timeprofile.trace --time-limit 60s --attach "$PID"
   ```

4. Stop the scratch process (`SIGTERM`) once the recording completes:

   ```bash
   kill -TERM "$PID"
   ```

5. Export and bucket the trace (see §6 for the reusable tool):

   ```bash
   xcrun xctrace export --input reindex-profile/timeprofile.trace \
     --xpath '/trace-toc/run[1]/data[1]/table[@schema="time-profile"]' \
     --output reindex-profile/timeprofile_agg.xml
   python3 reindex-profile/tools/bucket_profile.py reindex-profile/timeprofile_agg.xml
   ```

6. **Determine the exact block-height range the 60s window actually covered**, from the trace's own `<start-date>` (in the export's `--toc` output) cross-referenced against `debug.log`'s `UpdateTip` timestamps — not from the datadir's *final* height, which is a trap (see §6, "getting the height window right"). This matters because block/tx mix varies enormously by height (§2a), so a bucket breakdown is only interpretable together with the height range it was measured on.

---

## 1. Scope and terms

**Subject:** where `zerod` spends CPU during `-reindex` (rebuild `chainstate` from local `blocks/*.dat`) and `bootstrap.dat` import (bulk-load a pre-staged flat file of blocks) — the two faster-than-network ways to catch a node up. Both were assumed "fast" but never measured; this investigation measured them, found the dominant cost, and implemented a first optimization for it.

**Working tree:** `ZeroPerf` (`/Users/walter/Work/ZK/ZeroPerf`, branch `perf-401`), built at `-O1` (`-pipe -O1 -g -fwrapv -fno-strict-aliasing`, the repo default). Binary is self-contained (verified via `otool -L`: only system libraries are dynamically linked; all third-party dependencies are static).

**Terms:**
- **Bucket:** one of a small number of mutually-exclusive CPU-time categories a profiling sample falls into. Bucketing matches on *any* frame in a sample's call stack, not just the leaf, so (e.g.) a sample inside `blake2b_compress_ref` called from `CheckEquihashSolution` counts as Equihash, not "blake2b" in isolation. §2's original bucket set (Sapling/Sprout tree update, Equihash, disk I/O) turned out to conflate two distinct costs under "Sapling/Sprout tree update" — see §2a.
- **Latch:** a single-slot memoization — one stored value (or empty), cleared by the one or two operations that change the underlying state, repopulated on next read. Not a cache: no key, no multiple entries, no capacity, no eviction policy, because there is only ever one live value to remember per object. §4 justifies this design directly against Zebra's comparable code.
- **Match / no-match:** a `root()` call that finds the latch already populated (match) returns it without recomputing; a call that finds it empty (no-match) recomputes and stores the result.
- **Activation height:** the mainnet block height at or after which a network upgrade's rules apply.

---

## 2. Measured CPU cost

The numbers below establish where CPU time actually goes. The method matters as much as the result, so it's described first: a real mainnet datadir (not synthetic/regtest — script/tx mix affects where time goes) was profiled with Instruments Time Profiler (`xcrun xctrace`, headless CLI) attached to the single worker thread that does the actual reindex/import work (`zcash-loadblk`, running `ThreadImport`). Every other thread (12 idle script-check-queue workers, RPC/net/wallet threads) is filtered out — an unfiltered, all-threads profile is dominated by idle-thread noise (85%+ of raw samples are threads blocked on a condvar) and says nothing about where real work goes. Samples carry real on-CPU nanosecond weight (Instruments' weighted sampling, not naive tick-counting) and a full call stack; every stack frame in every captured sample resolved to a real function name with **0% unaccounted/missing backtraces** in every run — full accounting, not a partial sample.

**Result — CPU breakdown, mutually exclusive buckets summing to ~100%, consistent across every run (`-reindex` on two different builds, `bootstrap.dat` import, at chain heights from ~10K to ~2M):**

*Superseded by §2a: this table's "Sapling/Sprout tree update" bucket is now known to conflate two distinct costs (Groth16 proof verification and tree/anchor recomputation) — see §2a for the corrected split and why. Kept here for history/comparison, not as current guidance.*

| Bucket | Typical range measured | Call path (leaf → root) |
|---|---|---|
| Sapling/Sprout tree update | 57–58% | `Fr::mul_assign`/`Fr::inverse` (BLS12-381 field arith) ← `jubjub::edwards::Point::add` ← `librustzcash_merkle_hash` ← `IncrementalMerkleTree::root()` ← `CCoinsViewCache::AbstractPushAnchor<...>` ← `ConnectBlock` |
| Equihash PoW verification | 24–27% | `blake2b_compress_ref` ← `blake2b_final` ← `Equihash<192,7>::IsValidSolution` ← `CheckEquihashSolution` ← `CheckBlockHeader` ← `ProcessNewBlock` |
| Disk I/O | 15–18% | `OpenDiskFile`/`ReadBlockFromDisk`/`UndoWriteToDisk` (`fopen`/`open` syscalls) ← `LoadExternalBlockFile`/`ConnectBlock` |

**This breakdown is identical for `-reindex` and `bootstrap.dat` import**, because both call the same `ConnectBlock`/`CheckEquihashSolution`/`AbstractPushAnchor` validation per block — `bootstrap.dat` only changes how block bytes arrive (pre-staged file vs. `blocks/*.dat` scan vs. network download), not what validation work happens once a block is in hand. Measured `bootstrap.dat` import wall-clock: **145.7 minutes** (8,743,120 ms, self-reported by `zerod`) for 2,468,990 blocks. **Practical conclusion: `bootstrap.dat`'s entire benefit is skipping network download time; it cannot reduce the CPU-bound validation cost**, which is the same regardless of how blocks arrive. (This conclusion is unaffected by §2a's correction — it's about which bucket dominates, not whether import mode changes total validation work.)

**Throughput, from the same `bootstrap.dat` run:** 2,468,990 blocks / 8,743.12s ≈ **282 blocks/sec** average across the *entire* chain history. §2a gives a directly-measured blocks/sec and an estimated bytes/sec for one specific 60-second/16,048-block window, which lands close to this whole-chain average — see §2a.

**Interpretation of each bucket:**
1. **Sapling/Sprout tree update (the largest bucket) is consensus-mandated** — every block that appends to either shielded pool's Merkle tree must produce a correct anchor. The lever is making the *recomputation* cheaper, not skipping it. §3–§4 cover what was investigated and implemented here. *(§2a: this bucket's dominant contents turned out to be Groth16 proof verification, not tree/anchor recomputation, at the height actually re-measured — see §2a before treating this interpretation as still accurate.)*
2. **Equihash verification is not a realistic optimization target** — inherent header validation; skipping or weakening it compromises consensus safety.
3. **Disk I/O** is a real, non-trivial cost, currently inferred from stack frames (`OpenDiskFile` appearing repeatedly suggests block/undo files are being `fopen`'d rather than kept open across reads) rather than measured directly — see §4a for the confirmed mechanism and §5's open item for direct measurement.
4. **The idle script-check-queue threads (`zcash-scriptch`, `-par`) cannot help any of this.** They are wired only to per-transaction signature verification, never to anchor/tree updates, in every codebase checked (Bitcoin Core, zcashd, Zero, Zebra — cross-repo research, `ZKs/Comparison.md` §8.3). This is a per-call cost problem in code that has never been parallelized, not a parallelism gap in otherwise-idle threads.

**Memory profiling: attach works, readout doesn't, headlessly.** Instruments' Allocations/Leaks templates need `task_for_pid` attach (`get-task-allow` entitlement + Developer Mode, both now satisfied) — attach succeeds, but the recorded per-allocation event data is stored in a proprietary binary blob readable only by the Instruments GUI; `xcrun xctrace export` has no schema for it in this Instruments version, unlike Time Profiler's exportable `time-profile` table. No byte/percentage memory breakdown has been obtained. `vmmap`/`heap`/`malloc_history` are all present on this machine (confirmed via `which`) and are CLI-native with no export-format dependency — the clear next step, not yet tried; a GUI session reading the existing `.trace` recordings directly also remains an option.

**dtrace remains postponed**, not because it's blocked, but because unrestricted use requires a SIP configuration change from Recovery OS (`csrutil enable --without dtrace`) — a machine-wide, invasive step not worth taking before confirming Instruments' System Trace/File Activity templates (kernel-tracepoint-based, no SIP change needed) leave a real gap for the disk-I/O question.

---

## 2a. Corrected measurement on the clean `perf-401` binary (§0's re-profiling run)

**What changed and why this section exists:** §2's original bucket definitions matched `jubjub`/`edwards::Point` substrings anywhere in a sample's call stack to mean "Sapling/Sprout tree update." But Sapling's Groth16 zk-SNARK proof verification (`librustzcash_sapling_check_spend`/`_check_output`, called from `ContextualCheckTransaction` in `main.cpp:1119`/`1137`) *also* does elliptic-curve arithmetic over the same `jubjub`/BLS12-381 types, deep inside `bellman::groth16::verifier::verify_proof`. §2's matching couldn't tell these apart, so all of it landed in one bucket. Re-running §0's profiling with a bucket set that checks for `bellman::groth16::verifier::verify_proof`/`miller_loop`/`final_exponentiation` specifically (see §6's tool) splits it correctly.

**Run details:** current clean `perf-401` binary (§5 item 7's stripped build), scratch datadir reindexing from a pre-staged mainnet chain, 60-second Time Profiler window. The window's actual block-height range was determined from the trace's `<start-date>` cross-referenced against `debug.log` (see §0 step 6 and §6's pitfall note) — **height 610,758 → 626,806**, i.e. May–July 2019, well after Sapling's mainnet activation (height 492,850, `chainparams.cpp:117`) but not a period of unusually heavy shielded activity by any special selection; this was simply where the reindex happened to be after ~19 minutes of runtime.

| Bucket | % of `zcash-loadblk` CPU | Call path |
|---|---|---|
| **Sapling Groth16 proof verification** | **60.9%** | `Fq::mul_assign`/`Fq12::square`/etc. (BLS12-381 pairing arith) ← `miller_loop` ← `bellman::groth16::verifier::verify_proof` ← `librustzcash_sapling_check_spend`/`_check_output` ← `ContextualCheckTransaction` |
| Disk I/O | 26.2% | Same syscalls as §2, larger share than §2's 15–18% at this height (more/bigger blocks per file-open at this point in the chain — not yet root-caused further) |
| Equihash PoW verification | 6.9% | Same call path as §2 |
| Sapling/Sprout tree/anchor update | 6.1% | Same call path as §2 — **this is what §2's "57–58%" figure actually measured almost none of, at this height**; §3/§4's latch work targeted this specific, much smaller slice |

**Cross-check against the un-migrated `bootstrap-import-profile` trace** (full 0–2.47M height range, captured on an earlier build, re-bucketed with the same corrected script): **0 Groth16 samples**, and the split reproduces §2's original 58.1/25.8/16.1 almost exactly. This confirms two things at once: (a) the corrected bucketing script is not the source of the discrepancy — it reproduces the old numbers exactly when Groth16 genuinely isn't present in a trace — and (b) §2's 58% figure was measured on a height range with negligible Sapling shielded-transaction volume (most likely still Sprout-dominated or pre/early-Sapling), so it was never wrong about *that window*, but it was wrong as a general claim about "the" Sapling/Sprout bucket, because the actual dominant cost (Groth16) barely existed in the window it was measured on.

**Practical conclusion — the bucket breakdown is height-dependent, not a fixed constant, and the previously "confirmed" 58% figure specifically undercounted Sapling Groth16 verification.** Any future profiling result must be reported together with its block-height range (§0 step 6) to be interpretable; a single "the breakdown is X/Y/Z" claim without a height range is not reproducible and should not be trusted at face value, including ones already in this document predating this section.

**Throughput for this specific window** (height 610,758 → 626,806, exactly 60s, computed from `debug.log`'s `UpdateTip` timestamps — exact, not estimated):
- **267.5 blocks/sec** (16,048 blocks / 60s).
- **~330 KB/sec estimated** (not exact — sampled block `size` at 41 evenly-strided heights via `getblock` RPC, averaged 1,266 bytes/block, multiplied by 16,048 blocks; individual block sizes in this range varied from 685 to 160,858 bytes, so this average carries real sampling uncertainty. An exact figure would require summing `getblock().size` over all 16,048 blocks in range, not done here).
- Consistent with §2's whole-chain `bootstrap.dat` average of ~282 blocks/sec — blocks/sec is fairly stable across most of the chain even though *where the CPU time within each block goes* varies a lot by height.

**Not yet investigated:** nothing in §3/§4/§5 was ever scoped against Groth16 proof verification cost specifically, because it wasn't known to be separately identifiable until this section. §3's latch and §5 item 2's proposed root-existence index both target the tree/anchor bucket only (6.1% of CPU at this height) — neither would touch the 60.9% Groth16 bucket. Whether Groth16 verification itself has any legitimate optimization headroom (e.g., batch verification of multiple proofs at once, which some zk-SNARK libraries support and `bellman` may or may not) has not been researched. This is the natural next investigation given these numbers, ahead of §5's existing item 2, but is not yet scoped — flagging here rather than silently reprioritizing §5's list without doing that scoping work.

---

## 3. The latch fix

This section covers what the latch does, what it measurably fixed, and what it structurally cannot fix. **The confirmed inefficiency:** `IncrementalMerkleTree::root()` (`src/zcash/IncrementalMerkleTree.cpp`) recomputes fully from `left`/`right`/`parents` on every call — a real `Hash::combine()` → `librustzcash_merkle_hash` FFI call for every populated tree level. `ConnectBlock` (`src/main.cpp`) calls `sapling_tree.root()`/`sprout_tree.root()` **twice per block, unconditionally**: once inside `PushAnchor`→`AbstractPushAnchor` (`src/coins.cpp:204`), once directly (`main.cpp:3173`/`3180`) — computing the identical value both times whenever nothing mutated the tree in between.

**Fix:** a `mutable boost::optional<Hash> cached_root` latch on `IncrementalMerkleTree`, populated on first `root()` call, cleared in the only two places that mutate tree state (`append()`, post-deserialize). Pure memoization of a deterministic function of existing state — no change to what's hashed, so no consensus or serialization-format risk.

**Why it helps `ConnectBlock` but not `HaveShieldedRequirements` — value vs. reference:**
- `AbstractPushAnchor(const Tree &tree, ...)` (`coins.h:574-575`) takes `tree` **by const reference**. `ConnectBlock`'s two calls (via `PushAnchor` and directly) therefore operate on the *same* `sapling_tree`/`sprout_tree` object — the first call populates the latch, the second matches it.
- `CCoinsViewCache::HaveShieldedRequirements` (`coins.cpp:570-599`), which validates each Sprout joinsplit's anchor during transaction input validation, declares `SproutMerkleTree tree;` **by value, freshly, inside the per-joinsplit loop** — a brand-new object every iteration, mutated once (`append()`) and read once (`root()`) before going out of scope. **There is structurally no second read on the same object for the latch to ever serve** — every call here is a guaranteed no-match, not a possible one, regardless of how the latch is implemented.

**Validation:** existing gtest suite passes unmodified (known-answer vectors, interleaved append/root checks, deserialize-invalid cases); a new test (`merkletree.RootCacheConsistency`) directly exercises match/no-match behavior across append and serialize/deserialize round-trips; full regression (Boost `test_bitcoin` 284/284, `zero-gtest` 206/206) confirmed clean, with pre-existing unrelated test flakiness (an unconnected wallet-key test, ~1-in-9 runs, present on the unmodified baseline too) ruled out as a false attribution to this change.

**Measured impact: correct, but flat.** Re-profiled with the same methodology: Sapling-tree bucket **57.9%** vs. the pre-fix **58.0%** baseline — no measurable change, despite the latch being demonstrably active. Direct instrumentation (a call/no-match counter plus per-block ground-truth Sprout-note-commitment/Sapling-output counts, gathered from real `-reindex` runs against Zero's own mainnet chain data — not inferred, not borrowed from Zcash usage statistics) explains why:

*Caution: gathered with the per-block counters that have since been removed from the source (§5 item 7) — a one-time finding, not something that can be re-derived from the current binary without re-adding equivalent instrumentation.*

| Block category (n) | avg `root()` calls/block | match rate |
|---|---|---|
| Idle (no shielded activity) | 5.00 | **100%** |
| Sapling outputs only | 5.00 | 80% |
| Sprout joinsplits only | 8.28 | 48.3% |
| Both | 8.22 | 36.4% |

Idle and Sapling-output-only blocks match perfectly — but they were already cheap (empty/near-empty tree, no real `combine()` work), so a perfect match rate there saves negligible CPU. **Sprout joinsplits drive both the extra call volume and the low match rate**, because each joinsplit's anchor is checked via `HaveShieldedRequirements`'s fresh-object pattern above — structurally unmatchable. Sapling spends (`tx.vShieldedSpend`, `coins.cpp:601-609`) never call `.append()`/`.root()` at all in that function, so they were never a candidate for this latch either way.

**Conclusion: the latch is correct and removes a real, confirmed redundancy, but that redundancy was a small, cheap-skewed slice of the 58% bucket.** The bucket's real cost is (a) genuinely new `append()`/`combine()` work proportional to shielded-output volume — unavoidable, it's hashing new data — and (b) Sprout-joinsplit anchor validation's fresh-object-per-joinsplit pattern, which no per-object latch can help, by construction, no matter how it's implemented.

---

## 4. Latch vs. cache

Compared directly against Zebra's actual code, to answer a natural question: why build a single-slot latch instead of a proper multi-entry cache (e.g., keyed by tree root, shared across joinsplits/blocks) that *could* help `HaveShieldedRequirements`? Zebra (the Rust reimplementation) was checked directly, by reading its source, to answer this rather than assume.

**Zebra's own tree type uses the same single-slot latch** (`zebra-chain/src/sprout/tree.rs:251-308`: `cached_root: RwLock<Option<Root>>`, cleared on `append()`, populated on `root()`) — confirming a keyed cache isn't the standard answer to *this* part of the problem either. The real difference is elsewhere:

- **Zebra's Sapling/Orchard anchor validation never constructs a tree object during validation at all.** `sapling_orchard_anchors_refer_to_final_treestates()` (`zebra-state/src/service/check/anchors.rs:24-119`) checks anchor membership against a `HashSet` (in-memory, non-finalized chain) or a RocksDB key-existence check (`contains_sapling_anchor` → `zs_contains`, `shielded.rs:108-111`) — populated once, at commit time, keyed by root with an empty `()` value (`shielded.rs:645`). This is not a bigger/better cache of the same kind — it's a **different technique**: a yes/no membership index over previously-seen roots, replacing tree reconstruction entirely rather than memoizing it.
- **Zebra's Sprout anchor validation is split.** The common case — a joinsplit anchored to a prior block's already-finalized tree — is equally cheap: a stored, pre-built tree fetched whole via `Arc` (`fetch_sprout_final_treestates`, `anchors.rs:132-176`; `zs_insert(&sprout_anchors, tree.root(), tree)` at commit, `shielded.rs:603`). But **chained joinsplits within one transaction** (joinsplit N's anchor = joinsplit N−1's own output tree) still pay the same construct/append/read cost Zero pays (`sprout_anchors_refer_to_treestates`, `anchors.rs:186-282`, lines 248-272: `Arc::make_mut` clone, `append()`, `root()`) — and Zebra's own source says so: *"This check is expensive, because it updates a note commitment tree for each sprout JoinSplit"* (`anchors.rs:452`).

**So the justification for the latch as built is precise, not just "it's what we had time for":** a keyed/multi-entry cache would not have helped `HaveShieldedRequirements` either, because the actual problem there isn't *insufficient memoization* — Zebra hits the identical wall for the same case (chained Sprout joinsplits) despite having a mature, independently-developed implementation. The technique that *does* sidestep the problem, in Zebra's Sapling/Orchard path, is structurally different: a membership index over known-good roots, not a cache of computed values keyed more cleverly. That's the concrete lead for further work (§5), not "make the latch bigger."

---

## 4a. Why disk I/O is open-read-close per block, in detail

§2/§2a's disk-I/O bucket was inferred from stack frames (`OpenDiskFile` recurring) rather than root-caused in the source until now. Reading `src/main.cpp` directly confirms the mechanism precisely, not just "it looks like fopen is called a lot":

- `OpenBlockFile`/`OpenUndoFile` (`main.cpp:4872-4877`) both call `OpenDiskFile` (`main.cpp:4849`), which does a **fresh, unconditional `fopen()` on every call** — there is no persistent or cached `FILE*` kept across calls anywhere in this path.
- Every call site (`ReadBlockFromDisk` at `main.cpp:2074`/`2099`, `WriteBlockToDisk` at `main.cpp:2056`, `UndoWriteToDisk` at `main.cpp:2523`, the undo-read counterpart at `main.cpp:2553`) wraps the fresh `FILE*` in a stack-local `CAutoFile` (`src/streams.h:398-427`). `CAutoFile`'s destructor (`streams.h:416-419`) calls `fclose()` unconditionally the moment that function returns — there is no way for the handle to outlive a single read or write.
- `ConnectBlock`/`LoadExternalBlockFile` call these once or twice per block (a read, and usually an undo-data write). A full reindex of ~2.5M blocks therefore performs on the order of **2.5–5 million `fopen`/`fclose` pairs**, even though the underlying `blkNNNNN.dat`/`revNNNNN.dat` files are ~128 MB each and each holds thousands of consecutive blocks — so the overwhelming majority of those open/close pairs are reopening a file that was just closed moments earlier for the *previous* block.

**Why this actually costs something** (not just "syscalls are slow" as a vague claim): each `fopen`/`fclose` pair is a full kernel `open`/`close` round-trip, and `fopen` additionally re-initializes stdio's internal buffer (`_bf`) from scratch every time, discarding whatever the previous call had just populated for the same file. The cost is being paid **once per block instead of once per file** — roughly a 100–1000x amplification versus the number of times a "file" conceptually needs opening, depending on how many blocks share one `blkNNNNN.dat`.

**The fix** (§5 item 4, still contingent on §5 item 3's direct measurement): keep a small map of already-open `FILE*` handles keyed by file index, opened once per `blkNNNNN.dat`/`revNNNNN.dat` and reused across all blocks that live in it, closed only when moving to the next file index (or at import completion). Bitcoin-derived codebases already do a version of this for the *write* path (`nLastBlockFile` tracking exists to avoid reopening for appends), but the *read* path (`ReadBlockFromDisk`) has no equivalent here — confirming precisely how much of the 26.2%/15-18% I/O bucket is read-side vs. write-side is exactly what §5 item 3's direct measurement would settle before implementing item 4.

---

## 5. Future directions

In priority order:

1. Done (§2a): re-ran §2/§3's measurements on the current, clean binary. **Result was not a reproduction** — it uncovered that §2's bucket definitions had conflated Sapling Groth16 proof verification with tree/anchor recomputation, and the actual dominant cost (60.9% at the measured height) is Groth16 verification, not tree/anchor work. See §2a in full before trusting any older percentage in this document.
2. **Scope whether Sapling Groth16 proof verification has any legitimate optimization headroom** (new, promoted to top priority given §2a — this is now the largest bucket by a wide margin, and nothing has investigated it yet). Candidate directions to research, not yet started: whether `bellman` (the Rust Groth16 implementation Zero's `librustzcash` links) supports batch verification of multiple proofs at once, which some pairing-based SNARK libraries do at meaningfully lower amortized cost than one-proof-at-a-time; whether any of this work is parallelizable across the otherwise-idle `zcash-scriptch` threads despite §2 item 4's finding that they're currently wired only to signature verification (a structural, not fundamental, limitation — worth confirming whether it could be changed, separately from whether it's worth changing). This needs real research into `bellman`'s API and Zcash's own history with this question before any implementation attempt.
3. **Root-existence-index for Sprout anchor validation in `HaveShieldedRequirements`** (the concrete lead from §4). Zero's `HaveShieldedRequirements` currently always constructs a fresh tree via `GetSproutAnchorAt` to validate a joinsplit's anchor, even for the common independently-anchored case where Zebra's Sapling/Orchard path only checks root membership. Adopting the same idea for Zero's Sprout path — confirm the anchor is a known-valid historical root via a membership check, rather than reconstructing and re-deriving tree state — is a materially larger change than the latch (§3), changing *what gets validated and how*, not just adding memoization. Not started. Chained-joinsplit transactions (where even Zebra pays the reconstruction cost) would remain unimproved by this change and are believed to be a small fraction of total joinsplits, though this has not been measured on Zero's chain and should be confirmed before or alongside implementation. **Re-ranked below item 2** given §2a: this only ever targeted the tree/anchor bucket, which is 6.1% of CPU at the height measured in §2a, versus Groth16's 60.9% — still worth doing, but no longer the biggest lever known.
4. **Direct disk-I/O measurement** via Instruments System Trace / File Activity templates (kernel-tracepoint-based, no further permission setup expected) — would replace the current stack-frame inference of the I/O bucket (15–18% in §2, 26.2% in §2a's specific window) with real per-file open/read counts and latencies, and confirm or refute the open-read-close theory (§4a) — specifically, how much is read-side vs. write-side — before investing in item 5.
5. **Disk I/O fix** (§4a), contingent on item 4: keep `blk*.dat`/`rev*.dat` file handles open across consecutive block reads within an import run instead of open-read-close per block. Non-consensus-affecting, lower risk than item 3.
6. **Memory profiling**: not blocked, just needs a different tool than originally tried. Instruments' Allocations/Leaks templates attach successfully (`task_for_pid`, entitlement + Developer Mode both satisfied) but their recorded data is a GUI-only proprietary blob with no `xctrace export` schema in this Instruments version — headless readout is a dead end via that specific template. `vmmap`, `heap`, and `malloc_history` are all present on this machine (`/usr/bin/vmmap` etc.) and are CLI-native with no export-format dependency — use one of those instead, or open the existing `.trace` files in the Instruments GUI directly. Not yet done either way.
7. **`-O1` vs `-O2`** as a deliberate, documented pair of builds — a user-reported "little difference" from an earlier, undocumented measurement, not yet reproduced here.
8. Done: the temporary match/no-match instrumentation (`libzcash::MerkleRootCacheStats`, per-block ground-truth counters) is now `#ifdef ZERO_PERF`-gated. A normal build (`ZERO_PERF` undefined) has zero trace of it, confirmed via `nm` on the built binary. Full regression re-run on this clean build: Boost `test_bitcoin` 284/284 (`--report_level=short`), `zero-gtest` 207/207 (`--gtest_brief=1`, `CachedWitnessesCleanIndex` excluded per existing quarantine) — no regressions from the removal. Remaining before this is fully finished: eventually strip the guarded code entirely once no longer needed, and do a final `-O2`/no-`-g` build to re-check release-shape performance.

---

## 6. How to make these determinations fast and simple next time

This investigation spent real time on two solvable problems: (a) parsing xctrace's XML export format correctly, and (b) figuring out which block-height range a profiling window actually covered. Both are now mechanical — do them this way, don't re-derive from scratch:

**Parsing an xctrace export.** `xcrun xctrace export` produces a flat XML table where `<thread>`, `<weight>`, `<tagged-backtrace>`, and even individual `<frame>` elements are each defined in full **only once**, and every subsequent occurrence is a bare `ref="N"` backreference to that first definition. A naive per-`<row>` regex that expects each row to be self-contained will silently undercount almost everything after the first sample — this is what caused an early parse of this same data to (wrongly) show 86% of samples as unbucketed "other." The reusable, correct tool is now checked in at `reindex-profile/tools/bucket_profile.py`: it maintains id→value tables for all four backreference types, resolves them per row, and buckets by call-stack substring match (edit the `BUCKETS` dict at the top to add/adjust categories — e.g. this is how the Groth16 vs. tree/anchor split in §2a was separated out). Usage:

```bash
xcrun xctrace export --input some.trace \
  --xpath '/trace-toc/run[1]/data[1]/table[@schema="time-profile"]' \
  --output some_agg.xml
python3 reindex-profile/tools/bucket_profile.py some_agg.xml [thread-name-substring]
```

The second argument filters to one thread by substring match (defaults to `zcash-loadblk`, the reindex/import worker thread this investigation cares about) — always filter to a specific thread; an unfiltered profile is dominated by idle-thread noise (§2).

**Getting the height window right — the trap to avoid.** It's tempting to assume the profiled window covers "recent" heights near wherever the datadir ended up at the end of the run, or to estimate the window's start time from when the launching shell command was issued. Both are wrong in ways that silently corrupt the result: a background-launched process's wall-clock launch time is not the same as when `xctrace record`'s 60-second window actually started (there's a gap while `-reindex` gets underway and while `xctrace` attaches), and — critically — **the machine's local clock and the trace/log timestamps may be in different timezones**, which will silently shift the derived window by hours if not accounted for (this happened during this investigation: an initial attempt used a UTC log timestamp as if it were the local PDT launch time, and landed on the wrong 60-second window entirely, at a height low enough to be pre-Sapling-activation — which should have been a red flag the moment Groth16 samples appeared in the data anyway). The reliable procedure:

1. Get the trace's actual recording start time, in its own stated timezone, from the export's table-of-contents: `xcrun xctrace export --input some.trace --toc | grep start-date`.
2. Convert explicitly to whatever timezone `debug.log` uses (check one `debug.log` line's format — Zero's is UTC) before comparing.
3. Grep `debug.log` for `UpdateTip` lines whose timestamp falls in `[start, start+60s]`, and read `height=` off the first and last matches in that range. Don't grep for a specific height number as a substring search (e.g. `height=937` will also match `height=937237` — a real mistake made during this investigation) — always bound by timestamp, then read the height back out.
4. Once bytes/sec is wanted alongside blocks/sec: sample block sizes across the derived height range via `getblock <hash>` RPC (needs a running node — a plain, non-`-reindex` launch pointed at the already-reindexed scratch datadir is enough and doesn't require redoing the reindex). A handful of evenly-strided samples gives a usable estimate; block size at any given height range can vary by two orders of magnitude block-to-block, so note the estimate's uncertainty rather than presenting it as exact — only a full sum over every block in range is exact, and that costs one RPC call per block.

**The general lesson for "fast and simple" next time:** don't trust a bucket percentage, a height range, or a throughput figure that wasn't independently cross-checked against a second source of truth (a different trace, a log timestamp, an RPC call) — every number in §2a that turned out to matter (the Groth16 split, the correct height window, the throughput estimate) was caught or confirmed by exactly this kind of cross-check, and every mistake caught along the way (the 86%-other parse bug, the wrong-timezone height window, the substring-match height search) was a case of trusting one source without a second check.
