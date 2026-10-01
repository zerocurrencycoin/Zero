# UpdateZero

Maintainer planning for the Zero full node: the documentation map, fork rules, upstream cherry-pick catalogs, release targeting, open maintainer issues, and public-doc drafts. Checklist status (Ordered next, Active, Pending) is kept in **TODO.md**; this file holds the reasoning and catalogs behind those items.

## 1. Internal documentation map

This map covers the project's internal documents only; the public documents are listed in the README. Internal documents are held back from the next release merge into `master` and move to a separate maintainer branch afterwards. Public documents never refer to them; drafts for public documents (section **6**) are copied as plain text.

| Document | Owns |
|----------|------|
| UpdateZero.md | This map; fork rules (CON-); upstream catalogs (PIR-, TNT-); Linux binary floor; Blockbook; drafts; DOC-, REL-, TST-, DEF- detail; completed fixes (C-) |
| ZeroStruct.md | zerod data structures, caches, options by workload, client requirements, integration concerns (INT-) |
| ZeroNodes.md | Zeronode operator guide; source for the planned public operator section |
| ZeroNodeDev.md | Zeronode implementation and validation; tracking items ZN-01 and ZN-02 |
| WitnessReindex.md | Shielded witness rebuild coverage |
| AtHeight.md | Height-bounded reindex and bootstrap labs |
| ZcashFixes.md | Shielded-pool vulnerability history and Zero posture |
| ZebraZero.md | Zebra and Ycash reference and port options |

Removed in 4.1.0: ExtTests.md (superseded by TEST_ZERO) and `zcutil/check-host.sh` (former alias for `zcutil/check-setup.sh`). Documents kept outside this repository, referred to by name: Comparison.md (cross-fork source comparison, indexers, reorg family), ZeroC.md (zerocurrencycoin GitHub org audit), StatusTransitions.md (node readiness states and UI status map), and the Insight explorer runbooks (InsightBlock.md, InsightPort.md).

**ID prefixes.** Rules and statuses: TODO.md "Tracking rules". Items owned here: CON, PIR, TNT, DOC, REL, TST, DEF; ZeroNodeDev.md: ZN; ZeroStruct.md: INT.

**Scope rules.** Ubuntu 18.04 / glibc compatibility stays internal (section **3.6**) until its timeline relative to the next release is decided; public documents say only that the build OS sets the binary floor. Insight host installation is a specialty track, and Insight or bitcore pull requests are not node merge work. DevFee UTXO tooling and key inventory stay out of this repository.

---

## 2. Fork rules

What makes Zero different from upstream Zcash and Bitcoin. Review new code that touches these areas against this section.

### Consensus

**CON-03 -- Branch id.** Sapling and Cosmos both use `0x7361707a` in `src/consensus/upgrades.cpp`. This is accepted technical debt; no fork is planned to separate them. Revisit when planning a consensus fork.

**Zeronode layer.** `src/zeronode/` is a port of TENT's masternode code. All `chainActive` dereferences there are guarded against null and out-of-range heights (ZeroNodeDev.md section 4).

**Equihash.** Zero keeps libsodium's C `crypto_generichash_blake2b_state` for `eh_HashState` (192,7). A Rust/CXX bridge as in Zcash v6+ is out of scope unless the PoW stack changes.

**Subsidy.** `GetBlockSubsidy` returns integer zatoshis; founders are `GetFoundersRewardAmount(subsidy) = subsidy * 75 / 1000`, truncated. Miner, `ConnectBlock`, GBT, zeronode payments and budget, and metrics must change together; add far-future halving tests with any change. Open: supply against the ~20M ZER target (postponed; does not gate a release) and **DOC-FR-NAMING** (section **7**).

### Reorg bound

`MAX_REORG_LENGTH` is 99 and a deeper reorg shuts the node down; `COINBASE_MATURITY` is 720. Analysis and options: section **8.3**.

### Engineering policy

- **Numeric.** Consensus and subsidy paths are integer-only, truncating toward zero. No new `float` or `double` in consensus without review.
- **Height and expiry.** `TransactionBuilder::SetExpiryHeight` mixes `int` height with `uint32_t` expiry; use explicit casts or `int64_t` for heights in new code.
- **Exceptions.** Throw by value: `throw std::runtime_error("...")`. `throw new` throws a heap pointer that `catch (const std::exception&)` never frees. Regression check: `rg 'throw new' src --glob '*.cpp'` returns nothing.
- **Branding.** User-visible strings say ZERO; clean residual Zcash and Bitcoin names when touching a file.

### Witness path

Zero uses `VerifyAndSetInitialWitness` and `BuildWitnessCache` with an optional `pblockIn`, coupled to `pcoinsTip` and chain views (`src/wallet/wallet.cpp`). While `BuildWitnessCache` runs, `fBuildingWitnessCache` makes RPC return error **-33**.

---

## 3. Build notes and upstream catalogs

### 3.1 Source-tree fixes to preserve

These fixes are on the integration line; check that upstream merges do not revert them.

| Area | Fix |
|------|-----|
| `src/hash.h` | VLA replaced by `CSHA256::OUTPUT_SIZE`; Apple Clang rejects C++ VLAs |
| `configure.ac` | Strip `-lstdc++` from `ZMQ_LIBS` on Darwin (libc++ duplicate symbols) |
| `depends/packages/*` | `sed` via `build_SED_INPLACE` (`sed -i.old`) for BSD sed |
| `secp256k1/configure.ac` | `AC_PROG_CC` instead of the removed `AC_PROG_CC_C89` (Autoconf 2.72+) |
| `secp256k1/src/tests.c` | `shortkey` zero-initialized, silencing GCC `-Wmaybe-uninitialized` as upstream did |
| `zcutil/fzero.sh` | `cleanup_secp256k1_la()` removes a stale `secp256k1.la` when `HOST` changes |
| `Makefile.am` | `distcleancheck_listfiles = find . -false` is intentional |
| `zeronodeman.cpp` | `SliceHash` `memcpy` source pointer and two-map erase order corrected |
| `zeronode/spork.h` | `4070908800` (year 2099) is the intentional "spork off" value; `budget.cpp` uses `INT_MAX` likewise |

### 3.2 Using the upstream catalogs

Pirate (sections **3.4**, **5**) and TENT (section **3.5**) are separate catalogs. **Reject**, **Skip**, and **Keep current** rows are settled. **Port**, **Review**, **Hold**, **Defer**, and **Implement** rows compete with Zcash and Bitcoin ports and Zero-local work for the next TODO slot. Prefer the Zcash fix when one exists; use Pirate or TENT only as a zcashd-shaped diff reference, or where Zero regressed upstream behavior. Commit ids in the catalogs identify the upstream change to port.

### 3.3 Open build question

`--disable-mining` builds work because the Equihash solver instantiations in `src/equihash.cpp` and `test_miner.cpp` are compiled only with `ENABLE_MINING`; validators are always built. Undecided: whether to separate the solver known-answer tests from `ENABLE_MINING`, or add a `--disable-mining` CI build.

### 3.4 Pirate upstream candidates

Pirate (`PirateNetwork/pirate`) is Komodo assetchain C++ on the zcashd lineage, not a zeronode fork. Komodo-only consensus (notary seasons, KIP coinbase, `-ac_*` arguments) is rejected.

| ID | Area | Pirate change | Zero today | Decision |
|----|------|---------------|------------|----------|
| PIR-02 | Coin selection | `79383e0a7` knapsack early exit `nTotalLower > 4*nTargetValue + CENT` | Scans all UTXOs | **Port**; existing `wallet_tests` knapsack cases must pass unchanged |
| PIR-04 | Relay policy | `6fb6a2e2b` `fAcceptDatacarrier` and an `IsStandard` NULL_DATA check | `-datacarriersize` only | **Port (partial)**; keep `MAX_OP_RETURN_RELAY = 80` |
| PIR-05 | P2P DoS | `2bec27973` addr rate limit (Bitcoin `0d64b8f709`, Zcash PR 6477) | Absent | **Port** from Bitcoin or Zcash |
| PIR-06..08 | P2P | addrv2 (BIP155), ASMap, I2P/SAM | Absent | **Defer**; P2P epic after PIR-05, together with fixed seeds (REL-08) |
| PIR-14b | Wallet | `consolidateaddress`, dust modes | Automatic `-consolidation` only | **Review** (section **5**) |
| PIR-15 | Wallet lock | `02c8dff72` lock metadata RPCs while locked | Standard zcashd | **Review**; product decision |
| PIR-16 | Insight | `insight-api-pirate` tx v5 and Sapling support | Insight operational | Separate infrastructure track |

Settled: PIR-01 (`ENABLE_SYSTEM_COMMAND` gate) and PIR-03 (witness-rebuild lockout) are shipped. PIR-09..12 are **Skip**: no matching code in Zero. PIR-13 (RT_CST_RST difficulty) and PIR-14 (Komodo coinbase and notary) are **Reject**.

**Order:** PIR-02, PIR-05, then PIR-06..08.

### 3.5 TENT upstream candidates

TENT (`TENTOfficial/TENT`, inactive since 2021) is the direct upstream of Zero's zeronode code. In the port, wire messages `mn*` became `zn*`, the treasury output was removed, and `CZeronodeWalletInterface` was added. Use TENT only where Zero regressed TENT behavior or missed a later fix. Never copy TENT tokenomics, `SliceHash`, unbounded reorg following, or obfuscation `ProcessMessage`.

