# TODO

Status, planning, and full work-item descriptions for the Zero full node.

Public docs (README, BUILD_ZERO, TEST_ZERO, ZERO_COIN, this file, CONTRIBUTING, AGENTS, man) do not link to maintainer-only files or to DevWallet address/scripting trees.

---

## Protocols, labels, and naming

| Prefix / label | Meaning | Status home |
|----------------|---------|-------------|
| **CON-NN** | Consensus / engineering invariant | Full text below |
| **WAL-*** | Wallet / RPC work | Lists below + full text here |
| **OPS-*** | Ops / DB / reindex / notify | Lists below + full text here |
| **FR-*** | Founders reward product/consensus options | Lists below; designs in maintainer architecture docs |
| **EXT-*** | Ext / Insight harness | Lists below |
| **TST-NN** | Test / gate work | Commands in TEST_ZERO; status + full text here |
| **S4--S8**, **W1--W6** | `getalldata` / soft-RPC slice IDs | Full text here |
| **Assure-4** | `wtxOrdered` ≡ `mapWallet` after erase | Done with WAL-WTXORDERED |

**Naming notes**

- **`listtransactions.py`** (qa): Bitcoin Core 2014 Python regression name; exercises the **`listtransactions` RPC**. Unrelated to the JSON field **`listtransactions`** inside **`getalldata`** responses. Origin commit on this line: `561bd561f` (2014-02-26, "Python-based regression tests"); header still says "Exercise the listtransactions API".
- **`getalldata` History field** is also named `listtransactions` (array of arc-tx objects). Do not conflate with the thin RPC or the qa script.
- **`vFoundersReward` / FoundersReward / developmentfee`**: code vs product string; reconcile under **DOC-FR-NAMING** (postponed).
- **Dev fee addresses**: project-internal only (private address tree). Not documented in public node docs.

---

## Ordered next (execution priority)

1. ~~**WAL-WTXORDERED** (+ Assure-4)~~ -- **done** (incremental `wtxOrdered`, keep accounts/`TxPair`). Line-by-line Zcash type match **deprioritized** (see **WAL-RPC-ACCOUNTS**, postponed).
2. ~~**Stable subsidy arithmetic**~~ -- **done** in-tree (`GetFoundersRewardAmount` / integer `GetBlockSubsidy`); naming later (**DOC-FR-NAMING**).
3. **WAL-GETALLDATA-W5** -- **revisit soon** (stashed on Zerowallet; pro/con below).
4. **TST-01** remainder / **TST-05** / **TST-03** -- harness gaps. **TST-09** alert half done; block/wallet notify open. **getalldata_scenario** Ext-validated (2026-07-24).
5. Postponed bucket (see Pending): **WAL-LOCKEDPOOL**, **OPS-CACHE-METRICS**, **OPS-TXINDEX-DEFAULT**, **OPS-AT-HEIGHT**, **TST-WITNESS-REINDEX**, **OPS-REINDEX** remainder, **OPS-ALERT-STRIP**, **DOC-FR-NAMING**, other getalldata W-items / ARG2 / UI window.
6. **FR-ROTATE / FR-TADDR / FR-Z** -- product/consensus. Not scheduled.
7. **WAL-RPC-ACCOUNTS** -- **postponed**; business decision + code-risk analysis. Not a gate for continuing const / getalldata work.
8. Release / docs track -- README merge, signing, macOS notarization, Linux RC, supply review.

---

## Active

- README rewrite: merge README0.md in
- Node setup and maintenance docs: validate user-facing instructions
- Release signing: checksum and signing procedure
- Chain bootstrap: end-user import path (`-loadblock` / auto-import); linearize tool in `contrib/linearize/`
- macOS developer signing (codesign + notarization)
- Total supply discrepancy: arithmetic vs ~20M ZER target
- ~~**Stable subsidy arithmetic**~~ -- **done** (helper + tests); keep ZERO_COIN as normative description
- RPC coverage matrix: `RPCs.csv` (`zero=y`) vs harness depth + client grep -> `RPCs_extended.csv` / `RPC_coverage.csv`
- **TST-01** -- exclusive getalldata gates and Ext `getalldata_scenario` are **working**; under development: `getsupply` / `zs_*` / sapling depth. Run: `./src/test/test_bitcoin --run_test=rpc_zero_exclusive_tests` ; `./qa/pull-tester/rpc-tests.sh getalldata_scenario`
- **TST-03** -- `zeronodestats` + zeronode/budget subcmds; arg validation first (under development)
- **TST-05** -- wire genesis (192,7) indices from `1927EQ.txt` + (48,5) KATs (under development)
- **TST-09** -- **done** (alert + block + wallet notify default-build skip markers in `DeprecationTest`)
- **WAL-GETALLDATA-W5** -- **revisit soon** (see Full descriptions)
- macOS datadir: wallet should use `Application Support/zero/` (INT-01)
- Fuzz harness setup

## Pending

- OPS-REINDEX remainder -- refuse / `-reindexforce`; SKIP-wallet below H
- OPS-ALERT-STRIP -- gut P2P `alert.cpp` after TST-09 slim
- DOC-FR-NAMING -- FoundersReward vs developmentfee naming
- TST-SAPLING-ROOT -- `finalsaplingroot.py` Bfail
- TST-WITNESS-REINDEX -- hub WitnessReindex.md; B1 `reindex_shielded.py` in Tier B pass; CleanIndex B2/C postponed
- OPS-CACHE-METRICS -- tunable insight split + hit/miss
- **WAL-GETALLDATA-CACHE (W6)** -- postponed; prefer after W5
- **WAL-GETALLDATA-W1** -- postponed; after current slew validated
- **WAL-GETALLDATA-W4** -- postponed; IVK decrypt review
- **WAL-GETALLDATA-ARG2-DEFAULT** -- postponed; justified default **2** (7d) -- see Full descriptions
- **WAL-UI-TX-WINDOW** -- postponed; Zerowallet History day control
- **WAL-QT-UI-TEST** -- postponed; no QTest/CI UI suite; manual soft-path checks only
- **WAL-GETALLDATA-HELPERS** -- C++ getalldata helpers still pending; Python **`assert_raises_message`** shipped in `util.py` (2026-07-24)
- **WAL-GETALLDATA-ADDRKEY** -- **Zerowallet / out of Zero400 scope**; finding kept in ZeroStruct §6.2 (no node prototype here)
- **WAL-GETALLDATA-LEGACY-SCOPE** -- which 2018--2020 surface can shrink (see Full descriptions)
- **WAL-RPC-ACCOUNTS** -- **postponed** (see Full descriptions); line-by-line Zcash `wtxOrdered` type match stays with this item
- OPS-TXINDEX-DEFAULT / OPS-AT-HEIGHT -- postponed
- EXT-INSIGHT-SUPERSET -- postponed
- `txindex.py` -- Bfail Debug; promote after green
- FR-ROTATE / FR-TADDR / FR-Z -- postponed
- v4.0.1 Linux RC (lazu) -- see TEST_ZERO 4.0.1 handoff
- P2P logging (`Unknown command` after zn dispatch) -- postponed (zeronode extension path)
- macOS libtool `-bind_at_load` -- export `MACOSX_DEPLOYMENT_TARGET=15.0` from build system
- Params archival / Windows hardening / branch-id CI / OpenSSL 3 / SwiftTX strip / release branch cleanup / Debian packaging / GitHub org cleanup

## Completed (selected)

### Founders window / wallet.py (2026-07-24)

- Regtest **`REGTEST_FOUNDERS_START`/`STOP`** = 1000/1500; **`founders_window.py`** Tier B (subsidy, shape, GBT, Insight founders balance).
- Short helpers: `block_subsidy`, `founders_share`, `miner_share`, `subsidy_range`, `miner_range`, `mature_height`, `mine_until_mature`, `mature_or_skip`, `assert_raises_message`.
- **`wallet.py`** Sapling port + fee-aware miner balances -> **Tier B pass**.

- ZERO_COIN.md consolidation; harness exit-code / getchaintips / zeronode null guards; shell-notify compile gate; OPS-DEV-UTXO; LevelDB `max_open_files` 256; OPS-CACHE measured; OPS-REINDEX markers/resume; OPS-BOOTSTRAP-DOC; WAL-WTXORDERED + Assure-4; S7 const wallet-tx walks (getalldata / listsinceblock / listtransactions iterate); TST-07 walletbackup; EXT five insight scripts B pass; getalldata S4--S8 + W2/W3 exclusive; `getalldata_scenario` Ext; longpoll funded-node pin; S8 once-per-episode WARNING; soft **-34** client path on Zerowallet
- v4.0.1 macOS `--strict` PASS (2026-06-09)
- PERF-TREE: ZeroPerf stays separate

---

## Full descriptions

### WAL-WTXORDERED / const policy

**Done:** Incremental `wtxOrdered` on insert/erase/reorder/rebuild; Assure-4 gtest; keep accounts/`TxPair`.

**Const (S7 and follow-ons):** Zero **continues const conversion** for wallet-tx read paths. Prefer `const CWalletTx*` / `const_iterator` over peer line-for-line identity. Code comments at the smart-time walk and `getalldata` ordered map state this. Line-by-line Zcash `wtxOrdered` **type** match is **deprioritized** and stays with postponed **WAL-RPC-ACCOUNTS**.

| Path | Const today | Kept non-const | Why non-const | Future mitigation |
|------|-------------|----------------|---------------|-------------------|
| `getalldata` `orderedTxs` | `map<int64_t, const CWalletTx*>` | -- | -- | -- |
| `getRpcArcTx(const CWalletTx&)` | yes | -- | -- | -- |
| `listsinceblock` map walk | `const_iterator` + `const CWalletTx&` | -- | -- | -- |
| `listtransactions` OrderedTxItems walk | `const_reverse_iterator` + `const CWalletTx*` | -- | -- | -- |
| `SendMoney` / create-send helpers | -- | `CWalletTx& wtxNew` / local `CWalletTx wtx` | Mutate and commit new wallet txs | Keep; do not force const on create path |
| `AddToWallet` / erase / reorder | -- | `CWalletTx&` in map | Insert/update wallet state | Keep |
| `TxPair` / `wtxOrdered` storage | -- | `CWalletTx*` (mutable) in multimap | Matches existing account-era type; shared with erase/reorder | After **WAL-RPC-ACCOUNTS**: pointer-only map; still store non-const pointers, expose const views at RPC readers |
| `OrderedTxItems` return | -- | `TxItems` with mutable pointers | Callers that only read should use const iterators (done for listtransactions) | Audit remaining `reverse_iterator` callers |

**Serious justification required** to drop const on a read path (e.g. API that must call a non-const method with no const overload). Document the call site if that happens.

**WAL-RPC-ACCOUNTS (postponed):** Drop obsolete account RPCs / BDB `acentry` merge only after a product decision plus caller/help/DB-upgrade review. Not a gate for const or getalldata work. Zcash pointer-only `wtxOrdered` type stays tied to this item alone.

### Helpers design (`getalldata`)

**Goal:** One parse/filter path so day window, `nCount`, watchonly, and datatype gates cannot drift between insert filter, emit, and tests.

**Define:** `src/wallet/rpczerowallet.h` / `.cpp` beside `IsGetAllDataTxTooOld`.

**Use (v1):** `getalldata` only. Exclusive tests may call exported helpers. Do not wrap `zs_*` emitters or HTTP (S8) in this pass.

| Helper | Status | Call sites | Replaces | Match |
|--------|--------|------------|----------|-------|
| `IsGetAllDataTxTooOld` | **shipped** | archive + wallet History insert; W3 tests | inline day compares | identical intent; keep thin emit `dayCutoff` |
| `ParseGetAllDataDayWindow(int)` | design | arg2 switch | switch body | identical |
| `ParseGetAllDataCount(params)` | design | nCount clamp | `>=3` / `<=0`->200 block | identical |
| `GetAllDataIncludeWatchonly(params)` | design | 4th arg | `size==4` bool | identical |
| `ShouldEmitGetAllDataBalances/History` | design | datatype 0/1/2 gates | repeated `params[0]` tests | very similar |
| Sort-key insert + W2 counter | design | archive + wallet merge | two near-copy blocks | very similar |
| Soft **-34** / in-flight | keep local to S6 | entry gate | -- | out of scope |
| `getRpcArcTx*` | already shared | getalldata + `zs_*` | -- | somewhat parallel; no re-wrap |
| Python day/`nCount` constants | design | `getalldata_scenario.py` | magic numbers in asserts | somewhat parallel |

### WAL-GETALLDATA-ARG2-DEFAULT (postponed) -- value **2**

**Arg2** = `transactiontype` day window: `0`=all, `1`=1d, `2`=7d, `3`=30d, `4`=90d, `5`=365d, other=all.

**Today:** when arg2 omitted, implementation uses `day = 365 * 30` (~30y).

**Proposed default when omitted: `2` (7 days).** Matches Zerowallet tip `{0, 2, 50, true}`; bounds CLI omitted-arg path; operators keep explicit `0` for full history. Risk: scripts that omitted arg2 and expected ~30y History -- release-note.

### WAL-GETALLDATA-W5 -- revisit soon

**Idea (stashed on Zerowallet):** split tip poll -- datatype **1** (balances) on the timer; full History (datatype **0**) on user action or every Nth tick.

**Relation to shipped code:** complementary to **S6** (-34 coalesce); reduces payload/decrypt when S6 allows a call; does not bypass **S5**; soft UX already covers soft errors.

**Pros / cons:** lower tip CPU vs stale History / dual GUI paths / W6 key complexity. **Risk:** Medium UX; Low consensus.

**Next:** revisit soon after S4--S8 + scenario soak; decide apply vs hold stash before W6.

### WAL-GETALLDATA-CACHE (W6)

Tip+dirty in-process cache. Stashed on Zero400. Prefer after W5. Orthogonal to `wtxOrdered`.

### WAL-GETALLDATA-W1 / W4

- **W1:** merge History key insert into the balance `mapWallet` pass. After slew soak.
- **W4:** IVK decrypt review. Postponed.

### WAL-GETALLDATA-HELPERS

Implement the **Helpers design** table above (`WAL-GETALLDATA-HELPERS` status: Pending).

### WAL-GETALLDATA-ADDRKEY (Zerowallet; out of Zero400 scope)

**Finding (2026-07-24):** fat-wallet `getalldata` samples hot in `EncodeBase58Check` because the balance walk keys `addressBalances` by freshly encoded address strings per UTXO. Structure, preferred fix, and rejected 8-byte hash keys: **ZeroStruct.md** §6.2.

**Outcome (2026-07-24):** no prototype in this tree (AGENTS: Zerowallet out of scope). Implement in Zerowallet / `rpczerowallet` when scheduled; Zero400 keeps the finding only.

### WAL-GETALLDATA-LEGACY-SCOPE (2018--2020 surface)

| Era | Keep / shrink |
|-----|---------------|
| **2018-11** add RPC | Keep RPC; do not grow kitchen-sink without datatype gates |
| **2019** redesign / `rpczerowallet` | Keep arc helpers; reduce duplicate day/count via helpers; W1 for double walks |
| **2020-11** GUI tip = full getalldata | Client W5 / S6; ARG2-DEFAULT **2** |

**Do not undo without replacement:** S4--S8, W2, const walks (S7).

### TST-01 / `getalldata_scenario`

Exclusive Boost: empty-wallet gates. Scenario Ext: populated wallet nCount/datatype. Further: `getsupply` / `zs_*`.

### Stable subsidy arithmetic (implementation)

Replace `double`×`COIN` and `* 0.075` / `* 7.5 / 100` mixes with integer zats: base **10.8 ZER** as integer zats; founders carve **`subsidy * 75 / 1000`** (trunc toward 0) via one helper used by miner, validate, GBT, and metrics. Reasoning and schedule: **ZERO_COIN.md**. Touch list: **BUILD_ZERO.md** §4.8.

### WAL-LOCKEDPOOL

Port LockedPool + optional `getmemoryinfo`; Zero has `GetLockedPageCount()` only.

### OPS / FR / EXT (short)

- **OPS-REINDEX / ALERT-STRIP / CACHE-METRICS / TXINDEX-DEFAULT / AT-HEIGHT:** see Pending.
- **FR-ROTATE / TADDR / Z:** product options; postponed.
- **EXT-INSIGHT-SUPERSET:** founders-index at START/STOP **done** (`founders_window.py` + Insight). Explorer-host PRs remain out of scope.

### WAL-UI-TX-WINDOW / WAL-QT-UI-TEST

Zerowallet History day control (pairs ARG2 / W5). No QTest suite; soft checks manual. Not a Zero400 harness item.

---

## Zcash / Bitcoin PR ideas

Checked against upstream tip (2026-07). Explorer-host PRs are out of scope here.

| Candidate | Upstream tip | Zero today | Action |
|-----------|--------------|------------|--------|
| Longpoll funded-node flake | Zcash still uses `random_transaction(self.nodes)` (can pick unfunded peer). Bitcoin Core uses **MiniWallet** on node0. | Zero pin to funded node in `getblocktemplate_longpoll.py` (Ext pass) | **Zcash PR candidate** (pin or MiniWallet-equivalent). Bitcoin: no funding PR needed. |
| Work-queue reject logging | Bitcoin + Zcash: **WARNING every** rejected request. Bitcoin already returns **503**. Zcash still **500** + every-reject WARNING. | Zero: **503** + WARNING **once per full episode** (S8); `rpc_workqueue_full` Ext | **Bitcoin PR candidate:** once-per-episode WARNING. **Zcash PR candidate:** 503 + once-per-episode (or at least 503). |

---

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidelines.
