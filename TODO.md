# TODO

Status and tracked work items for the Zero node.

---

## Ordered next (execution priority)

1. **WAL-WTXORDERED** (+ Assure-4) -- incremental `wtxOrdered`; primary wallet CPU fix. Orthogonal to **`txindex`** / insight (different store; see **ZeroStruct** §13.4.2). Measure via microbench / ZeroPerf retarget, not full insight reindex. Alternate only: **WAL-PIRATE-TIMESMART**.
2. Consensus integer math (**CON-02**) -- **accepted:** TENT-style **`vFoundersReward`** + integer `* 75 / 1000` via `GetFoundersRewardAmount`; naming reconcile later (**DOC-FR-NAMING**). Sites **UpdateZero** CON-02.
3. **TST-01** (scenario depth) / **TST-05** ((192,7)+(48,5) KATs; drop (96,5)) / **TST-03** -- remaining harness gaps. **TST-09** alert half **done** (default skip); block/wallet notify still open. **TST-07** carved: partition + walletbackup closed; sapling root separate.
4. **WAL-LOCKEDPOOL** / **OPS-CACHE-METRICS** / **OPS-TXINDEX-DEFAULT** / **OPS-AT-HEIGHT** / **TST-WITNESS-REINDEX** / **OPS-REINDEX** remainder / **OPS-ALERT-STRIP** / **DOC-FR-NAMING** -- postponed (see Pending).
5. **FR-ROTATE / FR-TADDR / FR-Z** -- product/consensus; explain **ZeroStruct** §13.8. Not scheduled.
6. **WAL-RPC-ACCOUNTS** -- business decision + code-risk analysis; independent of WAL-WTXORDERED and of founders type.
7. Release / docs track -- README merge, signing, macOS notarization, Linux RC, supply review, etc. (Active list).

## Active

- README rewrite: merge README0.md in
- Node setup and maintenance docs: validate all user-facing instructions
- Release signing: establish checksum and signing procedure.
- Chain bootstrap: document end-user import path (`-loadblock` / auto-import); linearize tool fixed in **`contrib/linearize/`** (commit **`f66b8b52b`**).
- macOS developer signing (codesign + notarization).
- Total supply discrepancy: review arithmetic vs project target of some 20M ZER.
- Consensus integer math (**CON-02**): shared helper returning TENT-style **`vFoundersReward`** with **`subsidy * 75 / 1000`**; also integerize `10.8 * COIN`. See **UpdateZero** CON-02.
- RPC coverage matrix: audit script cross-ref **`RPCs.csv`** (`zero=y`) vs harness depth + client grep; output **`RPCs_extended.csv`** columns or **`RPC_coverage.csv`** (**ZeroStruct.md** section **6.3**).
- TST-01 -- **param skeletons PASS** (`rpc_zero_exclusive_tests` / `rpc_zero_experimental_tests`, rechecked 2026-07-22). Still open: scenario depth for **`getalldata`** first, then **`getsupply`** / **`zs_*`** / sapling experimental RPCs (**`UpdateZero.md`** TST-01).
- TST-03 -- **`zeronodestats`** + zeronode/budget subcmds with no harness hit (**`startzeronode`**, **`zeronodecurrent`**, **`getzeronodeoutputs`**, **`znbudget*`**); arg validation first, integration optional.
- TST-05 -- **(96,5) dropped**. Genesis **(192,7)** indices saved in repo-root **`1927EQ.txt`** (regenerate: `DUMP_1927EQ=./1927EQ.txt ./src/test/test_bitcoin --run_test=equihash_tests/dump_mainnet_genesis_192_7_indices`). Still open: wire into Boost cases + **(48,5)** index KATs.
- ~~TST-07-partition~~ / ~~TST-07-walletbackup~~ -- **done**. Sapling header script = **TST-SAPLING-ROOT** (`finalsaplingroot.py`, still Bfail).
- TST-09 -- **alertnotify acceptance = PASS** (`DeprecationTest.AlertNotify`: default build, 0 side-effect lines / skip path). Still open: **`-blocknotify`** / **`-walletnotify`** only. Full **`alert.cpp`** strip = **OPS-ALERT-STRIP** (postponed).
- WAL-WTXORDERED -- review further; detail **ZeroStruct** §13.4.2–13.4.3 (incl. relation to **`txindex`**). Port incremental `wtxOrdered` (keep accounts / `TxPair`). Sync erase/reorder: `EraseFromWallet`, `DeleteTransactions`, `ReorderWalletTransactions`, `UpdateWalletTransactionOrder` (also TENT, Pirate, PirateOcean). **Includes Assure-4:** delete then assert `wtxOrdered` ≡ `mapWallet` (same PR as the port). Measure: wallet microbench / ZeroPerf retarget -- not full insight reindex. Alternate: **WAL-PIRATE-TIMESMART**.
- WAL-RPC-ACCOUNTS -- postponed; business decision whether to drop obsolete account RPCs **plus separate code-risk analysis** (BDB acentry, callers, help) -- **ZeroStruct** §13.4.2. Independent of WAL-WTXORDERED.
- WAL-PIRATE-TIMESMART -- postponed track; Pirate skips `OrderedTxItems` on insert by setting both times to blocktime (**ZeroStruct** §13.4.2).
- WAL-LOCKEDPOOL -- postponed; port LockedPool + optional `getmemoryinfo`; Zero has only `GetLockedPageCount()` (**ZeroStruct** §4.3.2a).
- ~~OPS-REINDEX-MARKERS~~ / ~~OPS-REINDEX-RESUME~~ -- **done** (write + consume `L`/`H`, telemetry; **ZeroStruct** §13.2).
- ~~OPS-DEV-UTXO~~ -- **done** 2026-07-22: local `getaddressutxos` dumps `~/Work/ZK/0/E/DevFeeWallets/data/founders_utxo_0{1,2,3}.tsv` (+ summaries).
- ~~OPS-PIRATE-DB~~ -- **done** (`max_open_files` **64→256** in `src/dbwrapper.cpp`; **ZeroStruct** §13.3). Compression / Pirate 1000 / per-DB knobs still optional.
- ~~OPS-CACHE~~ -- **done** (Linux VPS status + measured split: **ZeroStruct** §4.3.1–4.3.2). Tunable 75% / hit-miss = **OPS-CACHE-METRICS** (postponed).
- ~~OPS-BOOTSTRAP-DOC~~ -- **done** (**ZeroStruct** §13.7).
- ~~PERF-TREE~~ -- **decided** 2026-07-22: keep **ZeroPerf** (`~/Work/ZK/ZeroPerf`, `Perf.md`) as a **separate** experiment tree; measure tip on Zero400; port ops (resume/snaps/monitors) into the perf lab as needed; land speed patches in Zero400 only after Linux/Windows A/B. Groth16 batch A vs B still open in ZeroPerf.
- macOS datadir: zerowallet400 should use **`Application Support/zero/`** (match **`GetDefaultDataDir`**); wallet currently uses **`Zero/`** (**ZeroStruct.md** **INT-01**).
- GTest fixes done 2026-06-09: **`CachedWitnesses*`** ported (harness merkle/commitment roots; Zero decrement semantics) except **`CleanIndex`** -- postponed under **TST-WITNESS-REINDEX** / **WitnessReindex.md** (prefer `reindex_shielded.py`); **`WriteCryptedSaplingZkey*`** / **`rpc_wallet_encrypted_wallet_sapzkeys`** encrypt-hang class fixed -- back in default gate
- Fuzz harness setup

