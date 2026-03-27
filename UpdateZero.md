# UpdateZero

Project hub for the Zero full-node repo: documentation map, integration branch, consensus and release notes, and cross-cutting work tags.

**Branch convention:** Integration work targets **`zero-merge`**. Side branches (e.g. naming spikes) are not release branches unless tagged.

**Section map:** **§1** documentation map & strategy · **§2** branch & version · **§3** consensus branch id · **§4** height / expiry · **§5** numeric policy · **§6** release artifacts · **§7** C++ exceptions · **§8** zeronode / TENT · **§9** raw RPC (#70) · **§10** tracking tags · **§11** roadmap · **§12** documentation rollout (phased) · **§13** work items & external alignment

---

## 1. Documentation map and strategy

### 1.1 Goal

Move **as much information as is reasonable** into **user-facing** documents so builders, operators, and integrators do not need maintainer-only files. **README** stays **short and inviting**; depth lives in **BUILD_ZERO**, **TEST_ZERO**, **TODO**, and a single **detailed coin/chain** document.

### 1.2 User-facing layer (no `Update*.md` links)

These files **must not** name or link **`Update*.md`** (readers should never depend on maintainer hubs).

| Doc | Audience | Role |
|-----|----------|------|
| **README.md** | Broad: investors, traders, miners, node runners, contributors | **Front page:** what Zero is, why it matters, how to get involved, clear CTAs; links to **ZERO_COIN**, **BUILD_ZERO**, **TEST_ZERO**, **TODO**, website/social. **Not** deep consensus internals or wallet coin-selection algorithms. |
| **BUILD_ZERO.md** | Builders and operators who compile or deploy | Install, depends, platforms, troubleshooting, release-style artifacts users touch (checksums, params/fetch where relevant). |
| **TEST_ZERO.md** | Developers validating changes | How to run tests, expectations, RPC test notes at user-appropriate depth. |
| **TODO.md** | Maintainers + contributors | Actionable checklist; may reference **BUILD_ZERO** / **ZERO_COIN**; no Update* pointers. |
| **ZERO_COIN.md** (target) | Serious users, pools, exchanges, integrators | **Central detailed reference:** economics (subsidy, halving, founders, zeronode share), chain params, supply notes, operational facts (ports, config), and **technical operational** topics (e.g. coin selection, fee behavior) that would bloat README. Merges the intent of current **`Subsidy.md`** + **`ZeroCoin.md`** into one maintained file. |
| **Man pages** (`doc/man/`) | CLI users | Match shipped binaries; deep flags stay here or in **BUILD_ZERO**. |

**Migration:** Add **`ZERO_COIN.md`** by consolidating **`Subsidy.md`** and **`ZeroCoin.md`**; then trim or retire the old two files (or keep **`Subsidy.md`** as a redirect stub—decide on cutover). Until merge, **`Subsidy.md`** remains the technical subsidy draft; **README** should eventually point only to **ZERO_COIN** for “how the chain works.”

### 1.3 Maintainer / engineering layer (`Update*.md` and specialized)

| Doc | Role (current; may shrink as user docs absorb content) |
|-----|----------------------------------------------------------|
| **UpdateZero.md** | This map, branch/version, consensus notes, release process, tags, **§12–§13** rollout and tracking |
| **UpdateBuild.md** | Depends pins, platforms, build-system rationale |
| **UpdateTests.md** | Suite orchestration, exclusions, harness limits, RPC test development plan |
| **UpdateFeatures.md** | Fork-specific architecture deltas (e.g. witness path, Equihash API) |

**Zeronode_wallet.md:** Specialized note on **`CZeronodeWalletInterface`** / wallet-optional builds—most developers never touch it. **Placement:** (a) keep standalone near **`src/zeronode/`**, (b) fold into **UpdateZero** or **UpdateFeatures** as a section, or (c) move a short summary into **BUILD_ZERO** (“wallet-disabled build”) with detail in one maintainer file. Pick one on next doc pass.

### 1.4 What belongs where (summary)

| Content type | Primary home |
|--------------|----------------|
| Vision, community, links, “get started” | **README** |
| Compile, platform quirks, deterministic deps | **BUILD_ZERO** |
| Running tests, CI-like validation | **TEST_ZERO** |
| Checklists, known doc debt, small tasks | **TODO** |
| Subsidy math, halving tables, zeronode %, `MAX_MONEY` caveats, coin selection, RPC/operational depth | **ZERO_COIN** |
| Dependency version matrix, GTest exclusion archaeology | **UpdateBuild** / **UpdateTests** |
| Branch id / internal triage, release tags | **UpdateZero** |

---

## 2. Branch, version, validation

### 2.1 Worktree example

```bash
cd ~/Work/ZK/Zero400
git fetch origin
git stash push -m "WIP"   # if dirty
git checkout zero-merge
git pull --ff-only origin zero-merge
```

### 2.2 Version strings

Release identity in **`configure.ac`** (`_CLIENT_VERSION_*`, release build rules), generated **`src/config/bitcoin-config.h`**, and aligned fallbacks in **`src/clientversion.h`**. **Pinned dependency versions and upgrade rationale:** **UpdateBuild.md §1**.

### 2.3 Validation after a version bump

```bash
./autogen.sh
./configure --without-gui   # or your usual flags
make -j"$(nproc)" -C src zerod zero-cli zero-tx 2>&1 | tee build.log
./src/test/test_bitcoin --run_test=rpc_rawparams   # Boost smoke; adjust as needed
./src/zerod -version
```

Confirm **`zerod -version`** (or `getnetworkinfo` subversion) matches the intended release.

---

## 3. Consensus branch id and sighash

Overwinter+ transactions bind a **consensus branch id** into the **signature hash**. Two upgrades sharing the same **`nBranchId`** can create replay analysis complexity unless activation and tx versioning make signed payloads distinct.

**Zero:** In **`src/consensus/upgrades.cpp`**, **Sapling** and **Cosmos** both use **`0x7361707a`**. Document intent (deliberate vs oversight) in coin/release notes; optional build-time guard is **NU-01** (**§10**).

**Reference:** TENT (`ZKs/TENT/…`) reuses Zcash Sapling’s id for multiple named post-Sapling upgrades—a “no new sighash epoch” pattern with similar tooling risk if rule sets diverge.

| Action | Risk |
|--------|------|
| Document duplicate ids | None |
| CI: fail on duplicate active mainnet `nBranchId` without whitelist | Build-time only |
| New Cosmos `nBranchId` | Coordinated network upgrade |

---

## 4. Height and expiry types

**`TransactionBuilder::SetExpiryHeight`** (**`src/transaction_builder.cpp`**): chain height **`int`** vs expiry **`uint32_t`**. Mixed comparisons follow usual C++ promotion rules; negative height vs unsigned expiry is a footgun.

Audit **`nExpiryHeight`**, **`GetExpiryHeight`**, **`TX_EXPIRY_HEIGHT_THRESHOLD`**, and RPC height parsing at boundaries. Prefer explicit casts and a single signed policy (e.g. **`int64_t`**) for “any chain height” in new code.

**Tests:** Boundary cases (expiry vs height, zero expiry vs ZIP-203, threshold edges) belong in the test suite; see **UpdateTests.md** for harness limits.

---

## 5. Numeric policy

Consensus and subsidy paths should be **integer-only**; avoid silent float promotion. Default rounding for reward splits unless otherwise specified: **truncate toward zero**.

**NUM-01:** Audit **`main.cpp`**, **`miner.cpp`**, **`zeronode/payments.cpp`**, and similar for **`double`** / magic fractions; share helpers so validator and miner match.

---

## 6. Release artifacts and signing

**Scope:** This repo does not document Guix until adopted (**REL-HOST**).

- **Tag:** `vMAJOR.MINOR.PATCH`
- **Archives:** `Zero-<ver>-<target>-<triplet>.<ext>` (one naming scheme across channels)
- **Checksum file:** e.g. **`SHA256SUMS-<ver>.txt`** — use **one** convention everywhere; detached **`*.asc`** on the manifest if signing

**Practice:** GPG-sign the manifest on a single controlled host; add platform codesigning when distributing installers. Users verify with **`sha256sum -c`** and optionally **`gpg --verify`**.

**Params / bootstrap:** If mirroring **`fetch-params`** or publishing snapshots, ship hashes and signed manifests; describe in **BUILD_ZERO.md** (user-facing), not by naming this file.

---

## 7. C++ exceptions

Use **`throw std::runtime_error("…");`**, not **`throw new std::runtime_error(…)`**, so **`catch (const std::exception&)`** works. (**Java** `throw new` in bundled deps is unrelated.)

**This repo:** **`src/**/*.cpp`** cleanup applied on the current integration line for the usual hotspots (`transaction_builder.cpp`, `main.cpp`, `zcbenchmarks.cpp`, …).

---

## 8. Zeronode vs TENT masternode code

**Layout:** **`src/zeronode/*`** parallels Dash-style **`masternode/*`** (e.g. **`zeronodeman`**, **`activezeronode`**, **`swifttx`**, budget/payments).

**Iterator / sync map bug (expired broadcast cleanup):** Wrong order—increment iterator then use stale key for sync-map erase. **Zero** uses the safe order (erase sync by **`(*it).first`**, then advance). Re-verify **TENT** when porting.

**Further review:** Diff **`swifttx.cpp`**, **`budget.cpp`**, **`payments.cpp`** vs upstream forks for post-fork security fixes.

**Automated tests:** Zeronode RPC and gaps—**UpdateTests.md**.

---

## 9. Raw transaction RPC (#70)

Verbose **`getrawtransaction`** / **`decoderawtransaction`** use **`TxToJSONExpanded`**. **`size`** is present on the integration branch; **`fees`** deferred (spent index / shielded economics).

---

## 10. Tracking tags

| Tag | Topic |
|-----|--------|
| **REL-4.0.1** | Release validation (**§2.3**), **`throw new`** cleanup (**§7**), zeronode iterator (**§8**) |
| **NUM-01** | Integer subsidy audit (**§5**) |
| **NU-01** | Branch id documentation / optional CI (**§3**) |
| **REL-HOST** | Params mirror, bootstrap policy, checksums/signing (**§6**) |

---

## 11. Roadmap

**REL-4.0.1:** In-tree: version strings, **`throw new`** removal, zeronode **`CheckAndRemove`** fix. Open: run **§2.3**, optional stress/ASAN on zeronode paths (**UpdateTests.md**).

**Backlog**

| When | Items |
|------|--------|
| Ready | Branch-id doc (**§3**); release checklist (**§6**); user-facing doc rollout (**§12**) |
| Research | Expiry-at-zero semantics; **NUM-01** inventory; **§9** fees; **§8** fork diffs |
| Decision | **NU-01** CI rule; new Cosmos id; **REL-HOST** mirror ownership |

| Tag | Next step |
|-----|------------|
| **REL-4.0.1** | Close after **§2.3** + chosen optional zeronode smoke |
| **NUM-01** | Inventory then shared integer helpers |
| **NU-01** | Publish id intent; then CI or fork-level id change |
| **REL-HOST** | Assign manifest/mirror owner |

---

## 12. Documentation rollout (phased)

**Principle:** Shape **user-facing** docs first; then **delete or slim** maintainer docs so they only hold what cannot live publicly without confusion.

| Phase | Focus | Deliverables |
|-------|--------|--------------|
| **A** | **README** | Hero narrative; audiences (trade, mine, node, build, contribute); links to **ZERO_COIN**, **BUILD_ZERO**, **TEST_ZERO**, **TODO**, official web + social; no deep consensus prose. |
| **B** | **ZERO_COIN.md** | Create file; merge **`Subsidy.md`** + **`ZeroCoin.md`** content; add sections for operational technicalities (coin selection, fee/relay behavior pointers, key RPCs)—cited to code where needed. |
| **C** | **BUILD_ZERO** / **TEST_ZERO** / **TODO** | Align with **§1.2** roles; move any orphan technical ops from README into **BUILD_ZERO** or **ZERO_COIN**; keep **TODO** as the running checklist (including doc debt). |
| **D** | **Cutover** | README links only to **ZERO_COIN** for chain economics; deprecate or remove **`Subsidy.md`** / **`ZeroCoin.md`** after redirect note or single release cycle. |
| **E** | **Update\*** | Re-read **UpdateBuild** / **UpdateTests** / **UpdateFeatures**; strip paragraphs now duplicated in user docs; keep pins, test archaeology, and internal triage only. |
| **F** | **Zeronode_wallet** | Resolve placement (**§1.3**); if folded, leave a one-line pointer from **BUILD_ZERO** (`--disable-wallet`). |

**Online properties (outside repo):** GitHub org/repo description, website, Twitter/X, Reddit, Medium, Discord, Telegram should **mirror** README messaging and visuals after Phase **A**–**B** (see **§13.1**). Same vocabulary: ticker, tagline, links, download path.

---

## 13. Work items and tracking

Use **GitHub Issues** (or org project board) for execution; this section is the **index** of streams that need parallel owners.

### 13.1 External presence (content + visuals)

| Item | Notes |
|------|--------|
| GitHub org / repo | Description, topics, pinned README, release assets template |
| Website | Match README CTAs; download + docs links |
| Twitter/X, Reddit, Medium | Tone and facts consistent with **ZERO_COIN** / README |
| Discord, Telegram | Moderation and pinned “official links” |
| Brand kit | Logo, colors, screenshots—single source for all channels |

### 13.2 Issues, limits, fork / deployment impact

Triage in a dedicated milestone or label set:

| Category | Examples | Typical impact |
|----------|----------|----------------|
| **Non-consensus bugfix** | RPC errors, logging, build | Node release only; no chain fork |
| **Consensus / fork** | Branch id change, subsidy rule change | Network upgrade, version gate, comms |
| **Index / explorer** | API schema, reindex | Explorer redeploy; optional full reindex |
| **Wallets** | zerowallet vs node RPC drift | Wallet release + user notice |
| **Open questions** | `MAX_MONEY` vs emission, alert system fate | Doc in **ZERO_COIN** / **TODO** until resolved |

Pull **UpdateTests** exclusions, **TODO** items, and **GitHub Issues** into one filtered view: *needs fork*, *needs explorer restart*, *needs wallet update*, *doc only*.

### 13.3 macOS builds: Developer-level support

| Item | Notes |
|------|--------|
| Apple Developer Program | Certificates for signing **zerod** / **zero-cli** / app bundles as product dictates |
| Notarization + stapling | Required for Gatekeeper-friendly distribution on current macOS |
| Hardened runtime / entitlements | As needed for binaries that use JIT, DYLD, or helpers |
| **BUILD_ZERO** | Document what Apple expects from **users** vs what **release** builds provide |

### 13.4 This file as hub

**UpdateZero.md** holds the **documentation map**, **rollout phases**, and **tracking index**. Detailed specs belong in **ZERO_COIN**, **BUILD_ZERO**, Issues, or runbooks—not duplicated here.
