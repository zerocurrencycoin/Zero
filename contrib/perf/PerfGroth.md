# Groth16 proof verification

Everything needed to decide and implement Sapling Groth16 batch verification.
Current state and forward path only; superseded attempts are not recorded here.

Numbers are cited by `M-*` id and live in `Measures.md`. Task status lives in
`docs/TASKS.md`.

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
- blake2b hashing is a separate item (closed, `docs/HASHLIBS.md`); it is 18-21% pre-Sapling but only
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


---

## Moved from Perf.md, 2026-09-07

Groth16 material that stayed in `Perf.md` after this document was created.
`Perf.md` owns ConnectBlock findings; Groth16 is this file's subject.

### 0.0 Groth16 item -- lead-in and step-by-step

Reviewer entry point for people who have not lived in §§2/6/9.4. Evidence stays in those sections; this is the decision story and ordered steps.

#### Review packet

| Item | Content |
|------|---------|
| **Ask** | Choose **Option A** (hand-port batch math on pinned 2018 crates) or **Option B** (migrate to `sapling-crypto` / `BatchValidator`). |
| **Why it matters** | Post-Sapling ConnectBlock CPU ~**48-55%** Groth16 (M-CPU-SEQ); up to **~60.9%** in one corrected window (M-CPU-CORR). |
| **Today** | Eager per-spend/output `verify_proof` on `zcash-loadblk`; no batch API; scriptcheck workers never see Groth16. |
| **Option A status** | Phases 0-1 **done** (MiMC KATs N=1..64 + corrupt); code **not in repo** (scratchpad). Phase 2+ blocked on decide. |
| **Option B status** | Upstream production since 2022 (zcashd, Zebra); Pirate has C++/`cxx` precedent. Migration cost **unscoped** (§0.6a cxx questions open). |
| **Not substitutes** | I/O and index work -- measured flat for throughput. |
| **Independent tracks** | Fat-wallet witness productize (§0.14); mining solve profile (G5). |
| **Decide inputs** | §0.1a pros/cons; §0.6a effort bands; §6-6.2 crypto/control-flow; §9.4 phase checklist. |
| **After decide** | Stage 2 evidence closeout -> Stage 3 implement -> measure vs post-Sap baselines; keep sequential fallback until proven. |

**Blocking rule:** no Groth16 product implementation (§9.4 Phase 2 onward) until A/B is chosen by a person.

#### Why it exists

1. **What we measured:** during mainnet `-reindex` / bootstrap import, after Sapling activation (~height 492,850), ConnectBlock CPU is dominated by verifying Sapling Groth16 proofs (spend/output). Corrected profiles: **~48-55%** chain-wide (M-CPU-SEQ); one corrected post-Sapling window hit **~60.9%** (M-CPU-CORR). Disk and Equihash are real but smaller.
2. **What that means for operators:** post-Sapling reindex/import is slow mainly because each shielded description pays a full pairing check on the single `zcash-loadblk` thread -- not because disk is slow. The I/O side was measured and is not the bottleneck (`Perf.md` S3, M-CPU-FD-THR).
3. **What Zero does today:** one `verify_proof` per spend/output, sequential, inside `ContextualCheckBlock` -> `ContextualCheckTransaction` -> `librustzcash_sapling_check_*`. Transparent script checks can use `zcash-scriptch` workers; Groth16 cannot -- different queue, never shared.
4. **What "batching" would change:** for N proofs that share a verifying key, combine them with random linear weights and pay **one** expensive final-exponentiation for the batch instead of N. Same pass/fail math class; different operation schedule (consensus-adjacent -- needs review).
5. **Why this is not "just implement it":** mid-investigation, upstream `sapling-crypto::BatchValidator` (production since 2022; used by zcashd and Zebra; Pirate has a C++/`cxx` precedent) appeared as a full alternative to hand-porting only the pairing batch math into Zero's pinned 2018 crates. That forks the project into a **decision**, not more Phase-2 coding.

#### Step-by-step

Human process order.

| Step | Action | Status |
|------|--------|--------|
| 1 | Measure ConnectBlock CPU buckets on real mainnet heights (pre- vs post-Sapling) | Done -- §2 |
| 2 | Confirm call path is per-proof, single-threaded; no hidden batch API in pinned crates | Done -- §6 |
| 3 | Confirm modern `bellman` has `batch.rs`; note crate migration cost (`ff`/`group` split) | Done -- §6 |
| 4 | Confirm pinned `pairing` already has multi-pair `miller_loop` (hand-port feasible) | Done -- §6 |
| 5 | Discover shipped `BatchValidator` (+ signature batching) and cross-ecosystem use | Done -- §6.1/§6.2 |
| 6 | Prototype hand-port math on pinned crates (MiMC fixtures, N=1..64, corrupt cases) | Done Phases 0-1 -- §9.4; **scratchpad only, not in repo** |
| 7 | **Decide:** Option A hand-port vs Option B adopt `sapling-crypto` | **Blocked -- person decides** (§0.1) |
| 8a | If A: Phase 2 FFI design -> Phase 3 shadow/batch in `main.cpp` -> review | Not started |
| 8b | If B: spike migration cost (FFI/`cxx`, depends, blast radius) then implement | Not started |
| 9 | Measure tip/window blk/s before vs after; keep sequential path as fallback until proven | Not started |
| 10 | Multicore batch / latency tuning | Later, separable |

#### How to explain it in one paragraph

Post-Sapling sync is Groth16-bound (~half of ConnectBlock CPU). Zero verifies every Sapling proof one-at-a-time on the import thread. Batch verification can collapse much of that cost; we proved the math works on Zero's old crates, but upstream already ships a stronger batcher that also covers signatures -- so the next move is choose hand-port vs migrate, not write Phase 2 yet. I/O work already shipped and measured flat; it is not a substitute for this item.

#### Pointers

- Decision detail / pro-con: §0.1 and §0.1a  
- CPU evidence: §2; measure IDs M-CPU-* in **Measures.md**  
- Crypto and control-flow constraints: §6  
- Hand-port phase checklist: §9.4  
- Independent of this decision: blake2b hashing (SIMD track closed) (§5 / §0.2 item 2), measure campaigns (stock rematch)

### 0.1a PENDING DECISION -- Groth16 batch verification: hand-port vs adopt `sapling-crypto`

**Pending questions (lab-wide, settled owners):**

| Question | Owner / gate | Status |
|----------|--------------|--------|
| Groth16 Option A vs B (§0.1a), **including the cxx-bridge scoping (§0.6a)** | Person | **Open** -- G2 then G3 consecutive after G5/G9. The cxx questions are not a separate decision: whether batching can land behind Zero's existing C ABI (`librustzcash.h`, raw `extern "C"`) or requires a cxx bridge **is** the A-vs-B cost difference |
| ARM fleet mix | Deploy survey | **Open**; relevant to the solver track only |
| W5/W6 / getalldata cache / Zerowallet notmodified | Product review | **Postponed** |
| Halo/Orchard for Zero | Not Zero consensus; Zebro D2 | **Postpone G8** |
| KAT adapt tests beyond TST-05 green | G9 | **Postponed** |

**Status: blocking.** No further Groth16 implementation work (§9.4 Phase 2 onward) should start until this is resolved by a person, not inferred from this document. Nothing below picks a winner.

**Decision needed:** for Sapling Groth16 batch verification (the single largest CPU-optimization opportunity found in this investigation, §2), should Zero (a) hand-port the batching math into its existing pinned 2018-era `bellman`/`pairing` crate stack, or (b) migrate to the current `sapling-crypto`/`bellman 0.14` crate stack and adopt its shipped `BatchValidator` directly?

**Option A -- Hand-port into the pinned stack** (§9.4 as written)

*Pro:*
- Smallest footprint -- no crate-version migration, no change to Zero's existing FFI shape (`librustzcash.h`, raw `extern "C"`), no touch to any dependency other than the one being extended.
- De-risked in real, tested code already: §9.4 Phases 0-1 (pure-Rust prototype) are done and passing -- a hand-ported random-linear-combination batch verifier built against the actual pinned `bellman 0.1.0`/`pairing 0.14.2`, validated against real Groth16 proofs from `bellman`'s own MiMC/BLS12-381 test circuit, batch accept/reject exactly matching per-proof `verify_proof` across N=1,2,8,64 and adversarial corrupted-proof cases, repeated 6 times. This isn't theoretical -- the core math is proven to work on Zero's actual dependency versions.
- Confirmed buildable: the pinned 2018-era crate pair builds clean under a modern Rust 1.90 toolchain (§9.4 Phase 0 finding) -- no toolchain-pinning workaround needed.
- Keeps Zero's build/dependency surface area unchanged, which matters for a project maintained by very few people (§0's own framing -- see `MEMORY.md`: user is sole owner/maintainer of the Zero repo family).

