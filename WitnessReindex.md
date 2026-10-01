# Shielded witness rebuild and reindex coverage

Test coverage for wallet `BuildWitnessCache` and note witnesses across `-reindex`, and the two remaining options. Tracked as TST-WITNESS-REINDEX.

---

## 1. Current coverage

| Test | Covers | Status |
|------|--------|--------|
| `qa/rpc-tests/reindex.py` | Transparent: mine, `-reindex`, `getblockcount` | Tier A |
| `qa/rpc-tests/reindex_shielded.py` | A Sapling note stays spendable after `-reindex`, through real `BuildWitnessCache`, `pcoinsTip`, and `ReadBlockFromDisk` | Tier B pass |
| `WalletTests.CachedWitnessesEmptyChain` / `ChainTip` / `DecrementFirst` | Forward witness cache semantics | GTest, in gate |
| `WalletTests.CachedWitnessesCleanIndex` | Reindex-style rebuild in process | Quarantined (`qa/zcash/test_filters.sh` `GTEST_PASS_EXCLUDE` / `GTEST_FAIL_ONLY`) |
| `rpc_zero_exclusive_tests` | RPC error **-33** while `fBuildingWitnessCache` is set (PIR-03) | Boost, in gate |

---

## 2. Remaining options

**Revive `CachedWitnessesCleanIndex`.** Do this only if in-process coverage is needed beyond `reindex_shielded.py`. The fixture needs `pcoinsTip` anchors and disk-backed blocks, which the default wallet fixture does not provide. Higher effort and risk than the RPC script it would duplicate.

**Witness read-path hardening.** `GetSproutNoteWitnesses` / `GetSaplingNoteWitnesses` (`src/wallet/wallet.cpp`) `assert` that each witness root matches the anchor. Proposal: replace the asserts with a logged skip returning `boost::none`, so a corrupt or empty witness cache cannot abort the node. This is consensus-adjacent wallet behavior and needs its own reviewed change and a test that feeds an inconsistent cache.
