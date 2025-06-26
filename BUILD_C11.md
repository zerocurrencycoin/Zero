# Build Compatibility Notes

## GCC Version Compatibility

Zero node implementation now includes modifications to support building with newer GCC versions while maintaining compatibility with the older Boost 1.70.0 library.

### Changes Made

1. **Modified `depends/packages/boost.mk`**:
   - Added compiler flags: `-Wno-nonnull -Wno-unused-parameter -Wno-implicit-fallthrough`
   - These flags suppress warnings causing failures with GCC 13+, which is appearantly safe and does not affect functionality

2. **Modified `zcutil/build.sh`**:
   - Selects GCC-11 when available
   - Falls back to default GCC if GCC-11 not installed


### Alternative
Install GCC-11:
```bash
sudo apt-get install gcc-11 g++-11
```

Select specific compilers:
```bash
CC=gcc-11 CXX=g++-11 ./zcutil/build.sh
```


