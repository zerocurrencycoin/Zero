# Spec: block-processing phase timers

Design and specification for `IMP-BENCH-ALWAYS` and its dependent parser work
(`AUT-BENCH-INGEST`). Covers what the existing timers measure, three defects
found by reading the call sites, the proposed shape, and what each change must
be checked against.

**No code changes are made by this document.** Tracking item and state:
`docs/TASKS.md` B1. Findings that motivate it: `docs/FINDINGS.md` S1.1.

Numbers cited by `M-*` id live in `Measures.md`. Line numbers are
`src/main.cpp` at the commit this was written against
(`b1a37bffc`); re-confirm before editing, they drift.

---

## 1. What exists today

Eleven `LogPrint("bench", ...)` sites, all in `src/main.cpp`:

| Line | Label | Accumulator | Scope |
|-----:|-------|-------------|-------|
| 3248 | `Connect %u transactions` | `nTimeConnect` | inside `ConnectBlock` |
| 3260 | `Verify %u txins` | `nTimeVerify` | inside `ConnectBlock` |
| 3339 | `Index writing` | `nTimeIndex` | inside `ConnectBlock` |
| 3347 | `Callbacks` | `nTimeCallbacks` | inside `ConnectBlock` |
| 3512 | `Disconnect block` | -- (no accumulator) | `DisconnectTip` |
| 3587 | `Load block from disk` | `nTimeReadFromDisk` | `ConnectTip` |
| 3599 | `Connect total` | `nTimeConnectTotal` | `ConnectTip` |
| 3603 | `Flush` | `nTimeFlush` | `ConnectTip` |
| 3608 | `Writing chainstate` | `nTimeChainState` | `ConnectTip` |
| 3633 | `Connect postprocess` | `nTimePostConnect` | `ConnectTip` |
| 3634 | `Connect block` | `nTimeTotal` | `ConnectTip` |

Two properties matter for the design:

**The measurement is unconditional; only the output is gated.** Each site is
`int64_t nTimeN = GetTimeMicros(); nTimeX += nTimeN - nTimePrev;` followed by
`LogPrint`. `LogPrint` early-outs at `LogAcceptCategory(category)`
(`src/util.h:97`) *before* `tfm::format` runs. So a node without
`-debug=bench` still pays every `GetTimeMicros()` call and still maintains
every accumulator -- and then discards the result.

**Nothing else is on by default.** `UpdateTip` (`src/main.cpp:3474`) logs
unconditionally per block -- hash, height, log2_work, tx count, date,
progress, cache size -- and **no timing**. A field node's `debug.log` shows how
far it got, never how long any phase took.

---

## 2. Defects in the existing timers

These are properties of the upstream instrumentation, inherited. They are
listed first because two of them change what the new work should emit -- a
periodic summary that faithfully reports these counters would inherit their
flaws.

### 2.1 Proof verification is not inside any timer -- the significant one

Groth16 proof verification is **48-55% of chain-wide `zcash-loadblk` CPU and
88-91% post-Sapling** (`PerfGroth.md` S1). It is covered by **no bench timer at
all**. Two separate paths, both outside:

- **Sprout JoinSplit.** `ConnectBlock` calls `CheckBlock` with a real
  `ProofVerifier` at **line 2982**. `nTimeStart` is set at **line 3049**.
  Verification therefore completes 67 lines *before the first timer starts*.
- **Sapling spend/output.** `librustzcash_sapling_check_spend` /
  `_check_output` (lines **1125** / **1143**) are reached from
  `ContextualCheckTransaction`, called by `ContextualCheckBlock` (line
  **4532**), which runs in `AcceptBlock` (line **4665**) -- during block
  *acceptance*, entirely outside `ConnectTip`.

**Consequence.** `- Connect block:` can report a small number while the node is
saturated verifying proofs. Any always-on summary built only from the existing
accumulators would systematically under-report the single largest cost, and
would do so *worst* exactly post-Sapling where it matters most. This is a
correctness requirement on the feature, not a nice-to-have: **a phase summary
that omits 88-91% of the work is worse than no summary**, because it invites
the reader to conclude the time went somewhere it did not.

**Implication for scope.** Closing this needs a new timer around proof
verification, not merely a new report over existing counters. That raises
`IMP-BENCH-ALWAYS` from "report what we have" to "report what we have, plus one
new measurement point". Recommend the new point be added **first**, since the
report is not worth shipping without it.

### 2.2 `nTimeConnect` and `nTimeVerify` overlap -- they do not partition

Both measure from the same origin:

