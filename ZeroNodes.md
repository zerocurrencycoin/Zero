# Zero Nodes -- zeronode operator guide

## 1. Purpose and role

**Purpose:** Run a **zeronode** on mainnet or testnet -- collateral, config, RPC, sporks, and pointers to economics docs.

**Include:** Operator setup, spork effects, coinbase order summary, P2P/discovery, testing pointers.

**Exclude:** `CZeronodeWalletInterface` and `--disable-wallet` (**`ZeroNodeDev.md`**); TNT execution (**`UpdateZero.md`** section **3.5**); port/reject anchors (**`ZeroNodeDev.md`** section **9**); insight/explorer flags (**`Runtime.md`**).

Developer documents in **UpdateZero.md** section **1**, **Documentation map**. **Developers:** **`ZeroNodeDev.md`**.

Last updated: Jun 2026.

---

## 2. TENT relationship

Zero's zeronode layer is a port of **TENT** (`ZKs/TENT`) masternode code into `src/zeronode/` (wire commands renamed `mn*` -> `zn*`). TENT kept a treasury coinbase output and direct `pwalletMain` access; Zero removed the treasury and added **`CZeronodeWalletInterface`**. File map: **`TENTZero.md`**. Port/reject detail: **`ZeroNodeDev.md`** section **9**; execution order: **`UpdateZero.md`** section **3.5**.

---

## 3. What a zeronode is

- **Collateral:** 10,000 ZER locked UTXO
- **Payment:** 20% -> 40% of block subsidy by 800k tiers (spork-gated)
- **Services:** SwiftTX, budget/superblocks, P2P extensions

Code: **`src/zeronode/`**.

---

## 4. Coinbase order

1. `GetBlockSubsidy(height)`
2. Founders **7.5%** (mainnet heights 412300-7999999)
3. Zeronode payee (`GetZeronodePayment` or budget)
4. Miner + fees

Tables: **`ZERO_COIN.md`** (emission totals and `contrib/stats/` tooling).

---

## 5. Sporks

| Spork | Effect |
|-------|--------|
| `SPORK_7_ZERONODE_PAYMENT_ENABLED` | Master zeronode pay switch |
| `SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED` | Tier schedule vs 100000 zat fixed |
| `SPORK_13_ENABLE_SUPERBLOCKS` | Budget payee path |
| `SPORK_3_SWIFTTX_BLOCK_FILTERING` | SwiftTX in blocks |

---

## 6. Operator setup

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

## 7. P2P

**Discovery:** ten DNS seeds (`seed0`..`seed9`.zerocurrency.io); `peers.dat` via `CAddrDB`. No fixed IP seeds in `chainparamsseeds.h` today.

**Zeronode extensions:** `spork`, `zn winner`, `zn announce`, `zn ping`, budget messages, SwiftTX locks. Dispatch: `src/main.cpp` -> `znodeman`, `budget`, `zeronodePayments`, `zeronodeSync`.

**Known issue:** spurious `Unknown command` log for handled extensions when `-debug=net` -- **`ZeroNodeDev.md`** section **9**; **`TODO.md`**.

---

## 8. Testing

Regtest: **`TEST_ZERO.md`**. Node test phases: **`ZeroNodeDev.md`** section **9**.

**Scheduled (Track Z):** Phase A RPC argument validation **now** (TST-03 / TNT-12). Phase B founders/zeronode coinbase next. Phase C two-node `startalias` after A/B. Phase D reorg after Cycle 2 reject-and-stay. Live-chain stats: **`ZERO_COIN.md`**. Execution: **`UpdateZero.md`** §3.5 / DOC-02.

---

## 9. References

| Topic | Doc |
|-------|-----|
| Dev / TENT ports | **`ZeroNodeDev.md`** |
| Economics | **`ZERO_COIN.md`** |
| CVE posture | **`ZcashFixes.md`** |
| Maintainer map | **`UpdateZero.md`** section **1** |
