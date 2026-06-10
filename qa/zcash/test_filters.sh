# Canonical C++ pass-only / fail-only filters for Zero harness.
# Sourced by contrib/run-tests.sh; read by qa/zcash/full_test_suite.py.
# 2026-06-09: encrypt-hang class fixed (crypter/wallet FVK write re-entry);
# WriteCryptedSaplingZkey* and rpc_wallet_encrypted_wallet_sapzkeys now pass.
# CachedWitnesses* ported except CleanIndex (reindex scenario needs the
# incremental BuildWitnessCache path: pcoinsTip anchors + ReadBlockFromDisk).
BOOST_PASS_EXCLUDE='!miner_tests'
BOOST_FAIL_ONLY='miner_tests'
GTEST_PASS_EXCLUDE='-WalletTests.CachedWitnessesCleanIndex'
GTEST_FAIL_ONLY='WalletTests.CachedWitnessesCleanIndex'
