#!/usr/bin/env bash
# Self-test for perflib.sh.
#
# perflib owns the value guards and the datadir disposition policy, so a
# regression here silently destroys a datadir or fabricates a number. Both
# directions are asserted: the guard fires when it should, and does not when
# it should not.
#
#   contrib/perf/perflib_selftest.sh
#
# Exit: 0 all pass, 1 any failure.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$HERE/perflib.sh"

FAILED=0
check() { # check CONDITION_RC MESSAGE
  if [ "$1" -ne 0 ]; then echo "FAIL: $2" >&2; FAILED=1; fi
}
# ok_if CONDITION... -- runs the condition as a command, so $? is unambiguous.
ok_if() {
  local msg="$1"; shift
  if ! "$@"; then echo "FAIL: $msg" >&2; FAILED=1; fi
}
eq() { # eq ACTUAL EXPECTED MESSAGE
  if [ "$1" != "$2" ]; then
    echo "FAIL: $3 (got '$1', want '$2')" >&2; FAILED=1
  fi
}
# Run a command in a subshell, expecting it to exit non-zero (die).
expect_fail() {
  local msg="$1"; shift
  if ( "$@" ) >/dev/null 2>&1; then
    echo "FAIL: $msg -- expected failure, got success" >&2; FAILED=1
  fi
}
expect_ok() {
  local msg="$1"; shift
  if ! ( "$@" ) >/dev/null 2>&1; then
    echo "FAIL: $msg -- expected success, got failure" >&2; FAILED=1
  fi
}

# ------------------------------------------------------------ value guards ---

expect_ok   "integer accepted"            require_num h 100
expect_ok   "decimal accepted"            require_num r 12.5
expect_fail "empty rejected"              require_num h ""
expect_fail "text rejected"               require_num h abc
expect_fail "two dots rejected"           require_num h 1.2.3

expect_ok   "zero is non-negative"        nonneg n 0
expect_fail "negative height rejected"    nonneg "height" -5
expect_fail "negative duration rejected"  nonneg "elapsed_s" -0.5

expect_ok   "positive accepted"           positive d 1
expect_fail "zero rejected as positive"   positive d 0
expect_fail "0.0 rejected as positive"    positive d 0.0

# safe_div: the divide-by-zero path must not crash and must not invent a value.
eq "$(safe_div 10 4)"           "2.5000" "safe_div computes"
eq "$(safe_div 10 0 2>/dev/null)"  ""    "safe_div by zero yields empty"
if safe_div 10 0 >/dev/null 2>&1; then
  echo "FAIL: safe_div by zero must return non-zero rc" >&2; FAILED=1
fi
eq "$(safe_div 10 0 NA 2>/dev/null)" "NA" "safe_div by zero honours a default"
eq "$(safe_div x 4 2>/dev/null)"    ""    "safe_div rejects a non-numeric operand"
# A zero NUMERATOR is legitimate: 0 ms over 100 blocks is 0, not an error.
eq "$(safe_div 0 100)"          "0.0000" "zero numerator is a real result"

# span_blocks: inclusive, and sign-checked.
eq "$(span_blocks 100 199)" "100" "span is inclusive of both ends"
eq "$(span_blocks 500 500)" "1"   "single-block span is 1, not 0"
expect_fail "reversed span rejected" span_blocks 200 100

# --------------------------------------------------- datadir disposition ----

TMP="$(mktemp -d)"
trap 'rm -r "$TMP" 2>/dev/null || true' EXIT

# aside (default): existing tree preserved, fresh one created.
DD="$TMP/dd"
mkdir -p "$DD"; echo marker > "$DD/keepme"
( unset ZERO_PERF_DATADIR_POLICY; dispose_datadir "$DD" TEST ) >/dev/null 2>&1
check $? "aside policy succeeds"
ok_if "aside recreates the datadir" test -d "$DD"
[ -f "$DD/keepme" ] && { echo "FAIL: aside must not leave old contents in place" >&2; FAILED=1; }
ASIDE_COUNT=$(find "$TMP" -maxdepth 1 -name 'dd.aside-*' | wc -l | tr -d ' ')
eq "$ASIDE_COUNT" "1" "aside preserves the old tree under a timestamped name"
KEPT=$(find "$TMP" -maxdepth 1 -name 'dd.aside-*' | head -1)
ok_if "set-aside tree still holds the original contents" test -f "$KEPT/keepme"

# keep: reuse in place, contents survive.
DD2="$TMP/dd2"; mkdir -p "$DD2"; echo m > "$DD2/keepme"
( ZERO_PERF_DATADIR_POLICY=keep dispose_datadir "$DD2" TEST ) >/dev/null 2>&1
check $? "keep policy succeeds"
ok_if "keep leaves existing contents alone" test -f "$DD2/keepme"

# external: must not create or modify anything.
DD3="$TMP/dd3"
( ZERO_PERF_DATADIR_POLICY=external dispose_datadir "$DD3" TEST ) >/dev/null 2>&1
check $? "external policy succeeds"
ok_if "external does not create the datadir" test ! -d "$DD3"

