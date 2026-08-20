#!/usr/bin/env python3
"""Classify test artifacts for retention: what is safe to reclaim, what is not.

Policy and rationale: contrib/perf/docs/POLICY.md "Cleaning up".

Lab runs leave large trees behind (test-logs is ~106M, reindex-profile ~17M),
and the tempting cleanup -- "delete anything old" -- destroys the evidence
behind published numbers. This tool answers the only question that matters
before deleting anything: **is this artifact still the source of a result
anyone can cite?**

An artifact is PROTECTED if any of these hold:
  - a ledger row names it (cpu_ledger source, ledger notes)
  - test-logs/DATA_INDEX.md names it
  - Measures.md names it (an M-* measure's evidence)
  - it contains a summary that is itself the record (SUMMARY.txt, FINDINGS.md,
    *.tsv, *.csv, measures_*.md)

Everything else is a CANDIDATE -- reviewable, not automatically doomed. This
tool never deletes; it prints, and --script emits commands for a human to read
before running.

Usage:
  contrib/perf/retention.py                 # report
  contrib/perf/retention.py --candidates    # only reclaimable
  contrib/perf/retention.py --script        # emit shell commands (not run)
  contrib/perf/retention.py --self-test
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TEST_LOGS = os.path.join(ROOT, "test-logs")
STORE = os.path.join(ROOT, "reindex-profile", "bench-summaries")

# Files whose presence means the directory holds a distilled result, not just
# raw capture data. Losing these loses the finding itself.
RESULT_FILES = re.compile(
    r"^(SUMMARY\.txt|FINDINGS\.md|NOTES\.md|.*\.tsv|.*\.csv|measures_.*\.md|.*\.json)$"
)

# Large regenerable raw capture data.
BULK_SUFFIX = (".trace", ".xml", ".jsonl.gz", ".tar.gz", ".tgz")


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def cited_names():
    """Every artifact name referenced by a ledger, the data index, or Measures."""
    cited = set()
    for name in ("cpu_ledger.jsonl", "ledger.jsonl"):
        p = os.path.join(STORE, name)
        for line in read_text(p).splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            for v in row.values():
                if isinstance(v, str):
                    for m in re.findall(r"test-logs/([A-Za-z0-9._-]+)", v):
                        cited.add(m)
    # Scan every perf document, not just two: a measure's evidence may be
    # cited from anywhere. Missing a citation is the expensive error --
    # it marks real evidence as reclaimable.
    docs = [os.path.join(TEST_LOGS, "DATA_INDEX.md")]
    for d in (HERE, os.path.join(HERE, "docs")):
        if os.path.isdir(d):
            docs += [os.path.join(d, f) for f in os.listdir(d)
                     if f.endswith(".md")]
    for doc in docs:
        txt = read_text(doc)
        for m in re.findall(r"test-logs/([A-Za-z0-9._-]+)", txt):
            cited.add(m)
        # Bare run-dir names, e.g. rescan-sys-20260814T014246Z
        for m in re.findall(r"\b([a-z0-9]+(?:-[a-z0-9]+)*-\d{8}T\d{6}Z)\b", txt):
            cited.add(m)
        # Bare top-level artifact dirs, e.g. `archives/...tar.gz`
        for m in re.findall(r"\b(archives|cpu-matrix[A-Za-z0-9._-]*|"
                            r"cpu-rebucket[A-Za-z0-9._-]*|review[A-Za-z0-9._-]*)/", txt):
            cited.add(m)
    return cited


def dir_size(path):
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def has_result_files(path):
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            if RESULT_FILES.match(f):
                return True
    return False


def bulk_bytes(path):
    """Regenerable raw capture bytes inside an otherwise-protected artifact."""
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            if f.endswith(BULK_SUFFIX):
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
    return total


# Never reclaimed, whatever the citation scan says. Lab scratch lives in /tmp
# and is disposable by design (tiny_baseline.sh defaults LAB=/tmp/...), so what
# survives under test-logs/ is the durable record. For archives/ specifically,
# the tarball is often the ONLY copy of a run whose scratch tree is long gone.
NEVER_RECLAIM = ("archives",)


def classify(entry, cited):
    """PROTECTED / CANDIDATE, with the reason. Reason is the point: a bare
    verdict is not reviewable."""
    name = entry["name"]
    if name in NEVER_RECLAIM:
        return "PROTECTED", "never reclaimed: durable archive, often the only copy"
    if name in cited:
        return "PROTECTED", "cited by a ledger, DATA_INDEX or Measures"
    if entry["results"]:
        return "PROTECTED", "contains a distilled result (summary/tsv/csv/json)"
    return "CANDIDATE", "no citation and no distilled result found"


def scan():
    out = []
    if not os.path.isdir(TEST_LOGS):
        return out
    cited = cited_names()
    for name in sorted(os.listdir(TEST_LOGS)):
        p = os.path.join(TEST_LOGS, name)
        if not os.path.isdir(p):
            continue
        e = {"name": name, "path": p, "size": dir_size(p),
             "results": has_result_files(p), "bulk": bulk_bytes(p)}
        e["status"], e["reason"] = classify(e, cited)
        out.append(e)
    return out


def mb(n):
    return n / (1024.0 * 1024.0)


def self_test():
    ok = True

    def check(c, m):
        nonlocal ok
        if not c:
            print("FAIL: " + m, file=sys.stderr)
            ok = False

    check(RESULT_FILES.match("SUMMARY.txt"), "SUMMARY.txt is a result file")
    check(RESULT_FILES.match("results.tsv"), "tsv is a result file")
    check(RESULT_FILES.match("measures_tiny.md"), "measures_*.md is a result file")
    check(not RESULT_FILES.match("debug.log"), "debug.log is not a result file")

    s, _ = classify({"name": "x", "results": False}, {"x"})
    check(s == "PROTECTED", "cited artifact protected")
    s, _ = classify({"name": "y", "results": True}, set())
    check(s == "PROTECTED", "artifact with distilled result protected")
    s, r = classify({"name": "z", "results": False}, set())
    check(s == "CANDIDATE" and r, "uncited, resultless is a candidate with a reason")

    c = cited_names()
    check(isinstance(c, set), "citation scan returns a set")
    # Guard the real risk: a known-cited capture must never be a candidate.
    if os.path.isdir(TEST_LOGS):
        rows = scan()
        prot = [r for r in rows if r["status"] == "PROTECTED"]
        check(len(prot) > 0, "at least one artifact is protected in this tree")
        for r in rows:
            if r["name"].startswith("cpu-matrix"):
                check(r["status"] == "PROTECTED", "cpu-matrix must be protected")
        # Regression guard: archives/ holds the M-WAL-SYNC-FAT evidence and is
        # cited only as `archives/...tar.gz`, with no test-logs/ prefix.
        for r in rows:
            if r["name"] == "archives":
                check(r["status"] == "PROTECTED",
                      "archives/ must be protected")
    # archives/ is protected unconditionally, even with no citations at all.
    s2, r2 = classify({"name": "archives", "results": False}, set())
    check(s2 == "PROTECTED" and "only copy" in r2,
          "archives/ protected even when uncited")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", action="store_true")
    ap.add_argument("--script", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv[1:])
    if a.self_test:
        return self_test()

    rows = scan()
    if not rows:
        print("no test-logs directory")
        return 0

    if a.script:
        print("# Review before running. Nothing here is executed by this tool.")
        print("# Protected artifacts are omitted entirely.")
        for r in rows:
            if r["status"] == "CANDIDATE":
                print("rm -rf %-58s # %.1f MB" % (
                    os.path.relpath(r["path"], ROOT), mb(r["size"])))
        for r in rows:
            if r["name"] in NEVER_RECLAIM:
                continue
            if r["status"] == "PROTECTED" and r["bulk"] > 5 * 1024 * 1024:
                print("# trim raw capture only, keep the summary: %s (%.1f MB bulk)"
                      % (os.path.relpath(r["path"], ROOT), mb(r["bulk"])))
        return 0

    shown = [r for r in rows if not a.candidates or r["status"] == "CANDIDATE"]
    print("%-46s %-10s %9s  %s" % ("ARTIFACT", "STATUS", "SIZE(MB)", "REASON"))
    print("-" * 110)
    for r in shown:
        print("%-46s %-10s %9.1f  %s" % (r["name"][:46], r["status"],
                                         mb(r["size"]), r["reason"]))
    prot = sum(r["size"] for r in rows if r["status"] == "PROTECTED")
    cand = sum(r["size"] for r in rows if r["status"] == "CANDIDATE")
    bulk = sum(r["bulk"] for r in rows if r["status"] == "PROTECTED")
    print("-" * 110)
    print("protected %.1f MB in %d artifacts; candidates %.1f MB in %d" % (
        mb(prot), sum(1 for r in rows if r["status"] == "PROTECTED"),
        mb(cand), sum(1 for r in rows if r["status"] == "CANDIDATE")))
    print("raw capture bytes inside protected artifacts: %.1f MB "
          "(trimmable without losing the result)" % mb(bulk))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
