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

BOOST_FIXTURE_TEST_SUITE(rpc_zero_experimental_tests, TestingSetup)

// zero_experimental param validation (P1)
BOOST_AUTO_TEST_CASE(rpc_getsaplingwitness_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("getsaplingwitness"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("getsaplingwitness deadbeef"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("getsaplingwitness deadbeef 0 1"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_getsaplingwitnessatheight_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("getsaplingwitnessatheight"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("getsaplingwitnessatheight deadbeef"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("getsaplingwitnessatheight deadbeef 0"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("getsaplingwitnessatheight deadbeef 0 100 1"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_getsaplingblocks_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("getsaplingblocks"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("getsaplingblocks 0"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("getsaplingblocks 0 1 1 1"), runtime_error);
}

BOOST_AUTO_TEST_SUITE_END()
