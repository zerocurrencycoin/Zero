# Autotools re-configure trap

Recorded 2026-08-19 after it fired on ZeroPerf. **Present in both trees**;
nothing here is perf-specific, but the note lives on the perf side because that
is where it was hit and where the hardening would be prototyped.

## Symptom

Any `make` fails before compiling anything:

```
configure: error: libdb_cxx headers missing, Bitcoin Core requires this library
for wallet functionality (--disable-wallet to disable wallet functionality)
```

The tree built fine minutes earlier and no dependency was removed.

## Trigger

Automake's maintainer-mode rules re-run `configure` when `configure.ac`,
`configure`, or `config.status` is newer than `Makefile`. Editing `configure.ac`
is the obvious cause; so is any `autogen.sh` run, a `git checkout` that touches
those files, or a stash pop that restores their timestamps.

The re-run is spawned by `make` **without** the environment the original
`configure` had.

## Root cause

The BDB, Boost and OpenSSL paths do not come from `configure` defaults. They
come from the depends prefix, exported as `CONFIG_SITE`:

```
depends/<host>/share/config.site      # e.g. aarch64-apple-darwin25.3.0
```

which prepends `-I$depends_prefix/include` to `CPPFLAGS`. `zcutil/fzero.sh`
provides `export_config_site()` and `zcutil/build-native.sh` / `build-win.sh`
call it, so a normal build is fine. **The automake-spawned re-run inherits none
of that**, so the BDB C++ header probe fails and the whole build stops.

Confirmed pre-existing and **not** caused by any local edit: with no
`configure.ac` change at all,

```bash
cd Zero400 && ./config.status --recheck     # same libdb_cxx error
```

## Recovery

Re-run configure with the depends config.site, then regenerate:

```bash
cd <tree>
export CONFIG_SITE="$PWD/depends/aarch64-apple-darwin25.3.0/share/config.site"
./config.status --recheck      # re-runs configure with the ORIGINAL arguments
./config.status                # regenerate Makefiles and bitcoin-config.h
make -C src zero-gtest test/test_bitcoin
```

`--recheck` matters: it replays the original argument list. A bare
`./configure` loses whatever flags the tree was built with.

Substitute the actual host triple; `zcutil/fzero.sh` `guess_build_host()`
derives it.

## Why it is worth hardening

- The error names a **missing library**, which is misleading: the library is
  present, the include path is not.
- It fires at an unrelated moment -- days after the edit that changed the
  timestamps, on whatever `make` runs next.
- It stops the build completely rather than degrading, and the obvious next
  move (`./configure`) silently drops the original flags.

## Hardening options, not implemented

1. **Persist `CONFIG_SITE` at configure time** so the automake re-run inherits
   it. Cheapest fix; needs a check that it does not leak into `make dist`.
2. **Detect and explain**: have `configure.ac` fail the BDB probe with a message
   naming `CONFIG_SITE` and the depends path, instead of the stock upstream text.
3. **Wrapper target**: a `make reconfigure` in `zcutil/` that exports the site
   file and calls `config.status --recheck`, so recovery is one documented
   command.
4. **Leave it**, and rely on this note. Acceptable while builds go through
   `zcutil/build-native.sh`, which already exports the site file.

Option 1 or 2 is the smallest real improvement. Both touch `configure.ac`, which
is Zero400-owned, so neither should land as a perf-local change.
