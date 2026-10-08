# conf-templates

Apply with `contrib/zero-conf.sh`. Default template **prod**, default file `/tmp/zero.conf`.
Do not copy a live datadir conf into git (credentials).

Ports:

- **23801-23820** -- deployments and tests that deliberately use chain defaults (mainnet P2P **23801** / RPC **23811**, testnet 23802/23812, regtest 23803/23813).
- **lab** template defaults to RPC **23941** (isolated). `ops-validate` Equihash / mine uses **23951**.
- QA RPC harness picks ephemeral ports in **11000+** / **12000+** (pid-based), not the deployment range.

| Template | Role | Default RPC |
|----------|------|-------------|
| **prod** | Production operator (`gen=0`, wallet RPC) | 23811 |
| **lab** | Isolated scratch for tests and `ops-validate.sh` (`listen=0`) | 23941 |
| **zerowallet** | GUI autogen keys (`txindex`, `deletetx*`, `consolidation*`) | 23811 |
| **insight** | Explorer flags + `disablewallet` (P2P 23801 in template) | 23811 |

`-dir` sets the directory, `-out` the filename. `-force` overwrites and allows `~/.zero`, `Application Support/zero|Zero`, or the product tree.

`contrib/zero.conf` is the commented example of every option with its default; these templates are ready-made files for one role each.
