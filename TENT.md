# TENT -- lineage, comparison, and remediation plan

Aggregate reference for TENT (masternode zcashd fork) vs Zero Currency. History, open fixes, node operations, P2P, and testnet/regtest validation plans.

Last updated: Jun 2026.

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

TENT left public GitHub for Gitea-style hosting in some eras; treat **TENTOfficial** repos and local **`ZKs/TENT`** tree as code truth when available.

---

## 2. Coinbase and economics (TENT vs Zero)

### TENT typical 4-vout coinbase

1. Founders / dev P2SH
2. Masternode payee P2PKH
3. Miner P2PKH
4. **Treasury** P2SH (protocol fee -- not present on Zero)

### Zero typical 3-vout coinbase

1. Founders 7.5% P2SH (2-of-3 rotation)
2. Zeronode 20-40% P2PKH
3. Miner + fees P2PKH

**4-vout on Zero (~10% of recent blocks):** dual **miner** payout split (pool operator), not treasury.

Code anchor: `TENT/src/masternode-payments.cpp` vs `Zero400/src/zeronode/payments.cpp`.

---

## 3. 2026 Zcash CVE posture

| CVE / issue | TENT | Zero |
|-------------|------|------|
| Orchard counterfeiting (NU6.2) | **N/A** (no Orchard) | **N/A** |
| Sprout `fChecked` (CVE-2026-35679) | **Audit** -- zcashd lineage | **N/A** (no `fChecked` in tree) |

See **`Zero400/ZcashFixes.md`** for full analysis.

---

## 4. TENT upstream fixes as Zero candidates

From **`UpdateZero.md`** TENT table (maintained in parallel):

| ID | TENT behavior | Zero status | Plan |
|----|---------------|-------------|------|
| **TENT-01** | No spurious P2P `Unknown command` after handled MN messages | Zero still logs (`TODO.md`) | **Port** -- log only unhandled commands |
| **TENT-02** | Testnet min-difficulty after height 13000 | Zero: no min-diff rule | **Optional** -- operator decision |
| **TENT-03** | Equihash 144,5 on testnet | Zero 192,7 everywhere | **Document**; no port without NU |
| **TENT-04** | LWMA3 after DIFA height | Zero legacy LWMA | **Evaluate** testnet stability |
| **TENT-05** | Treasury coinbase output | **Removed** in Zero | **Reject** |
| **TENT-06** | Variable founders % | Zero fixed 7.5% | **Reject** |
| **TENT-07** | MN integration tests | Neither tree has them | **Implement on Zero regtest first** |
| **TENT-08** | External `masternode-setup` docs | Obsolete wiki refs | **Replace** with `ZeroNodes.md` |

---

## 5. Planned TENT-side fixes (for TENT maintainers)

Priority sequence if operating a TENT node fork:

1. **Security:** Backport zcashd v6.12.0 Sprout `fChecked` fix; confirm no Orchard code paths.
2. **P2P (TENT-01):** Align extension dispatch logging with TENT `else` branch (no false `Unknown command`).
3. **Docs:** Publish testnet join steps (seeds, ports, faucet) -- Zero gap mirrors this.
4. **Tests:** Regtest masternode payment test (TENT-07 shared gap).
5. **Difficulty (TENT-02/04):** Decide testnet min-diff + LWMA3 vs Zero parity.

---

## 6. Node operations (TENT)

| Item | Typical TENT | Zero reference |
|------|--------------|----------------|
| Collateral | Masternode collateral UTXO | 10,000 ZER zeronode |
| Config | `masternode.conf` | `zeronode.conf` |
| RPC | `masternode start`, `startalias` | `zeronode start`, `startalias` |
| Source map | **`TENTZero.md`** |
| Operator docs | **`Zero400/ZeroNodes.md`** |
| Wallet boundary (Zero-only) | **`Zero400/ZeroNodeDev.md`** |

Operational repos (historical): **TENTOfficial/masternode-setup**. Prefer **`ZeroNodes.md`** for Zero.

---

## 7. P2P improvements

### Known Zero issue (from TENT comparison)

`src/main.cpp` ~7025-7033: zeronode extension commands (`znp`, `znb`, `znget`, `dseg`, spork) handled in subsystems but still emit `Unknown command` when `-debug=net`.

**Fix plan:**

1. Track whether any handler consumed the message.
2. Log `Unknown command` only when no handler matched.
3. Mirror TENT extension dispatch `else` behavior.

### Validation

- Regtest 2-node: enable `-debug=net`; send zeronode messages; assert no spurious unknown log.
- Mainnet peer capture (optional): compare message types during sync.

---

## 8. Testnet and regtest deployment plan

### TENT testnet (upstream)

- P2P port **8233** in upstream params (verify current `chainparams`).
- Optional min-difficulty after height **13000** (TENT-02).
- Equihash **144,5** on testnet post-fork (TENT-03).

### Zero testnet (local tree)

| Network | P2P | RPC | Notes |
|---------|-----|-----|-------|
| testnet | 23802 | 23812 | fee-start height 1; no qa harness |
| regtest | 23803 | 23813 | all automated tests |

### Validation roadmap (shared TENT/Zero methodology)

| Phase | Goal | Harness |
|-------|------|---------|
| **A** | RPC arg validation | Boost `rpc_zeronode_tests` |
| **B** | Regtest coinbase founders + zeronode vouts | New `coinbase_rewards.py` |
| **C** | 2-node zeronode/masternode payment | Manual -> scripted |
| **D** | Reorg + input age | `invalidateblock` regtest |
| **E** | Mock wallet interface | `CZeronodeWalletInterface` double |
| **F** | Mainnet decode regression | `decode_coinbase.py` / `chain_stats.py` |

Document testnet operator bootstrap in **BUILD_ZERO.md** (gap); regtest remains **TEST_ZERO.md**.

---

## 9. Firo (related clone research)

**Firo** is **not** a zcashd Sprout/Sapling/Orchard fork. Privacy uses **Lelantus / Spark**. Zcash 2026 Orchard and Sprout CVEs do **not** apply. Listed alongside TENT in **`ZcashFixes.md`** clone table for ecosystem completeness.

---

## 10. References

| Doc | Path |
|-----|------|
| TENT source file map | **`TENTZero.md`** |
| Zero zeronode hub | `Zero400/ZeroNodes.md` |
| Zero dev interface | `Zero400/ZeroNodeDev.md` |
| CVE analysis | `Zero400/ZcashFixes.md` |
| Coinbase economics | `Zero400/ZERO_COIN.md` |
| Multisig / founders | `Zeros/MULTISIG.md` |
