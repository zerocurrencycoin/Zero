# Equihash (192,7) -- the two solvers Zero ships

**Subject: which solver runs, where it came from, and how the two compare.**
Zero ships `EhOptimisedSolve` (the `default` solver, inherited from zcashd) and
a vendored copy of tromp's solver (`src/pow/tromp/`), which
`contrib/conf-templates/prod.conf` selects.

**Inclusion rule.** A section belongs here if it answers *"which solver, from
where, and how do they compare?"* Data-structure internals are `SOLVER.md`;
what to build is `PLAN.md`; how to validate is `METHOD.md`.

Entry point for the whole set: `README.md`.

---

## 1. Lineage: how Zero got these solvers

### 1.1 `EhOptimisedSolve` is upstream, frozen at 2016-06

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

### 1.2 The row-width formula is identical across the family

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

### 1.3 Zero also ships tromp, configured for (192,7)

Earlier sections of this document treated a tromp port as prospective work
(`FINDINGS.md` S2a calls it "reachable by recompiling"; `SOLVER.md` S2.3 derived a RESTBITS constraint
for a hypothetical port). **That understated what is already in the tree.**

`src/pow/tromp/` exists in Zero, exactly as in current Zcash
(`src/miner.cpp:8`), and is compiled at **`WN 192 / WK 7`**
(`src/pow/tromp/equi.h:20,24`). `miner.cpp:539` dispatches on
`-equihashsolver`, and **`contrib/conf-templates/prod.conf` sets
`equihashsolver=tromp` by default.**

Its constants land exactly where `SOLVER.md` S2.3's arithmetic predicted a port would have
to sit:

| | Value |
|---|---|
| RESTBITS | **4** (`SOLVER.md` S2.3 derived: must be <= 6) |
| BUCKBITS | 20 -> 1,048,576 buckets |
| SLOTBITS | 6 -> SLOTRANGE 64 |
| tag width | 20 + 2x6 = **32 bits exactly** |
| CANTOR | **not defined** -- pre-Cantor vintage |

This is independent confirmation of the 32-bit wall: the vendored copy sits at
RESTBITS=4 because that is what fits, not by tuning preference.

**What this changes:**

- The (192,7) memory and sort analysis in S1/`SOLVER.md` S3 describes
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

## 2. Measured: tromp vs default

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

## 3. What updating the vendored copy would buy

Zero's `src/pow/tromp/` is **608 lines against upstream's 1,160**. The gap is
**not** three cleanly missing features -- a first pass by macro-diff overcounted
it. Enumerated properly [Verified, source diff]:

| Upstream construct | In Zero? | What it is |
|--------------------|----------|------------|
| **`NBLAKES` / `blake2bip`** | **ABSENT** | 4-way interleaved AVX2 BLAKE2b. **Real, and the one that matters** |
| **`ASM_BLAKE`** | **ABSENT** | xenoncat's 4-way x86 assembly BLAKE2b, via C binding. Real; x86-only |
| **`CANTOR`** | **ABSENT** | Cantor slot-pair packing. Real, but **inapplicable** at (192,7) (`SOLVER.md` S2.3, `SOLVER.md` S2.2) |
| `XBITMAP` | absent | **Not a loss.** Upstream comments it "might as well be obsoleted as it performs worse even in that case"; capped at 64 slots |
| `ATOMIC` | **present, renamed** | Zero has it as `EQUIHASH_TROMP_ATOMIC` and **builds with it on** (`src/Makefile.am:384`) |
| `TREEMINBITS` / `tree_t` typedef | absent, **no effect** | Upstream selects `u16` or `u32` by width; Zero hardcodes `u32 bid_s0_s1`. At (192,7) the tag needs 32 bits (`SOLVER.md` S2.3), so `u32` is the only correct choice anyway |
| `HIST` / `SPARK` | present | Bucket-size histogram debug output |

So the honest count is **two applicable absences, both BLAKE2b batching**, plus
Cantor which is absent and should stay absent. The vendored copy is not a
crippled subset -- it is the same algorithm with the same tree tags, the same
bucket structure, the same atomics, and a **scalar** hash loop
(`digit0`, `equi_miner.h:386`: one `crypto_generichash_blake2b_*` call per
block, libsodium, no batching).

Which of these matter at (192,7) is not the same question as which mattered at
(200,9), and the answer is decided by one measurement.

