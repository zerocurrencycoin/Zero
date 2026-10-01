#!/usr/bin/env bash
# Run check-setup.sh, check-release.sh, then build.sh; not a test runner. --help for options.
set -euo pipefail
ME="build-release"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

CHECK_ARGS=()
BUILD_ARGS=()
HOST_WIN=0
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
    -h|--help)
      echo "Usage: zcutil/build-release.sh [check-release options] [--win] [-- build.sh args]"
      echo "Runs zcutil/check-setup.sh, zcutil/check-release.sh, then zcutil/build.sh."
      echo "Not a test runner; follow with contrib/run-tests.sh --strict."
      echo "--win: check-setup --win and build.sh -win."
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
  run_check_setup --win
  win_in_build=0
  for a in "${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"}"; do
    if [[ "$a" == "-win" || "$a" == "--win" ]]; then
      win_in_build=1
    fi
  done
  if [[ "$win_in_build" -eq 0 ]]; then
    BUILD_ARGS=("-win" "${BUILD_ARGS[@]+"${BUILD_ARGS[@]}"}")
  fi
else
  run_check_setup
fi

if [[ ${#CHECK_ARGS[@]} -gt 0 ]]; then
  "$REPO_ROOT/zcutil/check-release.sh" "${CHECK_ARGS[@]}"
else
  "$REPO_ROOT/zcutil/check-release.sh"
fi
if [[ ${#BUILD_ARGS[@]} -gt 0 ]]; then
  exec "$REPO_ROOT/zcutil/build.sh" "${BUILD_ARGS[@]}"
else
  exec "$REPO_ROOT/zcutil/build.sh"
fi
