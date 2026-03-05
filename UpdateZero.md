# UpdateZero

This document tracks the Zero node update and stabilization effort. Zero is a Zcash-family cryptocurrency node (C++/Rust) targeting Windows (primary user deployment), Linux (VPS and validation), and macOS including Apple Silicon. Scope is the full node repo only; zerowallet is out of scope.

UpdateZero assembles status, open items, long-term plans, gotchas, and gaps. TODO.md holds user-facing items already decided for implementation.

---

## Documentation Split

Canonical declaration. User-facing docs must never reference project docs. Project docs may reference each other and user-facing docs.

| Group | Files | Audience |
|-------|-------|----------|
| **User-facing** | README.md, BUILD_ZERO.md, TEST_ZERO.md, CONTRIBUTING.md, TODO.md | Contributors, users building/running Zero. Current state only; no future plans. |
| **Project** | UpdateZero.md, UpdateBuild.md, UpdateTests.md, UpdateFeatures.md, Zeronode_wallet.md, Subsidy.md, doc/files.md | Maintainers, status tracking, design decisions, plans, futures. |

CONTRIBUTING and README state placement rules only; neither mentions project docs.

---

## 1. Project Documentation Map

```
                    UpdateZero (hub)
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
  UpdateBuild       UpdateTests      UpdateFeatures
  (build, depends,  (suites, fixes,  (architecture,
   platform setup)   procedures)     cross-fork)
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
  Zeronode_wallet     Subsidy          doc/files
  (wallet interface)  (halving,        (data dir)
                       subsidy)
```

| Document | Scope |
|----------|-------|
| **UpdateZero** | Status, open items, plans, gotchas, in-code TODOs |
| **UpdateBuild** | Build system, depends, platform setup, library versions |
| **UpdateTests** | Test suites, results, fixes, procedures |
| **UpdateFeatures** | Architecture, production code, cross-fork analysis |
| **Zeronode_wallet** | Wallet abstraction for zeronode |
| **Subsidy** | Block subsidy, halving algorithm |
| **doc/files** | Data directory layout |
| **ZKs/Comparison** | Cross-project: difficulty, Equihash, toolchain (outside repo) |
| **TODO** | User-facing items with design and timelines |
| **BUILD_ZERO** | User-facing build guide (README → BUILD_ZERO) |
| **TEST_ZERO** | User-facing test procedures (README → TEST_ZERO) |

### Content placement policy

Place content in the document whose scope it matches. Avoid duplication: reference other docs (e.g. "See UpdateBuild §5") rather than repeating. Remove content when it becomes obsolete or moves elsewhere. Update\*.md files may reference each other; user-facing docs must not reference Update\* or other project docs.

**Level of detail:** User-facing docs cover at a level appropriate for users (how to run, troubleshoot, fix). Project docs add content only when there is significant additional, non-duplicate, lasting project information (design, status, cross-fork, implementation notes). If user-facing covers it adequately, do not duplicate in project docs.

**Documentation examples:** Do not add optional arguments to examples unless they demonstrate a specific point (e.g. override, glitch workaround). When describing mkrelease-*.sh or similar packaging scripts, include remarks on versions (APP_VERSION source, inferability) and sizes (zerod, artifacts) where relevant.

### Update and partition rules (prevent gaps like #70)

When fixing code or changing behavior: (1) Update the project doc that owns that scope — UpdateBuild (depends, build), UpdateTests (suites, procedures), UpdateFeatures (architecture), UpdateZero (status, TODOs). (2) If an item is in §5 (Filed/Referenced Issues) or an Open Question, mark it Done or update notes when fixed. (3) Remove or archive obsolete TODO text; do not leave "TODO" for completed work. (4) Partition: each doc has clear scope; avoid cross-doc duplication; when in doubt, put in UpdateZero and reference from others.

### Workflows

