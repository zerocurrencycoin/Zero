#!/bin/bash
# Windows cross-build via MXE. Set MXE_ROOT (default $HOME/mxe) or pass -m/--mxe.
# MXE_PATH=$MXE_ROOT/usr/bin
set -eu -o pipefail

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--mxe) MXE_ROOT="$2"; shift 2 ;;
    *) break ;;
  esac
done

MXE_ROOT="${MXE_ROOT:-$HOME/mxe}"
MXE_PATH="${MXE_ROOT}/usr/bin"
export PATH="$MXE_PATH:$PATH"

HOST=x86_64-w64-mingw32
CC=$(command -v x86_64-w64-mingw32.static-gcc 2>/dev/null)
[ -n "$CC" ] || { echo "build-win: x86_64-w64-mingw32.static-gcc not found. Set MXE_ROOT (e.g. export MXE_ROOT=\$HOME/mxe)" >&2; exit 1; }
CXX="${CC%gcc}g++"
WINDRES=$(command -v x86_64-w64-mingw32.static-windres 2>/dev/null)
[ -n "$WINDRES" ] || { echo "build-win: x86_64-w64-mingw32.static-windres not found" >&2; exit 1; }
PREFIX="$(pwd)/depends/$HOST"

set -x
cd "$(dirname "$(readlink -f "$0")")/.."

(cd depends && make HOST=$HOST V=1 NO_QT=1) || exit 1
./autogen.sh
CONFIG_SITE=$PWD/depends/x86_64-w64-mingw32/share/config.site CXXFLAGS+="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" ./configure --prefix="${PREFIX}" --host=x86_64-w64-mingw32 --enable-static --disable-shared --disable-zmq --disable-rust
sed -i 's/-lboost_system-mt /-lboost_system-mt-s /' configure
cd src/
CC="${CC}" CXX="${CXX}" WINDRES="${WINDRES}" make V=1 -j4 zerod.exe zero-cli.exe zero-tx.exe
