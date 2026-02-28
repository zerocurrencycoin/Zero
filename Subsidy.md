# Zero Block Subsidy and Halving Algorithm

Zero's subsidy model is more complex than Bitcoin's simple halving, but unlike Zcash has no 25% Founder reward and no slow-start ramp. This document describes the implementation in detail with code references and on-chain actuals.

## 1. Overview

| Component | Zero | Bitcoin | Zcash | Pirate |
|-----------|------|---------|-------|--------|
| Base subsidy | 10 ZER (pre-fee) / 10.8 ZER (post-fee) | 50 BTC | 12.5 ZEC (slow-start) | Asset-chain config |
| Halving interval | 800k pre-Blossom, 1.6M post-Blossom | 210k | 840k / 1.68M | ASSETCHAINS_HALVING |
| Slow start | None | None | 20k blocks | None |
| Founder/dev reward | 7.5% | None | 20% (ECC+ZF) | None |
| Node reward | 20–40% (zeronode) | None | None | Notary pay |
| Blossom scaling | Yes (2× spacing) | N/A | Yes | N/A |

**Actual halving dates (mainnet, from insight.zerocurrency.io):**

| Event | Block | Date (UTC) | Days from genesis | Days since prior |
|-------|-------|------------|-------------------|------------------|
| Genesis | 0 | Feb 20, 2017 19:33:20 | 0 | — |
| Halving 1 | 800,000 | Mar 7, 2020 ~00:53 | ~1,112 | 1,112 |
| Halving 2 | 1,600,000 | Mar 25, 2023 | ~2,223 | ~1,111 |
| Halving 3 | 2,400,000 | ~Apr 10–12, 2026 | ~3,334 | ~1,111 |

Target spacing 120 s → 800k blocks ≈ 1,111 days (3.04 years). Actual intervals match closely.

---

## 2. Consensus Constants

**Location:** `src/consensus/params.h:79–87`

| Constant | Value |
|----------|-------|
| PRE_BLOSSOM_POW_TARGET_SPACING | 120 s |
| POST_BLOSSOM_POW_TARGET_SPACING | 60 s |
| BLOSSOM_POW_TARGET_SPACING_RATIO | 2 |
| PRE_BLOSSOM_HALVING_INTERVAL | 800000 |
| PRE_BLOSSOM_REGTEST_HALVING_INTERVAL | 150 |
| POST_BLOSSOM_HALVING_INTERVAL | 1,600,000 |
| POST_BLOSSOM_REGTEST_HALVING_INTERVAL | 300 |

**Blossom activation:** `NO_ACTIVATION_HEIGHT` on main, testnet, regtest — pre-Blossom formula applies everywhere.

---

## 3. Base Block Subsidy

**Location:** `src/main.cpp:2109`

```cpp
CAmount GetBlockSubsidy(int nHeight, const Consensus::Params& consensusParams)
{
  CAmount nSubsidy = 10 * COIN;
  if (nHeight>=consensusParams.nFeeStartBlockHeight) {
    nSubsidy = 10.8 * COIN;
  }

    int halvings = consensusParams.Halving(nHeight);
    if (halvings >= 64)
        return 0;

    if (consensusParams.NetworkUpgradeActive(nHeight, Consensus::UPGRADE_BLOSSOM)) {
        return (nSubsidy / Consensus::BLOSSOM_POW_TARGET_SPACING_RATIO) >> halvings;
    } else {
        return nSubsidy >> halvings;
    }
}
```

- **Pre-fee** (height < nFeeStartBlockHeight): 10 ZER base
- **Post-fee**: 10.8 ZER base
- **Halvings**: Right-shift; subsidy → 0 when halvings ≥ 64
- **Blossom**: Post-Blossom divides by BLOSSOM_POW_TARGET_SPACING_RATIO (2) before halving → effective base 5.4 ZER

---

## 4. Reward Transition Block (nFeeStartBlockHeight)

**Location:** `src/chainparams.cpp:87, 258, 418`

| Network | nFeeStartBlockHeight |
|---------|----------------------|
| Main | 412300 |
| Testnet | 1 |
| Regtest | 5000 |

**Single transition at block 412,300 (mainnet):**
- Base subsidy: 10 → 10.8 ZER
- Founders reward: starts (7.5% of block subsidy)
- Zeronode: no height gate; spork-controlled; percentage tiers use nPreBlossomSubsidyHalvingInterval (800k)

