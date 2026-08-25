# Tasks

What is open, in what order. **10 items**, each one deliverable with sub-steps.

**This file carries no evidence.** Every "why" lives in `FINDINGS.md` (what was
measured), `../PerfGroth.md` (Groth16), or a spec, and is cited here rather
than restated. If a row needs a paragraph of justification, the justification
belongs in the other file.

Status (`POLICY.md` S1):

- **Kanban:** ToDo -> InProgress -> InTest -> Finished. The project owner
  defines what these mean.
- **Disposition:** Open | Blocked | Finished | Postponed | Aside

Sequencing is **A before B before C** within a group; groups are independent
unless a dependency is named. **D** runs in parallel throughout.

---

## Board

| Item | Kanban | Disposition | Effort | Why |
|------|--------|-------------|--------|-----|
| A1 Enforce existing rules | **InTest** | Open | S | `FINDINGS.md` S1.3 |
| A2 Record binary and platform | **InTest** | Open | M | `FINDINGS.md` S1.2, `SCHEMA.md` |
| A3 Microbenchmark baseline | ToDo | Open | S | `FINDINGS.md` S4 |
| B1 Phase timers | **InProgress** | Open | S-M | `FINDINGS.md` S1.1, `../PerfTimers.md` |
| B2 First non-macOS measurement | ToDo | Open | M | `../PerfPlatforms.md` |
| B3 NOTEIDX staleness | ToDo | Open | S | `FINDINGS.md` S3.1 |
| C1 Documentation consolidation | **InTest** | Open | M | `MIGRATION.md` |
| C2 Remaining measurement gaps | ToDo | Open | M | `FINDINGS.md` S4 |
| C3 Inherited build/DB defects | ToDo | Open | M | `../BUILD_RECONFIG.md` |
| D1 Equihash / blake2 integration | **InProgress** | Open | M | `../equ/README.md` |
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
| 3 | **B1c/d** proof counters + `BenchSummary` | Product change, Zero400 review. B1a/b (parser side) are Finished |

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
| c | Back-annotate existing rows | Finished |
| d | Stamp at write time (**F1b**, not per launcher) | **Finished** -- `append_row` and `cmd_add` stamp; an unstamped row is now unrepresentable |
| e | Fingerprint v2 with `fingerprint_v` | Open |
| f | Group-by / filter; refuse cross-platform pooling by default | Open |
| g | Add `run_id` to CPU rows | Open |

a-c must precede any non-macOS run and are Finished.

**Kanban: InTest. Effort M.**

### A3. Record the microbenchmark baseline

`M-ZCB-SUITE` has no numeric archive. Runner exists
(`performance-measurements.sh`).

Time-sensitive in one direction: a batching result needs a per-proof baseline
taken beforehand, so this is worth more during the postponement than after.

**Kanban: ToDo. Effort S.**

---

## B -- after A

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
| 0b | `Xc.reserve()` -- one line, and the most informative single measurement | ToDo, V1 |
| a | Add new build-time options to `feature_bundles.json`; classify each | ToDo |
| b | Ensure `features.workload.op` distinguishes solve / verify / sync | ToDo |
| c | Record the baseline on the target host before any change | ToDo |
| d | Confirm `platform.arch` is carried -- SIMD results are arch-specific | ToDo |
| e | Keep the `blake2b` bucket ordered before `equihash` | ToDo |

Harness: `mine_bench.sh`, `performance-measurements.sh`, KATs in
`src/test/data/`. Analysis and plan: **`../equ/`**.

**Kanban: ToDo. Effort M**, dominated by (c).

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

### F1 rationale (as proposed)

Compilation is standalone and slow; a lint/self-test gate should not wait on
it. Proposal:

| Stage | Runs | Gate |
|-------|------|------|
| **build** | `zcutil/build.sh` | standalone; no regression gate attached |
| **validate** | `lint-perf.sh` + tool self-tests + `contrib/run-tests.sh` | **the regression gate** |
| **release** | `zcutil/check-release.sh` | validate must have passed |