```
line 3247:  nTime1 = GetTimeMicros(); nTimeConnect += nTime1 - nTimeStart;
line 3259:  nTime2 = GetTimeMicros(); nTimeVerify  += nTime2 - nTimeStart;   // nTimeStart, not nTime1
```

`nTimeVerify` is *cumulative from `nTimeStart`*, so it **includes** the whole
`nTimeConnect` span. Adding the two double-counts the connect phase. This is
upstream Bitcoin/Zcash behaviour and the labels do not say so.

**Requirement.** A summary must not present these as sibling shares of a whole,
and must not sum them. Either report `verify_excl = nTimeVerify - nTimeConnect`
as the script-verification-only span, or label the field explicitly cumulative.
Silently emitting both next to each other in a table is how this becomes a
published wrong number.

### 2.3 Uncovered spans inside `ConnectBlock`

`nTimeStart` (3049) begins after `CheckBlock` (2982) and after
`CCheckQueueControl` construction (3047). Undo-data write and index writes
between the Verify site (3260) and the Index site (3339) fall inside
`nTimeIndex`, which is fine, but the pre-`nTimeStart` region is attributed to
nothing. `nTimeTotal` at line 3632 accumulates `nTime6 - nTime1` measured in
`ConnectTip`, so the `ConnectBlock` interior sums do **not** reconcile against
it.

**Requirement.** The summary must emit an explicit `unattributed` residual
rather than letting phases silently fail to sum. A residual that grows is
itself a finding.

---

## 3. Proposed design

### 3.1 Principle

Report **from counters the node already maintains**, add the **one** missing
measurement point that S2.1 shows is required for the report to be honest, and
emit on an interval rather than per block. Do not add a second parallel timing
system.

### 3.2 New measurement point

One accumulator pair around proof verification:

| Counter | Span | Site |
|---------|------|------|
| `nTimeProofSprout` | `CheckBlock`'s `CheckTransaction` loop when the verifier is not `Disabled()` | around line 2982 |
| `nTimeProofSapling` | the spend/output/binding-sig block | around lines 1125-1165 |

Two counters rather than one, because the pools have different cost curves
across Sapling activation and collapsing them loses the distinction the S1-vs-S3
captures exist to show. Both are `GetTimeMicros()` deltas into a static
`int64_t`, matching the existing idiom exactly.

**Cost.** Two `GetTimeMicros()` calls per block on the Sprout path. The
existing code already makes 6+ such calls per block unconditionally, so this is
within the noise of what is already paid. Confirm against the recorded same-host
repeat pair before and after (S5).

**Placement caution.** `ContextualCheckTransaction` is also called from
`AcceptToMemoryPool` (line 1497). A counter placed at 1125/1143 accumulates
mempool-admission proof checks as well as block-validation ones. Either scope
the counter to the block path or -- better -- keep them separate, because
mempool proof-check cost is itself worth knowing and conflating the two makes
both unreadable.

### 3.3 Emission

A single line, on an interval, at default log level. Shape:

```
BenchSummary height=%d interval_blocks=%d interval_s=%.1f
  proof_sprout=%.1f/%.1f proof_sapling=%.1f/%.1f connect=%.1f/%.1f
  verify_excl=%.1f/%.1f index=%.1f/%.1f callbacks=%.1f/%.1f
  readdisk=%.1f/%.1f flush=%.1f/%.1f chainstate=%.1f/%.1f
  postconnect=%.1f/%.1f unattributed=%.1f/%.1f total=%.1f/%.1f
```

Each field is **`interval/cumulative` seconds**. Both, not one:

- **Cumulative alone cannot show a region got slower.** After 500k blocks a
  cumulative mean is so damped that a phase doubling in the current band barely
  moves it. That is the regression the feature exists to catch.
- **Interval alone loses the run-level picture** and makes trials hard to
  compare.

The existing `[%.2fs]` fields are cumulative-only, which is why they have never
answered a "when did it get slow" question.

### 3.4 Interval selection

Follow the established `-mrclogevery` pattern (default 16384, S4.2 of
`docs/HOWTO.md`) rather than inventing a new convention: `-benchsummaryevery=N`
blocks, `0` to disable.

**Default: on.** The point of the feature is evidence from field nodes that
were not specially configured; an opt-in default reproduces the gap it exists to
close. At 16384 blocks this is a handful of lines per hour of IBD, against a
per-block `UpdateTip` line already being written -- roughly a 0.006% increase in
line count. That ratio is the argument for default-on, and it should be
re-stated in review rather than assumed.

**Height-based, not wall-clock.** Blocks are the unit every other measure here
uses, so a height interval makes summaries directly comparable across trials at
the same window. A wall-clock interval would emit differently-sized samples in
fast and slow regions -- precisely confounding the comparison.

