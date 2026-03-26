package=native_ccache
$(package)_version=4.13.1
$(package)_download_path=https://github.com/ccache/ccache/releases/download/v$($(package)_version)/
$(package)_file_name=ccache-$($(package)_version).tar.gz
$(package)_sha256_hash=e822547b0344c567c6f748f75d4da056c360e2196da12d213ec0caf39d72896d

define $(package)_preprocess_cmds
  mkdir -p build
endef

define $(package)_config_cmds
  cd build && cmake .. -DCMAKE_INSTALL_PREFIX=$($(package)_staging_prefix_dir) \
    -DDEPS=DOWNLOAD \
    -DREDIS_STORAGE_BACKEND=OFF \
    -DHTTP_STORAGE_BACKEND=OFF \
    -DENABLE_TESTING=OFF
endef

define $(package)_build_cmds
  cd build && $(MAKE)
endef

define $(package)_stage_cmds
  cd build && $(MAKE) install
endef

define $(package)_postprocess_cmds
  rm -rf lib include
endef
