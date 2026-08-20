# Next directions: measurement, automation, documentation

Where the remaining leverage is, now that **GROTH-DECIDE is postponed pending
developer review** (`PerfTasks.md` S1). Everything here is deliberately
**independent of that decision** -- nothing below becomes wasted work whichever
of Option A or Option B is eventually chosen.

Each item states what is true today, what would change, and how the result gets
checked. Items are grouped by kind, and ranked within each group by
**leverage divided by cost** rather than by appeal.

Conventions: effort in bands (**S/M/L/XL**), never calendar days, per
`PerfDoc.md` S2. A number with no `M-*` binding is not yet a measure.

Companion documents produced alongside this one:

| Document | Holds |
|----------|-------|
| `PerfTimers.md` | Design and spec for the phase-timer work (S2.1, S3.1), including three defects found in the existing timers |
| `PerfPlatforms.md` | Tooling survey: what the harness depends on, and the Ubuntu / Windows 11 / WSL2 equivalents |

---

## 1. Summary: what to do first

| Rank | Item | Kind | Effort | Why it is first |
|-----:|------|------|--------|-----------------|
| 1 | **IMP-BENCH-ALWAYS** | Product + measurement | **S-M** | The timers already run on every block in every node and the results are thrown away. Spec: `PerfTimers.md`. Raised from S after the design pass found proof verification is untimed (S2.1) |
| 2 | **AUT-BENCH-INGEST** | Automation | **S** | `zerod` emits 11 bench phase lines; the parser reads 1. The other 10 need no node change |
| 3 | **AUT-LINT-DOCS** | Automation | **S** | 693 unenforced doc violations against a stated hard rule; checker and fix mode already exist |
| 4 | **FIX-WAL-WITNESS-NOTEIDX-STALE** | Product | **S** | Already-open task; analysis complete, defect localized to two call sites |
| 5 | **AUT-CI-PERF-BRANCH** | Automation | **S** | CI does not fire on pushes to `perf-402`, and runs no lint at all |
| 6 | **BENCH-THERMAL-LONG** | Measurement | **M** | Every published capture is 60s; thermal throttling on multi-hour runs has never been checked |
| 7 | **BENCH-P1-RESCAN** | Measurement | **M** | Fills the documented hole in the wallet-size curve between p1 and fat |
| 8 | **DOC-PERF-RESTRUCTURE** | Documentation | **L** | Real problem, but the trigger condition it names has not yet been met -- see S4.1 |

---

## 2. Measurement gaps worth closing

`PerfTasks.md` S6 lists five coverage gaps. They are not equally worth closing;
the ranking below is the point of this section.

### 2.1 IMP-BENCH-ALWAYS -- always-on phase timing (rank 1)

**The finding that motivates this.** In `ConnectTip`
(`src/main.cpp:3580-3634`) the phase timers are computed **unconditionally**:

```cpp
int64_t nTime2 = GetTimeMicros(); nTimeReadFromDisk += nTime2 - nTime1;
LogPrint("bench", "  - Load block from disk: %.2fms [%.2fs]\n", ...);
```

`GetTimeMicros()` and the `nTime*` accumulator run on every block. Only the
**output** is gated -- `LogPrint` early-outs at
`LogAcceptCategory(category)` (`src/util.h:97`) before `tfm::format` is
reached, so an unselected category costs a category check and nothing else.

The consequence: **every field node already measures where block-processing
time goes, then discards it.** `UpdateTip` (`src/main.cpp:3474`) logs
unconditionally on every block -- hash, height, log2_work, tx count, date,
progress, cache size -- and **no timing at all**. A user reporting a slow node
sends a `debug.log` with height and cache size and nothing about which phase is
slow.

**What would change.** Emit a periodic phase-timing summary from the counters
that already exist -- not per block, which would be noise, but every N blocks
(reuse the `-mrclogevery` pattern, default 16384).

**Scope correction from the design pass.** Specifying this
(`PerfTimers.md`) turned up a defect that changes the item: **proof
verification is inside no bench timer at all.** Sprout JoinSplit verification
runs in `CheckBlock` at `main.cpp:2982`, while the first timer `nTimeStart` is
set at `3049`; Sapling spend/output verification runs in `ContextualCheckBlock`
during block *acceptance*, outside `ConnectTip` entirely. So a summary built
only from existing counters would omit 88-91% of post-Sapling cost while
appearing complete -- worse than no summary. `IMP-BENCH-ALWAYS` therefore
requires **one new measurement point** as well as a new report. Full analysis,
including two further timer defects, is in `PerfTimers.md` S2.

