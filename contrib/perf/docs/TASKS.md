# Tasks

Work items and their state. The only place a task id lives, so two records
cannot disagree. Items are listed, not explained: each names its subject and
links to the document that owns it (`MAP.md`).

Status (`POLICY.md` S1): Kanban ToDo -> InProgress -> InTest -> Finished;
disposition Open | Blocked | Finished | Postponed | Aside. Aside means
postponed pending review, not refused.

## Board

| Item | Kanban | Disposition | Effort | Why |
|------|--------|-------------|--------|-----|
| A3 Microbenchmark baseline | ToDo | Open | S | `FINDINGS.md` S4 |
| A4 Workload taxonomy A-E | ToDo | Open | S-M | this file, A4 |
| A5 CodexPerf review triage | **InProgress** | Open | M | `../../CodexPerf.md` |
| B2 First non-macOS measurement | ToDo | Open | M | `../PerfPlatforms.md` |
| B2a Suite-run gotchas | ToDo | Open | S | four results that look like defects |
| C1 Documentation consolidation | **InTest** | Open | M | `MIGRATION.md` |
| C2 Remaining measurement gaps | ToDo | Open | M | `FINDINGS.md` S4 |
| C3 Inherited build/DB defects | ToDo | Open | M | `../BUILD_RECONFIG.md` |
| C4 Per-workload utilization profile | ToDo | Open | L | this file, C4 |
| D1 Equihash / blake2 integration | **InProgress** | Open | M | `../equ/README.md` |
| D2 `Xc.reserve()` | ToDo | Open | XS | `../equ/FINDINGS.md` S1.1b |
| D3 Fold `len` to compile-time | **InTest** | Open | XS | **1.22x solve measured**; `../equ/FINDINGS.md` S3.2 |
| D5 Measure the **vendored tromp** path | **InTest** | Open | S | **5.69x, V5 PASSED**; `../equ/FINDINGS.md` S2f.4 |
| F1 Regression gate on validate | **InTest** | Open | S | `validate.sh` |
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

**GROTH** -- Sapling Groth16 batch verification. Everything about it,
including the librustzcash dependency it rests on, is `../PerfGroth.md`.

- Batch verification: awaiting a maintainer's choice
- **Precondition: close C1 documentation work, finish Tests, and cut an
  reference benchmark (5-10 trials preferred) before any algorithm experiment.** Rationale and
  the exception (fork-for-custody, which is packaging) in `../PerfGroth.md`
- **Attempt the Ycash/Pirate-level move directly (M).** Proven in action:
  each fork is upstream history plus ~3 project-specific commits (network
  prefixes, activation heights, encoding), both trees checked out at
  `ZK/ZKs/rustzcash/`. Not research -- a bounded change of known shape
- **Host downloadable artifacts under project control.** 741 MB of Zcash
  parameters from `download.z.cash`, the librustzcash tarball, and lab
  snapshots with no canonical source. Parameters are hash-verified so a mirror
  adds no trust; independent of the fork decision
- **Fork for custody (S, no consensus risk).** Take `06da3b9a` into
  `zerocurrencycoin/librustzcash` unchanged, on a node branch with `master` left
  mirroring upstream; acceptance test is a
  byte-identical `librustzcash.a`. Then move `librustzcash.h` into
  `src/rust/include/`. Recommendation, counter-arguments and what would change
  it: `../PerfGroth.md`
- **Dependency, and it constrains the above:** Zero pins librustzcash
  `06da3b9a` (2018-10-27), **6724 commits** behind, and the C FFI crate it
  pins **no longer exists upstream** -- moved into `zcash/zcash`. There is no
  newer version of what Zero consumes
between Option A and Option B; the options diverge at the FFI boundary, so
starting either wastes the other. Prototype frozen.

Everything: **`../PerfGroth.md`**. Nothing below depends on it.

---

## A -- do first

### A3. Record the microbenchmark baseline

`M-ZCB-SUITE` has no numeric archive. Runner exists
(`performance-measurements.sh`).

Time-sensitive in one direction: a batching result needs a per-proof baseline
taken beforehand, so this is worth more during the postponement than after.

**Kanban: ToDo. Effort S.**

### A4. Name the demanding workloads, and make the names selectable

`features.workload.op` is the field that keeps a solve trial from pooling with
a reindex trial (`SCHEMA.md` S5). It is currently a **free-text string** --
`stamp.py --op` has no enum and no validation -- so the guard that
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
| b | Validate `--op` against it in RecBench; refuse an unknown value rather than recording it | ToDo |
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
| **P0** | FDCACHE: `CacheOpen` releases `LOCK(latch.cs)` at function exit, then the caller deserializes through the shared `FILE*` unlocked | **CONFIRMED** (`main.cpp:4924`; read sites `:2130`, `:2617`) | **Real.** Another thread can `fseek` or `fclose` the same stream mid-read |
| **P1** | `-mrclogevery=0` divides by zero | **CONFIRMED**, since fixed (`main.cpp:3254`, `:4971`) | **Real.** `nHeight % logEvery` was unvalidated at both sites; both now read the startup-validated `nPerfLogEvery` (step b) |
| P1 | FDCACHE probe always reports false -- flags absent from `HelpMessage` | Not re-checked | Plausible; affects provenance labelling |
| P1 | CI builds neither `--enable-perf` nor the perf lint | Consistent with F2 | Already tracked as **F2** (Postponed, needs repo settings) |
| P2 | Evidence set larger than authoritative; doc drift | **CONFIRMED** one case | `POLICY.md:68` said `unicode-docs` was not in default `CHECKS`; it is (`lint-perf.sh:107`). **Fixed** |
| P2 | Portability unproven, one host | Agrees with `FINDINGS.md` S4 | Already **B2** |
| P2 | `--enable-perf` couples counters with behaviour change | Accurate reading of `configure.ac` | Worth splitting; see (c) |
| P3 | Out-of-scope wallet docs in `keep/` | Agrees with `NOTES.md` | Already **C1c** |
| P3 | `git diff --check` trailing whitespace | Not re-checked | Cheap CI addition |

