# Equihash (192,7) -- findings

What is measured and computed about Zero's Equihash solver at production
parameters. Facts only; the optimization plan is `PLAN.md`, the measurement
method is `METHOD.md`.

Every number marked `[Measured]` comes from this tree. `[Computed]` is derived
from the source constants and is reproducible from them. Anything else is
labelled as an estimate.

Entry point for the whole set: `README.md` in this directory.

---

## 1. Where we start, and the size of the gap

Zero uses Equihash **(192,7)** on mainnet and testnet, and **(48,5)** on
regtest (`src/chainparams.cpp:94,265,425`). Only those two are instantiated
(`src/crypto/equihash.h:199-200`).

Current single-core baseline, this tree, macOS/arm64 [Measured,
`test-logs/res-mine-20260819/solve.tsv`, M-MINE-SOLVE]:

| Metric | Value |
|--------|-------|
| `zcbenchmark solveequihash`, n=3 | 54.2 / 67.1 / 69.0 s per solve |
| Effective rate | **~0.016 Sol/s** |
| CPU | 100% of **one** core, single thread |
| Peak physical footprint | **7148 MB** for one solve |
| RSS trajectory | 343 -> 6560 MB, rising and falling per attempt |

A modern GPU miner on comparable Equihash parameters is quoted in the tens of
Sol/s [Estimate, vendor/pool figures, not measured here]. Taking ~100 Sol/s as
the reference point, the gap is roughly **four orders of magnitude**
(0.016 -> 100 Sol/s, ~6000x).

That number should be read carefully. It is not one 6000x optimization; it is
a product of independent factors, and the plan below is organised by them:

| Factor | Rough contribution | Stage |
|--------|-------------------:|-------|
| Algorithm/data-structure (allocation, sort, index storage) | 2-10x | S1 |
| SIMD (AVX2/AVX-512/NEON) on hash and merge | 2-5x | S2 |
| Multi-core | 4-16x (core count, memory permitting) | S3 |
| GPU | 10-100x over one core | S4 |

Multiplied out, S1-S3 plausibly reach the low hundreds of times faster on a
good CPU; the rest is GPU. **No stage is skippable**: S3 is blocked by memory
today (PLAN.md S1.2), and S4 inherits whatever S1 fixes about the data layout.

### 1.1 Where the memory actually goes -- computed, not assumed

The 7.15 GB is explained exactly by the row-width constants, and the cause is
narrower than "unoptimized solver". From `src/crypto/equihash.h:175-180`:

```
CollisionByteLength = (24+7)/8            = 3 B
HashLength          = (K+1) * 3           = 24 B
TruncatedWidth      = max(24+1, 2*3 + 1*2^(K-1)) = 70 B    <-- fixed, ALL rounds
init_size           = 2^25                = 33,554,432 rows
```

- `Xt` at round 0: 33.5M x 70 B = **2.19 GB**
- Peak with the `Xc` merge buffer live: **~4.4 GB**
- Measured peak: **7.15 GB** [Measured] -- the remainder is allocator slack,
  `partialSolns`, and the final-round `FinalTruncatedWidth` of 134 B.

**The specific defect: `TruncatedWidth` is a single fixed 70 B for every
round**, sized for the worst round (`2^(K-1)` index bytes at round K-1). Round
0 needs ~25 B and pays 70 B. That is a ~2.8x overcharge on the largest list,
carried through the whole solve.

Two corrections to the naive reading, both verified in this tree:

- **Zero's rows are NOT heap-allocated per row.** `StepRow` holds
  `unsigned char hash[WIDTH]` -- a fixed inline array
  (`equihash.h:StepRow`). `Xt` is one `std::vector` with `reserve(init_size)`,
  so it is already arena-like. The 59%-malloc profile from the Requihash
  reference does **not** transfer; that codebase stored a `Vec` per row.
- **Zero already implements the in-place merge.** The `posFree` cursor writes
  merged rows back into freed slots of `Xt`
  (`equihash.cpp`, `OptimisedSolve`) -- one of the four canonical 2016-17
  techniques, already present.

So of the four 2016-17 techniques, Zero has in-place merge and static-ish
allocation; what it lacks is **per-round row sizing** and **compact
index-pointer storage**. That narrows S1 considerably and is why S1.1 profiles
before changing anything.

### 1.1a Per-round widths: what is needed vs what is allocated

