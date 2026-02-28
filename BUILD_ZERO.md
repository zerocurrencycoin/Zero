# BUILD_ZERO

Build guide for the Zero node (zerod). Quick Start, data directory layout, and developer build knowledge. For zerod vs zerowallet toolchains, see [BUILD.md](BUILD.md).

---

## 1. Introduction

Zero is a Zcash-family cryptocurrency node. This document describes how to build zerod from source on Linux, macOS ARM64, and Windows (generic). Dev and test target for macOS is ARM64; for Linux, Ubuntu 24.04. The build uses autotools with a `depends/` system for deterministic dependency builds. Each platform has specific toolchain and configure requirements.

**Requirements:** Full build: Mac &lt;6 GB, Linux &lt;5 GB disk. 4-core 16 GB RAM compiles promptly; 2 CPU 4 GB manages. GCC 7.0+, GNU Make 4.0+, Python 3.6+, Git 2.0+. C++14 required (Boost 1.88).

---

## 2. Quick Start

### 2.1 General

```bash
git clone https://github.com/zerocurrencycoin/Zero.git
cd Zero
./zcutil/fetch-params.sh
./zcutil/build.sh -j4
```

Binaries: `src/zerod`, `src/zero-cli`, `src/zero-tx`. zerowallet is a separate application (zerowalletmac, zerowalletlinux, zerowalletwin repos).

### 2.2 Linux x86_64

**OS tested:** Ubuntu 24.04 only.

**Packages:**
```bash
sudo apt update
sudo apt install build-essential pkg-config libc6-dev m4 g++-multilib \
  autoconf libtool ncurses-dev unzip git python3 python3-zmq \
  zlib1g-dev wget bsdmainutils automake cmake curl
```

**Build:**
```bash
./zcutil/fetch-params.sh
./zcutil/build.sh -j$(nproc)
```

**Output:** `src/zerod`, `src/zero-cli`, `src/zero-tx`.

### 2.3 macOS ARM64

**OS tested:** macOS 24.5.0 (darwin 24.5.0).

**Prerequisites:**
```bash
brew install automake cmake pkg-config coreutils
```

**Build:**
```bash
./zcutil/fetch-params.sh
./zcutil/build.sh -j4
```

**Output:** `src/zerod`, `src/zero-cli`, `src/zero-tx`.

### 2.4 Windows

**Cross-compile from Linux** (recommended):

```bash
sudo apt install mingw-w64 build-essential
./zcutil/build-win.sh -j$(nproc)
```

Output: `src/zerod.exe`, `src/zero-cli.exe`, `src/zero-tx.exe`.

**Manual steps** (if not using build-win.sh): depends with `HOST=x86_64-w64-mingw32`; configure with `--disable-zmq --disable-rust`, posix threads (`-gcc-posix`), CXXFLAGS for PTW32/BN128; sed fix for boost_system-mt; make in src/.

**WSL2:** Use Linux instructions; build and run inside WSL2.

**Data dir:** `%APPDATA%\zero`. **Params:** `%APPDATA%\ZcashParams`. Firewall: allow zerod.exe. Antivirus may need to whitelist binaries.

---

## 3. .zero Directory

### 3.1 Location

| Platform | Data directory | Params directory |
|----------|----------------|------------------|
| Linux | `~/.zero` | `~/.zcash-params` |
| macOS | `~/Library/Application Support/zero` | `~/Library/Application Support/ZcashParams` |
| Windows | `%APPDATA%\zero` | `%APPDATA%\ZcashParams` |

Override with `-datadir=<path>`.

### 3.2 Files

See [doc/files.md](doc/files.md) for details.

