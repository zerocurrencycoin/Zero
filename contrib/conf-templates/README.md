# conf-templates

Apply with `contrib/zero-conf.sh`. Default template **prod**, default file `/tmp/zero.conf`.
Do not copy a live datadir conf into git (credentials).

| Template | Role | Default RPC |
|----------|------|-------------|
| **prod** | Production operator (`gen=0`, wallet RPC) | 23811 |
| **lab** | Isolated scratch for tests and `ops-validate.sh` (`listen=0`) | 23941 |
| **zerowallet** | GUI autogen keys (`txindex`, `deletetx*`, `consolidation*`) | 23811 |
| **insight** | Explorer flags + `disablewallet` (P2P 23801 in template) | 23811 |

`-dir` sets the directory, `-out` the filename. `-force` overwrites and allows `~/.zero`, `Application Support/zero|Zero`, or the product tree.

`contrib/zero.conf` is the commented example of every option with its default; these templates are ready-made files for one role each.
