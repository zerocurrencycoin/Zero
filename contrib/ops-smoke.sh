#!/usr/bin/env bash
# Zero400 ops smoke: COLD, RESTART, ATTACH only.
# Scratch datadir is outside the repo. Conf from contrib/conf-templates/lab.conf.
#
#   contrib/ops-smoke.sh cold
#   contrib/ops-smoke.sh restart
#   contrib/ops-smoke.sh attach
#
# Env: ZERO_OPS_LAB (default $TMPDIR/zero400-ops), ZERO_RPCPORT (default 23941)
set -euo pipefail
ME="ops-smoke"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/../zcutil/fzero.sh"
ZEROD="${ZEROD:-$REPO_ROOT/src/zerod}"
ZERO_CLI="${ZERO_CLI:-$REPO_ROOT/src/zero-cli}"
LAB="${ZERO_OPS_LAB:-${TMPDIR:-/tmp}/zero400-ops}"
RPCPORT="${ZERO_RPCPORT:-23941}"
LEDGER="${ZERO_OPS_LEDGER:-$ZERO_BUILD_DIR/ops-status.jsonl}"
CMD="${1:-}"

usage() {
  echo "Usage: contrib/ops-smoke.sh cold|start|restart|attach"
}

refuse_lab() {
  local d
  d="$(cd "$1" 2>/dev/null && pwd -P || echo "$1")"
  case "$d" in
    "$HOME/Library/Application Support/zero"|"$HOME/Library/Application Support/Zero"|"$HOME/.zero")
      echo "ERROR: LAB is default user datadir" >&2; exit 1 ;;
  esac
  case "$d" in
    "$REPO_ROOT"|"$REPO_ROOT"/*)
      echo "ERROR: LAB must not be under Zero400" >&2; exit 1 ;;
  esac
}

cli() { "$ZERO_CLI" -datadir="$LAB" -rpcport="$RPCPORT" "$@"; }

append_ledger() {
  mkdir -p "$(dirname "$LEDGER")"
  printf '{"ts":"%s","id":"%s","exit":%s,"head":"%s","zerod":"%s","lab":"%s"}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" \
    "$(git -C "$REPO_ROOT" rev-parse --short HEAD)" \
    "$(shasum -a 256 "$ZEROD" | awk '{print $1}')" \
    "$LAB" >> "$LEDGER"
}

[[ -x "$ZEROD" ]] || { echo "missing $ZEROD" >&2; exit 1; }
[[ -n "$CMD" ]] || { usage >&2; exit 2; }

case "$CMD" in
  cold)
    refuse_lab "$LAB"
    mkdir -p "$LAB"
    rm -rf "$LAB/blocks" "$LAB/chainstate" "$LAB/wallet.zero" "$LAB/.lock" "$LAB/debug.log" "$LAB/.cookie"
    ZERO_RPCPORT="$RPCPORT" "$REPO_ROOT/contrib/zero-conf.sh" lab -dir "$LAB" -out zero.conf -force
    "$ZEROD" -datadir="$LAB" -daemon -listen=0 -connect=0 -maxconnections=0 -rpcport="$RPCPORT"
    cli -rpcwait getblockchaininfo >/dev/null
    h="$(cli getblockcount)"
    cli stop >/dev/null
    echo "OPS-START-COLD height=$h"
    append_ledger OPS-START-COLD 0
    ;;
  start)
    refuse_lab "$LAB"
    mkdir -p "$LAB"
    rm -rf "$LAB/blocks" "$LAB/chainstate" "$LAB/wallet.zero" "$LAB/.lock" "$LAB/debug.log" "$LAB/.cookie"
    ZERO_RPCPORT="$RPCPORT" "$REPO_ROOT/contrib/zero-conf.sh" lab -dir "$LAB" -out zero.conf -force
    "$ZEROD" -datadir="$LAB" -daemon -listen=0 -connect=0 -maxconnections=0 -rpcport="$RPCPORT"
    cli -rpcwait getblockchaininfo >/dev/null
    echo "OPS-START running rpcport=$RPCPORT (attach or stop via zero-cli)"
    append_ledger OPS-START 0
    ;;
  restart)
    refuse_lab "$LAB"
    [[ -f "$LAB/zero.conf" ]] || { echo "run cold first" >&2; exit 1; }
    cli stop >/dev/null 2>&1 || true
    sleep 2
    h0="$(cli getblockcount 2>/dev/null || echo NA)"
    "$ZEROD" -datadir="$LAB" -daemon -listen=0 -connect=0 -maxconnections=0 -rpcport="$RPCPORT"
    cli -rpcwait getblockcount >/dev/null
    h1="$(cli getblockcount)"
    cli stop >/dev/null
    echo "OPS-RESTART height=$h1 (before_stop=${h0})"
    append_ledger OPS-RESTART 0
    ;;
  attach)
    refuse_lab "$LAB"
    cli -rpcwait getblockchaininfo
    cli getnetworkinfo >/dev/null
    cli getwalletinfo >/dev/null 2>&1 || true
    echo "OPS-ATTACH ok"
    append_ledger OPS-ATTACH 0
    ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac
