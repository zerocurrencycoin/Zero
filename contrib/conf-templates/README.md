# conf-templates

Apply with `contrib/zero-conf.sh`. Default template **prod**, default file `/tmp/zero.conf`.
Do not copy a live datadir conf into git (credentials).

| Template | Adds over the empty file | Use when | Default RPC port |
|----------|--------------------------|----------|------------------|
| **prod** | Generated `rpcuser` and `rpcpassword`, `gen=0`, `genproclimit=1`, `equihashsolver=tromp` | A client that does not read `.cookie`, such as Zerowallet or a tool under another user | 23811 |
| **lab** | `listen=0`, `maxconnections=0` | An isolated scratch node for tests and `ops-validate.sh` | 23941 |
| **zerowallet** | The keys Zerowallet writes when it creates `zero.conf` (`txindex`, `deletetx`, `keeptx*`, `consolidation*`, `rpcworkqueue`) | A node for Zerowallet configured as the wallet would | 23811 |
| **insight** | `txindex`, `insightexplorer`, ZMQ on 127.0.0.1:28332, `disablewallet`, P2P port 23801 | An explorer backend | 23811 |

`-dir` sets the directory, `-out` the filename. `-force` overwrites and allows `~/.zero`, `Application Support/zero|Zero`, or the product tree.
