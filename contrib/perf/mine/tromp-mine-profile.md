# Tromp (192,7) miner profile -- 4 threads

Spot capture of the operator mainnet `zerod` mining Equihash (192,7) with the
**tromp** solver (`equihashsolver=tromp`, `genproclimit=4`). Companion to
`zero-mine-profile.md`, which profiled the **default** `EhOptimisedSolve` at
`genproclimit=1`. The two solvers are different algorithms: the function
breakdown does not carry over between them.

Not a lab campaign. `contrib/perf/` harness was not used; this is `/usr/bin/sample`
against the live operator node, same method as the companion note.

## Capture identity

| Field | Value |
|-------|-------|
| Host time | 2026-09-01 23:33:19 -0700 |
| Tool | `/usr/bin/sample`, 60 s, 1 ms |
| Samples per thread | 48710 |
| Miner threads | 4 (`zcash-miner`), 194840 samples total |
| Threads sampled | 20 |
| pid | 8732 |
| Solver | tromp (`src/miner.cpp:668`), `equi eq(1)` -- one thread per solve |
| Binary | `src/zerod -daemon`, arm64, clang `-O2 -g` |
| Host | Apple M4 Pro, 10P+4E, 48 GB |
| `phys_footprint` | 16.0 GB (peak 16.0 GB) |
| Process CPU | 400% (4 cores saturated) |
| `localsolps` | 0.97 - 1.22 |
| `networksolps` | ~900 |
| difficulty | ~4130-4340 |

## Exclusive CPU, miner threads only

Self time (stack leaf), as % of the 194840 miner-thread samples. Non-miner
threads are excluded, so these percentages do not need the "other threads
leaking in" caveat the companion note carries. Column sums to 100%.

| Function | Samples | % of miner |
|----------|--------:|-----------:|
| `blake2b_compress_ref` | 95342 | **48.93** |
| `equi::digitodd` (self) | 42129 | **21.62** |
| `equi::digiteven` (self) | 39445 | **20.24** |
| `BitcoinMiner` (self) | 7105 | 3.65 |
| `_platform_memmove` | 3996 | 2.05 |
| `equi::digit0` (self) | 1376 | 0.71 |
| `_platform_memset` | 944 | 0.48 |
| `blake2b_final` | 870 | 0.45 |
| `memset_s` | 700 | 0.36 |
| `__bzero` | 666 | 0.34 |
| `DYLD-STUB$$memcpy` | 609 | 0.31 |
| `blake2b_update` | 495 | 0.25 |
| `DYLD-STUB$$mkostemps` | 392 | 0.20 |
| `sodium_memzero` | 289 | 0.15 |
| `DYLD-STUB$$memset_s` | 278 | 0.14 |
| `crypto_generichash_blake2b_final` | 78 | 0.04 |
| `DYLD-STUB$$bzero` | 70 | 0.04 |

### Grouped

| Work | Samples | % of miner |
|------|--------:|-----------:|
| **BLAKE2b** (`compress_ref` + `final` + `update` + generichash) | 96785 | **49.67** |
| **Round merge** (`digitodd` + `digiteven` self) | 81574 | **41.87** |
| `memmove` / `memset` / `bzero` / `memset_s` / stubs | 7654 | 3.93 |
| `BitcoinMiner` self (template, cancel check) | 7105 | 3.65 |
| `digit0` self | 1376 | 0.71 |

## Inclusive, by solver phase

Direct children of `BitcoinMiner`. All 4 miner threads are 100% in
`BitcoinMiner`; the solver is the whole workload.

| Phase | Samples | % of miner |
|-------|--------:|-----------:|
| `digit0` -- leaf generation | 105295 | **54.04** |
| `digitodd` -- odd rounds | 42129 | 21.62 |
| `digiteven` -- even rounds | 39445 | 20.24 |
| `equi` ctor / `alloctrees` | 530 | 0.27 |
| `blake2b_update` / `final` (direct) | 281 | 0.14 |
| `candidate` / `listindices0` | 28 | 0.01 |
| `CreateNewBlock` | 27 | 0.01 |
| `BitcoinMiner` self | 7105 | 3.65 |

Rounds 1-6 together (`digitodd` + `digiteven`) are **41.87%**; leaf generation
alone is **54.04%**.

