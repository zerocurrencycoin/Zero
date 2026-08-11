#!/usr/bin/env bash
# Product/tree identity receipt. Not a compile, not --strict tests, not host setup.
# Host/setup: zcutil/check-setup.sh
# Default stdout: READY / NOT READY plus one line per step. Full dump: -v
# Dirty tracked files and non-allowlisted untracked fail READY (not a release tree).
#   zcutil/check-release.sh
#   zcutil/check-release.sh --exact
#   zcutil/check-release.sh --allow-dirty   # identity only; not a release claim
#   zcutil/check-release.sh -v
set -euo pipefail
ME="check-release"
# shellcheck disable=SC1091
. "$(dirname "${BASH_SOURCE[0]}")/fzero.sh"
cd "$REPO_ROOT"

RELEASE="v4.0.1"
EXPECT_REF=""
PIN_MODE="at-least"
ALLOW_DIRTY=0
NO_WRITE=0
LEVELS="tree,build"
STEP_TREE=""
STEP_PIN=""
STEP_DEP=""
STEP_CFG=""
STEP_BUILD=""

usage() {
  cat <<'EOF'
Usage: zcutil/check-release.sh [options]

Stdout is READY or NOT READY plus one line per step (tree, pin, build).
Full log: -v or .build/ready-latest.txt
Host/setup (python, cxx, params): zcutil/check-setup.sh

A dirty working tree is NOT READY. Allowlisted untracked only:
  contrib/linearize/*.(tgz|cfg*)  .build/
Use --allow-dirty for an identity receipt on a WIP tree (not a release claim).

  --release REF      product version on the receipt (default: v4.0.1)
  --expect REF       git object vs HEAD (default: --release tag)
  --at-least         HEAD may be the pin or a descendant (default)
  --exact            HEAD must equal the pin (tag day)
  --allow-dirty      do not fail on modified / untracked files
  --strict-git       no-op; clean tree is already the default
  --levels=LIST      tree,depends,configure,build
  -v, --verbose      print the full receipt
  --no-write         do not write .build/ready-*.txt
  -h, --help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --release) RELEASE="${2:?}"; shift 2 ;;
    --release=*) RELEASE="${1#--release=}"; shift ;;
    --expect) EXPECT_REF="${2:?}"; shift 2 ;;
    --expect=*) EXPECT_REF="${1#--expect=}"; shift ;;
    --at-least) PIN_MODE="at-least"; shift ;;
    --exact) PIN_MODE="exact"; shift ;;
    --allow-dirty) ALLOW_DIRTY=1; shift ;;
    --strict-git) shift ;;
    --levels=*) LEVELS="${1#--levels=}"; shift ;;
    --win)
      echo "check-release: --win is zcutil/check-setup.sh --win" >&2
      exit 2
      ;;
    -v|--verbose) RECEIPT_VERBOSE=1; shift ;;
    --write) NO_WRITE=0; shift ;;
    --no-write) NO_WRITE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

PIN_REF="${EXPECT_REF:-$RELEASE}"
has_level() { [[ ",$LEVELS," == *",$1,"* ]]; }

if has_level toolchain || has_level params; then
  echo "check-release: toolchain/params are zcutil/check-setup.sh" >&2
  exit 2
fi
if has_level compile; then
  LEVELS="$LEVELS,build"
fi

guess_build_host
ALLOW_UNTRACKED_RE='^(contrib/linearize/.*\.(tgz|cfg[0-9]*)|\.build/.*)$'
HEAD_SHORT=""
PIN_NOTE=""
TREE_NOTE=""
ZEROD_NOTE=""

receipt_init ready
receipt_log "=== ready $RECEIPT_UTC ==="
receipt_log "repo $REPO_ROOT"
receipt_log "cwd $(pwd)"
receipt_log "release $RELEASE"
receipt_log "pin $PIN_REF mode=$PIN_MODE"
receipt_log "levels $LEVELS"
receipt_log "HOST ${HOST:-unset}"

if has_level tree; then
  receipt_log "--- tree ---"
  git status -sb | receipt_cap
  git log -1 --oneline | receipt_cap
  HEAD_SHA="$(git rev-parse HEAD)"
  HEAD_SHORT="$(git rev-parse --short HEAD)"
  receipt_log "HEAD $HEAD_SHA"
  receipt_log "branch $(git rev-parse --abbrev-ref HEAD)"
  TREE_NOTE="$(git rev-parse --abbrev-ref HEAD)"
  if git rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1; then
    receipt_log "upstream $(git rev-parse --abbrev-ref '@{upstream}')"
    receipt_log "ahead_behind $(git rev-list --left-right --count '@{upstream}'...HEAD | tr '\t' ' ')"
  fi
  NMOD=0
  NUNTR=0
  dirty="$(git status --porcelain --untracked-files=all)"
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    code="${line:0:2}"
    path="${line:3}"
    if [[ "$code" == "??" ]]; then
      if [[ "$path" =~ $ALLOW_UNTRACKED_RE ]]; then
        receipt_log "untracked allowlisted: $path"
        continue
      fi
      receipt_log "untracked: $path"
      NUNTR=$((NUNTR + 1))
    else
      receipt_log "dirty tracked: $line"
      NMOD=$((NMOD + 1))
    fi
  done <<<"$dirty"
  if [[ "$NMOD" -gt 0 || "$NUNTR" -gt 0 ]]; then
    TREE_NOTE="$TREE_NOTE dirty ${NMOD} modified ${NUNTR} untracked"
  else
    TREE_NOTE="$TREE_NOTE clean"
  fi
  if [[ "$ALLOW_DIRTY" -eq 1 ]]; then
    if [[ "$NMOD" -gt 0 || "$NUNTR" -gt 0 ]]; then
      receipt_warn "dirty tree ignored (--allow-dirty): ${NMOD} modified, ${NUNTR} untracked"
      STEP_TREE="WARN  ${NMOD} modified, ${NUNTR} untracked (--allow-dirty)"
    else
      STEP_TREE="PASS  clean  $TREE_NOTE $HEAD_SHORT"
    fi
  else
    if [[ "$NMOD" -gt 0 || "$NUNTR" -gt 0 ]]; then
      receipt_fail "working tree dirty: ${NMOD} modified, ${NUNTR} untracked (not a release tree; --allow-dirty for identity-only)"
      STEP_TREE="FAIL  ${NMOD} modified, ${NUNTR} untracked"
    else
      STEP_TREE="PASS  clean  $(git rev-parse --abbrev-ref HEAD) $HEAD_SHORT"
    fi
  fi
  if [[ -n "${ZEROPERF:-}" ]]; then
    if [[ -d "$ZEROPERF/.git" ]] || [[ -f "$ZEROPERF/.git" ]]; then
      PERF_HEAD="$(git -C "$ZEROPERF" rev-parse HEAD)"
      receipt_log "zeroperf_head $PERF_HEAD $(git -C "$ZEROPERF" log -1 --format='%h %s')"
      if git cat-file -t "$PERF_HEAD" >/dev/null 2>&1; then
        MB="$(git merge-base HEAD "$PERF_HEAD")"
        receipt_log "merge-base $MB $(git log -1 --format='%h %s' "$MB")"
        receipt_log "--- unique vs merge-base ---"
        git log --oneline "$MB"..HEAD | receipt_cap
        if [[ -n "${EXPECT_MERGE_BASE:-}" ]]; then
          EXP_MB="$(git rev-parse --verify "${EXPECT_MERGE_BASE}^{commit}")"
          if [[ "$MB" == "$EXP_MB" ]]; then
            receipt_pass "merge-base matches EXPECT_MERGE_BASE"
          else
            receipt_fail "merge-base $MB != EXPECT_MERGE_BASE $EXP_MB"
          fi
        fi
      else
        receipt_warn "ZeroPerf HEAD $PERF_HEAD not in this object DB; fetch before merge-base"
      fi
    else
      receipt_fail "ZEROPERF set but not a git checkout: $ZEROPERF"
    fi
  else
    receipt_log "merge-base skipped (set ZEROPERF to a sibling checkout)"
  fi

  if ! WANT="$(git rev-parse --verify "${PIN_REF}^{commit}" 2>/dev/null)"; then
    receipt_fail "pin $PIN_REF is not a git object in this repo"
    PIN_NOTE="pin missing"
    STEP_PIN="FAIL  $PIN_REF not in this repo"
  else
    receipt_log "pin_sha $WANT"
    if [[ "$PIN_MODE" == "exact" ]]; then
      if [[ "$HEAD_SHA" == "$WANT" ]]; then
        receipt_pass "HEAD equals $PIN_REF"
        PIN_NOTE="exact $PIN_REF"
        STEP_PIN="PASS  exact $PIN_REF  HEAD $HEAD_SHORT"
      else
        receipt_fail "HEAD $HEAD_SHORT != $PIN_REF (use default --at-least if this line is ahead of the tag)"
        PIN_NOTE="exact miss"
        STEP_PIN="FAIL  HEAD $HEAD_SHORT != $PIN_REF"
      fi
    else
      if git merge-base --is-ancestor "$WANT" HEAD; then
        if [[ "$HEAD_SHA" == "$WANT" ]]; then
          receipt_pass "HEAD equals $PIN_REF"
          PIN_NOTE="at $PIN_REF"
          STEP_PIN="PASS  at $PIN_REF  HEAD $HEAD_SHORT"
        else
          receipt_warn "HEAD $HEAD_SHORT is ahead of $PIN_REF tag"
          receipt_pass "HEAD descendant of $PIN_REF"
          PIN_NOTE="ahead of $PIN_REF"
          STEP_PIN="PASS  $PIN_REF at-least  HEAD $HEAD_SHORT ahead of tag"
        fi
      else
        receipt_fail "HEAD is not $PIN_REF or a descendant"
        PIN_NOTE="not based on $PIN_REF"
        STEP_PIN="FAIL  HEAD $HEAD_SHORT not based on $PIN_REF"
      fi
    fi
  fi
fi

if has_level depends; then
  receipt_log "--- depends ---"
  SITE="$(depends_config_site)"
  receipt_log "HOST ${HOST:-unset}"
  receipt_log "config.site $SITE"
  if [[ -n "$HOST" && -f "$SITE" ]]; then
    receipt_pass "depends config.site"
    STEP_DEP="PASS  HOST $HOST"
  else
    receipt_fail "depends not built for HOST=${HOST:-?} (zcutil/build.sh always runs make -C depends)"
    STEP_DEP="FAIL  no config.site for HOST=${HOST:-?}"
  fi
fi

if has_level configure; then
  receipt_log "--- configure ---"
  if [[ -f "$REPO_ROOT/config.status" ]]; then
    receipt_pass "config.status present"
    STEP_CFG="PASS  config.status"
  else
    receipt_fail "config.status missing (configure not run)"
    STEP_CFG="FAIL  no config.status"
  fi
fi

if has_level build; then
  receipt_log "--- build ---"
  BUILD_OK=1
  if [[ -x "$REPO_ROOT/src/zerod" ]]; then
    ZMTIME="$(stat -f '%Sm' -t '%Y-%m-%d' src/zerod 2>/dev/null || stat -c '%y' src/zerod | cut -d' ' -f1)"
    receipt_log "zerod_mtime $(stat -f '%Sm' -t '%Y-%m-%dT%H:%M:%S' src/zerod 2>/dev/null || stat -c '%y' src/zerod)"
    receipt_log "zerod_sha256 $(shasum -a 256 src/zerod | awk '{print $1}')"
    src/zerod -version 2>/dev/null | head -1 | receipt_cap || true
    receipt_pass "src/zerod executable"
    ZEROD_NOTE="zerod $ZMTIME"
    if HEAD_CT="$(git log -1 --format=%ct 2>/dev/null)"; then
      Z_CT="$(stat -f %m src/zerod 2>/dev/null || stat -c %Y src/zerod)"
      if [[ -n "$Z_CT" && "$Z_CT" -lt "$HEAD_CT" ]]; then
        receipt_warn "zerod dated $ZMTIME is older than HEAD; rebuild before treating this as this commit"
        ZEROD_NOTE="zerod $ZMTIME older than HEAD"
      fi
    fi
  else
    receipt_fail "src/zerod missing (zcutil/build.sh / zcutil/build-release.sh)"
    ZEROD_NOTE="zerod missing"
    BUILD_OK=0
  fi
  if [[ -x "$REPO_ROOT/src/zero-cli" ]]; then
    receipt_log "zero-cli_sha256 $(shasum -a 256 src/zero-cli | awk '{print $1}')"
    receipt_pass "src/zero-cli executable"
  else
    receipt_fail "src/zero-cli missing"
    BUILD_OK=0
  fi
  if [[ -x "$REPO_ROOT/src/test/test_bitcoin" ]]; then
    receipt_pass "src/test/test_bitcoin executable"
  else
    receipt_warn "src/test/test_bitcoin missing (--disable-tests?)"
  fi
  if [[ "$BUILD_OK" -eq 0 ]]; then
    STEP_BUILD="FAIL  $ZEROD_NOTE"
  elif [[ "$ZEROD_NOTE" == *"older than HEAD"* ]]; then
    STEP_BUILD="WARN  $ZEROD_NOTE"
  else
    STEP_BUILD="PASS  $ZEROD_NOTE"
  fi
fi

if [[ "$CHECK_FAIL" -eq 0 ]]; then
  receipt_log "READY exit=0"
else
  receipt_log "NOT READY exit=1"
fi
receipt_commit

if [[ "$CHECK_FAIL" -eq 0 ]]; then
  echo "READY"
else
  echo "NOT READY"
fi
[[ -n "$STEP_TREE" ]] && echo "tree       $STEP_TREE"
[[ -n "$STEP_PIN" ]] && echo "pin        $STEP_PIN"
[[ -n "$STEP_DEP" ]] && echo "depends    $STEP_DEP"
[[ -n "$STEP_CFG" ]] && echo "configure  $STEP_CFG"
[[ -n "$STEP_BUILD" ]] && echo "build      $STEP_BUILD"
echo "receipt    $RECEIPT"

exit "$CHECK_FAIL"
