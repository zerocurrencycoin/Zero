# BUILD_ZERO

Build, configure, and release the Zero full node: `zerod`, `zero-cli`, and `zero-tx`. Operators who build from source need Paths through Configuration; contributors also need How the build works and Troubleshooting; maintainers need Release.

---

## Scope

| Build host | Output | Tested |
|------------|--------|--------|
| Linux x86_64 | Linux binaries | Ubuntu 24.04, GCC 13.3 |
| macOS ARM64 | macOS binaries, macOS 15.0 and later | macOS 26.3, Apple Clang 21.0 |
| Linux x86_64 with MXE | Windows x86_64 binaries (`.exe`) | Cross-build only |

A Linux binary runs on the build OS release or newer (glibc and libstdc++ floor). Windows builds have no ZMQ. The desktop wallet, Zerowallet, is a separate application.

---

## Paths

| Platform | Data directory | Proving parameters |
|----------|----------------|--------------------|
| Linux | `~/.zero` | `~/.zcash-params` |
| macOS | `~/Library/Application Support/zero` | `~/Library/Application Support/ZcashParams` |
| Windows | `%APPDATA%\zero` | `%APPDATA%\ZcashParams` |

`-datadir=<path>` moves the data directory; the parameters stay in the platform path. Defaults are set in `GetDefaultDataDir` and `ZC_GetBaseParamsDir` (`src/util.cpp`).

At mainnet height 2567263 the data directory holds about 8.4 GiB of chain data (`blocks/` 7.8 GiB, `chainstate/` 0.6 GiB); the parameters take 741 MiB.

---

## Requirements

| Item | Requirement |
|------|-------------|
| Compiler | C++14: GCC 7 or later on Linux, Apple Clang on macOS, MXE mingw-w64 for Windows |
| Tools | GNU Make 4.0 or later, Git 2.0 or later, autotools |
| Python | 3.10 or later, checked by `zcutil/check-setup.sh` and `contrib/run-tests.sh`; validated on 3.10.18 and 3.12 |
| Memory | 16 GB for parallel `make`; lower `-j` if the linker is killed |
| Disk | Under 6 GB for the tree, `depends/`, and objects |

Libraries come from `depends/` as pinned, hashed source archives, not from the system package manager.

---

## Build

Fetch the proving parameters once per machine, before the first start of `zerod`. `fetch-params.sh` downloads `sapling-spend.params`, `sapling-output.params`, and `sprout-groth16.params` from `https://download.z.cash/downloads`, checks SHA-256, and keeps files that already have the expected size. Release packages install it as `zero-fetch-params`.

### Linux

```bash
sudo apt install build-essential pkg-config libc6-dev m4 g++-multilib \
  autoconf libtool ncurses-dev unzip git python3 python3-zmq \
  zlib1g-dev wget bsdmainutils automake cmake curl
git clone https://github.com/zerocurrencycoin/Zero.git && cd Zero
./zcutil/fetch-params.sh
./zcutil/build.sh -j$(nproc)
```

Other distributions: install the same tools under their package names.

### macOS

```bash
brew install automake cmake pkg-config coreutils
./zcutil/fetch-params.sh
./zcutil/build.sh -j4
```

`sw_vers -productVersion` shows the macOS release; the `depends` host name carries the Darwin version from `uname -r` (for example `aarch64-apple-darwin25.3.0`). Darwin needs Boost built with `--toolset=clang` and `-Wno-enum-constexpr-conversion`, which `boost.mk` applies; `configure.ac` adds `-Wno-enum-constexpr-conversion` for the node when the compiler supports it, and `build.sh` exports `MACOSX_DEPLOYMENT_TARGET=15.0`.

### Windows

Cross-build on the Linux host. Build MXE once (2 to 4 hours):

```bash
export MXE_ROOT=$HOME/mxe
sudo apt install -y autoconf automake autopoint bash bison bzip2 flex g++ g++-multilib gettext git gperf \
  intltool libc6-dev-i386 libgdk-pixbuf2.0-dev libltdl-dev libssl-dev libtool-bin libxml-parser-perl make \
  openssl p7zip-full patch perl pkg-config python3-mako python3-setuptools python3-tk python3-venv ruby sed \
  unzip wget xz-utils zstd
git clone https://github.com/mxe/mxe.git "$MXE_ROOT"
make -C "$MXE_ROOT" MXE_TARGETS='x86_64-w64-mingw32.static' gcc -j$(nproc)
```

Then build Zero; `-m PATH` overrides `MXE_ROOT`:

```bash
./zcutil/build.sh -win
```

Binaries are in `src/` on every platform.

---

## Configuration

`zerod` starts only when `zero.conf` exists in the data directory. An empty file is a complete configuration:

