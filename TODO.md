# TODO

User-facing items decided for implementation, with clear design and timelines. To contribute, see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Active

- [ ] **Consensus subsidy / founders integer math:** Replace **`double`/`COIN`** mixes listed in **BUILD_ZERO.md** §**4.10.1** with one **`CAmount`** policy (shared **`FoundersRewardFromSubsidy(s)`** or equivalent, **`75/1000`** floor, integer **`GetBlockSubsidy`** bases). Update **`main_tests`**, **`rpc_wallet_tests`** **`getblocksubsidy`**, **`founders_reward` GTest**. **Spec / community sign-off** if visible supply or reward split changes.
- [ ] **Parallel Tier A RPC (`contrib/run-tests.sh --jobs>1`):** Reproduce hangs minimally (e.g. **`paymentdisclosure`** with **`N=4`** on macOS). Options: lower default **`N`**, serialize conflict-prune scripts, or document serial-only gate (already in **TEST_ZERO.md**). Depends on investigation, not blocking serial **`--strict`**.
- [ ] **`CZeronodeBroadcast::CheckInputsAndAdd`** (**`src/zeronode/zeronode.cpp`**): **`pConfIndex`** from **`chainActive[...]`** is now null-checked (defer / erase broadcast). **`CheckAndVerify`** and any other **`chainActive[height]`** sites should be audited the same way
- [ ] **Engineering triage:** for buckets (*fork required*, *explorer/index*, *wallet release*, *doc only*) until GitHub Issues are adopted. macOS: Developer ID, notarization, **BUILD_ZERO** guidance for signed releases.
- [ ] Update sample `zero.conf` entries (options, defaults, and comments for 4.0.x).
- [ ] Update Nodes installation and operating instructions (deployment/runbook docs).
- [ ] **Debian packaging:** Decide canonical path — `zcutil/release-linux.sh` (`Package: zero`, `artifacts/linux-zero-v*.deb`) vs legacy `zcutil/build-debian-package.sh` (`zcash` naming). Deprecate or align one script; update **BUILD_ZERO.md** §2.5 when decided.
- [ ] **`zcutil/fetch-params.sh`:** Align naming (params dir / script name) and document mirror URLs in **BUILD_ZERO.md** (release/params policy); optional `pipefail` / style match to `fzero.sh` wrappers.

---

## Completed

- [x] **ZERO_COIN + Appendix D:** Chain economics and ops in **ZERO_COIN.md**; maintainer subsidy excerpts in **UpdateZero** Appendix D.

- [x] **`run-tests.sh` background jobs:** **`run_bg`** uses **`BG_LAST_PID`** (no **`$(run_bg …)`** subshell) so **`wait`** reflects real GTest/Boost/Tier-A child exit codes (**TEST_ZERO.md** Harness changelog).
- [x] **`getchaintips` RPC test:** Split-network **`setup_network`**, **`CHAIN_BOOTSTRAP`**, branch/rejoin assertions (**`qa/rpc-tests/getchaintips.py`**
- [x] **`rescan_import.py` executable:** Git index **`100755`** so **`rpc-tests.sh`** can run the script (**TEST_ZERO.md** Harness changelog).
- [x] **macOS + optional all-platform system Rust:** **`depends/packages/rust.mk`** — **`RUST_USE_SYSTEM=1`** for non-macOS; **Darwin** default system; **`FORCE_DEPENDS_RUST=1`** for pinned **1.32.0**. Documented **BUILD_ZERO.md** §**4.1**, **§4.6**, **§4.9**, **§4.11–4.12**, **§5.1–5.2**.
- [x] **Zeronode `pConfIndex` null guard:** **`src/zeronode/zeronode.cpp`** **`CheckInputsAndAdd`** — no deref when **`chainActive[confHeight]`** is null (**BUILD_ZERO.md** §**4.12**).
