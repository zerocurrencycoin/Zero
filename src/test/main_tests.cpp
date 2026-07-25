// Copyright (c) 2014 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php .

#include "chainparams.h"
#include "main.h"

#include "test/test_bitcoin.h"

#include <boost/signals2/signal.hpp>
#include <boost/test/unit_test.hpp>


BOOST_FIXTURE_TEST_SUITE(main_tests, TestingSetup)

// 12.5 * COIN: subsidy at end of slow-start in upstream (Bitcoin/Zcash) model
const CAmount REFERENCE_INITIAL_SUBSIDY = 12.5 * COIN;

// Zero uses 10/10.8 ZER, no slow-start; runs Zero-specific tests instead of reference tests
static bool UsesReferenceSubsidyModel(const Consensus::Params& p) {
    return GetBlockSubsidy(p.nSubsidySlowStartInterval ? p.nSubsidySlowStartInterval : 1, p) == REFERENCE_INITIAL_SUBSIDY;
}

// Zero subsidy: integer zats -- 10 ZER pre-fee, 10.8 (108/10) post-fee, halving every 800k
static const CAmount SUBSIDY_POST_FEE = 108 * COIN / 10;

static void TestBlockSubsidyHalvingsZero(const Consensus::Params& consensusParams) {
    BOOST_CHECK_EQUAL(GetBlockSubsidy(0, consensusParams), 10 * COIN);
    BOOST_CHECK_EQUAL(GetBlockSubsidy(consensusParams.nFeeStartBlockHeight - 1, consensusParams), 10 * COIN);
    BOOST_CHECK_EQUAL(GetBlockSubsidy(consensusParams.nFeeStartBlockHeight, consensusParams), SUBSIDY_POST_FEE);
    BOOST_CHECK_EQUAL(GetBlockSubsidy(800000 - 1, consensusParams), SUBSIDY_POST_FEE);
    BOOST_CHECK_EQUAL(GetBlockSubsidy(800000, consensusParams), SUBSIDY_POST_FEE >> 1);
    BOOST_CHECK_EQUAL(GetBlockSubsidy(1600000, consensusParams), SUBSIDY_POST_FEE >> 2);
    BOOST_CHECK_EQUAL(GetBlockSubsidy(2400000, consensusParams), SUBSIDY_POST_FEE >> 3);
    BOOST_CHECK_EQUAL(GetBlockSubsidy(800000 * 64 - 1, consensusParams), 0);
}

static void TestFoundersRewardAmountZero() {
    // 7.5% = * 75 / 1000, trunc toward 0
    BOOST_CHECK_EQUAL(GetFoundersRewardAmount(SUBSIDY_POST_FEE), 81 * COIN / 100);
    BOOST_CHECK_EQUAL(GetFoundersRewardAmount(SUBSIDY_POST_FEE >> 1), 405 * COIN / 1000);
    BOOST_CHECK_EQUAL(GetFoundersRewardAmount(SUBSIDY_POST_FEE >> 2), 2025 * COIN / 10000);
    BOOST_CHECK_EQUAL(GetFoundersRewardAmount(SUBSIDY_POST_FEE >> 3), 10125 * COIN / 100000);
    BOOST_CHECK_EQUAL(GetFoundersRewardAmount(0), 0);
    // Truncation: not divisible by 1000
    BOOST_CHECK_EQUAL(GetFoundersRewardAmount(999), 74);
    BOOST_CHECK_EQUAL(GetFoundersRewardAmount(1000), 75);
}

static void TestSubsidyLimitZero(const Consensus::Params& consensusParams) {
    // Zero supply (~25.6M ZER) exceeds MAX_MONEY; validate each subsidy is in range
    int nHeight = 0;
    for (; nHeight < consensusParams.nFeeStartBlockHeight; nHeight++) {
        CAmount nSubsidy = GetBlockSubsidy(nHeight, consensusParams);
        BOOST_CHECK(MoneyRange(nSubsidy));
    }
    CAmount nSubsidy;
    do {
        nSubsidy = GetBlockSubsidy(nHeight, consensusParams);
        BOOST_CHECK(MoneyRange(nSubsidy));
        ++nHeight;
    } while (nSubsidy > 0);
}

static int GetTotalHalvings(const Consensus::Params& consensusParams) {
    // This assumes that BLOSSOM_POW_TARGET_SPACING_RATIO == 2
    // and treats blossom activation as a halving event
    return consensusParams.vUpgrades[Consensus::UPGRADE_BLOSSOM].nActivationHeight == Consensus::NetworkUpgrade::NO_ACTIVATION_HEIGHT ? 64 : 65;
}

