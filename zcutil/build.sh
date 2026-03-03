#!/usr/bin/env bash
# Copyright 2026 Zero Developers
# Wrapper: run build-<platform>.sh. Linux/Darwin -> build-native, -win -> build-win (Linux only).
set -e -u -o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:-}" == "-win" ]] || [[ "${1:-}" == "--win" ]]; then
  shift
  exec "$SCRIPT_DIR/build-win.sh" "$@"
fi
case "$(uname -s)" in
  Linux|Darwin) exec "$SCRIPT_DIR/build-native.sh" "$@" ;;
  *)            echo "build.sh: Linux or macOS only. Use build.sh -win for Windows cross from Linux." >&2; exit 1 ;;
esac
