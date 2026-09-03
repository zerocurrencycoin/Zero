# Tasks

What is open, in what order. **15 items**, each one deliverable with sub-steps.

**This file carries no evidence.** Every "why" lives in `FINDINGS.md` (what was
measured), `../PerfGroth.md` (Groth16), or a spec, and is cited here rather
than restated. If a row needs a paragraph of justification, the justification
belongs in the other file.

Status (`POLICY.md` S1):

- **Kanban:** ToDo -> InProgress -> InTest -> Finished. The project owner
  defines what these mean.
- **Disposition:** Open | Blocked | Finished | Postponed | Aside

**Aside** now means *postponed pending review*, not *refused*. Each Aside item
carries the condition that would reopen it; see the Aside section.

Sequencing is **A before B before C** within a group; groups are independent
unless a dependency is named. **D** runs in parallel throughout.

---

## Board

| Item | Kanban | Disposition | Effort | Why |
|------|--------|-------------|--------|-----|
| A1 Enforce existing rules | **InTest** | Open | S | `FINDINGS.md` S1.3 |
| A2 Record binary and platform | **InTest** | Open | M | `FINDINGS.md` S1.2, `SCHEMA.md` |
| A3 Microbenchmark baseline | ToDo | Open | S | `FINDINGS.md` S4 |
| A4 Workload taxonomy A-E | ToDo | Open | S-M | this file, A4 |
| A5 CodexPerf review triage | **InProgress** | Open | M | `../../CodexPerf.md` |
| B1 Phase timers | **InProgress** | Open | S-M | `FINDINGS.md` S1.1, `../PerfTimers.md` |
| B2 First non-macOS measurement | ToDo | Open | M | `../PerfPlatforms.md` |
| B3 NOTEIDX staleness | ToDo | Open | S | `FINDINGS.md` S3.1 |
| C1 Documentation consolidation | **InTest** | Open | M | `MIGRATION.md` |
| C2 Remaining measurement gaps | ToDo | Open | M | `FINDINGS.md` S4 |
| C3 Inherited build/DB defects | ToDo | Open | M | `../BUILD_RECONFIG.md` |
| C4 Per-workload utilization profile | ToDo | Open | L | this file, C4 |
| C5 Document clean-up | ToDo | Open | M | this file, C5 |
| D1 Equihash / blake2 integration | **InProgress** | Open | M | `../equ/README.md` |
| D2 `Xc.reserve()` | ToDo | Open | XS | `../equ/FINDINGS.md` S1.1b |
| D3 Fold `len` to compile-time | **InTest** | Open | XS | **1.22x solve measured**; `../equ/FINDINGS.md` S3.2 |
| D4 Fixed-nonce timing harness | **Finished** | Finished | S | `../equ/METHOD.md` S3.2e |
| D5 Measure the **vendored tromp** path | **InTest** | Open | S | **5.69x, V5 PASSED**; `../equ/FINDINGS.md` S2f.4 |
| E1 Script corpus and safety | **Finished** | Finished | M | `POLICY.md` S3.1 |
| F1 Regression gate on validate | **InTest** | Open | S | `validate.sh` |
| F1b A2d stamp at write time | **Finished** | Finished | S-M | this file, F1b |
| F2 CI wiring | -- | **Postponed** | S | needs repo settings |
| GROTH | -- | Postponed | L-XL | `../PerfGroth.md` |

### Where to start next session

Everything below is Open unless marked otherwise. Three items are at **InTest**
and share one exit condition: **none has been exercised from a clean checkout
on a second machine.** That is the single highest-value next step, because it
is also what would validate the cross-platform schema work.

| Next | Item | Why it is next |
|------|------|----------------|
| 1 | **B2** first non-macOS capture | Now recordable (A2/F1b landed). Would move A1, A2, F1 and C1 out of InTest together, since a clean-checkout Linux run exercises all four |
| 2 | **A3** microbenchmark baseline | Effort S, no decision needed, and worth more the longer GROTH stays postponed: a batching result needs a per-proof baseline taken beforehand |
| 3 | **D2** `Xc.reserve()` | One line, V1, and the most informative single measurement in the Equihash plan. The harness and paired method now exist (D4), so this is a ~30 min run. Steps: D2 below |
| 4 | **B1c/d** proof counters + `BenchSummary` | Product change, Zero400 review. B1a/b (parser side) are Finished |

**Do not start** GROTH (maintainer's decision) or F2 (needs repository
settings). Both are Postponed, not forgotten.

**Standing caveat:** every gate is local. `validate.sh` runs only when a person
runs it, so until F2 lands a contributor who skips it bypasses all of A1.

---

## Postponed

**GROTH** -- Sapling Groth16 batch verification. Awaiting a maintainer's choice
between Option A and Option B; the options diverge at the FFI boundary, so
starting either wastes the other. Prototype frozen.

Everything: **`../PerfGroth.md`**. Nothing below depends on it.

---

## A -- do first

### A1. Enforce the rules that already exist

Make `lint-perf.sh` the enforcement point, then wire it into CI.

| Step | What | State |
|------|------|-------|
| a | Run `fix_ascii.py --fix` | **Finished** -- 693 -> 0 in owned scope |
| b | Add `unicode-docs` to the default `CHECKS` | **Finished** -- scoped to owned docs, `keep/` excluded |
| c | Citation + absolute-path checks | **Finished** -- `check_citations.py`, gated as `citations`. Scoped to measurement figures so it is signal, not noise |
| d | CI wiring | **Moved** to F2 (Postponed) |
| e | Gate tool self-tests in `lint-perf.sh` | **Finished** -- **17/17** Python tools plus `perflib.sh` |
| f | Harden `fix_ascii --fix`: scope, formula and blast-radius guards | **Finished** -- `POLICY.md` S7.4 |

(a) without (b) drifts again; (d) is where (b) and (c) stop being advisory.

**Kanban: InProgress. Effort S.** No product code. (a) and (b) Finished.

### A2. Record what the binary and platform were

Schema: **`SCHEMA.md`**.

| Step | What | State |
|------|------|-------|
| a | `platform_stamp.py` | Finished |
| b | `feature_bundles.json` | Finished |
| c | Back-annotate existing rows | **Partial** -- `platform` populated on all 49 rows (`*.v2.jsonl`); `features` is `{}` on every one, so no row carries `workload.op`. Completing it is A4f |
| d | Stamp at write time (**F1b**, not per launcher) | **Finished** -- `append_row` and `cmd_add` stamp; an unstamped row is now unrepresentable |
| e | Fingerprint v2 with `fingerprint_v` | Open |
| f | Group-by / filter; refuse cross-platform pooling by default | Open |
| g | Add `run_id` to CPU rows | Open |

a-b must precede any non-macOS run and are Finished. (c) is partial -- see A4f.

**Kanban: InTest. Effort M.**

### A3. Record the microbenchmark baseline

`M-ZCB-SUITE` has no numeric archive. Runner exists
(`performance-measurements.sh`).

Time-sensitive in one direction: a batching result needs a per-proof baseline
taken beforehand, so this is worth more during the postponement than after.

**Kanban: ToDo. Effort S.**

### A4. Name the demanding workloads, and make the names selectable

`features.workload.op` is the field that keeps a solve trial from pooling with
a reindex trial (`SCHEMA.md` S5). It is currently a **free-text string** --
`platform_stamp.py --op` has no enum and no validation -- so the guard that
refuses cross-workload pooling has nothing to key on. Every existing row reads
`reindex`.

Utilization varies widely across the demanding cases, and they are demanding
in **different resources**, which is why one number per case is not enough and
why they must not be averaged together.

| Class | Workload | Bound by | Hot thread | Distinguishing input |
|-------|----------|----------|------------|----------------------|
| **A** | Initial load: P2P sync, `-loadblock` bootstrap, unrolled capture | CPU, serial | `zcash-loadblk` | Block source |
| **B** | Reindex of an existing datadir | CPU, serial | `zcash-loadblk` | No network; blocks already local |
| **C** | Fat-wallet ingest / rescan | Witness scan, `cs_wallet` | `Main Thread` | Wallet shape -- see C below |
| **D** | Mining (solve) | CPU + **memory capacity** | miner thread | Params (192,7) vs (48,5) |
| **E** | Era: Sprout vs Sapling vs mixed | CPU, but a *different* mix | as A/B | Height window |

**A and B differ only in how blocks are sourced**, not in what validation
costs -- measured to agree within ~3 points on every bucket at the same
heights (`FINDINGS.md` S3.4). They stay separate `op` values because the
*sourcing* cost is real even though the validation cost is not; pooling them
would hide a network-side regression.

**C is not one workload.** The wallet shape is the variable, and the two
extremes load different code:

