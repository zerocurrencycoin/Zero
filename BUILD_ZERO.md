# BUILD_ZERO

Build guide for the Zero node (zerod). Quick Start, data directory layout, and developer build knowledge.

---

## 1. Introduction

Zero is a Zcash-family cryptocurrency node. This document describes how to build zerod from source on Linux, macOS ARM64, and Windows (generic). Dev and test target is Ubuntu 24.04; moving forward is the overarching goal, not a design decision. The build uses autotools with a `depends/` system for deterministic dependency builds. Each platform has specific toolchain and configure requirements.

**Requirements:** Full build: Mac &lt;6 GB, Linux &lt;5 GB disk. 4-core 16 GB RAM compiles promptly; 2 CPU 4 GB manages. GCC 7.0+, GNU Make 4.0+, Python 3.6+, Git 2.0+. C++14 required (Boost 1.88).

---

## 2. Quick Start

### 2.1 General

```bash
git clone https://github.com/zerocurrencycoin/Zero.git
cd Zero
./zcutil/fetch-params.sh
./zcutil/build.sh
```

Binaries: `src/zerod`, `src/zero-cli`, `src/zero-tx`. Optional: `src/zerowallet` (Qt GUI) if built with `--with-gui=qt5`.

### 2.2 Linux x86_64

**OS tested:** Ubuntu 24.04 only.

**Packages:**
```bash
sudo apt install build-essential pkg-config libc6-dev m4 g++-multilib \
  autoconf libtool ncurses-dev unzip git python3 python3-zmq \
  zlib1g-dev wget bsdmainutils automake cmake curl
```

**GUI (optional):** On Ubuntu 22.04+ `qt5-default` is deprecated; use:
```bash
sudo apt install qtbase5-dev qtbase5-dev-tools qttools5-dev-tools libqt5websockets5-dev
```

**Build:**
```bash
./zcutil/fetch-params.sh
./zcutil/build.sh
```

**Output:** `src/zerod`, `src/zero-cli`, `src/zero-tx`.

### 2.3 macOS ARM64

**OS tested:** macOS 24.5.0 (darwin 24.5.0).

**Prerequisites:**
```bash
brew install automake cmake pkg-config coreutils
```

**GUI (optional):** For zerowallet: `brew install qt5`; add `$(brew --prefix qt5)/bin` to PATH if needed.

**Build:**
```bash
./zcutil/fetch-params.sh
./zcutil/build.sh
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
cd depends && make HOST=$HOST && cd ..
./autogen.sh
CONFIG_SITE=$PWD/depends/$HOST/share/config.site \
  CXXFLAGS="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" \
  ./configure --prefix=$PWD/depends/$HOST --host=$HOST --enable-static --disable-shared --disable-zmq --disable-rust
sed -i 's/-lboost_system-mt /-lboost_system-mt-s /' configure
cd src && make CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix zerod.exe zero-cli.exe zero-tx.exe
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
cd "$MXE_ROOT" && make MXE_TARGETS='x86_64-w64-mingw32.static' gcc
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

### 4.3 zcutil/build.sh

```
./zcutil/build.sh [ --enable-lcov | --disable-tests ] [ --disable-mining ] [ --enable-proton ] [ MAKEARGS... ]
```

- Flags must come before make args.
- `-jN` is optional on every platform. Omit to use auto-detected jobs (capped at 4). Use `-jN` only when overriding default behavior.
- `CONFIGURE_FLAGS` passed to configure; multi-word values need escaping, e.g. `CONFIGURE_FLAGS='CXXFLAGS=-g\ -Wno-enum-constexpr-conversion'`.

### 4.4 Variables and Overrides

| Variable | Purpose |
|----------|---------|
| `MXE_ROOT` | MXE install root; `MXE_PATH=$MXE_ROOT/usr/bin` (default `$HOME/mxe`; use `/usr/lib/mxe` for system) |
| `CC`, `CXX` | Compiler (e.g. `gcc-11`, `g++-11`) |
| `MAKE` | Make command (e.g. `gmake`) |
| `BUILD`, `HOST` | Triplet for porters |
| `CONFIGURE_FLAGS` | Extra configure options |
| `CCACHE_DIR` | ccache cache (optional). ccache 4.12.2 in depends; `ccache -M 5G` for size. |

### 4.5 Intermediate Results

- Depends: `depends/$HOST/` (e.g. `x86_64-unknown-linux-gnu`, `aarch64-apple-darwin24.5.0`).
- Binaries: `src/zerod`, `src/zero-cli`, `src/zero-tx`. GUI: `src/qt/zerowallet` if built with `--with-gui=qt5`.
- Tests: `contrib/run-tests.sh`; logs in `test-logs/`. See [TEST_ZERO.md](TEST_ZERO.md).

### 4.6 Configure Options

| Option | Purpose |
|--------|---------|
| `--disable-wallet` | Daemon only (servers) |
| `--with-gui=qt5` | Build zerowallet (Qt5) |
| `--without-gui` | Daemon only |
| `--enable-debug` | Debug symbols |
| `--disable-mining` | Exclude mining code |
| `--enable-ccache` | Use ccache (default: auto) |

---

## 5. Per-Platform Detail

### 5.1 Linux x86_64

**Compiler:** GCC. `zcutil/build.sh` prefers GCC-11 if available (Boost compatibility). Install: `sudo apt install gcc-11 g++-11`.

**Depends:** `make -C depends/` uses `config.guess` for HOST. Output: `depends/x86_64-unknown-linux-gnu/`.

**Configure:** `CONFIG_SITE=$PWD/depends/x86_64-unknown-linux-gnu/share/config.site ./configure --enable-hardening`.

**Portable sed:** Depends use `sed -i.old` for in-place edits (BSD/GNU compatible).

### 5.2 macOS ARM64

**Compiler:** Apple Clang. No GCC.

**Prerequisites:** `automake`, `cmake`, `pkg-config`, `coreutils` (for `gnproc`).

**Host triplet:** `aarch64-apple-darwin24.5.0` (config.guess 2025).

**Configure:**
```bash
CONFIG_SITE=$PWD/depends/aarch64-apple-darwin24.5.0/share/config.site \
./configure --enable-hardening --enable-proton=no --enable-mining \
  CXXFLAGS="-g -Wno-enum-constexpr-conversion"
