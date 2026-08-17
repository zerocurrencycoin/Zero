#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.

"""TNT-12 Phase B: zeronode coinbase with default (off) sporks."""

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
    start_nodes,
)

REGTEST_FOUNDERS_ADDR = "t2FwcEhFdNXuFMv1tcYwaBJtYVtMj8b1uTg"


class ZeronodeCoinbaseTest(BitcoinTestFramework):

    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 2)

    def setup_network(self, split=False):
        extra = [['-debug', '-txindex']] * 2
        self.nodes = start_nodes(2, self.options.tmpdir, extra)
        connect_nodes_bi(self.nodes, 0, 1)
        self.is_network_split = False
        self.sync_all()

    def run_test(self):
        node = self.nodes[0]
        stats = node.zeronodestats()
        assert_equal(Decimal(stats['chainStats']['zeronodepayment']), Decimal(0))

        keys = node.createsporkkeys()
        assert 'pubkey' in keys and keys['pubkey']
        assert 'privkey' in keys and keys['privkey']

        # Unsigned update: regtest strSporkKey has no matching wallet key.
        assert_equal(node.spork('SPORK_7_ZERONODE_PAYMENT_ENABLED', 0), 'failure')

        mine_to_height(node, self.nodes, REGTEST_FOUNDERS_START)
        cb = node.getblock(node.getblockhash(REGTEST_FOUNDERS_START), 2)['tx'][0]
        # Sporks off: miner + founders only; no zeronode vout.
        assert_equal(len(cb['vout']), 2)
        assert_equal(Decimal(cb['vout'][0]['value']), miner_share(REGTEST_FOUNDERS_START))
        assert_equal(Decimal(cb['vout'][1]['value']), founders_share(REGTEST_FOUNDERS_START))
        assert_equal(cb['vout'][1]['scriptPubKey']['addresses'][0],
                     REGTEST_FOUNDERS_ADDR)
        stats = node.zeronodestats()
        assert_equal(Decimal(stats['chainStats']['zeronodepayment']), Decimal(0))


if __name__ == '__main__':
    ZeronodeCoinbaseTest().main()
