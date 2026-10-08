#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""
Index flags stored in the block index (archiverule, txindex, prunedblockfiles,
insightexplorer, zindex) decide whether startup reindexes:

- A new datadir records the flags without a reindex.
- Changing an index option on a datadir with blocks reindexes once and keeps
  the chain.
- Restarting with unchanged options does not reindex.
- Turning the option off again reindexes once more.
"""

import os
import time

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, initialize_chain_clean, \
    start_node, stop_node, wait_bitcoinds

BLOCKS = 20
MISMATCH = "Reindex source: DB_FLAG mismatch"


class ReindexDbFlagsTest(BitcoinTestFramework):

    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 1)

    def setup_network(self):
        self.nodes = [start_node(0, self.options.tmpdir)]
        self.is_network_split = False

    def log_lines(self):
        path = os.path.join(self.options.tmpdir, "node0", "regtest", "debug.log")
        with open(path, encoding="utf-8", errors="replace") as f:
            return [line for line in f if MISMATCH in line]

    def restart(self, args):
        stop_node(self.nodes[0], 0)
        wait_bitcoinds()
        before = len(self.log_lines())
        self.nodes[0] = start_node(0, self.options.tmpdir, args)
        deadline = time.time() + 120
        while self.nodes[0].getblockcount() < BLOCKS:
            assert time.time() < deadline, "chain not restored after restart"
            time.sleep(0.5)
        assert_equal(self.nodes[0].getblockcount(), BLOCKS)
        return self.log_lines()[before:]

    def run_test(self):
        assert_equal(self.log_lines(), [])
        self.nodes[0].generate(BLOCKS)

        new = self.restart(["-zindex=1"])
        assert_equal(len(new), 1)
        assert "(zindex stored=0 desired=1)" in new[0]

        assert_equal(self.restart(["-zindex=1"]), [])

        new = self.restart([])
        assert_equal(len(new), 1)
        assert "(zindex stored=1 desired=0)" in new[0]


if __name__ == '__main__':
    ReindexDbFlagsTest().main()
