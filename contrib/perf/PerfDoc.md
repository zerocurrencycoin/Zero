# PerfDoc - ZeroPerf-only context from Zero400-owned documents

Zero400 owns the authoritative code, tests, and project documents. ZeroPerf owns
`contrib/perf/` -- which holds both the harness and the four perf documents
(**Perf.md**, **Measures.md**, **Stores.md**, **PerfDoc.md**) -- plus a gated
source layer. Nothing perf-specific remains at the repo root.

This file holds the perf-relevant material that previously lived only in
ZeroPerf's copies of Zero400-owned documents (**UpdateZero.md**, **AGENTS.md**,
**ZeroStruct.md**, **TEST_ZERO.md**, **TODO.md**, **AtHeight.md**,
**WitnessReindex.md**, **ExtTests.md**), so those copies can be replaced with
Zero400's versions without losing anything.

**Not repeated here.** Every technical topic those copies mentioned -- `§0.14` /
`§0.16`, NOTEIDX, `fBuildingWitnessCache`, PIR-03 / TST-08, W5/W6,
`WAL-RPC-ACCOUNTS`, `zcbenchmark` -- is already covered in **Perf.md** or
**Measures.md**. What follows is only what those documents did *not* carry.

---

## 1. Document ownership and routing

Where perf work is written down, and what each file is for.

| Document | Owner | Purpose |
|----------|-------|---------|
| **contrib/perf/Perf.md** | ZeroPerf | ConnectBlock / sync optimization narrative. CPU buckets; Groth **G**; **P1-P4**; Stages 0-6; **L0-L7**; lab materials; §0.13 BENCH/FIX/IMP. Cites Measures.md for numbers. |
| **contrib/perf/Measures.md** | ZeroPerf | Quantitative measures inventory. Vocabulary; **`M-*`** campaigns; comparability; extraction schema; §8 ledger `CAMPAIGN=` map. |
| **contrib/perf/Stores.md** | ZeroPerf | Storage / datadir structure notes. |
| **contrib/perf/PerfDoc.md** | ZeroPerf | This file. Perf context extracted from Zero400-owned docs. |
| **AtHeight.md** | **Zero400** | Height-bounded reindex / short-snap lab procedure. Tiny/short archive unpack, timed reindex, resume interrupt lab. Points numbers to Measures.md. |
| **ZeroStruct.md** | **Zero400** | Architecture: structures, indexes, algorithms (esp. §4.3, §6.2, §13). Problem/pro-con only, not task status. |
| **TODO.md** | **Zero400** | Status and full task text for `OPS-*` / `WAL-*` / `FR-*` / `EXT-*`. |
| **TEST_ZERO.md** | **Zero400** | Validation runbook and tier inventory. |

**Routing by identifier** -- which document owns which prefix:

| Identifier | Goes in |
|------------|---------|
| **`M-*`** (measure ids, campaign numbers) | **Measures.md** (vocabulary, comparability, extraction, ledger §8) |
| **`PERF-*`** (ConnectBlock optimization narrative) | **Perf.md** (next experiments; cite Measures.md for numbers) |
| **`OPS-*`** / **`WAL-*`** / **`FR-*`** / **`EXT-*`** (status + task text) | **TODO.md** (Zero400) |
| **`OPS-*`** / **`WAL-*`** / **`FR-*`** (architecture) | **ZeroStruct.md** (Zero400) |
| **`OPS-AT-HEIGHT`** | **AtHeight.md** procedure; status in TODO.md |
| **`INT-*`** | **ZeroStruct.md** §11.7 (Zero400) |

Numbers live in **Measures.md** under an `M-*` id. Perf.md and this file cite
that id rather than restating the figure -- a number with no `M-*` binding is
not yet a measure.

---

## 2. Lab and long-run discipline

Constraints on how perf trials are run. These bound the harness in
`contrib/perf/` and are why campaigns are append-only and restartable.

- **No unrestartable long batches.** Do not start a batch of trials where each
  trial is expected to take **more than 20 minutes**, unless each trial can be
  **restarted individually**: separate invocation, separate scratch/out dir,
  append-only ledger, no all-or-nothing runs.
