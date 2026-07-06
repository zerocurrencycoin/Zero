# `zerod` sync performance: current understanding, and next steps

## 0. Next tasks

Open, in priority order:

1. **Finish the full-chain memory-footprint timeline** (§7) — a height-checkpoint `vmmap` sweep (100K/500K/900K/1.5M/2M/2.47M-final) was still running as of this writing; only two checkpoints (278K, 500K) are in hand so far. Re-run `malloc_history`/`MallocStackLogging` at a window sampled entirely post-Sapling-activation (the current stack-logged window straddles the boundary, likely understating Sapling-Groth16-adjacent bookkeeping's share).
2. **Scope NEON blake2b integration for Equihash verification** (§5) — a maintained implementation exists (`BLAKE2/BLAKE2`'s `neon/` directory) but integration effort (API fit, licensing, correctness validation against known-answer vectors) hasn't been assessed.
3. **Code and test: `-O1` vs `-O2` build comparison** — a user-reported "little difference," never reproduced with a real measurement.
4. **Implement Sapling Groth16 batch verification** — the largest bucket by far (48–55% of CPU post-Sapling-activation, §2). §6 scoped this: real batch-verification code exists in `zkcrypto/bellman` (the modern successor to Zero's pinned, ~2019-vintage `ebfull/bellman`) and the pinned `pairing::Engine::miller_loop` primitive it would need already exists in-tree, so a hand-port is feasible without a full crate-stack upgrade — but it requires restructuring `ContextualCheckBlock`'s per-transaction verify-or-reject control flow into buffer-then-batch-verify, plus a per-batch CSPRNG, and is real consensus-code-caliber work. Not started past scoping. §7 additionally confirmed Groth16 verification itself allocates essentially no heap memory, so this is a pure-CPU optimization target with no memory-scaling side effects to worry about.

Postponed (documented here so they aren't lost, not scheduled for near-term work):
- **Run the bootstrap-import leg of `bench_matrix.sh` for real** — the datadir-reset bug is fixed and validated on a small dry run only; a full 4-trial × 2-condition bootstrap comparison hasn't been run.
- **`LoadBlockIndexDB`'s missing interruption point** (§3) — a real, narrow-blast-radius gap; not scoped for a fix, may stay a documented limitation indefinitely.
- **Restructuring validation to batch Groth16 proofs and/or share work with idle `zcash-scriptch` threads** (§6) — scoped, feasible in principle, but a substantial control-flow change to consensus-critical code; not scheduled.

Done (pointer only — see the referenced section for the finding):
- §2: CPU bucket breakdown, corrected and confirmed chain-wide — Groth16, not tree/anchor recomputation, dominates post-Sapling.
- §4: the `IncrementalMerkleTree::root()` latch — implemented, correct, measurably flat (redundancy it removed was already cheap).
- §5: root-caused Equihash's CPU share to an unaccelerated blake2b backend (libsodium has no ARM/NEON path), not an algorithm issue.
- §3: read-handle latch + buffer-size knob for disk I/O — implemented and measured at both pre- and post-Sapling heights, with a true no-fdcache baseline isolating `-perffdcache`'s own effect from `-perfbufsize`'s — no throughput win found at either height range; code-reviewed and tightened (only `main.cpp`/`main.h` carry changes, `streams.h`/`init.cpp` are back to zero diff from upstream — see §3's implementation-status note).
- §4: root-existence index for Sprout/Sapling anchor validation in `HaveShieldedRequirements` — implemented (`HaveSproutAnchorAt`/`HaveSaplingAnchorAt`, existence-only checks through the `CCoinsView` chain down to a `db.Exists()` on the same DB key, skipping tree deserialization), matching Zebra's membership-check technique; full regression clean (Boost `test_bitcoin` 284/284; `zero-gtest` 205/207, the 2 failures reproduced identically against the unmodified baseline — pre-existing test-order-dependent flakiness, not a regression).
- §6: scoped Sapling Groth16 batch-verification headroom — confirmed no batching exists in the pinned `bellman`, confirmed the underlying `miller_loop` primitive needed to hand-port it already does, confirmed the `zcash-scriptch` idle-thread angle is a queue-wiring gap not a proof-system limitation. Scoping only, no implementation (item 4 above).
- §7: memory profiling via `vmmap`/`heap`/`malloc_history` (CLI-native, unblocking the Instruments GUI-only-export dead end) — found footprint grows with chain length (no leak signature), `AddToBlockIndex`'s permanent block-index map is the single largest allocation site (~66% of tracked `ThreadImport` allocation in the sampled window), and confirmed Sapling Groth16 verification allocates essentially zero heap despite dominating CPU. Full-chain timeline still in progress (item 1 above).

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

Difference: -1.66%, t ≈ -1.07 — not distinguishable from noise at this sample size (would need |t| > ~2.5–2.6 for significance with n=4 each). This establishes the noise floor this methodology resolves at a 300,000-block window: ~1.5–3% CV per condition. Consistent with average block size (~1.3–2KB) being far smaller than either buffer setting.

**Re-measured at post-Sapling heights, with a true no-fdcache baseline added (§0 item 1).** The original A/B above never tested `-perffdcache` against a real off condition (every trial had `-perffdcache=1`), and only covered pre-Sapling heights. `bench_matrix.sh` was extended with a third `nofdcache` condition (`-reindex` with neither flag — the fd-cache code path entirely inactive) and re-run at warmup=600,000→measured 600,000–900,000 (entirely post-Sapling; activation is 492,850), 4 trials per condition, 3 conditions:

| Condition | n | Mean blk/s | Stdev | CV |
|---|---|---|---|---|
| No fd-cache | 4 | 307.22 | 5.615 | 1.83% |
| Default buffer (fdcache on) | 4 | 310.56 | 0.261 | 0.08% |
| 1MB buffer (fdcache on) | 4 | 309.28 | 0.000 | 0.00% |

`ReadFdCache` log lines confirm the mechanism itself is engaging correctly at these heights: `nofdcache` trials show `opens=0 hits=0` throughout (code path genuinely inactive, not just untuned), while both fdcache-on conditions show **99.9% hit rate** — identical to the pre-Sapling hit rate found earlier, confirming §3's single-slot-latch design holds at post-Sapling heights and shielded-tx volumes too.

**Result: still no measurable throughput win, now with the isolation this item set out to get.**
- **fd-cache on vs. off** (no-fdcache → default-buffer): +1.09%, t ≈ 1.19 — not distinguishable from noise (same |t| > ~2.5–2.6 bar as before).
- **Buffer size, fd-cache held on** (default-buffer → 1MB-buffer): −0.41%, t ≈ −9.80 — a real, statistically clear *difference*, but in the wrong direction (1MB buffer is *slower*) and tiny in absolute terms (1.3 blk/s); most plausibly page-cache/allocation overhead from a 1MB `setvbuf` buffer per open handle outweighing any I/O-batching benefit at these small (~1.3–2KB) block sizes, not a real optimization opportunity.
- **Combined** (no-fdcache → 1MB-buffer): +0.67%, t ≈ 0.73 — not distinguishable from noise.

This closes §0 item 1's open question: post-Sapling heights behave the same as pre-Sapling did — the fd-cache mechanism works exactly as designed (99.9% hit rate, confirmed genuinely inactive in the off condition) but produces no measurable reindex throughput improvement, isolated from buffer size, at either pre- or post-Sapling heights. Disk I/O's remaining headroom (§2: ~25–26% of CPU post-Sapling) is dominated by genuine read/write/transfer time, not open/close overhead — consistent with §3's earlier `fs_usage` finding that open/close/stat together were only 6–34% of the disk-I/O bucket.

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

**Latch vs. cache — checked against Zebra directly, not assumed.** Zebra's own Sprout tree type uses the identical single-slot latch pattern (`cached_root: RwLock<Option<Root>>`, cleared on `append()`), confirming a keyed cache isn't the standard answer here either. The real difference: Zebra's Sapling/Orchard anchor validation never constructs a tree object during validation at all — it checks anchor membership against a `HashSet`/RocksDB key-existence check, populated once at commit time — a *different technique* (a membership index over previously-seen roots), not a bigger cache. Zebra's Sprout path still pays the same construct/append/read cost for **chained joinsplits within one transaction** as Zero does, by its own source's admission ("this check is expensive, because it updates a note commitment tree for each sprout JoinSplit"). **So a keyed/multi-entry cache would not have helped `HaveShieldedRequirements` either** — the actual problem isn't insufficient memoization, since Zebra hits the identical wall despite a mature, independent implementation. The membership-index technique is the concrete lead for further work, not a bigger latch.

**Implemented: the membership-index technique (§0 item 3).** `CCoinsView`'s existing `GetSproutAnchorAt`/`GetSaplingAnchorAt` (`coins.h`/`coins.cpp`/`txdb.cpp`) always deserialize the full stored tree, even when the caller only needs to know the anchor is valid. But at the DB layer (`CCoinsViewDB`, `txdb.cpp`), the LevelDB key is already the root itself (`make_pair(DB_SPROUT_ANCHOR, rt)`/`make_pair(DB_SAPLING_ANCHOR, rt)`) — a pure existence check (`db.Exists`) was already possible at that layer without a schema change, just not exposed. Added `HaveSproutAnchorAt`/`HaveSaplingAnchorAt` as new virtual methods through the same chain (`CCoinsView` → `CCoinsViewBacked` → `CCoinsViewCache` → `CCoinsViewDB`), existence-only at every layer: `CCoinsViewCache`'s variant checks its own in-memory anchor cache first (reusing an already-fetched entry without touching the base view again) and otherwise defers to base *without* populating the tree cache — a later `GetSproutAnchorAt`/`GetSaplingAnchorAt` call still works correctly, it just pays its own DB read at that point, same as before this change.

`HaveShieldedRequirements` (`coins.cpp`) now uses these where the tree object was never actually used afterward:
- **Sapling spends**: the tree fetched via `GetSaplingAnchorAt` was never read again after the existence check — switched unconditionally to `HaveSaplingAnchorAt`. Sapling spends never chain (§4's finding: they never call `.append()`/`.root()` in this function), so this is always safe.
- **Sprout joinsplits**: chaining (a later joinsplit's anchor matching an earlier one's output root, via the `intermediates` map) is only *possible* when a transaction has more than one joinsplit. Added a `mayChain = tx.vJoinSplit.size() > 1` guard: single-joinsplit transactions (structurally unable to consume an `intermediates` entry) use `HaveSproutAnchorAt` and skip tree reconstruction/`intermediates` bookkeeping entirely; multi-joinsplit transactions fall through to the original tree-reconstruction path unchanged, preserving exact existing behavior for the one case that needs it.

**Validation.** `test/coins_tests.cpp`'s `chained_joinsplits` case (2–4 joinsplits per transaction, every ordering/chaining combination) exercises exactly the `mayChain = true` path and passes unmodified — the multi-joinsplit path is byte-for-byte the pre-existing code. Four other `CCoinsView`-subclassing test doubles (`test/coins_tests.cpp`'s `CCoinsViewTest`, `zcbenchmarks.cpp`/`gtest/test_validation.cpp`/`gtest/test_mempool.cpp`/`gtest/test_transaction_builder.cpp`'s `FakeCoinsViewDB`/`TransactionBuilderCoinsViewDB`) each override `GetSproutAnchorAt`/`GetSaplingAnchorAt` directly but hadn't overridden the new `Have*AnchorAt` methods — without a fix they'd silently inherit the `CCoinsView` base class's `return false`, breaking every existence check against them. Added matching `Have*AnchorAt` overrides to all four, mirroring each one's existing `Get*AnchorAt` logic (membership check against the same backing map/condition, no tree deserialization). Full regression: Boost `test_bitcoin` 284/284 clean; `zero-gtest` 205/207, with the 2 failures (`WalletTests.ClearNoteWitnessCache`, intermittently `wallet_zkeys_tests.WriteCryptedSaplingZkeyDirectToDb`) reproduced identically against the unmodified baseline (same failures, same pass-in-isolation behavior) — confirmed pre-existing test-order-dependent flakiness in wallet-test global state, not a regression, and consistent with §4's own already-documented "pre-existing unrelated wallet-key test flake" note.

**Not yet measured for CPU-bucket impact.** Implemented and regression-tested, but not yet re-profiled with Instruments to quantify the effect on the tree/anchor bucket (~6–14% of CPU per §2) — the Sprout-joinsplit share of that bucket should shrink for single-joinsplit transactions (the common case per §4's per-block table: idle/Sapling-only blocks already had cheap, near-empty trees, so the volume this targets is specifically Sprout-joinsplit-bearing blocks), but by how much hasn't been measured.

---

## 5. Equihash's CPU share: a libsodium/ARM gap, not an algorithm issue

**The question.** §2 showed Equihash verification taking 6–28% of CPU depending on height, with `blake2b_compress_ref` recurring in every sample. Given Equihash verification is supposed to be cheap by design (asymmetric proof-of-work), is this a real inefficiency? **Answer: the algorithm is correct and minimal; the cost is a missing SIMD backend, specific to this build's architecture.**

**The algorithm itself is correct and lightweight.** `Equihash<N,K>::IsValidSolution` does exactly what the spec requires for mainnet's `Equihash<192,7>`: `2^K = 128` calls to `GenerateHash` (one blake2b invocation each), followed by a 7-round collision/ordering/distinctness check using only `memcmp`/XOR-style comparisons — no re-solving, no search, no redundant hashing. There is no algorithmic bug here.

**The cost is entirely inside blake2b's compression function, running unaccelerated on this hardware.** Every one of the 128 per-block hash calls goes through libsodium (not the Rust `blake2-rfc` crate also vendored in this tree — that's for something else). libsodium 1.0.21 dispatches its blake2b compression function at runtime via `blake2b_pick_best_implementation()`, choosing between `avx2`/`sse41`/`ssse3`/`ref` backends — but **all three accelerated backends are gated behind x86-only intrinsics headers**. On `aarch64-apple-darwin` (Apple Silicon), none of those headers exist, so the dispatcher unconditionally falls through to `blake2b_compress_ref`, the plain scalar C implementation, for every call.

**Checked and ruled out: no fix via upgrading dependencies or Apple's native crypto.** libsodium has released twice since 1.0.21 (1.0.22, 2026-04-09, current) — its actual `ChangeLog` shows post-quantum KEMs and new SHA-3 APIs, no mention of blake2b/NEON/ARM anywhere. Across every release checked (1.0.18–1.0.22), ARM/aarch64 wins landed for AES-GCM, AEGIS, and Argon2/SHA3 — blake2b has never once been included; a version bump is confirmed not to fix this. Apple's CryptoKit has no BLAKE2b support at all (SHA-2/AES/legacy only).

**A real, actively-maintained implementation to integrate from, if pursued.** The official reference repo `BLAKE2/BLAKE2` ships a `neon/` directory with `blake2b-neon.c` implementing BLAKE2b via ARM NEON/ASIMD intrinsics, plus a dedicated `Aarch64` makefile — and its most recent commit (2023) was a correctness fix by `veorq`, one of the two original BLAKE2 authors. Not stale or abandoned code. Integration would mean vendoring this implementation and wiring it in as a replacement compress function for this call path (either patched into the vendored libsodium build, or called directly from `equihash.cpp`, bypassing libsodium's generichash API for this one use site). Not yet scoped past confirming the file exists and targets the right architecture — actual integration effort (API fit, licensing, correctness validation against known-answer vectors) hasn't been assessed (§0 item 1).

**Independent confirmation this is a fixed, hardware-level cost, not something content-dependent:** Equihash's per-block cost held constant at 0.252ms ± 1.2% CV across six capture windows spanning pre- and post-Sapling heights and blocks/sec ranging 237–1,103 (§2's per-block table) — versus 21–46% CV for every other bucket, all of which scale with shielded-tx volume or block size. A cost that doesn't move with any chain-content variable is exactly what "fixed per-header hashing cost, paid by an unaccelerated compression function" predicts.

---

## 6. Sapling Groth16 batch-verification headroom: scoped, not implemented

**The question (§0 item 4).** §2 found Sapling Groth16 proof verification dominating post-Sapling CPU (48–55% chain-wide). Does `bellman` (Zero's pinned `librustzcash` Groth16 implementation) support batch verification, and could that work run on the currently-idle `zcash-scriptch` threads?

**Confirmed: every proof is verified independently, on one thread, with no batching anywhere in the call chain.** `bellman::groth16::verifier::verify_proof` (`bellman/src/groth16/verifier.rs`, pinned via `librustzcash` commit `06da3b9ac8f278e5d4ae13088cf0a4c03d2c13f5`, fetched fresh from upstream since the depends cache only stores the built `.a`/`.h`, not source) takes exactly one `Proof`/one set of public inputs and does one 3-pairing Miller loop + one final exponentiation — no loop, no batch parameter, no alternate entry point. `librustzcash_sapling_check_spend`/`_check_output` (`librustzcash/src/rustzcash.rs`) each wrap a single `verify_proof` call and are invoked once per `SpendDescription`/`OutputDescription`, from `ContextualCheckTransaction` (`main.cpp`), which `ContextualCheckBlock` calls via a plain `BOOST_FOREACH` over `block.vtx` — sequential, single-threaded, on the same worker thread that does everything else during reindex (`zcash-loadblk`). This confirmed the "structural, not fundamental" framing from §0: `ContextualCheckInputs`' `CScriptCheck`/`scriptcheckqueue` dispatch (the thing that actually wakes `zcash-scriptch` threads) covers *only* transparent script/signature verification and is wired up entirely separately from, and after, `ContextualCheckBlock`'s Groth16 checks — the two paths never share a queue, so idle `zcash-scriptch` threads structurally cannot pick up Groth16 work without new wiring, not because of any inherent limitation in the proof system.

**Confirmed: real batch-verification support exists, but only in a materially newer `bellman`.** The maintained successor `zkcrypto/bellman` (the pinned `ebfull/bellman` is ~2019-vintage; `zkcrypto/bellman` is its modern continuation) ships `groth16/src/verifier/batch.rs` plus a `groth16/benches/batch.rs` benchmark — a real, tested feature, not a proposal. It implements the standard random-linear-combination technique: for N proofs sharing one `VerifyingKey`, draw a random scalar `z_i` per proof, fold each proof's `(A, B, C)` terms and public inputs into running accumulators weighted by `z_i`, then do **one multi-Miller-loop + one final exponentiation for the whole batch** instead of N independent ones — collapsing the batch's expensive final-exponentiation count from O(N) to O(1). A `verify_multicore` variant additionally shards the batch into `rayon` `par_chunks(8)` work-items, run over `rayon`'s global threadpool, then reduces the partial Miller-loop results — real, existing parallel-execution code, not something to build from scratch.

**But this is not a drop-in upgrade.** Modern `bellman`'s `groth16` crate requires `edition = "2021"`, `rust-version = "1.60"`, and depends on `ff 0.13`/`group 0.13`/`pairing 0.23`/`bls12_381 0.8` — all from the post-2020 `ff`/`group` trait-split redesign of the Rust pairing-crypto ecosystem. The pinned crate stack (`pairing 0.14.2`, path-dependency, `rand 0.4`, no `ff`/`group` split at all) predates that redesign entirely. Adopting `zkcrypto/bellman`'s `batch.rs` as-is would mean migrating Zero's entire `librustzcash`/`bellman`/`pairing`/`jubjub` stack across that ecosystem-wide API break — a large, separate undertaking, not a small patch.

**The good news: the core primitive the algorithm needs already exists in the pinned crate, so a hand-ported batch verifier is feasible without that migration.** The pinned `pairing::Engine` trait (`pairing/src/lib.rs`) already defines `miller_loop<I>(i: I) -> Fqk` accepting an arbitrary-length iterator of `(G1Affine::Prepared, G2Affine::Prepared)` pairs — `verify_proof` itself already calls it with 3 pairs per single-proof check. `CurveAffine::prepare()`/`::Prepared` are likewise already present. This means the random-linear-combination batching math (accumulate weighted terms across N proofs, feed them all into one `miller_loop` call, one `final_exponentiation`) can be hand-ported into the pinned `bellman`/`pairing` version without a crate upgrade — the trait shapes line up. What pinned `bellman` lacks and would need adding: the accumulator/random-scalar bookkeeping itself (straightforward to port from `batch.rs`'s logic), and — for the multicore variant specifically — a parallel-execution primitive, since `rayon` isn't in the pinned crate's dependencies (`futures-cpupool`/`crossbeam`/`num_cpus` are present but used only by the *prover*, e.g. FFT/multi-exponentiation in `prover.rs`, never the verifier).

**What this changes for a real implementation, beyond the crypto:**
- **Batching requires buffering proofs before verifying them**, which doesn't fit `ContextualCheckTransaction`'s current per-transaction, immediate-verify-or-reject control flow (`ContextualCheckBlock`'s `BOOST_FOREACH` calls it once per tx and expects an immediate pass/fail). A batched version would need to collect all of a block's Sapling spend/output proofs first, verify the batch once, and only then be able to say a proof failed — with the caveat noted in `zkcrypto`'s own doc-comment: batch verification confirms *all* proofs are valid but "loses the ability to easily pinpoint failing proofs," so a failed batch needs a fallback to per-proof `verify_single` to identify which transaction to reject (already provided for exactly this purpose by `Item::verify_single` in `batch.rs`).
- **The random verifier scalars need a CSPRNG**, sourced per block (or per batch) — a new input this call path doesn't currently have.
- **Consensus-criticality**: unlike §3/§4's fixes (pure memoization, no change to what's computed), swapping single-proof verification for batch verification changes the exact sequence of cryptographic operations performed to reach a pass/fail — this needs the same scrutiny consensus-code changes always require, even though the math is a standard, published technique (not novel here).

**Not started, deliberately scoped no further than this.** Per §0 item 4, this was a research/scoping task, not an implementation. Estimated headroom: collapsing N final-exponentiations to 1 per batch, against a bucket that's 48–55% of chain-wide CPU (§2), is a substantial, structurally-supported target — but realizing it requires (a) hand-porting the batch algorithm using the pinned crate's existing `miller_loop` primitive, (b) restructuring `ContextualCheckBlock`'s per-tx control flow to buffer-then-batch-verify, and (c) deciding whether to also port a parallel accumulation path (would need vendoring a `rayon`-equivalent, or reusing the existing `futures-cpupool`/`crossbeam` machinery `prover.rs` already depends on) to actually engage otherwise-idle cores. None of this is started.

---

## 7. Memory profiling: `AddToBlockIndex` dominates, Groth16 verification allocates nothing

**The question (§0's memory-profiling item).** Instruments' Allocations/Leaks templates attach successfully but produce a GUI-only proprietary blob with no `xctrace export` schema in this Instruments version (§2) — a documented dead end for headless use. `vmmap`/`heap`/`malloc_history` are CLI-native with no export-format dependency; this section is their first real use against a live `-reindex`.

**Method.** `vmmap -summary <pid>` gives `Physical footprint` at a point in time — used here to build a footprint-vs-height timeline via a small driver (`reindex-profile/memprofile/snapshot_at_heights.sh`) that polls `getblockcount` and snapshots at fixed height checkpoints. `heap <pid>` gives a live per-size-class allocation census, no special launch flags needed. `malloc_history <pid> -callTree` gives a full allocation-site call tree attributing every live allocation to the code path that made it — but only for allocations made *after* `MallocStackLogging=1` is set, so this needed a separate `-reindex` launched with that environment variable (real, non-trivial overhead: stack-logging is not something to leave on for a full multi-hour chain reindex, so this run was capped at a representative window rather than run to chain tip).

**Footprint grows with chain length, roughly linearly, not unboundedly — no leak signature found.** Three checkpoints so far on the full-chain sweep: 535.3MB at height 278,072, 956.1MB at height 500,436 (spans Sapling activation at 492,850), 1,638.4MB at height 901,000. Growth rate holds essentially steady across the Sapling activation boundary — **1.94KB/block** for 278K→500K (pre/early-Sapling) vs. **1.74KB/block** for 500K→901K (entirely post-Sapling) — consistent with the dominant cost (`AddToBlockIndex`, below) being a roughly constant per-block-header cost, not something that scales with shielded-tx volume the way §2's CPU buckets do. This is consistent with §0's next-step framing (was there unbounded growth?) resolving to "no": the growth tracks `AddToBlockIndex` building a permanent, one-entry-per-block-header in-memory index (see below), which is expected, bounded-per-block, and doesn't compact or evict, not a leak. (Chain-length-proportional growth is real and worth knowing operator-side — a fully-synced node's block-index memory floor scales with chain height, projecting to roughly 4–5GB at full chain tip (~2.47M blocks) if the rate holds — but that's a capacity-planning fact, not a defect.)

**Allocation-site breakdown (`malloc_history -callTree`, 673-second stack-logged window spanning roughly height 20,198 → 501,321, i.e. crossing Sapling activation):** ~987MB total tracked allocation across the window, essentially all of it (896MB, >90%) under the single `ThreadImport` worker thread, confirming again (as in §1's profiling methodology) that this is where real work happens. Within that:

| Call path | Allocation | Share of `ThreadImport` |
|---|---|---|
| `AddToBlockIndex` (building the permanent `uint256`→`CBlockIndex*` block-index map + per-header metadata) | ~589MB | ~66% |
| `CCoinsViewCache::Flush`/`BatchWrite` (flushing coins/anchor/nullifier caches to the LevelDB-backed chainstate) | ~160MB+ (multiple call sites) | ~18%+ |
| `CCoinsViewCache::HaveShieldedRequirements` → `GetNullifier` (nullifier-set cache insertion) | ~37MB (main pass) + ~4.8MB (reprocessing pass) | ~4% |
| `CCoinsViewCache::HaveInputs`/`FetchCoins`/`GetCoins` (transparent UTXO cache population) | ~29.8MB + ~9.5MB | ~4% |

**`AddToBlockIndex` is the single largest identifiable allocation site — expected, not a bug.** It permanently retains one `CBlockIndex` object (plus a `vector<unsigned char>` for header-adjacent data and a hash-map entry) per block header for the lifetime of the process — by construction, chain-length-proportional, never freed, never meant to be. At ~589MB for roughly 480,000 headers in this window, that's on the order of ~1.2KB/header of permanent retained memory — consistent with `CBlockIndex`'s field set (hashes, work, heights, pointers) plus map/allocator overhead. Confirms this is the primary driver of the footprint-vs-height growth measured above, not a separate or surprising cost.

**Confirmed: Sapling Groth16 proof verification allocates essentially nothing on the heap.** Despite dominating CPU (48–55% of chain-wide CPU per §2) and this stack-logging window spanning well past Sapling activation, `librustzcash_sapling_check_spend`/`_check_output`/`verify_proof`/`miller_loop`/`final_exponentiation` appear **zero times** anywhere in the call tree. The only Groth16-adjacent allocation found at all is `librustzcash_init_zksnark_params` (~58MB, ~4.9MB, and a handful of smaller frames) — one-time proving/verifying-key loading at process startup, not a per-verification or per-block cost. This cleanly decouples §2's CPU-dominant bucket from the memory profile: BLS12-381 field/pairing arithmetic operates on fixed-size stack types, so verifying more proofs costs CPU time but not heap growth — a useful confirmation that Groth16 verification (and by extension, any future batch-verification work per §6) is not a memory-scaling concern, only a CPU one.

**Not yet complete: the full-chain footprint timeline.** The height-checkpoint sweep (100K/500K/900K/1.5M/2M/2.47M-final checkpoints) was still running as of this writing, past the 500,436 datapoint above — later checkpoints, particularly past height 900,000 where Groth16/tree-anchor volume is heavier (§2's captures 2–6), would confirm whether the ~1.9KB/block rate holds steady or scales with shielded-tx density the way CPU cost does (§2's per-block table). Not yet re-run under `MallocStackLogging` at post-Sapling-heavy heights specifically — the stack-logged window above happens to straddle the Sapling activation boundary but is dominated by pre-activation volume by block count, so its allocation-site percentages likely understate Sapling-Groth16-adjacent bookkeeping (anchor cache writes, nullifier-set growth) relative to a window sampled entirely post-activation.
