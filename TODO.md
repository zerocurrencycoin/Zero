# TODO

Open follow-ups for the Zero **full node** (`zerod`). Commands and inventory: **TEST_ZERO.md**. Chain economics: **ZERO_COIN.md**. Build: **BUILD_ZERO.md**.

---

## Labels

| Prefix | Meaning |
|--------|---------|
| **CON-*** | Consensus / engineering invariant |
| **WAL-*** | Wallet / RPC |
| **OPS-*** | Ops / DB / notify / build surface |
| **EXT-*** | Extended harness |
| **TST-*** | Test / gate work |

---

## Ordered next

1. **WAL-GETALLDATA-NOTMODIFIED** -- change-keyed "nothing new" answer, ahead of W5. Design
   evaluation in **Full descriptions**. Short form: replace the 20 s time gate with a state
   key, serve unchanged state from cache, and keep a slow safety refresh.
2. **WAL-GETALLDATA-W5** -- tip poll split (balances vs History); revisit after the getalldata
   soak and after NOTMODIFIED lands.
3. **TST-01** remainder / **TST-03** -- harness gaps with ready consumers (see Full
   descriptions). **TST-05** and **TST-09** notify half are **in tree** (`miner_tests`
   `CreateNewBlock_regtest_48_5`; `equihash_tests` `validator_testvectors_192_7*`;
   `DeprecationTest.BlockNotifyDefaultSkipsShell` / `WalletNotifyDefaultSkipsShell`) --
   unblocks **OPS-ALERT-STRIP**.
4. Release / docs track -- Linux `--strict` + `--suite`; Windows MXE **never executed** in this program; supply review (~20M ZER target). **Signing / checksums during release prep** (REL-01/02). Receipts: **`.build/`** via `zcutil/check-setup.sh` and `zcutil/check-release.sh`. Python floor remains **3.10+** (not 3.11). Ops smoke and ZeroPerf pull-in (one or two increments): **TEST_ZERO.md** §8.
5. Postponed bucket: see **Pending** (not scheduled).

---

## Active

- Node setup and maintenance docs: keep user-facing instructions accurate
- Chain bootstrap: end-user import path (`-loadblock` / auto-import); linearize in `contrib/linearize/`
- Total supply discrepancy: arithmetic vs ~20M ZER target
- RPC coverage matrix: `RPCs.csv` vs harness depth
- **TST-01** -- exclusive getalldata + Ext `getalldata_scenario` working; under development: `getsupply` / `zs_*` / sapling depth
- **TST-03** -- `zeronodestats` + zeronode/budget subcmds; arg validation
- **TST-05** -- **done**: (48,5) `CreateNewBlock_regtest_48_5` live in `miner_tests`; genesis (192,7) KATs `validator_testvectors_192_7` / `_h1` in `equihash_tests`; KATs ship from `src/test/data/`
- **TST-09** -- **done**: alertnotify plus `DeprecationTest.BlockNotifyDefaultSkipsShell` / `WalletNotifyDefaultSkipsShell`. Unblocks **OPS-ALERT-STRIP**
- **WAL-GETALLDATA-W5** -- revisit soon
- macOS datadir: prefer `Application Support/zero/` for wallet
- Fuzz harness setup
- macOS libtool `-bind_at_load` -- ensure `MACOSX_DEPLOYMENT_TARGET` from build system

---

## Pending

- OPS-REINDEX remainder -- refuse / `-reindexforce`; skip-wallet below H
- OPS-ALERT-STRIP -- gut P2P `alert.cpp` after TST-09 slim
- TST-SAPLING-ROOT -- `finalsaplingroot.py` (Bfail)
- TST-WITNESS-REINDEX -- witness rebuild / CleanIndex coverage
- OPS-CACHE-METRICS -- tunable cache metrics
- WAL-GETALLDATA-CACHE (W6), W1, W4, ARG2-DEFAULT, HELPERS -- after W5 / soak
- WAL-GETALLDATA-LEGACY-SCOPE -- which 2018--2020 surface can shrink
- WAL-RPC-ACCOUNTS -- postponed; product decision required
- WAL-LOCKEDPOOL -- LockedPool / `getmemoryinfo`
- OPS-TXINDEX-DEFAULT / OPS-AT-HEIGHT -- postponed
- OPS-TOR-COMPILE-OUT -- optional `--disable-tor`
- OPS-I2P -- ecosystem track only; no Zero implementation scheduled
- OPS-DEBUGLOG-TIMING -- filter/process `debug.log` timing tooling
- EXT-INSIGHT-SUPERSET -- postponed
- `txindex.py` -- promote after green
- P2P logging after zn dispatch -- **done** (TNT-01)
- Params archival / Windows hardening / branch-id CI / OpenSSL 3 / SwiftTX strip / Debian packaging

