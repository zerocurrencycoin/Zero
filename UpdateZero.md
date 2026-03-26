# UpdateZero

Project tracking for the Zero full-node repo. **Branch convention:** day-to-day integration targets **`zero-merge`**. Branches like **`zero-400names`** are **spike / naming** lines—revisit to merge or drop; do not treat them as release branches unless explicitly tagged.

**Section map:** **§1** docs · **§2** branch & version · **§3** consensus branch id · **§4** height / expiry · **§5** numeric policy · **§6** release artifacts · **§7** C++ exceptions · **§8** zeronode / TENT · **§9** RPC #70 · **§10** remainder · **§11** tracking tags · **§12** roadmap & status (review cycle + tables).

---

## 1. Documentation split (summary)

| Group | Examples | Audience |
|-------|-----------|----------|
| User-facing | README.md, BUILD_ZERO.md, TEST_ZERO.md, TODO.md | Builders and operators |
| Project | **UpdateZero.md**, UpdateBuild.md, UpdateTests.md, UpdateFeatures.md, … | Maintainers, design, status |

User-facing docs must not reference project doc filenames.

---

## 2. Branch, version, and validation (4.0.1 on `zero-merge`)

### 2.1 Switching worktrees (example: `~/Work/ZK/Zero400`)

```bash
cd ~/Work/ZK/Zero400
git fetch origin
git stash push -m "WIP"   # if dirty
git checkout zero-merge
git pull --ff-only origin zero-merge
# Later: git checkout zero-400names && git stash pop
```

### 2.2 In-code version **4.0.1**

| Location | Role |
|----------|------|
| **`configure.ac`** | `_CLIENT_VERSION_MAJOR/MINOR/REVISION` → packaged **4.0.1** when `BUILD` is release (50) |
| **`src/config/bitcoin-config.h`** | Generated: `CLIENT_VERSION_*`, `COPYRIGHT_YEAR` |
| **`src/clientversion.h`** | Fallback when not using `HAVE_CONFIG_H`—keep aligned when editing defaults |

### 2.3 Validation after bump

```bash
./autogen.sh
./configure --without-gui   # or your usual flags
make -j"$(nproc)" -C src zerod zero-cli zero-tx 2>&1 | tee build.log
./src/test/test_zero --run_test=rpc_rawparams   # smoke; expand per platform
./src/zerod -version
```

Expect **`zerod -version`** (or RPC `getnetworkinfo` subversion) to report **4.0.1** (and internal build suffix per `configure.ac` rules).

---

## 3. Consensus branch id, sighash, and activation ordering

### 3.1 What “same consensus branch id for sighash” means

Overwinter+ transactions include a **consensus branch id** in the **signature hash** (ZIP-243 and friends). **If two network upgrades share the same `nBranchId`**, signatures computed under one era’s rules can **replay** as valid under the other **for the same id**, unless something else (different tx version, different active flags, or different **activation height** semantics) makes the **signed payload** differ in practice.

**“Unless activation ordering makes them indistinguishable”** means: if **Sapling** is always active whenever **Cosmos** is active and **no tx can exist** in one era without already satisfying the other’s rules, **replay between names** may be **moot**—but **long-lived UTXOs** and **wallet signing** across historical heights still deserve a clear story.

### 3.2 Zero today

In **`src/consensus/upgrades.cpp`**, **Sapling** and **Cosmos** both use **`0x7361707a`**. That matches **ZIP-style id collision** risk unless deliberately documented.

### 3.3 TENT (SnowGem family) approach

In **`ZKs/TENT/src/consensus/upgrades.cpp`**, multiple post-Sapling **named** upgrades reuse **`0x76b809bb`** (Sapling’s id in Zcash). That pattern often means **“no new sighash epoch”**—policy or blocksize changes without changing the **signature domain**. **Risk:** if two **different** rule sets were assumed independent but share an id, tooling and replay analysis get harder.

### 3.4 Suggestions (from review)—effort / risk

| # | Suggestion | Complexity | Upgrade risk |
|---|------------|------------|--------------|
| **2** | **Document** duplicate ids (Sapling/Cosmos) as **intentional** or **accidental**; if intentional, publish **one paragraph** in **ZeroCoin.md** / release notes. | **Low** | **None** |
| **3** | **CI/static assert:** fail build if **two active mainnet upgrades** share **`nBranchId`** without a **whitelist comment** (or enforce uniqueness). | **Medium** | **None** (build-time only) |
| **Assign new Cosmos id** | New **`nBranchId`** + **coordinated network upgrade** | **High** | **Hard fork** unless gated and universally deployed |

Prefer **(2) then (3)** before considering **new id**. Tracked as **NU-01** in **§11**.