- **One trial per invocation.** A campaign is a sequence of independently
  resumable invocations, not one long process.
- **Scratch is disposable; goldens are read-only.** Copy or softlink lab inputs
  into scratch; never mutate an original. See Perf.md "Lab materials".
- **Effort in bands, not calendar time.** Do not invent or refine day/week
  estimates without measured evidence. Prefer **S/M/L** or named work packages.

---

## 3. Out-of-scope for this tree

**Dev fee / founders addresses are project-internal.** Founders and DevFee payee
addresses, and address-ops scripts, stay out of this tree. Do **not** put
DevWallet handling, scripting, or host paths in ZeroStruct, TEST_ZERO, TODO,
AtHeight, Measures, Perf, or any other product document.

Perf work that touches fat-wallet behavior uses the out-of-tree `DevFeeWallets`
material by reference only (see Perf.md "Lab materials"), never by copying
addresses or host paths into a tracked document.

---

## 4. Documentation conventions

Applies to the ZeroPerf-owned documents (Perf.md, Measures.md, Stores.md, this
file). Zero400's AGENTS.md is authoritative; repeated here because these are the
rules perf documents most often break.

- **Typography:** no emojis or decorative Unicode in any document except
  `README.md`. Use ASCII: `--` not em-dash, `->` not arrow, `"` not curly
  quotes, `...` not ellipsis.
- **Headings:** no parenthetical asides in `#`-`######` titles. Put the aside on
  the first line under the heading. Bad: `### 0.8 Signals (updated)`. Good:
  `### 0.8 Signals` followed by a sentence.
