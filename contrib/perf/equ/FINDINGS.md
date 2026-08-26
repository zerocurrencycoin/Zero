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

Both are V2 (differential vs unmodified solver, `METHOD.md` S3.2); neither
changes which solutions are found.

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

---

## 3. Solver mechanism: keys, widths, and where the constants live

How the collision key, the row widths and the comparator length actually
behave in `OptimisedSolve`. Read this before changing any of them; the task
steps that consume it are `../docs/TASKS.md` D2/D3, which cite this section
rather than restating it.

### 3.1 The collision key

**What the 3 bytes are, exactly.** `CollisionByteLength = (CollisionBitLength
+ 7)/8 = (24+7)/8 = 3`. `ExpandArray` (`equihash.cpp:61`) writes each 24-bit
digit into its own 3 bytes with `byte_pad = 0`, so at (192,7) the digits are
**byte-aligned with no padding** -- 24 bits is exactly 3 bytes, no bit shifting
at read time. This is a property of (192,7), not of Equihash: at (200,9)
`CollisionBitLength` is 20 and the same expansion pads into 3 bytes with 4 bits
wasted. A (200,9)-derived constant would be wrong here.

**Why the key is always at offset 0.** The merge constructor
(`equihash.cpp:299-313`) XORs from `trim` and writes to `hash[i-trim]`, so each
round **shifts the row left**, discarding the digit just consumed:

```
round r:   [ digit_r | digit_r+1 | ... | indices ]
                 XOR -> zero, trimmed off
round r+1: [ digit_r+1 | ...     | indices ]     <- key back at offset 0
```

So the sort key is the first 3 bytes at **every** round, and `HasCollision`
(`:279`) compares `hash[0..l)`. The row narrows by 3 bytes of hash per round
while the index tail doubles.

**How the 25-vs-70 numbers arise: computed at runtime, but never in the inner
loop.** The distinction matters, because "computed per round" and "computed per
row" differ by a factor of 33.5 million.

Two locals in `OptimisedSolve` carry the per-round shape (`equihash.cpp:519`):

```cpp
size_t hashLen    = HashLength;        // 24 -> 21 -> 18 ... one subtract per round
size_t lenIndices = sizeof(eh_trunc);  //  1 ->  2 ->  4 ... one shift per round
...
hashLen -= CollisionByteLength;        // :594, once per round
lenIndices *= 2;                       // :595, once per round
```

`needed = hashLen + lenIndices` is therefore **derived, not looked up** -- and
updated **7 times per solve**, at the round boundary. Reproduced exactly by
arithmetic on the enums:

| Round | `hashLen` | `lenIndices` | needed | allocated | waste |
|------:|----------:|-------------:|-------:|----------:|------:|
| 0 | 24 | 1 | **25** | 70 | 45 |
| 1 | 21 | 2 | 23 | 70 | 47 |
| 2 | 18 | 4 | 22 | 70 | 48 |
| 3 | 15 | 8 | 23 | 70 | 47 |
| 4 | 12 | 16 | 28 | 70 | 42 |
| 5 | 9 | 32 | 41 | 70 | 29 |
| 6 | 6 | 64 | **70** | 70 | **0** |

`TruncatedWidth = max(HashLength+1, 2*CollisionByteLength + 1*2^(K-1)) = max(25,
70) = 70` is a **compile-time enum** (`equihash.h:179`), evaluated by the
compiler, never at runtime. It is sized for round 6 -- the only round where
waste is zero.

**Where each is used in the hot path:**

| Value | Kind | Touched per | Hot? |
|-------|------|-------------|------|
| `TruncatedWidth` (70) | compile-time enum | never at runtime -- it is the array bound in the type | -- |
| `hashLen`, `lenIndices` | runtime `size_t` local | **round** (7x per solve) | no |
| `CollisionByteLength` (3) | compile-time enum, **laundered** through `CompareSR`'s ctor | **comparison** (~840M per round) | **yes -- this item** |

So the row is `TruncatedStepRow<70>`, a fixed-size type: the 70 is baked into
`unsigned char hash[70]` and there is **no per-row width computation or
lookup** anywhere. The merge constructor does take `hashLen`/`lenIndices` per
row (`:559`), but as already-computed arguments, not recomputed values.

#### Why a constant beats an automatic, when both live in a register

The obvious objection: `hashLen` is an automatic `size_t` and
`CompareSR::len` is a member of a functor `std::sort` copies by value -- both
end up in a **register**, so there is no per-comparison load. That is correct,
and it is *not* what this change is about.

