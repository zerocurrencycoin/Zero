#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Write or verify SHA256SUMS for release artifacts. --help for options.
set -euo pipefail
# shellcheck disable=SC2034
ME="checksums"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

usage() {
  cat <<'USAGE'
Usage: zcutil/checksums.sh [--verify] [DIR]

Write DIR/SHA256SUMS covering every file in DIR (default: artifacts), or check
the files against an existing SHA256SUMS with --verify. The file uses the
sha256sum format, so operators can check it with `sha256sum -c SHA256SUMS` on
Linux or `shasum -a 256 -c SHA256SUMS` on macOS.

Run after platform signing (codesign, Authenticode): signing changes the files.
SHA256SUMS itself and its signatures (SHA256SUMS.asc, SHA256SUMS.sig) are not listed.

  --verify     check DIR against DIR/SHA256SUMS; exit 1 on any mismatch
  -h | --help  this text
USAGE
}

VERIFY=0
DIR="artifacts"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --verify) VERIFY=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) usage >&2; exit 2 ;;
    *) DIR="$1"; shift ;;
  esac
done

[ -d "$DIR" ] || err "directory not found: $DIR"
cd "$DIR"

if [ "$VERIFY" -eq 1 ]; then
  [ -f SHA256SUMS ] || err "no SHA256SUMS in $DIR"
  sha256_cmd -c SHA256SUMS || err "checksum mismatch in $DIR"
  step_done "Verify SHA256SUMS"
  exit 0
fi

FILES=()
while IFS= read -r f; do FILES+=("$f"); done < <(
  find . -maxdepth 1 -type f ! -name 'SHA256SUMS' ! -name 'SHA256SUMS.*' ! -name '.*' | sed 's|^\./||' | LC_ALL=C sort
)
[ "${#FILES[@]}" -gt 0 ] || err "no files to hash in $DIR"

sha256_cmd "${FILES[@]}" > SHA256SUMS.tmp
mv SHA256SUMS.tmp SHA256SUMS
sha256_cmd -c SHA256SUMS >/dev/null || err "written SHA256SUMS does not verify"
step_done "Write SHA256SUMS (${#FILES[@]} files)"
notice "$DIR/SHA256SUMS"
