# Document review: contrib/perf

Every document in `contrib/perf/`, with its goal, audience, inclusion criteria
and a critique. Written to find duplication, obsolescence and material that no
longer belongs.

**Nothing is deleted by this document.** `AGENTS.md` requires explicit
confirmation before removing files. Recommendations here are proposals, and the
ones involving removal are collected in S4 so they can be accepted or rejected
as a set.

Method: inbound-reference counts measured across all `.md`/`.py`/`.sh`/`.yml`
in the tree (excluding vendored trees and `test-logs/`); line counts and
overlap measured directly.

---

## 1. Summary table

| Document | Lines | Inbound | Verdict |
|----------|------:|--------:|---------|
| `README.md` | 417 | 14 | **Keep** -- per-tool reference; overlap with BENCHMARKING now declared |
| `Measures.md` | 444 | 11 | **Keep** -- the numbers inventory; the `M-*` authority |
| `Perf.md` | 1875 | 10 | **Keep, restructure later** -- 72% is one section |
| `BENCHMARKING.md` | 342 | 9 | **Keep** -- best document in the set |
| `PerfTasks.md` | 118 | 8 | **Keep** -- the task register |
| `PerfNext.md` | 400 | 6 | **Keep** -- ranked next-directions |
| `PerfDoc.md` | 305 | 6 | **Keep, prune S6-S10** -- self-declared duplication |
| `PerfGroth.md` | 173 | 5 | **Keep, frozen** -- complete, awaiting review |
| `PerfPlatforms.md` | 267 | 4 | **Keep** -- new, multi-platform survey |
| `PerfTimers.md` | 280 | 3 | **Keep** -- new, phase-timer spec |
| `PerfStores.md` | 325 | 0 (new) | **Keep** -- new, store schema spec |
| `BUILD_RECONFIG.md` | 89 | 3 | **Keep** -- bound to open `IMP-BUILD-RECONFIG` |
| `PERF_RESTRUCTURE.md` | 84 | 2 | **Keep until acted on** -- then fold into the result |
| `Stores.md` | 170 | 2 | **Keep, rename later** -- name collides with `PerfStores.md` |
| `Peer.md` | 471 | 2 | **Relocate** -- ops notes, not perf |
| `TENT.md` | 94 | 1 | **Relocate** -- fork lineage, not perf |
| `TENTZero.md` | 29 | 4 | **Relocate** with `TENT.md` |
| `ZcashV.md` | 132 | 0 | **Relocate** -- security notes, not perf |
| `ZeroWallet_Design.md` | 375 | 0 | **Out of scope** -- Qt wallet UI |
| `desys.md` | 100 | 0 | **Out of scope** -- Qt wallet theming |

Twenty documents, 6190 lines. **Five of them (1102 lines, 18%) are not about
node performance at all.**

---

## 2. Per-document detail

### 2.1 Core set -- keep

**`BENCHMARKING.md`** (342 lines, 9 inbound)
*Goal:* teach the measurement workflow. *Audience:* anyone taking a
measurement. *Inclusion:* how to run and read; traps that produced wrong
numbers.
*Critique:* the strongest document here. The benchmark-vs-profile distinction
in the opening is the single most useful paragraph in the set, and S3.1's table
of traps-with-evidence is the right way to record a mistake. Overlap with
`README.md` (all 13 tools in both) is now declared at both ends rather than
silently present. **No change needed.**

**`Measures.md`** (444 lines, 11 inbound)
*Goal:* every number, bound to an `M-*` id. *Audience:* anyone citing a figure.
*Critique:* the load-bearing reference. Two defects: it carries **31 unicode
violations** (`PerfNext.md` S3.2), and `M-ZCB-SUITE` is recorded with **no
checked-in numeric archive** -- a placeholder rather than a measure, tracked as
`BENCH-ZCB-ARCHIVE`. Its authority is undermined by the figure-restatement
problem: the same numbers appear in 5 other documents, so a correction here
does not propagate (`AUT-LINT-CITATIONS`).

**`README.md`** (417 lines, 14 inbound -- most-referenced)
*Goal:* per-tool reference. *Audience:* someone who knows why and needs the
invocation.
*Critique:* had two competing top-level headings and a stale "at the repo root"
claim, both fixed. Remaining concern: at 417 lines it is longer than
`BENCHMARKING.md`, which it tells readers to read first. That inversion is
tolerable for a reference, but if it grows further the per-tool sections should
move to tool `--help` output, which cannot drift from the code.

