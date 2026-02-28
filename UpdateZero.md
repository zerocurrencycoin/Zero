# UpdateZero

This document tracks the Zero node update and stabilization effort. Zero is a Zcash-family cryptocurrency node (C++/Rust) targeting Windows (primary user deployment), Linux (VPS and validation), and macOS including Apple Silicon. Scope is the full node repo only; zerowallet is out of scope.

UpdateZero assembles status, open items, long-term plans, gotchas, and gaps. TODO.md holds user-facing items already decided for implementation.

---

## Documentation Split

**Direction:** User-facing docs must never reference project docs. Project docs may reference each other.

| Group | Files | Audience |
|-------|-------|----------|
| **User-facing** | README.md, BUILD_ZERO.md, TEST_ZERO.md, CONTRIBUTING.md, TODO.md | Contributors, users building/running Zero |
| **Project** | UpdateZero.md, UpdateBuild.md, UpdateTests.md, UpdateFeatures.md, Zeronode_wallet.md, Subsidy.md, doc/files.md | Maintainers, status tracking, design decisions |

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

- **Active branches**: `arm-mac-build` (ARM Mac), `mac_linux_boost188` (Boost 1.88, Mac+Linux). Both based on `origin/zeronode_wallet` or `origin/master`.
- Remote: `https://github.com/zerocurrencycoin/Zero`
- Workflow: Do not push or merge to upstream. Commit only to a feature branch or fork.

## 3. Status Summary

### 3.1 Build

| Platform | Status | Notes |
|----------|--------|-------|
| Linux x86_64 | Untested with current changes | Base branch builds on Linux. Primary dev and validation platform. |
| Windows | Untested | Primary user deployment platform. MinGW cross-compile; requirements TBD. |
| macOS ARM64 | Working | All binaries produced. Compatibility defined by macOS 24.5.0. Host triplet aarch64-apple-darwin24.5.0. |
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
| Tests | Fix-now items | pyblake2 prereq, nuparams, rpc_wallet founders %, block_subsidy. z_getnewaddress extra-args fix applied. |

### 4.2 P2 — Delayed

| Module | Item | Notes |
|--------|------|-------|
| Dependencies | OpenSSL | 1.1.1w EOL. Options: keep short-term; remove (audit call sites); migrate to 3.x. Requires audit before proceeding. |
| Dependencies | Rust | Pin modern version (1.81+). rust.mk currently 1.32.0; ARM Mac uses system symlink (no aarch64-apple-darwin binaries for 1.32.0). Target: update rust.mk for pinned modern Rust. |
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

| Item | Status | Notes |
|------|--------|------|
| PYTHON detection in tests-config.sh | Done | pyenv 2.7.18 or python2 if unset |
| Regtest block count fix | Open | Test uses actual block count vs Zero -regtestblocktime; needs decision |
| Python 3 migration | Planned | When feasible; hashlib.blake2b replaces pyblake2 |
| GTest 1.12.1 upgrade | Pending | C++14 min; cross-fork validation |

### 4.6 Documented Mismatches (Subsidy §11.1)

| Location | Issue |
|----------|-------|
| `src/amount.h` | `MAX_MONEY = 16.95M ZER`; Zero total supply ~25.6M ZER exceeds this; validation uses per-subsidy `MoneyRange` only, not cumulative |
| `TODO.md`, `TEST_ZERO.md` | Outdated `338665500000000` total subsidy reference; Zero total ≈ 2.56e15 zatoshi |
| `README.md` | "Stable supply is 3888 ZER, after first halfing" — ambiguous; 3888 ≈ daily emission (720×5.4) after first halving, not total supply |
| `doc/tor.md` | `"subver" : "/MagicBean:1.0.0/"` — legacy; Zero uses Ambrym |

### 4.7 User-Facing Documentation Review (Area to Improve)

**Issue:** Links in README, BUILD_ZERO, and other user-facing docs point to Zcash, Bitcoin, and third-party sites. Several need review and improvement.

