// Copyright 2026 Zero Developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php.

#include "rpc/server.h"
#include "rpc/client.h"
#include "wallet/wallet.h"
#include "util.h"

#include "test/test_bitcoin.h"

#include <boost/algorithm/string.hpp>
#include <boost/test/unit_test.hpp>

#include <stdint.h>
#include <string>
#include <univalue.h>

using namespace std;

extern UniValue CallRPC(string args);
extern bool initWitnessesBuilt;
extern bool fBuildingWitnessCache;
extern uint64_t GetGetAllDataSortKeyCollisionCount();
extern void ResetGetAllDataSortKeyCollisionCount();
extern void ResetRpcDataContinueState();
extern void SetGetAllDataInFlightForTest(bool inFlight);
extern bool IsGetAllDataTxTooOld(int64_t blockTime, int64_t now, int dayDays);

/** Like CallRPC, but goes through CRPCTable::execute (warmup / S5 / witness-cache gates). */
static UniValue CallRPCExecute(string args)
{
    vector<string> vArgs;
    boost::split(vArgs, args, boost::is_any_of(" \t"));
    string strMethod = vArgs[0];
    vArgs.erase(vArgs.begin());
    for (size_t i = 0; i < vArgs.size(); i++) {
        if (vArgs[i] == "\"\"") {
            vArgs[i] = "";
        }
    }
    UniValue params = RPCConvertValues(strMethod, vArgs);
    BOOST_CHECK(tableRPC[strMethod]);
    try {
        return tableRPC.execute(strMethod, params);
    } catch (const UniValue& objError) {
        throw runtime_error(find_value(objError, "message").get_str());
    }
}

static void CheckRPCExecuteThrows(const string& rpcString, const string& expectedErrorMessage)
{
    try {
        CallRPCExecute(rpcString);
        BOOST_FAIL("Should have caused an error");
    } catch (const runtime_error& e) {
        BOOST_CHECK_EQUAL(expectedErrorMessage, e.what());
    }
}

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
    ResetRpcDataContinueState();
    mapArgs["-rpcdatacontinue"] = "0";
    BOOST_CHECK_THROW(CallRPC("getalldata 0 0 0 0 0"), runtime_error);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 0"));
    BOOST_CHECK(r.isObject());
}

// S4 / param matrix: datatype 0/1/2, nCount clamp, 4-arg watchonly (Zerowallet shape).
BOOST_AUTO_TEST_CASE(rpc_getalldata_ncount_datatype_watchonly)
{
    ResetRpcDataContinueState();
    mapArgs["-rpcdatacontinue"] = "0";
    UniValue r;

    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 1"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK(r.exists("addressbalance"));
    BOOST_CHECK(r.exists("listtransactions"));
    BOOST_CHECK(r["listtransactions"].isArray());

    ResetRpcDataContinueState();
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 2"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK(r.exists("listtransactions"));
    BOOST_CHECK(r["listtransactions"].isArray());

    // nCount <= 0 clamps to 200 (empty wallet => length 0, still accepted)
    ResetRpcDataContinueState();
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 0 0 0"));
    BOOST_CHECK(r["listtransactions"].isArray());
    BOOST_CHECK(r["listtransactions"].size() <= 200);

    ResetRpcDataContinueState();
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 0 0 -1"));
    BOOST_CHECK(r["listtransactions"].isArray());

    ResetRpcDataContinueState();
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 0 2 1"));
    BOOST_CHECK(r["listtransactions"].size() <= 1);

    // Zerowallet 4-arg form: datatype, type, count, watchonly
    ResetRpcDataContinueState();
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 0 2 50 true"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK(r.exists("listtransactions"));

    ResetRpcDataContinueState();
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 0 2 50 false"));
    BOOST_CHECK(r.isObject());

    mapArgs["-rpcdatacontinue"] = "0";
    ResetRpcDataContinueState();
}

// S5: gate is in CRPCTable::execute (CallRPC bypasses it).
BOOST_AUTO_TEST_CASE(rpc_getalldata_s5_witness_gate)
{
    ResetRpcDataContinueState();
    mapArgs["-rpcdatacontinue"] = "0";

    // execute() also rejects while warmup; TestingSetup never finishes warmup.
    if (RPCIsInWarmup(nullptr))
        SetRPCWarmupFinished();

    const bool saved = initWitnessesBuilt;
    initWitnessesBuilt = false;

    CheckRPCExecuteThrows("getalldata 1",
        "RPC Command disabled until witnesses are built.");
    CheckRPCExecuteThrows("z_sendmany",
        "RPC Command disabled until witnesses are built.");

    // Other RPCs still allowed once warmup is done.
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPCExecute("getsupply 0"));
    BOOST_CHECK(r.isObject());

    initWitnessesBuilt = true;
    ResetRpcDataContinueState();
    BOOST_CHECK_NO_THROW(r = CallRPCExecute("getalldata 1"));
    BOOST_CHECK(r.isObject());

    initWitnessesBuilt = saved;
    mapArgs["-rpcdatacontinue"] = "0";
    ResetRpcDataContinueState();
}

