// Copyright 2026 Zero Developers
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
extern void CheckRPCThrows(std::string rpcString, std::string expectedErrorMessage);

BOOST_FIXTURE_TEST_SUITE(rpc_zeronode_budget_tests, TestingSetup)

// Group A: Read-only budget RPCs (require RegisterBudgetRPCCommands enabled)
BOOST_AUTO_TEST_CASE(rpc_getnextsuperblock)
{
    BOOST_CHECK_THROW(CallRPC("getnextsuperblock extra"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getnextsuperblock"));
    BOOST_CHECK(r.isNum() || (r.isStr() && r.get_str() == "unknown"));
}

BOOST_AUTO_TEST_CASE(rpc_getbudgetinfo)
{
    BOOST_CHECK_THROW(CallRPC("getbudgetinfo a b"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getbudgetinfo"));
    BOOST_CHECK(r.isArray());
}

BOOST_AUTO_TEST_CASE(rpc_getbudgetprojection)
{
    BOOST_CHECK_THROW(CallRPC("getbudgetprojection extra"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getbudgetprojection"));
    BOOST_CHECK(r.isArray());
}

// Group B: Param validation
BOOST_AUTO_TEST_CASE(rpc_znbudgetvote_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("znbudgetvote"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("znbudgetvote local"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("znbudgetvote local deadbeef"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("znbudgetvote local ed2f83cedee59a91406f5f47ec4d60bf5a7f9ee6293913c82976bd2d3a658041 maybe"));
    BOOST_CHECK(r.isStr());
    BOOST_CHECK_EQUAL(r.get_str(), "You can only vote 'yes' or 'no'");
}

BOOST_AUTO_TEST_CASE(rpc_preparebudget_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("preparebudget"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("preparebudget a"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_submitbudget_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("submitbudget"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("submitbudget a"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_znbudget_super_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("znbudget invalid"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("znbudget unknown"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_znbudgetrawvote_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("znbudgetrawvote"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_znbudget_getvotes_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("znbudget getvotes"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_checkbudgets)
{
    BOOST_CHECK_THROW(CallRPC("checkbudgets extra"), runtime_error);
    BOOST_CHECK_NO_THROW(CallRPC("checkbudgets"));
}

BOOST_AUTO_TEST_SUITE_END()