```

- `--enable-proton=no`: Qpid Proton incompatible with CMake 4.x.
- `-Wno-enum-constexpr-conversion`: Boost/Clang 17 compatibility.

**Rust:** Depends pins current system Rust on macOS ARM64 (1.32.0 has no aarch64 binaries). Test same pinned approach on Windows and Linux.

**BDB:** If `database` mutex crash: `rm -rf "$HOME/Library/Application Support/zero/database"`.

### 5.3 Windows

**Cross-compile:** `HOST=x86_64-w64-mingw32`. Requires MXE with `x86_64-w64-mingw32-gcc-posix` and `x86_64-w64-mingw32-g++-posix`. Set `MXE_ROOT` (default `$HOME/mxe`; `MXE_PATH=$MXE_ROOT/usr/bin`). See §2.4 for full steps.

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

**GCC 13+ warnings:** Install GCC-11 or use `CC=gcc-11 CXX=g++-11 ./zcutil/build.sh`.

**GCC too old:** Need GCC 7.0+. Update or use `update-alternatives` to switch.

### 6.4 Memory Exhausted

**"virtual memory exhausted" or "killed":** Override jobs: `make -j1 zerod`. Or add swap.

### 6.5 Mining Disabled

With `--disable-mining`, `test_miner` is excluded from tests. Equihash template instantiations are guarded by `ENABLE_MINING`.

### 6.6 Qt/GUI Not Found

Install Qt5: `sudo apt install qtbase5-dev qtbase5-dev-tools qttools5-dev-tools libqt5websockets5-dev` (Ubuntu 22.04+; `qt5-default` deprecated). Or `brew install qt5` on macOS.

### 6.7 Clean Rebuild

**Depends:** The `depends/` Makefile has no `clean` target. Remove artifacts manually:

| Level | Command | Use case |
|-------|---------|----------|
| BDB only | `rm -rf depends/work/build/*/bdb depends/built/*/bdb` | BDB package change (e.g. bdb.mk CFLAGS) |
| All depends | `rm -rf depends/work depends/built` | Rebuild all packages |
| Full tree | `rm -rf depends/work depends/built depends/$HOST` | Staging dir corrupted or HOST changed |

**Full clean rebuild:**
```bash
make clean && make distclean
rm -rf depends/work depends/built depends/$(./depends/config.guess)
./autogen.sh
./zcutil/build.sh
```

### 6.8 Build Log

```bash
make 2>&1 | tee build.log
grep -i error build.log
```

