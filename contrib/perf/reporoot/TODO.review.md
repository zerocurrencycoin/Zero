# TODO.md -- review and proposed rewrite

**Draft for the Zero400 tree. Not applied.** Reviewed 2026-09-09 against
`src/` and `qa/` at `perf_b1b2` (`a2a691fb3`). Every state claim below was
checked in source; where it was not, that is said.

## 1. What is wrong with the current file

**It has three lists of the same items.** "Ordered next" (4 entries), "Active"
(12), and "Pending" (18) overlap: `WAL-GETALLDATA-W5` appears in Ordered next
and Active; `TST-01/03/05/09` appear in both; the four `TST-*` items then get
"Full descriptions" sections further down. An item's state has to be assembled
from three places, and they can disagree.

**"Active" does not mean active.** It holds items nobody is working on
(`Fuzz harness setup`, `macOS datadir`, `RPC coverage matrix`) beside items
under development. There is no way to tell which is which.

**Completed work is summarised, not removed.** The "Completed (summary)"
section plus the "Full descriptions" for finished items is roughly a third of
the file describing work that is done.

**Verified correct:** the technical claims spot-checked all hold --
`GetFoundersRewardAmount` (`src/main.cpp:2177`, used at `:4590`),
`IsGetAllDataTxTooOld` (tested at `src/test/rpc_zero_exclusive_tests.cpp:267`),
`rpc_zeronodestats` (`src/test/rpc_zeronode_tests.cpp:113`), the `txindex.py`
`int(... * COIN)` fix (`qa/rpc-tests/txindex.py:63,79`). The file is accurate;
it is the structure that costs time.

## 2. Proposed structure

One table, one row per item, one state each. Full descriptions stay only for
items whose *next action* is not obvious from one line.

| Column | Meaning |
|--------|---------|
| Id | `CON-` / `WAL-` / `OPS-` / `EXT-` / `TST-` |
| State | Active / Next / Pending / Postponed / Done-this-cycle |
| Next action | The concrete thing to do, or the gate that blocks it |

"Done" items move out of the file entirely at each release; the release notes
are their record.

## 3. WAL-GETALLDATA -- detail and proposed resolution

The family is one RPC (`getalldata`, `src/wallet/rpczerowallet.cpp`) and seven
open sub-items. What is already shipped: the S6 in-flight gate and time
coalesce (`cs_getalldata_gate`, `:44-69`, returning `RPC_DATA_CONTINUE` rather
than rewalking), `IsGetAllDataTxTooOld`, S4-S8 and W2, and const walks on the
read paths.

| Item | What it is | Proposed disposition |
|------|-----------|----------------------|
| **W5** tip poll split | Balances (datatype 1) on a timer; full History on user action or every Nth tick | **Do next.** It is the only one with a measured motivation -- the soft `-34` coalesce exists because the full walk is too expensive to run per tick. W5 removes the reason for the coalesce rather than mitigating it |
| **W6** in-process cache | Tip + dirty cache | **After W5.** A cache in front of a walk that W5 is about to make conditional would be tuned against the wrong access pattern |
| **W1** merge History key insert into balance walk | One walk instead of two | **Fold into W5.** Same code path, same review; splitting them means walking the wallet twice in review as well as at runtime |
| **W4** IVK decrypt review | Is the decrypt hot? | **Measure before deciding.** This is a perf question with no measurement: it belongs as an `M-*` row, not a TODO item. Propose moving it to ZeroPerf as a measure task |
| **ARG2-DEFAULT** | Omitted arg2 gives a ~30-year window; proposed default 2 (7 days) | **Postpone to a release boundary.** It is a silent behaviour change for any script that omitted arg2, so it needs a release note and a major/minor bump, not a quiet fix |
| **HELPERS** | One parse/filter path for day window, `nCount`, watchonly, datatype gates | **Do with W5.** W5 touches the same parse path; doing them separately means editing it twice |
| **LEGACY-SCOPE** | Which 2018-2020 surface can shrink | **Keep as a standing constraint, not a task.** It says "do not grow the kitchen sink without datatype gates" and "do not undo S4-S8/W2 without replacement". That is a review rule. Move it to the file's header as a policy line and close the item |

**Justification for the ordering:** W5 is the only member with an established
cost motivation; W1 and HELPERS share its code path and are cheaper done
together than sequentially; W6 depends on W5's outcome; W4 is unmeasured and
should not be scheduled as engineering work before it is a measurement; ARG2 is
gated by release process, not by code; LEGACY-SCOPE is not a task at all.

## 4. TST-01 / 03 / 05 / 09 -- detail and proposed resolution

All four are **test-coverage** items. In each case the node feature exists and
the gap is the harness, which is why they have sat: they are not blocked, they
are unowned.

