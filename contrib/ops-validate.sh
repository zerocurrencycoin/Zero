#!/usr/bin/env bash
# Runtime ops validation: one catalog id per invocation.
# Copy this file to Zero400 as contrib/ops-validate.sh later.
#
# Interesting (operator-equivalent data, this binary):
#   contrib/ops-validate.sh live     # RPC to SRC (operator datadir); does not start or stop
#   contrib/ops-validate.sh attach   # RPC to LAB; does not start or stop
#   contrib/ops-validate.sh copy     # rsync blocks/chainstate into LAB, isolated start, wait stable tip
#
# Binary-up only (not a wallet/sync test):
#   contrib/ops-validate.sh cold
#
# Load exercises (one trial per invocation; default -disablewallet, stop 100000):
#   contrib/ops-validate.sh reindex            # -reindex tiny snap to 100000
#   contrib/ops-validate.sh reindex all        # -reindex to snap tip (tiny 187417)
#   contrib/ops-validate.sh reindex all p0     # same, inject wallet id 0
#   contrib/ops-validate.sh rescan p0          # keep indexes, -rescan, wait Done loading
#   contrib/ops-validate.sh bootstrap          # -loadblock to 100000
#   contrib/ops-validate.sh bootstrap all      # -loadblock to end of file
#   contrib/ops-validate.sh wallets            # list p0/p1/fat paths
# Add keep / --keep / ZERO_OPS_KEEP=1 to leave LAB zerod up, then attach (not live).
# Wallet: p0|p1|fat|none or --wallet=PATH (default none = -disablewallet).
#
# Env:
#   ZERO_OPS_LAB       scratch for copy/cold/reindex (default $TMPDIR/zero-ops-validate)
#   ZERO_OPS_SRC       read-only source (default ~/Library/Application Support/zero)
#   ZERO_OPS_WALLET    wallet path (overrides p0/p1/fat). default empty = -disablewallet
#   ZERO_OPS_WALLET_P0 / P1 / FAT   catalog paths (default SRC/wallet.zero0, personalbak, wallet.zero)
#   ZERO_OPS_SNAP      tiny|short|full  (reindex/rescan chain; default tiny). also snap=tiny
#   ZERO_OPS_TARGET    stop height (default 100000). all = to end / snap tip
#   ZERO_OPS_BOOTSTRAP / LOADBLOCK   bootstrap.dat copy (not the lab original)
#   ZERO_OPS_KEEP      1 = do not stop LAB zerod (then attach / stop)
#   ZERO_RPCPORT       LAB rpcport (default 23941). live uses SRC conf rpcport.
#   ZERO_OPS_WAIT      seconds to wait (default 1800)
#   ZERO_OPS_LEDGER    append-only JSONL
#   ZERO400            extra refuse path for LAB
#   LINEARIZE_DIR      out-of-tree linearize dir holding the original bootstrap.dat
#                      (default ~/Work/ZK/linearize)
set -euo pipefail
ME="ops-validate"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/../zcutil/fzero.sh"
cd "$REPO_ROOT"
# shellcheck disable=SC1091
. "$REPO_ROOT/contrib/perf/datadir_guard.sh"

ZEROD="${ZEROD:-$REPO_ROOT/src/zerod}"
ZERO_CLI="${ZERO_CLI:-$REPO_ROOT/src/zero-cli}"
LAB="${ZERO_OPS_LAB:-${TMPDIR:-/tmp}/zero-ops-validate}"
RPCPORT="${ZERO_RPCPORT:-23941}"
WAIT_S="${ZERO_OPS_WAIT:-1800}"
export ZERO400="${ZERO400:-$HOME/Work/ZK/Zero400}"
LINEARIZE_DIR="${LINEARIZE_DIR:-$HOME/Work/ZK/linearize}"
SRC="${ZERO_OPS_SRC:-$HOME/Library/Application Support/zero}"
SNAP="${ZERO_OPS_SNAP:-tiny}"
WALLET_FILE="${ZERO_OPS_WALLET:-${ZERO_PERF_WALLET_FILE:-}}"
WALLET_SEL=""
BOOTSTRAP="${ZERO_OPS_BOOTSTRAP:-${LOADBLOCK:-}}"
TARGET="${ZERO_OPS_TARGET:-}"
ARG_TARGET=""
TPL_DIR="$REPO_ROOT/contrib/conf-templates"
ZERO_CONF="$REPO_ROOT/contrib/zero-conf.sh"

