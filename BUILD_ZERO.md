# BUILD_ZERO

Build guide for the Zero full node binary `zerod`.

**Quick Start:** §2 — clone, install packages, and build variants for Linux, macOS, Windows, and packaging.  
**Data directory:** §3 — `.zero` location, params, files.  
**Developer:** §4 — pinned dependency versions, depends layout for porting, `config.site`, `build.sh` flags.  
**Per-platform:** §5 — manual configure and platform quirks; basic commands are in §2.  
**Testing:** [TEST_ZERO.md](TEST_ZERO.md) — runners, filters, Tier A gate, `full_test_suite.py`; bulk RPC names in `qa/pull-tester/rpc-tests.sh`.  
**Troubleshooting:** §6 — params, BDB, memory, clean rebuild.

---

## 1. Introduction

Zero is a Zcash-family cryptocurrency node. Build `zerod` from source on Linux, macOS ARM64, or Windows (cross-compile from Linux). **OS coverage tested for builds:** Ubuntu 24.04, macOS 24.5.0. The tree uses Autotools with **`depends/`** for deterministic dependency builds.

### 1.1 System requirements

| Category | Requirement |
|----------|-------------|
| **Disk (build)** | Mac &lt;6 GB, Linux &lt;5 GB for toolchain + object files (more for `depends/` caches). |
| **Disk (runtime)** | Full node datadir and params: see §3. |
| **RAM** | ~4 cores / 16 GB RAM comfortable for parallel `make`; reduce `-j` if the linker is OOM-killed. |
| **Toolchain** | **C++14:** GCC 7.0+ (Linux), Apple Clang (macOS), MXE mingw-w64 (Windows cross). **GNU Make** 4.0+. **Git** 2.0+. |
| **Boost (from depends)** | 1.88.x (see §4.1). |
| **Python** | **3.10+** for `depends` scripts, RPC tests, and `qa/zcash/full_test_suite.py`. Maintainer validation uses **Python 3.12**; use 3.10+ for supported behavior. |

**Build variants:** commands, packages, and outputs are in **§2**, **§5**, and **§2.4** for Windows. This document is the canonical place for full install lists and script options.

**Porting to other Linux distros or unfamiliar hosts:** Most linked libraries are built from **`depends/`** as hashed tarballs, not the distro package manager. You need a working toolchain and build utilities; see **§2.2.1**, **§4.8**, and **§4.9** for version choices and recipe notes. Cross-project dependency comparison is not duplicated here; compare **`depends/packages/*.mk`** and upstream release trees when aligning with Bitcoin Core, Zcash, or similar codebases.

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

### 2.2.1 Other Linux distributions

CI and docs are oriented to **Debian/Ubuntu** package names (§2.2). On **Fedora/RHEL**, **openSUSE**, **Arch**, **Alpine**, etc., install the **same role** of tools: a C++14-capable GCC or Clang, GNU Make, Autoconf/Automake/Libtool, pkg-config, Python **3.10+**, Git, patch, curl/wget, and typical build headers (`zlib`, `ncurses` where the recipe expects them—match the Ubuntu list as closely as possible). Wallet-enabled builds still expect **Berkeley DB** to come from **`depends/`** (BDB 6.2.x), not necessarily from the distro.

If **`make -C depends`** fails on a new host, check **§4.8** for hash commands, portable `sed`, and the triplet from **`depends/config.guess`**, and **§4.9** for recipe-specific notes.

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

**Stripping:** Default **`zcutil/build.sh`** outputs are **not** stripped (larger binaries, easier debugging). Release packaging may strip unless you pass **`-s`** to **`release-linux.sh`** to skip strip.

**Legacy Debian builder:** `./zcutil/build-debian-package.sh` — Zcash-era package name (`zcash`), paths, and metadata. Kept for reference; do not mix with `release-linux.sh` outputs without reading both scripts. See **TODO.md** (Active) for consolidation task.

