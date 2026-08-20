# Profiling and measurement tooling across platforms

What the perf harness depends on today, what the equivalent capability is on
Ubuntu Linux and Windows 11 (native and WSL2), and which existing open-source
tools would do the processing rather than being written here.

Written as a **survey and recommendation**, not a plan of record. Nothing here
is scheduled; items judged worth doing are tracked in `PerfTasks.md` with the
reasoning in `PerfNext.md`.

---

## 1. Why this matters now

Every published number in this repo was produced on macOS/arm64. Fourteen
tools in `contrib/perf/` carry macOS assumptions:

| Tool | macOS-only dependency |
|------|----------------------|
| `profile_run.sh`, `capture_sequence.sh` | `xcrun xctrace` |
| `bucket_profile2.py`, `decode_captures.py` | xctrace XML export format |
| `res_sample.sh` | `footprint`, `vm_stat`, `ps -M`, `iostat`, `sample` |
| `prep_lab_datadir.sh`, `tiny_baseline.sh`, and others | `~/Library/Application Support` datadir |

Zero ships Linux and Windows binaries. **No profile has ever been taken on
either**, so no CPU attribution figure here is known to hold off macOS/arm64 --
a caveat worth stating explicitly next to the numbers, because the Groth16
share is the basis of the pending GROTH-DECIDE and that decision is not
macOS-specific.

Two specific reasons the numbers might not transfer:

- **Architecture, not just OS.** All captures are arm64. x86-64 has different
  vector width and a different bls12_381 code path; the pinned crates ship
  assembly for both. The Groth16 share could plausibly differ by more than the
  4% same-host repeat spread.
- **blake2b.** `PerfTasks.md` records that stock arm64 still links
  `blake2b_compress_ref` (the portable C fallback). On x86-64 an SSE/AVX path
  may be selected instead, which would move the blake2b bucket -- 18-21%
  pre-Sapling -- without any source change.

---

## 2. The good news: the portable part is most of the value

`bucket_profile2.py` is 263 lines, of which **only `parse()` (lines 119-158) is
xctrace-specific**. `classify()`, `pool_of()` and the `BUCKETS` table are pure
**symbol-name matching** and carry no format assumption at all.

That table is where the accumulated knowledge lives -- including the two
orderings that must not be "tidied" (groth16 before tree_anchor; witness_cache
before wallet_other), each of which was a published wrong number first
(`BENCHMARKING.md` S3.1).

**Consequence for any porting work:** the task is to write a new `parse()` that
yields the same `(thread, weight_ns, frames)` tuples from a Linux or Windows
profile. The bucketing, layering and leaf logic is reused unchanged, and --
importantly -- results stay comparable across platforms **because the same
classifier produced them**. Rewriting the bucketing per platform would forfeit
exactly that.

This is a favourable architecture that was not designed for portability; it is
worth preserving deliberately rather than by luck. Recommend the parse boundary
be made explicit (a documented input contract) before a second parser is
written against it.

---

## 3. Ubuntu Linux

### 3.1 CPU profiling -- the direct xctrace equivalent

| Capability | macOS today | Ubuntu equivalent | Notes |
|------------|-------------|-------------------|-------|
| Sampling profiler | `xcrun xctrace record --template 'Time Profiler'` | **`perf record -F 99 -g -p PID`** | Kernel-native, no instrumentation. The standard answer |
| Export to parseable text | `xctrace export --xpath ...` (XML) | `perf script` (text) or `perf report --stdio` | `perf script` output is straightforward to parse into frames |
| Folded stacks for tooling | -- | **`stackcollapse-perf.pl`** (FlameGraph) | Produces `frame;frame;frame count` -- a near-ideal input for `classify()` |
| Flame graph rendering | not used here | `flamegraph.pl`, or `perf script report flamegraph` | Visual, complements bucket tables |

**Recommended input format: folded stacks.** Brendan Gregg's FlameGraph
`stackcollapse-perf.pl` (CDDL/GPL, widely packaged) converts `perf script` into
one line per unique stack with a sample count. A `parse()` for that format is
perhaps 20 lines and is *simpler* than the existing xctrace XML backreference
resolution. It is also the de-facto interchange format, so several other
profilers can feed the same path.

**Practical requirements.**

- `perf_event_paranoid` must permit user profiling
  (`sysctl kernel.perf_event_paranoid`, typically needs `<=1`, or `CAP_PERFMON`).
  This is the usual first obstacle in containers and CI.
- Frame pointers or DWARF unwinding. `--call-graph dwarf` works without frame
  pointers but produces much larger captures; Ubuntu 24.04 ships more packages
  built with frame pointers, which helps.
- Debug symbols for `zerod` -- the tree already builds with `CXXFLAGS=-g`
  (confirmed in `config.log`), so this is satisfied.
- Rust symbols from the pinned crates will appear mangled much as they do in
  the current captures; the existing `BUCKETS` needles already match mangled
  forms such as `Fr$u20$as$u20$pairing`, so they should carry over.

