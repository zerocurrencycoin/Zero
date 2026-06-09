# Linearize
Construct a linear, no-fork, best version of the blockchain.

Zero uses **CBlockHeader + Equihash `nSolution`** on disk (not Bitcoin's 80-byte header). `linearize-data.py` hashes headers the same way as `getblockhash` / `SerializeHash(CBlockHeader)`.

## Step 1: Download hash list

    $ ./linearize-hashes.py linearize.cfg > hashlist.txt

Required configuration file settings for linearize-hashes:
* RPC: rpcuser, rpcpassword

Optional config file setting for linearize-hashes:
* RPC: host, port
* Block chain: min_height, max_height

## Step 2: Copy local block data

    $ ./linearize-data.py linearize.cfg

Required configuration file settings:
* "input": bitcoind blocks/ directory containing blkNNNNN.dat
* "hashlist": text file containing list of block hashes, linearized-hashes.py
output.
* "output_file": bootstrap.dat
      or
* "output": output directory for linearized blocks/blkNNNNN.dat output

Optional config file setting for linearize-data:
* "netmagic": network magic number
* "max_out_sz": maximum output file size (default `1000*1000*1000`)
* "split_timestamp": Optional (default **0**). Set to **1** to split output files when a new month is first seen (only with `output=<dir>`, not `output_file`).
* "file_timestamp": Set each file's last-modified time to that of the
most recent block in that file.
