# Every thread this node launches

Inventory 2026-09-12, `codequery raw 'threadGroup\.create_thread|boost::thread\(|std::thread\(|pthread_create' src/`
excluding `leveldb/`, `test/`, `univalue/`. Sizing and locking logic:
`CONCURRENCY.md`. This file is the census.

**17 launch sites. Sixteen are fixed-count; one is the only pool whose width a
user sets.**

## 1. Sized by configuration

| Thread | Site | Count | Sizing |
|--------|------|------:|--------|
| `ThreadScriptCheck` | `init.cpp:1366` | `nScriptCheckThreads - 1` | `-par`; `0` = auto via `GetNumCores()`, negative leaves N cores free, capped at `MAX_SCRIPTCHECK_THREADS` = 16 (`main.h:91`). **The only user-sized pool** |
| Async RPC worker | `asyncrpcqueue.cpp:179` | **1** | `addWorker()` called once (`rpc/server.cpp:311`); the multi-worker loop is commented out. See P9 |
| HTTP workers | `httpserver.cpp` | `-rpcthreads`, default **4** | Separate from the `threadHTTP` dispatcher below |

## 2. Fixed singletons

| Thread | Site | Purpose |
|--------|------|---------|
| `net` (`ThreadSocketHandler`) | `net.cpp:1782` | Socket read/write |
| `msghand` (`ThreadMessageHandler`) | `net.cpp:1791` | P2P message processing |
| `opencon` (`ThreadOpenConnections`) | `net.cpp:1788` | Outbound connection management |
| `addcon` (`ThreadOpenAddedConnections`) | `net.cpp:1785` | `-addnode` peers |
| `dnsseed` (`ThreadDNSAddressSeed`) | `net.cpp:1779` | **Conditional** -- skipped when seeding is disabled |
| `threadHTTP` | `httpserver.cpp:459` | libevent dispatcher |
| `torcontrol` | `torcontrol.cpp:760` | **Conditional** -- Tor control port only |
| `scheduler` | `init.cpp:1371` | `CScheduler::serviceQueue` |
| `ThreadShowMetricsScreen` | `init.cpp:1381` | **Conditional** -- `-showmetrics` |
| `ThreadImport` | `init.cpp:2126` | `-loadblock` / reindex. **This is `zcash-loadblk`**, the thread every sync measurement profiles |
| `ThreadCheckObfuScationPool` | `init.cpp:2278` | Zeronode maintenance |
| `txnotify` (`ThreadNotifyRecentlyAdded`) | `init.cpp:2299` | Wallet notification |
| `ThreadFlushWalletDB` | `init.cpp:2327` | **Conditional** -- wallet enabled |
| `ThreadSendAlert` | `init.cpp:2332` | Alert system |

## 3. What this census changes

**The perf picture is unaffected.** Sync is bound on `ThreadImport`
(`zcash-loadblk`) doing proof verification that no pool touches, which is why
adding cores does not help post-Sapling sync. Nothing in this list contradicts
that -- it confirms there is no verification pool to widen.

**Two are the ones that matter for concurrency risk:**

- **`ThreadScriptCheck`** is the only genuinely variable-width pool, and its
  work is transparent-script verification -- stateless, which is why it is
  safe to widen.
- **Async RPC at one worker** is load-bearing for wallet safety (P9), not a
  performance choice.

**Five are conditional** (`dnsseed`, `torcontrol`, metrics, wallet flush, and
`ThreadImport` only with import files), so a given run launches fewer than 17.

## 3a. Are the 14 fixed threads useful in this environment?

Reviewed 2026-09-12 for a **lab/measurement node and a typical operator
node**, which is what this tree cares about.

| Thread | Useful here? | Note |
|--------|--------------|------|
| `net`, `msghand`, `opencon` | **Yes** | Core P2P. A lab reindex with `-listen=0 -connect=0` still starts them |
| `addcon` | Only with `-addnode` | Idle otherwise |
| `dnsseed` | **No, in the lab** | Gated; a lab node with `-connect=0` should not seed. Already conditional |
| `threadHTTP` + HTTP workers | **Yes** | RPC is how every measurement reads height |
| `scheduler` | **Yes** | Periodic maintenance |
| `torcontrol` | **No** | Gated on `-listenonion`; runtime onion is off by default (root `TODO.md` has `OPS-TOR-COMPILE-OUT` postponed to compile it out entirely). Never starts in the lab |
| `ThreadShowMetricsScreen` | **No, in the lab** | Gated on `-showmetrics`; lab launchers pass `-showmetrics=0` |
| `ThreadImport` | **Yes -- the one being measured** | `zcash-loadblk` |
| `txnotify` | Only with wallet notification | |
| `ThreadFlushWalletDB` | Only with wallet | Lab runs use `-disablewallet` |
| `ThreadSendAlert` | **Questionable** | The alert system is the subject of `OPS-ALERT-STRIP` (postponed): P2P `alert.cpp` is slated to be gutted. A thread for a feature being removed |
| `ThreadCheckObfuScationPool` | **Questionable** | **Launched unconditionally** (`init.cpp:2278`, single site, no gate found). Zeronode maintenance on a node that may not be a zeronode |

