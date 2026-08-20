#!/usr/bin/env bash
export LC_ALL=C
# End-to-end CPU profile of a running zerod: capture -> export -> bucket ->
# collate, with the height window derived from debug.log rather than guessed.
#
# Replaces the manual four-step sequence (xctrace record, xctrace export,
# bucket_profile2.py, profile_collate.py add) that is easy to get wrong: the
# usual mistakes are forgetting the thread filter, mis-stating the height
# window, and never collating so the capture is a one-off text file.
#
# Usage (repo root, node already running):
#   contrib/perf/profile_run.sh <scenario> [datadir] [secs] [thread]
#
#   scenario  ledger key, e.g. S3-reindex-p1-postsap
#   datadir   default: guessed from the running zerod's -datadir
#   secs      capture length, default 60
#   thread    thread filter, default zcash-loadblk
#             (use "Main Thread" for wallet rescan captures)
#
# Env:
#   ZERO_PROFILE_OUT   output dir (default test-logs/profile-<scenario>-<utc>)
#   ZERO_PROFILE_NOTE  note recorded in the ledger
#
# Exit: 0 ok, 1 no node / capture failed, 2 usage.

set -uo pipefail

SCEN="${1:?usage: profile_run.sh <scenario> [datadir] [secs] [thread]}"
DATADIR="${2:-}"
SECS="${3:-60}"
THREAD="${4:-zcash-loadblk}"

PID="$(pgrep -x zerod | head -1)"
[ -n "$PID" ] || { echo "no zerod running" >&2; exit 1; }

# Derive datadir from the process if not given.
if [ -z "$DATADIR" ]; then
  DATADIR="$(ps -o command= -p "$PID" | sed -n 's/.*-datadir=\([^ ]*\).*/\1/p')"
fi
[ -n "$DATADIR" ] || { echo "cannot determine datadir; pass it explicitly" >&2; exit 1; }

LOG="$DATADIR/debug.log"
[ -r "$LOG" ] || LOG="$DATADIR/regtest/debug.log"

UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${ZERO_PROFILE_OUT:-test-logs/profile-${SCEN}-${UTC}}"
mkdir -p "$OUT"

height_now() {
  [ -r "$LOG" ] || { echo ""; return; }
  tail -n 400 "$LOG" 2>/dev/null \
    | awk 'match($0,/height=[0-9]+/){h=substr($0,RSTART+7,RLENGTH-7)} END{print h}'
}

H0="$(height_now)"
echo "capture: pid=$PID thread=$THREAD secs=$SECS start_height=${H0:-unknown}"

if ! xcrun xctrace record --template 'Time Profiler' \
      --output "$OUT/tp.trace" --time-limit "${SECS}s" --attach "$PID" >"$OUT/xctrace.log" 2>&1; then
  echo "xctrace record failed; see $OUT/xctrace.log" >&2
  exit 1
fi
H1="$(height_now)"

xcrun xctrace export --input "$OUT/tp.trace" \
  --xpath '/trace-toc/run[1]/data[1]/table[@schema="time-profile"]' \
  --output "$OUT/tp.xml" >>"$OUT/xctrace.log" 2>&1

# Thermal state: a long capture on a hot machine is measured on a slower CPU
# than a cold one, with no marker in the time-profile table. Record it.
xcrun xctrace export --input "$OUT/tp.trace" \
  --xpath '/trace-toc/run[1]/data[1]/table[@schema="device-thermal-state-intervals"]' \
  --output "$OUT/thermal.xml" >>"$OUT/xctrace.log" 2>&1 || true
THERM="$(grep -oE 'Nominal|Fair|Serious|Critical' "$OUT/thermal.xml" 2>/dev/null | sort -u | tr '\n' ',' | sed 's/,$//')"
[ -n "$THERM" ] || THERM="unknown"

WINDOW="${H0:-0}-${H1:-0}"
python3 contrib/perf/bucket_profile2.py "$OUT/tp.xml" "$THREAD" \
  --json "$OUT/buckets.json" > "$OUT/buckets.txt" 2>&1 || {
    echo "bucketing failed; see $OUT/buckets.txt" >&2; exit 1; }

NOTE="${ZERO_PROFILE_NOTE:-}"
[ "$THERM" = "Nominal" ] || NOTE="$NOTE [thermal=$THERM]"

contrib/perf/profile_collate.py add "$OUT/buckets.json" \
  --scenario "$SCEN" --window "$WINDOW" --note "$NOTE" >/dev/null

echo "window=$WINDOW thermal=$THERM"
sed -n '/^Buckets/,/^Layers/p' "$OUT/buckets.txt" | head -12
echo "artifacts: $OUT"
