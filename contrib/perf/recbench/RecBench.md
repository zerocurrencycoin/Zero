# RecBench

**Record benchmark results so they can be compared.** A result is only worth
storing if a later reader can tell what produced it and whether it is
comparable to another. RecBench is the store, the identity that makes that
decision possible, and the collation over it.

It is **not** a benchmark runner. Launchers measure; RecBench records.

## Status

The store was reset on 2026-09-03 when the record format changed; earlier
ledgers are archived outside this tree (S6).

Identity (S4), store topology (S5) and ordering (S6) are settled and built.
What is open is listed under Tasks, and neither open item changes the row
shape.

## 1. The components

| Component | What it is |
|---|---|
| `recbench.py` | Writer and collator: record, dedup, group, report |
| `stamp.py` | Reads platform, build and compiled features into a row |
| `features.json` | Named feature combinations (bundles) and flag classes |
| `backannotate.py` | One-time migration of pre-schema rows. Not part of normal use |
| `rbpaths.py` | Every path RecBench reads or writes |
| `projects.json` | One entry per project RecBench can record for |

```bash
python3 recbench/recbench.py --index                    # what stores exist
python3 recbench/recbench.py --report                   # collate current rows
python3 recbench/recbench.py --merge NAME [--context ID | --across-contexts]
```

```bash
python3 recbench/recbench.py --import-tsv <file.tsv> --campaign <name>
python3 recbench/recbench.py --report --md <out.md>
python3 recbench/stamp.py --binary src/zerod
```

### Roots, and running standalone

`rbpaths.py` defines two roots that move independently:

| Root | Holds | Default |
|---|---|---|
| `RB_ROOT` | RecBench's own code, `features.json`, salt | directory of `rbpaths.py` |
| `HOST_ROOT` | the measured project: store, binary, build headers | three levels above `RB_ROOT` |

`RB_ROOT` is what makes the subsystem **relocatable** -- move `recbench/`
anywhere, including out of this repository, and nothing inside needs editing.
`HOST_ROOT` is what makes it **reusable**.

| Variable | Sets |
|---|---|
| `RB_PROJECT` | which project to record for |
| `RB_PROJECTS` | `projects.json` location |
| `RB_PROJECT_ROOT` | override the selected project's root |
| `RB_STORE` | override the store directory |
| `RB_SALT` | salt file |
| `RB_RUN_LABEL` | free-text label for a set of runs |
| `RB_BINARY`, `RB_BUILD_HEADER`, `RB_CONFIG_HEADER` | override one bound path |

**No project path is compiled in.** `projects.json` holds one entry per target
-- Zero400, ZeroPerf, zerowallet, uniblake -- each with its own `root`, `store`
and bound paths. A root may be relative to RecBench or absolute or `~`-based,
so projects need not live under one tree.

```bash
RB_PROJECT=uniblake python3 recbench/recbench.py --report
RB_PROJECT_ROOT=/path/to/other/zero python3 recbench/stamp.py
```

Adding a target means adding an entry, not editing a module. An unbound path
or unknown project yields `None`, and the affected fields record as unknown
rather than reading a plausible wrong file.

Verified by copying `recbench/` to an unrelated directory and running the
suites there.

Stores live under `HOST_ROOT/reindex-profile/bench-summaries/` (gitignored:
results are local working data, not repo state).

## 2. Identity: what makes two results comparable

Every row carries two hashes with distinct jobs.

**`context_id`** -- *where and with what*. A 16-char digest over platform (os,
os_version, arch, cpu_model, cores, threads), build (version, commit, dirty)
and compiled features. Two rows sharing it are directly comparable. It is the
quick equality check: one string, not three nested blocks.

Host identity is **excluded** from it, so two identical machines share a
context and re-imaging one does not orphan its history. Host identity is still
recorded, in two forms: `hostname` in plain, as the human label that makes a
result traceable back to a machine, and `host_id`, a salted hash stable across
renames for grouping one machine's own trials. An earlier revision hashed the
hostname *instead of* recording it, on the grounds that ledgers are committed
publicly -- they are not, and the same block already carries `binary`, a real
user path.

**`fingerprint`** -- *which measurement*. Identifies one trial for dedup on
write. It includes `context_id`, because without it the same trial run on two
machines collided and the second was silently dropped -- exactly the case a
cross-platform baseline consists of.

