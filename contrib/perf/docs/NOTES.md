# Notes

Index of **point-in-time evaluations**: work done once, against a specific
version, at a specific date. They are kept as they were written.

**These are not maintained.** A note records what was believed and measured
then. Policy -- the header format, the "ask before updating" rule, and the
date/version requirement -- is **`POLICY.md` S5**.

A note is not a finding. When something in a note is still true and still
matters, it is promoted into `FINDINGS.md` with a current citation; the note
stays as the record of when it was first established.

---

## Index

Relocated notes now live in **`../keep/`**. They are kept as written and are
not maintained.

| Note | Date | Applies to | Subject |
|------|------|-----------|---------|
| `../keep/ZcashV.md` | 2026-06-08 | Zcash 2026 CVEs; RPC samples at h2,471,322 | Sprout `fChecked` and Orchard counterfeiting bugs; relevance to zcashd-lineage forks |
| `../keep/Peer.md` | 2026-06-10 | Zero400 v4.0.1, macOS | Peer and RPC operations: paths, config, DNS seeds, addrman. Cited by `../Measures.md` (M-PEER-LOAD) and `../Stores.md` |
| `../keep/ZeroWallet_Design.md` | 2026-06-26 | zerowallet400, Qt5 | Desktop wallet UI styling and themes |
| `../keep/desys.md` | 2026-06 (est.) | zerowallet400, Qt5 | Ice-blue light theme design system |
| `../keep/TENT.md` | frozen | TENT `bcb429b` (2021-11-13) | TENT masternode fork lineage and comparison |
| `../keep/TENTZero.md` | frozen | TENT `bcb429b` (2021-11-13) | TENT to Zero zeronode file map. **Referenced by Zero400 documents** -- see below |

Dates marked `(est.)` are inferred from surrounding content rather than stated
in the note; recorded as estimates rather than omitted (`POLICY.md` S5).

### Inbound references from Zero400

`keep/TENTZero.md` is cited by **`UpdateZero.md`**, `ZeroNodes.md` and
`ZeroNodeDev.md` (11 sites), which name it as `TENTZero.md` without a path.

Because nothing in ZeroPerf depends on it, the cleaner resolution is to **move
the file into the Zero400 tree** that does. Until then it stays in `../keep/`
and readers resolve the name by search.

### Retired

These were superseded during the 2026-08 consolidation and removed. Recorded
so their absence is not mistaken for loss:

| Retired | Content now in |
|---------|----------------|
| `BENCHMARKING.md` | `HOWTO.md` |
| `PerfTasks.md`, `PerfNext.md` | `TASKS.md`, `FINDINGS.md` |
| `PerfStores.md` | `SCHEMA.md` |
| `PerfDocReview.md` | `MIGRATION.md`, this file |
| `PerfDoc.md` | `POLICY.md` (S7.1 routing, S7.2 scope), `HOWTO.md` |
| `PERF_RESTRUCTURE.md` | Diagnosis acted on in `MIGRATION.md`; every claim validated before retirement |

## Live specs, not notes

These are current working documents, not archived evaluations. They stay live
until the work they specify lands, then their durable content moves to
`FINDINGS.md`:

| Document | Subject | Status |
|----------|---------|--------|
| `../PerfGroth.md` | Groth16: evidence, options, implementation path | **The focused Groth16 document.** Frozen pending review, not archived |
| `../PerfTimers.md` | Phase-timer design and spec | Live until `TASKS.md` B1 lands |
| `../PerfPlatforms.md` | Cross-platform tooling survey | Live until `TASKS.md` B2 lands |
| `../BUILD_RECONFIG.md` | Autotools reconfigure options | Live until `TASKS.md` C3 lands |
| `../equ/README.md` | Equihash (192,7) mining: entry point, status, next actions | Live; the plan for `TASKS.md` D1 |
| `../equ/FINDINGS.md` | What is measured and computed about the (192,7) solver | Live |
| `../equ/METHOD.md` | How to measure a solver change and how hard to validate it | Live |
| `../equ/PLAN.md` | Staged optimization plan, S0 -> S4, across three platforms | Live |
| `../Measures.md` | `M-*` inventory | Live; the numbers authority |
| `../Stores.md` | Chain / datadir storage | Live. Name collides with `SCHEMA.md`'s subject; rename when next touched |
| `../README.md` | Per-tool reference | Live; `HOWTO.md` S4.1 is the index |

## Off-subject

Four notes are not about node performance and are in `contrib/perf/` by
accident of where the work happened. Two of them -- the zerowallet UI
documents -- are out of scope for this repository entirely (`POLICY.md` S2).

Proposed relocations, **pending confirmation**, are in `MIGRATION.md` S3.
Nothing is moved or deleted without it.
