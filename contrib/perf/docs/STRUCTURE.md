# Document structure: what is wrong, measured, and the plan to fix it

`contrib/perf` documents overlap heavily. This states the problem in numbers,
proposes a partition by ownership, and sequences the work. It is a plan; the
only parts executed so far are noted as **Done**.

Written 2026-09-06.

## 1. The problem, measured

### 1.1 Perf.md is 77% task tracking

| Section | Lines | Nature |
|---|--:|---|
| **S0 Status at a glance** (22 subsections) | **1359** | Status and task tracking |
| S1 Scope and method | 76 | Findings |
| S2 CPU cost breakdown | 64 | Findings |
| S3 Disk I/O and the fd-cache fix | 51 | Findings |
| S4 Merkle-root latch | 27 | Findings |
| S5 Equihash hashing | 24 | Findings |
| S6 Groth16 batch headroom | 80 | Findings |
| S7 Memory profiling | 38 | Findings |
| S8 `AddToBlockIndex` detail | 59 | Findings |
| S9 Status review and paths | 93 | Status |
| **Total** | **1883** | **1452 lines (77%) are status** |

The document's actual findings are **419 lines**. Everything else is work
tracking that `TASKS.md` exists to hold.

### 1.2 The two files track the same work, separately

| | Task ids tracked |
|---|--:|
| `Perf.md` | **41** |
| `docs/TASKS.md` | 11 |
| Tracked in **both**, independently | **8** ids |

Eight items have two status records that can disagree, and have: one was
carried as "postponed" in `Perf.md` after the underlying question had been
answered elsewhere.

Worst single offender: **S0.13 "Plans and specifications"** -- 187 lines
holding **74 task ids and 21 status markers**. That is a task list inside a
findings document.

### 1.3 No document owns a topic

Fourteen recurring topics, counted across all `contrib/perf` markdown:

| Topic | Mentions | Files | Largest holder | Its share |
|---|--:|--:|---|--:|
| `wallet` | 515 | **23** | `Perf.md` | 36% |
| `reindex` | 293 | 19 | `Perf.md` | 41% |
| `witness` | 254 | 12 | `Perf.md` | 58% |
| `Sapling` | 219 | 16 | `Perf.md` | 51% |
| `Equihash` | 145 | **21** | `Perf.md` | **28%** |
| `tromp` | 133 | 13 | `equ/VENDORED.md` | 29% |
| `Groth16` | 131 | 16 | `Perf.md` | 55% |
| `NOTEIDX` | 108 | 10 | `Perf.md` | 76% |

**`Perf.md` is the largest holder of 10 of 16 topics** and the designated owner
of none. `Equihash` is the sharpest case: 21 files, and the directory that
exists for it (`equ/`) holds **25%** while `Perf.md` holds 28%.

Fifteen percent of `Perf.md`'s lines mention a subject that another document
owns.

`Perf.md` and `TASKS.md` each touch **13 of the 14**. A reader chasing witness
behaviour consults eleven files and reconciles them.

## 2. Rules, partition and constraints

All three are `MAP.md`: what each document is for, the one-owner rules, and
what must not happen during a move. They are durable; this file is the
transient plan for getting there.

## 3. Sequence

| # | Step | Effort | State |
|--:|---|---|---|
| 1 | Archive superseded planning artifacts to `ZK/OLD/SAVE` | S | **Done** 2026-09-06: `Perf.md` S9.2 NEON plan, `summary.txt`, an early disposition draft |
| 2 | Move S0.13 (74 ids) into `TASKS.md` | S | Highest ratio of duplication removed per line moved |
| 3 | Move remaining pure-status subsections into `TASKS.md` | M | S0.0-0.7, S0.9, S0.11, S0.12, S0.15, S9.1 |
| 4 | Extract S0.14 to `docs/WITNESS.md` | M | Largest single findings block, currently buried in a status section |
| 5 | Extract S0.16 to `docs/OPS.md` | M | -- |
| 6 | Fold S6/S9.3/S9.4 into `PerfGroth.md` | M | -- |
| 7 | Sweep `wallet`/`witness` mentions across the remaining files | L | Do last; least mechanical |

**Do steps 2-3 before 4-7.** Removing the status material first shrinks the
document that the later steps have to reason about, and removes the
double-tracking that makes any move ambiguous.

