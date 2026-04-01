# ZERO_COIN — User-observable chain and node

Reference for **what the Zero network and this node do** from an operator, miner, pool, exchange, and integrator perspective: economics visible on-chain, heights and dates, ports, operational facts, and how Zero differs from upstream where it matters.

| Audience | Use |
|----------|-----|
| Miners / pools | Block reward, halving, zeronode share, payout expectations. |
| Node operators | Ports, config, sync, resources. |
| Exchanges | Supply, emission, RPC, branch ids. |
| Developers | Consensus-visible rules; code truth in **`src/`**. |

**Not in scope:** build instructions (**[BUILD_ZERO.md](BUILD_ZERO.md)**), tests (**[TEST_ZERO.md](TEST_ZERO.md)**), long C++ excerpts and test-file inventories.
---

## Glossary

| Term | Meaning |
|------|--------|
| **ZER** | Ticker; amounts in RPC/wallet often in **zatoshi** (see `MAX_MONEY` / `MoneyRange` in consensus code). |
| **zatoshi** | Smallest unit (like Bitcoin’s satoshi). |
| **Transparent address (t-addr)** | Public UTXO address. |
| **Shielded address (z-addr)** | Shielded pool (**Sapling** generation in this codebase). |
| **Sapling** | Shielded protocol generation; activation heights per network in **`getblockchaininfo`**. |
| **Sprout** | Earlier shielded path; relevance follows shipped rules. |
| **JoinSplit** | Shielded component moving value into/out of the pool. |
| **Note / commitment / nullifier** | Shielded note lifecycle on-chain. |
| **Equihash (192, 7)** | PoW parameters for Zero; differs from Zcash’s common **(200, 9)**. |
| **Block subsidy** | New coins per block before fees; **halving** reduces it. |
| **Halving** | Subsidy right-shift at interval boundaries (see **Halving calendar**). |
| **Founders reward** | **7.5%** of block subsidy in eligible heights to rotating transparent addresses. |
| **Zeronode** | Incentive layer; **20–40%** of block value when sporks enable tiers (see **Zeronode payments**). |
| **Spork** | Live-adjustable network toggle (zeronode tiers, etc.). |
| **COINBASE_MATURITY** | **720** confirmations before coinbase is spendable (this tree; not Bitcoin’s 100). |
| **Coinbase** | Subsidy + fees in the block reward transaction. |
| **Mainnet / testnet / regtest** | Production / public test / local regression. |
| **Network upgrade (NU) / branch id** | Rule set by height; **branch id** in sighash for Overwinter+ txs. |
| **zerod** / **zero-cli** / **zero-tx** | Daemon, RPC client, tx utility (**doc/man/**). |
| **RPC** | JSON-RPC from **zerod**. |
| **Pruning / txindex** | Optional modes; may force **reindex** (**BUILD_ZERO**, **init** help). |
| **Reindex** / **Rescan** | Chain index rebuild vs wallet rescan. |
| **Params** | Proving keys; **fetch-params** scripts. |
| **MAX_MONEY** | Caps **single-output** amounts; **total issued** (~25.6M ZER) is a separate concept (**Total supply**). |
| **Deprecation** | Node may enforce upgrade by height/date (see README). |
| **P2P subver** | Peer user-agent (Zero branding, not upstream “MagicBean”). |
| **Mempool** | Unconfirmed txs awaiting blocks. |
| **ZIP** | Zcash Improvement Proposal; informative lineage. |

---

## Chain launch

- **Genesis:** 19 Feb 2017; hash `068cbb5db6bc11be5b93479ea4df41fa7e012e92ca8603c315f9b1a2202205c6`.
- **No ICO, no premine** - emission follows the subsidy schedule below.

---

## Economics vs Bitcoin / Zcash / Pirate (summary)

| Component | Zero | Bitcoin | Zcash | Pirate |
|-----------|------|---------|-------|--------|
| Base subsidy | 10 ZER (pre-fee) / 10.8 ZER (post-fee) | 50 BTC (historic) | 12.5 ZEC (slow-start era) | Asset-chain config |
| Halving interval | 800k pre-Blossom, 1.6M post-Blossom | 210k | 840k / 1.68M | ASSETCHAINS_HALVING |
| Founder/dev | **7.5%** of subsidy | None | 20% (ECC+ZF era) | None |
| Node reward | **20–40%** zeronode | None | None | Notary-style pay |

Target block spacing **120 s** (pre-Blossom) → ~800k blocks ≈ targets **1,111 days** (~3.04 years) between halvings.

---

## Halving calendar

| Event | Block | Date (UTC) |
|-------|-------|------------|
| Genesis | 0 | 19 Feb 2017 11:26:40 |
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

**pre-Blossom** halving index **`nHeight / 800000`** applies for documentation purposes.

---

## Block subsidy rule (conceptual)

1. Base **10 ZER** per block before **fee-start**; **10.8 ZER** at and after fee-start (see table below).
2. **Halving count** from height (pre-Blossom: **`height / 800000`**; no Zcash-style slow-start shift on Zero).
3. Subsidy = base `>> halvings` (right shift); zero after 64 halvings.
4. If Blossom were active at a height, implementation also divides base by **2** before shifting; on today’s mainnet params Blossom is not activated, so this path is not used on mainnet until a future NU changes that.

Implementation: **`GetBlockSubsidy`** in **`src/main.cpp`** (maintainer code excerpt: **UpdateZero** Appendix D).

---

## Fee-start height (`nFeeStartBlockHeight`)

| Network | Height |
|---------|--------|
| Mainnet | **412,300** |
| Testnet | 1 |
| Regtest | 5,000 |

At **mainnet** fee-start: base subsidy **10 → 10.8 ZER**; **founders** output becomes required in coinbase (when also before last founders height). Zeronode tiers key off **800k** height multiples (**pre-Blossom** interval).

---

## Founders reward (7.5%)

- **When:** `height ≥ fee-start` and `height ≤` last founders height (**7,999,999** under current pre-Blossom formula for last founders block).
- **Amount:** **7.5%** of **`GetBlockSubsidy`** for that height (see code paths in **`zeronode/payments.cpp`**, **`budget.cpp`**).
- **Where:** Rotates among **`vFoundersRewardAddress`** (**mainnet** addresses in **Founder and system addresses** below). **`getblockchaininfo`** exposes this stream as **`developmentfee`**.

---

## Zeronode payments (20–40%)

Share of **block value** (subsidy before fees split—not the same as “% of coinbase after fees” in all edge cases; miners also take fees).

| Mainnet height (typical tiers) | Approx. % of block value |
|--------------------------------|---------------------------|
| < 800,000 | 20% |
| ≥ 800,000 | 25% |
| ≥ 1,600,000 | 30% |
| ≥ 2,400,000 | 35% |
| ≥ 3,200,000 | 40% |

**Sporks:** **`SPORK_7_ZERONODE_PAYMENT_ENABLED`** must be on for non-zero zeronode payment; **`SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED`** selects tier schedule vs fixed **100,000** zatoshis. **`SPORK_13_ENABLE_SUPERBLOCKS`** can route payees through **budget** instead of default zeronode fill.

---

## Coinbase payee order (typical)

1. **`blockValue`** = **`GetBlockSubsidy(height)`**.
2. **Founders** = **7.5%** of **`blockValue`** when required.
3. **Zeronode** = **`GetZeronodePayment`** (or budget path).
4. **Miner** ≈ **`blockValue − founders − zeronode + fees`** (see **`FillBlockPayee`** in **`src/zeronode/payments.cpp`** / **`budget.cpp`**).

---

## Worked example (update over time)

**Height 2,382,565** (illustrative): halvings **= 2** → subsidy **10.8 >> 2 = 2.7 ZER**; founders **0.2025 ZER**; zeronode **30%** of block value in that band → **0.81 ZER**; miner **~1.6875 ZER** plus fees. Next halving boundary at **2,400,000**.

---

## Total supply and MAX_MONEY

Long-run issued sum is on the order of **~25.6M ZER** under the piecewise schedule (pre-fee era, post-fee segment, geometric halving tail). **`MAX_MONEY`** in **`src/amount.h`** (~16.95M ZER expressed in zatoshi) limits **per-output** amounts; **cumulative** issuance can exceed that constant—validation uses **`MoneyRange`** on individual subsidy outputs, not a running cap on total supply. Integrators should not equate **`MAX_MONEY`** with “max ZER that will ever exist.”

Circulating supply figures from third parties (explorers, aggregators) should be checked against your own node.

---

## Network upgrades and branch identifiers (integrators)

Transactions signed under Overwinter-style rules bind a **consensus branch id** into the **sighash**. **Sapling** and **Cosmos** both use **`0x7361707a`** in **`src/consensus/upgrades.cpp`**. There is **no separate sighash epoch** between them on the current roadmap unless a future NU introduces a new **`nBranchId`**.

Wallets and signers must use activation heights from **`getblockchaininfo`** / **`getblock`** for their network. **Replay** across chains depends on chain ID, peers, and transaction format—not branch id alone.

---

## Founder and system addresses (on-chain reference)

### Founders (mainnet, rotate by height)

`t3hmg6WApjqVFw9oPWTDy4JLEqXcUWthg5v`, `t3hrh5M7eaGA5zXCitPXz2pbe146GkVPWHs`, `t3aWmHqBGS7watoKQLa7uykeTaYHoYqM361`, `t3hsi89hPsZzmnbs3pny6cfAxMxV5TJLErj`, `t3TdGxPVUdMXd6qDrDCEuJETLadZ9Ki3s9r`, `t3cb5ZjKmbGbqDaYk97Auam9kXXikGQBmyY`, `t3V1YovGUPW9WSBoAHS48FDdUfUTo6LDpZR`, `t3KB9n28MVg31oo856t1tQGfJuYq8usTvSi`, `t3dqSV4YGj5V3WjQhqFGrKTMUf9Tgc6xnJM`, `t3aJkYT1i6tyytq8J6khPaDNtgZsBSXgfBf`

Testnet/regtest: **`src/chainparams.cpp`** (`GetFoundersRewardAddressAtHeight`).

### Zeronode dummy (collateral checks only)

Not a normal payout sink: **mainnet** `t1TLNF3seMZennWmmxik8r1PVEKj5zudgRw`; testnet `tmWuQ8Yh3pHDa8MingmN8ECPRBxo2n8uZRs`; regtest `s1eQnJdoWDhKhxDrX8ev3aFjb1J6ZwXCxUT`. Used to build validation-only transactions for **10,000 ZER** collateral checks.

### ZeroWallet donation (out-of-tree)

**Mainnet** donation UI address (zerowallet repo): `t1fDbALrS7tZV7DDvadAT7yHi5Sztptj8yP` — verify against current wallet source.

---

## Operational reference

- **Default RPC port:** **23801** (see **`contrib/zero.conf`**, README).
- **Datadir:** typically **`~/.zero`**; wallet file often **`wallet.zero`**—**back up** before upgrades.
- **Proving params:** **fetch-params** / **BUILD_ZERO** for mirrors and naming.
- **Tor:** **`doc/tor.md`**; ensure **subver** examples match shipped branding (not legacy MagicBean).
- **New addresses:** `getnewaddress` (transparent), `z_getnewaddress sapling` (shielded); list: `getaddressesbyaccount ""`, `z_listaddresses`.

---

## Security and experimental status

The node is **experimental**; use at your own risk. Back up keys and wallet files. See README deprecation policy and [Zcash security information](https://z.cash/support/security/) for zk-SNARK wallet hygiene.

**P2P alerts:** Bitcoin/Zcash-style network alerts are deprecated upstream; Zero may still carry related test scaffolding—product decision is maintainer scope (**UpdateZero** decisions / code), not wallet RPC.

---

## References

### Project

| Resource | URL |
|----------|-----|
| Zero website | [zerocurrency.io](https://zerocurrency.io) |
| This repository | [github.com/zerocurrencycoin/Zero](https://github.com/zerocurrencycoin/Zero) |
| Releases | [github.com/zerocurrencycoin/Zero/releases](https://github.com/zerocurrencycoin/Zero/releases) |

### Community

| Resource | URL |
|----------|-----|
| BitcoinTalk (older) | [topic 1796036](https://bitcointalk.org/index.php?topic=1796036.0) |
| BitcoinTalk (newer) | [topic 3310714](https://bitcointalk.org/index.php?topic=3310714.0) |

### Protocol lineage

| Resource | URL |
|----------|-----|
| Zcash protocol (PDF) | [protocol.pdf](https://github.com/zcash/zips/raw/master/protocol/protocol.pdf) |
| ZIPs | [zips.z.cash](https://zips.z.cash/) |
| Bitcoin Core docs | [bitcoincore.org](https://bitcoincore.org/en/doc/) |

Mining sites (e.g. [miningpoolstats.stream/zero](https://miningpoolstats.stream/zero)) may drift from your node—**verify on-chain**.

### In-repo technical sources

| Topic | Document |
|-------|----------|
| Build, depends | [BUILD_ZERO.md](BUILD_ZERO.md) |
| Tests, maturity 720 | [TEST_ZERO.md](TEST_ZERO.md) |
| CLI flags | [doc/man/](doc/man/) |