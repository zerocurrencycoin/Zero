# Zero Currency Build Guide

This document provides comprehensive instructions for building Zero Currency (zerod) and Zero Wallet (zerowallet) from source.

## Table of Contents
- [System Requirements](#system-requirements)
- [GNU Toolchain Setup](#gnu-toolchain-setup)
- [C++11 Configuration](#c11-configuration)
- [Package Dependencies](#package-dependencies)
- [Build Process](#build-process)
- [Troubleshooting](#troubleshooting)
- [Build Configuration Options](#build-configuration-options)

---

## System Requirements

### **Supported Platforms**
- **Linux**: Ubuntu 18.04+, Debian 9+, CentOS 7+, Fedora 28+
- **macOS**: 10.14+ (Mojave and later)
- **Windows**: Windows 10+ (MinGW cross-compilation or WSL2)

### **Minimum Hardware**
- **RAM**: 4GB (8GB recommended for parallel builds)
- **Storage**: 10GB free space for full build
- **CPU**: Multi-core processor (build time scales with cores)

### **Software Requirements**
- **GCC**: 7.0+ (supports C++11/14/17)
- **GNU Make**: 4.0+
- **Python**: 3.6+
- **Git**: 2.0+

---

## GNU Toolchain Setup

### **1. Install GNU Compiler Collection (GCC)**

#### **Ubuntu/Debian:**
```bash
# Update package lists
sudo apt update

# Install GCC and development tools
sudo apt install build-essential

# Verify GCC version (should be 7.0 or higher)
gcc --version
g++ --version

# Example output:
# gcc (Ubuntu 9.4.0-1ubuntu1~20.04.2) 9.4.0
# g++ (Ubuntu 9.4.0-1ubuntu1~20.04.2) 9.4.0
```

#### **CentOS/RHEL/Fedora:**
```bash
# CentOS/RHEL
sudo yum groupinstall "Development Tools"
# OR for newer versions
sudo dnf groupinstall "Development Tools"

# Fedora
sudo dnf install gcc gcc-c++ make

# Verify installation
gcc --version
g++ --version
```

#### **macOS:**
```bash
# Install Xcode Command Line Tools
xcode-select --install

# OR install via Homebrew
brew install gcc

# Verify installation
gcc --version
g++ --version
```

### **2. Configure GNU Environment Variables**

#### **Set Compiler Preferences:**
```bash
# Add to ~/.bashrc or ~/.profile for persistent settings
export CC=gcc
export CXX=g++
export CFLAGS="-O2 -g"
export CXXFLAGS="-O2 -g"

# Apply settings to current session
source ~/.bashrc
```

#### **Multi-Core Build Configuration:**
```bash
# Set parallel build jobs (adjust based on CPU cores)
export MAKEFLAGS="-j$(nproc)"

# For macOS
export MAKEFLAGS="-j$(sysctl -n hw.ncpu)"

# For Windows (in WSL2)
export MAKEFLAGS="-j$(nproc)"

# Verify core count
echo "Building with $(nproc) parallel jobs"
```

#### **Windows Cross-Compilation Setup:**
```bash
# Install MinGW-w64 cross-compilation toolchain (Linux → Windows)
sudo apt install mingw-w64

# Set MinGW environment for cross-compilation
export HOST=x86_64-w64-mingw32
export CC=${HOST}-gcc
export CXX=${HOST}-g++
export AR=${HOST}-ar
export STRIP=${HOST}-strip
```

### **3. GNU Autotools Setup**

```bash
# Ubuntu/Debian
sudo apt install autoconf automake libtool m4

# CentOS/RHEL/Fedora
sudo yum install autoconf automake libtool m4
# OR
sudo dnf install autoconf automake libtool m4

# macOS (via Homebrew)
brew install autoconf automake libtool

# Verify autotools versions
autoconf --version    # Should be 2.69+
automake --version    # Should be 1.15+
libtool --version     # Should be 2.4+
```

---

## C++11 Configuration

Zero Currency requires C++11 standard support for modern C++ features.

### **1. Verify C++11 Support**

```bash
# Test C++11 compiler support
echo '#include <iostream>
#include <memory>
int main() {
    auto ptr = std::make_unique<int>(42);
    std::cout << "C++11 support: " << *ptr << std::endl;
    return 0;
}' > test_cpp11.cpp

# Compile with C++11 standard
g++ -std=c++11 test_cpp11.cpp -o test_cpp11

# Run test
./test_cpp11
# Expected output: C++11 support: 42

# Clean up
rm test_cpp11.cpp test_cpp11
```

### **2. Configure C++11 Build Environment**

```bash
# Set C++11 as default standard
export CXXFLAGS="$CXXFLAGS -std=c++11"

# Alternative: Set specific C++ standard (C++14/17 also supported)
export CXXFLAGS="$CXXFLAGS -std=c++14"

# Verify configuration
echo $CXXFLAGS
```

### **3. GCC C++11 Feature Support**

Zero Currency uses these C++11 features:
- **Auto keyword**: Automatic type deduction
- **Lambda expressions**: Anonymous functions
- **Smart pointers**: `std::unique_ptr`, `std::shared_ptr`
- **Range-based for loops**: Simplified iteration
- **Move semantics**: Efficient object transfers
- **Thread support**: `std::thread`, `std::mutex`

---

## Package Dependencies

### **Core Build Dependencies**

Install all required packages:

```bash
# Ubuntu/Debian - Complete package installation
sudo apt update
sudo apt install \
    build-essential \
    pkg-config \
    libc6-dev \
    m4 \
    g++-multilib \
    autoconf \
    libtool \
    ncurses-dev \
    unzip \
    git \
    python3 \
    python3-zmq \
    zlib1g-dev \
    wget \
    bsdmainutils \
    automake \
    cmake \
    curl

# Verify critical packages
pkg-config --version
python3 --version
cmake --version
```

### **Optional GUI Dependencies**

For building Zero Wallet (GUI):

```bash
# Ubuntu/Debian - Complete Qt5 and GUI dependencies
sudo apt install \
    qt5-default \
    qt5-qmake \
    qtbase5-dev \
    qtbase5-dev-tools \
    qttools5-dev-tools \
    libqt5gui5 \
    libqt5core5a \
    libqt5webkit5-dev \
    libqt5websockets5-dev \
    libprotobuf-dev \
    protobuf-compiler

# macOS (via Homebrew)
brew install qt5 protobuf

# Set Qt5 path for macOS
export PATH="/usr/local/opt/qt5/bin:$PATH"
```

### **Complete Package Installation Command**

```bash
#!/bin/bash
# Complete Zero Currency build dependency installation

echo "=== Installing Zero Currency Build Dependencies ==="

# Core build dependencies
sudo apt update
sudo apt install -y \
    build-essential \
    pkg-config \
    libc6-dev \
    m4 \
    g++-multilib \
    autoconf \
    libtool \
    ncurses-dev \
    unzip \
    git \
    python3 \
    python3-zmq \
    zlib1g-dev \
    wget \
    bsdmainutils \
    automake \
    cmake \
    curl

echo "✓ Core build dependencies installed"

# Optional GUI dependencies (for zerowallet)
read -p "Install GUI dependencies for Zero Wallet? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo apt install -y \
        qt5-default \
        qt5-qmake \
        qtbase5-dev \
        qtbase5-dev-tools \
        qttools5-dev-tools \
        libqt5gui5 \
        libqt5core5a \
        libqt5webkit5-dev \
        libqt5websockets5-dev \
        libprotobuf-dev \
        protobuf-compiler
    echo "✓ GUI dependencies installed"
fi

echo "=== Package installation complete ==="
```

### **Package Verification Script**

```bash
#!/bin/bash
# Package verification script
echo "=== Zero Currency Build Dependencies Check ==="

# Check critical build tools
command -v gcc >/dev/null 2>&1 || { echo "ERROR: gcc not found"; exit 1; }
command -v g++ >/dev/null 2>&1 || { echo "ERROR: g++ not found"; exit 1; }
command -v make >/dev/null 2>&1 || { echo "ERROR: make not found"; exit 1; }
command -v autoconf >/dev/null 2>&1 || { echo "ERROR: autoconf not found"; exit 1; }
command -v automake >/dev/null 2>&1 || { echo "ERROR: automake not found"; exit 1; }
command -v libtool >/dev/null 2>&1 || { echo "ERROR: libtool not found"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
command -v cmake >/dev/null 2>&1 || { echo "ERROR: cmake not found"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git not found"; exit 1; }

echo "✓ All required build tools found"

# Check Python ZMQ support
python3 -c "import zmq; print('✓ Python ZMQ support:', zmq.zmq_version())" 2>/dev/null || \
    echo "WARNING: python3-zmq not available"

# Check GCC version
GCC_VERSION=$(gcc -dumpversion | cut -d. -f1)
if [ "$GCC_VERSION" -ge 7 ]; then
    echo "✓ GCC version: $(gcc --version | head -n1)"
else
    echo "ERROR: GCC version $GCC_VERSION too old (need 7.0+)"
    exit 1
fi

# Check C++11 support
if g++ -std=c++11 -dM -E - < /dev/null | grep -q __cplusplus; then
    echo "✓ C++11 support confirmed"
else
    echo "ERROR: C++11 support not available"
    exit 1
fi

# Check Qt5 (optional for GUI)
if command -v qmake >/dev/null 2>&1; then
    echo "✓ Qt5 qmake found: $(qmake --version | grep -o 'Qt version [0-9.]*')"
    
    # Check specific Qt5 components
    pkg-config --exists Qt5Core && echo "✓ Qt5Core available" || echo "WARNING: Qt5Core not found"
    pkg-config --exists Qt5Widgets && echo "✓ Qt5Widgets available" || echo "WARNING: Qt5Widgets not found"
    pkg-config --exists Qt5WebSockets && echo "✓ Qt5WebSockets available" || echo "WARNING: Qt5WebSockets not found"
else
    echo "INFO: Qt5 not installed (GUI wallet will not be available)"
fi

echo "=== Dependency verification complete ==="
```

---

## Build Process

### **1. Clone Repository**

```bash
# Clone Zero Currency source code
git clone https://github.com/zerocurrencycoin/zero.git
cd zero

# Check current branch and latest commits
git branch -v
git log --oneline -5
```

### **2. Build Dependencies (Depends System)**

Zero Currency uses a depends system to build required libraries from source:

```bash
# Navigate to depends directory
cd depends

# Build all dependencies (this takes 30-60 minutes)
make -j$(nproc)

# Monitor build progress
# Dependencies built include: Boost, Berkeley DB, OpenSSL, ZeroMQ, etc.

# Verify depends build completion
ls -la x86_64-unknown-linux-gnu/
# Should contain: bin/ include/ lib/ share/ directories

# Return to root directory
cd ..
```

#### **Depends Build Troubleshooting:**
```bash
# If depends build fails, try single-threaded build
cd depends
make -j1

# Clean and rebuild specific dependency
make clean-boost
make boost

# View available make targets
make help
```

### **3. Configure Build System**

```bash
# Generate configure script
./autogen.sh

# Configure build with depends
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu

# Alternative: Configure with custom options
./configure \
    --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu \
    --enable-cxx \
    --disable-shared \
    --with-pic \
    --with-bignum=no \
    --enable-module-recovery
```

#### **Common Configure Options:**
```bash
# Wallet-disabled build
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu --disable-wallet

# Debug build
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu --enable-debug

# GUI wallet build
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu --with-gui=qt5

# View all configure options
./configure --help
```

### **4. Build Zero Currency**

```bash
# Build Zero daemon (primary binary)
make -j$(nproc) zerod

# Build all binaries
make -j$(nproc)

# Build specific targets
make -j$(nproc) zero-cli    # Command-line interface
make -j$(nproc) zero-tx     # Transaction utility
make -j$(nproc) zerowallet  # GUI wallet (if configured)

# Monitor build progress
# Build typically takes 15-30 minutes depending on hardware
```

#### **Build Output Locations:**
```bash
# Built binaries location
ls -la src/
# Key files:
# - zerod         (Zero Currency daemon)
# - zero-cli      (Command line interface)
# - zero-tx       (Transaction manipulation tool)
# - qt/zerowallet (GUI wallet, if built)
```

### **5. Build Verification**

```bash
# Test zerod binary
src/zerod --version
# Expected output: Zero Core Daemon version v2.x.x

# Test zero-cli
src/zero-cli --version
# Expected output: Zero Core RPC client version v2.x.x

# Basic functionality test
src/zerod -testnet -daemon
sleep 5
src/zero-cli -testnet getblockchaininfo
src/zero-cli -testnet stop
```

### **6. Windows-Specific Build Instructions**

#### **Method 1: MinGW Cross-Compilation (Linux → Windows)**

**Prerequisites:**
```bash
# Install MinGW-w64 toolchain on Linux (Ubuntu/Debian)
sudo apt update
sudo apt install mingw-w64 build-essential

# Verify MinGW installation
x86_64-w64-mingw32-gcc --version
```

**Cross-Compilation Process:**
```bash
# 1. Prepare dependencies for Windows target
cd depends
make HOST=x86_64-w64-mingw32 -j$(nproc)
cd ..

# 2. Configure for Windows cross-compilation
./autogen.sh
./configure --prefix=$(pwd)/depends/x86_64-w64-mingw32 \
            --host=x86_64-w64-mingw32 \
            --disable-shared \
            --enable-static

# 3. Build Windows binaries
make -j$(nproc)

# 4. Windows binaries will be created:
# - src/zerod.exe
# - src/zero-cli.exe
# - src/zero-tx.exe
```

**Deployment to Windows:**
```bash
# Copy required files to Windows machine:
# 1. Built .exe files from src/
# 2. Zero configuration files
# 3. Zcash parameters (if needed)

# On Windows, create data directory:
# %APPDATA%\Zero\

# Create zero.conf configuration file in data directory
```

#### **Method 2: Windows Subsystem for Linux (WSL2)**

**Setup WSL2 Environment:**
```bash
# 1. Install WSL2 on Windows 10/11
# Follow Microsoft's official WSL2 installation guide

# 2. Install Ubuntu 20.04+ in WSL2
# Use Microsoft Store or wsl --install

# 3. Inside WSL2, follow standard Linux build instructions:
sudo apt update
sudo apt install build-essential pkg-config libc6-dev m4 g++-multilib \
    autoconf libtool ncurses-dev unzip git python3 python3-zmq \
    zlib1g-dev wget bsdmainutils automake cmake curl

# 4. Build normally as Linux
./zcutil/build.sh -j$(nproc)

# 5. Binaries run natively in WSL2 environment
./src/zerod --version
```

#### **Windows Build Testing:**
```bash
# For cross-compiled Windows binaries, test on Windows machine:

# 1. Copy .exe files to Windows
# 2. Install Python 3 + dependencies:
pip install simplejson wheel pyblake2

# 3. Run basic tests:
zerod.exe --version
zero-cli.exe --version

# 4. For full testing, set environment:
set BITCOIND=path\to\zerod.exe
cd qa\rpc-tests
pytest

# 5. Create Windows service (optional):
# Use NSSM or sc.exe to install zerod as Windows service
```

#### **Windows-Specific Notes:**
- **Firewall**: Allow zerod.exe through Windows Firewall
- **Antivirus**: May need to whitelist cryptocurrency binaries
- **Data Directory**: Default location is `%APPDATA%\Zero\`
- **Configuration**: Use `zero.conf` in data directory
- **Parameters**: Download parameters to `%APPDATA%\ZcashParams\`
- **Dependencies**: Visual Studio redistributables may be required

---

## Troubleshooting

### **Common Build Issues**

#### **1. GCC Version Too Old**
```bash
# Error: "This application requires GCC 7.0 or later"
# Solution: Update GCC
sudo apt install gcc-9 g++-9
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-9 60
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-9 60
```

#### **2. Boost Compilation Warnings**
```bash
# Error: Boost 1.70.0 deprecation warnings with GCC 13+
# Solution: Warnings already suppressed in src/Makefile.am
grep -n "Wno-deprecated-declarations" src/Makefile.am
# Should show: AM_CXXFLAGS += -Wno-deprecated-declarations -Wno-nonnull
```

#### **3. Berkeley DB Issues**
```bash
# Error: "Berkeley DB not found"
# Solution: Ensure depends build completed successfully
ls depends/x86_64-unknown-linux-gnu/lib/libdb*
# Should show Berkeley DB libraries

# Rebuild depends if necessary
cd depends && make clean-bdb && make bdb && cd ..
```

#### **4. Memory Issues During Build**
```bash
# Error: "virtual memory exhausted" or "killed"
# Solution: Reduce parallel jobs
make -j1 zerod

# Or add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### **5. Qt/GUI Build Issues**
```bash
# Error: Qt5 not found
# Solution: Install complete Qt5 development packages
sudo apt install \
    qt5-default \
    qt5-qmake \
    qtbase5-dev \
    qtbase5-dev-tools \
    qttools5-dev-tools \
    libqt5websockets5-dev

# Set Qt5 path (if needed)
export PKG_CONFIG_PATH="/usr/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH"

# Verify Qt5 installation
qmake --version
pkg-config --modversion Qt5Core
```

### **Build Log Analysis**

```bash
# Capture full build log
make -j$(nproc) zerod 2>&1 | tee build.log

# Search for errors
grep -i error build.log
grep -i "undefined reference" build.log

# Check warnings
grep -i warning build.log | head -20
```

### **Clean Build Process**

```bash
# Clean previous build
make clean

# Clean configuration
make distclean

# Clean depends (if needed)
cd depends && make clean && cd ..

# Full rebuild
./autogen.sh
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu
make -j$(nproc) zerod
```

---

## Build Configuration Options

### **Wallet Configuration**

```bash
# Enable wallet (default)
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu

# Disable wallet (for servers/nodes)
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu --disable-wallet
```

### **GUI Configuration**

```bash
# Build with Qt5 GUI
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu --with-gui=qt5

# Disable GUI (daemon only)
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu --without-gui
```

### **Debug/Release Builds**

```bash
# Release build (default, optimized)
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu

# Debug build (symbols, no optimization)
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu --enable-debug

# Debug with optimization
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu --enable-debug --enable-optimize
```

### **Advanced Options**

```bash
# Full feature build
./configure \
    --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu \
    --enable-cxx \
    --enable-static \
    --disable-shared \
    --with-pic \
    --enable-benchmark \
    --enable-tests

# Minimal build (smallest binary)
./configure \
    --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu \
    --disable-wallet \
    --disable-zmq \
    --disable-tests \
    --disable-bench \
    --without-gui
```

---

## Installation

### **System Installation**

```bash
# Install to system (optional)
sudo make install

# Install to custom prefix
make install DESTDIR=/opt/zero

# Create symlinks for easy access
sudo ln -sf /usr/local/bin/zerod /usr/bin/zerod
sudo ln -sf /usr/local/bin/zero-cli /usr/bin/zero-cli
```

### **Portable Installation**

```bash
# Create portable directory
mkdir -p ~/zero-portable
cp src/zerod ~/zero-portable/
cp src/zero-cli ~/zero-portable/
cp src/zero-tx ~/zero-portable/

# Add to PATH
echo 'export PATH="$HOME/zero-portable:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## Build Performance Tips

### **Optimization Flags**

```bash
# High-performance build
export CXXFLAGS="-O3 -march=native -mtune=native"
export CFLAGS="-O3 -march=native -mtune=native"

# Configure and build
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu
make -j$(nproc) zerod
```

### **Parallel Build Tuning**

```bash
# Optimal parallel jobs (usually CPU cores + 1)
CORES=$(nproc)
JOBS=$((CORES + 1))
make -j$JOBS zerod

# For systems with limited RAM
make -j2 zerod
```

### **ccache Integration**

```bash
# Install ccache for faster rebuilds
sudo apt install ccache

# Configure ccache
export CC="ccache gcc"
export CXX="ccache g++"
export CCACHE_DIR="$HOME/.ccache"

# Set cache size
ccache -M 5G

# Check cache statistics
ccache -s
```

---

## Validation and Testing

### **Basic Functionality Test**

```bash
# Version check
./src/zerod --version

# Help output
./src/zerod --help

# Configuration test
./src/zerod -testnet -printtoconsole &
sleep 10
./src/zero-cli -testnet getblockchaininfo
./src/zero-cli -testnet stop
```

### **Unit Tests (Currently Broken)** ⚠️

**Known Issue: Unit tests have linking errors and are currently broken.**

```bash
# Attempting to build unit tests will show linking errors:
make check
# Error examples:
# - undefined reference to `IsMine(CKeyStore const&, CScript const&)'
# - undefined reference to `zeronodeConfig'
# - undefined reference to `RegisterZeroExclusiveRPCCommands(CRPCTable&)'
# - undefined reference to `bitdb'
```

#### **Test Issues Identified:**

1. **Wallet Function Linking Errors:**
   ```
   undefined reference to `IsMine(CKeyStore const&, CScript const&)'
   ```
   - **Cause:** Test files reference wallet functions but don't link wallet library
   - **Files Affected:** `multisig_tests.cpp`, `rpc_wallet_tests.cpp`

2. **Zeronode Configuration Errors:**
   ```
   undefined reference to `zeronodeConfig'
   undefined reference to `CZeronodeConfig::read(...)'
   ```
   - **Cause:** Missing zeronode configuration object linking
   - **Files Affected:** Main test harness

3. **Database Backend Errors:**
   ```
   undefined reference to `bitdb'
   undefined reference to `CDBEnv::Flush(bool)'
   ```
   - **Cause:** Berkeley DB environment not properly linked in tests

4. **RPC Registration Errors:**
   ```
   undefined reference to `RegisterZeroExclusiveRPCCommands(CRPCTable&)'
   ```
   - **Cause:** Zero-specific RPC commands not linked in test builds

#### **Test Fix Requirements:**

To fix the broken tests, the following linking issues need resolution:

```bash
# Required additions to src/Makefile.test.include:
# 1. Add wallet library: $(LIBBITCOIN_WALLET)
# 2. Add zeronode objects: zeronode/zeronodeconfig.o
# 3. Add DB environment: proper Berkeley DB linking
# 4. Add Zero RPC registration functions
```

#### **Manual Testing Workaround:**

Since unit tests are broken, use manual verification:

```bash
# Manual functionality verification
./src/zerod -testnet -printtoconsole &
sleep 10

# Test basic RPC functionality
./src/zero-cli -testnet getblockchaininfo
./src/zero-cli -testnet getwalletinfo
./src/zero-cli -testnet getnewaddress

# Test zeronode commands  
./src/zero-cli -testnet zeronode status
./src/zero-cli -testnet zeronode list

# Stop daemon
./src/zero-cli -testnet stop
```

### **Regression Tests (Working)**

Python regression tests are more likely to work as they test the built binaries:

```bash
# Navigate to RPC tests directory
cd qa/rpc-tests

# Run individual tests
python3 wallet.py
python3 blockchain.py
python3 mempool_reorg.py

# Run with test framework
../pull-tester/rpc-tests.sh wallet

# View available tests
ls *.py | grep -v test_framework

# Run extended test suite (takes longer)
../pull-tester/rpc-tests.sh -extended
```

#### **RPC Test Dependencies:**

```bash
# Ensure Python requirements are met
python3 -c "import zmq; print('✓ ZMQ available')" || echo "❌ Install python3-zmq"
python3 -c "import json; print('✓ JSON available')"
python3 -c "import threading; print('✓ Threading available')"

# Test with specific options
PYTHON_DEBUG=1 qa/pull-tester/rpc-tests.sh wallet
```

---

## Fixing Broken Unit Tests

### **Test Linking Issues Resolution**

The unit tests are broken due to missing library links. Here's how to fix them:

#### **1. Update Test Makefile**

Edit `src/Makefile.test.include` to add missing dependencies:

```bash
# Find the test_bitcoin_LDADD section and ensure it includes:
test_bitcoin_LDADD = \
  $(LIBBITCOIN_SERVER) \
  $(LIBBITCOIN_CLI) \
  $(LIBBITCOIN_COMMON) \
  $(LIBBITCOIN_UTIL) \
  $(LIBBITCOIN_WALLET) \    # <- ADD THIS
  $(LIBBITCOIN_ZMQ) \
  $(LIBBITCOIN_CONSENSUS) \
  $(LIBZCASH) \
  $(LIBZCASH_LIBS) \
  $(LIBUNIVALUE) \
  $(LIBLEVELDB) \
  $(LIBMEMENV) \
  $(BOOST_LIBS) \
  $(BOOST_UNIT_TEST_FRAMEWORK_LIB) \
  $(LIBSECP256K1) \
  $(EVENT_LIBS) \
  $(EVENT_PTHREADS_LIBS)
```

#### **2. Add Missing Object Files**

Add zeronode configuration objects to the test build:

```bash
# Add to test_bitcoin_SOURCES in Makefile.test.include:
test_bitcoin_SOURCES += \
  zeronode/zeronodeconfig.cpp \    # <- ADD THIS
  zeronode/zeronodeconfig.h        # <- ADD THIS
```

#### **3. Fix RPC Registration**

Create missing RPC registration function or add conditional compilation:

```cpp
// In src/rpc/register.h - add missing function or make it conditional:
#ifdef ENABLE_WALLET
void RegisterZeroExclusiveRPCCommands(CRPCTable& tableRPC);
#else
inline void RegisterZeroExclusiveRPCCommands(CRPCTable& tableRPC) {}
#endif
```

#### **4. Conditional Test Compilation**

Wrap wallet-dependent tests in conditional compilation:

```cpp
// In test files like multisig_tests.cpp:
#ifdef ENABLE_WALLET
BOOST_AUTO_TEST_CASE(multisig_test)
{
    // Test code using IsMine() function
}
#endif
```

#### **5. Test Build Commands**

After fixes, build and run tests:

```bash
# Clean previous build
make clean

# Rebuild with tests
make -j$(nproc)
make check

# Run specific test suites
src/test/test_bitcoin --run_test=basic_tests
src/test/test_bitcoin --run_test=script_tests
```

### **Alternative: Skip Broken Tests**

If fixing tests is complex, disable problematic test files:

```bash
# Comment out broken tests in src/Makefile.test.include:
# test/multisig_tests.cpp \    <- Comment out
# test/rpc_wallet_tests.cpp \  <- Comment out

# Build without broken tests
make check
```

### **Test Status Summary**

| Test Category | Status | Action Required |
|---------------|--------|-----------------|
| **Unit Tests** | ❌ Broken | Fix linking issues |
| **RPC Tests** | ✅ Working | Use for validation |
| **Integration Tests** | ⚠️ Unknown | Manual verification |
| **Build Tests** | ✅ Working | Already functional |

---

## Build Success Verification

Upon successful build completion, you should have:

```bash
# Core binaries
ls -la src/zerod       # Zero Currency daemon
ls -la src/zero-cli    # Command-line interface
ls -la src/zero-tx     # Transaction utility

# Optional GUI binary (if built with --with-gui=qt5)
ls -la src/qt/zerowallet

# Check binary functionality
./src/zerod --version
./src/zero-cli --version

echo "✓ Zero Currency build completed successfully!"
```

---

## Support and Resources

### **Documentation**
- **Official Docs**: https://docs.zerocurrency.com
- **Developer Guide**: https://github.com/zerocurrencycoin/zero/doc
- **RPC Documentation**: Use `zero-cli help` for command reference

### **Community Support**
- **GitHub Issues**: https://github.com/zerocurrencycoin/zero/issues
- **Discord**: Zero Currency community channels
- **Reddit**: r/ZeroCurrency

### **Build Environment Resources**
- **GNU Autotools Manual**: https://www.gnu.org/software/autotools/
- **GCC Documentation**: https://gcc.gnu.org/onlinedocs/
- **C++11 Reference**: https://en.cppreference.com/w/cpp/11

---

*Last Updated: December 2024*  
*Zero Currency Version: 2.x.x*  
*Build Guide Version: 1.0*