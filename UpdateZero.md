# UpdateZero

Maintainer hub.

---

## 1. Documentation map

User-facing docs: **README**, **BUILD_ZERO**, **TEST_ZERO**, **ZERO_COIN**, **TODO**, **CONTRIBUTING**, **AGENTS.md**.
They do not reference this file.

---

## 2. Consensus and zeronode

**Branch id.** Sapling and Cosmos both use **`0x7361707a`** in `src/consensus/upgrades.cpp`. Duplicate id is documented technical debt until a deliberate NU.

**Zeronode.** `src/zeronode/*` parallels Dash-style `masternode/*`. Safe iterator order when cleaning expired broadcasts. `CheckInputsAndAdd` has a null-guard for `chainActive[height]`; other sites need the same audit (see §7 issues).

---

## 3. Engineering policy

**Height and expiry.** `TransactionBuilder::SetExpiryHeight` mixes `int` chain height with `uint32_t` expiry. Prefer explicit casts or `int64_t` for height in new code.

**Numeric policy (NUM-01).** Consensus and subsidy paths should be integer-only; default rounding: truncate toward zero. No new float in consensus without review. See BUILD_ZERO §4.8 for touchpoint audit.

**C++ exceptions.** `throw std::runtime_error("...")`, not `throw new`. Removed from `src/**/*.cpp` on the integration line.

---

## 4. Release process

**Artifacts.** Tag `vMAJOR.MINOR.PATCH`; archives `Zero-<ver>-<target>-<triplet>.<ext>`; checksum file and optional detached `.asc`.

**Version identity.** `configure.ac` (`_CLIENT_VERSION_*`), `src/config/bitcoin-config.h`, `src/clientversion.h`. After bump: build/smoke per BUILD_ZERO, contributor gate per TEST_ZERO, confirm `zerod -version`.

```bash
cd ~/Work/ZK/Zero400
git fetch origin
git checkout zero-merge
git pull --ff-only origin zero-merge
```

---

## 5. Fork-specific implementation

**Witness path.** Zero uses `VerifyAndSetInitialWitness` and `BuildWitnessCache` with optional `pblockIn`, coupling to `pcoinsTip` and chain views. Hardening: null checks, `pblockIn`, nullifier guards. Code: `src/wallet/wallet.cpp`, `wallet.h`.

**Equihash.** Zero keeps libsodium C `crypto_generichash_blake2b_state` for `eh_HashState`. A Rust/CXX bridge like Zcash v6+ would need `librustzcash`/`rustcxx` alignment -- out of scope unless the PoW stack moves.

**Branding.** User-visible strings should read ZERO. Clean residual Zcash/Bitcoin names when touching files; not consensus.

---

## 6. Test harness prescriptions

Use when porting or fixing RPC tests. How to run: TEST_ZERO.

**P2P / regtest.** Peers must advertise `nVersion >= 170007`; `mininode.py` default 170009. Regtest magic must match `chainparams.cpp`.

**Coinbase maturity 720.** Call `mine_until_node_has_mature_coinbase` or `ensure_mature_coinbase_or_skip` before spends. Optional `ZERO_MINE_COINBASE=1` for bulk mine.

**Regtest NU.** `-nuparams=6f76727a:1` (Overwinter), `-nuparams=7361707a:1` (Sapling). Blossom: set `-nuparams` above tip after maturity mining.

**Wallet.** Sprout viewing key: if `GetSproutNoteNullifier` is empty, skip nullifier map update. Ref: `wallet.cpp`, `wallet_changeindicator.py`.

**Python 3.** `serialize_script_num`: `bytearray.append(int)`, not `chr(...)`. Import `initialize_chain_clean` when used.

**Partition tests.** `split=True`: only edges 0-1 and 2-3; `CHAIN_BOOTSTRAP` + guard before re-mine. Ref: `getchaintips.py`.

New prescription: add a row here and a TEST_ZERO harness changelog entry if behavior is user-visible.

---

## 7. Subsidy implementation reference

Code excerpts for consensus subsidy paths. File:line drift possible -- verify against `src/`. User narrative: ZERO_COIN.md.

**GetBlockSubsidy** (`src/main.cpp`):

