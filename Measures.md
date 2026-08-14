# Measures

**Audience:** Maintainers developing debug.log duration extraction and performance tooling (ZeroPerf).
**Scope:** Canonical **`M-*`** inventory: vocabulary, catalogued results, comparability rules, extraction schema, and ledger `CAMPAIGN=` bindings. Out-of-tree lab numbers appear as summary rows without host paths.

**Not this file:** Optimization narrative, BENCH/FIX/IMP, baseline tracks **L0-L7**, Stages, **G**/**P1-P4**, Groth decision, lab material paths (**Perf.md**). Structure/algorithms (**ZeroStruct.md**). Contributor gates (**TEST_ZERO.md**). Short-snap procedure (**AtHeight.md**). Script usage (**contrib/perf/README.md**).

**ID rule:** Quantitative results use **`M-*`** IDs here only. Perf cites those IDs in one line. New campaigns get an `M-*` row here before citation elsewhere. Ledger `CAMPAIGN=` strings bind in §8. Prefer `height_per_s` when height and block counts differ. Do not put BENCH/FIX/IMP, L0-L7, Stages, or G/P priorities in this file.

**Branch note:** Re-verify tip numbers before citing in release notes.

---

## 1. Controlled vocabulary

Use these terms consistently in logs, JSONL exports, and docs.

### 1.1 Operation classes (`op_class`)

| Token | Meaning |
|-------|---------|
| `init` | Process start through RPC usable / `Done loading` |
| `ibd` | Initial block download (network) |
| `reindex` | Local `-reindex` / `-reindex-chainstate` of existing `blocks/` |
| `rescan` | Wallet `-rescan` / `ScanForWalletTransactions` on an already-indexed chain |
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
| `vmmap` | macOS `vmmap` / footprint / Writable regions |
| `heap` | macOS `heap` size-class census |
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

| Content | Home |
|---------|------|
| `M-*` numbers, vocabulary, contradictions, extraction schema, ledger map | **This file** |
| Optimization narrative, BENCH/FIX/IMP, L0-L7, Stages, G/P, Groth, lab materials | **Perf.md** |
| Short-snap / resume procedure | **AtHeight.md** (results rows here) |
| Script launch recipes | **contrib/perf/README.md** |
| Contributor gates / suite walls | **TEST_ZERO.md** (cite stable `M-H-*` only) |
| Cache structure | **ZeroStruct.md** (cite `M-CACHE-*` for measured samples) |
| DevFee ages | Out-of-tree; summary `M-SH-*` / `M-DR-*` rows here only |

One number table per campaign here. User-facing docs cite stable confirmed rows only -- not Instruments methodology.

---

## 3. Catalog by measure type

Stored campaign numbers live only in the tables below. Re-runnable recipes are in §5. Work not yet measured is specified in **Perf.md** §0.13 (BENCH-*), not as placeholder `M-*` rows here.

### 3.1 Init / warmup

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-INIT-01 | Wait for `Done loading` | Timeout default **500 s** (`ZCASH_LOAD_TIMEOUT`) | `repro` | `debug_log` | Zero400 `qa/pull-tester/run-bitcoind-for-test.sh` |
| M-INIT-02 | Catch-up to Done loading (fat wallet spot) | **~29 s** cited in status-take notes (800k-tx class) | `spot` / may be absent on current Zero400 tip | `none` | Status-take docs when present; treat as unverified until re-logged |
| M-INIT-03 | Stuck LoadBlockIndex / warmup | RPC **-28** for **>50 min** (misconfigured bootstrap reset; fixed in `bench_matrix` by excluding `blocks/` on bootstrap reset). Inner interrupt: Perf **FIX-LBI** | `campaign` | `none` | harness + `main.cpp` |

Use case: gate RPC clients and harnesses; **not** ops-ready.

### 3.2 Reindex / bootstrap / catch-up throughput

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-RX-TINY | `wall_s`, `height_per_s` | Tip **187417**; **198 s**; **946.6 h/s** | `campaign` | `none` | `AtHeight.md` (2026-07 manual) |
| M-RX-TINY-20260811a | `wall_s`, `height_per_s` | Tip **187417**; **193 s**; **971.1 h/s**; `run_id=tiny-20260811T081310Z` | `campaign` | `debug_log` | `test-logs/measures_tiny-20260811T081310Z.csv` |
| M-RX-TINY-20260811b | `wall_s`, `height_per_s` | Tip **187417**; **188 s**; **996.9 h/s**; `run_id=tiny-20260811T085328Z` | `campaign` | `debug_log` | `test-logs/measures_tiny-20260811T085328Z.csv` |
| M-RX-TINY-20260811c | `wall_s`, `height_per_s` | Tip **187417**; **204 s**; **918.7 h/s**; `run_id=tiny-20260811T192820Z` (after FIX-LBI; **concurrent** with bootstrap smoke -- treat as noisy) | `campaign` | `debug_log` | `test-logs/measures_tiny-20260811T192820Z.csv` |
| M-RX-TINY-20260811d | `wall_s`, `height_per_s` | Tip **187417**; **220 s**; **851.9 h/s**; `run_id=tiny-20260811T200056Z` -- **contended** with L1/L2 baseline job; not a clean solo | `campaign` | `debug_log` | `test-logs/baseline_tiny_solo_20260811T200056Z.log` |
| M-RX-SHORT-20260811b | same | Tip **245992**; **264 s**; **931.8 h/s**; `run_id=short-20260811T200447Z` -- after tiny in same L0 job; still shared host with L2 | `campaign` | `debug_log` | `test-logs/baseline_short_solo_20260811T200447Z.log` |
| M-RX-SHORT | same | Tip **245992**; **274 s**; **897.8 h/s** | `campaign` | `none` | `AtHeight.md` (2026-07 manual) |
| M-RX-SHORT-20260811 | same | Tip **245992**; **247 s**; **995.9 h/s**; `run_id=short-20260811T085646Z` | `campaign` | `debug_log` | `test-logs/measures_short-20260811T085646Z.csv` |
| M-RX-SHORT-DELTA | marginal 3rd blk | **76 s**; **770.7 h/s** (from 2026-07 tiny/short) | `estimate` | `none` | `AtHeight.md` derived |
| M-RX-SHORT-DELTA-20260811 | marginal 3rd blk | **59 s**; **992.8 h/s** (247−188 wall; 58575 ht) | `estimate` | `debug_log` | derived from 20260811b tiny/short |
| M-RX-PHASEA | partial wipe reindex | **~190 s** to ht **~198k**; **~1053 h/s** sample; RSS **~523–540 MiB** | `campaign` | `lab_monitor` | out-of-tree bench REPORT |
| M-RX-LONGHAUL | tip reindex (`env=insight`, `-disablewallet`) | **~9338 s (~2.59 h)** ht **282100→2501537**; RSS **~1.77 GiB**; tag `env=insight` -- do not size wallet hosts from this row | `campaign` | `lab_monitor` | out-of-tree longhaul CSV / REPORT |
| M-RX-FULL-CLASS | full archive class | **~8–10 h** estimate; archive **~8.1 GiB** | `estimate` | `none` | `AtHeight.md` |
| M-IBD-CLASS | network sync class | **~6–10 h** | `estimate` | `none` | `BUILD_ZERO.md` |
| M-BOOT-FULL | bootstrap.dat import | **145.7 min**; **2,468,990** blocks; **≈282 blk/s** | `campaign` | `debug_log` (+ profile optional) | `Perf.md` §2 |
| M-BOOT-NEW-20260813 | new Zero400 `bootstrap.dat` smoke | n=1 window 50k-75k; **1000 blk/s** (25.0 s / 25000); magic `5a45524f`; hashlist **0-2468990** (2468991 hashes); file **5415354491** B. Peer class M-BOOT-PRESAP (~1076 n=4) | `campaign` | `lab_monitor` | `test-logs/postsapling-20260813T220819Z/` |
| M-BOOT-SMOKE-20260811 | bootstrap window 50k–75k | **862.07 blk/s** (n=1); concurrent with tiny -- **superseded** by M-BOOT-PRESAP | `campaign` | `lab_monitor` | noisy; see M-BOOT-PRESAP |
| M-BOOT-PRESAP | bootstrap window 50k-75k | **mean 1075.63 blk/s** (n=4, stdev 19.61; min 1041.67 max 1086.96); stock; ledger `CAMPAIGN=bootstrap-presap` | `campaign` | `lab_monitor` | `REPORT-bootstrap-presap.md` |
| M-RX-PRESAP | reindex window 50k-75k | **mean 1012.12 blk/s** (n=4, stdev 45.97; min 961.54 max 1086.96); stock; ledger `CAMPAIGN=reindex-presap`; peer M-BOOT-PRESAP | `campaign` | `lab_monitor` | `REPORT-reindex-presap.md` |
| M-RX-UTIL-SMOKE | reindex same window 50k-75k | **1041.67 blk/s** (n=1); ledger `CAMPAIGN=util-smoke`; util.tsv on; peer band for M-BOOT-PRESAP / M-RX-PRESAP | `campaign` | `lab_monitor` | `REPORT-util-smoke.md` |
| M-RX-PRESAP-AB | pre-Sapling A/B | **~1094** vs **~1076 blk/s** (NS) | `repro` | `zero_perf` + `debug_log` | `Perf.md` §3; `contrib/perf/bench_matrix.sh` |
| M-RX-POSTSAP-AB | post-Sapling A/B (FDCACHE-era) | **~307–311 blk/s**; fdcache null win | `repro` | `zero_perf` + `debug_log` | `Perf.md` §3; historical TSV |
| M-RX-POSTSAP-STOCK | stock `-reindex` rematch | **mean 298.45 blk/s** (n=4, stdev 5.17; min 289.58 max 302.42); window 600k-900k; ledger `CAMPAIGN=postsapling` | `campaign` | `lab_monitor` + ledger | `REPORT-postsapling.md` |
| M-BOOT-POSTSAP | stock bootstrap rematch | **mean 300.15 blk/s** (n=4, stdev 0.96; min 298.80 max 301.20); window 600k-900k; ledger `CAMPAIGN=bootstrap-postsap`; **parity** with M-RX-POSTSAP-STOCK | `campaign` | `lab_monitor` | `REPORT-bootstrap-postsap.md` |
| M-BOOT-ONSET | stock bootstrap Sapling-onset | **129.87 blk/s** (n=1); window 490k-520k; ledger `CAMPAIGN=sapling-onset`; slower than deep post-Sap (~300) -- dual Sprout+Sapling load (see M-DENS-ONSET-*) | `campaign` | `lab_monitor` | `REPORT-sapling-onset.md` |
| M-RX-ONSET | stock reindex Sapling-onset | **140.19 blk/s** (n=1); window 490k-520k; ledger `CAMPAIGN=reindex-onset`; peer M-BOOT-ONSET (~parity; both ~2x slower than deep post-Sap ~300) | `campaign` | `lab_monitor` | `REPORT-reindex-onset.md` |
| M-MINE-REGTEST-SMOKE | regtest `generate` (48,5) | **8** blocks in **1 s** wall (~125 ms/blk wall); util sampled; solve too cheap for Instruments-grade ms -- smoke for BENCH-MINE env | `campaign` | `lab_monitor` | `test-logs/mine-20260812T153357Z/` |
| M-MINE-NEON-PROBE | arm64 stock binary | `hw.optional.neon=1`; `blake2b_compress_ref` present; `blake2b_compress_neon=0`; `ZERO_PERF_NEON_ZEROD` unset | `spot` | `nm`/`sysctl` | `neon-probe.txt` |
| *(none yet)* | mainnet (192,7) timed solve | **Scheduled -- Track M / G5** -- `MINE_MAINNET_SOLVE=1` + Instruments; harness stub only (`run_mine_bench.sh mainnet-template`) | -- | -- | Perf §0.9 / §0.16 |
| M-WAL-SYNC-P0 | wallet profile0 + tiny `-reindex` | tip **187417** in ~198 s (~**950** blk/s class); RSS **104->408 MiB**; wallet **106496** B flat; txcount **0** | `campaign` | `lab_monitor` | `test-logs/walletsync-20260812T153358Z/util.tsv` |
| M-WAL-SYNC-P1 | wallet profile1 + tiny `-reindex` | tip **187417** in **~201 s** (~**918** blk/s from h~2.8k); RSS **~103->398 MiB**; wallet **237568** B flat; txcount **133**; note_tx **0** -- near P0; no witness hotspot expected | `campaign` | `lab_monitor` | `test-logs/walletsync-20260813T055703Z/` |
| M-WAL-SYNC-FAT | fat wallet + tiny `-reindex` | tip **187417** in **~2.75 h** (~**19 blk/s**); wallet **785457152** B flat; txcount **801619**; RSS ~0.7->1.5 GiB -- **~50x** slower than M-WAL-SYNC-P0; util.tsv stalled mid-run (getwalletinfo vs cs_wallet) -- wall from debug.log tip + mid-run captures | `campaign` | `lab_monitor` + `xctrace` | `test-logs/walletsync-20260812T174850Z/`; CPU `test-logs/walletsync-fat-cpu-20260812T194107Z/` + `archives/…tar.gz` |
| M-CPU-WAL-FAT | fat wallet mid-sync Time Profiler | 5 sync windows h **133k–181k**: loadblk **~99.7%**; after G0b needles `witness_cache` **~97%**, `wallet_add_ordered` **~0.03%**; tip idle. blk/s **~20–21** flat | `campaign` | `xctrace` + `bucket_profile.py` | `test-logs/walletsync-fat-cpu-20260812T194107Z/`; rebucket `capture_005/buckets_ALL_g0b.txt` |
| M-WAL-NOTE-DENS | fat golden note density | **note_tx 1403 / txcount 801619 (0.175%)**; sprout **0**; sapling **1403** | `spot` | `cli` getwalletinfo | `test-logs/g0c-note-density/` |
| M-WAL-WITNESS-IBD-AB | `-walletwitness=ibd-defer` A/B | fat tiny to h~15k: stock **16.75** vs defer **595** blk/s (~**35x**) | `campaign` | `lab_monitor` | `test-logs/g0d-witness-ibd-ab/SUMMARY.txt` |
| M-WAL-WITNESS-NOTEIDX-AB | `-walletwitnessnote=1` A/B | fat tiny to h~8k: stock **14.86** vs noteidx **485.7** blk/s (~**33x**); no ibd-defer | `campaign` | `lab_monitor` | `test-logs/g0-noteidx-ab/SUMMARY.txt` |
| M-WAL-DIRTY-CONT | INV-DIRTY-CONT stock+NOTEIDX+stats | tiny to h~11k: `scan_txs=1403`/`mapWallet=801619`; **note_visits=0** (all notes Sapling, tiny pre-Sap) -- early_continue **N/A** on this band | `spot` | `lab_monitor` | `test-logs/witness-lab-dirty-cont-20260813T041447Z/` |
| M-WAL-WITNESS-REBUILD | BENCH-WIT-REBUILD defer ± NOTEIDX | tiny tip **187417**: import+defer wall ~**333 s** either flag; tip `RebuildWitnessCacheForChainTip` runs but **height walk skipped** (no notes at/below tip) -- walk perf needs post-Sap tip; e2e validates walk with notes | `campaign` | `lab_monitor` | `test-logs/witness-lab-rebuild*-20260813T*/` |
| M-WAL-WITNESS-TIP-AB | tip-only fat WIT height-walk ± NOTEIDX | tip **2518018**; rescan window startHeight **2516577** (~1441 blk): stock `scan_txs=801619` **7659 ms** vs note `scan_txs=1403` **220 ms** (~**35x**); `note_tx_count=1403`. Walk runs at end of wallet Rescan; `-walletwitness=rebuild` hook after. Requires rebuilt binary with `-walletwitnessnote` | `campaign` | `lab_monitor` | `test-logs/witness-lab-tip-rebuild-*-20260813T071*` |
| M-WAL-RESCAN-FAT | fat wallet `-rescan` from genesis (clears witnesses) | **Done.** `Rescanning last 2518691 blocks` 01:32:18 -> walk begin 13:24:38 UTC (~**11.9 h**, overall **~59 blk/s**). Fast h~98k-1.56M: **~1200-1650 blk/s**. Cliff h~**1601804** (Halving 2 / founders slot): **~19 blk/s** class to tip. End walk `startHeight=2505881` `tip=2518691` (~12.8k blk) `scan_txs=1403` `noteidx=1` **2009 ms**; P2P catch-up 2518692-2518993 **42 ms**; follow-tip **0-1 ms**. `Done loading` 13:24:44. txcount **801619** note_tx **1403**. **Not** ConnectBlock/Groth. Per-block `BuildWitnessCache(., true)` + `AddToWalletIfInvolvingMe`. `ibd-defer` does not apply | `campaign` | `lab_monitor` + `vmmap`/`iostat` | lab `debug.log`; `test-logs/rescan-sys-20260814T014246Z/` |
| M-WAL-RESCAN-FAT-CPU | Time Profiler during M-WAL-RESCAN-FAT | pre-sap h~288k-378k: `witness_cache` **82.2%**, Select **31%**. post-sap fast h~913k-985k: `witness_cache` **72.3%**, Select **27.5%**, `wallet_add_ordered` **14.1%**. slow h~1.708M and rematch h~1.753M: `witness_cache` **99.3-99.4%**, Select **97.6-97.9%** -- NOTEIDX Ensure after `AddToWallet` invalidate | `campaign` | `xctrace` + `bucket_profile.py` | `test-logs/rescan-xctrace-20260814T013547Z/`; `...-postsap-.../`; `...-slow-20260814T032423Z/`; `...-slow2-20260814T040320Z/` |
| M-GAD-FAT-TINY | tip-quiet getalldata fat@tiny tip | after `-walletwitness=rebuild`: datatype1 **~0.75 s**; datatype0/7d **~1.2 s**; resp ~3.5 KB -- **not** mainnet Idx1 UTXO load | `spot` | `cli_timer` | `test-logs/g0e-idx1-tip-util/` |
| M-RX-WINDOW | mid-chain window | e.g. **267.5 blk/s**; **~330 KB/s** (h 610k–626k) | `campaign` | `xctrace` + `debug_log` | `Perf.md` §2 |

Use case: ConnectBlock / disk / validation cost; compare only **same height window and wallet flags**.

### 3.2a Shielded density (era composition)

Offline height-band counts from `contrib/perf/shielded_density.py` (`reindex-profile/shielded-density.csv`). Sapling activation **492850**. Progress: fine rematch windows + coarse 400k bands to tip **done**.

| ID | Era | Result | Type | Tools | Source |
|----|-----|--------|------|-------|--------|
| M-DENS-PRESAP-50K75K | 50k-75k | blocks **25000**; sprout_js **7806**; sapling spend/out **0/0**; shielded_tx/block **0.312**; tx_total **37219** | `campaign` | `lab_monitor` (RPC+deserialize) | `shielded-density.csv` |
| M-DENS-ONSET-490K520K | 490k-520k | blocks **30000**; sapling spend/out **5717/5993**; sprout_js **22579**; shielded_tx/block **0.922**; sapling_tx **8388**; sprout_tx **19268** | `campaign` | same | `shielded-density.csv` |
| M-DENS-POSTSAP-600K900K | 600k-900k | blocks **300000**; sapling spend/out **131234/132852**; sprout_js **11486**; shielded_tx/block **0.650**; sapling_tx **185725**; sprout_tx **9281**; tx_total **576978** | `campaign` | same | `shielded-density.csv` |
| M-DENS-COARSE-0-400K | 0-399999 | blocks **400000**; sprout_js **196469**; sapling **0**; shielded_tx/block **0.466** | `campaign` | same | `shielded-density.csv` |
| M-DENS-COARSE-400K-ACT | 400000-492849 | blocks **92850**; sprout_js **79122**; sapling **0**; shielded_tx/block **0.758** | `campaign` | same | `shielded-density.csv` |
| M-DENS-COARSE-ACT-800K | 492850-799999 | blocks **307150**; sapling spend/out **106252/108002**; sprout_js **68978**; shielded_tx/block **0.688** | `campaign` | same | `shielded-density.csv` |
| M-DENS-COARSE-800K-1.2M | 800000-1199999 | blocks **400000**; sapling spend/out **189479/190755**; sprout_js **2437**; shielded_tx/block **0.658** | `campaign` | same | `shielded-density.csv` |
| M-DENS-COARSE-1.2M-1.6M | 1200000-1599999 | blocks **400000**; sapling spend/out **214533/216445**; sprout_js **122**; shielded_tx/block **0.695** | `campaign` | same | `shielded-density.csv` |
| M-DENS-COARSE-1.6M-2.0M | 1600000-1999999 | blocks **400000**; sapling spend/out **234435/234488**; sprout_js **0**; shielded_tx/block **0.701** | `campaign` | same | `shielded-density.csv` |
| M-DENS-COARSE-2.0M-2.4M | 2000000-2399999 | blocks **400000**; sapling spend/out **125616/127295**; sprout_js **4**; shielded_tx/block **0.383** | `campaign` | same | `shielded-density.csv` |
| M-DENS-COARSE-2.4M-TIP | 2400000-2516575 | blocks **116576**; sapling spend/out **31173/31351**; sprout_js **0**; shielded_tx/block **0.333** | `campaign` | same | `shielded-density.csv` |

**Note:** Zero `getblock` verbosity 2 omits shield arrays; scanner uses raw hex. Sprout JS dominates pre-Sap and early post-Sap, then falls to ~0 by 1.6M+. Sapling proofs/block peak mid post-Sap then tip density drops (~0.33-0.38 shielded_tx/block). Coarse tip scan **complete** (`DENSITY_SCAN_DONE`).

### 3.2b Equihash KATs

TST-05 vectors under `contrib/perf/kats/` (repo-root copies accepted). Tests: `equihash_tests` green.

| Artifact | Params | Role |
|----------|--------|------|
| `1927EQ.txt` | (192,7) mainnet genesis | 128 indices + nNonce/nSolution; header-form |
| `1927EQ_h1.hex` | (192,7) height 1 | Full block hex |
| In-test regtest genesis | (48,5) | Validator + solver cases |

**Decision:** archive for reuse. **Postponed (G9):** further adapt/extra validate tests.

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
| M-CPU-WAL0-TINY | wallet0 + tiny `-reindex` Time Profiler | Two 75s captures (h **2.4k-94k**, **100k-184k**); loadblk **~87%** process; buckets (loadblk): field/pairing-class **~42%**, Equihash **~28%**, disk **~17%**, tree **~13%**, wallet_add **~0.2%**; top leaves `Fr::mul_assign` ~37%, `blake2b_compress_ref` ~18% -- **pre-Sap**: do not call field math Sapling Groth16 | `campaign` | `xctrace` + `bucket_profile.py` | `test-logs/wallet0-cpu-profile-20260812T163014Z/` |

Use case: prioritize Groth16 batching vs disk vs Equihash; filter thread `zcash-loadblk` / import thread. Pre-Sap profiles need jubjub/needle discipline (Perf G1 SOP).

### 3.4 Memory

Long-interval leak screen and allocation attribution. Prefer **Writable regions** over Physical footprint when compression varies (macOS). Tools: `vmmap -summary`, `heap`, `MallocStackLogging=1` + `malloc_history -callTree`. Method detail: **Perf.md** §7.

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|------|-------|--------|
| M-MEM-VMMAP | `vmmap` checkpoints vs height | Six points h **278072 → 2470587**: Physical **535M → 3.1G**; Writable **702M → 4.7G**; compressed share uneven (0–71%) | `campaign` | `vmmap` | `Perf.md` §7 table |
| M-MEM-TIP | tip footprint | Physical **~3.1G**, Writable **~4.7G** @ h **~2.47M** (same sweep end) | `campaign` | `vmmap` | `Perf.md` §7 |
| M-MEM-GROWTH | Writable KB/block (segments) | Rough **~1–3 KB/block**; noisy; **no accelerating leak signature** -- linear with chain length | `campaign` | `vmmap` | derived from M-MEM-VMMAP |
| M-MEM-HEAP | `heap` size-class census | Used as live census during reindex; no separate archived class table | `capability` / `spot` | `heap` | `Perf.md` §7 method |
| M-MEM-ALLOC | `malloc_history` window | Window ~h **20198→501321**, ~673 s stack-logged; ~**987 MiB** tracked; **ThreadImport ~90%+**; **AddToBlockIndex ~66%** (~589 MiB); Flush/BatchWrite ~18%+; nullifier/UTXO cache ~8%; Groth16 verify **0** heap frames | `campaign` | `malloc_stack` | `Perf.md` §7–8 |
| M-MEM-PARAMS | zk params load | `librustzcash_init_zksnark_params` ~**58 MiB** (+ smaller) -- **startup once**, not per-block | `campaign` | `malloc_stack` | `Perf.md` §7 |
| M-MEM-SHIELDEX | static size | Shieldex fields **~176 B/block** ≈ **~435 MB** at tip | `estimate` | `none` | `Perf.md` §8.2 |

**Comparability:** Physical footprint alone can fake a "slowing growth" story under compressor pressure; use Writable (M-MEM-GROWTH / M-MEM-VMMAP) for leak claims. Stack-logging window straddles Sapling activation; a pure post-Sap `malloc_history` pass was skipped as unlikely to change the qualitative read (Groth16 verify still 0 heap; AddToBlockIndex unrelated to Sapling).

### 3.5 Cache / dbcache / RPC micro-latency

| ID | Metric | Result | Type | Tools | Source |
|----|--------|--------|--------|-------|--------|
| M-CACHE-MATRIX | budgets + p50 | e.g. dbcache **800** off: **100/183/517** MiB; generate(100) p50 **~835 ms**; getdbinfo **~4.3 ms** | `repro` | `cli_timer` + `debug_log` | `contrib/measure_dbcache_utxo.py`; ZeroStruct §4.3.4; TEST_ZERO |
| M-CACHE-2500 | longer mine | peak UTXO **0.1 MiB / 500** entries; tip txouts **3000** | `campaign` | same | TEST_ZERO sample `20260725_193336` |
| M-CACHE-MAIN | insight mainnet spot (`env=insight`) | BI/CS/UTXO **600/58/142**; tip cache **~77 MiB**; do not apply to non-insight wallet hosts | `spot` | `debug_log` | ZeroStruct §4.3.1 |

Use case for M-CACHE-MATRIX / M-CACHE-2500: cache sizing on a wallet / non-insight host. Do not apply M-CACHE-MAIN budgets there.

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
| Insight / explorer host | M-RX-LONGHAUL, M-CACHE-MAIN, M-RX-FULL-CLASS | Own deployment sizing; do not blend with wallet-node rows |
| Performance optimization (ConnectBlock) | M-CPU-*, M-RX-POSTSAP-*, M-BOOT-* | Groth16 vs disk vs Equihash priority |
| Short-snap CI / lab | M-RX-TINY*, M-RX-SHORT* | Fast ConnectBlock smoke without full tip |
| VPS dbcache tuning (non-insight) | M-CACHE-MATRIX, M-CACHE-2500 | 800 vs 2048 vs 4096 |
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

## 6. Comparability rules

| Topic | Conflict | Resolution |
|-------|----------|------------|
| Tip reindex hours | Estimate **8-10 h** / sync **6-10 h** vs longhaul **~2.6 h** | Different ops (IBD vs local reindex; wallet on/off; insight). Record those fields; do not collapse to one tip time |
| blk/s by era | ~**1100** pre-Sapling vs ~**250-310** post-Sapling vs ~**282** whole-chain vs short-snap ~**900** h/s | Same metric, different height/content. Compare **same window** only |
| CPU buckets | Legacy **58% "tree"** vs Groth16 **48-61%** | Prefer post-correction; mark legacy superseded |
| Memory growth | Physical footprint "slows"; Writable regions linear | Prefer Writable (M-MEM-VMMAP / M-MEM-GROWTH); Physical confounded by compressor |
| `--all` wall | **1275 s** (stale) vs **1063 s** | Prefer dated M-H-ALL row |
| walletbackup | Guess **15-25 min** vs measured **~80 s** | Prefer measured M-H-WB |
| Insight vs wallet host | Insight dbcache/tip times vs validator+wallet | Tag `env=insight` on insight rows; never size a non-insight wallet host from them |

Correctness vs throughput are separate questions: fd-cache **99.9%** hits (latch works) is not an A/B blk/s win (M-CPU-FD-THR **null**). Keep distinct `metric` rows.

---

## 7. Duration extraction

Shipped filter-then-process path: `contrib/perf/extract_measures.py` (plus `run_tiny_baseline.sh`, `run_postsapling_baseline.sh`, `accumulate_bench.py`). Outputs under `test-logs/` / `reindex-profile/bench-summaries/` (gitignored). Launch recipes: **contrib/perf/README.md**. Non-blocking extractor extensions: **Perf.md** §0.13 harness notes.

### 7.1 Pipeline

1. **Filter** -- keep-list of `log_marker` keys; drop or 1/N-sample `update_tip`.
2. **Segment** -- split runs on process start; attach settings (`-reindex`, insight, dbcache) from nearby lines or companion `meta.env`.
3. **Duration** -- emit JSONL events, then reduce to rows:

```text
{"run_id":"…","op_class":"reindex","metric":"height_per_s","value":897.8,"unit":"h/s","height_start":0,"height_end":245992,"wall_s":274,"tools":"debug_log","type":"campaign","source":"AtHeight.md"}
```

4. **Present** -- markdown tables generated from JSONL; do not hand-copy numbers without `run_id`.

### 7.2 Accuracy

- Timestamps: parse debug.log clock; for xctrace, correlate `--toc` start-date to UTC UpdateTip (**Perf.md** §1).
- Rates: `(h1-h0)/(t1-t0)` from first/last UpdateTip in window; reject clock skew or tip stalls.
- Always record: wallet on/off, `dbcache`, `height_start/end`, host OS/CPU, binary version; tag `env=insight` when that deployment is in use.
- Soft RPC ages (drain) are not ConnectBlock rates -- keep `op_class` distinct.
- Prefer stock markers for cross-host tooling; gate `zero_perf` / xctrace as optional enrichments.

### 7.3 Layers

| Layer | Format |
|-------|--------|
| Operator | Markdown tables here / stable rows in TEST_ZERO |
| Tooling | JSONL under `test-logs/` or `reindex-profile/` |
| Summary | CSV: `run_id,op_class,metric,value,unit,height_start,height_end,wall_s,tools,type,source` |

### 7.4 Highest-value missing extractions

1. Witness rebuild wall from `building_witnesses` first/last (M-WIT-LOG gap).
2. Init: `init_message` sequence through `init_done_loading`, then catch-up until tip quiet.
3. Reindex: `reindex_source` -> `reindex_finished` (+ per-file when logged).
4. Optional `-debug=bench` into the same JSONL schema.
5. Unify AtHeight / out-of-tree lab CSV into this schema.

---

## 8. Ledger campaigns

`accumulate_bench.py` stores `CAMPAIGN=` strings in `reindex-profile/bench-summaries/ledger.*`. Cite numbers only through the bound **`M-*`** ID. How to run a campaign: **Perf.md** §0.13 + **contrib/perf/README.md**.

| Ledger `CAMPAIGN=` | Mode | Window | Bound `M-*` | Notes |
|--------------------|------|--------|-------------|-------|
| `postsapling` | reindex stock | 600k-900k | M-RX-POSTSAP-STOCK | Primary post-Sap reindex baseline |
| `postsapling-historical` | reindex FDCACHE-era | 600k-900k | M-RX-POSTSAP-AB | Historical A/B; not current mix |
| `bootstrap-presap` | bootstrap stock | 50k-75k | M-BOOT-PRESAP | Peer M-RX-PRESAP |
| `bootstrap-new-20260813` | bootstrap stock | 50k-75k | M-BOOT-NEW-20260813 | Regenerated Zero400 bootstrap.dat smoke |
| `reindex-presap` | reindex stock | 50k-75k | M-RX-PRESAP | Peer M-BOOT-PRESAP |
| `bootstrap-postsap` | bootstrap stock | 600k-900k | M-BOOT-POSTSAP | Peer M-RX-POSTSAP-STOCK; **parity** |
| `bootstrap-smoke` | bootstrap stock | 50k-75k | M-BOOT-SMOKE-20260811 | Superseded; contended |
| `util-smoke` | reindex stock | 50k-75k | M-RX-UTIL-SMOKE | util.tsv on |
| `sapling-onset` | bootstrap stock | 490k-520k | M-BOOT-ONSET | Stage 1; n=1 |
| `reindex-onset` | reindex stock | 490k-520k | M-RX-ONSET | Stage 1 peer to M-BOOT-ONSET; n=1 |
| `mine-equihash-regtest` | regtest generate | (48,5) | M-MINE-REGTEST-SMOKE | BENCH-MINE env smoke |
| `mine-equihash-neon-probe` | probe | arm64 | M-MINE-NEON-PROBE | NEON A/B gated on NEON zerod |
| `wallet-sync-profile0` | reindex + wallet | tiny tip | M-WAL-SYNC-P0 | Dev wallet profile0; no host paths |
| `wallet-sync-profile1` | reindex + wallet | tiny tip | M-WAL-SYNC-P1 | Mid-size personal; txcount 133; note_tx 0; near P0 |
| `wallet-sync-fat` | reindex + fat wallet | tiny tip | M-WAL-SYNC-FAT, M-CPU-WAL-FAT | Done; FINDINGS + archive `walletsync-fat-g0-20260812.tar.gz`; Perf §0.14 |
| `witness-tip-rebuild` | tip template + fat wallet | tip 2518018 | M-WAL-WITNESS-TIP-AB | `tip-rebuild` / `tip-rebuild-note`; insight flags required |
| `wallet-rescan-fat` | `-rescan` + fat wallet | genesis to live tip | M-WAL-RESCAN-FAT, M-WAL-RESCAN-FAT-CPU | **Done** (~11.9 h). Clears witnesses; per-block Verify not ChainTip; NOTEIDX stale storm; end walk 2.0 s |
| `cycle-1` / `cycle-2` / `cycle-3` | wallet x op rematch | tiny / window / tip | assigned when first measured | `run_cycle_campaign.sh`; collate `collate_cycle.py`; one trial per invocation |

Unmeasured work (Idx1 tip getalldata, mainnet 192,7 solve Instruments **scheduled G5**, FDCACHE 8/16KB, optional onset n=4) gets an `M-*` when first measured. **Postponed:** NEON A/B (G7), Halo/Orchard notes body (G8), KAT adapt tests (G9). Groth G2/G3 consecutive after G5/G9 slot.

**Cross-campaign notes**

- Pre-Sap 50k-75k: M-BOOT-PRESAP vs M-RX-PRESAP in the same band; M-RX-UTIL-SMOKE n=1 sits inside.
- Post-Sap 600k-900k: M-BOOT-POSTSAP vs M-RX-POSTSAP-STOCK -- bootstrap ≈ reindex.
- Sapling-onset 490k-520k: M-BOOT-ONSET **~130** vs M-RX-ONSET **~140 blk/s** (n=1 each) -- ~parity; both ~2x slower than deep post-Sap ~300; density M-DENS-ONSET shows dual Sprout+Sapling load. Coarse density tip-complete.
- Wallet tiny reindex: M-WAL-SYNC-P0 (~950 blk/s, empty) vs M-WAL-SYNC-P1 (~918 blk/s, txcount 133, note_tx 0) vs M-WAL-SYNC-FAT (~19 blk/s, ~800k txs, ~50x) -- fat hotspot is per-block Verify (M-CPU-WAL-FAT), not OrderedTxItems. Mitigations: ibd-defer ~35x; **NOTEIDX** ~33x at 0.175% note-tx density. RPC `-33` on full rebuild with status allowlist -- Perf §0.14/§0.16.
- Fat `-rescan` (M-WAL-RESCAN-FAT): **finished** genesis to tip **2518691** in ~**11.9 h** (overall ~**59 blk/s**). Fast ~1.2k-1.6k blk/s to h~1.56M, then **~19 blk/s** from h~1.601M (Select **~98%**, M-WAL-RESCAN-FAT-CPU). End height-walk **2.0 s** (~12.8k blk, NOTEIDX hot); not the wall. Not comparable to ConnectBlock reindex. Cause: NOTEIDX Ensure after unconditional `AddToWallet` invalidate (FIX-WAL-WITNESS-NOTEIDX-STALE). `ibd-defer` does not apply (`ScanForWalletTransactions`, not ChainTip IBD).
- M-RX-TINY-20260811d / M-RX-SHORT-20260811b ran under host contention with long bootstrap; not clean solo baselines.
