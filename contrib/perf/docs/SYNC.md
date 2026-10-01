# Block validation and import

Where `zerod` spends time connecting blocks during `-reindex`, `-loadblock`
bootstrap and network sync, the changes made to that path, and what remains.
Wallet-on cost is `WITNESS.md`; shielded proof verification cost and its
batching decision are `PerfGroth.md`. Work items are `PLAN.md` group K.

All figures are macOS/arm64, one host, profiled on the `zcash-loadblk` thread
(`ThreadImport`). Figures are bound to `M-*` ids in `Measures.md`.

---

## 1. Where the time goes

Validation is serial on one thread and CPU-bound: one core at 100%, disk
syscalls under 5% of samples. `-par` script-check workers do not touch any of
the costs below; they verify transparent signatures only.

**Height region decides the mix; operation type does not.** Reindex,
bootstrap and sync agree within ~3 points on every bucket at the same heights
-- they differ in how blocks are sourced, not in what validation costs. A
figure without a height window is not comparable to anything. Sapling
activates at height 492,850.

| Region | Throughput | Dominant cost | Id |
|--------|-----------|---------------|----|
| pre-Sapling, ~h50k-75k | ~1,018-1,027 blk/s (n=11) | tree/anchor, Equihash | M-RX-PRESAP |
| Sapling onset, h490k-520k | 130-140 blk/s (n=2) | proof verification | M-RX-ONSET |
| post-Sapling, h600k-900k | 298.45 blk/s reindex, 300.15 bootstrap (n=4 each) | proof verification 48-55% | M-RX-POSTSAP-STOCK, M-BOOT-POSTSAP |
| whole chain, bootstrap | ~282 blk/s; 2,468,990 blocks in 145.7 min | -- | M-BOOT-FULL |

Same-host repeatability is 4% (178.0 s vs 171.0 s, unchanged binary): the
noise floor any claimed improvement must clear. Insight indexes
(`-insightexplorer`) cost ~9% on a tiny reindex and widen the spread from ~1%
to ~4.5% (M-RX-TINY-20260930); a comparison must hold them constant. Within one tiny reindex the
rate varies 28% across height bands (M-LAB-BAND-TINY), so an endpoint rate
hides structure.

**Per-block cost, six captures across the chain** (M-CPU-SEQ):

| Capture | Heights | blk/s | Proof verify ms | Disk I/O ms | Tree/anchor ms | Equihash ms |
|---|---|--:|--:|--:|--:|--:|
| 1 | 5,373-336,144 | 1,102.6 | -- | 0.149 | 0.494 | 0.2557 |
| 2 | 626,078-702,200 | 253.7 | 2.149 | 0.983 | 0.543 | 0.2513 |
| 3 | 995,392-1,083,180 | 292.6 | 1.788 | 0.888 | 0.463 | 0.2493 |
| 4 | 1,411,397-1,482,630 | 237.4 | 2.324 | 1.050 | 0.587 | 0.2476 |
| 5 | 1,693,202-1,777,052 | 279.5 | 1.921 | 0.893 | 0.500 | 0.2541 |
| 6 | 2,032,619-2,173,838 | 470.7 | 1.005 | 0.543 | 0.288 | 0.2530 |
| **mean / CV** | | | 1.84 / 27.7% | 0.75 / 45.7% | 0.48 / 21.5% | **0.252 / 1.2%** |

Proof verification, disk and tree cost scale with shielded volume and block
size. Equihash is a fixed per-header cost. These captures predate uniblake and
the redundant-verification skip; Equihash is now ~45 us/block ("Equihash verifications per block" below).

**What does not show in `-debug=bench`.** Proof verification runs in
`CheckBlock` and `ContextualCheckBlock`, before and outside the `nTime*`
timers, so a phase summary from today's counters omits 88-91% of post-Sapling
cost while appearing complete. `nTimeVerify` also includes `nTimeConnect`.
Spec: `PerfTimers.md`; work item `PLAN.md` P1.

---

## 2. Equihash verification

`Equihash<192,7>::IsValidSolution` is minimal: 128 BLAKE2b calls and a
7-round comparison check. Its cost was the BLAKE2b compression function, which
libsodium 1.0.21 and 1.0.22 run as scalar C on aarch64 (the SIMD backends are
x86-only; the two versions are byte-identical for BLAKE2b).

