#!/usr/bin/env bash
# Run Zero tests. Modes:
#   passing (default): pass-only C++ + Tier A RPC; excludes known hang/crash/fail suites.
#   --fail: ONLY the C++ suites excluded from default (known hang, crash, or fail; see TEST_ZERO.md).
#   --all: same C++ filters as default + rpc-tests.sh -all (-A -B -E pass tiers).
#   --rpcfail: rpc-tests.sh -rpcfail (-Bfail -Efail diagnostic; no C++, no util).
#
# Usage: ./contrib/run-tests.sh [--quick] [--no-python] [--build-checks] [--jobs=N] [--strict] [--fail|--all|-all|--rpcfail|--suite] [rpc_test]
# --strict: after all selected steps, exit 1 if any failed (default: exit 0 with WARNING if any failed).
# Env: ZERO_MINE_COINBASE=1 to mine 1000 blocks for get_coinbase_address tests (slow).
# --quick: skip zero-gtest and test_bitcoin (run only quick: bitcoin-util-test, secp256k1, univalue, check-symbols, check-security)
# --no-python: skip Python RPC tests (qa/rpc-tests); superset of --quick (adds C++ layers per mode).
# --build-checks: run make check-security (requires python on PATH; see TEST_ZERO.md)
# --jobs=N: Tier A RPC only, default pass-only mode. Serial (N=1) is the supported path (CI / contributor gate).
# --suite: run qa/zcash/full_test_suite.py only (ordered stages; not --all, not default).
# rpc_test: basename of one qa/rpc-tests script (e.g. proxy_test or proxy_test.py).
#   Runs ONLY that script via rpc-tests.sh (skips C++/util/gtest). Preferred single-test entry.

set -e
if [ -z "${BASH_VERSION:-}" ]; then
    echo "run-tests.sh requires bash (use ./contrib/run-tests.sh or bash contrib/run-tests.sh)" >&2
    exit 2
fi
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export BUILDDIR="${BUILDDIR:-$REPO_ROOT}"
export ZERO_RPC_CACHE_DIR="${ZERO_RPC_CACHE_DIR:-$REPO_ROOT/cache}"

LOG_DIR="${LOG_DIR:-$REPO_ROOT/test-logs}"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_PREFIX="$LOG_DIR/${TIMESTAMP}"

# Default: exclude these suites. --fail: run ONLY these (must match TEST_ZERO.md Known failures).
# Canonical values: qa/zcash/test_filters.sh
. "$REPO_ROOT/qa/zcash/test_filters.sh"

# Tier A basenames for --jobs=N parallel runs only. Canonical list: testScriptsTierA in qa/pull-tester/rpc-tests.sh.
# Serial gate uses: rpc-tests.sh -A
PYTHON_PASSING=(
    blockchain disablewallet httpbasics reindex decodescript keypool
    paymentdisclosure
    getchaintips rewind_index p2p_nu_peer_management
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
STRICT=0
OVERALL_FAIL=0
RPC_SINGLE=""
for arg in "$@"; do
    case "$arg" in
        --quick) QUICK=1 ;;
        --no-python) NO_PYTHON=1 ;;
        --build-checks) BUILD_CHECKS=1 ;;
        --strict) STRICT=1 ;;
        --fail) MODE=fail ;;
        --all|-all) MODE=all ;;
        --rpcfail) MODE=rpcfail ;;
        --suite) FULL_SUITE=1 ;;
        --jobs=*) PYTHON_JOBS="${arg#--jobs=}" ;;
        -*)
            echo "Unknown option: $arg" >&2
            echo "Usage: $0 [--quick] [--no-python] [--build-checks] [--jobs=N] [--strict] [--fail|--all|-all|--rpcfail|--suite] [rpc_test.py]" >&2
            exit 2
            ;;
        *)
            # Single RPC script: proxy_test / proxy_test.py / path/to/proxy_test.py
            base="$(basename "$arg")"
            base="${base%.py}"
            if [ -n "$RPC_SINGLE" ]; then
                echo "Only one rpc_test name allowed (got '$RPC_SINGLE' and '$base')" >&2
                exit 2
            fi
            if [ ! -f "$REPO_ROOT/qa/rpc-tests/${base}.py" ]; then
                echo "Unknown rpc_test: $arg (expected qa/rpc-tests/${base}.py)" >&2
                exit 2
            fi
            RPC_SINGLE="$base"
            ;;
    esac
done


bump_fail() {
    OVERALL_FAIL=1
}

