# Locks

Everything known about locking in this node: what the instrument measures,
what it found, how to reproduce it, and what remains open. Work items are
`PLAN.md` group B.

## The instrument, and a defect it had

`DEBUG_LOCKORDER` builds compile `push_lock` and `pop_lock` in `sync.cpp`.
These maintain a per-thread stack of held locks and report, at shutdown:
recursive acquisitions, `LeaveCritical` underflows, per-site attribution, and
lock-order inversions.

**The recursion counter was wrong until 2026-09-22 and its published figures
should not be cited.** `push_lock` pushed the new entry onto the stack and
then scanned the stack *including that entry*, so the first comparison matched
the lock against itself. Consequences, reproduced in a standalone harness of
the same loop:

| Event | Counter said | Truth |
|-------|-------------|-------|
| Plain lock of A on an empty stack | recursive | not recursive |
| Lock B while holding A | recursive, site "B under A" | not recursive |
| Re-lock A while holding A | recursive | recursive |

So the counter incremented on **every non-try acquisition**, and attribution
recorded a nested lock of a *different* mutex as a recursion of that mutex.
Any figure derived from it before the fix is an acquisition count.

The fix scans strictly below the pushed entry. The test that it is right is
arithmetic: the per-site rows now sum to the reported total exactly, where
before they left a large unexplained remainder.

## What recursion actually exists

Full tiny reindex, 187,418 blocks, corrected instrument.
`test-logs/lockattr-corrected-20260922/`.

**Six sites, 1,109,483 acquisitions, 5.92 per block, sum reconciled.**

| Per block | Count | Mutex | Acquiring | Under |
|----------:|------:|-------|-----------|-------|
| 1.48 | 277,354 | `cs` | `txmempool.cpp:713` | `txmempool.cpp:434` |
| 1.48 | 277,354 | `cs` | `txmempool.cpp:375` | `txmempool.cpp:434` |
| 1.48 | 277,354 | `cs` | `txmempool.cpp:241` | `txmempool.cpp:434` |
| 1.00 | 187,418 | `cs_main` | `main.cpp:3495` | `main.cpp:3966` |
| 0.48 | 89,936 | `cs_main` | `main.cpp:2499` | `main.cpp:3966` |
| 0.00 | 67 | `cs_LastBlockFile` | `main.cpp:2942` | `main.cpp:4374` |

Every one is a caller holding a lock that a callee takes again:

- `CTxMemPool::removeForBlock` holds `cs`, then calls `remove`,
  `removeConflicts` and `ClearPrioritisation`, each of which takes `cs`. Once
  per transaction removed, which is why the rate is fractional per block.
- `ConnectTip` holds `cs_main`; `FlushStateToDisk` and `GetSpendHeight` take
  it again.
- `FindBlockPos` holds `cs_LastBlockFile` and calls `FlushBlockFile`, which
  takes it again.

This is lock-per-function composition -- each function acquires what it needs
without assuming its caller did -- which is the reason these mutexes are
recursive. It is not defensive duplication, and it is not one function
locking itself: the acquiring and holding sites are always different
functions.

**Inherited, not local.** Zcash, Pirate, Ycash and Hush3 carry the same three
`LOCK(cs_LastBlockFile)` sites and the same `removeForBlock` structure.

## Nested locks of different mutexes are the deadlock question

Recursion -- one thread re-taking a lock it holds -- cannot deadlock against
itself. **Ordered nesting of different mutexes can**, if two threads take the
same pair in opposite orders.

That is what `lockorders` exists for. Every (held, acquiring) pair is recorded
with the stack that produced it; if the reverse pair is ever seen,
`potential_deadlock_detected` prints both stacks and asserts. It is a global
map, so a pair established by one thread is checked against every other.

**Measured: zero `POTENTIAL DEADLOCK` detections and zero underflows** across
every instrumented reindex run to date.

Two limits worth stating:

- **Single-threaded coverage.** A reindex exercises one dominant worker, so
  pairs only that path establishes are the only ones checked. An inversion
  reachable only under concurrent RPC and validation would not appear. This
  is the gap the worker experiments (`PLAN.md` group B) are meant to close.
- **`TRY_LOCK` is excluded.** `push_lock` skips the whole scan when `fTry` is
  set, because a try-lock that fails bails rather than blocks. Genuine
  inversions involving a try-lock are therefore not detected, only the
  non-try ones.

## Cost

An earlier measurement put a recursive re-acquire at 4.55 ns -- an uncontended
recursive mutex increments a count, it does not enter the kernel -- and all
recursion at roughly 0.007% of wall. **That figure predates the counter fix**
and was computed against an inflated count, so the true total is lower still.
Either way the conclusion holds: recursion is not a throughput problem, and no
change here is justified on performance grounds.

## Reproducing

```
./configure --enable-debug --with-gui=no CONFIG_SITE=<depends>/share/config.site
make clean && make -j4
```

`--enable-debug` sets `-DDEBUG_LOCKORDER`. **Rebuild from clean**: configure
regenerates makefiles without invalidating objects, so an incremental build
produces a binary where only recompiled translation units carry the
instrumentation. Check with `nm src/zerod | grep LogLockStats` and compare the
binary timestamp.

Then a full tiny reindex, stopped cleanly so `LogLockStats()` runs at
shutdown:

```
tar -xzf chainblocks-tiny.tgz -C $LAB
./src/zerod -datadir=$LAB -reindex -disablewallet -daemon
# wait for height 187417
./src/zero-cli -datadir=$LAB stop
grep LockStats $LAB/debug.log
```

`validate.sh` will fail `buildconfig` while a debug binary is in the tree.
That is the guard working; rebuild release afterwards.

**Do not compare timings between debug and release runs.** `--enable-debug`
builds at `-O0`; the same reindex took 131 s release and 363 s debug.
Acquisition counts are deterministic per block and do compare.

## Open

- Concurrency coverage: every result here comes from a single-worker reindex.
- `TRY_LOCK` paths are uninstrumented.
- Shielded note selection does not lock the notes it selects
  (`PLAN.md` B4); the single async RPC worker is what currently prevents the
  race, which makes it a standing constraint rather than a settled design.
