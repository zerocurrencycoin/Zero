#!/usr/bin/env bash
# The libsodium build benchmarks compare against, in one place.
#
# Benchmarks that use libsodium as an oracle must state which build, not just
# which version: a poured Homebrew bottle measured 13% slower than the same
# version built -O3, and an earlier session drew two opposite conclusions from
# that difference alone (docs/CROSSPROJECT.md S4).
#
# Prints a prefix suitable for `make bench SODIUM=$(sodium_oracle.sh)`.
# Exit 1 with an explanation if no suitable build exists, rather than falling
# back to whatever the system happens to have.
#
#   contrib/perf/sodium_oracle.sh          # print the prefix
#   contrib/perf/sodium_oracle.sh --build  # build it if absent, then print

export LC_ALL=C
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VER="${ZERO_PERF_SODIUM_VER:-1.0.22}"
PREFIX="${ZERO_PERF_SODIUM_PREFIX:-$REPO_ROOT/reindex-profile/tools/sodium/$VER}"
URL="https://github.com/jedisct1/libsodium/releases/download/${VER}-RELEASE/libsodium-${VER}.tar.gz"

have() { [ -r "$PREFIX/include/sodium/version.h" ] && [ -r "$PREFIX/lib/libsodium.a" ]; }

if have; then
  got=$(sed -n 's/.*SODIUM_VERSION_STRING "\(.*\)".*/\1/p' "$PREFIX/include/sodium/version.h")
  if [ "$got" != "$VER" ]; then
    echo "sodium_oracle: $PREFIX holds $got, expected $VER" >&2
    exit 1
  fi
  echo "$PREFIX"
  exit 0
fi

if [ "${1:-}" != "--build" ]; then
  cat >&2 <<MSG
sodium_oracle: no $VER build at $PREFIX
  build it:  contrib/perf/sodium_oracle.sh --build
  or set:    ZERO_PERF_SODIUM_PREFIX=/path/to/prefix
Not falling back to a system libsodium: its build flags are unknown, and an
oracle built differently from the one under test invalidates the comparison.
MSG
  exit 1
fi

# -O3 static, matching depends/packages/libsodium.mk, so the oracle is built
# the way the shipped library is.
tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
echo "sodium_oracle: building $VER -> $PREFIX" >&2
curl -sL "$URL" | tar xz -C "$tmp" --strip-components=1 || { echo "download failed" >&2; exit 1; }
( cd "$tmp" && CFLAGS="-O3" ./configure --enable-static --disable-shared --prefix="$PREFIX" >/dev/null 2>&1 \
  && make -j"$(sysctl -n hw.ncpu 2>/dev/null || echo 4)" >/dev/null 2>&1 && make install >/dev/null 2>&1 ) \
  || { echo "sodium_oracle: build failed" >&2; exit 1; }
have || { echo "sodium_oracle: build produced no library" >&2; exit 1; }
echo "$PREFIX"