BOOST_AUTO_TEST_CASE(rpc_getalldata_data_continue)
{
    ResetRpcDataContinueState();
    mapArgs["-rpcdatacontinue"] = "0";
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 1"));
    BOOST_CHECK(r.isObject());

    mapArgs["-rpcdatacontinue"] = "3600";
    try {
        CallRPC("getalldata 1");
        BOOST_FAIL("expected RPC_DATA_CONTINUE");
    } catch (const runtime_error& e) {
        BOOST_CHECK_EQUAL(string(e.what()), "rpc_data_continue");
    }

    mapArgs["-rpcdatacontinue"] = "0";
    ResetRpcDataContinueState();
}

// S6 in-flight: second getalldata while gate held returns soft continue.
BOOST_AUTO_TEST_CASE(rpc_getalldata_s6_inflight)
{
    ResetRpcDataContinueState();
    mapArgs["-rpcdatacontinue"] = "0";
    SetGetAllDataInFlightForTest(true);
    try {
        CallRPC("getalldata 1");
        BOOST_FAIL("expected RPC_DATA_CONTINUE while in-flight");
    } catch (const runtime_error& e) {
        BOOST_CHECK_EQUAL(string(e.what()), "rpc_data_continue");
    }
    SetGetAllDataInFlightForTest(false);
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getalldata 1"));
    BOOST_CHECK(r.isObject());
    mapArgs["-rpcdatacontinue"] = "0";
    ResetRpcDataContinueState();
}

// S7: walks use const refs / pointers; assert stable shape and repeatable success
// (no dedicated "zero copies" assert). Empty wallet is enough for crash/shape.
BOOST_AUTO_TEST_CASE(rpc_getalldata_s7_shape)
{
    ResetRpcDataContinueState();
    mapArgs["-rpcdatacontinue"] = "0";
    UniValue a, b;
    BOOST_CHECK_NO_THROW(a = CallRPC("getalldata 0 2 50"));
    ResetRpcDataContinueState();
    BOOST_CHECK_NO_THROW(b = CallRPC("getalldata 0 2 50"));
    BOOST_CHECK(a.isObject());
    BOOST_CHECK(b.isObject());
    BOOST_CHECK(a.exists("listtransactions"));
    BOOST_CHECK(b.exists("listtransactions"));
    BOOST_CHECK(a.exists("addressbalance"));
    BOOST_CHECK(b.exists("addressbalance"));
    BOOST_CHECK_EQUAL(a["listtransactions"].size(), b["listtransactions"].size());

    // listsinceblock also uses const CWalletTx& after S7 follow-on
    UniValue ls;
    BOOST_CHECK_NO_THROW(ls = CallRPC("listsinceblock"));
    BOOST_CHECK(ls.isObject());
    BOOST_CHECK(ls.exists("transactions"));

    mapArgs["-rpcdatacontinue"] = "0";
    ResetRpcDataContinueState();
}

BOOST_AUTO_TEST_CASE(rpc_getalldata_w3_day_cutoff_helper)
{
    // W3: 7-day window -- block 8 days ago is too old; 6 days ago is not
    const int64_t now = 1700000000;
    const int64_t day = 60 * 60 * 24;
    BOOST_CHECK(IsGetAllDataTxTooOld(now - 8 * day, now, 7));
    BOOST_CHECK(!IsGetAllDataTxTooOld(now - 6 * day, now, 7));
    BOOST_CHECK(!IsGetAllDataTxTooOld(now, now, 7));
}

