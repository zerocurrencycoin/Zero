# Running ThreadSanitizer on Linux

**Not runnable on the current host.** `configure.ac:471` states TSan is
"supported on Linux x86_64 and tested on Ubuntu 12.04"; this tree's only
measurement host is macOS/arm64. These are the instructions for when a Linux
host exists -- the same prerequisite as **B2**.

## Why TSan, given DEBUG_LOCKORDER exists

They find different classes and neither subsumes the other:

| | DEBUG_LOCKORDER | ThreadSanitizer |
|---|---|---|
| Finds | lock-order inversions; `AssertLockHeld` violations | **data races on unsynchronised memory** |
| Sees plain `u32` incremented from two threads | **no** | **yes** |
| Needs the race to actually interleave | no -- flags the *order* | yes, but detects near-misses via happens-before |
| Cost | small | 5-15x slowdown, 5-10x memory |

The `xfull`/`bfull`/`hfull` race was found **by reading**, not by tooling.
TSan is what would have found it automatically, and it is the only tool here
that would.

## Build

```bash
./autogen.sh
./configure --enable-tsan --enable-debug --with-incompatible-bdb
make -j4
```

Notes from `configure.ac:470-477`:

- **`--enable-tsan` and `--enable-asan` are mutually exclusive.** Separate
  build trees, separate runs.
- **Needs `-fPIE -pie`**; non-position-independent executables are
  unsupported. `--enable-hardening` (default) already supplies these.
- **Static libc/libstdc++ is unsupported**, so do not combine with a
  fully-static release build.
- `--enable-debug` adds `DEBUG_LOCKORDER`, which is compatible and worth
  having in the same tree: one run, both classes.

## Run

Order matters -- cheapest and most targeted first.

```bash
# 1. Unit suite. Fastest signal, no network, no chain data.
TSAN_OPTIONS="halt_on_error=0 history_size=4 second_deadlock_stack=1" \
  ./src/test/test_bitcoin --log_level=message 2>&1 | tee tsan-unit.log

# 2. RPC/functional suite. Exercises the P2P and wallet threads the unit
#    tests never start -- this is where the 17 launch sites (THREADS.md)
#    actually run.
TSAN_OPTIONS="halt_on_error=0 history_size=4" \
  ./qa/pull-tester/rpc-tests.sh 2>&1 | tee tsan-rpc.log

# 3. A short reindex. Exercises ThreadImport (zcash-loadblk) plus the
#    script-check pool at a real width.
TSAN_OPTIONS="halt_on_error=0" \
  ./src/zerod -datadir=/tmp/tsanlab -reindex -disablewallet -par=4
```

`halt_on_error=0` is deliberate: collect every report in one pass rather than
stopping at the first. `history_size=4` widens the recorded access history at
a memory cost -- raise it only if reports show "unknown thread".

## Reading the output

A TSan report names two stacks and the object. Triage in this order:

1. **Is the object in `src/leveldb/` or `depends/`?** Vendored; record it and
   move on. Not ours to fix, and upstream may already know.
2. **Is one stack a diagnostic counter?** Like the `?full` case -- real, low
   severity, fix by making the type atomic.
3. **Is either stack in wallet or chainstate code?** Escalate. That is a
   correctness question, not hygiene.

**A clean TSan run is not proof of absence** -- it only observed the
interleavings that happened. Report n, the suites run, and the wall time.

## Expected findings, stated in advance

So that a clean run is informative rather than reassuring:

- **libsnark.** The 2016 commit disabling multi-worker async RPC cites
  "libsnark which by default uses multiple threads". Whether the pinned crates
  spawn threads inside proof verification has never been verified here
  (`THREADS.md` S4). TSan on a reindex would answer it.
- **leveldb.** Has its own threading (`env_posix.cc`); expect noise.
- **The script-check pool at `-par>1`.** The one genuinely parallel path in
  normal operation.

## Recording the result

One `M-*` row is not the right shape -- a TSan run is a verdict, not a
measurement. Write `test-logs/tsan-<utc>/FINDINGS.md` with the build config,
the suites run, wall time, and one line per report with its triage class.
`RECORDS_READINESS.md` S3a item 3 (a `verdict` kind) is what would let this
into the store proper.
