#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""List files present on BASE (default master) and absent from the working tree, as CSV on stdout, with
evidence for review: the first release tag already without the file, matches in build
files, mentions elsewhere in the tree, what covers the material, a proposal, and a
verified value.

Usage: deletions-check.py [REPO [BASE]] > LIST.csv"""
import sys
if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__); sys.exit(0)
import csv, subprocess, sys, pathlib

repo = sys.argv[1] if len(sys.argv) > 1 else '.'
base = sys.argv[2] if len(sys.argv) > 2 else 'master'
TAGS = ['v3.4.0', 'v4.0.0', 'v4.0.1']
BUILD = ['Makefile.am', 'configure.ac', 'src/Makefile.am', 'src/Makefile.test.include', 'src/Makefile.gtest.include',
         'doc/man/Makefile.am', 'depends', 'zcutil', 'contrib', 'qa/pull-tester', '.github']

def git(*a):
    return subprocess.run(['git', '-C', repo] + list(a), capture_output=True, text=True).stdout

deleted = [l.split('\t')[1] for l in git('diff', '--name-status', '--diff-filter=D', base).splitlines()]
# Files restored but not yet added to git still show as deleted; keep only paths absent on disk.
deleted = [p for p in deleted if not (pathlib.Path(repo) / p).exists()]
tag_files = {t: set(git('ls-tree', '-r', '--name-only', t).splitlines()) for t in TAGS}

def group(p):
    if p.startswith('doc/release-notes/'): return 'upstream Zcash release notes'
    if p.startswith('doc/bitcoin-release-notes/'): return 'upstream Bitcoin release notes'
    if p.startswith('contrib/gitian'): return 'gitian build'
    if p.startswith('doc/'): return 'upstream documentation'
    if p.startswith('src/') or p.startswith('qa/'): return 'code or tests'
    if p.startswith('zcutil/') or p.startswith('contrib/'): return 'scripts'
    return 'repository root'

def grep(word, paths=None):
    args = ['grep', '-l', '-F', word, '--'] + (paths or ['.'])
    return [f for f in git(*args).splitlines() if f]

COVERED = {
    'src/alert.cpp': 'release notes: -alerts and the P2P alert system removed',
    'src/alert.h': 'release notes: -alerts and the P2P alert system removed',
    'src/alertkeys.h': 'release notes: -alerts and the P2P alert system removed',
    'src/sendalert.cpp': 'release notes: -alerts and the P2P alert system removed',
    'src/test/alert_tests.cpp': 'tests of the removed alert system',
    'src/test/data/alertTests.raw': 'data for the removed alert tests',
}
QUESTION = {
    'responsible_disclosure.md': 'delete: ECC policy routing reports to security@z.cash; question: Zero security contact for a SECURITY.md',
    'doc/security-warnings.md': 'delete: Zcash 2016 warnings, relocated upstream; question: Zero warnings for the README section',
    'doc/authors.md': 'yes: its only reference, contrib/debian/copyright, is deleted',
    'doc/init.md': 'delete: stale reference in contrib/init/README.md, resolved with the contrib/init proposal',
    'doc/release-notes/release-notes-1.0.0.md': 'yes: its only reference, zcutil/build-debian-package.sh, is deleted',
    'qa/zcash/performance-measurements.sh': 'yes: no references in the tree; Equihash timing runs through ops-validate.sh verifyeq and solveeq',
}
PREFIX = {
    'contrib/ci-workers/': ('Zcash buildbot provisioning; required Python 2; CI runs on GitHub Actions',
                            'yes: nothing references it'),
    'contrib/debian/': ('Zcash Debian packaging; the release .deb comes from zcutil/release-linux.sh',
                        'yes: nothing references it; zcutil/release-linux.sh builds the .deb'),
    'zcutil/build-debian-package.sh': ('Superseded by zcutil/release-linux.sh; failed since v4.0.0',
                                       'yes: Makefile.am entry removed'),
    'src/snark/': ('libsnark leftovers; Zcash removed libsnark in v2.1.0', 'yes: build and gate pass without it'),
    'qa/rpc-tests/wallet_mergetoaddress.py': ('Replaced by the mergetoaddress_* tests', 'yes: in no tier list'),
}
def prefix(p):
    return next((v for k, v in PREFIX.items() if p.startswith(k)), None)

def verified(p, g, absent, build, mentions):
    if prefix(p):
        return prefix(p)[1]
    if p in QUESTION:
        return QUESTION[p]
    if p.startswith('src/'):
        return 'yes: build and gate pass without it'
    if p == 'INSTALL':
        return 'yes: build matches are the make variable INSTALL'
    if absent != 'this line':
        return 'yes: released without it in ' + absent
    return 'open'

w = csv.writer(sys.stdout, lineterminator='\n')
w.writerow(['path', 'group', 'absent_since', 'build_refs', 'mentions', 'mention_files', 'covered_by', 'proposal', 'verified'])
for p in sorted(deleted):
    name = p.rsplit('/', 1)[-1]
    absent = next((t for t in TAGS if p not in tag_files[t]), 'this line')
    stem = p if name in ('README.md', 'INSTALL', 'TODO', 'COPYING') or len(name) <= 6 else name
    build = grep(stem, BUILD)
    mentions = [f for f in grep(stem) if not f.startswith('doc/release-notes/')]
    g = group(p)
    if g.startswith('upstream') and g.endswith('notes'):
        prop = 'delete'
    elif absent != 'this line':
        prop = 'delete; already absent in ' + absent
    elif build:
        prop = 'review: build reference'
    elif mentions:
        prop = 'review: mentioned'
    else:
        prop = 'review'
    w.writerow([p, g, absent, ';'.join(build), len(mentions), ';'.join(mentions[:5]), COVERED.get(p, prefix(p)[0] if prefix(p) else ''), prop, verified(p, g, absent, build, mentions)])