*Con:*
- Reinvents ~4 years of upstream engineering (`BatchValidator` shipped in `zcash_proofs` 2022-07-05) rather than reusing it.
- **Misses signature batching entirely** -- `sapling-crypto`'s `BatchValidator` batches RedJubjub `spend_auth_sig`/binding signatures alongside Groth16 proofs (§6.1); the hand-port plan only ever scoped proof batching, since Zero's current `check_spend` verifies the signature eagerly, per-call, ahead of the proof check (§9.4 Phase 0 finding). A hand-ported Groth16-only batcher leaves that signature-verification cost fully unaddressed.
- No production track record for *this specific port* -- the math is proven against synthetic MiMC test-circuit proofs, not against real Sapling spend/output circuits or adversarial conditions beyond what §9.4's test plan covers. `BatchValidator` by contrast has ~4 years of live-network exposure across `zcashd` and Zebra.
- Batch-size tuning (how many proofs per batch, what latency budget) has no precedent to draw from -- Zebra's real, tuned parameters (`MAX_BATCH_SIZE=64`, `MAX_BATCH_LATENCY=100ms`, §6.2) apply to `BatchValidator`'s architecture, not directly transferable to a hand-rolled one.
- Building consensus-critical cryptographic code in-house, however well-tested, carries more independent-review burden (§9.4 Phase 6) than adopting code multiple other implementations already run in production.

**Option B -- Adopt `sapling-crypto` directly**

*Pro:*
- Reuses battle-tested code: `BatchValidator` has run in `zcashd` and Zebra (both currently active, `zcashd` until its imminent end-of-life ~2026-07-18) for roughly four years, and is the architecture of the two most-current reference implementations in the ecosystem (§6.2).
- Gets signature batching for free, a real efficiency gain the hand-port plan never scoped.
- Real integration precedent exists for exactly Zero's situation: Pirate Chain, a same-lineage C++ zcashd fork, has already done this exact migration (its own vendored `cxx`-bridge Rust crate wrapping `BatchValidator`, §6.2) -- a template closer to Zero's actual codebase than Zebra's from-scratch Rust design.
- Real, tuned batch-size parameters already exist to start from (`MAX_BATCH_SIZE=64`/`MAX_BATCH_LATENCY=100ms`), rather than guessing.
- Positions Zero on a currently-maintained crate lineage instead of a snapshot of a since-heavily-refactored 2018 dependency graph, which may reduce future maintenance friction (e.g. if any future Sapling/consensus fix upstream only lands against the current crate generation).

*Con:*
- Materially larger, effectively unscoped effort: crosses the `ff`/`group` trait-split ecosystem-wide API break (§6) -- every type in Zero's `librustzcash`/`bellman`/`pairing`/`jubjub` call path is affected, not just the verifier.
- Unknown whether Zero's current C-header FFI (`librustzcash.h`) can be kept as-is or needs replacing with a `cxx`-bridge like `zcashd`'s current architecture (§0.5 -- genuinely unresolved, not just unscoped).
- No prototype exists for this path at all -- unlike Option A, zero hands-on validation has been done; the entire cost/risk profile is currently an estimate, not a measurement.
- Real risk of the migration itself introducing regressions unrelated to Groth16 batching, simply by virtue of touching every consumer of the affected crates -- a much larger consensus-code blast radius than Option A's narrowly-scoped change.
- Bigger, harder-to-interrupt effort for a single-maintainer project -- more exposure if only partially completed.

**Recommendation (offered, not decided): lean toward Option B if the migration cost turns out to be smaller than it currently looks, otherwise Option A.** Concretely: the single highest-leverage next step is **not** more coding on either path, but **scoping Option B's actual migration cost** (§0.2 item 6) -- right now it's the con with the least evidence behind it ("large, separate undertaking" is a characterization from §6, not a sized estimate), while Option A's cost and viability are already fully measured (§9.4 Phases 0-1). A short, bounded research spike into what the `ff`/`group` migration and FFI-layer question actually require (see §0.5, §0.6) would turn this from a qualitative pro/con list into a comparison grounded in bridge/depends evidence (§0.6a). Until then, Option A is the lower-uncertainty choice by default only because a working prototype exists -- not because it has been shown better.

### 0.6a Groth Option B migration-cost spike

Qualitative scope only. Calendar time estimates are **not** refined here -- there is no measured basis for days/weeks claims.

**Question:** how large is adopting `sapling-crypto::BatchValidator` relative to continuing the hand-port on pinned crates?

| Layer | Finding | Effort band |
|-------|---------|-------------|
| Crypto API | `BatchValidator` batches Groth16 and RedJubjub spend-auth/binding sigs; Zebra documents batch-size / latency knobs | Reuse if crates move |
| Crate graph | Modern stack crosses the `ff`/`group` trait split vs Zero's pinned 2018 `bellman`/`pairing`/`jubjub` | L-XL depends + Rust consumers |
| FFI | See **cxx questions** below | M-L if adopting cxx; unknown if C header can be kept |
| Consensus glue | Buffer proofs in `ContextualCheckBlock` (today eager per-tx); batch-fail policy | M |
| Hand-port alternative | `groth16-batch-poc` Phases 0-1 prove math on pinned crates; Phase 2 = FFI + `main` only, no crate migration, no sig batching | M after decide A |

**Decision inputs, not a schedule:** Option B is a release-scale migration if done like current zcashd (depends + bridge + Sapling verify + regression). Option A is narrower (Phase 2-3 on pinned crates) but omits signature batching and keeps in-house crypto review. Next engineering choice after baseline numbers: Pirate/zcashd bridge inventory **or** Option A Phase 2 FFI sketch -- not both in parallel.

**Lab host:** this ZeroPerf machine is arm64; deployment fleet mix remains unknown.

#### cxx questions

