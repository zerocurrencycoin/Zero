# ZeroCoin — Chain, coin, and operations reference

Single reference for all chain history, consensus and economic parameters, subsidy, halving, zeronodes, supply, operations, addresses, and security. Fill from Subsidy.md, README.md, doc/, UpdateZero.md, block explorers, and operators.

**Audience:** Miners, pool operators, node operators, exchanges, DEX, developers.

---

## 1. Purpose and audience

| Audience | Use case |
|----------|----------|
| Miners / pools | Block reward, halving schedule, zeronode share (20–40%), payout expectations, stratum/API. |
| Node operators | Network params, RPC, pruning, sync, resource requirements. |
| Exchanges / DEX | Listing requirements, supply, emission, post-halving economics. |
| Developers | Consensus rules, subsidy curve, founders reward, addresses in code, upgrade process. |

---

## 2. Chain history and stages

*Fill from: Subsidy.md, README, UpdateZero.md, repo tags.*

- **Genesis / launch:** Block 0 date, mainnet parameters.
- **Major upgrades / hard forks:** Dates, block heights, rule changes (subsidy, zeronodes).
- **Halving schedule:** Block heights and dates for each halving; block reward before/after.
- **References:** Repo tags, Subsidy.md, UpdateZero.md.

---

## 3. Consensus and economic parameters

*Fill from: Subsidy.md, consensus code, src/amount.h.*

- **Block time, difficulty, max supply.**
- **Block subsidy:** Curve (initial reward, halving interval). Founders reward (e.g. 7.5%); correct value per Subsidy.md §11.3, UpdateZero §5.
- **Zeronode payments:** Percentage range (e.g. 20–40%), eligibility, lock/commit rules.
- **MAX_MONEY / MoneyRange:** Per-subsidy validation; total supply (~25.6M ZER) vs cap (amount.h). Document or align.
- **Supply clarification:** README “3888 ZER” — clarify total supply vs daily emission (e.g. 720×5.4); fix ambiguity.

---

## 4. Block subsidy and halving

*Fill from: Subsidy.md.*

- Block reward curve; halving interval and block heights.
- Founders reward (correct value; fix §11.3 discrepancy if any).
- Dates and heights for each halving; reward before/after.

---

## 5. Zeronode payments

*Fill from: Subsidy.md, pool/node operator input.*

- Percentage range (e.g. 20–40%); eligibility; lock/commit rules.
- Payout flow; pool/node operator impact.

---

## 6. Supply and distribution

*Fill from: Subsidy.md, consensus, block explorers.*

- Total supply (~25.6M ZER); MAX_MONEY vs per-subsidy validation.
- Circulating supply; emission rate (ZER/day or per block).
- “3888 ZER”: state clearly whether daily emission or total supply (see §3).

---

## 7. Distributions and performance

*Fill from: block explorers, pool/node data.*

- Supply distribution: circulating, emission rate, locked/unlocked.
- Network performance: typical block times, hashrate (if public), difficulty trend.
- Utilization: active addresses, tx volume, zeronode count (if tracked). Data source and update frequency.

---

## 8. Post-halving expectations

*Fill from: Subsidy.md, observed data. Label assumptions vs observed.*

- Next halving: block height and estimated date; new block reward; impact on emission rate.
- Expected results: supply growth rate, miner/pool economics, stability notes.

---

## 9. Operational reference

*Fill from: README, doc/, contrib/ configs, pool docs.*

- **Node / RPC:** Ports, config examples (e.g. contrib/zero.conf), pruning, reindex. Link to README or doc/.
- **Miners / pools:** Stratum, payout frequency, zeronode share handling. Link to pool docs.
- **Wallets:** zerowallet, zero-cli; recommended binaries and versions for mainnet.
- **Privacy / tor:** doc/tor.md — subver (update from legacy MagicBean to Gaua/Ambrym if applicable).

---

## 10. Addresses and keys (wallet-relevant)

*Fill from: Subsidy.md §15.*

- ZeroWallet donation address (zerowallet settings refs).
- Wallet RPCs: getnewaddress, z_getnewaddress.
- Other addresses in code (Subsidy.md §15 as needed).

---

## 11. Security and upgrades

*Fill from: UpdateZero.md, consensus process.*

- **Consensus-critical:** Upgrade process, activation heights, rollback policy (if any).
- **P2P alert code:** alertkeys.h, sendalert.cpp, alert_tests.cpp — Zcash removed Aug 2025; document Zero’s decision (keep or remove) here or in Subsidy.md §15.5.
- **Warnings:** Experimental status, backup, key custody. Link to security docs.

---

## 12. Content guidelines

- **Cite sources:** Every number from Subsidy.md, consensus, or stated data source (explorer, pool).
- **Date vs block height:** Prefer both where relevant (e.g. “Halving at block N (approx. YYYY-MM-DD)”).
- **No speculation:** Distinguish “planned” vs “current” vs “observed.”
- **Limitations:** State when data is estimated, self-reported, or from a single source.
- **Sensitivity:** Omit or keep internal: price, adoption claims, legal/regulatory, commercial terms until approved for publication.

---

## 13. Relation to other docs (Zero repo)

| Document | Role |
|----------|------|
| Subsidy.md | Source of truth for subsidy, halving, founders, zeronodes. ZeroCoin.md reflects it for external reference. |
| UpdateZero.md | Project status, plans, triage (e.g. detected issues from zerowallet). |
| README.md | High-level; link to ZeroCoin.md for full chain/coin/ops reference. |
| doc/ | Operational how-to; ZeroCoin.md can link into specific doc/ files. |

---

## 14. Maintenance

- **Update triggers:** Each halving; major releases; material change to subsidy or zeronode rules.
- **Owner:** Zero project / node repo maintainers.
- **Review:** Technical reviewers, pool operators, (if applicable) exchange contacts before major releases.
