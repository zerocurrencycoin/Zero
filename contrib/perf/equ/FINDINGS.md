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

## 2b. Tree tags, Cantor pairing, and the (192,7) 32-bit wall

Technique #4 (compact index-pointer storage) in the reference implementation,
and what blocks a direct port. Source read locally at
`~/Work/ZK/ZKs/equihash-tromp/equi_miner.h`.

### 2b.1 Why the tag replaces accumulated indices

Zero stores every accumulated index tag, so a row grows as the hash shrinks
(S1.1a). tromp stores a fixed back-pointer to the **pair** that formed the row
and reconstructs the 128 indices once, at the end, only for rows that became
solutions:

| Round | Zero: hash + indices | tromp: hash + tag |
|------:|---------------------:|------------------:|
| 0 | 24 + 1 = 25 B | 24 + 4 = 28 B |
| 3 | 15 + 8 = 23 B | 15 + 4 = 19 B |
| 6 | 6 + 64 = **70 B** | 6 + 4 = **10 B** |

Zero's rows grow after round 4; tromp's shrink monotonically. **Round 6 sets
peak memory, and it is irreducible without this change** -- which is why
per-round widths alone cannot lower the peak (S1.1a).

### 2b.2 Cantor pairing: the bit arithmetic

A merged row's two parent slots are **unordered**, so storing them as two
independent fields wastes the half of the code space where `s0 > s1`.
Cantor pairing `c(s0,s1) = s1*(s1+1)/2 + s0` for `s0 < s1` is a bijection onto
a range roughly half as large -- a **2-bit** saving:

```
plain:  bid_s0_s1 = ((bid << SLOTBITS | s0) << SLOTBITS) | s1   // 2*SLOTBITS
cantor: bid_s0_s1 = (bid << CANTORBITS) | c(s0,s1)              // 2*SLOTBITS-2
```

**The 2 bits are not free.** `NSLOTPAIRS ~ NSLOTS^2/2` must fit
`2^(2*SLOTBITS-2) = SLOTRANGE^2/4`, so `NSLOTS <= SLOTRANGE/sqrt(2) =
0.707*SLOTRANGE` -- tromp's source comment, "must be under sqrt(2)/2 with
-DCANTOR", enforced by `static_assert(NSLOTPAIRS <= 1<<CANTORBITS)`.

**Buckets must therefore be deliberately underfilled.** This is what `SAVEMEM`
does. Bucket capacity is `SLOTRANGE = 2^SLOTBITS`, but only `NSLOTS =
SLOTRANGE * SAVEMEM` slots are usable [Computed, (200,9) RESTBITS=10]:

| Quantity | Value |
|----------|------:|
| SLOTRANGE (2^12) | 4096 |
| SAVEMEM | 9/14 = 0.643 |
| **NSLOTS** | **2633** |
| NSLOTPAIRS | 3,467,660 |
| CANTORBITS capacity (2^22) | 4,194,304 -- fits |

Underfilling is safe only because occupancy is tight: his comment notes an
expected bucket size of 512+ has "such relatively small standard deviation that
we can reduce capacity with negligible discarding". The same Poisson property
computed in S3.2a. **Overflow discards rows, and a discarded row is a lost
solution** -- so the margin is a correctness parameter, not just a memory one.

So Cantor is a **conditional** 6% saving on a 4-byte tag, bought with a 36%
bucket-capacity reduction. His own README calls it "a small gain".

### 2b.3 The (192,7) wall: the tag does not fit 32 bits

`TREEMINBITS = BUCKBITS + CANTORBITS`, and the code hard-fails with
`#error tree doesnt fit in 32 bits` above 32. At (192,7) `DIGITBITS` is **24**
rather than 20, so `BUCKBITS = DIGITBITS - RESTBITS` is 4 bits wider for the
same RESTBITS [Computed]:

| Params | RESTBITS | BUCKBITS | SLOTBITS | TREEMINBITS | Fits u32 |
|--------|---------:|---------:|---------:|------------:|:--------:|
| (200,9) | 10 (his default) | 10 | 12 | **32** | yes |
| (192,7) | 4 | 20 | 6 | 30 | yes |
| (192,7) | 6 | 18 | 8 | **32** | yes |
| (192,7) | 7 | 17 | 9 | 33 | **no** |
| (192,7) | **10** | 14 | 12 | **36** | **no** |
| (192,7) | 12 | 12 | 14 | 38 | **no** |

