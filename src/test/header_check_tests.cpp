#if defined(HAVE_CONFIG_H)
#include "config/bitcoin-config.h"
#endif

#include "coins.h"
#include "test/test_bitcoin.h"
#include "test/regtest_helpers.h"

#include <boost/test/unit_test.hpp>

#ifdef ENABLE_MINING

// Header checks around the BLOCK_VALID_TREE Equihash skip: what ConnectBlock
// trusts, what it still checks, and the checks the skip relies on.

BOOST_FIXTURE_TEST_SUITE(header_check_tests, RegtestSetup)

// First half of the skip: ConnectBlock does not re-verify the Equihash solution of a
// block whose index entry is already at BLOCK_VALID_TREE. AcceptBlockHeader
// verified that header before raising the entry, and the entry is keyed by the
// header hash, so a second verification recomputes a known answer.
//
// The block handed to ConnectBlock here carries a corrupt solution under a
// valid index entry. With the skip it connects; with the skip reverted
// CheckBlock re-runs CheckEquihashSolution and rejects it as invalid-solution.
// The same skip in AcceptBlock has no observable effect outside the ZERO_PERF
// per-caller counters, so it is not pinned here.
BOOST_AUTO_TEST_CASE(connectblock_trusts_valid_tree_header)
{
    const CChainParams& chainparams = Params();
    const CBlock block = MineOneRegtestBlock(CScript() << OP_TRUE);
    const CBlock bad = WithCorruptSolution(block);

    LOCK(cs_main);
    BOOST_REQUIRE(chainActive.Tip()->GetBlockHash() == block.GetHash());
    CBlockIndex* pindex = UnconnectTip();

    // The header check proper does reject this header.
    auto verifier = libzcash::ProofVerifier::Disabled();
    CValidationState headerState;
    BOOST_CHECK(!CheckBlock(bad, headerState, chainparams, verifier, true, true));
    BOOST_CHECK_EQUAL(headerState.GetRejectReason(), "invalid-solution");

    CCoinsViewCache view(pcoinsTip);
    CValidationState connectState;
    BOOST_CHECK_MESSAGE(ConnectBlock(bad, connectState, pindex, view, chainparams, false),
                        "ConnectBlock re-verified a BLOCK_VALID_TREE header: "
                            << connectState.GetRejectReason());
}

// Second half of the skip: what keeps the skip safe for a block read back from disk.
// ConnectTip reads a block it was not handed in memory, and ReadBlockFromDisk
// re-checks the header (Equihash and proof of work) of what it read; the
// index-entry overload also compares the hash. With the skip in ConnectBlock,
// the read is the only Equihash check on that path, so bytes that changed on
// disk after AcceptBlock must fail there. Removing the re-check from
// ReadBlockFromDisk fails the first assertion.
BOOST_AUTO_TEST_CASE(readblockfromdisk_rechecks_header)
{
    const CChainParams& chainparams = Params();
    const CBlock block = MineOneRegtestBlock(CScript() << OP_TRUE);

    LOCK(cs_main);
    CBlockIndex* pindex = chainActive.Tip();
    BOOST_REQUIRE(pindex->GetBlockHash() == block.GetHash());
    const CDiskBlockPos pos = pindex->GetBlockPos();

    CBlock read;
    BOOST_REQUIRE(ReadBlockFromDisk(read, pos, chainparams.GetConsensus()));
    BOOST_REQUIRE(read.GetHash() == block.GetHash());

    // nSolution is the last header field: its bytes end where the header does.
    const unsigned int headerSize = ::GetSerializeSize(block.GetBlockHeader(), SER_DISK, CLIENT_VERSION);
    const long solutionOffset = pos.nPos + headerSize - block.nSolution.size();
    {
        FILE* f = OpenBlockFile(pos, false);
        BOOST_REQUIRE(f != NULL);
        BOOST_REQUIRE_EQUAL(fseek(f, solutionOffset, SEEK_SET), 0);
        int c = fgetc(f);
        BOOST_REQUIRE(c != EOF);
        BOOST_REQUIRE_EQUAL(fseek(f, solutionOffset, SEEK_SET), 0);
        BOOST_REQUIRE(fputc(c ^ 0x01, f) != EOF);
        BOOST_REQUIRE_EQUAL(fclose(f), 0);
    }

    BOOST_CHECK_MESSAGE(!ReadBlockFromDisk(read, pos, chainparams.GetConsensus()),
                        "ReadBlockFromDisk accepted a block whose Equihash solution changed on disk");
    BOOST_CHECK(!ReadBlockFromDisk(read, pindex, chainparams.GetConsensus()));
}

// Bounds of the skip. The skip trusts the header only: under the same valid entry,
// ConnectBlock still rebuilds the merkle root from the transactions it is
// given. That check is the CVE-2012-2459 guard, and its input is the
// transaction list, not the header.
BOOST_AUTO_TEST_CASE(connectblock_still_checks_merkle_root)
{
    const CChainParams& chainparams = Params();
    CBlock bad = MineOneRegtestBlock(CScript() << OP_TRUE);

    LOCK(cs_main);
    CBlockIndex* pindex = UnconnectTip();

    CMutableTransaction coinbase(bad.vtx[0]);
    coinbase.vin[0].scriptSig << OP_0;
    bad.vtx[0] = CTransaction(coinbase);

    CCoinsViewCache view(pcoinsTip);
    CValidationState state;
    BOOST_CHECK(!ConnectBlock(bad, state, pindex, view, chainparams, false));
    BOOST_CHECK_EQUAL(state.GetRejectReason(), "bad-txnmrklroot");
}

