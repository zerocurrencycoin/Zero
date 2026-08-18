# ExtTests -- Extended test investigations (witness, mining/Equihash, external interfaces)

Standalone record of three test investigations completed 2026-07-01/02. These
extend the **TST-\*** backlog items in `UpdateZero.md` §4 (Testing) with full
root-cause analysis, verified run results, and proposed fixes. Cross-references
to `UpdateZero.md` TST-NN / §-numbers are kept so this file can be folded back if
desired.

**Baseline (2026-07-01):** `./contrib/run-tests.sh --all` (no `--strict`) passes
clean -- C++ suites, quick checks, and the then-current pass-tier RPC set
(**34** invocations at that date), 0 failures. As of **2026-07-22**, pass-tier
**`-all`** is **47** (A10+B29+E8 including **`getalldata_scenario`** / **`rpc_workqueue_full`** / Insight B-pass + Ext greens; exact lists **TEST_ZERO.md** §3).
Failures discussed below appear only when a test is run *outside* the harness
filter (raw `zero-gtest` binary) or is in a known-fail tier that `--all` does not
gate on.

---

## 1. `CachedWitnessesCleanIndex`: reindex coverage gap + `GetNoteWitnesses` crash-on-corrupt-cache

*(Relates to `UpdateZero.md` TST-04, TST-08, §2 Witness path, §3.3 CachedWitnesses, PIR-03. Investigation 2026-07-01.)*

**Task hub (postponed):** **WitnessReindex.md** -- proposed **`reindex_shielded.py`** (B1), CleanIndex gtest (B2), witness hardening (C). Tracking: **TST-WITNESS-REINDEX**.

Extends TST-04 with precise root cause and two concrete, separable proposals
(B: harness/coverage; C: hardening). This section remains the RCA record; TST-04's
one-line "seed `CCoinsViewCache`" summary is superseded here.

### Finding 1 -- not a regression, not a tier issue
`WalletTests.CachedWitnessesCleanIndex` (`src/wallet/gtest/test_wallet.cpp:1523`)
is a **deliberately quarantined C++ known-fail**, not an RPC tier item (Tier
A/B/E are the Python RPC tiers only). It is excluded from the pass gate by the
gtest **filter**, not by a `DISABLED_` prefix:
- `qa/zcash/test_filters.sh:9` -- `GTEST_PASS_EXCLUDE='-WalletTests.CachedWitnessesCleanIndex'` (default and `--all`).
- `qa/zcash/test_filters.sh:10` -- `GTEST_FAIL_ONLY='WalletTests.CachedWitnessesCleanIndex'` (`run-tests.sh --fail` diagnostic mode).
- The `TEST(...)` macro is intentionally left enabled so `--fail` can still exercise it. Running the raw binary (`./src/zero-gtest` with no filter) therefore hits the failure by design; the supported entry point is `./contrib/run-tests.sh` (any mode), which applies the filter. Documented context: **TEST_ZERO.md** ("CachedWitnesses* gtest port (except CleanIndex)"); ported in commit `4f430f5c5`.

### Finding 2 -- why it cannot pass in the current harness
The reindex loop (`test_wallet.cpp:1566`) drives
`BuildWitnessCache(&indices[i], false, &blocks[i])` block-by-block.
`VerifyAndSetInitialWitness` sets the **initial** witness from `pblockIn` (the
June port wired this via `SetBlockCommitmentTrees`), but `BuildWitnessCache`'s
incremental `while` loop (`wallet.cpp:1607`) then walks `chainActive` and for
**every subsequent block** requires two things the gtest harness does not
provide:
- `pcoinsTip->GetSproutAnchorAt(...)` / `GetSaplingAnchorAt(...)` (`wallet.cpp:1619,1623`) -- `pcoinsTip` is **null** in the harness.
- `ReadBlockFromDisk(block, pblockindex, ...)` (`wallet.cpp:1627`) -- blocks are **never written to disk** by the test.

