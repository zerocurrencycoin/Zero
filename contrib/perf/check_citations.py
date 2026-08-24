#!/usr/bin/env python3
"""Flag measurement figures that name no source, and absolute paths in docs.

Two rules exist in writing and nothing enforced either, which is how a
693-violation ASCII backlog and 11 stale absolute paths accumulated:

  1. A number is cited by `M-*` id (docs/POLICY.md S7.1). Measures.md owns
     figures; everything else cites the id.
  2. No absolute paths in tracked documents (docs/POLICY.md S7.3).

Scope is deliberately narrow, because a check that fires on everything gets
ignored:

  - Only MEASUREMENT-shaped figures count -- throughput (blk/s, h/s),
    per-block cost (ms/block), CPU share. A config value (`MAX_BATCH_LATENCY=
    100ms`), a disk size (`8 GB`) or a file count is not a measure.
  - A figure is satisfied by an `M-*` id OR by naming its evidence directly
    (a run directory, a ledger, a `.csv`/`.tsv`/`.json` artifact). Provenance
    is the point; the id is one way to give it.
  - Code fences are skipped: sample output is not a claim.

Usage:
  contrib/perf/check_citations.py                 # owned docs; exit 1 on findings
  contrib/perf/check_citations.py PATH...         # limit to given paths
  contrib/perf/check_citations.py --paths-only    # only rule 2
  contrib/perf/check_citations.py --self-test

Exit: 0 clean, 1 findings, 2 usage error.
"""
import os
import re
import subprocess
import sys

# Measurement-shaped figures only.
MEASURE = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:blk/s|h/s)\b"
    r"|\b\d+(?:\.\d+)?\s?ms/block\b"
    r"|\b\d+(?:\.\d+)?\s?%\s+(?:of\s+)?(?:CPU|cpu)\b"
)

# Either an M-* id, or evidence named directly.
CITED = re.compile(
    r"\bM-[A-Z0-9][A-Z0-9-]*\b"
    r"|\b[a-z0-9][a-z0-9-]*-\d{8}T\d{6}Z\b"        # run directory
    r"|\b\w[\w.-]*\.(?:csv|tsv|jsonl|json|log|txt)\b"
    r"|\bledger\b|\bMeasures\.md\b|\bDATA_INDEX\.md\b"
)

# Absolute paths that must not appear in a tracked document.
ABS_PATH = re.compile(r"~/[A-Za-z0-9_.-]+/|/Users/[A-Za-z0-9_.-]+/|/home/[A-Za-z0-9_.-]+/")

# Illustrative placeholders and the product's own documented defaults are not
# leaks: `~/.zero` IS the Unix datadir and has to be nameable.
ABS_OK = re.compile(
    r"/home/u/"                                    # self-test fixture
    r"|~/\.zero\b|~/\.zcash-params\b"              # documented product defaults
    r"|~/Library/Application Support\b"
    r"|<[A-Za-z_-]+>/"                             # <linearize>/bootstrap.dat
    r"|<name>|<user>|`?\.\.\.`?"                     # the rule quoting itself
)

# A line that STATES the prohibition is not a violation of it.
RULE_TEXT = re.compile(r"Never write|must not|do not (?:write|put)|prohibit",
                       re.I)

# Lines either side of a figure that may carry its provenance. Small on
# purpose: a citation four paragraphs away is not a citation.
CONTEXT = 6

SKIP_DIR = re.compile(r"contrib/perf/(keep|zcash-lint|mine|groth16-batch-poc)/")


def owned_docs():
    out = subprocess.run(["git", "ls-files", "contrib/perf/*.md",
                          "contrib/perf/**/*.md"],
                         capture_output=True, text=True)
    if out.returncode:
        sys.exit("not a git repo (run from repo root)")
    return [p for p in out.stdout.split() if not SKIP_DIR.search(p)]


