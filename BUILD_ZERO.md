# BUILD_ZERO

Build guide for the Zero full node binary `zerod`.

**Quick Start:** section 2 -- clone, install packages, build (Linux, macOS, Windows cross-compile, packaging).
**Data directory:** section 3. **Developer / depends:** section 4. **Per-platform:** section 5. **Troubleshooting:** section 6.

---

## 1. Introduction

Build `zerod` from source on Linux, macOS ARM64, or Windows (cross-compile from Linux). **Tested:** Ubuntu 24.04, macOS 26.3 (Darwin 25.3). **Runtime rule of thumb:** the **build OS** sets the binary's glibc/libstdc++ floor -- deploy on that OS class or newer. The tree uses Autotools with **`depends/`** for deterministic dependency builds.

### 1.1 System requirements

| Category | Requirement |
|----------|-------------|
| **Disk (build)** | Mac &lt;6 GB, Linux &lt;5 GB for toolchain + object files (more for `depends/` caches). |
| **Disk (runtime)** | Full node datadir and params: see section 3. |
| **RAM** | ~4 cores / 16 GB RAM comfortable for parallel `make`; reduce `-j` if the linker is OOM-killed. |
| **Toolchain** | **C++14.** Linux: **GCC 7.0+** (tested: GCC 13.3 on Ubuntu 24.04). macOS: **Apple Clang** (tested: Apple Clang 21.0 on macOS 26.3, Apple Clang 17.0 on macOS 15.5). Windows cross: **MXE mingw-w64**. **GNU Make** 4.0+. **Git** 2.0+. |
| **Boost (from depends)** | 1.88.x (see section 4.1). |
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

`fetch-params.sh` is **system setup** (once per machine, before first `zerod` start). Confirm with `zcutil/check-setup.sh`. It is not a step in `zcutil/check-release.sh` / `zcutil/build.sh`. Later rebuilds: `./zcutil/build.sh` only.

Binaries: `src/zerod`, `src/zero-cli`, `src/zero-tx`. The Qt desktop wallet is a separate application (not built from this tree).

**Receipts.** Gitignored **`.build/`** holds identity and command logs (`ready-*.txt`, `build-native-*.log`, `test-logs/`). Autotools `config.log` / `config.status` stay at the repo root (also gitignored) and are not the validation pin. Older **`logs/`** and **`test-logs/`** paths remain gitignored if present.

**Rebuild stages** (`./zcutil/build.sh` runs these in order). Sapling params (`./zcutil/fetch-params.sh`) are **system setup** (before first `zerod` start, section 3). They are not part of this cycle.

| Stage | What `build.sh` runs | When it is cheap | When it is expensive |
|-------|----------------------|------------------|----------------------|
| **depends** | `make -C depends` (always invoked) | Cached tarballs in `depends/built/$HOST/` match recipe hashes: checksum check, restamp `depends/$HOST/`, no package compile | Missing sources, checksum mismatch, recipe/`.mk` change, new `HOST`, wiped `depends/built` or `depends/$HOST/` -- **fetch and/or rebuild that package** (see below) |
| **autogen** | `./autogen.sh` | Always seconds-class: regenerates `configure` via autoreconf. Does **not** fetch or compile Boost, Rust, or BDB | Missing automake/libtool (fails, does not hang on a download) |
| **configure** | `./configure` with `CONFIG_SITE=depends/$HOST/share/config.site` | Seconds to a couple of minutes: compiler/header probes, writes `config.status` | Does **not** rebuild depends. Slow or wrong if `config.site` is missing (depends not installed for this `HOST`) |
| **compile** | `make` | Incremental objects already built | Full tree compile after clean / first configure |

`make -C depends` is **not** a no-op invocation -- it always runs `check-sources` / `check-packages` -- but a warm cache does not recompile Boost.

**Depends packages that can fetch or rebuild** (`depends/packages/packages.mk`; default `NO_PROTON=1` omits Proton):

