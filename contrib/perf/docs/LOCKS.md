# Locks

Everything known about locking in this node: what the instrument measures,
what it found, how to reproduce it, and what remains open.

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

Full tiny reindex, corrected instrument: M-LOCK-ATTR.

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

**Upstream removed the block-file patterns; Zcash did not port the removals.**

| Bitcoin commit | Change |
|----------------|--------|
| `83f1ec33ce` | Stops holding `cs_LastBlockFile` across the `setBestChain` callback |
| `0bd882b740` | Removes `RecursiveMutex cs_nBlockSequenceId`; the counter becomes `int32_t ... GUARDED_BY(::cs_main)`, since `cs_main` is already held at its one use |
| `fade2a44f4` | Moves `cs_LastBlockFile` into `BlockManager`; the `LOCK2(cs_main, cs_LastBlockFile)` in `FlushStateToDisk` goes |

Zcash still has `LOCK2(cs_main, cs_LastBlockFile)` and
`LOCK(cs_nBlockSequenceId)`; Zero inherits both. Porting is a structural
refactor of block storage, justified by correctness or a restructuring of
`main.cpp`, not by the cost below.

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
  is the gap the worker experiments (`PLAN.md` B6) are meant to close.
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

## Contention

`DEBUG_LOCKCONTENTION` builds log `LOCKCONTENTION: <name>` each time a lock is
found held and the caller waits. That gives how often, by lock name only: no
site, no wait time, and one log line per event, so it is usable for short
runs and unusable on a live node. What would answer "how often and how long,
where" is a per-site counter beside the attribution map the order instrument
already keeps: contended acquisitions and total and maximum wait in
microseconds per (lock, file, line), dumped at shutdown and by an RPC, in
perf builds only (`PLAN.md` B8). No contention figure exists yet.

## Long holds and hang risks

Review of the source, not measured unless an `M-*` id is given. Every `LOCK2`
in node code takes `cs_main` before `cs_wallet`.

| Finding | Mechanism | Detection | Reporting today | Mitigation |
|---------|-----------|-----------|-----------------|------------|
| Rescan blocks the node | `ScanForWalletTransactions` holds `cs_main` and `cs_wallet` for the whole scan, with no shutdown check in its loop; a fat-wallet genesis rescan ran ~11.9 h (M-WAL-RESCAN-FAT). Reached at startup by `-rescan` and on a live node by `z_importkey`, `z_importviewingkey`, `importwallet` | RPC calls time out (`zero-cli` default 900 s) | none beyond the GUI progress hook | shutdown check every N blocks with the locator left at the last scanned block; release `cs_main` periodically |
| Witness height walk | `BuildWitnessCache(pindex, false)` under both locks; 7.7 s on a fat tip rebuild without NOTEIDX (M-WAL-WITNESS-TIP-AB) | `getblockcount` stalls for the walk | `-33` to wallet RPCs only | `PLAN.md` A6 |
| Per-block witness Verify | `VerifyAndSetInitialWitness` under both locks every block in IBD and reindex; 72-99% of CPU with a fat wallet (M-CPU-WAL-FAT) | slow sync, RPC latency | none | `-walletwitness=ibd-defer` (`WITNESS.md`) |
| `getwalletinfo` behind a witness build | waits on `cs_wallet` for minutes | monitoring clients time out | none | the harness bounds its calls (`ZERO_PERF_CLI_TIMEOUT_S`) |
| `CDB::Rewrite` spin | waits in `while (true)` for the file's use count to reach 0; a held handle spins forever. The source carries a commented-out trace for this | none | none | log the use count every N seconds; a bounded wait with an error (`PLAN.md` A13) |
| Zeronode try-locks on `cs_main` | 8 `TRY_LOCK(cs_main)` sites in zeronode code avoid an inversion with zeronode locks; the order instrument does not check try-locks | none | none | keep them try-locks; record them as non-blocking order edges in a lock-debug run (`PLAN.md` B1) |
| HTTP work queue full | requests behind `cs_main` fill `-rpcworkqueue`; the next get HTTP 503 with no reason | client sees 503 | one server log line per episode | `PLAN.md` C6 |

