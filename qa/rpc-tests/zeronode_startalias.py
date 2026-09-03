#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.

"""TNT-12 Phase C: two-node znsync and startalias.

A successful startalias needs an exact 10000 ZER collateral UTXO. Regtest
halves every 150 blocks, so total miner emission is ~3000 ZER -- not enough
to form that UTXO without a premine or a regtest-only collateral amount.
This script covers the path that is reachable: znsync to 999, zeronode.conf
load, startalias without a valid vin.
"""

import os
import time

from test_framework.authproxy import JSONRPCException
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    connect_nodes_bi,
    initialize_chain_clean,
    mine_to_height,
    p2p_port,
    start_node,
    start_nodes,
    stop_node,
)

SYNC_TIMEOUT = 180
ZN_ARGS = ['-debug=zeronode', '-txindex=1']


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


if __name__ == '__main__':
    ZeronodeStartaliasTest().main()
