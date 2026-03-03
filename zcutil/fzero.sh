# shellcheck shell=bash
# Copyright 2026 Zero Developers
# Shared build helpers for Zero node (build-native, build-win).
# Usage: ME="script-name"; . "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
# Provides: SCRIPT_DIR, REPO_ROOT, JOBS, err, warn, info, notice, step_done, section,
#           log_capture, analyze_build_log, build_fail, parse_build_args, parse_build_win_args,
#           resolve_host_*, build_depends_*, run_autogen, run_configure_*, run_make_*

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
JOBS="$(nproc 2>/dev/null || (sysctl -n hw.ncpu 2>/dev/null) || echo 2)"

# shellcheck disable=SC1091
. "$SCRIPT_DIR/fmessage.sh"

section() { echo ""; notice "[$1]"; }

# Build log analysis (call when build fails and LOG_FILE is set)
analyze_build_log() {
  local f="${1:-$LOG_FILE}"
  [ -n "$f" ] && [ -f "$f" ] || return 0
  echo "" >&2
  echo "=== Build analysis (from $f) ===" >&2
  echo "--- Errors ---" >&2
  grep -iE "error:|fatal|undefined reference|cannot find|No such file" "$f" 2>/dev/null | tail -30 || echo "(none)" >&2
  echo "--- Warnings (last 15) ---" >&2
  grep -iE "warning:" "$f" 2>/dev/null | tail -15 || echo "(none)" >&2
}

# Log capture: tee to LOG_FILE or cat. Used when -L/--log passed.
log_capture() {
  if [ -n "${LOG_FILE:-}" ]; then tee -a "$LOG_FILE"; else cat; fi
}

# Call on build failure: analyze log if set, then err.
build_fail() {
  [ -n "${LOG_FILE:-}" ] && [ -f "$LOG_FILE" ] && analyze_build_log "$LOG_FILE"
  err "${1:-build failed}"
}

# Cap -jN at 4. nproc (Linux), gnproc (Mac coreutils), sysctl (Mac native).
detect_jobs() {
  local n=2
  if command -v nproc &>/dev/null; then
    n=$(nproc 2>/dev/null || echo 2)
  elif command -v gnproc &>/dev/null; then
    n=$(gnproc 2>/dev/null || echo 2)
  elif [[ "$(uname -s)" == "Darwin" ]] && command -v sysctl &>/dev/null; then
    n=$(sysctl -n hw.ncpu 2>/dev/null || echo 2)
  fi
  [[ "$n" -gt 4 ]] && n=4
  echo "$n"
}

# Parse native build args. Sets LCOV_ARG, HARDENING_ARG, TEST_ARG, MINING_ARG, PROTON_ARG, DAEMON_ARG, LOG_FILE, MAKEARGS.
# Usage: parse_build_args "logs/build-native.log" "$@"
# shellcheck disable=SC2034
parse_build_args() {
  local default_log="${1:-logs/build-native.log}"
  shift
  if [[ "x$*" == "x--help" ]]; then
    show_build_help "$default_log"
    exit 0
  fi
  LCOV_ARG=''
  HARDENING_ARG='--enable-hardening'
  TEST_ARG=''
  MINING_ARG=''
  PROTON_ARG='--enable-proton=no'
  DAEMON_ARG=''
  LOG_FILE=''
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -L) LOG_FILE="${LOG_FILE:-$REPO_ROOT/$default_log}"; shift ;;
      -L=*) LOG_FILE="${1#-L=}"; shift ;;
      --log)
        if [ -n "${2:-}" ] && [[ "$2" != -* ]]; then LOG_FILE="$2"; shift 2
        else LOG_FILE="${LOG_FILE:-$REPO_ROOT/$default_log}"; shift; fi
        ;;
      --log=*) LOG_FILE="${1#--log=}"; shift ;;
      --enable-lcov)   LCOV_ARG='--enable-lcov'; HARDENING_ARG='--disable-hardening'; shift ;;
      --disable-tests) TEST_ARG='--enable-tests=no'; shift ;;
      --disable-mining) MINING_ARG='--enable-mining=no'; shift ;;
      --enable-proton) PROTON_ARG=''; shift ;;
      --daemon)        DAEMON_ARG='--disable-zmq --disable-rust'; shift ;;
      *)               break ;;
    esac
  done
  [ -n "$LOG_FILE" ] && mkdir -p "$(dirname "$LOG_FILE")"
  makeargs_from_argv "$@"
}

