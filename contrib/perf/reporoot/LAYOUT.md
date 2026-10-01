# Repository layout: root documents and inherited `contrib/`

Draft for Zero. Compared against Zero `72e421e41` and its working tree.
Pending items only; applied proposals are removed.

## Root documents

`README.md` names the ship set: `README`, `ZERO_COIN`, `BUILD_ZERO`,
`TEST_ZERO`, `CONTRIBUTING`, `TODO`, `AGENTS`, `doc/man/`. Already done in
Zero: `ExtTests.md` removed, `UpdateZero.md` and `ZeroStruct.md` cut down.

| File | Proposal | Reason |
|------|----------|--------|
| `AtHeight.md` | Move to `doc/design/` | Labelled project planning; answers a maintainer's question, not a user's |
| `WitnessReindex.md` | Move to `doc/design/` | Findings and proposals on witness rebuild, a planning document |
| `README.md` line 1 | Delete the stray `concept` before the banner image | Renders on the repository front page |

Check before moving: no ship-set document links to either file.

## Inherited `contrib/`

`contrib/init/` and `contrib/macdeploy/` are already in Zero's REL-05. Two
directories are not:

| Path | State | Proposal |
|------|-------|----------|
| `contrib/spendfrom/` | Partly ported: Zero datadir and RPC ports. Fails at import on Python 3: needs the unmaintained `jsonrpc` package, imports the Python 2 `ConfigParser`, and `setup.py` uses `distutils`, removed in Python 3.12. Transparent coins only | **Delete**, with its entry in `contrib/README.md`. `zero-cli` raw-transaction and `z_sendmany` calls cover coin control; a port would be a new tool, not a fix |
| `contrib/qos/` | Works for Zero: `tc.sh` shapes traffic on port 23801. Linux only (`tc`, `iptables`); comments and `README.md` still say Bitcoin and `bitcoind`. Untested | **Keep, fix the text**: Zero names in the comments and README; state Linux only and untested. Or add it to REL-05 if Zero would rather not carry operator samples |

Add the outcome to REL-05 so inherited `contrib/` is decided in one item.

## Names that stay

Zcash-era names that are correct for Zero; a cleanup must not change them:
`~/.zcash-params` (shared parameter files), `qa/zcash/`, the thread names
`zcash-loadblk` and `zcash-scriptch`, and the exception type
`missing_zcash_conf`, whose message already says `zero.conf`.