**fetch-params script:** `zcutil/fetch-params.sh` still follows upstream Zcash naming and download URLs; modernization tracked in **TODO.md**.

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

### 4.1 Dependency versions and porting notes

Dependencies are pinned in **`depends/packages/*.mk`** (and related `native_*` / `crate_*` recipes). **Policy:** reproducibility (hashed tarballs), known breakage on specific hosts, or CI determinism. Local developers may sometimes use system tools where this doc says so (e.g. Rust on macOS ARM64).

| Component | Version | Recipe / lock | Notes for builders / porters |
|-----------|---------|---------------|------------------------------|
| BerkeleyDB | 6.2.32 | `bdb.mk` | Wallet format 6.2.x; **6.2.32** fixes ARM64 mutex issues vs 6.2.23. AGPLv3. Built via depends, not optional for default wallet. |
| Boost | 1.88.0 | `boost.mk` | Node + tests. Darwin needs **`--toolset=clang`** and often **`-Wno-enum-constexpr-conversion`** (§5.2). |
| OpenSSL | 1.1.1w | `openssl.mk` | RPC TLS and legacy EVP call sites. **1.1.1 is EOL upstream**; **project decision:** stay on **1.1.1w** in **`depends`** until a scheduled, audited move to **OpenSSL 3.x** (or removal) with EVP/TLS regression tests. |
| libsodium | 1.0.21 | `libsodium.mk` | Crypto; URL pinned to GitHub releases. |
| libevent | 2.1.12 | `libevent.mk` | Network stack. |
| ZeroMQ | 4.3.5 | `zeromq.mk` | Default **ZMQ** notifications (`-zmqpubhashblock`, `-zmqpubhashtx`, …). |
| ccache | 4.13.1 | `native_ccache.mk` | Optional faster rebuilds; **`CCACHE_DIR`**, **`--enable-ccache`**. |
| Rust | depends **1.32.0** + **PATH** | `rust.mk` | **Project decision:** use **system `rustc` / `cargo` on `PATH`** on **macOS** and **Linux** for **`librustzcash`** / **`cargo`** steps (e.g. **rustc 1.91.x** on maintainer machines). **Windows** / some cross hosts still use the **depends**-downloaded toolchain per recipe. **Target:** one modern pinned toolchain everywhere remains **deferred**. |
| librustzcash | snapshot `06da3b9` | `crate_*.mk`, `Cargo.lock` | Consensus-linked; upgrade only with protocol work. |
| Googletest | 1.16.0 | `googletest.mk` | Last GTest line on **C++14**; 1.17+ expects C++17. |
| utfcpp | 3.1 | `utfcpp.mk` | Header-only; UTF-8 checks in wallet RPC paths. |
| Qpid Proton | 0.26.0 recipe; **off** | `proton.mk`, configure | **AMQP** would duplicate ZMQ’s role (`-amqppub*`); recipe exists but **`--enable-proton=no`** / **`NO_PROTON=1`** default—CMake/toolchain friction. |
| config.guess / config.sub | vendor drop | `depends/config.*` | **Apple Silicon** must resolve to **`aarch64-apple-darwin*`**, not **`arm-apple-darwin`**. |

**ZMQ vs AMQP:** Proton is not downloaded in default depends builds. Do not enable Proton unless you are actively reviving the AMQP path; that workflow is outside the scope of this guide.

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

### 4.4 Depends layout and host portability

When **`./zcutil/build.sh`** or **`make -C depends`** runs:

