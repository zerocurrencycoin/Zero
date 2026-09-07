# Measuring across projects: uniblake, Zero, and what to share

Zero and uniblake each record measurements, independently and incompatibly.
This document reviews uniblake's practice, states why the two stores should
stay separate, and specifies the narrow thing worth sharing.

Written 2026-09-05 from the state of both trees on that date.

## 1. uniblake's practice, reviewed

uniblake's harness is **stronger than Zero's in three specific ways**, and the
gaps are worth closing here rather than admiring there.

| Area | uniblake | RecBench |
|---|---|---|
| Test targets | 11 `check-*` targets: KAT, alias, negative, portable, backends, wine, sanitize, wipe-modes, nosodium | none of this kind -- RecBench is a store, not a runner |
| Benchmarks | 4 harnesses: compare, isa, phases, prefix | launchers measure; no micro-benchmarks |
| Dispersion | two per row, with named kinds (`iqr`, `mad`, `stddev`, `ci95`) | `stdev` computed at collation only |
| Repetition | `REPS_MENU = (5, 10, 100)` -- a menu, not a free number | `--trial N`, no guidance |
| Value semantics | `kind` column: point / median / cumulative / series / share / count | implicit; every value treated alike |
| Execution mode | `exec` column: native / emulated / cross | absent -- a wine or rosetta run looks native |
| Oracle identity | `oracle` + `oracle_flags` columns | not modelled |
| Platform id | `tools/platform_id.sh`, derived from hardware | `platform_id` hash, derived from a stamp |

Three of these are lessons Zero should adopt, and one of them cost this
session a wrong number (S3).

**`kind` is the sharpest idea.** A cumulative average and an instantaneous
rate are different quantities, and reporting a spread over samples of the
first is meaningless. RecBench has no such column, so its `stdev` over a
`cumulative` value would be exactly that mistake, silently.

**`exec` matters for correctness of conclusions, not just labelling.** uniblake
records rows measured under wine; those digests are correct and their timings
are meaningless. RecBench cannot express this, so a Rosetta or emulated run
would pool with native rows.

**The `REPS_MENU` discipline** -- "two runs at 7 and 9 reps are not comparable,
and nothing is gained by the difference" -- is the kind of rule that makes
results combinable by construction. RecBench's `--trial` has no equivalent.

What RecBench does better: **identity as first-class**. Four hashes
(`platform_id`, `build_id`, `config_id`, `dataset_id`) composed into
`context_id`, with an explicit merge that refuses to combine differing
contexts. uniblake's `platform` is a string; two spellings of one machine
would not group, which `platform_id.sh` mitigates by generating rather than
solving structurally.

## 2. Why not one store

The schemas share **three columns**: `metric`, `value`, `unit`. Everything else
is a different spelling of a similar idea -- `commit`/`build_id`,
`platform`/`platform_id`, `supersedes`/`superseded`, `utc`/`recorded_at`,
`note`/`notes`.

That is not an argument for merging them. It is an argument that **the payload
already agrees and the envelope never will**, which is exactly the split
RecBench S7 (R6) predicted: identity is project-specific, payload is not.

A single store would need one project to adopt the other's envelope. uniblake
would gain `dataset_id` (meaningless for a digest rate) and lose `kind`,
`exec`, `oracle_flags`; Zero would gain columns it cannot populate. Neither is
an improvement.

**Recommendation: keep two stores, define one exchange format.**

## 3. Collect locally, combine deliberately

The exchange unit is the row RecBench already supports: `metric` / `value` /
`unit` plus an envelope naming platform, build and conditions. uniblake's
`record.py` emits every field needed except the four hashes; RecBench's
`--import-tsv` accepts a TSV.

Concretely, and in dependency order:

| Step | What | Why first |
|---|---|---|
| 1 | Add `kind` and `exec` to RecBench rows, defaulting to `point` / `native` | Cheapest, and prevents a class of wrong aggregate. No identity change |
| 2 | Add `oracle` / `oracle_flags` as `features.runtime` keys in Zero's launchers | Already expressible; needs no schema change. See S3 |
| 3 | Write `recbench.py --import-unibench <measurements.tsv>` mapping uniblake's 24 columns onto the envelope | One direction only: uniblake is the producer, RecBench the archive |
| 4 | Keep `campaign` as the join key across projects; never `context_id` | Contexts are per-tree by construction and will never match |

Step 3 is deliberately one-directional. Zero's chain-sync rows have no meaning
in uniblake's store, and a bidirectional sync invites the pooling both designs
exist to prevent.

**What must not be shared: a `context_id`.** The hash covers a project's own
platform/build/config/dataset. Two projects computing it over different
inputs would produce collisions that mean nothing, or differences that mean
nothing. Compare by `metric` + `unit` + explicit conditions, never by context
equality.

## 4. The oracle-flags gap, and a claim it produced that was wrong

uniblake's `record.py` docstring states the rule:

> "libsodium 1.0.21" named two builds 64% apart on the same machine, because
> the version was recorded and the optimisation level was not.

This session repeated that mistake within an hour of reading it, twice, in
opposite directions. Both are recorded because the second was nearly published
as a finding.

**First error: an untuned oracle.** A blake2b comparison was run against
Homebrew's libsodium 1.0.22 -- a poured bottle, built generically for arm64 --
and recorded as a 2.36x uniblake advantage with +11.8% on bulk.

**Second error: a single run.** Re-run against Zero's `depends` libsodium
1.0.21 (`-O3`, static), one sample gave 161.7 ns, and the conclusion drawn was
that **1.0.22 is a performance regression**. It is not. Repeating each three
times:

| Oracle build | leaf ns/digest, n=3 | sd |
|---|--:|--:|
| depends 1.0.21, `-O3` static | 165.7 | 0.06 |
| 1.0.22, `-O3` static, same options | 166.4 | 0.47 |

**0.4% apart -- noise.** The single 161.7 reading was the low end of run
variance, and an A/B built on one sample from each side is not a measurement.

**Proof from the source, not the clock.** The complete blake2b difference
between 1.0.21 and 1.0.22 is `/* LCOV_EXCL_LINE */` coverage comments on error
paths. Compiling `blake2b-compress-ref.c` at `-O3` from both trees yields
**byte-identical assembly** (1573 lines each). There is no mechanism by which
blake2b performance could differ.

```
diff -rq sodium21/.../blake2b/ref sodium22/.../blake2b/ref
  -> only blake2b-ref.c differs; the compress kernels are identical
cc -O3 -S blake2b-compress-ref.c   (both trees) -> identical .s
```

The same holds for `crypto_core/ed25519`: 0 non-comment lines changed.

Across the whole source tree, 239 files differ only by LCOV comments and 54
have substantive changes -- `randombytes.c` (restructured init and an
Emscripten path), `codecs.c`, and a new `crypto_ipcrypt` module. None touches
blake2b.

**Corrected conclusions:**

1. uniblake's advantage on this machine is **2.10x on the prefix-heavy leaf
   case** and **nil on bulk** (1725 vs 1719 MB/s, +0.3%), measured against a
   properly built oracle.
2. **1.0.21 and 1.0.22 are performance-equivalent for blake2b**, provably so.
   Any earlier statement that either version is faster was an artifact of
   build flags or of a single sample.

## 5. libsodium version, and where uniblake reaches Zero

Both are owned elsewhere and are not restated here:

- Which libsodium, and why: `SODIUM_SURVEY.md`.
- Which library computes which hash, and the 12 files uniblake touches:
  `HASHLIBS.md`.
