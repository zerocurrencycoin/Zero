# Measures: zerod operation durations and quantitative results

**Audience:** Maintainers developing debug.log duration extraction and performance tooling (ZeroPerf).  
**Scope:** Inventory of quantitative measures and results found in ZeroPerf, Zero400, `qa/`, and `contrib/`, plus out-of-tree lab numbers summarized here without host paths. Organized for tooling design: vocabulary, launch method, tools used, uniqueness, contradictions, and doc placement.

**Not this file:** Optimization narratives and open design decisions (**Perf.md**). Structure/algorithm design (**ZeroStruct.md** in Zero400 when present). Contributor gate how-to (**TEST_ZERO.md**).

**Branch note:** Numbers below were harvested from trees as of 2026-08; re-verify against tip before citing in release notes.

---

## 1. Controlled vocabulary

Use these terms consistently in logs, JSONL exports, and docs.

### 1.1 Operation classes (`op_class`)

| Token | Meaning |
|-------|---------|
| `init` | Process start through RPC usable / `Done loading` |
| `ibd` | Initial block download (network) |
| `reindex` | Local `-reindex` / `-reindex-chainstate` of existing `blocks/` |
| `bootstrap` | `-loadblock` / `bootstrap.dat` import |
| `catchup` | Restart tip catch-up after warmup (not full IBD) |
| `witness` | Wallet `BuildWitnessCache` / Building Witnesses |
| `connect` | Per-block `ConnectBlock` (and `-debug=bench` substeps) |
| `rpc` | JSON-RPC call latency |
| `getalldata` | Kitchen-sink wallet RPC cost class |
| `shield` | `z_shieldcoinbase` / related shield ops |
| `drain` | Ops drain loop (shield + send) |
| `harness` | Test suite / script wall time (not product sync) |
| `cache` | dbcache / UTXO / LevelDB budget and fill |
| `memory` | Process footprint / allocation attribution |
| `cpu_bucket` | Profiled CPU share of ConnectBlock work |

### 1.2 Metrics (`metric`)

| Token | Unit | Definition |
|-------|------|------------|
| `wall_s` | s | Wall clock for a bounded run |
| `wall_ms` | ms | Same, millisecond precision |
| `height_per_s` | h/s | `(height_end - height_start) / wall_s` |
| `blk_per_s` | blk/s | Blocks connected per second (synonym of height_per_s when 1:1) |
| `ms_per_block` | ms/blk | Mean cost per block in a window |
| `cpu_pct` | % | Share of filtered profile samples in a bucket |
| `p50_ms` / `p90_ms` | ms | Percentile latency |
| `age_s` | s | Time from broadcast to conf>=1 (or vanish/timeout class) |
| `mib` | MiB | Memory or cache size |
| `fill_pct` | % | Used / budget |
| `ok_rate` | 0..1 | Success fraction of trials |

### 1.3 Result type (`type`)

| Token | Meaning |
|-------|---------|
| `campaign` | One-off measured campaign with stored numbers |
| `repro` | Repeatable harness; re-runnable for new numbers |
| `spot` | Single log/ops observation |
| `estimate` | Order-of-magnitude or derived, not a timed campaign |
| `capability` | Code can emit timings; no archived result set |
| `plan` | Proposed measure; not implemented |

### 1.4 Tools (`tools`)

| Token | Meaning |
|-------|---------|
| `none` | Stock `zerod` + wall clock / RPC / debug.log |
| `debug_log` | Parse stock `debug.log` markers only |
| `debug_bench` | `-debug=bench` ConnectBlock micros (in-tree) |
| `cli_timer` | External script times `zero-cli` |
| `xctrace` | macOS Instruments Time Profiler + export |
| `fs_usage` | macOS `fs_usage` (often root) |
| `vmmap` | macOS `vmmap` / footprint |
| `malloc_stack` | `MallocStackLogging` + `malloc_history` |
| `zero_perf` | Compile-time `ZERO_PERF` / `ZERO_FDCACHE` counters |
| `zcbench` | `zcbenchmark` RPC + `performance-measurements.sh` |
| `lab_monitor` | External `ps` / sample / CSV monitors (out-of-tree bench) |
| `ops_probe` | DevFee probe / drain scripts |

