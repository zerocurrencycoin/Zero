# ZeroNodeDev -- zeronode source

## 1. Purpose and role

**Purpose:** Source-level zeronode layer -- wallet abstraction, remaining call-site mismatches, **ZND** path anchors, and **TNT-12** test phases.

**Include:** `CZeronodeWalletInterface` / stub; library split; SwiftTX / `CReserveKey` leftovers; ZND-to-TNT crosswalk with source paths; test phases A-F (complexity, coverage, impact, sequence).

**Exclude:** Operator workflow and operator-visible reorg (**`ZeroNodes.md`**); TNT execution order and reorg product decision (**`UpdateZero.md`** sections **3.5**, **3.5.1**); file map (**`TENTZero.md`**); emission (**`ZERO_COIN.md`**); family reorg taxonomy (**`Comparison.md`** section **14.5**).

**Operators:** **`ZeroNodes.md`**. Cite **ZND-NN** only in ZeroNode files. Cite **TNT-NN** for scheduling in **`UpdateZero.md`**.

Wallet-boundary work is **settled**: `CZeronodeWalletInterface` plus `CZeronodeWalletStub` (`--disable-wallet`).

---

## 2. Wallet interface

Zeronode code used to call `pwalletMain` from the server library (circular link, no `--disable-wallet`, `#ifdef ENABLE_WALLET` scatter, `wallet.h` in headers).

`g_zeronodeWallet` is a 13-method interface. `init.cpp` installs the real implementation or the stub. Callers check `IsAvailable()` before wallet ops. Stub: locked, balance 0, key/tx ops false.

| Category | Methods |
|----------|---------|
| State | `IsLocked()`, `GetBalance()`, `IsAvailable()`, `NullifierCount()` |
| Keys | `GetKey()`, `GetZeronodeVinAndKeys()` |
| Coins | `LockCoin()`, `UnlockCoin()`, `AvailableCoins()` |
| Transactions | `GetBudgetSystemCollateralTX()`, `CommitTransaction()` |
| Control | `Lock()`, `UpdatedTransaction()`, `IncrementRequestCount()`, `GetRequestCount()` |
| Thread safety | `GetCS()` |

```cpp
if (!g_zeronodeWallet || !g_zeronodeWallet->IsAvailable()) return false;
LOCK(g_zeronodeWallet->GetCS());
g_zeronodeWallet->LockCoin(output);
```

**Server (`libbitcoin_server.a`):** activezeronode, budget, payments, zeronode-sync, zerodeman, spork, obfuscation, swifttx, zeronode, zeronodeconfig.

**Wallet (`libbitcoin_wallet.a`):** `zeronode-wallet-interface.cpp` only.

`CommitTransaction(..., void* reservekey, ...)` keeps `CReserveKey` out of server headers. Optional later: `ZeronodeWalletResult` instead of `bool` (not implemented).

---

## 3. Remaining mismatches

Not TENT ports. Local cleanup.

**`CReserveKey reservekey(pwalletMain)`** at `budget.cpp` and `rpc/zeronode-budget.cpp`: by design. The interface takes `void*`; those call sites construct the reserve key next to the wallet.

**`swifttx.cpp` `ProcessConsensusVote`:** `if (pwalletMain)` wraps an already-guarded `g_zeronodeWallet->GetRequestCount` / `IncrementRequestCount`. The outer check is redundant. Replace with the interface-only guard if SwiftTX stays. **DEF-06:** do not strip SwiftTX; `SPORK_2` / `SPORK_3` are **on** mainnet.

**Build / stub checks:** `make zerod zero-cli`; `./configure --disable-wallet && make zerod`; log line `Initialized zeronode wallet interface`. No dedicated GTest for the interface yet (phase **E**).

---

## 4. ZND anchors

**ZND-01..08** are stable labels for TENT-vs-Zero **source paths**. Port/reject **decisions and schedule** live in **`UpdateZero.md`** section **3.5** (**TNT-NN**). Do not copy TNT recommendation text here.

File map: **`TENTZero.md`**. Payments files: `TENT/src/masternode-payments.cpp` vs `src/zeronode/payments.cpp`.

| ZND | TNT | Topic | Zero path / note |
|-----|-----|-------|------------------|
| **ZND-01** | **TNT-01** | P2P else-branch after zeronode handlers | `main.cpp` ~7070: handlers only, no `Unknown command`. **Done** in tree. |
| **ZND-02** | **TNT-07** | Testnet min-difficulty after h13000 | Zero `nPowAllowMinDifficultyBlocksAfterHeight = none` |
| **ZND-03** | **TNT-08** | Equihash testnet 144,5 | Zero 192,7 on both nets |
| **ZND-04** | **TNT-09** | LWMA3 after DIFA | Zero Zcash 17-block window |
| **ZND-05** | **TNT-10** | Treasury 4th coinbase vout | **Removed** |
| **ZND-06** | **TNT-11** | Founders % by upgrade | Zero fixed 7.5% after fee-start |
| **ZND-07** | **TNT-12** | Integration tests | Zero phases A-C in tree; TENT has none |
| **ZND-08** | **TNT-13** | External MN setup scripts | Operator text: **`ZeroNodes.md`** |

