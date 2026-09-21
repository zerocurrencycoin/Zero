# Plan

Work register, grouped by subject and code area. Within a group, items are
ordered by dependency first, then priority, urgency, complexity and risk.

**Detail belongs here** when this file is where the work is decided: an
implementation plan, the options considered, the reason one was chosen. Items
whose full treatment lives in another document carry a reference and only
enough text to schedule them or establish a dependency.

**Relationship to `TASKS.md`.** PLAN.md supersedes it for scheduling.
`TASKS.md` is frozen pending migration (X1); do not add to it. Ids are
preserved so existing citations resolve.

Status: **Kanban** ToDo | InProgress | InTest | Done. **Disposition** Open |
Blocked | Done | Postponed | Aside. Every item carries both. Aside means
postponed pending review, not refused.

**A change is not Done until its measurement is recorded.** Code that works
but has no measured result and no documented status is indistinguishable from
code nobody has checked. See X5 for the mechanism that enforces this.

---

## Group W -- Working tree and commit

Area: `src/`, repository hygiene.

### W1. Presentation-only changes removed

Kanban Done / Disposition Done. `test-logs/w2-build-20260921/` (build and
tests after the revert).

Three blank-line insertions (`arith_uint256.cpp:109`, `main.cpp:160`,
`main.cpp:181`) removed; `arith_uint256.cpp` left the diff entirely, having
carried no functional change. Found with `git diff -U0 | grep '^+$'`.
`validate.sh`'s whitespace check covers trailing whitespace and tabs, not
blank-line insertion, so it reported clean throughout.

**Rule.** No presentation-only edits to inherited upstream files. `src/` is a
Zcash fork with live upstream drift; such edits recur at every merge and code
copy and bury functional changes in review. Formatting changes only inside a
hunk already being modified for a functional reason.

**Extend the check.** `validate.sh` gains a rule that fails on a hunk
consisting solely of blank-line additions or removals in `src/`. Without it
this recurs; the rule above is a convention, the check is the enforcement.

### W2. Build and test the reverted tree

Kanban Done / Disposition Done. `test-logs/w2-build-20260921/`.

Three lines were removed by script and verified by eye, not by compiler, so
the build is the gate. `make -j12` clean, exit 0; `zerod`, `test_bitcoin` and
`zero-gtest` all relinked; binary reports `v4.0.1-37f3f3459-dirty`.

Results, 2026-09-21:

| Suite | Result |
|-------|--------|
| Boost `test_bitcoin` | 325 test cases, no errors |
| `zero-gtest`, project filter | **220 passed**, exit 0 |
| `zero-gtest`, unfiltered | aborts in `WalletTests.CachedWitnessesCleanIndex` |

