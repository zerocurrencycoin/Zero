# `zerod` sync performance: current understanding, and next steps

## 0. Status at a glance (updated 2026-07-08, end of session)

**Where this stands:** three real fixes shipped (§3 fd-cache/bufsize, §4 root latch, §4 anchor-existence index) — two of the three measured *zero* throughput win despite being correct and well-tested, a genuinely useful negative result. The one bucket that actually matters (Groth16 proof verification, 48–55% of chain-wide CPU) is scoped in depth but not yet implemented; a real, working proof-of-concept for the hand-port approach was built and tested this session (Phases 0–1 of a 7-phase plan), then **a materially better option surfaced mid-session** — an already-shipped, production-proven batch verifier upstream — that needs a decision before Phase 2 continues. See §0.1.

### 0.1 Immediate next step (decide before any more Groth16 code work)

**Hand-port vs. adopt upstream — this is the actual next action, not more coding.** §6.1/§6.2 found that `zcash/sapling-crypto`'s `BatchValidator` (production since 2022, used today by both `zcashd` and Zebra, with a real C++ integration precedent in Pirate Chain — a same-lineage fork) does more than the hand-port plan (§9.4) scoped: it batches RedJubjub signatures too, not just Groth16 proofs. Two live options:

1. **Continue the hand-port** (§9.4 as written) — port only the batching math into Zero's pinned 2018-era crate stack. Phases 0–1 are done and passing (see §0.3). Smaller footprint, no crate migration, but reinvents ~4 years of upstream work and misses signature batching.
2. **Adopt `sapling-crypto` directly** — migrate to the current crate stack, call `BatchValidator` as-is, following `zcashd`'s or Pirate Chain's real integration as a template. Bigger migration (crosses the `ff`/`group` trait-split §6 flagged as "a large, separate undertaking"), but battle-tested, includes signature batching, has a real batch-size precedent (`MAX_BATCH_SIZE=64`/`MAX_BATCH_LATENCY=100ms` from Zebra).

**This decision is not made in this document — it needs a person to weigh migration cost against reuse value.** Full detail: §6.1 (what upstream ships), §6.2 (who else has adopted it), §9.4's status note (what's already built and tested for option 1).

### 0.1a PENDING DECISION — Groth16 batch verification: hand-port vs. adopt `sapling-crypto`

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

**Recommendation (offered, not decided): lean toward Option B if the migration cost turns out to be smaller than it currently looks, otherwise Option A.** Concretely: the single highest-leverage next step is **not** more coding on either path, but **scoping Option B's actual migration cost** (§0.2 item 6) — right now it's the con with the least evidence behind it ("large, separate undertaking" is a characterization from §6, not a sized estimate), while Option A's cost and viability are already fully measured (§9.4 Phases 0–1). A short, bounded research spike into what the `ff`/`group` migration and FFI-layer question actually require (see §0.5, §0.6) would turn this from a qualitative pro/con list into a real comparison. Until that spike happens, Option A is the lower-uncertainty choice by default, purely because it's the one with a working prototype — not because it's been shown to be better.

### 0.2 Priority-ordered open items

1. **[Decision, not code] Hand-port vs. adopt** — see §0.1. Blocks all further Groth16 work.
2. **NEON blake2b integration for Equihash** (§5, plan in §9.2) — lower payoff (6–12% of CPU) than Groth16 but far lower risk (not consensus-critical) and exercises the same vendor/test muscle. **Recommended as the next item to actually *start* coding**, independent of the Groth16 decision above. First sub-step before investing further: confirm whether Zero's real deployments are ARM or x86_64 — this only helps ARM, and that hasn't been checked.
3. **`-O1` vs `-O2` build comparison** — a user-reported "little difference," never reproduced with a real measurement. Cheap, quick, still not done.
4. **Size and consider removing/gating `CBlockIndex`'s "Shieldex" fields** (§8.2) — 22 always-present `int64_t` fields, ~176 bytes/block (~435MB chain-wide at tip) regardless of whether `-zindex` is on. One field (`nNotarizations`) is confirmed fully dead. Not sized against `AddToBlockIndex`'s total footprint or scoped for a fix — smallest, most self-contained item on this list if someone wants a quick win.
5. **[If option 1 chosen in §0.1] Groth16 hand-port Phase 2 onward** — §9.4 Phases 0–1 done; Phase 2 (FFI/build changes) and Phase 3 (`main.cpp` consensus-code edit) explicitly not started, pending both the §0.1 decision and separate go-ahead given Phase 3's blast radius.
6. **[If option 2 chosen in §0.1] Scope the `sapling-crypto` migration cost** — not sized at all yet: what breaks when Zero's `librustzcash`/`bellman`/`pairing`/`jubjub` stack moves to the current `ff`/`group`-split crate generation, whether Zero's C-header FFI (`librustzcash.h`) can stay or needs a `cxx`-bridge rewrite like `zcashd`'s, and how big a lift that really is. This is real, unscoped work either way — a research spike of its own before implementation could start down this path.

