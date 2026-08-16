#!/usr/bin/env bash
# Write a zero.conf from contrib/conf-templates/.
# Default: template prod, file /tmp/zero.conf
#
#   contrib/zero-conf.sh
#   contrib/zero-conf.sh lab -dir /tmp/zero400-ops
#   contrib/zero-conf.sh insight -dir ~/.zero -force
#
# -dir DIR     directory (default /tmp)
# -out NAME    filename (default zero.conf)
# -force       overwrite; also allow ~/.zero, Application Support/zero|Zero, and the repo
set -euo pipefail
ME="zero-conf"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/../zcutil/fzero.sh"

TPL_DIR="$REPO_ROOT/contrib/conf-templates"
NAME="prod"
DIR="/tmp"
OUTNAME="zero.conf"
FORCE=0
RPCUSER="${ZERO_RPCUSER:-}"
RPCPASSWORD="${ZERO_RPCPASSWORD:-}"
RPCPORT="${ZERO_RPCPORT:-}"
DBCACHE="${ZERO_DBCACHE:-}"

usage() {
  echo "Usage: contrib/zero-conf.sh [template] [-dir DIR] [-out NAME] [-force]"
  echo "Templates: prod (default), test, lab, node, zerowallet, insight, full"
  echo "Default path: /tmp/zero.conf"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -dir|--dir) DIR="${2:?}"; shift 2 ;;
    -dir=*) DIR="${1#-dir=}"; shift ;;
    -out|--out) OUTNAME="${2:?}"; shift 2 ;;
    -out=*) OUTNAME="${1#-out=}"; shift ;;
    -force|--force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "unknown $1" >&2; usage >&2; exit 2 ;;
    *)
      if [[ "$NAME" != "prod" && -n "${1:-}" ]]; then
        echo "unexpected arg $1" >&2; exit 2
      fi
      NAME="${1%.conf}"
      shift
      ;;
  esac
done

SRC="$TPL_DIR/${NAME}.conf"
[[ -f "$SRC" ]] || { echo "missing template $SRC" >&2; usage >&2; exit 1; }

case "$NAME" in
  lab|test) : "${RPCUSER:=lab}"; : "${RPCPASSWORD:=lab}"; : "${RPCPORT:=23941}" ;;
  *)        : "${RPCUSER:=zero}"; : "${RPCPASSWORD:=zero}"; : "${RPCPORT:=23811}" ;;
esac

resolve() { (cd "$1" 2>/dev/null && pwd -P) || echo "$1"; }
mkdir -p "$DIR"
dest_res="$(resolve "$DIR")"
OUT="$DIR/$OUTNAME"

protected=0
case "$dest_res" in
  "$HOME/Library/Application Support/zero"|"$HOME/Library/Application Support/Zero"|"$HOME/.zero")
    protected=1 ;;
esac
case "$dest_res" in
  "$REPO_ROOT"|"$REPO_ROOT"/*) protected=1 ;;
esac

if [[ "$protected" -eq 1 ]] && [[ "$FORCE" -ne 1 ]]; then
  echo "ERROR: $dest_res is a default datadir or the product tree (pass -force)" >&2
  exit 1
fi
if [[ -f "$OUT" ]] && [[ "$FORCE" -ne 1 ]]; then
  echo "ERROR: $OUT exists (pass -force)" >&2
  exit 1
fi

PY="$(find_python3)" || err "Python 3.10+ required"
"$PY" - "$SRC" "$RPCUSER" "$RPCPASSWORD" "$RPCPORT" "$DBCACHE" "$OUT" <<'PY'
import sys
src, user, password, port, dbcache, out = sys.argv[1:7]
body = open(src, encoding="utf-8").read()
body = body.replace("@RPCUSER@", user).replace("@RPCPASSWORD@", password).replace("@RPCPORT@", port)
if dbcache:
    body = body.replace("@DBCACHE@", dbcache)
    body = body.replace("#dbcache=@DBCACHE@", "dbcache=" + dbcache)
else:
    body = body.replace("dbcache=@DBCACHE@\n", "")
    body = body.replace("#dbcache=@DBCACHE@\n", "")
open(out, "w", encoding="utf-8").write(body)
print("wrote", out)
PY