**The P0 finding contradicted a claim in our own documentation.**
`Perf.md` S3 called the implementation "functionally correct"; the lock
lifetime does not support that. This is the review's most valuable
contribution and the reason it is worth acting on rather than filing.
The claim is now **retracted** in place (step d), so the two records agree.

| Step | What | State |
|------|------|-------|
| a | **FDCACHE retained** pending x86-64 Linux and Windows validation (B2). Fix the lock lifetime **before enabling** it with concurrent readers: RAII lease across seek+read, or positional `pread` | **Deferred to B2** |
| a2 | Measure FDCACHE on the two workloads where the mechanism could pay: **random `getblock` RPC** and **cold cache / slow storage** | ToDo |
| b | Validate `-mrclogevery` at startup | **Finished** -- `InitPerfLogEvery()`; 3 build configs clean |
| c | Split `--enable-perf` into counters (safe) and experimental behaviour (FDCACHE) | ToDo |
| d | Correct `Perf.md` S3 -- retract "functionally correct" and cite the lock-lifetime defect | **Finished** 2026-09-08 -- retracted in place, both read sites named, reachability and the required fix stated |
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
`use of undeclared identifier`. That is the class of breakage F2/A5
flags as invisible to current CI -- and an argument for the `--enable-perf` CI
job, independent of FDCACHE's disposition.

**FDCACHE: RETAINED, by owner decision.** Optional perf instrumentation, not
shipped behaviour; kept at least until x86-64 Linux and Windows results exist.
Why it is retained, the two unmeasured cases that could still pay, and the
concurrency bound on the RPC case are **`../Perf.md` S3**, which owns the
subject. A5-a2 is the task for measuring them.

**Assessment of the review itself: accurate and useful.** Every claim spot
checked held up against the source, including one that contradicts our own
documentation -- which is the kind of finding an internal reviewer is least
likely to produce. Its P2/P3 items largely restate work already tracked (B2,
C1c, F2), so its marginal value is concentrated in P0 and the two P1 defects.

**Kanban: InProgress. Effort M.**

### B2. First non-macOS measurement

Survey: **`../PerfPlatforms.md`**.

| Step | What |
|------|------|
| a | State the platform caveat wherever CPU numbers are published |
| b | Document the `parse()` input contract in `bucket_profile2.py` |
| c | Linux `perf record` + folded-stack parser | **Finished** -- `bucket_profile2.py` parses folded stacks; format detected by content, self-tested |
| d | Port `res_sample.sh` to `psutil` | ToDo -- needs a Linux host to validate against |

**Requires A2** so the result is recordable -- now satisfied: A2f landed, and
RecBench records platform, build, config and dataset identity, so a Linux row
cannot pool with a macOS one or be dropped as a duplicate.

**Running it on Linux.** Everything below is a command; nothing needs a design
decision first.

```bash
# 1. capture (perf, root or perf_event_paranoid<=1)
perf record -F 999 -g -p $(pgrep -f 'zerod') -- sleep 300
perf script | stackcollapse-perf.pl > out.folded

# 2. bucket it, same tool and buckets as the macOS path
python3 contrib/perf/bucket_profile2.py out.folded all --json out.json

# 3. record the result
python3 contrib/perf/recbench/recbench.py --append \
  --campaign linux-baseline --run-id linux-$(date -u +%Y%m%dT%H%M%SZ) \
  --workload op=reindex --workload snap=tiny ...
```

The parser takes folded stacks or xctrace XML and decides by content, so a
Linux capture and a macOS capture bucket through the same `classify()` and
compare directly. `--thread all` is needed on the Linux path: folded stacks
carry no thread name.

**What still needs the host:** (d), because `psutil` sampling behaviour cannot
be validated against a `ps` path that does not exist on macOS. (a) is doable
anywhere and is folded into C5.

**Kanban: InProgress. Effort M.**

**Suite-run gotchas to carry into any platform run**

Four results that look like platform defects and are not. Each cost time once.

| Item | What |
|------|------|
| a | **`Tests completed:`, not just exit code.** A runner can exit 0 having run nothing: a guard that declines to start the payload, or a killed waiter, is indistinguishable from a clean pass. Confirm the marker, then cross-check the totals against the per-script lines (`require_marker`, `require_counts_agree`) |
| b | **uniblake sibling.** Resolves to the checkout beside this tree with no configuration; its short HEAD is the package version, so a uniblake commit rebuilds it on its own |
| c | **Deliberately held.** `WalletTests.CachedWitnessesCleanIndex` is excluded in `qa/zcash/test_filters.sh` and fails unfiltered on every platform -- its reindex scenario needs the `pcoinsTip` + `ReadBlockFromDisk` path the gtest harness cannot provide |
| d | **`Permission denied` is a file mode**, not a port problem. `core.fileMode=true` strips a local `+x` on checkout, so a test committed `100644` fails before it runs. Check `git ls-files -s` first |
| e | **A skip is not a pass.** Three more instances found by sweeping for the shape: `check-security` failures were discarded by `\|\| true`; `rpc-tests.sh` fell off the end with status 0 when wallet/utils/bitcoind were not all enabled; and a tier selecting nothing printed "Tests completed: 0" and exited 0. All now fail |

