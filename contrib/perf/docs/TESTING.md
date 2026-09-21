# Testing

The test and validation system: how to run it, the rules a test must follow,
known defects, and the plan for the suite. **The only document holding test
state.** Performance findings belong to their subject documents; this file
holds nothing about where sync time goes.

Work items live in `PLAN.md` as a single reference to this file; the detail is
here.

## Running the suites

| Suite | Invocation | Expected |
|-------|-----------|----------|
| Boost | `./src/test/test_bitcoin` | no errors |
| GTest | `qa/zcash/test_filters.sh` | all pass |
| RPC | `qa/pull-tester/rpc-tests.sh` | per tier, below |
| Lab gates | `contrib/perf/validate.sh` | lint and selftest PASS |

**Run GTest through `qa/zcash/test_filters.sh`, never bare.** A bare
`./src/zero-gtest` aborts in `WalletTests.CachedWitnessesCleanIndex` before
printing any summary, so the run looks like a crash with no pass count. The
filter script exists for this.

### `CachedWitnessesCleanIndex` is held failing on purpose

Added upstream as `1fc3c86f9` ("Add a reindex test that fails because of a bug
in decrementing witness caches", Zcash PR 1904) and excluded here by
`qa/zcash/test_filters.sh:7`. Its reindex scenario needs the `pcoinsTip` and
`ReadBlockFromDisk` path the GTest harness cannot provide. It aborts the
binary at `wallet.cpp:2594` on every platform, deterministically -- not
intermittently.

The underlying witness-cache decrement bug is real and unfixed upstream. It is
a product question, tracked in `PRODUCT.md`.

**Do not re-diagnose this.** It has been mistaken for an intermittent fault
more than once, at real cost each time. The rule in the gotchas table below --
a held test is not a failing test -- is the generalisation.

## Suite-run gotchas

Four results that look like platform defects and are not. Each cost time once.

| Item | What |
|------|------|
| a | **`Tests completed:`, not just exit code.** A runner can exit 0 having run nothing: a guard that declines to start the payload, or a killed waiter, is indistinguishable from a clean pass. Confirm the marker, then cross-check the totals against the per-script lines (`require_marker`, `require_counts_agree`) |
| b | **uniblake sibling.** Resolves to the checkout beside this tree with no configuration; its short HEAD is the package version, so a uniblake commit rebuilds it on its own |
| c | **Deliberately held.** `WalletTests.CachedWitnessesCleanIndex` is excluded in `qa/zcash/test_filters.sh` and fails unfiltered on every platform -- its reindex scenario needs the `pcoinsTip` + `ReadBlockFromDisk` path the gtest harness cannot provide |
| d | **`Permission denied` is a file mode**, not a port problem. `core.fileMode=true` strips a local `+x` on checkout, so a test committed `100644` fails before it runs. Check `git ls-files -s` first |
| e | **A skip is not a pass.** Three more instances found by sweeping for the shape: `check-security` failures were discarded by `\|\| true`; `rpc-tests.sh` fell off the end with status 0 when wallet/utils/bitcoind were not all enabled; and a tier selecting nothing printed "Tests completed: 0" and exited 0. All now fail |

## Suite plan: constants, tiers, failure modes

30/30). Tier U created, validated and emptied. Full Bfail/Efail sweep run: 16
of 39 pass. Standards written up in `POLICY.md` S2.2. Remaining: move the 16
after a stability check, and work the 23 failures by mode.



Zero's regtest `COINBASE_MATURITY` is **720**, not Bitcoin's 100. Tests ported
from Zcash assume the short maturity, so a chain that is tall enough upstream
has no spendable coinbase here.

**What already exists** (`qa/rpc-tests/test_framework/util.py`), and it is more
than the discussion suggests:

| Helper | Role |
|--------|------|
| `COINBASE_MATURITY = 720`, `mature_height(n)` | The constant and the target tip |
| `mine_to_height(node, nodes, h)` | Exact tip, for tests asserting NU heights |
| `mine_until_mature(node, nodes)` | Predicate loop; may overshoot |
| `mature_or_skip(node, nodes, label)` | Incremental, then bulk, then print and skip |
| `ensure_coinbase_utxos` / `ZERO_MINE_COINBASE=1` | Opt-in 1000-block bulk mine |
| `initialize_chain` | **Cached chain mined once to `COINBASE_MATURITY + 5` = 725**, reused across runs, rebuilt when stale |

The cache is the substantive fix: 720 blocks are mined once (69 MB on disk) and
copied per test, so maturity costs one build rather than one per test.

**The gap.** 64 tests call `initialize_chain_clean` -- an empty chain, no
mature coinbase -- against 3 that use the cached `initialize_chain`. Every
`clean` test must then mine 720+ blocks itself or skip. That ratio, not the
helper set, is what keeps tests in Tier B fail.

