// Copyright (c) 2026 The Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php.

#include "txdb.h"
#include "test/test_bitcoin.h"

#include <boost/test/unit_test.hpp>

/**
 * Reindex progress markers (DB_REINDEX_FLAG / LASTFILE / LASTBLOCK)
 * and resume start-file selection (OPS-REINDEX-RESUME + telemetry inputs).
 */
BOOST_FIXTURE_TEST_SUITE(reindex_tests, BasicTestingSetup)

BOOST_AUTO_TEST_CASE(reindex_lastfile_marker_roundtrip)
{
    CBlockTreeDB db(1 << 20, /*fMemory=*/true);

    int nFile = -1;
    BOOST_CHECK(!db.ReadReindexLastFile(nFile));

    BOOST_CHECK(db.WriteReindexLastFile(3));
    BOOST_CHECK(db.ReadReindexLastFile(nFile));
    BOOST_CHECK_EQUAL(nFile, 3);

    BOOST_CHECK(db.WriteReindexLastFile(7));
    BOOST_CHECK(db.ReadReindexLastFile(nFile));
    BOOST_CHECK_EQUAL(nFile, 7);
}

BOOST_AUTO_TEST_CASE(reindex_lastblock_marker_roundtrip)
{
    CBlockTreeDB db(1 << 20, /*fMemory=*/true);

    int nHeight = -1;
    BOOST_CHECK(!db.ReadReindexLastBlock(nHeight));

    BOOST_CHECK(db.WriteReindexLastBlock(720));
    BOOST_CHECK(db.ReadReindexLastBlock(nHeight));
    BOOST_CHECK_EQUAL(nHeight, 720);

    BOOST_CHECK(db.WriteReindexLastBlock(150000));
    BOOST_CHECK(db.ReadReindexLastBlock(nHeight));
    BOOST_CHECK_EQUAL(nHeight, 150000);
}

BOOST_AUTO_TEST_CASE(reindex_flag_roundtrip)
{
    CBlockTreeDB db(1 << 20, /*fMemory=*/true);

    bool fReindexing = true;
    BOOST_CHECK(db.ReadReindexing(fReindexing));
    BOOST_CHECK(!fReindexing);

    BOOST_CHECK(db.WriteReindexing(true));
    BOOST_CHECK(db.ReadReindexing(fReindexing));
    BOOST_CHECK(fReindexing);

    BOOST_CHECK(db.WriteReindexing(false));
    BOOST_CHECK(db.ReadReindexing(fReindexing));
    BOOST_CHECK(!fReindexing);
}

BOOST_AUTO_TEST_CASE(reindex_resume_start_file)
{
    std::string reason;

    BOOST_CHECK_EQUAL(ReindexResumeStartFile(-1, 10, &reason), 0);
    BOOST_CHECK(reason.find("absent") != std::string::npos);

    BOOST_CHECK_EQUAL(ReindexResumeStartFile(0, 10, &reason), 1);
    BOOST_CHECK(reason.find("resume") != std::string::npos);

    BOOST_CHECK_EQUAL(ReindexResumeStartFile(3, 10, &reason), 4);
    BOOST_CHECK(reason.find("resume") != std::string::npos);

    // Last completed file was the final blk -- start past EOF (import loop exits).
    BOOST_CHECK_EQUAL(ReindexResumeStartFile(9, 10, &reason), 10);
    BOOST_CHECK(reason.find("nothing left") != std::string::npos);

    // Out of range: treat as full replay from 0.
    BOOST_CHECK_EQUAL(ReindexResumeStartFile(10, 10, &reason), 0);
    BOOST_CHECK(reason.find("out of range") != std::string::npos);

    BOOST_CHECK_EQUAL(ReindexResumeStartFile(99, 5, &reason), 0);
    BOOST_CHECK(reason.find("out of range") != std::string::npos);

    BOOST_CHECK_EQUAL(ReindexResumeStartFile(3, 0, &reason), 0);
    BOOST_CHECK(reason.find("no blk") != std::string::npos);

    // nullptr reason is allowed.
    BOOST_CHECK_EQUAL(ReindexResumeStartFile(2, 8, nullptr), 3);
}

/**
 * Simulate interrupted reindex state in blocks/index: 'R' set, L/H written.
 * Resume cursor must be L+1; clearing 'R' must leave L/H (post-finish semantics).
 */
BOOST_AUTO_TEST_CASE(reindex_interrupted_state_resume_cursor)
{
    CBlockTreeDB db(1 << 20, /*fMemory=*/true);

    BOOST_CHECK(db.WriteReindexing(true));
    BOOST_CHECK(db.WriteReindexLastFile(4));
    BOOST_CHECK(db.WriteReindexLastBlock(12345));

    bool fReindexing = false;
    int nLastFile = -1;
    int nLastBlock = -1;
    BOOST_CHECK(db.ReadReindexing(fReindexing));
    BOOST_CHECK(fReindexing);
    BOOST_CHECK(db.ReadReindexLastFile(nLastFile));
    BOOST_CHECK_EQUAL(nLastFile, 4);
    BOOST_CHECK(db.ReadReindexLastBlock(nLastBlock));
    BOOST_CHECK_EQUAL(nLastBlock, 12345);

    const int nBlkFiles = 12;
    std::string reason;
    BOOST_CHECK_EQUAL(ReindexResumeStartFile(nLastFile, nBlkFiles, &reason), 5);

    // Finish: erase 'R', keep L/H as historical markers.
    BOOST_CHECK(db.WriteReindexing(false));
    BOOST_CHECK(db.ReadReindexing(fReindexing));
    BOOST_CHECK(!fReindexing);
    BOOST_CHECK(db.ReadReindexLastFile(nLastFile));
    BOOST_CHECK_EQUAL(nLastFile, 4);
    BOOST_CHECK(db.ReadReindexLastBlock(nLastBlock));
    BOOST_CHECK_EQUAL(nLastBlock, 12345);
}

/**
 * Fresh wipe / empty index: no L -> resume helper starts at 0 (full import).
 */
BOOST_AUTO_TEST_CASE(reindex_fresh_index_no_lastfile)
{
    CBlockTreeDB db(1 << 20, /*fMemory=*/true);

    BOOST_CHECK(db.WriteReindexing(true));
    int nLastFile = -1;
    BOOST_CHECK(!db.ReadReindexLastFile(nLastFile));

    std::string reason;
    BOOST_CHECK_EQUAL(ReindexResumeStartFile(-1, 41, &reason), 0);
    BOOST_CHECK(reason.find("absent") != std::string::npos);
}

/**
 * DB_FLAG round-trip for insight/txindex (mismatch detect inputs; wipe not exercised here).
 */
BOOST_AUTO_TEST_CASE(reindex_db_flag_insight_txindex)
{
    CBlockTreeDB db(1 << 20, /*fMemory=*/true);

    bool fVal = true;
    BOOST_CHECK(!db.ReadFlag("insightexplorer", fVal));
    BOOST_CHECK(db.WriteFlag("insightexplorer", true));
    BOOST_CHECK(db.ReadFlag("insightexplorer", fVal));
    BOOST_CHECK(fVal);

    BOOST_CHECK(db.WriteFlag("insightexplorer", false));
    BOOST_CHECK(db.ReadFlag("insightexplorer", fVal));
    BOOST_CHECK(!fVal);

    BOOST_CHECK(db.WriteFlag("txindex", true));
    BOOST_CHECK(db.ReadFlag("txindex", fVal));
    BOOST_CHECK(fVal);
}

BOOST_AUTO_TEST_SUITE_END()
