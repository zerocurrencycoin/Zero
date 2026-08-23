# Vendored Zcash lint scripts

Unmodified copy of `test/lint/` from the Zcash tree at
`~/Work/ZK/ZKs/zcash`, taken **2026-08-19**.

| Field | Value |
|-------|-------|
| Source | `ZKs/zcash/test/lint/` |
| Zcash checkout at copy time | `86451a18b` (2026-01-08, "make-release.py: Updated book for 6.11.0.") |
| Last upstream change to `test/lint/` | `85781de2c` (2023-04-13) |
| Files | 15; upstream copies except `lint-include-guards.sh` (see Local changes); `README.md` is upstream's |

Here for **experimentation only**. Not wired into `contrib/run-tests.sh` or CI,
and not run by any perf script. Zero ships no lint suite of its own.

## Running

The scripts assume they are run from a repo root and mostly operate on tracked
files or on the working diff:

```bash
cd ~/Work/ZK/ZeroPerf
contrib/perf/zcash-lint/lint-whitespace.sh
contrib/perf/zcash-lint/lint-shebang.sh
contrib/perf/zcash-lint/lint-all.sh      # runs every lint-*.sh, exit 1 if any fail
```

`lint-all.sh` globs `lint-*.sh` beside itself, so it picks up whatever is in
this directory.

## Baseline against ZeroPerf, 2026-08-19

| Script | Exit | Note |
|--------|------|------|
| `lint-whitespace.sh` | 0 | clean |
| `lint-shell.sh` | 0 | shellcheck not installed; self-skips |
| `lint-cargo-patches.sh` | 0 | clean |
| `lint-make-dist.sh` | 0 | clean |
| `lint-shebang.sh` | 1 | 12 scripts use `#!/bin/bash`, not `#!/usr/bin/env bash`; 11 are `contrib/perf/*.sh`. Zero400 `zcutil/*.sh` already uses the env form (8 of 8) |
| `lint-shell-locale.sh` | 1 | ~20 scripts lack `export LC_ALL=C` |
| `lint-python-utf8-encoding.sh` | 1 | `open()` without `encoding="utf8"`; 3 sites in `contrib/perf/` |
| `lint-include-guards.sh` | 1 | **Not applicable.** Expects `ZCASH_*` guards; Zero inherited `BITCOIN_*` from Bitcoin |
| `lint-includes.sh` | 1 | include ordering / duplication, 251 lines |
| `lint-locale-dependence.sh` | 1 | 71 lines |

### Local changes to the vendored scripts

`lint-include-guards.sh`: `HEADER_ID_PREFIX` changed from `ZCASH_` to
`${HEADER_ID_PREFIX:-BITCOIN_}`. Zero inherited `BITCOIN_*` guards from Bitcoin
(111 headers) rather than Zcash's `ZCASH_*` (11). Overridable from the
environment, so the upstream behaviour is still reachable:
`HEADER_ID_PREFIX=ZCASH_ contrib/perf/zcash-lint/lint-include-guards.sh`.
This took the finding count from 225 to 52; the remainder are headers using
`ZCASH_`, `ZC_`, `ASYNCRPCOPERATION_`, `ZERONODE_` and similar prefixes.

### Acted on

`lint-shebang.sh`: the 9 `contrib/perf/*.sh` scripts using `#!/bin/bash` now use
`#!/usr/bin/env bash`. Zero400-owned scripts were left alone.
`contrib/perf/datadir_guard.sh` is still reported and is a **false positive**:
it is sourced, not executed (mode 644, no shebang by design).

`lint-python-utf8-encoding.sh`: 9 `open()` calls across `decode_captures.py`,
`extract_measures.py` and `measure_dbcache_utxo.py` now pass `encoding="utf8"`
explicitly. These parse `debug.log`; without it they inherit the platform
locale and can raise on non-UTF-8 bytes.

`lint-shell-locale.sh`: `export LC_ALL=C` added as the first non-comment line to
the 10 executable `contrib/perf/*.sh`. Locale-dependent `sort`/`grep` collation
changes results in a measurement harness. `datadir_guard.sh` is deliberately
excluded and still reported: it is sourced, so setting `LC_ALL` there would
override the caller's locale.

`shellcheck` (0.11.0, installed 2026-08-19), run over `contrib/perf/*.sh` with
the upstream exclusion set: 9 findings, of which one mattered --
**SC2115** on `tiny_baseline.sh:49`, `rm -rf "$LAB"/*`, now `rm -rf "${LAB:?}"/*`
so an empty `LAB` can never expand to `/*`. `LAB` already has a default and
passes `refuse_live_datadir`, so this is insurance, not a live bug. The other
`rm -rf "$VAR"` sites in the harness lack the `/*` suffix; an empty variable
there fails harmlessly, which is why shellcheck flags only the one.
Remaining: 3x SC1010, 2x SC2155, 2x SC2034 -- style, not acted on.

