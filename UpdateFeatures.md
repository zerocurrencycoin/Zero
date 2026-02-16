# UpdateFeatures

Architecture changes, production code fixes, cross-fork analysis, and
design decisions for the Zero node.

## 1. Witness Cache Architecture

### 1.1 Background

Zcash wallet maintains Merkle tree witnesses for each shielded note.
Witnesses track a note's position in the commitment tree and are updated
with each new block. They are required to construct spend proofs.

The Zcash-family forks have diverged significantly in how they manage
witness state.

### 1.2 Upstream Zcash Approach

Zcash uses `IncrementNoteWitnesses`, called once per block from `ChainTip`:

```
void CWallet::IncrementNoteWitnesses(
    const Consensus::Params& consensus,
    const CBlockIndex* pindex,
    const CBlock* pblockIn,
    MerkleFrontiers& frontiers,
    bool performOrchardWalletUpdates)
```

Key properties:
- Incremental: processes one block at a time.
- Receives Merkle tree frontiers as parameters from the caller.
- Never calls `ReadBlockFromDisk` or `pcoinsTip` internally.
- For each commitment in the block, appends to all existing witnesses.
- Creates new witnesses when encountering wallet-owned notes.
- Manages a witness cache bounded by `WITNESS_CACHE_SIZE`.

Complemented by `DecrementNoteWitnesses` for reorgs and
`ClearNoteWitnessCache` for full resets.

Used by: Zcash, Fluxd, Horizen/Zen, Zclassic.

### 1.3 Zero's Custom Approach

In February 2020, cryptoforge replaced `IncrementNoteWitnesses` with two
new functions:

**`VerifyAndSetInitialWitness`**: For each wallet note, validates the
existing witness against the Sapling/Sprout Merkle root at its recorded
height. If validation fails or no witness exists, rebuilds the initial
witness from scratch by reading the note's block from disk.

**`BuildWitnessCache`**: Orchestrator. Calls `VerifyAndSetInitialWitness`
to get a start height, then walks the chain forward block-by-block,
appending commitments to all witnesses. Includes multi-threaded dispatch,
progress UI, periodic disk flushes, and block prefetching.

Key properties:
- Full-chain rebuild: can reconstruct witnesses from any point.
- Reads blocks from disk via `ReadBlockFromDisk`.
- Reads Merkle tree roots via `pcoinsTip->GetSaplingAnchorAt`.
- Multi-threaded witness building via `BuildSingleSaplingWitness`.
- Designed for resilience during IBD on wallets with many notes.

Introduced in commit `bf12a78d4` ("Delete & Witnesses", 2020-02-06) and
cleaned up in `b6d25dd2d` ("Witness rework cleanup", 2020-02-13).

### 1.4 Production Code Fixes

Three null-dereference bugs and one cache-size bug were identified in
`VerifyAndSetInitialWitness`:

| Bug | Location | Trigger | Fix |
|-----|----------|---------|-----|
| `pblockindex->pprev` null deref | Sprout + Sapling tree init | Genesis block (height 0) | Guard: `if (pblockindex->pprev && pcoinsTip)` |
| `pcoinsTip` null deref | Sprout + Sapling anchor lookup | Test environment | Early return: `if (!pcoinsTip && !pblockIn) return` |
| `*item.second.nullifier` on `boost::none` | Sprout + Sapling minimum height | Unscanned notes | Guard: `if (item.second.nullifier)` |
| `nWitnessCacheSize` not reset | `ClearNoteWitnessCache` | Any clear operation | Added `nWitnessCacheSize = 0;` |

Additionally, both `VerifyAndSetInitialWitness` and `BuildWitnessCache`
received a `const CBlock* pblockIn = nullptr` parameter. When provided,
the function uses the caller's block instead of calling `ReadBlockFromDisk`.
This follows the same pattern Zcash uses in `IncrementNoteWitnesses`.
In production the parameter defaults to `nullptr` and behavior is unchanged.

**Files**: `src/wallet/wallet.cpp`, `src/wallet/wallet.h`

### 1.5 Pre-existing Test Incompatibilities

Zero's custom witness functions assume infrastructure that the GTest
harness does not provide:

| Requirement | Available in production | Available in tests |
|-------------|----------------------|-------------------|
| `pcoinsTip` (UTXO/anchor DB) | Yes | No (NULL) |
| `ReadBlockFromDisk` | Yes | No (no block files) |
| `mapBlockIndex` populated | Yes | Partially (manual setup) |
| `chainActive` set | Yes | Partially (manual setup) |

The original tests were written for `IncrementNoteWitnesses` which has
none of these requirements. When Zero replaced `IncrementNoteWitnesses`,
the tests were updated to call `BuildWitnessCache` but the test
infrastructure was not updated to provide the needed state. This caused
latent failures.

Four `CachedWitnesses*` tests and `UpdatedSaplingNoteData` remain
failing. See UpdateTests.md section 4.

### 1.6 Cross-Fork Comparison

| Project | Witness Strategy | Functions | Status |
|---------|-----------------|-----------|--------|
| Zcash | Per-block incremental | `IncrementNoteWitnesses` | Active, maintained |
| Fluxd | Per-block incremental | `IncrementNoteWitnesses` | Active |
| Horizen/Zen | Per-block incremental | `IncrementNoteWitnesses` | Active |
| Zero | Full-chain rebuild | `VerifyAndSetInitialWitness`, `BuildWitnessCache` | Active, bugs fixed |
| HUSH3 | Full-chain rebuild | `VerifyAndSetInitialWitness`, `BuildWitnessCache` | Active, same bugs unfixed |
| Pirate | Rust-backed SaplingWallet | `IncrementSaplingWallet`, `DecrementSaplingWallet` | Active; old functions commented out |