Earlier notes' witnesses are never incremented past their initial height ->
`GetWitnessesAndAnchors` returns empties -> ~12,000 `EXPECT_TRUE` failures ->
mismatched cached roots -> `assert(*rt == witnesses[i]->root())` at
`wallet.cpp:2445` -> `SIGABRT` (exit 134), which also aborts the rest of the
gtest binary.

### Finding 3 -- real coverage gap
Audited the RPC suite for equivalent coverage. `reindex.py` and
`rescan_startup.py` are **taddr-only** (no shielded notes). `wallet_treestate.py`
exercises witness/anchor logic but only through normal forward block connection
(`z_sendmany` + `generate`), never the reindex/reorg rebuild path. **No automated
test anywhere** exercises `BuildWitnessCache` rebuilding shielded witnesses on
reindex. Quarantining `CachedWitnessesCleanIndex` leaves that path with zero
coverage.

### Proposed solution B -- close the reindex coverage gap
Two routes; the RPC route is preferred.
- **B1 (preferred) -- shielded RPC reindex test (`reindex_shielded.py`).** Implemented: `qa/rpc-tests/reindex_shielded.py` (hub **WitnessReindex.md** §2). Sapling shield, `-reindex`, assert balance + further `z_sendmany`. Exercises real `BuildWitnessCache` + `pcoinsTip` + `ReadBlockFromDisk`. Run: `./qa/pull-tester/rpc-tests.sh reindex_shielded`. Promote to Tier B pass when green; CleanIndex stays quarantined.
- **B2 (heavier) -- port the gtest.** Give the gtest harness (a) a `CCoinsViewCache`-backed `pcoinsTip` seeded with each block's Sprout/Sapling `(root -> tree)` anchors (extend the existing `SetBlockCommitmentTrees` helper), and (b) a disk-resolvable `ReadBlockFromDisk` -- either write blocks to a temp block store, or refactor `BuildWitnessCache` to accept an injectable block source. Medium-high effort; risk of cross-test global state leakage (must tear down `pcoinsTip` alongside the existing `mapBlockIndex` cleanup). Only pursue if in-process coverage is specifically wanted; otherwise B1 subsumes it. If completed, un-quarantine by removing the name from `GTEST_PASS_EXCLUDE`/`GTEST_FAIL_ONLY` in `qa/zcash/test_filters.sh`.

### Proposed solution C -- harden `GetSproutNoteWitnesses` / `GetSaplingNoteWitnesses` (crash-on-corrupt-cache)
Low effort, orthogonal to B. Two symmetric call sites (`wallet.cpp:2445` Sprout,
~`2472` Sapling) `assert(*rt == witnesses[i]->root())` on inconsistent cached
anchors. This is a wallet **read path** (invoked when assembling `z_sendmany`
spends), so an internally inconsistent witness cache (interrupted rebuild after
crash/kill, reorg edge case, upgrade/downgrade migration bug) aborts the node via
`SIGABRT` instead of surfacing a recoverable error -- and `assert` compiles out
under `-DNDEBUG`, so release builds get no protection and would instead proceed
with a **wrong anchor** (spend rejected or malformed). Proposed change: replace
the abort with a logged skip that returns no witness for the offending note
(callers already handle `boost::optional` = `boost::none`):

```cpp
if (!rt) {
    rt = witnesses[i]->root();
} else if (*rt != witnesses[i]->root()) {
    LogPrintf("%s: inconsistent witness anchor for note %s (cache corrupt?); "
              "skipping; consider -rescan.\n", __func__, note.hash.ToString());
    witnesses[i] = boost::none;   // never return a mismatched-anchor witness
    continue;
}
```

*Caveat:* this changes consensus-adjacent wallet behavior; it must **log loudly**
(and ideally set a wallet-health flag) so real corruption is not silently hidden.
Ship as its own reviewed PR, ideally with maintainer sign-off. Side benefit: with
C in place, B2's failure mode degrades to soft errors instead of `SIGABRT`, which
is friendlier to CI.

