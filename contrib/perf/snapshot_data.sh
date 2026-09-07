#!/usr/bin/env bash
# Copy a data file aside before it is overwritten, so the prior revision
# survives the update that replaces it.
#
# Lab scratch is disposable and ledgers are append-only, but the collated
# outputs -- REPORT.md, collation.json, util.tsv, measures_*.csv -- are
# rewritten in place by each run. Without a copy the previous revision is
# gone, and "what did this say before the change?" is unanswerable.
#
# Usage: snapshot_data.sh FILE [FILE...]
# Writes FILE.prev-<utc> next to each existing FILE. Missing files are
# skipped, not created: there is no prior revision of a file that does not
# exist yet.

export LC_ALL=C
set -euo pipefail

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
rc=0

for f in "$@"; do
  if [ ! -e "$f" ]; then
    echo "skip (absent): $f"
    continue
  fi
  dest="${f}.prev-${stamp}"
  if cp -p "$f" "$dest"; then
    echo "saved: $dest"
  else
    echo "ERROR: could not copy $f" >&2
    rc=1
  fi
done

exit "$rc"