None of these is a deadlock: each ends when the holder finishes. The
practical failure is a supervisor or front-end that reads a long hold as a
hung node and kills it mid-rescan.

## Designs for the open work

In the order they pay off. Each states its acceptance check.

**1. Contention counters (B8).** In `CMutexLock::Enter`, the
`DEBUG_LOCKCONTENTION` path already tries the lock first and logs when it
fails. Under `ZERO_PERF` instead: on a failed try, time the blocking
`lock()` with `GetTimeMicros()` and add (count, total, max) to a fixed-size
table keyed by (lock name, file, line), protected by its own uninstrumented
mutex or accumulated per thread and merged at shutdown. Report the table
sorted by total wait to `debug.log` at shutdown and through a perf-build
RPC, with a reset. Uncontended acquisitions pay one extra try-lock, in perf
builds only. Check: a unit test holds a mutex in one thread for a known
time while another waits, and the site shows one event with wait >= that
time.

**2. Interruptible rescan (A14b; reporting first in A14a).** `ScanForWalletTransactions` returns a
count; its callers (`init.cpp` startup rescan, `z_importkey`,
`z_importviewingkey`, `importwallet`) then treat the chain as scanned, and
the final `BuildWitnessCache(tip, false)` runs only at the end. So an early
return alone would mark unscanned blocks as scanned. Steps: (1) the scan
returns an interrupted state with the last fully scanned block; (2) callers
write that block's locator, not the tip's, and skip the final witness build,
leaving witnesses unbuilt (`-31`); (3) a restart resumes from the wallet's
locator through the existing startup path; (4) later, release both locks
between batches.

Corner cases, each a test:

| Case | Risk | Rule |
|------|------|------|
| `rescan=1` in `zero.conf` | every start rescans from genesis; a supervisor that kills slow starts never lets it finish (confirmed on regtest: each start logged a rescan) | `-rescan` belongs on the command line once; the harness refuses `rescan=` (`lab_conf`); a persisted "rescan from height H" wallet record would let `-rescan` resume instead of restart |
| `stop` or SIGTERM mid-scan | today ignored until the scan ends; the supervisor's kill timeout then SIGKILLs | check `ShutdownRequested()` every N blocks or T seconds, whichever comes first; T well below common supervisor timeouts (90 s for systemd) |
| SIGKILL mid-scan | progress since the last locator write is lost, never corrupt: the wallet database commits atomically | write the locator every batch, so a kill loses at most one batch |
| Two rescans at once (two imports, or an import during a startup rescan) | with locks released between batches, two scans interleave and race on the locator | one rescan at a time: a second request fails with "rescan in progress" instead of queueing |
| Reorg while locks are released | `chainActive.Next(pindex)` returns null for a disconnected block and the scan ends early, reporting success | on re-acquiring, if `chainActive.Contains(pindex)` is false, resume from the fork point |
| New blocks connected during the scan | the same transactions arrive by the scan and by `SyncTransaction` | `AddToWallet` is idempotent; no rule needed beyond a test |
| Interrupted import RPC | the client gets an error, the key is already stored, the scan resumes at next start | the error text says the scan resumes on restart |

Check: regtest, a rescan long enough to interrupt; `stop` returns within T;
the restart resumes; the wallet equals one from an uninterrupted rescan; a
second import during the scan is refused; a reorg during the scan is
followed.

**3. Height walk (A6).** Same batch pattern for `BuildWitnessCache(pindex,
false)`: release both locks every N blocks, abort and restart the walk if
the tip changed. Check: R5c, a tip change during the walk, completes with
correct witnesses; `getblockcount` answers during the walk.

**4. Try-lock edges in the order map (B1).** Record (held, try-acquired)
pairs from `TRY_LOCK` as non-blocking edges in a second map; at shutdown,
report any blocking edge whose reverse exists only as a try-lock edge. Such a
pair cannot deadlock today and becomes a deadlock the moment the try-lock is
made blocking. Check: the 8 zeronode `TRY_LOCK(cs_main)` sites appear in the
report with their partner locks.