run_cmd() {
    local name="$1"
    shift
    local log="$LOG_PREFIX-$name.log"
    local status
    echo "=== $name ==="
    set +e
    "$@" 2>&1 | tee "$log"
    status=${PIPESTATUS[0]}
    set -e
    if [ "$status" -eq 0 ]; then
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
    echo "=== $name (background) ===" >&2
    "$@" >"$log" 2>&1 &
    BG_LAST_PID=$!
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
    echo "--- full_test_suite (--suite) ---"
    if ! run_cmd "full_test_suite" "$PY3" "$REPO_ROOT/qa/zcash/full_test_suite.py" "${FULL_SUITE_SKIP[@]}"; then
        echo "FAIL: full_test_suite exited with error"
        exit 1
    fi
    echo "--- Done. Logs in $LOG_DIR ---"
    exit 0
fi

# Single RPC script by name: only that test (no util / C++ / Tier A).
if [ -n "$RPC_SINGLE" ]; then
    echo "--- Single RPC: qa/rpc-tests/${RPC_SINGLE}.py ---"
    PY3=$(find_python3)
    if [ -z "$PY3" ]; then
        echo "FAIL: Python 3.10+ required for RPC tests"
        exit 1
    fi
    export PYTHON="$PY3"
    if [ "$(uname -s)" = "Darwin" ]; then
        orphaned=$(pgrep -f "zerod -datadir=/var/folders" 2>/dev/null | wc -l)
        if [ "$orphaned" -gt 0 ]; then
            echo "--- Killing $orphaned orphaned zerod ---"
            pkill -f "zerod -datadir=/var/folders" 2>/dev/null || true
        fi
    fi
    if ! run_cmd "rpc-$RPC_SINGLE" \
        env PYTHON="$PY3" "$REPO_ROOT/qa/pull-tester/rpc-tests.sh" "$RPC_SINGLE"; then
        bump_fail
    fi
    echo ""
    echo "--- Done. Logs in $LOG_DIR ---"
    if [ "$OVERALL_FAIL" -eq 1 ]; then
        if [ "$STRICT" -eq 1 ]; then
            echo "FAIL: $RPC_SINGLE failed with --strict" >&2
            exit 1
        fi
        echo "WARNING: $RPC_SINGLE failed. Re-run with --strict to exit 1 on failure."
        exit 0
    fi
    exit 0
fi

# --rpcfail: RPC known-fail tiers only (-Bfail -Efail).
if [ "$MODE" = "rpcfail" ]; then
    echo "--- --rpcfail: RPC -Bfail -Efail (diagnostic; no util, no C++) ---"
    PY3=$(find_python3)
    if [ -n "$PY3" ]; then
        export PYTHON="$PY3"
        if ! run_cmd "rpc-rpcfail" \
            env PYTHON="$PY3" "$REPO_ROOT/qa/pull-tester/rpc-tests.sh" -rpcfail; then
            bump_fail
        fi
    else
        echo "Skipping Python RPC tests: Python 3.10+ not found"
    fi
    echo ""
    echo "--- Done. Logs in $LOG_DIR ---"
    if [ "$OVERALL_FAIL" -eq 1 ]; then
        if [ "$STRICT" -eq 1 ]; then
            echo "FAIL: one or more steps failed with --strict" >&2
            exit 1
        fi
        echo "WARNING: one or more steps failed. Re-run with --strict to exit 1 on failure."
    fi
    exit 0
fi

# --fail: only suites listed in TEST_ZERO.md Known failures (hang / crash / fail).
if [ "$MODE" = "fail" ]; then
    echo "--- --fail: known hang / crash / fail C++ suites only (no util, no RPC) ---"
    if [ "$QUICK" -eq 1 ]; then
        echo "NOTE: --quick with --fail skips C++; run without --quick to execute excluded suites."
    else
        GTEST_PID=""
        if [ -x "src/zero-gtest" ]; then
            echo "--- GTest: CachedWitnessesCleanIndex (needs pcoinsTip/disk-block harness) ---"
            run_bg "zero-gtest-fail-only" \
                ./src/zero-gtest --gtest_filter="$GTEST_FAIL_ONLY"
            GTEST_PID=$BG_LAST_PID
        fi
        BTEST_PID=""
        if [ -x "src/test/test_bitcoin" ] && [ -n "$BOOST_FAIL_ONLY" ]; then
            echo "--- Boost fail-only: $BOOST_FAIL_ONLY ---"
            run_bg "test_bitcoin-fail-only" \
                ./src/test/test_bitcoin --run_test="$BOOST_FAIL_ONLY" --log_level=test_suite
            BTEST_PID=$BG_LAST_PID
        fi
        if [ -n "$GTEST_PID" ] && ! wait "$GTEST_PID" 2>/dev/null; then
            echo "FAIL: zero-gtest (see $LOG_PREFIX-zero-gtest-fail-only.log)"
            bump_fail
        fi
        if [ -n "$BTEST_PID" ] && ! wait "$BTEST_PID" 2>/dev/null; then
            echo "FAIL: test_bitcoin (see $LOG_PREFIX-test_bitcoin-fail-only.log)"
            bump_fail
        fi
        if [ -z "$GTEST_PID" ] && [ -z "$BTEST_PID" ]; then
            echo "FAIL: --fail requires src/zero-gtest and/or src/test/test_bitcoin"
            bump_fail
        fi
    fi
    echo ""
    echo "--- Done. Logs in $LOG_DIR ---"
    if [ "$OVERALL_FAIL" -eq 1 ]; then
        if [ "$STRICT" -eq 1 ]; then
            echo "FAIL: one or more steps failed with --strict" >&2
            exit 1
        fi
        echo "WARNING: one or more steps failed. Re-run with --strict to exit 1 on failure."
    fi
    exit 0
fi

echo "--- Quick tests ---"
if ! run_cmd "bitcoin-util-test" \
    bash -c "cd \"$REPO_ROOT/src\" && srcdir=\$(pwd) PYTHONPATH=\$(pwd)/test python3 test/bitcoin-util-test.py"; then
    bump_fail
fi

if ! run_cmd "secp256k1-check" make -C src secp256k1-check; then
    bump_fail
fi
if ! run_cmd "univalue-check" make -C src univalue-check; then
    bump_fail
fi

if [ -x "src/zerod" ]; then
    if ! run_cmd "check-symbols" make -C src check-symbols 2>/dev/null; then
        bump_fail
    fi
    if ! run_cmd "check-security" make -C src check-security 2>/dev/null; then
        bump_fail
    fi
fi

if [ "$QUICK" -eq 0 ]; then
    echo ""
    GTEST_PID=""
    if [ -x "src/zero-gtest" ]; then
        echo "--- GTest (excludes --fail suites: CachedWitnessesCleanIndex) ---"
        run_bg "zero-gtest" \
            ./src/zero-gtest --gtest_filter="$GTEST_PASS_EXCLUDE"
        GTEST_PID=$BG_LAST_PID
    fi

    echo ""
    BTEST_PID=""
    if [ -x "src/test/test_bitcoin" ]; then
        echo "--- Boost ---"
        if [ -n "$BOOST_PASS_EXCLUDE" ]; then
            run_bg "test_bitcoin" \
                ./src/test/test_bitcoin --run_test="$BOOST_PASS_EXCLUDE" --log_level=test_suite
        else
            run_bg "test_bitcoin" \
                ./src/test/test_bitcoin --log_level=test_suite
        fi
        BTEST_PID=$BG_LAST_PID
    fi

    echo "zero-gtest PID: $GTEST_PID"
    echo "test_bitcoin PID: $BTEST_PID"
    echo "Waiting for background tests..."
    if [ -n "$GTEST_PID" ] && ! wait "$GTEST_PID" 2>/dev/null; then
        echo "FAIL: zero-gtest (see $LOG_PREFIX-zero-gtest.log)"
        bump_fail
    fi
    if [ -n "$BTEST_PID" ] && ! wait "$BTEST_PID" 2>/dev/null; then
        echo "FAIL: test_bitcoin (see $LOG_PREFIX-test_bitcoin.log)"
        bump_fail
    fi
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
        if [ "$MODE" = "all" ]; then
            echo "--- Python RPC (rpc-tests.sh -all: -A -B -E pass) ---"
            if ! run_cmd "rpc-all" \
                env PYTHON="$PY3" "$REPO_ROOT/qa/pull-tester/rpc-tests.sh" -all; then
                bump_fail
            fi
        elif [ "$PYTHON_JOBS" -gt 1 ]; then
            echo "--- Python RPC (pass-only: ${#PYTHON_PASSING[@]} tests, jobs=$PYTHON_JOBS) ---"
            PIDS=()
            PYNAMES=()
            for t in "${PYTHON_PASSING[@]}"; do
                run_bg "rpc-$t" \
                    env PYTHON="$PY3" "$REPO_ROOT/qa/pull-tester/rpc-tests.sh" "$t"
                PIDS+=("$BG_LAST_PID")
                PYNAMES+=("$t")
                while [ "$(jobs -r 2>/dev/null | wc -l)" -ge "$PYTHON_JOBS" ]; do sleep 1; done
            done
            pi=0
            for p in "${PIDS[@]}"; do
                name="${PYNAMES[$pi]}"
                pi=$((pi + 1))
                if ! wait "$p" 2>/dev/null; then
                    echo "FAIL: parallel RPC rpc-$name (PID $p, log $LOG_PREFIX-rpc-$name.log)"
                    bump_fail
                fi
            done
        else
            echo "--- Python RPC (Tier A: rpc-tests.sh -A) ---"
            if ! run_cmd "rpc-tier-a" \
                env PYTHON="$PY3" "$REPO_ROOT/qa/pull-tester/rpc-tests.sh" -A; then
                bump_fail
            fi
        fi
    else
        echo "Skipping Python RPC tests: Python 3.10+ not found"
    fi
fi

echo ""
echo "--- Done. Logs in $LOG_DIR ---"
echo "Review: ls -la $LOG_PREFIX-*.log"
if [ "$OVERALL_FAIL" -eq 1 ]; then
    if [ "$STRICT" -eq 1 ]; then
        echo "FAIL: one or more steps failed with --strict" >&2
        exit 1
    fi
    echo "WARNING: one or more steps failed. Re-run with --strict to exit 1 on failure."
    exit 0
fi
exit 0
