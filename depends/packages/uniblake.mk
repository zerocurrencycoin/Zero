package=uniblake
$(package)_version=dev
$(package)_dependencies=

# Built from a local checkout, not a pinned tarball. uniblake and this tree
# move together; a hash here means bumping two lines every time either does,
# and a tag that silently drifts out of step with what is actually built.
#
# UNIBLAKE_SRC selects the checkout. $(package)_version carries the source's
# HEAD so the build id changes when uniblake does and depends rebuilds on its
# own; a dirty tree gets -dirty, so uncommitted work is never mistaken for a
# committed state.
UNIBLAKE_SRC ?= $(HOME)/Work/ZK/uniblake
$(package)_version:=$(shell cd $(UNIBLAKE_SRC) 2>/dev/null && \
    printf '%s%s' "$$(git rev-parse --short HEAD 2>/dev/null || echo nogit)" \
                  "$$(git diff --quiet 2>/dev/null || echo -dirty)")

define $(package)_fetch_cmds
endef

# depends has already cd'd into the extract directory, so copy into `.`.
# Copying into $(package)_extract_dir instead nests a second copy inside it and
# the build step then finds no Makefile.
define $(package)_extract_cmds
  cp -R $(UNIBLAKE_SRC)/Makefile $(UNIBLAKE_SRC)/include $(UNIBLAKE_SRC)/src .
endef

# No autotools: a plain Makefile producing one static library and two headers.
# libsodium is uniblake's test oracle, not a dependency, so none is passed.
# depends names the compiler $(HOST)-gcc, which exists for a cross build and
# not for a native one: on Ubuntu x86_64-pc-linux-gnu-gcc is absent and gcc is
# what there is. Packages with autotools do not notice because configure falls
# back on its own; uniblake has no configure step, so it would run a compiler
# that is not there, produce nothing, and let depends stamp the step as built.
#
# Resolve at build time rather than assuming either name.
define $(package)_build_cmds
  CC_REAL="$($(package)_cc)"; \
  command -v $$$$(echo $$$$CC_REAL | cut -d' ' -f1) >/dev/null 2>&1 || CC_REAL="$(default_build_CC)"; \
  AR_REAL="$($(package)_ar)"; \
  command -v $$$$AR_REAL >/dev/null 2>&1 || AR_REAL=ar; \
  $(MAKE) CC="$$$$CC_REAL" CFLAGS="$($(package)_cflags) $($(package)_cppflags)" AR="$$$$AR_REAL" && \
  test -f build/libuniblake.a
endef

define $(package)_stage_cmds
  mkdir -p $($(package)_staging_prefix_dir)/include/uniblake \
           $($(package)_staging_prefix_dir)/lib && \
  cp include/uniblake/uniblake.h include/uniblake/prefix.h \
     $($(package)_staging_prefix_dir)/include/uniblake/ && \
  cp build/libuniblake.a $($(package)_staging_prefix_dir)/lib/
endef
