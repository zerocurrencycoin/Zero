# UpdateZero
*Project Planning*

## 1. Documentation map

**Purpose (this file):** Maintainer **execution map** -- fork rules, cherry-pick **decisions and order**, port plans, audits, public-doc drafts pending copy.

**Include:** CON-* rules; Pirate catalog (**3.4**, **5**); TENT catalog (**3.5**); how to pull from those tables (**3.3a**); Linux binary compatibility (**3.6**); Blockbook (**4**); Proton (**6**); drafts (**7**); CSV (**8**); DOC-* audits; RPC test prescriptions. Pointers only to backlog IDs owned elsewhere.

**Exclude:** **checklist / ordered backlog status** (**TODO.md** owns Active / Pending / Ordered next); zerod structure and deep task semantics (**ZeroStruct**); zeronode operator/dev detail (**ZeroNodes**, **ZeroNodeDev**); clone/ecosystem compare (**Comparison.md**); clone paths (**ZKRepos.md**); full org repo audit (**`~/Work/ZK/Repos/ZeroC.md`**); Zebra research (**ZebraZero**).

Developer documents: **this section**.

### Audience and public vs internal

**Branch / merge plan (4.0.1):**

| Class | At **v4.0.1 GA** | Ongoing |
|-------|------------------|---------|
| **Public** | Merge into **`master`** with the release | Stay on the release line; edit via normal PRs |
| **Internal / project** | **Hold back** from the GA merge set | Eventually live on a **separate maintainer branch** (or sibling tree) for continued update without shipping with public docs |

Public set (working): **README**, **BUILD_ZERO**, **TEST_ZERO**, **ZERO_COIN**, **TODO**, **CONTRIBUTING**, **AGENTS**, **doc/man/**. Internal set (working): **UpdateZero**, **ZeroStruct**, **ZeroNodes***, **ExtTests**, **AtHeight**, **ZcashFixes**, **ZebraZero**, **WitnessReindex**, and related project notes. Exact membership of each set can still move until GA.

**Public docs** list readers in **README**; they must **not** href maintainer files (this file, ZeroStruct, ExtTests, ZeroNodes*, ZcashFixes, …).

**Target content rule.** Once a topic is **released** in a public doc, **internal** copies **pare down** to a one-line pointer -- no parallel full body. Thinning internals is intentional after public owns the fact.

**Ubuntu 18.04 / ABI / Insight-host compatibility:** discuss **only in internal/project docs** (**UpdateZero** section **3.6**, Insight specialty tree) until a **resolution timeline vs v4.0.1** is decided. Do **not** expand Ubuntu 18 special-build detail into public BUILD / TEST / TODO / README / ZERO_COIN. Public may say only that **build OS sets the binary floor** (tested on 24.04) without an 18 matrix.

**Audience tiers:**

| Tier | Who | Surfaces |
|------|-----|----------|
| **Public** | Node users, builders, contributors | README, BUILD_ZERO, TEST_ZERO, ZERO_COIN, TODO, CONTRIBUTING, man pages |
| **Internal / project** | Maintainers | UpdateZero, ZeroStruct, ZeroNodes*, **`ZKs/Comparison.md`**, **`ZKs/ZKRepos.md`**, ... |
| **Specialty ops** | At most a few people worldwide (besides the project lead) | **`~/Work/ZK/insight/`** |

**Insight** is specialty. Public docs: short explorer pointer only. Full host conf / bitcore / nginx stay in **`~/Work/ZK/insight/`**. **Skip** Insight/bitcore PR / merge work on the Zero400 track.

**Dev fee / specialty ops (project-internal):** DevFee UTXO labs, drain tooling, and related key inventory stay out of this tree. Do **not** expand DevWallet handling, scripting, or host paths into ZeroStruct, TEST_ZERO, TODO, AtHeight, or other product docs.

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


**Zeronode** guides (**ZeroNodes.md**, **ZeroNodeDev.md**) are maintainer documents today (not in README). Whether any zeronode material later moves public is part of the TBD split above.

### Developer documents


| File                            | Purpose                                               | Include                                                                                                                                     | Exclude                                                                                                |
| ------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **UpdateZero.md**               | Decisions and execution order                         | This map; **3.3a** catalog use; **3.4** PIR; **3.5** TNT; **3.6** Linux compatibility; **4**--**8**                                          | Content owned by other rows                                                                            |
| **ZeroStruct.md**               | **zerod** structures, indexes, caches, locking, algorithms; options by use case | Datadir, LevelDB keys, `-dbcache`, ConnectBlock / wallet paths, client matrices (**§11**), **INT-NN** (**§11.7**) | Status FSM / UI conditions (**StatusTransitions.md**); ecosystem compare (**Comparison.md**); Blockbook port (**4**); zeronode setup (**ZeroNodes**) |
| **StatusTransitions.md**        | Node readiness status contract                        | Behavioral states, RPC codes, wallet conditions, UI presentation maps, diagrams                                  | Structures/algorithms (**ZeroStruct**); wrap checklist (**Wrap401.md** interim) |
| **ZeroNodes.md**                | Run a **zeronode** (operator)                         | Collateral, conf, RPC, sporks, coinbase summary, P2P, **operator-visible reorg**                                                            | ZND / TNT-12 (**ZeroNodeDev** sections **4**--**5**); TNT catalog (**3.5**); family reorg (**Comparison** §14.5) |
| **ZeroNodeDev.md**              | **Zeronode source**                                   | `CZeronodeWalletInterface`; remaining call sites; **ZND** path anchors; **TNT-12** phases                                                   | Operator workflow / operator reorg (**ZeroNodes**); TNT catalog (**3.5**); file map (**TENTZero**)     |
| **~/Work/ZK/ZKs/Comparison.md** | Clone **source** diffs + ecosystem services           | PoW, wallet, P2P, toolchain; **section 12** indexers/explorers/notifications (absorbs former **ZKNodes.md**)                              | Org audit (**Repos/ZeroC**); local paths (**ZKRepos**); zerod how-to (**ZeroStruct**)                   |
| **~/Work/ZK/ZKs/CDBRewrite.md** | `CDB::Rewrite` deadlock across the family              | Spin loop present in Zero / Zclassic / Zcash / Pirate, removed by Bitcoin; per-fork diffs; excluded tests; leave Zero as-is. Task: **IMP-DB-REWRITE-SPIN** (Perf.md)                    |
| **~/Work/ZK/ZKs/ZKRepos.md**    | **Local clone paths** under `ZKs/`                    | Path index, `git pull` loop, Zero400 working copies                                                                                         | Ecosystem compare, org audit, zerod flags                                                                |
| **~/Work/ZK/Repos/ZeroC.md**    | **zerocurrencycoin** org GitHub audit                 | All org repos, mobile/light stack inventory, archive tiers, **`ZeroC.csv`**                                                                 | Local paths (**ZKRepos**); cross-fork indexer compare (**Comparison** section **12**)                   |
| **ZebraZero.md**                | zebrad / YEC / CipherScan reference                   | Sidecar validation, Orchard lessons, YEC fork notes                                                                                         | zerod how-to (**ZeroStruct**)                                                                          |

### Zeronode documents (ZeroNode*)


| File               | Audience                                                                 |
| ------------------ | ------------------------------------------------------------------------ |
| **ZeroNodes.md**   | Operators: `zeronode.conf`, `startalias`, sporks, collateral, deep-reorg exit |
| **ZeroNodeDev.md** | Developers: wallet interface, ZND path anchors (section **4**), TNT-12 phases (section **5**) |
| **TENTZero.md**    | File map only (`~/Work/ZK/ZeroPerf/contrib/perf/TENTZero.md`)                         |




### Cherry-pick ID prefixes


| Prefix  | Section               | Meaning                                                    | Cited in                            |
| ------- | --------------------- | ---------------------------------------------------------- | ----------------------------------- |
| **PIR** | **3.4**, **5** | **P**irate upstream cherry-pick / review candidate      | **UpdateZero** Pirate table |
| **TNT** | **3.5**     | **T**ENT upstream cherry-pick candidate                    | **UpdateZero** TENT table |
| **ZND** | **ZeroNodeDev** **4** | **Z**ero**N**ode **D**ev source-path anchor                | **ZeroNode** files only             |
| **CON** | **2**                 | Zero **consensus** / engineering invariant                 | **UpdateZero** fork rules           |


**TNT** = execution catalog here (section **3.5**). **ZND** = source-path anchors in **ZeroNodeDev** section **4**. Do not cite **ZND-NN** outside **ZeroNode** files. Do not duplicate TNT recommendation rows in ZeroNodeDev or TENTZero.

### Cross-link rules


| Direction                | Rule                                                  |
| ------------------------ | ----------------------------------------------------- |
| Public -> maintainer     | None (no hrefs to UpdateZero / ZeroStruct / ZeroNodes* / DevWallet trees) |
| Public -> DevWallet      | None (no Dev fee scripting or address-ops docs)       |
| Maintainer -> public     | Allowed                                               |
| Maintainer -> maintainer | One-line pointer when another file **owns** the topic |


**Redundancy:** One owner per table or procedure. TNT execution order only here (**3.5**). Reorg **product** decision only **3.5.1**. Reorg **operator** text only **ZeroNodes** section **6**. Reorg **family** table only **Comparison.md** section **14.5**. ZND paths only **ZeroNodeDev** section **4**. TNT-12 phases only **ZeroNodeDev** section **5**. File map only **`~/Work/ZK/ZeroPerf/contrib/perf/TENTZero.md`**. Ecosystem/indexer compare only **Comparison.md** (section **12**). Clone paths only **ZKRepos.md**. Org repo audit only **`Repos/ZeroC.md`**. **zerod** structures/algorithms and per-client requirement matrices only **ZeroStruct.md** (sections **5**, **11**). Node readiness status FSM / conditions / UI maps only **StatusTransitions.md**. Blockbook port and Insight **execution status** only here (**section 4**); do not duplicate full `zero.conf` or RPC catalogs in **4.3** -- pointer only.

**ID namespaces (do not mix):**

| Prefix | Owner | Meaning |
|--------|-------|---------|
| **INT-NN** | **ZeroStruct.md** section **11.7** | Client integration concern (Insight, zerowallet, paths) |
| **C-NN** | **UpdateZero.md** section **8** Completed | Maintainer audit log (fixed items); not **INT-NN** |
| **PIR-NN** / **TNT-NN** | **UpdateZero.md** sections **3.4**, **3.5**, **5** | Cherry-pick candidate or status (not in public TODO) |
| **TST-NN** | **TEST_ZERO.md** | Test task or gate |
| **CON-NN** | **UpdateZero.md** section **2** | Consensus / engineering invariant |

**Topic registry (canonical owner -- one hop max elsewhere):**

| Topic ID | Owner |
|----------|-------|
| **OPS-SHELL** | **BUILD_ZERO.md** section **4.6.1** (shell notify, distributed-build policy) |
| **OPS-EXPLORER** | **BUILD_ZERO.md** section **4.6.2** -- public short pointer only (UI + minimum flags) |
| **OPS-INSIGHT-CONF** | Specialty: **`~/Work/ZK/insight/InsightBlock.md`** section **2.2** + **`config/`** (not a general Zero audience) |
| **OPS-LINUX-ABI** | **UpdateZero.md** section **3.6** (internal; Ubuntu 18 / multi-OS until timeline vs 4.0.1 decided) |
| **OPS-*** / **WAL-*** / **FR-*** / **EXT-*** (status + full task text) | **TODO.md** |
| **OPS-*** / **WAL-*** / **FR-*** (architecture: structures, indexes, algorithms) | **ZeroStruct.md** (esp. §4.3, §6.2, §13) -- problem/pro-con only, not task runbooks |
| **WAL-STATUS-*** / node readiness conditions / UI status map | **StatusTransitions.md** |
| **INT-*** | **ZeroStruct.md** section **11.7** |
| **Clone wallet / P2P / shielding history** | **`ZKs/Comparison.md`** sections **3**, **4** |
| **Indexer / explorer across coins** | **`ZKs/Comparison.md`** section **12** |
| **PIR / TNT execution** | **UpdateZero.md** **3.4** (Pirate) and **3.5** (TENT). How to pull: **3.3a**. Not a separate public TODO list. |

---



## 2. Fork-specific reference

What makes Zero different from upstream Zcash and Bitcoin: consensus parameters, engineering rules, subsidy implementation. New code touching any of these areas must be reviewed against this section.

### Consensus

**Branch id.** Sapling and Cosmos both use `0x7361707a` in `src/consensus/upgrades.cpp`. Duplicate id is documented technical debt until a deliberate NU. See CON-03.

**Zeronode.** `src/zeronode/`* ported from TENT `masternode/*` (see `ZeroNodeDev.md`). Safe iterator order when cleaning expired broadcasts. All `chainActive` dereferences now guarded (audit **C-07**, **C-14** in section **8** Completed -- not **INT-NN**).

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

**Subsidy / founders / zeronode economics (public):** **ZERO_COIN.md** (Emission timeline, Stable arithmetic, Emission totals).

**Implementation touch list (`double` sites):** **BUILD_ZERO.md** §4.8. Integer helper status: **TODO.md**.

**Coverage rule:** miner, `ConnectBlock`, GBT, and metrics must stay in lockstep on any subsidy or founders change; add far-future halving tests when editing.

---



## 3. Build and test notes

Release lifecycle and compiler flags: BUILD_ZERO §2.6-2.7. Source-tree fix log, dependency comparison, and test-porting prescriptions below.

### 3.1 Source-tree build fixes (applied)

Log of fixes on the integration line. Kept so future merges do not revert them. Grouped by area.

**Equihash / `ENABLE_MINING` (open for future consideration).**

Default builds enable mining. `./configure --disable-mining` omits miner code; Equihash **solver** template instantiations in `src/equihash.cpp` for `(192,7)` and `(48,5)` are wrapped in `#ifdef ENABLE_MINING` so the link succeeds without mining objects. Validator paths stay available. `test_miner.cpp` is listed in `zero_gtest_SOURCES` only when `ENABLE_MINING` (`src/Makefile.gtest.include`).

**Why keep the guard:** release or policy builds may ship without a local miner while still validating PoW; without the ifdef, `--disable-mining` fails at link. **Open:** whether to further split solver KATs / gtest from `ENABLE_MINING`, or document a supported `--disable-mining` CI matrix -- not scheduled; do not expand into public BUILD_ZERO beyond "mining on/off is a configure choice."

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



### 3.2 Dependency versions

**Current Zero actuals (versions to build against):** **BUILD_ZERO.md** §4.1 / `depends/packages/*.mk`.

**Ecosystem peer comparisons:** **`~/Work/ZK/ZKs/Comparison.md`** (and related ZKs docs). Zero-specific decisions that are not "what we ship today" stay in this file (e.g. OpenSSL stay-on-1.1.1w until audited, Rust system-default). Do not maintain a parallel peer matrix here.


Verified from `depends/packages/*.mk` in each repo.

### 3.3 Test prescriptions

**Moved to public TEST_ZERO** (commands, maturity **720**, harness changelog, per-script debug, tier inventory). Do not keep a parallel body here.

**Maintainer-only remainder:** when a new port pitfall is *not* yet written into TEST_ZERO, park a one-line note here until copied, then delete. Coverage and open TST-* status: public **TODO.md**.



### 3.3a Upstream catalogs

Pirate (**3.4**, **5**) and TENT (**3.5**) are separate lists. A row sitting in a table is not frozen. **Reject**, **Skip**, and **Keep current** are nos. **Port**, **Review**, **Hold**, **Defer**, and **Implement** compete with Zcash/Bitcoin ports and Zero-local work for the next **TODO.md** Ordered next slot. You pick. Insight/bitcore PRs stay in **`~/Work/ZK/insight/`**, not the node merge set.

**Pirate -- pull from 3.4.** Next node-repo work that is actually a cherry-pick: **PIR-02** (knapsack early exit; existing `wallet_tests`). Then **PIR-05** (addr rate-limit from `bitcoin-src` or Zcash PR 6477). PIR-01 is shipped. PIR-03 leftover is product (WALK-UNLOCK), not a remaining Pirate port. PIR-06--08 is a P2P epic after PIR-05. **WAL-PIRATE-TIMESMART** (`5f0cab6ba`: `nTimeSmart = nTimeReceived`) is an emergency alternate to Zero `wtxOrdered`; it drops arrival-time semantics -- prefer the Zero path (ZeroStruct §13.4).

**TENT -- pull from 3.5.** Next node-repo work: **TNT-12** remainder (phases **ZeroNodeDev** section **5**; C full `startalias` needs 10000 ZER, regtest emission ~3000). **TNT-04**: watch OVERPAY `LogPrintf` / `--zn-pay`; do not port `>=` without hits. TNT-01 is done. TNT-02/03: keep 99 + exit. Do not copy TENT live reorg follow, `SliceHash`, treasury, or obfuscation `ProcessMessage`.

### 3.4 Pirate upstream cherry-pick candidates (2022--2026)

**Status:** This section owns PIR rows and order. Schedule a **Port**/**Review** row when it beats Ordered next. Shipped rows (PIR-01) stay historical. Insight/bitcore PRs: specialty only.