**Validation:** `main.cpp:4503` — coinbase must include founders output when `nHeight >= nFeeStartBlockHeight && nHeight <= GetLastFoundersRewardBlockHeight(nHeight)`.

---

## 5. Halving Function

**Location:** `src/consensus/params.cpp:14`

```cpp
int Params::Halving(int nHeight) const {
    if (NetworkUpgradeActive(nHeight, Consensus::UPGRADE_BLOSSOM)) {
        int64_t blossomActivationHeight = vUpgrades[Consensus::UPGRADE_BLOSSOM].nActivationHeight;
        int64_t scaledHalvings = ((blossomActivationHeight - SubsidySlowStartShift()) * Consensus::BLOSSOM_POW_TARGET_SPACING_RATIO)
            + (nHeight - blossomActivationHeight);
        return (int) (scaledHalvings / nPostBlossomSubsidyHalvingInterval);
    } else {
        return nHeight / nPreBlossomSubsidyHalvingInterval;
    }
}
```

**Zero-specific:** `nSubsidySlowStartInterval` is not set in chainparams → defaults to 0 → `SubsidySlowStartShift() = 0`. No slow start. Pre-Blossom: `halvings = nHeight / 800000`.

---

## 6. GetLastFoundersRewardBlockHeight

**Location:** `src/consensus/params.cpp:35`

```cpp
int Params::GetLastFoundersRewardBlockHeight(int nHeight) const {
    // zip208: max({ height : N | Halving(height) < 1 })
    // H := blossom activation; SS := SubsidySlowStartShift(); R := BLOSSOM_POW_TARGET_SPACING_RATIO
    bool blossomActive = NetworkUpgradeActive(nHeight, Consensus::UPGRADE_BLOSSOM);
    if (blossomActive) {
        int blossomActivationHeight = vUpgrades[Consensus::UPGRADE_BLOSSOM].nActivationHeight;
        return blossomActivationHeight + nPostBlossomSubsidyHalvingInterval
            - (blossomActivationHeight - SubsidySlowStartShift()) * BLOSSOM_POW_TARGET_SPACING_RATIO - 1;
    } else {
        return (nPreBlossomSubsidyHalvingInterval*10)  - 1;
    }
}
```

**Pre-Blossom:** `800000*10 - 1 = 7,999,999`

**Height validation:** `chainparams.cpp:606, 623` — `GetFoundersRewardScriptAtHeight` / `GetFoundersRewardAddressAtHeight` require `nFeeStartBlockHeight <= nHeight <= GetLastFoundersRewardBlockHeight(nHeight)`; otherwise return null/OP_RETURN.

---

## 7. Founders Reward (7.5%)

**Location:** `src/zeronode/payments.cpp:306–320`, `src/zeronode/budget.cpp:536–545`

```cpp
CAmount vFoundersReward = blockValue * 7.5 / 100;
```

**Applied when:** `nHeight >= nFeeStartBlockHeight && nHeight <= GetLastFoundersRewardBlockHeight(nHeight)`.

**Recipient:** `Params().GetFoundersRewardScriptAtHeight(nHeight)` — rotates through `vFoundersRewardAddress` by height.

---

## 8. Zeronode Payments (20–40%)

**Location:** `src/main.cpp:2129`

```cpp
int64_t GetZeronodePayment(int nHeight, int64_t blockValue, int nZeronodeCount)
{
    int64_t ret = blockValue * 20 / 100;
    if (IsSporkActive(SPORK_7_ZERONODE_PAYMENT_ENABLED)) {
      if (IsSporkActive(SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED)) {
        if(nHeight >= nPreBlossomSubsidyHalvingInterval * 1) ret = blockValue * 25 / 100;
        if(nHeight >= nPreBlossomSubsidyHalvingInterval * 2) ret = blockValue * 30 / 100;
        if(nHeight >= nPreBlossomSubsidyHalvingInterval * 3) ret = blockValue * 35 / 100;
        if(nHeight >= nPreBlossomSubsidyHalvingInterval * 4) ret = blockValue * 40 / 100;
      } else {
        ret = 100000;
      }
    } else {
      ret = 0;
    }
    return ret;
}
```

| Height | Zeronode % (SPORK_6 + SPORK_7) |
|--------|--------------------------------|
| < 800k | 20% |
| ≥ 800k | 25% |
| ≥ 1.6M | 30% |
| ≥ 2.4M | 35% |
| ≥ 3.2M | 40% |