### 0.3 What's actually been built and tested (not just planned)

- **§3, §4 (root latch), §4 (anchor-existence index):** implemented, in this repo's tracked source, full regression-tested (Boost `test_bitcoin` 284/284; `zero-gtest` 205–207/207 with 2 known pre-existing flakes). These are real, committed changes.
- **§9.4 Phases 0–1 (Groth16 hand-port prototype):** real, working code — but **lives entirely in this session's scratchpad** (`/private/tmp/claude-501/.../scratchpad/groth16-batch/`), **not in this repo, and not durable past session end.** Fetched the pinned `librustzcash` source at the exact commit, hand-ported a random-linear-combination batch verifier against the real pinned `bellman`/`pairing` crates, generated genuine Groth16 proofs via `bellman`'s own MiMC/BLS12-381 test circuit, and confirmed batch accept/reject exactly matches per-proof `verify_proof` for N=1,2,8,64 (all-valid and one-corrupted-among-N), repeated 6 times. **If picked back up, Phase 0 (fetch the pinned source) needs re-running from scratch** — nothing to reload, only results to trust (which are fully written up in §9.4, not just asserted here).

### 0.4 Postponed (documented so they aren't lost, not scheduled for near-term work)

- **Run the bootstrap-import leg of `bench_matrix.sh` for real** — the datadir-reset bug is fixed and validated on a small dry run only; a full 4-trial × 2-condition bootstrap comparison hasn't been run.
- **`LoadBlockIndexDB`'s missing interruption point** (§3) — a real, narrow-blast-radius gap; not scoped for a fix, may stay a documented limitation indefinitely.
- **A second `MallocStackLogging` window sampled entirely post-Sapling-activation** (§7) — the current one straddles the activation boundary; given Groth16 verification itself allocates nothing and the dominant allocator (`AddToBlockIndex`) has no Sapling-specific component, a second window is unlikely to change the qualitative conclusion, so not pursued further.
- **§9.4's originally-planned per-transaction-attributed fallback design** (Phase 4) — §6.2 found current `zcashd` doesn't do this at all (it rejects the whole block with one generic error on batch failure); whether Zero should match that simpler upstream behavior or keep the more careful per-tx design is an open question folded into §0.1's decision, not resolved separately.
- **Multicore/`rayon`-equivalent parallel batch verification** — both the hand-port (§9.4 Phase 2 item 10) and Zebra's real deployment (§6.2, `sapling-crypto`'s `"multicore"` feature) treat this as separable, later work on top of single-threaded batching, not a prerequisite.

### 0.5 Known gaps in understanding / unresolved questions

- **ARM vs. x86_64 real deployment mix for Zero nodes — unknown.** Directly determines whether NEON blake2b (item 2, §0.2) is worth pursuing at all; not checked this session or any prior one.
- **Whether Zero's current C-header FFI (`librustzcash.h`, raw `extern "C"`) could be kept alongside a `sapling-crypto` migration, or would need replacing with a `cxx`-bridge like `zcashd`'s current architecture** — not investigated; directly affects how big option 2 in §0.1 really is.
- **Whether Zero's own `CBlockIndex` "Shieldex" fields (§8.2) are used by anything beyond the one RPC endpoint confirmed** (`rpc/blockchain.cpp`'s shielded-tx-rate stats) — confirmed one real consumer, didn't exhaustively check for others before suggesting the fields could be gated/removed.
- **No `-O1`/`-O2` measurement exists at all** (item 3, §0.2) — the "little difference" claim in this document's history has never been checked against real data, in either direction.
- **§9.4 Phase 4's fallback design vs. current `zcashd`'s simpler whole-block-reject behavior** — genuinely open, not just postponed (see §0.4); affects error-message/ban-scoring granularity, not correctness.

