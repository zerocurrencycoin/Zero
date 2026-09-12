# Tasks

Work items and their state. The only place a task id lives, so two records
cannot disagree. Items are listed, not explained: each names its subject and
links to the document that owns it (`POLICY.md` S2.0a).

Status (`POLICY.md` S1): Kanban ToDo -> InProgress -> InTest -> Finished;
disposition Open | Blocked | Finished | Postponed | Aside. Aside means
postponed pending review, not refused.

## Board

| Item | Kanban | Disposition | Effort | Why |
|------|--------|-------------|--------|-----|
| A3 Microbenchmark baseline | **InTest** | Open | S | 4 of 17 run; M-ZCB-SAP-VERIFY/CREATE; `test-logs/a3-zcbench-20260910/` |
| A4 Workload taxonomy A-E | ToDo | Open | S-M | this file, A4 |
| A5 CodexPerf review triage | Finished | -- | M | `../../CodexPerf.md` |
| B2 First non-macOS measurement | ToDo | **Postponed** | M | needs a Linux host; see Linux/Windows group |
| B2a Suite-run gotchas | ToDo | Open | S | four results that look like defects |
| C1 Documentation consolidation | **InTest** | Open | M | `POLICY.md` S2.0 |
| E2 Script corpus + schema | **InProgress** | Open | M | this file, E2 |
| C2 Remaining measurement gaps | ToDo | Open | M | `FINDINGS.md` S4 |
| C3 Inherited build/DB defects | ToDo | Open | M | `../BUILD_RECONFIG.md` |
| C4 Per-workload utilization profile | ToDo | Open | L | this file, C4 |
| D1 Equihash / blake2 integration | **InProgress** | Open | M | `../equ/README.md` |
| D2 `Xc.reserve()` | **Ready** | Open | XS | verified `equihash.cpp:384`; this file, D2 |
| D3 Fold `len` to compile-time | **InTest** | Open | XS | **applied** `equihash.cpp:557` (`05cdcefe6`); 1.22x (M-EQ-D3-SORT) |
| D5 tromp path + **now the default** | **Finished** | -- | S | 5.69x (M-EQ-TROMP-SPEEDUP); `test-logs/tromp-default-20260909/` |
| F1 Regression gate on validate | **InTest** | Open | S | `validate.sh` |
| F2 CI wiring | -- | **Postponed** | S | needs repo settings |
| R0 Note locking | -- | **Assessed** | -- | closed into P9 |
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

### GROTH -- status review, 2026-09-09

**Remains postponed.** Reviewed, not reopened: the review is of whether the
description and its pending decisions are still accurate, and they are.

**Verified against the dependency, not the document:**

| Claim | Check |
|---|---|
| Pin is `06da3b9a` (2018-10-27) | **Confirmed** -- `depends/packages/librustzcash.mk:7`, and the commit dates 2018-10-27 |
| 6724 commits behind | **Confirmed exactly** -- `git rev-list --count 06da3b9a..HEAD` = 6724 against upstream HEAD 2026-09-03 |
| The C FFI crate no longer exists upstream | **Confirmed** -- `librustzcash/` now holds only a README: "This crate has been moved into https://github.com/zcash/zcash" |

So the load-bearing fact is intact: **there is no newer version of what Zero
consumes.** Option B is not "upgrade a dependency", it is "adopt a different
integration boundary", and that is the whole of the A-vs-B cost difference.

**The decision is genuinely blocked on a person, not on evidence.** Both
options are scoped, the math was proved on the pinned crates (Phases 0-1,
scratchpad only), and the branch point is the FFI boundary -- so starting
either wastes the other. That is a maintainer's call about risk appetite on
consensus-critical code, and no further lab work changes it.

**What is worth doing while postponed, in order:**

| # | Item | Why now |
|---|------|---------|
| 1 | **A3 microbenchmark baseline** | A batching result needs a per-proof baseline taken *beforehand*. Taken afterwards it is not a comparison. This is the only genuinely time-sensitive item on the whole board |
| 2 | **P1 proof-verification counters** | Groth16 verification is inside no timer at all, so a phase summary today omits 88-91% of post-Sapling cost while looking complete. Any before/after needs this first |
| 3 | **Fork for custody** (S, no consensus risk) | Take `06da3b9a` into a Zero-owned mirror unchanged; acceptance test is a byte-identical `librustzcash.a`. Independent of A-vs-B, and it stops the build depending on an upstream path that has already moved once |
| 4 | **Host the downloadable artifacts** | 741 MB of parameters from `download.z.cash` plus the librustzcash tarball. Parameters are hash-verified so a mirror adds no trust. Independent of everything else |

(3) and (4) are packaging, carry no consensus risk, and are the two things that
reduce exposure without pre-empting the decision. (1) and (2) are prerequisites
for measuring any outcome.