*Non-action:* disabling the test with a `DISABLED_` prefix is **not** needed --
the `test_filters.sh` exclusion is the correct mechanism and already keeps
default/`--all` runs green.

*Key files:* `src/wallet/gtest/test_wallet.cpp:1523`, `src/wallet/wallet.cpp`
(`BuildWitnessCache` 1576, `VerifyAndSetInitialWitness` 1320,
`DecrementNoteWitnesses` 1255, `GetSproutNoteWitnesses`/`GetSaplingNoteWitnesses`
~2429/2456), `qa/zcash/test_filters.sh`, `qa/rpc-tests/reindex.py`.

---

## 2. Equihash params and mining-test status

Relates to `UpdateZero.md` TST-05. Zero instantiates **(192,7)** (mainnet/testnet) and **(48,5)** (regtest) only; other `n,k` throw.

Boost `equihash_tests` covers genesis headers, `1927EQ.txt` / `1927EQ_h1.hex` validators, and `solver_testvectors_48_5` when `ENABLE_MINING`. GTest `test_equihash.cpp` is the (48,5) solver cancel / array suite. Timed (192,7) solve/verify is wallet RPC `zcbenchmark`, not a frozen nonce table.

Remaining gap: `src/gtest/test_miner.cpp` only checks `Miner.GetScriptForMinerAddress`. RPC `generate` on regtest is (48,5). A live `CreateNewBlock` + solve smoke (regtest) is optional later; do not resurrect a parameter-frozen `blockinfo[]`.

*Key files:* `src/test/equihash_tests.cpp`, `src/gtest/test_equihash.cpp`, `src/gtest/test_miner.cpp`, `src/crypto/equihash.{h,cpp}`, `src/chainparams.cpp`.

---

## 3. External-interface (RPC / REST / CLI / config) coverage for third-party tools

*(Relates to `UpdateZero.md` TST-01, TST-03, DOC-02, §8 RPC/options CSV,
OPS-EXPLORER; TEST_ZERO.md insight-cache analysis. Audit 2026-07-02.)*

Motivated by the external-integration study. Question posed: which interfaces
that wallets, explorers, and pool/monitoring tools depend on are under-tested or
untested. Findings distinguish *quarantined-but-written* from *genuinely
thin/absent*.

### Surface measured
**152** registered RPC commands (across `src/rpc/*.cpp`, `src/wallet/rpc*.cpp`);
**8** REST endpoints
(`/rest/{tx,block,block/notxdetails,headers,chaininfo,mempool/info,mempool/contents,getutxos}`,
`src/rest.cpp`); ZMQ publisher; `zero.conf` option surface. ~30+ RPCs are
Zero/Zcash-specific and integration-critical: the `z_*` shielded family,
`zeronode` / `znbudget` / `getzeronode*`, and the Insight explorer index set
(`getaddressbalance/utxos/deltas/txids`, `getspentinfo`, `getblockhashes`).

### Finding A -- explorer/REST interfaces are quarantined AND were broken (highest-leverage gap)
The tests that exercise what explorers and Insight-based wallets consume --
`rest.py`, `addressindex.py`, `spentindex.py`, `timestampindex.py`,
`getrawtransaction_insight.py` -- were in **`testScriptsTierBFailDebug`**
(`qa/pull-tester/rpc-tests.sh`); none was in a pass tier, so `--all`
(A + B-pass + E-pass) never gated on them. **Empirically verified 2026-07-02 --
ran all five individually via `rpc-tests.sh <name>`; result: 0/5 pass.** This
*corrects* an earlier assumption that the block was cache-only: the scripts
self-provision insight
(`extra_args = [['-debug','-txindex','-experimentalfeatures','-insightexplorer']]*3`),
so the failures are **real, in three distinct classes**:

1. **Python-3 port bugs (test-code).** `rest.py:57` -- `body.decode('utf-8')` on the binary `/rest/getutxos.bin` endpoint (`0xd2` is not valid UTF-8; the `.bin` response must stay bytes). `getrawtransaction_insight.py:69` and `spentindex.py:85` -- `vout = filter(lambda ...)` then `vout[0]`: in Py3 `filter` returns a non-subscriptable iterator (needs `list(...)`). `timestampindex.py` -- `assert_equal(list, range(...))`: a bare `range` object is compared to a list (needs `list(range(...))`). `addressindex.py` -- `list index out of range` on `listunspent()[0]` before maturity.
2. **Zero value/height assumptions.** `addressindex.py` maturity/height math assumes upstream `COINBASE_MATURITY=100`; Zero is **720** (same class as the `wallet.py` balance mismatch in `UpdateZero.md` §3.3).
3. **`vin.valueSat` -- resolved as stale test expectation, not a code gap.** `spentindex.py`/`getrawtransaction_insight.py`/`addressindex.py` asserted `tx['vin'][0]['valueSat']`. Code lookup (`src/rpc/rawtransaction.cpp`): the spent-index **vin** block emits `value` + **`valueZat`** (lines 182-183), never `valueSat`; **vout** emits `value` + `valueZat` + `valueSat` (200-202), where `valueSat` is a legacy alias carrying the same integer as `valueZat`. No production code or in-tree Insight consumer references `vin.valueSat` -- only these three tests did. So Zcash/Zero renamed `valueSat`->`valueZat`; vout keeps the alias for old clients, vin was never given it. Conclusion: the RPC is internally consistent; the **test** was wrong. Fixed by asserting `valueZat` on vin (no `rawtransaction.cpp` change). If a future Insight/Blockbook client is found to require `valueSat` on vin, adding the one-line alias mirroring vout is trivial -- but nothing in-tree needs it today.

So Zero's REST API and Insight index RPCs -- the backbone of `insight-api-zero` /
block explorers -- had **no passing coverage in the gate, and the scripts did not
pass at all** before this work.

#### Fixes applied 2026-07-02 (Steps 1-2 + test-side of Step 3; production code untouched)
Edited the five scripts:
- **Py3 ports:** `list(filter(...))` at every `filter(...)[i]` site (`spentindex`, `getrawtransaction_insight`, `addressindex`); `list(range(...))` in `timestampindex` `assert_equal`; `rest.py` reads the `/rest/getutxos.bin` response via `response_object=True` + `.read()` (raw bytes, no utf-8 decode).

**Script lineage (clarified):** these are **Zcash-origin** Insight qa scripts (bundled `-insightexplorer` args). Failures against Zero are **Zero consensus/fixture mismatches** (maturity **720**, regtest founders vout gated until fee-start height), not “Pirate tests.” Pirate’s own suite uses **separate** `-addressindex` / `-spentindex` / `-timestampindex` flags.
- **Maturity/height:** replaced hardcoded upstream-100 heights (102/106/107/108/109/110/111) with `COINBASE_MATURITY`-relative expressions (`mature_tip + N`, and `COINBASE_MATURITY + 2` in `rest.py`), keyed off the `mature_height(5)` helper the scripts already call.
- **valueSat -> valueZat** on all vin assertions (item 3).

