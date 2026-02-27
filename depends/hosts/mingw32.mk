mingw32_CC=x86_64-w64-mingw32.static-gcc
mingw32_CXX=x86_64-w64-mingw32.static-g++
mingw32_AR=x86_64-w64-mingw32.static-ar
mingw32_RANLIB=x86_64-w64-mingw32.static-ranlib
mingw32_STRIP=x86_64-w64-mingw32.static-strip
mingw32_NM=x86_64-w64-mingw32.static-nm
mingw32_WINDRES=x86_64-w64-mingw32.static-windres
mingw32_CFLAGS=-pipe -fopenmp -DPTW32_STATIC_LIB
mingw32_CXXFLAGS=$(mingw32_CFLAGS) -std=c++14

mingw32_release_CFLAGS=-O1
mingw32_release_CXXFLAGS=$(mingw32_release_CFLAGS)

mingw32_debug_CFLAGS=-O1
mingw32_debug_CXXFLAGS=$(mingw32_debug_CFLAGS)

mingw32_debug_CPPFLAGS=-D_GLIBCXX_DEBUG -D_GLIBCXX_DEBUG_PEDANTIC
