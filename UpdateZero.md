# UpdateZero

Maintainer **execution hub**. Developer documents in **UpdateZero.md** section **1**, **Documentation map**.

---

## 1. Documentation map

**Purpose (this file):** Maintainer **execution hub** -- fork rules, cherry-pick **decisions and order**, port plans, audits, public-doc drafts pending copy.

**Include:** CON-* rules; PIR/TNT execution (**3.4**, **3.5**); Blockbook (**4**); Pirate review (**5**); Proton (**6**); drafts (**7**); CSV (**8**); DOC-* audits; RPC test prescriptions.

**Exclude:** zerod structure (**ZeroStruct**); zeronode operator/dev detail (**ZeroNodes**, **ZeroNodeDev**); ecosystem compare (**ZKNodes.md**); clone source diffs (**Comparison.md**); Zebra research (**ZebraZero**).

Developer documents: **this section**.

### Public project documents

Listed in **README** Documentation table. Public docs do **not** link to maintainer files below. Section **7** drafts copy **text** into public files without maintainer hrefs.


| Document            | Role                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------ |
| **README.md**       | Project front page; build and doc entry                                              |
| **BUILD_ZERO.md**   | Build, platforms, depends, troubleshooting                                           |
| **TEST_ZERO.md**    | Test runners, Tier A gate, harness, known failures                                   |
| **ZERO_COIN.md**    | Chain reference: emission, halving, founders, zeronodes summary, addresses, glossary |
| **TODO.md**         | Implementation checklist and tracked follow-ups                                      |
| **CONTRIBUTING.md** | Contribution workflow                                                                |
| **AGENTS.md**       | Agent scope and repo rules                                                           |
| **doc/man/**        | Shipped CLI manuals (`zerod`, `zero-cli`, `zero-tx`)                                 |


**Zeronode operator and developer guides** (**ZeroNodes.md**, **ZeroNodeDev.md**) are **maintainer documents** (below). They are **not** in the README listing; operators reach them via `UpdateZero.md` or maintainer links.

### Developer documents


| File                            | Purpose                                               | Include                                                                                                                                     | Exclude                                                                                                |
| ------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **UpdateZero.md**               | Decisions and execution order                         | This map; **3.4** PIR; **3.5** TNT; **4**--**8**                                                                                            | Content owned by other rows                                                                            |
| **ZeroStruct.md**               | **zerod** structure and options by use case           | Datadir, `-dbcache`, flags per workload, `ConnectBlock`, wallet chain ops, clients; brief zeronode cache; Zcash/Pirate **orientation** only | Ecosystem compare (**ZKNodes.md**); zeronode setup (**ZeroNodes**); wallet interface (**ZeroNodeDev**) |
| **ZeroNodes.md**                | Run a **zeronode** (operator)                         | Collateral, conf, RPC, sporks, coinbase summary, P2P, economics pointers                                                                    | ZND table (**ZeroNodeDev** section **9**); TNT order (**3.5**); insight flags (**ZeroStruct**)         |
| **ZeroNodeDev.md**              | **Zeronode source** (wallet boundary, TENT, tests)    | `CZeronodeWalletInterface`; library split; **ZND anchors** (section **9**); test phases                                                     | Operator workflow (**ZeroNodes**); TNT order (**3.5**)                                                 |
| **~/Work/ZK/ZKs/ZKNodes.md**    | Ecosystem **compare/contrast** (validators, indexers) | Cross-fork indexing strategies, Blockbook-by-coin, Insight vs external DB                                                                   | **Comparison**, **ZeroStruct**, **UpdateZero** duplication                                             |
| **~/Work/ZK/ZKs/Comparison.md** | Clone **source** diffs                                | PoW, wallet, P2P, toolchain                                                                                                                 | Node ecosystem compare (**ZKNodes.md**)                                                                |
| **ZebraZero.md**                | zebrad / YEC / CipherScan reference                   | Sidecar validation, Orchard lessons, YEC fork notes                                                                                         | zerod how-to (**ZeroStruct**)                                                                          |




### Zeronode documents (ZeroNode*)


| File               | Audience                                                                 |
| ------------------ | ------------------------------------------------------------------------ |
| **ZeroNodes.md**   | Operators: `zeronode.conf`, `startalias`, sporks, collateral             |
| **ZeroNodeDev.md** | Developers: TENT port map, wallet interface, ZND anchors (section **9**) |




### Cherry-pick ID prefixes


| Prefix  | Section               | Meaning                                                    | Cited in                            |
| ------- | --------------------- | ---------------------------------------------------------- | ----------------------------------- |
| **PIR** | **3.4**               | **P**irate upstream cherry-pick candidate                  | **UpdateZero** execution table      |
| **TNT** | **3.5**               | **T**ENT upstream cherry-pick candidate                    | **UpdateZero** execution table only |
| **ZND** | **ZeroNodeDev** **9** | **Z**ero**N**ode **D**ev anchor (port/reject + file paths) | **ZeroNode** files only             |
| **CON** | **2**                 | Zero **consensus** / engineering invariant                 | **UpdateZero** fork rules           |


**TNT** and **ZND** cover overlapping TENT topics: **TNT** = priority and execution order here; **ZND** = technical detail in **ZeroNodeDev** section **9**. Do not cite **ZND-NN** outside **ZeroNode** files.

**ZND anchors** (defined only in **ZeroNodeDev.md** section **9**): stable IDs tying each TENT-vs-Zero zeronode topic to **source paths** and a port/reject recommendation.

### Cross-link rules


| Direction                | Rule                                                  |
| ------------------------ | ----------------------------------------------------- |
| Public -> maintainer     | None                                                  |
| Maintainer -> public     | Allowed                                               |
| Maintainer -> maintainer | One-line pointer when another file **owns** the topic |


**Redundancy:** One owner per table or procedure. TNT execution order only here (**3.5**). ZND detail only **ZeroNodeDev** section **9**. Ecosystem compare only **ZKNodes.md**. zerod internals only **ZeroStruct.md**.

---



## 2. Fork-specific reference

What makes Zero different from upstream Zcash and Bitcoin: consensus parameters, engineering rules, subsidy implementation. New code touching any of these areas must be reviewed against this section.

### Consensus

**Branch id.** Sapling and Cosmos both use `0x7361707a` in `src/consensus/upgrades.cpp`. Duplicate id is documented technical debt until a deliberate NU. See CON-03.

**Zeronode.** `src/zeronode/`* ported from TENT `masternode/*` (see `ZeroNodeDev.md`). Safe iterator order when cleaning expired broadcasts. All `chainActive` dereferences now guarded (C-07, C-14).

**Equihash.** Zero keeps libsodium C `crypto_generichash_blake2b_state` for `eh_HashState` (192,7 parameters). A Rust/CXX bridge like Zcash v6+ would need `librustzcash`/`rustcxx` alignment -- out of scope unless the PoW stack moves.

### Policy

**Numeric.** Consensus and subsidy paths: integer-only. Default rounding: truncate toward zero. No new `float`/`double` in consensus without review. See BUILD_ZERO §4.8.

**Height and expiry.** `TransactionBuilder::SetExpiryHeight` mixes `int` chain height with `uint32_t` expiry. Prefer explicit casts or `int64_t` for height in new code.

**C++ exceptions.** Use `throw std::runtime_error("...");` -- **not** `throw new std::runtime_error("...");`.

**Why** `throw new` **is wrong.** `throw new T(...)` allocates on the heap, throws a pointer type (`T`*), and nothing deletes the object unless the catcher uses `catch (T* e) { delete e; }`. Typical `catch (const std::exception&)` or `catch (...)` does **not** free it -> **leak** and mismatched catch types. Standard style is `throw std::runtime_error(...)` (by value); the exception object is copied/moved into the unwind machinery.

**Change record.** Five C++sites were fixed in commit++ `a09cea932` ++(Mar 2026):++ `src/transaction_builder.cpp` ++(++`SetExpiryHeight`++),++ `src/main.cpp` ++(++`CreateNewContextualCMutableTransaction`++),++ `src/zcbenchmarks.cpp` ++(three sites). See Appendix A2, Completed C-12. **Verification:**++ `rg 'throw new' src --glob '*.cpp'` ++should return no matches (Java under++ `secp256k1` ++may still use++ `throw new` ++for Java exceptions; out of scope for C++ policy).

**Branding.** User-visible strings should read ZERO. Clean residual Zcash/Bitcoin names when touching files; not consensus.3

### Witness path

Zero uses `VerifyAndSetInitialWitness` and `BuildWitnessCache` with optional `pblockIn`, coupling to `pcoinsTip` and chain views. Hardening: null checks, `pblockIn`, nullifier guards. Code: `src/wallet/wallet.cpp`, `wallet.h`.

### Subsidy implementation

Code excerpts for consensus subsidy paths. File:line numbers may drift -- verify against `src/`. User-facing narrative: ZERO_COIN.md.

> **Coverage requirement:** `GetBlockSubsidy`, `Params::Halving`, founders reward, and zeronode payment paths are consensus-critical. Any change must match in both validator and miner code. Far-future halving tests are required. See CON-01 and CON-02.

**GetBlockSubsidy** (`src/main.cpp`):

```cpp
CAmount GetBlockSubsidy(int nHeight, const Consensus::Params& consensusParams)
{
  CAmount nSubsidy = 10 * COIN;
  if (nHeight>=consensusParams.nFeeStartBlockHeight) {
    nSubsidy = 10.8 * COIN;
  }

    int halvings = consensusParams.Halving(nHeight);
    if (halvings >= 64)
        return 0;

    if (consensusParams.NetworkUpgradeActive(nHeight, Consensus::UPGRADE_BLOSSOM)) {
        return (nSubsidy / Consensus::BLOSSOM_POW_TARGET_SPACING_RATIO) >> halvings;
    } else {
        return nSubsidy >> halvings;
    }
}
```

**Params::Halving** (`src/consensus/params.cpp`): pre-Blossom `halvings = nHeight / nPreBlossomSubsidyHalvingInterval` (800000). No slow start.

**GetLastFoundersRewardBlockHeight:** pre-Blossom `800000*10 - 1 = 7,999,999`.

**Founders:** `src/zeronode/payments.cpp`, `budget.cpp` -- `blockValue * 7.5 / 100`.

**GetZeronodePayment** (`src/main.cpp`): default 20% of `blockValue`; tier steps at 800k multiples with SPORK_6/7.

**FillBlockPayee** (`src/zeronode/payments.cpp`): superblock path vs default; order: blockValue, founders, zeronode, miner + fees.

**Consensus validation** (`src/main.cpp`): requires founders output when `nFeeStartBlockHeight <= height <= GetLastFoundersRewardBlockHeight`.

**Addresses in code:** `src/chainparams.cpp` -- `vFoundersRewardAddress` (mainnet/testnet/regtest); RPC `developmentfee` (`src/rpc/zeronode.cpp`). `ZeronodeDummyAddress` -- collateral validation only.

---



## 3. Build and test notes

Release lifecycle and compiler flags: BUILD_ZERO §2.6-2.7. Source-tree fix log, dependency comparison, and test-porting prescriptions below.

### 3.1 Source-tree build fixes (applied)

Log of fixes on the integration line. Kept so future merges do not revert them. Grouped by area.

**Equihash / mining guard.**

- `src/equihash.cpp`: template instantiations for `(192,7)` and `(48,5)` wrapped in `#ifdef ENABLE_MINING`. Without this, `--disable-mining` builds fail to link. Ref: `Makefile.am` `ENABLE_MINING` conditional.
- `src/Makefile.gtest.include`: `test_miner.cpp` in `zero_gtest_SOURCES` only when `ENABLE_MINING`. Otherwise GTest binary pulls missing symbols.

**Compiler / platform portability.**

- `src/hash.h`: replaced VLA with `CSHA256::OUTPUT_SIZE` constant for stack buffer. Apple Clang rejects VLAs in C++ by default (`-Werror=vla`).
- `configure.ac`: strip `-lstdc++` from `ZMQ_LIBS` on `*darwin*`. Darwin Clang links `libc++`; mixing causes duplicate-symbol link errors.
- `depends/packages/` recipes: all `sed` calls use `build_SED_INPLACE` (`sed -i.old`). GNU `sed -i` without backup suffix fails on macOS BSD `sed`.

**Autotools / secp256k1.**

- `secp256k1/configure.ac`: replaced obsolete `AC_PROG_CC_C89` with `AC_PROG_CC`. Autoconf 2.72+ removed the C89-specific macro. Ref: `build-aux/m4/ax_pthread.m4` still uses `AS_ECHO`; when refreshing vendored `build-aux/m4/` macros, prefer `AS_ECHO` patterns from current autoconf-archive to reduce further deprecation warnings.
- `zcutil/fzero.sh`: `cleanup_secp256k1_la()` deletes stale `secp256k1.la` when `HOST` changes between builds (e.g. native -> cross). Without cleanup, libtool resolves wrong archive paths.
- `Makefile.am`: `distcleancheck_listfiles = find . -false` is intentional; prevents `make distcheck` from flagging generated files.

**Zeronode / spork.**

- `src/zeronode/zeronodeman.cpp`: `SliceHash` `memcpy` source pointer corrected (was reading past buffer). Ref: A1.
- `src/zeronode/spork.h`: sentinel value `4070908800` (year 2099) is the intentional "spork disabled" encoding; `budget.cpp` uses `INT_MAX` similarly. Not a bug.



### 3.2 Dependency versions (peer comparison, Apr 2026)

Where Zero sits relative to peers. Authoritative version table (no peer columns): BUILD_ZERO §4.1. Peer repos in `~/Work/ZK/ZKs/`; wallet and clone comparison `ZKs/Comparison.md` (section **3** wallet, **4** P2P); Pirate/TENT cherry-picks **§3.4** / **§3.5**; 2026 shielded CVEs `ZcashFixes.md` Appendix; clone index `ZKs/ZKRepos.md`.


| Library   | Zero          | Zcash   | Pirate      | Horizen | Bitcoin | Zero source                     |
| --------- | ------------- | ------- | ----------- | ------- | ------- | ------------------------------- |
| BDB       | 6.2.32        | 6.2.23  | 6.2.32      | 6.2.23  | removed | `depends/packages/bdb.mk`       |
| libsodium | 1.0.21        | 1.0.20  | 1.0.18      | 1.0.18  | --      | `depends/packages/libsodium.mk` |
| Boost     | 1.88.0        | 1.83.0  | 1.83.0      | 1.82.0  | 1.88.0  | `depends/packages/boost.mk`     |
| Rust      | system (1.90) | 1.81.0  | (cxxbridge) | 1.70.0  | --      | `depends/packages/rust.mk`      |
| OpenSSL   | 1.1.1w        | removed | removed     | 1.1.1w  | removed | `depends/packages/openssl.mk`   |


Verified from `depends/packages/*.mk` in each repo.

### 3.3 Test prescriptions

Cheat sheet for maintainers porting or fixing RPC tests. Originated from pitfalls found during the `getchaintips`, `wallet_changeaddresses`, `wallet_changeindicator`, and other test ports where upstream assumptions silently broke. Run tests per TEST_ZERO. Harness details (helpers, script-specific notes) are in TEST_ZERO §RPC harness details.

**Coinbase maturity 720.** Zero regtest uses `COINBASE_MATURITY = 720` (`src/consensus/consensus.h`), not the upstream 100. Every ported test that spends coinbase must mine to maturity first.

**P2P / regtest.** `nVersion >= 170007`; `mininode.py` default 170009. Regtest magic must match `chainparams.cpp`.

**Regtest NU.** `-nuparams=6f76727a:1` (Overwinter), `-nuparams=7361707a:1` (Sapling). Blossom: set above tip after maturity mining.

**Python 3.** `serialize_script_num`: `bytearray.append(int)`, not `chr(...)`. Import `initialize_chain_clean` when used.

**Partition tests.** `split=True`: only edges 0-1 and 2-3; `CHAIN_BOOTSTRAP` + guard before re-mine.

New prescription: add here and add a TEST_ZERO harness changelog entry if user-visible.

**Coverage gaps.**


| Area                | Coverage     | Key gaps                                                                 |
| ------------------- | ------------ | ------------------------------------------------------------------------ |
| zero_exclusive RPCs | 0%           | `zs_listtransactions`, `zs_gettransaction`, `getalldata`, `getsupply`    |
| zero_experimental   | 0%           | `getsaplingwitness`, `getsaplingwitnessatheight`, `getsaplingblocks`     |
| Zeronode logic      | 0%           | Payment calc, budget validation, collateral                              |
| SwiftTX / Spork     | 0%           | Lock conflict, activation, quorum vote (DEF-06: removal planned)         |
| Zeronode RPC        | ~25%         | `zeronodecurrent`, `getzeronodeoutputs`, `startzeronode`, budget subcmds |
| Mining/PoW          | 75%          | `miner_tests` excluded (192,7 vs 96,5)                                   |
| Wallet              | 80%          | CDB::Rewrite blocks 3 tests                                              |
| RPC Python (Tier A) | 10 pass-only | exit 0 != full scenario coverage; see `TEST_ZERO.md` tier counts         |
| Fuzz                | 0%           | No infra                                                                 |


**Debug notes.**

- **CachedWitnesses (GTest).** `WalletTests.CachedWitnesses`* fails because `BuildWitnessCache` is a no-op when `pcoinsTip` is null in the GTest harness. `EXPECT_DEATH` in `DecrementNoteWitnesses` does not match the actual abort path. Partial fix: seed `CCoinsViewCache` manually; still fails on witnesses added before cache population. Ref: `src/wallet/gtest/test_wallet.cpp`, TST-03 P2.
- **CDB::Rewrite (GTest + Boost).** `EncryptWallet` calls `CDB::Rewrite` which busy-waits on `mapFileUseCount` while the wallet DB is still open by the test harness. Indefinite hang. Affects `WriteCryptedSaplingZkey`* (GTest) and `rpc_wallet_encrypted_wallet_sapzkeys` (Boost). Fix: close wallet handle before rewrite, or test-only persistence path. Ref: `src/wallet/db.cpp`, `src/wallet/gtest/test_wallet_zkeys.cpp`, TST-03 P2.
- **wallet.py balance (RPC).** Node0 reports ~19 ZER mature vs expected 29. Cause: `COINBASE_MATURITY = 720` means fewer coinbase outputs are spendable than upstream scripts expect. Not a code bug; test expectation needs adjusting.



### 3.4 Pirate upstream cherry-pick candidates (2022--2026)

**Repo:** `~/Work/ZK/ZKs/pirate` (`PirateNetwork/pirate`), Komodo assetchain C++ on zcashd lineage -- not a zeronode fork. Releases sampled: v5.5.0 (2022-06), v5.7.0 (2023-06), v5.8.x (2024-03), v5.9.x (2024-09). Recent tip work is mostly build/CI/Komodo merges; portable fixes are scattered single commits.

**Where other Pirate research lives:** Wallet algorithms, RPC controls, hex validation, glossary -> `ZKs/Comparison.md` section **3**. P2P matrix and cross-chain timeline -> section **4.1**. Insight ops -> `~/Work/ZK/ZKs/insight/README.md`. Orchard CVE posture -> `ZcashFixes.md` Appendix A.1. TENT -> **§3.5** and `ZeroNodeDev.md` section **9**.

**Cherry-pick rule:** Prefer Zcash upstream when the same fix exists there. Use Pirate as a diff anchor only when it already merged a feature onto a zcashd-shaped tree. Reject Komodo-only consensus (notary seasons, KIP coinbase, `-ac_`*). Wallet consolidation and dust tooling: **section 5** (under review, not rejected outright).


| ID      | Area                    | Pirate ref                                                                                                                             | Zero status                                                                                                                                         | Recommendation                                                                                                      | Priority       |
| ------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------- |
| PIR-01  | Security                | `d213d7884` (2026-01) `ENABLE_SYSTEM_COMMAND` gate on `runCommand`                                                                     | Unguarded `::system` in `alert.cpp`, `init.cpp`, `wallet.cpp` (`-alertnotify`, `-blocknotify`, `-walletnotify`)                                     | **Port** -- opt-in compile flag; log skip message when disabled                                                     | High           |
| PIR-02  | Wallet / coin selection | Knapsack early exit `nTotalLower > 4*nTargetValue + CENT` (`79383e0a7`, jl777, 2017-10-18 Komodo interest calc)                        | Missing; scans all UTXOs                                                                                                                            | **Port** -- low-risk perf; optional `std::shuffle` as Pirate                                                        | Medium         |
| PIR-03  | Wallet / RPC            | `1f707492f` (2024-03) witness rebuild lockout (`fBuilingWitnessCache`)                                                                 | `initWitnessesBuilt` never cleared on rebuild (**Comparison.md** 2.4)                                                                               | **Port (adapted)** -- in-progress flag; block `z_sendmany` until complete                                           | Medium         |
| PIR-04  | Policy / relay          | `6fb6a2e2b` (2024-05) `fAcceptDatacarrier` from `-datacarrier`; `IsStandard` rejects oversize or disabled OP_RETURN                    | Partial: `-datacarriersize` in `init.cpp`; size enforced in `Solver()` template match; no global `fAcceptDatacarrier`; Komodo AC size constants N/A | **Port (partial)** -- add `fAcceptDatacarrier` + `IsStandard` NULL_DATA check; keep Zero `MAX_OP_RETURN_RELAY = 80` | Low            |
| PIR-05  | P2P / DoS               | `2bec27973` (2023-03) rate-limit incoming `addr` processing; commit message cites Bitcoin `0d64b8f709` and Zcash `7c739e2b2` (PR 6477) | Not present                                                                                                                                         | **Consider** -- port from `bitcoin-src` or Zcash PR; Pirate is ~2y late backport                                    | Medium         |
| PIR-06  | P2P                     | BIP155 / addrv2 (`50699aba6`, `b5ae39c84`, 2022-05)                                                                                    | Not present                                                                                                                                         | **Defer** -- `Comparison.md` 3.1; port from `bitcoin-src`                                                           | Low (epic)     |
| PIR-07  | P2P                     | ASMap (`de6779711`, 2020-10; `-asmap` in `init.cpp`)                                                                                   | Not present                                                                                                                                         | **Defer** -- same; needs `util/asmap.cpp`, addrman churn, seed tooling                                              | Low (epic)     |
| PIR-08  | P2P                     | I2P/SAM (`c8127046b`, 2022-05; `-i2psam`, `-i2pacceptincoming`)                                                                        | Not present                                                                                                                                         | **Defer** -- optional operator feature; significant `net.cpp` / GUI surface                                         | Low            |
| PIR-09  | Util                    | `8ef165bb9` (2025-05) `HasPrefix` `static_assert`                                                                                      | No `HasPrefix` in tree                                                                                                                              | **Skip** -- only if/when `util/string.h` is merged from Core                                                        | N/A            |
| PIR-10  | RPC docs                | `e187da704` / PR #111 `z_getbalances` help text                                                                                        | Zero has no `z_getbalances` RPC                                                                                                                     | **Skip**                                                                                                            | N/A            |
| PIR-11  | Index DB                | `1a9d6bed9` (2023-12) `GetZkProofHash` `SAPLING` -> `SPEND` enum typo                                                                  | No `GetZkProofHash` / Komodo proof DB                                                                                                               | **Skip**                                                                                                            | N/A            |
| PIR-12  | Consensus index         | `5a82d1aab` (2023-11) Komodo `SPROUT_VALUE_VERSION` / `SAPLING_VALUE_VERSION` -> `80102`                                               | Zero uses Zcash constants `1001400` / `1010100` in `chain.h` (correct for this chain)                                                               | **Skip** -- Komodo-specific serialization bug                                                                       | N/A            |
| PIR-13  | Consensus / PoW         | RT_CST_RST / Zawy adaptive PoW in `pirate/src/pow.cpp`                                                                                 | Zero: Zcash 17-block window, tighter caps (`Comparison.md` section **2**)                                                                           | **Reject** -- consensus change, not a bugfix port                                                                   | N/A            |
| PIR-14  | Komodo / ARRR           | KIP coinbase, notary hooks, `-ac_*` args                                                                                               | N/A                                                                                                                                                 | **Reject**                                                                                                          | N/A            |
| PIR-14b | Wallet consolidation    | `consolidateaddress`, cleanup/dust modes, `z_getbalances`                                                                              | Partial: auto `-consolidation` only; no manual RPC                                                                                                  | **Review** -- **section 5**                                                                                         | Medium         |
| PIR-15  | Wallet / RPC lockdown   | `02c8dff72`, `e55606130` (2024) lock metadata RPCs when encrypted+locked; `unlockforreporting=1`                                       | Standard zcashd lock behavior                                                                                                                       | **Review** -- product decision; not a correctness fix                                                               | Low            |
| PIR-16  | Insight / explorer      | `insight-api-pirate` tx v5 + Sapling commits (2024)                                                                                    | Zero Insight operational; mainnet [insight.zeromachine.io](https://insight.zeromachine.io/); ops `~/Work/ZK/ZKs/insight/` | **Separate track** (JS/hosting); Pirate API as optional diff anchor | Medium (infra) |


**Suggested execution order (node repo only):**

1. **PIR-01** -- single focused security PR; document in BUILD_ZERO that `-blocknotify` / `-walletnotify` require `-DENABLE_SYSTEM_COMMAND`.
2. **PIR-03** -- wallet correctness; add **TST-08** GTest that `z_sendmany` returns **-33** while `fBuildingWitnessCache` is set.
3. **PIR-02** -- coin selection perf; run existing `wallet_tests` knapsack cases unchanged.
4. **PIR-05** then **PIR-06--08** -- schedule as a P2P modernization epic tied to fixed-seed work (DOC-02 fixed-seed note) and `Comparison.md` gap list.

**PIR-01 patch shape (reference):**

```cpp
#ifdef ENABLE_SYSTEM_COMMAND
    boost::thread t(runCommand, strCmd);
#else
    LogPrintf("Block notification skipped: %s\n"
              "To enable, rebuild with: ./configure CXXFLAGS=\"-DENABLE_SYSTEM_COMMAND\"\n",
              strCmd);
#endif
```

Files: `src/alert.cpp`, `src/init.cpp`, `src/util.cpp`, `src/util.h`, `src/wallet/wallet.cpp` (same set as Pirate `d213d7884`).

#### 3.4.2 `ENABLE_SYSTEM_COMMAND` -- nature, rationale, legitimate use, tests

**Nature of change.** Compile-time gate on **`runCommand()`** and three notify call sites. Not consensus, not wire format, not default RPC behavior. Default binaries: flags accepted on CLI/conf but **never** call **`::system()`**. Opt-in rebuild only.

**Why port (PIR-01).**

| Risk | Detail |
|------|--------|
| Shell execution | **`::system()`** runs **`/bin/sh -c`** with operator-supplied strings |
| Config trust | **`-blocknotify`**, **`-walletnotify`**, **`-alertnotify`** live in **`zero.conf`**; compromise or typo -> code execution as **`zerod`** uid |
| Low default value | Most nodes use ZMQ or external indexers; unguarded shell in every release widens blast radius |
| Peer precedent | Pirate **`d213d7884`** (2026-01); same file set |

**When operators may still need shell hooks**

| Scenario | Flag | Example command shape | Why not ZMQ alone |
|----------|------|----------------------|-------------------|
| Pre-ZMQ script | **`-blocknotify`** | **`/opt/indexer/on_block.sh %s`** | Existing shell pipeline predating ZMQ wiring |
| Wallet fifo / ledger | **`-walletnotify`** | **`echo %s >> /var/run/zero-tx.fifo`** | Sidecar expects txid stream without polling RPC |
| Deprecation banner | **`-alertnotify`** | **`mail -s alert ops@example.com`** with **`%s`** body | **`CAlert::Notify`** path; no ZMQ equivalent for deprecation text |
| One-shot regtest hook | **`-blocknotify`** | **`touch /tmp/regtest-tip`** | Quick local integration smoke (use regtest only) |

**Default recommendation:** **`-zmqpubhashblock`**, **`-zmqpubhashtx`**, or RPC sidecar -- document in **BUILD_ZERO.md** section **4.6** (Shell notify hooks).

**Test support (either build mode)**

| Build | Test | Expected |
|-------|------|----------|
| Default (no **`ENABLE_SYSTEM_COMMAND`**) | GTest **`DeprecationTest.AlertNotify`** | Temp notify file **empty** after deprecation **`CAlert::Notify`** |
| **`CXXFLAGS="-DENABLE_SYSTEM_COMMAND"`** | Same test | Temp file **one line** with sanitized deprecation message |
| Either | Manual regtest | **`-blocknotify`** with **`echo`** -- runs only on enabled build; skipped log on default |
| Either | **`rg 'runCommand|::system'`** on notify paths | **`runCommand`** body only in **`util.cpp`** behind **`#ifdef`** |

**Not in default CI today:** Tier A RPC has no **`blocknotify`** script (removed **`forknotify.py`**). GTest coverage is the gate for PIR-01 regression.

**Public doc:** **BUILD_ZERO.md** section **4.6** (Shell notify hooks). Section **7.0** draft row marked ready.

**PIR-03 Zero-specific note:** `BuildWitnessCache` runs from `CWallet::ChainTip` each block (`wallet.cpp` ~623); `initWitnessesBuilt` is never cleared on rebuild. See `ZKs/Comparison.md` section **3.4** for lockout comparison; patch in table above.

#### 3.4.1 Provenance

Cross-chain history, commit volume, feature dates, wallet RPC matrices, hex validation, and glossary: `ZKs/Comparison.md` section **3** (wallet) and **4.1** (timeline). This section keeps **PIR execution only** (table, order, patch shapes).

**Cherry-pick implication.** Portable Pirate fixes for Zero are a small set (PIR-01--05 plus deferred P2P epic PIR-06--08). The 2022 P2P bundle is late Bitcoin Core, not Pirate research. Zcash parallel work was NU/consensus/Rust, not P2P -- port P2P from Core (or Zcash PR 6477 for addr rate limit), using Pirate only as a zcashd-shaped diff anchor.

### 3.5 TENT upstream cherry-pick candidates (2018--2021)

**Repo:** `~/Work/ZK/ZKs/TENT` ([TENTOfficial/TENT](https://github.com/TENTOfficial/TENT)), Snowgem lineage zcashd + masternode layer. Tip frozen **2021-11** (~333 commits). Zero `src/zeronode/`* is a port of TENT `src/masternode/*` (wire `mn*` -> `zn*`, treasury removed, `CZeronodeWalletInterface`). TENT is the **direct upstream** for zeronode behavior, not a distant peer like Pirate.

**Where other TENT research lives:** P2P masternode wire inventory -> `ZKs/Comparison.md` section **4** (TENT subsection). File-level port map and wallet boundary -> `ZeroNodeDev.md` sections **2**--**9**. Operator workflow -> `ZeroNodes.md`.

**Cherry-pick rule:** Prefer fixes already landed on Zero's integration line (C-07, C-11, C-14, C-21). Use TENT only where Zero's zeronode fork **regressed** TENT behavior or never picked up a post-port TENT commit. Reject Snowgem/TENT tokenomics (treasury, upgrade-named consensus hooks, Atlantis/Wakanda/Knowhere schedules).


| ID         | Area                    | TENT ref                                                                                                                                                  | Zero status                                                                                                                         | Recommendation                                                                                                   | Priority |
| ---------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | -------- |
| **TNT-01** | P2P / logging           | `main.cpp` else branch: extension dispatch **without** trailing `Unknown command` log                                                                     | Zero logs after `znodeman` / budget / payments / SwiftTX / spork / sync dispatch (`main.cpp` ~7033)                                 | **Port** -- match TENT; detail **ZeroNodeDev.md** section **9**                                                  | High     |
| **TNT-02** | Chain / reorg           | `6f64bb7` (2021-07) removed `ActivateBestChainStep` shutdown on `reorgLength > MAX_REORG_LENGTH` (masternode comment: MN path must not die on deep reorg) | Zero **still** shuts down at `MAX_REORG_LENGTH` (99) with modal + `StartShutdown()` (`main.cpp` ~3678)                              | **Port (adapted)** -- remove or relax shutdown for zeronode operators; pair with TNT-03 review                   | High     |
| **TNT-03** | Chain / reorg           | TENT `main.h`: `MAX_REORG_LENGTH = COINBASE_MATURITY - 1`; later dropped shutdown only                                                                    | Zero: `MAX_REORG_LENGTH = 100 - 1` with comment that maturity **720** is too large (`main.h` ~69); witness cache uses same constant | **Review** -- reconcile 99-block cap with `COINBASE_MATURITY = 720` and wallet witness rewind (`main.cpp` ~5244) | Medium   |
| **TNT-04** | Zeronode / payments     | `74bbde2` (2019-09) payee validation uses `out.nValue >= requiredMasternodePayment`                                                                       | Zero requires exact match `out.nValue == requiredZeronodePayment` (`zeronode/payments.cpp` ~555)                                    | **Port (review)** -- allow >= minimum when drift/spork logic intends tolerance                                   | Medium   |
| **TNT-05** | Wallet / coin selection | `3915ac3` (2021-05) `GetCoinbaseProtected(chainActive.Height() + 1)` in `SelectCoins`                                                                     | Zero uses static `Params().GetConsensus().fCoinbaseMustBeProtected` (`wallet.cpp` ~4333)                                            | **Skip unless** Zero adds height-gated coinbase shielding like TENT Atlantis fork                                | Low      |
| **TNT-06** | RPC / UX                | `e3d39f1` (2021-01) sync wait text: "Syncing masternodes list..."                                                                                         | Zero: "Zeronode is not synced..." (`rpc/zeronode.cpp` ~122, ~331)                                                                   | **Port** -- copy-only UX fix                                                                                     | Low      |
| **TNT-07** | Consensus / testnet     | `chainparams.cpp` testnet `nPowAllowMinDifficultyBlocksAfterHeight = 13000`                                                                               | Zero testnet: `boost::none`                                                                                                         | **Consensus decision** -- **ZeroNodeDev.md** section **9**                                                       | Low      |
| **TNT-08** | Consensus / Equihash    | TENT epoch fork mainnet 192,7 vs testnet 144,5 (`validEHparameterList`)                                                                                   | Zero: 192,7 mainnet **and** testnet                                                                                                 | **Reject** without NU -- **ZeroNodeDev.md** section **9**                                                        | N/A      |
| **TNT-09** | Consensus / PoW         | TENT LWMA3 after DIFA height                                                                                                                              | Zero: Zcash 17-block window                                                                                                         | **Defer** -- **ZeroNodeDev.md** section **9**                                                                    | Low      |
| **TNT-10** | Tokenomics              | Treasury coinbase, `GetTreasuryRewardScriptAtHeight`                                                                                                      | **Removed** on Zero                                                                                                                 | **Reject** -- **ZeroNodeDev.md** section **9**                                                                   | N/A      |
| **TNT-11** | Tokenomics              | Founders % by upgrade (5 / 7.5 / 15)                                                                                                                      | Zero fixed **7.5%** after fee-start                                                                                                 | **Reject** -- **ZeroNodeDev.md** section **9**                                                                   | N/A      |
| **TNT-12** | Testing                 | No masternode integration tests in TENT either                                                                                                            | Zero: no regtest zeronode harness                                                                                                   | **Implement** on Zero first; **ZeroNodeDev.md** section **9** test roadmap                                       | Medium   |
| **TNT-13** | Docs / ops              | External MN setup scripts (obsolete in the wild)                                                                                                          | Same gap on Zero                                                                                                                    | **Doc** -- **ZeroNodes.md** / BUILD_ZERO when scripted                                                           | Medium   |
| **TNT-14** | Build                   | `db81202` (2021-01) libsnark `-march` via `ax_gcc_archflag` for cross-compile                                                                             | Not in Zero `configure.ac` / `build-aux/m4/`                                                                                        | **Review** -- port if cross-build libsnark failures recur                                                        | Low      |
| **TNT-15** | Consensus               | `cb0284e` minimum block time after UPGRADE_WAKANDA                                                                                                        | TENT-only upgrade name                                                                                                              | **Skip** -- no Zero equivalent fork                                                                              | N/A      |
| **TNT-16** | RPC product             | `sendtoaddressnochange`, `sendmanynochange`, wallet-encryption experiments (2021)                                                                         | Not in Zero RPC surface                                                                                                             | **Reject** -- out of scope unless product asks                                                                   | N/A      |
| **TNT-17** | Checkpoints             | `00c34dc` TENT mainnet checkpoint + fork shutdown messaging                                                                                               | Zero has its own checkpoint table; no TENT heights                                                                                  | **Skip** -- chain-specific                                                                                       | N/A      |


Port/reject **detail** and source **anchors**: `ZeroNodeDev.md` section **9**. This section keeps **TNT** execution order only.

**Suggested execution order (zeronode / chain ops):**

1. **TNT-01** -- one-line logging fix; unblocks `-debug=net` triage (**TODO.md**).
2. **TNT-02** + **TNT-03** -- single PR: reorg policy aligned with `COINBASE_MATURITY` 720 and zeronode survival on deep reorg (follow TENT `6f64bb7` intent, not literal re-enable of 719-block shutdown).
3. **TNT-04** -- payment validation only if mainnet coinbase rejects valid winner payouts today.
4. **TNT-12** -- regtest coinbase + two-node script (DOC-02 phase B/C) before more TENT code ports.

**TNT-01 patch shape (reference):**

TENT ends the `else` branch after extension handlers with no log. Zero should drop line ~7033 or guard it so handled `zn*` / spork / SwiftTX commands do not emit `Unknown command` (keep the `notfound` exception already present).

**TNT-02 context:** TENT removed shutdown because masternode operators could not recover from a 100+ block reorg during network churn. Zero kept Zcash-era shutdown but capped at **99** while maturity is **720** -- an intentional mismatch documented in `main.h`, still painful for zeronode collateral UTXOs tied to long reorgs.

#### 3.5.1 TNT-02 / TNT-03 reorg policy (postponed)

Two constants serve different jobs and must not be conflated:

| Constant | Value | Role |
| -------- | ----- | ---- |
| **`COINBASE_MATURITY`** | **720** blocks | Consensus: coinbase outputs are unspendable until 720 confirmations (`consensus.h`). |
| **`MAX_REORG_LENGTH`** | **`100 - 1` = 99** | Node policy: if a reorg or rewind would roll back **more than 99 blocks**, the node shows a modal and **`StartShutdown()`** (`main.cpp` ~3678, ~5253). Witness cache size is **`MAX_REORG_LENGTH + 1`** (`wallet.h`). |

**Why Zero uses 99, not 719.** Upstream Zcash set `MAX_REORG_LENGTH = COINBASE_MATURITY - 1` so the node could always reorg far enough to undo immature coinbases. Zero's comment in `main.h` rejects 719 as **too much** for witness-cache memory and rebuild cost. The cap is a **practical safety bound**, not a consensus rule.

**The operational gap (TNT-02).** TENT removed the deep-reorg shutdown so masternode/zeronode operators stay up through network churn. Zero **still exits** on reorg depth **> 99**, which can strand zeronode collateral when a reorg is deeper than 99 but shallower than 720.

**The design tension (TNT-03).** Raising `MAX_REORG_LENGTH` toward maturity improves zeronode survivability but increases witness-cache work on large rewinds. Lowering it further would worsen operator pain. Any change must update **`WITNESS_CACHE_SIZE`**, **`init.cpp`** `keeptxfornblocks` floor (`MAX_REORG_LENGTH + 1`), and the unintended-rewind path in **`RewindBlockIndex`** together.

**Recommendation (single PR when scheduled, not now):**

1. **TNT-02:** Remove or relax **`StartShutdown()`** on `reorgLength > MAX_REORG_LENGTH` in **`ActivateBestChainStep`** and on unintended rewind (~5253). Prefer **log + alert + continue on longest chain** over process exit. Follow TENT **`6f64bb7` intent**, not a blind restore of 719-block shutdown.
2. **TNT-03:** Pick a new **`MAX_REORG_LENGTH`** with explicit tradeoff (keep 99, moderate raise, or staged policy). Document zeronode operator expectations. Regtest or two-node reorg script before mainnet.
3. **Do not** set `MAX_REORG_LENGTH = COINBASE_MATURITY - 1` without a witness-cache and memory review.

**Status:** **Postponed** -- tracked as **DEF-07** (§4). Depends on zeronode operator input and regtest coverage (**TNT-12**). **PIR-03** (witness RPC lockout during rebuild) is a separate wallet fix and does not resolve reorg shutdown policy.

---



## 4. Issues and tasks

All tracked issues, deferred decisions, and work backlog.

**Rule:** Items involving possible errors or unconfirmed arithmetic stay here until researched, confirmed, and fixed. They do not enter user-facing docs until resolved.

**Grouping.** Items are partitioned by topic area, then sequenced within each group by urgency (high first). Each item has a consistent designator: prefix identifies the group, number identifies the item within it.


| Prefix | Group                      | Rationale                                                         |
| ------ | -------------------------- | ----------------------------------------------------------------- |
| DOC    | Documentation              | User-facing accuracy; blocks release.                             |
| CON    | Consensus and code         | Correctness of chain rules and node code; highest technical risk. |
| REL    | Release and infrastructure | Packaging, signing, distribution; required for shipping.          |
| TST    | Testing                    | Coverage and reliability; supports confidence in CON and REL.     |
| DEF    | Deferred                   | Known debt with no immediate timeline.                            |




### Documentation

**DOC-01 -- README rewrite.** High urgency. Merge README.md and README0.md into one coherent front page. Current README has era-dependent figures, marketing-era copy, and inconsistencies with ZERO_COIN.md.

**DOC-02 -- Node setup and maintenance.** Validate and update all user-facing instructions for running a Zero full node and a Zeronode.

*A. Full node (zerod) reference facts* (validated Apr 2026):


| Item               | Value                                                                                   | Source                               |
| ------------------ | --------------------------------------------------------------------------------------- | ------------------------------------ |
| Data directory     | `~/.zero` (Linux), `~/Library/Application Support/zero` (macOS), `%APPDATA%\zero` (Win) | `src/util.cpp` `GetDefaultDataDir`   |
| Params directory   | `~/.zcash-params` (Linux), `~/Library/Application Support/ZcashParams` (macOS)          | `src/util.cpp` `ZC_GetBaseParamsDir` |
| Config file        | `zero.conf` in data dir                                                                 | `src/init.cpp` help                  |
| P2P ports          | mainnet **23801**, testnet **23802**, regtest **23803**                                 | `src/chainparams.cpp`                |
| RPC ports          | mainnet **23811**, testnet **23812**, regtest **23813**                                 | `src/chainparamsbase.cpp`            |
| Params fetched     | `sapling-spend.params`, `sapling-output.params`, `sprout-groth16.params`                | `zcutil/fetch-params.sh`             |
| Sprout keys        | `sprout-proving.key`, `sprout-verifying.key` -- **commented out**, no longer fetched    | same                                 |
| Help `-port` text  | **Fixed:** was showing Zcash defaults 8233/18233; corrected to 23801/23802              | `src/init.cpp:417`                   |
| `util.cpp` comment | **Fixed:** was `Unix: ~/.zcash`; corrected to `~/.zero`                                 | `src/util.cpp`                       |


**Runtime check:** `zerod` runs fine on the maintainer tree (Apr 2026).

Gaps to address in BUILD_ZERO / README: minimal quickstart (install deps, build, fetch-params, launch `zerod`), explain `zero.conf` RPC credentials for first-time operators.

*B. Zeronode setup* (validated against code):


| Item                  | Value                                                                         | Source                                                                        |
| --------------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Collateral            | **10,000 ZER** exactly                                                        | `src/wallet/wallet.cpp` (`ONLY_10000`), `src/zeronode/activezeronode.cpp:410` |
| Config file           | `zeronode.conf` in data dir (override: `-znconf`)                             | `src/util.cpp` `GetZeronodeConfigFile`                                        |
| Config format         | `alias IP:port privkey txid index`                                            | `src/zeronode/zeronodeconfig.cpp`                                             |
| Required conf entries | `zeronode=1`, `zeronodeprivkey=<key>`, `externalip=<ip>:23801`                | `src/init.cpp`                                                                |
| Key generation        | `zero-cli zeronode genkey`                                                    | `src/rpc/zeronode.cpp`                                                        |
| Stale comment         | `zeronode-wallet-interface.cpp:72` said "1000 ZERO" -- **fixed** to 10000 ZER | code fix applied                                                              |




### Zeronode `chainActive` hardening: reasoning and tests (DOC-02)

**Scope.** Edits in `src/zeronode/zeronode.cpp`, `zeronode.h`, `swifttx.cpp` (and related audit of `payments.cpp`, `budget.cpp`, `zeronode-sync.cpp`, `spork.cpp`). Tracked as **C-21** in Completed.

**Invariant (why any of this matters).** `CChain::operator[]` returns NULL for out-of-range or negative height (`src/chain.h:644-647`). `chainActive.Tip()` can be NULL on an empty chain. Reads of `chainActive` must hold `cs_main` so height and `vChain` do not change under the reader.

**Prior state and risk.**


| Location                | Risk                                                                                   | Mitigation                                                 |
| ----------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `CZeronodePing(CTxIn&)` | `chainActive[Height()-12]` null deref when `Height() < 12`; possible race without lock | `LOCK(cs_main)`; use genesis or null hash when short chain |
| `CreateNewLock`         | `Tip()` null; `(height - nTxAge) + 4` negative                                         | Guard `pTip`; `if (nBlockHeight < 0) return 0`             |
| `GetZeronodeInputAge`   | After reorg down, `Tip()->nHeight < cacheInputAgeBlock` -> negative "age"              | Invalidate cache; clamp return `>= 0`                      |
| `GetLastPaid`           | Redundant second `Tip()` check                                                         | Reuse `pindexPrev` after first null check                  |
| `CheckInputsAndAdd`     | `chainActive[...]` past tip                                                            | Existing `if (!pConfIndex)` defer path (unchanged)         |


---



#### 1. `CZeronodePing(CTxIn&)` and `LOCK(cs_main)` (`zeronode.cpp` ~680)

**Reasoning.** Ping `blockHash` binds the ping to a block deep enough to limit abuse (`height - 12`). That requires reading `chainActive.Height()` and `chainActive[...]`. Same-thread callers (`activezeronode.cpp` ~180 `SendZeronodePing`, ~263 `Register`) may or may not already hold `cs_main`; the constructor must not assume. Locking in the constructor makes the read **self-contained** and matches the rest of the codebase (validation-style access to `chainActive`).

**Expected behavior.**

- `h = chainActive.Height()`. If `h >= 12`, `blockHash` = hash of block at height `h - 12`. If `h < 12`, use **genesis** index when present, else `uint256()`.
- Peers still validate in `CZeronodePing::CheckAndUpdate` (`zeronode.cpp` ~749): unknown `blockHash` or block too old (`nHeight < chainActive.Height() - 24`) rejects the ping without updating state.

**Test steps (regtest).**

1. Build `zerod` / `zero-cli`. Start: `zerod -regtest -daemon -zeronode=1 -debug=zeronode` (add usual `-datadir` if needed).
2. Mine or sync until zeronode registration is allowed (`zeronodeSync` / logs). Note `getblockcount`.
3. Trigger a ping path: e.g. `startzeronode` / `startalias` per your RPC surface after collateral + `zeronode.conf` setup, or the code path that calls `CActiveZeronode::SendZeronodePing`.
4. **Case A -- short chain:** With `getblockcount` **< 12**, repeat step 3. **Pass:** no crash; log may show ping flow; `blockHash` should match `getblockhash 0` (genesis) when genesis exists.
5. **Case B -- long chain:** Mine to `getblockcount` **>= 12**. Repeat step 3. **Pass:** `blockHash` matches `getblockhash ($height - 12)` (compare manually).
6. **Mainnet / normal:** Regression only: pings still sign; compatible peers accept or reject per existing rules.

---



#### 2. `GetZeronodeInputAge` cache (`zeronode.h` ~256, caller `zeronodeman.cpp` ~503)

**Reasoning.** The method caches `GetInputAge(vin)` and the tip height at fill time to avoid recomputation. If the chain **reorgs downward**, the new tip height can be **below** `cacheInputAgeBlock`, so `cacheInputAge + (pTip->nHeight - cacheInputAgeBlock)` becomes **negative** (undefined semantics for "age"). Clearing the cache forces a fresh `GetInputAge`; clamping `nAge` to `>= 0` is a last-resort guard.

**Expected behavior.** If `pTip->nHeight >= cacheInputAgeBlock` or cache empty: same as before. If tip dropped below cached height: cache zeroed; next call refills from current chain.

**Test steps (regtest).**

1. Run zeronode on regtest with collateral and listing working (`zeronode list` / `list-conf` as applicable).
2. Record `getblockcount` and best-block hash.
3. `zero-cli invalidateblock <hash_of_recent_block>` (RPC table: `hidden` / `blockchain.cpp`). Tip moves back.
4. Wait for zeronode scoring / peer logic to touch `GetZeronodeInputAge`, or restart `zerod` and reconnect peers to force passes.
5. **Pass:** no crash; no negative values in `-debug=zeronode` logs tied to input age; zeronode list remains coherent.
6. **Fallback:** Two-node regtest, longer fork wins (classic reorg); same pass criteria.

**Automated backlog.** No harness test today; candidate for TST-03 (GTest with controlled `CZeronode` + mock chain) or contributor brief.

---



#### 3. `CreateNewLock` (`swifttx.cpp` ~228)

**Reasoning.** SwiftTX lock height uses tip and input age. Null tip must not deref. Extreme `nTxAge` vs tip can make `(pTip->nHeight - nTxAge) + 4` negative; storing that would corrupt lock metadata. Early `return 0` skips creating/updating the lock.

**Test steps.** Mainnet: spork usually off -> **no behavior change**. Testnet/dev with `SPORK_2_SWIFTTX` on: `-debug=swiftx`, exercise `ix` / lock flow; **pass:** no crash; logs may show early return on bad inputs only.

---



#### 4. `GetLastPaid` (`zeronode.cpp` ~242)

**Reasoning.** After `pindexPrev == NULL` return, `BlockReading` should use the same pointer to avoid a second `Tip()` read (clarity; same correctness).

**Test steps.** Covered by general zeronode RPC / sync regression; no separate protocol surface.

---

**Note on filename.** There is no `ZeroUpdate.md` in this tree; this subsection lives in **UpdateZero.md** under DOC-02 so maintainer reasoning and tests stay next to the node-setup audit.

*C. External install script audit.* The `zeronode_install.sh` from `ZeroNodes-UpdatesPending` repo is **obsolete**:


| Issue                   | Detail                                                                                                                      |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Ubuntu 16.04/18.04 only | Rejects all other distros; both are EOL                                                                                     |
| Binary download URLs    | Point to `Zero-Wallets` release zips for Ubuntu 16.04/18.04; no current builds                                              |
| Runs as root            | Installs to `/usr/local/bin`, configures `systemd` as root user                                                             |
| Hardcoded params URLs   | Downloads from `z.cash/downloads/` -- same as `fetch-params.sh` but includes `sprout-proving.key` which is no longer needed |
| Correct port/config     | Uses 23801 (correct) and standard `zero.conf` entries (correct)                                                             |
| Collateral              | Not checked by script; relies on user having 10,000 ZER in wallet                                                           |
| No TLS / auth           | Generates random rpcuser/rpcpassword (adequate for localhost)                                                               |


Recommendation: archive `ZeroNodes-UpdatesPending` repo; replace with updated instructions in BUILD_ZERO or a new section of README.

*D. Wiki review: [Zero Node Setup - English](https://github.com/zerocurrencycoin/Zero-Wallets/wiki/Zero-Node-Setup---English)* (last edited Apr 2020):


| Item                   | Wiki says                                                          | Status                                                                                                                                                                          |
| ---------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| OS requirement         | Ubuntu 16.04 or 18.04                                              | **Obsolete.** Both EOL. Current builds target Ubuntu 24.04+ (GCC 13.3).                                                                                                         |
| Install method         | `wget` script from `Zero-Scripts` repo                             | **Obsolete.** Points to `zerocurrencycoin/Zero-Scripts/master/zeronode_install.sh`; actual script is in `ZeroNodes-UpdatesPending`. `Zero-Scripts` repo does not appear in org. |
| Binary source          | Pre-built zips from `Zero-Wallets` releases                        | **Stale.** Release zips are from 2019; no current pre-built binaries. Building from source is the only option.                                                                  |
| Collateral             | 10K ZER exactly                                                    | **Correct.** Code checks `10000 * COIN`.                                                                                                                                        |
| P2P port               | 23801                                                              | **Correct.**                                                                                                                                                                    |
| `zeronode.conf` format | `alias IP:port privkey txid index`                                 | **Correct.** Matches `src/zeronode/zeronodeconfig.cpp`.                                                                                                                         |
| Data dir paths         | `~/.zero` (Linux), `~/Library/"Application Support"/zero/` (macOS) | **Correct.**                                                                                                                                                                    |
| Start command          | `startalias "alias"` (Linux/macOS)                                 | **Correct.** `startalias` RPC exists in `src/rpc/zeronode.cpp`. Also available via `startzeronode "alias" "0" "my_zn"`.                                                         |
| Windows start          | SimpleWallet "Start Alias" button                                  | **Cannot verify.** SimpleWallet is archived; `zerowallet` (active GUI) may have different UI.                                                                                   |
| Block explorer         | `insight.zerocurrency.io`                                          | **Superseded.** Mainnet explorer: [insight.zeromachine.io](https://insight.zeromachine.io/). Public docs: README, BUILD_ZERO, ZERO_COIN. |
| Params download        | Not mentioned (script handles it)                                  | **Gap.** Wiki should document `zcutil/fetch-params.sh` for source builds.                                                                                                       |
| `zero.conf` RPC config | Script generates random rpcuser/rpcpassword                        | **Adequate for localhost** but wiki doesn't explain manual config for source builds.                                                                                            |
| Systemd service        | Script creates `/etc/systemd/system/Zero.service`                  | **Not applicable** for source builds. Should document manual systemd setup.                                                                                                     |


Recommendation: retire the wiki page (or add a deprecation banner). Replace with an up-to-date section in BUILD_ZERO covering: (1) build from source, (2) fetch-params, (3) create `zero.conf`, (4) launch `zerod`, (5) zeronode setup (collateral, `zeronode.conf`, `startalias`). Link from README.

*E. GitHub org repo disposition* (47 repos, reviewed Apr 2026):


| Action               | Repos                                                                                                                             | Rationale                                                                |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **Keep public, pin** | `Zero` (main node), `zerowallet` (active GUI)                                                                                     | Active development                                                       |
| **Keep public**      | `Zero-Wallets` (release binaries), `Docs`                                                                                         | User-facing                                                              |
| **Archive**          | `SimpleWallet-archived`, `OptiminerZero-AMD-4GB-GPU-ONLY`, `OptiminerEquihash-AMD-Nvid-GPU`                                       | Already archived or obsolete mining tools                                |
| **Archive**          | `ZeroNodes-UpdatesPending`, `SMOS-SCRIPT`, `Zero-Ultimate-Wallet`, `Zero-Machine`                                                 | Obsolete setup scripts and dead projects                                 |
| **Archive**          | `zero-mobile-wallet`, `zerowallet-mobile`, `zerowallet-lite`, `zerowallet-light-cli`, `cordova-plugin-litewallet`, `lightwalletd` | Abandoned wallet/light-wallet experiments                                |
| **Archive**          | `Zero-Arizen`, `Zero-SwingWallet`, `MyZeroWallet`, `zepio`, `Zero-slate`, `ZDrop`                                                 | Abandoned third-party wallet forks                                       |
| **Archive**          | `Zero-Telegram-Discord-Relay-Bot`, `CMC-bot`, `ZeroTipBot-Telegram`, `wzer_volume`                                                | Dead bots/utilities                                                      |
| **Archive**          | `z-nomp`, `node-stratum-pool`, `Zero-Team-Miningcore-UI`, `iquidus-zero`                                                          | Dead mining pool/explorer forks                                          |
| **Archive**          | `bitgo-utxo-lib`, `bitcore-build-zero`, `bitcoind-rpc`, `zerojs`                                                                  | Dead JS library forks; **not** the active Insight four-pack              |
| **Archive**          | `ZeroWalletGenerator-Paper-Wallet`, `equihashverify-192_7`, `slips`, `blockbook`, `librustzcash`                                  | One-off forks, no maintained divergence                                  |
| **Keep public**      | `insight-ui-zero`, `insight-api-zero`, `bitcore-lib-zero`, `bitcore-node-zero`, `zero-pools-insight-explorer`, `bitcore-message-zero` | Insight stack (2026-06); ops `~/Work/ZK/ZKs/insight/`                  |
| **Keep public**      | `Zero-MiningCore`                                                                                                                 | 4 stars, Equihash 192/7 reference                                        |


*E. GitHub issue suggestions:*

**Issue #70 -- getrawtransaction missing "size" and "fees".** Already acknowledged by maintainer. `size` is straightforward: add `entry.push_back(Pair("size", (int)::GetSerializeSize(tx, SER_NETWORK, PROTOCOL_VERSION)))` in `TxToJSON` / `TxToJSONExpanded` (`src/rpc/rawtransaction.cpp`). `fees` for transparent-only: `sum(vin values) - sum(vout values)`, requires input lookup. For shielded: non-trivial (vpub_old/vpub_new for Sprout, valueBalance for Sapling). Suggest: add `size` now, add `fee` for transparent-only with a `-txindex` requirement, defer shielded fee display. Could be a contributor task.

**Issue #69 -- insight-ui + insight-api.** Infrastructure/hosting request, not a core-node code change. **Address in ops:** mainnet explorer at [insight.zeromachine.io](https://insight.zeromachine.io/); operator detail in `~/Work/ZK/ZKs/insight/`. Close core-repo issue with pointer to public README/BUILD_ZERO explorer sections.

### Consensus and code

**CON-01 -- Total supply discrepancy.** Project target: some **20M ZER**. Current `GetBlockSubsidy` piecewise sum computes ~25.6M long-run. Action: review arithmetic vs spec, determine whether 10.8 post-fee base or halving params need adjustment, compare upstream. `MAX_MONEY` caps per-output only. User-facing docs say "some 20M" until resolved.

**CON-02 -- Consensus integer math.** Replace `double`/`COIN` mixes in `GetBlockSubsidy`, founders `* 0.075`, validation paths with `CAmount` integer policy. At halving 7, `8437500 * 0.075 = 632812.5` causes miner/validator disagreement -- deterministic consensus failure ~21 years out. Fix: `blockValue * 75 / 1000`.

**CON-03 -- Branch id posture.** Sapling and Cosmos share `0x7361707a`. No planned fork to split. Optional: CI guard for duplicate `nBranchId`.

~~CON-05~~ closed -> C-16.

### Release and infrastructure

**REL-01 -- Release signing.** No checksum or signing procedure. See BUILD_ZERO §2.6.

**REL-02 -- macOS developer signing.** Apple Developer Program, `codesign` + `xcrun notarytool`. Without it, Gatekeeper quarantine.

**REL-03 -- Params archival.** `fetch-params.sh` references upstream Zcash names/mirrors. Audit file names vs `zerod` startup, verify URLs.

**REL-04 -- Chain bootstrap.** Document snapshot sourcing, verification, datadir placement. Currently undocumented.

**REL-05 -- Debian packaging.** `build-debian-package.sh` (zcash naming) likely superseded by `release-linux.sh`. Confirm and deprecate.

**REL-06 -- Release branch cleanup.** Fifteen branches (v1.0.12--z21) redundant with tags. Safe to delete remotely.

**REL-07 -- Build validation.** Validated Apr 2026.

*Flag comparison (build-native.sh vs build-win.sh):*


| Flag                                          | Native               | Windows                                                  | Notes                            |
| --------------------------------------------- | -------------------- | -------------------------------------------------------- | -------------------------------- |
| `--enable-hardening`                          | yes (default)        | not passed                                               | **Gap -- see steps below**       |
| `--disable-zmq --disable-rust`                | only with `--daemon` | always                                                   | Intentional: Win has no Rust/ZMQ |
| `--enable-static --disable-shared`            | no                   | yes                                                      | Static cross-build               |
| `CXXFLAGS`                                    | `-g`                 | `-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread` | Different by design              |
| post-configure `sed` (Boost `-mt` -> `-mt-s`) | no                   | yes                                                      | MXE static Boost naming          |


Both pass `HOST`/`BUILD`/`NO_PROTON` to `make -C depends`. `release-linux.sh` only packages -- no configure.

*Steps to resolve the hardening gap:*

1. **Evaluate MinGW hardening support.** `configure.ac` (line 472) checks for `-fstack-protector-all`, `-D_FORTIFY_SOURCE=2`, `-Wformat-security`. On Linux it also adds `-Wl,-z,relro` and `-Wl,-z,now` (RELRO/BIND_NOW). Test which of these MXE's `x86_64-w64-mingw32-g++` accepts.
2. **Add** `--enable-hardening` **to** `build-win.sh`**.** In `run_configure_win()` (`zcutil/build-win.sh:66`), add the flag after `--disable-proton`. If any check fails under MinGW, `configure` will error; handle with conditional or patch `configure.ac` to skip Linux-only linker flags on Windows.
3. **Verify with a test build.** `make -C depends HOST=x86_64-w64-mingw32 && zcutil/build.sh -win`. Confirm `zerod.exe` links with stack protector.
4. **Document.** Update BUILD_ZERO §2.7 (Compiler and release flags) with Windows hardening status.

*References:* `configure.ac:122-126` (hardening arg), `configure.ac:472-492` (hardening checks), `zcutil/build-win.sh:66-71` (Windows configure), `zcutil/build-native.sh:83-86` (native configure).

### Testing

Items marked **"contributor-ready"** are self-contained enough to be written up as GitHub issues with `good first issue` or `help wanted` labels. They have clear scope, acceptance criteria, and don't require signing keys, maintainer authority, or consensus decisions. See also: DEF-06 (SwiftTX strip), CON-03 (branch id CI guard), REL-05 (Debian packaging), REL-07 (Windows hardening), issue #70 (getrawtransaction size/fees) -- all delegable with varying scope.

**TST-01 -- zero_exclusive param validation.** High importance. **Contributor-ready.**

Zero's own RPCs and experimental RPCs have 0% scenario coverage beyond the skeleton param-validation tests already in `src/test/rpc_zero_exclusive_tests.cpp` and `src/test/rpc_zero_experimental_tests.cpp`. Those files currently test that bad argument counts throw `runtime_error` and that basic calls return the expected JSON type, but they do not exercise any wallet state, chain state, or error paths.

*Scope:* Extend the existing Boost.Test files with scenario coverage for each RPC. Each test case should use the `TestingSetup` fixture (wallet + regtest chain) and cover: (a) valid calls with expected return structure, (b) boundary values (empty wallet, zero height, nonexistent address), (c) error paths (invalid address format, out-of-range parameters). RPCs to cover:


| RPC                         | File                              | Current state              |
| --------------------------- | --------------------------------- | -------------------------- |
| `zs_listtransactions`       | `rpc_zero_exclusive_tests.cpp`    | Param count only           |
| `zs_gettransaction`         | same                              | Param count only           |
| `zs_listspentbyaddress`     | same                              | Param count only           |
| `zs_listreceivedbyaddress`  | same                              | Param count only           |
| `zs_listsentbyaddress`      | same                              | Param count only           |
| `getalldata`                | same                              | Param count + basic return |
| `getsupply`                 | same                              | Param count + field check  |
| `getsaplingwitness`         | `rpc_zero_experimental_tests.cpp` | Param count only           |
| `getsaplingwitnessatheight` | same                              | Param count only           |
| `getsaplingblocks`          | same                              | Param count only           |


*How to build and run:* `zcutil/build.sh` (or `build-native.sh`) builds `test_bitcoin`. Run individual suites: `./src/test/test_bitcoin --run_test=rpc_zero_exclusive_tests`. See TEST_ZERO for full instructions.

*Acceptance criteria:* Each RPC has at least 3 test cases (valid, boundary, error). Tests pass under `./contrib/run-tests.sh --strict`. No new dependencies.

*References:* `src/wallet/rpczerowallet.cpp` (RPC implementations), `src/wallet/rpczerowallet.h` (declarations), `src/rpc/client.cpp` (vRPCConvertParams entries), `src/test/rpc_wallet_tests.cpp` (example of existing Boost RPC tests).

**TST-02 -- Parallel Tier A RPC.** Deprioritized. `paymentdisclosure` hang under `--jobs>1`. Serial gate is sufficient.

**TST-03 -- Zeronode / budget subcmd validation.** P1 priority. Write Boost.Test or GTest cases for `zeronodecurrent`, `getzeronodeoutputs`, `startzeronode`, and `znbudget` subcommands. Focus on argument validation and error returns; full integration requires zeronode collateral setup.

**TST-04 -- Zeronode and CDB GTest fixes.** P2 priority. Fix `WalletTests.CachedWitnesses`* (seed `CCoinsViewCache` in harness), fix `CDB::Rewrite` hang (close wallet handle before rewrite or test-only persistence path), unblock `WriteCryptedSaplingZkey*` and `rpc_wallet_encrypted_wallet_sapzkeys`. See §3.3 Debug notes for root cause analysis.

**TST-05 -- Equihash (192,7) test vectors.** **Contributor-ready.**

The existing Equihash tests in `src/test/equihash_tests.cpp` and `src/gtest/test_equihash.cpp` contain solver and validator vectors only for the (96,5) and (48,5) parameter sets inherited from upstream Zcash. Zero uses **(192,7)** (`src/crypto/equihash.h:203`, `Eh192_7`). Both test files detect the mismatch at runtime and skip:

```
// Zero uses (192,7); test vectors are for (96,5). Skip when params mismatch.
if (Params().GetConsensus().nEquihashN != 96) { return; }
```

This means Zero's actual PoW algorithm has **zero known-answer test coverage**.

*Task:* Generate known-answer test vectors for `Equihash<192,7>` and add them to both the Boost and GTest suites.

*Steps:*

1. **Generate vectors.** Use the existing solver (`Equihash<192,7>::BasicSolve` in `src/crypto/equihash.cpp:823`, requires `ENABLE_MINING`). Write a small standalone program or extend a test to: pick a few input strings and nonces, call `BasicSolve`, collect the solution index arrays. Alternatively, extract vectors from known Zero mainnet block headers (parse block, extract `nNonce` and `nSolution`, verify with `Equihash<192,7>::IsValidSolution`).
2. **Add Boost vectors.** In `src/test/equihash_tests.cpp`, add a new `BOOST_AUTO_TEST_CASE(solver_testvectors_192_7)` that calls `TestEquihashSolvers(192, 7, ...)` with the generated vectors. Follow the pattern of the existing `solver_testvectors` case (line 108). Guard with `#ifdef ENABLE_MINING` since solving requires the mining code path.
3. **Add GTest vectors.** In `src/gtest/test_equihash.cpp`, add a `TEST(equihash_tests, check_basic_solver_192_7)` that initializes `Equihash<192,7>`, hashes an input, and verifies the solver produces expected solutions. Follow the pattern of `check_basic_solver_cancelled` (line 84) but assert specific solution contents instead of cancellation behavior.
4. **Add validator vectors.** Add `BOOST_AUTO_TEST_CASE(validator_testvectors_192_7)` that calls `EhIsValidSolution(192, 7, state, minimal_soln, isValid)` with known-good and known-bad solutions. This does not require `ENABLE_MINING`.

*Key files:* `src/crypto/equihash.h` (template declarations, `Eh192_7` instance), `src/crypto/equihash.cpp:820-830` (explicit instantiations for 192,7), `src/test/equihash_tests.cpp` (Boost tests), `src/gtest/test_equihash.cpp` (GTest tests), `src/chainparams.cpp` (`nEquihashN=192`, `nEquihashK=7`).

*Acceptance criteria:* At least 3 solver vectors (different inputs/nonces) and 3 validator vectors (2 valid, 1 invalid). Tests run and pass under `./contrib/run-tests.sh --strict`. Solution arrays are committed as literal data (same style as existing 96,5 vectors). No changes to the Equihash algorithm code.

**TST-06 -- Fuzz harness.** **Contributor-ready.**

Zero has no structured fuzzing infrastructure. The only fuzz-related code is `CNode::Fuzz()` in `src/net.cpp:1943`, a legacy message-corruption function activated by the hidden `-fuzzmessagestest` flag -- it randomly flips bits in outgoing P2P messages, which is not coverage-guided fuzzing and cannot be used for automated bug finding.

*Task:* Set up a coverage-guided fuzz harness using libFuzzer (Clang) or AFL, targeting the highest-value attack surfaces.

*Recommended initial targets (in priority order):*

1. **Deserialization.** `CBlock`, `CTransaction`, `CBlockHeader` deserialization from untrusted byte streams. Entry point: `CDataStream >> obj`. Malformed blocks/txs are the most common P2P attack vector.
2. **Script parsing.** `CScript` operations, `EvalScript`, `VerifyScript`. Entry point: construct a `CScript` from fuzz input, evaluate.
3. **Equihash validation.** `Equihash<192,7>::IsValidSolution` with arbitrary solution bytes. Tests that the validator rejects malformed solutions without crashing.
4. **Address parsing.** `DecodeDestination`, `KeyIO` functions with arbitrary strings.

*Steps:*

1. **Add a fuzz target directory.** Create `src/fuzz/` with one `.cpp` file per target. Each file defines `extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)` (libFuzzer convention).
2. **Example -- transaction deserialization fuzz target:**
  ```cpp
   #include "primitives/transaction.h"
   #include "streams.h"
   #include <cstdint>
   #include <vector>

   extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
       CDataStream ss(std::vector<unsigned char>(data, data + size),
                      SER_NETWORK, PROTOCOL_VERSION);
       try {
           CTransaction tx;
           ss >> tx;
       } catch (...) {}
       return 0;
   }
  ```
3. **Build integration.** Add a `Makefile.am` target or a standalone `CMakeLists.txt` that compiles fuzz targets with `-fsanitize=fuzzer,address` (Clang) or links against AFL's compiler wrappers. Bitcoin Core's `src/test/fuzz/` is a good reference for Makefile integration patterns.
4. **Seed corpus.** Extract raw serialized transactions and blocks from the regtest chain (`zerod -regtest`, then `zero-cli getblock <hash> 0` for hex) to seed the fuzzer's initial corpus.
5. **CI integration (optional).** Add a GitHub Actions job that runs each fuzzer for a fixed duration (e.g., 60 seconds) on each push, primarily to catch regressions.



*References:* Bitcoin Core `src/test/fuzz/` (mature fuzz harness, same serialization framework), Zcash `src/test/fuzz/` (if present), libFuzzer docs ([https://llvm.org/docs/LibFuzzer.html](https://llvm.org/docs/LibFuzzer.html)), AFL++ docs ([https://github.com/AFLplusplus/AFLplusplus](https://github.com/AFLplusplus/AFLplusplus)).

*Acceptance criteria:* At least 2 fuzz targets (deserialization + one other) that compile and run for 60 seconds without crashing on a clean regtest corpus. Documented build instructions in a `src/fuzz/README.md` or in TEST_ZERO. No changes to production code required.

**TST-07 -- Partition and wallet tests.** P3 priority. Partition P2P test (`split=True` edge topology), wallet backup/restore scenario. Requires `CHAIN_BOOTSTRAP` and maturity mining. See §3.3 test prescriptions for regtest setup.

**TST-08 -- PIR-03 witness lockout (`RPC_BUILDING_WITNESS_CACHE = -33`).** P1 priority. **Blocks PIR-03 merge without this or an equivalent regtest check.**

*Problem:* While **`BuildWitnessCache`** runs, **`initWitnessesBuilt`** is false and witness state is mid-rebuild. Without **`fBuildingWitnessCache`**, **`z_sendmany`** could proceed with stale witnesses or only the generic **-31** (`RPC_DISABLED_BEFORE_WITNESSES`) when witnesses were never built -- not when a rebuild is in flight.

*Scope (GTest, minimal):*

1. Set **`fBuildingWitnessCache = true`** (and wallet loaded) in a test fixture.
2. Invoke RPC dispatch for **`z_sendmany`** (same path as **`src/rpc/server.cpp`** table lookup + **`JSONRPCError`**).
3. Assert JSON-RPC **error code -33** and message substring **`building witness cache`**.

*Optional follow-up:* regtest that triggers a real **`BuildWitnessCache`** (slow; harness lacks full **`pcoinsTip`** chain -- see **`CachedWitnessesCleanIndex`** notes in TEST_ZERO).

*Files:* new case in **`src/wallet/gtest/`** or **`src/gtest/`** exercising **`tableRPC`** / **`CRPCTable::execute`**; **`src/rpc/protocol.h`** (**`-33`**), **`src/rpc/server.cpp`**, **`src/wallet/wallet.cpp`**.

*Acceptance:* **`./src/zero-gtest --gtest_filter=...`** passes; case included in default pass-only gate once stable.

### Deferred

**DEF-02 -- OpenSSL.** Remain on 1.1.1w until audited 3.x or removal. 1.1.1 EOL Sep 2023; no upstream patches. Zero uses OpenSSL for RPC TLS and legacy EVP call sites. Peer comparison: Horizen retains 1.1.1w; Zcash and Bitcoin removed OpenSSL entirely. See BUILD_ZERO §4.1 (OpenSSL row), §3.2 (peer comparison). Migration path: audit all `EVP_`*, `SSL_*`, `RAND_*` call sites, add TLS regression tests, then bump or remove.

~~DEF-03~~ closed -> C-17.

~~DEF-04~~ closed (legacy Proton build; **section 6**).

**DEF-05 -- Boost >1.88.** Googletest 1.16.0 is the last release on C++14; GTest 1.17+ requires C++17. A Boost bump past 1.88 may also require C++17 headers. Upgrade path: evaluate C++17 readiness of all `src/` code, revalidate `ax_boost_`* m4 macros, rebuild full depends graph. See BUILD_ZERO §4.1 (Boost, Googletest rows).

**DEF-06 -- SwiftTX removal.** Zeronode instant-confirmation quorum (see Reference below). Not implemented on the Zero network; `SPORK_2_SWIFTTX` never activated. Plan: remove `src/zeronode/swifttx.cpp`, `swifttx.h`, hidden CLI options (`-enableswifttx`, `-swifttxdepth`), P2P messages (`ix`, `txlvote`), lock-conflict checks in `main.cpp`. Keep `-deleteconflicttx` (serves `-deletetx` pruning for reorgs/double-spends independent of SwiftTX). Remove `Options.csv` SwiftTX hidden entries. Blocked on: confirming no mainnet spork activation history.

**DEF-07 -- TNT-02 / TNT-03 deep reorg policy.** **Postponed.** Zero shuts down when reorg or rewind depth exceeds **`MAX_REORG_LENGTH` (99)** while **`COINBASE_MATURITY` is 720**. Zeronode operators can be forced offline on reorgs between 100 and 719 blocks. TENT removed this shutdown for masternode survival; Zero has not. **Recommendation:** one adapted PR -- relax shutdown (**TNT-02**), pick a justified new cap and witness-cache sizing (**TNT-03**), regtest before mainnet. Full logic: **§3.5.1**. Not scheduled until **TNT-12** harness exists. Independent of **PIR-03** and Insight work.

### Reference

**SwiftTX.** Zeronode quorum instant-lock (`SWIFTTX_SIGNATURES_REQUIRED` / `SWIFTTX_SIGNATURES_TOTAL` in `src/zeronode/swifttx.h`). Controlled by `SPORK_2_SWIFTTX` (never activated on mainnet). Code: `src/zeronode/swifttx.cpp`, `src/main.cpp`. **Planned for removal** (DEF-06).

**Hidden options and CLI inventories.** Options parsed in `src/init.cpp` but not shown in `--help` output. Tracked in `Options.csv` as `*-hidden` category.


| Option              | Default  | Effect                                                                                                  | Disposition     |
| ------------------- | -------- | ------------------------------------------------------------------------------------------------------- | --------------- |
| `-deleteconflicttx` | true     | With `-deletetx`, allow removing conflicted wallet txs (reorgs, double-spends -- not SwiftTX-specific). | Keep            |
| `-enableswifttx`    | true     | Wallet-side SwiftTX lock acceptance.                                                                    | Remove (DEF-06) |
| `-swifttxdepth`     | 5 (0-60) | Virtual confirmation depth for SwiftTX-locked txs.                                                      | Remove (DEF-06) |


**CSV inventories.** `RPCs.csv`, `RPCs_extended.csv`, `Options.csv`, `Options_extended.csv`, `Reindex_Rescan.csv`. Update both base and extended files when adding or removing RPCs, options, or hidden options. The `*-hidden` category in `Options.csv` tracks undocumented options listed above.

**Test exclusions.** Default pass-only filters, reasons, and mitigation directions: TEST_ZERO §Known failures.

### Completed

Kept for merge-conflict prevention: if an upstream merge re-introduces a pattern listed here, the maintainer can detect the regression.


| #    | Item                 | Detail                                                                                                                  |
| ---- | -------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| C-01 | Chain economics doc  | ZERO_COIN.md consolidated; subsidy excerpts in §2.                                                                      |
| C-02 | Doc consolidation    | UpdateBuild / UpdateTests folded into §3.                                                                               |
| C-03 | `run-tests.sh` jobs  | `run_bg` / `BG_LAST_PID`; child exit codes correct.                                                                     |
| C-04 | `getchaintips` test  | Split topology, `CHAIN_BOOTSTRAP = 30`, branch/rejoin assertions.                                                       |
| C-05 | `rescan_import.py`   | Git index mode 100755.                                                                                                  |
| C-06 | macOS system Rust    | `RUST_USE_SYSTEM` in `depends/packages/rust.mk`.                                                                        |
| C-07 | Null guard           | `CheckInputsAndAdd` in `zeronode.cpp` null-checked. Ref: A6.                                                            |
| C-08 | Unicode cleanup      | Decorative Unicode stripped from all docs except README.md.                                                             |
| C-09 | Branch cleanup       | `backup/attribution-rewrite-202603201534` deleted.                                                                      |
| C-10 | Tag fix              | `v.3.3.1` and `v3.3.12` replaced with `v3.3.1` (pushed).                                                                |
| C-11 | Iterator fix         | `zeronodeman.cpp:323-324` erase order corrected. Ref: A1.                                                               |
| C-12 | throw new            | Removed from 5 C++ sites. Ref: A2.                                                                                      |
| C-13 | Debug stdout         | Cited paths (`wallet/src/`) not in tree; false positive. Ref: A5.                                                       |
| C-14 | chainActive guards   | `CZeronodePing` and `CreateNewLock` null-guarded. Ref: A6, CON-04.                                                      |
| C-15 | Rust system default  | System Rust on all platforms; 1.32.0 legacy/CI-only. Ref: DEF-01.                                                       |
| C-16 | zcrawreceive posture | Legacy Sprout RPC; self-deprecated, dead on Sapling nodes. No action until Sprout strip. Ref: CON-05.                   |
| C-17 | librustzcash pin     | Snapshot `06da3b9` consensus-linked; no upgrade without new NU. Ref: DEF-03.                                            |
| C-18 | Legacy Proton build  | Off by default (`NO_PROTON=1`). Not productized; use ZMQ. **Section 6**.                                                |
| C-19 | `-port` help text    | Was 8233/18233 (Zcash); fixed to 23801/23802. `src/init.cpp:417`.                                                       |
| C-20 | Stale comments       | `util.cpp` data dir comment `~/.zcash` -> `~/.zero`; collateral comment `1000` -> `10000`.                              |
| C-21 | Zeronode chainActive | Negative `nBlockHeight` guard in `swifttx.cpp`; reorg-safe `GetZeronodeInputAge`; `GetLastPaid` uses `pindexPrev` only. |


---



## 4. Blockbook and explorer backends

Daemon ecosystem compare: `~/Work/ZK/ZKs/ZKNodes.md`. Blockbook port detail stays in this section **4** only. **zerod** structure and use-case options: `ZeroStruct.md`.

### 4.1 What Blockbook is

[Trezor Blockbook](https://github.com/trezor/blockbook): Go service that maintains **its own** address/tx index while syncing from a full node's JSON-RPC. Targets Trezor Suite and packaged `.deb` backends. **Does not** require `-insightexplorer` on the node; does require a synced daemon with `txindex=1` for arbitrary `getrawtransaction`.

Zero org fork (`zerocurrencycoin/blockbook`) has no `configs/coins/zero.json` and is abandoned. **Insight/Bitcore** is operational separately (`section 4.3`). Blockbook Zero port remains an **infra track**, not a core-node cherry-pick.

### 4.2 Zcash port -- JSON path (Zero port template)

Reference: `trezor/blockbook` `bchain/coins/zec/`, `configs/coins/zcash.json`.


| Item                                            | Zcash mainnet                                                   |
| ----------------------------------------------- | --------------------------------------------------------------- |
| Blockbook public / internal / backend RPC / ZMQ | 9132 / 9032 / 8032 / 38332                                      |
| Block ingest                                    | `getblock <hash> 2` -- full JSON txs                            |
| Field hack                                      | Replace `"valueZat"` with `"valueSat"` in JSON                  |
| Txids in v2 body                                | Missing; second call `getblock <hash> 1` for id list            |
| Memory fallback                                 | On RPC size error: v1 block + per-tx `getrawtransaction`        |
| Parsing                                         | `ZCashParser.ParseTxFromJson` -- **no** raw binary block parser |
| Mempool                                         | Same JSON path via `getrawtransaction`                          |


**Zero port estimate:** new `configs/coins/zero.json` (ports in unused Blockbook series), point `backend_rpc` at **23811**, t-address HRP/SLIP44 for Zero, reuse **ZEC Go package** pattern (JSON RPC). No Firo-style binary parser unless Zero block wire format diverges (it does not today).

### 4.2a Blockbook detail and self-hostable alternatives

Trezor's explorer/indexer, Go over RocksDB, multi-coin from the ground up — where the broader Zcash ecosystem is consolidating. DB-backed RocksDB scales the address indexing that strains the Node-8 Insight heap (the Insight crash-#3 OOM class). **Best long-term fit, postponed per direction:** a new language/runtime (Go/RocksDB) and a separate deployment; near-term effort is keeping Insight healthy.

Upstream `configs/coins/` ships **100** coin configs including `zcash.json` / `zcash_testnet.json`, `flux.json`, `snowgem.json` (TENT), `firo.json` — so Zcash, Flux, SnowGem, Firo have templates. **No** `zero.json`: a Zero config would be authored from `zcash.json`, whose address/equihash handling is already present upstream.

**Local clone provenance.** `~/Work/ZK/ZKs/insight/blockbook/` cloned `--depth 1` 2026-06-20 from `github.com/trezor/blockbook` (canonical upstream, not a fork); branch `master`, HEAD `cfa7374` (2026-06-19). `zerocurrencycoin/blockbook` is a **2020 fork** (last push 2020-12-23), an abandoned earlier Zero-on-Blockbook attempt; the fresh upstream clone supersedes it. `~/Work/ZK/ZKs/insight/lbe-hellcatz/` cloned `--depth 1` 2026-06-20 from `github.com/hellcatz/lbe-css`; branch `master`, HEAD `60d5e73` (2023-05-19); root `ondrejsika/lbe` (2020). Both tiny single-maintainer projects — lightweight references, not maintained products.

**Self-hostable explorer alternatives** (Blockbook in context):


| Explorer                                                                                          | Stack                         | Multi-coin                           | Fit for Zero                                                                                                                                            |
| ------------------------------------------------------------------------------------------------- | ----------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Blockbook (Trezor)**                                                                            | Go + RocksDB                  | Yes (many, incl. Zcash forks)        | **Best long-term**; postponed per direction (detail above).                                                                                             |
| Iquidus Explorer                                                                                  | Node.js + MongoDB             | One coin/instance, re-skinnable      | Proven on Zcash forks (Hush runs it); DB-backed; viable fallback.                                                                                       |
| LBE (hellcatz, fork of ondrejsika/lbe)                                                            | Python/Flask, RPC-only, no DB | Yes; explicitly Zcash/equihash forks | Lightweight; needs only `getblock`/`getrawtransaction`/`decoderawtransaction`; **lacks rich address indexing** → reference/fallback, not a replacement. |
| btc-rpc-explorer                                                                                  | Node.js, RPC-only             | Bitcoin-likes                        | Weak fit (not shielded-aware).                                                                                                                          |
| Hosted aggregators (Blockchair, Tokenview, blockexplorer.one, chainz.cryptoid, Foundry zcashinfo) | SaaS                          | Yes                                  | Reference UIs; not self-hostable.                                                                                                                       |




### 4.3 Insight / Bitcore (Zero status)

**Public mainnet explorer:** [insight.zeromachine.io](https://insight.zeromachine.io/)

Stack: `insight-ui-zero`, `insight-api-zero`, `bitcore-node-zero`, `bitcore-lib-zero`. Public operator summary in **README**, **BUILD_ZERO** (Block explorer), **ZERO_COIN**. Internal runbooks: `~/Work/ZK/ZKs/insight/`.

**Node requirements** (`zerod`):

```ini
experimentalfeatures=1
insightexplorer=1
txindex=1
```

First enable of `-insightexplorer` requires **`-reindex`**. Large `-dbcache` (4096+ MiB on mainnet) recommended — see `ZeroStruct.md` Insight use case.

Uses **daemon addressindex RPCs** (`getaddressbalance`, `getaddresstxids`, ...), not Blockbook's internal index. **Transparent P2PKH/P2SH only** — no chain-wide shielded (z-addr) search.

Pirate `insight-api-pirate` (2024 tx format) is a **JS diff anchor** only — not a `zerod` cherry-pick.

**Blockbook** remains a separate optional backend (`section 4.1`); it does not require `-insightexplorer` on the node.

### 4.4 Operator comparison


| Approach                     | Node load                          | Index location                  | Best for                |
| ---------------------------- | ---------------------------------- | ------------------------------- | ----------------------- |
| `-insightexplorer` + Bitcore | High; 75% `-dbcache` to block tree | `blocks/index/`                 | Mainnet Insight UI ([insight.zeromachine.io](https://insight.zeromachine.io/)) |
| Blockbook + plain `txindex`  | RPC-heavy sync                     | Blockbook LevelDB               | Trezor-style API        |
| `gettxoutsetinfo` only       | Periodic scan                      | None per-address                | Supply audit            |
| `contrib/stats/*`            | RPC optional                       | None (model or coinbase decode) | Zero emission reporting |


---



## 5. Pirate wallet features under review

**Repo:** `~/Work/ZK/ZKs/pirate`. Portable wallet ops only -- not Komodo consensus, notary, or KIP coinbase (**PIR-14 reject**). Wallet vs consolidation on-chain behavior: `ZeroStruct.md` **section 6**.

### 5.1 Already in Zero


| Mechanism                  | Zero flags / code                                                        | On-chain?                                                                |
| -------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| Auto Sapling consolidation | `-consolidation=1`, `-consolidatesaplingaddress=`, `-consolidationtxfee` | Yes -- `AsyncRPCOperation_saplingconsolidation`, `CommitConsolidationTx` |
| Manual merge               | `-experimentalfeatures`, `-zmergetoaddress` -> `z_mergetoaddress` RPC    | Yes -- `SendTransaction` / `CommitTransaction`                           |
| Witness rebuild gap        | `BuildWitnessCache` / `initWitnessesBuilt`                               | N/A -- **PIR-03** port candidate                                         |




### 5.2 Pirate capabilities under consideration


| Feature                            | Pirate                                          | Zero today                      | Recommendation                                                                      |
| ---------------------------------- | ----------------------------------------------- | ------------------------------- | ----------------------------------------------------------------------------------- |
| `consolidateaddress` **RPC**       | Manual trigger per z-addr                       | None                            | **Review** -- operator control for large Sapling wallets; adapt without Komodo deps |
| `consolidationstatus` **RPC**      | Status of auto consolidation                    | None                            | **Review** -- low cost if auto consolidation stays                                  |
| `z_getbalances`                    | All z-addrs + balances in one call              | None (`z_gettotalbalance` only) | **Review** -- wallet UX; Zcash upstream still draft PR                              |
| **Cleanup / dust modes**           | Aggressive consolidation; dust filter threshold | None                            | **Review** -- useful for spammed wallets; define Zero policy thresholds             |
| **GetFilteredNotes optimization**  | Large-wallet note selection                     | Older path                      | **Consider** with PIR-03 witness work                                               |
| `maxprocessingthreads`             | Throttle witness/decrypt threads                | None                            | **Consider** -- ops tuning                                                          |
| **Witness lockout during rebuild** | `fBuildingWitnessCache` blocks `z_sendmany`     | Gap documented                  | **Port (PIR-03)**                                                                   |
| **Knapsack early exit**            | Perf                                            | Missing                         | **Port (PIR-02)**                                                                   |




### 5.3 Reject for Zero (Pirate-specific)


| Item                                         | Reason                               |
| -------------------------------------------- | ------------------------------------ |
| KIP coinbase, notary RPCs, `-ac_*`           | Komodo assetchain                    |
| RT_CST_RST PoW                               | Consensus change                     |
| `z_getbalances` tied to Komodo account model | If ported, use Zcash-shaped API only |




### 5.4 Suggested port order (wallet)

1. **PIR-03** witness lockout + regtest/`z_sendmany` guard test.
2. `consolidateaddress` RPC (manual consolidation) reusing `AsyncRPCOperation_saplingconsolidation` building blocks.
3. `z_getbalances` or document `z_gettotalbalance` + `z_listaddresses` workaround.
4. Dust filter / cleanup mode -- product decision on default thresholds.

---



## 6. Legacy Proton build (not productized)

Optional `--enable-proton` build of upstream `src/amqp/` (Qpid Proton). Default `NO_PROTON=1`. Duplicates ZMQ pub/sub; no operator docs, no CI, no planned ports. Use `-zmqpub*` for block/tx notifications. Optional code deletion PR later; no action required.

## 7. Pending public documentation (drafts for review)

**Public docs do not link** to maintainer files (**UpdateZero.md**, **ZeroStruct.md**, **ZKNodes.md**, etc.). When a draft below is approved, **copy the markdown block** into the target public file without adding maintainer hrefs.

### 7.0 Draft backlog


| Target            | Draft                                             | Status                                                                    | Maintainer source (do not link from public) |
| ----------------- | ------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------- |
| **ZERO_COIN.md**  | **7.1** dev balances (insight)                    | Ready                                                                     | `contrib/stats/chain_stats.py`              |
| **ZERO_COIN.md**  | **7.2** supply vs UTXO                            | Ready                                                                     | **ZeroStruct** use cases                    |
| **ZERO_COIN.md**  | **7.7** zeronode boundary (economics vs setup)    | Ready                                                                     | **ZeroNodes** operator detail               |
| **BUILD_ZERO.md** | **7.3** explorer node flags                       | Copied (**Block explorer** section)                                       | **ZeroStruct** Insight use case             |
| **BUILD_ZERO.md** | **7.6** REST                                      | Ready                                                                     | **ZeroStruct** REST row                     |
| **BUILD_ZERO.md** | **7.8** public testnet join                       | Ready                                                                     | DOC-02 / testnet seeds                      |
| **BUILD_ZERO.md** | **7.9** zeronode operator (optional)              | **Deferred** -- keep in **ZeroNodes** until product approves public steps | **ZeroNodes**                               |
| **README.md**     | **7.4** node vs wallet scope                      | Copied (Block explorer + scope)                                           | **ZeroStruct**                              |
| **Insight.md**    | **7.5** flag bundle                               | Copied (**BUILD_ZERO** Block explorer)                                    | **ZeroStruct** Insight use case             |
| **ZERO_COIN.md**  | Port/datadir matrix excerpt from DOC-02           | **Gap**                                                                   | **UpdateZero** DOC-02 table                 |
| **BUILD_ZERO.md** | `-blocknotify` / `ENABLE_SYSTEM_COMMAND` (PIR-01) | Ready (**4.6** Shell notify hooks)                                        | **UpdateZero** **3.4.2**                    |
| **README.md**     | Testnet one-liner                                 | **Gap**                                                                   | seeds in `chainparams.cpp`                  |


**ZeroNodes.md** / **ZeroNodeDev.md** stay **maintainer-only** (section **1**). Public **ZERO_COIN.md** keeps **economics and coinbase order**; full `startalias` workflow waits on **7.9** approval or stays internal.

### 7.1 ZERO_COIN.md -- insight for dev balances

```markdown
On-chain dev address balances (compare to emission model) require a synced mainnet node with:

experimentalfeatures=1
insightexplorer=1

Then: ./contrib/stats/chain_stats.py --cons --dev
```



### 7.2 ZERO_COIN.md -- supply vs UTXO

```markdown
`chain_stats.py --cons` sums consensus subsidy (miner + nodes + dev split). It is not the UTXO set total.
For aggregate transparent total at tip use `gettxoutsetinfo` (slow). Per-address balances need `-insightexplorer` or an external indexer.
```



### 7.3 BUILD_ZERO.md -- explorer node flags

```markdown
Dedicated explorer / indexer node (not recommended for desktop wallet):

experimentalfeatures=1
insightexplorer=1
txindex=1
dbcache=4096

First enable requires one run with `-reindex`. Insight uses ~75% of `-dbcache` for `blocks/index/`.
Mainnet RPC 23811.
```



### 7.4 README.md -- node vs wallet scope

```markdown
This repository builds the full node (zerod, zero-cli, zero-tx). The Qt wallet (zerowallet) is a separate application and does not enable blockchain address indexes by default.
```



### 7.5 Insight operator flag bundle (public draft)

```markdown
Required zerod configuration:

experimentalfeatures=1
insightexplorer=1
txindex=1

Addressindex RPCs: getaddressbalance, getaddresstxids, getaddressdeltas, getaddressutxos, getaddressmempool, getspentinfo, getblockdeltas, getblockhashes.
Transparent P2PKH/P2SH only. Regtest tests: TEST_ZERO.md experimental section.
```



### 7.6 BUILD_ZERO.md -- REST

```markdown
Optional HTTP REST (`-rest=1`) exposes Bitcoin-Core-style GET endpoints on the RPC port (`/rest/tx/`, `/rest/block/`, `/rest/mempool/`, `/rest/getutxos`). Default off. Not used by Insight. Test: qa/rpc-tests/rest.py.
```



### 7.7 ZERO_COIN.md -- zeronode economics vs operator setup

```markdown
## Zeronode payments (economics)

This section documents **coinbase splits and spork-gated tiers** (20-40% of block value when enabled). It does not replace a full operator runbook.

Running a zeronode requires **10,000 ZER** collateral locked in a UTXO, a synced **zerod** with wallet, and a **`zeronode.conf`** entry. Use `zero-cli zeronode genkey` and `zeronode startalias` after the collateral transaction confirms. Mainnet P2P **23801**, RPC **23811**.

For spork names and payment order in coinbase, see **Zeronode payments** above. For emission totals, use `./contrib/stats/chain_stats.py --cons`.
```



### 7.8 BUILD_ZERO.md -- public testnet join

```markdown
### Public testnet

Add to `zero.conf`:

testnet=1
rpcuser=...
rpcpassword=...

DNS seeds: `testnet1.zerocurrency.io`, `testnet2.zerocurrency.io` (verify live peers before relying).

./src/zerod -testnet -daemon
./src/zero-cli -testnet getblockchaininfo
```

No qa harness connects to testnet; use **regtest** for automated tests (**TEST_ZERO.md**).

```

### 7.9 BUILD_ZERO.md -- zeronode operator (deferred)

```markdown
```



### Zeronode operator

Collateral: **10,000 ZER**. Configure `zeronode.conf`, then `zero-cli zeronode startalias <alias>`.

(Full steps pending maintainer review -- economics in ZERO_COIN.md **Zeronode payments**.)

```

Copy from **ZeroNodes.md** when approved for public release; until then keep operator detail maintainer-only.

---

## 8. RPC and options CSV verification (2026-06)

Files: **`RPCs.csv`**, **`RPCs_extended.csv`**, **`Options.csv`**. Update base + extended together when adding RPCs.

### 8.1 Corrections applied

| Row | Was | Now | Reason |
|-----|-----|-----|--------|
| `getaddresstxids`, `getaddressbalance`, `getaddressdeltas`, `getaddressutxos`, `getaddressmempool` pirate column | `n` | **`y`** | Pirate uses legacy `addressindex=1` config; same RPC family as Zcash/Zero |
| `consolidateaddress`, `z_getbalances` | missing | **added** (Pirate `y`, Zero `n`) | Pirate-only wallet RPCs under review (**section 5**) |

### 8.2 Confirmed accurate (spot checks)

| RPC / flag | Zero | Notes |
|------------|------|-------|
| `getspentinfo`, `getblockdeltas`, `getblockhashes` | y | insightexplorer gate |
| `gettxoutsetinfo` | y | No per-address dump |
| `z_mergetoaddress` | y | Requires `-zmergetoaddress` |
| `getexperimentalfeatures` | n in Zero | No RPC; use `-experimentalfeatures` flag only |
| `z_gettreestate`, `z_getsubtreesbyindex` | n | Zcash NU5+ RPCs |
| `-insightexplorer` | Options | Bundled index flag in Zero (not separate `addressindex` option) |
| Pirate index config | separate `addressindex=1` lines | Same RPCs; config style differs (**`ZKNodes.md`**) |

### 8.3 Intentional `zero_missing_sources` column

**B** = in CSV for cross-chain inventory only; **not implemented** in Zero (`dumptxoutset`, `scantxoutset`, Core descriptor RPCs, etc.). Do not treat as planned ports.

---

## Appendix: Identified issues

External AI-assisted code audit (Mar 2026), maintainer triage, subsequent review. Original log in `zero_errs.txt` (not a source file; unmodified).

### A1. Iterator bug in zeronode cleanup

**Cited:** `src/zeronode/zeronodeman.cpp:323-324`. Two-map erase in wrong order; correct pattern at lines 263-267.

**Status:** Fixed. -> C-11. Code: §3.1 (Zeronode / spork group).

### A2. throw new std::runtime_error (5 sites)

**Cited:** `src/transaction_builder.cpp:82`, `src/main.cpp:7477`, + 3 in `src/zcbenchmarks.cpp`. Inherited from upstream Zcash (same pattern in `zcash/zcash` master and Horizen).

**Fix (pattern).** Replace:

```cpp
throw new std::runtime_error("message");
```

with:

```cpp
throw std::runtime_error("message");
```

**Commit:** `a09cea932` (Renames and fixes, Mar 2026).

**Status:** Fixed. -> C-12. Policy: §2 (C++ exceptions).

### A3. Floating-point in block subsidy

**Cited:** `src/main.cpp:2113`, `src/main.cpp:4508`. At halving 7, `8437500 * 0.075 = 632812.5` causes miner/validator disagreement.

**Status:** Open. -> CON-01 (supply), CON-02 (integer math). Code touchpoints: BUILD_ZERO §4.8.1.

### A4. Duplicate branch ID

**Cited:** `src/consensus/upgrades.cpp:28-33`. Sapling and Cosmos both use `0x7361707a`.

**Status:** Open. -> CON-03. Reference: §2 Consensus (Branch id).

### A5. Debug output leaks

**Cited:** `wallet/src/rpc.cpp:1281`, `wallet/src/websockets.cpp:698`.

**Status:** False positive. Zero's directory is `src/wallet/`, not `wallet/src/`. Neither `websockets.cpp` nor `rpc.cpp` exists at the cited paths. Full `std::cout` audit: no release-path leaks. -> C-13.

### A6. Null deref in CheckInputsAndAdd

**Cited:** `src/zeronode/zeronode.cpp:615-616`. `chainActive[pMNIndex->nHeight + 14]` returns NULL on short chains.

**Status:** Fixed. -> C-07 (original site), C-14 (remaining two sites). All `chainActive` dereferences in `src/zeronode/` now guarded.

### A7. OpenSSL 1.1.1w + Rust 1.32.0

**Cited:** `depends/packages/openssl.mk:2`, `depends/packages/rust.mk:31`. EOL and outdated respectively.

**Status:** Open. -> DEF-01 (Rust), DEF-02 (OpenSSL). Peer comparison: §3.2.

### A8. Build notes

**Cited:** fetch-params mirrors, `-g` in release, no signing.

**Status:** Open. -> REL-01 (signing), REL-02 (macOS signing), REL-03 (params). Compiler flags: BUILD_ZERO §2.7.

### Tracking summary


| ID  | Description            | Status         | Tracking       |
| --- | ---------------------- | -------------- | -------------- |
| A1  | Iterator erase order   | Fixed          | C-11           |
| A2  | throw new (5 sites)    | Fixed          | C-12           |
| A3  | Float in subsidy       | Open           | CON-01, CON-02 |
| A4  | Duplicate branch ID    | Open           | CON-03         |
| A5  | Debug stdout leaks     | False positive | C-13           |
| A6  | Null deref chainActive | Fixed          | C-07, C-14     |
| A7  | OpenSSL/Rust versions  | Open           | DEF-01, DEF-02 |
| A8  | Build/params/signing   | Open           | REL-01..03     |


---

## DOC-02 follow-up: zeronode documentation and functional tests

Outline for closing gaps from zeronode gap analysis and mainnet coinbase verification (Jun 2026). **TENT cherry-pick table:** `UpdateZero.md` section 3.5. **Zeronode port detail and test roadmap:** `ZeroNodeDev.md` section **9**.

### Documentation deliverables


| Step | Deliverable              | Target doc                                                     | Content                                                                           |
| ---- | ------------------------ | -------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| 1    | **Operator runbook**     | `BUILD_ZERO.md` new subsection or README link                  | Build, `fetch-params`, `zero.conf` RPC creds, `zerod` launch, ports (23801/23811) |
| 2    | **Zeronode setup**       | Replace obsolete wiki / `ZeroNodes-UpdatesPending` script refs | Collateral 10k ZER, `zeronode.conf` -- see `ZeroNodes.md`                         |
| 3    | **Economics cross-link** | `ZERO_COIN.md`                                                 | Coinbase 3-way split, emission tables, `chain_stats.py`                           |
| 4    | **Wallet boundary**      | `ZeroNodeDev.md` + `ZeroNodes.md`                              | Dev interface vs operator workflow                                                |
| 5    | **Security pointer**     | `ZcashFixes.md` + ZERO_COIN Security                           | Sapling-only, no Orchard, Sprout CVE N/A                                          |
| 6    | **Multisig founders**    | `Zeros/MULTISIG.md` appendix                                   | Done Jun 2026                                                                     |


### Functional test roadmap (TST-03 extension)


| Phase | Test                          | Harness                                                        | Pass criteria                                                              |
| ----- | ----------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **A** | RPC argument validation       | Existing `rpc_zeronode_tests`, `rpc_zeronode_budget_tests`     | Expand budget subcmds per TST-03                                           |
| **B** | Regtest single-node coinbase  | New `qa/rpc-tests/coinbase_rewards.py` or gtest                | After height 5000: founders vout 7.5%, zeronode vout when spork on         |
| **C** | Regtest 2-node zeronode       | Manual -> scripted                                             | Collateral UTXO, `startalias`, payment in coinbase within N blocks         |
| **D** | Reorg / `GetZeronodeInputAge` | Regtest `invalidateblock`                                      | Steps in DOC-02 subsection (already written); automate when harness allows |
| **E** | Mock wallet                   | Inject `CZeronodeWalletInterface` test double                  | Ping/payment paths without full wallet                                     |
| **F** | Mainnet decode regression     | `decode_coinbase.py` optional CI fixtures (see `ZERO_COIN.md`) | Requires archived block hash fixtures or mocked RPC                        |


### Priority order

1. Phase A (low cost, extend existing Boost suites).
2. Phase B (consensus-critical coinbase + founders alignment with `test_foundersreward.cpp`).
3. DOC steps 1-2 (retire broken external install docs).
4. Phase C (multi-node -- highest value, highest setup cost).

---

## Testnet and regtest: usage, gaps, documentation placement

### Zero networks (from code + TEST_ZERO.md)


| Network     | P2P   | RPC   | Equihash | Fee-start    | Harness use                       |
| ----------- | ----- | ----- | -------- | ------------ | --------------------------------- |
| **mainnet** | 23801 | 23811 | 192,7    | block 412300 | Manual ops only; **no CI**        |
| **testnet** | 23802 | 23812 | 192,7    | block 1      | **Not used** by qa harness        |
| **regtest** | 23803 | 23813 | 48,5     | block 5000   | **All** automated RPC/Boost tests |


**Regtest notes:**

- `-regtest=1`; mine with `generate` / `generatetoaddress` (not `setgenerate` on testnet -- `fMiningRequiresPeers`).
- NU activation: `-nuparams=<branchHex>:<height>` (see `TEST_ZERO.md`, `util.py` `NU_TEST_ARGS`).
- Frozen cache tip **725** (`COINBASE_MATURITY` 720 + 5) for fast wallet tests.
- Public testnet: no min-difficulty rule on Zero (see **ZeroNodeDev.md** section **9**).

**Testnet notes:**

- Public peers exist but **qa/pull-tester never connects** to testnet (by design).
- `turnstile.py` documents optional manual testnet steps (Bfail Retired tier).
- Operators: same `fetch-params` as mainnet; `testnet=1` in `zero.conf`.

### Where to document (future doc map)


| Topic                       | Primary home                                        | Secondary                     |
| --------------------------- | --------------------------------------------------- | ----------------------------- |
| Regtest dev workflow        | `TEST_ZERO.md` (exists)                             | `BUILD_ZERO.md` quick pointer |
| Testnet join / faucet       | **Gap** -- add `BUILD_ZERO.md` subsection           | README operational            |
| Port / datadir matrix       | `UpdateZero.md` DOC-02 table (exists)               | `ZERO_COIN.md`                |
| `-nuparams` recipe          | `TEST_ZERO.md`                                      | Zcash regtest book pattern    |
| Coinbase inspection         | `ZERO_COIN.md`                                      | `Zeros/MULTISIG.md`           |
| Zeronode regtest multi-node | **Gap** -- DOC-02 steps -> BUILD_ZERO when scripted | `ZeroNodes.md`                |
| Security / CVE posture      | `ZcashFixes.md`                                     | README Security bullet        |


### Ecosystem testnet instructions (survey Jun 2026)


| Project   | Public testnet docs                                                                                    | Regtest / dev                                                  | Notes                                                                   |
| --------- | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **Zero**  | **Undocumented** public testnet join                                                                   | `TEST_ZERO.md` regtest authoritative                           | Recommend BUILD_ZERO testnet subsection: seeds, `testnet=1`, no harness |
| **Zcash** | [zcash.conf guide](https://zcash.readthedocs.io/en/latest/rtd_pages/zcash_conf_guide.html) `testnet=1` | [Regtest book](https://zcash.github.io/zcash/dev/regtest.html) | Reference upstream only                                                 |


Other clone testnets: `ZKs/Comparison.md`, `ZcashFixes.md` Appendix.

### Suggested testnet doc snippet (for BUILD_ZERO, not yet added)

```bash

```



# Public testnet (operator)

testnet=1
rpcuser=...
rpcpassword=...
addnode=   # document current seeds from chainparams or community
./src/zerod -testnet -daemon
./src/zero-cli -testnet getblockchaininfo

```

Regtest developer path remains **`TEST_ZERO.md` Quick start** and `./contrib/run-tests.sh`.

---

## Mainnet RPC tooling (Jun 2026)

Synced nodes: **Mac** (`~/.zero`) and **laz24** (`ssh lazu`, datadir `/home/ubuntu/.zero`, CLI `/home/ubuntu/Work/ZK/ZeroLinux/src/zero-cli`).

Repeatable coinbase decode and emission stats: **`ZERO_COIN.md`** (Emission totals section).

Cross-reference: **`ZcashFixes.md`**, **`ZebraZero.md`**.

**Orchard assetchain research** (removed from this file): not a Zero port source; use sidecar **`zebrad`** on Zcash per **`ZebraZero.md`**. **Fixed-seed maintainer note** remains under Testnet operator bootstrap below.

---

## Appendix: Wallet decode tools and network bootstrap (Jun 2026)

Planned home for operator tooling survey. Primary maintainer doc: this section; user narrative in **ZERO_COIN.md** Operational reference.

### wallet.zero format

- Berkeley DB **6.2.32** (depends); default filename **`wallet.zero`** (`-wallet=`).
- Schema: [ZIP 400](https://zips.z.cash/zip-0400) lineage (`zkey`, `czkey`, `sapzkey`, `ckey`, ...).
- In-tree recovery: **`zerod -salvagewallet`**, `CWalletDB::Recover()` in `src/wallet/walletdb.cpp`.

### Preferred export (running node)

| RPC | Output |
|-----|--------|
| `dumpwallet <path>` | Transparent WIF + metadata |
| `z_exportwallet <path>` | Shielded key export |
| `z_exportkey` / `z_exportviewingkey` | Per-address |
| `backupwallet <path>` | Binary copy |

### Offline / external tools

| Tool | Zero applicability |
|------|-------------------|
| **`db_dump`** (BDB 6.2.x from depends) | Raw record dump; match depends version |
| **[zmigrate](https://github.com/BlockchainCommons/zmigrate)** | Parses zcashd BDB; encrypted fields not decrypted yet |
| **[Zallet migrate-zcashd-wallet](https://zcash.github.io/wallet/cli/migrate-zcashd-wallet.html)** | Same; `--allow-warnings` for fork chains |
| **pywallet** | Transparent keys only; misses Sprout/Sapling DB keys |

Recipe:

```bash
./src/zero-cli dumpwallet /tmp/zero-export.txt
/path/to/depends/.../db_dump -p ~/.zero/wallet.zero > wallet.dump.txt
```

### Mainnet operator bootstrap

```bash
./zcutil/fetch-params.sh          # or zero-fetch-params
```



# ~/.zero/zero.conf

rpcuser=...
rpcpassword=...
./src/zerod -daemon
./src/zero-cli getblockchaininfo

```

Ports: P2P **23801**, RPC **23811**. Datadir: **`~/.zero`**.

### Testnet operator bootstrap

```bash
testnet=1
```



# P2P 23802, RPC 23812; fee-start height 1

./src/zerod -testnet -daemon
./src/zero-cli -testnet getblockchaininfo

```

Public testnet seeds: **`src/chainparams.cpp`** DNS entries `testnet1.zerocurrency.io`, `testnet2.zerocurrency.io` (verify live peers before relying). No qa harness connects to testnet by design (**TEST_ZERO.md**).

**Fixed-seed gap (maintainer note):** Mainnet uses ten DNS seeds (`seed0`..`seed9`.zerocurrency.io) but **`src/chainparamsseeds.h`** fixed arrays are empty -- no IP fallback if DNS fails (Bitcoin Core ships hardcoded seeds via `contrib/seeds/generate-seeds.py`). Consider resolving `*.zerocurrency.io` and populating `pnSeed6_main` / `pnSeed6_test` on release.

### Regtest (developers)

See **TEST_ZERO.md** Quick start; ports **23803/23813**; Equihash **(48,5)**; fee-start **5000**.

```

