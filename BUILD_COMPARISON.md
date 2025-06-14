# Build Architecture Comparison Report

## Build System Commands

### Zero Currency
```bash
# Dependencies
cd depends && make -j$(nproc)
# Configure  
./configure --prefix=$(pwd)/depends/x86_64-unknown-linux-gnu
# Build
make -j$(nproc) zerod
```
**Source**: BUILD.md:376-392, 410-425, 442-458

### Bitcoin Core  
```bash
# Linux
cmake -B build
cmake --build build -j$(nproc)

# Windows Cross-compile
gmake -C depends HOST=x86_64-w64-mingw32
cmake -B build --toolchain depends/x86_64-w64-mingw32/toolchain.cmake
cmake --build build
```
**Source**: doc/build-unix.md, doc/build-windows.md

### Zcash
```bash
./zcutil/fetch-params.sh
./zcutil/clean.sh  
./zcutil/build.sh -j$(nproc)
```
**Source**: README.md, zcash.readthedocs.io/en/latest/rtd_pages/Debian-Ubuntu-build.html

### Pirate/Horizen
**Pirate**: Boost 1.83.0, BDB 6.2.32  
**Horizen**: Boost 1.82.0, BDB 6.2.23  
**Source**: HPVER.md:8-11

## Windows Build Analysis

### Bitcoin - Windows Cross-Compilation (Mingw-w64)
```bash
# Install dependencies (refer to depends/README.md)
# Optional: Install NSIS for installer
git clone https://github.com/bitcoin/bitcoin.git
gmake -C depends HOST=x86_64-w64-mingw32
cmake -B build --toolchain depends/x86_64-w64-mingw32/toolchain.cmake  
cmake --build build
# Install to Windows directory
cmake --install build --prefix /mnt/c/workspace/bitcoin
# Optional installer
cmake --build build --target deploy
```
**Source**: doc/build-windows.md
**WSL Note**: Bitcoin source must be in default mount filesystem

### Bitcoin - Windows Native (Visual Studio)
**Reference**: "see separate documentation" mentioned in doc/build-windows.md
**Status**: Visual Studio build documented separately (not fetched)

### Zero - Windows Support
**Ubuntu Linux**: BUILD.md:18-21 lists "Windows 10+ (WSL2 recommended)"
**Cross-compilation**: Not documented
**Native Windows**: Not documented  
**Available**: No Windows-specific build instructions found

### Zcash - Windows Support
**Documentation**: "Currently, Zcash is only officially supported on Debian and Ubuntu"  
**Status**: No Windows build support

### Pirate/Horizen - Windows Support  
**Status**: No specific Windows build documentation found in fetched materials

## Dependencies Comparison

### Zero Currency (BUILD.md:187-218)
```bash
sudo apt install \
    build-essential pkg-config libc6-dev m4 g++-multilib \
    autoconf libtool ncurses-dev unzip git python3 python3-zmq \
    zlib1g-dev wget bsdmainutils automake cmake curl

# GUI (BUILD.md:221-244)  
sudo apt install \
    qt5-default qt5-qmake qtbase5-dev qtbase5-dev-tools \
    qttools5-dev-tools libqt5gui5 libqt5core5a \
    libqt5webkit5-dev libqt5websockets5-dev \
    libprotobuf-dev protobuf-compiler
```

### Bitcoin Core
```bash
# Minimal
sudo apt-get install build-essential cmake pkgconf python3
sudo apt-get install libevent-dev libboost-dev
# GUI
sudo apt-get install qt6-base-dev qt6-tools-dev  
```

### Zcash
```bash
sudo apt-get install \
build-essential pkg-config libc6-dev m4 g++-multilib \
autoconf libtool ncurses-dev unzip git python3 python3-zmq \
zlib1g-dev curl bsdmainutils automake libtinfo5
```

## Cross-Platform Build Matrix

| Project | Mingw Cross-compile | Windows Native | Documentation |
|---------|-------------------|----------------|---------------|
| Zero | Not documented | Not documented | BUILD.md (Linux only) |
| Bitcoin | ✓ Full support | ✓ VS support | doc/build-windows.md |  
| Zcash | Not supported | Not supported | Linux only |
| Pirate | Not documented | Not documented | Experimental |
| Horizen | Not documented | Not documented | Limited docs |

## Depends System Details

### Zero (depends/README.md:1-28)
```bash
# Cross-compile targets
make HOST=x86_64-w64-mingw32 -j4    # Win64
make HOST=i686-w64-mingw32           # Win32  
make HOST=x86_64-apple-darwin11      # MacOSX
make HOST=arm-linux-gnueabihf        # ARM
```
**Note**: Zero includes Windows cross-compile targets but no build documentation

### Bitcoin Cross-compile hosts (standard)
- `i686-w64-mingw32` for Win32
- `x86_64-w64-mingw32` for Win64  
- `x86_64-apple-darwin11` for MacOSX
- `arm-linux-gnueabihf` for Linux ARM

## Testing Infrastructure Status

### Zero (BUILD.md:746-801)
**Unit Tests**: Broken - linking errors identified
```
undefined reference to `IsMine(CKeyStore const&, CScript const&)'
undefined reference to `zeronodeConfig'  
undefined reference to `RegisterZeroExclusiveRPCCommands(CRPCTable&)'
undefined reference to `bitdb'
```
**Functional Tests**: Working (qa/rpc-tests/)

### Bitcoin (BTESTS.md)
**Unit Tests**: Working (src/test/)  
**Functional Tests**: Working (test/functional/)
**Fuzz Tests**: Working (src/test/fuzz/)
**Framework**: Boost Test + Python

### Zcash (ZTESTS.md)  
**Unit Tests**: Working (src/test/)
**Functional Tests**: Working (qa/rpc-tests/)
**Privacy Tests**: zk-SNARK specific (src/zcash/)
**Framework**: Boost Test + Python

## Library Version Requirements

**Zero**: C++11 minimum (BUILD.md:133-183)
**Bitcoin**: Modern C++ (CMake managed)
**Zcash**: Modern C++ 
**Pirate**: Boost 1.83.0, Berkeley DB 6.2.32
**Horizen**: Boost 1.82.0, Berkeley DB 6.2.23

## Build System Architecture

| Project | Primary | Config | Make | Depends |
|---------|---------|--------|------|---------|
| Zero | Autotools | ./configure | make | Custom /depends |
| Bitcoin | CMake | cmake -B | cmake --build | Toolchain files |
| Zcash | Custom | zcutil scripts | make | Custom system |
| Pirate | Inherited | Komodo/Zcash | make | Inherited |
| Horizen | Inherited | Zcash-based | make | Custom /depends |