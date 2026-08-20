#!/usr/bin/env python3
"""Bucket an xctrace time-profile export, with pool and leaf-class attribution.

Successor to reindex-profile/tools/bucket_profile.py. Same backreference
parsing (that part reproduces exactly and is not changed); different reporting.

What is different and why:

  1. groth16_proof replaces sapling_groth16_proof. The bls12_381 pairing code
     verifies BOTH Sprout JoinSplits and Sapling spends/outputs, so the old
     name implied Sapling work in pre-Sapling blocks. Where the entry point is
     identifiable the sample is further attributed to a POOL (sprout / sapling
     / shared), so pre- and post-Sapling captures can be compared honestly.

  2. blake2b is its own bucket, ahead of equihash. Previously blake2b_compress
     was inside the equihash bucket and no record cited a blake2b percentage,
     which is the number the NEON question needs.

  3. disk_io is split into disk_syscall (time actually in a read/write/open
     syscall) and disk_decode (ReadBlockFromDisk / LoadExternalBlockFile on the
     stack but executing deserialization or memmove underneath). On a measured
     pre-Sapling reindex the old single bucket read 14.66% while syscall leaves
     summed to 4.91% -- about two thirds of "disk" was not disk.

  4. Every run also emits a leaf-frame table and the per-thread split, so
     "would more cores help" is answerable from the same artifact.

Usage:
  contrib/perf/bucket_profile2.py <export.xml> [thread-substring] [--json out.json]

Default thread filter is zcash-loadblk (reindex/import). Use "Main Thread" for
wallet rescan captures.
"""
import collections
import json
import re
import sys
import xml.etree.ElementTree as ET

# Order matters: first match on ANY frame in the stack wins.
BUCKETS = collections.OrderedDict([
    ("witness_cache", [
        "VerifyAndSetInitialWitness", "BuildWitnessCache", "DecrementNoteWitnesses",
        "ClearNoteWitnessCache", "ClearSingleNoteWitnessCache",
        "UpdateSaplingNullifierNoteMap", "UpdateNullifierNoteMap",
    ]),
    ("wallet_add_ordered", [
        "AddToWallet", "OrderedTxItems", "SyncTransaction", "SyncMetaData",
        "SyncWithWallets", "IncOrderPosNext", "wtxOrdered", "nTimeSmart",
    ]),
    ("wallet_db", ["CWalletDB", "BerkeleyBatch", "Db::", "wallet.zero"]),
    ("wallet_other", ["CWallet::"]),
    # Groth16 proof verification. Pool-agnostic: same code for Sprout and Sapling.
    ("groth16_proof", [
        "bellman::groth16::verifier::verify_proof", "miller_loop", "final_exponentiation",
        "librustzcash_sapling_check_spend", "librustzcash_sapling_check_output",
        "librustzcash_sprout_verify", "pairing::", "bls12_381",
        "Fr::mul_assign", "Fr$u20$as$u20$pairing", "mul_assign::",
    ]),
    # Pedersen/merkle tree and anchor maintenance. Keep AFTER groth16: jubjub
    # Point::add appears in both, and attributing it to tree understated Groth
    # by ~50 points in the original M-CPU-LEGACY misbucket.
    ("tree_anchor", [
        "AbstractPushAnchor", "IncrementalMerkleTree", "librustzcash_merkle_hash",
        "PushAnchor", "merkle_hash", "sapling_crypto::jubjub::edwards::Point",
    ]),
    # blake2b: its own bucket, ahead of equihash, so the NEON question has a number.
    ("blake2b", ["blake2b", "Blake2b", "blake2b_compress"]),
    ("equihash", ["CheckEquihashSolution", "IsValidSolution", "CheckBlockHeader", "Equihash<"]),
    # Real syscall time.
    ("disk_syscall", [
        "__open_nocancel", "__close_nocancel", "__read_nocancel", "__write_nocancel",
        "__lseek", "__pread", "__pwrite",
    ]),
    # Block IO path but NOT in a syscall: deserialize, memmove, buffer copies.
    ("disk_decode", [
        "OpenDiskFile", "ReadBlockFromDisk", "UndoWriteToDisk", "WriteBlockToDisk",
        "LoadExternalBlockFile", "fopen", "fread", "fwrite", "CAutoFile", "Unserialize",
    ]),
    ("leveldb_db", ["leveldb::"]),
    ("sha256_txhash", ["sha256::"]),
    ("connect_block", [
        "ConnectBlock", "ConnectTip", "ActivateBestChain",
        "ContextualCheckBlock", "CheckBlock", "AcceptBlock",
    ]),
])

# Pool attribution for groth16_proof, checked before the generic needles.
POOL = [
    ("sprout", ["librustzcash_sprout_verify", "JSDescription", "JoinSplit"]),
    ("sapling", ["librustzcash_sapling_check_spend", "librustzcash_sapling_check_output",
                 "SaplingSpend", "SaplingOutput"]),
]


# LAYERS: a second, ORTHOGONAL view that does not depend on bucket order.
# First-match bucketing can only answer one question per capture: with wallet
# buckets first a rescan shows "which wallet function" and crypto reads 0.00%;
# with crypto first it shows "which primitive" and wallet reads 0.00%. Neither
# is wrong, but a mixed workload (wallet-on reindex) hides half of itself.
#
# LAYERS instead asks, per sample, "is any frame of this kind present", and a
# sample may count in more than one layer. Shares therefore sum to >100% and
# that is intentional: it makes nesting visible (wallet work that is doing
# crypto underneath) rather than forcing an either/or.
LAYERS = collections.OrderedDict([
    ("wallet_layer", ["CWallet::", "CWalletDB", "CMerkleTx", "BuildWitnessCache",
                      "VerifyAndSetInitialWitness", "AddToWallet", "OrderedTxItems"]),
    ("crypto_layer", ["bls12_381", "pairing::", "miller_loop", "final_exponentiation",
                      "blake2b", "librustzcash_merkle_hash", "sapling_crypto::",
                      "librustzcash_sapling", "librustzcash_sprout"]),
    ("validation_layer", ["ConnectBlock", "ConnectTip", "ContextualCheckBlock",
                          "CheckBlock", "AcceptBlock", "ActivateBestChain"]),
    ("io_layer", ["ReadBlockFromDisk", "LoadExternalBlockFile", "OpenDiskFile",
                  "__open_nocancel", "__read_nocancel", "__write_nocancel", "leveldb::"]),
])


