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

## Economics vs Bitcoin / Zcash / Zero

| Component | Zero | Bitcoin | Zcash |
|-----------|------|---------|-------|
| Base subsidy | 10 ZER (pre-fee) / 10.8 ZER (post-fee) | 50 BTC (historic) | 12.5 ZEC (slow-start era) |
| Halving interval | 800k pre-Blossom, 1.6M post-Blossom | 210k | 840k / 1.68M |
| Founder/dev | **7.5%** of subsidy | None | 20% (ECC+ZF era) |
| Node reward | **20-40%** zeronode | None | None |

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
- **Datadir / wallet:** see table below; wallet file **`wallet.zero`** -- **back up** before upgrades.
- **Proving params:** `zcutil/fetch-params.sh`; see [BUILD_ZERO -- .zero directory](BUILD_ZERO.md#3-zero-directory).

### Default data paths

Replace **`USERNAME`** with your OS login. Platform setup examples: [README](README.md#data-directory-zeroconf-wallet-chain).

| Platform | Data directory | Proving params |
|----------|----------------|----------------|
| **Linux** | `~/.zero` | `~/.zcash-params` |
| **macOS** | `~/Library/Application Support/zero` | `~/Library/Application Support/ZcashParams` |
| **Windows** | `C:\Users\USERNAME\AppData\Roaming\zero` | `C:\Users\USERNAME\AppData\Roaming\ZcashParams` |

- **Tor:** `doc/tor.md`.
- **New addresses:** `getnewaddress` (transparent), `z_getnewaddress sapling` (shielded); list: `getaddressesbyaccount ""`, `z_listaddresses`.

### Block explorer

Mainnet: [https://insight.zeromachine.io/](https://insight.zeromachine.io/) — **Zero Insight** (blocks, transactions, transparent address search).

Source: `insight-ui-zero`, `insight-api-zero`, `bitcore-node-zero`, `bitcore-lib-zero`. Backend **`zerod`** uses **`-experimentalfeatures`**, **`-insightexplorer`**, and **`-txindex`** (see [BUILD_ZERO.md -- Block explorer](BUILD_ZERO.md#462-block-explorer)).

---

## Security

The node is **experimental**; use at your own risk. Back up keys and wallet files. See [README -- Deprecation](README.md#-deprecation-policy) and [Zcash security information](https://z.cash/support/security/).

**2026 Zcash CVEs:** Zero has **no Orchard** and **no `fChecked` Sprout bypass**. Full analysis: **`ZcashFixes.md`**.

---

## Emission totals and chain statistics (Jun 2026)

Consensus-model totals from `GetBlockSubsidy` + 7.5% dev + tiered nodes share (sporks on).

```bash
./contrib/stats/chain_stats.py --cons                  # through chain tip
./contrib/stats/chain_stats.py --cons --thru 2400000   # fixed height
./contrib/stats/chain_stats.py --cons --dev            # dev addr deposited + balance
./contrib/stats/chain_stats.py --verify
./contrib/stats/decode_coinbase.py --heights 2400000
./contrib/stats/decode_coinbase.py --start 2471200 --count 200 --summary
./contrib/stats/chain_stats.py --scan 2471200 200
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--cons` | on | Consensus emission report |
| `--thru HEIGHT` | chain tip | Cumulative through tip, or fixed height |
| `--dev` | off | Dev rotation addresses: model deposited + on-chain balance |
| `--cli PATH` | `src/zero-cli` | RPC client |
| `--verify` | off | Model subsidy sum vs live tip |
| `--scan START COUNT` | off | Coinbase vout histogram |

Split totals (through height 2,400,000):

```
Total:     14,790,161.35 ZER
Miner:    10,600,091.78 ZER
Nodes:    3,390,032.47 ZER
Dev:            800,037.10 ZER
```

Live tip (Jun 2026, height **2,477,766**): **`--verify`** -- model subsidy **~14.895M ZER**; sprout pool **~25,842 ZER**, sapling **~547,065 ZER**. On-chain dev balances need **`zerod`** with `-experimentalfeatures -insightexplorer`.

### Through halving 3 (height 2,400,000 inclusive)

| Component | ZER | Share of subsidy |
|-----------|-----|------------------|
| **Block subsidy (minted)** | **14,790,161.35** | 100% |
| Miner | 10,600,091.78 | 71.67% |
| Nodes (20/25/30% tiers) | 3,390,032.47 | 22.92% |
| Dev (7.5%) | 800,037.10 | 5.41% |

### Subsidy by era (same through 2,400,000)

| Height range | Blocks | Subsidy/block | Era total ZER |
|--------------|--------|---------------|---------------|
| 0 - 412,299 | 412,300 | 10.0 | 4,123,000.00 |
| 412,300 - 799,999 | 387,700 | 10.8 | 4,187,160.00 |
| 800,000 - 1,599,999 | 800,000 | 5.4 | 4,320,000.00 |
| 1,600,000 - 2,399,999 | 800,000 | 2.7 | 2,160,000.00 |
| 2,400,000 | 1 | 1.35 | 1.35 |

### Dev received through height 2,400,000 (by rotation index)

| Index | Address (prefix) | Cumulative ZER |
|-------|------------------|----------------|
| 0 | `t3hmg6WApjq...` | 314,037.00 |
| 1 | `t3hrh5M7eaG...` | 324,000.00 |
| 2 | `t3aWmHqBGS7...` | 162,000.00 |
| 3 | `t3hsi89hPsZ...` | 0.10125 (starts at 2,400,000) |
| 4-9 | (next eras) | 0.00 |

Rotation interval: **800,000** blocks per index (`height / 800000`). Full addresses: **Dev and system addresses** above.

### Grand totals (projected)

| Milestone | Height | Cumulative subsidy ZER |
|-----------|--------|------------------------|
| Halving 3 | 2,400,000 | 14,790,161.35 |
| Dev end | 7,999,999 | 16,933,285.00 (model) |
| Asymptotic cap | gtest `slow_start_subsidy` | **21,000,000** (`MAX_MONEY`) |

Dev share continues until block **7,999,999**; nodes tiers step at each 800k boundary through 40% at 3,200,000+.

### Coinbase layout and dual-miner splits

Typical **3-vout** coinbase: dev P2SH + nodes P2PKH + miner P2PKH.

**4-vout** coinbases (~10% of recent blocks): extra transparent output is **miner payout split** across two t-addresses (pool operator), **not** a fourth protocol fee. Zero has no treasury 4th coinbase output.

Tools: see command table in **Emission totals** above.

### Customary on-chain stats (when node synced)

| RPC | Use |
|-----|-----|
| `getblockchaininfo` | Tip, `valuePools` (sprout/sapling/transparent), `developmentfee` |
| `getblock <hash> 2` | Coinbase vout decode |
| `gettxoutsetinfo` | UTXO set size (requires no pruning) |
| `getmininginfo` | Network hash, difficulty |

Sprout pool on mainnet remains non-zero (historical shielded balance); Sapling is the active wallet generation.

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

Mainnet-verified coinbase behavior and `contrib/stats/decode_coinbase.py` usage: run locally against synced **`src/zerod`**. Dev multisig: **`Zeros/MULTISIG.md`**. Zcash 2026 vulnerabilities: **`ZcashFixes.md`**. Emission tables: **`contrib/stats/chain_stats.py`**.
