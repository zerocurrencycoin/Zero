#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""
Shielded reindex coverage: Sapling note remains spendable after -reindex.

Exercises real BuildWitnessCache + pcoinsTip + ReadBlockFromDisk (not the
quarantined CachedWitnessesCleanIndex gtest harness). See WitnessReindex.md.

Tier: B pass / Ext candidate (maturity mining ~720 blocks).
"""

import time
from decimal import Decimal

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    COINBASE_MATURITY,
    assert_equal,
    get_coinbase_address,
    initialize_chain_clean,
    start_node,
    stop_node,
    wait_and_assert_operationid_status,
    wait_bitcoinds,
)


def wait_until_witnesses_ready(node, zaddr, timeout=600):
    """Retry z_getbalance until witness rebuild (-31/-33) is done."""
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            return Decimal(node.z_getbalance(zaddr))
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "witness" in msg or "-33" in msg or "-31" in msg:
                time.sleep(2)
                continue
            time.sleep(1)
    raise RuntimeError(
        "witnesses not ready within %ss: %s" % (timeout, last_err)
    )


class ReindexShieldedTest(BitcoinTestFramework):
    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 1)

    def setup_network(self):
        self.nodes = []
        self.is_network_split = False
        # NU_TEST_ARGS (Overwinter+Sapling at 1) applied by start_node.
        self.nodes.append(
            start_node(0, self.options.tmpdir, ["-debug=zrpcunsafe"])
        )

    def run_test(self):
        node = self.nodes[0]

        print("Mining to mature coinbase (COINBASE_MATURITY=%d)..." % COINBASE_MATURITY)
        node.generate(COINBASE_MATURITY + 1)
        assert_equal(node.getblockcount(), COINBASE_MATURITY + 1)

        taddr = get_coinbase_address(node)
        zaddr = node.z_getnewaddress("sapling")
        amount = Decimal("1.0")
        fee = Decimal("0.0001")
        recipients = [{"address": zaddr, "amount": amount}]

        print("Shielding %s to Sapling..." % amount)
        opid = node.z_sendmany(taddr, recipients, 1, fee)
        wait_and_assert_operationid_status(node, opid)
        node.generate(1)
        tip_before = node.getblockcount()
        bal_before = Decimal(node.z_getbalance(zaddr))
        assert_equal(bal_before, amount)
        print("Pre-reindex: tip=%d z_balance=%s" % (tip_before, bal_before))

        print("Stopping and restarting with -reindex -checkblockindex=1...")
        stop_node(node, 0)
        wait_bitcoinds()
        # Reindex + wallet witness rebuild on ~720 blocks; allow longer RPC wait.
        self.nodes[0] = start_node(
            0,
            self.options.tmpdir,
            ["-debug=zrpcunsafe", "-reindex", "-checkblockindex=1"],
            timewait=900,
        )
        node = self.nodes[0]

        # RPC can come up mid-reindex; wait until tip is restored.
        deadline = time.time() + 900
        tip_after = node.getblockcount()
        while tip_after < tip_before and time.time() < deadline:
            time.sleep(1)
            tip_after = node.getblockcount()
        assert_equal(tip_after, tip_before)
        bal_after = wait_until_witnesses_ready(node, zaddr)
        assert_equal(bal_after, bal_before)
        print("Post-reindex: tip=%d z_balance=%s" % (tip_after, bal_after))

        # Witnesses must support a further shielded spend.
        zaddr2 = node.z_getnewaddress("sapling")
        send_amt = Decimal("0.4")
        recipients2 = [{"address": zaddr2, "amount": send_amt}]
        print("Post-reindex z_sendmany %s -> new sapling..." % send_amt)
        opid2 = node.z_sendmany(zaddr, recipients2, 1, fee)
        wait_and_assert_operationid_status(node, opid2)
        node.generate(1)
        assert_equal(Decimal(node.z_getbalance(zaddr2)), send_amt)
        expected_change = amount - send_amt - fee
        assert_equal(Decimal(node.z_getbalance(zaddr)), expected_change)
        print("Success: shielded spend after -reindex")


if __name__ == "__main__":
    ReindexShieldedTest().main()