**Issues:**
- **Zcash branding:** Security (z.cash/support/security), user guide (Zcash wiki), params (download.z.cash) all point to Zcash. Zero should either host its own equivalents or explicitly state these are Zcash resources.
- **Security:** README links to z.cash/support/security for security info. Zero should have its own security page or clearly label as Zcash guidance.
- **Issue template:** .github/ISSUE_TEMPLATE.md still references security@z.cash and Zcash GPG keys; should be Zero-specific.
- **Stale links:** bitcointalk, jenkins.bluematt.me, googlecode.com, and other legacy URLs may be dead.
- **No Zero security contact:** No documented Zero-specific security contact or GPG key.

**Recommendations:**
- Add or link to a Zero-specific security page (or explicitly label Zcash as shared guidance).
- Update .github/ISSUE_TEMPLATE.md with Zero security contact and keys.
- Audit and remove/replace broken links.
- Consider hosting params on a Zero-controlled mirror.

## 5. In-Code TODOs, Documented Bugs, Filed Bugs

**Terms:** *Filed* = zerocurrencycoin/Zero GitHub issues/PRs. *In-code TODOs* = file:line references in the codebase. §5.5 indexes tracked items; §5.6–5.9 give expanded details for selected items; §5.1–5.3 are code tables by module; §5.4 lists fixed bugs.

### 5.5 Filed / Referenced Issues

Index of external issues and in-code refs. Order: actionable, then pending, then deferred.

| ID | Context |
|----|---------|
| #70 | getrawtransaction missing "size" and "fees" — §5.6 (size), §5.7 (fees deferred) |
| #71 (PR) | Raspberry Pi 5 ARM64 build — §5.8 |
| Zcash #1614 | Sprout anchor selection — wallet.cpp:3249 — §5.9 |
| #966 | test_checktransaction.cpp — §5.3 |
| #1350 | test_wallet.cpp — §5.2 |
| #1354 | asyncrpcoperation.cpp — §5.2 |
| #1366 | asyncrpcoperation_common.cpp — §5.2 |

### 5.6 TODO: getrawtransaction size (Issue #70)

**Issue:** [zerocurrencycoin/Zero#70](https://github.com/zerocurrencycoin/Zero/issues/70) — `getrawtransaction "txid" 1` and `decoderawtransaction "hex"` return verbose JSON without `size`. `fees` deferred (§5.7).

**Fix:** Add `size` to `TxToJSONExpanded` (the function that builds verbose JSON for both RPCs). Same change fixes both.

| Item | Detail |
|------|--------|
| **File** | `src/rpc/rawtransaction.cpp` |
| **Function** | `TxToJSONExpanded` (lines 150–247) |
| **Insert after** | Line 154: `entry.push_back(Pair("txid", txid.GetHex()));` |
| **Add** | `entry.push_back(Pair("size", (int)::GetSerializeSize(tx, SER_NETWORK, PROTOCOL_VERSION)));` |
| **Reference** | `TxToJSON` (same file, line 255) already has this pattern |

**Affected RPCs:** `getrawtransaction` (verbose), `decoderawtransaction` — both call `TxToJSONExpanded` (lines 444, 775).

**Test:** `src/test/rpc_tests.cpp` — `rpc_rawparams` (lines 99–102). Assertion: `BOOST_CHECK_EQUAL(find_value(r.get_obj(), "size").get_int(), 225);` for known 225-byte rawtx. Run: `./src/test/test_bitcoin -t rpc_rawparams` or via `contrib/run-tests.sh`.

**Backward compatibility:** Additive JSON key; no schema validation; existing consumers access specific keys only. Safe.

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
| rpc/rawtransaction.cpp | 154 | TODO | Add size to TxToJSONExpanded (#70). §5.6. |
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

**zerod:** [BUILD_ZERO.md](BUILD_ZERO.md) §2.4, §5.3; [UpdateBuild.md](UpdateBuild.md) §2.2.

**zerowallet:** zerowallet BUILD.md §Windows, §MXE; UpdateWallet §Cross-Compilation (zerowallet-specific content TBD).

**Upstream:** Zclassic, zen use same host triplets; Zcash no build-windows doc; Bitcoin/Zcash depends `download-win` target.

**Items and notes (pending Windows build confirmation on Linux):** Update zerowallet BUILD.md to reference BUILD_ZERO for zerod/Windows. Determine whether UpdateWallet retains Windows zerowallet-specific info.