| Workflow | Where to look |
|----------|---------------|
| **Investigate a bug** | §5 (Documented Bugs, In-Code TODOs); UpdateTests §4 (per-suite failures); UpdateFeatures §1 (witness fixes) |
| **Plan a new feature** | §4 (Open Items, prioritization); UpdateFeatures (architecture constraints); TODO |
| **Track project status** | §3 (Status Summary); §4 (Open Items); §7 (Direction) |
| **Run or debug tests** | UpdateTests §3 (runners, invocation); §4 (per-suite status); §6 (notes) |
| **Build on new platform / upgrade dependency** | UpdateBuild §2 (platform setup); §3 (depends); §5 (version table) |
| **Compare difficulty / Equihash / toolchain across forks** | ZKs/Comparison.md (§1 Difficulty, §5 Equihash & PoW, §4 Toolchain) |

## 2. Branch

- **Main line**: `zero-merge`. Future work: branch from and merge into `zero-merge`.
- **Legacy/feature branches**: `arm-mac-build` (ARM Mac), `mac_linux_boost188` (Boost 1.88), `p3-tests` (Python 3 migration, incomplete). These were based on `origin/zeronode_wallet` or `origin/master`; reconcile into `zero-merge` as needed.
- Remote: `https://github.com/zerocurrencycoin/Zero`
- Workflow: Do not push or merge to upstream. Commit to feature branches; merge to `zero-merge`.

### 2.2 Update other Zero repo instances

```bash
cd /path/to/other/Zero
git fetch origin
git checkout zero-merge
git pull origin zero-merge
```

### 2.3 Cursor configuration (documented; resolution delayed)

**Current:** Zero and zerowallet each have `.cursor/rules/mainline-branches.mdc` (alwaysApply: true). Zero has CLAUDE.md; zerowallet does not.

**Issues to resolve (later):** (1) Rule placement: local vs project vs repo vs user; which directions go where. (2) AGENTS.md: neither repo has it; decide if needed. (3) Harmonization: rules, CLAUDE.md, AGENTS.md across Zero and zerowallet. (4) Duplication: mainline-branches.mdc identical in both repos; consider shared or single source. (5) File-specific rules: none yet; globs for *.cpp, *.sh, etc. not defined.

### 2.4 Versioning (locations, values, influences)

| Type | Repo | Location | Value | Influence |
|------|------|----------|-------|-----------|
| **APP_VERSION** | zerowallet | `src/version.h` | `"4.0.0"` | zerowallet UI, mkrelease artifacts |
| **CLIENT_VERSION** | Zero | `configure.ac` → `bitcoin-config.h` | 4.0.0 (4000050) | RPC `version`; subversion string |
| **CLIENT_NAME** | Zero | `src/clientversion.cpp` | `"Gaua"` | P2P subversion; RPC `subversion` |
| **PROTOCOL_VERSION** | Zero | `src/version.h` | 170009 | Serialization; P2P; zeronode; RPC |
| **MIN_PEER_PROTO_VERSION** | Zero | `src/version.h` | 170007 | Peer disconnect threshold |
| **MIN_PEER_PROTO_VERSION_ENFORCEMENT** | Zero | `src/version.h` | 170008 | `ActiveProtocol()`; zeronode payments |
| **vUpgrades[].nProtocolVersion** | Zero | `src/chainparams.cpp` | 170002–170009 | Per-epoch peer rejection |
| **walletversion** | Zero | `CWallet::GetVersion()` | 10500+ | Wallet DB format; RPC `getinfo` |

**zerowallet:** `APP_VERSION` in `zerowalletmac/src/version.h`. Used by `mainwindow.cpp`, `main.cpp`, `rpc.cpp`, `websockets.cpp`, mkrelease scripts. zerowallet displays node values (CLIENT_NAME, CLIENT_VERSION, PROTOCOL_VERSION, walletversion) via RPC; it does not set them.

**Inter-node P2P implications**