`validate` is the natural attachment point: it already exists as a target
(`contrib/run-tests.sh --strict`), it needs no compiler, and it is what a
release is supposed to depend on. Attaching to `build` would couple a
30-second check to a 4-hour compile; attaching to `release` alone would let
regressions accumulate until the end.

**Kanban: ToDo. Effort S.** Local `validate` first, since it works without any
repository settings.

### F1b. A2d resolution: where the stamp is emitted (proposal)

A2d ("call `platform_stamp.py` from every launcher") is what keeps A2 in
InTest. Three options were considered.

| Option | How | Cost | Failure mode |
|--------|-----|------|--------------|
| **A. Per-launcher call** | Each of the 10 launchers calls the helper and merges the block into its row | 10 edits; drifts as launchers are added | A launcher that forgets it writes an unstamped row, and nothing notices |
| **B. Stamp at write time (recommended)** | `accumulate_bench.py` / `profile_collate.py` call `platform_stamp` when appending a row | 2 edits, both in code already under self-test | None: a row cannot be written without a stamp |
| **C. Post-hoc backfill** | Stamp rows after the fact from run metadata | 1 edit | The values are inferred, not observed -- exactly the provenance problem being fixed |

**Recommend B.** The justification is that it makes the invariant structural
rather than procedural: every row reaches the ledger through one of two writer
functions, so stamping *there* means an unstamped row is unrepresentable. A is
ten chances to forget; C records a guess.

Two caveats B must handle, and they are why this is a change rather than a
one-liner:

- **The writer runs after the node exits**, so `build.*` must be captured from
  the binary that actually ran, not from whatever `src/zerod` is at write time.
  Pass the binary path into the writer; fall back to unknown rather than
  guessing.
- **`features.workload` is known only to the launcher** (op, wallet, snap,
  height range). The writer cannot infer it. Launchers pass it as arguments --
  a much smaller change than emitting the whole block, and the fields already
  exist as parameters in most of them.

Exit condition for A2: one measurement recorded end to end through the writer,
with a populated `platform`, `build` and `features` block, and the aggregation
guard (A2f) refusing to pool it with an existing macOS row from a different
binary.

**Kanban: ToDo. Effort S-M.**

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

**All 9 migrated.** The only `rm -rf` calls left on a datadir path are
`dispose_datadir`'s own implementation, a temp-dir trap in the self-test, and
two `$SCRATCH/chainstate` subdirectory wipes, which are not datadir resets.
All local `log()` copies are gone.

**Kanban: InProgress. Effort M**, dominated by (e) and (f).

---

## Blockers and incomplete work

Stated explicitly so nothing above reads as finished when it is not.

| Item | State | What is needed |
|------|-------|----------------|
| **A2d** stamp helper in launchers | **Open** | See the proposal in F1 below |
| **E1f** launcher migration | **Finished** | 9 of 9 |
| **A2d** stamp helper in launchers | **Open** | Blocks A2 leaving InTest, and blocks B2 (first Linux capture) from being recordable |
| **GROTH** | **Postponed** | A maintainer's decision; nothing else depends on it |
| **`Perf.md` retirement** | **Not ready** | Holds detail for B1, B3 and GROTH. Re-run the caveat diff (`MIGRATION.md` S6) before retiring |

---

## Aside -- will not do

| Item | Reason |
|------|--------|
| Drop `cs_main` during the witness height walk | Abort-and-restart cannot converge once walk time exceeds block spacing |
| CleanIndex gtest harness | Needs anchors and disk-backed blocks the gtest harness lacks; `reindex_shielded.py` covers the gap |
| FDCACHE buffer-size sweep | `FINDINGS.md` S3.2 |
| NEON blake2b **on the sync track** | `FINDINGS.md` S2.5. Does not apply to the mining use case -- see D1 |
| Halo / Orchard | Not Zero consensus |
| Post-Sapling bootstrap / sync captures | `FINDINGS.md` S3.4 |
| Remove dead `nNotarizations` | Opportunistic only, if `chain.h` is touched anyway |
| Native Windows ETW profiling | `../PerfPlatforms.md`; blocked on symbols and an unvalidated build path |

