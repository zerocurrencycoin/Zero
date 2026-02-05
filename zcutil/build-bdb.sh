#!/usr/bin/env bash
# Build Berkeley DB 6.2.32 for Zero wallet support on Raspberry Pi

set -eu -o pipefail

cd "$(dirname "$0")/.."

ZERO_ROOT=$(pwd)
BDB_PREFIX="${ZERO_ROOT}/db6"

echo "================================================"
echo "Building Berkeley DB 6.2.32 for Zero"
echo "This is required for wallet functionality"
echo "================================================"

# Create directory for BDB
mkdir -p $BDB_PREFIX

# Download Berkeley DB 6.2.32
if [ ! -f "db-6.2.32.tar.gz" ]; then
    echo "Downloading Berkeley DB 6.2.32..."
    wget 'http://download.oracle.com/berkeley-db/db-6.2.32.tar.gz'
    
    # Verify checksum
    echo 'a9c5e2b004a5777aa03510cfe5cd766a4a3b777713406b02809c17c8e0e7a8fb  db-6.2.32.tar.gz' | sha256sum -c
fi

# Extract if not already extracted
if [ ! -d "db-6.2.32" ]; then
    echo "Extracting Berkeley DB..."
    tar -xzvf db-6.2.32.tar.gz
fi

# Build and install BDB
echo "Building Berkeley DB (this will take 10-20 minutes)..."
cd db-6.2.32/build_unix/

# Configure with static build and PIC support
../dist/configure \
    --enable-cxx \
    --disable-shared \
    --with-pic \
    --prefix=$BDB_PREFIX \
    CFLAGS="-O2 -mcpu=cortex-a76" \
    CXXFLAGS="-O2 -mcpu=cortex-a76"

# Build with limited parallelism for Raspberry Pi
make -j2
make install

cd $ZERO_ROOT

echo "================================================"
echo "Berkeley DB 6.2.32 installed successfully!"
echo "Installation directory: $BDB_PREFIX"
echo "================================================"
echo ""
echo "Now you can build Zero with wallet support:"
echo "  source ~/.cargo/env"
echo "  ./autogen.sh"
echo "  ./configure \\"
echo "    --enable-hardening \\"
echo "    --disable-tests \\"
echo "    --disable-bench \\"
echo "    --without-gui \\"
echo "    LDFLAGS=\"-L${BDB_PREFIX}/lib/\" \\"
echo "    CPPFLAGS=\"-I${BDB_PREFIX}/include/\" \\"
echo "    CXXFLAGS=\"-O2 -mcpu=cortex-a76\" \\"
echo "    CFLAGS=\"-O2 -mcpu=cortex-a76\""
echo "  make -j2"
echo ""
