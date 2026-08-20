# Groth16 proof verification

Everything needed to decide and implement Sapling Groth16 batch verification.
Current state and forward path only; superseded attempts are not recorded here.

Numbers are cited by `M-*` id and live in `Measures.md`. Task status lives in
`PerfTasks.md`.

**This is the focused Groth16 document.** It is the single home for Groth16
evidence, options and implementation path. Other documents cite its conclusions
and carry a headline figure at most -- they deliberately do not restate the
evidence here. When adding Groth16 material anywhere in `contrib/perf/`, add it
to this file instead. Task state: `docs/TASKS.md`. Everything else:
`docs/FINDINGS.md`, which explicitly excludes this topic.

> **Postponed pending developer review (2026-08-20).** This document is
> complete and reviewable as it stands; it is waiting on a maintainer to pick
> Option A or Option B (S4), not on further measurement. **Do not start
> implementation work, and do not extend the prototype in S7.** The decision
> is a judgement call about consensus-critical crypto and migration cost, and
> the two options diverge at the FFI boundary. The crux to answer first is S4
> question 4: if batching can land behind the existing C ABI, Option A avoids
> a release-scale migration entirely.

---

## 1. Why this matters

Groth16 proof verification is the dominant cost of block validation once
Sapling is active.

| Region | Groth16 share of `zcash-loadblk` | Measure |
|--------|---------------------------------:|---------|
| pre-Sapling (h26k-125k) | ~43% | S1 captures, `cpu_ledger.jsonl` |
| **post-Sapling (h521k-605k)** | **88-91%** | S3 captures |
| chain-wide average | 48-55% | M-CPU-SEQ |
| one corrected window | 60.9% | M-CPU-CORR |

Post-Sapling it is not the largest component, it is nearly the whole workload.
Leaf frames shift from `Fr::mul_assign` (Sprout JoinSplit scalar field) to
`Fq::mul` / `Fq::sqr` / `Fq::add` and `G1::CurveProjective` -- Sapling base
field pairing arithmetic.

Pre-Sapling Groth16 is **Sprout JoinSplit** verification: the same bls12_381
code serves both pools, which is why the bucket is named `groth16_proof` and
not `sapling_groth16_proof`.

## 2. Current implementation

Every proof is verified **independently, on one thread, with no batching
anywhere in the call chain**.

- Entry points: `librustzcash_sapling_check_spend`, `librustzcash_sapling_check_output`
- Rust side: `bellman::groth16::verifier::verify_proof`, one proof per call
- C++ side: eager per-transaction verification inside `ContextualCheckBlock`
- FFI: `librustzcash.h`, raw `extern "C"`; **no `cxx` bridge in tree**

Pinned crate set is 2018-era `bellman` / `pairing` / `jubjub`, at
`librustzcash` commit `06da3b9ac8f278e5d4ae13088cf0a4c03d2c13f5`.

## 3. The headroom

Batch verification replaces N independent pairing checks with one randomized
linear combination, amortizing the expensive final exponentiation.

- The maintained successor (`zkcrypto/bellman`) ships `batch.rs`; the pinned
  crate does not.
- **The primitive the algorithm needs already exists in the pinned crate**, so
  a hand-port is feasible without a crate migration.
- Modern `bellman` requires `edition = 2021` / `rust-version = 1.60`, and
  `zcash/librustzcash` `main` no longer contains `bellman`/`pairing` at all --
  so "just upgrade the dependency" is not available.

## 4. The decision: Option A vs Option B

**Blocking.** No implementation work past prototype should start until this is
resolved, because the two paths diverge at the FFI boundary and would waste
each other's work.

### Option A -- hand-port batch math into the pinned stack

**For**
- Smallest footprint: no crate migration, no change to the existing FFI shape.
- Prototype exists and passes (pure-Rust, outside FFI).
- Pinned 2018 crates confirmed to build clean under a modern toolchain.
- Build and dependency surface unchanged -- material for a project with very
  few maintainers.

**Against**
- Reimplements roughly four years of upstream work.
- **Misses signature batching entirely.** `sapling-crypto`'s `BatchValidator`
  also batches RedJubjub `spend_auth_sig` / `binding_sig`; a Groth16-only
  hand-port does not.
