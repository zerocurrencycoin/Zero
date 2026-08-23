#!/usr/bin/env python3
"""Flag decorative non-ASCII in documents and code.

Project rule (AGENTS.md): no emojis or decorative Unicode in any document
except README.md; use ASCII equivalents -- `--` not em-dash, `->` not arrow,
`"` not curly quotes, `...` not ellipsis. Nothing enforced it, so violations
accumulated.

Usage (from repo root):
  contrib/perf/fix_ascii.py                       # report; exit 1 if violations
  contrib/perf/fix_ascii.py --fix                 # rewrite, contrib/perf/ only
  contrib/perf/fix_ascii.py --fix --all-paths     # outside contrib/perf/ too
  contrib/perf/fix_ascii.py --fix --ascii-formula # include formula-bearing files

Every --fix confirms before writing (Y/n). There is no flag to skip it.
  contrib/perf/fix_ascii.py --all      # include tolerated characters
  contrib/perf/fix_ascii.py PATH...    # limit to given paths

Exit status: 0 clean, 1 violations found, 2 usage error.
"""
import contextlib
import io
import os
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

# README.md is exempt from the no-decorative-Unicode rule.
EXEMPT = re.compile(r"(^|/)README\.md$")

# How many paths to list before eliding, in the confirmation prompt.
MAX_LIST = 10

# Content that makes a blind substitution unsafe. U+00B7 is a product in an
# equation and a separator in a list; the table cannot tell them apart, so any
# file that looks mathematical is excluded from --fix unless explicitly allowed.
FORMULA_HINT = re.compile(
    r"[=<>]\s*[A-Za-z0-9(]"          # an equation or comparison
    r"|\b(?:equation|verify_proof|miller_loop|final_exponentiation)\b"
    r"|[\u00b7\u00d7\u2212\u2264\u2265\u2260\u2261\u2211\u220f\u221a]"
    r"|\b[A-Za-z]\s*[*/]\s*[A-Za-z]\b"  # symbolic product or quotient
)


