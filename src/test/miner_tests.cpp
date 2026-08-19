#if defined(HAVE_CONFIG_H)
#include "config/bitcoin-config.h"
#endif

#include "arith_uint256.h"
#include "chainparams.h"
#include "consensus/validation.h"
#include "crypto/equihash.h"
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

    crypto_generichash_blake2b_state eh_state;
    EhInitialiseState(n, k, eh_state);
    CEquihashInput I{*pblock};
    CDataStream ss(SER_NETWORK, PROTOCOL_VERSION);
    ss << I;
    crypto_generichash_blake2b_update(&eh_state, (unsigned char*)&ss[0], ss.size());

    bool found = false;
    while (!found) {
        pblock->nNonce = ArithToUint256(UintToArith256(pblock->nNonce) + 1);
        crypto_generichash_blake2b_state curr_state = eh_state;
        crypto_generichash_blake2b_update(&curr_state, pblock->nNonce.begin(), pblock->nNonce.size());
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

BOOST_AUTO_TEST_SUITE_END()

#endif // ENABLE_MINING