- Each third-party library is a **`depends/packages/<name>.mk`** recipe (version, URL, hash, per-host flags).
- **`depends/Makefile`** and **`depends/builders/*.mk`** define **`build_`*** helpers (compiler, flags, staging). **Linux** typically uses **`sha256sum`**; **Darwin** uses **`shasum -a 256`** for checksums—custom builders must not assume one or the other.
- **Portable `sed`:** recipes use **`build_SED_INPLACE`** from **`depends/Makefile`** (**`sed -i.old`** style) because **BSD** `sed` requires a backup extension and **GNU** `sed` allows **`-i`**. If you patch **`.mk`** files, avoid bare **`sed -i`** without the project pattern.
- **`depends/funcs.mk`** **`fetch_file`** uses quoted paths so **`dash`** as **`/bin/sh`** does not break on spaces.
- Native vs cross: **`zcutil/build-native.sh`**, **`zcutil/fzero.sh`** (job cap **`FZERO_MAX_JOBS`**), and **`zcutil/build-win.sh`** are separate entrypoints; **`HOST`** and artifacts differ (§2.4, §5.3).

### 4.5 zcutil/build.sh

```
./zcutil/build.sh [ --enable-lcov | --disable-tests ] [ --disable-mining ] [ --enable-proton ] [ --daemon ] [ MAKEARGS... ]
```

- `--daemon`: `--disable-zmq --disable-rust` for configure. Aligns with build-win.sh.
- `--enable-proton`: native builds include Proton in `depends/` and configure (default without this flag: `NO_PROTON=1` for `depends` and `--disable-proton` for configure — same convention as Windows cross, which always omits Proton from depends and passes `--disable-proton`).
- Flags must come before `-jN` and other make args. Example: `./zcutil/build.sh --disable-mining -j4` (correct); `./zcutil/build.sh -j4 --disable-mining` (wrong — flag passed to make).
- Parallel jobs: `zcutil/fzero.sh` sets **`FZERO_MAX_JOBS`** (default **8** at top of that file). Auto-detected CPU count is capped to that value; pass `-jN` to override (still capped). Per-run override without editing the file: `FZERO_MAX_JOBS=2 ./zcutil/build.sh`. Detection: Linux `nproc`; macOS `sysctl -n hw.ncpu` or `gnproc` (Homebrew coreutils).
- `CONFIGURE_FLAGS` passed to configure; multi-word values need escaping, e.g. `CONFIGURE_FLAGS='CXXFLAGS=-g\ -Wno-enum-constexpr-conversion'`.

### 4.6 Variables and Overrides

| Variable | Purpose |
|----------|---------|
| `FZERO_MAX_JOBS` | Cap for auto `-j` and for explicit `-jN` when N exceeds cap (`zcutil/fzero.sh`; default 8 in file) |
| `MXE_ROOT` | MXE install root; `MXE_PATH=$MXE_ROOT/usr/bin` (default `$HOME/mxe`; use `/usr/lib/mxe` for system) |
| `CC`, `CXX` | Compiler (e.g. `gcc-11`, `g++-11`) |
| `MAKE` | Make command (e.g. `gmake`) |
| `BUILD`, `HOST` | Triplet for porters |
| `CONFIGURE_FLAGS` | Extra configure options |
| `CCACHE_DIR` | ccache cache (optional). ccache 4.13.1 in depends; `ccache -M 5G` for size. |

### 4.7 Intermediate results

- **Depends:** `depends/$HOST/` (e.g. `x86_64-unknown-linux-gnu`, `aarch64-apple-darwin25.3.0`).
- **Binaries:** `src/zerod`, `src/zero-cli`, `src/zero-tx`.
- **Tests:** With the default configure, the build also produces **`src/test/test_bitcoin`** (Boost) and **`src/zero-gtest`** (GoogleTest). How to run them, pass-only filters, `contrib/run-tests.sh` and `qa/zcash/full_test_suite.py`, the Tier A allowlist (and where Tier B/C names live), and how to add tests are documented in **[TEST_ZERO.md](TEST_ZERO.md)**—not duplicated here.

### 4.8 Configure Options

| Option | Purpose |
|--------|---------|
| `--disable-wallet` | Daemon only (servers) |
| `--enable-debug` | Debug symbols |
| `--disable-mining` | Exclude mining code |
| `--enable-ccache` | Use ccache (default: auto) |

### 4.9 Depends recipe troubleshooting

