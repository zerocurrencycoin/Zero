# Equihash (192,7) -- measurement method

How to measure a solver change, how hard to validate it, and what to record.
The facts being measured are in `FINDINGS.md`; what to build is `PLAN.md`.

Entry point for the whole set: `README.md` in this directory.

---

## 3. Method: regtest (48,5) for correctness, (192,7) for performance

**(48,5) is a correctness gate, never a performance proxy.** 512 leaves versus
33.5M is a **65,536x** ratio; it fits in cache, exercises no memory hierarchy,
and will mislead about every bottleneck that matters.

Use it exactly as intended -- a very quick check that a change is still
correct:

```bash
# seconds, not minutes: does the optimized solver still find valid solutions?
src/test/test_bitcoin --run_test=equihash_tests
contrib/perf/mine_bench.sh regtest        # (48,5) generate, util.tsv
```

Then measure on the real parameters:

```bash
# the real thing: one timed solve, one trial per invocation
contrib/perf/mine_bench.sh mainnet-template   # env stub
MINE_MAINNET_SOLVE=1 contrib/perf/mine_bench.sh mainnet-template
./src/zero-cli zcbenchmark solveequihash 3    # the baseline above
```

**Per-run discipline** (`../docs/POLICY.md` S4): one trial per invocation, no
unrestartable batches, and every result stamped with platform, build and
feature set so a Linux number and a macOS number can be told apart
(`../docs/SCHEMA.md`). A solve takes ~60 s, so a 4-trial comparison is minutes,
not hours -- there is no excuse for an unstamped n=1 claim here.

### 3.1 Two ladders: S = what to build, V = how hard to check it

The document uses two independent scales, and they are easy to confuse because
both are numbered. Stated once:

| Ladder | Means | Values |
|--------|-------|--------|
| **S** | **Stage** of optimization -- *what* to build, in order | S1 single core -> S2 SIMD -> S3 multi-core -> S4 GPU |
| **V** | **Validation** level -- *how hard* to check a change | V0 (seconds) -> V5 (cross-implementation) |

They are orthogonal: an S1 change and an S4 change can both need V2, and a
one-line S1 change may need only V1. `S1.1`/`S1.2` are *sub-steps within
stage 1*, not validation levels.

Full stage list, so "S1-S4" is never ambiguous:

| Stage | Scope | Section |
|-------|-------|---------|
| **S0** | Profile (192,7); establish an x86-64 Linux baseline | S9 |
| **S1** | Single core: memory layout, sort, allocation, BLAKE2b check | S4 |
| **S1.1** | Profile before changing anything | S4 |
| **S1.2** | Cut peak memory (`Xc.reserve`, per-round widths, index pointers) | S4 |
| **S1.3** | Replace comparison sort with radix/bucket | S4 |
| **S1.4** | Pointed BLAKE2b work, only if the profile justifies it | S4 |
| **S2** | Special instructions on one core: AVX2, AVX-512, NEON | S5 |
| **S3** | Multiple cores | S6 |
| **S4** | GPU: CUDA, OpenCL, Metal | S7 |

### 3.2 Validation level per optimization step

How far to validate depends on how far a change can silently corrupt results.
A miner that emits *invalid* solutions wastes work without erroring, so the
gate must scale with the risk, not with the effort.

Each level *includes* every level below it.

**V0 -- does it still compile and find anything?**
`src/test/test_bitcoin --run_test=equihash_tests` (the (48,5) and (192,7)
KATs, `src/test/data/1927EQ*`) plus a regtest (48,5) solve. Seconds. Catches
gross breakage: wrong widths, off-by-one in the merge, a solver that returns
nothing. **Run on every edit, always.**

**V1 -- is each solution actually valid?**
V0 plus feeding every emitted solution back through the *unmodified* verifier
(`CheckEquihashSolution`). Seconds. Catches a solver that emits plausible-looking
but invalid index sets -- the failure mode that costs a miner real work while
looking like bad luck. **Required for any hash-kernel change**, where a wrong
SIMD lane silently invalidates everything.

**V2 -- does it find the SAME solutions?**
V1 plus a differential run: same `base_state`, old and new solver, compare the
*sorted solution sets* for equality. Minutes. This is the gate that catches an
optimization which is fast because it **drops** solutions -- faster wall-clock,
lower Sol/s, and invisible to V0 and V1. **Required for anything touching row
layout, sort order, or merge grouping.**

**V3 -- does it work at production scale?**
V2 plus one full (192,7) solve whose solution `CheckEquihashSolution` accepts.
1-2 min. (48,5) exercises no memory hierarchy, so V0-V2 can all pass on a
change that breaks at 33.5M rows. **Required before recording any performance
number.**