| File/dir | Purpose |
|----------|---------|
| zero.conf | Configuration |
| zerod.pid | Process ID while running |
| blocks/blk000??.dat | Block data (128 MiB per file) |
| blocks/rev000??.dat | Block undo data |
| blocks/index/* | Block index (LevelDB) |
| chainstate/* | Chain state (LevelDB) |
| database/* | BDB environment |
| db.log | Wallet DB log |
| debug.log | Debug output |
| fee_estimates.dat | Fee statistics |
| peers.dat | Peer database |
| wallet.zero | Wallet (BDB) |
| .cookie | RPC auth cookie |

### 3.3 Size Estimates

| Component | Approx. size |
|-----------|--------------|
| .zero (full sync) | under 8 GB |
| .zcash_params (Sapling only) | ~800 MB |
| Fresh .zero (no chain) | &lt;50 MB |

**Sync time:** ~6–10 hours for full chain (varies by network and disk).

### 3.4 Zcash Params

Run `./zcutil/fetch-params.sh` before first start. Zero fetches Sapling params only (~800 MB). Sprout params are not used. Source: `https://download.z.cash/downloads`. If present and checksum-valid, no download occurs.

**Planned:** Backup, blockchain snapshot, sample files, params mirror.

---

## 4. Developer Knowledge

### 4.1 Versions Used

| Package | Version |
|---------|---------|
| BerkeleyDB | 6.2.32 |
| Boost | 1.88.0 |
| OpenSSL | 1.1.1w |
| libsodium | 1.0.21 |
| libevent | 2.1.12 |
| ZeroMQ | 4.3.5 |
| ccache | 4.12.2 |
| Rust (depends) | Pinned current (macOS ARM64); 1.32.0 (Linux/Win). Note: test pinned Rust on Windows and Linux. |

**ZMQ:** ZeroMQ 4.3.5 is built and used by default for block/tx notifications (`-zmqpubhashblock`, `-zmqpubhashtx`, etc.). AMQP 1.0 (via Qpid Proton 0.26.0) would provide the same role with `-amqppub*`; we do not use it. Proton is not built or downloaded; disabled since 2017 (gcc/CMake issues).

### 4.2 Build Flow

1. `depends/` builds libraries into `depends/$HOST/` (bin, include, lib, share).
2. `./autogen.sh` generates configure.
3. `./configure` with `CONFIG_SITE=$PWD/depends/$HOST/share/config.site`.
4. `make` builds zerod, zero-cli, zero-tx.

**zcutil/build.sh** runs steps 1–4 in one command. It sets `HOST` via `depends/config.guess`, builds depends, runs autogen, configure, and make.

### 4.3 config.site

`depends/$HOST/share/config.site` is generated from `depends/config.site.in` when depends is built. It is sourced by `./configure` when `CONFIG_SITE` is set. It preconfigures:

- **CC, CXX:** Host compiler (from `depends/hosts/*.mk`). For Windows: `x86_64-w64-mingw32-gcc-posix`, `x86_64-w64-mingw32-g++-posix`.
- **CFLAGS, CXXFLAGS, CPPFLAGS, LDFLAGS:** From host config.
- **PKG_CONFIG_LIBDIR, PKG_CONFIG_PATH:** Point to `depends/$HOST/lib/pkgconfig` and `share/pkgconfig`.
- **Prefix:** `-I$depends_prefix/include`, `-L$depends_prefix/lib` so configure finds depends-built libraries.

Without `CONFIG_SITE`, configure would use system compilers and paths.

**Source:** `depends/config.site.in`; template variables `@CC@`, `@CXX@`, `@host_os@`, etc. are substituted by `depends/Makefile` when building `depends/$HOST/share/config.site`.

### 4.4 zcutil/build.sh

```
./zcutil/build.sh [ --enable-lcov | --disable-tests ] [ --disable-mining ] [ --enable-proton ] [ --daemon ] [ MAKEARGS... ]
```

- `--daemon`: `--disable-zmq --disable-rust` for configure. Aligns with build-win.sh.
- Flags must come before `-jN` and other make args.
- `-jN` capped at 4 by default; use `-j$(nproc)` or `-j$(sysctl -n hw.ncpu)` to override.
- `CONFIGURE_FLAGS` passed to configure; multi-word values need escaping, e.g. `CONFIGURE_FLAGS='CXXFLAGS=-g\ -Wno-enum-constexpr-conversion'`.

### 4.5 Variables and Overrides

| Variable | Purpose |
|----------|---------|
| `CC`, `CXX` | Compiler override |
| `MAKE` | Make command (e.g. `gmake`) |
| `BUILD`, `HOST` | Triplet for porters |
| `CONFIGURE_FLAGS` | Extra configure options |
| `CCACHE_DIR` | ccache cache (optional). ccache 4.12.2 in depends; `ccache -M 5G` for size. |

### 4.6 Intermediate Results

- Depends: `depends/$HOST/` (e.g. `x86_64-unknown-linux-gnu`, `aarch64-apple-darwin25.3.0`).
- Binaries: `src/zerod`, `src/zero-cli`, `src/zero-tx`.
- Tests: `contrib/run-tests.sh`; logs in `test-logs/`. See [TEST_ZERO.md](TEST_ZERO.md).

### 4.7 Configure Options

| Option | Purpose |
|--------|---------|
| `--disable-wallet` | Daemon only (servers) |
| `--enable-debug` | Debug symbols |
| `--disable-mining` | Exclude mining code |
| `--enable-ccache` | Use ccache (default: auto) |

---

## 5. Per-Platform Detail

### 5.1 Linux x86_64

**Compiler:** GCC. Need GCC 7.0+ for C++14.

**Depends:** `make -C depends/` uses `config.guess` for HOST. Output: `depends/x86_64-unknown-linux-gnu/`.

**Configure:** `CONFIG_SITE=$PWD/depends/x86_64-unknown-linux-gnu/share/config.site ./configure --enable-hardening`.

**Portable sed:** Depends use `sed -i.old` for in-place edits (BSD/GNU compatible).

### 5.2 macOS ARM64

**Compiler:** Apple Clang. No GCC.

**Prerequisites:** `automake`, `cmake`, `pkg-config`, `coreutils` (for `gnproc`).

**Host triplet:** `aarch64-apple-darwin*` from config.guess (e.g. darwin24.5.0, darwin25.3.0).

**Configure:** (HOST from `./depends/config.guess` or `build.sh`)
```bash
CONFIG_SITE=$PWD/depends/$HOST/share/config.site \
./configure --enable-hardening --enable-proton=no --enable-mining \
  CXXFLAGS="-g -Wno-enum-constexpr-conversion"
```

- `--enable-proton=no`: Qpid Proton incompatible with CMake 4.x.
- `-Wno-enum-constexpr-conversion`: Boost/Clang 17 compatibility.

**Rust:** Depends pins current system Rust on macOS ARM64 (1.32.0 has no aarch64 binaries). Test same pinned approach on Windows and Linux.

**BDB:** If `database` mutex crash: `rm -rf "$HOME/Library/Application Support/zero/database"`.

### 5.3 Windows

**Cross-compile from Linux:** `./zcutil/build-win.sh -j$(nproc)`. Requires `mingw-w64` (posix threads). See §2.4.

**Toolchain:** zerod uses system mingw-w64 directly (`apt install mingw-w64`). No MXE. Compilers: `x86_64-w64-mingw32-gcc-posix`, `x86_64-w64-mingw32-g++-posix`.

**build-win.sh flow:**

1. **Depends:** `make HOST=x86_64-w64-mingw32` in `depends/`. Includes `depends/hosts/mingw32.mk`, which sets `mingw32_CC`, `mingw32_CXX` to the posix compilers and `mingw32_CFLAGS`/`mingw32_CXXFLAGS` (e.g. `-fopenmp`, `-DPTW32_STATIC_LIB`). Builds Boost, OpenSSL, libevent, etc. for Windows. Output: `depends/x86_64-w64-mingw32/` (include, lib, share).

2. **config.site:** Depends generates `depends/x86_64-w64-mingw32/share/config.site` with CC, CXX, CFLAGS, CXXFLAGS, LDFLAGS, PKG_CONFIG paths. See §4.3.

3. **Configure:** `CONFIG_SITE=$PWD/depends/x86_64-w64-mingw32/share/config.site ./configure --host=x86_64-w64-mingw32 --enable-static --disable-shared --disable-zmq --disable-rust` plus CXXFLAGS for PTW32_STATIC_LIB, CURVE_ALT_BN128, -fopenmp, -pthread.

4. **Sed fix:** `sed -i 's/-lboost_system-mt /-lboost_system-mt-s /' configure` — configure emits shared boost lib; MinGW static build needs `-lboost_system-mt-s`.

5. **Make:** `CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix make zerod.exe zero-cli.exe zero-tx.exe` in `src/`.

**mingw32.mk:** `depends/hosts/mingw32.mk` defines compiler and flags. When `HOST=x86_64-w64-mingw32`, `depends/Makefile` sets `host_os=mingw32` and includes this file. All depends packages (Boost, OpenSSL, etc.) use these settings.

**Native/WSL:** Use Linux instructions inside WSL2.

---

## 6. Detecting, Diagnosing, Troubleshooting

### 6.1 Params Missing

```
Please run 'zero-fetch-params' or './zcutil/fetch-params.sh' and then restart.
```

Run `./zcutil/fetch-params.sh` before starting zerod.

### 6.2 Berkeley DB

**Version:** BDB 6.2.32 only (from `depends/packages/bdb.mk`). Used for wallet storage (`wallet/walletdb.cpp`, `wallet/db.cpp`).

**Not found:** Ensure depends built: `ls depends/$HOST/lib/libdb*`.

**Mutex crash (macOS):** Remove `database/` in data dir and restart.

### 6.3 Boost / GCC

**GCC too old:** Need GCC 7.0+ for C++14.

### 6.4 Memory Exhausted

**"virtual memory exhausted" or "killed":** Reduce jobs: `make -j1 zerod`. Or add swap.

### 6.5 Mining Disabled

With `--disable-mining`, `test_miner` is excluded from tests. Equihash template instantiations are guarded by `ENABLE_MINING`.

### 6.6 zerowallet

zerowallet (Qt GUI) is built from separate repos. This repo builds only zerod, zero-cli, zero-tx. See [BUILD.md](BUILD.md) for zerod vs zerowallet toolchains.

### 6.7 Clean Rebuild

```bash
make clean && make distclean
cd depends && make clean && cd ..
./autogen.sh
CONFIG_SITE=$PWD/depends/$HOST/share/config.site ./configure ...
make -j4
```

### 6.8 Build Log

```bash
make -j4 2>&1 | tee build.log
grep -i error build.log
```