**Why it is rank 1.** It is the only item here that converts an existing
per-block cost from waste into evidence. It also removes the standing need to
reproduce a user's slowness in the lab before it can be diagnosed at all.

**Risks and bounds.**

- **Log volume.** At 16384-block intervals this is a handful of lines per hour
  of IBD -- negligible against what `UpdateTip` already writes per block.
- **Cumulative-vs-delta.** The existing `[%.2fs]` fields are cumulative since
  process start, which is the wrong shape for spotting a region that got slow.
  Report **both** the interval delta and the cumulative total, or the summary
  will hide exactly the regressions it exists to find.
- **Not a profiler.** Six phase buckets will not replace a Time Profiler
  capture. It answers "which phase" so the profile can be aimed, per the
  benchmark-vs-profile split in `BENCHMARKING.md`.
- Consensus-neutral: reads counters, changes no validation behaviour.

**How the result is checked.** Run tiny reindex with and without the flag,
confirm the reported phase totals sum to within rounding of the existing
`- Connect block:` total under `-debug=bench`, and confirm throughput is
unchanged against the recorded same-host repeat pair
(`tiny-20260819T234958Z` / `tiny-20260819T235438Z`, 4% spread).

**Effort S.** Product change; belongs to Zero400 review, not ZeroPerf alone.

### 2.2 BENCH-THERMAL-LONG -- has anything ever throttled? (rank 6)

**Today:** thermal state is exported and recorded, and has been **Nominal in
all four rescan captures** -- but every capture is 60s
(`DATA_INDEX.md` S6). Sixty seconds is far too short to reach a thermal limit
on any modern machine, so "Nominal" is close to a tautology.

This matters because it silently bounds every long-run throughput number in
`ledger.jsonl`. A multi-hour post-Sapling reindex that throttles at hour two is
indistinguishable, in the current data, from one that does not.

**What would change.** During one already-planned long run, sample thermal
state on an interval (`res_sample.sh` already samples on a period and already
has the `debug.log` height fallback for blocked RPC) and record it as a column
alongside height. No new run is needed -- **attach it to a run that was going
to happen anyway**, which is what makes this M rather than L.

**Outcome either way is useful:** if nothing throttles, the long-run numbers
are confirmed comparable and the caveat can be retired from `PerfTasks.md` S6.
If something does, every multi-hour figure needs a thermal column before it can
be compared across trials.

### 2.3 BENCH-P1-RESCAN -- the hole in the wallet-size curve (rank 7)

`BENCHMARKING.md` S2.4 records rescan cost as none/p0/p1 all 0-0.32% and fat
72-99%. That is a **two-order-of-magnitude gap with no measured point inside
it**, so the shape of the curve between them is unknown -- it could be a knee
at some note count, or smooth growth. Which one it is determines whether
NOTEIDX-class work matters for mid-size wallets or only for the golden fat one.

**Caveat that bounds the design.** `BENCHMARKING.md` S1.3 warns a p0 wallet
rescans in **2 ms** -- there is nothing to profile, and a capture taken anyway
records concurrent block connection instead. A p1 capture risks the same
outcome. Establish first, by throughput timing rather than by capture, that p1
rescan takes long enough to profile at all. If it does not, the useful
experiment is a **synthetic wallet series** at increasing note counts, not a
p1 capture.

### 2.4 Deliberately not ranked: post-Sapling bootstrap and sync captures

`PerfTasks.md` S6 lists these as a gap. They are the **lowest-value** item on
that list, and the existing data says why: bootstrap, reindex and sync agree
within ~3 points on every bucket at the same heights
(`BENCHMARKING.md` S1.4), which states outright "do not spend capture budget
re-proving this". They differ in how blocks are *sourced*, not in what
validation costs.

Filling this gap would consume the most lab wall time of any item here to
confirm a result already measured twice. **Recommend leaving open and
unfilled**, with the reason recorded so it is not repeatedly rediscovered as an
obvious gap.

---

## 3. Automation opportunities

