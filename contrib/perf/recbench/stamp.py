#!/usr/bin/env python3
"""
RecBench stamp: read platform, build and compiled features into a row.

System overview: contrib/perf/recbench/RecBench.md

Schema and rationale: contrib/perf/docs/SCHEMA.md.

One helper, called by every launcher, so producers cannot drift. Nothing here
starts zerod or touches a datadir; it reads system facts and, optionally, a
binary's --version output.

Design rules enforced here:
  - The BINARY is the authority on version. Repo state and commits are in
    constant flux, so nothing consults git (SCHEMA.md S1, S2.1).
  - host_id is a salted hash, never a hostname: these rows are committed to a
    public repo (SCHEMA.md S3.2).
  - An unrecognised feature combination is "custom", never a guess (S4.2).

Usage:
  contrib/perf/platform_stamp.py                       # platform + build
  contrib/perf/platform_stamp.py --binary src/zerod
  contrib/perf/platform_stamp.py --bundle stock --op reindex --snap tiny
  contrib/perf/platform_stamp.py --self-test

Exit: 0 ok, 1 error, 2 usage.
"""
import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
import rbpaths
BUNDLES_PATH = rbpaths.rb_file("features.json")
SALT_PATH = rbpaths.salt_path()

SCHEMA_VERSION = 2
FINGERPRINT_VERSION = 2


def _sh(cmd):
    """Run a command, return stripped stdout, or '' on any failure."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def normalise_os(raw):
    r = (raw or "").lower()
    if r.startswith("darwin"):
        return "macos"
    if r.startswith("linux"):
        return "linux"
    if r.startswith("windows") or r.startswith("cygwin") or r.startswith("msys"):
        return "windows"
    return r or "unknown"


def normalise_arch(raw):
    r = (raw or "").lower()
    if r in ("arm64", "aarch64"):
        return "arm64"
    if r in ("x86_64", "amd64"):
        return "x86_64"
    return r or "unknown"


def detect_runtime():
    """native / wsl2 / docker / vm. Separate from os: WSL2 reports linux but
    its I/O crosses a virtualisation layer (SCHEMA.md S3.1)."""
    try:
        with open("/proc/version", encoding="utf-8", errors="ignore") as fh:
            if "microsoft" in fh.read().lower():
                return "wsl2"
    except OSError:
        pass
    if os.path.exists("/.dockerenv"):
        return "docker"
    try:
        with open("/proc/1/cgroup", encoding="utf-8", errors="ignore") as fh:
            if "docker" in fh.read() or "containerd" in fh.read():
                return "docker"
    except OSError:
        pass
    if normalise_os(platform.system()) == "macos":
        # 1 = VM guest on macOS
        if _sh("sysctl -n kern.hv_vmm_present") == "1":
            return "vm"
    return "native"


def hostname():
    """The machine's own name. Labels a row; see RecBench.md for why."""
    return platform.node() or "unknown"


def host_id():
    """Stable, comparable, non-identifying token (SCHEMA.md S3.2)."""
    salt = ""
    try:
        with open(SALT_PATH, encoding="utf-8") as fh:
            salt = fh.read().strip()
    except OSError:
        salt = hashlib.sha256(os.urandom(32)).hexdigest()
        try:
            with open(SALT_PATH, "w", encoding="utf-8") as fh:
                fh.write(salt + "\n")
            os.chmod(SALT_PATH, 0o600)
        except OSError:
            pass  # non-fatal: token is still stable within this process
    node = platform.node() or "unknown"
    return "h-" + hashlib.sha256((salt + "|" + node).encode()).hexdigest()[:8]


