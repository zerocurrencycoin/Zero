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

**ID prefixes.** Rules and statuses: TODO.md "Tracking rules". Items owned here: CON, PIR, TNT, BTC, ZEC, CLN, DOC, REL, TST, DEF, and the RE- details (section 8); ZeroNodeDev.md: ZN; ZeroStruct.md: INT.

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

Pirate (sections **3.4**, **5**), TENT (section **3.5**), and Bitcoin, Zcash, and clone features (section **3.7**) are separate catalogs. **Reject**, **Skip**, and **Keep current** rows are settled. **Port**, **Review**, **Hold**, **Defer**, and **Implement** rows compete with Zcash and Bitcoin ports and Zero-local work for the next TODO slot. Prefer the Zcash fix when one exists; use Pirate or TENT only as a zcashd-shaped diff reference, or where Zero regressed upstream behavior. Commit ids in the catalogs identify the upstream change to port.

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
| TNT-09 | LWMA3 difficulty | Zcash 17-block window | **Defer**; CH-01 |
| TNT-12 | Zeronode tests | Phases A, B, C (partial), E in tree | **Implement**; ZN-01 |
| TNT-13 | Operator setup scripts | None | ZN-01 |
| TNT-14 | libsnark `-march` (`db81202`) | Absent | Review only if a libsnark cross-build fails |
| TNT-18 | `AcceptableInputs`, the collateral-only ATMP copy in `main.cpp` | Reads `-relaypriority` / `-limitfreerelay` with looser defaults than ATMP | **Postpone**; the looser collateral path is deliberate. Do not merge the flags into one global. Resolve with the wider ATMP duplication question; CH-04 |
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

### 3.7 Bitcoin, Zcash, and clone feature catalog

Features of Bitcoin Core (BTC), zcashd or Zebra (ZEC), and other clones (CLN) that Zero lacks or differs on, with a decision per row (TODO "Tracking rules"). Facts and sources: Comparison.md section 17.

