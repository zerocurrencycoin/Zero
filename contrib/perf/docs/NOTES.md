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

| Note | Date | Applies to | Subject | Superseded by |
|------|------|-----------|---------|---------------|
| `../ZcashV.md` | 2026-06-08 | Zcash 2026 CVEs; RPC samples at h2,471,322 | Sprout `fChecked` and Orchard counterfeiting bugs; relevance to zcashd-lineage forks | nothing |
| `../Peer.md` | 2026-06-10 | Zero400 v4.0.1, macOS | Peer and RPC operations: paths, config, DNS seeds, addrman | nothing |
| `../ZeroWallet_Design.md` | 2026-06-26 | zerowallet400, Qt5 | Desktop wallet UI styling and themes | nothing |
| `../desys.md` | 2026-06 (est.) | zerowallet400, Qt5 | Ice-blue light theme design system | nothing |
| `../TENT.md` | frozen | TENT `bcb429b` (2021-11-13) | TENT masternode fork lineage and comparison | nothing |
| `../TENTZero.md` | frozen | TENT `bcb429b` (2021-11-13) | TENT to Zero zeronode file map | nothing |
| `../PERF_RESTRUCTURE.md` | 2026-08 | `Perf.md` before restructuring | Proposal to restructure `Perf.md` | acted on -- `MIGRATION.md` |
| `../PerfDocReview.md` | 2026-08-20 | 21-document `contrib/perf/` set | Per-document goal, audience and critique | `MIGRATION.md` |
| `../PerfStores.md` | 2026-08-20 | ledgers before schema v2 | Measurement-store assessment | `SCHEMA.md` |
| `../PerfNext.md` | 2026-08-20 | task set before consolidation | Ranked next directions | `TASKS.md`, `FINDINGS.md` |
| `../PerfTasks.md` | 2026-08-20 | task set before consolidation | Task register | `TASKS.md` |

Dates marked `(est.)` are inferred from surrounding content rather than stated
in the note; recorded as estimates rather than omitted (`POLICY.md` S5).

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
| `../Measures.md` | `M-*` inventory | Live; the numbers authority |
| `../Stores.md` | Chain / datadir storage | Live. Name collides with `SCHEMA.md`'s subject; rename when next touched |
| `../README.md` | Per-tool reference | Live; `HOWTO.md` S4.1 is the index |

## Off-subject

Four notes are not about node performance and are in `contrib/perf/` by
accident of where the work happened. Two of them -- the zerowallet UI
documents -- are out of scope for this repository entirely (`POLICY.md` S2).

Proposed relocations, **pending confirmation**, are in `MIGRATION.md` S3.
Nothing is moved or deleted without it.