**V4 -- is the speedup real?**
V3 with n>=4 trials, stamped with platform/build/features and appended to the
ledger, with `phys_mb` sampled. ~10 min. The recorded baseline spans
54.2-69.0 s (27%), so fewer trials cannot separate a 20% win from noise.
**Required before claiming a speedup.**

**V5 -- does an independent implementation agree?**
V4 plus a second implementation producing the same solution set: a Ycash build
(same lineage, already instantiates (192,7)) or tromp recompiled at
`WN 192 / WK 7`. Hours. **Required only before shipping to mainnet miners.**

**The load-bearing rule: never accept a solver that finds *fewer* or
*different* solutions.** An optimization that drops solutions looks like a
speedup on wall-clock and is a loss in Sol/s. V2 is the gate that catches it,
and it is cheap -- run the two solvers on the same `base_state` and compare
the emitted index sets.

Mapping to the stages:

| Change | Minimum gate | Why |
|--------|--------------|-----|
| Per-round row sizing (PLAN.md S1.2) | **V2** | Alters memory layout; must not change solutions |
| Index-pointer storage (PLAN.md S1.2) | **V2** | Reconstruction correctness is the whole risk |
| Radix sort (PLAN.md S1.3) | **V2** | Different ordering can change collision grouping |
| BLAKE2b kernel swap (S1.4, S2) | **V1** + bit-exact self-test | A wrong kernel silently invalidates every solution |
| SIMD merge (S2) | **V2** | Same as radix sort, plus lane-boundary bugs |
| Multi-core (S3) | **V2** + race check | Nondeterministic ordering; run V2 repeatedly |
| GPU (S4) | **V3** + CPU re-verification of every solution | Kernel bugs are indistinguishable from bad luck |

**Where to stop.** Take S1-S2 fully to V4 -- they are portable, low-risk, and
the numbers feed everything downstream. Take S3 to V4 with a repeated V2. Take
S4 to V3 during development and V5 only if it is destined for real miners; a
GPU solver that never leaves the lab does not need the cross-implementation
gate, and demanding it early would stall the work that produces the numbers.

### 3.2a How to test alternative implementations

Two modes, and both are needed for different reasons.

**Standalone (fast, where iteration happens).** A harness that constructs a
`base_state` directly and calls a chosen solver, with no node, no chain, no
RPC. Zero already has the seam: `EhOptimisedSolve(n, k, base_state, validBlock,
cancelled)` is a free function taking a callback, so a variant is a sibling
function with the same signature. What is missing is a **registry** so
variants can be enumerated and compared.

The Requihash implementation shows the pattern worth copying
[Reported: Requihash `Req/rust/src/solve/mod.rs` (out of tree)]:

```rust
pub trait Solver { fn solve(&self, engine: &Requihash) -> Vec<Vec<EhIndex>>;
                   fn name(&self) -> &'static str; }
pub fn all_solvers() -> Vec<Box<dyn Solver>> { /* reference, arena, bucket, ... */ }
```

with one test that runs **every registered solver on the same inputs and
asserts identical sorted solution sets** -- 30 nonces x 2 parameter sets,
**0.45 s** [Measured, this session: `cargo test --release --lib
all_solvers_agree`]. That is V2 made automatic and cheap enough to run on
every edit.

The C++ equivalent for Zero:

```cpp
// contrib/perf/eqsolve_bench.cpp  (standalone, links libbitcoin_crypto)
using SolveFn = bool(*)(const eh_HashState&, ValidFn, CancelFn);
struct Variant { const char* name; SolveFn fn; };
static const Variant kVariants[] = {
    {"basic",     EhBasicSolve},
    {"optimised", EhOptimisedSolve},     // today's default
    {"reserved",  EhSolveXcReserved},    // S1.2 step 1
    {"strided",   EhSolveStrided},       // S1.2 step 2
};
```

Then one differential driver: for each nonce, run every variant, sort the
solution sets, assert equality, and report wall time and peak RSS per variant.
**Build it before the first optimization**, not after -- it is what makes V2
free, and every later stage reuses it.

**In-system (slow, where truth lives).** The standalone harness cannot catch
integration faults: cancellation behaviour, the `-equihashsolver` dispatch in
`miner.cpp:539`, thread interaction with the miner loop, or memory pressure
against a running node. Two existing entry points cover it:

```bash
./src/zero-cli zcbenchmark solveequihash 3    # in-process, real dispatch
contrib/perf/mine_bench.sh regtest            # full miner loop, (48,5)
MINE_MAINNET_SOLVE=1 contrib/perf/mine_bench.sh mainnet-template
```

