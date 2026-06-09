# Canonical C++ pass-only / fail-only filters for Zero harness.
# Sourced by contrib/run-tests.sh; read by qa/zcash/full_test_suite.py.
BOOST_PASS_EXCLUDE='!miner_tests:!rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys'
BOOST_FAIL_ONLY='miner_tests:rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys'
GTEST_PASS_EXCLUDE='-wallet_zkeys_tests.WriteCryptedSaplingZkey*:WalletTests.CachedWitnesses*'
GTEST_FAIL_ONLY='wallet_zkeys_tests.WriteCryptedSaplingZkey*:WalletTests.CachedWitnesses*'
