# Findings

What is known, **most recent first**. The newest work is at the top because it
is what current decisions rest on; older results are still true and still
cited, but they are settled and need less of a reader's attention.

Figures cite an `M-*` id in `../Measures.md`, which owns them; provenance for
recent work is `test-logs/DATA_INDEX.md`.

**Groth16 is not covered here.** It is the single largest topic and has its own
focused document: **`../PerfGroth.md`**. This file cites its conclusions and
does not restate its evidence.

**Platform caveat, applies to everything below.** Every measurement in this
document was taken on **macOS / arm64** on one host. Relative CPU shares should
transfer, since they are dominated by userspace arithmetic; absolute throughput
and anything touching disk should not be assumed to.

---

## 1. Current: what the latest work established

### 1.1 Instrumentation is measuring the wrong thing

Reading the block-processing timers end to end found three defects, in
descending order of consequence. Full analysis: `../PerfTimers.md`.

**Proof verification is inside no timer at all.** Sprout JoinSplit verification
runs in `CheckBlock` (`main.cpp:2982`), 67 lines *before* the first timer
`nTimeStart` (`3049`). Sapling spend/output verification runs in
`ContextualCheckBlock` during block *acceptance*, outside `ConnectTip`
entirely. So Groth16 verification -- the largest post-Sapling cost -- is
invisible to `-debug=bench`.

**Consequence for upcoming work:** a phase summary built from today's counters
would omit 88-91% of post-Sapling cost *while appearing complete*. Adding a
proof counter is therefore a prerequisite for the summary, not an enhancement
of it -- `TASKS.md` B1.

**`nTimeConnect` and `nTimeVerify` overlap.** Both measure from `nTimeStart`, so
verify *includes* connect and summing them double-counts. Inherited from
upstream; the labels do not say so. Any consumer must report
`verify_excl = nTimeVerify - nTimeConnect` or mark the field cumulative.

**The timers run but are discarded.** `GetTimeMicros()` and every `nTime*`
accumulator execute on every block regardless of logging; only the `LogPrint`
output is gated. Every field node already measures where its time goes and
throws it away.

### 1.2 Results were not recordable across platforms or builds

Neither ledger had any field for OS, architecture, binary version or feature
set. Every existing row came from one macOS/arm64 host and nothing said so, so
the first Linux row would have been silently averaged into the same means.

Two further gaps: `binary` recorded a filesystem path rather than a version,
and nothing captured that a build was **dirty** -- so no existing measurement
can be tied to a commit.

Design and current state: **`SCHEMA.md`**. Remaining work and its exit
condition: `TASKS.md` A2.

### 1.3 Two rules were unenforced, and both had drifted

The ASCII-only rule (693 violations, 498 in `Perf.md`) and the "numbers live in
`Measures.md` under an `M-*` id" rule (the Groth16 share restated in five
documents). Both are written down; neither is checked. Pattern and fix:
`POLICY.md` S2.1, `TASKS.md` A1.

### 1.4 Direction this points

1. **Instrument the proof path before building any summary** (B1).
2. **Exercise the schema once end to end**, then take the first Linux capture
   (A2, B2) -- the architecture assumption is untested.
3. **Record the microbenchmark baseline now** (A3): `verifysaplingspend` /
   `verifysaplingoutput` measure per-proof cost directly, and a batching result
   needs that baseline taken *beforehand*.

---

## 2. Equihash and blake2 -- parallel track

**Delineated deliberately.** Work in these areas is developed in parallel,
outside the sync/ConnectBlock investigation, and will be tested and benchmarked
after integration into the ZeroPerf structures. This section is the seam.

Nothing here is mixed into S1 or S3, because the two tracks answer different
questions and are measured on different workloads. Conflating them has already
produced one wrong number in this program's history.

### 2.1 Why it is a separate track

| | Sync / ConnectBlock (S1, S3) | Equihash / blake2 (this section) |
|---|---|---|
| **Question** | How long to validate the chain? | How long to solve or verify a PoW header? |
| **Workload** | reindex / bootstrap / sync / rescan | mine, `zcbenchmark solve/verify` |
| **Hot thread** | `zcash-loadblk`, or `Main Thread` for rescan | miner thread |
| **Who cares** | Every operator syncing a node | Miners; validation cost for everyone |
| **Harness** | `profile_run.sh`, throughput ledger | `mine_bench.sh`, `performance-measurements.sh` |

