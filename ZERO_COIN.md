# ZERO_COIN — User-observable chain and node

Reference for **what the Zero network and this node do** from an operator and integrator perspective: economics visible on-chain, heights and dates, ports and operational facts, and how that differs from upstream where it matters.

**Not in scope here:** build instructions (**[BUILD_ZERO.md](BUILD_ZERO.md)**), tests (**[TEST_ZERO.md](TEST_ZERO.md)**), implementation walkthroughs, or maintainer planning docs at the repo root.

**Document status:** Section-by-section narrative is still outlined in **[ZeroCoin.md](ZeroCoin.md)**; subsidy formulas and code-accurate tables remain in **[Subsidy.md](Subsidy.md)** while that file is split and retired. **Glossary** and **References** below are authoritative for shared terminology and external pointers.

---

## Glossary

| Term | Meaning |
|------|--------|
| **ZER** | Ticker for the Zero currency; amounts in the wallet/RPC are often in **zatoshi** (see `MAX_MONEY` / `MoneyRange` in consensus code). |
| **zatoshi** | Smallest indivisible unit (same naming convention as Bitcoin’s satoshi). |
| **Transparent address (t-addr)** | Public UTXO address; balances and flows visible on-chain like Bitcoin. |
| **Shielded address (z-addr)** | Address using the shielded pool; privacy via Zcash-family zk-SNARKs (**Sapling** generation in this codebase). |
| **Sapling** | Shielded protocol generation used on Zero; see network upgrade / branch IDs in consensus code for activation on each network. |
| **Sprout** | Earlier shielded pool generation (legacy path in Zcash lineage; relevance on Zero follows shipped consensus rules). |
| **JoinSplit** | Shielded transaction component that moves value into/out of the shielded pool (Zcash terminology). |
| **Note / commitment / nullifier** | Shielded note: commitment recorded on-chain; nullifier spent when the note is used. |
| **Equihash (192, 7)** | Proof-of-work algorithm parameters for Zero (**n = 192**, **k = 7**); differs from Zcash’s common **(200, 9)** deployment. |
| **Block subsidy** | Newly issued coins per block before fees; schedule includes **halving** steps (see **Subsidy** for exact function). |
| **Halving** | Periodic reduction of the block subsidy at defined block heights. |
| **Founders reward** | Fraction of the subsidy directed to founders’ addresses in eligible height ranges (see **Subsidy**; on-chain visible). |
| **Zeronode** | Incentive layer: operators lock collateral and may receive a **percentage of block value** (spork-gated tier range; see **Subsidy**). |
| **Spork** | Live-adjustable feature or economics toggle enforced by the network (Zcash-family pattern; Zero uses it for zeronode tiers and related behavior). |
| **COINBASE_MATURITY** | Number of confirmations before coinbase outputs are spendable (**720** on Zero mainnet/regtest in this tree—differs from Bitcoin **100** and Zcash **100**). |
| **Coinbase (block reward)** | Subsidy + fees in the coinbase transaction; maturity rules affect tests and wallet spendability. |
| **Mainnet / testnet / regtest** | **Mainnet** is public production; **testnet** is public test; **regtest** is local-only regression (see **chainparams** / **TEST_ZERO** for test behavior). |
| **Network upgrade (NU) / branch id** | Consensus rule sets selected by height; **branch id** identifies the rule set (Overwinter / Sapling / … as implemented in Zero). |
| **zerod** | Full node daemon: validates blocks, serves P2P and RPC. |
| **zero-cli** | RPC client for `zerod`. |
| **zero-tx** | Transaction utility binary (see **doc/man/**). |
| **RPC** | JSON-RPC interface exposed by **zerod** for querying chain, mempool, and wallet (when enabled). |
| **Pruning / txindex / insight / zindex** | Optional indexes and storage modes; turning them on can force **reindex** (see **BUILD_ZERO** and **init** help). |
| **Reindex** | Rebuild local indexes from block files; heavy operation. |
| **Rescan** | Wallet-only pass over the chain to find transactions (see wallet/import RPCs). |
| **Params (proving keys)** | Large download for shielded proving; **fetch-params** scripts in the repo. |
| **MAX_MONEY** | Consensus constant capping single-output amounts; **total issued supply** can still differ from that cap in documentation—see **Subsidy** for supply discussion. |
| **Deprecation height** | Node may shut down past a built-in date/height if not upgraded (see README deprecation note for current major version). |
| **P2P subver** | Peer user-agent string advertised on the wire (node branding; differs from upstream “MagicBean” lineage). |
| **Mempool** | Unconfirmed transactions held by the node before block inclusion. |
| **Difficulty / block time** | Target spacing and adjustment rules are chain-specific (see consensus params vs Bitcoin/Zcash). |
| **ZIP** | Zcash Improvement Proposal; informative for cryptography and protocol lineage; Zero may diverge after fork. |

---

## References

### Project

| Resource | URL |
|----------|-----|
| Zero website | [zerocurrency.io](https://zerocurrency.io) |
| This repository | [github.com/zerocurrencycoin/Zero](https://github.com/zerocurrencycoin/Zero) |
| Releases | [github.com/zerocurrencycoin/Zero/releases](https://github.com/zerocurrencycoin/Zero/releases) |

### Community (verify links before citing as “official”)

| Resource | URL |
|----------|-----|
| BitcoinTalk (older thread) | [topic 1796036](https://bitcointalk.org/index.php?topic=1796036.0) |
| BitcoinTalk (newer thread) | [topic 3310714](https://bitcointalk.org/index.php?topic=3310714.0) |

### Protocol lineage (Zcash / Bitcoin)

| Resource | URL |
|----------|-----|
| Zcash protocol specification (PDF) | [protocol.pdf](https://github.com/zcash/zips/raw/master/protocol/protocol.pdf) |
| Zcash Improvement Proposals | [zips.z.cash](https://zips.z.cash/) |
| Bitcoin Core documentation | [bitcoincore.org](https://bitcoincore.org/en/doc/) |

### Security (Zcash-hosted; informative for zk-SNARK wallets)

| Resource | URL |
|----------|-----|
| Zcash security information | [z.cash/support/security](https://z.cash/support/security/) |

### Third-party metrics (not endorsed; verify independently)

Mining aggregators and calculators (e.g. [miningpoolstats.stream/zero](https://miningpoolstats.stream/zero), [whattomine.com](https://whattomine.com)) publish **Equihash (192, 7)** and **ZER** data that drifts from chain state—always cross-check against your own node or explorer.

### In-repo technical sources

| Topic | Document |
|-------|----------|
| Subsidy, halving, founders, zeronode split, supply notes | [Subsidy.md](Subsidy.md) |
| Outline for expanding **ZERO_COIN** sections | [ZeroCoin.md](ZeroCoin.md) |
| Build, platforms, depends | [BUILD_ZERO.md](BUILD_ZERO.md) |
| Tests, maturity **720**, harness overview | [TEST_ZERO.md](TEST_ZERO.md) |
| Shipped CLI flags | [doc/man/](doc/man/) |