**Proposed resolution of the decision itself, with justification.** If forced
to recommend: **Option B (migrate to the upstream batcher) is the better
target, and Option A (hand-port onto pinned crates) is the better first step**
-- but only if the fork-for-custody work (3) lands first, because both options
then build on a boundary Zero controls. The reason B is the target is that it
is production-proven in zcashd and Zebra and also covers signature batching,
so the same migration buys two wins; the reason A is the first step is that
the Phase 0-1 math is already proved on the pinned crates and gives a
correctness oracle that B's output can be checked against. **This is a
recommendation for the maintainer to accept or reject, not a decision.**

**Documentation state:** `../PerfGroth.md` is 938 lines and 23 tables, over
the ten-per-file ceiling. It is the single largest findings document after
`Perf.md` and holds the whole subject correctly (0 FDCACHE mentions after
T5a). No content problem found; the table count is the open item.

---

## A -- do first

### A3. Record the microbenchmark baseline

`M-ZCB-SUITE` has no numeric archive. Runner exists
(`performance-measurements.sh`).

Time-sensitive in one direction: a batching result needs a per-proof baseline
taken beforehand, so this is worth more during the postponement than after.

**Kanban: InTest 2026-09-10.** Four of seventeen benchmarks recorded --
`verifysaplingspend` / `verifysaplingoutput` (n=1000 each) and their `create`
counterparts, bound to **M-ZCB-SAP-VERIFY** and **M-ZCB-SAP-CREATE**. The two
verify rows are the per-proof Groth16 baseline GROTH needs taken beforehand,
so the time-sensitive part is done.

Two defects found by running it: the runner wrote `zcash.conf` where Zero needs
`zero.conf`, so no node started and **the script still exited 0** (fixed,
`performance-measurements.sh:86,116`); and `parameterloading` fails with RPC
error -3 (recorded, not fixed). Detail:
`test-logs/a3-zcbench-20260910/FINDINGS.md`.

Remaining: the other thirteen, several of which need a populated wallet.

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

`CodexPerf.md` (repo root, 2026-08-21) is an independent review of the branch,
verified against source. Two findings were real defects in shipped-by-flag code;
**neither is reachable in a release build** (`bitcoin-config.h` has
`/* #undef ZERO_PERF */` and `/* #undef ZERO_FDCACHE */`).

| # | Finding | Disposition |
|---|---------|-------------|
| **P0** | FDCACHE lock lifetime (`main.cpp:4924`; read sites `:2130`, `:2617`) | **Moved to P8** (postponed) |
| **P1** | `-mrclogevery=0` divides by zero (`main.cpp:3254`, `:4971`) | **Finished** -- `InitPerfLogEvery()` validates once at startup; 3 build configs clean |
| P1 | FDCACHE probe reports false; flags absent from `HelpMessage` | **Moved to P8** |
| P1 | CI builds neither `--enable-perf` nor the perf lint | **F2** (Postponed, needs repo settings) |
| P2 | `--enable-perf` couples counters with behaviour change | **Moved to P8** |
| P2 | Doc drift, evidence set larger than authoritative | **Fixed** -- `POLICY.md` corrected |
| P2 | Portability unproven, one host | **B2** |
| P3 | Out-of-scope wallet docs in `keep/`; `git diff --check` | `keep/` reviewed and mapped; whitespace is a cheap CI addition under F2 |

**The P1 fix caught a bug the default build could not.** The first version of
the `nPerfLogEvery` declaration was nested inside `#ifdef ZERO_FDCACHE`, so a
`ZERO_PERF`-only build failed with `use of undeclared identifier`. That class of
breakage is invisible to current CI and is an argument for the `--enable-perf`
job independent of FDCACHE's disposition.

**Kanban: Finished.** Everything remaining is P8 or F2.

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

Placement rules and the accretion budget: `POLICY.md` S2.0, S2.0a.

| Step | What | State |
|------|------|-------|
| a | Build the docs set, pulling material in incrementally | **Finished** |
| b | `NOTES.md`: stamp dated evaluations with date and version | ToDo |
| c | Route by reader type; one subject per file | ToDo |
| d | Segregate deep internals behind a marked boundary | ToDo |
| e | Strike obsolete history; remove, do not narrate | **In progress** -- SIMD/status swept 2026-09-06 |
| f | Purge mechanism claims not traceable to code or measurement | ToDo |
| g | Fix `SCHEMA.md` statements contradicted by the store | ToDo |
| h | Delete `Perf.md`'s status sections | **Finished** 2026-09-08 -- S0.1-0.13, S0.15, S9/S9.1 deleted; 1560 -> 1061 lines |
| i | `equ/`: figures bound to `M-EQ-*` ids | **Finished** 2026-09-06. The "215 restatements" were mostly derivations; 27 bare, most already cross-referenced |
| n | **Cut tables.** Detail, examples and criteria below | ToDo |

#### C1n. Cut undersized tables

Criteria are `check_tables.py` (>=2 data rows, rows x cols >= 9, <=10 tables
per file); run it for the current counts. Replace a failing table with a
sentence, a clause, a vertical list or a subsection -- a table is the last
resort, not the default. Reported, not gated (`POLICY.md` S2.0 rule 4 says
that should change).

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
| D2 | `Xc.reserve()` sizing | **Ready to run** | S | below |
| D3 | Per-variant solve measurement | ToDo | M | `../equ/METHOD.md` |
| D4 | Keep the `blake2b` bucket ordered before `equihash` | ToDo | S | `../equ/PLAN.md` |

