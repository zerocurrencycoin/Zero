// Copyright 2026 Zero Developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php.

#include "rpc/server.h"
#include "rpc/client.h"

#include "test/test_bitcoin.h"

#include <boost/algorithm/string.hpp>
#include <boost/test/unit_test.hpp>

#include <string>
#include <univalue.h>

using namespace std;

extern UniValue CallRPC(string args);
extern void CheckRPCThrows(std::string rpcString, std::string expectedErrorMessage);

BOOST_FIXTURE_TEST_SUITE(rpc_zeronode_tests, TestingSetup)

// Group A: Read-only Zeronode RPCs
BOOST_AUTO_TEST_CASE(rpc_createzeronodekey)
{
    BOOST_CHECK_THROW(CallRPC("createzeronodekey extra"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("createzeronodekey"));
    BOOST_CHECK(r.isStr());
    BOOST_CHECK(!r.get_str().empty());
}

BOOST_AUTO_TEST_CASE(rpc_listzeronodeconf)
{
    BOOST_CHECK_THROW(CallRPC("listzeronodeconf a b"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("listzeronodeconf"));
    BOOST_CHECK(r.isArray());
    BOOST_CHECK_NO_THROW(r = CallRPC("listzeronodeconf \"\""));
    BOOST_CHECK(r.isArray());
}

BOOST_AUTO_TEST_CASE(rpc_znsync)
{
    BOOST_CHECK_THROW(CallRPC("znsync"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("znsync invalid"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("znsync status"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK(r.exists("IsBlockchainSynced"));
    BOOST_CHECK_NO_THROW(r = CallRPC("znsync reset"));
    BOOST_CHECK(r.isStr());
    BOOST_CHECK_EQUAL(r.get_str(), "success");
}

BOOST_AUTO_TEST_CASE(rpc_getzeronodecount)
{
    BOOST_CHECK_THROW(CallRPC("getzeronodecount extra"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getzeronodecount"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK(r.exists("total"));
    BOOST_CHECK(r.exists("enabled"));
}

BOOST_AUTO_TEST_CASE(rpc_listzeronodes)
{
    BOOST_CHECK_THROW(CallRPC("listzeronodes a b"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("listzeronodes"));
    BOOST_CHECK(r.isArray());
    BOOST_CHECK_NO_THROW(r = CallRPC("listzeronodes \"\""));
    BOOST_CHECK(r.isArray());
}

BOOST_AUTO_TEST_CASE(rpc_spork)
{
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("spork show"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK_NO_THROW(r = CallRPC("spork active"));
    BOOST_CHECK(r.isObject());
}

// Group B: Param validation
BOOST_AUTO_TEST_CASE(rpc_zeronodeconnect_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("zeronodeconnect"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("zeronodeconnect a b"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_startalias_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("startalias"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("startalias a b"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_getzeronodestatus_throws_when_not_zeronode)
{
    CheckRPCThrows("getzeronodestatus", "This is not a zeronode");
}

BOOST_AUTO_TEST_CASE(rpc_zeronode_super_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("zeronode invalid"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("zeronode unknown"), runtime_error);
}

BOOST_AUTO_TEST_SUITE_END()