if [[ -n "${ZERO_BUILD_DIR:-}" ]]; then
  LEDGER="${ZERO_OPS_LEDGER:-$ZERO_BUILD_DIR/ops-status.jsonl}"
else
  LEDGER="${ZERO_OPS_LEDGER:-$REPO_ROOT/test-logs/ops-status.jsonl}"
fi

CMD="${1:-}"
KEEP="${ZERO_OPS_KEEP:-0}"
ARG2=""
if [[ $# -ge 1 ]]; then
  shift
  for a in "$@"; do
    case "$a" in
      keep|--keep) KEEP=1 ;;
      all|ALL) ARG_TARGET=all ;;
      snap=*) SNAP="${a#snap=}" ;;
      --snap=*) SNAP="${a#--snap=}" ;;
      wallet=*) WALLET_SEL="${a#wallet=}" ;;
      --wallet=*) WALLET_SEL="${a#--wallet=}" ;;
      p0|p1|fat|none|nowallet|0|1|3) WALLET_SEL="$a" ;;
      *)
        if [[ "$a" =~ ^[0-9]+$ ]]; then
          ARG_TARGET="$a"
        elif [[ -f "$a" ]]; then
          WALLET_SEL="$a"
        elif [[ "$CMD" == "boot" || "$CMD" == "cold" ]]; then
          ARG2="$a"
        else
          echo "ERROR: extra arg $a (want all|N|p0|p1|fat|none|keep|snap=tiny|--wallet=PATH)" >&2
          exit 2
        fi
        ;;
    esac
  done
fi
TPL="lab"

usage() {
  echo "Usage: contrib/ops-validate.sh CMD [all|N] [p0|p1|fat|none] [keep] [snap=tiny|short|full]"
  echo "CMD: reindex|rescan|bootstrap|live|copy|cold|attach|stop|wallets"
  echo "reindex: -reindex from blk*.dat. Default stop 100000. reindex all = snap tip."
  echo "rescan: keep indexes, -rescan, wait Done loading. Wallet recommended (p0|p1|fat)."
  echo "bootstrap: -loadblock to 100000 (bootstrap all = end of file). always -disablewallet."
  echo "wallet: p0|p1|fat|none or --wallet=PATH  (contrib/ops-validate.sh wallets)"
  echo "live: RPC to SRC only. attach: RPC to LAB. keep: leave LAB zerod running."
}

resolve() { (cd "$1" 2>/dev/null && pwd -P) || echo "$1"; }

refuse_lab() { refuse_live_datadir LAB "$1"; }

src_rpcport() {
  local conf="$1/zero.conf" p=""
  if [[ -f "$conf" ]]; then
    p="$(awk -F= '/^rpcport=/{print $2; exit}' "$conf" | tr -d '\r')"
  fi
  printf '%s\n' "${p:-23811}"
}

cli() { "$ZERO_CLI" -datadir="$LAB" -rpcport="$RPCPORT" "$@"; }
cli_src() { "$ZERO_CLI" -datadir="$SRC" -rpcport="$(src_rpcport "$SRC")" "$@"; }

append_ledger() {
  mkdir -p "$(dirname "$LEDGER")"
  local zsha="missing"
  if [[ -x "$ZEROD" ]]; then
    zsha="$(shasum -a 256 "$ZEROD" | awk '{print $1}')"
  fi
  printf '{"ts":"%s","id":"%s","exit":%s,"head":"%s","zerod":"%s","lab":"%s","src":"%s","height":"%s","duration_s":%s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" \
    "$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo none)" \
    "$zsha" "$LAB" "$SRC" "${3:-}" "${4:-0}" >> "$LEDGER"
}

cmd_extra() {
  if [[ -n "$WALLET_FILE" ]]; then
    echo ""
  else
    echo "-disablewallet"
  fi
}

maybe_inject_wallet() {
  if [[ -n "$WALLET_FILE" ]]; then
    inject_wallet
  else
    echo "nowallet (-disablewallet)"
  fi
}

finish_ok() {
  local id="$1" h="${2:-}"
  local dur=$(( $(date +%s) - T0 ))
  echo "$id height=${h:-} duration=${dur}s wallet=${WALLET_FILE:-none} target=$(target_label)"
  append_ledger "$id" 0 "$h" "$dur"
}

maybe_stop() {
  if [[ "$KEEP" == "1" ]]; then
    echo "left running datadir=$LAB rpcport=$RPCPORT (attach / stop; live is SRC not LAB)"
    return 0
  fi
  cli stop >/dev/null
}