---

## Completed (summary)

- WAL-WTXORDERED + Assure-4; getalldata S4--S8 + W2/W3 exclusive; `getalldata_scenario` Ext
- Founders regtest window + `founders_window.py`; Tier B wallet Sapling port
- Integer subsidy: `GetBlockSubsidy` in zats; founders **`GetFoundersRewardAmount` = `subsidy * 75 / 1000`** (miner, `ConnectBlock`, GBT, metrics). Naming (`developmentfee` vs founders) still **DOC-FR-NAMING**. Supply vs ~20M target still open.
- ZERO_COIN consolidation; shell-notify compile gate; LevelDB `max_open_files`; reindex markers/resume
- Insight-oriented Tier B scripts promoted when green; longpoll funded-node pin; workqueue 503 + once-per-episode WARNING
- Harness exit-code / getchaintips / zeronode null guards

---

## Full descriptions

### Stable subsidy arithmetic

**Done in tree.** `GetBlockSubsidy` uses integer zats (10 ZER pre fee-start; `108 * COIN / 10` after). Founders **`GetFoundersRewardAmount(subsidy)` = `subsidy * 75 / 1000`** (trunc toward 0), used by miner, `ConnectBlock`, GBT, zeronode payments/budget, and metrics. Tests: `main_tests.cpp`, `test_foundersreward.cpp`. Schedule text: **ZERO_COIN.md**. Remaining: **DOC-FR-NAMING**; supply-target review (not the helper).

### WAL-WTXORDERED / const policy

**Done:** Incremental `wtxOrdered`; Assure-4. Continue const conversion on wallet-tx **read** paths. Line-by-line Zcash `wtxOrdered` type match stays with postponed **WAL-RPC-ACCOUNTS**.

### Helpers design (`getalldata`)

One parse/filter path for day window, `nCount`, watchonly, and datatype gates (`rpczerowallet`). `IsGetAllDataTxTooOld` shipped; remaining helpers listed under Pending **WAL-GETALLDATA-HELPERS**.

### WAL-GETALLDATA-ARG2-DEFAULT (postponed)

When arg2 omitted, today ~30y window. Proposed default **2** (7 days). Release-note risk for scripts that omitted arg2.

### WAL-GETALLDATA-NOTMODIFIED

Replace the time-keyed `-34` gate with a state-keyed one. Evaluation of the open questions:

**Key on height or tip hash?** **Height alone is wrong.** A same-height reorg (block replaced
at equal height) leaves the height unchanged while balances and History change -- the wallet
would serve a stale answer with no way to notice. Use the **tip hash**; it is 32 bytes, already
at hand under `cs_main`, and covers reorgs for free. Height is still worth carrying alongside
for logging and for the staleness check below, but must not be the key on its own.

**Wallet tx without a new block.** A tip key alone misses a wallet-visible change with no new
block: a new unconfirmed tx, a conflict, or a rescan. Key on the pair **(tip hash, wallet
change counter)**, the counter bumped wherever `mapWallet` is mutated. Either component
changing invalidates.

**20 s is the wrong axis, not merely the wrong number.** Nominal block spacing is 120 s, so a
20 s timer is both too eager (four wasted full walks per block) and unsound (it can suppress a
call that *would* have changed). Dropping the timer entirely once the state key exists is
correct: a caller polling at 1 Hz costs a key comparison per call, not a walk.

**Flurry / update-spacing floor -- recommend NOT adding one initially.** A minimum store-update
spacing (30-60 s) only helps if tip updates genuinely arrive in bursts. During IBD or a deep
reorg they do, but the cost there is dominated by block processing, not by this RPC, and a
floor would make the wallet *deliberately* stale during exactly the window a user is watching.
Add it only if a burst is measured; if added, it belongs on the **cache refresh**, not on the
answer -- serve the cached body immediately and refresh in the background.