#### Verification runs 2026-07-02 (after the fixes): 3/5 now pass, up from 0/5
**PASS:** `timestampindex.py`, `getrawtransaction_insight.py`, `rest.py` (the last after the additional `rest.py` Py3 fixes documented below).
**Promoted 2026-07-22 (EXT-INSIGHT-FIXTURES):**
- **`spentindex.py` / `addressindex.py` -- Zero single-output regtest coinbase.** Scripts assumed Zcash 2-vout coinbase. **Decision: adapt tests to Zero settings** (maturity **720**, tip ~725 **below** fee-start **1000** → **1-vout**; halving-aware miner balances). Edits applied and **verified PASS** 2026-07-21; **re-PASS + moved to Tier B pass** 2026-07-22. Founders transition coverage: **`founders_window.py`** (ExtTests §4).
- **`rest.py` -- RESOLVED as two more Python-3 idiom bugs; the REST API is correct.** Investigated 2026-07-02. The `.bin` decode fix exposed later Py2 relics, fixed in turn:
  - **`rest.py:161` (getutxos bin hash).** Was `hex(deser_uint256(output))[2:].zfill(65).rstrip("L")`. `deser_uint256` returns the right integer, but a uint256 is **64** hex chars and `.zfill(65)` padded to **65**, so it could never equal the 64-char `getbestblockhash()`; `.rstrip("L")` is a Py2 long-suffix relic. Verified by simulation: `zfill(65)` never matches, `zfill(64)` matches exactly. Fixed to `.zfill(64)` (dropped `rstrip`). **Not** a byte-order or REST-payload issue.
  - **`rest.py:256,264` (block/header hex compare).** `response_str.encode("hex")` -- Py3 removed the `"hex"` codec from `str/bytes.encode`. `response_str`/`response_header_str` are raw block **bytes** (`.bin` endpoint); the `.hex` endpoint returns ASCII-hex bytes. Fixed with `binascii.hexlify(...)` (returns bytes, matches the hex endpoint). `binascii` already imported.
  Conclusion: `rest.py`'s failures were **entirely test-side Python-3 porting**, no REST/serialization defect. **Verified 2026-07-02: `rest.py` now PASSES.**

#### Fix A (revised) -- ordered plan
Not a cache/tier reshuffle alone.
1. Port the five scripts to Python 3 (`list(filter(...))`, `list(range(...))`, keep `.bin` responses as bytes). **[done]**
2. Re-base height/maturity math on `COINBASE_MATURITY=720` (reuse the `mature_height` / `mature_or_skip` helpers already used elsewhere). **[done]**
3. Resolve the `vin.valueSat` question -- confirmed a stale test expectation; asserted `valueZat` instead. **[done, no code change]**
4. `rest.py` deeper failures -- resolved (two more Py3 idioms; see above). **[done]** `rest.py` passes.
5. `spentindex`/`addressindex` -- adapt to Zero 1-vout regtest settings. **[done 2026-07-21; both PASS]**
6. Promote greens from `testScriptsTierBFailDebug` to a pass group; acceptance under `./contrib/run-tests.sh --all --strict`. **[done 2026-07-22 for the five insight scripts -> Tier B pass]** Process lesson (verify ≠ promote): **TEST_ZERO.md** section **Process -> Tier engagement**.

#### Related: pure `-txindex` (`txindex.py`) -- Bfail Debug 2026-07-22
Orphan Bitcoin-era script (was not in `rpc-tests.sh`). Complements insight suite; does **not** replace it. Inventoried under **`testScriptsTierBFailDebug`**. Failures / suggested fixes: **TEST_ZERO.md** `txindex.py` debug (Py3 `Decimal` into `CTxOut.nValue`; Bitcoin **50**-ZER asserts vs Zero regtest **10** ZER). Run: `./qa/pull-tester/rpc-tests.sh txindex`. Promote to B pass only after green.