Two things it is not:

- **Not a memory-load saving.** `len` is register-resident across the sort.
  Nothing is fetched per comparison.
- **Not a substitution of `hashLen` for `CollisionByteLength`.** At the round
  sort they are different numbers -- 3 versus the whole remaining hash
  (`equihash.cpp:538` vs `:603`). Swapping them would change what is compared.

What it *is*: **what the compiler can prove about the value.** `memcmp` with a
runtime length is opaque -- the compiler must call a routine engineered for any
size, which spends its opening instructions dispatching on a size it turns out
to be 3. With a literal, `memcmp` is a builtin, and -- decisively -- it becomes
**inlinable into the sort's inner comparison**, which a call never is.

Measured on this host (arm64, clang `-O2`), compiling both comparator shapes:

| Shape | Emitted for one comparison |
|-------|----------------------------|
| Runtime `len` in a register | `stp`/`mov` frame setup, **`bl _memcmp`**, `lsr`, `ldp`, `ret` -- a real call, with a link-register spill and reload |
| `LEN` as a template parameter | 11 instructions, no call: two `ldrh`+`ldrb` pairs, `orr`, **`rev`** byte-swap, `cmp`, `cset` -- the compiler turns the 3-byte compare into a single big-endian integer compare |

**The question that actually decides the item** is whether the constant already
propagates through `CompareSR`'s constructor when `std::sort` inlines
everything -- in which case the fold is already happening and the change
measures null. Compiling the real call shape
(`std::sort(..., CompareSR(CollisionByteLength))`, sort fully inlined):

| Version | `bl _memcmp` call sites in the emitted sort |
|---------|--------------------------------------------:|
| `CompareSR(CollisionByteLength)` -- today | **72** |
| `CompareSRFixed<CollisionByteLength>` | **0** |

So the constant does **not** survive the constructor: passing a compile-time
enum through a `size_t` member launders it, and every one of `std::sort`'s
comparison sites keeps the call. The fold is real and not already being done.

**Generalises past this case:** a compile-time constant passed as a *function
argument* and stored in a member is only a constant to the reader. To be one
for the optimizer it has to reach the use site in the **type**. That is the
whole difference between `CompareSR` and `CompareSRFixed`, and it is why the
2016 template refactor mattered and why missing the comparator cost something.

**Measured: the call is the whole gap.** A standalone repro of the round sort
(70-byte rows, 3-byte key, `std::sort`, clang `-O2`, arm64) at production
round-0 size [Measured, `test-logs/eqsort-20260826/`, n=5]:

| Variant | `bl memcmp` | med s, 2^25 rows | med s, 2^22 rows |
|---------|------------:|-----------------:|-----------------:|
| `CompareSR(CollisionByteLength)` -- today | **72** | **4.490** | 0.500 |
| `CompareSRFixed<3>` | 0 | **2.631** | 0.297 |
| hardcoded `memcmp(a,b,3)` | 0 | 2.642 | 0.297 |
| explicit `key24` integer compare | 0 | 2.631 | 0.294 |

**1.71x on the sort** (1.68x at 1/8 the size, so not a cache artifact), spread
under 4%. Two results beyond the headline:

- **The constant does not survive the constructor.** Passing a compile-time
  enum through a `size_t` parameter launders it; all 72 comparison sites keep
  the call.
- **Once the length is a constant, clang derives the optimal form itself** --
  `ldrh`+`ldrb`, `orr`, `rev`, `cmp`, i.e. a big-endian 24-bit integer compare.
  Hardcoding the literal and hand-writing the key extraction are **within noise
  of the template** (2.642 and 2.631 vs 2.631). Explicit extraction buys
  nothing *for the comparison itself*; its value in Experiment B is avoiding
  the re-read across O(m log m) comparisons, which this microbenchmark does not
  model.

**Bounds on this number.** It is the sort phase alone, not a solve: a solve is
~60 s and this is one phase of one round. It is a standalone binary, not the
tree build -- different flags and `std::sort` instantiation, so the in-tree
gain must be confirmed before it is cited as a solver result. Keys are uniform
random, matching BLAKE2b output. One host, arm64, 128 B line.

**Solve-level, paired and settled** [Measured,
`test-logs/eqsolve-fixednonce-20260826/`]. Applied in-tree (one line,
`equihash.cpp:538`) and measured with a fixed-nonce harness so both arms solve
identical work:

