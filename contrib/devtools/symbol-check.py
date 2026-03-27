#!/usr/bin/env python3
# Copyright (c) 2014 Wladimir J. van der Laan
# Copyright (c) 2016-2019 The Zcash developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .
'''
A script to check that the (Linux) executables only contain allowed gcc, glibc
and libstdc++ version symbols.  This makes sure they are compatible with the
minimum supported Linux distribution versions.

Example usage:

    python contrib/devtools/symbol-check.py src/zerod src/zero-cli src/zero-tx
'''
from __future__ import division, print_function
import subprocess
import re
import sys
import os

# Ubuntu 24.04 LTS (Noble) target:
#   glibc 2.39, libstdc++ (GCC 14) GLIBCXX 3.4.33, CXXABI 1.3.15
#
MAX_VERSIONS = {
    'GCC':     (4, 4, 0),
    'CXXABI':  (1, 3, 15),
    'GLIBCXX': (3, 4, 33),
    'GLIBC':   (2, 39)
}
# See here for a description of _IO_stdin_used:
# https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=634261#109

# Ignore symbols that are exported as part of every executable
IGNORE_EXPORTS = {
'_edata', '_end', '_init', '__bss_start', '_fini', '_IO_stdin_used'
}

# Demangled prefixes for common C++ runtime exports (stdlib, iostreams, RTTI, vtables).
# These are expected when building without -fvisibility=hidden and are not a compatibility concern.
IGNORE_EXPORT_PREFIXES = (
    'std::', 'void std::', 'typeinfo for ', 'vtable for ', 'VTT for ',
    '__libc_', 'in6addr_', 'stdin', 'stdout', 'stderr',
)
READELF_CMD = os.getenv('READELF', '/usr/bin/readelf')
CPPFILT_CMD = os.getenv('CPPFILT', '/usr/bin/c++filt')
# Allowed NEEDED libraries
ALLOWED_LIBRARIES = {
# zerod
'libgcc_s.so.1', # GCC base support
'libc.so.6', # C library
'libstdc++.so.6', # C++ standard library
'libpthread.so.0', # threading
'libanl.so.1', # DNS resolve
'libm.so.6', # math library
'librt.so.1', # real-time (clock)
'libgomp.so.1', # OpenMP support library
'ld-linux-x86-64.so.2', # 64-bit dynamic linker
'ld-linux.so.2', # 32-bit dynamic linker
'libdl.so.2' # programming interface to dynamic linker
}

class CPPFilt(object):
    '''
    Demangle C++ symbol names.

    Use a pipe to the 'c++filt' command.
    '''
    def __init__(self):
        self.proc = subprocess.Popen(CPPFILT_CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def __call__(self, mangled):
        data = (mangled + '\n').encode('utf-8') if isinstance(mangled, str) else mangled + b'\n'
        self.proc.stdin.write(data)
        self.proc.stdin.flush()
        result = self.proc.stdout.readline().rstrip()
        return result.decode('utf-8') if isinstance(result, bytes) else result

    def close(self):
        self.proc.stdin.close()
        self.proc.stdout.close()
        self.proc.wait()

def read_symbols(executable, imports=True):
    '''
    Parse an ELF executable and return a list of (symbol,version) tuples
    for dynamic, imported symbols.
    '''
    p = subprocess.Popen([READELF_CMD, '--dyn-syms', '-W', executable], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    if p.returncode:
        raise IOError('Could not read symbols for %s: %s' % (executable, stderr.strip()))
    if isinstance(stdout, bytes):
        stdout = stdout.decode()
    syms = []
    for line in stdout.split('\n'):
        line = line.split()
        if len(line)>7 and re.match('[0-9]+:$', line[0]):
            (sym, _, version) = line[7].partition('@')
            is_import = line[6] == 'UND'
            if version.startswith('@'):
                version = version[1:]
            if is_import == imports:
                syms.append((sym, version))
    return syms

def check_version(max_versions, version):
    if '_' in version:
        (lib, _, ver) = version.rpartition('_')
    else:
        lib = version
        ver = '0'
    ver = tuple([int(x) for x in ver.split('.')])
    if not lib in max_versions:
        return False
    return ver <= max_versions[lib]

def read_libraries(filename):
    p = subprocess.Popen([READELF_CMD, '-d', '-W', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    (stdout, stderr) = p.communicate()
    if p.returncode:
        raise IOError('Error opening file')
    if isinstance(stdout, bytes):
        stdout = stdout.decode()
    libraries = []
    for line in stdout.split('\n'):
        tokens = line.split()
        if len(tokens)>2 and tokens[1] == '(NEEDED)':
            match = re.match(r'^Shared library: \[(.*)\]$', ' '.join(tokens[2:]))
            if match:
                libraries.append(match.group(1))
            else:
                raise ValueError('Unparseable (NEEDED) specification')
    return libraries

if __name__ == '__main__':
    cppfilt = CPPFilt()
    retval = 0
    for filename in sys.argv[1:]:
        # Check imported symbols
        for sym,version in read_symbols(filename, True):
            if version and not check_version(MAX_VERSIONS, version):
                print('%s: symbol %s from unsupported version %s' % (filename, cppfilt(sym), version))
                retval = 1
        # Check exported symbols
        for sym,version in read_symbols(filename, False):
            if sym in IGNORE_EXPORTS:
                continue
            demangled = cppfilt(sym)
            if demangled.startswith(IGNORE_EXPORT_PREFIXES):
                continue
            print('%s: export of symbol %s not allowed' % (filename, demangled))
            retval = 1
        # Check dependency libraries
        for library_name in read_libraries(filename):
            if library_name not in ALLOWED_LIBRARIES:
                print('%s: NEEDED library %s is not allowed' % (filename, library_name))
                retval = 1

    exit(retval)


