# TODO

Status and tracked work items for the Zero node.

---

## Ordered next (execution priority)

1. **OPS-DEV-UTXO** -- Dev/founders transparent UTXO inventory without fat wallet load. **Balances done** via public Insight scalars (`~/Work/ZK/0/E/DevFeeWallets/data/founders_utxo_summary.json`, ~379682 ZER across slots 1–3). **Full UTXO lists blocked:** public `/addrs/{addr}/utxo` returns **413** on active slots; local Mac `zerod` was down. Finish with `getaddressutxos` on an insight-enabled node (`-insightexplorer`, prefer `-disablewallet`).
2. **WAL-WTXORDERED** (+ Assure-4) -- incremental `wtxOrdered`; primary wallet CPU fix. Orthogonal to **`txindex`** / insight (different store; see **ZeroStruct** §13.4.2). Measure via microbench / ZeroPerf retarget, not full insight reindex. Alternate only: **WAL-PIRATE-TIMESMART**.
3. **EXT-INSIGHT-FIXTURES** -- promote adapted addressindex/spentindex scripts out of FailDebug.
4. **OPS-REINDEX-CONF** -- warn or one-shot if `reindex=1` in conf (ops footgun).
5. **OPS-PIRATE-DB** -- evaluate `max_open_files` 64→256 after FD evidence (**ZeroStruct** §13.3).
6. Consensus integer math -- replace `double`/`COIN` mixes in subsidy and founders paths.
7. **TST-01** / **TST-09** / **TST-03** -- RPC and shell-notify harness gaps (as listed under Active).
8. **OPS-REINDEX-RESUME** / **OPS-REINDEX-SKIP** -- consume markers / skip-wallet below H (write path already shipped).
9. **WAL-LOCKEDPOOL** / **OPS-CACHE-METRICS** / **OPS-TXINDEX-DEFAULT** -- postponed perf/ops polish.
10. **FR-ROTATE / FR-TADDR / FR-Z** -- product/consensus; explain **ZeroStruct** §13.8. Not scheduled.
11. **WAL-RPC-ACCOUNTS** -- business decision + code-risk analysis; independent of WAL-WTXORDERED and of founders type.
12. Release / docs track -- README merge, signing, macOS notarization, Linux RC, supply review, etc. (Active list).

## Active

