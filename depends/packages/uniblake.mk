package=uniblake
$(package)_version=0.1.1
$(package)_download_path=https://github.com/wkarshat/$(package)/archive/
$(package)_file_name=$(package)-$($(package)_git_commit).tar.gz
$(package)_download_file=$($(package)_git_commit).tar.gz
$(package)_sha256_hash=2a30a6b0e4a90920de1fab6e66f33925d0d11ce93e56903b488cddd72067cea6
$(package)_git_commit=5bf129e39e2ed5a43fe7c4271f4cd2ea140a2729
$(package)_dependencies=

# No autotools: a plain Makefile producing one static library and two headers.
# libsodium is the library's test oracle, not a dependency -- `make` builds
# the library alone and links nothing, so no SODIUM is passed here.
define $(package)_build_cmds
  $(MAKE) CC="$($(package)_cc)" CFLAGS="$($(package)_cflags) $($(package)_cppflags)" AR="$($(package)_ar)"
endef

define $(package)_stage_cmds
  mkdir -p $($(package)_staging_prefix_dir)/include/uniblake \
           $($(package)_staging_prefix_dir)/lib && \
  cp include/uniblake/uniblake.h include/uniblake/prefix.h \
     $($(package)_staging_prefix_dir)/include/uniblake/ && \
  cp build/libuniblake.a $($(package)_staging_prefix_dir)/lib/
endef
