# Open questions needing a design decision

Raised 2026-09-09. Each states the question, the options, and a justified
recommendation. **None is decided.**

## Q1. `z_sendmany` note reservation (P9)

Harden `sendmany` with `lock_notes()`, or record the coupling and leave it?

- **Pro:** defence in depth; the safety property stops depending on a comment;
  the pattern exists two files away in `mergetoaddress`.
- **Con:** local divergence on wallet spend selection against a 2018 base;
  upstream's own answer was to restructure the whole async path; the failure is
  unreachable unless someone re-enables a disabled option.
- **Recommendation: document now (P9 item 1); do not harden yet.** The
  history settles it -- Zcash disabled multi-worker in `008fccfa4` (2016-09-01)
  saying "Disabled until we can lock notes", met that precondition in
  `06553d139` (2022-10-24, PR #6408, issues #2621/#5654) via a
  `wallet_tx_builder` Zero does not have, and only then re-enabled the loop.
  Zero is on the pre-2022 side of that line, and the policy protecting it is
  the same one upstream relied on for six years. Adding ad-hoc locks to a 2018
  base is not the upstream path; the upstream path is `wallet_tx_builder`,
  which is a far larger change than P9 contemplates.

## Q2. TST-09 notify tests -- what is the assertion?

`-blocknotify` and `-walletnotify` are implemented but untested. The design
question is what the test asserts, not whether to write it.

- **Option A -- side-effect file.** Point the hook at a script that touches a
  file; assert the file appears after `generate(1)` / a wallet tx.
  Simple, portable, and tests the wiring end to end. Timing-sensitive: needs a
  bounded wait, not a fixed sleep.
- **Option B -- assert on substitution.** Have the script record `%s` and
  assert it equals the expected block hash / txid. Tests wiring *and* the
  substitution contract, which is the part that could silently regress.
- **Recommendation: B.** A is a strict subset and the extra assertion is one
  line. The substitution is the actual contract an operator depends on.
- **Open sub-question:** one script covering both hooks, or two? One is less
  code; two isolate a failure. Recommend two, in one file.

## Q3. Does `equihashsolver` default change? (D5) -- **RESOLVED 2026-09-09**

**Done: tromp is now the default.** The declared stance (conf templates, for
years) was correct and the code was wrong. Applied with a parameter guard,
pinned by a mutation-tested case, recorded in
`test-logs/tromp-default-20260909/FINDINGS.md`. Needs a release note. Original
framing kept below for the record.

tromp measures **5.69x** faster at **3.3 GB** vs the default solver's 7.15 GB
(M-EQ-TROMP-SPEEDUP, M-EQ-PEAK-TROMP, M-EQ-PEAK-DEFAULT), is vendored at
`src/pow/tromp/`, and is already selectable at runtime. Default is still
`"default"` (`init.cpp:551`).

- **Pro:** it is strictly better on both axes and the code is already shipped.
- **Con:** it changes what every miner runs by default; needs a KAT/soak
  statement and a release note; consensus-adjacent even though solving is not
  consensus (verification is).
- **Recommendation: yes, but gated on a stated validation set** -- the (192,7)
  KATs plus a mainnet-template solve, and a release note. This is a product
  decision, not a lab one, which is why D5 is InTest rather than Finished.

## Q4. librustzcash: stay pinned, or move to a fork's newer base? (GROTH)

Zero pins `06da3b9a` (2018-10-27), **6724 commits** behind, and the C FFI crate
it consumes **no longer exists upstream** (verified: upstream
`librustzcash/README.md` now reads "This crate has been moved into
zcash/zcash").

Pirate and Ycash both carry the same lineage with a small number of
project-specific commits and are checked out locally.

- **Option A -- stay pinned, hand-port batching onto the 2018 crates.** Phases
  0-1 already proved the math there. Lowest immediate risk, no dependency
  change, but permanently diverges and inherits no upstream fixes.
- **Option B -- adopt Pirate's or Ycash's newer base, then batch.** Gets a
  maintained crate set and signature batching; cost is unscoped and the FFI
  boundary changes (cxx bridge vs raw `extern "C"`), which *is* the A-vs-B cost
  difference.
- **Recommendation: fork-for-custody first, regardless.** Take `06da3b9a` into
  a Zero-owned mirror unchanged, acceptance test a byte-identical
  `librustzcash.a`. It is S-effort, carries no consensus risk, and stops the
  build depending on an upstream path that has already moved once. Only then
  decide A vs B.
- **Prerequisite for either: A3 and P1.** A batching result needs a per-proof
  baseline taken beforehand, and Groth16 verification is currently inside no
  timer at all -- so today's counters would omit 88-91% of post-Sapling cost
  while appearing complete.
- **Validation the decision needs, and does not have:** a benchmark of the
  *current* pinned integration, so any move has a before. That is A3.

## Q5. Gated RPC entry points -- **detailed in `RPC_GATING.md`**

**Correction to the premise: only one RPC is gated today, not two.**
`CGetAllDataInFlightGuard` is instantiated once, in `getalldata`
(`rpczerowallet.cpp:2073`). So the work is 1 -> 4.

**Recommendation: one shared guard keyed by RPC name** (`RPC_GATING.md` S4
Option B), then register `zs_listtransactions`,
`zs_listreceivedbyaddress` and one of the `zs_list*byaddress` pair. Gate by
cost, not by file membership -- `zs_gettransaction` is a point lookup and must
**not** be gated, or a cheap call starts returning `-34`.

**Open sub-question:** shared in-flight slot (bounds total wallet load) or
per-RPC (friendlier to a UI wanting two views)? **Recommend per-RPC**, because
it cannot break an existing client; add a shared cap only if load proves it
necessary.

## Q6. librustzcash -- **detailed in `LIBRUSTZCASH_DECISION.md`**

**Recommendation: vendor in-tree first, unchanged, regardless of A-vs-B.**
Both surviving sibling forks (Pirate 1.69, Ycash 1.63) moved the Rust to
`src/rust/{include,src}` and dropped `librustzcash.mk` entirely -- the same
layout `PerfGroth.md` proposed. Zero is the only one still fetching a crate
upstream has deleted. Acceptance test: byte-identical `librustzcash.a`.

Then **Option A on the vendored tree** -- the math is already proved on those
crates, and after vendoring "unmaintained upstream" stops being an argument.
B stays the long-term target for signature batching.

**Already validated, do not re-run:** the 2018 crate builds under **system
rustc 1.90.0** and under pinned 1.32.0 (`BUILD_ZERO.md:63,311`;
`rust.mk:20,36`). Viability is closed; only direction remains.

**Hard prerequisite:** A3 and P1 before any batching work.

## Q7. The `nTimeVerify` reported field -- what should Zero400 change?

**The defect.** `nTimeConnect` and `nTimeVerify` both measure from
`nTimeStart` (`main.cpp:3269`, `:3281`), so `nTimeVerify` **includes**
`nTimeConnect`. The `-debug=bench` line reads:

    - Connect N transactions: X ms
    - Verify N txins: Y ms

and a reader naturally sums X + Y. That double-counts: Y already contains X.
Inherited from upstream Bitcoin; the labels do not say so. Compounding it,
**neither field covers proof verification at all** (P1).

**Three options.**

| # | Option | Effect on existing consumers |
|---|--------|------------------------------|
| A | Leave the field, document the overlap in the log text | None. A parser keeps working; a human reading the log learns the truth |
| B | Report `verify_excl = nTimeVerify - nTimeConnect` under the existing label | **Silently changes an existing number.** Any script or dashboard tracking "Verify" sees a step change with no version signal |
| C | Keep `Verify` as-is and **add** a `Verify excl` field beside it | Additive. Old parsers unaffected; new ones get the non-overlapping figure |

**Recommendation: C, with A's wording as part of it.**

*Justification.* B is the tempting one -- it makes the obvious reading correct
-- but it changes the meaning of a field that has had one meaning since
Bitcoin, without any way for a consumer to detect the change. That is the same
class of hazard as `WAL-GETALLDATA-ARG2-DEFAULT`: a silent behaviour change to
a long-standing default. C costs one extra field and is unambiguous, and it
composes with P1: once proof counters land, the bench line can report
`Connect`, `Verify excl`, `Proof` and `Index` as four non-overlapping buckets
that actually sum to something meaningful. That is the shape a phase summary
needs, and B alone would not get there.

*If C is refused on log-width grounds*, take A. Do not take B without a
release note and a version marker in the log format.

**Owner: Zero400.** Evidence: `test-logs/p1-proto-20260910/FINDINGS.md`,
`PerfTimers.md` S3.