| Package | Role | Fetch (first time / cache miss) | Rebuild compile |
|---------|------|---------------------------------|-----------------|
| **boost** | C++ (chrono, filesystem, program_options, system, thread, test) | Large 1.88 source tarball (`archives.boost.io` or depends-sources mirror) | **The usual long one.** `b2` is hardcoded `-j2` in `boost.mk` |
| **rust** | cargo/rustc for librustzcash | **macOS:** default is **system** rust (symlink; no 1.32 tarball) unless `FORCE_DEPENDS_RUST=1`. **Linux:** pinned **1.32.0** dist tarball unless `RUST_USE_SYSTEM=1` | Tarball extract + stage, or symlink; not a Boost-class compile by itself |
| **librustzcash** + **crates** | Sapling/Rust FFI | GitHub tarball + many crate tarballs on first miss | **`cargo --release --frozen`** -- long on a cold cache; follows rust |
| **openssl** | TLS | Dist tarball | Moderate compile |
| **bdb** | Wallet (`wallet_packages`; default on) | Dist tarball | Moderate; skipped only if `NO_WALLET` |
| **libevent**, **zeromq**, **libsodium**, **utfcpp**, **googletest** | Event, ZMQ, crypto, tests | Smaller tarballs | Shorter than Boost / librustzcash |
| **native_ccache** | Native helper | Small | Small |
| **proton** | AMQP | Off unless `--enable-proton` | Not in the default cycle |

A recipe hash includes `packages/<name>.mk` and patches. Editing those, changing `HOST`, `DEBUG`, or `NO_WALLET`, or deleting `depends/built/$HOST/<pkg>/` forces that package. Autogen and configure never kick Boost or Rust compiles.

There is **no** flag on `build.sh` to skip depends, autogen, or configure. Incremental object rebuild: `make -j` in an already-configured tree. Warm `depends/built/$HOST/` means `make -C depends` still runs but does not recompile Boost. Host/setup: `zcutil/check-setup.sh` (toolchain, params). Product/tree: `zcutil/check-release.sh` (tree / depends / configure / **build**). Compile wrapper: `zcutil/build-release.sh` (setup + receipt then `build.sh`). Tests: `contrib/run-tests.sh --strict`.

**Python:** **3.10+** (harness floor). Not 3.11. `hashlib.blake2b` is stdlib; maintainer validation uses 3.12.

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

**Other Linux distros:** Install the same toolchain roles as the Ubuntu list above. BDB comes from `depends/`. If `make -C depends` fails, see section 4.7.


### 2.3 macOS ARM64

Binaries target macOS 15.0 and later (`OSX_MIN_VERSION` in `depends/hosts/darwin.mk`). The depends host triplet carries the Darwin kernel version (for example `aarch64-apple-darwin25.3.0`), not the macOS release:

| macOS release | Darwin version | Status |
|---------------|----------------|--------|
| 26.3 Tahoe | 25.3 | Tested |
| 15.5 Sequoia | 24.5 | Tested previously |
| 15.0 Sequoia | 24.0 | Minimum deployment target |

`sw_vers -productVersion` shows the macOS release; `uname -r` shows the Darwin version.

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

### 2.5 Packaging

Each platform has a packaging script that stages `zerod`, `zero-cli`, `zero-tx`, and README from a finished build, writes an archive to `artifacts/`, and then rewrites `artifacts/SHA256SUMS` for everything in that directory. Staging happens in `bin/`; both directories are gitignored. The version comes from the configured tree (`X.Y.Z`, keeping a `-rcN` or `-betaN` suffix) unless `-v` is given. Every script takes `--help`, `-s` (skip stripping), and `-L` (capture a log).

| Platform | Run on | Command | Output |
|----------|--------|---------|--------|
| Linux | Linux, after `./zcutil/build.sh` | `./zcutil/release-linux.sh` | `linux-zero-v<ver>.tgz`, `linux-zero-v<ver>.deb` (`Package: zero`, with `zero-fetch-params`) |
| macOS | macOS, after `./zcutil/build.sh` | `./zcutil/release-macos.sh [--sign IDENTITY] [--notarize PROFILE]` | `macos-zero-v<ver>-<arch>.zip` (with `zero-fetch-params`) |
| Windows | Linux build host, after `./zcutil/build.sh -win` | `./zcutil/release-win.sh [--sign-pkcs12 FILE]` | `win-zero-v<ver>.zip` |

The `.deb` `Version:` field writes a release-candidate suffix as `~rcN`, so Debian orders `4.1.0~rc1` before `4.1.0`. On macOS, `--sign` applies a Developer ID Application signature with the hardened runtime and a secure timestamp, and `--notarize` submits the zip with `xcrun notarytool` using a stored keychain profile; a zip of command-line tools cannot be stapled, so Gatekeeper checks the notarization online on first run. On Windows, `--sign-pkcs12` applies Authenticode with `osslsigncode` (password in `ZERO_AUTHENTICODE_PASS`). Without these options the archives are unsigned and the scripts warn.

