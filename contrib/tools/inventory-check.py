#!/usr/bin/env python3
# Copyright 2026 Zero Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php.
"""Check doc/RPCs.csv and doc/Options.csv against the RPC tables and option parsing in src/.

Modes (combine as needed; without a mode the script only reports differences):
  --apply        append rows for RPCs and options found in src/ but missing from the files
  --disposition  rewrite the disposition column of doc/RPCs.csv from the RPC tables and help text
  --audit        list presence cells (bitcoin, zcash, pirate) that disagree with upstream source trees
  --upstream DIR directory holding bitcoin-src, zcash, and pirate checkouts (env ZERO_UPSTREAM);
                 needed by --apply and --audit

Dispositions: supported; deprecated (help text starts with DEPRECATED or says the command is
depreciated); experimental (upstream runtime gate fExperimentalMode or an "Experimental" table
category); hidden (table category "hidden"); compiled-out (registered only with ENABLE_ZCRAW_RPC);
removed (handler kept, table entry commented out).
"""
import argparse, csv, os, pathlib, re, subprocess, sys

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('repo', nargs='?', default='.')
ap.add_argument('--apply', action='store_true')
ap.add_argument('--disposition', action='store_true')
ap.add_argument('--audit', action='store_true')
ap.add_argument('--upstream', default=os.environ.get('ZERO_UPSTREAM', ''))
args = ap.parse_args()
repo = pathlib.Path(args.repo)
RPCS, OPTS = repo / 'doc/RPCs.csv', repo / 'doc/Options.csv'
CLI_TX = ('src/bitcoin-cli.cpp', 'src/bitcoin-tx.cpp')
REMOVED = {'zcrawkeygen'}

def git_grep(pattern, *paths, cwd=None):
    r = subprocess.run(['git', '-C', str(cwd or repo), 'grep', '-n', '-E', pattern, '--'] + list(paths),
                       capture_output=True, text=True)
    return r.stdout.splitlines()

def skip(f):
    return f in CLI_TX or '/test/' in f or '/gtest/' in f

# RPC tables: { "category", "name", &handler, okSafe }, with the enclosing #if conditions.
rpc = {}
for f in sorted(set(l.split(':')[0] for l in git_grep(r'\{ *"[^"]+", *"[A-Za-z0-9_]+", *&', 'src'))):
    if skip(f):
        continue
    stack = []
    for line in (repo / f).read_text(errors='replace').splitlines():
        s = line.strip()
        if s.startswith('//'):
            continue
        m = re.match(r'#\s*if(n?def)?\s+(.*)', s)
        if m:
            stack.append(m.group(2).strip()); continue
        if s.startswith('#endif') and stack:
            stack.pop(); continue
        if s.startswith('#else') and stack:
            stack[-1] = 'not ' + stack[-1]; continue
        m = re.search(r'\{ *"([^"]+)", *"([A-Za-z0-9_]+)", *&([A-Za-z0-9_:]+)', line)
        if m:
            rpc[m.group(2)] = (m.group(1), f, ' && '.join(stack), m.group(3))

help_opts, parsed = {}, set()
for l in git_grep(r'HelpMessageOpt\("-[a-z0-9-]+', 'src'):
    f = l.split(':')[0]
    if not skip(f):
        for o in re.findall(r'HelpMessageOpt\("-([a-z0-9-]+)', l):
            help_opts[o] = f
for l in git_grep(r'(GetArg|GetBoolArg|mapArgs\.count|mapArgs\[|mapMultiArgs\[|mapMultiArgs\.count|SoftSetArg|SoftSetBoolArg|IsArgSet)\("-[a-z0-9-]+', 'src'):
    if not skip(l.split(':')[0]):
        parsed.update(re.findall(r'"-([a-z0-9-]+)"', l))

def load(p, key):
    with p.open() as fh:
        rows = list(csv.DictReader(fh))
    return rows, {r[key]: r for r in rows}

def save(p, rows):
    hdr = list(rows[0].keys())
    tmp = p.with_suffix('.tmp')
    with tmp.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, lineterminator='\n')
        w.writeheader(); w.writerows(rows)
    tmp.replace(p)