### 3.1 AUT-BENCH-INGEST -- parse the other ten bench lines (rank 2)

**Measured today:** `zerod` emits **11 distinct** `LogPrint("bench", ...)`
phase lines (`src/main.cpp:3248, 3260, 3339, 3347, 3512, 3587, 3599, 3603,
3608, 3633, 3634`). `extract_measures.py` has exactly **one** regex,
`BENCH_CONNECT_RE` (line 66), matching only `- Connect block:` -- the
**total**. The ten lines that decompose that total are parsed by nothing.

So `--bench` currently ingests the one number that says least: it reports that
a block took N ms without any of the breakdown that explains why.

**What would change.** Extend the parser to the full set -- connect
transactions, verify txins, index writing, callbacks, load-from-disk, connect
total, flush, chainstate, postconnect, disconnect. Emit each as its own
Measures token so a phase becomes a first-class series.

**Why it is rank 2.** No node change and no new lab run. It is a parser
extension against output the node already produces, and it pairs directly with
IMP-BENCH-ALWAYS: that item makes the lines available in the field, this one
makes them readable.

**Bound.** `-debug=bench` is per block, so a full reindex produces millions of
lines. Aggregate on ingest -- per height band, as the existing throughput rows
already are -- rather than emitting a row per block.

### 3.2 AUT-LINT-DOCS -- enforce the documented ASCII rule (rank 3)

`AGENTS.md` states a hard rule: no emojis or decorative Unicode in any document
except `README.md`. **693 violations are present**, including **498 in
`Perf.md`** -- the most-cited perf document -- and 31 in `Measures.md`.

The rule is unenforced by construction, not by oversight: `lint-perf.sh` gates
its `unicode` check on **code only** (comment at line 65), and a
`unicode-docs` check exists at line 69 but is **not in the default `CHECKS`
list**. So `lint-perf.sh` reports `OWNED SCOPE CLEAN` and exits 0 while the
documents drift.

**Verified safe to fix.** `check-unicode.py --fix` is a whole-file
`str.replace` over 15 mappings with **no code-fence awareness**, so before
recommending it I searched for replaceable characters inside fenced blocks:
**13 lines, none executable** -- Mermaid diagram labels, log-output samples
using an ellipsis as a placeholder, and one JSON example. Substitution there is
harmless. Roughly 630 of the 693 are those safe mappings; the rest are math and
box-drawing glyphs with no mapping, which `--fix` leaves untouched and which
need a per-site judgement.

**Two parts, and the second is the one that lasts:** run `--fix`, then add
`unicode-docs` to the default `CHECKS` so the drift cannot silently resume.

### 3.3 AUT-CI-PERF-BRANCH -- CI does not cover this branch (rank 5)

`.github/workflows/tests.yml` triggers on push to `[main, master, develop]`.
The active branch is **`perf-402`**; none of those three exist as the working
branch here. `pull_request:` still fires for PRs regardless of target, so the
gap is specifically **direct pushes to `perf-402` run no CI at all**.

Separately, **CI runs no lint step** -- not `lint-perf.sh`, not
`check-unicode.py`. Both are fast, hermetic, and need no build, which makes
them the cheapest possible CI additions and a natural home for S3.2's
enforcement.

**Recommend:** add the working branch to the push trigger, and add a lint job
that runs before the 240-minute build so a formatting failure does not wait on
a full compile.

### 3.4 AUT-LEDGER-PROVENANCE -- make back-imported rows self-identifying

`BENCHMARKING.md` S3.1 records a trap already hit: **12 ledger rows share one
`recorded_at`**, seeded from a July TSV, under `run_id`
`historical-postsapling-202607`. They are the largest single campaign in a
35-row ledger (confirmed: `postsapling-historical`, 12 rows).

The guard today is "check `run_id` / `recorded_at`" -- a human convention,
which is exactly what failed the first time. A machine check is cheap:
`accumulate_bench.py` can flag rows sharing a `recorded_at`, or carry an
explicit `imported=true` field, so collation marks them rather than relying on
a reader remembering. **Effort S.**

---

### 3.5 BENCH-ZCB-ARCHIVE -- record the microbenchmark baseline