### 3.1 Leaf generation is 67% of runtime

Timing `digit0` (all the BLAKE2b) separately from the merge rounds, vendored
tromp, (192,7) [Measured, `test-logs/tromp-genshare-20260826/`, n=3]:

| nonce | total s | gen s | **gen share** |
|------:|--------:|------:|--------------:|
| 0 | 10.01 | 6.25 | 62.4% |
| 1 | 9.20 | 6.44 | 70.0% |
| 2 | 8.73 | 6.05 | 69.3% |

**mean 67.3% generation, 32.7% merge.**

Compare tromp's own figure at (200,9): *"my solver was spending 45% of runtime
on hashing"* -- the observation that prompted him to ask xenoncat for an
assembly BLAKE2b binding. **At (192,7) it is 67%**, and the reason is
structural: the leaf list is **16x larger** (33.5M vs 2.1M rows, so 16.8M vs
1.05M blake2b calls) while the merge has **fewer rounds** (7 vs 9). The
parameter set shifts work from merge into hashing.

**Amdahl ceiling: 3.05x** if hashing were free.

### 3.2 Ranking the missing features

| Missing feature | Phase | Est. overall | Applies at (192,7)? |
|-----------------|-------|-------------:|---------------------|
| **Multi-way BLAKE2b** (`blake2bip`, `NBLAKES=4`, AVX2) | generation, **67%** | **1.5-2.0x** | **Yes -- and worth more than at (200,9)** |
| ASM BLAKE2b (xenoncat 4-way) | generation, 67% | similar, x86 asm only | Yes, but not on arm64 |
| **Cantor** | merge, 33% | **~1.02x** | **No -- fails the 32-bit fit** (`SOLVER.md` S2.3) |
| Bucket-count reduction (2^16 -> 2^12 at (200,9)) | merge, 33% | small | **Already there**: vendored `RESTBITS 4` gives 2^20 buckets, forced by `SOLVER.md` S2.3 |
| XBITMAP | merge | none | **No** -- upstream calls it obsolete and slower |
| `tree_t` width selection | merge | none | **No** -- `u32` is forced at (192,7) regardless |

**Both real absences are the same thing: batched BLAKE2b.** `NBLAKES`/
`blake2bip` (AVX2 intrinsics) and `ASM_BLAKE` (xenoncat assembly) are two
implementations of one idea -- hash 4 blocks per call instead of 1. That is why
the ranking collapses to a single question.

**Multi-way BLAKE2b is the whole prize.** Hashing 4 lanes at once against a
67% share yields 1.5-2.0x overall depending on realised lane efficiency; the
same change at (200,9)'s 45% share would yield only 1.3-1.5x. **This is the
rare case where Zero's unusual parameters make an upstream optimisation *more*
valuable, not less.**

**Cantor is confirmed dead for Zero from a third direction.** It touches only
the merge (33%), saves 2 bits of a 4-byte tag, and even a generous 5% merge
improvement is **1.017x overall** -- before accounting for the fact that it
cannot fit 32 bits at (192,7) with usable RESTBITS (`SOLVER.md` S2.3) and would force
bucket underfilling the parameters do not permit (`SOLVER.md` S2.2).

### 3.3 Grouping: what the vendored copy does

Zero's vendored tromp does **no sorting at all**, in either stage. Both stages
are insert-based, and both are present:

| Stage | Mechanism | In Zero? |
|-------|-----------|----------|
| **1. Bucket insert** | `getslot(r, bucketid)` -> `nslots[r&1][bucketid]++`, atomic under `EQUIHASH_TROMP_ATOMIC` (built on, `src/Makefile.am:384`) | **Yes, identical to upstream** |
| **2. Within-bucket grouping** | `collisiondata`: group a bucket's slots by their `RESTBITS` "x-hash" so only same-xhash pairs are XORed | **Yes, but the older form** |

**Stage 2 is where the vendored copy is behind, and it is Solardiz's
contribution.** tromp's README credits him for the final pre-deadline speed
boost: *"my 2nd stage bucket sort could benefit from linking rather than
listing xor-able slots"*. Zero has the **listing** form; upstream has
**linking**:

| | Zero (listing) | Upstream (linking) |
|---|---|---|
| Structure | `xhashslots[NRESTS][XFULL]` -- a fixed array per xhash | `xhashslots[NRESTS]` head + `nextxhashslot[NSLOTS]` chain |
| Per-bucket `clear()` | `NRESTS` counters, but the arrays are `NRESTS x XFULL` | `NRESTS + NSLOTS` entries |
| Capacity | **`XFULL` = 16 per xhash; excess is dropped** (`xfull++`) | unbounded within the bucket -- a chain has no cap |
| Bytes cleared/bucket at Zero's params | 16 + 16x16 = **272** | 16 + 64 = **80** |

So linking is both **less clearing work** and **structurally incapable of the
`XFULL` overflow class**.

**Does the missing `XFULL` cap actually cost Zero anything? Measured: no.**
Accumulating the drop counters across all rounds [Measured,
`test-logs/tromp-drops-20260826/`, n=4]:

| nonce | `xfull` | `bfull` | `hfull` |
|------:|--------:|--------:|--------:|
| 0 | **0** | 12 | 67 |
| 1 | **0** | 1 | 91 |
| 2 | **0** | 1 | 98 |
| 3 | **0** | 0 | 361 |

- **`xfull` = 0 on every nonce.** At `RESTBITS 4` a bucket holds 64 slots spread
  over 16 xhash values -- expected 4 per xhash against `XFULL` = 16, so the
  listing array is 4x over-provisioned and never fills. **The linking form's
  correctness advantage is real but does not bind at these parameters.**
- **`bfull` is small but nonzero** (0-12): these are `NSLOTS` bucket overflows,
  i.e. genuinely dropped rows. Linking does not fix this -- it is the bucket
  capacity question (`SOLVER.md` S3.1), not the xhash list.
- `hfull` counts duplicate-hash rejects, which are correct behaviour, not loss.

**Consequence:** adopting linking is a **modest clearing-cost win in the merge
phase (33% of runtime)**, not a correctness fix for Zero. It ranks below
multi-way BLAKE2b by a wide margin.

**A real defect found while measuring this:** `equi`'s constructor never
initialises `xfull`/`hfull`/`bfull` -- only the threaded worker resets them
(`equi_miner.h:585`). A single-threaded caller like `miner.cpp` reads
uninitialised memory if it inspects them before the first reset. Harmless today
because `miner.cpp` assigns before reading, but it is a live trap for anyone
adding diagnostics, and it produced garbage counts in the first run of this
measurement.

### 3.4 BLAKE2b variants and bit-accuracy

Multi-way BLAKE2b (S3.2) is only safe if it produces **bit-identical output**
to what consensus requires. The variants are not interchangeable, and one of
them is a different function.

**What Zero's consensus actually specifies** (`equihash.cpp:39-47`):

| Parameter | Value |
|-----------|-------|
| Personalization | **`"ZERO_PoW"`** + LE32(N) + LE32(K) -- **not** Zcash's `"ZcashPoW"` |
| Digest length | `(512/N)*N/8` = **48 bytes** at (192,7) (Zcash: 50 at (200,9)) |
| Key / salt | none |
| Hashes per blake call | `512/N` = **2** |

The personalization string is a **consensus parameter**: it is mixed into the
BLAKE2b parameter block, so any solver producing Zero-valid solutions must use
`ZERO_PoW`, and a solver ported from Zcash unchanged will silently produce
solutions Zero rejects. Same for the 48-byte digest.

**The variants, and whether each is a drop-in:**

| Variant | Same output as `blake2b`? | Notes |
|---------|---------------------------|-------|
| **`blake2b`** (libsodium, today) | -- the reference | `crypto_generichash_blake2b_init_salt_personal`; scalar |
| **`blake2b` AVX2/NEON kernel** | **Yes, bit-identical** | Same algorithm, vectorised *within* one compression. A drop-in **if** it exposes personalization + arbitrary digest length |
| **`blake2bip` / 4-way interleaved** | **Yes, bit-identical** | Hashes 4 **independent** inputs in parallel lanes. Each lane is an ordinary blake2b; parallelism is across messages, not within one |
| **`blake2bp`** | **NO -- different function** | A *tree/parallel mode* with a different output for the same input. This is the "semantic gap" tromp's README describes |
| xenoncat 4-way asm | Yes, bit-identical | Same 4-way-independent shape as `blake2bip`, hand-written x86 |

