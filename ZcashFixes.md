# Zcash shielded-pool vulnerabilities and remediation (2026)

Draft for publication. Scope: Orchard counterfeiting (May--June 2026), Sprout verification bypass CVE-2026-35679 (March 2026), and Zero Currency applicability.

**Publication status:** Draft (Jun 2026). Audience: node operators, fork maintainers, integrators.

**Fork CVE posture (all clones, including PIRATETST):** Appendix only. Do not duplicate elsewhere.

---

## Introduction

In the first half of 2026, Zcash disclosed two critical flaws in its shielded stacks: an **Orchard soundness bug** that could permit undetectable counterfeiting inside the Orchard pool, and a **Sprout verification bypass** tied to the zcashd `fChecked` block flag. Both required coordinated network upgrades.

**Zero Currency (ZER) is not in danger from either vulnerability.**

Zero is a zcashd-lineage full node that **does not implement Orchard or NU5**. Consensus upgrades stop at Sapling, Cosmos, and Blossom. The Sprout CVE mechanism (`CBlock::fChecked` skipping proof reverification) **does not exist in the Zero tree** -- there is no `fChecked` symbol, and `ConnectBlock` invokes `CheckBlock` with `ProofVerifier::Strict()` for JoinSplit verification.

The sections below explain both bugs, analyze the Zero tree, compare disclosure practice to 2018, and outline a planned Sprout sunset policy. Fork posture for other projects appears once, in the Appendix.

---

## Part 1: Orchard counterfeiting vulnerability

### 1.1 Timeline

