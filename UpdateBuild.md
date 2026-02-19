# UpdateBuild

Build system changes, dependency management, platform setup, and library
upgrade planning for the Zero node.

**Cross-references**: UpdateZero.md §1.1 (document index). Related: UpdateFeatures.md §4 (BDB, OpenSSL), UpdateTests.md §1.1 (GTest), §6.2 (WriteCryptedSaplingZkeyDirectToDb).

## 1. Build System Overview

Zero uses autotools with a `depends/` system for deterministic dependency
builds. Each library has a `.mk` recipe in `depends/packages/` specifying
version, download URL, SHA256, and per-platform build options. GNU
`config.guess` and `config.sub` detect the host triplet.

Build tools that run on the build machine use the `build_` prefix (e.g.
`build_SHA256SUM`, `build_DOWNLOAD`). These are defined in `depends/Makefile`
and `depends/builders/*.mk`, with per-OS overrides where needed (e.g. Darwin
uses `shasum -a 256` instead of `sha256sum`).

### 1.1 Portable sed in-place

BSD sed (macOS) and GNU sed (Linux, WSL) have incompatible `-i` syntax.
BSD requires an explicit backup extension after `-i`; GNU treats it as
optional. The GNU form `sed -i -e "s/foo/bar/" file` fails on macOS because
BSD interprets `-e` as a separate option, not the backup suffix.

A portable form is `sed -i.old "s/foo/bar/" file`. Both implementations
accept it: GNU creates `file.old` as backup; BSD requires the extension.
The `.old` backup files are left in the build tree and discarded when the
extract dir is cleaned.

To avoid repetition and platform-specific branches, a single variable
`build_SED_INPLACE` is defined in `depends/Makefile` and used in all
package preprocess steps:

```
# Portable sed in-place: works on Mac (BSD), Ubuntu, WSL (GNU sed).
build_SED_INPLACE = sed -i.old
# GNU native: sed -i -e
```

Used in: `boost.mk`, `openssl.mk`, `bdb.mk`. The `bdb.mk` previously had a
redundant `sed -i -e` line (duplicate of an earlier replacement) that
failed on macOS; it was removed.

## 2. Platform Setup

**Version targets** (e.g. OpenSSL 1.1.1w, libsodium 1.0.20) are upgrade
targets until compatibility is verified. Build with current library
versions first; upgrade after validation.

### 2.1 Linux x86_64

Standard build with `depends/`. Primary development and validation
platform. No changes to the Linux build path in this update. Regression
testing required to confirm shared changes (download URLs, sed patterns)
do not break existing builds.

### 2.2 Windows

Cross-compiled via MinGW. Primary user deployment platform. No changes
to the Windows build path in this update. Regression testing required.

### 2.3 macOS ARM64

New platform addition. **Compatibility defined by macOS 24.5.0 (darwin
24.5.0) until further testing.**

- Host triplet: `aarch64-apple-darwin24.5.0`
- Compiler: Apple Clang 17.0
- System Rust: 1.91.1

**Homebrew prerequisites (install before build):**
```bash
brew install automake cmake pkg-config coreutils
```
- `automake` — autotools
- `cmake` — build config (leveldb, etc.)
- `pkg-config` — library detection
- `coreutils` — `gnproc` (CPU count for parallel builds)

Configure command:

```
CONFIG_SITE=$PWD/depends/aarch64-apple-darwin24.5.0/share/config.site \
./configure --enable-hardening --enable-proton=no --enable-mining \
CXXFLAGS="-g -Wno-enum-constexpr-conversion"
```

- `--enable-proton=no`: Qpid Proton CMakeLists.txt incompatible with CMake 4.x. Optional AMQP component.
- `-Wno-enum-constexpr-conversion`: Suppresses Boost 1.70 / Clang 17 incompatibility.

Runtime prerequisite after a BDB mutex crash:
`rm -rf "$HOME/Library/Application Support/zero/database"`

### 2.4 macOS x86 (Intel)

Not supported. EOL macOS version; not verified to compile or run.
Strike for the time being.

### 2.5 Build Script (zcutil/build.sh)

**Argument order:** Flags must come before make arguments. The script parses
only the first positional argument for each flag.

```
./zcutil/build.sh [ --enable-lcov | --disable-tests ] [ --disable-mining ] [ --enable-proton ] [ MAKEARGS... ]
```

