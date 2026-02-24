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

### 1.1 Cross-Reference Index

| Topic | UpdateZero | UpdateBuild | UpdateTests | UpdateFeatures |
|-------|------------|-------------|-------------|----------------|
| Build/platform setup | §3.1, §4.1 | §1–4 | — | — |
| Depends changes | §4.1 | §3 | — | — |
| Library versions, upgrade plan | §6.2 | §5–7 | — | — |
| BDB, wallet | — | §6.1, §7.1 | §4.5 | §4.1 |
| Test results, fixes | §3.2, §4.2 | — | §1–4, §8 | — |
| Test prioritization | §5 | — | §5 | — |
| Open test failures | §5.1 | — | §4 | — |
| Witness architecture | — | — | §4.5 | §1 |
| z_getnewaddress, RPC | — | — | §4.6, §5 | — |
| GTest version | — | §5.3, §7 | §2.1 | — |
| OpenSSL, TLS | §5.2 | §6.8, §7.4 | — | §4.2 |
| Rust, librustzcash | §5.2 | §3.3, §5.2, §6.7, §6.9, §7.3 | — | — |

### 1.2 Documentation Principles

**Partition (scope and ownership)**

| Doc | Owns | Does not own |
|-----|------|--------------|
| UpdateZero | Status, direction, open items, plans | Implementation detail |
| UpdateBuild | Build system, depends, platform setup, library versions | Test procedures, production code design |
| UpdateTests | Test suites, results, fixes, procedures, runner config | Build recipes, architecture decisions |
| UpdateFeatures | Architecture, production code changes, cross-fork analysis | Test harness fixes, build system |

Source changes: test files → UpdateTests. Production code: small fix tied to one test → UpdateTests; broader scope → UpdateFeatures.

**Terminology**

- Status: Done | Open | Documented | Planned | Pending | Set aside (UpdateZero open items)
- Test status: Excl | Fix | Pass | Skip (UpdateTests per-suite)
- Urgency: Immediate | Delayed | Deferred (UpdateZero); Fix now | Later | Set aside (UpdateTests)
- Use "pass-only" for run mode; "PASS" for suite result

**Cross-references**

- One index: UpdateZero §1.1. Other docs: single-line header cross-ref to index.
- Inline: prefer doc name + one section (e.g. "UpdateTests §4") over multiple sections.
- No cross-check paragraph; index is authoritative.

**Format**

- Tables: `| Col | Col |`; no extra pipes.
- Section numbering: 1, 2, 3…; subsections 1.1, 1.2…

**Redundancy (regression, Rust, Build):** §3.1, §4.1, §5.1–5.2 duplicated
status and open items that belong in UpdateBuild and UpdateTests. Cause:
UpdateZero was the status hub and summarized build changes; the line
between "status" and "implementation" was fuzzy. Doc reviews focused on
partition (scope) and cross-refs, not deduplication. Fix: minimal pointers
in UpdateZero; implementation in UpdateBuild/UpdateTests. Index §1.1 is
authoritative for where each topic lives.

## 2. Branch

- Branch: `arm-mac-build` based on `origin/zeronode_wallet`
- Remote: `https://github.com/zerocurrencycoin/Zero`
- Recent: Boost 1.88, BDB 6.2.32, libsodium 1.0.21, duplicate -lc++ fix

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
(download URLs, sed portability). Linux and Windows regression required
before merge. See UpdateBuild §2–3; procedure UpdateTests §3.

### 3.2 Tests

Test results, fixes, exclusions, and procedures are in **UpdateTests.md**. Run `contrib/run-tests.sh`; logs go to `test-logs/`.

### 3.3 Features

Production code changes in `wallet.cpp` and `wallet.h` fix three
null-dereference bugs and one cache-size bug in Zero's custom witness
functions. These are pre-existing bugs also present in HUSH3.
See UpdateFeatures.md section 1.

## 4. Recent Changes

### 4.1 Build System

1. Boost 1.70 → 1.88.0 (Zcash-validated path) for Clang 17 compatibility
2. OpenSSL 1.1.1a → 1.1.1w for ARM64 target support
3. Rust: UpdateBuild §3.3
4. BerkeleyDB 6.2.23 → 6.2.32 (native ARM64 mutex; workaround removed)
5. libsodium 1.0.15 → 1.0.21, download URL fix (old path 404)
6. config.guess/config.sub: 2015 to 2025 (ARM Mac identification)
7. equihash.cpp: `ENABLE_MINING` guard on explicit template instantiations
8. configure.ac: strip -lstdc++ from ZMQ_LIBS on Darwin (duplicate -lc++ fix)

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

### 5.1 Immediate

1. **Platform regression** — UpdateTests §3: verify build and pass on Linux x86_64, Windows
2. **Fix-now test items** — UpdateTests §4 (pyblake2, nuparams, rpc_wallet founders %, block_subsidy). z_getnewaddress extra-args fix applied.

### 5.2 Delayed

3. **OpenSSL** — UpdateBuild §6.8, UpdateFeatures §4.2
4. **Rust** — UpdateBuild §6.7 (pin modern version; rust.mk update pending)
5. **Failing tests** — UpdateTests §4

### 5.3 Deferred

6. **Zeronode test suite** — Zero-specific features (zeronode, budget, SwiftTX) have 0% test coverage. High impact; not part of current port.
7. **Enhanced error handling** — Replace boolean returns in zeronode wallet interface with detailed error reporting. Optional enhancement.

### 5.4 Open questions / Pending approvals

| Item | Status | Notes |
|------|--------|-------|
| PYTHON detection in tests-config.sh | Done | tests-config.sh sets PYTHON from pyenv 2.7.18 or python2 if unset |
| Regtest block count fix | Open | Test uses actual block count vs Zero -regtestblocktime; needs decision |
| get_coinbase_address impl gap | Documented | Skip; fix would need Zero listunspent/generated behavior |
| Python 3 migration | Planned | When feasible; hashlib.blake2b replaces pyblake2 |
| GTest 1.12.1 upgrade | Pending | C++14 min; cross-fork validation |
| Alert_tests | Set aside | Deprecated; raw data MagicBean-specific |

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

### 6.3 Test Health

Target: zero crashes and segfaults in GTest, isolated root causes in Boost
tests. Pre-existing test failures that require architectural changes are
documented but not prioritized over platform stabilization.