**Origin**: Zero's custom witness code was written by cryptoforge in Feb
2020. HUSH3's repo (shallow clone, Duke, Jul 2025) contains identical
code with the same bugs. Both projects share the same developer. Pirate's
repo (shallow clone, Cryptoforge, Sep 2024) has all three functions
commented out, replaced by a Rust `SaplingWallet` object that maintains
Merkle tree state in Rust with C++ feeding it commitments.

**HUSH3 bugs**: The three null-dereference bugs fixed in Zero
(`pprev`, `pcoinsTip`, `nullifier`) are present and unfixed in HUSH3's
current codebase.

### 1.7 Architectural Assessment

**Strengths of Zero's approach**:
- Can recover witness state from any point in the chain.
- Does not require maintaining cumulative tree state in memory.
- Validates witness correctness against on-chain Merkle roots.

**Weaknesses**:
- Depends on `pcoinsTip` and `ReadBlockFromDisk`, making it untestable
  without full chain infrastructure.
- Multi-threaded `BuildSingleSaplingWitness` adds complexity with raw
  `boost::thread` management.
- `ReadBlockFromDisk` calls inside witness building duplicate I/O that
  `ChainTip` already performed.
- Main while-loop in `BuildWitnessCache` has unguarded `pprev` and
  `pcoinsTip` accesses (safe in production, fragile in principle).

**Options**:
1. **Keep current code, fix bugs** (done). Minimum change.
2. **Restore `IncrementNoteWitnesses` as secondary path**. Enables
   tests, provides fallback, reduces upstream divergence. Medium effort.
3. **Adopt Pirate's Rust SaplingWallet approach**. Forward-looking but
   major architectural change.
4. **Revert to upstream `IncrementNoteWitnesses` entirely**. Simplest
   maintenance path but discards performance work for IBD scenarios.

Current decision: option 1 (short-term), evaluate option 2 (medium-term).

## 2. Equihash State API

Zcash v6.x migrated `eh_HashState` from a libsodium C typedef to a
Rust-backed CXX bridge wrapper.

| API | Type | Signature | Used by |
|-----|------|-----------|---------|
| Old (C) | `crypto_generichash_blake2b_state` | `int InitialiseState(eh_HashState& base_state)` | Zero, Horizen, Pirate, Fluxd, Zclassic, HUSH |
| New (Rust) | `struct { rust::Box<blake2b::State> inner; }` | `eh_HashState InitialiseState()` | Zcash v6.11.0 only |

The new API is part of Zcash's progressive migration of crypto primitives
to Rust via CXX interop. No other fork has adopted it. Adopting it would
require the full `rustcxx` build infrastructure and updated `librustzcash`.

**Decision**: Stay on old C API. Functionally equivalent. Used by every
other fork.

## 3. Branding

Incomplete rebranding from original Zcash fork. Runtime-facing code
mostly says "ZERO" but autotools config, copyright headers, and some test
strings still say "Zcash" or "Bitcoin". Not a functional issue unless it
causes confusion in user-facing output (RPC help, logs, deprecation
warnings). Low priority; address opportunistically when touching affected
files.

## 4. Library Dependencies with Feature Impact

Some library upgrades or removals have implications beyond build
configuration. These are tracked here for architectural awareness;
build-level details are in UpdateBuild.md.

### 4.1 BerkeleyDB and Wallet Compatibility

BDB version determines wallet file format and storage behavior. All
Zcash-family projects use BDB 6.2.x (AGPLv3). Wallet files created
with 6.2.23 are compatible with 6.2.32 (same on-disk format). The
BDB mutex fix on ARM64 directly affects wallet reliability at runtime.

The BDB 6.2.32 upgrade may also resolve the `WriteCryptedSaplingZkeyDirectToDb`
test hang caused by BDB mutex/atomic issues. See UpdateBuild.md section 6.1.

Bitcoin Core has migrated entirely from BDB to SQLite-backed descriptor
wallets. No Zcash-family project has followed this path.
See UpdateBuild.md section 7.1.

### 4.2 OpenSSL and TLS

Zero uses OpenSSL for RPC TLS and some legacy crypto paths. Zcash and
Bitcoin Core have removed OpenSSL entirely, using libsodium and bundled
libsecp256k1 instead. The decision to keep, upgrade, or remove OpenSSL
affects RPC security, the cryptographic dependency surface, and
compatibility with deployment environments that require TLS.

Current version (1.1.1w) is EOL. Options range from staying on 1.1.1w,
migrating to 3.5.x LTS, or removing OpenSSL entirely.
See UpdateBuild.md section 7.4.

## 5. Identified Requirements

### 5.1 Linux and Windows Validation

All production code changes (wallet.cpp, wallet.h, equihash.cpp) must be
validated on Linux and Windows before merge. The changes are defensive
(null guards with unchanged production paths) but regression testing is
required.

### 5.2 Witness Test Coverage

The manual witness building pattern used in three tests should be
extracted to a shared helper. The `CreateValidBlock` helper needs
consistent teardown. See UpdateTests.md section 5.

### 5.3 Documentation

Process for the Zero project should include:
- A changelog or release notes capturing what changed and why.
- Build instructions per platform verified against clean environments.
- Test execution procedures with expected results and known exclusions.
