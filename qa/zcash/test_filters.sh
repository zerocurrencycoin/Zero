# C++ gate filters, sourced by contrib/run-tests.sh and read by full_test_suite.py.
# CachedWitnessesCleanIndex needs pcoinsTip anchors and disk blocks the gtest fixture lacks.
# GTEST_SPROUT_PROOF builds Sprout proofs: about 3 GiB peak RSS and two thirds of the C++ CPU
# time, which overloads small hosts; no run mode includes it. Run it alone:
#   ./src/zero-gtest --gtest_filter="$GTEST_SPROUT_PROOF"
BOOST_PASS_EXCLUDE=''
BOOST_FAIL_ONLY=''
GTEST_SPROUT_PROOF='joinsplit.full_api_test:TransactionBuilder.SproutToSproutAndSapling:TransactionBuilder.SaplingToSprout'
GTEST_PASS_EXCLUDE="-WalletTests.CachedWitnessesCleanIndex:${GTEST_SPROUT_PROOF}"
GTEST_FAIL_ONLY='WalletTests.CachedWitnessesCleanIndex'