`OptimisedSolve` runs the merge loop for **r = 1 .. K-1 (6 iterations)** at a
fixed `TruncatedWidth`, then one final step at `FinalTruncatedWidth`
(`equihash.cpp`, `for (int r = 1; r < K ...)`; final row is
`TruncatedStepRow<FinalTruncatedWidth>`).

A truncated row carries the *remaining* hash bytes plus one `eh_trunc` per
accumulated index. Both change every round, in opposite directions:

| Round | hash B left | indices | needed B | allocated B | waste |
|------:|------------:|--------:|---------:|------------:|------:|
| 0 | 24 | 1 | **25** | 70 | 45 |
| 1 | 21 | 2 | 23 | 70 | 47 |
| 2 | 18 | 4 | 22 | 70 | 48 |
| 3 | 15 | 8 | 23 | 70 | 47 |
| 4 | 12 | 16 | 28 | 70 | 42 |
| 5 | 9 | 32 | 41 | 70 | 29 |
| 6 | 6 | 64 | **70** | 70 | 0 |
| 7 (final) | 3 | 128 | 131 | **134** | 3 |

`TruncatedWidth = 70` is `max(HashLength+1, 2*CollisionByteLength + 2^(K-1))`
-- i.e. sized for **round 6**, the worst of the 6 loop rounds. Every earlier
round pays that width. Rounds 0-3 need 22-25 B and are charged 70 B: a
**~3x overcharge on the rounds holding the largest lists**.

Per-round sizing would give roughly `25/70 = 0.36x` on the round-0 array. The
catch is that `Xt` is a single `std::vector<TruncatedStepRow<W>>` with `W` a
compile-time template parameter, so per-round widths mean either a different
type per round (template recursion over `r`) or a byte-array with a runtime
stride. **The stride approach is the smaller change** and is what S1.2
proposes.

### 1.1a1 Where the buffers live, and how they are aligned

Two allocations dominate, both plain `std::vector` heap buffers -- so
malloc/`mmap` for multi-GB sizes, page-aligned by the allocator, and otherwise
unaligned internally:

| Buffer | Allocation | Element | Alignment |
|--------|------------|---------|-----------|
| `Xt` | `std::vector`, `reserve(init_size)` | `TruncatedStepRow<70>` | **1 byte** |
| `Xc` | `std::vector`, **no reserve** | same | **1 byte** |
| `partialSolns` | `vector<shared_ptr<eh_trunc>>` | pointer | 8 |

`StepRow` is `unsigned char hash[WIDTH]` and nothing else, so `alignof` is
**1** and `sizeof` is exactly 70 -- no padding, tightly packed, and **no
cache-line alignment whatsoever**. The rows are contiguous at a 70-byte stride
inside one large buffer.

**The stride is the problem.** With a 64-byte cache line and a 70-byte stride:

- **94%** of rows straddle **2** cache lines; 6% straddle 3
- Average lines touched per row: **2.06**, against a floor of 70/64 = **1.09**
- So the sort pays roughly **1.9x the cache-line traffic** it needs to

And the sort compares only `CollisionByteLength = 3` bytes at the front of each
row while `std::sort` swaps all **70**. That is the mechanism by which row
width shows up as *time*, not just as *space*: the comparison is cheap, the
data movement around it is not.

#### How to get to 1 or 2 cache lines

**First, the line size is not 64 B on the machine that produced the baseline.**
Measured on this host: `hw.cachelinesize = 128`, `hw.pagesize = 16384`
(Apple M4 Pro). So the same 70 B row behaves differently by architecture:

| Architecture | Line | 70 B row: avg lines | single-line |
|---|---:|---:|---:|
| x86-64 | 64 B | **2.06** | 0% |
| Apple M-series | **128 B** | **1.53** | **47%** |

The 2.06 figure quoted earlier is the **x86 case**; on the arm64 host where the
54-69 s baseline was measured it is 1.53. That does not remove the problem --
1.53 against a 0.55 floor (70/128) is still ~2.8x -- but it means **the
alignment experiments will read differently on the two platforms**, and an
arm64-only result must not be generalised.

Computed for a 64 B line (x86-64), all offsets over one period:

