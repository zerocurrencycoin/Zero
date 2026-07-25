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
    disconnect_mininode_connections,
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

# Inbound mininode budget (4 of each protocol version = 12). Enough to exercise
# handshake mix / NU mining / reject without a 30-SYN burst on Linux.
N_SPROUT = 4
N_OVERWINTER = 4
N_SAPLING = 4
N_INITIAL = N_SPROUT + N_OVERWINTER + N_SAPLING  # 12


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

    def wait_for_reject(self, conn, substr, timeout=15.0):
        """Wait until mininode on_reject has populated conn.rejectMessage."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            msg = getattr(conn, 'rejectMessage', None)
            if msg is not None and substr in str(msg):
                return msg
            time.sleep(0.05)
        raise AssertionError(
            "reject timeout: want substring %r, got %r"
            % (substr, getattr(conn, 'rejectMessage', None))
        )

    def wait_for_version_counts(self, want_sprout, want_ow, want_sap, timeout=90.0):
        """Wait until getpeerinfo version tallies match (handshake complete)."""
        t0 = time.time()
        last = (0, 0, 0, 0)
        while time.time() - t0 < timeout:
            peerinfo = self.nodes[0].getpeerinfo()
            versions = [x["version"] for x in peerinfo]
            last = (
                len(peerinfo),
                versions.count(V_SPROUT),
                versions.count(V_OVERWINTER),
                versions.count(V_SAPLING),
            )
            if (last[1] >= want_sprout and last[2] >= want_ow and last[3] >= want_sap
                    and last[0] >= want_sprout + want_ow + want_sap):
                return versions
            time.sleep(0.2)
        raise AssertionError(
            "peer version timeout: total=%d sprout=%d overwinter=%d sapling=%d "
            "(want %d/%d/%d); check accept backlog / mininode pchMessageStart"
            % (last[0], last[1], last[2], last[3], want_sprout, want_ow, want_sap)
        )

    def _connect_peers(self, test, nodes):
        """Stagger inbound mininode connects so Linux accept() backlog keeps up."""
        counts = (N_SPROUT, N_OVERWINTER, N_SAPLING)
        versions = (V_SPROUT, V_OVERWINTER, V_SAPLING)
        # Round-robin by version so one version does not monopolize early slots.
        for i in range(max(counts)):
            for n_want, ver in zip(counts, versions):
                if i < n_want:
                    nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0],
                                          test, "regtest", ver))
            time.sleep(0.05)

    def run_test(self):
        test = TestManager()
        nodes = []
        # Register sockets first; NetworkThread must start after connects
        # (starting earlier left getpeerinfo empty on macOS).
        self._connect_peers(test, nodes)
        NetworkThread().start()

        versions = self.wait_for_version_counts(N_SPROUT, N_OVERWINTER, N_SAPLING)
        assert_equal(len(self.nodes[0].getpeerinfo()), N_INITIAL,
                     "expected %d mininode peers" % N_INITIAL)
        assert_equal(versions.count(V_SPROUT), N_SPROUT)
        assert_equal(versions.count(V_OVERWINTER), N_OVERWINTER)
        assert_equal(versions.count(V_SAPLING), N_SAPLING)

        self.nodes[0].generate(9)
        assert_equal(9, self.nodes[0].getblockcount())
        assert_equal(len(self.nodes[0].getpeerinfo()), N_INITIAL)

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
        assert_equal(versions.count(V_SPROUT), N_SPROUT)
        assert_equal(versions.count(V_OVERWINTER), N_OVERWINTER)
        assert_equal(versions.count(V_SAPLING), N_SAPLING)

        self.nodes[0].generate(1)

        nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_OVERWINTER))
        time.sleep(3)
        assert_equal(len(self.nodes[0].getpeerinfo()), N_INITIAL + 1)

        nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_SAPLING))
        time.sleep(3)
        assert_equal(len(self.nodes[0].getpeerinfo()), N_INITIAL + 2)

        reject_sub = "Version must be %d or greater" % MIN_PEER_PROTO_VERSION
        bad = NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_BELOW_MIN)
        nodes.append(bad)
        self.wait_for_reject(bad, reject_sub)

        peerinfo = self.nodes[0].getpeerinfo()
        versions = [x["version"] for x in peerinfo]
        assert_equal(versions.count(V_SPROUT), N_SPROUT)
        assert_equal(versions.count(V_OVERWINTER), N_OVERWINTER + 1)
        assert_equal(versions.count(V_SAPLING), N_SAPLING + 1)

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
        assert_equal(versions.count(V_SPROUT), N_SPROUT)
        assert_equal(versions.count(V_OVERWINTER), N_OVERWINTER + 1)
        assert_equal(versions.count(V_SAPLING), N_SAPLING + 1)

        self.nodes[0].generate(1)

        nodes.append(NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_SAPLING))
        time.sleep(3)
        assert_equal(len(self.nodes[0].getpeerinfo()), N_INITIAL + 3)

        bad2 = NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_BELOW_MIN)
        nodes.append(bad2)
        self.wait_for_reject(bad2, reject_sub)

        bad3 = NodeConn('127.0.0.1', p2p_port(0), self.nodes[0], test, "regtest", V_BELOW_MIN)
        nodes.append(bad3)
        self.wait_for_reject(bad3, reject_sub)

        peerinfo = self.nodes[0].getpeerinfo()
        versions = [x["version"] for x in peerinfo]
        assert_equal(versions.count(V_SPROUT), N_SPROUT)
        assert_equal(versions.count(V_OVERWINTER), N_OVERWINTER + 1)
        assert_equal(versions.count(V_SAPLING), N_SAPLING + 2)

        disconnect_mininode_connections(nodes)


if __name__ == '__main__':
    NUPeerManagementTest().main()
