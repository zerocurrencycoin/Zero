# Build Compatibility Notes

## GCC Version Compatibility

This Zero node implementation includes modifications to support building with newer GCC versions while maintaining compatibility with the older Boost 1.70.0 library.

### Changes Made

1. **Modified `depends/packages/boost.mk`**:
   - Added compiler flags: `-Wno-nonnull -Wno-unused-parameter -Wno-implicit-fallthrough`
   - These flags suppress warnings that cause build failures with GCC 13+

2. **Modified `zcutil/build.sh`**:
   - Automatically prefers GCC-11 when available
   - Falls back to default GCC if GCC-11 not installed
   - Exports CC and CXX environment variables

### Recommended Setup

**⚠️ IMPORTANT:** For best compatibility, install GCC-11:
```bash
sudo apt-get install gcc-11 g++-11
```

The build script will automatically detect and warn if GCC-11 is not available. While the build may work with newer GCC versions, GCC-11 provides the most reliable compilation experience with the older Boost 1.70.0 library.

### Manual Override

To use specific compilers:
```bash
CC=gcc-11 CXX=g++-11 ./zcutil/build.sh
```

### Known Issues

- Boost 1.70.0 has compatibility issues with GCC 13+
- The added warning suppressions are safe and don't affect functionality
- This maintains full compatibility with older GCC versions

### Build Requirements

- 8GB RAM recommended
- GCC-11 preferred (automatically detected)
- All standard Zero dependencies installed