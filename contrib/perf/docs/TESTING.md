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

| C1 Documentation consolidation | **InTest** | Open | M | `POLICY.md` S2.0 |
| E2 Script corpus + schema | **InProgress** | Open | M | this file, E2 |
| C2 Remaining measurement gaps | ToDo | Open | M | `FINDINGS.md` S4 |
| C3 Inherited build/DB defects | ToDo | Open | M | `../BUILD_RECONFIG.md` |
| C4 Per-workload utilization profile | ToDo | Open | L | this file, C4 |
| D1 Equihash / blake2 integration | **InProgress** | Open | M | `../equ/README.md` |
| D2 `Xc.reserve()` | **Ready** | Open | XS | verified `equihash.cpp:384`; this file, D2 |
| D3 Fold `len` to compile-time | **InTest** | Open | XS | **applied** `equihash.cpp:557` (`05cdcefe6`); 1.22x (M-EQ-D3-SORT) |
| D5 tromp path + **now the default** | **Finished** | -- | S | 5.69x (M-EQ-TROMP-SPEEDUP); `test-logs/tromp-default-20260909/` |
| F1 Regression gate on validate | **InTest** | Open | S | `validate.sh` |
| F2 CI wiring | -- | **Postponed** | S | needs repo settings |
| R0 Note locking | -- | **Assessed** | -- | closed into P9 |
| GROTH | -- | Postponed | L-XL | `../PerfGroth.md` |

### Where to start next session

Everything below is Open unless marked otherwise. Three items are at **InTest**
and share one exit condition: **none has been exercised from a clean checkout
on a second machine.** That is the single highest-value next step, because it
is also what would validate the cross-platform schema work.

| Next | Item | Why it is next |
|------|------|----------------|
| 1 | **B2** first non-macOS capture | Now recordable (A2/F1b landed). Would move A1, A2, F1 and C1 out of InTest together, since a clean-checkout Linux run exercises all four |
| 2 | **A3** microbenchmark baseline | Effort S, no decision needed, and worth more the longer GROTH stays postponed: a batching result needs a per-proof baseline taken beforehand |
| 3 | **D2** `Xc.reserve()` | One line, V1, and the most informative single measurement in the Equihash plan. The harness and paired method now exist (D4), so this is a ~30 min run. Steps: D2 below |
| 4 | **B1c/d** proof counters + `BenchSummary` | Product change, Zero400 review. B1a/b (parser side) are Finished |

**Do not start** GROTH (maintainer's decision) or F2 (needs repository
settings). Both are Postponed, not forgotten.

**Standing caveat:** every gate is local. `validate.sh` runs only when a person
runs it, so until F2 lands a contributor who skips it bypasses all of A1.

---

## Postponed

**GROTH** -- Sapling Groth16 batch verification. Everything about it,
including the librustzcash dependency it rests on, is `../PerfGroth.md`.

- Batch verification: awaiting a maintainer's choice
- **Precondition: close C1 documentation work, finish Tests, and cut an
  reference benchmark (5-10 trials preferred) before any algorithm experiment.** Rationale and
  the exception (fork-for-custody, which is packaging) in `../PerfGroth.md`
- **Attempt the Ycash/Pirate-level move directly (M).** Proven in action:
  each fork is upstream history plus ~3 project-specific commits (network
  prefixes, activation heights, encoding), both trees checked out at
  `ZK/ZKs/rustzcash/`. Not research -- a bounded change of known shape
- **Host downloadable artifacts under project control.** 741 MB of Zcash
  parameters from `download.z.cash`, the librustzcash tarball, and lab
  snapshots with no canonical source. Parameters are hash-verified so a mirror
  adds no trust; independent of the fork decision
- **Fork for custody (S, no consensus risk).** Take `06da3b9a` into
  `zerocurrencycoin/librustzcash` unchanged, on a node branch with `master` left
  mirroring upstream; acceptance test is a
  byte-identical `librustzcash.a`. Then move `librustzcash.h` into
  `src/rust/include/`. Recommendation, counter-arguments and what would change
  it: `../PerfGroth.md`