**5. Concurrent coverage run (B1, B6).** A `DEBUG_LOCKORDER` build on
regtest, blocks generated continuously while a driver issues
`getblockcount`, `getwalletinfo`, `z_sendmany` and `z_mergetoaddress` in
parallel. Check: zero `POTENTIAL DEADLOCK` reports, and the order map holds
pairs a single-worker reindex never produces.

**6. `CDB::Rewrite` wait (A13).** Log the file's use count every 10 s while
waiting; after a configurable timeout return false so `backupwallet` and
`encryptwallet` fail with an error instead of hanging. Check: a test holds a
`CDB` handle and the rewrite fails after the timeout with a log line.

**7. Work-queue rejection (C6).** Put the reason in the HTTP 503 body.
Check: `zero-cli` prints "Work queue depth exceeded" at depth 1 under load.

## Open

- Concurrency coverage: every result here comes from a single-worker reindex.
- `TRY_LOCK` paths are uninstrumented.
- No contention counts or wait times per site (`PLAN.md` B8).
- Shielded note selection does not lock the notes it selects; see below.

## Shielded note selection and the single async worker

Zero has shielded-note locking -- `setLockedSaplingNotes` (`wallet.h:1110`),
`IsLockedNote` for `JSOutPoint` and `SaplingOutPoint` (`:1135`, `:1146`) --
and `GetFilteredNotes` skips locked notes by default (`ignoreLocked=true`).
Where each spender selects its inputs, and whether it locks them:

| Operation | Inputs | Selected on | Locks them |
|-----------|--------|-------------|------------|
| `z_sendmany` | notes, UTXOs | async worker, at execution (`find_unspent_notes`) | No |
| `z_mergetoaddress` | notes, UTXOs | HTTP thread, in the RPC handler | Yes, in the operation constructor (`lock_notes()`, `lock_utxos()`) |
| `z_shieldcoinbase` | coinbase UTXOs only | HTTP thread | Yes (`lock_utxos()`) |
| Sapling migration, consolidation | notes | async worker | No |

All async operations run on one worker (`rpc/server.cpp:311`), so
`z_sendmany`, migration and consolidation cannot select concurrently with
each other. The single worker does **not** serialise `z_mergetoaddress`: its
selection runs on an HTTP thread and can overlap a `z_sendmany` executing on
the worker. `z_sendmany` skips notes `z_mergetoaddress` has already locked,
but `z_mergetoaddress` can pick a note `z_sendmany` has selected and not yet
spent. The consequence is a double spend of one note; the node and mempool
reject the second transaction, so one operation fails. Funds are not at risk.

**Upstream history.** Zcash added `-rpcasyncthreads` in `8d08172d0` and
disabled it thirteen days later in `008fccfa4` ("Disabled until we can lock
notes and also tune performance of libsnark"). Note locking then landed in
three steps: `z_mergetoaddress` (`4e6400bc0`, PR #3106), Sapling note locking
in `CWallet` (`0e0f5e4ea`, PR #3496; Zero's `b6b2b5d26`), and the send path
(`06553d139`, PR #6408, fixing #2621 and #5654) inside `wallet_tx_builder`, a
restructure Zero does not have. Zero carries the first two. libsnark is not
built in Zero.

**Options** (`PLAN.md` B4, decision 2):

1. Record the constraint here and leave code unchanged. Enabling more than one
   async worker, or adding a selector outside the worker, must add note locking
   to `z_sendmany` first.
2. Add `lock_notes()` / `unlock_notes()` to `z_sendmany`, mirroring
   `z_mergetoaddress`. About 20 lines against an in-tree pattern; closes the
   `z_mergetoaddress` overlap above and removes the dependency on worker count,
   but diverges on wallet spend selection from a base upstream has since
   restructured.

Recommendation: (1) now; (2) if the overlap failure is seen in practice or
multiple workers are reconsidered. Before (2), instrument the corner cases and
add a deadlock timeout.
