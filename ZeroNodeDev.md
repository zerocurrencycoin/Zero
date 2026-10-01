# ZeroNodeDev -- zeronode implementation and validation

Zeronode implementation and validation: the wallet abstraction that lets the zeronode layer build without a wallet, remaining call-site cleanup, test phases, manual regtest checks, and the tracking items ZN-01 and ZN-02, and sporks. The operator how-to is ZeroNodes.md.

---

## 1. Wallet interface

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

## 2. Remaining mismatches

Local cleanup, not TENT ports.

**`CReserveKey reservekey(pwalletMain)`** at `budget.cpp` and `rpc/zeronode-budget.cpp`: by design. The interface takes `void*`; those call sites construct the reserve key next to the wallet.

**`swifttx.cpp` `ProcessConsensusVote`:** `if (pwalletMain)` wraps an already-guarded `g_zeronodeWallet->GetRequestCount` / `IncrementRequestCount`. The outer check is redundant; replace it with the interface-only guard. SwiftTX itself stays while its mainnet sporks are on.

**Build / stub checks:** `make zerod zero-cli`; `./configure --disable-wallet && make zerod`; log line `Initialized zeronode wallet interface`. The phase E mock covers the interface in GTest.

---

## 3. Test phases

TENT has no masternode integration tests to port; Zero writes its own (ZN-01). Do not use TENT as the test oracle: Zero has no treasury vout, a different founders rule, different testnet Equihash, and `==` payee amounts (TNT-04).

Regtest facts that shape every phase: sporks default **off**; collateral must be **exactly** 10,000 ZER; coinbase maturity is **720**; with halvings every 150 blocks, total regtest miner emission is about 3000 ZER.

| Phase | Test | Status | Covers | Remaining |
|-------|------|--------|--------|-----------|
| **A** (TST-03) | Boost `rpc_zeronode_tests`, `rpc_zeronode_budget_tests` | In `--strict` | Arity and bad-arg throws for zeronode and `znbudget` RPCs; `zeronodestats` keys; `createsporkkeys`; `GetZeronodePayment` amounts via spork injection | Extend with new RPCs |
| **B** | `qa/rpc-tests/zeronode_coinbase.py` | Tier B | Sporks off: `zeronodestats` payment 0; founders window has no zn vout; unsigned `spork` update returns `failure` | None |
| **C** | `qa/rpc-tests/zeronode_startalias.py` | Tier B, partial | Two nodes reach `znsync` `RequestedZeronodeAssets == 999`; `zeronode.conf` loads; `startalias` fails cleanly without a valid vin | Success path and payee: needs a regtest collateral amount or premine, not more `generate` |
| **D** | Not written | Open | Applied reorgs via `invalidateblock`: `GetZeronodeInputAge` and collateral after disconnect. Reorgs deeper than 99 already exit (`reorg_limit.py`) | Write after C success path |
| **E** | GTest `src/gtest/test_zeronode_wallet_mock.cpp` (`ZeronodeWalletMock.*`) | In gate | Recording mock of `CZeronodeWalletInterface`: `LockCoin` / `UnlockCoin` / `GetZeronodeVinAndKeys` / request counts; `ManageStatus` (unavailable, locked, zero balance); `SelectCoinsZeronode`; no BDB | Ping and payment paths |
| **F** | `contrib/stats/chain_stats.py --zn-pay START COUNT` on a synced node | Manual | Mainnet zn amounts vs model (not payee script; that needs `txindex` + payee list). Evidence for TNT-04 | Run when a synced node is available |

Phase E is a recording mock for GTest, distinct from the `--disable-wallet` stub (`CZeronodeWalletStub`). It does not replace phase C (broadcast, list sync, `startalias`).

---

## 4. Regtest checks

The `chainActive` hardening in the zeronode layer (C-21) has no automated test. The checks below are manual regtest procedures and candidates for automation in phase D or the phase E mock. Invariant for all of them: `CChain::operator[]` returns null for a negative or out-of-range height, `chainActive.Tip()` is null on an empty chain, and reads of `chainActive` must hold `cs_main`.

