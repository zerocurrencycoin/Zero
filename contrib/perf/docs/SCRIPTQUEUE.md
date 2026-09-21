# The script-check pool: a worked example of measuring the wrong thing

Two measurements of the same pool, days apart, gave opposite answers. Both
instruments were working correctly.

## Measurement 1: `max_concurrent` = 14

`CCheckQueue` instrumented to track `nTotal - nIdle`, high-water mark over the
run. Over a tiny reindex it reached **14 within the first 32k blocks and stayed
there**, with 201,657 batches taken.

**Conclusion drawn:** "the pool is not dormant during reindex; every worker
engages."

## Measurement 2: stack sampling

`sample <pid> 10` during a post-Sapling import. All **13 `zcash-scriptch`
threads were blocked in `__psynch_cvwait` for the entire sample** -- 105,261
samples, zero of them in a check.

**Conclusion:** the pool is idle.

## Both are right; one answers the question

`max_concurrent` is a **high-water mark**. It records that fourteen
participants were once simultaneously non-idle -- plausibly for microseconds
during a single batch -- and is monotonic: once set, it never falls. It cannot
distinguish "saturated throughout" from "briefly touched once".

Stack sampling measures **occupancy**: at N moments, how many threads were
running? That is the question "are these threads useful" actually asks.

## The rule

**A maximum is not a utilisation.** Neither is a count of work items, nor a
wakeup tally -- 201,657 batches over 187,418 blocks sounds substantial and is
consistent with each worker taking a sliver and immediately re-parking.

To claim a pool is used, measure **occupancy over time**: sampled stacks, or a
duty-cycle counter (time-in-check / wall time per worker). To claim it is
*needed*, remove it and measure the difference.

This is the same failure as reporting `ps`'s decaying average as an
instantaneous rate (`CPU_MEASUREMENT.md`): an instrument answering a
neighbouring question, reported as though it answered this one.

## What this means for `-par`

The P20 proposal -- cap `MAX_SCRIPTCHECK_THREADS` at 4 -- was weakened by
measurement 1 and is **restored by measurement 2**. On this workload the
13 workers do nothing. The A/B in `CONCURRENCY.md` S5.1 remains the deciding
test, but the prior now favours the cap.

**Caveat, unchanged:** these blocks are below the last checkpoint, so
`fExpensiveChecks` is false and `ConnectBlock` passes `NULL` instead of the
queue (`main.cpp:3110`). A post-checkpoint workload is where script checks
would actually run, and that measurement has not been taken.
