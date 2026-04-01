# UpdateZero

Maintainer hub: **documentation map**, branch and validation, consensus and engineering notes, release and roadmap, **Appendix A** (test/harness prescriptions), **Appendix B** (short editor notes), **Appendix C** (draft blocks for **ZERO_COIN.md**), **Appendix D** (subsidy implementation excerpts and **`src/`** pointers for maintainers).

**Branch convention:** Integration work targets **`zero-merge`**. Side branches are not release branches unless tagged.

**Contents:** §1 Map · §2 Branch & validation · §3 Consensus & zeronode · §4 Engineering policy · §5 Release, tags, roadmap · §6 Rollout & decisions · §7 Fork-specific implementation · Appendix A test/harness · Appendix B editor notes · Appendix C **ZERO_COIN** source material · Appendix D subsidy code supplement

---

## 1. Documentation map

Documentation is split so **builders and operators never need this file**. **[README.md](README.md)**, **[BUILD_ZERO.md](BUILD_ZERO.md)**, and **[TEST_ZERO.md](TEST_ZERO.md)** each open with a short **partitioning** note: user-facing docs do not reference **`Update*.md`**; **[AGENTS.md](AGENTS.md)** lists the definitive user-facing set and forbids linking **`UpdateZero.md`** from those guides.

**Audiences and first stops.** Visitors and miners start at **README**. Node operators use **README** then **ZERO_COIN** (ports, maturity, glossary). Builders use **BUILD_ZERO**; contributors add **TEST_ZERO**, **CONTRIBUTING**, and **TODO**. Integrators and pools rely on **ZERO_COIN** and **doc/man/**. Maintainers use **UpdateZero** (this file), **UpdateBuild.md**, **UpdateTests.md**, and **TODO**.

**Typical paths.** (1) Run a node: README → ZERO_COIN; build only if compiling (**BUILD_ZERO**). (2) Build from source: BUILD_ZERO → TEST_ZERO to validate. (3) Ship a release: TEST_ZERO strict gate + BUILD_ZERO smoke + §5 below. (4) Chain behavior only: **ZERO_COIN**, not UpdateZero.

**Where content lives.** Vision and links → **README**. Compile, depends, platforms → **BUILD_ZERO**. Tests and logs → **TEST_ZERO**. Checklists → **TODO**. Observable chain and node facts, glossary → **ZERO_COIN**; subsidy code excerpts → **Appendix D** below. Dependency pins → **BUILD_ZERO** §4.1; cross-coin dependency comparison → **UpdateBuild** §5. Branch-id policy, NUM-01, deep zeronode notes → **UpdateZero**. Test exclusions and P1–P4 backlog → **UpdateTests**.

**Health check.** A builder following **BUILD_ZERO** + **TEST_ZERO** alone should succeed without opening UpdateZero.

---

## 2. Branch, version, validation

```bash
cd ~/Work/ZK/Zero400
git fetch origin
git stash push -m "WIP"   # if dirty
git checkout zero-merge
git pull --ff-only origin zero-merge
```

Release identity lives in **`configure.ac`** (`_CLIENT_VERSION_*`), **`src/config/bitcoin-config.h`**, and **`src/clientversion.h`**. Pinned dependencies: **BUILD_ZERO.md** §4.1; deferred upgrade queue: **UpdateBuild.md** §4. After a version bump, run build/smoke per **BUILD_ZERO** and the contributor gate per **TEST_ZERO**; confirm **`zerod -version`** matches the intended release.

---

## 3. Consensus and zeronode

**Network upgrades and branch id.** Overwinter-style transactions bind a **consensus branch id** into the **signature hash**. In **`src/consensus/upgrades.cpp`**, **Sapling** and **Cosmos** both use **`0x7361707a`**. There is **no** planned fork solely to split those ids; duplicate id is documented **technical debt** until a deliberate NU. Integrator-facing wording belongs in **ZERO_COIN.md** (*Network upgrades and branch identifiers*). Optional later: CI guard for duplicate active mainnet **`nBranchId`** (**NU-01**).

**Zeronode vs TENT.** **`src/zeronode/*`** parallels Dash-style **`masternode/*`**. Zero uses a safe iterator order when cleaning expired broadcasts (erase sync key, then advance). **`CZeronodeBroadcast::CheckAndVerify`** must not dereference **`chainActive[height]`** when **`CChain::operator[]`** returns **NULL** (short active chain, IBD, regtest)—use **`if (!pConfIndex) return false;`** before **`GetBlockTime()`**. **CheckInputsAndAdd** already has a null-guard; audit other **`chainActive[...]`** sites (**TODO.md**). Diff **`swifttx.cpp`**, **`budget.cpp`**, **`payments.cpp`** against upstream forks for post-fork fixes. Test gaps: **UpdateTests.md**; commands: **TEST_ZERO.md**.

---

## 4. Engineering policy

**Height and expiry.** **`TransactionBuilder::SetExpiryHeight`** mixes **`int`** chain height with **`uint32_t`** expiry—avoid implicit promotion bugs; prefer explicit casts or **`int64_t`** for height in new code. Boundary behavior belongs in the test suite; runbook **TEST_ZERO.md**.

**Numeric policy (NUM-01).** Consensus and subsidy paths should be **integer-only**; default rounding for reward splits: **truncate toward zero**. **Trigger:** changes to **`main.cpp`**, **`miner.cpp`**, **`zeronode/payments.cpp`**, **`consensus/`**, or subsidy/fee math in **`wallet/`**; or audit before a major release. **Owner:** **TODO.md** + **BUILD_ZERO.md** §4.10–4.10.1. **Steps:** (1) Grep **`double`**, **`float`**, **`/ 100.0`**, **`0.075`**, **`10.8 * COIN`** under **`src/`** in those areas. (2) For each subsidy / founders / zeronode / miner split, match **validation** and **mining** paths for identical order of operations. (3) Prefer **`a * b / c`** on widened integers; no new float in consensus without review. (4) Add regression tests for far-future halving. (5) After refactors, **ZERO_COIN** states user-visible numbers; code is truth. **Exit:** no stray float in targeted paths or each documented non-consensus; tests aligned with **BUILD_ZERO** §4.10.

**C++ exceptions.** Use **`throw std::runtime_error("…");`**, not **`throw new …`**. **`throw new`** has been removed from **`src/**/*.cpp`** on the integration line. Test with **`EXPECT_THROW`**, **`CheckRPCThrows`**, or Python **`JSONRPCException`** where the error crosses a boundary.

**Raw transaction RPC (#70).** Verbose **`getrawtransaction`** / **`decoderawtransaction`** use **`TxToJSONExpanded`**. **`size`** is present; **`fees`** deferred (spent index / shielded economics).

---

## 5. Release, tags, and roadmap

**Release artifacts.** Tag **`vMAJOR.MINOR.PATCH`**; archives **`Zero-<ver>-<target>-<triplet>.<ext>`**; one checksum convention (e.g. **`SHA256SUMS-<ver>.txt`**) and optional detached **`*.asc`**. Guix undocumented until adopted (**REL-HOST**). Params and mirror policy: describe in **BUILD_ZERO.md**.

**Tags.** **REL-4.0.1** — release validation (§2), zeronode robustness (§3). **NUM-01** — §4 numeric policy. **NU-01** — branch-id posture in **ZERO_COIN**; optional CI. **REL-HOST** — mirrors and signing.

**Roadmap.** Near term: run validation after each bump; close zeronode **`chainActive[]`** audit items (**TODO**); keep Tier A RPC **serial** as the gate (**`--jobs>1`** experimental). Backlog themes: keep **ZERO_COIN** and **Appendix C/D** aligned with **`src/`** after consensus edits; align **README** with §1 map; **NUM-01** and expiry-at-zero research; **REL-HOST** and **fetch-params** (**TODO**); P1–P4 and harness work in **UpdateTests**. Per tag: **REL-4.0.1** — green strict gate + notes; **NUM-01** — §4 steps + **BUILD_ZERO** §4.10; **NU-01** — **ZERO_COIN** subsection complete; **REL-HOST** — manifest owner.

---

## 6. Rollout and decisions

**Phased rollout.** **A** — README hero, links, partitioning blurb. **B** — **ZERO_COIN** body from **Appendix C** + glossary; **Appendix D** for maintainer subsidy excerpts. **C** — **BUILD_ZERO** / **TEST_ZERO** / **TODO** aligned with §1; **TEST_ZERO** leads with Quick Start and harness overview. **D** — README doc map lists **ZERO_COIN** as the chain reference. **E** — **UpdateBuild** / **UpdateTests** hold only what user docs do not. **F** — **Zeronode_wallet** placement (standalone vs **BUILD_ZERO** `--disable-wallet` note).

**Tracking.** **TODO.md**, **TEST_ZERO** (known failures / changelog), **UpdateTests** (IDs, P1–P4), this file. GitHub Issues deferred. External presence (site, socials, brand) should match **README** / **ZERO_COIN** facts.

**Impact categories** for prioritization: non-consensus bugfix (node release only); consensus / fork (NU + comms); index / explorer (redeploy); wallets (wallet release + notice).

**Decisions (detail elsewhere):** OpenSSL **1.1.1w** in **depends** until audited **3.x** — **BUILD_ZERO** §4.1, **UpdateBuild**. Sapling/Cosmos **`nBranchId`** **`0x7361707a`** — §3, **ZERO_COIN**, **NU-01**. System Rust where supported — **BUILD_ZERO** §4.11–4.12. Float / **NUM-01** — §4, **BUILD_ZERO** §4.10. **`throw new`** removed — §4. Zeronode NULL **`pConfIndex`** — §3, **TODO**. Params — **TODO**, **BUILD_ZERO**. Test backlog — **UpdateTests**, **TEST_ZERO**.

---

## 7. Fork-specific implementation

**Witness path.** Upstream Zcash often increments witnesses from **ChainTip** without **`ReadBlockFromDisk`** in the wallet. Zero uses **`VerifyAndSetInitialWitness`** and **`BuildWitnessCache`** with optional **`pblockIn`**, coupling to **`pcoinsTip`** and chain views. Hardening: null checks, **`pblockIn`**, nullifier guards. **Tradeoff:** harder unit testing → exclusions in **UpdateTests.md**; commands **TEST_ZERO.md**. Code: **`src/wallet/wallet.cpp`**, **`wallet.h`**.

**Equihash.** Zero keeps **libsodium C** **`crypto_generichash_blake2b_state`** for **`eh_HashState`**. A Rust/CXX bridge like Zcash v6+ would need **`librustzcash`** / **`rustcxx`** alignment—out of scope unless the PoW stack moves.

**Branding.** User-visible strings should read **ZERO**. Clean residual **Zcash** / **Bitcoin** names in tests or metadata when touching those files; not consensus.

---

## Appendix A — Test and harness change prescriptions

Use when **porting or fixing** RPC tests. **How to run** and log reading: **TEST_ZERO.md**. **Backlog IDs:** **UpdateTests.md**.

**P2P / regtest.** Peers must advertise **`nVersion` ≥ 170007**; **`mininode.py`** default **170009**. Regtest **magic** must match **`chainparams.cpp`**. Do not cap **`ver_send`** at Sprout for Sapling tests. Refs: **`p2p_txexpiry_dos.py`**, **`p2p_nu_peer_management.py`**, **TEST_ZERO**.

**Coinbase maturity 720.** After short or clean chains, call **`mine_until_node_has_mature_coinbase`** or **`ensure_mature_coinbase_or_skip`** before spends. Optional **`ZERO_MINE_COINBASE=1`** for bulk mine. Refs: **`wallet_changeindicator.py`**, **`wallet_changeaddresses.py`**, **`util.py`**.

**Regtest NU.** **`-nuparams=6f76727a:1`** (Overwinter), **`-nuparams=7361707a:1`** (Sapling). Blossom tests: set Blossom **`-nuparams`** above tip after maturity mining. Refs: **`wallet_changeaddresses.py`**, **`wallet_overwintertx.py`**.

**Wallet.** Sprout viewing key: if **`GetSproutNoteNullifier`** is empty, skip nullifier map update (no **`assert(false)`**). Ref: **`wallet.cpp`**, **`wallet_changeindicator.py`**.

**Python 3.** **`serialize_script_num`**: **`bytearray.append(int)`**, not **`chr(...)`**. Import **`initialize_chain_clean`** when used.

**Partition tests.** **`split=True`**: only edges **0–1** and **2–3**; **`CHAIN_BOOTSTRAP`** + guard before re-mine. Ref: **`getchaintips.py`**.

**Parallel Tier A.** **`--jobs>1`** is best-effort; serial **`N=1`** is the gate. **TODO.md**: **`paymentdisclosure`** hang under load.

New prescription: add a row above and a **TEST_ZERO** harness changelog entry if behavior is user-visible.

---

## Appendix B — Notes for documentation editors

- §1 is the **only** full documentation map; user-facing files repeat the short partitioning paragraph only.
- **TEST_ZERO** order: Quick Start → harness **prose** → then tables (changelog, reference, allowlists).
- **Appendix C** supplies **ZERO_COIN** draft text; **Appendix D** holds subsidy code excerpts—update **D** when consensus paths change.

---

## Appendix C — Source material for ZERO_COIN.md

**Purpose.** Editors **adapt** the subsections below into **ZERO_COIN.md** narrative sections. Code excerpts and file:line-heavy material live in **Appendix D**. This appendix is **maintainer-only**; do not link it from user-facing docs.

**Do not paste into ZERO_COIN:** long **` ```cpp `** blocks, ConnectBlock validation snippets, cross-chain source comparisons, RPC test file inventories—those stay in **Appendix D**, **TEST_ZERO**, **UpdateTests**, or **src/**.

### C.1 Economics and emission (draft for ZERO_COIN)

**Summary vs other chains (one paragraph).** Zero uses a **block subsidy** with **halving** steps, **no Zcash-style slow start**, a **7.5% founders** allocation on the subsidy in eligible heights, and a **zeronode** share of block value (**20–40%** tiered, spork-gated). Base subsidy is **10 ZER** before the fee-start height and **10.8 ZER** after (mainnet fee-start **412300**). Halving interval is **800,000** blocks pre-Blossom and **1,600,000** post-Blossom; **Blossom** is not activated at a fixed height on mainnet in current params—the pre-Blossom halving formula applies for height accounting used in docs unless that changes. Target spacing **120 s** pre-Blossom. Actual halving dates on mainnet can be taken from chain explorers (e.g. heights **800k**, **1.6M**, **2.4M** with ~3-year spacing).

**Constants (operator table).** Pre-Blossom target spacing **120 s**; post-Blossom **60 s** when active; pre-Blossom halving interval **800,000** blocks; post-Blossom **1,600,000**; regtest uses shorter intervals for testing (**ZERO_COIN** timing table; **params.h** for exact names).

**Subsidy rule (prose).** Starting from **10 ZER** (or **10.8 ZER** at and after fee-start), the subsidy is right-shifted by the **halving count**. When Blossom rules apply, the base is also divided by the Blossom spacing ratio (**2**) before halving shifts. Subsidy hits zero after 64 halvings.

**Fee-start height (table).** Mainnet **412300**; testnet **1**; regtest **5000**. At fee-start on mainnet: base steps to **10.8 ZER** and founders outputs become required in coinbase through the last founders height per consensus.

**Founders (7.5%).** Applied when height is between fee-start and **`GetLastFoundersRewardBlockHeight`** (pre-Blossom last founders height **7,999,999** per current formula). Recipient rotates through **`vFoundersRewardAddress`** by height.

**Zeronodes.** **`GetZeronodePayment`**: default **20%** of block value when sporks enable full tier schedule; tiers step at halving multiples (**25%**, **30%**, **35%**, **40%**) with **SPORK_6** and **SPORK_7**; without **SPORK_6**, a fixed **100,000** zatoshis; without **SPORK_7**, **0**. Budget superblocks can replace the normal payee path when enabled.

**Payee order (bullets).** Typical block: **`blockValue`** from **`GetBlockSubsidy`**; founders take **7.5%** of that when required; zeronode payment computed from **`GetZeronodePayment`**; **miner** receives remainder plus fees (see **`FillBlockPayee`** in **`zeronode/payments.cpp`** / budget path).

**Worked example (refresh periodically).** Example height **2,382,565**: halvings **2** → subsidy **2.7 ZER**; founders **0.2025 ZER**; zeronode **30%** in that band → **0.81 ZER**; miner **~1.6875 ZER** plus fees (**ZERO_COIN** worked example).

**Total issued (summary).** Roughly **~25.6M ZER** long-run under the documented piecewise sum (pre-fee era, post-fee pre-halving, geometric halving chain). **MAX_MONEY** in **`amount.h`** caps **single-output** amounts and does **not** equal total issued supply—validation uses **`MoneyRange`** per subsidy output; state this clearly for integrators.

### C.2 Operations (draft for ZERO_COIN)

**Ports and config.** Default RPC port **23801** (see README / **contrib/zero.conf**). Datadir **`.zero`**; proving params via **fetch-params** scripts (**BUILD_ZERO** for mirrors and naming).

**P2P.** Subversion string uses Zero branding (not upstream “MagicBean”); exact pattern in node and **doc/tor.md** should match shipped builds.

**Security warnings.** Experimental software; backup **`wallet.zero`**; key custody; link README security and Zcash security page where appropriate.

### C.3 Addresses and on-chain references (draft for ZERO_COIN)

**Founders addresses (mainnet).** Rotate by height; **`chainparams.cpp`** and **ZERO_COIN** founder table.

**Zeronode dummy address.** Used for **collateral validation** constructs, not a normal payout sink—**ZERO_COIN** + **Appendix D.11**.

**ZeroWallet donation address.** Lives in **zerowallet** tree, not this repo—point readers to wallet documentation.

### C.4 Integrator alignment (branch id)

Ensure **ZERO_COIN** *Network upgrades and branch identifiers* states: Sapling and Cosmos share **`0x7361707a`**; wallets and signers must follow **`getblockchaininfo`** activation heights for their network; replay between chains depends on chain ID and peers, not branch id alone.

### C.5 What stays out of ZERO_COIN (reference only)

Long **` ```cpp `** blocks, **ConnectBlock** founders check, cross-chain source comparisons, §11.1 internal review table, §11.2/§14 test file lists—**Appendix D** below (or **src/**). Integer migration spec: **BUILD_ZERO** §4.10. Harness porting: **Appendix A** above.

---

## Appendix D — Subsidy implementation reference

**Purpose.** Code excerpts, validation references, and porter notes for consensus subsidy paths. **File:line** drift is possible—verify against **`src/`**. User narrative: **ZERO_COIN.md**.

### D.1 Base block subsidy — `GetBlockSubsidy`

**Location:** `src/main.cpp` (search `GetBlockSubsidy`).

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

- Pre-fee: **10 ZER** base; post-fee: **10.8 ZER**; halvings: right-shift; Blossom path divides base by **2** before shift when that NU is active.

### D.2 Halving — `Params::Halving`

**Location:** `src/consensus/params.cpp` (search `Params::Halving`).

```cpp
int Params::Halving(int nHeight) const {
    if (NetworkUpgradeActive(nHeight, Consensus::UPGRADE_BLOSSOM)) {
        int64_t blossomActivationHeight = vUpgrades[Consensus::UPGRADE_BLOSSOM].nActivationHeight;
        int64_t scaledHalvings = ((blossomActivationHeight - SubsidySlowStartShift()) * Consensus::BLOSSOM_POW_TARGET_SPACING_RATIO)
            + (nHeight - blossomActivationHeight);
        return (int) (scaledHalvings / nPostBlossomSubsidyHalvingInterval);
    } else {
        return nHeight / nPreBlossomSubsidyHalvingInterval;
    }
}
```

**Zero:** no slow start (`SubsidySlowStartShift() == 0`); pre-Blossom: `halvings = nHeight / 800000`.

### D.3 Last founders block — `GetLastFoundersRewardBlockHeight`

**Location:** `src/consensus/params.cpp`.

```cpp
int Params::GetLastFoundersRewardBlockHeight(int nHeight) const {
    bool blossomActive = NetworkUpgradeActive(nHeight, Consensus::UPGRADE_BLOSSOM);
    if (blossomActive) {
        int blossomActivationHeight = vUpgrades[Consensus::UPGRADE_BLOSSOM].nActivationHeight;
        return blossomActivationHeight + nPostBlossomSubsidyHalvingInterval
            - (blossomActivationHeight - SubsidySlowStartShift()) * BLOSSOM_POW_TARGET_SPACING_RATIO - 1;
    } else {
        return (nPreBlossomSubsidyHalvingInterval*10)  - 1;
    }
}
```

Pre-Blossom: **`800000*10 - 1 = 7,999,999`**. **`GetFoundersRewardScriptAtHeight`** / **`GetFoundersRewardAddressAtHeight`** require fee-start ≤ height ≤ last founders height.

### D.4 Founders and zeronode excerpts

**Founders (example pattern):** `src/zeronode/payments.cpp`, `src/zeronode/budget.cpp` — `blockValue * 7.5 / 100` when height is in the founders window.

**`GetZeronodePayment`:** `src/main.cpp` — default **20%** of `blockValue`; with **SPORK_7** and **SPORK_6**, tier steps at **800k** multiples (**25%** … **40%**); without **SPORK_6**, **100000** zatoshis; without **SPORK_7**, **0**.

**`FillBlockPayee`:** `src/zeronode/payments.cpp` — superblock path vs **`zeronodePayments.FillBlockPayee`**; order: **`blockValue`**, founders, zeronode, miner + fees (**`miner.cpp`** **`CreateNewBlock`**).

### D.5 Total supply formula (maintainer)

Piecewise sum (mainnet, fee-start **412300**): pre-fee **[0, 412299]**; post-fee segment before first halving; then geometric halving tail → long-run **≈ 25.6M ZER**. **`MAX_MONEY`** vs cumulative issuance: see **ZERO_COIN** *Total supply and MAX_MONEY*.

### D.6 Internal review table (§11.1 migration)

| Location | Issue |
|----------|-------|
| `src/amount.h` | `MAX_MONEY` vs total issued ~25.6M ZER — per-output **`MoneyRange`** only. |
| `TODO.md` / legacy docs | Drop outdated **`338665500000000`** total-subsidy zatoshi references if any remain. |
| `doc/tor.md` | **subver** examples must match shipped Zero branding, not legacy MagicBean. |

### D.7 RPC Python tests — sample inventory

| File | Note |
|------|------|
| `test_framework/blocktools.py` | Regtest halving interval, founder % from fee-start height |
| `test_framework/util.py` | Zero branch IDs |
| `blockchain.py` / `wallet.py` | Amount expectations — align with Zero params when porting |

### D.8 Consensus validation (founders output)

**Location:** `src/main.cpp` (coinbase check near founders height range).

```cpp
if ((nHeight >= consensusParams.nFeeStartBlockHeight) && (nHeight <= consensusParams.GetLastFoundersRewardBlockHeight(nHeight))) {
    // Must find output: scriptPubKey == GetFoundersRewardScriptAtHeight(nHeight)
    //                   nValue == GetBlockSubsidy(nHeight, ...) * 0.075
    if (!found) return state.DoS(100, error("founders reward missing"), REJECT_INVALID, "cb-no-founders-reward");
}
```

### D.9 Comparison with other chains (summary)

**Bitcoin:** `halvings = nHeight / 210000`; **50 BTC >> halvings**; no founder/zeronode slice in coinbase taxonomy used here.

**Zcash:** 20% founder era, slow start, **`SubsidySlowStartShift`**, Blossom-scaled halving; later funding streams (ZIP 214).

**Pirate:** asset-chain **`komodo_ac_block_subsidy`**, **`ASSETCHAINS_*`** parameters.

### D.10 Tests and logs

**C++:** `main_tests.cpp` — subsidy tests may skip under Zero reference model; `test_foundersreward.cpp`; regtest halving intervals.

**Logs:** `payments.cpp` — zeronode/founder/miner/coinbase trace lines.

### D.11 Addresses and keys in code

**Founders:** `src/chainparams.cpp` — **`vFoundersRewardAddress`** mainnet/testnet/regtest; RPC **`developmentfee`** (`src/rpc/zeronode.cpp`).

**Zeronode dummy:** `chainparams.cpp` **`ZeronodeDummyAddress`** — collateral validation only (`zeronode.cpp` **`GetTestingCollateralScript`**).

**ZeroWallet donation:** out-of-tree **`zerowallet`** settings.

**Test WIF / extended keys:** `src/test/rpc_tests.cpp`, `qa/rpc-tests/sprout_sapling_migration.py` (verify paths in tree).

**Alert signing:** legacy P2P alert tests vs Zcash removal — see codebase and **ZERO_COIN** security note; product decision is maintainer scope.