def scan(path, paths_only=False):
    """Return [(lineno, rule, text)] for PATH."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    findings = []
    fence = False
    for lineno, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue  # sample output is not a claim
        if not paths_only and MEASURE.search(line) and not CITED.search(line):
            # Provenance often sits on a neighbouring line rather than the one
            # carrying the number: a table's intro sentence, or the next line
            # of a wrapped sentence. Citing each table row separately would be
            # noise, so look at a small window instead.
            lo = max(0, lineno - 1 - CONTEXT)
            hi = min(len(lines), lineno + CONTEXT)
            if not any(CITED.search(x) for x in lines[lo:hi]):
                findings.append((lineno, "uncited-measure", line.strip()))
        for m in ABS_PATH.finditer(line):
            frag = line[max(0, m.start() - 8):m.end() + 24]
            if not ABS_OK.search(frag) and not RULE_TEXT.search(line):
                findings.append((lineno, "absolute-path", line.strip()))
                break
    return findings


def self_test():
    import tempfile

    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    def scan_text(text, **kw):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(text)
            p = fh.name
        try:
            return scan(p, **kw)
        finally:
            os.unlink(p)

    def rules(text, **kw):
        return {r for _, r, _ in scan_text(text, **kw)}

    # Rule 1: an uncited measurement is flagged.
    check("uncited-measure" in rules("Throughput was 1070.95 blk/s here.\n"),
          "a bare throughput figure is flagged")
    check("uncited-measure" in rules("The walk cost 5.31 ms/block.\n"),
          "a bare per-block cost is flagged")

    # ... and any form of provenance satisfies it.
    for cited in ("1070.95 blk/s (M-CPU-SEQ)",
                  "1070.95 blk/s -- see tiny-20260819T234958Z",
                  "1070.95 blk/s from measures_tiny.csv",
                  "1070.95 blk/s in the ledger",
                  "5.31 ms/block per Measures.md"):
        check("uncited-measure" not in rules(cited + "\n"),
              "provenance satisfies the citation rule: %r" % cited)

    # Non-measurements must NOT fire, or the check becomes noise.
    for benign in ("MAX_BATCH_LATENCY=100ms", "roughly 8 GB per solver thread",
                   "42 files of ~128 MB", "test-logs is ~101 MB",
                   "a 4% spread", "wallet.zero is 749MB"):
        check(rules(benign + "\n") == set(),
              "benign figure must not be flagged: %r" % benign)

    # Code fences are exempt: sample output is not a claim.
    check(rules("```\nreindex: 1070.95 blk/s\n```\n") == set(),
          "figures inside a code fence are not claims")

    # Rule 2: absolute paths.
    check("absolute-path" in rules("See /Users/someone/Work/thing.md\n"),
          "a /Users path is flagged")
    check("absolute-path" in rules("Kept at ~/Work/ZK/ZKs/Comparison.md\n"),
          "a ~/Work path is flagged")

    # ... but the product's own documented defaults are nameable.
    for allowed in ("the Unix datadir is ~/.zero",
                    "params live in ~/.zcash-params",
                    "macOS uses ~/Library/Application Support/zero",
                    "cp <linearize>/bootstrap.dat $SCRATCH/"):
        check("absolute-path" not in rules(allowed + "\n"),
              "documented default must be nameable: %r" % allowed)

    # A line stating the rule is not a breach of it.
    check("absolute-path" not in
          rules("Never write `/Users/<name>/...` into a tracked document.\n"),
          "a line stating the prohibition is not itself a violation")

    # --paths-only suppresses rule 1 but keeps rule 2.
    both = "1070.95 blk/s at /Users/x/y/\n"
    check("uncited-measure" not in rules(both, paths_only=True),
          "--paths-only suppresses the citation rule")
    check("absolute-path" in rules(both, paths_only=True),
          "--paths-only keeps the path rule")

    # Provenance on a neighbouring line counts: a table intro or a wrapped
    # sentence should not force a citation onto every row.
    check(rules("Source: the ledger, n as noted.\n\n| x | 130 blk/s |\n") == set(),
          "a table intro citation covers its rows")
    check("uncited-measure" not in
          rules("It ran at 5.31 ms/block\nstock (M-WAL-WITNESS-TIP-AB).\n"),
          "a citation on the next line of a wrapped sentence counts")
    # ... but not one far away.
    far = "cited in M-FOO\n" + "\n" * 12 + "ran at 130 blk/s\n"
    check("uncited-measure" in rules(far),
          "a citation many lines away does not count")

    # Line numbers are 1-based and real.
    f = scan_text("ok\nok\n1070.95 blk/s\n")
    check(f and f[0][0] == 3, "line numbers are 1-based")

    check(scan_text("Nothing notable here.\n") == [], "a clean document is clean")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    paths_only = "--paths-only" in argv
    paths = [a for a in argv if not a.startswith("--")] or owned_docs()

    total = 0
    for p in sorted(paths):
        for lineno, rule, text in scan(p, paths_only=paths_only):
            print("%s:%d: %s: %s" % (p, lineno, rule, text[:110]))
            total += 1
    if total:
        print("\n%d finding(s). A measurement needs an M-* id or named "
              "evidence; documents name no absolute paths." % total,
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
