# Plan

What to decide and what to do next, grouped so that related work moves
together. **One line per item.** Detail lives in the document that owns the
subject; if an item needs explaining, the explanation belongs there, not here.

Status carries two independent ratings:

| Axis | Values | Means |
|------|--------|-------|
| **Kanban** | ToDo, InProgress, InTest, Closed | where the card is |
| **Disposition** | Open, Blocked, Fixed, Postponed | what happened to the issue |

`Closed/Fixed` is repaired; `Closed/Postponed` is dropped without repair. A
card is not Closed until its result is recorded where the subject lives.

`TASKS.md` is frozen and superseded; ids are preserved.

---

## Decisions outstanding

These block or redirect work below. Nothing else here needs an answer.

| # | Decision | Bearing |
|---|----------|---------|
| 1 | **Documentation target shape**: seven owned files | Group D below |

**GROTH** is deferred to the maintainer's own schedule, after this
consolidation effort is validated and released. It is not raised again here;
its state is `PerfGroth.md`.

---

## A. Witness bottleneck -- the largest measured win available

Owner: `Perf.md` S0, moving to `FINDINGS.md`. Sequence is strict.

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| A1 | Narrow `fNoteTxIndexStale` invalidation (was P2) | ToDo | Open |
| A2 | Review `Perf.md` L85-194 for redundancy and stale content, with A1 | ToDo | Open |
| A3 | Benchmark both bottlenecks | ToDo | Blocked on A1, F3 |
| A4 | Remeasure `-rescan`; overnight, scripted, outside the harness | ToDo | Blocked on A1 |

A1 is specified and ready. A4 before A1 would reproduce the existing figure and
establish nothing.

---

## B. Locking

Owner: `LOCKS.md`.

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| B1 | Validation method: order, balance, races, contention, throughput | ToDo | Open |
| B2 | `IsInitialBlockDownload` `cs_main` acquisitions (was P21) | InTest | Open |
| B3 | Nine recursive `LOCK` sites (was P14) | ToDo | Open |
| B4 | Shielded note selection has no locking (was P9) | ToDo | Open |
| B5 | Retract `LOCKS.md`'s claim on the unallocated id P25 | ToDo | Open |

B2 is fixed by hoisting the flag test above the lock; it needs the post-fix
measurement before it closes. B4 is a correctness gap, not a frequency
question: shared lists and indexes need locking whatever their call rate.

---

## C. Messaging and logging

Owner: needs one. Inventory exists: `log_inventory.py`, 1,388 call sites, 590
gated, 798 always-on, 31 categories.

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| C1 | Catalogue outcomes and propose a disposition per class | ToDo | Open |
| C2 | Review level and area assignment (was P16) | ToDo | Blocked on C1 |
| C3 | Work-queue rejection returns no client-visible error | ToDo | Open |
| C4 | Alerting criteria: what an operator must see, and how | ToDo | Blocked on C2 |

C1's output is a reviewable list in the owning document, not in this file.

---

## D. Documentation

Owner: `POLICY.md` S2.0. Target: seven owned files.

| Target | Absorbs |
|--------|---------|
| `FINDINGS.md` | `Perf.md` less its B1/B3/GROTH detail, `NOTES.md` |
| `PerfGroth.md` | -- |
| `CONCURRENCY.md` | `THREADS.md`, `SCRIPTQUEUE.md` |
| `LOCKS.md` | -- |
| `METHOD.md` | `CPU_MEASUREMENT.md`, `HOWTO.md`, `TOOLING_FAILURES.md`, `SCHEMA.md`, `RECORDS_READINESS.md` |
| `TESTING.md` | test material from `TASKS.md`, `SODIUM_SURVEY.md`, `HOWTO.md`, `POLICY.md` |
| `OPERATIONS.md` | queue, RPC and REST sizing |

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| D1 | Consolidate to the target shape; keep a retirement ledger | InProgress | Open |
| D2 | Unify `Perf.md` section numbering, then retire it | ToDo | Blocked on A2, D1 |
| D3 | Prune cross-references to those still valid; extend `check_citations.py` to catch the rest | ToDo | Blocked on D1 |
| D4 | Migrate remaining `TASKS.md` ids; retire the A-F and T/R letters | InProgress | Open |

