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
  Refuses default runtime datadir and Zero400 as a writable LAB/scratch.
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
    home = Path.home()
    return [
        home / "Library" / "Application Support" / "zero",
        home / "Library" / "Application Support" / "Zero",
        home / ".zero",
        home / "AppData" / "Roaming" / "zero",
    ]


def zero400_root() -> Path:
    raw = os.environ.get("ZERO400", str(Path.home() / "Work" / "ZK" / "Zero400"))
    return Path(raw)


def _is_under(path: Path, root: Path) -> bool:
    try:
        resolve_path(path).relative_to(resolve_path(root))
        return True
    except ValueError:
        return False


def live_kind(path: Path) -> Optional[str]:
    """Return 'runtime', 'zero400', or None."""
    for d in default_runtime_datadirs():
        if _is_under(path, d):
            return "runtime"
    z4 = zero400_root()
    if _is_under(path, z4):
        return "zero400"
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

        live_dirs = list(default_runtime_datadirs()) + [zero400_root()]
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
    p.add_argument("--is-live", metavar="PATH", help="Exit 0 if runtime or Zero400")
    p.add_argument("--is-runtime", metavar="PATH", help="Exit 0 if default runtime datadir")
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
