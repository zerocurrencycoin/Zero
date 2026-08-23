#!/usr/bin/env python3
"""Platform mapping for Zero's default paths -- the single source of truth.

Mirrors the product exactly:

  GetDefaultDataDir()   src/util.cpp   Windows: %APPDATA%\\zero
                                       macOS:   ~/Library/Application Support/zero
                                       Unix:    ~/.zero
  ZC_GetBaseParamsDir() src/util.cpp   Windows: %APPDATA%\\ZcashParams
                                       macOS:   ~/Library/Application Support/ZcashParams
                                       Unix:    ~/.zcash-params

Why this file exists. An earlier helper returned *every* platform's candidate
path on *every* platform, so on macOS it reported `~/.zero` (a Unix path) as a
live datadir. A self-test iterating that list then created and moved a
directory that does not belong to this platform at all. One mapping, selected
by the running platform, removes that whole class of error.

Cross-platform paths remain available for the narrow case that genuinely needs
them -- scanning an archive copied from another machine -- but only via
`all_platform_datadirs()`, which is explicit about what it is.

Usage:
  python3 contrib/perf/zeropaths.py            # show this platform's mapping
  python3 contrib/perf/zeropaths.py --json
  python3 contrib/perf/zeropaths.py --self-test

Exit: 0 ok, 1 self-test failure.
"""
import json
import os
import platform
import sys
from pathlib import Path

# Directory leaf names, as the product spells them. Case matters on Linux.
DATADIR_LEAF = "zero"
PARAMS_LEAF_WIN_MAC = "ZcashParams"
PARAMS_LEAF_UNIX = ".zcash-params"


def platform_key(system=None):
    """'windows' | 'macos' | 'unix' -- the three cases util.cpp distinguishes."""
    s = (system or platform.system()).lower()
    if s.startswith("win") or s in ("cygwin", "msys"):
        return "windows"
    if s == "darwin":
        return "macos"
    return "unix"


def _appdata(env=None):
    env = os.environ if env is None else env
    return Path(env.get("APPDATA", str(Path(env.get("HOME", "~")) / "AppData" / "Roaming")))


def default_datadir(system=None, env=None, home=None):
    """The ONE default datadir for the given platform. Mirrors GetDefaultDataDir()."""
    key = platform_key(system)
    home = Path(home) if home is not None else Path((env or os.environ).get("HOME") or Path.home())
    if key == "windows":
        return _appdata(env) / DATADIR_LEAF
    if key == "macos":
        return home / "Library" / "Application Support" / DATADIR_LEAF
    return home / ("." + DATADIR_LEAF)


def default_params_dir(system=None, env=None, home=None):
    """The proving-params directory. Mirrors ZC_GetBaseParamsDir().

    Note the Windows/macOS leaf is a SIBLING of the datadir, not inside it."""
    key = platform_key(system)
    home = Path(home) if home is not None else Path((env or os.environ).get("HOME") or Path.home())
    if key == "windows":
        return _appdata(env) / PARAMS_LEAF_WIN_MAC
    if key == "macos":
        return home / "Library" / "Application Support" / PARAMS_LEAF_WIN_MAC
    return home / PARAMS_LEAF_UNIX


def datadir_variants(system=None, env=None, home=None):
    """This platform's default plus spellings the same platform may produce.

    macOS filesystems are usually case-insensitive, so `Zero` and `zero` are the
    same directory; both are listed so a case-differing argument still matches.
    Paths from OTHER platforms are deliberately excluded -- that was the bug.
    """
    key = platform_key(system)
    base = default_datadir(system, env, home)
    if key == "macos":
        return [base, base.parent / "Zero"]
    return [base]


def all_platform_datadirs(env=None, home=None):
    """EVERY platform's default datadir name, on any host.

    Two different questions are asked of these paths, and conflating them is a
    bug in either direction:

      "Which datadir would zerod use here?"   -> default_datadir()  (one path)
      "Might this path be somebody's real     -> this function      (all names)
       Zero datadir, whatever the platform?"

    Protection uses this wider set. A `~/.zero` on a macOS host is not what
    zerod would create there, but it is still very plausibly a real datadir --
    copied from a Linux box, or created by a script following Unix
    instructions. Deleting it because "that is not the macOS path" is exactly
    the failure this guards against.
    """
    out = []
    for sysname in ("Windows", "Darwin", "Linux"):
        for p in datadir_variants(sysname, env, home):
            if p not in out:
                out.append(p)
    return out


def protected_datadirs(env=None, home=None):
    """Every path that must never be written to or deleted by a lab run.

    Superset of `all_platform_datadirs`: also covers spellings a real
    deployment may use that no single platform's default names.
    """
    home_p = Path(home) if home is not None else Path(
        (env or os.environ).get("HOME") or Path.home())
    out = list(all_platform_datadirs(env, home))
    extra = [
        home_p / ".zero",                                  # Unix name, any host
        home_p / ".Zero",
        home_p / "zero",                                   # bare, seen in the wild
        home_p / "Library" / "Application Support" / "zero",
        home_p / "Library" / "Application Support" / "Zero",
        home_p / "AppData" / "Roaming" / "zero",
        home_p / "AppData" / "Roaming" / "Zero",
        home_p / "Application Data" / "zero",              # Windows < Vista
    ]
    for p in extra:
        if p not in out:
            out.append(p)
    return out