**Two worth raising**, neither urgent:

- **`ThreadSendAlert`** exists for a subsystem already scheduled for removal.
  It should go out with `OPS-ALERT-STRIP`, not before -- removing the thread
  while `alert.cpp` remains would leave the feature half-wired.
- **`ThreadCheckObfuScationPool` is the only unconditional launch in the
  zeronode set.** Every other optional subsystem gates its thread. Worth
  checking whether it can be gated on the same condition the rest of the
  zeronode code uses; if the answer is "it has to run to discover whether
  this node is a zeronode", that is worth a comment at the launch site.

**Nothing here is a performance finding.** Sixteen mostly-idle threads cost
stack and a scheduler slot, not CPU. The reason to care is surface area: each
is a thread TSan must model and a place a lock can be taken.

## 3b. The conditional threads and how each is sized

All five are **boolean, not sized** -- present or absent, never N of them:

| Thread | Condition | Count when on |
|--------|-----------|--------------:|
| `dnsseed` | seeding enabled and not `-connect` | 1 |
| `torcontrol` | `-listenonion` | 1 |
| `ThreadShowMetricsScreen` | `-showmetrics` | 1 |
| `ThreadFlushWalletDB` | wallet enabled | 1 |
| `ThreadImport` | always created; does work only with import files or reindex | 1 |

So the **only** width decisions in the whole node are `-par`
(script check), `-rpcthreads` (HTTP), and the disabled `-rpcasyncthreads`.

## 3c. `showbsizes` / HIST / SPARK / LOGSPARK: dead code, verified

`showbsizes(r)` (`pow/tromp/equi_miner.h:405`) is the per-round bucket
observation hook the miner and the benchmark both pass. **It does nothing, in
every configuration**, and two of its three modes cannot be enabled at all.

| Macro | Intent | State |
|-------|--------|-------|
| `HIST` | print a bucket-occupancy histogram | body is `// printf(...)`, commented out |
| `SPARK` | print a unicode sparkline of occupancy | **does not compile**: uses `SPARKSCALE`, which is defined nowhere in the tree |
| `LOGSPARK` | log-scaled sparkline | same `SPARKSCALE` dependency, same failure |

**Verified**, not assumed: `codequery raw -n 'define SPARKSCALE' src/` returns
no match, and compiling the header with `-DSPARK` fails with
`error: use of undeclared identifier 'SPARKSCALE'` at `:418`.

So with none of the three defined the whole function body is preprocessed away
and every call is a no-op; with any of them defined the build breaks. This is
why adding a `showbsizes(WK)` call during the P11 refactor was harmless -- and
why removing it anyway was still right, since the equivalence argument should
not rest on the callee being dead.

**Resolution options:**

1. **Delete `showbsizes` and its hook.** The miner's lambda and the `WK`-1
   hook contract exist only to feed it. Removes ~25 lines of vendored code and
   one parameter from `EhTrompSolveRounds`. **Cost: divergence from upstream
   tromp**, which matters if the vendored copy is ever re-synced.
2. **Leave it, and say so.** One comment at `:405` recording that it is
   inert and that `SPARK`/`LOGSPARK` are broken, so the next reader does not
   try to enable them and lose an hour.
3. **Fix `SPARKSCALE` and keep it.** Only worth it if per-round bucket
   occupancy is actually wanted -- and `PERF_PROBE` in the benchmark already
   reports the `xfull`/`bfull`/`hfull` drop counters, which is the same
   diagnostic in a form that works.

**Recommendation: (2) now, (1) when the vendored copy is next touched.**
The hook costs nothing at runtime and the comment is the cheap fix; deleting
vendored code is a decision to make once, deliberately, not as a side effect
of a refactor. `PERF_PROBE` already covers the diagnostic need, so nothing is
lost either way.

## 3d. Core-count derivation, and why it differs by platform

Only **one** thread count in the node is derived from the CPU:
`nScriptCheckThreads`, via `GetNumCores()` (`util.cpp:948`), which is

    return boost::thread::physical_concurrency();

and `-par` resolution at `init.cpp:1125-1129`:

| `-par` | Result |
|--------|--------|
| `0` (default) | `GetNumCores()`, then capped at `MAX_SCRIPTCHECK_THREADS = 16` |
| negative `-n` | `GetNumCores() - n` -- leave n cores free |
| positive | used as given, still capped at 16 |
| resolved `<= 0` | `0` -- no pool; checks run on the connecting thread |

