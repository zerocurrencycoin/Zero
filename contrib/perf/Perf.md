# `zerod` sync performance: current understanding, and next steps

**Groth16** now lives in **[PerfGroth.md](PerfGroth.md)**; **task state** in **`docs/TASKS.md`**. This file keeps findings and method.

**New to benchmarking this node?** Read **`docs/HOWTO.md`** first -- this file is the investigation narrative and assumes the workflow is already familiar. Data provenance for every recent number: `test-logs/DATA_INDEX.md`.

**Quantitative inventory** (`M-*` campaigns, vocabulary, comparability, extraction, ledger `CAMPAIGN=` map): **[Measures.md](Measures.md)** -- cite IDs only here; means/stdevs live there. This file keeps optimization narrative, **BENCH-/FIX-/IMP-***, baseline tracks **L0-L7**, Stages 0-6, priorities **G**/**P1-P4**, Groth decision, and **lab materials** (§1). Doc-map, lab discipline, and harness inventory: **`docs/POLICY.md`**.

**Program: recreate the ConnectBlock / import performance baseline** so Groth and other decisions sit on current measured numbers. Already-shipped product work with tests stays in the tree (§3 fd-cache, §4 root latch + anchor index, reindex resume, ExtTests **B1** `reindex_shielded`, founders integer subsidy, FIX-LBI/IMPORT). **Baseline tracks** (§0.13 F **L0-L7**): tiny/short, pre-Sap reindex+bootstrap, post-Sap reindex+bootstrap, era segments, util; then Groth decision inputs. FDCACHE 4x2 postponed. Accounts/W5 pending review.

**ID note:** ExtTests **B1** (`reindex_shielded`) is unrelated to baseline track **L1**. Do not reuse bare B0-B7 for lab tracks.

## 0. Status at a glance

Orientation for the sync/perf lab. Detail lives in subsections and **Measures.md**.

**Where this stands:** Three ConnectBlock-adjacent fixes shipped (§3 fd-cache, §4 root latch, §4 anchor-existence index); two measured **null** throughput wins (useful negatives). Post-Sapling import CPU is still **Groth16-bound** (~48–55% chain-wide, M-CPU-SEQ). Batch verification is the largest open sync win; **Option A vs B is undecided** -- do not start Phase 2 product code until a person chooses. Hand-port Phases 0–1 proved the math on pinned crates (scratchpad only). Fat-wallet witness path is a separate track (§0.14): lab prototypes measured; **Cycle 1** STALE next. Mining: regtest solve smoke + NEON probe done; **G5** mainnet (192,7) timed solve **scheduled** (Track M). See §0.0 / §0.1a (Groth review) and §0.15 (backlog).

### 0.0 Groth16 item -- lead-in and step-by-step

Reviewer entry point for people who have not lived in §§2/6/9.4. Evidence stays in those sections; this is the decision story and ordered steps.

#### Review packet

| Item | Content |
|------|---------|
| **Ask** | Choose **Option A** (hand-port batch math on pinned 2018 crates) or **Option B** (migrate to `sapling-crypto` / `BatchValidator`). |
| **Why it matters** | Post-Sapling ConnectBlock CPU ~**48–55%** Groth16 (M-CPU-SEQ); up to **~60.9%** in one corrected window (M-CPU-CORR). |
| **Today** | Eager per-spend/output `verify_proof` on `zcash-loadblk`; no batch API; scriptcheck workers never see Groth16. |
| **Option A status** | Phases 0–1 **done** (MiMC KATs N=1..64 + corrupt); code **not in repo** (scratchpad). Phase 2+ blocked on decide. |
| **Option B status** | Upstream production since 2022 (zcashd, Zebra); Pirate has C++/`cxx` precedent. Migration cost **unscoped** (§0.6a cxx questions open). |
| **Not substitutes** | fd-cache / latch / anchor index -- shipped, measured flat for throughput. |
| **Independent tracks** | Fat-wallet witness productize (§0.14); Equihash NEON (P1/G7); mining solve profile (G5). |
| **Decide inputs** | §0.1a pros/cons; §0.6a effort bands; §6–6.2 crypto/control-flow; §9.4 phase checklist. |
| **After decide** | Stage 2 evidence closeout -> Stage 3 implement -> measure vs post-Sap baselines; keep sequential fallback until proven. |

**Blocking rule:** no Groth16 product implementation (§9.4 Phase 2 onward) until A/B is chosen by a person.

#### Why it exists

1. **What we measured:** during mainnet `-reindex` / bootstrap import, after Sapling activation (~height 492,850), ConnectBlock CPU is dominated by verifying Sapling Groth16 proofs (spend/output). Corrected profiles: **~48–55%** chain-wide (M-CPU-SEQ); one corrected post-Sapling window hit **~60.9%** (M-CPU-CORR). Disk and Equihash are real but smaller.
2. **What that means for operators:** post-Sapling reindex/import is slow mainly because each shielded description pays a full pairing check on the single `zcash-loadblk` thread -- not because "disk is slow" in the fd-cache sense (fd-cache A/B was a **null** throughput win).
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
| 6 | Prototype hand-port math on pinned crates (MiMC fixtures, N=1..64, corrupt cases) | Done Phases 0–1 -- §9.4; **scratchpad only, not in repo** |
| 7 | **Decide:** Option A hand-port vs Option B adopt `sapling-crypto` | **Blocked -- person decides** (§0.1) |
| 8a | If A: Phase 2 FFI design -> Phase 3 shadow/batch in `main.cpp` -> review | Not started |
| 8b | If B: spike migration cost (FFI/`cxx`, depends, blast radius) then implement | Not started |
| 9 | Measure tip/window blk/s before vs after; keep sequential path as fallback until proven | Not started |
| 10 | Multicore batch / latency tuning | Later, separable |

#### How to explain it in one paragraph

Post-Sapling sync is Groth16-bound (~half of ConnectBlock CPU). Zero verifies every Sapling proof one-at-a-time on the import thread. Batch verification can collapse much of that cost; we proved the math works on Zero's old crates, but upstream already ships a stronger batcher that also covers signatures -- so the next move is choose hand-port vs migrate, not write Phase 2 yet. Disk and FDCACHE work already shipped and measured flat; they are not substitutes for this item.

#### Pointers

- Decision detail / pro-con: §0.1 and §0.1a  
- CPU evidence: §2; measure IDs M-CPU-* in **Measures.md**  
- Crypto and control-flow constraints: §6  
- Hand-port phase checklist: §9.4  
- Independent of this decision: NEON blake2b (§5 / §0.2 item 2), measure campaigns (stock rematch)

### 0.1 Immediate next step

Decide before any more Groth16 product code. **Hand-port vs. adopt upstream — this is the actual next action, not more coding.** §6.1/§6.2 found that `zcash/sapling-crypto`'s `BatchValidator` (production since 2022, used today by both `zcashd` and Zebra, with a real C++ integration precedent in Pirate Chain — a same-lineage fork) does more than the hand-port plan (§9.4) scoped: it batches RedJubjub signatures too, not just Groth16 proofs. Two live options:

1. **Continue the hand-port** (§9.4 as written) — port only the batching math into Zero's pinned 2018-era crate stack. Phases 0–1 are done and passing (see §0.3). Smaller footprint, no crate migration, but reinvents ~4 years of upstream work and misses signature batching.
2. **Adopt `sapling-crypto` directly** — migrate to the current crate stack, call `BatchValidator` as-is, following `zcashd`'s or Pirate Chain's real integration as a template. Bigger migration (crosses the `ff`/`group` trait-split §6 flagged as "a large, separate undertaking"), but battle-tested, includes signature batching, has a real batch-size precedent (`MAX_BATCH_SIZE=64`/`MAX_BATCH_LATENCY=100ms` from Zebra).

**This decision is not made in this document — it needs a person to weigh migration cost against reuse value.** Full detail: §6.1 (what upstream ships), §6.2 (who else has adopted it), §9.4's status note (what's already built and tested for option 1).

### 0.1a PENDING DECISION -- Groth16 batch verification: hand-port vs adopt `sapling-crypto`

**Pending questions (lab-wide, settled owners):**

| Question | Owner / gate | Status |
|----------|--------------|--------|
| Groth16 Option A vs B (§0.1a), **including the cxx-bridge scoping (§0.6a)** | Person | **Open** -- G2 then G3 consecutive after G5/G9. The cxx questions are not a separate decision: whether batching can land behind Zero's existing C ABI (`librustzcash.h`, raw `extern "C"`) or requires a cxx bridge **is** the A-vs-B cost difference |
| ARM fleet mix (NEON worth?) | Deploy survey | **Open**; G7 NEON **postponed** anyway |
| FDCACHE 8/16KB vs default vs 1MB | G6 | **Hold** |
| W5/W6 / getalldata cache / Zerowallet notmodified | Product review | **Postponed** |
| Halo/Orchard for Zero | Not Zero consensus; Zebro D2 | **Postpone G8** |
| KAT adapt tests beyond TST-05 green | G9 | **Postponed** |

**Status: blocking.** No further Groth16 implementation work (§9.4 Phase 2 onward) should start until this is resolved by a person, not inferred from this document. Nothing below picks a winner.

**Decision needed:** for Sapling Groth16 batch verification (the single largest CPU-optimization opportunity found in this investigation, §2), should Zero (a) hand-port the batching math into its existing pinned 2018-era `bellman`/`pairing` crate stack, or (b) migrate to the current `sapling-crypto`/`bellman 0.14` crate stack and adopt its shipped `BatchValidator` directly?

**Option A — Hand-port into the pinned stack** (§9.4 as written)

*Pro:*
- Smallest footprint — no crate-version migration, no change to Zero's existing FFI shape (`librustzcash.h`, raw `extern "C"`), no touch to any dependency other than the one being extended.
- De-risked in real, tested code already: §9.4 Phases 0–1 (pure-Rust prototype) are done and passing — a hand-ported random-linear-combination batch verifier built against the actual pinned `bellman 0.1.0`/`pairing 0.14.2`, validated against real Groth16 proofs from `bellman`'s own MiMC/BLS12-381 test circuit, batch accept/reject exactly matching per-proof `verify_proof` across N=1,2,8,64 and adversarial corrupted-proof cases, repeated 6 times. This isn't theoretical — the core math is proven to work on Zero's actual dependency versions.
- Confirmed buildable: the pinned 2018-era crate pair builds clean under a modern Rust 1.90 toolchain (§9.4 Phase 0 finding) — no toolchain-pinning workaround needed.
- Keeps Zero's build/dependency surface area unchanged, which matters for a project maintained by very few people (§0's own framing — see `MEMORY.md`: user is sole owner/maintainer of the Zero repo family).

*Con:*
- Reinvents ~4 years of upstream engineering (`BatchValidator` shipped in `zcash_proofs` 2022-07-05) rather than reusing it.
- **Misses signature batching entirely** — `sapling-crypto`'s `BatchValidator` batches RedJubjub `spend_auth_sig`/binding signatures alongside Groth16 proofs (§6.1); the hand-port plan only ever scoped proof batching, since Zero's current `check_spend` verifies the signature eagerly, per-call, ahead of the proof check (§9.4 Phase 0 finding). A hand-ported Groth16-only batcher leaves that signature-verification cost fully unaddressed.
- No production track record for *this specific port* — the math is proven against synthetic MiMC test-circuit proofs, not against real Sapling spend/output circuits or adversarial conditions beyond what §9.4's test plan covers. `BatchValidator` by contrast has ~4 years of live-network exposure across `zcashd` and Zebra.
- Batch-size tuning (how many proofs per batch, what latency budget) has no precedent to draw from — Zebra's real, tuned parameters (`MAX_BATCH_SIZE=64`, `MAX_BATCH_LATENCY=100ms`, §6.2) apply to `BatchValidator`'s architecture, not directly transferable to a hand-rolled one.
- Building consensus-critical cryptographic code in-house, however well-tested, carries more independent-review burden (§9.4 Phase 6) than adopting code multiple other implementations already run in production.

**Option B — Adopt `sapling-crypto` directly**

*Pro:*
- Reuses battle-tested code: `BatchValidator` has run in `zcashd` and Zebra (both currently active, `zcashd` until its imminent end-of-life ~2026-07-18) for roughly four years, and is the architecture of the two most-current reference implementations in the ecosystem (§6.2).
- Gets signature batching for free, a real efficiency gain the hand-port plan never scoped.
- Real integration precedent exists for exactly Zero's situation: Pirate Chain, a same-lineage C++ zcashd fork, has already done this exact migration (its own vendored `cxx`-bridge Rust crate wrapping `BatchValidator`, §6.2) — a template closer to Zero's actual codebase than Zebra's from-scratch Rust design.
- Real, tuned batch-size parameters already exist to start from (`MAX_BATCH_SIZE=64`/`MAX_BATCH_LATENCY=100ms`), rather than guessing.
- Positions Zero on a currently-maintained crate lineage instead of a snapshot of a since-heavily-refactored 2018 dependency graph, which may reduce future maintenance friction (e.g. if any future Sapling/consensus fix upstream only lands against the current crate generation).

*Con:*
- Materially larger, effectively unscoped effort: crosses the `ff`/`group` trait-split ecosystem-wide API break (§6) — every type in Zero's `librustzcash`/`bellman`/`pairing`/`jubjub` call path is affected, not just the verifier.
- Unknown whether Zero's current C-header FFI (`librustzcash.h`) can be kept as-is or needs replacing with a `cxx`-bridge like `zcashd`'s current architecture (§0.5 — genuinely unresolved, not just unscoped).
- No prototype exists for this path at all — unlike Option A, zero hands-on validation has been done; the entire cost/risk profile is currently an estimate, not a measurement.
- Real risk of the migration itself introducing regressions unrelated to Groth16 batching, simply by virtue of touching every consumer of the affected crates — a much larger consensus-code blast radius than Option A's narrowly-scoped change.
- Bigger, harder-to-interrupt effort for a single-maintainer project — more exposure if only partially completed.

**Recommendation (offered, not decided): lean toward Option B if the migration cost turns out to be smaller than it currently looks, otherwise Option A.** Concretely: the single highest-leverage next step is **not** more coding on either path, but **scoping Option B's actual migration cost** (§0.2 item 6) — right now it's the con with the least evidence behind it ("large, separate undertaking" is a characterization from §6, not a sized estimate), while Option A's cost and viability are already fully measured (§9.4 Phases 0–1). A short, bounded research spike into what the `ff`/`group` migration and FFI-layer question actually require (see §0.5, §0.6) would turn this from a qualitative pro/con list into a comparison grounded in bridge/depends evidence (§0.6a). Until then, Option A is the lower-uncertainty choice by default only because a working prototype exists -- not because it has been shown better.

### 0.2 Priority-ordered open items

ConnectBlock / sync lab only. Planning for this tree stays here (and in **Measures.md** / **WitnessReindex.md** where noted). Do **not** heavily rework **TODO.md** / **ExtTests.md** / **UpdateZero.md** or other Zero400-owned documents on ZeroPerf -- they are authoritative on the product branch. Prefer keeping ZeroPerf's copies close to Zero400's so the diff stays readable, but exact match is a **preference, not a requirement**: a change that is right for ZeroPerf can land here first. Perf context that would otherwise go in those documents belongs in **`docs/POLICY.md`**.

**Groth16 investigation group (ongoing -- one decision gate, then phased work):** hand-port vs adopt (`§0.1a`); optional migration-cost spike; Phases 2+ only after decide; multicore later. Treat as one program, not mixed with FR/wallet Decide items.

**Parallel effort (independent of Groth):** Equihash / blake2b / NEON -- ARM-mix check first; mining profile optional and separate from reindex-verify CPU.

| # | Item | Deps | Effort | Risk | Note |
|---|------|------|--------|------|------|
| G | Groth16 program | Person decides A/B | L (spike) then XL | Consensus if Phase 3 | See §0.0-0.1a; Stages 2-3 |
| P1 | NEON blake2b (Equihash) | Confirm ARM deployments | M | Low (not consensus) | Parallel to Groth; Stage 4 |
| P2 | Segmented wallet-off rematch + bootstrap segments + shielded-era profile table | Lab materials | M | None | Track **L3** / BENCH-SEG; Stage 1 |
| P3 | Shieldex | Optional dead-field PR; full gate **set aside** (§0.10) | S / M | Med if gating | RSS only |
| P4 | LoadBlockIndex inner interrupt | None | S | Very low | **Done** FIX-LBI |
| -- | `-O1`/`-O2` + FDCACHE 4×2 | Deliberate resume | M wall | None | **Postponed together** -- O1 estimated low impact; retest with 4×2 later |

**Decoupled product Decide (not Groth -- different owners/risk):** FR-ROTATE / FR-TADDR / FR-Z. **Accounts / W5:** postponed, pending further review (§0.12) -- do not block sync lab. Track product Decide on Zero400 **TODO** at merge; do not edit Zero400 from this lab.

### 0.2a Postponed triage

Columns: impact / deps / effort / risk / suggest.

| Item | Impact if done | Deps | Effort | Risk | Suggest |
|------|----------------|------|--------|------|---------|
| Bootstrap matrix leg (n≥1 then n=4) | Closes M-BOOT gap vs reindex | Fixed reset; bootstrap.dat copy | M–L wall | Low | **Done** pre-Sapling (M-BOOT-PRESAP); optional post-Sapling |
| LoadBlockIndex interrupt | Lab/ops stop without SIGKILL | None | S | Very low | **Done** FIX-LBI |
| FDCACHE 4×2 + O1/O2 | Confirms null / compiler | ZERO_FDCACHE build; wall time | L | None | **Hold** (bundle later) |
| OPS-AT-HEIGHT / stopatheight | Ops UX | Product design | M | Med | Hold (Zero400) |
| OPS-REINDEX refuse / `-reindexforce` | Footgun | Loud warn shipped | S | Low | **Postpone** -- warn enough for now (§0.8a) |
| OPS-REINDEX-SKIP wallet below H | Fat-wallet reindex | Resume markers shipped | M | Med wallet | **Postpone** -- not ConnectBlock (§0.8a) |
| CleanIndex ExtTests B2 / witness C | In-process coverage / hardening | ExtTests B1 RPC shipped | M / S | Med / Med | Hold (B1 enough for now) |
| Second post-Sapling malloc window | Allocation narrative | None | M | None | Skip (unlikely to change §7) |
| Multicore Groth batch | Throughput on idle cores | Groth land first | M | Med | After single-thread batch |

### 0.2b Lab facts

Do not confuse with product TODO on Zero400. Numbers: **Measures.md** only.

- Integer founders helper **`GetFoundersRewardAmount` = `subsidy * 75 / 1000`** and integer `GetBlockSubsidy` base are **present in this tree and Zero400** (tests in `main_tests` / founders gtest). Treat checklist "implement subsidy" lines as **status-lag** until Zero400 TODO is updated on merge -- not as missing code here.
- Reindex **resume** (`L`/`H`/`R`, conf loud warn): **shipped**; interrupt/resume lab in AtHeight. Refuse/`-reindexforce` and skip-wallet: **not** shipped.
- **FIX-LBI / FIX-IMPORT-POLL:** `LoadBlockIndexDB` and `ThreadImport` honor `ShutdownRequested()`; mid-file interrupt does not advance `L`.
- Baseline campaigns done: **M-RX-POSTSAP-STOCK**, **M-BOOT-PRESAP**, **M-RX-PRESAP**, **M-BOOT-POSTSAP** (parity note in Measures §8). Util sampling on by default in `postsapling_reindex.sh`. Contended tiny/short: **M-RX-TINY-20260811d** / **M-RX-SHORT-20260811b**.

### 0.3 What's actually been built and tested

- **§3, §4 (root latch), §4 (anchor-existence index):** implemented, in this repo's tracked source, full regression-tested (Boost `test_bitcoin` 284/284; `zero-gtest` 205–207/207 with 2 known pre-existing flakes). These are real, committed changes.
- **§9.4 Phases 0–1 (Groth16 hand-port prototype):** real, working code — but **lives entirely in this session's scratchpad** (`/private/tmp/claude-501/.../scratchpad/groth16-batch/`), **not in this repo, and not durable past session end.** Fetched the pinned `librustzcash` source at the exact commit, hand-ported a random-linear-combination batch verifier against the real pinned `bellman`/`pairing` crates, generated genuine Groth16 proofs via `bellman`'s own MiMC/BLS12-381 test circuit, and confirmed batch accept/reject exactly matches per-proof `verify_proof` for N=1,2,8,64 (all-valid and one-corrupted-among-N), repeated 6 times. **If picked back up, Phase 0 (fetch the pinned source) needs re-running from scratch** — nothing to reload, only results to trust (which are fully written up in §9.4, not just asserted here).

### 0.4 Postponed

- **FDCACHE-era bootstrap 4x2 via `bench_matrix.sh`:** still not re-run; stock bootstrap peers are done (**M-BOOT-PRESAP**, **M-BOOT-POSTSAP**). Reset bug fixed earlier.
- **`LoadBlockIndexDB` interruption:** fixed -- FIX-LBI.
- **A second `MallocStackLogging` window sampled entirely post-Sapling-activation** (§7) — the current one straddles the activation boundary; given Groth16 verification itself allocates nothing and the dominant allocator (`AddToBlockIndex`) has no Sapling-specific component, a second window is unlikely to change the qualitative conclusion, so not pursued further.
- **§9.4's originally-planned per-transaction-attributed fallback design** (Phase 4) — §6.2 found current `zcashd` doesn't do this at all (it rejects the whole block with one generic error on batch failure); whether Zero should match that simpler upstream behavior or keep the more careful per-tx design is an open question folded into §0.1's decision, not resolved separately.
- **Multicore/`rayon`-equivalent parallel batch verification** — both the hand-port (§9.4 Phase 2 item 10) and Zebra's real deployment (§6.2, `sapling-crypto`'s `"multicore"` feature) treat this as separable, later work on top of single-threaded batching, not a prerequisite.

### 0.5 Known gaps / unresolved questions

- **ARM vs. x86_64 real deployment mix for Zero nodes — unknown.** Directly determines whether NEON blake2b (item 2, §0.2) is worth pursuing at all; not checked this session or any prior one.
- **Whether Zero's current C-header FFI (`librustzcash.h`, raw `extern "C"`) could be kept alongside a `sapling-crypto` migration, or would need replacing with a `cxx`-bridge like `zcashd`'s current architecture** — not investigated; directly affects how big option 2 in §0.1 really is.
- **Whether Zero's own `CBlockIndex` "Shieldex" fields (§8.2) are used by anything beyond the one RPC endpoint confirmed** (`rpc/blockchain.cpp`'s shielded-tx-rate stats) — confirmed one real consumer, didn't exhaustively check for others before suggesting the fields could be gated/removed.
- **No `-O1`/`-O2` measurement exists at all** (item 3, §0.2) — the "little difference" claim in this document's history has never been checked against real data, in either direction.
- **§9.4 Phase 4's fallback design vs. current `zcashd`'s simpler whole-block-reject behavior** — genuinely open, not just postponed (see §0.4); affects error-message/ban-scoring granularity, not correctness.

### 0.6 Possible research spikes

- **Whether Pirate Chain's C++ `cxx`-bridge port (`src/rust/src/sapling.rs`, `src/rust/src/bridge.rs`) is directly adaptable to Zero**, given both are same-lineage zcashd forks — could shortcut a large fraction of option 2's (§0.1) scoping work if their crate-version pins and build tooling are close enough to Zero's `depends/` system. Not checked: how their `depends`-equivalent build step differs from Zero's, or how much of their bridge code is Pirate-specific vs. reusable.
- **Whether `zcashd`'s own pre-`cxx`-migration history (its git log, before the current `rust/bridge.h` architecture) shows an intermediate step comparable to Zero's current state** — could reveal a real, tested incremental path from raw-C FFI to batching, rather than jumping straight to `cxx`. Not investigated — the `zcashd` checkout fetched this session was a shallow, single-commit clone with no history to search.
- **Whether `Equihash::IsValidSolution` has existing test fixtures with known edge cases** (§9.2 step 4 flags `src/test/equihash_tests.cpp` as unchecked) — would materially de-risk the NEON differential-testing step; a five-minute check not yet done.


### 0.6a Groth Option B migration-cost spike

Qualitative scope only. Calendar time estimates are **not** refined here -- there is no measured basis for days/weeks claims.

**Question:** how large is adopting `sapling-crypto::BatchValidator` relative to continuing the hand-port on pinned crates?

| Layer | Finding | Effort band |
|-------|---------|-------------|
| Crypto API | `BatchValidator` batches Groth16 and RedJubjub spend-auth/binding sigs; Zebra documents batch-size / latency knobs | Reuse if crates move |
| Crate graph | Modern stack crosses the `ff`/`group` trait split vs Zero's pinned 2018 `bellman`/`pairing`/`jubjub` | L–XL depends + Rust consumers |
| FFI | See **cxx questions** below | M–L if adopting cxx; unknown if C header can be kept |
| Consensus glue | Buffer proofs in `ContextualCheckBlock` (today eager per-tx); batch-fail policy | M |
| Hand-port alternative | `groth16-batch-poc` Phases 0–1 prove math on pinned crates; Phase 2 = FFI + `main` only, no crate migration, no sig batching | M after decide A |

**Decision inputs, not a schedule:** Option B is a release-scale migration if done like current zcashd (depends + bridge + Sapling verify + regression). Option A is narrower (Phase 2–3 on pinned crates) but omits signature batching and keeps in-house crypto review. Next engineering choice after baseline numbers: Pirate/zcashd bridge inventory **or** Option A Phase 2 FFI sketch -- not both in parallel.

**Lab host:** this ZeroPerf machine is arm64 with NEON available; fleet mix remains unknown.

#### cxx questions

**What `cxx` is:** the [cxx](https://cxx.rs/) crate generates a typed bridge between C++ and Rust so each side can call the other with real types, instead of hand-written `extern "C"` plus raw pointers/bytes. Modern `zcashd` uses this pattern for Sapling (`rust::Box<...>`, generated bridge headers). Pirate mirrors that shape in a vendored `src/rust/` crate.

**What Zero has today:** `librustzcash.h` and raw `extern "C"` entry points (e.g. `librustzcash_sapling_check_spend`). No in-tree `cxx` bridge.

**Open questions (unanswered -- these are the spike, not settled facts):**

1. **Must Option B use `cxx`?** Or can upgraded Rust crates still expose a stable C ABI that keeps Zero's existing header shape?
2. **If `cxx` is required,** what is the blast radius in Zero's `depends/` / cargo-offline / reproducible-build path compared to Pirate or current zcashd?
3. **How much of Pirate's or zcashd's bridge** is reusable vs fork-specific?
4. **Can batching land behind the current C FFI** as an incremental Option A/B hybrid, or is crate migration inseparable from the bridge rewrite?

Until those are answered with file/crate evidence, do not treat "need cxx" as decided -- treat it as the main unknown that sizes Option B.

### 0.7 Section index

Pointer list only; each section states its own finding.

§0.0 Groth16 review packet / steps · §0.1 decision · §0.2 sync-lab priorities · §0.2a postponed triage · §0.2b lab facts · §0.6a Option B / cxx · §0.8 signals · §0.8a reindex remainder · §0.9 mining+density · §0.10 Shieldex · §0.11 huge-wallet · §0.12 accounts/W5/TST · §0.13 plans (BENCH/FIX/IMP, L0-L7, Stages) · §0.13 G stages · §0.14 wallet witness · §0.15 open work menu · §0.16 reorg / productize / lab wallets · §1 methodology · §2 CPU buckets · §3 fd-cache · §4 latch/anchor · §5 Equihash · §6 Groth16 · §7 memory · §8 allocations · §9 paths / §9.4 Phases 0–1.

---

### 0.8 Signals, `fRequestShutdown`, and debug.log rotate

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
| T1 | Equihash verify in header checks (reindex) | Smaller but steady | Optional every N headers |
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

POSIX `sigaction(SIGTERM/SIGINT/SIGHUP/SIGPIPE)` is under `#ifndef WIN32` in `init.cpp`. This tree has **no** `SetConsoleCtrlHandler` wiring for Ctrl+C → `StartShutdown()`.

| Event | Expected / observed | Validation |
|-------|---------------------|------------|
| RPC `stop` | `StartShutdown()` → interrupt → `Shutdown()` | `zero-cli stop`; clean exit; datadir lock released |
| Console Ctrl+C | **Observed:** does **not** exit immediately. Delay is consistent with orderly teardown / **updating stores** (`Shutdown()`: wallet `Flush`, `FlushStateToDisk`, LevelDB/BDB close, zeronode dumps) rather than an instant kill | Confirm `Shutdown: In progress...` (or equivalent) in `debug.log` before process exit; note wall time vs tip/wallet size |
| Console close / kill | May still be abrupt depending on host/console | Document if different from Ctrl+C |
| SIGHUP / logrotate reopen | **N/A** (POSIX-only) | No parity claim |
| Service stop (if hosted) | Wrapper-dependent | Note only |

**Code vs observation:** in-tree `zerod` does not register a Win32 console handler; if Ctrl+C still triggers a multi-second exit with store flushes, record **which binary** (`zerod` / Qt / wrapper) and console host produced that path on the validation machine. Do not assume POSIX SIGINT semantics on Windows.

**Plan:** Windows smoke: (1) RPC stop clean; (2) Ctrl+C -- expect delayed exit + store flush evidence in log; (3) no SIGHUP logrotate claim.

### 0.8a Not-done reindex items

Assessment and recommendation.

| Item | Status | Impact | Deps | Effort | Risk | Recommendation |
|------|--------|--------|------|--------|------|----------------|
| Resume `L`/`H`/`R` + telemetry | **Shipped** | High ops | -- | -- | -- | Keep; already labbed (AtHeight) |
| Conf `reindex=` **loud warn** | **Shipped** | Medium | -- | -- | -- | Keep |
| Conf / mismatch **refuse** + `-reindexforce` | Not done | Medium footgun | Product UX copy | S | Low | **Postpone** -- warn already reduces footgun; refuse is nice-to-have after merge, not on perf critical path |
| **SKIP-wallet** below H | Not done | High for fat-wallet reindex | Resume markers | M | Med (wallet/tip consistency) | **Postpone** -- valuable for DevFee-scale wallet reindex, but separate from ConnectBlock lab; needs careful wallet-scan semantics |
| Skip-chain connect below H | Out of scope | -- | Snapshot story | L | High | **Do not pursue** until assumeutxo-class design |
| LoadBlockIndex interrupt | **Done** (FIX-LBI) | High for stuck lab/bootstrap-reset | None | S | Very low | Shipped -- poll every 1000 |
| Bootstrap segment benches | Pre-Sapling n=4 done | High measure | bootstrap.dat | M–L wall | Low | Optional post-Sapling bootstrap window / density CSV |

**Justify:** shipped resume+warn already make reindex operable and interruptible at file boundaries. Remaining refuse/skip-wallet are product/ops polish and fat-wallet specific -- they do not improve Groth16 or stock `-disablewallet` blk/s. Lab priority is interruptibility + segmented bootstrap/reindex measures.

### 0.9 Measure-task add-ons

Mining profile and shielded density table.

**`zcash-loadblk`:** pthread name of `ThreadImport` (`init.cpp`) -- the single worker that runs `-reindex` / `bootstrap.dat` / `-loadblock`. Instruments Time Profiler filters to this thread for ConnectBlock CPU. Not the miner (`zcash-miner`) and not scriptcheck (`zcash-scriptch`).

**Mining profile status**

| Work | Status | Measure / tool |
|------|--------|----------------|
| Regtest `generate` (48,5) env + util | **Done** | M-MINE-REGTEST-SMOKE (~125 ms/blk wall, solve too cheap for Instruments-grade) |
| arm64 NEON / blake2b symbol probe | **Done** | M-MINE-NEON-PROBE (`compress_ref` only; no NEON zerod) |
| Validator KATs (192,7)/(48,5) | **Done** | TST-05; `contrib/perf/kats/` |
| Reindex **verify** Equihash cost | **Done** | M-CPU-SEQ ~**0.252 ms/blk** (not mining) |
| Mainnet-template **timed solve** (192,7) + Instruments on `zcash-miner` | **Scheduled -- Track M** | G5; `mine_bench.sh mainnet-template` only stubs env unless `MINE_MAINNET_SOLVE=1` |
| Live mainnet mining / pool / GBT production hash | **Out of lab scope** | Not a ZeroPerf campaign |
| NEON solve A/B | **Parked** | G7; needs NEON-enabled zerod + ARM fleet mix |

**Procedure for G5 (Track M):** one trial when the Instruments host is free; parallel with Cycle 1, not gated on STALE. `ENABLE_MINING`; disposable isolated mainnet template (never default Application Support); Instruments on **`zcash-miner`** during solve -- not during `-reindex`; record solve ms/block + blake2b share; compare to verify-only ~0.25 ms/blk; campaign `mine-equihash-*`. Do not batch multiple long solves.

**Single shielded density table (drive lookups once):**

**When:** **now / before or in parallel with Stage 1 onset rematch** -- offline scan of `blocks/` or `bootstrap.dat`, wallet off, **no** long `zerod` trial and **not** gated on rematch completion. Prefer finishing density **before** citing onset rematch numbers so those rows can reference `era` ids. Rematch may proceed with a provisional era label if CSV is still building; backfill the cite when the file lands.

**What:** CSV keyed by height or era id with columns `era`, `h0`, `h1`, `sapling_spends`, `sapling_outputs`, `sprout_js`, `fully_shielded_tx`, `blocks`, `shielded_tx_per_block`. Eras at least: pre-Sapling (match M-*-PRESAP windows), Sapling-onset (e.g. 490k-520k), deep post-Sapling (match 600k-900k). Store under `reindex-profile/shielded-density.csv` (gitignored). Assign an `M-*` row in Measures when first produced -- until then this stays a Perf §0.9 / BENCH-SEG input, not a placeholder measure ID.

**Chunked scan / progress (required):** do not wait for a full tip pass before assessing. Use two layers:

1. **Progress cursor (monitor):** append-only checkpoint file (e.g. `reindex-profile/shielded-density.progress.jsonl`) every **400k heights** completed (or wall ~N minutes if preferred). Fields: `h_done`, `blocks_scanned`, running totals for spends/outputs/js, `ts`. Tip ~2.5M => **~7** coarse ticks (400k = half of an **800k** lab band). Resume = continue from last `h_done + 1`.

2. **Density rows (assess):** write/append CSV rows as each **closed** height band finishes -- partial chain is still usable.
   - **Fine first (Stage 1 value):** rematch windows -- e.g. 50k-75k, 490k-520k, 600k-900k -- scan these before or as dedicated passes so onset rematch is not blocked on a tip-wide job.
   - **Coarse chain bands:** **400k** height bands for whole-chain shape (~7 to tip), but **split at Sapling activation 492850** so no row mixes pre- and post-Sapling (e.g. `0-399999`, `400000-492849`, `492850-799999`, `800000-1199999`, ...). Do **not** use a naive band that straddles activation.

**Partial-run rule:** any completed fine or coarse band with a CSV row is citable; incomplete bands stay out of Measures until closed. Progress file alone is ops monitoring, not a measure row.

**Scanner:** `contrib/perf/shielded_density.py` (RPC `getblock <hash> false` + mininode). Zero's `getblock` verbosity 2 omits shield arrays -- do not count from that JSON.

Attempt outcome; finish or set aside.

**Finding (unchanged):** 22×`int64_t` always in RAM (~176 B/block); disk populate/serialize gated on `-zindex`; real RPC consumer in `rpc/blockchain.cpp`; **`nNotarizations` dead** (increment commented out).

**Finish plan (if pursued)**

1. Grep-complete consumer list (done for RPC; re-confirm wallet/metrics).
2. Small PR: remove or `#if 0` dead notarization fields + RPC keys + tests -- **low risk** if `-zindex` RPC accepts absent keys / always-zero removal.
3. Medium PR: move remaining Shieldex counters behind a heap sidecar or `unique_ptr` allocated only when `fZindex` -- **med risk** (every `CBlockIndex` site, upgrade/compat).
4. Measure RSS tip with/without sidecar on short snap.

**Set aside (recommended now):** do **not** block Groth/measure track on (3). Optional tiny PR for (2) only when editing `chain.h` anyway. Full gating is a memory project with index-layout risk; payoff ~435 MB tip RSS, zero ConnectBlock ms. **Status: set aside with explanation; tiny dead-field cleanup optional.**

### 0.11 Huge-wallet utilization

Execution plan is ready to run.

**Scope:** tip-quiet wallet RPC CPU/latency; **not** `zcash-loadblk` blk/s. Profiles **0 / 2 / 3** = named wallet snapshots (empty / extracting / current fat). Separately, getalldata **day code 2** = **7 days** of History (`rpczerowallet.cpp`: 1→1d, 2→7d, 3→30d, …; omitted arg2 still ~30y).

**"Not in tree"** means: no implementation commit in Zero400/ZeroPerf product sources for that item -- design/finding only, or code lives in **Zerowallet** / private DevFee ops / a stash branch. Status snapshot (do not edit Zero400 TODO from here):

| Item | ZeroPerf | Zero400 (read-only note) | Notes |
|------|----------|--------------------------|-------|
| Integer subsidy helper | **In tree + tested** | **In tree + tested** | Checklist may still say implement -- lag only |
| W5 tip-poll split | Not in tree | Not in tree | **Postponed / pending review** (§0.12) |
| W6 tip cache | Not in tree | Not in tree | Blocked on W5 review |
| ADDRKEY typed balance keys | Not in tree | Finding only; **Zerowallet scope** | |
| S4–S8, W2/W3, S7 const, wtxOrdered | In tree | In tree | |
| Soft -34 client path | Client | Documented | |

**Execute**

1. Copy wallets 0/2/3 into disposable datadirs; `-connect=0`; never write production paths.
2. Matrix: `getalldata` datatype 0 vs 1; day **2** (7d) vs 0/omit; nCount 50 vs 200; watchonly on/off if used.
3. Time wall_ms; sample `ps`/Instruments on RPC/wallet thread; note UTXO count / txcount / RSS.
4. Optional: 1000 unused T-addrs control wallet -- expect small delta vs UTXO-fat profile 3.
5. Record under Measures M-GAD-* / campaign `wallet-util-*`; no host paths in public docs.

### 0.12 Accounts, W5, TST

Revisited recommendations.

**Accounts (`WAL-RPC-ACCOUNTS`) and W5 -- postponed, pending further review.**

Both stay **out of the active sync-lab queue**. No implement / apply recommendation until a separate product review revisits them.

| Item | Status | Why parked |
|------|--------|------------|
| **WAL-RPC-ACCOUNTS** | **Postponed / pending review** | Not needed for ConnectBlock or measured tip throughput; const walks + incremental `wtxOrdered` already ship with accounts kept. Dropping account RPCs/BDB `acentry` is a product/compat decision, not a perf gate. |
| **W5** tip-poll History vs Balance split | **Postponed / pending review** | Consensus-free wallet/client policy; may still matter for fat tip polls, but needs soak evidence + Zerowallet UX review before apply-vs-hold. Do **not** treat as "recommend apply." |
| **W6** tip cache | Blocked on W5 review | -- |
| **ADDRKEY** | Zerowallet scope | Orthogonal; not a node ConnectBlock task |

**TST -- implement vs postpone (justified)**

| Item | Rec | Why |
|------|-----|-----|
| **TST-09** `-blocknotify` / `-walletnotify` | **Done** | `DeprecationTest.BlockNotify*` / `WalletNotify*`; alert half already done |
| **TST-05** Equihash (192,7)/(48,5) KATs | **Done** (validator + solver cases; `1927EQ.txt` + `1927EQ_h1.hex`) | `equihash_tests` green; pairs BENCH-MINE |
| **TST-01** `getsupply` / `zs_*` depth | **Implement opportunistically** | Exclusive depth; not gate-blocking; pairs getalldata work |
| **TST-03** zeronode arg validation | **Scheduled -- Track Z Phase A** | Expand existing Boost; no sync-lab coupling. Phase C 2-node after A/B (**ZeroNodeDev.md** §9, **UpdateZero** TNT-12) |
| **CleanIndex ExtTests B2** / witness C | **Postpone** | ExtTests B1 `reindex_shielded` covers reindex witness; B2 high harness cost |
| **finalsaplingroot** / other Bfail | **Postpone** | Not on measure critical path |

### 0.13 Plans and specifications

Benchmarking, immediate fixes, and improvements.

Doc ownership: **BENCH-/FIX-/IMP-***, **L0-L7**, Stages, **G**/**P1-P4**, lab materials (§1) here. **`M-*`** numbers + ledger `CAMPAIGN=` map: **Measures.md** §8 (one-line ID cites below). Do **not** edit Zero400 TODO/ExtTests from this track. Scripts: `contrib/perf/`.

