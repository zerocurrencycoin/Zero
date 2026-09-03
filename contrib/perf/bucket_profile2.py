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


def parse_folded(path):
    """Parse folded stacks: `frame;frame;frame<TAB or space>count` per line.

    The format `perf script | stackcollapse-perf.pl` emits, and what FlameGraph
    consumes. Chosen over `perf script` output directly because collapsing is
    the part that varies between perf versions, and because a folded file is
    plain text -- so this parser is testable anywhere, including on a host with
    no perf.

    Thread is not in the format. Every sample is attributed to one synthetic
    thread name, which the caller filters on; use --thread all to keep them.
    """
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            stack, sep, count = line.rpartition(" ")
            if not sep:
                stack, sep, count = line.rpartition("\t")
            if not sep:
                continue
            try:
                weight = int(count)
            except ValueError:
                continue
            frames = [f for f in stack.split(";") if f]
            if not frames:
                continue
            # Folded stacks are leaf-last; the xctrace path yields leaf-first.
            out.append(("folded", weight, list(reversed(frames))))
    return out


def parse_any(path):
    """Dispatch on content, not on a flag: an XML file starts with '<'."""
    with open(path, "rb") as fh:
        head = fh.read(64).lstrip()
    return parse(path) if head.startswith(b"<") else parse_folded(path)


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



def self_test():
    """Pin the bucket-ordering regressions that produced published wrong numbers.

    classify() is five lines, but every CPU share in the ledger comes out of
    it, and it is order-sensitive: first match wins on any frame in the stack.
    Four figures have been wrong because of that (docs/FINDINGS.md S3.3), so
    each is pinned here as an executable assertion rather than a comment.
    """
    ok = True

    def check(cond, msg):
        nonlocal ok
        if not cond:
            print("FAIL: " + msg, file=sys.stderr)
            ok = False

    order = list(BUCKETS)

    def before(a, b):
        """Ordering assertion that reports a missing bucket instead of raising."""
        if a not in order or b not in order:
            check(False, "bucket missing from BUCKETS: %s" %
                  ", ".join(x for x in (a, b) if x not in order))
            return False
        return order.index(a) < order.index(b)

    # 1. groth16 BEFORE tree_anchor. jubjub Point::add appears in both paths;
    #    ordering tree first understated Groth16 by ~50 points.
    check(before("groth16_proof", "tree_anchor"),
          "groth16_proof must be ordered before tree_anchor")
    check(classify(["sapling_crypto::jubjub::edwards::Point::add",
                    "bellman::groth16::verifier::verify_proof"]) == "groth16_proof",
          "a stack containing verify_proof must bucket as groth16, not tree")

    # 2. witness_cache BEFORE wallet_other. A bare CWallet:: needle otherwise
    #    swallows VerifyAndSetInitialWitness.
    check(before("witness_cache", "wallet_other"),
          "witness_cache must be ordered before wallet_other")
    check(classify(["CWallet::VerifyAndSetInitialWitness"]) == "witness_cache",
          "VerifyAndSetInitialWitness must not fall into wallet_other")

    # 3. blake2b BEFORE equihash. blake2b was hidden inside equihash, so no
    #    blake2b figure existed at all.
    check(before("blake2b", "equihash"),
          "blake2b must be ordered before equihash")

    # 4. disk split. disk_io over-attributed 14.66% vs 4.91% of real syscall
    #    leaves; the merged bucket must stay split.
    check("disk_syscall" in BUCKETS and "disk_decode" in BUCKETS,
          "disk_syscall / disk_decode split must be preserved")
    check("disk_io" not in BUCKETS, "the merged disk_io bucket must not return")

    # Folded stacks: the Linux path. Testable here because the format is text,
    # so the parser does not need perf or a Linux host to be exercised.
    import os
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "out.folded")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("main;ConnectBlock;blake2b_compress_ref 120\n")
            fh.write("main;ConnectBlock;bls12_381_pairing 30\n")
            fh.write("\n# comment\n")
            fh.write("main;ReadBlockFromDisk;__read 10\t\n")
        rows = parse_folded(f)
        check(len(rows) == 3, "folded: three sample lines parsed")
        check(rows[0][1] == 120, "folded: weight read")
        check(rows[0][2][0] == "blake2b_compress_ref", "folded: leaf first")
        check(classify(rows[0][2]) == "blake2b", "folded: leaf classifies")
        check(parse_any(f) == rows, "parse_any dispatches folded by content")

    # Unmatched frames are attributed, not dropped.
    check(classify(["some::unknown::frame"]) == "other",
          "unmatched stack must bucket as 'other'")
    check(classify([]) == "other", "empty stack must not raise")

    # Pool attribution is separate from bucketing and defaults to shared.
    check(pool_of(["librustzcash_sprout_verify"]) == "sprout", "sprout pool")
    check(pool_of(["librustzcash_sapling_check_spend"]) == "sapling", "sapling pool")
    check(pool_of(["miller_loop"]) == "shared",
          "code common to both pools must be 'shared', not guessed")

    # Buckets are mutually exclusive: classify returns one name from the table.
    check(classify(["BuildWitnessCache", "verify_proof"]) in BUCKETS,
          "classify must return a known bucket name")

    print("self-test OK" if ok else "self-test FAILED", file=sys.stderr)
    return 0 if ok else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if not argv:
        print(__doc__)
        return 2
    path = argv[0]
    want = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else "zcash-loadblk"
    jsonout = None
    if "--json" in argv:
        jsonout = argv[argv.index("--json") + 1]

    rows = parse_any(path)
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

    # A thread filter that matches nothing is the most common operator error
    # (HOWTO S2.4). Report it as such rather than dividing by zero -- and never
    # emit a 0.00% table, which reads like a real measurement.
    if total_all <= 0:
        print("no samples in this trace", file=sys.stderr)
        return 1
    if total <= 0:
        print(f"no samples on thread {want!r}; "
              f"threads present: {', '.join(sorted(per_thread)[:6])}",
              file=sys.stderr)
        return 1

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