`context_id` leads the collation key, so results from different machines or
binaries form separate groups instead of being averaged into one mean.

### 2.1 Window, dataset, context

A **height window** is the block range a trial measures: `warmup_height` to
`end_height`, where the warm-up portion is imported but not timed. It is one
input among several, not an identity of its own.

A **dataset** is the whole input: which snapshot, and which window over it.
`dataset_id` hashes `{snap, tip_height, tip_hash, warmup_height, end_height}`,
so re-running the same window over a different snapshot is a different dataset
even though the numbers look alike.

A **context** is everything that must match for two rows to be comparable:
platform, build, config and dataset together. Two rows in one context are
peers; two rows in different contexts are not, whatever else they share.

Worked from the store as it stands -- the D5 comparison is three contexts:

| context | n | campaign | condition | dataset_id | config_id |
|---|--:|---|---|---|---|
| `2952a969` | 4 | tromp-crosscheck | tromp | `fd448a4a` | `40c863a3` |
| `551d47fb` | 4 | tromp-crosscheck | default | `fd448a4a` | `b7cf9324` |
| `7caec507` | 2 | uniblake-b1/b2 | uniblake | `fd448a4a` | `188c8402` |

All three share a dataset and differ only in `config_id`, which is why they are
separate contexts: same input, different thing measured. Collation groups
within each and reports the A/B delta across them.

## 3. What a row records

Specified in **`../docs/SCHEMA.md`**: version block, platform block, feature
bundles, confidence markers. That document owns the row shape; this one owns
the system around it.

Rules that have already been violated once, so they are stated here too:

1. **The binary is the authority on version.** Read from `zerod --version` /
   `build.h`, never from `git` -- the tree moves after a binary is built.
2. **Additive only.** Absent means *unknown*, never *default*.
3. **`build.dirty == true` disqualifies a row from being a baseline.**
4. **Never redefine a bundle.** Add `-v2`; old rows silently change meaning
   otherwise.

## 4. Identity: build is not test

`context_id` once conflated two independent things, which was a design error
rather than a detail:

- **Build** -- what binary was produced: version, commit, dirty, compile-time
  defines. Detectable from `src/config/bitcoin-config.h`.
- **Run** -- what was measured and how: `solver`, `op`, other
  runtime flags. Not in any header.

`HASH_BACKEND` is the proof. It was added to `features.json` under a build
flag class, but it is **not a `#define`** -- Zero links uniblake
unconditionally and the kernel is chosen at runtime through `ub_kernel_set()`.
So `detect_build_features()` can never see it. Filing a runtime property as a
compile-time one is a category error, and the same applies to
`solver=tromp`, which changes the measurement completely while leaving
the binary byte-identical.

**Proposed resolution.** Three independent ids, and `context_id` becomes their
composition rather than an opaque blob:

| Id | Over | Answers |
|---|---|---|
| `platform_id` | os, os_version, arch, cpu_model, cores, threads | same machine class? |
| `build_id` | version, commit, dirty, compile defines | same binary? |
| `config_id` | `features.runtime` + `features.workload` (e.g. `solver`, `op`) | same thing measured? |

`context_id = hash(platform_id + build_id + config_id)`, so the single-string
equality check survives while each axis stays separately queryable. "Same
binary, different solver?" and "same solver, different machine?" are both
answerable; against one blob, neither is.

**Justification.** The three change for unrelated reasons and on different
timescales -- a machine is replaced yearly, a binary daily, a runtime flag
between trials. Folding them into one hash means any change looks identical to
any other: a row from a new machine and a row with a different solver are both
just "a different context", with nothing to say which.

**Implemented as specified**, while the store was empty.

### 4.1 Repeat runs of the same test

The axes identify a *configuration*, not an occurrence, deliberately: **repeat
runs of the same benchmark share a `context_id`**, or n>1 is impossible and
every trial becomes its own group. Occurrence is carried by three fields the
fingerprint includes, so repeats store separately and collate together -- the
property n>=4 paired trials depend on.

They are not interchangeable:

| Field | Scope | Set by |
|---|---|---|
| `run_id` | one invocation of a launcher | the launcher, timestamped: `postsapling-20260813T220819Z` |
| `trial` | one measurement inside that invocation | the trial loop, `1..N_TRIALS` |
| `recorded_at` | when the row was written | the writer, UTC |