#### A. Benchmarking

| Spec ID | Campaign / measure | Goal | Method | Pass / deliverable | Deps | Status |
|---------|-------------------|------|--------|-------------------|------|--------|
| **BENCH-STOCK** | M-RX-POSTSAP-STOCK | Stock ConnectBlock baseline | `postsapling_reindex.sh` n=4, window 600k-900k, `-disablewallet`, ledger | Mean/stdev in Measures | Full/short source datadir | **Done** |
| **BENCH-BOOT** | M-BOOT-PRESAP / M-BOOT-POSTSAP | Bootstrap import vs reindex | `MODE=bootstrap`; reset excludes `blocks/`; n>=1 then n=4 | Comparable height_per_s; no -28 stuck | Original `bootstrap.dat` copy-only | **Done** (pre-Sap + post-Sap; post-Sap parity in Measures) |
| **BENCH-SEG** | M-DENS-* / M-BOOT-ONSET / M-RX-ONSET | Era-bounded throughput + density | Density tip-complete; onset bootstrap+reindex n=1 peers done | Per-era rows in Measures §3.2a / §8 | Density CSV (§0.9) | **Parked** vs witness (L3 n=4 optional on track switch) |
| **BENCH-UTIL** | M-RX-UTIL-SMOKE | RSS/CPU during import | `SAMPLE_UTIL=1` on short window | util.tsv milestones | Stock binary | Smoke done; keep on postsap runs |
| **BENCH-MINE** | M-MINE-REGTEST-SMOKE / M-MINE-NEON-PROBE | Solve cost ≠ verify | regtest+probe done; mainnet Instruments opt-in; **NEON A/B parked** (grouped hold) | ms/block + blake2b share | NEON build (parked) | **Active** (solve profile); NEON hold |
| **BENCH-WAL** | M-WAL-SYNC-* / M-CPU-WAL-* / M-WAL-WITNESS-* / M-GAD-FAT-TINY | Tip RPC + wallet-on sync util | fat ~50x catalogued; ibd-defer ~35x; NOTEIDX ~33x; getalldata fat@tiny done; full-mainnet Idx1 + §0.11 matrix open | wall_ms + CPU + wallet_bytes | Disposable copies | Witness flags lab-opt-in; matrix later |
| **BENCH-FDCACHE** | 4×2 + O1/O2 | Confirm null / compiler | Bundled later; not current mix | A/B ledger | ZERO_FDCACHE build | **Postponed** |
| **BENCH-WIN-SIG** | Windows stop / Ctrl+C | Document teardown | RPC stop + Ctrl+C; inspect `debug.log` for `Shutdown` / flush | Written expected-behavior note | Win host/VM | **Plan** |
| **BENCH-LOGROT** | Linux debug.log HUP | Validate `create`+HUP | mv/touch/HUP or logrotate `create`; `-debug=rpc` | New file grows; rotated frozen | Linux host | **Plan** (macOS done) |

**Harness rules (all BENCH-*):** never write default Application Support / `%APPDATA%\zero`; refuse that path; cite Measures vocabulary; append ledger via `accumulate_bench.py`. Do **not** batch trials expected to exceed **~20 minutes each** unless each trial can be restarted alone (separate command / resume from trial index). Long windows (e.g. post-Sap 600k-900k) run as one trial per invocation, or with explicit `TRIAL=` / resume support.

**Extractor extensions (non-blocking):** rotation-aware multi-file `debugN.log`; optional `-debug=bench` / xctrace into the same Measures vocabulary; witness/init duration fields so tip-hour contradictions can be cross-checked in structured form. Do not block these on Groth16 product work.

#### B. Immediate fixes

| Fix ID | Change | Why now | Spec | Risk |
|--------|--------|---------|------|------|
| **FIX-LBI** | Inner `ShutdownRequested()` + `interruption_point()` in `LoadBlockIndexDB` long loops | Lab/ops stuck without SIGKILL; high-CPU site | **Done:** poll every 1000 in collect / accounting / fill-link loops; return false | Very low |
| **FIX-IMPORT-POLL** | `ThreadImport` honors shutdown at file boundaries | Ctrl+C / stop during reindex/bootstrap | **Done:** poll before each blk file and after `LoadExternalBlockFile`; do not advance `L` mid-file; skip further bootstrap/loadblock if shutting down | Low |
| **FIX-LOG-DOC** | Ops note: logrotate needs `create`/`touch` before HUP | Prevents silent write-to-renamed-inode | **Done:** `doc/files.md` + Perf §0.8; Linux validate still BENCH-LOGROT | None |
| **FIX-TST09** | Tests for `-blocknotify` / `-walletnotify` | Alert strip confidence | **Done** -- `DeprecationTest` block+wallet skip markers | Low |
| **FIX-WAL-WITNESS-IBD** | Skip/throttle `BuildWitnessCache` during IBD; rebuild at tip | Fat-wallet reindex ~50x (M-CPU-WAL-FAT) | **Prototype done** -- `-walletwitness=ibd-defer` (~35x to h15k); Boost coverage green; productize open -- §0.14 | Med (spend UX during sync) |
| **FIX-WAL-WITNESS-NOTEIDX** | Iterate note-bearing txs only | Same; avoid `empty()` on ~801k maps | **Prototype done** -- `-walletwitnessnote=1` (~33x h8k); walk done; stale narrowing **specified** -- §0.14 | Low–med |
| **FIX-WAL-WITNESS-NOTEIDX-STALE** | Invalidate NOTEIDX only on note-membership change | Founders-dense `-rescan`/IBD Ensure storm (M-WAL-RESCAN-FAT) | **Specified** -- Cycle 1; §0.14 | Med (missed note insert) |
| **FIX-WAL-WITNESS-DIRTY** | Dirty set for notes needing initial witness | Differential; skip validated | **Proposed** -- §0.14 | Med (reorg/load) |
| **FIX-WIT-WALK-UNLOCK** | Drop `cs_main` during full height walk; abort/restart if tip moves | R5c: mid-`-33` reorg is unreachable while the walk holds `cs_main` | **Not recommended** -- analysed 2026-08-19; abort-and-restart cannot converge once walk time exceeds the 120 s block spacing (full stock walk ~3.7 h => E[attempts] ~10^48). Faster walks (NOTEIDX, 35x) make it unnecessary; slower ones make it impossible. Arithmetic and test plan: ZeroPerf `TODO.md` | Moot -- not scheduled |

Out of immediate queue: refuse/`-reindexforce`, skip-wallet below H, Shieldex gating, Accounts, W5, Groth Phase 2 (decision-blocked). FDCACHE buffer A/B (G6) held until wallet-witness triage decides order.

#### C. Improvements

| Imp ID | Improvement | Track | Gate |
|--------|-------------|-------|------|
| **IMP-BOOT-SEG** | Segmented bootstrap + reindex rematch + density CSV | Measure (§A) | Lab wall time |
| **IMP-NEON** | NEON blake2b if ARM mix warrants | Equihash | ARM deployment check |
| **IMP-GROTH-SPIKE** | Bound Option B migration cost (FFI/`cxx`, `ff`/`group`) | Groth | Person still decides A/B before Phase 2 |
| **IMP-SHIELDEX-DEAD** | Optional remove dead `nNotarizations` when touching `chain.h` | RSS/cleanup | Opportunistic; full gate set aside |
| **IMP-BUILD-RECONFIG** | Harden the autotools re-configure path: the automake-spawned `configure` re-run inherits no `CONFIG_SITE`, so it dies on a misleading "libdb_cxx headers missing" on a tree that built minutes earlier. Pre-existing in **both** trees (reproduces in Zero400 with no local edit). Options and recovery: **[BUILD_RECONFIG.md](BUILD_RECONFIG.md)**. Smallest real fixes (persist `CONFIG_SITE`, or make the BDB probe name it) touch `configure.ac`, which is Zero400-owned -- not a perf-local change | Build / ops | A re-run triggered by touching `configure.ac` completes, or fails with a message naming `CONFIG_SITE` |
| **IMP-DB-REWRITE-SPIN** | `CDB::Rewrite` (`src/wallet/db.cpp:389`) spins `while (mapFileUseCount[strFile] != 0) { MilliSleep(100); }`. If a caller still holds the file open the count never drops and the loop runs forever with **no log line, no timeout and no error** -- indistinguishable from a slow node. Introduced/diagnosed Feb 2026 (`f6497b208`); **never fixed, only worked around**: two gtests and one Boost test are excluded for it (`WriteCryptedSaplingZkey*`, `rpc_wallet_encrypted_wallet_sapzkeys`), so the deadlock path has **no test coverage at all**. Original notes recorded scope-block and separate-file attempts, both of which still hung; the leftover diagnostic is the commented-out refcount `LogPrintf` at `db.cpp:394`, driven by hand under gdb/lldb. **Do:** bound the loop (iteration or wall-clock cap), log the holder past a threshold, decide fail-loud vs spin; then re-check whether the three excluded tests can be restored. Cross-project comparison (Zclassic byte-identical, Zcash/Pirate idiom-only deltas, Bitcoin removed the path): **`~/Work/ZK/ZKs/CDBRewrite.md`**. | Wallet / ops | Reproduce under an excluded test; a bounded loop must surface the holding refcount instead of hanging |
| **IMP-WITNESS-B2** | CleanIndex gtest harness | WitnessReindex | **Do not run for confidence** -- always-fail; B1 `reindex_shielded.py` covers the product gap |
| **IMP-WAL-MATRIX** | Execute §0.11 getalldata matrix | Wallet util | Disposable wallets; Accounts/W5 still pending review |

#### D. Explicit non-goals

- Edit Zero400 TODO / ExtTests / UpdateZero from ZeroPerf lab
- FDCACHE 4×2 until deliberately resumed
- WAL-RPC-ACCOUNTS or W5 implementation
- Groth16 Phase 2+ without §0.1a decision

#### E. Recent results

Pointers only -- numbers in **Measures.md**.

| Item | Pointer |
|------|---------|
| FIX-LBI / FIX-IMPORT-POLL / FIX-TST09 | Shipped (this tree) |
| Pre-Sap peer | M-BOOT-PRESAP, M-RX-PRESAP |
| Post-Sap peer | M-BOOT-POSTSAP, M-RX-POSTSAP-STOCK (parity) |
| Contended snaps | M-RX-TINY-20260811d, M-RX-SHORT-20260811b |
| Density | M-DENS-* fine + coarse tip-complete (`shielded-density.csv`) |
| Onset rematch | M-BOOT-ONSET (~130) / M-RX-ONSET (~140) n=1 peers |
| Wallet sync | M-WAL-SYNC-P0 / M-WAL-SYNC-FAT / M-CPU-WAL-FAT / M-CPU-WAL0-TINY; archive `test-logs/archives/walletsync-fat-g0-20260812.tar.gz`; FINDINGS + §0.14 |
| Equihash KATs | `contrib/perf/kats/` + TST-05 green; G9 adapt postponed |
| Accepted queue | Perf §0.13 G -- G0 catalogued; witness FIX triage next; G6 held; G7/G8 postpone |
| Ledger map | Measures §8 `CAMPAIGN=` |

#### F. Baseline recreation program

Active program -- not optional leftovers.

Goal: one coherent **current** baseline set for decisions (Groth A/B, NEON, further ConnectBlock work). Prior session under-scoped this as interruptibility + one bootstrap window; that was wrong relative to the program.

| Track | Items | Why | Status |
|-------|-------|-----|--------|
| **Already shipped + tested** | §3 FDCACHE path, §4 latch + anchor Exists, resume L/H/R, ExtTests **B1** `reindex_shielded`, founders integer subsidy, FIX-LBI/IMPORT, `groth16-batch-poc` Phases 0-1 | Product/lab foundation; do not re-litigate | In tree |
| **L0 clean snaps** | Solo tiny + short after FIX-LBI | Uncontaminated tip rates | Done; **contended** -- see M-RX-TINY-20260811d / M-RX-SHORT-20260811b; optional clean re-run |
| **L1 pre-Sap peer** | Reindex n=4 window 50k-75k | Peer to M-BOOT-PRESAP | **Done** -- M-RX-PRESAP |
| **L2 post-Sap bootstrap** | Bootstrap n=4 window 600k-900k | Peer to M-RX-POSTSAP-STOCK | **Done** -- M-BOOT-POSTSAP |
| **L3 era segments** | Sapling-onset rematch + density table | Era-bounded narrative | **Near-done** -- density tip-complete; M-BOOT-ONSET / M-RX-ONSET n=1 peers; optional n=4 if noise warrants |
| **L4 util** | util.tsv on L1/L2-class trials | RSS/CPU at milestones | On by default; smoke M-RX-UTIL-SMOKE |
| **L5 TST-09** | `-blocknotify` / `-walletnotify` default-build markers | Approved PIR-01 companion; alert half done | **Done** (FIX-TST09) |
| **L6 Groth inputs** | Option B migration-cost spike; keep `groth16-batch-poc` runnable | Unblocks §0.1a without Phase 2 code | Spike prose in §0.6a; poc verify still open |
| **L7 ARM note** | This lab host is **arm64** (NEON=1) | Deployment mix still unknown; NEON worth labbing here | Fact |
| Hold | FDCACHE 4x2, Accounts/W5, CleanIndex ExtTests B2, Groth Phase 2 | Explicit non-goals until gates clear | -- |

**Naming:** **L0-L7** = baseline recreation tracks. ExtTests **B1** / CleanIndex **B2** = harness IDs (WitnessReindex / ExtTests) -- different namespace.

Acceptance: Measures.md rows for L0-L3 campaigns with ledger REPORT lines; TST-09 green on default `zero-gtest`; §0.1a inputs include the cxx questions in §0.6a answered with evidence or explicitly still open.

#### G. Next stages

Ordered stages for improvements, experiments, and doc/code updates. No calendar estimates. Gates are explicit.

**Stage 0 -- Finish baseline in flight**

- **Done.** Tracks L0/L1/L2 complete; Measures rows + §0.13 E pointers updated.
- Pre-Sap / post-Sap peer parity: see Measures §8 cross-campaign notes.
- Next: Stage 1 era segments; long trials only one-at-a-time or with per-trial resume.

**Stage 1 -- Close the baseline matrix**

Status: density tip-complete; onset bootstrap + reindex peers n=1 **done**.

- Density: `shielded-density.csv` / **M-DENS-*** (fine + coarse to tip); `DENSITY_SCAN_DONE`.
- Onset: **M-BOOT-ONSET** 129.87 vs **M-RX-ONSET** 140.19 blk/s (n=1 each, 490k-520k) -- ~parity; both ~2x slower than deep post-Sap ~300 (dual Sprout+Sapling).
- Optional: raise onset to n=4 only if noise warrants; clean solo tiny if L0 stays contention-marked.
- Gate to Stage 2: met (density + onset throughput + peer).

#### Accepted lab queue

Owner-accepted order (solo host; one long trial at a time):

| Step | ID | Work | Status |
|------|-----|------|--------|
| 1 | **G0** | Fat-wallet tiny sync + CPU catalog vs P0 | **Done** -- ~19 blk/s, ~50x; `VerifyAndSetInitialWitness` ~97%; archive + FINDINGS + §0.14 |
| 2 | **G1** | Measurement hygiene: leaf+height SOP; needle notes | **Done** |
| 3 | **G0b** | Lab hygiene: util sampler timeout; split witness vs AddToWallet buckets | **Done** -- `WALLETINFO_TIMEOUT_S`; `witness_cache` bucket (re-bucket ~97% / add_ordered ~0.03%) |
| 4 | **G0c** | Note-density on golden fat wallet | **Done** -- note_tx **1403 / 801619 (0.175%)**, all Sapling |
| 5 | **G0d** | Prototype **FIX-WAL-WITNESS-IBD** A/B | **Done** -- stock **16.75** vs defer **595** blk/s to h~15k (~**35x**); `-walletwitness=ibd-defer` |
| 6 | **G0e** | Tip-quiet getalldata on fat tiny tip | **Done** (scoped) -- ~0.75–1.2 s after rebuild; **not** mainnet Idx1 513k-UTXO; full Idx1 still open |
| -- | **NOTEIDX** | FIX-WAL-WITNESS-NOTEIDX prototype | **Advanced** -- `-walletwitnessnote=1` ~**33x** to h8k (14.9→486 blk/s); DIRTY still postponed |
| -- | **G6** | FDCACHE 8/16 KB A/B | **Hold** -- stock binary has no `-perffdcache`; prior 1MB A/B **null** (M-CPU-FD-THR); low priority vs witness ship |
| 7 | **G5** | Equihash solve Instruments (mainnet template) | **Scheduled -- Track M**; parallel with Cycle 1 |
| 8 | **G9** | KAT adapt/extra validate postponed | Note only |
| -- | **G7** / **G8** | NEON / Halo-Orchard | **Postpone** |
| 9 | **G2** then **G3** | Groth decision then implement | Consecutive after G5/G9 slot |

**Next after this batch:** Opt-in packaging done; Id 1 (M-WAL-SYNC-P1) done; disposable tip **2518018** + post-Sap WIT A/B **done**. P2P follow-tip / full bootstrap later. **FIX-WIT-WALK-UNLOCK** and Idx1 optional. Density/L3 parked. **Cycle 1** STALE next. **G5** Track M parallel. Groth G2/G3 after G5/G9.

