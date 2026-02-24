// Copyright (c) 2025 The Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php.

#include "rpc/server.h"
#include "rpc/client.h"

#include "test/test_bitcoin.h"

#include <boost/test/unit_test.hpp>

#include <string>
#include <univalue.h>

using namespace std;

extern UniValue CallRPC(string args);

BOOST_FIXTURE_TEST_SUITE(rpc_zero_exclusive_tests, TestingSetup)

// Group F: zero_exclusive param validation (P1)
BOOST_AUTO_TEST_CASE(rpc_zs_listtransactions_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("zs_listtransactions 1 2"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("zs_listtransactions"));
    BOOST_CHECK(r.isArray());
}

BOOST_AUTO_TEST_CASE(rpc_zs_gettransaction_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("zs_gettransaction"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("zs_gettransaction a b"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_zs_listspentbyaddress_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("zs_listspentbyaddress"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("zs_listspentbyaddress t1KzZ5n2TPEGYXTZ3WYGL1AYEumEQaRoHaL 0 0"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_zs_listreceivedbyaddress_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("zs_listreceivedbyaddress"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("zs_listreceivedbyaddress t1KzZ5n2TPEGYXTZ3WYGL1AYEumEQaRoHaL 0 0"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_zs_listsentbyaddress_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("zs_listsentbyaddress"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("zs_listsentbyaddress t1KzZ5n2TPEGYXTZ3WYGL1AYEumEQaRoHaL 0 0"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_getalldata_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("getalldata 0 0 0 0 0"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 0"));
    BOOST_CHECK(r.isObject());
}

BOOST_AUTO_TEST_CASE(rpc_getsupply_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("getsupply 0 1"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getsupply 0"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK(r.exists("supplyzats"));
    BOOST_CHECK(r.exists("supply"));
}

BOOST_AUTO_TEST_SUITE_END()