**Closed:** `equihash.cpp` calls uniblake through `crypto/eh_hashstate.h`
since `c9bbe6ad9`, measured 2.03x on the Equihash access pattern against
libsodium 1.0.22 at -O3. The gain is prefix-state reuse, not vectorisation;
bulk throughput of the two libraries is within 1-2%. Library division:
`HASHLIBS.md`.

### Equihash verifications per block

Before `37f3f3459`, `CheckBlock` ran 3.00 times per block during reindex
(562,254 calls over 187,418 blocks, `test-logs/lockstats-20260912/`), and each
call re-verified the Equihash solution. That commit skips the PoW branch of
`CheckBlockHeader` in `AcceptBlock` and `ConnectBlock` when the index entry
is already at `BLOCK_VALID_TREE`, which `AcceptBlockHeader` reaches only after
verifying the header. A Zcash-family block hash covers `nSolution`, so the
index entry pins the verified header. The merkle check is untouched: it is the
CVE-2012-2459 duplicate-transaction guard, and its input is the transaction
list, not the header.

**Measured after the change** (M-EQ-VERIFY-SITES, `ZERO_PERF` per-caller
counters):

| Caller | Calls per block | us per call |
|--------|----------------:|------------:|
| `ProcessNewBlock` preliminary `CheckBlock` | 1.00 | 23.5 |
| `AcceptBlockHeader` | 1.00 | 21.6 |
| `AcceptBlock`, `ConnectBlock` | 0 | -- |
| `ReadBlockFromDisk` | 0 during reindex -- the block is passed to `ConnectTip` in memory | -- |

Equihash is now ~45 us/block, ~7% of a tiny-window reindex (M-RX-TINYWIN).
The two remaining calls verify the same header. Removing one would save
~22 us/block -- ~3.5% of a tiny window, under 1% post-Sapling -- and needs a
cached checked bit on the block object, the pattern behind zcashd's `fChecked`
CVE-2026-35679. Not proposed.

**Validation still missing** for the skip: a test that corrupts the Equihash
solution between `AcceptBlock` and `ConnectBlock`, and a `getblock` RPC
concurrent with reindex (an `nStatus` read racing its write). Existing
coverage: `invalidblockrequest.py`, `reorg_limit.py`, `mempool_reorg.py`.

---

## 3. Disk I/O and FDCACHE

`OpenDiskFile` does an unconditional `fopen` per call and `CAutoFile` closes
it on return, so a full reindex performs 2.5-5M open/close pairs on ~128 MB
files it just closed. Open, close and stat together are 0.048 ms/block (M-CPU-FS), 6-34%
of the disk bucket (`fs_usage`); the rest is transfer.

**FDCACHE** (`#ifdef ZERO_FDCACHE`, compiled out of release builds): `-perffdcache=1`
keeps one read handle per file kind (`BLK`, `REV`) in a single-slot latch,
99.9% hit rate from genesis to h900k; `-perfbufsize=N` sets a `setvbuf` size.

**Result: no throughput gain** (M-CPU-FD-THR), reindex h600k-900k, n=4:

| Condition | Mean blk/s | CV |
|---|--:|--:|
| No fd-cache | 307.22 | 1.83% |
| fd-cache, default buffer | 310.56 | 0.08% |
| fd-cache, 1 MB buffer | 309.28 | 0.00% |

On vs off +1.09%, t ~ 1.19, inside noise. The same null holds pre-Sapling. The
ceiling explains it: disk syscalls are 4.91% of samples, and halving syscalls
per read recovers at most ~2.5% -- below the 4% repeatability floor. Reads
are sequential in height order, which OS readahead already covers.

**Unmeasured cases where it could pay**, both latency rather than throughput
questions: random `getblock`/explorer serving (consecutive reads hit
different files; measure RPC latency percentiles), and cold cache or slow
storage (Linux `drop_caches`, `PLAN.md` group F).

**Defects if it resumes** (`PLAN.md` P8, postponed):

- `CacheOpen` (`main.cpp:4924`) releases the latch lock at return and callers
  read the shared `FILE*` unlocked (`:2130`, `:2617`). Safe for single-reader
  reindex only; a multi-reader measurement needs an RAII lease or `pread`
  first.
- `--enable-perf` couples safe counters with the FDCACHE behaviour change;
  split them so counters build without the experiment. Worth doing even if
  FDCACHE is dropped.
- The FDCACHE probe reportedly always returns false, and the flags are absent
  from `HelpMessage`.