**`Perf.md`** (1875 lines, 10 inbound)
*Goal:* findings and method. *Audience:* someone needing why, not how.
*Critique:* the known problem, measured again here: **lines 13-1371 = 72%** of
the file sits under "0. Status at a glance" before section 1 begins; 95
headings; Groth16 discussed in 8 places; **498 unicode violations**, the
largest concentration in the tree. `PERF_RESTRUCTURE.md` diagnoses this
correctly and its own advice is to wait for the Groth16 decision -- now
postponed. `DOC-STATUS-SPLIT` is the safe subset.

**`PerfTasks.md`** (118 lines, 8 inbound)
*Goal:* every tracked item with state. *Audience:* whoever picks up work.
*Critique:* the right size and the right shape -- states are defined, "set
aside" carries reasons. It has absorbed 9 new items this cycle and is the file
most at risk of becoming a second `Perf.md` if narrative creeps in. Keep item
text to one line plus a pointer.

**`PerfDoc.md`** (305 lines, 6 inbound)
*Goal:* governance -- ownership, lab discipline, conventions.
*Critique:* S1-S5 are genuinely policy and belong. **S6-S10 duplicate
`BENCHMARKING.md` Part 4 and the file says so itself**, retained only because
other documents link by section number. That is a real constraint, but it is
also how duplication becomes permanent. Recommend fixing inbound links, then
pruning -- tracked, not urgent.

**`PerfGroth.md`** (173 lines, 5 inbound)
*Goal:* Groth16 evidence and the A/B decision. *Critique:* complete, well
argued, correctly frozen pending developer review. Its S4 question 4 (can
batching land behind the existing C ABI?) is the crux and is clearly stated.
No change until the review concludes.

**`PerfNext.md`**, **`PerfTimers.md`**, **`PerfPlatforms.md`**,
**`PerfStores.md`** (1272 lines, new this cycle)
*Critique:* each has a distinct reader -- ranked priorities, a spec for unbuilt
timer work, a platform survey, a store schema. None duplicated an existing
home. But **four new documents in one cycle is the failure mode
`PERF_RESTRUCTURE.md` diagnosed**, and the honest reading is that the set is
now near its useful limit. The moratorium recorded in `PerfNext.md` S6.1 should
hold: no new perf documents until `DOC-STATUS-SPLIT` lands.

**`BUILD_RECONFIG.md`** (89 lines, 3 inbound) -- options for the open
`IMP-BUILD-RECONFIG`. Keep while that item is open; fold into the fix when it
lands.

**`PERF_RESTRUCTURE.md`** (84 lines, 2 inbound) -- a proposal, correctly marked
"Not applied". Keep until acted on, then fold into the result rather than
leaving a stale plan beside a restructured document.

**`Stores.md`** (170 lines, 2 inbound) -- datadir/chain storage notes. Content
fine. **Name collides with the new `PerfStores.md`** (measurement stores);
rename to `ChainStores.md` when next touched, not for tidiness alone.

### 2.2 Off-subject -- relocate

These are competent documents about something other than node sync
performance. They are in `contrib/perf/` by accident of where the work
happened.

**`Peer.md`** (471 lines, 2 inbound) -- peer/RPC operations for a macOS mainnet
node: paths, config, DNS seeds, addrman. **Operator material.** Its natural
home is the Zero400 ops documentation (`TEST_ZERO.md` S8 / `ZeroNodes.md`).
Nothing in it is about measuring sync cost. At 471 lines it is the second
longest in the directory.

**`TENT.md`** (94) + **`TENTZero.md`** (29) -- lineage and file map for the
TENT masternode fork, frozen at `bcb429b (2021-11-13)`. **Fork-comparison
material**, already pointing at `UpdateZero.md` and `~/Work/ZK/ZKs/` for its
execution catalog. Belongs with that material.

**`ZcashV.md`** (132, **0 inbound**) -- 2026 Zcash vulnerability notes (Sprout
`fChecked`, Orchard counterfeiting). **Security material**, explicitly
referencing `Zero400/src/`. Valuable, wrong directory, and nothing links to it
-- so it is currently findable only by listing the directory.

### 2.3 Out of scope -- confirm disposition

