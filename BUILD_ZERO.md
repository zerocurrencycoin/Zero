# BUILD_ZERO

Build guide for the Zero node (zerod).

**Quick Start:** §2 — clone, install packages, run build script.  
**Data directory:** §3 — `.zero` location, params, files.  
**Developer:** §4 — versions, build flow, config.site, build.sh flags.  
**Per-platform:** §5 — manual configure, platform quirks (see §2 for basic commands).  
**Troubleshooting:** §6 — params, BDB, memory, clean rebuild.

---

## 1. Introduction

Zero is a Zcash-family cryptocurrency node. Build zerod from source on Linux, macOS ARM64, or Windows (cross-compile from Linux). Tested: Ubuntu 24.04, macOS 24.5.0. Autotools with `depends/` for deterministic dependency builds.

**Requirements:** Mac &lt;6 GB, Linux &lt;5 GB disk. 4-core 16 GB RAM. GCC 7.0+, GNU Make 4.0+, Python 3.6+, Git 2.0+. C++14 (Boost 1.88).

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

**MXE cross-compile (from Linux):**

Windows builds use [MXE](https://mxe.cc/) (M Cross Environment). Build MXE once (2–4 h), then reuse.

**1. Set MXE root** (default `$HOME/mxe`; use `/usr/lib/mxe` for system install):
```bash
export MXE_ROOT="${MXE_ROOT:-$HOME/mxe}"
export MXE_PATH="${MXE_ROOT}/usr/bin"
export PATH="$MXE_PATH:$PATH"
```

**2. Build MXE** (one-time; see [MXE standalone](#24a-mxe-standalone) below if needed).

**3. Build Zero:**
```bash
./zcutil/fetch-params.sh
./zcutil/build-win.sh
```

Or manually:
```bash
HOST=x86_64-w64-mingw32
cd depends && make HOST=$HOST NO_QT=1 -j$(nproc) && cd ..
./autogen.sh
CONFIG_SITE=$PWD/depends/$HOST/share/config.site \
  CXXFLAGS="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" \
  ./configure --prefix=$PWD/depends/$HOST --host=$HOST --enable-static --disable-shared --disable-zmq --disable-rust
sed -i 's/-lboost_system-mt /-lboost_system-mt-s /' configure
cd src && make CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix -j$(nproc) zerod.exe zero-cli.exe zero-tx.exe
```

Binaries: `src/zerod.exe`, `src/zero-cli.exe`, `src/zero-tx.exe`.

**Override MXE location:** `MXE_ROOT=/path/to/mxe ./zcutil/build-win.sh` or `./zcutil/build-win.sh -m /path/to/mxe`

**WSL2:** Use Linux instructions; build and run inside WSL2.

**Data dir:** `%APPDATA%\zero`. **Params:** `%APPDATA%\ZcashParams`. Firewall: allow zerod.exe. Antivirus may need to whitelist binaries.

#### 2.4a MXE standalone

If MXE is not yet built:
```bash
export MXE_ROOT="${MXE_ROOT:-$HOME/mxe}"
sudo apt install -y autoconf automake autopoint bash bison bzip2 flex g++ g++-multilib gettext git gperf intltool libc6-dev-i386 libgdk-pixbuf2.0-dev libltdl-dev libssl-dev libtool-bin libxml-parser-perl make openssl p7zip-full patch perl pkg-config python3-mako python3-setuptools python3-tk python3-venv ruby sed unzip wget xz-utils zstd
git clone https://github.com/mxe/mxe.git "$MXE_ROOT"
cd "$MXE_ROOT" && make MXE_TARGETS='x86_64-w64-mingw32.static' gcc -j$(nproc)
```
Then build Zero as above.

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
- Flags must come before `-jN` and other make args. Example: `./zcutil/build.sh --disable-mining -j4` (correct); `./zcutil/build.sh -j4 --disable-mining` (wrong — flag passed to make).
- `-jN` capped at 4 by default. Linux: `nproc`; macOS: `sysctl -n hw.ncpu` or `gnproc` (from `brew install coreutils`).
- `CONFIGURE_FLAGS` passed to configure; multi-word values need escaping, e.g. `CONFIGURE_FLAGS='CXXFLAGS=-g\ -Wno-enum-constexpr-conversion'`.

### 4.5 Variables and Overrides

| Variable | Purpose |
|----------|---------|
<<<<<<< HEAD
| `CC`, `CXX` | Compiler override |
=======
| `MXE_ROOT` | MXE install root; `MXE_PATH=$MXE_ROOT/usr/bin` (default `$HOME/mxe`; use `/usr/lib/mxe` for system) |
| `CC`, `CXX` | Compiler (e.g. `gcc-11`, `g++-11`) |
>>>>>>> origin/mac_linux_boost188
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

**Compiler:** GCC 7.0+ for C++14.

**Manual build** (if not using build.sh): `make -C depends/` (HOST from config.guess), then `CONFIG_SITE=$PWD/depends/x86_64-unknown-linux-gnu/share/config.site ./configure --enable-hardening`, then `make`.

### 5.2 macOS ARM64

**Compiler:** Apple Clang.

**Manual build:** HOST from `./depends/config.guess`. Configure with `--enable-proton=no` (Proton incompatible with CMake 4.x) and `CXXFLAGS="-g -Wno-enum-constexpr-conversion"` (Boost/Clang 17). See §2.3 for prerequisites.

**Rust:** Depends uses system Rust on ARM64 (1.32.0 has no aarch64 binaries).

**BDB mutex crash:** See §6.2.

### 5.3 Windows

<<<<<<< HEAD
**Cross-compile from Linux:** See §2.4. Toolchain: system mingw-w64 (`apt install mingw-w64`). No MXE.
=======
**Cross-compile:** `HOST=x86_64-w64-mingw32`. Requires MXE with `x86_64-w64-mingw32-gcc-posix` and `x86_64-w64-mingw32-g++-posix`. Set `MXE_ROOT` (default `$HOME/mxe`; `MXE_PATH=$MXE_ROOT/usr/bin`). See §2.4 for full steps.
>>>>>>> origin/mac_linux_boost188

**Manual build:** (1) `make HOST=x86_64-w64-mingw32` in depends; (2) configure with CONFIG_SITE (see §4.3), `--host=x86_64-w64-mingw32 --enable-static --disable-shared --disable-zmq --disable-rust`, CXXFLAGS for PTW32_STATIC_LIB, CURVE_ALT_BN128; (3) sed fix: `sed -i 's/-lboost_system-mt /-lboost_system-mt-s /' configure`; (4) make in src/ with `CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix`.

**WSL2:** Use Linux instructions.

---

## 6. Detecting, Diagnosing, Troubleshooting

### 6.1 Params Missing

```
Please run 'zero-fetch-params' or './zcutil/fetch-params.sh' and then restart.
```

Run `./zcutil/fetch-params.sh` before starting zerod.

### 6.2 Berkeley DB

BDB 6.2.32 (depends). Used for wallet storage.

**Not found:** Ensure depends built: `ls depends/$HOST/lib/libdb*`.

**Mutex crash (macOS):** `rm -rf "$HOME/Library/Application Support/zero/database"` and restart.

### 6.3 Boost / GCC

**GCC too old:** Need GCC 7.0+ for C++14.

### 6.4 Memory Exhausted

**"virtual memory exhausted" or "killed":** Reduce jobs: `make -j1 zerod`. Or add swap.

### 6.5 Mining Disabled

With `--disable-mining`, `test_miner` is excluded from tests. Equihash template instantiations are guarded by `ENABLE_MINING`.

### 6.6 zerowallet

zerowallet (Qt GUI) is built from separate repos (zerowalletmac, zerowalletlinux, zerowalletwin). This repo builds only zerod, zero-cli, zero-tx.

**zerod vs zerowallet toolchains:** zerod uses system GCC (Linux), Clang (macOS), mingw-w64 (Windows). Zerowallet uses Qt; Windows may use MXE for static Qt; static Qt on Linux for Linux may require gcc-11 (Qt struggles with GCC 13 on Ubuntu 24.04).

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