| Shape | Meaning | Expected bound |
|-------|---------|----------------|
| `few-utxo-many-tx` | Many transactions against an owned key, few unspent | `mapWallet` walk, witness scan |
| `many-utxo-few-tx` | Many unspent outputs, shallow history | Note commitment / witness cache |

Only the first is measured today (fat: 749 MB, 801619 tx, **72-99%** in
`witness_cache`, `FINDINGS.md` S3.1). The second is **unmeasured** and is a
named gap, not an assumption.

**E is a modifier, not a separate run.** Era is already carried by
`workload.from_height` / `to_height`; what is missing is that nothing
*derives* the era from them, so a reader must know that 492850 is Sapling
activation to interpret a row. A derived `era` field makes the height window
self-describing.

| Era | Height window | What dominates |
|-----|---------------|----------------|
| `sprout` | 0 .. 492849 | Groth16 ~43%, blake2b ~20% |
| `sapling` | 492850 .. tip | Groth16 **88-91%**, blake2b 3-4% |
| `mixed` | Any window straddling 492850 | Neither -- **not comparable to either** |

A window that straddles activation is the trap: it produces a number that is
an average of two regimes and matches neither. `mixed` exists so such a row
is labelled rather than silently misread.

| Step | What | State |
|------|------|-------|
| a | Define the `op` enum -- **accepted**: `sync`, `bootstrap`, `reindex`, `rescan`, `solve`, `verify`. Confirm each against real runs as they are taken | ToDo |
| b | Validate `--op` against it in `platform_stamp.py`; refuse an unknown value rather than recording it | ToDo |
| c | Add `workload.wallet_shape` for class C; `null` when `wallet: none` | ToDo |
| d | Derive `workload.era` from the height window, including `mixed` | ToDo |
| e | Extend the S5.1 pooling guard to refuse differing `op` and `era` by default | ToDo |
| f | Back-annotate `features` on the 49 `*.v2.jsonl` rows -- **`op` and `era` only**, both derivable. Not `wallet_shape` or bundle detail: those were not observed and would be invention. Completes A2c | ToDo |

The six values map onto the classes as: A = `sync` or `bootstrap`, B =
`reindex`, C = `rescan`, D = `solve` or `verify`. E is not an `op` -- it is the
derived `era`, orthogonal to all six.

**How precise should the back-annotation be, at this stage?** Deliberately
minimal. Only two fields are **derivable from what was recorded**: `op` (every
existing row is a reindex) and `era` (from the height window already stored).
Everything else in the `features` block -- wallet shape, runtime flags, bundle
membership -- was **not observed at the time** and would be reconstructed from
memory, which is the provenance problem the schema exists to prevent (the same
reason option C was rejected in F1b).

So the goal is **not** a fully-populated historical ledger. It is that old rows
carry enough to be *correctly excluded* from new comparisons: a row with
`op: reindex, era: sprout` will not silently pool with a post-Sapling solve
trial. Rows stay honestly sparse; the sparseness is the record. Fields that
matter get populated going forward by the writers, not backwards by inference.

(a) and (b) are the load-bearing pair -- an enum nothing checks is a comment.
(e) is what converts the taxonomy from documentation into a guard, and mirrors
the existing `platform.arch` refusal.

**Kanban: ToDo. Effort S-M.** No product code. Prerequisite for C4, which
publishes per-class tables and needs the classes to exist first.

---

## B -- after A

### A5. Triage the CodexPerf external review

`CodexPerf.md` (repo root, 2026-08-21, 180 lines) is an independent review of
the branch. **Verified against source before triage** -- it is accurate on
every point checked, and two findings are real defects in shipped-by-flag code.

| # | Finding | Verified? | Disposition |
|---|---------|-----------|-------------|
| **P0** | FDCACHE: `CacheOpen` releases `LOCK(latch.cs)` at function exit, then the caller deserializes through the shared `FILE*` unlocked | **CONFIRMED** (`main.cpp:4902-4925`) | **Real.** Another thread can `fseek` or `fclose` the same stream mid-read |
| **P1** | `-mrclogevery=0` divides by zero | **CONFIRMED** (`main.cpp:3232`, `:4950`) | **Real.** `nHeight % logEvery` unvalidated at both sites |
| P1 | FDCACHE probe always reports false -- flags absent from `HelpMessage` | Not re-checked | Plausible; affects provenance labelling |
| P1 | CI builds neither `--enable-perf` nor the perf lint | Consistent with F2 | Already tracked as **F2** (Postponed, needs repo settings) |
| P2 | Evidence set larger than authoritative; doc drift | **CONFIRMED** one case | `POLICY.md:68` said `unicode-docs` was not in default `CHECKS`; it is (`lint-perf.sh:107`). **Fixed** |
| P2 | Portability unproven, one host | Agrees with `FINDINGS.md` S4 | Already **B2** |
| P2 | `--enable-perf` couples counters with behaviour change | Accurate reading of `configure.ac` | Worth splitting; see (c) |
| P3 | Out-of-scope wallet docs in `keep/` | Agrees with `NOTES.md` | Already **C1c** |
| P3 | `git diff --check` trailing whitespace | Not re-checked | Cheap CI addition |

**The P0 finding contradicts a claim in our own documentation.**
`Perf.md:1525` calls the implementation "functionally correct"; the lock
lifetime does not support that. This is the review's most valuable
contribution and the reason it is worth acting on rather than filing.

| Step | What | State |
|------|------|-------|
| a | **FDCACHE retained** pending x86-64 Linux and Windows validation (B2). Fix the lock lifetime **before enabling** it with concurrent readers: RAII lease across seek+read, or positional `pread` | **Deferred to B2** |
| a2 | Measure FDCACHE on the two workloads where the mechanism could pay: **random `getblock` RPC** and **cold cache / slow storage** | ToDo |
| b | Validate `-mrclogevery` at startup | **Finished** -- `InitPerfLogEvery()`; 3 build configs clean |
| c | Split `--enable-perf` into counters (safe) and experimental behaviour (FDCACHE) | ToDo |
| d | Correct `Perf.md:1525` -- retract "functionally correct" and cite the lock-lifetime defect | ToDo |
| e | Re-verify the FDCACHE probe and the `HelpMessage` gap | ToDo |

(a) and (b) are the two that touch shipped behaviour. Both are Zero400-owned
(`src/`), so they are specified here and reviewed there.

#### Reachability, and the disposition of each

Verified: `src/config/bitcoin-config.h` has `/* #undef ZERO_PERF */` and
`/* #undef ZERO_FDCACHE */`. **A default build compiles out both.**

| Defect | Reachable in a release build? |
|--------|-------------------------------|
| FDCACHE lock lifetime (P0) | **No** -- needs `--enable-perf` **and** `-perffdcache=1` (default false) |
| `-mrclogevery=0` (P1) | **No** -- both modulo sites are inside `#ifdef ZERO_PERF` |

**`-mrclogevery`: FIXED.** One validated read at startup replaces two unguarded
`GetArg` lookups:

- `InitPerfLogEvery()` (`main.cpp`) reads once, rejects `< 1` and
  `> PERF_LOG_EVERY_MAX`, and throws a specific message at startup rather than
  dividing by zero mid-sync.
- Called from `init.cpp` before any block is connected.
- Both call sites now read `nPerfLogEvery`.

Verified in **three** configurations: default build, `-DZERO_PERF`, and
`-DZERO_PERF -DZERO_FDCACHE`, all 0 errors. **The perf-only build caught a real
bug the default build could not**: the first version of the declaration was
nested inside `#ifdef ZERO_FDCACHE`, so a `ZERO_PERF`-only build failed with
`use of undeclared identifier`. That is precisely the class of breakage F2/A5
flags as invisible to current CI -- and an argument for the `--enable-perf` CI
job, independent of FDCACHE's disposition.

**FDCACHE: RETAINED, by owner decision.** It is optional perf instrumentation,
not shipped behaviour, and it stays **at least until results are validated on
x86-64 Linux and Windows**. The null result (S3.2) is one platform, and macOS
stdio behaviour does not predict either target -- the same reasoning that keeps
B2 open. The P0 lock-lifetime issue remains **real and documented**, and is a
prerequisite for *enabling* the flag in any multi-reader context, not a reason
to delete a compiled-out research path.

#### FDCACHE: the untested cases where it could pay

The null (S3.2) is established for **sequential reindex on macOS/arm64 with a
warm page cache**. Two workloads have the opposite access pattern and are
unmeasured. Recorded so the flag's retention has a stated purpose:

