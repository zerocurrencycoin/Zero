#!/usr/bin/env python3
#
# Execute all of the automated tests related to Zcash.
#

import argparse
from glob import glob
import os
import re
import subprocess
import sys

REPOROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

def repofile(filename):
    return os.path.join(REPOROOT, filename)

# Same exclusions as contrib/run-tests.sh — canonical source: qa/zcash/test_filters.sh
def _load_test_filters():
    script = repofile('qa/zcash/test_filters.sh')
    out = subprocess.check_output(
        ['bash', '-c', 'source "$1" && printf "%s\\n%s" "$BOOST_PASS_EXCLUDE" "$GTEST_PASS_EXCLUDE"', 'bash', script],
        text=True,
    ).strip().split('\n', 1)
    return out[0], out[1] if len(out) > 1 else ''

BOOST_PASS_EXCLUDE, GTEST_PASS_FILTER = _load_test_filters()


def btest_command(unfiltered):
    cmd = [repofile('src/test/test_bitcoin'), '-p']
    if not unfiltered and BOOST_PASS_EXCLUDE:
        cmd.append('--run_test=' + BOOST_PASS_EXCLUDE)
    return cmd


def gtest_command(unfiltered):
    cmd = [repofile('src/zero-gtest')]
    if not unfiltered:
        cmd.append('--gtest_filter=' + GTEST_PASS_FILTER)
    return cmd


#
# Custom test runners
#

RE_RPATH_RUNPATH = re.compile('No RPATH.*No RUNPATH')
RE_FORTIFY_AVAILABLE = re.compile('FORTIFY_SOURCE support available.*Yes')
RE_FORTIFY_USED = re.compile('Binary compiled with FORTIFY_SOURCE support.*Yes')

def test_rpath_runpath(filename):
    output = subprocess.check_output(
        [repofile('qa/zcash/checksec.sh'), '--file', repofile(filename)],
        universal_newlines=True,
    )
    if RE_RPATH_RUNPATH.search(output):
        print('PASS: %s has no RPATH or RUNPATH.' % filename)
        return True
    else:
        print('FAIL: %s has an RPATH or a RUNPATH.' % filename)
        print(output)
        return False

