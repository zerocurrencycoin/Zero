#!/usr/bin/env python3
# Copyright (c) 2014-2015 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

#
# Test txindex generation and fetching
#
# Harness: Bfail Debug (rpc-tests.sh).
# Zero: coinbase is 10 ZER, not Bitcoin's 50; assertions below use the
# node's own reported amount rather than a hardcoded subsidy.
#

import time
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *
from test_framework.script import *
from test_framework.mininode import *
import binascii

class TxIndexTest(BitcoinTestFramework):

    def setup_chain(self):
        print(("Initializing test directory "+self.options.tmpdir))
        initialize_chain_clean(self.options.tmpdir, 4)

    def setup_network(self):
        self.nodes = []
        # Nodes 0/1 are "wallet" nodes
        self.nodes.append(start_node(0, self.options.tmpdir, ["-debug"]))
        self.nodes.append(start_node(1, self.options.tmpdir, ["-debug", "-txindex"]))
        # Nodes 2/3 are used for testing
        self.nodes.append(start_node(2, self.options.tmpdir, ["-debug", "-txindex"]))
        self.nodes.append(start_node(3, self.options.tmpdir, ["-debug", "-txindex"]))
        connect_nodes(self.nodes[0], 1)
        connect_nodes(self.nodes[0], 2)
        connect_nodes(self.nodes[0], 3)

        self.is_network_split = False
        self.sync_all()

    def run_test(self):
        print("Mining blocks...")
        mature_tip = mature_height(5)
        self.nodes[0].generate(mature_tip)
        self.sync_all()

        chain_height = self.nodes[1].getblockcount()
        assert_equal(chain_height, mature_tip)

        print("Testing transaction index...")

        privkey = "cSdkPxkAjA4HDr5VHgsebAPDEh9Gyub4HK8UJr2DFGGqKKy4K5sG"
        address = "mgY65WSfEmsyYaYPQaXhmXMeBhwp4EcsQW"
        addressHash = binascii.unhexlify("0b2f0a0c31bfe0406b0ccc1381fdbe311946dadc")
        scriptPubKey = CScript([OP_DUP, OP_HASH160, addressHash, OP_EQUALVERIFY, OP_CHECKSIG])
        unspent = self.nodes[0].listunspent()
        tx = CTransaction()
        # listunspent returns amounts as Decimal, and Decimal * int stays
        # Decimal, which struct.pack("<q", ...) rejects. Under Python 2 this
        # was a float and packed by coercion. Convert explicitly, as the
        # passing tests do with `int * COIN` (addressindex.py).
        amount = int(unspent[0]["amount"] * COIN)
        tx.vin = [CTxIn(COutPoint(int(unspent[0]["txid"], 16), unspent[0]["vout"]))]
        tx.vout = [CTxOut(amount, scriptPubKey)]
        tx.rehash()

        signed_tx = self.nodes[0].signrawtransaction(binascii.hexlify(tx.serialize()).decode("utf-8"))
        txid = self.nodes[0].sendrawtransaction(signed_tx["hex"], True)
        self.nodes[0].generate(1)
        self.sync_all()

        # Check verbose raw transaction results
        verbose = self.nodes[3].getrawtransaction(unspent[0]["txid"], 1)
        # Assert against the amount the node reported for this very output,
        # not a hardcoded subsidy: upstream's 50 is Bitcoin's, and Zero's is
        # 10. Pinning the literal makes the test track the subsidy schedule
        # rather than the txindex behaviour it exists to check.
        expected_zat = int(unspent[0]["amount"] * COIN)
        assert_equal(verbose["vout"][unspent[0]["vout"]]["valueZat"], expected_zat)
        assert_equal(verbose["vout"][unspent[0]["vout"]]["value"], unspent[0]["amount"])

        print("Passed\n")


if __name__ == '__main__':
    TxIndexTest().main()