**A tromp port at (192,7) requires RESTBITS <= 6**, far below his tuned 10, or
a 64-bit `tree_t` that doubles tag cost. RESTBITS <= 6 also trips the
`RESTBITS < 8` branch that forces `SAVEMEM 1`, removing the underfill that
Cantor depends on -- so at (192,7) the two settings pull against each other.

**This is a checkable blocker not documented in the plan**, and it should be
resolved before any port is scoped (S2a lists the port as the strongest V5
oracle).

### 2b.4 Alternatives to Cantor for Zero

For Zero the win is 70 B -> ~10 B. Two bits of a 4-byte tag is rounding error
against that, and the constraint chain (Cantor -> underfill -> discard risk)
is real complexity.

| Option | Saving vs plain | Cost |
|--------|----------------:|------|
| **Plain two slot fields** | 0 | None. **Start here** |
| Widen `tree_t` to `u64` | -4 B/row | Simplest (192,7) fix; rows ~14 B, still 5x better than 70 |
| Cantor | 2 bits | Forces `SAVEMEM <= 0.707`; discard risk; **no benefit at (192,7)**, S2b.5 |

### 2b.5 Is Cantor desirable for Zero? No -- and the reason is arithmetic

Cantor saves **2 bits**. Two bits only matter if they move the tag across a
**storage-class boundary** -- 32 bits to 16, or 64 to 32. Anywhere else the
saving is absorbed by padding and buys literally nothing. So the question is
narrow and answerable [Computed].

**Case A -- Zero keeps its flat sorted array (no buckets).** A tag identifies a
pair of row indices; rows number 2^25, so an index is 25 bits:

| | bits | storage |
|---|---:|---|
| plain pair | 50 | `u64` |
| cantor | ~49 | `u64` |

**No change.** Both land in `u64`; Cantor saves nothing at all.

**Case B -- Zero adopts a bucket architecture.** Tag is `bucket + pair-of-slots`,
and the boundary is crossed in exactly one configuration:

| RESTBITS | plain | cantor | Effect |
|---------:|------:|-------:|--------|
| 4 | 32 (`u32`) | 30 (`u32`) | none |
| **6** | **34 (`u64`)** | **32 (`u32`)** | **Cantor halves the tag** |
| 8 | 36 (`u64`) | 34 (`u64`) | none |
| 10 | 38 (`u64`) | 36 (`u64`) | none |
| 12 | 40 (`u64`) | 38 (`u64`) | none |

So there is **one** viable case: RESTBITS=6. **And that case fails its own
constraint.** At RESTBITS=6, `BUCKBITS`=18 gives 262,144 buckets holding 2^25
rows -- mean occupancy **128**, sd **11.3**. Cantor caps usable capacity at
`0.707 x SLOTRANGE` = **181 slots**:

| Quantity | Value |
|----------|------:|
| mean occupancy | 128.0 |
| capacity for a 50% zero-drop solve (S2d.1) | **188** |
| Cantor permits (0.707 x 256) | **181** |
| shortfall | **7 slots -- does not fit** |

(The earlier version of this table used an inherited 5-sigma figure, 185.
Deriving the target properly makes the requirement **stricter**, 188, so the
conclusion is unchanged and slightly stronger.)

Expected overflowing buckets: ~0.37 per round, **~2.6 across 7 rounds**. Every
overflow **discards rows**, and a discarded row can be a lost solution. At ~2
solutions per nonce (S3.2a) that is not a rounding error -- it is exactly the
failure mode V2 exists to catch (`METHOD.md` S3.2).

This is also why tromp's own code forces `SAVEMEM 1` when `RESTBITS < 8`
("can't save much memory in such small buckets"): small buckets have a large
*relative* standard deviation, so they cannot be underfilled safely. **Cantor
needs underfilling; small buckets forbid it. At (192,7) the only RESTBITS where
Cantor would pay is in the range where it is unsafe.**

**Verdict: skip Cantor for Zero.** It is optional in tromp's design and
undesirable in Zero's. The whole prize is 70 B -> ~10-14 B per row; 2 bits of a
4-byte tag is under 1% of that, contingent on a constraint chain
(Cantor -> underfill -> discard risk) that does not hold at these parameters.
Implement plain fields, and revisit only if a measured profile shows tag width
binding -- which the arithmetic above says it will not.

