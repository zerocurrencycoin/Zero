#!/usr/bin/env python3
# Copyright (c) 2018 The Zcash developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .
#
# Network upgrade peer checks on regtest with -nuparams (Overwinter 10, Sapling 15).
#
# Zero sets MIN_PEER_PROTO_VERSION=170007 and ties disconnects to the current epoch's
# nProtocolVersion (see main.cpp ProcessMessage). Peers below 170007 never connect; peers
# 170007/170008/170009 all satisfy Overwinter (170005) and Sapling (170007), so unlike
# upstream Zcash this test does not observe epoch-based mass disconnects for those
# versions. We still verify handshakes, mining past activations, new inbound peers, and
# reject for sub-minimum protocol (170006).


from test_framework.mininode import (
    NodeConn,
    NodeConnCB,
    NetworkThread,
    msg_ping,
)
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import initialize_chain_clean, start_nodes, \
    p2p_port, assert_equal

import time

# src/version.h
MIN_PEER_PROTO_VERSION = 170007

V_SPROUT = 170007
V_OVERWINTER = 170008
V_SAPLING = 170009
V_BELOW_MIN = 170006


class TestManager(NodeConnCB):
    def __init__(self):
        NodeConnCB.__init__(self)
        self.create_callback_map()

    def on_close(self, conn):
        pass

    def on_reject(self, conn, message):
        conn.rejectMessage = message


class NUPeerManagementTest(BitcoinTestFramework):

    def setup_chain(self):
        print("Initializing test directory "+self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 1)

    def setup_network(self):
        self.nodes = start_nodes(1, self.options.tmpdir, extra_args=[[
            '-nuparams=6f76727a:10',
            '-nuparams=7361707a:15',
            '-debug',
            '-whitelist=127.0.0.1',
        ]])

    def wait_for_peer_count(self, want, timeout=60.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            n = len(self.nodes[0].getpeerinfo())
            if n >= want:
                return n
            time.sleep(0.1)
        return len(self.nodes[0].getpeerinfo())

    def run_test(self):
        test = TestManager()

        nodes = []
        for _x in range(10):
            nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0],
                test, "regtest", V_SPROUT))
            nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0],
                test, "regtest", V_OVERWINTER))
            nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0],
                test, "regtest", V_SAPLING))

        NetworkThread().start()

        n = self.wait_for_peer_count(30)
        assert_equal(n, 30, "expected 30 mininode peers (check regtest pchMessageStart in mininode)")

        peerinfo = self.nodes[0].getpeerinfo()
        versions = [x["version"] for x in peerinfo]
        assert_equal(versions.count(V_SPROUT), 10)
        assert_equal(versions.count(V_OVERWINTER), 10)
        assert_equal(versions.count(V_SAPLING), 10)

        self.nodes[0].generate(9)
        assert_equal(9, self.nodes[0].getblockcount())
        assert_equal(len(self.nodes[0].getpeerinfo()), 30)

        self.nodes[0].generate(1)
        assert_equal(10, self.nodes[0].getblockcount())

        pingCounter = 1
        for node in nodes:
            node.send_message(msg_ping(pingCounter))
            pingCounter += 1
        time.sleep(2)

        peerinfo = self.nodes[0].getpeerinfo()
        versions = [x["version"] for x in peerinfo]
        # Zero: 170007 still >= Overwinter epoch requirement (170005); peers stay connected.
        assert_equal(versions.count(V_SPROUT), 10)
        assert_equal(versions.count(V_OVERWINTER), 10)
        assert_equal(versions.count(V_SAPLING), 10)

        self.nodes[0].generate(1)

        nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_OVERWINTER))
        time.sleep(3)
        assert_equal(len(self.nodes[0].getpeerinfo()), 31)

        nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_SAPLING))
        time.sleep(3)
        assert_equal(len(self.nodes[0].getpeerinfo()), 32)

        bad = NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_BELOW_MIN)
        nodes.append(bad)
        time.sleep(3)
        assert (
            ("Version must be %d or greater" % MIN_PEER_PROTO_VERSION) in str(bad.rejectMessage)
        )

        peerinfo = self.nodes[0].getpeerinfo()
        versions = [x["version"] for x in peerinfo]
        assert_equal(versions.count(V_SPROUT), 10)
        assert_equal(versions.count(V_OVERWINTER), 11)
        assert_equal(versions.count(V_SAPLING), 11)

        self.nodes[0].generate(4)
        assert_equal(15, self.nodes[0].getblockcount())

        pingCounter = 1
        for node in nodes:
            if getattr(node, 'state', '') != 'closed':
                try:
                    node.send_message(msg_ping(pingCounter))
                except Exception:
                    pass
                pingCounter += 1
        time.sleep(2)

        peerinfo = self.nodes[0].getpeerinfo()
        versions = [x["version"] for x in peerinfo]
        assert_equal(versions.count(V_SPROUT), 10)
        assert_equal(versions.count(V_OVERWINTER), 11)
        assert_equal(versions.count(V_SAPLING), 11)

        self.nodes[0].generate(1)

        nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_SAPLING))
        time.sleep(3)
        assert_equal(len(self.nodes[0].getpeerinfo()), 33)

        bad2 = NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_BELOW_MIN)
        nodes.append(bad2)
        time.sleep(3)
        assert (
            ("Version must be %d or greater" % MIN_PEER_PROTO_VERSION) in str(bad2.rejectMessage)
        )

        bad3 = NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_BELOW_MIN)
        nodes.append(bad3)
        time.sleep(3)
        assert (
            ("Version must be %d or greater" % MIN_PEER_PROTO_VERSION) in str(bad3.rejectMessage)
        )

        peerinfo = self.nodes[0].getpeerinfo()
        versions = [x["version"] for x in peerinfo]
        assert_equal(versions.count(V_SPROUT), 10)
        assert_equal(versions.count(V_OVERWINTER), 11)
        assert_equal(versions.count(V_SAPLING), 12)

        for node in nodes:
            try:
                node.disconnect_node()
            except Exception:
                pass


if __name__ == '__main__':
    NUPeerManagementTest().main()