---

## Finished this cycle

| Item | Evidence |
|------|----------|
| Result schema: platform, version, features, fingerprint | `SCHEMA.md` |
| `platform_stamp.py`, `feature_bundles.json` | self-tests pass |
| Existing ledger rows back-annotated | `*.v2.jsonl`; originals kept |
| Flag classes: architectural / scenario / perf | `POLICY.md` S3 |
| Retention classifier; `archives/` never reclaimable | `retention.py`, `POLICY.md` S6 |
| `.host_salt` excluded from git | `.gitignore` |
| Timer defects found | `FINDINGS.md` S1.1 |
| Docs set restructured; 7 retired, 6 relocated | `MIGRATION.md`, `NOTES.md` |
| Shared shell library; 6 duplicated helpers consolidated | `perflib.sh` |
| Datadir disposition policy, default set-aside | `POLICY.md` S3.1 |
| `fix_ascii --fix` blast-radius guards | `POLICY.md` S7.4 |
| Tool self-tests gated; **17/17** Python tools plus `perflib.sh` | `lint-perf.sh` |
| Divide-by-zero and sign-inversion guards | `perflib.sh`, `bucket_profile2.py` |
| Platform-independent production-datadir protection | `zeropaths.py`, `POLICY.md` S3.1 |
| Read vs destroy split as separate permissions | `POLICY.md` S3.1 |
| Regression gate `validate.sh`; 15 self-tests + lint, logged per run | F1 |
| (192,7) Equihash analysis: memory fully explained, 144 MB target refuted, coupling corrected | `../equ/` |
| (192,7) solver baseline vectors captured and verified (was: none above 512 rows) | `solver_baseline_192_7` |
| Run logging: `warn()`/`die()` reach the driver log; `tiny_baseline.sh` and `validate.sh` keep durable logs | `POLICY.md` S3.2 |
| Full self-test coverage: `collate_cycle.py`, `shielded_density.py` | 17/17 |
| `collate_cycle`: missing rate no longer counted as 0.0 (dragged a mean from 100.0 to 33.3); malformed ledger line no longer aborts collation | `collate_cycle.py` |
| `accumulate_bench.collate`: one incomplete row raised `KeyError`, so **no** report could be produced from the whole ledger. Now excluded with a warning; report output verified byte-identical | `accumulate_bench.py` |
| Grouping keys: a missing height no longer collides with a genuine height-0 window | `accumulate_bench.py` |
| A1c: citation + absolute-path lint checks, gated | `check_citations.py` |
| F1b: stamping moved to the ledger writers, making an unstamped row unrepresentable | `accumulate_bench.py`, `profile_collate.py` |
| B1a: all 11 `-debug=bench` phase lines parsed (was 1) | `extract_measures.py` |
| B1b: `verify_excl_ms()` -- verify includes connect, so they are never summed | `extract_measures.py` |
| `validate.sh`: `A && B \|\| C` could record both PASS and FAIL | `validate.sh` |
| Real lab cycle: tiny reindex 187417 blk, 175.0 s, 1070.95 blk/s | ledger `labcycle-verify` |
| `tiny_baseline.sh` now appends to the throughput ledger (`CAMPAIGN` was documented but unused) | E1 |
| `rm -rf` eliminated outside the explicitly-forced path | E1 |
| `perflib.sh` resolves its own directory under zsh as well as bash | `perflib.sh` |
| All 9 launchers on `perflib.sh` | E1f |
| `fix_ascii.py` rename; Y/n confirm on every file change | `POLICY.md` S7.4 |

| Unicode backlog cleared and gated | `lint-perf.sh` `unicode-docs`, 0/0 |
| Absolute paths struck from tracked docs | `POLICY.md` S7.3 |
| `Perf.md` caveat diff: 0 orphaned rules | `MIGRATION.md` S6 |