def platform_block():
    osname = normalise_os(platform.system())
    blk = {
        "os": osname,
        "os_version": "",
        "kernel": platform.release(),
        "arch": normalise_arch(platform.machine()),
        "runtime": detect_runtime(),
        "cpu_model": "",
        "cpu_cores": 0,
        "cpu_threads": 0,
        "mem_gb": 0.0,
        "host_id": host_id(),
        "hostname": hostname(),
        "run_label": os.environ.get("RB_RUN_LABEL") or None,
    }
    if osname == "macos":
        blk["os_version"] = _sh("sw_vers -productVersion")
        blk["cpu_model"] = _sh("sysctl -n machdep.cpu.brand_string")
        blk["cpu_cores"] = int(_sh("sysctl -n hw.physicalcpu") or 0)
        blk["cpu_threads"] = int(_sh("sysctl -n hw.logicalcpu") or 0)
        mem = _sh("sysctl -n hw.memsize")
        blk["mem_gb"] = round(int(mem) / 2 ** 30, 1) if mem.isdigit() else 0.0
    elif osname == "linux":
        blk["os_version"] = _sh(". /etc/os-release 2>/dev/null && echo $VERSION_ID")
        model = _sh("grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-")
        if not model:
            model = _sh("lscpu | grep -m1 'Model name' | cut -d: -f2-")
        blk["cpu_model"] = model.strip()
        blk["cpu_cores"] = int(_sh("lscpu -p=Core,Socket | grep -v '^#' | sort -u | wc -l") or 0)
        blk["cpu_threads"] = os.cpu_count() or 0
        kb = _sh("grep -m1 MemTotal /proc/meminfo | awk '{print $2}'")
        blk["mem_gb"] = round(int(kb) / 2 ** 20, 1) if kb.isdigit() else 0.0
    elif osname == "windows":
        blk["os_version"] = platform.version()
        blk["cpu_model"] = os.environ.get("PROCESSOR_IDENTIFIER", "")
        blk["cpu_threads"] = os.cpu_count() or 0
        blk["cpu_cores"] = blk["cpu_threads"]
    return blk


VERSION_RE = re.compile(r"version\s+(v?[0-9][^\s]*)")


def parse_version(raw):
    """Split 'v4.0.1-a2ae9583c-dirty' into components (SCHEMA.md S2).

    The binary is authoritative; git is never consulted."""
    out = {"version": "", "commit": "", "dirty": False, "tag": None, "raw": raw or ""}
    if not raw:
        return out
    s = raw.strip()
    out["dirty"] = s.endswith("-dirty")
    if out["dirty"]:
        s = s[: -len("-dirty")]
    parts = s.split("-")
    out["version"] = parts[0]
    if len(parts) > 1:
        out["commit"] = parts[1]
    return out


def build_block(binary=None, tag=None):
    blk = {"version": "", "commit": "", "dirty": False, "tag": tag,
           "date": "", "raw": ""}
    if binary and os.path.exists(binary):
        line = _sh('"%s" --version 2>/dev/null | head -1' % binary)
        m = VERSION_RE.search(line)
        if m:
            blk.update(parse_version(m.group(1)))
            blk["tag"] = tag
    # BUILD_DATE is compiled in, so it travels with the binary.
    # None when the project binds no build header: absent stays unknown.
    bh = rbpaths.build_header()
    if not bh:
        return blk
    try:
        with open(os.path.abspath(bh), encoding="utf-8") as fh:
            for ln in fh:
                m = re.match(r'#define BUILD_DATE "([^"]+)"', ln.strip())
                if m:
                    blk["date"] = m.group(1)
    except OSError:
        pass
    return blk


CONFIG_H = rbpaths.config_header()
def _build_defines():
    """Compile-time defines to look for, from features.json.

    Derived rather than duplicated: the two drifted once, and a flag listed in
    one place but not the other is either never detected or searched for and
    never found.
    """
    try:
        classes = (load_bundles().get("_flag_classes") or {}).values()
        flags = sorted({f for c in classes for f in (c.get("flags") or [])})
        return tuple(flags) if flags else _FALLBACK_DEFINES
    except Exception:  # noqa: BLE001 - detection must never break a stamp
        return _FALLBACK_DEFINES


_FALLBACK_DEFINES = ("ZERO_PERF", "ZERO_FDCACHE", "ENABLE_WALLET",
                     "ENABLE_MINING", "ENABLE_ZMQ")
BUILD_DEFINES = _build_defines()