BOOST_AUTO_TEST_CASE(rpc_getalldata_w2_collision_counter_reset)
{
    ResetGetAllDataSortKeyCollisionCount();
    BOOST_CHECK_EQUAL(GetGetAllDataSortKeyCollisionCount(), 0);
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

// Witness / IBD-defer corner cases and DoS gates (FIX-WAL-WITNESS-*)
BOOST_AUTO_TEST_CASE(rpc_witness_building_cache_blocks_all_rpc)
{
    // While fBuildingWitnessCache: wallet/spend/data blocked (-33); status/ops allowlisted.
    if (RPCIsInWarmup(nullptr))
        SetRPCWarmupFinished();
    const bool savedBuild = fBuildingWitnessCache;
    const bool savedInit = initWitnessesBuilt;
    initWitnessesBuilt = true;
    fBuildingWitnessCache = true;
    // TST-08 / PIR-03: spend path must see -33 (message), not only -31.
    CheckRPCExecuteThrows("z_sendmany",
        "RPC interface disabled while building witness cache. Check debug.log for progress.");
    CheckRPCExecuteThrows("getsupply 0",
        "RPC interface disabled while building witness cache. Check debug.log for progress.");
    CheckRPCExecuteThrows("getalldata 1",
        "RPC interface disabled while building witness cache. Check debug.log for progress.");
    CheckRPCExecuteThrows("getwalletinfo",
        "RPC interface disabled while building witness cache. Check debug.log for progress.");
    fBuildingWitnessCache = savedBuild;
    initWitnessesBuilt = savedInit;
}

BOOST_AUTO_TEST_CASE(rpc_witness_building_cache_allows_status_rpc)
{
    if (RPCIsInWarmup(nullptr))
        SetRPCWarmupFinished();
    const bool savedBuild = fBuildingWitnessCache;
    const bool savedInit = initWitnessesBuilt;
    initWitnessesBuilt = true;
    fBuildingWitnessCache = true;
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPCExecute("getblockcount"));
    BOOST_CHECK(r.isNum());
    BOOST_CHECK_NO_THROW(r = CallRPCExecute("getblockchaininfo"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK_NO_THROW(r = CallRPCExecute("getnetworkinfo"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK_NO_THROW(r = CallRPCExecute("help"));
    // stop is allowlisted at the gate; do not invoke actor (would shut down the process).
    BOOST_CHECK(tableRPC["stop"] != nullptr);
    fBuildingWitnessCache = savedBuild;
    initWitnessesBuilt = savedInit;
}

BOOST_AUTO_TEST_CASE(rpc_walletinfo_note_inventory_fields)
{
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPC("getwalletinfo"));
    BOOST_CHECK(r.isObject());
    BOOST_CHECK(r.exists("txcount"));
    BOOST_CHECK(r.exists("note_tx_count"));
    BOOST_CHECK(r.exists("sprout_note_count"));
    BOOST_CHECK(r.exists("sapling_note_count"));
    BOOST_CHECK(r["note_tx_count"].get_int() >= 0);
    BOOST_CHECK(r["sprout_note_count"].get_int() >= 0);
    BOOST_CHECK(r["sapling_note_count"].get_int() >= 0);
}

BOOST_AUTO_TEST_CASE(wallet_witness_ibd_defer_arg)
{
    mapArgs.erase("-walletwitness");
    BOOST_CHECK(!CWallet::IsIBDWitnessDeferred());
    mapArgs["-walletwitness"] = "ibd-defer";
    BOOST_CHECK(CWallet::IsIBDWitnessDeferred());
    mapArgs["-walletwitness"] = "rebuild";
    BOOST_CHECK(!CWallet::IsIBDWitnessDeferred());
    mapArgs["-walletwitness"] = "default";
    BOOST_CHECK(!CWallet::IsIBDWitnessDeferred());
    mapArgs.erase("-walletwitness");
}

BOOST_AUTO_TEST_CASE(wallet_witness_note_arg)
{
    mapArgs.erase("-walletwitnessnote");
    BOOST_CHECK(!CWallet::IsWitnessNoteIndexEnabled());
    mapArgs["-walletwitnessnote"] = "1";
    BOOST_CHECK(CWallet::IsWitnessNoteIndexEnabled());
    mapArgs["-walletwitnessnote"] = "0";
    BOOST_CHECK(!CWallet::IsWitnessNoteIndexEnabled());
    mapArgs.erase("-walletwitnessnote");
}

BOOST_AUTO_TEST_CASE(rpc_witness_gate_allows_walletinfo_when_unbuilt)
{
    // Monitoring must remain available during ibd-defer (getalldata gated; getwalletinfo not).
    if (RPCIsInWarmup(nullptr))
        SetRPCWarmupFinished();
    const bool saved = initWitnessesBuilt;
    initWitnessesBuilt = false;
    UniValue r;
    BOOST_CHECK_NO_THROW(r = CallRPCExecute("getwalletinfo"));
    BOOST_CHECK(r.isObject());
    CheckRPCExecuteThrows("getalldata 1",
        "RPC Command disabled until witnesses are built.");
    initWitnessesBuilt = saved;
}

BOOST_AUTO_TEST_SUITE_END()
