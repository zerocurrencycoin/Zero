# TODO

User-facing items decided for implementation, with clear design and timelines. To contribute, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Active

- [ ] **Documentation rollout:** README front page (community, mining, noding, trading, links to docs and social). Add **ZERO_COIN.md** (merge **Subsidy.md** + **ZeroCoin.md**); point README at **ZERO_COIN** for chain economics. Tighten **BUILD_ZERO** / **TEST_ZERO** roles; trim **Update\*** after user docs absorb content. Align GitHub, website, and social copy with README.
- [ ] **Engineering triage:** GitHub Issues bucketed by *fork required*, *explorer/index*, *wallet release*, *doc only*. macOS: Developer ID, notarization, **BUILD_ZERO** guidance for signed releases.
- [ ] Update sample `zero.conf` entries (options, defaults, and comments for 4.0.x).
- [ ] Update Nodes installation and operating instructions (deployment/runbook docs).
- [ ] **Debian packaging:** Decide canonical path — `zcutil/release-linux.sh` (`Package: zero`, `artifacts/linux-zero-v*.deb`) vs legacy `zcutil/build-debian-package.sh` (`zcash` naming). Deprecate or align one script; update **BUILD_ZERO.md** §2.5 when decided.
- [ ] **`zcutil/fetch-params.sh`:** Align naming (params dir / script name) and document mirror URLs in **BUILD_ZERO.md** (release/params policy); optional `pipefail` / style match to `fzero.sh` wrappers.

---

## Completed

*None.*
