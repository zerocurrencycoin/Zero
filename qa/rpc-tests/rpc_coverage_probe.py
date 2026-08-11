#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.

"""
Probe RPCs that are not already string-referenced by qa/rpc-tests or C++ RPC/gtest.

For each uncovered method (or --all-registered), classify:
  recognize -- server knows the method (not -32601)
  respond   -- JSON-RPC success or error returned
  crash     -- node no longer answers getblockcount after the call

Destructive / state-changing methods are only checked via help <name>
(recognize+respond without side effects).

Does NOT prove argument coverage: it checks that each RPC is reachable,
not that its parameters are exercised.

Run:
  ./qa/pull-tester/rpc-tests.sh rpc_coverage_probe
  ZERO_RPC_PROBE_ALL=1 ./qa/pull-tester/rpc-tests.sh rpc_coverage_probe
"""

from __future__ import print_function

import os
import re
import sys
from pathlib import Path

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, initialize_chain_clean, start_nodes
from test_framework.authproxy import JSONRPCException


# Methods that must not be invoked with empty args (side effects / shutdown).
SKIP_INVOKE = {
    "stop",
    "generate",
    "setgenerate",
    "invalidateblock",
    "reconsiderblock",
    "clearbanned",
    "setban",
    "disconnectnode",
    "addnode",
    "submitblock",
    "sendrawtransaction",
    "sendtoaddress",
    "sendmany",
    "sendfrom",
    "move",
    "z_sendmany",
    "z_shieldcoinbase",
    "z_mergetoaddress",
    "z_setmigration",
    "backupwallet",
    "dumpwallet",
    "importwallet",
    "encryptwallet",
    "walletpassphrase",
    "walletpassphrasechange",
    "walletlock",
    "importprivkey",
    "importaddress",
    "keypoolrefill",
    "startzeronode",
    "startalias",
    "submitbudget",
    "preparebudget",
    "znbudgetvote",
    "znbudgetrawvote",
    "spork",  # can change network consensus params when keyed
}


def _repo_root():
    # qa/rpc-tests/<this> -> repo root
    return Path(__file__).resolve().parents[2]


def registered_rpc_names():
    """Parse CRPCCommand tables: { \"category\", \"name\", &actor"""
    root = _repo_root()
    pat = re.compile(r'\{\s*"[^"]+"\s*,\s*"([a-z][a-z0-9_]*)"\s*,\s*&')
    names = set()
    for p in (root / "src").rglob("*.cpp"):
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for m in pat.finditer(text):
            names.add(m.group(1))
    return names


def covered_rpc_names(registered):
    """String-match coverage in qa scripts + C++ unit/gtest (over-counts comments)."""
    root = _repo_root()
    blobs = []
    for p in (root / "qa" / "rpc-tests").glob("*.py"):
        if p.name == "rpc_coverage_probe.py":
            continue
        try:
            blobs.append(p.read_text(errors="ignore"))
        except OSError:
            pass
    for base in (
        root / "src" / "test",
        root / "src" / "wallet" / "gtest",
        root / "src" / "gtest",
    ):
        if not base.is_dir():
            continue
        for p in base.rglob("*.cpp"):
            try:
                blobs.append(p.read_text(errors="ignore"))
            except OSError:
                pass
    blob = "\n".join(blobs)
    covered = set()
    for name in registered:
        if re.search(r"\b" + re.escape(name) + r"\b", blob):
            covered.add(name)
    return covered


class RPCCoverageProbeTest(BitcoinTestFramework):
    def setup_chain(self):
        print("Initializing test directory " + self.options.tmpdir)
        initialize_chain_clean(self.options.tmpdir, 1)

    def setup_network(self, split=False):
        self.nodes = start_nodes(1, self.options.tmpdir)
        self.is_network_split = False

    def _alive(self):
        try:
            self.nodes[0].getblockcount()
            return True
        except Exception:
            return False

    def _call_empty(self, name):
        # AuthServiceProxy: node.name() with no args
        return getattr(self.nodes[0], name)()

    def run_test(self):
        registered = registered_rpc_names()
        covered = covered_rpc_names(registered)
        probe_all = os.environ.get("ZERO_RPC_PROBE_ALL", "") in ("1", "true", "yes")
        if probe_all:
            targets = sorted(registered)
            print("ZERO_RPC_PROBE_ALL=1 -- probing all %d registered RPCs" % len(targets))
        else:
            targets = sorted(registered - covered)
            print(
                "registered=%d covered_string_hit=%d uncovered=%d"
                % (len(registered), len(covered), len(targets))
            )

        rows = []
        crashes = []

        for name in targets:
            row = {
                "rpc": name,
                "mode": "help" if name in SKIP_INVOKE else "empty_args",
                "recognize": False,
                "respond": False,
                "crash": False,
                "code": None,
                "message": "",
            }
            if not self._alive():
                row["crash"] = True
                crashes.append(name)
                rows.append(row)
                print("ABORT: node dead before %s" % name)
                break

            try:
                if name in SKIP_INVOKE:
                    self.nodes[0].help(name)
                    row["recognize"] = True
                    row["respond"] = True
                    row["message"] = "help_ok"
                else:
                    try:
                        self._call_empty(name)
                        row["recognize"] = True
                        row["respond"] = True
                        row["message"] = "ok"
                    except JSONRPCException as e:
                        row["respond"] = True
                        err = e.error if isinstance(e.error, dict) else {}
                        code = err.get("code")
                        msg = err.get("message", "")
                        row["code"] = code
                        row["message"] = (msg or "")[:120]
                        # -32601 method not found => not recognized
                        row["recognize"] = code != -32601
            except Exception as e:
                row["message"] = ("exception: %s" % e)[:160]
                if not self._alive():
                    row["crash"] = True
                    crashes.append(name)

            if not self._alive():
                row["crash"] = True
                if name not in crashes:
                    crashes.append(name)

            rows.append(row)
            status = (
                "CRASH"
                if row["crash"]
                else (
                    "ok"
                    if row["message"] == "ok"
                    else (
                        "help"
                        if row["message"] == "help_ok"
                        else "err(%s)" % row["code"]
                    )
                )
            )
            print(
                "%s\t%s\trecognize=%s respond=%s crash=%s\t%s"
                % (
                    name,
                    row["mode"],
                    row["recognize"],
                    row["respond"],
                    row["crash"],
                    status if status != "err(None)" else row["message"],
                )
            )

        n = len(rows)
        n_rec = sum(1 for r in rows if r["recognize"])
        n_resp = sum(1 for r in rows if r["respond"])
        n_crash = sum(1 for r in rows if r["crash"])
        print(
            "SUMMARY probe=%d recognize=%d respond=%d crash=%d"
            % (n, n_rec, n_resp, n_crash)
        )

        # Soft assert: every probed method must respond without crashing.
        assert_equal(n_crash, 0)
        assert n_resp == n, "expected every probe to get a JSON-RPC response"
        # help/stop always registered; empty-arg probes should recognize except bugs
        unknown = [r["rpc"] for r in rows if not r["recognize"]]
        assert not unknown, "method not found for registered names: %s" % unknown


if __name__ == "__main__":
    RPCCoverageProbeTest().main()
