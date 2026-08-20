# PerfDoc - ZeroPerf governance and context

**Scope, after the 2026-08 split.** This file holds what is *policy*: who owns
which document, how lab runs must be bounded, what is out of scope, and the
documentation conventions. Operational how-to moved out:

| Looking for | Read |
|-------------|------|
| How to run and read a measurement | `BENCHMARKING.md` |
| Groth16 evidence, decision, plan | `PerfGroth.md` |
| Task list and state | `PerfTasks.md` |
| What to work on next, and why not the rest | `PerfNext.md` |
| Phase-timer design and spec | `PerfTimers.md` |
| Cross-platform tooling survey | `PerfPlatforms.md` |
| Measurement-store schema and aggregation keys | `PerfStores.md` |
| Which document to read, and which to retire | `PerfDocReview.md` |
| Findings and method | `Perf.md` |
| Numbers bound to `M-*` | `Measures.md` |

Sections 6-11 below (build flags, witness baselines, logging facilities, test
types, lint, harness inventory) are **operational reference that duplicates
`BENCHMARKING.md` Part 4**. They are retained for now because other documents
link to them by section number; the reintegration plan is at the end of this
file.

Zero400 owns the authoritative code, tests, and project documents. ZeroPerf owns
`contrib/perf/` -- which holds both the harness and the four perf documents
(**Perf.md**, **Measures.md**, **Stores.md**, **PerfDoc.md**) -- plus a gated
source layer. Nothing perf-specific remains at the repo root.

This file holds the perf-relevant material that previously lived only in
ZeroPerf's copies of Zero400-owned documents (**UpdateZero.md**, **AGENTS.md**,
**ZeroStruct.md**, **TEST_ZERO.md**, **TODO.md**, **AtHeight.md**,
**WitnessReindex.md**, **ExtTests.md**), so those copies can be replaced with
Zero400's versions without losing anything.

**Not repeated here.** Every technical topic those copies mentioned -- `§0.14` /
`§0.16`, NOTEIDX, `fBuildingWitnessCache`, PIR-03 / TST-08, W5/W6,
`WAL-RPC-ACCOUNTS`, `zcbenchmark` -- is already covered in **Perf.md** or
**Measures.md**. What follows is only what those documents did *not* carry.

---

## 1. Document ownership and routing

Where perf work is written down, and what each file is for.

| Document | Owner | Purpose |
|----------|-------|---------|
| **contrib/perf/Perf.md** | ZeroPerf | ConnectBlock / sync optimization narrative. CPU buckets; Groth **G**; **P1-P4**; Stages 0-6; **L0-L7**; lab materials; §0.13 BENCH/FIX/IMP. Cites Measures.md for numbers. |
| **contrib/perf/Measures.md** | ZeroPerf | Quantitative measures inventory. Vocabulary; **`M-*`** campaigns; comparability; extraction schema; §8 ledger `CAMPAIGN=` map. |
| **contrib/perf/Stores.md** | ZeroPerf | Storage / datadir structure notes. |
| **contrib/perf/PerfDoc.md** | ZeroPerf | This file. Perf context extracted from Zero400-owned docs. |
| **contrib/perf/BENCHMARKING.md** | ZeroPerf | **How to benchmark and profile.** Workflow, reading the three views, traps that produced wrong numbers. Start here. |
| **contrib/perf/PerfGroth.md** | ZeroPerf | Groth16: evidence, the blocking Option A/B decision, implementation path. |
| **contrib/perf/PerfTasks.md** | ZeroPerf | Every tracked item with state and blocker. |
| **contrib/perf/PerfNext.md** | ZeroPerf | Next directions: which measurement gaps, automation and documentation work are worth doing, ranked, and which are deliberately not. Written while GROTH-DECIDE is postponed; every item is independent of that decision. |
| **contrib/perf/PerfTimers.md** | ZeroPerf | Design and spec for block-processing phase timers. Records three defects in the inherited `-debug=bench` instrumentation, the most significant being that proof verification is timed by nothing. Spec only -- no code changes. |
| **contrib/perf/PerfPlatforms.md** | ZeroPerf | Tooling survey: macOS dependencies of the harness, Ubuntu / Windows 11 / WSL2 equivalents, and existing OSS tools worth adopting rather than rewriting. |
| **contrib/perf/PerfStores.md** | ZeroPerf | Measurement-store schema: platform identity, binary versioning, feature-set encoding, and the fingerprint/aggregation rules that make a multi-platform body of measures searchable. Spec only. Distinct from `Stores.md` (chain/datadir storage). |
| **contrib/perf/PerfDocReview.md** | ZeroPerf | Per-document goal, audience, inclusion criteria and critique for every file in `contrib/perf/`. Identifies duplication, obsolescence and off-subject material; proposed relocations need confirmation. |
| **contrib/perf/PERF_RESTRUCTURE.md** | ZeroPerf | Proposal to restructure Perf.md. Not applied. |
| **test-logs/DATA_INDEX.md** | ZeroPerf | Every number produced, with the log or ledger it came from. |
| **AtHeight.md** | **Zero400** | Height-bounded reindex / short-snap lab procedure. Tiny/short archive unpack, timed reindex, resume interrupt lab. Points numbers to Measures.md. |
| **ZeroStruct.md** | **Zero400** | Architecture: structures, indexes, algorithms (esp. §4.3, §6.2, §13). Problem/pro-con only, not task status. |
| **TODO.md** | **Zero400** | Status and full task text for `OPS-*` / `WAL-*` / `FR-*` / `EXT-*`. |
| **TEST_ZERO.md** | **Zero400** | Validation runbook and tier inventory. |

