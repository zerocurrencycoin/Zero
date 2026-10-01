#!/usr/bin/env python3
"""Shared debug.log path spec, rotation names, and live-datadir write guard.

Path spec (extract_measures.py, stall_check.py):
  --datadir DIR     DIR/debug.log
  --rotated         also rotation siblings in DIR and in directory operands
  --log SPEC        repeatable file, directory, or glob
  positional SPEC   same as --log

Rotation names (--rotated only; not other *.log):
  debug.log.N     Bitcoin / logrotate
  debugN.log      Zero (debug10.log, ...)
  debug.N.log

Write guard (launchers via datadir_guard.sh):
  Refuses default runtime datadir and the product tree as a writable LAB/scratch.
  Override: ZERO_PERF_ALLOW_LIVE_DATADIR=1 or --allow-live-datadir
  (prints a warning; can destroy the live node).

Usage:
  python3 contrib/perf/debuglog.py --self-test
  python3 contrib/perf/debuglog.py --list --datadir DIR [--rotated] [--log SPEC ...]
  python3 contrib/perf/debuglog.py --guard-write [--allow-live-datadir] --label LAB PATH
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zeropaths as _zeropaths  # noqa: E402
from typing import Iterable, Optional

ROTATED_NAME_RE = re.compile(
    r"^(?:debug\.log\.\d+|debug\d+\.log|debug\.\d+\.log)$"
)

_ENV_ALLOW = "ZERO_PERF_ALLOW_LIVE_DATADIR"


def resolve_path(p: Path) -> Path:
    try:
        return p.resolve()
    except OSError:
        return p


def default_runtime_datadirs() -> list[Path]:
    """THIS platform's default datadir spellings -- not every platform's.

    Delegates to zeropaths.py, which mirrors GetDefaultDataDir(). Returning
    other platforms' paths here previously made a macOS host treat the Unix
    `~/.zero` as live, and a self-test iterating the list created and moved a
    directory belonging to no platform in use.
    """
    return list(_zeropaths.datadir_variants())


def product_roots() -> list:
    """The product tree(s) a lab must never write into.

    An explicit ZERO_PRODUCT_TREE wins. Otherwise the product tree is found
    from git: this checkout is a worktree of it, so the parent of the common
    git directory is the product tree whatever its directory is called. A
    hard-coded default path stopped protecting anything when the tree was
    renamed. When this checkout is the main clone there is no separate
    product tree, and the list is empty.
    """
    raw = os.environ.get("ZERO_PRODUCT_TREE")
    if raw:
        return [Path(raw)]
    roots = []
    here = Path(__file__).resolve().parent
    try:
        import subprocess
        out = subprocess.run(
            ["git", "-C", str(here), "rev-parse", "--path-format=absolute",
             "--git-common-dir", "--show-toplevel"],
            capture_output=True, text=True, timeout=10, check=True).stdout.split()
        common, top = Path(out[0]), Path(out[1])
        product = common.parent
        # When this checkout IS the main tree there is no separate product
        # tree to protect; protecting ourselves would refuse every lab path.
        if resolve_path(product) != resolve_path(top):
            roots.append(product)
    except Exception:
        pass
    return roots


def _is_under(path: Path, root: Path) -> bool:
    try:
        resolve_path(path).relative_to(resolve_path(root))
        return True
    except ValueError:
        return False


def live_kind(path: Path) -> Optional[str]:
    """Return 'runtime', 'product', or None.

    'runtime' covers EVERY plausible production datadir name, not just the one
    this platform would create. A `~/.zero` on a macOS host is not what zerod
    makes there, but it is very plausibly a real datadir copied from a Linux
    box -- and the incident this guards against was an attempt to delete a
    production datadir, not a mis-mapped path. Protection is deliberately
    wider than platform detection (zeropaths.is_protected_datadir).
    """
    if _zeropaths.is_protected_datadir(path):
        return "runtime"
    for root in product_roots():
        if _is_under(path, root):
            return "product"
    return None


def is_default_runtime_datadir(path: Path) -> bool:
    return live_kind(path) == "runtime"


def allow_live_datadir(flag: bool = False) -> bool:
    if flag:
        return True
    v = os.environ.get(_ENV_ALLOW, "")
    return v in ("1", "true", "yes", "YES")


def guard_write(path: Path, *, allow_live: bool = False, label: str = "LAB") -> None:
    kind = live_kind(path)
    if kind is None:
        return
    resolved = resolve_path(path)
    if allow_live_datadir(allow_live):
        print(
            f"WARNING: {_ENV_ALLOW} set; {label} is live ({kind}): {resolved}",
            file=sys.stderr,
        )
        return
    raise SystemExit(
        f"ERROR: {label} must not be a live datadir ({kind}): {resolved}\n"
        f"Use a disposable scratch path, or set {_ENV_ALLOW}=1 "
        f"(or pass --allow-live-datadir) if you intend to write here."
    )


def is_rotated_debug_name(name: str) -> bool:
    return bool(ROTATED_NAME_RE.fullmatch(name))


def list_datadir_logs(datadir: Path, rotated: bool) -> list[Path]:
    """DIR/debug.log, plus rotation siblings when rotated."""
    if not datadir.is_dir():
        raise SystemExit(f"ERROR: not a directory: {datadir}")
    found: list[Path] = []
    primary = datadir / "debug.log"
    if primary.is_file():
        found.append(primary)
    if rotated:
        for p in datadir.iterdir():
            if p.is_file() and is_rotated_debug_name(p.name):
                found.append(p)
        found.sort(key=lambda p: (p.stat().st_mtime, p.name))
    if not found:
        hint = " (try --rotated)" if not rotated else ""
        raise SystemExit(f"ERROR: no debug.log under {datadir}{hint}")
    return _dedupe(found)


def _has_glob(spec: str) -> bool:
    return any(ch in spec for ch in "*?[")


def expand_spec(spec: str, rotated: bool) -> list[Path]:
    if _has_glob(spec):
        matches = [Path(p) for p in sorted(glob.glob(spec))]
        if not matches:
            raise SystemExit(f"ERROR: glob matched nothing: {spec}")
        out: list[Path] = []
        for p in matches:
            if p.is_dir():
                out.extend(list_datadir_logs(p, rotated))
            elif p.is_file():
                out.append(p)
        if not out:
            raise SystemExit(f"ERROR: glob matched no files: {spec}")
        return _dedupe(out)
    p = Path(spec)
    if p.is_dir():
        return list_datadir_logs(p, rotated)
    if p.is_file():
        return [p]
    raise SystemExit(f"ERROR: not a file or directory: {p}")


def _dedupe(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        key = resolve_path(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def resolve_log_paths(
    *,
    datadir: Optional[Path] = None,
    rotated: bool = False,
    logs: Optional[Iterable[Path | str]] = None,
) -> list[Path]:
    """Combine --datadir / --rotated / --log / positional specs, oldest-first inside a datadir."""
    out: list[Path] = []
    if datadir is not None:
        out.extend(list_datadir_logs(datadir, rotated))
    for spec in logs or []:
        out.extend(expand_spec(str(spec), rotated))
    out = _dedupe(out)
    if not out:
        raise SystemExit("ERROR: provide --datadir, --log, and/or .log paths")
    return out


def add_log_input_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "logs",
        nargs="*",
        type=Path,
        help="Log file, datadir, or glob (same as --log)",
    )
    p.add_argument(
        "--log",
        dest="log_specs",
        action="append",
        default=[],
        metavar="SPEC",
        help="File, directory, or glob; repeatable. Explicit files need not be named debug.log",
    )
    p.add_argument(
        "--datadir",
        type=Path,
        help="Read DIR/debug.log (default runtime datadir allowed; read-only)",
    )
    p.add_argument(
        "--rotated",
        action="store_true",
        help="With --datadir or a directory operand, also read rotation siblings "
        "(debug.log.N, debugN.log, debug.N.log); not other *.log",
    )


def paths_from_args(args: argparse.Namespace) -> list[Path]:
    specs = list(args.log_specs) + [str(p) for p in args.logs]
    return resolve_log_paths(datadir=args.datadir, rotated=args.rotated, logs=specs)


def run_self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="debuglog-") as td:
        d = Path(td)
        (d / "debug.log").write_text("primary\n")
        (d / "debug.log.1").write_text("btc1\n")
        (d / "debug10.log").write_text("zero10\n")
        (d / "debug.2.log").write_text("dot2\n")
        (d / "notes.log").write_text("other\n")
        (d / "debug.log.snapshot").write_text("snap\n")

        only = list_datadir_logs(d, rotated=False)
        assert [p.name for p in only] == ["debug.log"], only

        rot = list_datadir_logs(d, rotated=True)
        names = {p.name for p in rot}
        assert "debug.log" in names
        assert "debug.log.1" in names
        assert "debug10.log" in names
        assert "debug.2.log" in names
        assert "notes.log" not in names
        assert "debug.log.snapshot" not in names

        globbed = expand_spec(str(d / "*.log"), rotated=False)
        glob_names = {p.name for p in globbed}
        assert "notes.log" in glob_names
        assert "debug.log" in glob_names
        assert "debug.log.1" not in glob_names  # suffix .1, not .log

        snap = expand_spec(str(d / "debug.log.snapshot"), rotated=False)
        assert snap[0].name == "debug.log.snapshot"

        via_dir = resolve_log_paths(logs=[d], rotated=False)
        assert via_dir[0].name == "debug.log"

        guard_write(d, label="LAB")

        # observed_runtime reads the node's own lines, last startup only.
        lg = d / "obs.log"
        lg.write_text("t Zero version v1\nt Using 14 threads for script verification\n"
                      "t Zero version v2\nt Using 4 threads for script verification\n"
                      "t Wallet disabled!\n", encoding="utf-8")
        assert observed_runtime(lg) == {"disablewallet": "1", "script_threads": "4"}, \
            observed_runtime(lg)
        lg.write_text("t Zero version v1\nt Using 0 threads for script verification\n",
                      encoding="utf-8")
        assert observed_runtime(lg) == {"script_threads": "0"}, observed_runtime(lg)

        # effective_runtime: conf keys, command line overrides, plumbing dropped.
        cf = d / "zero.conf"
        cf.write_text("rpcuser=x\ninsightexplorer=1\ndbcache=512\n# par=9\npar=2\n",
                      encoding="utf-8")
        eff = effective_runtime(cf, "-disablewallet -reindex -par=4 -rpcport=1")
        assert eff == {"insightexplorer": "1", "dbcache": "512", "par": "4",
                       "disablewallet": "1"}, eff
        # check_runtime: agreement passes; each disagreement is named.
        lg.write_text("t Zero version v1\nt Using 4 threads for script verification\n"
                      "t Cache configuration:\nt * Using 384.0MiB for block index database\n"
                      "t * Using 40.0MiB for chain state database\n"
                      "t * Using 88.0MiB for in-memory UTXO set\nt Wallet disabled!\n",
                      encoding="utf-8")
        obs = observed_runtime(lg)
        assert check_runtime(eff, obs) == [], check_runtime(eff, obs)
        assert len(check_runtime(dict(eff, par="7"), obs)) == 1
        assert len(check_runtime(dict(eff, dbcache="800"), obs)) == 1
        assert len(check_runtime({k: v for k, v in eff.items() if k != "disablewallet"}, obs)) == 1
        assert check_runtime(dict(eff, par="0"), obs) == []   # auto width: not checked

        fake_allow = d / "not-live"
        fake_allow.mkdir()
        os.environ.pop(_ENV_ALLOW, None)
        guard_write(fake_allow, allow_live=True, label="LAB")

        # The guard's whole purpose is REFUSING a live datadir. Passing on a
        # scratch path proves nothing on its own -- a guard that never fires
        # would pass every assertion above. Each live location is therefore
        # asserted to raise, and the override asserted to let it through.
        import contextlib
        import io

        # The product root must resolve to something that exists when not
        # overridden: a stale default path is refused by prefix and so passes
        # the loop below while protecting nothing (a product-tree
        # rename went unnoticed that way). Only a worktree has one.
        # A worktree (.git is a file) always has a product tree; an empty
        # list there means detection failed and the guard would be silent.
        top = Path(__file__).resolve().parents[2]
        if (top / ".git").is_file() and not os.environ.get("ZERO_PRODUCT_TREE"):
            assert product_roots(), "worktree but no product tree detected"
        if not os.environ.get("ZERO_PRODUCT_TREE") and product_roots():
            assert any(r.is_dir() for r in product_roots()), \
                f"no product root exists: {product_roots()}"
        live_dirs = list(default_runtime_datadirs()) + product_roots()
        checked = 0
        quiet = contextlib.redirect_stderr(io.StringIO())  # expected WARNINGs
        for live in live_dirs:
            if live is None:
                continue
            target = Path(live) / "scratch-probe"
            assert live_kind(target) is not None, f"not classified live: {target}"
            os.environ.pop(_ENV_ALLOW, None)
            try:
                guard_write(target, label="LAB")
            except SystemExit:
                checked += 1
            else:
                raise AssertionError(f"guard did NOT refuse a live datadir: {target}")

            # Explicit override must be honoured, or the escape hatch is broken.
            with quiet:
                guard_write(target, allow_live=True, label="LAB")

            # Env override must be honoured too -- launchers use this form.
            os.environ[_ENV_ALLOW] = "1"
            try:
                with quiet:
                    guard_write(target, label="LAB")
            finally:
                os.environ.pop(_ENV_ALLOW, None)
        assert checked > 0, "no live datadir was exercised; guard is untested"

        # A path merely *resembling* a live datadir by name must not be refused.
        lookalike = d / "Application Support" / "zero"
        lookalike.mkdir(parents=True)
        guard_write(lookalike, label="LAB")

    print("self-test OK")
    return 0


_RE_SCRIPT_THREADS = re.compile(r"Using (\d+) threads for script verification")
_RE_CACHE_MIB = re.compile(r"\* Using ([0-9.]+)MiB for ")

# Runtime keys that change what a measurement means. Recorded from the conf the
# node read plus its command line; everything else in a conf is RPC plumbing.
RUNTIME_KEYS = ("disablewallet", "par", "dbcache", "experimentalfeatures",
                "insightexplorer", "txindex", "zindex", "equihashsolver",
                "walletwitness", "walletwitnessnote", "rpcthreads",
                "rpcworkqueue", "perffdcache", "perfbufsize")
DEFAULT_DBCACHE_MIB = 800   # nDefaultDbCache, src/txdb.h
MAX_SCRIPT_THREADS = 16     # MAX_SCRIPTCHECK_THREADS, src/main.h


def _kv(token: str):
    token = token.strip().lstrip("-")
    if not token or token.startswith("#"):
        return None
    k, _, v = token.partition("=")
    return k.strip(), (v.strip() if _ else "1")


def effective_runtime(conf: Optional[Path], zerod_args: str = "") -> dict:
    """RUNTIME_KEYS as the node received them: conf file, then command line.

    The command line overrides the conf, as in zerod. Keys absent from both are
    omitted rather than filled with defaults, so a row states what was set.
    """
    out = {}
    if conf and Path(conf).is_file():
        for line in Path(conf).read_text(encoding="utf-8", errors="replace").splitlines():
            kv = _kv(line)
            if kv and kv[0] in RUNTIME_KEYS:
                out[kv[0]] = kv[1]
    for tok in zerod_args.split():
        kv = _kv(tok) if tok.startswith("-") else None
        if kv and kv[0] in RUNTIME_KEYS:
            out[kv[0]] = kv[1]
    return out


def check_runtime(effective: dict, observed: dict) -> list:
    """Mismatches between what was set and what the node's log shows."""
    bad = []
    wallet_off = effective.get("disablewallet", "0") not in ("0", "")
    if wallet_off != (observed.get("disablewallet") == "1"):
        bad.append("disablewallet set=%d observed=%s" % (wallet_off, observed.get("disablewallet", "absent")))
    par = effective.get("par")
    if par is not None and par.lstrip("-").isdigit() and int(par) >= 1:
        n = int(par)
        want = 0 if n == 1 else min(n, MAX_SCRIPT_THREADS)
        if observed.get("script_threads") != str(want):
            bad.append("par=%d expects %d script threads, observed=%s"
                       % (n, want, observed.get("script_threads", "absent")))
    want_cache = int(effective.get("dbcache", DEFAULT_DBCACHE_MIB))
    got = observed.get("dbcache_mib")
    if got is not None and abs(int(got) - want_cache) > 1:
        bad.append("dbcache set=%d observed=%s MiB" % (want_cache, got))
    return bad


