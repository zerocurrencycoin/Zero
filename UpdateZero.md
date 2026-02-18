# UpdateZero

Tracking document for the Zero node update and stabilization effort.
Zero is a Zcash-family cryptocurrency node (C++/Rust). Target platforms
are Windows (primary user deployment), Linux (primary for VPS hosting,
development, and community validation), and macOS including Apple Silicon.

## 1. Documentation Map

| Document | Scope | Boundary |
|----------|-------|----------|
| **UpdateZero.md** | Status, direction, open items, plans | What and why. No implementation detail. |
| **UpdateBuild.md** | Build system, dependencies, platform setup, library versions | How to build. Version research and upgrade path. |
| **UpdateTests.md** | Test suites, results, fixes, procedures | Test-specific changes. Small source fixes that directly address test failures. |
| **UpdateFeatures.md** | Architecture, production code changes, new features, requirements | Source changes beyond test fixes. Cross-fork analysis. Design decisions. |

Source changes to test files always go in UpdateTests. Source changes to
production code are placed case-by-case: small fixes tied to a specific
test failure go in UpdateTests; changes with broader architectural scope
or cross-platform implications go in UpdateFeatures.

## 2. Branch

- Branch: `arm-mac-build` based on `origin/zeronode_wallet` (HEAD: `2b260530e`)
- Remote: `https://github.com/zerocurrencycoin/Zero`
- Modified files: 14 (7 depends, 1 source build fix, 3 gtest fixes, 3 wallet)
- Untracked: documentation files, configure backups

**Workflow:** Do not push or merge to upstream `origin/main` or `origin/zeronode_wallet`.
Commit only to `arm-mac-build` (or a fork).

## 3. Status Summary

### 3.1 Build

| Platform | Status | Notes |
|----------|--------|-------|
| Linux x86_64 | Untested with current changes | Base branch builds on Linux. Primary dev and validation platform. |
| Windows | Untested | Primary user deployment platform. |
| macOS ARM64 | Working | All binaries produced. Compatibility defined by macOS 24.5.0 until further testing. |
| ~~macOS x86~~ | Not supported | EOL; not verified to compile or run. |

Build changes target ARM Mac enablement but touch shared infrastructure
(download URLs, sed portability). Library version upgrades (e.g. 1.1.1w,
libsodium 1.0.20) are targets until compatibility verified. Linux and
Windows regression testing required before merge. See UpdateBuild.md
sections 2 and 3.

### 3.2 Tests

| Suite | Platform | Passed | Failed | Crashed | Excluded | Total |
|-------|----------|--------|--------|---------|----------|-------|
| GTest | macOS ARM64 | 200 | 1 | 0 | 5 | 206 |
| Boost | macOS ARM64 | ~11 | ~249 | — | — | 260 |

GTest: 4 fixes applied, 4 pre-existing failures excluded, 1 hang excluded.
Boost: cascade failure from 2-3 root causes; most of the 249 are not
independent bugs. See UpdateTests.md sections 3 and 4.

### 3.3 Features

Production code changes in `wallet.cpp` and `wallet.h` fix three
null-dereference bugs and one cache-size bug in Zero's custom witness
functions. These are pre-existing bugs also present in HUSH3.
See UpdateFeatures.md section 1.

## 4. Recent Changes

### 4.1 Build System

1. Boost 1.70 download URL, toolset, sed portability, Clang 17 compatibility
2. OpenSSL 1.1.1a to 1.1.1w for ARM64 target support
3. Rust depends: system Rust symlink for ARM Mac (1.32.0 has no ARM binaries)
4. BerkeleyDB: POSIX mutex override for ARM64 macOS
5. libsodium: download URL fix (old path 404)
6. config.guess/config.sub: 2015 to 2025 (ARM Mac identification)
7. equihash.cpp: `ENABLE_MINING` guard on explicit template instantiations

### 4.2 Test Fixes

1. `PoW.MinDifficultyRules` — guard on unset `boost::optional` consensus parameter
2. `DeprecationTest.AlertNotify` — test string matched to runtime branding
3. `equihash_tests.check_optimised_solver_cancelled` — relaxed platform-dependent assertion
4. `WalletTests` (multiple) — test harness adapted for Zero's witness API

### 4.3 Production Code Fixes

1. `VerifyAndSetInitialWitness` — null-pointer guards for `pprev`, `pcoinsTip`, `nullifier`
2. `VerifyAndSetInitialWitness` / `BuildWitnessCache` — added `pblockIn` parameter
3. `ClearNoteWitnessCache` — reset `nWitnessCacheSize` to 0

## 5. Open Items

### 5.1 High Priority

1. **Linux regression test** — verify all changes build and pass on Linux x86_64
2. **BDB 6.2.32 upgrade** — fixes ARM64 mutex natively, removes workaround, same DB format and license. See UpdateBuild.md section 6.1
3. **Boost test cascade** — isolate root-cause crashes in `subsidy_limit_test` and `Alert_tests`; most of 249 failures should collapse to 2-3 real issues. See UpdateTests.md section 4.1

### 5.2 Medium Priority

4. **CachedWitnesses tests** (4 tests) — pre-existing failures from witness API mismatch. Options: restore `IncrementNoteWitnesses` for test use or adapt test infrastructure. See UpdateFeatures.md section 1.5
5. **WriteCryptedSaplingZkeyDirectToDb hang** — BDB mutex issue; may resolve with 6.2.32 upgrade
6. **Low-risk dependency upgrades** — libsodium, libevent, ZeroMQ, ccache to Zcash-matching versions. See UpdateBuild.md section 6

### 5.3 Deferred

7. **Boost 1.83** — major jump, high risk, reference Zcash v6.11.0
8. **OpenSSL evaluation** — remove or migrate to 3.5.x LTS
9. **Rust version pinning** — replace system symlink with pinned download for CI
10. **Witness architecture evaluation** — assess `BuildWitnessCache` vs upstream `IncrementNoteWitnesses`. See UpdateFeatures.md section 1.6

### 5.4 Deferred (from TODO.md)

11. **Zeronode test suite** — Zero-specific features (zeronode, budget, SwiftTX) have 0% test coverage. Phase 5 in TODO.md. High impact; not part of current port.
12. **Enhanced error handling** — Replace boolean returns in zeronode wallet interface with detailed error reporting (ZeronodeWalletError, ZeronodeWalletResult). Phase 3 in TODO.md. Optional enhancement.

## 6. Direction

### 6.1 Immediate Goal

Stabilize the build and test suite on all three platforms with minimum
changes. Current changes should not alter production behavior on Linux
or Windows. ARM Mac is a new platform addition, not a divergence.

### 6.2 Dependency Baseline

Bring Zero's dependency set to at least the versions used by Zcash v6.11.0,
prioritized by risk: BDB first (low risk, high value), then patch-level
bumps, then major version upgrades. See UpdateBuild.md sections 6 and 7
for upgrade plan and cross-project version comparison.

### 6.3 Witness Architecture

Zero replaced Zcash's per-block `IncrementNoteWitnesses` with a custom
full-chain `VerifyAndSetInitialWitness` / `BuildWitnessCache` system in
Feb 2020. This divergence is shared with HUSH3 and was abandoned by Pirate.
Short-term: fix bugs in current code. Medium-term: evaluate restoring
`IncrementNoteWitnesses` as a secondary path. Long-term: track Zcash's
witness evolution for future protocol upgrades. See UpdateFeatures.md section 1.

### 6.4 Test Health

Target: zero crashes and segfaults in GTest, isolated root causes in Boost
tests. Pre-existing test failures that require architectural changes are
documented but not prioritized over platform stabilization.