**Verified in source 2026-09-09** (`a2a691fb3`), because three of these were
carried on documentation alone:

| Item | Claim | Source check |
|---|---|---|
| D2 | `Xc` has no `reserve()` | **Confirmed.** `crypto/equihash.cpp:384` declares `std::vector<FullStepRow<FullWidth>> Xc;` with no reserve, while `X` (`:337`) and `Xt` (`:541`) both reserve `init_size` |
| D3 | 1.22x measured, patch applied | **Confirmed both.** `CompareSRFixed<CollisionByteLength>()` at `equihash.cpp:557`, template at `equihash.h:90`, committed in `05cdcefe6`. **Correction:** an earlier revision of this row said the patch was "measured then reverted". That was wrong -- it read the `hashLen`/`lenIndices` declarations at `:537-538`, which serve the *other* sort sites, and missed the converted call at `:557` |
| D5 | tromp 5.69x | **Confirmed both.** Vendored solver at `src/pow/tromp/`, selected by `equihashsolver=tromp` (`miner.cpp:540`, `:663`); figure is M-EQ-TROMP-SPEEDUP |

**D2 -- ready, and here is the whole change.** `Xc` accumulates collision rows
while `X` is still live, so it reallocates repeatedly with both full-size
buffers resident; `M-EQ-PEAK-DEFAULT` is 7.15 GB peak / 6.6 GB footprint and
`equ/FINDINGS.md` S1.1b attributes roughly half of it to this. One line,
before the fill loop:

```cpp
std::vector<FullStepRow<FullWidth>> Xc;
Xc.reserve(/* expected collisions this round */);   // D2
```

- **Reward:** the memory half of the (192,7) problem. Peak footprint is what
  gates independent-solve parallelism (`equ/PLAN.md` S6.0), so this is worth
  more than its cost suggests.
- **Risk: low, and bounded by the gates.** It cannot change solutions -- only
  the allocation schedule. V1 is "solutions unchanged"; the V2 oracle
  (`test-logs/eqvectors/solver_baseline_192_7.txt`, 5 distinct solutions,
  archived and `0444`) is the check.
- **Dependencies: none outstanding.** The fixed-nonce paired harness exists
  (`SOLVE_TIMING_1927`), the baseline is archived (C4e Finished), and D3 proved
  the paired method resolves a ~20% effect. A binary is present (`src/zerod`,
  `src/test/test_bitcoin`, built 2026-09-05) but must be **rebuilt** after the
  edit.
- **Sizing is the only judgement.** Reserving too much wastes what the change
  is trying to save. `equ/PLAN.md` proposes per-round counters (C4 automation
  item 4) to size it from data rather than guessing -- worth doing first if the
  first guess measures badly.

**D3 -- what moves it to Finished.** Patch applied, measured, committed, and
the rationale is terse in-code (`equihash.h:85-88` says which sites are
constant and which are not). What is outstanding is only **V2 revalidation on
the committed form** -- the 1.22x was taken on a working-tree patch, and no
recorded run confirms the committed code still produces the 5 baseline
solutions. That run is D3's exit condition, not a re-implementation.

**Only site 557 was converted, and that is correct.** `hashLen` shrinks by
`CollisionByteLength` each round, so the final-round and partial-merge sorts
(`:436`, `:622`, `:692`) pass a genuinely runtime length; folding those needs
per-round instantiation, which is the per-round-width work in `equ/PLAN.md`
S1.2, not this item. `:378` is the same sort in `BasicSolve`, which mining does
not use.

**D5 -- Finished 2026-09-09.** tromp is now the default (`miner.cpp:544`),
with a parameter guard falling back to the reference solver off (192,7)
(`:552`) -- required, because the vendored solver is compiled for fixed WN/WK
and the default change made regtest reach it for the first time. Help text and
metrics reporting aligned; conf templates already said `tromp`. New test
`miner_tests/equihashsolver_default_and_param_guard` pins both halves and was
mutation-tested. Full record: `test-logs/tromp-default-20260909/FINDINGS.md`.
Needs a release note.

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

**Disposition, 2026-09-09.** Eight open steps is a backlog, not a plan. Sorted
by whether anything actually depends on them:

| Step | Disposition | Why |
|------|-------------|-----|
| **i** consolidate datadir protection | **Do it.** Effort S | Three implementations of the guard that stops a lab destroying a production datadir (`perflib.sh:147`, `prep_lab_datadir.sh:37`, `datadir_guard.sh:33`). POLICY S3.1 records this class of bug already destroying a datadir once. This is the only safety item on the list |
| **j** promote the timeout-guarded `cli()` | **Do it with (i).** Effort XS | `res_sample.sh:34` wraps in `timeout`, `witness_lab.sh:78` does not, and the unguarded one is exactly the documented `getwalletinfo`/`cs_wallet` blocking hazard. Promoting the safer version turns a caveat into a default |
| **n/o/p** `checkpoint_row` -> `progress.tsv` -> ledger | **Defer to C4.** | These exist to make long runs restartable and only pay off when a long run is actually scheduled. C4 is the campaign that needs them; building them earlier means guessing the column set |
| **k** `utc_iso()` beside `utc_stamp()` | **Close as won't-do.** | Three UTC formats across 16 sites, all three legitimate (filenames, row fields, logs). Unifying them changes filenames for no benefit |
| **m** source `perflib.sh` in 3 more scripts | **Fold into (i).** | Two of the three are the datadir-guard scripts (i) already rewrites |
| **q** state restartability in POLICY S4 | **Do it.** Effort XS | One paragraph; the ~20 min heuristic is misleading without it (a 17-minute restartable trial and an unrestartable multi-hour rescan are not the same risk) |

Net: (i)+(j)+(m) as one change, (q) as a paragraph, (n/o/p) deferred to C4,
(k) closed. That is one task instead of eight.

### E2. Script corpus and schema -- one item

**Consolidates E1, T4e, T4g, A2 and A4**, which tracked one body of work under
five ids. Subitems keep their letters so existing references resolve.

| Subitem | From | State |
|---------|------|-------|
| Shared library, datadir policy, value guards, launcher migration (a-h) | E1 | **Finished** |
| Consolidate datadir protection on one implementation (i) + `cli()` timeout (j) + source perflib in 3 scripts (m) | E1 | **In process** -- one change, the only safety item |
| Restartability paragraph in POLICY S4 (q) | E1 | **In process** -- with (i) |
| `checkpoint_row` -> `progress.tsv` -> ledger (n/o/p), and use the series not the endpoint | E1, T4e | **Postponed to C4** -- needs a scheduled long run to size the columns |
| `utc_iso()` unification (k) | E1 | **Closed, won't do** -- three formats, all legitimate |
| Machine-readable handoff between `witness_lab.sh` and `ops-campaign.sh` | T4g | **Undecided** -- `key=value` file or a RecBench row; both work, pick one |
| `op` enum + validation + back-annotation (A4a/b/f, A2c) | A4, A2 | **In process** -- load-bearing; blocks C4 |
| `wallet_shape`, `era` derivation, pooling guard (A4c/d/e) | A4 | **Postponed** -- needs the enum first |
| Fingerprint v2, cross-platform pooling guard (A2e/f) | A2 | **Postponed** -- blocked on B2, no Linux row exists to test against |

**Why one item:** all of it is the harness that records measurements, and the
five ids meant a reader had to assemble the state from five places. The
duplicate pair (A2c and A4f were the same job) is now stated once.

### T4/T4g/T4e -- disposition

| Item | Disposition | Why |
|------|-------------|-----|
| **T4g** numbers passed as prose | **Do it.** Effort S | `witness_lab.sh` writes `wall_s=$elapsed` into `SUMMARY.txt`; `ops-campaign.sh` recovers it by regex, and an integer-only pattern silently truncated `141.763` to `141`. Caught by review, not by a test -- so the same class of bug is undetectable elsewhere in the chain. Fix: write a `key=value` file the consumer sources, or a RecBench row |
| **T4e** endpoint vs progress series | **Fold into C4 (n/o/p).** | Same subject: the series exists in `debug.log`, collation reads only the endpoint, and a single blk/s figure hides a 28% spread across height bands (M-LAB-BAND-TINY). It is the reason (n/o/p) is worth doing, so track it there rather than twice |

### A2/A4 -- schema items, and what actually blocks what

| Item | Disposition | Why |
|------|-------------|-----|
| **A4a/b** `op` enum + validation | **Do first of the schema items.** Effort S | `--op` is unvalidated free text, so the pooling guard has no key and every existing row reads `reindex`. An enum nothing checks is a comment. (a) and (b) are load-bearing; (c)-(f) are not |
| **A4f** back-annotate 49 rows | **Do with (a)/(b).** Effort XS | Only `op` and `era` are derivable; both are. The point is that old rows can be *correctly excluded*, not that they be complete |
| **A4c/d/e** wallet_shape, era derivation, pooling guard | **After (a)/(b).** | (e) is what converts the taxonomy into a guard, but it needs the enum to key on |
| **A2c** `features` back-annotation | **Same work as A4f.** Close the duplicate id | Two ids for one job is the double-record problem the board exists to prevent |
| **A2e/f** fingerprint v2, pooling guard | **Blocked on B2, not on effort.** | A2f refuses to pool a Linux row with a macOS one. There are no Linux rows, so it cannot be tested. Do it when B2 produces one |

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
| **`Perf.md` retirement** | **Not ready** | Holds detail for B1, B3 and GROTH. Re-run the caveat diff before retiring |

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
| P1 Proof-verification counters | **InTest** | Open | S-M | prototype builds both configs; `test-logs/p1-proto-20260910/` |
| P2 NOTEIDX staleness | ToDo | Open | S | `FINDINGS.md` S3.1 |
| P4 Witness RPC gate inconsistent | **InTest** | Open | S-M | this file, P4. Steps 1-2 landed |
| P5 `boost::optional` -> `std::optional` | ToDo | Open | M | this file, P5 |
| P6 Anchor depth for shielded spends | ToDo | Open | L | this file, P6 |
| P7 Coin-selection call clarity | ToDo | Open | S-M | this file, P7 |
| P8 FDCACHE disposition | -- | **Postponed** | S-M | `../Perf.md` S3 |
| P9 Note locking / single-worker | ToDo | Open | S | this file, P9 -- **needs a decision** |
| P10 Explicit parameters at defaulted calls | ToDo | Open | S | this file, P10 |
| P11 tromp driver duplicated | ToDo | Open | S | this file, P11 |

