# Result schema

How a measurement is recorded so that results from different machines,
binaries and feature combinations can be **selected, grouped and aggregated**
rather than silently averaged together.

Applies to both ledgers under `reindex-profile/bench-summaries/`:
`ledger.jsonl` (throughput) and `cpu_ledger.jsonl` (CPU attribution).

Status: **specified, partially implemented.** The `*.v2.jsonl` ledgers carry
`schema`, `platform` and `build`; `features` is still `{}` on every row.
Migration is tracked as **`TASKS.md` A2** (there is no "Track S").

---

## 1. Design rules

1. **The binary is the authority on version.** Repo state and commits are in
   constant flux; a result is produced by a *binary*, not by a checkout. Every
   version field is read from `zerod --version` / `build.h`, never from `git`.
2. **Additive only.** 49 rows already exist. New fields are added; none are
   repurposed or removed. Absent means *unknown*, never *default*.
3. **Every dimension is selectable.** Platform is not special -- it sorts,
   groups and filters exactly like campaign, mode or condition (S5).
4. **Record what was, not what should have been.** A dirty build is recorded
   as dirty rather than cleaned up.

---

## 2. Version block -- `build`

`zerod --version` prints one authoritative line:

```
Zero Daemon version v4.0.1-a2ae9583c-dirty
                    |      |         |
                    |      |         +-- dirty flag: uncommitted changes
                    |      +------------ commit at build time
                    +------------------- base version
```

Compiled in via `src/obj/build.h` (`BUILD_SUFFIX`, `BUILD_DATE`), so it travels
with the binary and stays correct however the working tree moves afterwards.

| Field | Type | This system | Source |
|-------|------|-------------|--------|
| `build.version` | string | `v4.0.1` | base, before first `-` |
| `build.commit` | string | `a2ae9583c` | `BUILD_SUFFIX`, before `-dirty` |
| `build.dirty` | bool | `true` | `-dirty` present |
| `build.date` | string | `2026-08-19T12:32:25-0700` | `BUILD_DATE` |
| `build.tag` | string or null | `null` | release/baseline tag, S2.2 |
| `build.raw` | string | `v4.0.1-a2ae9583c-dirty` | verbatim, never parsed by consumers |

`build.raw` is kept so a future parsing change cannot lose information already
captured.

### 2.1 Why the commit is recorded but not trusted

`build.commit` identifies **which source produced this binary**, which is
useful. It is not a reliable handle for *recovering* that source: the branch
may be rebased, the commit may never be pushed, and `build.dirty` may say the
tree did not match any commit at all.

The current binary is exactly this case -- `a2ae9583c-dirty`, while the branch
head has moved on. So every existing measurement was produced by a binary that
corresponds to **no commit anywhere**. Recording `dirty` makes that visible
instead of implying a reproducibility that does not exist.

**Rule: `build.dirty == true` disqualifies a row from being a baseline.** It
may still be compared informally, but it cannot anchor a release comparison.

### 2.2 `build.tag` -- the stable anchor

Because repo state is unreliable, the durable association is
**tag -> binary -> results**, established at baseline/release time rather than
inferred later.

- At release or baseline, the tag is applied and the binary built from it.
- `build.tag` is populated (`v4.0.2-baseline`, `perf-402-baseline-1`).
- `null` means a development build -- comparable within a session, not a
  reference point.

This makes "compare the current binary against the last baseline" a query
(`build.tag != null`), not an act of archaeology.

---

## 3. Platform block -- `platform`

Initialised with this system's values, so the schema ships with a working
example and the 49 existing rows can be back-stamped correctly.

| Field | Type | This system | Source |
|-------|------|-------------|--------|
| `platform.os` | string | `macos` | `platform.system()` normalised |
| `platform.os_version` | string | `26.3` | `sw_vers -productVersion` |
| `platform.kernel` | string | `25.3.0` | `platform.release()` |
| `platform.arch` | string | `arm64` | `platform.machine()` |
| `platform.runtime` | string | `native` | `native` / `wsl2` / `docker` / `vm` |
| `platform.cpu_model` | string | `Apple M4 Pro` | `machdep.cpu.brand_string` |
| `platform.cpu_cores` | int | `14` | `hw.physicalcpu` |
| `platform.cpu_threads` | int | `14` | `hw.logicalcpu` |
| `platform.mem_gb` | number | `48.0` | `hw.memsize` |
| `platform.host_id` | string | `h-<8 hex>` | salted hash, S3.2 |