**Mid-update tip change -- already handled, no work needed.** `getalldata` takes
`LOCK(cs_main)` at `rpczerowallet.cpp:2075` and holds it for the whole body, so the tip is
frozen for the duration of a call. The snapshot cannot tear. Read the key **inside** the same
lock that produces the answer and the cache entry is consistent by construction. (This is worth
stating explicitly because `FIX-WIT-WALK-UNLOCK` proposes dropping `cs_main` during the witness
walk -- if that ever extends here, the tear becomes real and the key must be re-read and the
result discarded on change.)

**Slow safety refresh -- recommend yes, 5-10 min.** Justification: the state key is only as good
as the counter bumps feeding it. A missed bump (a new `mapWallet` mutation path added later
without touching the counter) turns into a wallet that silently never updates, which is a worse
failure than a slow one. A forced full refresh every 5-10 min bounds that blast radius to one
interval at negligible cost -- roughly one extra walk per 3-5 blocks. Treat it as a **latent-bug
backstop**, not a correctness mechanism, and log when it fires with a changed result: that log
line is the signal that a bump is missing.

**Warn on abnormally fast tip movement.** Nominal spacing is 120 s. If consecutive tip changes
arrive **under 10 s** apart outside IBD, something is wrong -- a reorg storm, a misconfigured
local miner, a peer feeding a bad chain -- and it is worth one rate-limited `LogPrintf` naming
the interval and both hashes. Keep it cheap and non-fatal: record the previous tip time next to
the cache key, compare on update, and suppress repeats (log at most once a minute) so a genuine
storm does not itself become the load. Do **not** gate serving on it; the warning is diagnostic
only. Explicitly skip while `IsInitialBlockDownload()` -- fast tips are normal there.

**FIX-WIT-WALK-UNLOCK -- analysed, NOT RECOMMENDED.** Status: an idea, examined and found to
have no viable operating point (see the restart arithmetic below). Not required for anything;
nothing depends on it. Recorded here so the analysis is not repeated, not as scheduled work.

**Analysis and recommendation.**

*What it proposes.* Drop `cs_main` during the full-height `BuildWitnessCache` walk
(`wallet.cpp:1664` and the `ChainTip` paths), aborting and restarting if the tip moves. The
motivation is R5c: while the walk holds `cs_main`, a mid-`-33` reorg is unreachable, so that
path cannot be tested or exercised. It is marked **product, not test-only**, risk **Med**.

*Why it is genuinely attractive.* On a fat wallet the walk is long. Holding `cs_main` for its
duration blocks block connection, RPC, and P2P tip advance -- the node is effectively frozen
while rebuilding. That is a real availability cost, and it is why the item exists.

*Why it is riskier than it looks.* `cs_main` is not merely protecting the tip pointer here; it
is what makes "the chain did not move under me" true for everything the walk touches --
`chainActive`, block index lookups, and the coins view the witness data is derived against.
Releasing it converts one long stall into a family of interleavings, and the failure mode is
silent wrong data rather than a hang.

*Interaction with the getalldata cache.* Today `getalldata` holds `LOCK(cs_main)` across its
whole body (`rpczerowallet.cpp:2075`), so a cache keyed on (tip hash, wallet counter) read
inside that lock is consistent by construction. If WALK-UNLOCK's pattern spreads to this path,
the cache becomes **actively harmful**: it would persist a torn answer instead of merely
recomputing one, and every later poll would serve the bad snapshot until the key changed.

*Recommendation: proceed, but not as a single change, and not into the cache path.*

1. **Keep the two items separate -- with an enforced invariant, not just a convention.**
   WALK-UNLOCK is a witness-rebuild concern; NOTMODIFIED/W5/W6 are a wallet-RPC concern. They
   must not land in the same release, and the separation needs to survive someone who has not
   read this entry:

   - **Invariant to state and hold:** the getalldata cache key is only valid if it is read
     under the same `cs_main` acquisition that produces the answer. `getalldata` takes
     `LOCK(cs_main)` at `rpczerowallet.cpp:2075` and holds it for the whole body.
   - **Enforcement:** put `AssertLockHeld(cs_main);` immediately before the cache-key read and
     the cache store. There is currently **no** `AssertLockHeld` anywhere in
     `rpczerowallet.cpp`, so this is new. If a future change drops the lock mid-body, a debug
     build aborts at the exact site instead of silently caching a torn answer.
   - **Comment the coupling at both ends:** at the cache site, that WALK-UNLOCK's pattern must
     not be extended here without the safeguards below; in `BuildWitnessCache`, that
     `getalldata` depends on whole-body `cs_main`.
   - **Sequencing:** build the cache first, while the lock discipline is still trivially
     correct. WALK-UNLOCK afterwards, gated, with the tests below already in place.