### 1.5 Event markers for duration extraction (`log_marker`)

Prefer exact substrings / regexes as tooling keys:

| Marker key | Typical debug.log / source | Bounds |
|------------|----------------------------|--------|
| `init_done_loading` | `Done loading` / InitMessage | End of RPC warmup (not ops-ready) |
| `init_message` | `init message:` | Init phase labels |
| `update_tip` | `UpdateTip:.*new height=` | Tip progress; sample for rates |
| `cache_config` | `Cache configuration:` | dbcache BI/CS/UTXO budgets |
| `cache_tip` | `UpdateTip:.*cache=` | Hot UTXO cache size |
| `reindex_source` | `Reindex source:` | Reindex start context |
| `reindex_progress` | `Reindex progress:` | Reindex progress |
| `reindex_finished` | `Reindexing finished` | Reindex end |
| `building_witnesses` | `Building Witnesses for block` | Witness rebuild progress |
| `read_fd_cache` | `ReadFdCache:` | fd-cache hit stats (`ZERO_FDCACHE`) |
| `bench_connect` | `- Connect block: .*ms` | `-debug=bench` |
| `rpc_warmup` | RPC **-28** / warmup strings | Client-visible warmup |

**Rule:** Durations are differences between ordered markers (or tip height deltas vs wall), never height-substring greps that collide across eras.

---

## 2. Documentation placement

| Content | Home | Audience |
|---------|------|----------|
| User / contributor: how to run gates, expected suite walls, safe ops recipes | **Zero400 `TEST_ZERO.md`** (and short pointers in **BUILD_ZERO.md**) | Public / contributor |
| Structures, cache budgets, algorithms | **Zero400 `ZeroStruct.md`** | Maintainer |
| Status FSM / soft RPC conditions | **Zero400 `StatusTransitions.md`** (when on branch) | Maintainer |
| Exploratory timings, campaigns, contradictions, tooling design | **This file (`ZeroPerf/Measures.md`)** | Project-internal |
| Optimization narrative and next experiments | **ZeroPerf `Perf.md`** | Project-internal |
| Short-snap lab procedure | **ZeroPerf / Zero400 `AtHeight.md`**; numbers also here | Mixed |
| DevFee shield/drain ages | Out-of-tree ops logs; summary rows here only | Ops-internal |

**Recommendation:** Keep **one number table per campaign** in Measures.md with `source` links. User-facing docs cite only **stable, confirmed** rows (or ranges) and never raw Instruments methodology.

---

## 3. Catalog by measure type

### 3.1 Init / warmup

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-INIT-01 | Wait for `Done loading` | Timeout default **500 s** (`ZCASH_LOAD_TIMEOUT`) | `repro` | `debug_log` | Zero400 `qa/pull-tester/run-bitcoind-for-test.sh` |
| M-INIT-02 | Catch-up to Done loading (fat wallet spot) | **~29 s** cited in status-take notes (800k-tx class) | `spot` / may be absent on current Zero400 tip | `none` | Status-take docs when present; treat as unverified until re-logged |
| M-INIT-03 | Stuck LoadBlockIndex / warmup | RPC **-28** for **>50 min** (misconfigured bootstrap reset) | `campaign` | `none` | `Perf.md` §3 |

Use case: gate RPC clients and harnesses; **not** ops-ready.