def is_protected_datadir(path, env=None, home=None):
    """True if PATH is, or is inside, ANY plausible production datadir.

    Platform-independent by design: use this for destructive-operation guards.
    `is_default_datadir` answers a different question and must not be used to
    decide whether deleting something is safe.
    """
    target = Path(path).expanduser()
    try:
        target = target.resolve()
    except OSError:
        target = target.absolute()
    for cand in protected_datadirs(env, home):
        try:
            cand_r = cand.resolve()
        except OSError:
            cand_r = cand.absolute()
        if target == cand_r or cand_r in target.parents:
            return True
    return False


def is_default_datadir(path, system=None, env=None, home=None):
    """True if PATH is, or is inside, this platform's default datadir."""
    target = Path(path).expanduser()
    try:
        target = target.resolve()
    except OSError:
        target = target.absolute()
    for cand in datadir_variants(system, env, home):
        try:
            cand_r = cand.resolve()
        except OSError:
            cand_r = cand.absolute()
        if target == cand_r or cand_r in target.parents:
            return True
    return False


def describe(system=None, env=None, home=None):
    return {
        "platform": platform_key(system),
        "datadir": str(default_datadir(system, env, home)),
        "datadir_variants": [str(p) for p in datadir_variants(system, env, home)],
        "params_dir": str(default_params_dir(system, env, home)),
        "wallet": str(default_datadir(system, env, home) / "wallet.zero"),
        "debug_log": str(default_datadir(system, env, home) / "debug.log"),
    }


def self_test():
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    H = "/home/u"
    E = {"HOME": H, "APPDATA": "C:\\Users\\u\\AppData\\Roaming"}

    # Each platform maps to exactly one datadir, matching util.cpp.
    check(str(default_datadir("Darwin", E, H)) ==
          "/home/u/Library/Application Support/zero", "macOS datadir")
    check(str(default_datadir("Linux", E, H)) == "/home/u/.zero", "Unix datadir")
    check("AppData" in str(default_datadir("Windows", E, H)) and
          str(default_datadir("Windows", E, H)).endswith("zero"), "Windows datadir")

    # Params dir is a SIBLING on Windows/macOS, not nested under the datadir.
    mac_params = default_datadir("Darwin", E, H).parent / "ZcashParams"
    check(default_params_dir("Darwin", E, H) == mac_params,
          "macOS params dir is a sibling of the datadir")
    check(str(default_params_dir("Linux", E, H)) == "/home/u/.zcash-params",
          "Unix params dir")

    # THE BUG THIS FILE EXISTS TO PREVENT: a platform must never claim another
    # platform's path as its own default.
    check(not is_default_datadir("/home/u/.zero", "Darwin", E, H),
          "macOS must NOT treat the Unix ~/.zero as its default datadir")
    check(not is_default_datadir("/home/u/Library/Application Support/zero",
                                 "Linux", E, H),
          "Linux must NOT treat the macOS path as its default datadir")
    check(is_default_datadir("/home/u/.zero", "Linux", E, H),
          "Linux recognises its own datadir")
    check(is_default_datadir("/home/u/Library/Application Support/zero",
                             "Darwin", E, H),
          "macOS recognises its own datadir")

    # Nested paths count as inside; unrelated ones do not.
    check(is_default_datadir("/home/u/.zero/blocks", "Linux", E, H),
          "a path inside the datadir is inside it")
    check(not is_default_datadir("/tmp/scratch", "Linux", E, H),
          "an unrelated scratch path is not the datadir")
    check(not is_default_datadir("/home/u/.zero-lab", "Linux", E, H),
          "a sibling with a shared prefix is NOT the datadir")

    # macOS case variant is recognised (case-insensitive filesystems).
    check(is_default_datadir("/home/u/Library/Application Support/Zero",
                             "Darwin", E, H), "macOS 'Zero' spelling matches")
    check(len(datadir_variants("Linux", E, H)) == 1,
          "Unix has exactly one spelling")

    # The cross-platform list is opt-in and complete.
    every = all_platform_datadirs(E, H)
    check(len(every) >= 3, "all_platform_datadirs covers every platform")
    check(any(".zero" in str(p) for p in every), "includes the Unix path")
    check(any("Application Support" in str(p) for p in every), "includes macOS")

    # PROTECTION is platform-independent: every plausible production datadir
    # name is gated on every host. The original incident was an attempt to
    # delete a production datadir, not merely a mis-mapped path.
    for p in ("/home/u/.zero",
              "/home/u/Library/Application Support/zero",
              "/home/u/Library/Application Support/Zero",
              "/home/u/AppData/Roaming/zero"):
        check(is_protected_datadir(p, E, H),
              "protected on every platform: %s" % p)
        check(is_protected_datadir(p + "/blocks", E, H),
              "contents are protected too: %s/blocks" % p)

    # ... including the ones this platform would NOT create itself.
    check(is_protected_datadir("/home/u/.zero", E, H)
          and not is_default_datadir("/home/u/.zero", "Darwin", E, H),
          "a non-native datadir name is protected even though it is not the "
          "platform default -- the two questions differ")

    # Scratch paths stay usable, or the lab cannot run at all.
    for p in ("/tmp/zero-lab-tiny", "/home/u/.zero-lab", "/home/u/zerowork",
              "/home/u/Work/scratch/zero-run"):
        check(not is_protected_datadir(p, E, H),
              "scratch path must remain usable: %s" % p)

    check(platform_key("Darwin") == "macos", "Darwin -> macos")
    check(platform_key("Linux") == "unix", "Linux -> unix")
    check(platform_key("Windows") == "windows", "Windows -> windows")
    check(platform_key("FreeBSD") == "unix", "unknown unix-like -> unix")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    info = describe()
    if "--json" in argv:
        print(json.dumps(info, indent=2))
    else:
        for k, v in info.items():
            if isinstance(v, list):
                v = ", ".join(v)
            print(f"{k:18} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