finish_err() {
  local id="$1" h="${2:-}"
  local dur=$(( $(date +%s) - T0 ))
  append_ledger "$id" 1 "$h" "$dur"
}

write_isolated_conf() {
  mkdir -p "$LAB"
  if [[ -x "$ZERO_CONF" && -f "$TPL_DIR/${TPL}.conf" ]]; then
    ZERO_RPCPORT="$RPCPORT" "$ZERO_CONF" "$TPL" -dir "$LAB" -out zero.conf -force
    return
  fi
  cat > "$LAB/zero.conf" <<EOF
server=1
listen=0
maxconnections=0
rpcport=$RPCPORT
EOF
  if [[ -z "$WALLET_FILE" ]]; then
    echo "disablewallet=1" >> "$LAB/zero.conf"
  fi
}

wait_rpc() {
  local limit="${1:-${WAIT_RPC_S:-180}}" i
  for i in $(seq 1 "$limit"); do
    if cli getblockchaininfo >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "ERROR: RPC not up in ${limit}s (params? see $LAB/debug.log)" >&2
  return 1
}

# First RPC is not a loaded tip. Wait until getblockcount repeats.
wait_stable_height() {
  local last="" h="" same=0 i=0
  while [[ "$i" -lt "$WAIT_S" ]]; do
    h="$(cli getblockcount 2>/dev/null || true)"
    if [[ "$h" =~ ^[0-9]+$ ]] && [[ "$h" == "$last" ]]; then
      same=$((same + 1))
      if [[ "$same" -ge 3 && "$h" -gt 0 ]]; then
        printf '%s\n' "$h"
        return 0
      fi
    else
      same=0
      last="$h"
    fi
    sleep 2
    i=$((i + 2))
  done
  echo "ERROR: height not stable in ${WAIT_S}s (last=$last). See $LAB/debug.log" >&2
  return 1
}

start_isolated() {
  # shellcheck disable=SC2086
  "$ZEROD" -datadir="$LAB" -daemon -listen=0 -connect=0 -maxconnections=0 -rpcport="$RPCPORT" $(cmd_extra)
  wait_rpc
}

wipe_chain() {
  rm -rf "$LAB/blocks" "$LAB/chainstate" "$LAB/wallet.zero" "$LAB/.lock" "$LAB/debug.log" "$LAB/.cookie"
}

copy_from_src() {
  local s
  s="$(resolve "$SRC")"
  [[ -d "$s/blocks" && -d "$s/chainstate" ]] || { echo "ERROR: SRC needs blocks/ and chainstate/: $s" >&2; exit 1; }
  if is_default_datadir "$LAB"; then
    echo "ERROR: copy dest is the default datadir" >&2
    exit 1
  fi
  if [[ "$(resolve "$LAB")" == "$s" ]]; then
    echo "ERROR: LAB and SRC are the same path" >&2
    exit 1
  fi
  if pgrep -x zerod >/dev/null 2>&1; then
    echo "ERROR: zerod is running; stop it before copy (do not snapshot a live chainstate)" >&2
    exit 1
  fi
  echo "wipe LAB then copy $s/{blocks,chainstate} -> $(resolve "$LAB") (read-only source)"
  rm -rf "$LAB"
  mkdir -p "$LAB"
  rsync -a --delete "$s/blocks/" "$LAB/blocks/"
  rsync -a --delete "$s/chainstate/" "$LAB/chainstate/"
  if [[ -n "$WALLET_FILE" && -f "$WALLET_FILE" ]]; then
    cp -p "$WALLET_FILE" "$LAB/wallet.zero"
    echo "copied wallet $WALLET_FILE"
  elif [[ -n "$WALLET_FILE" && -f "$s/wallet.zero" ]]; then
    cp -p "$s/wallet.zero" "$LAB/wallet.zero"
    echo "copied wallet.zero"
  else
    echo "nowallet (did not copy wallet.zero)"
  fi
}

# Load/import stop height. Default 100000. all = 0 (run to end).
resolve_load_target() {
  local tok="${1:-}"
  [[ -n "$tok" ]] || tok="${ZERO_OPS_TARGET:-}"
  case "$tok" in
    all|ALL) echo 0 ;;
    "") echo 100000 ;;
    *)
      if [[ "$tok" =~ ^[0-9]+$ ]]; then
        echo "$tok"
      else
        echo "ERROR: target must be all or a block height (got '$tok')" >&2
        exit 1
      fi
      ;;
  esac
}

