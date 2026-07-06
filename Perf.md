# `zerod` sync performance: current understanding, and next steps

## 0. Next tasks

Open, in priority order:

1. **Re-test the disk-I/O fix (§3) at post-Sapling heights, and with `-perffdcache` isolated from `-perfbufsize`.** The completed A/B found no measurable throughput win, but only at pre-Sapling heights and only with the fd-cache always on (only buffer size varied) — open questions, not a closed result.
2. **Code and test: memory profiling** — `vmmap`/`heap`/`malloc_history` (CLI-native, no export-format dependency) are the next thing to try; Instruments' Allocations/Leaks templates attach but their data is GUI-only in this Instruments version.
3. **Root-existence index for Sprout anchor validation** in `HaveShieldedRequirements` (§4's concrete lead) — confirm anchors via membership check instead of reconstructing tree state, matching Zebra's Sapling/Orchard technique. Targets the tree/anchor bucket (~14% of CPU, §2), smaller than Groth16 but larger than disk I/O's remaining headroom. Not started.
4. **Scope Sapling Groth16 proof verification for optimization headroom** — the largest bucket by far (48–55% of CPU post-Sapling-activation, §2). Research whether `bellman` (Zero's `librustzcash` Groth16 implementation) supports batch proof verification, and whether that work could run on the currently-idle `zcash-scriptch` threads (structural, not fundamental, limitation — §2). Not started.
5. **Scope NEON blake2b integration for Equihash verification** (§5) — a maintained implementation exists (`BLAKE2/BLAKE2`'s `neon/` directory) but integration effort (API fit, licensing, correctness validation against known-answer vectors) hasn't been assessed.
6. **Code and test: `-O1` vs `-O2` build comparison** — a user-reported "little difference," never reproduced with a real measurement.

Postponed (documented here so they aren't lost, not scheduled for near-term work):
- **Run the bootstrap-import leg of `bench_matrix.sh` for real** — the datadir-reset bug is fixed and validated on a small dry run only; a full 4-trial × 2-condition bootstrap comparison hasn't been run.
- **`LoadBlockIndexDB`'s missing interruption point** (§3) — a real, narrow-blast-radius gap; not scoped for a fix, may stay a documented limitation indefinitely.

Done (pointer only — see the referenced section for the finding):
- §2: CPU bucket breakdown, corrected and confirmed chain-wide — Groth16, not tree/anchor recomputation, dominates post-Sapling.
- §4: the `IncrementalMerkleTree::root()` latch — implemented, correct, measurably flat (redundancy it removed was already cheap).
- §5: root-caused Equihash's CPU share to an unaccelerated blake2b backend (libsodium has no ARM/NEON path), not an algorithm issue.
- §3: read-handle latch + buffer-size knob for disk I/O — implemented, measured, no win found yet (item 1 above); code-reviewed and tightened (only `main.cpp`/`main.h` carry changes, `streams.h`/`init.cpp` are back to zero diff from upstream — see §3's implementation-status note).

---

## 1. Scope, method, and reproduction procedure

**Subject:** where `zerod` spends CPU during `-reindex` (rebuild `chainstate` from local `blocks/*.dat`) and `bootstrap.dat` import (bulk-load a pre-staged flat file of blocks) — the two faster-than-network ways to catch a node up. Both were assumed "fast" but never measured; this investigation measured them, found the dominant costs, and implemented and measured fixes for two of them.

**Working tree:** `ZeroPerf` (`/Users/walter/Work/ZK/ZeroPerf`, branch `perf-401`), built at `-O1` (`-pipe -O1 -g -fwrapv -fno-strict-aliasing`, the repo default). Binary is self-contained (verified via `otool -L`: only system libraries dynamically linked, all third-party dependencies static).

**Terms:**
- **Bucket:** one of a small number of mutually-exclusive CPU-time categories a profiling sample falls into, matched against *any* frame in a sample's call stack (not just the leaf).
- **Latch:** a single-slot memoization — one stored value (or empty), cleared by the operations that change underlying state, repopulated on next read. Not a cache: no key, no multiple entries, no eviction policy, because there is only ever one live value to remember.
- **Activation height:** the mainnet block height at or after which a network upgrade's rules apply. Sapling: height 492,850 (`chainparams.cpp`).

**Profiling method:** a real mainnet datadir (not synthetic/regtest — script/tx mix affects where time goes) profiled with Instruments Time Profiler (`xcrun xctrace`, headless CLI) attached to the single worker thread that does the actual reindex/import work (`zcash-loadblk`, running `ThreadImport`). Every other thread (idle script-check-queue workers, RPC/net/wallet threads) is filtered out — unfiltered, all-threads profiles are dominated by idle-thread noise (85%+ of raw samples blocked on a condvar) and say nothing about where real work goes.

**Reproduction procedure** (fresh scratch datadir → launch → attach profiler → export/bucket → determine the exact height window covered):

1. Fresh scratch datadir (chainstate excluded; `-reindex` rebuilds it — source `~/Library/Application Support/Zero/` is only ever read, never modified):

   ```bash
   cd /Users/walter/Work/ZK/ZeroPerf
   rm -rf reindex-profile/datadir
   rsync -a --exclude='chainstate' "/Users/walter/Library/Application Support/Zero/" reindex-profile/datadir/
   ```

2. Launch `-reindex`, poll `getblockcount` via `zero-cli` until height has advanced (RPC gives an exact, race-free signal — don't guess from wall-clock or log-tailing), then attach Time Profiler:

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

   `xcrun xctrace export` produces a flat XML table where `<thread>`, `<weight>`, `<tagged-backtrace>`, and `<frame>` elements are each defined in full **only once**, with every later occurrence a bare `ref="N"` backreference — a naive per-row regex silently undercounts almost everything after the first sample. `reindex-profile/tools/bucket_profile.py` resolves all four backreference types correctly and buckets by call-stack substring match (edit the `BUCKETS` dict to add/adjust categories). Second argument filters to one thread by substring (default `zcash-loadblk`) — always filter to a specific thread.

4. **Determine the exact block-height range the window covered** — not from the datadir's *final* height, which is a trap; block/tx mix varies enormously by height, so a bucket breakdown is only interpretable together with its height range:

   1. Get the trace's actual recording start time, in its own stated timezone: `xcrun xctrace export --input some.trace --toc | grep start-date`.
   2. Convert explicitly to whatever timezone `debug.log` uses (Zero's is UTC) — a background-launched process's wall-clock launch time is not the same as when the recording window actually started, and mixing local time with a UTC log timestamp will silently shift the derived window by hours.
   3. Grep `debug.log` for `UpdateTip` lines whose timestamp falls in `[start, start+60s]`, and read `height=` off the first and last matches — bound by timestamp, not by searching for a height number as a substring (`height=937` also matches `height=937237`).
   4. For bytes/sec alongside blocks/sec: sample block `size` at a handful of evenly-strided heights via `getblock` RPC (needs a running node — pointing a plain launch at the already-reindexed scratch datadir works, no need to redo the reindex). Block size varies by two orders of magnitude block-to-block, so treat this as an estimate with real uncertainty, not an exact figure.

**General lesson:** don't trust a bucket percentage, height range, or throughput figure that wasn't cross-checked against a second source of truth (a different trace, a log timestamp, an RPC call) — every number in §2 that turned out to matter was caught or confirmed this way, and every early mistake (an 86%-other mis-parse, a wrong-timezone height window, a substring-match height search) was a case of trusting one source without a second check.

---

## 2. CPU cost breakdown: what dominates, and why it's height-dependent

**Original measurement** (`-reindex` on two builds, `bootstrap.dat` import, chain heights ~10K–2M; mutually exclusive buckets, `zcash-loadblk` thread only, 0% unaccounted backtraces in every run):

| Bucket | Typical range | Call path (leaf → root) |
|---|---|---|
| Sapling/Sprout tree update | 57–58% | `Fr::mul_assign`/`Fr::inverse` (BLS12-381 field arith) ← `jubjub::edwards::Point::add` ← `librustzcash_merkle_hash` ← `IncrementalMerkleTree::root()` ← `CCoinsViewCache::AbstractPushAnchor` ← `ConnectBlock` |
| Equihash PoW verification | 24–27% | `blake2b_compress_ref` ← `blake2b_final` ← `Equihash<192,7>::IsValidSolution` ← `CheckEquihashSolution` ← `CheckBlockHeader` |
| Disk I/O | 15–18% | `OpenDiskFile`/`ReadBlockFromDisk`/`UndoWriteToDisk` (`fopen`/`open` syscalls) ← `LoadExternalBlockFile`/`ConnectBlock` |

**This breakdown is identical for `-reindex` and `bootstrap.dat` import** — both call the same `ConnectBlock`/`CheckEquihashSolution`/`AbstractPushAnchor` validation per block; `bootstrap.dat` only changes how block bytes arrive, not what validation happens once a block is in hand. Measured `bootstrap.dat` import: **145.7 minutes** (8,743,120 ms, self-reported) for 2,468,990 blocks, ≈282 blocks/sec average across the entire chain history. **`bootstrap.dat`'s entire benefit is skipping network download time; it cannot reduce the CPU-bound validation cost.**

**The idle script-check-queue threads (`zcash-scriptch`, `-par`) cannot help any of this bucket breakdown.** They're wired only to per-transaction signature verification, never to anchor/tree updates, in every codebase checked (Bitcoin Core, zcashd, Zero, Zebra). This is a per-call cost problem in code that has never been parallelized, not a parallelism gap in otherwise-idle threads.

**Correction — the table above conflates two distinct costs.** Sapling's Groth16 zk-SNARK proof verification (`librustzcash_sapling_check_spend`/`_check_output`, called from `ContextualCheckTransaction`) *also* does elliptic-curve arithmetic over the same `jubjub`/BLS12-381 types used by tree-anchor recomputation, deep inside `bellman::groth16::verifier::verify_proof` — the original bucket definitions couldn't tell these apart. Re-bucketing with a set that checks for `bellman::groth16::verifier::verify_proof`/`miller_loop`/`final_exponentiation` specifically splits it correctly:

| Bucket | % of CPU (height 610,758–626,806) | Call path |
|---|---|---|
| **Sapling Groth16 proof verification** | **60.9%** | `Fq::mul_assign`/`Fq12::square` (BLS12-381 pairing arith) ← `miller_loop` ← `bellman::groth16::verifier::verify_proof` ← `librustzcash_sapling_check_spend`/`_check_output` ← `ContextualCheckTransaction` |
| Disk I/O | 26.2% | Same syscalls as above |
| Equihash PoW verification | 6.9% | Same call path as above |
| Sapling/Sprout tree/anchor update | 6.1% | Same call path as above — **this is what the original "57–58%" figure actually measured almost none of** |

Cross-checking against an earlier-build trace spanning the full 0–2.47M height range and re-bucketed with the corrected script gives **0 Groth16 samples**, reproducing the original 58/26/16 split almost exactly — confirming the corrected script isn't the source of the discrepancy, and that the original figure was measured on a height range with negligible Sapling shielded-tx volume (Sprout-dominated or pre/early-Sapling), so it wasn't wrong about *that window*, only wrong as a general claim about "the" bucket breakdown.

**The bucket breakdown is height-dependent, not a fixed constant** — any profiling result needs its block-height range reported alongside it to be interpretable. Throughput for the 610,758–626,806 window: 267.5 blocks/sec (exact, from `UpdateTip` timestamps), ~330 KB/sec (estimated from 41 evenly-strided `getblock` samples, individual blocks ranging 685–160,858 bytes) — consistent with the whole-chain ~282 blocks/sec average.

**Whole-chain confirmation, six 5-minute windows spanning the reindexed range** (`contrib/perf/capture_sequence.sh` drove the repeating capture; `contrib/perf/decode_captures.py` exported/bucketed each one and derived its exact height range from the trace's own timestamp cross-referenced against a `debug.log` snapshot — see `contrib/perf/README.md`):

| Capture | Height range | blocks/sec | Groth16 | Disk I/O | Tree/anchor | Equihash |
|---|---|---|---|---|---|---|
| 1 | 5,373 → 336,144 | 1,102.6 | 0% (pre-Sapling) | 16.54% | 54.99%* | 28.46% |
| 2 | 626,078 → 702,200 | 253.7 | 54.74% | 25.03% | 13.83% | 6.40% |
| 3 | 995,392 → 1,083,180 | 292.6 | 52.77% | 26.20% | 13.67% | 7.36% |
| 4 | 1,411,397 → 1,482,630 | 237.4 | 55.23% | 24.94% | 13.94% | 5.88% |
| 5 | 1,693,202 → 1,777,052 | 279.5 | 53.84% | 25.03% | 14.01% | 7.12% |
| 6 | 2,032,619 → 2,173,838 | 470.7 | 48.09% | 26.02% | 13.78% | 12.11% |

*Capture 1 is pre-Sapling-activation: its "tree/anchor" share is inflated only because Groth16 doesn't exist yet at these heights.

Post-Sapling (captures 2–6), Groth16 is consistently dominant (48–55%) across five independently-sampled ranges spanning nearly the whole post-activation chain — the single-window 60.9% figure was directionally correct, though the exact percentage tracks per-window shielded-tx volume rather than being a fixed per-block overhead. Disk I/O (~25–26%) and tree/anchor (~14%) are comparably stable. Equihash's *share* climbs from ~6% to ~12% (captures 4→6) — a percentage effect, not a cost effect (see per-block table below): capture 6 processed more blocks/sec, spreading a constant per-header cost over less wall-clock time per block.

**Per-block absolute cost, the more informative view:**

| Capture | Groth16 ms/block | Disk I/O ms/block | Tree/anchor ms/block | **Equihash ms/block** |
|---|---|---|---|---|
| 1 (pre-Sapling) | — | 0.149 | 0.494 | **0.2557** |
| 2 | 2.149 | 0.983 | 0.543 | **0.2513** |
| 3 | 1.788 | 0.888 | 0.463 | **0.2493** |
| 4 | 2.324 | 1.050 | 0.587 | **0.2476** |
| 5 | 1.921 | 0.893 | 0.500 | **0.2541** |
| 6 | 1.005 | 0.543 | 0.288 | **0.2530** |
| **mean / CV** | 1.84ms / **27.7%** | 0.75ms / **45.7%** | 0.48ms / **21.5%** | **0.252ms / 1.2%** |

Groth16, disk I/O, and tree/anchor per-block cost all vary substantially (21–46% CV) — expected, each scales with shielded-tx volume or block/undo-file size. **Equihash's per-block cost is essentially constant (0.252ms ± 1.2% CV)** across pre- and post-Sapling heights and blocks/sec ranging 237–1,103 — the signature of a fixed per-call cost independent of block content (root cause: §5).

**Not yet investigated:** nothing has targeted Groth16 verification cost specifically (§0 item 2) — the latch (§4) and the proposed root-existence index (§0 item 4) both target the tree/anchor bucket only, ~6–14% of CPU, not the 48–60% Groth16 bucket.

**Memory profiling:** Instruments' Allocations/Leaks templates attach successfully (`task_for_pid`, entitlement + Developer Mode satisfied) but their recorded data is a GUI-only proprietary blob with no `xctrace export` schema in this Instruments version — headless readout is a dead end via that template. `vmmap`/`heap`/`malloc_history` are CLI-native with no export-format dependency and haven't been tried yet (§0 item 5).

---

## 3. Disk I/O: open-close-per-block mechanism, and the implemented fix

**Mechanism.** `OpenBlockFile`/`OpenUndoFile` both call `OpenDiskFile`, which does a **fresh, unconditional `fopen()` on every call** — no persistent or cached `FILE*` anywhere in this path. Every call site wraps the fresh `FILE*` in a stack-local `CAutoFile`, whose destructor calls `fclose()` unconditionally the moment the function returns. `ConnectBlock`/`LoadExternalBlockFile` call these once or twice per block (a read, usually an undo-data write) — a full ~2.5M-block reindex therefore performs on the order of **2.5–5 million `fopen`/`fclose` pairs**, even though the underlying `blkNNNNN.dat`/`revNNNNN.dat` files are ~128MB each holding thousands of consecutive blocks: the overwhelming majority of those pairs reopen a file that was just closed moments earlier for the previous block. Each pair is a full kernel `open`/`close` round-trip, and `fopen` additionally re-initializes stdio's internal buffer from scratch every time — cost paid once per block instead of once per file, a 100–1000x amplification.

**Direct syscall-level confirmation** (`fs_usage -f filesys -w <pid>`, root-only, always available, no SIP change needed unlike full `dtrace`; Instruments' File Activity template records real data but has no `xcrun xctrace export` schema in this Instruments version — GUI-only, not usable headlessly): in a 180-second `-reindex` window, `open` alone was 23% of traced filesystem time; `open+close+stat64+fstat64` together came to ~0.048ms/block — real, but only 6–34% of the disk-I/O bucket depending on capture window, meaning most of that bucket is genuine read/write/transfer time, not open/close overhead.

**The fix, `#ifdef ZERO_FDCACHE`-gated** (a macro separate from `ZERO_PERF`, independently buildable/strippable):

- **`-perffdcache=1`** (default 0): `ReadBlockFromDisk`/`UndoReadFromDisk` use a single-slot read-handle latch per file kind (`BlockFileKind::BLK`/`REV`) instead of `OpenDiskFile`'s fresh-open/close-per-call path — mirroring `IncrementalMerkleTree::root()`'s latch (§4), not a multi-entry keyed cache. Ownership stays with the latch: `CAutoFile` borrows the handle for the duration of one read and is prevented from closing it on destruction via `ReleaseOnScopeExit`, a small RAII helper that calls `CAutoFile::release()` (an already-existing, pre-`ZERO_FDCACHE` method — no changes to `CAutoFile`/`streams.h` were needed). Stats (opens/hits, plain counters under the latch's own lock) log periodically as `ReadFdCache: height=N opens=... hits=... hit-rate=...%`. Read-only handles only: write handles are excluded, since `FlushBlockFile`'s truncate/close and `CAutoFile`'s owning-close semantics make caching writable handles a real correctness hazard for a smaller expected benefit.
- **`-perfbufsize=N`** (default 0 = unchanged libc default): `setvbuf`s a freshly-opened handle to an N-byte buffer in `OpenDiskFile`, instead of the libc/filesystem default (commonly 4–8KB).

**Latch, not a multi-slot cache — checked, not assumed.** An earlier version used a 4-slot LRU on the theory that RPC/reorg access could interleave across multiple files. Measuring real access during a `-reindex` run showed the open count grows strictly monotonically with no repeats for long stretches, then occasionally revisits an earlier file — traced to `LoadExternalBlockFile`'s "out of order child" handling, which reprocesses an earlier block file when a later block's parent hasn't connected yet. A single-slot latch handles this correctly by design (a miss costs one `fopen`, not a correctness issue) — measured hit rate stayed **99.9%** even across that access pattern, heights 0 through ~900,000.

**Implementation status: functionally correct, compiles clean both with and without `ZERO_FDCACHE`, no unit test coverage.** Only `main.cpp`/`main.h` carry changes — `streams.h` and `init.cpp` ended at zero diff from upstream after an earlier, more invasive draft (a `CAutoFile` ownership flag, an unused `CloseAllCachedReadFiles` shutdown hook) was reviewed back out in favor of the smaller `ReleaseOnScopeExit` approach and removing dead code. Known, accepted gaps: `ReleaseOnScopeExit` is constructed (as an inert no-op) even in normal builds without `ZERO_FDCACHE`; no gtest exists for the latch's hit/miss/stale-reopen behavior, unlike §4's latch which has a dedicated test.

**Measured result: no throughput improvement from either flag, at pre-Sapling heights.** Repeated-trial A/B (`contrib/perf/bench_matrix.sh`: fixed height range warmup=50,000→measured 50,000–350,000, exact elapsed time from `debug.log` `UpdateTip` timestamps, 4 trials per condition, both with `-perffdcache=1`):

| Condition | n | Mean blk/s | Stdev | CV |
|---|---|---|---|---|
| Default buffer | 4 | 1,094.1 | 15.9 | 1.45% |
| 1MB buffer | 4 | 1,075.9 | 29.9 | 2.77% |

Difference: -1.66%, t ≈ -1.07 — not distinguishable from noise at this sample size (would need |t| > ~2.5–2.6 for significance with n=4 each). This establishes the noise floor this methodology resolves at a 300,000-block window: ~1.5–3% CV per condition. Consistent with average block size (~1.3–2KB) being far smaller than either buffer setting. Not yet tested: `-perffdcache` against a true no-fdcache baseline (all trials above had it on), and the same comparison at post-Sapling heights (§0 item 3).

**A datadir-reset bug found and fixed while building the bootstrap-import benchmark leg.** `bench_matrix.sh`'s scratch-datadir reset originally used one procedure for both `-reindex` and `-loadblock` trials — rsync excluding only `chainstate`. Correct for `-reindex` (which rescans existing `blk*.dat`/`rev*.dat` by design), wrong for `-loadblock`: reusing a fully-synced source's `blocks/` directory made `-loadblock` reconcile its import against an already-populated, multi-million-block index instead of starting from an empty chain. Fixed: bootstrap-mode resets now also exclude `blocks/`. Before the fix, `LoadBlockIndexDB` reported an existing index spanning `heights=2440414...2484412` and RPC stayed in `"Loading block index..."` (`getblockcount` returning error -28) for over 50 minutes before any import progress was measurable; after the fix, RPC comes up and warmup height is reached within seconds.

**A narrow-blast-radius interruptibility gap found while diagnosing the above (pre-existing, upstream-inherited — not introduced by this work).** The stuck process couldn't be stopped by RPC `stop` (not up yet) or `SIGTERM` (no effect for 50+ minutes) — traced to `LoadBlockIndexDB`'s per-block accounting loop (the `BOOST_FOREACH` over `vSortedByHeight` building `nChainWork`/`nChainTx`/branch-ID data), which has exactly one `interruption_point()` call *before* the loop starts and none inside it. On a multi-million-block index this loop alone can run for tens of minutes with no way to interrupt it short of `SIGKILL`. Only reachable when reconciling a very large pre-existing index (not normal `-reindex`/`-loadblock` usage). `bench_matrix.sh` now bounds every wait loop to 10 minutes and escalates `SIGTERM` then `SIGKILL` automatically.

**Tooling:** `contrib/perf/bench_matrix.sh` — repeated-trial A/B harness for any `-perffdcache`/`-perfbufsize` combination, against `-reindex` and (given a `bootstrap.dat` path) `-loadblock`. See `contrib/perf/README.md` for usage.

---

## 4. The Merkle-root latch

**The confirmed inefficiency.** `IncrementalMerkleTree::root()` recomputes fully from `left`/`right`/`parents` on every call — a real `Hash::combine()` → `librustzcash_merkle_hash` FFI call per populated tree level. `ConnectBlock` calls `sapling_tree.root()`/`sprout_tree.root()` **twice per block, unconditionally**: once inside `PushAnchor`→`AbstractPushAnchor`, once directly — computing the identical value both times whenever nothing mutated the tree in between.

**Fix:** a `mutable boost::optional<Hash> cached_root` latch on `IncrementalMerkleTree`, populated on first `root()` call, cleared in the only two places that mutate tree state (`append()`, post-deserialize). Pure memoization of a deterministic function of existing state — no change to what's hashed, so no consensus or serialization-format risk.

**Why it helps `ConnectBlock` but not `HaveShieldedRequirements` — value vs. reference.** `AbstractPushAnchor` takes `tree` by const reference, so `ConnectBlock`'s two calls operate on the same object — the first populates the latch, the second matches it. `CCoinsViewCache::HaveShieldedRequirements`, which validates each Sprout joinsplit's anchor, declares its tree **by value, freshly, inside the per-joinsplit loop** — a brand-new object every iteration, mutated once and read once before going out of scope. There is structurally no second read on the same object for the latch to ever serve — every call here is a guaranteed no-match, regardless of implementation.

**Validation.** Existing gtest suite passes unmodified; a new test (`merkletree.RootCacheConsistency`) exercises match/no-match behavior across append and serialize/deserialize round-trips; full regression (Boost `test_bitcoin` 284/284, `zero-gtest` 206/206) clean, with a pre-existing unrelated wallet-key test flake (~1-in-9 runs, present on the unmodified baseline too) ruled out as false attribution. The instrumentation (`libzcash::MerkleRootCacheStats`) is `#ifdef ZERO_PERF`-gated and confirmed to leave zero trace in a normal build via `nm`; full regression on that clean build (Boost 284/284, gtest 207/207) shows no regressions from the removal.

**Measured impact: correct, but flat.** Re-profiled with the same methodology: Sapling-tree bucket 57.9% vs. the pre-fix 58.0% baseline — no measurable change, despite the latch being demonstrably active. Ground-truth per-block counters (since removed, superseded by coarser periodic logging) explain why:

| Block category | avg `root()` calls/block | match rate |
|---|---|---|
| Idle (no shielded activity) | 5.00 | **100%** |
| Sapling outputs only | 5.00 | 80% |
| Sprout joinsplits only | 8.28 | 48.3% |
| Both | 8.22 | 36.4% |

Idle and Sapling-output-only blocks match perfectly but were already cheap (empty/near-empty tree). **Sprout joinsplits drive both the extra call volume and the low match rate**, since each joinsplit's anchor is checked via `HaveShieldedRequirements`'s fresh-object pattern — structurally unmatchable. Sapling spends never call `.append()`/`.root()` in that function, so they were never a candidate for this latch either way. **Conclusion: the latch is correct and removes a real, confirmed redundancy, but that redundancy was a small, cheap-skewed slice of the bucket.** The bucket's real cost is (a) genuinely new `append()`/`combine()` work proportional to shielded-output volume — unavoidable — and (b) Sprout-joinsplit anchor validation's fresh-object-per-joinsplit pattern, which no per-object latch can help by construction.

**Latch vs. cache — checked against Zebra directly, not assumed.** Zebra's own Sprout tree type uses the identical single-slot latch pattern (`cached_root: RwLock<Option<Root>>`, cleared on `append()`), confirming a keyed cache isn't the standard answer here either. The real difference: Zebra's Sapling/Orchard anchor validation never constructs a tree object during validation at all — it checks anchor membership against a `HashSet`/RocksDB key-existence check, populated once at commit time — a *different technique* (a membership index over previously-seen roots), not a bigger cache. Zebra's Sprout path still pays the same construct/append/read cost for **chained joinsplits within one transaction** as Zero does, by its own source's admission ("this check is expensive, because it updates a note commitment tree for each sprout JoinSplit"). **So a keyed/multi-entry cache would not have helped `HaveShieldedRequirements` either** — the actual problem isn't insufficient memoization, since Zebra hits the identical wall despite a mature, independent implementation. The membership-index technique is the concrete lead for further work (§0 item 4), not a bigger latch.

---

## 5. Equihash's CPU share: a libsodium/ARM gap, not an algorithm issue

**The question.** §2 showed Equihash verification taking 6–28% of CPU depending on height, with `blake2b_compress_ref` recurring in every sample. Given Equihash verification is supposed to be cheap by design (asymmetric proof-of-work), is this a real inefficiency? **Answer: the algorithm is correct and minimal; the cost is a missing SIMD backend, specific to this build's architecture.**

**The algorithm itself is correct and lightweight.** `Equihash<N,K>::IsValidSolution` does exactly what the spec requires for mainnet's `Equihash<192,7>`: `2^K = 128` calls to `GenerateHash` (one blake2b invocation each), followed by a 7-round collision/ordering/distinctness check using only `memcmp`/XOR-style comparisons — no re-solving, no search, no redundant hashing. There is no algorithmic bug here.

**The cost is entirely inside blake2b's compression function, running unaccelerated on this hardware.** Every one of the 128 per-block hash calls goes through libsodium (not the Rust `blake2-rfc` crate also vendored in this tree — that's for something else). libsodium 1.0.21 dispatches its blake2b compression function at runtime via `blake2b_pick_best_implementation()`, choosing between `avx2`/`sse41`/`ssse3`/`ref` backends — but **all three accelerated backends are gated behind x86-only intrinsics headers**. On `aarch64-apple-darwin` (Apple Silicon), none of those headers exist, so the dispatcher unconditionally falls through to `blake2b_compress_ref`, the plain scalar C implementation, for every call.

**Checked and ruled out: no fix via upgrading dependencies or Apple's native crypto.** libsodium has released twice since 1.0.21 (1.0.22, 2026-04-09, current) — its actual `ChangeLog` shows post-quantum KEMs and new SHA-3 APIs, no mention of blake2b/NEON/ARM anywhere. Across every release checked (1.0.18–1.0.22), ARM/aarch64 wins landed for AES-GCM, AEGIS, and Argon2/SHA3 — blake2b has never once been included; a version bump is confirmed not to fix this. Apple's CryptoKit has no BLAKE2b support at all (SHA-2/AES/legacy only).

**A real, actively-maintained implementation to integrate from, if pursued.** The official reference repo `BLAKE2/BLAKE2` ships a `neon/` directory with `blake2b-neon.c` implementing BLAKE2b via ARM NEON/ASIMD intrinsics, plus a dedicated `Aarch64` makefile — and its most recent commit (2023) was a correctness fix by `veorq`, one of the two original BLAKE2 authors. Not stale or abandoned code. Integration would mean vendoring this implementation and wiring it in as a replacement compress function for this call path (either patched into the vendored libsodium build, or called directly from `equihash.cpp`, bypassing libsodium's generichash API for this one use site). Not yet scoped past confirming the file exists and targets the right architecture — actual integration effort (API fit, licensing, correctness validation against known-answer vectors) hasn't been assessed (§0 item 1).

**Independent confirmation this is a fixed, hardware-level cost, not something content-dependent:** Equihash's per-block cost held constant at 0.252ms ± 1.2% CV across six capture windows spanning pre- and post-Sapling heights and blocks/sec ranging 237–1,103 (§2's per-block table) — versus 21–46% CV for every other bucket, all of which scale with shielded-tx volume or block size. A cost that doesn't move with any chain-content variable is exactly what "fixed per-header hashing cost, paid by an unaccelerated compression function" predicts.