### 3.2 Reindex / bootstrap / catch-up throughput

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-RX-TINY | `wall_s`, `height_per_s` | Tip **187417**; **198 s**; **946.6 h/s** | `campaign` | `none` | `AtHeight.md` (2026-07 manual) |
| M-RX-TINY-20260811a | `wall_s`, `height_per_s` | Tip **187417**; **193 s**; **971.1 h/s**; `run_id=tiny-20260811T081310Z` | `campaign` | `debug_log` | `test-logs/measures_tiny-20260811T081310Z.csv` |
| M-RX-TINY-20260811b | `wall_s`, `height_per_s` | Tip **187417**; **188 s**; **996.9 h/s**; `run_id=tiny-20260811T085328Z` | `campaign` | `debug_log` | `test-logs/measures_tiny-20260811T085328Z.csv` |
| M-RX-SHORT | same | Tip **245992**; **274 s**; **897.8 h/s** | `campaign` | `none` | `AtHeight.md` (2026-07 manual) |
| M-RX-SHORT-20260811 | same | Tip **245992**; **247 s**; **995.9 h/s**; `run_id=short-20260811T085646Z` | `campaign` | `debug_log` | `test-logs/measures_short-20260811T085646Z.csv` |
| M-RX-SHORT-DELTA | marginal 3rd blk | **76 s**; **770.7 h/s** (from 2026-07 tiny/short) | `estimate` | `none` | `AtHeight.md` derived |
| M-RX-SHORT-DELTA-20260811 | marginal 3rd blk | **59 s**; **992.8 h/s** (247−188 wall; 58575 ht) | `estimate` | `debug_log` | derived from 20260811b tiny/short |
| M-RX-PHASEA | partial wipe reindex | **~190 s** to ht **~198k**; **~1053 h/s** sample; RSS **~523–540 MiB** | `campaign` | `lab_monitor` | out-of-tree bench REPORT |
| M-RX-LONGHAUL | tip reindex (`env=insight`, `-disablewallet`) | **~9338 s (~2.59 h)** ht **282100→2501537**; RSS **~1.77 GiB** -- insight lab only (§7.1) | `campaign` | `lab_monitor` | out-of-tree longhaul CSV / REPORT |
| M-RX-FULL-CLASS | full archive class | **~8–10 h** estimate; archive **~8.1 GiB** | `estimate` | `none` | `AtHeight.md` |
| M-IBD-CLASS | network sync class | **~6–10 h** | `estimate` | `none` | `BUILD_ZERO.md` |
| M-BOOT-FULL | bootstrap.dat import | **145.7 min**; **2,468,990** blocks; **≈282 blk/s** | `campaign` | `debug_log` (+ profile optional) | `Perf.md` §2 |
| M-RX-PRESAP-AB | pre-Sapling A/B | **~1094** vs **~1076 blk/s** (NS) | `repro` | `zero_perf` + `debug_log` | `Perf.md` §3; `contrib/perf/bench_matrix.sh` |
| M-RX-POSTSAP-AB | post-Sapling A/B | **~307–311 blk/s**; fdcache null win | `repro` | `zero_perf` + `debug_log` | `Perf.md` §3 |
| M-RX-WINDOW | mid-chain window | e.g. **267.5 blk/s**; **~330 KB/s** (h 610k–626k) | `campaign` | `xctrace` + `debug_log` | `Perf.md` §2 |

Use case: ConnectBlock / disk / validation cost; compare only **same height window and wallet flags**.

### 3.3 CPU buckets (profiled)

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-CPU-CORR | corrected post-Sapling window | Groth16 **60.9%**, Disk **26.2%**, Equihash **6.9%**, Tree **6.1%** | `campaign` | `xctrace` | `Perf.md` §2 |
| M-CPU-SEQ | six-capture sequence | Groth16 **48–55%** chain-wide; Equihash **0.252 ms/blk** CV **1.2%**; Groth16 **1.84 ms/blk** | `campaign` | `xctrace` | `Perf.md` §2; `contrib/perf/capture_sequence.sh` |
| M-CPU-LEGACY | early misbucket | "Tree" **57–58%** (Groth16 folded in) | `campaign` | `xctrace` | `Perf.md` §2 -- **superseded** |
| M-CPU-LATCH | root latch | Tree bucket flat **57.9 vs 58.0%** | `campaign` | `xctrace` + `zero_perf` | `Perf.md` §4 |
| M-CPU-FD | fd-cache hit rate | **99.9%** hits -- confirms latch operates as designed | `repro` | `zero_perf` | `Perf.md` §3 |
| M-CPU-FD-THR | fd-cache throughput A/B | **null** blk/s win vs nofdcache (separate from hit rate) | `repro` | `zero_perf` | `Perf.md` §3 |
| M-CPU-FS | open/close share | open **23%** of traced FS time; **~0.048 ms/blk** | `campaign` | `fs_usage` | `Perf.md` §3 |

Use case: prioritize Groth16 batching vs disk vs Equihash; filter thread `zcash-loadblk` / import thread.