| Width | avg lines | 1-line | 2-line | 3-line | mem vs 70 |
|------:|----------:|-------:|-------:|-------:|----------:|
| 70 (today) | 2.06 | 0% | 94% | 6% | 1.00x |
| 72 | 2.00 | 0% | 100% | 0% | 1.03x |
| 80 | 2.00 | 0% | 100% | 0% | 1.14x |
| 88 | 2.25 | 0% | 75% | 25% | 1.26x |
| 128 | 2.00 | 0% | 100% | 0% | 1.83x |
| **64** | **1.00** | **100%** | 0% | 0% | 0.91x |
| **32** | **1.00** | **100%** | 0% | 0% | 0.46x |

**Padding upward never reaches 1 line on x86.** Any width above 64 straddles at
least 2; 88 and 112 are actively worse than 70 because they land badly against
the line. Widths reaching avg 1.00:

| Line size | Widths giving 1.00 avg |
|---|---|
| 64 B (x86-64) | 8, 16, 32, **64** |
| 128 B (Apple M) | 8, 16, 32, 64, **128** |

**This answers "should we scale to 32, 64, 72 bytes?" directly:** 32 and 64
are both single-line on *both* architectures and are the right targets. **72 is
not** -- it is above 64, so on x86 it straddles 2 lines (no better than 70)
while costing 3% more memory; on M-series it is 1.56, marginally worse than 70.
**128 is single-line on M-series only** and doubles memory, so it is a
measurement tool (Experiment C), not a shipping choice.

The only route to a single line on both is **<= 64 B with a width dividing
64** -- which is per-round sizing (PLAN.md S1.2), not padding.

**4- or 8-byte alignment does almost nothing here.** Those affect scalar load
alignment, not line straddling: a 70 B row at 8 B alignment still crosses a
line boundary about as often. They matter only if the sort key were read as a
`u32`/`u64` (PLAN.md S1.3), where an aligned 4 B load is cheaper than an unaligned one
-- a micro-effect next to the line traffic.

What per-round sizing actually buys, using the next width that divides 64:

| Round | needed | width | avg lines |
|------:|-------:|------:|----------:|
| 0 | 25 | **32** | **1.00** |
| 1-3 | 22-23 | 24 | 1.25 |
| 4 | 28 | **32** | **1.00** |
| 5 | 41 | 48 | 1.50 |
| 6 | 70 | 128 | 2.00 |

Rounds 0-5 -- the ones holding the largest lists -- reach 1.00-1.50 lines.
Only round 6 is stuck at 2.00, and by then the list is the same size but the
row genuinely needs 70 B.

#### The V2 experiments, in implementable detail

Both are V2 (differential vs unmodified solver, S3.2); neither changes which
solutions are found.

**Experiment A -- index-permutation sort.** Sort a `u32` array of row indices
instead of the rows, then materialise the permutation once.

```cpp
// before:  std::sort(Xt.begin(), Xt.end(), CompareSR(CollisionByteLength));
// after:
std::vector<uint32_t> idx(Xt.size());
std::iota(idx.begin(), idx.end(), 0u);
std::sort(idx.begin(), idx.end(), [&](uint32_t a, uint32_t b) {
    return memcmp(Xt[a].hash, Xt[b].hash, CollisionByteLength) < 0;
});
// then apply the permutation into a second buffer, or in-place via cycle walk
```

- **Sort moves 4 B per element instead of 70** -- an 17.5x reduction in swap
  traffic, and `idx` (128 MB) fits far better in cache than 2.19 GB of rows.
- **Cost:** +128 MB, plus one permutation pass over the rows.
- **Risk:** the comparator now does a random-access read into `Xt` per
  comparison, so it trades sequential swap traffic for random read traffic.
  **This is why it must be measured, not assumed** -- it is the single most
  likely large win and also the one that could regress.
- **Measure:** wall time of the sort phase alone, plus L1/LLC miss counts if
  `perf` is available (Linux, S8).

**Experiment B -- extract the key, sort key+index pairs.** Strictly better than
A if it works, because it removes the random access.

```cpp
struct KeyIdx { uint32_t key; uint32_t idx; };   // 8 B, cache-friendly
// key = first 3 bytes of the row, big-endian, in the low 24 bits
std::vector<KeyIdx> ks(Xt.size());
for (size_t i = 0; i < Xt.size(); i++)
    ks[i] = { be24(Xt[i].hash), (uint32_t)i };
std::sort(ks.begin(), ks.end(), [](KeyIdx a, KeyIdx b){ return a.key < b.key; });
```

