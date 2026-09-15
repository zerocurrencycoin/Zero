# Concurrency and thread sizing: what is in place now

Inventory taken 2026-09-11 against `src/` at `a2a691fb3` + working changes.
Locations and logic only; performance findings belong to `../Perf.md`.

## 1. Thread pools and their sizing

| Pool | Knob | Default | Sized where | Cap |
|------|------|---------|-------------|-----|
| Script verification | `-par` | `DEFAULT_SCRIPTCHECK_THREADS` | `init.cpp:1125-1129`; `0` = auto, negative = leave N cores free, resolved via `GetNumCores()` | `MAX_SCRIPTCHECK_THREADS = 16` (`main.h:91`) |
| HTTP/RPC service | `-rpcthreads` | **4** (`httpserver.h:14`) | `httpserver.cpp` | -- |
| HTTP work queue depth | `-rpcworkqueue` | **16** (`httpserver.h:15`) | `httpserver.cpp:443`, floored at 1 | -- |
| Async RPC (`z_*` operations) | `-rpcasyncthreads` | **1, and the option is disabled** | `rpc/server.cpp:311`; the multi-worker loop is commented out | effectively 1 |
| Mining | `-genproclimit` | `-1` = all cores | `init.cpp` | -- |
| Equihash tromp solver | constructor arg | `equi eq(1)` in `miner.cpp` | -- | `EQUIHASH_TROMP_THREADED` off |

**Two of these are pinned at one for stated reasons**, and they are the
interesting ones:

- **Async RPC.** Disabled in Zcash `008fccfa4` (2016-09-01) with the reason in
  the commit: *"Disabled until we can lock notes and also tune performance of
  libsnark which by default uses multiple threads."* Upstream met the
  note-locking half in `06553d139` (2022-10-24) and re-enabled its loop; Zero
  is before that fix. **This is what makes unreserved `z_sendmany` note
  selection safe today** -- see `TASKS.md` P9.
- **tromp solver.** `equi eq(1)` is single-threaded, so the barrier, the worker
  pool and the atomic counters are all compiled out.

## 2. What is deliberately NOT parallelised

| Path | Why |
|------|-----|
| Groth16 / JoinSplit proof verification | Runs on the import thread; `scriptcheck` workers never see it. This is why post-Sapling sync is single-core bound (`../Perf.md` S2) |
| Block connection / state write | Serial by design |
| Wallet note selection | No reservation mechanism on the `sendmany` path; safety currently comes from the single async worker (P9) |

For comparison, Zebra parallelises **stateless verification** (signatures,
proofs) through a rayon pool sized by `parallel_cpu_threads`, defaulting to the
logical core count, while keeping state writes serial. Zero's equivalent split
does not exist: verification is not on a pool at all.

## 3. Synchronisation primitives in the solver

`src/pow/tromp/equi_miner.h` states the rule at the typedef (`:30-44`): threads,
atomics and the barrier "are one feature and must move together -- threads
without atomics hand two workers the same slot; atomics without threads pay for
a capability nothing uses."

| State | Type | Concurrent access |
|-------|------|-------------------|
| Slot counters `nslots` | `au32` | `atomic_fetch_add_explicit`, relaxed (`:335`) |
| Solution counter `nsols` | `au32` | `atomic_fetch_add_explicit`, relaxed (`:383`) |
| `xfull` / `hfull` / `bfull` | `au32` **since 2026-09-11** | Incremented inside `digit0`/`digitodd`/`digiteven` by every worker; **reset** only by thread 0 between barriers (`:758`, `:770`) |
| Heap `heap0`/`heap1` | raw, per-instance | `calloc` in `htalloc::alloc`, freed by `~equi()`. Two `equi` objects share nothing |

**The `?full` counters were the gap**: increments race, resets do not. Fixed and
timed -- no measurable cost, since the production build is single-threaded and
`au32` is then a plain `u32` (`test-logs/atomics-timing-20260911/FINDINGS.md`).

