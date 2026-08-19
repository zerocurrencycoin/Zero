#!/usr/bin/env python3
"""Flag non-ASCII characters that AGENTS.md bans from documents and code.

AGENTS.md: no emojis or decorative Unicode in any document except README.md;
use ASCII equivalents -- `--` not em-dash, `->` not arrow, `"` not curly
quotes, `...` not ellipsis. Nothing enforced this, so violations accumulated.

Usage (from repo root):
  contrib/perf/check-unicode.py            # report; exit 1 if violations
  contrib/perf/check-unicode.py --fix      # rewrite the safe substitutions
  contrib/perf/check-unicode.py --all      # include tolerated characters
  contrib/perf/check-unicode.py PATH...    # limit to given paths

Exit status: 0 clean, 1 violations found, 2 usage error.
"""
import re
import subprocess
import sys
import unicodedata

# Substitutions applied by --fix. Value is the ASCII replacement.
REPLACE = {
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2192": "->",   # rightwards arrow
    "\u2190": "<-",   # leftwards arrow
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u2026": "...",  # ellipsis
    "\u00b7": "-",    # middle dot
    "\u2022": "-",    # bullet
    "\u00d7": "x",    # multiplication sign
    "\u2248": "~",    # almost equal to
    "\u00a0": " ",    # no-break space
    "\u202f": " ",    # narrow no-break space
}

# Reported but never auto-fixed: no safe ASCII equivalent.
FLAG_ONLY_RANGES = (
    (0x1F300, 0x1FAFF),  # emoji and pictographs
    (0x2600, 0x27BF),    # misc symbols, dingbats (includes U+2705)
    (0xFE00, 0xFE0F),    # variation selectors
)

# Tolerated by default: conventional in this tree, not decorative.
TOLERATED = {
    "\u00a7",  # section sign (SS) -- used as `SS 0.14` style section refs throughout
}

# Vendored or captured-data paths: not ours to normalize.
SKIP_PATH = re.compile(
    r"^(src/(leveldb|univalue|secp256k1|snark|crypto/ctaes)/"
    r"|depends/"
    r"|contrib/perf/(mine|groth16-batch-poc)/"
    r"|contrib/perf/dis-nodes\.txt$"      # captured chat text, keep verbatim
    r"|share/genbuild\.sh$)"
)
CHECK_EXT = re.compile(r"\.(md|cpp|h|hpp|py|sh|txt|conf|csv|include|ac|am)$")

# AGENTS.md exempts README.md from the no-decorative-Unicode rule.
EXEMPT = re.compile(r"(^|/)README\.md$")


def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    if out.returncode:
        sys.exit("not a git repo (run from repo root)")
    return out.stdout.split()


def flag_only(ch):
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in FLAG_ONLY_RANGES)


def scan(path, show_all):
    try:
        text = open(path, encoding="utf-8").read()
    except (UnicodeDecodeError, OSError):
        return []
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for ch in line:
            if ord(ch) < 128:
                continue
            if ch in TOLERATED and not show_all:
                continue
            kind = "replace" if ch in REPLACE else ("flag" if flag_only(ch) else "other")
            hits.append((lineno, ch, kind))
    return hits


def main(argv):
    show_all = "--all" in argv
    do_fix = "--fix" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        paths = [f for f in tracked_files()
                 if CHECK_EXT.search(f) and not SKIP_PATH.match(f)]

    violations = 0
    fixed_files = 0
    for path in sorted(paths):
        exempt = bool(EXEMPT.search(path))
        hits = scan(path, show_all)
        if not hits:
            continue
        if exempt and not show_all:
            continue
        if do_fix and not exempt:
            text = open(path, encoding="utf-8").read()
            new = text
            for bad, good in REPLACE.items():
                new = new.replace(bad, good)
            if new != text:
                open(path, "w", encoding="utf-8").write(new)
                fixed_files += 1
            hits = scan(path, show_all)
            if not hits:
                continue
        for lineno, ch, kind in hits:
            name = unicodedata.name(ch, "UNNAMED")
            note = " (README exempt)" if exempt else ""
            sugg = f" -> {REPLACE[ch]!r}" if ch in REPLACE else ""
            print(f"{path}:{lineno}: U+{ord(ch):04X} {name}{sugg}{note}")
            if not exempt:
                violations += 1

    if do_fix:
        print(f"\n{fixed_files} file(s) rewritten", file=sys.stderr)
    if violations:
        print(f"\n{violations} violation(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