| Workload | Why the mechanism could matter | Measurable how |
|----------|-------------------------------|----------------|
| **Random `getblock` / REST / explorer serving** | Consecutive requests hit **different** `blk*.dat` files, so every read pays `fopen`+`fclose` that the latch would elide. Sequential reindex hits the same file repeatedly, which is why the cache had nothing to save there | Drive `getblock` over a random height sample against a synced node, with and without `-perffdcache`; compare RPC latency percentiles, not throughput |
| **Cold cache / slow storage** | The 4.91% syscall share assumes the page cache already holds the data. On first touch, or on network/spinning storage, the read itself dominates and buffer size becomes relevant | Same reindex window with the page cache dropped between trials; **Linux only** (`/proc/sys/vm/drop_caches`), which makes this a B2 item |

**Both are latency questions, not throughput questions**, which is why the
existing throughput harness measured nothing: it was the wrong instrument for
the case where the mechanism helps. The reindex null stands and is not
contradicted by either.

**Prerequisite for the RPC case:** concurrent readers are exactly the P0
condition (`main.cpp:4902`), so the lock-lifetime fix must land **before** any
multi-client `getblock` measurement -- otherwise the experiment is measuring an
unsafe path.

**Assessment of the review itself: accurate and useful.** Every claim spot
checked held up against the source, including one that contradicts our own
documentation -- which is the kind of finding an internal reviewer is least
likely to produce. Its P2/P3 items largely restate work already tracked (B2,
C1c, F2), so its marginal value is concentrated in P0 and the two P1 defects.

**Kanban: InProgress. Effort M.**

### B1. Phase timers

Spec: **`../PerfTimers.md`**.

| Step | What | Owner |
|------|------|-------|
| a | Parse the 10 unparsed `-debug=bench` phase lines | **Finished** -- all 11 parse; formats taken from the `LogPrint` calls |
| b | Fix the verify/connect overlap | **Finished** -- `verify_excl_ms()`; a negative span yields `None`, never a negative duration |
| c | Add proof-verification counters | Zero400 |
| d | Emit periodic `BenchSummary` | Zero400 |
| e | Parse `BenchSummary` | ZeroPerf |

Order is forced: (b) with or before (a), or the double-count is frozen into
stored data. (c) before (d) -- reason in `FINDINGS.md` S1.1.

**Kanban: ToDo. Effort S-M.** (a) and (b) need no node change.

### B2. First non-macOS measurement

Survey: **`../PerfPlatforms.md`**.

| Step | What |
|------|------|
| a | State the platform caveat wherever CPU numbers are published |
| b | Document the `parse()` input contract in `bucket_profile2.py` |
| c | Linux `perf record` + folded-stack parser, reusing `classify()` / `BUCKETS` |
| d | Port `res_sample.sh` to `psutil` |

**Requires A2** so the result is recordable. Native Windows ETW is Aside.

**Kanban: ToDo. Effort M.**

### B3. NOTEIDX staleness

Invalidate the note index only on note-membership change. Defect, cost and
call sites: `FINDINGS.md` S3.1.

**Kanban: ToDo. Effort S.** Product change, Zero400 review.

---

## C -- after B

### C1. Documentation consolidation

Scope and rationale: **`MIGRATION.md`**.

| Step | What | State |
|------|------|-------|
| a | Build the docs set, pulling material in incrementally | **Finished** |
| b | `NOTES.md`: stamp dated evaluations with date and version | ToDo |
| c | Relocate off-subject documents -- **needs confirmation** | ToDo |
| d | Retire superseded originals once content has a home | **Finished** -- 7 retired, 6 relocated to `../keep/` |
| e | Caveat diff before retiring `Perf.md` | **Finished** -- 0 orphaned rules; `MIGRATION.md` S6 |

**Kanban: InProgress. Effort M.**

### C2. Remaining measurement gaps

Gaps and their effect: `FINDINGS.md` S4.

| Gap | Note |
|-----|------|
| Thermal on long runs | Attach to a scheduled run; do not schedule one |
| p1 rescan | First confirm by timing that p1 is long enough to profile |
| Segmented bootstrap | Lab wall time |

**Kanban: ToDo. Effort M.**

### C3. Inherited build and DB defects

| Item | Note |
|------|------|
| Autotools re-run inherits no `CONFIG_SITE` | Options: `../BUILD_RECONFIG.md`. Touches Zero400-owned `configure.ac` |
| `CDB::Rewrite` spins with no log or timeout | Upstream, all Zcash-family forks |

**Kanban: ToDo. Effort M.**

### C4. Publish a per-workload utilization profile

One table per workload class (A4), each reporting the resources that class is
actually bound by. **Requires A4** -- the classes must be selectable before
per-class tables can be generated from the ledger rather than hand-written.

**Why tables rather than prose.** The current numbers are scattered across
`FINDINGS.md` S2.3, S3.1 and S3.2 in three different shapes, and the reader
must already know which are comparable. A fixed column set per class makes
non-comparability visible instead of inferred.

**Report these columns per class**, because the classes are bound by different
resources and a single column set would be mostly empty:

| Class | Columns that matter |
|-------|--------------------|
| A, B | blk/s, CPU% of one core, thread count, bucket shares, height window |
| C | blk/s, CPU% , witness-scan share, `mapWallet` size, wallet MB, tx count |
| D | s/solve, Sol/s, **peak phys MB**, CPU% , thread count |
| E | bucket shares only -- a *modifier* on A/B, reported as a column split |

**Publish M4 and x86-64 as separate columns, never as one mean.** Two findings
are architecture-specific and the difference is large enough to invert a
conclusion:

| Property | Apple M4 Pro | x86-64 | Consequence |
|----------|-------------:|-------:|-------------|
| Cache line | **128 B** | 64 B | 70 B row: 1.53 vs **2.06** avg lines |
| Base page | **16 KB** | 4 KB | 2.19 GB buffer: 143,524 vs **574,095** pages |
| Vector width | NEON 128-bit | AVX2 256 / AVX-512 512 | 2 vs 4-8 BLAKE2b lanes |
| L2 | 16 MB shared | 1-2 MB private | Bucket sizing differs |

Measured on this host: `hw.cachelinesize=128`, `hw.pagesize=16384`,
`Mac16,7`, 14 cores, 48 GB.

The consequence to state wherever a number is published: **an arm64 result
does not predict x86.** Apple's larger line and page flatter the current code,
so the row-straddling and TLB problems should read *worse* on x86, not the
same -- a concrete prediction the first Linux run (B2) tests.

### C4 durations -- rough, to be replaced with actuals

Derived by arithmetic from the rates already recorded under M-RX-TINY*,
M-RX-POSTSAP-STOCK, M-BOOT-POSTSAP, M-WAL-RESCAN-FAT and M-MINE-SOLVE
(`../Measures.md` owns the figures; `FINDINGS.md` S3.2 summarises the regions).
**These are projections from those rates, not timings of these specific runs**
-- they exist to make the campaign schedulable, and each is replaced with an
actual as its cell is filled.

| Class | Case | Scope | Est. per trial | n | Est. total |
|-------|------|-------|---------------:|--:|-----------:|
| **B** | reindex tiny | 187417 blk, pre-Sap | **~3 min** | 4 | ~12 min |
| **B** | reindex short | 245992 blk, pre-Sap | **~4 min** | 4 | ~16 min |
| **B** | reindex post-Sap window | 600k-900k, 300k blk | **~17 min** | 4 | **~70 min** |
| **A** | bootstrap pre-Sap | to h100000 | **~2 min** | 4 | ~8 min |
| **A** | bootstrap post-Sap | 300k blk window | **~17 min** | 4 | ~70 min |
| **A** | P2P sync | network-bound, not CPU-bound | **unbounded** | 1 | see note |
| **C** | rescan p0 / p1 | 106 KB wallet | **~2 ms** / unknown | 4 | minutes |
| **C** | rescan fat `few-utxo-many-tx` | fat wallet, rate cliff above h1.6M (M-WAL-RESCAN-FAT) | **hours** | 1 | **long trial** |
| **C** | rescan fat `many-utxo-few-tx` | wallet does not exist yet | -- | -- | **blocked: needs a wallet** |
| **D** | solve (192,7) | one solve | **~60 s** | 4 | ~6 min |
| **D** | verify (192,7) | one header | **~0.1 ms** | 20 | seconds |
| **E** | era split | no extra runs -- a column split on B rows | **0** | -- | 0 |

Three consequences for scheduling:

- **E is free.** It re-slices existing B captures by height window; it is not a
  campaign. Only `mixed` windows need re-running, and only if any exist.
- **`many-utxo-few-tx` is unblocked** -- a suitable wallet is being supplied.
  Until it lands the cell is empty-and-named, not speculative.
- **The fat rescan and the post-Sapling windows are the long poles.**

**Is the ~20 minute rule the right threshold here?** It is the right *rule* on
the wrong *axis* for these cases. POLICY S4 reads "do not start a batch where
each trial exceeds ~20 minutes **unless each can be restarted individually**"
-- so the binding condition is restartability, and 20 minutes is only a proxy
for "long enough that losing it hurts".