A capture from one track is **not comparable** to the other and must not be
pooled with it. The schema keeps them apart via
`features.workload.op` (`SCHEMA.md` S5).

### 2.2 Use cases, and why they diverge

- **Mining (solve).** Throughput per watt on a miner's hardware. Equihash
  (192,7) needs roughly 8 GB per solver thread. Improving solve speed benefits
  miners and changes network hashrate distribution; it does **not** speed up
  node sync.
- **Validation (verify).** Every node verifies every header. Cheap already
  (p50 0.100 ms, n=20), so it is a correctness-and-regression concern more than
  an optimization target -- but a regression here is felt chain-wide.
- **blake2b as a shared primitive.** Used by Equihash *and* elsewhere in
  validation, which is why it must be bucketed separately from `equihash` --
  see S3.3.

### 2.3 Established so far

| Result | Value | Source |
|--------|-------|--------|
| `verifyequihash`, n=20 | p50 **0.100 ms** | `zcbenchmark` |
| `solveequihash`, n=3 | 54.2 / 67.1 / 69.0 s | `zcbenchmark` |
| Solve CPU | 100% of one core, single thread | `solve.tsv` |
| Solve peak footprint | **7148 MB** | `solve.tsv` |
| regtest (48,5) mine | **83 ms/block** | `mine-20260819T234157Z/results.tsv` |
| KATs | genesis (192,7) vectors green | `src/test/data/1927EQ*` |
| arm64 blake2b symbol | still links `blake2b_compress_ref` (portable C) | neon probe |

`mine_bench.sh` provides `regtest`, `mainnet-template` and `neon-probe` modes.
A mainnet (192,7) timed solve is scheduled but not run.

### 2.4 Integration expectations for the queued work

When the parallel Equihash/blake2 work lands, it is measured through the same
structures as everything else, with these specifics:

- **Bundle first.** Any new build-time option gets an entry in
  `feature_bundles.json` before a trial is recorded, or every row reads
  `custom` and cannot be grouped (`POLICY.md` S3).
- **Classify the flag.** Is it architectural, scenario, or perf? That decides
  whether it belongs in the bundle key.
- **`workload.op` must distinguish solve from verify from sync.** Otherwise a
  solve trial pools with a reindex trial.
- **Baseline before change.** Record the S2.3 numbers on the target host with
  the current binary first; a delta against a differently-built baseline is not
  a delta.
- **Keep the blake2b bucket separate** from `equihash` (S3.3).
- **arm64 vs x86-64 matters more here than anywhere else**, because the
  candidate optimizations are SIMD intrinsics. A NEON result says nothing about
  AVX2 and vice versa; `platform.arch` is doing real work in this track.

### 2.5 Standing judgement, open to revision

blake2b is **18-21% pre-Sapling but 3-4% post-Sapling**, so on the *sync* track
it does not compete with Groth16 for attention. That is a statement about sync,
not about mining, and it is the reason NEON blake2b sits `Aside` on the sync
track (`TASKS.md`). If the parallel work targets the mining use case, this
judgement does not apply to it.

---

## 3. Settled: the sync investigation

Older results, still true and still cited. Ordered most-recent first within the
section.

### 3.1 Wallet size dominates rescan, for reasons unrelated to block validation

On a large wallet, rescan cost is not ConnectBlock -- it is the witness scan.

| Wallet | Rescan CPU share | Note |
|--------|-----------------|------|
| none / p0 / p1 | 0 - 0.32% | p0 rescans in **2 ms**; nothing to profile |
| fat (749 MB, 801619 tx) | **72 - 99%** in `witness_cache` | Dominated by `SelectWalletTxsForWitnessScan` |

Above h1.6M the scan reaches **97-99%** and throughput falls to ~19 blk/s
(M-WAL-RESCAN-FAT).
Cause: a founders coinbase per block invalidates the note index, forcing an
O(`mapWallet`) rebuild for 1403/801619 (**0.175%**) note-bearing txs. Fix is
localised to two call sites -- `TASKS.md` B3.

**NOTEIDX** (iterate note-bearing txs only) gives **35x** on the witness walk:
0.153 ms/block versus 5.31-5.72 ms/block stock (M-WAL-WITNESS-TIP-AB).
Shipped, opt-in.

