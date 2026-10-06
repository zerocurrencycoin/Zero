#if defined(HAVE_CONFIG_H)
#include "config/bitcoin-config.h"
#endif

#include "chainparams.h"
#include "miner.h"
#include "pow/tromp/equi.h"   // WN / WK the vendored solver is compiled for
#include "test/test_bitcoin.h"
#include "test/regtest_helpers.h"
#include "util.h"

#include <boost/test/unit_test.hpp>

#ifdef ENABLE_MINING

// Live CreateNewBlock -> Equihash (48,5) -> ProcessNewBlock on regtest.
//
// A frozen blockinfo[] table (extranonce + nonce per height) is how Bitcoin Core
// and early Zcash miner_tests extended a long chain without a solver in the
// test binary. That table is PoW-parameter-specific. Authoring one for Zero
// mainnet (192,7) would mean running OptimisedSolve once per height (on the
// order of a minute each) and storing nSolution, not a compact nonce. Use
// regtest (48,5) live solve instead.

BOOST_FIXTURE_TEST_SUITE(miner_tests, RegtestSetup)

BOOST_AUTO_TEST_CASE(CreateNewBlock_regtest_48_5)
{
    CScript scriptPubKey = CScript() << OP_TRUE;
    {
        LOCK(cs_main);
        BOOST_REQUIRE_EQUAL(chainActive.Height(), 0);
    }
    MineOneRegtestBlock(scriptPubKey);
    MineOneRegtestBlock(scriptPubKey);
    {
        LOCK(cs_main);
        BOOST_CHECK_EQUAL(chainActive.Height(), 2);
    }
}

// The solver the miner uses comes from SelectEquihashSolver, the same function
// these cases call, so a change to the default or to the (192,7) guard in
// miner.cpp shows up here.
BOOST_AUTO_TEST_CASE(equihash_solver_default_is_tromp_on_mainnet)
{
    BOOST_CHECK_EQUAL(std::string(DEFAULT_EQUIHASH_SOLVER), "tromp");
    mapArgs.erase("-equihashsolver");
    const auto& mainnet = Params(CBaseChainParams::MAIN).GetConsensus();
    BOOST_REQUIRE_EQUAL(mainnet.nEquihashN, static_cast<unsigned int>(WN));
    BOOST_REQUIRE_EQUAL(mainnet.nEquihashK, static_cast<unsigned int>(WK));
    BOOST_CHECK_EQUAL(SelectEquihashSolver(mainnet), "tromp");
}

BOOST_AUTO_TEST_CASE(equihash_solver_tromp_falls_back_off_its_parameters)
{
    const auto& regtest = Params(CBaseChainParams::REGTEST).GetConsensus();
    BOOST_REQUIRE(!(regtest.nEquihashN == WN && regtest.nEquihashK == WK));
    mapArgs.erase("-equihashsolver");
    BOOST_CHECK_EQUAL(SelectEquihashSolver(regtest), "default");
    mapArgs["-equihashsolver"] = "tromp";
    BOOST_CHECK_EQUAL(SelectEquihashSolver(regtest), "default");
    mapArgs.erase("-equihashsolver");
}

BOOST_AUTO_TEST_CASE(equihash_solver_explicit_and_unknown_values)
{
    const auto& mainnet = Params(CBaseChainParams::MAIN).GetConsensus();
    mapArgs["-equihashsolver"] = "default";
    BOOST_CHECK_EQUAL(SelectEquihashSolver(mainnet), "default");
    mapArgs["-equihashsolver"] = "tromp";
    BOOST_CHECK_EQUAL(SelectEquihashSolver(mainnet), "tromp");
    // Unknown names are empty, which init.cpp turns into a startup error
    // instead of the miner thread's assert.
    mapArgs["-equihashsolver"] = "bogus";
    BOOST_CHECK_EQUAL(SelectEquihashSolver(mainnet), "");
    mapArgs.erase("-equihashsolver");
}

BOOST_AUTO_TEST_SUITE_END()

#endif // ENABLE_MINING
