#!/usr/bin/env bash
# Windows cross-build via MXE. Set MXE_ROOT (default $HOME/mxe) or pass -m/--mxe.
# MAKEARGS (e.g. -jN) are applied to both dependencies and src.
set -eu -o pipefail

# Parse MXE path before other setup
while [[ $# -gt 0 ]]; do
    case "$1" in
        -m|--mxe) MXE_ROOT="$2"; shift 2 ;;
        *) break ;;
    esac
done
MXE_ROOT="${MXE_ROOT:-$HOME/mxe}"
MXE_PATH="${MXE_ROOT}/usr/bin"
export PATH="$MXE_PATH:$PATH"

function cmd_pref() {
    if type -p "$2" > /dev/null; then
        eval "$1=$2"
    else
        eval "$1=$3"
    fi
}

# If a g-prefixed version of the command exists, use it preferentially.
function gprefix() {
    cmd_pref "$1" "g$2" "$2"
}

gprefix READLINK readlink
cd "$(dirname "$("$READLINK" -f "$0")")/.."

HOST=x86_64-w64-mingw32
CC=$(command -v x86_64-w64-mingw32.static-gcc 2>/dev/null)
[ -n "$CC" ] || { echo "build-win: x86_64-w64-mingw32.static-gcc not found. Set MXE_ROOT (e.g. export MXE_ROOT=\$HOME/mxe)" >&2; exit 1; }
CXX="${CC%gcc}g++"
WINDRES=$(command -v x86_64-w64-mingw32.static-windres 2>/dev/null)
[ -n "$WINDRES" ] || { echo "build-win: x86_64-w64-mingw32.static-windres not found" >&2; exit 1; }
PREFIX="$PWD/depends/$HOST"

# Allow user overrides to $MAKE.
if [[ -z "${MAKE-}" ]]; then
    MAKE=make
fi

# Allow users to set arbitrary compile flags. Most users will not need this.
if [[ -z "${CONFIGURE_FLAGS-}" ]]; then
    CONFIGURE_FLAGS=""
fi

# Cap -jN at 4. Detect CPU count: nproc (Linux), gnproc (Mac with coreutils), sysctl (Mac native).
detect_jobs() {
    local n=4
    if command -v nproc &>/dev/null; then
        n=$(nproc 2>/dev/null || echo 4)
    elif command -v gnproc &>/dev/null; then
        n=$(gnproc 2>/dev/null || echo 4)
    elif [[ "$(uname -s)" == "Darwin" ]] && command -v sysctl &>/dev/null; then
        n=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
    fi
    [[ "$n" -gt 4 ]] && n=4
    echo "$n"
}

if [ "x$*" = 'x--help' ]
then
    cat <<EOF
Usage:

$0 --help
  Show this help message and exit.

$0 [ -m/--mxe PATH ] [ MAKEARGS... ]
  Windows cross-build via MXE. Cross-compiles zerod, zero-cli, zero-tx from Linux.

  -m, --mxe PATH   MXE install root (default: \$HOME/mxe)
  MAKEARGS: -jN is capped at 4. If omitted, -jN is added (N=min(CPUs,4)).
  Aligns with build.sh (daemon/cli only: no Qt, no ZMQ, no Rust).
EOF
    exit 0
fi

set -x

# Build MAKEARGS: cap -jN at 4, or add -j$(detect_jobs) if no -j given.
MAKEARGS=()
HAS_JOBS=0
for arg in "$@"; do
    if [[ "$arg" =~ ^-j([0-9]+)$ ]]; then
        n="${BASH_REMATCH[1]}"
        [[ "$n" -gt 4 ]] && n=4
        MAKEARGS+=("-j$n")
        HAS_JOBS=1
    else
        MAKEARGS+=("$arg")
    fi
done
[[ $HAS_JOBS -eq 0 ]] && MAKEARGS=("-j$(detect_jobs)" "${MAKEARGS[@]}")

eval "$MAKE" --version
"$CC" --version | head -1

HOST="$HOST" "$MAKE" "${MAKEARGS[@]}" -C ./depends/ V=1 NO_QT=1

# Remove stale secp256k1 .la when host changed (fixes ld "search path not found" warning)
if [ -f src/secp256k1/libsecp256k1.la ] && [ -d "depends/$HOST" ]; then
  la_host=$(grep 'dependency_libs' src/secp256k1/libsecp256k1.la 2>/dev/null | sed -n 's|.*depends/\([^/]*\)/.*|\1|p')
  if [ -n "$la_host" ] && [ "$la_host" != "$HOST" ]; then
    rm -f src/secp256k1/libsecp256k1.la src/secp256k1/config.status
  fi
fi

./autogen.sh
sed -i.bak 's/-lboost_system-mt /-lboost_system-mt-s /' configure && rm -f configure.bak
CONFIG_SITE="$PWD/depends/$HOST/share/config.site" CXXFLAGS+="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" ./configure --prefix="$PREFIX" --host=x86_64-w64-mingw32 --enable-static --disable-shared --disable-zmq --disable-rust $CONFIGURE_FLAGS

cd src/
CC="$CC" CXX="$CXX" WINDRES="$WINDRES" "$MAKE" "${MAKEARGS[@]}" V=1 zerod.exe zero-cli.exe zero-tx.exe
