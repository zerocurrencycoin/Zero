# Zeronode Wallet Interface

Wallet abstraction for Zero's zeronode (masternode) functionality. Addresses circular linking, enables wallet-optional builds, and decouples server from wallet.

**Status:** Complete (June 2025). **Architecture:** Strategy pattern — `CZeronodeWalletInterface` (real) and `CZeronodeWalletStub` (wallet-disabled).

---

## 1. Problem, Solution, Approach

### Problem

Zeronode code was tightly coupled to the wallet library. Server code directly accessed `pwalletMain` and wallet types, causing:

- **Circular linking** — Server ↔ wallet dependencies; linker errors
- **Wallet-required builds** — No clean `--disable-wallet` path
- **Scattered `#ifdef ENABLE_WALLET`** — Brittle guards around direct access
- **Header pollution** — `wallet.h`, `CWallet`, `CReserveKey` pulled into server

### Solution

1. **Interface abstraction** — `IZeronodeWalletInterface` with 13 methods; server calls `g_zeronodeWallet->Method()` instead of `pwalletMain->Method()`.
2. **Two implementations** — Real (forwards to `pwalletMain`) and stub (safe no-ops); selected at init.
3. **Library restructuring** — `zeronodeconfig.cpp`, `swifttx.cpp`, `activezeronode.cpp` moved to server lib; only `zeronode-wallet-interface.cpp` in wallet lib.
4. **Type erasure** — `CommitTransaction(..., void* reservekey, ...)` avoids `wallet.h` in headers; call sites construct `CReserveKey(pwalletMain)` locally when needed.

### How It Works

- `init.cpp` instantiates real or stub and assigns to `g_zeronodeWallet`.
- Paths check `g_zeronodeWallet->IsAvailable()` before wallet ops.
- Stub returns locked=true, balance=0, false for key/tx ops.

---

## 2. Interface and Usage

### Interface (13 methods)

| Category | Methods |
|----------|---------|
| State | `IsLocked()`, `GetBalance()`, `IsAvailable()`, `NullifierCount()` |
| Keys | `GetKey()`, `GetZeronodeVinAndKeys()` |
| Coins | `LockCoin()`, `UnlockCoin()`, `AvailableCoins()` |
| Transactions | `GetBudgetSystemCollateralTX()`, `CommitTransaction()` |
| Control | `Lock()`, `UpdatedTransaction()`, `IncrementRequestCount()`, `GetRequestCount()` |
| Thread safety | `GetCS()` |

### Usage Patterns

```cpp
// Availability check
if (!g_zeronodeWallet || !g_zeronodeWallet->IsAvailable()) return false;

// Thread-safe sequence
LOCK(g_zeronodeWallet->GetCS());
g_zeronodeWallet->LockCoin(output);
```

### Library Layout

**Server (`libbitcoin_server.a`):** activezeronode, budget, payments, zeronode-sync, zerodeman, spork, obfuscation, swifttx, zeronode, zeronodeconfig.

**Wallet (`libbitcoin_wallet.a`):** zeronode-wallet-interface.cpp only.

---

## 3. Known Mismatches

**Minimal direct wallet access:** Almost all use goes through `g_zeronodeWallet`. Two intentional exceptions:

| Location | Issue | Notes |
|----------|-------|-------|
| `budget.cpp:201`, `rpc/zeronode-budget.cpp:141` | `CReserveKey reservekey(pwalletMain)` | Interface takes `void*`; call sites construct reserve key locally. Type erasure by design. |
| `swifttx.cpp:339` | `if (pwalletMain)` before `g_zeronodeWallet` | Redundant; see below. |

### SwiftTX and Redundancy

SwiftTX flow: (1) client broadcasts `"ix"`; (2) zeronodes vote; (3) lock completes at `SWIFTTX_SIGNATURES_REQUIRED`. `ProcessConsensusVote` runs on vote arrival. Wallet-originated txs track "signatures received" via `IncrementRequestCount` for UI propagation status.

At line 339, `if (pwalletMain)` is redundant: `GetRequestCount` returns 0 when `pwalletMain` is null; `IncrementRequestCount` guards internally. Replace with `if (g_zeronodeWallet && g_zeronodeWallet->GetRequestCount(ctx.txHash) > 0) { g_zeronodeWallet->IncrementRequestCount(ctx.txHash); }`.