# Parse Windows build args. Sets LOG_FILE, MAKEARGS.
# Usage: parse_build_win_args "logs/build-win.log" "$@"
# shellcheck disable=SC2034
parse_build_win_args() {
  local default_log="${1:-logs/build-win.log}"
  shift
  if [[ "x$*" == "x--help" ]] || [[ "x$*" == "x-h" ]]; then
    show_build_win_help "$default_log"
    exit 0
  fi
  LOG_FILE=''
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -L) LOG_FILE="${LOG_FILE:-$REPO_ROOT/$default_log}"; shift ;;
      -L=*) LOG_FILE="${1#-L=}"; shift ;;
      --log)
        if [ -n "${2:-}" ] && [[ "$2" != -* ]]; then LOG_FILE="$2"; shift 2
        else LOG_FILE="${LOG_FILE:-$REPO_ROOT/$default_log}"; shift; fi
        ;;
      --log=*) LOG_FILE="${1#--log=}"; shift ;;
      *) break ;;
    esac
  done
  [ -n "$LOG_FILE" ] && mkdir -p "$(dirname "$LOG_FILE")"
  makeargs_from_argv "$@"
}

makeargs_from_argv() {
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
  if [[ $HAS_JOBS -eq 0 ]]; then
    MAKEARGS=("-j$(detect_jobs)" "${MAKEARGS[@]}")
  fi
}

show_build_help() {
  local log="${1:-logs/build-native.log}"
  cat <<EOF
Usage: $ME --help
  Show this help message and exit.

Usage: $ME [ -L | --log PATH ] [ --enable-lcov | --disable-tests ] [ --disable-mining ] [ --enable-proton ] [ --daemon ] [ MAKEARGS... ]
  Build Zero and its dependencies from source. MAKEARGS apply to both depends and src.

  -L, --log PATH  capture build log (default: $log)
  --daemon: Build daemon/cli only (--disable-zmq --disable-rust). Aligns with build-win.sh.
  --enable-lcov: Add coverage instrumentation (make cov).
  --disable-tests: Do not build tests.
  --disable-mining: Do not build mining code.
  --enable-proton: Build Apache Qpid Proton (AMQP support).

  MAKEARGS: -jN capped at 4. Default: -j\$(detect_jobs).
EOF
}

show_build_win_help() {
  local log="${1:-logs/build-win.log}"
  cat <<EOF
Usage: $ME [ -L | --log PATH ] [ -jN ] [ MAKEARGS... ]

  Cross-compile zerod for Windows (x86_64) from Linux.
  Requires: mingw-w64 (sudo apt install mingw-w64 build-essential)

  -L, --log PATH  capture build log (default: $log)
  -jN: Parallel jobs (default: -j\$(nproc) or -j4).
  Output: src/zerod.exe, src/zero-cli.exe, src/zero-tx.exe
EOF
}

# Resolve HOST, BUILD, CC, CXX for native (Linux/Mac). Call from repo root.
resolve_host_native() {
  [[ -z "${CC:-}" ]] && CC=gcc
  [[ -z "${CXX:-}" ]] && CXX=g++
  export CC CXX
  [[ -z "${MAKE:-}" ]] && MAKE=make
  [[ -z "${BUILD:-}" ]] && BUILD="$(./depends/config.guess)"
  [[ -z "${HOST:-}" ]] && HOST="$BUILD"
  [[ -z "${CONFIGURE_FLAGS:-}" ]] && CONFIGURE_FLAGS=""
}

