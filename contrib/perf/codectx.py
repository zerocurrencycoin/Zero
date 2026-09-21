#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Answer structural questions about C++ source that grep and awk get wrong.

Written after repeated failures in one session:

  - `awk 'NR<=N && /LOCK\\(cs_main\\)/ {l=NR}'` reports the nearest *textually
    preceding* match, which is routinely in a different function. It answered
    "LOCK at 706" for a call at line 795 in an unrelated function.
  - Multi-word phrases spanning a line break are invisible to line-oriented
    grep: "This is mostly\\n// redundant" was reported absent when present.
  - `awk -v f="file N"` with an unquoted pair silently treats "N" as a filename.

These are not grep bugs; they are the wrong tool for a question about scope.
This tool tracks brace depth and function extents.

  codectx.py enclosing FILE LINE            which function contains LINE
  codectx.py holds FILE LINE PATTERN        does PATTERN appear in LINE's
                                            enclosing function, before LINE
  codectx.py calls FILE SYMBOL              call sites with their enclosing
                                            function
  codectx.py phrase PATTERN [PATH...]       match across line breaks,
                                            comment-aware
  codectx.py --self-test

Exit: 0 found / true, 1 not found / false, 2 usage error.
"""
import os
import re
import sys

# A function definition at file scope: optional qualifiers, a name, an
# argument list, then an opening brace on the same or next line. Deliberately
# conservative -- it is better to miss an exotic declaration than to claim a
# wrong enclosing scope.
FUNC_RE = re.compile(
    r'^[A-Za-z_][\w:<>,\s\*&~]*?'      # return type / qualifiers
    r'\b([A-Za-z_~][\w:]*)\s*'          # function name (captured)
    r'\([^;]*?\)\s*'                    # argument list, not a declaration
    r'(?:const\s*)?(?:noexcept\s*)?'
    r'(?:\{|$)'
)


def functions(path):
    """Yield (name, start_line, end_line) for each file-scope function body.

    Brace-counted, so nested blocks and lambdas do not end a function early.
    Lines inside strings or comments can still miscount braces; that is
    accepted and is why `enclosing` reports its confidence.
    """
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    except OSError:
        return
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if (not stripped or stripped.startswith(("//", "*", "#", "}"))
                or line[0].isspace()):
            i += 1
            continue
        m = FUNC_RE.match(line)
        if not m:
            i += 1
            continue
        # Find the opening brace: same line, or the next non-blank one.
        j = i
        while j < n and "{" not in lines[j]:
            if ";" in lines[j]:       # a declaration, not a definition
                break
            j += 1
        if j >= n or ";" in lines[j] and "{" not in lines[j]:
            i += 1
            continue
        depth, k = 0, j
        started = False
        while k < n:
            depth += lines[k].count("{") - lines[k].count("}")
            if lines[k].count("{"):
                started = True
            if started and depth <= 0:
                break
            k += 1
        yield (m.group(1), i + 1, min(k + 1, n))
        i = k + 1


def enclosing(path, line):
    best = None
    for name, a, b in functions(path):
        if a <= line <= b and (best is None or a > best[1]):
            best = (name, a, b)
    return best


def holds(path, line, pattern):
    """Does PATTERN occur inside LINE's enclosing function, before LINE?"""
    fn = enclosing(path, line)
    if fn is None:
        return None, []
    name, a, b = fn
    rx = re.compile(pattern)
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    hits = [(i + 1, lines[i].strip())
            for i in range(a - 1, min(line, b))
            if rx.search(lines[i])]
    return (name, a, b), hits


def phrase(pattern, paths):
    """Match PATTERN against text with line breaks and comment markers folded.

    A phrase split across two comment lines is one phrase to a reader and two
    lines to grep. Collapse "\\n// " and "\\n * " to a space before matching,
    then map the offset back to a line number.
    """
    rx = re.compile(pattern, re.I)
    out = []
    for p in paths:
        try:
            raw = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        folded = re.sub(r'\n\s*(?://+|\*)?[ \t]*', ' ', raw)
        # offset map: index in folded -> line number in raw
        line_of, ln = [], 1
        i = 0
        while i < len(raw):
            if raw[i] == "\n":
                ln += 1
                j = i + 1
                while j < len(raw) and (raw[j] in " \t"
                                        or raw.startswith("//", j)
                                        or raw[j] == "*"):
                    if raw[j] == "\n":
                        break
                    j += 1
                line_of.append(ln)
                i = j
                continue
            line_of.append(ln)
            i += 1
        for m in rx.finditer(folded):
            idx = min(m.start(), len(line_of) - 1) if line_of else 0
            out.append((p, line_of[idx] if line_of else 1,
                        m.group(0)[:90]))
    return out


