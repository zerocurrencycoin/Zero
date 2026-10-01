#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""
Block pruning is disabled in Zero (the -prune option and its checks are commented
out in init.cpp; txindex is always on). This test pins that contract:

- -prune=550 is accepted and ignored: getblockchaininfo reports pruned=false and
  no pruneheight.
- Every block stays readable, including after -reindex with -prune set (the
  prune-and-reindex path that deletes block files must not run).
- The pruneblockchain RPC does not exist.

If pruning is restored, replace this test.
"""

from test_framework.authproxy import JSONRPCException
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, initialize_chain_clean, \
    start_node, stop_node, wait_bitcoinds

BLOCKS = 200
PRUNE_ARGS = ["-prune=550"]


class PruningDisabledTest(BitcoinTestFramework):

    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 1)

    def setup_network(self):
        self.nodes = [start_node(0, self.options.tmpdir, PRUNE_ARGS)]
        self.is_network_split = False

    def check_not_pruned(self, node, height):
        info = node.getblockchaininfo()
        assert_equal(info["pruned"], False)
        assert "pruneheight" not in info
        assert_equal(node.getblockcount(), height)
        for h in (1, height // 2, height):
            block = node.getblock(node.getblockhash(h))
            assert_equal(block["height"], h)

    def run_test(self):
        node = self.nodes[0]
        node.generate(BLOCKS)
        self.check_not_pruned(node, BLOCKS)

        try:
            node.pruneblockchain(1)
            raise AssertionError("pruneblockchain should not exist")
        except JSONRPCException as e:
            assert_equal(e.error["code"], -32601)

        stop_node(node, 0)
        wait_bitcoinds()
        self.nodes[0] = start_node(0, self.options.tmpdir, PRUNE_ARGS + ["-reindex"])
        self.check_not_pruned(self.nodes[0], BLOCKS)


if __name__ == '__main__':
    PruningDisabledTest().main()