That proxy breaks down at both ends of this campaign:

| Case | Duration | Restartable? | Verdict |
|------|---------:|--------------|---------|
| reindex post-Sap window | ~17 min | yes, per trial | Under the threshold, and safe anyway |
| bootstrap post-Sap | ~17 min | yes, per trial | Same |
| **fat rescan** | **hours** | **no -- one indivisible scan** | The rule's 20 min says nothing useful; what matters is that it cannot resume |
| P2P sync | unbounded | resumes naturally | Long but self-restarting; the rule does not bite |

So **~20 minutes stays as a batching heuristic**, with the axis stated in
POLICY S4: restartability is the criterion, duration is a hint. A 4-hour trial
that checkpoints is safer than a 25-minute one that does not.

**Checkpoint often; collate separately.** This is the operating rule for every
long trial, and it is implementable now for the cases below.

*Checkpointing* -- the running trial appends a progress row and never rewrites
one. `res_sample.sh` already samples on an interval and `stall_check.py`
already parses `UpdateTip` from `debug.log`; a checkpoint is those two writing
one append-only `progress.tsv` per run:

```
utc  height  elapsed_s  blk_s_since_last  rss_mb  phys_mb  peers
```

*Collating* -- a separate pass, after the run, reads `progress.tsv` and emits
ledger rows. It never runs in-process, so a crash cannot corrupt it and a
killed trial still leaves a readable file. `accumulate_bench.py --import-tsv`
already does exactly this shape of import.

The split is the point: **the trial writes, the collator reads.** An
interrupted run at hour 3 yields 3 hours of citable progress rows instead of
nothing.

Implement where understood and feasible, which is:

| Case | Checkpoint feasible now? | How |
|------|--------------------------|-----|
| **Fat rescan** | **Yes** | Per-height rates are already in `debug.log`; `res_sample.sh` is already the sampler. Wire both to `progress.tsv` |
| **Network sync** | **Yes** | Same, plus `peer_count`. Already the natural shape for a run with no fixed end |
| **Post-Sap reindex/bootstrap** | Yes, and cheap | ~17 min, already restartable; checkpointing costs nothing and makes an interrupted run usable |
| **Solve (192,7)** | **No -- do not** | One solve is ~60 s and atomic; there is no meaningful mid-solve state. Sample `phys_mb` on an interval instead, which `res_sample.sh` already does |

Do not checkpoint what has no resumable state. For the solve, interval RSS
sampling is the analogous instrument and it already exists.

**Network sync: reproducible, environment-dependent, high variance.** The
procedure is deterministic and repeats exactly; what varies is the environment
(peer set and quality, bandwidth, tip distance at start, time of day). That is
**variance, not irreproducibility**, and the two call for opposite treatment:
an irreproducible measurement gets excluded, a high-variance one gets **more
trials and its spread reported**.

So it is recorded like any other trial, with the environment captured as
fields rather than waved at in prose:

| Field | Why it is a column |
|-------|--------------------|
| `peer_count` at start and mean | The first-order determinant of rate |
| `from_height`, `to_height` | Tip distance at start; the run is not comparable without it |
| `wall_s`, blk/s **by region** | Aggregate rate hides the pre/post-Sapling split |
| Stall events by class | `tip_gap`, `tip_silent`, `timeout_burst` from `stall_check.py` |
| `started_utc` | Time-of-day and network-conditions proxy |
| n, and **min/max, not just mean** | With variance this high, a mean alone misleads |

**Separate audience from reindex, and say so in the schema, not in prose.**
`op: sync` versus `op: reindex` already separates them for the pooling guard
(A4e). The audience difference is real -- a new operator asking "is my node
stuck?" versus a developer asking "did this change help?" -- and it is served
by *which document publishes the row*, not by recording it less precisely.

**Precision is set by what shows up in the data, not by an audience judgement.**
Report the digits the measurement supports: if the spread across n trials is
30%, the mean gets two significant figures and the spread is published beside
it. That rule is the same for sync as for a solve; nothing is recorded loosely
because a reader is assumed to be casual.

Deliverables, both from the same rows:

| Output | For | Content |
|--------|-----|---------|
| Ledger rows | Lab | `op: sync`, full field set above, n>=3, spread reported |
| Operator note | README / BUILD_ZERO | Observed range and what normal progress looks like, so a slow sync is distinguishable from a stuck one |

### C4 automation, and not overwriting prior results

**Initial runs are ad-hoc by design** -- the first trial of anything is a
person at a terminal finding out what breaks. Automation is proposed for what
comes *after* the shape is known, and only where a step is already being
repeated by hand.

**What already protects prior results** (verified, not assumed):

| Mechanism | Guarantee | Where |
|-----------|-----------|-------|
| `append_row` | Append-only, and a re-append of an identical trial is **skipped**, not duplicated | `accumulate_bench.py:152` |
| Datadir `aside` default | A re-run renames the old tree to `<path>.aside-<utc>` rather than deleting it | `POLICY.md` S3.1 |
| `archives/` never reclaimed | Hard-coded non-reclaimable, independent of age or size | `retention.py`, `POLICY.md` S6.4 |
| Per-run logs | `validate.sh` logs per run, so a failure is not overwritten by the next green run | `POLICY.md` S3.2 |

So the ledger and datadirs are covered. **Three real gaps remain**, all of them
places where a new run writes to a fixed path:

| Gap | Risk | Fix |
|-----|------|-----|
| `DUMP_1927_SOLVER=<path>` | Same filename each run silently overwrites the previous solver dump | Write `solver_<variant>_<utc>.txt`; never reuse the baseline's name |
| `test-logs/eqvectors/solver_baseline_192_7.txt` | It is the **V2 reference**. Overwriting it destroys the oracle every later change is checked against | Mark read-only; copy to `test-logs/archives/` before any D2/D3 work begins |
| Instruments captures | `profile_run.sh <name>` reuses a name if given one | Include the UTC stamp in the scenario name |

**The baseline dump is the one that actually matters.** If it is regenerated
from a modified solver, every subsequent differential compares the change
against itself and V2 silently passes forever. **Done** -- step (e) below: it
is archived under `test-logs/archives/` and the working copy is `0444`, so
`DUMP_1927_SOLVER` pointed at it now fails rather than overwrites.

**Script reuse is E1's subject, not C4's.** Survey, findings and actions:
**E1, "Reuse gaps"**. What matters here is only that the C4 campaign needs
**no new runner** -- it is `ops-campaign.sh` with more catalog rows,
`res_sample.sh` with another output mode, and an existing import flag.

| New need | Existing helper |
|----------|-----------------|
| Checkpoint sampling | `res_sample.sh` interval sampler + `phys_mb` (E1o) |
| Progress -> ledger | `accumulate_bench.py --import-tsv` (E1p) |
| Stall classification | `stall_check.py` -- `tip_gap`, `tip_silent`, `timeout_burst` |
| Campaign resume | `ops-campaign.sh` catalog + `status.jsonl` |
| Height parsing | `debuglog.py` path spec, `extract_measures.py --elapsed-heights` |

**Proposed automation, in the order it earns its keep:**

| # | Automation | Replaces | When |
|---|-----------|----------|------|
| 1 | **`eqbench.sh <variant>`** -- build-tagged wrapper: V0 tests, V2 differential against the archived baseline, n>=4 timed solves, `phys_mb`, ledger append | The D2/D3 step lists run by hand | After D2 is done once manually |
| 2 | **Solver variant registry** -- `EhSolveXcReserved` etc. behind a name, so variants are enumerable and comparable in one process | Rebuild-and-revert between variants | When a third variant appears |
| 3 | **`--self-test` for the differential** -- assert the archived baseline still parses and has 5 solutions before trusting a comparison | Nothing; this is new | With (1) |
| 4 | **Per-round counters** (D2, step 1 of the tuning) | Guessing the reserve | Before per-round widths |
| 5 | **Campaign driver over `cycle_trials.tsv`** -- one C4 cell per invocation, resumable, status in `status.jsonl` | Hand-tracking which cells are done | When more than ~6 cells remain |

(1) is the highest value: the D2 and D3 step lists are the same six actions
twice, and a wrapper makes the V2 differential impossible to skip. (2) is what
`METHOD.md` S3.2a already specifies and should be built when it stops being
hypothetical. (5) reuses `ops-campaign.sh`'s existing catalog-plus-ledger shape
rather than inventing a runner.

**Do not automate** the ad-hoc first run of anything, or the fat rescan until
E1n-p give it a progress record -- automating an unrestartable multi-hour
trial mostly automates losing it.

