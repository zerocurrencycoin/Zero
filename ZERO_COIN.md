# ZERO_COIN

Chain economics and consensus parameters of the Zero mainnet, for miners, pools, exchanges, and integrators. Amounts are computed with the integer arithmetic of the code (`GetBlockSubsidy`, `GetFoundersRewardAmount`, `GetZeronodePayment` in `src/main.cpp`) and checked against the chain; 1 ZER = 100,000,000 zatoshis.

---

## Chain

| Parameter | Value |
|-----------|-------|
| Genesis | 2017-02-19 10:26:40 UTC, `068cbb5db6bc11be5b93479ea4df41fa7e012e92ca8603c315f9b1a2202205c6`; pays no coins |
| Proof of work | Equihash (192,7), personalization `ZERO_PoW`; Zcash uses (200,9) |
| Block spacing | 120 s target |
| Difficulty adjustment | Digishield per block (`GetNextWorkRequired`, `CalculateNextWorkRequired` in `src/pow.cpp`): mean target of the last 17 blocks, scaled by their median-time-past timespan dampened by 4 and bounded to 90-130% of 17 x 120 s (`nPowAveragingWindow` 17, `nPowMaxAdjustUp` 10, `nPowMaxAdjustDown` 30); Zcash uses 17, 16, 32 |
| Coinbase maturity | 720 blocks |
| Ports | P2P 23801, RPC 23811 (testnet 23802 and 23812, regtest 23803 and 23813) |

| Network upgrade | Mainnet height | Branch ID |
|-----------------|----------------|-----------|
| Overwinter and Sapling | 492,850 (2019-01-05) | `0x6f76727a`, `0x7361707a` |
| Cosmos | 620,450 (2019-07-02) | `0x7361707a`, the Sapling ID |
| Blossom | not scheduled | -- |

Signers take the branch ID for a height from `getblockchaininfo`. Shielded addresses are Sapling; the Sprout pool still holds coins from before Sapling.

---

## Block subsidy

| Heights | Base subsidy |
|---------|--------------|
| 1 to 412,299 | 10 ZER |
| From 412,300 (fee-start) | 10.8 ZER |

The subsidy is the base shifted right once per 800,000 blocks (`height / 800,000` halvings). At halving 30 it is 1 zatoshi; from halving 31, height 24,800,000, it is 0. Fee-start on testnet is height 1, on regtest 1000. The code divides the base by 2 under Blossom, which is not scheduled.

---

## Coinbase split

The coinbase pays the subsidy plus fees and no more (`ConnectBlock`); the shares below come out of the subsidy and do not add coins.

1. **Development fee:** 7.5% of the subsidy (`subsidy * 75 / 1000`, truncated) from fee-start through height 7,999,999, to a P2SH address that rotates every 800,000 blocks (Addresses).
2. **Zeronode payment:** a share of the subsidy by height, enforced on mainnet since block 620,426 (2019-07-02); the network-wide switches are in doc/zeronodes.md "Sporks".

   | Heights | Zeronode share |
   |---------|----------------|
   | Below 800,000 | 20% |
   | From 800,000 | 25% |
   | From 1,600,000 | 30% |
   | From 2,400,000 | 35% |
   | From 3,200,000 | 40% |

3. **Miner:** the rest, plus fees.

**For pools.** `getblocktemplate` returns the complete coinbase in `coinbasetxn`, with the development fee (`foundersreward`) and the zeronode output (`payee`, `payee_amount`); `getblocksubsidy` reports `miner` already net of the development fee, with the zeronode share still in it. A coinbase built from these fields that pays less than the template is accepted, and the difference is lost.

Example at height 2,500,000: subsidy 10.8 >> 3 = 1.35 ZER; development fee 0.10125; zeronode 35% = 0.4725; miner 0.77625 plus fees. A typical coinbase has three outputs: development fee, zeronode, miner. A fourth output is a pool splitting its miner payout.

**Naming.** The development fee runs on the founders-reward code inherited from Zcash (`GetFoundersRewardAmount`, `vFoundersRewardAddress`), so `getblocksubsidy` and block templates call it `founders`, and `zeronodestats` calls it `developmentfee`. It differs from Zcash's founders reward, which took 20% of the subsidy for Zcash's first four years.

---

## Emission

| Date (UTC) | Height | Event | Base subsidy |
|------------|--------|-------|--------------|
| 2017-02-19 | 0 | Genesis, no coins | -- |
| 2018-09-15 | 412,300 | Fee-start: development fee begins | 10.8 ZER |
| 2019-07-02 | 620,426 | Zeronode payee enforced | 10.8 ZER |
| 2020-03-07 | 800,000 | Halving 1 | 5.4 ZER |
| 2023-03-26 | 1,600,000 | Halving 2 | 2.7 ZER |
| 2026-03-12 | 2,400,000 | Halving 3 | 1.35 ZER |
| About 2029 | 3,200,000 | Halving 4 | 0.675 ZER |
| -- | 7,999,999 | Last development fee | -- |
| -- | 24,800,000 | Subsidy reaches 0 (halving 31) | -- |

| Through height | Minted | Development fee | Zeronode share | Miner share |
|----------------|--------|-----------------|----------------|-------------|
| 2,400,000 | 14,790,151.35 | 800,037.10 | 3,390,030.47 | 10,600,083.78 |
| 7,999,999 | 16,933,275.00 | 960,771.37 | 4,193,280.00 | 11,779,223.63 |
| 24,800,000 (all) | **16,950,149.896** | 960,771.368 | 4,200,029.872 | 11,789,348.656 |

