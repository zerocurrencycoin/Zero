#!/usr/bin/env python3
# Copyright (c) 2014 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .

#
# Test spending coinbase transactions.
# The coinbase transaction in block N can appear in block
# N+COINBASE_MATURITY (720 on Zero)... so is valid in the mempool
# when the best block height is N+COINBASE_MATURITY-1.
# This test makes sure coinbase spends that will be mature
# in the next block are accepted into the memory pool,
# but less mature coinbase spends are NOT.
#
# Uses the shared initialize_chain cache (tip = COINBASE_MATURITY + 5),
# so the spendable-boundary coinbases are in node 0's first mining round.
#

from decimal import Decimal

from test_framework.test_framework import BitcoinTestFramework
from test_framework.authproxy import JSONRPCException
from test_framework.util import assert_equal, assert_greater_than, assert_raises, \
    start_node, COINBASE_MATURITY


# Create one-input, one-output, no-fee transaction:
class MempoolSpendCoinbaseTest(BitcoinTestFramework):

    def setup_network(self):
        # Just need one node for this test
        args = ["-checkmempool", "-debug=mempool"]
        self.nodes = []
        self.nodes.append(start_node(0, self.options.tmpdir, args))
        self.is_network_split = False

    def create_tx(self, from_txid, to_address, amount):
        inputs = [{ "txid" : from_txid, "vout" : 0}]
        outputs = { to_address : amount }
        rawtx = self.nodes[0].createrawtransaction(inputs, outputs)
        signresult = self.nodes[0].signrawtransaction(rawtx)
        assert_equal(signresult["complete"], True)
        return signresult["hex"]

    def run_test(self):
        chain_height = self.nodes[0].getblockcount()
        # initialize_chain cache extends to COINBASE_MATURITY + 5 (see TEST_ZERO.md)
        assert_greater_than(chain_height, COINBASE_MATURITY)
        node0_address = self.nodes[0].getnewaddress()

        # Coinbase at height chain_height-COINBASE_MATURITY+1 ok in mempool,
        # should get mined. Coinbase at height chain_height-COINBASE_MATURITY+2
        # is too immature to spend.
        spendable_height = chain_height - COINBASE_MATURITY + 1
        b = [ self.nodes[0].getblockhash(n) for n in range(spendable_height, spendable_height + 2) ]
        coinbase_txids = [ self.nodes[0].getblock(h)['tx'][0] for h in b ]
        # Regtest subsidy is below the upstream 50; spend the actual coinbase
        # value minus a small fee instead of a hardcoded 10.
        coinbase_values = [ self.nodes[0].gettxout(txid, 0)['value'] for txid in coinbase_txids ]
        spends_raw = [ self.create_tx(txid, node0_address, value - Decimal("0.0001"))
                       for (txid, value) in zip(coinbase_txids, coinbase_values) ]

        spend_mature_id = self.nodes[0].sendrawtransaction(spends_raw[0])

        # coinbase at the next height should be too immature to spend
        assert_raises(JSONRPCException, self.nodes[0].sendrawtransaction, spends_raw[1])

        # mempool should have just the mature spend:
        mempoolinfo = self.nodes[0].getmempoolinfo()
        assert_equal(mempoolinfo['size'], 1)
        assert_equal(self.nodes[0].getrawmempool(), [ spend_mature_id ])

        # the size of the memory pool should be greater than 1x ~100 bytes
        assert_greater_than(mempoolinfo['bytes'], 100)
        # the actual memory usage should be strictly greater than the size
        # of the memory pool
        assert_greater_than(mempoolinfo['usage'], mempoolinfo['bytes'])

        # mine a block, the mature spend should get confirmed
        self.nodes[0].generate(1)
        mempoolinfo = self.nodes[0].getmempoolinfo()
        assert_equal(mempoolinfo['size'], 0)
        assert_equal(mempoolinfo['bytes'], 0)
        assert_equal(mempoolinfo['usage'], 0)
        assert_equal(set(self.nodes[0].getrawmempool()), set())

        # ... and now the next coinbase can be spent:
        spend_next_id = self.nodes[0].sendrawtransaction(spends_raw[1])
        mempoolinfo = self.nodes[0].getmempoolinfo()
        assert_equal(mempoolinfo['size'], 1)
        assert_equal(self.nodes[0].getrawmempool(), [ spend_next_id ])
        assert_greater_than(mempoolinfo['bytes'], 100)
        assert_greater_than(mempoolinfo['usage'], mempoolinfo['bytes'])

if __name__ == '__main__':
    MempoolSpendCoinbaseTest().main()
