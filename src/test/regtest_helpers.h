#ifndef BITCOIN_TEST_REGTEST_HELPERS_H
#define BITCOIN_TEST_REGTEST_HELPERS_H

// Regtest (48,5) block helpers shared by Boost suites: solve a block live,
// submit it, step the tip back, corrupt a solution. Mining builds only.

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
#include "version.h"

#include <functional>
#include <memory>

#include <boost/test/unit_test.hpp>

#ifdef ENABLE_MINING

struct RegtestSetup : public TestingSetup {
    RegtestSetup() : TestingSetup(CBaseChainParams::REGTEST) {}
};

// A block on the current tip with a valid (48,5) solution, not yet submitted.
inline CBlock SolveRegtestBlock(CScript scriptPubKey)
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
    return *pblock;
}

inline CBlock MineOneRegtestBlock(CScript scriptPubKey)
{
    CBlock block = SolveRegtestBlock(scriptPubKey);
    CValidationState state;
    BOOST_REQUIRE_MESSAGE(ProcessNewBlock(state, Params(), NULL, &block, true, NULL),
                          state.GetRejectReason());
    return block;
}

// Disconnect the tip back to its parent while keeping its index entry valid:
// the state of a block accepted (BLOCK_VALID_TREE, data on disk) but not yet
// connected. Requires cs_main.
inline CBlockIndex* UnconnectTip()
{
    CBlockIndex* pindex = chainActive.Tip();
    CValidationState state;
    BOOST_REQUIRE(InvalidateBlock(state, Params(), pindex));
    BOOST_REQUIRE(ReconsiderBlock(state, pindex));
    BOOST_REQUIRE(chainActive.Tip() == pindex->pprev);
    BOOST_REQUIRE(pindex->IsValid(BLOCK_VALID_TREE));
    return pindex;
}

// Flip one byte of the Equihash solution. The block hash covers nSolution, so
// the copy no longer matches its index entry, and the solution is invalid.
inline CBlock WithCorruptSolution(const CBlock& block)
{
    CBlock bad = block;
    BOOST_REQUIRE(!bad.nSolution.empty());
    bad.nSolution[0] ^= 0x01;
    BOOST_REQUIRE(!CheckEquihashSolution(&bad, Params().GetConsensus()));
    return bad;
}

#endif // ENABLE_MINING

#endif // BITCOIN_TEST_REGTEST_HELPERS_H