| Site | Risk before the fix | Fix |
|------|---------------------|-----|
| `CZeronodePing(CTxIn&)` | Null dereference of `chainActive[Height()-12]` below height 12; unlocked read | `LOCK(cs_main)`; genesis or null hash on a short chain |
| `GetZeronodeInputAge` | After a reorg below the cached height, a negative age | Clear the cache; clamp the result to 0 or more |
| `CreateNewLock` (SwiftTX) | Null tip; negative `(height - nTxAge) + 4` | Guard the tip; return 0 when negative |
| `GetLastPaid` | Redundant second `Tip()` read | Reuse `pindexPrev` |
| `CheckInputsAndAdd` | `chainActive[...]` past the tip | Existing deferral when `pConfIndex` is null |

**Ping block hash.** A ping binds to the block 12 below the tip to limit replay; peers reject pings whose block is unknown or more than 24 blocks old (`CZeronodePing::CheckAndUpdate`). Start `zerod -regtest -zeronode=1 -debug=zeronode` with collateral and `zeronode.conf` in place, then trigger a ping (`startzeronode`, `startalias`, or `CActiveZeronode::SendZeronodePing`). With `getblockcount` below 12 the node must not crash and the ping hash must equal `getblockhash 0`. At 12 or more it must equal `getblockhash (height - 12)`.

**Input age after a reorg.** With a zeronode listed on regtest, record the tip, `invalidateblock` a recent block, and let scoring touch `GetZeronodeInputAge` (or restart and reconnect). There must be no crash, no negative input age in `-debug=zeronode` output, and a consistent zeronode list. A two-node fork where the longer chain wins exercises the same path.

**SwiftTX lock height.** Mainnet behavior is unchanged. On testnet or regtest with `SPORK_2_SWIFTTX` on and `-debug=swiftx`, exercise the lock flow; the node must not crash, and bad inputs return early.

---

## 5. Tracking

**ZN-01 -- Zeronode implementation, validation, and operator how-to.** The zeronode layer carries payee checks that can reject blocks (SPORK_8), but its integration tests are partial and the public operator documentation is obsolete. Work, in order:

