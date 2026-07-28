#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.

"""
S8: HTTP work queue full returns 503 with body "Work queue depth exceeded".

WorkQueue maxDepth counts *pending* items (not the in-flight worker).
With -rpcworkqueue=1 -rpcthreads=1:
  1) longpoll occupies the worker (dequeued)
  2) request A sits pending (queue size 1)
  3) request B must get HTTP 503

Run: ./qa/pull-tester/rpc-tests.sh rpc_workqueue_full
"""

from __future__ import print_function

import base64
import threading
import time

try:
    import http.client as httplib
except ImportError:
    import httplib
try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
    connect_nodes_bi,
    initialize_chain_clean,
    start_node,
)


class RpcWorkQueueFullTest(BitcoinTestFramework):
    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 2)

    def setup_network(self):
        self.nodes = [
            start_node(0, self.options.tmpdir, extra_args=[
                "-rpcworkqueue=1",
                "-rpcthreads=1",
            ]),
            start_node(1, self.options.tmpdir),
        ]
        connect_nodes_bi(self.nodes, 0, 1)
        self.is_network_split = False
        self.sync_all()

    def run_test(self):
        self.nodes[0].generate(1)
        self.sync_all()
        template = self.nodes[0].getblocktemplate()
        longpollid = template["longpollid"]

        url = urlparse.urlparse(self.nodes[0].url)
        auth = base64.b64encode(
            (url.username + ":" + url.password).encode("utf-8")
        ).decode("ascii")
        headers = {
            "Authorization": "Basic " + auth,
            "Content-Type": "application/json",
        }

        def post_async(body, out_list):
            try:
                conn = httplib.HTTPConnection(url.hostname, url.port, timeout=120)
                conn.request("POST", "/", body, headers)
                resp = conn.getresponse()
                out_list.append((resp.status, resp.read()))
                conn.close()
            except Exception as e:
                out_list.append(("err", str(e)))

        lp_out = []
        a_out = []
        thr_lp = threading.Thread(
            target=post_async,
            args=(
                '{"jsonrpc":"1.0","id":"lp","method":"getblocktemplate",'
                '"params":[{"longpollid":"%s"}]}' % longpollid,
                lp_out,
            ),
        )
        thr_lp.daemon = True
        thr_lp.start()
        time.sleep(1.0)

        # Pending slot (depth 1) while longpoll runs
        thr_a = threading.Thread(
            target=post_async,
            args=(
                '{"jsonrpc":"1.0","id":"a","method":"getblockcount","params":[]}',
                a_out,
            ),
        )
        thr_a.daemon = True
        thr_a.start()
        time.sleep(0.5)

        # Must be rejected -- queue full
        conn = httplib.HTTPConnection(url.hostname, url.port, timeout=30)
        conn.request(
            "POST",
            "/",
            '{"jsonrpc":"1.0","id":"b","method":"getblockcount","params":[]}',
            headers,
        )
        resp = conn.getresponse()
        body = resp.read()
        status = resp.status
        conn.close()

        assert_equal(status, 503)
        assert b"Work queue depth exceeded" in body, body

        # Unblock longpoll via peer tip; do not call node0 RPC until workers drain.
        self.nodes[1].generate(1)
        thr_lp.join(30)
        thr_a.join(30)
        time.sleep(0.5)

        # Queue drained; normal JSON-RPC works again.
        assert self.nodes[0].getblockcount() >= 2
        # Peer height (avoid sync_all while diagnosing queue pressure)
        assert self.nodes[1].getblockcount() >= 2


if __name__ == "__main__":
    RpcWorkQueueFullTest().main()
