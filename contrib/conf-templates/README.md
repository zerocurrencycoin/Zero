# conf-templates

Apply with `contrib/zero-conf.sh`. Default template **prod**, default file `/tmp/zero.conf`.
Do not copy a live datadir conf into git (credentials).

| Template | Role |
|----------|------|
| **prod** | Default. Production operator action (`gen=0`, wallet RPC) |
| **test** | Isolated tests (`listen=0`) |
| **lab** | OPS scratch (`listen=0`) |
| **node** | Bare node + wallet RPC |
| **zerowallet** | GUI autogen keys (`txindex`, `deletetx*`, `consolidation*`) |
| **insight** | Explorer flags + `disablewallet` |
| **full** | Listening node, wallet, `txindex` (not Insight indexes) |

`-dir` sets the directory, `-out` the filename. `-force` overwrites and allows `~/.zero`, `Application Support/zero|Zero`, or the product tree.

In-tree samples `contrib/zero.conf` and `contrib/debian/examples/zero.conf` remain; prefer these templates for new files.
