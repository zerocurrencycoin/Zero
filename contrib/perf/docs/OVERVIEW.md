# ZeroPerf: what this effort is

Entry point for the ZeroPerf work. Problem statement, goals, what has been
established, and where each kind of reader goes next.

This is the **front door**. It is deliberately short and stable: findings
change, the problem statement does not.

---

## 1. Problem statement

A Zero full node must validate the entire chain from genesis before it is
usable. That cost falls on every operator who syncs, reindexes, or rescans a
wallet, and it grows with the chain.

Three things have been established by measurement, each with consequences for
what is worth doing. Evidence and numbers: **[FINDINGS.md](FINDINGS.md)**.

- **Groth16 proof verification dominates post-Sapling validation.** Almost
  everything else is rounding, so almost every other optimization is a
  rounding-error optimization. Pre-Sapling the same code verifies Sprout
  JoinSplits; blake2b is the next largest share there, but it falls away
  post-Sapling, which is why it is not a sync target.
- **The work is serial and CPU-bound.** Storage and I/O tuning cannot help,
  established by measuring a null result rather than assumed.
- **Witness-scan cost is a separate problem with a separate shape.** On a large
  wallet the rescan bottleneck is the witness scan, not block validation, so the
  two need different fixes and different measurements.
- **Equihash solve and verify are a parallel track**, measured separately: they
  answer a mining question, not a sync question.

The goal is not "make it faster" in the abstract. It is to know **where the
time goes, with evidence**, so that the few changes that would matter are
chosen deliberately, and changes that sound promising but measure null are
identified before they ship.

---

## 2. Goals

| Goal | Meaning |
|------|---------|
| **Measure before changing** | No optimization ships on reasoning alone. A change needs a baseline, a measurement, and a comparison on the same host |
| **Make results durable** | A number is worthless without its window, thread, platform, binary and feature set. Results are recorded so they aggregate across time and machines |
| **Prefer negatives to guesses** | A measured null is a real result. Two are recorded here, and both stopped work that would otherwise have continued |
| **Keep the product path clean** | Lab instrumentation is compiled out by default. What ships is what users run |
| **Leave the decision to a person** | Where the choice is a judgement call about consensus-critical code, the work stops at a documented decision, not an implementation |

---

## 3. Where this stands

| Area | State | Detail |
|------|-------|--------|
| **Groth16 batch verification** | The largest known win. **Postponed pending developer review** -- the choice is a maintainer's, not a measurement's | `../PerfGroth.md` |
| **Shipped fixes** | Six landed, three of them pure memoisation | `FINDINGS.md` S3.5 |
| **Measured nulls** | I/O tuning, established rather than assumed | `FINDINGS.md` S3.2 |
| **Wallet witness path** | Separate track; one fix shipped, one defect open | `FINDINGS.md` S3.1 |
| **Equihash / blake2** | Parallel track, integrating | `FINDINGS.md` S2 |
| **Blind spots** | Bound what can be concluded from any of the above | `FINDINGS.md` S4 |

Current work and its order: **[TASKS.md](TASKS.md)**.

---

## 4. Proposed solutions, and their status

Stated so a reader can see what is proposed versus established.

| Proposal | Rationale | Status |
|----------|-----------|--------|
| **Batch Groth16 verification** | Amortises the pairing final exponentiation across a block's proofs | Postponed on an A/B decision |
| **Always-on phase timing** | Field nodes report how far they got, never where the time went | Specified, not built |
| **Groth16 verification counters** | Groth16 verification sits outside every existing timer | Specified; prerequisite for the above |
| **NOTEIDX staleness fix** | The note index is invalidated by transactions that can never appear in it | Open, defect localised |
| **Cross-platform measurement** | Every published number is from one machine and one architecture | Schema Finished, first Linux run open |

---

## 5. Reader routing

### Operators

You do not need this directory. Two practical consequences of the findings:

- **A single import is CPU-bound and single-threaded.** More cores do not speed
  it up, and faster storage helps less than expected.
- **A large wallet makes rescan much slower**, for reasons unrelated to block
  validation.

Build and run: root **`README.md`**, **`BUILD_ZERO.md`**. Operational
validation: **`contrib/ops-validate.sh`**, **`TEST_ZERO.md`**.

If a node seems abnormally slow, the useful artifact is `debug.log` -- though
it currently records progress but not timing (`TASKS.md` B1).

### Zero project developers

- **[HOWTO.md](HOWTO.md)** -- how to take a measurement and read it. Read before
  running anything; it documents traps that produced published wrong numbers.
- **[FINDINGS.md](FINDINGS.md)** -- what is known and how confident.
- **[TASKS.md](TASKS.md)** -- what is open, in what order, with Kanban state.
- **[SCHEMA.md](SCHEMA.md)** -- how to record a result so it aggregates.
- **[POLICY.md](POLICY.md)** -- rules, ownership, lab discipline, cleanup.

Product changes are specified here and **reviewed in Zero400**, which owns
`src/`.

### External contributors

The harness is reusable and the method is the transferable part:

- Bucket classification is **symbol-name based** and portable; only the trace
  parser is platform-specific. A new platform needs one new parser function,
  not a new classifier.
- Results carry platform, build and feature identity, so measurements from
  different machines can be compared or deliberately kept apart.
- Every published figure names the log or capture it came from.

Most useful contributions right now, in order: a **Linux `perf` capture**
(first non-macOS data point), an **x86-64 result** (the architecture assumption
is untested), and **independent review of the Groth16 options**
(`../PerfGroth.md`).

### Parallel and ecosystem projects

Zcash-family forks share most of this code, so several findings should
transfer directly, and the framing is deliberately fork-neutral:

- Groth16 dominance post-Sapling is a property of the shared bls12_381
  verification path, not of Zero.
- The witness-scan cost on large wallets is shared wallet code.
- `CDB::Rewrite` spinning with no log or timeout is upstream and present across
  the family.
- The phase-timer gaps are inherited from upstream Bitcoin/Zcash
  instrumentation and are worth checking in any fork relying on `-debug=bench`
  (`FINDINGS.md` S1.1).

Where a finding is upstream rather than Zero-specific, it is marked as such so
it can be carried back or adapted without re-deriving it.

---

## 6. What this effort will not do

Recorded so it is not repeatedly re-proposed:

- **Consensus changes.** Batch verification must accept exactly the proofs the
  per-proof path accepts.
- **Speculative optimization.** Every Aside item carries a measured or
  arithmetic reason (`TASKS.md`).
- **Halo / Orchard.** Not Zero consensus.
- **Zerowallet.** Full node only.