`os` is normalised to `macos` / `linux` / `windows`; raw values vary
(`Darwin`, `Linux`, `Windows`).

### 3.1 Why `runtime` is separate from `os`

WSL2 reports `linux` and is a real Linux kernel, but its I/O crosses a
virtualisation layer, so disk numbers characterise WSL2 rather than either
Linux or Windows. Folding it into `os` would merge two populations that differ
exactly where measurement is sensitive. Same argument for containers and VMs.

Detection: `microsoft` in `/proc/version` (wsl2); `/.dockerenv` (docker);
hypervisor hints (vm); else `native`.

### 3.2 `host_id` -- comparable without identifying

Trials compared against each other must come from the same machine. That needs
a stable token, not a hostname: these files are committed to a public
repository, and the existing `binary` field already leaks a real user path.

Salted hash, salt stored locally and uncommitted, truncated to 8 hex.
Same machine gives the same token; the token discloses nothing.

---

## 4. Feature block -- `features`

Feature state is currently smeared across `condition` (a flat four-value enum
from one FDCACHE experiment) and free-text `notes` that already contains
`fdcache_built=0;mode=bootstrap;...`. An ad-hoc schema has emerged in a text
field; this gives it a real one.

### 4.1 Structure

```json
"features": {
  "bundle": "stock",
  "build":   {"ZERO_PERF": false, "ZERO_FDCACHE": false,
              "ENABLE_WALLET": true, "ENABLE_MINING": true, "ENABLE_ZMQ": true},
  "runtime": {"disablewallet": true, "dbcache": 450,
              "walletwitness": null, "walletwitnessnote": false},
  "workload":{"op": "reindex", "wallet": "none", "snap": "tiny",
              "from_height": 0, "to_height": 187417}
}
```

Four parts because they fail differently: `build` needs a rebuild to change,
`runtime` is per-invocation, `workload` describes inputs rather than the node,
and `bundle` names the combination.

### 4.2 Bundles -- named feature combinations

A raw feature map is precise but unusable as a grouping key: nobody groups by
a nine-key dictionary. A **bundle** is a short name for a combination that is
declared once and referenced by every run.

Bundles are defined in `contrib/perf/feature_bundles.json`:

| Bundle | Build features | Meaning |
|--------|---------------|---------|
| `stock` | none of the perf defines | Ships to users. **The default comparison baseline** |
| `perf` | `ZERO_PERF`, `ZERO_FDCACHE` | Lab instrumentation build |
| `perf-fdcache-on` | `perf` + `-perffdcache=1` | FDCACHE enabled at runtime |
| `noteidx` | stock + `-walletwitnessnote=1` | NOTEIDX witness path |
| `ibd-defer` | stock + `-walletwitness=ibd-defer` | Deferred witness build |

Rules that keep bundles honest:

- **A bundle is a name for a feature set, not a substitute for it.** Both are
  stored. If they disagree, the explicit maps win and the mismatch is a bug.
- **Bundles are versioned** (`bundle_v`). Redefining a bundle silently would
  make old rows mean something new -- add `perf-v2`, never redefine `perf`.
- **An unrecognised combination gets `bundle: "custom"`**, never a guess.

This is what makes "all NOTEIDX runs on arm64 against the last baseline" a
one-line filter.

---

## 5. Selection, grouping and aggregation

Every field above is a **selectable dimension**, on equal footing with
`campaign`, `mode`, `condition` and `trial`. Aggregation takes a group-by list
and a filter; platform is not privileged.

```
group_by = [platform.arch, build.tag, features.bundle]
filter   = {features.workload.op: "reindex", build.dirty: false}
```

Selection is **all, subset, or one**, chosen per query, exactly like other
global parameters:

| Intent | Selection |
|--------|-----------|
| One platform | `platform.os == "macos" and platform.arch == "arm64"` |
| Subset | `platform.arch in ["arm64", "x86_64"]` |
| All, but kept apart | group by `platform.arch` -- separate rows, one report |
| All, pooled | no platform in group-by; **requires an explicit override**, S5.1 |

### 5.1 The guard