**Kanban: ToDo. Effort S.** Documentation only; (a) is already wired into
`contrib/run-tests.sh`.

### B3. NOTEIDX staleness

**Moved** to Product handoff P2: the invalidation call sites are wallet code,
so the fix belongs in the product tree. Evidence stays here.

---

## C -- after B

### C1. Documentation consolidation and clean-up

Analysis and partition plan: `STRUCTURE.md`. Placement rules: `MAP.md`.

| Step | What | State |
|------|------|-------|
| a | Build the docs set, pulling material in incrementally | **Finished** |
| b | `NOTES.md`: stamp dated evaluations with date and version | ToDo |
| c | Route by reader type; one subject per file | ToDo |
| d | Segregate deep internals behind a marked boundary | ToDo |
| e | Strike obsolete history; remove, do not narrate | **In progress** -- SIMD/status swept 2026-09-06 |
| f | Purge mechanism claims not traceable to code or measurement | ToDo |
| g | Fix `SCHEMA.md` statements contradicted by the store | ToDo |
| h | Fold or archive `Perf.md`'s status sections into this file | ToDo -- `STRUCTURE.md` S4 steps 2-3 |
| i | `equ/`: figures bound to `M-EQ-*` ids | **Finished** 2026-09-06. The "215 restatements" were mostly derivations; 27 bare, most already cross-referenced |
| n | **Cut tables.** Detail, examples and criteria below | ToDo |

#### C1n. Tables: prevalence, criteria, and what to do

**Prevalence** [re-measured 2026-09-08]. 472 tables across 40 table-bearing
documents (43 markdown files scanned). **84 fail the size threshold** and
**13 files exceed the ten-per-file ceiling**. Three files hold a third of all
tables: `Perf.md` 64, `TASKS.md` 48, `equ/SOLVER.md` 43.

The figures move as the documents are edited, and this file is one of the three
offenders: an earlier revision recorded 469/84 with `TASKS.md` at 45, and the
task list gained tables while describing the table problem, then shed one when
the FDCACHE exposition moved out (T5a). Re-run
`check_tables.py` rather than trusting the count here -- the checker is the
authority and these numbers are a snapshot of it.

**Criteria, enforced by `check_tables.py`, reported in `lint-perf.sh`:**

- at least **2 data rows**
- **rows x columns at least 9**
- at most **10 tables per file** -- a ceiling, not a target

A 2x5 A/B passes; a 2x2 does not. The threshold cannot see content, so passing
it is necessary and not sufficient.

**Failing shapes, most common first:**

| Shape | Count | Usually is | Replace with |
|---|--:|---|---|
| 2 x 3 | 20 | a pair of items with a note each | two sentences |
| 4 x 2 | 18 | a labelled list | vertical list |
| 3 x 2 | 16 | a labelled list | vertical list or prose |
| 2 x 4 | 10 | sometimes a real A/B -- read it | keep if the columns differ meaningfully |
| 2 x 2 | 9 | a phrase | one sentence |

**Worked failures.**

`PerfPlatforms.md:18` -- 4x2, `Tool | macOS-only dependency`. A list of four
tools and what each needs. A vertical list carries it without the grid.

`Measures.md:363` -- 3x2, `Layer | Format`. Three layers, one format each;
three sentences or a vertical list.

`Perf.md:759` -- 2x3, `Item | Change | Validation`. Two items. Two sentences.

**Worked improvements, already applied.**

`Measures.md` -- twelve tables shared the header
`ID | Metric | Result | Type | Tools | Source`: one relation split twelve ways
by section heading, six of them holding three rows or fewer. Category became a
**column**, the twelve headers became one, ten now-redundant headings were
removed. All 105 `M-*` ids survive. 25 tables to 12 headers over one relation.

`docs/PRODUCT.md` -- 12 to 10. Two list-shaped tables became prose: three call
sites with their false-return handling, and three tests with what each pins.

`docs/HASHLIBS.md` -- 12 to 9. Three tables in S1 duplicated the fuller
inventory in S1.4 and became four sentences.

`PerfGroth.md` -- a 1x2 table holding two comma-separated crate lists became
two sentences.

**Automation and what it tracks.**

| Tool | Tracks | Gate |
|---|---|---|
| `check_tables.py` | table size, per-file count | reported, not gated -- the failing set predates the rule |
| `check_concentration.py` | one owner per subject (`MAP.md` S3) | reported, not gated |
| `check_citations.py` | figures carry an `M-*` id; no absolute paths | **gating** |

`check_tables.py` is self-tested on five boundary cases -- 3x4 passes, 1-row
fails, 2x2 fails, 2x5 passes, headerless continuation block passes -- and each
assertion is mutation-tested. It found a bug in its own first version:
continuation blocks of a table split by prose have no header row, and
subtracting one reported five real registry rows as one-row tables. 88 dropped
to 84 when that was fixed.

**Order of work.** The three largest files are already scheduled for splitting
(S3 in `STRUCTURE.md`); a table that moves to the document owning its subject
usually stops duplicating one three sections away. Do the splits first, then
sweep what remains against the threshold.
| j | Concentration checks in `lint-perf.sh` | **Finished** 2026-09-07 -- `check_concentration.py`, reporting not gating |
| l | Library inventory consolidated in `HASHLIBS.md` | **Finished** 2026-09-08 -- libsodium 15 functions / 4 subsystems, librustzcash 31 of 32, uniblake 18 calls, three linked blake2b implementations |

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

Requires A4 (workload classes selectable). Durations are estimates until
actuals replace them; automation must not overwrite prior results.

