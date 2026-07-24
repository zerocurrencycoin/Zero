#!/usr/bin/env python3
# Copyright (c) 2015 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .


from test_framework.socks5 import Socks5Configuration, Socks5Command, Socks5Server, AddressType
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import assert_equal, ipv6_loopback_available, start_nodes

import queue
import os
import socket
import sys

'''
Test plan:
- Start dummy SOCKS5 proxies (IPv4 unauth, IPv4 auth+unauth, optional IPv6)
- Start zerods with matching -proxy / -onion / -proxyrandomize
- addnode (onetry) and check SOCKS commands + getnetworkinfo

Any of the three Socks5Server binds may fail (port busy, IPv6 disabled for
security, etc.): emit a strong WARNING and continue with whatever legs remain.
If no proxy can bind, the test warns and exits successfully (nothing to assert).

Socks5Configuration.unauth / .auth are independent server capabilities:
  unauth=True  -> accept method 0x00 (no credentials)
  auth=True    -> accept method 0x02 (username/password)
conf1: unauth only ("other proxy"). conf2/conf3: unauth+auth (Tor-like).
'''

# Destination cases exercised through a node's configured proxy.
# Each entry: (label, addnode_arg, expect_addr, expect_port, onion_only)
ADDNODE_CASES = (
    ("IPv4", "15.61.23.23:1234", "15.61.23.23", 1234, False),
    ("IPv6-destination", "[1233:3432:2434:2343:3234:2345:6546:4534]:5443",
     "1233:3432:2434:2343:3234:2345:6546:4534", 5443, False),
    ("onion", "bitcoinostk4e4re.onion:8333", "bitcoinostk4e4re.onion", 8333, True),
    ("DNS", "node.noumenon:8333", "node.noumenon", 8333, False),
)


def _warn(msg):
    print("WARNING: %s" % msg, file=sys.stderr)


def _strong_warn(msg):
    """Bind / environment failures that skip a whole proxy or leg."""
    print("WARNING: *** %s ***" % msg, file=sys.stderr)


def _addr_label(conf):
    host, port = conf.addr[0], conf.addr[1]
    if conf.af == socket.AF_INET6:
        return "[%s]:%i" % (host, port)
    return "%s:%i" % (host, port)


def _proxy_arg(conf):
    """zerod -proxy= / -onion= value for this bind."""
    if conf.af == socket.AF_INET6:
        return "[%s]:%i" % (conf.addr[0], conf.addr[1])
    return "%s:%i" % (conf.addr[0], conf.addr[1])


def start_socks_proxy(conf, label):
    """Bind/start Socks5Server. On any failure: strong WARNING, return None."""
    try:
        serv = Socks5Server(conf)
        serv.start()
        return serv
    except OSError as e:
        _strong_warn(
            "%s SOCKS bind %s failed (%s); skipping this proxy. "
            "Remaining proxy legs will still run."
            % (label, _addr_label(conf), e)
        )
        return None
    except Exception as e:
        _strong_warn(
            "%s SOCKS start %s failed (%s: %s); skipping this proxy. "
            "Remaining proxy legs will still run."
            % (label, _addr_label(conf), type(e).__name__, e)
        )
        return None


def make_socks_conf(af, host, port_base, unauth, auth):
    conf = Socks5Configuration()
    conf.af = af
    conf.addr = (host, port_base + (os.getpid() % 1000))
    conf.unauth = unauth
    conf.auth = auth
    return conf