- **PROTOCOL_VERSION (170009):** Sent in `version` message; used in `ssSend.SetVersion(min(peer, PROTOCOL_VERSION))` so both peers use the lower version for wire messages. Bumping to 170010 alone: backward compatible (min() keeps 170009 with existing peers). Bumping with a new `vUpgrades` entry: enables new epoch; peers below that `nProtocolVersion` are rejected.
- **MIN_PEER_PROTO_VERSION (170007):** `main.cpp` disconnects peers with `nVersion < 170007`. Raising excludes older nodes.
- **MIN_PEER_PROTO_VERSION_ENFORCEMENT (170008):** Returned by `ActiveProtocol()`. Used by zeronode payments (`zeronode/payments.cpp`), budget (`zeronode/budget.cpp`), sync (`zeronode/zeronode-sync.cpp`). Zeronodes require `protocolVersion >= ActiveProtocol()`. Raising excludes older zeronodes from governance.
- **vUpgrades[].nProtocolVersion:** `main.cpp` rejects peers with `nVersion < vUpgrades[currentEpoch].nProtocolVersion`. To bump to 170010, add a new upgrade in `chainparams.cpp` with `nProtocolVersion = 170010` and `nActivationHeight`; otherwise 170010 has no effect.
- **CLIENT_NAME:** `contrib/seeds/makeseeds.py` `PATTERN_AGENT` must match (currently `/Gaua:.../`).

**Node internals**

- **PROTOCOL_VERSION:** Passed to `CDataStream`, `GetSerializeSize`, `CHashWriter` for blocks, tx, addresses, keys, witnesses, zeronode data. Serialization format depends on it; changing it can break parsing of data produced by other nodes or stored on disk.
- **walletversion:** Wallet DB schema; `SetMinVersion`/`SetMaxVersion` control feature flags. Independent of P2P.

**Unit and validation tests**

- **PROTOCOL_VERSION:** Used in serialize, bloom, policyestimator, transaction, block, pmt, alert tests. Tests assume current format; bumping may require regenerating fixtures (e.g. `alert_tests.raw`).
- **CLIENT_NAME:** `alert_tests.cpp` uses `FormatSubVersion(CLIENT_NAME, ...)`. Alert system deprecated; raw data may need regeneration if CLIENT_NAME changes.

## 3. Status Summary

### 3.1 Build

| Platform | Status | Notes |
|----------|--------|-------|
| Linux x86_64 | Untested with current changes | Base branch builds on Linux. Primary dev and validation platform. |
| Windows | See BUILD_ZERO §2.4 | Primary user deployment platform. MinGW cross-compile from Linux. |
| macOS ARM64 | Working | All binaries produced. Host triplet from config.guess (e.g. aarch64-apple-darwin25.3.0). |
| macOS x86 | Not supported | EOL; not verified. |

Build changes target ARM Mac enablement but touch shared infrastructure
(download URLs, sed portability). Linux and Windows regression required
before merge.

### 3.2 Tests

GTest 201 pass, 5 excluded. Boost 47 suites pass (3 excluded). RPC Python
19 pass (verified). Run `contrib/run-tests.sh`; logs go to `test-logs/`.
Details: **UpdateTests** §4.

### 3.3 Features

Production code fixes in `wallet.cpp` and `wallet.h`: three null-dereference
bugs and one cache-size bug in Zero's custom witness functions. Pre-existing
bugs also present in HUSH3.

## 4. Open Items by Module (Prioritized)

### 4.1 P1 — Immediate

| Module | Item | Notes |
|--------|------|-------|
| Build | Platform regression | Verify build and pass on Linux x86_64, Windows |
| Tests | Fix-now items | Skip-logic instances (rate as fail, not run): get_coinbase_address, getchaintips, clean-chain amounts, protocol version; PYTHON_PASSING omits scripts. See UpdateTests §4.8.1. z_getnewaddress extra-args fix applied. |

### 4.2 P2 — Delayed

| Module | Item | Notes |
|--------|------|-------|
| Dependencies | OpenSSL | Settled on 1.1.1w (final 1.1.1 LTS). Migration to 3.x postponed. |
| Dependencies | Rust | Prefer system Rust when recent enough (e.g. 1.70+); avoid undue pinning in depends for Linux/Windows. macOS ARM64: rust.mk symlinks system (no aarch64-apple-darwin in 1.32.0). |
| Tests | Failing tests | GTest CachedWitnesses*, WriteCryptedSaplingZkey; Boost Alert, equihash, miner; RPC Python get_coinbase_address, clean-chain amounts. |

### 4.3 P3 — Deferred