2. **Abort-and-restart, never resume -- and two concrete hazards that make "restart" harder
   than it sounds.** Reading `CWallet::BuildWitnessCache` (`wallet.cpp:1667`) shows the walk is
   not merely tip-dependent:

   - **`LOCK2(cs_main, cs_wallet)`.** Unlocking means releasing **both**. Dropping only
     `cs_main` while holding `cs_wallet` still blocks every wallet RPC, so it buys much less
     availability than the item implies; dropping both exposes the wallet as well as the chain.
   - **`wtxScan` holds raw pointers into `mapWallet`** (`wallet.cpp:1351`, selected once and
     reused every height). `mapWallet` is a `std::map`, so insertions are safe, but there are
     **27** `mapWallet.erase` / `mapWallet[...]` sites in `wallet.cpp`. Any erase during an
     unlocked window dangles those pointers and the walk dereferences freed memory -- a
     use-after-free, not a stale read. **Assurance:** on relock, either re-run
     `SelectWalletTxsForWitnessScan` (simple, costs one pass) or hold a generation counter on
     `mapWallet` and restart if it moved. Re-running is preferable: it is obviously correct and
     the walk already pays that cost once.
   - **Loop advance is `chainActive.Next(pblockindex)`.** After a reorg `pblockindex` can be on
     a stale branch, where `Next()` returns null and the walk silently *stops early* rather
     than failing -- a partially built cache that looks complete. **Assurance:** on relock,
     confirm `chainActive.Contains(pblockindex)` before continuing; if false, restart from the
     new tip rather than trusting `Next()`.
   - **Restart means restart:** discard partial witness state, do not resume. Resuming a
     partially built cache across a reorg is the case most likely to produce
     plausible-but-wrong witnesses, which is silent and consensus-adjacent.