static void TestBlockSubsidyHalvings(const Consensus::Params& consensusParams)
{
    bool blossomActive = false;
    int blossomActivationHeight = consensusParams.vUpgrades[Consensus::UPGRADE_BLOSSOM].nActivationHeight;
    int nHeight = consensusParams.nSubsidySlowStartInterval;
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, consensusParams), REFERENCE_INITIAL_SUBSIDY);
    CAmount nPreviousSubsidy = REFERENCE_INITIAL_SUBSIDY;
    for (int nHalvings = 1; nHalvings < GetTotalHalvings(consensusParams); nHalvings++) {
        if (blossomActive) {
            if (nHeight == blossomActivationHeight) {
                int preBlossomHeight = (nHalvings - 1) * consensusParams.nPreBlossomSubsidyHalvingInterval + consensusParams.SubsidySlowStartShift();
                nHeight += (preBlossomHeight - blossomActivationHeight) * Consensus::BLOSSOM_POW_TARGET_SPACING_RATIO;
            } else {
                nHeight += consensusParams.nPostBlossomSubsidyHalvingInterval;
            }
        } else {
            nHeight = nHalvings * consensusParams.nPreBlossomSubsidyHalvingInterval + consensusParams.SubsidySlowStartShift();
            if (consensusParams.NetworkUpgradeActive(nHeight, Consensus::UPGRADE_BLOSSOM)) {
                nHeight = blossomActivationHeight;
                blossomActive = true;
            }
        }
        BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight - 1, consensusParams), nPreviousSubsidy);
        CAmount nSubsidy = GetBlockSubsidy(nHeight, consensusParams);
        BOOST_CHECK(nSubsidy <= REFERENCE_INITIAL_SUBSIDY);
        BOOST_CHECK_EQUAL(nSubsidy, nPreviousSubsidy / 2);
        nPreviousSubsidy = nSubsidy;
    }
    BOOST_CHECK_EQUAL(GetBlockSubsidy(nHeight, consensusParams), 0);
}

static void TestBlockSubsidyHalvings(int nSubsidySlowStartInterval, int nPreBlossomSubsidyHalvingInterval, int blossomActivationHeight)
{
    Consensus::Params consensusParams;
    consensusParams.nSubsidySlowStartInterval = nSubsidySlowStartInterval;
    consensusParams.nPreBlossomSubsidyHalvingInterval = nPreBlossomSubsidyHalvingInterval;
    consensusParams.nPostBlossomSubsidyHalvingInterval = nPreBlossomSubsidyHalvingInterval * Consensus::BLOSSOM_POW_TARGET_SPACING_RATIO;
    consensusParams.vUpgrades[Consensus::UPGRADE_BLOSSOM].nActivationHeight = blossomActivationHeight;
    TestBlockSubsidyHalvings(consensusParams);
}

BOOST_AUTO_TEST_CASE(block_subsidy_test)
{
    const Consensus::Params& mainParams = Params(CBaseChainParams::MAIN).GetConsensus();
    if (UsesReferenceSubsidyModel(mainParams)) {
        TestBlockSubsidyHalvings(mainParams); // As in main
    TestBlockSubsidyHalvings(20000, Consensus::PRE_BLOSSOM_HALVING_INTERVAL, Consensus::NetworkUpgrade::NO_ACTIVATION_HEIGHT); // Pre-Blossom
    TestBlockSubsidyHalvings(50, 150, 80); // As in regtest
    TestBlockSubsidyHalvings(500, 1000, 900); // Just another interval
    TestBlockSubsidyHalvings(500, 1000, 3000); // Multiple halvings before Blossom activation
    } else {
        TestBlockSubsidyHalvingsZero(mainParams); // Zero: 10/10.8 ZER, 800k halving
        TestFoundersRewardAmountZero();
    }
}

BOOST_AUTO_TEST_CASE(subsidy_limit_test)
{
    const Consensus::Params& consensusParams = Params(CBaseChainParams::MAIN).GetConsensus();
    if (!UsesReferenceSubsidyModel(consensusParams)) {
        TestSubsidyLimitZero(consensusParams); // Zero: validate MoneyRange over full supply
        return;
    }

    CAmount nSum = 0;
    int nHeight = 0;
    // Mining slow start
    for (; nHeight < consensusParams.nSubsidySlowStartInterval; nHeight++) {
        CAmount nSubsidy = GetBlockSubsidy(nHeight, consensusParams);
        BOOST_CHECK(nSubsidy <= REFERENCE_INITIAL_SUBSIDY);
        nSum += nSubsidy;
        BOOST_CHECK(MoneyRange(nSum));
    }
    BOOST_CHECK_EQUAL(nSum, 12500000000000ULL);

    // Regular mining
    CAmount nSubsidy;
    do {
        nSubsidy = GetBlockSubsidy(nHeight, consensusParams);
        BOOST_CHECK(nSubsidy <= REFERENCE_INITIAL_SUBSIDY);
        nSum += nSubsidy;
        BOOST_ASSERT(MoneyRange(nSum));
        ++nHeight;
    } while (nSubsidy > 0);

    // Changing the block interval from 10 to 2.5 minutes causes truncation
    // effects to occur earlier (from the 9th halving interval instead of the
    // 11th), decreasing the total monetary supply by 0.0693 ZEC.
    // BOOST_CHECK_EQUAL(nSum, 2099999997690000ULL);
    // Reducing the interval further to 1.25 minutes has a similar effect,
    // decreasing the total monetary supply by another 0.09240 ZEC.
    // BOOST_CHECK_EQUAL(nSum, 2099999990760000ULL);
    BOOST_CHECK_EQUAL(nSum, 2099999981520000LL);
}

bool ReturnFalse() { return false; }
bool ReturnTrue() { return true; }

BOOST_AUTO_TEST_CASE(test_combiner_all)
{
    boost::signals2::signal<bool (), CombinerAll> Test;
    BOOST_CHECK(Test());
    Test.connect(&ReturnFalse);
    BOOST_CHECK(!Test());
    Test.connect(&ReturnTrue);
    BOOST_CHECK(!Test());
    Test.disconnect(&ReturnFalse);
    BOOST_CHECK(Test());
    Test.disconnect(&ReturnTrue);
    BOOST_CHECK(Test());
}

BOOST_AUTO_TEST_SUITE_END()