**`ZeroWallet_Design.md`** (375, 0 inbound) and **`desys.md`** (100, 0 inbound)
are Qt **desktop wallet** UI design-system documents: themes, CSS tokens,
colour palettes.

`AGENTS.md` states: *"Full node only. Zerowallet out of scope."*
`PerfDoc.md` S1 states ZeroPerf owns `contrib/perf/` for perf work.

**These 475 lines are out of scope for the repository, not merely misfiled.**
They also hold **32 of the tree's unicode violations** and are the only
documents here containing box-drawing and shade glyphs, which is why the
`--fix` safety analysis had to special-case them.

Neither is referenced by anything. Recommend they move to the zerowallet
project or an out-of-tree design folder. **Not deleted without confirmation** --
they represent real work and may be the only copy.

---

## 3. Cross-cutting findings

### 3.1 Duplication, measured

| Duplication | Measurement | Status |
|-------------|-------------|--------|
| Tool documentation | 13 of 13 tools in both `README.md` and `BENCHMARKING.md` S4.1 | Division now declared |
| `PerfDoc.md` S6-S10 vs `BENCHMARKING.md` Part 4 | Self-declared | Tracked, blocked on inbound links |
| Groth16 share figure | 5 documents | `AUT-LINT-CITATIONS` |
| NOTEIDX 35x figure | 5 documents | `AUT-LINT-CITATIONS` |
| Datadir-guard rule | `README.md`, `PerfDoc.md`, tool headers | Acceptable -- a safety rule worth repeating |

The last row is a deliberate exception: **not all repetition is redundancy.** A
rule that prevents destroying a live datadir earns restatement at each point of
use. The test is whether a reader acting on one copy alone would be misled.

### 3.2 Obsolescence

- **`Perf.md` S9** ("recommended path forward: NEON blake2b and Groth16
  batching") -- NEON is now **set aside** (`PerfTasks.md` S5) and Groth16 is
  **postponed**. A section titled "recommended path forward" recommending a
  set-aside item is actively misleading; it is the clearest instance of the
  status/findings mixing that `DOC-STATUS-SPLIT` addresses.
- **`README.md`** referenced `Perf.md` "at the repo root" -- fixed.
- **`PerfDoc.md`** S11 harness inventory -- already struck in the 2026-08-20
  pass, correctly.

### 3.3 The pattern behind most of these

Four separate findings this cycle share one shape: **a rule exists, is written
down, and nothing enforces it.**

| Rule | Where stated | Drift |
|------|--------------|-------|
| No decorative unicode outside README | `AGENTS.md` | 693 violations |
| Numbers live in `Measures.md` under `M-*` | `PerfDoc.md` S1 | Figures in 5 documents each |
| Full node only, zerowallet out of scope | `AGENTS.md` | 475 lines of wallet UI docs |
| One host per comparison | `BENCHMARKING.md` S4.5 | No host field in either store |

The generalisable fix is not more documentation -- it is moving each rule into
`lint-perf.sh` or a schema check. That is why `AUT-LINT-DOCS`,
`AUT-LINT-CITATIONS` and the `PerfStores.md` fingerprint work rank as highly as
they do despite being unglamorous.

---

## 4. Proposed dispositions requiring confirmation

Grouped so they can be accepted or rejected together. **No file is moved or
deleted without explicit approval** (`AGENTS.md`).

| Group | Files | Proposal | Risk |
|-------|-------|----------|------|
| **D1** | `ZeroWallet_Design.md`, `desys.md` (475 lines) | Move out of the repo -- out of scope per `AGENTS.md` | Low. Zero inbound links. May be the only copy; move, do not delete |
| **D2** | `Peer.md` (471) | Move to Zero400 ops docs | Low-medium. 2 inbound refs need updating |
| **D3** | `TENT.md`, `TENTZero.md` (123) | Move to `~/Work/ZK/ZKs/` with the rest of the TENT material | Medium. `TENTZero.md` has 4 inbound refs, and a prior commit specifically repointed its citations here |
| **D4** | `ZcashV.md` (132) | Move to security docs | Low. Zero inbound |
| **D5** | `Stores.md` | Rename `ChainStores.md` | Low, but breaks 2 links for tidiness alone -- defer |

D1-D4 would remove **1201 lines (19%)** of off-subject material, leaving a
perf set that is entirely about perf.

**Recommend taking D1 and D4 first** -- zero inbound links, so nothing breaks --
and treating D2/D3 as a second step once the destination is agreed.