The unfiltered abort is expected and is not a regression.
`CachedWitnessesCleanIndex` is a **deliberately held failing test**: added
upstream as `1fc3c86f9` ("Add a reindex test that fails because of a bug in
decrementing witness caches", Zcash PR 1904, 2016) and excluded by this
project's own `qa/zcash/test_filters.sh:7`. Its reindex scenario needs the
`pcoinsTip` + `ReadBlockFromDisk` path the gtest harness cannot provide.
Deterministic, 3 of 3 in isolation, on every platform.

**Run gtest through `qa/zcash/test_filters.sh`, not bare.** A bare
`./src/zero-gtest` aborts on this test and reports nothing else, which is how
it gets misread as an intermittent fault.

### W3. Commit `contrib/perf/` and the four src fixes

Kanban ToDo / Disposition **Blocked** on W2.

Commit on `perf_b1b2`, do not push pending review. The four src changes are
independently justified and each cites upstream precedent or a measurement.
Branch is currently level with origin, so the commit is cheap and reversible.
Holding the work while the documentation reorganization runs across sessions
risks losing provenance.

---

## Group X -- Register structure and process

### X1. Migrate TASKS.md into PLAN.md; fix structural defects on the way

Kanban InProgress / Disposition Open.

P-ids preserved. Defects to resolve during migration, not after: P21 has a
section and no board row; P24 a row and no section; P4-P7 rows cite sections
that do not exist; P25 is cited by `LOCKS.md` but was never allocated. Each
migrated item gets both status ratings and a verified current state -- several
board rows are known stale (see L3).

### X2. Disposition `Finished` renamed to `Done`; both ratings on every item

Kanban InProgress / Disposition Open.

Applied in this file. X2 covers items still to migrate.

### X3. Retire the A-F and T/R group letters

Kanban ToDo / Disposition Open.

The letters encode no property a reader can predict: section order runs
A, B, C, D, F, E; `A5` sits under "B -- after A"; the A2/A4 table sits under
"E". PLAN groups are subject-named instead. Migration maps old ids to new
groups once, in X1.

### X4. `M-*` and `INV-*` registers

Kanban ToDo / Disposition Open.

`M-*` is justified and stays: measurement ids owned by `Measures.md`, cited
from findings, never scheduled. `INV-*` has one member (`INV-ARM-MIX`, the
deployment fleet mix gating ARM vector work); fold it into E5 and retire the
prefix.

### X5. Definition of Done, and the mechanism that enforces it

Kanban ToDo / Disposition Open.

**Problem.** A fix landed in `37f3f3459` with a correct in-code comment citing
its own measurement, and no register entry anywhere. It was invisible to both
tracking documents. Separately, several items sit at InTest with no record of
what would move them to Done.

**Definition.** An item is Done when all four hold:

1. the change is in the tree,
2. its measurement is recorded with a `test-logs/` path or `M-*` id,
3. the owning document states the outcome,
4. this register says Done with both ratings.

A change satisfying only (1) is **InTest**, never Done. An implementation
without a measurement is an unfinished task, not a finished one.

**Enforcement.** `validate.sh` gains a check: for each item here at Kanban
Done, require a `test-logs/` path or `M-*` id in its row. This is mechanical
and cheap, and it is the only proposal here that prevents recurrence rather
than describing it.

**Inbound direction too.** A commit touching `src/` with no PLAN item
referenced is the other half of the same gap. Cheapest workable form: a
pre-commit reminder, not a hard block, since lab-only commits are frequent and
legitimate.

---

## Group D -- Documentation consolidation

Area: `contrib/perf/docs/`. Supersedes TASKS.md C1.

**Target shape.** Seven documents, from twenty-one.

| Target | Absorbs | Subject |
|--------|---------|---------|
| `FINDINGS.md` | `Perf.md` (less B1/B3/GROTH detail), `NOTES.md` | What is known |
| `PerfGroth.md` | -- | Groth16 |
| `CONCURRENCY.md` | `THREADS.md`, `SCRIPTQUEUE.md` | Threads, pools, sizing |
| `LOCKS.md` | -- | Locking |
| `METHOD.md` | `CPU_MEASUREMENT.md`, `HOWTO.md`, `TOOLING_FAILURES.md`, `SCHEMA.md`, `RECORDS_READINESS.md` | Testing, validation, tooling, records |
| `OPERATIONS.md` | queue/RPC/REST sizing | Operational tuning |
| `PLAN.md` | `TASKS.md` | This file |

### D1. Relocate B1/B3/GROTH detail out of `Perf.md`, then retire it

Kanban ToDo / Disposition **Blocked** on B1, D6. `Perf.md` is marked not ready
for retirement precisely because it holds this detail; relocating it is the
gate.

### D2. Fold `THREADS.md` and `SCRIPTQUEUE.md` into `CONCURRENCY.md`

Kanban ToDo / Disposition Open. Thread census, pool sizing and the
`max_concurrent`-versus-occupancy lesson are one subject.

### D3. `LOCKS.md` stays dedicated

Kanban ToDo / Disposition Open. Locking has code-wide implications even though
symptoms appear only under concurrent execution. Register it in this file and
retract its P25 claim (L5).

### D4. Create `METHOD.md`; `CPU_MEASUREMENT.md` becomes a section of it

Kanban ToDo / Disposition Open.

`CPU_MEASUREMENT.md` resolves a specific contradiction: CPU figures in this
work have ranged between near-0 and 208% because four different quantities
were reported as one -- process CPU rate, `ps %cpu` (a decaying average),
bucket share of sampled stacks, and wall-clock share of a phase. A 48-55%
proof-verification bucket share and a 100% process rate are both correct and
not comparable: the first is a share of CPU spent, the second a share of one
core. Reporting them side by side implies half the machine is idle when one
core is saturated and thirteen are unused.

This is measurement methodology, so it belongs with the rest of it rather than
standing alone. Reconciling it against earlier utilization assessments is C2's
work, tracked in group E.

### D5. Create `OPERATIONS.md` for queue, RPC and REST sizing

Kanban ToDo / Disposition Open. Operational tuning of a Zcash-lineage node, not
a performance finding. Receives Q1 and Q2.

### D6. Unify `Perf.md` section titles and numbering

Kanban ToDo / Disposition Open.

One numbered 0.x heading survives (`0.16`); S0 otherwise carries seventeen
unnumbered subsections. Citations to S0.11, S0.13, S0.14 and S0.15 point at
headings that no longer exist. S6 has no heading at all -- S6 and S6.1 moved to
`PerfGroth.md` and S6.2 was left behind, still citing S6.1 and a S9.4 that does
not exist. Renumber and repair together; splitting them would mean touching the
same lines twice.

### D7. Retirement ledger

Kanban ToDo / Disposition Open. Running record of every document, section and
area retired, updated as D1-D6 land. Without it, consolidation loses track of
what was folded where and readers keep chasing dead paths.

### D8. Prune cross-references

Kanban ToDo / Disposition Open. Do last: references churn while D1-D6 move
content. Keep only those strictly necessary and still valid.

### D9. Extend `check_citations.py` to intra-document references

Kanban ToDo / Disposition Open. It reports clean while `this file, P5`, `S0.14`
and `P25` are all broken, because it does not check references whose target is
in the same file or in a sibling doc. Pairs with D8: the prune is once, the
check is forever.

---

## Group L -- Locking

Area: `src/sync.{h,cpp}`, `src/main.cpp`. Doc: `LOCKS.md`.

### L1. Locking validation methodology

Kanban ToDo / Disposition Open. Lands in `METHOD.md` (D4).

What a locking change must pass before it counts as measured:

| Concern | Instrument | Pass condition |
|---------|-----------|----------------|
| Lock-order inversion | `DEBUG_LOCKORDER` build, full tiny reindex | 0 `POTENTIAL DEADLOCK` |
| Balance | same run | 0 `LeaveCritical` underflows |
| Data race | TSAN build, targeted workload | no new reports vs baseline |
| Contention cost | instrumented `sync.cpp`, acquisition counts + ns/acquire | recorded, compared to baseline |
| Throughput | paired A/B, n>=3, same height window | `|t|` above the noise bar (~2.5) or reported as null |

The existing baseline is a full tiny reindex (187,418 blocks) under
`DEBUG_LOCKORDER`: 2,901,309 recursive acquisitions (~15.5/block), 0
underflows, 0 deadlock detections, 9 distinct recursive sites, 4.55 ns per
re-acquire, 0.013 s total (0.007% of wall). Reference material for further
review: `test-logs/lockattr-20260913/`, `test-logs/lockstats-20260912/`.

### L2. Re-run the L1 suite after each locking change

Kanban ToDo / Disposition Open. Gate for L3 and L4.

### L3. P21 `IsInitialBlockDownload` acquires `cs_main` 4x per block

Kanban InTest / Disposition Open.

Fixed. Hoist, not split. Measure.

`fImporting` and `fReindex` are plain bools set once during init and read
without `cs_main` elsewhere in `main.cpp`; the answer they give does not depend
on chain state, so the test moves above the lock and returns early during
exactly the phase when the latch has not tripped. This removes all four
acquisitions per block with no call-site changes and no new API -- the
alternative on record was splitting into locked and unlocked variants and
classifying 19 call sites.

Outstanding: the 4.00/block and 44%-of-recursion figures are pre-fix. Re-run
L1 and record the post-fix counts before this moves to Done.

### L4. Recursive `LOCK`s at nine sites

Kanban ToDo / Disposition **Aside**.

Previously Postponed on the measurement: all recursion costs 0.007% of wall,
so there is no throughput case. Re-opened as Aside because the planned locking
work (L1-L3) changes the calculus -- four of the nine sites re-lock at their
own source line with integer-exact per-block counts, the signature of
defensive `LOCK`s in functions already called under the lock. Decide as part
of L1, not separately: if the validation suite is being run anyway, the
marginal cost of correcting these is small even though the performance gain is
not the reason to do it.

### L5. Update `LOCKS.md`

Kanban ToDo / Disposition Open. Retract the P25 tracking claim -- that id was
never allocated -- and point it at this register. Add the L1 reference
materials.

---

## Group M -- Messaging, logging and alerting

Area: all of `src/`. No existing document owns this subject.

**Measured scope, 2026-09-21** (M1, `log_inventory.py`). 1,388 call sites
outside vendored trees: 590 gated, 798 always-on, 31 categories. **Most
logging in this node is ungated**, and a third of the always-on sites are
`error()` calls that also carry control flow. That shape, not any single site,
is what M2 acts on.

### M1. Inventory every message

Kanban Done / Disposition Done. `log_inventory.py`;
`test-logs/loginv-20260921/messages.tsv`.

Scripted sweep producing a TSV: file, line, construct, category,
gated-or-always, enclosing function, message text. Levels in this codebase are
implicit -- `LogPrintf` versus `LogPrint(category)` versus `error()` -- so the
inventory records which construct is used rather than a nominal severity.
Re-runnable; `--summary` prints counts without the TSV.

**1,388 call sites: 590 gated, 798 always-on, 31 categories.**

| Construct | Sites | Emits |
|-----------|------:|-------|
| `LogPrint` | 590 | only with its `-debug` category enabled |
| `LogPrintf` | 532 | always |
| `error` | 260 | always, and returns a failure code |
| `LogPrintStr` | 6 | always |

`error()` is the class a plain `LogPrint` grep misses: it both logs and
returns false, so it carries control flow as well as a message. 172 of
`main.cpp`'s 241 always-on sites are `error()`.

Concentration: `zeronode` is 229 of 590 gated sites, and the next category
(`net`) has 39. Always-on sites concentrate in `main.cpp` 241, `init.cpp` 116,
`wallet/wallet.cpp` 51, `net.cpp` 41, `netbase.cpp` 35.

### M2. Review level and area assignment

Kanban ToDo / Disposition Open. Absorbs P16. Input: M1's TSV.

Two failure directions, both present: messages emitted always that should be
gated (log volume during reindex), and messages gated behind a category no
operator would enable that should be visible.

Review order, by what the inventory shows:

1. **`error()` sites, 260.** Each logs and returns a failure. The question per
   site is whether the caller already reports the failure -- if so the log line
   is duplicate volume, if not it is the only record. Start with `main.cpp`'s
   172.
2. **`zeronode`, 229 of 590 gated sites.** One category covering 39% of all
   gated logging cannot be selective; enabling it is all-or-nothing. Candidate
   for splitting into sub-categories.
3. **`init.cpp`, 116 always-on.** Startup is a bounded phase, so volume matters
   less; check instead for messages that should survive into a quieter default.
4. **Always-on in per-block paths.** `main.cpp` and `wallet/wallet.cpp` sites
   reached during reindex are the volume risk; the inventory's `func` column
   locates them.

### M3. Work-queue rejection is invisible to clients

Kanban ToDo / Disposition Open.

libevent's HTTP layer rejects the request before it reaches Zero's JSON-RPC
dispatch and returns HTTP 500 with a non-JSON body; `zero-cli` sees a completed
connection and exits 0. The `LogPrintf` warning is always-on and reaches
`debug.log` on every occurrence, but nothing reaches the caller. Measured: 7
rejections at queue depth 4 under a load a full-tip node should serve
trivially, with zero client-visible errors.

Fix: return a JSON-RPC error object so clients can retry. This is the concrete
instance of the M2 class -- a condition the operator must act on, logged where
only a log reader will find it.

### M4. Alerting criteria

Kanban ToDo / Disposition **Blocked** on M2. Which conditions an operator must
see, and through which channel. Without stated criteria, M2's
"important-but-invisible" half has nothing to judge against.

---

## Group Q -- Queue and thread sizing

Area: `src/httpserver.{h,cpp}`, `src/checkqueue.h`, `src/init.cpp`.
Doc: `OPERATIONS.md` (D5).

### Q1. Document RPC queue depth and thread count

Kanban ToDo / Disposition Open.

The load-bearing distinction: `-rpcthreads` sets how many requests are served
concurrently, `-rpcworkqueue` how many may wait. Conflating them caused a
real regression -- the queue was lowered 16 to 4 on the argument that
`getalldata` serialises itself behind an in-flight gate, which correctly
justifies not adding threads and does not justify shrinking the buffer that
absorbs bursts. Depth reverted to 16; threads stay at 4, which the measurement
does not contradict.

Document both knobs with their measured effect and the usability consequence
(M3: a short queue rejects work silently).

### Q2. Script-check pool sizing

Kanban ToDo / Disposition Open. Absorbs P20.

`-par=0` spawns `nScriptCheckThreads - 1` workers; the calling thread
participates via `CCheckQueueControl(fMaster=true)`, so counting spawned
threads understates the pool by one. At 1 CPU zero workers are created and
running inline is correct; at 2 and 4 the formula matches core count. The open
question is only the large-host case: 13 workers measured idle throughout a
post-Sapling import (105,261 stack samples, all in `__psynch_cvwait`), against
a `max_concurrent` high-water mark of 14 that cannot distinguish "saturated"
from "briefly touched once". Evidence: `SCRIPTQUEUE.md`, folding into
`CONCURRENCY.md` via D2.

---

## Group R -- `getchaintips` cost

Area: `src/rpc/blockchain.cpp:1101`.

Measured 8.012 s against ~0.23 s for every other RPC tested, on a 2,518,018
block index returning 214 tips. The ~0.23 s floor is `zero-cli` process spawn,
not server time.

### R1. Separate the costs before fixing either

Kanban ToDo / Disposition Open. Prerequisite for R2 and R3.

**There is no replicated sort, and no sort call at all.** The code builds
`std::set<const CBlockIndex*, CompareBlocksByHeight>`, which maintains order
incrementally: the comparator runs on every insert and every erase, and
iteration at the end is already in order. So the candidate costs are:

| Cost | Work | Fix if dominant |
|------|------|-----------------|
| Insert | 2.5M inserts, ~54M comparator calls, 2.5M red-black node allocations | unordered container |
| Erase | 2.5M erase-by-key, each re-descending the tree | mark instead of erase |
| Ordering | maintained continuously by the comparator, needed only for 214 survivors | do not order until the end |

The comparator itself is cheap -- an `int` compare with a pointer tiebreak --
so the cost is tree churn and cache misses across 2.5M nodes, not comparison
arithmetic. That distinguishes this from the startup path, where the
comparator did dominate.

Measure insert and erase separately (wall time per phase, allocation counts)
before choosing. The three fixes are independent and should be evaluated
independently.

### R2. Do not materialize the full set

Kanban ToDo / Disposition Open. Depends on R1.

A block is a tip iff no block names it as `pprev`. That is answerable without
ever holding a set of all blocks: one pass collecting `pprev` pointers into an
`unordered_set`, a second emitting blocks absent from it. Peak memory is the
parent set rather than the full block set, neither pass orders anything, and
the ~214 survivors are sorted once at the end where ordering is cheap.

This may make R3 unnecessary; evaluate it first.

### R3. Unordered container for the existing shape

Kanban ToDo / Disposition Open. Fallback if R2 is rejected.

`std::unordered_set<const CBlockIndex*>` removes the comparisons and the tree;
sort the survivors at the end. The set is an implementation detail and output
order is imposed afterwards, so the result is unchanged: the same 214 tips in
the same order.

Not urgent -- `getchaintips` is a diagnostic and the cost is visible only on a
full-tip node. Recorded so the shape is known before anyone puts it behind a
monitoring poll.

---

## Group B -- Witness bottleneck

Area: `src/wallet/wallet.cpp`. Doc: `Perf.md` S0, moving to `FINDINGS.md`.

Two bottlenecks, one behind the other. The first is fixed and shipped opt-in;
the second is what remains.

**First: Verify walks all of `mapWallet`.** `VerifyAndSetInitialWitness`
iterated every wallet transaction per block though 1,403 of 801,619 (0.175%)
bear notes. Addressed by NOTEIDX (`-walletwitnessnote=1`), ~33x measured.

**Second: `EnsureNoteTxIndex` rebuilds on a flag that is set too broadly.**
The index rebuild is O(`mapWallet`) and runs whenever `fNoteTxIndexStale` is
set -- which every `AddToWallet` and `EraseFromWallet` does, including
transparent transactions and no-op merges. On the fat wallet, founders
coinbases arrive every block after height 1,600,000, so the flag is set per
block and the rebuild runs per block: `SelectWalletTxsForWitnessScan` at ~98%
CPU, ~19 blk/s.

### B1. Narrow the invalidation (P2 / FIX-WAL-WITNESS-NOTEIDX-STALE)

Kanban ToDo / Disposition Open. Largest measured win available.

Membership rule: a txid belongs to `vNoteTxHashes` iff `mapSproutNoteData` or
`mapSaplingNoteData` is nonempty. Membership changes only when a note-bearing
tx is inserted, a note-bearing tx is erased, or an existing tx goes empty to
nonempty via `UpdatedNoteData`. It does not change for transparent
insert/update/erase or for a merkle merge on an existing entry.

Implementation, from the specification at `Perf.md` L85-194 (which B2 reviews
before this lands):

- helper `HasNoteData(const CWalletTx&)`, true iff either note map is nonempty
- `AddToWallet` load path: invalidate iff `HasNoteData(wtxIn)`
- `AddToWallet` live path: compute `hadNotes` before the merge, `hasNotes`
  after; invalidate iff `fInsertedNew ? hasNotes : (hadNotes != hasNotes)`
- `EraseFromWallet`: capture `HasNoteData` before the erase; invalidate iff true
- do not invalidate at the top of `AddToWallet`

The founders coinbases driving the per-block rebuild have empty note maps, so
not invalidating on transparent Add/Erase removes the rebuild entirely rather
than shrinking it.

### B2. Review `Perf.md` L85-194 for redundancy and stale content

Kanban ToDo / Disposition Open. Do with B1; feeds D1.

The section states the same membership rule in a prose paragraph, a lifecycle
table and a proposed-rule block. Reduce to one statement plus the call-site
rules, and verify the defect description still matches the code before it is
relocated into `FINDINGS.md`.

### B3. Benchmark plan for both bottlenecks

Kanban ToDo / Disposition **Blocked** on B1 and V4.

Needs a post-Sapling tip with notes in range: the tiny (187,417) and short
(245,992) tips are both pre-Sapling (activation 492,850), so the fat golden
wallet's height walk is skipped entirely on them and neither can exercise this.

### B4. Remeasure `-rescan`; validate the 11.9 h figure

Kanban ToDo / Disposition **Blocked** on B1.

Re-running before B1 lands would reproduce ~11.9 h and establish nothing: the
changes since are P23 (startup index load, a different phase) and the lock
fixes (0.007% of wall). Schedule after B1 as a standalone script writing
results outside the harness, launched overnight.

---

## Group P -- Product handoff

Node code owned by Zero400, tracked here because the evidence is here. Ids
preserved from TASKS.md.

**Dependency:** P5 before P6; P6 subsumes what remains of P4. P1, P2 and P5 are
independent.

| Id | Item | Kanban | Disp | Note |
|----|------|--------|------|------|
| P1 | Proof-verification counters | InTest | Open | Approach chosen, prototype builds both configs, not landed. Blocks any phase summary: proof verification sits in no timer, so a summary built today omits 88-91% of post-Sapling cost while appearing complete |
| P4 | Witness RPC gate inconsistent | InTest | Open | Steps 1-2 landed; remainder subsumed by P6 |
| P5 | `boost::optional` -> `std::optional` | ToDo | Open | Gates P6; not started |
| P6 | Anchor depth for shielded spends | ToDo | Blocked on P5 | |
| P7 | Coin-selection call clarity | ToDo | Open | Locate existing coverage in repo and ZK documents before writing new analysis; may already be documented |
| P8 | FDCACHE disposition | ToDo | Postponed | Compiled out of release builds; retained pending Linux/Windows validation |
| P9 | Note locking / single-worker | ToDo | Open | **Needs a decision.** `z_sendmany` never locks the notes it selects; safety rests entirely on the async RPC queue running one worker. Correctness stakes, not performance |
| P10 | Explicit parameters at defaulted calls | ToDo | Open | |
| P13 | `CheckBlock` runs 3x per block | ToDo | Open | Measured, not inferred |
| P17 | Out-of-order child on reindex | ToDo | Open | |
| P18 | `ShrinkDebugFile` keeps the tail | ToDo | Open | Wrong half; pairs with M2 |
| P19 | Delete unbuilt `src/snark/` | ToDo | Open | Partly done -- last commit removed ~7,500 lines |

Merged: P16 into M2, P20 into Q2, P21 into L3, P22 into E5, P24 into group R,
P14 into L4. Done: P11, P12, P15, P23. Never allocated: P3, P25.

---

## Group E -- Measurement backlog

### E1. A3 microbenchmark baseline

Kanban InTest / Disposition Open. 4 of 17 run; several of the remainder need a
populated wallet. Worth more the longer GROTH stays postponed -- a batching
result needs a per-proof baseline taken beforehand, not after.

### E2. D2 `Xc.reserve()`

Kanban **Ready** / Disposition Open. One line at `equihash.cpp:384`, harness
and paired method already exist, ~30 min. Cheapest real measurement available.

### E3. C2 remaining measurement gaps

Kanban ToDo / Disposition Open. Includes reconciling `CPU_MEASUREMENT.md`
against earlier utilization assessments (see D4).

### E4. R1 non-blake2b hash-library surface

Kanban ToDo / Disposition Open. Owner: `HASHLIBS.md` S1.5A.

No new run: re-bucket archived M-CPU-SEQ captures by adding `crypto_sign_*`,
`crypto_aead_*` and `crypto_scalarmult*` buckets to `classify()` in
`bucket_profile2.py`.

### E5. P22 threaded tromp solver

Kanban ToDo / Disposition Open. Absorbs `INV-ARM-MIX` (X4).

Never measured. Document the procedure and add it to the profile corpus so it
is repeatable rather than a one-off. Memory coupling (~3.3 GB per instance) is
the stated real constraint, and the deployment fleet mix gates whether ARM
vector work is worth scheduling at all.

---

## Group T -- Tooling and methodology

### T1. Document `validate.sh`

Kanban ToDo / Disposition Open. Lands in `METHOD.md`.

Stages (`lint`, `selftest`), the 21 checks, and the owned-versus-inherited
scope rule -- the report prints OWNED and TOTAL columns and passes when owned
scope is clean, with inherited upstream findings set aside deliberately. That
distinction is the part a newcomer misreads. Also record the three checks
currently set aside (include guards, include ordering, locale dependence) and
why. Receives the new rules from W1 and X5.

### T2. Catalog the scripts

Kanban ToDo / Disposition Open.

About 40 scripts in `contrib/perf/` with no index: purpose, inputs, outputs,
and when to reach for each. Currently the only way to find the right one is to
read them. Pairs with T1 -- both exist so the lab is usable by someone who did
not build it.

New this cycle, to include: `log_inventory.py` (M1, message inventory TSV,
`--summary` for counts).

### T3. T0 test suite

Kanban ToDo / Disposition Open.

`COINBASE_MATURITY=720` against Bitcoin's 100, so ported tests assume short
maturity. 64 tests call `initialize_chain_clean` against 3 using the cached
`initialize_chain` -- that ratio is the suite's runtime problem. 16 of 39
known-broken tests now pass; promote only after a stability check. 23 failures
remain, grouped by mode.

---

## Group V -- Cross-platform validation

### T4. A bare `zero-gtest` run aborts and reports nothing

Kanban ToDo / Disposition Open. Size XS.

`WalletTests.CachedWitnessesCleanIndex` is held failing by design and excluded
in `qa/zcash/test_filters.sh`. Run bare, it aborts the binary at
`wallet.cpp:2594` before any summary prints, so the operator sees a hard crash
and no pass count -- and the natural reading is a regression in witness code.

Two cheap fixes, either sufficient: have the test skip itself with
`GTEST_SKIP()` and a pointer to the filter script when its harness
prerequisites are absent, or document the filtered invocation at the point
where a reader would reach for the bare one (`METHOD.md`, T1).

Second-order: the held test is real, unfixed upstream behaviour in witness
cache decrementing. It is a product question, not a lab one, and is already
noted in `PRODUCT.md:223`.

### V1. Linux VPS and Windows/WSL runbook

Kanban ToDo / Disposition Open. Was B2.

Configuration, build, run and collection instructions for non-macOS hosts.
Every measurement in this tree is macOS/arm64 on one host: relative CPU shares
should transfer, absolute throughput and anything touching disk should not be
assumed to. The runbook is the prerequisite for saying anything else.

Must cover: build prerequisites and depends handling per platform; the lab
datadir and conf (including that snapshot chainstate requires
`experimentalfeatures=1` and `insightexplorer=1` or the node reindexes from
genesis); which harness scripts are portable and which are macOS-only
(`xctrace`, `sample`, `vmmap` are all Darwin); the `psutil` port that B2 step
(d) was blocked on; and where results land so they are poolable.

### V2. First non-macOS capture

Kanban ToDo / Disposition **Blocked** on V1 and a host. Would move A1, A2, F1
and C1 out of InTest together, since a clean-checkout run exercises all four.

### V3. Re-validate the consolidated implementation

Kanban ToDo / Disposition **Blocked** on V2 and D1-D9. Phase 4: confirm the
reorganized documentation and tooling work for someone starting from a clean
checkout on another platform.

### V4. Disposable full tip above height 492,850 with fat notes in range

Kanban ToDo / Disposition Open. Blocking input for B3. Not required for the
opt-in ship; recommended before default-on.

---

## Outstanding decisions

| # | Decision | Why it is yours |
|---|----------|-----------------|
| 1 | **P9** shielded-note locking | Accept the single-worker invariant and document it as a constraint, or add explicit locking. Correctness stakes; the current safety property is undocumented and would break if the queue ever ran two workers |
| 2 | **GROTH** | Still 48-60% of post-Sapling CPU with nothing aimed at it. Two flat results (fd-cache, Merkle latch) demonstrate the smaller buckets do not move the total |
| 3 | **W2 build authorization** | Blocks W3 and therefore the commit |
| 4 | **X3** retire A-F and T/R letters | Recommended; affects every migrated id |
| 5 | **L4** nine recursive lock sites | Aside pending your call: no throughput case (0.007%), but the locking work is happening anyway |

---

## Note on partitioning

Ten groups, by code area and subject: W and X are process, D documentation,
L/M/Q/R/B/P/E/T/V the technical subjects. Every group maps to files a change
would touch -- L to `sync.cpp` and `main.cpp`, Q to `httpserver` and
`checkqueue`, R to one RPC function, B to `wallet.cpp`. Items that shared an
area were combined rather than listed twice: P20 into Q2, P16 into M2, P21 into
L3, P22 into E5, P24 into group R, P14 into L4.

New findings go to the owning subject document and get at most a one-line item
here. A finding that needs a new document needs a retirement to pay for it
(D7).