The zeronode and miner columns apply the zeronode tiers from height 1. On the chain, zeronode outputs began with the spork switches in 2019 (blocks 594,334 to 620,426); the 1,274,150.16 ZER that the tiers assign to heights 1 to 620,425 went to miners or was not claimed.

**Maximum supply.** 16,950,149.896 ZER, the sum of the subsidy over all heights. `MAX_MONEY` in `src/amount.h` has exactly this value, and GTest `founders_reward_test.slow_start_subsidy` asserts that the subsidy sum equals it. Validation applies `MoneyRange` (0 to `MAX_MONEY`) to each output and value balance.

**Supply on the chain** at height 2,568,279 is 1,781 ZER below the schedule (`getsupply`): coinbases claimed less than allowed, mostly through misconfigured pool software, and consensus accepts a short coinbase without creating the difference.

`contrib/stats/chain_stats.py` and `contrib/stats/decode_coinbase.py` recompute these figures from a synced node.

---

## Addresses

**Encodings**, from `base58Prefixes` and `bech32HRPs` in `src/chainparams.cpp`. Mainnet uses Zcash's encodings unchanged, so a Zero address cannot be told from a Zcash address by its form; a wallet must know the network.

| Kind | Mainnet | Testnet | Regtest |
|------|---------|---------|---------|
| Transparent P2PKH | `1C B8`, `t1...` | `1D 25`, `tm...` | As testnet |
| Transparent P2SH | `1C BD`, `t3...` | `1C BA`, `t2...` | As testnet |
| Private key (WIF) | `80`, `K...` or `L...` | `EF`, `c...` | As testnet |
| BIP32 extended public, private key | `04 88 B2 1E`, `04 88 AD E4` | `04 35 87 CF`, `04 35 83 94` | As testnet |
| Sprout address, viewing key, spending key | `zc...`, `ZiVK...`, `SK...` | `zt...` and testnet prefixes | As testnet |
| Sapling address | `zs` | `ztestsapling` | `zregtestsapling` |
| Sapling full, incoming viewing key | `zviews`, `zivks` | `zviewtestsapling`, `zivktestsapling` | `zviewregtestsapling`, `zivkregtestsapling` |
| Sapling extended spending key, full viewing key | `secret-extended-key-main`, `zxviews` | `secret-extended-key-test`, `zxviewtestsapling` | `secret-extended-key-regtest`, `zxviewregtestsapling` |
| BIP44 coin type (`bip44CoinType`) | 323 (SLIP-44) | 1 | 1 |

**Development fee**, by rotation index (`height / 800,000`):

| Index | Address | Lifetime ZER |
|-------|---------|--------------|
| 0 | `t3hmg6WApjqVFw9oPWTDy4JLEqXcUWthg5v` | 314,037.00 (from fee-start) |
| 1 | `t3hrh5M7eaGA5zXCitPXz2pbe146GkVPWHs` | 324,000.00 |
| 2 | `t3aWmHqBGS7watoKQLa7uykeTaYHoYqM361` | 162,000.00 |
| 3 | `t3hsi89hPsZzmnbs3pny6cfAxMxV5TJLErj` | 81,000.00 |
| 4 | `t3TdGxPVUdMXd6qDrDCEuJETLadZ9Ki3s9r` | 40,500.00 |
| 5 | `t3cb5ZjKmbGbqDaYk97Auam9kXXikGQBmyY` | 20,250.00 |
| 6 | `t3V1YovGUPW9WSBoAHS48FDdUfUTo6LDpZR` | 10,125.00 |
| 7 | `t3KB9n28MVg31oo856t1tQGfJuYq8usTvSi` | 5,062.496 |
| 8 | `t3dqSV4YGj5V3WjQhqFGrKTMUf9Tgc6xnJM` | 2,531.248 |
| 9 | `t3aJkYT1i6tyytq8J6khPaDNtgZsBSXgfBf` | 1,265.624 |

Testnet and regtest addresses: `vFoundersRewardAddress` in `src/chainparams.cpp`.

**Zeronode dummy address**, used to build validation-only transactions for the 10,000 ZER collateral check: mainnet `t1TLNF3seMZennWmmxik8r1PVEKj5zudgRw`, testnet `tmWuQ8Yh3pHDa8MingmN8ECPRBxo2n8uZRs`, regtest `s1eQnJdoWDhKhxDrX8ev3aFjb1J6ZwXCxUT`.

**ZeroWallet donation address**, published with the desktop wallet: `t1fDbALrS7tZV7DDvadAT7yHi5Sztptj8yP`.

---

## Comparison

| | Zero | Zcash | Bitcoin |
|-|------|-------|---------|
| Proof of work | Equihash (192,7) | Equihash (200,9) | SHA-256d |
| Block spacing | 120 s | 150 s, 75 s after Blossom | 600 s |
| Initial subsidy | 10 ZER, 10.8 from fee-start | 12.5 ZEC after slow start | 50 BTC |
| Halving interval | 800,000 blocks | 840,000, 1,680,000 after Blossom | 210,000 |
| Maximum supply | 16,950,149.896 ZER | 21,000,000 ZEC | 21,000,000 BTC |
| Protocol share | 7.5% development fee from height 412,300; 20 to 40% zeronodes | 20% founders reward for four years, then the development fund | None |

Protocol specification of the Zcash family: [Zcash Protocol Specification](https://zips.z.cash/protocol/protocol.pdf).