### 3.4 Memory

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-MEM-TIP | footprint at tip | Physical **~3.1G**, Writable **~4.7G** @ h **~2.47M** | `campaign` | `vmmap` | `Perf.md` §7 |
| M-MEM-ALLOC | malloc_history window | AddToBlockIndex **~66%** of tracked heap; Groth16 verify **0 heap** | `campaign` | `malloc_stack` | `Perf.md` §7–8 |
| M-MEM-SHIELDEX | static size | Shieldex fields **~176 B/block** ≈ **~435 MB** at tip | `estimate` | `none` | `Perf.md` §8.2 |

### 3.5 Cache / dbcache / RPC micro-latency

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-CACHE-MATRIX | budgets + p50 | e.g. dbcache **800** off: **100/183/517** MiB; generate(100) p50 **~835 ms**; getdbinfo **~4.3 ms** | `repro` | `cli_timer` + `debug_log` | `contrib/measure_dbcache_utxo.py`; ZeroStruct §4.3.4; TEST_ZERO |
| M-CACHE-2500 | longer mine | peak UTXO **0.1 MiB / 500** entries; tip txouts **3000** | `campaign` | same | TEST_ZERO sample `20260725_193336` |
| M-CACHE-MAIN | insight mainnet spot (`env=insight`) | BI/CS/UTXO **600/58/142**; tip cache **~77 MiB** -- insight lab only (§7.1) | `spot` | `debug_log` | ZeroStruct §4.3.1 |

Use case for M-CACHE-MATRIX / M-CACHE-2500: cache sizing on a **wallet / non-insight** host. Do not apply M-CACHE-MAIN budgets to that host.

### 3.6 Witness rebuild

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-WIT-LOG | Building Witnesses progress | **No archived wall_s** | `capability` | `debug_log` | `wallet.cpp` log line |
| M-WIT-EST | proposed shielded reindex effort | **~5–20 min/run** (estimate only) | `estimate` / `plan` | `none` | ExtTests / WitnessReindex notes |

**Gap:** highest-value missing duration class for status/ops tooling.

### 3.7 getalldata / wallet RPC

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-GAD-SOFT | coalesce gate | default **-rpcdatacontinue=20** s | `repro` | `none` | node help / DevFee README |
| M-GAD-HOT | fat-wallet profile | hot in `EncodeBase58Check`; **no wall_ms table** | `spot` | sample/profile | ZeroStruct §6.2; DevFee README |
| M-GAD-S7 | post-S7 expectation | "lower user time"; unquantified | `plan` | `cli_timer` | DevFee README |

### 3.8 Shield / drain (ops)

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-SH-300400 | shield UTXO limit | **300:** 10/10 ok ~90 KB; **400:** 7/10 ok ~119 KB | `campaign` | `ops_probe` | out-of-tree shield probe log |
| M-DR-AGE | shield conf age | e.g. n=148; p50 **120 s**; p90 **330 s**; max **886 s** | `campaign` | `ops_probe` | `drain_idx_*.log` (sample 20260805) |

Use case: ops reliability under tip quiet; not consensus validation cost.

### 3.9 Harness / test suite walls

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-H-STRICT | `--strict` | **~211–212 s** | `spot`/`repro` | `none` | TEST_ZERO |
| M-H-ALL | `--all` | **~1063 s** (2026-07-02); stale **~1275 s** also listed | `campaign` | `none` | TEST_ZERO |
| M-H-SUITE | `--suite` | **~1306 s** | `spot` | `none` | TEST_ZERO |
| M-H-RPC-OUT | slow scripts | protectcoinbase **220 s**; zkey_import **108 s**; … | `campaign` | `none` | TEST_ZERO §3 |
| M-H-WB | walletbackup | measured **~80 s** (earlier guess 15–25 min) | `campaign` | `none` | TEST_ZERO |

Use case: CI / contributor expectation only. **Do not** compare to IBD/reindex.

### 3.10 Microbenchmarks (`zcbenchmark`)

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-ZCB-SUITE | JoinSplit / Sapling / Equihash / connectblockslow / … | **No checked-in numeric archive** | `capability` / `repro` | `zcbench` | `qa/zcash/performance-measurements.sh`; `src/zcbenchmarks.cpp` |