class ProxyTest(BitcoinTestFramework):
    def __init__(self):
        # conf1: unauth-only IPv4 ("other proxy")
        self.conf1 = make_socks_conf(socket.AF_INET, '127.0.0.1', 13000, True, False)
        # conf2: Tor-like IPv4 (unauth + auth)
        self.conf2 = make_socks_conf(socket.AF_INET, '127.0.0.1', 14000, True, True)
        # conf3: Tor-like IPv6 localhost
        self.conf3 = make_socks_conf(socket.AF_INET6, '::1', 15000, True, True)

        self.serv1 = start_socks_proxy(self.conf1, "conf1/IPv4-unauth")
        self.serv2 = start_socks_proxy(self.conf2, "conf2/IPv4-auth+unauth")
        if ipv6_loopback_available():
            self.serv3 = start_socks_proxy(self.conf3, "conf3/IPv6")
        else:
            self.serv3 = None
            _strong_warn(
                "No usable ::1 loopback on %s (IPv6 may be disabled); "
                "skipping conf3/IPv6 proxy."
                % sys.platform
            )

        # Node legs: only those whose proxies bound successfully.
        # Each leg: name, node_args, proxy_slots (serv for each ADDNODE_CASES index),
        # auth expect, test_onion, networkinfo checker kwargs.
        self.legs = []
        if self.serv1 is not None:
            self.legs.append({
                "name": "basic-proxy-conf1",
                "args": [
                    '-listen', '-debug=net', '-debug=proxy',
                    '-proxy=%s' % _proxy_arg(self.conf1),
                    '-proxyrandomize=1',
                ],
                "proxy_for_case": [self.serv1, self.serv1, self.serv1, self.serv1],
                "auth": False,
                "test_onion": True,
                "netinfo": {
                    "proxy_nets": ("ipv4", "ipv6", "onion"),
                    "proxy": _proxy_arg(self.conf1),
                    "randomize": True,
                    "onion_reachable": True,
                },
            })
        else:
            _strong_warn("Skipping leg basic-proxy-conf1 (conf1 unavailable)")

        if self.serv1 is not None and self.serv2 is not None:
            self.legs.append({
                "name": "proxy-conf1-onion-conf2",
                "args": [
                    '-listen', '-debug=net', '-debug=proxy',
                    '-proxy=%s' % _proxy_arg(self.conf1),
                    '-onion=%s' % _proxy_arg(self.conf2),
                    '-proxyrandomize=0',
                ],
                "proxy_for_case": [self.serv1, self.serv1, self.serv2, self.serv1],
                "auth": False,
                "test_onion": True,
                "netinfo": {
                    "proxy_nets": ("ipv4", "ipv6"),
                    "proxy": _proxy_arg(self.conf1),
                    "randomize": False,
                    "onion_proxy": _proxy_arg(self.conf2),
                    "onion_randomize": False,
                    "onion_reachable": True,
                },
            })
        else:
            _strong_warn(
                "Skipping leg proxy-conf1-onion-conf2 "
                "(needs both conf1 and conf2)"
            )

        if self.serv2 is not None:
            self.legs.append({
                "name": "proxy-conf2-randomize",
                "args": [
                    '-listen', '-debug=net', '-debug=proxy',
                    '-proxy=%s' % _proxy_arg(self.conf2),
                    '-proxyrandomize=1',
                ],
                "proxy_for_case": [self.serv2, self.serv2, self.serv2, self.serv2],
                "auth": True,
                "test_onion": True,
                "expect_unique_credentials": True,
                "netinfo": {
                    "proxy_nets": ("ipv4", "ipv6", "onion"),
                    "proxy": _proxy_arg(self.conf2),
                    "randomize": True,
                    "onion_reachable": True,
                },
            })
        else:
            _strong_warn("Skipping leg proxy-conf2-randomize (conf2 unavailable)")

        if self.serv3 is not None:
            self.legs.append({
                "name": "proxy-conf3-ipv6",
                "args": [
                    '-listen', '-debug=net', '-debug=proxy',
                    '-proxy=%s' % _proxy_arg(self.conf3),
                    '-proxyrandomize=0',
                    '-noonion',
                ],
                "proxy_for_case": [self.serv3, self.serv3, self.serv3, self.serv3],
                "auth": False,
                "test_onion": False,
                "netinfo": {
                    "proxy_nets": ("ipv4", "ipv6"),
                    "proxy": _proxy_arg(self.conf3),
                    "randomize": False,
                    "onion_reachable": False,
                },
            })
        else:
            _strong_warn("Skipping leg proxy-conf3-ipv6 (conf3 unavailable)")

        if not self.legs:
            _strong_warn(
                "No SOCKS proxies available; proxy_test has nothing to run "
                "(will pass without node asserts)."
            )

    def setup_nodes(self):
        # Note: proxies are not used to connect to local nodes (NET_UNROUTABLE).
        if not self.legs:
            # Framework expects >=1 node in some paths; start a minimal node
            # with no proxy so setup completes, then run_test no-ops.
            return start_nodes(1, self.options.tmpdir, extra_args=[['-listen=0']])
        extra_args = [leg["args"] for leg in self.legs]
        return start_nodes(len(extra_args), self.options.tmpdir, extra_args=extra_args)

    def _expect_socks_cmd(self, proxy, what, timeout=60):
        try:
            cmd = proxy.queue.get(timeout=timeout)
        except queue.Empty:
            _warn("Timed out after %ss waiting for SOCKS command (%s)" % (timeout, what))
            raise AssertionError("SOCKS command timeout: %s" % what)
        if isinstance(cmd, Exception):
            _warn("SOCKS proxy raised during %s: %r" % (what, cmd))
            raise AssertionError("SOCKS proxy error during %s: %s" % (what, cmd))
        if not isinstance(cmd, Socks5Command):
            _warn("Unexpected SOCKS queue item during %s: %r" % (what, cmd))
            raise AssertionError("Unexpected SOCKS queue item during %s: %r" % (what, cmd))
        return cmd

    def run_addnode_cases(self, node, proxy_for_case, auth, test_onion=True):
        """Parametrized addnode/SOCKS checks shared by all legs."""
        rv = []
        for i, (label, addnode_arg, expect_addr, expect_port, onion_only) in enumerate(ADDNODE_CASES):
            if onion_only and not test_onion:
                continue
            node.addnode(addnode_arg, "onetry")
            cmd = self._expect_socks_cmd(
                proxy_for_case[i],
                "%s addnode via proxy" % label,
            )
            # zerod SOCKS5 sends atyp DOMAINNAME even for IPv4/IPv6 literals
            assert_equal(cmd.atyp, AddressType.DOMAINNAME)
            assert_equal(cmd.addr, expect_addr)
            assert_equal(cmd.port, expect_port)
            if not auth:
                assert_equal(cmd.username, None)
                assert_equal(cmd.password, None)
            rv.append(cmd)
        return rv

    def check_networkinfo(self, node, netinfo):
        """Parametrized getnetworkinfo proxy asserts for one leg."""
        n = {}
        for x in node.getnetworkinfo()['networks']:
            n[x['name']] = x
        for net in netinfo["proxy_nets"]:
            assert_equal(n[net]['proxy'], netinfo["proxy"])
            assert_equal(n[net]['proxy_randomize_credentials'], netinfo["randomize"])
        if "onion_proxy" in netinfo:
            assert_equal(n['onion']['proxy'], netinfo["onion_proxy"])
            assert_equal(
                n['onion']['proxy_randomize_credentials'],
                netinfo["onion_randomize"],
            )
        assert_equal(n['onion']['reachable'], netinfo["onion_reachable"])

    def run_leg(self, node_index, leg):
        """Run addnode cases + optional credential uniqueness + getnetworkinfo."""
        print("=== proxy_test leg: %s (node %d) ===" % (leg["name"], node_index))
        rv = self.run_addnode_cases(
            self.nodes[node_index],
            leg["proxy_for_case"],
            leg["auth"],
            test_onion=leg["test_onion"],
        )
        if leg.get("expect_unique_credentials"):
            credentials = set((x.username, x.password) for x in rv)
            assert_equal(len(credentials), len(rv))
        self.check_networkinfo(self.nodes[node_index], leg["netinfo"])

    def run_test(self):
        if not self.legs:
            _strong_warn("proxy_test: no legs executed (all proxies unavailable)")
            return
        for i, leg in enumerate(self.legs):
            self.run_leg(i, leg)


if __name__ == '__main__':
    ProxyTest().main()