---

## 4. Height / expiry type mismatches (`TransactionBuilder` and elsewhere)

### 4.1 `SetExpiryHeight` (`src/transaction_builder.cpp`)

- **`nHeight`:** **`int`** (constructor stores chain height used to build the contextual tx).
- **`nExpiryHeight`:** **`uint32_t`** (Overwinter expiry field on the transaction).

**Condition today:** `nExpiryHeight < nHeight || nExpiryHeight <= 0 || nExpiryHeight >= TX_EXPIRY_HEIGHT_THRESHOLD`

**C++ usual arithmetic conversions:** comparing **`uint32_t`** to **`int`** promotes **`int`** to unsigned (or vice versa depending on operand order)—**negative `nHeight`** becomes a large unsigned when mixed with **`uint32_t`**, which can make comparisons surprising.

**`nExpiryHeight <= 0`:** for **`uint32_t`**, equivalent to **`nExpiryHeight == 0`** only.

### 4.2 Other height-related sites to audit

Search patterns: **`uint32_t.*[Hh]eight`**, **`nExpiryHeight`**, **`GetExpiryHeight`**, **`TX_EXPIRY_HEIGHT_THRESHOLD`**, RPC args that take height as **`int`** vs **`uint64_t`**. Wallet/RPC layers often use **`int`** for chain height while consensus uses **`int`** / **`unsigned int`** / **`uint32_t`** in different structs—**prefer explicit casts** and **one signed policy** (e.g. `int64_t` for “any chain height” in new code) documented at boundaries.

### 4.3 Test suitability

| Case | Idea |
|------|------|
| **Expiry &lt; height** | Construct `TransactionBuilder(params, nHeight=100000, …)`, `SetExpiryHeight(99999)` → **`EXPECT_THROW(..., std::runtime_error)`** (requires **`throw std::runtime_error`**, not `throw new`). |
| **Expiry == 0** | Same harness; assert whether **0** is rejected or allowed per ZIP-203 + `CreateNewContextualCMutableTransaction` defaults—**spec first**, then lock behavior with a test. |
| **At / above `TX_EXPIRY_HEIGHT_THRESHOLD`** | Boundary test at **500000000** and **499999999** (typical constant in Zcash-family `consensus.h`). |
| **Cross-module** | Mirror tests for **`CreateNewContextualCMutableTransaction`** paths in **`main.cpp`** that validate expiry—same boundaries, consensus-facing. |

Apply the same **boundary-test mindset** anywhere height is parsed from RPC JSON (`get_int`, `get_int64`) and stored in narrower types.

---

## 5. Numeric policy: floats, division, rounding (**processing rule**)

**Goal:** consensus and subsidy decomposition use **integer-only** paths; eliminate silent promotion.

**When floats appear unavoidable** (legacy formulas, logging): **convert to integer as soon as possible** using **explicit truncation toward zero** unless a written spec demands another rounding mode:

- Prefer **`CAmount` / `int64_t` zatoshi** end-to-end.
- For rational fractions: **`value * numer / denom`** with **overflow check** (widen to **`int128` / `arith_uint256`** if needed before multiply).
- **Document** rounding: default **truncate toward zero** for reward splits unless changed by network agreement.

**Subsidy / founders / miner / zeronode:** schedule a **dedicated work item** (**§11**, **NUM-01**): audit **`main.cpp`**, **`miner.cpp`**, **`zeronode/payments.cpp`**, and any **`double` / `0.075` / `10.8 * COIN`**-style expressions; replace with **shared helpers** so validator and miner use **identical** integer expressions.

**Review:** §5 content is **normative for new code**; full codebase retrofit is **staged** with **§11** / **§12**.

---

## 6. Release artifacts, checksums, signing (**no Guix**)

**Scope:** Do **not** document Guix in this repo’s release path until explicitly adopted. Tracked in part as **REL-HOST** (**§11**).

### 6.1 Naming (concrete)

Use a **single release id** everywhere:

- **Git tag:** `v4.0.1`
- **Archive basename:** `Zero-4.0.1-<target>-<triplet>`  
  Examples: `Zero-4.0.1-linux-x86_64-gnu.tar.gz`, `Zero-4.0.1-macos-arm64.tar.gz`, `Zero-4.0.1-win64.zip`
- **Checksum manifest:** `SHA256SUMS-4.0.1.txt` or `sha256sum-Zero-4.0.1.txt` (pick one; **use consistently**)
- **Signature:** `SHA256SUMS-4.0.1.txt.asc` (detached GPG) **or** sign only the manifest

### 6.2 Files to add or update (typical)

