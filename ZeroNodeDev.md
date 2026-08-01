# ZeroNodeDev -- zeronode wallet interface
*Project Planning*

## 1. Purpose and role

**Purpose:** **Source-level** zeronode layer -- wallet abstraction, TENT lineage, **ZND anchors**, functional test roadmap.

**Include:** `CZeronodeWalletInterface` / stub; library split; section **9** ZND table with diff anchors; test phases A-F.

**Exclude:** Operator workflow (**`ZeroNodes.md`**); TNT execution order (**`UpdateZero.md`** section **3.5**); general zerod architecture (**`ZeroStruct.md`**).

Developer documents in **UpdateZero.md** section **1**, **Documentation map**. **Operators:** **`ZeroNodes.md`**.

**Status:** Complete (June 2025). Strategy pattern: `CZeronodeWalletInterface` + `CZeronodeWalletStub` (`--disable-wallet`).

---

## 2. Problem, Solution, Approach

### Problem

Zeronode code was tightly coupled to the wallet library. Server code directly accessed `pwalletMain` and wallet types, causing:

- **Circular linking** -- Server <-> wallet dependencies; linker errors
- **Wallet-required builds** -- No clean `--disable-wallet` path
- **Scattered `#ifdef ENABLE_WALLET`** -- Brittle guards around direct access
- **Header pollution** -- `wallet.h`, `CWallet`, `CReserveKey` pulled into server

### Solution

1. **Interface abstraction** -- `IZeronodeWalletInterface` with 13 methods; server calls `g_zeronodeWallet->Method()` instead of `pwalletMain->Method()`.
2. **Two implementations** -- Real (forwards to `pwalletMain`) and stub (safe no-ops); selected at init.
3. **Library restructuring** -- `zeronodeconfig.cpp`, `swifttx.cpp`, `activezeronode.cpp` moved to server lib; only `zeronode-wallet-interface.cpp` in wallet lib.
4. **Type erasure** -- `CommitTransaction(..., void* reservekey, ...)` avoids `wallet.h` in headers; call sites construct `CReserveKey(pwalletMain)` locally when needed.

### How It Works

- `init.cpp` instantiates real or stub and assigns to `g_zeronodeWallet`.
- Paths check `g_zeronodeWallet->IsAvailable()` before wallet ops.
- Stub returns locked=true, balance=0, false for key/tx ops.

---

## 3. Interface and Usage

### Interface -- 13 methods

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

## 4. Known Mismatches

**Minimal direct wallet access:** Almost all use goes through `g_zeronodeWallet`. Two intentional exceptions:

| Location | Issue | Notes |
|----------|-------|-------|
| `budget.cpp:201`, `rpc/zeronode-budget.cpp:141` | `CReserveKey reservekey(pwalletMain)` | Interface takes `void*`; call sites construct reserve key locally. Type erasure by design. |
| `swifttx.cpp:339` | `if (pwalletMain)` before `g_zeronodeWallet` | Redundant; see below. |

### SwiftTX and Redundancy

SwiftTX flow: (1) client broadcasts `"ix"`; (2) zeronodes vote; (3) lock completes at `SWIFTTX_SIGNATURES_REQUIRED`. `ProcessConsensusVote` runs on vote arrival. Wallet-originated txs track "signatures received" via `IncrementRequestCount` for UI propagation status.

At line 339, `if (pwalletMain)` is redundant: `GetRequestCount` returns 0 when `pwalletMain` is null; `IncrementRequestCount` guards internally. Replace with `if (g_zeronodeWallet && g_zeronodeWallet->GetRequestCount(ctx.txHash) > 0) { g_zeronodeWallet->IncrementRequestCount(ctx.txHash); }`.

---

## 5. Test Types and Approaches

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
- Zeronode RPCs: partial automated coverage (**`rpc_zeronode_tests`**, **`rpc_zeronode_budget_tests`**). Logic and integration gaps remain for budget flow, sync edge cases, and multi-node scenarios.
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

## 6. Files Modified

