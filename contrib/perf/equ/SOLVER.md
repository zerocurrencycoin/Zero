# Equihash (192,7) -- solver internals

**Subject: how the two solvers Zero ships actually work**, at the level of
rows, keys, tags, buckets and the constants that size them. Everything here is
computed from the source or measured in this tree.

**Inclusion rule.** A section belongs here if it answers *"how does the solver
represent or process data?"* It does **not** belong here if it answers what to
build (`PLAN.md`), how to validate a change (`METHOD.md`), or what the current
numbers are (`FINDINGS.md`).

Entry point for the whole set: `README.md`.

---

## 1. Keys, widths, and where the constants live

How the collision key, the row widths and the comparator length actually
behave in `OptimisedSolve`. Read this before changing any of them; the task
steps that consume it are `../docs/TASKS.md` D2/D3, which cite this section
rather than restating it.

### 1.1 The collision key

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

### 1.2 Widths, templates, and the comparator length

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

### 1.3 Collision distribution, and why the list is self-sustaining

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
rows -- and dropping rows loses solutions (`METHOD.md` S1.2).

### 1.4 `HasCollision` versus the sort

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

### 1.5 Remaining C++ fold candidates

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
predictability, and the key distribution is computable (S1.3): a comparison
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
inversion (S2.6): a 2016 decision about hardware behaviour, cheap to re-test,
and at least one such decision has already flipped.** Not scheduled; recorded
so the reasoning is not lost.

### 1.6 Why the sort is replaceable: size, range, distribution

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
(`METHOD.md` S1.2). A counting sort derives its offsets from an actual count
pass, so overflow is impossible by construction -- **that is why counting sort,
not a hash table, is the right S1.3 step for Zero.**

Sequencing: this section is the argument for **S1.3**, gated **V2** (it changes
grouping order). D3 is the V1 patch that makes the current sort cheaper and
measures how much of its cost is call overhead -- which is what says whether
S1.3 is worth the V2 gate. Do not start S1.3 before D3 reports.

---

## 1.7 Parameter reference: what each constant is, at all three sets

Every constant below is derived from `(n, k)`; none is independently tunable
except `RESTBITS`, and that only within the range the tag width permits (S2.3).

**Base parameters** -- fixed by the parameter set [Computed]:

| Constant | Meaning | (48,5) | **(192,7)** | (200,9) |
|----------|---------|-------:|------------:|--------:|
| `WN` / `n` | Hash bits the solution must cancel | 48 | **192** | 200 |
| `WK` / `k` | Merge rounds | 5 | **7** | 9 |
| `NDIGITS` = `k+1` | Digits the hash is cut into | 6 | **8** | 10 |
| **`DIGITBITS`** = `n/(k+1)` | **Bits per collision digit** -- the width matched each round | 8 | **24** | 20 |
| `init_size` = `2^(DIGITBITS+1)` | Leaf rows generated | 512 | **33,554,432** | 2,097,152 |
| `PROOFSIZE` = `2^k` | Indices in a solution | 32 | **128** | 512 |

`DIGITBITS` is the one to hold onto: it is **larger at (192,7) than at
(200,9)** (24 vs 20) despite `n` being smaller, because `k` is smaller too.
Everything awkward about Zero's parameters follows from that single fact --
a 16x larger leaf list, and a bucket space 16x wider.

