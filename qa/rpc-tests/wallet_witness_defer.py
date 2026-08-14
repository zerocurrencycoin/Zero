#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""
PROD-WIT-REGTEST: opt-in ibd-defer + NOTEIDX after -reindex.

R1/R2: Sapling spend after deferred rebuild.
R5a: invalidate tip once chain tip restored (around rebuild window), then recover+spend.
R5b: 1-, 3-, 10-, and 20-block invalidate after witnesses built; remine; spend still works.
R7b: SIGKILL during -walletwitness=rebuild; restart; eventually spend.

Tier: B pass. See Perf.md §0.15 / §0.16.
"""

import time
from decimal import Decimal

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    COINBASE_MATURITY,
    assert_equal,
    assert_greater_than,
    bitcoind_processes,
    get_coinbase_address,
    initialize_chain_clean,
    start_node,
    stop_node,
    wait_and_assert_operationid_status,
    wait_bitcoinds,
)


def reorg_n_blocks(node, n):
    """Disconnect n blocks via invalidateblock, remine n. Requires tip >= n."""
    tip = node.getblockcount()
    assert_greater_than(tip, n - 1)
    deep_hash = node.getblockhash(tip - n + 1)
    print("R5b-%d: invalidate height %d (%s) then remine %d" % (n, tip - n + 1, deep_hash, n))
    node.invalidateblock(deep_hash)
    assert_equal(node.getblockcount(), tip - n)
    node.generate(n)
    assert_equal(node.getblockcount(), tip)


def wait_until_witnesses_ready(node, zaddr, timeout=900):
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


class WalletWitnessDeferTest(BitcoinTestFramework):
    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 1)

    def setup_network(self):
        self.nodes = []
        self.is_network_split = False
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
        wi = node.getwalletinfo()
        assert_greater_than(wi.get("note_tx_count", 0), 0)
        print(
            "Pre-reindex: tip=%d z_balance=%s note_tx_count=%s"
            % (tip_before, bal_before, wi.get("note_tx_count"))
        )

        defer_args = [
            "-debug=zrpcunsafe",
            "-reindex",
            "-checkblockindex=1",
            "-walletwitness=ibd-defer",
            "-walletwitnessnote=1",
        ]
        print("Restart with %s ..." % " ".join(defer_args))
        stop_node(node, 0)
        wait_bitcoinds()
        self.nodes[0] = start_node(
            0, self.options.tmpdir, defer_args, timewait=900
        )
        node = self.nodes[0]

        deadline = time.time() + 900
        tip_after = node.getblockcount()
        while tip_after < tip_before and time.time() < deadline:
            time.sleep(1)
            tip_after = node.getblockcount()
        assert_equal(tip_after, tip_before)

        # R5a: tip restored; poke reorg around post-import rebuild window.
        tip_hash = node.getbestblockhash()
        print("R5a: invalidateblock %s (tip restored)" % tip_hash)
        node.invalidateblock(tip_hash)
        assert_equal(node.getblockcount(), tip_before - 1)
        assert_greater_than(node.getblockcount(), 0)
        node.getblockchaininfo()
        node.generate(1)
        tip_after = node.getblockcount()
        assert_equal(tip_after, tip_before)

        bal_after = wait_until_witnesses_ready(node, zaddr)
        assert_equal(bal_after, bal_before)
        wi2 = node.getwalletinfo()
        assert_greater_than(wi2.get("note_tx_count", 0), 0)
        print(
            "Post-reindex+defer+noteidx+R5a: tip=%d z_balance=%s note_tx_count=%s"
            % (tip_after, bal_after, wi2.get("note_tx_count"))
        )

        zaddr2 = node.z_getnewaddress("sapling")
        send_amt = Decimal("0.4")
        recipients2 = [{"address": zaddr2, "amount": send_amt}]
        print("Post-rebuild z_sendmany %s -> new sapling..." % send_amt)
        opid2 = node.z_sendmany(zaddr, recipients2, 1, fee)
        wait_and_assert_operationid_status(node, opid2)
        node.generate(1)
        assert_equal(Decimal(node.z_getbalance(zaddr2)), send_amt)
        expected_change = amount - send_amt - fee
        assert_equal(Decimal(node.z_getbalance(zaddr)), expected_change)
        print("Success: R1/R2/R5a defer+NOTEIDX shielded spend after -reindex")

        # R5b: post-build reorgs inside WITNESS_CACHE_SIZE (100) / MAX_REORG (99).
        # 1 and 3 are tip-poke / short multi-pop. 10 and 20 exercise deeper Decrement
        # still well below the 99 policy cap (excessive reject is TNT-02 / R5d).
        reorg_n_blocks(node, 1)
        node.generate(3)
        reorg_n_blocks(node, 3)
        node.generate(10)
        reorg_n_blocks(node, 10)
        node.generate(20)
        reorg_n_blocks(node, 20)

        zaddr3 = node.z_getnewaddress("sapling")
        send2 = Decimal("0.1")
        opid3 = node.z_sendmany(
            zaddr, [{"address": zaddr3, "amount": send2}], 1, fee
        )
        wait_and_assert_operationid_status(node, opid3)
        node.generate(1)
        assert_equal(Decimal(node.z_getbalance(zaddr3)), send2)
        print("Success: R5b 1/3/10/20-block spend after post-build reorg")

        # R7b: SIGKILL during forced tip rebuild; restart and spend.
        print("R7b: restart with -walletwitness=rebuild then SIGKILL")
        stop_node(node, 0)
        wait_bitcoinds()
        self.nodes[0] = start_node(
            0,
            self.options.tmpdir,
            [
                "-debug=zrpcunsafe",
                "-walletwitness=rebuild",
                "-walletwitnessnote=1",
            ],
            timewait=900,
        )
        proc = bitcoind_processes[0]
        proc.kill()
        proc.wait()
        bitcoind_processes.pop(0, None)
        print("R7b: killed pid; restart with defer+noteidx")
        self.nodes[0] = start_node(
            0,
            self.options.tmpdir,
            [
                "-debug=zrpcunsafe",
                "-walletwitness=ibd-defer",
                "-walletwitnessnote=1",
            ],
            timewait=900,
        )
        node = self.nodes[0]
        zaddr4 = node.z_getnewaddress("sapling")
        send3 = Decimal("0.05")
        bal_ready = wait_until_witnesses_ready(node, zaddr)
        assert_greater_than(bal_ready, Decimal("0"))
        opid4 = node.z_sendmany(
            zaddr, [{"address": zaddr4, "amount": send3}], 1, fee
        )
        wait_and_assert_operationid_status(node, opid4)
        node.generate(1)
        assert_equal(Decimal(node.z_getbalance(zaddr4)), send3)
        print("Success: R7b spend after kill mid-rebuild restart")


if __name__ == "__main__":
    WalletWitnessDeferTest().main()