### Finding B -- shielded (`z_*`) coverage is good; a few high-value holes remain
`z_sendmany`, `z_shieldcoinbase`, `z_mergetoaddress`, `z_listunspent`,
import/export, nullifiers, treestate, and anchor-fork are covered by Tier B pass
scripts (`wallet_*`, `zkey_import_export.py`, `wallet_treestate.py`,
`wallet_anchorfork.py`). Gaps: **`z_setmigration`/`z_getmigrationstatus`** -- a
test *exists* (`qa/rpc-tests/sprout_sapling_migration.py`) but is **retired**
(`testScriptsTierBFailRetired`; correction to first pass, which implied it was
absent), so migration is un-gated; **`getalldata`** (the Zero aggregate
explorer/wallet RPC that Insight-style clients call) has only the Boost
`rpc_zero_exclusive_tests.cpp` argument-validation case (TST-01), no functional
round-trip. `z_getpaymentdisclosure`/`z_validatepaymentdisclosure` are covered by
Tier A `paymentdisclosure.py` (adequate).
- *Fix B (prototype):* triage `sprout_sapling_migration.py` for the same Py3/maturity issues as Finding A and un-retire if the failures are test-side; add a `getalldata` round-trip assertion to an existing wallet script.

### Finding C -- zeronode RPCs are argument-validated only (already tracked)
`zeronode`, `znbudget`, `getzeronode*` have Boost argument/error tests scoped in
**TST-03**, but no functional integration (requires 10,000 ZER collateral +
activation). Cross-reference, not new work here.

### Finding D -- config-file / CLI-surface parity has no automated check
The `UpdateZero.md` §8 RPC/options CSV is a **manual** verification snapshot;
nothing asserts at build/CI time that documented `zero.conf` options and RPC help
text still match the registered command table (drift is how `-port` help showed
Zcash defaults -- see DOC-02).
- *Fix D (prototype):* a lightweight test that dumps the live command table (`help` RPC) and the option list, diffs against the committed CSV, and fails on drift. Cheap regression guard for exactly the external-tool-facing contract the study tracks.

### Priority
**A** first (largest real gap, directly serves explorers/wallets; Py3/maturity
already done, coinbase-shape + `rest.py` deser remain), then **D** (cheap drift
guard), then **B**, then **C** (blocked on collateral harness).

*Key files:* `qa/pull-tester/rpc-tests.sh` (tier arrays),
`qa/rpc-tests/{rest,addressindex,spentindex,timestampindex,getrawtransaction_insight}.py`,
`qa/rpc-tests/test_tier_inventory.csv`, `src/rest.cpp`, `src/rpc/misc.cpp`
(`fInsightExplorer` gating), `src/wallet/rpcwallet.cpp` (`z_*`),
`src/rpc/rawtransaction.cpp` (`value`/`valueZat`/`valueSat` emission),
`src/zeronode/payments.cpp` (founders-output gate),
`src/test/rpc_zero_exclusive_tests.cpp` (TST-01), TEST_ZERO.md (insight cache
analysis).

---

## 4. Founders window (regtest)

Constants (C++ and Python): **`REGTEST_FOUNDERS_START`/`STOP`** = **1000**/**1500**.
Active **`[START, STOP)`**: base **10.8**, founders **7.5%**, two coinbase vouts.
Outside: one miner vout (base **10** below START; **10.8** at/after STOP).
Maturity stays **720**.

**RPC / Insight:** **`founders_window.py`** (Tier B) mines START/STOP boundaries,
asserts subsidy + coinbase shape + GBT, and with `-insightexplorer` checks
`getaddressbalance` / `getaddresstxids` on regtest payee
`t2FwcEhFdNXuFMv1tcYwaBJtYVtMj8b1uTg`. Helpers: **`block_subsidy`**,
**`founders_share`**, **`miner_share`**, **`subsidy_range`**, **`miner_range`**.
Insight scripts at tip ~725 stay below START (1-vout). **EXT-INSIGHT-SUPERSET**
founders-index slice: **done** in this script (2026-07-24).

---

## Working-tree changes from this investigation
Test-script edits only (no production code):
- `qa/rpc-tests/rest.py`
- `qa/rpc-tests/addressindex.py`
- `qa/rpc-tests/spentindex.py`
- `qa/rpc-tests/getrawtransaction_insight.py`
- `qa/rpc-tests/timestampindex.py`

`UpdateZero.md` is intentionally left unmodified; this file is the standalone
home for the above.