**Columns per class**

| Class | Columns that matter |
|-------|--------------------|
| A, B | blk/s, CPU% of one core, thread count, bucket shares, height window |
| C | blk/s, CPU% , witness-scan share, `mapWallet` size, wallet MB, tx count |
| D | s/solve, Sol/s, **peak phys MB**, CPU% , thread count |
| E | bucket shares only -- a *modifier* on A/B, reported as a column split |
**M4 and x86-64 report as separate columns, never one mean**

| Property | Apple M4 Pro | x86-64 | Consequence |
|----------|-------------:|-------:|-------------|
| Cache line | **128 B** | 64 B | 70 B row: 1.53 vs **2.06** avg lines |
| Base page | **16 KB** | 4 KB | 2.19 GB buffer: 143,524 vs **574,095** pages |
| Vector width | 128-bit | AVX2 256 / AVX-512 512 | 2 vs 4-8 BLAKE2b lanes |
| L2 | 16 MB shared | 1-2 MB private | Bucket sizing differs |

**C4 durations -- rough, to be replaced with actuals**

**These are projections from those rates, not timings of these specific runs**
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
**Is the ~20 minute rule the right threshold here?** It is the right *rule* on
| Case | Duration | Restartable? | Verdict |
|------|---------:|--------------|---------|
| reindex post-Sap window | ~17 min | yes, per trial | Under the threshold, and safe anyway |
| bootstrap post-Sap | ~17 min | yes, per trial | Same |
| **fat rescan** | **hours** | **no -- one indivisible scan** | The rule's 20 min says nothing useful; what matters is that it cannot resume |
| P2P sync | unbounded | resumes naturally | Long but self-restarting; the rule does not bite |
**Checkpoint often; collate separately.** This is the operating rule for every
| Case | Checkpoint feasible now? | How |
|------|--------------------------|-----|
| **Fat rescan** | **Yes** | Per-height rates are already in `debug.log`; `res_sample.sh` is already the sampler. Wire both to `progress.tsv` |
| **Network sync** | **Yes** | Same, plus `peer_count`. Already the natural shape for a run with no fixed end |
| **Post-Sap reindex/bootstrap** | Yes, and cheap | ~17 min, already restartable; checkpointing costs nothing and makes an interrupted run usable |
| **Solve (192,7)** | **No -- do not** | One solve is ~60 s and atomic; there is no meaningful mid-solve state. Sample `phys_mb` on an interval instead, which `res_sample.sh` already does |
**Network sync: reproducible, environment-dependent, high variance.** The
| Field | Why it is a column |
|-------|--------------------|
| `peer_count` at start and mean | The first-order determinant of rate |
| `from_height`, `to_height` | Tip distance at start; the run is not comparable without it |
| `wall_s`, blk/s **by region** | Aggregate rate hides the pre/post-Sapling split |
| Stall events by class | `tip_gap`, `tip_silent`, `timeout_burst` from `stall_check.py` |
| `started_utc` | Time-of-day and network-conditions proxy |
| n, and **min/max, not just mean** | With variance this high, a mean alone misleads |
**Separate audience from reindex, and say so in the schema, not in prose.**
**Precision is set by what shows up in the data, not by an audience judgement.**
| Output | For | Content |
|--------|-----|---------|
| Ledger rows | Lab | `op: sync`, full field set above, n>=3, spread reported |
| Operator note | README / BUILD_ZERO | Observed range and what normal progress looks like, so a slow sync is distinguishable from a stuck one |

**C4 automation, and not overwriting prior results**

**Initial runs are ad-hoc by design** -- the first trial of anything is a
**What already protects prior results** (verified, not assumed):
| Mechanism | Guarantee | Where |
|-----------|-----------|-------|
| `append_row` | Append-only, and a re-append of an identical trial is **skipped**, not duplicated | RecBench `append_row` |
| Datadir `aside` default | A re-run renames the old tree to `<path>.aside-<utc>` rather than deleting it | `POLICY.md` S3.1 |
| `archives/` never reclaimed | Hard-coded non-reclaimable, independent of age or size | `retention.py`, `POLICY.md` S6.4 |
| Per-run logs | `validate.sh` logs per run, so a failure is not overwritten by the next green run | `POLICY.md` S3.2 |
| Gap | Risk | Fix |
|-----|------|-----|
| `DUMP_1927_SOLVER=<path>` | Same filename each run silently overwrites the previous solver dump | Write `solver_<variant>_<utc>.txt`; never reuse the baseline's name |
| `test-logs/eqvectors/solver_baseline_192_7.txt` | It is the **V2 reference**. Overwriting it destroys the oracle every later change is checked against | Mark read-only; copy to `test-logs/archives/` before any D2/D3 work begins |
| Instruments captures | `profile_run.sh <name>` reuses a name if given one | Include the UTC stamp in the scenario name |
**The baseline dump is the one that actually matters.** If it is regenerated
**Script reuse is E1's subject, not C4's.** Survey, findings and actions:
**E1, "Reuse gaps"**. What matters here is only that the C4 campaign needs
| New need | Existing helper |
|----------|-----------------|
| Checkpoint sampling | `res_sample.sh` interval sampler + `phys_mb` (E1o) |
| Progress -> ledger | `recbench.py --import-tsv` (E1p) |
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
**Do not automate** the ad-hoc first run of anything, or the fat rescan until
| Step | What | State |
|------|------|-------|
| a | Fixed column set per class, above | ToDo |
| b | Generate from the ledger, not by hand -- a hand-copied figure is a restatement (`README.md` rule 3) | ToDo |
| c | Empty cells for unmeasured combinations, named as gaps | ToDo |
| d | Arch as a **column split**, never a pooled mean | ToDo |
| e | **Archive `solver_baseline_192_7.txt` and mark read-only** -- prerequisite for D2 | **Finished** -- `archives/eqvectors-solver-baseline-192-7-20260825.tar.gz`, sha256 `3154de69`, source now `0444`. Both paths PROTECTED in `retention.py` |
| f | Stamp variant and UTC into every dump/capture path; no fixed-name writes | ToDo |
| g | Network sync as `op: sync` rows, n>=3, spread reported, plus an operator note derived from them | ToDo |
**Kanban: ToDo. Effort L**, dominated by actually running the missing cells.

