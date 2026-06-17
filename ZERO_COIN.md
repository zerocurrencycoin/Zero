# ZERO_COIN - User-observable chain and node

Chain economics, consensus parameters, operational facts, and where Zero differs from upstream.

| Audience | Use |
|----------|-----|
| Miners / pools | Block reward, halving, zeronode share, payout expectations. |
| Node operators | Ports, config, sync, resources. |
| Exchanges / integrators | Supply, emission, RPC, branch ids. |
| Developers | Consensus-visible rules; code truth in **`src/`**. |

---

## Glossary

| Term | Meaning |
|------|--------|
| **ZER** | Ticker; amounts in RPC/wallet often in **zatoshi** (see `MAX_MONEY` / `MoneyRange` in consensus code). |
| **zatoshi** | Smallest unit (like Bitcoin's satoshi). |
| **Transparent address (t-addr)** | Public UTXO address. |
| **Shielded address (z-addr)** | Shielded pool (**Sapling** generation in this codebase). |
| **Sapling** | Shielded protocol generation; activation heights per network in **`getblockchaininfo`**. |
| **Sprout** | Earlier shielded path; relevance follows shipped rules. |
| **JoinSplit** | Shielded component moving value into/out of the pool. |
| **Note / commitment / nullifier** | Shielded note lifecycle on-chain. |
| **Equihash (192, 7)** | PoW parameters for Zero; differs from Zcash's common **(200, 9)**. |
| **Block subsidy** | New coins per block before fees; **halving** reduces it. |
| **Halving** | Subsidy right-shift at interval boundaries (see **Halving calendar**). |
| **Founders reward** | **7.5%** of block subsidy in eligible heights to rotating transparent addresses. |
| **Zeronode** | Incentive layer; **20-40%** of block value when sporks enable tiers (see **Zeronode payments**). |
| **Spork** | Live-adjustable network toggle (zeronode tiers, etc.). |
| **COINBASE_MATURITY** | **720** confirmations before coinbase is spendable (this tree; not Bitcoin's 100). |
| **Coinbase** | Subsidy + fees in the block reward transaction. |
| **Mainnet / testnet / regtest** | Production / public test / local regression. |
| **Network upgrade (NU) / branch id** | Rule set by height; **branch id** in sighash for Overwinter+ txs. |
| **zerod** / **zero-cli** / **zero-tx** | Daemon, RPC client, tx utility (**doc/man/**). |
| **RPC** | JSON-RPC from **zerod**. |
| **Pruning / txindex** | Optional modes; may force **reindex**. |
| **Reindex** / **Rescan** | Chain index rebuild vs wallet rescan. |
| **Params** | Proving keys; **fetch-params** scripts. |
| **MAX_MONEY** | Caps **single-output** amounts; total issued supply is a separate concept (**Total supply**). |
| **Deprecation** | Node may enforce upgrade by height/date (see [README -- Deprecation](README.md#-deprecation-policy)). |
| **P2P subver** | Peer user-agent (Zero branding). |
| **Mempool** | Unconfirmed txs awaiting blocks. |

---

## Chain launch

- **Genesis:** 19 Feb 2017; hash `068cbb5db6bc11be5b93479ea4df41fa7e012e92ca8603c315f9b1a2202205c6`.
- **No ICO, no premine** -- emission follows the subsidy schedule below.

---

## Economics vs Bitcoin / Zcash / Pirate

| Component | Zero | Bitcoin | Zcash | Pirate |
|-----------|------|---------|-------|--------|
| Base subsidy | 10 ZER (pre-fee) / 10.8 ZER (post-fee) | 50 BTC (historic) | 12.5 ZEC (slow-start era) | Asset-chain config |
| Halving interval | 800k pre-Blossom, 1.6M post-Blossom | 210k | 840k / 1.68M | ASSETCHAINS_HALVING |
| Founder/dev | **7.5%** of subsidy | None | 20% (ECC+ZF era) | None |
| Node reward | **20-40%** zeronode | None | None | Notary-style pay |

Target block spacing **120 s** (pre-Blossom); ~800k blocks per halving interval is about **1,111 days** (~3.04 years).

---

## Halving calendar

| Event | Block | Date (UTC) |
|-------|-------|------------|
| Genesis | 0 | 19 Feb 2017 |
| Halving 1 | 800,000 | March 7, 2020 |
| Halving 2 | 1,600,000 | March 25, 2023 |
| Halving 3 | 2,400,000 | March 12, 2026 |

---

## Timing constants (consensus)

| Constant | Value |
|----------|-------|
| PRE_BLOSSOM_POW_TARGET_SPACING | 120 s |
| BLOSSOM_POW_TARGET_SPACING_RATIO | 2 |
| PRE_BLOSSOM_HALVING_INTERVAL | 800,000 blocks |
| PRE_BLOSSOM_REGTEST_HALVING_INTERVAL | 150 |
| POST_BLOSSOM_REGTEST_HALVING_INTERVAL | 300 |

Pre-Blossom halving index: **`nHeight / 800000`**.

---

## Block subsidy rule

1. Base **10 ZER** per block before **fee-start**; **10.8 ZER** at and after fee-start.
2. **Halving count** from height (pre-Blossom: **`height / 800000`**; no Zcash-style slow-start shift).
3. Subsidy = base `>> halvings` (right shift); zero after 64 halvings.
4. If Blossom were active, implementation divides base by **2** before shifting; Blossom is not activated on mainnet in current params.

Implementation: **`GetBlockSubsidy`** in **`src/main.cpp`**.

---

## Fee-start height (`nFeeStartBlockHeight`)

| Network | Height |
|---------|--------|
| Mainnet | **412,300** |
| Testnet | 1 |
| Regtest | 5,000 |

At mainnet fee-start: base subsidy steps **10 -> 10.8 ZER**; founders output becomes required in coinbase (when also before last founders height). Zeronode tiers key off **800k** height multiples.

---

## Founders reward (7.5%)

- **When:** `height >= fee-start` and `height <=` last founders height (**7,999,999** under pre-Blossom formula).
- **Amount:** **7.5%** of **`GetBlockSubsidy`** for that height.
- **Where:** Rotates among **`vFoundersRewardAddress`** (mainnet addresses in **Founder and system addresses** below). **`getblockchaininfo`** exposes this as **`developmentfee`**.

---

## Zeronode payments (20-40%)

Share of **block value** (subsidy before fees split).

| Mainnet height | Approx. % of block value |
|----------------|--------------------------|
| < 800,000 | 20% |
| >= 800,000 | 25% |
| >= 1,600,000 | 30% |
| >= 2,400,000 | 35% |
| >= 3,200,000 | 40% |

**Sporks:** **`SPORK_7_ZERONODE_PAYMENT_ENABLED`** must be on for non-zero zeronode payment; **`SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED`** selects tier schedule vs fixed **100,000** zatoshis. **`SPORK_13_ENABLE_SUPERBLOCKS`** routes payees through **budget** instead of default zeronode fill.

---

## Coinbase payee order

1. **`blockValue`** = **`GetBlockSubsidy(height)`**.
2. **Founders** = **7.5%** of **`blockValue`** when required.
3. **Zeronode** = **`GetZeronodePayment`** (or budget path).
4. **Miner** = **`blockValue - founders - zeronode + fees`**.

---

## Worked example

**Height 2,382,565**: halvings = 2; subsidy = 10.8 >> 2 = **2.7 ZER**; founders **0.2025 ZER**; zeronode 30% of block value = **0.81 ZER**; miner **~1.6875 ZER** + fees.

---

## Total supply and MAX_MONEY

Total supply is targeted at some **20M ZER**. **`MAX_MONEY`** in **`src/amount.h`** limits per-output amounts; validation uses **`MoneyRange`** on individual subsidy outputs, not a running cap on total supply. Integrators should not equate **`MAX_MONEY`** with total supply.

---

## Network upgrades and branch identifiers

Overwinter-style transactions bind a **consensus branch id** into the **sighash**. **Sapling** and **Cosmos** both use **`0x7361707a`** in **`src/consensus/upgrades.cpp`**. There is no separate sighash epoch between them unless a future NU introduces a new **`nBranchId`**.

Wallets and signers must use activation heights from **`getblockchaininfo`** / **`getblock`** for their network.

---

## Founder and system addresses

### Founders (mainnet, rotate by height)

`t3hmg6WApjqVFw9oPWTDy4JLEqXcUWthg5v`, `t3hrh5M7eaGA5zXCitPXz2pbe146GkVPWHs`, `t3aWmHqBGS7watoKQLa7uykeTaYHoYqM361`, `t3hsi89hPsZzmnbs3pny6cfAxMxV5TJLErj`, `t3TdGxPVUdMXd6qDrDCEuJETLadZ9Ki3s9r`, `t3cb5ZjKmbGbqDaYk97Auam9kXXikGQBmyY`, `t3V1YovGUPW9WSBoAHS48FDdUfUTo6LDpZR`, `t3KB9n28MVg31oo856t1tQGfJuYq8usTvSi`, `t3dqSV4YGj5V3WjQhqFGrKTMUf9Tgc6xnJM`, `t3aJkYT1i6tyytq8J6khPaDNtgZsBSXgfBf`

Testnet/regtest: **`src/chainparams.cpp`** (`GetFoundersRewardAddressAtHeight`).

### Zeronode dummy (collateral checks only)

Mainnet `t1TLNF3seMZennWmmxik8r1PVEKj5zudgRw`; testnet `tmWuQ8Yh3pHDa8MingmN8ECPRBxo2n8uZRs`; regtest `s1eQnJdoWDhKhxDrX8ev3aFjb1J6ZwXCxUT`. Used to build validation-only transactions for **10,000 ZER** collateral checks.

### ZeroWallet donation (out-of-tree)

Mainnet donation address (zerowallet repo): `t1fDbALrS7tZV7DDvadAT7yHi5Sztptj8yP`.

---

## Operational reference

- **Default RPC port:** **23801** (see [README -- Running Zero](README.md#-running-zero), `contrib/zero.conf`).
- **Datadir:** `~/.zero`; wallet file `wallet.zero` -- **back up** before upgrades.
- **Proving params:** `zcutil/fetch-params.sh`; see [BUILD_ZERO -- .zero directory](BUILD_ZERO.md#3-zero-directory).
- **Tor:** `doc/tor.md`.
- **New addresses:** `getnewaddress` (transparent), `z_getnewaddress sapling` (shielded); list: `getaddressesbyaccount ""`, `z_listaddresses`.

---

## Security

The node is **experimental**; use at your own risk. Back up keys and wallet files. See [README -- Deprecation](README.md#-deprecation-policy) and [Zcash security information](https://z.cash/support/security/).

---

## References

| Resource | URL |
|----------|-----|
| Zero website | [zerocurrency.io](https://zerocurrency.io) |
| Releases | [github.com/zerocurrencycoin/Zero/releases](https://github.com/zerocurrencycoin/Zero/releases) |
| BitcoinTalk | [topic 3310714](https://bitcointalk.org/index.php?topic=3310714.0) |
| Zcash protocol (PDF) | [protocol.pdf](https://github.com/zcash/zips/raw/master/protocol/protocol.pdf) |
| Zcash security | [z.cash/support/security](https://z.cash/support/security/) |

---

## Coinbase validation (extended)

Mainnet-verified coinbase behavior, pool 4-vout splits, halving **2,400,000** samples, and `contrib/decode_coinbase.py` are documented in **[ZeroMac/ZERO_COIN.md](../ZeroMac/ZERO_COIN.md)** (appendix). Founders multisig detail: **`Zeros/MULTISIG.md`**. Zcash 2026 CVE applicability: **`ZcashV.md`**.
