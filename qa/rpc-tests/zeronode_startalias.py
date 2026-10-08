#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.

"""
Two-node znsync and startalias.

A successful startalias needs an exact 10000 ZER collateral UTXO. With halvings every
150 blocks, total regtest miner emission is about 3000 ZER, too little to form that UTXO
without a premine or a regtest-only collateral amount. This test covers the reachable
path: znsync to 999, zeronode.conf load, and startalias without a valid vin.

Port rule: on mainnet a zeronode must use the mainnet default P2P port; on other networks
that port is refused. Two regtest checks reach it without collateral: zerod refuses a
zeronode.conf line on the mainnet port at startup, and a zeronode announcing the mainnet
port (-zeronodeaddr) reports "not capable" once its wallet holds mature coins.
"""

import os
import subprocess
import time

from test_framework.authproxy import JSONRPCException
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    connect_nodes_bi,
    initialize_chain_clean,
    mature_height,
    mine_to_height,
    p2p_port,
    start_node,
    start_nodes,
    stop_node,
)

SYNC_TIMEOUT = 180
ZN_ARGS = ['-debug=zeronode', '-txindex=1']
MAINNET_PORT = 23801
CONF_PORT_ERROR = '(%d could be used only on mainnet)' % MAINNET_PORT
STATUS_PORT_ERROR = ('Not capable zeronode: Invalid port: %d - %d is only supported on mainnet.'
                     % (MAINNET_PORT, MAINNET_PORT))


def wait_zn_synced(node, timeout=SYNC_TIMEOUT):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = node.znsync('status')
        if last.get('RequestedZeronodeAssets') == 999:
            return last
        time.sleep(1)
    raise AssertionError('znsync did not finish: %r' % last)


class ZeronodeStartaliasTest(BitcoinTestFramework):

    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 2)

    def setup_network(self, split=False):
        extra = [ZN_ARGS, ZN_ARGS]
        self.nodes = start_nodes(2, self.options.tmpdir, extra)
        connect_nodes_bi(self.nodes, 0, 1)
        self.is_network_split = False
        self.sync_all()

    def run_test(self):
        node = self.nodes[0]
        mine_to_height(node, self.nodes, 20)
        wait_zn_synced(node)

        privkey = node.createzeronodekey()
        dummy_txid = '00' * 32
        conf_path = os.path.join(self.options.tmpdir, 'node0', 'regtest', 'zeronode.conf')
        ip = '127.0.0.1:%d' % p2p_port(0)
        with open(conf_path, 'w') as f:
            f.write('# test zeronode.conf\n')
            f.write('zn1 %s %s %s 0\n' % (ip, privkey, dummy_txid))

        stop_node(self.nodes[0], 0)
        self.nodes[0] = start_node(0, self.options.tmpdir, extra_args=ZN_ARGS)
        connect_nodes_bi(self.nodes, 0, 1)
        node = self.nodes[0]
        self.sync_all()
        wait_zn_synced(node)

        conf = node.listzeronodeconf()
        assert any(e.get('alias') == 'zn1' for e in conf), conf

        try:
            node.startalias('zn1')
            raise AssertionError('startalias should fail without a 10000 vin')
        except JSONRPCException as e:
            msg = e.error.get('message', '')
            assert 'Failed to start alias' in msg, e.error

        # zeronode.conf on the mainnet port: zerod exits before starting.
        stop_node(self.nodes[0], 0)
        with open(conf_path, 'w') as f:
            f.write('zn1 127.0.0.1:%d %s %s 0\n' % (MAINNET_PORT, privkey, dummy_txid))
        binary = os.getenv("BITCOIND", "zerod")
        datadir = os.path.join(self.options.tmpdir, 'node0')
        proc = subprocess.run([binary, '-datadir=' + datadir], capture_output=True, text=True, timeout=120)
        assert proc.returncode != 0, 'zerod started with a mainnet-port zeronode.conf'
        assert CONF_PORT_ERROR in proc.stderr, proc.stderr
        os.remove(conf_path)

        # A zeronode announcing the mainnet port is not capable. ManageStatus checks the
        # port after the wallet holds a mature balance.
        zn_args = ZN_ARGS + ['-zeronode=1', '-zeronodeprivkey=' + privkey,
                             '-zeronodeaddr=127.0.0.1:%d' % MAINNET_PORT]
        self.nodes[0] = start_node(0, self.options.tmpdir, extra_args=zn_args)
        connect_nodes_bi(self.nodes, 0, 1)
        node = self.nodes[0]
        mine_to_height(node, self.nodes, mature_height(5))
        wait_zn_synced(node)
        deadline = time.time() + SYNC_TIMEOUT
        status = None
        while time.time() < deadline:
            status = node.zeronodedebug()
            if 'Invalid port' in status:
                break
            time.sleep(1)
        assert status == STATUS_PORT_ERROR, status


if __name__ == '__main__':
    ZeronodeStartaliasTest().main()