def parse(path):
    """Resolve xctrace id/ref backreferences; yield (thread, weight_ns, frames)."""
    tree = ET.parse(path)
    root = tree.getroot()
    threads, weights, frames_by_id, backtraces = {}, {}, {}, {}

    def resolve(el, store, build):
        rid = el.get("id")
        ref = el.get("ref")
        if ref is not None:
            return store.get(ref)
        val = build(el)
        if rid is not None:
            store[rid] = val
        return val

    out = []
    for row in root.iter("row"):
        th = wt = bt = None
        for child in row:
            tag = child.tag
            if tag == "thread":
                # Name lives in the fmt attribute, not element text (text is the tid).
                th = resolve(child, threads, lambda e: e.get("fmt") or "")
            elif tag == "weight":
                wt = resolve(child, weights, lambda e: float("".join(e.itertext()).strip() or 0))
            elif tag in ("tagged-backtrace", "backtrace"):
                def build_bt(e):
                    fs = []
                    for fr in e.iter("frame"):
                        f = resolve(fr, frames_by_id, lambda x: x.get("name") or "")
                        if f:
                            fs.append(f)
                    return fs
                bt = resolve(child, backtraces, build_bt)
        if th is not None and wt:
            out.append((th, wt, bt or []))
    return out


def classify(frames):
    for bucket, needles in BUCKETS.items():
        if any(any(n in f for n in needles) for f in frames):
            return bucket
    return "other"


def pool_of(frames):
    for name, needles in POOL:
        if any(any(n in f for n in needles) for f in frames):
            return name
    return "shared"


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    path = argv[0]
    want = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else "zcash-loadblk"
    jsonout = None
    if "--json" in argv:
        jsonout = argv[argv.index("--json") + 1]

    rows = parse(path)
    if not rows:
        print("no samples parsed", file=sys.stderr)
        return 1

    per_thread = collections.Counter()
    for th, wt, _ in rows:
        per_thread[th] += wt
    total_all = sum(per_thread.values())

    sel = [(th, wt, fr) for th, wt, fr in rows if want in th]
    if not sel:
        print(f"no samples on thread matching {want!r}", file=sys.stderr)
        print("threads present:", file=sys.stderr)
        for th, wt in per_thread.most_common(8):
            print(f"  {th}  {wt/1e9:.3f}s", file=sys.stderr)
        return 1

    total = sum(wt for _, wt, _ in sel)
    buckets = collections.Counter()
    pools = collections.Counter()
    leaves = collections.Counter()
    layers = collections.Counter()
    for _, wt, fr in sel:
        for lname, needles in LAYERS.items():
            if any(any(n in f for n in needles) for f in fr):
                layers[lname] += wt
        b = classify(fr)
        buckets[b] += wt
        if b == "groth16_proof":
            pools[pool_of(fr)] += wt
        for f in fr[:8]:
            if f and not f.startswith("<unresolved"):
                leaves[f] += wt
                break

    print(f"samples {len(rows)}  total {total_all/1e9:.3f}s across {len(per_thread)} threads")
    print(f"\nPer-thread split (top 10):")
    for th, wt in per_thread.most_common(10):
        print(f"  {th[:60]:60} {wt/1e9:8.3f}s {wt/total_all*100:6.2f}%")

    print(f"\nBuckets on {want!r}: {total/1e9:.3f}s")
    for b, wt in buckets.most_common():
        print(f"  {b:20} {wt/1e9:8.3f}s {wt/total*100:6.2f}%")

    print(f"\nLayers on {want!r} (overlapping; a sample counts in every layer present,")
    print(f"so these do NOT sum to 100% -- overlap is the point):")
    for l, wt in layers.most_common():
        print(f"  {l:20} {wt/1e9:8.3f}s {wt/total*100:6.2f}%")
    if not layers:
        print("  (none matched)")

    if pools:
        print(f"\ngroth16_proof pool attribution:")
        g = sum(pools.values())
        for p, wt in pools.most_common():
            print(f"  {p:20} {wt/1e9:8.3f}s {wt/g*100:6.2f}% of groth16")

    print(f"\nTop leaf frames on {want!r}:")
    for f, wt in leaves.most_common(12):
        print(f"  {wt/total*100:6.2f}%  {wt/1e9:7.3f}s  {f[:80]}")

    if jsonout:
        with open(jsonout, "w", encoding="utf8") as fh:
            json.dump({
                "thread_filter": want,
                "total_s": total / 1e9,
                "total_all_threads_s": total_all / 1e9,
                "threads": {t: w / 1e9 for t, w in per_thread.items()},
                "buckets": {b: w / 1e9 for b, w in buckets.items()},
                "bucket_pct": {b: w / total * 100 for b, w in buckets.items()},
                "groth16_pools": {p: w / 1e9 for p, w in pools.items()},
                "layer_pct": {l: w / total * 100 for l, w in layers.items()},
                "leaves": {f: w / 1e9 for f, w in leaves.most_common(25)},
            }, fh, indent=2)
        print(f"\nwrote {jsonout}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