- **History:** do not accumulate dated incremental-fix narrative ("fixed X on
  DATE, then Y, then Z"). Prefer the settled current state. Keep
  path-dependent rationale only when the decision still depends on what was
  tried and rejected.
- **Claims:** specific and actionable, with scope and bounds. No superlatives
  without evidence.

---

## 5. Perf-relevant pointers into Zero400 documents

Context a perf reader needs, owned and maintained by Zero400. Read the Zero400
copy; do not fork these into ZeroPerf.

| Topic | Zero400 document | Why perf cares |
|-------|------------------|----------------|
| Height-bounded reindex / short-snap procedure | **AtHeight.md** | The tiny/short lab procedure behind `M-RX-TINY` / `M-RX-SHORT`; numbers land in Measures.md |
| Witness rebuild across `-reindex` | **WitnessReindex.md** | Scope of `BuildWitnessCache` / note witnesses; `qa/rpc-tests/reindex_shielded.py` is the Tier B gate |
| Wallet / RPC architecture | **ZeroStruct.md** §4.3, §6.2, §13 | Structures behind the witness and `wtxOrdered` work; problem/pro-con, not status |
| Tier inventory and runbook | **TEST_ZERO.md** | Which suites gate a change; the Tier A/B pass lists |
| Equihash test surface | **ExtTests.md** | `equihash_tests` coverage; KATs now at `src/test/data/`. Python Equihash in `qa/` is not authoritative and not performant -- C++ `CheckEquihashSolution` / `zcbenchmark` is |
| Task status | **TODO.md** | `FIX-*` / `IMP-*` scheduling that Perf.md §0.13 references |

---

## 6. Building with instrumentation

The gated source layer is off unless configured in. ZeroPerf adds one option
(`configure.ac`, ZeroPerf-only -- Zero400 has no such flag):

```bash
./autogen.sh
./configure --enable-perf
make
```

`--enable-perf` defines **both** `ZERO_PERF` (root() latch counters) and
`ZERO_FDCACHE` (the `-perffdcache` / `-perfbufsize` block-file read latch).
They are one lab feature with one audience; splitting them would double an
already-untested build matrix. Default is **no**, so a stock build is
byte-identical to Zero400's.

**Editing `configure.ac` arms an autotools trap**: the next `make` re-runs
`configure` without the depends `CONFIG_SITE` and dies on a misleading
"libdb_cxx headers missing". Pre-existing in both trees, not caused by
`--enable-perf`. Symptom, cause, recovery and hardening options:
**[BUILD_RECONFIG.md](BUILD_RECONFIG.md)**.

Runtime flags, meaningful only in an `--enable-perf` build:

| Flag | Default | Effect |
|------|---------|--------|
| `-perffdcache` | off | Use the one-entry read latch per blk/rev file |
| `-perfbufsize=N` | 0 (libc) | `setvbuf` size on block-file reads |
| `-mrclogevery=N` | 16384 | Block-height interval for the root() match-rate log |

**Why this exists.** Before it, neither gate appeared in `configure.ac`, any
Makefile, or `bitcoin-config.h` -- the code was unreachable from any normal
build and had likely never been compiled. That is how `-perffdcache` came to
bind the wrong `GetArg` overload (`atoi64("")` is 0, so a bare flag read as
false) and go unnoticed. Gated code that cannot be built cannot be tested.

## 7. Lint automation

`contrib/perf/lint-perf.sh` runs every check in one pass and filters to code
ZeroPerf owns.

```bash
contrib/perf/lint-perf.sh            # gate: exit 1 only on contrib/perf/ findings
contrib/perf/lint-perf.sh --summary  # counts only, one line per check
contrib/perf/lint-perf.sh --all      # no filter, every finding tree-wide
contrib/perf/lint-perf.sh --list     # what runs, then exit
```

It wraps `contrib/perf/check-unicode.py`, `shellcheck`, and the nine vendored
`zcash-lint/lint-*.sh`, printing OWNED and TOTAL counts per check.

**Why filtered.** `zcash-lint/lint-all.sh` exits 1 on roughly 200 findings that
live in code inherited from Bitcoin and Zcash. Those are set aside -- changing
them diverges from upstream for no functional gain -- so an unfiltered gate is
permanently red, and a permanently red gate gets ignored. This one is green when
`contrib/perf/` is clean and still prints the upstream totals for visibility.

**Scope decisions baked in:**

| Decision | Reason |
|----------|--------|
| Gate scope is `^contrib/perf/` | The only code ZeroPerf owns |
| `datadir_guard.sh` excluded | Sourced, mode 644: shebang meaningless, and `LC_ALL` there would override the caller's locale. Two linters flag it; both are false positives |
| Unicode gate covers `*.sh` / `*.py` only | Perf `.md` and captured `.txt` are a separate concern (UpdateZero.md DOC-UNICODE). `--all` still shows them |
| `shellcheck -f gcc` | Emits `path:line:col:`, so one path filter works across every check |

**Default filtering.** Three checks report only inherited upstream findings that
are set aside; their TOTAL is high, constant and uninformative, so it prints as
`set aside` unless `--all` is given: `include-guards` (52), `includes` (186),
`locale-dependence` (71). `--all` and `--summary` compose.

Baseline as of 2026-08-19: **OWNED 0 across all eleven checks**, exit 0.
Verified to fail correctly by introducing an unused loop counter and an
em-dash, and to return to 0 when reverted.

## 8. Harness inventory

All ZeroPerf-only tooling lives under **`contrib/perf/`** (22 files). Nothing
perf-specific remains in `qa/` or elsewhere in `contrib/`.

| Script | Role |
|--------|------|
| `bench_matrix.sh`, `capture_sequence.sh`, `tiny_baseline.sh`, `postsapling_reindex.sh` | Campaign drivers |
| `witness_lab.sh`, `wallet_sync_profile.sh`, `mine_bench.sh` | Targeted labs |
| `ops-campaign.sh`, `prep_lab_datadir.sh`, `datadir_guard.sh` | Orchestration and the live-datadir write guard |
| `accumulate_bench.py`, `extract_measures.py`, `collate_cycle.py`, `decode_captures.py` | Ledger and trace extraction |
| `debuglog.py`, `stall_check.py`, `shielded_density.py` | Log parsing and analysis |
| `measure_dbcache_utxo.py` | dbcache / UTXO matrix (**M-CACHE-MATRIX**) |
| `performance-measurements.sh` | `zcbenchmark` / valgrind runner (**M-ZCB-SUITE**); run from repo root |
| `kats/README.md` | Equihash KAT regeneration; vectors ship from `src/test/data/` |

Run recipes: **contrib/perf/README.md**. Campaign definitions: **Perf.md** §0.13.
