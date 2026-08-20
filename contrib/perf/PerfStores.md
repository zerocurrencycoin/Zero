# Spec: measurement stores for multi-platform, versioned, feature-aware results

How results are recorded so that a body of measures taken on different
platforms, binaries and feature combinations stays **aggregatable and
searchable**. Assessment of the two stores as they are, the defects that block
multi-platform use, and a proposed schema extension.

**Specification only -- no store rewrite is performed by this document.**
Tracking: `PerfTasks.md`. Platform tooling background: `PerfPlatforms.md`.
Numbers vocabulary and comparability rules: `Measures.md`.

Not to be confused with `Stores.md`, which is about **datadir / on-disk chain
storage**. This file is about the **measurement result stores**. That name
collision is itself a finding (S6).

---

## 1. The stores as they are

Two append-only JSONL ledgers under `reindex-profile/bench-summaries/`.

### 1.1 Throughput ledger (`ledger.jsonl`, 35 rows)

All 35 rows carry all 14 fields -- the schema is uniform, which is a good
starting point:

`binary`, `blocks`, `blocks_per_sec`, `campaign`, `condition`, `elapsed_s`,
`end_height`, `fingerprint`, `mode`, `notes`, `recorded_at`, `run_id`,
`trial`, `warmup_height`

### 1.2 CPU ledger (`cpu_ledger.jsonl`, 14 rows)

`bucket_pct`, `buckets_s`, `groth16_pools`, `note`, `recorded_at`, `scenario`,
`source`, `thread_filter`, `thread_split_s`, `total_all_threads_s`, `total_s`,
`window`

### 1.3 What is already right

Worth stating, because the proposal below should not disturb it:

- **Append-only with idempotent import.** `fingerprint` dedups re-imports.
- **Uniform schemas.** No optional-field archaeology.
- **Provenance on the CPU side.** Every row carries `source`, and all 14
  resolve to an existing file (verified).
- **Window and thread recorded.** `window` and `thread_filter` satisfy the rule
  that a bare percentage is not comparable (`BENCHMARKING.md` S4.5).
- **Rich structured payloads.** `buckets_s`, `groth16_pools`,
  `thread_split_s` keep full resolution rather than a pre-summarised number.

---

## 2. Defects that block multi-platform aggregation

### 2.1 No platform identity at all -- the blocking one

**Neither store has any field for OS, architecture, kernel, CPU model, or host.**

Every one of the 49 rows was taken on macOS/arm64, and nothing in either file
says so. The moment a Linux row is appended, the stores become **silently
wrong**: `profile_collate.py report` would average an arm64 and an x86-64
capture into one mean, and `REPORT.md` would present it as a single condition.

This is not a hypothetical. `PerfPlatforms.md` S1 records two concrete reasons
the numbers differ by platform -- x86-64 takes a different bls12_381 path, and
blake2b may select an SSE/AVX implementation where arm64 links the portable
fallback, moving an 18-21% bucket with no source change.

**Consequence:** platform fields must land **before** the first non-macOS run,
not after. Retrofitting means back-annotating 49 rows from memory. Right now
that back-annotation is trivially correct -- everything is macOS/arm64 -- which
makes this the cheapest it will ever be.

### 2.2 `binary` is a filesystem path, not a version

Two distinct values across 35 rows: `""` and
`/Users/walter/Work/ZK/ZeroPerf/src/zerod`. That is the path where a binary
once sat, not which binary ran. It is host-specific, meaningless on another
machine, and identical across every code change ever measured.

**The identity already exists and is not being captured.** `zerod --version`
prints:

```
Zero Daemon version v4.0.1-a2ae9583c-dirty
```

That is version, commit **and dirty flag**. Two things follow immediately:

- **A dirty flag matters and is being discarded.** The current binary reports
  `-dirty` at commit `a2ae9583c` while HEAD is `b1a37bffc`. So the recorded
  numbers came from a build with uncommitted changes that no longer
  corresponds to any commit. Nothing in the ledger says so, and no result can
  be exactly reproduced from a commit id.
- **Recording it is nearly free**, since the string is one subprocess call away
  in every launcher that already starts `zerod`.

### 2.3 Feature set is smeared across `condition` and `notes`

`condition` has four values (`stock`, `defaultbuf`, `1mbbuf`, `nofdcache`) --
a flat enum encoding one historical FDCACHE experiment. It cannot express a
combination.

Meanwhile `notes` already carries semi-structured pairs:

```
fdcache_built=0;mode=bootstrap;util=stock_trial1/util.tsv
```

**An ad-hoc schema has emerged in a free-text field.** `fdcache_built=0` is a
build-feature flag; `mode=` duplicates the real `mode` column. This is the
system asking for a feature field. Leaving it in `notes` means it is
unsearchable, unvalidated, and silently divergent between producers.

The feature surface that must be expressible is known and bounded:

