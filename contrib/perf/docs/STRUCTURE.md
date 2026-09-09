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
of none. `Equihash`: 21 files, and the directory that
exists for it (`equ/`) holds **25%** while `Perf.md` holds 28%.

Fifteen percent of `Perf.md`'s lines mention a subject that another document
owns.

`Perf.md` and `TASKS.md` each touch **13 of the 14**. A reader chasing witness
behaviour consults eleven files and reconciles them.

## 2. Rules, partition and constraints

All three are `MAP.md`: what each document is for, the one-owner rules, and
what must not happen during a move. They are durable; this file is the
transient plan for getting there.

## 2.6 Terms that accumulated dozens of mentions

Measured 2026-09-08 across all `contrib/perf` markdown. A term appearing in
many files is not itself a fault -- a tool name cited from ten places is
correct. What these eight share is that **no document holds a majority**, which
means the subject is discussed wherever it is met rather than covered once.

| Term | Mentions | Files | Largest holder | Assessment |
|---|--:|--:|--:|---|
| `wallet` | 498 | 26 | Perf.md 36% | **No owner.** Largest single term in the tree |
| `reindex` | 290 | 20 | Perf.md 38% | **No owner.** Operation named in every launcher document |
| `witness` | 252 | 15 | Perf.md 58% | Weak owner; `docs/WITNESS.md` is planned and would take it |
| `Sapling` | 221 | 20 | Perf.md 38% | **No owner.** Era marker used as a shorthand for "post-492850" |
| `datadir` | 139 | 13 | README 27% | **No owner.** The rule is POLICY S4; the rest restate it |
| `Equihash` | 137 | 22 | Perf.md 22% | `equ/` owns it and holds 54%; the 22 files are the problem |
| `blake2b` | 133 | 19 | Perf.md 19% | `HASHLIBS.md` now owns it; sweep pending |
| `tromp` | 130 | 13 | VENDORED 30% | Owner correct, share too low |

**What to do with each is not the same.**

- `wallet`, `reindex`, `Sapling`, `datadir` are **vocabulary**, not subjects.
  They will appear wherever the work is described, and chasing the count is
  pointless. What is worth fixing is the *rule* restatement behind `datadir`
  (POLICY S4 owns it) and the *finding* restatement behind `reindex`.
- `witness`, `Equihash`, `blake2b`, `tromp` are **subjects with owners**. Their
  counts are a real defect and `check_concentration.py` gates them.

**The distinction matters more than the counts.** A term that names a subject
must concentrate; a term that names an operation or an era will not, and a
target for it would be enforced by deleting useful prose.

## 2.7 Where the mentions actually are, and what to do

**Scoped by area** (2026-09-08). The sprawl is not repo-wide:

| Term | `contrib/perf` | `qa/` | repo root |
|---|--:|--:|--:|
| `wallet` | 727 | 221 | 284 |
| `reindex` | 579 | 22 | 98 |
| `Sapling` | 520 | 112 | 50 |
| `blake2b` | **531** | 4 | 3 |
| `witness` | 407 | 35 | 24 |
| `Equihash` | 319 | 3 | 38 |
| `Groth16` | 270 | 0 | 2 |
| `tromp` | 195 | 0 | 1 |

`contrib/perf` holds the great majority of every term, and for `blake2b`,
`Groth16` and `tromp` it holds essentially all of them. **The problem is this
directory's, not the repository's**, which is why the work is scoped here and
why `qa/` and the root are referenced rather than edited.

### `(192,7)`: 154 mentions reviewed line by line

Distribution: `equ/` 109, `Measures.md` 10, `Perf.md` 8, `mine/` 9, remainder
scattered. Zero400-owned root documents hold a further 30 and are not editable
from this tree (`POLICY.md` S7).

**Reviewed, not counted.** 59 occurrences are in table rows, spread across
**35 distinct tables**; the rest are prose. (An earlier revision said 73 rows;
that counted headings as rows.) The three `SOLVER.md` tables sharing a
`(48,5) | (192,7) | (200,9)` header were checked individually and hold distinct
content -- protocol constants, tromp tuning constants, derived bucket capacity.