| Item | Node side | Test gap | Proposed resolution |
|------|-----------|----------|---------------------|
| **TST-01** `getalldata` | Shipped | Exclusive Boost covers empty-wallet gates; Ext `getalldata_scenario` covers a populated wallet. Open: `getsupply`, `zs_*`, sapling depth | **Split.** The `getalldata` half is done; carry the remainder as `TST-01b getsupply/zs_*` so a finished item stops reading as open |
| **TST-03** zeronode | Shipped; `rpc_zeronodestats` exists (`src/test/rpc_zeronode_tests.cpp:113`) | Arg validation only, and it is already asserted (`:115` checks the throw) | **Close it.** Re-run the suite; if green, this is Done and the line should go |
| **TST-05** mining | (48,5) `CreateNewBlock` live in `miner_tests`; genesis (192,7) KATs in `equihash_tests` | Marked green in ZeroPerf (`TASKS.md`); further KAT adaptation was **postponed (G9)** | **Close the TST-05 line and keep G9 in ZeroPerf.** Two trees tracking one postponement is the double-record problem |
| **TST-09** notify | All three hooks exist: `-alertnotify` (`src/init.cpp:358`), `-blocknotify` (`:359`, wired `:595`, `:2111`), `-walletnotify` (`:464`, wired `src/wallet/wallet.cpp:2274`) | `alertnotify` tested; `blocknotify` / `walletnotify` untested | **Do it -- this is the cheapest real gap.** Both are shell-command hooks with an observable side effect: point them at a script that touches a file, generate a block / send a wallet tx in regtest, assert the file exists. One `qa/rpc-tests` script covers both |

**Justification:** TST-03 and TST-05 appear open but are not -- closing them
removes two of the four without any work, which is worth more than it sounds
because a list where half the entries are stale trains people to skip it (the
same finding as the Bfail sweep, where 41% of a known-broken list passed).
TST-09 is the only one with genuine missing coverage, and it is small and
mechanical. TST-01's open half is real but larger, and should not be filed
under the same id as the part that is finished.

**Dependency:** `OPS-ALERT-STRIP` ("gut P2P `alert.cpp` after TST-09 slim") is
blocked on TST-09 and should say so in one line rather than being discovered
by reading both.

## 5. Linux and Windows -- group and postpone

Scattered across "Ordered next" item 3 and Pending. Proposed: one block,
postponed together, with a stated reason.

| Item | Why postponed |
|------|---------------|
| Linux `--strict` + `--suite` release track | Needs a retest on the current tree; the last run predates the branch's build and test changes |
| Windows MXE build | **Never executed in this program.** Not a regression -- it has no baseline at all |
| Windows hardening; native ETW profiling | Blocked on the MXE build above, and on symbol format |
| Params archival, branch-id CI, OpenSSL 3, Debian packaging | Release-engineering, same retest gate |

**Justification for postponing as a group rather than individually:** every one
of them needs the same prerequisite -- a validated build on that platform at
the current version. Scheduling any single item first still pays that cost, so
they are one unit of work. Recording them separately as "open" overstates how
much is ready to start. This is WIP pending a remeasure, not a backlog.

This also matches ZeroPerf **B2** (first non-macOS measurement), which is the
same prerequisite from the lab side. B2 landing is what unblocks this group.

## 6. Items that should move out of TODO.md

| Item | Where it belongs | Why |
|------|------------------|-----|
| `WAL-GETALLDATA-W4` IVK decrypt review | ZeroPerf, as a measure task | It asks "is this hot", which is a measurement, not a change |
| `OPS-CACHE-METRICS` tunable cache metrics | ZeroPerf | Same -- it is instrumentation to answer a perf question |
| `OPS-DEBUGLOG-TIMING` | ZeroPerf | `extract_measures.py` and `stall_check.py` already do this; the item is stale |
| `TST-SAPLING-ROOT`, `TST-WITNESS-REINDEX` | Keep, but cross-reference ZeroPerf P2/P4 | The evidence is in the perf tree; the fix is node code |
| `OPS-I2P` | Delete the item, keep one line under a "watching" heading | "Track ecosystem only, no implementation scheduled" is not a task |

## 7. Summary of the proposed edit

- Three overlapping lists -> one table.
- Close **TST-03**, **TST-05** (stale-open).
- Split **TST-01** into the finished half and `TST-01b`.
- Schedule **TST-09** (smallest real gap; unblocks `OPS-ALERT-STRIP`).
- Order the `WAL-GETALLDATA` family: W5+W1+HELPERS together, then W6; ARG2 to a
  release boundary; W4 out to ZeroPerf; LEGACY-SCOPE becomes a header rule.
- Group Linux/Windows as one postponed block pending a current-version build.
- Move four measurement-shaped items to ZeroPerf.
- Delete the "Completed (summary)" section at the next release.

Estimated result: 125 lines -> about 70, with no item losing information.