Without SPORK_6: fixed 100,000 zatoshis. Without SPORK_7: 0.

---

## 9. Block Payee Flow

**Location:** `src/zeronode/payments.cpp:260–269`

```cpp
void FillBlockPayee(CMutableTransaction& txNew, CAmount nFees, CTxOut& txFounders, CTxOut& txZeronodes)
{
    if (IsSporkActive(SPORK_13_ENABLE_SUPERBLOCKS) && budget.IsBudgetPaymentBlock(pindexPrev->nHeight + 1))
        budget.FillBlockPayee(txNew, nFees, txFounders, txZeronodes);
    else
        zeronodePayments.FillBlockPayee(txNew, nFees, txFounders, txZeronodes);
}
```

**CZeronodePayments::FillBlockPayee** (`payments.cpp:281`):
1. `blockValue = GetBlockSubsidy(nHeight, Params().GetConsensus())`
2. `zeronodePayment = GetZeronodePayment(nHeight, blockValue)`
3. `vFoundersReward = blockValue * 7.5 / 100`
4. Miner: `blockValue - vFoundersReward - zeronodePayment + nFees`
5. Append founders and zeronode outputs when applicable

**CBudgetManager::FillBlockPayee** (`budget.cpp:506`): Same founders logic; zeronode amount from winning finalized budget.

**Miner:** `miner.cpp:415` — `CreateNewBlock` calls `FillBlockPayee` after setting coinbase from block subsidy.

---

## 10. Example: Block 2,382,565

- **Halvings:** 2,382,565 / 800,000 = 2 → subsidy = 10.8 >> 2 = **2.7 ZER**
- **Founders:** 2.7 × 7.5% = **0.2025 ZER**
- **Zeronode:** 30% (height ≥ 1.6M, < 2.4M) → **0.81 ZER**
- **Miner:** 2.7 − 0.2025 − 0.81 = **1.6875 ZER** + fees
- **Next halving:** block 2,400,000 (~17,435 blocks ≈ 24 days at 120 s)

---

## 11. Total Supply

**Formula (mainnet, nFeeStartBlockHeight = 412300):**

- **Pre-fee** [0, 412299]: 412,300 × 10 = **4,123,000 ZER**
- **First 800k period** [412300, 799999]: 387,700 × 10.8 = **4,187,160 ZER**
- **Halving chain** [800k → 51.2M]: 10.8 × 800,000 × (1 + ½ + ¼ + … + ½⁶³) ≈ 10.8 × 800,000 × 2 = **17,280,000 ZER**

**Total ≈ 25,590,160 ZER ≈ 25.6M ZER**

| Era | Block range | Count | Subsidy/block | Total |
|-----|-------------|-------|---------------|-------|
| 0a | [0, 412300) | 412,300 | 10 | 4,123,000 |
| 0b | [412300, 800k) | 387,700 | 10.8 | 4,187,160 |
| 1 | [800k, 1.6M) | 800,000 | 5.4 | 4,320,000 |
| 2 | [1.6M, 2.4M) | 800,000 | 2.7 | 2,160,000 |
| … | … | 800,000 each | halves | … |
| 63 | [50.4M, 51.2M) | 800,000 | 10.8/2⁶³ | ~0 |

**Sum to block 2,382,565:** ~14.74M ZER (excluding fees). CoinGecko/insight-api-zero circulating supply ~14.65M.

**Note:** Zero's total supply (~25.6M ZER) exceeds `MAX_MONEY` (16.95M ZER in `amount.h`). `subsidy_limit_test` validates each block subsidy with `MoneyRange(nSubsidy)` rather than the cumulative sum.

### 11.1 For Later Review

| Location | Issue |
|----------|-------|
| `src/amount.h` | `MAX_MONEY = 1695014989600000` (16.95M ZER in zatoshi). Zero total supply ~25.6M ZER exceeds this; validation uses per-subsidy `MoneyRange` only. |
| (removed) | `338665500000000` — outdated total subsidy (zatoshi); Zero total ≈ 2.56e15. |
| `TODO.md` | Same `338665500000000` reference. |
| `TEST.md` | Same `338665500000000` reference. |
| `README.md` | "Stable supply is 3888 ZER, after first halfing" — ambiguous; 3888 ≈ daily emission (720×5.4) after first halving, not total supply. |
| `doc/tor.md` | `"subver" : "/MagicBean:1.0.0/"` — legacy; Zero uses Ambrym. |

