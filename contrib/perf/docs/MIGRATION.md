# Migration into contrib/perf/docs

State of the consolidation: 21 documents / 6809 lines in `contrib/perf/`
becoming a small set in `contrib/perf/docs/` -- 6 written so far, 3 pending.

**Complete (2026-08-21).** Seven documents were retired and six relocated to
`../keep/`. Eight remain live in `contrib/perf/`. The table in S3 is kept as
the record of where each source went -- entries naming a retired file describe
history, not a current path.

Current state: `NOTES.md` indexes what was kept and what was retired.

---

## 1. Why

The set grew past reviewability. Concretely: across three working sessions the
set was read repeatedly and still *grew* by 5 documents, because every new
finding looked like it needed a new home. That is the failure mode, and adding
another document rather than consolidating would repeat it.

The replacement is small enough to hold in view, organised by **the reader's
question** rather than by investigation order.

## 2. Target set

| Document | Subject | State |
|----------|---------|-------|
| `OVERVIEW.md` | Vision, problem, goals, reader routing | **Finished** |
| `README.md` | Entry point and rules | **Finished** |
| `SCHEMA.md` | Result schema, versioning, features, fingerprint | **Finished** |
| `TASKS.md` | Consolidated open work, Kanban board | **Finished** |
| `POLICY.md` | Rules, flag classes, lab discipline, cleanup | **Finished** |
| `HOWTO.md` | Measurement workflow | **Finished** |
| `FINDINGS.md` | What we know and how confident | **Finished** |
| `NOTES.md` | Frozen point-in-time evaluations | **Finished** |

## 3. Source disposition

| Source | Lines | Disposition |
|--------|------:|-------------|
| `BENCHMARKING.md` | 342 | -> `HOWTO.md` (**Finished**). Parts 2.4 / 3.2 / 4.5 delegated to `FINDINGS.md`, `POLICY.md`, `SCHEMA.md` rather than copied. **Superseded** |
| `Perf.md` | 1875 | **Split four ways**: vision/problem -> `OVERVIEW.md` (**Finished**); durable results -> `FINDINGS.md` (**Finished**); volatile status -> `TASKS.md` (**Finished**); dated evaluations -> `NOTES.md`. Groth16 bulk stays in `PerfGroth.md`. 72% is one section; the largest single job |
| `Measures.md` | 444 | -> stays as the `M-*` inventory, cited by `FINDINGS.md`. Not merged -- it is a data file in prose form |
| `PerfDoc.md` | 305 | S1-S5 -> `POLICY.md` (**Finished**); S6-S10 duplicate `BENCHMARKING.md` Part 4, drop on migration. **Superseded** |
| `PerfTasks.md` | 118 | -> `TASKS.md`. **Superseded** |
| `PerfNext.md` | 400 | -> `TASKS.md` + `FINDINGS.md`. **Superseded** |
| `PerfDocReview.md` | ~300 | -> this file + `NOTES.md`. **Superseded** |
| `README.md` | 417 | Per-tool reference. Candidate for tool `--help` instead of prose |
| `PerfTimers.md` | 280 | Keep as a spec until built, then -> `FINDINGS.md` |
| `PerfPlatforms.md` | 267 | Keep as a survey until acted on, then -> `FINDINGS.md` + `NOTES.md` |
| `PerfStores.md` | 325 | **Superseded by `SCHEMA.md`** |
| `PerfGroth.md` | 173 | **Keep and expand.** The focused Groth16 document; other files cite it and carry none of its bulk. Not folded into `FINDINGS.md` |
| `PERF_RESTRUCTURE.md` | 84 | -> `NOTES.md`. Its diagnosis is being acted on here |
| `BUILD_RECONFIG.md` | 89 | Keep while `C3` is open |
| `Stores.md` | 170 | Chain/datadir storage. Live; see `NOTES.md` |
| `Peer.md` | 471 | Off-subject: ops notes -> Zero400 |
| `TENT.md`, `TENTZero.md` | 123 | Off-subject: fork lineage -> out-of-tree ZKs notes |
| `ZcashV.md` | 132 | Off-subject: security notes. **0 inbound** |
| `ZeroWallet_Design.md`, `desys.md` | 475 | **Out of scope** -- Qt wallet UI; `AGENTS.md` says full node only. **0 inbound** |

## 4. Dated notes

Indexed with their dates, versions and supersession state in **`NOTES.md`**,
which is the durable record. Archive policy is `POLICY.md` S5. Neither is
repeated here.

## 5. Order -- completed

1. **`OVERVIEW.md`, `README.md`, `SCHEMA.md`, `TASKS.md`, `POLICY.md`** --
   Finished. New work lands here.
2. **`HOWTO.md`, `FINDINGS.md`, `NOTES.md`** -- Finished. The docs set is
   complete; every subject has a home.
3. **Retire superseded originals** -- **done 2026-08-21**, seven files, after
   each had a home. `PerfDoc.md` S1 routing and S3 scope were redistributed
   into `POLICY.md` S7.1/S7.2 first; `PERF_RESTRUCTURE.md` had every claim
   validated against `Perf.md` before removal.
4. **Relocate off-subject material** -- **done**, six files to `../keep/`.

## 6. Caveat diff -- `Perf.md` (2026-08-21)

The stated risk of the consolidation was losing a hard-won caveat while
summarising. `Perf.md` was checked mechanically before being kept.

| Measure | Result |
|---------|--------|
| Normative lines (`do not` / `never` / `must not`) in `Perf.md` | **107** |
| Already carried by the new set | 47 |
| Reviewed individually | 60 |
| **Genuinely orphaned rules found** | **0** |

What the 60 turned out to be, by subject: witness / RPC-code behaviour (22),
implementation detail for open items (10), measurement discipline (9),
lab and datadir safety (7), consensus and code specifics (6), Groth16 (5),
ownership (1).

**Conclusion: nothing is orphaned, and `Perf.md` must stay.** The uncovered
lines are not rules the new set dropped -- they are implementation detail bound
to work that has not landed yet:

- **Witness `-31` / `-33` RPC codes** -- 55 sites in `Perf.md`, and 5 in
  Zero400's `TODO.md`, which owns that surface (`POLICY.md` S7.1).
- **`assumeutxo` / skip-chain, `fZindex`** -- single mentions of explicitly
  out-of-scope or not-pursued options. Correctly absent from a set describing
  current work.
- **NOTEIDX staleness detail** -- the `AddToWallet` / `EraseFromWallet`
  invalidation rules belong with `TASKS.md` B3 and move to `FINDINGS.md` when
  that lands.

**Rule going forward:** `Perf.md` is retired only when the open items it holds
detail for -- B1, B3, GROTH -- have landed and their caveats have moved to
`FINDINGS.md`. Re-run this diff before retiring it.

---

Retiring originals carries the remaining risk: losing a hard-won caveat while merging. Mitigation
is the one the original proposal named -- mechanically diff all `M-*` ids and
all "do not" / "keep after" warnings before and after.
