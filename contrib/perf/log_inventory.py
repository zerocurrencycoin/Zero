#!/usr/bin/env python3
"""Inventory every logging call site in src/, as TSV.

PLAN.md M1. Produces data for the M2 review; makes no judgement about whether
a level or category is correct.

Columns: file, line, construct, category, gated, func, text

  construct  LogPrintf | LogPrint | error | LogPrintfZ ... (as written)
  category   the -debug category for LogPrint("cat", ...), else empty
  gated      yes if the site only emits when a -debug category is enabled
  func       enclosing function, best-effort from the preceding definition
  text       the format string, truncated, tabs/newlines escaped

Vendored trees (snark, univalue, leveldb, secp256k1, crc32c) are excluded:
they are inherited code this project does not own.

Usage:
    ./log_inventory.py [--src DIR] [--out FILE]
    ./log_inventory.py --summary      # counts only, no TSV
"""

import argparse
import os
import re
import sys

EXCLUDE_DIRS = {"snark", "univalue", "leveldb", "secp256k1", "crc32c", "obj"}
EXTS = (".cpp", ".h", ".hpp", ".cc")

# LogPrintf(...) / LogPrint("cat", ...) / error(...) and Z variants.
CALL = re.compile(r'\b(LogPrint[A-Za-z]*|error)\s*\(')
# First string literal after the opening paren.
FIRST_STR = re.compile(r'\s*"((?:[^"\\]|\\.)*)"')
# Best-effort function definition: a line starting at column 0 with a name(
FUNC_DEF = re.compile(r'^[A-Za-z_][A-Za-z0-9_:<>,\s\*&~]*\b([A-Za-z_~][A-Za-z0-9_]*)\s*\(')


def iter_sources(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in sorted(filenames):
            if fn.endswith(EXTS):
                yield os.path.join(dirpath, fn)


def escape(s, limit=160):
    s = s.replace("\\n", " ").replace("\t", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def scan(path, root):
    """Yield one record per logging call site."""
    try:
        with open(path, "r", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as exc:
        print(f"warn: {path}: {exc}", file=sys.stderr)
        return

    rel = os.path.relpath(path, root)
    func = ""
    for i, line in enumerate(lines, 1):
        m = FUNC_DEF.match(line)
        if m and not line.lstrip().startswith(("//", "*", "#")):
            func = m.group(1)

        for call in CALL.finditer(line):
            construct = call.group(1)
            rest = line[call.end():]
            sm = FIRST_STR.match(rest)
            first = sm.group(1) if sm else ""

            # LogPrint's first argument is the -debug category; everything
            # else emits unconditionally. A category with no letters (e.g. a
            # variable) is recorded as unknown rather than guessed.
            if construct == "LogPrint" and sm:
                category, gated = first, "yes"
                tm = FIRST_STR.match(rest[sm.end():].lstrip().lstrip(","))
                text = tm.group(1) if tm else ""
            elif construct == "LogPrint":
                category, gated, text = "?", "yes", ""
            else:
                category, gated, text = "", "no", first

            yield (rel, i, construct, category, gated, func, escape(text))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_src = os.path.normpath(os.path.join(here, "..", "..", "src"))

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=default_src, help="source root (default: repo src/)")
    ap.add_argument("--out", help="write TSV here (default: stdout)")
    ap.add_argument("--summary", action="store_true", help="print counts only")
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        sys.exit(f"error: no such directory: {args.src}")

    rows = []
    for path in iter_sources(args.src):
        rows.extend(scan(path, args.src))

    if args.summary:
        by_construct, by_category, by_file = {}, {}, {}
        for rel, _, construct, category, gated, _, _ in rows:
            by_construct[construct] = by_construct.get(construct, 0) + 1
            if gated == "yes":
                by_category[category] = by_category.get(category, 0) + 1
            else:
                by_file[rel] = by_file.get(rel, 0) + 1

        gated = sum(1 for r in rows if r[4] == "yes")
        print(f"call sites      {len(rows)}")
        print(f"  gated         {gated}")
        print(f"  always-on     {len(rows) - gated}")
        print(f"  categories    {len(by_category)}")
        print("\nby construct")
        for k, v in sorted(by_construct.items(), key=lambda kv: -kv[1]):
            print(f"  {v:5d}  {k}")
        print("\ntop categories")
        for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])[:12]:
            print(f"  {v:5d}  {k}")
        print("\ntop files by always-on sites")
        for k, v in sorted(by_file.items(), key=lambda kv: -kv[1])[:12]:
            print(f"  {v:5d}  {k}")
        return

    out = open(args.out, "w") if args.out else sys.stdout
    try:
        print("file\tline\tconstruct\tcategory\tgated\tfunc\ttext", file=out)
        for row in rows:
            print("\t".join(str(c) for c in row), file=out)
    finally:
        if args.out:
            out.close()
            print(f"{len(rows)} call sites -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
