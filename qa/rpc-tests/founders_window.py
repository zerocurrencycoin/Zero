#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.

"""Regtest founders window: [REGTEST_FOUNDERS_START, STOP) + Insight index."""

from decimal import Decimal

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
    connect_nodes_bi,
    founders_share,
    initialize_chain_clean,
    mine_to_height,
    miner_share,
    REGTEST_FOUNDERS_START,
    REGTEST_FOUNDERS_STOP,
    start_nodes,
)

# Single regtest founders payee (chainparams.cpp vFoundersRewardAddress).
REGTEST_FOUNDERS_ADDR = "t2FwcEhFdNXuFMv1tcYwaBJtYVtMj8b1uTg"
INSIGHT_ARGS = [
    '-debug', '-txindex', '-experimentalfeatures', '-insightexplorer',
]
COIN = 100000000


class FoundersWindowTest(BitcoinTestFramework):

    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 2)

    def setup_network(self, split=False):
        self.nodes = start_nodes(2, self.options.tmpdir, [INSIGHT_ARGS] * 2)
        connect_nodes_bi(self.nodes, 0, 1)
        self.is_network_split = False
        self.sync_all()

    def check_height(self, height, active):
        """getblocksubsidy + coinbase vouts at height; active => founders on."""
        node = self.nodes[0]
        sub = node.getblocksubsidy(height)
        share = founders_share(height)
        miner = miner_share(height)
        assert_equal(Decimal(sub['founders']), share)
        assert_equal(Decimal(sub['miner']), miner)
        assert_equal(share > 0, active)

        cb = node.getblock(node.getblockhash(height), 2)['tx'][0]
        if active:
            assert_equal(len(cb['vout']), 2)
            assert_equal(Decimal(cb['vout'][0]['value']), miner)
            assert_equal(Decimal(cb['vout'][1]['value']), share)
            assert_equal(cb['vout'][1]['scriptPubKey']['addresses'][0],
                         REGTEST_FOUNDERS_ADDR)
        else:
            assert_equal(len(cb['vout']), 1)
            assert_equal(Decimal(cb['vout'][0]['value']), miner)

    def run_test(self):
        start = REGTEST_FOUNDERS_START
        stop = REGTEST_FOUNDERS_STOP
        node = self.nodes[0]
        peer = self.nodes[1]

        mine_to_height(node, self.nodes, start - 1)
        self.check_height(start - 1, False)
        bal = peer.getaddressbalance(REGTEST_FOUNDERS_ADDR)
        assert_equal(bal['balance'], 0)

        mine_to_height(node, self.nodes, start)
        self.check_height(start, True)
        tmpl = node.getblocktemplate()
        assert_equal(int(tmpl['coinbasetxn']['foundersreward']),
                     int(founders_share(start + 1) * COIN))
        # Insight: founders payee indexed at START
        bal = peer.getaddressbalance(REGTEST_FOUNDERS_ADDR)
        assert_equal(bal['balance'], int(founders_share(start) * COIN))
        assert_equal(bal['received'], int(founders_share(start) * COIN))
        assert_equal(len(peer.getaddresstxids(REGTEST_FOUNDERS_ADDR)), 1)

        mine_to_height(node, self.nodes, stop - 1)
        self.check_height(stop - 1, True)

        mine_to_height(node, self.nodes, stop)
        self.check_height(stop, False)
        assert 'foundersreward' not in node.getblocktemplate()['coinbasetxn']
        # Cumulative founders through last FR height (stop - 1)
        expected = 0
        for h in range(start, stop):
            expected += int(founders_share(h) * COIN)
        bal = peer.getaddressbalance(REGTEST_FOUNDERS_ADDR)
        assert_equal(bal['balance'], expected)
        assert_equal(bal['received'], expected)
        assert_equal(len(peer.getaddresstxids(REGTEST_FOUNDERS_ADDR)), stop - start)


if __name__ == '__main__':
    FoundersWindowTest().main()