**Routing by identifier** -- which document owns which prefix:

| Identifier | Goes in |
|------------|---------|
| **`M-*`** (measure ids, campaign numbers) | **Measures.md** (vocabulary, comparability, extraction, ledger §8) |
| **`PERF-*`** (ConnectBlock optimization narrative) | **Perf.md** (next experiments; cite Measures.md for numbers) |
| **`OPS-*`** / **`WAL-*`** / **`FR-*`** / **`EXT-*`** (status + task text) | **TODO.md** (Zero400) |
| **`OPS-*`** / **`WAL-*`** / **`FR-*`** (architecture) | **ZeroStruct.md** (Zero400) |
| **`OPS-AT-HEIGHT`** | **AtHeight.md** procedure; status in TODO.md |
| **`INT-*`** | **ZeroStruct.md** §11.7 (Zero400) |

Numbers live in **Measures.md** under an `M-*` id. Perf.md and this file cite
that id rather than restating the figure -- a number with no `M-*` binding is
not yet a measure.

---

## 2. Lab and long-run discipline

Constraints on how perf trials are run. These bound the harness in
`contrib/perf/` and are why campaigns are append-only and restartable.

- **No unrestartable long batches.** Do not start a batch of trials where each
  trial is expected to take **more than 20 minutes**, unless each trial can be
  **restarted individually**: separate invocation, separate scratch/out dir,
  append-only ledger, no all-or-nothing runs.
- **One trial per invocation.** A campaign is a sequence of independently
  resumable invocations, not one long process.
- **Scratch is disposable; goldens are read-only.** Copy or softlink lab inputs
  into scratch; never mutate an original. See Perf.md "Lab materials".
- **Effort in bands, not calendar time.** Do not invent or refine day/week
  estimates without measured evidence. Prefer **S/M/L** or named work packages.

---

## 3. Out-of-scope for this tree

**Dev fee / founders addresses are project-internal.** Founders and DevFee payee
addresses, and address-ops scripts, stay out of this tree. Do **not** put
DevWallet handling, scripting, or host paths in ZeroStruct, TEST_ZERO, TODO,
AtHeight, Measures, Perf, or any other product document.

Perf work that touches fat-wallet behavior uses the out-of-tree `DevFeeWallets`
material by reference only (see Perf.md "Lab materials"), never by copying
addresses or host paths into a tracked document.

---

## 4. Documentation conventions

Applies to the ZeroPerf-owned documents (Perf.md, Measures.md, Stores.md, this
file). Zero400's AGENTS.md is authoritative; repeated here because these are the
rules perf documents most often break.

- **Typography:** no emojis or decorative Unicode in any document except
  `README.md`. Use ASCII: `--` not em-dash, `->` not arrow, `"` not curly
  quotes, `...` not ellipsis.
- **Headings:** no parenthetical asides in `#`-`######` titles. Put the aside on
  the first line under the heading. Bad: `### 0.8 Signals (updated)`. Good:
  `### 0.8 Signals` followed by a sentence.