These repeat §4.1 / §5 in recipe-specific form—useful when **`make -C depends`** stops in one package.

| Package | What to know |
|---------|----------------|
| **Boost** | Darwin bootstrap uses **`--toolset=clang`**; **`$(build_SED_INPLACE)`** adjusts the toolset line in **`boost.mk`**. If **`AX_BOOST_THREAD`** fails on Darwin+Clang, ensure **`boost_thread`** can link (static archive path). |
| **OpenSSL** | Recipe preprocesses with **`build_SED_INPLACE`**. **aarch64** Darwin uses OpenSSL’s **`darwin64-arm64-cc`** target. |
| **Berkeley DB** | **6.2.32**; recipe must stay on portable **`sed`** patterns—GNU-only **`sed -i -e`** in patches breaks **macOS** (and is wrong for any strict BSD **`sed`**). |
| **Rust / librustzcash** | **macOS** and **Linux:** **system** **`rustc`**/**`cargo`** on **`PATH`** (see §4.1 table). **Windows** / some hosts: **depends**-supplied toolchain. **`librustzcash`** builds with whichever **`cargo`** runs. |
| **Googletest** | If you change macOS deployment targets or see link warnings about **OSX** version, **`googletest.mk`** aligns **`OSX_MIN_VERSION`** with the rest of the graph—**rebuild depends** after changing it. |
| **libsodium, libevent, ZeroMQ, ccache** | Routine version bumps: update version + hash in **`.mk`**, then full depends rebuild and smoke test. |

---

## 5. Per-Platform Detail

### 5.1 Linux x86_64

**Compiler:** GCC 7.0+ for C++14.

**Other distros:** See **§2.2.1** for Fedora/Arch/Alpine-style hosts; triplet may be **`x86_64-unknown-linux-gnu`** or similar—use the **`depends/$HOST/`** directory that **`config.guess`** produces, not only the Ubuntu example path below.

**Manual build** (if not using build.sh): `make -C depends/` (HOST from `depends/config.guess`), then `CONFIG_SITE=$PWD/depends/$HOST/share/config.site ./configure --enable-hardening` (substitute your **`$HOST`**), then `make`.

### 5.2 macOS ARM64

**Compiler:** Apple Clang.

**Manual build:** HOST from `./depends/config.guess`. Configure with `--enable-proton=no` (Proton incompatible with CMake 4.x) and `CXXFLAGS="-g -Wno-enum-constexpr-conversion"` (Boost/Clang 17). See §2.3 for prerequisites.

**Rust:** Depends uses system Rust on ARM64 (1.32.0 has no aarch64 binaries).

**BDB mutex crash:** See §6.2.

### 5.3 Windows

**Cross-compile:** `HOST=x86_64-w64-mingw32`. Requires MXE with `x86_64-w64-mingw32.static-gcc`. Set `MXE_ROOT` (default `$HOME/mxe`; `MXE_PATH=$MXE_ROOT/usr/bin`). See §2.4 for full steps.

**Manual build:** (1) `make HOST=x86_64-w64-mingw32` in depends; (2) configure with CONFIG_SITE (see §4.3), `--host=x86_64-w64-mingw32 --enable-static --disable-shared --disable-zmq --disable-rust --disable-proton`, CXXFLAGS for PTW32_STATIC_LIB, CURVE_ALT_BN128; (3) Boost `-mt` → `-mt-s` fix: use `sed -i.bak '…' configure && rm -f configure.bak` for macOS/Linux portability (see `zcutil/build-win.sh`); (4) make in src/ with `CC=x86_64-w64-mingw32-gcc-posix CXX=x86_64-w64-mingw32-g++-posix`.

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

### 6.5 Mining disabled builds

With **`./configure --disable-mining`**, mining code is omitted from the binary; Equihash template instantiations follow **`ENABLE_MINING`**. Impact on **test targets** (e.g. `test_miner`, GTest/Boost suites) is described in **[TEST_ZERO.md](TEST_ZERO.md)**.

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

