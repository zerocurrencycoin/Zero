#!/usr/bin/env bash
# Run check-setup.sh, check-release.sh (tree), build.sh, then check-release.sh on the build; not a test runner. --help for options.
set -euo pipefail
ME="build-release"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

CHECK_ARGS=()
BUILD_ARGS=()
SETUP_ARGS=()
HOST_WIN=0
LEVELS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --)
      shift
      BUILD_ARGS+=("$@")
      break
      ;;
    --win|-win)
      HOST_WIN=1
      shift
      ;;
    --no-wine)
      SETUP_ARGS+=("--no-wine")
      shift
      ;;
    --levels=*)
      LEVELS="${1#--levels=}"
      shift
      ;;
    -h|--help)
      echo "Usage: zcutil/build-release.sh [check-release options] [--win] [--no-wine] [-- build.sh args]"
      echo "Runs zcutil/check-setup.sh, zcutil/check-release.sh --levels=tree, zcutil/build.sh,"
      echo "then zcutil/check-release.sh on the result."
      echo "Not a test runner; follow with contrib/run-tests.sh --strict."
      echo "--levels=LIST: levels of the check after the build (default: tree,configure,build;"
      echo "  with --win tree,configure, since the build level reads the native src/zerod)."
      echo "--win: check-setup --win and build.sh -win."
      echo "--no-wine: with --win, check-setup --no-wine (no wine smoke check on this host)."
      echo "build.sh always runs depends, autogen, configure, make; for an incremental"
      echo "rebuild of a configured tree run make -j directly."
      exit 0
      ;;
    *)
      CHECK_ARGS+=("$1")
      shift
      ;;
  esac
done

for a in "${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"}"; do
  if [[ "$a" == "-win" || "$a" == "--win" ]]; then
    HOST_WIN=1
  fi
done

if [[ "$HOST_WIN" -eq 1 ]]; then
  run_check_setup --win "${SETUP_ARGS[@]+"${SETUP_ARGS[@]}"}"
  win_in_build=0
  for a in "${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"}"; do
    if [[ "$a" == "-win" || "$a" == "--win" ]]; then
      win_in_build=1
    fi
  done
  if [[ "$win_in_build" -eq 0 ]]; then
    BUILD_ARGS=("-win" "${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"}")
  fi
  LEVELS="${LEVELS:-tree,configure}"
else
  run_check_setup
  LEVELS="${LEVELS:-tree,configure,build}"
fi

# Before the build only the tree and pin can be checked; configure and build levels need its output.
"$REPO_ROOT/zcutil/check-release.sh" "${CHECK_ARGS[@]+"${CHECK_ARGS[@]}"}" --levels=tree
"$REPO_ROOT/zcutil/build.sh" "${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"}"
"$REPO_ROOT/zcutil/check-release.sh" "${CHECK_ARGS[@]+"${CHECK_ARGS[@]}"}" "--levels=$LEVELS"
