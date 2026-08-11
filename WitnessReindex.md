# Shielded witness rebuild and reindex coverage

**Status:** B1 shipped -- `qa/rpc-tests/reindex_shielded.py` in Tier B pass (validated 2026-08-11). CleanIndex gtest (B2) and witness hardening (C) remain postponed (IMP-WITNESS-B2 in **Perf.md** §0.13).  
**Scope:** wallet `BuildWitnessCache` / note witnesses across `-reindex` (not mainnet height-stop -- see **AtHeight.md**). Sync-lab reindex remainder (refuse / skip-wallet / LoadBlockIndex interrupt): **Perf.md** §0.8a / §0.13 -- do not edit Zero400 TODO from this track.

**Authoritative investigation:** **ExtTests.md** §1 (2026-07-01). This file is the **task hub** for CleanIndex / B1 / B2 / C.

---

## 1. Problem

No automated test exercised **shielded** witness rebuild on `-reindex` until B1:

| Existing | Covers |
|----------|--------|
| `qa/rpc-tests/reindex.py` (Tier A) | Transparent only: mine 3, `-reindex`, `getblockcount` |
| `WalletTests.CachedWitnessesEmptyChain/ChainTip/DecrementFirst` | Forward cache semantics in gtest (in gate) |
| `WalletTests.CachedWitnessesCleanIndex` | Intended reindex-style rebuild -- **quarantined** (see below) |
| `qa/rpc-tests/reindex_shielded.py` (B1) | Sapling shield -> `-reindex` -> balance + further spend |

Quarantine filter: `qa/zcash/test_filters.sh` -- `GTEST_PASS_EXCLUDE` / `GTEST_FAIL_ONLY` for `WalletTests.CachedWitnessesCleanIndex`.

---

## 2. `reindex_shielded.py` (ExtTests B1 -- preferred)

**Goal:** regtest RPC script that proves Sapling notes remain spendable after `-reindex`.

**Implemented flow:**

1. `initialize_chain_clean`, one node, wallet on (`NU_TEST_ARGS` via `start_node`).
2. Mine to maturity (`COINBASE_MATURITY` = 720).
3. Sapling `z_getnewaddress` / `z_sendmany` (t->z), mine 1.
4. Record tip + shielded balance.
5. Stop / restart with `-reindex` `-checkblockindex=1`.
6. Assert tip + balance unchanged; further `z_sendmany` (z->z) succeeds.

**Run:**

```bash
./qa/pull-tester/rpc-tests.sh reindex_shielded
```

**Tier:** Tier B pass once green (not Tier A -- maturity mining is slow).  
**Effort:** ~5–20 min per run.  
**Why preferred over gtest CleanIndex:** real `pcoinsTip` + `ReadBlockFromDisk` + `BuildWitnessCache`; no harness faking.

---

## 3. How to fix CleanIndex (ExtTests B2) -- postponed

`CachedWitnessesCleanIndex` is an **always-fail**, not flaky. Only this one `CachedWitnesses*` case is quarantined; the other three stay in the gate.

**Root cause:** the reindex loop calls `BuildWitnessCache` which needs `pcoinsTip` anchors and `ReadBlockFromDisk`. The gtest has neither (`pcoinsTip` null; blocks never written to disk) -> empty witnesses -> EXPECT flood -> `assert` in `GetSproutNoteWitnesses` -> abort.

**Fix paths (do not mix in one PR):**

| Path | What | When |
|------|------|------|
| **B1** | Ship `reindex_shielded.py` (this hub) | Preferred coverage; leave CleanIndex quarantined |
| **B2** | Seed harness `pcoinsTip` with Sprout/Sapling `(root -> tree)` anchors; make blocks disk-resolvable (temp block store or injectable reader); tear down globals; then remove name from `GTEST_PASS_EXCLUDE` / `GTEST_FAIL_ONLY` | Only if in-process coverage required after B1 |
| **C** | Replace `assert` on inconsistent witness roots with logged skip + `boost::none` | Separate reviewed PR; orthogonal crash hardening |

B1 closes the **coverage gap**. B2 closes the **gtest**. C closes the **assert-on-corrupt-cache** footgun. Keeping CleanIndex quarantined after B1 is intentional.

---

## 4. Witness read-path hardening (ExtTests C) -- postponed

Replace `assert` on inconsistent witness roots in `GetSproutNoteWitnesses` / `GetSaplingNoteWitnesses` with logged skip + `boost::none`. Separate reviewed change; consensus-adjacent wallet behavior.

---

## 5. Related tracks (do not merge into this task)

| Track | Relation |
|-------|----------|
| **OPS-AT-HEIGHT** / **AtHeight.md** | Mainnet short/tiny snaps; no `-stopatheight` |
| **OPS-REINDEX-RESUME** | File-cursor resume (`L`/`H`) -- shipped |
| **OPS-REINDEX-CONF** | Sticky `reindex=` warn (loud); refuse postponed |
| **TST-08** / PIR-03 | `-33` while `fBuildingWitnessCache` -- separate |
| **EXT-INSIGHT-FIXTURES** | Insight RPC promote -- orthogonal |

---

## 6. Cross-links

- Full RCA: **ExtTests.md** §1  
- Gate / filter: **TEST_ZERO.md** (CachedWitnesses*, Appendix)  
- Legacy backlog lines: **UpdateZero.md** TST-04 / TST-08  
- Code: `src/wallet/gtest/test_wallet.cpp` (`CachedWitnessesCleanIndex`), `src/wallet/wallet.cpp` (`BuildWitnessCache`)  
- Tracking: **TODO.md** -- **TST-WITNESS-REINDEX**