**Memory is the real constraint on independent parallel solves**, not locking:
~3.3 GB per tromp instance (M-EQ-PEAK-TROMP), ~7.15 GB per reference instance
(M-EQ-PEAK-DEFAULT).

## 4. Validating locking across the codebase

Zero already carries the upstream lock-order machinery; it is **off by default**
in this build.

| Tool | What it gives | How to enable |
|------|---------------|---------------|
| `DEBUG_LOCKORDER` | Records lock order at every `LOCK()`, aborts on inversion | `./configure --enable-debug`, or `-DDEBUG_LOCKORDER` |
| `AssertLockHeld()` | Declares a required lock at a function boundary | Already used; add at newly-annotated functions |
| ThreadSanitizer | Detects data races the lock order cannot see (plain-`u32` races like `?full` was) | `-fsanitize=thread`; incompatible with ASan, needs its own build |
| `-par=N` sweep | Exercises the script-check pool at several widths | Runtime only |

**Recommended validation sequence**, cheapest first:

1. **Build once with `DEBUG_LOCKORDER` and run the existing `qa` suite.** No
   new tests needed; it either finds an inversion or it does not. This is the
   single highest-value check and it has, as far as this tree records, never
   been run here.
2. **ThreadSanitizer over `qa/rpc-tests`**, same reasoning. TSan is what would
   have caught the `?full` race automatically rather than by reading.
3. **Only then** consider enabling `EQUIHASH_TROMP_THREADED` or
   `-rpcasyncthreads > 1`, each behind its own measurement, and never both at
   once.

**Do not** enable a threading feature and add a test for it in the same change:
the test then only proves the feature does not crash, not that it was needed.

## 4a. Recursive locking and unbalanced unlock: risk and severity

The two counters added to `sync.cpp` measure different things with **very
different severity**, and conflating them would be a mistake.

### Recursive acquisition -- legal, diagnostic only

A thread taking a lock it already holds. `CCriticalSection` wraps
`boost::recursive_mutex`, so this is **defined, supported behaviour**: the
owner's count increments and the lock is released when the count returns to
zero. Measured **5,567,609 times (~29.7/block)** on a tiny reindex, with zero
ill effects.

| Risk | Severity | Why |
|------|---------:|-----|
| Deadlock from re-entry | **None** | Recursive mutexes exist precisely to allow it |
| Hidden lock contract | **Low, real** | A callee asserting a lock may be relying on *some* caller up the stack having taken it. That is P12 exactly: `GetSpentIndex` asserts `cs_main`, four callers do not take it, and it works only because something above them usually does |
| Held longer than intended | **Low** | Re-entry extends the critical section by the callee's duration. With `cs_main` around block connection this is already long |

**Why count it at all:** the absolute value is uninteresting; a **change** is
not. A rise means a path began acquiring at a new depth, which is where a
contract like P12's gets broken silently.

### Unbalanced unlock -- always a defect

`LeaveCritical()` with an empty lock stack. Measured **0** over 5.5M
acquisitions.

| Risk | Severity | Why |
|------|---------:|-----|
| Undefined behaviour in the checker | **High**, and it was live | The original `pop_lock()` called `pop_back()` on a possibly-empty `std::vector`. That is UB -- not "returns nothing", but unspecified memory behaviour in the *diagnostic* path |
| Lock released while still needed | **Critical**, if it reaches the mutex | Another thread enters a critical section the first still believes it holds |
| Corrupted lock-order data | **High** | The recorded stack no longer matches reality, so every later inversion verdict is untrustworthy |

**Note the asymmetry**: the *counter* only tracks the shadow stack in
`DEBUG_LOCKORDER` builds -- an underflow there means the instrumentation's
model is wrong, which usually means a real `LOCK`/unlock imbalance, but the
release build's actual mutex operations are `boost`'s and are separately
correct. So an underflow is a **strong signal of a defect**, not proof of a
live one.