**Gap:** no p1 rescan capture, so the curve between 0.32% and 72% is unmeasured.

### 3.2 Import is serial and CPU-bound, so I/O tuning cannot help

One thread at 100%, disk syscalls under 5% of samples. Measured, not assumed --
and it explains a null result rather than merely asserting one.

Throughput by region (n in the ledger):

Source for all three: the throughput ledger
(`reindex-profile/bench-summaries/ledger.jsonl`), n as noted.

| Region | Rate | n |
|--------|------|---|
| pre-Sapling (~h50k-75k) | ~1018-1027 blk/s | 11 |
| Sapling onset (h490k-520k) | 130-140 blk/s | 2 |
| deep post-Sapling (h600k-900k) | ~300-304 blk/s | 22 |

Same-host repeatability is **4%** (178.0 s vs 171.0 s on an unchanged binary),
which is the noise floor any claimed improvement must clear.

**The FDCACHE lesson.** A buffer-size A/B measured a 1.1% spread against
1.7-4.5% noise -- indistinguishable from nothing. Profiling the same workload
afterwards showed why an I/O knob had nothing to act on. **Profile first when
the bottleneck is unknown; benchmark when it is known and a delta needs
proving.** Set `Aside`.

### 3.3 Bucketing is load-bearing, and has been wrong before

Attribution is first-match-wins over the stack, so bucket order determines the
answer. Four published figures were wrong because of it:

| Wrong figure | Cause | Corrected to |
|--------------|-------|--------------|
| "Tree 57-58%" | `jubjub Point::add` is in both tree and proof paths; tree matched first | Groth16 understated by ~50 points |
| Witness cost missing | a bare `CWallet::` needle matched first | `VerifyAndSetInitialWitness` attributed correctly |
| `disk_io` 14.66% | one bucket over-matched | 4.91% real syscall leaves, split into `disk_syscall` / `disk_decode` |
| No blake2b figure at all | hidden inside `equihash` | own bucket, ordered first |

The current ordering encodes these corrections and **must not be "tidied"** --
the operational rule is in `HOWTO.md` S2.1.

**A bucket reading 0.00% for something plainly running is expected**, and is
the same effect seen from the other side -- check the overlapping *layers* view
before believing it.

### 3.4 Operation type barely matters; height region matters enormously

Bootstrap, reindex and sync agree within **~3 points** on every bucket at the
same heights. They differ in how blocks are *sourced*, not in what validation
costs -- which is why filling the "no post-Sapling bootstrap capture" gap is
`Aside` rather than open.

Height region, by contrast, changes everything: the Groth16 share moves from
~43% pre-Sapling to 88-91% post-Sapling. **A measurement without a height
window is not comparable to anything.**

### 3.5 Shipped fixes

| Fix | Effect |
|-----|--------|
| Merkle-root latch | `IncrementalMerkleTree::root()` memoised, invalidated on append and deserialize |
| Anchor-existence index | Anchor existence checks indexed |
| Block-file read latch | `-perffdcache`; requires `--enable-perf` |
| Witness IBD deferral | `-walletwitness=ibd-defer`, opt-in |
| NOTEIDX | `-walletwitnessnote`, opt-in; 35x on the witness walk |
| Shutdown responsiveness | Block-index load and `ThreadImport` honour shutdown |

The first three are pure memoisation: they change *how fast* a value is
obtained, never *what* is computed. That is why they carried a far lighter
review burden than batch verification would.

---

## 4. Known blind spots

Bounds on everything above.

| Blind spot | Effect |
|-----------|--------|
| One platform, one architecture | All numbers macOS/arm64. `TASKS.md` B2 |
| Groth16 verification untimed | The largest post-Sapling cost is invisible to `-debug=bench`. S1.1 |
| Thermal never observed non-Nominal | Every capture is 60 s; no multi-hour run has been checked for throttling |
| Microbenchmark suite unrecorded | 19 benchmarks runnable, `M-ZCB-SUITE` has no numeric archive |
| No p1 rescan capture | Two-order-of-magnitude hole in the wallet-size curve. S3.1 |
| Dirty builds | Every existing row came from a binary matching no commit. `SCHEMA.md` S2.1 |
