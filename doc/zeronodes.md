# Zeronodes

Implementation reference for the zeronode layer of `zerod`: zeronodes, sporks, SwiftTX, and budgets. This code comes from Dash and PIVX, not from Zcash. It lives in `src/zeronode/`, with RPCs in `src/rpc/zeronode.cpp`, `src/rpc/zeronode-budget.cpp`, and `src/rpc/spork.cpp`.

---

## 1. Code layout

| File | Role |
|------|------|
| `zeronode.cpp`, `zeronodeman.cpp` | Zeronode list, broadcasts (`znb`), pings, and scores |
| `activezeronode.cpp` | This node's own zeronode status |
| `zeronodeconfig.cpp` | `zeronode.conf` aliases for `startalias` |
| `payments.cpp` | Payee votes, block payee fill (`FillBlockPayee`) and check (`IsBlockPayeeValid`) |
| `zeronode-sync.cpp` | Sync of sporks, zeronode list, payment votes, and budgets from peers |
| `spork.cpp`, `sporkdb.cpp` | Sporks (section 2) |
| `swifttx.cpp` | SwiftTX transaction locks (section 3) |
| `budget.cpp` | Budget proposals and superblocks (section 4) |
| `obfuscation.cpp` | `CObfuScationSigner`, which signs and verifies zeronode messages, and `ThreadCheckObfuScationPool`, the maintenance loop (sync, ping, list cleanup, `zncache.dat` dump); no mixing code |
| `zeronode-wallet-interface.cpp` | Wallet access for collateral and keys |

Zeronode code looks up transactions by txid with `GetTransaction` (`src/main.cpp`): the collateral owner check (`CObfuScationSigner::IsVinAssociatedWithPubkey`), the broadcast signature-time check (`zeronode.cpp`), SwiftTX input lookups, and budget collateral. With the always-on transaction index every lookup succeeds; without it, only transactions with unspent outputs are found.

---

## 2. Sporks

A spork is a network-wide switch carried in a signed `spork` message. Nodes relay sporks, answer `getsporks`, and store them in `sporks/` (LevelDB). A spork value is a Unix time: `IsSporkActive` returns true when the value is before the current time. Without a received message the default applies, 4070908800 (2099-01-01), which is off.

| Spork (ID) | Checked in | Effect when active | Mainnet |
|------------|------------|--------------------|---------------------|
| `SPORK_2_SWIFTTX` (10001) | `swifttx.cpp`, `CMerkleTx::GetTransactionLockSignatures` | SwiftTX locks are processed | active |
| `SPORK_3_SWIFTTX_BLOCK_FILTERING` (10002) | `CheckBlock` in `src/main.cpp` | A block with a transaction that conflicts with a lock is rejected (`conflicting-tx-ix`) | active |
| `SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED` (10005) | `GetZeronodePayment`, `rpc/mining.cpp` | Zeronode share by halving index, 20 to 40% of block value; when off, a fixed 100000 zatoshis | active |
| `SPORK_7_ZERONODE_PAYMENT_ENABLED` (10006) | `GetZeronodePayment`, `rpc/mining.cpp` | Zeronode share is paid; when off, 0 | active |
| `SPORK_8_ZERONODE_PAYMENT_ENFORCEMENT` (10007) | `payments.cpp`, `zeronode-sync.cpp`, `zeronodeman.cpp`, `rpc/mining.cpp` | Blocks must pay the expected zeronode payee | active |
| `SPORK_9_ZERONODE_BUDGET_ENFORCEMENT` (10008) | `payments.cpp` | Budget payments are enforced | off |
| `SPORK_13_ENABLE_SUPERBLOCKS` (10012) | `payments.cpp` | Superblocks pay budget proposals instead of the zeronode payee | off |

`zero-cli spork active` shows which sporks are active; `spork show` shows their values.

---

## 3. SwiftTX

Zeronodes vote to lock the inputs of a transaction (messages `ix` and `txlvote`); a locked input cannot be spent by a different transaction. With `SPORK_3` active, `CheckBlock` rejects blocks that contain such a conflicting spend.

---

## 4. Budget

Budget proposals and votes travel in `zprop`, `mvote`, `fbs`, `fbvote`, and `znvs` messages and are stored in `budget.dat`. The budget RPCs are in `src/rpc/zeronode-budget.cpp` (11 rows in `doc/RPCs.csv`). Payment through a budget superblock needs `SPORK_13`, and its enforcement `SPORK_9`; both are off on mainnet, so the superblock paths in `FillBlockPayee` and `IsBlockPayeeValid` do not run. Nodes still relay and store budget messages.

---

## 5. Interactions with the node

| Area | Code | Spork |
|------|------|-------|
| Coinbase amount | `GetZeronodePayment` (`src/main.cpp`) | 6, 7 |
| Block validity | `IsBlockPayeeValid` (`payments.cpp`): payee, superblock | 8; 9, 13 |
| Block validity | `CheckBlock`: lock conflict, `conflicting-tx-ix` | 3 |
| Mempool | `AcceptableInputs`: refuses a spend of a locked input by another transaction | 2 |
| Mining | `FillBlockPayee`, `getblocktemplate` (`rpc/mining.cpp`) | 6, 7, 8, 13 |
| Wallet confirmations | `CMerkleTx::GetDepthInMainChain` adds `-swifttxdepth` (default 5) to a locked transaction under 6 confirmations; `enableIX` defaults to true, and the one-argument overload drops its argument | 2 |
| P2P and sync | `spork`, `getsporks`, `ix`, `txlvote`, budget messages; zeronode sync stages for sporks and budgets; inventory relay in `src/main.cpp` | -- |
| Transaction index | `GetTransaction` lookups (section 1); the `txindex=1` check for zeronodes in `AppInit2` cannot fail | -- |

---

## 6. Review

1. **History of the payment sporks.** Scan every mainnet coinbase from the fee-start height with `contrib/stats/decode_coinbase.py` and compare the zeronode output with `GetZeronodePayment` for sporks 6 and 7 both on, both off, and 7 only. The result shows whether a fixed value in code would validate the whole chain or needs a height boundary.
2. **SwiftTX use.** On a mainnet node, count `ix` and `txlvote` messages and entries in `mapTxLocks` over a week (`-debug=zeronode`). Check whether any Zero wallet or service sends lock requests.
3. **Budget use.** Run `getbudgetinfo` and `getbudgetprojection` on mainnet, and check the size of `budget.dat` and the count of proposals and finalized budgets.
4. **Active-spork tests.** Tests run only with sporks at their defaults: `zeronode_coinbase.py` shows that a spork update fails without the regtest spork private key. Add a regtest signing key to the test framework, then test each row of section 5 with the spork on and off, across two nodes that must agree on block validity.
5. **Wallet depth.** Fix or confirm the one-argument `GetDepthInMainChain` overload, then list which RPCs (`listtransactions`, `getalldata`, `z_*`) report SwiftTX-raised confirmations.
6. **Upstream.** Read how PIVX and Dash retired or replaced SwiftX/InstantSend and budgets, and which sporks they hard-coded.
