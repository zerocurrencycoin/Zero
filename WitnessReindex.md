# Shielded witness rebuild and reindex coverage

**Status:** findings and proposals captured; implementation **postponed** (**TST-WITNESS-REINDEX** in **TODO.md**).  
**Scope:** wallet `BuildWitnessCache` / note witnesses across `-reindex` (not mainnet height-stop -- see **AtHeight.md**).

**Authoritative investigation:** **ExtTests.md** §1 (2026-07-01). This file is the **task hub** and the **`reindex_shielded`** design note so CleanIndex / B1 / B2 / C are not scattered only across TEST_ZERO / UpdateZero / ExtTests.

---

## 1. Problem

No automated test exercises **shielded** witness rebuild on `-reindex`:

| Existing | Covers |
|----------|--------|
| `qa/rpc-tests/reindex.py` (Tier A) | Transparent only: mine 3, `-reindex`, `getblockcount` |
| `WalletTests.CachedWitnessesEmptyChain/ChainTip/DecrementFirst` | Forward cache semantics in gtest (in gate) |
| `WalletTests.CachedWitnessesCleanIndex` | Intended reindex-style rebuild -- **quarantined** (see below) |

Quarantine filter: `qa/zcash/test_filters.sh` -- `GTEST_PASS_EXCLUDE` / `GTEST_FAIL_ONLY` for `WalletTests.CachedWitnessesCleanIndex`.

---

## 2. Proposed `reindex_shielded.py` (preferred -- ExtTests B1)

**Goal:** regtest RPC script that proves Sapling notes remain spendable after `-reindex`.

**Sketch:**

1. `initialize_chain_clean`, one node, wallet on.  
2. Mine to maturity (`COINBASE_MATURITY` = 720).  
3. `z_getnewaddress` / `z_sendmany` (t->z or z->z), mine enough for spendability.  
4. Record shielded balance / note count.  
5. `stop` / restart with `-reindex` (and `-checkblockindex=1` optional).  
6. Wait until tip restored; assert shielded balance unchanged and a further `z_sendmany` succeeds.

**Tier:** Tier B pass (or Ext) once green -- not Tier A (maturity mining is slow).  
**Effort:** M (~0.5–1 day) + **~5–20 min** per run.  
**Why preferred over gtest CleanIndex:** real `pcoinsTip` + `ReadBlockFromDisk` + `BuildWitnessCache`; no harness faking.

**Not started:** no `qa/rpc-tests/reindex_shielded.py` in tree yet.

---

## 3. CleanIndex gtest (ExtTests B2) -- postponed

Revive `CachedWitnessesCleanIndex` only if in-process coverage is required after B1. Needs harness `pcoinsTip` anchors + disk-backed blocks. Higher risk/effort than B1.

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
- Tracking: **TODO.md** -- **TST-WITNESS-REINDEX** (postponed)
