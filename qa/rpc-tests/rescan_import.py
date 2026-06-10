#!/usr/bin/env python3
# Copyright (c) 2025 The Zcash developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .

#
# P1: Test z_importkey with rescan=yes updates balance correctly
#


from decimal import Decimal
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
    get_coinbase_address,
    start_nodes,
    wait_and_assert_operationid_status,
)


class RescanImportTest(BitcoinTestFramework):

    def setup_nodes(self):
        return start_nodes(4, self.options.tmpdir, [[
            '-experimentalfeatures', '-zmergetoaddress',
        ]] * 4)

    def run_test(self):
        # Sanity-check the test harness
        assert_equal(self.nodes[0].getblockcount(), 200)

        taddr = get_coinbase_address(self.nodes[0])

        saplingAddr0 = self.nodes[0].z_getnewaddress('sapling')
        saplingAddr1 = self.nodes[1].z_getnewaddress('sapling')

        # Node 0 shields funds to saplingAddr0
        recipients = [{"address": saplingAddr0, "amount": Decimal('10')}]
        myopid = self.nodes[0].z_sendmany(taddr, recipients, 1, 0)
        wait_and_assert_operationid_status(self.nodes[0], myopid)

        self.sync_all()
        self.nodes[2].generate(1)
        self.sync_all()

        assert_equal(self.nodes[0].z_getbalance(saplingAddr0), Decimal('10'))
        assert_equal(self.nodes[1].z_getbalance(saplingAddr1), Decimal('0'))

        # Node 1 imports saplingAddr0's key with rescan=yes, should see balance
        sk0 = self.nodes[0].z_exportkey(saplingAddr0)
        self.nodes[1].z_importkey(sk0, "yes")
        assert_equal(self.nodes[1].z_getbalance(saplingAddr0), Decimal('10'))


if __name__ == '__main__':
    RescanImportTest().main()