| Step | What | State |
|------|------|-------|
| a | Fixed column set per class, above | ToDo |
| b | Generate from the ledger, not by hand -- a hand-copied figure is a restatement (`README.md` rule 3) | ToDo |
| c | Empty cells for unmeasured combinations, named as gaps | ToDo |
| d | Arch as a **column split**, never a pooled mean | ToDo |
| e | **Archive `solver_baseline_192_7.txt` and mark read-only** -- prerequisite for D2 | **Finished** -- `archives/eqvectors-solver-baseline-192-7-20260825.tar.gz`, sha256 `3154de69`, source now `0444`. Both paths PROTECTED in `retention.py` |
| f | Stamp variant and UTC into every dump/capture path; no fixed-name writes | ToDo |
| g | Network sync as `op: sync` rows, n>=3, spread reported, plus an operator note derived from them | ToDo |

Checkpointing is **E1n-p** -- it is a `perflib.sh` capability, not a C4
deliverable. C4 consumes it; E1 builds it.

(c) matters more than it looks: the C `many-utxo-few-tx` shape and every
x86-64 cell are currently empty, and an empty cell is the honest rendering.

**Kanban: ToDo. Effort L**, dominated by actually running the missing cells.
Depends on **A4**; the x86-64 column depends on **B2**.

### C5. Document clean-up: audience, altitude, and accuracy

The doc set is **~11,000 lines** across 25 owned files. `docs/` was consolidated
once (`MIGRATION.md`, complete 2026-08-21) and holds the line at seven files,
but two things happened after: `Perf.md` (**1,875 lines**) stayed live rather
than being archived, and the `equ/` set grew to **~3,900 lines across 6 files**
outside that discipline. The result is a set that is accurate in the small and
unreadable in the large.

**The problem is audience, not length.** Almost nothing distinguishes what a
node operator, a maintainer, and someone changing the solver each need. So
kernel-level internals -- NEON register pressure, tromp bucket tags, BLAKE2b
round structure -- sit on the same page as facts a reader needs in the first
minute. **Very few readers ever need that layer**, and it should be segregated
or referenced out, not deleted wholesale.

| Step | What | State |
|------|------|-------|
| a | **Define reader types and route by them.** Operator / maintainer / solver-implementer. Each document declares its audience in its first lines; `OVERVIEW.md` routes | ToDo |
| b | **Segregate deep internals.** Kernel and solver-internal material moves behind a clearly-marked boundary (an appendix, or `equ/SOLVER.md` as the acknowledged deep tier) and is *cited* from the readable tier, never restated | ToDo |
| c | **Strike obsolete history.** Tried-and-failed and superseded lines are removed, not narrated. Keep a result only where it stops the work being retried; one or two lines, not a section | ToDo |
| d | **Purge invented technical detail.** Any mechanism claim not traceable to code or a measurement is struck. See the correction note below | ToDo |
| e | **Fix schema statements.** `SCHEMA.md` claimed "not yet implemented" while `*.v2.jsonl` already carried `schema`/`platform`/`build`, and twice cited a "Track S" that never existed. **Done** -- but the class needs a sweep: status lines that drifted from what the code does | **Partial** |
| f | **Fold or archive `Perf.md`.** 1,875 lines, superseded in part by `docs/`. Either archive with a scope stamp or fold what is still current | ToDo |
| g | **Apply the `equ/` set to the same rules `docs/README.md` sets** -- one subject per file, numbers cited not restated, audience declared | ToDo |

**Accuracy rules this item enforces** (they caused the defects it cleans up):

1. **State only what is used.** For the hash kernel, Zero uses AVX2 on 64-bit
   Intel, single-threaded. Do not represent other ISAs, kernels or threading
   modes -- not as a plan, a ceiling, or an aside.
2. **No invented mechanism.** If a claim is not read from the source or
   measured, it does not go in.
3. **BLAKE2b and Equihash internals are documented in the uniblake project,
   and the cross-implementation survey in the ZK reference tree.** Reference
   them; do not restate here.
4. **No transient results in durable documents.** Percentage shares,
   ns/digest figures and speedups change with hardware, compiler and workload.
   They belong in a dated capture or the ledger, cited by id -- never inline in
   a document meant to stay true. The same applies to status: do not write what
   is enabled or disabled "today".
5. **Zero documents Zero.** Scope is Zero's use cases, load and performance
   patterns. Solver and hash-library internals are another project's subject.

**Finding the duplication.** Grepping for **`NEON`**, **`AVX2`**, **`tromp`**,
**`blake2`** or **`Equihash`** locates it quickly -- these terms cluster in the
material that is most duplicated, most transient, and least Zero-specific.
Current counts: `tromp` 120 times across 9 files (37 in `../equ/VENDORED.md`,
21 in `../equ/FINDINGS.md`, 19 in `../equ/METHOD.md`, 17 in
`../equ/SOLVER.md`); `NEON` 59 times, 34 of them in `../Perf.md`. Treat a high
count as the signal to cull, repartition or obsolete the file outright rather
than to edit it in place.

**Deferred from the 2026-09-03 pass** -- fixed at the source, not yet swept:

| # | What | Where |
|---|------|-------|
| 1 | 34 `NEON` mentions and the bulk of the tree's stale SIMD claims | `../Perf.md` |
| 2 | tromp and solver-internal material at a depth no Zero reader needs; S4 is a survey of other projects' implementations | `../equ/` |
| 3 | Transient shares inline in profile notes rather than cited from a capture | `../mine/*.md` |
| 4 | NEON-era wording | `../Measures.md`, `../README.md` |

**Correction on record (2026-09-03).** `PLAN.md` S5 claimed the merge loop
vectorises via "XOR and compare over 24-bit keys". That mechanism was never
verified against the source and is struck. The same pass asserted a build-time
claim about which SIMD kernel was active, which was both wrong and the kind of
status statement rule 4 forbids. Recorded because (d) exists to catch this
class: the failure mode is writing from inference rather than from the tree.

**Kanban: ToDo. Effort M.** No product code. Do (d) and (e) first -- they are
correctness, not tidying. (a) and (b) are the design decision and should be
agreed before (f) or (g) move any text.

---

## D -- parallel: Equihash and blake2

### D1. Integrate the queued Equihash / blake2 work

Developed in parallel with the sync investigation, benchmarked once integrated.
Why it is a separate track, its use cases, and what is established:
**`FINDINGS.md` S2**.

**A block of work, then separate items.** The checklist below is the
integration seam and holds whatever the parallel work contains. Individual
optimizations become their own items once landed, each with its own baseline.

| Step | What | State |
|------|------|-------|
| 0 | (192,7) analysis: findings, method, staged plan | **Finished** -- `../equ/` |
| 0a | (192,7) solver baseline vectors, 5 solutions, each verified | **Finished** -- `solver_baseline_192_7` |
| 0b | `Xc.reserve()` -- promoted to its own item; steps in **D2** | ToDo, V1 |
| 0c | Fold `len` to a compile-time constant -- own item; steps in **D3** | **Done, V1+V2+V4** -- 1.22x |
| a | Add new build-time options to `feature_bundles.json`; classify each | ToDo |
| b | Ensure `features.workload.op` distinguishes solve / verify / sync | ToDo |
| c | Record the baseline on the target host before any change | ToDo |
| d | Confirm `platform.arch` is carried -- SIMD results are arch-specific | ToDo |
| e | Keep the `blake2b` bucket ordered before `equihash` | ToDo |

Harness: `mine_bench.sh`, `performance-measurements.sh`, KATs in
`src/test/data/`. Analysis and plan: **`../equ/`**.

**Kanban: ToDo. Effort M**, dominated by (c).

### D5. Measure the vendored tromp solver -- priority, may reorder D2/S1

**Zero already ships tromp at (192,7)** and `prod.conf` selects it by default
(`equihashsolver=tromp`). Full finding: `../equ/FINDINGS.md` S2f.3.

Consequence: **every solver number in this tree measures the wrong binary for a
default miner.** `zcbenchmark solveequihash` calls `EhOptimisedSolve` directly,
so the 6.6 GB peak, the 60 s solve and the D3 1.22x all describe the
`default` path, which `prod.conf` does not select.

Method, and the four compatibility conditions that make the comparison valid:
**`../equ/METHOD.md` S3.2f**. Summary: identical `blake2b_state` object,
identical index encoding (both use `cBitLen`/`DIGITBITS` = 24), both
single-threaded, both verified in-loop. The one real difference --
tromp's `MAXSOLS = 8` cap -- is **measured, not equalised**.

| Step | What | Est. |
|------|------|------|
| a | Add `SOLVE_TIMING_SOLVER=default\|tromp` to the D4 harness; lift the driver verbatim from `miner.cpp:669-684` | ~1 h |
| b | **Solution-set equality first** -- same nonces, both solvers, compare sorted sets. This is a **V5** cross-implementation check, the strongest oracle in `METHOD.md` S3.2 | ~5 min |
| c | Paired per-nonce timing, n>=4, plus `nsols` from both | ~10 min |
| d | Peak `phys_mb` both -- tromp's two heaps vs `Xt`+`Xc`; compare against the ~3.3 GB computed in `../equ/FINDINGS.md` S1.2a | with (c) |
| e | Decide: continue S1 on `OptimisedSolve`, or shift to updating the vendored copy | -- |