- No production track record for this specific port; math is proven only
  against synthetic test-circuit proofs.
- Batch-size and latency tuning has no precedent to start from.
- In-house consensus-critical crypto carries a heavier independent-review
  burden.

### Option B -- adopt `sapling-crypto::BatchValidator`

**For**
- Battle-tested: runs in `zcashd` and Zebra.
- Signature batching included.
- Same-lineage precedent: Pirate Chain, a C++ zcashd fork, has integrated it.
- Tuned parameters already exist (`MAX_BATCH_SIZE=64`, `MAX_BATCH_LATENCY=100ms`).
- Puts Zero on a maintained crate lineage rather than a 2018 snapshot.

**Against**
- Release-scale migration: crosses the `ff` / `group` trait split against
  Zero's pinned `bellman` / `pairing` / `jubjub`. Effort band **L-XL**.
- May require a `cxx` bridge -- see below.
- Touches `depends/`, cargo-offline, and the reproducible-build path.

### The cxx question is part of this decision, not separate

Zero's FFI today is `librustzcash.h` with raw `extern "C"`. Modern zcashd and
Zebra use `cxx`. Open questions, all scoping rather than settled:

1. Does Option B **require** `cxx`, or can upgraded crates still expose a
   stable C ABI keeping Zero's header shape?
2. If required, what is the blast radius in `depends/`, cargo-offline and
   reproducible builds?
3. How much of Pirate's or zcashd's bridge is reusable versus fork-specific?
4. **Can batching land behind the existing C FFI** as an A/B hybrid, or is
   crate migration inseparable from batching?

Question 4 is the crux: if batching can ship behind the current C ABI, Option A
avoids a release-scale migration entirely.

## 5. Implementation path, whichever option wins

Ordered; each step is a gate.

1. Read `verifier.rs` end to end at the pinned commit.
2. Prototype the batch math as a standalone Rust unit outside the FFI boundary
   (`#[cfg(test)]` only). **Done for Option A.**
3. Design the FFI/buffering boundary before writing Rust. Current
   `_check_spend` / `_check_output` are eager and per-proof; batching needs a
   collect-then-verify shape.
4. Restructure `ContextualCheckBlock` control flow: collect all Sapling
   spend/output proofs across a block's transactions, verify once, and define
   the batch-failure policy (a failed batch must fall back to per-proof
   verification to identify the offending transaction).
5. Source the per-batch CSPRNG -- a new input this call path does not have
   today. Check `random.h` / `GetRandBytes` equivalents.
6. Scope consensus-safety review as its own step. Unlike the root-latch and
   anchor-index work (pure memoization, no change to what is computed), this
   changes *how* a consensus predicate is evaluated.

## 6. Constraints and non-goals

- **Batch failure must be recoverable.** A batch that fails verification
  cannot reject the block outright; it must identify which proof failed.
- **No consensus change.** Batch verification must accept exactly the set of
  proofs the per-proof path accepts.
- Per-transaction-attributed fallback as originally sketched is **not** what
  current `zcashd` does; it rejects the batch and re-verifies.
- Halo/Orchard is **out of scope** -- not Zero consensus.
- NEON blake2b is a separate item; blake2b is 18-21% pre-Sapling but only
  3-4% post-Sapling, so it does not compete with this.

## 7. Prototype

`contrib/perf/groth16-batch-poc/` -- standalone Rust, pinned crates, proves the
batch math outside the FFI boundary. Its fetched dependency checkout
(`/librustzcash-pinned/`) is gitignored and never committed.

## 8. Measuring a change

```bash
# post-Sapling capture, ~15 min to reach the region
tar -xzf "$HOME/Library/Application Support/zero/chainblocks-postsap12.tgz" -C $LAB blocks
./src/zerod -datadir=$LAB -reindex -daemon
contrib/perf/profile_run.sh S3-groth-after $LAB 60
contrib/perf/profile_collate.py report --scenario S3-groth-after
```

Compare against the recorded S3 baselines (88.5% none, 91.5% p1). Throughput
side: `postsapling_reindex.sh`, ledger `CAMPAIGN=`.