## 2c. Bitfields: a 2016 decision that modern compilers have inverted

`struct tree` (`equi_miner.h:167`) carries the comment:

> formerly i had these bitfields ... but these were poorly optimized by the
> compiler so now we do things "manually"

**That was true in 2016. On the 2026 toolchain it is reversed.** Compiling both
forms, construct-then-read-all-three-fields, clang `-O2`
[Measured, macOS/arm64, `test-logs/cantor-bitfield-20260826/`]:

| Form | Instructions | Emitted |
|------|-------------:|---------|
| Manual pack/unpack (his) | **7** | `lsl`, `orr`, `orr`, `ubfx`, `and`, `add`, `add` |
| Bitfield (rejected) | **5** | `and`, `and`, `and`, `add`, `add` |

The manual form packs the word and immediately unpacks it; the compiler cannot
see through the round trip. The bitfield form never materialises the packed
word, and clang emits `ubfx`/`bfi` natively where a real field extract is
needed. **Clearer and fewer instructions.**

**Platform caveat: arm64 macOS only.** `ubfx`/`bfi` are AArch64 bitfield
instructions. x86-64 has `BEXTR`/`SHRX` under BMI1/BMI2 but different codegen
rules, and GCC's bitfield handling differs from clang's. **x86-64 and GCC are
TBD** -- do not generalise this result. It is the same warning as the cache-line
and page-size findings (S1.1a1): a codegen conclusion from one architecture
predicts nothing about the other.

**Generalisable lesson:** a performance comment that names compiler behaviour
has an expiry date. Zero's tree carries several 2016-era decisions of this kind;
each is cheap to re-test and at least one has already flipped.

### 2c.1 A readable tag type

If the tag is implemented for Zero, the manual `bid_s0_s1` packing is worth
neither its opacity nor (on arm64) its instruction count. Field order is
**bucket first, then slots**, matching the packing order so the bucket id
occupies the high bits: bucket is the coarse key used to address the bucket
array, and keeping it in the high bits means a single shift recovers it,
with no mask. Slots are the low-order detail within that bucket.

```cpp
// Identifies a merged row by the pair of parent slots that produced it.
// One 32-bit word; reconstructed into full indices only at solution time.
struct TreeTag {
    // Low bits first: bit-field allocation order is implementation-defined,
    // so the static_assert below is what actually pins the size.
    uint32_t slot1  : SLOTBITS;   // second parent slot, within the bucket
    uint32_t slot0  : SLOTBITS;   // first  parent slot, within the bucket
    uint32_t bucket : BUCKBITS;   // coarse key: which bucket on the prior layer

    TreeTag() = default;

    TreeTag(uint32_t bucketId, uint32_t s0, uint32_t s1)
        : slot1(s1)
        , slot0(s0)
        , bucket(bucketId)
    {}
};

static_assert(sizeof(TreeTag) == 4, "TreeTag must stay one word");
static_assert(BUCKBITS + 2 * SLOTBITS <= 32, "tag does not fit 32 bits");
```

The two `static_assert`s replace the `#error` and make the (192,7) constraint
(S2b.3) a compile-time failure with a readable message rather than a silent
mis-size. **Round-0 tags store a leaf index instead of a pair** -- keep that as
a separate named constructor or a distinct type rather than overloading the
same fields, which is the least readable part of the original.

## 2d. Bucket capacity: deriving the target instead of inheriting it

### 2d.1 Why 5 sigma was the wrong question

Earlier sizing in this document used **5 sigma**, taken from the convention in
the surrounding literature rather than derived. It is the wrong shape of
target: sigma is a *per-bucket* statement, but what matters is **no bucket
overflowing anywhere, across every bucket and every round**.

State the goal directly: **a 50% chance of losing no row at all over the whole
solve.** With `N = NBUCKETS x 7` independent bucket-rounds, the per-bucket
tolerance is

```
p_bucket = 1 - 0.5^(1/N)
```

and the capacity is the Poisson quantile at `1 - p_bucket`. Poisson is
right-skewed, so a plain normal quantile understates the tail; the figures
below use a Cornish-Fisher correction (`skew = 1/sqrt(lambda)`) [Computed]:

| BUCKBITS | buckets | lambda | z | capacity | overprovision |
|---------:|--------:|-------:|--:|---------:|--------------:|
| 18 | 262,144 | 128 | 5.29 | 188 | **1.468x** |
| 16 | 65,536 | 512 | 4.79 | 621 | 1.213x |
| 14 | 16,384 | 2,048 | 4.44 | 2,250 | 1.098x |
| 12 | 4,096 | 8,192 | 4.09 | 8,563 | **1.045x** |
| 10 | 1,024 | 32,768 | 3.74 | 33,445 | 1.021x |
| 8 | 256 | 131,072 | 3.37 | 132,291 | **1.009x** |

**The 5-sigma convention lands near-correct only at many small buckets** (18
bits needs 5.29) and is increasingly wasteful as buckets grow -- at 8 bits the
honest requirement is 3.37 sigma. Using 5 there would over-provision by ~1.5%
of a multi-GB array for nothing.

**The real lesson is that the cost of safety collapses with bucket size**:
1.468x at 262k buckets versus **1.009x** at 256. Relative spread is
`1/sqrt(lambda)`, so large buckets are nearly free to make safe.

Verified against measurement [Measured,
`test-logs/bucketsort-20260826/`]: at the benchmark's lambda=1024 the model
predicts **1.114x** for a 50% zero-drop target. Observed: 1.045x dropped
0.10%, **1.10x dropped 0.0007%**, 1.20x dropped nothing. Model and measurement
agree.

### 2d.2 Bucket size: safety and cache pull the same way

Cache fit was previously argued as a separate tuning axis from overflow safety.
It is not -- **they agree**. Assuming 32 B rows after per-round sizing:

| BUCKBITS | overprovision | bytes/bucket | Fits |
|---------:|--------------:|-------------:|------|
| 18 | 1.468x | 0.01 MB | L1 |
| 14 | 1.098x | 0.07 MB | L1 |
| **12** | **1.045x** | **0.27 MB** | **L2 (x86 private)** |
| 10 | 1.021x | 1.07 MB | L2 (M-series shared) |
| 8 | 1.009x | 4.23 MB | L2 (M-series only) |

**BUCKBITS=12 is the defensible default**: 4.5% overprovision, and 0.27 MB fits
a 1-2 MB private x86 L2 *and* an M-series shared L2. Below 12 the memory saving
is small (4.5% -> 2.1%) while the working set stops fitting commodity x86 L2.
Above 12 the overprovision cost climbs fast for no cache benefit, since L1 is
already exceeded by the *stream* rather than the bucket.

This supersedes the earlier framing in S3.3, which treated bucket count purely
as a cache question and left overflow as a separate concern.

### 2d.3 Sorting vs hashing vs approximate grouping -- measured

The merge needs rows sharing 24 bits to be **adjacent**. Total order is an
artifact of using a comparison sort to get there. Three strategies, same
workload, 70 B rows, 2^22 rows [Measured, n=3, arm64]:

| Strategy | Passes | Time | vs sort | Produces |
|----------|-------:|-----:|--------:|----------|
| **A** `std::sort` + `CompareSRFixed<3>` (today, post-D3) | O(m log m) | 0.316 s | 1.00x | total order |
| **B** counting sort on the full 24-bit key | 2 (count, scatter) | **0.084 s** | **3.8x** | exact grouping |
| **C** bucket insert on the high 12 bits | 1 (insert) | **0.021 s** | **15.0x** | approximate grouping |

Three conclusions:

1. **Exact grouping is 3.8x cheaper than total order and loses nothing.**
   Counting sort is `O(m)`, needs no layout change, and drops in behind the
   same interface. Its cost is a 2^24-entry count array (64 MB) plus one output
   buffer -- the second buffer Zero already pays for as `Xc`.
2. **Approximate grouping is 15x but is not a drop-in.** Bucketing on the high
   12 bits leaves the low 12 unsorted *within* each bucket, so the merge must
   then group inside the bucket -- either a second counting pass or a
   comparison sort on a now cache-resident bucket. The 15x is the *first* pass
   only; it is not the complete replacement cost.
3. **Overflow is the price of the single pass.** C drops rows when a bucket
   fills: measured 0.10% at 1.045x, 0.0007% at 1.10x, 0 at 1.20x. **A dropped
   row can be a lost solution** (`METHOD.md` S3.2), so C requires either
   over-provisioning to the S2d.1 target or an overflow path.

