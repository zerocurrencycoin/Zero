// Copyright (c) 2015 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php .

#include "main.h"
#include "pow.h"
#include "util.h"
#include "utiltest.h"
#include "test/test_bitcoin.h"

#include <boost/test/unit_test.hpp>

using namespace std;

BOOST_FIXTURE_TEST_SUITE(pow_tests, BasicTestingSetup)

/* Test calculation of next difficulty target with no constraints applying */
BOOST_AUTO_TEST_CASE(get_next_work)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();
    // Zero: 120s pre-Blossom; Zcash: 150s
    BOOST_CHECK(params.PoWTargetSpacing(0) == 120 || params.PoWTargetSpacing(0) == 150);

    int64_t nLastRetargetTime = 1000000000; // NOTE: Not an actual block time
    int64_t nThisTime = 1000003570;
    arith_uint256 bnAvg;
    bnAvg.SetCompact(0x1d00ffff);
    uint32_t expected = (params.PoWTargetSpacing(0) == 150) ? 0x1d011998u : 0x1d012feeu; // Zero 120s
    BOOST_CHECK_EQUAL(expected,
                      CalculateNextWorkRequired(bnAvg, nThisTime, nLastRetargetTime, params, 0));
}


BOOST_AUTO_TEST_CASE(get_next_work_blossom)
{
    const Consensus::Params& params = RegtestActivateBlossom(true);
    // Zero: 60s post-Blossom; Zcash: 75s
    BOOST_CHECK(params.PoWTargetSpacing(0) == 60 || params.PoWTargetSpacing(0) == 75);

    int64_t nLastRetargetTime = 1000000000; // NOTE: Not an actual block time
    int64_t nThisTime = (params.PoWTargetSpacing(0) == 75) ? 1000001445 : 1000001156; // Zero: 17*60*1.133
    arith_uint256 bnAvg;
    bnAvg.SetCompact(0x1d00ffff);
    uint32_t result = CalculateNextWorkRequired(bnAvg, nThisTime, nLastRetargetTime, params, 0);
    BOOST_CHECK_GT(0x1d011998u, result);

    RegtestDeactivateBlossom();
}

/* Test the constraint on the upper bound for next work */
BOOST_AUTO_TEST_CASE(get_next_work_pow_limit)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();

    int64_t nLastRetargetTime = 1231006505;
    int64_t nThisTime = 1233061996;
    arith_uint256 bnAvg;
    bnAvg.SetCompact(0x1f07ffff);
    uint32_t expected = (params.PoWTargetSpacing(0) == 150) ? 0x1f07ffffu : 0x1f0a6665u; // Zero 120s
    BOOST_CHECK_EQUAL(expected,
                      CalculateNextWorkRequired(bnAvg, nThisTime, nLastRetargetTime, params, 0));
}

BOOST_AUTO_TEST_CASE(get_next_work_pow_limit_blossom)
{
    const Consensus::Params& params = RegtestActivateBlossom(true);

    int64_t nLastRetargetTime = 1231006505;
    int64_t nThisTime = 1233061996;
    arith_uint256 bnAvg;
    bnAvg.SetCompact(0x1f07ffff);
    BOOST_CHECK_EQUAL(0x1f07ffff,
                      CalculateNextWorkRequired(bnAvg, nThisTime, nLastRetargetTime, params, 0));

    RegtestDeactivateBlossom();
}

/* Test the constraint on the lower bound for actual time taken */
BOOST_AUTO_TEST_CASE(get_next_work_lower_limit_actual)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();

    int64_t nLastRetargetTime = 1000000000; // NOTE: Not an actual block time
    // 17*spacing*(1 - PoWMaxAdjustUp*PoWDampingFactor): 150s->917, 120s->734
    int64_t nThisTime = 1000000000 - (params.PoWTargetSpacing(0) == 150 ? 917 : 734);
    arith_uint256 bnAvg;
    bnAvg.SetCompact(0x1c05a3f4);
    uint32_t expected = (params.PoWTargetSpacing(0) == 150) ? 0x1c04bcebu : 0x1c05138eu; // Zero 120s
    BOOST_CHECK_EQUAL(expected,
                      CalculateNextWorkRequired(bnAvg, nThisTime, nLastRetargetTime, params, 0));
}