**Division of labour:** standalone for V0-V2 on every edit (seconds);
in-system for V3-V4 when a number is going to be recorded (minutes). A change
that passes standalone and fails in-system is an integration bug, and knowing
which of the two broke is most of the diagnosis.

### 3.2b Stepping through the Requihash variants

Requihash's `solve/` is a ladder that was *measured at each rung*, and the rungs
map onto Zero's situation unevenly -- which is the useful part:

| Requihash variant | What it changed | Their gain | Applies to Zero? |
|---|---|---|---|
| `reference` | baseline, `Vec` per row | 1.00x | **No** -- Zero is already flat-array |
| `arena` | flat arena, no per-row heap | 1.55-1.58x | **Already done** (`StepRow` inline array) |
| `bucket` | counting sort on the collision digit | +14% (1.86x cum.) | **Yes** -- S1.3, Zero uses `std::sort` |
| `parallel` | rayon over leaf generation | 1.91x | Partly -- S3, and note their 1.9x ceiling |
| `pointer` | compact index-pointer storage | prototype | **Yes** -- S1.2, and see S1.5 below |

Two lessons transfer better than the code does. First, **each rung was
validated by the same `all_solvers_agree` differential** before its number was
believed. Second, their `pointer` module is deliberately *not registered* in
`all_solvers()` while it remains a prototype -- an explicit "measured but not
trusted" state that keeps a promising variant in the tree without letting it
into results. Zero's registry should have the same property.

