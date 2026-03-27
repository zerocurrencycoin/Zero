# UpdateBuild

Maintainer hub: **peer dependency snapshot**, **in-tree build archaeology**, **deferred upgrades**, and **planned validation**. Porter-facing **version rationale**, **depends layout**, **recipe debugging**, and **other Linux** guidance live in **BUILD_ZERO.md** (§2.2.1, §4.1, §4.8, §4.9)—not duplicated here.

---

## 1. Index

| Topic | Where |
|-------|--------|
| Version table + why pins exist | **BUILD_ZERO.md** §4.1 |
| `depends/` layout, `sed`/checksum portability | **BUILD_ZERO.md** §4.8 |
| When a single depends package fails | **BUILD_ZERO.md** §4.9 |
| Install lists, `config.site`, `build.sh` | **BUILD_ZERO.md** §2–§5 |

---

## 2. Autoconf macros (maintainer)

**`build-aux/m4/`** — when refreshing **`ax_pthread.m4`** or other vendored macros, prefer **`AS_ECHO`** patterns from current autoconf-archive (reduces Autoconf deprecation noise vs **`$as_echo`**).

---

## 3. Source-tree build fixes

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

## 4. Deferred upgrades

| Item | Note |
|------|------|
| **Rust pin** | Replace 1.32.0 download + ARM symlink with one pinned modern toolchain for all targets. |
| **OpenSSL** | See **BUILD_ZERO.md** §4.1; needs call-site audit and test plan before 3.x or removal. |
| **librustzcash** | With network upgrades only. |
| **Proton** | Revisit only if AMQP path is productized. |
| **utfcpp** | Optional header-only bump. |
| **Boost >1.88** | Requires C++ standard and **`ax_boost_*`** revalidation. |

---

## 5. Peer dependency snapshot

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

## 6. Reference layout

Local comparison trees often live under **`~/Work/ZK/ZKs/`** (bitcoin-src, zcash, zen, pirate, fluxd, zclassic, hush3, …). **Zero** node checkouts typically **`~/Work/ZK/Zero400`** (or parallel **`ZeroLinux`** / **`ZeroWin`** build dirs).

**`ZKs/Comparison.md`:** PoW, peer logic, Equihash ecosystem notes—separate from this file.

---

## 7. Planned build validation

| Check | Purpose |
|-------|---------|
| **Parity** | Same configure knobs on **`build.sh --daemon`** and **`build-win.sh`** where intended (`--disable-zmq`, `--disable-rust`, …). |
| **Depends smoke** | **`make -C depends HOST=x86_64-w64-mingw32`** succeeds on Linux before full Windows artifact build. |

Optional later: **`config.site`** presence, **`configure --help`** drift vs scripts, PE sanity on Windows outputs.