**Recommended order: B before C.** Counting sort captures 3.8x with **no
correctness risk at all** -- it cannot drop a row, because its offsets come
from an actual count pass. C's further gain is real but buys a class of bug
(silent solution loss) that V2 exists to catch and that would need
over-provisioning to suppress. Take the safe 3.8x first, then measure whether
the residual is worth the overflow machinery.

## 2e. Cross-implementation survey: trees, grouping, and sizing

Read from the local clones under `~/Work/ZK/ZKs/` (out of tree). The question
is not "who ran (192,7)" (S2a) but **which structural choices recur**, since a
choice five independent implementations converge on is likely forced by the
algorithm rather than by taste.

| Implementation | Grouping | Tag / back-pointer | Overflow |
|----------------|----------|--------------------|----------|
| **Zero** (this tree) | `std::sort`, comparison | **none** -- accumulates all indices | impossible |
| **tromp** | bucket insert, atomic slot counter | `bid_s0_s1`, 32-bit, **Cantor optional** | **drops** |
| **silentarmy** (OpenCL) | bucket insert, `atomic_add` on row counter | `ENCODE_INPUTS(row,slot0,slot1)`, **plain packing** | **drops**, counted |
| **Khovratovich reference** | direct index into `tupleList[index]`, `filledList` counter | `Tuple::reference` / `Fork{ref1,ref2}` | capacity `FORK_MULTIPLIER` |
| **BTCGPU / nheqminer** | tromp fork | tromp's | tromp's |

### 2e.1 What everyone else does that Zero does not

**Nobody else sorts.** Four of five group by **writing rows into a bucket
addressed by the collision digit** -- one pass, `O(m)`, no comparisons. Zero is
alone in paying `O(m log m)` for a total order the merge does not need. That is
the strongest external support for S2d.3's counting-sort recommendation.

**Everybody else stores a back-pointer.** All four alternatives keep a fixed
reference to the *parent pair* and reconstruct indices at the end. The
Khovratovich reference -- the paper author's own code -- is explicit about it:
`class Fork { Input ref1, ref2; }` and `Tuple::reference`. **Zero's accumulated
index tail is the outlier**, and it is the direct cause of the 70 B row (S1.1a)
and of round 6 setting peak memory (S2b.1).

**Everybody else accepts overflow.** Bucket insert cannot resize, so all three
production solvers drop rows when a bucket fills; silentarmy tracks a `dropped`
counter through every kernel. Zero's in-place merge cannot lose a row. **That
is a real property Zero currently has and would give up** -- worth stating,
because S2d.3's counting sort keeps it while bucket insert does not.

### 2e.2 Cantor is the minority choice

Of the implementations using a `(row, slot0, slot1)` tag, **only tromp packs
with Cantor**, and there it is an `#ifdef` added late. silentarmy uses plain
shifts and masks, hand-specialised per configuration
(`input.cl:385-406`), with one variant even noting "1 spare bit" rather than
reaching for a denser encoding. This corroborates S2b.5 from a second
direction: the 2 bits are not worth the constraint chain, and the field's own
practice reflects that.

### 2e.3 Independent confirmation of the sizing model

silentarmy's `param.h` sets bucket overhead by hand per configuration, with
this comment:

> The actual number of elements per row is closer to the theoretical average
> (less variance) when NR_ROWS_LOG is small. So accordingly OVERHEAD can be
> smaller.

That is exactly the `1/sqrt(lambda)` result derived in S2d.1, stated
qualitatively. Their tuned constants against the model's 50%-zero-drop capacity
at (200,9), 2^21 elements, 9 rounds [Computed]:

| NR_ROWS_LOG | lambda | their NR_SLOTS | derived capacity | theirs / derived |
|------------:|-------:|---------------:|-----------------:|-----------------:|
| 18 | 8.0 | 24 | 26.1 | **0.92** |
| 19 | 4.0 | 20 | 18.5 | **1.08** |
| 20 (simplified) | 2.0 | 12 | 13.9 | **0.87** |
| 20 | 2.0 | 18 | 13.9 | 1.30 |

**Three of four land within ~10% of the derived target**, from independent hand
tuning. That is meaningful validation of the model in S2d.1 -- and the two
sitting *below* 1.00 are consistent with their design accepting a small drop
rate, which they measure rather than forbid.