- **Dependency, and it constrains the above:** Zero pins librustzcash
  `06da3b9a` (2018-10-27), **6724 commits** behind, and the C FFI crate it
  pins **no longer exists upstream** -- moved into `zcash/zcash`. There is no
  newer version of what Zero consumes
between Option A and Option B; the options diverge at the FFI boundary, so
starting either wastes the other. Prototype frozen.

Everything: **`../PerfGroth.md`**. Nothing below depends on it.

### GROTH -- status review, 2026-09-09

**Remains postponed.** Reviewed, not reopened: the review is of whether the
description and its pending decisions are still accurate, and they are.

**Verified against the dependency, not the document:**

| Claim | Check |
|---|---|
| Pin is `06da3b9a` (2018-10-27) | **Confirmed** -- `depends/packages/librustzcash.mk:7`, and the commit dates 2018-10-27 |
| 6724 commits behind | **Confirmed exactly** -- `git rev-list --count 06da3b9a..HEAD` = 6724 against upstream HEAD 2026-09-03 |
| The C FFI crate no longer exists upstream | **Confirmed** -- `librustzcash/` now holds only a README: "This crate has been moved into https://github.com/zcash/zcash" |

So the load-bearing fact is intact: **there is no newer version of what Zero
consumes.** Option B is not "upgrade a dependency", it is "adopt a different
integration boundary", and that is the whole of the A-vs-B cost difference.

**The decision is genuinely blocked on a person, not on evidence.** Both
options are scoped, the math was proved on the pinned crates (Phases 0-1,
scratchpad only), and the branch point is the FFI boundary -- so starting
either wastes the other. That is a maintainer's call about risk appetite on
consensus-critical code, and no further lab work changes it.

**What is worth doing while postponed, in order:**

| # | Item | Why now |
|---|------|---------|
| 1 | **A3 microbenchmark baseline** | A batching result needs a per-proof baseline taken *beforehand*. Taken afterwards it is not a comparison. This is the only genuinely time-sensitive item on the whole board |
| 2 | **P1 proof-verification counters** | Groth16 verification is inside no timer at all, so a phase summary today omits 88-91% of post-Sapling cost while looking complete. Any before/after needs this first |
| 3 | **Fork for custody** (S, no consensus risk) | Take `06da3b9a` into a Zero-owned mirror unchanged; acceptance test is a byte-identical `librustzcash.a`. Independent of A-vs-B, and it stops the build depending on an upstream path that has already moved once |
| 4 | **Host the downloadable artifacts** | 741 MB of parameters from `download.z.cash` plus the librustzcash tarball. Parameters are hash-verified so a mirror adds no trust. Independent of everything else |

(3) and (4) are packaging, carry no consensus risk, and are the two things that
reduce exposure without pre-empting the decision. (1) and (2) are prerequisites
for measuring any outcome.

**Proposed resolution of the decision itself, with justification.** If forced
to recommend: **Option B (migrate to the upstream batcher) is the better
target, and Option A (hand-port onto pinned crates) is the better first step**
-- but only if the fork-for-custody work (3) lands first, because both options
then build on a boundary Zero controls. The reason B is the target is that it
is production-proven in zcashd and Zebra and also covers signature batching,
so the same migration buys two wins; the reason A is the first step is that
the Phase 0-1 math is already proved on the pinned crates and gives a
correctness oracle that B's output can be checked against. **This is a
recommendation for the maintainer to accept or reject, not a decision.**

**Documentation state:** `../PerfGroth.md` is 938 lines and 23 tables, over
the ten-per-file ceiling. It is the single largest findings document after
`Perf.md` and holds the whole subject correctly (0 FDCACHE mentions after
T5a). No content problem found; the table count is the open item.

---

## A -- do first

### A3. Record the microbenchmark baseline

`M-ZCB-SUITE` has no numeric archive. Runner exists
(`performance-measurements.sh`).

Time-sensitive in one direction: a batching result needs a per-proof baseline
taken beforehand, so this is worth more during the postponement than after.
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