### 3.11 Peer / misc

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-PEER-LOAD | peers.dat load | **3073** addrs in **3 ms** | `spot` | `debug_log` | Peer.md (ZeroPerf) |

### 3.12 In-tree `-debug=bench`

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-BENCH-CONNECT | ConnectBlock substep ms | **No archived campaign** in docs | `capability` | `debug_bench` | `src/main.cpp` LogPrint("bench", ...) |

---

## 4. By application / use case

| Use case | Primary measure IDs | What decision it informs |
|----------|--------------------|---------------------------|
| Desktop validator + wallet restart | M-INIT-*, M-WIT-*, catch-up rates | When Zerowallet may send; soft RPC policy |
| Insight / explorer reindex | M-RX-LONGHAUL, M-CACHE-MAIN, M-RX-FULL-CLASS | Host sizing; `-disablewallet` for chain-only |
| Performance optimization (ConnectBlock) | M-CPU-*, M-RX-POSTSAP-AB, M-BOOT-FULL | Groth16 vs disk vs Equihash priority |
| Short-snap CI / lab | M-RX-TINY, M-RX-SHORT | Fast ConnectBlock smoke without full tip |
| VPS dbcache tuning (non-insight) | M-CACHE-MATRIX, M-CACHE-2500 | 800 vs 2048 vs 4096 |
| Insight explorer host (separate) | M-CACHE-MAIN, M-RX-LONGHAUL | Own deployment; do not blend with wallet node |
| DevFee drain reliability | M-SH-*, M-DR-AGE | Pack size 300; tip-quiet; conf ages |
| Contributor merge gate | M-H-* | Expected wall for `--strict` / `--all` |
| Upstream microbench compare | M-ZCB-SUITE | Regressions in crypto/wallet micros |

---

## 5. Launch and tools matrix

| Tool / command | op_class | Tools | Core-only? |
|----------------|----------|-------|------------|
| `zerod -disablewallet -reindex` + wall + UpdateTip | `reindex` | `none`/`debug_log` | YES |
| `zerod -debug=bench` | `connect` | `debug_bench` | YES |
| `grep`/`rg` on debug.log markers | many | `debug_log` | YES |
| `contrib/measure_dbcache_utxo.py` | `cache`/`rpc` | `cli_timer`+`debug_log` | YES (+ `getdbinfo`) |
| `qa/pull-tester/run-bitcoind-for-test.sh` | `init` | `debug_log` | YES |
| `./contrib/run-tests.sh` | `harness` | `none` | YES |
| `qa/zcash/performance-measurements.sh` | micros | `zcbench` | YES (+ archives for some benches) |
| `contrib/perf/capture_sequence.sh` + `decode_captures.py` | `cpu_bucket` | `xctrace` | NO -- macOS Instruments |
| `contrib/perf/bench_matrix.sh` | `reindex` | `zero_perf`+`debug_log` | NO -- needs `ZERO_FDCACHE` build |
| `fs_usage` / `vmmap` / `malloc_history` | `memory`/`cpu_bucket` | platform tools | NO |
| out-of-tree `run_phase.sh` + `monitor.sh` | `reindex` | `lab_monitor` | NO -- external CSV monitors |
| out-of-tree shield / drain probe scripts | `shield`/`drain` | `ops_probe` | YES RPC to stock zerod |

---

## 6. Unique vs repetitive

### Campaigns (unique stored numbers)

- Tiny/short snap walls; Phase A/B + longhaul tip; bootstrap 145.7 min; CPU capture sequence; fdcache A/B; memory sweep; shield 300/400; drain age sample; measure_dbcache matrix samples; TEST_ZERO `--all` day measurement.

### Repetitive / re-runnable

- Marker recipes (UpdateTip, Cache configuration, Done loading, Reindex finished).
- `measure_dbcache_utxo.py`, `bench_matrix.sh`, `capture_sequence.sh`, `run-tests.sh`, `performance-measurements.sh`, drain/probe scripts.
- `-debug=bench` emission (capability).

### Plans (not yet measures)

- OPS-DEBUGLOG-TIMING filter-then-process suite.
- Per-blk-file wall in reindex (lab REPORT proposals).
- Witness rebuild duration campaign.
- getalldata wall_ms table on DevFee-scale wallet.

---

## 7. Contradictions and comparability rules