BOOST_AUTO_TEST_CASE(get_next_work_lower_limit_actual_blossom)
{
    const Consensus::Params& params = RegtestActivateBlossom(true);

    int64_t nLastRetargetTime = 1000000000; // NOTE: Not an actual block time
    // 17*spacing*(1 - factor): 75s->458, 60s->367
    int64_t nThisTime = 1000000000 - (params.PoWTargetSpacing(0) == 75 ? 458 : 367);
    arith_uint256 bnAvg;
    bnAvg.SetCompact(0x1c05a3f4);
    uint32_t expected = (params.PoWTargetSpacing(0) == 75) ? 0x1c04bcebu : 0x1c04bbc9u; // Zero 60s
    BOOST_CHECK_EQUAL(expected,
                      CalculateNextWorkRequired(bnAvg, nThisTime, nLastRetargetTime, params, 0));

    RegtestDeactivateBlossom();
}

/* Test the constraint on the upper bound for actual time taken */
BOOST_AUTO_TEST_CASE(get_next_work_upper_limit_actual)
{
    SelectParams(CBaseChainParams::MAIN);
    const Consensus::Params& params = Params().GetConsensus();

    int64_t nLastRetargetTime = 1000000000; // NOTE: Not an actual block time
    // 17*spacing*(1 + maxAdjustDown*PoWDampingFactor): 150s->5815, 120s->4652
    int64_t nThisTime = 1000000000 + (params.PoWTargetSpacing(0) == 150 ? 5815 : 4652);
    arith_uint256 bnAvg;
    bnAvg.SetCompact(0x1c387f6f);
    uint32_t expected = (params.PoWTargetSpacing(0) == 150) ? 0x1c4a93bbu : 0x1c497276u; // Zero 120s
    BOOST_CHECK_EQUAL(expected,
                      CalculateNextWorkRequired(bnAvg, nThisTime, nLastRetargetTime, params, 0));
}

BOOST_AUTO_TEST_CASE(get_next_work_upper_limit_actual_blossom)
{
    const Consensus::Params& params = RegtestActivateBlossom(true);

    int64_t nLastRetargetTime = 1000000000; // NOTE: Not an actual block time
    // 17*spacing*(1 + factor): 75s->2908, 60s->2326
    int64_t nThisTime = 1000000000 + (params.PoWTargetSpacing(0) == 75 ? 2908 : 2326);
    arith_uint256 bnAvg;
    bnAvg.SetCompact(0x1c387f6f);
    uint32_t expected = (params.PoWTargetSpacing(0) == 75) ? 0x1c4a93bbu : 0x1c4a8e0fu; // Zero 60s
    BOOST_CHECK_EQUAL(expected,
                      CalculateNextWorkRequired(bnAvg, nThisTime, nLastRetargetTime, params, 0));

    RegtestDeactivateBlossom();
}

void GetBlockProofEquivalentTimeImpl(const Consensus::Params& params) {
    std::vector<CBlockIndex> blocks(10000);
    for (int i = 0; i < 10000; i++) {
        blocks[i].pprev = i ? &blocks[i - 1] : NULL;
        blocks[i].nHeight = i;
        blocks[i].nTime = i ? blocks[i - 1].nTime + params.PoWTargetSpacing(i) : 1269211443;
        blocks[i].nBits = 0x207fffff; /* target 0x7fffff000... */
        blocks[i].nChainWork = i ? blocks[i - 1].nChainWork + GetBlockProof(blocks[i - 1]) : arith_uint256(0);
    }

    for (int j = 0; j < 1000; j++) {
        CBlockIndex *p1 = &blocks[GetRand(10000)];
        CBlockIndex *p2 = &blocks[GetRand(10000)];
        CBlockIndex *p3 = &blocks[GetRand(10000)];

        int64_t tdiff = GetBlockProofEquivalentTime(*p1, *p2, *p3, params);
        BOOST_CHECK_EQUAL(tdiff, p1->GetBlockTime() - p2->GetBlockTime());
    }
}

BOOST_AUTO_TEST_CASE(GetBlockProofEquivalentTime_test)
{
    SelectParams(CBaseChainParams::MAIN);
    GetBlockProofEquivalentTimeImpl(Params().GetConsensus());
}

BOOST_AUTO_TEST_CASE(GetBlockProofEquivalentTime_test_blossom)
{
    GetBlockProofEquivalentTimeImpl(RegtestActivateBlossom(true));
    RegtestDeactivateBlossom();
}

BOOST_AUTO_TEST_SUITE_END()
