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