```cpp
CAmount GetBlockSubsidy(int nHeight, const Consensus::Params& consensusParams)
{
  CAmount nSubsidy = 10 * COIN;
  if (nHeight>=consensusParams.nFeeStartBlockHeight) {
    nSubsidy = 10.8 * COIN;
  }

    int halvings = consensusParams.Halving(nHeight);
    if (halvings >= 64)
        return 0;

    if (consensusParams.NetworkUpgradeActive(nHeight, Consensus::UPGRADE_BLOSSOM)) {
        return (nSubsidy / Consensus::BLOSSOM_POW_TARGET_SPACING_RATIO) >> halvings;
    } else {
        return nSubsidy >> halvings;
    }
}
```

**Params::Halving** (`src/consensus/params.cpp`): pre-Blossom `halvings = nHeight / nPreBlossomSubsidyHalvingInterval` (800000). No slow start.

**GetLastFoundersRewardBlockHeight:** pre-Blossom `800000*10 - 1 = 7,999,999`.

**Founders:** `src/zeronode/payments.cpp`, `budget.cpp` -- `blockValue * 7.5 / 100`.

**GetZeronodePayment** (`src/main.cpp`): default 20% of `blockValue`; tier steps at 800k multiples with SPORK_6/7.

**FillBlockPayee** (`src/zeronode/payments.cpp`): superblock path vs default; order: blockValue, founders, zeronode, miner + fees.

**Consensus validation** (`src/main.cpp`): requires founders output when `nFeeStartBlockHeight <= height <= GetLastFoundersRewardBlockHeight`.

**Addresses in code:** `src/chainparams.cpp` -- `vFoundersRewardAddress` (mainnet/testnet/regtest); RPC `developmentfee` (`src/rpc/zeronode.cpp`). `ZeronodeDummyAddress` -- collateral validation only.

---

## 8. Build reference

### Autoconf macros

`build-aux/m4/` -- when refreshing `ax_pthread.m4` or other vendored macros, prefer `AS_ECHO` patterns from current autoconf-archive (reduces Autoconf deprecation noise vs `$as_echo`).

### Source-tree build fixes (applied)

- `equihash.cpp`: template instantiations guarded with `ENABLE_MINING`.
- `hash.h`: `CSHA256::OUTPUT_SIZE` for stack buffers (Clang VLA warnings).
- `secp256k1 .la`: `fzero.sh` `cleanup_secp256k1_la()` drops stale `.la` when embedded HOST disagrees with current `$HOST`; invoked by `build-native.sh` / `build-win.sh`.
- Automake: `distcleancheck_listfiles = find . -false` override intentional (vendored trees / dist hooks).
- `secp256k1 configure`: `AC_PROG_CC` instead of obsolete C89 macro.
- ZMQ on Darwin: `configure.ac` strips `-lstdc++` from `ZMQ_LIBS` on `*darwin*` when `libc++` is selected (avoids duplicate C++ stdlib linkage).
- GTest: `test_miner.cpp` only in `zero_gtest_SOURCES` when `ENABLE_MINING` (`src/Makefile.gtest.include`).
- Zeronode: `SliceHash` `memcpy` source pointer arithmetic corrected (fortify / correctness).
- Spork sentinels: `4070908800` in `src/zeronode/spork.h` `SPORK_*_DEFAULT` values is intentional "off" encoding; `budget.cpp` `GetBudgetPaymentCycleBlocks()` uses `INT_MAX` for the same purpose on mainnet.

### Peer dependency snapshot (Apr 2026)

| Library | Zero | Zcash | Pirate | Bitcoin | Zero source |
|---------|------|-------|--------|---------|-------------|
| BDB | 6.2.32 | 6.2.23 | 6.2.32 | removed | `depends/packages/bdb.mk` |
| libsodium | 1.0.21 | 1.0.20 | 1.0.18 | -- | `depends/packages/libsodium.mk` |
| Boost | 1.88.0 | 1.83.0 | 1.83.0 | 1.88.0 | `depends/packages/boost.mk` |
| Rust | 1.32.0 | 1.81.0 | 1.69.0 | -- | `depends/packages/rust.mk` |
| OpenSSL | 1.1.1w | removed | -- | removed | `depends/packages/openssl.mk` |

Version pins live in `depends/packages/*.mk` (`$(package)_version` variable). The table above is a point-in-time comparison. Zcash/Pirate/Bitcoin columns are historical snapshots of their respective trees; re-verify against upstream before any merge or release.