3. **Bound by elapsed time, not restart count -- and the restart model itself does not hold.**

   *Correcting the inputs first.* An earlier pass cited M-WAL-RESCAN-FAT's **11.9 h** as the
   walk cost. That is the **rescan** (`ScanForWalletTransactions`, genesis to tip, ~59 blk/s).
   The witness walk inside that same measure was **2009 ms over ~12.8k blocks**. Mixing them
   overstates the walk by four orders of magnitude.

   *Derived per-block walk cost*, from M-WAL-WITNESS-TIP-AB (1441 blocks, fat wallet):

   | Mode | Measured | Per block |
   |------|----------|-----------|
   | stock (`scan_txs=801619`) | 7659 ms | **~5.32 ms** |
   | NOTEIDX (`scan_txs=1403`) | 220 ms | **~0.153 ms** |

   Sanity check: 12.8k blocks x 0.153 ms predicts **2.0 s**, and M-WAL-RESCAN-FAT measured
   **2009 ms**. The model reproduces an independent measurement, so the extrapolations below
   are grounded rather than invented.

   | Walk span | stock | NOTEIDX |
   |-----------|-------|---------|
   | tip window (1.4k blk) | 7.7 s | 0.22 s |
   | end walk (12.8k blk) | 68 s | 2.0 s |
   | 100k blk | 8.9 min | 15.3 s |
   | full chain (2.52M blk) | **3.7 h** | **6.4 min** |

   *The paradox: abort-and-restart cannot converge once the walk exceeds block spacing.*
   Spacing is **120 s**. A walk of duration **T** that restarts on every tip arrival faces the
   same T again. Modelling tip arrivals as Poisson at 1/120 s, P(clean run) = exp(-T/120):

   | Walk | T | P(clean) | E[attempts] | E[total work] |
   |------|---|---------:|------------:|--------------:|
   | tip, NOTEIDX | 0.22 s | 0.998 | 1.00 | 0.2 s |
   | tip, stock | 7.7 s | 0.938 | 1.07 | 8.2 s |
   | 100k, NOTEIDX | 15.3 s | 0.880 | 1.14 | 17.4 s |
   | end walk, stock | 68 s | 0.567 | 1.76 | 120 s |
   | full, NOTEIDX | 384 s | 0.041 | **24.6** | **2.6 h** |
   | 100k, stock | 532 s | 0.012 | **83.9** | **12.4 h** |
   | full, stock | 13386 s | ~0 | **~10^48** | **effectively never** |

   Two conclusions follow, and both are counter-intuitive:

   - **A restart *count* cap is inert exactly where it is safe and fatal exactly where it is
     needed.** For T under ~15 s it is never reached (E[attempts] ~1.1). For the full stock walk
     it is exhausted immediately -- and capping there is arguably the *correct* behaviour, since
     retrying is hopeless. So the cap never does what it was written for: it is not a livelock
     guard, it is a disguised "give up" switch.
   - **The expensive cases are precisely the ones that must not unlock at all.** Full stock walk
     under abort-and-restart is unachievable, not slow. Unlocking there does not trade
     availability for latency -- it trades a 3.7 h stall for *never finishing*.

   *Recommendation.*

   - **Unlock only when T is comfortably below spacing.** Estimate T up front from
     `(endHeight - startHeight) x per-block cost` and the NOTEIDX flag, both known before the
     walk starts. Unlock only if the estimate is under ~30 s (P(clean) > 0.78). Otherwise keep
     the current `LOCK2` hold: a bounded stall beats non-completion.
   - **Bound cumulative unlocked time, not attempts.** Budget ~2x the single-attempt estimate.
     On exceeding it, finish under the lock and log why.
   - **Progress high-water mark as the livelock signal.** If two consecutive attempts do not
     advance the furthest height reached, stop retrying and finish locked. This scales where a
     count does not.
   - **NOTEIDX changes the answer by 35x** and moves the full walk from "never" to 6.4 min.
     Whether unlocking is worth doing at all should be decided *after* NOTEIDX is the default,
     not before -- it may remove the motivation entirely.
   - **Paradoxical case worth stating:** making the walk faster (NOTEIDX) makes unlocking
     *less* necessary, while making it slower (stock, fat wallet, full rebuild) makes unlocking
     *impossible*. There is no regime where abort-and-restart unlocking is both necessary and
     workable, unless restart cost is decoupled from walk cost (resume-with-validation rather
     than restart-from-scratch) -- which item 2 rejects as unsafe. **That tension is the core
     finding: the item as specified may have no viable operating point.**

4. **Re-validate, do not assume.** After each unlock/relock, re-read the tip hash and confirm
   the block index entries the walk depends on are still on the active chain -- not just that
   the height matches. A same-height reorg is exactly the case that passes a height check and
   fails a hash check.
5. **Gate it.** Ship behind a flag defaulting to the current locked behaviour, as with
   `-walletwitness`. It is a Med-risk change to consensus-adjacent wallet state with no
   automated coverage of the reorg path it exists to enable.
6. **Test the thing it unblocks.** The stated purpose is making mid-`-33` reorg reachable. If
   the change lands without a regtest case that actually drives a reorg during a rebuild, it
   has added risk and delivered none of its justification.

*Build tests first? Partly -- and the split matters.*

Tests-first is right in principle but **R1-R3 and R6 cannot be written against today's build**:
the walk holds `LOCK2(cs_main, cs_wallet)` for its duration, and `invalidateblock`
(`rpc/blockchain.cpp:283`) needs `cs_main`, so a reorg RPC simply blocks until the walk
finishes. The interleaving is not merely hard to hit -- it is unreachable by construction.
Writing those tests first would produce suites that pass trivially and prove nothing, which is
worse than not having them: they would look like coverage.

What *can* be built first -- checked against the current implementation, not assumed:

| Candidate | Runs today? | Finding |
|-----------|-------------|---------|
| **Differential oracle** (from-scratch vs incremental witnesses) | **Yes** | Pure function of final chain state, no concurrency. `ClearNoteWitnessCache` (`wallet.cpp:1242`) and `RebuildWitnessCacheForChainTip` (`:1657`) give the two halves; witness state is directly assertable (`witnessHeight`, `witnesses`), with precedent in `WalletTests.CachedWitnesses*`. Passes today and **should** -- it is a correctness baseline, not a WALK-UNLOCK test |
| **Timing baseline** (per-block walk cost, stock vs NOTEIDX) | **Yes** | Pure measurement. Would confirm or correct the 5.32 / 0.153 ms per-block figures on regtest rather than extrapolating from one mainnet window |
| **R4** (dangling `wtxScan` under ASan) | **No -- vacuous today** | The race is impossible: the walk holds `LOCK2(cs_main, cs_wallet)` (`wallet.cpp:1670`) and every `mapWallet.erase` takes `cs_wallet` (checked `:2417/:2421`, `:3497/:3505`). A test would pass while asserting nothing. It only becomes meaningful in an unlocked build |
| **R5** (livelock bound / estimator) | **No -- nothing to test** | There is **no** estimator in the tree: zero matches for any walk-cost estimate in `wallet.{h,cpp}`. The inputs exist (`IsWitnessNoteIndexEnabled`, start/end heights are locals) but the function does not. Writing the test first would mean writing the estimator first, for a feature now judged infeasible |

**So: of the four, two would pass today and two would be vacuous or unwritable.** The two that
work -- the differential oracle and the timing baseline -- are worth having **independently of
WALK-UNLOCK**: the oracle is a general witness-correctness check, and the baseline replaces an
extrapolation with a measurement. The two that do not work are only meaningful for a design
that the analysis above shows has no viable operating point.

What must wait for the unlocked build: **R1, R2, R3, R6, R7**. Write them against the unlocked
build *and* verify each fails against a deliberately broken variant (for R2: an implementation
that compares heights instead of hashes). A scenario that has never failed has not been tested.

*Test plan -- provoking the gaps, not just asserting the happy path.*

The whole justification for WALK-UNLOCK is making a mid-rebuild reorg reachable. Today it is
unreachable, so **none of these scenarios can fail today** -- they must be written against the
unlocked build and must be shown to fail against a deliberately broken variant, or they prove
nothing.

Existing infrastructure to build on: `qa/rpc-tests/invalidateblock.py`, `mempool_reorg.py`,
`reorg_limit.py`, `wallet_anchorfork.py` already drive reorgs via `invalidateblock`; regtest
generate is (48,5) so blocks are cheap.

| # | Scenario | Provokes | Assertion |
|---|----------|----------|-----------|
| R1 | `invalidateblock` on the tip while a rebuild is walking | tip moves under the walk | rebuild restarts and completes; witnesses match a from-scratch rebuild on the final chain |
| R2 | Same-height reorg (invalidate tip, mine a different block at the same height) | height-check anti-pattern | must restart. A build that only compares heights passes R1 but fails R2 -- this is the discriminating case |
| R3 | Deeper reorg (invalidate N blocks, mine N+1 on the fork) | stale `pblockindex`; `chainActive.Next()` returning null | walk must not stop early with a partial cache reported as complete |
| R4 | Wallet tx erased during the unlocked window (conflicted tx removed) | dangling `wtxScan` pointers | no use-after-free; run under ASan. `--enable-asan` already exists in `configure.ac` |
| R5 | Tip advancing continuously for longer than the walk | livelock / restart bound | completes via the elapsed-time budget and falls back to a locked walk; never spins forever |
| R6 | Reorg arriving between the last height and the `initWitnessesBuilt` flag set | half-set state visible to RPC | `-33` gate stays consistent; no RPC observes "built" against the old chain |
| R7 | `getalldata` polled throughout R1-R3 | cache poisoning (item 1) | never returns a body whose key does not match the final chain |

*Automation.*

- **Deterministic driver, not sleeps.** A regtest python test that starts a rebuild on a wallet
  large enough to make the walk take seconds, then issues `invalidateblock` / `generate` from a
  second connection. **The observable signal is the `-33` gate**, not a status field:
  `fBuildingWitnessCache` lives in `rpc/server.cpp:37` and is only surfaced by dispatch
  throwing `RPC_BUILDING_WITNESS_CACHE` (`server.cpp:453,462`) on blocked RPCs, while the
  status allowlist stays available. So the driver polls an allowlisted RPC and treats "a
  wallet RPC now returns -33" as "rebuild in progress". Timing-based tests here will be flaky;
  gate on that observed state, as `contrib/perf/ops-campaign.sh` does.