| Path | Change |
|------|--------|
| **`BUILD_ZERO.md`** / **`README.md`** | Release section: download → verify **`sha256sum`** → optional **`gpg --verify`** |
| **`contrib/gitian-descriptors/*.yml`** | **Remove or archive** if obsolete; replace with “manual release checklist” |
| **`doc/release-process.md`** (if present) | Same |
| **Release attach list** | `zerod`, `zero-cli`, `zero-tx`, `README`, **`SHA256SUMS*`**, **`.asc`** |

### 6.3 SHA256 invocations

**Linux / macOS (generate manifest):**

```bash
cd artifacts/4.0.1
sha256sum zerod zero-cli zero-tx > ../SHA256SUMS-4.0.1.txt
```

**Verify:**

```bash
sha256sum -c SHA256SUMS-4.0.1.txt
```

**Windows (PowerShell):**

```powershell
Get-FileHash -Algorithm SHA256 zerod.exe,zero-cli.exe,zero-tx.exe | Format-Table
# Build a line-per-file manifest to match sha256sum format if desired
```

### 6.4 Signing: per-build platform vs fixed Linux signer

| Approach | Pros | Cons |
|----------|------|------|
| **Sign on Linux only** (GPG + reproducible-ish tarball) | One key, one procedure | macOS/Windows may still need **codesign** / **Authenticode** on their respective hosts |
| **Sign on each platform** | Native notary / Authenticode | Key sprawl; harder to document |

**Practical split:** **GPG-sign the SHA256 manifest** on a **single hardened Linux** box; **additionally** **codesign** macOS `.app`/`.dmg` on **macOS** and **Authenticode** on **Windows** when distributing installers. **Verification:** users always **`sha256sum -c`**; optionally **`gpg --verify`** the manifest.

### 6.5 Params and bootstraps (what Zcash ecosystem does)

- **Params:** Zcash historically hosted **`download.z.cash`** URLs (see **`zcutil/fetch-params.sh`** in Zcash). **Clones** often **reuse the same script** or mirror URLs—**dependency on Zcash infra** unless mirrored.
- **Bootstrap:** **Not** part of consensus; various community / third-party hosts offer **snapshots** (quality varies). **Document:** “official” vs “community” with **hash verification** mandatory.

**Zero action:** host **`fetch-params` mirror** + optional **bootstrap** with **`SHA256SUMS`** and **signed manifest**; document in **BUILD_ZERO.md**.

---

## 7. `throw new std::runtime_error` — Zcash and clones (C++)

**Java** `throw new` in secp bundles is **unrelated**; below is **C++** only.

### 7.1 Confirmed instances (representative grep, local `ZKs/` trees)

| Tree | Files (approx.) |
|------|------------------|
| **zcash** | `transaction_builder.cpp`, `main.cpp`, `miner.cpp` (Orchard paths), `zcbenchmarks.cpp` (multiple file-open throws) |
| **Zero (this repo)** | **Fixed in 4.0.1 line:** `transaction_builder.cpp`, `main.cpp`, `zcbenchmarks.cpp` — **no remaining `throw new`** in `src/*.cpp` except unrelated Java |
| **zclassic** | `transaction_builder.cpp`, `main.cpp`, `zcbenchmarks.cpp` |
| **fluxd** | `main.cpp`, `zcbenchmarks.cpp` |
| **pirate** | `zcbenchmarks.cpp` (minimal set in C++; Java elsewhere) |
| **TENT** | `transaction_builder.cpp`, `zcbenchmarks.cpp` |
| **hush3** | *(none found in quick grep—recheck if needed)* |

**Fix:** `throw std::runtime_error("...");` — matches **`catch (const std::exception&)`** everywhere.

---

## 8. Zeronode vs TENT “masternode” (implementation comparison)

### 8.1 Structure

Zero **`src/zeronode/*`** aligns with Dash-style **`masternode/*`** in TENT: **`zeronodeman` ↔ `masternodeman`**, **`activezeronode` ↔ `activemasternode`**, **`swifttx`**, budget/payments.

### 8.2 Identical bug pattern (expired broadcast cleanup)

**Zero** `src/zeronode/zeronodeman.cpp` and **TENT** `src/masternodeman.cpp` both had:

1. `mapSeen*Broadcast.erase(it3++);`
2. `*Sync.mapSeenSync*.erase((*it3).second.GetHash());` **after** increment → **UB / wrong key**.

**Correct pattern** (present **earlier in the same function** for VIN-based cleanup): erase sync map with **`(*it3).first`**, **then** `mapSeen*Broadcast.erase(it3++)`.

**Zero 4.0.1 line:** **fixed** to match the good loop.

**TENT:** still contains the buggy order at **`masternodeman.cpp:~323–324`** (verify when porting).