---

## 9. Issues and Tasks

All tracked issues, deferred decisions, and work backlog. TODO.md is a minimal contributor-facing subset.

**Impact categories:** non-consensus bugfix (node release only); consensus/fork (NU + comms); index/explorer (redeploy); wallets (wallet release + notice).

**Rule:** Items about possible errors, misstatements, or unconfirmed arithmetic (e.g. supply computation, subsidy rounding) stay here until researched, confirmed, and fixed or mitigated. They do not go into user-facing documentation until resolved.

### README rewrite (high urgency)

Merge/rewrite README.md and README0.md into a single coherent front page. Current README has era-dependent figures, marketing-era copy, and inconsistencies with ZERO_COIN.md.

### Params archival

`zcutil/fetch-params.sh` still references upstream Zcash parameter file names and mirror URLs. Tasks: (1) Audit parameter file names vs what `zerod` actually loads at startup. (2) Verify mirror URLs are live. (3) If mirrors are dead or renamed, update the script or document the manual procedure. See BUILD_ZERO §3.

### Chain bootstrap procedure

Document a bootstrap procedure for new node operators: where to obtain a trusted chain snapshot, verification steps, and datadir placement. This is separate from params (proving key files) -- bootstrap is about the block/chainstate data. Currently undocumented.

### Debian packaging

`zcutil/build-debian-package.sh` (zcash naming) likely superseded by `zcutil/release-linux.sh` (zero naming). Confirm and deprecate.

### Parallel Tier A RPC (deprioritized)

`paymentdisclosure` hang under `--jobs>1`. Serial gate is sufficient. Deprioritized with other CI-focused issues.

### Release branch cleanup

Fifteen release branches (v1.0.12 through z21) are redundant with their corresponding tags and safe to delete remotely. No commits are reachable only from the branch.

### SUPPLY-01 -- Total supply discrepancy

Project target is some **20M ZER**. Current `GetBlockSubsidy` piecewise sum (fee-start 412300, 10.8 ZER post-fee base, geometric halving) computes ~25.6M ZER long-run. This exceeds the target.

**Action:** (1) Review implementation arithmetic vs original spec. (2) Determine whether the 10.8 post-fee base or the fee-start transition needs adjustment. (3) Compare upstream Zcash and Pirate supply computations. (4) `MAX_MONEY` in `amount.h` caps per-output amounts only; not a total-supply cap. User-facing docs say "some 20M" until resolved.

### NUM-01 -- Consensus integer math

Replace `double`/`COIN` mixes in `GetBlockSubsidy`, founders `* 0.075`, and validation paths with `CAmount` integer policy. Audit touchpoints in BUILD_ZERO §4.8. Steps: grep `double`/`float`/`0.075`/`10.8 * COIN` under `src/` in consensus paths; match validation and mining for identical order of operations; add far-future halving tests.

### NU-01 -- Branch id posture

Sapling and Cosmos share `0x7361707a`. No planned fork to split. Optional: CI guard for duplicate active mainnet `nBranchId`.

### chainActive[] audit

Full audit of `src/zeronode/` for `chainActive[` bracket access and `chainActive.Tip()` dereference without null guard. `CChain::operator[]` returns NULL when `nHeight < 0` or `nHeight >= vChain.size()` (`src/chain.h:644-647`).

**Unguarded sites (fix required):**

| File | Line | Function | Risk |
|------|------|----------|------|
| `zeronode.cpp` | 685 | `CZeronodePing::CZeronodePing(CTxIn&)` | `chainActive[chainActive.Height() - 12]` -- NULL if chain < 12 blocks (startup/regtest). Not external input. |
| `swifttx.cpp` | 231 | `CreateNewLock` | `chainActive.Tip()->nHeight` -- NULL if no tip (empty chain). Internal/tx-driven. |

**Already guarded (no action):**

| File | Line | Function |
|------|------|----------|
| `zeronode.cpp` | 613 | `CheckInputsAndAdd` -- `pConfIndex` null-checked before use. |
| `swifttx.cpp` | 424 | `CleanTransactionLocksList` -- `if (chainActive.Tip() == NULL) return`. |
| `budget.cpp` | multiple | `FillBlockPayee`, `GetBudget`, `IsValid`, `GetBlockCurrentCycle`, `AutoCheck` -- all assign `pindexPrev = chainActive.Tip()` then check before use. |
| `payments.cpp` | multiple | `IsBlockValueValid`, `FillBlockPayee`, `ProcessMessage`, `IsScheduled`, `Sync` -- compound `if (!locked \|\| chainActive.Tip() == NULL) return` guards. |
| `zeronode-sync.cpp` | | `Process` -- `pindexPrev` checked. |

