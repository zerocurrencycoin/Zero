# `TODO.md` proposals

Draft for Zero, in `TODO.md`'s own form: one-line entries for the named
section, then Full descriptions. Compared against Zero `72e421e41` and its
working tree; applied proposals are removed.

## Entries

Pending, Build, packaging, and release -- extend the REL-05 line:

- REL-05 -- inherited contrib and packaging tooling: ... ; `contrib/spendfrom/` (delete); `contrib/qos/` (keep, Zero naming)

Pending, a new Documentation group:

- DOC-ROOT-PLANNING -- move `AtHeight.md` and `WitnessReindex.md` to `doc/design/`

Remove from Pending; the perf tree tracks them:

- WAL-GETALLDATA W4 (IVK decrypt review) -- a measurement; drop W4 from the WAL-GETALLDATA-CACHE line
- OPS-CACHE-METRICS -- a measurement
- OPS-DEBUGLOG-TIMING -- done by `contrib/perf` `extract_measures.py`, `stall_check.py`, `debuglog.py`

## Full descriptions

### REL-05 -- `contrib/spendfrom/` and `contrib/qos/`

`contrib/spendfrom/` is partly ported (Zero datadir and RPC ports) and fails
at import on Python 3: it needs the unmaintained `jsonrpc` package, imports
the Python 2 `ConfigParser`, and `setup.py` uses `distutils`, removed in
Python 3.12. It handles transparent coins only; `zero-cli` raw-transaction
calls and `z_sendmany` cover coin control. Delete it and its entry in
`contrib/README.md`.

`contrib/qos/tc.sh` works for Zero: it shapes traffic on port 23801, Linux
only (`tc`, `iptables`), untested. Its comments and `README.md` say Bitcoin
and `bitcoind`. Keep it with Zero names, stating Linux only and untested.

Names that stay through any cleanup: `~/.zcash-params`, `qa/zcash/`, thread
names `zcash-loadblk` and `zcash-scriptch`, and `missing_zcash_conf`, whose
message already says `zero.conf`.

### DOC-ROOT-PLANNING

`README.md` names the ship set: `README`, `ZERO_COIN`, `BUILD_ZERO`,
`TEST_ZERO`, `CONTRIBUTING`, `TODO`, `AGENTS`, `doc/man/`. `AtHeight.md` and
`WitnessReindex.md` are labelled project planning and answer maintainer
questions. Check that no ship-set document links to them, then move both.