### 11.2 RPC Python tests (`qa/rpc-tests/`)

| File | Status |
|------|--------|
| `test_framework/blocktools.py` | Fixed: 10 ZER, halving 150, 7.5% founder from block 5000. |
| `test_framework/util.py` | Fixed: Zero branch IDs (6f76727a, 7361707a). |
| `blockchain.py` | Fixed: total_amount 1745 (149×10 + 51×5), txouts 200. |
| `README.md` | Fixed: ZEC → ZER. |
| `zcjoinsplitdoublespend.py` | Fixed: ZEC → ZER. |
| `invalidblockrequest.py` | Fixed: tx amounts 9 ZER for 10 ZER coinbase. |
| `wallet.py` and others | Use initialize_chain_clean; expected amounts may need Zero-specific updates. |

---

## 12. Consensus Validation

**Location:** `src/main.cpp:4503`

```cpp
if ((nHeight >= consensusParams.nFeeStartBlockHeight) && (nHeight <= consensusParams.GetLastFoundersRewardBlockHeight(nHeight))) {
    // Must find output: scriptPubKey == GetFoundersRewardScriptAtHeight(nHeight)
    //                   nValue == GetBlockSubsidy(nHeight, ...) * 0.075
    if (!found) return state.DoS(100, error("founders reward missing"), REJECT_INVALID, "cb-no-founders-reward");
}
```

---

## 13. Comparison with Other Chains

**Bitcoin** (`validation.cpp:1922`): `halvings = nHeight / 210000`; 50 BTC >> halvings; no slow start, no founder/node reward.

**Zcash:** 20% founder reward; slow start 20k blocks, `SubsidySlowStartShift = 10000`; pre-Blossom `(height - SS) / 840000`; post-Blossom scaled; funding streams (ZIP 214) in later versions.

**Pirate** (`main.cpp:2942`): `komodo_ac_block_subsidy(nHeight)`; asset-chain params `ASSETCHAINS_HALVING`, `ASSETCHAINS_REWARD`, etc.; multi-era model in `komodo_utils.cpp:822`.

---

## 14. Test and Log References

**Tests:** `main_tests.cpp` — `block_subsidy_test`, `subsidy_limit_test` skipped for Zero (`UsesReferenceSubsidyModel`); `test_foundersreward.cpp` — `regtest_get_last_block_blossom`, `regtest`; `blocktools.py:55` — regtest halvings `(counter+heightAdjust)/150`.

**Logs:** `payments.cpp:331–337` — `Zeronode payment to %s`, `Total miner to %s`, `Total founder to %s`, `Total zero node to %s`, `Total Coinbase to %s`.

---

## 15. Addresses and Keys in Code

Reference of hardcoded addresses and keys, their locations, and purpose.

### 15.1 Founders Reward (Developer Fund) Addresses

**Location:** `src/chainparams.cpp:230–241` (mainnet), `390–402` (testnet), `530` (regtest)

**Purpose:** 7.5% of block subsidy; rotates by block height via `GetFoundersRewardAddressAtHeight()`.

| Network | Addresses |
|---------|-----------|
| **Mainnet** | `t3hmg6WApjqVFw9oPWTDy4JLEqXcUWthg5v`, `t3hrh5M7eaGA5zXCitPXz2pbe146GkVPWHs`, `t3aWmHqBGS7watoKQLa7uykeTaYHoYqM361`, `t3hsi89hPsZzmnbs3pny6cfAxMxV5TJLErj`, `t3TdGxPVUdMXd6qDrDCEuJETLadZ9Ki3s9r`, `t3cb5ZjKmbGbqDaYk97Auam9kXXikGQBmyY`, `t3V1YovGUPW9WSBoAHS48FDdUfUTo6LDpZR`, `t3KB9n28MVg31oo856t1tQGfJuYq8usTvSi`, `t3dqSV4YGj5V3WjQhqFGrKTMUf9Tgc6xnJM`, `t3aJkYT1i6tyytq8J6khPaDNtgZsBSXgfBf` |
| **Testnet** | `t2BEnZwurNtPyhyWdZ82zTdS93rKyoUpgMJ`, `t2AwNRubry4rQrEvHwAdpYve4Gz5cSmjGXA`, … (10 addresses) |
| **Regtest** | `t2FwcEhFdNXuFMv1tcYwaBJtYVtMj8b1uTg` |

