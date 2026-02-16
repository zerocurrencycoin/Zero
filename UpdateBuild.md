# UpdateBuild

Build system changes, dependency management, platform setup, and library
upgrade planning for the Zero node.

## 1. Build System Overview

Zero uses autotools with a `depends/` system for deterministic dependency
builds. Each library has a `.mk` recipe in `depends/packages/` specifying
version, download URL, SHA256, and per-platform build options. GNU
`config.guess` and `config.sub` detect the host triplet.

## 2. Platform Setup

### 2.1 Linux x86_64

Standard build with `depends/`. Primary development and validation
platform. No changes to the Linux build path in this update. Regression
testing required to confirm shared changes (download URLs, sed patterns)
do not break existing builds.

### 2.2 Windows

Cross-compiled via MinGW. Primary user deployment platform. No changes
to the Windows build path in this update. Regression testing required.

### 2.3 macOS ARM64

New platform addition.

- Host triplet: `aarch64-apple-darwin24.5.0`
- Compiler: Apple Clang 17.0
- System Rust: 1.91.1
- Homebrew prerequisites: `automake`, `cmake`, `pkg-config`

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

## 3. Depends Changes

### 3.1 boost.mk

Boost 1.70.0. Five changes:

1. **Download URL**: `dl.bintray.com` to `archives.boost.io`. Bintray shut down 2021.
2. **Toolset**: `--toolset=darwin-4.2.1` to `--toolset=clang`. Old darwin toolset injects `-fcoalesce-templates`, unsupported by modern Clang.
3. **Toolset/archiver variables**: `$(package)_toolset_darwin=clang` and `$(package)_archiver_darwin=$($(package)_ar)` for consistency with toolset change.
4. **sed portability**: `sed -i -e` to `sed -i.old`. BSD sed on macOS requires backup extension. Pattern broadened from `using gcc ;` to `using [a-z]* ;` to match whatever toolset bootstrap selects.
5. **CXXFLAGS**: Added `-Wno-enum-constexpr-conversion` for Darwin. Boost 1.70 headers trigger a hard error in Clang 17.

Alternatives for the sed approach:
- Write `project-config.jam` directly (what Bitcoin Core does).
- Use `user-config.jam` override file.
- Current approach is adequate while Boost stays at 1.70.

### 3.2 openssl.mk

OpenSSL 1.1.1a to 1.1.1w.

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

BerkeleyDB 6.2.23. One line added:

`$(package)_config_opts_aarch64_darwin=--with-mutex=POSIX/pthreads/library`

BDB 6.2.23 default mutex selection fails at runtime on ARM64 macOS with
`DB_LOCK_NOTGRANTED`. This supplements the existing generic
`$(package)_config_opts_aarch64=--disable-atomicsupport`.
Becomes unnecessary after BDB 6.2.32 upgrade (section 6.1).

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

## 5. Library Versions

### 5.1 Core Libraries

| Package | Current | Released | Latest Stable | Released | Gap | Risk | Notes |
|---------|---------|----------|---------------|----------|-----|------|-------|
| Boost | 1.70.0 | Jun 2019 | 1.90.0 | 2025 | ~6y | High | 20 minor versions behind |
| OpenSSL | 1.1.1w | Sep 2023 | 3.6.1 | Jan 2026 | EOL | High | Series end-of-life |
| libsodium | 1.0.15 | Oct 2017 | 1.0.21 | Jan 2025 | ~7y | Low | Stable ABI |
| libevent | 2.1.8 | Jan 2017 | 2.1.12 | Jul 2020 | ~3y | Low | Patch-level |
| BerkeleyDB | 6.2.23 | Mar 2016 | 6.2.32 | Apr 2017 | 1y | Low | Same format/license |
| ZeroMQ | 4.3.1 | Jan 2019 | 4.3.5 | Oct 2023 | ~4y | Low | Patch-level |

### 5.2 Rust Toolchain

