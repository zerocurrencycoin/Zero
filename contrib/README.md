# contrib

Tools and samples that ship with the Zero full node but are not part of `zerod`. Use is described where it applies: BUILD_ZERO "Configuration" for the configuration files, TEST_ZERO "Run" and "Operational checks" for the test drivers. Each script lists its options with `--help`.

## Configuration

| Path | Purpose |
|------|---------|
| `zero.conf` | Commented example: every option an operator sets, with its default |
| `zero-conf.sh`, [conf-templates/](conf-templates/) | Write a `zero.conf` from a role template |

## Testing and validation

| Path | Purpose |
|------|---------|
| `run-tests.sh` | Merge gate and release test run |
| `run-boost-individual.sh` | Run each Boost suite of `test_bitcoin` separately and report per suite |
| `ops-validate.sh` | Start, restart, reindex, and import checks on scratch data directories |
| [testgen/](testgen/) | Generator for the base58 test vectors in `src/test/data/`; TODO "Base58 vectors" ports it to Zero's address prefixes |

## Chain data and statistics

| Path | Purpose |
|------|---------|
| `stats/chain_stats.py` | Emission and coinbase-split totals, from the model or a synced node |
| `stats/decode_coinbase.py` | Decode the coinbase outputs of given heights |
| `stats/block_rate_replay.py` | Replay block timestamps through the block-rate warning and fast-block checks |
| [linearize/](linearize/) | Build `bootstrap.dat` from a synced node's block files (Zero header format) |
| `zmq/zmq_sub.py` | Example ZMQ subscriber for `-zmqpub*` notifications |
| [seeds/](seeds/) | `generate-seeds.py` writes `src/chainparamsseeds.h` from `nodes_main.txt` and `nodes_test.txt`; TODO "Peer discovery" |

## Maintenance

| Path | Purpose |
|------|---------|
| `tools/inventory-check.py` | Check `doc/RPCs.csv` and `doc/Options.csv` against the RPC tables and option parsing in `src/` |
| `tools/reindex-rescan-table.py` | Write `doc/Reindex_Rescan.csv` |
| `devtools/gen-manpages.sh` | Regenerate `doc/man/` from the help text, at each version change |
| `devtools/symbol-check.py`, `devtools/security-check.py` | ELF symbol-version and hardening checks run by `make check-symbols` and `make check-security` |
| `devtools/git-subtree-check.sh` | Check that a vendored subtree (`src/leveldb`, `src/secp256k1`, `src/univalue`) matches the upstream squash commit recorded by `git subtree` |

## Legacy

Inherited from Bitcoin Core or Zcash and not working or not used for Zero. Each is covered by the TODO item named.

| Path | State | TODO item |
|------|-------|-----------|
| `amqp/` | AMQP subscriber; AMQP is not built | "AMQP removal" |
| `zcashd.bash-completion`, `zcash-cli.bash-completion`, `zcash-tx.bash-completion` | Complete the Zcash binary names, not `zerod`, `zero-cli`, `zero-tx` | "Contrib cleanup" |
| `init/` | `bitcoind` service files | "Contrib cleanup" (one `zerod.service`) |
| `bitrpc/` | Needs the Python `jsonrpc` module; `zero-cli` does the same | "Contrib cleanup" |
| `spendfrom/` | Bitcoin raw-transaction tool, Bitcoin data directory | "Contrib cleanup" |
| `qos/` | Linux traffic shaping for port 23801 | "Contrib cleanup" |
| `tidy_datadir.sh` | Removes pre-0.8 Bitcoin database files | "Contrib cleanup" |
| `macdeploy/` | Builds a Bitcoin Core `.dmg`; Zero ships a zip (`zcutil/release-macos.sh`) | "Contrib cleanup" |
| `verify-commits/` | Verifies merges against Bitcoin Core maintainer keys | "Contrib cleanup" |
| `verifysfbinaries/` | Verifies SourceForge downloads; Zero does not publish there | "Contrib cleanup" |
| `test-patches/` | Patches for a Bitcoin Jenkins host that no longer exists | "Contrib cleanup" |
| `devtools/github-merge.sh`, `fix-copyright-headers.py`, `optimize-pngs.py` | Bitcoin Core maintainer tools; Zero merges through GitHub pull requests | "Contrib cleanup" |

The inherited README files in these directories are kept as upstream wrote them.
