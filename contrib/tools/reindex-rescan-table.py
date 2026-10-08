#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Write the recovery and wallet-maintenance option table (reindex, rescan, witness rebuild,
transaction deletion, consolidation) as CSV on stdout.

Code references are listed in ROWS as file:function[token] and verified against src/; a
reference that no longer matches is reported on stderr and the exit status is 1. The help,
man, and tests columns are derived from src/init.cpp, doc/man/zerod.1, and the test trees.

Usage: reindex-rescan-table.py [REPO] > TABLE.csv"""
import sys
if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__); sys.exit(0)
import csv, re, subprocess, sys, pathlib

repo = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
ROWS = [
 ('reindex', 'chain', 'init.cpp:AppInit2[fReindex = GetBoolArg]; init.cpp:ThreadImport[ReindexResumeStartFile]; txdb.cpp:CBlockTreeDB::WriteReindexing; init.cpp:ThreadImport[LoadExternalBlockFile]'),
 ('rescan', 'wallet', 'init.cpp:AppInit2[ScanForWalletTransactions(pindexRescan]; wallet.cpp:CWallet::ScanForWalletTransactions'),
 ('walletwitness', 'wallet', 'init.cpp:ThreadImport[RebuildWitnessCacheForChainTip]; wallet.cpp:CWallet::RebuildWitnessCacheForChainTip'),
 ('walletwitnessnote', 'wallet', 'wallet.cpp:CWallet::IsWitnessNoteIndexEnabled[-walletwitnessnote]'),
 ('zapwallettxes', 'wallet', 'init.cpp:AppInit2[-zapwallettxes]'),
 ('salvagewallet', 'wallet', 'init.cpp:AppInit2[-salvagewallet]; wallet.cpp:CWallet::Verify[-salvagewallet]'),
 ('deletetx', 'wallet', 'init.cpp:AppInit2[-deletetx]; wallet.cpp:CWallet::DeleteWalletTransactions'),
 ('deleteinterval', 'wallet', 'init.cpp:AppInit2[-deleteinterval]; wallet.cpp:CWallet::DeleteWalletTransactions'),
 ('keeptxnum', 'wallet', 'init.cpp:AppInit2[-keeptxnum]; wallet.cpp:CWallet::DeleteWalletTransactions'),
 ('keeptxfornblocks', 'wallet', 'init.cpp:AppInit2[-keeptxfornblocks]; wallet.cpp:CWallet::DeleteWalletTransactions'),
 ('deleteconflicttx', 'wallet', 'init.cpp:AppInit2[-deleteconflicttx]'),
 ('consolidation', 'wallet', 'init.cpp:AppInit2[-consolidation]; asyncrpcoperation_saplingconsolidation.cpp:AsyncRPCOperation_saplingconsolidation::main_impl'),
 ('consolidationtxfee', 'wallet', 'init.cpp:AppInit2[-consolidationtxfee]'),
 ('consolidatesaplingaddress', 'wallet', 'init.cpp:AppInit2[-consolidatesaplingaddress]; asyncrpcoperation_saplingconsolidation.cpp:AsyncRPCOperation_saplingconsolidation::main_impl'),
]

def git(*a):
    return subprocess.run(['git', '-C', str(repo)] + list(a), capture_output=True, text=True).stdout

def find(fname):
    hits = [l for l in git('ls-files', 'src').splitlines() if l.endswith('/' + fname)]
    hits = [h for h in hits if '/test/' not in h and '/bench/' not in h and '/gtest/' not in h]
    return min(hits, key=len) if hits else None

errors = []
def verify(refs):
    for ref in refs.split('; '):
        m = re.match(r'([^:]+):([A-Za-z0-9_:]+)(?:\[(.*)\])?$', ref)
        f, fn, tok = m.group(1), m.group(2), m.group(3)
        path = find(f)
        text = (repo / path).read_text(errors='replace') if path else ''
        short = fn.split('::')[-1]
        if not re.search(r'\b%s\s*\(' % re.escape(short), text):
            errors.append('%s: function %s not in %s' % (ref, fn, f))
        if tok and tok not in text:
            errors.append('%s: token not in %s' % (ref, f))

man = (repo / 'doc/man/zerod.1').read_text(errors='replace')
w = csv.writer(sys.stdout, lineterminator='\n')
w.writerow(['option', 'area', 'code_refs', 'help', 'man', 'tests'])
for opt, area, refs in ROWS:
    verify(refs)
    help_ = 'y' if git('grep', '-l', 'HelpMessageOpt("-%s' % opt, '--', 'src/init.cpp').strip() else 'n'
    in_man = 'y' if re.search(r'\\-%s\b' % re.escape(opt), man) else 'n'
    tests = sorted(set(p.rsplit('/', 1)[-1] for p in git('grep', '-l', '-E', r'"-%s(=|")' % re.escape(opt), '--',
                     'qa/rpc-tests', 'src/test', 'src/gtest', 'src/wallet/gtest').splitlines()))
    w.writerow(['-' + opt, area, refs, help_, in_man, ' '.join(tests)])
for e in errors:
    print('REF', e, file=sys.stderr)
sys.exit(1 if errors else 0)
