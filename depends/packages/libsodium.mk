# ZeroPerf: libsodium 1.0.22 (released 2026-04-08). Zero400 stays on 1.0.21.
#
# The previous pin cited zerowallet, whose own build script cited this file --
# circular, with no technical reason on either side. zerowallet uses
# crypto_secretbox / sha256 / randombytes only and reaches the node over RPC,
# sharing no ABI with it, so the two need not match.
#
# Verified equivalent before switching: blake2b and ed25519 differ only by
# LCOV_EXCL_LINE comments between 1.0.21 and 1.0.22, and the blake2b compress
# kernel compiles to byte-identical assembly. Same gtest results, including the
# same pre-existing WalletTests failure. See contrib/perf/docs/SODIUM_SURVEY.md.
package=libsodium
$(package)_version=1.0.22
$(package)_download_path=https://github.com/jedisct1/libsodium/releases/download/$($(package)_version)-RELEASE/
$(package)_file_name=$(package)-$($(package)_version).tar.gz
$(package)_sha256_hash=adbdd8f16149e81ac6078a03aca6fc03b592b89ef7b5ed83841c086191be3349
$(package)_dependencies=
$(package)_config_opts=
$(package)_cflags_release=-O3

define $(package)_preprocess_cmds
  cd $($(package)_build_subdir); ./autogen.sh
endef

define $(package)_config_cmds
  $($(package)_autoconf) --enable-static --disable-shared
endef

define $(package)_build_cmds
  $(MAKE)
endef

define $(package)_stage_cmds
  $(MAKE) DESTDIR=$($(package)_staging_dir) install
endef
