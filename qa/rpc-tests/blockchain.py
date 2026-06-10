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
)

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
        height = node.getblockcount()

        # The shared initialize_chain cache tip is COINBASE_MATURITY + 5 (see
        # TEST_ZERO.md), so derive the expected emission from the regtest
        # subsidy schedule instead of hardcoding totals at height 200.
        # Zero regtest: 10 ZER subsidy, halving every 150 blocks
        # (PRE_BLOSSOM_REGTEST_HALVING_INTERVAL; Blossom not active here),
        # no dev fee before block 5000. Mirror consensus integer math
        # (GetBlockSubsidy: 10*COIN >> floor(h/150)) in zatoshis.
        halving_interval = 150
        total_zats = sum((10 * 100000000) >> (h // halving_interval)
                         for h in range(1, height + 1))
        expected_total = decimal.Decimal(total_zats) / 100000000

        # e.g. height 200 -> 1745 ZER (149*10 + 51*5); height 725 -> 2881.25 ZER
        assert_equal(res[u'total_amount'], expected_total)
        assert_equal(res[u'transactions'], height)  # 1 coinbase tx per block
        assert_equal(res[u'height'], height)
        assert_equal(res[u'txouts'], height)  # 1 output per block (no dev fee before block 5000)
        assert res[u'bytes_serialized'] > 0
        assert_equal(len(res[u'bestblock']), 64)
        assert_equal(len(res[u'hash_serialized']), 64)


if __name__ == '__main__':
    BlockchainTest().main()
