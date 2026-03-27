#!/usr/bin/env bash
# Run Zero tests. Modes:
#   passing (default): only tests that pass; excludes known failures and hang/crash.
#   --fail: pass + fail; excludes only hang/crash.
#   --all: everything including hang/crash (no exclusions; GTest may hang on WriteCryptedSaplingZkeyDirectToDb).
#
# Usage: ./contrib/run-tests.sh [--quick] [--no-python] [--build-checks] [--jobs=N] [--fail|--all|--full-suite|--full]
# Env: ZERO_MINE_COINBASE=1 to mine 1000 blocks for get_coinbase_address tests (slow).
# --quick: skip zero-gtest and test_bitcoin (run only quick: bitcoin-util-test, secp256k1, univalue, check-symbols, check-security)
# --no-python: skip Python RPC tests (qa/rpc-tests)
# --build-checks: run make check-security (requires python on PATH; see TEST_ZERO.md)
# --jobs=N: run Python RPC tests in parallel (default 1). E.g. --jobs=4.
# ZERO_MINE_COINBASE=1: mine 1000 blocks when tests need get_coinbase_address (slow; not used in main run).
# --fail: pass + fail (exclude only hang/crash)
# --all: everything including hang/crash (no exclusions)
# --full-suite, --full: run qa/zcash/full_test_suite.py (btest, gtest, sec-hard, no-dot-so, util-test, secp256k1, univalue, rpc). On failure: report error and exit 1. Differs from --all: adds sec-hard, no-dot-so; uses full test_bitcoin -p, zero-gtest with no filter.

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LOG_DIR="${LOG_DIR:-$REPO_ROOT/test-logs}"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_PREFIX="$LOG_DIR/${TIMESTAMP}"

BOOST_EXCLUDE='!Alert_tests:!equihash_tests:!miner_tests:!rpc_wallet_tests/rpc_wallet_encrypted_wallet_sapzkeys'

PYTHON_PASSING=(
    blockchain disablewallet httpbasics reindex rescan_import rescan_startup decodescript keypool
    paymentdisclosure prioritisetransaction wallet_treestate wallet_anchorfork
    getchaintips rewind_index wallet_overwintertx wallet_changeaddresses
    shorter_block_times p2p_nu_peer_management
    txn_doublespend
)

echo "Zero test validation - $TIMESTAMP"
echo "Logs: $LOG_DIR"
echo ""

find_python3() {
    if [ -n "$PYTHON" ]; then echo "$PYTHON"; return; fi
    if command -v python3 &>/dev/null && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then echo "python3"; return; fi
    if command -v python &>/dev/null && python -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then echo "python"; return; fi
    echo ""
}

MODE=passing
QUICK=0
NO_PYTHON=0
FULL_SUITE=0
BUILD_CHECKS=0
PYTHON_JOBS=1
for arg in "$@"; do
    case "$arg" in
        --quick) QUICK=1 ;;
        --no-python) NO_PYTHON=1 ;;
        --build-checks) BUILD_CHECKS=1 ;;
        --fail) MODE=fail ;;
        --all) MODE=all ;;
        --full-suite|--full) FULL_SUITE=1 ;;
        --jobs=*) PYTHON_JOBS="${arg#--jobs=}" ;;
    esac
done

run_cmd() {
    local name="$1"
    shift
    local log="$LOG_PREFIX-$name.log"
    echo "=== $name ==="
    if "$@" 2>&1 | tee "$log"; then
        echo "PASS: $name"
        return 0
    else
        echo "FAIL: $name (see $log)"
        return 1
    fi
}

run_bg() {
    local name="$1"
    shift
    local log="$LOG_PREFIX-$name.log"
    echo "=== $name (background) ==="
    ("$@" 2>&1 | tee "$log") &
    echo $!
}

if [ "$BUILD_CHECKS" -eq 1 ]; then
    echo "--- Build checks ---"
    PY_DIR=""
    if [ -n "$PYTHON" ] && [ -x "$PYTHON" ]; then
        PY_DIR="$(dirname "$PYTHON")"
    elif command -v python3 &>/dev/null; then
        PY_DIR="$(dirname "$(command -v python3)")"
    elif command -v python &>/dev/null; then
        PY_DIR="$(dirname "$(command -v python)")"
    fi
    if [ -n "$PY_DIR" ]; then
        run_cmd "check-security" env PATH="$PY_DIR:$PATH" make -C src check-security || true
    else
        echo "Skipping check-security: no python in PATH (set PYTHON or use python3)"
    fi
    echo ""
fi

if [ "$FULL_SUITE" -eq 1 ]; then
    PY3=$(find_python3)
    if [ -z "$PY3" ]; then
        echo "FAIL: Python 3.10+ required for full_test_suite"
        exit 1
    fi
    FULL_SUITE_SKIP=()
    if [ "$(uname -s)" = "Darwin" ]; then
        FULL_SUITE_SKIP=(--skip sec-hard --skip no-dot-so)
    fi
    echo "--- full_test_suite ---"
    if ! run_cmd "full_test_suite" "$PY3" "$REPO_ROOT/qa/zcash/full_test_suite.py" "${FULL_SUITE_SKIP[@]}"; then
        echo "FAIL: full_test_suite exited with error"
        exit 1
    fi
    echo "--- Done. Logs in $LOG_DIR ---"
    exit 0