`Measures.md` records `M-ZCB-SUITE` as having **no checked-in numeric
archive**. The runner exists (`performance-measurements.sh`) and `zcbenchmark`
dispatches **19** named benchmarks (`rpcwallet.cpp:2759-2839`), but only
`connectblockslow` is mentioned anywhere in the measures inventory, and the
mine campaign separately recorded `verifyequihash` / `solveequihash`.

**The two that matter most are unrecorded:** `verifysaplingspend` and
`verifysaplingoutput` measure **per-proof verification cost directly** -- the
exact quantity Groth16 batching is meant to improve. The runner already invokes
them at n=1000 and n=1.

**Why record them now, during the postponement.** A batching result is only
meaningful against a per-proof baseline taken on the same host and binary. If
that baseline is captured after a change lands, it is not a baseline. This is
cheap (microbenchmarks, not multi-hour trials), needs no decision, and is
strictly more valuable the longer GROTH-DECIDE stays open.

**Bound.** These are microbenchmarks over synthetic inputs -- they measure the
verifier, not block validation, and must not be cited as chain-wide shares.
Also useful beyond Groth16: `trydecryptsaplingnotes` and
`incsaplingnotewitnesses` bear directly on the wallet paths in S2.3.

Other stats surfaces reviewed and **not** proposed as work, so the review is not
repeated: `getmempoolinfo`, `getnettotals`, `getpeerinfo`, `getmininginfo` all
exist and are stable, but none bears on sync CPU cost, which is the question
this program is about. `getmemoryinfo` is **absent** from this tree (consistent
with `WAL-LOCKEDPOOL` in Zero400 `TODO.md`). There is **no `src/bench/`**
microbenchmark framework as upstream Bitcoin Core has -- `zcbenchmark` is the
only microbenchmark surface, which is why S3.5 matters.

## 4. Documentation

### 4.1 DOC-PERF-RESTRUCTURE -- do not start yet (rank 8)

`PERF_RESTRUCTURE.md` is a careful, well-evidenced proposal: `Perf.md` is 1871
lines, 73% of it under a single "Status at a glance" heading, with Groth16
discussed in 8 separate places.

**Its own recommendation is to wait:** "Do the split when Groth16 A-vs-B is
decided, not before. That decision will rewrite 0.0/0.1a/0.6a anyway, and
restructuring around a pending decision means doing it twice."

GROTH-DECIDE is now **postponed pending developer review**, which is not the
same as decided. The trigger condition has not been met, so the proposal's own
logic says hold. **Recommend: leave unapplied**, and re-read it when the review
concludes.

One caveat worth recording now, while the reasoning is fresh: a postponement of
unknown length is a weaker argument for waiting than a decision expected soon.
If the review stays open long enough that `Perf.md` keeps accreting status
subsections, the balance shifts and the split becomes worth doing first. The
signal to watch is new `0.x` subsections appearing.

### 4.2 DOC-STATUS-SPLIT -- the part that can be done now

`PERF_RESTRUCTURE.md` proposes a separate `STATUS.md` for the volatile layer,
on the grounds that ~7 status subsections churn every session while the
findings do not.

**This part does not depend on the Groth16 outcome** -- it is about separating
volatile from durable content, which is true regardless of which option wins.
Extracting the status layer would also *reduce* the eventual restructure cost
by removing the churn from the file being restructured.

Recommend as **S-M**, and as the one restructuring step safe to take during the
postponement. The stated risk in the parent proposal still applies: mechanically
diff all `M-*` ids and all "do not" / "keep after" warnings before and after, so
no hard-won caveat is lost in the move.

### 4.3 DOC-GROTH-REVIEW-PACKET -- make the pending review easy to say yes to

GROTH-DECIDE is blocked on a person, so the highest-value documentation work is
whatever shortens that review. `PerfGroth.md` is already complete and now
carries a postponement banner.

What would help a reviewer beyond that is an explicit statement of **what
evidence would change the recommendation** -- the decision is currently
presented as a balanced pro/con with no stated tipping point. Naming the
condition under which each option wins converts an open-ended judgement call
into a checkable question, and S4 question 4 is already most of the way there:
if batching can land behind the existing C ABI, Option A avoids a
release-scale migration entirely.

---

## 6. Documentation reconciliation -- second pass

A reconciliation pass ran on 2026-08-20 and is recorded in `PerfDoc.md`
"Disposition of sections 6-10". This is the follow-up review, and it starts
with the finding that matters most.

