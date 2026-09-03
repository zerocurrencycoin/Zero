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
$(package)_dependencies=

# Three ways to select uniblake, in precedence order. The default tracks the
# latest local checkout rather than a pin, because this tree and uniblake move
# together: pinning during co-development means tag, push, re-hash and edit two
# lines for every experiment.
#
#   1. UNIBLAKE_SRC=/path   an explicit checkout
#   2. UNIBLAKE_COMMIT=<sha> a pinned tarball, fetched and SHA-256 verified
#      (with UNIBLAKE_SHA256=<hash>); for CI and release builds
#   3. neither              the first checkout found next to this tree
#
# Case 3 is what makes a plain `./zcutil/build.sh` work with no setup. It looks
# beside this tree first, so a sibling clone is found without configuration,
# then falls back to the historical location.
#
# The version stamp carries the checkout's HEAD, so a uniblake commit changes
# the build id and depends rebuilds on its own -- no manual cache clearing. A
# dirty tree reads -dirty, so uncommitted work is never mistaken for committed.
#
# A pin, if used, must be at or after the commit renaming uniblake's output
# knob to UB_BUILD. Earlier commits spell it `BUILD ?= build`, the build
# triplet this tree exports as BUILD wins, the archive lands in ./<triplet>/,
# and the build step's `test -f build/libuniblake.a` catches it.
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

endif

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
