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
| A1 Enforce existing rules | InProgress | Open | S | `FINDINGS.md` S1.3 |
| A2 Record binary and platform | InTest | Open | M | `FINDINGS.md` S1.2, `SCHEMA.md` |
| A3 Microbenchmark baseline | ToDo | Open | S | `FINDINGS.md` S4 |
| B1 Phase timers | ToDo | Open | S-M | `FINDINGS.md` S1.1, `../PerfTimers.md` |
| B2 First non-macOS measurement | ToDo | Open | M | `../PerfPlatforms.md` |
| B3 NOTEIDX staleness | ToDo | Open | S | `FINDINGS.md` S3.1 |
| C1 Documentation consolidation | InProgress | Open | M | `MIGRATION.md` |
| C2 Remaining measurement gaps | ToDo | Open | M | `FINDINGS.md` S4 |
| C3 Inherited build/DB defects | ToDo | Open | M | `../BUILD_RECONFIG.md` |
| D1 Equihash / blake2 integration | ToDo | Open | M | `FINDINGS.md` S2 |
| GROTH | -- | Postponed | L-XL | `../PerfGroth.md` |

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
| a | Run `check-unicode.py --fix` | **Finished** -- 693 -> 0 in owned scope |
| b | Add `unicode-docs` to the default `CHECKS` | **Finished** -- scoped to owned docs, `keep/` excluded |
| c | Add a citation check: a bare figure with no `M-*` id, and an absolute-path check (`POLICY.md` S7.3) | ToDo |
| d | Add the working branch to the CI push trigger, and a lint job ahead of the build | ToDo |

(a) without (b) drifts again; (d) is where (b) and (c) stop being advisory.

**Kanban: InProgress. Effort S.** No product code. (a) and (b) Finished.

### A2. Record what the binary and platform were

Schema: **`SCHEMA.md`**.

| Step | What | State |
|------|------|-------|
| a | `platform_stamp.py` | Finished |
| b | `feature_bundles.json` | Finished |
| c | Back-annotate existing rows | Finished |
| d | Call the helper from every launcher | Open -- most of the remaining effort |
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
| a | Parse the 10 unparsed `-debug=bench` phase lines | ZeroPerf |
| b | Fix the verify/connect overlap | ZeroPerf + product |
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

| Step | What |
|------|------|
| a | Add new build-time options to `feature_bundles.json`; classify each |
| b | Ensure `features.workload.op` distinguishes solve / verify / sync |
| c | Record the baseline on the target host before any change |
| d | Confirm `platform.arch` is carried -- SIMD results are arch-specific |
| e | Keep the `blake2b` bucket ordered before `equihash` |

Harness: `mine_bench.sh`, `performance-measurements.sh`, KATs in
`src/test/data/`.

**Kanban: ToDo. Effort M**, dominated by (c).

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
| Unicode backlog cleared and gated | `lint-perf.sh` `unicode-docs`, 0/0 |
| Absolute paths struck from tracked docs | `POLICY.md` S7.3 |
| `Perf.md` caveat diff: 0 orphaned rules | `MIGRATION.md` S6 |
