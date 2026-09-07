# Equihash (192,7) mining optimization

Zero mines Equihash **(192,7)** on mainnet and testnet, **(48,5)** on regtest
(`src/chainparams.cpp:94,265,425`). This directory holds the analysis and plan
for making the solver competitive.

**Equihash is this directory's subject, and belongs here rather than being
spread across the perf tree**: solver internals, lineage, measurement method,
plans and solve findings all live in these files. The one deliberate exception
is Equihash's **verification** cost during block connection, which is a sync
finding and stays in `../Perf.md` S5. Placement rules generally:
`../docs/MAP.md`.

## The set

| Document | Single subject | Read when |
|----------|----------------|-----------|
| **[FINDINGS.md](FINDINGS.md)** | **What is measured**: current numbers, and the size of the gap | Deciding what is worth doing |
| **[SOLVER.md](SOLVER.md)** | **How the solvers work**: keys, widths, tags, buckets, and the constants that size them | Changing a data structure |
| **[VENDORED.md](VENDORED.md)** | **Which solver runs**: lineage, the default-vs-tromp comparison, and what updating the vendored copy would buy | Deciding which code path to invest in |
| **[METHOD.md](METHOD.md)** | **How to measure and validate** a change | Running anything |
| **[PLAN.md](PLAN.md)** | **What to build**, in what order, S0 -> S4 | Picking up work |

**Inclusion rules.** A number goes in `FINDINGS`. A data-structure explanation
goes in `SOLVER`. A statement about provenance or solver choice goes in
`VENDORED`. A gate or procedure goes in `METHOD`. A proposal goes in `PLAN`.
Nothing is restated across two of them -- the owning document is cited by
section id instead.

Split along the seam the perf docs use -- facts, method, plan -- with the
solver internals and the vendored-copy question separated out once each grew
past the point where `FINDINGS` could be read as one subject. Related tracks: `../docs/FINDINGS.md` S2 (why Equihash is a
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

Fixed-nonce timing harness (added; the V4 instrument):

```bash
SOLVE_TIMING_1927=4 SOLVE_TIMING_TSV=test-logs/<run>/timing.tsv \
  ./src/test/test_bitcoin --run_test=equihash_tests/solver_timing_192_7 \
  --log_level=message
```

Walks nonces 0,1,2,... so two builds solve **identical work**; emits
`nonce, secs, nsols` and verifies every solution inside the timing loop. Use it
instead of `zcbenchmark solveequihash` for any A/B -- that RPC randomises the
nonce per trial, giving 29-49% spread and unpairable samples
(`METHOD.md` S3.2e).

## Next actions

| # | Action | Effort | Gate |
|---|--------|--------|------|
| 1 | **`Xc.reserve()`** -- one line, and the single most informative measurement in the plan (`PLAN.md` S1.2) | XS | V1 |
| 2 | **Profile (192,7)** to confirm or refute the sort-dominated hypothesis (`PLAN.md` S1.1) | S | V0 |
| ~~3~~ | **Fold `len` to a compile-time constant** -- **DONE, 1.22x solve** (`FINDINGS.md` S3.2) | XS | V4 passed |
| 4 | **x86-64 Linux baseline** -- every number here is macOS/arm64 | S | V4 |

Item 3 is **done**: 1.22x on the solve, paired fixed-nonce, V2 and V4 passed.
Item 1 is the remaining one-line-scale change; item 2 decides the order of
everything after. Item 4 matters because two findings are architecture-specific: the cache
line is 128 B here versus 64 B on x86, and the base page is 16 KB versus 4 KB.

## Open, and deliberately not started

- **Per-round row widths** and **compact index-pointer storage** -- the two
  structural memory changes (`PLAN.md` S1.2). Both V2.
- **Round-by-round snapshots** for debugging: deferred at ~15 GB per solve;
  per-round counts plus key checksums proposed instead (`METHOD.md` S3.2d).
- **A tromp port at `-DWN=192 -DWK=7`** -- reachable (his generic
  `digitodd`/`digiteven` path exists) and the strongest available V5 oracle
  (`FINDINGS.md` `FINDINGS.md` S2a).

## Set review, 2026-09-06

Six files, 4,286 lines. An earlier version of this review declared every file
justified on the strength of each having a distinct topic. **That was not a
review** -- checking that six files have six subjects says nothing about
whether the same material appears in several of them. Redone by measurement.

**What was found.** Prose is not re-argued: across 924 prose sentences, only 5
cross-file near-duplicates (>0.80 similarity), and 11 repeated 5-word phrases,
most of them file paths. The set does not restate its arguments.

**Figures recur across files, but most occurrences are legitimate.** 34
distinct figures appear in three or more files, on 218 lines (5% of the set).
That count was first reported as the redundancy. It is not: the great majority
are **derivations** -- `33.5M rows x 70 B`, `6 rounds x 2 copies x 2.19 GB` --
which must restate a figure in order to compute with it, and section headings
naming the quantity they explain.

Filtering to lines that carry a shared figure with **no arithmetic and no
cross-reference** leaves **27**, spread over six files. Of those, most are
prose that cites a section alongside the number (`FINDINGS.md S1.2a`,
`VENDORED.md S3.6`), which is the intended pattern.

**So the set's real problem is not repetition of figures.** It is that the
figures had **no ids to cite**: 4,300 lines with two `M-*` references. A reader
finding `3.3 GB` in four files could not tell whether they were the same
measurement.

**Fix applied.** Six ids registered in `../Measures.md`: `M-EQ-ROW-WIDTH`,
`M-EQ-XT-ROUND0`, `M-EQ-PEAK-DEFAULT`, `M-EQ-PEAK-TROMP`,
`M-EQ-TROMP-SPEEDUP`, `M-EQ-D3-SORT`. Five bare table restatements now cite an
id instead of repeating a number. The remaining occurrences are derivations and
are correct as written -- **a mechanical sweep of them would break the
arithmetic**, which is why the earlier plan to "replace 215 restated figures"
was wrong and has been withdrawn.

**File-by-file, with the overlap that remains:**

| File | Lines | Distinct subject | Overlap |
|---|--:|---|---|
| `README.md` | 163 | Entry point, inclusion rules | Restates rules from METHOD by design |
| `FINDINGS.md` | 672 | Measured and computed results | **67 lines carry shared figures** -- the largest source |
| `SOLVER.md` | 1281 | How both solvers work internally | 46 lines; derives `RESTBITS`, others cite it correctly |
| `VENDORED.md` | 756 | Which solver ships, lineage, comparison | 40 lines; boundary with SOLVER holds by citation |
| `METHOD.md` | 490 | How to measure and validate | 6 lines -- cleanest file in the set |
| `PLAN.md` | 924 | What to build next, and gates | 45 lines |

**Not yet answered:** whether `SOLVER.md` at 1281 lines should be split, and
whether `PLAN.md`'s absorbed task material belongs with the plan or with
`METHOD.md`. Both need reading the content, not counting it.