| Kind | Items |
|------|-------|
| Compile-time | `ZERO_PERF`, `ZERO_FDCACHE`, `ENABLE_WALLET`, `ENABLE_MINING`, `ENABLE_ZMQ`, `ENABLE_PROTON` |
| Runtime, perf-relevant | `-walletwitness=`, `-walletwitnessnote`, `-perffdcache`, `-perfbufsize`, `-dbcache`, `-disablewallet`, `-insightexplorer`, `-txindex`, `-par` |
| Workload shape | wallet id (`none`/`p0`/`p1`/`fat`), chain snap (`tiny`/`short`/`postsap12`/`full`) |

Note `ZERO_PERF` / `ZERO_FDCACHE` are **`#undef` in the current build**, yet
four rows have `condition=nofdcache` and five `1mbbuf`. Whether those trials
ran a perf-enabled binary is not recoverable from the ledger -- exactly the
ambiguity a feature field removes.

### 2.4 `fingerprint` omits every field this spec adds

```python
key = campaign|run_id|mode|condition|trial|warmup_height|end_height|elapsed_s|blocks_per_sec
```

No platform, no version, no feature set. Two genuinely different rows -- same
campaign and trial on macOS and Linux -- that happen to produce the same
`elapsed_s` and `blocks_per_sec` would **collide and the second be silently
dropped as a duplicate**.

The probability is low with float-valued `elapsed_s`, but the failure is
silent data loss, and it becomes likelier exactly where it hurts: rounded or
back-imported rows. The 12 back-imported `postsapling-historical` rows show
duplicate-prone values already (`elapsed 970.0` three times,
`DATA_INDEX.md` S8).

**Any field added for aggregation must also enter the fingerprint**, or dedup
silently defeats the aggregation.

### 2.5 The two stores cannot be joined

A throughput row has `run_id` and `campaign`; a CPU row has `scenario` and
`window`. There is no shared key, so "what was the CPU breakdown during the run
that produced this throughput number" cannot be answered by query -- only by
reading `DATA_INDEX.md` prose. Both describe the same runs.

### 2.6 Minor: field naming diverges

`note` (CPU) vs `notes` (throughput); `scenario` vs `campaign`/`mode`. Small,
but it forces every consumer to special-case each store.

---

## 3. Proposed schema extension

**Principle: add fields, never repurpose or remove them.** The stores are
append-only and 49 rows exist; the extension must let old and new rows coexist,
with absent fields read as "unknown", not "default".

### 3.1 Common block, both stores

| Field | Type | Example | Source |
|-------|------|---------|--------|
| `schema` | int | `2` | constant; absent means 1 |
| `platform.os` | string | `macos`, `linux`, `windows` | `platform.system()` normalised |
| `platform.arch` | string | `arm64`, `x86_64` | `platform.machine()` normalised |
| `platform.os_release` | string | `15.3`, `24.04`, `11-26100` | `platform.release()` |
| `platform.runtime` | string | `native`, `wsl2`, `docker` | see S3.3 |
| `platform.cpu_model` | string | `Apple M1 Max`, `AMD Ryzen 9 7950X` | `sysctl` / `/proc/cpuinfo` |
| `platform.cpu_cores` | int | `10` | physical cores |
| `platform.host_id` | string | `h-3f9a2c` | **salted hash**, see S3.4 |
| `build.version` | string | `v4.0.1` | `zerod --version` |
| `build.commit` | string | `a2ae9583c` | `zerod --version` |
| `build.dirty` | bool | `true` | `-dirty` suffix present |
| `build.date` | string | `2026-08-19T12:32:25-0700` | `BUILD_DATE` in `build.h` |
| `build.compiler` | string | `clang-17`, `gcc-13` | configure-time |
| `features` | object | see S3.2 | launcher |
| `recorded_at` | string | existing | unchanged |

Dotted names denote **nested JSON objects**, not literal dotted keys -- keeps
the row readable and lets a consumer take `platform` whole.

### 3.2 The `features` object

```json
"features": {
  "build": ["ENABLE_WALLET", "ENABLE_MINING", "ENABLE_ZMQ"],
  "runtime": {"disablewallet": true, "dbcache": 450, "walletwitnessnote": false},
  "workload": {"wallet": "p1", "snap": "postsap12", "op": "reindex"}
}
```

Three sub-objects because the three kinds fail differently: `build` needs a
rebuild to change, `runtime` is per-invocation, `workload` describes inputs
rather than the node.

**`build` is a sorted list of enabled defines**, not a map -- so a
feature-combination is one comparable string when sorted and joined, which is
what makes the aggregation in S4 cheap.

**Only record flags that are set**, plus a fixed list of always-recorded
perf-relevant ones. Recording every default would bloat rows and churn the
fingerprint whenever an unrelated default changes upstream.

