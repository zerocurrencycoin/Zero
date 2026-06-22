# BUILD_ZERO

Build guide for the Zero full node binary `zerod`.

**Quick Start:** §2 -- clone, install packages, build (Linux, macOS, Windows cross-compile, packaging).
**Data directory:** §3. **Developer / depends:** §4. **Per-platform:** §5. **Troubleshooting:** §6.
**Testing:** [TEST_ZERO.md -- Quick start](TEST_ZERO.md#quick-start-by-use-case).

---

## 1. Introduction

Build `zerod` from source on Linux, macOS ARM64, or Windows (cross-compile from Linux). **Tested:** Ubuntu 24.04, macOS 24.5.0. The tree uses Autotools with **`depends/`** for deterministic dependency builds.

### 1.1 System requirements

| Category | Requirement |
|----------|-------------|
| **Disk (build)** | Mac &lt;6 GB, Linux &lt;5 GB for toolchain + object files (more for `depends/` caches). |
| **Disk (runtime)** | Full node datadir and params: see §3. |
| **RAM** | ~4 cores / 16 GB RAM comfortable for parallel `make`; reduce `-j` if the linker is OOM-killed. |
| **Toolchain** | **C++14.** Linux: **GCC 7.0+** (tested: GCC 13.3 on Ubuntu 24.04). macOS: **Apple Clang** (tested: Apple Clang 17.0 on macOS 24.5.0). Windows cross: **MXE mingw-w64**. **GNU Make** 4.0+. **Git** 2.0+. |
| **Boost (from depends)** | 1.88.x (see §4.1). |
| **Python** | **3.10+** for `depends` scripts, RPC tests, and `qa/zcash/full_test_suite.py`. Maintainer validation uses **Python 3.12**; use 3.10+ for supported behavior. |

Most linked libraries are built from **`depends/`** as hashed tarballs, not the distro package manager.

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

**Other Linux distros:** Install the same toolchain roles as the Ubuntu list above. BDB comes from `depends/`. If `make -C depends` fails, see §4.8-4.9.

#### 2.2a Remote Linux build host (lazu / ZeroLinux)

Maintainer clone: **`/home/ubuntu/Work/ZK/ZeroLinux`** on host **`lazu`** (Ubuntu 24.04, **2** cores, **~4 GB** RAM). Same upstream remote as macOS; branch **`zero-400names`**.

```bash
cd /home/ubuntu/Work/ZK/ZeroLinux
git fetch origin
git checkout zero-400names
git pull --ff-only origin zero-400names
./zcutil/fetch-params.sh
./zcutil/build.sh -j2
./contrib/run-tests.sh --strict
```

Optional widen: **`./contrib/run-tests.sh --suite`** (Linux ELF stages). See [TEST_ZERO.md](TEST_ZERO.md).

Disk: full native + depends build needs several GB free. If **`/`** is near full, see §6.9 before building.

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

Windows builds use [MXE](https://mxe.cc/) (M Cross Environment). Build MXE once (2-4 h), then reuse.

**1. Set MXE root** (default **`$HOME/mxe`**):

Use a **home-built** MXE (GCC 11.x on lazu). Apt **`mxe-*`** packages install **`/usr/lib/mxe`** with an older toolchain (GCC 5.5) -- **`build-win.sh`** does not use that path unless **`MXE_ROOT`** is set explicitly.

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
cd depends && env NO_PROTON=1 make HOST=$HOST -j$(nproc) && cd ..
./autogen.sh
CONFIG_SITE=$PWD/depends/$HOST/share/config.site \
  CXXFLAGS="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" \
  ./configure --prefix=$PWD/depends/$HOST --host=$HOST --enable-static --disable-shared --disable-zmq --disable-rust --disable-proton
# Prefer ./zcutil/build-win.sh (uses sed -i.bak for GNU vs BSD sed). On Linux-only, sed -i may work without backup.
sed -i.bak 's/-lboost_system-mt /-lboost_system-mt-s /' configure && rm -f configure.bak
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

### 2.5 Packaging on Linux

**Recommended (current Zero naming):** After building, run:

```bash
./zcutil/release-linux.sh
```

Output: `artifacts/linux-zero-v<VERSION>.tgz` and `artifacts/linux-zero-v<VERSION>.deb` (`Package: zero`, includes `zero-fetch-params` when `zcutil/fetch-params.sh` is present). Version is semver from `src/zerod --version` unless `-v X.Y.Z`. Use `-s` to skip stripping; `-L` to capture log.

Default builds are **not** stripped. `release-linux.sh` strips unless you pass `-s`.

### 2.6 Release lifecycle

**Version bump.** `configure.ac` (`_CLIENT_VERSION_*`), `src/config/bitcoin-config.h`, `src/clientversion.h`. After bump: build per §2, run contributor gate, confirm `zerod -version`.

**Git.**

```bash
git fetch origin
git checkout zero-merge
git pull --ff-only origin zero-merge
```

Tag `vMAJOR.MINOR.PATCH`. Archives: `Zero-<ver>-<target>-<triplet>.<ext>`.

**Build and test.** Build per §2. Then:

```bash
./contrib/run-tests.sh --strict
```

Quick smoke (C++ only): `./contrib/run-tests.sh --no-python --strict`. On failure: [TEST_ZERO.md](TEST_ZERO.md).

**Package.** `zcutil/release-linux.sh` stages stripped binaries into tarball and .deb. `contrib/devtools/split-debug.sh` exists for separate debuginfo but is not wired in.

**Signing.** No procedure exists yet. Minimum viable: Linux `SHA256SUMS` + GPG; macOS Developer ID + notarization; Windows Authenticode OV.

### 2.7 Compiler and release flags

| Source | Flag | Effect |
|--------|------|--------|
| `depends/hosts/linux.mk` (darwin, mingw32) | `-O1 -pipe` | Via `config.site`. Zcash-inherited. Bitcoin Core uses `-O2`. |
| `zcutil/build-native.sh` | `CXXFLAGS='-g'` | Always. Inflates objects; suppresses `-Wall`/`-Wextra` via `CXXFLAGS_overridden`. |
| `zcutil/build-win.sh` | `CXXFLAGS="-DPTW32_STATIC_LIB ..."` | No `-g`; inherits `-O1`. |
| `zcutil/release-linux.sh` | `strip` | Strips staged binaries by default. |
| `contrib/devtools/split-debug.sh` | `objcopy --only-keep-debug` | Not wired into release. |

**Proposed changes:** (1) Gate `-g` behind `ZERO_DEBUG=1`. (2) Evaluate `-O2` for release. (3) Decouple `CXXFLAGS_overridden` from bare `-g`. (4) Integrate `split-debug.sh` for `-dbg` package.

---

## 3. .zero Directory

Default paths are implemented in **`src/util.cpp`** (`GetDefaultDataDir`, `ZC_GetBaseParamsDir`). Override chain data with **`-datadir=<path>`**; params stay under the platform ZcashParams path unless you relocate them manually.

### 3.1 Location

| Platform | Data directory | Params directory |
|----------|----------------|------------------|
| **Linux** | `~/.zero` | `~/.zcash-params` |
| **macOS** | `/Users/USERNAME/Library/Application Support/zero` | `/Users/USERNAME/Library/Application Support/ZcashParams` |
| **Windows** | `C:\Users\USERNAME\AppData\Roaming\zero` | `C:\Users\USERNAME\AppData\Roaming\ZcashParams` |

Replace **`USERNAME`** with your login. **`~/.zero` is Linux only** unless you pass `-datadir=$HOME/.zero` on macOS.

**macOS example:**

```bash
mkdir -p "/Users/$(whoami)/Library/Application Support/zero"
echo "server=1" > "/Users/$(whoami)/Library/Application Support/zero/zero.conf"
./src/zerod -daemon
```

**Windows example** (PowerShell; user `Alice`):

```powershell
mkdir C:\Users\Alice\AppData\Roaming\zero
echo server=1 > C:\Users\Alice\AppData\Roaming\zero\zero.conf
.\src\zerod.exe -daemon
```

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

**Sync time:** ~6-10 hours for full chain (varies by network and disk).

### 3.4 Zcash Params

Run `./zcutil/fetch-params.sh` before first start. Zero fetches Sapling params only (~800 MB). Sprout params are not used. Source: `https://download.z.cash/downloads`. If present and checksum-valid, no download occurs.

**Params mirror:** still planned.

**Chain bootstrap (linearize):** Build **`bootstrap.dat`** from a synced node's **`blocks/`** dir. Zero block files include **Equihash `nSolution`**; use this tree's **`contrib/linearize/`** (not upstream Bitcoin linearize). See [contrib/linearize/README.md](contrib/linearize/README.md).

```bash
cd contrib/linearize
cp example-linearize.cfg linearize.cfg   # edit: rpcuser/rpcpassword, input=blocks dir, output path with ~8+ GB free
./linearize-hashes.py linearize.cfg > hashlist.txt
./linearize-data.py linearize.cfg
```

Import: copy **`bootstrap.dat`** to datadir; **`zerod`** auto-imports on first start when the file is present (see **`src/init.cpp`**). Local cfg/hashlist/output are gitignored.

---

## 4. Developer Knowledge

### 4.1 Dependency versions and porting notes

Pinned in **`depends/packages/*.mk`** (hashed tarballs for reproducibility).

| Component | Version | Recipe / lock | Notes for builders / porters |
|-----------|---------|---------------|------------------------------|
| BerkeleyDB | 6.2.32 | `bdb.mk` | Wallet format 6.2.x; **6.2.32** fixes ARM64 mutex issues vs 6.2.23. AGPLv3. Built via depends, not optional for default wallet. |
| Boost | 1.88.0 | `boost.mk` | Node + tests. Darwin needs **`--toolset=clang`** and often **`-Wno-enum-constexpr-conversion`** (§5.2). |
| OpenSSL | 1.1.1w | `openssl.mk` | RPC TLS and legacy EVP call sites. **1.1.1 is EOL upstream**; **project decision:** stay on **1.1.1w** in **`depends`** until a scheduled, audited move to **OpenSSL 3.x** (or removal) with EVP/TLS regression tests. |
| libsodium | 1.0.21 | `libsodium.mk` | Crypto; URL pinned to GitHub releases. |
| libevent | 2.1.12 | `libevent.mk` | Network stack. |
| ZeroMQ | 4.3.5 | `zeromq.mk` | Default **ZMQ** notifications (`-zmqpubhashblock`, `-zmqpubhashtx`, ...). |
| ccache | 4.13.1 | `native_ccache.mk` | Optional faster rebuilds; **`CCACHE_DIR`**, **`--enable-ccache`**. |
| Rust | **system** (no pin; 1.90 on macOS) | `rust.mk` | **Default: system `cargo`/`rustc`** on macOS (always) and Linux/Windows when **`RUST_USE_SYSTEM=1`**. Symlinks into `depends` prefix. **`FORCE_DEPENDS_RUST=1`** forces legacy pinned **1.32.0** tarballs (CI / reproducibility only). Cross-builds: **`rustup target add`** for the host triple. |
| librustzcash | snapshot `06da3b9` | `crate_*.mk`, `Cargo.lock` | Consensus-linked; upgrade only with protocol work. |
| Googletest | 1.16.0 | `googletest.mk` | Last GTest line on **C++14**; 1.17+ expects C++17. |
| utfcpp | 3.1 | `utfcpp.mk` | Header-only; UTF-8 checks in wallet RPC paths. |
| Qpid Proton | 0.26.0 recipe; **off** | `proton.mk`, configure | **AMQP** would duplicate ZMQ's role (`-amqppub*`); recipe exists but **`--enable-proton=no`** / **`NO_PROTON=1`** default--CMake/toolchain friction. |
| config.guess / config.sub | vendor drop | `depends/config.*` | **Apple Silicon** must resolve to **`aarch64-apple-darwin*`**, not **`arm-apple-darwin`**. |


### 4.2 Build flow

`zcutil/build.sh` runs: `make -C depends` -> `autogen.sh` -> `configure` with `CONFIG_SITE` -> `make`. Manual steps are in §5.

**config.site:** `depends/$HOST/share/config.site` sets CC, CXX, flags, and pkg-config paths from the depends build. Without it, configure uses system paths.

### 4.3 Depends layout

- Each library is a `depends/packages/<name>.mk` recipe (version, URL, hash).
- **Portable `sed`:** recipes use `build_SED_INPLACE` (`sed -i.old` style). Do not use bare `sed -i`.
- Checksums: Linux `sha256sum`, Darwin `shasum -a 256`.

### 4.4 zcutil/build.sh

```
./zcutil/build.sh [ --enable-lcov | --disable-tests ] [ --disable-mining ] [ --enable-proton ] [ --daemon ] [ MAKEARGS... ]
```

- `--daemon`: `--disable-zmq --disable-rust`.
- Flags must come **before** `-jN`. Example: `./zcutil/build.sh --disable-mining -j4`.
- Job cap: `FZERO_MAX_JOBS` in `zcutil/fzero.sh` (default 8). Override: `FZERO_MAX_JOBS=2 ./zcutil/build.sh`.

### 4.5 Variables

| Variable | Purpose |
|----------|---------|
| `FZERO_MAX_JOBS` | Job cap (default 8 in `zcutil/fzero.sh`) |
| `MXE_ROOT` | MXE install root (default `$HOME/mxe`) |
| `CC`, `CXX` | Compiler override |
| `HOST` | Target triplet for cross-compile |
| `CONFIGURE_FLAGS` | Extra configure options |
| `FORCE_DEPENDS_RUST` | `1` = legacy pinned Rust 1.32.0 on all platforms (CI only) |
| `RUST_USE_SYSTEM` | `1` = system `cargo`/`rustc` on Linux/Windows (macOS always uses system) |

### 4.6 Configure options

| Option | Purpose |
|--------|---------|
| `--disable-wallet` | Daemon only (servers) |
| `--enable-debug` | Debug symbols |
| `--disable-mining` | Exclude mining code |
| `--enable-ccache` | Use ccache (default: auto) |

### 4.7 Depends recipe troubleshooting

| Package | What to know |
|---------|----------------|
| **Boost** | Darwin bootstrap uses **`--toolset=clang`**; **`$(build_SED_INPLACE)`** adjusts the toolset line in **`boost.mk`**. If **`AX_BOOST_THREAD`** fails on Darwin+Clang, ensure **`boost_thread`** can link (static archive path). |
| **OpenSSL** | Recipe preprocesses with **`build_SED_INPLACE`**. **aarch64** Darwin uses OpenSSL's **`darwin64-arm64-cc`** target. |
| **Berkeley DB** | **6.2.32**; recipe must stay on portable **`sed`** patterns--GNU-only **`sed -i -e`** in patches breaks **macOS** (and is wrong for any strict BSD **`sed`**). |
| **Rust / librustzcash** | System Rust by default on macOS; Linux/Windows use system when **`RUST_USE_SYSTEM=1`**, else legacy 1.32.0. **`librustzcash`** invokes **`$(host_prefix)/native/bin/cargo`** (symlinked). |
| **Googletest** | If you change macOS deployment targets or see link warnings about **OSX** version, **`googletest.mk`** aligns **`OSX_MIN_VERSION`** with the rest of the graph--**rebuild depends** after changing it. |
| **libsodium, libevent, ZeroMQ, ccache** | Routine version bumps: update version + hash in **`.mk`**, then full depends rebuild and smoke test. |

### 4.8 Subsidy, founders, and `COIN`: integer strategy (proposed)

**Problem:** Expressions like **`10.8 * COIN`**, **`GetBlockSubsidy(...) * 0.075`**, and **`blockValue * 7.5 / 100`** mix **`double`** with **`CAmount`** (`int64_t` zats). Rounding differs by path (miner vs **`ConnectBlock`** check vs RPC), and far-future halvings can make **`subsidy * 0.075`** non-integral.

**Policy (target state):**

1. **Consensus paths** -- compute only with **`int64_t`**: integer literals in zats (e.g. **`1080000000`** for **10.8 ZER** where that is the rule) or **`CAmount` × num / den** with **one** documented rounding rule (**floor** unless a BIP/ZIP specifies otherwise).
2. **Fractions** -- encode percentages as rationals with integer denominator (**7.5%** -> **`blockValue * 75 / 1000`**, floor). Use the **same** helper in **`FillBlockPayee`**, **`ConnectBlock`** founders check, and any duplicate logic (**`budget.cpp`**, **`payments.cpp`**, **`main.cpp`**).
3. **`GetBlockSubsidy`** -- avoid **`double`×`COIN`**; derive halving from integer base subsidy constants.
4. **RPC / metrics** -- compute amounts as **`CAmount`**, then **`ValueFromAmount`** (or equivalent) for JSON; do not subtract **`subsidy * 0.075`** in **`double`** for displayed totals if that can diverge from chain rules.
5. **Change control** -- any edit to subsidy or founders split is a **consensus** change: tests in **`main_tests`**, **`rpc_wallet_tests`** **`getblocksubsidy`**, **`test_foundersreward`**, and re-sync from a known height.

**Tracking:** see TODO.md.

#### 4.8.1 Current code touchpoints (`double` / mixed arithmetic)

| File | Lines (approx.) | Notes |
|------|-----------------|--------|
| **`src/main.cpp`** | **2111-2113** | **`GetBlockSubsidy`**: **`10 * COIN`**, **`10.8 * COIN`** (`double` × `COIN`). |
| **`src/main.cpp`** | **4508** | Founders output check: **`GetBlockSubsidy(...) * 0.075`** (`double`). |
| **`src/zeronode/payments.cpp`** | **305** | **`vFoundersReward = blockValue * 7.5 / 100`** (promotion via **`7.5`**). |
| **`src/zeronode/budget.cpp`** | **536-537** | Same pattern on **`txNew.vout[0].nValue`**. |
| **`src/rpc/mining.cpp`** | **946** | **`getblocksubsidy`**: **`nFoundersReward = nReward*0.075`**. |
| **`src/metrics.cpp`** | **346** | **`subsidy -= subsidy*0.075`** (UI / immature totals). |
| **`src/rpc/zeronode.cpp`** | **1090** | **`vFoundersReward = blockValue * 7.5 / 100`**. |
| **`src/test/main_tests.cpp`** | **16-32**, **40-45**, **124-134** | Expectations use **`10.8 * COIN`**, **`5.4 * COIN`**, etc. -- update when **`GetBlockSubsidy`** goes integer-only. |
| **`src/test/rpc_wallet_tests.cpp`** | **273-290** | **`getblocksubsidy`** RPC expected **`founders`** decimals. |

**Good pattern (reference):** **`GetZeronodePayment`** in **`src/main.cpp`** (**~2129-2145**) uses **`blockValue * 20 / 100`**-style **integer** arithmetic.

**Non-consensus:** **`src/init.cpp`** (obfuscation denominations use fractional **`COIN`**), **`src/wallet/test/wallet_tests.cpp`** -- not chain rules.

---

## 5. Per-Platform Detail

### 5.1 Linux x86_64

GCC 7.0+ for C++14. Manual build: `make -C depends`, then `CONFIG_SITE=$PWD/depends/$HOST/share/config.site ./configure`, then `make`.

### 5.2 macOS ARM64

Apple Clang. Configure with `--enable-proton=no` and `CXXFLAGS="-g -Wno-enum-constexpr-conversion"` (Boost/Clang). BDB mutex crash: see §6.2.

### 5.3 Windows

Cross-compile from Linux via MXE. See §2.4 for full steps. Manual: `make HOST=x86_64-w64-mingw32 -C depends`, configure with `--host`, make in `src/` with mingw compilers.

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

### 6.5 Mining disabled builds

With **`./configure --disable-mining`**, mining code is omitted from the binary; Equihash template instantiations follow **`ENABLE_MINING`**. Impact on **test targets** (e.g. `test_miner`, GTest/Boost suites) is described in **[TEST_ZERO.md](TEST_ZERO.md)**.

### 6.6 zerowallet

zerowallet (Qt GUI) is built from separate repos. This repo builds only zerod, zero-cli, zero-tx.

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

### 6.9 Disk space on build hosts

Low disk causes failed links, truncated depends tarballs, and RPC cache build failures. On a tight VPS, reclaim before **`./zcutil/build.sh`** or **`./contrib/run-tests.sh`**.

| Target | Command / notes |
|--------|-----------------|
| apt package indexes | **`sudo rm -rf /var/lib/apt/lists/*`** then **`sudo apt-get update`** (~900 MB on typical Ubuntu) |
| apt `.deb` cache | **`sudo apt-get clean`** / **`autoclean`** |
| compiler cache | **`ccache -C`** or **`rm -rf ~/.ccache`** |
| depends work dirs | **`rm -rf depends/work/*`** per clone (rebuilt on next depends make) |
| RPC harness cache | **`<repo>/cache/`** (gitignored; safe to delete; Tier A rebuilds to maturity **725**) |
| MXE build artifacts | **`rm -rf ~/mxe/pkg/* ~/mxe/log/*`** (keep **`~/mxe/usr`**) |
| Duplicate apt MXE | **`sudo apt-get purge 'mxe-*'`** if Windows builds use **`$HOME/mxe`** only (~1.9 GB under **`/usr/lib/mxe`**) |
| journald | **`sudo journalctl --vacuum-time=7d`** |
| snap old revisions | **`snap list --all`**; remove **`disabled`** revisions |
| swapfile | **`/swapfile`** reserves disk whether used or not; shrink/remove only if RAM headroom allows (see session notes) |

**Not helpful on typical dev VPS:** **`/var/cache`** (~200 MB), Apache logs (~6 MB). Largest consumer is usually **`~/Work`** build trees -- audit with **`du -sh ~/Work/ZK/*`**.