# replace: destructive, and only on request.
DD4="$TMP/dd4"; mkdir -p "$DD4"; echo m > "$DD4/gone"
( ZERO_PERF_DATADIR_POLICY=replace dispose_datadir "$DD4" TEST ) >/dev/null 2>&1
check $? "replace policy succeeds"
ok_if "replace recreates the datadir" test -d "$DD4"
[ -f "$DD4/gone" ] && { echo "FAIL: replace must remove old contents" >&2; FAILED=1; }
ASIDE_AFTER=$(find "$TMP" -maxdepth 1 -name 'dd4.aside-*' | wc -l | tr -d ' ')
eq "$ASIDE_AFTER" "0" "replace does not set aside"

# Deletion is `rm -r`; -f only under force. A file the user cannot remove
# must surface as an error, not be forced through.
DD7="$TMP/dd7"; mkdir -p "$DD7/sub"; echo m > "$DD7/sub/f"; chmod 500 "$DD7/sub"
( ZERO_PERF_DATADIR_POLICY=replace dispose_datadir "$DD7" TEST ) >/dev/null 2>&1
RC=$?
chmod 700 "$DD7/sub" 2>/dev/null || true
ok_if "un-removable tree reports an error rather than forcing" test "$RC" -ne 0
( ZERO_PERF_DATADIR_POLICY=replace ZERO_PERF_FORCE=1 dispose_datadir "$DD7" TEST ) >/dev/null 2>&1
ok_if "force removes what plain rm -r could not" test -d "$DD7"

# An unknown policy must fail loudly rather than silently defaulting.
expect_fail "unknown policy rejected" \
  env ZERO_PERF_DATADIR_POLICY=bogus bash -c \
  ". '$HERE/perflib.sh'; dispose_datadir '$TMP/dd5' TEST"

# The default really is aside, not replace: a caller that sets nothing must
# not lose data.
DD6="$TMP/dd6"; mkdir -p "$DD6"; echo m > "$DD6/keepme"
( unset ZERO_PERF_DATADIR_POLICY; dispose_datadir "$DD6" TEST ) >/dev/null 2>&1
ok_if "default policy is aside (data-preserving), not replace" \
  test "$(find "$TMP" -maxdepth 1 -name 'dd6.aside-*' | wc -l | tr -d ' ')" = "1"

# A live datadir must still be refused regardless of policy. The path is
# resolved for THIS platform (zeropaths.py) rather than hardcoded: ~/.zero is
# live on Unix but is not a Zero path at all on macOS or Windows.
LIVE_DD="$(python3 "$HERE/zeropaths.py" --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["datadir"])')"
expect_fail "live datadir refused even under replace" \
  env ZERO_PERF_DATADIR_POLICY=replace bash -c \
  ". '$HERE/perflib.sh'; dispose_datadir '$LIVE_DD' TEST"

# ... and refused under the data-preserving default too, so no policy is a
# way around the guard.
expect_fail "live datadir refused under the default policy" \
  bash -c ". '$HERE/perflib.sh'; dispose_datadir '$LIVE_DD' TEST"

# EVERY plausible production datadir name is refused, on every platform and
# under every policy -- including names this host would not itself create.
# The original incident was an attempt to delete a production datadir.
for PROD in "$HOME/.zero" "$HOME/Library/Application Support/zero" \
            "$HOME/Library/Application Support/Zero" \
            "$HOME/AppData/Roaming/zero" "$HOME/zero"; do
  for POL in aside replace keep external; do
    expect_fail "production datadir refused (policy=$POL): $PROD" \
      env ZERO_PERF_DATADIR_POLICY="$POL" bash -c \
      ". '$HERE/perflib.sh'; dispose_datadir '$PROD' TEST"
  done
  # Force must not be an escape hatch for a production path.
  expect_fail "force does not bypass production-datadir protection: $PROD" \
    env ZERO_PERF_DATADIR_POLICY=replace ZERO_PERF_FORCE=1 bash -c \
    ". '$HERE/perflib.sh'; dispose_datadir '$PROD' TEST"
  # Contents are protected too, not just the directory itself.
  expect_fail "contents of a production datadir refused: $PROD/blocks" \
    bash -c ". '$HERE/perflib.sh'; dispose_datadir '$PROD/blocks' TEST"
done

# ZERO_PERF_ALLOW_LIVE_DATADIR permits READING a live datadir. It must not
# also authorise destroying one: it is routinely set for a whole session, so a
# destructive policy would otherwise run unchallenged. This deleted a real
# datadir during development.
for PROD in "$HOME/.zero" "$HOME/Library/Application Support/zero"; do
  for POL in aside replace recreate; do
    expect_fail "ALLOW_LIVE_DATADIR alone must not permit '$POL' on $PROD" \
      env ZERO_PERF_ALLOW_LIVE_DATADIR=1 ZERO_PERF_DATADIR_POLICY="$POL" \
      bash -c ". '$HERE/perflib.sh'; dispose_datadir '$PROD' TEST"
  done
  # Non-destructive policies stay available under the read override.
  expect_ok "ALLOW_LIVE_DATADIR still permits 'keep' on $PROD" \
    env ZERO_PERF_ALLOW_LIVE_DATADIR=1 ZERO_PERF_DATADIR_POLICY=keep \
    bash -c ". '$HERE/perflib.sh'; dispose_datadir '$PROD' TEST"