- **8 B per element, fully sequential, integer compare** -- no `memcmp`, no
  indirection during the sort.
- Sets up S1.3 directly: a 24-bit key in a `u32` is a textbook 3-pass radix
  (or one counting pass on the high byte per round).
- **Cost:** +256 MB for `ks`, and one extraction pass.

**Experiment C -- padding control (the null test).** Build with
`TruncatedWidth` forced to 72 and to 128 and re-measure. Neither reaches 1
line, so if either changes sort time materially, the cost is *line count*; if
neither does, the cost is *bytes moved* and only per-round sizing helps. Cheap,
and it disambiguates A and B's results.

### 1.1b How 2.19 GB becomes 7.15 GB

Three multipliers, each verifiable:

1. **`Xt` reserved at full size: 2.19 GB.** `Xt.reserve(init_size)` allocates
   33,554,432 x 70 B up front and the row count does not fall much between
   rounds (that is the birthday-collision property Equihash relies on).
2. **`Xc` is a second full-size buffer: +2.19 GB worst case -> 4.38 GB.** The
   merge writes candidates into `Xc`, then drains them back into `Xt`'s freed
   slots via `posFree`.
3. **`Xc` has no `reserve()`** (`equihash.cpp`: `std::vector<...> Xc;` then
   `Xc.emplace_back`). It grows geometrically, and **during a reallocation the
   old and new buffers are both live**. A double from 1.09 -> 2.19 GB holds
   3.28 GB transiently; on top of a 2.19 GB `Xt` that is ~5.5 GB, and with
   allocator slack, `partialSolns`, and the 134 B final round the measured
   **7.15 GB** [Measured] is fully accounted for.

**The cheapest single fix in this whole document is `Xc.reserve()`** -- and it
is equally valuable as a **measurement**, which is the better reason to do it
first.

As a fix: one line, removes the realloc transient and its copy traffic, V1 only
(it cannot change which solutions are found).

As a measurement target it settles several open questions at once, because it
changes *exactly one thing*:

| Question | What the result tells you |
|----------|---------------------------|
| How much of the 7.15 GB is realloc transient? | Peak should drop to ~4.4 GB. If it does not, the S1.1b model is wrong and the excess is elsewhere |
| Is copy traffic material to wall time? | Realloc copies ~3 GB per round. If time barely moves, S1.2's bandwidth argument is confirmed from a second direction |
| Does peak memory alone unlock threads? | At ~4.4 GB a 16 GB host goes 1 -> 3 concurrent solves (S6.0 Model A) with no other change |
| Is the allocator or the algorithm at fault? | A clean 7.15 -> 4.4 GB says allocator behaviour; a smaller drop says the model is incomplete |

**Record it as its own measurement, not folded into a larger change.** It is
the only single-line experiment in the plan whose result discriminates between
competing explanations, and doing it inside a bundle wastes that.

**7.1 GB for a single-threaded solve is the binding constraint on everything
downstream** [Measured]. Naive multi-core scaling would need ~7 GB per thread:
8 threads would be ~57 GB, which no ordinary mining host has. So the memory
work in S1 is not merely a speed optimization -- **it is the prerequisite for
S3 existing at all**.

### 1.2a The 2016 "144 MB" figure, and why it is not the right comparison

The published (200,9) memory records -- xenoncat 178 MB, tromp 144 MB
[Reported: Requihash `Equihash.md` S3 (out of tree)] -- get quoted against
Zero's 7.15 GB as if the gap were all implementation quality. **Most of it is
not.** Two separate factors, and only one is a defect:

**Factor 1: the parameters are much larger.** Run the *same zcashd algorithm*
at both parameter sets:

| | Zcash (200,9) | Zero (192,7) |
|---|---:|---:|
| `CollisionBitLength` `n/(k+1)` | 20 | **24** |
| `init_size` `2^(cbl+1)` | 2,097,152 | **33,554,432** (16x) |
| `TruncatedWidth` | 262 B | 70 B |
| **`Xt` under this algorithm** | **0.51 GB** | **2.19 GB** |

So zcashd's own solver would need ~0.5 GB at (200,9) -- already 3.5x above
tromp's 144 MB -- and 2.19 GB at (192,7). **The 4.3x Zero/Zcash ratio is the
parameter set**, mostly the 16x larger leaf list partly offset by narrower
rows.