**RPC:** `getblockchaininfo` exposes as `developmentfee` (`src/rpc/zeronode.cpp:1123`).

### 15.2 Zeronode Dummy Addresses

**Location:** `src/chainparams.cpp:146` (mainnet), `317` (testnet), `471` (regtest)

**Purpose:** Output address for a validation-only transaction. Used when verifying Zeronode 10,000 ZER collateral: code builds a fake tx (vin = collateral, vout = 9999.99 ZER to dummy), runs `AcceptableInputs()`; tx is never broadcast. The dummy address must be valid for script construction but receives no real funds.

| Network | Address |
|---------|---------|
| **Mainnet** | `t1TLNF3seMZennWmmxik8r1PVEKj5zudgRw` |
| **Testnet** | `tmWuQ8Yh3pHDa8MingmN8ECPRBxo2n8uZRs` |
| **Regtest** | `s1eQnJdoWDhKhxDrX8ev3aFjb1J6ZwXCxUT` |

**Usage:** `src/zeronode/zeronode.cpp:203, 570` → `GetTestingCollateralScript(Params().ZeronodeDummyAddress(), scriptPubKey)`.

### 15.3 ZeroWallet Donation Address

**Location:** `zerowallet/src/settings.cpp:490, 568`

**Purpose:** Donation / zboard address shown in ZeroWallet UI.

| Network | Address |
|---------|---------|
| **Mainnet** | `t1fDbALrS7tZV7DDvadAT7yHi5Sztptj8yP` |
| **Testnet** | `ztestsaplingXXX` (placeholder) |

### 15.4 Test Private Keys (zerod)

**Location:** `src/test/rpc_tests.cpp:132–133`

**Purpose:** WIF keys for multisig signing in regtest; used to sign a raw transaction in `rpc_signrawtransaction` test.

| Key (WIF) |
|-----------|
| `KzsXybp9jX64P5ekX1KUxRQ79Jht9uzW7LorgwE65i5rWACL6LQe` |
| `Kyhdf5LuKTRx4ge69ybABsiUAWjVRK4XGxAKk2FQLp2HjGMy87Z4` |

**Location:** `qa/rpc-tests/sprout_sapling_migration.py:15`

**Purpose:** Regtest extended key for Sprout→Sapling migration tests.

| Key |
|-----|
| `secret-extended-key-regtest1qv62zt2fqyqqpqrh2qzc08h7gncf4447jh9kvnnnhjg959fkwt7mhw9j8e9at7attx8z6u3953u86vcnsujdc2ckdlcmztjt44x3uxpah5mxtncxd0mqcnz9eq8rghh5m4j44ep5d9702sdvvwawqassulktfegrcp4twxgqdxx4eww3lau0mywuaeztpla2cmvagr5nj98elt45zh6fjznadl6wz52n2uyhdwcm2wlsu8fnxstrk6s4t55t8dy6jkgx5g0cwpchh5qffp8x5` |

### 15.5 Alert Signing Key

**Location:** `src/test/alert_tests.cpp:39–41` (references `alertkeys.h`, not committed)

**Purpose:** Signs `CAlert` for network alert tests. Key must be in `alertkeys.h`; file is gitignored and must not be committed.

**Note:** The P2P alert system is long outdated and likely deprecated. **Bitcoin:** Retirement announced Nov 2016; final disabling alert Jan 2017; code removed (PR #7692). **Zcash (upstream):** Removed P2P alert system Aug 2025 (commit cc6e096); deleted `alertkeys.h`, `sendalert.cpp`, `alert_tests.cpp`; kept `-alertnotify` and deprecation/fork detection. Zero inherited the legacy from Zcash; uses a placeholder key and has disabled signature checks in tests (`alert_tests.cpp`).

### 15.6 Inspecting and generating wallet addresses

Wallet T- and Z-addresses are created at runtime by zerod when RPCs are invoked (e.g. by ZeroWallet on first connect or when the user requests a new address). They are not hardcoded.

**List addresses:** RPC `getaddressesbyaccount ""` (T-addresses), `z_listaddresses` (Z-addresses). CLI: `zero-cli getaddressesbyaccount ""`, `zero-cli z_listaddresses`.

**Request new keys:** RPC `getnewaddress` (T), `z_getnewaddress sapling` (Z). CLI: `zero-cli getnewaddress`, `zero-cli z_getnewaddress sapling`.