**Tier B fail is 28 tests and mixes four unrelated causes** ("porting /
maturity / comptool / Py3"), so its size overstates the maturity problem.
Sampled by running them [Measured, 2026-09-04]:

| Test | Actual cause |
|------|--------------|
| `mergetoaddress_sapling.py` | **None -- passes.** Ran twice, `Tests successful`, and uses no maturity helper |
| `wallet_listnotes.py` | Maturity: `assert_equal(200, getblockcount())` at lines 21, 31, 65 -- the upstream 100-maturity cache height |
| `wallet_sapling.py` | Assertion failure, same shape |
| `txindex.py` | **Fixed, now passes** -- two defects, neither maturity. See below |
| `reorg_limit.py` | Fails after mining; cause not yet isolated |

So of five sampled: two pass (one after a fix), two are hardcoded heights, one
unknown. Only two of five were maturity-related.

**`txindex.py`, resolved.** It carried two independent defects, and the
serialization one *was* a Python 2 leftover of the semantic kind rather than
the syntactic kind:

1. `unspent[0]["amount"] * 100000000` -- JSON-RPC parses money as `Decimal`,
   and `Decimal * int` stays `Decimal`, which `struct.pack("<q", ...)` rejects.
   Under Python 2 the value was a float and packed by coercion. Fixed with
   `int(... * COIN)`, the idiom the passing `addressindex.py` already uses.
2. `assert_equal(verbose["vout"][0]["valueZat"], 5000000000)` -- Bitcoin's
   50-coin subsidy; Zero's is 10. Fixed by asserting against the amount the
   node reported for that output, so the test tracks txindex behaviour rather
   than the subsidy schedule.

Passes twice in a row.

**Syntactic Python 2 leftovers are gone.** A scan across every
`qa/rpc-tests/*.py` and the framework for `print "`, `has_key(`,
`.iteritems()`, `.itervalues()`, `.iterkeys()`, `xrange(`, and
`except E, e` returns **nothing**. What remains is this semantic class --
`Decimal` where an `int` is required, and division semantics -- which no
syntax check finds.

**The hardcoded-50 pattern persists elsewhere.** `mergetoaddress_helper.py`,
`wallet_mergetoaddress.py` and `wallet_shieldcoinbase.py` each assert
`immature_balance == 50` and `getbalance() == 50`. None of the three is in any
tier list -- the `_sapling` variants run instead -- so they are unexercised
rather than passing. Worth fixing when they are next run, not before.

**List reconciliation** [Measured, 2026-09-04]. 97 test files, and after
correction **three** runnable tests were in no list -- not the ten a first pass
suggested. That pass used a regex that missed hyphenated names, so
`bip65-cltv-p2p.py`, `bipdersig-p2p.py` and `p2p-acceptblock.py` were reported
as hidden while already filed under Bfail and Efail.

Genuinely unfiled, now **Tier U** (`-U`, in `-list-csv`, its own runner):
`wallet_mergetoaddress.py`, `zcjoinsplit.py`, `zcjoinsplitdoublespend.py`.
Tier U is not a verdict -- it means never placed. Run each once and move it to
the tier its result earns.

Correctly excluded, no `__main__` or no `run_test`: `mergetoaddress_helper.py`,
`tx_expiry_helper.py`, `wallet_shieldcoinbase.py` (variant base class),
`wallet_shieldcoinbase_sprout.py`.

The inventory now has no duplicate entries: A 10, B 34, Bfail 28, E 8,
Efail 5, U 3.

**Next steps, cheapest first:**

| # | Step | Why |
|---|------|-----|
| a | Re-run the 28 and re-file by observed cause | The list is stale enough that at least one test in it passes; triage from evidence, not the original label |
| b | Fix hardcoded heights (`wallet_listnotes.py`, `wallet_sapling.py`) | Replace `assert_equal(200, ...)` with `mature_height()`-relative assertions. Contained, and the helpers already exist |
| b2 | Fix hardcoded subsidies where a test is actually run | Assert against the node's reported amount, as `txindex.py` now does and `getrawtransaction_insight.py` already did |

**Converted so far** [2026-09-04]. `COINBASE_SUBSIDY = 10` and
`block_reward(n)` were added to `test_framework/util.py` beside
`COINBASE_MATURITY`, so both constants live in one place:

| File | Change | Result |
|------|--------|--------|
| `txindex.py` | Decimal->int for `struct.pack`; assert the node's own amount | **passes** (Bfail) |
| `wallet_listnotes.py` | literal 200/201/202 -> `base_height` + delta | **passes** (Bfail) |
| `mergetoaddress_helper.py`, `wallet_mergetoaddress.py`, `wallet_shieldcoinbase.py` | `50` -> `block_reward(5)` | unlisted; unverified |
| `bip65-cltv-p2p.py`, `bipdersig-p2p.py` | `generate(100)` -> `generate(COINBASE_MATURITY)` before spending the coinbase | unlisted; unverified |
| `reorg_limit.py` | literals -> `MAX_REORG_LENGTH` and a tip-relative base | **passes** (was Bfail) |
| `wallet_treestate.py` | comment only | still fails, and **not for a maturity reason** -- see below |

**Not every 100 is maturity.** `reorg_limit.py`'s 99 and 100 are a reorg at
exactly the limit and one past it: `MAX_REORG_LENGTH = 99`, rejected when
`reorgLength > 99`. Converting either to 720 would destroy what the test
checks. Both, and the height assertions, now derive from a
`MAX_REORG_LENGTH` in `test_framework/util.py` kept in sync with `src/main.h`.
Each numeric site has to be read for what the number means.

**Correction: `wallet_treestate.py` passes.** An earlier revision of this note
recorded it as blocked by `-regtestprotectcoinbase`. That was wrong: the run it
was based on carried a broken `mine_to_height` edit of mine. Run clean, it
passes, and both the edit and its comment were removed. The mechanism it
described -- `SelectCoins` taking the no-coinbase list that `AvailableCoins`
builds by skipping `IsCoinBase() && !fIncludeCoinBase` (`wallet.cpp:4278`,
`4493`), with "Coinbase funds can only be sent to a zaddr" at `4821` -- is an
accurate description of the code, but is not why this test failed.

**Next steps, cheapest first:**

| # | Step | Why |
|---|------|-----|
| a | Re-run the Bfail/Efail set and re-file by observed cause | Done 2026-09-04; see the sweep below |
| b | Fix hardcoded heights and subsidies | Replace literals with `mature_height()` / `block_reward()`; the helpers exist |
| c | Move passing tests out of Bfail | `mergetoaddress_sapling.py` at minimum; a known-broken list containing passing tests trains people to ignore it |
| d | Consider `initialize_chain` for tests that only need a funded wallet | Converts a 720-block mine per test into a cache copy. Only where the test does not require a clean chain |
| e | Split the Py3/comptool tests into their own tier | They are not maturity work and do not belong in the same queue |
| f | Place unfiled tests in a tier | Done: Tier U created, validated and emptied |

**Full Bfail/Efail sweep** [Measured, 2026-09-04, all 39 scripts run once]:

| Outcome | Count |
|---------|------:|
| **PASS** | **16** |
| FAIL, assertion | 15 |
| FAIL, comptool | 3 |
| FAIL, other | 4 |
| FAIL, "Method not found" | 1 |

**41% of the known-broken set passes.** Passing: `mergetoaddress_sapling`,
`mergetoaddress_mixednotes`, `mergetoaddress_sprout`, `rawtransactions`,
`mempool_tx_expiry`, `fundrawtransaction`, `signrawtransaction_offline`,
`regtest_signrawtransaction`, `key_import_export`, `zkey_import_export`,
`wallet_shieldcoinbase_sapling`, `wallet_protectcoinbase`, `wallet_nullifiers`,
`prioritisetransaction`, `wallet_treestate`, `wallet_overwintertx`.

A list where two in five entries are green is not a triage tool; it is a
backlog nobody has re-read. Moving them is step (c), and the sweep is the
evidence for it. Each was run once here -- a 10x stability check like the one
the three moved tests got should precede the move.

**The 23 failures, by mode.** Grouped by what actually went wrong, which is
not how the tier groups them:

| Mode | n | Tests | Suggested next step |
|------|--:|-------|---------------------|
| Assertion | 15 | `finalsaplingroot`, `mempool_nu_activation`, `merkle_blocks`, `p2p-acceptblock`, `rescan_import`, `shorter_block_times`, `sprout_sapling_migration`, `turnstile`, `wallet_addresses`, `wallet_changeaddresses`, `wallet_listreceived`, `wallet_mergetoaddress`, `wallet_persistence`, `wallet_sapling`, `zcjoinsplitdoublespend` | Read each assertion. The three fixed so far were all literals -- a Bitcoin height, a Bitcoin subsidy, a cache tip. Expect the same class, and check `POLICY.md` S2.2 before editing |
| comptool | 3 | `bip65-cltv-p2p`, `bipdersig-p2p`, `invalidblockrequest` | Not maturity or subsidy. The comptool harness is a separate porting job; give it its own tier so it stops diluting this one |
| Other | 4 | `getblocktemplate_proposals`, `mempool_reorg`, `pruning`, `smartfees` | Unclassified -- each needs one read of its log. `pruning` mines 200 and may be a height case; the rest are unknown |
| Method not found | 1 | `zcjoinsplit` | Sprout raw-joinsplit RPC absent. Retired, not fixable |

**Per-test logs** from the sweep are at `/tmp/sw_<test>.log` for the session
that produced this; re-running `-Bfail` regenerates them. The counts above are
one run each, so a mode may be wrong for a flaky test -- treat the grouping as
a triage starting point, not a verdict.

(a) is the prerequisite: the current grouping cannot be trusted to say what is
maturity-related.

**Kanban: ToDo. Effort M.** Test-harness work, no product change.