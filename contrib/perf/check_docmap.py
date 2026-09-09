#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Every tracked .md under contrib/perf must have a row in the documentation map.

The map is the last section of README.md. A document with no inclusion rule accretes:
nobody can say what does not belong in it, so everything does. This set reached
43 files that way, five of them about the set itself.

Two directions are checked:

  missing   a tracked .md with no row -> it has no inclusion rule
  stale     a row naming a path that no longer exists -> the map lies

A row may name a file (`Perf.md`), a directory (`equ/`, `mine/*.md`) or several
comma-separated files. Matching is by basename or by directory prefix.

  check_docmap.py [root]
  check_docmap.py --self-test

Exit: 0 clean, 1 findings, 2 usage error.
"""
import os
import re
import sys

MAP_DOC = "README.md"
SECTION = "## Documentation map"


def map_rows(root):
    """Return the raw text of the placement table in MAP_DOC."""
    path = os.path.join(root, MAP_DOC)
    try:
        s = open(path, encoding="utf-8").read()
    except OSError:
        return ""
    i = s.find(SECTION)
    if i < 0:
        return ""
    j = s.find("\n## ", i + len(SECTION))
    return s[i:j if j > 0 else len(s)]


def docs(root):
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs
                   if d not in (".git", "test-logs", "__pycache__", "archives")]
        for f in files:
            if f.endswith(".md") and ".prev-" not in f:
                out.append(os.path.relpath(os.path.join(base, f), root))
    return sorted(out)


def covered(rel, section):
    """True if a row names REL by basename, or by a directory wildcard row.

    A directory only counts when the map names it as a wildcard -- `equ/`,
    `keep/*.md`, `mine/*.md`. Matching a bare `docs/` substring would let any
    row mentioning `docs/POLICY.md` cover every future file in docs/, which is
    the accretion this check exists to stop.
    """
    for form in ("`%s`" % rel, "`%s`" % os.path.basename(rel)):
        if form in section:
            return True
    d = os.path.dirname(rel)
    while d:
        for form in ("`%s/`" % d, "`%s/*.md`" % d):
            if form in section:
                return True
        d = os.path.dirname(d)
    return False


def scan(root):
    section = map_rows(root)
    bad = []
    if not section:
        return ["%s: placement map %s not found" % (root, MAP_DOC)]
    for rel in docs(root):
        if not covered(rel, section):
            bad.append("%s: no row in %s %s" % (rel, MAP_DOC, SECTION))
    # stale: a backticked *.md in the table naming a file that is gone
    present = {os.path.basename(d) for d in docs(root)}
    for name in sorted(set(re.findall(r"`([A-Za-z0-9_/.-]+\.md)`", section))):
        if os.path.basename(name) not in present:
            bad.append("%s %s: row names missing file %s"
                       % (MAP_DOC, SECTION, name))
    return bad


def self_test():
    import tempfile
    ok = True

    def build(td, section, files):
        open(os.path.join(td, MAP_DOC), "w", encoding="utf-8").write(
            SECTION + "\n\n| `README.md` | map | -- |\n" + section)
        for f in files:
            p = os.path.join(td, f)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write("x\n")

    with tempfile.TemporaryDirectory() as td:
        build(td, "| `A.md` | owns | not |\n", ["A.md"])
        ok &= scan(td) == []
    with tempfile.TemporaryDirectory() as td:  # missing row
        build(td, "| `A.md` | owns | not |\n", ["A.md", "B.md"])
        ok &= any("B.md" in x and "no row" in x for x in scan(td))
    with tempfile.TemporaryDirectory() as td:  # stale row
        build(td, "| `A.md` | owns | not |\n| `Gone.md` | owns | not |\n", ["A.md"])
        ok &= any("Gone.md" in x and "missing file" in x for x in scan(td))
    with tempfile.TemporaryDirectory() as td:  # directory row covers children
        build(td, "| `equ/` | owns | not |\n", ["equ/X.md"])
        ok &= scan(td) == []
    with tempfile.TemporaryDirectory() as td:  # no map at all
        open(os.path.join(td, "X.md"), "w", encoding="utf-8").write("x\n")
        ok &= scan(td) != []
    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    root = argv[1] if len(argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    bad = scan(root)
    for b in bad:
        print(b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
