# uniblake: BLAKE2b for Equihash. Built from a local checkout by default, not
# a pinned tarball, because this tree and uniblake are developed together.
#
# Stamps: depends guards each step with .stamp_<step> in the build dir and its
# ordering is order-only, so a step whose stamp exists is skipped whether or not
# it produced anything -- which is why both bugs noted at the build step below
# were silent. To rerun one step, delete its stamp rather than the tree:
#
#   D=depends/work/build/$HOST/uniblake/*/
#   rm $D/.stamp_built && make -C depends uniblake HOST=$HOST
#
# The build dir is <version>-<build_id>; build_id hashes the recipe and version,
# so editing this file yields a fresh dir, while deleting the dir without
# editing reuses the old name and any stamp left by a failed run.
#
package=uniblake
$(package)_dependencies=

# Selection, in precedence order:
#
#   1. UNIBLAKE_SRC=/path                       explicit checkout
#   2. UNIBLAKE_COMMIT=<sha> UNIBLAKE_SHA256=<hash>  pinned tarball; CI/release
#   3. neither                                  first checkout found beside this tree
#
# Case 3 is what lets a plain ./zcutil/build.sh work unconfigured. The version
# stamp carries the checkout's HEAD (plus -dirty), so a uniblake commit changes
# the build id and depends rebuilds on its own; no cache clearing.
#
# A pin must be at or after the uniblake commit renaming its output knob to
# UB_BUILD -- see the build step below.
UNIBLAKE_COMMIT ?=
UNIBLAKE_SHA256 ?=

# Search order for an unconfigured checkout. First hit wins.
UNIBLAKE_SEARCH := $(CURDIR)/../../uniblake $(CURDIR)/../uniblake $(HOME)/Work/ZK/uniblake
UNIBLAKE_SRC ?= $(firstword $(foreach d,$(UNIBLAKE_SEARCH),$(if $(wildcard $(d)/Makefile),$(d))))

ifneq ($(UNIBLAKE_COMMIT),)

# Pinned: reproducible, no local checkout needed.
$(package)_version=$(UNIBLAKE_COMMIT)
$(package)_download_path=https://github.com/wkarshat/$(package)/archive/
$(package)_file_name=$(package)-$(UNIBLAKE_COMMIT).tar.gz
$(package)_download_file=$(UNIBLAKE_COMMIT).tar.gz
$(package)_git_commit=$(UNIBLAKE_COMMIT)
$(package)_sha256_hash=$(UNIBLAKE_SHA256)

else

ifeq ($(UNIBLAKE_SRC),)
$(error no uniblake checkout found. Looked for a Makefile in: $(UNIBLAKE_SEARCH). Clone uniblake beside this tree, pass UNIBLAKE_SRC=/path, or pin with UNIBLAKE_COMMIT=<sha> UNIBLAKE_SHA256=<hash>)
endif

# An explicit UNIBLAKE_SRC skips the search, so check it points at something
# before the extract step fails on a missing file with no useful message.
ifeq ($(wildcard $(UNIBLAKE_SRC)/Makefile),)
$(error UNIBLAKE_SRC=$(UNIBLAKE_SRC) has no Makefile -- not a uniblake checkout)
endif

$(package)_version:=$(shell cd $(UNIBLAKE_SRC) 2>/dev/null && \
    printf '%s%s' "$$(git rev-parse --short HEAD 2>/dev/null || echo nogit)" \
                  "$$(git diff --quiet 2>/dev/null || echo -dirty)")

define $(package)_fetch_cmds
endef

# depends has already cd'd into the extract dir; copy into `.`. Copying into
# $(package)_extract_dir nests a second copy inside it and the build finds no
# Makefile.
define $(package)_extract_cmds
  cp -R $(UNIBLAKE_SRC)/Makefile $(UNIBLAKE_SRC)/include $(UNIBLAKE_SRC)/src .
endef

endif

# No autotools: a plain Makefile producing one static library and two headers.
# libsodium is uniblake's test oracle, not a dependency, so none is passed.
#
# CC/AR are resolved at build time. depends names the compiler $(HOST)-gcc,
# which exists when cross-compiling and not natively (Ubuntu has gcc, not
# x86_64-pc-linux-gnu-gcc). Autotools packages absorb this in configure;
# uniblake has none, so an unresolved name would run nothing, produce nothing,
# and still be stamped as built.
#
# UB_BUILD is uniblake's output dir, passed explicitly: zcutil/build-native.sh
# exports BUILD (the build triplet) for depends, and uniblake once spelled this
# knob `BUILD ?= build`, so the triplet won and the archive landed in
# ./<triplet>/ while this recipe staged an empty prefix without erroring.
# uniblake renamed it to UB_BUILD and now rejects a command-line BUILD. Naming
# it here keeps the staged path a property of this recipe, not of whichever
# uniblake is pinned.
#
# The trailing `test -f` makes a build that produces no library fail at the
# build step, where the message is true.
define $(package)_build_cmds
  CC_REAL="$($(package)_cc)"; \
  command -v $$$$(echo $$$$CC_REAL | cut -d' ' -f1) >/dev/null 2>&1 || CC_REAL="$(default_build_CC)"; \
  AR_REAL="$($(package)_ar)"; \
  command -v $$$$AR_REAL >/dev/null 2>&1 || AR_REAL=ar; \
  $(MAKE) UB_BUILD=build CC="$$$$CC_REAL" CFLAGS="$($(package)_cflags) $($(package)_cppflags)" AR="$$$$AR_REAL" && \
  test -f build/libuniblake.a
endef

define $(package)_stage_cmds
  mkdir -p $($(package)_staging_prefix_dir)/include/uniblake \
           $($(package)_staging_prefix_dir)/lib && \
  cp include/uniblake/uniblake.h include/uniblake/prefix.h \
     $($(package)_staging_prefix_dir)/include/uniblake/ && \
  cp build/libuniblake.a $($(package)_staging_prefix_dir)/lib/
endef
