#!/usr/bin/env bash

set -eu -o pipefail

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

if [[ -z "${CC-}" ]]; then
    CC=gcc
fi
if [[ -z "${CXX-}" ]]; then
    CXX=g++
fi
export CC CXX

# Allow user overrides to $MAKE. Typical usage for users who need it:
#   MAKE=gmake ./zcutil/build.sh -j$(nproc)
if [[ -z "${MAKE-}" ]]; then
    MAKE=make
fi

# Allow overrides to $BUILD and $HOST for porters. Most users will not need it.
#   BUILD=i686-pc-linux-gnu ./zcutil/build.sh
if [[ -z "${BUILD-}" ]]; then
    BUILD="$(./depends/config.guess)"
fi
if [[ -z "${HOST-}" ]]; then
    HOST="$BUILD"
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

$0 [ --enable-lcov || --disable-tests ] [ --disable-mining ] [ --enable-proton ] [ --daemon ] [ MAKEARGS... ]
  Build Zcash and most of its transitive dependencies from
  source. MAKEARGS are applied to both dependencies and Zcash itself.

  If --daemon is passed, build daemon/cli only: --disable-zmq and --disable-rust.
  Aligns with build-win.sh.

  If --enable-lcov is passed, Zcash is configured to add coverage
  instrumentation, thus enabling "make cov" to work.
  If --disable-tests is passed instead, the Zcash tests are not built.

  If --disable-mining is passed, Zcash is configured to not build any mining
  code. It must be passed after the test arguments, if present.

  If --enable-proton is passed, Zcash is configured to build the Apache Qpid Proton
  library required for AMQP support. This library is not built by default.
  It must be passed after the test/mining arguments, if present.

  MAKEARGS: -jN is capped at 4. If omitted, -jN is added (N=min(CPUs,4)).
  On macOS, use sysctl -n hw.ncpu or install coreutils for gnproc.
EOF
    exit 0
fi

set -x

# If --enable-lcov is the first argument, enable lcov coverage support:
LCOV_ARG=''
HARDENING_ARG='--enable-hardening'
TEST_ARG=''
if [ "x${1:-}" = 'x--enable-lcov' ]
then
    LCOV_ARG='--enable-lcov'
    HARDENING_ARG='--disable-hardening'
    shift
elif [ "x${1:-}" = 'x--disable-tests' ]
then
    TEST_ARG='--enable-tests=no'
    shift
fi

# If --disable-mining is the next argument, disable mining code:
MINING_ARG=''
if [ "x${1:-}" = 'x--disable-mining' ]
then
    MINING_ARG='--enable-mining=no'
    shift
fi

# If --enable-proton is the next argument, enable building Proton code:
PROTON_ARG='--enable-proton=no'
if [ "x${1:-}" = 'x--enable-proton' ]
then
    PROTON_ARG=''
    shift
fi

# If --daemon is the next argument, skip ZMQ/Rust (align with build-win.sh):
DAEMON_ARG=''
if [ "x${1:-}" = 'x--daemon' ]
then
    DAEMON_ARG='--disable-zmq --disable-rust'
    shift
fi

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
as --version
ld -v

HOST="$HOST" BUILD="$BUILD" NO_PROTON="$PROTON_ARG" "$MAKE" "${MAKEARGS[@]}" -C ./depends/ V=1

# Remove stale secp256k1 .la when host changed (fixes ld "search path not found" warning)
if [ -f src/secp256k1/libsecp256k1.la ] && [ -d "depends/$HOST" ]; then
  la_host=$(grep 'dependency_libs' src/secp256k1/libsecp256k1.la 2>/dev/null | sed -n 's|.*depends/\([^/]*\)/.*|\1|p')
  if [ -n "$la_host" ] && [ "$la_host" != "$HOST" ]; then
    rm -f src/secp256k1/libsecp256k1.la src/secp256k1/config.status
  fi
fi

./autogen.sh
CONFIG_SITE="$PWD/depends/$HOST/share/config.site" ./configure "$HARDENING_ARG" "$LCOV_ARG" "$TEST_ARG" "$MINING_ARG" "$PROTON_ARG" $DAEMON_ARG $CONFIGURE_FLAGS CXXFLAGS='-g'
"$MAKE" "${MAKEARGS[@]}" V=1