**Bucket geometry** -- derived from `DIGITBITS` and the one tunable,
`RESTBITS` [Computed, at each tree's actual setting]:

| Constant | Meaning | (48,5) RB=4 | **(192,7) RB=4** | (200,9) RB=10 |
|----------|---------|------------:|-----------------:|--------------:|
| **`RESTBITS`** | **Bits left unbucketed** within a digit; the tuning knob | 4 | **4** | 10 |
| `BUCKBITS` = `DIGITBITS-RESTBITS` | Bits selecting the bucket | 4 | **20** | 10 |
| `NBUCKETS` = `2^BUCKBITS` | Buckets per round | 16 | **1,048,576** | 1,024 |
| `SLOTBITS` = `RESTBITS+2` | Bits addressing a slot in a bucket | 6 | **6** | 12 |
| `SLOTRANGE` = `2^SLOTBITS` | Addressable slots | 64 | **64** | 4,096 |
| `SAVEMEM` | Fraction of `SLOTRANGE` actually used | 1 | **1** | 9/14 |
| `NSLOTS` = `SLOTRANGE x SAVEMEM` | **Real bucket capacity** | 64 | **64** | 2,633 |
| tag bits = `BUCKBITS + 2*SLOTBITS` | Must fit `tree_t` | 16 | **32** | 34 (Cantor: 32) |

**How the two halves interact.** `RESTBITS` splits each digit: `BUCKBITS`
chooses the bucket, the remaining `RESTBITS` are the "x-hash" used for
second-stage grouping *within* a bucket (S2.5). Raising `RESTBITS` gives fewer,
larger buckets; lowering it gives more, smaller ones. `NBUCKETS x SLOTRANGE` is
**invariant** under `RESTBITS` -- it only changes the shape, not the total.

**Occupancy, which is what the shape actually controls** [Computed]:

| | (48,5) RB=4 | **(192,7) RB=4** | (200,9) RB=10 |
|---|------------:|-----------------:|--------------:|
| Rows | 512 | 33,554,432 | 2,097,152 |
| Buckets | 16 | 1,048,576 | 1,024 |
| **Expected rows/bucket** | **32.0** | **32.0** | **2,048** |
| Capacity (`NSLOTS`) | 64 | 64 | 2,633 |
| **Over-provision** | **2.00x** | **2.00x** | **1.29x** |

This table is the whole memory story. (200,9) at RESTBITS 10 has ~2,048 rows per
bucket, so relative spread is small and capacity can sit at 1.29x. **(192,7) at
RESTBITS 4 has 32 rows per bucket**, where spread is large and `SAVEMEM 1` is
forced -- costing **2.00x**, which is where the 3.3 GB goes
(`VENDORED.md` S3.6).

And RESTBITS 4 is not a choice: at (192,7) anything above 6 pushes the tag past
32 bits (S2.3). **The memory cost traces directly back to `DIGITBITS` = 24.**

## 2. Tree tags: the DAG representation

Technique #4 (compact index-pointer storage) in the reference implementation,
and what blocks a direct port. Source read locally at
`~/Work/ZK/ZKs/equihash-tromp/equi_miner.h`.

### 2.1 Why the tag replaces accumulated indices

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

### 2.2 Cantor pairing: the arithmetic, and why Zero should not use it

Cantor pairing `c(s0,s1) = s1*(s1+1)/2 + s0` maps an **unordered** slot pair to
one integer, saving **2 bits** over two independent fields. tromp uses it behind
`#ifdef CANTOR`, added 2016-11-17; silentarmy and the Khovratovich reference do
not (S4).

**The 2 bits are conditional.** `NSLOTPAIRS ~ NSLOTS^2/2` must fit
`2^(2*SLOTBITS-2)`, so `NSLOTS <= SLOTRANGE/sqrt(2) = 0.707*SLOTRANGE` --
tromp's source comment, "must be under sqrt(2)/2 with -DCANTOR", enforced by
`static_assert`. **Buckets must be deliberately underfilled**, which is what
`SAVEMEM` does: at (200,9) `SAVEMEM 9/14` = 0.643 gives NSLOTS 2633 of a 4096
range, and the pair count fits.

**Two bits only matter if they cross a storage-class boundary** -- 64 to 32 or
32 to 16. Anywhere else, padding absorbs them. At (192,7) [Computed]:

*Case A, flat array (Zero's current shape):* a tag names a pair of row indices,
25 bits each. Plain = 50 bits, Cantor = 49. **Both land in `u64`. No saving.**

*Case B, buckets:* the boundary is crossed in exactly one configuration --

| RESTBITS | plain | Cantor | Effect |
|---------:|------:|-------:|--------|
| 4 | 32 (`u32`) | 30 | none |
| **6** | **34 (`u64`)** | **32 (`u32`)** | **halves the tag** |
| 8 | 36 | 34 | none -- both `u64` |
| 10 (tromp default) | 38 | 36 | none |

**And that one case fails its own constraint.** At RESTBITS 6, `BUCKBITS` 18
gives 262,144 buckets holding 2^25 rows: mean occupancy 128, sd 11.3. Cantor
caps usable capacity at 0.707 x 256 = **181 slots**, while a 50%-zero-drop
solve needs **188** (S1.1). Expected overflowing buckets: ~2.6 across 7 rounds,
and **every overflow discards rows**, which can lose solutions.

This is structural, not bad luck: tromp's own code forces `SAVEMEM 1` when
`RESTBITS < 8` ("can't save much memory in such small buckets"), because small
buckets have large *relative* spread. **Cantor requires underfilling; small
buckets forbid it; at (192,7) the only RESTBITS where Cantor pays is inside the
range where it is unsafe.**

**Verdict: do not implement Cantor for Zero.** It is optional upstream, absent
from two of three peer implementations, and inapplicable here. The prize for
the DAG is 70 B -> ~10-32 B per row; 2 bits of a 4-byte tag is under 1% of
that, bought with a three-link constraint chain that does not hold.

### 2.3 The 32-bit wall, and tag width options

`TREEMINBITS = BUCKBITS + 2*SLOTBITS` must fit `tree_t`, and the code hard-fails
above 32 with `#error tree doesnt fit in 32 bits`. At (192,7) `DIGITBITS` is 24
rather than 20, so `BUCKBITS` is 4 bits wider for the same RESTBITS
[Computed]:

| Params | RESTBITS | BUCKBITS | SLOTBITS | TREEMINBITS | Fits `u32` |
|--------|---------:|---------:|---------:|------------:|:----------:|
| (200,9) | 10 | 10 | 12 | **32** | yes |
| (192,7) | 4 | 20 | 6 | **32** | yes |
| (192,7) | 6 | 18 | 8 | **32** | yes |
| (192,7) | 8 | 16 | 10 | 36 | **no** |
| (192,7) | 10 | 14 | 12 | 38 | **no** |

**RESTBITS <= 6 is the only range that fits 32 bits at (192,7)** -- which is
why Zero's vendored copy sits at RESTBITS 4 (S5.3), and it is a constraint, not
a tuning choice.

| Option | Effect | Cost |
|--------|--------|------|
| **`RESTBITS <= 6`** (today) | Fits `u32` | 2^20 buckets of 64 slots -- small buckets force **2.0x over-provision** (S1.1) |
| **`u64 tree_t`** | Any RESTBITS | **Blocked: requires reworking `alloctrees()`** -- S2.3a |
| **Split the tag**: bucket implied by position | `2*SLOTBITS` -> `u16` | Row's bucket must be recoverable from where it sits; a layout change |
| Cantor | 2 bits | Does not reach (S2.2) |


### 2.4 DAG vs accumulated indices: the trade

Technique #4 is a **representation** choice: how a row records which leaves
produced it. Both forms are correct; they trade space against indirection.

| | Zero: accumulated indices | tromp/xenoncat: DAG tree tag |
|---|---|---|
| Row stores | every index tag so far, `2^r` of them | one fixed back-pointer to the parent **pair** |
| Width by round | 1, 2, 4, 8, 16, 32, **64** B | **4 B, constant** |
| Crossover | -- | **round 2** (4 B vs 4 B); DAG wins from round 3 |
| Solution readout | already present in the row | walk the DAG, depth `k` |
| Rounds retained | one buffer; `posFree` reuses consumed slots | **all rounds** must stay readable for the walk |

**Pro (DAG):**

- **Row width stops growing.** The accumulated form doubles its index tail every
  round, so it *grows* after round 4 even as the hash shrinks (S1.1a). The DAG
  is flat.
- **Reconstruction is free.** A solution has `2^k = 128` leaves, so the walk
  visits ~127 internal nodes. At 2-5 solutions per nonce that is **~635 node
  visits per solve**, against ~8e8 sort comparisons -- unmeasurable.
- **It enables the parallel merge.** Disjoint read/write regions (ping-pong)
  are what let tromp partition a round across threads; `posFree` slot reuse is
  inherently serial (S1.2a).
- **Measured: it wins decisively.** 6.6 GB -> 3.3 GB (`VENDORED.md` S2), *despite* the
  retention cost below.

**Con (DAG):**

- **All rounds stay live.** The walk reads prior rounds, so nothing can be freed
  until solutions are extracted. Zero's in-place merge frees as it goes. This is
  a real cost -- and the measurement shows the per-row saving (70 B -> ~10-28 B)
  dominates it by roughly 2x.
- **Reconstruction is random-access.** The walk chases pointers across the whole
  working set, so it is cache-hostile -- but at ~635 visits, irrelevant.
- **Correctness risk moves.** With accumulated indices the solution is simply
  read off. With a DAG, a tag-packing bug yields *plausible but wrong* indices.
  `METHOD.md` S1.2 gates index-pointer work at **V2** for exactly this reason:
  the verifier catches invalid output, not silently-wrong reconstruction.
- **Tag width is a hard constraint, not a tunable.** At (192,7) the tag needs
  exactly 32 bits and only `RESTBITS <= 6` fits (S2.3) -- discovered by
  arithmetic and confirmed by the vendored copy sitting at `RESTBITS 4`.

**Implementations, and what each demonstrates:**

| Implementation | Tag | Note |
|----------------|-----|------|
| tromp | `bid_s0_s1`, 32-bit, optional Cantor | Manual packing; **bitfields are now faster** (S2.6) |
| silentarmy | `ENCODE_INPUTS(row,slot0,slot1)` | **Plain packing, no Cantor**; hand-specialised per config |
| Khovratovich reference | `Fork{ref1, ref2}`, `Tuple::reference` | The paper author's own code uses the DAG |
| Zero | none | **The outlier** |

**Verdict: adopt the DAG, skip Cantor.** The structure is universal across
independent implementations including the reference; only the *packing* detail
differs, and the densest packing is the one nobody but tromp uses and which does
not fit Zero's parameters.

### 2.5 Implementation detail and open questions

Recorded so the reasoning is not re-derived. **None are measured**; several are
computable and are computed here.

### The 32-bit constraint: can it be relaxed?

`TREEMINBITS = BUCKBITS + 2*SLOTBITS` must fit `tree_t`. At (192,7)
`DIGITBITS` is 24, forcing `RESTBITS <= 6` (S2.3). Four ways out:

| Option | Effect | Cost |
|--------|--------|------|
| **`RESTBITS <= 6`** (what the vendored copy does at 4) | Fits 32 bits today | 2^20 buckets of 64 slots -- small buckets, so **2.0x over-provision** is forced (`VENDORED.md` S3.6) |
| **`u64 tree_t`** | Any RESTBITS; removes the constraint entirely | **Blocked: requires reworking `alloctrees()`** -- S2.3a |
| **Split the tag**: bucket implied by position, only slots stored | `2*SLOTBITS` = 12-16 bits -> `u16` | Requires the row's bucket to be recoverable from where it sits; a real layout change |
| Cantor | Saves 2 bits | **Does not reach**: 34 -> 32 only at RESTBITS=6, where the fit then fails on capacity (S2.2) |

#### S2.3a `u64 tree_t` does not fit at (192,7): per-round slot capacity

**Attempted twice, both reverted.** The first attempt faulted; the second, after
a type-safe layout rewrite, produced solutions that **did not verify**. Both
have the same root cause, and it is a hard capacity limit rather than a coding
error.

**The layout.** A slot at round r holds
`[tree_0][tree_2]...[tree_r][remaining hash]` -- each even round *prepends* one
tree word into space the shrinking hash has vacated. `alloctrees()` expresses
this as `trees0[r/2] = (bucket0 *)(heap0 + r/2)`, where `heap0` is `u32 *`, so
the offset is r/2 **tree words** -- correct only while `sizeof(tree) == 4`.

**Step 1 -- type-safe rewrite (kept).** Typing the heap pointers `tree *` makes
the pointer arithmetic carry the unit, so the offset stays correct under any
tag width. Verified as a **no-op with the u32 tag**: solution sets byte-identical
(V2). This is a strict improvement and is retained.

**Step 2 -- widen to u64 (reverted).** With the layout now correct, the solver
no longer faults -- and instead emits solutions that fail
`CheckEquihashSolution`. The reason is per-round capacity [Computed]:

| Round | tree words | hash still live | needed | `slot0` (u64 tag) |
|------:|-----------:|----------------:|-------:|------------------:|
| 0 | 1 x 8 | 24 B | 32 B | 32 B -- fits |
| 2 | 2 x 8 | 16 B | 32 B | 32 B -- fits |
| **4** | **3 x 8** | **12 B** | **36 B** | **32 B -- OVERFLOW** |
| **6** | **4 x 8** | **4 B** | **36 B** | **32 B -- OVERFLOW** |

**The hash shrinks by one 4-byte unit every *two* rounds while a tree word is
added every round it is that heap's turn.** With a 4-byte tag the two rates
balance and the slot never overflows; with an 8-byte tag they do not, and rounds
4 and 6 write 4 bytes past the slot into the next slot's tree word -- corrupting
the reconstruction of a *different* row. Hence valid-looking indices that fail
verification.

**This is the real reason (192,7) is pinned to RESTBITS <= 6**, and it is a
stronger constraint than "the tag must fit 32 bits" (S2.3): the tag must fit
32 bits **because the slot geometry cannot absorb a wider one**.

**A wider tag therefore requires widening the slots**, i.e. `HASHWORDS0/1`
gaining a unit -- which costs the memory the wider tag was meant to save. That
is the trade in full:

| | slot0 | slot1 | heaps at 2.0x |
|---|------:|------:|--------------:|
| u32 tag (today) | 28 | 24 | **3.25 GB** |
| u64 tag + widened slots | 40 | 36 | **4.75 GB** |

**So the `u64` path costs +46% memory to enable a bucket retune that was
supposed to save 40%.** The two do not compose, and the "widen the tag, then
raise RESTBITS" sequence is dead at these parameters.

**The assert that now guards it** (kept, and verified to reject `u64` while
accepting `u32`):

```cpp
static_assert(((WK + 1) / 2) * sizeof(tree) + 4 <= sizeof(slot0), ...);
static_assert((WK / 2)       * sizeof(tree) + 4 <= sizeof(slot1), ...);
```

An earlier version asserted only that the slot could hold *all* the tree words
(`32 >= 4*8`), which passes while the layout still overflows -- the residual
hash is what the `+ 4` accounts for. **The weaker assert let a corrupting build
compile**, which is the lesson worth keeping: assert the binding case, not the
aggregate.

#### `u64 tree_t`: what actually changes

**12 code sites reference the type** (an earlier count of 18 included comments
and a `tree_t` typedef the vendored copy does not have):

| Kind | Count | Lines |
|------|------:|-------|
| Definition + 2 constructors | 3 | 75, 78, 81 |
| Struct members (`slot0`, `slot1`) | 2 | 108, 113 |
| Function parameters (`listindices0/1`, `candidate`) | 3 | 236, 248, 256 |
| Constructions | 4 | 420, 474, 530, 553 |

Plus **11 accessor call sites** (`getindex`, `bucketid`, `slotid0`, `slotid1`).

**Why constructors and accessors are separate concerns.** The constructors
*write* the packed field; the accessors *read* it. They fail differently:

- **Constructors** encode `(bid, s0, s1)` into one word. A width change alters
  the shift amounts, and `(bid << SLOTBITS | s0) << SLOTBITS | s1` computed in
  `u32` **silently truncates** before it ever reaches a `u64` field. This is the
  one place a widening goes wrong invisibly.
- **Accessors** decode, inheriting the width from the field; only return types
  need checking. If the constructors are right, the accessors follow.

That asymmetry is why validation targets the encode/decode pair, not either
alone.

**`sizeof(tree)` and the real slot cost** [Measured, compiled]:

| | `u32` tag | `u64` tag |
|---|---:|---:|
| `sizeof(tree)` / `alignof` | 4 / 4 | **8 / 8** |
| `slot0` (tag + 6 hashunits) | 28 | **32** |
| `slot1` (tag + 5 hashunits) | 24 | **32** |

**`slot1` grows by 8, not 4** -- 8-byte alignment forces trailing padding on a
28-byte payload, so unpadded arithmetic understates the cost. Memory:
**3.25 -> 4.00 GB, +0.75 GB (+23%)** at the current 2.0x provision.

Both slots landing on 32 B is otherwise favourable: 32 divides 64 and 128, so
slots stop straddling cache lines (S1.1a1).

**On memory targets generally:** what peak is acceptable is a **deployment**
question -- GB per core on the miner's hardware, or VRAM per GPU instance -- not
a property of the algorithm. This host's large unified memory makes 3-4 GB
unremarkable and tells us nothing about a 4-core x86 box or an 8 GB card. The
figures here are inputs to that sizing, not a target.

#### Validating a tag width change

The failure mode is silent truncation in the constructor, so the gates target
encode/decode rather than solver output:

| Gate | What it proves | Cost |
|------|----------------|------|
| **Round-trip** `(bid, s0, s1)` -> construct -> read all three accessors -> assert equality | Packing, masking and shift-width correctness | Domain at RESTBITS 4 is 2^20 x 64 x 64 = 4.4e9, so **corners** (0, max, max-1 per field) plus a random sweep; seconds |
| **Static assert** `BUCKBITS + 2*SLOTBITS <= 8*sizeof(tree_t)` | The fit, at compile time, replacing `#error` | free |
| **Static assert** `sizeof(slot0)` / `sizeof(slot1)` equal expected | Catches unintended padding -- exactly the `slot1` surprise above | free |
| Leaf-tag identity: `tree(idx).getindex() == idx` | The `tree(u32 idx)` constructor, which stores a raw index rather than a triple | trivial |
| **Cross-solver V2** vs `EhOptimisedSolve` | End to end: identical solution sets | ~1 min, harness exists |

The first and fourth are what a width change specifically needs; the
cross-solver check confirms nothing else moved.

#### Passing `tree` by value: already optimal

`listindices0/1` and `candidate` take `const tree t` **by value**, not by
reference. That looks like a copy but is not, and it is worth stating because
the instinct on seeing a struct parameter is to add `&`.

Compiled, arm64 clang `-O2` [Measured, `test-logs/u64tag-20260826/`]:

| Signature | Emitted |
|-----------|---------|
| `f(const tree32 t)` -- by value | `ubfx`, `and`, `add`, `add`, `ret` -- **5 instructions, no load** |
| `f(const tree32& t)` -- by reference | `ldr w8,[x0]` then the same 4 -- **an extra load** |
| `f(u32 v)` -- raw scalar | **identical to by-value** |

A 4-byte trivially-copyable struct is passed **in a register**, exactly as a
`u32` would be; the wrapper is free. Passing by reference forces it to memory
so the callee can dereference, which is strictly worse.

**This holds at `u64` too**: by-value uses `x0` directly, by-reference adds
`ldr x8,[x0]`. The ABI passes trivially-copyable aggregates up to 16 bytes in
registers on AArch64 and in `rdi`/`rsi` on SysV x86-64, so the same conclusion
should transfer -- though that is inference from the ABI, not a measurement on
x86.

**Consequence for a width change:** no signature changes are needed. `const
tree t` stays correct and optimal at 8 bytes. It would only need revisiting
past 16 bytes, where the ABI starts passing aggregates indirectly.

#### Storing tags separately: possible, and a genuine trade

Structure-of-arrays -- `tree tags[NSLOTS]` plus `hashunit hashes[NSLOTS][W]` per
bucket, instead of interleaved `slot{tree; hash[]}` -- is straightforward.

- **It removes the padding.** Stored separately, `slot1`'s payload costs 8 + 20
  = 28 rather than 32, recovering most of the +23%.
- **It halves merge locality.** The merge scan reads a slot's hash to compute
  the collision and writes the resulting tag. Interleaved, that is one cache
  line; split, it is one line in each of two arrays -- two streams and two TLB
  entries per slot, for the phase that touches every slot every round.

**Padding against locality**, and the merge scan is the hot phase while the
padding is a fixed 12% of `slot1`. Interleaved is probably right, but both
layouts are easy to build and a bucket-scan microbenchmark would settle it
directly rather than by argument.

#### Atomics: why they are there, and what they cost

`getslot()` returns the next free slot index in a bucket. Under
`EQUIHASH_TROMP_ATOMIC` (**built on** in Zero, `src/Makefile.am:384`) that is
`atomic_fetch_add(relaxed)`; otherwise a plain `++`.

**Why atomic:** with `nthreads > 1`, any thread may write any bucket -- the
target is `xorbucketid`, derived from the hash, not from the thread's own
partition. The counter is genuinely shared, and a plain increment would hand two
threads the same slot. `relaxed` suffices because the only requirement is that
each caller gets a distinct index; nothing else is ordered against it.

**Cost, single-threaded** [Measured, isolated, 2^25 increments over 2^20
counters]:

| | Time | Ratio |
|---|---:|---:|
| `atomic_fetch_add` relaxed | 0.036 s | **1.32x** |
| plain `++` | 0.027 s | -- |

David Jaenson's contribution upstream was making this switchable so
single-threaded builds could skip it. Zero compiled it in unconditionally while
running `equi eq(1)` -- paying for a capability it never used.

**Removed from the build** (`src/Makefile.am`: the `-DEQUIHASH_TROMP_ATOMIC`
CPPFLAG is gone; the `#ifdef` sites remain as the switch, with a comment
requiring it be restored in the same commit that passes `nthreads > 1`).

**Correctness: unchanged.** Same 4 nonces, solution sets **byte-identical** to
the atomic build, and `xfull`/`bfull`/`hfull` identical too (0/12/67, 0/1/91,
0/1/98, 0/0/361).

**Timing, and why it is not a clean result:**

| nonce | with atomics | without | ratio |
|------:|-------------:|--------:|------:|
| 0 | 9.827 | 8.673 | 1.133x |
| 1 | 8.743 | 8.140 | 1.074x |
| 2 | 8.682 | 8.110 | 1.071x |
| 3 | 8.789 | 8.197 | 1.072x |

Median **1.073x**. **This is larger than the ~0.2% the isolated microbenchmark
predicts, and the two runs were not taken back to back**, so host state differs
between them. Under `METHOD.md` S3.2g the honest reading is: the change is not
a regression, correctness is preserved, and the apparent 7% **is not
established** -- it is within the range where separate runs on a live host stop
being comparable.

Two candidate explanations, both untested: the microbenchmark isolates the
counter but not its effect on surrounding code scheduling (the atomic is a
compiler barrier for `relaxed` ordering only in a limited sense, but it does
inhibit some reordering around the increment); or the runs simply drifted. **A
paired A/B in one session would settle it**, and is cheap -- but the change is
justified on "unused capability removed, correctness verified" regardless of
whether the 7% survives.

**Under threading the cost changes character** -- contention rather than
instruction overhead. Counters for hot buckets become shared lines bouncing
between cores, and the write scatter targets exactly those lines.

### Reconstruction cost, stated in consistent units

Stated in consistent units, because per-solve and per-solution figures are
easy to conflate [Computed, k=7]:

| Quantity | Per solution | Per solve (5 solutions) |
|----------|-------------:|------------------------:|
| Leaves | 128 | 640 |
| Internal nodes visited | 127 | **635** |
| Child pointer reads (2 per node) | 254 | **1,270** |

Against **840,000,000** sort comparisons per round in `EhOptimisedSolve`
(33,554,432 rows x log2 = 25), reconstruction is **1,270 reads against 8.4e8
comparisons** -- roughly **1.5 parts per million** of one round, and there are
seven rounds.

So there is nothing to optimise here, and the two candidate optimisations are
listed only to close them out: memoising shared subtrees saves a few hundred
reads; widening the tag to store two levels halves depth but doubles tag width
-- a bad trade against S2.5's memory arithmetic.

### Retained buffers: one vs all, and why the walk is cache-hostile

| | Zero (accumulated) | DAG |
|---|---|---|
| Live during merge | **one** array; `posFree` reuses consumed slots | **all rounds** -- the walk reads them |
| Bytes at (192,7) | 33.5M x 70 B = **2.19 GB** (plus `Xc`) | 33.5M x (28 + 24) B across two heaps = **~1.7 GB** |
| Measured peak | **6.6 GB** | **3.3 GB** |

Retaining all rounds costs *less* than one wide array, because the per-row
saving (70 -> ~10-28 B) exceeds the retention multiplier. That is the whole
argument for the DAG in one line.

**Why the walk is cache-hostile, specifically:** each step reads a tag, decodes
a `(bucket, slot0, slot1)`, and jumps to two locations in the *previous*
round's heap -- addresses determined by hash values, so effectively random
across a ~1.7 GB working set. Every step is a likely TLB and LLC miss, and the
two children are unrelated addresses, so there is no prefetchable stride. At
1,270 random reads per solve (above), that is **microseconds against a ~9 s
solve.**

**But the layout is cache-friendly where it matters.** The walk is the
*only* random-access phase; everything else is sequential:

| Phase | Access pattern | Layout consequence |
|-------|----------------|--------------------|
| Leaf generation | append into `bucket[slot]`, bucket chosen by hash | scattered **writes**, but write-combining friendly; one line per slot |
| Merge scan | **linear** over every slot in a bucket | fully sequential, prefetchable |
| Merge write | scatter into `xorbucketid` | same as generation |
| **Reconstruction** | **random**, pointer-chasing | the only hostile phase, and 1e-6 of the work |

**The interleaved layout is the reason.** `slot0 { tree attr; hashunit hash[6]; }`
puts the tag **adjacent to the hash it describes**, so the merge scan -- which
reads the hash to compute a collision and writes the tag of the result -- touches
one cache line per slot, not two. A separate parallel tag array would halve the
merge's spatial locality to save nothing. **Interleaving is right for the 99.9999%
case and wrong only for the walk, which is the correct trade.**

### Gates for wrong indices -- and why the verifier is mostly enough

**Equihash is asymmetric by design: solving is hard, verifying is cheap.** That
is the point of the construction, and it is measured -- `verifyequihash` p50 is
**0.054 ms** (`VENDORED.md` S2). So the verifier *is* a usable gate, and the question is
only what it fails to catch.

**What `CheckEquihashSolution` proves:** the 128 indices are in range, distinct,
correctly ordered, and their hashes XOR to zero at every level. **A wrong
reconstruction cannot pass this** -- if the walk returns the wrong leaves, the
XOR will not vanish. So a tag bug produces a *rejected* solution, not an
accepted bad one.

**What it does not give:** localisation, and detection of *missing* solutions. A
tag bug that corrupts one subtree shows up as "found 3 instead of 4" -- which
looks like a slow nonce, not a defect. That is the failure V2 exists for
(`METHOD.md` S1.2), and it is why the cross-solver differential (`VENDORED.md` S2) matters
more than any new gate.

| Gate | Catches | Cost | Needed? |
|------|---------|------|---------|
| **Existing verifier** (V1) | Any wrong index set | 0.054 ms | **Already sufficient for correctness** |
| **Cross-solver V2** vs `EhOptimisedSolve` | Missing/dropped solutions | ~1 min, harness exists | **Yes -- the real gate** |
| Tag round-trip: pack `(b,s0,s1)`, unpack, assert equality over the full domain | Packing/masking bugs, exhaustively | seconds, offline | **Cheap; do it with any tag change** |
| Per-round count + checksum (`METHOD.md` S3.2d) | Localises a divergence to a round | one pass/round | Only when debugging a known divergence |
| Reconstruct-and-recompute intermediate XORs | A walk returning valid-looking but wrong leaves | ~127 XORs/solution | **Not now** -- the verifier already rejects these |

**Task, if index correctness becomes a concern:** build the
reconstruct-and-recompute gate -- re-derive each level's XOR from the
reconstructed leaves and assert it matches the stored row. It is the only gate
that would localise a walk bug rather than merely reject its output. **Not
justified today**, because no tag-based reconstruction exists in Zero yet and
the verifier rejects bad output regardless. Filed so it is not re-derived if a
DAG lands and reconstruction becomes suspect.

### Is a parallel merge actually feasible?

**Yes structurally, and the vendored copy is already most of the way there** --
but the yield is bounded by a measured number.

Present in Zero's copy: `nthreads` in `equi`, `pthread_barrier_t barry`,
`getslot()` atomic under `EQUIHASH_TROMP_ATOMIC` (**built on**), and the
`digitodd`/`digiteven` loops already stride by `nthreads`. `miner.cpp`
constructs `equi eq(1)` -- **the parallelism exists and is not used.**

The structural bound: merge parallelism scales only the merge. Leaf generation
is a separate phase with its own (much simpler) parallel structure -- independent
hashes into disjoint output buckets. The existing `nthreads` plumbing already
strides both, so whichever phase is worth threading, the expression exists.

**So the feasible near-term step is not writing a parallel merge -- it is
passing `nthreads > 1`** and measuring. That is a one-line change to a code
path that already has barriers and atomics. Whether it is *correct* under
concurrency is the open question, and the 2018 upstream fix ("fix
initialization bug identified by YihaoPeng") is a reason to check rather than
assume.

**What threading does to caching.** Not obviously good, and worth predicting
before measuring:

| Effect | Direction |
|--------|-----------|
| Buckets are partitioned across threads (`bucketid += nthreads`), so each thread scans a **disjoint** set | **Good** -- no false sharing on the scan |
| But the **write** target is `xorbucketid`, chosen by hash, so any thread may write any bucket | **Bad** -- write scatter is now shared across cores; lines ping-pong between L1s |
| `nslots[r&1][bucketid]` is an atomic counter touched by every writer | **Bad** -- contended atomics on shared lines, exactly the slot the write scatter targets |
| Working set is **constant in N** (one solve, shared heaps) | **Good** for capacity, but N threads now share one L2/LLC, so effective per-thread cache shrinks by ~N |
| Generation is embarrassingly parallel, disjoint output buckets aside | **Good** -- independent hashes, no shared read state |

**Prediction: generation should scale near-linearly, the merge should scale
poorly**, because the merge's write pattern makes every bucket a potential
shared line and the slot counters are contended. That is testable with the
existing `nthreads` plumbing and is the reason to measure phases separately
rather than reporting one wall-clock number.

#### What "giving up ping-pong" actually means

Ping-pong is `heap0`/`heap1` with round `r` reading one and writing the other
(S1.2a). Collapsing to a single array saves ~0.8 GB (`VENDORED.md` S3.6) and costs three
things, of which only the first is fundamental:

1. **Disjoint read/write regions disappear.** With one array, a thread writing a
   merged row may overwrite a slot another thread has not yet read. tromp's two
   heaps make "read region" and "write region" statically distinct, which is
   what makes the round barrier sufficient for correctness. In one array, you
   need either a `posFree`-style cursor (Zero's `OptimisedSolve` approach --
   **inherently serial**, and the reason its merge cannot be threaded) or
   per-slot synchronisation, which costs more than the memory saved.
2. **Per-round widths become harder.** Two heaps can have different slot sizes
   (28 B and 24 B here) because each is sized for the rounds it holds. One array
   carries a single stride sized for the widest round -- the same constraint
   that gives `EhOptimisedSolve` its fixed 70 B (S1.1a).
3. **The write is no longer append-only.** Ping-pong writes into a fresh region
   each round; in-place writes must respect what has been consumed, which is
   bookkeeping the barrier currently handles for free.

**So the ~0.9 GB figure in `VENDORED.md` S3.6 is not merely "smaller and slower" -- it is a
different concurrency model.** The saving is real; what it costs is the
structural property that makes a threaded merge expressible at all. Whether
that trade is worth taking depends on the deployment target: a memory-starved
configuration may want the 0.8 GB and never thread the merge, while a
multi-core host wants the two heaps. **It is a sizing decision, not a
correctness or performance one**, and this document should not pick a side.

### 2.6 Bitfields: a 2016 decision compilers have inverted

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

#### A readable tag type

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
(S2.3) a compile-time failure with a readable message rather than a silent
mis-size. **Round-0 tags store a leaf index instead of a pair** -- keep that as
a separate named constructor or a distinct type rather than overloading the
same fields, which is the least readable part of the original.

---

## 3. Bucket capacity and grouping strategy

### 3.1 Deriving capacity from a stated goal

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

### 3.2 Bucket size: safety and cache agree

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

This supersedes the earlier framing in S1.6, which treated bucket count purely
as a cache question and left overflow as a separate concern.

### 3.3 Sorting vs hashing vs approximate grouping

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
   row can be a lost solution** (`METHOD.md` S1.2), so C requires either
   over-provisioning to the `SOLVER.md` S1.1 target or an overflow path.

**Recommended order: B before C.** Counting sort captures 3.8x with **no
correctness risk at all** -- it cannot drop a row, because its offsets come
from an actual count pass. C's further gain is real but buys a class of bug
(silent solution loss) that V2 exists to catch and that would need
over-provisioning to suppress. Take the safe 3.8x first, then measure whether
the residual is worth the overflow machinery.