### What is inside each phase

`digit0` (105295 samples) is almost entirely the hash kernel:

| Leaf | % of digit0 | % of miner |
|------|------------:|-----------:|
| `blake2b_compress_ref` | 90.55 | 48.93 |
| `_platform_memmove` | 3.80 | 2.05 |
| `equi::digit0` self | 1.31 | 0.71 |
| everything else | 4.34 | 2.35 |

`digitodd` + `digiteven` (81574 samples) are **100% self time** -- no callees
above threshold. The merge is inlined straight-line code over the bucket
arrays: no sort call, no comparator, no allocation in the round loop.

## Findings

1. **BLAKE2b is the single largest cost: ~49.7% of miner CPU**, essentially all
   of it `blake2b_compress_ref` (48.93%) inside `digit0`. The companion default-solver
   profile put BLAKE2b at 12-28%; tromp's efficient merge raises hashing's *share*
   by shrinking everything else.

2. **`blake2b_compress_ref` is the scalar reference implementation.** Confirms
   `mine_bench.sh neon-probe` (M-MINE-NEON-PROBE): stock arm64 still links the
   reference compressor. Roughly half of mining CPU is running a portable C
   kernel with no NEON. This is the largest single optimization target on this host.

3. **The sort disappeared.** The default solver spent ~61% in row sort/compare
   (`memcmp` + `__partition` + `introsort` + row ctor). Tromp's bucket merge shows
   **no sort at all** -- no `_platform_memcmp`, no `std::__partition`, no `_qsort`
   above 7 samples. `memcmp`/`memmove`/`memset` combined are 3.93%, versus 41.7%.
   This is the mechanism behind the measured 5.69x in `../equ/VENDORED.md` S2.

4. **Round merge is 41.87%, entirely self time.** `digitodd`/`digiteven` have no
   callees above threshold -- inlined straight-line code over bucket arrays.
   Optimizing it means SIMD/prefetch on the bucket walk, not swapping a sort.

5. **Model A confirmed at 4 threads.** `equi eq(1)` is single-threaded per solve
   (`src/miner.cpp:670`); 4 independent solves, 400% CPU, 16.0 GB footprint --
   ~4 GB per solve, consistent with the 3.3 GB per-solve measurement in
   `../equ/VENDORED.md` S2 plus per-thread overhead. On this 48 GB host memory is
   not the binding constraint; the 10 performance cores are.

6. **Template rebuild is negligible while mining.** `CreateNewBlock` is 27
   samples (0.01%); `BitcoinMiner` self (cancel check, nonce loop) is 3.65%.

## Optimization implications

The two targets, in order, and both are `equ/PLAN.md` **S2** (SIMD) rather than
S1 (memory/sort) -- the sort work S1 targets is already gone under tromp:

| Target | Share | Note |
|---|---:|---|
| NEON BLAKE2b | 49.7% | Reference kernel today. Amdahl ceiling ~2.0x if hashing went free; a 2x kernel gives ~1.33x overall. **V1 minimum** (`METHOD.md` S3.2) -- a wrong SIMD lane silently invalidates solutions. |
| Bucket-merge SIMD / prefetch | 41.9% | Straight-line, no callees. Harder to attack; measure cache behaviour first. |

Memory work (`Xc.reserve`, per-round widths) targets the **default** solver's
7.15 GB and does not apply to this path.

## Caveats

- One 60 s capture, n=1, of a live node at a single solver round position. The
  companion note showed the default solver's exclusive mix shifting materially
  across captures (blake2b 12-28%); treat these percentages as one sample.
  Anything claiming a *speedup* needs **V4** (n>=4, fixed-nonce harness).
- `sample` counts on-CPU stacks only; it cannot see memory stalls. The 41.87%
  self time in the round merge may be substantially cache-miss wait.
- Percentages are of miner-thread samples, not wall-clock solve time.
- DWARF symbolication warnings on `.a` members are `sample` noise, not a bug.

## Files

| Path | What |
|------|------|
| `mine/tromp-mine-profile.md` | This note |
| `test-logs/tromp-profile-20260901/zerod-tromp-sample.txt` | 60 s `sample`, 2026-09-01 23:33:19 -0700 |
