# Equihash (192,7) -- optimization plan

Staged plan from one CPU core to GPUs, across Linux, Windows and macOS. This
is an outline, not a result: what to build, in what order, and what gates each
step.

Evidence for the ordering is in `FINDINGS.md`; how to validate a change is
`METHOD.md`.

Entry point for the whole set: `README.md` in this directory.

---

## 4. Stage 1 -- single core, algorithm and memory

Highest value, lowest risk, and a prerequisite for S2-S4. Every item here is
portable across all three platforms and needs no new dependency.

**What the reference profile says, and why it only partly applies.** An
independent Requihash implementation profiled its solver and found the
intuitive target was third [Reported: Requihash `Req/BENCHMARK.md` S2 (out of
tree)]: malloc/free **59%**, sort **24%**, BLAKE2b **17%**; arena + bucket sort
gave **1.86x**.

**That malloc figure does not transfer to Zero** (S1.1): the Requihash
reference stored a heap `Vec` per row, whereas Zero's `StepRow` is a fixed
inline array inside one reserved `std::vector`. Zero has already paid the arena
win. What survives from that profile as a live hypothesis for Zero is the
**sort share** -- Zero uses `std::sort` with a comparator
(`CompareSR(CollisionByteLength)`) on a 3-byte key, exactly the radix-sort
candidate S1.3 describes.

So the expected Zero profile is *different*: allocation low, sort and BLAKE2b
higher, memory bandwidth prominent because the working set is 2.2-7 GB rather
than a few hundred MB. **S1.1 measures it rather than assuming either
profile.**

### S1.1 Profile the real solver before changing anything

Do not start from the table above; reproduce it for Zero at (192,7).

```bash
MINE_MAINNET_SOLVE=1 contrib/perf/mine_bench.sh mainnet-template &
contrib/perf/profile_run.sh S-EQU-SOLVE "$LAB" 60 "<miner thread>"
```

Note the thread filter: the solver does **not** run on `zcash-loadblk`
(`../docs/HOWTO.md` S2.4 -- the wrong filter silently returns nothing). Confirm
the miner thread name first.

Exit: a bucket/leaf breakdown for (192,7) that either confirms or refutes the
allocation-dominated hypothesis. **If BLAKE2b is >40% here, S2 moves ahead of
the rest of S1** -- the 33.5M-leaf list makes that plausible in a way it is
not at (200,9).

### S1.2 Cut peak memory from ~7 GB

The single most important item in the plan. Techniques, in the order the
Equihash record establishes them [Reported:
Requihash `Equihash.md` S3 (out of tree)]:

1. **Compact index-pointer storage.** Store a binary tree of index *pairs*,
   reconstructing full indices only at solution time -- a `(2^k)/k` space win
   (at k=7, ~18x on index storage). The single largest memory technique in the
   record.
2. **Static allocation.** Size all working memory once from `(n,k)`; no
   per-row heap traffic.
