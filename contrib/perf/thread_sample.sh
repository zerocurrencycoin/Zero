#!/usr/bin/env bash
# Per-thread + per-process CPU/memory sampler.
#
# Usage: thread_sample.sh PID OUT_DIR [PERIOD_S] [N_SAMPLES] [LABEL] [DATADIR]
#
# Writes OUT_DIR/proc.tsv (whole process) and OUT_DIR/threads.tsv (per thread).
# DATADIR is optional and only supplies the height column.
#
# Column layout verified against real `ps -M` output rather than assumed:
# the process row carries USER first (NF=17+), thread rows omit it (NF=6)
# and put %CPU in $2, STIME in $5 and UTIME in $6. An earlier version read
# $3/$4 and logged STAT/PRI as if they were CPU numbers.
export LC_ALL=C
PID="$1"; OUT="$2"; PERIOD="${3:-10}"; N="${4:-30}"; LABEL="${5:-run}"; DATADIR="${6:-}"
mkdir -p "$OUT"
PROC_TSV="$OUT/proc.tsv"; THR_TSV="$OUT/threads.tsv"
[ -s "$PROC_TSV" ] || printf "ts\tlabel\tpid\tpct_cpu\tpct_mem\trss_kb\tnth\tnrun\tphys_mb\theight\n" > "$PROC_TSV"
[ -s "$THR_TSV" ]  || printf "ts\tlabel\tpid\ttid\tpct_cpu\tstate\tstime\tutime\n" > "$THR_TSV"
for _ in $(seq 1 "$N"); do
  kill -0 "$PID" 2>/dev/null || break
  ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  # Height comes from the datadir under test, passed in -- never a glob over
  # /tmp. An earlier version globbed /tmp/zero-lab-*/debug.log and recorded a
  # stale height from a previous run when the caller used another path.
  h=""
  if [ -n "$DATADIR" ] && [ -f "$DATADIR/debug.log" ]; then
    h=$(grep -o 'height=[0-9]*' "$DATADIR/debug.log" 2>/dev/null | tail -1 | cut -d= -f2)
  fi
  read -r c m r <<<"$(ps -o %cpu=,%mem=,rss= -p "$PID" 2>/dev/null | head -1)"
  # #TH reads "28/3" (total/running) when any thread is on-core, else "28".
  th=$(top -l 1 -pid "$PID" -stats th 2>/dev/null | tail -1 | tr -d ' ')
  nth=${th%%/*}; nrun=${th##*/}; [ "$nrun" = "$th" ] && nrun=0
  phys=$(vmmap -summary "$PID" 2>/dev/null | awk -F: '/Physical footprint:/{
      v=$2; gsub(/^[ \t]+|[ \t]+$/,"",v);
      if(v~/G/){gsub(/[^0-9.]/,"",v); printf "%.1f", v*1024; exit}
      if(v~/M/){gsub(/[^0-9.]/,"",v); printf "%.1f", v; exit}
      if(v~/K/){gsub(/[^0-9.]/,"",v); printf "%.1f", v/1024; exit}}')
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "$ts" "$LABEL" "$PID" "${c:-}" "${m:-}" "${r:-}" "${nth:-}" "${nrun:-}" "${phys:-}" "${h:-}" >> "$PROC_TSV"
  ps -M "$PID" 2>/dev/null | awk -v ts="$ts" -v lb="$LABEL" -v pid="$PID" '
      NF==6 && $1 ~ /^[0-9.]+$/ { n++; printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", ts, lb, pid, n, $2, $3, $5, $6 }
      NF>=15 { n++; printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", ts, lb, pid, n, $4, $5, $7, $8 }' >> "$THR_TSV"
  sleep "$PERIOD"
done