def test_fortify_source(filename):
    proc = subprocess.Popen(
        [repofile('qa/zcash/checksec.sh'), '--fortify-file', repofile(filename)],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    line1 = proc.stdout.readline()
    line2 = proc.stdout.readline()
    proc.terminate()
    if RE_FORTIFY_AVAILABLE.search(line1) and RE_FORTIFY_USED.search(line2):
        print('PASS: %s has FORTIFY_SOURCE.' % filename)
        return True
    else:
        print('FAIL: %s is missing FORTIFY_SOURCE.' % filename)
        return False

def _env_for_make():
    """Return env with python in PATH so security-check.py can run."""
    env = os.environ.copy()
    python_dir = None
    py = os.environ.get('PYTHON')
    if py and os.path.isabs(py) and os.path.isfile(py):
        python_dir = os.path.dirname(py)
    elif sys.executable:
        python_dir = os.path.dirname(os.path.abspath(sys.executable))
    if python_dir:
        env['PATH'] = python_dir + os.pathsep + env.get('PATH', '')
    return env


def check_security_hardening():
    ret = True

    # PIE, RELRO, Canary, and NX are tested by make check-security.
    # security-check.py uses shebang #!/usr/bin/env python; ensure python in PATH.
    ret &= subprocess.call(
        ['make', '-C', repofile('src'), 'check-security'],
        env=_env_for_make()
    ) == 0

    # The remaining checks are only for ELF binaries
    # Assume that if zerod is an ELF binary, they all are
    with open(repofile('src/zerod'), 'rb') as f:
        magic = f.read(4)
        if not magic.startswith(b'\x7fELF'):
            return ret

    ret &= test_rpath_runpath('src/zerod')
    ret &= test_rpath_runpath('src/zero-cli')
    ret &= test_rpath_runpath('src/zero-gtest')
    ret &= test_rpath_runpath('src/zero-tx')
    ret &= test_rpath_runpath('src/test/test_bitcoin')

    # NOTE: checksec.sh does not reliably determine whether FORTIFY_SOURCE
    # is enabled for the entire binary. See issue #915.
    ret &= test_fortify_source('src/zerod')
    ret &= test_fortify_source('src/zero-cli')
    ret &= test_fortify_source('src/zero-gtest')
    ret &= test_fortify_source('src/zero-tx')
    ret &= test_fortify_source('src/test/test_bitcoin')

    return ret

def ensure_nodotso_depends():
    depends_dir = os.path.join(REPOROOT, 'depends')
    arch_dir = os.path.join(depends_dir, 'x86_64-unknown-linux-gnu')
    if not os.path.isdir(arch_dir):
        arch_dirs = glob(os.path.join(depends_dir, 'x86_64-apple-darwin*'))
        if arch_dirs:
            arch_dir = arch_dirs[0]
        else:
            arch_dirs = glob(os.path.join(depends_dir, 'aarch64-apple-darwin*'))
            if arch_dirs:
                arch_dir = arch_dirs[0]

    if not os.path.isdir(arch_dir):
        print(
            "Skipping no-dot-so: no depends arch dir "
            "(run 'make' in depends/ for Linux/macOS depends build)"
        )
        return True

    exit_code = 0
    lib_dir = os.path.join(arch_dir, 'lib')
    libraries = os.listdir(lib_dir)
    for lib in libraries:
        if lib.find(".so") != -1:
            print(lib)
            exit_code = 1

    if exit_code == 0:
        print("PASS.")
    else:
        print("FAIL.")

    return exit_code == 0

def util_test():
    return subprocess.call(
        [repofile('src/test/bitcoin-util-test.py')],
        cwd=repofile('src'),
        env={'PYTHONPATH': repofile('src/test'), 'srcdir': repofile('src')}
    ) == 0


#
# Tests
#

STAGES = [
    'btest',
    'gtest',
    'sec-hard',
    'no-dot-so',
    'util-test',
    'secp256k1',
    'univalue',
    'rpc',
]

STAGE_COMMANDS = {
    'sec-hard': check_security_hardening,
    'no-dot-so': ensure_nodotso_depends,
    'util-test': util_test,
    'secp256k1': ['make', '-C', repofile('src/secp256k1'), 'check'],
    'univalue': ['make', '-C', repofile('src/univalue'), 'check'],
    'rpc': [repofile('qa/pull-tester/rpc-tests.sh')],
}


#
# Test driver
#

def run_stage(stage, unfiltered=False):
    print('Running stage %s' % stage)
    print('=' * (len(stage) + 14))
    print()

    if stage == 'btest':
        ret = subprocess.call(btest_command(unfiltered)) == 0
    elif stage == 'gtest':
        ret = subprocess.call(gtest_command(unfiltered)) == 0
    else:
        cmd = STAGE_COMMANDS[stage]
        if type(cmd) == type([]):
            ret = subprocess.call(cmd) == 0
        else:
            ret = cmd()

    print()
    print('-' * (len(stage) + 15))
    print('Finished stage %s' % stage)
    print()

    return ret

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--list-stages', dest='list', action='store_true')
    parser.add_argument('--skip', action='append', default=[], metavar='STAGE',
                        help='Skip stage (repeatable). Stages: %s' % ', '.join(STAGES))
    parser.add_argument(
        '--unfiltered',
        action='store_true',
        help='btest/gtest: no exclusions (may hang; includes suites run only under run-tests.sh --fail).',
    )
    parser.add_argument('stage', nargs='*', default=STAGES,
                        help='One of %s' % STAGES)
    args = parser.parse_args()

    if args.list:
        for s in STAGES:
            print(s)
        sys.exit(0)

    skip_set = set(args.skip)
    for s in skip_set:
        if s not in STAGES:
            print("Invalid --skip '%s' (choose from %s)" % (s, STAGES))
            sys.exit(1)

    stages_to_run = [s for s in args.stage if s not in skip_set]
    if skip_set:
        print("Skipping stages: %s" % ', '.join(sorted(skip_set)))

    unfiltered = args.unfiltered or os.environ.get('ZERO_FULL_SUITE_UNFILTERED') == '1'
    if unfiltered:
        print('Unfiltered btest/gtest (ZERO_FULL_SUITE_UNFILTERED=1 or --unfiltered)')

    passed = True
    for s in stages_to_run:
        passed &= run_stage(s, unfiltered=unfiltered)

    if not passed:
        print("!!! One or more test stages failed !!!")
        sys.exit(1)

if __name__ == '__main__':
    main()