Examples:
- `./zcutil/build.sh --disable-mining -j4` (correct)
- `./zcutil/build.sh -j4 --disable-mining` (wrong: --disable-mining passed to make)

**Parallel jobs (-j):** On Linux use `nproc`; on macOS `nproc` is not standard.
Use `sysctl -n hw.ncpu` or install GNU coreutils (`brew install coreutils`) for
`gnproc`. The script caps `-jN` at 4 by default.

**gnproc on Mac:** Homebrew coreutils installs GNU utils with a `g` prefix
(e.g. `gnproc`, `gmake`). Add `$(brew --prefix coreutils)/libexec/gnubin` to
PATH to use un-prefixed names, or call `gnproc` explicitly.

**CONFIGURE_FLAGS:** Passed unquoted to `./configure`; the shell splits on
spaces. Values with spaces (e.g. `CXXFLAGS="-g -Wno-..."`) break. Workaround:
escape spaces, e.g. `CONFIGURE_FLAGS='CXXFLAGS=-g\ -Wno-deprecated-builtins\ -Wno-enum-constexpr-conversion'`.
Same behavior on Linux. Zcash and similar projects use CONFIGURE_FLAGS for
single-token overrides; multi-word values need escaping.

## 3. Depends Changes

### 3.1 boost.mk

Boost 1.70.0. Five changes:

1. **Download URL**: `dl.bintray.com` to `archives.boost.io`. Bintray shut down 2021.
2. **Toolset**: `--toolset=darwin-4.2.1` to `--toolset=clang`. Old darwin toolset injects `-fcoalesce-templates`, unsupported by modern Clang.
3. **Toolset/archiver variables**: `$(package)_toolset_darwin=clang` and `$(package)_archiver_darwin=$($(package)_ar)` for consistency with toolset change.
4. **sed portability**: Uses `$(build_SED_INPLACE)`. See section 1.1. Pattern broadened from `using gcc ;` to `using [a-z]* ;` to match whatever toolset bootstrap selects.
5. **CXXFLAGS**: Added `-Wno-enum-constexpr-conversion` for Darwin. Boost 1.70 headers trigger a hard error in Clang 17.
6. **configure.ac**: Fallback when `AX_BOOST_THREAD` fails (darwin + Clang 17). If `BOOST_THREAD_LIB` is empty but `libboost_thread.a` exists in the Boost lib dir, add `-lboost_thread` explicitly. Uses `sed 's/.*-L//;s/ .*//'` to extract lib path from `BOOST_LDFLAGS`.

Alternatives for the sed approach:
- Write `project-config.jam` directly (what Bitcoin Core does).
- Use `user-config.jam` override file.
- Current approach is adequate while Boost stays at 1.70.

### 3.2 openssl.mk

OpenSSL 1.1.1a to 1.1.1w.

- Preprocess steps use `$(build_SED_INPLACE)`. See section 1.1.
- 1.1.1a (2018) has no `darwin64-arm64-cc` target.
- 1.1.1w is the final 1.1.1 LTS release (Sep 2023). Updated download URL (GitHub releases) and SHA256.
- Added `$(package)_config_opts_aarch64_darwin=darwin64-arm64-cc`.
- OpenSSL 1.1.1 is EOL. Future: remove or migrate to 3.x. See section 6.9.

### 3.3 rust.mk

System Rust for ARM Mac.

- Rust 1.32.0 (Jan 2019) has no `aarch64-apple-darwin` binaries.
- Added conditional: on native ARM Mac builds, skip download and symlink system `rustc`/`cargo` into the depends tree.
- Original 1.32.0 download path is completely unchanged for all other platforms.
- librustzcash at commit `06da3b9` uses Rust edition 2015, compatible with modern Rust.

Alternatives:
- **Current (symlink)**: Simple, works for local dev. Couples build to system Rust.
- **Pin a modern Rust version**: Update `rust.mk` to download e.g. Rust 1.81+ with `aarch64-apple-darwin` hashes. Fully deterministic.
- **Recommendation**: Pin a modern version for CI. Symlink is adequate for development.

### 3.4 bdb.mk

BerkeleyDB 6.2.23. Two changes:

1. **ARM64 mutex**: Added
   `$(package)_config_opts_aarch64_darwin=--with-mutex=POSIX/pthreads/library`.
   BDB 6.2.23 default mutex selection fails at runtime on ARM64 macOS with
   `DB_LOCK_NOTGRANTED`. This supplements the existing generic
   `$(package)_config_opts_aarch64=--disable-atomicsupport`.
   Becomes unnecessary after BDB 6.2.32 upgrade (section 6.1).

2. **sed portability**: Preprocess steps now use `$(build_SED_INPLACE)`.
   Removed redundant `sed -i -e` line that duplicated the WinIoCtl.h
   replacement and failed on macOS. See section 1.1.

### 3.5 libsodium.mk

URL fix only. Old download path at `download.libsodium.org` returned 404.
Updated to GitHub releases. Same version (1.0.15), same SHA256.

### 3.6 config.guess and config.sub

Replaced 2015 versions with 2025 versions from GNU Savannah. The 2015
`config.guess` misidentified ARM Mac as `arm-apple-darwin` instead of
`aarch64-apple-darwin`, causing cascading build failures. These are
standard vendor files; full replacement is the normal update procedure.

## 4. Source Build Fixes

### 4.1 equihash.cpp

Added `#ifdef ENABLE_MINING` / `#endif` around `Equihash<192,7>::BasicSolve`
and `Equihash<192,7>::OptimisedSolve` explicit template instantiations.
The `<48,5>` variants already had this guard. The member functions are
guarded in the header; the `.cpp` instantiations must match. Without this,
builds with `--enable-mining=no` fail to link.

### 4.2 hash.h (CHash256, CHash160)

**Issue:** `unsigned char buf[sha.OUTPUT_SIZE]` triggered Clang VLA warning
(`variable length arrays in C++ are a Clang extension`).

**Type:** `OUTPUT_SIZE` is `static const size_t` in `CSHA256` (32) and
`CRIPEMD160` (20). `sha.OUTPUT_SIZE` and `CSHA256::OUTPUT_SIZE` are the same
value, but the compiler treats `sha.OUTPUT_SIZE` in an array bound as
potentially non-constant (member access).

**Macro:** None; no preprocessor macros involved.

**Override:** `config.site` or `CXXFLAGS` could add `-Wno-vla-cxx-extension` to
suppress the warning, but that hides the issue.

**Fix:** Use `CSHA256::OUTPUT_SIZE` instead of `sha.OUTPUT_SIZE` for the
intermediate buffer. Both CHash256 and CHash160 use a 32-byte SHA-256
intermediate; the size is a compile-time constant.

**Comparison:** Zcash and Bitcoin use `buf[CSHA256::OUTPUT_SIZE]`. Pirate uses
`sha.OUTPUT_SIZE` in the legacy `Finalize(unsigned char*)` overload but
`CSHA256::OUTPUT_SIZE` in the `Finalize(Span)` overload.

**Pirate Span output:** Pirate adds `Finalize(Span<unsigned char> output)` (or
`std::span`). The caller passes a non-owning view of the output buffer; the
function writes the hash into that span. Benefits: (1) caller controls storage
(stack, vector, array); (2) no pointer+length pair; (3) span carries size, so
`assert(output.size() == OUTPUT_SIZE)` enforces bounds. The span is the output
parameter; internally Pirate still uses `buf[CSHA256::OUTPUT_SIZE]` for the
intermediate SHA-256 result, then copies to `output.data()`.

### 4.3 Build Warnings (non-fatal)

**Definitions override:** Automake pre-defines variables and targets. When
`Makefile.am` assigns to the same name, the user definition overrides the
built-in. The last definition wins.

**Overridden variables in `Makefile.am`:**

| Variable/target | User value | Purpose |
|-----------------|------------|---------|
| `GZIP_ENV` | `"-9n"` | Gzip flags for `make dist` (max compression, no name). |
| `distcleancheck` | `@:` (no-op) | See below. |