- README rewrite: merge README0.md in
- Node setup and maintenance docs: validate all user-facing instructions
- Release signing: establish checksum and signing procedure.
- Chain bootstrap: document end-user import path (`-loadblock` / auto-import); linearize tool fixed in **`contrib/linearize/`** (commit **`f66b8b52b`**).
- macOS developer signing (codesign + notarization).
- Total supply discrepancy: review arithmetic vs project target of some 20M ZER.
- Consensus integer math: replace `double`/`COIN` mixes in subsidy and founders paths.
- RPC coverage matrix: audit script cross-ref **`RPCs.csv`** (`zero=y`) vs harness depth + client grep; output **`RPCs_extended.csv`** columns or **`RPC_coverage.csv`** (**ZeroStruct.md** section **6.3**).
- TST-01 scenario tests -- **`getalldata`** first (wallet UI shape: balances, addresses, txs after mine/spend); then **`getsupply`**, **`zs_*`** exclusive RPCs (**`UpdateZero.md`** TST-01; extend **`src/test/rpc_zero_exclusive_tests.cpp`** or regtest).
- TST-01 scenario tests -- **`getsaplingblocks`**, **`getsaplingwitness`**, **`getsaplingwitnessatheight`** (**`src/test/rpc_zero_experimental_tests.cpp`**; Insight uses these).
- TST-03 -- **`zeronodestats`** + zeronode/budget subcmds with no harness hit (**`startzeronode`**, **`zeronodecurrent`**, **`getzeronodeoutputs`**, **`znbudget*`**); arg validation first, integration optional.
- TST-09 -- shell notify **disabled** build (default): **`-blocknotify`**, **`-walletnotify`**, **`-alertnotify`** in conf must **not** run **`::system`**; side-effect files stay empty; **`debug.log`** contains skip message. **`-alertnotify`**: extend **`DeprecationTest.AlertNotify`** (already 0 lines). **`-blocknotify`** / **`-walletnotify`**: add GTest or regtest (mine/spend + marker file). Opt-in **`ENABLE_SYSTEM_COMMAND`** build: parity tests that hooks **do** run. **UpdateZero.md** TST-09; **BUILD_ZERO.md** section **4.6.1** (**OPS-SHELL**).
- WAL-WTXORDERED -- review further; detail **ZeroStruct** §13.4.2–13.4.3 (incl. relation to **`txindex`**). Port incremental `wtxOrdered` (keep accounts / `TxPair`). Sync erase/reorder: `EraseFromWallet`, `DeleteTransactions`, `ReorderWalletTransactions`, `UpdateWalletTransactionOrder` (also TENT, Pirate, PirateOcean). **Includes Assure-4:** delete then assert `wtxOrdered` ≡ `mapWallet` (same PR as the port). Measure: wallet microbench / ZeroPerf retarget -- not full insight reindex. Alternate: **WAL-PIRATE-TIMESMART**.
- WAL-RPC-ACCOUNTS -- postponed; business decision whether to drop obsolete account RPCs **plus separate code-risk analysis** (BDB acentry, callers, help) -- **ZeroStruct** §13.4.2. Independent of WAL-WTXORDERED.
- WAL-PIRATE-TIMESMART -- postponed track; Pirate skips `OrderedTxItems` on insert by setting both times to blocktime (**ZeroStruct** §13.4.2).
- WAL-LOCKEDPOOL -- postponed; port LockedPool + optional `getmemoryinfo`; Zero has only `GetLockedPageCount()` (**ZeroStruct** §4.3.2a).
- OPS-REINDEX-MARKERS -- **write shipped** (`LASTFILE` + `LASTBLOCK` after each blk file); consume postponed (**OPS-REINDEX-RESUME**).
- OPS-DEV-UTXO -- balances via Insight scalars written; full UTXO dump needs local `getaddressutxos` (public Insight 413 on slots 1–3). See Ordered next #1.
- ~~OPS-CACHE~~ -- **done** (Linux VPS status + measured split: **ZeroStruct** §4.3.1–4.3.2). Tunable 75% / hit-miss = **OPS-CACHE-METRICS** (postponed).
- ~~OPS-BOOTSTRAP-DOC~~ -- **done** (**ZeroStruct** §13.7).
- macOS datadir: zerowallet400 should use **`Application Support/zero/`** (match **`GetDefaultDataDir`**); wallet currently uses **`Zero/`** (**ZeroStruct.md** **INT-01**).
- GTest fixes done 2026-06-09: **`CachedWitnesses*`** ported (harness merkle/commitment roots; Zero decrement semantics) except **`CleanIndex`** (needs coins-view harness); **`WriteCryptedSaplingZkey*`** / **`rpc_wallet_encrypted_wallet_sapzkeys`** encrypt-hang class fixed (wallet-DB re-entry deadlock in `AddCryptedSaplingSpendingKey`) -- back in default gate
- Equihash (192,7) test vectors
- Fuzz harness setup

## Pending

- OPS-REINDEX-CONF -- postponed; warn or one-shot if `reindex=1` in conf.
- OPS-REINDEX-RESUME -- postponed; consume `LASTFILE`/`LASTBLOCK` (write path shipped).
- OPS-REINDEX-SKIP -- postponed; skip-wallet below H only (not skip-chain).
- OPS-PIRATE-DB -- postponed; evaluate LevelDB knobs; consider raising hardcoded `max_open_files` **64 → 256** (not necessarily Pirate's 1000) after FD/`lsof` evidence -- thrashing ≠ leak (**ZeroStruct** §13.3).
- OPS-CACHE-METRICS -- postponed; tunable 75% insight split + optional hit/miss.
- OPS-TXINDEX-DEFAULT -- postponed; see Active note / ZeroStruct §13.1.
- EXT-INSIGHT-FIXTURES -- scripts adapted to Zero settings (1-vout, maturity 720, halving-aware balances); verify/promote remaining. FR / fee-start=1000 = **EXT-INSIGHT-SUPERSET**.
- EXT-INSIGHT-SUPERSET -- postponed; ExtTests §5.
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
- Partition and wallet tests
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

---

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidelines.
