# Shell and search failures in this work, and what closes each

Every instance where a `bash`/`grep`/`sed`/`awk` invocation returned a wrong or
misleading answer that was then acted on. Recorded because the pattern is
consistent: **each failed silently and produced a plausible-looking result.**

## 1. The failures

| # | What was run | What it returned | Why it was wrong |
|---|--------------|------------------|------------------|
| 1 | `grep --include=*.cpp` under zsh | "one call site" | zsh expanded the glob, matched nothing, printed nothing. Twelve call sites existed. zsh also aborts the command line on a non-matching glob, so the rest of the pipeline never ran |
| 2 | `awk -F=` on colon-separated `vmmap` output | every memory value blank | Wrong field separator; no error |
| 3 | `grep 'bitcoin\.conf' contrib/perf/ qa/` | "none" | **Scope assumed.** Nine files in `contrib/init/` and `contrib/spendfrom/` were never searched, and the conclusion was reported tree-wide |
| 4 | `grep -n 'hashLen' equihash.cpp:537` | "D3 patch not applied, measured then reverted" | Read the wrong lines. The change is `CompareSRFixed<>` at `:557`; `:537-538` are declarations serving *other* sort sites |
| 5 | `sed -i '' 's/^Equihash=47/Equihash=48/'` | silently no-op | The value was not at line start; `^` never matched. The ratchet stayed wrong until the next validate caught it |
| 6 | `strings src/zerod \| grep -c 'PerfProof:'` -> `0` | "counters missing" | `CXXFLAGS=-DZERO_PERF` does not reach the build; `ZERO_PERF` comes from `configure --enable-perf` into `bitcoin-config.h`. Inspected a binary built without the define |
| 7 | `bash performance-measurements.sh time <bench>` -> exit 0 | "benchmarks ran" | Node never started (`zcash.conf` vs `zero.conf`); every benchmark produced zero samples and the script still returned success |
| 8 | `codequery.sh count 'bitcoin\.conf'` | "NO MATCHES" | **The tool itself was wrong**: `count` hardcoded `-t cxx`, so non-C++ files could never match, and with no path it searched `src/` only |

## 2. Which `codequery.sh` fixes

**Closed by the tool as it stood:** 1 (no glob expansion, explicit no-match),
2 (not a text-field problem, but the same class -- use the tool rather than
hand-parsing).

**Closed by the tool after the fixes made today:** 3, 8. `count` no longer
restricts to C++; every mode with no PATH now searches the repository root and
**prints the scope it used** to stderr.

**Not closed by any search tool:** 4, 5, 6, 7. These are not search failures.

## 3. Closing the rest

| Gap | Failure | Closure |
|-----|---------|---------|
| **Reading the wrong line** (4) | A grep hit is not a reading of the code | Quote the *enclosing construct*, not the matched line. For "is this change applied", check the artifact -- a symbol in the object file, a test that fails when reverted |
| **`sed -i` no-ops** (5) | An anchored pattern that does not match exits 0 and changes nothing | **Never use `sed -i` for a value edit.** Use a Python replace that `assert`s the old text was present -- as every other edit in this session did. The one `sed -i` used was the one that failed |
| **Build flags not reaching the build** (6) | `CXXFLAGS` on the make line does not override `configure`-derived defines | Verify by artifact: `nm` for the symbol, `strings` for the format string, on the object you actually built. State which define came from where |
| **Wrapper exit code** (7) | A script that cannot do its job still exits 0 | `POLICY.md` S4 already requires verify-by-artifact. The gap was not the rule but its application: **check the output file has rows before reading the numbers** |

## 4. The one structural change

**`codequery.sh` is now installed as a project skill** (`.claude/skills/codequery/`)
so it is offered in context rather than remembered. Its description names the
trigger: *use it instead of ad-hoc grep whenever the answer will be written
down*.

Two defects in the tool were found by using it against failure 3, and both are
fixed: the C++-only type filter on `count`/`files`, and the implicit scope.
A tool that reports "no matches" for a file type it never searched is worse
than no tool, because the answer looks authoritative.

## 4a. `CPPFLAGS=` on the make line: three failures, one cause

Hit three times this session, each differently:

| Attempt | Symptom |
|---------|---------|
| `CXXFLAGS=-DZERO_PERF` | Define never reached any compile. `strings` showed 0 counters; reported as "counters missing" |
| `CPPFLAGS=-DDEBUG_LOCKORDER` | Only the TUs make chose to rebuild got the define. `POTENTIAL DEADLOCK` absent until `touch sync.cpp` |
| `CPPFLAGS=-DZERO_PERF` after a partial rebuild | **Link failure** -- `main.o` had the define, `sync.o` and `IncrementalMerkleTree.o` did not: `Undefined symbols: EnterCritical`, `MerkleRootCacheStats::calls` |

**Cause.** These defines come from `configure` into
`src/config/bitcoin-config.h`. Passing them on the make line changes the
compile of *only the files make decides to rebuild*, so the object set ends up
inconsistent. The link either fails loudly (best case) or succeeds with half
the tree instrumented.

**Rule: use `./configure --enable-perf` / `--enable-debug` and rebuild, or
`touch` every translation unit the define reaches.** A conditional symbol
defined in one TU and referenced from another is what turns this from a silent
wrong answer into a link error -- which is the good outcome.

**Which TUs, per define.** The dependency is not visible from the file being
edited, because the define changes a *header* and the definition and its
callers sit in different static archives:

| Define | Must rebuild together | Archive |
|--------|----------------------|---------|
| `DEBUG_LOCKORDER` | `sync.cpp` (the definitions) | `libbitcoin_util` |
| | **every TU that uses `LOCK()` / `AssertLockHeld()`** -- measured: not a short list. Restoring the default build surfaced stale objects in `main.o`, `init.o`, `sendalert.o`, `alert.o`, `addrman_tests.o` and more, one link error at a time | `libbitcoin_server`, `libbitcoin_common`, `libbitcoin_util`, test objects |
| `ZERO_PERF` | `main.cpp` (the counters and their logger) | `libbitcoin_server` |
| | `zcash/IncrementalMerkleTree.cpp` (`MerkleRootCacheStats`) | **`libzcash`** |

**Why it links rather than silently misbehaves.** `sync.h:86-95` declares
`EnterCritical` / `LeaveCritical` / `AssertLockHeldInternal` as **external
functions** under `DEBUG_LOCKORDER` and as **`static inline` no-ops** without
it. So a caller compiled with the define emits an undefined reference that
only `sync.o` compiled with the define can satisfy:

    Undefined symbols for architecture arm64:
      "EnterCritical(char const*, char const*, int, void*, bool)",
        referenced from: ... libbitcoin_server_a-main.o

`ZERO_PERF` behaves the same way through `MerkleRootCacheStats::calls` in
`libzcash`. **Three archives, one header** -- which is why `touch`ing only the
file you edited is never enough.

Finding the set is a `codequery` question, not a guess: the symbol names in the
linker error name the TUs, and `codequery raw -ln '<symbol>' src/` locates
them.

**Fourth failure, and the worst: `CPPFLAGS=` on the make line REPLACES
configure's `CPPFLAGS`, it does not add to it.** The generated `Makefile:313`
sets

    CPPFLAGS = -Qunused-arguments -I<depends>/include -DHAVE_BUILD_INFO \
               -D__STDC_FORMAT_MACROS -DPTHREAD_STACK_MIN=16384 -DMAC_OSX

so `make CPPFLAGS="-DDEBUG_LOCKORDER"` silently dropped **`-DMAC_OSX`** along
with the depends include path and three other defines. The build succeeded,
and the resulting binary resolved the proving-params directory to the Linux
path `~/.zcash-params` instead of `~/Library/Application Support/ZcashParams`
(`util.cpp:524`, `#ifdef MAC_OSX`). The node then refused to start with
"Cannot find the Zero network parameters", and a lock-stats measurement run
produced **zero blocks** while looking like a normal failure.

**This is worse than the first three** because nothing about the symptom
points at the cause: a missing params directory reads as an environment
problem, not as a build-flag problem.

**Corrected rule.** Either

    ./configure --enable-debug     # or --enable-perf; then plain `make`

or, if a one-off define is genuinely needed, **append** rather than replace:

    make CPPFLAGS="$(grep -m1 '^CPPFLAGS = ' Makefile | cut -d= -f2-) -DDEBUG_LOCKORDER"

`configure` is the supported path and the only one that keeps the platform
defines consistent. **`touch`ing the right files is necessary but not
sufficient** -- that fixes staleness, not flag replacement.