- **A debug hook is required.** These races are not reliably reachable from outside. Add a
  test-only knob (`-walletwitnessteststall=<ms>`, compiled under the existing `--enable-perf`
  gate) that sleeps inside the walk at a chosen height, so the reorg lands in the window every
  time. Without it R2/R4/R6 are luck, not tests. Precedent exists:
  `SetGetAllDataInFlightForTest` in `rpczerowallet.cpp` is exactly this pattern.
- **Differential oracle.** For each scenario the assertion is "witnesses equal a from-scratch
  rebuild on the final chain". That comparison is the real test; everything else is setup.
- **ASan run in CI for R4.** `--enable-asan` exists; the use-after-free class is invisible
  otherwise.
- **Record as `M-WIT-REORG-*`** in Measures with the campaign that produced them, so a later
  regression has a baseline to diff against.

*If it is deferred instead:* nothing is lost on the cache side. The current lock discipline is
what makes NOTMODIFIED simple, so deferring WALK-UNLOCK is the cheaper sequencing.

**Decrypt cost is the prize.** The History path decrypts note ciphertexts on every call
(`rpczerowallet.cpp` ~218-240) to recover amount and memo. Between blocks that is pure
re-derivation. Caching the assembled answer removes it entirely for the common poll.

Supersedes part of W5's motivation; W5's split still matters for the first call after a change.

### WAL-GETALLDATA-W5

Split tip poll: balances (datatype **1**) on timer; full History on user action or every Nth tick. Complementary to soft **-34** coalesce. Revisit after soak; decide before W6.

### WAL-GETALLDATA-CACHE (W6) / W1 / W4

In-process tip+dirty cache (after W5). W1: merge History key insert into balance walk. W4: IVK decrypt review.

### WAL-GETALLDATA-LEGACY-SCOPE

Keep RPC; do not grow kitchen-sink without datatype gates. Do not undo S4--S8 / W2 / const walks without replacement.

### TST-01 / `getalldata_scenario`

Exclusive Boost: empty-wallet gates (20 cases in `rpc_zero_exclusive_tests.cpp`). Ext scenario:
populated wallet (`qa/rpc-tests/getalldata_scenario.py`). Both in tree and running.

**Ready now, has a consumer:** `getsupply` is registered (`rpc/client.cpp`, `rpc/zeronode.cpp`)
but has no test. Supply is the open **~20M ZER** question in the release/docs track, so a
`getsupply` case pays for itself immediately. **Defer:** `zs_*` and further sapling variants --
no waiting consumer.

### TST-03 / zeronodestats

**Ready now, has a consumer:** `zeronodestats` is cited in **public** `ZERO_COIN.md` as the
operator path to `chainStats.developmentfee` (the founders carve), and is already exercised by
**`qa/rpc-tests/zeronode_coinbase.py`** (Tier **B pass**; listed in `qa/pull-tester/rpc-tests.sh`
lines 77 and 170, and in `qa/rpc-tests/test_tier_inventory.csv`). Arg validation and the
`chainStats` shape are worth locking down because a public document points users at them.

**The "wider matrix" -- corrected.** An earlier pass counted JSON *field* names
(`zeronodepaymentzats`, `zeronodelist`, the budget fields) as if they were RPCs. They are keys
inside `zeronodestats` output, not dispatchable commands. The real registered surface in
`src/rpc/zeronode.cpp` is **16 RPCs**, and coverage is much better than that pass suggested:
`src/test/rpc_zeronode_tests.cpp` is an **18-case Boost suite** covering 15 of the 16.

| RPC | Covered by | Kind |
|-----|------------|------|
| `createzeronodekey` | Boost + `zeronode_startalias.py` | trivial: key gen |
| `getzeronodecount` | Boost | trivial: counter read |
| `getzeronodeoutputs` | Boost | wallet-dependent |
| `getzeronodestatus` | Boost (throws-when-not-zeronode) | state-dependent |
| `getzeronodewinners` | Boost | payment schedule |
| `listzeronodeconf` | Boost + `zeronode_startalias.py` | trivial: conf echo |
| `listzeronodes` | Boost | list walk |
| `startalias` | Boost (param validation) + `zeronode_startalias.py` | mutating |
| `startzeronode` | Boost (param validation) | mutating |
| `zeronode` | Boost + `zeronode_coinbase.py` + `zeronode_startalias.py` | dispatcher |
| `zeronodeconnect` | Boost (param validation) | network |
| `zeronodecurrent` | Boost | trivial: single lookup |
| `zeronodedebug` | Boost | trivial: status string |
| `zeronodestats` | Boost + `zeronode_coinbase.py` | aggregate; public doc points here |
| `znsync` | Boost + `zeronode_startalias.py` | sync state |
| **`getzeronodescores`** | **NONE** | last-N-blocks score list |