### 3.2 Alternatives worth knowing

| Tool | Use | Trade-off |
|------|-----|-----------|
| **`perf`** | Default choice | Needs paranoid setting; the ecosystem standard |
| **eBPF / `bpftrace`** | Custom probes, off-CPU time, latency histograms | Root; can answer questions `perf` cannot, e.g. block-on-lock time |
| **`OProfile`, `sysprof`** | System-wide sampling | Largely superseded by `perf` |
| **Valgrind `callgrind`** | Exact instruction counts, deterministic | 20-100x slowdown -- unusable for a multi-hour reindex, but *excellent* for a single-block or microbenchmark comparison where determinism beats speed |
| **`heaptrack`, Massif** | Allocation profiling | Complements the RSS sampling in `res_sample.sh` |

**`callgrind` is worth a specific note.** `performance-measurements.sh` already
has a valgrind runner. Determinism is exactly what the FDCACHE A/B lacked when
a 1.1% effect sat inside 1.7-4.5% noise (`DATA_INDEX.md` S2). For small,
CPU-bound comparisons -- a Groth16 batching before/after, say -- instruction
counts would resolve differences that wall-clock cannot, at the cost of not
being real time.

### 3.3 Resource sampling

`res_sample.sh` columns map cleanly:

| Column | macOS | Ubuntu |
|--------|-------|--------|
| CPU%, RSS | `ps` | `ps` (same flags mostly work) |
| Physical footprint | `footprint` | `/proc/PID/smaps_rollup` (`Pss`, `Rss`) -- arguably better |
| Per-thread CPU | `ps -M` | `/proc/PID/task/*/stat`, or `top -H` |
| Host disk MB/s | `iostat` | `iostat` (sysstat), or `/proc/diskstats` |
| Pageins, compressed | `vm_stat` | `/proc/vmstat`, `/proc/meminfo` |
| Thermal | `xctrace` thermal-state | `/sys/class/thermal/`, `turbostat` -- **better than macOS here**, exposes per-core frequency directly |

Linux is the **easier** platform for the S2.2 thermal question in `PerfNext.md`:
`turbostat` reports actual achieved frequency, so throttling is directly
observable rather than inferred from a coarse Nominal/Serious state.

`/proc` parsing needs no privilege, which makes a Linux `res_sample.sh` more
portable than the macOS original -- no `sudo`-gated tools in the required set.

---

## 4. Windows 11

Windows splits into two genuinely different targets. Conflating them is the
main risk here.

### 4.1 Native Windows

| Capability | Tool | Notes |
|------------|------|-------|
| Sampling profiler | **Windows Performance Recorder / Analyzer (WPR/WPA)**, ETW-based | The platform-native answer; `wpr -start CPU -filemode`, analyse in WPA |
| Command-line export | `xperf`, `tracerpt` | ETW traces export to XML/CSV -- parseable, though verbose |
| Lightweight alternative | **Superluminal**, **Very Sleepy**, **Intel VTune** | VTune is free and strong on x86-64 microarchitecture detail |
| Symbols | PDB via `dbghelp` | **The main obstacle** -- see below |

**The symbol problem is the real blocker, not the profiler.** Zero's Windows
binaries are cross-compiled with MXE/MinGW (`BUILD_ZERO.md`), producing DWARF
in a PE container rather than MSVC PDBs. ETW tooling expects PDBs. Practical
consequences:

- WPA may show addresses rather than names for `zerod` frames, which makes
  `classify()` useless -- it matches on symbol names.
- Workarounds exist (`--call-graph` with DWARF-aware tooling, or building with
  MSVC) but each is a project in itself.

**Recommendation: do not start with native Windows profiling.** The cost is
dominated by toolchain/symbol work unrelated to the perf questions being asked.

Note also that `README.md` and `TODO.md` record Windows MXE as **never executed
in this program** -- so Windows profiling would be built atop a build path that
is itself unvalidated. Sequence the build validation first.

### 4.2 WSL2 -- the pragmatic path

WSL2 runs a real Linux kernel, so in principle everything in S3 applies. Two
caveats that materially affect measurement:

- **`perf` is not shipped by default.** The Microsoft kernel may lack matching
  `linux-tools`; users commonly build `perf` from the WSL2 kernel source. Once
  present, it works.
- **I/O goes through a virtualised layer.** Filesystem performance differs
  sharply between the WSL2 ext4 VHD and a `/mnt/c` DrvFs mount. **Any disk
  measurement taken under WSL2 characterises WSL2, not Windows** -- and given
  that the workload is already known to be serial-CPU-bound with disk syscalls
  under 5%, this matters less for CPU attribution than it would otherwise. State
  it explicitly on any WSL2 number regardless.

WSL2 is the cheapest way to get *any* non-macOS data point, and CPU
attribution -- the figure that actually underpins GROTH-DECIDE -- should
transfer, since it is dominated by userspace arithmetic rather than syscalls.

