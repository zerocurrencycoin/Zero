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

## 6. Harness inventory

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