3. **In-place merge.** Write merged rows into freed slots of the sorted input
   (zcash `BasicSolve`'s `posFree` cursor), so two full copies never coexist.

**Targets, staged** (S1.2a explains why 144 MB is not among them):

| Step | Expected peak | Multi-core at 16 GB |
|------|--------------:|---------------------|
| today | 7.15 GB | 2 threads |
| `Xc.reserve()` | ~4.4 GB | 3 threads |
| + per-round widths | ~2.2 GB | 7 threads |
| + index pointers | ~1.0-1.5 GB | 10-16 threads |

`Xt` alone is 2.19 GB at these parameters, so anything below that requires the
index-pointer work. Verify with `res_sample.sh` `phys_mb`, not with an
estimate.

### S1.2a Is compact index storage a memory win or a performance win?

Both, but **indirectly**, and the distinction matters for how to sequence it.

*Directly*, it is a memory optimization: storing index *pairs* instead of
accumulated index lists is a `(2^k)/k` space win on the index portion -- at
k=7, 128 indices become 2 pointers. It does not remove a single hash
evaluation or a single comparison.

*Indirectly*, it becomes a performance optimization through three channels:

1. **Smaller rows mean less memory traffic.** Every round sorts the list and
   copies rows `Xt -> Xc -> Xt`. Narrower rows move fewer bytes.
2. **Smaller rows mean better cache behaviour.** The sort's compare-and-swap
   working set shrinks; more rows per cache line.
3. **Smaller rows unlock parallelism.** At ~7 GB per solve, S3 and S4 are
   impossible. This is the largest effect and it is categorical, not
   incremental -- it converts "cannot run 8 threads" into "can".

**But do not overstate channel 1.** Bandwidth accounting, stated carefully
because the numbers are easy to misread:

| Quantity | Value | What it is |
|----------|------:|------------|
| Resident peak | 7.15 GB | Memory *held*; the constraint on threads [Measured] |
| One sweep of `Xt` | 2.19 GB | 33.5M rows x 70 B |
| **Cumulative traffic** | **~26 GB** | 6 rounds x 2 copies x 2.19 GB, **summed over the whole ~60 s solve** |

The 26 GB is **bytes moved over a minute, not bytes resident** -- nothing ever
allocates it. Spread across a 54-69 s solve it averages **~0.44 GB/s**, roughly
**1% of DDR4 dual-channel bandwidth**, or **under one second** of transfer if
issued at full rate.

The conclusion: **bandwidth is not where the time goes.** ~99% of the solve is
something else -- most plausibly the comparison sort over 33.5M rows (S1.3).
Narrowing rows helps that through *cache behaviour*, not through raw bytes
moved. Per-round widths cut the average row to ~33 B (0.47x), a real but
second-order direct gain.

The measured trace agrees: RSS climbs 409 -> 4832 MB, holds, then falls to
366 MB as buffers free, with disk I/O peaking at 3.99 MB/s and settling under
0.1 -- so nothing swaps and the working set fits
[Measured, `test-logs/res-mine-20260819/solve.tsv`].

**Sequencing consequence.** Order the memory work by cost-to-benefit, not by
prestige:

| Step | Effort | Direct perf | Memory | Gate |
|------|--------|-------------|--------|------|
| `Xc.reserve()` | 1 line | small (no realloc copies) | removes ~2-3 GB transient | V1 |
| Per-round widths | M | ~0.47x traffic, better cache | 2.19 -> ~1.0 GB | V2 |
| Index pointers | L | small directly; large via cache + parallelism | ~1.0 -> under 0.5 GB | V2 |

Index pointers are the **largest memory win and the smallest direct speed win**
of the three. Do them for what they unlock (S3, S4), not for what they save on
one core -- and do the two cheaper steps first, because they may already clear
the threshold that makes multi-core viable.

### S1.2b What the sort is actually doing, and why 3 bytes

**Why a sort at all.** Each round must find rows whose next `CollisionBitLength
= 24` bits match. Sorting on those bits brings equal-prefix rows adjacent, so
the merge is a linear scan over runs. It is a *grouping* operation; total order
is an artifact of using a comparison sort to achieve it.

**Why 3 bytes.** `CollisionByteLength = (24+7)/8 = 3`. The comparator is:

```cpp
memcmp(a.hash, b.hash, len)   // len = CollisionByteLength = 3, a RUNTIME value
```

Three inefficiencies, all fixable:

1. **`memcmp` with a runtime length** cannot be inlined to a fixed-width
   compare. A `u32` load, byte-swap and integer compare would be a handful of
   instructions; `memcmp(...,3)` is a call into a generic routine.
2. **`std::sort` is `O(m log m)` comparisons** -- with m = 33.5M, log2(m) = 25,
   so ~840M comparisons per round, ~5 billion over 6 rounds. The key is only
   24 bits wide, which is exactly the case radix/counting sort handles in
   `O(m)`.
3. **Every swap moves 70 B** (S1.1a1) though only 3 are compared.

**Why is `len` runtime and not fixed per round?** It is an accident of the
class design, not a requirement. `CollisionByteLength` **is** a compile-time
enum (`equihash.h:175`), but it is passed into `CompareSR`'s constructor and
stored as a `size_t len` member, so the constant is laundered into a runtime
value the optimizer cannot fold. Two call sites pass a genuinely varying value
(`CompareSR(hashLen)` at `equihash.cpp:417`), which is presumably why the
member exists at all.

The fix is mechanical and costs nothing:

```cpp
template<size_t LEN>                       // compile-time
struct CompareSRFixed {
    template<size_t W>
    inline bool operator()(const StepRow<W>& a, const StepRow<W>& b) const {
        return memcmp(a.hash, b.hash, LEN) < 0;   // LEN now constant-folded
    }
};
// use: std::sort(Xt.begin(), Xt.end(), CompareSRFixed<CollisionByteLength>{});
```

With `LEN` a constant, `memcmp(...,3)` compiles to a handful of inline
instructions instead of a call. **V1 only** -- it cannot change ordering.

**Would a u64 key read help?** Yes, and more than the constant-folding. Reading
3 bytes as part of a wider load and comparing as an integer replaces
byte-at-a-time semantics with one compare:

```cpp
// 24-bit big-endian key from the row's first 3 bytes
static inline uint32_t key24(const unsigned char* p) {
    return (uint32_t)p[0] << 16 | (uint32_t)p[1] << 8 | p[2];
}
```

A `u64` load is only safe if at least 8 bytes are readable from the row start
-- true here (rows are >= 22 B) -- but on x86 an unaligned `u64` load is fine
while on arm64 it is fine for normal memory too, so `memcpy` into a `uint64_t`
(which compiles to a single load) is the portable form. **The larger win is
extracting the key once into a separate array (Experiment B) rather than
re-reading it on every comparison** -- `std::sort` performs O(m log m)
comparisons over the same m rows, so each key is re-read ~25 times.

**Is `memcmp` on unaligned `a`/`b` suboptimal? UNVERIFIED -- do not treat the
usual answer as measured.** Rows are 1-byte aligned (S1.1a1), so `memcmp`'s
internal wide loads are unaligned. The *common* claim is that unaligned loads
within a cache line are near-free on both modern x86 and arm64, so the real
costs would be the un-inlined call and line-straddling. **Neither this tree nor
this document has measured it on either architecture**, and the two differ
enough elsewhere (128 B vs 64 B lines, NEON vs AVX2) that assuming parity is
exactly the kind of cross-platform generalisation S8 warns against.

Concretely unmeasured: whether an unaligned 4/8 B load costs extra on Apple
M-series, and whether x86 split-line penalties are material at this access
pattern. **Experiment C plus a 4/8 B-aligned variant would settle it**, and
until then the alignment recommendation rests on the line-straddling arithmetic
(which *is* computed) rather than on load-alignment claims (which are not).

**Implementation note -- these two are separable and both cheap:**

| Change | Effort | Gate | Independent? |
|---|---|---|---|
| Fold `len` to a compile-time constant | ~10 lines, one new comparator template | **V1** | Yes -- ships alone |
| Extract the key once into a `u32` array | ~20 lines, Experiment B | **V2** | Yes -- ships alone |

Do the fold **first**: it is V1, cannot change ordering, and measuring it alone
tells you how much of the sort cost is call overhead versus data movement --
which then predicts how much extraction can add. Doing both at once conflates
two effects that have different fixes at S2 (the fold helps scalar code; the
extraction is what SIMD can act on).

**What it should be.** A counting sort on the high byte of the 24-bit key --
256 buckets, one counting pass, one scatter pass, `O(m)` -- which is the
"incomplete bucket sort" of the 2016-17 wave: it never produces a fully sorted
list, only the grouping the merge needs. That is S1.3, and Experiment B above
is its natural precursor because it materialises the key as a `u32`.

#### Hand-crafted sort: how many entries, and how uniform?

A hand-written sort needs two facts about the data. Both are computable, and
they are unusually favourable here.

**Entry count is fixed and known:** `init_size = 2^25 = 33,554,432` rows, every
round, every solve. No growth, no reallocation, no unknown *m*. That alone
justifies a static allocation.

**Distribution is as close to uniform as it gets.** The key is 24 bits of
BLAKE2b output, so keys are effectively independent uniform draws -- the
"truly uncorrelated" case. With 2^25 rows over 2^24 keys (lambda = 2.0):

| Rows sharing a key | Share of keys |
|---|---:|
| 0 | 13.5% |
| 1 | 27.1% |
| 2 | 27.1% |
| 3 | 18.0% |
| 4 | 9.0% |
| 5+ | 5.2% |

For a counting sort on the **high byte** (256 buckets):

- expected **131,072** rows per bucket
- standard deviation **361** (0.28% of the mean)
- **+5 sigma = 132,879**, i.e. **1.4% over-provisioning** covers a
  one-in-3.5-million bucket

**That is the tuning result:** a fixed 256-bucket layout with ~1.5-2%
headroom is statistically safe without any dynamic sizing, and 2 passes
(count, scatter) suffice. Compare tromp's ~2.0x over-provisioning (S1.2a),
which buys single-pass insertion and pays 50x the headroom -- the counting
sort's second pass is what makes the tight bound possible.

**Bucket count is the free tunable.** 256 (high byte), 4,096 (12 bits), or
65,536 (16 bits) all keep sigma/mean under 1%; the choice is a cache question,
not a correctness one:

| Buckets | Rows/bucket | Bytes/bucket at 70 B | Fits |
|---:|---:|---:|---|
| 256 | 131,072 | 8.8 MB | L2 (M-series 16 MB shared) |
| 4,096 | 8,192 | 573 KB | L2 (x86 private) |
| 65,536 | 512 | 36 KB | L1d |

**This is the concrete platform-specific tuning knob** (S5's L2 note): 256 may
suit Apple's large shared L2, 4,096 x86's smaller private L2. Sweep it; the
distribution guarantees none of them overflow.

#### Bucket sort vs hash table

Both group rows by collision prefix; they differ in when the grouping is
materialised.

| | Counting/bucket sort | Hash table (tromp) |
|---|---|---|
| Structure | count pass, prefix sum, scatter pass | fixed-capacity slot array per bucket |
| Sizing | exact, derived from the count pass | over-provisioned (`SAVEMEM`, ~2.0x here) |
| Overflow | impossible | possible; slots beyond `NSLOTS` are **dropped** |
| Passes over data | 2 (count, scatter) | 1 (insert) |
| Memory | one output buffer | `NBUCKETS x NSLOTS` up front |
| Fits Zero today | **yes** -- drop-in for `std::sort` | needs the whole layout |

**Counting sort is the right S1.3 step for Zero**: it replaces `std::sort`
behind the same interface, needs no layout change, and is exactly the
"incomplete bucket sort" of the 2016-17 wave. The hash-table form is tromp's,
and it buys single-pass insertion at the cost of over-provisioning **and
accepting solution loss on overflow** -- a trade only worth making as part of a
full port, and one that must be validated against V2 precisely because it can
silently drop solutions.

### S1.2c `std::vector` and the alternatives to the heap

`Xt` and `Xc` are `std::vector`, which for multi-GB sizes means `mmap` under
the hood. What that costs, and what else is available:

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| `std::vector` (today) | Portable, RAII, `reserve` available | Growth reallocs (the `Xc` bug), value-initialises on resize, one alignment (1 B) | Keep for `Xt`; fix `Xc` |
| `reserve()` + `emplace_back` | Removes realloc entirely | Still 1 B aligned | **Do this now** (one line) |
| `std::aligned_alloc` / `posix_memalign` | Control alignment | Manual lifetime; needs a deleter | Only if Experiment C shows alignment matters |
| `mmap` with `MAP_POPULATE` (Linux) | Pre-faults pages, avoids fault storm on first touch | Linux-only; needs a portability shim | Worth testing at S8 |
| Huge pages (2 MB) | 2.19 GB is ~1.1M 4K pages -> ~1000 huge pages; large TLB win | `madvise(MADV_HUGEPAGE)` Linux, `VirtualAlloc` Windows, limited macOS | **Promising, measure at S8** |
| Stack / `alloca` | No allocator | Impossible: GB-scale | No |
| Custom pool | Full control | Reimplements the allocator | Not justified |

**The stack is not an option** at these sizes, but two heap refinements are
worth measuring:

- **Huge pages -- and the base page size differs by platform.** Measured on
  this host: `hw.pagesize = 16384` (Apple M4 Pro), against 4096 on x86-64. For
  a 2.19 GB buffer:

  | Platform | Base page | Pages for 2.19 GB | Large-page option |
  |---|---:|---:|---|
  | x86-64 Linux | 4 KB | **574,095** | 2 MB / 1 GB, `MADV_HUGEPAGE` or `hugetlbfs` |
  | x86-64 Windows | 4 KB | 574,095 | 2 MB, needs `SeLockMemoryPrivilege` |
  | Apple M4/M5 | **16 KB** | **143,524** | 2 MB superpages via `VM_FLAGS_SUPERPAGE_SIZE_2MB`, limited |

  **Apple's 16 KB base page already gives a 4x TLB advantage over x86's 4 KB**,
  which is one reason the arm64 baseline may be less TLB-bound than an x86 run
  will be. On x86-64, 574k pages against an L2 dTLB of roughly 1.5-2k entries
  means the sort's working set is far beyond TLB reach and 2 MB pages should be
  a **larger** win there than on M-series. **This is a concrete prediction to
  test at S8** and a reason not to generalise the arm64 profile.
- **Pre-faulting.** The RSS ramp in the trace (409 -> 4832 MB over ~14 s)
  partly reflects demand paging. `MAP_POPULATE` or an explicit touch loop moves
  that cost to a predictable place and may reduce it.

Both are S8/platform items, both V1 (they cannot change results).

### S1.3 Replace the comparison sort

24-bit collision keys are ideal for radix/counting sort ("incomplete bucket
sort": partition on the collision digit, never fully sort). Bucket count must
be derived for (192,7) -- see S2 above; do not copy a (200,9) constant.

### S1.4 Pointed BLAKE2b work (only what the profile justifies)

Zero's build links `blake2b_compress_ref`, the **portable C fallback**, on
arm64 [Measured: neon probe, `test-logs/res-mine-20260819/`]. Two separable
questions:

- **Is a better scalar/SIMD kernel selected at build time?** Free win if the
  answer is no and a dispatching implementation is available.
- **Can leaf generation be batched?** Equihash generates 33.5M independent
  leaves -- ideal for `hash_many`-style batched BLAKE2b. But note the
  Requihash finding: batched SIMD converged to *parity* at larger parameters
  because **memory bandwidth, not compute, bounded the batch** [Reported].
  Measure before committing.

**Stage 1 exit:** peak memory at or below ~2.2 GB (`Xt`-bound) with the
allocation waste removed, a measured speedup on (192,7) with
n>=4 trials, regtest tests still green, results in the ledger with platform and
build stamped.

---

## 5. Stage 2 -- special instructions, one core

Only after S1, because SIMD accelerates whatever layout S1 leaves behind.

| Target | Instruction set | Notes |
|--------|-----------------|-------|
| x86-64 | **AVX2** | The baseline for mining hosts; xenoncat's (200,9) solver was AVX2 |
| x86-64 | AVX-512 | Narrow deployment, downclocking risk -- measure, do not assume |
| arm64 | **NEON** | macOS Apple Silicon and ARM Linux; currently unused (S1.4) |

Two distinct targets: **BLAKE2b compression** (well-trodden; reference AVX2 and
NEON kernels exist) and **the merge/sort inner loop** (XOR and compare over
24-bit keys vectorise, but gains depend on the S1 layout).

#### Vector width and cache architecture, measured

Measured on this host (`sysctl hw.*`, Apple M4 Pro) against typical x86-64:

| | Apple M4/M5 | x86-64 (Zen 4 / Golden Cove) |
|---|---|---|
| Vector ISA | NEON **128-bit** (+ SME on M4) | AVX2 **256-bit**, AVX-512 **512-bit** |
| Cache line | **128 B** | 64 B |
| Base page | **16 KB** | 4 KB |
| L1d | 128 KB/core (perf) | 32-48 KB/core |
| L2 | **16 MB shared per 5 cores** | 1-2 MB/core private |
| L3 | none (SLC instead) | 32-96 MB shared |

Three consequences for this work:

- **NEON is 128-bit and does not widen.** Where AVX2 processes 4 BLAKE2b lanes
  and AVX-512 processes 8, NEON processes 2. So the *ceiling* for batched
  hashing is structurally lower on arm64, and an arm64 "SIMD gives little"
  result does **not** predict x86.
- **Apple's 128 B line halves the row-straddling problem** (1.53 vs 2.06 avg
  lines) and its 16 KB page quarters TLB pressure -- both flatter the current
  code on arm64 relative to how it will behave on x86.
- **Apple's large shared L2 (16 MB) vs x86's small private L2** changes bucket
  sizing: a bucket that fits in 16 MB shared may thrash a 1 MB private L2.
  `RESTBITS`/bucket-count tuning is therefore **platform-specific**, not a
  single constant.

**Where the instruction sets are documented (current, 2026):**

| ISA | Reference |
|---|---|
| x86-64 (AVX2, AVX-512, AVX10) | *Intel 64 and IA-32 Architectures Software Developer's Manual*, and the **Intel Intrinsics Guide** (searchable, per-intrinsic latency/throughput) |
| x86 microarchitecture timings | Agner Fog's instruction tables; uops.info (measured, per-uarch) |
| AMD | *AMD64 Architecture Programmer's Manual*, vols 1-5 |
| Arm NEON / SVE / SME | *Arm Architecture Reference Manual* (ARM ARM), and the **Arm Intrinsics Reference** |
| Apple-specific | Apple Silicon CPU Optimization Guide (M-series pipeline and cache behaviour) |

Note **AVX10** is the current consolidation of the AVX-512 feature mess and is
what new x86 work should target rather than raw AVX-512 feature bits; check
availability at runtime either way.

**Dispatch discipline.** Runtime CPU detection with a scalar fallback, and a
self-test gate that asserts every SIMD kernel matches scalar bit-for-bit before
it is used. A wrong SIMD kernel produces invalid solutions, which on a miner
means silently wasted work.

`ENABLE_MINING` and any new SIMD flag are **scenario flags** in the feature
bundle sense (`../docs/POLICY.md` S3): they vary per test batch and must be in the
bundle key, or an AVX2 run and a scalar run will pool into one meaningless
mean.

**Stage 2 exit:** measured per-ISA speedup on the same host, self-test gate
green, arch recorded (`platform.arch` -- a NEON result says nothing about
AVX2).

---

## 6. Stage 3 -- multiple cores

### 6.0 The memory/core coupling is weaker than it looks -- two models

I overstated this earlier. **Memory only scales with thread count under one of
two parallelism models**, and the choice between them is the real decision:

**Model A -- independent solves per thread.** N threads each run a whole solve
on a different nonce. Memory is **N x per-solve**:

| Per-solve | 16 GB host | 32 GB | 64 GB | 128 GB |
|---|---:|---:|---:|---:|
| 7.15 GB (today) | 1 | 3 | 7 | 15 |
| 4.4 GB (`Xc.reserve`) | 3 | 6 | 12 | 24 |
| 2.2 GB (per-round) | 6 | 12 | 24 | 49 |
| 1.2 GB (index-ptr) | 11 | 22 | 45 | 90 |

Near-linear speedup, trivial to implement, no shared state -- and it is the
model the coupling claim assumes.

**Model B -- intra-solve parallelism.** N threads cooperate on **one** solve
sharing one working set. **Memory is constant in N**: ~2.19 GB whether 1 thread
or 16. So on a 16 GB host, 8-thread Model B is feasible **today, at 7.15 GB,
with no memory work at all**.

The catch is Amdahl. Parallelising only leaf generation (the easy half):

| gen share | N=8 | N=16 |
|---|---:|---:|
| 13% (measured at large params) | 1.13x | 1.14x |
| 25% | 1.28x | 1.31x |
| 50% | 1.78x | 1.88x |

**Generation-only parallelism is worth ~1.15x at these parameters** -- which is
why the Requihash reference measured 1.9x only at small parameters where
generation was 24%. The merge must be parallelised for Model B to pay, and that
needs disjoint read/write regions (S1.2a) -- i.e. ping-pong, which costs 1.93x
memory and partly re-introduces the coupling by a different route.

**Alternatives that decouple further:**

| Approach | Memory | Speedup | Note |
|---|---|---|---|
| Model A | N x | ~N | Simple; memory-bound |
| Model B, gen-only | 1x | ~1.15x | Free today, small |
| Model B, merge-parallel | ~1.9x (ping-pong) | up to ~N | The real target |
| **Hybrid** | M x, M < N | ~N | M solves x (N/M) threads each -- tune M to RAM |
| Bucket-partitioned Model B | 1x + per-thread scratch | up to ~N | Partition by collision prefix; barrier per round |

**The hybrid is probably the practical answer**: 2-4 concurrent solves, each
using 2-4 threads on the merge, sized so total memory fits. It needs both the
memory work *and* merge parallelism, but neither has to be complete before it
pays.

**Revised claim:** memory does not gate multi-core absolutely -- it gates
*Model A*, which is the easiest and highest-yield form. Model B is available
today at low yield. **Record peak memory alongside every scaling measurement**
so which model is in play is never ambiguous.

Two parallelisation axes, and they are not equivalent:

1. **Parallel leaf generation.** Easy: 33.5M independent BLAKE2b evaluations.
   But it is only the generation fraction, so its ceiling is bounded by
   Amdahl -- Requihash measured **1.9x and no more** from generation-only
   parallelism [Reported].
2. **Parallel merge.** The real lever, and harder: partition each round by
   collision-prefix bucket across threads, with a barrier per round. Cross-
   bucket collisions and the round barrier are the difficulty.
3. **Independent solves per thread** (trivially parallel, N x memory). The
   fallback if (2) proves too invasive -- and the option most directly gated by
   S1.2.

Interaction to watch: **memory bandwidth saturation**. If S1.4 finds batched
hashing bandwidth-bound on one core, N cores will contend harder. Record
per-thread CPU *and* achieved scaling; a 4x thread count yielding 1.5x is a
bandwidth result, not a bug.

**Stage 3 exit:** measured scaling curve (1, 2, 4, 8 threads) with peak memory
at each point, on a host whose core count is recorded.

---

## 7. Stage 4 -- GPU

Where the remaining order of magnitude lives, and where the platform matrix
becomes real.

| Backend | Vendor | Platforms | Note |
|---------|--------|-----------|------|
| **CUDA** | Nvidia | Linux, Windows | Largest miner ecosystem, best tooling |
| **OpenCL** | Nvidia, AMD, Intel | Linux, Windows, macOS (deprecated) | One source, several vendors; Apple deprecated it |
| **Metal** | Apple | macOS | The only first-class macOS GPU path |
| **Vulkan compute** | All | Linux, Windows, Android | Portable, more plumbing |

**Recommended order: CUDA first** (largest mining install base, best profiling
tools), **then OpenCL** for AMD coverage, **Metal only if macOS mining is a
real goal** -- macOS is a development platform here, not a mining platform, and
Metal is a separate kernel language.

Note the naming in the brief: **NEON is a CPU SIMD instruction set (S2), not a
GPU backend.** Apple GPU work is Metal.

GPU-specific concerns beyond porting:

- **Memory hierarchy is the whole game.** VRAM capacity bounds parallel solve
  instances; a 7 GB working set is impossible, ~1 GB is workable on an 8 GB
  card. **The memory work gates S4 as hard as it gates S3.**
- **Occupancy vs working set.** More concurrent solves means less memory each.
- **PCIe transfer** should be negligible if solving stays resident -- verify,
  do not assume.
- **Validate every solution on CPU** before submission. A GPU kernel bug that
  yields invalid solutions is indistinguishable from bad luck at the pool.

**Stage 4 exit:** Sol/s on named hardware, with power draw if the comparison is
to be economically meaningful; solutions CPU-validated.

---

## 8. Platform matrix

| Concern | Linux | Windows | macOS |
|---------|-------|---------|-------|
| Build | Primary; `zcutil/build.sh` | MXE cross-compile, **never executed in this program** (`../docs/TASKS.md`) | Supported; the dev platform here |
| CPU profiling | `perf` + folded stacks (`../PerfPlatforms.md` S3) | ETW/WPA -- blocked on MinGW/PDB symbols | Instruments/`xctrace` -- the only path exercised so far |
| Threading | pthreads | pthreads via MinGW | pthreads |
| GPU | CUDA, OpenCL, Vulkan | CUDA, OpenCL, Vulkan | Metal only |
| Status | **Recommended target** | Build path needs validation first | Dev and correctness only |

**Every published number in this tree is macOS/arm64** (`../docs/FINDINGS.md`).
For a mining plan that is the wrong platform: mining happens on Linux and
Windows, on x86-64 and GPUs. **An x86-64 Linux baseline is a prerequisite for
this plan to mean anything**, and it is already tracked as `TASKS.md` B2.

Two known blockers, neither introduced here: Windows MXE builds have never been
executed, and native Windows profiling is blocked on symbol format
(`../PerfPlatforms.md` S4.1).

---

## 9. Sequencing and honest expectations

| Stage | Work | Effort | Gate |
|-------|------|--------|------|
| **S0** | Profile (192,7); x86-64 Linux baseline | S | None -- start here |
| **S1** | Memory to <1 GB; arena; radix sort; BLAKE2b check | M | S0 |
| **S2** | AVX2 / NEON, dispatch + self-test gate | M | S1 |
| **S3** | Multi-core (merge-parallel preferred) | M-L | **memory work is a hard gate** |
| **S4** | GPU: CUDA, then OpenCL | L-XL | memory work; S2 informs kernels |

**What this plan does not claim.** It does not promise 100 Sol/s. It says the
gap decomposes into four factors, that the first is measurable now, and that
the memory result blocks two of the others. A realistic near-term outcome from
S1+S2 is **single-digit-to-low-double-digit Sol/s on a good CPU**; competitive
GPU rates require S4 and are gated on everything before it.

**What would invalidate the plan.** If S1.1 profiling shows Zero's solver is already
memory-lean and BLAKE2b-dominated at (192,7), then S1.2 is unnecessary, S2
moves first, and the staging above is wrong. That is the intended outcome of
measuring before optimizing, and it is why S0 exists.

**The verifier is deliberately left alone at this stage.** Zero's verifier is
the slower, portable, scalar implementation, and that is the correct choice
while the solver is the target: verification is ~0.100 ms
(`../docs/FINDINGS.md` S2.3) and is not on any hot path this plan touches. It
becomes worth revisiting only when the **demanding modes of operation** are
re-optimized -- chain sync, reindex, bootstrap, and rescan -- where the same
verification runs per block rather than per mined candidate. That is a
separate track with a separate workload
(`features.workload.op = sync`, not `solve`), and the two must not be pooled.
Zebro's fully parametric `is_valid_solution(n, k, ...)` is the right *shape*
for that future work even though its solver is not.

**Related but out of scope.** Sync-side Equihash cost is a *different*
question, already answered: Equihash verification is ~0.100 ms
(`../docs/FINDINGS.md` S2.3), and blake2b is 3-4% of post-Sapling sync, so none of
this work speeds up node sync. Mining and sync are separate tracks
(`../docs/FINDINGS.md` S2.1), and results must not be pooled -- `features.workload.op`
distinguishes `solve` from `verify` from `sync` (`../docs/SCHEMA.md` S5).