**distcleancheck:** Automake's default `distcleancheck` runs during `make
distcheck`. It verifies the source tree is clean after extracting the tarball,
configuring, building, and running `make distclean`—i.e. no leftover generated
files. Zero overrides it with `@:` (no-op) so the check is skipped. Common
reasons: vendored subdirs (leveldb, secp256k1) or custom dist-hooks leave
artifacts; the project uses `distcheck-hook` for leveldb instead.

**Comparison (Pirate, Zcash):**

| Variable/target | Zero | Pirate | Zcash |
|-----------------|------|--------|-------|
| `GZIP_ENV` | `"-9n"` | `"-9n"` | not set |
| `distcleancheck` | `@:` | `@:` | not set |
| `dist-hook` | leveldb clean, secp256k1 distclean, git archive | same | git archive only |
| `distcheck-hook` | leveldb copy + clean | same | not present |

Pirate matches Zero. Zcash has simplified: no GZIP_ENV or distcleancheck
override; dist-hook only archives clientversion; no distcheck-hook (leveldb
handled differently or no longer vendored).

Override is intentional. The warning appears because Automake detects the
name collision.

| Warning | Status | Fix |
|---------|--------|-----|
| **libzcash_a_LDFLAGS** | Fixed | Removed. Static libs (`.a`) do not use LDFLAGS; variable was unused. |
| **AC_PROG_CC_C89 obsolete** | Fixed | Replaced with `AC_PROG_CC` in `src/secp256k1/configure.ac`. |
| **ignoring duplicate libraries: '-lc++'** | Open | Libtool adds `-lc++`; `-stdlib=libc++` (Darwin) also pulls it in. Harmless. |
| **GZIP_ENV / distcleancheck override** | Intentional | User definitions override Automake defaults. See above. |

### 4.4 test_miner and --disable-mining

When `--enable-mining=no`, `GetScriptForMinerAddress` is not compiled (miner.cpp
wrapped in `#ifdef ENABLE_MINING`). `test_miner.cpp` still references it and
fails to link.

**Solution:** Conditionally exclude `test_miner.cpp` from the GTest build.

In `src/Makefile.gtest.include`, remove `gtest/test_miner.cpp` from the main
`zero_gtest_SOURCES` block and add:

```
if ENABLE_MINING
zero_gtest_SOURCES += gtest/test_miner.cpp
endif
```

## 5. Library Versions

### 5.1 Core Libraries

| Package | Current | Target | Status |
|---------|---------|--------|--------|
| BerkeleyDB | 6.2.32 | 6.2.32 | ✓ At target |
| libsodium | 1.0.21 | 1.0.21 | ✓ At target |
| libevent | 2.1.12 | 2.1.12 | ✓ At target |
| ZeroMQ | 4.3.5 | 4.3.5 | ✓ At target |
| Boost | 1.70.0 | Postponed | Intentionally not upgraded |
| OpenSSL | 1.1.1w | TBD | EOL; keep for now |

### 5.2 Rust Toolchain

| Package | Current | Target | Status |
|---------|---------|--------|--------|
| Rust (in rust.mk) | 1.32.0 / system | 1.93.1 | Not upgraded; ARM Mac uses system 1.91.1 |
| librustzcash | 0.1 (06da3b9) | Deferred | Tied to protocol version |

### 5.3 Build Tools

| Package | Current | Target | Status |
|---------|---------|--------|--------|
| ccache | 4.12.2 | 4.12.2 | ✓ At target |
| utfcpp | 3.1 | 4.0.9 | Deferred |
| Qpid Proton | 0.26.0 | 0.39.0 | Disabled |

Google Test version tracking is in UpdateTests.md section 1.1.

### 5.4 Vendored Rust Crates

Pinned in `depends/packages/crate_*.mk`, compiled into `librustzcash`.
Versions locked by `Cargo.lock` at commit `06da3b9`.

| Crate | Version | Notes |
|-------|---------|-------|
| bellman | 0.1.0 | Zcash proving system |
| pairing | 0.14.2 | Elliptic curve pairing |
| sapling-crypto | 0.0.1 | Sapling circuit |
| rand | 0.4.3 | Deprecated; modern is 0.8+ |
| byteorder | 1.2.7 | Stable |
| libc | 0.2.45 | Stable |
| lazy_static | 1.2.0 | Stable |

## 6. Upgrade Plan

Prioritized by risk. Target baseline: Zcash v6.11.0 or Bitcoin Core v30.2,
whichever is higher and applicable. See section 7 for cross-project
version comparison.

### 6.1 BerkeleyDB 6.2.23 → 6.2.32

**Done.** `bdb.mk` at 6.2.32. ARM64 mutex fixed natively; `--with-mutex` workaround removed. See UpdateFeatures.md §4.1 for wallet compatibility.

BDB version and license context:

| Version | License | DB Format | ARM64 | Notes |
|---------|---------|-----------|-------|-------|
| 5.3.28 | Sleepycat | 5.x | — | Last non-AGPL. Incompatible wallet format. |
| 6.2.23 (current) | AGPLv3 | 6.2 | Broken mutex | Needs workaround. |
| 6.2.32 (target) | AGPLv3 | 6.2 | Fixed | Drop-in upgrade. |
| 18.1.40 (latest) | AGPLv3 | 6.2-compat | Full | Unnecessary version jump. |

### 6.2 libsodium 1.0.15 → 1.0.21

**Done.** `libsodium.mk` at 1.0.21.

### 6.3 libevent 2.1.8 → 2.1.12

**Done.** `libevent.mk` at 2.1.12.

### 6.4 ZeroMQ 4.3.1 → 4.3.5

**Done.** `zeromq.mk` at 4.3.5.

### 6.5 ccache 3.3.1 → 4.12.2

**Done.** `native_ccache.mk` at 4.12.2.

### 6.6 Boost 1.70.0

**Postponed.** High risk. Major version jump.

**Zero starting point:** 1.70.0 (Jun 2019). ~6 years, 13+ minor versions behind Zcash.

**Boost support among projects:**

| Version | Projects |
|---------|----------|
| 1.70.0 | Zero, Fluxd |
| 1.72.0 | HUSH |
| 1.80.0 | Zclassic |
| 1.82.0 | Horizen |
| 1.83.0 | Zcash v6.11.0, Pirate |
| 1.88.0 | Bitcoin Core v30.2 |
| 1.90.0 | Latest |

**Upgrade choices when ready:**

| Version | Validated by | Notes |
|---------|--------------|-------|
| 1.83.0 | Zcash, Pirate | Zcash `boost.mk` provides tested path. API changes in Filesystem, Thread, Test. |
| 1.88.0 | Bitcoin Core | Bitcoin `depends/packages/boost.mk` reference. |
| 1.90.0 | Latest | Newest; least upstream validation. |

**Recommendation:** Target 1.83.0 (Zcash-validated) for lowest risk. Keep 1.70.0 until upgrade is scheduled.

### 6.7 Rust 1.32.0 to 1.93.1

Confirmed. Medium risk. Target latest stable (1.93.1).

librustzcash at commit `06da3b9` is edition-2015 code and compiles with
any modern Rust. No edition-specific features exercised.

Action: rewrite `rust.mk` to download pinned version with
`aarch64-apple-darwin` hashes. Reference Zcash `native_rust.mk`.
Replaces system symlink approach with deterministic pinned download.

### 6.8 OpenSSL

**Postponed.** Separate effort. Requires detailed validation strategy before proceeding.

**Current understanding** (see UpdateFeatures.md §4.2):
- Zero uses OpenSSL for RPC TLS and legacy crypto paths.
- 1.1.1w is EOL (final 1.1.1 release, Sep 2023); no further security fixes.
- Zcash and Bitcoin Core removed OpenSSL; Zero, Horizen, Fluxd, Zclassic still carry it.
- Options: (1) Keep 1.1.1w short-term; (2) Remove (audit call sites, use libsodium+libsecp256k1); (3) Migrate to 3.5.x LTS (API migration).

**Before proceeding**: Audit all OpenSSL call sites; document TLS/crypto usage; define validation strategy (unit tests, integration tests, TLS handshake verification, deployment compatibility). Do not mix with Boost or other upgrades.

### 6.9 librustzcash

Deferred. Tied to protocol/consensus version. Upgrade only alongside
network upgrade. Current snapshot is Sapling-era; modern librustzcash is
a monorepo of many crates.

### 6.10 Qpid Proton

Deferred. Currently disabled (`--enable-proton=no`). Optional AMQP
messaging. Re-evaluate if needed.

Google Test upgrade is tracked in UpdateTests.md section 1.1.

## 7. Cross-Project Library Versions

How each Zcash-family project versions its core dependencies. Referenced
from UpdateZero.md section 6.2 and UpdateFeatures.md section 4.

Google Test is tracked separately in UpdateTests.md section 1.1.