`./zcutil/checksums.sh` writes `artifacts/SHA256SUMS` on its own, and `./zcutil/checksums.sh --verify` checks the directory against it. Run it after any signing step, because signing changes the files.

Default builds are **not** stripped. The packaging scripts strip the staged copies unless you pass `-s`.

### 2.6 Release lifecycle

**Version bump.** `configure.ac` (`_CLIENT_VERSION_*`), `src/config/bitcoin-config.h`, `src/clientversion.h`. After bump: build per section 2, run contributor gate, confirm `zerod -version`.

**Git.**

Tag `vMAJOR.MINOR.PATCH` from the release line after a clean build and contributor gate. Archives: `Zero-<ver>-<target>-<triplet>.<ext>`.

**Build and test.** Build per section 2. Confirm the machine with `zcutil/check-setup.sh` and identity with `zcutil/check-release.sh --exact` when tagging (clean tree; HEAD must equal `--release`, default **v4.1.0-rc1**; the version `configure.ac` produces and `zerod -version` must match it). Then `zcutil/build-release.sh` if you still need a compile, and:

```bash
./contrib/run-tests.sh --all
```

The runner exits 0 and prints WARNING when a step fails unless `--strict` is given; read its summary. Logs: `.build/test-logs/`. Quick smoke (C++ only): `./contrib/run-tests.sh --no-python --strict`.

**Package.** Run the packaging script for each shipped platform (section 2.5). `contrib/devtools/split-debug.sh` exists for separate debuginfo but is not wired in.

**Checksum and sign.** Do this during release prep (same sitting as tag + package), not after the GitHub Release is published. Unsigned CI artifacts are not releases. Sign macOS and Windows binaries with the packaging script options, collect all archives in one `artifacts/` directory, run `./zcutil/checksums.sh`, then sign `SHA256SUMS` with the method chosen for the release (undecided). Publish the archives, `SHA256SUMS`, and its signature together. RC recording (present vs explicitly missing): [TEST_ZERO.md](TEST_ZERO.md) section 8.

**Verify a download.** In the download directory:

| Platform | Commands |
|----------|----------|
| Linux | `sha256sum --ignore-missing -c SHA256SUMS` |
| macOS | `shasum -a 256 --ignore-missing -c SHA256SUMS`; after unzipping, `codesign --verify --strict zerod` and `spctl --assess --type execute -v zerod` |
| Windows (PowerShell) | `Get-FileHash -Algorithm SHA256 win-zero-v<ver>.zip` and compare with the line in `SHA256SUMS`; `signtool verify /pa zerod.exe` (Windows SDK) |

`--ignore-missing` skips lines for archives of other platforms that were not downloaded.

### 2.7 Compiler and release flags

| Source | Flag | Effect |
|--------|------|--------|
| `depends/hosts/linux.mk` (darwin, mingw32) | `-O1 -pipe` | Via `config.site`. Zcash-inherited. Bitcoin Core uses `-O2`. |
| `zcutil/build-native.sh` | `CXXFLAGS='-g'` | Always. Inflates objects; suppresses `-Wall`/`-Wextra` via `CXXFLAGS_overridden`. |
| `zcutil/build-win.sh` | `CXXFLAGS="-DPTW32_STATIC_LIB ..."` | No `-g`; inherits `-O1`. |
| `zcutil/release-*.sh` | `strip` | Strip staged binaries by default. |
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

### 3.2 Configuration file

`zerod` starts only when `zero.conf` exists in the data directory; an empty file is valid. `contrib/zero.conf` is the commented example: every line is commented out and shows the built-in default, grouped by network, RPC server, wallet, indexes, performance, mining, zeronode, notifications, and logging. Copy it, then uncomment only the lines to change. A comment after a value on the same line is ignored. Command-line options override the file. `reindex=` never belongs in the file: run `zerod -reindex` once instead.

`contrib/zero-conf.sh` writes a ready-made file for one role from `contrib/conf-templates/` and fills in RPC credentials:

| Template | Role | RPC port |
|----------|------|----------|
| `prod` (default) | Node with wallet RPC, no mining | 23811 |
| `lab` | Isolated scratch node, no peers | 23941 |
| `zerowallet` | The file Zerowallet generates | 23811 |
| `insight` | Explorer node: indexes, ZMQ, no wallet | 23811 |

```bash
./contrib/zero-conf.sh prod -dir ~/.zero
```

`zero-conf.sh --help` lists the options. Without `rpcuser` and `rpcpassword`, `zero-cli` authenticates with the `.cookie` file in the data directory.

