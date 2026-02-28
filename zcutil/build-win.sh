#!/bin/bash
# Windows cross-compile from Linux. Requires: mingw-w64 (x86_64-w64-mingw32-gcc-posix).
# Run from Linux: sudo apt install mingw-w64 build-essential

HOST=x86_64-w64-mingw32
CXX=x86_64-w64-mingw32-g++-posix
CC=x86_64-w64-mingw32-gcc-posix
PREFIX="$(pwd)/depends/$HOST"

set -eu -o pipefail

detect_jobs() {
    if command -v nproc &>/dev/null; then
        nproc 2>/dev/null || echo 4
    else
        echo 4
    fi
}

if [ "x$*" = 'x--help' ] || [ "x$*" = 'x-h' ]; then
    cat <<EOF
Usage: $0 [ -jN ] [ MAKEARGS... ]

  Cross-compile zerod for Windows (x86_64) from Linux.
  Requires: mingw-w64 (sudo apt install mingw-w64 build-essential)

  -jN: Parallel jobs (default: -j\$(nproc) or -j4).
  MAKEARGS: Passed to make for both depends and src.

  Output: src/zerod.exe, src/zero-cli.exe, src/zero-tx.exe
EOF
    exit 0
fi

MAKEARGS=()
HAS_JOBS=0
for arg in "$@"; do
    if [[ "$arg" =~ ^-j([0-9]+)$ ]]; then
        MAKEARGS+=("$arg")
        HAS_JOBS=1
    else
        MAKEARGS+=("$arg")
    fi
done
[[ $HAS_JOBS -eq 0 ]] && MAKEARGS=("-j$(detect_jobs)" "${MAKEARGS[@]}")

set -x
cd "$(dirname "$(readlink -f "$0")")/.."

cd depends/ && make HOST=$HOST V=1 "${MAKEARGS[@]}" && cd ../
./autogen.sh
CONFIG_SITE=$PWD/depends/x86_64-w64-mingw32/share/config.site CXXFLAGS+="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" ./configure --prefix="${PREFIX}" --host=x86_64-w64-mingw32 --enable-static --disable-shared --disable-zmq --disable-rust
sed -i.bak 's/-lboost_system-mt /-lboost_system-mt-s /' configure && rm -f configure.bak
cd src/
CC="${CC}" CXX="${CXX}" make V=1 "${MAKEARGS[@]}" zerod.exe zero-cli.exe zero-tx.exe