### 0.6 Possible research spikes (not yet scoped as tasks — smaller than the items above, worth a look if time allows)

- **Whether Pirate Chain's C++ `cxx`-bridge port (`src/rust/src/sapling.rs`, `src/rust/src/bridge.rs`) is directly adaptable to Zero**, given both are same-lineage zcashd forks — could shortcut a large fraction of option 2's (§0.1) scoping work if their crate-version pins and build tooling are close enough to Zero's `depends/` system. Not checked: how their `depends`-equivalent build step differs from Zero's, or how much of their bridge code is Pirate-specific vs. reusable.
- **Whether `zcashd`'s own pre-`cxx`-migration history (its git log, before the current `rust/bridge.h` architecture) shows an intermediate step comparable to Zero's current state** — could reveal a real, tested incremental path from raw-C FFI to batching, rather than jumping straight to `cxx`. Not investigated — the `zcashd` checkout fetched this session was a shallow, single-commit clone with no history to search.
- **Whether `Equihash::IsValidSolution` has existing test fixtures with known edge cases** (§9.2 step 4 flags `src/test/equihash_tests.cpp` as unchecked) — would materially de-risk the NEON differential-testing step; a five-minute check not yet done.

### 0.7 Section index (each section's own header states its finding — this is a pointer list, not a summary)

§1 methodology · §2 CPU bucket breakdown (Groth16 dominates post-Sapling) · §3 disk I/O fd-cache/bufsize (implemented, no measured win) · §4 root latch (implemented, flat) + anchor-existence index (implemented, untested for CPU-bucket impact) · §5 Equihash/blake2b root cause · §6 Groth16 batching scoped, §6.1 upstream `BatchValidator` found, §6.2 cross-ecosystem survey · §7 memory profiling (`AddToBlockIndex` dominates) · §8 per-block allocation detail + Shieldex field audit · §9 recommended paths, §9.4 Groth16 execution plan (Phases 0–1 done).

---

## 1. Scope, method, and reproduction procedure

**Subject:** where `zerod` spends CPU during `-reindex` (rebuild `chainstate` from local `blocks/*.dat`) and `bootstrap.dat` import (bulk-load a pre-staged flat file of blocks) — the two faster-than-network ways to catch a node up. Both were assumed "fast" but never measured; this investigation measured them, found the dominant costs, and implemented and measured fixes for two of them.

**Working tree:** `ZeroPerf` (`/Users/walter/Work/ZK/ZeroPerf`, branch `perf-401`), built at `-O1` (`-pipe -O1 -g -fwrapv -fno-strict-aliasing`, the repo default). Binary is self-contained (verified via `otool -L`: only system libraries dynamically linked, all third-party dependencies static).

**Terms:**
- **Bucket:** one of a small number of mutually-exclusive CPU-time categories a profiling sample falls into, matched against *any* frame in a sample's call stack (not just the leaf).
- **Latch:** a single-slot memoization — one stored value (or empty), cleared by the operations that change underlying state, repopulated on next read. Not a cache: no key, no multiple entries, no eviction policy, because there is only ever one live value to remember.
- **Activation height:** the mainnet block height at or after which a network upgrade's rules apply. Sapling: height 492,850 (`chainparams.cpp`).

