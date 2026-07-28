# TENT to Zero zeronode port map

Source correspondence between **`ZKs/TENT`** and **`Zero400`**. Operator context: **`TENT.md`**, **`Zero400/ZeroNodes.md`**. Wallet boundary (Zero-only): **`Zero400/ZeroNodeDev.md`**.

**TENT repo:** `~/Work/ZK/ZKs/TENT` -- [TENTOfficial/TENT](https://github.com/TENTOfficial/TENT) (`bcb429b` snapshot Mar 2026).

---

## Directory map

| TENT `src/masternode/` | Zero `src/zeronode/` | Notes |
|----------------------|----------------------|-------|
| `masternode.cpp` | `zeronode.cpp` | List, ping, broadcast |
| `masternode-payments.cpp` | `payments.cpp` | Coinbase payee; **treasury 4th vout removed** in Zero |
| `masternode-budget.cpp` | `budget.cpp` | Superblock budget |
| `masternode-sync.cpp` | `zeronode-sync.cpp` | P2P sync messages |
| `darksend*.cpp` | `obfuscation.cpp` | Mixing (reduced in Zero) |
| `swifttx.cpp` | `swifttx.cpp` | Instant lock votes |
| `spork.cpp` | `spork.cpp` | Live toggles |
| `masternodeconfig.cpp` | `zeronodeconfig.cpp` | `masternode.conf` vs `zeronode.conf` |
| `rpc/masternode*.cpp` | `rpc/zeronode*.cpp` | RPC rename |
| *(none)* | `wallet/zeronode-wallet-interface.cpp` | Zero **`CZeronodeWalletInterface`**; TENT uses `pwalletMain` directly |

---

## Economics diff

| Item | TENT | Zero |
|------|------|------|
| 4th coinbase vout | Treasury P2SH | **Absent** (dual-miner split only, pool ops) |
| Founders/dev % | 5 / 7.5 / 15 by era | Fixed **7.5%** |
| Config | `-masternode`, `mnconf` | `-zeronode`, `zeronode.conf` |

Code anchors: `TENT/src/masternode-payments.cpp` vs `Zero400/src/zeronode/payments.cpp`.

---

## Port candidates (from TENT)

| ID | TENT behavior | Zero action |
|----|---------------|-------------|
| TENT-01 | No spurious P2P `Unknown command` after handled MN msgs | Port logging fix (`Zero400/TODO.md`) |
| TENT-02 | Testnet min-diff after h 13000 | Optional; document only |
| TENT-05 | Treasury coinbase | **Rejected** |
| TENT-07 | MN integration tests | Shared gap; regtest first on Zero |

Full table: **`Zero400/UpdateZero.md`** TENT section.

---

## P2P extension messages (shared lineage)

Handled in both trees: `znp`, `znb`, `znget`, `dseg`, spork, budget payloads. Zero extension dispatch: `Zero400/src/main.cpp` (~7025+).