# Resolve HOST, CC, CXX for Windows cross. Call from repo root.
resolve_host_win() {
  HOST=x86_64-w64-mingw32
  CXX=x86_64-w64-mingw32-g++-posix
  CC=x86_64-w64-mingw32-gcc-posix
  PREFIX="$PWD/depends/$HOST"
}

# Shared: set CONFIG_SITE for configure. Call from repo root.
export_config_site() { export CONFIG_SITE="$PWD/depends/$HOST/share/config.site"; }

# Build depends. Call from repo root. Sets HOST, BUILD, NO_PROTON for native.
build_depends_native() {
  eval "$MAKE" --version
  as --version
  ld -v
  if [ -n "${LOG_FILE:-}" ]; then
    HOST="$HOST" BUILD="$BUILD" NO_PROTON="$PROTON_ARG" "$MAKE" "${MAKEARGS[@]}" -C ./depends/ V=1 2>&1 | log_capture
  else
    HOST="$HOST" BUILD="$BUILD" NO_PROTON="$PROTON_ARG" "$MAKE" "${MAKEARGS[@]}" -C ./depends/ V=1
  fi
}

# Build depends for Windows. Call from repo root.
build_depends_win() {
  if [ -n "${LOG_FILE:-}" ]; then
    make -C depends HOST="$HOST" V=1 "${MAKEARGS[@]}" 2>&1 | log_capture
  else
    make -C depends HOST="$HOST" V=1 "${MAKEARGS[@]}"
  fi
}

# Run autogen. Call from repo root.
run_autogen() {
  ./autogen.sh
}

# Run configure for native. Call from repo root.
run_configure_native() {
  export_config_site
  if [ -n "${LOG_FILE:-}" ]; then
    ./configure "$HARDENING_ARG" "$LCOV_ARG" "$TEST_ARG" "$MINING_ARG" $PROTON_ARG $DAEMON_ARG $CONFIGURE_FLAGS CXXFLAGS='-g' 2>&1 | log_capture
  else
    ./configure "$HARDENING_ARG" "$LCOV_ARG" "$TEST_ARG" "$MINING_ARG" $PROTON_ARG $DAEMON_ARG $CONFIGURE_FLAGS CXXFLAGS='-g'
  fi
}

# Run configure for Windows. Call from repo root. Includes sed fix for boost_system-mt.
run_configure_win() {
  export_config_site
  if [ -n "${LOG_FILE:-}" ]; then
    CXXFLAGS+="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" \
      ./configure --prefix="$PREFIX" --host="$HOST" --enable-static --disable-shared --disable-zmq --disable-rust 2>&1 | log_capture
  else
    CXXFLAGS+="-DPTW32_STATIC_LIB -DCURVE_ALT_BN128 -fopenmp -pthread" \
      ./configure --prefix="$PREFIX" --host="$HOST" --enable-static --disable-shared --disable-zmq --disable-rust
  fi
  sed -i.bak 's/-lboost_system-mt /-lboost_system-mt-s /' configure && rm -f configure.bak
}

# Run make for native. Call from repo root.
run_make_native() {
  if [ -n "${LOG_FILE:-}" ]; then
    "$MAKE" "${MAKEARGS[@]}" V=1 2>&1 | log_capture
  else
    "$MAKE" "${MAKEARGS[@]}" V=1
  fi
}

# Run make for Windows. Call from repo root; make runs in src/.
run_make_win() {
  cd src
  if [ -n "${LOG_FILE:-}" ]; then
    CC="$CC" CXX="$CXX" make V=1 "${MAKEARGS[@]}" zerod.exe zero-cli.exe zero-tx.exe 2>&1 | log_capture
  else
    CC="$CC" CXX="$CXX" make V=1 "${MAKEARGS[@]}" zerod.exe zero-cli.exe zero-tx.exe
  fi
}