def has_formula(path):
    """True if PATH holds content a blind substitution could corrupt."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (UnicodeDecodeError, OSError):
        return False
    return bool(FORMULA_HINT.search(text))


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


def self_test():
    """Pin the substitution table and the scope guard.

    This tool has damaged content before: run tree-wide, its U+00B7 -> '-'
    mapping turned products into apparent subtraction in a Groth16 pairing
    equation, and it rewrote eight Zero400-owned documents this tree does not
    own. Both failures are silent -- the file still parses. So the scope guard
    and the risky mappings are asserted here.
    """
    import tempfile

    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    # Substitution table: each mapping is ASCII and non-empty.
    for bad, good in REPLACE.items():
        check(good and all(ord(c) < 128 for c in good),
              "replacement for U+%04X must be ASCII" % ord(bad))
    check(REPLACE["\u2014"] == "--", "em dash -> --")
    check(REPLACE["\u2192"] == "->", "rightwards arrow -> ->")

    # U+00B7 is the known-dangerous one: harmless in a separator list, wrong in
    # an equation. It stays mapped, but the hazard is recorded here so anyone
    # changing the table meets the reason.
    check("\u00b7" in REPLACE, "middle dot is in the table")
    check(REPLACE["\u00b7"] == "-",
          "middle dot maps to '-'; NEVER bulk-apply to a document with formulas "
          "(docs/POLICY.md S7.4)")

    # Flag-only ranges must never gain a silent replacement.
    for lo, hi in FLAG_ONLY_RANGES:
        check(lo <= hi, "flag-only range is ordered")
        check(not any(lo <= ord(c) <= hi for c in REPLACE),
              "no flag-only codepoint may also be auto-replaced")

    # Section sign is tolerated: it is conventional here, not decorative.
    check("\u00a7" in TOLERATED, "section sign tolerated")

    # Exemption and skip paths.
    check(EXEMPT.search("README.md"), "root README exempt")
    check(EXEMPT.search("contrib/perf/README.md"), "nested README exempt")
    check(not EXEMPT.search("contrib/perf/Perf.md"), "other docs are not exempt")
    check(SKIP_PATH.match("src/leveldb/db.cc"), "vendored leveldb skipped")
    check(SKIP_PATH.match("depends/x.mk"), "depends skipped")
    check(not SKIP_PATH.match("contrib/perf/Perf.md"), "owned docs not skipped")

    # scan() reports position and kind.
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "t.md")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("plain\nem \u2014 dash\nemoji \U0001F600\n")
        hits = scan(f, False)
        kinds = {k for _, _, k in hits}
        check(any(ch == "\u2014" for _, ch, _ in hits), "em dash detected")
        check("replace" in kinds, "em dash classified replaceable")
        check("flag" in kinds, "emoji classified flag-only, not replaced")
        check(all(ln > 0 for ln, _, _ in hits), "line numbers are 1-based")

        clean = os.path.join(d, "c.md")
        with open(clean, "w", encoding="utf-8") as fh:
            fh.write("pure ascii -- fine\n")
        check(scan(clean, False) == [], "clean file yields no hits")

    # SCOPE GUARD, tested by BEHAVIOUR not by source text: --fix must not
    # write outside contrib/perf/ without --all-paths. This is the guard that
    # was missing when eight Zero400-owned documents were rewritten.
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            outside = "NotOurs.md"
            inside_dir = os.path.join("contrib", "perf")
            os.makedirs(inside_dir)
            inside = os.path.join(inside_dir, "Ours.md")
            body = "em \u2014 dash\n"
            for f in (outside, inside):
                with open(f, "w", encoding="utf-8") as fh:
                    fh.write(body)

            # Non-interactive: confirmation must default to NO.
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(err):
                rc = main(["prog", "--fix", outside, inside])
            check(rc == 2, "without a TTY, --fix refuses rather than assuming yes")
            check(open(inside, encoding="utf-8").read() == body,
                  "a refused run leaves even in-scope files unchanged")

            # With confirmation, the in-scope file is rewritten and the
            # out-of-scope one still is not.
            global confirm_changes
            real_confirm = confirm_changes
            confirm_changes = lambda paths: True
            try:
                with contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(err):
                    main(["prog", "--fix", outside, inside])
            finally:
                confirm_changes = real_confirm

            check(open(outside, encoding="utf-8").read() == body,
                  "--fix must NOT rewrite a file outside contrib/perf/")
            check("\u2014" not in open(inside, encoding="utf-8").read(),
                  "--fix must rewrite a file inside contrib/perf/")
            check("scoped" in err.getvalue(), "the skip is reported, not silent")

            # BLAST RADIUS: a formula-bearing file must be refused, and the
            # substitution must not have been applied.
            math_f = os.path.join(inside_dir, "Math.md")
            math_body = "the equation A \u00b7 B = C \u2014 see\n"
            with open(math_f, "w", encoding="utf-8") as fh:
                fh.write(math_body)
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(err):
                rc = main(["prog", "--fix", math_f])
            check(rc == 2, "--fix refuses a formula-bearing file")
            check(open(math_f, encoding="utf-8").read() == math_body,
                  "a refused formula file is left byte-identical")
            check("formula" in err.getvalue(), "the refusal names the reason")

            # ... and proceeds when the operator has checked them.
            with contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(io.StringIO()):
                confirm_changes = lambda paths: True
                try:
                    main(["prog", "--fix", "--ascii-formula", math_f])
                finally:
                    confirm_changes = real_confirm
            check("\u2014" not in open(math_f, encoding="utf-8").read(),
                  "--ascii-formula permits the rewrite")

            # The scope override exists and works, so the hatch is real.
            confirm_changes = lambda paths: True
            try:
                with contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    main(["prog", "--fix", "--all-paths", outside])
            finally:
                confirm_changes = real_confirm
            check("\u2014" not in open(outside, encoding="utf-8").read(),
                  "--all-paths must allow writes outside contrib/perf/")
        finally:
            os.chdir(cwd)

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def confirm_changes(paths):
    """Standard Y/n confirmation before rewriting files.

    Returns True only on an explicit yes. Without a TTY there is nobody to ask,
    so the answer is no -- a script or CI job must not rewrite files by default.
    """
    print("About to rewrite %d file(s):" % len(paths), file=sys.stderr)
    for p in paths[:MAX_LIST]:
        print("    %s" % p, file=sys.stderr)
    if len(paths) > MAX_LIST:
        print("    ... and %d more" % (len(paths) - MAX_LIST), file=sys.stderr)
    if not sys.stdin.isatty():
        print("not a terminal; refusing to rewrite without confirmation",
              file=sys.stderr)
        return False
    try:
        reply = input("Proceed? [Y/n] ").strip().lower()
    except EOFError:
        return False
    return reply in ("", "y", "yes")


def main(argv):
    if "--self-test" in argv:
        return self_test()
    show_all = "--all" in argv
    do_fix = "--fix" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        paths = [f for f in tracked_files()
                 if CHECK_EXT.search(f) and not SKIP_PATH.match(f)]

    # --fix is scoped to ZeroPerf-owned files. Zero400 owns the root documents
    # and src/; rewriting them from this tree contradicts the ownership rule
    # (contrib/perf/docs/POLICY.md S7) and has silently damaged content before:
    # the U+00B7 -> '-' mapping turned products into apparent subtraction in a
    # Groth16 pairing equation. Reporting is unrestricted; only writing is not.
    OWNED = "contrib/perf/"
    if do_fix and "--all-paths" not in argv:
        skipped = [p for p in paths if not p.startswith(OWNED)]
        paths = [p for p in paths if p.startswith(OWNED)]
        if skipped:
            print("--fix scoped to %s; %d file(s) outside it left unchanged."
                  % (OWNED, len(skipped)), file=sys.stderr)
            print("  Report them with no --fix, or override with --all-paths.",
                  file=sys.stderr)

    # Blast-radius guard. A --fix that would touch many files, or any file
    # holding mathematics, is not something to run unattended: this tool has
    # silently rewritten eight documents it did not own, and its U+00B7 -> '-'
    # mapping turned products into apparent subtraction in a pairing equation
    # (docs/POLICY.md S7.4). Both classes now require explicit confirmation.
    if do_fix:
        planned = [p for p in paths if scan(p, show_all) and not EXEMPT.search(p)]
        formula = [p for p in planned if has_formula(p)]
        if formula and "--ascii-formula" not in argv:
            print("REFUSING --fix: %d file(s) contain formula-like content."
                  % len(formula), file=sys.stderr)
            for p in formula[:10]:
                print("    %s" % p, file=sys.stderr)
            if len(formula) > 10:
                print("    ... and %d more" % (len(formula) - 10), file=sys.stderr)
            print("  Substitutions such as U+00B7 -> '-' change meaning in "
                  "mathematics.\n  Fix these by hand, or pass "
                  "--ascii-formula if you have checked each one.",
                  file=sys.stderr)
            return 2

        # Every file change is confirmed. There is no flag to skip this:
        # an unattended rewrite is how eight unowned documents and a pairing
        # equation were damaged (docs/POLICY.md S7.4). Non-interactive callers
        # get a refusal, not a silent yes.
        if planned and not confirm_changes(planned):
            print("aborted; no files changed", file=sys.stderr)
            return 2

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
