# Records system: readiness for current and upcoming results

Assessed 2026-09-10 against `recbench/recbench.py` and the results produced
this session (A3, G5, D3 V2, tromp default).

## 1. What the store handles well

Row identity, provenance and de-duplication are solid. `TSV_FIELDS` carries
`fingerprint`, `platform_id`, `build_id`, `config_id`, `dataset_id`,
`superseded` and `recorded_at`, so a Linux row cannot silently pool with a
macOS one and a re-append of an identical trial is skipped rather than
duplicated. `kind` distinguishes `point` / `median` / `cumulative` / `series` /
`share` / `count`, which is what stops a stdev being taken over a cumulative
value.

## 2. The gap: no place for rep count or dispersion

**A row stores one `value`.** `n` and `stdev` exist only in *collation output*
(`recbench.py:599-609`), computed across rows. There is no field for "this
measurement was 1000 reps with CV 7.3%".

That is a poor fit for everything measured this session:

| Result | Shape | Fits a row today? |
|--------|-------|-------------------|
| M-ZCB-SAP-VERIFY | 1000 reps, one process, steady median + CV | **No** -- n and CV go in `notes` as prose |
| M-EQ-SOLVE-1927-FIXED | 4 paired nonces, per-nonce times | **No** -- either 4 rows with no pairing key, or 1 row losing the detail |
| D3 V2 | set equality, pass/fail | **No** -- not a numeric metric at all |
| tromp default | a decision plus a test | **No** -- not a measurement |

The schema is **sync-shaped**: `warmup_height`, `end_height`, `blocks`,
`blocks_per_sec` are first-class, while rep-based microbenchmarks and
pass/fail validations are not. That was correct when the only workload was
reindex. It is now the constraint.

## 3. Implemented 2026-09-10

Five fields added to `TSV_FIELDS`, with write-path validation
(`validate_reps`) and twelve self-test assertions, one of them mutation-tested:

| Field | Holds |
|-------|-------|
| `n_reps` | repetitions behind `value` |
| `warmup_dropped` | leading reps excluded before summarising |
| `dispersion` | spread of the kept reps |
| `dispersion_kind` | `cv` \| `stdev` \| `iqr` \| `range` |
| `pair_key` | groups rows that are one paired measurement |

**Validation rejects the shapes that would be unreadable later**: a dispersion
with no kind (7.3 could be a percent or a stdev in seconds), a kind with no
dispersion, an unknown kind, a `cv` above 1.0, a negative dispersion,
`n_reps` below 1, a warmup count with no `n_reps`, a warmup that drops every
rep, and non-numeric values. All fields stay optional, so existing sync rows
are unaffected -- verified by a self-test that an empty row passes.

The remaining items below are **not** implemented.

## 3a. Still needed

| # | Change | Why |
|---|--------|-----|
| 3 | Add a `verdict` kind (`pass` / `fail`) | D3 V2 and the solver-guard test are results worth keeping and cannot be stored. Today they live only in `FINDINGS.md` |
| 4 | Teach `collate()` to group by `pair_key` | The field now exists, but collation still pools by context alone, so a paired sweep is not yet summarised as one measurement |

## 3b. Values are stored as decimal fractions

**A stored ratio is a fraction: `cv 0.073`, never `7.3`.** Percent is a display
format; putting it in the store invites a second division by 100 or a missing
one, and neither is detectable afterwards -- a column holding `7.3` cannot be
distinguished from one holding a stdev in seconds. Formatting to `7.3%` is the
reader's job.

Enforced: `validate_reps` rejects `cv` above 1.0 with a message naming the
likely cause, and the self-test asserts that `{"dispersion": 7.3,
"dispersion_kind": "cv"}` is refused.

## 3c. Which columns are actually necessary

30 columns, but they are not equally load-bearing. Sorted by what breaks
without them:

**Computed, never hand-written (6).** `fingerprint`, `context_id`,
`platform_id`, `build_id`, `config_id`, `dataset_id`. `append_row` derives
these; a caller supplying them is a bug.

**The minimum a row needs to mean anything (5).** `metric`, `value`, `unit`,
`kind`, `recorded_at`. Without `unit` a number is not a measurement; without
`kind` a median and a point value pool; without `recorded_at` nothing can be
ordered.

**Needed to compare across runs (4).** `campaign`, `run_id`, `binary`,
`superseded`. These answer "which trial was this, and is it still current".

**Needed only for the workload that has them (rest).** `warmup_height`,
`end_height`, `blocks`, `elapsed_s`, `blocks_per_sec` are **sync-shaped** and
empty on a microbenchmark row; `n_reps`, `warmup_dropped`, `dispersion`,
`dispersion_kind`, `pair_key` are **rep-shaped** and empty on a sync row;
`mode`, `condition`, `trial`, `exec`, `notes` are optional context.

**Practical answer: a usable row is 5 mandatory fields plus the 6 computed
ones.** Everything else is optional and typed to a workload. That is why
adding five rep fields cost nothing -- the schema is already sparse by design,
and a new workload adds columns rather than reinterpreting existing ones.

## 4. Interim rule, until those land

**Every result gets a `FINDINGS.md` in its own `test-logs/<task>-<utc>/`,
and the `M-*` row in `Measures.md` carries n and dispersion in its Result
cell.** That is what was done for A3, G5, D3 V2 and the tromp default this
session. It is prose, not schema, but it is durable and citable.

Do **not** wait for the schema before recording. A result held out of the store
because the store cannot type it is a result that gets lost.

## 5. Archiving earlier results

`retention.py` already treats `archives/` as `NEVER_RECLAIM` (`:146`) and
PROTECTED, so anything moved there is safe regardless of age or size. Existing
archives: `eqvectors-solver-baseline-192-7-20260825.tar.gz` (the V2 oracle),
`walletsync-fat-g0-20260812.tar.gz`, `sodium121-binaries`.

**Rule: archive by format-agnostic tarball, with a note saying what the format
is.** Earlier results predate the current schema and several predate RecBench
entirely. They should not be reformatted to fit -- reformatting a measurement
is editing it. Tar the directory as it stands, put it under `archives/`, and
record in the owning document what instrument produced it and why its format
differs. The `.prev-<utc>` convention (`snapshot_data.sh`) covers the same
need for single collated files.

**Provenance beats uniformity.** A result whose format is odd but whose origin
is documented is usable; a result normalised into the current schema by
someone guessing at its provenance is not.