| Topic | Conflict | Resolution rule |
|-------|----------|-----------------|
| Tip reindex hours | Estimate **8–10 h** / sync **6–10 h** vs longhaul **~2.6 h** | Different ops (network IBD vs local reindex; wallet on/off). Record those fields; do not collapse to one "tip time" |
| blk/s by era | ~**1100** pre-Sapling vs ~**250–310** post-Sapling vs ~**282** whole-chain vs short-snap ~**900** h/s | Same metric, different height/content. Compare **same window** only |
| CPU buckets | Legacy **58% "tree"** vs Groth16 **48–61%** | Misbucket then corrected. Prefer post-correction; mark legacy superseded |
| Memory growth | Physical footprint "slows"; Writable regions linear | Compression confound. Prefer Writable for long-run growth claims |
| `--all` wall | **1275 s** (stale) vs **1063 s** (dated) | Same harness, old vs new row. Prefer dated; strike stale |
| walletbackup | Guess **15–25 min** vs measured **~80 s** | Guess vs campaign. Prefer measured |

**Not contradictions -- separate questions (same pattern as every other section):**

| Correctness / expected behavior | Throughput / wall time |
|--------------------------------|-------------------------|
| fd-cache **99.9%** hits (latch works as designed) | A/B blk/s vs nofdcache (**null** win) -- M-CPU-FD-THR |
| root-latch match rates | ConnectBlock blk/s unchanged |
| Any functional "it does what we coded" | Separate `metric` rows for `height_per_s` / `wall_s` |

### 7.1 Insight set aside

Insight-index (`-experimentalfeatures` + `-insightexplorer`) is a **separate deployment and test environment** from a validator+wallet node:

- Own lab rows: M-RX-LONGHAUL, M-CACHE-MAIN (and future insight-only campaigns).
- Do **not** use insight dbcache splits or tip times to size a non-insight wallet host.
- Do **not** mix insight reindex walls into "default sync" product copy.
- Wallet/drain golden datadir may enable insight for ops; that is still an **ops** environment, not the contributor gate default.

---

## 8. Making measures accurate and consistent

### 8.1 Extraction pipeline (target)

1. **Filter** -- keep-list of `log_marker` keys; drop or 1/N-sample `update_tip`.
2. **Segment** -- split runs on `Initializing` / process start; attach settings guess (`-reindex`, insight, dbcache) from nearby lines or companion `meta.env`.
3. **Duration** -- emit JSONL events, then reduce to rows:

```text
{"run_id":"…","op_class":"reindex","metric":"height_per_s","value":897.8,"unit":"h/s","height_start":0,"height_end":245992,"wall_s":274,"tools":"debug_log","type":"campaign","source":"AtHeight.md"}
```

4. **Present** -- human table (markdown) generated from JSONL; never hand-copy numbers without `run_id`.

### 8.2 Accuracy rules

- Timestamps: parse debug.log clock; for xctrace, correlate `--toc` start-date to UTC UpdateTip (Perf.md method).
- Rates: `(h1-h0)/(t1-t0)` from first/last UpdateTip in window; reject windows with clock skew or tip stalls.
- Always record: `wallet` on/off, `dbcache`, `height_start/end`, host OS/CPU, binary version string.
- If the run is an **insight** deployment, tag `env=insight` and keep those rows in the insight set (§7.1); do not default-merge with wallet-node rows.
- Soft RPC ages (drain) are **not** ConnectBlock rates; keep `op_class` distinct.
- Prefer stock markers for cross-host tooling; gate `zero_perf` / xctrace as optional enrichments.

### 8.3 Human-readable + machine-friendly

| Layer | Format |
|-------|--------|
| Operator | Markdown tables in Measures.md / TEST_ZERO (stable rows only) |
| Tooling | JSONL under `test-logs/` or `reindex-profile/` with vocabulary above |
| Summary | CSV columns: `run_id,op_class,metric,value,unit,height_start,height_end,wall_s,tools,type,source` |

### 8.4 Priority gaps for debug.log duration tooling

