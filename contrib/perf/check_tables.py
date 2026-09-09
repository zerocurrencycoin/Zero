#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Flag tables too small to earn the form, and files carrying too many.

Two rules, both from docs/STRUCTURE.md:

  size    A table needs at least 2 data rows and rows x columns >= 9. One row
          is a sentence; two rows over two columns is a phrase. Two rows over
          five columns is a real comparison and passes.

  count   At most 10 tables per file. This is a ceiling, not a target: a file
          at ten can still be badly decomposed.

Neither rule judges content, so both under-report. A table can pass on size
and still be an enumeration of components listed elsewhere.

  check_tables.py [--max-per-file N] [paths...]
  check_tables.py --self-test

Exit: 0 clean, 1 findings, 2 usage error.
"""
import os
import sys

MIN_ROWS = 2
MIN_CELLS = 9
MAX_PER_FILE = 10


def tables(path):
    """Yield (line_no, data_rows, columns) for each table in PATH."""
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return
    prev = False
    for i, line in enumerate(lines):
        cur = line.lstrip().startswith("|")
        if cur and not prev:
            j, n = i, 0
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                n += 1
                j += 1
            cols = len(line.strip().strip("|").split("|"))
            # A separator row (|---|---|) means line 1 was a header; without
            # one this is a continuation block of a table interrupted by prose,
            # and every line is data. Subtracting a header that is not there
            # reported real registry rows as one-row tables.
            has_header = (i + 1 < len(lines)
                          and set(lines[i + 1].replace("|", "").strip())
                          <= set("-: ")
                          and lines[i + 1].lstrip().startswith("|"))
            yield (i + 1, n - 2 if has_header else n, cols)
        prev = cur


def _docs(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, _d, files in os.walk(p):
                out += [os.path.join(root, f) for f in files
                        if f.endswith(".md") and ".prev-" not in f]
        elif p.endswith(".md") and ".prev-" not in p:
            out.append(p)
    return sorted(out)


def scan(files, max_per_file=MAX_PER_FILE):
    bad = []
    for f in files:
        found = list(tables(f))
        if len(found) > max_per_file:
            bad.append("%s: %d tables, limit %d"
                       % (f, len(found), max_per_file))
        for line, rows, cols in found:
            if rows < MIN_ROWS or rows * cols < MIN_CELLS:
                bad.append("%s:%d: table too small: %d rows x %d cols"
                           % (f, line, rows, cols))
    return bad


def main(argv):
    if "--self-test" in argv:
        return self_test()
    mx = MAX_PER_FILE
    if "--max-per-file" in argv:
        i = argv.index("--max-per-file")
        try:
            mx = int(argv[i + 1])
        except (IndexError, ValueError):
            print("usage: --max-per-file N", file=sys.stderr)
            return 2
        del argv[i:i + 2]
    bad = scan(_docs(argv[1:] or ["contrib/perf"]), mx)
    for b in bad:
        print(b)
    return 1 if bad else 0


def self_test():
    import tempfile
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    with tempfile.TemporaryDirectory() as td:
        big = os.path.join(td, "big.md")
        # 3 rows x 4 cols = 12 cells: passes both rules.
        open(big, "w").write(
            "| a | b | c | d |\n|---|---|---|---|\n"
            + "| 1 | 2 | 3 | 4 |\n" * 3)
        check(not scan([big]), "3x4 table passes")

        one = os.path.join(td, "one.md")
        open(one, "w").write("| a | b |\n|---|---|\n| 1 | 2 |\n")
        check(scan([one]), "1-row table is reported")

        two2 = os.path.join(td, "two2.md")
        open(two2, "w").write("| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n")
        check(scan([two2]), "2x2 table (4 cells) is reported")

        two5 = os.path.join(td, "two5.md")
        open(two5, "w").write(
            "| a | b | c | d | e |\n|---|---|---|---|---|\n"
            "| 1 | 2 | 3 | 4 | 5 |\n| 6 | 7 | 8 | 9 | 0 |\n")
        check(not scan([two5]), "2x5 table (10 cells) passes -- a real A/B")

        # A continuation block: rows with no header, from a table split by
        # prose. Every line is data, so 3 rows x 7 cols must pass.
        cont = os.path.join(td, "cont.md")
        open(cont, "w").write(
            "| a | b | c | d | e | f | g |\n" * 3)
        check(not scan([cont]),
              "headerless continuation block counts every line as data")

        many = os.path.join(td, "many.md")
        open(many, "w").write(
            ("| a | b | c | d |\n|---|---|---|---|\n"
             + "| 1 | 2 | 3 | 4 |\n" * 3 + "\ntext\n\n") * 11)
        hits = scan([many])
        check(any("11 tables" in h for h in hits), "per-file ceiling is reported")
        check(not scan([many], max_per_file=99), "--max-per-file raises the ceiling")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