A launcher run with `N_TRIALS=4` produces **one `run_id` and four `trial`
numbers**. `run_id` groups trials that shared a setup -- one datadir unroll,
one binary, one machine state -- so a systematic fault in that setup is visible
as a whole run rather than four unrelated outliers. `trial` orders them within
it, which is what makes warm-up effects legible: trial 1 is often slower for
reasons that are not the thing being measured.

`recorded_at` is neither. It is when the row reached the store, which for a
long trial is well after the measurement, and it is the only one usable for
sorting across runs.

### 4.2 Campaign and dataset are not the same thing

`campaign` is **intent** -- a named set of runs a person chose to group. It is
a free label, and two campaigns may measure identical data.

A dataset is **input** -- which chain snapshot, which height window. It changes
what is measured regardless of intent.

They are conflated today: the window sits in `warmup_height`/`end_height` as
plain fields, the snapshot is not recorded at all, and `campaign` does duty for
both. Two runs over different snapshots can therefore share a `context_id` and
be averaged -- the same class of error as cross-platform pooling.

**Proposal: a fourth axis `dataset_id`**, over snapshot identity plus height
window, with `campaign` remaining a label and never part of identity.

*Justification.* The test for an identity axis is "does changing it make two
results incomparable?" Snapshot and window pass; campaign fails -- renaming a
campaign changes nothing about the measurement, and comparing across campaigns
is a feature. Keeping campaign out of identity is what lets a re-measurement
under a new name still compare against the old one.

*The data already exists, in the wrong place.* `tiny_baseline.sh` knows
`snap=tiny|short|full` and writes it to `--notes` as free text; several
launchers already call `getblockcount`. So the snapshot is recorded today as
prose nothing can group by.

**Fix, in order.** Each step is useful alone, and none is blocked on a
decision:

| Step | What | Depends on |
|---|---|---|
| 1 | `recbench.py` gains `--runtime k=v` and `--workload k=v`, repeatable | -- |
| 2 | The four launchers that call RecBench pass what they already know: `snap`, `op`, `solver` | 1 |
| 3 | `config_id` starts populating, from step 2 | 2 |
| 4 | Add `dataset_id` over `{snap, tip_height, tip_hash, warmup_height, end_height}` | 2 |
| 5 | Stop `campaign` being load-bearing: it stays a label, never identity | 4 |

Steps 1-3 close S4.3 and are R2. Steps 4-5 are the dataset axis and are R1b.
The ordering matters: **do not add `dataset_id` before step 2**, or it is
`None` on every row and repeats exactly the mistake S4.3 records.

*Why not sooner.* Nothing forces it while one machine measures one snapshot --
the pooling error needs two datasets to bite. B2 (the first Linux baseline) is
when it starts mattering, so steps 1-4 should land before that run, not after.

### 4.3 `config_id`: the empty-hash mistake, and what fixed it

`config_id` was originally hashed from `features.workload`, which no launcher
populates. Every row got `da39a3ee5e6b4b0d` -- the hash of the empty string --
so the field was identical everywhere and distinguished nothing, while making
`context_id` look more precise than it was.

Two changes:

- **`None`, not a hash, when nothing is known.** An empty hash asserts
  "unconfigured"; `None` says "unrecorded".
- **Feed it `features.runtime` as well as `workload`**, so `solver`
  can reach identity.

**Populated, with a live application.** `recbench.py` takes `--runtime k=v` and
`--workload k=v`; `mine_bench.sh` reads the solver from the scratch conf and
passes it, `tiny_baseline.sh` passes `snap` and `op`, `postsapling_reindex.sh`
passes `op`.

The application is the D5 comparison, now in the store: eight rows, four
per solver, identical in platform and build and separated only by
`runtime.solver`. Without `config_id` those eight share a context and
collate to one meaningless mean. With it they form two groups and the A/B
delta is computable -- which is what `--report` now prints.

**Kill condition retained.** A field that is `None` on every row is worse than
no field: it implies a distinction the store cannot make. That was true of
`config_id` before the launchers passed anything, and it is why `dataset_id`
was specified before it was built, not after.

### 4.4 Remaining tension

