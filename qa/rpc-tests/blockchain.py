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
)

# Regtest halving interval (consensus/params.h PRE_BLOSSOM_REGTEST_HALVING_INTERVAL).
REGTEST_HALVING_INTERVAL = 150

# initialize_chain mines to COINBASE_MATURITY + 5 after the 200-block distribution.
CACHE_CHAIN_TIP = COINBASE_MATURITY + 5


def regtest_supply_at_height(height):
    """Coinbase subsidy sum for regtest heights 1..height (no founder before block 5000)."""
    total_sat = 0
    for h in range(1, height + 1):
        halvings = h // REGTEST_HALVING_INTERVAL
        total_sat += (10 * 100000000) >> halvings
    return decimal.Decimal(total_sat) / decimal.Decimal(100000000)


class BlockchainTest(BitcoinTestFramework):
    """
    Test blockchain-related RPC calls:

        - gettxoutsetinfo

    """

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

        # Warm cache tip (COINBASE_MATURITY + 5): regtest 10 ZER base, halving every 150 blocks.
        assert_equal(res[u'height'], CACHE_CHAIN_TIP)
        assert_equal(res[u'transactions'], CACHE_CHAIN_TIP)
        assert_equal(res[u'txouts'], CACHE_CHAIN_TIP)  # 1 output per block (no founder before block 5000)
        assert_equal(
            res[u'total_amount'],
            regtest_supply_at_height(CACHE_CHAIN_TIP).quantize(decimal.Decimal('0.00000001')),
        )
        assert res[u'bytes_serialized'] > 0
        assert_equal(len(res[u'bestblock']), 64)
        assert_equal(len(res[u'hash_serialized']), 64)


if __name__ == '__main__':
    BlockchainTest().main()
