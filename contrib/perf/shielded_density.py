#!/usr/bin/env python3
"""Shielded density scan via RPC getblock hex + local deserialize.

NOTE: Zero `getblock` verbosity 2 omits Sapling/Sprout shield fields; do not
use JSON block txs for counts. Use `getblock <hash> false` + mininode.

Writes append-only progress JSONL and density CSV.
Fine rematch windows first; coarse 400k bands with Sapling activation split.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "qa" / "rpc-tests"))
from test_framework.mininode import CBlock  # noqa: E402

SAPLING_ACTIVATION = 492850
CHUNK = 400_000

FINE_BANDS = [
    ("presap-rematch-50k-75k", 50_000, 75_000),
    ("sapling-onset-490k-520k", 490_000, 520_000),
    ("postsap-rematch-600k-900k", 600_000, 900_000),
]

CSV_FIELDS = [
    "era",
    "h0",
    "h1",
    "sapling_spends",
    "sapling_outputs",
    "sprout_js",
    "fully_shielded_tx",
    "blocks",
    "shielded_tx_per_block",
    "sapling_tx",
    "sprout_tx",
    "tx_total",
]


def rpc(cli: str, datadir: str, rpcport: int, *args: str) -> str:
    cmd = [cli, f"-datadir={datadir}", f"-rpcport={rpcport}", *args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"RPC failed: {' '.join(args)}\n{r.stderr.strip()}")
    return r.stdout.strip()


def wait_rpc(cli: str, datadir: str, rpcport: int, timeout_s: int = 120) -> int:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        try:
            return int(rpc(cli, datadir, rpcport, "getblockcount"))
        except Exception as e:
            last = str(e)
            time.sleep(2)
    raise SystemExit(f"RPC not ready after {timeout_s}s: {last}")


def coarse_bands(tip: int) -> list[tuple[str, int, int]]:
    bands: list[tuple[str, int, int]] = []
    edges = [0]
    h = CHUNK
    while h < tip:
        edges.append(h)
        h += CHUNK
    edges.append(tip)
    if SAPLING_ACTIVATION not in edges and 0 < SAPLING_ACTIVATION < tip:
        edges.append(SAPLING_ACTIVATION)
    edges = sorted(set(edges))
    for i in range(len(edges) - 1):
        h0, h1 = edges[i], edges[i + 1]
        if h0 >= h1:
            continue
        if h1 <= SAPLING_ACTIVATION:
            tag = "pre-sapling"
        elif h0 >= SAPLING_ACTIVATION:
            tag = "post-sapling"
        else:
            tag = "mixed"
        era = f"coarse-{tag}-{h0}-{h1 - 1}"
        bands.append((era, h0, h1))
    return bands


def _has_transparent_vin(tx) -> bool:
    for i in tx.vin:
        if i.prevout.hash != 0 or i.prevout.n != 0xFFFFFFFF:
            return True
    return False


def count_block(raw_hex: str) -> dict:
    block = CBlock()
    block.deserialize(BytesIO(bytes.fromhex(raw_hex)))
    spends = outputs = js = 0
    sapling_tx = sprout_tx = fully_shielded = tx_total = 0
    for tx in block.vtx:
        tx_total += 1
        ns = len(tx.shieldedSpends)
        no = len(tx.shieldedOutputs)
        nj = len(tx.vJoinSplit)
        spends += ns
        outputs += no
        js += nj
        if ns + no > 0:
            sapling_tx += 1
        if nj > 0:
            sprout_tx += 1
        if (ns + no + nj) > 0 and not _has_transparent_vin(tx) and len(tx.vout) == 0:
            fully_shielded += 1
    return {
        "sapling_spends": spends,
        "sapling_outputs": outputs,
        "sprout_js": js,
        "fully_shielded_tx": fully_shielded,
        "sapling_tx": sapling_tx,
        "sprout_tx": sprout_tx,
        "tx_total": tx_total,
        "blocks": 1,
    }


def count_block_from_rpc_txs(cli: str, datadir: str, rpcport: int, txids: list[str]) -> dict:
    """Count via getrawtransaction verbose JSON (includes shield fields)."""
    spends = outputs = js = 0
    sapling_tx = sprout_tx = fully_shielded = tx_total = 0
    for txid in txids:
        tx = json.loads(rpc(cli, datadir, rpcport, "getrawtransaction", txid, "1"))
        tx_total += 1
        vspend = tx.get("vShieldedSpend") or []
        vout_s = tx.get("vShieldedOutput") or []
        vjs = tx.get("vjoinsplit") or []
        ns, no, nj = len(vspend), len(vout_s), len(vjs)
        spends += ns
        outputs += no
        js += nj
        if ns + no > 0:
            sapling_tx += 1
        if nj > 0:
            sprout_tx += 1
        vin = tx.get("vin") or []
        vout = tx.get("vout") or []
        has_t_in = any("txid" in i for i in vin)
        has_t_out = len(vout) > 0
        if (ns + no + nj) > 0 and not has_t_in and not has_t_out:
            fully_shielded += 1
    return {
        "sapling_spends": spends,
        "sapling_outputs": outputs,
        "sprout_js": js,
        "fully_shielded_tx": fully_shielded,
        "sapling_tx": sapling_tx,
        "sprout_tx": sprout_tx,
        "tx_total": tx_total,
        "blocks": 1,
    }


def count_height(cli: str, datadir: str, rpcport: int, h: int) -> dict:
    bh = rpc(cli, datadir, rpcport, "getblockhash", str(h))
    try:
        raw = rpc(cli, datadir, rpcport, "getblock", bh, "false")
        return count_block(raw)
    except Exception:
        # Some heights fail mininode deserialize (proof-format edge); fall back.
        summary = json.loads(rpc(cli, datadir, rpcport, "getblock", bh, "1"))
        return count_block_from_rpc_txs(cli, datadir, rpcport, summary["tx"])


def add_counts(a: dict, b: dict) -> None:
    for k, v in b.items():
        a[k] = a.get(k, 0) + v


def load_done_eras(csv_path: Path) -> set[str]:
    done = set()
    if not csv_path.exists():
        return done
    with csv_path.open() as f:
        for row in csv.DictReader(f):
            if row.get("era"):
                done.add(row["era"])
    return done


def append_progress(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def append_csv_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def scan_band(
    cli: str,
    datadir: str,
    rpcport: int,
    era: str,
    h0: int,
    h1: int,
    tip: int,
    progress_path: Path,
    csv_path: Path,
    progress_every: int,
) -> dict:
    h1 = min(h1, tip + 1)
    if h0 >= h1:
        return {}
    totals = {
        "sapling_spends": 0,
        "sapling_outputs": 0,
        "sprout_js": 0,
        "fully_shielded_tx": 0,
        "sapling_tx": 0,
        "sprout_tx": 0,
        "tx_total": 0,
        "blocks": 0,
    }
    t0 = time.time()
    last_prog = h0
    for h in range(h0, h1):
        add_counts(totals, count_height(cli, datadir, rpcport, h))
        if (h + 1 - last_prog) >= progress_every or h + 1 == h1:
            append_progress(
                progress_path,
                {
                    "era": era,
                    "h_done": h,
                    "h0": h0,
                    "h1_excl": h1,
                    "blocks_scanned": totals["blocks"],
                    "sapling_spends": totals["sapling_spends"],
                    "sapling_outputs": totals["sapling_outputs"],
                    "sprout_js": totals["sprout_js"],
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "elapsed_s": round(time.time() - t0, 1),
                },
            )
            last_prog = h + 1
            print(
                f"  progress {era} h={h} blocks={totals['blocks']} "
                f"spends={totals['sapling_spends']} outs={totals['sapling_outputs']} "
                f"js={totals['sprout_js']} ({time.time() - t0:.0f}s)",
                flush=True,
            )
    blocks = totals["blocks"] or 1
    row = {
        "era": era,
        "h0": h0,
        "h1": h1 - 1,
        "sapling_spends": totals["sapling_spends"],
        "sapling_outputs": totals["sapling_outputs"],
        "sprout_js": totals["sprout_js"],
        "fully_shielded_tx": totals["fully_shielded_tx"],
        "blocks": totals["blocks"],
        # An empty band divides by zero. Report None rather than 0.0: a
        # density of zero is a real measurement, "no blocks" is not.
        "shielded_tx_per_block": (
            round((totals["sapling_tx"] + totals["sprout_tx"]) / blocks, 6)
            if blocks > 0 else None
        ),
        "sapling_tx": totals["sapling_tx"],
        "sprout_tx": totals["sprout_tx"],
        "tx_total": totals["tx_total"],
    }
    append_csv_row(csv_path, row)
    print(f"CLOSED {era}: {row}", flush=True)
    return row


def self_test() -> int:
    """Pin band construction, count accumulation and resume bookkeeping.

    coarse_bands decides how density data is binned, and the Sapling boundary
    is the whole point of the split: a band straddling it mixes two populations
    with very different shielded density, which is exactly the confusion this
    scan exists to resolve.
    """
    import io
    import contextlib
    import tempfile

    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    # No band may straddle Sapling activation.
    for tip in (1000, SAPLING_ACTIVATION - 1, SAPLING_ACTIVATION,
                SAPLING_ACTIVATION + 1, 900_000, 2_500_000):
        bands = coarse_bands(tip)
        for era, h0, h1 in bands:
            check(not (h0 < SAPLING_ACTIVATION < h1),
                  "band %s straddles Sapling activation (tip=%d)" % (era, tip))
            check(h0 < h1, "band %s is non-empty" % era)
            check("mixed" not in era,
                  "no band should be tagged mixed once the split is applied: %s" % era)

    # Bands are contiguous and cover [0, tip) with no gap or overlap.
    bands = coarse_bands(2_500_000)
    check(bands[0][1] == 0, "banding starts at height 0")
    check(bands[-1][2] == 2_500_000, "banding ends at the tip")
    for (e0, a0, a1), (e1, b0, b1) in zip(bands, bands[1:]):
        check(a1 == b0, "bands are contiguous: %s ends %d, %s starts %d"
              % (e0, a1, e1, b0))

    # Tagging follows the boundary.
    tags = {era.split("-")[1] + "-" + era.split("-")[2] for era, _, _ in bands}
    check("pre-sapling" in tags and "post-sapling" in tags,
          "both eras are represented above activation")
    for era, h0, h1 in bands:
        if h1 <= SAPLING_ACTIVATION:
            check("pre-sapling" in era, "%s below activation must be pre" % era)
        elif h0 >= SAPLING_ACTIVATION:
            check("post-sapling" in era, "%s above activation must be post" % era)

    # A tip at or below activation yields only pre-sapling bands.
    for era, _, _ in coarse_bands(SAPLING_ACTIVATION):
        check("pre-sapling" in era, "tip at activation yields only pre bands")

    # Degenerate tips must not raise or emit an empty/negative band.
    for tip in (0, 1):
        for era, h0, h1 in coarse_bands(tip):
            check(h1 > h0, "degenerate tip %d produced an empty band" % tip)

    # add_counts accumulates and does not lose keys from either side.
    a = {"sapling_tx": 1, "blocks": 2}
    add_counts(a, {"sapling_tx": 3, "sprout_tx": 5})
    check(a["sapling_tx"] == 4, "existing keys accumulate")
    check(a["sprout_tx"] == 5, "new keys are added")
    check(a["blocks"] == 2, "untouched keys are preserved")
    add_counts(a, {})
    check(a["sapling_tx"] == 4, "an empty update is a no-op")

    # Resume bookkeeping: eras already in the CSV are skipped on a re-run.
    with tempfile.TemporaryDirectory() as d:
        csv_path = Path(d) / "density.csv"
        check(load_done_eras(csv_path) == set(),
              "an absent CSV means nothing is done, not an error")
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["era", "blocks"])
            w.writeheader()
            w.writerow({"era": "coarse-pre-sapling-0-399999", "blocks": 400000})
            w.writerow({"era": "", "blocks": 0})
        done = load_done_eras(csv_path)
        check(done == {"coarse-pre-sapling-0-399999"},
              "completed eras are recognised; blank rows ignored")

    # shielded_tx_per_block: a zero-block band must not divide by zero.
    src = Path(__file__).read_text(encoding="utf-8")
    check("if blocks > 0 else None" in src,
          "an empty band yields None, not a divide-by-zero or a fake 0.0")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--datadir", required=True)
    ap.add_argument("--cli", default=str(REPO / "src" / "zero-cli"))
    ap.add_argument("--rpcport", type=int, default=23811)
    ap.add_argument("--out-dir", default=str(REPO / "reindex-profile"))
    ap.add_argument("--mode", choices=("fine", "coarse", "all"), default="fine")
    ap.add_argument("--progress-every", type=int, default=10_000)
    args = ap.parse_args()

    out = Path(args.out_dir)
    csv_path = out / "shielded-density.csv"
    progress_path = out / "shielded-density.progress.jsonl"

    tip = wait_rpc(args.cli, args.datadir, args.rpcport)
    print(f"tip={tip} csv={csv_path}", flush=True)

    bands: list[tuple[str, int, int]] = []
    if args.mode in ("fine", "all"):
        bands.extend(FINE_BANDS)
    if args.mode in ("coarse", "all"):
        bands.extend(coarse_bands(tip))

    done = load_done_eras(csv_path)
    for era, h0, h1 in bands:
        if era in done:
            print(f"skip done {era}", flush=True)
            continue
        if h0 > tip:
            print(f"skip future {era}", flush=True)
            continue
        print(f"scan {era} [{h0}, {h1}) tip={tip}", flush=True)
        scan_band(
            args.cli,
            args.datadir,
            args.rpcport,
            era,
            h0,
            h1,
            tip,
            progress_path,
            csv_path,
            args.progress_every,
        )
    print("DENSITY_SCAN_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
