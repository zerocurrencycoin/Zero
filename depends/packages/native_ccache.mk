package=native_ccache
$(package)_version=4.12.2
$(package)_download_path=https://github.com/ccache/ccache/releases/download/v$($(package)_version)/
$(package)_file_name=ccache-$($(package)_version).tar.gz
$(package)_sha256_hash=2a087efb66b62d4c66d4eb276748bbfa797ff3bde20adf44c53e5a8b9f3679af

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