**The count that matters more:** `contrib/perf` markdown contains **474
tables**. `(192,7)` reaching 35 of them is a symptom of that, not a separate
problem.

**What is genuinely repeated** is the *comparison frame itself*: five documents
independently establish that Zero runs `(192,7)` and explain why `(200,9)` work
does not transfer. That framing belongs in one place, cited from the others.

| Document | Mentions | Should it hold the frame? |
|---|--:|---|
| `equ/SOLVER.md` | 26 | Yes -- derives the constants |
| `equ/FINDINGS.md` | 26 | No -- cite SOLVER |
| `equ/VENDORED.md` | 21 | No -- cite SOLVER |
| `equ/METHOD.md` | 19 | No -- cite SOLVER |
| `equ/PLAN.md` | 12 | No -- cite SOLVER |

An earlier revision of this section reported 201 and then, on recount, called
the concentration good. Both were wrong: the first figure included `.prev-*`
backups, and the second substituted a ratio for a reading. The count is not the
finding; the duplicated framing is.

### 472 tables against a target of about 24

Target: **no more than 10 tables per file, roughly two dozen across the set**,
`Measures.md` excepted as a registry.

Counts below are a snapshot [2026-09-08]; `check_tables.py` is the authority
and the numbers move with every edit.

| File | Tables | Over 10 by |
|---|--:|--:|
| `Perf.md` | **64** | +54 |
| `docs/TASKS.md` | **48** | +38 |
| `equ/SOLVER.md` | **43** | +33 |
| `equ/PLAN.md` | 26 | +16 |
| `equ/VENDORED.md` | 25 | +15 |
| `Measures.md` | 25 | registry, exempt |
| `PerfGroth.md` | 23 | +13 |
| `equ/FINDINGS.md` | 18 | +8 |
| `keep/Peer.md`, `keep/ZeroWallet_Design.md` | 15 each | archived notes, not maintained |
| `docs/POLICY.md` | 13 | +3 |
| `recbench/RecBench.md`, `equ/METHOD.md` | 11 each | +1 |

**13 files exceed 10; 207 tables above the per-file limit.** The set total is
472 against a target near 24 -- a factor of twenty.

`docs/PRODUCT.md` and `docs/HASHLIBS.md` were on this list at 12 each and have
since been brought to 10 and 9 (`TASKS.md` C1n, worked improvements), which is
why the file count is 13 rather than the 15 an earlier revision recorded.

**`Measures.md` reviewed, and it was not exempt.** An earlier note here
excused its 25 tables as "a registry doing its job". Checking the headers
showed **twelve of them shared the identical header**
`ID | Metric | Result | Type | Tools | Source` -- one relation split twelve
ways by section heading, six of the twelve holding three rows or fewer.

Normalised 2026-09-08: category became a **column**, the twelve headers became
one, and the ten redundant category headings were removed. All 105 `M-*` ids
survive. The physical table count stays at 25 only because explanatory prose
sits between some row groups; the relation is now single, which is what
mattered.

Twelve identical headers over one relation is a split table, whatever the
file is called.

**Where the excess is.** Three files hold 155 of the 472: `Perf.md`,
`TASKS.md`, `equ/SOLVER.md`. Two of those are already scheduled for splitting
(S3), which is the cheapest route to the target -- a table that moves to the
document that owns its subject stops being a duplicate of one three sections
away.

**A worked example.** `docs/PRODUCT.md` item **P4** carried nine tables under
one heading for a single product finding; two were lists in grid form and are
now sentences, leaving seven. Seven is still one argument split seven ways --
family comparison, gate behaviour, call-site inventory -- where two or three
would carry the comparisons a reader makes.

### Which tables to cut, and what to replace them with

**Threshold: at least 2 data rows, and rows x columns at least 9.** One row is
a sentence. Two rows over two columns is a phrase. Two rows over five columns
is a real A/B and passes. Enforced by `check_tables.py`, reported in
`lint-perf.sh`.