**Fix:** Add null checks at `zeronode.cpp:685` and `swifttx.cpp:231`. Both trigger only on very short chains (< 12 blocks), not from peer-supplied input, so crash risk is startup/regtest-only. Not exploitable.

### Deferred upgrades

| Item | Note |
|------|------|
| Rust pin | Replace 1.32.0 + ARM symlink with one pinned modern toolchain. |
| OpenSSL | Remain on 1.1.1w until audited 3.x or removal. |
| librustzcash | With network upgrades only. |
| Proton / AMQP | Revisit only if AMQP productized. AMQP options (`-amqppub{hashblock,hashtx,rawblock,rawtx}`) exist in init.cpp HelpMessage but are not tracked in Options.csv pending productization. |
| Boost >1.88 | Requires C++ standard and `ax_boost_*` revalidation. |

### Hidden options (no HelpMessageOpt, parsed in init.cpp)

| Option | Default | Effect |
|--------|---------|--------|
| `-deleteconflicttx` | true | With `-deletetx`, allow removing conflicted (depth -1) wallet txs. Wallet-only. |
| `-enableswifttx` | true | Wallet-side SwiftTX lock depth/signatures. Does not disable `main.cpp` IX helpers. |
| `-swifttxdepth` | 5 (clamp 0-60) | Virtual confirmation boost for SwiftTX-locked txs in wallet and `GetIXConfirmations`. |

Added to Options.csv as `*-hidden` category. Not in `-help` output.

### zcrawreceive (legacy Sprout)

Sprout-only note decryption + commitment witness probe. Self-marked DEPRECATED in RPC help. Both params are strings so missing `vRPCConvertParams` entry is correct (no fix needed). Still operable for Sprout ciphertexts. Deprecate and remove with Sprout removal; do not expose in user docs.

### Release build flags

Current state of optimization and debug flags:

| Source | Flag | Effect |
|--------|------|--------|
| `depends/hosts/linux.mk` (and darwin, mingw32, freebsd) | `-O1 -pipe` | Injected via `config.site` for both release and debug. Conservative; Zcash-like. Bitcoin Core uses `-O2`. |
| `zcutil/build-native.sh` | `CXXFLAGS='-g'` | Always passed to `./configure`. Adds debug symbols to every native build. Also suppresses `configure.ac` warning flags (`-Wall`/`-Wextra`) because setting `CXXFLAGS` triggers `CXXFLAGS_overridden`. |
| `zcutil/build-win.sh` | `CXXFLAGS="-DPTW32_STATIC_LIB ..."` | No `-g`; no explicit optimization (inherits depends `-O1`). |
| `zcutil/release-linux.sh` | `strip` on staged copies | Strips `zerod`, `zero-cli`, `zero-tx` in tarball and .deb by default. `-s` flag skips. |
| `contrib/devtools/split-debug.sh` | `objcopy --only-keep-debug` | Exists but not wired into release pipeline. |

**Proposed changes:**

1. **`build-native.sh`:** Gate `-g` behind `ZERO_DEBUG=1` or remove it from the default configure line. Currently it inflates objects and suppresses warning flags for all builds.
2. **`depends/hosts/*.mk`:** Evaluate `-O2` for release (benchmark first); `-O1` is Zcash-inherited, not optimal.
3. **`configure.ac`:** Decouple `CXXFLAGS_overridden` from bare `-g` so warning flags are not suppressed when only debug symbols are requested.
4. **`release-linux.sh`:** Optionally integrate `split-debug.sh` for a separate `-dbg` package.

### Release signing and integrity

No release checksum or signing procedure exists. Minimum viable and ideal approaches:

**Linux:** Publish `SHA256SUMS` + detached GPG signature (`SHA256SUMS.asc`) from a dedicated release key. Document: import key, `gpg --verify`, `sha256sum -c`. Ideal: reproducible builds + multi-builder attestations (Bitcoin Core Guix model). Cost: time only.