### P11. The tromp solver driver is written twice

`miner.cpp:668-700` and `src/test/equihash_tests.cpp:414-450` each contain the
same call sequence -- `setstate`, `digit0`, the `digitodd`/`digiteven` round
loop, `digitK`, then the solution walk. **Copied, not shared**, and the copies
have already drifted: the test zeroes `xfull`/`bfull`/`hfull` *before*
`digit0`, the miner does not; the miner calls `showbsizes()` per round, the
test does not.

The test comment says the driver is "lifted verbatim from `miner.cpp` so this
measures the code path a miner actually runs". That is the intent, and
duplication is exactly what breaks it -- a change to the miner's sequence
silently stops the benchmark measuring the miner.

**Proposed resolution:** extract one `EhSolveTromp(state, nsols_out, ...)`
helper, called by both. `miner.cpp` keeps its cancellation and
`showbsizes` handling around it; the test keeps its `PERF_PROBE`
instrumentation around it. **Effort S.**

**Why it is not urgent:** both copies currently produce identical solution
sets on the same nonces (M-EQ-TROMP-PAIRED), so the drift has not yet changed
behaviour. It is a maintenance hazard, not a live defect.

**Memory and concurrency, checked while reading this:**

- Allocation is **per-instance**: `htalloc::alloc` uses `calloc`, freed by
  `~equi() -> dealloctrees()` (`equi_miner.h:281,323`). Two `equi` objects
  share nothing, so concurrent *independent* solves need no lock -- they need
  memory (~3.3 GB each, M-EQ-PEAK-TROMP).
- Slot and solution counters are `au32`, which is `std::atomic<u32>` **only
  under `EQUIHASH_TROMP_THREADED`** (`equi_miner.h:39-44`). `miner.cpp`
  constructs `equi eq(1)`, so that is off and the plain `u32` path is used.
- **`xfull` / `bfull` / `hfull` are plain `u32` regardless** (`:302-304`) and
  are incremented in the hot path (`:566`). They are diagnostics, not
  correctness state, but they would race if the threaded path were ever
  enabled. The header already documents that threads, atomics and the barrier
  "are one feature and must move together"; these three counters are **not**
  covered by that statement and should be, if `nthreads > 1` is ever passed.

### P8. FDCACHE: lock lifetime, flag split, probe

**Postponed.** Everything about the `-perffdcache` / `-perfbufsize` experiment
that is node code, collected here so it is one item rather than five scattered
across A5. The subject itself -- mechanism, measured result, concurrency bound
-- is `../Perf.md` S3.

**Why postponed rather than open:** the flag is compiled out of release builds,
defaults off even under `--enable-perf`, and measured no throughput win at
either era (M-CPU-FD-THR). Nothing depends on it. It is retained because the
null is one platform (macOS/arm64, warm page cache) and macOS stdio does not
predict Linux or Windows -- so the disposition is a **B2 output**, not a
decision to take now.

| Step | What | Reachable today? |
|------|------|------------------|
| a | Lock lifetime: `CacheOpen` drops `LOCK(latch.cs)` at return, caller reads the shared `FILE*` unlocked. Fix with an RAII lease across seek+read, or positional `pread` | No -- needs `--enable-perf` **and** `-perffdcache=1` |
| b | Split `--enable-perf` into counters (safe) and experimental behaviour (FDCACHE), so the counters can be built without the experiment | No -- build-time only |
| c | Re-verify the FDCACHE probe and the `HelpMessage` gap; the probe reportedly always returns false, which mislabels provenance | No -- affects lab labelling, not the node |

**Order if it resumes:** (a) before any multi-reader measurement, because
concurrent readers are exactly the unsafe condition. (b) is independent and is
the one worth doing even if FDCACHE is dropped -- it decouples safe counters
from the experiment. (c) is lab hygiene.

**What would reopen it:** a B2 result on Linux or Windows showing a non-null
effect, or a workload that is not CPU-bound -- random `getblock` serving, cold
cache, slow storage (`../Perf.md` S3 names both and how to measure them).

**What would close it:** a B2 null on both platforms. Then delete the flag, the
latch and `bench_matrix.sh`'s FDCACHE conditions rather than carrying a
compiled-out path indefinitely.

### P9. Shielded-note locking and the single-worker policy