## D -- parallel: Equihash and blake2

Subject owner: `../equ/`. Substance moved there 2026-09-06; this section lists
items and state only.

| # | Item | State | Effort | Detail |
|---|---|---|---|---|
| D1 | Integrate the queued Equihash / blake2 work | **InProgress** | M | `../equ/README.md` |
| D2 | `Xc.reserve()` sizing | ToDo | S | `../equ/PLAN.md` (queued solver work) |
| D3 | Per-variant solve measurement | ToDo | M | `../equ/METHOD.md` |
| D4 | Keep the `blake2b` bucket ordered before `equihash` | ToDo | S | `../equ/PLAN.md` |

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
happens in RecBench / `profile_collate.py` at row-append, not in
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
| p | Collate `progress.tsv` -> ledger post-run via `recbench.py --import-tsv` | ToDo |
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

## Product handoff

Changes this investigation identified that are **node code**, not lab tooling.
They cannot be done from ZeroPerf, but they are tracked here, with the rest of
the perf work, rather than in the product backlog: the evidence for each lives
in this tree and splitting the item from its evidence is how both get stale.

Same labels as the board above. Owner is the product tree; disposition is
whether ZeroPerf still needs it.

**Dependencies:** P4 steps 1-2 landed; P5 before P6; P6 subsumes what remains
of P4. P1, P2 and P5 are independent of each other.

| Item | Kanban | Disposition | Effort | Evidence |
|------|--------|-------------|--------|----------|
| P1 Proof-verification counters | ToDo | Open | S-M | `../PerfTimers.md` S3, `FINDINGS.md` S1.1 |
| P2 NOTEIDX staleness | ToDo | Open | S | `FINDINGS.md` S3.1 |
| P4 Witness RPC gate inconsistent | **InTest** | Open | S-M | this file, P4. Steps 1-2 landed |
| P5 `boost::optional` -> `std::optional` | ToDo | Open | M | this file, P5 |
| P6 Anchor depth for shielded spends | ToDo | Open | L | this file, P6 |
| P7 Coin-selection call clarity | ToDo | Open | S-M | this file, P7 |

## Aside -- postponed, pending review

**Renamed from "will not do".** Nothing here has been refused on the merits;
each was set down because something else was worth more at the time, or because
the evidence then available said the return was small. That is a **judgement
against a snapshot**, and several of the snapshots are already stale -- the
Equihash analysis (`../equ/`) re-examined vectorisation on the mining track after it had
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
| FDCACHE buffer-size sweep | Measured null (`../Perf.md` S3) | A workload that is **not** CPU-bound -- a slower-storage host, random `getblock` serving (A5-a2), or post-Groth-batching |
| SIMD for the Equihash round merge | Not analysed | **TBD, on hold.** Reopens on a decision to invest in arm64 mining |
| Halo / Orchard | Not Zero consensus | A deliberate NU that adopts them. Not a lab decision |
| Post-Sapling bootstrap / sync captures **as a comparison** | A and B agree within ~3 points (`FINDINGS.md` S3.4) | Superseded in part: C4 schedules these as **utilization** cells, which is a different question than re-proving the equivalence |
| Remove dead `nNotarizations` | Not worth a commit of its own | `chain.h` being touched for another reason |
| Native Windows ETW profiling | Blocked on symbol format and an unvalidated MXE build path (`../PerfPlatforms.md`) | A validated Windows build, which is a prerequisite anyway. Reopens if Windows becomes a mining target (`../equ/PLAN.md` S8) |

---

## Vectorisation

Subject owner: `uniblake/docs/NEON.md` for kernel results; `equ/` for solver
ISA work. This section lists items only.

| Item | State | Note |
|---|---|---|
| blake2b vector kernel A/B | **Closed** | Measured in uniblake; slower than scalar there. Not restated here |
| Solver ISA work (AVX2 / Arm SIMD) | **Open** | Owner: `equ/PLAN.md` S2 |
| `INV-ARM-MIX` -- deployment fleet mix | **Open** | Gates whether any ARM vector work is worth scheduling |
| `mine_bench.sh` probe mode | **Kept** | Test mode; not used in production in the current version |

## Tests

Work items for the test and validation system: the harness, self-tests, gates
and lab discipline. Findings and rationale belong to the documents that own
them; this section tracks state.

### T0. Test suite: constants, tiers, failure modes

**Status 2026-09-04.** Three tests fixed and moved to Bpass (10 runs each,
30/30). Tier U created, validated and emptied. Full Bfail/Efail sweep run: 16
of 39 pass. Standards written up in `POLICY.md` S2.2. Remaining: move the 16
after a stability check, and work the 23 failures by mode.



Zero's regtest `COINBASE_MATURITY` is **720**, not Bitcoin's 100. Tests ported
from Zcash assume the short maturity, so a chain that is tall enough upstream
has no spendable coinbase here.