fi

echo "--- Quick tests ---"
run_cmd "bitcoin-util-test" \
    bash -c "cd \"$REPO_ROOT/src\" && srcdir=\$(pwd) PYTHONPATH=\$(pwd)/test python3 test/bitcoin-util-test.py" || true

run_cmd "secp256k1-check" make -C src secp256k1-check || true
run_cmd "univalue-check" make -C src univalue-check || true

if [ -x "src/zerod" ]; then
    run_cmd "check-symbols" make -C src check-symbols 2>/dev/null || true
    run_cmd "check-security" make -C src check-security 2>/dev/null || true
fi

if [ "$QUICK" -eq 0 ]; then
    echo ""
    GTEST_PID=""
    if [ -x "src/zero-gtest" ]; then
        if [ "$MODE" = "all" ]; then
            echo "--- GTest (all; includes hang/crash) ---"
            GTEST_PID=$(run_bg "zero-gtest" ./src/zero-gtest 2>&1)
        else
            echo "--- GTest (excludes hang/crash: WriteCryptedSaplingZkey*, CachedWitnesses*) ---"
            GTEST_PID=$(run_bg "zero-gtest" \
                ./src/zero-gtest --gtest_filter='-wallet_zkeys_tests.WriteCryptedSaplingZkey*:WalletTests.CachedWitnesses*')
        fi
    fi

    echo ""
    BTEST_PID=""
    if [ -x "src/test/test_bitcoin" ]; then
        if [ "$MODE" = "fail" ] || [ "$MODE" = "all" ]; then
            echo "--- Boost (all) ---"
            BTEST_PID=$(run_bg "test_bitcoin" ./src/test/test_bitcoin --log_level=test_suite 2>&1)
        else
            echo "--- Boost (pass-only: exclude Alert, equihash, miner) ---"
            BTEST_PID=$(run_bg "test_bitcoin" ./src/test/test_bitcoin --run_test="$BOOST_EXCLUDE" --log_level=test_suite 2>&1)
        fi
    fi

    echo "zero-gtest PID: $GTEST_PID"
    echo "test_bitcoin PID: $BTEST_PID"
    echo "Waiting for background tests..."
    [ -n "$GTEST_PID" ] && wait $GTEST_PID 2>/dev/null || true
    [ -n "$BTEST_PID" ] && wait $BTEST_PID 2>/dev/null || true
fi

if [ "$NO_PYTHON" -eq 0 ]; then
    echo ""
    if [ "$(uname -s)" = "Darwin" ]; then
        orphaned=$(pgrep -f "zerod -datadir=/var/folders" 2>/dev/null | wc -l)
        if [ "$orphaned" -gt 0 ]; then
            echo "--- Killing $orphaned orphaned zerod ---"
            pkill -f "zerod -datadir=/var/folders" 2>/dev/null || true
        fi
    fi
    PY3=$(find_python3)
    if [ -n "$PY3" ]; then
        export PYTHON="$PY3"
        if [ "$MODE" = "fail" ] || [ "$MODE" = "all" ]; then
            echo "--- Python RPC (all) ---"
            run_cmd "rpc-all" \
                env PYTHON="$PY3" "$REPO_ROOT/qa/pull-tester/rpc-tests.sh" -extended || true
        elif [ "$PYTHON_JOBS" -gt 1 ]; then
            echo "--- Python RPC (pass-only: ${#PYTHON_PASSING[@]} tests, jobs=$PYTHON_JOBS) ---"
            PIDS=()
            for t in "${PYTHON_PASSING[@]}"; do
                pid=$(run_bg "rpc-$t" \
                    env PYTHON="$PY3" "$REPO_ROOT/qa/pull-tester/rpc-tests.sh" "$t" || true)
                PIDS+=("$pid")
                while [ "$(jobs -r 2>/dev/null | wc -l)" -ge "$PYTHON_JOBS" ]; do sleep 1; done
            done
            for p in "${PIDS[@]}"; do wait "$p" 2>/dev/null || true; done
        else
            echo "--- Python RPC (pass-only: ${#PYTHON_PASSING[@]} verified) ---"
            for t in "${PYTHON_PASSING[@]}"; do
                run_cmd "rpc-$t" \
                    env PYTHON="$PY3" "$REPO_ROOT/qa/pull-tester/rpc-tests.sh" "$t" || true
            done
        fi
    else
        echo "Skipping Python RPC tests: Python 3.10+ not found"
    fi
fi

echo ""
echo "--- Done. Logs in $LOG_DIR ---"
echo "Review: ls -la $LOG_PREFIX-*.log"
