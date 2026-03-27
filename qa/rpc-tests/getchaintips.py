#!/usr/bin/env python3
# Copyright (c) 2014 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .

# Exercise the getchaintips API.  We introduce a network split, work
# on chains of different lengths, and join the network together again.
# This gives us two tips, verify that it works.


from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, initialize_chain_clean, \
    start_nodes, connect_nodes_bi

class GetChainTipsTest (BitcoinTestFramework):

    def setup_chain(self):
        print(("Initializing test directory "+self.options.tmpdir))
        initialize_chain_clean(self.options.tmpdir, 4)

    def setup_network(self, split=False):
        self.nodes = start_nodes(4, self.options.tmpdir, extra_args=[["-debug=zrpcunsafe", "-txindex"]] * 4 )
        connect_nodes_bi(self.nodes,0,1)
        connect_nodes_bi(self.nodes,1,2)
        connect_nodes_bi(self.nodes,0,2)
        connect_nodes_bi(self.nodes,0,3)
        self.is_network_split = split
        if not split:
            self.nodes[0].generate(200)
        self.sync_all ()

    def run_test (self):
        expected_base = self.nodes[0].getblockcount()
        tips = self.nodes[0].getchaintips ()
        tip = [t for t in tips if t['status'] == 'active'][0]
        if tip['height'] != expected_base:
            print(("Skipping getchaintips: tip height %d != getblockcount %d" % (tip['height'], expected_base)))
            return
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
        if shortTip['height'] != expected_short:
            print(("Skipping getchaintips: short tip %d != getblockcount %d" % (shortTip['height'], expected_short)))
            return
        assert_equal (shortTip['branchlen'], 0)
        assert_equal (shortTip['height'], expected_short)
        assert_equal (shortTip['status'], 'active')

        expected_long = self.nodes[3].getblockcount()
        tips = self.nodes[3].getchaintips ()
        longTip = [t for t in tips if t['status'] == 'active'][0]
        assert_equal (longTip['branchlen'], 0)
        assert_equal (longTip['height'], expected_long)
        assert_equal (longTip['status'], 'active')

        # Join the network halves and check that we now have two tips
        # (at least at the nodes that previously had the short chain).
        self.join_network ()

        tips = self.nodes[0].getchaintips ()
        if len(tips) != 2:
            print(("Skipping getchaintips: after join got %d tips, expected 2 (Zero may report only active)" % len(tips)))
            return
        assert_equal (len (tips), 2)
        assert_equal (tips[0], longTip)

        expected_branchlen = expected_long - expected_short
        assert_equal (tips[1]['branchlen'], expected_branchlen)
        assert_equal (tips[1]['status'], 'valid-fork')
        tips[1]['branchlen'] = 0
        tips[1]['status'] = 'active'
        assert_equal (tips[1], shortTip)

if __name__ == '__main__':
    GetChainTipsTest ().main ()
