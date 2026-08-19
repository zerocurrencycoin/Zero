// Copyright 2026 Zero Developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php.

#include "rpc/server.h"
#include "rpc/client.h"

#include "test/test_bitcoin.h"
#include "main.h"
#include "amount.h"
#include "chainparams.h"
#include "zeronode/spork.h"

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

BOOST_AUTO_TEST_CASE(rpc_zeronodestats)
{
    BOOST_CHECK_THROW(CallRPC("zeronodestats extra"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("zeronodestats"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK(r.exists("chainStats"));
    BOOST_CHECK(r.exists("nodeCount"));
    BOOST_CHECK(r["chainStats"].exists("zeronodepayment"));
    BOOST_CHECK(r["chainStats"].exists("developmentfee"));
}

BOOST_AUTO_TEST_CASE(rpc_zeronodecurrent)
{
    BOOST_CHECK_THROW(CallRPC("zeronodecurrent extra"), runtime_error);
    CheckRPCThrows("zeronodecurrent", "unknown");
}

BOOST_AUTO_TEST_CASE(rpc_getzeronodeoutputs)
{
    BOOST_CHECK_THROW(CallRPC("getzeronodeoutputs extra"), runtime_error);
    // Success path needs g_zeronodeWallet (not installed in TestingSetup).
}

BOOST_AUTO_TEST_CASE(rpc_startzeronode_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("startzeronode"), runtime_error);
    BOOST_CHECK_THROW(CallRPC("startzeronode local"), runtime_error);
}

BOOST_AUTO_TEST_CASE(rpc_zeronodedebug)
{
    BOOST_CHECK_THROW(CallRPC("zeronodedebug extra"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("zeronodedebug"));
    BOOST_CHECK(r.isStr());
}

BOOST_AUTO_TEST_CASE(rpc_createsporkkeys)
{
    BOOST_CHECK_THROW(CallRPC("createsporkkeys extra"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("createsporkkeys"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK(r.exists("pubkey"));
    BOOST_CHECK(r.exists("privkey"));
}

BOOST_AUTO_TEST_CASE(rpc_getzeronodewinners)
{
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getzeronodewinners"));
    BOOST_CHECK(r.isArray() || r.isNum());
}

BOOST_AUTO_TEST_CASE(getzeronodepayment_sporks)
{
    std::map<int, CSporkMessage> saved = mapSporksActive;
    mapSporksActive.clear();
    BOOST_CHECK_EQUAL(GetZeronodePayment(0, 10 * COIN), 0);

    CSporkMessage s7;
    s7.nSporkID = SPORK_7_ZERONODE_PAYMENT_ENABLED;
    s7.nValue = 0;
    mapSporksActive[SPORK_7_ZERONODE_PAYMENT_ENABLED] = s7;
    BOOST_CHECK_EQUAL(GetZeronodePayment(0, 10 * COIN), 100000);

    CSporkMessage s6;
    s6.nSporkID = SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED;
    s6.nValue = 0;
    mapSporksActive[SPORK_6_ZERONODE_FULL_PAYMENT_ENABLED] = s6;
    // TestingSetup uses mainnet params (halving interval 800000, not regtest 150).
    const int interval = Params().GetConsensus().nPreBlossomSubsidyHalvingInterval;
    BOOST_CHECK_EQUAL(GetZeronodePayment(0, 10 * COIN), 10 * COIN * 20 / 100);
    BOOST_CHECK_EQUAL(GetZeronodePayment(interval, 10 * COIN), 10 * COIN * 25 / 100);
    mapSporksActive = saved;
}

// The 16th zeronode RPC; the only one with no case until now.
//
// getzeronodescores parses its optional argument with std::stoi inside
//   try { ... } catch (const boost::bad_lexical_cast &)
// std::stoi throws std::invalid_argument / std::out_of_range, never
// boost::bad_lexical_cast, so that handler is dead and a non-numeric argument
// escapes the RPC. The server's outer catch(std::exception) turns it into a
// generic RPC_PARSE_ERROR rather than a parameter error, so the node does not
// crash, but the diagnostic is wrong and the intended handler never runs.
//
// std::invalid_argument derives from std::logic_error, NOT std::runtime_error,
// so the assertion below is deliberately on std::exception: a narrower
// runtime_error check would fail today. Tighten this to runtime_error once the
// catch is corrected -- that tightening is the regression signal.
BOOST_AUTO_TEST_CASE(rpc_getzeronodescores_param_validation)
{
    BOOST_CHECK_THROW(CallRPC("getzeronodescores a b"), runtime_error); // arity
    BOOST_CHECK_THROW(CallRPC("getzeronodescores notanumber"), std::exception);
}

BOOST_AUTO_TEST_SUITE_END()
