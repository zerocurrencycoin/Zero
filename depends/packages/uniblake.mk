# uniblake: built from a local checkout, not a pinned tarball.
#
# --- how depends drives a package ---------------------------------------
#
# Six ordered steps, each guarded by a stamp file in the build directory:
#
#   .stamp_fetched  .stamp_extracted  .stamp_preprocessed
#   .stamp_configured  .stamp_built  .stamp_staged
#
# The dependencies between them are ORDER-ONLY (`|` in funcs.mk). Make will
# not rerun a step whose stamp exists, regardless of whether that step
# produced anything. A stamp is a claim, not evidence.
#
# The build directory is named <version>-<build_id>, where build_id hashes the
# recipe files and the version. Editing this file changes the id and creates a
# fresh directory; deleting the directory without changing the recipe recreates
# the same name, so any stamp written by a previous failed run applies again.
#
# --- how to debug a failure here ----------------------------------------
#
# The log tells you which step ran by what it echoes: "Extracting uniblake...",
# "Building uniblake...", "Staging uniblake...". A missing line means the step
# was SKIPPED because its stamp existed, not that it succeeded quietly.
#
#   cp: cannot stat 'build/libuniblake.a'   -- staging ran, build did not, or
#                                              build ran and produced nothing
#
# Look in the build directory:
#
#   D=depends/work/build/$HOST/uniblake/*/
#   ls -a $D            # Makefile, include, src, and which stamps exist
#   ls $D/build         # the objects and the archive, if the build worked
#
# Then remove the specific stamp rather than the whole tree, so the step reruns
# without discarding the rest:
#
#   rm $D/.stamp_built && make -C depends uniblake HOST=$HOST
#
# --- two failures this recipe has already had ---------------------------
#
# 1. extract_cmds copied into $(package)_extract_dir. depends has already cd'd
#    there, so that nested a second copy one level down and the build found no
#    Makefile. Copy into `.`.
#
# 2. depends names the compiler $(HOST)-gcc. That exists for a cross build and
#    not for a native one: on Ubuntu x86_64-pc-linux-gnu-gcc is absent and gcc
#    is what there is. Autotools packages never notice, because configure
#    probes and falls back by itself. uniblake has no configure step, so it ran
#    a compiler that was not there, produced nothing, and depends stamped the
#    step as built -- leaving .stamp_built beside an empty directory and a
#    staging error that named the wrong step.
#
# Both were silent. Hence the `test -f` at the end of build_cmds: a build that
# produces no library must fail at the build step, where the message is true.
#
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
#
# UB_BUILD is uniblake's output directory. It is passed explicitly rather than
# left to default because zcutil/build-native.sh puts BUILD -- the build triplet
# -- in the environment for depends, and uniblake once spelled this knob `BUILD
# ?= build`: the inherited triplet won, the archive landed in ./<triplet>/, and
# this recipe staged an empty prefix without erroring. uniblake renamed the knob
# to UB_BUILD to end that collision, and rejects a command-line BUILD outright.
#
# Naming it here keeps the staged path a property of this recipe rather than of
# whatever default the pinned uniblake happens to carry.
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
