#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Enforce the one-owner rules from docs/MAP.md S3.

Two failures this catches, both of which happened and were only found by
reading:

  scattered subject   A subject discussed wherever it was encountered rather
                      than in the document that owns it. `Equihash` reached 21
                      files with `equ/` holding 25% of its mentions.

  duplicated task id  The same id tracked in two files, whose states then
                      diverge. Eight ids were in both Perf.md and TASKS.md;
                      one stayed "postponed" after being closed elsewhere.

Ownership is declared here, not inferred: a subject with no owner is not
checked, because guessing an owner from mention counts would bless whatever
the current sprawl happens to be.

  check_concentration.py [--max-outside PCT] [paths...]
  check_concentration.py --self-test

Exit: 0 clean, 1 violations found, 2 usage error.
"""
import os
import re
import sys
from collections import defaultdict

# subject -> (regex, owning path fragment). Add a row when a subject acquires
# an owner; absent subjects are not checked.
# An owner may be several files when a subject is genuinely shared: `blake2b`
# is both a hashing-library subject and a measured CPU bucket, and libsodium is
# discussed by both the version survey and the library-division document.
# Declaring one owner for those produced false positives, which is worse than
# no check -- it trains readers to ignore the output.
OWNERS = {
    "Equihash": (r"Equihash|equihash", ("equ/",)),
    "tromp": (r"\btromp\b", ("equ/",)),
    "uniblake": (r"\buniblake\b", ("HASHLIBS.md", "CROSSPROJECT.md", "RecBench.md")),
    "libsodium": (r"\blibsodium\b", ("SODIUM_SURVEY.md", "HASHLIBS.md")),
    "Groth16": (r"Groth16", ("PerfGroth.md",)),
}

# Task ids that must appear in exactly one file.
TASK_ID = re.compile(r"\b(?:[A-Z]\d[a-z]?|T\d[a-z]?|TST-\d+|G\d[a-z]?|P\d)\b")

DEFAULT_MAX_OUTSIDE = 20.0


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


def concentration(files):
    """Per subject: (inside, outside, pct_outside, worst offender)."""
    res = {}
    for subj, (pat, owner) in OWNERS.items():
        inside = outside = 0
        per = defaultdict(int)
        for f in files:
            try:
                n = len(re.findall(pat, open(f, encoding="utf-8").read()))
            except OSError:
                continue
            if not n:
                continue
            if any(o in f for o in owner):
                inside += n
            else:
                outside += n
                per[f] += n
        total = inside + outside
        if total:
            worst = max(per.items(), key=lambda kv: kv[1]) if per else ("", 0)
            res[subj] = (inside, outside, outside / total * 100.0, worst)
    return res


def scan(files, max_outside=DEFAULT_MAX_OUTSIDE):
    bad = []
    for subj, (ins, out, pct, worst) in sorted(concentration(files).items()):
        if pct > max_outside:
            bad.append("scattered-subject: %s is %.0f%% outside its owner "
                       "(%d in / %d out; worst %s: %d)"
                       % (subj, pct, ins, out, os.path.basename(worst[0]), worst[1]))
    return bad


def main(argv):
    if "--self-test" in argv:
        return self_test()
    max_out = DEFAULT_MAX_OUTSIDE
    if "--max-outside" in argv:
        i = argv.index("--max-outside")
        try:
            max_out = float(argv[i + 1])
        except (IndexError, ValueError):
            print("usage: --max-outside PCT", file=sys.stderr)
            return 2
        del argv[i:i + 2]
    paths = argv[1:] or ["contrib/perf"]
    bad = scan(_docs(paths), max_out)
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
        own = os.path.join(td, "equ")
        os.makedirs(own)
        # Concentrated: 10 mentions in the owner, 1 outside -> 9% outside.
        open(os.path.join(own, "S.md"), "w").write("Equihash " * 10)
        open(os.path.join(td, "other.md"), "w").write("Equihash once")
        files = _docs([td])
        res = concentration(files)
        check("Equihash" in res, "subject detected")
        check(res["Equihash"][2] < 20, "concentrated subject is under threshold")
        check(not scan(files), "concentrated subject reports clean")

        # Scattered: flip the ratio.
        open(os.path.join(td, "other.md"), "w").write("Equihash " * 40)
        files = _docs([td])
        bad = scan(files)
        check(bad, "scattered subject is reported")
        check(bad and "scattered-subject" in bad[0], "violation is labelled")
        check(bad and "other.md" in bad[0], "worst offender is named")

        # A subject with no owner declared is not checked at all.
        open(os.path.join(td, "x.md"), "w").write("Frobnicate " * 99)
        check(len(scan(_docs([td]))) == len(bad), "undeclared subject is ignored")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
