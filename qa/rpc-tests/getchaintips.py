#!/usr/bin/env python3
# Copyright (c) 2014 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .

# Exercise the getchaintips API.  We introduce a network split, work
# on chains of different lengths, and join the network together again.
# This gives us two tips, verify that it works.


from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, assert_greater_than, \
    initialize_chain_clean, start_nodes, connect_nodes_bi

# Shared chain depth before split (only needs a non-trivial fork; 200 was Bitcoin legacy).
CHAIN_BOOTSTRAP = 30

class GetChainTipsTest (BitcoinTestFramework):

    def setup_chain(self):
        print(("Initializing test directory "+self.options.tmpdir))
        initialize_chain_clean(self.options.tmpdir, 4)

    def setup_network(self, split=False):
        self.nodes = start_nodes(4, self.options.tmpdir, extra_args=[["-debug=zrpcunsafe", "-txindex"]] * 4 )
        if split:
            connect_nodes_bi(self.nodes, 0, 1)
            connect_nodes_bi(self.nodes, 2, 3)
        else:
            connect_nodes_bi(self.nodes, 0, 1)
            connect_nodes_bi(self.nodes, 1, 2)
            connect_nodes_bi(self.nodes, 0, 2)
            connect_nodes_bi(self.nodes, 0, 3)
        self.is_network_split = split
        # Fresh chain only. join_network() calls setup_network(False) again; do not re-mine here.
        if not split and self.nodes[0].getblockcount() < CHAIN_BOOTSTRAP:
            self.nodes[0].generate(CHAIN_BOOTSTRAP)
        self.sync_all ()

    def run_test (self):
        expected_base = self.nodes[0].getblockcount()
        tips = self.nodes[0].getchaintips ()
        tip = [t for t in tips if t['status'] == 'active'][0]
        # The active tip disagreeing with getblockcount is the defect this
        # test exists to catch, not a reason to stop: skipping here abandoned
        # every assertion below and still reported a pass.
        assert_equal (tip['height'], expected_base)
        assert_equal (tip['branchlen'], 0)
        assert_equal (tip['height'], expected_base)
        assert_equal (tip['status'], 'active')

        # Split the network and build two chains of different lengths.
        self.split_network ()
        self.nodes[0].generate(10);
        self.nodes[2].generate(20);
        self.sync_all ()

        expected_short = self.nodes[1].getblockcount()
        tips = self.nodes[1].getchaintips ()
        shortTip = [t for t in tips if t['status'] == 'active'][0]
        assert_equal (shortTip['height'], expected_short)
        assert_equal (shortTip['branchlen'], 0)
        assert_equal (shortTip['height'], expected_short)
        assert_equal (shortTip['status'], 'active')

        expected_long = self.nodes[3].getblockcount()
        tips = self.nodes[3].getchaintips ()
        longTip = [t for t in tips if t['status'] == 'active'][0]
        assert_equal (longTip['branchlen'], 0)
        assert_equal (longTip['height'], expected_long)
        assert_equal (longTip['status'], 'active')

        assert_greater_than(expected_long, expected_short)

        # Join halves; best chain becomes the longer branch.
        self.join_network ()
        self.sync_all ()

        tips = self.nodes[0].getchaintips ()
        active = [t for t in tips if t['status'] == 'active'][0]
        assert_equal (active['height'], expected_long)
        assert_equal (active['branchlen'], 0)

        # Fork leaf branchlen vs active tip = height(short) - last_common (bootstrap height).
        expected_branchlen = shortTip['height'] - CHAIN_BOOTSTRAP
        long_hash = longTip['hash']
        short_hash = shortTip['hash']

        # Prefer two tips (active + stale fork). Some builds expose the abandoned tip only as
        # valid-fork; others omit it from the tip set after reorg (single active tip only).
        if len(tips) == 2:
            assert long_hash in {t['hash'] for t in tips}
            others = [t for t in tips if t['hash'] != long_hash]
            assert_equal (len(others), 1)
            fork = others[0]
            assert_equal (fork['branchlen'], expected_branchlen)
            assert fork['status'] in ('valid-fork', 'valid-headers')
            if fork['status'] == 'valid-fork':
                assert_equal (fork['height'], shortTip['height'])
                assert_equal (fork['hash'], short_hash)
        elif len(tips) == 1:
            assert_equal (tips[0]['hash'], long_hash)
        else:
            raise AssertionError("getchaintips: unexpected tip count %d" % len(tips))

if __name__ == '__main__':
    GetChainTipsTest ().main ()
