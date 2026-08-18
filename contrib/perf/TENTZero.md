# TENT to Zero zeronode port map

Source correspondence between **`~/Work/ZK/ZKs/TENT`** and Zero `src/zeronode/`. This file is the **file map only**.

TENT HEAD is frozen: GitHub `TENTOfficial/TENT` and the local clone are **`bcb429b` (2021-11-13)**. There is no later masternode drop to merge.

**Do not duplicate here:** operator workflow (**`ZeroNodes.md`**); wallet interface (**`ZeroNodeDev.md`** sections **1**--**3**); TNT execution catalog (**`UpdateZero.md`** section **3.5**); zeronode test phases (**`ZeroNodeDev.md`** section **5**); emission / coinbase amounts (**`ZERO_COIN.md`**); family reorg taxonomy (**`~/Work/ZK/ZKs/Comparison.md`** section **14.5**). TENT clone notes: **`TENT.md`**.

---

## Directory map

TENT masternode sources sit in **`src/`** (not a `masternode/` subdirectory). Zero groups them under **`src/zeronode/`**. Wire commands were renamed `mn*` to `zn*`.

| TENT `src/` | Zero | Notes |
|-------------|------|-------|
| `masternode.cpp` / `masternode.h` | `zeronode/zeronode.cpp` / `.h` | List, ping, broadcast. Zero `SliceHash` copies **8** bytes at `slice * 8`; TENT still uses `&hash + slice * 64` / 64 bytes -- do not copy TENT. |
| `masternodeman.cpp` | `zeronode/zeronodeman.cpp` | Manager |
| `masternode-payments.cpp` | `zeronode/payments.cpp` | Coinbase payee; Zero removed treasury 4th vout |
| `masternode-budget.cpp` | `zeronode/budget.cpp` | Superblock budget |
| `masternode-sync.cpp` | `zeronode/zeronode-sync.cpp` | P2P sync messages |
| `darksend*.cpp` | `zeronode/obfuscation.cpp` | Mixing reduced in Zero; TENT still dispatches obfuscation in `ProcessMessage` |
| `swifttx.cpp` | `zeronode/swifttx.cpp` | Instant lock votes; Zero **DEF-06** may remove |
| `spork.cpp` | `zeronode/spork.cpp` | Live toggles |
| `masternodeconfig.cpp` | `zeronode/zeronodeconfig.cpp` | `masternode.conf` vs `zeronode.conf` |
| `rpcmasternode.cpp` / budget RPC | `rpc/zeronode.cpp` / `rpc/zeronode-budget.cpp` | RPC rename |
| *(none)* | `zeronode/zeronode-wallet-interface.cpp` | Zero **`CZeronodeWalletInterface`**; TENT uses `pwalletMain` |

Payments diff anchor: `TENT/src/masternode-payments.cpp` vs `src/zeronode/payments.cpp`.
