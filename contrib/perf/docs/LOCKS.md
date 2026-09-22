# Locks: every finding, in one place

**This file is the single location for lock findings.** Measurements,
call-rate analysis, upstream precedent and disposition. Task state lives in
`TASKS.md` under the item ids named here; nothing about locks is recorded
anywhere else.

Tracking item: **P25** (this file's contents as a unit). Individual fixes keep
their own ids: P9, P12, P14, P15, P21.

## 1. What was measured

Instrumented `sync.cpp` under `DEBUG_LOCKORDER`, full tiny reindex
(187,418 blocks). `test-logs/lockattr-20260913/`, `test-logs/lockstats-20260912/`.

| Metric | Value |
|--------|------:|
| Recursive acquisitions | **2,901,309** (~15.5/block) |
| `LeaveCritical` underflows | **0** |
| `POTENTIAL DEADLOCK` detections | **0** |
| Distinct recursive sites | **9** |
| Cost of a recursive re-acquire | **4.55 ns** (not a syscall) |
| Total cost of all recursion | **0.013 s = 0.007% of wall** |

## 2. The nine sites

| Per block | Acquiring | Under | Same site? |
|----------:|-----------|-------|:----------:|
| **4.00** | `IsInitialBlockDownload` `:2249` | `:3906` / `:4791` | no |
| 2.00 | `FlushStateToDisk` `:3435` | itself | **YES** |
| 1.00 | `cs_nBlockSequenceId` `:4285` | itself | **YES** |
| 1.00 | `cs_LastBlockFile` `:4314` | itself | **YES** |
| 1.00 | `cs_LastBlockFile` `:4373` | itself | **YES** |
| 1.00 | `cs_main` `:3435` | `:3906` | no |
| 0.48 | `GetSpendHeight` `:2471` | `:3906` | no |

**Four sites re-lock at their own source line** with integer-exact per-block
counts -- the signature of defensive `LOCK` statements in functions already
called under the lock, not of a design needing recursion.

## 3. Call-rate decomposition

| Source | per block | share |
|--------|----------:|------:|
| **`IsInitialBlockDownload`** | **5.00** | **44%** |
| `FlushStateToDisk` self-recursion | 2.00 | 17% |
| `cs_LastBlockFile` self-recursion (x2) | 2.00 | 17% |
| `cs_nBlockSequenceId` self-recursion | 1.00 | 9% |
| `cs_main` `:3435` under `:3906` | 1.00 | 9% |
| `GetSpendHeight` | 0.48 | 4% |

## 4. Upstream precedent

| Commit | Date | Project | What |
|--------|------|---------|------|
| `83f1ec33ce` | 2017-07-24 | Bitcoin | stop holding `cs_LastBlockFile` across a callback |
| `0bd882b740` | 2021-08-28 | Bitcoin | **remove `RecursiveMutex cs_nBlockSequenceId`** -- "At this point, the cs_main lock is set, hence we can use a plain int" |
| `fade2a44f4` | 2022-01-02 | Bitcoin | `BlockManager` refactor; the `LOCK2` in `FlushStateToDisk` disappears |
| `14ec1016b` | 2019-12-27 | Zcash | **`LOCK(cs_main)` in `getspentinfo` and `getblockdeltas`** (v2.1.1) |

Neither Bitcoin fix was ported to Zcash; Zero inherits both from the 2013-2014
lineage. The Zcash fix **was** available and Zero lacked it -- now applied.

## 5. Disposition

| Item | State | Note |
|------|-------|------|
| **P12** `getspentinfo` missing `LOCK(cs_main)` | **Finished** | `rpc/misc.cpp:1110`, upstream verbatim |
| **P15** `getblockdeltas` missing `LOCK(cs_main)` | **Finished** | `rpc/blockchain.cpp:482`, same commit |
| **P21** `IsInitialBlockDownload` 4x/block | **Finished** | `fImporting \|\| fReindex` hoisted above the lock; removes 44% of recursion during reindex |
| **P14** defensive recursive `LOCK`s | **Postponed** | 0.007% of wall; upstream fixes are structural refactors. Reopens if `main.cpp` is restructured, or if an inversion traces here |
| **P9** `z_sendmany` note reservation | **Needs a decision** | Single async worker is what makes it safe; see `reporoot/OPEN_QUESTIONS.md` Q1 |

## 6. What is NOT a lock finding

Recorded here so it is not re-discovered as one:

- **`LOCK()` is not a system call.** 7.07 ns uncontended, **4.55 ns**
  recursive. Removing recursion buys correctness clarity, not speed.
- **`underflows = 0`** establishes a clean baseline. The original
  `pop_lock()` called `pop_back()` on a possibly-empty vector -- undefined
  behaviour in the diagnostic path, now counted and refused.
- **Zero lock-order inversions** across the whole Boost suite. The one
  `DEBUG_LOCKORDER` finding was an `AssertLockHeld` violation (P12), not an
  inversion.

## 7. How to reproduce

```bash
./configure --enable-debug && make          # DEBUG_LOCKORDER
LAB=/tmp/lab bash contrib/perf/tiny_baseline.sh
grep -A26 'LockStats: recursive' /tmp/lab/debug.log
```

`LogLockStats()` (`sync.cpp`) reports totals plus the top 25 recursive sites
by count, keyed `<mutex> <acquiring file:line> under <holding file:line>`.
**Leaving the configuration requires `make -C src clean`** -- `LOCK()` expands
in every locking TU, so a partial rebuild link-errors
(`BUILDCONFIG.md`).