**And "the right files" is not enumerable for `DEBUG_LOCKORDER`.** `LOCK()`
expands to a `CMutexLock` constructor that calls `EnterCritical`, so *every*
TU that locks anything is affected. Restoring the default build after the
lock-stats run took **five** successive link failures, each naming a different
stale object. The only reliable procedure:

    # enter the configuration
    ./configure --enable-debug && make

    # leave it
    find src -name '*.o' -newermt '<when the define build started>' -delete
    find src -name '*.a' -newermt '<same>' -delete
    make

**A define that changes a widely-included header is a whole-tree rebuild.**
Treating it as an incremental one is what produced every failure in this
section.

**Verify by artifact either way**: `strings <binary> | grep <format string>`,
or `nm <object> | grep <symbol>`. A build that "succeeded" is not evidence the
define was applied.

## 5. The pattern

Seven of eight failures returned **a plausible value, not an error**. That is
the property to design against: prefer a tool that fails loudly, assert the
precondition in the edit, and verify the artifact rather than the exit code.

## 6. Shell and search tooling: accumulated observations

Collected across this session. The purpose is to stop rediscovering the same
classes.

### 6.1 What actually failed, by class

| Class | Instances | Example |
|-------|----------:|---------|
| **Scope assumed, not stated** | 2 | `grep` over two directories reported "no `bitcoin.conf` anywhere"; nine files had it |
| **Tool silently restricted** | 1 | `codequery count` hardcoded `-t cxx`, so non-C++ files could never match -- and it reported "no matches" authoritatively |
| **Shell portability** | 2 | zsh expanded `--include=*.cpp` and aborted the line; BSD `cat -A` is not GNU `cat -A` |
| **Anchored edit silently no-op** | 1 | `sed -i '' 's/^Equihash=47/...'` matched nothing, exited 0, changed nothing |
| **Wrong field separator** | 1 | `awk -F=` on colon-separated `vmmap` output -- every value blank, no error |
| **Build flags** | 5 | See S4a |
| **Exit code trusted over artifact** | 2 | `performance-measurements.sh` exited 0 having started no node; a "successful" build with no binary |

**Seven of these returned a plausible value rather than an error.** That is the
property to design against.

### 6.2 Mitigations now in place

| Mitigation | Closes |
|------------|--------|
| `codequery.sh` as a project skill, offered in context | scope-assumed, glob expansion |
| `codequery` prints the scope it used; defaults to repo root | scope-assumed |
| `codequery count` searches all file types; `countcxx` for C/C++ only | tool silently restricted |
| `check_buildconfig.py` + `buildconfig` lint check | build flags, exit-code-trusted |
| Python `replace` with `assert old in s` for every edit | anchored no-op |
| `POLICY.md` S4: verify by artifact, not exit code | exit-code-trusted |

### 6.3 Rules that follow, and are not yet enforced by anything

1. **Never `sed -i` for a value edit.** Use a Python replace that asserts the
   old text was present. The one `sed -i` used this session is the one that
   silently did nothing.
2. **Assume BSD userland, not GNU.** `cat -A`, `sed -i` without an argument,
   `grep -P`, `readlink -f`, `date -d` all differ or are absent on macOS.
   Prefer `od -c` over `cat -A`, `python3` over `sed -i`, and test any
   `sed -i ''` form twice.
3. **A glob that may not match needs a guard.** Under zsh a non-matching glob
   aborts the whole command line, and the line still exits 0 because the last
   statement succeeded.
4. **Quote the tool's number, not a hand-tallied one.** When a count goes into
   a document, it comes from `codequery count` or `check_tables.py`, not from
   reading output.
5. **Prefer a checked script over a pipeline** when the answer will be
   recorded. Pipelines fail at the first stage and report the last one's
   status.

### 6.4 What is still open

- **No lint check for `sed -i` in tracked scripts.** Rule 1 is prose.
- **No portability check.** Rule 2 is prose; a `shellcheck` directive or a
  banned-pattern grep could enforce the common cases.
- **`codequery` has no self-test.** It is now load-bearing -- it gates what
  gets written down -- and two defects in it were found only by using it
  against a known answer. It should assert, on a fixture tree, that a known
  string is found in a shell file, a Python file and a markdown file, and that
  a known-absent string reports no-match with exit 1.

That last one is the highest-value remaining item in this section: a search
tool that can be wrong about a negative is worse than no tool, because the
answer looks authoritative.