rpc_rows, rows = load(RPCS, 'rpc')
opt_rows, opts = load(OPTS, 'option')
print('== %s: %d registered RPCs, %d rows, %d zero=y' % (RPCS, len(rpc), len(rows), sum(r['zero'] == 'y' for r in rows.values())))
for n in sorted(rpc):
    if n not in rows:
        print('MISSING_ROW', n, rpc[n][1], rpc[n][2])
for n, r in sorted(rows.items()):
    if r['zero'] == 'y' and n not in rpc:
        print('NOT_REGISTERED', n)
conv = set(re.findall(r'\{ *"([a-z_A-Z0-9]+)", *\d+ *\}', (repo / 'src/rpc/client.cpp').read_text()))
for n in sorted(conv - set(rpc) - REMOVED):
    print('CLIENT_CONVERSION_UNREGISTERED', n)
print('== %s: %d in help, %d parsed, %d rows' % (OPTS, len(help_opts), len(parsed), len(opts)))
for o in sorted(set(help_opts) | parsed):
    if o not in opts:
        print('NO_ROW', o, 'help' if o in help_opts else 'hidden')
for o, r in sorted(opts.items()):
    if o not in help_opts and o not in parsed:
        print('ROW_NOT_IN_SRC', o)

def upstream(name):
    if not args.upstream:
        sys.exit('--upstream DIR or ZERO_UPSTREAM is required for this mode')
    return pathlib.Path(args.upstream) / name

def present(name, pattern):
    return 'y' if git_grep(pattern, 'src', cwd=upstream(name)) else 'n'

UP = (('bitcoin', 'bitcoin-src'), ('zcash', 'zcash'), ('pirate', 'pirate'))

if args.apply:
    for n in sorted(rpc):
        if n not in rows:
            r = {k: '' for k in rpc_rows[0]}
            r.update({'rpc': n, 'type': rpc[n][0], 'zero': 'n' if 'ENABLE_ZCRAW' in rpc[n][2] else 'y'})
            for col, d in UP:
                r[col] = present(d, r'"%s"' % re.escape(n))
            rpc_rows.append(r); print('ADDED', n)
    save(RPCS, rpc_rows)
    for o in sorted(set(help_opts) | parsed):
        if o not in opts:
            r = {k: '' for k in opt_rows[0]}
            r.update({'option': o, 'category': 'uncategorized', 'zero': 'y'})
            for col, d in UP:
                r[col] = present(d, r'"-%s(=|")' % re.escape(o))
            opt_rows.append(r); print('ADDED', o, '(set category by hand)')
    save(OPTS, opt_rows)

def handler_text(name, fn):
    for l in git_grep(r'UniValue %s\(const UniValue' % re.escape(fn), 'src'):
        t = (repo / l.split(':')[0]).read_text(errors='replace')
        i = t.find('UniValue %s(const UniValue' % fn)
        j = t.find('\nUniValue ', i + 10)
        return t[i:j if j > 0 else len(t)]
    return ''

if args.disposition:
    counts = {}
    for r in rpc_rows:
        n = r['rpc']
        if n in REMOVED:
            d = 'removed'
        elif n not in rpc:
            d = ''
        else:
            cat, f, cond, fn = rpc[n]
            body = handler_text(n, fn)
            if 'ENABLE_ZCRAW' in cond:
                d = 'compiled-out'
            elif cat == 'hidden':
                d = 'hidden'
            elif re.search(r'"\\nDEPRECATED|"This command is depreciated', body):
                d = 'deprecated'
            elif 'fExperimentalMode' in body or 'experimental' in cat.lower():
                d = 'experimental'
            else:
                d = 'supported'
        r['disposition'] = d
        counts[d] = counts.get(d, 0) + 1
    save(RPCS, rpc_rows)
    print('DISPOSITION', counts)

if args.audit:
    for n, r in sorted(rows.items()):
        for col, d in UP:
            v = present(d, r'"%s"' % re.escape(n))
            if r[col] in ('y', 'n') and r[col] != v:
                print('RPC', n, col, 'csv=%s src=%s' % (r[col], v))
    for o, r in sorted(opts.items()):
        for col, d in UP:
            v = present(d, r'"-%s(=|")' % re.escape(o))
            if r[col] in ('y', 'n') and r[col] != v:
                print('OPT', o, col, 'csv=%s src=%s' % (r[col], v))