1. Validation: phase C success path, which needs a regtest collateral amount or premine; then phase D (section 3).
2. Validation: automate the section 4 checks.
3. Validation: phase F mainnet payment scan as evidence for TNT-04 (`==` payee amounts, OVERPAY logging).
4. Implementation: the `ProcessConsensusVote` guard (section 2); TNT-19 budget end block before any superblock activation.
5. Operator how-to: public operator section in BUILD_ZERO, drawn from ZeroNodes.md; setup scripts (TNT-13) if written.
6. Legacy material: archive the `ZeroNodes-UpdatesPending` repository (its install script supports only Ubuntu 16.04 and 18.04, downloads 2019 binaries, and runs as root); retire or banner the [Zero Node Setup wiki page](https://github.com/zerocurrencycoin/Zero-Wallets/wiki/Zero-Node-Setup---English), which points to missing scripts and the old explorer.

**ZN-02 -- Spork future.** Decide which spork-controlled features to keep: zeronode payments and enforcement (SPORK_6, 7, 8), SwiftTX (SPORK_2, 3; DEF-06 in UpdateZero), and budgets and superblocks (SPORK_9, 13). Weigh capability against divergence from the Zcash ecosystem (upstream ports, Zebra) and support load (P2P messages, tests, operator documentation).

Background, key status, and options: section 6.

---

## 6. Sporks

Network-wide switches inherited with the zeronode code from TENT. This section covers origin, mechanics, Zero's sporks, assessment, alternatives, and the key status that ZN-02 decides on.

### 6.1 Lineage

- **Dash, 2014.** Introduced during the June 2014 "RC3" rollout of Darkcoin (later Dash): new code shipped inactive and was switched on by a signed network message once most nodes had upgraded; the community named it the spork ([Dash documentation](https://dash-docs.readthedocs.io/en/0.13.0/introduction/features.html)). Dash later gated masternode payments, budgets and superblocks, and InstantSend the same way.
- **SnowGem, 2016 to 2019; renamed TENT, later Gemlink.** A Zcash-based chain that took Dash's masternode, budget, and spork code; TENT's `spork.cpp` carries "Copyright (c) 2014-2016 The Dash developers" and "2016-2017 The SnowGem developers".
- **Zero, 2019.** Commit `20ad58542` ("Zeronodes", 2019-04-24, CryptoForge) ported TENT's masternodes as zeronodes, renamed `mn*` messages to `zn*`, numbered sporks from 10001, and added new mainnet and testnet spork keys. The regtest key is TENT's mainnet key.
- **License notice.** Commit `a09cea932` (2026-03-26, "Renames and fixes") replaced the Dash and earlier copyright lines in all 24 `src/zeronode/` files with "Copyright 2026 Zero Developers". The MIT license requires keeping the original notices; tracked as DOC-NOTICES (UpdateZero), postponed.

### 6.2 Mechanics

- **Message.** `CSporkMessage`: spork ID, value, signing time, signature. The value is a Unix time; a spork is active when its value is below the node's clock (`IsSporkActive`). `4070908800` (year 2099) means off and is the default for every ID.
- **Validation.** `ProcessSpork` accepts a message only if it is signed by the key matching `strSporkKey` (`src/chainparams.cpp`) and is newer than the stored one; a bad signature costs the peer 100 misbehavior points. Accepted messages are relayed and written to the spork database, so values survive a restart; `getsporks` serves them to new peers.
- **Administration.** A node started with `-sporkkey=<privkey>` can sign updates with the `spork` RPC. `createsporkkeys` generates a key pair for regtest tests.
- **Reach into block validity.** With SPORK_3 on, `CheckBlock` rejects blocks that spend an input locked by SwiftTX in a different transaction, and lock conflicts call `ReprocessBlocks(15)`, which disconnects and reprocesses up to 15 blocks. With SPORK_8 on, blocks failing the zeronode payee check are rejected. Both depend on node-local state (received locks, the zeronode list), not only on the chain.

### 6.3 Zero's sporks

| Spork | Effect | Affects block validity |
|-------|--------|------------------------|
| `SPORK_2_SWIFTTX` | SwiftTX instant locks | No |
| `SPORK_3_SWIFTTX_BLOCK_FILTERING` | Reject blocks conflicting with locks | Yes |
| `SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED` | Tiered zeronode payment instead of 100,000 zatoshis | Payment amount |
| `SPORK_7_ZERONODE_PAYMENT_ENABLED` | Zeronode payments on | Payment presence |
| `SPORK_8_ZERONODE_PAYMENT_ENFORCEMENT` | Reject blocks failing payee checks | Yes |
| `SPORK_9_ZERONODE_BUDGET_ENFORCEMENT` | Budget payee enforcement | Yes |
| `SPORK_13_ENABLE_SUPERBLOCKS` | Budget superblocks | Yes |

SPORK_2 and SPORK_3 were set on mainnet with value `1558907000` (2019-05-26); SPORK_9 and SPORK_13 are off (`4070908800`). Current values: `zero-cli spork show` on a synced mainnet node.

### 6.4 Assessment

**For.** Features ship dormant and switch on without a release; an emergency off switch; staged activation after most nodes upgrade.

**Against.**

- One key controls behavior that decides block validity (SPORK_3, 8, 9, 13), outside the code release process.
- A lost key freezes the values; a stolen key lets its holder switch enforcement and split the network.
- Activation depends on each node's clock and local state, not only on the chain.
- Extra P2P messages, code, and tests that Zcash and Zebra do not have, and that every upstream merge must work around.
- Bitcoin retired its comparable single-key alert system in 0.13 (2016): centralized, unaccountable, with denial-of-service bugs (CVE-2016-10724, CVE-2016-10725); the keys were published in 2018 ([bitcoin.org](https://bitcoin.org/en/posts/alert-key-and-vulnerabilities-disclosure)).

### 6.5 Alternatives

- **Height activation in a release** (ZIP 200 network upgrades; Zero's Cosmos): deterministic and reviewable; needs a coordinated release.
- **Miner signalling** (BIP 9 version bits): activation when enough blocks signal; no key.
- **Quorum signing** (Dash LLMQ and ChainLocks): masternode quorums replace a single signer for some functions; a large new subsystem.
- **Values fixed in code**: what any spork becomes after the key is lost.

### 6.6 Key status and options

The mainnet spork private key holder is unknown. It was generated for commit `20ad58542` by CryptoForge, who also has the final commits on many of the project's 2018-2022 repositories (ZeroC.md); no document in this repository or in the TENT material records custody. Without the key, values change only through a release, rolled out like a network upgrade.

1. Ask CryptoForge whether the key exists.
2. A release with a new `strSporkKey`, with recorded custody (REL-01 signing keys are the model).
3. A release that fixes spork behavior in code at an activation height: payments as they are now, SwiftTX and budgets off or removed (DEF-06). This also removes the single-key dependency.
4. Keep the current values unchanged indefinitely.

Recommendation: option 3 with the next planned network upgrade, pursuing option 1 in parallel.
