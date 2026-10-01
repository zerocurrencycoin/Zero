# Zero Nodes -- zeronode operator guide

How to run a zeronode on mainnet or testnet: collateral, configuration, sporks, coinbase payments, and node behavior on a deep reorg. Source for the public operator section in BUILD_ZERO (ZN-01 in ZeroNodeDev.md).

---

## 1. What a zeronode is

A zeronode is a full node that locks exactly **10,000 ZER** of collateral in one UTXO and in return receives a share of each block reward once the payment sporks are on. Zero's zeronode layer is a renamed port of TENT's masternode code (`src/zeronode/`).

- **Payment:** 20% of the block subsidy, rising by 5% every 800,000 blocks to 40%, when the payment sporks are enabled.
- **Services:** zeronode list and payment voting, SwiftTX instant locks (sporks `SPORK_2` and `SPORK_3` are on mainnet), and budget superblocks (sporks off).

---

## 2. Coinbase order

1. `GetBlockSubsidy(height)`
2. Founders output, 7.5% (mainnet heights 412300 to 7999999)
3. Zeronode payee (`GetZeronodePayment`, or the budget payee when superblocks are on)
4. Miner, plus fees

Payee amounts must match exactly; overpayment to the winner is logged as `OVERPAY`.

---

## 3. Sporks

Sporks are network-wide switches signed with the spork key. The unsigned default for the IDs below is off (timestamp `4070908800`); mainnet uses signed values. Regtest tests that need payees activate sporks with `createsporkkeys` and `spork`. Mechanics and key status: ZeroNodeDev.md section 6.

| Spork | Effect |
|-------|--------|
| `SPORK_7_ZERONODE_PAYMENT_ENABLED` | Master switch for zeronode payments |
| `SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED` | Tiered schedule instead of a fixed 100,000 zatoshis |
| `SPORK_8_ZERONODE_PAYMENT_ENFORCEMENT` | Reject blocks that fail payee checks |
| `SPORK_13_ENABLE_SUPERBLOCKS` | Budget payee path |
| `SPORK_2_SWIFTTX` | SwiftTX instant locks (mainnet on) |
| `SPORK_3_SWIFTTX_BLOCK_FILTERING` | SwiftTX conflict filtering in blocks (mainnet on) |

---

## 4. Setup

```bash
./zcutil/fetch-params.sh
./src/zerod -daemon
./src/zero-cli zeronode genkey
# send exactly 10000 ZER to an address in this wallet; wait for confirmations
./src/zero-cli getzeronodeoutputs
```

`zero.conf` on the zeronode host:

```text
zeronode=1
zeronodeprivkey=<key from zeronode genkey>
externalip=<public ip>:23801
```

`zeronode.conf` in the data directory (override with `-znconf`), one line per zeronode:

```text
MN1 <public ip>:23801 <zeronodeprivkey> <collateral txid> <output index>
```

Then start it with `./src/zero-cli zeronode startalias MN1` (or `startzeronode "alias" "0" "MN1"`).

**Ports:** mainnet P2P 23801, RPC 23811. **Data directory:** `~/.zero` (Linux), `~/Library/Application Support/zero` (macOS), `%APPDATA%\zero` (Windows). A wallet-disabled build cannot run a zeronode: collateral lookup and signing need the wallet.

---

## 5. Deep reorg

A node refuses to apply a reorg, or an unintended rewind at startup, deeper than 99 blocks. Instead it logs the event, shows a modal, and shuts down; the competing fork is not connected. Coinbase maturity (720 blocks) is a separate rule.

A reorg of 100 to 719 blocks therefore takes the zeronode off the network while its collateral may still be immature. The 99-block bound is tied to the size of the shielded witness cache; following unbounded reorgs, as TENT does, is rejected. Analysis and options: UpdateZero section 8.3.

---

## 6. P2P

**Discovery:** ten DNS seeds (`seed0`..`seed9.zerocurrency.io`) and `peers.dat`. There are no fixed IP seeds (REL-08); a node cannot find peers if DNS fails.

**Zeronode messages:** `spork`, zeronode winner, announce, and ping, budget messages, and SwiftTX locks, dispatched in `src/main.cpp` after the standard messages to the zeronode manager, budget, payments, SwiftTX, spork, and sync handlers.