### 4.3 What a Windows number would and would not tell us

Worth being precise, because this bounds how much the effort is worth:

- **Would transfer:** relative CPU shares between buckets, since they are
  dominated by userspace crypto.
- **Would not transfer:** absolute throughput, disk behaviour, and anything
  involving the datadir layout or file handles.

---

## 5. Processing and reporting: existing tools rather than new code

The harness currently hand-rolls its ledger, collation and reporting. Some of
that is well-judged; some is reinvention. An honest split:

### 5.1 Worth keeping hand-rolled

`accumulate_bench.py` / `profile_collate.py` are append-only JSONL ledgers with
campaign grouping and n/mean/stdev/min/max. That is a small amount of code
closely fitted to the comparability rules in `Measures.md`, and those rules are
the actual asset. A general framework would not know that a capture needs a
window and a thread to be comparable (`BENCHMARKING.md` S4.5).

### 5.2 Where existing tools would genuinely help

| Need | Candidate | Why |
|------|-----------|-----|
| Statistical rigour on A/B results | **`hyperfine`** (MIT) | Warmup runs, outlier detection, and it reports when a difference is within noise. The FDCACHE A/B -- 1.1% effect on 1.7-4.5% noise -- is exactly the case it exists to flag |
| Significance testing | `scipy.stats`, or `benchstat` from Go's toolchain | `REPORT.md` gives n/mean/stdev but no confidence statement. `benchstat`'s model (report a delta only when significant) directly suits the ledger |
| Flame graphs from existing captures | **FlameGraph** (`stackcollapse-*`, `flamegraph.pl`) | Also the recommended Linux ingest path (S3.1) -- one dependency serving two purposes |
| Cross-platform process sampling | **`psutil`** (Python, BSD) | Replaces most of `res_sample.sh`'s per-platform shelling out with one API across macOS/Linux/Windows |
| Trace interchange | **Perfetto / Chrome Trace Event JSON** | A well-specified format with mature viewers; a plausible common target for xctrace, `perf` and ETW exports |
| Continuous/production profiling | **Parca**, **Pyroscope** (eBPF, Linux) | Directly addresses the "no always-on timing" gap for operators, at the cost of running an agent |

**Strongest single recommendation: `psutil`.** It would collapse the most
platform-specific shell code (`res_sample.sh`: `footprint`, `vm_stat`, `ps -M`,
`iostat`) into one dependency that already works on all three platforms, and it
needs no privilege. It does not cover thermal or per-core frequency, so
`turbostat`/`xctrace` stay for that.

**`hyperfine` caveat.** It is built for short repeatable commands. A multi-hour
reindex violates the "no unrestartable long batches" rule in `PerfDoc.md` S2 --
so use it for microbenchmarks and short trials, **not** as a replacement for the
campaign ledger. Its statistical *approach* is worth borrowing even where the
tool is not.

### 5.3 Prior art worth reading before designing anything

- **Bitcoin Core `src/bench/`** -- a nanobench-based microbenchmark suite.
  **This tree has no `src/bench/`** (confirmed absent), which is why
  `zcbenchmark` is the only microbenchmark surface. Core's framework is the
  obvious model if per-function benchmarks are ever wanted.
- **`zcash/zcash` performance work** -- same lineage; their Sapling batching
  measurements are directly comparable and are the natural cross-check for any
  Groth16 result here.
- **`benchstat`** -- for its output discipline: report a delta only when it
  clears noise.

---

## 6. Recommendations, ranked

| Rank | Item | Effort | Rationale |
|-----:|------|--------|-----------|
| 1 | **State the platform caveat** next to published CPU numbers | **S** | All numbers are macOS/arm64; GROTH-DECIDE rests on them. Costs one sentence per document, removes a silent assumption |
| 2 | **Document the `parse()` input contract** in `bucket_profile2.py` | **S** | Makes the portable/non-portable boundary explicit before a second parser exists (S2) |
| 3 | **Linux `perf` + folded-stack `parse()`** | **M** | One new parse function reusing all bucketing. First non-macOS data point; validates or breaks the arch assumption |
| 4 | **`psutil`-based resource sampler** | **M** | Collapses the most platform-specific shell code; works on all three targets |
| 5 | **WSL2 spot check** | **S-M** | Cheapest Windows-adjacent CPU number, given a Linux parser exists (rank 3) |
| 6 | **`callgrind` for small deterministic A/Bs** | **M** | Resolves effects that wall-clock noise hides; runner already exists |
| 7 | **Native Windows ETW profiling** | **L-XL** | Blocked behind MinGW/PDB symbols and an unvalidated MXE build path (S4.1) |

Ranks 1 and 2 are documentation-only, cost almost nothing, and make every later
item cheaper. Rank 3 is the first that produces a new number.

**None of this is scheduled.** It is a survey; scheduling is
`PerfTasks.md`.
