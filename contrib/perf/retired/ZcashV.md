# Zcash 2026 vulnerabilities and fork ecosystem notes

Scope: Sprout verification bug (Mar 2026) and Orchard counterfeiting bug (May-Jun 2026). Relevance to Zero and other zcashd-lineage clones. Code inspection references **`Zero400/src/`** unless noted.

Last updated: 2026-06-08 (mainnet RPC samples at height 2,471,322).

---

## 1. Vulnerability summaries

### 1.1 Sprout / `fChecked` (CVE-2026-35679)

| Field | Detail |
|-------|--------|
| **Disclosed** | 2026-03-23 (Alex "Scalar" Sol); public 2026-03-31 |
| **Affected** | zcashd v3.1.0 through v6.11.x |
| **Fixed** | [zcashd v6.12.0](https://github.com/zcash/zcash/releases/tag/v6.12.0), patch [db969c63](https://github.com/zcash/zcash/commit/db969c63f48f0f9fc518112ed0b7ace1af78b9d0) |
| **Mechanism** | `CheckBlock` runs twice (`AcceptBlock`, then `ConnectBlock`). Sprout proof verification is deferred to the second pass with `ProofVerifier::Strict()`. The Bitcoin-inherited `CBlock::fChecked` flag could be set on the first pass (with `ProofVerifier::Disabled()`), causing the second pass to skip all checks including Sprout proofs. |
| **Impact** | Malicious miner could include invalid Sprout JoinSplits in a block at tip. Bounded to ~25k ZEC in deprecated Sprout pool; turnstile prevents supply inflation. Mempool and reindex paths still verified proofs. |
| **Not affected** | [Zebra](https://zfnd.org/) (alternate implementation; would fork on exploit) |
| **References** | [Forum disclosure](https://forum.zcashcommunity.com/t/security-disclosure-we-remediated-a-vulnerability-in-sprout/55180), [ZODL write-up](https://zodl.com/zcashd-sprout-verification-vulnerability/), [NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-35679) |

### 1.2 Orchard soundness (NU6.2 emergency fork)

| Field | Detail |
|-------|--------|
| **Discovered** | 2026-05-29 (Taylor Hornby, Shielded Labs; AI-assisted audit) |
| **Disclosed publicly** | 2026-06-04+ |
| **Affected** | Zcash Orchard pool (Halo2 `halo2_gadgets` circuit) since May 2022 activation |
| **Fixed** | Emergency soft fork (disable Orchard), then [NU6.2](https://zfnd.org/zebra-4-5-3-and-5-0-0-emergency-soft-fork-and-nu6-2-activation/) at mainnet height 3,364,600 (2026-06-03); zcashd v6.12.5 / v6.20.0 |
| **Mechanism** | Under-constrained elliptic-curve multiplication in Orchard Action circuit; prover could pass verification with invalid state transition. |
| **Impact** | Theoretical unlimited counterfeit ZEC **inside Orchard pool**; undetectable pre-fix due to privacy. Turnstile showed no supply-cap violation during incident window. |
| **Follow-up** | [Ironwood](https://tachyon.z.cash/blog/auditing-orchard-supply/) -- new shielded pool + forced Orchard turnstile migration for supply audit |
| **References** | [Shielded Labs](https://shieldedlabs.net/the-orchard-counterfeiting-vulnerability/), [forum thread](https://forum.zcashcommunity.com/t/the-orchard-counterfeiting-vulnerability-and-next-steps/56015) |

---

## 2. Shielded pool status by project

| Project | Sprout | Sapling | Orchard | Notes |
|---------|--------|---------|---------|-------|
| **Zcash (ZEC)** | Deprecated (ZIP 211); pool ~25k ZEC | Active | Active (NU6.2 fixed circuit) | Reference implementation |
| **Zero (ZER)** | Historical chain data; monitored pool | Active | **Not implemented** | Upgrades through Blossom/Cosmos in `consensus/params.h` |
| **TENT** | Same lineage as Zero fork era | Active | No | Masternode + treasury outputs (4th coinbase vout) |
| **Pirate (ARRR)** | No mainnet use | **100% shielded** mainnet | Testnet only (2026) | [Not affected blog](https://piratechain.com/blog/pirate-chain-arrr-not-affected-by-critical-zcash-orchard-vulnerability/) |
| **Hush3** | **Code removed** (v3.4+) | Enforced z2z | No | [git.hush.is](https://git.hush.is/hush/hush3) |
| **Horizen (ZEN)** | Removed 2024 | Removed 2024 | No | [ZenIP-42207](https://github.com/HorizenOfficial/ZenIPs/blob/zenip_42207-draft/zenip_42207.md); pivot to Base L3 |
| **Komodo (KMD)** | Consensus-disabled 2019; proof check removed 2024 | Assetchain-dependent | No | [2018 coordinated fix](https://komodoplatform.com/en/blog/komodo-eliminated-critical-vulnerability/) |
| **Verus (VRSC)** | Via Komodo lineage | Privacy txs | No | Komodo-based |
| **Ycash (YEC)** | **Preserved by design** (friendly fork) | Active | No | Last major release ~2022; **audit `fChecked` backport** |
| **Firo** | N/A (Lelantus, not zcash pools) | N/A | N/A | Different stack |

---

## 3. Clone reactions (public chatter, Mar-Jun 2026)

| Project | Sprout Mar 2026 | Orchard Jun 2026 |
|---------|-----------------|------------------|
| **Pirate** | No post found | **Formal blog**: not affected; Orchard testnet will include Zcash fix before mainnet |
| **Hush** | Silence | Silence (structurally mitigated) |
| **Horizen** | Silence | Silence (shielded removed 2024) |
| **Komodo** | Silence | Silence (Sprout disabled at consensus) |
| **Verus / Ycash / ZClassic** | No 2026 advisories | No 2026 advisories |
| **Zero** | No public statement | No public statement |

**Ecosystem themes (Zcash forum / media):**

- Sprout: calls to sunset Sprout; Scalar bounty (~200 ZEC); NU7 schedule slip.
- Orchard: ZEC price drawdown; debate over **provable supply** in privacy pools; AI-assisted discovery (Opus 4.8); Ironwood migration proposal.
- **Disclosure gap vs 2018:** Komodo and Horizen received private notice for the 2018 counterfeiting bug; 2026 fixes were Zcash-centric (pools, ZODL, Zebra) with **no documented fork outreach**.

---

## 4. Historical fork coordination (pre-2026)

| Year | Event | Fork response |
|------|-------|---------------|
| **2018** | Sprout counterfeiting (PHGR13 paper error) | Horizen ZEN 2.0.16 Groth16 subset; Komodo merged fix across 40+ chains under Sapling upgrade cover |
| **2020+** | zcashd `fChecked` optimization introduced (v3.1.0) | Silent until 2026 Scalar disclosure |
| **2024** | Komodo Drogon | Sprout proof verification removed; Sprout txs banned since 2019 |
| **2024** | Horizen ZenIP-42207 | Shielded pool removed from mainchain |

Upstream guidance for Sapling-era forks: [zcash/zcash#3831](https://github.com/zcash/zcash/issues/3831) -- disable legacy Sprout proofs on forks that never had Sprout deposits.

---

## 5. Zero code inspection (Zero400)

### 5.1 Sprout / `fChecked` applicability

| Check | Result |
|-------|--------|
| `CBlock::fChecked` in tree | **Absent** (`grep` over `src/primitives/block.h`, `src/main.cpp`) |
| `ProcessNewBlock` first pass | `ProofVerifier::Disabled()` (`main.cpp` ~4654) |
| `ConnectBlock` second pass | `ProofVerifier::Strict()` when `fExpensiveChecks` (`main.cpp` ~2941-2945) |
| Comment at ConnectBlock | Explicit: "Check it again to verify JoinSplit proofs" |

**Conclusion:** The specific **zcashd v6.12.0 `fChecked` bug does not apply** to Zero. Residual inherited behavior: blocks that are checkpoint ancestors skip expensive script/proof checks during IBD (last mainnet checkpoint height **700,000**).

### 5.2 Orchard applicability

**Not applicable.** Network upgrades in `src/consensus/params.h`: Overwinter, Sapling, Cosmos, Blossom -- no NU5/Orchard.

### 5.3 Sapling / JoinSplit (ongoing audit surface)

Zero still verifies Sprout JoinSplits on the connect path when `fExpensiveChecks` is true. Sapling spends/outputs validated in `ContextualCheckTransaction` / `CheckTransaction`. Separate from the two 2026 CVE classes but same general ZK maintenance burden.

---

## 6. Suggested actions for Zero

| Priority | Action |
|----------|--------|
| **P0** | Document security posture (Sapling-only mainnet, no `fChecked`, ConnectBlock Strict path) -- optional short note for operators/exchanges |
| **P1** | Line-audit `ConnectBlock` / `CheckTransaction` JoinSplit loop against [db969c63](https://github.com/zcash/zcash/commit/db969c63f48f0f9fc518112ed0b7ace1af78b9d0) pattern (confirm no other early-return skips strict verification on tip blocks) |
| **P1** | Fix stale comment in `ContextualCheckBlock` ("20% founders") -- code uses **7.5%** |
| **P2** | If ever porting Orchard: follow Pirate model (testnet-only until Zcash-hardened circuit + NU-style fork) |
| **P2** | Monitor [Zcash GitHub security advisories](https://github.com/zcash/zcash/security/advisories); forks are not on 2018-style private disclosure list |
| **P3** | Consider Sprout deprecation alignment with ZIP-2003 direction (reduce JoinSplit attack surface) |

---

## 7. References

| Resource | URL |
|----------|-----|
| Sprout disclosure | https://forum.zcashcommunity.com/t/security-disclosure-we-remediated-a-vulnerability-in-sprout/55180 |
| Orchard disclosure | https://forum.zcashcommunity.com/t/the-orchard-counterfeiting-vulnerability-and-next-steps/56015 |
| Ironwood / supply audit | https://tachyon.z.cash/blog/auditing-orchard-supply/ |
| Zebra NU6.2 | https://zfnd.org/zebra-4-5-3-and-5-0-0-emergency-soft-fork-and-nu6-2-activation/ |
| Pirate not affected | https://piratechain.com/blog/pirate-chain-arrr-not-affected-by-critical-zcash-orchard-vulnerability/ |
| Zero validation code | `Zero400/src/main.cpp`, `Zero400/src/miner.cpp`, `Zero400/src/zeronode/payments.cpp` |
