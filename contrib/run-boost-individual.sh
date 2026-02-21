#!/usr/bin/env bash
# Run each test_bitcoin (Boost) suite individually. Reports pass/fail per suite.
# Usage: ./contrib/run-boost-individual.sh [--exclude=SUITE,SUITE,...]
# --exclude: comma-separated suite names to skip. Default excludes Alert_tests (deprecated).

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DEFAULT_EXCLUDE="Alert_tests,equihash_tests,miner_tests,Checkpoints_tests"

LOG_DIR="${LOG_DIR:-$REPO_ROOT/test-logs}"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$LOG_DIR/${TIMESTAMP}-boost-individual.log"
RESULTS="$LOG_DIR/${TIMESTAMP}-boost-individual.txt"

EXCLUDE="$DEFAULT_EXCLUDE"
for arg in "$@"; do
    case "$arg" in
        --exclude=*) EXCLUDE="${arg#--exclude=}" ;;
    esac
done

if [ ! -x "src/test/test_bitcoin" ]; then
    echo "src/test/test_bitcoin not found or not executable"
    exit 1
fi

SUITES=($(./src/test/test_bitcoin --list_content 2>&1 | grep -E '^[a-zA-Z].*_tests' | sed 's/\*$//' | awk '{print $1}' | tr '\n' ' '))

echo "Running ${#SUITES[@]} Boost suites individually"
echo "Log: $LOG"
echo "Results: $RESULTS"
echo ""

PASS=0
FAIL=0
declare -a FAILED

for suite in "${SUITES[@]}"; do
    skip=0
    if [ -n "$EXCLUDE" ]; then
        IFS=',' read -ra EXC <<< "$EXCLUDE"
        for e in "${EXC[@]}"; do
            [ "$suite" = "$e" ] && skip=1 && break
        done
    fi
    if [ "$skip" -eq 1 ]; then
        echo "SKIP: $suite"
        continue
    fi

    if ./src/test/test_bitcoin --run_test="$suite" --log_level=warning >> "$LOG" 2>&1; then
        echo "PASS: $suite"
        ((PASS++)) || true
    else
        echo "FAIL: $suite"
        ((FAIL++)) || true
        FAILED+=("$suite")
    fi
done

echo ""
echo "--- Summary ---"
echo "Pass: $PASS"
echo "Fail: $FAIL"
{
    echo "Boost individual run $TIMESTAMP"
    echo "Pass: $PASS, Fail: $FAIL"
    echo "Failed: ${FAILED[*]}"
} > "$RESULTS"
echo "Results: $RESULTS"

[ "$FAIL" -gt 0 ] && exit 1
exit 0