Reorg policy is **not** a ZND row: chain validation, not `src/zeronode/`. **TNT-02** / **TNT-03** in **`UpdateZero.md`** section **3.5.1**; operator effect in **`ZeroNodes.md`** section **6**.

---

## 5. TNT-12 test phases

TENT has no masternode integration tests to cherry-pick. Implement on Zero. Catalog vs other TNT work: **`UpdateZero.md`** section **3.5**. **TST-03** is the Boost arg-validation slice of phase **A** (`TEST_ZERO.md`).

**A:** Boost `rpc_zeronode_tests` / `rpc_zeronode_budget_tests` -- extra-arg throws, `zeronodestats` keys, `createsporkkeys`, injected `GetZeronodePayment`. In `--strict`.

**B:** `qa/rpc-tests/zeronode_coinbase.py` -- sporks off: `zeronodestats` payment 0; founders window has no zn vout; `createsporkkeys` works; unsigned `spork` update returns `failure`. Amount math with sporks **on** is the Boost injection case (regtest has no published `-sporkkey`).

**C:** `qa/rpc-tests/zeronode_startalias.py` -- two nodes, wait `znsync` `RequestedZeronodeAssets == 999`, `zeronode.conf` load, `startalias` without a valid vin. Full success + payee needs an exact **10000 ZER** UTXO; regtest halves every 150 blocks so miner emission totals ~3000 ZER. That success path needs a regtest collateral amount or a premine, not more `generate`. B and C are **Tier B**.

Regtest sporks default **off**. Collateral must be **exactly** 10,000 ZER. Coinbase maturity is **720**.

| Phase | What | Complexity | Coverage | Impact | Sequence |
|-------|------|------------|----------|--------|----------|
| **A** | Boost RPC arg tests; `zeronodestats` + budget subcmds; injected `GetZeronodePayment` (**TST-03**) | **S** -- no chain, no peers | Dispatch / arity / JSON keys / spork amount math. Does not start a zeronode. | Stops zerowallet/Insight client surprises on bad args. In `--strict`. | **First.** Independent of TNT-02. |
| **B** | Regtest coinbase: founders 7.5% in the fee-start window; zn vout absent while SPORK_7 off | **S-M** -- one node, `generate`, decode coinbase | Consensus split vs `GetFoundersRewardAmount` / `GetZeronodePayment`. Not winner-vote or `startalias`. | Catches subsidy/founders/zn amount bugs before 2-node work. Align with `founders_window.py`. | **After A.** Do not assume TENT "height > 5000"; Zero gates pay on sporks. |
| **C** | Two-node `znsync` + `startalias` without a 10000 vin; full success is blocked on regtest emission | **M** -- peers, conf restart, list sync | Sync-to-999, conf parse, Create fail. Not a payee. | Catches znsync/conf/startalias wiring. | **After A and B.** Not gated on TNT-02. |
| **D** | `invalidateblock` / input age; excessive-reorg is already `reorg_limit.py` (exit at >99) | **M** once C exists | `GetZeronodeInputAge`, collateral after disconnect | Prevents a zeronode-only surprise on applied reorgs | **Applied** reorgs after C. Excessive (>99) is current exit; not waiting on TNT-02. |
| **E** | Mock `IZeronodeWalletInterface` GTest | **S** | Ping/payment/lock without BDB | Fast boundary regression; does not replace C | In tree: `test_zeronode_wallet_mock.cpp`. |
| **F** | Mainnet coinbase decode / zn-amount scan | **S** given a synced node | Amounts vs model, not winner scriptPubKey (needs `txindex` + payee list) | Evidence for **TNT-04**. Watch OVERPAY `LogPrintf`. | Anytime a synced node exists. `contrib/stats/chain_stats.py --zn-pay START COUNT` (**`ZERO_COIN.md`**). |

**Order:** A -> B -> C. Run **F** when RPC is available (does not wait on C). **D** applied-reorg after C. **E** can overlap C.

Do not copy TENT as the test oracle: Zero has no treasury vout, different founders rule, different Equihash on testnet, and `==` payee amounts until TNT-04 says otherwise.

### Phase E

Replace `g_zeronodeWallet` with a test double of `CZeronodeWalletInterface`. Record calls (`LockCoin`, `GetZeronodeVinAndKeys`, `CommitTransaction`, request counts) and force returns. No BDB. Covers ping, payment, and lock paths that today only run with a real wallet.

Does not replace phase **C** (broadcast, list sync, `startalias`). `--disable-wallet` already installs `CZeronodeWalletStub` (locked, balance 0, key/tx ops false); E is a recording mock for GTest, not that stub. `CReserveKey(pwalletMain)` at budget RPC sites stays: the interface takes `void*` on purpose.

GTest: `src/gtest/test_zeronode_wallet_mock.cpp` (`ZeronodeWalletMock.*`). Run: `./src/zero-gtest --gtest_filter=ZeronodeWalletMock.*`. Records `LockCoin` / `UnlockCoin` / `GetZeronodeVinAndKeys` / request counts; forces vin success; drives `ManageStatus` (unavailable / locked / zero balance) and `SelectCoinsZeronode` without BDB. Not the `--disable-wallet` stub.