1. **Witness rebuild** wall from `building_witnesses` first/last (+ optional %).
2. **Init**: `init_message` sequence durations through `init_done_loading`, then separate catch-up until tip quiet.
3. **Reindex**: `reindex_source` → `reindex_finished` plus per-file if/when logged.
4. **ConnectBlock**: optional ingest of `-debug=bench` lines into same JSONL schema.
5. Unify AtHeight / out-of-tree lab CSV into the same schema (today: ad hoc `meta.env` + `samples*.csv`).

---

## 9. Recommended documentation structure changes

### Zero400 (user / contributor facing)

| File | Change |
|------|--------|
| **TEST_ZERO.md** | Keep suite walls and gate commands; add a short **Measures pointer** to ZeroPerf for IBD/reindex campaigns; strike stale **1275 s** if still present; never host Instruments methodology |
| **BUILD_ZERO.md** | Keep sync time **class** ranges only; link Measures for measured lab tip times |
| **ZeroStruct.md** | Keep cache **structure** and one worked example; move campaign matrices' home citation to Measures |
| **StatusTransitions.md** | Keep behavioral markers (`Done loading` ≠ ready); do not duplicate throughput tables |
| **AtHeight.md** | Keep procedure; single results table may remain, with "canonical inventory: ZeroPerf/Measures.md" |

### ZeroPerf (project-internal)

| File | Change |
|------|--------|
| **Measures.md** (this file) | Canonical inventory + vocabulary + contradictions + tooling target |
| **Perf.md** | Narrative and next experiments only; each new campaign adds a row ID here |
| **AtHeight.md** | Keep procedure; results catalogued here (`M-RX-*`); no host-local lab path tables |
| **UpdateZero.md** | Developer-doc map + topic registry rows for **Measures** / **Perf** / **AtHeight** / **OPS-AT-HEIGHT** |
| **contrib/perf/README.md** | Launch recipes; reference metric tokens |

### Out-of-tree ops

DevFee / founders UTXO tooling and private lab harnesses are **not** documented or path-cited in Zero400 / ZeroPerf. Summarize ages/rates here with measure IDs only; no host paths.

### Naming discipline

- New campaigns get an **M-*** ID in Measures.md before being cited elsewhere.
- Prefer `height_per_s` over informal "blk/s" when height and blocks differ.
- Prefer `type=campaign|repro|spot|estimate|capability|plan` on every row.

---

## 10. Source index (code and docs)

| Path | Role |
|------|------|
| `ZeroPerf/Perf.md` | ConnectBlock/bootstrap/CPU/memory campaigns |
| `ZeroPerf/AtHeight.md` | Short-snap reindex procedure + numbers |
| `ZeroPerf/contrib/perf/*` | capture_sequence, decode_captures, bench_matrix |
| `ZeroPerf/reindex-profile/` | Raw TSV / memprofile artifacts (local) |
| `Zero400/contrib/measure_dbcache_utxo.py` | dbcache + RPC p50 |
| `Zero400/qa/pull-tester/run-bitcoind-for-test.sh` | Done loading wait |
| `Zero400/qa/zcash/performance-measurements.sh` | zcbenchmark runner |
| `Zero400/src/main.cpp` | `-debug=bench` ConnectBlock micros |
| `Zero400/src/wallet/wallet.cpp` | Building Witnesses log |
| `Zero400/TEST_ZERO.md` | Harness walls |
| `Zero400/ZeroStruct.md` | Cache budgets / structure |

---

## 11. Immediate tooling recommendation

**Proposed new file:** `contrib/perf/extract_measures.py` (filter-then-process; does not launch `zerod`).

Build a path that:

1. Accepts one or more `debug.log` / `debugN.log` files (rotation-aware), or `--datadir` that is **not** the default user datadir.
2. Emits JSONL using §1 vocabulary.
3. Prints a markdown summary table (human) and writes `measures_<run_id>.csv` (machine).
4. Starts with stock markers only (`init_*`, `update_tip`, `reindex_*`, `building_witnesses`, `cache_*`); plug in `-debug=bench` and xctrace as optional backends later.

Do **not** block that on Groth16 product work; it unblocks witness/init duration gaps and reconciles the 2.6 h vs 8–10 h contradiction with structured fields.

**Ship path:** `contrib/perf/extract_measures.py` (+ `run_tiny_baseline.sh` for M-RX-TINY/SHORT labs). Outputs land under `test-logs/` (gitignored).