| ID | Area | Zero today | Decision |
|----|------|------------|----------|
| TNT-04 | Zeronode payee amount | Exact match (`==`); logs `OVERPAY` when a payee receives more than required | **Hold `>=`**; port only if OVERPAY lines appear (below) |
| TNT-07 | Testnet min-difficulty after height 13000 | None | Consensus decision |
| TNT-09 | LWMA3 difficulty | Zcash 17-block window | **Defer** |
| TNT-12 | Zeronode tests | Phases A, B, C (partial), E in tree | **Implement**; ZN-01 |
| TNT-13 | Operator setup scripts | None | ZN-01 |
| TNT-14 | libsnark `-march` (`db81202`) | Absent | Review only if a libsnark cross-build fails |
| TNT-18 | `AcceptableInputs`, the collateral-only ATMP copy in `main.cpp` | Reads `-relaypriority` / `-limitfreerelay` with looser defaults than ATMP | **Postpone**; the looser collateral path is deliberate. Do not merge the flags into one global. Resolve with the wider ATMP duplication question |
| TNT-19 | Budget proposal end block (`e082fd4`, `fb8e2c0`) | `nBlockEnd` computed as `start + cycle * count` in `rpc/zeronode-budget.cpp` and `(cycle + 1) * count` in `budget.cpp` | **Review** before any superblock activation; TENT moved to `start + cycle * count + 1`. Superblocks are off on mainnet |

Settled: TNT-01 done. TNT-02 and TNT-03 follow the reorg bound in section **2**. TNT-05 is **Skip** with a condition; TNT-06 is adopted:

- **TNT-05** -- TENT `3915ac3` fixed `sendtoaddress` / `sendmany` by making wallet coin selection ask `GetCoinbaseProtected(height)`, because TENT ends mandatory coinbase shielding at an upgrade height. Zero keeps a static `fCoinbaseMustBeProtected = true` on mainnet and testnet, so wallet and consensus already agree. Port only if Zero ever makes coinbase shielding height-dependent.
- **TNT-06** -- TENT `e3d39f1` separated zeronode list sync from chain sync in two RPC errors. Zero's `rpc/zeronode.cpp` reports "Zeronode list syncing, please wait. Current status: " followed by `GetSyncStatus()`. TNT-15 and TNT-17 are **Skip**; TNT-08, TNT-10, TNT-11, and TNT-16 are **Reject**.

Other post-port TENT changes were reviewed and are not needed: the block-size crash and rescan fixes depend on TENT's height-based size limits; the IBD latch fix is already equivalent in Zero; the collateral `nLockTime` change was reverted in TENT itself; the masternode score height change does not apply because Zero scores from a block hash; the collateral-constant refactor adds nothing for Zero's fixed 10000 ZER collateral.

**TNT-04 detail.** TENT `74bbde2` switched payee validation from `==` to `>=` while removing a height gate that Zero never had. Under `>=`, overpaying the winner script (the miner takes less) would validate; underpaying fails either way. `IsTransactionValid` enforces only when winner signatures exist, and SPORK_8 decides whether a failed check rejects the block. Zero keeps `==` and logs OVERPAY; scan mainnet with `chain_stats.py --zn-pay`. Sampled windows have matched the model exactly.

### 3.6 Linux binary compatibility

Zero Linux builds use the host `gcc` with static `depends/` libraries but link `libc.so.6`, `libstdc++.so.6`, `libpthread`, and `libm` dynamically. **The build OS therefore sets the runtime floor.** A `zerod` built on Ubuntu 24.04 does not run on 18.04 (`GLIBC_2.28+`, `GLIBCXX_3.4.26+` symbols); confirm with `objdump -T ./zerod | grep GLIBC`. `contrib/devtools/symbol-check.py` is capped at 24.04 symbols and does not widen compatibility; `zcutil/release-linux.sh` only strips and packages.

**Target.** Main effort is Ubuntu 24.04. Interoperability with 18.04, 20.04, and 22.04 is wanted; 16.04 is not covered. Tracked as **OPS-LINUX-OTHER** (TODO).

| Project | Linux build | Runtime floor |
|---------|-------------|---------------|
| Bitcoin Core 28.0+ | Guix, pinned glibc | glibc 2.31 (Ubuntu 20.04+); 27.x was the last line to run on 18.04 |
| Zcash 6.2+ | `depends/` + autotools | 22.04 Tier 1; 18.04 dropped in 5.6, 20.04 in 6.2 |
| Pirate | `depends/` + autotools | Host glibc, as Zero |
| Zero | `build.sh` + `depends/`, system gcc | 24.04 in practice |

**Rust.** On Linux, `RUST_USE_SYSTEM=1` uses the host `rustc`; `FORCE_DEPENDS_RUST=1` uses the pinned 1.32.0, the only option on 18.04, where distribution Rust is missing or too old. Distribution `rustc` versions per Ubuntu release (roughly 1.75 on 22.04, 1.75 to 1.90 on 24.04, 1.41 to 1.75 on 20.04) are unverified estimates; OPS-TOOLCHAIN-MATRIX (TODO) tracks verifying them. The Rust version affects the build, not the glibc floor.

The Insight production host runs Ubuntu 18.04. Its problems are separate: (A) binary ABI, fixed only by an 18.04-built binary or a host upgrade; (B) Node 8 and OS age; (C) `dbcache` on a 4 GiB VPS (about 2048 at most); (D) systemd and nginx configuration. An 18.04 build path exists (extra instructions and a helper script, no source changes); it is internal.

**Open decisions, in order** (postponed; not a release gate):

1. Timeline for the Insight host and the 18.04 path relative to the next release.
2. Insight artifacts: keep 18.04-built binaries, or upgrade the VPS to 22.04+, which resolves A and B together.
3. Validate build and run on 20.04 and 22.04 before declaring a minimum runtime OS; 22.04 is the recommended target.
4. If 22.04 becomes the floor: build releases in `ubuntu:22.04` Docker, retarget `symbol-check.py` `MAX_VERSIONS`, and add a 22.04 CI build.
5. Guix: defer unless a dedicated REL item is opened.

Docker is suited to release artifact builds; a VM or production-like VPS is needed once for systemd and Insight integration.

```bash
docker run --rm -v "$PWD:/work" -w /work ubuntu:22.04 bash -lc '
  apt-get update && apt-get install -y build-essential libtool autotools-dev \
    automake pkg-config curl git python3 bsdmainutils
  ./zcutil/fetch-params.sh && ./zcutil/build.sh -j$(nproc)
'
python3 contrib/devtools/symbol-check.py src/zerod src/zero-cli src/zero-tx
```

---

## 4. Blockbook and explorer backends

