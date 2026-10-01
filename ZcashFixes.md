# Shielded-pool vulnerabilities in the Zcash lineage

A record of the major soundness and verification flaws found in Zcash's shielded pools, how Zcash and its forks responded, and what each means for Zero. It covers the 2018 Sprout counterfeiting flaw, the March 2026 Sprout verification bypass (CVE-2026-35679), and the June 2026 Orchard counterfeiting flaw. Audience: Zero's board, maintainers, operators, and integrators. The opening sections need no cryptography background; the technical detail for each incident comes at the end of its section.

---

## Summary

Zcash-lineage chains, Zero among them, let users hold coins in **shielded pools**. A shielded transaction hides sender, receiver, and amount, and proves with a zero-knowledge proof that it creates no money. Because amounts are hidden, a flaw in that proof system can create coins that no outside observer can detect. Three such flaws have been found:

| Incident | Pool | Found | Fixed | Could create coins? | Zero affected? |
|----------|------|-------|-------|---------------------|----------------|
| Sprout counterfeiting (CVE-2019-7167) | Sprout | March 2018 | Sapling upgrade, October 2018 | Yes, inside Sprout | No: Zero moved Sprout proofs to Groth16 with Sapling, as Zcash did |
| Sprout verification bypass (CVE-2026-35679) | Sprout | March 2026 | zcashd v6.12.0, March 2026 | Yes, by a malicious miner | No: the flawed code path does not exist in Zero |
| Orchard counterfeiting | Orchard | May 2026 | NU6.2 network upgrade, June 2026 | Yes, inside Orchard | No: Zero has no Orchard pool |

**Zero is not affected by any of the three.** Zero stops at the Sapling generation of the protocol (network upgrades Overwinter, Sapling, Blossom, and the Zero-specific Cosmos) and never adopted Orchard. Its block validation always re-verifies shielded proofs when a block is connected. Two open items remain for Zero, both covered in section 7: a proposed policy to wind down the legacy Sprout pool, and a line-by-line audit against the 2026 Sprout patch.

The 2026 incidents also changed disclosure practice. In 2018 Zcash privately warned forks before going public; in 2026 no fork received advance notice. Forks now have to track Zcash security releases themselves.

---

## 1. Background

**Shielded pools.** Zcash has had three shielded pools, each tied to a proof system:

| Pool | Introduced | Proof system | Status in Zcash | Status in Zero |
|------|-----------|--------------|-----------------|----------------|
| Sprout | Launch, 2016 | BCTV14 (PHGR13 variant), Groth16 after Sapling | Deprecated; ~25k ZEC remain | Historical balance; Groth16 spends still verified |
| Sapling | October 2018 | Groth16 | Active | Active |
| Orchard | NU5, May 2022 | Halo 2 (no trusted setup) | Active after NU6.2 | Not implemented |

**Soundness.** A proof system is *sound* if a false statement cannot be proven. For a shielded pool the statement is "these inputs exist, are unspent, and balance the outputs". A soundness flaw lets someone prove a false balance, which means minting coins that no one can see.

**Verifying key.** Every node checks proofs against a fixed public verifying key that is pinned in consensus. Fixing a flawed circuit changes that key, which makes the fix a network upgrade that every node must adopt at the same block height.

**Turnstile (ZIP 209).** Each pool keeps a running total of value moved in and out. If a pool's balance would go negative, the block is invalid. Counterfeit coins are therefore trapped inside the affected pool and cannot leave it in excess of what went in. This bounds the damage to total supply, but not the damage to other holders of that pool.

**Soft and hard forks.** A soft fork only tightens rules (for example, rejecting all Orchard transactions); non-upgraded nodes still accept the resulting blocks. A hard fork changes rules in a way old nodes reject (for example, a new verifying key), so every node must upgrade.

---

## 2. Orchard counterfeiting, 2026

### 2.1 Overview

