#!/usr/bin/env python3
# Copyright (c) 2014 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .

#
# Test RPC calls related to blockchain state. Tests correspond to code in
# rpc/blockchain.cpp.
#


import decimal

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    initialize_chain,
    assert_equal,
    start_nodes,
    connect_nodes_bi,
    COINBASE_MATURITY,
    REGTEST_FOUNDERS_START,
    subsidy_range,
)

# initialize_chain mines to COINBASE_MATURITY + 5 after the 200-block distribution.
CACHE_CHAIN_TIP = COINBASE_MATURITY + 5


class BlockchainTest(BitcoinTestFramework):
    """gettxoutsetinfo against warm-cache tip."""

    def setup_chain(self):
        print(("Initializing test directory " + self.options.tmpdir))
        initialize_chain(self.options.tmpdir)

    def setup_network(self, split=False):
        self.nodes = start_nodes(2, self.options.tmpdir)
        connect_nodes_bi(self.nodes, 0, 1)
        self.is_network_split = False
        self.sync_all()

    def run_test(self):
        node = self.nodes[0]
        res = node.gettxoutsetinfo()

        assert CACHE_CHAIN_TIP < REGTEST_FOUNDERS_START
        assert_equal(res[u'height'], CACHE_CHAIN_TIP)
        assert_equal(res[u'transactions'], CACHE_CHAIN_TIP)
        # Below founders START: one miner output per coinbase
        assert_equal(res[u'txouts'], CACHE_CHAIN_TIP)
        assert_equal(
            res[u'total_amount'],
            subsidy_range(1, CACHE_CHAIN_TIP).quantize(decimal.Decimal('0.00000001')),
        )
        assert res[u'bytes_serialized'] > 0
        assert_equal(len(res[u'bestblock']), 64)
        assert_equal(len(res[u'hash_serialized']), 64)


if __name__ == '__main__':
    BlockchainTest().main()