| Module | Item | Notes |
|--------|------|-------|
| Zeronode | Test suite | RPC param/read-only: partial (rpc_zeronode_tests, rpc_zeronode_budget_tests). Logic/integration: 0%. See UpdateTests §11.4. |
| Zeronode | Enhanced error handling | Replace boolean returns in zeronode wallet interface with detailed error reporting. Optional enhancement; design complete. |

### 4.4 P4 — Set Aside

| Module | Item | Notes |
|--------|------|-------|
| Tests | WriteCryptedSaplingZkeyDirectToDb | CDB::Rewrite deadlock; first wallet never closed. Excluded. |
| Tests | Alert_tests | Deprecated; raw data MagicBean-specific. |
| Tests | equihash_tests, miner_tests | Zero (192,7) vs test (96,5); excluded. |
| Tests | get_coinbase_address impl gap | listunspent with generated returns empty when nuparams activate early. Skip; fix would need Zero listunspent/generated behavior. |

### 4.5 Open Questions / Pending

**Note:** TODO.md will be updated later.

| Item | Status | Notes |
|------|--------|------|
| PYTHON detection in tests-config.sh | Done | BUILDDIR set; PYTHON from run-tests.sh |
| Regtest block count | Open | See §4.5.1 |
| Cursor harmonization | Documented; delayed | See §2.3. Full issue list documented; resolution postponed. |
| Python 3 migration | Incomplete | run-tests.sh uses Py3; 10 scripts have python2 shebang; full_test_suite.py has 2.7.18 fallback; CI requires Py2.7 for Ansible. Transition plan: UpdateTests §6.2.1. |
| Python in install scripts | — | contrib/ci-workers/unix.yml (Ansible, installs Python); contrib/ci-workers/tasks/install-pip.yml (runs get-pip.py). CI relocated to ~/Work/ZK/CI. |
| GTest 1.12.1 upgrade | Pending | Cross-fork alignment; Zero uses 1.16.0. See §4.5.2. |

### 4.5.1 Regtest — skip logic (rate as fail, not run)

**Skip-logic instances:** getchaintips (skip when len(tips) != 2); wallet.py clean-chain (skip when node0 balance != 29); zero_regtest_subsidy for node1. These are effectively not run; rate as fail for coverage. See UpdateTests §4.8.1.

**Context:** Zcash-style 200-block chain vs Zero (subsidy 10 ZER/block, halving 150, COINBASE_MATURITY=720). Decisions deferred: cached chain, align expectations, reduce blocks.

### 4.5.2 GTest exclusions (documented)

**CachedWitnesses* (4 tests):** CreateValidBlock harness lacks pcoinsTip, ReadBlockFromDisk; BuildWitnessCache returns early when pcoinsTip null. Excluded. **WriteCryptedSaplingZkey*:** CDB::Rewrite deadlock. Excluded.

**Version:** Zero uses GTest 1.16.0 (C++14). Zcash 1.12.1 is lower bound / known-good; prefer current latest (1.16) unless precluded. 1.17.0 requires C++17; stay on 1.16 until C++17 migration.

### 4.6 Documented Mismatches (Subsidy §11.1)

| Location | Issue |
|----------|-------|
| `src/amount.h` | `MAX_MONEY = 16.95M ZER`; Zero total supply ~25.6M ZER exceeds this; validation uses per-subsidy `MoneyRange` only, not cumulative |
| `TODO.md`, `TEST_ZERO.md` | Outdated `338665500000000` total subsidy reference; Zero total ≈ 2.56e15 zatoshi |
| `doc/tor.md` | `"subver" : "/MagicBean:1.0.0/"` — legacy; Zero uses Gaua |

### 4.7 User-Facing Documentation Review (Area to Improve)

**Issue:** Links in README, BUILD_ZERO, and other user-facing docs point to Zcash, Bitcoin, and third-party sites. Several need review and improvement.

**Issues:**
- **Zcash branding:** Security (z.cash/support/security), user guide (Zcash wiki), params (download.z.cash) all point to Zcash. Zero should either host its own equivalents or explicitly state these are Zcash resources.
- **Security:** README links to z.cash/support/security for security info. Zero should have its own security page or clearly label as Zcash guidance.
- **Issue template:** Moved to ~/Work/ZK/CI/Zero/. When implemented, should be Zero-specific (security contact, GPG keys).
- **Stale links:** bitcointalk, jenkins.bluematt.me, googlecode.com, and other legacy URLs may be dead.
- **No Zero security contact:** No documented Zero-specific security contact or GPG key.