| File | Change |
|------|--------|
| `zeronode-wallet-interface.h` | Created -- interface definition |
| `zeronode-wallet-interface.cpp` | Created -- real and stub impls |
| `Makefile.am` | Library restructuring, linking order |
| `Makefile.test.include` | Test linking deps |
| `rpc/register.h` | Conditional RPC |
| `init.cpp` | Wallet init guards |
| `zeronode.cpp`, `swifttx.cpp`, `rpc/zeronode.cpp`, `rpc/blockchain.cpp`, `budget.cpp` | Interface migration |

---

## 7. Future Enhancement

**Phase 3 (optional):** Replace `bool` returns with `ZeronodeWalletResult` (error code, message, context). Design complete; not implemented.

---

## 8. Lessons Learned

- Strategy pattern decouples while preserving behavior.
- `void*` for `CReserveKey` keeps headers wallet-free.
- `IsAvailable()` guard pattern prevents null errors.
- Use `GetCS()` for multi-op sequences.
- Stub returns secure defaults (locked, zero balance).

---

## 9. TENT lineage and upstream candidates

Zero `src/zeronode/*` maps from TENT `src/masternode/*` (**`ZeroNodes.md`** section **2**). TENT uses direct **`pwalletMain`**; Zero uses **`CZeronodeWalletInterface`** (this file, sections **2**--**8**).

**TNT execution order:** **`UpdateZero.md`** section **3.5** only. This section owns **ZND anchors**.

### ZND anchors

**ZND-01..08** are stable labels (**Z**ero**N**ode **D**ev) for TENT-vs-Zero zeronode topics. Each row ties **behavior** to **source paths** and a port/reject recommendation. Cite **ZND IDs only in ZeroNode* files** (`ZeroNodes.md`, this file). **`UpdateZero.md`** section **3.5** uses **TNT** (**T**ENT) IDs for execution priority, not ZND IDs in prose.

**Diff anchor (payments):** `TENT/src/masternode-payments.cpp` vs `Zero400/src/zeronode/payments.cpp` (rename, treasury removal, Zero spork names).

### Port / reject table

| ID | TENT behavior | Zero today | Recommendation |
|----|---------------|------------|----------------|
| **ZND-01** | P2P: no spurious `Unknown command` after handled zeronode messages | Still logs (`TODO.md`, `main.cpp` ~7027) | **Port** -- drop trailing log or log only unhandled commands |
| **ZND-02** | Testnet min-difficulty after height 13000 (`pow.cpp`) | `nPowAllowMinDifficultyBlocksAfterHeight = none` | **Consensus decision** -- only if operators want easier public testnet mining |
| **ZND-03** | Equihash epoch fork (mainnet 192,7 vs testnet 144,5) | 192,7 on testnet | **Document** -- do not port without explicit NU |
| **ZND-04** | LWMA3 difficulty after DIFA height | Legacy LWMA path | Evaluate if testnet instability warrants port |
| **ZND-05** | Treasury coinbase + `GetTreasuryRewardScriptAtHeight` | **Removed** | **Reject** -- not Zero tokenomics |
| **ZND-06** | Founders schedule by upgrade (5% / 7.5% / 15%) | Fixed **7.5%** after fee-start | **Reject** |
| **ZND-07** | Masternode integration tests | None in either tree | **Implement** on Zero regtest first |
| **ZND-08** | External masternode-setup docs | Obsolete scripts in the wild | **Replace** with **`ZeroNodes.md`** / BUILD_ZERO operator section |

### Functional test roadmap (from DOC-02)

| Phase | Test | Pass criteria |
|-------|------|---------------|
| **A** | RPC argument validation | Extend `rpc_zeronode_tests`, `rpc_zeronode_budget_tests` |
| **B** | Regtest coinbase split | Founders 7.5%, zeronode vout when spork on (height > 5000) |
| **C** | Regtest 2-node zeronode | `startalias`, payment in coinbase within N blocks |
| **D** | Reorg / `GetZeronodeInputAge` | `invalidateblock` steps; automate when harness allows |
| **E** | Mock wallet | Test double for `CZeronodeWalletInterface` |
| **F** | Mainnet decode regression | optional CI fixtures (see **`ZERO_COIN.md`**) |

Priority: A -> B -> C. See **`UpdateZero.md`** DOC-02 for doc deliverables.

