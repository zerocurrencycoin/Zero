# Zero Nodes -- zeronode operator guide

## 1. Purpose and role

**Purpose:** Run a **zeronode** on mainnet or testnet -- collateral, config, RPC, sporks, and what the node does on a deep reorg.

**Include:** Operator setup, spork effects, coinbase order summary, P2P/discovery, operator-visible reorg policy.

**Exclude:** `CZeronodeWalletInterface` and `--disable-wallet` (**`ZeroNodeDev.md`**); TNT execution catalog (**`UpdateZero.md`** section **3.5**); ZND anchors (**`ZeroNodeDev.md`** section **4**); test phases (**`ZeroNodeDev.md`** section **5**); file map (**`TENTZero.md`**); emission tables (**`ZERO_COIN.md`**); family reorg compare (**`~/Work/ZK/ZKs/Comparison.md`** section **14.5**); insight/explorer flags (**`ZeroStruct.md`**).

Developer documents in **UpdateZero.md** section **1**. **Developers:** **`ZeroNodeDev.md`**.

---

## 2. What a zeronode is

Zero's zeronode layer is a renamed port of frozen TENT masternode code. File map: **`TENTZero.md`**.

- **Collateral:** 10,000 ZER locked UTXO (exact amount)
- **Payment:** 20% -> 40% of block subsidy by 800k tiers, spork-gated
- **Services:** SwiftTX (`SPORK_2` / `SPORK_3` **on** mainnet since 1558907000; do not strip -- **DEF-06**), budget/superblocks (those sporks remain off), P2P extensions

Code: **`src/zeronode/`**.

---

## 3. Coinbase order

1. `GetBlockSubsidy(height)`
2. Founders **7.5%** (mainnet heights 412300-7999999)
3. Zeronode payee (`GetZeronodePayment` or budget)
4. Miner + fees

Amounts and `contrib/stats/` commands: **`ZERO_COIN.md`**.

---

## 4. Sporks

Unsigned default for these IDs is **off** (timestamp `4070908800`). Mainnet uses signed sporks. Regtest tests that need payees must activate the relevant sporks with `createsporkkeys` / `spork`.

| Spork | Effect |
|-------|--------|
| `SPORK_7_ZERONODE_PAYMENT_ENABLED` | Master zeronode pay switch |
| `SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED` | Tier schedule vs 100000 zat fixed |
| `SPORK_8_ZERONODE_PAYMENT_ENFORCEMENT` | Reject blocks that fail payee checks |
| `SPORK_13_ENABLE_SUPERBLOCKS` | Budget payee path |
| `SPORK_2_SWIFTTX` | SwiftTX instant-lock (mainnet **on**) |
| `SPORK_3_SWIFTTX_BLOCK_FILTERING` | SwiftTX in blocks (mainnet **on**) |

---

## 5. Operator setup

```bash
./zcutil/fetch-params.sh
./src/zerod -daemon
./src/zero-cli zeronode genkey
# zeronode.conf: alias MN1 <ip>:23801 <privkey> <txid> <vout>
./src/zero-cli zeronode startalias MN1
```

**Ports:** mainnet P2P **23801**, RPC **23811**. **Datadir:** [README datadir table](README.md#data-directory-zeroconf-wallet-chain).

**Wallet-disabled build:** stub interface -- **`ZeroNodeDev.md`**.

---

## 6. Deep reorg

Settled policy: **do not apply** a reorg or unintended rewind deeper than **99** blocks (`MAX_REORG_LENGTH = 100 - 1` in `main.h`). Coinbase **maturity** is **720** (when a coinbase UTXO may be spent). Those numbers are not interchangeable.

If a most-work fork would disconnect **more than 99** blocks, this node logs, shows a modal, and **`StartShutdown()`**. The fork is **not** connected. The same bound applies to an unintended rewind at startup.

A reorg of **100--719** blocks therefore takes this process **off relay** while collateral can still be immature. That is accepted operator behavior, not a pending cap change. Do not raise 99 toward 720 (witness cache is `WITNESS_CACHE_SIZE = MAX_REORG_LENGTH + 1` = 100 slots). Do not copy TENT unbounded follow.

Family compare: **`~/Work/ZK/ZKs/Comparison.md`** section **14.5**. Catalog IDs **TNT-02** / **TNT-03**: **`UpdateZero.md`** section **3.5.1** (keep 99; no scheduled policy change).

---

## 7. P2P

**Discovery:** ten DNS seeds (`seed0`..`seed9`.zerocurrency.io); `peers.dat` via `CAddrDB`. No fixed IP seeds in `chainparamsseeds.h` today.

**Zeronode extensions:** `spork`, `zn winner`, `zn announce`, `zn ping`, budget messages, SwiftTX locks. Dispatch: `src/main.cpp` else-branch after `notfound` -> `znodeman`, `budget`, `zeronodePayments`, SwiftTX, spork, `zeronodeSync`. Handled commands do not emit `Unknown command` (**TNT-01** done in tree).

---

## 8. Testing

Regtest runner: **`TEST_ZERO.md`**. Zeronode phases A-F: **`ZeroNodeDev.md`** section **5**. Live coinbase checks: **`ZERO_COIN.md`** (`chain_stats.py`).

---

## 9. References

| Topic | Doc |
|-------|-----|
| Wallet interface / tests | **`ZeroNodeDev.md`** |
| File map | **`TENTZero.md`** |
| TNT catalog | **`UpdateZero.md`** section **3.5** |
| Economics | **`ZERO_COIN.md`** |
| Reorg family | **`~/Work/ZK/ZKs/Comparison.md`** section **14.5** |
| CVE posture | **`ZcashFixes.md`** |
| Maintainer map | **`UpdateZero.md`** section **1** |
