# UpdateBuild

Depends recipes, host platforms, and in-tree dependency choices. **Canonical version and rationale:** **§1**. User build steps: **BUILD_ZERO.md**.

---

## 1. Versions and rationale

| Component | In-tree | Source | Rationale / next step |
|-----------|---------|--------|------------------------|
| BerkeleyDB | 6.2.32 | `depends/packages/bdb.mk` | Wallet format 6.2.x; 6.2.32 fixes ARM64 mutex vs 6.2.23. AGPLv3. |
| libsodium | 1.0.21 | `libsodium.mk` | Crypto; URL pinned to GitHub releases. |
| libevent | 2.1.12 | `libevent.mk` | Network stack. |
| ZeroMQ | 4.3.5 | `zeromq.mk` | ZMQ RPC/notifications. |
| Boost | 1.88.0 | `boost.mk` | Test + server; Clang/Darwin toolset and `build_SED_INPLACE` patches in recipe. |
| OpenSSL | 1.1.1w | `openssl.mk` | RPC TLS + legacy call sites. **EOL branch**—defer removal or 3.x migration until call sites audited and tests defined. |
| Rust (depends) | 1.32.0 download; **macOS ARM64** symlinks host `rustc`/`cargo` | `rust.mk` | 1.32.0 has no aarch64-apple-darwin upstream tarball; symlink uses system toolchain. **Target:** pin one modern toolchain for all hosts in `rust.mk`. |
| librustzcash | Snapshot `06da3b9` | crate_*.mk + `Cargo.lock` | Tied to consensus; upgrade only with protocol work. |
| ccache | 4.13.1 | `native_ccache.mk` | Faster rebuilds. |
| Googletest | 1.16.0 | `googletest.mk` | Last GTest on C++14; 1.17+ wants C++17. |
| utfcpp | 3.1 | `utfcpp.mk` | Memo UTF-8 checks in wallet RPC paths; upgrade deferred. |
| Qpid Proton | 0.26.0 recipe; **off** | `proton.mk`, configure | Disabled (`--enable-proton=no`): CMake friction on current hosts. |
| config.guess / config.sub | Current vendor drop | `depends/config.*` | ARM Mac must resolve to `aarch64-apple-darwin*`, not `arm-apple-darwin`. |

**Pinning policy:** Reproducibility (hashed tarballs), known breakage, or CI determinism. Local dev may use system tools when documented in **BUILD_ZERO.md**.

**Rust crates** (representative, full list in `depends/packages/crate_*.mk`): bellman, pairing, sapling-crypto, rand, byteorder, libc, lazy_static—locked with librustzcash snapshot.

---

## 2. Build system mechanics

Autotools + **`depends/`**: each package is a **`depends/packages/*.mk`** recipe (version, URL, hash, host flags). Build-machine helpers use the **`build_`** prefix from **`depends/Makefile`** and **`depends/builders/*.mk`** (e.g. Darwin uses **`shasum -a 256`** where Linux uses **`sha256sum`**).

**Portable sed in-place:** BSD requires **`sed -i.<ext>`**; GNU accepts **`sed -i`**. Project standard: **`build_SED_INPLACE = sed -i.old`** in **`depends/Makefile`**. Used in **`boost.mk`**, **`openssl.mk`**, **`bdb.mk`**.

**fetch_file:** Quoted path in **`test -f`** for dash (**`depends/funcs.mk`**).

**`set -e`:** Avoid **`[[ a ]] && cmd`** when a false condition must not exit the script; use **`if …; then …; fi`**.

**Scripts:** **`zcutil/build-native.sh`** (host resolution, configure flags), **`zcutil/fzero.sh`** (**`FZERO_MAX_JOBS`**, job capping), **`zcutil/build-win.sh`** (Windows cross from Linux). Native Linux/macOS vs Windows cross stay separate entrypoints (different **`HOST`**, artifacts).

---

## 3. Platforms

| Host | Notes |
|------|--------|
| Linux x86_64 | Primary native build; standard **`depends/`** flow. |
| Windows | Cross from Linux: **`HOST=x86_64-w64-mingw32`**, **`build-win.sh`**. |
| macOS ARM64 | Triplet **`aarch64-apple-darwin*`**; **`--enable-proton=no`**; **`-Wno-enum-constexpr-conversion`** for Boost/Clang; BDB issues sometimes cleared by removing a stale **`database/`** under datadir. MacPorts: **`configure.ac`** can add **`/opt/local`**; **`CONFIG_SITE`** from depends should still win for prefix libs. |
| macOS x86_64 | Not supported. |

**Toolchain:** GCC (Linux), Clang (macOS), MinGW-w64 (Windows cross). C++14 baseline.

**Stripping:** Default **`zcutil`** builds do not strip binaries (larger **`zerod`** / **`zero-cli`**). Release packaging may strip separately.

**Autoconf macros:** **`build-aux/m4/`**; **`ax_pthread.m4`** updated where **`$as_echo`** triggered Autoconf deprecation warnings—prefer **`AS_ECHO`** patterns from current autoconf-archive when refreshing macros.

---

## 4. Depends package notes

### 4.1 Boost

1. Version **1.88.0** in **`boost.mk`**.
2. **Toolset:** **`--toolset=clang`** on Darwin (old bootstrap toolsets can inject unsupported flags on Clang).
3. **sed:** **`$(build_SED_INPLACE)`**; pattern adjusts bootstrap toolset line.
4. **CXXFLAGS:** **`-Wno-enum-constexpr-conversion`** on Darwin where needed.
5. **configure.ac:** If **`AX_BOOST_THREAD`** fails on Darwin+Clang, link **`boost_thread`** when the static archive exists.