| Date (UTC unless noted) | Event |
|-------------------------|--------|
| **May 2022** | Orchard activated on Zcash mainnet (NU5). Bug present from activation. |
| **May 28, 2026** | Anthropic releases Opus 4.8 model. |
| **May 29, 2026, ~23:53** | Taylor Hornby (Shielded Labs audit) discovers flaw; private report to ZODL. |
| **May 31, 2026** | Private coordination with miners and exchanges begins. |
| **Jun 2, 2026, ~02:00** | Emergency soft fork at mainnet height **3,363,426** -- Orchard actions **disabled** ([Zebra 4.5.3](https://github.com/ZcashFoundation/zebra/releases/tag/v4.5.3), [zcashd v6.12.5](https://github.com/zcash/zcash/releases/tag/v6.12.5)). |
| **Jun 3, 2026, ~00:05 EDT** | **NU6.2** hard fork at height **3,364,600** -- Orchard **re-enabled** with fixed circuit ([Zebra 5.0.0](https://github.com/ZcashFoundation/zebra/releases/tag/v5.0.0), [zcashd v6.20.0](https://github.com/zcash/zcash/releases/tag/v6.20.0)). |
| **Jun 4, 2026+** | Public disclosure ([Shielded Labs](https://shieldedlabs.net/the-orchard-counterfeiting-vulnerability/), [Zcash Foundation](https://zfnd.org/zebra-4-5-3-and-5-0-0-emergency-soft-fork-and-nu6-2-activation/)). |

Testnet: Orchard disable window default height **4,048,500**; NU6.2 at **4,052,000**.

### 1.2 Impact

- **Affected:** Orchard shielded pool only (Halo2 Action circuit).
- **Mechanism:** Prover could satisfy verification with **invalid state transitions** -- counterfeit or double-spent value **inside Orchard**.
- **Not affected:** Total ZEC supply cap (turnstile accounting); Sapling and transparent pools; privacy of honest transactions.
- **Exploitation:** Researcher built a **complete regtest exploit** generating unlimited counterfeit ZEC ([Shielded Labs disclosure](https://shieldedlabs.net/the-orchard-counterfeiting-vulnerability/)). No known mainnet exploitation; **cannot be ruled out cryptographically** due to Orchard privacy.
- **Affected software:** `halo2_gadgets` < 0.5.0, `orchard` < 0.14.0, `zcashd` v5.0.0--v6.12.3, `zebrad` < 4.5.1.

### 1.3 Root cause (circuit soundness)

Upstream description ([zcashd v6.20.0 release notes](https://github.com/zcash/zcash/releases/tag/v6.20.0)):

The incomplete double-and-add loop in `ecc::chip::mul` (in `halo2_gadgets`) kept per-iteration base coordinates `(x_p, y_p)` constant across loop rows via `q_mul_2`, but **never constrained them to the real circuit base**. Coordinates were assigned with `assign_advice` without connecting to doubling-row or complete-addition anchors.

A prover could run the loop against a free base `B' != base`, making the gadget verify:

```text
[a] base + [b] B'    instead of    [scalar] base
```

That breaks soundness: the proof attests to a state transition that did not occur.

**Fix:** `halo2_gadgets` v0.5.0 ([halo2 PR #888](https://github.com/zcash/halo2/pull/888)) anchors the base correctly. Because the verifying key is **consensus-pinned**, fixing the circuit requires a **network upgrade (NU6.2)**, not a node-only patch.

Secondary fix in NU6.2: **strict Orchard proof length** -- reject bundles with non-canonical proof size (extra bytes appended to valid proofs, not counted by ZIP 317 fees).

### 1.4 Zebra remediation (two releases)

**Phase A -- Zebra 4.5.3 (soft fork):**

- Reject all transactions and blocks containing Orchard actions after height 3,363,426.
- Mempool revalidated at activation.
- Peers relaying Orchard data during the window are **not** DoS-penalized (network stays connected while operators upgrade).
- Rationale: a direct verification patch would leak vulnerability details; disabling Orchard limited exposure while NU6.2 was prepared.

**Phase B -- Zebra 5.0.0 (NU6.2):**

- Consensus branch ID **`0x5437f330`** at height 3,364,600.
- Re-enable Orchard with **fixed circuit** and new pinned verifying key.
- **Dual verifying keys** for historical sync ([Zebra halo2 module](https://zebra.zfnd.org/internal/zebra_consensus/halo2/index.html)):

| Era | Key | Blocks |
|-----|-----|--------|
| Pre-NU6.2 Orchard | `InsecurePreNu6_2` / `VERIFYING_KEY_PRE_NU6_2` | NU5 through soft-fork history |
| Post-NU6.2 Orchard | `FixedPostNu6_2` / `VERIFYING_KEY_POST_NU6_2` | NU6.2 onward |

`verifier_for(network_upgrade)` routes each bundle explicitly; keys must **never** be interchanged.

### 1.5 zcashd parallel track

- **v6.12.5:** Orchard-disabling soft fork (aligned with Zebra 4.5.3 intent).
- **v6.20.0:** NU6.2 activation with updated Orchard verifying key and proof-length rule.

---

## Part 2: Sprout verification bypass (CVE-2026-35679)

### 2.1 Timeline

| Date | Event |
|------|--------|
| **2018** | Sprout counterfeiting bug (PHGR13); fixed at Sapling activation (different issue). |
| **2020+ (zcashd v3.1.0)** | `CBlock::fChecked` optimization introduced. |
| **2026-03-23** | Private disclosure by Alex "Scalar" Sol. |
| **2026-03-31** | Public disclosure. |
| **2026-03-31+** | Fixed in [zcashd v6.12.0](https://github.com/zcash/zcash/releases/tag/v6.12.0), patch [db969c63](https://github.com/zcash/zcash/commit/db969c63f48f0f9fc518112ed0b7ace1af78b9d0). |
| **CVE** | [CVE-2026-35679](https://nvd.nist.gov/vuln/detail/CVE-2026-35679) |

References: [Zcash forum disclosure](https://forum.zcashcommunity.com/t/security-disclosure-we-remediated-a-vulnerability-in-sprout/55180), [ZODL write-up](https://zodl.com/zcashd-sprout-verification-vulnerability/).

### 2.2 Impact

- **Affected:** zcashd v3.1.0 through v6.11.x with Sprout JoinSplit verification path.
- **Mechanism:** `CheckBlock` runs twice (`AcceptBlock`, then `ConnectBlock`). Sprout proofs verified in `CheckTransaction` with the passed `ProofVerifier`. On first pass, `ProofVerifier::Disabled()` could be used; `fChecked` was set, causing second pass to **skip all checks** including Sprout proofs.
- **Attacker model:** Malicious miner includes invalid Sprout JoinSplits at block tip.
- **Bounded exposure:** ~25k ZEC in deprecated Sprout pool; turnstile prevents global supply inflation.
- **Not affected:** [Zebra](https://zfnd.org/) (alternate implementation; would fork on exploit).

### 2.3 Upstream fix pattern (conceptual)

Zcash patch ensures Sprout proof verification cannot be skipped on the connect path when `fChecked` is set -- reverification or flag clearing on the proof-critical path. See commit [db969c63](https://github.com/zcash/zcash/commit/db969c63f48f0f9fc518112ed0b7ace1af78b9d0).

### 2.4 Zero tree analysis

**Zero does not implement `fChecked`.** Grep across `Zero400/src` returns no matches.

**Connect path uses strict verification:**

```2941:2946:src/main.cpp
    auto verifier = libzcash::ProofVerifier::Strict();
    auto disabledVerifier = libzcash::ProofVerifier::Disabled();

    // Check it again to verify JoinSplit proofs, and in case a previous version let a bad block in
    if (!CheckBlock(block, state, chainparams, fExpensiveChecks ? verifier : disabledVerifier, !fJustCheck, !fJustCheck))
```

**JoinSplit verification in CheckTransaction:**

```1180:1186:src/main.cpp
        BOOST_FOREACH(const JSDescription &joinsplit, tx.vJoinSplit) {
            if (!joinsplit.Verify(*pzcashParams, verifier, tx.joinSplitPubKey)) {
                return state.DoS(100, error("CheckTransaction(): joinsplit does not verify"),
                                    REJECT_INVALID, "bad-txns-joinsplit-verification-failed");
```

**Groth Sprout proofs** call `librustzcash_sprout_verify`:

```100:116:src/primitives/transaction.cpp
    bool operator()(const libzcash::GrothProof& proof) const
    {
        uint256 h_sig = params.h_sig(jsdesc.randomSeed, jsdesc.nullifiers, joinSplitPubKey);

        return librustzcash_sprout_verify(
            proof.begin(),
            jsdesc.anchor.begin(),
            h_sig.begin(),
            /* ... macs, nullifiers, commitments, vpub_old, vpub_new ... */
        );
    }
```

**Legacy PHGR proofs** skip verification post-checkpoint (same as upstream zcashd):

```93:97:src/primitives/transaction.cpp
    bool operator()(const libzcash::PHGRProof& proof) const
    {
        // We checkpoint after Sapling activation, so we can skip verification
        // for all Sprout proofs.
        return true;
    }
```

**ZIP209 turnstile** enforced on mainnet:

```2967:2977:src/main.cpp
    if (chainparams.ZIP209Enabled()) {
        if (pindex->nChainSproutValue) {
            if (*pindex->nChainSproutValue < 0) {
                return state.DoS(100, error("ConnectBlock(): turnstile violation in Sprout shielded value pool"),
```

**Conclusion for Zero:** CVE-2026-35679 mechanism is **not applicable**. Residual Sprout exposure is historical pool balance and PHGR checkpoint trust, not the `fChecked` bypass.

---

## Part 3: Planned Zero policy -- post-Sapling Sprout proof disable

**Status:** Plan only (not implemented). Document for future NU discussion.

### 3.1 Zcash direction (reference)

Zcash ZIP 211 deprecated Sprout **defense in depth**: after Sapling activation, new Sprout **outputs** were discouraged; migration tooling moves Sprout to Sapling. Orchard era added further pool migration proposals (Ironwood).

### 3.2 Zero-specific plan

| Rule (proposed) | Detail |
|-----------------|--------|
| **Disable new Sprout proofs as source** | Reject txs that **create** new Sprout JoinSplit outputs (shielding **into** Sprout) after activation height H. |
| **Allow Sprout as destination only** | Permit spending **existing** Sprout notes out to transparent or Sapling (vpub_old / migration paths) until pool drains. |
| **Groth verification** | Keep `librustzcash_sprout_verify` for allowed spend paths until pool empty or further sunset. |
| **PHGR** | Already skipped post-checkpoint; consider hard reject of PHGR proof type at H. |
| **Turnstile** | Keep ZIP209 monitoring until Sprout pool balance is zero; do not disable turnstile checks while any Sprout value remains on-chain. |
| **Wallet RPC** | Disable `z_getnewaddress('sprout')`, `z_shieldcoinbase` to Sprout, and `z_mergetoaddress` Sprout destination after H; retain migration RPCs. |

**Operational note:** `sprout-groth16.params` remains required at startup today (`src/init.cpp` `ZC_LoadParams`). A Sapling-only policy still needs Sprout verify params until historical spends are gone.

**QA anchor:** `qa/rpc-tests/sprout_sapling_migration.py`, `mergetoaddress_sprout.py`, `turnstile.py`.

---

## Part 4: Disclosure chain changes (2018 vs 2026)

| Aspect | 2018 Sprout counterfeiting | 2026 Sprout fChecked | 2026 Orchard |
|--------|---------------------------|----------------------|--------------|
| **Discoverer** | Ariel Gabizon (ECC) | Alex "Scalar" Sol | Taylor Hornby (Shielded Labs audit) |
| **Private notice to forks** | Horizen, Komodo (documented) | No documented fork outreach | No documented fork outreach |
| **Public coordination** | Sapling upgrade cover | zcashd v6.12.0 | NU6.2 emergency fork |
| **Alternate impl (Zebra)** | N/A early era | Not affected | 4.5.3 + 5.0.0 |
| **AI role** | None | None | Opus 4.8 assisted audit |
| **Market / forum** | Limited | Scalar bounty (~200 ZEC) | ZEC drawdown; Ironwood proposal |

**Ecosystem gap:** 2026 fixes were Zcash-centric (ZODL, Zebra, Shielded Labs). Most zcashd forks received **no public advisories** despite differing Sprout connect paths and absent Orchard code.

**Zero public statement:** None as of Jun 2026. Technical posture: this file and `ZERO_COIN.md` Security section.

---

## Appendix: Fork stack and 2026 CVE posture

Single reference for clone research. Algorithm comparisons live in `ZKs/Comparison.md`; clone paths in `ZKs/ZKRepos.md`.

| Project | Stack | Orchard | Sprout | 2026 Orchard CVE | 2026 Sprout CVE | Action |
|---------|-------|---------|--------|------------------|-----------------|--------|
| **Zcash** | zcashd / Zebra | Mainnet NU6.2 | Deprecated pool | Patched ([v6.20.0](https://github.com/zcash/zcash/releases/tag/v6.20.0)) | Patched ([v6.12.0](https://github.com/zcash/zcash/releases/tag/v6.12.0)) | Reference |
| **Zebra** | Rust full node | NU6.2 dual keys | N/A path | 4.5.3 + 5.0.0 | Unaffected | Monitor (`ZebraZero.md`) |
| **Zero** | zcashd fork | **None** | Active pool | **N/A** | **N/A** (no `fChecked`) | Monitor; Part 3 sunset |
| **Ycash** | zcashd fork | None | Preserved | N/A | Audit Sprout path | Diff `main.cpp` per release |
| **Other zcashd forks** | Varies | Usually none | Varies | Usually N/A | Audit Sprout path | Diff on security tags |
| **Orchard assetchain (test)** | AC `-ac_orchard` | Test only | N/A | Track NU6.2-class fixes | N/A | External research only |

### A.1 Orchard assetchain testnet (PIRATETST)

Komodo-style assetchain flags -- not zcashd `-regtest`, not importable to Zero via `-nuparams`. Not grouped for Zero porting; Orchard study uses Zcash **`zebrad`** only.

---

## References

| Resource | URL |
|----------|-----|
| Shielded Labs Orchard disclosure | https://shieldedlabs.net/the-orchard-counterfeiting-vulnerability/ |
| Zcash Foundation Zebra 4.5.3 / 5.0.0 | https://zfnd.org/zebra-4-5-3-and-5-0-0-emergency-soft-fork-and-nu6-2-activation/ |
| zcashd v6.20.0 | https://github.com/zcash/zcash/releases/tag/v6.20.0 |
| zcashd v6.12.0 (Sprout fix) | https://github.com/zcash/zcash/releases/tag/v6.12.0 |
| Sprout patch db969c63 | https://github.com/zcash/zcash/commit/db969c63f48f0f9fc518112ed0b7ace1af78b9d0 |
| CVE-2026-35679 | https://nvd.nist.gov/vuln/detail/CVE-2026-35679 |
| Sprout forum thread | https://forum.zcashcommunity.com/t/security-disclosure-we-remediated-a-vulnerability-in-sprout/55180 |
| Orchard forum thread | https://forum.zcashcommunity.com/t/the-orchard-counterfeiting-vulnerability-and-next-steps/56015 |
| halo2_gadgets 0.5.0 | https://github.com/zcash/halo2/pull/888 |
| Zebra halo2 docs | https://zebra.zfnd.org/internal/zebra_consensus/halo2/index.html |
| Zero consensus (no Orchard) | `src/consensus/upgrades.cpp` |

---

## Conclusions

1. **Orchard (Jun 2026):** A four-year soundness bug in `halo2_gadgets` could have allowed undetectable counterfeiting inside the Orchard pool. Remediation required an emergency Orchard shutdown (Jun 2) and NU6.2 hard fork (Jun 3) with a new pinned verifying key. Zebra implements dual-key historical verification.

2. **Sprout fChecked (Mar 2026):** A zcashd optimization allowed block-level skipping of Sprout proof checks. Fixed in v6.12.0. Zebra was never affected.

3. **Zero Currency is not in danger from either vulnerability.** Zero has **no Orchard implementation** and **no `fChecked` bypass path**. Operators should still monitor Sprout pool balance (ZIP209) and plan a future **Sprout destination-only** sunset aligned with turnstile accounting.

4. **Disclosure practice changed:** 2026 incidents lacked the 2018-style private fork notification. Zero maintainers should subscribe to ZODL/Zebra releases and diff zcashd security patches even when Orchard is absent.

**Related Zero docs:** `ZebraZero.md`, `ZERO_COIN.md`, `UpdateZero.md`.
