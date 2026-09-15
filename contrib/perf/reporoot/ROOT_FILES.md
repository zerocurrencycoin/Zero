# Repo-root documents: which belong there

**Draft. Recommendation only; no file moved or deleted.** Reviewed 2026-09-09.

`README.md` declares a **ship set** -- the documents a distribution presents:
`README`, `ZERO_COIN`, `BUILD_ZERO`, `TEST_ZERO`, `CONTRIBUTING`, `TODO`,
`AGENTS`, `doc/man/`. Everything else at the root is there by accretion.

## Assessment

| File | Lines | Self-describes as | Recommendation |
|------|------:|-------------------|----------------|
| `AtHeight.md` | 194 | "*Project Planning*" | **Move.** Planning, not product. `doc/design/` or the perf tree |
| `WitnessReindex.md` | 65 | "*Project Planning*", "findings and proposals captured" | **Move.** Its subject is witness rebuild -- ZeroPerf measures it (M-WAL-*), so the evidence and the proposal are in different trees today |
| `ExtTests.md` | 101 | "Extended harness notes (**maintainer**)", explicitly *not* the public runbook | **Move** beside the harness: `qa/`. It even says the authority is `qa/pull-tester/rpc-tests.sh` |
| `ZeroStruct.md` | 1225 | Architecture reference | **Keep, but split.** Genuine reference and the largest root document. Sections tied to open `OPS-*`/`WAL-*` work are task state; the durable architecture is not |
| `UpdateZero.md` | 1652 | Execution catalog | **Keep, extract.** Largest file in the repo. Sections that are finished history belong in release notes; sections ready for open access could publish |
| `ZcashFixes.md`, `ZebraZero.md`, `ZeroNodeDev.md`, `ZeroNodes.md`, `ReleaseNotes401.md` | 155-320 | mixed | Review individually; not urgent |

## Justification

**The test is the reader, not the topic.** A root document should answer a
question a user, miner, exchange or builder actually arrives with. `AtHeight`
and `WitnessReindex` answer questions *we* have while planning; `ExtTests`
answers a maintainer's question and says so in its first line.

**`qa/` and `contrib/` are the right destinations and are already less strict**
than the root -- work there does not carry ship-set expectations, which is why
the perf tree lives under `contrib/perf/`.

**This is a Zero400 decision.** Moving a root file changes what a distribution
presents, so it needs the product tree's agreement even though the analysis is
cheap. Transient copies of anything needed for reference can live here.

## Sequence

1. Confirm the three "Project Planning" files have no inbound links from ship-set documents.
2. Move `ExtTests.md` to `qa/` -- lowest risk, it already points there.
3. Move `AtHeight.md`, `WitnessReindex.md` to `doc/design/`.
4. `ZeroStruct` / `UpdateZero` splits: separate exercise, needs reading.