// Bounds of the skip. The skip is conditional on BLOCK_VALID_TREE: an entry below it
// has not had its header verified, and ConnectBlock still verifies it.
BOOST_AUTO_TEST_CASE(connectblock_checks_header_below_valid_tree)
{
    const CChainParams& chainparams = Params();
    const CBlock bad = WithCorruptSolution(MineOneRegtestBlock(CScript() << OP_TRUE));

    LOCK(cs_main);
    CBlockIndex* pindex = UnconnectTip();
    const unsigned int savedStatus = pindex->nStatus;
    pindex->nStatus = (pindex->nStatus & ~BLOCK_VALID_MASK) | BLOCK_VALID_HEADER;
    BOOST_REQUIRE(!pindex->IsValid(BLOCK_VALID_TREE));

    CCoinsViewCache view(pcoinsTip);
    CValidationState state;
    BOOST_CHECK(!ConnectBlock(bad, state, pindex, view, chainparams, false));
    BOOST_CHECK_EQUAL(state.GetRejectReason(), "invalid-solution");
    pindex->nStatus = savedStatus;
}

// Entry points. A block arriving with a corrupt solution is
// rejected on submission, before any index entry exists for it; the same
// block intact is accepted, so the corruption alone caused the rejection.
// Two checks guard this path, the preliminary CheckBlock and
// AcceptBlockHeader; either alone keeps this test passing.
BOOST_AUTO_TEST_CASE(processnewblock_rejects_corrupt_solution)
{
    const CChainParams& chainparams = Params();
    CBlock good = SolveRegtestBlock(CScript() << OP_TRUE);
    CBlock bad = WithCorruptSolution(good);

    CValidationState badState;
    BOOST_CHECK(!ProcessNewBlock(badState, chainparams, NULL, &bad, true, NULL));
    BOOST_CHECK_EQUAL(badState.GetRejectReason(), "invalid-solution");
    {
        LOCK(cs_main);
        BOOST_CHECK(mapBlockIndex.count(bad.GetHash()) == 0);
        BOOST_CHECK_EQUAL(chainActive.Height(), 0);
    }

    CValidationState goodState;
    BOOST_CHECK_MESSAGE(ProcessNewBlock(goodState, chainparams, NULL, &good, true, NULL),
                        goodState.GetRejectReason());
    LOCK(cs_main);
    BOOST_CHECK_EQUAL(chainActive.Height(), 1);
}

// Entry points. TestBlockValidity (block proposals) runs
// ConnectBlock with fJustCheck, where the skip never applies, and verifies the
// solution itself when asked to.
BOOST_AUTO_TEST_CASE(testblockvalidity_checks_solution)
{
    const CChainParams& chainparams = Params();
    CBlock good = SolveRegtestBlock(CScript() << OP_TRUE);
    CBlock bad = WithCorruptSolution(good);

    LOCK(cs_main);
    CValidationState goodState;
    BOOST_CHECK_MESSAGE(TestBlockValidity(goodState, chainparams, good, chainActive.Tip(), true, true),
                        goodState.GetRejectReason());
    CValidationState badState;
    BOOST_CHECK(!TestBlockValidity(badState, chainparams, bad, chainActive.Tip(), true, true));
    BOOST_CHECK_EQUAL(badState.GetRejectReason(), "invalid-solution");
}

// The Equihash input is the whole header except the solution, so changing any
// other header field invalidates a solution that was valid for it.
BOOST_AUTO_TEST_CASE(solution_binds_the_rest_of_the_header)
{
    CBlock block = SolveRegtestBlock(CScript() << OP_TRUE);
    BOOST_REQUIRE(CheckEquihashSolution(&block, Params().GetConsensus()));
    block.nNonce = ArithToUint256(UintToArith256(block.nNonce) + 1);
    BOOST_CHECK(!CheckEquihashSolution(&block, Params().GetConsensus()));

    CValidationState state;
    BOOST_CHECK(!ProcessNewBlock(state, Params(), NULL, &block, true, NULL));
    BOOST_CHECK_EQUAL(state.GetRejectReason(), "invalid-solution");
}

// A block already in the index, submitted again, is accepted as a duplicate:
// the header path finds it and nothing is re-verified or re-connected.
BOOST_AUTO_TEST_CASE(resubmitted_block_is_a_harmless_duplicate)
{
    CBlock block = MineOneRegtestBlock(CScript() << OP_TRUE);
    CValidationState state;
    BOOST_CHECK_MESSAGE(ProcessNewBlock(state, Params(), NULL, &block, true, NULL),
                        state.GetRejectReason());
    LOCK(cs_main);
    BOOST_CHECK_EQUAL(chainActive.Height(), 1);
    BOOST_CHECK(chainActive.Tip()->GetBlockHash() == block.GetHash());
}

BOOST_AUTO_TEST_SUITE_END()

#endif // ENABLE_MINING