snap_target() {
  case "$SNAP" in
    tiny) echo 187417 ;;
    short) echo 245992 ;;
    full) echo 0 ;;
    *) echo "ERROR: SNAP must be tiny|short|full (got '$SNAP')" >&2; exit 1 ;;
  esac
}

# $1 = reindex|rescan|bootstrap
apply_cmd_target() {
  local kind="$1"
  local tok="${ARG_TARGET:-${TARGET:-}}"
  case "$kind" in
    bootstrap)
      TARGET="$(resolve_load_target "$tok")"
      ;;
    reindex|rescan)
      case "$tok" in
        all|ALL)
          ARG_TARGET=all
          TARGET="$(snap_target)"
          ;;
        "")
          if [[ "$kind" == "rescan" ]]; then
            TARGET="$(snap_target)"
          else
            TARGET="$(resolve_load_target "")"
          fi
          ;;
        *)
          TARGET="$(resolve_load_target "$tok")"
          ;;
      esac
      ;;
  esac
  if [[ "$TARGET" -eq 0 ]]; then
    WAIT_S="${ZERO_OPS_WAIT:-10800}"
  fi
}

wallet_catalog_path() {
  local id="$1"
  case "$id" in
    none|nowallet|"") echo "" ;;
    p0|0) echo "${ZERO_OPS_WALLET_P0:-${ZERO_PERF_WALLET_P0:-$SRC/wallet.zero0}}" ;;
    p1|1) echo "${ZERO_OPS_WALLET_P1:-${ZERO_PERF_WALLET_P1:-$SRC/wallet.zero.personalbak-20260720}}" ;;
    fat|3) echo "${ZERO_OPS_WALLET_FAT:-${ZERO_PERF_WALLET_FAT:-$SRC/wallet.zero}}" ;;
    *) echo "$id" ;;
  esac
}

resolve_wallet() {
  local id="$1" p
  p="$(wallet_catalog_path "$id")"
  case "$id" in
    none|nowallet|"") echo ""; return 0 ;;
  esac
  if [[ -z "$p" ]]; then
    echo "ERROR: wallet '$id' resolved empty" >&2
    exit 1
  fi
  if [[ ! -f "$p" ]]; then
    echo "ERROR: wallet file missing: $p (id=$id). Set ZERO_OPS_WALLET_P0/P1/FAT or --wallet=PATH" >&2
    exit 1
  fi
  echo "$p"
}

cmd_wallets() {
  local id p
  printf "%-6s  %-8s  %s\n" "id" "bytes" "path"
  for id in p0 p1 fat; do
    p="$(wallet_catalog_path "$id")"
    if [[ -f "$p" ]]; then
      printf "%-6s  %-8s  %s\n" "$id" "$(stat -f%z "$p" 2>/dev/null || stat -c%s "$p")" "$p"
    else
      printf "%-6s  %-8s  %s\n" "$id" "MISSING" "$p"
    fi
  done
  echo "none    --        -disablewallet (default)"
}

wait_done_loading() {
  local i=0
  while [[ "$i" -lt "$WAIT_S" ]]; do
    if grep -q "Done loading" "$LAB/debug.log" 2>/dev/null; then
      return 0
    fi
    sleep 2
    i=$((i + 2))
  done
  echo "ERROR: Done loading not seen in ${WAIT_S}s (last height=$(cli getblockcount 2>/dev/null || echo none)). See $LAB/debug.log" >&2
  return 1
}

target_label() {
  if [[ -z "${TARGET:-}" ]]; then
    echo n/a
  elif [[ "$TARGET" -eq 0 ]]; then
    echo end
  else
    echo "$TARGET"
  fi
}

unpack_snap() {
  refuse_lab "$LAB"
  if pgrep -x zerod >/dev/null 2>&1; then
    echo "ERROR: stop zerod before reindex/bootstrap/rescan" >&2
    exit 1
  fi
  rm -rf "$LAB"
  mkdir -p "$LAB"
  case "$SNAP" in
    tiny)
      [[ -f "$SRC/chainblocks-tiny.tgz" ]] || { echo "ERROR: missing $SRC/chainblocks-tiny.tgz" >&2; exit 1; }
      tar -xzf "$SRC/chainblocks-tiny.tgz" -C "$LAB"
      ;;
    short)
      [[ -f "$SRC/chainblocks-short.tgz" ]] || { echo "ERROR: missing $SRC/chainblocks-short.tgz" >&2; exit 1; }
      tar -xzf "$SRC/chainblocks-short.tgz" -C "$LAB"
      ;;
    full)
      mkdir -p "$LAB/blocks"
      rsync -a --delete "$SRC/blocks/" "$LAB/blocks/"
      if [[ -d "$SRC/chainstate" ]]; then
        rsync -a --delete "$SRC/chainstate/" "$LAB/chainstate/"
      fi
      ;;
    *)
      echo "ERROR: ZERO_OPS_SNAP must be tiny|short|full" >&2
      exit 1
      ;;
  esac
  rm -rf "$LAB/.lock" "$LAB/.cookie"
  rm -f "$LAB/zero.conf"
}