`TESTING.md` is written. Subject documents hold only their subject: the
hash-library survey should not carry wallet-test results.

---

## E. Cheap measurements, no prerequisites

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| E1 | `Xc.reserve()` -- one line, paired run exists (was D2) | ToDo | Open |
| E2 | Re-bucket archived captures for the non-blake2b surface -- no new run (was R1) | ToDo | Open |
| E3 | Microbenchmark baseline, 4 of 17 run (was A3) | InTest | Open |
| E4 | Threaded solver: measure, document procedure, add to corpus (was P22) | ToDo | Open |

E1 and E2 are the least costly real results available.

---

## F. Cross-platform

Owner: `METHOD.md` once D1 lands.

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| F1 | Linux VPS and Windows/WSL runbook (was B2) | ToDo | Open |
| F2 | First non-macOS capture | ToDo | Blocked on F1, host |
| F3 | Disposable tip above height 492850 with notes in range | ToDo | Open |
| F4 | Re-validate the consolidated tree on another platform | ToDo | Blocked on F2, D1 |

Every existing measurement is macOS/arm64 on one host. F2 moves four items out
of InTest at once.

---

## G. Testing

Owner: `TESTING.md`. All test state, defects and suite work live there.

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| G1 | Suite plan: maturity constant, `initialize_chain_clean` ratio, 23 failures by mode | ToDo | Open |
| G2 | A bare GTest run aborts and prints no summary | ToDo | Open |

---

## H. Process

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| H1 | No presentation-only edits to inherited files; `validate.sh` check | Closed | Fixed |
| H2 | A card closes only with its result recorded; `validate.sh` check | ToDo | Open |

H1's rule: formatting changes only inside a hunk already being changed for a
functional reason. Such edits otherwise recur at every upstream merge and bury
real changes in review.

H2 exists because a fix reached the tree with a correct in-code comment and no
record anywhere.

---

## Product handoff

Node code owned by Zero400, tracked here because the evidence is here.
Dependency: P5 before P6; P6 subsumes what remains of P4.

| Id | Item | Kanban | Disp |
|----|------|--------|------|
| P1 | Proof-verification counters | InTest | Open |
| P4 | Witness RPC gate inconsistent | InTest | Open |
| P5 | `boost::optional` to `std::optional` | ToDo | Open |
| P6 | Anchor depth for shielded spends | ToDo | Blocked on P5 |
| P7 | Coin-selection call clarity -- find existing coverage first | ToDo | Open |
| P8 | FDCACHE disposition | ToDo | Postponed |
| P10 | Explicit parameters at defaulted calls | ToDo | Open |
| P13 | `CheckBlock` runs 3x per block | ToDo | Open |
| P17 | Out-of-order child on reindex | ToDo | Open |
| P18 | `ShrinkDebugFile` keeps the tail | ToDo | Open |
| P19 | Delete unbuilt `src/snark/` | ToDo | Open |
| P20 | `-par=0` allocates idle workers | ToDo | Open |
| P24 | `getchaintips` is O(chain length) | ToDo | Open |

P1 gates any phase summary: proof verification sits in no timer, so a summary
built today omits most post-Sapling cost while appearing complete.

P24: measure insert and erase separately before choosing a fix. The ordered set
is maintained continuously by its comparator and only 214 survivors need
ordering; not materialising the full set may remove the cost entirely.

Closed: P11, P12, P15, P23 (Fixed). P14 to B3, P16 to C2, P21 to B2, P22 to E4,
P9 to B4, P2 to A1. Never allocated: P3, P25.