def observed_runtime(log: Path) -> dict:
    """Runtime state as the node reported it, from its own startup lines.

    A launcher declares the flags it passed; this is what the node actually
    did, so a record can be refused when the two disagree. Only the last
    startup in the file counts: a reused datadir holds earlier runs.
    """
    wallet_disabled = None
    threads = None
    cache = None
    with open(log, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "Zero version" in line or "Zcash version" in line:
                wallet_disabled, threads, cache = None, None, None
            m = _RE_SCRIPT_THREADS.search(line)
            if m:
                threads = int(m.group(1))
            if "Wallet disabled!" in line:
                wallet_disabled = True
            if "Cache configuration:" in line:
                cache = 0.0
            m = _RE_CACHE_MIB.search(line)
            if m and cache is not None:
                cache += float(m.group(1))
    out = {}
    if wallet_disabled is not None:
        out["disablewallet"] = "1" if wallet_disabled else "0"
    if threads is not None:
        out["script_threads"] = str(threads)
    if cache is not None:
        out["dbcache_mib"] = str(int(round(cache)))
    return out


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--list", action="store_true", help="Print resolved log paths")
    p.add_argument("--guard-write", metavar="PATH", help="Refuse live datadir unless allowed")
    p.add_argument("--label", default="LAB")
    p.add_argument(
        "--allow-live-datadir",
        action="store_true",
        help=f"Override write refuse (same as {_ENV_ALLOW}=1)",
    )
    p.add_argument("--is-live", metavar="PATH", help="Exit 0 if runtime or product tree")
    p.add_argument("--is-runtime", metavar="PATH", help="Exit 0 if default runtime datadir")
    p.add_argument("--observed-runtime", metavar="LOG",
                   help="Print key=value runtime state the node reported in LOG")
    p.add_argument("--check-runtime", metavar="LOG",
                   help="Print the effective runtime (--conf + --zerod-args) as key=value; "
                        "exit 1 if LOG shows the node did not apply it")
    p.add_argument("--conf", metavar="PATH", help="with --check-runtime: the zero.conf the node read")
    p.add_argument("--zerod-args", default="", help="with --check-runtime: zerod's command line")
    add_log_input_args(p)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.self_test:
        return run_self_test()
    if args.is_runtime is not None:
        return 0 if is_default_runtime_datadir(Path(args.is_runtime)) else 1
    if args.is_live is not None:
        return 0 if live_kind(Path(args.is_live)) is not None else 1
    if args.check_runtime is not None:
        eff = effective_runtime(Path(args.conf) if args.conf else None, args.zerod_args)
        bad = check_runtime(eff, observed_runtime(Path(args.check_runtime)))
        for k, v in sorted(eff.items()):
            print(f"{k}={v}")
        for b in bad:
            print("runtime mismatch: " + b, file=sys.stderr)
        return 1 if bad else 0
    if args.observed_runtime is not None:
        for k, v in sorted(observed_runtime(Path(args.observed_runtime)).items()):
            print(f"{k}={v}")
        return 0
    if args.guard_write is not None:
        guard_write(
            Path(args.guard_write),
            allow_live=args.allow_live_datadir,
            label=args.label,
        )
        return 0
    if args.list or args.datadir or args.logs or args.log_specs:
        for p in paths_from_args(args):
            print(p)
        return 0
    build_arg_parser().error("use --self-test, --list, --guard-write, --is-live, or --is-runtime")
    return 2


if __name__ == "__main__":
    sys.exit(main())