## Pending

- OPS-REINDEX (remainder) -- **postponed** as one track: refuse / `-reindexforce` (**OPS-REINDEX-CONF**); SKIP-wallet below H (**OPS-REINDEX-SKIP**). Loud warn + markers + resume already shipped (**ZeroStruct** §13.1–13.2).
- OPS-ALERT-STRIP -- postponed; remove or gut P2P **`alert.cpp`** / unused alert relay after TST-09 slim. Keep **`-alertnotify`** help + deprecation skip path until then (Bitcoin removed P2P alerts but kept the hook; Zcash still has both).
- DOC-FR-NAMING -- postponed (**accepted** to defer); reconcile **FoundersReward** / **`vFoundersReward`** (code; CON-02) vs **developmentfee** (product RPC) vs docs/site. Keep **`nFeeStartBlockHeight`** (22 refs -- all carve/subsidy-step gates; see **TEST_ZERO**). Optional: dual-key RPC aliases.
- TST-SAPLING-ROOT -- postponed/Bfail; `finalsaplingroot.py` maturity port (was limbo under TST-07).
- TST-WITNESS-REINDEX -- postponed; hub **WitnessReindex.md** (proposed `reindex_shielded.py`, CleanIndex gtest B2, witness assert hardening C). RCA: **ExtTests.md** §1.
- OPS-CACHE-METRICS -- postponed; tunable 75% insight split + optional hit/miss (**ZeroStruct** §4.3).
- OPS-TXINDEX-DEFAULT -- postponed; see Active note / ZeroStruct §13.1.
- OPS-AT-HEIGHT -- postponed; height-bounded reindex/bootstrap findings in **AtHeight.md** (no `-stopatheight` in Zero; short snap + linearize `max_height`; ecosystem note). Implementation (daemon stop-at-height or further tooling) not scheduled.
- ~~EXT-INSIGHT-FIXTURES~~ -- **done 2026-07-22**; five insight RPC scripts in Tier B pass (`rpc-tests.sh`).
- EXT-INSIGHT-SUPERSET -- postponed; ExtTests §5 (founders / fee-start index coverage).
- `txindex.py` -- inventoried **Bfail Debug** 2026-07-22 (was orphan); Py3 Decimal + Bitcoin 50-ZER asserts; failures/fixes in **TEST_ZERO.md**; promote after green (not Insight substitute).
- OPS-AT-HEIGHT ops recipe -- **AtHeight.md** §4.1 (short/tiny snap unpack + resume interrupt); daemon `-stopatheight` still postponed.
- FR-ROTATE / FR-TADDR / FR-Z -- postponed; detail **ZeroStruct** §13.8.
- **v4.0.1 Linux RC (lazu / `ZeroLinux`):** macOS **`--strict`** PASS 2026-06-09. Linux rebuild + validation **strongly recommended** before tag/merge; **`--strict` is not an automatic release block** -- maintainer decides. See **TEST_ZERO.md** section **4.0.1 handoff** and **BUILD_ZERO.md** section **2.2a**.
  1. Reclaim disk on lazu (**~4 GB** free on **`/`** is tight; need several GB for depends + objects).
  2. `cd /home/ubuntu/Work/ZK/ZeroLinux && git fetch && git checkout zero-400names && git pull --ff-only`
  3. `./zcutil/fetch-params.sh` (if params missing)
  4. `./zcutil/build.sh -j2`
  5. Recommended: `./contrib/run-tests.sh --strict` (then optional **`--suite`**)
  6. Tag **`v4.0.1`** / merge when maintainer accepts risk if gate skipped or partial