**Profiling method:** a real mainnet datadir (not synthetic/regtest — script/tx mix affects where time goes) profiled with Instruments Time Profiler (`xcrun xctrace`, headless CLI) attached to the single worker thread that does the actual reindex/import work (`zcash-loadblk`, running `ThreadImport`). Every other thread (idle script-check-queue workers, RPC/net/**wallet** threads) is filtered out — unfiltered, all-threads profiles are dominated by idle-thread noise (85%+ of raw samples blocked on a condvar) and say nothing about where real work goes.

**Scope note -- not wallet:** this Perf.md line and `contrib/perf/` (`capture_sequence.sh`, `bench_matrix.sh`, `bucket_profile.py`) measure **ConnectBlock / import** throughput and CPU buckets (Groth16, Equihash, disk, trees). They intentionally **exclude** wallet/`AddToWallet`/`OrderedTxItems`. Fat-wallet reindex pain and `wtxOrdered` work are **out of scope** here; see Zero400 **ZeroStruct** §13.4.3.

**Retarget for wallet CPU (if measuring `wtxOrdered`):** do **not** reuse the default filter. Attach to the thread that runs `AddToWallet` (or temporarily avoid filtering wallet frames); add buckets for `OrderedTxItems` / `AddToWallet` / `CWallet::`; use a **large wallet** datadir and a **short** height window; prefer insight/txindex off when indexes are not under test. `bench_matrix.sh` blk/s is only informative if the window is wallet-bound -- otherwise it reports ConnectBlock noise.

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

---

## 2. CPU cost breakdown: what dominates, and why it's height-dependent

**Original measurement** (`-reindex` on two builds, `bootstrap.dat` import, chain heights ~10K–2M; mutually exclusive buckets, `zcash-loadblk` thread only, 0% unaccounted backtraces in every run):

| Bucket | Typical range | Call path (leaf → root) |
|---|---|---|
| Sapling/Sprout tree update | 57–58% | `Fr::mul_assign`/`Fr::inverse` (BLS12-381 field arith) ← `jubjub::edwards::Point::add` ← `librustzcash_merkle_hash` ← `IncrementalMerkleTree::root()` ← `CCoinsViewCache::AbstractPushAnchor` ← `ConnectBlock` |
| Equihash PoW verification | 24–27% | `blake2b_compress_ref` ← `blake2b_final` ← `Equihash<192,7>::IsValidSolution` ← `CheckEquihashSolution` ← `CheckBlockHeader` |
| Disk I/O | 15–18% | `OpenDiskFile`/`ReadBlockFromDisk`/`UndoWriteToDisk` (`fopen`/`open` syscalls) ← `LoadExternalBlockFile`/`ConnectBlock` |

**This breakdown is identical for `-reindex` and `bootstrap.dat` import** — both call the same `ConnectBlock`/`CheckEquihashSolution`/`AbstractPushAnchor` validation per block; `bootstrap.dat` only changes how block bytes arrive, not what validation happens once a block is in hand. Measured `bootstrap.dat` import: **145.7 minutes** (8,743,120 ms, self-reported) for 2,468,990 blocks, ≈282 blocks/sec average across the entire chain history. **`bootstrap.dat`'s entire benefit is skipping network download time; it cannot reduce the CPU-bound validation cost.**

**`bootstrap.dat`'s source, for reproducibility (previously undocumented).** The 5,415,354,491-byte file used for these measurements (`reindex-profile/bootstrap/bootstrap.dat`) was generated locally via Zero400's own `contrib/linearize` tooling (`/Users/walter/Work/ZK/Zero400/contrib/linearize/linearize-hashes.py` + `linearize-data.py`, which build a bootstrap file directly from a synced node's own `blocks/*.dat`, not downloaded from any external source) — an identical-size copy is kept at `/Users/walter/Work/ZK/Zero400/contrib/linearize/bootstrap.dat`. If `reindex-profile/bootstrap/bootstrap.dat` is ever deleted as scratch, it can be regenerated by re-running `linearize-data.py` against a fully-synced datadir, or copied fresh from the Zero400 location above — not refetched from any network source.

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

**Implemented: the membership-index technique (§0 item 3).** `CCoinsView`'s existing `GetSproutAnchorAt`/`GetSaplingAnchorAt` (`coins.h`/`coins.cpp`/`txdb.cpp`) always deserialize the full stored tree, even when the caller only needs to know the anchor is valid. But at the DB layer (`CCoinsViewDB`, `txdb.cpp`), the LevelDB key is already the root itself (`make_pair(DB_SPROUT_ANCHOR, rt)`/`make_pair(DB_SAPLING_ANCHOR, rt)`) — a pure existence check (`db.Exists`) was already possible at that layer without a schema change, just not exposed. Added `HaveSproutAnchorAt`/`HaveSaplingAnchorAt` as new virtual methods through the same chain (`CCoinsView` → `CCoinsViewBacked` → `CCoinsViewCache` → `CCoinsViewDB`), existence-only at every layer: `CCoinsViewCache`'s variant checks its own in-memory anchor cache first (reusing an already-fetched entry without touching the base view again) and otherwise defers to base *without* populating the tree cache — a later `GetSproutAnchorAt`/`GetSaplingAnchorAt` call still works correctly, it just pays its own DB read at that point, same as before this change.

`HaveShieldedRequirements` (`coins.cpp`) now uses these where the tree object was never actually used afterward:
- **Sapling spends**: the tree fetched via `GetSaplingAnchorAt` was never read again after the existence check — switched unconditionally to `HaveSaplingAnchorAt`. Sapling spends never chain (§4's finding: they never call `.append()`/`.root()` in this function), so this is always safe.
- **Sprout joinsplits**: chaining (a later joinsplit's anchor matching an earlier one's output root, via the `intermediates` map) is only *possible* when a transaction has more than one joinsplit. Added a `mayChain = tx.vJoinSplit.size() > 1` guard: single-joinsplit transactions (structurally unable to consume an `intermediates` entry) use `HaveSproutAnchorAt` and skip tree reconstruction/`intermediates` bookkeeping entirely; multi-joinsplit transactions fall through to the original tree-reconstruction path unchanged, preserving exact existing behavior for the one case that needs it.

**Validation.** `test/coins_tests.cpp`'s `chained_joinsplits` case (2–4 joinsplits per transaction, every ordering/chaining combination) exercises exactly the `mayChain = true` path and passes unmodified — the multi-joinsplit path is byte-for-byte the pre-existing code. Four other `CCoinsView`-subclassing test doubles (`test/coins_tests.cpp`'s `CCoinsViewTest`, `zcbenchmarks.cpp`/`gtest/test_validation.cpp`/`gtest/test_mempool.cpp`/`gtest/test_transaction_builder.cpp`'s `FakeCoinsViewDB`/`TransactionBuilderCoinsViewDB`) each override `GetSproutAnchorAt`/`GetSaplingAnchorAt` directly but hadn't overridden the new `Have*AnchorAt` methods — without a fix they'd silently inherit the `CCoinsView` base class's `return false`, breaking every existence check against them. Added matching `Have*AnchorAt` overrides to all four, mirroring each one's existing `Get*AnchorAt` logic (membership check against the same backing map/condition, no tree deserialization). Full regression: Boost `test_bitcoin` 284/284 clean; `zero-gtest` 205/207, with the 2 failures (`WalletTests.ClearNoteWitnessCache`, intermittently `wallet_zkeys_tests.WriteCryptedSaplingZkeyDirectToDb`) reproduced identically against the unmodified baseline (same failures, same pass-in-isolation behavior) — confirmed pre-existing test-order-dependent flakiness in wallet-test global state, not a regression, and consistent with §4's own already-documented "pre-existing unrelated wallet-key test flake" note.

**Not yet measured for CPU-bucket impact.** Implemented and regression-tested, but not yet re-profiled with Instruments to quantify the effect on the tree/anchor bucket (~6–14% of CPU per §2) — the Sprout-joinsplit share of that bucket should shrink for single-joinsplit transactions (the common case per §4's per-block table: idle/Sapling-only blocks already had cheap, near-empty trees, so the volume this targets is specifically Sprout-joinsplit-bearing blocks), but by how much hasn't been measured.

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

### 6.2 Cross-ecosystem status: who else has (and hasn't) adopted batch verification

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

**Net conclusion, corrected for the compression confound: memory grows roughly linearly with chain length (no leak signature), at a rate in the rough 1–3KB/block range that's noisier than initially measured but not cleanly increasing or decreasing** — consistent with the dominant cost (`AddToBlockIndex`, below) being close to a constant per-block-header cost. This resolves §0's original next-step framing (was there unbounded growth?) to "no": growth tracks a permanent, one-entry-per-block-header in-memory index that's expected to accumulate and never compact, not a leak. (Chain-length-proportional growth is real and worth knowing operator-side — a fully-synced node's block-index memory floor scales with chain height, and this run's `Writable regions: Total` reached 4.7GB at the real chain tip — but that's a capacity-planning fact, not a defect.)

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

### 8.1 `AddToBlockIndex` (`main.cpp:3932`) — 4 heap allocations per block

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