done

# perflib must locate its own directory under zsh as well as bash. Under zsh
# BASH_SOURCE is unset; it previously resolved to $PWD, so the guard file was
# "not found" and every call took the fail-closed branch.
if command -v zsh >/dev/null 2>&1; then
  ZDIR=$(zsh -c ". '$HERE/perflib.sh'; printf '%s' \"\$_PERFLIB_DIR\"" 2>/dev/null)
  ok_if "perflib resolves its directory under zsh" test "$ZDIR" = "$HERE"
fi

# Scratch paths must still work, or the lab cannot run.
for OKDIR in "$TMP/scratch-ok" "$TMP/.zero-lab"; do
  expect_ok "scratch path remains usable: $OKDIR" \
    bash -c ". '$HERE/perflib.sh'; dispose_datadir '$OKDIR' TEST"
done

# ------------------------------------------------------------------ misc ----

# warn/die must reach the driver log, not stderr only. A failed run
# previously left a log showing normal progress and no error.
LOGF="$TMP/driver.log"
# Run in a child shell so DRIVER_LOG is exported into it; shellcheck cannot
# see the use across the source boundary either way.
# shellcheck disable=SC2016  # $1 must expand in the child, not here
env DRIVER_LOG="$LOGF" bash -c \
  '. "$1/perflib.sh"; log "normal"; warn "a warning"' _ "$HERE" >/dev/null 2>&1
ok_if "log() writes to DRIVER_LOG"    grep -q "normal" "$LOGF"
ok_if "warn() writes to DRIVER_LOG"   grep -q "WARNING: a warning" "$LOGF"
# shellcheck disable=SC2016  # $1 must expand in the child, not here
env DRIVER_LOG="$LOGF" bash -c \
  '. "$1/perflib.sh"; die "fatal thing"' _ "$HERE" >/dev/null 2>&1
ok_if "die() writes to DRIVER_LOG"    grep -q "ERROR: fatal thing" "$LOGF"
# ... and still work with no DRIVER_LOG set, rather than erroring.
expect_ok "warn() tolerates an unset DRIVER_LOG" \
  bash -c ". '$HERE/perflib.sh'; warn 'no log configured'"

ok_if "utc_stamp returns a value" test -n "$(utc_stamp)"
case "$(run_id tiny)" in tiny-*Z) ;; *) echo "FAIL: run_id shape" >&2; FAILED=1 ;; esac
ok_if "log emits without DRIVER_LOG set" test -n "$(log hello)"

# ------------------------------------------------------ run verification ---

VERDIR="$(mktemp -d)"
trap 'rm -rf "$VERDIR"' EXIT

: > "$VERDIR/empty.log"
printf 'Running testscript a\n--- Success: a ---\nTests completed: 1\n' \
  > "$VERDIR/good.log"
printf 'Running testscript a\nRunning testscript b\n--- Success: a ---\n' \
  > "$VERDIR/partial.log"

expect_fail "require_file rejects a missing artifact" \
  bash -c ". '$HERE/perflib.sh'; require_file '$VERDIR/nosuch.log' run"
expect_fail "require_file rejects an empty artifact" \
  bash -c ". '$HERE/perflib.sh'; require_file '$VERDIR/empty.log' run"
expect_ok   "require_file accepts a written artifact" \
  bash -c ". '$HERE/perflib.sh'; require_file '$VERDIR/good.log' run"

expect_ok   "require_marker finds the completion marker" \
  bash -c ". '$HERE/perflib.sh'; require_marker '$VERDIR/good.log' '^Tests completed:' rpc"
# A suite killed part-way exits without its marker; that must not read as success.
expect_fail "require_marker rejects an incomplete run" \
  bash -c ". '$HERE/perflib.sh'; require_marker '$VERDIR/partial.log' '^Tests completed:' rpc"

eq "$(count_matches "$VERDIR/good.log" '^Running testscript')" 1 "count_matches counts"
eq "$(count_matches "$VERDIR/nosuch.log" 'anything')" 0 "count_matches is 0 when absent"

expect_ok "counts agree on a clean run" \
  bash -c ". '$HERE/perflib.sh'; require_counts_agree '$VERDIR/good.log' \
           '^Running testscript' '^--- Success' '^!!! FAIL' rpc"
# 2 started, 1 passed, 0 failed: the suite lost a test without reporting it.
expect_fail "counts disagree when a test vanished" \
  bash -c ". '$HERE/perflib.sh'; require_counts_agree '$VERDIR/partial.log' \
           '^Running testscript' '^--- Success' '^!!! FAIL' rpc"

if [ "$FAILED" -eq 0 ]; then echo "self-test OK" >&2; else echo "self-test FAILED" >&2; fi
exit "$FAILED"