**G8 lookup note (postpone body):** Zebro treats Orchard/Halo2 as a gated decision (D2): launch assumption Orchard-only / no Sprout-Sapling residue; blocked on **NU6.2 Halo2 incident review** (emergency Orchard disable, dual verifying keys, proof-length rule -- see Zebro `ROADMAP.md` M4, `ZEBRO.md` D2). No Orchard numbers until that opens. Pirate NU5+ integration attempts: review when G8 resumes; not a ZeroPerf implement track. Zero consensus remains Sprout+Sapling Groth16 only.

**G1 -- leaf table + height SOP**

1. Capture Time Profiler during a height-bounded import (or tip RPC).
2. Record `height_before` / `height_after` (and era: pre-Sap / onset / post-Sap).
3. Export XML; run `bucket_profile.py` with `zcash-loadblk` and optionally `ALL`.
4. Report **buckets** (near 100% of filtered weight) and **top leaves** (top-N only -- do not expect 100%).
5. Do not name `Fr::mul_assign` as Sapling Groth16 unless the stack also hits `verify_proof` / `miller_loop` / `librustzcash_sapling_check_*` (jubjub/pairing frames are shared with tree and Sprout paths). Prefer post-Sap windows for Groth narrative; pre-Sap for Sprout/tree/Equihash/disk.

**Stage 2 -- Groth decision inputs only**

- Answer §0.6a **cxx questions** with file/crate evidence from Pirate and/or zcashd, or mark each still open.
- Confirm `groth16-batch-poc` still runs against pinned checkout.
- **Person decides** §0.1a Option A vs B. No Phase 2 product code before that.
- Queue: run **immediately after** G5/G9 slot (accepted queue steps 6--7), not interleaved with G6/G5.

**Stage 3 -- Path-dependent Groth implementation**

- If A: Phase 2 FFI design on pinned crates -> Phase 3 shadow/batch in `main.cpp` -> measure vs Stage 1 post-Sap baseline.
- If B: depends + bridge work package first; then BatchValidator wiring; measure same windows.
- Keep sequential verify as fallback until proven.
- Multicore batch is a later stage on top of single-thread batch.
- Queue: **consecutive with G2** (same program run series).

**Stage 4 -- Equihash solve profile (NEON postponed)**

- BENCH-MINE tools: `contrib/perf/mine_bench.sh` (regtest / mainnet-template / neon-probe).
- Regtest smoke + NEON probe measured (M-MINE-*); TST-05 **done** (kats in `contrib/perf/kats/`).
- Mainnet (192,7) timed solve: Instruments / opt-in -- **G5** in accepted queue.
- **G7 NEON postponed** (grouped hold above). Stock arm64 remains `compress_ref`-only.
- Verify baseline still ~0.252 ms/blk Equihash (M-CPU-SEQ).

**Stage 5 -- Ops and platform validation**

- Linux debug.log `create`+HUP.
- Windows RPC stop + Ctrl+C store-flush note on a real host.
- Optional: refuse/`-reindexforce` only after merge planning; skip-wallet still postponed.

**Stage 6 -- Wallet tip util + wallet-on reindex**

- Fat-wallet reindex bottleneck catalogued (M-WAL-SYNC-FAT / M-CPU-WAL-FAT); mitigations §0.14.
- Idx1 tip util (G0e); then §0.11 getalldata matrix on disposable profiles 0/2/3.
- Accounts / W5 remain postponed pending review -- do not block Stage 0–4.

**Hold until deliberate resume:** FDCACHE 4x2 + O1/O2 (G6 after witness triage); CleanIndex ExtTests B2; Shieldex full gate; Zero400 TODO edits from this tree.

### 0.14 Wallet-on reindex -- witness bottleneck (G0)

**Settled:** With a large `mapWallet`, IBD/reindex wall is dominated by per-block `BuildWitnessCache(..., witnessOnly=true)` -> `VerifyAndSetInitialWitness` -- **not** by `OrderedTxItems` (WAL-WTXORDERED already incremental). Evidence: M-WAL-SYNC-FAT / M-CPU-WAL-FAT; archive `test-logs/archives/walletsync-fat-g0-20260812.tar.gz`. Genesis `-rescan` on the same Id 3 fat wallet (M-WAL-RESCAN-FAT) is the same Verify path, not ConnectBlock: **finished** 2,518,691 blocks in ~**11.9 h**; cliff at height **1600000** (Halving 2 / founders payee) to ~**19 blk/s** with Select **~98%**; end height-walk **2.0 s**. Next product: **FIX-WAL-WITNESS-NOTEIDX-STALE**.

**Lab flags (opt-in, not default):**
- `-walletwitness=ibd-defer` -- skip per-block IBD `BuildWitnessCache`; rebuild once after `ThreadImport` (M-WAL-WITNESS-IBD-AB ~**35x** to h15k).
- `-walletwitness=rebuild` -- force tip rebuild after import (ungates getalldata).
- `-walletwitnessnote=1` -- **NOTEIDX** (note-bearing tx index): Verify + height walk iterate note txs only (M-WAL-NOTE-DENS **0.175%**; M-WAL-WITNESS-NOTEIDX-AB ~**33x** to h8k without defer).

**Call path (stock):** `ChainTip` IBD branch -> `BuildWitnessCache(pindex, true)` every block -> `VerifyAndSetInitialWitness` over `mapWallet`. With NOTEIDX, Verify walks `vNoteTxHashes` (~1403) after one index build.

**Util sampler:** `wallet_sync_profile.sh` -- `WALLETINFO_TIMEOUT_S` (default 5) so fat `cs_wallet` contention cannot stall `util.tsv`.

#### Mitigation assessment

Effort bands: **S** small, **M** medium, **L** large (no calendar estimates). Impact = expected fraction of the ~50x fat gap closable if the hypothesis holds.

##### FIX-WAL-WITNESS-IBD -- skip/throttle during IBD

| Axis | Assessment |
|------|------------|
| **Idea** | During `IsInitialBlockDownload` (and/or `-reindex` import), do **not** call `BuildWitnessCache` every block; rebuild once when leaving IBD (or every N blocks / at tip). Near-tip path (`BuildWitnessCache(pindex, false)`) unchanged. |
| **Impact** | **High** if almost all of the 97% stack is avoidable until tip -- potential return toward empty-wallet blk/s class for ConnectBlock-bound work (Equihash/disk/tree). Residual: still need one rebuild at tip (cost once, not per block). |
| **Complexity** | **Low–med**. Policy change in `ChainTip` + ensure `initWitnessesBuilt` / spend RPCs stay gated until rebuild completes (existing `initWitnessesBuilt` already gates some paths). |
| **Effort** | **S** for flag prototype; **M** to productize (RPC/docs: z_sendmany unavailable until catch-up; tests). |
| **Risk** | **Med**. Spends/migration during IBD already restricted; must not leave `initWitnessesBuilt` true with empty/wrong witnesses; reorg during deferred rebuild; operators expecting spend-while-syncing. |
| **Status** | **Prototype measured** -- `-walletwitness=ibd-defer` + post-import `RebuildWitnessCacheForChainTip`. |

**Shipped sketch:** `IsIBDWitnessDeferred()` in `ChainTip`; import-end rebuild in `ThreadImport`. Productize: default-or-opt-in, `reindex_shielded` with flag, kill/restart.

##### FIX-WAL-WITNESS-NOTEIDX -- note-bearing tx index

| Axis | Assessment |
|------|------------|
| **Idea** | Maintain note-bearing txid list; `VerifyAndSetInitialWitness` iterates that set, not all `mapWallet`. |
| **Impact** | **High** on golden fat: **1403 / 801619 (0.175%)** note txs (M-WAL-NOTE-DENS). A/B ~**33x** (M-WAL-WITNESS-NOTEIDX-AB). |
| **Complexity** | **Med**. Stale flag + Ensure rebuild. Remaining: stale is too broad (FIX-WAL-WITNESS-NOTEIDX-STALE). |
| **Effort** | Prototype **done**; height walk **done** (shared `SelectWalletTxsForWitnessScan`). Stale narrowing **S**. |
| **Risk** | **Low–med**. Missed invalidate -> skipped note -> spend failure. |
| **Status** | **Shipped in tree** -- Verify + height walk; e2e `wallet_witness_defer.py` green; gtest Select A/B. Stale storm on transparent AddToWallet **open**. |

**What NOTEIDX does** (`-walletwitnessnote=1`):

- `vNoteTxHashes` + `fNoteTxIndexStale`; `EnsureNoteTxIndex()` / `SelectWalletTxsForWitnessScan()`.
- Invalidate on **note-membership** change only (FIX-WAL-WITNESS-NOTEIDX-STALE). **Today** every `AddToWallet` / `EraseFromWallet` invalidates.
- Used by **`VerifyAndSetInitialWitness`** and the **`BuildWitnessCache` height walk** (`witnessOnly=false`).
- Measured IBD: ~33x blk/s (M-WAL-WITNESS-NOTEIDX-AB). Walk logs `BuildWitnessCache height-walk begin/done` with `scan_txs` + `elapsed_ms`.

**Lifecycle and size**

| Event | Index behavior |
|-------|----------------|
| Process start / new `CWallet` | `fNoteTxIndexStale=true`, `vNoteTxHashes` empty |
| `LoadWallet` | Stale stays true from ctor; invalidate only if the loaded tx has notes (STALE). Today every load Add invalidates. |
| First `VerifyAndSetInitialWitness` with flag on | `EnsureNoteTxIndex()`: full `mapWallet` scan once -> fill vector |
| Later Verify while not stale | Walk vector only (O(note_tx)) |
| Transparent `AddToWallet` / `EraseFromWallet` | **STALE:** do not invalidate. Today: invalidate |
| Note insert / note erase / empty-to-nonempty `UpdatedNoteData` | Invalidate; next Ensure rebuilds |
| Restart | Not persisted; rebuild on first Ensure after load |
| Flag off | Vector unused; Verify walks all `mapWallet` |

**Size (RAM, not disk):** `vector<uint256>` ~= `note_tx_count * 32` bytes + vector capacity slack. Golden fat: **1403** note txs -> ~**45 KiB** hashes (negligible vs ~785 MB wallet). `getwalletinfo.note_tx_count` is the live cardinality signal. Cost spike = **one** O(`mapWallet`) Ensure after a real membership change; steady Verify with a hot index is O(note_tx). Unconditional `AddToWallet` invalidate makes that spike **per involving block** (M-WAL-RESCAN-FAT-CPU). `ibd-defer` skips ChainTip Verify, not `-rescan`.

##### FIX-WAL-WITNESS-NOTEIDX-STALE

Narrow when `InvalidateNoteTxIndex` runs. Ready to implement; do not change Select/Ensure/walk algorithms.

**Yes: skipping transparent txs is most of the work.** NOTEIDX already omits transparent txs from Verify and the height walk. The remaining cost is `EnsureNoteTxIndex` rebuilding `vNoteTxHashes` by scanning all of `mapWallet` whenever `fNoteTxIndexStale` is set. On the Id 3 fat wallet that flag is set on every founders coinbase after height **1600000** (Halving 2 / founders slot rotation): about one `AddToWallet` per block, then per-block Verify. Time Profiler in that band: `SelectWalletTxsForWitnessScan` **~98%**, **~19 blk/s** (M-WAL-RESCAN-FAT). Those coinbases have empty note maps. Not invalidating on transparent Add/Erase removes that Ensure. Remaining invalidates are note-bearing inserts, note-bearing erases, and empty-to-nonempty note-map merges -- **1403 / 801619 (0.175%)** on this golden, not per-block. Incremental `push_back`/`erase` on the vector is optional and not required for the win.

**Defect.** `AddToWallet` calls `InvalidateNoteTxIndex()` before insert/merge, including `fFromLoadWallet`, no-op merges (`fInsertedNew` and `fUpdated` both false), and transparent txs. `EraseFromWallet` invalidates for every erased txid. `EnsureNoteTxIndex` is then O(`mapWallet`) on the next `SelectWalletTxsForWitnessScan`. Callers of Select: `VerifyAndSetInitialWitness` (every `BuildWitnessCache`) and the `witnessOnly=false` height walk (once per rebuild, Select once at walk start).

**Note membership.** A txid is a member of `vNoteTxHashes` iff `mapSproutNoteData` or `mapSaplingNoteData` is nonempty (`EnsureNoteTxIndex` loop). Membership **changes** when a note-bearing tx is inserted, a note-bearing tx is erased, or an existing tx goes empty to nonempty via `UpdatedNoteData`. Membership **does not change** for transparent insert/update/erase, merkle/`hashBlock` merge on an existing tx, or note-field merges that stay nonempty. `UpdatedNoteData` treats incoming empty note maps as unchanged and does not clear existing notes, so nonempty-to-empty via merge is not a current path; still treat `hadNotes != hasNotes` after merge as the update rule.

**How to tell the tx is already in `mapWallet`.** `AddToWalletIfInvolvingMe` already has `fExisted = mapWallet.count(tx.GetHash()) != 0`. `AddToWallet` (non-load) uses `mapWallet.insert` -> `fInsertedNew = ret.second` (`false` means already present). That does not skip Ensure by itself. Ensure returns immediately only when `!fNoteTxIndexStale`. Skipping Ensure means **do not set stale** on that call. Do not skip `AddToWallet` entirely on `fExisted` during `-rescan` (`fUpdate=true`); merkle merge still runs. Optional later: skip AddToWallet when `fExisted && !fUpdate`. Not this patch.

**Proposed rule.** Helper (name flexible): `HasNoteData(const CWalletTx&)` true iff either note map is nonempty. Keep `InvalidateNoteTxIndex()` as `fNoteTxIndexStale = true`.

`AddToWallet` `fFromLoadWallet`: invalidate iff `HasNoteData(wtxIn)`. `CWallet` already starts stale; a transparent-only load leaves stale true until the first Ensure (empty vector). A note tx loaded after an Ensure mid-load still invalidates.

`AddToWallet` live path: compute `hadNotes = !fInsertedNew && HasNoteData(wtx)` **before** merge; run existing insert/merge including `UpdatedNoteData`; then `hasNotes = HasNoteData(wtx)`. Invalidate iff `fInsertedNew ? hasNotes : (hadNotes != hasNotes)`.

`EraseFromWallet`: if `it` found, `bool notes = HasNoteData(it->second)` **before** `mapWallet.erase`; invalidate iff `notes`.

Do not invalidate at the top of `AddToWallet`. Flag off (`-walletwitnessnote` unset): Select ignores the vector; stale writes are harmless. Still apply the rule so a later flag-on restart is not required for correctness of in-process toggle (flag is startup-only today).

**Walk logs.** Per-block rescan/IBD uses `BuildWitnessCache(pindex, true)` and returns after Verify -- **no** walk lines. Walk exists only on `witnessOnly=false`:

- `BuildWitnessCache height-walk begin scan_txs=%d mapWallet=%d noteidx=%d startHeight=%d tip=%d`
- `Building Witnesses for block %i %.4f complete` every 100 heights until near tip
- `BuildWitnessCache height-walk done scan_txs=%d elapsed_ms=%d tip=%d`

`-rescan` from genesis calls `BuildWitnessCache(tip, false)` at the **end** of `ScanForWalletTransactions`, still under RPC warmup (`-28 Rescanning...`). Warmup is checked before `fBuildingWitnessCache` (`-33`). Operators will not see `-33` for that inner walk.

`startHeight` is `VerifyAndSetInitialWitness` return + 1. `SaplingWitnessMinimumHeight` only lowers that floor for notes with `GetSaplingSpendDepth <= WITNESS_CACHE_SIZE` (100): unspent (depth 0) or spent in the last 100 blocks. Spent-long-ago notes do not pull the walk, even if they sit in the 1403 note-tx index. Initials are set at birth during the per-block `true` pass; the end walk only increments from that min height to tip.

**Measured (M-WAL-RESCAN-FAT):** end walk `startHeight=2505881` `tip=2518691` (~12.8k blk) `scan_txs=1403` `noteidx=1` **2009 ms**. Not a genesis-to-tip rebuild and not the rescan wall. P2P catch-up `2518692-2518993` **42 ms**. Follow-tip walks **0-1 ms**. `-walletwitness=rebuild` after `Done loading` did not log a second long walk (witnesses already at tip). Contrast M-WAL-WITNESS-TIP-AB (~1441 blk, 220 ms noteidx vs 7659 ms stock). `scan_txs=1403` with `noteidx=1` means the index was hot. `scan_txs=801619` means flag off or Select walked all of `mapWallet`.

**Affected behaviors**

| Path | Today | After patch |
|------|-------|-------------|
| `-rescan` + NOTEIDX + Id 3 fat (founders every block after 1.6M) | Ensure O(mapWallet) per involving block; Select ~98% CPU | Transparent AddToWallet does not stale; Select O(note_tx); one Ensure after load |
| Stock IBD `ChainTip` `witnessOnly=true` + same wallet | Same storm from 1.6M if Verify runs every block | Same win; defer still skips Verify entirely |
| `ibd-defer` IBD | Verify skipped; stale still set; one Ensure at tip rebuild | Stale less often; tip Ensure still once if any note tx arrived |
| Near-tip `ChainTip(..., false)` follow-tip | Founders block: AddToWallet stale + Verify + walk; Ensure O(mapWallet) every block if NOTEIDX on | Transparent coinbase does not stale; walk Select stays O(note_tx) |
| `LoadWallet` | 801k invalidates (already stale) | Invalidate only on the 1403 note txs; first Ensure unchanged |
| `DeleteWalletTransactions` -> `EraseFromWallet` | Invalidate even for transparent deletes (`fDeleteInterval`) | Invalidate only if the erased tx had notes |
| New shielded receive / `z_sendmany` result | Invalidate (correct) | Unchanged: insert has notes |
| `UpdatedNoteData` finds notes on an existing transparent tx | Invalidate already (unconditional) | Invalidate iff empty -> nonempty |
| Zap / `importwallet` / dump rescan | Storm like `-rescan` | Transparent-heavy wallets cheap; note inserts still stale once each |
| Flag off | Vector unused | No Select change |
| Spend / witnesses | Risk = missed stale on a new note tx | Tests below; do not skip invalidate on `HasNoteData` insert |

**Not this patch:** `ibd-defer`; DIRTY; skipping Equihash/`ReadBlockFromDisk` on rescan; clearing witnesses without `-rescan`; RPC `-28` vs `-33` ordering; `FIX-WIT-WALK-UNLOCK`.

**Tests.** Extend `WalletTests.NoteTxIndexTracksNoteBearingTxs` (or a sibling). After a hot index (`Ensure`, stale false, size 0 or 1). **One gtest, both `AddToWallet` flavors** -- do not split STALE and disconnect-style merge into a later PR.

Connect-style (`pblock` set / live insert-or-merge, same as `ConnectTip` `SyncWithWallets(tx, pblock)`):

1. Live `AddToWallet` transparent (`fFromLoadWallet=false`) -> stale stays false, size unchanged.
2. `EraseFromWallet` that transparent tx -> stale stays false.
3. Live `AddToWallet` with nonempty `mapSaplingNoteData` -> stale true; Ensure size += 1; Select with flag on returns that txid.
4. `EraseFromWallet` that note tx -> stale true; Ensure size -= 1.
5. Existing transparent tx, `AddToWallet` merge with `UpdatedNoteData` adding a Sapling map entry -> stale true.
6. Existing note tx, merge that keeps maps nonempty (merkle/`hashBlock` only) -> stale stays false.

Disconnect-style (`pblock` null, `fUpdate=true`, same as `DisconnectTip` / conflicted / mempool `SyncWithWallets(tx, NULL)`):

7. Existed transparent, incoming `hashBlock` null -> merge no-ops; stale stays false.
8. Existed note tx, same NULL merge -> stale stays false (membership unchanged). Decrement is a separate call; this case only covers `AddToWallet`.

Keep: load-path transparent then Ensure size 0; load-path note then Ensure size 1; Select A/B flag on/off.

Do **not** add skip-`AddToWallet` on `fExisted && fUpdate` in this PR. That skip already exists for `!fUpdate` and is unused on `SyncTransaction`. Skipping merge when `fUpdate` is true is a different product change (breaks `-rescan` merkle and disconnect accounting).

**Third skip -- when it would ever be justified.** Two skips already exist or are specified:

1. `AddToWalletIfInvolvingMe`: `fExisted && !fUpdate` returns without `AddToWallet`. Used by `importwallet` (default `fUpdate=false`). Unused on `SyncTransaction` / `-rescan` (both pass `fUpdate=true`).
2. STALE: do not `InvalidateNoteTxIndex` on transparent Add/Erase. This is the founders-cliff fix (new involving txs still enter `AddToWallet`; they must not rebuild `vNoteTxHashes`).

A third skip -- do not call `AddToWallet` when `fExisted && fUpdate` -- is **almost never justified**. Callers that pass `fUpdate=true` need the merge: `-rescan` merkle/`hashBlock`, `DisconnectTip` `SyncWithWallets(tx, NULL)` (merkle not updated; conflict/depth on the fly), mempool-to-confirm, conflicted. The founders cliff is **first insert** of new transparent involving txs (`fInsertedNew`); skipping existed+update does not touch that path. After STALE, remaining cost inside `AddToWallet` for an already-present transparent tx is `FindMySproutNotes` / `FindMySaplingNotes` (still run when `fUpdate`) plus a no-op merge (`WriteToDisk` only if `fInsertedNew || fUpdated`).

Schedule a third skip **only if** post-STALE Time Profiler in the post-1.6M band still shows `FindMyNotes` / `AddToWallet` as the wall. The candidate then is narrower than "skip AddToWallet": skip repeated `FindMyNotes` on an already-indexed tx when keys have not changed. Do not skip the merge. Do not put either form in Cycle 1.