**The `blake2bp` trap is documented in tromp's own history.** His README:
Zooko suggested Samuel Neves' `blake2bp`; he *"initially reject[ed] this
approach due to different blake2bp semantics"*, then *"managed to bridge the
semantic gap and modify Samuel's source to serve Equihash's purposes"* -- i.e.
he took the SIMD machinery and drove it as 4 independent blake2b instances, not
as blake2bp. **Anyone adopting that code must inherit the modification, not the
stock library.**

**How to prove bit-accuracy before trusting any kernel swap:**

1. **KAT first.** `src/test/data/1927EQ.txt` and `1927EQ_h1.hex` pin (192,7)
   vectors; `zero_mainnet_genesis_equihash_192_7_valid` pins the genesis
   solution. A kernel change that breaks these is caught in seconds.
2. **Differential on the hash itself**, not only on solutions: for the same
   `base_state` and block index, assert the new kernel's 48 bytes equal
   libsodium's, over a few million inputs. Cheaper and far more localising than
   discovering it via a missing solution.
3. **Then V2** (`METHOD.md` S3.2): identical solution sets. `METHOD.md` already
   sets **V1 + bit-exact self-test** as the minimum for a BLAKE2b kernel swap,
   for exactly this reason -- a wrong lane silently invalidates every solution
   while looking like bad luck.

**Consequence for S3.2's 1.5-2.0x:** the achievable win is real, but the
adoption path is *not* "link a faster blake2b". It is "obtain a 4-way
**independent** blake2b that supports personalization and a 48-byte digest,
then prove bit-equality." The personalization requirement alone rules out
several stock SIMD implementations that hardcode 64-byte output.

### 3.5 Exact vintage, and Zero-specific modifications

**Full upstream clone obtained** (143 commits, 2016-10-13 to 2018-08-07),
so the chronology below is from git, not from the README narrative.

**Zero runs tromp with modifications -- not stock.** The vendored copy is a
port, and the changes are all integration, not algorithm:

| Change | Why |
|--------|-----|
| `blake2b.h` -> **libsodium** (`crypto_generichash_blake2b_*`) | Uses the node's existing crypto dep instead of tromp's bundled BLAKE2 |
| `setheader()` **removed** | Zero builds `base_state` in `EhInitialiseState` with **`ZERO_PoW`** personalization; tromp's builds it with a caller-supplied string |
| `HEADERNONCELEN` / `POW_HEADER_LENGTH` removed | Zero passes a prepared state, not a raw 140-byte header |
| `WN 200 / WK 9` -> **`WN 192 / WK 7`** | The parameter change |
| `ATOMIC` -> `EQUIHASH_TROMP_ATOMIC` | Renamed to namespace the build flag |
| Include paths, `compat/endian.h` | Tree integration |

**The libsodium swap is the significant one.** It replaces tromp's BLAKE2
implementation -- the same layer his later `blake2bip`/`ASM_BLAKE` work
accelerates. So adopting multi-way BLAKE2b means re-introducing a hashing
backend that was deliberately removed, and re-proving bit-equality against
libsodium's output (S3.4).

**Exact vintage, from git.** Zero has the **listing** form of `collisiondata`
(`xhashslots[NRESTS][XFULL]`), which upstream replaced on **2016-10-27**
(`fc72754`, "change 2nd stage bucketsort to slot linking" -- Solardiz's
contribution). Zero's copy therefore predates that commit:

| Upstream milestone | Date | In Zero? |
|--------------------|------|----------|
| Initial commit | 2016-10-13 | -- |
| **Zero's vintage** | **before 2016-10-27** | -- |
| `blake2bip` prepared | 2016-10-26 | **No** |
| **Slot linking** (Solardiz) | **2016-10-27** | **No** |
| Contest deadline | 2016-11-04 | -- |
| **Cantor** | **2016-11-17** | **No** (and inapplicable, `SOLVER.md` S2.2) |
| ASM_BLAKE / 2^10 buckets | 2016-11-18 | **No** |
| Last upstream commit | 2018-08-07 | **No** |

**81 upstream commits post-date Zero's vendored copy**, and the vintage is a
~2-week-old snapshot from *before* the contest deadline. That is the concrete
answer to "how could the submission be so performant": Zero does not have the
submission -- it has a **pre-submission** snapshot, and still measures 5.7x
faster than `OptimisedSolve`.

### 3.6 Where the 3.3 GB goes

**The measured 3.3 GB is over-provisioning, not row width** [Computed, matches
the 3.3 GB measured in S2]:

| Term | Value |
|------|------:|
| `NBUCKETS` (RESTBITS 4) | 1,048,576 |
| `NSLOTS` (SAVEMEM forced to 1 below RESTBITS 8) | 64 |
| Total slots | 67,108,864 = **2.0x** the 33.5M expected rows |
| heap0 (28 B/slot) | 1.75 GB |
| heap1 (24 B/slot) | 1.50 GB |
| **Both** | **3.25 GB** |

Rows are already narrow (24-28 B against Zero's 70). **The 2.0x slot
over-provision is the dominant term**, and it is forced: at RESTBITS 4 buckets
hold only 64 slots, so relative spread is large (`SOLVER.md` S3.1) and `SAVEMEM 1` is
required. Small buckets are why the vendored configuration is memory-hungry --
and RESTBITS 4 was chosen to fit the 32-bit tag (`SOLVER.md` S2.3), not for memory.

**Path toward the "under 1 GB" target in `PLAN.md` S1.2** [Computed]:

| Step | Peak | Cost |
|------|-----:|------|
| Vendored today (2.0x over-provision) | **3.25 GB** | -- |
| RESTBITS 12 -> 2^12 buckets, 1.045x over-provision (`SOLVER.md` S3.1) | **1.70 GB** | **requires `u64` tag** (`SOLVER.md` S2.5) |
| + single array instead of ping-pong | 0.91 GB | **gives up the parallel merge** (S1.2a) |
| + per-round hash widths | 0.52 GB | tromp already shrinks the hash per round |

**Floor:** a row cannot go below hash + tag. Round 0 needs 24 + 4 = 28 B
(**0.91 GB**); the final round needs 6 + 4 = 10 B (0.33 GB). Since peak is set
by the widest live round, **~0.9 GB is the realistic floor** for a
tag-based solver at (192,7) with tight buckets.

**"<1 GB" is reachable, but only by taking all three steps**, and each has a
distinct cost:

- **~1.7 GB**: bucket retuning plus a `u64` tag. No layout change, ping-pong
  retained.
- **~0.9 GB**: additionally gives up ping-pong -- a different concurrency model
  (below), not just a smaller allocation.

**No target is recommended here, because the right one is deployment-specific.**
Peak memory matters as **GB per concurrent solve on the target hardware**: a
4-core x86 miner with 16 GB, an 8 GB GPU, and this host's large unified memory
imply three different answers, and none of them follow from the algorithm. The
figures above are the menu; picking from it requires knowing the hardware and
the concurrency model, which is a sizing exercise this document does not do.

`PLAN.md` S1.2's "under 1 GB" predates the DAG measurement and should be read as
one point on this menu rather than a goal.

### 3.7 The architecture caveat

Upstream's fast paths are **`blake2-avx2/blake2bip.h`** and xenoncat's x86
assembly. Neither exists for NEON. So on this host the realistic near-term gain
is smaller than 1.5-2.0x, and the honest statement is:

- **x86-64**: 1.5-2.0x is reachable by adopting upstream's existing AVX2 code.
- **arm64**: requires a NEON `blake2bip` equivalent that **does not exist
  upstream** -- new work, not a port.

This is the same architecture split flagged in S1.1a1 and `PLAN.md` S5: NEON is
128-bit and processes 2 lanes where AVX2 does 4, so even a NEON port would
reach roughly half the lane parallelism. **The 67% share is architecture-
independent and measured; the achievable speedup is not.**

### 3.8 What this reorders

1. **Multi-way BLAKE2b in the tromp path** is now the highest-value Equihash
   item -- above every S1.2 memory target, which address the default solver
   production does not select (S2).
2. **NEON blake2b: on hold.** The mining-track share is measured (S3.1), but
   the work itself is deferred -- there is no upstream NEON `blake2bip`, so it
   is new development rather than a port. The measured basis is recorded here
   so the decision can be revisited; it is not a queued item.
3. **Do not port Cantor.** Third independent confirmation.

---

## 4. Cross-implementation survey

Read from the local clones under `~/Work/ZK/ZKs/` (out of tree). The question
is not "who ran (192,7)" (`FINDINGS.md` S2a) but **which structural choices recur**, since a
choice five independent implementations converge on is likely forced by the
algorithm rather than by taste.

| Implementation | Grouping | Tag / back-pointer | Overflow |
|----------------|----------|--------------------|----------|
| **Zero** (this tree) | `std::sort`, comparison | **none** -- accumulates all indices | impossible |
| **tromp** | bucket insert, atomic slot counter | `bid_s0_s1`, 32-bit, **Cantor optional** | **drops** |
| **silentarmy** (OpenCL) | bucket insert, `atomic_add` on row counter | `ENCODE_INPUTS(row,slot0,slot1)`, **plain packing** | **drops**, counted |
| **Khovratovich reference** | direct index into `tupleList[index]`, `filledList` counter | `Tuple::reference` / `Fork{ref1,ref2}` | capacity `FORK_MULTIPLIER` |
| **BTCGPU / nheqminer** | tromp fork | tromp's | tromp's |

### 4.1 What everyone else does that Zero does not

**Nobody else sorts.** Four of five group by **writing rows into a bucket
addressed by the collision digit** -- one pass, `O(m)`, no comparisons. Zero is
alone in paying `O(m log m)` for a total order the merge does not need. That is
the strongest external support for `SOLVER.md` S3.3's counting-sort recommendation.

**Everybody else stores a back-pointer.** All four alternatives keep a fixed
reference to the *parent pair* and reconstruct indices at the end. The
Khovratovich reference -- the paper author's own code -- is explicit about it:
`class Fork { Input ref1, ref2; }` and `Tuple::reference`. **Zero's accumulated
index tail is the outlier**, and it is the direct cause of the 70 B row (S1.1a)
and of round 6 setting peak memory (`SOLVER.md` S2.1).

**Everybody else accepts overflow.** Bucket insert cannot resize, so all three
production solvers drop rows when a bucket fills; silentarmy tracks a `dropped`
counter through every kernel. Zero's in-place merge cannot lose a row. **That
is a real property Zero currently has and would give up** -- worth stating,
because `SOLVER.md` S3.3's counting sort keeps it while bucket insert does not.

### 4.2 Cantor is the minority choice

Of the implementations using a `(row, slot0, slot1)` tag, **only tromp packs
with Cantor**, and there it is an `#ifdef` added late. silentarmy uses plain
shifts and masks, hand-specialised per configuration
(`input.cl:385-406`), with one variant even noting "1 spare bit" rather than
reaching for a denser encoding. This corroborates `SOLVER.md` S2.2 from a second
direction: the 2 bits are not worth the constraint chain, and the field's own
practice reflects that.

### 4.3 Independent confirmation of the sizing model

silentarmy's `param.h` sets bucket overhead by hand per configuration, with
this comment:

> The actual number of elements per row is closer to the theoretical average
> (less variance) when NR_ROWS_LOG is small. So accordingly OVERHEAD can be
> smaller.

That is exactly the `1/sqrt(lambda)` result derived in `SOLVER.md` S3.1, stated
qualitatively. Their tuned constants against the model's 50%-zero-drop capacity
at (200,9), 2^21 elements, 9 rounds [Computed]:

| NR_ROWS_LOG | lambda | their NR_SLOTS | derived capacity | theirs / derived |
|------------:|-------:|---------------:|-----------------:|-----------------:|
| 18 | 8.0 | 24 | 26.1 | **0.92** |
| 19 | 4.0 | 20 | 18.5 | **1.08** |
| 20 (simplified) | 2.0 | 12 | 13.9 | **0.87** |
| 20 | 2.0 | 18 | 13.9 | 1.30 |

**Three of four land within ~10% of the derived target**, from independent hand
tuning. That is meaningful validation of the model in `SOLVER.md` S3.1 -- and the two
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
power of two -- the derived capacity (`SOLVER.md` S3.1) is already an awkward number
(8,563 at BUCKBITS=12), and it should be left awkward rather than rounded up to
8,192 or 16,384. **Measure both**, since the effect is real but its magnitude on
a CPU is unverified here.

### 4.4 What this survey changes

| Item | Effect |
|------|--------|
| Counting sort (`SOLVER.md` S3.3) | **Strengthened** -- no other implementation sorts |
| Back-pointer tag (S2b) | **Strengthened** -- universal; Zero is the outlier |
| Cantor (`SOLVER.md` S2.2) | **Strengthened** -- minority choice even among tag users |
| Bucket sizing (`SOLVER.md` S3.1) | **Independently corroborated** within ~10% |
| Overflow tolerance | **New caution** -- Zero has a no-loss property others lack |