### Patched: lint-shell.sh (was broken on macOS)

`lint-shell.sh` does not work on macOS. Its file-discovery regex contains an
empty alternation branch:

    grep -vE '(qa/zcash/checksec\.sh|src/(|leveldb|secp256k1|univalue)/)'

GNU grep accepts `(|leveldb|...)`; BSD/macOS grep rejects it as an "empty
(sub)expression", so no files reach shellcheck and it exits on a usage error
that looks like a lint failure. Run shellcheck directly instead:

```bash
shellcheck --exclude=SC2046,SC2086,SC2162,SC2035,SC2043,SC2094,SC2129,SC2164,SC2230 \
  $(git ls-files 'contrib/perf/*.sh')
```

**Patched 2026-08-19:** the empty branch is removed --
`src/(leveldb|secp256k1|univalue)/` -- which keeps the intent and is valid POSIX
ERE. Verified: the script now actually reaches shellcheck, reports 78 findings
tree-wide, and still skips the vendored subtrees.

Confirmed on macOS that **both** `/usr/bin/grep` (BSD) and `ugrep` 7.5.0 reject
the original; GNU grep accepts it, which is why upstream never saw this.

**RECHECK:** the fix is POSIX-valid so it should behave identically under GNU
grep, but that has not been exercised here. Re-run `lint-shell.sh` on Linux
before relying on it there or upstreaming the change. A `RECHECK:` comment
marks the line in the script.

Nothing else has been acted on.

## Results, 2026-08-19 (after cleanup)

Findings, not output lines. "perf" = findings in `contrib/perf/`.

| Script | Findings | perf | Disposition |
|--------|---------:|-----:|-------------|
| `lint-whitespace.sh` | 0 | 0 | clean |
| `lint-make-dist.sh` | 0 | 0 | clean |
| `lint-cargo-patches.sh` | 0 | 0 | clean |
| `lint-shell.sh` + shellcheck | 78 | **0** | **perf resolved.** Rest is upstream: will not fix |
| `lint-shebang.sh` | 15 | 1 | perf resolved; the 1 is `datadir_guard.sh`, false positive (sourced, mode 644). Rest upstream: will not fix |
| `lint-shell-locale.sh` | 38 | 1 | same; `datadir_guard.sh` deliberately excluded (sourced, would override caller locale) |
| `lint-python-utf8-encoding.sh` | 17 | 0 | perf resolved. Rest upstream: will not fix |
| `lint-include-guards.sh` | 52 | 0 | real after the `BITCOIN_` recode, all in inherited `src/` headers: **will not fix** |
| `lint-includes.sh` | many | 0 | include ordering in inherited upstream source: **will not fix** |
| `lint-locale-dependence.sh` | 71 | 0 | C++ locale-dependent calls in consensus-adjacent inherited code: **will not fix** without per-site review |

**Standing rule:** findings in code inherited from Bitcoin/Zcash are *set aside
/ will not fix*, not postponed. Changing them diverges from upstream, creates
permanent merge friction, and buys no function. Only ZeroPerf-owned files under
`contrib/perf/` are held to these linters.

### shellcheck resolutions in contrib/perf

`contrib/perf/*.sh` is now **shellcheck clean** under the upstream exclusion set.

| Finding | Site | Resolution |
|---------|------|------------|
| SC2115 | `tiny_baseline.sh:49` | `rm -rf "$LAB"/*` -> `"${LAB:?}"/*`; an empty `LAB` can never expand to `/*` |
| SC1010 | `ops-campaign.sh:110` | `local done` renamed `done_list`. **This also fixed a live bug**: the loop below compared against `$done`, which was never assigned, so `next_id` matched nothing |
| SC1010 | `wallet_sync_profile.sh:191` | `sample_row done` -> `sample_row "done"`; a literal phase label beside `start` / `measure` / `after_stop`, not the keyword |
| SC2155 x2 | `bench_matrix.sh:306`, `ops-campaign.sh:243` | split `local x=$(cmd)` into declare + assign so the command's exit status is not masked |
| SC2034 x3 | `bench_matrix.sh` bounded retry loops | `for i in $(seq ...)` -> `for _ in ...` where the counter is unused |

## Relation to fix_ascii.py

No script here checks source **content** for non-ASCII.
`lint-python-utf8-encoding.sh` is the only one matching "utf8", and it checks
how Python `open()` calls are written, not what characters files contain.
Bitcoin Core's 16 linters have no such check either. `contrib/perf/fix_ascii.py`
covers that gap; see UpdateZero.md **DOC-UNICODE**.