**Assessed 2026-09-09** against `src/` at `a2a691fb3` and the sibling forks in
`ZKs/`. The original R0 premise cited upstream `234aaa3a`; **that hash does not
resolve in the upstream repo**, so the claim "the fix is in crates absent from
Zero's pin" is **unverified and probably wrong** -- what was found instead is
below, and it is a C++ wallet matter, not a Rust crate one.

**What exists.** Zero has shielded-note locking: `setLockedSaplingNotes`
(`wallet.h:1110`), `IsLockedNote` for `JSOutPoint` and `SaplingOutPoint`
(`:1135`, `:1146`). Selection honours it -- `GetFilteredNotes` skips locked
notes at `wallet.cpp:6034` / `:6107`, with `ignoreLocked` defaulting true.

| Operation | Locks its inputs? |
|-----------|-------------------|
| `z_mergetoaddress` | **Yes** -- `lock_notes()` / `unlock_notes()` (`asyncrpcoperation_mergetoaddress.cpp:116`, `:130`, `:185`) |
| `z_sendmany` | **No** -- zero `LockNote` calls |
| `z_shieldcoinbase` | **No** |

**The single-worker policy: found, with the reason in the commit.** Searched
Zcash history rather than inferring:

| Commit | Date | What |
|---|---|---|
| `8d08172d0` | 2016-08-19 | Adds `-rpcasyncthreads`, default 1. Shipped in release-notes-1.0.0-beta1 |
| `008fccfa4` | **2016-09-01** | **Disables it, 13 days later, same author** |
| `4e6400bc0` | 2018-03-15 | **Note locking for `z_mergetoaddress`** (PR #3106, issue #3046, "mergetoaddress-concurrent"). This is the `lock_notes()`/`unlock_notes()` Zero has |
| `0e0f5e4ea` | 2018-09-12 | **Sapling note locking in `CWallet`** (PR #3496, closes issue #3442). This is `setLockedSaplingNotes` / `IsLockedNote` -- **Zero has this too**, commit `b6b2b5d26` |
| `06553d139` | 2022-10-24 | **Note locking for the send path**, in `wallet_tx_builder` (PR #6408), fixing issues **#2621** and **#5654**. Orchard deliberately excluded, tracked separately |
| `69ab52cb3` | 2023-03-30 | Doxygen for note locking |
| `2d456afeb` | 2023-03-31 | Merge of #6408 |

The disabling commit states the reason in the code it left behind:

> `// Disabled until we can lock notes and also tune performance of libsnark`
> `// which by default uses multiple threads`

**So note locking was always the named precondition for multiple workers** --
this is not an inference. Upstream met it in 2022 and the worker loop is live
again in current zcashd (`rpc/server.cpp:349`), while the help text stays
commented out.

**Zero has the first two and not the third.** It carries `4e6400bc0`
(mergetoaddress locking) and `0e0f5e4ea` (Sapling note locking in `CWallet`,
as `b6b2b5d26`), which is why the mechanism exists and `mergetoaddress` uses
it. It stops before `06553d139`, which is the one that put locking on the
**send** path -- and that landed in `wallet_tx_builder`, a file Zero does not
have and which upstream introduced as part of a wholesale restructure of
transaction construction.

So the gap is real, its shape is known, and closing it upstream's way means
adopting `wallet_tx_builder`. That is the honest scope: **not a 20-line patch**
as an earlier revision of this item estimated. The original R0 note was
directionally right about the exposure and wrong about the location -- it is
C++ wallet code, not a Rust crate version.

**Issue trail, for anyone re-opening this:** upstream #3046 (concurrent
mergetoaddress) -> #3442 (Sapling note locking) -> **#2621 / #5654** (the send
path, fixed 2022). Zero closed the first two.

**Provenance: this is inherited, not a Zero defect.** Checked across
`ZKs/{zcash,ycash,hush3,zclassic,pirate}`:

- The `mergetoaddress`-locks / `sendmany`-does-not asymmetry comes from the
  2018-era Zcash base Zero forked from.
- **Modern upstream deleted the convenience overload entirely.** Current
  zcashd has one `GetFilteredNotes` with every parameter explicit, including a
  `NoteFilter` and `asOfHeight` (`zcash/src/wallet/wallet.h:2203`). It also
  restructured the async operations, so neither `LockNote` in `sendmany` nor
  `lock_notes` in `mergetoaddress` survives in that form.
- **The single-worker policy is upstream and deliberate.** The comment
  "Launch one async rpc worker. The ability to launch multiple workers is not
  recommended at present and thus the option is disabled" is **byte-identical
  in all five forks**, predates Zcash's 2016 `rpc/` move (`4519a766b`), and is
  still in zcashd as of 2023. It is a ten-year-stable decision, not an
  oversight.

**So the disposition changes.** The safety property is upstream policy that
five independent projects have kept. Zero is not exposed today, and matching
upstream means **keeping one worker**, not adding locks to work around removing
it.

| # | Action | Recommendation |
|---|--------|----------------|
| 1 | Comment at `rpc/server.cpp:311` recording *why* single-worker matters -- that `z_sendmany` selection is unreserved and serialisation is what makes it safe | **Do.** Zero risk, and it is the missing half of an existing upstream comment that says "not recommended" without saying what breaks |
| 2 | Add `lock_notes()`/`unlock_notes()` to `sendmany`, mirroring `mergetoaddress` | **Ask first.** It is ~20 lines against an in-tree pattern and removes the dependency on worker count -- but it diverges from a 2018 base that upstream has since restructured wholesale, and it touches wallet spend selection. See the question below |
| 3 | Same for `z_shieldcoinbase` | With (2) or not at all |

**Open question for the maintainer.** Do we harden `sendmany` (2), or record
the coupling and leave it (1 only)?

- **Pro hardening:** defence in depth; the property stops depending on a
  comment; the pattern already exists two files away.
- **Con:** it is local divergence on wallet spend selection in a tree that
  pins a 2018 base; upstream's own answer was to restructure the whole async
  path, which Zero is not doing; and the failure it prevents is unreachable
  unless someone re-enables a disabled option.
- **Recommendation: (1) now, (2) only if `-rpcasyncthreads` is ever
  reconsidered.** The comment is what makes the coupling discoverable, and it
  is the change that cannot be wrong.

**Kanban: ToDo (item 1). Disposition: Open.** Owner Zero400.

### P10. Explicit parameters at defaulted call sites

**Rule.** A call that relies on defaulted parameters must be justified in a
terse comment naming the values taken and why, **or** pass them explicitly.
When in doubt, pass them explicitly.

**The case that prompted it.** `asyncrpcoperation_sendmany.cpp:955` calls the
6-argument `GetFilteredNotes(sproutEntries, saplingEntries, fromaddress_,
mindepth_)` -- and that overload has **no `ignoreLocked` parameter at all**. It
forwards to the 9-argument form (`wallet.cpp:5982`), which defaults
`ignoreLocked=true`. Reading the call site, nothing says whether locked notes
are skipped; it takes two hops and a header to find out.

**Scope of the change, measured before proposing it:**

| Site | What is hidden |
|------|----------------|
| `asyncrpcoperation_sendmany.cpp:955` | `maxDepth=INT_MAX`, `ignoreSpent=true`, `requireSpendingKey=true`, `ignoreLocked=true` |
| Other `GetFilteredNotes` callers | To be enumerated as part of the item |

**Provenance, and why that matters here.** The wrapper is **upstream Zcash**
(`39e58e79b`, 2018-10-09, "Add functionality from GetUnspentFilteredNotes to
GetFilteredNotes") and is present identically in ycash, hush3, zclassic and
pirate. Zero did not write it. Modern upstream **removed** it in favour of one
fully-explicit signature -- so making Zero's call sites explicit moves *toward*
upstream's own conclusion rather than away from it, which is the opposite of
the usual divergence risk.

**Proposed resolution:** add the explicit arguments at the call sites (no
signature change, no behaviour change, trivially reviewable), and a one-line
comment where a default is genuinely load-bearing. Do **not** delete the
overload -- that is upstream's restructure, not ours.

**Applies beyond this function.** The rule is general: prefer explicit
arguments at any call where a defaulted parameter changes what the code does,
and where the default is not obvious from the call site.

**Kanban: ToDo. Effort S.** Owner Zero400 (`src/wallet/`).

### Linux and Windows -- one postponed group, pending a current-version build

Scattered across B2, C3, the release track and the Aside list. Grouped here
because **every one of them has the same prerequisite**: a validated build on
that platform at the current version. Scheduling any single item still pays
that cost, so they are one unit of work, and listing them separately overstates
how much is ready to start. This is WIP pending a remeasure, not a backlog.

| Item | Platform | State |
|------|----------|-------|
| **B2** first non-macOS capture (steps a, b, d) | Linux | Step (c) Finished -- the folded-stack parser works and is self-tested. (d) needs a host to validate `psutil` against |
| FDCACHE validation (**P8**) | Linux + Windows | The null is macOS-only; macOS stdio predicts neither |
| Cold-cache measurement | Linux only | Needs `/proc/sys/vm/drop_caches` |
| `--strict` / `--suite` release track | Linux | Last run predates this branch's build and test changes; needs a retest, not a first run |
| MXE cross-build | Windows | **Never executed in this program.** No baseline exists -- this is a first run, not a retest |
| Windows hardening; native ETW profiling | Windows | Blocked on the MXE build above |
| Params archival, branch-id CI, OpenSSL 3, Debian packaging | Both | Release engineering behind the same gate |

**Two different things in one group.** Linux items are a **remeasure** -- the
capability exists and the numbers are stale. Windows items are a **first
build** -- MXE has never been executed here, so "unproven" understates it.
Keeping them together is right because both wait on the same host work, but
they should not be estimated as if they were the same risk.

**What unblocks it:** one Linux host with a clean checkout. That single run
also moves A2e/f, F1, C1 and D3/D5 out of InTest, which is why B2 is the
highest-value item on the board and why this group is postponed rather than
abandoned.

**Postponed, not refused.** Reopens the moment a non-macOS host is available.

---

## Vectorisation

Items and state only. Solver ISA work is owned by `../equ/`; blake2b kernel
results are **not this tree's** and are cited from `docs/HASHLIBS.md`, which
owns the library division.

| Item | State | Note |
|---|---|---|
| blake2b vector kernel A/B | **Closed** | Negative result adopted from the kernel library; figures and their provenance are `docs/HASHLIBS.md`. Not restated here |
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
| R0 | **Note locking -- assessed 2026-09-09; see P9.** The premise was wrong in one direction and right in another: Zero **does** have shielded-note locking, and the async RPC queue runs **one worker**, so the double-hand scenario is not reachable today. `z_sendmany` never locks the notes it selects, so the protection depends entirely on that single-worker serialisation. Moved to **P9** |
| R1 | Profile the non-blake2b libsodium surface (Ed25519 48 calls, AEAD 8, scalarmult 3) | Nothing there is profiled; `docs/HASHLIBS.md` S1.5A. Answer "is it hot" before designing. **Plan below** |
| R2 | Measure `init_salt_personal` share of a one-shot digest | Decides whether `docs/HASHLIBS.md` S1.5D is worth building. **Plan below** |
| R3 | Evaluate `CBLAKE2bWriter` on uniblake | Expected null (bulk case is 1.01x); the case is uniformity, not speed. **Plan below** |

#### R1-R3: where each runs, and why

Not one topic: **R1 is a node profiling question; R2 and R3 are kernel
questions** and belong in the sibling library's tree with its own bench harness
and measurement format (`docs/HASHLIBS.md` owns the division).

| | Question | Tree | Records to |
|---|---|---|---|
| **R1** | Is any non-blake2b libsodium call hot during sync? | ZeroPerf | `M-*` in `Measures.md` |
| **R2** | What share of a one-shot digest is parameter-block setup? | Kernel library | its `measurements.tsv` |
| **R3** | Does the streaming entry point behave like the bulk one? | Kernel library, then a node A/B only if non-null | tsv, then `M-*` if it reaches the node |

**R1 needs no new run.** The six-capture sequence behind M-CPU-SEQ already
contains these frames; `classify()` in `bucket_profile2.py` folds them into a
general bucket. Add `crypto_sign_*`, `crypto_aead_*`, `crypto_scalarmult*` as
their own buckets, re-bucket the archived captures, done. Cheapest of the
three, so first.

**R2 and R3 are library properties, independent of Zero.** The harness and a
provenance-carrying format already exist there; re-implementing either here
would duplicate both and produce figures that cannot sit beside the 2.03x
Equihash-pattern result they need to be compared with.

**R3's node half is gated on its kernel half.** `CBLAKE2bWriter` is the only
high-volume consensus site (`docs/HASHLIBS.md` S1.5C). A null on the streaming
pattern -- expected, bulk is 1.01x -- closes R3 as a negative result with
nothing to port. Only a non-null justifies a node A/B, and that is consensus
hashing, so it needs the bit-identical gate the Equihash swap used.

**Order:** R1, then R2 (decides whether S1.5D is worth building), then R3
(close it either way).

**Prerequisite for all three:** none. They do not depend on B2, GROTH, or the
documentation work.
| T4g | **`witness_lab.sh` -> `ops-campaign.sh` passes numbers as prose.** The producer writes `wall_s=$elapsed` into `SUMMARY.txt`; the consumer recovers it with a regex. An integer-only pattern silently truncated `141.763` to `141` when millisecond timing landed -- caught by review, not by a test. Both are shell scripts in one tree: the value should be written as a machine-readable field (a `key=value` file sourced by the consumer, or a RecBench row) rather than scraped from a summary written for humans |
| T4e | Use the progress series, not just the endpoint | Every run now yields a height/time series (M-LAB-BAND-TINY). A single blk/s figure hides a 28% spread across height bands; collation reads only the endpoint |

### T5. Landed 2026-09-08

| # | Item | Where |
|---|---|---|
| T5a | FDCACHE consolidated into `Perf.md` S3; "functionally correct" retracted; 12 restatements deleted | `Perf.md`, `PerfGroth.md` (now 0 mentions) |
| T5b | A5 source line references re-derived against the tree | `TASKS.md` A5 |
| T5c | Table counts re-measured; hardcoded copies removed | `TASKS.md`, `lint-perf.sh` |
| T5d | Meta-docs deleted: `MAP.md` (folded into `POLICY.md` S2.0a), `STRUCTURE.md`, `MIGRATION.md`, `OVERVIEW.md`, `docs/README.md` | `docs/` 15 -> 10 files |
| T5e | `Perf.md` status sections deleted (S0.1-0.13, S0.15, S9/S9.1) | 1560 -> 1061 lines |
| T5f | Out-of-scope Qt wallet docs deleted | `keep/desys.md`, `keep/ZeroWallet_Design.md` |

Accretion budget and the subtractive rules that came out of this:
`POLICY.md` S2.0.