---

## 4. Test Types and Approaches

### 4.1 Build Tests

| Test | Command | Pass criterion |
|------|---------|----------------|
| Wallet-enabled | `make zerod zero-cli` | Both link and run |
| Wallet-disabled | `./configure --disable-wallet && make zerod` | Links; no wallet symbols |
| Init log | `./zerod -testnet` | Log shows "Initialized zeronode wallet interface" |

### 4.2 Unit-Level Testing

**Stub behavior:** In wallet-disabled build, all interface calls must be safe. Stub returns: `IsLocked()=true`, `GetBalance()=0`, `IsAvailable()=false`, `GetKey()`/`GetZeronodeVinAndKeys()`/`CommitTransaction()`=false. No crashes on null.

**Mock injection:** The interface enables replacing `g_zeronodeWallet` with a test double. A mock can record calls, force specific return values, or simulate failures. No existing unit tests use this yet; the design supports it.

**Isolation:** Server code that uses only `g_zeronodeWallet` can be tested without a real wallet. Requires building a minimal harness that provides chain state and mempool.

### 4.3 Integration Tests

| Path | Trigger | Verification |
|------|---------|---------------|
| Zeronode start | `zero-cli zeronode start` | Uses `GetZeronodeVinAndKeys`, `LockCoin`, `AvailableCoins` |
| Budget proposal | `zero-cli submitbudget ...` | Uses `GetBudgetSystemCollateralTX`, `CommitTransaction` |
| SwiftTX | Send instant tx (`"ix"`) from wallet | `IncrementRequestCount`, `UpdatedTransaction` exercised; lock completes |
| RPC lock | `zero-cli zeronode ...` (wallet ops) | Uses `Lock()` |

**SwiftTX verification:** Enable `-debug=swiftx`; send ix from wallet; check logs for `ProcessConsensusVote`, lock completion, and request-count updates.

### 4.4 Regression and Sanity

- **Redundancy fix:** After replacing `if (pwalletMain)` with interface-only guard, SwiftTX flow must behave identically.
- **Thread safety:** Multi-threaded zeronode ops (e.g., concurrent RPC + sync) should not deadlock; `GetCS()` must serialize wallet access.
- **Memory:** No leaks under repeated zeronode start/stop or budget proposal cycles.

### 4.5 Coverage Gaps

- No dedicated GTest or Boost tests for the interface.
- Zeronode RPCs: partial automated coverage (rpc_zeronode_tests, rpc_zeronode_budget_tests). Logic and integration coverage gaps are tracked in the maintainer test plan, not in this note.
- SwiftTX path is exercised manually or via full-node sync, not isolated.

### 4.6 Test Commands Summary

```bash
# Build
make clean && make zerod zero-cli
./configure --disable-wallet && make zerod

# Manual integration
./zerod -testnet -debug=zeronode,swiftx
zero-cli zeronode start
zero-cli submitbudget "name" "url" 1 100 "addr" 100 "fee-tx"
```

---

## 5. Files Modified

| File | Change |
|------|--------|
| `zeronode-wallet-interface.h` | Created — interface definition |
| `zeronode-wallet-interface.cpp` | Created — real and stub impls |
| `Makefile.am` | Library restructuring, linking order |
| `Makefile.test.include` | Test linking deps |
| `rpc/register.h` | Conditional RPC |
| `init.cpp` | Wallet init guards |
| `zeronode.cpp`, `swifttx.cpp`, `rpc/zeronode.cpp`, `rpc/blockchain.cpp`, `budget.cpp` | Interface migration |

---

## 6. Future Enhancement

**Phase 3 (optional):** Replace `bool` returns with `ZeronodeWalletResult` (error code, message, context). Design complete; not implemented.

---

## 7. Lessons Learned

- Strategy pattern decouples while preserving behavior.
- `void*` for `CReserveKey` keeps headers wallet-free.
- `IsAvailable()` guard pattern prevents null errors.
- Use `GetCS()` for multi-op sequences.
- Stub returns secure defaults (locked, zero balance).
