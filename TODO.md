# TODO

User-facing items decided for implementation, with clear design and timelines. To contribute, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Active

- [ ] **Zeronode broadcast verify — null `chainActive` index:** **`CZeronodeBroadcast::CheckAndVerify`** (**`src/zeronode/zeronode.cpp`**) uses **`chainActive[pMNIndex->nHeight + ZERONODE_MIN_CONFIRMATIONS - 1]`** without a null check; can crash on short active chain. See **UpdateZero.md** §8. Track fix + regtest in GitHub Issues.
- [ ] **ZERO_COIN vs maintainer docs — scope split and Subsidy disposition:** **ZERO_COIN.md** = **user-observable** blockchain and node behavior plus **past and future events** (heights, dates, on-chain-visible economics, operational facts). **Exclude** implementation detail and **design/implementation rationale** (maintainers and planning). On **UpdateZero** redo: merge **Subsidy.md** portions that are code-centric, “why we did X,” or enhancement planning into **UpdateZero** or a **standalone maintainer technical note**—or keep **Subsidy.md** for that layer only. Decide **Subsidy.md** after **ZERO_COIN** ships: stub, split, or maintainer-only appendix. Align **README** / **README0** links and **ZeroCoin.md** cutover.
- [ ] **Documentation rollout:** README front page (community, mining, noding, trading, links to docs and social). Add **ZERO_COIN.md** per scope item above; point README at **ZERO_COIN** for chain behavior. Tighten **BUILD_ZERO** / **TEST_ZERO** roles; trim **Update\*** after user docs absorb content. Align GitHub, website, and social copy with README.
- [ ] **Engineering triage:** GitHub Issues bucketed by *fork required*, *explorer/index*, *wallet release*, *doc only*. macOS: Developer ID, notarization, **BUILD_ZERO** guidance for signed releases.
- [ ] Update sample `zero.conf` entries (options, defaults, and comments for 4.0.x).
- [ ] Update Nodes installation and operating instructions (deployment/runbook docs).
- [ ] **Debian packaging:** Decide canonical path — `zcutil/release-linux.sh` (`Package: zero`, `artifacts/linux-zero-v*.deb`) vs legacy `zcutil/build-debian-package.sh` (`zcash` naming). Deprecate or align one script; update **BUILD_ZERO.md** §2.5 when decided.
- [ ] **`zcutil/fetch-params.sh`:** Align naming (params dir / script name) and document mirror URLs in **BUILD_ZERO.md** (release/params policy); optional `pipefail` / style match to `fzero.sh` wrappers.

---

## Completed

*None.*