**What already exists** (`qa/rpc-tests/test_framework/util.py`), and it is more
than the discussion suggests:

| Helper | Role |
|--------|------|
| `COINBASE_MATURITY = 720`, `mature_height(n)` | The constant and the target tip |
| `mine_to_height(node, nodes, h)` | Exact tip, for tests asserting NU heights |
| `mine_until_mature(node, nodes)` | Predicate loop; may overshoot |
| `mature_or_skip(node, nodes, label)` | Incremental, then bulk, then print and skip |
| `ensure_coinbase_utxos` / `ZERO_MINE_COINBASE=1` | Opt-in 1000-block bulk mine |
| `initialize_chain` | **Cached chain mined once to `COINBASE_MATURITY + 5` = 725**, reused across runs, rebuilt when stale |

The cache is the substantive fix: 720 blocks are mined once (69 MB on disk) and
copied per test, so maturity costs one build rather than one per test.

**The gap.** 64 tests call `initialize_chain_clean` -- an empty chain, no
mature coinbase -- against 3 that use the cached `initialize_chain`. Every
`clean` test must then mine 720+ blocks itself or skip. That ratio, not the
helper set, is what keeps tests in Tier B fail.

**Tier B fail is 28 tests and mixes four unrelated causes** ("porting /
maturity / comptool / Py3"), so its size overstates the maturity problem.
Sampled by running them [Measured, 2026-09-04]:

| Test | Actual cause |
|------|--------------|
| `mergetoaddress_sapling.py` | **None -- passes.** Ran twice, `Tests successful`, and uses no maturity helper |
| `wallet_listnotes.py` | Maturity: `assert_equal(200, getblockcount())` at lines 21, 31, 65 -- the upstream 100-maturity cache height |
| `wallet_sapling.py` | Assertion failure, same shape |
| `txindex.py` | **Fixed, now passes** -- two defects, neither maturity. See below |
| `reorg_limit.py` | Fails after mining; cause not yet isolated |

So of five sampled: two pass (one after a fix), two are hardcoded heights, one
unknown. Only two of five were maturity-related.

**`txindex.py`, resolved.** It carried two independent defects, and the
serialization one *was* a Python 2 leftover of the semantic kind rather than
the syntactic kind:

1. `unspent[0]["amount"] * 100000000` -- JSON-RPC parses money as `Decimal`,
   and `Decimal * int` stays `Decimal`, which `struct.pack("<q", ...)` rejects.
   Under Python 2 the value was a float and packed by coercion. Fixed with
   `int(... * COIN)`, the idiom the passing `addressindex.py` already uses.
2. `assert_equal(verbose["vout"][0]["valueZat"], 5000000000)` -- Bitcoin's
   50-coin subsidy; Zero's is 10. Fixed by asserting against the amount the
   node reported for that output, so the test tracks txindex behaviour rather
   than the subsidy schedule.

Passes twice in a row.

**Syntactic Python 2 leftovers are gone.** A scan across every
`qa/rpc-tests/*.py` and the framework for `print "`, `has_key(`,
`.iteritems()`, `.itervalues()`, `.iterkeys()`, `xrange(`, and
`except E, e` returns **nothing**. What remains is this semantic class --
`Decimal` where an `int` is required, and division semantics -- which no
syntax check finds.

**The hardcoded-50 pattern persists elsewhere.** `mergetoaddress_helper.py`,
`wallet_mergetoaddress.py` and `wallet_shieldcoinbase.py` each assert
`immature_balance == 50` and `getbalance() == 50`. None of the three is in any
tier list -- the `_sapling` variants run instead -- so they are unexercised
rather than passing. Worth fixing when they are next run, not before.

**List reconciliation** [Measured, 2026-09-04]. 97 test files, and after
correction **three** runnable tests were in no list -- not the ten a first pass
suggested. That pass used a regex that missed hyphenated names, so
`bip65-cltv-p2p.py`, `bipdersig-p2p.py` and `p2p-acceptblock.py` were reported
as hidden while already filed under Bfail and Efail.

Genuinely unfiled, now **Tier U** (`-U`, in `-list-csv`, its own runner):
`wallet_mergetoaddress.py`, `zcjoinsplit.py`, `zcjoinsplitdoublespend.py`.
Tier U is not a verdict -- it means never placed. Run each once and move it to
the tier its result earns.

Correctly excluded, no `__main__` or no `run_test`: `mergetoaddress_helper.py`,
`tx_expiry_helper.py`, `wallet_shieldcoinbase.py` (variant base class),
`wallet_shieldcoinbase_sprout.py`.

The inventory now has no duplicate entries: A 10, B 34, Bfail 28, E 8,
Efail 5, U 3.

**Next steps, cheapest first:**

| # | Step | Why |
|---|------|-----|
| a | Re-run the 28 and re-file by observed cause | The list is stale enough that at least one test in it passes; triage from evidence, not the original label |
| b | Fix hardcoded heights (`wallet_listnotes.py`, `wallet_sapling.py`) | Replace `assert_equal(200, ...)` with `mature_height()`-relative assertions. Contained, and the helpers already exist |
| b2 | Fix hardcoded subsidies where a test is actually run | Assert against the node's reported amount, as `txindex.py` now does and `getrawtransaction_insight.py` already did |

**Converted so far** [2026-09-04]. `COINBASE_SUBSIDY = 10` and
`block_reward(n)` were added to `test_framework/util.py` beside
`COINBASE_MATURITY`, so both constants live in one place:

| File | Change | Result |
|------|--------|--------|
| `txindex.py` | Decimal->int for `struct.pack`; assert the node's own amount | **passes** (Bfail) |
| `wallet_listnotes.py` | literal 200/201/202 -> `base_height` + delta | **passes** (Bfail) |
| `mergetoaddress_helper.py`, `wallet_mergetoaddress.py`, `wallet_shieldcoinbase.py` | `50` -> `block_reward(5)` | unlisted; unverified |
| `bip65-cltv-p2p.py`, `bipdersig-p2p.py` | `generate(100)` -> `generate(COINBASE_MATURITY)` before spending the coinbase | unlisted; unverified |
| `reorg_limit.py` | literals -> `MAX_REORG_LENGTH` and a tip-relative base | **passes** (was Bfail) |
| `wallet_treestate.py` | comment only | still fails, and **not for a maturity reason** -- see below |

**Not every 100 is maturity.** `reorg_limit.py`'s 99 and 100 are a reorg at
exactly the limit and one past it: `MAX_REORG_LENGTH = 99`, rejected when
`reorgLength > 99`. Converting either to 720 would destroy what the test
checks. Both, and the height assertions, now derive from a
`MAX_REORG_LENGTH` in `test_framework/util.py` kept in sync with `src/main.h`.
Each numeric site has to be read for what the number means.

**Correction: `wallet_treestate.py` passes.** An earlier revision of this note
recorded it as blocked by `-regtestprotectcoinbase`. That was wrong: the run it
was based on carried a broken `mine_to_height` edit of mine. Run clean, it
passes, and both the edit and its comment were removed. The mechanism it
described -- `SelectCoins` taking the no-coinbase list that `AvailableCoins`
builds by skipping `IsCoinBase() && !fIncludeCoinBase` (`wallet.cpp:4278`,
`4493`), with "Coinbase funds can only be sent to a zaddr" at `4821` -- is an
accurate description of the code, but is not why this test failed.

**Next steps, cheapest first:**

| # | Step | Why |
|---|------|-----|
| a | Re-run the Bfail/Efail set and re-file by observed cause | Done 2026-09-04; see the sweep below |
| b | Fix hardcoded heights and subsidies | Replace literals with `mature_height()` / `block_reward()`; the helpers exist |
| c | Move passing tests out of Bfail | `mergetoaddress_sapling.py` at minimum; a known-broken list containing passing tests trains people to ignore it |
| d | Consider `initialize_chain` for tests that only need a funded wallet | Converts a 720-block mine per test into a cache copy. Only where the test does not require a clean chain |
| e | Split the Py3/comptool tests into their own tier | They are not maturity work and do not belong in the same queue |
| f | Place unfiled tests in a tier | Done: Tier U created, validated and emptied |

**Full Bfail/Efail sweep** [Measured, 2026-09-04, all 39 scripts run once]:

| Outcome | Count |
|---------|------:|
| **PASS** | **16** |
| FAIL, assertion | 15 |
| FAIL, comptool | 3 |
| FAIL, other | 4 |
| FAIL, "Method not found" | 1 |

**41% of the known-broken set passes.** Passing: `mergetoaddress_sapling`,
`mergetoaddress_mixednotes`, `mergetoaddress_sprout`, `rawtransactions`,
`mempool_tx_expiry`, `fundrawtransaction`, `signrawtransaction_offline`,
`regtest_signrawtransaction`, `key_import_export`, `zkey_import_export`,
`wallet_shieldcoinbase_sapling`, `wallet_protectcoinbase`, `wallet_nullifiers`,
`prioritisetransaction`, `wallet_treestate`, `wallet_overwintertx`.

A list where two in five entries are green is not a triage tool; it is a
backlog nobody has re-read. Moving them is step (c), and the sweep is the
evidence for it. Each was run once here -- a 10x stability check like the one
the three moved tests got should precede the move.

**The 23 failures, by mode.** Grouped by what actually went wrong, which is
not how the tier groups them:

| Mode | n | Tests | Suggested next step |
|------|--:|-------|---------------------|
| Assertion | 15 | `finalsaplingroot`, `mempool_nu_activation`, `merkle_blocks`, `p2p-acceptblock`, `rescan_import`, `shorter_block_times`, `sprout_sapling_migration`, `turnstile`, `wallet_addresses`, `wallet_changeaddresses`, `wallet_listreceived`, `wallet_mergetoaddress`, `wallet_persistence`, `wallet_sapling`, `zcjoinsplitdoublespend` | Read each assertion. The three fixed so far were all literals -- a Bitcoin height, a Bitcoin subsidy, a cache tip. Expect the same class, and check `POLICY.md` S2.2 before editing |
| comptool | 3 | `bip65-cltv-p2p`, `bipdersig-p2p`, `invalidblockrequest` | Not maturity or subsidy. The comptool harness is a separate porting job; give it its own tier so it stops diluting this one |
| Other | 4 | `getblocktemplate_proposals`, `mempool_reorg`, `pruning`, `smartfees` | Unclassified -- each needs one read of its log. `pruning` mines 200 and may be a height case; the rest are unknown |
| Method not found | 1 | `zcjoinsplit` | Sprout raw-joinsplit RPC absent. Retired, not fixable |

**Per-test logs** from the sweep are at `/tmp/sw_<test>.log` for the session
that produced this; re-running `-Bfail` regenerates them. The counts above are
one run each, so a mode may be wrong for a flaky test -- treat the grouping as
a triage starting point, not a verdict.

(a) is the prerequisite: the current grouping cannot be trusted to say what is
maturity-related.

**Kanban: ToDo. Effort M.** Test-harness work, no product change.


### T1. Landed 2026-09-05/06

| # | Item | Where |
|---|---|---|
| T1a | Store resolved via `rbpaths`, not a compiled-in path | `recbench/recbench.py` |
| T1b | `--record` rows carry `bundle` / `bundle_v` / `effective` | `recbench/recbench.py` |
| T1c | Launcher declares the `-disablewallet` it runs with | `tiny_baseline.sh` |
| T1d | `vmmap` footprint parse fixed (`-F:`) -- memory had never been captured | 3 launchers |
| T1e | `repo_root()` by marker file, not `../..` counting | `zeropaths.py` + 4 sites |
| T1f | `kind` / `exec` columns, in the collation key | `recbench/recbench.py` |
| T1g | `set -e` exit-on-success bug | `mine_bench.sh` |
| T1h | libsodium pinned 1.0.22 for the lab | `depends/packages/libsodium.mk` |

Rationale and evidence: `docs/SODIUM_SURVEY.md`, `recbench/RecBench.md`.

### T2. Tooling added

| Tool | Purpose |
|---|---|
| `codequery.sh` | Source queries; reports no-match explicitly (exit 1) |
| `sodium_oracle.sh` | One canonical libsodium oracle; refuses a system fallback |
| `snapshot_data.sh` | `FILE.prev-<utc>` before a run overwrites a collated output |
| `thread_sample.sh` | Per-thread CPU/RSS. Standalone by decision -- no callers |

### T3. Self-tests strengthened

Six assertions added across `recbench`, `perflib` and `zeropaths`, each
mutation-tested: the defect was reintroduced and the suite confirmed red.
Detail in each suite's source.

### T4. Open

| # | Item | Note |
|---|---|---|
| R0 | **Note locking: assess, document and address Zero's exposure.** Upstream `234aaa3a` (2026-07-27) locks a proved transaction's notes so ordinary selection cannot re-hand them; the fix is in crates absent from Zero's 2018 pin. Determine whether Zero's own note selection can hand the same notes to a second transaction while a proved one is broadcastable, document the finding, and fix if present. Owner: Zero400 if it is a node change |
| R1 | Profile the non-blake2b libsodium surface (Ed25519 48 calls, AEAD 8, scalarmult 3) | Nothing there is profiled; `docs/HASHLIBS.md` S1.5A. Answer "is it hot" before designing |
| R2 | Measure `init_salt_personal` share of a one-shot digest | Decides whether `docs/HASHLIBS.md` S1.5D (uniblake parameter-block entry point) is worth building |
| R3 | Evaluate `CBLAKE2bWriter` on uniblake | Expected null (bulk case is 1.01x); the case is uniformity, not speed, on consensus hashing |
| T4g | **`witness_lab.sh` -> `ops-campaign.sh` passes numbers as prose.** The producer writes `wall_s=$elapsed` into `SUMMARY.txt`; the consumer recovers it with a regex. An integer-only pattern silently truncated `141.763` to `141` when millisecond timing landed -- caught by review, not by a test. Both are shell scripts in one tree: the value should be written as a machine-readable field (a `key=value` file sourced by the consumer, or a RecBench row) rather than scraped from a summary written for humans |
| T4e | Use the progress series, not just the endpoint | Every run now yields a height/time series (M-LAB-BAND-TINY). A single blk/s figure hides a 28% spread across height bands; collation reads only the endpoint |

### T5. Landed 2026-09-08: doc-vs-tool drift

Three places where a document stated something the tree no longer supported.
All were found by running the checkers rather than reading the prose, which is
the point: **a restated count is a copy, and copies drift.**

| # | Item | Where |
|---|---|---|
| T5a | FDCACHE "functionally correct" **retracted** -- the A5 P0 lock-lifetime defect stated in place, with both read sites, its reachability and the required fix | `Perf.md` S3 |
| T5b | A5 source line references refreshed against the current tree | `TASKS.md` A5 |
| T5c | Table counts re-measured; the two hardcoded copies in `lint-perf.sh` removed | `TASKS.md` C1n, `STRUCTURE.md`, `lint-perf.sh` |

**T5a, kept in proportion.** `Perf.md` and A5 disagreed about the same parked
flag. Re-verified against source, tightened to two sentences, and **all FDCACHE
exposition consolidated into `../Perf.md` S3**, which owns the subject: this
file had ~40 lines explaining it, against the rule that `TASKS.md` may mention a
subject but not explain one (`MAP.md`). A documentation-consistency fix, not a
bug fix -- the flag is compiled out, defaults off, measured null, and its
single-reader bound is only reachable by the A5-a2 `getblock` case. An earlier
draft of this entry overstated it. A5-d Finished; A5-a stays deferred to B2.

**T5b.** A5 cited `main.cpp:4902-4925` for P0 and `:3232`, `:4950` for P1;
the code has moved to `:4924` and `:3254`, `:4971`. Line numbers in a
document age badly against a tree that is still being edited -- these are kept
because they are load-bearing evidence for a confirmed defect, and were
re-derived rather than trusted.

**T5c.** `check_tables.py` reported 85 undersized tables and 13 files over the
ceiling against documented figures of 84 and 13, with `TASKS.md` itself at 48
tables against a recorded 45. Counts re-measured (472 tables, 40 table-bearing
documents) and the snapshots labelled as snapshots. `lint-perf.sh` restated "84" in two
places, in a set-aside message and a comment; both now name the condition
without the number, since the checker is the authority and the message was
wrong every time a table was added.

Verified after the change: `validate.sh` PASS -- lint clean on owned scope, 17
of 17 self-tests green, `check_tables.py --self-test` OK. Concentration is
unchanged (four scattered subjects), as expected: none of this moved a
subject between documents.