**Repo:** `~/Work/ZK/ZKs/pirate` (`PirateNetwork/pirate`), Komodo assetchain C++ on zcashd lineage -- not a zeronode fork. Releases sampled: v5.5.0 (2022-06), v5.7.0 (2023-06), v5.8.x (2024-03), v5.9.x (2024-09). Recent tip work is mostly build/CI/Komodo merges; portable fixes are scattered single commits.

**Where other Pirate research lives:** Wallet algorithms, RPC controls, hex validation, glossary -> `ZKs/Comparison.md` section **3**. P2P matrix and cross-chain timeline -> `Comparison.md` section **4** (**4.1**). Insight ops -> `~/Work/ZK/insight/README.md`. Orchard CVE posture -> `ZcashFixes.md` Appendix A.1. TENT -> **section 3.5**.

**Cherry-pick rule:** Prefer Zcash upstream when the same fix exists there. Use Pirate as a diff anchor only when it already merged a feature onto a zcashd-shaped tree. Reject Komodo-only consensus (notary seasons, KIP coinbase, `-ac_`*). Wallet consolidation and dust tooling: **section 5** (under review, not rejected outright).

#### 3.4.1 Provenance

Cross-chain history, commit volume, feature dates, wallet RPC matrices, hex validation, and glossary: `ZKs/Comparison.md` section **3** (wallet) and section **4** (P2P; timeline **4.1**). This section keeps **PIR execution only** (table, order, patch shapes).

**Cherry-pick implication.** Portable Pirate fixes for Zero are a small set (PIR-01--05 plus deferred P2P epic PIR-06--08). The 2022 P2P bundle is late Bitcoin Core, not Pirate research. Zcash parallel work was NU/consensus/Rust, not P2P -- port P2P from Core (or Zcash PR 6477 for addr rate limit), using Pirate only as a zcashd-shaped diff anchor.