**Decision:** keep Insight operational for the mainnet explorer ([insight.zeromachine.io](https://insight.zeromachine.io/)). A Blockbook port is the preferred long-term indexer but is postponed: it is a separate Go and RocksDB deployment, and near-term effort goes to keeping Insight healthy. RocksDB-backed indexing would remove the address-index memory pressure that causes Insight's Node 8 out-of-memory failures.

[Trezor Blockbook](https://github.com/trezor/blockbook) keeps its own address and transaction index while syncing over JSON-RPC. It needs a synced node with `txindex=1`, not `-insightexplorer`. Upstream ships about 100 coin configurations, including Zcash, Flux, SnowGem (TENT), and Firo, but none for Zero; the `zerocurrencycoin/blockbook` fork is abandoned.

**Port template.** The Zcash backend (`bchain/coins/zec/`, `configs/coins/zcash.json`) uses ports 9132 / 9032 / 8032 / 38332 (public, internal, backend RPC, ZMQ). It ingests blocks with `getblock <hash> 2`, rewrites `"valueZat"` to `"valueSat"`, fetches txids with a second `getblock <hash> 1`, and on RPC size errors falls back to a verbosity-1 block plus per-transaction `getrawtransaction`. Parsing is JSON only. A Zero port needs a new `configs/coins/zero.json` (an unused Blockbook port series, `backend_rpc` 23811, Zero's t-address prefix and SLIP44) and can reuse the ZEC Go package.

**Fallbacks.** Iquidus (Node.js and MongoDB, used by Zcash forks such as Hush) or LBE (Python, RPC only, without a rich address index). btc-rpc-explorer is not shielded-aware.

---

## 5. Pirate wallet features under review

Same queue as section **3.4**. Zero already has automatic Sapling consolidation (`-consolidation`, `-consolidatesaplingaddress`, `-consolidationtxfee`), manual `z_mergetoaddress` (with `-experimentalfeatures -zmergetoaddress`), and the witness-rebuild lockout.

| Feature | Zero today | Decision |
|---------|------------|----------|
| `consolidateaddress` RPC | None | **Review**; manual per-address consolidation for large Sapling wallets |
| `consolidationstatus` RPC | None | **Review**; low cost if automatic consolidation stays |
| `z_getbalances` | `z_gettotalbalance` only | **Review**; Zcash-shaped API, not Komodo's account model |
| Cleanup and dust modes | None | **Review**; needs Zero thresholds |
| `GetFilteredNotes` large-wallet path | Older path | Consider |
| `maxprocessingthreads` | None | Consider for operations tuning |

**Order:** `consolidateaddress` (reusing `AsyncRPCOperation_saplingconsolidation`); `z_getbalances`, or a documented `z_gettotalbalance` plus `z_listaddresses` workaround; dust thresholds.

---

## 6. Pending public documentation

Drafts approved for copying into public documents as plain text.

| Target | Draft | Status |
|--------|-------|--------|
| ZERO_COIN.md | **6.1** supply vs UTXO | Ready |
| ZERO_COIN.md | **6.2** zeronode economics boundary | Ready |
| BUILD_ZERO.md | **6.3** REST | Ready |
| BUILD_ZERO.md | **6.4** public testnet join | Ready; verify seeds first |
| README.md or CONTRIBUTING.md | **6.5** wallet file export | Ready |
| ZERO_COIN.md | Port and datadir table (DOC-03) | Gap |

### 6.1 ZERO_COIN.md -- supply vs UTXO

```markdown
`chain_stats.py --cons` sums consensus subsidy (miner + nodes + dev split). It is not the UTXO set total.
For aggregate transparent total at tip use `gettxoutsetinfo` (slow). Per-address balances need `-insightexplorer` or an external indexer.
```

### 6.2 ZERO_COIN.md -- zeronode economics boundary

```markdown
This section documents coinbase splits and spork-gated tiers (20-40% of block value when enabled).
```

### 6.3 BUILD_ZERO.md -- REST

```markdown
Optional HTTP REST (`-rest=1`) exposes Bitcoin-Core-style GET endpoints on the RPC port (`/rest/tx/`, `/rest/block/`, `/rest/mempool/`, `/rest/getutxos`). Default off. Not used by Insight. Test: qa/rpc-tests/rest.py.
```

### 6.4 BUILD_ZERO.md -- public testnet join

````markdown
### Public testnet

Testnet uses P2P 23802 and RPC 23812. Add to `zero.conf`:

    testnet=1
    rpcuser=...
    rpcpassword=...

DNS seeds: `testnet1.zerocurrency.io`, `testnet2.zerocurrency.io`.

    ./src/zerod -testnet -daemon
    ./src/zero-cli -testnet getblockchaininfo

No qa harness connects to testnet; automated tests use regtest.
````

### 6.5 Wallet file export

````markdown
The wallet file is Berkeley DB 6.2.32, default name `wallet.zero` (`-wallet=`), schema in the ZIP 400 lineage (`zkey`, `czkey`, `sapzkey`, `ckey`, ...). Recovery: `zerod -salvagewallet`.

Export from a running node:

| RPC | Output |
|-----|--------|
| `dumpwallet <path>` | Transparent WIF + metadata |
| `z_exportwallet <path>` | Shielded keys |
| `z_exportkey` / `z_exportviewingkey` | Per address |
| `backupwallet <path>` | Binary copy |

Offline tools: `db_dump` from the matching BDB 6.2.x build; zmigrate and Zallet `migrate-zcashd-wallet` parse zcashd BDB (encrypted fields not decrypted); pywallet reads transparent keys only.
````

---

## 7. Open maintainer issues

Items involving unconfirmed errors or arithmetic stay here until confirmed and fixed; they do not enter public documents before then.

### Documentation

**DOC-NOTICES -- Upstream copyright notices.** Postponed. Commit `a09cea932` (2026-03-26) replaced the Dash and earlier copyright lines in the 24 `src/zeronode/` files with "Copyright 2026 Zero Developers"; the MIT license requires keeping the original notices. Restore them from `20ad58542`.

**DOC-02 -- Node setup.** Remaining deliverables: an operator runbook in BUILD_ZERO (build, `fetch-params`, `zero.conf` RPC credentials, launch, ports); the economics draft **6.2**; a security statement (Sapling only, no Orchard, 2026 Sprout CVE not applicable). Zeronode setup is part of ZN-01.

**Fixed-seed gap.** Tracked as REL-08.

**DOC-03 -- One `zero.conf` sample and one source for ports.** Zero ports are P2P 23801 / 23802 / 23803 and RPC 23811 / 23812 / 23813 (mainnet, testnet, regtest). They come only from `chainparams.cpp` and `chainparamsbase.cpp` through `Params().GetDefaultPort()` and `BaseParams().RPCPort()`; there is no `#define`. Other chains relate RPC and P2P ports differently, so no formula carries over:

| Project | Main P2P | Main RPC | Relation |
|---------|----------|----------|----------|
| Zcash | 8233 | 8232 | RPC = P2P - 1 |
| Pirate | 7770 | 7771 | RPC = P2P + 1 |
| TENT | 16113 | 16112 | RPC = P2P - 1 |
| Zero | 23801 | 23811 | RPC = P2P + 10 |

Data directory: `~/.zero`, `~/Library/Application Support/zero`, `%APPDATA%\zero`. Params: `~/.zcash-params` or `~/Library/Application Support/ZcashParams`.

Scope: every place that describes or writes `zero.conf` fields must agree with the options the node actually parses -- `init.cpp` help text and hidden options, `Options.csv`, `doc/man/`, `contrib/zero.conf`, `contrib/conf-templates/` with `contrib/zero-conf.sh`, the Debian example, README and BUILD_ZERO samples, and the conf zerowallet generates (zerowallet `src/connection.cpp`). Each field should be described once, with its default and purpose, and samples should use only documented fields.

Remaining work: one commented canonical `zero.conf` under `contrib/`, with the others reduced to a pointer; ZeroWallet's generated conf limited to `server`, `rpcuser`, `rpcpassword`, `rpcport`, with wallet extras (`deletetx*`, `consolidation*`) documented as wallet policy; hardcoded RPC ports in `HelpExampleRpc`, `bitrpc.py`, and `linearize-hashes.py` replaced by `BaseParams().RPCPort()` or conf values; `-port` / `-rpcport` help and zeronode port checks switched to the params accessors.

*`-port` and `-rpcport` help.* `init.cpp` prints `(default: 23801 or testnet: 23802)` and `(default: 23811 or testnet: 23812)` from integer literals. The same numbers are defined once per network in the chain parameters: P2P in `CChainParams::nDefaultPort` (`chainparams.cpp`, read with `GetDefaultPort()`), RPC in `CBaseChainParams::nRPCPort` (`chainparamsbase.cpp`, read with `RPCPort()`). Zcash builds the help from them, for example `Params(CBaseChainParams::MAIN).GetDefaultPort()` and `Params(CBaseChainParams::TESTNET).GetDefaultPort()`, with `BaseParams`-style accessors for RPC. Doing the same removes the risk of help text drifting from the real defaults. Behavior does not change; validation is `zerod -help` output before and after, plus the existing RPC and P2P tests.

**DOC-CONVENTIONS -- Documentation and comment rules.** Draft rules below, collected from review of the documentation passes. Target: the agent and contributor instruction files (AGENTS.md and the global agent configuration), aggregated with the wider LLM coding configuration effort so one rule set applies across Zero repositories. Until adopted there, these are guidance.

- *Sizing.* Content drives length: include what a reader needs to use, change, or validate the code or decision; drop what goes stale. No fixed line limits.
- *Inline code comments.* Explain why: invariants, cross-component constraints, consensus and locking requirements. No task ids, status notes, dates, change history, personal paths, or references to planning documents.
- *Function and class documentation.* Doxygen `/** ... */` on interfaces and non-trivial functions: purpose, parameters, returns, preconditions, locking and thread safety, failure behavior; as long as the interface requires.
- *File headers.* Copyright and license; optionally a short purpose. No change logs.
- *Tests.* More latitude than production code: scenario, choice of heights and amounts, known failures, how to run. Python tests open with a docstring.
- *Scripts.* Shebang, copyright for Zero-authored scripts, one-line purpose. Scripts with options provide `usage()` behind `-h` / `--help` (Usage, Modes or commands, Options, Env) and the header refers to it; scripts without options state usage on one header line.
- *Upstream, vendored, ported code.* Keep original comments even when moved or lightly edited; correct only factual errors; keep diffs minimal.
- *Public documents.* README is the public map. No references to internal documents or external files. ASCII, `##` headings, no parenthetical headings, repo-relative paths, current state only, no transient values.
- *Internal documents.* This file's section 1 is the internal map. External documents by name, never by filesystem path; other Zero repositories by repo-relative path only when necessary. History only where a decision's rationale depends on it. Transient counts only in section 7 Validation counts.
- *Reference records* (for example ZcashFixes) keep their comparisons, timelines, and third-party detail; restructure for readers, do not cut. Verify factual claims and link sources inline and in a references section.
- *No filler.* Every sentence states a fact, a decision, or an action. Cut generic, non-committal, conversational text a reader cannot act on: vague hedges, feel-good assessment, and fill-in placeholders. Tracking item status (postponed, not scheduled, does not gate a release, decide after X) stays. Applies to documents, comments, and help text.
- *Streamlining.* Classify a document before cutting it; move unique facts rather than delete them; verify done / open claims against the code.

**DOC-FR-NAMING.** Reconcile `vFoundersReward`, FoundersReward, `developmentfee`, and GBT `founders` naming across code and ZERO_COIN. Founders destination options (FR-ROTATE, FR-TADDR, FR-Z) are product decisions, not release gates.

**GitHub issues.** #70 (`getrawtransaction` lacks `size` and `fees`): `size` is implemented in `TxToJSON` and `TxToJSONExpanded` (serialized bytes via `GetSerializeSize`), documented in the `getrawtransaction` and `decoderawtransaction` help, and covered by `rpc_tests` (decoderawtransaction) and `getrawtransaction_insight.py` (getrawtransaction verbose and getblock verbosity 2 compared with the hex length). It is additive; Bitcoin Core and Zcash return the same key. Remaining: a transparent-only `fee` that requires `txindex`, with shielded fees deferred; suitable for a contributor. #69 (insight-ui and insight-api): close with a pointer to the public explorer.

### Release and infrastructure

**REL-01 -- Release signing and checksums.** Single item for packaging, signing, and checksum work on all platforms. Procedure: BUILD_ZERO sections 2.5 (packaging, signing options, `checksums.sh`) and 2.6 (checksum and sign, verify a download); release bar: TEST_ZERO section 8. Open:

1. Keys: decide who holds the GPG, Apple Developer ID, and Authenticode keys; publish the GPG key fingerprint.
2. Linux: first `release-linux.sh` run on the Ubuntu build host (`dpkg-deb`, GNU `strip`); GPG signature over `SHA256SUMS`.
3. macOS: Apple Developer Program enrollment; first `release-macos.sh --sign --notarize` run (`codesign`, `xcrun notarytool`, stapling).
4. Windows: first MXE build packaged by `release-win.sh` with Authenticode signing.

**REL-03 -- Params archival.** `fetch-params.sh` uses upstream Zcash file names and mirrors; audit the names against `zerod` startup and verify the URLs.

**REL-04 -- Chain bootstrap.** Document snapshot sourcing, verification, and datadir placement for end users. Operators validate with `contrib/ops-validate.sh bootstrap` against a copy, never the original file; packed snapshots stay outside git.

**REL-05 -- Inherited contrib and packaging tooling.** Decide per path: keep, adapt to Zero, or remove.

| Path | State |
|------|-------|
| `zcutil/build-debian-package.sh`, `contrib/debian/` | Superseded by the `.deb` from `release-linux.sh`; the script copies bash-completion files that do not exist |
| `contrib/macdeploy/` | Upstream Qt-wallet DMG tooling; there is no Qt wallet |
| `src/amqp/`, `contrib/amqp/`, `depends` `proton.mk` | Qpid Proton AMQP; off by default (`NO_PROTON=1`), duplicates ZMQ, no documentation or CI |
| `contrib/ci-workers/` | Upstream Zcash Ansible buildbot setup; Zero CI is GitHub Actions |
| `contrib/init/` | `bitcoind` service files (systemd, OpenRC, upstart, SysV) with Bitcoin names and paths |
| `contrib/zmq/` | ZMQ subscriber example; ZMQ is the supported notification path, and BUILD_ZERO does not refer to the example |

**REL-06 -- History and branch cleanup.** Review separately before any deletion: whether to squash the release-line commits before merging into `master`; which local branches to delete (backup branches from rebases, merged work branches, perf branches); and the old remote release branches that duplicate their tags. Deletion is irreversible for anything not merged or tagged, so list each branch with its merge and tag status first.

**REL-07 -- Windows hardening.** `build-win.sh` does not pass `--enable-hardening`. Test which hardening flags MXE `x86_64-w64-mingw32-g++` accepts (`-z relro` and `-z now` are Linux-only), add the flag in `run_configure_win()`, build `zerod.exe` and confirm the stack protector, then record the result in BUILD_ZERO.

**REL-08 -- Fixed seeds.** Mainnet has ten DNS seeds (`seed0`..`seed9.zerocurrency.io`) but `src/chainparamsseeds.h` has empty `pnSeed6_main` and `pnSeed6_test` arrays, and `contrib/seeds/nodes_main.txt` still holds a single address from 2017. A node whose DNS lookups fail and whose `peers.dat` is empty cannot find peers. Steps: collect addresses of long-running public nodes on port 23801 (from `getpeerinfo` on well-connected nodes or a crawl of the DNS seeds); keep those with a protocol version at or above `MIN_PEER_PROTO_VERSION` and good uptime; write them to `contrib/seeds/nodes_main.txt` and `nodes_test.txt`; run `contrib/seeds/generate-seeds.py contrib/seeds > src/chainparamsseeds.h`; refresh before each release. Validation: start with an empty datadir and `-dnsseed=0` and confirm the node connects from the fixed seeds alone.

**REL-09 -- Version consistency check.** `zcutil/check-release.sh` checks the git tag but not that `configure.ac` produces the same version. Proposal: compute the version from `_CLIENT_VERSION_*` (build below 25 beta, 25-49 `rc<build-24>`, 50 final) and fail the receipt when it differs from `--release`; also confirm `zerod --version` of the built binary. Today the check is manual: `zerod --version` on the tagged clean tree must print exactly the tag.

**Release flag proposals.** Gate `-g` behind `ZERO_DEBUG=1`; evaluate `-O2`; decouple `CXXFLAGS_overridden` from a bare `-g`; add `split-debug.sh` output as a `-dbg` package.

**Build host disk.** Safe to reclaim: apt lists and cache, ccache, `depends/work/*`, the repository `cache/`, MXE package and log directories, and the systemd journal.

### Testing

Items marked **contributor-ready** have clear scope and need no signing keys or consensus decisions.

**TST-01 -- zero_exclusive and experimental RPC scenarios.** Contributor-ready. `getalldata` is fully covered for empty-wallet gates and by the Ext `getalldata_scenario`; its remaining gap is mined-transaction History and balance depth. The others need at least three cases each (valid, boundary, error) using the `TestingSetup` fixture; implementations are in `src/wallet/rpczerowallet.cpp`.

| RPC | File | Today |
|-----|------|-------|
| `zs_listtransactions`, `zs_gettransaction`, `zs_listspentbyaddress`, `zs_listreceivedbyaddress`, `zs_listsentbyaddress` | `rpc_zero_exclusive_tests.cpp` | Parameter count only |
| `getsupply` | same | Parameter count and fields |
| `getsaplingwitness`, `getsaplingwitnessatheight`, `getsaplingblocks` | `rpc_zero_experimental_tests.cpp` | Parameter count only |

**TST-06 -- Fuzz harness.** Contributor-ready. Zero has no coverage-guided fuzzing; `CNode::Fuzz` (`-fuzzmessagestest`) only flips bits in outgoing messages. Add `src/fuzz/` with libFuzzer targets (`LLVMFuzzerTestOneInput`) built with `-fsanitize=fuzzer,address`, following Bitcoin Core `src/test/fuzz/`. Targets, in order: `CTransaction`, `CBlock`, and `CBlockHeader` deserialization; `CScript` / `EvalScript`; `Equihash<192,7>::IsValidSolution` on arbitrary bytes; `DecodeDestination`. Seed the corpus from regtest `getblock <hash> 0`. Acceptance: two targets run 60 seconds without a crash, with documented build steps.

**TST-TIERS -- Tier naming and grouping.** Postponed until after v4.1.0. Renaming touches `qa/pull-tester/rpc-tests.sh`, `contrib/run-tests.sh`, `qa/rpc-tests/test_tier_inventory.csv`, `qa/rpc-tests/README.md`, `qa/zcash/full_test_suite.py`, CI (`.github/workflows/tests.yml` uses `--strict` only), and about 150 mentions across TEST_ZERO, TODO, the release notes, and internal documents, plus contributors' habits.

Current scheme and proposed replacement:

| Today | Flag | Proposed | Flag | Basis |
|-------|------|----------|------|-------|
| Tier A | `-A` | gate | `-gate` | Justified: it is exactly the contributor merge gate (default of `run-tests.sh`, fast, deterministic, no heavy mining) |
| Tier B pass | `-B` | full | `-full` | Slower wallet, mempool, index, and zeronode scripts that pass |
| Ext pass | `-E` | extended (or split) | `-ext` | Upstream `testScriptsExt` means extended: slow or special setup. "infra" fits only half the members: `rpcbind_test`, `getblocktemplate_longpoll`, `rpc_workqueue_full`, `maxblocksinflight` test server, network, or P2P infrastructure; `invalidateblock`, `receivedby`, `getalldata_scenario`, `rpc_coverage_probe` are extended functional tests. Either keep one "extended" group or split into `infra` and fold the rest into `full` |
| Bfail Debug, Bfail Retired, Efail | `-Bfail`, `-Efail`, `-rpcfail` | excluded | `-excluded` | One list of scripts excluded from passing tiers; the reason is an attribute, not a tier |

Exclusion reasons (attribute values), replacing the Debug / Retired / Efail split:

| Reason | Meaning | Examples today |
|--------|---------|----------------|
| `port` | Needs porting to Zero parameters, maturity 720, or Python 3 | `wallet_sapling`, `rawtransactions`, `bip65-cltv-p2p`, `getblocktemplate_proposals` |
| `heavy` | Passes or may pass but needs multi-GB memory or long runtime | `wallet_shieldcoinbase_sapling`, `wallet_nullifiers` |
| `resource` | Depends on disk size or fee-estimator behavior | `pruning`, `smartfees` |
| `retired` | Sprout-era or manual testnet; not expected to return | `turnstile`, `sprout_sapling_migration` |

Implementation outline: one `testScriptsExcluded` array with `name:reason` entries (or a parallel associative array); `-excluded` runs all, `-excluded=port` a subset; `-list-csv` emits `tier,group,script` with `group` carrying the reason for excluded scripts. Old flags (`-A`, `-B`, `-E`, `-Bfail`, `-Efail`, `-rpcfail`, `--rpcfail`) stay as aliases for one release with a deprecation notice. Update documents and CSV in the same change.

**TST-02 -- Parallel Tier A.** Deprioritized: `paymentdisclosure` hangs under `--jobs>1`, and the serial gate is sufficient.

#### Regtest reference

| Network | P2P | RPC | Equihash | Fee-start / founders window | Harness use |
|---------|-----|-----|----------|-----------------------------|-------------|
| Mainnet | 23801 | 23811 | 192,7 | Height 412300 | Manual operations only |
| Testnet | 23802 | 23812 | 192,7 | Height 1 | None; qa never connects to testnet |
| Regtest | 23803 | 23813 | 48,5 | Heights 1000 to 1500 (`REGTEST_FOUNDERS_START` / `STOP`) | All automated RPC and Boost tests |

Regtest mines with `generate` (`setgenerate` waits for peers on mainnet and testnet). Network upgrades activate with `-nuparams=<branchHex>:<height>`. The shared RPC cache stops at tip 725 (`COINBASE_MATURITY` plus 5). Zero has no testnet minimum-difficulty rule (TNT-07). With halvings every 150 blocks, total regtest miner emission is about 3000 ZER, below the 10000 ZER zeronode collateral. Regtest sporks default to off.

### Deferred

**Third-party upgrades not possible now.**

- OpenSSL: stay on 1.1.1w (end of life) until 3.x is audited or OpenSSL is removed; it serves RPC TLS and legacy EVP call sites. Zcash and Bitcoin removed it. Path: audit `EVP_*`, `SSL_*`, and `RAND_*` call sites, add TLS regression tests, then upgrade or remove.
- Boost above 1.88 and GTest 1.17+: require C++17. Path: C++17 readiness of `src/`, revalidated `ax_boost_*` macros, full depends rebuild.

**DEF-06 -- SwiftTX.** Mainnet `SPORK_2_SWIFTTX` and `SPORK_3_SWIFTTX_BLOCK_FILTERING` are active (signed 1558907000). `swifttx.cpp`, `ix`, and `txlvote` stay until a signed spork turns them off or a network upgrade removes them. The hidden options `-enableswifttx` (default true) and `-swifttxdepth` (default 5) go with them. `-deleteconflicttx` (default true; with `-deletetx`, removes conflicted wallet transactions after reorgs or double spends) is unrelated and stays. Budget superblocks are off (`SPORK_9`, `SPORK_13` = 4070908800).

### Reference

**CSV inventories.** `RPCs.csv`, `RPCs_extended.csv`, `Options.csv`, `Options_extended.csv`, and `Reindex_Rescan.csv`. Update base and extended files together when adding or removing an RPC or option. The `*-hidden` category in `Options.csv` lists options parsed in `init.cpp` but absent from `--help`. A `zero_missing_sources` value of **B** marks RPCs listed only for cross-chain comparison (`dumptxoutset`, `scantxoutset`, descriptor RPCs); they are not planned ports.

### Validation counts

The only place in the documentation where test and RPC counts are recorded; update it when tiers or RPC tables change, and use it to check that a run covered what it should. Recorded 2026-09-30.

| Set | Count | Regenerate |
|-----|------:|-----------|
| Tier A (gate) | 10 | `./qa/pull-tester/rpc-tests.sh -list-csv` |
| Tier B pass | 31 invocations (30 scripts; `txn_doublespend` twice) | same |
| Ext pass | 8 | same |
| `-all` total | 49 invocations | same |
| Bfail debug / retired | 28 / 8 | same |
| Efail | 5 | same |
| `RPCs.csv` rows / `zero=y` | 278 / 172 | count rows in `RPCs.csv` |

---

## 8. Chain safety

How `zerod` detects, reports, and reacts to abnormal chain conditions: a reorg deeper than the local bound, a heavier chain that this node considers invalid, an abnormal block rate, and the end-of-support height. Tracked as **CON-04** (TODO). Mainnet values: 120-second blocks (Blossom is not active, so 720 blocks per day), `COINBASE_MATURITY` 720, `MAX_REORG_LENGTH` 99, last checkpoint at height 700,000.

### 8.1 Summary

| Mechanism | Code | Can fire on mainnet | Reported through | Automatic reaction | Tests |
|-----------|------|---------------------|------------------|--------------------|-------|
| Reorg bound | `ActivateBestChainStep` and the startup rewind check, `src/main.cpp` | Yes: any reorg deeper than 99 blocks | `debug.log`, stderr | Shutdown; repeats on every restart while the heavier chain is offered | `reorg_limit.py`, Tier B fail (cache-tip heights) |
| Heavier invalid chain | `CheckForkWarningConditions`, `src/main.cpp` | Yes: after initial sync, an invalid chain with 6 or more blocks of extra work | `debug.log`, RPC warning fields, `-alertnotify` | None | None |
| Large valid fork | `CheckForkWarningConditionsOnNewFork`, `src/main.cpp` | No: dead code (section 8.4) | -- | -- | None |
| Block rate | `PartitionCheck`, `src/main.cpp`, scheduled every 60 s | Yes: 77 or fewer, or 167 or more, blocks in 4 hours (120 expected); in practice a hashrate drop of about 65% or a threefold rise (section 8.5) | `debug.log`, RPC warning fields until restart, `-alertnotify` | None | None |
| End of support | `EnforceNodeDeprecation`, `src/deprecation.cpp` | Yes: warning from height 3,985,640, halt at 4,005,800 (about April 2032) | `debug.log`, stderr, `getdeprecationinfo`, `-alertnotify` | Shutdown; refuses to restart | 12 GTests `DeprecationTest.*` |

### 8.2 Reporting channels

- **Log.** Every mechanism writes to `debug.log`. Messages raised through `ThreadSafeMessageBox` also go to stderr on a daemon (`src/noui.cpp`).
- **RPC.** `GetWarnings("statusbar")` feeds `errors` in `getinfo` and `getmininginfo` and `warnings` in `getnetworkinfo`. It carries the invalid-chain warning and the block-rate warning (`strMiscWarning`, which is never cleared until restart). The reorg-bound shutdown does not appear there, because the node stops.
- **`-alertnotify`.** Runs only in builds with `ENABLE_SYSTEM_COMMAND` (BUILD_ZERO section 4.6.1); release builds log the skip. It fires for deprecation, the invalid-chain warning, and the block-rate warning. It does **not** fire for the reorg-bound shutdown.
- **Gap.** A release binary has no push channel. Monitoring must poll the RPC warning fields or watch `debug.log` and process exit.

### 8.3 Reorg bound

**Mechanism.** Before disconnecting any block, `ActivateBestChainStep` computes the reorg length from the old tip to the fork point. Above `MAX_REORG_LENGTH` it logs the old tip, the new tip, and the fork point, shows "the node is shutting down for your safety", and calls `StartShutdown()`; the competing chain is not applied. The same check runs at startup for a rewind caused by insufficiently validated blocks. `intendedRewind` exempts two Zcash testnet heights (252500, 584000) that do not exist on Zero's networks. After a restart, peers offer the same heavier chain and the node stops again, so recovery is manual.

**Origin.** zcashd PR [#2463](https://github.com/zcash/zcash/pull/2463) (str4d, merged 2018-02-21, v1.0.15): "a larger reorg would crash their nodes. It has the additional economic side-effect of ensuring that by default, nodes do not accept re-orgs that delete currently-spendable coinbase". The crash was the wallet witness cache running empty ([#1302](https://github.com/zcash/zcash/issues/1302)); `WITNESS_CACHE_SIZE = MAX_REORG_LENGTH + 1`. The review noted that "all forks would require an upgrade in order to be resolved under this policy"; a configurable `chainforkdecision` was dropped. In zcashd the bound is `COINBASE_MATURITY - 1` = 99. Zero raised maturity to 720 but kept 99 (`src/main.h` comment: "COINBASE_MATURITY of 720 is too much"), so on Zero the bound protects the witness cache only; a reorg of 100 to 719 blocks cannot unwind a spendable coinbase anyway. The check is `reorgLength > MAX_REORG_LENGTH`: a reorg of 100 or more blocks stops the node. zcashd (`src/main.cpp`, January 2026 checkout), Ycash, TENT, and Zclassic use the same 99 and the same shutdown.

**Field.** Comparison.md section 14.5 surveys the zcashd lineage; summary:

| Project | Bound | On breach |
|---------|-------|-----------|
| zcashd, Ycash, Zero | 99 | Shut down |
| TENT | none on the live path since `6f64bb7` (2021) | Follows the fork past the witness cache |
| Pirate, Hush (Komodo) | 99, `-maxreorg=N` | Refuses and invalidates forks below the last dPoW notarization; above it, a reorg over the bound shuts down and the log suggests restarting with `-maxreorg=<length+10>` |
| Flux | 40; 5000 while the tip is at heights 2,020,000 to 2,025,000 (`GetMaxReorgDepth`) | `ContextualCheckBlockHeader` rejects a header that forks 40 or more blocks below the tip (`bad-fork-prior-to-maxreorgdepth`, misbehavior 10); the node stays up on its chain; the startup rewind check still exits |
| Zclassic | 99 and `-maxreorgdepth` 10 | Finalizes at 10, shuts down at 99 |
| Horizen | none | Delay penalty (`GetBlockDelay`, `src/main.cpp`): a block arriving more than 5 blocks below the active height (`PENALTY_THRESHOLD`) gives its chain a delay equal to the gap; the delay grows by the gap for each further late block and falls by 1 for each block above the active height. Chain selection ranks lower total delay before more work, so a withheld chain must out-mine the public chain by its delay before it can win ([Decrypt](https://decrypt.co/3650/horizen-new-bitcoin-consensus)) |
| Bitcoin Core, Litecoin, Bitcoin SV | none | Follows the most-work chain at any depth; a pruned node cannot reorg below its kept blocks (`MIN_BLOCKS_TO_KEEP` 288) |
| Bitcoin Gold | auto-finalization 9 blocks (`-minfinalizationdepth`, ABC code) | Blocks finalized after 9 confirmations and a minimum age; deeper forks rejected |
| Firo | 5 blocks within an enforcement height window | Invalidates the deeper chain and stays up; `-allowdeepreorg` overrides |
| Zebra | 1000 since 5.2.0 | Finalizes older blocks and stays up ([ZF](https://zfnd.org/zebra-5-2-0-wider-rollback-window/), [#10650](https://github.com/ZcashFoundation/zebra/pull/10650)) |
| zcashd sidecar | raising 99 to 1000 | Witness cache and wallet checkpoints grow about tenfold ([#11403](https://github.com/ZcashFoundation/zebra/issues/11403)) |

Outside the lineage: Bitcoin Cash ABC finalized blocks after 10 confirmations (rolling checkpoints, 0.18.5, 2018), criticized for raising the chain-split risk ([BitMEX Research](https://www.bitmex.com/blog/bitcoin-cash-abcs-rolling-10-block-checkpoints)); Ethereum Classic used MESS, a scoring penalty on late large reorgs (ECIP-1100, 2020, replaced 2024) ([ECIP-1100](https://ecips.ethereumclassic.org/ECIPs/ecip-1100)); Dash ChainLocks have a masternode quorum sign the first block seen at each height ([Dash docs](https://dash-user-docs.readthedocs.io/projects/core/en/20.1.0/docs/guide/dash-features-chainlocks.html)); Komodo dPoW notarizes block hashes on another chain ([Komodo](https://komodoplatform.com/delayed-proof-of-work/)). Recent incidents: Horizen's 38-block reorg in June 2018, Monero's 18-block reorg by the Qubic pool at about a third of the hashrate in September 2025 ([The Block](https://www.theblock.co/post/370628/monero-shaken-by-block-reorg-reviving-tensions-with-qubic)).

**Assessment.** The bound prevents a deep double spend against nodes that saw the original chain, but it turns the attack into a halt: an attacker who publishes a heavier private chain more than 99 blocks deep (about 3.3 hours of majority hashrate) stops every synced node, while nodes that sync from scratch follow the attacker's chain. The result is a split that needs coordinated manual recovery, and the shutdown sends no notification. The last checkpoint (700,000) gives no protection near the tip.

**Options.**

1. Keep shut-down, add observability: call `AlertNotify` and log a fixed marker before `StartShutdown()`; document recovery (inspect `getchaintips`, choose the chain, `invalidateblock` or `reconsiderblock`, restart).
2. Reject and stay up (Flux, Zebra): keep the 99-block bound but refuse the fork without exiting, keep serving the current chain, and raise a persistent RPC warning and `-alertnotify`. A split then persists until operators act, so it needs monitoring.
3. Raise the bound toward 719 (Zebra direction): grow the witness cache with it; measure wallet memory and file size first.
4. External finality: a delay penalty (Horizen) or quorum signing (ChainLocks over zeronodes) are consensus changes and belong with a planned fork.

**Checkpoints are not a reorg defense here.** A checkpoint makes the node reject any chain that conflicts with a hard-coded block hash, so it finalizes history only below the checkpoint. Bitcoin Core stopped adding checkpoints after 2014, moved their remaining roles to `nMinimumChainWork` (2016), `assumevalid` (2017), and headers presync (PR #25717, 2022), and removed them in PR [#31649](https://github.com/bitcoin/bitcoin/pull/31649) (merged 2025-03-14): "The headers presync logic ... should be enough to prevent memory DoS using low-work headers. Therefore, we no longer have any use for checkpoints." The objection throughout was that developer-chosen hashes put history under release control. The Zcash ecosystem still maintains them: zcashd added height 3,000,000 in July 2025, and Zebra ships 14,049 mainnet checkpoints up to height 3,373,206 to validate settled network upgrades ([Zebra checkpoints](https://github.com/ZcashFoundation/zebra/blob/main/zebra-chain/src/parameters/checkpoint/README.md)). Zero's last checkpoint is 700,000 (block time October 2019). In Zero a checkpoint does four things: blocks that are ancestors of the last checkpoint skip script checks and Sprout and Sapling proof verification in `ConnectBlock` (`fExpensiveChecks`), which shortens sync and `-reindex`; forks below it are rejected (`ContextualCheckBlockHeader`); its height and transaction counts drive `verificationprogress` and rescan progress; and its height gates inventory relay during initial download. Zero has no `assumevalid`. A refresh therefore speeds sync and reindex and finalizes history below the new height; it does nothing near the tip. Zebra generates checkpoints with `zebra-checkpoints` from a synced node at most 400 blocks or 32 MiB apart, and its checkpoint verifier accepts each segment as a hash chain to the next checkpoint, skipping most contextual checks, up to a mandatory checkpoint at Canopy activation.

**Proposal.** Now: option 1 and a working `reorg_limit.py`. Then decide between options 2 and 3 with measured witness-cache cost.

### 8.4 Heavier chain and large fork warnings

**Mechanism.** Two branches in `CheckForkWarningConditions`, both suppressed during initial block download:

- **Invalid chain.** `pindexBestInvalid` tracks the most-work block that failed validation (`InvalidChainFound`). When it has more than 6 blocks of work above the tip, the node logs "Found invalid chain at least ~6 blocks longer than our best chain. Chain state database corruption likely.", runs `-alertnotify`, and sets `fLargeWorkInvalidChainFound`. `GetWarnings` then reports "We do not appear to fully agree with our peers! You may need to upgrade, or other nodes may need to upgrade." Causes: miners follow rules this node lacks (an outdated binary or a missed upgrade), this node follows rules they lack, or local corruption.
- **Large valid fork.** Intended to warn about a valid competing chain of 7 or more blocks within 72 blocks of the tip. `CheckForkWarningConditionsOnNewFork` is called only after a connect failure, with `vpindexToConnect.back()`, the first block above the fork point; its work above the fork is about one block, never the required 7. The branch, `pindexBestForkTip`, and `fLargeWorkForkFound` are dead. Bitcoin Core found the same and removed it ([#19905](https://bitcoincore.reviews/19905), 2020); the feature dates from the 2013 split (BIP 50) and PR #2658.

**Recovery.** Compare versions (`getpeerinfo` `subver`), inspect `getchaintips` (`invalid` status), upgrade if behind; `-reindex` when corruption is suspected.

**Proposals.** Remove the dead branch as in #19905. Add a regtest test: node A runs `invalidateblock` on a block that node B extends by 7 or more blocks; after sync, A must report the warning in `getnetworkinfo` and `getinfo`.

### 8.5 Block rate

**Mechanism.** Every 60 seconds, after initial download and at most once per 24 hours, `PartitionCheck` counts best-header blocks with timestamps in the last 4 hours and compares the count with the Poisson expectation (120 at 120-second spacing). It warns when the probability of the exact count is at most one in 109,500, which the code describes as one false positive per 50 years: 77 or fewer blocks ("check your network connection") or 167 or more ("abnormally high number of blocks generated"). The warning goes to `strMiscWarning` and `-alertnotify`; details are in the `partitioncheck` debug category.

**Meaning on Zero.** The count depends on hashrate and on the difficulty adjustment as much as on connectivity. Zero uses the zcashd averaging-window retarget: a 17-block window over median-time-past, the timespan dampened by 1/4, bounded to at most 10% harder and 30% easier per block (`nPowMaxAdjustUp` 10, `nPowMaxAdjustDown` 30; zcashd uses 16 and 32). Comparison.md section 4 compares this algorithm with LWMA, RT_CST_RST, and the other lineage retargets, with Zawy's analyses ([zawy12/difficulty-algorithms](https://github.com/zawy12/difficulty-algorithms), local checkout in ZKs). A deterministic simulation of that retarget after a sudden hashrate step gives the first-4-hour counts:

| Hashrate step | Blocks in the first 4 hours | Check fires |
|---------------|-----------------------------|-------------|
| x0.30 | 68 | Low |
| x0.346 | 77 | Low (boundary) |
| x0.5 | 94 | No |
| x2 | 144 | No |
| x3.09 | 167 | High (boundary) |
| x5 | 197 | High |

The adjustment absorbs smaller steps within the window, so without noise the check fires only for a drop of about 65% or more, or a rise to about three times the hashrate. Poisson noise then widens the trigger band somewhat. A rise of that size is what a rented-hashrate attack looks like; because the count uses best-header timestamps, a released private chain mined that fast can also trigger it. Header timestamps are miner-set, within the median-time-past and 2-hour future limits.

**History.** Added in Bitcoin Core PR [#5947](https://mirror.b10c.me/bitcoin-bitcoin/5947/) (Gavin Andresen, 2015), switched to header timestamps in #6256, disabled in 0.12.1, and removed in [#8275](https://mirror.b10c.me/bitcoin-bitcoin/8275/) (2016) for false positives. zcashd kept it and added the Blossom spacing adjustment that Zero inherited.

**Proposals.** Replay mainnet history (block timestamps from the index or `chain_stats.py`) through the same 4-hour window and record how often each threshold would have fired, together with the hashrate swings behind them. Record a year of mainnet block counts per 4-hour window (`chain_stats.py` or the block index) and count how often the thresholds would have fired. Then keep it with the warning cleared when the rate returns to normal, or remove it as Bitcoin Core did. Test instance: regtest with mock time, a burst of blocks inside 4 hours, then check `getnetworkinfo` `warnings`.

### 8.6 End of support

**Mechanism.** `DEPRECATION_HEIGHT = APPROX_RELEASE_HEIGHT + WEEKS_UNTIL_DEPRECATION * 7 * 24 * 30` (`src/deprecation.h`); `7 * 24 * 30` is blocks per week at 120-second spacing. Values: 1,385,000 + 520 * 5,040 = **4,005,800**. From 4 weeks before (height 3,985,640) the node logs a warning and runs `-alertnotify` once, and again on each startup; at the height it shuts down and refuses to restart. Mainnet only; regtest and testnet ignore it. `getdeprecationinfo` reports the height.

**Current values.** `APPROX_RELEASE_HEIGHT` 1,385,000 corresponds to about May 2022 and has not been raised since. With the tip near 2.55M (September 2026), the halt is about 1.46M blocks away, around April 2032. The 520-week window therefore runs from 2022, not from the v4.1.0 release.

**History on Zero.** Through 2019 merges carried zcashd's per-release values; CryptoForge set a 13-week window in 2018 and new heights in 2019 and 2020, and a 2021 commit added a year. Commit `5f9c6a410` (2022-05-30) moved the window to 520 weeks ("Push deprecation out 10 years"), when v3.3.0 was about to halt; it has not been refreshed since.

**Field.** Values from local checkouts in ZKs:

| Project | Checkout | Release height | Window | Warning | Policy |
|---------|----------|----------------|--------|---------|--------|
| zcashd | 2026-01 | 3,198,076 | 16 weeks (`RELEASE_TO_DEPRECATION_WEEKS`) | 2 weeks | Raised at every release (127 commits since 2017); window shortened for RCs and upgrades |
| Zebra | 2026-06 | 3,382,189 (`ESTIMATED_RELEASE_HEIGHT`) | 37 days (`EOS_PANIC_AFTER`, cut for NU7) | 14 days before | Panics at the end-of-support height |
| Ycash | 2026-04 | 2,244,000 | Disabled (`INT_MAX - 1`) | 2 weeks | Turned off |
| Zclassic | 2024-12 | 99,235,543 | 70 weeks | 2 weeks | Effectively off: release height far beyond the chain |
| Horizen | 2025-07 | 1,775,300 | 24 weeks | 2 weeks | History not in the shallow checkout |
| Flux | 2025-12 | 2,127,000 | 104 weeks | 4 weeks | History not in the shallow checkout |
| Pirate | 2026-01 | from `DEPRECATION_HEIGHT` 4,820,333 | 52 weeks | 2 months | Halt height set directly; 38 updates through 2024 |
| TENT | 2021-11 | 1,870,000 | 100 weeks | 96 days (comment says 4 weeks) | Inactive since 2021 |

zcashd releases about every 6 weeks and supports each for about 16 weeks; at its end-of-support height the binary halts and refuses to restart ([zcashd release support](https://zcash.github.io/zcash/user/release-support.html)). The field splits between short windows with frequent releases (zcashd, Zebra), long windows (Flux, Pirate, TENT, Zero), and disabling (Ycash, Zclassic).

**Proposals.** Set `APPROX_RELEASE_HEIGHT` to the tip at each release tag and check it in `zcutil/check-release.sh` (with REL-09). Choose the window deliberately: a long window lowers upgrade pressure, a short one keeps old binaries from lingering through consensus changes.

### 8.7 Finality and fork-choice designs

Background for the decision in section 8.3, from the source of each project (checkouts in ZKs) and published reviews.

**Horizen delay penalty.** Mechanism in section 8.3. Introduced after the June 2018 38-block attack ([Horizen proposal](https://blog.horizen.io/zencash-leads-the-fight-against-the-51-attack/)). Daira Hopwood's critique: after a temporary two-sided network partition, each side sees the other's blocks as late and penalizes them, so the partition can become permanent; Horizen answered that a penalty decays by one per block on the accepted chain ([CoinDesk](https://www.coindesk.com/tech/2018/10/10/a-solution-to-cryptos-51-attack-fine-miners-before-it-happens)). Further limits: "late" is judged against each node's own view, so nodes with different connectivity can disagree; startup sync is exempt; an attacker who publishes each block on time but outpaces the network gains nothing from it, while one who withholds loses. No other project in the ZKs checkouts adopted it.

**Peer penalties.** A peer that sends a block or header conflicting with local finality is scored, and at 100 points disconnected and banned:

| Trigger | Score | Projects |
|---------|-------|----------|
| Header forks below the last checkpoint | 100 | zcashd, Ycash, Zclassic, Horizen, TENT, Firo, Zero (`ContextualCheckBlockHeader`); Bitcoin Core until checkpoints were removed |
| Block below the last dPoW notarization | 100 | Pirate, Hush |
| Spork with a bad signature | 100 | Zero, TENT, Dash lineage |
| Block conflicting with a finalized block | 20 | Zclassic |
| Header deeper than the reorg bound | 10 | Flux |
| Block conflicting with a finalized block | none (cached invalid) | Bitcoin Gold |

Banning makes the node stop hearing the conflicting chain, which is the intent against an attacker and a risk during an honest split: the node cannot learn that it is on the minority side.

**Rolling finalization (Bitcoin ABC, Bitcoin Gold, Zclassic).** Bitcoin ABC 0.18.5 (November 2018) finalizes the block 10 below the tip (`-maxreorgdepth`, -1 disables) and refuses any chain conflicting with it; `finalizeblock`, `parkblock`, and `unparkblock` let operators override, and deep reorgs are parked until enough extra work accumulates ([release notes](https://bitcoinabc.org/doc/release-notes/release-notes-0.18.5.html)). Bitcoin Gold carries the same code with depth 9 (`-minfinalizationdepth`) and an 80-minute minimum age (`-minfinalizationage`): a block is finalized only after its header has been known for that long, so an attacker cannot force finalization by releasing a deep chain quickly. In the BTG checkout the code arrived in a December 2024 merge; during its July 2020 attack BTG instead shipped an emergency checkpoint. Zclassic carries the ABC code with depth 10 and a 20-point peer penalty. Reception: BitMEX Research judged that rolling checkpoints defend against deep hostile reorgs but raise the chain-split risk, because an attacker who reorgs 9 blocks while the network finds the 10th can split nodes by timing ([BitMEX Research](https://www.bitmex.com/blog/bitcoin-cash-abcs-rolling-10-block-checkpoints)). MIT DCI research on BTG's 2020 attacks found double-spend counterattacks by victims in the wild, an alternative defense that needs no protocol change ([MIT DCI](https://dci.mit.edu/dci-news/2020/5/4/reorgs-on-bitcoin-gold-counterattacks-in-the-wild-medium-post-by-james-lovejoy)). The ABC age rule is the main difference: it ties finality to observed time, not only to depth.

**Avalanche post-consensus (eCash).** Since September 2022, eCash nodes holding staked coins poll each other with the Avalanche protocol about each new PoW block and finalize it once the poll converges, usually within one block interval; a finalized block cannot be reorged regardless of work, and exchanges credit after one confirmation. Pre-consensus on transactions followed in November 2025 ([eCash post-consensus](https://e.cash/blog/post-consensus)). It replaces depth with a stake-weighted vote, a subsystem comparable in size to Dash ChainLocks.

**Flux.** Rejects headers 40 or more blocks deep at header acceptance, stays up, and widened the bound to 5000 for a planned upgrade window (section 8.3). For: no shutdown, no download of the deep fork, a per-height override for planned events. Against: a split persists silently; the bound is enforced before the fork is even downloaded, so the node cannot evaluate it; 40 blocks at Flux's 30-second Proof-of-Node spacing (`nPonTargetSpacing`) is 20 minutes, shorter than Zero's 99 blocks at 2 minutes. Relevance to Zero: the header-level check and the height-window override are the parts worth considering for option 2; the bound itself would follow from Zero's witness cache, not from Flux.

**Configurable bounds and recovery.** zcashd dropped a configurable `chainforkdecision` during review of #2463 and kept a fixed bound with recovery by software upgrade. Projects that made it configurable: Pirate and Hush (`-maxreorg`, with a restart hint), Zclassic and Bitcoin ABC (`-maxreorgdepth`), Bitcoin Gold (`-minfinalizationdepth`, `-minfinalizationage`), Firo (`-allowdeepreorg` to bypass). Recovery tools in those trees: `finalizeblock`, `parkblock`, `unparkblock`, plus the Bitcoin-era `invalidateblock` and `reconsiderblock`, which Zero has. A configurable bound helps recovery only together with a deep enough witness cache; on Zero a value above 99 would empty the cache.

**Reorgs deeper than coinbase maturity.** A coinbase output becomes spendable after `COINBASE_MATURITY` blocks. A reorg deeper than that can remove a coinbase whose outputs were already spent; every transaction descending from it becomes permanently invalid and cannot be re-mined on the new chain, unlike ordinary transactions that return to the mempool. This is why Bitcoin set maturity to 100 and why zcashd tied its bound to `COINBASE_MATURITY - 1`. Zebra's 1000-block window exceeds Zcash's maturity of 100, and Comparison.md section 14.5 notes that it accepts such losses inside the window. Zero's maturity of 720 is far above its bound of 99, so the coinbase rule is not the binding constraint; the witness cache is, and it is recoverable by rebuilding (`-walletwitness=rebuild`, `-rescan`, or `-reindex`), at a time cost.

### 8.8 Sync and reindex acceleration

| Mechanism | What it does | Trust | Projects |
|-----------|--------------|-------|----------|
| Checkpoints | Below the last checkpoint, skip scripts and proofs (`fExpensiveChecks`); reject forks below it | Hard-coded hashes | zcashd (3,000,000, July 2025), Ycash, Pirate (3,817,031), Flux, Zclassic, Horizen, TENT, Firo, Zero (700,000, last updated `724cd577f`, 2019-12-21); Bitcoin Core removed 2025 |
| `nMinimumChainWork` | Treat the node as syncing, and ignore chains, below a hard-coded work total | Hard-coded work | Bitcoin Core and the zcashd lineage, Zero |
| `assumevalid` | Skip script checks for ancestors of one hard-coded block; all other validation runs | Hard-coded hash | Bitcoin Core (block 912,683 in the October 2025 checkout), Bitcoin Gold, Firo; not zcashd or Zero |
| Headers presync | Before storing a peer's headers, check in compressed form that they reach `nMinimumChainWork`, then re-download and store them | None | Bitcoin Core since PR #25717 (2022) |
| assumeutxo | Load a UTXO-set snapshot at a hard-coded height, sync from there, validate history in the background | Hard-coded snapshot hash | Bitcoin Core 28 (mainnet snapshot at 840,000) |
| Zebra checkpoint verifier | Accept segments of at most 400 blocks or 32 MiB as hash chains to the next checkpoint; mandatory up to Canopy | Hard-coded hashes | Zebra (14,049 mainnet checkpoints, last 3,373,206) |

**Bitcoin Core.** Checkpoints were replaced, not `assumevalid`: `assumevalid` is still raised every release. Presync ([PR #25717](https://github.com/bitcoin/bitcoin/pull/25717)) closed the remaining checkpoint role, the memory exhaustion from low-work headers. A node first downloads a peer's headers without storing them, keeping only the running work and a small salted commitment for every few hundred headers; once the work passes `nMinimumChainWork`, it downloads the headers again, checks them against the commitments, and stores them. Its tests: the unit test `headers_sync_chainwork_tests` drives the state machine with a low-work chain (rejected) and a sufficient one (accepted); the functional test `p2p_headers_sync_with_minchainwork.py` shows that nodes with a work requirement keep no headers from a short chain, accept them once the chain is long enough, report presync height in `getpeerinfo`, and still complete a 2000-block reorg; the fuzz target `p2p_headers_presync` feeds random header sequences. With those in place, PR #31649 removed checkpoints.

**Zebra.** Checkpoints are the sync method below the mandatory height, not only a speed-up. Zebra checkpoint-verifies everything before Canopy because it does not implement some older rules: it never verifies Sprout-on-BCTV14 proofs, and it cannot check the ZIP 212 note-plaintext grace period after Canopy with librustzcash, so the mandatory height sits after that period ([zebra_consensus](https://doc-internal.zebra.zfnd.org/zebra_consensus/index.html), [#8430](https://github.com/ZcashFoundation/zebra/issues/8430)). Above the last checkpoint, blocks are fully verified and kept in the non-finalized state, the 1000-block rollback window. The two do not interact in practice: checkpoints are generated from a synced node and shipped with releases months behind the tip, so the rollback window always lies above them; a reorg cannot cross a checkpoint.

**Zero.** zcashd lineage: checkpoints, `nMinimumChainWork`, no `assumevalid`, no presync. Zero also skips PHGR (BCTV14) Sprout proof verification, as zcashd does (ZcashFixes.md). Checkpoints stopped at 700,000 when per-release maintenance ended with the 2019 maintainer, not by decision. Opportunities, cheapest first:

1. Refresh checkpoints and `nMinimumChainWork` every release: sync and `-reindex` skip script and proof checks up to the new height.
2. Port `assumevalid`: skips scripts without rejecting forks, so it speeds sync without the finality side effect; shielded proofs would need the same treatment to matter for Zero.
3. Presync and assumeutxo: large ports from a much newer Bitcoin Core; assumeutxo would also need the shielded state (note commitment trees, nullifier sets) in the snapshot.

### 8.9 Related items and tests

| Mechanism | Items | Tests | Documents |
|-----------|-------|-------|-----------|
| Reorg bound | CON-04; DOC-02 (operator runbook); ZN-01 phase D (applied reorgs, ZeroNodeDev.md section 3); TST-WITNESS-REINDEX (witness rebuild) | `reorg_limit.py` (Tier B fail, cache-tip heights); `wallet_witness_defer.py` | ZeroNodes.md section 5; WitnessReindex.md |
| Heavier invalid chain | CON-04 | None; proposed in section 8.4 (`invalidateblock` on one node, extension on another) | -- |
| Large valid fork | CON-04 (remove dead code) | None | -- |
| Block rate | CON-04; TNT-09 (LWMA3 retarget, deferred) | None; proposed in section 8.5 | Comparison.md section 4 |
| End of support | CON-04; REL-09 (release check) | `DeprecationTest.*` (12 GTests), including `AlertNotify` | BUILD_ZERO section 4.6.1 (`-alertnotify` build flag) |
| All, reporting | OPS-CONF-UNIFY (`-alertnotify` text); DOC-02 | `DeprecationTest.AlertNotify`, `BlockNotifyDefaultSkipsShell`, `WalletNotifyDefaultSkipsShell` | -- |

### 8.10 Actions

1. Observability: `AlertNotify` and a log marker before the reorg-bound shutdown; list the RPC fields monitors should poll.
2. Tests: make `reorg_limit.py` pass and move it into a tier; add the invalid-chain test (section 8.4) and the block-rate test (section 8.5).
3. Code: remove the dead large-fork branch; clear `strMiscWarning` when the block rate is normal again, or remove the check after the replay in section 8.5.
4. Release: raise `APPROX_RELEASE_HEIGHT` at every tag and check it with REL-09; refresh checkpoints and `nMinimumChainWork` for sync, not as reorg protection.
5. Operator runbook for all four events, published with DOC-02.
6. Decisions: reorg-bound behavior (section 8.3 options 2 and 3) and the end-of-support window.

### 8.11 References

- zcashd reorg limit: [PR #2463](https://github.com/zcash/zcash/pull/2463), [issue #1302](https://github.com/zcash/zcash/issues/1302); end of support: [release support](https://zcash.github.io/zcash/user/release-support.html); `zcraw*` removal: commit `37921677e` (v5.4.0).
- Zebra: [5.2.0 rollback window](https://zfnd.org/zebra-5-2-0-wider-rollback-window/), [PR #10650](https://github.com/ZcashFoundation/zebra/pull/10650), [issue #11403](https://github.com/ZcashFoundation/zebra/issues/11403), [checkpoints](https://github.com/ZcashFoundation/zebra/blob/main/zebra-chain/src/parameters/checkpoint/README.md).
- Bitcoin Core: fork warnings [review of #19905](https://bitcoincore.reviews/19905); partition check [#5947](https://mirror.b10c.me/bitcoin-bitcoin/5947/), [#8275](https://mirror.b10c.me/bitcoin-bitcoin/8275/); checkpoint removal [#31649](https://github.com/bitcoin/bitcoin/pull/31649); alert retirement [bitcoin.org](https://bitcoin.org/en/posts/alert-key-and-vulnerabilities-disclosure).
- Other chains: [BitMEX Research on ABC rolling checkpoints](https://www.bitmex.com/blog/bitcoin-cash-abcs-rolling-10-block-checkpoints); [ECIP-1100 MESS](https://ecips.ethereumclassic.org/ECIPs/ecip-1100); [Horizen delay penalty](https://decrypt.co/3650/horizen-new-bitcoin-consensus); [Dash ChainLocks](https://dash-user-docs.readthedocs.io/projects/core/en/20.1.0/docs/guide/dash-features-chainlocks.html); [Komodo dPoW](https://komodoplatform.com/delayed-proof-of-work/); [Monero reorg, September 2025](https://www.theblock.co/post/370628/monero-shaken-by-block-reorg-reviving-tensions-with-qubic).
- Difficulty: [zawy12/difficulty-algorithms](https://github.com/zawy12/difficulty-algorithms).
- Local: Comparison.md sections 4 and 14.5; checkouts of zcash, zebra, ycash, zclassic, zen, fluxd, pirate, TENT, and bitcoin-src in ZKs.