| Library | Zero | Zcash | Horizen | Pirate | Fluxd | Zclassic | HUSH | Bitcoin | Latest | Target |
|---------|------|-------|---------|--------|-------|----------|------|---------|--------|--------|
| BerkeleyDB | 6.2.32 | 6.2.23 | 6.2.23 | 6.2.32 | 6.2.23 | 6.2.23 | 6.2.23 | (removed) | 6.2.32 | ✓ |
| libsodium | 1.0.21 | 1.0.20 | 1.0.18 | 1.0.18 | 1.0.15 | 1.0.15 | 1.0.18 | — | 1.0.21 | ✓ |
| libevent | 2.1.12 | 2.1.12 | 2.1.8 | 2.1.12 | 2.1.12 | 2.1.8 | 2.1.8 | 2.1.12 | 2.1.12 | ✓ |
| ZeroMQ | 4.3.5 | 4.3.5 | 4.3.4 | 4.3.1 | 4.3.1 | 4.3.1 | (removed) | 4.3.5 | 4.3.5 | ✓ |
| ccache | 4.12.2 | 4.11.3 | 3.3.1 | — | 3.3.1 | 3.3.1 | 3.3.1 | — | 4.12.2 | ✓ |
| Boost | 1.70.0 | 1.83.0 | 1.82.0 | 1.83.0 | 1.70.0 | 1.80.0 | 1.72.0 | 1.88.0 | 1.90.0 | Postponed |
| Rust | 1.32.0 | 1.81.0 | 1.70.0 | 1.69.0 | 1.32.0 | 1.32.0 | 1.32.0 | — | 1.93.1 | **1.93.1** |
| OpenSSL | 1.1.1w | (removed) | 1.1.1w | — | 1.1.1a | 1.1.1a | (none) | (removed) | 3.6.1 | TBD |

Zero at target for BDB, libsodium, libevent, ZeroMQ, ccache. Boost postponed. Rust and OpenSSL not upgraded.

### 7.1 BerkeleyDB

All Zcash-family projects use BDB 6.2.x (AGPLv3). Pirate already
upgraded to 6.2.32, confirming the path is safe. Oracle documentation
confirms DB file format did not change between 6.2 and 18.1.

Bitcoin Core removed BerkeleyDB entirely:
- v0.21 (2020): SQLite-backed descriptor wallets introduced.
- v23.0 (2022): descriptor wallets became default.
- v24.0 (2022): `migratewallet` RPC added.
- v26+ (2023+): legacy BDB wallet creation deprecated.

No Zcash-family project has implemented this migration.

### 7.2 Boost

**Choices:** 1.83.0 (Zcash), 1.88.0 (Bitcoin Core), 1.90.0 (latest).

Zero and Fluxd use 1.70.0. The jump to 1.83 spans ~6 years and 13 minor
versions, with API changes in Filesystem, Thread, and Test. Zcash
`boost.mk` provides a tested upgrade path for 1.83.0. Prefer 1.83.0 when
upgrading.

### 7.3 Rust

Target: 1.93.1 (latest). Zero's librustzcash is edition-2015 code that
compiles with any modern Rust. Pinning to a specific version with
download hashes replaces the current system-Rust symlink.

### 7.4 OpenSSL

**Postponed.** Separate effort. See §6.8 and UpdateFeatures.md §4.2.

Projects: Zcash, Bitcoin (removed); HUSH (WolfSSL); Zero, Horizen, Fluxd, Zclassic (1.1.1x). Zero on 1.1.1w (EOL). Requires call-site audit and validation strategy before any change.

## 8. Reference Repositories

Cloned to `~/Work/ZK/` for comparison.

| Project | Repo | Version | Date | Upstream |
|---------|------|---------|------|----------|
| Bitcoin Core | bitcoin-src | v30.2 | Jan 2026 | github.com/bitcoin/bitcoin |
| Zcash | zcash | v6.11.0 | Jan 2026 | github.com/zcash/zcash |
| HUSH | hush3 | v3.10.4 | Jul 2025 | git.hush.is/hush/hush3 |
| Zclassic | zclassic | v2.1.1.60 | Dec 2024 | github.com/ZclassicCommunity/zclassic |
| Horizen | zen | v6.0.0 | Jul 2025 | github.com/HorizenOfficial/zen |
| Fluxd | fluxd | v9.0.6 | Dec 2024 | github.com/RunOnFlux/fluxd |
| Pirate | pirate | v5.9.0 | Sep 2024 | github.com/PirateNetwork/pirate |
| Zero | ZeroMac | arm-mac-build | Feb 2026 | github.com/zerocurrencycoin/zero |

HUSH and Pirate local clones are shallow (single squashed commit).