**Caveat: follow-tip.** At tip, 16384 blocks is roughly three weeks at 120s
spacing, so a followed node emits almost never. Either accept that (the feature
targets IBD/reindex/catch-up, where the cost is) or add a wall-clock backstop
that also fires after N hours. Recommend accepting it initially and revisiting
only if field logs prove uninformative -- a backstop reintroduces the
variable-sample-size problem above.

### 3.5 Explicitly not proposed

| Not doing | Why |
|-----------|-----|
| Per-block always-on timing lines | Millions of lines on a reindex; `-debug=bench` already covers per-block when wanted |
| A new RPC surfacing the counters | `getblockchaininfo`-style polling is a different feature with a different consumer; log lines are what field reports already carry |
| Replacing the `-debug=bench` lines | They stay; this is a summary layer over the same counters |
| Timing inside the script-check thread pool | `CCheckQueueControl` is concurrent; a wall-clock span there is not attributable to a phase without per-thread accounting |
| Sub-phase Groth16 breakdown | That is Time Profiler work (`docs/HOWTO.md` Part 2), not log instrumentation |

---

## 4. Parser work (`AUT-BENCH-INGEST`)

`extract_measures.py` has exactly one bench regex, `BENCH_CONNECT_RE` (line
66), matching `- Connect block:` -- the total. The ten lines that decompose it
are parsed by nothing, so `--bench` today ingests the least informative of the
eleven.

**Two independent deliverables**, in this order:

1. **Parse the existing ten lines.** No node change, works on logs already on
   disk. Each becomes a Measures token (`connect_ms`, `verify_excl_ms`,
   `index_ms`, `callbacks_ms`, `readdisk_ms`, `flush_ms`, `chainstate_ms`,
   `postconnect_ms`, `disconnect_ms`, `total_ms`).
2. **Parse `BenchSummary`.** Depends on S3.3 landing.

**Aggregate on ingest.** `-debug=bench` is per block, so a full reindex is
millions of lines. Emit per height band, as existing throughput rows already
are -- not a row per block. Carry `n` per band; `docs/HOWTO.md` S4.5 rule 3
requires trial count with every figure.

**Carry the S2.2 hazard into the parser.** If both `connect` and `verify` are
ingested, the verify token must be the exclusive form or explicitly named
cumulative. The parser is where this gets frozen into data that outlives the
reader who knew the caveat.

---

## 5. How each change is checked

| Change | Check |
|--------|-------|
| New proof counters | Sum of `proof_sprout + proof_sapling` against a Time Profiler capture's `groth16_proof` bucket on the same window. Expect agreement within a few points; a large gap means the counter is misplaced |
| Any new timer | Throughput unchanged vs the recorded same-host repeat pair `tiny-20260819T234958Z` / `tiny-20260819T235438Z` (178.0s / 171.0s, 4% spread). A regression outside that spread is the new instrumentation |
| Summary arithmetic | Phases plus `unattributed` reconcile to `total` within rounding, on a tiny reindex |
| `verify_excl` | Equals `nTimeVerify - nTimeConnect`; assert non-negative, since a negative value means the S2.2 relationship changed upstream |
| Parser | `--self-test` extended with a fixture log containing all eleven line shapes plus a `BenchSummary` |
| Default-on decision | Line-count delta measured on a tiny reindex, stated in review |

**Post-Sapling validation is mandatory for S2.1.** A pre-Sapling-only check
would show small proof counters and could pass a misplaced timer. Use the
12-file trimmed archive (`chainblocks-postsap12.tgz`, reaches h583699+,
`docs/HOWTO.md` S1.2), where proof cost is 88-91% and a misplacement is
obvious.

---

## 6. Sequencing and ownership

1. **Parse the existing ten lines** (S4 item 1) -- ZeroPerf-owned, no node
   change, immediately useful on logs already captured.
2. **Add proof-verification counters** (S3.2) -- product change, Zero400 review.
   Required before any summary is worth shipping (S2.1).
3. **Emit `BenchSummary`** (S3.3) -- product change, Zero400 review.
4. **Parse `BenchSummary`** (S4 item 2).

Steps 2 and 3 touch `src/main.cpp`, which is **Zero400-owned**
(`docs/POLICY.md` S1). They are specified here and reviewed there. Step 1 is
`contrib/perf/` and can proceed independently.

**Not gated on GROTH-DECIDE.** Measuring proof cost is not the same as changing
how proofs are verified, and better measurement is useful whichever of Option A
or Option B is eventually chosen. If batching does land, these counters are how
its effect gets measured in the field.