One caution their comment adds that the model does not capture: *"Even (as
opposed to odd) values of OVERHEAD sometimes significantly decrease performance
as they cause VRAM channel conflicts."* A capacity that is statistically ideal
can be an alignment pessimum. **Sweep the neighbourhood of the derived value
rather than adopting it exactly** -- the same lesson as the row-width finding,
where 72 B is worse than 70 B (S1.1a1).

#### VRAM channel conflicts vs cache associativity conflicts

These are the **same failure in different hardware**, and the distinction
matters because only one of them applies to Zero's CPU solver.

| | GPU: memory channel conflict | CPU: cache set conflict |
|---|---|---|
| Resource contended | DRAM **channels** (and banks) | Cache **sets** (ways per set) |
| Selector | low-order address bits pick the channel | mid-order address bits pick the set |
| Failure | many concurrent accesses land on one channel; its bandwidth serialises while others idle | more than `ways` live lines map to one set; each eviction is a miss |
| Trigger | a **power-of-two** stride aligns every lane onto the same channel | a stride whose period against `sets x line` is small |
| Typical fix | make the stride **odd** or non-power-of-two -- hence silentarmy's "even values decrease performance" | pad or skew the stride so the set index rotates |

**Why silentarmy hits it and Zero probably does not.** A GPU issues a warp of
32-64 lanes *simultaneously*, each at `base + lane*stride`. If `stride` is a
power of two the low bits are identical across lanes, so every lane addresses
the same channel and the access serialises. An even `OVERHEAD` makes
`NR_SLOTS x SLOT_LEN` power-of-two-aligned, which is exactly that case.

A CPU issues those accesses **sequentially**, so there is no simultaneous
channel contention -- the equivalent risk is associativity. Computed for this
workload [Computed]:

| Cache | sets x line | rows before a set repeats, W=70 | W=32 | W=128 |
|-------|------------:|--------------------------------:|-----:|------:|
| M4 L1d (128 KB, 8-way, 128 B) | 16,384 B | 8,192 | 512 | 128 |
| x86 L1d (48 KB, 8-way, 64 B) | 6,144 B | 3,072 | 192 | 48 |
| x86 L2 (1 MB, 16-way, 64 B) | 65,536 B | 32,768 | 2,048 | 512 |

Every period is far larger than the associativity (8-16 ways), so **a
sequential sweep never conflicts** -- the lines are consumed and retired long
before the set index wraps. This holds for 70 B and for the 32 B target alike.

**Where it could still bite: the scatter.** Counting sort's second pass and any
bucket insert write to `NBUCKETS` cursors at once. If bucket capacity is a
power of two, those cursors are separated by a power-of-two stride, and with
enough live buckets they collide in the same cache sets -- the CPU analogue of
the channel problem, and the reason the same odd-stride fix applies.

**Practical rule for S1.3:** size buckets so the per-bucket span is **not** a
power of two -- the derived capacity (S2d.1) is already an awkward number
(8,563 at BUCKBITS=12), and it should be left awkward rather than rounded up to
8,192 or 16,384. **Measure both**, since the effect is real but its magnitude on
a CPU is unverified here.

### 2e.4 What this survey changes

| Item | Effect |
|------|--------|
| Counting sort (S2d.3) | **Strengthened** -- no other implementation sorts |
| Back-pointer tag (S2b) | **Strengthened** -- universal; Zero is the outlier |
| Cantor (S2b.5) | **Strengthened** -- minority choice even among tag users |
| Bucket sizing (S2d.1) | **Independently corroborated** within ~10% |
| Overflow tolerance | **New caution** -- Zero has a no-loss property others lack |

## 2f. How Zero got this solver -- lineage, and a correction

### 2f.1 Zero did not write it, and has not touched it

Every commit to `src/crypto/equihash.{h,cpp}` predates Zero
[Verified, `git log --follow`]:

| Date | Commit | Change |
|------|--------|--------|
| 2016-02-28 | `22ac8e130` | Original validator + basic solver |
| 2016-04-19 | `5c4bf96f6` | Index-truncation optimisation |
| 2016-05-04 | `479c0d317` | Truncated indices in the same buffer ("H/T tromp for the idea!") |
| 2016-05-06 | `487afa1c9` | `CompareSR` extracted |
| 2016-05-07 | `ded9a873c` | Templates; `hash[WIDTH]`; `len` dropped from `StepRow` |
| 2016-06-01 | `559ceca99` | `HasCollision` branchless -> early exit |