**What `cxx` is:** the [cxx](https://cxx.rs/) crate generates a typed bridge between C++ and Rust so each side can call the other with real types, instead of hand-written `extern "C"` plus raw pointers/bytes. Modern `zcashd` uses this pattern for Sapling (`rust::Box<...>`, generated bridge headers). Pirate mirrors that shape in a vendored `src/rust/` crate.

**What Zero has today:** `librustzcash.h` and raw `extern "C"` entry points (e.g. `librustzcash_sapling_check_spend`). No in-tree `cxx` bridge.

**Open questions** for the Option A/B spike: `PerfGroth.md`, which owns Groth16.

**Doc ownership:** this file only. Do **not** edit Zero400 **TODO** / ExtTests / UpdateZero from the ZeroPerf lab track until a deliberate merge.

**Where `ShutdownRequested()` / `fRequestShutdown` are checked today**

| Location | Role |
|----------|------|
| `bitcoind.cpp` main loop | Exit when shutdown requested |
| `init.cpp` AppInit / tip wait / return | Abort init / return false |
| `main.cpp` VerifyDB loop | Break verification early |
| `zeronode.cpp` | Early return on some paths |
| `sendalert.cpp` | Wait loops |
| `zcbenchmarks.cpp` | Abort bench |
| Deprecation gtest | Expect flag after alert threshold |

**Not sufficient alone:** setting the flag does not stop CPU-bound work until that thread hits `interruption_point()` or polls `ShutdownRequested()`.

**Add shutdown polling where CPU stays hot (updated item)**

Prefer `interruption_point()` on Boost worker threads; add explicit `ShutdownRequested()` returns in long CPU loops that may not be interruptible yet.

| Tier | Function / area | Why (CPU) | Mechanism |
|------|-----------------|-----------|-----------|
| T0 | `LoadBlockIndexDB` `vSortedByHeight` + map build (`main.cpp`) | Multi-minute index reconcile | `interruption_point()` every N -- **FIX-LBI done** |
| T0 | `ThreadImport` / `LoadExternalBlockFile` between files / progress (`init.cpp` / `main.cpp`) | Full reindex / bootstrap on `zcash-loadblk` | `ShutdownRequested()` -- **FIX-IMPORT-POLL done** |
| T1 | `ConnectBlock` / `ContextualCheckBlock` outer per-block path on import | Dominant reindex CPU (Groth16 inside) | Rely on thread interrupt at block boundaries; optional flag check per block |
| T1 | PoW verify in header checks (reindex) | Smaller but steady | Optional every N headers |
| T2 | `BuildWitnessCache` wallet rebuild | Fat-wallet start | Flag check between heights |
| -- | Signal handlers | -- | **Never** call `exit()`; only set atomics |

**ID note:** Tiers **T0-T2** are interrupt-site ordering in this subsection only. Lab priorities remain **G** / **P1-P4** in §0.2.

Do **not** spray checks into every Groth16 pairing call (overhead). Boundaries of blocks/files/heights are enough.

#### debug.log reopen

Explain `create`; validate Linux / Windows.

**What `create` means (logrotate):** after rotating (renaming) the old `debug.log`, logrotate's `create mode owner group` creates a **new empty file at the original path** before `postrotate`. That matches what `freopen(..., "a", fileout)` expects: a path named `debug.log` exists again. Equivalent manual step: `mv debug.log debug.log.1 && touch debug.log && kill -HUP $PID`.

Without `create`/`touch`, behavior depends on OS/`freopen`: the process may keep writing to the renamed inode until reopen succeeds. **macOS validated** with touch+HUP+`-debug=rpc` (new file received lines; rotated size unchanged).

**Validation plan (not yet run here)**

| Platform | Steps | Pass criteria |
|----------|-------|---------------|
| **Linux** | Install/sample logrotate snippet with `create 0600` + `postrotate kill -HUP $(cat datadir/.../zerod.pid)`; or manual mv/touch/HUP; force `-debug=rpc` traffic | New `debug.log` grows; `.1` does not; process stays up |
| **Windows** | No SIGHUP. Document: rotate by stopping node or using copytruncate-style tooling; or implement/confirm reopen trigger if any Win path exists (today reopen is SIGHUP-only) | Expected: **graceful rotate via SIGHUP is POSIX-only**; Windows ops use stop/start or external copy while stopped |
| **macOS** | Done | -- |

#### Windows signals

Expected behavior and validation plan.

POSIX `sigaction(SIGTERM/SIGINT/SIGHUP/SIGPIPE)` is under `#ifndef WIN32` in `init.cpp`. This tree has **no** `SetConsoleCtrlHandler` wiring for Ctrl+C -> `StartShutdown()`.

| Event | Expected / observed | Validation |
|-------|---------------------|------------|
| RPC `stop` | `StartShutdown()` -> interrupt -> `Shutdown()` | `zero-cli stop`; clean exit; datadir lock released |
| Console Ctrl+C | **Observed:** does **not** exit immediately. Delay is consistent with orderly teardown / **updating stores** (`Shutdown()`: wallet `Flush`, `FlushStateToDisk`, LevelDB/BDB close, zeronode dumps) rather than an instant kill | Confirm `Shutdown: In progress...` (or equivalent) in `debug.log` before process exit; note wall time vs tip/wallet size |
| Console close / kill | May still be abrupt depending on host/console | Document if different from Ctrl+C |
| SIGHUP / logrotate reopen | **N/A** (POSIX-only) | No parity claim |
| Service stop (if hosted) | Wrapper-dependent | Note only |

**Code vs observation:** in-tree `zerod` does not register a Win32 console handler; if Ctrl+C still triggers a multi-second exit with store flushes, record **which binary** (`zerod` / Qt / wrapper) and console host produced that path on the validation machine. Do not assume POSIX SIGINT semantics on Windows.

**Plan:** Windows smoke: (1) RPC stop clean; (2) Ctrl+C -- expect delayed exit + store flush evidence in log; (3) no SIGHUP logrotate claim.

## 6. Sapling Groth16 batch-verification headroom: scoped, not implemented

**Reviewers:** start at §0.0 **Review packet** and §0.1a; this section is the evidence trail (call path, crate facts, ecosystem). Decision is open -- nothing here chooses A vs B.

**The question (§0 item 4).** §2 found Sapling Groth16 proof verification dominating post-Sapling CPU (48-55% chain-wide). Does `bellman` (Zero's pinned `librustzcash` Groth16 implementation) support batch verification, and could that work run on the currently-idle `zcash-scriptch` threads?

**Confirmed: every proof is verified independently, on one thread, with no batching anywhere in the call chain.** `bellman::groth16::verifier::verify_proof` (`bellman/src/groth16/verifier.rs`, pinned via `librustzcash` commit `06da3b9ac8f278e5d4ae13088cf0a4c03d2c13f5`, fetched fresh from upstream since the depends cache only stores the built `.a`/`.h`, not source) takes exactly one `Proof`/one set of public inputs and does one 3-pairing Miller loop + one final exponentiation -- no loop, no batch parameter, no alternate entry point. `librustzcash_sapling_check_spend`/`_check_output` (`librustzcash/src/rustzcash.rs`) each wrap a single `verify_proof` call and are invoked once per `SpendDescription`/`OutputDescription`, from `ContextualCheckTransaction` (`main.cpp`), which `ContextualCheckBlock` calls via a plain `BOOST_FOREACH` over `block.vtx` -- sequential, single-threaded, on the same worker thread that does everything else during reindex (`zcash-loadblk`). This confirmed the "structural, not fundamental" framing from §0: `ContextualCheckInputs`' `CScriptCheck`/`scriptcheckqueue` dispatch (the thing that actually wakes `zcash-scriptch` threads) covers *only* transparent script/signature verification and is wired up entirely separately from, and after, `ContextualCheckBlock`'s Groth16 checks -- the two paths never share a queue, so idle `zcash-scriptch` threads structurally cannot pick up Groth16 work without new wiring, not because of any inherent limitation in the proof system.

**Confirmed: real batch-verification support exists, but only in a materially newer `bellman`.** The maintained successor `zkcrypto/bellman` (the pinned `ebfull/bellman` is ~2019-vintage; `zkcrypto/bellman` is its modern continuation) ships `groth16/src/verifier/batch.rs` plus a `groth16/benches/batch.rs` benchmark -- a real, tested feature, not a proposal. It implements the standard random-linear-combination technique: for N proofs sharing one `VerifyingKey`, draw a random scalar `z_i` per proof, fold each proof's `(A, B, C)` terms and public inputs into running accumulators weighted by `z_i`, then do **one multi-Miller-loop + one final exponentiation for the whole batch** instead of N independent ones -- collapsing the batch's expensive final-exponentiation count from O(N) to O(1). A `verify_multicore` variant additionally shards the batch into `rayon` `par_chunks(8)` work-items, run over `rayon`'s global threadpool, then reduces the partial Miller-loop results -- real, existing parallel-execution code, not something to build from scratch.

**But this is not a drop-in upgrade.** Modern `bellman`'s `groth16` crate requires `edition = "2021"`, `rust-version = "1.60"`, and depends on `ff 0.13`/`group 0.13`/`pairing 0.23`/`bls12_381 0.8` -- all from the post-2020 `ff`/`group` trait-split redesign of the Rust pairing-crypto ecosystem. The pinned crate stack (`pairing 0.14.2`, path-dependency, `rand 0.4`, no `ff`/`group` split at all) predates that redesign entirely. Adopting `zkcrypto/bellman`'s `batch.rs` as-is would mean migrating Zero's entire `librustzcash`/`bellman`/`pairing`/`jubjub` stack across that ecosystem-wide API break -- a large, separate undertaking, not a small patch.

**The good news: the core primitive the algorithm needs already exists in the pinned crate, so a hand-ported batch verifier is feasible without that migration.** The pinned `pairing::Engine` trait (`pairing/src/lib.rs`) already defines `miller_loop<I>(i: I) -> Fqk` accepting an arbitrary-length iterator of `(G1Affine::Prepared, G2Affine::Prepared)` pairs -- `verify_proof` itself already calls it with 3 pairs per single-proof check. `CurveAffine::prepare()`/`::Prepared` are likewise already present. This means the random-linear-combination batching math (accumulate weighted terms across N proofs, feed them all into one `miller_loop` call, one `final_exponentiation`) can be hand-ported into the pinned `bellman`/`pairing` version without a crate upgrade -- the trait shapes line up. What pinned `bellman` lacks and would need adding: the accumulator/random-scalar bookkeeping itself (straightforward to port from `batch.rs`'s logic), and -- for the multicore variant specifically -- a parallel-execution primitive, since `rayon` isn't in the pinned crate's dependencies (`futures-cpupool`/`crossbeam`/`num_cpus` are present but used only by the *prover*, e.g. FFT/multi-exponentiation in `prover.rs`, never the verifier).

**What this changes for a real implementation, beyond the crypto:**
- **Batching requires buffering proofs before verifying them**, which doesn't fit `ContextualCheckTransaction`'s current per-transaction, immediate-verify-or-reject control flow (`ContextualCheckBlock`'s `BOOST_FOREACH` calls it once per tx and expects an immediate pass/fail). A batched version would need to collect all of a block's Sapling spend/output proofs first, verify the batch once, and only then be able to say a proof failed -- with the caveat noted in `zkcrypto`'s own doc-comment: batch verification confirms *all* proofs are valid but "loses the ability to easily pinpoint failing proofs," so a failed batch needs a fallback to per-proof `verify_single` to identify which transaction to reject (already provided for exactly this purpose by `Item::verify_single` in `batch.rs`).
- **The random verifier scalars need a CSPRNG**, sourced per block (or per batch) -- a new input this call path doesn't currently have.
- **Consensus-criticality**: unlike §3/§4's fixes (pure memoization, no change to what's computed), swapping single-proof verification for batch verification changes the exact sequence of cryptographic operations performed to reach a pass/fail -- this needs the same scrutiny consensus-code changes always require, even though the math is a standard, published technique (not novel here).

**Not started, deliberately scoped no further than this.** Per §0 item 4, this was a research/scoping task, not an implementation. Estimated headroom: collapsing N final-exponentiations to 1 per batch, against a bucket that's 48-55% of chain-wide CPU (§2), is a substantial, structurally-supported target -- but realizing it requires (a) hand-porting the batch algorithm using the pinned crate's existing `miller_loop` primitive, (b) restructuring `ContextualCheckBlock`'s per-tx control flow to buffer-then-batch-verify, and (c) deciding whether to also port a parallel accumulation path (would need vendoring a `rayon`-equivalent, or reusing the existing `futures-cpupool`/`crossbeam` machinery `prover.rs` already depends on) to actually engage otherwise-idle cores. None of this is started.

### 6.1 Ecosystem check: is there a more advanced, already-shipped batch verifier? Yes -- and it changes the picture.

**The question.** §6 above frames the work as "hand-port `zkcrypto/bellman`'s `batch.rs`." Before committing to that path, this subsection checked: is the pinned `librustzcash` (Oct 2018) actually the latest available, or has the ecosystem moved further -- and if so, does upstream already ship a *complete* batch verifier (not just the low-level pairing primitive), that a hand-port would be reinventing?

**Finding: the ecosystem has moved substantially, and `zcash/librustzcash`'s current `main` no longer contains `bellman`/`pairing`/`sapling-crypto` at all.** Fetched `zcash/librustzcash`'s current `main` (commit `1c7f7d86`, 2026-07-09 -- actively maintained, pushed same day as this check). Its workspace (`Cargo.toml`) no longer includes `bellman`, `pairing`, `sapling-crypto`, or `librustzcash` (the FFI crate itself) as members at all -- these have been split out into independently-versioned, separately-published crates: `bellman = "0.14"` (crates.io, last published 2023-03-20, `zkcrypto/bellman`'s modern continuation -- the same repo §6 above already investigated) and `sapling = { package = "sapling-crypto", version = "0.7" }` (crates.io, `zcash/sapling-crypto`, last released 2026-04-21). The 2018-era all-in-one monorepo layout this repo's pin (`06da3b9ac8f278e5d4ae13088cf0a4c03d2c13f5`) reflects is not how the ecosystem is structured today -- it's a snapshot from a much earlier point in a since-heavily-refactored dependency graph.

**Bigger finding: `sapling-crypto` already ships a complete, production Sapling `BatchValidator` -- not just the low-level pairing primitive `batch.rs` provides.** Fetched `zcash/sapling-crypto` at its current release (`v0.7.0`) and read `src/verifier/batch.rs` in full. `sapling_crypto::BatchValidator` (traces back to `zcash_proofs::sapling::BatchValidator`, added in `zcash_proofs` v0.7.1, **2022-07-05** -- this has been in production for roughly four years) does everything §6/§9.4's plan set out to hand-build:
- `check_bundle(bundle, sighash)` -- walks a Sapling transaction bundle's spends and outputs, runs the *same* per-item consensus checks the pinned `check_spend`/`check_output` do (small-order checks, anchor/nullifier handling), but **queues** the Groth16 proof and the RedJubjub `spend_auth_sig`/binding signature into batch verifiers instead of checking them immediately -- `self.spend_proofs.queue(...)`, `self.output_proofs.queue(...)`, `self.signatures.queue(...)`.
- `validate(spend_vk, output_vk, rng)` -- batch-verifies everything queued: signatures first (`redjubjub::batch::Verifier`), then Sapling spend proofs and output proofs each via `groth16::batch::Verifier::verify`/`verify_multicore` (the exact `bellman` `batch.rs` code §6 already found) -- three separate batches, not one combined batch, each against its own verifying key.
- **This batches signatures too, not just Groth16 proofs** -- something §6/§9.4's plan didn't scope, since the pinned FFI's `check_spend` verifies `spend_auth_sig` eagerly per-call (§9.4 Phase 0 finding). Batch-verifying RedJubjub signatures is a separate, real technique (also random-linear-combination-based) with its own headroom, orthogonal to Groth16 batching.
- Returns a single pass/fail for the whole batch, with the same "can't pinpoint which proof failed" limitation `batch.rs` itself documents -- callers needing attribution re-verify individually, same tradeoff §9.4's Phase 4 fallback design already anticipated.

**Confirmed in real production use, not experimental:** `sapling_crypto::BatchValidator` is used directly by Zebra (Zcash Foundation's Rust full node) in `zebra-consensus/src/primitives/sapling.rs`, wrapped in a `tower_batch_control::Batch` async service (`zebra-consensus/src/primitives.rs`) with real, tuned production parameters: **`MAX_BATCH_SIZE = 64`, `MAX_BATCH_LATENCY = 100ms`** -- i.e. Zebra batches up to 64 Sapling proofs or waits at most 100ms, whichever comes first, before flushing a batch through `BatchValidator::validate`. This is the answer to "how big should a batch be" that §9.4's plan left unspecified -- a real, shipped, presumably-tuned answer, not a guess.

**What this means for §9.4's plan.** Two paths now exist, and they trade off differently:

1. **Hand-port** (§9.4 as written): port only the random-linear-combination math into the *pinned* 2018-era `bellman`/`pairing`, keeping Zero's entire crate stack otherwise unchanged. Smaller footprint, no crate-version migration, but reinvents logic that upstream has already built, hardened, and run in production for ~4 years -- including the signature-batching piece §9.4 didn't originally scope at all.
2. **Adopt `sapling-crypto` directly** (not previously considered): migrate Zero's Sapling verification call path to depend on the current, maintained `sapling-crypto`/`bellman 0.14`/`bls12_381`/`group`/`ff`-split crate stack, and call `BatchValidator` as-is -- the same code Zebra runs today. Larger footprint (the crate-stack migration §6 above already flagged as "a large, separate undertaking"), but gets a battle-tested implementation, signature batching for free, and a real precedent for batch-size tuning (`MAX_BATCH_SIZE`/`MAX_BATCH_LATENCY`), instead of hand-porting and re-validating logic that already exists.

**This is a genuine fork in the road that should be decided before Phase 2 of §9.4 proceeds** -- not resolved here. The hand-port path is still valid and its Phase 0-1 groundwork (already executed -- see §9.4) isn't wasted (the math is the math either way, and the standalone prototype validated it works against real proofs), but "reuse the upstream crate that Zebra already runs in production" is a materially different, and arguably lower-total-risk, option that wasn't on the table when §6/§9.4 were originally scoped. Not sized or investigated further here (crate-migration cost, C++/Rust FFI shape against the newer crate stack, and whether `librustzcash`'s current C FFI layer -- if one still exists at this pin -- could be reused rather than hand-rolled, are all open).

*Investigation steps, in order:*
1. Pull the exact pinned `librustzcash` commit (`06da3b9ac8f278e5d4ae13088cf0a4c03d2c13f5`) and read `verifier.rs` end to end; confirm `Proof`/`VerifyingKey`/`PreparedVerifyingKey` struct shapes match what `zkcrypto/bellman`'s `batch.rs` accumulator logic needs field-for-field -- `batch.rs` was written against the post-split `ff 0.13`/`group 0.13`, the pinned crate predates that split entirely, so every type substitution needs individual checking, not just the top-level call signature.
2. Prototype the batch math as a standalone Rust unit, outside the FFI boundary first -- a `#[cfg(test)]`-only batch-verify function against the pinned `bellman`/`pairing` crates, fed known-good and known-bad Groth16 proofs from the existing prover test fixtures. Validates the ported math against known-answer vectors before touching any FFI/consensus surface.
3. Design the FFI/buffering boundary before writing Rust: current `librustzcash_sapling_check_spend`/`_check_output` are eager, per-description, return `bool` immediately. Decide the batched shape -- e.g. a defer/collect call plus a `librustzcash_sapling_batch_validate` call returning per-item pass/fail or an opaque failure index, vs. collecting proofs block-side in `main.cpp` and passing an array across one new FFI call.
4. Restructure `ContextualCheckBlock`'s control flow: collect all Sapling spend/output proofs across the block's transactions first, batch-verify once, and only on batch failure fall back to per-proof `verify_single` (already provided in `batch.rs` for exactly this) to identify which transaction/description to reject -- the existing per-description error codes (`bad-txns-sapling-spend-description-invalid` etc., `main.cpp:1131,1146`) must still point at the correct tx for RPC/ban-scoring correctness.
5. Source the per-batch CSPRNG -- a new input this call path doesn't have today; check `random.h`/existing `GetRandBytes`-equivalent usage elsewhere in `main.cpp` for the process's existing secure-RNG convention, sourced fresh per block (or per batch), never reused across batches.
6. Scope the consensus-safety review as its own step, separate from perf measurement: unlike §3/§4 (pure memoization, no change to what's computed), this changes the actual sequence of cryptographic operations used to reach pass/fail -- get independent review of the ported math specifically, regardless of whether the perf win materializes.

*Test plan:*
1. Known-answer-vector tests in Rust, before FFI: feed the standalone prototype (investigation step 2) mixes of all-valid and one-invalid-among-N proof sets; assert batch accept/reject matches per-proof `verify_proof` exactly, across N = 1, 2, 8, 64.
2. New C++ gtest mirroring §4's `merkletree.RootCacheConsistency` precedent -- exercise the new FFI entry point(s) directly with fixtures reused from `zcbenchmarks.cpp`'s existing Sapling spend/output benchmark inputs (`zcbenchmarks.cpp:706,739` already construct valid spend/output descriptions for benchmarking).
3. Adversarial/negative tests: corrupt one proof in a batch of N (bit-flip `zkproof`, wrong `anchor`, wrong `nullifier`); confirm the batch fails, then confirm the `verify_single` fallback correctly identifies *which* item -- the specific property `zkcrypto`'s own doc-comment flags as the hard part of batching.
4. Full existing regression suite unchanged and clean: Boost `test_bitcoin` (284/284 baseline) and `zero-gtest` (205-207/207 baseline, 2 known pre-existing flakes) -- same bar §4 was held to.
5. Real-chain differential test: `-reindex` over a real post-Sapling height range (reuse §2's already-sampled windows, e.g. 610,758-626,806 or 995,392-1,083,180) on both batched and unbatched binaries; diff resulting `chainstate`/best-block-hash -- must be byte-identical. Strongest available correctness check since it's not synthetic.
6. Perf re-measurement with the existing tooling: same Instruments/`xctrace` methodology as §2 (`contrib/perf/capture_sequence.sh` + `decode_captures.py`), same height windows, for a directly comparable before/after Groth16-bucket percentage and ms/block figure; plus a `bench_matrix.sh`-style throughput A/B with the same statistical rigor (t-test, n>=4 trials) §3 used -- §3's "implemented but no measurable win" outcome is a reminder not to skip this step.
7. If the multicore/parallel-accumulation variant is pursued: a separate throughput test varying `-par`/thread count, since the entire point there is engaging otherwise-idle `zcash-scriptch`-adjacent cores -- measure scaling, not just single-thread speedup.

### 9.4 Groth16 batch verification: full execution plan

Confirmed this session, and load-bearing for the plan below: the actual FFI signatures at the boundary this work has to cross (`depends/aarch64-apple-darwin25.3.0/include/librustzcash.h:139-175`) -- `librustzcash_sapling_check_spend(ctx, cv, anchor, nullifier, rk, zkproof, spendAuthSig, sighashValue)` and `_check_output(ctx, cv, cm, ephemeralKey, zkproof)` take **raw serialized proof bytes**, not a pre-parsed `Proof` struct -- deserialization currently happens inside each Rust call, once per call. No `librustzcash` Rust source is vendored in this repo (only the built header/`.a` under `depends/aarch64-apple-darwin25.3.0/`) -- same situation as libsodium (§5/§9.2): the pinned source has to be fetched fresh for any of this to be real editable code, not assumed from the header alone.

**Phase 0 -- Setup (no code changes): DONE.** Fetched `zcash/librustzcash` at the pinned commit into an isolated scratchpad checkout (`/private/tmp/.../scratchpad/groth16-batch/librustzcash-pinned`, outside this repo -- no tracked files touched). Findings, reading the real source rather than assuming from the header:

**Spike result, 2026-08 (scratch only -- nothing landed in Zero).** A
standalone spike outside this tree confirmed the algorithm is portable: the
random-linear-combination batch verifier from `zkcrypto/bellman` was
hand-ported against the pinned `bellman`, and batch accept/reject matched
per-proof `verify_proof` exactly at N=1, 2, 8 and 64, including single-invalid
detection. It establishes feasibility and nothing more -- **no Zero code was
changed, no measurement of Zero was taken, and the FFI question below is
untouched by it.**

The FFI constraint the spike confirmed: `librustzcash_sapling_check_spend` and
`_check_output` take raw serialized proof bytes and deserialize per call, so
batching requires either buffering at the C++ boundary or a new entry point.


**Phase 1 -- Pure-Rust correctness, zero consensus exposure: DONE.**

4. ~~Write a batch-verify function~~ Done -- hand-ported the random-linear-combination algorithm from `zkcrypto/bellman`'s `batch.rs` into a real standalone binary crate (`batch-poc/src/main.rs` in the scratchpad, path-dependent on the pinned `bellman`/`pairing`, **not** vendored into or built by this repo), using only the pinned crate's confirmed-present primitives from item 3 above.
5. ~~Generate known-good/known-bad proof fixtures~~ Done, via a stronger source than originally planned: rather than reusing `zcbenchmarks.cpp`'s Sapling fixtures (which need the full Sapling circuit + trusted setup), used `bellman`'s own real end-to-end test circuit (`bellman/tests/mimc.rs`'s MiMC/BLS12-381 construction) to generate genuine `generate_random_parameters`/`create_random_proof` Groth16 proofs -- real proofs over the real pinned Bls12 engine, not synthetic stand-ins.
6. ~~Test N = 1, 2, 8, 64~~ Done and passing: all-valid batches at N=1,2,8,64 -- batch accept exactly matches per-proof `verify_proof` (`reference_ok == batch_ok == true`) on every run. One-corrupted-proof-among-N at N=2,8,64 -- batch correctly rejects and agrees with the reference that not all proofs were individually valid. Re-ran 6 times total (fresh circuit parameters and fresh random proofs each run, real `thread_rng()`) -- zero disagreements across all runs.
7. **Exit criterion: MET.** The standalone batch verifier agrees with per-proof `verify_proof` on every fixture generated, including adversarial (corrupted) ones, across repeated runs with fresh randomness. Phase 2 is unblocked by this criterion, but **not started** -- see the status note at the end of this section.

**Phase 2 -- FFI boundary design**

8. Design the new entry point: `librustzcash_sapling_batch_validate(ctx, n, cv[], anchor[], nullifier[], rk[], zkproof[], spendAuthSig[], sighashValue[], out_results[])` -- collect-then-call, since `main.cpp` already has all spend/output data in hand per-block. Keep the existing single-proof functions exported unchanged -- they're needed for Phase 4's fallback.
9. Source the per-batch CSPRNG: match whatever secure-RNG convention existing consensus code already uses (grep `main.cpp`/`random.h` for `GetRandBytes`/`GetStrongRandBytes`) -- freshly drawn per batch, never reused.
10. Implement the new FFI function in the fetched checkout, wrapping Phase 1's proven logic, adding only the accumulator/random-scalar bookkeeping to the pinned `bellman` (no crate upgrade -- the `miller_loop` shape already matches per §6). Skip the multicore/`rayon` variant here -- separable, later work, not required for the O(N)->O(1) final-exponentiation win.
11. Build `librustzcash.a` from the modified checkout; confirm it links against `main.cpp` with a local copy of `librustzcash.h` carrying the new declaration (the depends-built header is normally auto-fetched, so a dev-local header is needed until this is upstreamed into the depends pin).

**Phase 3 -- Shadow-mode integration in `main.cpp` (the safety-critical step)**

12. In `ContextualCheckBlock`/`ContextualCheckTransaction` (`main.cpp:1113-1164`), buffer all of a block's Sapling spend/output proofs as they're encountered, **without changing the existing sequential `check_spend`/`check_output` calls or their control flow** -- those remain sole authority for accept/reject, exactly as today.
13. After the existing per-proof checks complete for the block, also run the new batch-verify function over the same buffered proofs as a pure side-check. Log any disagreement loudly (a dedicated tag, e.g. `LogPrintf("groth16batch", ...)`) but never let it affect `state.DoS(...)`/accept-reject. This is deliberately wasted CPU during the shadow period -- the price of a free, continuous differential test.
14. Run this shadow-mode build through real `-reindex`/sync activity spanning both pre- and post-Sapling heights -- reuse the exact height windows already sampled in §2/§3 (610,758-626,806; 995,392-1,083,180; the full six-capture chain-wide sweep) so results are directly comparable to existing baselines.
15. **Exit criterion:** zero disagreements between shadow batch-verify and the authoritative sequential path across a large, real, chain-wide sample. Any disagreement found here sends the work back to Phase 1.

**Phase 4 -- Controlled cutover**

16. Flip the batch path to authoritative for the accept case only, behind a build/runtime flag, matching the perf-flag convention. On batch success, accept as today. On batch failure, fall back to the existing per-proof path (`verify_single`) to get the real, individually-attributed failing transaction/description before rejecting -- preserving today's exact error codes (`bad-txns-sapling-spend-description-invalid` etc., `main.cpp:1131,1146`) so RPC/ban-scoring behavior is unchanged.
17. Add an explicit test for the fallback path itself: construct a batch where batch-verify wrongly reports failure (or a genuinely bad-proof batch) and confirm the fallback correctly re-derives the same accept/reject the pre-batch code would have, unassisted.

**Phase 5 -- Full validation**

18. Adversarial tests: bit-flip `zkproof`/`anchor`/`nullifier` in one proof among N; confirm the batch fails and the fallback correctly identifies the specific bad transaction.
19. Full regression: Boost `test_bitcoin` (284/284 baseline) and `zero-gtest` (205-207/207, 2 known pre-existing flakes) -- same bar as §3/§4.
20. Real-chain differential test: `-reindex` the same height range on both the batched (flag-on) and baseline (flag-off) binaries; diff resulting `chainstate`/best-block-hash -- must be byte-identical.
21. Perf re-measurement: same `contrib/perf/capture_sequence.sh`/`decode_captures.py` methodology and height windows as §2, for a directly comparable before/after Groth16-bucket ms/block figure, plus a `bench_matrix.sh`-style throughput A/B (n>=4 trials, t-test). A mechanism can work exactly as designed and still show no measurable win, so measure rather than assume.

**Phase 6 -- Sign-off**

22. Independent review of the ported batching math against the published random-linear-combination technique and the pinned crate's real types -- not just a diff review -- before removing the Phase 4 fallback and treating this as the sole verification path.
23. Optionally, only after all of the above: the multicore/`rayon`-equivalent variant to also engage idle `zcash-scriptch`-adjacent cores -- a separate, additive project, not a prerequisite for the O(N)->O(1) win.

**Status: Phases 0-1 executed and passing (see findings inline above); Phases 2-6 deliberately not started.** Phase 0/1's artifacts (the pinned-commit checkout and the `batch-poc` scratch crate) live outside this repo, under the session scratchpad -- nothing in `depends/`, `src/`, or any tracked file was modified to produce these results. Phases 2-6 were intentionally not run in the same pass: Phase 2 begins touching build/link configuration, and Phase 3 edits `main.cpp`'s consensus-critical block-validation path -- exactly the step this plan's containment strategy (§9.3) exists to gate carefully rather than run through unattended. Stopped here for explicit direction before proceeding, consistent with §9.3's core principle (never let the batched path be the only path) extended to the process of building it: don't let unattended execution be the only check on consensus-code changes either.


### 9.3 Recommended path: Groth16 batch verification, made controlled

§6 already has a 6-step investigation plan and 7-step test plan. **§9.4 below supersedes both with a single, ordered, numbered execution plan** -- grounded in the real FFI signatures confirmed from `depends/aarch64-apple-darwin25.3.0/include/librustzcash.h` -- that merges §6's investigation/test content with this section's containment strategy into one sequence a developer can actually start from.

**Core principle: never let the batched path be the only path.** Every phase in §9.4 keeps the existing, proven single-proof `verify_proof` call as a mandatory fallback or cross-check, so a bug in the new code can only cause *extra* verification work, never a wrong accept/reject -- until the very last, explicitly-flagged phase.

**Why this is more work than "port `batch.rs` and test it," and worth it anyway:** the failure mode being guarded against -- a false-accept of an invalid shielded proof -- is categorically worse than anything else in this investigation has touched (§3/§4's fixes were pure memoization with no semantic change; this one isn't). The shadow-mode phase in §9.4 turns every day of ordinary development/testing activity into free differential-testing signal against real chain data before the new path is ever trusted to decide anything alone -- a substantially stronger validation posture than a fixed test suite alone can provide for a change of this kind.


---

## librustzcash: what Zero depends on, and how far it has drifted

Groth16 verification is librustzcash's job, so any batch-verification work
rests on this dependency. Established 2026-09-08 from the upstream repository
(`ZK/ZKs/librustzcash`, updated to `5e770a91`, 2026-09-03).

### The pin

| | |
|---|---|
| Zero pins | `06da3b9a`, **2018-10-27** |
| Upstream HEAD | `5e770a91`, 2026-09-03 |
| Distance | **6724 commits**, ~7 years |

The pin lives in `depends/packages/librustzcash.mk` as `_git_commit`, fetched
as a GitHub archive tarball rather than a Cargo dependency.

### The crate Zero depends on no longer exists upstream

`librustzcash/README.md` at HEAD reads, in full:

> This crate has been moved into https://github.com/zcash/zcash.

The C FFI -- the `librustzcash_*` entry points Zero links -- is now in
`zcash/zcash` under `src/rust/`, described there as *"Rust FFI used by the
zcashd binary. Not an official API."* Upstream `librustzcash` is now a
workspace of published Rust crates (`zcash_primitives`, `zcash_proofs`,
`zcash_protocol`, ...) with no C surface.

**Consequence for any upgrade.** There is no newer version of the thing Zero
pins. Moving forward means either following the FFI into `zcash/zcash`, or
consuming the Rust crates directly and writing the FFI Zero needs. That is the
same decision recorded above as Option A/B, and this is the evidence that it
cannot be deferred indefinitely: the dependency is discontinued at the point
Zero consumes it.

### How the family consumes it

| Project | Mechanism | Pin |
|---|---|---|
| **Zero** | depends tarball, C FFI | `06da3b9a` (2018-10-27), upstream |
| hush3 | depends tarball, C FFI | `06da3b9a` -- identical to Zero |
| Ycash | Cargo `rev` | `cc26e791`, **not an upstream commit** -- own fork |
| Pirate | Cargo `rev` | `c5098346`, **not an upstream commit** -- own fork |
| **Zebra** | **published crates** | `zcash_primitives = "0.28"`, `zcash_proofs = "0.28"`, `zcash_protocol = "0.9"` |

Three distinct strategies. Zero and hush3 share a 2018 upstream commit; Ycash
and Pirate each maintain a fork; **Zebra alone consumes versioned crates**, and
is therefore the only one of the five that can take an upstream fix without a
merge.

Zebra is also the only one with no C FFI at all -- it is Rust end to end, so
the FFI-shape question that dominates Zero's Option A/B does not arise for it.
That makes Zebra a poor model for Zero's migration but a useful demonstration
that the crates are consumable as published artifacts.

### What Groth16 actually uses today

**librustzcash version:** the 2018 pin `06da3b9a`, via `depends`. Checkouts of
every generation for direct comparison: `ZK/ZKs/rustzcash/`.

**The consensus verification path is four functions, all in `main.cpp`:**

| Function | Role |
|---|---|
| `librustzcash_sapling_verification_ctx_init` | open a batch context |
| `librustzcash_sapling_check_spend` | verify one Spend proof |
| `librustzcash_sapling_check_output` | verify one Output proof |
| `librustzcash_sapling_final_check` | binding-signature check |
| `librustzcash_sapling_verification_ctx_free` | close |

`zcbenchmarks.cpp` calls the same set for `verifyequihash`-style benchmarks.
The proving side (`sapling_spend_proof`, `sapling_output_proof`,
`sapling_proving_ctx_*`) is wallet-only and not on the sync path.

**The context already exists.** `..._ctx_init`/`_final_check` bracket the
per-block loop, so there is a batch scope in the C++ today -- what is missing is
an entry point that defers verification into it rather than verifying eagerly
per spend and per output.

**libsodium's role in Groth16: none.** Sapling proof verification is entirely
Rust-side. libsodium appears elsewhere in the same block-validation path --
Ed25519 for JoinSplit signatures, blake2b for sighash -- but not inside proof
verification. The division is `../docs/HASHLIBS.md`; it is not restated here.

### Who maintains this code

Commits since 2022, whole repository:

| Author | Commits |
|---|--:|
| Kris Nuttycombe | 2696 |
| Jack Grigg | 967 |
| Danny Willems | 387 |
| str4d | 216 |
| Daira-Emma Hopwood | 154 |

**But `zcash_proofs` -- the crate Zero's verification path sits on -- has taken
3 commits since 2022**, all release bumps. The proving code itself moved out to
an external `sapling-crypto` crate (0.7), and the 6724 commits are concentrated
in wallet, transparent-pool and Orchard work.

That is the useful shape of the answer: **the code Zero depends on is not being
actively rewritten; the repository around it is.** An upgrade would import
years of change to crates Zero does not use, in order to reach a proving path
that has barely moved.

### What 6724 commits went into

Not tweaks. The repository was restructured and its scope changed several
times. By year: 125 (2018), 420 (2019), 447 (2020), 525 (2021), 521 (2022),
675 (2023), **1209 (2024), 1052 (2025), 1735 (2026)** -- accelerating, not
winding down.

**The crate set at Zero's pin, and now:**

**At `06da3b9a` (2018):** `bellman`, `pairing`, `sapling-crypto`, `zip32`, `zcash_wallet`, `librustzcash`, `zcash_primitives`, `zcash_proofs`.

**At HEAD (2026):** `zcash_primitives`, `zcash_proofs`, `zcash_keys`, `zcash_transparent`, `zcash_client_backend`, `zcash_client_sqlite`, `zcash_history`, `zcash_pool_migration`, `pczt`, `components`, `zcash`.

**Four of the eight crates Zero's pin contains no longer live here at all.**
`bellman`, `pairing`, `sapling-crypto` and `zip32` were split into their own
repositories; the proving stack Zero links was extracted from under it. In the
other direction, ten crates arrived that did not exist in 2018 -- wallet
backend, SQLite storage, transparent-pool handling, PCZT.

**Release history of the two crates Zero's FFI sits on** (`zcash_primitives`,
matching `zcash_proofs`):

| Version | Date |
|---|---|
| 0.5.0 | 2021-03-26 |
| 0.8.0 | 2022-10-19 |
| 0.10.0 | 2023-02-01 |
| 0.13.0 | 2023-09-25 |
| 0.15.0 | 2024-03-25 |
| 0.20.0 | 2024-11-14 |
| 0.25.0 | 2025-09-25 |
| **0.30.0** | 2026-07-24 |

**Twenty-five major versions**, each a breaking change by semver convention.

**Where the work went**, by commits mentioning each theme since the pin:

| Theme | Commits | What it is |
|---|--:|---|
| transparent | 536 | Transparent-pool handling extracted into `zcash_transparent` |
| **Orchard** | **524** | An entire second shielded pool (NU5, 2022) that Zero does not have |
| PCZT | 292 | Partially Created Zcash Transactions -- a signing protocol |
| sync | 58 | Wallet sync engine |
| unified addresses | 30 | UA format across pools |
| ZIP-317 | 27 | Fee mechanism |
| halo2 | 7 | Named rarely because it lives in its own repo |

**The dominant themes are features Zero does not implement.** Orchard, PCZT,
unified addresses and the wallet backend are the bulk of the work, and none of
it reaches a node that has only Sprout and Sapling. That is the argument
against a naive "upgrade to current": most of the distance is scope Zero
declined, not fixes it is missing.

**What that leaves.** The Sapling proving and verifying code Zero actually
calls has moved from `sapling-crypto` + `bellman` into `zcash_proofs` on top of
externally-maintained `bellman`/`bls12_381`. Whether that path carries
arithmetic improvements worth having is **not established here** and is the one
question worth measuring.

### How the family solved this, and what it implies for Zero

| Project | Strategy | Detail |
|---|---|---|
| **Zebra** | Published crates | `zcash_primitives = "0.28"` -- takes upstream releases directly |
| **Ycash** | **Own fork** | `github.com/ycashfoundation/librustzcash`, rev `cc26e791` |
| **Pirate** | **Own fork** | `github.com/piratenetwork/librustzcash`, rev `c5098346` |
| **TENT** | Upstream tarball | `06da3b9a` -- **the same commit as Zero**. Its `librustzcash.mk` was last touched 2021-01-09; the repository stopped at 2021-11 |
| **Zero, hush3** | Upstream tarball | `06da3b9a`, 2018, on a crate that no longer exists |

**Two of the four peers forked; TENT did neither.** Ycash (2021) and Pirate
(2024) each host their own `librustzcash` under their own organisation, because
the upstream shape they consumed stopped being available.

**Why Zero did not pick up TENT's work: there is none to pick up.** TENT pins
the identical 2018 commit, its `librustzcash.mk` was last edited 2021-01-09,
and the repository's last commit is 2021-11-13. It is the same position as
Zero, frozen three years earlier -- not a source of newer work. An earlier note
here said TENT used per-crate pins; that was `fluxd`, a different project, and
the claim is withdrawn.

**Verification is single-threaded by construction.** `bellman` at Zero's pin
ships `src/multicore.rs`, used by `groth16/prover.rs`, `generator.rs`,
`multiexp.rs` and `domain.rs` -- but **not** by `groth16/verifier.rs`. The
threading serves proving; the verification that dominates ConnectBlock runs one
proof per call on one thread. Horizen is the only project in this lineage to
have built the alternative (batched asynchronous verification,
`zen/src/sc/asyncproofverifier.*`), for sidechain certificates rather than
Sapling spends.

**Full trajectory analysis, ecosystem comparison and effort assessment:
`ZK/ZKs/rustzcash/ZcashRust.md`** (out of tree), alongside checkouts of every
generation. In summary: reaching Ycash's level is an FFI delta of **+5/-1
functions**, three of which are one feature Zero does not implement, so the
1127-commit distance overstates the work by a wide margin -- what dominates is
consensus-equivalence testing, which is the same size either way.

**Recommendation and its counter-arguments: the Recommendation section at the
end of this document.**

### Effort: what it would cost Zero to reach Ycash or Pirate level

The useful measure is not commit distance but **FFI surface delta**, because
that is what Zero's C++ actually consumes.

| | Exports | vs Zero |
|---|--:|---|
| Zero (2018) | 32 | -- |
| **Ycash** | 36 | **+5, -1** |
| **Pirate** | 41 | +10, -1 |

**Ycash delta, in full:**

| Symbol | Note |
|---|---|
| `librustzcash_sapling_compute_cmu` | **renames** Zero's `_compute_cm` |
| `librustzcash_getrandom` | new |
| `librustzcash_mmr_append` | ZIP-221 history tree |
| `librustzcash_mmr_delete` | ZIP-221 |
| `librustzcash_mmr_hash_node` | ZIP-221 |

Three of the five additions are one feature: **ZIP-221 MMR history trees**,
which Zero does not implement. `_compute_cmu` is a rename of a function Zero
already calls. Strip the MMR feature and the delta is **one rename plus
`getrandom`**.

**Pirate adds a further five**, all wallet: `get_bip39_seed`,
`get_seed_phrase`, `restore_seed_from_phase` [sic], and
`add_sapling_{spend,output}_to_context`. Zero needs none of them.

#### Effort assessment

| Target | Commit distance | FFI delta | Real work | Band |
|---|--:|---|---|---|
| **Ycash level** | 1127 | +5/-1, 3 of 5 are ZIP-221 | Rename one call site; adopt or stub MMR; rebuild; verify consensus equivalence | **M** |
| **Pirate level** | 2462 | +10/-1 | Ycash's work plus wallet FFI Zero will not call | **M-L**, and the extra buys nothing |
| **Zebra level** | n/a | no FFI at all | Rewrite the boundary as Rust-native | **XL**, different architecture |

**The commit counts are misleading and the FFI delta is the honest number.**
1127 commits sounds like a rewrite; the surface Zero consumes moved by one
rename plus an optional feature.

**What the bands do not cover, and what dominates the real cost:** consensus
equivalence. Any change to proof verification must be shown to accept and
reject exactly the same blocks. That testing is the same size whether the delta
is one function or forty, and it is the reason none of this is **S**.

#### Sequence

1. **Fork first, migrate never-or-later.** Take `06da3b9a` into
   `zerocurrencycoin/librustzcash` unchanged. Verified by producing a
   byte-identical `librustzcash.a`. This is custody, not an upgrade, and it is
   the precondition for everything else: today Zero builds from a tarball of a
   third-party repository whose README redirects elsewhere.
2. **Move the C header into Zero's tree**, as Ycash, Pirate and upstream all
   did. Removes the dependency on the crate that no longer exists.
3. **Only then** evaluate whether the proving path has anything worth taking.
   `zcash_proofs` at 3 commits since 2022 suggests it does not, and step 3
   should not be started without a measurement that says otherwise.

Steps 1 and 2 are packaging and carry no consensus risk. Step 3 is where the
equivalence testing lands, and it is optional.

---


### What this does not establish

- **Whether the 6724 commits contain a fix Zero needs.** Not audited. The
  distance is the finding; its contents are not.
- **Whether the FFI in `zcash/zcash` is drop-in.** Its own README disclaims
  API stability.
- **Consensus equivalence of any newer proof code.** Any move requires the
  verification-equivalence testing already specified for Option A/B.

---

## Recommendation for Zero: fork for custody, defer the upgrade

A decision with arguments on both sides, stated so the case against is
answerable rather than absent. Cross-chain evidence: `ZK/ZKs/rustzcash/`
(out of tree).

### The recommendation

**Do (now):**

1. Fork `zcash/librustzcash@06da3b9a` into `zerocurrencycoin/librustzcash`,
   unchanged. Acceptance test: `depends` produces a byte-identical
   `librustzcash.a`.
2. Move `librustzcash.h` into Zero's tree at `src/rust/include/`, matching what
   upstream, Ycash and Pirate all did.

**Do not (yet):** upgrade the pin, adopt Ycash's or Pirate's FFI, or start
batch verification.

### Why -- the arguments for

| Argument | Evidence |
|---|---|
| **The dependency is discontinued at the point Zero consumes it** | `librustzcash/README.md` upstream reads only *"This crate has been moved into github.com/zcash/zcash."* There is no newer version of what Zero pins |
| **The build fetches a third-party tarball** | `depends/packages/librustzcash.mk` downloads `github.com/zcash/librustzcash/archive/06da3b9a.tar.gz`. A reproducible build depends on a URL Zero does not control, for a repository that has moved on |
| **Every peer that faced this forked** | Ycash 2021, Pirate 2024, both under their own organisation, both carrying the header in-tree |
| **It is packaging, not consensus** | No code changes. Byte-identical output is the test, and it either passes or the fork is wrong |
| **It unblocks everything else** | Batch verification, an FFI entry point, a version move -- each needs a repository Zero can commit to. Today there is none |

### The arguments against, and the answers

| Against | Answer |
|---|---|
| *"Nothing is broken -- the build works."* | True, and this changes nothing about the build. The risk is availability and provenance, not function: a deleted tag or a moved archive breaks `depends` with no local fallback |
| *"A fork is a maintenance burden."* | An unchanged fork of a frozen repository has no maintenance. The burden begins only if Zero starts changing it, which is a later decision |
| *"Better to upgrade properly than fork a 2018 commit."* | The upgrade is **M** at best (`Effort` above) and dominated by consensus-equivalence testing. The fork is **S** and is a precondition either way -- upgrading also needs somewhere to put the result |
| *"Four other projects sit on the same pin; it is clearly fine."* | Two of them are dead (TENT last commit 2021-11) and one is older than Zero (Horizen, 2018-08). That is not a healthy cohort to take assurance from |
| *"The effort is better spent on measured wins."* | Agreed, and that is why the upgrade is deferred. The fork is hours, not a program |

### Why the upgrade is deferred, specifically

**`zcash_proofs` has taken 3 commits since 2022**, all release bumps. The
Sapling verification path Zero calls has barely moved; the 6724 commits are
Orchard, transparent-pool, PCZT and wallet work Zero does not use. An upgrade
imports years of change to reach code that is nearly the same.

**The measured opportunity is not in the dependency version.** Groth16
verification is 48-55% of post-Sapling ConnectBlock CPU and is single-threaded
by construction -- `bellman`'s `multicore.rs` serves the prover, not
`groth16/verifier.rs`. Batching or parallelising it is worth more than any
version bump, and both need the FFI boundary changed, which needs the fork
first.

### Sequencing: finish the current work before starting algorithm experiments

**Nothing in this document should begin until the documentation and test work
in progress is closed and a baseline benchmark is cut.** Stated as a
precondition, not a preference:

| Before | Why |
|---|---|
| **Close the `contrib/perf` documentation work** (`docs/TASKS.md` C1, 30 steps open; the gating one is folding `Perf.md`'s status sections) | A dependency change lands findings in a tree whose subjects are still 40-66% outside their owners. The result would be filed wherever it was written |
| **Finish the pending test work** (`docs/TASKS.md` Tests) | An algorithm change is judged by whether the suites still pass. Suites with known-held failures and no recorded baseline cannot make that judgement |
| **Cut a reference benchmark** on the current build -- 5-10 trials preferred, all measurements kept -- recorded, with `cpu_busy` and millisecond timing | Without it, "did this help" is unanswerable. The lab only became able to resolve sub-1% differences on 2026-09-07 (M-LAB-WALL-MS, M-LAB-REPRO), and no multi-trial baseline has been taken since |

**The order is not arbitrary.** A Groth16 or librustzcash experiment produces a
number whose meaning depends entirely on what it is compared against. Today the
comparison would be against runs taken with second-resolution timing, on a
harness that has since changed, filed into documents being restructured. The
measurement would be real and the conclusion unciteable.

The fork-for-custody step (below) is the exception: it is packaging, changes no
code, and its acceptance test is a byte-identical archive. It can proceed in
parallel.

### Strength of the precedent

The commit distances (Ycash 1127, Pirate 2462) overstate what each project
actually did. Isolating fork-specific work: **each fork carries about three
commits of its own** -- network prefixes, activation heights, encoding -- on top
of upstream history pulled forward. The named authors on both forks are the
upstream Zcash team (`ZK/ZKs/rustzcash/ZcashRust.md` S9).

**So the move is not research; it is a bounded change of known shape, performed
twice independently.** Both trees are checked out locally for reference.

### Until it is tried, the performance effect is unknown

**No claim about direction or size of any performance change should be made
before a build exists.** Neither a newer librustzcash nor a deeper uniblake
integration has been built for Zero, so:

- Whether the post-2018 Sapling arithmetic is faster, slower or identical is
  **not measured**. `zcash_proofs` at 3 commits since 2022 argues for
  "identical", but that is an inference from commit counts, not a measurement.
- Whether extending uniblake to the remaining blake2b sites
  (`docs/HASHLIBS.md` S1.5) helps is likewise unmeasured, and the bulk case
  there measured 1.01x -- so the expected value is near zero and could be
  negative.

The lab can now resolve differences it previously could not: wall time is
measured in milliseconds rather than whole seconds (M-LAB-WALL-MS). What is
missing is the build, not the instrument -- though the variance of any
particular workload has to be established per workload, not assumed from one.

### Related: local hosting of downloadable artifacts

The same provenance argument that motivates forking librustzcash applies to
every artifact the build and the lab fetch from a third party:

| Artifact | Size | Source | Risk |
|---|--:|---|---|
| Zcash parameters (`sprout-groth16`, `sapling-{spend,output}`, sprout keys) | **741 MB** | `download.z.cash` | Build and node startup fail if it moves |
| librustzcash tarball | -- | `github.com/zcash/librustzcash/archive/` | Discontinued repository (above) |
| Chain snapshots, `bootstrap.dat`, block archives | GB-scale | ad hoc, local | Not reproducible off this machine |

**Recommendation: host these under project control**, in the same organisation
as the librustzcash fork. Parameters are content-addressed by hash and
verifiable, so a mirror is a mirror -- no trust is added by hosting them, and
availability stops depending on a third party. Lab artifacts (snapshots,
bootstrap) additionally have no canonical source today, which makes any
measurement taken against them unreproducible by anyone else.

This is packaging and hosting work, independent of the fork decision, and can
proceed in parallel.

### What would change this recommendation

- A **security advisory** against the pinned code: upgrade becomes urgent, and
  the fork becomes the vehicle for a backport.
- **Zero adopting Orchard or ZIP-221**: the FFI delta stops being a rename and
  the Ycash-level move becomes necessary rather than optional.
- A **measurement showing the newer proving path is materially faster**: not
  expected, given 3 commits, but it has not been measured and that is an
  honest gap.