**Factor 2: tromp's algorithm is different, and it does not scale the way the
naive one does.** tromp uses fixed-capacity per-bucket slot arrays sized from
the parameters, not one list of full rows. Computing his own constants
(`RESTBITS=10`, `NBUCKETS=2^(DIGITBITS-RESTBITS)`, `NSLOTS=2^(RESTBITS+2)`,
two hash tables):

| | (200,9) | (192,7) |
|---|---:|---:|
| `BUCKBITS` | 10 | **14** |
| `NBUCKETS` | 1,024 | **16,384** |
| tromp two-table footprint | **~224 MB** | **~3,328 MB** |

That ~224 MB is the right order for the quoted 144-178 MB (the difference is
`SAVEMEM` tuning and the exact `RESTBITS`). But **at (192,7) tromp's own design
needs ~3.3 GB** -- because `BUCKBITS` grows with `DIGITBITS`, so the bucket
count goes up 16x.

**What this means for the plan:**

- **"Get to 144 MB" is not an available target at (192,7).** The honest
  reference point is ~3.3 GB for a tromp-class solver, or ~2.2 GB for `Xt`
  under the current algorithm.
- **The real defect is the excess above `Xt`**, not `Xt` itself: 2.19 GB is
  what this algorithm costs at these parameters, while 7.15 GB is what it
  actually uses (S1.1b). Closing that gap -- `Xc.reserve()`, per-round widths
  -- is a **3x** win, not a 50x one.
- **RESTBITS is a shape knob, not a size knob.** I checked: `NBUCKETS x
  NSLOTS` is **invariant** under `RESTBITS`, because
  `NBUCKETS = 2^(DIGITBITS-RESTBITS)` and `NSLOTS = 2^(RESTBITS+2)`. So at
  (192,7):

  | RESTBITS | NBUCKETS | NSLOTS | total slots | MB |
  |---------:|---------:|-------:|------------:|---:|
  | 8 | 65,536 | 1,024 | 67.1M | 3328 |
  | 10 | 16,384 | 4,096 | 67.1M | 3328 |
  | **12** | **4,096** | **16,384** | 67.1M | 3328 |
  | 14 | 1,024 | 65,536 | 67.1M | 3328 |

  **So 4,096 buckets instead of 16,384 would not save a byte.** What it changes
  is *behaviour*, and there are real reasons to prefer one end:

  - **Fewer, larger buckets (RESTBITS 12+):** fewer bucket headers, better
    streaming within a bucket, fewer partition boundaries -- but a larger
    per-bucket working set that may exceed L2, and coarser parallel
    granularity.
  - **More, smaller buckets (RESTBITS 8-10):** each bucket may fit in L1/L2,
    which is the point of the design, and finer granularity for S3's
    bucket-parallel merge -- but more headers and more boundary handling.

  tromp's default of 10 was tuned for (200,9), where it yields 1,024 buckets.
  At (192,7) the same setting gives **16,384** buckets of 4,096 slots. Whether
  that is right is an **empirical question at these parameters**, and it is
  cheap to sweep: `-DRESTBITS=8/10/12` is a rebuild, not a rewrite. The 2.0x
  over-provisioning (67.1M slots for 33.5M expected rows) is the real memory
  lever, and it is `SAVEMEM`, not `RESTBITS`.

#### Why two hash tables, and what "double buffer" really means

tromp allocates `heap0` and `heap1` and alternates between them. That is
**ping-pong, not duplication**, and his own layout comment
(`equi_miner.h`, "The following table shows the layout of these heaps") makes
the reason explicit:

```
             heap0         heap1
round  hashes   tree   hashes tree
0      A A A A A A 0   . . . . . .
1      A A A A A A 0   B B B B B 1
2      C C C C C 2 0   B B B B B 1
3      C C C C C 2 0   D D D D 3 1
```

Round r reads one heap and writes the other. Once round 1 has consumed the `A`
hashes, that space is reused in round 2 for the shorter `C` hashes **plus their
tree tags** -- so the hash region shrinks each round exactly as the tree-tag
region grows, and the two heaps together stay flat. He describes it as "an
optimized version of xenoncat's fixed memory layout, avoiding any waste".

**Does ping-pong dictate a full second copy? No -- and the arithmetic is worth
doing**, because the intuitive answer is wrong:

| | Slot | Total |
|---|---:|---:|
| `heap0` (rounds 0,2,4,6) | 28 B | 1792 MB |
| `heap1` (rounds 1,3,5) | 24 B | 1536 MB |
| **both** | | **3328 MB** |
| single array sized for the widest round | 27 B | 1728 MB |

**The second heap is 0.86x the first, not 1.0x**, because each heap is sized
for the widest round *it* will ever hold, and the two see different rounds. So
ping-pong costs **1.93x** a single array, not 2x -- and it is only that because
**both must be live during a round**: round r reads one and writes the other,
element by element, with no ordering guarantee that would let the read space be
reclaimed early.

**Why pay it at all?** The alternative is in-place merge (what Zero does with
`posFree`), which requires the merged output to fit in slots already freed by
consumed inputs. That works, but it forces:

- a **single fixed row width** for all rounds, because one array cannot change
  stride mid-flight -- which is precisely the 70 B overcharge (S1.1a); and
- **serialisation of the free/reuse discipline**, since a thread cannot write
  into a slot another thread may not have consumed yet. tromp's separate
  read/write regions are what make his bucket-parallel merge safe with only a
  round barrier.

So the trade is: **in-place saves ~1.9x memory and costs both per-round sizing
and easy parallelism.** At (200,9) with 224 MB either way, ping-pong is
obviously right. At (192,7), 3328 MB vs 1728 MB is a real decision -- and it is
the reason S3 (multi-core) and S1.2 (memory) are coupled rather than
independent.

**Your interleaving idea -- one array of (read,write) pairs instead of two
arrays -- is a real design and worth stating precisely.** Layout
`struct Slot { hash_r[W0]; hash_rp1[W1]; }` at a single stride, so each round
reads field A and writes field B of the *same* cache line.

- **For:** one allocation; the write target is in a line already fetched for
  the read, potentially halving line traffic; no second TLB working set.
- **Against:** the stride becomes W0+W1 permanently, so it carries the *sum* of
  two rounds' widths for the whole solve -- roughly the 1.93x back again. And
  it only helps if the read and write indices coincide, which they do **not**:
  a round reads bucket *i* and writes to bucket *j = f(hash)*, scattered. The
  write lands in a different slot than the read, so the "already fetched line"
  benefit largely evaporates.
- **Verdict:** attractive for a *streaming* transform, not for the
  scatter-by-hash that Equihash's merge actually performs. Worth a paragraph
  here so it is not re-proposed, not worth building without a measurement
  showing read/write locality that the algorithm does not obviously have.

**On "Zero executed the same idea worse" -- that was too glib, and here is the
precise version.** Zero and tromp made *different* trades, not better and worse
ones:

| | Zero | tromp |
|---|---|---|
| Second buffer | `Xc`, transient merge scratch | `heap1`, persistent ping-pong |
| Row width | fixed 70 B, all rounds | per-heap 28/24 B, hash shrinks as tags grow |
| Memory | 2.19 GB (`Xt`) + `Xc` | 3.33 GB both heaps |
| Parallel merge | hard (`posFree` reuse is serial) | natural (disjoint read/write regions) |

Zero's design is **more memory-frugal in principle** and pays for it in fixed
row width and serial merge. What is unambiguously a *defect* rather than a
trade is narrower: **`Xc` is unreserved** (S1.1b), so it reallocates and
transiently doubles -- giving neither in-place's frugality nor ping-pong's
parallelism. Fixing that one line moves Zero to ~4.4 GB and makes the
comparison honest; the rest is a genuine design choice to be made on measured
evidence.

**The tree tags in tromp's layout are the index-pointer representation**
(PLAN.md S1.2a). His design gets the space win *and* the ping-pong from one layout, so
adopting either alone captures less than half -- an argument for evaluating a
port rather than incrementally patching `Xt`/`Xc`.

Revised target: **under 1 GB** is ambitious but plausible via per-round widths
plus index pointers; **~2 GB** is the realistic near-term figure once the
allocation waste is removed. Neither is 144 MB, and a plan that promises 144 MB
at (192,7) is promising something the parameters forbid.

---

## 2. Parameter shape: why (192,7) is not (200,9)

Most published Equihash optimization targets Zcash's (200,9). Zero's (192,7)
differs in ways that change which techniques pay:

| | Zero (192,7) | Zcash (200,9) | regtest (48,5) |
|---|---|---|---|
| Collision bits `n/(k+1)` | **24** | 20 | 8 |
| Initial list size `2^(n/(k+1)+1)` | **33,554,432** | 2,097,152 | 512 |
| Indices per solution `2^k` | **128** | 512 | 32 |
| Merge rounds `k` | 7 | 9 | 5 |

Three consequences:

- **The leaf list is 16x larger than Zcash's** (33.5M vs 2.1M). Leaf
  generation and the first merge round matter proportionally more, which
  raises BLAKE2b's share relative to (200,9) profiles.
- **Fewer, wider rounds.** 7 rounds instead of 9, with 24-bit collision keys
  instead of 20-bit. A 24-bit key is still small enough for radix/bucket
  sorting, but the bucket table is 16x wider -- bucket sizing must be
  re-derived for (192,7), not copied from a (200,9) solver.
- **Solutions carry 128 indices, not 512**, so index bookkeeping is a smaller
  share of memory than at (200,9) -- but 33.5M leaves means the *leaf* array
  dominates instead.

**Do not port (200,9) constants blindly.** Bucket counts, table widths and
memory sizing all follow from `n/(k+1)`, and every one of them differs.

---

## 2a. Parallel projects: who else runs non-default Equihash

Surveyed in the local reference clones (`ZKs/`), because the useful question is
not "who ran (192,7)" but "whose solver can be pointed at it".

| Project | Params instantiated | Solver | (192,7)? |
|---------|--------------------|--------|----------|
| **Zero** (this tree) | (192,7), (48,5) | own `OptimisedSolve` | **yes, in production** |
| **Ycash** | 96/3, 200/9, 96/5, 48/5, 144/5, **192/7** | same zcashd-lineage template | **yes, instantiated** |
| Zclassic | 96/3, 200/9, 96/5, 48/5 | same lineage | no |
| Zcash | 200/9 | zcashd + vendored tromp | no |
| tromp upstream | `#define WN 200 / WK 9` | own, pthreads + AVX2 BLAKE2 | **reachable, see below** |
| BTCGPU-equihash | `WN 200 / WK 9` | tromp fork + **CUDA** | reachable, same caveat |

Three findings that matter for the plan:

**1. Ycash instantiates (192,7) with a byte-identical row-width formula.**
`ycash/src/crypto/equihash.h:209` has the same
`TruncatedWidth=max(HashLength+..., 2*CollisionByteLength+...*(1 << (K-1)))`
expression as Zero. So Ycash carries the same fixed-70-byte overcharge at
(192,7) -- it is a **shared lineage defect, not a Zero bug**, and any fix is
portable back to that lineage. Ycash is the closest thing to a peer
implementation to compare against.

**2. No local reference solver branches on (192,7)** -- tromp and
BTCGPU-equihash are both `WN==200 && WK==9` at compile time. But the
constraint is softer than it looks: tromp's `equi.h` derives everything
generically (`NDIGITS = WK+1`, `DIGITBITS = WN/NDIGITS`), and the
`#if WN==200 && WK==9` block contains *unrolled specializations* (`digit1`..
`digit9`) with an `#else` generic loop
(`for r in 1..WK: digitodd(r) / digiteven(r)`) for arbitrary parameters. So
**(192,7) is reachable by recompiling with `WN 192 / WK 7`**, losing the
unrolled fast path but keeping the structure, the pthread barriers, and the
AVX2 BLAKE2 backends. That is the cheapest route to a second independent
(192,7) solver and a cross-check oracle.

**3. BTCGPU-equihash is the nearest GPU prior art** -- a tromp fork with
`equi_miner.cu` and `blake2b.cu`, plus the same generic/unrolled split. It is
the reference to read for S4, not to port verbatim.

**Zebro** (Zebra lineage, Rust) is the counter-example worth recording: its
verifier is fully parametric (`is_valid_solution(n, k, ...)`), but its pinned
`equihash-0.3.0` crate ships **`solve_200_9` only**, from tromp's `690fc5e`
(2016-10-20) -- frozen 28 days before his own bucket-count optimization,
with threading deliberately removed in 2024 for Windows compatibility.
Verified in the vendored crate: zero Cantor-coding matches, zero pthread
matches, hardcoded `#define WN 200 / WK 9`. So that lineage has regressed to a
more primitive solver than either Zero's or tromp's current upstream, and is
not a source to borrow performance from -- though its parametric *verifier* is
the right shape.

---