**Incremental `vNoteTxHashes` -- later.** After STALE, `EnsureNoteTxIndex` runs on real note-membership changes only (insert/erase/empty-to-nonempty), not per founders block. One O(`mapWallet`) scan per new shield is acceptable on this golden (1403 notes over the wallet's life vs millions of Ensures during fat `-rescan`). Incremental `push_back` / erase makes that Ensure O(1) but must stay consistent with load, zap, `EraseFromWallet`, and flag-off. Schedule after Cycle 1 rematch **if** Ensure still appears in follow-tip or `importwallet` profiles. Not required for the 19 blk/s cliff.

Boost/regtest: R8 is this gtest. Fat `-rescan` rematch is a lab measure (M-WAL-RESCAN-FAT), not CI. R5b (1/3/10/20) covers Decrement + spend, not NOTEIDX stale.

**Measure gate.** Repeat M-WAL-RESCAN-FAT-CPU after 1.6M with the patch: Select should fall from ~98% toward the pre-cliff mix (Verify + `GetSaplingSpendDepth` / `GetDepth`, not Ensure). Height rate should leave the ~19 blk/s floor if Ensure was the bound. Do not compare to ConnectBlock ~300 blk/s.

**Campaign conclusions.** M-WAL-RESCAN-FAT, confirmed finished.

- The wall is `ScanForWalletTransactions` (per-block `BuildWitnessCache(pindex, true)` + `AddToWalletIfInvolvingMe`), ~**11.9 h** to height **2518691**. The end `witnessOnly=false` walk is **2.0 s** on this wallet; follow-tip is **0-1 ms**. Do not optimize or productize around a long post-rescan walk for Id 3.
- NOTEIDX already keeps Verify/walk on **1403** note txs. The ~**19 blk/s** floor after height **1600000** is Ensure rebuilding that index because every founders coinbase `AddToWallet` invalidates it. Those coinbases have empty note maps. **FIX-WAL-WITNESS-NOTEIDX-STALE** is the remaining NOTEIDX completeness item.
- `ibd-defer` does not apply to `-rescan`. Stock IBD `ChainTip` with the same wallet hits the same storm unless defer skips Verify or STALE lands.
- `1403` is this wallet's note-bearing txs, not chain-wide Sapling density (M-DENS). Walk `startHeight` is min witness height among unspent/recently-spent notes, not oldest note-tx birth.
- Lab pid still following tip after `Done loading`. Do not copy `wallet.zero` back to the live datadir; do not `z_sendmany` on the lab copy.

**Recommended actions**

1. **Cycle 1:** FIX-WAL-WITNESS-NOTEIDX-STALE + gtest R8 (connect-style and disconnect-style `AddToWallet` in the same suite). Do not fold in skip-`AddToWallet` on `fUpdate`, WALK-UNLOCK, incremental `vNoteTxHashes` `push_back`, or `ibd-defer`.
2. Rematch M-WAL-RESCAN-FAT-CPU in the post-1.6M band (measure gate above). Optional: one full `-rescan` after STALE if the CPU rematch is ambiguous. Same cycle, not a separate product PR.
3. After rematch: flag collapse below (NOTEIDX default; drop `-walletwitnessnote`). Keep `ibd-defer` opt-in until the existing default-on gate.
4. **Cycle 2:** Decrement no `exit(1)` + recovery. **TNT-02** reject-and-stay is not scheduled (keep 99 + exit). Not TENT follow, not Zebra-1000. See §0.16 cycles.

| Axis | Assessment |
|------|------------|
| **Idea** | Invalidate NOTEIDX only on note-membership changes. |
| **Impact** | **High** on founders-dense / any wallet with involving txs in most blocks (M-WAL-RESCAN-FAT). |
| **Complexity** | **Low**. Two call sites + helper; gtest. |
| **Effort** | **S**. |
| **Risk** | **Med** if a note insert path skips invalidate -- spend/witness skip. Gtest required. |
| **Status** | **Specified** -- Cycle 1. |

#### Flag and RPC collapse

Today the witness surface is three flags, three bools, and four RPC codes. Collapse after Cycle 1 rematch, in the same validation window -- not a year of one-flag PRs.

**Flags now**

| Flag | Role |
|------|------|
| `-walletwitness=` empty / `ibd-defer` / `rebuild` | Per-block Verify vs skip-until-tip vs force rebuild |
| `-walletwitnessnote=0/1` | NOTEIDX on Verify + height walk |
| `-walletwitnessstats` | Lab-only CONT counters |

**Proposed**

| Surface | After collapse |
|---------|----------------|
| One flag | `-walletwitness=` `stock` / `defer` / `rebuild`. `stock` = current default (per-block Verify). `defer` = today's `ibd-defer`. `rebuild` unchanged. |
| NOTEIDX | Always on once STALE lands. Drop `-walletwitnessnote`. Without STALE, default-on NOTEIDX re-hits the Ensure storm. |
| Stats | Keep hidden (`-debug=witness` or undocumented). Not a product flag. |
| Wallet bools | One enum `WitnessReady { NotBuilt, Building, Ready }` instead of `initWitnessesBuilt` + `fBuildingWitnessCache`. `fNoteTxIndexStale` stays private; never an RPC field. |
| RPC codes | Keep **-28** (warmup), **-31** (unbuilt), **-32** (zeronodes -- do not steal), **-33** (rebuilding). Do not add a code for rejected-reorg; put it on `getblockchaininfo` `errors` / warnings. Status allowlist stays the five names. Do not copy Pirate freeze-all-RPC. |

Clients already retry `-31` and `-33`. Collapsing those two into one `RPC_WALLET_NOT_READY` would save a code and break Zerowallet if it keys on the number. Keep both.

**Not this collapse:** DIRTY flag, `-maxreorg` (Cycle 3), WALK-UNLOCK.

| Axis | NOTEIDX (Verify + walk) |
|------|-------------------------|
| **Impact** | **High** IBD (~33x); tip rebuild walk no longer O(mapWallet) per height |
| **Effort** | **Done** |
| **Risk** | **Low–med** (invalidate correctness) |

#### Interaction: IBD, defer, NOTEIDX, DIRTY, height walk

```
ChainTip / ThreadImport
|
+-- IsIBD && ibd-defer?
|     yes -> skip BuildWitnessCache this block
|     no  -> BuildWitnessCache(pindex, witnessOnly=true)   # per-block IBD
|              -> VerifyAndSetInitialWitness  [NOTEIDX scan]
|              -> return (no height walk, no -33)
|
+-- !IsIBD (near tip) -> BuildWitnessCache(pindex, false)
|                          -> Verify [NOTEIDX]
|                          -> height walk [NOTEIDX]  # sets -33
|
+-- import end && (ibd-defer|rebuild) -> RebuildWitnessCacheForChainTip()
                                         -> BuildWitnessCache(tip, false)  # full path
```

| Mechanism | Removes work from | Does not remove |
|-----------|-------------------|-----------------|
| **NOTEIDX** | Transparent txs in Verify **and** height walk | Per-block Verify frequency; Ensure O(mapWallet) while stale (FIX-WAL-WITNESS-NOTEIDX-STALE); already-validated note visits |
| **ibd-defer** | Entire per-block Verify during IBD | One tip rebuild (Verify + walk) + `-33` window |
| **DIRTY** (not built) | Would remove validated-note visits inside Verify | Height-walk appends; useless if defer skips Verify |
| **Height walk** | Needed once to advance witnesses from initial height to tip | -- |

**Combinations**

| Flags | IBD cost | Tip / post-import | When `-33` |
|-------|----------|-------------------|------------|
| stock | Verify every block over `mapWallet` | occasional full rebuild | full rebuild only |
| noteidx | Verify every block over note txs (~0.175%) | full rebuild walk over note txs | full rebuild only |
| defer | ~ConnectBlock only | one full rebuild at import end | that rebuild |
| defer+noteidx | ~ConnectBlock only | one full rebuild, NOTEIDX walk | that rebuild (shortest) |

**DIRTY vs defer:** if product default is defer, DIRTY's surface (per-block Verify) is gone -- **park DIRTY**. NOTEIDX walk is the tip-rebuild optimization.

##### FIX-WAL-WITNESS-DIRTY -- differential initial-witness set

**What DIRTY means:** NOTEIDX skips *transparent* txs; DIRTY would skip *already-validated notes* too.

**INV-DIRTY-CONT** (`-walletwitnessstats=1`): logs `WitnessStats ... note_visits= early_continue= full_work=` per Verify. Runner: `contrib/perf/witness_lab.sh dirty-cont`.

**Lab result (tiny, stock+NOTEIDX, to h~11k):** `scan_txs=1403` / `mapWallet=801619` (NOTEIDX live). **`note_visits=0`** -- all golden notes are Sapling (activation 492850); tiny tip 187417 is pre-Sapling, so `GetDepthInMainChain()==0` for every note tx during this band. Early-continue rate **not measurable** on tiny. Meaningful CONT needs a **post-Sapling** height window (full/short past 492850) -- L wall; only if stock per-block Verify remains a product default.

**DIRTY recommendation:** **Park.** Defer product path + pre-Sap CONT null result. Do not prototype unless post-Sap CONT shows high early_continue **and** stock Verify stays default.

**Automation vs one-time**

| Lab | Automation | Cadence |
|-----|------------|---------|
| INV-DIRTY-CONT | `witness_lab.sh dirty-cont` (reusable) | **One-time** decision sample per chain band; not CI |
| BENCH-WIT-REBUILD | `witness_lab.sh rebuild` / `rebuild-noteidx` | **One A/B pair** before default-on; re-run when walk/flags change; not CI |
| e2e R1/R2 | `wallet_witness_defer.py` (Tier B) | **Every** relevant change / Tier B |

#### Recommended order

1. **G0b hygiene** -- **done**.
2. **G0c / NOTEIDX density + A/B** -- **done** (0.175%; ~33x). Walk **done**. **FIX-WAL-WITNESS-NOTEIDX-STALE** Cycle 1 (specified).
3. **G0d IBD defer A/B** -- **done** (~35x).
4. **DIRTY** -- still optional (tip-rebuild asymptotics).
5. **Productize** -- decisions in §0.14; execute §0.15 Tier A (docs -> NOTEIDX walk -> RPC allowlist -> rebuild bench -> regtest -> opt-in ship -> default-on gate).
6. **G0e** fat@tiny getalldata -- **done** (scoped); full-mainnet Idx1 open (Tier B).
7. **G6** FDCACHE 8/16KB -- **hold** (Tier C).

#### RPC lockout during witness operations

Two independent mechanisms in `CRPCTable::execute` (`rpc/server.cpp`):

| Gate | When | What is blocked | Error |
|------|------|-----------------|-------|
| `!initWitnessesBuilt` | Witnesses never finished / cleared for full rebuild | **`z_sendmany`**, **`getalldata` only** | **-31** `RPC_DISABLED_BEFORE_WITNESSES` |
| `fBuildingWitnessCache` | Set only in `BuildWitnessCache` **after** Verify, when `witnessOnly=false` (height-walk rebuild) | **All** RPC methods | **-33** `RPC_BUILDING_WITNESS_CACHE` |

**When `-33` actually fires:** not on the per-block IBD `witnessOnly=true` path (Verify returns before `fBuildingWitnessCache=true`). Fires on near-tip full rebuild, `-walletwitness=rebuild`, and post-`ibd-defer` import rebuild. During stock fat IBD the practical stall is **`cs_wallet` held in Verify** (util sampler / wallet RPCs block), not the global `-33` flag.

**Peer comparison** (local trees under `~/Work/ZK/ZKs/`)

| Project | Pref-init / never-built | During full rebuild | Error codes | Notes |
|---------|-------------------------|---------------------|-------------|-------|
| **Zero** | `-31` on **`z_sendmany` + `getalldata`** if `!initWitnessesBuilt` | **All** RPC if `fBuildingWitnessCache` | **-31**, **-33** | Clears `initWitnessesBuilt` for full rebuild; sets building flag only on `witnessOnly=false` path |
| **Pirate** | `-31` on **`z_sendmany` + `z_sendmany_prepare_offline`** if `!fInitWitnessesBuilt` | **All** RPC if `fBuilingWitnessCache` (typo upstream) | **-31**, **-32** | Same global freeze idea; Zero renumbered building to **-33**. PIR-03 source. |
| **Ycash** (`YCASH_WR`) | `-31` on **`z_sendmany` only** | **All** RPC if `fBuildingWitnessCache` | **-31**, **-32** | Same Pirate/WR family shape; no `getalldata` gate |
| **TENT** | `-31` on **`z_sendmany` only** if `!initWitnessesBuilt` | **No** building flag / no all-RPC freeze | **-31** only | `BuildWitnessCache` walks `mapWallet` like Zero but never sets a mid-rebuild lockout; ends by setting `initWitnessesBuilt=true`. Spends can race a long rebuild. |
| **zcashd** (modern) | No `-31`/`-33` in `execute()` | No global witness freeze | N/A | Incremental `IncrementNoteWitnesses` on notify; different wallet model -- not a drop-in policy template for Zero's `BuildWitnessCache` |

**Error codes: do not add witness to `-32`**

| Code | Zero (`protocol.h`) | Pirate / Ycash |
|------|---------------------|----------------|
| **-31** | `RPC_DISABLED_BEFORE_WITNESSES` | same meaning (spend until init) |
| **-32** | **`RPC_ZERONODES_NOT_SYNCED`** (zeronode layer) | `RPC_BUILDING_WITNESS_CACHE` |
| **-33** | `RPC_BUILDING_WITNESS_CACHE` | (unused / different) |
| **-34** | `RPC_DATA_CONTINUE` (getalldata soft) | -- |

Zero already occupies **-32** for zeronodes. Remapping witness rebuild onto `-32` would collide with `RPC_ZERONODES_NOT_SYNCED` and break clients that key on that code. **Keep witness rebuild at `-33`.** When comparing docs/logs to Pirate/Ycash, treat their **-32** as Zero's **-33**. Clients should match on message substring and/or Zero's `-33`, not assume Pirate numbering.

**Recommendation (justified)**

1. **Keep `-31` / `-33` as today** -- do not invent a third witness code; do not steal `-32`.
2. **Keep `-31` for spends + Zero `getalldata`** -- matches Pirate/Ycash spend safety; getalldata is Zero-specific note History.
3. **Do not copy TENT** (no rebuild freeze) -- fat tip rebuild under defer needs mid-flight protection.
4. **Do not copy zcashd's "no lockout"** until incremental witnesses exist.
5. **Diverge from Pirate global freeze:** keep `-33` for wallet/spend/data; **allowlist** `stop`, `help`, `getblockcount`, `getblockchaininfo` (optional net/uptime). Not `getwalletinfo` / `z_*` / `getalldata`.
6. **Shrink the window** with NOTEIDX walk + defer, not by dropping `-33`.

**Implications**

1. **Correctness:** Spend/data gates prevent half-built note use; allowlist must stay non-wallet.
2. **Availability:** Global Pirate freeze makes fat tip rebuild look like a dead node; allowlist fixes monitors/`stop`.
3. **NOTEIDX:** Shortens Verify and (once walk extended) height-walk -- reduces `-33` duration without changing policy.
4. **Clients:** `-33` = retryable soft-outage; `-31` = not ready. Document both.
5. **Self-DoS only:** remote peers cannot set the flag.

**Risk assessment**

| Risk | Severity | Likelihood | Notes |
|------|----------|------------|-------|
| Spend with stale witnesses if freeze removed carelessly | **High** | Low if keep spend gates | Do not adopt TENT "no `-33`" |
| Ops blind during rebuild (all RPC down) | **Med** | **High** on fat rebuild | Allowlist status/ops |
| IBD util/RPC stall via `cs_wallet` (no `-33`) | **Med** | **High** on stock fat sync | Mitigated by ibd-defer / NOTEIDX |
| Comparison.md / PIR prose lag ("z_sendmany only") | **Low** | Certain | Code == Pirate global; docs catch up here |
| Productizing defer without documenting spend delay | **Med** | Med | `initWitnessesBuilt` false until rebuild finishes |

**Product direction:** allowlist as above + NOTEIDX walk + ibd-defer package. **TST-08 done**.

#### Tests

| Test | Covers |
|------|--------|
| `rpc_witness_building_cache_blocks_all_rpc` | `-33` on `z_sendmany`, `getsupply`, `getalldata` (TST-08 + global freeze) |
| `rpc_getalldata_s5_witness_gate` | `-31` on getalldata/z_sendmany |
| `rpc_witness_gate_allows_walletinfo_when_unbuilt` | Monitoring while `-31` |
| `rpc_walletinfo_note_inventory_fields` | NOTEIDX-related counters |
| `wallet_witness_ibd_defer_arg` | `IsIBDWitnessDeferred()` |
| `WalletTests.NoteTxIndexTracksNoteBearingTxs` | NOTEIDX stale/rebuild; extend for STALE (transparent must not stale) |

Lab notes also under gitignored `test-logs/witness-defer-test-plan.md`.

#### Companion hygiene (not FIX-WAL-WITNESS-*)

| Item | Change | Validation |
|------|--------|------------|
| Util sampler | `WALLETINFO_TIMEOUT_S` (default 5) | Fat util.tsv advances |
| `bucket_profile.py` (local `reindex-profile/tools/`) | `witness_cache` before `wallet_add_ordered` | Rebucket ~97% / ~0.03% |

#### What "productize" means here

Lab prototypes prove a speedup under opt-in flags on disposable datadirs. **Productize** = turn that into something operators get without knowing lab knobs -- with defaults, docs, tests, and failure modes that match production use.

| Layer | Lab today | Productize checklist |
|-------|-----------|----------------------|
| **Defaults** | Flags off; stock path still ~50x fat | Choose default on / opt-in / compile-time; document spend-unavailable-until-rebuild |
| **Completeness** | NOTEIDX Verify + height walk done; **stale too broad** | FIX-WAL-WITNESS-NOTEIDX-STALE before calling NOTEIDX done |
| **RPC policy** | Pirate-style global `-33` | Keep vs allowlist status RPCs (`getblockcount`, `stop`, …) -- §0.14 lockout |
| **Tests** | Boost 46/46 exclusive + NOTEIDX gtest | Add regtest: defer through import -> rebuild -> spend; reorg during defer; kill/restart mid-rebuild |
| **Ops docs** | `contrib/perf/README`, Perf §0.14 | Release notes / help text; Zerowallet retry on `-31`/`-33` |
| **Measure gate** | h~8k / h~15k A/Bs | One fat tiny-to-tip (or agreed band) with product flags; compare tip rebuild wall vs stock |
| **Exit criteria** | Prototype A/B green | Default (or shipped opt-in) + tests in `--strict` + no silent witness skip |

Not productize: leaving `-walletwitness=*` as undocumented lab-only forever; shipping defer without documenting that `initWitnessesBuilt` stays false until post-import rebuild.

#### Productize decisions

Recommended answers (open until you override). Rationale under each.

| Question | Recommendation | Why |
|----------|----------------|-----|
| **Defaults** | **Two-step:** (1) ship **documented opt-in** (`ibd-defer` + `noteidx`); (2) flip **default on** only after regtest + rebuild/tip gate | Spends already `-31` until witnesses built, so defer mostly moves when witnesses appear -- but default-on without tip rebuild wall and kill/restart coverage is the wrong first cut. Empty wallets unchanged either way. |
| **Completeness** | **Require FIX-WAL-WITNESS-NOTEIDX-STALE** so Ensure is not per transparent AddToWallet; walk already uses Select | IBD/rescan/follow-tip on founders-dense wallets otherwise pay O(mapWallet) Ensure every block (M-WAL-RESCAN-FAT) |
| **RPC policy** | **Keep `-33` for wallet/spend/data RPCs; allowlist chain/ops:** `stop`, `help`, `getblockcount`, `getblockchaininfo`, `getnetworkinfo`. **Do not** allowlist `getwalletinfo` / `getalldata` / `z_*` during rebuild. Zero has **no** `uptime` RPC. | Matches correctness need (no half-built note reads) and fixes "node looks dead" for monitors. Pirate global freeze is the wrong ops default once defer concentrates rebuild at tip. |
| **Tests** | Opt-in ship: Boost allowlist + R1/R2/R5a (Tier B). **Default-on:** R5b/R7b + kill/restart. R5c is **FIX-WIT-WALK-UNLOCK** (product), not a missing e2e. | Flag unit tests do not prove ChainTip/import coupling. |
| **Ops docs** | **Always with ship** (PROD-WIT-DOCS): help text, `-31`/`-33` retry, "no spend until rebuild finishes" | Cheap; prevents false "node hung" reports. |
| **Measure gate** | **BENCH-WIT-REBUILD required** before default-on; **BENCH-WIT-TIP optional** (one combined `defer+noteidx` trial, not 4-way) | Rebuild isolates `-33` duration. Partial-height A/Bs already prove IBD; tip is confirmation, not discovery. |
| **DIRTY** | **Park** while productizing defer; run INV-DIRTY-CONT only if stock per-block Verify stays a supported default | Defer removes DIRTY's payoff surface; see DIRTY section. |
| **Exit (opt-in)** | Flags in help + docs + Boost in `--strict` + no silent skip | Shipable without flipping defaults. |
| **Exit (default-on)** | Opt-in exit + PROD-WIT-REGTEST + BENCH-WIT-REBUILD + NOTEIDX walk | Then remove "lab only" language. |

**Combo to ship:** treat `ibd-defer` + NOTEIDX as one product package (docs/tests shared). `-walletwitness=rebuild` stays operator/debug.

### 0.15 Open work menu

Tiered. Effort S/M/L. One long trial at a time.

#### Tier A -- do next (witness productize path)

| Order | ID | Work | Effort | Status |
|------:|----|------|--------|--------|
| 1 | PROD-WIT-DOCS | Help strings; `-31`/`-33` retry; defer semantics | S | **done** (help + release note text §0.16) |
| 2 | PROTO-NOTEIDX-WALK | NOTEIDX in height walk | S–M | **done** |
| 2b | FIX-WAL-WITNESS-NOTEIDX-STALE | Invalidate only on note membership | S | **specified** -- Cycle 1; gtest then lab rematch M-WAL-RESCAN-FAT |
| 3 | PROTO-RPC-ALLOW + PROD-WIT-RPC | Status allowlist + Boost | S | **done** (`server.cpp` + `rpc_witness_building_cache_allows_status_rpc`) |
| 4 | BENCH-WIT-REBUILD | Tip rebuild wall ± NOTEIDX | M | **done** tiny (M-WAL-WITNESS-REBUILD, walk noop pre-Sap); post-Sap tip M-WAL-WITNESS-TIP-AB; genesis-rescan end walk M-WAL-RESCAN-FAT **2.0 s** |
| 5 | PROD-WIT-REGTEST R1/R2/R5a | `wallet_witness_defer.py` | M | **done** (Tier B; R5a invalidate at tip-restored) |
| 6 | PROD-WIT-DEFER + NOTEIDX | Ship **opt-in** package | M | **shipped docs/tests** (defaults off; tag when ready) |
| 7 | *(gate)* | Flip **defaults on** | S | after post-Sap rebuild + R5b/R7b; **FIX-WIT-WALK-UNLOCK** optional (not opt-in gate) |

#### Tier B -- after A, or deliberate track switch

| ID | Work | Effort | When |
|----|------|--------|------|
| BENCH-WIT-TIP | One fat trial: stock vs `defer+noteidx` | L wall | Before default-on if rebuild alone feels thin |
| INV-GROTH-CXX | Pirate/zcashd cxx evidence for §0.6a | M | Start of Groth review / G2 |
| INV-DIRTY-CONT | continue_rate under stock+NOTEIDX | S | Only if stock per-block Verify remains default -- else skip |
| INV-CS-WALLET | Which RPCs block on `cs_wallet` in fat IBD | S | Doc polish; optional |
| BENCH-MINE-G5 | Mainnet (192,7) solve Instruments | M | **Scheduled -- Track M**; parallel with Cycle 1; orthogonal to witness |
| BENCH-GAD-IDX1 | Full-tip getalldata Idx1 (~513k UTXO); G0e was fat@tiny only | L | **Parked** until disposable full tip; not witness-blocking |

#### Tier C -- hold / park

| ID | Why hold |
|----|----------|
| PROTO-DIRTY | Wait INV-DIRTY-CONT; likely low value if defer is default |
| PROTO-GROTH-A2 / B0 | Blocked on person A/B decide |
| INV-GROTH-FALLBACK | Policy at implement time, not now |
| INV-SIG-SHARE | Nice for Option B sizing; after cxx spike |
| INV-ARM-MIX / G7 NEON | Fleet unknown; NEON parked |
| BENCH-FD-MID / G6 | Prior null; needs special binary |
| BENCH-BOOT-POST | Parity already noted |
| BENCH-SEG / L3 | **Parked** vs witness track; density tip + onset n=1 done; n=4 optional |

#### Glossary for Tier A items

**NOTEIDX** -- lifecycle/size/axes above; walk **done**; remaining = FIX-WAL-WITNESS-NOTEIDX-STALE.

**BENCH-WIT-REBUILD** -- **lab benchmark** via `witness_lab.sh rebuild|rebuild-noteidx` (not a unit test). **Functions:** `RebuildWitnessCacheForChainTip` / `BuildWitnessCache(..., false)`. **Flag:** `-walletwitness=rebuild`. **Tiny result (M-WAL-WITNESS-REBUILD):** defer import ~333 s to h187417; tip rebuild called but height walk **skipped** (no Sapling notes at/below tiny tip). **Walk correctness** proven by e2e `wallet_witness_defer.py` (notes in regtest tip). Post-Sapling tip A/B still open for walk **duration**.

**DIRTY / INV-DIRTY-CONT** -- see DIRTY section; park with defer-default plan.

#### PROD-WIT-REGTEST -- enumerated e2e

**Existing coverage (compare)**

| ID | Kind | What it proves | Gap vs productize |
|----|------|----------------|-------------------|
| `rpc_getalldata_s5_witness_gate` | Boost | `-31` on getalldata/z_sendmany | No chain / defer |
| `rpc_witness_building_cache_blocks_all_rpc` | Boost | `-33` on spend/data/`getwalletinfo` when flag forced | Allowlist path covered by sibling case |
| `rpc_witness_building_cache_allows_status_rpc` | Boost | `getblockcount` / `getblockchaininfo` / `getnetworkinfo` / `help` ok under `-33` | Flag forced; not real rebuild; `stop` gate-only |
| `rpc_witness_gate_allows_walletinfo_when_unbuilt` | Boost | getwalletinfo ok under `-31` | Correct: blocked under `-33` |
| `wallet_witness_ibd_defer_arg` | Boost | `IsIBDWitnessDeferred()` parses arg | No import behavior |
| `WalletTests.NoteTxIndexTracksNoteBearingTxs` | GTest | Index stale/rebuild membership | No ChainTip / walk |
| `reindex_shielded.py` (Ext B1) | Regtest | Sapling note spendable after `-reindex`; waits `-31`/`-33` | **No** `ibd-defer` / NOTEIDX; **no** allowlist; **no** kill/restart; maturity ~720 blocks |

**Proposed cases** (new `qa/rpc-tests/wallet_witness_defer.py` or extend `reindex_shielded.py`)

| Case | Group | Priority | Spec | Effort |
|------|-------|----------|------|--------|
| **R1** Defer then spend | Core defer | **P0** | Args: `-walletwitness=ibd-defer`. Shield 1 ZEC; mine N blocks (Sapling active). While import/IBD deferred: `z_sendmany` -> **-31** (or still building). After tip rebuild completes: `z_sendmany` succeeds; balance consistent. | M (can reuse reindex_shielded skeleton; shorten maturity if NU_TEST_ARGS allow) |
| **R2** NOTEIDX + defer spend | Core package | **P0** | Same as R1 with `-walletwitnessnote=1`. Assert `getwalletinfo.note_tx_count >= 1` after shield. | S on top of R1 |
| **R3** `-33` vs allowlist | RPC policy | **P0** | Boost: status allowlisted; spend/data `-33`. E2e during real rebuild optional (racey on short tip). | **done** (Boost) |
| **R4** Stock reindex still spends | Regression | **P1** | Keep/alias `reindex_shielded.py` behavior (no defer) so stock path does not regress. | Exists -- promote/gate |
| **R5** Reorg under defer | Correctness | **P1** | Split into R5a/b/c in §0.16. | R5a **done** in e2e |
| **R6** Kill/restart mid-defer | Ops | **P1** | SIGTERM or `-9` during deferred import; restart without defer or with; must not set `initWitnessesBuilt` with empty witnesses; eventually spend works. | M |
| **R7** Kill/restart mid-rebuild | Ops | **P2** | Interrupt during full rebuild (`-33` window); restart; rebuild resumes or restarts cleanly; spend works. | M (harder to hit race) |
| **R8** NOTEIDX invalidate | Index | **P1** | STALE: transparent Add/Erase must not set stale; note insert/erase and empty-to-nonempty must. **Same gtest:** connect-style (`pblock` set) and disconnect-style (`pblock` null) `AddToWallet`. Implement gate for FIX-WAL-WITNESS-NOTEIDX-STALE. | S |

**Grouping**

1. **Core package (P0):** R1 + R2 + R3 -- **opt-in ship gate** (met).
2. **Stock regression (P1):** R4 -- already have Ext test.
3. **Reorg-sharp (P1–P2):** R5a/b + GTest decrement **done**. R5c = **FIX-WIT-WALK-UNLOCK** (product).
4. **Adversarial ops (P1–P2):** R6 open; R7b **done** -- R7b is the default-on kill gate.
5. **Index (P1):** R8 -- gtest required with FIX-WAL-WITNESS-NOTEIDX-STALE.

**Priority order (remaining tests):** R6, R8. **FIX-WIT-WALK-UNLOCK** is code, then e2e.

**Harness note:** Boost alone cannot replace R1/R5/R6 (needs `pcoinsTip` + `ReadBlockFromDisk` + real `ThreadImport`). Prefer Python regtest; keep Boost for gate/unit.

#### Already closed

G0–G0e, NOTEIDX A/B, TST-05, TST-08, M-MINE-REGTEST-SMOKE, M-MINE-NEON-PROBE, fd-cache null, latch/anchor null throughput, PIR-03 in tree.

#### Accepted queue vs this menu

Witness **Tier A** Cycle 1 (STALE) is the active productize path. Groth stays on G2/G3 after G5/G9 slot. G5 is **Track M**, scheduled parallel -- do not interleave G6 or DIRTY into Cycle 1.

### 0.16 Reorg-sharp, opt-in ship, RPC/load, denser lab

#### Reorg-sharp

**Meaning:** Witness cache state is tied to chain tip height (`witnessHeight`, front-of-deque witnesses, `witnessRootValidated`). A reorg disconnects blocks and calls `DecrementNoteWitnesses`, which pops one witness layer when `witnesses.size() > 1` and clears validation flags via other paths. Bugs or incomplete updates here are **sharp** -- wrong root -> spend fail / assert-class failure; missing decrement -> stale witness; over-clear -> forced rebuild. DIRTY sets (if ever built) are especially sharp: must re-dirty notes whose witnesses were popped. With **ibd-defer**, a reorg *during* deferred IBD (witnesses not yet built) is a different mode than a reorg *after* tip rebuild.

**Failure modes to gate**

| Mode | Hazard | Desired recovery |
|------|--------|------------------|
| Reorg while deferred (pre-rebuild) | Spends still `-31`; no half-built cache | Stay unbuilt; rebuild at import end on new tip |
| Reorg during full rebuild (`-33`) | Mid-walk tip moves | Abort/restart rebuild; never `initWitnessesBuilt=true` with partial walk |
| Reorg after built (normal) | `DecrementNoteWitnesses` must match depth | Spends work; optional short rebuild if cache empty |
| Deep reorg / rewind past note birth | Cache may be empty or inconsistent | Clear + `BuildWitnessCache(tip,false)` or refuse with `-31` until rebuild |
| Kill mid-rebuild + reorg on restart | Stale flags on disk | Load: if uncertain, force rebuild before spends |

**Proposed tests** (extend `wallet_witness_defer.py` or sibling; Tier B)

| ID | Group | Priority | Spec | Status / gate |
|----|-------|----------|------|---------------|
| **R5a** | Reorg @ defer window | **P1** (opt-in validated) | Tip restored after reindex+defer; `invalidateblock` tip; remine; wait witnesses; spend | **done** |
| **R5b** | Reorg after built | **P1** (default-on) | Built tip; 1-, 3-, 10-, and 20-block invalidate; remine; spend | **done** (10/20 added) |
| **R5c** | Reorg during `-33` | **P2** | See **FIX-WIT-WALK-UNLOCK** below. Not a reachable e2e on current locks. | **product open** |
| **R5d** | Excessive reorg | **P1** (Cycle 2) | Fork deeper than `MAX_REORG_LENGTH`; node stays up; `getblockcount` unchanged; no `Shutdown: done`; warning in log | **blocked on Cycle 2** |
| **R7b** | Kill mid-rebuild | **P2** (default-on) | SIGKILL during `-walletwitness=rebuild`; restart defer+noteidx; eventually spend | **done** (best-effort race on short tip) |
| **GTest-DEC** | Unit decrement | **P1** | size==1 keep-last (CachedWitnesses*); witnessHeight above disconnect skips pop | **done** (`DecrementNoteWitnessesSkipsAboveHeight`) |

**Groups (reorg-sharp only)**

1. **Defer-window:** R5a -- **done**.
2. **Post-build soft path:** R5b -- **done** (1/3/10/20).
3. **Rebuild-window:** R7b **done** (process death). R5c is not a missing test -- see FIX-WIT-WALK-UNLOCK.
4. **Excessive (not applied):** R5d -- Cycle 2.
5. **Unit edges:** GTest-DEC -- **done**.

**Do not run for confidence:** Bfail RPC tiers (known-fail inventory) or `CachedWitnessesCleanIndex` (always-fail gtest). Coverage those would have provided for shielded reindex is **B1** `reindex_shielded.py`.

#### FIX-WIT-WALK-UNLOCK

**What R5c wanted that other cases do not assert:** a **concurrent** tip change *while* `BuildWitnessCache(..., false)` is mutating note witnesses -- then prove `initWitnessesBuilt` is not set true on a partial walk, spends stay `-31`/`-33`, and the walk aborts or restarts on the new tip.

R5a is reorg **before** rebuild (defer window). R5b is reorg **after** `initWitnessesBuilt`. R7b is **SIGKILL** mid-rebuild (in-memory flags die with the process; wallet.dat may be partial; restart must not spend until rebuild). GTest-DEC is decrement math with no RPC and no `cs_main` walk. Boost allowlist is dispatch policy with the flag forced, no walk. None of those overlap a live walk racing `InvalidateBlock` / P2P `ProcessNewBlock`.

**Why it is not reachable today:** the height walk holds `LOCK2(cs_main, cs_wallet)` for the whole loop (`wallet.cpp` `BuildWitnessCache`). `invalidateblock` is not allowlisted, so it returns `-33` without taking the lock. P2P connect waits on `cs_main` and runs **after** the walk sets `initWitnessesBuilt=true` -- that is R5b, not mid-walk. Measured walk (M-WAL-WITNESS-TIP-AB): stock **7659 ms** / NOTEIDX **220 ms** of held `cs_main`.

**Why it is not the opt-in ship gate:** opt-in defaults off; the lock **serializes** reorgs to after the walk; R7b covers process death; R5a/R5b cover defer-window and post-build reorg. The remaining hazard is **ops latency** (allowlisted `getblockcount` stalls on `cs_main`) and a future walk that **releases** the lock without abort logic.

**Product work (not a longer lab):** periodically drop `cs_main` in the height walk; poll `ShutdownRequested()`; if `chainActive.Tip()` moved or a disconnect landed, abort the walk, leave `initWitnessesBuilt=false`, restart `RebuildWitnessCacheForChainTip` (recovery mode 2) or hard-clear (mode 3). Then an e2e can `invalidateblock` or wait for P2P reorg **during** `-33`. Until that change, a fat-tip soak only shows `-33` on spends and stalled status RPCs.

**Not addressed meanwhile** (do not confuse with R5c): DIRTY re-dirty on pop; default-on of defer; Idx1 getalldata; P2P/DNS follow-tip; full bootstrap ingest; G5 mining (Track M, scheduled); Bfail/CleanIndex.

**Recovery modes (product)**

1. **Soft:** decrement path only (current) when cache depth sufficient.
2. **Rebuild:** `RebuildWitnessCacheForChainTip` if after reorg any note lacks usable witness (detect: empty witnesses / failed root check).
3. **Hard clear:** `ClearNoteWitnessCache` + rebuild if inconsistency logged (prefer over assert / `exit(1)`).
4. **RPC:** keep `-31` until rebuilt; `-33` while rebuilding; status allowlist for monitors.

**Crash and flush.** Chainstate (`FlushStateToDisk` in `Shutdown`) and wallet (`pwalletMain->Flush(true)`; periodic `ThreadFlushWalletDB`) are **separate** databases. `SetBestChainINTERNAL` is an atomic BDB txn for **note-bearing** txs + `nWitnessCacheSize` + best-block locator only. Transparent `AddToWallet` uses per-tx `WriteToDisk`. There is no cross-DB commit with `chainstate/`. After a crash, startup uses the wallet locator (`ReadBestBlock`) and rescans; `clearWitnessCaches` / `-rescan` rebuilds witnesses. Orderly `StartShutdown` reaches that flush. `DecrementNoteWitnesses` `exit(1)` on null `pindex` and `AbortNode` both skip a clean wallet+chain flush if they do not return through `Shutdown()`. Replace those `exit(1)` paths with log + recovery mode 2/3, then `StartShutdown` only if disk is unwritable (`AbortNode` already does that for consensus abort). Do not add a third flush mechanism; use existing `Shutdown` and `SetBestChain`.

**SIGKILL cannot be caught.** POSIX `SIGKILL` (signal 9) cannot be caught, blocked, or ignored. Neither can `SIGSTOP`. `zerod` has no handler path, no `Shutdown()`, no wallet/chain flush. Lab **R7b** uses Python `proc.kill()` = SIGKILL; recovery is restart + whatever hit disk. `SIGTERM` (15) *can* be caught -- that is why FIX-LBI / FIX-IMPORT-POLL exist. Do not design crash recovery around intercepting SIGKILL.

**Excessive reorg -- reject before mutate (TNT-02).** Today `ActivateBestChainStep` computes `reorgLength` from `chainActive` vs fork, then on `> MAX_REORG_LENGTH` logs, `StartShutdown()`, `return false` **before** `DisconnectTip`. Invariant to keep: no `DisconnectTip` / `ConnectTip` / `SyncWithWallets` / `ChainTip` / insight reverse / wallet `AddToWallet` on that fork. Headers may already sit in `mapBlockIndex` / `setBlockIndexCandidates` (required to measure depth); that is not a tip switch. Change: drop `StartShutdown()`; keep `return false`; warning not fatal modal; persist current tip (already on disk). Do **not** follow the fork (TENT `6f64bb7` code). Same gate in unintended `RewindBlockIndex`. New e2e **R5d** once implemented.

#### Integration cycles

Performance first, then crash/reorg hardening. Each cycle is one reviewable PR plus its validation, not a micro-PR per flag or per test ID. Incremental retest of every neighbor is prudent in principle; the cost of that cadence on this tree is months of idle. Bound it: gtest + the one e2e that the cycle changes; rematch the one measure the cycle claims; do not re-run genesis `-rescan` or post-Sap n=4 unless the rematch is ambiguous.

**Cache vs cap (Cycle 3).** Today `WITNESS_CACHE_SIZE = MAX_REORG_LENGTH + 1` (100 slots, apply bound 99). `IncrementNoteWitnesses` caps the per-note deque at that size; `DecrementNoteWitnesses` pops one layer per disconnected block. Cycle 2 **reject-and-stay** never applies past 99, so a 100-slot deque is always enough for an applied reorg. Cycle 3 is the only place the numbers can diverge.

Do **not** choose a cache shorter than the apply cap. If `WITNESS_CACHE_SIZE < MAX_REORG_LENGTH + 1`, an applied reorg of depth D with `cache <= D <= cap` empties the deque while the node still treats the reorg as legal -- spends fail or hit `exit(1)` / forced rebuild. That is the failure mode TNT-03 exists to prevent, not an option. Raising the cap toward maturity 720 or Zebra 1000 means growing the deque (RAM per note) or accepting rebuild-on-deep-reorg; `keeptxfornblocks` is already floored at `MAX_REORG_LENGTH + 1`. Cycle 2 "rebuild if cache short" is recovery after crash or a legal-depth pop that left no layers -- a different sentence.

**Cycle rematch campaign.** Same wallet x op matrix after each cycle, one restartable trial per invocation: `contrib/perf/ops-campaign.sh`. Ops: sync (caught-up start), rescan, reindex, bootstrap. Wallets: none / p0 / p1 / fat. Collate: `contrib/perf/collate_cycle.py`. Do not batch long trials.

| Cycle | Bundle | Deps | Impact | Effort | Risk | Validation |
|-------|--------|------|--------|--------|------|------------|
| **1 -- witness perf** | Package A: STALE + R8 both `AddToWallet` flavors. After rematch: flag collapse (NOTEIDX default; drop `-walletwitnessnote`). | NOTEIDX prototype in tree | **High** fat `-rescan`/IBD after 1.6M (M-WAL-RESCAN-FAT) | **S** then **S** for flags | **Med** missed note invalidate | R8 gtest; campaign `SET=gate` (fat tiny + optional full rescan); post-1.6M CPU if tiny is ambiguous |
| **2 -- stay up** | Decrement no `exit(1)`; recovery 2/3. **TNT-02** reject-and-stay is **not scheduled** (keep 99 + exit). | None on A | **Med** (crash recovery) | **M** | **Med** | GTest-DEC follow-on for rebuild-if-short |
| **3 -- cap sizing** | Packages F then optional G: move 99 only with `WITNESS_CACHE_SIZE >= cap+1` / `keeptxfornblocks` / rewind; optional `-maxreorg` as reject-bound | Cycle 2 proven | **Med** (memory, rebuild cost) | **M-L** | **High** if deque shallower than apply bound | Memory/rebuild review; rematch campaign + RSS; not Zebra-1000 by default |

**Parallel tracks** (do not wait on Cycle 1; do not batch into Cycle 2):

| Track | Bundle | When | Impact | Effort | Risk | Validation |
|-------|--------|------|--------|--------|------|------------|
| **M -- mining** | **G5** mainnet (192,7) timed solve + Instruments on `zcash-miner` | Scheduled now. One trial; Instruments host when free. Orthogonal to witness. Groth G2/G3 still after G5/G9 | **Med** (solve vs verify; NEON later) | **M** wall for one solve | **Low** (disposable template; never Application Support) | `MINE_MAINNET_SOLVE=1`; campaign `mine-equihash-*`; compare to verify ~0.25 ms/blk |
| **Z -- zeronode** | **TST-03** / **TNT-12** / **DOC-02** | **A now** (arg validation, existing Boost). **B** founders window with Cycle 1 if the lab node is free. **C** 2-node after A/B. **D** zeronode `invalidateblock` after Cycle 2. Docs steps 1-2 with A | **Med** product (no harness today) | A **S**; C **M** | **Low** A; **Med** C (collateral setup) | Expand `rpc_zeronode_tests`; then scripted `startalias` |

Package **E** (Decrement uses Select) and incremental `vNoteTxHashes`: after Cycle 1 rematch, only if profiles still show those walks. **WALK-UNLOCK** / R5c: after Cycle 2 if mid-rebuild ops latency matters; not a Cycle 1 or 2 gate. Third skip: only if post-STALE `FindMyNotes` is the wall.

#### Work packages vs later items

| Package | IDs | What | Cycle |
|---------|-----|------|-------|
| **A -- STALE** | FIX-WAL-WITNESS-NOTEIDX-STALE, R8 | Narrow invalidate; gtest connect + disconnect `AddToWallet` | **1**. Not skip-`AddToWallet`. |
| **B -- applied reorg depth** | R5b | 1/3/10/20 post-build invalidate+spend | **Done** in `wallet_witness_defer.py`. |
| **C -- reject-and-stay** | TNT-02, DEF-07 (policy half), R5d | Drop live/rewind `StartShutdown`; do not apply; warn; stay up | **2** with D. Not TENT unbounded connect. |
| **D -- crash-safe witness** | recovery 2/3, GTest-DEC follow-on | No `exit(1)` in Decrement; rebuild if cache short; rely on `Shutdown` flush | **2** with C. |
| **E -- Decrement NOTEIDX** | later | `DecrementNoteWitnesses` uses `SelectWalletTxsForWitnessScan` | After 1 rematch if still hot. Independent of 2. |
| **F -- cap vs maturity** | TNT-03, DEF-07 (sizing half) | Change 99 only with `WITNESS_CACHE_SIZE >= cap+1`, `keeptxfornblocks`, rewind | **3**. Not Zebra-1000 unless memory reviewed. |
| **G -- optional `-maxreorg`** | Pirate-like | Operator raise **if** C is default reject-and-stay | **3** after F. Not an apply-unbounded escape. |

**Not Cycle 1:** skip `AddToWallet` when `fExisted && fUpdate`; WALK-UNLOCK; raising cap; G5; TNT-12 Phase C.

#### Opt-in ship checklist

Ship **`-walletwitness=ibd-defer`** + **`-walletwitnessnote=1`** as documented opt-in (defaults off):

1. Help strings + Perf/contrib README (opt-in wording) -- **done**.
2. NOTEIDX walk **done**; Select shared.
3. Boost gates in `--strict` (incl. allowlist) -- **done**.
4. Tier B: R1/R2/R5a/R5b/R7b -- **done** in `wallet_witness_defer.py`.
5. PROTO-RPC-ALLOW under `-33` -- **done** (`stop`/`help`/`getblockcount`/`getblockchaininfo`/`getnetworkinfo`).
6. Post-Sap **WIT-REBUILD** with notes in range -- **done** (M-WAL-WITNESS-TIP-AB).
7. Release note (paste at tag / GA notes) -- **done** (text below).

**Opt-in package: ready to ship** (defaults remain off). Default-on = above + R5b/R7b. **FIX-WIT-WALK-UNLOCK** is separate product work (optional before default-on if mid-rebuild reorg must be a live race).

**Release note text (opt-in witness flags):**

```
Opt-in wallet witness flags (defaults off):
  -walletwitness=ibd-defer
      Skip per-block witness build during IBD/reindex; rebuild once after import.
  -walletwitnessnote=1
      Witness scan (Verify + height walk) iterates note-bearing txs only.

While witnesses are unbuilt or rebuilding:
  -31  z_sendmany / getalldata until initial witnesses exist
  -33  wallet/spend/data RPCs while a full tip rebuild runs
Status RPCs remain available under -33: stop, help, getblockcount,
getblockchaininfo, getnetworkinfo.

Clients should retry -31/-33. Do not assume spends work until rebuild finishes.
Recommended together for fat wallets: ibd-defer + -walletwitnessnote=1.
```

#### RPC status allowlist + load tests

**How the list was chosen:** Pirate freezes **all** RPC while rebuilding. Zero keeps `-33` on wallet/spend/data so half-built notes cannot be read or spent, and **allowlists** only methods that do not touch the wallet: `stop` (ops can halt a long rebuild), `help`, `getblockcount`, `getblockchaininfo`, `getnetworkinfo` (monitors / Zerowallet "is the node alive"). Denied by default: any other name, including `getwalletinfo`, `getalldata`, `z_*`, `getsupply`, `invalidateblock`. Zero has no `uptime` RPC. `-32` is zeronodes; do not remap.

**What tests actually prove**

| Test | Proves | Does not prove |
|------|--------|----------------|
| `rpc_witness_building_cache_blocks_all_rpc` | `-33` message on `z_sendmany`, `getsupply`, `getalldata`, `getwalletinfo` when flag forced | Exhaustive RPC inventory; real walk |
| `rpc_witness_building_cache_allows_status_rpc` | `getblockcount` / `getblockchaininfo` / `getnetworkinfo` / `help` execute; `stop` exists at the gate (actor not invoked) | Those calls return **during** a real walk (`getblockcount` takes `cs_main` and **stalls** until the walk drops the lock) |
| `rpc_getalldata_s5_witness_gate` | `-31` on getalldata/z_sendmany when never built | `-33` window |
| `wallet_witness_defer.py` R1/R2 | After import+rebuild, spend works | Mid-walk RPC mix |

Safety of "others are not allowed" is the **deny-by-default** name check in `CRPCTable::execute`, not a per-RPC case. Adding a name to the allowlist is the risky change; leaving a method off is safe. Hidden RPCs (`invalidateblock`) are `-33` today -- required so R5c cannot inject via RPC until FIX-WIT-WALK-UNLOCK.

**Load / soak (lab, not CI)**

| Test | How | Metric |
|------|-----|--------|
| Status poll under rebuild | Loop `getblockcount` while `-walletwitness=rebuild` on fat tip | Expect **stall** for walk duration (cs_main), then success; not a hang forever |
| Spend storm while `-31` | Parallel `z_sendmany` before rebuild done | All `-31`; no crash |
| getalldata after rebuild | datatype 0/1; day 2 vs omit; nCount 50/200 | wall_ms; RSS; resp bytes |
| Concurrent status + getalldata at tip-quiet | 1 status/s + 1 gad | No deadlock; gad latency |

#### More e2e and WIT-REBUILD

| Work | Why |
|------|-----|
| R3 allowlist e2e | Optional; Boost already gates allowlist |
| R5c / FIX-WIT-WALK-UNLOCK | Product: drop `cs_main` in the walk, then e2e mid-`-33` disconnect |
| Promote R1/R2 to pass-tier only after stable wall time / optional shorten maturity | Routine gate later |
| **WIT-REBUILD post-Sap** | Fat wallet + tip **>492850**; time `height-walk done elapsed_ms` stock vs noteidx | Real `-33` window -- see assess below |
| WIT-REBUILD + reorg inject | After FIX-WIT-WALK-UNLOCK | recovery mode 2/3 |

Automation: `ZERO_PERF_CHAIN_SNAP=full` on `witness_lab.sh rebuild|rebuild-noteidx` (or tip-only rebuild once a full template exists); one trial at a time.

#### Disposable full tip -- what and how

**What:** A scratch `-datadir` that holds a **mainnet tip** chain (blocks + chainstate near live tip ~2.5M), used for labs that tiny/short cannot answer: Sapling-note height walk, Idx1 getalldata (~513k UTXO), tip-quiet RPC. **Disposable** = never the default Application Support / `%APPDATA%` path; wipe after the trial; goldens stay read-only.

**Why tiny/short fail for post-Sap walk:** tiny tip **187417**, short tip **245992** -- both **pre-Sapling** (activation **492850**). Fat golden notes are Sapling -> height walk **skipped** on those snaps (M-WAL-WITNESS-REBUILD).

**How (tip transplant -- preferred):**

```bash
# Live datadir stopped. Scratch must not be Application Support/zero.
PROD="$HOME/Library/Application Support/zero"
SCRATCH="$PWD/reindex-profile/fulltip-812-datadir"
rsync -a --delete --exclude='wallet.zero*' --exclude='debug*.log' \
  --exclude='.lock' --exclude='zero.conf' --exclude='chainblocks*.tgz' \
  "$PROD/" "$SCRATCH/"
# REQUIRED if source used Insight indexes (else reindex-from-genesis):
#   experimentalfeatures=1
#   insightexplorer=1
```

Verified: tip **2518018**, no reindex, with those flags. Archive pack: `COPYFILE_DISABLE=1 tar -C "$PROD" -czf chainblocks812-clean.tgz blocks chainstate`.

**How (witness rebuild A/B -- full `-reindex` path):**

```bash
ZERO_PERF_SRC_DATADIR="$HOME/Library/Application Support/zero" \
ZERO_PERF_CHAIN_SNAP=full \
ZERO_PERF_WALLET_FILE=/path/to/golden/fat/wallet.zero \
  contrib/perf/witness_lab.sh rebuild-noteidx
```

`SNAP=full` rsyncs `blocks/` (drops chainstate), copies wallet, `-reindex` + `ibd-defer` -- **L wall**. Prefer tip-only:

```bash
ZERO_PERF_TIP_TEMPLATE=$PWD/reindex-profile/fulltip-812-datadir \
ZERO_PERF_WALLET_FILE=/path/to/fat/wallet.zero \
  contrib/perf/witness_lab.sh tip-rebuild-note   # then tip-rebuild
```

**Measured (M-WAL-WITNESS-TIP-AB):** fat @ tip **2518018**; Rescan height-walk (~1441 blk from 2516577): stock **7659 ms** / 801619 txs vs `-walletwitnessnote` **220 ms** / 1403 txs (~**35x**). Rebuild `zerod` after flag renames.

**Idx1:** same full-tip scratch at quiet tip; getalldata datatype matrix (BENCH-GAD-IDX1) still open.

#### Post-Sap WIT-REBUILD -- effort and duration

| Piece | Effort | Duration band | Evidence / bound |
|-------|--------|---------------|------------------|
| Script/docs for `SNAP=full` (exists) or tip-only mode | **S** | -- | `witness_lab.sh` already has `full` |
| Prep disposable full tip (rsync ~10G blocks + `-reindex`) | **M** ops | **L wall** once | Empty full-chain import historically ~**145 min** (bootstrap); wallet-off reindex same class |
| Fat + defer import to full tip (if not tip-only) | **M** ops | **L wall** per trial | Defer IBD ~ConnectBlock-only; tiny defer import ~**333 s** to h187417 (M-WAL-WITNESS-REBUILD) -- full tip scales with chain length, not note walk |
| Tip height-walk A/B (the measurement) | **S** once tip ready | **unknown** until run | Tiny walk **skipped**; NOTEIDX scans **1403** txs; stock would scan **~801k** -- expect large NOTEIDX win; do **not** invent wall_ms |
| Pair of trials (stock vs noteidx) | -- | **2x** tip-walk (or 2x full reindex if no template) | Lab rule: one long trial per invocation |

**Assess:** Coding/docs **S**; ops **M**; wall **L** for first full reindex, then tip-only A/B should be much shorter than reindex (walk-bound). **Blocking input:** disposable full tip (or any tip >492850 with fat notes in range). Not required for opt-in ship; recommended before default-on.

#### Density / L3 and Idx1 tip

**Shielded density + L3 (BENCH-SEG): parked** relative to witness opt-in. Offline `shielded_density.csv` counts Sapling spends/outputs / Sprout JS per height band (fine rematch windows + coarse 400k bands split at activation). **L3** = era-bounded ConnectBlock rematch (onset bootstrap/reindex peers) using those era labels -- wallet-off sync narrative, not witness. Done: density tip-complete; onset n=1 peers. Optional: n=4 if noise warrants. Resume only on deliberate Stage-1 / rematch track switch.

**Idx1 tip getalldata -- remains open.** Same disposable full tip as above. G0e was fat@**tiny** only (~0.75–1.2 s). **BENCH-GAD-IDX1** = quiet full tip + datatype matrix; L wall; not witness-blocking.

#### Dev profile Id 1 retest + inflated wallet library

**Profiles (opaque ids in public docs -- no host paths):**

| Id | Intent | Prior |
|----|--------|-------|
| **0** | Empty / tiny keypool | M-WAL-SYNC-P0 ~950 blk/s |
| **1** | Non-empty mid-size (Dev personal / extracting) | **M-WAL-SYNC-P1** -- ~918 blk/s; wallet 237568 B; txcount 133; note_tx 0 |
| **2** | Extracting / intermediate | §0.11 matrix slot |
| **3** / fat | Golden ~800k tx | G0 / NOTEIDX / defer |

**Id 1 (`M-WAL-SYNC-P1`)**

1. Tiny `-reindex` on disposable scratch -- **done** (`test-logs/walletsync-20260813T055703Z/`).
2. Catalog: wallet **237568** B flat; txcount **133**; note_tx **0**; tip **187417** in **~201 s** (~**918** blk/s); RSS **~103->398 MiB**.
3. CPU Time Profiler -- **skipped**: no notes; throughput in P0 class (witness_cache not the story). Revisit only if a later Id 1 golden gains Sapling notes.
4. A/B defer+note -- low value here (note_tx 0); keep for fat / Id 2+.
5. Tip-quiet getalldata -- optional; not Idx1.

**Inflated wallet library (reuse)**

- Keep **read-only golden copies** outside scratch (ops-local; not git): Id 0/1/2/3 (+ fat). After each trial, **discard** scratch; never mutate goldens.
- Optional: one **pre-inflated scratch template** (chainstate+blocks at tiny/short tip + wallet copy) rsync'd per run to skip tar extract -- still copy wallet from golden each time.
- Document sizes in Measures when measured (`wallet_bytes`, txcount, note_tx); refresh goldens only on deliberate ops snapshot.
- Cleanup rule (post-lab): wipe used scratch datadirs (e.g. `witness-tip-rebuild-datadir`); keep one full-tip **template** (`fulltip-812-datadir`) until P2P/bootstrap labs finish; keep `test-logs/*/SUMMARY` + archives. Never touch Application Support `zero/` or Zero400 trees.

#### Proposed next execution order

1. Opt-in ship -- packaging **done** (tag when maintainer cuts release); defaults off.
2. P2P follow-tip from archive template (DNS, distinct rpcport); full bootstrap ingest later.
3. **FIX-WIT-WALK-UNLOCK** -- product; then mid-`-33` e2e.
4. Idx1 / L3 n=4 -- **parked** until deliberate track switch.


## 1. Scope, method, and reproduction procedure

**Subject:** where `zerod` spends CPU during `-reindex` (rebuild `chainstate` from local `blocks/*.dat`) and `bootstrap.dat` import (bulk-load a pre-staged flat file of blocks) — the two faster-than-network ways to catch a node up. Both were assumed "fast" but never measured; this investigation measured them, found the dominant costs, and implemented and measured fixes for two of them.

**Working tree:** `ZeroPerf` (`/Users/walter/Work/ZK/ZeroPerf`, branch `perf-401`), built at `-O1` (`-pipe -O1 -g -fwrapv -fno-strict-aliasing`, the repo default). Binary is self-contained (verified via `otool -L`: only system libraries dynamically linked, all third-party dependencies static).

**Terms:**
- **Bucket:** one of a small number of mutually-exclusive CPU-time categories a profiling sample falls into, matched against *any* frame in a sample's call stack (not just the leaf).
- **Latch:** a single-slot memoization — one stored value (or empty), cleared by the operations that change underlying state, repopulated on next read. Not a cache: no key, no multiple entries, no eviction policy, because there is only ever one live value to remember.
- **Activation height:** the mainnet block height at or after which a network upgrade's rules apply. Sapling: height 492,850 (`chainparams.cpp`).

**Profiling method:** a real mainnet datadir (not synthetic/regtest — script/tx mix affects where time goes) profiled with Instruments Time Profiler (`xcrun xctrace`, headless CLI) attached to the single worker thread that does the actual reindex/import work (`zcash-loadblk`, running `ThreadImport`). Every other thread (idle script-check-queue workers, RPC/net/**wallet** threads) is filtered out — unfiltered, all-threads profiles are dominated by idle-thread noise (85%+ of raw samples blocked on a condvar) and say nothing about where real work goes.

**Scope note -- ConnectBlock vs wallet-on:** `capture_sequence.sh` / `bench_matrix.sh` default filter is **ConnectBlock / import** on `zcash-loadblk` (Groth16, Equihash, disk, trees). Fat-wallet reindex is a **separate** track: M-WAL-SYNC-FAT / M-CPU-WAL-FAT / §0.14 -- bottleneck is `VerifyAndSetInitialWitness`, not `OrderedTxItems` (WAL-WTXORDERED done). ZeroStruct §13.4.3 for order-insert history.

**Retarget for wallet-on sync CPU:** attach Time Profiler to live `-reindex` with fat wallet; bucket **ALL** threads (or loadblk -- witness runs on loadblk); use `witness_cache` needles (§0.14 hygiene) plus AddToWallet/OrderedTxItems; record height window. Do not interpret empty-wallet profiles as fat-wallet cost.

**Reproduction procedure** (fresh scratch datadir → launch → attach profiler → export/bucket → determine the exact height window covered):

1. Fresh scratch datadir (chainstate excluded; `-reindex` rebuilds it — source `~/Library/Application Support/Zero/` is only ever read, never modified):

   ```bash
   cd /Users/walter/Work/ZK/ZeroPerf
   rm -rf reindex-profile/datadir
   rsync -a --exclude='chainstate' "/Users/walter/Library/Application Support/Zero/" reindex-profile/datadir/
   ```

2. Launch `-reindex`, poll `getblockcount` via `zero-cli` until height has advanced (RPC gives an exact, race-free signal — don't guess from wall-clock or log-tailing), then attach Time Profiler:

   ```bash
   ./src/zerod -datadir="$PWD/reindex-profile/datadir" -reindex -connect=0 -listen=0 -rpcport=23920 &
   PID=$!
   until h=$(./src/zero-cli -datadir="$PWD/reindex-profile/datadir" -rpcport=23920 getblockcount 2>/dev/null) \
         && [[ "$h" =~ ^[0-9]+$ ]] && [ "$h" -gt 3000 ]; do sleep 3; done
   xcrun xctrace record --template 'Time Profiler' --output reindex-profile/timeprofile.trace --time-limit 60s --attach "$PID"
   kill -TERM "$PID"  # once the recording completes
   ```

3. Export and bucket the trace:

   ```bash
   xcrun xctrace export --input reindex-profile/timeprofile.trace \
     --xpath '/trace-toc/run[1]/data[1]/table[@schema="time-profile"]' \
     --output reindex-profile/timeprofile_agg.xml
   python3 reindex-profile/tools/bucket_profile.py reindex-profile/timeprofile_agg.xml
   ```

   `xcrun xctrace export` produces a flat XML table where `<thread>`, `<weight>`, `<tagged-backtrace>`, and `<frame>` elements are each defined in full **only once**, with every later occurrence a bare `ref="N"` backreference — a naive per-row regex silently undercounts almost everything after the first sample. `reindex-profile/tools/bucket_profile.py` resolves all four backreference types correctly and buckets by call-stack substring match (edit the `BUCKETS` dict to add/adjust categories). Second argument filters to one thread by substring (default `zcash-loadblk`) — always filter to a specific thread.

4. **Determine the exact block-height range the window covered** — not from the datadir's *final* height, which is a trap; block/tx mix varies enormously by height, so a bucket breakdown is only interpretable together with its height range:

   1. Get the trace's actual recording start time, in its own stated timezone: `xcrun xctrace export --input some.trace --toc | grep start-date`.
   2. Convert explicitly to whatever timezone `debug.log` uses (Zero's is UTC) — a background-launched process's wall-clock launch time is not the same as when the recording window actually started, and mixing local time with a UTC log timestamp will silently shift the derived window by hours.
   3. Grep `debug.log` for `UpdateTip` lines whose timestamp falls in `[start, start+60s]`, and read `height=` off the first and last matches — bound by timestamp, not by searching for a height number as a substring (`height=937` also matches `height=937237`).
   4. For bytes/sec alongside blocks/sec: sample block `size` at a handful of evenly-strided heights via `getblock` RPC (needs a running node — pointing a plain launch at the already-reindexed scratch datadir works, no need to redo the reindex). Block size varies by two orders of magnitude block-to-block, so treat this as an estimate with real uncertainty, not an exact figure.

**General lesson:** don't trust a bucket percentage, height range, or throughput figure that wasn't cross-checked against a second source of truth (a different trace, a log timestamp, an RPC call) — every number in §2 that turned out to matter was caught or confirmed this way, and every early mistake (an 86%-other mis-parse, a wrong-timezone height window, a substring-match height search) was a case of trusting one source without a second check.

### Lab materials

Canonical home for lab inputs and scratch locations (not duplicated in Measures). Do not modify originals; copy or softlink into scratch.

| Role | Location | Notes |
|------|----------|-------|
| Original `bootstrap.dat` | Out-of-tree `~/Work/ZK/linearize/bootstrap.dat` | Regenerated **2026-08-13** (~5.04 GiB); hashlist heights **0-2468990**; magic ZERO `5a45524f`. Live tip ~2518018 is ahead. Moved out of `Zero400/contrib/linearize/` **2026-08-16** (repo tree keeps only `hashlist.txt` + the `linearize-*.py` scripts). Lab softlink: `reindex-profile/bootstrap-src/bootstrap.dat`. Smoke: **M-BOOT-NEW-20260813**. Read-only / copy only. |
| Full chain snap | macOS Application Support `zero/` | Live tip **2518018** (verified); `blocks/` ~10G + `chainstate` ~619M + `blocks/index` ~4.7G. Live tree may have **xattrs** (`com.apple.provenance`) with **no** on-disk `._*` (`find . -name '._*'` empty) -- macOS `tar` still emits AppleDouble into archives unless `COPYFILE_DISABLE=1`. Prefer **`chainblocks812-clean.tgz`** (~8.5G) or rsync. Older `chainblocks812.tgz` may include `._*`. Tip transplant needs `insightexplorer=1`. |
| Short / tiny snaps | same datadir | `chainblocks-short.tgz` ~342M; `chainblocks-tiny.tgz` ~228M; sha256 sidecar |
| Disposable full tip scratch | `reindex-profile/fulltip-812-datadir` | rsync from live (or clean archive); `zero.conf` must include `experimentalfeatures=1` + `insightexplorer=1` or node **reindexes from genesis** |
| Bench ledger / reports | `reindex-profile/bench-summaries/` | `ledger.*` via `accumulate_bench.py`; historical TSV / memprofile |
| Post-Sapling scratch | `reindex-profile/postsapling-datadir` | From `postsapling_reindex.sh` |
| DevFee ops wallets | out-of-tree DevFeeWallets | Fat-address getalldata; not ConnectBlock CPU |

Bootstrap-mode datadir reset must exclude `blocks/` (M-INIT-03 / §3). Current stock campaigns use `-reindex` / `-loadblock` without FDCACHE 4x2. Script usage: **contrib/perf/README.md**. Bound ledger campaigns: **Measures.md** §8.

---

## 2. CPU cost breakdown: what dominates, and why it's height-dependent

**Original measurement** (`-reindex` on two builds, `bootstrap.dat` import, chain heights ~10K–2M; mutually exclusive buckets, `zcash-loadblk` thread only, 0% unaccounted backtraces in every run):

| Bucket | Typical range | Call path (leaf → root) |
|---|---|---|
| Sapling/Sprout tree update | 57–58% | `Fr::mul_assign`/`Fr::inverse` (BLS12-381 field arith) ← `jubjub::edwards::Point::add` ← `librustzcash_merkle_hash` ← `IncrementalMerkleTree::root()` ← `CCoinsViewCache::AbstractPushAnchor` ← `ConnectBlock` |
| Equihash PoW verification | 24–27% | `blake2b_compress_ref` ← `blake2b_final` ← `Equihash<192,7>::IsValidSolution` ← `CheckEquihashSolution` ← `CheckBlockHeader` |
| Disk I/O | 15–18% | `OpenDiskFile`/`ReadBlockFromDisk`/`UndoWriteToDisk` (`fopen`/`open` syscalls) ← `LoadExternalBlockFile`/`ConnectBlock` |

**This breakdown is identical for `-reindex` and `bootstrap.dat` import** — both call the same `ConnectBlock`/`CheckEquihashSolution`/`AbstractPushAnchor` validation per block; `bootstrap.dat` only changes how block bytes arrive, not what validation happens once a block is in hand. Measured `bootstrap.dat` import: **145.7 minutes** (8,743,120 ms, self-reported) for 2,468,990 blocks, ≈282 blocks/sec average across the entire chain history. **`bootstrap.dat`'s entire benefit is skipping network download time; it cannot reduce the CPU-bound validation cost.**

**`bootstrap.dat` for these measurements** was generated via Zero400 `contrib/linearize` from a synced node's `blocks/` (not a network download). Paths and regenerate notes: §1 Lab materials.

**The idle script-check-queue threads (`zcash-scriptch`, `-par`) cannot help any of this bucket breakdown.** They're wired only to per-transaction signature verification, never to anchor/tree updates, in every codebase checked (Bitcoin Core, zcashd, Zero, Zebra). This is a per-call cost problem in code that has never been parallelized, not a parallelism gap in otherwise-idle threads.

**Correction — the table above conflates two distinct costs.** Sapling's Groth16 zk-SNARK proof verification (`librustzcash_sapling_check_spend`/`_check_output`, called from `ContextualCheckTransaction`) *also* does elliptic-curve arithmetic over the same `jubjub`/BLS12-381 types used by tree-anchor recomputation, deep inside `bellman::groth16::verifier::verify_proof` — the original bucket definitions couldn't tell these apart. Re-bucketing with a set that checks for `bellman::groth16::verifier::verify_proof`/`miller_loop`/`final_exponentiation` specifically splits it correctly:

| Bucket | % of CPU (height 610,758–626,806) | Call path |
|---|---|---|
| **Sapling Groth16 proof verification** | **60.9%** | `Fq::mul_assign`/`Fq12::square` (BLS12-381 pairing arith) ← `miller_loop` ← `bellman::groth16::verifier::verify_proof` ← `librustzcash_sapling_check_spend`/`_check_output` ← `ContextualCheckTransaction` |
| Disk I/O | 26.2% | Same syscalls as above |
| Equihash PoW verification | 6.9% | Same call path as above |
| Sapling/Sprout tree/anchor update | 6.1% | Same call path as above — **this is what the original "57–58%" figure actually measured almost none of** |

Cross-checking against an earlier-build trace spanning the full 0–2.47M height range and re-bucketed with the corrected script gives **0 Groth16 samples**, reproducing the original 58/26/16 split almost exactly — confirming the corrected script isn't the source of the discrepancy, and that the original figure was measured on a height range with negligible Sapling shielded-tx volume (Sprout-dominated or pre/early-Sapling), so it wasn't wrong about *that window*, only wrong as a general claim about "the" bucket breakdown.

**The bucket breakdown is height-dependent, not a fixed constant** — any profiling result needs its block-height range reported alongside it to be interpretable. Throughput for the 610,758–626,806 window: 267.5 blocks/sec (exact, from `UpdateTip` timestamps), ~330 KB/sec (estimated from 41 evenly-strided `getblock` samples, individual blocks ranging 685–160,858 bytes) — consistent with the whole-chain ~282 blocks/sec average.

**Whole-chain confirmation, six 5-minute windows spanning the reindexed range** (`contrib/perf/capture_sequence.sh` drove the repeating capture; `contrib/perf/decode_captures.py` exported/bucketed each one and derived its exact height range from the trace's own timestamp cross-referenced against a `debug.log` snapshot — see `contrib/perf/README.md`):

| Capture | Height range | blocks/sec | Groth16 | Disk I/O | Tree/anchor | Equihash |
|---|---|---|---|---|---|---|
| 1 | 5,373 → 336,144 | 1,102.6 | 0% (pre-Sapling) | 16.54% | 54.99%* | 28.46% |
| 2 | 626,078 → 702,200 | 253.7 | 54.74% | 25.03% | 13.83% | 6.40% |
| 3 | 995,392 → 1,083,180 | 292.6 | 52.77% | 26.20% | 13.67% | 7.36% |
| 4 | 1,411,397 → 1,482,630 | 237.4 | 55.23% | 24.94% | 13.94% | 5.88% |
| 5 | 1,693,202 → 1,777,052 | 279.5 | 53.84% | 25.03% | 14.01% | 7.12% |
| 6 | 2,032,619 → 2,173,838 | 470.7 | 48.09% | 26.02% | 13.78% | 12.11% |

*Capture 1 is pre-Sapling-activation: its "tree/anchor" share is inflated only because Groth16 doesn't exist yet at these heights.

Post-Sapling (captures 2–6), Groth16 is consistently dominant (48–55%) across five independently-sampled ranges spanning nearly the whole post-activation chain — the single-window 60.9% figure was directionally correct, though the exact percentage tracks per-window shielded-tx volume rather than being a fixed per-block overhead. Disk I/O (~25–26%) and tree/anchor (~14%) are comparably stable. Equihash's *share* climbs from ~6% to ~12% (captures 4→6) — a percentage effect, not a cost effect (see per-block table below): capture 6 processed more blocks/sec, spreading a constant per-header cost over less wall-clock time per block.

**Per-block absolute cost, the more informative view:**

| Capture | Groth16 ms/block | Disk I/O ms/block | Tree/anchor ms/block | **Equihash ms/block** |
|---|---|---|---|---|
| 1 (pre-Sapling) | — | 0.149 | 0.494 | **0.2557** |
| 2 | 2.149 | 0.983 | 0.543 | **0.2513** |
| 3 | 1.788 | 0.888 | 0.463 | **0.2493** |
| 4 | 2.324 | 1.050 | 0.587 | **0.2476** |
| 5 | 1.921 | 0.893 | 0.500 | **0.2541** |
| 6 | 1.005 | 0.543 | 0.288 | **0.2530** |
| **mean / CV** | 1.84ms / **27.7%** | 0.75ms / **45.7%** | 0.48ms / **21.5%** | **0.252ms / 1.2%** |

Groth16, disk I/O, and tree/anchor per-block cost all vary substantially (21–46% CV) — expected, each scales with shielded-tx volume or block/undo-file size. **Equihash's per-block cost is essentially constant (0.252ms ± 1.2% CV)** across pre- and post-Sapling heights and blocks/sec ranging 237–1,103 — the signature of a fixed per-call cost independent of block content (root cause: §5).

**Not yet investigated:** nothing has targeted Groth16 verification cost specifically (§0 item 2) — the latch (§4) and the proposed root-existence index (§0 item 4) both target the tree/anchor bucket only, ~6–14% of CPU, not the 48–60% Groth16 bucket.

**Memory profiling:** Instruments' Allocations/Leaks templates attach successfully (`task_for_pid`, entitlement + Developer Mode satisfied) but their recorded data is a GUI-only proprietary blob with no `xctrace export` schema in this Instruments version — headless readout is a dead end via that template. `vmmap`/`heap`/`malloc_history` are CLI-native with no export-format dependency and haven't been tried yet (§0 item 5).

---

## 3. Disk I/O: open-close-per-block mechanism, and the implemented fix

**Mechanism.** `OpenBlockFile`/`OpenUndoFile` both call `OpenDiskFile`, which does a **fresh, unconditional `fopen()` on every call** — no persistent or cached `FILE*` anywhere in this path. Every call site wraps the fresh `FILE*` in a stack-local `CAutoFile`, whose destructor calls `fclose()` unconditionally the moment the function returns. `ConnectBlock`/`LoadExternalBlockFile` call these once or twice per block (a read, usually an undo-data write) — a full ~2.5M-block reindex therefore performs on the order of **2.5–5 million `fopen`/`fclose` pairs**, even though the underlying `blkNNNNN.dat`/`revNNNNN.dat` files are ~128MB each holding thousands of consecutive blocks: the overwhelming majority of those pairs reopen a file that was just closed moments earlier for the previous block. Each pair is a full kernel `open`/`close` round-trip, and `fopen` additionally re-initializes stdio's internal buffer from scratch every time — cost paid once per block instead of once per file, a 100–1000x amplification.

**Direct syscall-level confirmation** (`fs_usage -f filesys -w <pid>`, root-only, always available, no SIP change needed unlike full `dtrace`; Instruments' File Activity template records real data but has no `xcrun xctrace export` schema in this Instruments version — GUI-only, not usable headlessly): in a 180-second `-reindex` window, `open` alone was 23% of traced filesystem time; `open+close+stat64+fstat64` together came to ~0.048ms/block — real, but only 6–34% of the disk-I/O bucket depending on capture window, meaning most of that bucket is genuine read/write/transfer time, not open/close overhead.

**The fix, `#ifdef ZERO_FDCACHE`-gated** (a macro separate from `ZERO_PERF`, independently buildable/strippable):

- **`-perffdcache=1`** (default 0): `ReadBlockFromDisk`/`UndoReadFromDisk` use a single-slot read-handle latch per file kind (`BlockFileKind::BLK`/`REV`) instead of `OpenDiskFile`'s fresh-open/close-per-call path — mirroring `IncrementalMerkleTree::root()`'s latch (§4), not a multi-entry keyed cache. Ownership stays with the latch: `CAutoFile` borrows the handle for the duration of one read and is prevented from closing it on destruction via `ReleaseOnScopeExit`, a small RAII helper that calls `CAutoFile::release()` (an already-existing, pre-`ZERO_FDCACHE` method — no changes to `CAutoFile`/`streams.h` were needed). Stats (opens/hits, plain counters under the latch's own lock) log periodically as `ReadFdCache: height=N opens=... hits=... hit-rate=...%`. Read-only handles only: write handles are excluded, since `FlushBlockFile`'s truncate/close and `CAutoFile`'s owning-close semantics make caching writable handles a real correctness hazard for a smaller expected benefit.
- **`-perfbufsize=N`** (default 0 = unchanged libc default): `setvbuf`s a freshly-opened handle to an N-byte buffer in `OpenDiskFile`, instead of the libc/filesystem default (commonly 4–8KB).

**Latch, not a multi-slot cache — checked, not assumed.** An earlier version used a 4-slot LRU on the theory that RPC/reorg access could interleave across multiple files. Measuring real access during a `-reindex` run showed the open count grows strictly monotonically with no repeats for long stretches, then occasionally revisits an earlier file — traced to `LoadExternalBlockFile`'s "out of order child" handling, which reprocesses an earlier block file when a later block's parent hasn't connected yet. A single-slot latch handles this correctly by design (a miss costs one `fopen`, not a correctness issue) — measured hit rate stayed **99.9%** even across that access pattern, heights 0 through ~900,000.

**Implementation status: functionally correct, compiles clean both with and without `ZERO_FDCACHE`, no unit test coverage.** Only `main.cpp`/`main.h` carry changes — `streams.h` and `init.cpp` ended at zero diff from upstream after an earlier, more invasive draft (a `CAutoFile` ownership flag, an unused `CloseAllCachedReadFiles` shutdown hook) was reviewed back out in favor of the smaller `ReleaseOnScopeExit` approach and removing dead code. Known, accepted gaps: `ReleaseOnScopeExit` is constructed (as an inert no-op) even in normal builds without `ZERO_FDCACHE`; no gtest exists for the latch's hit/miss/stale-reopen behavior, unlike §4's latch which has a dedicated test.

**Measured result: no throughput improvement from either flag, at pre-Sapling heights.** Repeated-trial A/B (`contrib/perf/bench_matrix.sh`: fixed height range warmup=50,000→measured 50,000–350,000, exact elapsed time from `debug.log` `UpdateTip` timestamps, 4 trials per condition, both with `-perffdcache=1`):

| Condition | n | Mean blk/s | Stdev | CV |
|---|---|---|---|---|
| Default buffer | 4 | 1,094.1 | 15.9 | 1.45% |
| 1MB buffer | 4 | 1,075.9 | 29.9 | 2.77% |

Difference: -1.66%, t ≈ -1.07 — not distinguishable from noise at this sample size (would need |t| > ~2.5–2.6 for significance with n=4 each). This establishes the noise floor this methodology resolves at a 300,000-block window: ~1.5–3% CV per condition. Consistent with average block size (~1.3–2KB) being far smaller than either buffer setting.

**Re-measured at post-Sapling heights, with a true no-fdcache baseline added (§0 item 1).** The original A/B above never tested `-perffdcache` against a real off condition (every trial had `-perffdcache=1`), and only covered pre-Sapling heights. `bench_matrix.sh` was extended with a third `nofdcache` condition (`-reindex` with neither flag — the fd-cache code path entirely inactive) and re-run at warmup=600,000→measured 600,000–900,000 (entirely post-Sapling; activation is 492,850), 4 trials per condition, 3 conditions:

| Condition | n | Mean blk/s | Stdev | CV |
|---|---|---|---|---|
| No fd-cache | 4 | 307.22 | 5.615 | 1.83% |
| Default buffer (fdcache on) | 4 | 310.56 | 0.261 | 0.08% |
| 1MB buffer (fdcache on) | 4 | 309.28 | 0.000 | 0.00% |

`ReadFdCache` log lines confirm the mechanism itself is engaging correctly at these heights: `nofdcache` trials show `opens=0 hits=0` throughout (code path genuinely inactive, not just untuned), while both fdcache-on conditions show **99.9% hit rate** — identical to the pre-Sapling hit rate found earlier, confirming §3's single-slot-latch design holds at post-Sapling heights and shielded-tx volumes too.

**Result: still no measurable throughput win, now with the isolation this item set out to get.**
- **fd-cache on vs. off** (no-fdcache → default-buffer): +1.09%, t ≈ 1.19 — not distinguishable from noise (same |t| > ~2.5–2.6 bar as before).
- **Buffer size, fd-cache held on** (default-buffer → 1MB-buffer): −0.41%, t ≈ −9.80 — a real, statistically clear *difference*, but in the wrong direction (1MB buffer is *slower*) and tiny in absolute terms (1.3 blk/s); most plausibly page-cache/allocation overhead from a 1MB `setvbuf` buffer per open handle outweighing any I/O-batching benefit at these small (~1.3–2KB) block sizes, not a real optimization opportunity.
- **Combined** (no-fdcache → 1MB-buffer): +0.67%, t ≈ 0.73 — not distinguishable from noise.

This closes §0 item 1's open question: post-Sapling heights behave the same as pre-Sapling did — the fd-cache mechanism works exactly as designed (99.9% hit rate, confirmed genuinely inactive in the off condition) but produces no measurable reindex throughput improvement, isolated from buffer size, at either pre- or post-Sapling heights. Disk I/O's remaining headroom (§2: ~25–26% of CPU post-Sapling) is dominated by genuine read/write/transfer time, not open/close overhead — consistent with §3's earlier `fs_usage` finding that open/close/stat together were only 6–34% of the disk-I/O bucket.

**A datadir-reset bug found and fixed while building the bootstrap-import benchmark leg.** `bench_matrix.sh`'s scratch-datadir reset originally used one procedure for both `-reindex` and `-loadblock` trials — rsync excluding only `chainstate`. Correct for `-reindex` (which rescans existing `blk*.dat`/`rev*.dat` by design), wrong for `-loadblock`: reusing a fully-synced source's `blocks/` directory made `-loadblock` reconcile its import against an already-populated, multi-million-block index instead of starting from an empty chain. Fixed: bootstrap-mode resets now also exclude `blocks/`. Before the fix, `LoadBlockIndexDB` reported an existing index spanning `heights=2440414...2484412` and RPC stayed in `"Loading block index..."` (`getblockcount` returning error -28) for over 50 minutes before any import progress was measurable; after the fix, RPC comes up and warmup height is reached within seconds.

**A narrow-blast-radius interruptibility gap found while diagnosing the above (pre-existing, upstream-inherited — not introduced by this work).** The stuck process couldn't be stopped by RPC `stop` (not up yet) or `SIGTERM` (no effect for 50+ minutes) — traced to `LoadBlockIndexDB`'s per-block accounting loop (the `BOOST_FOREACH` over `vSortedByHeight` building `nChainWork`/`nChainTx`/branch-ID data), which has exactly one `interruption_point()` call *before* the loop starts and none inside it. On a multi-million-block index this loop alone can run for tens of minutes with no way to interrupt it short of `SIGKILL`. Only reachable when reconciling a very large pre-existing index (not normal `-reindex`/`-loadblock` usage). `bench_matrix.sh` now bounds every wait loop to 10 minutes and escalates `SIGTERM` then `SIGKILL` automatically.

**Tooling:** `contrib/perf/bench_matrix.sh` — repeated-trial A/B harness for any `-perffdcache`/`-perfbufsize` combination, against `-reindex` and (given a `bootstrap.dat` path) `-loadblock`. See `contrib/perf/README.md` for usage.

**G6 (accepted queue):** when FDCACHE resumes, add **8192** and **16384** bufsize conditions vs libc default and 1048576 -- 1MB already looked slightly worse; mid-size buffers test the "syscall vs cache pressure" hypothesis without assuming 1MB is optimal.

---

## 4. The Merkle-root latch

**The confirmed inefficiency.** `IncrementalMerkleTree::root()` recomputes fully from `left`/`right`/`parents` on every call — a real `Hash::combine()` → `librustzcash_merkle_hash` FFI call per populated tree level. `ConnectBlock` calls `sapling_tree.root()`/`sprout_tree.root()` **twice per block, unconditionally**: once inside `PushAnchor`→`AbstractPushAnchor`, once directly — computing the identical value both times whenever nothing mutated the tree in between.

**Fix:** a `mutable boost::optional<Hash> cached_root` latch on `IncrementalMerkleTree`, populated on first `root()` call, cleared in the only two places that mutate tree state (`append()`, post-deserialize). Pure memoization of a deterministic function of existing state — no change to what's hashed, so no consensus or serialization-format risk.

**Why it helps `ConnectBlock` but not `HaveShieldedRequirements` — value vs. reference.** `AbstractPushAnchor` takes `tree` by const reference, so `ConnectBlock`'s two calls operate on the same object — the first populates the latch, the second matches it. `CCoinsViewCache::HaveShieldedRequirements`, which validates each Sprout joinsplit's anchor, declares its tree **by value, freshly, inside the per-joinsplit loop** — a brand-new object every iteration, mutated once and read once before going out of scope. There is structurally no second read on the same object for the latch to ever serve — every call here is a guaranteed no-match, regardless of implementation.

**Validation.** Existing gtest suite passes unmodified; a new test (`merkletree.RootCacheConsistency`) exercises match/no-match behavior across append and serialize/deserialize round-trips; full regression (Boost `test_bitcoin` 284/284, `zero-gtest` 206/206) clean, with a pre-existing unrelated wallet-key test flake (~1-in-9 runs, present on the unmodified baseline too) ruled out as false attribution. The instrumentation (`libzcash::MerkleRootCacheStats`) is `#ifdef ZERO_PERF`-gated and confirmed to leave zero trace in a normal build via `nm`; full regression on that clean build (Boost 284/284, gtest 207/207) shows no regressions from the removal.

**Measured impact: correct, but flat.** Re-profiled with the same methodology: Sapling-tree bucket 57.9% vs. the pre-fix 58.0% baseline — no measurable change, despite the latch being demonstrably active. Ground-truth per-block counters (since removed, superseded by coarser periodic logging) explain why:

| Block category | avg `root()` calls/block | match rate |
|---|---|---|
| Idle (no shielded activity) | 5.00 | **100%** |
| Sapling outputs only | 5.00 | 80% |
| Sprout joinsplits only | 8.28 | 48.3% |
| Both | 8.22 | 36.4% |

Idle and Sapling-output-only blocks match perfectly but were already cheap (empty/near-empty tree). **Sprout joinsplits drive both the extra call volume and the low match rate**, since each joinsplit's anchor is checked via `HaveShieldedRequirements`'s fresh-object pattern — structurally unmatchable. Sapling spends never call `.append()`/`.root()` in that function, so they were never a candidate for this latch either way. **Conclusion: the latch is correct and removes a real, confirmed redundancy, but that redundancy was a small, cheap-skewed slice of the bucket.** The bucket's real cost is (a) genuinely new `append()`/`combine()` work proportional to shielded-output volume — unavoidable — and (b) Sprout-joinsplit anchor validation's fresh-object-per-joinsplit pattern, which no per-object latch can help by construction.

**Latch vs. cache — checked against Zebra directly, not assumed.** Zebra's own Sprout tree type uses the identical single-slot latch pattern (`cached_root: RwLock<Option<Root>>`, cleared on `append()`), confirming a keyed cache isn't the standard answer here either. The real difference: Zebra's Sapling/Orchard anchor validation never constructs a tree object during validation at all — it checks anchor membership against a `HashSet`/RocksDB key-existence check, populated once at commit time — a *different technique* (a membership index over previously-seen roots), not a bigger cache. Zebra's Sprout path still pays the same construct/append/read cost for **chained joinsplits within one transaction** as Zero does, by its own source's admission ("this check is expensive, because it updates a note commitment tree for each sprout JoinSplit"). **So a keyed/multi-entry cache would not have helped `HaveShieldedRequirements` either** — the actual problem isn't insufficient memoization, since Zebra hits the identical wall despite a mature, independent implementation. The membership-index technique is the concrete lead for further work, not a bigger latch.

**Implemented then undone: membership-index `Have*AnchorAt` (§0 item 3).** Zebra-style existence checks (`db.Exists` on the root key, no tree deserialize) were added through the `CCoinsView` chain and wired into `HaveShieldedRequirements` for single-JoinSplit / Sapling-spend cases. Expected win: skip tree loads in the small tree/anchor CPU bucket. **Never measured as a throughput win.** Wiring into `HaveShieldedRequirements` broke ATMP: that path calls the check under tip/mempool, then `SetBackend(dummy)`, then checks again -- `Get*AnchorAt` warms the cache for the second call; existence-only `Have*` does not, so dummy => reject (`JoinSplit requirements not met`). **Removed the `Have*AnchorAt` API** (no caller left that needed it). `HaveShieldedRequirements` stays on `Get*`. Regression: `coins_tests/shielded_survive_dummy`. Revisit only with a non-ATMP caller and a measured win; do not re-plumb into `HaveShieldedRequirements` without that test.

---

## 5. Equihash's CPU share: a libsodium/ARM gap, not an algorithm issue

**The question.** §2 showed Equihash verification taking 6–28% of CPU depending on height, with `blake2b_compress_ref` recurring in every sample. Given Equihash verification is supposed to be cheap by design (asymmetric proof-of-work), is this a real inefficiency? **Answer: the algorithm is correct and minimal; the cost is a missing SIMD backend, specific to this build's architecture.**

**The algorithm itself is correct and lightweight.** `Equihash<N,K>::IsValidSolution` does exactly what the spec requires for mainnet's `Equihash<192,7>`: `2^K = 128` calls to `GenerateHash` (one blake2b invocation each), followed by a 7-round collision/ordering/distinctness check using only `memcmp`/XOR-style comparisons — no re-solving, no search, no redundant hashing. There is no algorithmic bug here.

**The cost is entirely inside blake2b's compression function, running unaccelerated on this hardware.** Every one of the 128 per-block hash calls goes through libsodium (not the Rust `blake2-rfc` crate also vendored in this tree — that's for something else). libsodium 1.0.21 dispatches its blake2b compression function at runtime via `blake2b_pick_best_implementation()`, choosing between `avx2`/`sse41`/`ssse3`/`ref` backends — but **all three accelerated backends are gated behind x86-only intrinsics headers**. On `aarch64-apple-darwin` (Apple Silicon), none of those headers exist, so the dispatcher unconditionally falls through to `blake2b_compress_ref`, the plain scalar C implementation, for every call.

**Checked and ruled out: no fix via upgrading dependencies or Apple's native crypto.** libsodium has released twice since 1.0.21 (1.0.22, 2026-04-09, current) — its actual `ChangeLog` shows post-quantum KEMs and new SHA-3 APIs, no mention of blake2b/NEON/ARM anywhere. Across every release checked (1.0.18–1.0.22), ARM/aarch64 wins landed for AES-GCM, AEGIS, and Argon2/SHA3 — blake2b has never once been included; a version bump is confirmed not to fix this. Apple's CryptoKit has no BLAKE2b support at all (SHA-2/AES/legacy only).

**A real, actively-maintained implementation to integrate from, if pursued.** The official reference repo `BLAKE2/BLAKE2` ships a `neon/` directory with `blake2b-neon.c` implementing BLAKE2b via ARM NEON/ASIMD intrinsics, plus a dedicated `Aarch64` makefile — and its most recent commit (2023) was a correctness fix by `veorq`, one of the two original BLAKE2 authors. Not stale or abandoned code. Integration would mean vendoring this implementation and wiring it in as a replacement compress function for this call path (either patched into the vendored libsodium build, or called directly from `equihash.cpp`, bypassing libsodium's generichash API for this one use site). Not yet scoped past confirming the file exists and targets the right architecture — actual integration effort (API fit, licensing, correctness validation against known-answer vectors) hasn't been assessed (§0 item 1).

**Independent confirmation this is a fixed, hardware-level cost, not something content-dependent:** Equihash's per-block cost held constant at 0.252ms ± 1.2% CV across six capture windows spanning pre- and post-Sapling heights and blocks/sec ranging 237–1,103 (§2's per-block table) — versus 21–46% CV for every other bucket, all of which scale with shielded-tx volume or block size. A cost that doesn't move with any chain-content variable is exactly what "fixed per-header hashing cost, paid by an unaccelerated compression function" predicts.

---

## 6. Sapling Groth16 batch-verification headroom: scoped, not implemented

**Reviewers:** start at §0.0 **Review packet** and §0.1a; this section is the evidence trail (call path, crate facts, ecosystem). Decision is open -- nothing here chooses A vs B.

**The question (§0 item 4).** §2 found Sapling Groth16 proof verification dominating post-Sapling CPU (48–55% chain-wide). Does `bellman` (Zero's pinned `librustzcash` Groth16 implementation) support batch verification, and could that work run on the currently-idle `zcash-scriptch` threads?

**Confirmed: every proof is verified independently, on one thread, with no batching anywhere in the call chain.** `bellman::groth16::verifier::verify_proof` (`bellman/src/groth16/verifier.rs`, pinned via `librustzcash` commit `06da3b9ac8f278e5d4ae13088cf0a4c03d2c13f5`, fetched fresh from upstream since the depends cache only stores the built `.a`/`.h`, not source) takes exactly one `Proof`/one set of public inputs and does one 3-pairing Miller loop + one final exponentiation — no loop, no batch parameter, no alternate entry point. `librustzcash_sapling_check_spend`/`_check_output` (`librustzcash/src/rustzcash.rs`) each wrap a single `verify_proof` call and are invoked once per `SpendDescription`/`OutputDescription`, from `ContextualCheckTransaction` (`main.cpp`), which `ContextualCheckBlock` calls via a plain `BOOST_FOREACH` over `block.vtx` — sequential, single-threaded, on the same worker thread that does everything else during reindex (`zcash-loadblk`). This confirmed the "structural, not fundamental" framing from §0: `ContextualCheckInputs`' `CScriptCheck`/`scriptcheckqueue` dispatch (the thing that actually wakes `zcash-scriptch` threads) covers *only* transparent script/signature verification and is wired up entirely separately from, and after, `ContextualCheckBlock`'s Groth16 checks — the two paths never share a queue, so idle `zcash-scriptch` threads structurally cannot pick up Groth16 work without new wiring, not because of any inherent limitation in the proof system.

**Confirmed: real batch-verification support exists, but only in a materially newer `bellman`.** The maintained successor `zkcrypto/bellman` (the pinned `ebfull/bellman` is ~2019-vintage; `zkcrypto/bellman` is its modern continuation) ships `groth16/src/verifier/batch.rs` plus a `groth16/benches/batch.rs` benchmark — a real, tested feature, not a proposal. It implements the standard random-linear-combination technique: for N proofs sharing one `VerifyingKey`, draw a random scalar `z_i` per proof, fold each proof's `(A, B, C)` terms and public inputs into running accumulators weighted by `z_i`, then do **one multi-Miller-loop + one final exponentiation for the whole batch** instead of N independent ones — collapsing the batch's expensive final-exponentiation count from O(N) to O(1). A `verify_multicore` variant additionally shards the batch into `rayon` `par_chunks(8)` work-items, run over `rayon`'s global threadpool, then reduces the partial Miller-loop results — real, existing parallel-execution code, not something to build from scratch.

**But this is not a drop-in upgrade.** Modern `bellman`'s `groth16` crate requires `edition = "2021"`, `rust-version = "1.60"`, and depends on `ff 0.13`/`group 0.13`/`pairing 0.23`/`bls12_381 0.8` — all from the post-2020 `ff`/`group` trait-split redesign of the Rust pairing-crypto ecosystem. The pinned crate stack (`pairing 0.14.2`, path-dependency, `rand 0.4`, no `ff`/`group` split at all) predates that redesign entirely. Adopting `zkcrypto/bellman`'s `batch.rs` as-is would mean migrating Zero's entire `librustzcash`/`bellman`/`pairing`/`jubjub` stack across that ecosystem-wide API break — a large, separate undertaking, not a small patch.

**The good news: the core primitive the algorithm needs already exists in the pinned crate, so a hand-ported batch verifier is feasible without that migration.** The pinned `pairing::Engine` trait (`pairing/src/lib.rs`) already defines `miller_loop<I>(i: I) -> Fqk` accepting an arbitrary-length iterator of `(G1Affine::Prepared, G2Affine::Prepared)` pairs — `verify_proof` itself already calls it with 3 pairs per single-proof check. `CurveAffine::prepare()`/`::Prepared` are likewise already present. This means the random-linear-combination batching math (accumulate weighted terms across N proofs, feed them all into one `miller_loop` call, one `final_exponentiation`) can be hand-ported into the pinned `bellman`/`pairing` version without a crate upgrade — the trait shapes line up. What pinned `bellman` lacks and would need adding: the accumulator/random-scalar bookkeeping itself (straightforward to port from `batch.rs`'s logic), and — for the multicore variant specifically — a parallel-execution primitive, since `rayon` isn't in the pinned crate's dependencies (`futures-cpupool`/`crossbeam`/`num_cpus` are present but used only by the *prover*, e.g. FFT/multi-exponentiation in `prover.rs`, never the verifier).

**What this changes for a real implementation, beyond the crypto:**
- **Batching requires buffering proofs before verifying them**, which doesn't fit `ContextualCheckTransaction`'s current per-transaction, immediate-verify-or-reject control flow (`ContextualCheckBlock`'s `BOOST_FOREACH` calls it once per tx and expects an immediate pass/fail). A batched version would need to collect all of a block's Sapling spend/output proofs first, verify the batch once, and only then be able to say a proof failed — with the caveat noted in `zkcrypto`'s own doc-comment: batch verification confirms *all* proofs are valid but "loses the ability to easily pinpoint failing proofs," so a failed batch needs a fallback to per-proof `verify_single` to identify which transaction to reject (already provided for exactly this purpose by `Item::verify_single` in `batch.rs`).
- **The random verifier scalars need a CSPRNG**, sourced per block (or per batch) — a new input this call path doesn't currently have.
- **Consensus-criticality**: unlike §3/§4's fixes (pure memoization, no change to what's computed), swapping single-proof verification for batch verification changes the exact sequence of cryptographic operations performed to reach a pass/fail — this needs the same scrutiny consensus-code changes always require, even though the math is a standard, published technique (not novel here).

**Not started, deliberately scoped no further than this.** Per §0 item 4, this was a research/scoping task, not an implementation. Estimated headroom: collapsing N final-exponentiations to 1 per batch, against a bucket that's 48–55% of chain-wide CPU (§2), is a substantial, structurally-supported target — but realizing it requires (a) hand-porting the batch algorithm using the pinned crate's existing `miller_loop` primitive, (b) restructuring `ContextualCheckBlock`'s per-tx control flow to buffer-then-batch-verify, and (c) deciding whether to also port a parallel accumulation path (would need vendoring a `rayon`-equivalent, or reusing the existing `futures-cpupool`/`crossbeam` machinery `prover.rs` already depends on) to actually engage otherwise-idle cores. None of this is started.

### 6.1 Ecosystem check: is there a more advanced, already-shipped batch verifier? Yes — and it changes the picture.

**The question.** §6 above frames the work as "hand-port `zkcrypto/bellman`'s `batch.rs`." Before committing to that path, this subsection checked: is the pinned `librustzcash` (Oct 2018) actually the latest available, or has the ecosystem moved further — and if so, does upstream already ship a *complete* batch verifier (not just the low-level pairing primitive), that a hand-port would be reinventing?

**Finding: the ecosystem has moved substantially, and `zcash/librustzcash`'s current `main` no longer contains `bellman`/`pairing`/`sapling-crypto` at all.** Fetched `zcash/librustzcash`'s current `main` (commit `1c7f7d86`, 2026-07-09 — actively maintained, pushed same day as this check). Its workspace (`Cargo.toml`) no longer includes `bellman`, `pairing`, `sapling-crypto`, or `librustzcash` (the FFI crate itself) as members at all — these have been split out into independently-versioned, separately-published crates: `bellman = "0.14"` (crates.io, last published 2023-03-20, `zkcrypto/bellman`'s modern continuation — the same repo §6 above already investigated) and `sapling = { package = "sapling-crypto", version = "0.7" }` (crates.io, `zcash/sapling-crypto`, last released 2026-04-21). The 2018-era all-in-one monorepo layout this repo's pin (`06da3b9ac8f278e5d4ae13088cf0a4c03d2c13f5`) reflects is not how the ecosystem is structured today — it's a snapshot from a much earlier point in a since-heavily-refactored dependency graph.

**Bigger finding: `sapling-crypto` already ships a complete, production Sapling `BatchValidator` — not just the low-level pairing primitive `batch.rs` provides.** Fetched `zcash/sapling-crypto` at its current release (`v0.7.0`) and read `src/verifier/batch.rs` in full. `sapling_crypto::BatchValidator` (traces back to `zcash_proofs::sapling::BatchValidator`, added in `zcash_proofs` v0.7.1, **2022-07-05** — this has been in production for roughly four years) does everything §6/§9.4's plan set out to hand-build:
- `check_bundle(bundle, sighash)` — walks a Sapling transaction bundle's spends and outputs, runs the *same* per-item consensus checks the pinned `check_spend`/`check_output` do (small-order checks, anchor/nullifier handling), but **queues** the Groth16 proof and the RedJubjub `spend_auth_sig`/binding signature into batch verifiers instead of checking them immediately — `self.spend_proofs.queue(...)`, `self.output_proofs.queue(...)`, `self.signatures.queue(...)`.
- `validate(spend_vk, output_vk, rng)` — batch-verifies everything queued: signatures first (`redjubjub::batch::Verifier`), then Sapling spend proofs and output proofs each via `groth16::batch::Verifier::verify`/`verify_multicore` (the exact `bellman` `batch.rs` code §6 already found) — three separate batches, not one combined batch, each against its own verifying key.
- **This batches signatures too, not just Groth16 proofs** — something §6/§9.4's plan didn't scope, since the pinned FFI's `check_spend` verifies `spend_auth_sig` eagerly per-call (§9.4 Phase 0 finding). Batch-verifying RedJubjub signatures is a separate, real technique (also random-linear-combination-based) with its own headroom, orthogonal to Groth16 batching.
- Returns a single pass/fail for the whole batch, with the same "can't pinpoint which proof failed" limitation `batch.rs` itself documents — callers needing attribution re-verify individually, same tradeoff §9.4's Phase 4 fallback design already anticipated.

**Confirmed in real production use, not experimental:** `sapling_crypto::BatchValidator` is used directly by Zebra (Zcash Foundation's Rust full node) in `zebra-consensus/src/primitives/sapling.rs`, wrapped in a `tower_batch_control::Batch` async service (`zebra-consensus/src/primitives.rs`) with real, tuned production parameters: **`MAX_BATCH_SIZE = 64`, `MAX_BATCH_LATENCY = 100ms`** — i.e. Zebra batches up to 64 Sapling proofs or waits at most 100ms, whichever comes first, before flushing a batch through `BatchValidator::validate`. This is the answer to "how big should a batch be" that §9.4's plan left unspecified — a real, shipped, presumably-tuned answer, not a guess.

**What this means for §9.4's plan.** Two paths now exist, and they trade off differently:

1. **Hand-port** (§9.4 as written): port only the random-linear-combination math into the *pinned* 2018-era `bellman`/`pairing`, keeping Zero's entire crate stack otherwise unchanged. Smaller footprint, no crate-version migration, but reinvents logic that upstream has already built, hardened, and run in production for ~4 years — including the signature-batching piece §9.4 didn't originally scope at all.
2. **Adopt `sapling-crypto` directly** (not previously considered): migrate Zero's Sapling verification call path to depend on the current, maintained `sapling-crypto`/`bellman 0.14`/`bls12_381`/`group`/`ff`-split crate stack, and call `BatchValidator` as-is — the same code Zebra runs today. Larger footprint (the crate-stack migration §6 above already flagged as "a large, separate undertaking"), but gets a battle-tested implementation, signature batching for free, and a real precedent for batch-size tuning (`MAX_BATCH_SIZE`/`MAX_BATCH_LATENCY`), instead of hand-porting and re-validating logic that already exists.

**This is a genuine fork in the road that should be decided before Phase 2 of §9.4 proceeds** — not resolved here. The hand-port path is still valid and its Phase 0–1 groundwork (already executed — see §9.4) isn't wasted (the math is the math either way, and the standalone prototype validated it works against real proofs), but "reuse the upstream crate that Zebra already runs in production" is a materially different, and arguably lower-total-risk, option that wasn't on the table when §6/§9.4 were originally scoped. Not sized or investigated further here (crate-migration cost, C++/Rust FFI shape against the newer crate stack, and whether `librustzcash`'s current C FFI layer — if one still exists at this pin — could be reused rather than hand-rolled, are all open).

*Investigation steps, in order:*
1. Pull the exact pinned `librustzcash` commit (`06da3b9ac8f278e5d4ae13088cf0a4c03d2c13f5`) and read `verifier.rs` end to end; confirm `Proof`/`VerifyingKey`/`PreparedVerifyingKey` struct shapes match what `zkcrypto/bellman`'s `batch.rs` accumulator logic needs field-for-field — `batch.rs` was written against the post-split `ff 0.13`/`group 0.13`, the pinned crate predates that split entirely, so every type substitution needs individual checking, not just the top-level call signature.
2. Prototype the batch math as a standalone Rust unit, outside the FFI boundary first — a `#[cfg(test)]`-only batch-verify function against the pinned `bellman`/`pairing` crates, fed known-good and known-bad Groth16 proofs from the existing prover test fixtures. Validates the ported math against known-answer vectors before touching any FFI/consensus surface.
3. Design the FFI/buffering boundary before writing Rust: current `librustzcash_sapling_check_spend`/`_check_output` are eager, per-description, return `bool` immediately. Decide the batched shape — e.g. a defer/collect call plus a `librustzcash_sapling_batch_validate` call returning per-item pass/fail or an opaque failure index, vs. collecting proofs block-side in `main.cpp` and passing an array across one new FFI call.
4. Restructure `ContextualCheckBlock`'s control flow: collect all Sapling spend/output proofs across the block's transactions first, batch-verify once, and only on batch failure fall back to per-proof `verify_single` (already provided in `batch.rs` for exactly this) to identify which transaction/description to reject — the existing per-description error codes (`bad-txns-sapling-spend-description-invalid` etc., `main.cpp:1131,1146`) must still point at the correct tx for RPC/ban-scoring correctness.
5. Source the per-batch CSPRNG — a new input this call path doesn't have today; check `random.h`/existing `GetRandBytes`-equivalent usage elsewhere in `main.cpp` for the process's existing secure-RNG convention, sourced fresh per block (or per batch), never reused across batches.
6. Scope the consensus-safety review as its own step, separate from perf measurement: unlike §3/§4 (pure memoization, no change to what's computed), this changes the actual sequence of cryptographic operations used to reach pass/fail — get independent review of the ported math specifically, regardless of whether the perf win materializes.

*Test plan:*
1. Known-answer-vector tests in Rust, before FFI: feed the standalone prototype (investigation step 2) mixes of all-valid and one-invalid-among-N proof sets; assert batch accept/reject matches per-proof `verify_proof` exactly, across N = 1, 2, 8, 64.
2. New C++ gtest mirroring §4's `merkletree.RootCacheConsistency` precedent — exercise the new FFI entry point(s) directly with fixtures reused from `zcbenchmarks.cpp`'s existing Sapling spend/output benchmark inputs (`zcbenchmarks.cpp:706,739` already construct valid spend/output descriptions for benchmarking).
3. Adversarial/negative tests: corrupt one proof in a batch of N (bit-flip `zkproof`, wrong `anchor`, wrong `nullifier`); confirm the batch fails, then confirm the `verify_single` fallback correctly identifies *which* item — the specific property `zkcrypto`'s own doc-comment flags as the hard part of batching.
4. Full existing regression suite unchanged and clean: Boost `test_bitcoin` (284/284 baseline) and `zero-gtest` (205–207/207 baseline, 2 known pre-existing flakes) — same bar §4 was held to.
5. Real-chain differential test: `-reindex` over a real post-Sapling height range (reuse §2's already-sampled windows, e.g. 610,758–626,806 or 995,392–1,083,180) on both batched and unbatched binaries; diff resulting `chainstate`/best-block-hash — must be byte-identical. Strongest available correctness check since it's not synthetic.
6. Perf re-measurement with the existing tooling: same Instruments/`xctrace` methodology as §2 (`contrib/perf/capture_sequence.sh` + `decode_captures.py`), same height windows, for a directly comparable before/after Groth16-bucket percentage and ms/block figure; plus a `bench_matrix.sh`-style throughput A/B with the same statistical rigor (t-test, n≥4 trials) §3 used — §3's "implemented but no measurable win" outcome is a reminder not to skip this step.
7. If the multicore/parallel-accumulation variant is pursued: a separate throughput test varying `-par`/thread count, since the entire point there is engaging otherwise-idle `zcash-scriptch`-adjacent cores — measure scaling, not just single-thread speedup.

### 6.2 Cross-ecosystem status: who else has and has not adopted batch verification

**Question.** §6.1 found `sapling-crypto`'s `BatchValidator` and confirmed Zebra uses it. How widely has this actually propagated across the rest of the Zcash-descended node ecosystem — is Zero unusually behind, or is unbatched verification still the norm among comparable forks? Checked five real, currently-active repositories directly (fetched each fresh this session, not from memory).

| Project | Relationship to Zero | Status, `pushed_at` (fetched this session) | Sapling proof verification |
|---|---|---|---|
| **`zcash/zcash`** (`zcashd`) | Common ancestor — Zero and every fork below descend from this codebase | Active but **being sunset**: repo's own README declares `zcashd` deprecated, automatic end-of-life node halt estimated **2026-07-18 at block height 3,417,100** (~10 days out at the time of this check), migration path is to Zebra (full node) or Zallet (wallet-only) | **Batches.** `ContextualCheckShieldedInputs` calls `tx.GetSaplingBundle().QueueAuthValidation(*saplingAuth, dataToBeSigned)` per transaction (`main.cpp:1417-1425`) into one `rust::Box<sapling::BatchValidator>` created per block (`main.cpp:3306-3307`, gated on `fExpensiveChecks`), validated once after the whole block's tx loop (`main.cpp:3847`: `saplingAuth.value()->validate()`) |
| **Zebra** (`ZcashFoundation/zebra`) | Independent Rust reimplementation, not a zcashd fork, but the reference "modern" architecture | Active, primary recommended node going forward per `zcashd`'s own deprecation notice | **Batches**, confirmed in §6.1 — `zebra-consensus/src/primitives/sapling.rs` wraps `sapling_crypto::BatchValidator` in a `tower_batch_control::Batch` async service, `MAX_BATCH_SIZE=64`/`MAX_BATCH_LATENCY=100ms`. Also confirmed this session: Zebra's `Cargo.toml` enables `sapling-crypto`'s `"multicore"` feature — it runs the `rayon`-parallel `verify_multicore` path (§6), not just single-threaded batching |
| **Pirate Chain** (`PirateNetwork/pirate`) | zcashd fork, same lineage as Zero | Active, `pushed_at` within 1 day of this check | **Batches** — a real, complete port: maintains its own vendored `src/rust/` crate wrapping `sapling_proofs::BatchValidator` behind a `cxx` bridge (`src/rust/src/sapling.rs`, `src/rust/src/bridge.rs`), mirroring the modern `zcashd`/Zebra architecture rather than calling out to an external crate directly. Not a stray reference — real `init_batch_validator`/`validate` wiring matching the same shape as `zcashd`'s. **The one fork checked that has already done the work this investigation is scoping.** |
| **Komodo** (`KomodoPlatform/komodo`) | zcashd fork, same lineage as Zero | Active, `pushed_at` within 2 weeks of this check | **Unbatched** — still calls `librustzcash_sapling_check_spend` directly (`main.cpp:1328`), the same raw-C FFI, one-proof-at-a-time pattern Zero has today. Zero confirmed `BatchValidator` references anywhere in `src/` |
| **VerusCoin** (`VerusCoin/VerusCoin`) | zcashd fork, same lineage as Zero | Active, `pushed_at` within 1 week of this check | **Unbatched** — same `librustzcash_sapling_check_spend` call pattern (`main.cpp:1411`), zero `BatchValidator` references |
| **Ycash** (`ycashfoundation/ycash`) | zcashd fork, same lineage as Zero | Active, `pushed_at` within ~2 months of this check | **Unbatched** — same pattern (`main.cpp:1148`), zero `BatchValidator` references |

**Reading this table.** Batch verification is not a fringe or experimental idea in this ecosystem — it's the architecture of the two most-current, most-actively-developed implementations (`zcashd` itself, right up to its own end-of-life, and Zebra, its designated successor), and at least one structurally-comparable fork (Pirate Chain) has already done the exact migration Zero is scoping. But it is **not universal** — three other zcashd-lineage forks checked (Komodo, VerusCoin, Ycash) are all still on the same unbatched, per-proof `librustzcash_sapling_check_spend` pattern Zero has. **Zero is in the majority position among forks, not an outlier** — most zcashd descendants haven't done this migration either, which is useful context on how much fork-maintenance effort this realistically represents (it isn't something every fork picks up for free; Pirate Chain is the exception, not the rule).

**One architecturally significant difference found in `zcashd`'s current batch-failure handling, relevant to §9.4's Phase 4 design.** §9.4's fallback plan (Phase 4, item 16) was designed to preserve today's exact per-transaction error codes on batch failure, by falling back to per-proof `verify_single` to identify which transaction to reject. **Current `zcashd` does not do this.** Its `saplingAuth.value()->validate()` check at `main.cpp:3847-3851` rejects the *entire block* with one generic error (`"bad-sapling-bundle-authorization"`) on any batch failure — there is no per-transaction re-verification or attribution anywhere in this path. The code comment there references a real fixed security issue (`GHSA-g4x5-crjh-29ff`, about binding-signature check ordering relative to a chain-supply consistency check) but says nothing about per-tx attribution being a design goal at all. This means §9.4's fallback-for-attribution design is **more conservative than what upstream `zcashd` itself now ships** — not wrong, but worth an explicit decision: whether Zero's Phase 4 should match upstream's simpler whole-block-reject behavior (less code, matches the reference implementation's current consensus behavior) or keep the more careful per-tx-attributed fallback originally planned (more code, better error messages/ban-scoring granularity, matches Zero's *own* current single-proof behavior exactly). Not decided here.

**Doesn't change the hand-port-vs-adopt fork in the road from §6.1**, but adds real weight to it: the "adopt upstream" option now has two working reference implementations to study (current `zcashd`'s `cxx`-bridge integration and Pirate Chain's, which — as a same-lineage C++ fork — is the closest architectural precedent to what Zero would actually need to build, more so than Zebra's from-scratch Rust design).

---

## 7. Memory profiling: `AddToBlockIndex` dominates, Groth16 verification allocates nothing

**The question (§0's memory-profiling item).** Instruments' Allocations/Leaks templates attach successfully but produce a GUI-only proprietary blob with no `xctrace export` schema in this Instruments version (§2) — a documented dead end for headless use. `vmmap`/`heap`/`malloc_history` are CLI-native with no export-format dependency; this section is their first real use against a live `-reindex`.

**Method.** `vmmap -summary <pid>` gives `Physical footprint` at a point in time — used here to build a footprint-vs-height timeline via a small driver (`reindex-profile/memprofile/snapshot_at_heights.sh`) that polls `getblockcount` and snapshots at fixed height checkpoints. `heap <pid>` gives a live per-size-class allocation census, no special launch flags needed. `malloc_history <pid> -callTree` gives a full allocation-site call tree attributing every live allocation to the code path that made it — but only for allocations made *after* `MallocStackLogging=1` is set, so this needed a separate `-reindex` launched with that environment variable (real, non-trivial overhead: stack-logging is not something to leave on for a full multi-hour chain reindex, so this run was capped at a representative window rather than run to chain tip).

**Footprint grows with chain length, not unboundedly — no leak signature found — but `vmmap`'s headline `Physical footprint` number is confounded by macOS memory compression over a run this long, and a naive read of it tells a misleading story.** Full-chain sweep, six checkpoints from height 278,072 to chain tip (2,470,587, matching this repo's documented ~2.47M-block chain):

| Height | `Physical footprint` | `Writable regions: Total` (written address space) | Swapped/compressed |
|---|---|---|---|
| 278,072 | 535.3M | 702.0M | 0K (0%) |
| 500,436 | 956.1M | 1.1G | 0K (0%) |
| 901,000 | 1.6G | 1.7G | 1.2G (71%) |
| 1,500,605 | 2.4G | 3.5G | 73.6M (2%) |
| 2,001,804 | 2.9G | 4.2G | 315.5M (7%) |
| 2,470,587 | 3.1G | 4.7G | 1.8G (38%) |

**Reading `Physical footprint` alone produces a spurious "growth rate is slowing down" story: 1.94 → 1.74 → 1.40 → 1.05 → 0.45 KB/block across the five segments — a suspiciously clean monotonic decline that doesn't survive a second look.** `Physical footprint` nets out macOS's memory compressor, and the "swapped/compressed" column above shows *why* it can't be trusted alone here: compression kicks in unevenly (0% for the first two checkpoints, a spike to 71% at height 901,000, then 2–38% afterward) as system-wide memory pressure varies over this ~2-hour run — that's a fact about *this machine's other memory demand during the run*, not about `zerod`'s own allocation behavior. **`Writable regions: Total`** (the total address space actually written to, unaffected by whether pages are later compressed) tells a cleaner story: it grows from 702.0M to 4.7G, monotonically, at a much less dramatically-declining rate (1.83, 1.53, 3.07, 1.43, 1.09 KB/block — noisier, with one high-swap-affected segment reading anomalously high, but no clean downward trend). **Lesson for any future memory-profiling work here: use `Writable regions: Total`, not the headline `Physical footprint` figure, when comparing checkpoints spread over a long enough run for compression pressure to vary** — this is the same class of mistake §1's methodology repeatedly warns about (don't trust one source without cross-checking against a second).

**Net conclusion:** see Measures **M-MEM-VMMAP** / **M-MEM-GROWTH** / **M-MEM-ALLOC** / **M-MEM-PARAMS**. Memory grows roughly linearly with chain length (no leak signature), ~1–3KB/block Writable; `AddToBlockIndex` dominates retained heap; Groth16 verify allocates nothing on the heap.

**Allocation-site breakdown (`malloc_history -callTree`, 673-second stack-logged window spanning roughly height 20,198 → 501,321, i.e. crossing Sapling activation):** ~987MB total tracked allocation across the window, essentially all of it (896MB, >90%) under the single `ThreadImport` worker thread, confirming again (as in §1's profiling methodology) that this is where real work happens. Within that:

| Call path | Allocation | Share of `ThreadImport` |
|---|---|---|
| `AddToBlockIndex` (building the permanent `uint256`→`CBlockIndex*` block-index map + per-header metadata) | ~589MB | ~66% |
| `CCoinsViewCache::Flush`/`BatchWrite` (flushing coins/anchor/nullifier caches to the LevelDB-backed chainstate) | ~160MB+ (multiple call sites) | ~18%+ |
| `CCoinsViewCache::HaveShieldedRequirements` → `GetNullifier` (nullifier-set cache insertion) | ~37MB (main pass) + ~4.8MB (reprocessing pass) | ~4% |
| `CCoinsViewCache::HaveInputs`/`FetchCoins`/`GetCoins` (transparent UTXO cache population) | ~29.8MB + ~9.5MB | ~4% |

**`AddToBlockIndex` is the single largest identifiable allocation site — expected, not a bug.** It permanently retains one `CBlockIndex` object (plus a `vector<unsigned char>` for header-adjacent data and a hash-map entry) per block header for the lifetime of the process — by construction, chain-length-proportional, never freed, never meant to be. At ~589MB for roughly 480,000 headers in this window, that's on the order of ~1.2KB/header of permanent retained memory — consistent with `CBlockIndex`'s field set (hashes, work, heights, pointers) plus map/allocator overhead. Confirms this is the primary driver of the footprint-vs-height growth measured above, not a separate or surprising cost.

**Confirmed: Sapling Groth16 proof verification allocates essentially nothing on the heap.** Despite dominating CPU (48–55% of chain-wide CPU per §2) and this stack-logging window spanning well past Sapling activation, `librustzcash_sapling_check_spend`/`_check_output`/`verify_proof`/`miller_loop`/`final_exponentiation` appear **zero times** anywhere in the call tree. The only Groth16-adjacent allocation found at all is `librustzcash_init_zksnark_params` (~58MB, ~4.9MB, and a handful of smaller frames) — one-time proving/verifying-key loading at process startup, not a per-verification or per-block cost. This cleanly decouples §2's CPU-dominant bucket from the memory profile: BLS12-381 field/pairing arithmetic operates on fixed-size stack types, so verifying more proofs costs CPU time but not heap growth — a useful confirmation that Groth16 verification (and by extension, any future batch-verification work per §6) is not a memory-scaling concern, only a CPU one.

**Full-chain footprint timeline: complete.** The height-checkpoint sweep ran to chain tip (2,470,587); see the table above. Not done: re-running `malloc_history`/`MallocStackLogging` at a window sampled entirely post-Sapling-activation specifically — the stack-logged window above happens to straddle the Sapling activation boundary but is dominated by pre-activation volume by block count, so its allocation-site percentages likely understate Sapling-Groth16-adjacent bookkeeping (anchor cache writes, nullifier-set growth) relative to a window sampled entirely post-activation. Given §7's headline finding — Groth16 verification itself allocates nothing, and `AddToBlockIndex` (a cost with no Sapling-specific component at all) dominates — a second stack-logged window is unlikely to change the qualitative conclusion, so this is left as a documented gap rather than pursued further.

---

## 8. `AddToBlockIndex` per-block allocation detail, and two dead ends chased down

**Motivation.** §7 reported `AddToBlockIndex` as ~66% of tracked allocation and ~1.2KB/header, as an aggregate. This section breaks that aggregate into its actual per-call allocation sites (piece count, size, lifetime) using the same `malloc_history -callTree` raw data §7 summarized, and resolves two follow-up questions: what the `CBlockIndex` "Shieldex" stat fields cost and who uses them, and what was actually behind an unexplained large-average-size Rust allocator (`alloc::raw_vec::finish_grow`) visible in the raw trace.

### 8.1 `AddToBlockIndex` -- 4 heap allocations per block

Site: `main.cpp` around the `AddToBlockIndex` implementation used on the import path.

| # | Site (`main.cpp` offset) | What | Count (stack-logged window) | Avg size | Total | Lifetime |
|---|---|---|---|---|---|---|
| 1 | `+212`: `new CBlockIndex(block)` | the `CBlockIndex` object itself | 423,978 (≈1/block) | 344 bytes | 259M | **Permanent** — owned by `mapBlockIndex`, never freed for the life of the process |
| 2 | `+432`: `nSolution = block.nSolution` (in the `CBlockIndex(const CBlockHeader&)` ctor) | Equihash solution bytes, `vector<unsigned char>` copy | 423,978 | 448 bytes | 181M | Permanent — lives inside the `CBlockIndex` from (1) |
| 3 | `+476`: `mapBlockIndex.insert(make_pair(hash, pindexNew))` | one node in `boost::unordered_map<uint256, CBlockIndex*, BlockHasher>` (`main.h:136`) | 423,978 | 64 bytes | 25.9M (+ occasional 6M/1.5M rehash bucket-array grows) | Permanent — the map is never cleared |
| 4 | `+996`: `setDirtyBlockIndex.insert(pindexNew)` | one node in `std::set<CBlockIndex*>` (`main.cpp:252`) | 423,978 | 48 bytes | 19.4M | **Transient** — cleared each time the dirty set flushes to `CBlockTreeDB` (periodic, not per-block) |

**Per block, steady state: 4 allocations, ~904 bytes**, of which ~856 bytes/block (~95%) is **permanently retained** (the `CBlockIndex` object + its embedded Equihash-solution vector + the map entry) and ~48 bytes/block is transient, reclaimed on the next dirty-set flush. This is the mechanism behind §7's measured ~1.2KB/header figure (the gap between 904 raw bytes and ~1.2KB is allocator bucket-size rounding — confirmed against `heap`'s own size-class histogram, which shows no exact 904-byte class, the nearest classes being 896 and larger).

Other per-block-scaling (but not literally-every-block; these fire per shielded-tx / per-flush-cycle rather than unconditionally) allocation sites in the same window, for reference: `CCoinsViewCache::BatchWrite`'s `BatchWriteAnchors` (Sprout tree snapshots, ~695 bytes/entry, 104M total) and its Sapling counterpart (~434 bytes/entry, ~1.4M total), nullifier-cache-entry insertion (~64 bytes/entry, ~35M total across three call sites), and UTXO-cache-entry insertion (~96 bytes/entry, ~20M total). All four are **transient** — evicted from the in-memory `CCoinsViewCache` on the next flush to the LevelDB-backed chainstate, not permanently retained the way `AddToBlockIndex`'s output is. This confirms §7's growth-driver finding at the individual-allocation-site level: only `AddToBlockIndex` explains the linear, unbounded-by-flush-cycle chain-length-proportional growth curve — the cache-write churn is real but bounded.

### 8.2 The "Shieldex" fields in `CBlockIndex`: reviewed, mostly gated correctly, one dead field found

**What they are.** `CBlockIndex` (`chain.h:164–338`) carries two parallel groups of `int64_t` fields beyond stock zcashd's layout — one set of 11 per-block counters (`nPayments`, `nShieldedTx`, `nShieldedOutputs`, `nFullyShieldedTx`, `nShieldingPayments`, `nShieldedPayments`, `nFullyShieldedPayments`, `nDeshieldingTx`, `nDeshieldingPayments`, `nShieldingTx`, `nNotarizations`) and a matching set of 11 `nChain*`-prefixed cumulative-from-genesis counters. Populated in `ReceivedBlockTransactions` (`main.cpp:4005–4165`): the per-block counters are computed once per block by walking `block.vtx` and classifying each transaction by shielded-input/output shape (fully-shielded `z→z`, shielding `t→z`, deshielding `z→t`, etc. — see the heuristic and its own documented caveats at `main.cpp:4043–4105`, which acknowledges this is a best-effort classification, not exact); the `nChain*` counters are running sums, each computed as `pprev->nChain* + this->n*` while walking newly-connectable blocks (`main.cpp:4150–4160`).

**Real consumer confirmed: `getblockchaininfo`-adjacent RPC (`src/rpc/blockchain.cpp`).** `nChainShieldedTx`, `nChainNotarizations`, and the rest feed an RPC endpoint whose own help text says it "will return a large amount of additional data if the shielded index (zindex) is enabled" (`rpc/blockchain.cpp:1238`) — computing shielded-tx rate, shielding/deshielding/fully-shielded percentages, and an "organic" (non-notarization) tx-rate estimate over a time window (`rpc/blockchain.cpp:1337–1424`). Not dead code, not speculative — a real, used feature.

**Correctly gated on disk, not gated in memory.** Population is conditional (`if (!fZindex) continue;` at `main.cpp:4036`, and the `nChain*` rollup is behind its own `if (fZindex)` at `main.cpp:4147`), and **disk serialization is correctly gated too** (`chain.h:582–594`: `if ((s.GetType() & SER_DISK) && fZindex) { READWRITE(nShieldedTx); ... }` — all 11 per-block fields, comment-flagged "Order is important!"). `fZindex` defaults to `false` (`DEFAULT_SHIELDEDINDEX`, `main.h:115`; confirmed via `init.cpp:391`'s help text, `default: 0`) — most nodes never populate or serialize these. **But the struct layout itself is unconditional**: all 22 `int64_t` fields (11 + 11 `nChain*`) exist in every `CBlockIndex` instance in RAM regardless of `-zindex`, costing ~176 bytes/block of always-present, usually-always-zero memory chain-wide (~176 bytes × 2.47M blocks ≈ 435MB at chain tip) — folded into but not separately broken out in §8.1's 344-byte average `CBlockIndex` size above. This is a real, quantifiable cost of having the feature compiled in, paid by every node whether or not `-zindex` is ever turned on; not a bug, but worth knowing if `CBlockIndex`'s in-memory footprint is ever a target (it is the single largest identified allocation site chain-wide per §7).

**One dead field found: `nNotarizations`.** Declared, zero-initialized, summed chain-wide into `nChainNotarizations`, exposed via RPC (`rpc/blockchain.cpp:1337,1365`) — but the only code that would ever increment it is a commented-out heuristic (`main.cpp:4044–4049`, with its own inline `TODO` about false-positive risk). It has stayed `0` for the life of this field. Not a correctness bug (RPC will just always report `notarizations: 0`/rate `0`), but it's dead weight: 8 bytes/block in `CBlockIndex` (16 with its `nChain*` counterpart) plus a disk-serialized field when `-zindex` is on, for a value that can never be anything but zero. Worth either implementing the heuristic for real or removing the field — currently neither.

**Not investigated further (out of scope here): whether shrinking `CBlockIndex`'s in-memory footprint — e.g. gating the Shieldex fields out of the struct entirely behind a compile-time or even runtime flag, rather than just gating their population/serialization — is worth pursuing.** Given `AddToBlockIndex` is §7's largest single allocation site and these fields are ~50% of the non-Equihash-solution portion of the object (176 of ~344 bytes), this is a plausible follow-up memory-focused optimization target, but sizing the actual win and the runtime-flag-vs-recompile tradeoff hasn't been done.

### 8.3 `alloc::raw_vec::finish_grow`: resolved — startup-only Groth16 parameter loading, not a per-block cost

**The question.** A prior pass over the raw `malloc_history` trace flagged `alloc::raw_vec::finish_grow` (Rust's generic `Vec` growth-reallocation routine) as the largest average-allocation-size symbol in the whole trace (reported as "1,062 count, 62.9KB avg, 66.8M total"), with "unidentified specific caller" — `finish_grow` is a single generic-monomorphized-but-symbol-collapsed function, so a flat grep across the trace merges every distinct call site that ever reallocates a growing `Vec` into one apparent hot spot.

**Resolution: not one caller — re-attributing each `finish_grow` occurrence to its actual immediate caller in the trace splits it cleanly.**

| Caller | Count | Total bytes | What it is |
|---|---|---|---|
| `bellman::groth16::Parameters<E>::read` | 12 | 62.91M | Deserializing the Sapling proving/verifying-key file |
| `sapling_crypto::jubjub::JubjubBls12::new` | 1,678 | 0.88M | Jubjub curve parameter-table construction |
| `pairing::bls12_381::ec::g2::G2Affine::prepare` | 6 | 0.28M | Precomputing a G2 point for pairing |
| (two single-allocation call sites, <1K each) | 2 | ~0.001M | — |

**The 62.9MB is `librustzcash_init_zksnark_params`, called exactly once at process startup (`init.cpp:790`), not inside the reindex loop.** This matches and reinforces §7's existing finding almost exactly — §7 had already identified `librustzcash_init_zksnark_params` as "~58MB, ~4.9MB, and a handful of smaller frames," one-time key loading, not a per-verification cost. The `finish_grow` figure is the same allocation, seen from one layer deeper in the call stack (the generic realloc routine `Parameters::read` calls into while growing its buffers to hold the ~50MB Sapling parameter file), not a separate or previously-unaccounted-for cost. **No new finding here — confirms §7's conclusion via independent attribution, closes the "unidentified caller" open question from the previous per-block-allocation pass.**

### 8.4 "So many allocations and indexes — all used in every scenario?"

Reviewed which of §7/§8's allocators are conditional on runtime flags vs. always active:

- **`CCoinsViewCache`'s coins/nullifier/anchor caches (`cacheCoins`, anchor maps, nullifier maps in `coins.h`) are unconditional** — always instantiated, not gated by wallet, `-txindex`, `-prune`, or `-zindex`. This is correct, not bloat: UTXO/nullifier/anchor tracking is required by consensus validation itself for every node, including pruned ones (pruning discards old block *files* after validation, not the validation-time working set).
- **`fTxIndex` defaults to `true`** (`main.cpp:83`) — the transaction index is on by default, unlike `-zindex`.
- **`fZindex` defaults to `false`** (`DEFAULT_SHIELDEDINDEX`, `main.h:115`) — its *disk* and *population* costs are correctly opt-in, but per §8.2 its *in-memory struct layout* cost is not: every node pays ~176 bytes/block for fields most nodes never populate.
- **`AddToBlockIndex`'s core allocations (§8.1, items 1–3) are unconditional and unavoidable for any full validation** (reindex, normal sync, or otherwise) — there is no flag that turns off block-index tracking; it's the mechanism the whole chainstate is built on.

Net: the allocation pattern isn't over-built for a hypothetical scenario — most of it is genuinely load-bearing for every node. The one confirmed gap is §8.2's Shieldex struct-layout cost, paid unconditionally despite being conditionally *used*.

---

## 9. Status review and recommended path forward: NEON blake2b and Groth16 batching

**Purpose.** §5 and §6 each scoped a large-headroom optimization but stopped short of a recommendation on *how* to actually advance the work with controlled risk. This section reviews where each stands and lays out a staged approach for both — sized to be interruptible and individually validated at each stage, rather than a single big-bang patch.

### 9.1 Status snapshot

| | Equihash/NEON (§5) | Groth16 batching (§6) |
|---|---|---|
| CPU share | 6–12% chain-wide, but 100% fixed-per-block cost (0.252ms ± 1.2% CV) | 48–55% chain-wide, scales with shielded-tx volume |
| Root cause confirmed | Yes — libsodium has no ARM/NEON blake2b backend, falls to scalar `blake2b_compress_ref` | Yes — no batching anywhere in the pinned `bellman`/`librustzcash` call chain |
| Fix exists upstream | Yes — `BLAKE2/BLAKE2`'s `neon/` (maintained, 2023 commit) | Yes — `zkcrypto/bellman`'s `batch.rs`, but written against a newer, incompatible crate generation |
| Portable without a larger migration? | Yes, in principle — but the actual call site goes through libsodium's `crypto_generichash_blake2b_*` API (`equihash.cpp:43,56,58`), not a raw compress call | Yes — pinned `pairing::Engine::miller_loop` already accepts the arbitrary-length iterator the batch math needs |
| Consensus-critical? | **No** — Equihash verification is proof-of-work validation, not a state-transition; a faster/slower hash implementation changes timing, not consensus outcomes, as long as it's bit-identical to the reference algorithm | **Yes** — changes the actual sequence of cryptographic operations used to reach a shielded-tx pass/fail |
| Blast radius of a bug | A wrong hash silently rejects valid blocks or accepts invalid ones — bad, but detectable immediately (chain halts or forks against every other node) | A wrong batch-verify could accept an invalid Sapling proof — a much worse, harder-to-detect failure mode (a false spend/output could be silently accepted) |
| Implementation status | Not started past confirming the upstream file exists | Not started past scoping + the investigation/test plan in §6 |

**The asymmetry that should drive sequencing:** NEON blake2b is lower CPU payoff but far lower risk and validates against a public, static known-answer-vector test suite (RFC 7693's official BLAKE2b test vectors) — correctness is binary and checkable in isolation, with no chain-state or consensus dependency. Groth16 batching is much higher payoff but consensus-critical, and its correctness can only really be validated by running it against real chain data end-to-end. **Recommendation: do NEON first.** It's a smaller, fully self-contained project that also exercises the same "vendor a maintained upstream implementation into this build" muscle the Groth16 work will need later (dependency vendoring, cross-compilation for `aarch64-apple-darwin`, correctness-test harness) — cheap practice for a higher-stakes change.

### 9.2 Recommended path: NEON blake2b

**Constraint the integration point must satisfy, confirmed from source:** `src/crypto/equihash.cpp` doesn't call a raw `blake2b_compress` function — it calls libsodium's stateful streaming API directly: `crypto_generichash_blake2b_init_salt_personal` (`equihash.cpp:43`), `crypto_generichash_blake2b_update` (`equihash.cpp:56`), `crypto_generichash_blake2b_final` (`equihash.cpp:58`), with a personalization block for Equihash's per-block domain separation. Any fix has to either (a) make libsodium's own dispatcher pick a NEON compression backend, or (b) bypass libsodium's generichash API at this call site entirely and call a NEON implementation directly, keeping libsodium for every other use in the codebase (`crypto_sign_verify_detached` for joinsplit sigs, etc. — confirmed via §5's earlier libsodium usage grep) unchanged.

**Recommend (b), not (a).** Patching libsodium's own dispatcher (`blake2b_pick_best_implementation()`) means carrying a fork of a security-sensitive, frequently-updated dependency indefinitely, re-applying the patch on every libsodium version bump. Calling a NEON implementation directly from `equihash.cpp`, gated to this one call site, is a smaller, self-contained, easily-removable change — and this is the only call site in the codebase where blake2b is a measured hot path (§2/§5), so there's no benefit to a codebase-wide fix.

**Staged plan:**

1. **Vendor, don't link.** Pull `blake2b-neon.c`/`blake2b-neon.h` (or the minimal subset needed — check what `neon/` actually requires vs. ships, e.g. reference headers it depends on) from `BLAKE2/BLAKE2` at a pinned commit, into a new `src/crypto/blake2/` directory, following the same "vendor at a pinned commit with a hash" convention `depends/packages/*.mk` already uses for every other third-party source. Check its license (`BLAKE2/BLAKE2` is dual CC0/OpenSSL/Apache-2.0-licensed per the reference repo — confirm which applies to `neon/` specifically and that it's compatible with Zero's existing license) before writing any integration code.
2. **Build a standalone correctness harness first, disconnected from `zerod` entirely.** A small test binary that links only the vendored NEON compression function and libsodium's existing `blake2b_compress_ref`, and diffs their output against (a) each other on random inputs and (b) [RFC 7693](https://www.rfc-editor.org/rfc/rfc7693)'s official BLAKE2b known-answer test vectors. This is the cheapest, fastest-iterating place to find a correctness bug — before it's anywhere near consensus code.
3. **Wire in behind a compile-time or runtime flag, not a silent replacement.** Something like `#ifdef ZERO_BLAKE2_NEON` (matching the existing `ZERO_FDCACHE`/`ZERO_PERF` convention from §3/§4) so the vendored path can be disabled instantly if a problem surfaces, and the reference (`blake2b_compress_ref`-backed) path stays the default until the new one is proven.
4. **Differential-test at the `Equihash::IsValidSolution` level**, not just the raw compression function: run both implementations (flag on vs. off) over the same real mainnet blocks — including known Equihash edge cases if any exist in test fixtures (`src/test/equihash_tests.cpp`, if present — check) — and confirm bit-identical `IsValidSolution` results across a large, real sample, not just synthetic RFC vectors. The compression function being individually correct doesn't guarantee it's wired into the multi-round collision/distinctness logic correctly.
5. **Measure, using the exact §2/§5 methodology** (`contrib/perf/capture_sequence.sh`/`decode_captures.py`, same height windows already sampled) — confirm the Equihash bucket's ms/block figure (baseline: 0.252ms ± 1.2% CV) actually drops, and by how much. Given libsodium's *other* accelerated backends (`avx2`/`sse41`) are gated behind x86 intrinsics with no ARM equivalent measured yet, there's no existing "how much would NEON help" baseline from this codebase to compare against — the measurement itself is the first real data point.
6. **Full regression** (Boost `test_bitcoin`, `zero-gtest`) at the same bar §3/§4 were held to, plus the standalone harness from step 2 kept as a permanent regression test, not a throwaway script.

**Note on scope:** this only helps Apple Silicon / ARM builds. If Zero's production nodes are predominantly x86_64 (worth checking, since it changes how much this is worth pursuing at all — see recommended first step below), the accelerated `avx2`/`sse41` backends are presumably already engaging on those, in which case this specific investigation's payoff is scoped to ARM deployments only. **This should be checked before investing further time**, since it directly affects the item's real-world priority relative to Groth16 batching.

### 9.3 Recommended path: Groth16 batch verification, made controlled

§6 already has a 6-step investigation plan and 7-step test plan. **§9.4 below supersedes both with a single, ordered, numbered execution plan** — grounded in the real FFI signatures confirmed from `depends/aarch64-apple-darwin25.3.0/include/librustzcash.h` — that merges §6's investigation/test content with this section's containment strategy into one sequence a developer can actually start from.

**Core principle: never let the batched path be the only path.** Every phase in §9.4 keeps the existing, proven single-proof `verify_proof` call as a mandatory fallback or cross-check, so a bug in the new code can only cause *extra* verification work, never a wrong accept/reject — until the very last, explicitly-flagged phase.

**Why this is more work than "port `batch.rs` and test it," and worth it anyway:** the failure mode being guarded against — a false-accept of an invalid shielded proof — is categorically worse than anything else in this investigation has touched (§3/§4's fixes were pure memoization with no semantic change; this one isn't). The shadow-mode phase in §9.4 turns every day of ordinary development/testing activity into free differential-testing signal against real chain data before the new path is ever trusted to decide anything alone — a substantially stronger validation posture than a fixed test suite alone can provide for a change of this kind.

### 9.4 Groth16 batch verification: full execution plan

Confirmed this session, and load-bearing for the plan below: the actual FFI signatures at the boundary this work has to cross (`depends/aarch64-apple-darwin25.3.0/include/librustzcash.h:139–175`) — `librustzcash_sapling_check_spend(ctx, cv, anchor, nullifier, rk, zkproof, spendAuthSig, sighashValue)` and `_check_output(ctx, cv, cm, ephemeralKey, zkproof)` take **raw serialized proof bytes**, not a pre-parsed `Proof` struct — deserialization currently happens inside each Rust call, once per call. No `librustzcash` Rust source is vendored in this repo (only the built header/`.a` under `depends/aarch64-apple-darwin25.3.0/`) — same situation as libsodium (§5/§9.2): the pinned source has to be fetched fresh for any of this to be real editable code, not assumed from the header alone.

**Phase 0 — Setup (no code changes): DONE.** Fetched `zcash/librustzcash` at the pinned commit into an isolated scratchpad checkout (`/private/tmp/.../scratchpad/groth16-batch/librustzcash-pinned`, outside this repo — no tracked files touched). Findings, reading the real source rather than assuming from the header:

1. ~~Fetch the pinned source~~ Done — shallow-fetched commit `06da3b9ac8f278e5d4ae13088cf0a4c03d2c13f5` directly (full clone times out; `git fetch --depth 1 origin <sha>` works in seconds).
2. ~~Confirm the FFI constraint~~ Confirmed, and refined: `librustzcash_sapling_check_spend`/`_check_output` (`librustzcash/src/rustzcash.rs:677,793`) do **more than proof verification** — `check_spend` also deserializes/checks the value commitment for small-order, deserializes the anchor, and verifies the RedJubjub `spend_auth_sig` **before** deserializing and calling `verify_proof` on the Groth16 proof itself. Only the final `verify_proof` call is what batches; the signature/small-order checks must stay per-proof, unbatched, ahead of the batch step. This refines Phase 2's FFI design (item 8): the new batch entry point should batch only the proof-verification step, with signature/commitment checks still happening per-item first (either in the same call or a separate pre-pass).
3. ~~Confirm struct shapes~~ Confirmed: `bellman::groth16::verifier::verify_proof` (`bellman/src/groth16/verifier.rs`) computes exactly the equation §6 described (`A·B - inputs·γ - C·δ = α·β`, rearranged for one final exponentiation) via `E::miller_loop`/`E::final_exponentiation`. `pairing::Engine::miller_loop<'a, I>(i: I) -> Self::Fqk where I: IntoIterator<Item = &'a (&'a G1Affine::Prepared, &'a G2Affine::Prepared)>` (`pairing/src/lib.rs:88`) is confirmed to genuinely accept an arbitrary-length iterator — this is real, not assumed. `zkcrypto/bellman`'s modern `batch.rs` (fetched for reference) uses a *different*, newer trait (`MultiMillerLoop`/`multi_miller_loop`, operator-overloaded `G1: AddAssign`) than the pinned crate's 2018-era `Engine`/`CurveProjective`/`CurveAffine` — but **every individual operation the algorithm needs (scalar mul, point addition, affine conversion, pairing-prepare) is present on the pinned traits**, just spelled as explicit methods (`add_assign`, `mul_assign`, `into_affine`, `.mul(...)`, `.prepare()`) instead of operator overloads. The port is a rewrite of *syntax*, not of *capability* — no primitive is missing.
4. **New finding, not in the original plan:** the pinned 2018-era `bellman 0.1.0`/`pairing 0.14.2` crate pair **builds clean under a modern Rust 1.90 toolchain** (`cargo check`/`build`/`run` all succeed; edition-2015 semantics still supported, only lint warnings — e.g. bare trait objects, `into_iter()` array-vs-slice ambiguity — no hard errors). This was an open risk (a 2018 crate against a 2026-era toolchain) and it's resolved: no toolchain-pinning workaround is needed to prototype or build against this dependency today.

**Phase 1 — Pure-Rust correctness, zero consensus exposure: DONE.**

4. ~~Write a batch-verify function~~ Done — hand-ported the random-linear-combination algorithm from `zkcrypto/bellman`'s `batch.rs` into a real standalone binary crate (`batch-poc/src/main.rs` in the scratchpad, path-dependent on the pinned `bellman`/`pairing`, **not** vendored into or built by this repo), using only the pinned crate's confirmed-present primitives from item 3 above.
5. ~~Generate known-good/known-bad proof fixtures~~ Done, via a stronger source than originally planned: rather than reusing `zcbenchmarks.cpp`'s Sapling fixtures (which need the full Sapling circuit + trusted setup), used `bellman`'s own real end-to-end test circuit (`bellman/tests/mimc.rs`'s MiMC/BLS12-381 construction) to generate genuine `generate_random_parameters`/`create_random_proof` Groth16 proofs — real proofs over the real pinned Bls12 engine, not synthetic stand-ins.
6. ~~Test N = 1, 2, 8, 64~~ Done and passing: all-valid batches at N=1,2,8,64 — batch accept exactly matches per-proof `verify_proof` (`reference_ok == batch_ok == true`) on every run. One-corrupted-proof-among-N at N=2,8,64 — batch correctly rejects and agrees with the reference that not all proofs were individually valid. Re-ran 6 times total (fresh circuit parameters and fresh random proofs each run, real `thread_rng()`) — zero disagreements across all runs.
7. **Exit criterion: MET.** The standalone batch verifier agrees with per-proof `verify_proof` on every fixture generated, including adversarial (corrupted) ones, across repeated runs with fresh randomness. Phase 2 is unblocked by this criterion, but **not started** — see the status note at the end of this section.

**Phase 2 — FFI boundary design**

8. Design the new entry point: `librustzcash_sapling_batch_validate(ctx, n, cv[], anchor[], nullifier[], rk[], zkproof[], spendAuthSig[], sighashValue[], out_results[])` — collect-then-call, since `main.cpp` already has all spend/output data in hand per-block. Keep the existing single-proof functions exported unchanged — they're needed for Phase 4's fallback.
9. Source the per-batch CSPRNG: match whatever secure-RNG convention existing consensus code already uses (grep `main.cpp`/`random.h` for `GetRandBytes`/`GetStrongRandBytes`) — freshly drawn per batch, never reused.
10. Implement the new FFI function in the fetched checkout, wrapping Phase 1's proven logic, adding only the accumulator/random-scalar bookkeeping to the pinned `bellman` (no crate upgrade — the `miller_loop` shape already matches per §6). Skip the multicore/`rayon` variant here — separable, later work, not required for the O(N)→O(1) final-exponentiation win.
11. Build `librustzcash.a` from the modified checkout; confirm it links against `main.cpp` with a local copy of `librustzcash.h` carrying the new declaration (the depends-built header is normally auto-fetched, so a dev-local header is needed until this is upstreamed into the depends pin).

**Phase 3 — Shadow-mode integration in `main.cpp` (the safety-critical step)**

12. In `ContextualCheckBlock`/`ContextualCheckTransaction` (`main.cpp:1113–1164`), buffer all of a block's Sapling spend/output proofs as they're encountered, **without changing the existing sequential `check_spend`/`check_output` calls or their control flow** — those remain sole authority for accept/reject, exactly as today.
13. After the existing per-proof checks complete for the block, also run the new batch-verify function over the same buffered proofs as a pure side-check. Log any disagreement loudly (a dedicated tag, e.g. `LogPrintf("groth16batch", ...)`) but never let it affect `state.DoS(...)`/accept-reject. This is deliberately wasted CPU during the shadow period — the price of a free, continuous differential test.
14. Run this shadow-mode build through real `-reindex`/sync activity spanning both pre- and post-Sapling heights — reuse the exact height windows already sampled in §2/§3 (610,758–626,806; 995,392–1,083,180; the full six-capture chain-wide sweep) so results are directly comparable to existing baselines.
15. **Exit criterion:** zero disagreements between shadow batch-verify and the authoritative sequential path across a large, real, chain-wide sample. Any disagreement found here sends the work back to Phase 1.

**Phase 4 — Controlled cutover**

16. Flip the batch path to authoritative for the accept case only, behind a build/runtime flag (matching the `ZERO_FDCACHE`-style convention, §3). On batch success, accept as today. On batch failure, fall back to the existing per-proof path (`verify_single`) to get the real, individually-attributed failing transaction/description before rejecting — preserving today's exact error codes (`bad-txns-sapling-spend-description-invalid` etc., `main.cpp:1131,1146`) so RPC/ban-scoring behavior is unchanged.
17. Add an explicit test for the fallback path itself: construct a batch where batch-verify wrongly reports failure (or a genuinely bad-proof batch) and confirm the fallback correctly re-derives the same accept/reject the pre-batch code would have, unassisted.

**Phase 5 — Full validation**

18. Adversarial tests: bit-flip `zkproof`/`anchor`/`nullifier` in one proof among N; confirm the batch fails and the fallback correctly identifies the specific bad transaction.
19. Full regression: Boost `test_bitcoin` (284/284 baseline) and `zero-gtest` (205–207/207, 2 known pre-existing flakes) — same bar as §3/§4.
20. Real-chain differential test: `-reindex` the same height range on both the batched (flag-on) and baseline (flag-off) binaries; diff resulting `chainstate`/best-block-hash — must be byte-identical.
21. Perf re-measurement: same `contrib/perf/capture_sequence.sh`/`decode_captures.py` methodology and height windows as §2, for a directly comparable before/after Groth16-bucket ms/block figure, plus a `bench_matrix.sh`-style throughput A/B (n≥4 trials, t-test) — don't skip this given §3's fd-cache work "worked as designed but showed no measurable win."

**Phase 6 — Sign-off**

22. Independent review of the ported batching math against the published random-linear-combination technique and the pinned crate's real types — not just a diff review — before removing the Phase 4 fallback and treating this as the sole verification path.
23. Optionally, only after all of the above: the multicore/`rayon`-equivalent variant to also engage idle `zcash-scriptch`-adjacent cores — a separate, additive project, not a prerequisite for the O(N)→O(1) win.

**Status: Phases 0–1 executed and passing (see findings inline above); Phases 2–6 deliberately not started.** Phase 0/1's artifacts (the pinned-commit checkout and the `batch-poc` scratch crate) live outside this repo, under the session scratchpad — nothing in `depends/`, `src/`, or any tracked file was modified to produce these results. Phases 2–6 were intentionally not run in the same pass: Phase 2 begins touching build/link configuration, and Phase 3 edits `main.cpp`'s consensus-critical block-validation path — exactly the step this plan's containment strategy (§9.3) exists to gate carefully rather than run through unattended. Stopped here for explicit direction before proceeding, consistent with §9.3's core principle (never let the batched path be the only path) extended to the process of building it: don't let unattended execution be the only check on consensus-code changes either.