**Hashes of hashes** mean `context_id` cannot be recomputed from a row without
the same three functions; concatenating the underlying fields would be more
transparent at equal cost. Not changed -- it would rewrite every context hash
for a readability gain. Revisit if the axes change anyway.

## 5. Store topology and merge

Today one file holds every row and contexts are separated at *read* time.
The alternative separates at *write* time: one store per context, merged on
demand.

The per-store design is probably right, because **a merge is a deliberate act
with a decision in it** -- two machines' results are only worth combining once
someone has decided they are comparable. It also gives each machine an
append-only file nothing else writes to, and lets a machine be archived by
moving one file.

`context_id` then becomes the check rather than the separator: a merge
verifies a store's rows share one context and refuses to combine differing
ones unless told to. Merged output would be a **derived view, never a source**.

**Implemented now:** newest-first ordering (S6), and **the store lives inside
the project**, at the path its `projects.json` entry names -- for Zero,
`reindex-profile/bench-summaries/`.

*Why in-project and not cwd.* A store keyed to the working directory produces a
different store depending on where the command was run, which is how results
get scattered and then silently not compared. Keying it to the project means
one target has one store wherever it is invoked from. `RB_STORE` overrides for
a scratch run, and the self-tests use it so they never touch the live store.
Both are gitignored: results are local working data, not repo state.

**Implemented.** Per-context stores, explicit merge, merged output a **view and
never a source**:

```
bench-summaries/<context_id>/ledger.jsonl     one writer, append-only
bench-summaries/merged/<name>.jsonl           derived; regenerable; never appended to
```

- A store is written by exactly one machine+binary+config. No locking, no
  interleaving, and a machine is archived by moving one directory.
- `--merge NAME` refuses to combine differing contexts without
  `--across-contexts`; `--context ID` limits it to named stores.
- A fingerprint collision **across** stores is a genuine duplicate import and
  is reported, not silently dropped -- silent dropping is what made
  cross-machine recording unsafe in the first place.
- `merged/` is excluded from every read path **by name**, so a later merge
  cannot consume an earlier one and double its rows.
- `--index` prints one line per context store: rows, platform, host, build and
  campaigns, so a directory of hashes is navigable without opening each file.

```bash
python3 recbench/recbench.py --index
python3 recbench/recbench.py --merge linux-vs-mac --across-contexts
python3 recbench/recbench.py --merge tromp --context 6efc64d41867a994
```

**Justification.** A merge is a judgement that two result sets are comparable.
Making it an operation forces that judgement to be explicit and reversible;
making it implicit at write time -- one file, separated at read -- hides it,
which is how cross-platform pooling went unnoticed while `SCHEMA.md` S5
already forbade it. Regenerable output also means a merge can be redone after
a rule changes, without touching sources.

**Alternatives considered**, and why they are not the default:

| Approach | Fits when | Why not now |
|---|---|---|
| One store, separate at read (today) | one machine, few contexts | Hid cross-platform pooling for weeks; the separation is invisible until someone looks |
| Store per machine | a fixed fleet | A machine running two binaries is two contexts; keying on the machine reintroduces the pooling it was meant to stop |
| Store per campaign | campaigns are the unit of work | A campaign spanning two hosts is the case that needs separating most |
| Per-context (proposed) | contexts are what comparability turns on | Directory count grows with contexts; needs an index to stay navigable |

**Selection criterion:** the store boundary should be *the thing that makes two
rows incomparable*, so that combining them is impossible by accident and
deliberate by construction. That is the context, not the machine or the
campaign.

Verified: merging three contexts is refused and names them; `--across-contexts`
permits it; a merged view does not change what the report reads; a fingerprint
present in two stores is reported.

## 6. Sorting and time

`recorded_at` is UTC on every row and appears in the TSV, but **is not a sort
key** -- grouping sorts by `(context_id, campaign, mode, condition, heights)`.
That is right for aggregation and wrong for history: "which result superseded
which" is not answerable from the store. JSONL append order is chronological
today only by accident, and a merge would break that.

**Implemented: newest-first.** Rows are **prepended**, not appended -- both the
JSONL and the TSV, with the TSV header held at line 1. Reading a store from the
top shows current and actionable material without seeking to the end. It
rewrites the file on each write, which is acceptable at this size and is part
of why stores should be per-context rather than one growing global file.

