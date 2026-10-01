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
#include "zeronode/swifttx.h"
#include "zeronode/zeronode.h"
#include "zeronode/zeronodeconfig.h"
#include "wallet/wallet.h"

#include <boost/algorithm/string.hpp>
#include <boost/filesystem.hpp>
#include <boost/filesystem/fstream.hpp>
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

// A fresh node has not synced the zeronode list; startalias reports that instead of starting.
BOOST_AUTO_TEST_CASE(rpc_startalias_reports_list_sync)
{
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("startalias zn1"));
    const std::string msg = find_value(r.get_obj(), "result").get_str();
    BOOST_CHECK(boost::starts_with(msg, "Zeronode list syncing, please wait. Current status: "));
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

// Amount constants written as decimal fractions of COIN fold to exact integers at
// compile time; a rounding change would fail the build.
static_assert(nHighTransactionFeeWarning == 1000000, "0.01 * COIN");
static_assert(DEFAULT_TRANSACTION_MAXFEE == 10000000, "0.1 * COIN");
static_assert(nHighTransactionMaxFeeWarning == 100000000, "100 * 0.01 * COIN");
static_assert(ZERONODE_COLLATERAL_CHECK_VALUE == 999999000000LL, "9999.99 ZER");
static_assert(SWIFTTX_MIN_COLLATERAL_FEE == 10000, "0.0001 ZER");

// Integer forms of former floating-point expressions: identical results over the
// whole range of zeronode counts and heights the network can reach.
BOOST_AUTO_TEST_CASE(zeronode_integer_math)
{
    for (int n = 0; n <= 200000; ++n) {
        BOOST_REQUIRE_EQUAL(ZeronodeCountWithMargin(n), int(n * 1.25));
        for (int nHeight : {0, 1, 1000, 2500000, 50000000}) {
            BOOST_REQUIRE_EQUAL(ZeronodePaymentWindowStart(nHeight, n), int(nHeight - (n * 1.25)));
        }
    }
    BOOST_CHECK_EQUAL(ZERONODE_COLLATERAL_CHECK_VALUE, CAmount(9999.99 * COIN));
    BOOST_CHECK_EQUAL(ZERONODE_COLLATERAL_CHECK_VALUE, CAmount(999999000000LL));
    BOOST_CHECK_EQUAL(SWIFTTX_MIN_COLLATERAL_FEE, CAmount(COIN * 0.0001));
    BOOST_CHECK_EQUAL(SWIFTTX_MIN_COLLATERAL_FEE, CAmount(10000));
    BOOST_CHECK_EQUAL(CAmount(COIN / 10), CAmount(0.1 * COIN));
}

// Zeronode port rule: mainnet requires the mainnet default port, testnet and regtest refuse it.
// The network comes from -testnet and -regtest, so each case sets those arguments.
class ScopedNetworkArgs
{
    std::map<std::string, std::string> saved;
public:
    explicit ScopedNetworkArgs(const std::string& flag) : saved(mapArgs)
    {
        mapArgs.erase("-testnet");
        mapArgs.erase("-regtest");
        if (!flag.empty()) mapArgs[flag] = "1";
    }
    ~ScopedNetworkArgs() { mapArgs = saved; }
};

BOOST_AUTO_TEST_CASE(zeronode_port_rule)
{
    BOOST_CHECK_EQUAL(ZeronodeMainnetPort(), 23801);
    {
        ScopedNetworkArgs net("");
        BOOST_CHECK(IsValidZeronodePort(23801));
        for (int port : {23802, 23803, 8233, 0})
            BOOST_CHECK(!IsValidZeronodePort(port));
    }
    for (const std::string flag : {"-testnet", "-regtest"}) {
        ScopedNetworkArgs net(flag);
        BOOST_CHECK(!IsValidZeronodePort(23801));
        for (int port : {23802, 23803, 8233})
            BOOST_CHECK(IsValidZeronodePort(port));
    }
}

// zeronode.conf lines are checked against the rule when the file is read at startup.
static bool ReadZeronodeConf(int port, std::string& strErr, int& nEntries)
{
    boost::filesystem::path path = boost::filesystem::temp_directory_path() / boost::filesystem::unique_path("zeronode-%%%%%%%%.conf");
    {
        boost::filesystem::ofstream f(path);
        f << "zn1 127.0.0.1:" << port << " 93HaYBVUCYjEMeeH1Y4sBGLALQZE1Yc1K64xiqgX37tGBDQL8Xg "
          << std::string(64, '0') << " 0\n";
    }
    std::string savedConf = mapArgs.count("-znconf") ? mapArgs["-znconf"] : "";
    mapArgs["-znconf"] = path.string();
    CZeronodeConfig config;
    bool fRead = config.read(strErr);
    nEntries = (int)config.getEntries().size();
    if (savedConf.empty()) mapArgs.erase("-znconf"); else mapArgs["-znconf"] = savedConf;
    boost::filesystem::remove(path);
    return fRead;
}

BOOST_AUTO_TEST_CASE(zeronode_conf_port)
{
    std::string strErr;
    int nEntries = 0;
    {
        ScopedNetworkArgs net("");
        BOOST_CHECK(ReadZeronodeConf(23801, strErr, nEntries));
        BOOST_CHECK_EQUAL(nEntries, 1);
        BOOST_CHECK(!ReadZeronodeConf(23802, strErr, nEntries));
        BOOST_CHECK(strErr.find("(must be 23801 for mainnet)") != std::string::npos);
    }
    {
        ScopedNetworkArgs net("-regtest");
        BOOST_CHECK(!ReadZeronodeConf(23801, strErr, nEntries));
        BOOST_CHECK(strErr.find("(23801 could be used only on mainnet)") != std::string::npos);
        BOOST_CHECK(ReadZeronodeConf(23803, strErr, nEntries));
        BOOST_CHECK_EQUAL(nEntries, 1);
    }
}

// A signed broadcast from a peer passes CheckAndUpdate only on an allowed port; a refused
// port is rejected without a misbehavior score.
static bool CheckBroadcastPort(int port, int& nDos)
{
    CKey keyCollateral, keyZeronode;
    keyCollateral.MakeNewKey(true);
    keyZeronode.MakeNewKey(true);
    CService service(("1.2.3.4:" + std::to_string(port)).c_str());
    CTxIn vin(COutPoint(uint256S("01"), 0));
    CZeronodeBroadcast znb(service, vin, keyCollateral.GetPubKey(), keyZeronode.GetPubKey(), PROTOCOL_VERSION);
    BOOST_REQUIRE(znb.Sign(keyCollateral));
    nDos = 0;
    return znb.CheckAndUpdate(nDos);
}

BOOST_AUTO_TEST_CASE(zeronode_broadcast_port)
{
    int nDos = 0;
    {
        ScopedNetworkArgs net("");
        BOOST_CHECK(CheckBroadcastPort(23801, nDos));
        BOOST_CHECK(!CheckBroadcastPort(23802, nDos));
        BOOST_CHECK_EQUAL(nDos, 0);
    }
    {
        ScopedNetworkArgs net("-regtest");
        BOOST_CHECK(!CheckBroadcastPort(23801, nDos));
        BOOST_CHECK_EQUAL(nDos, 0);
        BOOST_CHECK(CheckBroadcastPort(23803, nDos));
    }
}

BOOST_AUTO_TEST_SUITE_END()
