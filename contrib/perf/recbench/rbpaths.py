#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""
RecBench paths. Every location RecBench reads or writes resolves through here.

Two roots, deliberately separate, because they move independently:

  RB_ROOT      RecBench's own files -- code, projects.json, the salt. Always
               the directory holding this module, so moving recbench/ anywhere,
               including out of this repository, changes nothing here.

  PROJECT_ROOT The tree being measured. Selected by name from projects.json,
               so one RecBench serves Zero400, ZeroPerf, zerowallet, uniblake
               and any other target without a module edit.

Design decisions, alternatives weighed and identifiers rejected: RecBench.md.

Environment:

  RB_PROJECT       project name from projects.json (default: its "default")
  RB_PROJECTS      projects.json location (default: RB_ROOT/projects.json)
  RB_PROJECT_ROOT  override the selected project's root
  RB_STORE         override the store directory
  RB_SALT          salt file (default: RB_ROOT/../.host_salt)
  RB_RUN_LABEL     free-text label for a set of runs
  RB_BINARY, RB_BUILD_HEADER, RB_CONFIG_HEADER   override one bound path
"""
import json
import os

RB_ROOT = os.path.dirname(os.path.abspath(__file__))


def _projects():
    path = os.environ.get("RB_PROJECTS") or os.path.join(RB_ROOT, "projects.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def project_name():
    cfg = _projects()
    return os.environ.get("RB_PROJECT") or cfg.get("default") or ""


def _project():
    return (_projects().get("projects") or {}).get(project_name()) or {}


def _abs(base, rel):
    """Resolve REL against BASE. '~' and absolute paths are honoured, so a
    project may live anywhere rather than only under this tree."""
    rel = os.path.expanduser(rel)
    if os.path.isabs(rel):
        return os.path.abspath(rel)
    return os.path.abspath(os.path.join(base, rel))


def project_root():
    env = os.environ.get("RB_PROJECT_ROOT")
    if env:
        return _abs(os.getcwd(), env)
    rel = _project().get("root")
    return _abs(RB_ROOT, rel) if rel else None


def store_dir():
    """Where ledgers live. Gitignored: results are local working data."""
    env = os.environ.get("RB_STORE")
    if env:
        return _abs(os.getcwd(), env)
    root, rel = project_root(), _project().get("store")
    return _abs(root, rel) if (root and rel) else None


def salt_path():
    env = os.environ.get("RB_SALT")
    if env:
        return _abs(os.getcwd(), env)
    return os.path.join(RB_ROOT, "..", ".host_salt")


def rb_file(*parts):
    """A file belonging to RecBench itself."""
    return os.path.join(RB_ROOT, *parts)


def _bound(key, env):
    """A path the project binds. None when unbound: the caller records the
    field as unknown rather than reading a plausible wrong file."""
    v = os.environ.get(env)
    if v:
        return _abs(os.getcwd(), v)
    rel = (_project().get("paths") or {}).get(key)
    root = project_root()
    return _abs(root, rel) if (rel and root) else None


def target_binary():
    return _bound("binary", "RB_BINARY")


def build_header():
    return _bound("build_header", "RB_BUILD_HEADER")


def config_header():
    return _bound("config_header", "RB_CONFIG_HEADER")


def self_test():
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  ok   " if cond else "  FAIL ") + msg)
        ok = ok and cond

    def with_env(**kw):
        old = {k: os.environ.get(k) for k in kw}
        for k, v in kw.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return old

    def restore(old):
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    check(os.path.isdir(RB_ROOT), "RB_ROOT is a directory")
    check(os.path.isfile(rb_file("projects.json")), "projects.json under RB_ROOT")
    check(os.path.isfile(rb_file("features.json")), "features.json under RB_ROOT")
    check(project_name() != "", "a default project is selected")
    check(target_binary() is not None, "default project binds a binary")

    o = with_env(RB_STORE="/tmp/rb-selftest")
    check(store_dir() == "/tmp/rb-selftest", "RB_STORE overrides")
    restore(o)

    # A second project must resolve without touching a module, including one
    # whose root is outside this tree.
    o = with_env(RB_PROJECT="uniblake", RB_BINARY=None)
    r = project_root()
    check(r is not None and "uniblake" in r, "a second project resolves by name")
    check(config_header() is None, "an unbound path is None, not a guess")
    restore(o)

    o = with_env(RB_PROJECT="no-such-project")
    check(project_root() is None, "unknown project yields None, not a default")
    restore(o)

    print("self-test OK" if ok else "self-test FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(self_test() if "--self-test" in sys.argv else 0)