def self_test():
    import tempfile
    ok = True

    def check(cond, why):
        nonlocal ok
        if not cond:
            print("FAIL: " + why, file=sys.stderr)
            ok = False

    src = """#include <x>
bool alpha(int a)
{
    LOCK(cs_main);
    return a;
}

bool beta(int b)
{
    // no lock here
    return b;
}
"""
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "t.cpp")
        open(p, "w", encoding="utf-8").write(src)

        fns = {n: (a, b) for n, a, b in functions(p)}
        check("alpha" in fns and "beta" in fns, "both functions found")

        e = enclosing(p, 5)
        check(e and e[0] == "alpha", "line 5 is inside alpha, got %r" % (e,))
        e = enclosing(p, 10)
        check(e and e[0] == "beta", "line 10 is inside beta, got %r" % (e,))

        # The exact failure awk produced: a lock in an EARLIER function must
        # not be reported as covering a later one.
        fn, hits = holds(p, 10, r"LOCK\(cs_main\)")
        check(fn and fn[0] == "beta", "holds() resolves the right function")
        check(hits == [], "lock in alpha must NOT count for beta")

        fn, hits = holds(p, 5, r"LOCK\(cs_main\)")
        check(len(hits) == 1, "lock in alpha counts for alpha")

        # Phrase spanning a comment line break.
        p2 = os.path.join(td, "c.cpp")
        open(p2, "w", encoding="utf-8").write(
            "int f() {\n    // This is mostly\n    // redundant with x.\n}\n")
        check(phrase(r"mostly\s+redundant", [p2]), "phrase across line break")
        check(not phrase(r"mostly\s+irrelevant", [p2]), "absent phrase")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    mode = argv[1]
    try:
        if mode == "enclosing":
            path, line = argv[2], int(argv[3])
            e = enclosing(path, line)
            if not e:
                print("%s:%d: no enclosing function found" % (path, line))
                return 1
            print("%s:%d is inside %s() [lines %d-%d]" % (path, line, e[0], e[1], e[2]))
            return 0
        if mode == "holds":
            path, line, pat = argv[2], int(argv[3]), argv[4]
            fn, hits = holds(path, line, pat)
            if fn is None:
                print("%s:%d: no enclosing function" % (path, line))
                return 1
            print("%s:%d inside %s() [%d-%d]" % (path, line, fn[0], fn[1], fn[2]))
            if not hits:
                print("  NOT FOUND in this function before line %d: %s" % (line, pat))
                return 1
            for ln, txt in hits:
                print("  %d: %s" % (ln, txt))
            return 0
        if mode == "calls":
            path, sym = argv[2], argv[3]
            rx = re.compile(r'\b%s\s*\(' % re.escape(sym))
            lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
            found = False
            for i, l in enumerate(lines, 1):
                if rx.search(l):
                    e = enclosing(path, i)
                    print("%s:%d  in %s()  %s"
                          % (path, i, e[0] if e else "<file scope>", l.strip()[:80]))
                    found = True
            return 0 if found else 1
        if mode == "phrase":
            pat, paths = argv[2], argv[3:] or ["."]
            files = []
            for p in paths:
                if os.path.isdir(p):
                    for root, _d, fs in os.walk(p):
                        files += [os.path.join(root, f) for f in fs
                                  if f.endswith((".cpp", ".h", ".hpp", ".tcc", ".c"))]
                else:
                    files.append(p)
            hits = phrase(pat, files)
            for f, ln, txt in hits:
                print("%s:%d: %s" % (f, ln, txt))
            return 0 if hits else 1
    except (IndexError, ValueError):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    print("unknown mode: %s" % mode, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