Against the tree: **84 of 472 tables fail**, and 13 files exceed the
ten-per-file ceiling. Shapes, worked examples and the order of work are in
`TASKS.md` C1n; not repeated here.

The threshold is necessary, not sufficient -- it cannot see content. A table
can pass on size and still be one of these:

**One data row.** It is a sentence. `Measures.md` S3.10-3.12 each held one.

**A list of sites or names with a one-clause note each.** Use prose or a
vertical list. `PRODUCT.md` had two of these -- three call sites with their
false-return handling, three tests with what they pin -- both now sentences.

**An enumeration of components already listed elsewhere.** Cite the list; do
not restate it as a grid.

**A status grid the board already holds.** `TASKS.md` owns state; a second copy
diverges.

**Ten per file is a ceiling, not a goal.** A file at ten tables can still be
badly decomposed -- ten grids where four sections and some prose would read
better. The count is a tripwire; the question underneath is whether each table
has rows a reader compares. `PRODUCT.md` at ten is under the limit and still
carries seven of its ten tables under a single heading (P4).

Replacements, in rough order of preference: a **sentence** when there is one
fact; a **comma-separated clause** when there are two or three parallel items;
a **vertical list** when each item needs its own line but no columns; a
**subsection heading** when the items are large enough to need their own
context. A table is the last resort, not the default shape.

### The structural cause

`Perf.md` is **1553 lines, of which section 0 is 1141 (73%)** across 22
subsections. It is a status document living inside a findings document. That
single fact explains most of the counts above: every subject acquires a status
line, a plan line, a priority-table row and a stage-list entry, so a subject
mentioned once in findings is mentioned five times in section 0.

The 28 Groth16 mentions in `Perf.md` are not justified by anything. They are 28
restatements of "Groth16 is postponed" in different tables.

Sections 7 and 8 are a second instance at smaller scale: both cover
`AddToBlockIndex` allocation (§7 has 17 `allocat*`, §8 has 4), and §8 is a
detail expansion of §7's finding rather than a separate subject.

### Mitigations, in order

**Immediate, mechanical, no judgement needed:**

1. **Split section 0 by destination -- it does not move wholesale.** An earlier
   version of this plan said it did; classifying its 16 subsections by content
   shows otherwise:

   | Destination | Subsections | Lines |
   |---|---|--:|
   | `TASKS.md` -- task ids and state only | 0.2, 0.11, 0.12 | ~70 |
   | `docs/WITNESS.md` -- findings | **0.14** | **386** |
   | `docs/OPS.md` -- findings | **0.16** | **267** |
   | Mixed, needs reading | 0.13, 0.15 | 283 |
   | Small, fold into neighbours | 0.1, 0.3, 0.5, 0.6, 0.8a | ~45 |
   | Findings, stay or move with their subject | 0.2a, 0.2b, 0.4, 0.9 | ~84 |

   **Only ~70 of 1141 lines are pure task material.** The section is not
   misfiled status; it is three documents wearing one heading. Moving it
   wholesale to `TASKS.md` would put 650 lines of findings in the task list --
   the same error in the opposite direction.
2. **Merge §7 and §8.** One subject, one section.
3. **Delete the priority/stage tables that restate the board.** They exist in
   `TASKS.md`; in `Perf.md` they are copies that diverge.

**Stepwise, needs reading:**

4. Extract `docs/WITNESS.md` (witness at 407 mentions, 58% held) and
   `docs/OPS.md` from what remains of section 0.
5. Sweep `Equihash` into `equ/` -- 319 mentions here against `equ/` holding
   54%.
6. Re-run `check_concentration.py` after each step; it is the acceptance test.

**The measurable target** is in `MAP.md` S3: no subject more than 20% outside
its owner. Steps 1-3 are expected to reach it for `Groth16` and `blake2b`
without any editorial judgement at all -- the material is misfiled, not
badly written.

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

