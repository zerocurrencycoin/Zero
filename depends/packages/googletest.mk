package=googletest
$(package)_version=1.16.0
$(package)_download_path=https://github.com/google/googletest/releases/download/v$($(package)_version)/
$(package)_file_name=$(package)-$($(package)_version).tar.gz
$(package)_sha256_hash=78c676fc63881529bf97bf9d45948d905a66833fbfa5318ea2cd7478cb98f399

define $(package)_set_vars
$(package)_cxxflags+=-std=c++11
$(package)_cxxflags_linux=-fPIC
$(package)_cxxflags_freebsd=-fPIC
endef

define $(package)_preprocess_cmds
  mkdir -p build
endef

define $(package)_config_cmds
  cd build && cmake .. -DCMAKE_INSTALL_PREFIX=$($(package)_staging_prefix_dir) \
    -DCMAKE_CXX_STANDARD=11 \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DBUILD_GMOCK=ON \
    -DBUILD_GTEST=ON
endef

define $(package)_build_cmds
  cd build && $(MAKE)
endef

define $(package)_stage_cmds
  cd build && $(MAKE) install
endef