`init.cpp:1366` then creates **`nScriptCheckThreads - 1`** threads, because the
calling thread participates.

**This host, measured:** `hw.ncpu` 14, `hw.physicalcpu` 14, `hw.logicalcpu` 14,
but `hw.perflevel0.logicalcpu` **10** performance cores and
`hw.perflevel1.logicalcpu` **4** efficiency cores.

**The platform divergence that matters:**

| | macOS / arm64 (this host) | Linux / x86-64 |
|---|---|---|
| `physical_concurrency()` | 14 -- counts **P and E cores alike** | physical cores, excluding SMT siblings |
| `hardware_concurrency()` | 14 | logical cores, i.e. **2x physical** with SMT |
| Asymmetry | **Yes** -- 10 fast + 4 slow | No -- all cores equivalent |

So `-par=0` produces a **13-thread pool of unequal cores** here, and on a
16-core SMT Linux box it produces 15 equal ones. The same default means
different things, and a barrier-style workload finishes when its *slowest*
participant does.

**This is the concrete argument for the `cores/2, cap 4` proposal**
(`CONCURRENCY.md` S5.1): not that fewer threads are faster, but that
scheduling onto E-cores adds variance for work that is not the bottleneck.
**Still unmeasured** -- the experiment is designed and not run, and the
prediction recorded there is "no difference outside noise".

**Everything else is fixed or boolean.** `-rpcthreads` defaults to a literal
**4** (`httpserver.h:14`) with no core derivation at all; `-rpcworkqueue` to
16; `-genproclimit` defaults to 1 with `-1` meaning all cores, but mining is
off by default; the tromp solver is constructed `equi eq(1)`. **No other
thread count varies with the machine.**

## 3e. Measured: what a running node actually starts

**Regtest, idle, default flags, 2026-09-15.** `sample <pid>` on a live
`zerod`, Alert thread already gated off:

| Count | Thread name | Source |
|------:|-------------|--------|
| **13** | `zcash-scriptch` | `ThreadScriptCheck`, `init.cpp:1366` |
| 4 | `zcash-httpworker` | `-rpcthreads`, default 4 |
| 1 | `zcash-http` | libevent dispatcher |
| 1 | main thread | -- |
| 1 | `zcash-scheduler` | `CScheduler::serviceQueue` |
| 1 | `zcash-net` | `ThreadSocketHandler` |
| 1 | `zcash-msghand` | `ThreadMessageHandler` |
| 1 | `zcash-opencon` | `ThreadOpenConnections` |
| 1 | `zcash-addcon` | `ThreadOpenAddedConnections` |
| 1 | `zero-obfuscation` | `ThreadCheckObfuScationPool` |
| 1 | `zcash-txnotify` | `ThreadNotifyRecentlyAdded` |
| 1 | `zcash-wallet` | `ThreadFlushWalletDB` |
| 1 | unnamed | async RPC worker |
| 1 | -- | remaining unnamed |
| **29** | **total** | RSS **76.3 MB** |

**Thirteen of twenty-nine threads -- 45% -- are script-check workers on an
idle node with nothing to validate.** That is `nScriptCheckThreads - 1` where
`-par=0` resolved to `GetNumCores()` = 14.

**This is the concrete form of the objection to `-par=0`.** The problem is not
that 14 counts E-cores as equal to P-cores; it is that **13 threads are
created and parked regardless of whether any script will ever be checked.**
They exist from startup to shutdown on a node that may be doing nothing but
serving RPC.

A regtest node, a `-disablewallet` reindex lab, an explorer backend serving
`getblock` -- none of these needs 13 script-check workers, and all three are
workloads this tree runs routinely.

**What it costs:** each thread carries a stack reservation (VSZ 415 GB
reserved, RSS 76.3 MB resident -- so the resident cost is modest and the
address-space cost is large but unbacked), a scheduler entry, and a slot in
every TSan/lock-order model. The wall-time cost on an idle node is ~0.

**The proposal (`CONCURRENCY.md` S5.1, `cores/2` capped at 4) would make this
3 threads instead of 13**, and the experiment there is designed to show
whether that costs anything on the one workload where script checks matter.
Until that runs, the observation stands on its own: **the default allocates
13 workers before knowing whether any work exists.**

## 4. Not yet reviewed

| Area | Why it is out of this census |
|------|------------------------------|
| `src/leveldb/` | Vendored; its own threading (`env_posix.cc`) |
| `src/test/` | Test harness threads, not node behaviour |
| librustzcash / libsnark internals | The 2016 comment disabling multi-worker async RPC cites libsnark "which by default uses multiple threads". **Never verified here** -- whether the pinned crates spawn threads during proof verification is unknown, and it bears directly on whether widening any pool is safe |

The libsnark question is the real gap this census exposes: a thread we do not
launch and have not counted may still exist inside the proof path.