**Consumers -- corrected.** An earlier pass searched only Zero400 and ZeroPerf and concluded
these RPCs had no consumer beyond a document mention. That was wrong: it never searched the
desktop wallet. **Zerowallet (`~/Work/ZK/zerowalletmac/src/rpc.cpp`) calls them directly.**

| RPC | Zerowallet call site | Also |
|-----|---------------------|------|
| `zeronodestats` | `rpc.cpp:687` | public `ZERO_COIN.md`; `zeronode_coinbase.py` |
| `listzeronodes` | `rpc.cpp:191` | Boost suite |
| `getzeronodeoutputs` | `rpc.cpp:181` | Boost suite |
| `getalldata` | `rpc.cpp:366` | the W5 / NOTMODIFIED subject |
| `getsupply` | `rpc.cpp:761` | the TST-01 target; supply review |
| `getzeronodescores` | **not called** | no consumer anywhere |

This changes the priority argument. `zeronodestats` and `listzeronodes` are not
documentation-only curiosities -- they are live dependencies of the shipped desktop wallet, so
their output **shape** is a compatibility surface. `getalldata` and `getsupply` being wallet
callers also confirms the NOTMODIFIED work and the TST-01 `getsupply` case have real consumers.

Zerowallet's full RPC surface (from `rpc.cpp`): `getinfo`, `getblockchaininfo`, `getnetworkinfo`,
`getnetworksolps`, `getmininginfo`, `getnewaddress`, `getaddressesbyaccount`, `listunspent`,
`listtransactions`, `getalldata`, `getsupply`, `z_getnewaddress`, `z_listaddresses`,
`z_listunspent`, `z_gettotalbalance`, `z_sendmany`, `z_getoperationstatus`, `z_importkey`,
`z_exportkey`, `z_validateaddress`, `z_setmigration`, `z_getmigrationstatus`, `zeronodestats`,
`zeronodepayment`, `listzeronodes`, `getzeronodeoutputs`, `stop`.

**Revised recommendation.** TST-03 is nearly done already -- 15 of 16 covered. The remaining
work is small and specific:

1. **Coverage gap closed.** `rpc_getzeronodescores_param_validation` added to
   `src/test/rpc_zeronode_tests.cpp` -- the suite is now **19 cases covering all 16** zeronode
   RPCs. Verified: 19/19 pass.
2. **`getzeronodescores` has a real bug the new test documents.** It parses its optional
   argument with `std::stoi` inside `try { } catch (const boost::bad_lexical_cast &)`.
   `std::stoi` throws `std::invalid_argument` / `std::out_of_range`, never
   `boost::bad_lexical_cast`, so the handler is dead. Confirmed by compiling the actual
   overloads. The server's outer `catch (const std::exception&)` (`rpc/server.cpp:416`) turns
   the escape into a generic `RPC_PARSE_ERROR`, so the node does not crash -- the diagnostic is
   simply wrong and the intended handler never runs. `std::invalid_argument` derives from
   `std::logic_error`, **not** `std::runtime_error`, so the new assertion is deliberately on
   `std::exception`; tightening it to `runtime_error` after the catch is fixed is the
   regression signal. **Lowest-risk RPC to fix:** no consumer calls it, including Zerowallet.
3. **Nothing else is urgent.** The budget RPCs named in the earlier pass are not RPCs.
   Superblock and budget payments remain spork-gated and off, so there is still no reachable
   behaviour to assert there.

### OPS-TOR-COMPILE-OUT (postponed)

Optional compile-out of Tor control. Runtime onion already off by default. Do not couple to I2P.

### OPS-I2P (postponed)

Track ecosystem only. No Zero implementation in this stage.

### Upstream PR ideas (node)

| Candidate | Note |
|-----------|------|
| Longpoll funded-node pin | Zero Ext already pins; useful upstream pattern |
| Work-queue reject logging | Zero: **503** + WARNING once per full episode |