**Proposed (R4): `superseded`, a nullable fingerprint.**

A row may name the fingerprint it retires. Readers default to current rows;
`--all-rows` shows the replaced ones too. Nothing is deleted -- the retired row
stays as provenance for how the number changed.

*Why a column and not deletion.* A wrong number that has been cited somewhere
must remain findable, or the citation dangles. Retirement is a statement about
which row to *use*, not about which existed.

*Why explicit and not inferred.* Newest-in-context looks like a free
supersession rule, but it is wrong: four trials of one campaign are peers, not
a chain, and a re-run under changed conditions is a new context rather than a
replacement. Only the person re-measuring knows which it is.

*Cost.* One nullable field, one filter in `collate`, and a `--superseded` flag.
No identity change, so it can land any time.

**Implemented.** `--record --superseded <fingerprint>` names the row this one
replaces; `--report` shows current rows by default and `--report --all-rows`
includes the replaced ones. Validated: n=1 mean 10.00 by default, n=2 mean 7.50
with `--all-rows`.

The two flags are deliberately unrelated names. `--superseded` **writes** -- it
records a relationship. `--all-rows` **reads** -- it turns off a filter. A
shared stem read as a modifier pair, which they are not.

Deliberately **not** in the fingerprint: retiring a row is a later editorial
act, and folding it into identity would mean the same measurement hashes
differently before and after something replaces it.

Three gaps, none of which affect the field's meaning:

| Gap | Consequence |
|---|---|
| ~~`--import-tsv` cannot set it~~ | **Closed** -- `--superseded` applies to every imported row, which is right for re-importing a corrected TSV |
| ~~Other collators ignore it~~ | **Closed** -- both filter at the load boundary, so a report cannot forget |
| ~~No existence check~~ | **Closed** -- a fingerprint no row carries is an error |

All three are closed. The filter lives at each collator's load boundary rather
than in its report, so a new report inherits it by default.

**Justification.** Append-only is right for provenance and wrong for currency:
without `superseded`, every corrected measurement leaves its wrong predecessor
equally citable, which is the failure this project already hit in its
documents. File order is chronological today only by accident, and the first
merge breaks it.

## 7. Scope, and what RecBench is not

RecBench is **cleanly separated from the ZeroPerf lab scripts** -- it imports
only the standard library plus its own `stamp`. It is **not separated from
Zero's workload model**: the row shape is a chain-sync trial
(`blocks_per_sec`, `warmup_height`, `end_height`), so a digest-rate
measurement does not fit it. That is why uniblake keeps its own
`measurements.tsv` rather than reusing this store.

Generic (identification, append-only store, dedup, grouping) and specific
(block heights, sync rates) are entangled at the schema level, not the import
level.

**Proposed (R6): envelope and payload.** Keep every identity field -- the four
ids, run/trial/recorded_at, platform, build -- as a fixed envelope every row
carries. Move the measurement into a payload of `{metric, value, unit}`, which
is the shape uniblake already uses.

A Zero reindex row becomes `metric=blocks_per_sec, unit=blk/s`; a uniblake row
`metric=leaf.blake2b, unit=ns/digest`. `warmup_height`/`end_height` move into
the dataset fields where they already belong.

*Justification.* The envelope is what makes results comparable and is genuinely
project-independent; the payload is what varies and is exactly what a second
project cannot share. Splitting them is the minimum change that lets one store
hold both, and it subsumes uniblake's `measurements.tsv` rather than requiring
a converter between two schemas.

**Implemented.** `metric`/`value`/`unit` are on every row, defaulting to
`blocks_per_sec` / `blk/s` so nothing that read the old column breaks. A
uniblake-shaped row (`leaf.blake2b`, 79.2, `ns/digest`) records and collates
through the same store.

Collation reads the payload, and **`metric` and `unit` are part of the grouping
key** -- without that, a ns/digest row and a blk/s row in one context would
average into a number of no unit at all. The report carries both columns and
the A/B delta names the unit it is a delta in. `blocks_per_sec` survives only
as the shorthand a Zero launcher may pass, which `payload()` maps onto the
metric.

Two Zero-specific columns remain in the envelope -- `warmup_height` and
`end_height` -- because the collators still group on them.