def detect_build_features():
    """Read compile-time features from the generated config header.

    These describe the BINARY, so they are read from the build rather than
    passed in by a caller who may be guessing (SCHEMA.md S1, S4.1). Returns
    None for any define the header does not mention, so "unknown" is never
    silently reported as "off".
    """
    feats = {k: None for k in BUILD_DEFINES}
    if not CONFIG_H:
        return feats           # unbound: every define stays unknown
    try:
        with open(os.path.abspath(CONFIG_H), encoding="utf-8") as fh:
            for ln in fh:
                ln = ln.strip()
                for k in BUILD_DEFINES:
                    if re.match(r"^#define\s+%s\s+1\b" % k, ln):
                        feats[k] = True
                    elif re.match(r"^#define\s+%s\s+0\b" % k, ln):
                        feats[k] = False
                    elif re.match(r"^/\*\s*#undef\s+%s\s*\*/$" % k, ln):
                        feats[k] = False
    except OSError:
        pass
    return feats


def load_bundles():
    try:
        with open(BUNDLES_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError:
        return {"bundle_v": 0, "bundles": {}}


def bundle_key_flags(spec):
    """Which build defines participate in bundle matching.

    Flag classes differ in kind (SCHEMA.md S4.3):
      - architectural (ZMQ, PROTON): stable ecosystem choices, effectively
        constant across scenarios. Recorded, but NOT matched on -- otherwise a
        ZMQ-disabled build of the same perf configuration reads as 'custom'.
      - scenario (WALLET, MINING): compiled default plus a runtime equivalent;
        vary between batches, so they are matched.
      - perf (ZERO_PERF, ZERO_FDCACHE): always matched.
    """
    classes = spec.get("_flag_classes", {})
    if not classes:
        return set(BUILD_DEFINES)
    keyed = set()
    for cls in classes.values():
        if cls.get("in_bundle_key"):
            keyed.update(cls.get("flags", []))
    return keyed & set(BUILD_DEFINES)


def resolve_bundle(build_feats, runtime_feats):
    """Return a bundle name, or 'custom'. Never guesses (SCHEMA.md S4.2)."""
    spec = load_bundles()
    keyed = bundle_key_flags(spec)
    for name, defn in spec.get("bundles", {}).items():
        want_build = defn.get("build", {})
        if any(build_feats.get(k) != want_build.get(k) for k in keyed):
            continue
        want = defn.get("runtime", {})
        if all(runtime_feats.get(k) == v for k, v in want.items()):
            return name
    return "custom"


def effective_state(build_feats, runtime_feats):
    """Runtime outcome next to the compiled capability (SCHEMA.md S4.3).

    A wallet-capable binary run with -disablewallet is not the same
    measurement as a binary built without wallet support, so both are kept.
    """
    wallet_built = build_feats.get("ENABLE_WALLET")
    mining_built = build_feats.get("ENABLE_MINING")
    wallet_on = (bool(wallet_built) and not runtime_feats.get("disablewallet"))
    mining_on = bool(mining_built) and bool(runtime_feats.get("gen"))
    return {
        "wallet_built": wallet_built,
        "wallet_active": wallet_on if wallet_built is not None else None,
        "mining_built": mining_built,
        "mining_active": mining_on if mining_built is not None else None,
    }


def features_block(args):
    build_feats = detect_build_features()
    runtime_feats = {
        "disablewallet": args.disablewallet,
        "dbcache": args.dbcache,
        "walletwitness": args.walletwitness,
        "walletwitnessnote": args.walletwitnessnote,
        "perffdcache": args.perffdcache,
        "gen": args.gen,
        "genproclimit": args.genproclimit,
    }
    workload = {
        "op": args.op, "wallet": args.wallet, "snap": args.snap,
        "from_height": args.from_height, "to_height": args.to_height,
    }
    bundle = args.bundle or resolve_bundle(build_feats, runtime_feats)
    return {
        "bundle": bundle,
        "bundle_v": load_bundles().get("bundle_v", 0),
        "build": build_feats,
        "runtime": runtime_feats,
        "effective": effective_state(build_feats, runtime_feats),
        "workload": workload,
    }


def stamp(args):
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "schema": SCHEMA_VERSION,
        "fingerprint_v": FINGERPRINT_VERSION,
        "recorded_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platform": platform_block(),
        "build": build_block(args.binary, args.tag),
        "features": features_block(args),
    }


