# librustzcash

The Rust proof dependency: what it replaced, what is already validated, and
what validation remains. Recommendation, not a decision.

**Background: it replaced libsnark, and that is settled.** libsnark
implemented the Sprout proving system (BCTV14/PGHR13 over alt_bn128) in C++.
Sapling moved proving and verification to Rust `bellman`, after which the C++
system was on no live path -- Sprout proof verification also routes through
librustzcash. Zcash removed libsnark in v2.1.0; Zebra never had it; Pirate,
Ycash and Hush all removed it. Zero still carries `src/snark/` unbuilt, which
is a deletion item, not an open question.

## 1. What is already validated (do not re-run)

| Question | Answer | Where |
|----------|--------|-------|
| Does the 2018 crate build on a modern toolchain? | **Yes.** macOS defaults to **system rustc**, currently **1.90.0** | `BUILD_ZERO.md:63,311`; `depends/packages/rust.mk:20` |
| Is the old pin still reproducible? | **Yes.** `FORCE_DEPENDS_RUST=1` builds against pinned **1.32.0** | `rust.mk:36-40` |
| Does it link? | **Yes.** `depends/aarch64-apple-darwin25.3.0/lib/librustzcash.a`, 6.35 MB | built 2026-09-01 |
| Integration points | Raw `extern "C"` via `librustzcash.h` | `PerfGroth.md` |

**So the "can we still build it" question is closed.** A 2018 crate compiling
under rustc 1.90 is the unusual outcome and it is already demonstrated across
two toolchains. Remaining questions are about *direction*, not viability.

## 2. What the siblings actually did -- this settles the shape

| Project | Rust integration | Toolchain |
|---------|------------------|-----------|
| **Upstream zcash** | Crate **deleted**; moved into `zcash/zcash` | current |
| **Pirate** | **`src/rust/{include,src}` in-tree**; no `librustzcash.mk` | 1.69.0 |
| **Ycash** | **`src/rust/{include,src}` in-tree**; no `librustzcash.mk` | 1.63.0 |
| **Zero** | External `depends/packages/librustzcash.mk`, pinned `06da3b9a` | system / 1.32.0 |

**Three independent projects converged on the same answer: bring the Rust
in-tree under `src/rust/`.** Zero is the only one still fetching a standalone
crate that upstream has deleted. `PerfGroth.md` already proposed moving
`librustzcash.h` into `src/rust/include/` -- which is exactly the layout Pirate
and Ycash have.

## 3. Recommendation

**Step 1 -- vendor in-tree, unchanged. Do this regardless of A-vs-B.**

Take `06da3b9a` into `src/rust/` with the Pirate/Ycash layout. **Acceptance
test: a byte-identical `librustzcash.a`.** Same code, same crate, same
toolchain -- only the fetch disappears.

*Justification:* it removes a build dependency on an upstream path that has
**already been deleted**; it matches what both surviving sibling forks do; it
carries no consensus risk because the artifact is bit-identical; and it is a
prerequisite for either batching option, so it is never wasted work. The
current arrangement's risk is not theoretical -- the crate Zero fetches does
not exist at HEAD upstream.

**Step 2 -- decide A vs B, but only after A3 and P1.**

- **Option A** (hand-port batching onto the 2018 crates): Phases 0-1 already
  proved the math there.
- **Option B** (adopt a newer base, e.g. Pirate's 1.69 or Ycash's 1.63
  lineage): gets maintained crates and signature batching, but changes the FFI
  boundary -- which *is* the A-vs-B cost difference.

**Recommendation: A, on the vendored tree.** Reasons: the math is already
proved on exactly those crates; after Step 1 the code is Zero's, so "unmaintained
upstream" stops being an argument; and B's real benefit (signature batching)
is a separate, later win that does not require paying the FFI migration now.
B remains the long-term target.

**Blocking prerequisite, unchanged:** A3 (per-proof baseline) and P1 (proof
counters). Groth16 verification is inside no timer, so today's instrumentation
would omit 88-91% of post-Sapling cost while appearing complete -- any
before/after would be meaningless. **This is the only thing that must happen
before batching work starts.**

## 4. Remaining validation, and what it costs

| # | Test | Why | Effort |
|---|------|-----|--------|
| 1 | Build with `FORCE_DEPENDS_RUST=1` and confirm `librustzcash.a` still links and the node runs | Pins the reproducible path before touching anything | S |
| 2 | Vendor in-tree; diff the resulting `.a` against the current one | The acceptance test for Step 1 | S |
| 3 | Run the Sapling gtests + `qa` shielded tests on the vendored build | Confirms the FFI surface is unchanged | S |
| 4 | Attempt a build against Pirate's 1.69 lineage **without adopting it** | Scopes Option B's real cost instead of estimating it | M |
| 5 | A3 microbenchmark baseline | The "before" for any batching claim | S |

(1)-(3) are Step 1's validation and are cheap. (4) is the only way to price
Option B honestly. (5) is time-sensitive and independent.

## 5. What is NOT recommended

- **Do not** upgrade the pin in place. The crate no longer exists upstream, so
  there is nothing to upgrade *to* on that path.
- **Do not** start batching before A3/P1.
- **Do not** adopt Pirate's or Ycash's tree wholesale. They carry their own
  consensus parameters; the useful thing is their *layout*, already copied in
  Step 1.
