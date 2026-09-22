# reporoot -- transient drafts for Zero400-owned root documents

**Transient. Nothing here is authoritative.** These are proposed rewrites of
documents this tree reads but does not edit (`POLICY.md` S7.1): `TODO.md`,
`TEST_ZERO.md`, `ZeroStruct.md`, `AtHeight.md`, `BUILD_ZERO.md`,
`WitnessReindex.md`, `ExtTests.md`, `UpdateZero.md`.

**Why drafts live here.** Those files are owned by the Zero400 product tree.
ZeroPerf can read them, and perf work produces findings and task-state changes
that belong in them, but editing them from this tree would fork the product
documentation across two checkouts. So the change is written here, reviewed,
and applied in Zero400 by whoever owns that tree.

**Lifecycle.** A draft is deleted once applied upstream, or once superseded.
A file here that has been applied is not a record -- the upstream document is.
This directory is not a second home for product documentation.

| Draft | Source document | State |
|-------|-----------------|-------|
| `TODO.review.md` | `TODO.md` | Proposed; not applied |
| `MIGRATION_PLAN.md` | -- | Repo consolidation plan; proposal only |
| `CLEANUP.md` | -- | Inherited `src/` material: inert, unused, misnamed |
| `MAINTREE_CHANGES.md` | -- | Changes this tree made outside `contrib/perf` |

**Disposition of this directory is the owner's.** Nothing here is deleted or
moved without instruction; the lifecycle note above describes intent, not a
mandate.

Excluded from the documentation map's per-file rule by the `reporoot/*.md`
wildcard: these are drafts of other trees' files, not documents of this one.