| Package | Current | Latest Stable | Gap | Risk | Notes |
|---------|---------|---------------|-----|------|-------|
| Rust (in rust.mk) | 1.32.0 pinned | 1.93.1 | ~7y | Med | Using system 1.91.1 on ARM Mac |
| librustzcash | 0.1 (06da3b9) | Monorepo (2024+) | ~5y | High | Tied to protocol version |

### 5.3 Build Tools

| Package | Current | Latest Stable | Gap | Risk | Notes |
|---------|---------|---------------|-----|------|-------|
| ccache | 3.3.1 | 4.12.2 | ~9y | Low | Build tool only |
| utfcpp | 3.1 | 4.0.9 | ~7y | Low | Header-only |
| Qpid Proton | 0.26.0 | 0.39.0 | ~5y | N/A | Currently disabled |

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

### 6.1 BerkeleyDB 6.2.23 to 6.2.32

Confirmed. Low risk.

Same AGPLv3 license, same DB file format, same ABI. Fixes ARM64
mutex/atomic issues natively. Removes `--with-mutex` workaround in
`bdb.mk`. May also fix `WriteCryptedSaplingZkeyDirectToDb` test hang.
Validated by Pirate v5.9.0. Zcash upstream issue #6977 confirms.
See UpdateFeatures.md section 4.1 for wallet compatibility implications.

Action: update version + SHA256 in `bdb.mk`, remove `--with-mutex` line.

BDB version and license context:

| Version | License | DB Format | ARM64 | Notes |
|---------|---------|-----------|-------|-------|
| 5.3.28 | Sleepycat | 5.x | — | Last non-AGPL. Incompatible wallet format. |
| 6.2.23 (current) | AGPLv3 | 6.2 | Broken mutex | Needs workaround. |
| 6.2.32 (target) | AGPLv3 | 6.2 | Fixed | Drop-in upgrade. |
| 18.1.40 (latest) | AGPLv3 | 6.2-compat | Full | Unnecessary version jump. |

### 6.2 libsodium 1.0.15 to 1.0.20

Confirmed. Low risk. Stable ABI, backward-compatible API. Matches Zcash v6.11.0.

### 6.3 libevent 2.1.8 to 2.1.12

Confirmed. Low risk. Patch-level bump. Matches Zcash, Bitcoin, Pirate, Fluxd.

### 6.4 ZeroMQ 4.3.1 to 4.3.5

Confirmed. Low risk. Patch-level bump. Matches Zcash, Bitcoin.

### 6.5 ccache 3.3.1 to 4.11.3

Confirmed. Low risk. Build tool only, not linked. Better Clang support.
Matches Zcash v6.11.0.

### 6.6 Boost 1.70.0

TBD. High risk. Major version jump.

Zcash v6.11.0 uses 1.83.0. Bitcoin Core v30.2 uses 1.88.0. Latest is
1.90.0. Target likely 1.83.0 (Zcash-validated) but Bitcoin's 1.88.0 is
also production-tested. Upgrading eliminates the
`-Wno-enum-constexpr-conversion` hack and sed toolset workarounds.
Reference Zcash `boost.mk` for the upgrade path.

### 6.7 Rust 1.32.0

TBD. Medium risk.

Zcash v6.11.0 uses 1.81.0. Latest stable is 1.93.1. librustzcash at
commit `06da3b9` is edition-2015 code and compiles with any modern Rust.
Target likely 1.81.0 (Zcash-validated); latest is also viable since the
Rust crate code is simple and edition-2015 compatible.

Action: rewrite `rust.mk` to download pinned version with
`aarch64-apple-darwin` hashes. Reference Zcash `native_rust.mk`.
Replaces system symlink approach with deterministic pinned download.

### 6.8 OpenSSL

TBD. See UpdateFeatures.md section 4.2 for feature implications.

Zcash and Bitcoin Core dropped OpenSSL entirely. Zero still uses it for
RPC TLS and legacy crypto paths. Options:

1. **Keep 1.1.1w** — current version, final 1.1.1 release, EOL. No code
   changes needed. Acceptable short-term.
2. **Remove** — follow Zcash. Requires auditing all OpenSSL call sites and
   confirming libsodium + libsecp256k1 cover all crypto needs.
3. **Migrate to 3.5.x LTS** — supported to Apr 2030. Requires API
   migration (providers model, deprecated low-level functions).

Starting position: keep 1.1.1w. Evaluate removal or 3.5.x migration
as a separate work item.

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
| BerkeleyDB | 6.2.23 | 6.2.23 | 6.2.23 | 6.2.32 | 6.2.23 | 6.2.23 | 6.2.23 | (removed) | 6.2.32 | **6.2.32** |
| libsodium | 1.0.15 | 1.0.20 | 1.0.18 | 1.0.18 | 1.0.15 | 1.0.15 | 1.0.18 | — | 1.0.21 | **1.0.20** |
| libevent | 2.1.8 | 2.1.12 | 2.1.8 | 2.1.12 | 2.1.12 | 2.1.8 | 2.1.8 | 2.1.12 | 2.1.12 | **2.1.12** |
| ZeroMQ | 4.3.1 | 4.3.5 | 4.3.4 | 4.3.1 | 4.3.1 | 4.3.1 | (removed) | 4.3.5 | 4.3.5 | **4.3.5** |
| ccache | 3.3.1 | 4.11.3 | 3.3.1 | — | 3.3.1 | 3.3.1 | 3.3.1 | — | 4.12.2 | **4.11.3** |
| Boost | 1.70.0 | 1.83.0 | 1.82.0 | 1.83.0 | 1.70.0 | 1.80.0 | 1.72.0 | 1.88.0 | 1.90.0 | TBD |
| Rust | 1.32.0 | 1.81.0 | 1.70.0 | 1.69.0 | 1.32.0 | 1.32.0 | 1.32.0 | — | 1.93.1 | TBD |
| OpenSSL | 1.1.1w | (removed) | 1.1.1w | — | 1.1.1a | 1.1.1a | (none) | (removed) | 3.6.1 | TBD |

Bold targets are confirmed. TBD targets have options discussed in
section 6. Confirmed targets match the highest version proven in
production among Zcash v6.11.0 and Bitcoin Core v30.2.

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

Zcash validates 1.83.0, Bitcoin Core validates 1.88.0, latest is 1.90.0.
Zero and Fluxd share the oldest version (1.70.0). The jump from 1.70 to
1.83 spans ~6 years and 13 minor versions, with API changes in
Filesystem, Thread, and Test. Zcash `boost.mk` provides a tested
upgrade path for 1.83.0.

### 7.3 Rust

Zcash uses 1.81.0. Zero's librustzcash is edition-2015 code that
compiles with any modern Rust. Matching Zcash at 1.81.0 is the
conservative choice; latest (1.93.1) is also viable since no
edition-specific features are exercised. Pinning to a specific version
with download hashes replaces the current system-Rust symlink.

### 7.4 OpenSSL

Projects showing "(removed)" or "(none)" handle TLS/crypto differently:

- **Zcash**: dropped OpenSSL. Uses libsodium for crypto, bundled libsecp256k1 for ECDSA.
- **Bitcoin**: dropped OpenSSL. Uses in-tree libsecp256k1.
- **Pirate**: Komodo-based. Never had OpenSSL in depends.
- **HUSH**: replaced OpenSSL with WolfSSL 4.8.1.
- **Zero, Horizen, Fluxd, Zclassic**: still carry OpenSSL for RPC TLS and legacy crypto paths.

OpenSSL 1.1.1w is the final release of the 1.1.1 series (Sep 2023).
There is no newer 1.1.1 patch. The series is EOL with no further
security fixes. Starting position is to keep 1.1.1w; removal or
migration to 3.5.x LTS is a separate evaluation.
See UpdateFeatures.md section 4.2.

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