### 3.3 `platform.runtime` -- why it is separate from `os`

WSL2 reports `linux` for `platform.system()` and is a real Linux kernel, but
`PerfPlatforms.md` S4.2 records that its I/O goes through a virtualised layer,
so **disk numbers characterise WSL2, not Windows or Linux**. Folding it into
`os` would silently merge WSL2 and native Linux rows.

Detection: `/proc/version` containing `microsoft` (WSL2);
`/.dockerenv` or cgroup inspection (docker); else `native`.

### 3.4 `platform.host_id` -- comparability without leaking identity

The rule that matters is one host per comparison
(`BENCHMARKING.md` S4.5): trials compared against each other must come from the
same machine. That needs a **stable, comparable** host token, not a hostname.

A raw hostname is personally identifying and these files are committed to a
public repository. Use a **salted hash**, salt stored locally and uncommitted,
truncated to 8 hex chars. Same machine gives the same token; the token reveals
nothing. This also avoids the `binary` field's mistake of embedding
`/Users/walter/...` -- a real path in a public repo, which the extension should
correct rather than replicate.

### 3.5 Join key across stores (S2.5)

Add `run_id` to CPU rows. `profile_run.sh` derives its window from `debug.log`
in a specific datadir, so it already knows the run; it simply does not record
it. With `run_id` on both sides the join is a dictionary lookup.

Keep `scenario` -- it is the human-facing label and does useful work in
`REPORT.md`.

### 3.6 Fingerprint v2 (S2.4)

Extend the key with `platform.os`, `platform.arch`, `platform.runtime`,
`platform.host_id`, `build.commit`, `build.dirty`, and the sorted
`features.build` join.

**Version the fingerprint, do not silently change it.** Store `fingerprint_v`
alongside. Recomputing v1 fingerprints under v2 rules would make every existing
row look new and re-import 49 duplicates. On import: compare v1 against v1, v2
against v2.

---

## 4. What this buys: aggregation and search

With the above, questions currently answerable only by reading prose become
queries over JSONL:

| Question | Selection |
|----------|-----------|
| Groth16 share, arm64 vs x86-64, same commit | group by `platform.arch`, filter `build.commit` |
| Did NOTEIDX help on Linux as on macOS? | group by `platform.os`, filter `features.runtime.walletwitnessnote` |
| Every result from a dirty build | filter `build.dirty == true` |
| Regression across a version bump | group by `build.commit`, order by `build.date` |
| Comparable set for a new trial | match `platform.*` + `build.*` + `features.build` |
| WSL2 vs native Linux | group by `platform.runtime` |

**The comparability rule becomes machine-checkable**, which is the real prize.
`accumulate_bench.py` can refuse -- or loudly flag -- an aggregation that spans
differing `platform.arch` or `build.commit`, instead of averaging them into a
number that looks authoritative. That converts a documented convention into an
enforced one, the same shift recommended for the ASCII rule
(`PerfNext.md` S3.2) and figure citation (S6.3).

**Naming for aggregation.** A single comparable key can be derived rather than
stored:

```
<os>-<arch>-<runtime>/<version>-<commit>[+dirty]/<features.build joined>
macos-arm64-native/v4.0.1-a2ae9583c+dirty/MINING,WALLET,ZMQ
```

Derived, not a field -- storing it would duplicate state that can disagree with
its parts.

---

## 5. Migration

Ordered so that no step depends on a later one.

1. **Back-annotate the 49 existing rows** with `schema: 1` plus the known
   `platform` block (all macOS/arm64/native) and `build.commit` where
   recoverable from `run_id` dates. Do this **first**, while "all macOS" is
   still true by inspection.
2. **Emit the new block from launchers.** One shared helper -- a
   `platform_stamp.py` next to `datadir_guard.sh` -- called by every launcher,
   so producers cannot drift.
3. **Fingerprint v2** with `fingerprint_v` (S3.6).
4. **Teach the collators.** `accumulate_bench.py` and `profile_collate.py`
   group by the S4 key and flag cross-platform aggregation.
5. **Add `run_id` to CPU rows** (S3.5).

Steps 1-3 must precede any non-macOS run. Steps 4-5 can follow.

**Effort: M overall**, dominated by step 2 (touching every launcher) rather
than by any conceptual difficulty.

**Risk: low.** Additive fields, versioned fingerprint, unchanged existing
values. The one destructive-looking step is step 1, which rewrites existing
rows -- do it as a script that writes a new file and keeps the original, not in
place, consistent with "mark superseded results, do not delete them"
(`BENCHMARKING.md` S4.5 rule 5).

---

## 6. Naming collision to resolve

`Stores.md` (datadir / chain storage) and this file both read as "the stores
document". Recommend `Stores.md` be renamed to `ChainStores.md` when next
touched -- **not now**, since other documents link to it by name and a rename
for tidiness alone is not worth the broken links.
