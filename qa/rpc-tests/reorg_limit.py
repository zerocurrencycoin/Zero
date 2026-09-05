#!/usr/bin/env python3
# Copyright (c) 2017 The Zcash developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .

#
# Test reorg limit
#


from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    MAX_REORG_LENGTH,
    check_node,
    connect_nodes_bi,
    sync_blocks,
)
from time import sleep

def check_stopped(i, timeout=10):
    stopped = False
    for x in range(1, timeout):
        ret = check_node(i)
        if ret is None:
            sleep(1)
        else:
            stopped = True
            break
    return stopped

class ReorgLimitTest(BitcoinTestFramework):

    def run_test(self):
        base = self.nodes[0].getblockcount()
        assert(self.nodes[2].getblockcount() == base)

        self.split_network()

        # A reorg of exactly MAX_REORG_LENGTH is the deepest the node accepts:
        # node 0 mines that many, node 2 mines one more and wins, so node 0
        # reorgs precisely at the limit.
        print("Test the maximum-allowed reorg:")
        print("Mine %d blocks on Node 0" % MAX_REORG_LENGTH)
        self.nodes[0].generate(MAX_REORG_LENGTH)
        assert(self.nodes[0].getblockcount() == base + MAX_REORG_LENGTH)
        assert(self.nodes[2].getblockcount() == base)

        print("Mine competing %d blocks on Node 2" % (MAX_REORG_LENGTH + 1))
        self.nodes[2].generate(MAX_REORG_LENGTH + 1)
        assert(self.nodes[0].getblockcount() == base + MAX_REORG_LENGTH)
        assert(self.nodes[2].getblockcount() == base + MAX_REORG_LENGTH + 1)

        print("Connect nodes to force a reorg")
        connect_nodes_bi(self.nodes, 0, 2)
        self.is_network_split = False
        sync_blocks(self.nodes)

        print("Check Node 0 is still running and on the correct chain")
        assert(self.nodes[0].getblockcount() == base + MAX_REORG_LENGTH + 1)

        self.split_network()

        # One deeper than the limit: this reorg must be refused.
        print("Test the minimum-rejected reorg:")
        print("Mine %d blocks on Node 0" % (MAX_REORG_LENGTH + 1))
        self.nodes[0].generate(MAX_REORG_LENGTH + 1)
        base2 = base + MAX_REORG_LENGTH + 1
        assert(self.nodes[0].getblockcount() == base2 + MAX_REORG_LENGTH + 1)
        assert(self.nodes[2].getblockcount() == base2)

        print("Mine competing %d blocks on Node 2" % (MAX_REORG_LENGTH + 2))
        self.nodes[2].generate(MAX_REORG_LENGTH + 2)
        assert(self.nodes[0].getblockcount() == base2 + MAX_REORG_LENGTH + 1)
        assert(self.nodes[2].getblockcount() == base2 + MAX_REORG_LENGTH + 2)

        print("Sync nodes to force a reorg")
        connect_nodes_bi(self.nodes, 0, 2)
        self.is_network_split = False
        # sync_blocks uses RPC calls to wait for nodes to be synced, so don't
        # call it here, because it will have a non-specific connection error
        # when Node 0 stops. Instead, we explicitly check for the process itself
        # to stop.

        print("Check Node 0 is no longer running")
        assert(check_stopped(0))

        # Dummy stop to enable the test to tear down
        self.nodes[0].stop = lambda: True

if __name__ == '__main__':
    ReorgLimitTest().main()