| ID | Feature | Zero today | Decision |
|----|---------|------------|----------|
| BTC-01 | `assumevalid` (skip scripts below one hash, no fork rejection) | Absent | **Review**; CH-05; must cover shielded proofs to matter |
| BTC-02 | Headers presync (PR #25717) | Absent | **Hold**; CH-05; only relevant if checkpoints are dropped |
| BTC-03 | assumeutxo snapshots | Absent | **Defer**; CH-05; needs shielded state in the snapshot |
| BTC-04 | Checkpoint removal (PR #31649) | Checkpoints to 700,000 | **Hold**; RE-03 keeps consensus checkpoints for coordinated upgrades |
| BTC-05 | Dead large-fork warning removed (#19905) | Dead branch present | **Port**; RE-02 |
| BTC-06 | Partition check removed (#8275) | Present | **Review**; CH-01 replay decides |
| BTC-07 | Pruning with wallet (0.12) and manual pruning (0.14) | Pruning disabled | **Hold**; section 8.10 |
| ZEC-01 | Zebra 1000-block rollback window, stays up | 99, halts | **Review**; RE-01 |
| ZEC-02 | Per-release end-of-support height | Set 2022, 520 weeks, ends about April 2032 | **Hold**; decided 2026-10-06 (section 8.6) |
| ZEC-03 | Checkpoint list generation (`zebra-checkpoints`) | Manual | **Review**; RE-03 tooling |
| CLN-01 | Flux header-level reorg bound with planned height windows | Halt after the fact | **Review**; RE-01 |
| CLN-02 | Horizen delay penalty, `getblockfinalityindex`, `getglobaltips` | Absent | **Review** as monitoring only; RE-05. Consensus use: **Reject** |
| CLN-03 | Horizen future-time limit against median-time-past | Bitcoin 2-hour limit | **Review**; CH-06 |
| CLN-04 | TENT minimum spacing (block time at least parent + spacing / 3) | Absent | **Review**; CH-06 |
| CLN-05 | TENT shielded-pool closure (t-to-z rejected, then all shielded transactions after 7 days) | -- | **Reject**; input to the Sprout wind-down: never close a pool to spends |
| CLN-06 | Pirate `rescan` RPC with a start height | Startup `-rescan` only | **Port**; RE-07 step 5 |
| CLN-07 | Bitcoin ABC and Gold `finalizeblock`, `parkblock`, minimum finalization age | Absent | **Review**; RE-04 tools, RE-06 |

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

**DOC-CONVENTIONS -- Rules not yet in AGENTS.md.** Code-comment and document rules to adopt into AGENTS.md; the documentation rules already there (filler, partitioning, references, ASCII, headings) are not repeated here.

- *Sizing.* Content drives length: what a reader needs to use, change, or validate the code or decision; nothing that goes stale.
- *Inline code comments.* Explain why: invariants, cross-component constraints, consensus and locking requirements. No task IDs, status notes, dates, change history, personal paths, or references to planning documents.
- *Function and class documentation.* Doxygen `/** ... */` on interfaces and non-trivial functions: purpose, parameters, returns, preconditions, locking and thread safety, failure behavior.
- *File headers.* Copyright and license; optionally a short purpose. No change logs.
- *Tests.* Scenario, choice of heights and amounts, known failures, how to run. Python tests open with a docstring.
- *Scripts.* Shebang, copyright for Zero-authored scripts, one-line purpose; `usage()` behind `-h` / `--help` (Usage, Modes or commands, Options, Env) when the script takes options.
- *Upstream, vendored, ported code.* Keep original comments, including copyright notices; correct only factual errors; keep diffs minimal.
- *Public documents.* No references to internal documents or external files; current state only; no transient values.
- *Internal documents.* External documents by name, never by filesystem path. History only where a decision's rationale depends on it. Transient counts only in section 7 Validation counts.
- *Reference records* (for example ZcashFixes, Comparison.md): keep comparisons, timelines, and third-party detail; link sources inline.
- *Cutting.* Move unique facts rather than delete them; verify done and open claims against the code.

**DOC-FR-NAMING.** Reconcile `vFoundersReward`, FoundersReward, `developmentfee`, and GBT `founders` naming across code and ZERO_COIN. Founders destination options (FR-ROTATE, FR-TADDR, FR-Z) are product decisions, not release gates.

**GitHub issues.** #70 (`getrawtransaction` lacks `size` and `fees`): `size` is implemented in `TxToJSON` and `TxToJSONExpanded` (serialized bytes via `GetSerializeSize`), documented in the `getrawtransaction` and `decoderawtransaction` help, and covered by `rpc_tests` (decoderawtransaction) and `getrawtransaction_insight.py` (getrawtransaction verbose and getblock verbosity 2 compared with the hex length). It is additive; Bitcoin Core and Zcash return the same key. Remaining: a transparent-only `fee` that requires `txindex`, with shielded fees deferred; suitable for a contributor. #69 (insight-ui and insight-api): close with a pointer to the public explorer.

### Release and infrastructure

**REL-01 -- Release signing and checksums.** Single item for packaging, signing, and checksum work on all platforms. Procedure: BUILD_ZERO sections 2.5 (packaging, signing options, `checksums.sh`) and 2.6 (checksum and sign, verify a download); release bar: TEST_ZERO section 8. Open:

1. Keys: decide who holds the GPG, Apple Developer ID, and Authenticode keys; publish the GPG key fingerprint.
2. Linux: first `release-linux.sh` run on the Ubuntu build host (`dpkg-deb`, GNU `strip`); GPG signature over `SHA256SUMS`.
3. macOS: Apple Developer Program enrollment; first `release-macos.sh --sign --notarize` run (`codesign`, `xcrun notarytool`, stapling).
4. Windows: first MXE build packaged by `release-win.sh` with Authenticode signing.

**REL-03 -- Params archival.** Postponed until after v4.1.0. `fetch-params.sh` uses upstream Zcash file names and mirrors; audit the names against `zerod` startup and verify the URLs.

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

**REL-08 -- Fixed seeds.** Postponed until after v4.1.0. Mainnet has ten DNS seeds (`seed0`..`seed9.zerocurrency.io`) but `src/chainparamsseeds.h` has empty `pnSeed6_main` and `pnSeed6_test` arrays, and `contrib/seeds/nodes_main.txt` still holds a single address from 2017. A node whose DNS lookups fail and whose `peers.dat` is empty cannot find peers. Steps: collect addresses of long-running public nodes on port 23801 (from `getpeerinfo` on well-connected nodes or a crawl of the DNS seeds); keep those with a protocol version at or above `MIN_PEER_PROTO_VERSION` and good uptime; write them to `contrib/seeds/nodes_main.txt` and `nodes_test.txt`; run `contrib/seeds/generate-seeds.py contrib/seeds > src/chainparamsseeds.h`; refresh before each release. Validation: start with an empty datadir and `-dnsseed=0` and confirm the node connects from the fixed seeds alone.

**Release flag proposals.** Gate `-g` behind `ZERO_DEBUG=1`; evaluate `-O2`; decouple `CXXFLAGS_overridden` from a bare `-g`; add `split-debug.sh` output as a `-dbg` package.

**Build host disk.** Safe to reclaim: apt lists and cache, ccache, `depends/work/*`, the repository `cache/`, MXE package and log directories, and the systemd journal.

### Testing

Items marked **contributor-ready** have clear scope and need no signing keys or consensus decisions.

**TST-07 -- Zero RPC depth.** Contributor-ready. Follows TST-01, which closed with the coverage below; implementations are in `src/wallet/rpczerowallet.cpp`.

| RPC | Covered | Open |
|-----|---------|------|
| `getalldata` | Empty-wallet gates (`rpc_zero_exclusive_tests.cpp`); populated wallet (`getalldata_scenario.py`) | Mined-transaction History and balance depth |
| `zs_listtransactions`, `zs_gettransaction`, `zs_listspentbyaddress`, `zs_listreceivedbyaddress`, `zs_listsentbyaddress` | Parameter counts; on a populated wallet, transparent spends and archived transactions after `-deletetx`, `-rescan`, `-reindex`, `-zapwallettxes`, and a reorg (`wallet_archive.py`) | Shielded outputs; filter types 1-3; watch-only |
| `getsupply` | Parameter count and fields; called at a populated tip | Values against the emission schedule at fixed heights |
| `getsaplingwitness`, `getsaplingwitnessatheight`, `getsaplingblocks` | Parameter count (`rpc_zero_experimental_tests.cpp`) | Results on a chain with Sapling notes |

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

### Wallet: transaction archive

Facts: ZeroStruct.md section 9.1. Covered by `wallet_archive.py`: history after `-deletetx`, after `-rescan`, `-reindex`, `-zapwallettxes`, and after a reorg.

| ID | Kind | Item |
|----|------|------|
| WAL-ARCHIVE-07 | Fix, research | During `-reindex` the history RPCs report archived, confirmed transactions as `orphan` until their block reconnects; gate the history RPCs during import or mark the state |
| WAL-ARCHIVE-04 | Research | Cost on large wallets: history RPC time against archive size (one disk read per entry and per transparent input); decide whether to cache input data in the archive record |
| WAL-ARCHIVE-05 | Research | Coexistence with pruning: block pinning, stored display data, or pruning only without a wallet; depends on OPS-TXINDEX-DEFAULT |

### Wallet file

Review of wallet load, read, and write (2026-10-06). Load (`CWalletDB::LoadWallet`) classifies every record failure as corrupt, non-critical, too new, or needing a rewrite, catches exceptions from deserialization, and `AppInit2` reports each case and stops startup on the fatal ones.

| ID | Kind | Item |
|----|------|------|
| WAL-FILE-01 | Fix | `CWallet::ScanForWalletTransactions` asserts that each block's Sprout and Sapling anchors exist in the chain state; a damaged chain state aborts the node during `-rescan` instead of reporting an error |
| WAL-FILE-02 | Fix | `CWallet::ReorderWalletTransactions` callers ignore the `WriteToDisk` result, so a failed order update is silent |
| WAL-FILE-03 | Review | Per-record range checks in `ReadKeyValue` (heights, indexes, note positions), archive records pointing at unknown blocks, encryption-state combinations, disk-full and lock errors on write |
| WAL-FILE-04 | Test | Damaged wallet files: truncated file, unknown record type, corrupt key, mismatched encryption; the node reports and stops, never crashes |

### RPC

**RPC-02 -- Server handling and parameters.** Research. Work queue size and reject behavior, client and server timeouts, `-rpcdatacontinue`, the list of RPCs allowed during witness rebuild, error codes for ignored or refused calls. Depends on RPC-01 (TODO).

**RPC-04 -- Chain-safety RPCs.** Research. Fork tips, extra `getchaintips` fields, a finality index (section 8.9). Depends on RE-05.

### Deferred

**Third-party upgrades not possible now.**

- OpenSSL: stay on 1.1.1w (end of life) until 3.x is audited or OpenSSL is removed; it serves RPC TLS and legacy EVP call sites. Zcash and Bitcoin removed it. Path: audit `EVP_*`, `SSL_*`, and `RAND_*` call sites, add TLS regression tests, then upgrade or remove.
- Boost above 1.88 and GTest 1.17+: require C++17. Path: C++17 readiness of `src/`, revalidated `ax_boost_*` macros, full depends rebuild.

**DEF-06 -- SwiftTX.** Never used on mainnet, although its sporks are on. Mainnet `SPORK_2_SWIFTTX` and `SPORK_3_SWIFTTX_BLOCK_FILTERING` are active (signed 1558907000). `swifttx.cpp`, `ix`, and `txlvote` stay until a signed spork turns them off or a network upgrade removes them. The hidden options `-enableswifttx` (default true) and `-swifttxdepth` (default 5) go with them. `-deleteconflicttx` (default true; with `-deletetx`, removes conflicted wallet transactions after reorgs or double spends) is unrelated and stays. Budget superblocks are off (`SPORK_9`, `SPORK_13` = 4070908800).

### Reference

**CSV inventories.** `RPCs.csv`, `RPCs_extended.csv`, `Options.csv`, `Options_extended.csv`, and `Reindex_Rescan.csv`. `Reindex_Rescan.csv` cites code as `file:function[token]` (a string to search for inside that function), never as line numbers, so references survive code movement. Update base and extended files together when adding or removing an RPC or option. The `*-hidden` category in `Options.csv` lists options parsed in `init.cpp` but absent from `--help`. A `zero_missing_sources` value of **B** marks RPCs listed only for cross-chain comparison (`dumptxoutset`, `scantxoutset`, descriptor RPCs); they are not planned ports.

### Validation counts

The only place in the documentation where test and RPC counts are recorded; update it when tiers or RPC tables change, and use it to check that a run covered what it should. Recorded 2026-10-05.

| Set | Count | Regenerate |
|-----|------:|-----------|
| Tier A (gate) | 10 | `./qa/pull-tester/rpc-tests.sh -list-csv` |
| Tier B pass | 33 invocations (32 scripts; `txn_doublespend` twice) | same |
| Ext pass | 8 | same |
| `-all` total | 51 invocations | same |
| Bfail debug / retired | 28 / 8 | same |
| Efail | 5 | same |
| `RPCs.csv` rows / `zero=y` | 278 / 172 | count rows in `RPCs.csv` |

---

## 8. Chain safety

How `zerod` detects, reports, and reacts to abnormal chain conditions, and what Zero should change: reorgs beyond the local bound, heavier invalid chains, abnormal block rates, end of support, checkpoints, recovery operations, and pruning. Mainnet values: 120-second blocks (Blossom is not active, so 720 blocks per day), `COINBASE_MATURITY` 720, `MAX_REORG_LENGTH` 99, checkpoints every 100,000 blocks to 700,000. Cross-project facts and history: Comparison.md section 17; this section keeps Zero facts, options, and decisions. Tracking: RE- items (section 8.13).

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
- **`-alertnotify`.** Runs only in builds with `ENABLE_SYSTEM_COMMAND`; release builds log the skip. It fires for deprecation, the invalid-chain warning, and the block-rate warning. It does **not** fire for the reorg-bound shutdown.
- **Gap.** A release binary has no push channel. Monitoring must poll the RPC warning fields or watch `debug.log` and process exit.

### 8.3 Reorg bound

**Mechanism.** Before disconnecting any block, `ActivateBestChainStep` computes the reorg length from the old tip to the fork point. If it exceeds `MAX_REORG_LENGTH` (99), the node logs the old tip, new tip, and fork point, prints "the node is shutting down for your safety", and calls `StartShutdown()` without applying the chain. The same check runs at startup for a rewind of insufficiently validated blocks; `intendedRewind` exempts two Zcash testnet heights that do not exist on Zero's networks. After a restart peers offer the same heavier chain and the node stops again.

**Origin on Zero.** Inherited from zcashd, where the bound equals `COINBASE_MATURITY - 1` and protects the wallet witness cache (`WITNESS_CACHE_SIZE = MAX_REORG_LENGTH + 1`). Zero raised maturity to 720 and kept 99 (`src/main.h`: "COINBASE_MATURITY of 720 is too much"), so on Zero the bound guards the witness cache only.

**Assessment.** Bitcoin follows the most-work chain at any depth; every bound is a deviation that must justify itself, and halting is the costliest form.

- **What triggers it.** In Nakamoto's model, a miner with hashrate share q < 1/2 catches up from z blocks behind with probability (q/(1-q))^z (Bitcoin whitepaper, section 11). For z = 100: q = 0.30 gives 1.6e-37, q = 0.40 gives 2.5e-18, q = 0.45 gives 1.9e-9, q = 0.49 gives 0.018. A reorg of 100 or more blocks therefore means a majority miner, a miner very close to half, or an honest split (a validity disagreement or a long partition); it is never ordinary chance.
- **What halting does to the majority rule.** If a fraction h of the honest hashrate runs on nodes that halt (pools run `zerod`), honest block production drops to (1 - h) of what it was, and the attacker's share of the remaining production becomes q / (q + (1 - h)(1 - q)). With every pool halting (h = 1) the attacker produces 100% of new blocks. Halting removes honest participants at the moment the most-work rule needs them, which converts a temporary, rented majority into the only growing chain.
- **Who follows which chain.** Halted nodes stay on the original chain but stop serving it; nodes that start or sync afterwards (new installs, explorers, light-wallet servers) see only the attacker's heavier chain and follow it. The network is split until operators coordinate.
- **Duration.** The attacker needs at least 100 honest blocks after the fork point, about 3.3 hours at 120-second spacing once the public chain's difficulty has adjusted to the withdrawn hashrate (17-block window, at most 30% easier per block).
- **What halting protects.** A halted node never applies the attacker's history, so it never reverses deposits it already credited. That protection exists only locally; the organization still has to choose a chain to rejoin, and every halted node needs manual action.
- **Record.** zcashd's recovery path, a release with a checkpoint, was used only for planned testnet rollbacks (heights 252,500 and 584,000); no mainnet use is recorded. Zebra moved to a 1000-block window that stays up.

**Options for RE-01.**

1. **Follow most work, as Bitcoin does.** Remove the halt. When a reorg exceeds the witness cache, clear the cache and rebuild it from the chain (`RebuildWitnessCacheForChainTip`, the path behind `-walletwitness=rebuild`); wallet RPCs are already gated during a rebuild. Raise an RPC warning and `-alertnotify` for any reorg deeper than a reporting threshold. Verify first how `DecrementNoteWitnesses` behaves when the rewind passes the cached depth; Zero's code differs from the zcashd assertion that caused #1302.
2. **Reject and stay up** (Flux, Zebra): keep a bound, refuse the deeper chain, keep serving the current one, warn persistently. Still a deviation from most work, without the halt.
3. **Raise the bound to at most 719.** A reorg deeper than coinbase maturity can delete a coinbase whose outputs were already spent; every transaction descending from it becomes permanently invalid and cannot be re-mined. Zero's maturity is 720, so a bound up to 719 never reaches that case, and the witness cache grows with the bound (about 200 KiB per note at 100 entries, about 1.4 MiB at 720). zcashd derivatives with maturity 100 cannot raise their bound past 99 without accepting such losses; Zebra's 1000-block window does accept them, which Zero should not copy. Combinable with options 1 and 2.
4. **Keep the halt, add notification and a runbook.** Minimum change; keeps the defect described above.
5. **Finality mechanisms** (delay penalty, rolling finalization, quorum signing): consensus changes, only with a coordinated network upgrade.

Current behavior has no runtime or compile-time option to stay up: `MAX_REORG_LENGTH` is a compile-time constant, and the witness cache size follows it. After a halt the operator can restart and `invalidateblock` the competing branch's first block; the node then stays on its chain, which is option 2 done by hand. A runtime option is possible (Pirate's `-maxreorg` pattern, bounded at 719 here, with the cache sized from it, or a policy switch between halt, reject, and follow) and belongs with RE-01.

Recommendation: option 1, after the witness-cache verification and the recovery tests in section 8.8, with the reporting threshold and witness cache sized per option 3; option 4's notification first, because it is small and helps under every option.

### 8.4 Heavier chain and large fork warnings

**Mechanism.** Two branches in `CheckForkWarningConditions`, both suppressed during initial block download:

- **Invalid chain.** `pindexBestInvalid` tracks the most-work block that failed validation (`InvalidChainFound`). When it has more than 6 blocks of work above the tip, the node logs "Found invalid chain at least ~6 blocks longer than our best chain. Chain state database corruption likely.", runs `-alertnotify`, and sets `fLargeWorkInvalidChainFound`. `GetWarnings` then reports "We do not appear to fully agree with our peers! You may need to upgrade, or other nodes may need to upgrade." Causes: miners follow rules this node lacks (an outdated binary or a missed upgrade), this node follows rules they lack, or local corruption.
- **Large valid fork.** Intended to warn about a valid competing chain of 7 or more blocks within 72 blocks of the tip. `CheckForkWarningConditionsOnNewFork` is called only after a connect failure, with `vpindexToConnect.back()`, the first block above the fork point; its work above the fork is about one block, never the required 7. The branch, `pindexBestForkTip`, and `fLargeWorkForkFound` are dead. Bitcoin Core found the same and removed it.

**Recovery.** Compare versions (`getpeerinfo` `subver`), inspect `getchaintips` (`invalid` status), upgrade if behind; `-reindex` when corruption is suspected.

**Proposals.** Remove the dead branch as in #19905. Add a regtest test: node A runs `invalidateblock` on a block that node B extends by 7 or more blocks; after sync, A must report the warning in `getnetworkinfo` and `getinfo`.

### 8.5 Block rate

**Mechanism.** Every 60 seconds, after initial download and at most once per 24 hours, `PartitionCheck` counts best-header blocks with timestamps in the last 4 hours and compares the count with the Poisson expectation (120 at 120-second spacing). It warns when the probability of the exact count is at most one in 109,500, which the code describes as one false positive per 50 years: 77 or fewer blocks ("check your network connection") or 167 or more ("abnormally high number of blocks generated"). The warning goes to `strMiscWarning` and `-alertnotify`; details are in the `partitioncheck` debug category.

**Meaning on Zero.** The count depends on hashrate and on the difficulty adjustment as much as on connectivity. Zero uses the zcashd averaging-window retarget: a 17-block window over median-time-past, the timespan dampened by 1/4, bounded to at most 10% harder and 30% easier per block (`nPowMaxAdjustUp` 10, `nPowMaxAdjustDown` 30; zcashd uses 16 and 32). A deterministic simulation of that retarget after a sudden hashrate step gives the first-4-hour counts:

| Hashrate step | Blocks in the first 4 hours | Check fires |
|---------------|-----------------------------|-------------|
| x0.30 | 68 | Low |
| x0.346 | 77 | Low (boundary) |
| x0.5 | 94 | No |
| x2 | 144 | No |
| x3.09 | 167 | High (boundary) |
| x5 | 197 | High |

The adjustment absorbs smaller steps within the window, so without noise the check fires only for a drop of about 65% or more, or a rise to about three times the hashrate. Poisson noise then widens the trigger band somewhat. A rise of that size is what a rented-hashrate attack looks like; because the count uses best-header timestamps, a released private chain mined that fast can also trigger it. Header timestamps are miner-set, within the median-time-past and 2-hour future limits.

**Proposals.** Replay mainnet history through the same 4-hour window with `contrib/stats/block_rate_replay.py` and record how often each threshold would have fired, together with the difficulty and gaps behind them (CH-01). Then keep it with the warning cleared when the rate returns to normal, or remove it as Bitcoin Core did. Test instance: regtest with mock time, a burst of blocks inside 4 hours, then check `getnetworkinfo` `warnings`.

### 8.6 End of support

**Mechanism.** `DEPRECATION_HEIGHT = APPROX_RELEASE_HEIGHT + WEEKS_UNTIL_DEPRECATION * 7 * 24 * 30` (`src/deprecation.h`); `7 * 24 * 30` is blocks per week at 120-second spacing. Values: 1,385,000 + 520 * 5,040 = **4,005,800**. From 4 weeks before (height 3,985,640) the node logs a warning and runs `-alertnotify` once, and again on each startup; at the height it shuts down and refuses to restart. Mainnet only; regtest and testnet ignore it. `getdeprecationinfo` reports the height.

**Current values.** `APPROX_RELEASE_HEIGHT` 1,385,000 corresponds to about May 2022 and has not been raised since. With the tip near 2.55M (September 2026), the halt is about 1.46M blocks away, around April 2032. The 520-week window therefore runs from 2022, not from the v4.1.0 release.

**History on Zero.** Through 2019 merges carried zcashd's per-release values; CryptoForge set a 13-week window in 2018 and new heights in 2019 and 2020, and a 2021 commit added a year. Commit `5f9c6a410` (2022-05-30) moved the window to 520 weeks ("Push deprecation out 10 years"), when v3.3.0 was about to halt; it has not been refreshed since.
**Decision (2026-10-06).** v4.1.0 keeps `APPROX_RELEASE_HEIGHT` 1,385,000 and the 520-week window: end of support stays at height 4,005,800, about April 2032. Revisit with the next release that should force an upgrade.

### 8.7 Checkpoints

**What a checkpoint does in Zero.** Four effects, all keyed on the highest checkpoint already in the block index (`GetLastCheckpoint`): its ancestors skip script checks and Sprout and Sapling proof verification in `ConnectBlock` (`fExpensiveChecks`), which shortens sync and `-reindex`; headers forking below it are rejected with a 100-point peer penalty (`ContextualCheckBlockHeader`); its height and transaction counts drive `verificationprogress` and rescan progress; its height gates inventory relay during initial download. Zero has no `assumevalid`.

**Trust.** Skipping checks below a checkpoint trusts that exactly that history, committed by the hash chain, was validated when mined and by every node synced before, and that release reviewers checked the hash. Zero's pre-Sapling Sprout proofs (PHGR, BCTV14, before height 492,850) are never verified, as in zcashd; the ZIP 209 turnstile bounds the Sprout pool balance. Zero never activated Canopy, so ZIP 212 does not apply.

**Older checkpoints.** They act only during initial sync, before the newest checkpoint's header arrives; with headers-first sync that window is short. Keeping the existing ones costs nothing and changes nothing; new releases need not add intermediate ones.

**Policy (RE-03).** A checkpoint changes which chains a node accepts, so a consensus checkpoint is a consensus change: ship one only with a coordinated network upgrade, when operators and pools are watching the transition. Between upgrades, use **advisory checkpoints**: expected hashes at intermediate heights that the node compares and reports on (log, RPC warning, `-alertnotify`), that validate indexes and reindex progress, and that serve as named restart points, without rejecting chains or skipping checks. A sync speed-up without the consensus effect is `assumevalid`-style skipping, which would have to cover shielded proofs to matter for Zero.

**Refresh procedure** (for the next coordinated upgrade, and for advisory checkpoints each release):

1. Height: the highest multiple of 10,000 at least 30 days (21,600 blocks) below the tip.
2. Data from a synced node: `getblockhash`, `getblock` (`time`, `chainwork`), `getchaintxstats 4096 <hash>` (transaction count and rate for `nTimeLastCheckpoint`, `nTransactionsLastCheckpoint`, `fTransactionsPerDay`); `nMinimumChainWork` from the block's `chainwork`.
3. The same values from a second, independently synced node and the explorer.
4. Validation: `Checkpoints_tests`, `verificationprogress` near 1, a timed `-reindex` of a copied datadir before and after.
5. Testnet likewise.
6. Tooling: a `zcutil/` script that prints the `chainparams.cpp` lines from two nodes and fails on mismatch.

### 8.8 Recovery operations

**Recovery steps.** Witness rebuild, rescan, and reindex nest: each includes the previous. Their code paths and startup order: ZeroStruct.md section 11.2a.

**Witness cache.** Up to 100 witnesses per note, at most about 2 KiB each, so about 200 KiB per note in memory and in the wallet file. A reorg deeper than the cache cannot rewind witnesses; they are rebuilt from the chain. Any wider window (option 2 or a temporary window) needs a larger cache or a planned rebuild.

**Runbook outline** (published with DOC-02; Zero tools only):

1. Detect: RPC warning fields, `getchaintips` (`valid-fork`, `invalid`), `debug.log` reorg and shutdown lines, explorer and pool reports.
2. Confirm: compare tips and versions across several nodes (`getchaintips`, `getpeerinfo` `subver`); classify as attack, honest split (validity disagreement or partition), or local fault.
3. Decide: which branch is canonical; for an attack, the branch seen first by most honest nodes; for a validity split, the branch following the current rules.
4. Act on nodes: `invalidateblock` on the rejected branch's first block, `reconsiderblock` to undo; restart after a halt with the same; `-reindex` for local corruption.
5. Coordinate: pools and exchanges raise confirmation counts or pause deposits; a release with an advisory or, at a coordinated upgrade, a consensus checkpoint.
6. Recover wallets: witness rebuild, rescan, or reindex as needed; verify balances.

**Recovery tests.**

1. `reorg_limit.py` repaired: a 100-block reorg, then the chosen behavior (halt and restart with `invalidateblock`, or follow with witness rebuild).
2. `invalidateblock` and `reconsiderblock` between two regtest branches.
3. A deep reorg with shielded notes, then witness rebuild; balances and `getalldata` match.
4. Timed `-reindex` of a mainnet copy with and without a newer checkpoint.
5. The warning tests in sections 8.4 and 8.5 and the monitoring test in section 8.9.
6. Attack simulation: three regtest nodes, one mining a private chain with more work, released at depths 6, 50, 150; record warnings, behavior, and recovery.

### 8.9 Monitoring

1. Notification before the reorg-bound shutdown (`AlertNotify` and a fixed log marker), whatever RE-01 decides.
2. Late-block tracking without consensus effect: record each header's arrival time and the active height at arrival; compute lateness and a Horizen-style score per fork tip; expose them in `getchaintips` and a fork-tips RPC modeled on Horizen's `getglobaltips`; warn on a late fork near the tip's work and on any reorg deeper than 6 blocks. Test: two regtest nodes, a private chain on one, reconnect, check fields and warnings.
3. External monitoring: a script polling several Zero nodes (`getchaintips`, warning fields, best hash per height), in the spirit of ForkMonitor.

### 8.10 Pruning

**State.** `-prune` and its checks are commented out in `init.cpp` (CryptoForge, 2020-11-19, `cf2282a1f`, the same day `txindex` became mandatory); the pruning code stays compiled and dormant; `getblockchaininfo` reports `pruned: false`; `pruning.py` is in the extended fail list.

**Node and wallet.** Pruning is a node behavior: once blocks are validated it deletes old block and undo files, keeping the UTXO set, the block index, and the most recent blocks. The wallet keeps working forward, because it follows blocks as they connect. Everything that reads a deleted block fails:

| Operation | Why it reads old blocks | Result on a pruned node |
|-----------|-------------------------|-------------------------|
| `-rescan`, key imports with rescan | Replays blocks from genesis or a birthday | Refused (zcashd: "Rescans are not possible in pruned mode") |
| Witness rebuild | Replays blocks from each note's creation to rebuild witnesses | Fails for notes older than the kept blocks |
| Transaction archive and zs_* history | `GetTransaction` reads the block holding each archived transaction and its inputs | Fails for pruned blocks; `txindex` is unavailable anyway |
| `getblock`, `getrawtransaction` for old data | Read block files | "Block not available (pruned data)" |
| Serving peers | Initial sync of other nodes needs old blocks | The node stops advertising full block service |
| Reorg deeper than the kept blocks | Needs undo data | Impossible; requires a reindex, which re-downloads everything |

**Decisions.**

1. Keep pruning disabled. The chain is about 8 GB, so the saving is small; the transaction archive, which is always on, reads old blocks through `txindex` (ZeroStruct.md section 9.1 describes it and its coexistence options); and a pruned wallet cannot rescan or rebuild witnesses below its kept blocks, which conflicts with the recovery steps in section 8.8 and with option 1 in section 8.3.
2. Leave the dormant code in place (upstream proximity, no runtime effect).
3. Keep `pruning.py` listed as failing, with its reason; `pruning_disabled.py` (Tier B) pins the disabled contract: `-prune=550` accepted and ignored, `pruned` false, every block readable after `-reindex`, no `pruneblockchain`.
4. Phases, each only if the previous shows demand:
   1. **Now:** disabled, contract pinned by `pruning_disabled.py`.
   2. **Measure:** disk use per component on a mainnet node (block files, undo files, chain state, `txindex`, Insight indexes, wallet) and operator demand. The chain is about 8 GB, so the case for pruning is weaker than for Zcash (141 GB in 2022).
   3. **Nodes without a wallet:** allow `-prune` only with `-disablewallet`, `txindex` off (needs OPS-TXINDEX-DEFAULT), and no Insight indexes. No archive, witness, or rescan conflict exists there. `MIN_BLOCKS_TO_KEEP` = 1440 (two days at 120-second blocks); a Zero-sized replacement for `pruning.py`.
   4. **Wallets:** only with archive coexistence (WAL-ARCHIVE-05) and with rescan and witness rebuild refused below the kept blocks, as zcashd does.

### 8.11 Related items and tests

| Area | Items | Tests |
|------|-------|-------|
| Reorg bound | RE-01; DOC-02; ZN-01 phase D; TST-WITNESS-REINDEX | `reorg_limit.py` (Tier B fail); `wallet_witness_defer.py` |
| Warnings | RE-02 | None yet (sections 8.4, 8.5) |
| Checkpoints | RE-03 | `Checkpoints_tests` |
| Recovery and monitoring | RE-04, RE-02 | Section 8.8 list |
| Block rate, difficulty | RE-02; CH-01 | None yet |
| End of support | Decision in section 8.6 | `DeprecationTest.*` (12 GTests) |
| Pruning | OPS-TXINDEX-DEFAULT | `pruning.py` (Efail) |

### 8.12 References

Sources: zcashd [#2463](https://github.com/zcash/zcash/pull/2463) and [#1302](https://github.com/zcash/zcash/issues/1302), the origin of the bound and the witness cache; [zawy12/difficulty-algorithms](https://github.com/zawy12/difficulty-algorithms) for the retarget analysis.

### 8.13 Items

**Status (2026-10-06): postponed until after v4.1.0.** Resume in this order:

1. RE-02: `AlertNotify` and a fixed log marker before `StartShutdown()` in the reorg-bound check (`ActivateBestChainStep[MAX_REORG_LENGTH]`, and the startup rewind check); remove `CheckForkWarningConditionsOnNewFork`, `pindexBestForkTip`, `pindexBestForkBase`, `fLargeWorkForkFound`; regtest test for the invalid-chain warning.
2. RE-04: repair `reorg_limit.py` (hard-coded heights against the cache tip); add the branch-switch and witness-rebuild recovery tests (section 8.8).
3. RE-01 prerequisite: a regtest test that rewinds a wallet with Sapling notes past `WITNESS_CACHE_SIZE` and records what `DecrementNoteWitnesses` and the RPCs do; then choose among the section 8.3 options, including a runtime bound up to 719.
4. RE-05 with CH-06: header arrival tracking and the fast-block and coinbase-only flags, after the CH-01 replay results.
5. RE-03 and RE-06 stay research.

| ID | Status | Item |
|----|--------|------|
| RE-01 | Research | Reorg-bound behavior (section 8.3): follow most work with witness rebuild, reject and stay up, or keep the halt; first verify `DecrementNoteWitnesses` on rewinds past the cache |
| RE-02 | Active | Notification and warning fixes: `-alertnotify` and a log marker before the reorg-bound shutdown; remove the dead large-fork branch; invalid-chain warning test (section 8.4) |
| RE-03 | Research | Checkpoint policy (section 8.7): consensus checkpoints only with coordinated upgrades, advisory checkpoints between, refresh procedure and tooling |
| RE-04 | Active | Recovery runbook and tests (section 8.8), published with DOC-02 |
| RE-05 | Research | Monitoring (section 8.9): late-block tracking, fork-tip RPC (RPC-04), external multi-node monitor, fast-block runs and empty blocks (CH-06) |
| RE-06 | Research | Finality mechanisms: evaluation only; adoption only with a coordinated network upgrade |
| RE-07 | Research | Recovery-step harmonization (below) |

**RE-07 -- Recovery-step harmonization.** Witness rebuild, rescan, and reindex (ZeroStruct.md section 11.2a) become explicit, observable, testable stages.

*Ready now* (design, implementation, validation in the current release line; no behavior change):

1. **Observe.** One log line per stage start and end, same format for all three: `Recovery stage <reindex|rescan|witness> start from=<height> to=<height>` and `... end blocks=<n> ms=<t>`. Status fields: `reindex_progress` (current file, height) in `getblockchaininfo`; `rescan_progress` and `witness_build` (height, done) in `getwalletinfo`. Tests read the log lines and fields.
2. **Validate**, new tests on the existing behavior:

| Test | Setup | Pass condition |
|------|-------|----------------|
| `rescan_equivalence` | Regtest wallet with transparent and Sapling activity; record balances, `getalldata 0 0`, unspent notes | After `-rescan`, after `-reindex`, and after `-walletwitness=rebuild`: identical results, notes spendable |
| `rescan_interrupt` | Start `-rescan` on a wallet with 2000 blocks of history; SIGKILL midway | Restart without flags completes; results match the baseline |
| `reindex_rescan_combined` | `-reindex -rescan` together | One replay (log shows reindex, rescan clears witnesses only), results match the baseline |
| `reindex_interrupt_resume` | Needs a test-only cap on block-file size so regtest spans several files | Restart after SIGKILL logs `Reindex resume:` with the expected start file; tip and wallet match |

*Following steps* (each after the previous, guarded by the tests above):

3. **Compose.** One startup function decides the stages from the flags and logs the plan ("reindex -> wallet replay -> witness build"); the stages keep their code.
4. **Resume rescan.** Write the wallet locator periodically during `ScanForWalletTransactions`, so an interrupted rescan continues instead of restarting.
5. **Select.** Rescan from a height and witness rebuild at runtime, as RPCs gated like the startup paths (Pirate has a `rescan` RPC with a start height).

**Reindex resume: validation and learning.** Covered by seven Boost tests (`reindex_tests.cpp`: marker round trips, resume start file, interrupted-state cursor, fresh index, `DB_FLAG` handling) and by the manual mainnet lab (AtHeight.md section 4.1 C: interrupt a short-snapshot reindex, restart without `-reindex`, check `Reindex source: resume`). The automated end-to-end test needs small block files (Bitcoin's `-fastprune` serves the same purpose). To learn more on real data: run the lab with `-debug=reindex`, record the `Reindex progress:` and `Reindex resume:` lines, time a full reindex against an interrupted and resumed one, and try the lab's edge cases (wrong flags force a wipe; a missing middle file ends the import).

---

## 9. Chain behavior

Changes to how the chain is produced, relayed, and synced, short of consensus rule changes unless stated. All Research. Cross-project facts: Comparison.md sections 2 (P2P), 4 (difficulty), 5 (coin selection), 17 (chain safety).

| ID | Item |
|----|------|
| CH-01 | Difficulty adjustment: the retarget algorithm and bounds (TNT-09 LWMA3 candidate) and the mainnet replay, first year, last 365 days, and full chain, with `contrib/stats/block_rate_replay.py` (`--first-year`, `--last-days 365`, `--all`; `--miners` for same-miner runs, `--csv` for difficulty and gaps per block) |
| CH-02 | P2P policy: peer penalty scores for conflicting chains, address relay (addrv2), ASMap, I2P (ecosystem track only; PIR-06..08) |
| CH-03 | Coin selection: which selection behavior is mandatory, which optional, and how operators choose |
| CH-04 | Mempool and relay policy: standardness, fees, the zeronode collateral acceptance path (TNT-18) |
| CH-05 | Sync acceleration: `assumevalid` covering scripts and shielded proofs, headers presync, assumeutxo (BTC-01..03); related to advisory checkpoints (RE-03) |
| CH-06 | Block timestamp spacing (below) |

**CH-06 -- Block timestamp spacing.** Research; reevaluate after the CH-01 mainnet replay, at the next coordinated upgrade planning, and after any fast-block incident.

*Rules elsewhere.* TENT Wakanda (`CheckBlockTimestamp`, [TENT main.cpp](https://github.com/TENTOfficial/TENT/blob/master/src/main.cpp)) rejects a block whose time is less than the parent's time plus one third of the target spacing; Horizen fork 6 ([fork6_timeblockfork.cpp](https://github.com/HorizenOfficial/zen/blob/master/src/zen/forks/fork6_timeblockfork.cpp)) limits block time against median-time-past instead of wall clock; Bitcoin's testnet4 timewarp fix ([BIP 94](https://github.com/bitcoin/bips/blob/master/bip-0094.mediawiki)) bounds the first block of a difficulty period against the previous one. Zero has only the Bitcoin rules: time above median-time-past of 11 blocks, at most 2 hours ahead of adjusted time.

*Honest frequencies at 120-second spacing* (exponential solve times):

| Interval below | Per block | Per day |
|----------------|-----------|---------|
| 1 s | 0.83% | 6.0 |
| 2 s | 1.65% | 11.9 |
| 10 s | 8.0% | 58 |
| 40 s (TENT rule at Zero's spacing) | 28.4% | 204 |

Two consecutive intervals under 2 s occur about every 5 days, three about every 308 days, four about every 51 years.

*Assessment.* A spacing/3 rule would make 28% of honest blocks invalid unless templates push timestamps forward, which moves chain time ahead of real time and interacts with the retarget; it limits how fast a withheld chain can be released only through the 2-hour future limit. A 1-2 s gap is not suspicious by itself (about 12 per day); runs are. Timestamps are miner-set within median-time-past and the future limit, so header arrival time at the node is the better signal.

*Decision (2026-10-06).* No consensus rule. Detection and reporting under RE-05:

- Flag two consecutive blocks from the same miner, each arriving within 2 s of its parent; the miner is identified by the coinbase payout script (and the pool tag in the coinbase input when present). Honest frequency of two consecutive sub-2 s gaps on the network is about one every 5 days; requiring the same miner makes a flag rarer still.
- Flag blocks with no transactions besides the coinbase when the mempool held transactions that fit.
- Thresholds are runtime options, for example `-fastblockgap=2` (seconds) and `-fastblockrun=2` (blocks), so operators can tune them without a release.
- Report through the RPC warning fields, a `forks` or `mining` debug category, and `-alertnotify`.