### 3.3 Files

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

### 3.4 Size Estimates

| Component | Approx. size |
|-----------|--------------|
| .zero (full sync) | around **8 GB** |
| .zcash_params (Sapling only) | ~800 MB |
| Fresh .zero (no chain) | &lt;50 MB |

**Sync time:** ~6-10 hours for full chain (varies by network and disk).

### 3.5 Zcash Params

**System setup**, not the build/validate cycle. Run `./zcutil/fetch-params.sh` once per machine before first `zerod` start. `zerod` needs three files in the params directory: `sapling-spend.params` (48 MB), `sapling-output.params` (3.6 MB), and `sprout-groth16.params` (726 MB, the Groth16 parameters that verify Sprout transactions). The pre-Sapling `sprout-proving.key` and `sprout-verifying.key` are not used and are not fetched. Source: `https://download.z.cash/downloads`. The script keeps a file that exists with the expected size; a file of any other size (an interrupted copy or a saved error page) moves to `<name>.bad` and downloads again. A download arrives in two parts, is joined, and moves into place only when its SHA-256 matches. `zerod` checks existence and size at startup and stops with a message naming the file, then verifies BLAKE2b hashes while loading. Release packages install the script as `zero-fetch-params`; it needs no other file.

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
| Boost | 1.88.0 | `boost.mk` | Node + tests. Darwin needs **`--toolset=clang`** and often **`-Wno-enum-constexpr-conversion`** (section 5.2). |
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
| Reconfigure after **`./autogen.sh`** | **`CONFIG_SITE=$PWD/depends/$HOST/share/config.site ./configure ...`** then **`make`** (see section 6.2) |
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

Extra options (e.g. **`ENABLE_SYSTEM_COMMAND`**) go in **`CONFIGURE_FLAGS`** for **`build.sh`**, or on the **`./configure`** line when configuring manually. Per-platform flag details: section 5.

### 4.3 Depends layout

- Each library is a `depends/packages/<name>.mk` recipe (version, URL, hash).
- **Portable `sed`:** recipes use `build_SED_INPLACE` (`sed -i.old` style). Do not use bare `sed -i`.
- Checksums: Linux `sha256sum`, Darwin `shasum -a 256`.

**Sharing depends between clones.** `depends/sources/` holds downloaded archives and is path-independent; several clones or worktrees can share one download directory with `SOURCES_PATH=/path/to/shared/sources`. `depends/built/` (override: `BASE_CACHE`) holds built packages whose files record the absolute prefix of the clone that built them, and its cache key does not include that path. Keep it per clone: do not copy `depends/built/` between clones, and after moving or renaming a clone run the clean rebuild in section 6.6.

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

#### 4.6.1 Shell notify hooks

Three optional flags run an **external shell command** when an event occurs. Each substitutes **`%s`** in the command string (block hash, transaction id, or sanitized warning text), then invokes the system shell via **`::system()`**:

| Flag | Trigger |
|------|---------|
| **`-blocknotify=<cmd>`** | Active chain tip changes |
| **`-walletnotify=<cmd>`** | Wallet sees a new or updated transaction |
| **`-alertnotify=<cmd>`** | Deprecation, long-fork, or unexpected block-rate warning |

**Default (release) builds do not execute these commands.** The hooks are gated at **compile time** by **`ENABLE_SYSTEM_COMMAND`**. If the flag is not set at build time, **`zerod`** logs that the notification was skipped and continues -- secure by default; opt-in only when the operator deliberately rebuilds.

**Distributed release policy (decision).** Official artifacts -- Linux tarball/`.deb` from **`zcutil/release-linux.sh`**, tagged GitHub releases, and CI contributor binaries -- stay **without** **`ENABLE_SYSTEM_COMMAND`**. That is intentional: default binaries must not invoke **`::system()`** even if an operator leaves legacy notify lines in **`zero.conf`**. Custom rebuilds may opt in; do not add the flag to release scripts or default **`CONFIGURE_FLAGS`** without an explicit security review and release-notes callout. Production indexers (Insight) use **ZMQ**, not shell hooks.

**Enable shell hooks** (operators who need them):

```bash
./configure CXXFLAGS="-DENABLE_SYSTEM_COMMAND"   # add to your usual CONFIGURE_FLAGS / zcutil/build.sh path
make -j$(nproc)
```

Verify: set **`-blocknotify='echo test >> /tmp/zero-blocknotify.log'`**, mine one regtest block, confirm the log line appears **only** on an **`ENABLE_SYSTEM_COMMAND`** build.