**(b) before (c).** If the solution sets disagree, the timings are
uninteresting until that is resolved.

The vendored copy is **pre-Cantor** (`RESTBITS 4`, no `CANTOR` define), so it
predates his later bucket-count and packing work -- updating it is a candidate
in its own right.

**Result: tromp is 5.69x faster and 3.3 GB vs 6.6 GB** [Measured,
`../equ/FINDINGS.md` S2f.4]. V5 solution-set equality **passed** -- identical
sets across 4 nonces. No nonce reached 7-8 solutions, so `MAXSOLS` did not
truncate.

**So S1.2's memory work does optimise a path production does not select.**
The useful work moves to (e): the vendored copy is pre-Cantor and predates
tromp's later bucket-count reductions. Steps (a)-(d) are **Finished**.

**Kanban: ToDo. Effort S.** Measurement only, no product change.

### D2. `Xc.reserve()` -- steps

Gate **V1** (it cannot change which solutions are found). Evidence:
`../equ/FINDINGS.md` S1.1b. Do this **first**: it changes exactly one thing, so
its result discriminates between competing explanations of the 7.15 GB peak.
Folding it into a bundle wastes that.

**Where.** `src/crypto/equihash.cpp`, `OptimisedSolve`. `Xt` is reserved at
`522`; `Xc` is declared at `544` with no reserve.

**The names.** From the Biryukov-Khovratovich paper the file cites
(`equihash.cpp:8-13`), where **X** is the list of hash-derived strings being
collided. The suffixes are the implementation's:

| Name | Reads as | Role |
|------|----------|------|
| `X` | the list | `BasicSolve`'s single list of `FullStepRow` (untruncated) |
| **`Xt`** | X **truncated** | `OptimisedSolve`'s main list -- `TruncatedStepRow`, indices stored as `eh_trunc` (1 byte) rather than full `eh_index` (4 bytes) |
| **`Xc`** | X **candidates** | Per-round scratch holding newly merged rows before they are drained back into `Xt`'s freed slots |
| `Xi` | X **item** | One merged row, `:558` |

`t` is the meaningful one: it marks the whole optimisation `OptimisedSolve` is
named for -- storing truncated index tags instead of full indices, which is
what makes `TruncatedWidth` 70 rather than `FullWidth`'s 262. `Xc` is scratch,
and its lifetime is the subject of this item.

**`init_size` is `2^(CollisionBitLength+1)`** (`equihash.cpp:507`), so at
(192,7) it is `2^25` = 33,554,432 -- the leaf count, fixed for every solve and
every round. That is the ceiling `Xc` can ever need, which is why
`reserve(init_size)` is correct-but-generous rather than a guess.

**`Xc` is declared inside the `for (r...)` loop**, so it is constructed and
destroyed once per round, not once per solve. Two variants follow, and they
predict different peaks:

| Variant | Diff | What a null result tells you |
|---------|------|------------------------------|
| **V-a** in-loop `Xc.reserve(init_size)` | 1 line | If peak stays ~7 GB, per-round churn dominates, not the realloc transient |
| **V-b** hoist `Xc` above the loop, `clear()` per round | ~3 lines | If V-b drops and V-a does not, the cost is allocate/free, not growth |

**Does `clear()` zero the buffer? No.** It destroys the elements and sets
`size()` to 0, leaving `capacity()` and the allocation untouched. For
`TruncatedStepRow` -- a trivially-destructible fixed `unsigned char` array --
destroying an element is a no-op, so `clear()` compiles to little more than
`size_ = 0`. The old bytes are still in memory; they are simply unreachable,
and the next `emplace_back` overwrites them. That is exactly what is wanted:
**no zeroing cost, no reallocation, and the reserve survives into the next
round.** It is necessary because without it round *r* would append after round
*r-1*'s rows and the merge would read stale data.

**Round -> count, and how the reserve is tuned.** The mapping is not recorded
anywhere, and the tuning cannot be argued without it. `Xt` starts at
`init_size`; the list does not shrink much per round (the birthday property).
But `Xc` holds only rows merged *in that round* before the `posFree` drain
returns them, and the drain runs inside the collision loop -- so `Xc`'s
**high-water mark** is far below its throughput, and is **not derivable from
`init_size`**: it depends how far the producer runs ahead of the drain.

So `reserve(init_size)` is a **correct ceiling, not a tuned value** -- it cannot
under-reserve, so it cannot reallocate. V-a/V-b measure whether the ceiling
costs anything. Record what was reserved on every row so a later tuned reserve
is comparable.

**Two instruments, not one.** A single counter serving reserve tuning,
per-round-width weighting and `METHOD.md` S3.2d's debugging checksum
generalises badly -- the three want different data, at different cost, on
different schedules:

| Instrument | Wants | Cost | Lifetime |
|-----------|-------|------|----------|
| **P1** (this item) | `Xc` high-water and `Xt` final size per round, one `-debug=pow` line | one compare per `emplace_back` | Temporary -- delete once the table exists |
| **P2** (S3.2d, separate) | row count + checksum over sorted keys per round | a pass over the sorted list | Permanent -- every future differential |

P2 is a **correctness** instrument that must survive into every later
comparison. Fusing it with a one-shot tuning probe means paying the checksum
forever or losing it when the probe is removed. P1 is ~5 lines and answers the
reserve question; build P2 with the differential harness.

| Step | What | Gate | Est. |
|------|------|------|------|
| a | **Before** baseline, n>=4 `solveequihash`, `phys_mb` sampled | V4 | **~6 min** |
| b | Apply V-a, build, `--run_test=equihash_tests` (10 cases) | V0 | build + **~10 s** |
| c | `solver_baseline_192_7` differential -- all 5 solutions, exactly | V2 | **~2 min** |
| d | n>=4 timed solves + `res_sample.sh` `phys_mb` | V4 | **~6 min** |
| e | Revert V-a, apply V-b, repeat (b)-(d) | V4 | **~9 min** + build |
| f | Append both to the ledger, stamped, reserve size in `notes` | -- | ~5 min |

**Estimates assume the measured ~60 s/solve** (54.2-69.0 s, n=3). They exclude
build time, which dominates and is not a lab cost. Total lab time excluding
builds: **~30 min**. Replace with actuals when run.

```bash
./src/test/test_bitcoin --run_test=equihash_tests          # V0
DUMP_1927_SOLVER=test-logs/eqvectors/xc_reserve_va.txt \
  ./src/test/test_bitcoin --run_test=equihash_tests/solver_baseline_192_7
diff <(sort test-logs/eqvectors/solver_baseline_192_7.txt) \
     <(sort test-logs/eqvectors/xc_reserve_va.txt)         # must be empty
./src/zero-cli zcbenchmark solveequihash 4                 # V4
```

**Exit:** peak `phys_mb` for both variants, n>=4 each, identical solution set,
and a stated answer to "how much of the 7.15 GB was realloc transient" --
including "less than predicted", which is a result.

**Kanban: ToDo. Effort XS** (diff), **S** (measurement). Product change,
Zero400 review.

### D3. Fold `len` to a compile-time constant -- steps

Gate **V1** (it cannot change ordering). Evidence: `../equ/PLAN.md` S1.2b.
Do **after** D2 so the two effects are not conflated.

**Where.** `src/crypto/equihash.h:68-77`. `CollisionByteLength` is a
compile-time enum (`equihash.h:175`), but `CompareSR` takes it as a constructor
argument and stores it in a `size_t len` member, so the constant is laundered
into a runtime value and `memcmp(...,3)` compiles to a call into a generic
routine instead of a few inline instructions.

**Mechanism -- what the 3 bytes are, why the key sits at offset 0, and how the
25-vs-70 widths arise:** `../equ/FINDINGS.md` S3.1. Summary for this item: the
sort key is the first **3** bytes at every round, byte-aligned with no padding
at (192,7).

**Why `CollisionByteLength` at some sites and `hashLen` at others.** They sort
on different things. The per-round sort groups by the **next collision digit**
-- always 3, per the above. The final round and the partial-solution sorts
compare the **whole remaining hash**, and `hashLen` shrinks by
`CollisionByteLength` each round (`hashLen -= CollisionByteLength`). So
`hashLen` is genuinely variable, and at the *final* sort it is 3 as well
(`HashLength = 24`, minus 6 rounds x 3 leaves 6, and the final round compares 6
then trims to 3) -- but it arrives there as a runtime value, so folding it
would require per-round instantiation. That is the per-round-width work
(`../equ/PLAN.md` S1.2), not this item.

