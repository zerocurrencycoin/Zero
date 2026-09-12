#!/usr/bin/env bash
# Known-good source queries. Wraps ripgrep with the flags that make a result
# trustworthy, and fails loudly instead of returning an empty set that reads
# like "no matches".
#
# Written because ad-hoc greps produced two wrong answers in one session:
#   - `grep --include=*.cpp` under zsh: the glob was expanded by the shell,
#     matched nothing, and printed nothing. An empty result was reported as
#     "only one call site". zsh also aborts the whole command on a
#     non-matching glob, so the surrounding pipeline never ran.
#   - `awk -F=` against colon-separated `vmmap` output: every field empty,
#     every value recorded as blank, no error.
#
# The rule both violate: a query that cannot match must say so, not return
# nothing quietly.
#
#   codequery.sh symbol <regex> [path...]   -- C/C++ callers of a symbol
#   codequery.sh files  <regex> [path...]   -- files containing a match
#   codequery.sh count    <regex> [path...] -- per-file match counts, ALL file types
#   codequery.sh countcxx <regex> [path...] -- per-file match counts, C/C++ only
#   codequery.sh raw    <rg args...>        -- escape hatch, still checked
#
# Exit: 0 matches found, 1 no matches (explicitly reported), 2 bad usage.

export LC_ALL=C
set -uo pipefail

die() { echo "codequery: $*" >&2; exit 2; }
command -v rg >/dev/null 2>&1 || die "ripgrep (rg) not installed"

mode="${1:-}"; shift || die "usage: codequery.sh {symbol|files|count|countcxx|raw} PATTERN [PATH...]"
[ -n "$mode" ] || die "missing mode"

# Scope is always stated. With no PATH, search the repository root rather than
# whatever the caller happened to cd into: a query answered over an assumed
# subtree and reported as tree-wide is how "no bitcoin.conf anywhere" was
# recorded when nine files had it.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
scope_note() {
  if [ "$#" -eq 0 ]; then
    echo "codequery: scope = repository root ($REPO_ROOT)" >&2
  fi
}

# Build-artifact and vendored trees that make a source question unanswerable:
# .deps/*.Po list every header a translation unit touched, so any symbol
# appears to be "used" everywhere.
COMMON=(--no-heading --line-number --color never
        --glob '!**/.deps/**' --glob '!**/*.Po' --glob '!depends/work/**'
        --glob '!**/obj/**' --glob '!**/build/**'
        --glob '!.git/**' --glob '!depends/**' --glob '!**/.prev-*'
        --glob '!test-logs/**' --glob '!reindex-profile/**')

case "$mode" in
  symbol)
    pat="${1:-}"; [ -n "$pat" ] || die "symbol: missing PATTERN"; shift
    # \b...\s*\( -- an actual call or declaration, not a substring. `ub_` as a
    # bare substring also matches sub_, pub_, stub_.
    rg "${COMMON[@]}" --type-add 'cxx:*.{c,cc,cpp,h,hpp,tcc}' -t cxx \
       "\\b${pat}\\s*\\(" "$@"
    ;;
  files)
    pat="${1:-}"; [ -n "$pat" ] || die "files: missing PATTERN"; shift
    rg "${COMMON[@]}" --files-with-matches \
       --type-add 'cxx:*.{c,cc,cpp,h,hpp,tcc}' -t cxx "$pat" "$@" | sort
    ;;
  count)
    # No -t filter: count answers "how many, where", and restricting it to C++
    # silently excludes shell, Python, docs and service files. A question about
    # a config filename or a flag name lives mostly outside src/, and reporting
    # "no matches" for a file type that was never searched is the exact failure
    # this tool exists to prevent. Use `countcxx` for the C/C++-only count.
    pat="${1:-}"; [ -n "$pat" ] || die "count: missing PATTERN"; shift
    scope_note "$@"; set -- "${@:-$REPO_ROOT}"
    rg "${COMMON[@]}" --count-matches "$pat" "$@" | sort -t: -k2 -rn
    ;;
  countcxx)
    pat="${1:-}"; [ -n "$pat" ] || die "countcxx: missing PATTERN"; shift
    scope_note "$@"; set -- "${@:-$REPO_ROOT}"
    rg "${COMMON[@]}" --count-matches \
       --type-add 'cxx:*.{c,cc,cpp,h,hpp,tcc}' -t cxx "$pat" "$@" | sort -t: -k2 -rn
    ;;
  raw)
    rg "${COMMON[@]}" "$@"
    ;;
  *) die "unknown mode '$mode'" ;;
esac

rc=$?
# rg exits 1 for "no matches". Say it, rather than leaving a silent empty set
# that a caller will read as a substantive answer.
if [ "$rc" -eq 1 ]; then
  echo "codequery: NO MATCHES for this query (this is an answer, not an error)" >&2
fi
exit "$rc"