```bash
mkdir -p ~/.zero && touch ~/.zero/zero.conf
./src/zerod -daemon
./src/zero-cli getblockchaininfo
```

It works because every option has a default that fits a local node: `zerod` listens for peers on port 23801, serves RPC on 127.0.0.1:23811, `zero-cli` on the same host authenticates with the `.cookie` file that `zerod` writes, and mining is off.

| File | What it adds over the empty file | Use it when |
|------|----------------------------------|-------------|
| `contrib/zero.conf` | Nothing: every option is commented out and shows its default, grouped by subject | Looking up an option and its default; uncomment only the lines to change |
| `contrib/zero-conf.sh prod` | `rpcuser`, `rpcpassword` (generated), and `equihashsolver=tromp` | A client that does not read `.cookie`, such as Zerowallet or a tool under another user |
| `contrib/zero-conf.sh insight` / `zerowallet` / `lab` | Explorer indexes and ZMQ / the file Zerowallet writes / an isolated node with no peers | Those roles; `contrib/conf-templates/README.md` describes each |

RPC from another host also needs `rpcbind` and `rpcallowip`. Command-line options override the file. `reindex=` never belongs in the file: run `zerod -reindex` once instead.

`-blocknotify`, `-walletnotify`, and `-alertnotify` run a shell command only in builds compiled with `-DENABLE_SYSTEM_COMMAND` in `CXXFLAGS`; release builds log the skipped command. The shell-free alternative is ZMQ, described in zcashd [doc/zmq.md](https://github.com/zcash/zcash/blob/v5.4.0/doc/zmq.md).

---

## How the build works

The `zcutil` scripts; each lists its options with `--help`:

| Script | Does | Used in |
|--------|------|---------|
| `fetch-params.sh` | Downloads and checks the proving parameters | Build |
| `build.sh` | Runs `build-native.sh` on Linux and macOS, `build-win.sh` with `-win` | Build |
| `build-native.sh`, `build-win.sh` | Native build; Windows cross-build with MXE | Build |
| `check-setup.sh` | Checks the build host: toolchain and parameters | Release |
| `check-release.sh` | Checks that tree, version, and build match a release tag | Release |
| `build-release.sh` | Runs `check-setup.sh`, `check-release.sh`, then `build.sh` | Release |
| `release-linux.sh`, `release-macos.sh`, `release-win.sh` | Stage, sign, and archive the binaries of one platform | Release |
| `checksums.sh` | Writes or verifies `artifacts/SHA256SUMS` | Release |
| `fzero.sh`, `fmessage.sh` | Shared helpers and messages, sourced by the scripts above | -- |

`zcutil/build.sh` runs four stages every time:

| Stage | Command | Cost |
|-------|---------|------|
| depends | `make -C depends` | Seconds with a warm cache in `depends/built/$HOST/`; long on a cold cache, mostly Boost and the Rust crates |
| autogen | `./autogen.sh` | Seconds |
| configure | `./configure` with `CONFIG_SITE=depends/$HOST/share/config.site` | Under two minutes |
| make | `make -jN` | Minutes incremental, longer from clean |

`config.site` points the compilers, headers, libraries, and pkg-config at `depends/$HOST/`. A `./configure` without it uses system paths and fails the wallet check (`libdb_cxx headers missing`), because Berkeley DB 6.2.32 comes only from `depends`.

After editing `src/` only, run `make -jN` in the configured tree. To run the stages by hand, as `build-native.sh` does:

```bash
HOST=$(./depends/config.guess)
make -C depends NO_PROTON=1 HOST="$HOST" -j$(nproc)
./autogen.sh
CONFIG_SITE=$PWD/depends/$HOST/share/config.site ./configure --prefix=$PWD/depends/$HOST --host="$HOST" CXXFLAGS='-g'
make -j$(nproc)
```

`depends/README.md` (variables such as `SOURCES_PATH` and `NO_WALLET`) and `depends/packages.md` (recipe format) are the upstream Bitcoin Core descriptions of `depends`. Keep `depends/built/` per clone: built packages record the absolute path of the clone that built them.

| Variable | Effect |
|----------|--------|
| `FZERO_MAX_JOBS` | Cap on make jobs (default 8, `zcutil/fzero.sh`) |
| `CONFIGURE_FLAGS` | Extra `./configure` options; not `CXXFLAGS`, which `build-native.sh` sets to `-g` after them |
| `RUST_USE_SYSTEM=1` | System `cargo` and `rustc` on Linux; macOS always uses the system Rust; otherwise `depends` uses the pinned Rust 1.32.0. Check which one a build used: `depends/$HOST/native/bin/rustc --version` (a symlink to the system `rustc` when system Rust is used) |

Versions are pinned in `depends/packages/*.mk`: Berkeley DB 6.2.32 sets the wallet file format and fixes the ARM64 mutex crashes of 6.2.23; OpenSSL 1.1.1w (end of life upstream); libsodium 1.0.21; libevent 2.1.12; Googletest 1.16.0, the last release for C++14; librustzcash changes only with protocol work.

`depends` compiles with `-O1`, as in zcashd; `build-native.sh` adds `-g`. The packaging scripts strip the copies they package.

---

## Datadir contents

| File | Purpose |
|------|---------|
| `zero.conf`, `zerod.pid` | Configuration; process ID while running |
| `blocks/blk*.dat`, `blocks/rev*.dat`, `blocks/index/` | Blocks (128 MiB files), undo data, block index (LevelDB) |
| `chainstate/` | Unspent outputs (LevelDB) |
| `wallet.zero`, `database/`, `db.log` | Wallet (Berkeley DB) and its environment |
| `debug.log`, `peers.dat`, `fee_estimates.dat` | Log, peer addresses, fee statistics |
| `.cookie` | RPC cookie, written at start and deleted on shutdown |
| `zeronode.conf`, `zncache.dat`, `znpayments.dat`, `budget.dat`, `sporks/` | Zeronode aliases (`-znconf`), zeronode list, payment votes, budget messages, sporks |
| `onion_private_key` | Tor hidden service key, only with `-listenonion` (off by default) |

**Index settings.** `blocks/index` records five settings as `DB_FLAG` entries (`CBlockTreeDB::UpdateFlag` in `src/txdb.cpp`, checked in `AppInit2`): `txindex` and `archiverule` always on, `prunedblockfiles` always off, `insightexplorer` and `zindex` from `-insightexplorer` and `-zindex` (default off). A mismatch with the current value on a datadir with blocks starts one `-reindex`; a missing entry counts as off; a new datadir records the values without a reindex. `-txindex` and `-prune` are not `zerod` options.

---

## Release

All steps run at the release commit on the release branch, with `git status --short` empty before each tag.

**Version.** `_CLIENT_VERSION_*` in `configure.ac`. `_CLIENT_VERSION_BUILD` 0 to 24 gives `-betaN` (N = build + 1), 25 to 49 `-rcN` (N = build - 24), 50 the release, above 50 `-N` (N = build - 50). After a change, rebuild and run `./contrib/devtools/gen-manpages.sh`.

**Test.** `./zcutil/check-setup.sh`, build, then TEST_ZERO "Release bar" on each platform.

**Tag.** `check-release.sh` must print READY on every line:

```bash
./zcutil/check-release.sh --release vX.Y.Z-rcN --expect HEAD --levels=tree,configure,build
git tag -a vX.Y.Z-rcN -m "Zero vX.Y.Z-rcN"
./zcutil/check-release.sh --release vX.Y.Z-rcN --exact --levels=tree,configure,build
git push origin <release branch> vX.Y.Z-rcN
```

**Package.** At the tag, on each build host. Each script stages the binaries and README in `bin/`, writes the archive to `artifacts/`, strips the copies unless given `-s`, and rewrites `artifacts/SHA256SUMS`. The version comes from the build unless given `-v`.

| Run on | Command | Output |
|--------|---------|--------|
| Linux, after `build.sh` | `./zcutil/release-linux.sh` | `linux-zero-v<ver>.tgz`, `linux-zero-v<ver>.deb` (`Package: zero`, with `zero-fetch-params`; `-rcN` is written `~rcN`) |
| macOS, after `build.sh` | `./zcutil/release-macos.sh --sign IDENTITY --notarize PROFILE` | `macos-zero-v<ver>-<arch>.zip`, with `zero-fetch-params` |
| Linux, after `build.sh -win` | `./zcutil/release-win.sh --sign-pkcs12 FILE` | `win-zero-v<ver>.zip` |

`--sign` applies a Developer ID signature with the hardened runtime; `--notarize` submits the zip with `xcrun notarytool` (Gatekeeper checks notarization online, since a zip of command-line tools cannot be stapled). `--sign-pkcs12` applies Authenticode with `osslsigncode`, password in `ZERO_AUTHENTICODE_PASS`. Without these options the archives are unsigned and the scripts warn.

**Checksum and sign.** In the same sitting: collect all archives in one `artifacts/`, run `./zcutil/checksums.sh` and `./zcutil/checksums.sh --verify` after the last signing step, then sign `SHA256SUMS` with the method chosen for the release. Unsigned CI artifacts are not releases.

**Publish.** The body is `doc/release-notes/release-notes-X.Y.Z.md`: the state at this release against the previous published release, for operators, miners, pools, and integrators.

```bash
gh release create vX.Y.Z artifacts/* --title "Zero vX.Y.Z" --notes-file doc/release-notes/release-notes-X.Y.Z.md
```

**Verify a download.** In the download directory (`--ignore-missing` skips other platforms' archives):

| Platform | Commands |
|----------|----------|
| Linux | `sha256sum --ignore-missing -c SHA256SUMS` |
| macOS | `shasum -a 256 --ignore-missing -c SHA256SUMS`; after unzipping, `codesign --verify --strict zerod` and `spctl --assess --type execute -v zerod` |
| Windows (PowerShell) | `Get-FileHash -Algorithm SHA256 win-zero-v<ver>.zip`, compared with `SHA256SUMS`; `signtool verify /pa zerod.exe` |

---

## Troubleshooting

| Symptom | Cause and fix |
|---------|---------------|
| `Please run 'zero-fetch-params' or './zcutil/fetch-params.sh'` | Parameters missing or of the wrong size: run `fetch-params.sh`. A wrong-size file is moved to `<name>.bad` and downloaded again |
| `libdb_cxx headers missing` | `./configure` ran without `CONFIG_SITE`, or `depends` was not built for this `HOST`: check `ls depends/$HOST/include/db_cxx.h`, then use `build.sh` or the manual stages above |
| `virtual memory exhausted`, or the compiler is killed | Lower the job count (`-j2`) or add swap |
| `ld: warning: -bind_at_load is deprecated` (macOS) | Manual `make` without `MACOSX_DEPLOYMENT_TARGET`; `build.sh` exports 15.0. Harmless |
| BDB mutex crash on start (macOS) | Remove `database/` in the data directory and restart |
| `search path '<old path>/depends/...' not found` | The clone was moved or `depends/built/` was copied from another clone: clean rebuild |
| Anything else after a recipe or host change | Clean rebuild |

Clean rebuild (`depends` has no `clean` target; `depends/sources/` can stay):

```bash
make distclean
rm -rf depends/$HOST depends/built/$HOST depends/work
./zcutil/build.sh
```

### Clock

Since Cosmos (height 620,450), `zerod` refuses a block whose time is more than 10 minutes ahead of its adjusted time (`time-too-new`, `CheckBlockHeader`), and a miner's clock sets its block timestamps. The adjusted time is the local clock plus the median offset reported by peers; a median of 70 minutes or more is ignored, with a one-time warning when no peer is within 5 minutes (`AddTimeData`). Both limits are compiled in. They only judge blocks against the current time, so a reindex or an import of old blocks is unaffected; a host clock more than 10 minutes slow refuses new blocks until it is corrected. `-mocktime` is for regression tests.

Ubuntu 18.04 and 24.04 both run `systemd-timesyncd` by default, which is accurate to milliseconds on a VPS; chrony is needed only for its reporting (`chronyc tracking`) or a stricter discipline.

| Check or setting | Command |
|------------------|---------|
| Synchronized, service active | `timedatectl` (`System clock synchronized: yes`, `NTP service: active`) |
| Offset and server, systemd 239 and later (Ubuntu 20.04 and later) | `timedatectl timesync-status` |
| Server, systemd 237 (Ubuntu 18.04), which shows no offset | `journalctl -u systemd-timesyncd --no-pager \| tail -5` ("Synchronized to time server") |
| Offset with any version | `chronyc tracking` with chrony; otherwise a one-shot query that sets nothing, below |
| Servers for timesyncd | `NTP=` in `/etc/systemd/timesyncd.conf`, then `systemctl restart systemd-timesyncd` |
| Enable after a stop | `timedatectl set-ntp true` |
| Peer offsets as the node sees them | `getpeerinfo` `timeoffset` |

One-shot offset on Ubuntu 18.04, where `ntpdate` coexists with timesyncd:

```bash
sudo apt-get install -y ntpdate
ntpdate -q time.cloudflare.com    # "offset +0.001842 sec"
```

### Chain diagnostics

| Question | Tool |
|----------|------|
| Is the node on the best chain; which forks did it see | `getblockchaininfo`, `getchaintips` (stale branches and their length) |
| Are the block and undo files consistent | `verifychain`, or `-checkblocks=N -checklevel=0..4` at startup |
| Does the coin supply add up | `gettxoutsetinfo` plus the shielded `valuePools` of `getblockchaininfo`, against `getsupply` (the schedule) |
| How fast do transactions arrive | `getchaintxstats`, `getmempoolinfo`, `getrawmempool` |
| Which peer sends what | `getpeerinfo`, `-debug=net`; ban with `setban` |
| Where does block connection spend time | `-debug=bench` |
| Leave a bad block or branch | `invalidateblock <hash>`, undo with `reconsiderblock` (hidden RPCs) |
| Rebuild indexes or the wallet view | `-reindex`, `-rescan`; import blocks with `-loadblock` and `-stopafterblockimport` |
| Cache use | `getdbinfo` |