prepare_snap_for_reindex() {
  unpack_snap
  rm -rf "$LAB/chainstate"
}

inject_wallet() {
  [[ -f "$WALLET_FILE" ]] || { echo "ERROR: wallet file missing: $WALLET_FILE" >&2; exit 1; }
  cp -p "$WALLET_FILE" "$LAB/wallet.zero"
  echo "injected wallet $WALLET_FILE -> $LAB/wallet.zero ($(stat -f%z "$WALLET_FILE" 2>/dev/null || stat -c%s "$WALLET_FILE") bytes)"
}

wait_until_height() {
  local need="$1" h="" i=0
  if [[ "$need" -le 0 ]]; then
    wait_stable_height
    return
  fi
  while [[ "$i" -lt "$WAIT_S" ]]; do
    h="$(cli getblockcount 2>/dev/null || true)"
    if [[ "$h" =~ ^[0-9]+$ ]] && [[ "$h" -ge "$need" ]]; then
      printf '%s\n' "$h"
      return 0
    fi
    sleep 2
    i=$((i + 2))
  done
  echo "ERROR: height $need not reached in ${WAIT_S}s (last=$h). See $LAB/debug.log" >&2
  return 1
}

walletinfo_ok() {
  perl -e 'alarm 30; exec @ARGV' -- "$ZERO_CLI" -datadir="$LAB" -rpcport="$RPCPORT" getwalletinfo >/dev/null
}

[[ -n "$CMD" ]] || { usage >&2; exit 2; }
if [[ "$CMD" == "wallets" || "$CMD" == "-h" || "$CMD" == "--help" ]]; then
  [[ "$CMD" == "wallets" ]] && { cmd_wallets; exit 0; }
  usage; exit 0
fi
if [[ -n "$WALLET_SEL" ]]; then
  WALLET_FILE="$(resolve_wallet "$WALLET_SEL")"
fi
[[ -x "$ZEROD" ]] || { echo "missing $ZEROD" >&2; exit 1; }

T0=$(date +%s)

