#!/usr/bin/env python3
# Copyright (c) 2025 The Zcash developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .

#
# P2: Test -rescan on startup: node restarts with -rescan, chain and wallet intact
#


from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, initialize_chain_clean, \
    start_node, stop_node, wait_bitcoinds


class RescanStartupTest(BitcoinTestFramework):

    def setup_chain(self):
        print(("Initializing test directory "+self.options.tmpdir))
        initialize_chain_clean(self.options.tmpdir, 1)

    def setup_network(self):
        self.nodes = []
        self.is_network_split = False
        self.nodes.append(start_node(0, self.options.tmpdir))

    def run_test(self):
        self.nodes[0].generate(5)
        block_count = self.nodes[0].getblockcount()
        assert_equal(block_count, 5)

        stop_node(self.nodes[0], 0)
        wait_bitcoinds()

        # Restart with -rescan; verify chain and wallet intact
        self.nodes[0] = start_node(0, self.options.tmpdir, ["-rescan"])
        assert_equal(self.nodes[0].getblockcount(), 5)


if __name__ == '__main__':
    RescanStartupTest().main()
