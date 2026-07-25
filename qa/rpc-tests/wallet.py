#!/usr/bin/env python3
# Copyright (c) 2014 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .


from test_framework.test_framework import BitcoinTestFramework
from test_framework.authproxy import JSONRPCException
from test_framework.util import assert_equal, assert_raises_message, \
    initialize_chain_clean, start_nodes, start_node, connect_nodes_bi, \
    stop_nodes, sync_blocks, sync_mempools, wait_and_assert_operationid_status, \
    wait_bitcoinds, miner_share, miner_range

from decimal import Decimal

class WalletTest (BitcoinTestFramework):

    def setup_chain(self):
        print(("Initializing test directory "+self.options.tmpdir))
        initialize_chain_clean(self.options.tmpdir, 4)

    def setup_network(self, split=False):
        self.nodes = start_nodes(3, self.options.tmpdir)
        connect_nodes_bi(self.nodes,0,1)
        connect_nodes_bi(self.nodes,1,2)
        connect_nodes_bi(self.nodes,0,2)
        self.is_network_split=False
        self.sync_all()

    def run_test (self):
        print("Mining blocks...")

        self.nodes[0].generate(4)

        walletinfo = self.nodes[0].getwalletinfo()
        assert_equal(walletinfo['immature_balance'], 40)
        assert_equal(walletinfo['balance'], 0)

        self.sync_all()
        self.nodes[1].generate(721)
        self.sync_all()
        self.nodes[1].generate(720)  # mature the 721 blocks (COINBASE_MATURITY=720)
        self.sync_all()

        # node1's 721 blocks are at chain heights 5..725 (after node0's 4); all < fee-start
        node1_subsidy = miner_range(5, 725)
        assert_equal(self.nodes[0].getbalance(), 40)
        assert_equal(self.nodes[1].getbalance(), node1_subsidy)
        assert_equal(self.nodes[2].getbalance(), 0)
        assert_equal(self.nodes[0].getbalance("*"), 40)
        assert_equal(self.nodes[1].getbalance("*"), node1_subsidy)
        assert_equal(self.nodes[2].getbalance("*"), 0)

        # Send 21 ZERO from 0 to 2 using sendtoaddress call.
        # Second transaction will be child of first, and will require a fee
        self.nodes[0].sendtoaddress(self.nodes[2].getnewaddress(), 11)
        self.nodes[0].sendtoaddress(self.nodes[2].getnewaddress(), 10)

        walletinfo = self.nodes[0].getwalletinfo()
        assert_equal(walletinfo['immature_balance'], 0)

        # Have node0 mine a block, thus it will collect its own fee.
        self.sync_all()
        self.nodes[0].generate(1)
        node0_cb_height = self.nodes[0].getblockcount()
        sync_blocks(self.nodes)  # Ensure node0's block is on all nodes before node1 builds

        # Have node1 generate 720 blocks (node0's coinbase needs COINBASE_MATURITY conf)
        self.nodes[1].generate(720)
        self.sync_all()

        # node0: heights 1..4 + its fee-collecting coinbase (may be in FR window).
        # Fees cancel: paid on send, returned when node0 mines that block.
        node0_expected = (
            miner_range(1, 4)
            + miner_share(node0_cb_height)
            - 21
        )
        node0_bal = self.nodes[0].getbalance()
        assert_equal(node0_bal, node0_expected)
        assert_equal(self.nodes[2].getbalance(), 21)
        assert_equal(self.nodes[0].getbalance("*"), node0_expected)
        assert_equal(self.nodes[2].getbalance("*"), 21)

        # Node0 should have three unspent outputs.
        # Create a couple of transactions to send them to node2, submit them through
        # node1, and make sure both node0 and node2 pick them up properly:
        node0utxos = self.nodes[0].listunspent(1)
        assert_equal(len(node0utxos), 3)

        # Check 'generated' field of listunspent
        # Node 0: has one coinbase utxo and two regular utxos
        assert_equal(sum(int(uxto["generated"] is True) for uxto in node0utxos), 1)
        # Node 1 mined 721+720+720 coinbases; listunspent omits immature
        # (need depth >= COINBASE_MATURITY+1). At tip 2166 that is 721+720=1441.
        node1utxos = self.nodes[1].listunspent(1)
        assert_equal(len(node1utxos), 1441)
        assert_equal(sum(int(uxto["generated"] is True) for uxto in node1utxos), 1441)
        # Node 2: has no coinbase utxos and two regular utxos
        node2utxos = self.nodes[2].listunspent(1)
        assert_equal(len(node2utxos), 2)
        assert_equal(sum(int(uxto["generated"] is True) for uxto in node2utxos), 0)

        # Catch an attempt to send a transaction with an absurdly high fee.
        # Send 1.0 from an utxo of value 10.0 but don't specify a change output, so then
        # the change of 9.0 becomes the fee, which is greater than estimated fee of 0.0021.
        inputs = []
        outputs = {}
        for utxo in node2utxos:
            if utxo["amount"] == Decimal("10.0"):
                break
        assert_equal(utxo["amount"], Decimal("10.0"))
        inputs.append({ "txid" : utxo["txid"], "vout" : utxo["vout"]})
        outputs[self.nodes[2].getnewaddress("")] = Decimal("1.0")
        raw_tx = self.nodes[2].createrawtransaction(inputs, outputs)
        signed_tx = self.nodes[2].signrawtransaction(raw_tx)
        try:
            self.nodes[2].sendrawtransaction(signed_tx["hex"])
        except JSONRPCException as e:
            errorString = e.error['message']
        assert("absurdly high fees" in errorString)
        assert("900000000 > 210000" in errorString)

        # create both transactions
        txns_to_send = []
        for utxo in node0utxos:
            inputs = []
            outputs = {}
            inputs.append({ "txid" : utxo["txid"], "vout" : utxo["vout"]})
            outputs[self.nodes[2].getnewaddress("")] = utxo["amount"]
            raw_tx = self.nodes[0].createrawtransaction(inputs, outputs)
            txns_to_send.append(self.nodes[0].signrawtransaction(raw_tx))

        # Have node 1 (miner) send the transactions
        self.nodes[1].sendrawtransaction(txns_to_send[0]["hex"], True)
        self.nodes[1].sendrawtransaction(txns_to_send[1]["hex"], True)
        self.nodes[1].sendrawtransaction(txns_to_send[2]["hex"], True)

        # Have node1 mine a block to confirm transactions:
        self.sync_all()
        self.nodes[1].generate(1)
        self.sync_all()

        # node2 receives all of node0's utxos (40 miner + tip coinbase - 21 already sent)
        node2_bal = Decimal(21) + node0_expected
        node0_bal = Decimal(0)
        assert_equal(self.nodes[0].getbalance(), node0_bal)
        assert_equal(self.nodes[2].getbalance(), node2_bal)
        assert_equal(self.nodes[0].getbalance("*"), node0_bal)
        assert_equal(self.nodes[2].getbalance("*"), node2_bal)

        # Send 10 ZERO normal
        address = self.nodes[0].getnewaddress("")
        fee = Decimal('0.001')
        self.nodes[2].settxfee(fee)
        self.nodes[2].sendtoaddress(address, 10, "", "", False)
        self.sync_all()
        self.nodes[2].generate(1)
        self.sync_all()
        node2_bal -= (Decimal(10) + fee)
        node0_bal = Decimal(10)
        assert_equal(self.nodes[2].getbalance(), node2_bal)
        assert_equal(self.nodes[0].getbalance(), node0_bal)
        assert_equal(self.nodes[2].getbalance("*"), node2_bal)
        assert_equal(self.nodes[0].getbalance("*"), node0_bal)

        # Send 10 with subtract fee from amount
        self.nodes[2].sendtoaddress(address, 10, "", "", True)
        self.sync_all()
        self.nodes[2].generate(1)
        self.sync_all()
        node2_bal -= Decimal(10)
        node0_bal += (Decimal(10) - fee)
        assert_equal(self.nodes[2].getbalance(), node2_bal)
        assert_equal(self.nodes[0].getbalance(), node0_bal)
        assert_equal(self.nodes[2].getbalance("*"), node2_bal)
        assert_equal(self.nodes[0].getbalance("*"), node0_bal)

        # Sendmany 10
        self.nodes[2].sendmany("", {address: 10}, 0, "", [])
        self.sync_all()
        self.nodes[2].generate(1)
        self.sync_all()
        node2_bal -= (Decimal(10) + fee)
        node0_bal += Decimal(10)
        assert_equal(self.nodes[2].getbalance(), node2_bal)
        assert_equal(self.nodes[0].getbalance(), node0_bal)
        assert_equal(self.nodes[2].getbalance("*"), node2_bal)
        assert_equal(self.nodes[0].getbalance("*"), node0_bal)

        # Sendmany 10 with subtract fee from amount
        self.nodes[2].sendmany("", {address: 10}, 0, "", [address])
        self.sync_all()
        self.nodes[2].generate(1)
        self.sync_all()
        node2_bal -= Decimal(10)
        node0_bal += (Decimal(10) - fee)
        assert_equal(self.nodes[2].getbalance(), node2_bal)
        assert_equal(self.nodes[0].getbalance(), node0_bal)
        assert_equal(self.nodes[2].getbalance("*"), node2_bal)
        assert_equal(self.nodes[0].getbalance("*"), node0_bal)

        # Test ResendWalletTransactions:
        # Create a couple of transactions, then start up a fourth
        # node (nodes[3]) and ask nodes[0] to rebroadcast.
        # EXPECT: nodes[3] should have those transactions in its mempool.
        txid1 = self.nodes[0].sendtoaddress(self.nodes[1].getnewaddress(), 1)
        txid2 = self.nodes[1].sendtoaddress(self.nodes[0].getnewaddress(), 1)
        sync_mempools(self.nodes)

        self.nodes.append(start_node(3, self.options.tmpdir))
        connect_nodes_bi(self.nodes, 0, 3)
        sync_blocks(self.nodes)

        relayed = self.nodes[0].resendwallettransactions()
        assert_equal(set(relayed), set([txid1, txid2]))
        sync_mempools(self.nodes)

        assert(txid1 in self.nodes[3].getrawmempool())

        #check if we can list zero value tx as available coins
        #1. create rawtx
        #2. hex-changed one output to 0.0
        #3. sign and send
        #4. check if recipient (node0) can list the zero value tx
        # Need a >=10 ZER input (early pre-halving coinbase); after hex-zero of 11.11,
        # only the 9.998 output remains for consensus.
        usp = [u for u in self.nodes[1].listunspent() if u['amount'] >= Decimal('10')]
        assert usp
        inputs = [{"txid":usp[0]['txid'], "vout":usp[0]['vout']}]
        outputs = {self.nodes[1].getnewaddress(): 9.998, self.nodes[0].getnewaddress(): 11.11}

        rawTx = self.nodes[1].createrawtransaction(inputs, outputs).replace("c0833842", "00000000") #replace 11.11 with 0.0 (int32)
        decRawTx = self.nodes[1].decoderawtransaction(rawTx)
        signedRawTx = self.nodes[1].signrawtransaction(rawTx)
        decRawTx = self.nodes[1].decoderawtransaction(signedRawTx['hex'])
        zeroValueTxid= decRawTx['txid']
        self.nodes[1].sendrawtransaction(signedRawTx['hex'])

        self.sync_all()
        self.nodes[1].generate(1) #mine a block
        self.sync_all()

        unspentTxs = self.nodes[0].listunspent() #zero value tx must be in listunspents output
        found = False
        for uTx in unspentTxs:
            if uTx['txid'] == zeroValueTxid:
                found = True
                assert_equal(uTx['amount'], Decimal('0.00000000'))
        assert(found)

        #do some -walletbroadcast tests
        stop_nodes(self.nodes)
        wait_bitcoinds()
        self.nodes = start_nodes(3, self.options.tmpdir, [["-walletbroadcast=0"],["-walletbroadcast=0"],["-walletbroadcast=0"]])
        connect_nodes_bi(self.nodes,0,1)
        connect_nodes_bi(self.nodes,1,2)
        connect_nodes_bi(self.nodes,0,2)
        self.sync_all()

        txIdNotBroadcasted  = self.nodes[0].sendtoaddress(self.nodes[2].getnewaddress(), 2)
        txObjNotBroadcasted = self.nodes[0].gettransaction(txIdNotBroadcasted)
        self.sync_all()
        self.nodes[1].generate(1) #mine a block, tx should not be in there
        self.sync_all()
        assert_equal(self.nodes[2].getbalance(), node2_bal) #should not be changed because tx was not broadcasted
        assert_equal(self.nodes[2].getbalance("*"), node2_bal) #should not be changed because tx was not broadcasted

        #now broadcast from another node, mine a block, sync, and check the balance
        self.nodes[1].sendrawtransaction(txObjNotBroadcasted['hex'])
        self.sync_all()
        self.nodes[1].generate(1)
        self.sync_all()
        txObjNotBroadcasted = self.nodes[0].gettransaction(txIdNotBroadcasted)
        node2_bal += Decimal(2)
        assert_equal(self.nodes[2].getbalance(), node2_bal)
        assert_equal(self.nodes[2].getbalance("*"), node2_bal)

        #create another tx
        txIdNotBroadcasted  = self.nodes[0].sendtoaddress(self.nodes[2].getnewaddress(), 2)

        #restart the nodes with -walletbroadcast=1
        stop_nodes(self.nodes)
        wait_bitcoinds()
        self.nodes = start_nodes(3, self.options.tmpdir)
        connect_nodes_bi(self.nodes,0,1)
        connect_nodes_bi(self.nodes,1,2)
        connect_nodes_bi(self.nodes,0,2)
        sync_blocks(self.nodes)

        self.nodes[0].generate(1)
        sync_blocks(self.nodes)

        #tx should be added to balance because after restarting the nodes tx should be broadcastet
        node2_bal += Decimal(2)
        assert_equal(self.nodes[2].getbalance(), node2_bal)
        assert_equal(self.nodes[2].getbalance("*"), node2_bal)

        # send from node 0 to node 2 taddr
        mytaddr = self.nodes[2].getnewaddress()
        mytxid = self.nodes[0].sendtoaddress(mytaddr, 10.0)
        self.sync_all()
        self.nodes[0].generate(1)
        self.sync_all()

        mybalance = self.nodes[2].z_getbalance(mytaddr)
        assert_equal(mybalance, Decimal('10.0'))

        mytxdetails = self.nodes[2].gettransaction(mytxid)
        myvjoinsplits = mytxdetails["vjoinsplit"]
        assert_equal(0, len(myvjoinsplits))

        # Sapling: taddr -> zaddr, then zaddr -> taddrs (replaces Sprout joinsplit path)
        myzaddr = self.nodes[2].z_getnewaddress('sapling')
        recipients = [{"address": myzaddr, "amount": 7}]
        wait_and_assert_operationid_status(
            self.nodes[2], self.nodes[2].z_sendmany(mytaddr, recipients))

        self.sync_all()
        self.nodes[2].generate(1)
        self.sync_all()

        zsendmanynotevalue = Decimal('7.0')
        zsendmanyfee = Decimal('0.0001')
        node2_bal += Decimal(10)  # received on mytaddr earlier
        node2utxobalance = node2_bal - zsendmanynotevalue - zsendmanyfee

        assert_equal(self.nodes[2].getbalance(), node2utxobalance)
        assert_equal(self.nodes[2].getbalance("*"), node2utxobalance)
        assert_equal(self.nodes[2].z_getbalance(myzaddr), zsendmanynotevalue)

        resp = self.nodes[2].z_gettotalbalance()
        assert_equal(Decimal(resp["transparent"]), node2utxobalance)
        assert_equal(Decimal(resp["private"]), zsendmanynotevalue)
        assert_equal(Decimal(resp["total"]), node2utxobalance + zsendmanynotevalue)

        node0balance = self.nodes[0].getbalance()
        node2balance = self.nodes[2].getbalance()
        recipients = [
            {"address": self.nodes[0].getnewaddress(), "amount": 1},
            {"address": self.nodes[2].getnewaddress(), "amount": 1.0},
        ]
        wait_and_assert_operationid_status(
            self.nodes[2], self.nodes[2].z_sendmany(myzaddr, recipients))

        self.sync_all()
        self.nodes[2].generate(1)
        self.sync_all()

        node0balance += Decimal('1.0')
        node2balance += Decimal('1.0')
        assert_equal(Decimal(self.nodes[0].getbalance()), node0balance)
        assert_equal(Decimal(self.nodes[0].getbalance("*")), node0balance)
        assert_equal(Decimal(self.nodes[2].getbalance()), node2balance)
        assert_equal(Decimal(self.nodes[2].getbalance("*")), node2balance)

        # sendtoaddress amount parsing
        txId = self.nodes[0].sendtoaddress(self.nodes[2].getnewaddress(), "2")
        assert_equal(self.nodes[0].gettransaction(txId)['amount'], Decimal('-2.00000000'))
        txId = self.nodes[0].sendtoaddress(self.nodes[2].getnewaddress(), "0.0001")
        assert_equal(self.nodes[0].gettransaction(txId)['amount'], Decimal('-0.00010000'))
        txId = self.nodes[0].sendtoaddress(self.nodes[2].getnewaddress(), "1e-4")
        assert_equal(self.nodes[0].gettransaction(txId)['amount'], Decimal('-0.00010000'))
        assert_raises_message(
            JSONRPCException, "Invalid amount",
            self.nodes[0].sendtoaddress, self.nodes[2].getnewaddress(), "1f-4")
        assert_raises_message(
            JSONRPCException, "not an integer",
            self.nodes[0].generate, "2")

        # Sapling amount=0 / fee edge cases
        myzaddr = self.nodes[0].z_getnewaddress('sapling')
        recipients = [{"address": myzaddr, "amount": Decimal('0.0')}]
        assert self.nodes[0].z_sendmany(myzaddr, recipients)

        assert_raises_message(
            JSONRPCException, "Small transaction amount",
            self.nodes[0].z_sendmany, myzaddr, recipients, 1, Decimal('0.1'))

        recipients = [{"address": myzaddr, "amount": Decimal('0.00000001')}]
        assert self.nodes[0].z_sendmany(myzaddr, recipients, 1, Decimal('0.0000001'))

        recipients = [{"address": myzaddr, "amount": Decimal('0.0')}]
        assert self.nodes[0].z_sendmany(myzaddr, recipients, 1, Decimal('0.0'))


if __name__ == '__main__':
    WalletTest ().main ()