case "$CMD" in
  reindex)
    refuse_lab "$LAB"
    prepare_snap_for_reindex
    maybe_inject_wallet
    write_isolated_conf
    apply_cmd_target reindex
    echo "OPS-REINDEX snap=$SNAP wallet=${WALLET_FILE:-none} target=$(target_label) (CLI -reindex, no sticky conf)"
    # shellcheck disable=SC2086
    "$ZEROD" -datadir="$LAB" -daemon -listen=0 -connect=0 -maxconnections=0 -rpcport="$RPCPORT" $(cmd_extra) -reindex
    wait_rpc
    h="$(wait_until_height "$TARGET")"
    if [[ "${ARG_TARGET:-}" == "all" || "$TARGET" -eq 0 ]]; then
      wait_done_loading
      h="$(cli getblockcount 2>/dev/null || echo "$h")"
    fi
    if [[ -n "$WALLET_FILE" ]]; then
      walletinfo_ok || { echo "ERROR: getwalletinfo failed or timed out" >&2; cli stop >/dev/null 2>&1 || true; finish_err OPS-REINDEX "$h"; exit 1; }
    fi
    maybe_stop
    finish_ok OPS-REINDEX "$h"
    ;;
  bootstrap)
    refuse_lab "$LAB"
    [[ -n "$BOOTSTRAP" && -f "$BOOTSTRAP" ]] || {
      echo "ERROR: set ZERO_OPS_BOOTSTRAP or LOADBLOCK to a bootstrap.dat copy" >&2
      exit 1
    }
    if [[ "$(resolve "$BOOTSTRAP")" == "$(resolve "$LINEARIZE_DIR/bootstrap.dat" 2>/dev/null || echo "")" ]]; then
      echo "ERROR: pass a copy of bootstrap.dat, not the lab original" >&2
      exit 1
    fi
    if pgrep -x zerod >/dev/null 2>&1; then
      echo "ERROR: stop zerod before bootstrap" >&2
      exit 1
    fi
    rm -rf "$LAB"
    mkdir -p "$LAB"
    cp -p "$BOOTSTRAP" "$LAB/bootstrap.dat"
    write_isolated_conf
    apply_cmd_target bootstrap
    echo "OPS-BOOTSTRAP loadblock=$LAB/bootstrap.dat target=$(target_label) wait=${WAIT_S}s"
    "$ZEROD" -datadir="$LAB" -daemon -listen=0 -connect=0 -maxconnections=0 -rpcport="$RPCPORT" \
      -disablewallet -loadblock="$LAB/bootstrap.dat"
    wait_rpc
    h="$(wait_until_height "$TARGET")"
    maybe_stop
    finish_ok OPS-BOOTSTRAP "$h"
    ;;
  rescan)
    refuse_lab "$LAB"
    unpack_snap
    [[ -d "$LAB/chainstate" ]] || { echo "ERROR: rescan needs chainstate in the snap (SNAP=$SNAP)" >&2; exit 1; }
    maybe_inject_wallet
    write_isolated_conf
    apply_cmd_target rescan
    echo "OPS-RESCAN snap=$SNAP wallet=${WALLET_FILE:-none} target=$(target_label) (CLI -rescan, indexes kept)"
    # shellcheck disable=SC2086
    "$ZEROD" -datadir="$LAB" -daemon -listen=0 -connect=0 -maxconnections=0 -rpcport="$RPCPORT" $(cmd_extra) -rescan
    wait_done_loading
    wait_rpc
    h="$(cli getblockcount 2>/dev/null || true)"
    if [[ "$TARGET" -gt 0 ]]; then
      h="$(wait_until_height "$TARGET")"
    else
      h="$(wait_until_height 0)"
    fi
    if [[ -n "$WALLET_FILE" ]]; then
      walletinfo_ok || echo "WARN: getwalletinfo failed or timed out"
    fi
    maybe_stop
    finish_ok OPS-RESCAN "$h"
    ;;
  live)
    [[ -d "$SRC" ]] || { echo "ERROR: SRC missing $SRC" >&2; exit 1; }
    if ! cli_src getblockchaininfo >/dev/null 2>&1; then
      echo "ERROR: no RPC on $SRC (start zerod on the default datadir first, then re-run live)" >&2
      echo "  e.g. $ZEROD -datadir=\"$SRC\" -daemon" >&2
      finish_err OPS-LIVE ""
      exit 1
    fi
    h="$(cli_src getblockcount)"
    cli_src getwalletinfo >/dev/null 2>&1 || echo "WARN: getwalletinfo failed"
    echo "OPS-LIVE height=$h src=$SRC rpcport=$(src_rpcport "$SRC") (did not start or stop)"
    if ! [[ "$h" =~ ^[0-9]+$ ]] || [[ "$h" -le 0 ]]; then
      echo "ERROR: live expected height > 0" >&2
      finish_err OPS-LIVE "$h"
      exit 1
    fi
    finish_ok OPS-LIVE "$h"
    ;;
  copy)
    refuse_lab "$LAB"
    copy_from_src
    write_isolated_conf
    WAIT_RPC_S=600 start_isolated
    h="$(wait_stable_height)"
    if [[ -f "$LAB/wallet.zero" ]]; then
      cli getwalletinfo >/dev/null
    fi
    maybe_stop
    echo "OPS-COPY src=$SRC lab=$LAB isolated (this zerod, no P2P)"
    finish_ok OPS-COPY "$h"
    ;;
  cold|boot)
    refuse_lab "$LAB"
    mkdir -p "$LAB"
    wipe_chain
    TPL="${ARG2:-lab}"
    write_isolated_conf
    start_isolated
    h="$(cli getblockcount)"
    maybe_stop
    echo "OPS-START-COLD (binary-up only, not a sync test)"
    finish_ok OPS-START-COLD "$h"
    ;;
  attach)
    refuse_lab "$LAB"
    wait_rpc
    cli getblockchaininfo
    h="$(cli getblockcount)"
    finish_ok OPS-ATTACH "$h"
    ;;
  stop)
    refuse_lab "$LAB"
    cli stop >/dev/null
    finish_ok OPS-STOP ""
    ;;
  -h|--help) usage; exit 0 ;;
  wallets) cmd_wallets; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac
