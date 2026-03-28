# UpdateZero

Project hub for the Zero full-node repo: documentation map, integration branch, consensus and release notes, and cross-cutting work tags.

**Branch convention:** Integration work targets **`zero-merge`**. Side branches (e.g. naming spikes) are not release branches unless tagged.

**Section map:** **§1** documentation map & strategy · **§2** branch & version · **§3** consensus branch id · **§4** height / expiry · **§5** numeric policy · **§6** release artifacts · **§7** C++ exceptions · **§8** zeronode / TENT · **§9** raw RPC (#70) · **§10** tracking tags · **§11** roadmap · **§12** documentation rollout (phased) · **§13** work items & external alignment (**§13.5** decisions / dedupe index)

---

## 1. Documentation map and strategy

### 1.1 Goal

Move **as much information as is reasonable** into **user-facing** documents so builders, operators, and integrators do not need maintainer-only files. **README** stays **short and inviting**; depth lives in **BUILD_ZERO**, **TEST_ZERO**, **TODO**, and a single **detailed coin/chain** document.

### 1.2 User-facing layer — no `Update*.md` pointers

**Full index:** **[README.md](README.md)** (Documentation section). **Definitive user-facing** subset for agents: **[AGENTS.md](AGENTS.md)**—narrower than the README map.

These **must not** hyperlink, name, or cite section labels of any **`Update*.md`** file: the **AGENTS.md** list, plus **README.md**, **Zeronode_wallet.md**, and any other doc the README map treats as user-facing. **README0.md** is **not** in that set (temporary README draft). **Subsidy.md** is legacy reference being split and retired—still avoid **`Update*`** pointers if it remains published briefly.

| Doc | Audience | Role |
|-----|----------|------|
| **README.md** | Broad: investors, traders, miners, node runners, contributors | **Front page:** what Zero is, CTAs, **full documentation map** |
| **BUILD_ZERO.md** | Builders and operators who compile or deploy | Install, depends, platforms, troubleshooting, release-style artifacts users touch |
| **TEST_ZERO.md** | Builders and contributors | Runners, modes, pass-only filters, Tier A gate, **`full_test_suite.py`**; bulk RPC names in **`rpc-tests.sh`**; known failures / plan; fork-specific harness notes |
| **CONTRIBUTING.md** | Contributors | Patches, review, workflow |
| **TODO.md** | Maintainers + contributors | Actionable checklist; **BUILD_ZERO** / chain-doc targets |
| **ZERO_COIN.md** | Operators, integrators | User-observable chain/node behavior and events; **Glossary** / **References** |
| **ZeroCoin.md** | Editors merging content | **Outline** until folded into **ZERO_COIN.md** |
| **Zeronode_wallet.md** | Developers on zeronode↔wallet | Interface, wallet-optional builds, coverage notes |
| **Subsidy.md** | Legacy readers | Technical subsidy/supply reference; **splitting** into **ZERO_COIN** and elsewhere, then **retired**—see README map |
| **Man pages** (`doc/man/`) | CLI users | Match shipped binaries; deep flags here or in **BUILD_ZERO** |
| **ZERO_COIN.md** (target) | Serious users, pools, exchanges, integrators | Replaces long economics blocks; **user-observable** behavior and events only—no **`Update*`** pointers when added |

**Migration:** Add **`ZERO_COIN.md`** from **user-observable** material in **`Subsidy.md`** and the outline in **`ZeroCoin.md`**. Move **implementation detail**, **code pointers**, and **rationale / future-enhancement planning** to **UpdateZero** on redo, a **standalone maintainer subsidy note**, or keep them only in **`Subsidy.md`**—see **TODO.md** item **ZERO_COIN vs maintainer docs — scope split and Subsidy disposition**. Then trim **`ZeroCoin.md`** and decide **`Subsidy.md`** cutover. **README** should eventually point to **ZERO_COIN** for how the chain **behaves**.

### 1.3 Maintainer and engineering layer — Update* index

Canonical list of maintainer/developer documentation. **§1.2** applies: user-facing guides do **not** name or link these files.

| Doc | Role (current; may shrink as user docs absorb content) |
|-----|----------------------------------------------------------|
| **UpdateZero.md** | Documentation map, branch/version, consensus notes, release process, tags, **§12–§13** rollout and tracking |
| **UpdateBuild.md** | Peer dep snapshot, in-tree build archaeology, deferred upgrades (pins: **BUILD_ZERO** §4); cross-project dependency comparison for porters. Canonical version pin matrix: **BUILD_ZERO.md** §4.1 (**§1.4**). |
| **UpdateTests.md** | PM / architect / implementer / maintainer | Exclusions, harness notes, coverage gaps and backlog, CSV / rescan inventories; **TEST_ZERO.md** is the only execution runbook |
| **UpdateFeatures.md** | Fork-specific architecture deltas (e.g. witness path, Equihash API) |

**Zeronode_wallet.md:** Specialized note on **`CZeronodeWalletInterface`** / wallet-optional builds—most developers never touch it. **Placement:** (a) keep standalone near **`src/zeronode/`**, (b) fold into **UpdateZero** or **UpdateFeatures** as a section, or (c) move a short summary into **BUILD_ZERO** (“wallet-disabled build”) with detail in one maintainer file. Pick one on next doc pass.

### 1.4 What belongs where — summary

| Content type | Primary home |
|--------------|----------------|
| Vision, community, links, “get started” | **README** |
| Compile, platform quirks, deterministic deps | **BUILD_ZERO** |
| Running tests, CI-like validation | **TEST_ZERO** |
| Checklists, known doc debt, small tasks | **TODO** |
| Observable subsidy/halving/zeronode figures, event timelines, ports, config patterns, user-facing operational depth | **ZERO_COIN** |
| Code pointers, `MAX_MONEY` / validation caveats, design rationale, enhancement planning tied to subsidy | **UpdateZero** redo, **Subsidy.md** maintainer layer, or standalone technical note |
| Dependency version matrix (canonical) | **BUILD_ZERO** §4.1 · Peer comparison: **UpdateBuild** §5 · GTest archaeology: **UpdateTests** |
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

Release identity in **`configure.ac`** (`_CLIENT_VERSION_*`, release build rules), generated **`src/config/bitcoin-config.h`**, and aligned fallbacks in **`src/clientversion.h`**. **Pinned dependency versions and upgrade rationale:** **BUILD_ZERO.md** §4.1; deferred queue **UpdateBuild.md** §4.

### 2.3 Validation after a version bump

Build and smoke steps: **BUILD_ZERO.md**; test pass and expectations: **TEST_ZERO.md**. Confirm **`zerod -version`** (or `getnetworkinfo` subversion) matches the intended release.

---

## 3. Consensus branch id and sighash

Overwinter+ transactions bind a **consensus branch id** into the **signature hash**. Two upgrades sharing the same **`nBranchId`** can create replay analysis complexity unless activation and tx versioning make signed payloads distinct.

**Zero:** In **`src/consensus/upgrades.cpp`**, **Sapling** and **Cosmos** both use **`0x7361707a`**.

**Maintainer decision:** **No branch-id change** and **no network fork** for Cosmos vs Sapling separation **for now**. Treat duplicate **`nBranchId`** as **accepted technical debt**: document user-visible / integrator implications in **ZERO_COIN** / release notes when those docs land; reassess only with a deliberate **NU** upgrade. **NU-01** (**§10**) shrinks to **documentation + monitoring**, not an active fork ticket.

**Reference:** TENT (`ZKs/TENT/…`) reuses Zcash Sapling’s id for multiple named post-Sapling upgrades—a “no new sighash epoch” pattern with similar tooling risk if rule sets diverge.

| Action | Risk |
|--------|------|
| Publish intent and replay posture in user docs | None |
| CI: fail on duplicate active mainnet `nBranchId` without whitelist | Build-time only; optional |
| New Cosmos `nBranchId` | **Deferred** — coordinated network upgrade only when scheduled |

---

## 4. Height and expiry types

**`TransactionBuilder::SetExpiryHeight`** (**`src/transaction_builder.cpp`**): chain height **`int`** vs expiry **`uint32_t`**. Mixed comparisons follow usual C++ promotion rules; negative height vs unsigned expiry is a footgun.

Audit **`nExpiryHeight`**, **`GetExpiryHeight`**, **`TX_EXPIRY_HEIGHT_THRESHOLD`**, and RPC height parsing at boundaries. Prefer explicit casts and a single signed policy (e.g. **`int64_t`**) for “any chain height” in new code.

**Tests:** Boundary cases (expiry vs height, zero expiry vs ZIP-203, threshold edges) belong in the test suite; runbook **TEST_ZERO.md**; harness limits **UpdateTests.md** §4.

---

## 5. Numeric policy

Consensus and subsidy paths should be **integer-only**; avoid silent float promotion. Default rounding for reward splits unless otherwise specified: **truncate toward zero**.

**NUM-01 — breadth (not two lines in `main.cpp` only):**

1. **Inventory:** Grep **`double`**, **`float`**, and fractional literals (**`0.075`**, **`10.8 * COIN`**, **`/ 100.0`**, etc.) under **`src/`**, prioritizing **`main.cpp`**, **`miner.cpp`**, **`zeronode/payments.cpp`**, **`consensus/`**, **`wallet/`** fee and reward paths.
2. **Pairing:** For each **subsidy / founders / zeronode / miner** split, locate **both** validation and mining paths; prove **identical integer semantics** (same rounding direction and order of operations).
3. **Helpers:** Centralize splits as **`CAmount` math** (e.g. **`a * b / c`** with **`int64_t`** widened where needed); ban **new** float in consensus-critical paths unless reviewed.
4. **Tests:** Add **regression** cases for **far-future halving** heights (see external review in **`zero_errs.txt`**: founder fraction **×** subsidy can become non-integer in **`double`**); property-style checks that miner and **`ConnectBlock`** agree per height.
5. **Emission narrative:** Reconcile **documented** total issue / splits with code after refactors (**community / miner / dev / zeronode** adjustments)—**UpdateZero** tracks policy; **ZERO_COIN** will state user-observable numbers.

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

**This repo:** **`throw new`** in **`src/**/*.cpp`** has been **removed** (integration line). Historical risk was **`std::terminate`** if a **`throw new`** path fired and only **`catch (const std::exception&)`** existed.

**Coverage testing:** For remaining **`throw std::runtime_error`** (and similar) on **real validation paths**:

- **Unit / GTest / Boost:** Call the **C++ function** or **wrapper** with inputs that violate the guard; use **`EXPECT_THROW(..., std::runtime_error)`** or **`ASSERT_THROW`** (or catch and inspect **`what()`**). No need to **`throw new`** to test—only the **branch** must be reachable.
- **RPC / integration:** **`CheckRPCThrows`**-style tests (Boost) or Python RPC tests that expect **`JSONRPCException`** map the same logic when the error crosses the RPC boundary.
- **Benchmarks / dead branches:** If a check lives only in **`zcbenchmarks.cpp`** or rarely used code, add a **small unit test** that forces the condition **or** document intentional non-coverage.

**Mocks:** Where setup is heavy (full **`CChain`**, wallet), use **minimal fixtures** (fake height, empty view) already common in **`src/test/`**—no special “mock **`throw new`**” machinery.

---

## 8. Zeronode vs TENT masternode code

**Layout:** **`src/zeronode/*`** parallels Dash-style **`masternode/*`** (e.g. **`zeronodeman`**, **`activezeronode`**, **`swifttx`**, budget/payments).

**Iterator / sync map bug (expired broadcast cleanup):** Wrong order—increment iterator then use stale key for sync-map erase. **Zero** uses the safe order (erase sync by **`(*it).first`**, then advance). Re-verify **TENT** when porting.

**`CZeronodeBroadcast::CheckAndVerify` — short active chain / null `chainActive` entry:**

After **`GetInputAge` ≥ `ZERONODE_MIN_CONFIRMATIONS`**, the code loads the collateral tx block (**`pMNIndex`**) and then:

```cpp
CBlockIndex* pConfIndex = chainActive[pMNIndex->nHeight + ZERONODE_MIN_CONFIRMATIONS - 1];
if (pConfIndex->GetBlockTime() > sigTime) { ... }
```

**`CChain::operator[]`** returns **`NULL`** when the height is **out of range** (**`chain.h`**: `nHeight < 0 || nHeight >= (int)vChain.size()`). If the **active chain** is shorter than **`pMNIndex->nHeight + ZERONODE_MIN_CONFIRMATIONS`** (e.g. **reorg**, **IBD**, **regtest** with few blocks, or inconsistent **`mapBlockIndex` / chainActive** state), **`pConfIndex`** is **null** and **`pConfIndex->GetBlockTime()`** is **undefined behavior** (typically **segfault**).

**Faulty execution (conceptual):** `pMNIndex->nHeight == H`, **`chainActive.Height() == H + k`** with **`k < ZERONODE_MIN_CONFIRMATIONS - 1`** → index **`H + ZERONODE_MIN_CONFIRMATIONS - 1`** is **≥ vChain.size()** → **NULL** → crash on **`GetBlockTime()`**. A peer can trigger **`CheckAndVerify`** with a crafted **`znb`** only when collateral depth checks pass—**short-chain** cases matter most on **new nodes** and **testnets**.

**Applicability — when this matters in practice**

- **Steady-state mainnet** with a **single consistent** view of **`chainActive`** and **`GetInputAge`**: if **`GetInputAge`** truly reflects depth on the **same** active chain as **`pMNIndex`**, the needed height is usually **already** on **`chainActive`** once **`GetInputAge ≥ ZERONODE_MIN_CONFIRMATIONS`**. The bug is **defensive**: it closes a gap if those views **diverge** (race, bug, or test harness).
- **High relevance:** **Regtest** / **custom harnesses** that tweak **`mapBlockIndex`**, **`chainActive`**, or confirmation counting **independently**; **IBD** or **reorg** windows where **`GetTransaction` / `mapBlockIndex`** can reference a block **not yet** at the expected offset on **`chainActive`**; **fuzzing** or **partial** chain state.
- **Risk shape:** **Local crash** (NULL deref) on the node processing the broadcast, not a consensus divergence—still worth fixing for **robustness** and **CI**.

**Mitigation:** **`if (!pConfIndex) return false;`** (and log) before use; optional **`assert`** in debug. Add a **regtest** RPC or unit test that announces a zeronode when **`chainActive`** is **just** long enough for **`GetInputAge`** but **not** for the **`pConfIndex`** height.

**Further review:** Diff **`swifttx.cpp`**, **`budget.cpp`**, **`payments.cpp`** vs upstream forks for post-fork security fixes.

**Automated tests:** How to run—**TEST_ZERO.md**; zeronode RPC gaps and exclusions—**UpdateTests.md**.

---

## 9. Raw transaction RPC — issue 70

Verbose **`getrawtransaction`** / **`decoderawtransaction`** use **`TxToJSONExpanded`**. **`size`** is present on the integration branch; **`fees`** deferred (spent index / shielded economics).

---

## 10. Tracking tags

| Tag | Topic |
|-----|--------|
| **REL-4.0.1** | Release validation (**§2.3** → **BUILD_ZERO** / **TEST_ZERO**), **`throw new`** cleanup (**§7**), zeronode iterator (**§8**) |
| **NUM-01** | Integer subsidy audit (**§5**) |
| **NU-01** | Sapling/Cosmos **duplicate `nBranchId`** — document posture (**§3**); optional CI guard only |
| **REL-HOST** | Params mirror, bootstrap policy, checksums/signing (**§6**) |

---

## 11. Roadmap

**REL-4.0.1:** In-tree: version strings, **`throw new`** removal, zeronode **`CheckAndRemove`** fix. Open: run **§2.3** (**BUILD_ZERO** / **TEST_ZERO**), optional stress/ASAN on zeronode paths (**UpdateTests.md**).

**Backlog**

| When | Items |
|------|--------|
| Ready | Branch-id doc (**§3**); release checklist (**§6**); user-facing doc rollout (**§12**) |
| Research | Expiry-at-zero semantics; **NUM-01** inventory; **§9** fees; **§8** fork diffs |
| Decision | **NU-01** optional CI guard; **REL-HOST** mirror ownership; **Cosmos id change deferred** (**§3**) |

| Tag | Next step |
|-----|------------|
| **REL-4.0.1** | Close after **§2.3** + chosen optional zeronode smoke |
| **NUM-01** | Inventory then shared integer helpers |
| **NU-01** | Publish duplicate-id / replay posture in **ZERO_COIN**; optional CI whitelist |
| **REL-HOST** | Assign manifest/mirror owner |

---

## 12. Documentation rollout — phased

**Principle:** Shape **user-facing** docs first; then **delete or slim** maintainer docs so they only hold what cannot live publicly without confusion.

| Phase | Focus | Deliverables |
|-------|--------|--------------|
| **A** | **README** | Hero narrative; audiences (trade, mine, node, build, contribute); links to **ZERO_COIN**, **BUILD_ZERO**, **TEST_ZERO**, **TODO**, official web + social; no deep consensus prose. |
| **B** | **ZERO_COIN.md** | Create file; merge **`Subsidy.md`** + **`ZeroCoin.md`** content; add sections for operational technicalities (coin selection, fee/relay behavior pointers, key RPCs)—cited to code where needed. |
| **C** | **BUILD_ZERO** / **TEST_ZERO** / **TODO** | Align with **§1.2** roles; move any orphan technical ops from README into **BUILD_ZERO** or **ZERO_COIN**; keep **TODO** as the running checklist (including doc debt). |
| **D** | **Cutover** | README links only to **ZERO_COIN** for chain economics; deprecate or remove **`Subsidy.md`** / **`ZeroCoin.md`** after redirect note or single release cycle. |
| **E** | **Update\*** | Re-read **UpdateBuild** / **UpdateTests** / **UpdateFeatures**; strip paragraphs now duplicated in user docs; keep peer snapshot, source-tree archaeology, and internal triage only (pins: **BUILD_ZERO** §4). |
| **F** | **Zeronode_wallet** | Resolve placement (**§1.3**); if folded, leave a one-line pointer from **BUILD_ZERO** (`--disable-wallet`). |

**Online properties (outside repo):** GitHub org/repo description, website, Twitter/X, Reddit, Medium, Discord, Telegram should **mirror** README messaging and visuals after Phase **A**–**B** (see **§13.1**). Same vocabulary: ticker, tagline, links, download path.

---

## 13. Work items and tracking

**Tracking policy:** Work is tracked **in-repo** (**`TODO.md`**, **`UpdateTests.md`**, **`TEST_ZERO.md`**, this file) while change velocity and investigation depth are high. **GitHub Issues** are **deferred** to a later cycle so issue hygiene does not slow development; when adopted, mirror the same categories below.

### 13.1 External presence — content and visuals

| Item | Notes |
|------|--------|
| GitHub org / repo | Description, topics, pinned README, release assets template |
| Website | Match README CTAs; download + docs links |
| Twitter/X, Reddit, Medium | Tone and facts consistent with **ZERO_COIN** / README |
| Discord, Telegram | Moderation and pinned “official links” |
| Brand kit | Logo, colors, screenshots—single source for all channels |

### 13.2 Categories, limits, fork / deployment impact

Use this table for **prioritization** and **release notes**; record concrete items in **`TODO.md`** or **`UpdateTests.md`** / **`TEST_ZERO.md`** until Issues are in use.

| Category | Examples | Typical impact |
|----------|----------|----------------|
| **Non-consensus bugfix** | RPC errors, logging, build | Node release only; no chain fork |
| **Consensus / fork** | Branch id change, subsidy rule change | Network upgrade, version gate, comms |
| **Index / explorer** | API schema, reindex | Explorer redeploy; optional full reindex |
| **Wallets** | zerowallet vs node RPC drift | Wallet release + user notice |
| **Open questions** | `MAX_MONEY` vs emission, alert system fate | Doc in **ZERO_COIN** / **TODO** until resolved |

### 13.3 macOS builds: Developer-level support

| Item | Notes |
|------|--------|
| Apple Developer Program | Certificates for signing **zerod** / **zero-cli** / app bundles as product dictates |
| Notarization + stapling | Required for Gatekeeper-friendly distribution on current macOS |
| Hardened runtime / entitlements | As needed for binaries that use JIT, DYLD, or helpers |
| **BUILD_ZERO** | Document what Apple expects from **users** vs what **release** builds provide |

### 13.4 This file as hub

**UpdateZero.md** holds the **documentation map**, **rollout phases**, and **tracking index**. Detailed specs belong in **ZERO_COIN**, **BUILD_ZERO**, or runbooks—not duplicated here.

### 13.5 Recorded decisions, external findings, and doc index

Single place to **deduplicate** ad-hoc notes (**`zero_errs.txt`**, staff review, CI work). **Execution** is **`TODO.md`** + harness docs until **GitHub Issues** are adopted (**§13** intro).

| Topic | Decision / status | Where detailed |
|-------|-------------------|----------------|
| **OpenSSL** | Stay on **1.1.1w** in **`depends`** until an **audited** **3.x** migration (or removal). | **BUILD_ZERO.md** §4.1, **UpdateBuild.md** |
| **Sapling / Cosmos `nBranchId`** | **Keep `0x7361707a` for both**; **no fork** to split IDs **for now**. Document posture for users/integrators. | **§3**, tag **NU-01** |
| **Rust / `librustzcash`** | Use **system `rustc` / `cargo` on `PATH`** on **macOS** and **Linux** (e.g. **1.91.x**); **depends** toolchain where the recipe still requires it (e.g. some **Windows** / cross builds). | **BUILD_ZERO.md** §4.1 / §4.9 |
| **Floating-point in consensus** | **NUM-01:** **broad** integer audit and paired miner/validator tests—not only two lines in **`main.cpp`**. | **§5** |
| **Historical `throw new`** | **Removed** from **`src/**/*.cpp`**. Cover **`throw std::runtime_error`** branches with **unit / RPC** tests (**§7**). | **§7** |
| **Zeronode `chainActive[]` null** | **Open bug pattern:** **`zeronode.cpp`** may deref **NULL** **`pConfIndex`** on short **active** chain (**§8**). | **§8**, **`TODO.md`** |
| **Qt wallet `std::cout` leak** | **Not in this repo.** Finding targeted **`wallet/src/rpc.cpp`** (Qt **zerowallet** tree). | **zerowallet** repo |
| **Params / `fetch-params.sh`** | Mirror URLs, naming, **`download.z.cash`** dependency — **REL-HOST** / **TODO.md** (`fetch-params` item). | **§6**, **TODO.md**, **BUILD_ZERO** when mirrored |

**Test harness backlog:** **`TEST_ZERO.md`** (**Known failures**, **Verification snapshot**, **Harness changelog**), **`UpdateTests.md`** (IDs **4.x–6.x** including **6.7** parallel Tier A, P1–P4). Do not duplicate those tables here.
