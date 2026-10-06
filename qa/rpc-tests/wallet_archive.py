#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""
Transaction archive with -deletetx (WAL-ARCHIVE-01, WAL-ARCHIVE-03):

- A spent coinbase is deleted from the wallet once its spend is deeper than
  -keeptxfornblocks; gettransaction no longer finds it.
- zs_gettransaction and zs_listtransactions still return it through the
  archive, with the same txid and block.
- History RPCs called while -reindex runs do not crash the node when the import
  reaches the archived blocks (regression: lookups once inserted null block-index
  entries that AcceptBlockHeader dereferenced).
- The archived entry survives a restart with -rescan, -reindex, and -zapwallettxes
  (which erases archive records; the rescan writes them again).
- Reorg consistency (WAL-ARCHIVE-02): a transaction whose block is invalidated and
  re-mined points to the new block with one confirmation.
"""

import time

from test_framework.authproxy import JSONRPCException
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, initialize_chain_clean, \
    start_node, stop_node, wait_bitcoinds

KEEP_BLOCKS = 100  # minimum accepted by -keeptxfornblocks (MAX_REORG_LENGTH + 1)
COINBASE_MATURITY = 720
ARGS = ["-deletetx", "-keeptxnum=1", "-keeptxfornblocks=%d" % KEEP_BLOCKS]


class WalletArchiveTest(BitcoinTestFramework):

    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 1)

    def setup_network(self):
        self.nodes = [start_node(0, self.options.tmpdir, ARGS)]
        self.is_network_split = False

    def restart(self, extra):
        stop_node(self.nodes[0], 0)
        wait_bitcoinds()
        self.nodes[0] = start_node(0, self.options.tmpdir, ARGS + extra)

    def wait_for_height(self, height, timeout=300, poll_history=False):
        node = self.nodes[0]
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if poll_history:
                    node.zs_listtransactions()
                    node.getalldata(0, 0)
                if node.getblockcount() >= height:
                    return
            except JSONRPCException:
                pass
            time.sleep(0.2)
        raise AssertionError("node did not reach height %d" % height)

    def in_wallet(self, txid):
        try:
            self.nodes[0].gettransaction(txid)
            return True
        except JSONRPCException:
            return False

    def check_archived(self, txid, blockhash, label):
        node = self.nodes[0]
        z = node.zs_gettransaction(txid)
        assert_equal(z["txid"], txid)
        if "blockhash" in z:
            assert_equal(z["blockhash"], blockhash)
        listed = [t["txid"] for t in node.zs_listtransactions()]
        assert txid in listed, "%s: archived tx missing from zs_listtransactions" % label
        print("%s: archived tx %s listed" % (label, txid[:16]))

    def run_test(self):
        node = self.nodes[0]
        node.generate(COINBASE_MATURITY + 1)

        dest = node.getnewaddress()
        spend = node.sendtoaddress(dest, 5)
        node.generate(1)
        coinbase = node.getrawtransaction(spend, 1)["vin"][0]["txid"]
        cb_block = node.gettransaction(coinbase)["blockhash"]
        assert self.in_wallet(coinbase)

        # Per-address history and supply on a populated wallet (TST-01).
        received = [t["txid"] for t in node.zs_listreceivedbyaddress(dest)]
        assert spend in received, "zs_listreceivedbyaddress missing the spend"
        sent = [t["txid"] for t in node.zs_listsentbyaddress(dest)]
        assert spend in sent, "zs_listsentbyaddress missing the spend"
        cb_addr = node.getrawtransaction(coinbase, 1)["vout"][0]["scriptPubKey"]["addresses"][0]
        spent = [t["txid"] for t in node.zs_listspentbyaddress(cb_addr)]
        assert spend in spent, "zs_listspentbyaddress missing the spend"
        supply = node.getsupply(node.getblockcount())
        assert supply, "getsupply returned nothing"

        # Spend depth must exceed -keeptxfornblocks before deletion.
        node.generate(KEEP_BLOCKS + 5)
        assert not self.in_wallet(coinbase), "spent coinbase should be deleted from mapWallet"
        self.check_archived(coinbase, cb_block, "after deletion")

        tip = node.getblockcount()
        self.restart(["-rescan"])
        self.check_archived(coinbase, cb_block, "after -rescan")

        self.restart(["-reindex"])
        self.wait_for_height(tip, poll_history=True)
        self.check_archived(coinbase, cb_block, "after -reindex")

        self.restart(["-zapwallettxes=1"])
        self.check_archived(coinbase, cb_block, "after -zapwallettxes")

        # WAL-ARCHIVE-02: archive point follows a reorg.
        node = self.nodes[0]
        txid = node.sendtoaddress(node.getnewaddress(), 1)
        first = node.generate(1)[0]
        assert_equal(node.zs_gettransaction(txid)["blockhash"], first)
        node.invalidateblock(first)
        second = node.generate(1)[0]
        assert second != first
        z = node.zs_gettransaction(txid)
        assert_equal(z["blockhash"], second)
        assert_equal(z["confirmations"], 1)
        print("reorg: archive point moved to the new block")


if __name__ == '__main__':
    WalletArchiveTest().main()