| Nonce | nsols | baseline s | D3 s | ratio |
|------:|------:|-----------:|-----:|------:|
| 0 | 4 | 67.55 | 56.87 | 1.188x |
| 1 | 2 | 55.98 | 43.85 | 1.276x |
| 2 | 3 | 62.06 | 52.55 | 1.181x |
| 3 | 2 | 54.24 | 43.87 | 1.236x |

**mean 1.220x, median 1.212x**, all four nonces improving, `nsols` identical
per nonce in both arms. Total 239.83 -> 197.14 s, 17.8% saved.

**1.22x solve against 1.71x sort is the expected relationship**: the solve also
spends time generating 33.5M leaves and running the merge, neither of which
this change touches. Peak footprint unchanged at 6.6 GB.

**An unpaired estimate of the same change read 1.30x mean / 1.51x median /
1.59x min** -- inflated by a favourable random-nonce draw. Random-nonce spread
is 29-49%; the same nonce re-run repeats to **0.2%**. The lesson generalises:
when the benchmark randomises its input, pair the runs or the input variance
swamps the effect (`METHOD.md` S3.2e).

**The consequence for S1.2.** Per-round sizing is not blocked by any runtime
cost -- the shape is already tracked in two cheap locals. It is blocked by `W`
being a **template parameter**, so a narrower round needs either a different
type per round or a byte array with a runtime stride. That is a typing problem,
not an arithmetic one, and it is why S1.2 proposes the stride.

### 3.2 Widths, templates, and the comparator length

**Where the templates came from, and why `len` survived.** From git history,
which settles the question rather than inferring it:

| Date | Commit | Change |
|------|--------|--------|
| 2016-02-28 | `22ac8e130` | Original validator + basic solver. `StepRow` holds `unsigned char* hash` and a `unsigned int len` member -- **heap pointer, runtime length** |
| 2016-05-06 | `487afa1c9` | `CompareSR` extracted from `operator<`, taking `size_t len` in its constructor |
| **2016-05-07** | **`ded9a873c`** | **`template<size_t WIDTH>`; `hash` becomes `unsigned char hash[WIDTH]` and `len` is deleted from `StepRow`**, pushed into method arguments |

So the templates arrived **one day after** `CompareSR`. `StepRow`'s own `len`
was removed in that refactor -- `IsZero(size_t len)`, `GetHex(size_t len)` --
but `CompareSR`'s copy was not. **The runtime `len` is a leftover from the
pre-template design, not a decision.** That is the honest answer to "why so
much template magic to stick 3 where `this->len` is now": the surrounding code
was already templated on width in 2016 and the comparator simply missed the
sweep.

**Does the length vary?**

| Axis | Varies? | Value |
|------|---------|-------|
| Per **iteration** (comparison) | No | 3 -- constant within a sort |
| Per **round** | No | 3 at every round; the trim keeps the key at offset 0 |
| Per **Equihash params** | **Yes** | `(N/(K+1)+7)/8`: **3** at (192,7), 3 at (200,9) (20 bits, 4 wasted), **1** at (48,5) |

It is constant everywhere except across parameter sets -- and the parameter set
is a compile-time template argument (`Equihash<192,7>`, `Equihash<48,5>`,
`equihash.h:199-200`). So `CollisionByteLength` is **already** a per-
instantiation compile-time enum; `CompareSRFixed<CollisionByteLength>` just
stops laundering it. Both instantiations still work, each with its own constant.

**What `CollisionByteLength` controls, and why it is hot.** It is the width of
one collision digit -- the unit of work per round. It appears in four roles:

| Role | Site | Frequency |
|------|------|-----------|
| **Sort comparator length** | `std::sort(..., CompareSR(CollisionByteLength))` `:538` | **~840M/round** |
| Collision test length | `HasCollision(Xt[i], Xt[i+j], CollisionByteLength)` `:549` | ~33.5M/round |
| Merge trim amount | `TruncatedStepRow{..., CollisionByteLength}` `:559` | per merged row |
| Per-round decrement | `hashLen -= CollisionByteLength` `:594` | 7/solve |

Only the first is hot, and only because `std::sort` does `O(m log m)`
comparisons: 33.5M rows, log2 = 25, so ~840M calls per round and ~5 billion per
solve. Every one currently pays a call into generic `memcmp` because the length
is a runtime member. **That is the entire content of this item** -- the other
three roles already see the enum directly.