- **History:** do not accumulate dated incremental-fix narrative ("fixed X on
  DATE, then Y, then Z"). Prefer the settled current state. Keep
  path-dependent rationale only when the decision still depends on what was
  tried and rejected.
- **Claims:** specific and actionable, with scope and bounds. No superlatives
  without evidence.

---

## 5. Perf-relevant pointers into Zero400 documents

Context a perf reader needs, owned and maintained by Zero400. Read the Zero400
copy; do not fork these into ZeroPerf.

| Topic | Zero400 document | Why perf cares |
|-------|------------------|----------------|
| Height-bounded reindex / short-snap procedure | **AtHeight.md** | The tiny/short lab procedure behind `M-RX-TINY` / `M-RX-SHORT`; numbers land in Measures.md |
| Witness rebuild across `-reindex` | **WitnessReindex.md** | Scope of `BuildWitnessCache` / note witnesses; `qa/rpc-tests/reindex_shielded.py` is the Tier B gate |
| Wallet / RPC architecture | **ZeroStruct.md** §4.3, §6.2, §13 | Structures behind the witness and `wtxOrdered` work; problem/pro-con, not status |
| Tier inventory and runbook | **TEST_ZERO.md** | Which suites gate a change; the Tier A/B pass lists |
| Equihash test surface | **ExtTests.md** | `equihash_tests` coverage; KATs now at `src/test/data/`. Python Equihash in `qa/` is not authoritative and not performant -- C++ `CheckEquihashSolution` / `zcbenchmark` is |
| Task status | **TODO.md** | `FIX-*` / `IMP-*` scheduling that Perf.md §0.13 references |

---

## 6. Building with instrumentation -- policy

Commands are in `BENCHMARKING.md` 4.2. What belongs here is the reasoning:

**One flag, not two.** `--enable-perf` defines **both** `ZERO_PERF` (root-latch
counters) and `ZERO_FDCACHE` (block-file read latch). They are separable in
principle but are one lab feature with one audience; two flags would double an
already-untested build matrix. Split only if a reason appears.

**Default off**, so a stock build is byte-identical to Zero400's.

**Why the flag exists at all.** Before it, neither gate appeared in
`configure.ac`, any Makefile, or `bitcoin-config.h` -- the code was unreachable
from any normal build and had likely never been compiled. That is how
`-perffdcache` came to bind the wrong `GetArg` overload (`atoi64("")` is 0, so
a bare flag read as false) and go unnoticed. **Gated code that cannot be built
cannot be tested**; any future gate needs a configure path on day one.

**Editing `configure.ac` arms an autotools trap** -- the next `make` re-runs
`configure` without the depends `CONFIG_SITE` and dies on a misleading
"libdb_cxx headers missing". Pre-existing in both trees. Symptom, cause,
recovery: **[BUILD_RECONFIG.md](BUILD_RECONFIG.md)**; tracked as
`IMP-BUILD-RECONFIG` in `PerfTasks.md`.

## 7. Witness-walk baselines -- scope limits

Usage is in `BENCHMARKING.md` 1.7. Retained here is the constraint a future
editor would otherwise re-learn:

`WalletTests.WitnessReadIsStableAndClearDiscards` operates on **one wallet and
one chain**. `CreateValidBlock` builds notes with random inputs, so two
independently constructed wallets do not share a chain and their witnesses are
not comparable -- an earlier version of this test compared two wallets and
failed for that reason, with the implementation correct and the test wrong. A
cross-wallet differential needs deterministic note construction first.

The test was verified sensitive by mutation: with `ClearNoteWitnessCache`
stubbed to `return;`, it fails at the clear assertion.

## 8. Logging and tracing -- what exists, and the gaps

Invocation is in `BENCHMARKING.md` 4.2/4.3. Retained here: the inventory and
what is missing.

| Layer | State |
|-------|-------|
| `-debug=<category>` | 30 categories; `zeronode` 228 sites, `net` 39, `bench` 11 |
| `-debug=bench` | per-block phase tree with cumulative totals; `extract_measures.py --bench` ingests it |
| `zcbenchmark` RPC | 19 named micro-benchmarks; runner `performance-measurements.sh` |
| `--enable-perf` counters | section 6 |
| Instruments / `sample` | `xctrace`, decoded by `bucket_profile2.py` |

**Gaps** (tracked in `PerfTasks.md` section 6): no tracing inside the witness
walk beyond its begin/done pair; no always-on subsystem timing, so a slow node
in the field yields no evidence; `-debug=bench` and `zcbenchmark` both work and
are used by no campaign, so neither has a recorded baseline.

## 9. Test and campaign types -- the matrix

Commands are in `BENCHMARKING.md` Part 1. Retained here: the dimensions, since
they determine what a capture can and cannot conclude.

**Operations:** reindex, bootstrap, rescan, sync, mine.

**Chain snaps** (tips measured, not assumed):

| Snap | Tip | Region |
|------|----:|--------|
| `tiny` | 187417 | pre-Sapling |
| `short` | 245992 | pre-Sapling |
| `postsap12` | ~583699+ | **post-Sapling, 1.65G** |
| `full` / 812 | ~2518018 | full chain, 8.5G |

Sapling activates at **492850**: only the last two reach it.

**Wallets:** `none` (control), `p0` 106KB, `p1` 237KB, `fat` 749MB / 801619 tx.

**Flags under test:** `noteidx`, `ibd-defer`, the FDCACHE trio.

**Campaign catalog:** `cycle_trials.tsv`, 11 trials in three sets (smoke 6,
gate 4, long 1), resumable via `ops-campaign.sh`.

## 10. Lint automation

`contrib/perf/lint-perf.sh` runs every check in one pass and filters to code
ZeroPerf owns.

```bash
contrib/perf/lint-perf.sh            # gate: exit 1 only on contrib/perf/ findings
contrib/perf/lint-perf.sh --summary  # counts only, one line per check
contrib/perf/lint-perf.sh --all      # no filter, every finding tree-wide
contrib/perf/lint-perf.sh --list     # what runs, then exit
```

It wraps `contrib/perf/check-unicode.py`, `shellcheck`, and the nine vendored
`zcash-lint/lint-*.sh`, printing OWNED and TOTAL counts per check.

**Why filtered.** `zcash-lint/lint-all.sh` exits 1 on roughly 200 findings that
live in code inherited from Bitcoin and Zcash. Those are set aside -- changing
them diverges from upstream for no functional gain -- so an unfiltered gate is
permanently red, and a permanently red gate gets ignored. This one is green when
`contrib/perf/` is clean and still prints the upstream totals for visibility.

**Scope decisions baked in:**

| Decision | Reason |
|----------|--------|
| Gate scope is `^contrib/perf/` | The only code ZeroPerf owns |
| `datadir_guard.sh` excluded | Sourced, mode 644: shebang meaningless, and `LC_ALL` there would override the caller's locale. Two linters flag it; both are false positives |
| Unicode gate covers `*.sh` / `*.py` only | Perf `.md` and captured `.txt` are a separate concern (UpdateZero.md DOC-UNICODE). `--all` still shows them |
| `shellcheck -f gcc` | Emits `path:line:col:`, so one path filter works across every check |

**Default filtering.** Three checks report only inherited upstream findings that
are set aside; their TOTAL is high, constant and uninformative, so it prints as
`set aside` unless `--all` is given: `include-guards` (52), `includes` (186),
`locale-dependence` (71). `--all` and `--summary` compose.

Baseline as of 2026-08-19: **OWNED 0 across all eleven checks**, exit 0.
Verified to fail correctly by introducing an unused loop counter and an
em-dash, and to return to 0 when reverted.

---

## Disposition of sections 6-10, after the 2026-08-20 pass

**Done in this pass:**

- **S11 Harness inventory -- struck.** It listed no tool built in the 2026-08
  work (`profile_run.sh`, `bucket_profile2.py`, `profile_collate.py`,
  `res_sample.sh`, `witness_walk_cost.py`, `check-unicode.py`, `lint-perf.sh`)
  and so was actively misleading. `BENCHMARKING.md` 4.1 is the list, and it is
  verified against the directory.
- **S6-S9 pared to what BENCHMARKING does not carry.** Commands, options and
  invocation moved out; what remains is reasoning, constraints and the
  dimensions of the test matrix -- the parts a future editor would otherwise
  re-derive. 294 lines to about 90.

**Verified current, not stale, during the pass:**

| Claim | Checked against |
|-------|-----------------|
| 30 debug categories | `grep LogPrint` over `src/` -- 30 |
| `--enable-perf` is the flag | `configure.ac` -- present |
| snap tips 187417 / 245992 | measured by reindex to completion |
| 19 zcbenchmark names | `rpcwallet.cpp` dispatch -- 19 |
| lint gate: 11 checks, OWNED 0 | `lint-perf.sh` run |

**Left for later review:**

- **S10 Lint automation** kept in full. Lint policy is governance, not
  measurement, so it belongs here rather than in `BENCHMARKING.md`. Worth a
  later look at whether the set-aside list has changed.
- **S1-S5** (ownership, lab discipline, out-of-scope, conventions, pointers
  into Zero400) untouched -- all policy, none duplicated elsewhere.
- The `postsap12` snap is new; S9 now lists it, but no campaign driver defaults
  to it yet. Worth wiring into `tiny_baseline.sh`-style entry points.
