#!/usr/bin/env bash
export LC_ALL=C
# Run the ZeroPerf checks and the vendored Zcash linters, filtered to the code
# ZeroPerf actually owns.
#
# Why this exists: contrib/perf/zcash-lint/lint-all.sh reports every finding in
# the tree and exits 1 on roughly 200 that live in code inherited from Bitcoin
# and Zcash. Those are set aside (will not fix) -- changing them diverges from
# upstream for no functional gain. An always-red gate teaches people to ignore
# it, so this wrapper scopes the gate to contrib/perf/ and reports the rest as
# information only.
#
# Usage (from repo root):
#   contrib/perf/lint-perf.sh            # gate on contrib/perf/; exit 1 only there
#   contrib/perf/lint-perf.sh --all      # no filter; show every finding
#   contrib/perf/lint-perf.sh --summary  # one line per check, counts only
#   contrib/perf/lint-perf.sh --list     # what runs, then exit
#
# TOTAL counts exclude checks whose findings are entirely set aside (see
# SETASIDE below): whole-check categories in inherited upstream code, plus perf
# .md / .txt for the unicode check. Use --all to include them.
#
# Exit: 0 clean in owned scope, 1 findings in owned scope, 2 usage error.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 2

LINT_DIR="contrib/perf/zcash-lint"
OWNED='^contrib/perf/'
# Sourced, mode 644: a shebang is meaningless and export LC_ALL=C there would
# override the caller's locale. Both linters flag it; both are false positives.
OWNED_EXCEPT='contrib/perf/datadir_guard\.sh'
SHELLCHECK_EXCLUDE="SC2046,SC2086,SC2162,SC2035,SC2043,SC2094,SC2129,SC2164,SC2230"

# Checks whose findings are entirely in inherited upstream code and are set
# aside (will not fix). Their TOTAL is high, constant, and uninformative, so it
# is suppressed by default; --all restores it. Counts as of 2026-08-19.
SETASIDE_CHECKS="include-guards includes locale-dependence"
declare -A SETASIDE_NOTE=(
  [include-guards]="52 headers use ZCASH_/ZC_/ASYNCRPCOPERATION_ prefixes"
  [includes]="include ordering and duplication in inherited source"
  [locale-dependence]="C++ locale-dependent calls, need per-site review"
)

# --all and --summary are independent: --all widens scope, --summary suppresses
# per-finding detail. They compose.
SHOW_ALL=0
SUMMARY=0
MODE=gate
for a in "$@"; do
  case "$a" in
    --all)     SHOW_ALL=1; MODE=all ;;
    --summary) SUMMARY=1 ;;
    --list)    MODE=list ;;
    -h|--help) sed -n '3,24p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

# name -> how to run it
run_check() {
  case "$1" in
    unicode)    # Gate on code only. Perf .md and captured .txt are a separate
                # concern (see UpdateZero.md DOC-UNICODE); --all shows them.
                contrib/perf/check-unicode.py \
                  $(git ls-files 'contrib/perf/*.sh' 'contrib/perf/*.py') 2>/dev/null ;;
    self-tests) # Run every tool that has a --self-test. These pin behaviour
                # that has been wrong before (bucket ordering, fingerprint
                # dedup), so a silent regression here corrupts published
                # numbers rather than crashing.
                for t in $(git ls-files 'contrib/perf/*.py'); do
                  grep -q -- '--self-test' "$t" || continue
                  out=$(python3 "$t" --self-test 2>&1) || \
                    printf '%s: %s\n' "$t" "$(printf '%s' "$out" | tail -1)"
                done ;;
    unicode-docs) # Owned documents only. Inherited src/ and root-level
                  # Zero400-owned docs are out of scope for this gate; run
                  # check-unicode.py with no args to see the whole tree.
                  # keep/ is archived point-in-time notes: kept as written,
                  # not maintained (docs/POLICY.md S5), so not gated.
                  contrib/perf/check-unicode.py \
                    $(git ls-files 'contrib/perf/*.md' 'contrib/perf/**/*.md' \
                      | grep -v '^contrib/perf/keep/') 2>/dev/null ;;
    shellcheck) # -f gcc gives "path:line:col: level: msg", so the same
                # path filter works as for the other checks.
                shellcheck -f gcc --exclude="$SHELLCHECK_EXCLUDE" \
                  $(git ls-files 'contrib/perf/*.sh') 2>&1 ;;
    *)          bash "$LINT_DIR/lint-$1.sh" 2>&1 ;;
  esac
}

CHECKS="self-tests unicode unicode-docs shellcheck whitespace shebang shell-locale
        python-utf8-encoding include-guards includes locale-dependence
        make-dist cargo-patches"

if [ "$MODE" = list ]; then
  echo "checks: $(echo $CHECKS | tr '\n' ' ')"
  echo "owned scope: $OWNED  (except $OWNED_EXCEPT)"
  exit 0
fi

owned_lines() { grep -E "$OWNED" | grep -vE "$OWNED_EXCEPT"; }

EXIT=0
printf '%-24s %8s %10s\n' CHECK OWNED TOTAL
printf '%-24s %8s %10s\n' ------------------------ -------- ----------
for c in $CHECKS; do
  out="$(run_check "$c")"
  total=$(printf '%s' "$out" | grep -cE '[^[:space:]]' )
  owned="$(printf '%s' "$out" | owned_lines)"
  n_owned=$(printf '%s' "$owned" | grep -cE '[^[:space:]]')
  # Suppress the TOTAL for wholly set-aside checks unless --all.
  shown_total="$total"
  if [ "$SHOW_ALL" -eq 0 ] && [[ " $SETASIDE_CHECKS " == *" $c "* ]]; then
    shown_total="set aside"
    setaside_note="${SETASIDE_NOTE[$c]}"
  fi
  printf '%-24s %8s %10s\n' "$c" "$n_owned" "$shown_total"
  if [ -n "${setaside_note:-}" ] && [ "$SUMMARY" -eq 0 ]; then
    printf '    (%s)\n' "$setaside_note"
  fi
  setaside_note=""
  if [ "$n_owned" -gt 0 ]; then
    EXIT=1
    if [ "$SUMMARY" -eq 0 ]; then
      printf '%s\n' "$owned" | sed 's/^/    /'
    fi
  fi
  if [ "$SHOW_ALL" -eq 1 ] && [ "$SUMMARY" -eq 0 ] && [ "$total" -gt 0 ]; then
    printf '%s\n' "$out" | sed 's/^/  | /'
  fi
done

echo
if [ "$EXIT" -eq 0 ]; then
  echo "OWNED SCOPE CLEAN (contrib/perf/). Non-zero TOTAL is inherited"
  echo "upstream code: set aside, will not fix. See zcash-lint/ZEROPERF.md."
else
  echo "Findings in owned scope (contrib/perf/) -- fix these."
fi
exit "$EXIT"