**Can `hashLen` come from a lookup table instead?** It could, and it would not
help. `hashLen` is updated **7 times per solve** by one subtract (`:594`); a
table lookup would replace an arithmetic op that costs nothing with a memory
read that costs more. The reason `hashLen` cannot be folded is not its cost --
it is that it is a *runtime* value, so a comparator templated on it would need
a different instantiation per round, which is the per-round-width work (S1.2),
not this item.

The distinction worth keeping: **`CollisionByteLength` is hot and constant**
(fold it); **`hashLen` is cold and variable** (leave it).

**The template, minimally.** Two parameters, and separating them is what makes
this look small rather than clever:

| Parameter | Belongs to | Bound at | Value at (192,7) |
|-----------|-----------|----------|------------------|
| `W` | `StepRow<W>` -- row width | since 2016-05-07 | 70 |
| `LEN` | comparator -- bytes compared | this item | 3 |

`W` is not new and is not changing -- `operator()` is **already** a member
template on `W` in today's `CompareSR`. The only change is `len` moving from a
constructor argument into a template parameter, finishing the 2016 refactor:

```cpp
template<size_t LEN>
struct CompareSRFixed {
    template<size_t W>
    inline bool operator()(const StepRow<W>& a, const StepRow<W>& b) const
    { return memcmp(a.hash, b.hash, LEN) < 0; }
};
```

One member function, no state, no constructor -- **shorter than `CompareSR`**,
which has both. With `LEN` a literal in the instantiated body, `memcmp(a, b, 3)`
is a compiler builtin expanded inline instead of a call.

**`size_t` is 64-bit here** (verified: `sizeof(size_t) == 8`, LP64 on both
arm64 macOS and x86-64 Linux). It is the right type for a length and costs
nothing as a template parameter, since it never exists at runtime. No change
needed.

**Should 25, 23, 28 round up to a multiple of 4 or 8?** Not for alignment, and
the arithmetic says why. Two separate questions get conflated here:

- **Scalar load alignment** -- would matter only if the key were read as a
  `u32`/`u64`. It is not; `memcmp` on 3 bytes does not care. Rounding 25 -> 28
  or 32 for this reason buys nothing today.
- **Cache-line straddling** -- the real cost, and rounding *up* makes it worse
  by adding bytes. Only widths **dividing** the line help: 32 and 64 are
  single-line on both 64 B (x86) and 128 B (Apple) lines; 72 and 88 are worse
  than 70.

So the useful rounding target is **32 for rounds 0-4** (needed 22-28, and 32
divides both line sizes) -- which is per-round sizing, S1.2, gated V2. Rounding
to 8 (24, 32, 48) is second-best: it helps only if a future key-extraction step
does aligned wide loads (Experiment B). **Neither is this item**, which changes
no widths at all.

### 3.2a Collision distribution, and why the list is self-sustaining

The per-round key is 24 bits, so 2^25 rows land in 2^24 buckets:
**lambda = 2.0** rows per key. Keys are BLAKE2b output, so occupancy is
Poisson [Computed]:

| Rows sharing a key | Probability | Keys (of 2^24) |
|-------------------:|------------:|---------------:|
| **0** | **13.5%** | 2,270,549 |
| 1 | 27.1% | 4,541,099 |
| **2** | **27.1%** | 4,541,099 |
| 3 | 18.0% | 3,027,399 |
| 4 | 9.0% | 1,513,700 |
| 5 | 3.6% | 605,480 |
| 6 | 1.2% | 201,827 |
| >=7 | 0.45% | -- |

**A key with 0 or 1 rows yields no pair; a key with j rows yields C(j,2)
pairs.** Expected pairs per key is `lambda^2/2 = 2.0`, so expected pairs per
round is `2.0 x 2^24 = 2^25` -- **exactly the input row count**.

That is the property the whole algorithm rests on: the list neither grows nor
collapses across rounds. It is why `Xt` stays near `init_size` for all 7 rounds
(so `reserve(init_size)` is the right ceiling, D2), and why memory does not
fall as the rounds progress even though each row gets narrower.

It also bounds what a bucket-based rewrite may do: at 13.5% empty and 5.2% of
keys holding 5+, any fixed-capacity scheme must either over-provision or drop
rows -- and dropping rows loses solutions (`METHOD.md` S3.2).

### 3.2b `HasCollision` versus the sort: why only one is worth changing

Both compare the same 3 bytes, in the same round, on the same rows. They differ
by **how many times**:

| | Calls per round | Form | Cost, 2^22 rows, n=5 |
|---|---:|---|---:|
| `std::sort` comparator | `m log2 m` = **8.4e8** | `memcmp`, runtime length -> **call** | **0.314 s** |
| `HasCollision` (`:279`) | `m` = **3.4e7** | hand-written byte loop, **already inlined** | **0.0033 s** |

Two independent factors, and they compound:

1. **25x more calls.** The sort compares every row against ~log2(m) = 25
   others; `HasCollision` walks the sorted list once, comparing neighbours.
2. **Per-call cost.** `HasCollision` is `for (j=0; j<l; j++)` over bytes --
   no library call to fold, so making its length constant is **1.02x**
   [Measured]. The sort's `memcmp` is a call, which is the whole D3 effect.

Measured ratio is **95x**, above the 25x call-count ratio -- the remainder is
the per-call difference.

**Consequence: the sort is the only site in the round loop worth changing.**
That is why D3 is one line rather than a sweep, and why `HasCollision` is
explicitly out of scope despite comparing the identical bytes.

### 3.3 Why the sort is replaceable: size, range, distribution

The fold is a patch on `std::sort`. The reason `std::sort` is the wrong
algorithm here is a property of the data, and all three facts are known ahead
of time rather than measured:

| Property | Value | Consequence |
|----------|-------|-------------|
| **Size** | `init_size` = 2^25 = 33,554,432 rows, fixed every round | No unknown *m*; a static bucket layout is safe |
| **Range** | key is 24 bits -> 2^24 = 16,777,216 distinct values | Small enough to index directly; radix/counting applies |
| **Distribution** | 24 bits of BLAKE2b output | Effectively independent uniform draws |

**Size and range together give the load factor.** 2^25 rows over 2^24 keys is
`lambda = 2.0` -- on average two rows per key, which is precisely the birthday
condition the algorithm needs and why the list does not shrink per round.

**Distribution makes the bucket sizing provable rather than empirical.** Keys
are uniform, so bucket occupancy is Poisson/binomial and the tail is tight.
Splitting the 24-bit key by its high bits:

| Buckets | Key bits used | Rows/bucket (mean) | sigma | +5 sigma | Headroom needed | Bytes/bucket at 70 B |
|--------:|--------------:|-------------------:|------:|---------:|----------------:|---------------------:|
| 256 | 8 | 131,072 | 361 | 132,879 | **1.4%** | 9.2 MB |
| 4,096 | 12 | 8,192 | 90 | 8,644 | **5.5%** | 573 KB |
| 65,536 | 16 | 512 | 22.6 | 625 | **22%** | 36 KB |

Two things follow, and they pull in opposite directions:

- **Fewer buckets are cheaper to provision.** Relative spread is
  `sigma/mean = 1/sqrt(mean)`, so headroom grows as buckets shrink: 1.4% at
  256, but 22% at 65,536. Over-provisioning at 65,536 costs more than the
  cache win is likely to return.
- **More buckets fit smaller caches.** 9.2 MB fits the M4's 16 MB shared L2 but
  not a typical 1-2 MB private x86 L2; 573 KB fits both. **This is the concrete
  reason bucket count is a platform-tuned constant, not a portable one**, and
  it is a prediction B2 can test.

**Collisions within a bucket are the point, not a problem.** Bucketing on the
high 8 bits leaves the low 16 bits unsorted inside each bucket. That is fine
for rounds 0-5: the merge needs rows sharing all 24 bits to be *adjacent*, so
each bucket still needs an inner grouping -- either a second counting pass on
the low 16 bits (2 passes total, `O(m)`) or a comparison sort on the now
cache-resident bucket. What it must **never** do is tromp's fixed-capacity
variant, which **drops** rows that overflow a bucket: at `lambda = 2.0` with 5
sigma headroom that is a one-in-3.5-million event per bucket, but a dropped row
is a lost solution, and lost solutions are exactly what V2 exists to catch
(`METHOD.md` S3.2). A counting sort derives its offsets from an actual count
pass, so overflow is impossible by construction -- **that is why counting sort,
not a hash table, is the right S1.3 step for Zero.**

Sequencing: this section is the argument for **S1.3**, gated **V2** (it changes
grouping order). D3 is the V1 patch that makes the current sort cheaper and
measures how much of its cost is call overhead -- which is what says whether
S1.3 is worth the V2 gate. Do not start S1.3 before D3 reports.