**Recommendations:**
- Add or link to a Zero-specific security page (or explicitly label Zcash as shared guidance).
- Update CI/Zero ISSUE_TEMPLATE.md with Zero security contact and keys when CI is implemented.
- Audit and remove/replace broken links.
- Consider hosting params on a Zero-controlled mirror.

## 5. In-Code TODOs, Documented Bugs, Filed Bugs

**Terms:** *Filed* = zerocurrencycoin/Zero GitHub issues/PRs. *In-code TODOs* = file:line references in the codebase. §5.5 indexes tracked items; §5.6–5.9 give expanded details for selected items; §5.1–5.3 are code tables by module; §5.4 lists fixed bugs.

### 5.5 Filed / Referenced Issues

Index of external issues and in-code refs. Order: actionable, then pending, then deferred.

| ID | Context |
|----|---------|
| #70 | getrawtransaction: size done (§5.6); fees deferred (§5.7) |
| #71 (PR) | Raspberry Pi 5 ARM64 build — §5.8 |
| Zcash #1614 | Sprout anchor selection — wallet.cpp:3249 — §5.9 |
| #966 | test_checktransaction.cpp — §5.3 |
| #1350 | test_wallet.cpp — §5.2 |
| #1354 | asyncrpcoperation.cpp — §5.2 |
| #1366 | asyncrpcoperation_common.cpp — §5.2 |

### 5.6 getrawtransaction size (Issue #70) — Done

