# C++ gate filters, sourced by contrib/run-tests.sh and read by full_test_suite.py.
# CachedWitnessesCleanIndex needs pcoinsTip anchors and disk blocks the gtest fixture lacks.
BOOST_PASS_EXCLUDE=''
BOOST_FAIL_ONLY=''
GTEST_PASS_EXCLUDE='-WalletTests.CachedWitnessesCleanIndex'
GTEST_FAIL_ONLY='WalletTests.CachedWitnessesCleanIndex'