**Nothing after 2016-06-01**, and nothing authored by Zero. The file is
upstream `zcashd` frozen at that point, inherited through the fork. The 70 B
row and the accumulated index tail are **not Zero decisions**; they are the
state of zcashd's own solver when the fork was taken.

### 2f.2 The formula is identical across the family

`TruncatedWidth` is **byte-identical** in Zcash, Zclassic, Ycash and Zero
[Verified, source diff]:

```
TruncatedWidth = max(HashLength + sizeof(eh_trunc),
                     2*CollisionByteLength + sizeof(eh_trunc)*(1 << (K-1)))
```

What differs is only which parameter sets are instantiated:

| Fork | Instantiated |
|------|--------------|
| Zcash | 96/3, 200/9, 96/5, 48/5 |
| **Zclassic** | 96/3, 200/9, 96/5, 48/5, **192/7** |
| Ycash | 96/3, 200/9, 96/5, 48/5, 144/5, **192/7** |
| **Zero** | **192/7**, 48/5 |

**Zclassic already carried (192,7)**, and Zero descends from Zclassic. So Zero
did not add the parameter set to a solver that could not handle it -- it
inherited both. The "unusual implementation" is the **shared** zcashd solver;
what is unusual is only that Zero *runs* it at (192,7) in production, where
`TruncatedWidth` evaluates to 70 rather than 200/9's 262 (S1.2a).

### 2f.3 Correction: Zero already ships tromp, configured for (192,7)

Earlier sections of this document treated a tromp port as prospective work
(S2a calls it "reachable by recompiling"; S2b.3 derived a RESTBITS constraint
for a hypothetical port). **That understated what is already in the tree.**

`src/pow/tromp/` exists in Zero, exactly as in current Zcash
(`src/miner.cpp:8`), and is compiled at **`WN 192 / WK 7`**
(`src/pow/tromp/equi.h:20,24`). `miner.cpp:539` dispatches on
`-equihashsolver`, and **`contrib/conf-templates/prod.conf` sets
`equihashsolver=tromp` by default.**

Its constants land exactly where S2b.3's arithmetic predicted a port would have
to sit:

| | Value |
|---|---|
| RESTBITS | **4** (S2b.3 derived: must be <= 6) |
| BUCKBITS | 20 -> 1,048,576 buckets |
| SLOTBITS | 6 -> SLOTRANGE 64 |
| tag width | 20 + 2x6 = **32 bits exactly** |
| CANTOR | **not defined** -- pre-Cantor vintage |

This is independent confirmation of the 32-bit wall: the vendored copy sits at
RESTBITS=4 because that is what fits, not by tuning preference.

**What this changes:**

- The (192,7) memory and sort analysis in S1/S2d describes
  `EhOptimisedSolve` -- the **`default`** solver. It is what
  `zcbenchmark solveequihash` measures (`src/zcbenchmarks.cpp` calls
  `EhOptimisedSolve` directly) and therefore what the 6.6 GB peak and the D3
  1.22x result apply to.
- **A miner running the shipped `prod.conf` is using tromp, not this code
  path.** The optimisation targets in S1.2 (per-round widths, index pointers)
  address a solver that production configs do not select by default.
- **Priority question, now open:** measure tromp at (192,7) on this host before
  investing further in `OptimisedSolve`. If the vendored solver is already
  materially faster and leaner, the S1 memory work is optimising the wrong
  binary, and the useful work shifts to updating the vendored copy (it predates
  Cantor and his later bucket-count reductions).

### 2f.4 Measured: tromp is 5.7x faster and half the memory

**D5 run** [Measured, `test-logs/tromp-crosscheck-20260826/`, n=4 paired
nonces, arm64, both single-threaded]:

| nonce | nsols | default s | tromp s | speedup |
|------:|------:|----------:|--------:|--------:|
| 0 | 4 | 59.54 | 9.83 | 6.06x |
| 1 | 2 | 45.86 | 8.74 | 5.25x |
| 2 | 3 | 54.38 | 8.68 | 6.26x |
| 3 | 2 | 45.66 | 8.79 | 5.20x |

**mean 5.69x, median 5.65x.** Peak physical footprint **6.6 GB -> 3.3 GB**.

**V5 cross-implementation check PASSED**: sorted solution sets are **identical**
across all 4 nonces. Two structurally different algorithms -- bucket-insert with
tree tags versus comparison sort with accumulated indices -- agree exactly. This
is the strongest oracle in `METHOD.md` S3.2, and it was available without the
port `README.md` assumed was needed.