**macOS:** Apple Developer ID signing + notarization (`codesign` + `xcrun notarytool`). $99/year. Without it, Gatekeeper blocks or warns; users must bypass ("developer cannot be verified"). Ad-hoc signing (`codesign -s -`) satisfies Apple Silicon requirements but does not pass Gatekeeper for downloads.

**Windows:** Authenticode OV certificate + `signtool sign`. Typically several hundred USD/year from a public CA; hardware token often required. Without it, SmartScreen shows "Windows protected your PC" on every download. EV certificates may build reputation faster.

**Cross-platform:** Sigstore/cosign as supplementary attestation layer. Does not replace GPG or OS signing for end-user trust.

**What peers do:** Bitcoin Core uses Guix + multi-builder GPG attestations + codesigned macOS/Windows. Zcash uses Gitian + gitian.sigs. Monero uses GPG-signed hashes.

### macOS developer signing (tracking)

Enroll in Apple Developer Program. Sign with Developer ID Application identity (`--options runtime`, `--timestamp`). Notarize with `xcrun notarytool`. Staple ticket for .dmg distribution. Without this, macOS users face Gatekeeper quarantine on every download.

### Build validation (pending)

| Check | Purpose |
|-------|---------|
| Parity | Same configure knobs on `build.sh --daemon` and `build-win.sh`. |
| Depends smoke | `make -C depends HOST=x86_64-w64-mingw32` succeeds before full Windows build. |

### Test exclusions and root causes

**GTest:** CachedWitnesses* excluded (harness lacks pcoinsTip). WriteCryptedSaplingZkeyDirectToDb hangs (CDB::Rewrite deadlock). 4.3-4.8 fixed.

**Boost:** Alert_tests excluded (MagicBean subver). equihash_tests excluded (96,5 vs 192,7). miner_tests excluded (same). rpc_wallet_encrypted_wallet_sapzkeys excluded (CDB::Rewrite). 5.4-5.8 fixed.

**RPC Python:** Skips for coinbase maturity (720), protocol version, clean-chain amounts. getchaintips main path fixed. Parallel Tier A (`--jobs>1`) unreliable.

### Test coverage gaps

| Area | Coverage | Key gaps |
|------|----------|----------|
| zero_exclusive RPCs | 0% | zs_listtransactions, zs_gettransaction, getalldata, getsupply |
| zero_experimental | 0% | getsaplingwitness, getsaplingwitnessatheight, getsaplingblocks |
| Zeronode logic | 0% | Payment calc, budget validation, collateral |
| SwiftTX / Spork | 0% | Lock conflict, activation |
| Zeronode RPC | ~25% | zeronodecurrent, getzeronodeoutputs, startzeronode, budget subcmds |
| Mining/PoW | 75% | miner_tests excluded (192,7 vs 96,5) |
| Wallet | 80% | CDB::Rewrite blocks 3 tests |
| RPC Python (Tier A) | 19 pass-only | exit 0 != full scenario coverage |
| Fuzz | 0% | No infra |

### zero_exclusive param validation (high importance)

Zero's own RPCs (`zs_listtransactions`, `zs_gettransaction`, `getalldata`, `getsupply`, `zs_listspentbyaddress`, `zs_listreceivedbyaddress`, `zs_listsentbyaddress`) and experimental RPCs (`getsaplingwitness`, `getsaplingwitnessatheight`, `getsaplingblocks`) have 0% test coverage. Minimum: Boost param-validation tests (bad-arg / missing-arg / help output). These are the only RPCs unique to Zero and the most likely to carry undiscovered issues.

### Test work priorities

**P1 (quick):** zeronode super/znbudget super subcmd validation; zero_experimental param validation.

**P2 (medium):** Zeronode logic GTest (mock znodeman, budget); SwiftTX/Spork GTest; Zeronode Python integration; CDB::Rewrite fix; CachedWitnesses pcoinsTip population.

**P3:** Zero (192,7) Equihash vectors; partition/misbehavior P2P; parallel Tier A stabilization; wallet backup/restore.

**P4 (deferred):** Fuzz infra; functional test migration.

### Debug notes

