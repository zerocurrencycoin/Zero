#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.

"""
UI-shaped getalldata coverage: datatype / nCount / balances vs thin listtransactions.

Uses transparent sends only (usual T addresses). Disables S6 time coalesce via
-rpcdatacontinue=0 so successive calls in one test succeed.

Run: ./qa/pull-tester/rpc-tests.sh getalldata_scenario
"""

from __future__ import print_function

from decimal import Decimal

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
    assert_greater_than,
    initialize_chain_clean,
    mine_until_mature,
    start_node,
)


class GetAllDataScenarioTest(BitcoinTestFramework):
    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 1)

    def setup_network(self):
        self.nodes = [
            start_node(0, self.options.tmpdir, extra_args=[
                "-rpcdatacontinue=0",
            ])
        ]
        self.is_network_split = False

    def run_test(self):
        node = self.nodes[0]
        mine_until_mature(node, self.nodes)

        # Build >5 wallet txs involving T addresses so nCount can bind.
        addrs = [node.getnewaddress() for _ in range(8)]
        for a in addrs:
            node.sendtoaddress(a, Decimal("0.01"))
        node.generate(1)

        # Datatype 1: balances, empty or short History list still present as array
        r1 = node.getalldata(1)
        assert isinstance(r1, dict)
        assert "addressbalance" in r1
        assert "listtransactions" in r1
        assert isinstance(r1["listtransactions"], list)

        # Datatype 0 + type 0 (all) + nCount 5
        r0 = node.getalldata(0, 0, 5)
        assert isinstance(r0["listtransactions"], list)
        assert_equal(len(r0["listtransactions"]) <= 5, True)
        assert_greater_than(len(r0["listtransactions"]), 0)

        # nCount <= 0 clamps to 200; length still bounded by wallet size
        r_clamp = node.getalldata(0, 0, 0)
        assert_equal(len(r_clamp["listtransactions"]) <= 200, True)

        # Datatype 2: txs + chain fields; nCount 3
        r2 = node.getalldata(2, 0, 3)
        assert_equal(len(r2["listtransactions"]) <= 3, True)

        # Zerowallet 4-arg shape
        r4 = node.getalldata(0, 2, 50, True)
        assert isinstance(r4["listtransactions"], list)
        assert_equal(len(r4["listtransactions"]) <= 50, True)

        # Spot-check: History entries expose txid strings
        for ht in r0["listtransactions"]:
            assert "txid" in ht and isinstance(ht["txid"], str) and len(ht["txid"]) == 64


if __name__ == "__main__":
    GetAllDataScenarioTest().main()