**No nonce emitted 7 or 8 solutions**, so tromp's `MAXSOLS = 8` cap did not
truncate and the arms are comparable. The harness warns at `rawSols >= 7`; it
did not fire. Counts (2-4) were identical in both arms.

**The 3.3 GB confirms the memory model.** S1.2a computed ~3328 MB for a
tromp-class two-heap solver at (192,7) *without measuring one*. The measurement
matches -- a prediction validated from an independent direction.

**Consequences:**

1. **A default miner is already ~5.7x faster and uses half the memory** than
   every solver figure previously recorded in this tree.
2. **S1's optimisation targets address the slower path.** `Xc.reserve()`,
   per-round widths and index-pointer storage all target `EhOptimisedSolve`,
   which `prod.conf` does not select.
3. **D3's 1.22x stands but scopes to the default solver** -- `zcbenchmark` and
   `equihashsolver=default`.
4. The vendored copy is **pre-Cantor** and predates tromp's later bucket-count
   reductions, so **updating it is now the higher-value line of work** than
   optimising `OptimisedSolve`.

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

### 3.2c Preserved for later review: remaining C++ fold candidates

D3 folded the sort comparator's length (1.22x solve). The same pattern -- **a
compile-time constant reaching the use site as data rather than as a type** --
appears elsewhere in `equihash.cpp`. **None of these are measured**; they are
recorded so the list is not re-derived.

| Site | Pattern | Est. calls/round | Gate |
|------|---------|-----------------:|------|
| `GetTruncatedIndices(len, lenIndices)` | Allocates a `shared_ptr<eh_trunc>` **per candidate row** | ~m | V1 |
| `TruncatedStepRow` ctor `len`/`lenIndices`/`trim` | Three runtime args per merged row; the merge is the second-hottest loop | ~m | V1 |
| `IsZero(size_t len)` | Runtime length, called per merged row (`:554`, `:561`) | ~m | V1 |
| `ExpandArray(bit_len, byte_pad)` | Runtime, generation only | 33.5M x 1 | V1 |
| `HasCollision(a, b, int l)` | Same fold as D3 | ~m + runs | **Measured 1.02x -- declined** |

**Start with `GetTruncatedIndices`.** It is a heap allocation in the merge
inner loop, and D3 established that call overhead in that region is worth ~20%
at solve level. An allocation is more expensive than a call.

#### Why `HasCollision` folded to nothing, and what is still open there

The fold measured **1.02x** [Measured] because there is no call to eliminate:
`HasCollision` is a hand-written byte loop, not a `memcmp`. It was made that
way deliberately -- upstream `559ceca99` (2016-06-01) replaced a **branchless**
form with an early exit:

```cpp
// before 2016-06:                      // after, and still current:
bool res = true;                        // "This doesn't need to be constant time."
for (int j = 0; j < l; j++)             for (int j = 0; j < l; j++) {
    res &= a.hash[j] == b.hash[j];          if (a.hash[j] != b.hash[j])
return res;                                     return false;
                                        }
                                        return true;
```

**Open question, worth re-testing on modern hardware.** That trade assumed an
early exit beats a branchless scan. Whether it still does depends on branch
predictability, and the key distribution is computable (S3.2a): a comparison
mismatches on the **first byte** roughly 255/256 of the time in the
non-colliding case, so the branch is highly predictable -- which favours the
early exit. But within a run of colliding rows all `l` bytes match, and run
lengths follow the Poisson profile (13.5% of keys empty, 27.1% singleton,
27.1% pairs, 5.2% five-or-more), so the branch alternates on run boundaries.

Three variants worth measuring together, all V1 (none can change results):

| Variant | Rationale |
|---------|-----------|
| Early exit (today) | Baseline |
| Branchless `res &=` (pre-2016) | No misprediction; always reads `l` bytes -- only 3 |
| Constant-length `LEN=3` + branchless | Fully unrolled 3-byte compare, no loop, no branch |

At `l = 3` the loop is short enough that the early exit may save nothing while
costing a mispredict. **This is the same class of finding as the bitfield
inversion (S2c): a 2016 decision about hardware behaviour, cheap to re-test,
and at least one such decision has already flipped.** Not scheduled; recorded
so the reasoning is not lost.

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