**CachedWitnesses*:** Partial fixes applied (index lifetime, pblockIn path). Still fails on pre-add witnesses and EXPECT_DEATH vs no assert. Debug: `./src/zero-gtest --gtest_filter='WalletTests.CachedWitnessesEmptyChain' --gtest_break_on_failure`.

**CDB::Rewrite:** `wallet/db.cpp` busy-waits on mapFileUseCount while EncryptWallet holds DB open. Fix path: close wallet DB before rewrite, or copy-then-rename.

**wallet.py node0 balance:** Node0 ~19 vs expected 29 on clean chain; COINBASE_MATURITY/subsidy. Debug: `--nocleanup`, `listunspent` at heights 4-6.

### CSV inventories

Repo-root CSVs (`RPCs.csv`, `RPCs_extended.csv`, `Options.csv`, `Options_extended.csv`, `Reindex_Rescan.csv`) track RPC/option comparison. Update both base and extended when adding/removing RPCs.

### Completed

- ZERO_COIN + UpdateZero §7: Chain economics and ops in ZERO_COIN.md; maintainer subsidy excerpts in UpdateZero §7.
- UpdateBuild / UpdateTests consolidation: Folded into UpdateZero §8 and §9.
- `run-tests.sh` background jobs: `run_bg` uses `BG_LAST_PID`; child exit codes correct.
- `getchaintips` RPC test: Split-network topology, CHAIN_BOOTSTRAP, branch/rejoin assertions.
- `rescan_import.py` executable: Git index 100755.
- macOS system Rust: `depends/packages/rust.mk` RUST_USE_SYSTEM.
- Zeronode `pConfIndex` null guard: `CheckInputsAndAdd` null-checked.
- Decorative Unicode stripped: Em-dashes, curly quotes, arrows replaced with ASCII in all docs except README.md. Rule added to AGENTS.md.
- `backup/attribution-rewrite-202603201534` branch deleted.
- Tag typos: `v.3.3.1` and `v3.3.12` replaced with `v3.3.1` (pushed to remote).
- Iterator bug (zeronodeman.cpp cleanup loop): erase order corrected, `mapSeenSyncZNB` first.
- `throw new std::runtime_error` removed from all 5 C++ sites.
- Debug `std::cout` leaks: cited paths (`wallet/src/rpc.cpp`, `websockets.cpp`) not present in this tree; only remaining `std::cout` is in test code (`test_paymentdisclosure.cpp`).

---

## Appendix: Identified issues (from zero_errs.txt)

Source: external AI-assisted code audit (Mar 2026), maintainer triage, and subsequent review. Original log in `zero_errs.txt`. Each item below gives the original finding, cited file/lines, actual status, and tracking chain.

### A1. Iterator bug in zeronode cleanup

**Cited:** `src/zeronode/zeronodeman.cpp:323-324`. Two-map erase in wrong order; `mapSeenZeronodeBroadcast.erase(it3++)` before `mapSeenZeronodePing.erase((*it_map).second...)` reads advanced/invalidated iterator. Fires every 60s in `CheckAndRemove` on any broadcast older than ~4.3h. Segfault if last entry; silent wrong-entry erase otherwise. Correct pattern existed 60 lines up (line 263-267).

**Status:** Fixed. Lines 318-326 now erase `mapSeenSyncZNB` first, then `mapSeenZeronodeBroadcast.erase(it3++)`. -> §9 Completed.

### A2. throw new std::runtime_error (5 sites)

**Cited:** `src/transaction_builder.cpp:82`, `src/main.cpp:7477`, + 3 in `src/zcbenchmarks.cpp`. Throws a pointer; all catch handlers catch by reference. If triggered, `std::terminate()`. Inherited from upstream Zcash; same pattern in Horizen at same lines. 3 of 5 in benchmark code (low risk); 2 in real validation paths.

**Status:** Fixed. All 5 sites corrected to `throw std::runtime_error(...)`. -> §9 Completed. -> §3 Engineering policy now mandates `throw`, not `throw new`.

### A3. Floating-point in block subsidy

**Cited:** `src/main.cpp:2113` (`nSubsidy = 10.8 * COIN`), `src/main.cpp:4508` (founders `* 0.075`). Double arithmetic. Works by coincidence on 64-bit for current values, but at halving 7 (~block 5.6M) founders fraction `8437500 * 0.075 = 632812.5` causes miner path (truncates to 632812) and validator path (keeps 632812.5 as double) to disagree. Deterministic consensus failure ~21 years out.