Worth reading rather than porting: their `pointer.rs` module docs stage the
work in three steps (graft the bucket sort onto the pointer layout; port
tromp's bounded xhash early-reject; only then consider bucket-addressed rows),
with the third gated on a measured threshold rather than done speculatively.

### 3.2c Vectors available to validate a tuning

Every experiment above is V1/V2, which means "did it change the answer". The
tree already ships the vectors to decide that -- **no new test data is needed
to start**:

| Vector / test | Params | What it pins |
|---|---|---|
| `validator_testvectors_192_7` | (192,7) | Verifier against known-good solutions |
| `validator_testvectors_192_7_h1` | (192,7) | Second header case |
| `zero_mainnet_genesis_equihash_192_7_valid` | (192,7) | The genesis solution verifies |
| `..._rejects_corrupt_solution` | (192,7) | A mutated solution is rejected |
| `validator_testvectors_48_5` | (48,5) | Regtest verifier |
| `solver_testvectors_48_5` | (48,5) | Solver at regtest scale (512 rows) |
| **`solver_baseline_192_7`** | **(192,7)** | **Full solution set, production scale -- the V2 baseline** |
| **`solver_timing_192_7`** | **(192,7)** | **Fixed-nonce solve timing -- the V4 harness** |
| `src/test/data/1927EQ.txt`, `1927EQ_h1.hex` | (192,7) | The raw KAT data |

**That gap is now closed.** `solver_baseline_192_7`
(`src/test/equihash_tests.cpp`) runs `EhOptimisedSolve` at (192,7), collects
**every** solution, verifies each through the untouched verifier, and dumps the
set:

```bash
DUMP_1927_SOLVER=test-logs/eqvectors/solver_baseline_192_7.txt \
  ./src/test/test_bitcoin --run_test=equihash_tests/solver_baseline_192_7
```

It is opt-in (one solve is ~60 s) so the default `equihash_tests` run is
unaffected -- verified: 10 cases, no errors, new case skips without the env var.

**Baseline captured** [Measured, `test-logs/eqvectors/solver_baseline_192_7.txt`]:

| Property | Value |
|---|---|
| Solutions found | **5**, all distinct |
| Indices per solution | 128 (= `2^k`), exactly |
| Index range | 106,595 .. 33,285,993 (all < `2^25`) |
| Duplicate indices within a solution | 0 |
| Each solution verifies independently | yes (checked in-test) |

The current `OptimisedSolve` is **definitive**: this is the reference set, and
any later change must reproduce all 5 exactly. Finding 4 is a regression even
if all 4 verify.

Note what the count reveals: a (192,7) solve yields ~5 solutions per nonce, not
1. A solver that returns after the first would look ~5x faster and mine ~5x
less -- precisely the failure V2 exists to catch, and a reason the baseline
records the **set**, not a count.

Additional oracles, in increasing cost:

- **The verifier as oracle (free, V1).** Every solution the solver emits can be
  checked by the untouched `CheckEquihashSolution`. Catches invalid output but
  **not** missing output.
- **Self-differential (V2).** Old vs new solver on the same input, compare
  sorted index sets. Catches dropped solutions -- the failure mode the verifier
  cannot see.
- **Ycash cross-check (V5).** Same lineage, already instantiates (192,7)
  (S2a); an independent binary agreeing on the solution set is strong
  evidence.
- **tromp at `-DWN=192 -DWK=7` (V5).** A genuinely different algorithm
  agreeing is the strongest available check, and doubles as the S2a evaluation.

### 3.2d Round-by-round snapshots -- deferred, with the reason

A tempting debugging aid: dump each round's row array to disk, so a failing
tuning can be diffed against the reference **round by round** rather than only
at the final solution set. It would localise a bug to "round 3's merge" instead
of "somewhere in the solve".

**Deferred, and the cost is why:** 2.19 GB per round x 7 rounds = **~15 GB per
solve** at full fidelity. Even sampling one bucket per round is awkward, since
the bug may be in a bucket you did not sample.

Cheaper substitutes that capture most of the value, worth doing *instead* for
now:

| Instead of | Do this | Cost |
|---|---|---|
| Full round dumps | Per-round **row count** and a checksum over the sorted collision keys | bytes |
| Full row inspection | Bucket **occupancy histogram** per round (validates the S1.2b distribution too) | KB |
| Diffing arrays | Diff the **final solution set** (V2), which is what correctness actually means | KB |

A per-round count-and-checksum line costs nothing and would localise most
merge bugs -- if round 3's row count diverges from the reference, that is the
round to look at. **Revisit full snapshots only if a bug survives the
checksums**, which would mean two implementations agree on counts and
checksums yet differ on solutions -- rare, and worth 15 GB when it happens.

### 3.2e Fixed-nonce timing: why the RPC benchmark cannot pair runs

`zcbenchmark solveequihash` draws a **random nonce per trial**
(`src/zcbenchmarks.cpp`, `randombytes_buf(nonce.begin(), 32)`). Each nonce is a
different search problem, so trials differ in **how much work they contain**,
not only in how fast that work runs.

Consequences, and they are not small:

- **Runs cannot be paired.** An A build and a B build draw different nonces, so
  a difference of means mixes the code change with the nonce draw.
- **Spread is dominated by the input, not the machine.** Measured n=4 baseline
  spread **29.3%**, n=10 spread **49.0%** -- against **0.2%** repeatability when
  the same nonce is re-run [Measured, `test-logs/eqsort-20260826/`].
- **Solution count varies per nonce** (2 to 4 observed), and a solve that finds
  more solutions does more work. Time without `nsols` is not interpretable.

So `zcbenchmark solveequihash` answers "what does a solve cost on average"
-- an honest question -- but it **cannot** answer "did this change help". For
that, use the fixed-nonce harness:

```bash
SOLVE_TIMING_1927=4 SOLVE_TIMING_TSV=test-logs/<run>/timing.tsv \
  ./src/test/test_bitcoin --run_test=equihash_tests/solver_timing_192_7 \
  --log_level=message
```

It walks nonces 0,1,2,... deterministically, so **run A and run B solve
identical work**; emits `nonce, secs, nsols` per trial; and verifies every
emitted solution inside the timing loop, so a "faster" solver that emits
garbage cannot post a number. Opt-in via the env var, ~30-70 s per nonce.

**Compare per nonce, not by pooled mean.** With paired data the right statistic
is the per-nonce ratio; a pooled mean throws away the pairing that makes the
comparison valid.

### 3.2f Cross-checking the vendored tromp solver, compatibly

Zero ships two (192,7) solvers (`../equ/FINDINGS.md` S2f.3): `EhOptimisedSolve`
(`default`, what every number in this tree measures) and vendored tromp
(`src/pow/tromp/`, what `prod.conf` selects). **Comparing them is only
meaningful if the comparison is compatible**, and four things must be held
equal or the result is not a solver comparison at all.

#### The four compatibility conditions, and why each already holds

| # | Condition | Status |
|---|-----------|--------|
| 1 | **Identical input state** | **Holds.** `equi::setstate(const crypto_generichash_blake2b_state*)` (`equi_miner.h:209`) takes exactly the `state` the D4 harness already builds with `EhInitialiseState` + `blake2b_update`. Pass the same object to both -- do not rebuild it |
| 2 | **Identical index encoding** | **Holds.** `miner.cpp:693` converts via `GetMinimalFromIndices(index_vector, DIGITBITS)`; `DIGITBITS = WN/(WK+1) = 24`, and the harness uses `cBitLen = n/(k+1) = 24`. Same function, same width, so solution sets are directly comparable |
| 3 | **Identical thread count** | **Holds if left alone.** `miner.cpp:669` constructs `equi eq(1)` -- single-threaded, matching `EhOptimisedSolve`. Zero builds with `-DEQUIHASH_TROMP_ATOMIC` (`src/Makefile.am:384`), so the atomic path is compiled in; **that is a cost tromp pays and `OptimisedSolve` does not**, and it must be reported, not silently equalised |
| 4 | **Identical verification** | **Must be added.** Every emitted solution goes through the untouched `CheckEquihashSolution`, same as the D4 harness does |

#### The one incompatibility that must be measured, not hidden

**`MAXSOLS = 8`** (`equi_miner.h:71`): tromp stores at most 8 solutions and
**silently discards the rest** (`if (soli < MAXSOLS)`). `EhOptimisedSolve` has
no such cap. Our genesis baseline finds 5 and fixed nonces have yielded 2-4
(S3.2a), so 8 is not binding *in observed cases* -- but it is a real semantic
difference and a nonce that produced 9+ would make tromp look correct while
losing work.

**Record `nsols` from both solvers on every nonce.** A divergence is a finding,
not noise. Do not raise `MAXSOLS` to make the comparison "fair": the shipped
value is what a miner runs.

#### Proposed harness: extend D4 rather than write a second one

`solver_timing_192_7` already does fixed nonces, per-nonce timing, `nsols`, and
in-loop verification. Add a solver selector so both paths run **the same nonce
sequence through the same timing and verification code**:

```bash
SOLVE_TIMING_1927=4 SOLVE_TIMING_SOLVER=default ...   # EhOptimisedSolve
SOLVE_TIMING_1927=4 SOLVE_TIMING_SOLVER=tromp   ...   # vendored tromp
```

This is the right shape because it makes the two arms differ in **one** thing.
Writing a separate tromp benchmark would reintroduce exactly the unpaired-input
problem that inflated the first D3 estimate by 30% (S3.2e).

The tromp driver is the loop already in `miner.cpp:669-684` -- lift it verbatim
rather than reimplementing:

```cpp
equi eq(1);
eq.setstate(&state);          // condition 1: the SAME state object
eq.digit0(0);
for (u32 r = 1; r < WK; r++)
    (r & 1) ? eq.digitodd(r, 0) : eq.digiteven(r, 0);
eq.digitK(0);
// then GetMinimalFromIndices(idx, DIGITBITS) per eq.sols[s]  -- condition 2
```

#### What to record, and the comparisons it enables

| Signal | Why |
|--------|-----|
| secs per nonce, both solvers | The headline; **paired**, so per-nonce ratio is the statistic |
| `nsols` per nonce, both | Guards `MAXSOLS`; a mismatch invalidates the time comparison |
| **solution set equality** | The real cross-check: two independent algorithms agreeing is **V5** evidence (S3.2), the strongest oracle available |
| peak `phys_mb`, both | tromp's two heaps vs `Xt`+`Xc`; the memory claim in S1.2 depends on which solver is meant |
| Build/platform stamp | Both arms are the same binary here, so only the selector differs |

#### Why this is worth more than a benchmark

A tromp-vs-default run on identical nonces is simultaneously:

1. **A performance comparison** -- which solver a miner should run.
2. **A V5 cross-implementation check** (S3.2) -- two structurally different
   algorithms, one bucket-based and one sort-based, agreeing on the solution
   set is far stronger evidence than either verifying alone. `../equ/README.md`
   lists a tromp port as the strongest available V5 oracle; **it is already in
   the tree**, so that oracle is available now at no porting cost.
3. **A validation of the analysis in S1/S2d** -- if tromp's measured peak is
   near the ~3.3 GB computed for a tromp-class solver at (192,7) (S1.2a), the
   model is confirmed from a second direction.

**Order:** (2) first. If the solution sets disagree, the timing numbers are
uninteresting until that is resolved.

### 3.3 What to record every time

Beyond wall time, capture what the measured baseline says matters:

| Signal | Why | Tool |
|--------|-----|------|
| Peak physical footprint | The binding constraint (PLAN.md S1.2) | `res_sample.sh` `phys_mb` |
| RSS trajectory | Distinguishes steady state from per-attempt churn | `res_sample.sh` |
| Per-thread CPU | Confirms whether S3 actually parallelised | `res_sample.sh` hot-thread |
| Sol/s | The headline; derive from trials, never a single run | `solve.tsv` |
| Bucket occupancy / overflow | (192,7) sizing correctness, S2 | new counter, S1 |

Rate is `trials / total_seconds`. With ~60 s solves, **report n and the spread,
never a single figure** -- the recorded n=3 baseline already spans 54.2-69.0 s,
a 27% range, so a single run cannot distinguish a 20% win from noise.

---

