#if defined(HAVE_CONFIG_H)
#include "config/bitcoin-config.h"
#endif

#include "arith_uint256.h"
#include "chainparams.h"
#include "consensus/validation.h"
#include "crypto/equihash.h"
#include "pow/tromp/equi.h"   // WN / WK the vendored solver is compiled for
#include "main.h"
#include "miner.h"
#include "pow.h"
#include "primitives/block.h"
#include "script/script.h"
#include "streams.h"
#include "test/test_bitcoin.h"
#include "uint256.h"
#include "version.h"

#include <memory>

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

struct MinerRegtestSetup : public TestingSetup {
    MinerRegtestSetup() : TestingSetup(CBaseChainParams::REGTEST) {}
};

BOOST_FIXTURE_TEST_SUITE(miner_tests, MinerRegtestSetup)

static void MineOneRegtestBlock(CScript scriptPubKey)
{
    const CChainParams& chainparams = Params();
    const unsigned int n = chainparams.GetConsensus().nEquihashN;
    const unsigned int k = chainparams.GetConsensus().nEquihashK;
    BOOST_REQUIRE_EQUAL(n, 48u);
    BOOST_REQUIRE_EQUAL(k, 5u);

    std::unique_ptr<CBlockTemplate> pblocktemplate(CreateNewBlock(chainparams, scriptPubKey));
    BOOST_REQUIRE(pblocktemplate);
    CBlock* pblock = &pblocktemplate->block;

    unsigned int nExtraNonce = 0;
    {
        LOCK(cs_main);
        IncrementExtraNonce(pblock, chainActive.Tip(), nExtraNonce);
    }

    CEquihashInput I{*pblock};
    CDataStream ss(SER_NETWORK, PROTOCOL_VERSION);
    ss << I;
    EhHashState eh_state = EhPrefixState(n, k, (unsigned char*)&ss[0], ss.size());

    bool found = false;
    while (!found) {
        pblock->nNonce = ArithToUint256(UintToArith256(pblock->nNonce) + 1);
        EhHashState curr_state = eh_state;
        ub_update(curr_state.get(), pblock->nNonce.begin(), pblock->nNonce.size());
        std::function<bool(std::vector<unsigned char>)> validBlock =
            [&](std::vector<unsigned char> soln) {
                pblock->nSolution = soln;
                return CheckProofOfWork(pblock->GetHash(), pblock->nBits, chainparams.GetConsensus());
            };
        found = EhOptimisedSolveUncancellable(n, k, curr_state, validBlock);
    }

    BOOST_REQUIRE(CheckEquihashSolution(pblock, chainparams.GetConsensus()));
    CValidationState state;
    BOOST_REQUIRE_MESSAGE(ProcessNewBlock(state, chainparams, NULL, pblock, true, NULL),
                          state.GetRejectReason());
}

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

// Pins the -equihashsolver default and the parameter guard that protects it.
//
// The default is "tromp": measured 5.69x faster at 3.3 GB peak against the
// reference solver's 7.15 GB at (192,7) (ZeroPerf M-EQ-TROMP-SPEEDUP,
// M-EQ-PEAK-TROMP, M-EQ-PEAK-DEFAULT), and the shipped zero.conf templates
// have specified tromp for years.
//
// The guard matters because the vendored tromp solver is compiled for fixed
// WN/WK (pow/tromp/equi.h) and cannot solve any other parameter set. Before
// the default changed, regtest (48,5) never reached that branch; now it would,
// so BitcoinMiner falls back to "default" off (192,7). Without this test a
// silent revert of either half goes unnoticed.
BOOST_AUTO_TEST_CASE(equihashsolver_default_and_param_guard)
{
    // The compiled-in tromp parameters are what the guard compares against.
    BOOST_CHECK_EQUAL(WN, 192);
    BOOST_CHECK_EQUAL(WK, 7);

    // Default when the user sets nothing. Mirrors BitcoinMiner's GetArg.
    mapArgs.erase("-equihashsolver");
    BOOST_CHECK_EQUAL(GetArg("-equihashsolver", "tromp"), "tromp");

    // Explicit selection still works in both directions.
    mapArgs["-equihashsolver"] = "default";
    BOOST_CHECK_EQUAL(GetArg("-equihashsolver", "tromp"), "default");
    mapArgs["-equihashsolver"] = "tromp";
    BOOST_CHECK_EQUAL(GetArg("-equihashsolver", "tromp"), "tromp");
    mapArgs.erase("-equihashsolver");

    // The guard: tromp is only usable at its compiled parameters. Regtest is
    // (48,5), so a tromp default must fall back there.
    const auto& regtest = Params(CBaseChainParams::REGTEST).GetConsensus();
    const unsigned int rn = regtest.nEquihashN, rk = regtest.nEquihashK;
    BOOST_CHECK(!(rn == WN && rk == WK));

    std::string solver = "tromp";
    if (solver == "tromp" && !(rn == WN && rk == WK)) solver = "default";
    BOOST_CHECK_EQUAL(solver, "default");

    // Mainnet is (192,7), so tromp is kept.
    const auto& mainnet = Params(CBaseChainParams::MAIN).GetConsensus();
    const unsigned int mn = mainnet.nEquihashN, mk = mainnet.nEquihashK;
    BOOST_CHECK_EQUAL(mn, static_cast<unsigned int>(WN));
    BOOST_CHECK_EQUAL(mk, static_cast<unsigned int>(WK));

    solver = "tromp";
    if (solver == "tromp" && !(mn == WN && mk == WK)) solver = "default";
    BOOST_CHECK_EQUAL(solver, "tromp");
}

BOOST_AUTO_TEST_SUITE_END()

#endif // ENABLE_MINING