- No gtest for latch hit/miss/stale-reopen.
- Buffer sweep, if resumed: add 8192 and 16384 against the libc default and
  1 MB (1 MB measured slightly slower).

Close it -- delete the flag, the latch and `bench_matrix.sh`'s FDCACHE
conditions -- on a null from Linux and Windows.

---

## 4. Trees and anchors

**Merkle-root latch, shipped.** `IncrementalMerkleTree::root()` recomputed on
every call and `ConnectBlock` calls it twice per block. A `cached_root` latch,
cleared on `append()` and deserialize, removes that; `merkletree.RootCacheConsistency`
covers it. Measured effect on the tree bucket: none (57.9% vs 58.0%). The
redundancy was real but cheap: idle and Sapling-output blocks matched 80-100%,
while Sprout JoinSplit blocks matched 36-48%, because
`HaveShieldedRequirements` builds a fresh tree per JoinSplit that no
per-object latch can serve. Zebra has the same Sprout cost.

**Anchor membership index, removed.** Existence-only `Have*AnchorAt` checks
wired into `HaveShieldedRequirements` broke mempool acceptance: ATMP checks,
switches to a dummy backend, and checks again, relying on `Get*AnchorAt`
having warmed the cache. Guard: `coins_tests/shielded_survive_dummy`. Revisit
only with a non-ATMP caller and a measured win.

Remaining tree cost is new `append()` work proportional to shielded outputs,
6-14% of CPU post-Sapling (M-CPU-SEQ).

---

## 5. Memory

Footprint grows linearly with chain length, 1-3 KB/block of written address
space, with no leak signature (M-MEM-VMMAP, M-MEM-GROWTH). Read
`Writable regions: Total` from `vmmap`, not `Physical footprint`: the latter
nets out macOS compression, which varied 0-71% over the run and produces a
spurious declining-growth trend.

| Height | Physical footprint | Writable total |
|---|--:|--:|
| 278,072 | 535 MB | 702 MB |
| 901,000 | 1.6 GB | 1.7 GB |
| 2,470,587 | 3.1 GB | 4.7 GB |

**Allocation sites** (M-MEM-ALLOC, `malloc_history` over h20k-501k): over 90%
under `ThreadImport`; `AddToBlockIndex` ~66%, coins-cache flush ~18%,
nullifier and UTXO cache ~4% each. Proof verification allocates nothing on the
heap; the only Groth16-related allocation is one-time parameter loading at
startup (~63 MB, M-MEM-PARAMS).

**`AddToBlockIndex`, per block:** four allocations, ~904 bytes, ~856
permanently retained -- the `CBlockIndex` (344 B), its Equihash solution
vector (448 B), the `mapBlockIndex` node (64 B) -- plus a 48 B
`setDirtyBlockIndex` node freed at flush. This is the chain-length growth.

**Shielded-index fields in `CBlockIndex`** (M-MEM-SHIELDEX). Eleven per-block
counters and eleven `nChain*` sums feed the `-zindex` statistics RPC. Population
and disk serialisation are gated on `fZindex` (default off); the struct layout
is not, so every node carries ~176 B/block of zeros, ~435 MB at tip.
`nNotarizations` can only ever be 0 -- its increment is commented out
(`main.cpp:4044-4049`) -- yet it is summed, serialised under `-zindex`, and
reported by RPC. Items: `PLAN.md` K1, K2.

---

## 6. Shipped changes

| Change | Effect |
|--------|--------|
| Equihash BLAKE2b via uniblake | 2.03x on the Equihash hash pattern |
| Skip re-verifying a header already at `BLOCK_VALID_TREE` (`37f3f3459`) | Equihash verifications during reindex down to 2.00 per block (M-EQ-VERIFY-SITES) |
| Merkle-root latch | Correct; no measurable throughput change |
| `CBlockIndexWorkComparator` single `CompareTo` | 14.7% off block-index load, 2.5M-block datadir |
| `IsInitialBlockDownload` hoist | Removes a `cs_main`-under-`cs_main` pair per call during sync (`LOCKS.md`) |
| `LoadBlockIndexDB` and `ThreadImport` honour shutdown | A multi-million-block index load can be stopped by SIGTERM |
| FDCACHE | Compiled out; see section 3 |

Out-of-order children on reindex were checked and need no change: 133,955
blocks stashed, 133,524 reparented, each once, because
`mapBlocksUnknownParent` erases what it visits (`test-logs/p17-outoforder-20260922/`).