**What was fixed:** `pop_lock()` now checks, counts, logs `LOCK UNDERFLOW`,
and **refuses the pop** rather than invoking UB. Zero occurrences establishes
the baseline; the value is that a future change which introduces one will be
visible instead of silently corrupting the stack.

## 5. Experiment plan: validating a concurrency change

Written 2026-09-12. **Nothing here has been run** except where marked.

### 5.1 `-par` sizing: is the default right?

**Proposal on the table: `cores/2`, capped at 4**, rather than today's
all-cores-up-to-16.

**The argument for it**, on the evidence this tree has: post-Sapling sync is
Groth16-bound on `ThreadImport` (`../Perf.md` S2), and script checking is not
the bottleneck. Threads that cannot help still contend for memory bandwidth
and, on this host, for 4 efficiency cores that are slower than the 10
performance cores -- a pool sized to 14 schedules work onto cores that finish
late and hold the round.

**The argument against changing it blind:** no measurement here has varied
`-par`. The default is upstream's and applies to every Bitcoin-family node;
diverging needs evidence, not reasoning.

**Experiment (cheap, ~2 h, no code change):**

| Arm | `-par` | Rationale |
|-----|-------:|-----------|
| A | 0 (auto = 14) | today's default on this host |
| B | 7 | cores/2 |
| C | 4 | the proposed cap |
| D | 1 | serial, the floor |

Fixed tiny reindex, n=4 per arm, paired by snapshot. Report `blocks_per_sec`
with n and dispersion as a fraction, plus `phys_mb` peak. **Pre-registered
prediction: no difference outside noise**, because the work is not script-bound
at these heights. If that holds, the finding is "the knob does not matter for
sync", which argues for the lower default on memory grounds alone and is worth
recording either way.

**Then repeat post-Sapling**, where the mix changes. A `-par` result from
pre-Sapling heights does not transfer.

### 5.2 Read-only RPC under concurrency

The P9/P12 questions are both "what happens when two readers overlap", and
nothing here has tested it.

| Step | What | Why |
|------|------|-----|
| 1 | `getblock` / `getrawtransaction` / `getspentinfo` driven from N clients against a synced node, N in {1, 2, 8} | These are the paths P12 found unlocked. Latency percentiles, not throughput |
| 2 | Same under `DEBUG_LOCKORDER` | An inversion between an RPC thread and the import thread would show here and nowhere else |
| 3 | Same under TSan, on Linux | The only way to see an unsynchronised read on chainstate |
| 4 | `getspentinfo` specifically, with `-txindex -spentindex` and a concurrent reindex | The P12 assertion path, exercised the way it would actually fail |

Step 4 is the one that decides P12: if the assertion fires under load, the lock
is required and the fix is not optional.

### 5.3 Verification parallelism: what would have to be true

Widening verification is the only change that could move post-Sapling sync, and
it is also the riskiest. **Do not attempt it before:**

1. **P1 measured post-Sapling** -- the cost is currently unquantified
   (`test-logs/p1-measured-20260912/FINDINGS.md`: the counters work but the
   tiny snap skips all proofs below the last checkpoint).
2. **The libsnark thread question answered** (S4 below). If the pinned crates
   already spawn threads inside proof verification, adding an outer pool
   oversubscribes rather than parallelises.
3. **TSan clean on the existing paths**, so a new race is attributable.

Then, and only then, the shape: verification is per-transaction and stateless
given an anchor, so it is a `CCheckQueue` candidate like script checks --
which is the structure Zebra reaches with rayon. The consensus risk is that
proof verification currently happens inside `CheckBlock` under `cs_main`;
moving it out changes when a failure is observed relative to the block being
connected.

### 5.4 Measured already

| Result | Where |
|--------|-------|
| Lock-order inversions: **0**; `AssertLockHeld` violation: **1** (P12) | `test-logs/lockorder-20260912/` |
| Recursive acquires: **5,567,609** (~29.7/block); underflows: **0** | `test-logs/lockstats-20260912/` |
| `?full` atomics cost: **-1.03%**, not distinguishable from noise | `test-logs/atomics-timing-20260911/` |