- ~~**`blockchain.py` vs cache:**~~ done 2026-06-09: `gettxoutsetinfo` expectations now derived from actual tip via regtest subsidy schedule; passes at fresh (200) and warm (725) cache.
- P2P logging (postponed): remove misleading `Unknown command` log after zeronode extension dispatch (`src/main.cpp` ~7025-7033). Valid commands (`znp`, `znb`, `znget`, `dseg`, spork, etc.) are handled in `znodeman` / budget / payments subsystems but still log when `-debug=net`. See **`ZeroNodeDev.md`** section **9**; `notfound` already has a no-log exception.
- macOS libtool `-bind_at_load` warning (postponed): export **`MACOSX_DEPLOYMENT_TARGET=15.0`** from the build system so manual **`make`** matches **`./zcutil/build.sh`**; workaround **`export MACOSX_DEPLOYMENT_TARGET=15.0`**. See **`UpdateZero.md`** **DEF-08**.
- Params archival: audit `fetch-params.sh` file names and URLs.
- Build validation: Windows hardening flag gap identified
- Branch id posture: CI guard for duplicate `nBranchId` (Sapling/Cosmos share `0x7361707a`).
- getrawtransaction size/fees
- OpenSSL: remain on 1.1.1w until audited 3.x or removal.
- SwiftTX removal: strip unused instant-confirmation code and hidden options.
- Release branch cleanup: fifteen branches redundant with tags.
- Debian packaging: confirm `build-debian-package.sh` superseded by `release-linux.sh`.
- GitHub org cleanup: archive ~37 obsolete repos; retire wiki Node Setup page.

## Completed

- ZERO_COIN.md: chain economics consolidated.
- `rescan_import.py` executable bit.
- `run-tests.sh` background jobs: child exit codes corrected.
- `getchaintips` RPC test: split topology, CHAIN_BOOTSTRAP.
- Zeronode null guard: `CheckInputsAndAdd`.
- Iterator bug: `zeronodeman.cpp` erase order.
- `throw new std::runtime_error` removed from 5 sites.
- chainActive[] null deref: all sites guarded.
- zcrawreceive: legacy Sprout, no action needed.
- Rust: system default on all platforms; 1.32.0 legacy/CI only.
- librustzcash: pinned, consensus-linked, no upgrade without new NU.
- Legacy Proton build off by default (`NO_PROTON=1`); optional `src/amqp/` -- use ZMQ for pub/sub instead.
- Tag typos corrected (`v3.3.1`).
- `-port` help text: was Zcash defaults; fixed to 23801/23802.
- Stale code comments: `~/.zcash` -> `~/.zero`; collateral `1000` -> `10000`.
- Zeronode: `chainActive` negative height / reorg edge cases in SwiftTX and input-age cache.
- Decorative Unicode stripped from docs.
- **v4.0.1 macOS contributor gate:** `./contrib/run-tests.sh --strict` **PASS** (~211s, 2026-06-09); GTest/Boost + Tier A RPC; **`blockchain.py`** warm-cache fix; encrypt + **`CachedWitnesses*`** gate widened. Darwin skips ELF **`--suite`** security stages; not a substitute for Linux RC.
- **PIR-01 shipped:** **`ENABLE_SYSTEM_COMMAND`** compile gate on **`runCommand`**; default builds skip shell notify (**BUILD_ZERO.md** section **4.6.1**).
- **OPS-DEV-UTXO done** (2026-07-22): founders transparent UTXO TSVs via local `getaddressutxos`.
- **OPS-PIRATE-DB done** (2026-07-22): `max_open_files=256` in `dbwrapper.cpp`.
- **TST-07 wallet half:** `walletbackup.py` -> Tier B pass (2026-07-22).
- **PERF-TREE decided** (2026-07-22): ZeroPerf stays separate; see Active note.

---

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidelines.
