# BUILD_ZERO

Build guide for the Zero full node binary `zerod`.

**Quick Start:** §2 -- clone, install packages, build (Linux, macOS, Windows cross-compile, packaging).
**Data directory:** §3. **Developer / depends:** §4. **Per-platform:** §5. **Troubleshooting:** §6.
**Testing:** [TEST_ZERO.md -- Use cases](TEST_ZERO.md#2-use-cases).

---

## 1. Introduction

Build `zerod` from source on Linux, macOS ARM64, or Windows (cross-compile from Linux). **Tested:** Ubuntu 24.04, macOS 24.5.0. **Runtime rule of thumb:** the **build OS** sets the binary's glibc/libstdc++ floor -- deploy on that OS class or newer. Maintainer ABI / multi-Ubuntu notes stay in internal docs until a public minimum-OS decision ships with a release. The tree uses Autotools with **`depends/`** for deterministic dependency builds.

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

Binaries: `src/zerod`, `src/zero-cli`, `src/zero-tx`. The Qt desktop wallet is a separate application (not built from this tree).

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

**Other Linux distros:** Install the same toolchain roles as the Ubuntu list above. BDB comes from `depends/`. If `make -C depends` fails, see §4.7.


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

Prefer a **home-built** MXE (modern GCC). Distro **`mxe-*`** packages may ship an older toolchain -- **`build-win.sh`** uses **`MXE_ROOT`** when set.

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

Tag `vMAJOR.MINOR.PATCH` from the release line after a clean build and contributor gate. Archives: `Zero-<ver>-<target>-<triplet>.<ext>`.

**Build and test.** Build per §2. Then:

```bash
./contrib/run-tests.sh --strict
```

Quick smoke (C++ only): `./contrib/run-tests.sh --no-python --strict`. On failure: [TEST_ZERO.md](TEST_ZERO.md).

**Package.** `zcutil/release-linux.sh` stages stripped binaries into tarball and .deb. `contrib/devtools/split-debug.sh` exists for separate debuginfo but is not wired in.

### 2.7 Compiler and release flags

| Source | Flag | Effect |
|--------|------|--------|
| `depends/hosts/linux.mk` (darwin, mingw32) | `-O1 -pipe` | Via `config.site`. Zcash-inherited. Bitcoin Core uses `-O2`. |
| `zcutil/build-native.sh` | `CXXFLAGS='-g'` | Always. Inflates objects; suppresses `-Wall`/`-Wextra` via `CXXFLAGS_overridden`. |
| `zcutil/build-win.sh` | `CXXFLAGS="-DPTW32_STATIC_LIB ..."` | No `-g`; inherits `-O1`. |
| `zcutil/release-linux.sh` | `strip` | Strips staged binaries by default. |
| `contrib/devtools/split-debug.sh` | `objcopy --only-keep-debug` | Not wired into release. |


---

## 3. .zero Directory

Default paths are implemented in **`src/util.cpp`** (`GetDefaultDataDir`, `ZC_GetBaseParamsDir`). Override chain data with **`-datadir=<path>`**; params stay under the platform ZcashParams path unless you relocate them manually.

### 3.1 Location

| Platform | Data directory | Params directory |
|----------|----------------|------------------|
| **Linux** | `~/.zero` | `~/.zcash-params` |
| **macOS** | `~/Library/Application Support/zero` (full: `/Users/USERNAME/Library/Application Support/zero`) | `~/Library/Application Support/ZcashParams` |
| **Windows** | `C:\Users\USERNAME\AppData\Roaming\zero` | `C:\Users\USERNAME\AppData\Roaming\ZcashParams` |

Replace **`USERNAME`** with your login (or use `$(whoami)` in shell examples). **`~/.zero` is Linux only** unless you pass `-datadir=$HOME/.zero` on macOS or Windows.

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
| .zero (full sync) | around **8 GB** |
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
| Qpid Proton | 0.26.0 recipe; **off** | `proton.mk`, configure | **`--disable-proton`** / **`NO_PROTON=1`** default; optional upstream code only |
| config.guess / config.sub | vendor drop | `depends/config.*` | **Apple Silicon** must resolve to **`aarch64-apple-darwin*`**, not **`arm-apple-darwin`**. |


### 4.2 Build flow

**Default:** use **`./zcutil/build.sh`**. It runs the full sequence below and sets **`CONFIG_SITE`** for you.

| Step | Command | Purpose |
|------|---------|---------|
| 1 | `make -C depends` (`NO_PROTON=1` by default) | Build pinned libs (BDB, Boost, OpenSSL, ...) into **`depends/$HOST/`** |
| 2 | `./autogen.sh` | Regenerate **`configure`** after **`configure.ac`** / **`Makefile.am`** edits |
| 3 | `./configure` with **`CONFIG_SITE=depends/$HOST/share/config.site`** | Point compilers and **`CPPFLAGS`/`LDFLAGS`** at the depends prefix |
| 4 | `make` | Build **`src/zerod`**, **`zero-cli`**, **`zero-tx`**, tests |

**`config.site`:** `depends/$HOST/share/config.site` sets CC, CXX, include/lib paths, and pkg-config from the depends build. Without it, **`./configure`** uses system paths and typically fails wallet checks (**`libdb_cxx headers missing`**) because Berkeley DB **6.2.32** comes from depends only, not Homebrew or apt.

**When to use what**

| Goal | Command |
|------|---------|
| Normal build from clean or dirty tree | **`./zcutil/build.sh -jN`** |
| Rebuild after editing **`src/`** only | **`make -jN`** (keep existing **`config.status`**) |
| Reconfigure after **`./autogen.sh`** | **`CONFIG_SITE=$PWD/depends/$HOST/share/config.site ./configure ...`** then **`make`** (see §6.2) |
| Depends library version bump | **`make -C depends`** then reconfigure + **`make`** |
| Bare **`./configure`** at repo root | **Avoid** -- misses BDB and other depends unless you pass **`CONFIG_SITE`** and **`--prefix=depends/$HOST`** |

**Manual configure** (same as **`build-native.sh`**, after step 1):

```bash
HOST=$(./depends/config.guess)
make -C depends NO_PROTON=1 HOST="$HOST" -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)"
CONFIG_SITE=$PWD/depends/$HOST/share/config.site \
  ./configure --prefix=$PWD/depends/$HOST --host="$HOST" --disable-proton CXXFLAGS='-g'
make -j"$(sysctl -n hw.ncpu 2>/dev/null || nproc)"
```

Extra options (e.g. **`ENABLE_SYSTEM_COMMAND`**) go in **`CONFIGURE_FLAGS`** for **`build.sh`**, or on the **`./configure`** line when configuring manually. Per-platform flag details: §5.

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

#### 4.6.1 Shell notify hooks (OPS-SHELL)

Three optional flags run an **external shell command** when an event occurs. Each substitutes **`%s`** in the command string (block hash, transaction id, or sanitized alert text), then invokes the system shell via **`::system()`**:

| Flag | Trigger |
|------|---------|
| **`-blocknotify=<cmd>`** | Active chain tip changes |
| **`-walletnotify=<cmd>`** | Wallet sees a new or updated transaction |
| **`-alertnotify=<cmd>`** | Deprecation or network alert text is emitted |

**Default (release) builds do not execute these commands.** The hooks are gated at **compile time** by **`ENABLE_SYSTEM_COMMAND`**. If the flag is not set at build time, **`zerod`** logs that the notification was skipped and continues -- secure by default; opt-in only when the operator deliberately rebuilds.

**Distributed release policy (decision).** Official artifacts -- Linux tarball/`.deb` from **`zcutil/release-linux.sh`**, tagged GitHub releases, and CI contributor binaries -- stay **without** **`ENABLE_SYSTEM_COMMAND`**. That is intentional: default binaries must not invoke **`::system()`** even if an operator leaves legacy notify lines in **`zero.conf`**. Custom rebuilds may opt in; do not add the flag to release scripts or default **`CONFIGURE_FLAGS`** without an explicit security review and release-notes callout. Production indexers (Insight) use **ZMQ**, not shell hooks.

**Enable shell hooks** (operators who need them):

```bash
./configure CXXFLAGS="-DENABLE_SYSTEM_COMMAND"   # add to your usual CONFIGURE_FLAGS / zcutil/build.sh path
make -j$(nproc)
```

Verify: set **`-blocknotify='echo test >> /tmp/zero-blocknotify.log'`**, mine one regtest block, confirm the log line appears **only** on an **`ENABLE_SYSTEM_COMMAND`** build.

**Why the gate exists.** Inherited Bitcoin Core behavior turns the node into a shell launcher. Config values come from **`zero.conf`** and the command line; even with sanitization on alert text, a mistaken or hostile config can run arbitrary commands as the **`zerod`** user. Most deployments use **ZMQ** or RPC polling instead; compile-time opt-in shrinks the attack surface of default binaries.

**When shell hooks are still appropriate**

| Use case | Example | Notes |
|----------|---------|-------|
| Legacy automation | **`blocknotify`** runs a fixed path script that touches a flag file for an old indexer | Prefer **`-zmqpubhashblock`** for new work |
| Wallet-driven ops | **`walletnotify`** appends txid to a fifo for a custom accounting daemon | Wallet must be enabled; high volume can spawn many threads |
| Deprecation / alert path | **`alertnotify`** emails or pages on deprecation banner (see GTest **`DeprecationTest.AlertNotify`**) | P2P alert relay is obsolete; deprecation still calls **`CAlert::Notify`** |

**Preferred alternatives (no shell)**

| Need | Use instead |
|------|-------------|
| New block | **`-zmqpubhashblock=tcp://127.0.0.1:28332`** (requires ZMQ-enabled build; default on) |
| New tx | **`-zmqpubhashtx=...`**, **`-zmqpubrawtx=...`** |
| Wallet activity | Poll **`listtransactions`** / **`zs_listtransactions`** from a sidecar, or ZMQ raw tx |

**Testing:** GTest **`DeprecationTest.AlertNotify`** covers **`-alertnotify`**. See **TEST_ZERO.md** / **TODO.md** for notify coverage status.


### 4.7 Depends recipe troubleshooting

| Package | What to know |
|---------|----------------|
| **Boost** | Darwin bootstrap uses **`--toolset=clang`**; **`$(build_SED_INPLACE)`** adjusts the toolset line in **`boost.mk`**. If **`AX_BOOST_THREAD`** fails on Darwin+Clang, ensure **`boost_thread`** can link (static archive path). |
| **OpenSSL** | Recipe preprocesses with **`build_SED_INPLACE`**. **aarch64** Darwin uses OpenSSL's **`darwin64-arm64-cc`** target. |
| **Berkeley DB** | **6.2.32**; recipe must stay on portable **`sed`** patterns--GNU-only **`sed -i -e`** in patches breaks **macOS** (and is wrong for any strict BSD **`sed`**). |
| **Rust / librustzcash** | System Rust by default on macOS; Linux/Windows use system when **`RUST_USE_SYSTEM=1`**, else legacy 1.32.0. **`librustzcash`** invokes **`$(host_prefix)/native/bin/cargo`** (symlinked). |
| **Googletest** | If you change macOS deployment targets or see link warnings about **OSX** version, **`googletest.mk`** aligns **`OSX_MIN_VERSION`** with the rest of the graph--**rebuild depends** after changing it. |
| **libsodium, libevent, ZeroMQ, ccache** | Routine version bumps: update version + hash in **`.mk`**, then full depends rebuild and smoke test. |


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

BDB **6.2.32** (depends). Used for wallet storage. Wallet-enabled builds require depends + **`CONFIG_SITE`** (see §4.2).

**`libdb_cxx headers missing` on configure:** You ran **`./configure`** without **`CONFIG_SITE`**, or depends was not built for the current **`HOST`**. Fix:

```bash
HOST=$(./depends/config.guess)
ls depends/$HOST/include/db_cxx.h depends/$HOST/lib/libdb_cxx*   # must exist
CONFIG_SITE=$PWD/depends/$HOST/share/config.site \
  ./configure --prefix=$PWD/depends/$HOST --host="$HOST" --disable-proton CXXFLAGS='-g'
```

Or run **`./zcutil/build.sh`**, which does this automatically. Do **not** use **`--disable-wallet`** unless you intentionally want a wallet-less daemon.

**Not found after depends build:** `ls depends/$HOST/lib/libdb*`. If **`depends/$HOST/share/config.site`** is missing, rebuild depends: **`make -C depends NO_PROTON=1 HOST=$HOST`**.

**Mutex crash (macOS):** `rm -rf "$HOME/Library/Application Support/zero/database"` and restart.

**`-bind_at_load` linker warning (macOS):** Manual **`make`** or **`make check-symbols`** without **`MACOSX_DEPLOYMENT_TARGET`** can print **`ld: warning: -bind_at_load is deprecated on macOS`**. GNU libtool adds the flag when the env var is unset (defaults to **`10.0`**). **`./zcutil/build.sh`** exports **`MACOSX_DEPLOYMENT_TARGET=15.0`**; for manual builds run **`export MACOSX_DEPLOYMENT_TARGET=15.0`** first. Build still succeeds; warning is cosmetic. Permanent Makefile/configure export: postponed (**TODO**).

### 6.3 Boost / GCC

**GCC too old:** Need GCC 7.0+ for C++14.

### 6.4 Memory Exhausted

**"virtual memory exhausted" or "killed":** Reduce jobs: `make -j1 zerod`. Or add swap.

### 6.5 Desktop wallet

The Qt desktop wallet is built elsewhere. This repo builds only `zerod`, `zero-cli`, `zero-tx`.

### 6.6 Clean Rebuild

```bash
make clean && make distclean
cd depends && make clean && cd ..
./autogen.sh
CONFIG_SITE=$PWD/depends/$HOST/share/config.site ./configure ...
make -j4
```

### 6.7 Build Log

```bash
make -j4 2>&1 | tee build.log
grep -i error build.log
```