For four years a flaw in the Orchard circuit let a prover produce valid-looking proofs for transactions that created or double-spent value inside the Orchard pool. Taylor Hornby, an independent researcher running an ongoing protocol audit for Shielded Labs, found it during a targeted review of the Orchard circuit assisted by Anthropic's Claude Opus 4.8 model ([Blockhead](https://www.blockhead.co/2026/06/05/zcash-founder-discloses-critical-orchard-forgery-flaw-fixed-by-emergency-hard-fork/); [ZODL](https://zodl.com/orchard-vulnerability-successfully-remediated/)), and built a complete regtest exploit that minted unlimited ZEC. No mainnet exploitation is known, but Orchard's privacy means it cannot be ruled out cryptographically. The turnstile kept total ZEC supply bounded.

Zcash fixed it in two steps: an emergency soft fork that switched Orchard off, followed about a day later by the NU6.2 hard fork that switched it back on with a corrected circuit and a new verifying key.

### 2.2 Timeline

| Date (UTC unless noted) | Event |
|-------------------------|-------|
| May 2022 | Orchard activates with NU5; the flaw is present from activation |
| May 28, 2026 | Anthropic releases the Claude Opus 4.8 model later used in the audit |
| May 29, 2026, ~23:53 | Taylor Hornby (Shielded Labs audit) finds the flaw and reports it privately to ZODL engineers |
| May 30-31, 2026 | Confirmation; private coordination with miners and exchanges begins |
| Jun 2, 2026, ~02:00 | Soft fork at height 3,363,426 disables Orchard actions ([Zebra 4.5.3](https://github.com/ZcashFoundation/zebra/releases/tag/v4.5.3), [zcashd v6.12.5](https://github.com/zcash/zcash/releases/tag/v6.12.5)) |
| Jun 3, 2026, ~00:05 EDT | NU6.2 hard fork at height 3,364,600 re-enables Orchard with the fixed circuit ([Zebra 5.0.0](https://github.com/ZcashFoundation/zebra/releases/tag/v5.0.0), [zcashd v6.20.0](https://github.com/zcash/zcash/releases/tag/v6.20.0)) |
| Jun 4-5, 2026 | Public disclosure by Zooko Wilcox, [Shielded Labs](https://shieldedlabs.net/the-orchard-counterfeiting-vulnerability/), [ZODL](https://zodl.com/orchard-vulnerability-successfully-remediated/), and the [Zcash Foundation](https://zfnd.org/zebra-4-5-3-and-5-0-0-emergency-soft-fork-and-nu6-2-activation/); ZEC falls about 30% ([Blockhead](https://www.blockhead.co/2026/06/05/zcash-founder-discloses-critical-orchard-forgery-flaw-fixed-by-emergency-hard-fork/)) |

On testnet the disable window began at height 4,048,500 and NU6.2 activated at 4,052,000.

### 2.3 Impact

- **Affected:** the Orchard pool only (the Halo 2 Action circuit). Affected software: `halo2_gadgets` before 0.5.0, `orchard` before 0.14.0, `zcash_primitives` before 0.28.0, zcashd v5.0.0 through v6.12.3, zebrad before 4.5.1 ([Zcash Foundation](https://zfnd.org/zebra-4-5-3-and-5-0-0-emergency-soft-fork-and-nu6-2-activation/)).
- **Not affected:** total ZEC supply (turnstile), the Sapling and transparent pools, and the privacy of honest transactions.
- **Exploitation:** proven on regtest; no known mainnet use; not provably absent.

### 2.4 Remediation

**Zebra 4.5.3 (soft fork).** Rejects every transaction and block with Orchard actions after height 3,363,426 and revalidates the mempool at activation. Peers that still relay Orchard data are not penalized, so the network stays connected while operators upgrade. Disabling Orchard, rather than shipping a verification patch, avoided revealing the flaw before the fix was ready.

**Zebra 5.0.0 (NU6.2 hard fork).** Consensus branch ID `0x5437f330` and network protocol version 170150 at height 3,364,600. Orchard returns with the fixed circuit and a new pinned verifying key. Historical Orchard blocks must still verify under the old key, so Zebra keeps both and selects one per block with `verifier_for(network_upgrade)`; the two keys must never be swapped:

| Era | Key | Blocks |
|-----|-----|--------|
| Before NU6.2 | `InsecurePreNu6_2` / `VERIFYING_KEY_PRE_NU6_2` | NU5 through the soft-fork window |
| NU6.2 onward | `FixedPostNu6_2` / `VERIFYING_KEY_POST_NU6_2` | From height 3,364,600 |

NU6.2 also enforces canonical Orchard proof length, rejecting bundles with extra bytes appended to a valid proof (bytes that ZIP 317 fees did not count).

**zcashd.** v6.12.5 shipped the Orchard-disabling soft fork (a first soft-fork patch was reported to have had problems and was replaced before activation, [RWA Times](https://rwatimes.substack.com/p/zcash-orchard)); v6.20.0 activates NU6.2 with the new verifying key and the proof-length rule. Details are in the [zcashd v6.20.0 release notes](https://github.com/zcash/zcash/releases/tag/v6.20.0) and the [Zebra halo2 module documentation](https://zebra.zfnd.org/internal/zebra_consensus/halo2/index.html).

### 2.5 Technical root cause

Orchard proofs compute elliptic-curve scalar multiplications inside the circuit with the `ecc::chip::mul` gadget in `halo2_gadgets`. Its incomplete double-and-add loop keeps the base-point coordinates `(x_p, y_p)` constant across loop rows via the `q_mul_2` selector, but never constrained them to equal the real base. The coordinates were assigned with `assign_advice` without being tied to the doubling-row or complete-addition anchors.

A prover could therefore run the loop against a free base `B' != base`, and the gadget would accept

```text
[a] base + [b] B'    instead of    [scalar] base
```

so the proof attests to a state transition that did not happen; in the Orchard Action this bypassed the diversified-address integrity check ([ZODL](https://zodl.com/orchard-vulnerability-successfully-remediated/)). `halo2_gadgets` 0.5.0 ([halo2 PR #888](https://github.com/zcash/halo2/pull/888)) constrains the base correctly.

---

## 3. Sprout verification bypass, CVE-2026-35679

### 3.1 Overview

zcashd checks each block twice: once when the block is accepted, and again when it is connected to the chain. An optimization added in zcashd v3.1.0 marked a block as already checked after the first pass, and the second pass then skipped all checks, including Sprout proof verification. Because the first pass may run with proof verification disabled, a malicious miner could include invalid Sprout transactions that no node ever verified. Exposure was bounded by the 25,424 ZEC left in the Sprout pool and by the turnstile ([ZODL](https://zodl.com/zcashd-sprout-verification-vulnerability/)).

### 3.2 Timeline

| Date | Event |
|------|-------|
| 2020 (zcashd v3.1.0) | `CBlock::fChecked` optimization introduced |
| March 23, 2026 | Private disclosure by Alex "Scalar" Sol |
| March 31, 2026 | Public disclosure; fixed in [zcashd v6.12.0](https://github.com/zcash/zcash/releases/tag/v6.12.0), patch [`db969c63`](https://github.com/zcash/zcash/commit/db969c63f48f0f9fc518112ed0b7ace1af78b9d0); 200 ZEC bounty (50 ZEC each from Shielded Labs, ZODL, the Zcash Foundation, and Bootstrap) |
| April 5, 2026 | [CVE-2026-35679](https://nvd.nist.gov/vuln/detail/CVE-2026-35679) published, CVSS 3.5 ([OpenCVE](https://app.opencve.io/cve/CVE-2026-35679)) |

Write-ups: [Zcash forum disclosure](https://forum.zcashcommunity.com/t/security-disclosure-we-remediated-a-vulnerability-in-sprout/55180), [ZODL analysis](https://zodl.com/zcashd-sprout-verification-vulnerability/), [Shielded Labs](https://shieldedlabs.net/zcash-vulnerability-successfully-remediated/). The `fChecked` optimization was inherited from Bitcoin Core and interacted incorrectly with zcashd's two-pass validation.

### 3.3 Impact

- **Affected:** zcashd v3.1.0 through v6.11.x.
- **Attacker:** a miner including invalid Sprout JoinSplits in a block it mines.
- **Bounded by:** the Sprout pool balance and the turnstile; no global supply inflation.
- **Not affected:** Zebra, which has no such flag and would have forked away from an exploiting block.

### 3.4 Technical detail

`CheckBlock` runs in `AcceptBlock` and again in `ConnectBlock`. Sprout proofs are verified in `CheckTransaction` with whatever `ProofVerifier` the caller passes. The first pass could use `ProofVerifier::Disabled()`, and it set `fChecked`; the second pass then returned early and never verified the proofs with `ProofVerifier::Strict()`. The patch ensures Sprout proof verification cannot be skipped on the connect path: the flag is cleared or proofs are re-verified on the proof-critical path.

---

## 4. Sprout counterfeiting, 2018 -- CVE-2019-7167

Ariel Gabizon of the Zcash Company (now the Electric Coin Company) found on March 1, 2018, at the Financial Cryptography 2018 conference, that the parameter-generation procedure for Sprout's original BCTV14 proving system exposed elements that allowed forged proofs, and therefore undetectable counterfeiting inside Sprout. The Sapling upgrade in October 2018 replaced Sprout's proving system with Groth16 and a new parameter set, closing the flaw; ECC kept it confidential until after activation and published it in February 2019 as [CVE-2019-7167](https://nvd.nist.gov/vuln/detail/CVE-2019-7167) ([ECC disclosure](https://electriccoin.co/blog/zcash-counterfeiting-vulnerability-successfully-remediated/)). On November 13, 2018, before going public, ECC privately notified Horizen and Komodo, reasoning that those two covered about two thirds of the affected capital in other chains while wider notice would raise exploitation risk ([ECC disclosure](https://electriccoin.co/blog/zcash-counterfeiting-vulnerability-successfully-remediated/); [Komodo write-up](https://komodoplatform.com/en/blog/komodo-eliminated-critical-vulnerability/)). The CVE was published on March 27, 2019 with CVSS 7.5 ([OpenCVE](https://www.opencve.io/cve/CVE-2019-7167)).

Zero adopted Sapling with the same Groth16 Sprout verification, and verification of pre-Sapling (PHGR) Sprout proofs is skipped behind a checkpoint, as in zcashd (section 7).

---

## 5. Disclosure practice, 2018 compared with 2026

| Aspect | 2018 Sprout counterfeiting | 2026 Sprout bypass | 2026 Orchard |
|--------|---------------------------|--------------------|--------------|
| Discoverer | Ariel Gabizon (ECC) | Alex "Scalar" Sol | Taylor Hornby (Shielded Labs audit) |
| Private notice to forks | Yes: Horizen and Komodo, November 13, 2018 | None documented | None documented |
| Public cover for the fix | Sapling upgrade | zcashd v6.12.0 | Emergency soft fork, then NU6.2 |
| Alternate implementation (Zebra) | Did not exist | Not affected | Fixed in 4.5.3 and 5.0.0 |
| AI involvement | None | None | Audit assisted by Claude Opus 4.8 |
| Market and community | Limited | 200 ZEC bounty | ZEC fell about 30% on disclosure; Ironwood supply-audit proposal |

The 2026 fixes were coordinated among ZODL, the Zcash Foundation (Zebra), and Shielded Labs. Most zcashd forks received no advisory at all, even though their Sprout validation paths differ and most lack Orchard code.

---

## 6. Ecosystem posture

### 6.1 Shielded pools by project

| Project | Sprout | Sapling | Orchard | Notes |
|---------|--------|---------|---------|-------|
| Zcash (ZEC) | Deprecated (ZIP 211); ~25k ZEC | Active | Active, fixed circuit | Reference implementation |
| Zero (ZER) | Historical balance, turnstile-monitored | Active | Not implemented | Upgrades through Blossom and Cosmos |
| TENT | Same lineage as Zero's fork era | Active | No | Masternodes plus a treasury coinbase output |
| Pirate (ARRR) | No mainnet use | Mandatory for all mainnet transactions | Testnet only | [Published "not affected" notice](https://piratechain.com/blog/pirate-chain-arrr-not-affected-by-critical-zcash-orchard-vulnerability/) |
| Hush | Code removed (v3.4+) | Enforced z-to-z | No | [git.hush.is/hush/hush3](https://git.hush.is/hush/hush3) |
| Horizen (ZEN) | Removed 2024 | Removed 2024 | No | [ZenIP-42207](https://github.com/HorizenOfficial/ZenIPs/blob/zenip_42207-draft/zenip_42207.md); moving to a Base L3 |
| Komodo (KMD) | Disabled in consensus 2019; proof check removed 2024 | Depends on assetchain | No | Coordinated fix in 2018 |
| Verus (VRSC) | Via Komodo lineage | Private transactions | No | Komodo-based |
| Ycash (YEC) | Kept by design | Active | No | Last major release around 2022; should audit for an `fChecked` backport |
| Firo | Not applicable (Lelantus) | Not applicable | Not applicable | Different proof stack |

### 6.2 Public responses, March to June 2026

| Project | Sprout bypass | Orchard |
|---------|---------------|---------|
| Zero | No public statement | No public statement |
| Pirate | None found | Formal notice: not affected; testnet Orchard will include the Zcash fix before mainnet |
| Hush | None | None (structurally mitigated) |
| Horizen | None | None (shielded pools removed in 2024) |
| Komodo | None | None (Sprout disabled in consensus) |
| Verus, Ycash, ZClassic | No advisories | No advisories |

Community discussion centered on pressure to retire Sprout, the Scalar bounty, a debate over auditing Orchard supply, and the [Ironwood proposal](https://tachyon.z.cash/blog/auditing-orchard-supply/).

### 6.3 Exposure by project

| Project | Stack | 2026 Orchard flaw | 2026 Sprout bypass | Action |
|---------|-------|-------------------|--------------------|--------|
| Zcash | zcashd / Zebra | Fixed ([v6.20.0](https://github.com/zcash/zcash/releases/tag/v6.20.0)) | Fixed ([v6.12.0](https://github.com/zcash/zcash/releases/tag/v6.12.0)) | Reference |
| Zebra | Rust full node | Fixed in 4.5.3 and 5.0.0 | Not affected | None |
| Zero | zcashd fork | Not applicable | Not applicable (no `fChecked`) | Monitor; Sprout wind-down (section 8) |
| Ycash | zcashd fork | Not applicable | Audit Sprout path | Diff `main.cpp` on each Zcash security release |
| Other zcashd forks | Varies | Usually not applicable | Audit Sprout path | Diff on each Zcash security release |

Komodo-style Orchard assetchains (`-ac_orchard`) exist only on test networks and are not a model for Zero; Orchard study should use Zcash `zebrad`.

---

## 7. Zero code analysis

**No `fChecked`.** The symbol does not exist anywhere in Zero's `src/`.

**Connect path verifies strictly.** `ConnectBlock` re-runs `CheckBlock` with the strict verifier whenever expensive checks apply:

```cpp
auto verifier = libzcash::ProofVerifier::Strict();
auto disabledVerifier = libzcash::ProofVerifier::Disabled();

// Check it again to verify JoinSplit proofs, and in case a previous version let a bad block in
if (!CheckBlock(block, state, chainparams, fExpensiveChecks ? verifier : disabledVerifier, !fJustCheck, !fJustCheck))
```

**JoinSplits are verified in `CheckTransaction`:**

```cpp
BOOST_FOREACH(const JSDescription &joinsplit, tx.vJoinSplit) {
    if (!joinsplit.Verify(*pzcashParams, verifier, tx.joinSplitPubKey)) {
        return state.DoS(100, error("CheckTransaction(): joinsplit does not verify"),
                            REJECT_INVALID, "bad-txns-joinsplit-verification-failed");
```

**Groth16 Sprout proofs** go to `librustzcash_sprout_verify` (`src/primitives/transaction.cpp`). **PHGR (BCTV14) proofs** return true without verification, because the chain is checkpointed after Sapling activation; this matches zcashd.

**The ZIP 209 turnstile is enforced** in `ConnectBlock`: a negative Sprout pool balance rejects the block.

| Check | Result |
|-------|--------|
| `CBlock::fChecked` | Absent |
| `ProcessNewBlock` first pass | `ProofVerifier::Disabled()` |
| `ConnectBlock` second pass | `ProofVerifier::Strict()` when `fExpensiveChecks` |
| ZIP 209 turnstile | Enforced |

**Conclusion.** The CVE-2026-35679 mechanism does not exist in Zero. The remaining Sprout trust is ordinary: blocks below the last mainnet checkpoint (700,000) skip expensive script and proof checks during initial sync, PHGR proofs are trusted behind the checkpoint, and the historical Sprout balance is bounded by the turnstile.

---

## 8. Proposed Zero policy: Sprout as destination only

Zcash ZIP 211 stopped new value from entering Sprout after Sapling and provides migration tooling. ZIP 2003, proposed for Zcash NU7, would disable version 4 transactions and so leave remaining Sprout funds unspendable without burning them ([Cointelegraph](https://cointelegraph.com/news/zcash-nu7-upgrade-sprout-funds-unspendable)). The proposal for Zero is gentler and not scheduled; it needs a consensus decision and an activation height H.

| Rule | Detail |
|------|--------|
| No new Sprout outputs | After H, reject transactions that move value into Sprout |
| Spends out remain valid | Existing Sprout notes may move to transparent or Sapling addresses until the pool is empty |
| Groth16 verification | Keep `librustzcash_sprout_verify` for those spends |
| PHGR | Consider rejecting the PHGR proof type outright at H |
| Turnstile | Keep ZIP 209 checks while any Sprout value remains |
| Wallet RPC | After H, disable creating Sprout addresses and Sprout destinations in `z_shieldcoinbase` and `z_mergetoaddress`; keep migration RPCs |

Nodes still need `sprout-groth16.params` at startup (`ZC_LoadParams`) until historical spends are gone. Regression scripts: `sprout_sapling_migration.py`, `mergetoaddress_sprout.py`, `turnstile.py`.

---

## 9. Recommended actions for Zero

| Priority | Action |
|----------|--------|
| P1 | Audit `ConnectBlock` and the `CheckTransaction` JoinSplit loop line by line against zcashd `db969c63`, confirming no other early return skips strict verification for tip blocks |
| P2 | Subscribe to [Zcash security advisories](https://github.com/zcash/zcash/security/advisories), ZODL, and Zebra releases, and diff every zcashd security release, since forks no longer receive advance notice |
| P2 | If Orchard is ever considered, follow Pirate's approach: testnet only until a Zcash-hardened circuit ships with an NU-style fork |
| P3 | Decide on the Sprout wind-down in section 8, taking into account Zcash's ZIP 2003 direction of making Sprout unspendable |

---

## References

| Resource | URL |
|----------|-----|
| Shielded Labs: the Orchard counterfeiting vulnerability | https://shieldedlabs.net/the-orchard-counterfeiting-vulnerability/ |
| Zcash Foundation: Zebra 4.5.3 and 5.0.0, soft fork and NU6.2 | https://zfnd.org/zebra-4-5-3-and-5-0-0-emergency-soft-fork-and-nu6-2-activation/ |
| Zcash forum: Orchard vulnerability and next steps | https://forum.zcashcommunity.com/t/the-orchard-counterfeiting-vulnerability-and-next-steps/56015 |
| Zebra 4.5.3 release | https://github.com/ZcashFoundation/zebra/releases/tag/v4.5.3 |
| Zebra 5.0.0 release | https://github.com/ZcashFoundation/zebra/releases/tag/v5.0.0 |
| zcashd v6.12.5 (Orchard disabled) | https://github.com/zcash/zcash/releases/tag/v6.12.5 |
| zcashd v6.20.0 (NU6.2) | https://github.com/zcash/zcash/releases/tag/v6.20.0 |
| halo2 PR #888 (`halo2_gadgets` 0.5.0) | https://github.com/zcash/halo2/pull/888 |
| Zebra halo2 verifying-key module | https://zebra.zfnd.org/internal/zebra_consensus/halo2/index.html |
| Ironwood: auditing Orchard supply | https://tachyon.z.cash/blog/auditing-orchard-supply/ |
| ZODL: Orchard vulnerability remediated | https://zodl.com/orchard-vulnerability-successfully-remediated/ |
| Blockhead: Orchard flaw disclosure and AI-assisted audit | https://www.blockhead.co/2026/06/05/zcash-founder-discloses-critical-orchard-forgery-flaw-fixed-by-emergency-hard-fork/ |
| RWA Times: Orchard soft fork report | https://rwatimes.substack.com/p/zcash-orchard |
| CVE-2026-35679 (NVD) | https://nvd.nist.gov/vuln/detail/CVE-2026-35679 |
| CVE-2026-35679 (OpenCVE) | https://app.opencve.io/cve/CVE-2026-35679 |
| Shielded Labs: Sprout vulnerability remediated | https://shieldedlabs.net/zcash-vulnerability-successfully-remediated/ |
| zcashd v6.12.0 (Sprout fix) | https://github.com/zcash/zcash/releases/tag/v6.12.0 |
| zcashd patch db969c63 | https://github.com/zcash/zcash/commit/db969c63f48f0f9fc518112ed0b7ace1af78b9d0 |
| Zcash forum: Sprout vulnerability disclosure | https://forum.zcashcommunity.com/t/security-disclosure-we-remediated-a-vulnerability-in-sprout/55180 |
| ZODL: zcashd Sprout verification vulnerability | https://zodl.com/zcashd-sprout-verification-vulnerability/ |
| CVE-2019-7167 (NVD) | https://nvd.nist.gov/vuln/detail/CVE-2019-7167 |
| CVE-2019-7167 (OpenCVE) | https://www.opencve.io/cve/CVE-2019-7167 |
| ECC: counterfeiting vulnerability remediated (2019) | https://electriccoin.co/blog/zcash-counterfeiting-vulnerability-successfully-remediated/ |
| Komodo: critical vulnerability eliminated (2018) | https://komodoplatform.com/en/blog/komodo-eliminated-critical-vulnerability/ |
| ZIP 209: prohibit negative shielded pool balances | https://zips.z.cash/zip-0209 |
| ZIP 211: disabling addition of new value to Sprout | https://zips.z.cash/zip-0211 |
| ZIP 317: proportional transfer fee | https://zips.z.cash/zip-0317 |
| Cointelegraph: NU7 and ZIP 2003 Sprout change | https://cointelegraph.com/news/zcash-nu7-upgrade-sprout-funds-unspendable |
| Zcash security advisories | https://github.com/zcash/zcash/security/advisories |
| Pirate Chain: not affected by the Orchard vulnerability | https://piratechain.com/blog/pirate-chain-arrr-not-affected-by-critical-zcash-orchard-vulnerability/ |
| Hush source | https://git.hush.is/hush/hush3 |
| Horizen ZenIP-42207 | https://github.com/HorizenOfficial/ZenIPs/blob/zenip_42207-draft/zenip_42207.md |