### 8.3 Zero-specific deltas (candidates to review vs TENT)

- Renaming, **zeronode** payment protocol version checks, **Zero** chain params.
- Any **PIVX/Dash** merges after fork point—**diff `swifttx.cpp`, `budget.cpp`, `payments.cpp`** for security fixes on TENT not yet in Zero.

### 8.4 Test coverage

| Area | Zero | TENT |
|------|------|------|
| **Unit / RPC** | Partial (**UpdateTests.md** zeronode RPC); iterator bug **not** covered | Unknown—assume similar gaps |
| **Integration** | Limited | Limited |

**Action:** add **regression test** or **stress** for **`CheckAndRemove`** / obfuscation timer path (hard in unit tests—consider **ASAN** run + long-run testnet).

---

## 9. Raw transaction RPC supplement (Issue #70)

Verbose **`getrawtransaction`** / **`decoderawtransaction`** use **`TxToJSONExpanded`**; **`size`** present on **`zero-merge`**; **`fees`** deferred. Spent-index and shielded economics affect fee inference—see historical note in **`zerocurrencycoin/Zero`** hub if merged.

---

## 10. Remainder

Route **subsidy doc mismatches**, **P2P alert decision**, and **user-facing link audit** to **Subsidy.md**, **ZeroCoin.md**, **README** per existing hub sections when the full **`UpdateZero.md`** from **`origin/zero-merge`** is reconciled with this file.

---

## 11. Tracking tags (IDs)

Use these in commits, PRs, and cross-doc references. **§12** summarizes readiness.

| ID / tag | Topic | Primary sections |
|----------|--------|------------------|
| **REL-4.0.1** | Version bump; **`throw new`** removal (**§7**); zeronode iterator (**§8.2**)—**validate** with **§2.3** build + targeted tests | **§2**, **§7**, **§8** |
| **NUM-01** | Integer subsidy/founders audit | **§5** |
| **NU-01** | Branch id / Cosmos vs Sapling documentation + optional CI assert | **§3** |
| **REL-HOST** | Params mirror + bootstrap doc + **SHA256SUMS** + GPG | **§6** |

---

## 12. Roadmap: review cycle, status, and plans

### 12.1 Review cycle

Material in **§12.3** (backlog / research / decisions) and any **new** rows added to **§12.4** should be **triage-reviewed within one release cycle** (target: before **4.0.2** or within **~8 weeks** of merge, whichever comes first).

### 12.2 **REL-4.0.1** — in-tree status (code vs process)

| Item | In-tree expectation | Process still open |
|------|---------------------|----------------------|
| **`configure.ac` → 4.0.1** (revision + release build rules) | **Done** (revision bumped on 4.0.1 line) | Run **§2.3**; confirm **`zerod -version`** |
| **No C++ `throw new`** in named paths | **Done** (`src/**/*.cpp` cleanup) | — |
| **Zeronode `CheckAndRemove` iterator / sync key** | **Done** | **§8.4** regression or ASAN stress |

### 12.3 Backlog by readiness

| Readiness | Topics | Sections |
|-----------|--------|----------|
| **Ready to implement** | Build/validation checklist; **§3.4** suggestion **(2)** documentation only; **§6** doc/checklist updates after small naming decisions; **§1** audit for user-facing → project-doc leaks; **§8.4** ASAN or stress on paths hitting **`CheckAndRemove`** | **§1**, **§2.3**, **§3**, **§6**, **§8** |
| **Research before coding** | Height/expiry spec (**§4.3** expiry == 0); **§5** float / magic-fraction **inventory**; **§8.3** TENT diff for security fixes; **§9** #70 fees / spent-index | **§4**, **§5**, **§8**, **§9** |
| **Design / decision first** | **§3.4** suggestion **(3)** CI rule + whitelist; **§3.4** new Cosmos **id** (fork); **§5** rounding + shared helpers after audit; **§6** signing split + params mirror ownership; **§8.4** unit test vs integration tradeoff | **§3**, **§5**, **§6**, **§8** |

### 12.4 Tracking tags vs next action

| Tag | Next action |
|-----|-------------|
| **REL-4.0.1** | Close when **§2.3** passes and optional **§8.4** smoke chosen |
| **NUM-01** | Schedule audit; output inventory doc before refactors |
| **NU-01** | Do **§3.4 (2)**; then decide on **(3)** or fork-level **id** change |
| **REL-HOST** | Decide mirror + manifest owner; align **§6** docs |

---

*Last updated: renumbered sections; consensus → expiry → economics → release → code fixes → RPC → tracking → roadmap tables; cross-refs aligned to **§1–§12**.*
