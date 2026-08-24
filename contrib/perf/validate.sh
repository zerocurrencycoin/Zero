#!/usr/bin/env bash
# ZeroPerf regression gate.
#
# The stage a release depends on. Compilation is standalone and slow, so the
# gate does not attach to it: a 30-second check must not wait on a multi-hour
# build. Nothing here needs a compiler.
#
#   build      zcutil/build.sh              standalone, no gate
#   validate   THIS SCRIPT                  the regression gate
#   release    zcutil/check-release.sh      requires validate to have passed
#
# Stages, fastest first, so a broken tree fails in seconds rather than minutes:
#
#   1 lint        lint-perf.sh    -- owned-scope style and policy checks
#   2 selftest    every tool's --self-test, plus perflib
#   3 harness     contrib/run-tests.sh --strict   (opt-in: --with-harness)
#
# Usage:
#   contrib/perf/validate.sh                 # lint + self-tests  (default)
#   contrib/perf/validate.sh --with-harness  # also run the product harness
#   contrib/perf/validate.sh --quick         # lint only
#   contrib/perf/validate.sh --list          # show stages, run nothing
#
# Exit: 0 all selected stages passed, 1 any failed, 2 usage error.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 1
# shellcheck source=/dev/null
. "$REPO_ROOT/contrib/perf/perflib.sh"

WITH_HARNESS=0
QUICK=0
for arg in "$@"; do
  case "$arg" in
    --with-harness) WITH_HARNESS=1 ;;
    --quick)        QUICK=1 ;;
    --list)
      echo "stages: lint selftest${WITH_HARNESS:+ harness}"
      echo "  lint      contrib/perf/lint-perf.sh"
      echo "  selftest  every contrib/perf tool with --self-test, plus perflib"
      echo "  harness   contrib/run-tests.sh --strict   (--with-harness)"
      exit 0 ;;
    -h|--help)
      sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# A gate result that exists only on a terminal cannot be cited later -- "did
# validate pass before that release?" needs an artifact. Kept per-run so a
# failure is not overwritten by the next green run.
VALIDATE_LOG="${ZERO_PERF_VALIDATE_LOG:-test-logs/validate-$(date -u +%Y%m%dT%H%M%SZ).log}"
mkdir -p "$(dirname "$VALIDATE_LOG")" 2>/dev/null || true
# shellcheck disable=SC2034  # consumed by log()/warn()/die() in perflib.sh
DRIVER_LOG="$VALIDATE_LOG"
: > "$VALIDATE_LOG"
STAGE_LIST="lint,selftest"
if [ "$WITH_HARNESS" -eq 1 ]; then STAGE_LIST="$STAGE_LIST,harness"; fi
log "validate START stages=$STAGE_LIST"
if [ -x ./src/zerod ]; then
  log "binary=$(./src/zerod --version 2>/dev/null | head -1)"
else
  log "binary=not built"
fi

FAILED=0
STAGE_RESULTS=""

record() { # record NAME STATUS
  STAGE_RESULTS="${STAGE_RESULTS}${1}=${2}"$'\n'
  log "stage $1 = $2"
  [ "$2" = PASS ] || FAILED=1
}

# --- stage 1: lint -----------------------------------------------------------
# lint-perf.sh exits 0 even with findings (it reports inherited counts too), so
# the owned-scope column is what decides. Anything non-zero there is ours.
echo "=== validate: lint ==="
LINT_OUT="$(bash contrib/perf/lint-perf.sh 2>&1)"
echo "$LINT_OUT"
printf '%s\n' "$LINT_OUT" >> "$VALIDATE_LOG"
OWNED_BAD="$(printf '%s\n' "$LINT_OUT" \
  | awk 'NR>2 && $2 ~ /^[0-9]+$/ && $2 > 0 { print $1 }')"
if [ -n "$OWNED_BAD" ]; then
  echo "FAIL: findings in owned scope:" >&2
  printf '  %s\n' $OWNED_BAD >&2
  record lint FAIL
else
  record lint PASS
fi

if [ "$QUICK" -eq 1 ]; then
  printf '\n%s' "$STAGE_RESULTS"
  if [ "$FAILED" -eq 0 ]; then
    echo "validate: PASS (quick)"
    log "validate PASS (quick)"
  else
    echo "validate: FAIL (quick)" >&2
    log "validate FAIL (quick)"
  fi
  echo "  log: $VALIDATE_LOG"
  exit "$FAILED"
fi

# --- stage 2: self-tests -----------------------------------------------------
# Run directly rather than via lint's self-tests check, so a failure names the
# tool and shows its output.
echo
echo "=== validate: self-tests ==="
ST_FAIL=0
if ! out="$(bash contrib/perf/perflib_selftest.sh 2>&1)"; then
  echo "FAIL perflib.sh"; printf '%s\n' "$out" | grep -i fail | head -5
  printf '%s\n' "$out" >> "$VALIDATE_LOG"
  ST_FAIL=1
else
  echo "  ok  perflib.sh"
fi
for tool in contrib/perf/*.py; do
  grep -q -- '--self-test' "$tool" || continue
  if out="$(python3 "$tool" --self-test 2>&1)"; then
    echo "  ok  $(basename "$tool")"
  else
    echo "FAIL $(basename "$tool")"
    printf '%s\n' "$out" | grep -i 'fail\|error' | head -5
    printf '=== %s ===\n%s\n' "$tool" "$out" >> "$VALIDATE_LOG"
    ST_FAIL=1
  fi
done
# if/else, not `A && B || C`: the latter would record BOTH results if
# `record ... PASS` ever returned non-zero.
if [ "$ST_FAIL" -eq 0 ]; then
  record selftest PASS
else
  record selftest FAIL
fi

# --- stage 3: product harness (opt-in) --------------------------------------
# Zero400 owns contrib/run-tests.sh; this composes it rather than editing it.
if [ "$WITH_HARNESS" -eq 1 ]; then
  echo
  echo "=== validate: harness ==="
  if [ ! -x ./src/zerod ]; then
    warn "src/zerod not built; harness stage skipped (build first)"
    record harness SKIP
  elif bash contrib/run-tests.sh --strict; then
    record harness PASS
  else
    record harness FAIL
  fi
fi

# --- summary -----------------------------------------------------------------
echo
echo "=== validate: summary ==="
# Herestring, not a pipe: `printf | while` runs the loop in a subshell, and
# any variable it touches is lost. The gate's exit status depends on $FAILED.
while IFS='=' read -r name status; do
  [ -n "$name" ] && printf '  %-10s %s\n' "$name" "$status"
done <<< "$STAGE_RESULTS"
if [ "$FAILED" -eq 0 ]; then
  echo "validate: PASS"
  log "validate PASS"
else
  echo "validate: FAIL" >&2
  log "validate FAIL"
fi
echo "  log: $VALIDATE_LOG"
exit "$FAILED"
