# Zero Nodes -- zeronode operator guide

Operators and integrators: setup, economics, sporks, testing. **Developers (wallet boundary, TENT port work):** **`ZeroNodeDev.md`**.

Last updated: Jun 2026.

---

## Document split

| Doc | Audience |
|-----|----------|
| **`ZeroNodes.md`** (this file) | Run a zeronode, RPC, sporks, economics pointers |
| **`ZeroNodeDev.md`** | Wallet interface, TENT lineage, upstream port candidates, test gaps |
| **`ZERO_COIN.md`** | Coinbase split, emission, datadir |
| **`UpdateZero.md`** | Maintainer roadmap, bootstrap, regtest map |

---

## TENT relationship

Zero's zeronode layer is a port of **TENT** (`ZKs/TENT`) masternode code into `src/zeronode/` (wire commands renamed `mn*` -> `zn*`). TENT kept a treasury coinbase output and direct `pwalletMain` access; Zero removed the treasury and added **`CZeronodeWalletInterface`**. File map: **`TENTZero.md`**. Port/reject decisions: **`ZeroNodeDev.md`** section 8.

---

## What a zeronode is

- **Collateral:** 10,000 ZER locked UTXO
- **Payment:** 20% -> 40% of block subsidy by 800k tiers (spork-gated)
- **Services:** SwiftTX, budget/superblocks, P2P extensions

Code: **`src/zeronode/`**.

---

## Coinbase order

1. `GetBlockSubsidy(height)`
2. Founders **7.5%** (mainnet heights 412300-7999999)
3. Zeronode payee (`GetZeronodePayment` or budget)
4. Miner + fees

Tables: **`ZERO_COIN.md`** (emission totals and `contrib/stats/` tooling).

---

## Sporks

| Spork | Effect |
|-------|--------|
| `SPORK_7_ZERONODE_PAYMENT_ENABLED` | Master zeronode pay switch |
| `SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED` | Tier schedule vs 100000 zat fixed |
| `SPORK_13_ENABLE_SUPERBLOCKS` | Budget payee path |
| `SPORK_3_SWIFTTX_BLOCK_FILTERING` | SwiftTX in blocks |

---

## Operator setup

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

## P2P

**Discovery:** ten DNS seeds (`seed0`..`seed9`.zerocurrency.io); `peers.dat` via `CAddrDB`. No fixed IP seeds in `chainparamsseeds.h` today -- see **`UpdateZero.md`** bootstrap note.

**Zeronode extensions:** `spork`, `zn winner`, `zn announce`, `zn ping`, budget messages, SwiftTX locks. Dispatch: `src/main.cpp` -> `znodeman`, `budget`, `zeronodePayments`, `zeronodeSync`.

**Known issue:** spurious `Unknown command` log for handled extensions -- **`ZeroNodeDev.md`** ZND-01, **`TODO.md`**.

---

## Testing

Regtest: **`TEST_ZERO.md`**. Node test phases: **`ZeroNodeDev.md`** section 8. Live-chain stats: **`ZERO_COIN.md`** (Emission totals).

---

## References

| Topic | Doc |
|-------|-----|
| Dev / TENT ports | `ZeroNodeDev.md` |
| Economics | `ZERO_COIN.md` |
| CVE posture | `ZcashFixes.md` |
