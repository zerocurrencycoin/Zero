// Copyright (c) 2026 The Zero developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php.

#include "txdb.h"
#include "test/test_bitcoin.h"

#include <boost/test/unit_test.hpp>

/**
 * Reindex progress markers (DB_REINDEX_LASTFILE / DB_REINDEX_LASTBLOCK).
 *
 * Written after each blk#####.dat completes in ThreadImport. Consume/resume
 * is postponed (OPS-REINDEX-RESUME); these tests cover persistence only.
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

BOOST_AUTO_TEST_SUITE_END()
