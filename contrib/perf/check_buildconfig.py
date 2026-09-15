#!/usr/bin/env python3
# Copyright (c) 2026 The Zero developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Verify a built binary matches the build configuration it was meant to have.

Five build-flag failures in one session, every one of them silent at build
time (docs/TOOLING_FAILURES.md S4a):

  - CXXFLAGS=-DZERO_PERF never reached any compile; the binary was inspected
    and reported as "counters missing".
  - CPPFLAGS=-DDEBUG_LOCKORDER reached only the TUs make chose to rebuild.
  - CPPFLAGS= on the make line REPLACED configure's CPPFLAGS, dropping
    -DMAC_OSX; the node then looked for proving parameters in the Linux path
    and a measurement run produced zero blocks.
  - Restoring the default build took eight successive link failures.
  - A stale 8-byte libunivalue.a blocked a rebuild without erroring.

The common property: the build succeeded and the binary was wrong. This checks
the artifact instead of trusting the command line.

  check_buildconfig.py <binary> [--expect NAME] [--reject NAME]
  check_buildconfig.py --self-test

NAME is a build feature from the table below. Exit 0 if every --expect is
present and every --reject is absent, 1 otherwise, 2 on usage error.
"""
import os
import subprocess
import sys

# feature -> (marker string in the binary, what it proves)
#
# Each marker is a string literal that only exists when the feature is
# compiled in. Chosen to be unique and stable: a log format string, not a
# symbol name, so this works on a stripped release binary too.
FEATURES = {
    "ZERO_PERF": ("PerfProof: height=",
                  "proof-verification counters (P1)"),
    "DEBUG_LOCKORDER": ("LockStats: recursive_acquires=",
                        "lock-order checker and hygiene counters"),
    "MAC_OSX": ("Library/Application Support",
                "macOS parameter and datadir paths"),
}


def markers(path):
    """Every printable string in PATH, as one blob."""
    try:
        out = subprocess.run(["strings", "-a", path], capture_output=True,
                             check=False)
    except OSError as e:
        raise RuntimeError("cannot run strings: %s" % e)
    return out.stdout.decode("utf-8", "replace")


def check(path, expect=(), reject=()):
    if not os.path.exists(path):
        return ["%s: no such file -- a build that 'succeeded' with no binary "
                "is the link having failed" % path]
    blob = markers(path)
    bad = []
    for name in expect:
        marker, what = FEATURES[name]
        if marker not in blob:
            bad.append("%s: expected %s (%s), marker %r absent"
                       % (path, name, what, marker))
    for name in reject:
        marker, what = FEATURES[name]
        if marker in blob:
            bad.append("%s: did NOT expect %s (%s), marker %r present"
                       % (path, name, what, marker))
    return bad


def self_test():
    import tempfile
    ok = True

    def expect(cond, why):
        nonlocal ok
        if not cond:
            print("FAIL: %s" % why, file=sys.stderr)
            ok = False

    with tempfile.TemporaryDirectory() as td:
        # A file containing one marker and not the other.
        p = os.path.join(td, "fake")
        with open(p, "w", encoding="utf-8") as f:
            f.write("noise PerfProof: height= more noise\n")

        expect(check(p, expect=["ZERO_PERF"]) == [],
               "present marker should pass --expect")
        expect(check(p, reject=["ZERO_PERF"]) != [],
               "present marker should fail --reject")
        expect(check(p, expect=["DEBUG_LOCKORDER"]) != [],
               "absent marker should fail --expect")
        expect(check(p, reject=["DEBUG_LOCKORDER"]) == [],
               "absent marker should pass --reject")
        # The failure that cost the most: no binary at all.
        expect(check(os.path.join(td, "gone"), expect=["ZERO_PERF"]) != [],
               "missing binary must be an error, not a pass")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    args = argv[1:]
    if not args:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    path = args[0]
    expect, reject = [], []
    i = 1
    while i < len(args):
        if args[i] in ("--expect", "--reject") and i + 1 < len(args):
            name = args[i + 1]
            if name not in FEATURES:
                print("unknown feature %r; known: %s"
                      % (name, ", ".join(sorted(FEATURES))), file=sys.stderr)
                return 2
            (expect if args[i] == "--expect" else reject).append(name)
            i += 2
        else:
            print("usage: check_buildconfig.py <binary> "
                  "[--expect NAME] [--reject NAME]", file=sys.stderr)
            return 2
    bad = check(path, expect, reject)
    for b in bad:
        print(b)
    if not bad:
        print("%s: build config as expected (expect=%s reject=%s)"
              % (path, expect or "-", reject or "-"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
