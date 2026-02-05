#!/usr/bin/env bash
# Complete build script for Zero with wallet support on Raspberry Pi
# Builds librustzcash manually with system Rust, uses custom BDB for wallet

set -eu -o pipefail

cd "$(dirname "$0")/.."

ZERO_ROOT=$(pwd)
BDB_PREFIX="${ZERO_ROOT}/db6"
BUILD_ARCH="aarch64-unknown-linux-gnu"
LIBRUSTZCASH_DIR="${ZERO_ROOT}/depends/work/build/${BUILD_ARCH}/librustzcash/0.1-af991e044ee"

echo "================================================"
echo "Building Zero with Wallet Support"
echo "Raspberry Pi 5 (ARM64) - Manual Build"
echo "================================================"

# Source Rust environment
source "$HOME/.cargo/env"

# Check Rust version
echo "Checking Rust version..."
rustc --version
cargo --version

# Check if Berkeley DB 6.2.32 is installed
if [ ! -f "${BDB_PREFIX}/lib/libdb_cxx.a" ]; then
    echo ""
    echo "ERROR: Berkeley DB 6.2.32 not found!"
    echo "Please run ./zcutil/build-bdb.sh first"
    echo ""
    exit 1
fi

echo "✓ Berkeley DB 6.2.32 found at ${BDB_PREFIX}"
echo ""

# Install required system packages
echo "Checking system dependencies..."
if ! dpkg -l | grep -q libutfcpp-dev; then
    echo "Installing libutfcpp-dev..."
    sudo apt-get install -y libutfcpp-dev
fi
echo "✓ System dependencies satisfied"
echo ""

# Apply source code fixes for modern compilers
echo "Applying source code patches..."

# Fix 1: Add boost::placeholders to validationinterface.cpp
if ! grep -q "using namespace boost::placeholders" src/validationinterface.cpp; then
    sed -i '/#include "validationinterface.h"/a \
using namespace boost::placeholders;' src/validationinterface.cpp
    echo "✓ Fixed boost placeholders in validationinterface.cpp"
fi

# Fix 2: Add <deque> header to httpserver.cpp
if ! grep -q "#include <deque>" src/httpserver.cpp; then
    sed -i '/#include <boost\/algorithm\/string\/case_conv.hpp>/i #include <deque>' src/httpserver.cpp
    echo "✓ Fixed missing <deque> in httpserver.cpp"
fi

# Fix 3: Add <stdexcept> header to crypto/equihash.h
if ! grep -q "#include <stdexcept>" src/crypto/equihash.h; then
    sed -i '/#include "equihash.tcc"/i #include <stdexcept>' src/crypto/equihash.h
    echo "✓ Fixed missing <stdexcept> in crypto/equihash.h"
fi

echo "✓ All source patches applied"
echo ""

# Extract librustzcash source if not already done
if [ ! -d "${LIBRUSTZCASH_DIR}" ]; then
    echo "Extracting librustzcash source from depends..."
    make -C ./depends/ HOST="$BUILD_ARCH" librustzcash || true
    sleep 2
fi

# Build librustzcash with system Rust
if [ ! -f "${LIBRUSTZCASH_DIR}/target/release/librustzcash.a" ]; then
    echo "Building librustzcash with Rust 1.70.0..."
    echo "This may take 30-60 minutes..."
    cd "${LIBRUSTZCASH_DIR}"
    cargo build --release
    cd "${ZERO_ROOT}"
    echo ""
    echo "✓ librustzcash built successfully"
else
    echo "✓ librustzcash already built"
fi
echo ""

# Create src/rust directory and copy librustzcash
echo "Installing librustzcash to src/rust/..."
mkdir -p "${ZERO_ROOT}/src/rust/lib"
mkdir -p "${ZERO_ROOT}/src/rust/include"

cp -v "${LIBRUSTZCASH_DIR}/target/release/librustzcash.a" \
      "${ZERO_ROOT}/src/rust/lib/"

cp -v "${LIBRUSTZCASH_DIR}/librustzcash/include/librustzcash.h" \
      "${ZERO_ROOT}/src/rust/include/"

echo "✓ librustzcash installed"
echo ""

# Generate configure script if needed
if [ ! -f "./configure" ]; then
    echo "Running autogen.sh..."
    ./autogen.sh
fi

# Configure with Berkeley DB and manually-built Rust components
echo "Configuring Zero with wallet support..."
./configure \
    --enable-hardening \
    --disable-tests \
    --disable-bench \
    --without-gui \
    --enable-proton=no \
    LDFLAGS="-L${BDB_PREFIX}/lib/ -L${ZERO_ROOT}/src/rust/lib/" \
    CPPFLAGS="-I${BDB_PREFIX}/include/ -I${ZERO_ROOT}/src/rust/include/" \
    CXXFLAGS="-O2 -mcpu=cortex-a76" \
    CFLAGS="-O2 -mcpu=cortex-a76"

echo ""
echo "================================================"
echo "Building Zero (this will take 2-4 hours)..."
echo "Using -j2 to conserve memory"
echo "================================================"
echo ""

# Build with limited parallelism
make -j2 V=1

echo ""
echo "================================================"
echo "Build complete!"
echo "================================================"
echo ""
echo "Binaries are in: ./src/"
echo "  - zerod (daemon with WALLET support)"
echo "  - zero-cli (command line interface)"
echo "  - zero-tx (transaction tool)"
echo ""
echo "Test the build:"
echo "  ./src/zerod --version"
echo "  ./src/zero-cli --version"
echo ""
echo "Your wallet will be created at: ~/.zero/wallet.zero"
echo "IMPORTANT: Backup your wallet regularly!"
echo ""