| Site | Function | Argument | Constant? |
|------|----------|----------|-----------|
| `359` | `BasicSolve` round sort | `CollisionByteLength` | yes |
| `417` | `BasicSolve` final sort | `hashLen` | no |
| **`538`** | **`OptimisedSolve` round sort** | `CollisionByteLength` | **yes** |
| `603` | `OptimisedSolve` final sort | `hashLen` | no |
| `673` | Partial-solution merge sort | `hashLen` | no |

**`538` is the only hot site.** It is the per-round sort over 33.5M rows inside
`OptimisedSolve`, which is what mining runs (`-equihashsolver` dispatch,
`miner.cpp:539`). `359` is the same sort in `BasicSolve`, which mining does not
use -- convert it for consistency if you like, but **attribute any measured win
to 538 alone**, and if you want the cleanest attribution, convert 538 only.

**Why a template, what varies, and where `size_t`/alignment land:**
`../equ/FINDINGS.md` S3.2. The three results that decide this item:

- `CompareSR`'s runtime `len` is a **leftover** -- `StepRow` was templated on
  width one day *after* `CompareSR` was extracted, and `len` was dropped from
  `StepRow` but not from the comparator. This finishes that refactor.
- The length is **constant per round and per iteration**, varying only across
  Equihash parameter sets -- which are already compile-time template arguments.
- `CompareSRFixed` is **shorter** than `CompareSR`: one member function, no
  state, no constructor.

```cpp
template<size_t LEN>
struct CompareSRFixed {
    template<size_t W>
    inline bool operator()(const StepRow<W>& a, const StepRow<W>& b) const
    { return memcmp(a.hash, b.hash, LEN) < 0; }
};
```

**Access.** `StepRow::hash` is `protected` (`equihash.h:50`) and `CompareSR`
reaches it via `friend class CompareSR` (`equihash.h:48`). **Make `hash`
`public` instead** and drop the friend declarations -- the class is an internal
solver row type with no invariant to protect, and every consumer is already a
friend. That removes a friend line per comparator rather than adding one, and
it is a prerequisite for the S1.2 per-round-width work, which will need several
more row-touching helpers.

| Step | What | Gate | Result |
|------|------|------|--------|
| a | `StepRow::hash` public; drop `friend class CompareSR` | -- | **Done** |
| b | Add `CompareSRFixed`; convert **538 only** | -- | **Done** -- 1 line in `equihash.cpp`, +17 in `equihash.h` |
| c | `equihash_tests` (10 cases) | V0 | **PASS** |
| d | Confirm the fold in the real build | -- | **PASS** -- 46 `memcmp` sites -> 0 in the `CompareSRFixed` path; the 44 left are `:603`'s runtime `hashLen`. Emits inlined `ldrh`/`ldrb`/`orr`/`rev`/`cmp` |
| e | `solver_baseline_192_7` differential | V2 | **PASS** -- sha256 identical, all 5 solutions |
| f | Paired fixed-nonce timing vs baseline arm | V4 | **1.220x mean, 1.212x median**, 4/4 nonces improving |
| g | Optionally convert 359 (`BasicSolve`, not used by mining) | V0 | Not done -- optional |

**Measured:** 1.22x on the solve, 1.71x on the sort phase in isolation. The
gap between them is expected: the solve also generates 33.5M leaves and runs
the merge, neither of which this touches. Peak footprint unchanged (6.6 GB) --
D3 alters no allocation. Detail: `../equ/FINDINGS.md` S3.2,
`test-logs/eqsolve-fixednonce-20260826/`.

**Remaining before Finished:** review on Zero400, which owns `src/`.

**Lesson recorded, because it nearly published a wrong number.** An unpaired
random-nonce measurement of this same change read **1.30x mean / 1.51x median /
1.59x min** -- all inflated by a favourable nonce draw. `zcbenchmark
solveequihash` randomises its input per trial, so spread is 29-49% and samples
cannot be paired across builds. The same nonce re-run repeats to **0.2%**.
Generalised: **when a benchmark randomises its input, pair the runs or the
input variance swamps the effect** (`../equ/METHOD.md` S3.2e).

**Interpreting the result.** This is a diagnostic as much as a fix: measured
alone it says how much of the sort cost is **call overhead** versus **data
movement**, which predicts how much Experiment B (extract the key once into a
`u32` array, `../equ/PLAN.md` S1.2b) can add. A near-null means the cost is
movement, and the 70 B swap width is the target.

**What comes after.** The size/range/distribution argument for replacing
`std::sort` with a counting sort -- and the bucket-count tuning that follows
from it -- is `../equ/FINDINGS.md` S3.3. That work is **S1.3, gated V2**. D3 is
the V1 patch that makes the current sort cheaper and measures how much of its
cost is call overhead, which is what says whether S1.3 earns its V2 gate. **Do
not start S1.3 before D3 reports.**

**Kanban: ToDo. Effort XS** (diff), **S** (measurement). Product change,
Zero400 review.

---

## F -- regression gating and CI

### F1. Where the gate attaches -- **implemented**

`contrib/perf/validate.sh` is the gate. Stages run fastest-first so a broken
tree fails in seconds:

| Stage | What | Default |
|-------|------|---------|
| `lint` | `lint-perf.sh`, failing on any owned-scope finding | on |
| `selftest` | every tool's `--self-test` plus `perflib` (15 total) | on |
| `harness` | `contrib/run-tests.sh --strict` | `--with-harness` |

`contrib/run-tests.sh` is Zero400-owned, so `validate.sh` **composes** it
rather than editing it. Verified to exit 1 on a seeded regression and 0 on a
clean tree -- a gate that reports FAIL but exits 0 is not a gate, and this one
did until the summary loop was moved off a pipeline.

**Kanban: InTest.** Exit condition: run it from a clean checkout on another
machine.

### F1b. Where the stamp is emitted -- **decided, shipped**

Three options were weighed for A2d; **B was chosen and has landed**. Stamping
happens in `accumulate_bench.py` / `profile_collate.py` at row-append, not in
each of the 10 launchers, which makes the invariant structural rather than
procedural: an unstamped row is unrepresentable. Per-launcher calls would have
been ten chances to forget; post-hoc backfill would have recorded a guess.

Two caveats it had to handle, both live in the code now: the writer runs after
the node exits, so `build.*` comes from the binary that actually ran rather
than whatever `src/zerod` is at write time; and `features.workload` is passed
in by the launcher, since the writer cannot infer it.

**Kanban: Finished.** What still keeps A2 in InTest is A2e/f, not this.

### F2. CI wiring -- **Postponed**

Separated from F1 because it needs something no code change provides:
repository settings access. `.github/workflows/tests.yml` triggers on push to
`[main, master, develop]`; the working branch is `perf-402`, so direct pushes
run no CI at all.

**Consequence while postponed:** every gate is **local only**. A contributor
who does not run `lint-perf.sh` bypasses all of it. F1 reduces but does not
remove this -- a local `validate` target still has to be run by a person.

Needed to unblock: add the working branch to the push trigger, and add a lint
job ahead of the 240-minute build.

---

## E -- script corpus and safety

### E1. Shared shell library

`perflib.sh` replaces helpers that had been copied and had drifted: `log()` was
byte-identical in 6 scripts, `cli()` in 5, `stop_node()` / `height_of()` in 3
each. It also owns the value guards and the datadir policy.

| Step | What | State |
|------|------|-------|
| a | `perflib.sh` + `perflib_selftest.sh`, gated | **Finished** |
| b | Datadir disposition policy, default `aside` | **Finished** -- `POLICY.md` S3.1 |
| c | Value guards: `require_num`, `nonneg`, `positive`, `safe_div`, `span_blocks` | **Finished** |
| d | Divide-by-zero guards in `bucket_profile2.py`, `shielded_density.py` | **Finished** |
| e | Unified datadir mapping (`zeropaths.py`) mirroring `GetDefaultDataDir()`, plus platform-independent production-datadir protection | **Finished** |
| f | Migrate launchers onto `perflib.sh` | **Finished** -- 9 of 9; every datadir wipe routes through `dispose_datadir` |
| g | `rm -r` by default, `-f` only under `ZERO_PERF_FORCE` / `--force` | **Finished** |
| h | Rename `check-unicode.py` -> `fix_ascii.py`; `--all-paths` / `--ascii-formula`; Y/n confirm replaces `--yes` | **Finished** |

**All 9 launchers migrated.** The only `rm -rf` calls left on a datadir path
are `dispose_datadir`'s own implementation, a temp-dir trap in the self-test,
and two `$SCRATCH/chainstate` subdirectory wipes, which are not datadir resets.
All local `log()` copies are gone.

#### Reuse gaps