**Rationale.** Inherited Bitcoin Core behavior turns the node into a shell launcher. Config values come from **`zero.conf`** and the command line; even with sanitization on warning text, a mistaken or hostile config can run arbitrary commands as the **`zerod`** user. Most deployments use **ZMQ** or RPC polling instead; compile-time opt-in shrinks the attack surface of default binaries.

**When shell hooks are still appropriate**

| Use case | Example | Notes |
|----------|---------|-------|
| Legacy automation | **`blocknotify`** runs a fixed path script that touches a flag file for an old indexer | Prefer **`-zmqpubhashblock`** for new work |
| Wallet-driven ops | **`walletnotify`** appends txid to a fifo for a custom accounting daemon | Wallet must be enabled; high volume can spawn many threads |
| Node warnings | **`alertnotify`** emails or pages on a deprecation or long-fork warning (GTest **`DeprecationTest.AlertNotify`**) | Fires on this node's own warnings only |

**Preferred alternatives (no shell)**

| Need | Use instead |
|------|-------------|
| New block | **`-zmqpubhashblock=tcp://127.0.0.1:28332`** (requires ZMQ-enabled build; default on) |
| New tx | **`-zmqpubhashtx=...`**, **`-zmqpubrawtx=...`** |
| Wallet activity | Poll **`listtransactions`** / **`zs_listtransactions`** from a sidecar, or ZMQ raw tx |

**Testing:** GTest **`DeprecationTest`** covers default-build `-alertnotify`, `-blocknotify`, and `-walletnotify`.


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

Apple Clang. Configure with `--enable-proton=no` and `CXXFLAGS="-g -Wno-enum-constexpr-conversion"` (Boost/Clang). BDB mutex crash: see section 6.2.

### 5.3 Windows

Cross-compile from Linux via MXE. See section 2.4 for full steps. Manual: `make HOST=x86_64-w64-mingw32 -C depends`, configure with `--host`, make in `src/` with mingw compilers.

---

## 6. Detecting, Diagnosing, Troubleshooting

### 6.1 Params Missing

```
Please run 'zero-fetch-params' or './zcutil/fetch-params.sh' and then restart.
```

Run `./zcutil/fetch-params.sh` before starting zerod.

### 6.2 Berkeley DB

BDB **6.2.32** (depends). Used for wallet storage. Wallet-enabled builds require depends + **`CONFIG_SITE`** (see section 4.2).

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

**`-bind_at_load` linker warning (macOS):** Manual **`make`** or **`make check-symbols`** without **`MACOSX_DEPLOYMENT_TARGET`** can print **`ld: warning: -bind_at_load is deprecated on macOS`**. GNU libtool adds the flag when the env var is unset (defaults to **`10.0`**). **`./zcutil/build.sh`** exports **`MACOSX_DEPLOYMENT_TARGET=15.0`**; for manual builds run **`export MACOSX_DEPLOYMENT_TARGET=15.0`** first. Build still succeeds; warning is cosmetic.

### 6.3 Boost / GCC

**GCC too old:** Need GCC 7.0+ for C++14.

### 6.4 Memory Exhausted

**"virtual memory exhausted" or "killed":** Reduce jobs: `make -j1 zerod`. Or add swap.

### 6.5 Desktop wallet

The Qt desktop wallet is built elsewhere. This repo builds only `zerod`, `zero-cli`, `zero-tx`.

### 6.6 Clean Rebuild

`depends/` has no `clean` target; remove its generated directories instead. Downloaded sources in `depends/sources/` can stay.

```bash
make distclean
rm -rf depends/$HOST depends/built/$HOST depends/work
./zcutil/build.sh
```

`$HOST` is the depends host triplet, the directory name under `depends/` (for example `x86_64-pc-linux-gnu` or `aarch64-apple-darwin25.3.0`).

**Moved or copied clone.** depends installs packages with an absolute prefix (`<clone>/depends/$HOST`), and its pkg-config files and the configure output record that path. After renaming or moving a clone, or copying `depends/built/` from another clone, the build still searches the old location (linker warning `search path '<old path>/depends/...' not found`), and would link the old libraries if that directory existed. Check with:

```bash
grep -rl "<old clone path>" depends/$HOST/lib/pkgconfig config.status src/Makefile
```

If anything matches, run the clean rebuild above. A fresh clone that builds its own `depends/` is not affected.

### 6.7 Build Log

```bash
make -j4 2>&1 | tee build.log
grep -i error build.log
```


