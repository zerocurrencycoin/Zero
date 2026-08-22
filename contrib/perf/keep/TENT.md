# TENT -- lineage, comparison, and remediation plan

Aggregate reference for TENT (masternode zcashd fork) vs Zero. Identity and TENT-side ops only. Execution catalog: **`UpdateZero.md`** section **3.5**. File map: **`TENTZero.md`**.

TENT HEAD is frozen at **`bcb429b` (2021-11-13)**. Local clone: `~/Work/ZK/ZKs/TENT`.

---

## 1. Identity and history

| Field | TENT | Zero |
|-------|------|------|
| **Upstream** | Zcash + Dash-style masternode | Same lineage; ported to `src/zeronode/` |
| **GitHub org** | [TENTOfficial](https://github.com/TENTOfficial) | [zerocurrencycoin/Zero](https://github.com/zerocurrencycoin/Zero) |
| **Ticker** | TENT | ZER |
| **Launch era** | Post-2017 privacy fork wave | Feb 2017 genesis |
| **Shielded** | Sprout + Sapling (no Orchard) | Sprout + Sapling (no Orchard) |
| **Node layer** | Masternode | Zeronode |
| **Treasury** | **5-10%** extra coinbase vout (4-way split) | **Removed** -- 3-way split only |
| **Founders/dev** | 5% / 7.5% / 15% by upgrade era | Fixed **7.5%** after fee-start |
| **PoW** | Equihash; testnet **144,5** epoch fork | **192,7** mainnet and testnet |

TENT left public GitHub for Gitea-style hosting in some eras; treat **TENTOfficial** repos and local **`ZKs/TENT`** as code truth. Amounts: **`ZERO_COIN.md`**. File map: **`TENTZero.md`**.

---

## 2. Coinbase shape

TENT typical **4-vout** coinbase: founders, masternode, miner, **treasury**. Zero typical **3-vout**: founders 7.5%, zeronode, miner. Extra 4th vout on Zero is dual-miner split, not treasury.

Amounts and scan tools: **`ZERO_COIN.md`**. Payments files: **`TENTZero.md`**.

---

## 3. 2026 Zcash CVE posture

| CVE / issue | TENT | Zero |
|-------------|------|------|
| Orchard counterfeiting (NU6.2) | **N/A** (no Orchard) | **N/A** |
| Sprout `fChecked` (CVE-2026-35679) | **Audit** -- zcashd lineage | **N/A** (no `fChecked` in tree) |

See **`Zero400/ZcashFixes.md`** for full analysis.

---

## 4. Upstream candidates

Do not maintain a second ID table here. **TNT-01..17** live in **`UpdateZero.md`** section **3.5**. Paths: **`ZeroNodeDev.md`** section **4**. File map: **`TENTZero.md`**.

TENT is frozen; there is no TENT-maintainer patch queue in this tree.

---

## 5. Node operations

| Item | Typical TENT | Zero reference |
|------|--------------|----------------|
| Collateral | Masternode collateral UTXO | **`ZeroNodes.md`** |
| Config | `masternode.conf` | `zeronode.conf` |
| RPC | `masternode start`, `startalias` | `zeronode start`, `startalias` |
| Source map | **`TENTZero.md`** |

Historical setup repos: **TENTOfficial/masternode-setup**. Prefer **`ZeroNodes.md`** for Zero.

---

## 6. P2P

Shared Dash-derived inventory: **`~/Work/ZK/ZKs/Comparison.md`** section **4**. Zero else-branch dispatch matches TENT (**TNT-01** done). Deep reorg: **`ZeroNodes.md`** section **6** and **`UpdateZero.md`** section **3.5.1**.

---

## 7. Testnet notes

TENT testnet used min-difficulty after height 13000 and Equihash **144,5** after an epoch fork (**TNT-07**, **TNT-08** -- do not port without a Zero NU). Zero testnet/regtest ports: **`TEST_ZERO.md`**. Zeronode test phases: **`ZeroNodeDev.md`** section **5**.

---

## 8. Firo (related clone research)

**Firo** is **not** a zcashd Sprout/Sapling/Orchard fork. Privacy uses **Lelantus / Spark**. Zcash 2026 Orchard and Sprout CVEs do **not** apply. Listed alongside TENT in **`ZcashFixes.md`** clone table for ecosystem completeness.

---

## 9. References

| Doc | Path |
|-----|------|
| File map | **`TENTZero.md`** |
| TNT catalog | **`UpdateZero.md`** section **3.5** |
| Operator | **`ZeroNodes.md`** |
| Source / tests | **`ZeroNodeDev.md`** |
| CVE | **`ZcashFixes.md`** |
| Economics | **`ZERO_COIN.md`** |
