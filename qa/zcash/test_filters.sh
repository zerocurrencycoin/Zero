# Canonical C++ pass-only / fail-only filters for Zero harness.
# Sourced by contrib/run-tests.sh; read by qa/zcash/full_test_suite.py.
# Boost: no working-gate exclude.
# GTest: CachedWitnessesCleanIndex held (reindex-style harness: pcoinsTip anchors + ReadBlockFromDisk).
BOOST_PASS_EXCLUDE=''
BOOST_FAIL_ONLY=''
GTEST_PASS_EXCLUDE='-WalletTests.CachedWitnessesCleanIndex'
GTEST_FAIL_ONLY='WalletTests.CachedWitnessesCleanIndex'