Pooling across differing `platform.arch`, `platform.runtime`, `build.version`
or `features.bundle` is **refused by default**, and overridable with an
explicit flag that is recorded in the output.

Reason: the failure is silent and authoritative-looking. An arm64 and an
x86-64 capture averaged into one "Groth16 share" produces a number that is
wrong in a way no reader can detect. Refusing by default converts a documented
convention into an enforced one.

Cross-platform pooling is occasionally legitimate -- "how does this behave
across the fleet" -- which is why it is a flag rather than a prohibition.

### 5.2 Derived grouping key

For display only, never stored (storing it would let it disagree with its
parts):

```
macos-arm64-native / v4.0.1-a2ae9583c+dirty / stock
linux-x86_64-native / v4.0.2 (tag: v4.0.2-baseline) / perf-fdcache-on
```

---

## 6. Fingerprint: intent, use and justification

### 6.1 What it is for

The fingerprint exists for **exactly one purpose: import idempotency.** Ledgers
are append-only and results arrive by re-import from TSVs and re-runs of
collation. Without a stable key, re-importing a file duplicates every row, and
duplicates silently corrupt every mean, stdev and trial count computed from
them.

It is a **content hash of the identity of a measurement** -- the fields that
together say "this is the same observation" -- so a re-import is recognised and
skipped.

### 6.2 What it is not for

- **Not a unique id.** `run_id` names a run; the fingerprint says whether two
  rows describe the same observation.
- **Not integrity or authenticity.** It is not signed and detects no tampering.
- **Not a grouping key.** Grouping uses the explicit dimensions in S5.

### 6.3 Why the current one is unsafe

```
campaign | run_id | mode | condition | trial | warmup_height | end_height | elapsed_s | blocks_per_sec
```

No platform, no version, no features. Two genuinely different observations --
same campaign and trial, one on macOS and one on Linux, coinciding on
`elapsed_s` and `blocks_per_sec` -- **collide, and the second is silently
dropped as a duplicate.**

The probability is low with float-valued timings, but the failure mode is
silent data loss of exactly the rows a multi-platform effort exists to gather.
It is likelier where values are rounded or back-imported: the 12
back-imported rows already show `elapsed 970.0` three times.

**Rule: any field that distinguishes two observations must be in the
fingerprint.** Adding a dimension for grouping while omitting it from the
fingerprint means dedup silently defeats the aggregation.

### 6.4 Fingerprint v2

Adds `platform.os`, `platform.arch`, `platform.runtime`, `platform.host_id`,
`build.version`, `build.commit`, `build.dirty`, `features.bundle` and the
sorted `features.build` map.

**Versioned, not silently changed.** Each row stores `fingerprint_v`; v1 keys
are compared against v1 and v2 against v2. Recomputing existing rows under v2
rules would make all 49 look new and re-import them as duplicates -- the exact
failure the mechanism exists to prevent.

Excluded deliberately: `recorded_at` (a re-import of the same observation must
match, and wall-clock differs), `notes`, and derived values such as
`blocks_per_sec` where the inputs are already present.

---

## 7. Dates and versions -- capture early

Every row carries, from the first write:

| Field | Meaning |
|-------|---------|
| `recorded_at` | when the row was written (UTC, ISO 8601) |
| `started_at` | when the measured run began |
| `build.date` | when the binary was built |
| `schema` | schema version of the row |
| `fingerprint_v` | fingerprint algorithm version |

For back-annotated historical rows where a value is estimated, record it and
mark it: `"date_confidence": "estimated"`. An estimated date with a marker is
more useful than an absent one, and far more useful than a precise-looking
fabrication.

---

## 8. Migration

Ordered so no step depends on a later one. Detail in `TASKS.md` **A2**.

1. Back-annotate 49 rows: `schema: 1`, this system's `platform` block, `build`
   where recoverable, `date_confidence: estimated`. **Write a new file, keep
   the original.**
2. Add the blocks to both ledgers (`schema: 2`).
3. One `platform_stamp.py` helper, called by every launcher.
4. Fingerprint v2 with `fingerprint_v`.
5. Teach collators the S5 group-by/filter and the S5.1 guard.
6. Add `run_id` to CPU rows so the two ledgers join.

Steps 1-3 must precede any non-macOS run.