### 6.1 Doc growth is itself the risk

The perf document set is **now 12 files and about 2900 lines**, of which
`Perf.md` alone is 1875. This session added three more (`PerfNext.md`,
`PerfTimers.md`, `PerfPlatforms.md`, 839 lines). That is a real cost and it
should be named rather than glossed: **more documents is the failure mode
`PERF_RESTRUCTURE.md` diagnosed**, not the fix for it.

The justification for the three new files is that each has a distinct reader
and none duplicated an existing home: a spec for unbuilt work, a platform
survey, and a ranked what-next. The justification would **not** extend to a
fourth. Recommend a moratorium on new perf documents until
`DOC-STATUS-SPLIT` lands and `Perf.md` shrinks.

### 6.2 Fixed in this pass

| Defect | Evidence | Fix |
|--------|----------|-----|
| `contrib/perf/README.md` had **two competing top-level headings** (`# contrib/perf` and `# perf`) -- a merge artifact | Second `#` at former line 17 | Merged; one top-level heading, second block became a routing table |
| README said `Perf.md` is "at the repo root" | `Perf.md` exists only in `contrib/perf/`; `PerfDoc.md` states nothing perf-specific remains at root | Corrected in place |
| README and `BENCHMARKING.md` S4.1 both document **all 13** tools with no stated division | Measured: 13 of 13 section names appear in both | Division stated explicitly at the top of each: S4.1 is the one-line index, README is the detail |

### 6.3 Measured redundancy, not yet fixed

| Symptom | Measurement |
|---------|-------------|
| Key figures restated across many files | The Groth16 share appears in **5** documents; the NOTEIDX 35x figure in **5** |
| `Perf.md` section 0 is the document | Lines 13-1371 = **72%** of the file before section 1 begins |
| `PerfDoc.md` S6-S10 duplicate `BENCHMARKING.md` Part 4 | Stated by `PerfDoc.md` itself, retained only for incoming section-number links |

The figure restatement is the one worth acting on, and the rule already exists:
`PerfDoc.md` S1 says numbers live in `Measures.md` under an `M-*` id and other
documents cite the id. It is simply not enforced -- much like the ASCII rule in
S3.2, an unenforced convention that drifted.

**Recommend `AUT-LINT-CITATIONS`** (effort **S**): extend `lint-perf.sh` to
flag a bare percentage or millisecond figure in a perf document that is not
accompanied by an `M-*` id. Mechanical, and it targets the actual failure --
a number drifting out of sync with its source across five files.

### 6.4 Deliberately not changed

- **`Perf.md` structure.** `PERF_RESTRUCTURE.md`'s own trigger is not met
  (S4.1). Restructuring during a postponement of unknown length risks doing it
  twice.
- **`PerfDoc.md` S6-S10.** Retained because other documents link by section
  number; removing them breaks inbound links for a cosmetic gain.
- **Root-level documents.** `README.md`, `TODO.md`, `TEST_ZERO.md`,
  `ZeroStruct.md` are **Zero400-owned** (`PerfDoc.md` S1). Restructuring them
  from this tree would contradict the ownership rule and create merge conflicts
  against the tree that owns them. The 693-violation unicode count in S3.2
  includes those files for the same reason -- report, do not unilaterally
  rewrite.

## 7. What is deliberately not proposed

Recorded so these are not repeatedly re-suggested as fresh ideas.

| Not doing | Why |
|-----------|-----|
| Anything downstream of GROTH-DECIDE | Postponed pending developer review; the options diverge at the FFI boundary (`PerfTasks.md` S1) |
| Post-Sapling bootstrap / sync captures | Re-proves a result already measured twice within ~3 points (S2.4) |
| FDCACHE buffer-size sweep | Set aside: the run is serial-CPU-bound, one thread at 100% with disk syscalls under 5%, so an IO knob has nothing to act on |
| NEON blake2b (G7) | blake2b is 3-4% post-Sapling; does not compete with Groth16 |
| `FIX-WIT-WALK-UNLOCK` | Set aside with arithmetic: abort-and-restart cannot converge once walk time exceeds 120s block spacing |
| Applying `PERF_RESTRUCTURE.md` | Its own trigger condition is not met (S4.1) |