**Issue:** [zerocurrencycoin/Zero#70](https://github.com/zerocurrencycoin/Zero/issues/70) — `getrawtransaction "txid" 1` and `decoderawtransaction "hex"` return verbose JSON without `size`.

**Status:** Fixed. `TxToJSONExpanded` (rawtransaction.cpp) adds `size` via `GetSerializeSize`. Test: `rpc_rawparams` asserts `find_value(r.get_obj(), "size").get_int() == 193`. `fees` deferred (§5.7).

### 5.7 TODO: getrawtransaction fees (Issue #70, deferred)

**Issue:** Same as §5.6 — reporter also requested `fees` in verbose output.

**Deferred:** Fee = sum(inputs) − sum(outputs) for transparent txs. Shielded txs use `valueBalance`; computing effective fee requires tracking decrypted values. Bitcoin Core exposes fee in `gettransaction` (wallet) and mempool RPCs; `getrawtransaction` does not. Options: (1) add fee for transparent-only txs; (2) document as unsupported for shielded; (3) implement full fee for both (higher effort).

**File:** `src/rpc/rawtransaction.cpp`, `TxToJSONExpanded` or new helper.

### 5.8 TODO: PR #71 Raspberry Pi 5 (ARM64) build

**PR:** [zerocurrencycoin/Zero#71](https://github.com/zerocurrencycoin/Zero/pull/71) — Add Raspberry Pi 5 (aarch64 Linux) build support. Target: master. Branch: `raspberry-pi-5-support`.

**Changes:** GCC 14.2 / Boost 1.83 header fixes (validationinterface.cpp, httpserver.cpp, equihash.h); build-bdb.sh, build-rpi-wallet-v2.sh; BUILD-RASPBERRY-PI.md. Tested on RPi 5 2GB, Debian Trixie, DietPi.

**Overlap with arm-mac-build:** Both use Boost 1.83, BDB 6.2.32. Shared file edits may conflict; review before merge. arm-mac-build targets macOS ARM64; #71 targets Linux aarch64.

**Action:** Review, resolve conflicts with arm-mac-build, complete PR checklist (docs, test plan, buildbot).

### 5.9 TODO: Sprout anchor selection (Zcash #1614)

**Reference:** [zcash/zcash#1614](https://github.com/zcash/zcash/issues/1614) — choose less recent JoinSplit, Spend, and Action anchors.

**Context:** `WitnessNoteCommitment` (wallet.cpp:3204) sets `final_anchor = tree.root()` — the chain-tip root. The TODO asks for a heuristic instead.

**Zcash discussion:** (1) **Latency** — newer anchor = faster spend; (2) **Reorg risk** — newer anchor more likely orphaned; (3) **Privacy** — newer anchor can leak timing (e.g. incoming payment just arrived); (4) **Privacy** — newer anchor can leak “you are online” vs older-anchor users; (5) **Privacy** — older anchor can leak “you are not new” vs newer-anchor users. Current choice (most recent anchor) optimizes latency and some privacy but is worst for reorg risk.

**Pro/con:** Newer anchor = lower latency, better for some privacy; older anchor (e.g. 10 blocks back) = fewer reorg invalidations, worse latency. str4d/zooko: prefer anchor N blocks back (e.g. 10); configurable per node.

**Relevance to Zero:** Zero still uses Sprout and `WitnessNoteCommitment`; Zcash has removed it. Same tradeoff applies; implementing a heuristic would improve reliability and align with Zcash analysis.

### 5.1 Zero-Specific (High Relevance)

| File | Line | Type | Description |
|------|------|------|-------------|
| zeronode/budget.cpp | 1424 | TODO | Multisig in coinbase on mainnet; add support in future release |
| zeronode/budget.cpp | 1433 | TODO | Track last time proposal was valid; erase if invalid 2 weeks |
| zeronode/budget.cpp | 1968 | TODO | If N cycles old, invalid |
| zeronode/budget.cpp | 1973 | TODO | Verify if can safely remove |
| zeronode/zeronode.cpp | 316 | TODO | Regtest fine with any addresses for now |
| zeronode/zeronode.cpp | 754 | TODO | Or should we also request this block? |
| zeronode/swifttx.cpp | 63 | TODO | Look into other script types that are normal |
| zeronode/rpc/zeronode.cpp | 356 | TODO | Consider better way for ACTIVE_ZERONODE_INITIAL |
| zeronode/payments.cpp | 324 | TODO | zeronode |
| zeronode/obfuscation.cpp | 125 | TODO | Rename/move to core |
| test/alert_tests.cpp | 290, 342 | TODO | Either implement proper alert keys or remove alert system entirely |
| test/Checkpoints_tests.cpp | 21 | TODO | Checkpoints have been removed for now |

### 5.2 Wallet / Shielded

| File | Line | Type | Description |
|------|------|------|-------------|
| wallet/wallet.cpp | 1227 | TODO | Expose local nullifier stats; for now global only |
| wallet/wallet.cpp | 1849 | TODO | Sapling. walletpassphrase currently unsupported |
| wallet/wallet.cpp | 2548 | TODO | Fix handling of 'change' outputs |
| wallet/wallet.cpp | 3249 | TODO | Select anchor via heuristic (Zcash #1614). See §5.9. |
| wallet/wallet.cpp | 4399 | TODO | Allow non-wallet inputs |
| wallet/wallet.cpp | 4696 | TODO | Pass scriptChange instead of reservekey |
| wallet/wallet.h | 170 | TODO | nOrderPos; calculate elsewhere |
| wallet/gtest/test_wallet.cpp | 1847 | TODO | New note should get witnessed (#1350) |
| wallet/asyncrpcoperation_sendmany.cpp | 388 | TODO | Use fromtaddr_ as change address? |
| wallet/asyncrpcoperation_sendmany.cpp | 960 | TODO | Refactor GetFilteredNotes to fetch only what we need |
| wallet/asyncrpcoperation_saplingmigration.cpp | 139 | TODO | Above functionality not implemented in zcashd |
| wallet/asyncrpcoperation_common.cpp | 43 | TODO | #1366 Get errors, print vErrors |
| wallet/rpcdisclosure.cpp | 126 | TODO | Init DB in init.cpp in future |
| wallet/crypter.cpp | 133, 303, 561 | TODO | Handle IV/encryption properly when supported |
| transaction_builder.cpp | 721 | TODO | Sprout payment disclosure |

### 5.3 Core / RPC / Network

| File | Line | Type | Description |
|------|------|------|-------------|
| main.cpp | 2865 | TODO | Simplify when Blossom activation height set |
| main.cpp | 4007 | TODO | Nefarious user could skew stats |
| main.cpp | 4594 | TODO | Deal better with return value for duplicate |
| main.cpp | 6633 | TODO | Prohibit joinsplits/shielded from mapOrphans |
| main.cpp | 6728 | TODO | Optimize: if pindexLast is ancestor, continue |
| rpc/blockchain.cpp | 863 | TODO | mempool.pruneSpent should be done by CCoinsViewMemPool |
| rpc/mining.cpp | 500 | TODO | Re-enable coinbasevalue once spec written |
| rpc/mining.cpp | 605 | TODO | Recheck connections/IBD; send expires-immediately template |
| rpcwallet.cpp | 1924, 1975, 2084 | TODO | Get rid of .c_str() by implementing SecureString::operator= |
| rpcwallet.cpp | 3039, 4226, 5055 | TODO | Various |
| httpserver.cpp | 72, 407, 414 | XXX | RAII for event_base, evhttp |
| torcontrol.cpp | 543 | TODO | Refactor shutdown sequence |
| miner.cpp | 667 | TODO | Factor out into function with same API per solver |

### 5.4 Documented Bugs (Fixed)

| Bug | Location | Fix |
|-----|----------|-----|
| pblockindex->pprev null deref | VerifyAndSetInitialWitness | Guard for genesis |
| pcoinsTip null deref | VerifyAndSetInitialWitness | Early return |
| *nullifier on boost::none | VerifyAndSetInitialWitness | Guard |
| nWitnessCacheSize not reset | ClearNoteWitnessCache | Added nWitnessCacheSize = 0 |
| zeronode.h:229 memcpy | SliceHash | memcpy(&n, (char*)&hash + slice*8, 8) |
| budget.cpp:35 overflow | Intentional sentinel | INT_MAX to silence |

## 6. Long-Term Plans, Gotchas, Gaps

Cross-cutting items and work queues.

### 6.1 Build and Dependencies

| Area | Status | Notes |
|------|--------|-------|
| Rust | Workaround | 1.32.0 lacks aarch64-apple-darwin; ARM Mac uses system symlink. Target: pin 1.81+ (UpdateBuild §3.3). |
| OpenSSL | EOL | 1.1.1w; migrate to 3.x or remove (UpdateBuild §3.2). |
| BDB, Boost, libsodium, etc. | At target | See UpdateBuild §5 for version table. |
| Windows | TBD | MinGW, WSL2, params, MSVC. |
| macOS BDB crash | Workaround | `rm -rf "$HOME/Library/Application Support/zero/database"`. |

### 6.2 Tests

| Area | Status | Notes |
|------|--------|-------|
| GTest harness | Blocking | CreateValidBlock lacks pcoinsTip, ReadBlockFromDisk; blocks CachedWitnesses*, UpdatedSaplingNoteData, NavigateFromSaplingNullifierToNote. Manual witness pattern used where fixed. |
| CDB::Rewrite deadlock | Set aside | WriteCryptedSaplingZkey; first wallet never closed. |
| RPC Python | Skips | get_coinbase_address, protocol version, getchaintips, clean-chain amounts; regtest 424 vs 210 block count. |
| Coverage gaps | Documented | zeronode RPCs, zero_exclusive (zs_*, getalldata, getsupply), zero_experimental (getsaplingwitness*). See UpdateTests §5. |
| test_miner | Pending | Exclude when `--enable-mining=no` (Makefile.gtest.include). |

### 6.3 Witness Architecture

Zero uses custom `VerifyAndSetInitialWitness` and `BuildWitnessCache` (full-chain rebuild) instead of Zcash's `IncrementNoteWitnesses` (per-block). Requires pcoinsTip, ReadBlockFromDisk, chain state. GTest harness does not provide these. See UpdateFeatures §1.

### 6.4 Zeronode

RPC param/read-only: partial coverage (rpc_zeronode_tests, rpc_zeronode_budget_tests). Logic, integration, remaining RPCs: no coverage. Enhanced error handling (ZeronodeWalletResult, ZeronodeWalletError) designed but not implemented. See Zeronode_wallet.md, UpdateTests §11.4.

### 6.5 Other Work Items

| Category | Items |
|----------|-------|
| Data/params | Backup, blockchain snapshot, sample files, params mirror (BUILD_ZERO); ztestsaplingXXX placeholder (Subsidy.md). |
| Test infra | script_test.py excluded (>40 min, COINBASE_MATURITY mismatch); leveldb, libsnark not in top-level check; runner unification optional. |
| Build | utfcpp 3.1→4.0.9 deferred; hash.h VLA fixed. |
| Process | Linux/Windows validation before merge; changelog, release notes, per-platform build instructions. |
| Low priority | Branding (autotools, copyright, test strings); UpdateBuild restructure proposal. |

## 7. Direction

### 7.1 Immediate Goal

Stabilize build and test suite on all three platforms with minimum changes.
ARM Mac is a new platform addition, not a divergence.

### 7.2 Dependency Baseline

Bring Zero's dependency set to at least Zcash v6.11.0 versions. Prioritized by
risk: BDB first, then patch-level bumps, then major upgrades.

### 7.3 Test Health

Target: zero crashes and segfaults in GTest; isolated root causes in Boost.
Pre-existing failures requiring architectural changes are documented but not
prioritized over platform stabilization.

## 8. RPC and Options Comparison

### 8.1 Files

| File | Purpose |
|------|---------|
| RPCs.csv | RPC presence: rpc, type, bitcoin, zcash, pirate, zero (y/n). |
| RPCs_extended.csv | Adds zero_missing_sources (B/Z/P when zero=n). Regenerate after edits. |
| Options.csv | Daemon options from zerod -help: option, category, maps_to_rpc, bitcoin, zcash, pirate, zero. B/Z/P inferred from typical fork behavior; verify against binaries when porting. |
| Options_extended.csv | Adds zero_missing_sources. Regenerate after edits. |

### 8.2 Updating RPCs.csv

When: after adding/removing RPCs or auditing another project. Add row: rpc, type, y/n per project. Verify: `awk -F',' 'NR>1 && ($4!="y"&&$4!="n" || $5!="y"&&$5!="n" || $6!="y"&&$6!="n") {print NR":"$0}' RPCs.csv`

Regenerate RPCs_extended.csv:
```bash
awk -F',' 'NR==1{print $0",zero_missing_sources";next}{src="";if($6=="n"){if($3=="y")src=src"B";if($4=="y")src=src"Z";if($5=="y")src=src"P"}print $0","src}' RPCs.csv > RPCs_extended.csv
```

### 8.3 Updating Options.csv

When: after adding/removing daemon options. Extract from `zerod -help`, `bitcoind -help`, etc. Columns: option, category, maps_to_rpc (RPC or config affected), bitcoin, zcash, pirate, zero.

Regenerate Options_extended.csv:
```bash
awk -F',' 'NR==1{print $0",zero_missing_sources";next}{src="";if($7=="n"){if($4=="y")src=src"B";if($5=="y")src=src"Z";if($6=="y")src=src"P"}print $0","src}' Options.csv > Options_extended.csv
```

### 8.4 zero_missing_sources

When zero=n: B=Bitcoin, Z=Zcash, P=Pirate. Filter ZP for "Zcash and Pirate have, Zero lacks."

### 8.5 Excel

Import RPCs_extended.csv or Options_extended.csv into Excel/Sheets. Filter on zero_missing_sources. No formulas needed.

---

## 9. Windows Build (Zero and zerowallet)

Status tracking. For build instructions, see referenced docs.

**zerod:** [BUILD_ZERO.md](BUILD_ZERO.md) §2.4, §5.3. Platform rationale: UpdateBuild §2.1.

**zerowallet:** zerowallet BUILD.md §Windows, §MXE; UpdateWallet §Cross-Compilation (zerowallet-specific content TBD).

**Upstream:** Zclassic, zen use same host triplets; Zcash no build-windows doc; Bitcoin/Zcash depends `download-win` target.

**Items and notes (pending Windows build confirmation on Linux):** Update zerowallet BUILD.md to reference BUILD_ZERO for zerod/Windows. Determine whether UpdateWallet retains Windows zerowallet-specific info.