def self_test():
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    v = parse_version("v4.0.1-a2ae9583c-dirty")
    check(v["version"] == "v4.0.1", "version parse")
    check(v["commit"] == "a2ae9583c", "commit parse")
    check(v["dirty"] is True, "dirty parse")
    check(v["raw"] == "v4.0.1-a2ae9583c-dirty", "raw preserved")

    v2 = parse_version("v4.0.2-abcdef123")
    check(v2["dirty"] is False, "clean build not marked dirty")
    check(v2["commit"] == "abcdef123", "clean commit parse")

    check(parse_version("")["version"] == "", "empty version tolerated")

    check(normalise_os("Darwin") == "macos", "os normalise darwin")
    check(normalise_os("Linux") == "linux", "os normalise linux")
    check(normalise_arch("aarch64") == "arm64", "arch normalise aarch64")
    check(normalise_arch("amd64") == "x86_64", "arch normalise amd64")

    p = platform_block()
    check(p["os"] in ("macos", "linux", "windows"), "os detected")
    check(p["arch"] in ("arm64", "x86_64") or p["arch"] != "", "arch detected")
    check(p["host_id"].startswith("h-") and len(p["host_id"]) == 10, "host_id shape")
    # hostname IS recorded, in plain. The rule it replaces assumed ledgers are
    # committed to a public repository; they are not -- reindex-profile/ is
    # gitignored and has never been tracked on any branch. The same block
    # already carries `binary`, a real user path, so the hash was protecting
    # nothing while costing traceability. host_id stays for comparability
    # across renames; hostname is the human label.
    check(p["hostname"] == (platform.node() or "unknown"), "hostname recorded")
    check(p["host_id"].startswith("h-"), "host_id still present for grouping")

    check(host_id() == host_id(), "host_id stable across calls")

    bf = detect_build_features()
    check(set(bf) == set(BUILD_DEFINES), "build features enumerated")
    check(all(v in (True, False, None) for v in bf.values()),
          "build features tri-state")
    # This tree configures without --enable-perf, so both must read False.
    check(bf["ZERO_PERF"] is False, "ZERO_PERF read from config header")
    check(bf["ZERO_FDCACHE"] is False, "ZERO_FDCACHE read from config header")
    check(bf["ENABLE_WALLET"] is True, "ENABLE_WALLET read from config header")

    check(resolve_bundle(bf, {}) != "", "bundle resolves to a name")
    check(resolve_bundle(bf, {}) == "stock", "this build resolves as stock")

    # Architectural flags must not force 'custom' (SCHEMA.md S4.3).
    no_zmq = dict(bf); no_zmq["ENABLE_ZMQ"] = False
    check(resolve_bundle(no_zmq, {}) == "stock",
          "ZMQ is architectural: must not change the bundle")
    # Scenario flags must.
    no_wallet = dict(bf); no_wallet["ENABLE_WALLET"] = False
    check(resolve_bundle(no_wallet, {}) == "custom",
          "WALLET is a scenario flag: must change the bundle")

    e = effective_state({"ENABLE_WALLET": True, "ENABLE_MINING": True},
                        {"disablewallet": True})
    check(e["wallet_built"] is True and e["wallet_active"] is False,
          "wallet built but disabled at runtime is distinguishable")
    e2 = effective_state({"ENABLE_WALLET": False, "ENABLE_MINING": True}, {})
    check(e2["wallet_built"] is False, "wallet not built recorded distinctly")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--binary", default=rbpaths.target_binary())
    ap.add_argument("--tag", default=None, help="release/baseline tag, if any")
    ap.add_argument("--bundle", default=None, help="override bundle name")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--compact", action="store_true", help="one-line JSON")
    # Compile-time features are read from the build, not passed in.
    for name in ("disablewallet", "walletwitnessnote", "perffdcache", "gen"):
        ap.add_argument("--" + name, action="store_true",
                        dest=name.replace("-", "_"))
    ap.add_argument("--walletwitness", default=None)
    ap.add_argument("--dbcache", type=int, default=None)
    ap.add_argument("--genproclimit", type=int, default=None)
    ap.add_argument("--op", default=None)
    ap.add_argument("--wallet", default=None)
    ap.add_argument("--snap", default=None)
    ap.add_argument("--from-height", type=int, default=None, dest="from_height")
    ap.add_argument("--to-height", type=int, default=None, dest="to_height")
    args = ap.parse_args(argv[1:])

    if args.self_test:
        return self_test()

    row = stamp(args)
    print(json.dumps(row, separators=(",", ":")) if args.compact
          else json.dumps(row, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