**5 of 17 shell scripts do not source `perflib.sh`.** E1f counted launchers and
was accurate on that scope; these five were outside it. `perflib.sh` provides
`log`/`warn`/`die`, `utc_stamp`, `run_id`, the value guards, `dispose_datadir`
and `stop_node`.

| Script | Duplicates | Action |
|--------|-----------|--------|
| `prep_lab_datadir.sh` | `refuse_protected` re-implements `_perflib_is_protected` | Call perflib's |
| `datadir_guard.sh` | `is_default_datadir`, `is_live_datadir` | Thin wrapper over perflib |
| `res_sample.sh` | `cli()` -- the **timeout-guarded** variant | Promote to perflib |
| `profile_run.sh` | own UTC stamp, own `height_now` | `utc_stamp`, `height_of` exist |
| `ops-campaign.sh` | -- | Source for `log`/`die`/`run_id`; keep catalog logic |

Three overlaps, in priority order:

1. **Datadir protection has three implementations** -- `perflib.sh:147`,
   `prep_lab_datadir.sh:37`, `datadir_guard.sh:33`. This is the guard that stops
   a lab destroying the production datadir. **A safety check with three
   implementations has three behaviours**, and POLICY S3.1 records that this
   class of bug already destroyed a datadir once.
2. **`cli()` exists twice and the safer version is not the shared one.**
   `res_sample.sh:34` wraps in `timeout`; `witness_lab.sh:78` does not. The
   unguarded one is exactly the documented `getwalletinfo`/`cs_wallet` blocking
   hazard. Promoting the guarded version turns a caveat into a default.
3. **Three UTC formats across 16 sites** -- compact for filenames, ISO for row
   fields, human for logs. All legitimate; only two are in perflib.

Steps:

| Step | What | State |
|------|------|-------|
| i | Consolidate datadir protection on `_perflib_is_protected`; the other two call it | ToDo |
| j | Promote the timeout-guarded `cli()` into `perflib.sh`; `witness_lab.sh` uses it | ToDo |
| k | Add `utc_iso()` beside `utc_stamp()`; migrate ad-hoc `date -u` sites | ToDo |
| n | `checkpoint_row()` in `perflib.sh` -- append-only `progress.tsv` writer | ToDo |
| o | `res_sample.sh` gains a `progress.tsv` output mode calling it | ToDo |
| p | Collate `progress.tsv` -> ledger post-run via `accumulate_bench.py --import-tsv` | ToDo |
| q | State the restartability axis in `POLICY.md` S4 beside the ~20 min heuristic | ToDo |
| m | Source `perflib.sh` in the remaining 3 scripts for `log`/`die`/`run_id` | ToDo |

(i) is the one that matters; the rest are tidiness with a small safety
component.

**Kanban: InProgress. Effort M**, dominated by (e) and (f).

---

## Blockers and incomplete work

Stated explicitly so nothing above reads as finished when it is not.

| Item | State | What is needed |
|------|-------|----------------|
| **A2c** `features` back-annotation | **Open** | `platform` landed on all 49 rows; `features` is `{}` on every one. Done as A4f |
| **A2e/f** fingerprint v2, pooling guard | **Open** | A2f is what refuses to pool a Linux row with a macOS one. Blocks A2 leaving InTest |
| **A4** workload `op` enum | **Open** | `--op` is unvalidated free text, so the S5.1 guard has no workload key. Blocks C4 |
| **C4** two empty cells | **Blocked, not slow** | `many-utxo-few-tx` needs a wallet that does not exist; the x86-64 column needs B2 |
| **GROTH** | **Postponed** | A maintainer's decision; nothing else depends on it |
| **`Perf.md` retirement** | **Not ready** | Holds detail for B1, B3 and GROTH. Re-run the caveat diff (`MIGRATION.md` S6) before retiring |

---

## Aside -- postponed, pending review

**Renamed from "will not do".** Nothing here has been refused on the merits;
each was set down because something else was worth more at the time, or because
the evidence then available said the return was small. That is a **judgement
against a snapshot**, and several of the snapshots are already stale -- the
Equihash analysis (`../equ/`) re-examined NEON on the mining track after it had
been set aside on the sync track, and found the share larger but the work
harder. That item has since been **settled outright**: the kernel was built in
uniblake and measured slower than scalar, so it left the Aside list as a
negative result rather than as a reopened one. That is the pattern this rename
anticipates -- the snapshot changes, so the judgement is revisited; a revisit
can close an item as readily as reopen it.

Each item states the condition that would reopen it. An item with no such
condition is either genuinely closed or has not been thought through -- both
worth knowing.

| Item | Reason set down | What would reopen it |
|------|-----------------|----------------------|
| Drop `cs_main` during the witness height walk | Abort-and-restart cannot converge once walk time exceeds block spacing | A design that checkpoints rather than restarts; or NOTEIDX reducing walk time below spacing |
| CleanIndex gtest harness | Needs anchors and disk-backed blocks the gtest harness lacks | `reindex_shielded.py` proving insufficient, or the gtest harness gaining disk-backed fixtures |
| FDCACHE buffer-size sweep | Measured null (`FINDINGS.md` S3.2) | A workload that is **not** CPU-bound -- a slower-storage host, random `getblock` serving (A5-a2), or post-Groth-batching |
| SIMD for the Equihash round merge | Not analysed | **TBD, on hold.** Reopens on a decision to invest in arm64 mining |
| Halo / Orchard | Not Zero consensus | A deliberate NU that adopts them. Not a lab decision |
| Post-Sapling bootstrap / sync captures **as a comparison** | A and B agree within ~3 points (`FINDINGS.md` S3.4) | Superseded in part: C4 schedules these as **utilization** cells, which is a different question than re-proving the equivalence |
| Remove dead `nNotarizations` | Not worth a commit of its own | `chain.h` being touched for another reason |
| Native Windows ETW profiling | Blocked on symbol format and an unvalidated MXE build path (`../PerfPlatforms.md`) | A validated Windows build, which is a prerequisite anyway. Reopens if Windows becomes a mining target (`../equ/PLAN.md` S8) |

---

## Lessons carried forward

Not a changelog -- the per-item record is in the tables above and in
`FINDINGS.md`. These are the **generalized findings**, stated so they apply to
the next investigation rather than only describing the last one.

| Lesson | Generalized form | Where it came from |
|--------|------------------|--------------------|
| **A guard with N implementations has N behaviours** | Safety checks (datadir protection, value guards) get exactly one implementation, called from everywhere | Three copies of the datadir guard; one datadir destroyed |
| **An invariant enforced procedurally will drift; enforce it structurally** | Put the check where the data must pass, not where a caller must remember. Stamping at the ledger writer makes an unstamped row unrepresentable | F1b, chosen over per-launcher calls |
| **A rule nobody checks is a comment** | Every written rule needs an enforcement point or an explicit note that it is advisory | ASCII rule drifted to 693 violations; `M-*` citation rule to 5 restatements |
| **A tool that has never failed a test has never been tested** | Self-tests gate the harness, not just the product. Five number-corrupting defects surfaced only when coverage was completed | `FINDINGS.md` S1.4 |
| **Measure a null and it becomes evidence; assume it and it stays a guess** | A measured negative result is publishable and stops work. Two did | FDCACHE; I/O tuning |
| **Profile when the bottleneck is unknown; benchmark when it is known** | Benchmarking an unknown bottleneck measures noise against noise | FDCACHE A/B (`FINDINGS.md` S3.2) |
| **First-match-wins attribution makes ordering load-bearing** | Any classifier whose rules overlap must have its order treated as code, not formatting | Four published figures wrong from bucket order |
| **A number without its window, platform and build is not comparable** | Record the conditions with the measurement or it cannot be aggregated later | Every pre-schema row came from one host and nothing said so |
| **A reference oracle stored once, writable, is not a reference** | Anything later changes are validated against gets archived and made read-only *before* the work starts | V2 solver baseline sat at the path its regenerator writes to |
| **Restartability, not duration, decides whether a long run is safe** | Checkpoint and collate separately: the trial appends, a later pass reads | ~20 min heuristic misapplied to an unrestartable multi-hour trial |
| **Sequence changes so each one's effect is attributable** | Two changes measured together answer neither question | D2 before D3; both against the preceding baseline |
| **If the benchmark randomises its input, pair the runs** | Otherwise input variance swamps the effect and the difference of means is partly the draw | Random-nonce solve read 1.30-1.59x; paired read **1.22x** |
| **A constant passed as an argument is not a constant to the optimizer** | To be folded it must reach the use site in the **type**, not in a member | `CompareSR`'s `size_t len`: 46 `memcmp` calls survived |
| **Prefer finishing an old refactor to adding a new mechanism** | Check whether the surrounding code already solved the problem and the site was missed | `CompareSR`'s runtime `len` is a leftover from the day before templates landed |