**Proposed (R6b): move them into `features.workload`, keep the grouping.**

They become `workload.warmup_height` / `workload.end_height`, alongside `snap`
and `op`, and `dataset_id` reads them from there. The collation key stops
naming them directly and groups on `dataset_id` instead, which it already
computes.

*Justification.* A height window is meaningful only for a chain-sync workload;
a digest-rate row has no such thing, and today records two nulls to say so.
`features.workload` is exactly the place for a field that some workloads have
and others do not, and `dataset_id` already hashes them, so grouping on it
loses nothing.

*What it buys.* The envelope becomes genuinely project-independent: identity,
occurrence, payload, and nothing about blocks. That is the condition under
which a second project can share the store rather than tolerate columns that
never apply to it.

**Implemented.** The window is promoted into `features.workload` at stamp
time and `dataset_id` reads it from there. A chain-sync row carries
`warmup_height`/`end_height`; a metric row carries neither, rather than two
zeros that would read as a real range.

`--metric` also relaxes the chain-sync argument requirement, so recording a
ns/digest result no longer means inventing a 0-0 window to satisfy a validator.

---

## Tasks

Sequenced: R1 and R2 change the row shape and must land before anything is
recorded at scale. R3 and R4 depend on R1.

| # | Task | State | Why |
|---|------|-------|-----|

Nothing open. The next item comes from a second machine recording (B2), which
is what the merge and index exist for and what will show whether they hold.

See Done for what landed.



### Done

| # | Task | Landed |
|---|------|--------|
| D1 | `context_id`; added to fingerprint and collation key | 2026-09-03 |
| D2 | Renamed and segregated into `contrib/perf/recbench/` | 2026-09-03 |
| D3 | Archived pre-format ledgers outside the tree; store reset | 2026-09-03 |
| D4 | `rbpaths.py`: RB_ROOT / HOST_ROOT split, env overrides, relocation verified | 2026-09-03 |
| D5 | Record `hostname` in plain alongside `host_id`; retire the no-leak rule | 2026-09-03 |
| D6 | ZeroPerf docs point at RecBench, not at its file paths | 2026-09-03 |
| D8 | Project paths externalised to `projects.json`; nothing project-specific in a module | 2026-09-03 |
| D9 | R1 identity axes implemented as specified, with re-evaluation recorded | 2026-09-03 |
| D10 | Newest-first ordering for JSONL and TSV | 2026-09-03 |
| D11 | `run_label`; rejected identifiers recorded (IP, MAC, machine UUID) | 2026-09-03 |
| D12 | R2: `--runtime` / `--workload`; four launchers pass what they know | 2026-09-03 |
| D13 | R1b: `dataset_id`; `campaign` is a label, not identity | 2026-09-03 |
| D14 | R5: build defines derived from `features.json`, not duplicated | 2026-09-03 |
| D15 | R3: per-context stores; reads span them, writes do not | 2026-09-03 |
| D16 | R7: uniblake B1/B2 and the D5 tromp pairs recorded | 2026-09-03 |
| D17 | R4: `--superseded` / `--all-rows`; retired rows kept, excluded from current | 2026-09-03 |
| D18 | R6: `metric`/`value`/`unit` payload; a ns/digest row records through the same store | 2026-09-03 |
| D19 | B2c: folded-stack parser, format detected by content, self-tested on macOS | 2026-09-03 |
| D20 | Product items to `TASKS.md` Product handoff; BenchSummary struck | 2026-09-03 |
| D21 | Recorded runtime key is `solver`, not `equihashsolver` | 2026-09-03 |
| D22 | `--superseded` rejects a fingerprint no row carries | 2026-09-03 |
| D23 | R6b: the height window lives in `features.workload`; a metric row records none | 2026-09-03 |
| D24 | R4 gaps closed: `--import-tsv` can retire, both collators filter at load | 2026-09-03 |
| D25 | Root documents restored to the product tree's state; the ASCII audit moved to `POLICY.md` | 2026-09-03 |
| D26 | R6c: collation reads `metric`/`value`/`unit`; metric and unit are part of the grouping key, so units never pool | 2026-09-03 |
| D27 | R3b: `--merge` with context selection and an across-contexts guard, `--index`, cross-store duplicate reporting | 2026-09-03 |