**Status:** Open. Tracked as SUPPLY-01 (total supply discrepancy) and NUM-01 (integer math policy) in §9. Fix: `blockValue * 75 / 1000` for both paths; audit all `double`/`float` in consensus. -> §9 SUPPLY-01, NUM-01.

### A4. Duplicate branch ID (Sapling == Cosmos)

**Cited:** `src/consensus/upgrades.cpp:28-33`. Both use `0x7361707a`. Transactions signed in one era are valid in the other; no replay protection between eras.

**Status:** Open. Tracked as NU-01 in §9. Internal idea, never fully activated. If long-lived UTXOs spent across eras, replay is possible. Evaluate whether unique Cosmos branch ID is needed or whether the upgrade can be formally retired. -> §9 NU-01.

### A5. Debug output leaks transaction data

**Cited:** `wallet/src/rpc.cpp:1281`, `wallet/src/websockets.cpp:698`. Two `std::cout` calls dumping full transaction JSON.

**Status:** False positive. Cited paths do not exist in Zero's source tree. Zero uses `src/wallet/rpcwallet.cpp` (not `wallet/src/rpc.cpp`) and has no `websockets.cpp`. Full `std::cout` audit of `src/` found: `metrics.cpp` (intentional TUI), test code behind `#ifdef` guards, `tinyformat.h` (library infra), `test_paymentdisclosure.cpp` (test only). No release-path stdout leaks exist. -> §9 Completed (false positive documented).

### A6. Null deref in CheckInputsAndAdd

**Cited:** `src/zeronode/zeronode.cpp:615-616`. `chainActive[pMNIndex->nHeight + 14]` returns NULL on short chains; any peer can trigger via znb message.

**Status:** Fixed. Null guard added. Two additional unguarded sites found in audit: `zeronode.cpp:685` (`CZeronodePing` constructor, `Height() - 12`) and `swifttx.cpp:231` (`CreateNewLock`, `Tip()->nHeight`). Both trigger only on chains < 12 blocks. -> §9 chainActive[] audit (expanded with full site table).

### A7. OpenSSL 1.1.1w + Rust 1.32.0

**Cited:** `depends/packages/openssl.mk:2`, `depends/packages/rust.mk:31`. OpenSSL 1.1.1 EOL Sep 2023. Rust 1.32.0 has known CVEs in vendored crates.

**Status:** Open. Tracked in §9 Deferred upgrades. OpenSSL 3.x migration is non-trivial; evaluated across Bitcoin/Zcash/clones. Rust uses system toolchain on macOS/Linux; pinned 1.32.0 only for depends cross-compile. -> §9 Deferred upgrades (Rust pin, OpenSSL).

### A8. Build notes (fetch-params, debug symbols, checksums)

**Cited:** `fetch-params.sh` downloads from `download.z.cash`. Debug symbols `-g` in release. No release checksums/signing.

**Status:**
- **fetch-params:** Open. Tracked as Params archival in §9. Mirror URLs and naming need audit.
- **Chain bootstrap:** Open. Tracked as separate item in §9.
- **Debug symbols:** Open. Tracked in §9 Release build flags. `build-native.sh` forces `CXXFLAGS='-g'`; `release-linux.sh` strips staged binaries.
- **Checksums/signing:** Open. Tracked in §9 Release signing and integrity + macOS developer signing. No procedure exists yet.

### Tracking chain summary

| ID | Description | Status | §9 tracking |
|----|-------------|--------|-------------|
| A1 | Iterator erase order | Fixed | Completed |
| A2 | throw new (5 sites) | Fixed | Completed |
| A3 | Float in subsidy/founders | Open | SUPPLY-01, NUM-01 |
| A4 | Duplicate branch ID | Open | NU-01 |
| A5 | Debug stdout leaks | False positive | Completed |
| A6 | Null deref chainActive | Partial (1 fixed, 2 remaining) | chainActive[] audit |
| A7 | OpenSSL/Rust versions | Open | Deferred upgrades |
| A8a | fetch-params mirrors | Open | Params archival |
| A8b | Chain bootstrap | Open | Chain bootstrap procedure |
| A8c | Debug symbols in release | Open | Release build flags |
| A8d | Checksums/signing | Open | Release signing, macOS signing |