### 4.2 OpenSSL

Preprocess uses **`$(build_SED_INPLACE)`**. **`darwin64-arm64-cc`** for aarch64 Darwin. **1.1.1** line is EOL; migration or removal is a dedicated effort (audit TLS + legacy EVP usage, then tests).

### 4.3 Rust

Linux/Windows: downloaded toolchain in depends. macOS ARM64: symlink host **`rustc`**/**`cargo`**. **`librustzcash`** at **`06da3b9`** builds with modern Rust when invoked from a modern toolchain.

### 4.4 BerkeleyDB

**6.2.32**; preprocess uses **`$(build_SED_INPLACE)`**. Removed redundant GNU-only **`sed -i -e`** that broke macOS.

### 4.5 libsodium / libevent / zeromq / ccache

At versions in **§1**; routine bumps follow hash + CI build verification.

### 4.6 Googletest

Darwin link warnings vs deployment target: **`googletest.mk`** aligns **`OSX_MIN_VERSION`** with the rest of the graph; rebuild **`depends`** after changing.

---

## 5. Source-tree build fixes

- **`equihash.cpp`:** Template instantiations for mining solvers guarded with **`ENABLE_MINING`** so **`--disable-mining`** links.
- **`hash.h`:** Use **`CSHA256::OUTPUT_SIZE`** for stack buffers to avoid Clang VLA-extension warnings on **`sha.OUTPUT_SIZE`**.
- **secp256k1 `.la`:** **`build.sh`** drops stale **`libsecp256k1.la`** when embedded **`HOST`** disagrees with current **`$HOST`** (macOS OS upgrade / path drift).
- **Automake:** **`GZIP_ENV`**, **`distcleancheck` `@:`** overrides are intentional (vendored trees / dist hooks). **`libzcash_a_LDFLAGS`**-style noise removed where invalid for static archives.
- **secp256k1 configure:** **`AC_PROG_CC`** instead of obsolete C89 macro.
- **ZMQ on Darwin:** Strip duplicate **`-lc++`** from **`libzmq`** private libs when **`libc++`** already selected.
- **GTest:** **`test_miner.cpp`** only in **`zero_gtest_SOURCES`** when **`ENABLE_MINING`** (**`src/Makefile.gtest.include`**).
- **zeronode:** **`SliceHash`** **`memcpy`** source pointer arithmetic corrected (fortify / correctness).
- **budget.cpp:** Sentinel **`4070908800`** → **`int`** truncation is intentional “off” encoding; cast or **`INT_MAX`** if warnings must be silenced.

---

## 6. Deferred upgrades

| Item | Note |
|------|------|
| **Rust pin** | Replace 1.32.0 download + ARM symlink with one pinned modern toolchain for all targets. |
| **OpenSSL** | See **§1**; needs call-site audit and test plan before 3.x or removal. |
| **librustzcash** | With network upgrades only. |
| **Proton** | Revisit only if AMQP path is productized. |
| **utfcpp** | Optional header-only bump. |
| **Boost >1.88** | Requires C++ standard and **`ax_boost_*`** revalidation. |

---

## 7. Peer dependency snapshot

Illustrative versions in other trees (for upgrade planning, not release of this repo):

| Library | Zero | Zcash | Horizen | Pirate | Fluxd | Zclassic | HUSH | Bitcoin |
|---------|------|-------|---------|--------|-------|----------|------|---------|
| BDB | 6.2.32 | 6.2.23 | 6.2.23 | 6.2.32 | 6.2.23 | 6.2.23 | 6.2.23 | removed |
| libsodium | 1.0.21 | 1.0.20 | 1.0.18 | 1.0.18 | 1.0.15 | 1.0.15 | 1.0.18 | — |
| libevent | 2.1.12 | 2.1.12 | 2.1.8 | 2.1.12 | 2.1.12 | 2.1.8 | 2.1.8 | 2.1.12 |
| ZeroMQ | 4.3.5 | 4.3.5 | 4.3.4 | 4.3.1 | 4.3.1 | 4.3.1 | — | 4.3.5 |
| Boost | 1.88.0 | 1.83.0 | 1.82.0 | 1.83.0 | 1.70.0 | 1.80.0 | 1.72.0 | 1.88.0 |
| Rust toolchain | 1.32.0 / symlink | 1.81.0 | 1.70.0 | 1.69.0 | 1.32.0 | 1.32.0 | 1.32.0 | — |
| OpenSSL | 1.1.1w | removed | 1.1.1w | — | 1.1.1a | 1.1.1a | WolfSSL | removed |

Bitcoin Core’s BDB removal and SQLite wallets are not mirrored in Zcash-family nodes.

---

## 8. Reference layout

Local comparison trees often live under **`~/Work/ZK/ZKs/`** (bitcoin-src, zcash, zen, pirate, fluxd, zclassic, hush3, …). **Zero** node checkouts typically **`~/Work/ZK/Zero400`** (or parallel **`ZeroLinux`** / **`ZeroWin`** build dirs).

**`ZKs/Comparison.md`:** PoW, peer logic, Equihash ecosystem notes—separate from this file.

---

## 9. Planned build validation

| Check | Purpose |
|-------|---------|
| **Parity** | Same configure knobs on **`build.sh --daemon`** and **`build-win.sh`** where intended (`--disable-zmq`, `--disable-rust`, …). |
| **Depends smoke** | **`make -C depends HOST=x86_64-w64-mingw32`** succeeds on Linux before full Windows artifact build. |

Optional later: **`config.site`** presence, **`configure --help`** drift vs scripts, PE sanity on Windows outputs.
