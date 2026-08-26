# Equihash (192,7) mining optimization

Zero mines Equihash **(192,7)** on mainnet and testnet, **(48,5)** on regtest
(`src/chainparams.cpp:94,265,425`). This directory holds the analysis and plan
for making the solver competitive.

## The set

| Document | Answers |
|----------|---------|
| **[FINDINGS.md](FINDINGS.md)** | What is measured and computed about the current solver; S3 is the solver mechanism (keys, widths, comparator) |
| **[METHOD.md](METHOD.md)** | How to measure a change and how hard to validate it |
| **[PLAN.md](PLAN.md)** | What to build, in what order, S0 -> S4 |

Split from one 1500-line file along the same seam the perf docs use: facts,
method, plan. Related tracks: `../docs/FINDINGS.md` S2 (why Equihash is a
parallel track, not sync work), `../docs/SCHEMA.md` (recording results so they
aggregate across platforms).

## Where things stand

**Baseline** [Measured, `test-logs/res-mine-20260819/solve.tsv`]:

| Metric | Value |
|--------|-------|
| `zcbenchmark solveequihash`, n=3 | 54.2 / 67.1 / 69.0 s per solve |
| Effective rate | ~0.016 Sol/s |
| CPU | 100% of one core, single thread |
| Peak physical footprint | 7148 MB |

Against a ~100 Sol/s GPU reference the gap is ~6000x, decomposing into four
independent factors (algorithm/memory, SIMD, multi-core, GPU) -- `PLAN.md` S1.

## What this analysis established

Five results that change what to do first. All are computed from the source or
measured in this tree; none were assumed from published (200,9) work.

1. **The 7.15 GB is fully explained** (`FINDINGS.md` S1.1b): `Xt` is 2.19 GB,
   `Xc` is a second full-size buffer, and **`Xc` has no `reserve()`** so it
   reallocates with both buffers live. One line of code accounts for roughly
   half the peak.

2. **`TruncatedWidth` is a fixed 70 B for all rounds**, sized for the worst
   (`FINDINGS.md` S1.1a). Rounds 0-3 need 22-25 B and pay 70 -- a ~3x
   overcharge on the rounds holding the largest lists.

3. **"Get to 144 MB" is not available at these parameters**
   (`FINDINGS.md` S1.2a). The same zcashd algorithm needs 0.51 GB at (200,9);
   tromp's own design needs ~3.3 GB at (192,7) because `BUCKBITS` grows with
   `DIGITBITS`. The realistic target is ~2 GB near-term, not 144 MB.

4. **Two assumptions imported from the Requihash profile did not transfer**
   (`FINDINGS.md` S1.1): Zero's rows are fixed inline arrays, not per-row heap
   allocations, so the 59%-malloc finding does not apply; and Zero already
   implements the in-place merge. Of the four canonical 2016-17 techniques,
   Zero has two.

5. **The memory/multi-core coupling is weaker than first stated**
   (`PLAN.md` S6.0). It gates *independent-solve* parallelism (memory x N), not
   *intra-solve* parallelism (memory constant in N) -- but the latter is worth
   only ~1.15x without a parallel merge.

## Validation assets

A **(192,7) solver baseline now exists** -- previously the only solver-side
vector was at (48,5), 512 rows, where no memory hierarchy is exercised:

```bash
DUMP_1927_SOLVER=test-logs/eqvectors/solver_baseline_192_7.txt \
  ./src/test/test_bitcoin --run_test=equihash_tests/solver_baseline_192_7
```

Captured [Measured, `test-logs/eqvectors/solver_baseline_192_7.txt`]: **5
distinct solutions**, 128 indices each, all in range, no duplicates, each
verified in-test by the untouched verifier. The current `OptimisedSolve` is
definitive; any later change must reproduce all 5.

Opt-in (one solve is ~60 s), so the default `equihash_tests` run is unaffected
-- 10 cases, no errors.

## Next actions

| # | Action | Effort | Gate |
|---|--------|--------|------|
| 1 | **`Xc.reserve()`** -- one line, and the single most informative measurement in the plan (`PLAN.md` S1.2) | XS | V1 |
| 2 | **Profile (192,7)** to confirm or refute the sort-dominated hypothesis (`PLAN.md` S1.1) | S | V0 |
| 3 | **Fold `len` to a compile-time constant** (`PLAN.md` S1.2b; mechanism `FINDINGS.md` S3.2) | XS | V1 |
| 4 | **x86-64 Linux baseline** -- every number here is macOS/arm64 | S | V4 |

Items 1 and 3 are one-line-scale and V1; item 2 decides the order of everything
after. Item 4 matters because two findings are architecture-specific: the cache
line is 128 B here versus 64 B on x86, and the base page is 16 KB versus 4 KB.

## Open, and deliberately not started

- **Per-round row widths** and **compact index-pointer storage** -- the two
  structural memory changes (`PLAN.md` S1.2). Both V2.
- **Round-by-round snapshots** for debugging: deferred at ~15 GB per solve;
  per-round counts plus key checksums proposed instead (`METHOD.md` S3.2d).
- **A tromp port at `-DWN=192 -DWK=7`** -- reachable (his generic
  `digitodd`/`digiteven` path exists) and the strongest available V5 oracle
  (`FINDINGS.md` S2a).
