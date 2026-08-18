#!/usr/bin/env bash
# Create a disposable lab datadir and unroll only blocks/ + chainstate/.
# Does not write zero.conf (operator does that). Does not start zerod.
# Default archive is read-only (no writes to Application Support).
#
# Usage (repo root):
#   contrib/perf/prep_lab_datadir.sh           # create + unroll
#   contrib/perf/prep_lab_datadir.sh create
#   contrib/perf/prep_lab_datadir.sh unroll
#
# Env:
#   LAB       dest datadir (default reindex-profile/mainnet-p2p-23911)
#   ARCHIVE   .tgz with top-level blocks/ and chainstate/ (unroll default:
#             $HOME/Library/Application Support/zero/chainblocks812-clean.tgz)
#   SRC       source datadir used only when ARCHIVE is set to empty
#             (default reindex-profile/fulltip-812-datadir)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
. "$REPO_ROOT/contrib/perf/datadir_guard.sh"
CMD="${1:-all}"
LAB="${LAB:-$REPO_ROOT/reindex-profile/mainnet-p2p-23911}"
SRC="${SRC:-$REPO_ROOT/reindex-profile/fulltip-812-datadir}"
DEFAULT_ARCHIVE="$HOME/Library/Application Support/zero/chainblocks812-clean.tgz"
# Unset -> default tgz. ARCHIVE="" -> unroll from SRC.
if [ "${ARCHIVE+set}" != "set" ]; then
  ARCHIVE="$DEFAULT_ARCHIVE"
fi

resolve() {
  (cd "$1" 2>/dev/null && pwd -P) || echo "$1"
}

refuse_protected() {
  refuse_live_datadir "$1" "$2"
}

usage() {
  echo "Usage: $0 [create|unroll]" >&2
  echo "  no args: create then unroll" >&2
  echo "  LAB=$LAB" >&2
  echo "  ARCHIVE=${ARCHIVE:-<empty, use SRC>}" >&2
  echo "  SRC=$SRC" >&2
  exit 2
}

do_create() {
  refuse_protected LAB "$LAB"
  mkdir -p "$LAB"
  echo "created $(resolve "$LAB")"
}

do_unroll() {
  refuse_protected LAB "$LAB"
  if [ ! -d "$LAB" ]; then
    echo "ERROR: LAB does not exist (run create first): $LAB" >&2
    exit 1
  fi
  lab_res="$(resolve "$LAB")"
  if [ -n "$ARCHIVE" ]; then
    if [ ! -f "$ARCHIVE" ]; then
      echo "ERROR: missing ARCHIVE $ARCHIVE" >&2
      exit 1
    fi
    echo "unroll archive $ARCHIVE -> $lab_res (blocks/ chainstate/ only, read-only source)"
    tar -xzf "$ARCHIVE" -C "$LAB" blocks chainstate
  else
    refuse_protected SRC "$SRC"
    src_res="$(resolve "$SRC")"
    if [ "$lab_res" = "$src_res" ]; then
      echo "ERROR: LAB and SRC are the same path: $lab_res" >&2
      exit 1
    fi
    if [ ! -d "$SRC/blocks" ] || [ ! -d "$SRC/chainstate" ]; then
      echo "ERROR: SRC needs blocks/ and chainstate/: $SRC" >&2
      exit 1
    fi
    echo "unroll $src_res/{blocks,chainstate} -> $lab_res"
    rsync -a --delete "$SRC/blocks/" "$LAB/blocks/"
    rsync -a --delete "$SRC/chainstate/" "$LAB/chainstate/"
  fi
  echo "unroll done (no zero.conf written)"
}

export COPYFILE_DISABLE=1

case "$CMD" in
  all)
    do_create
    do_unroll
    ;;
  create)
    do_create
    ;;
  unroll)
    do_unroll
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    ;;
esac
