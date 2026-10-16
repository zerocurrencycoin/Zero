# Zero v4.0.0

Released 2026-03-21, tag `v4.0.0`. It follows the 3.3.1 line (`Ambrym`), whose last build is the v3.4.0 release for Ubuntu 24.04.

## Summary

Zero **v4.0.0** (`Gaua`) full node: build system refresh for Linux, macOS, and Windows, Python 3 RPC tests, documentation consolidation, and a wallet interface for the zeronode code.

## Build

- New build script layout: `zcutil/build.sh`, with `build-win.sh` aligned to it for MXE cross-builds on Linux.
- Build fixes for GCC 13 and later, including the Boost `PTHREAD_STACK_MIN` fix and path quoting in `depends`.
- Pinned dependencies:

| Package | Version |
|---------|---------|
| Boost | 1.88.0 |
| Berkeley DB | 6.2.32 |
| libsodium | 1.0.21 |
| libevent | 2.1.12 |
| OpenSSL | 1.1.1w |
| ZeroMQ | 4.3.5 |
| ccache (native) | 4.13.1 |
| GoogleTest | 1.16.0 |

## Tests

- RPC tests run on Python 3.
- Founders reward and transaction-size tests match the implementation; test framework and runner updates.

## Zeronodes and wallet

- Zeronode code reaches the wallet through one interface, with a stub when the wallet is unavailable, instead of using the wallet object directly.
- Zeronode budget, RPC, and validation error handling.

## Documentation

- Build documentation for Linux, macOS, and Windows in BUILD_ZERO.

## Downloads

Linux, macOS, and Windows archives are attached to the GitHub release `v4.0.0`.