| ID      | Area                    | Pirate ref                                                                                                                             | Zero status                                                                                                                                         | Recommendation                                                                                                      | Priority       |
| ------- | ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------- |
| PIR-01  | Security                | `d213d7884` (2026-01) `ENABLE_SYSTEM_COMMAND` gate on `runCommand`                                                                     | **Shipped** -- opt-in compile flag; default builds log skip, no **`::system`** (`alert.cpp`, `init.cpp`, `wallet.cpp`)                              | Spec **OPS-SHELL** -> **BUILD_ZERO.md** section **4.6.1**; automation **TST-09** | High           |
| PIR-02  | Wallet / coin selection | Knapsack early exit `nTotalLower > 4*nTargetValue + CENT` (`79383e0a7`, jl777, 2017-10-18 Komodo interest calc)                        | Missing; scans all UTXOs                                                                                                                            | **Port** -- low-risk perf; optional `std::shuffle` as Pirate                                                        | Medium         |
| PIR-03  | Wallet / RPC            | `1f707492f` (2024-03) witness rebuild lockout (`fBuilingWitnessCache`)                                                                 | `initWitnessesBuilt` never cleared on rebuild (**Comparison.md** **3.4**)                                                                           | **Port (adapted)** -- in-progress flag; block `z_sendmany` until complete                                           | Medium         |
| PIR-04  | Policy / relay          | `6fb6a2e2b` (2024-05) `fAcceptDatacarrier` from `-datacarrier`; `IsStandard` rejects oversize or disabled OP_RETURN                    | Partial: `-datacarriersize` in `init.cpp`; size enforced in `Solver()` template match; no global `fAcceptDatacarrier`; Komodo AC size constants N/A | **Port (partial)** -- add `fAcceptDatacarrier` + `IsStandard` NULL_DATA check; keep Zero `MAX_OP_RETURN_RELAY = 80` | Low            |
| PIR-05  | P2P / DoS               | `2bec27973` (2023-03) rate-limit incoming `addr` processing; commit message cites Bitcoin `0d64b8f709` and Zcash `7c739e2b2` (PR 6477) | Not present                                                                                                                                         | **Consider** -- port from `bitcoin-src` or Zcash PR; Pirate is ~2y late backport                                    | Medium         |
| PIR-06  | P2P                     | BIP155 / addrv2 (`50699aba6`, `b5ae39c84`, 2022-05)                                                                                    | Not present                                                                                                                                         | **Defer** -- `Comparison.md` section **4**; port from `bitcoin-src`                                                 | Low (epic)     |
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
| PIR-16  | Insight / explorer      | `insight-api-pirate` tx v5 + Sapling commits (2024)                                                                                    | Zero Insight operational; mainnet [insight.zeromachine.io](https://insight.zeromachine.io/); ops `~/Work/ZK/insight/` | **Separate track** (JS/hosting); Pirate API as optional diff anchor | Medium (infra) |


**Suggested execution order (node repo only):**

1. **PIR-01** -- **shipped**; spec **OPS-SHELL** in **BUILD_ZERO.md** section **4.6.1**; **TST-09** pending.
2. **PIR-02** -- coin selection perf; run existing `wallet_tests` knapsack cases unchanged.
3. **PIR-05** then **PIR-06--08** -- P2P epic; `bitcoin-src` or Zcash PR 6477 for addr rate-limit; tied to fixed-seed work (DOC-02) and `Comparison.md` gap list.
4. **PIR-03 leftover** -- product, not a remaining Pirate port. Remaining: **TST-08** GTest that `z_sendmany` returns **-33** while `fBuildingWitnessCache` is set.

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

#### 3.4.2 PIR-01 (shipped) -- OPS-SHELL

**Owner:** **BUILD_ZERO.md** section **4.6.1** (flags, opt-in rebuild, distributed-release policy, ZMQ alternatives). **Tests:** **TEST_ZERO.md** **TST-09**. Do not duplicate that spec here.

**PIR-03 Zero-specific note:** `BuildWitnessCache` runs from `CWallet::ChainTip` each block (`wallet.cpp` ~623); `initWitnessesBuilt` is never cleared on rebuild. See `ZKs/Comparison.md` section **3.4** for lockout comparison; patch in table above.

### 3.5 TENT upstream cherry-pick candidates (2018--2021)

**Status:** This section owns TNT rows and order. Schedule a **Port**/**Implement**/**Hold** row when it beats Ordered next. **TNT-01** is in tree. Reorg **product** text is **3.5.1**. Zeronode tests: **ZeroNodeDev** section **5**. File map: **`~/Work/ZK/ZeroPerf/contrib/perf/TENTZero.md`**.

**Repo:** `~/Work/ZK/ZKs/TENT` ([TENTOfficial/TENT](https://github.com/TENTOfficial/TENT)). Tip frozen **`bcb429b` (2021-11-13)**. Zero `src/zeronode/`* is a port of TENT `src/masternode*` (wire `mn*` -> `zn*`, treasury removed, `CZeronodeWalletInterface`). TENT is the **direct upstream** for zeronode behavior, not a living vendor.

**Where other TENT research lives:** P2P masternode wire inventory -> `ZKs/Comparison.md` section **4**. File map -> **`~/Work/ZK/ZeroPerf/contrib/perf/TENTZero.md`**. Wallet interface -> **`ZeroNodeDev.md`** sections **1**--**3**. Operator workflow and deep-reorg exit -> **`ZeroNodes.md`**. Family reorg table -> **`Comparison.md`** section **14.5**.

**Cherry-pick rule:** Prefer fixes already landed on Zero's integration line (audit **C-07**, **C-11**, **C-14**, **C-21** in section **8** Completed). Use TENT only where Zero's zeronode fork **regressed** TENT behavior or never picked up a post-port TENT commit. Reject Snowgem/TENT tokenomics (treasury, upgrade-named consensus hooks, Atlantis/Wakanda/Knowhere schedules). Do not copy TENT `SliceHash`, live unbounded reorg follow, or obfuscation `ProcessMessage`.


| ID         | Area                    | TENT ref | Zero status | Recommendation | Priority |
| ---------- | ----------------------- | -------- | ----------- | -------------- | -------- |
| **TNT-01** | P2P / logging | Else-branch dispatch without trailing `Unknown command` log | **Done** -- `main.cpp` ~7070 handlers then return | **Done**. Drop from TODO. | N/A |
| **TNT-02** | Chain / reorg | `6f64bb7` deleted live depth check; live path **follows** unbounded | Zero **exits** at depth **> 99** | **Keep current.** Do not copy TENT follow. **3.5.1** | N/A |
| **TNT-03** | Chain / reorg | `MAX_REORG_LENGTH = COINBASE_MATURITY - 1` | Zero cap **99**; maturity **720** | **Keep 99.** Do not raise toward 719. **3.5.1** | N/A |
| **TNT-04** | Zeronode / payments | `74bbde2` always `>=` (plus Alfheimr-gate removal, not messages-only) | Zero `==`. `LogPrintf` on **overpay** (`>`). | **Hold `>=`.** Watch `debug.log` / `--zn-pay`. **3.5.2** | Low |
| **TNT-05** | Wallet / coin selection | `3915ac3` height-gated `GetCoinbaseProtected` | Static `fCoinbaseMustBeProtected` | **Skip unless** Zero adds height-gated shielding | Low |
| **TNT-06** | RPC / UX | `e3d39f1` (2021-01) prefix "Syncing masternodes list..." (list sync, not "node not synced") | `"Zeronode is not synced..."` + `GetSyncStatus()` already names the asset | **Skip** as a TENT port. Optional 2-line prefix on an RPC UX pass. | N/A |
| **TNT-07** | Consensus / testnet | Min-diff after h13000 | `boost::none` | **Consensus decision** | Low |
| **TNT-08** | Consensus / Equihash | Testnet 144,5 epoch | 192,7 both nets | **Reject** without NU | N/A |
| **TNT-09** | Consensus / PoW | LWMA3 after DIFA | Zcash 17-block window | **Defer** | Low |
| **TNT-10** | Tokenomics | Treasury coinbase | **Removed** | **Reject** | N/A |
| **TNT-11** | Tokenomics | Founders 5 / 7.5 / 15 by upgrade | Fixed **7.5%** after fee-start | **Reject** | N/A |
| **TNT-12** | Testing | No MN integration tests in TENT | Boost A + Python B/C + GTest E in tree | **Implement** on Zero. Phases **ZeroNodeDev.md** section **5**. | Medium |
| **TNT-13** | Docs / ops | External MN setup scripts | Operator guide exists | **Doc** -- **ZeroNodes.md** / BUILD_ZERO when scripted | Medium |
| **TNT-14** | Build | `db81202` libsnark `-march` | Not in Zero `configure.ac` | **Review** if cross-build libsnark fails | Low |
| **TNT-15** | Consensus | Wakanda min block time | TENT-only upgrade | **Skip** | N/A |
| **TNT-16** | RPC product | `*nochange` send RPCs | Absent | **Reject** unless product asks | N/A |
| **TNT-17** | Checkpoints | TENT mainnet checkpoint | Zero's own table | **Skip** | N/A |

This section keeps **TNT** execution order only. Source paths: **ZeroNodeDev.md** section **4**. File map: **`~/Work/ZK/ZeroPerf/contrib/perf/TENTZero.md`**.

**Suggested execution order:**

Witness Cycle 1 (STALE) is **Perf.md**, not TNT.

1. **TNT-12 Phase A** / **TST-03** -- Boost RPC args.
2. **TNT-12 Phase B** -- regtest coinbase / `GetZeronodePayment` with sporks off and injected on.
3. **TNT-12 Phase C** -- two-node `startalias` after A/B.
4. **TNT-04** -- watch overpay `LogPrintf`; `--zn-pay`. Do not port `>=` without hits.

**TNT-01** is done. **TNT-02** / **TNT-03**: keep 99 + exit (**3.5.1**). **TNT-06** is not a port.

#### 3.5.1 Reorg policy

Two constants serve different jobs and must not be conflated:

| Constant | Value | Role |
| -------- | ----- | ---- |
| **`COINBASE_MATURITY`** | **720** blocks | Consensus: coinbase outputs are unspendable until 720 confirmations (`consensus.h`). |
| **`MAX_REORG_LENGTH`** | **`100 - 1` = 99** | Node policy: do not **apply** a reorg/rewind deeper than 99. On breach: modal + **`StartShutdown()`** before `DisconnectTip`. Witness cache size is **`MAX_REORG_LENGTH + 1`** (`wallet.h`). |

**Settled:** keep **99** and the current **exit** posture. Operator text: **`ZeroNodes.md`** section **6**. Family table: **`Comparison.md`** section **14.5**.

**TNT-03:** **Keep 99.** Do not set `MAX_REORG_LENGTH = COINBASE_MATURITY - 1` (719). That would require growing the shielded witness deque in lockstep. Not scheduled.

**TNT-02:** TENT `6f64bb7` follows unbounded live reorgs. Do not copy that. Dropping `StartShutdown()` while still refusing the fork (reject-and-stay) is a different ops choice; **not scheduled**. Catalog row stays for history.

#### 3.5.2 TNT-04 payee amount

TENT `74bbde2` (2019-09, "correct check payee valid") is not a message-only patch. It:

1. Collapsed the Alfheimr height gate: pre-fork **`==`**, post-Alfheimr **`>=`**, then **always `>=`**.
2. Dropped the extra vote-count branch that only ran after Alfheimr.
3. Quieted some `LogPrintf` payee dumps to `LogPrint`.

Zero never had Alfheimr and still requires **`==`**. `GetZeronodePayment` ignores node count in both trees. `>=` would accept **overpay** to the winner script (miner takes less). Underpay fails both. `IsTransactionValid` only enforces when winner signatures exist; **SPORK_8** then decides whether a failed check rejects the block.

Do not port `>=`. Add a **`LogPrintf`** when paid **`>`** required (the case `==` would reject) so live `debug.log` shows whether it occurs without `-debug=zeronode`. Scan: `chain_stats.py --zn-pay`. Sampled windows (tip ~2521664, 2.4M, 1.6M, 0.8M) were all exact vs model.

#### 3.5.3 TNT-06 sync string

TENT `e3d39f1` (2021-01) changed two RPC prefixes from "Masternode is not synced" to "Syncing masternodes list" because the wait is list/asset sync, not chain IBD. Zero still uses "Zeronode is not synced" plus `GetSyncStatus()`, which already names sporks / list / winners / budget. Not a behavior port. Skip unless an RPC copy pass wants the two-line prefix.

---

### 3.6 Linux binary compatibility and release targeting

Maintainer reference for **glibc / libstdc++ floors**, peer distro policy, Insight prod mismatch, and Zero release recommendations. Public build steps stay in **BUILD_ZERO.md**; this section owns **why** and **what to target**.

#### 3.6.1 Guix (Bitcoin)

**Guix** is GNU's functional package manager. Bitcoin Core uses **Guix deterministically build** release binaries inside a pinned Guix environment (`contrib/guix/`, `doc/guix.md` in **bitcoin-src**). Effect:

- Official **bitcoind** Linux binaries are **not** "whatever glibc was on the maintainer laptop."
- Toolchain and **glibc baseline** are fixed in the Guix graph (time-machine pin); symbol versions stay within a chosen minimum (Bitcoin **28.0+** documents **glibc 2.31** minimum for **running** those releases).
- Reproducibility: same inputs -> same outputs across builders.

Zero **does not** ship Guix today. Zero Linux builds use **native `gcc`/`g++`** on the build host + **`depends/`** static third-party libs, but **dynamic** `libc.so.6` and `libstdc++.so.6`. **Build OS = runtime floor** unless you use a container/VM of the oldest target OS.

#### 3.6.2 Bitcoin Core -- Ubuntu 18.04 cutoff

| Release line | Ubuntu 18.04 (glibc 2.27) |
|--------------|---------------------------|
| **27.x and earlier** | Prebuilt **Guix** binaries generally still **ran** on 18.04 (older glibc floor; release notes did not raise minimum before 28). |
| **28.0+** | **Dropped.** Minimum **glibc 2.31** -> **Ubuntu 20.04+** class (18.04 explicitly named in release notes). |

**Last major line with 18.04 viable for official binaries:** **27.x**. **28.0** is the breaking release for 18.04.

Current **bitcoin-src** clone (`~/Work/ZK/ZKs/bitcoin-src`): tag **v30.2** (Jan 2026). Build system is **CMake** + Guix; not comparable to Zero's Autotools path.

#### 3.6.3 Zcash -- platform tiers and timeline

Zcash documents tiers in `doc/book/src/user/platform-support.md` and `doc/dev/platform-tier-policy.md`.

| Tier | Meaning |
|------|---------|
| **Tier 1** | ECC **release binaries** + **tests must pass** after each change. "Guaranteed to work." |
| **Tier 2** | **Release binaries** + **must build**; tests not always run. |
| **Tier 3** | Code **may** work; **no official binaries**; build/test not required. |

**Release notes milestones (Ubuntu-focused):**

| Version | Ubuntu / platform change |
|---------|--------------------------|
| **5.6.0** | **Removed Ubuntu 18.04** from supported platforms (May 2023 EOL; Tier 2 policy). Added **22.04 as Tier 3**. |
| **6.2.0** | **Removed Ubuntu 20.04** (GitHub dropped 20.04 CI runners). **Moved 22.04 to Tier 1.** **24.04 Tier 3** (CI test). |

**Current zcash clone:** **v6.11.0** (Jan 2026). **zcashd** deprecation in progress (zebrad / Zallet); still relevant for comparison.

**Docker / VM:** Zcash docs do **not** mandate either; CI uses GitHub **runner OS images** (now 22.04 Tier 1). Maintainers building for a **minimum OS** use the same pattern as Zero: **build inside that OS** (VM or `docker run ubuntu:22.04`).

#### 3.6.4 Insight prod on Ubuntu 18.04 -- which "pain"?

Separate issues often conflated:

| Pain | Layer | Detail |
|------|-------|--------|
| **A. zerod binary ABI** | **Node binary** | Copying **`zerod` built on Ubuntu 24** to **18.04** fails: **glibc 2.27** and **GCC 7 libstdc++** below symbols from a 24/GCC-13 build (`GLIBC_2.28+`, `GLIBCXX_3.4.26+`). **Cannot be fixed** by config flags on 18; need **18.04-built** binary or **host upgrade**. |
| **B. Insight stack age** | **Node.js / OS** | Prod survey: **Ubuntu 18.04**, **Node 8**, nginx/systemd 237 (`InsightPort.md`, `InsightSystem.md`). EOL stack; upgrade path open -- **independent** of zerod C++ ABI. |
| **C. RAM / `-dbcache`** | **Runtime** | 4 GiB VPS: **`dbcache=4096`** not sustainable; use **~2048** (**ZeroStruct.md** section 4). |
| **D. systemd / nginx** | **Ops** | 237 directive placement, no `proxy_read_timeout` override, journald defaults (`InsightBlock.md` section 4.2). |

**Current maintainer work (24 -> 18 zerod):** falls under **A**. Expected outcome: **failure** until build root matches 18.04 (or prod moves to 22.04+). **`ldd ./zerod`** and **`objdump -T ./zerod | grep GLIBC`** on both hosts to confirm.

**InsightInternal.md** appendix **B.2** tracks **18 vs 24** host migration (survey / parallel 24.04 cutover) -- **B** above, not a substitute for **A**.

#### 3.6.5 Building for old Ubuntu: Docker vs VM

| | **Docker** (`ubuntu:22.04` / `:18.04` image) | **VM** (same OS guest) |
|---|---------------------------------------------|-------------------------|
| **Purpose** | Reproducible **compile** environment | Compile + **systemd** / reboot / full stack test |
| **Speed** | Fast start; bind-mount repo | Heavier setup |
| **`depends/` + Equihash** | Works with `-v $PWD:/work` and volume for ccache | Native I/O |
| **systemd units** | Limited in default container | Full **`zerod.service`** validation |
| **18.04 builder** | Possible but **18.04 is EOL** -- isolated network only | Same caution |
| **Pinning** | Image digest `@sha256:...` | VM snapshot |

**Recommendation:** **Docker** for **release artifact** builds (minimum OS tag); **VM** or **prod-like VPS** once for systemd/Insight integration. Neither replaces **building on the oldest OS you support**.

Example (22.04 floor):

```bash
docker run --rm -v "$PWD:/work" -w /work ubuntu:22.04 bash -lc '
  apt-get update && apt-get install -y build-essential libtool autotools-dev \
    automake pkg-config curl git python3 bsdmainutils
  ./zcutil/fetch-params.sh && ./zcutil/build.sh -j$(nproc)
'
python3 contrib/devtools/symbol-check.py src/zerod src/zero-cli src/zero-tx
```

Tune **`symbol-check.py`** `MAX_VERSIONS` to match the **builder** OS, not 24.04, when gating release binaries.

#### 3.6.6 Pirate (`~/Work/ZK/ZKs/pirate`) -- apt blocks and `build-ubuntu24.sh`

**Clone state (Apr 2026):** checked out **v5.9.1** (Jan 2026); recent tip includes **PIR-01** (`ENABLE_SYSTEM_COMMAND` gate, commit `d213d7884`). Tags **v5.7.x -- v5.9.1**; ~290 commits **v5.8.0..v5.9.1**. Active vs Zero: Komodo-assetchain lineage; releases **2024--2026** while TENT frozen 2021.

**README "apt blocks"** (package lists per distro -- **not** blockchain blocks):

| Block | Extra / different packages |
|-------|----------------------------|
| **18.04** | Base build deps + **gcc-9 / g++-9** via `ubuntu-toolchain-r/test` PPA (`update-alternatives`). 18.04 default GCC too old for modern tree. README marks **18.04 EOL, to be removed**. |
| **20.04** | Standard `build-essential`, `python3-zmq`, `libsodium-dev`, `bison`, ... -- no GCC PPA. |
| **22.04** | Same as 20.04 + **`liblz4-dev`**. |

**Build scripts:** `zcutil/build.sh` and `zcutil/build-ubuntu24.sh` are **functionally identical** (only whitespace at EOF differs). **`build-ubuntu24.sh` is a naming hint** for operators on 24.04, **not** a different configure path, sysroot, or glibc pin. Both run: `make -C depends NO_QT=1` -> `./autogen.sh` -> `CONFIG_SITE=depends/$HOST/share/config.site ./configure ... --with-gui=no` -> `make`.

**Outcome:** Pirate binaries inherit **host glibc/libstdc++** same as Zero. README still documents 18/20/22 **build** deps; **runtime** on 18 requires **building on 18** (or GCC 9 on 18), not copying a 24-built binary.

#### 3.6.7 Peer snapshot (ZKs clones, Apr 2026)

| Project | Clone tag / activity | Linux build model | Notable floor / policy |
|---------|---------------------|-------------------|-------------------------|
| **Bitcoin** | **v30.2** | **Guix** + CMake | Run: **glibc 2.31+** (since 28.0); **no 18.04** |
| **Zcash** | **v6.11.0** | `depends/` + autotools | **Tier 1: 22.04**; 18.04 gone (5.6); 20.04 gone (6.2) |
| **Pirate** | **v5.9.1** (Jan 2026) | `depends/` + autotools; README 18/20/22 apt | Komodo legacy; 18.04 docs stale |
| **Zen** | **v6.0.0** (Jul 2025) | zcash-style `zcutil/build.sh` | Horizen fork; check tag release notes for NU |
| **TENT** | Frozen **~2021** | `depends/` + autotools | README 18/04/20.04 apt; GCC 4.9--7 era |
| **Firo** | Active default branch (Jun 2026 commits) | Bitcoin-derived; own doc set | Separate from zcashd line |
| **Zero** | **zero-400names** / **4.0.x** | `build-native.sh` + `depends/` + **system gcc** | **De facto 24.04** build host; no Guix |

**Suggested Zero updates (from peers, not automatic ports):**

1. **Adopt explicit minimum runtime OS** (recommend **22.04+** to align with Zcash Tier 1 and Bitcoin 28+; **drop 18.04** for new binaries).
2. **Release builder** in **`ubuntu:22.04` Docker** (or lazu VM at 22.04) -- not "compile on 24, deploy to 18."
3. **Retarget `symbol-check.py`** `MAX_VERSIONS` to **22.04** symbols when enforcing release binaries; add CI step on 22.04 builder.
4. **Long-term:** evaluate **Guix** or **static-libstdc++** on old baseline (Guix preferred industry pattern; static glibc **not** viable).
5. **Insight track:** **B.2** host upgrade to **22.04 or 24.04** in parallel with zerod built on same line -- resolves **A** and **B** together.
6. **Pirate `build-ubuntu24.sh`:** do **not** copy blindly -- Zero already has **`build-native.sh`**; if adding **`build-ubuntu22.sh`**, use it as **doc alias** only or parameterize **`MIN_UBUNTU`** in one script.

#### 3.6.8 Rust across Ubuntu 18 -- 24 (Zero)

Zero **`depends/packages/rust.mk`**:

| Mode | When | Rust version |
|------|------|--------------|
| **System Rust** | Default Linux when **`RUST_USE_SYSTEM=1`**; **always on macOS** | Whatever **`which rustc`** returns on build host (e.g. **1.90** on 24.04) |
| **Pinned depends** | **`FORCE_DEPENDS_RUST=1`** (CI / reproducibility) | **1.32.0** tarball |

**By Ubuntu (typical distro packages, not Zero-specific):**

| Ubuntu | Typical `rustc` | Zero build note |
|--------|-----------------|-----------------|
| **18.04** | Often **missing** or very old if `apt install rustc` | Use **`FORCE_DEPENDS_RUST=1`** or manual rustup; system path unreliable |
| **20.04** | **1.41--1.75** (varies with updates) | May work with **`RUST_USE_SYSTEM=1`**; verify `librustzcash` build |
| **22.04** | **1.75+** | Usually sufficient for **`RUST_USE_SYSTEM=1`** |
| **24.04** | **1.75--1.90+** | Current maintainer default |

**Important:** Rust version affects **compile time**, not **`zerod` glibc** on Linux (Rust code links into the binary / `.so` with the same C++ linker). **`RUST_USE_SYSTEM=1` on 24** does not make the binary run on **18**. **`--disable-rust`** (`build.sh --daemon`) avoids Rust for daemon-only builds.

#### 3.6.9 Zero today -- configuration summary

| Aspect | Current behavior |
|--------|------------------|
| **Build entry** | `./zcutil/build.sh` -> **`build-native.sh`** |
| **Depends** | `NO_PROTON=1 make -C depends`; static BDB, Boost, OpenSSL, ... |
| **Linker inputs** | **Dynamic** `libc`, `libstdc++`, `libpthread`, `libm` from **build host** |
| **Compiler** | **`g++ -m64`** from host (`depends/hosts/linux.mk`) |
| **Maintainer host** | **lazu / ZeroLinux** documented as **24.04**; macOS **--strict** PASS (recommended gate, not hard block) |
| **Insight prod** | **18.04** VPS -- **ABI mismatch** with 24-built `zerod` |
| **Check script** | `contrib/devtools/symbol-check.py` capped at **24.04** symbols (does not widen compatibility) |
| **Release packaging** | `zcutil/release-linux.sh` strips; **no** multi-OS matrix |

#### 3.6.10 Ubuntu matrix -- special 18.04 path (internal only)

**Scope:** This subsection is **internal/project** until a **timeline vs v4.0.1 GA** is chosen. Public docs must not grow an 18.04 matrix or special-build how-to in the meantime.

| Ubuntu | Build | Run binary from that OS | Process status |
|--------|-------|-------------------------|----------------|
| **24.04** | Mainline **`./zcutil/build.sh`** (lazu) | Yes on 24+ class hosts | Linux RC checklist (public: recommend rebuild; **`--strict`** maintainer call) |
| **18.04** | **Special path exists:** extra instructions + helper script; **no mainline source modifications** | Yes for binaries built on 18 | **Internal only**; not wired into public TODO / TEST_ZERO / BUILD_ZERO; **timeline vs 4.0.1 TBD** |
| **20.04** | **TBD** | **TBD** | Not claimed |
| **22.04** | **TBD** | **TBD** | Not claimed |

**Hard rule:** a **24-built** `zerod` does **not** run on **18.04**. Use the 18 special build for Insight-class hosts, or upgrade the host -- decision deferred with the timeline above.

**Process debt (internal):** name the 18 script path here or in Insight specialty docs; decide Insight artifacts = 18-built vs host upgrade; only then optionally promote a one-line public note.

#### 3.6.11 Recommendations (Zero 4.0.x line)

**Do not pursue running a Ubuntu 24-built `zerod` on Ubuntu 18** except as a negative test. Paths:

| Priority | Action | Resolves |
|----------|--------|----------|
| **1** | **Decide timeline vs v4.0.1 GA** for Insight host / 18 special path (keep internal until then; no public BUILD/TEST matrix) | Scope |
| **2** | **Decide** Insight track: keep 18-built artifacts **or** upgrade VPS to **22.04+** | Ops |
| **3** | **Validate 20.04 / 22.04** build+run (currently **TBD**) before declaring a minimum runtime OS | Expectations |
| **4** | **v4.0.1:** Linux rebuild on lazu **recommended**; **`--strict`** strongly suggested -- **maintainer decides** tag/merge (**TEST_ZERO.md** §8). Public docs merge at GA; **internal docs held back** (separate branch later) | RC |
| **5** | Optional later: **`ubuntu:22.04` CI** + retarget **`symbol-check.py`** if 22 becomes the floor | Regressions |
| **6** | **Defer Guix** unless dedicated REL item | Wide binaries |
| **7** | BUILD_ZERO keeps a **one-line pointer** to this section; avoid duplicating tables | Single owner |

**Tracked elsewhere:** Insight **18 vs 24** host survey (**InsightInternal.md** B.2); **`dbcache`** on 4 GiB (**ZeroStruct.md** section 4); Linux RC and ops soaks (**TEST_ZERO.md** §8).

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

**DOC-03 -- Reconcile `zero.conf` samples and port defaults (contrib + ZeroWallet).** Medium urgency. Eliminate contradictory examples; stop hardcoding the wrong port class.

*Problem:* Multiple independent `zero.conf` / RPC defaults disagree or use **P2P port as RPC**:

| Source | Role today | Ports / notes |
|--------|------------|---------------|
| `contrib/zero.conf` | Minimal operator sample | `rpcport=23811`; stale `addnode=` IPs remain |
| `contrib/debian/examples/zero.conf` | Debian example | **Fixed** (Zero text, `#rpcport=23811`) |
| `contrib/linearize/example-linearize.cfg` | Linearize RPC client | **Fixed** `port=23811` |
| `contrib/linearize/linearize-hashes.py` | Default if cfg omits `port` | **Fixed** 23811 |
| `contrib/bitrpc/bitrpc.py` | Legacy interactive RPC wrapper | **Fixed** 23811 + Zero prompts |
| `src/rpc/server.cpp` `HelpExampleRpc` | Every RPC help curl line | **Fixed** `http://127.0.0.1:23811/` + `zero.conf` in experimental help |
| ZeroWallet (`zerowalletmac/src/connection.cpp`) | Autogenerates datadir `zero.conf` | `rpcport=23811` **correct**; also sets `txindex`, `deletetx*`, `consolidation*` |

*Port relationship (ecosystem -- no shared formula):*

| Project | Main P2P | Main RPC | RPC vs P2P |
|---------|----------|----------|------------|
| **Zcash** | 8233 | 8232 | RPC = P2P **- 1** |
| **Pirate** | 7770 | 7771 | RPC = P2P **+ 1** |
| **TENT** | 16113 | 16112 | RPC = P2P **- 1** |
| **Zero** | 23801 | 23811 | RPC = P2P **+ 10** (same +10 on test/reg: 23802/12, 23803/13) |

There is **no** `#define` for these numbers. Runtime accessors only: `Params(...).GetDefaultPort()`, `BaseParams().RPCPort()` (set in `chainparams.cpp` / `chainparamsbase.cpp`). Help text today literals numbers (Zcash uses `Params()` for `-port` help but still hardcodes RPC). Pirate `HelpExampleRpc` uses `ASSETCHAINS_RPCPORT` (dynamic); Zcash/TENT/Zero hardcode mainnet RPC in the curl URL.

*Acceptance:*

1. Single canonical **commented** `zero.conf` example under `contrib/` (or `contrib/debian/examples/` as installable copy of the same file). Deprecate or thin the others to a one-line pointer.
2. Align ZeroWallet-generated keys with that sample for the **minimal** set (`server`, `rpcuser`, `rpcpassword`, `rpcport`); wallet-only extras (`deletetx*`, `consolidation*`) documented as wallet policy, not required for bare `zerod`.
3. Replace hardcoded RPC ports in `HelpExampleRpc`, `bitrpc.py`, `linearize-hashes.py` (+ example cfg) with **mainnet RPC default from the same source of truth** (prefer `BaseParams().RPCPort()` in C++; document testnet override). Prefer reading `zero.conf` / `-rpcport` over assuming localhost mainnet.
4. User-facing strings: **Zero** / `zero.conf` / `zerod` -- not Zcash. **Done for** RPC help, `HelpExampleRpc`, privacy blurb product name, debian/bitrpc/linearize samples, miner/timedata logs; see report for `configure.ac` / `ZcashParams` / consensus strings left untouched.
5. Zeronode P2P checks may keep mainnet **23801** but should use `Params(CBaseChainParams::MAIN).GetDefaultPort()` instead of a naked literal.

*Code follow-on (same epic or DEF):* init/cli help for `-port`/`-rpcport` should call `Params(...).GetDefaultPort()` / `BaseParams`/`CreateBaseChainParams` style accessors like Zcash `-port` help, so testnet defaults cannot drift from `chainparams*`.

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

*E. GitHub org repo disposition* (47 repos, reviewed Apr 2026). **Full audit:** **`~/Work/ZK/Repos/ZeroC.md`**, **`ZeroC.csv`**. Summary only:


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
| **Keep public**      | `insight-ui-zero`, `insight-api-zero`, `bitcore-lib-zero`, `bitcore-node-zero`, `zero-pools-insight-explorer`, `bitcore-message-zero` | Insight stack (2026-06); ops `~/Work/ZK/insight/`                  |
| **Keep public**      | `Zero-MiningCore`                                                                                                                 | 4 stars, Equihash 192/7 reference                                        |


*E. GitHub issue suggestions:*

**Issue #70 -- getrawtransaction missing "size" and "fees".** Already acknowledged by maintainer. `size` is straightforward: add `entry.push_back(Pair("size", (int)::GetSerializeSize(tx, SER_NETWORK, PROTOCOL_VERSION)))` in `TxToJSON` / `TxToJSONExpanded` (`src/rpc/rawtransaction.cpp`). `fees` for transparent-only: `sum(vin values) - sum(vout values)`, requires input lookup. For shielded: non-trivial (vpub_old/vpub_new for Sprout, valueBalance for Sapling). Suggest: add `size` now, add `fee` for transparent-only with a `-txindex` requirement, defer shielded fee display. Could be a contributor task.

**Issue #69 -- insight-ui + insight-api.** Infrastructure/hosting request, not a core-node code change. **Address in ops:** mainnet explorer at [insight.zeromachine.io](https://insight.zeromachine.io/); operator detail in `~/Work/ZK/insight/`. Close core-repo issue with pointer to public README/BUILD_ZERO explorer sections.

**Backlog status (OPS-*, WAL-*, FR-*, EXT-*, Ordered next):** **TODO.md** only. Do not keep parallel todo paragraphs here.

**Technical homes (pointers):** reindex / markers / skip-wallet -- **ZeroStruct** §13.2; short-snap resume ops -- **AtHeight.md** §4.1; Pirate DB-knobs -- §13.3; `wtxOrdered` / Pirate timesmart / relation to **`txindex`** -- §13.4 (esp. §13.4.2); LockedPool -- §4.3.2a; bootstrap -- §13.7; founders designs -- §13.8; Insight qa promote -- **ExtTests.md** + TODO **EXT-INSIGHT-*** (five scripts **B pass** 2026-07-22); pure **`txindex.py`** still **Bfail Debug** (**TEST_ZERO**). Operator reindex footgun: **`InsightBlock.md`**.

**Desktop wallet UI tests (out of zerod scope):** Zerowallet (`~/Work/ZK/zerowalletmac`) documents **no automated tests** (`UpdateWallet.md` Gaps). Bitcoin Core has `src/qt/test/`; sampled PirateOcean / safewallet-style Qt trees generally lack an equivalent harness. Track UI automation under the wallet repo, not Zero400.

### Consensus and code (execution notes)

**Supply target vs model:** Product target **some 20M ZER**; piecewise mint can model higher long-run. User-facing schedule and issued totals: **ZERO_COIN.md**. Open review stays on **TODO** (supply discrepancy).

**Stable subsidy arithmetic (accepted):** Integer zats on consensus paths; founders **`subsidy * 75 / 1000`** trunc toward 0 via `GetFoundersRewardAmount`; integer **10.8 ZER** base. **In tree** (not an open implement item). Remaining: **DOC-FR-NAMING**; supply-target review on **TODO**. Reasoning: **ZERO_COIN.md**. Touch list: **BUILD_ZERO.md** §4.8.

**Branch id posture:** Sapling and Cosmos share `0x7361707a`. No planned fork to split. Optional: CI guard for duplicate `nBranchId`.

### Release and infrastructure

**REL-01 -- Release signing.** No checksum or signing procedure yet. **When:** during release prep (tag + package + hash + sign), not after the GitHub Release is live. Unsigned CI artifacts are not releases. Public owner: BUILD_ZERO §2.6. RC recording: TEST_ZERO §8.

**REL-02 -- macOS developer signing.** Apple Developer Program, `codesign` + `xcrun notarytool`. Without it, Gatekeeper quarantine. Same sitting as REL-01 for any macOS artifact that ships.

**REL-03 -- Params archival.** `fetch-params.sh` references upstream Zcash names/mirrors. Audit file names vs `zerod` startup, verify URLs.

**REL-04 -- Chain bootstrap.** Document snapshot sourcing, verification, datadir placement. Currently undocumented. Ops soak (copy / `-loadblock`, never mutate the original): TEST_ZERO §8 OPS-BOOTSTRAP. Packed snaps stay outside git.

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

**TST-01 -- zero_exclusive / experimental scenario coverage.** High importance. **Contributor-ready.**

**Recheck 2026-07-24:** exclusive suite **PASS** including S4 nCount/datatype/watchonly, S5 (`execute` + warmup finish), S6 time+in-flight, S7 shape (`./src/test/test_bitcoin --run_test=rpc_zero_exclusive_tests`). Remaining gap is **mined-tx scenario** depth (Tier B) for History/balances vs `listtransactions`.

*Scope:* Extend the existing Boost.Test files with scenario coverage for each RPC. Each test case should use the `TestingSetup` fixture (wallet + regtest chain) and cover: (a) valid calls with expected return structure, (b) boundary values (empty wallet, zero height, nonexistent address), (c) error paths (invalid address format, out-of-range parameters). RPCs to cover:


| RPC                         | File                              | Current state              |
| --------------------------- | --------------------------------- | -------------------------- |
| `zs_listtransactions`       | `rpc_zero_exclusive_tests.cpp`    | Param count only           |
| `zs_gettransaction`         | same                              | Param count only           |
| `zs_listspentbyaddress`     | same                              | Param count only           |
| `zs_listreceivedbyaddress`  | same                              | Param count only           |
| `zs_listsentbyaddress`      | same                              | Param count only           |
| `getalldata`                | same                              | **Done (exclusive):** S4 nCount/datatype/watchonly, S5 `execute` gate, S6 time+in-flight, S7 shape, W2/W3. **Open:** mined History length / balances scenario (Tier B) |
| `getsupply`                 | same                              | Param count + field check  |
| `getsaplingwitness`         | `rpc_zero_experimental_tests.cpp` | Param count only           |
| `getsaplingwitnessatheight` | same                              | Param count only           |
| `getsaplingblocks`          | same                              | Param count only           |


*How to build and run:* `zcutil/build.sh` (or `build-native.sh`) builds `test_bitcoin`. Run individual suites: `./src/test/test_bitcoin --run_test=rpc_zero_exclusive_tests`. See TEST_ZERO for full instructions.

*Acceptance criteria:* Each RPC has at least 3 test cases (valid, boundary, error). Tests pass under `./contrib/run-tests.sh --strict`. No new dependencies.

*References:* `src/wallet/rpczerowallet.cpp` (RPC implementations), `src/wallet/rpczerowallet.h` (declarations), `src/rpc/client.cpp` (vRPCConvertParams entries), `src/test/rpc_wallet_tests.cpp` (example of existing Boost RPC tests).

**TST-02 -- Parallel Tier A RPC.** Deprioritized. `paymentdisclosure` hang under `--jobs>1`. Serial gate is sufficient.

**TST-03 -- Zeronode / budget subcmd validation.** P1 priority. Write Boost.Test or GTest cases for `zeronodecurrent`, `getzeronodeoutputs`, `startzeronode`, and `znbudget` subcommands. Focus on argument validation and error returns; full integration requires zeronode collateral setup.

**TST-09 -- Shell notify disabled (default build, PIR-01).**

**`-alertnotify` half: PASS / closed** (2026-07-22). Keep **`DeprecationTest.AlertNotify`**: default build accepts the flag and produces **0** side-effect lines (PIR-01 skip; may log `Alert notification skipped:`). No new alertnotify cases. Do **not** require shell-fires parity with Zcash (Zero deliberately gates `::system`). Full **`alert.cpp`** removal = **OPS-ALERT-STRIP** (postponed in **TODO**). P2P `alert_tests.cpp` stays out of **`BITCOIN_TESTS`**.

**Still open:** **`-blocknotify`** and **`-walletnotify`** only -- marker file empty + optional skip log on default build.

*Opt-in parity (manual only):* `ENABLE_SYSTEM_COMMAND` build may assert hooks fire; not a `--strict` gate.

*References:* **`src/init.cpp`**, **`src/wallet/wallet.cpp`**, **`src/alert.cpp`**, **`src/gtest/test_deprecation.cpp`**, **BUILD_ZERO.md** §4.6.1.

**TST-04 -- Zeronode and CDB GTest fixes.** P2 priority. Fix `WalletTests.CachedWitnesses`* (seed `CCoinsViewCache` in harness), fix `CDB::Rewrite` hang (close wallet handle before rewrite or test-only persistence path), unblock `WriteCryptedSaplingZkey*` and `rpc_wallet_encrypted_wallet_sapzkeys`. See §3.3 Debug notes for root cause analysis.

**TST-05 -- Equihash KATs for Zero params only.** **Contributor-ready.**

Supported params: **(192,7)** mainnet/testnet, **(48,5)** regtest. Dispatch in `equihash.h` throws on anything else. Boost `equihash_tests`: genesis header valid + corrupt `nSolution`; `validator_testvectors_192_7` / `_h1` / `_48_5`; `solver_testvectors_48_5` under `ENABLE_MINING`. Files: `src/test/data/1927EQ.txt`, `1927EQ_h1.hex`.

```bash
DUMP_1927EQ=./src/test/data/1927EQ.txt ./src/test/test_bitcoin --run_test=equihash_tests/dump_mainnet_genesis_192_7_indices
contrib/ops-validate.sh equihash
contrib/ops-validate.sh verifyeq
contrib/ops-validate.sh solveeq
```

Header form is `CEquihashInput||nNonce` (`pow.cpp`). Solver cases `#ifdef ENABLE_MINING`; validator always on. Timed (192,7) solve is `ops-validate.sh solveeq` (default one sample; pass N). Regtest `generate` is `ops-validate.sh mine`, not this KAT task.

*Acceptance:* `--run_test=equihash_tests` green; `--strict` green. No algorithm changes.

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

**TST-07 -- Partition and wallet tests.** **Closed (carved).**

| Piece | Script | Status |
|-------|--------|--------|
| Partition | `getchaintips.py` | **Tier A** |
| Wallet backup | `walletbackup.py` | **Tier B pass** (2026-07-22) |

Sapling header root script moved to **TST-SAPLING-ROOT** (`finalsaplingroot.py`, still Bfail) -- see **TODO** Pending.

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

**DEF-06 -- SwiftTX removal.** **Not fitting.** Mainnet **`spork show`**: `SPORK_2_SWIFTTX` and `SPORK_3_SWIFTTX_BLOCK_FILTERING` are **1558907000** (2019-05-26) -- **active**. Budget superblocks remain off (`SPORK_13` / `SPORK_9` = 4070908800). Do not strip `swifttx.cpp` / `ix` / `txlvote` while those sporks are on. Revisit only after a signed spork turns them off (or an explicit NU). Local `if (pwalletMain)` in `ProcessConsensusVote` is still a small cleanup if the file stays.

**DEF-07 -- Reorg bound.** **Settled: 99 + exit.** See **§3.5.1** and **`ZeroNodes.md`** section **6**. TNT-02/03 are not scheduled. Family: **`Comparison.md`** §14.5.

**DEF-08 -- macOS `MACOSX_DEPLOYMENT_TARGET` / libtool `-bind_at_load`.** **Postponed.** Manual **`make`** or **`make check-symbols`** on Darwin without **`MACOSX_DEPLOYMENT_TARGET`** can emit **`ld: warning: -bind_at_load is deprecated on macOS`**. GNU libtool (**`build-aux/ltmain.sh`**) adds **`-Wl,-bind_at_load`** for C++ executable links when **`${MACOSX_DEPLOYMENT_TARGET-10.0}`** matches **`10.[0123]`**; when the env var is unset, the default **`10.0`** incorrectly matches on modern macOS. **`./zcutil/build.sh`** already exports **`MACOSX_DEPLOYMENT_TARGET=15.0`** (same as **`depends/hosts/darwin.mk`** **`OSX_MIN_VERSION=15.0`** and **`-mmacosx-version-min=15.0`** on the compiler). **Workaround:** **`export MACOSX_DEPLOYMENT_TARGET=15.0`** before manual make. **Fix (deferred):** set and export **`MACOSX_DEPLOYMENT_TARGET`** from **`configure.ac`** / top-level **`Makefile.am`** on Darwin so all make invocations inherit it without operator env. Harmless for release; cosmetic linker warning only.

### Reference

**SwiftTX.** Zeronode quorum instant-lock (`SWIFTTX_SIGNATURES_REQUIRED` / `SWIFTTX_SIGNATURES_TOTAL`). **`SPORK_2` / `SPORK_3` are on mainnet** (signed 1558907000). Code: `src/zeronode/swifttx.cpp`, `src/main.cpp`. **DEF-06:** do not remove while those sporks are active.

**Hidden options and CLI inventories.** Options parsed in `src/init.cpp` but not shown in `--help` output. Tracked in `Options.csv` as `*-hidden` category.


| Option              | Default  | Effect                                                                                                  | Disposition     |
| ------------------- | -------- | ------------------------------------------------------------------------------------------------------- | --------------- |
| `-deleteconflicttx` | true     | With `-deletetx`, allow removing conflicted wallet txs (reorgs, double-spends -- not SwiftTX-specific). | Keep            |
| `-enableswifttx`    | true     | Wallet-side SwiftTX lock acceptance.                                                                    | Remove (DEF-06) |
| `-swifttxdepth`     | 5 (0-60) | Virtual confirmation depth for SwiftTX-locked txs.                                                      | Remove (DEF-06) |


**CSV inventories.** `RPCs.csv`, `RPCs_extended.csv`, `Options.csv`, `Options_extended.csv`, `Reindex_Rescan.csv`. Update both base and extended files when adding or removing RPCs, options, or hidden options. The `*-hidden` category in `Options.csv` tracks undocumented options listed above.

**Test exclusions.** Default pass-only filters, reasons, and mitigation directions: TEST_ZERO §Known failures.

### Completed (maintainer audit log -- prefix **C-NN**, not **INT-NN**)

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

Daemon / indexer ecosystem compare: `~/Work/ZK/ZKs/Comparison.md` section **12**. Blockbook port detail stays in this section **4** only. **zerod** structure and use-case options: `ZeroStruct.md`.

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

**Local clone provenance.** Trezor Blockbook: **`~/Work/ZK/ZKs/blockbook/`** (canonical upstream; was under a nested insight path). `zerocurrencycoin/blockbook` is a **2020 fork** (abandoned). LBE (hellcatz / ondrejsika): lightweight RPC-only reference -- re-clone under **`ZKs/`** if needed; not co-located with **`~/Work/ZK/insight/`**.

**Self-hostable explorer alternatives** (Blockbook in context):


| Explorer                                                                                          | Stack                         | Multi-coin                           | Fit for Zero                                                                                                                                            |
| ------------------------------------------------------------------------------------------------- | ----------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Blockbook (Trezor)**                                                                            | Go + RocksDB                  | Yes (many, incl. Zcash forks)        | **Best long-term**; postponed per direction (detail above).                                                                                             |
| Iquidus Explorer                                                                                  | Node.js + MongoDB             | One coin/instance, re-skinnable      | Proven on Zcash forks (Hush runs it); DB-backed; viable fallback.                                                                                       |
| LBE (hellcatz, fork of ondrejsika/lbe)                                                            | Python/Flask, RPC-only, no DB | Yes; explicitly Zcash/equihash forks | Lightweight; needs only `getblock`/`getrawtransaction`/`decoderawtransaction`; **lacks rich address indexing** → reference/fallback, not a replacement. |
| btc-rpc-explorer                                                                                  | Node.js, RPC-only             | Bitcoin-likes                        | Weak fit (not shielded-aware).                                                                                                                          |
| Hosted aggregators (Blockchair, Tokenview, blockexplorer.one, chainz.cryptoid, Foundry zcashinfo) | SaaS                          | Yes                                  | Reference UIs; not self-hostable.                                                                                                                       |




### 4.3 Insight / Bitcore

**Ops and host runbooks:** **`~/Work/ZK/insight/`** only (README, InsightBlock, config/).

**zerod flags (public, current):** **BUILD_ZERO.md** §4.6.2. Do not duplicate Insight install/nginx/bitcore procedure here.

**Zero decision:** keep Insight operational for mainnet UI; Blockbook remains a separate postponed infra track (**4.1**). Explorer-host PRs stay in **`~/Work/ZK/insight/`**.

### 4.4 Indexer approach pointer

Cross-fork indexing strategies: **`~/Work/ZK/ZKs/Comparison.md`** section **12**. Zero emission tooling: `contrib/stats/*` (see **ZERO_COIN.md**).

---



## 5. Pirate wallet features under review

**Status:** Pirate wallet review. Same queue as **3.4**; pull a row when it beats Ordered next.

**Repo:** `~/Work/ZK/ZKs/pirate`. Portable wallet ops only -- not Komodo consensus, notary, or KIP coinbase (**PIR-14 reject**). Wallet vs consolidation on-chain behavior: `ZeroStruct.md` **section 8**.

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

**Public docs do not link** to maintainer files (**UpdateZero.md**, **ZeroStruct.md**, **Comparison.md**, etc.). When a draft below is approved, **copy the markdown block** into the target public file without adding maintainer hrefs.

### 7.0 Draft backlog


| Target            | Draft                                             | Status                                                                    | Maintainer source (do not link from public) |
| ----------------- | ------------------------------------------------- | ------------------------------------------------------------------------- | ------------------------------------------- |
| **ZERO_COIN.md**  | **7.1** dev balances (insight)                    | Ready                                                                     | `contrib/stats/chain_stats.py`              |
| **ZERO_COIN.md**  | **7.2** supply vs UTXO                            | Ready                                                                     | **ZeroStruct** use cases                    |
| **ZERO_COIN.md**  | **7.7** zeronode boundary (economics vs setup)    | Ready                                                                     | **ZeroNodes** operator detail               |
| **BUILD_ZERO.md** | **7.3** explorer node flags                       | **Transitioned** -- BUILD_ZERO §4.6.2 + `~/Work/ZK/insight/` (draft body removed) | Insight specialty |
| **BUILD_ZERO.md** | **7.6** REST                                      | Ready                                                                     | **ZeroStruct** REST row                     |
| **BUILD_ZERO.md** | **7.8** public testnet join                       | Ready                                                                     | DOC-02 / testnet seeds                      |
| **BUILD_ZERO.md** | **7.9** zeronode operator (optional)              | **Deferred** -- keep in **ZeroNodes** until product approves public steps | **ZeroNodes**                               |
| **README.md**     | **7.4** node vs wallet scope                      | Copied / verify in README                                                 | --                                          |
| **Insight ops**   | **7.5** flag bundle                               | **Transitioned** -- insight README + BUILD_ZERO §4.6.2 (draft body removed) | `~/Work/ZK/insight/` |
| **ZERO_COIN.md**  | Port/datadir matrix excerpt from DOC-02           | **Gap**                                                                   | **UpdateZero** DOC-02 table                 |
| **BUILD_ZERO.md** | `-blocknotify` / `ENABLE_SYSTEM_COMMAND` (PIR-01) | Ready (**4.6.1** **OPS-SHELL**)                                        | **UpdateZero** **3.4.2**                    |
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



### 7.3 / 7.5 Explorer drafts -- removed

Content transitioned: **BUILD_ZERO.md** §4.6.2 (`zerod` flags, dbcache, reindex, RPC 23811); host procedure and addressindex RPC list in **`~/Work/ZK/insight/`**. No parallel draft body here.

### 7.4 README.md -- node vs wallet scope

```markdown
This repository builds the full node (zerod, zero-cli, zero-tx). The Qt wallet (zerowallet) is a separate application and does not enable blockchain address indexes by default.
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
| Pirate index config | separate `addressindex=1` lines | Same RPCs; config style differs (**`Comparison.md`** section **12**) |

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

Outline for remaining zeronode doc gaps. **TNT catalog:** section **3.5**. **TNT-12 phases:** `ZeroNodeDev.md` section **5** only (do not duplicate that table here). **Operator reorg:** `ZeroNodes.md` section **6**. **File map:** `~/Work/ZK/ZeroPerf/contrib/perf/TENTZero.md`.

### Documentation deliverables

| Step | Deliverable              | Target doc                                                     | Content                                                                           |
| ---- | ------------------------ | -------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| 1    | **Operator runbook**     | `BUILD_ZERO.md` new subsection or README link                  | Build, `fetch-params`, `zero.conf` RPC creds, `zerod` launch, ports (23801/23811) |
| 2    | **Zeronode setup**       | Replace obsolete wiki / `ZeroNodes-UpdatesPending` script refs | Collateral 10k ZER, `zeronode.conf` -- see `ZeroNodes.md`                         |
| 3    | **Economics cross-link** | `ZERO_COIN.md`                                                 | Coinbase 3-way split, emission tables, `chain_stats.py`                           |
| 4    | **Wallet boundary**      | `ZeroNodeDev.md` + `ZeroNodes.md`                              | Dev interface vs operator workflow                                                |
| 5    | **Security pointer**     | `ZcashFixes.md` + ZERO_COIN Security                           | Sapling-only, no Orchard, Sprout CVE N/A                                          |
| 6    | **Multisig founders**    | `Zeros/MULTISIG.md` appendix                                   | Done Jun 2026                                                                     |


### Functional tests

**TNT-12** / **TST-03** phases A-F, complexity, and sequence: **`ZeroNodeDev.md`** section **5**. DOC steps 1-2 can ride with phase A.

---

## Testnet and regtest: usage, gaps, documentation placement

### Zero networks (from code + TEST_ZERO.md)


| Network     | P2P   | RPC   | Equihash | Fee-start    | Harness use                       |
| ----------- | ----- | ----- | -------- | ------------ | --------------------------------- |
| **mainnet** | 23801 | 23811 | 192,7    | block 412300 | Manual ops only; **no CI**        |
| **testnet** | 23802 | 23812 | 192,7    | block 1      | **Not used** by qa harness        |
| **regtest** | 23803 | 23813 | 48,5     | block 1000 (off 1500) | **All** automated RPC/Boost tests |


**Regtest notes:**

- `-regtest=1`; mine with `generate` / `generatetoaddress` (not `setgenerate` on testnet -- `fMiningRequiresPeers`).
- NU activation: `-nuparams=<branchHex>:<height>` (see `TEST_ZERO.md`, `util.py` `NU_TEST_ARGS`).
- Frozen cache tip **725** (`COINBASE_MATURITY` 720 + 5) for fast wallet tests.
- Public testnet: no min-difficulty rule on Zero (**TNT-07**; ZND-02 path in **ZeroNodeDev.md** section **4**).

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


---

### wallet.zero format ***

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

### External tools ***

| Tool | Zero applicability |
|------|-------------------|
| **`db_dump`** (BDB 6.2.x from depends) | Raw record dump; match depends version |
| **[zmigrate](https://github.com/BlockchainCommons/zmigrate)** | Parses zcashd BDB; encrypted fields not decrypted yet |
| **[Zallet migrate-zcashd-wallet](https://zcash.github.io/wallet/cli/migrate-zcashd-wallet.html)** | Same; `--allow-warnings` for fork chains |
| **pywallet** | Transparent keys only; misses Sprout/Sapling DB keys |

```bash
./src/zero-cli dumpwallet /tmp/zero-export.txt
/path/to/depends/.../db_dump -p ~/.zero/wallet.zero > wallet.dump.txt
```

*** Move to README or CONTRIB

### Mainnet user
P2P ports **23801**, RPC **23811**. Datadir on Linux: **`~/.zero`**.

```bash
./zcutil/fetch-params.sh          # or zero-fetch-params

# ~/.zero/zero.conf

rpcuser={USER}
rpcpassword={PASSWORD}
./src/zerod -daemon
./src/zero-cli getblockchaininfo
```
**Fixed-seed gap:** Mainnet uses ten DNS seeds (`seed0`..`seed9`.zerocurrency.io) but **`src/chainparamsseeds.h`** arrays are empty -- no IP fallback if DNS fails (Bitcoin Core ships hardcoded URLs generated via `contrib/seeds/generate-seeds.py`). Consider resolving `*.zerocurrency.io`.
Public testnet seeds: **`src/chainparams.cpp`** DNS entries `testnet1.zerocurrency.io`, `testnet2.zerocurrency.io` (verify live peers before relying). No qa harness connects to testnet by design (**TEST_ZERO.md**).

### Testnet operator
P2P ports 23802, RPC 23812

```bash
# ~/.zero/zero.conf

testnet=1
rpcuser={USER}
rpcpassword={PASSWORD}
addnode=

./src/zerod -testnet -daemon
./src/zero-cli -testnet getblockchaininfo
```

### Regtest developer
P2P ports 23803, RPC 23813
Equihash **(48,5)**
**`REGTEST_FOUNDERS_START`/`STOP`** = **1000**/**1500**.

---

## DOC-BUILD-INTAKE (from public BUILD_ZERO scrub)

Maintainer-only material removed from **BUILD_ZERO.md** so the public build guide has no host names, absolute paths, insight install, or unfinished proposals.

### Remote Linux build host notes

Keep Linux release validation on a **generic** Ubuntu-class builder (2+ cores, several GB free). Steps: fetch release line, `./zcutil/fetch-params.sh`, `./zcutil/build.sh`, `./contrib/run-tests.sh --strict`. Optional widen: `--suite` (ELF stages). Darwin skips ELF release checks; `rpcbind_test` may be reduced on some hosts. `--strict` is a gate signal, not an automatic release block.

### Compiler / release flag proposals (not public)

(1) Gate `-g` behind `ZERO_DEBUG=1`. (2) Evaluate `-O2` for release. (3) Decouple `CXXFLAGS_overridden` from bare `-g`. (4) Integrate `split-debug.sh` for `-dbg` package.

### Insight / explorer backend (specialty; not in BUILD_ZERO)

Public UI: insight.zeromachine.io. Backend flags for a transparent index node: `experimentalfeatures=1`, `insightexplorer=1`, `txindex=1`; large `dbcache`; first enable needs `-reindex`. Host install (nginx, bitcore, sizing) stays in the specialty insight tree -- never path-cite it from public docs.

### Subsidy arithmetic touch list (implementation)

Schedule: **ZERO_COIN.md**. Status: **TODO.md**. Convert `double` mixes at approximately:

| File | Notes |
|------|--------|
| `src/main.cpp` | `GetBlockSubsidy` `10`/`10.8 * COIN`; founders `* 0.075` |
| `src/zeronode/payments.cpp` / `budget.cpp` | `* 7.5 / 100` |
| `src/rpc/mining.cpp` / `zeronode.cpp` | `getblocksubsidy` / founders |
| `src/metrics.cpp` | UI immature totals |
| `src/test/main_tests.cpp` / `rpc_wallet_tests.cpp` | expectations |

Good pattern: `GetZeronodePayment` integer percent.

### Disk reclaim on small build hosts

Safe: apt lists/clean, ccache, `depends/work/*`, repo `cache/`, MXE pkg/log under `$HOME/mxe`, journal vacuum. Do not document personal `~/Work/...` trees in public docs.

---

## DOC-TEST-INTAKE (from TEST_ZERO deep reference)

Public **TEST_ZERO.md** keeps use cases, inventory, and interpreting results only.

Moved / retained in **ExtTests.md**:

- Promote-vs-verify rule (pass alone != in gate until array+CSV+§3 update)
- Maturity / clean-chain porting notes
- CachedWitnessesCleanIndex / Equihash / external-interface current state
- Cache dir and `--jobs` standing notes

Dated process diaries, RC handoffs, host disk stats, and verification snapshots stay out of public TEST_ZERO. Prefer ExtTests or this hub for narrative.

---

## DOC-TODO-INTAKE (stripped from public TODO)

Items removed from public **TODO.md** (wrong audience or external product):

- Wrap / StatusTransitions / Wrap401 stamp gates
- Zerowallet UI / QTest / soft-path / ADDRKEY client work
- Perf sibling tree / debug.log campaign process
- README0 merge chore (done via README rewrite)
- Host-named Linux RC checklists
- DevFee / specialty ops pointers

Keep engineering detail for those topics here or in ZeroStruct / ExtTests as appropriate -- not in the ship set.

### DOC-FR-NAMING / FR-* (moved from public TODO)

Product / naming options -- not scheduled on the public checklist:

- **DOC-FR-NAMING** -- reconcile `vFoundersReward` / FoundersReward / `developmentfee` / GBT `founders` strings across code and ZERO_COIN.
- **FR-ROTATE / FR-TADDR / FR-Z** -- founders destination product/consensus options (rotate policy, transparent vs shielded). Not a node release gate.

### REL-SIGNING (moved from public TODO)

**Status:** Active maintainer work. Public **BUILD_ZERO** §2.6 now requires checksums/signatures during release prep; the operator verify procedure is still unpublished.

**When:** during release prep, before publishing the GitHub Release. TEST_ZERO §8 RC bar records hashes/signatures as present or explicitly missing.

**Minimum viable (all platforms):**

| Platform | Artifact check | Signing |
|----------|----------------|---------|
| **Linux** | `SHA256SUMS` (or `SHA256SUMS.asc`) listing release tarball/deb hashes | Detached **GPG** signature over the sums file; publish key fingerprint with releases |
| **macOS** | Same hash list for `.tar.gz` / `.dmg` if shipped | **Developer ID** application signing + **notarization** (stapler) for distributable binaries |
| **Windows** | Same hash list for `.zip` / installer | **Authenticode** (OV or EV) on `zerod.exe` / installer |

**Also document when ready:** where keys live, who signs, how operators verify (`gpg --verify`, `sha256sum -c`, macOS `spctl` / notarization ticket, Windows sig check), and that unsigned CI artifacts are not releases.

**Out of scope for this item alone:** Guix/reproducible builds (separate if pursued); desktop-wallet signing (other repos).

When the procedure is ready, copy operator-facing verify steps into **BUILD_ZERO** (no maintainer IDs).

---

## DOC-UNICODE: non-ASCII policy and audit

**Local to ZeroPerf.** Zero400 `src/` is left as-is; this section records what is
there, what is deliberate, and what the checker tolerates.

**Rule (AGENTS.md):** no emojis or decorative Unicode in any document except
`README.md`; use ASCII -- `--` not em-dash, `->` not arrow, `"` not curly
quotes, `...` not ellipsis. Nothing enforced it, so violations accumulated.

**Checker:** `contrib/perf/check-unicode.py` (report; `--fix` for safe
substitutions; `--all` to include tolerated; exit 1 on violations). Its own
substitution table is written with `\uXXXX` escapes so the tool is self-clean.

### Settings

| Setting | Contents | Why |
|---------|----------|-----|
| `REPLACE` | em/en dash, both arrows, curly single and double quotes, ellipsis, middle dot, bullet, multiplication sign, almost-equal, NBSP, narrow NBSP | Exact ASCII equivalent exists; `--fix` rewrites these |
| `FLAG_ONLY_RANGES` | emoji and pictographs (U+1F300-1FAFF), misc symbols and dingbats (U+2600-27BF, includes the check mark), variation selectors | No safe ASCII equivalent; reported for a human, never auto-rewritten |
| `TOLERATED` | section sign U+00A7 | 468 of 694 tree-wide hits; conventional section notation in the perf docs, not decoration. `--all` reports it anyway |
| `SKIP_PATH` | `src/{leveldb,univalue,secp256k1,snark,crypto/ctaes}`, `depends/`, `contrib/perf/{mine,groth16-batch-poc}/`, `contrib/perf/dis-nodes.txt`, `share/genbuild.sh` | Vendored source and captured data. Captures preserve what was captured; normalizing them would corrupt the record |
| `EXEMPT` | `README.md` (any directory) | AGENTS.md exempts it explicitly |

### Zero400 `src/` -- keep as is

Three classes, none changed:

| Class | Sites | Disposition |
|-------|-------|-------------|
| **Mathematical / spec notation** | `zcash/JoinSplit.hpp` 19-21 `pi_A/pi_B/pi_C` as Groth16 proof elements; `consensus/params.cpp:37` Z-notation `:` from ZIP-208; `wallet/gtest/test_wallet.cpp:2336` "identical to" | **Keep.** Ties the code to the protocol spec; ASCII substitutes lose that |
| **Quoted data** | `wallet/paymentdisclosure.h:27` -- the ISO-8859-1 rendering of byte `0xFF` | **Keep.** Rewriting makes the comment factually wrong |
| **Curly apostrophes** (U+2019) | `crypto/equihash.cpp:12` (NDSS '16 citation); `wallet/rpcwallet.cpp` 4156 / 4164 | **Keep for now, inherited.** Both `rpcwallet.cpp` strings are verbatim Zcash (`zcash/src/wallet/rpcwallet.cpp` 5104 / 5112). Note these are **RPC help text**, not comments: they reach operator terminals |

Also present and unchanged: `wallet/db.cpp:394` arrow in a commented-out debug
line, and `qa/rpc-tests/addressindex.py:111` section sign in a doc reference.

### Perf scripts -- doc references struck

`contrib/perf/*.sh` and `*.py` previously carried `Perf.md SS N` pointers in
comments. Struck; the substance was kept inline where it mattered (for example
"bound by timestamp, not by searching for a height substring: `height=937` also
matches `height=937237`"). Rationale: shipped code should not href maintainer
documents (see the public-docs rule above), and section numbers decay --
`src/wallet/gtest/test_wallet_zkeys.cpp:406` still cites **UpdateTests.md**,
retired some time ago with its core content moved into `TEST_ZERO.md` and the
remainder consolidated here.

### Upstream comparison

Neither upstream enforces ASCII in source, and both carry non-ASCII:

| Tree | Files with non-ASCII in `src/` | Most common |
|------|-------------------------------|-------------|
| **Zcash** | 23 | U+2019 curly apostrophe (54), variation selector + keycap (57, emoji sequences), curly double quotes (32) |
| **Bitcoin Core** | 43 | box drawing (approx. 440 across 6 glyphs), ellipsis (81), curly apostrophe (18), em dash (11) |

Bitcoin has `test/lint/` (16 linters) and Zcash `test/lint/` (13); **neither
includes an ASCII or Unicode check**. Zcash's `lint-whitespace.sh` covers
trailing whitespace and tabs only. So Zero's rule is stricter than either
upstream -- which is a defensible local choice, but it means inherited code will
keep arriving with non-ASCII, and a blanket `--fix` over `src/` would create
diff noise against upstream for no functional gain.
