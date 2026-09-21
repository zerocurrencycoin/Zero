# Validating a build configuration

**The problem, measured.** Five build-flag failures in one session
(`TOOLING_FAILURES.md` S4a). Every one of them: **the build succeeded and the
binary was wrong.** None was caught by the build.

| Attempt | Result |
|---------|--------|
| `CXXFLAGS=-DZERO_PERF` | define never reached any compile |
| `CPPFLAGS=-DDEBUG_LOCKORDER` | reached only the TUs make chose to rebuild |
| `CPPFLAGS=` on the make line | **replaced** configure's flags, dropping `-DMAC_OSX`; two measurement runs produced zero blocks, reported as a missing-parameters environment error |
| restoring the default build | eight successive link failures |
| stale 8-byte `libunivalue.a` | blocked the rebuild without erroring |

## The method: check the artifact, never the command line

`contrib/perf/check_buildconfig.py` looks for **string markers that exist only
when a feature is compiled in** -- a log format string, not a symbol, so it
works on a stripped binary:

| Feature | Marker | Proves |
|---------|--------|--------|
| `ZERO_PERF` | `PerfProof: height=` | proof-verification counters (P1) |
| `DEBUG_LOCKORDER` | `LockStats: recursive_acquires=` | lock checker and hygiene counters |
| `MAC_OSX` | `Library/Application Support` | macOS parameter and datadir paths |

```bash
# the default build: platform defines present, lab instrumentation absent
contrib/perf/check_buildconfig.py src/zerod \
  --expect MAC_OSX --reject ZERO_PERF --reject DEBUG_LOCKORDER

# after entering a lab configuration
contrib/perf/check_buildconfig.py src/zerod --expect ZERO_PERF --expect MAC_OSX
```

Exit 1 on any mismatch. **A missing binary is an error, not a pass** -- that
case is asserted in the self-test, because "build succeeded, no binary" is what
a failed link looks like from the outside.

Wired into `lint-perf.sh` as the `buildconfig` check, so the default build is
verified on every `validate.sh` run.

## Procedure for entering and leaving a build configuration

**Enter:**

```bash
./configure --enable-perf        # or --enable-debug; never CPPFLAGS= on make
make -j4
contrib/perf/check_buildconfig.py src/zerod --expect ZERO_PERF --expect MAC_OSX
```

**Leave:**

```bash
make -C src clean          # removes exactly what src/Makefile built
./configure                # back to defaults
make -j4
contrib/perf/check_buildconfig.py src/zerod --expect MAC_OSX --reject ZERO_PERF
```

## Never use a blanket `find -delete` in this tree

**This was done once and it was a serious mistake.** A
`find src \( -name '*.o' -o -name '*.a' \) -delete` intended to clear objects
tainted by a define also removed **vendored sub-project artifacts** --
`src/univalue/.libs/libunivalue.a` and `src/leveldb/*.a` -- which are produced
by their own makefiles and are not rebuilt by `make -C src`. Recovery took
several manual steps and left an 8-byte stub archive that blocked the rebuild
until deleted by hand.

**Two things were wrong, and only one was the blast radius:**

1. **The command was unbounded.** `find` walked into `univalue/` and
   `leveldb/`, which `make -C src clean` would never touch.
2. **The premise was wrong.** An earlier revision of this file claimed
   archives "retain old members". They do not: `src/Makefile:2285ff` shows
   every archive rule runs `rm -f <archive>` and re-creates it from the full
   current object list. An archive is always exactly its objects. The repeated
   link failures were **stale objects that make had no reason to rebuild** --
   `make clean` handles that correctly and no `find` was ever needed.

### The rule

**Use the build system's own clean target. Do not hand-roll deletion.**

```bash
make -C src clean                 # the supported way
make -C src/univalue clean        # only if a sub-project is genuinely stale
make -C src/leveldb clean
```

### If a manual delete is ever unavoidable

It should not be, but if it is:

1. **List before deleting. Always.** `find ... -print` first, read the list,
   then re-run with `-delete`. Never combine discovery and destruction in one
   command.
2. **Bound the path explicitly**, excluding every vendored tree:

   ```bash
   find src -name '*.o' \
     -not -path 'src/univalue/*' \
     -not -path 'src/leveldb/*' \
     -not -path 'src/secp256k1/*' \
     -print            # inspect, THEN add -delete
   ```
3. **Confirm the vendored list first.** Sub-projects are those with their own
   `Makefile.am`: `codequery raw -l 'AC_INIT' src/*/configure.ac` or simply
   `ls src/*/Makefile.am`. Anything in that list is off limits.
4. **Never delete `.a` by hand.** Archives are always regenerated from
   objects; deleting objects alone is sufficient, and deleting a vendored
   archive is what caused the recovery work.
5. **Verify by artifact afterwards** -- `check_buildconfig.py` on the rebuilt
   binary.

**This is a directive, not a preference.** The blanket form cost a full
rebuild and a manual sub-project repair, and the thing it was trying to fix
had a supported one-line solution.

## Why `touch` is not enough

## Why `touch` is not enough

`LOCK()` expands to a `CMutexLock` constructor that calls `EnterCritical`, so
**every TU that locks anything** depends on `DEBUG_LOCKORDER`. There is no
short list to `touch`. A define that changes a widely-included header is a
whole-tree rebuild; treating it as incremental is what produced the eight link
failures.

The link errors are at least loud. The dangerous case is a define that changes
*behaviour* without changing any symbol -- `MAC_OSX` is exactly that, and it
produced a plausible-looking runtime error two directories away from the cause.
That is the case this checker exists for.
