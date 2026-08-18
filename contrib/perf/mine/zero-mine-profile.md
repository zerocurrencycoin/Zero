# Live CPU miner profile

Spot capture of the operator mainnet `zerod` while `setgenerate true 1` was hashing Equihash (192,7). Not a lab campaign, not `ops-validate.sh mine` (that path is isolated regtest (48,5) `generate`).

Raw `sample` output lives in this directory. The exclusive/inclusive tables below are from the 01:29 capture (`zerod-mine-sample-now.txt`). The four 60 s / 5 min series is `zerod-mine-sample-{1,2,3,4}.txt`.

## Capture identity

| Field | Value |
|-------|-------|
| Host time | 2026-08-18 01:29:53 -0700 |
| Tool | `/usr/bin/sample` every 1 ms, requested 60 s |
| Samples per thread | 50758 (~50.8 s of on-CPU stacks in the graph) |
| pid | 40344 |
| Binary | `/Users/walter/Work/ZK/Zero400/src/zerod -daemon` |
| Datadir | `~/Library/Application Support/zero` |
| RPC | 23811 |
| Launch time | 2026-08-18 00:32:43 -0700 (~57 min up at sample) |
| Arch | ARM64 macOS 26.3 |

## Four-interval series

Same pid, still `generate=true` `genproclimit=1`, start-to-start 5 min, 60 s `sample` each. Taken 2026-08-18 07:57-08:13 -0700 (~7.4 h up). Every interval is 100% of the hasher thread in `BitcoinMiner` -> `EhOptimisedSolve`.

| File | Host start | samples/thread | CPU% | RSS | tip | `localsolps` | `networksolps` | bytes |
|------|------------|---------------:|-----:|----:|----:|-------------:|---------------:|------:|
| `zerod-mine-sample-1.txt` | 07:57:54 | 50735 | 97.5 | 3.0 GiB | 2522392 | 0.029 | 903 | 709K |
| `zerod-mine-sample-2.txt` | 08:02:54 | 51039 | 98.7 | 5.4 GiB | 2522392 | 0.029 | 903 | 547K |
| `zerod-mine-sample-3.txt` | 08:07:54 | 50977 | 99.9 | 5.0 GiB | 2522393 | 0.029 | 859 | 585K |
| `zerod-mine-sample-4.txt` | 08:12:54 | 50926 | 99.6 | 2.5 GiB | 2522393 | 0.029 | 859 | 564K |

Exclusive buckets as % of miner thread. Mix moves with Equihash round; memcmp+partition stay the majority.

| Capture | memcpy/memcmp | partition | blake2b | ExpandArray | introsort self |
|---------|--------------:|----------:|--------:|------------:|---------------:|
| 01:29 `now` | 41.7 | 19.3 | 27.9 | 3.9 | 2.5 |
| 1 | 48.7 | 25.6 | 15.8 | 1.7 | 3.3 |
| 2 | 49.0 | 25.6 | 15.9 | 1.7 | 3.1 |
| 3 | 52.5 | 26.2 | 12.0 | 1.3 | 3.1 |
| 4 | 45.5 | 24.0 | 20.0 | 2.5 | 3.1 |

Top exclusive leaf in all five files is `_platform_memcmp` (27-42%). Next is either `std::__partition<TruncatedStepRow<70>>` or `blake2b_compress_ref`.

## Live miner at 01:29 capture

`generate=true`, `genproclimit=1`. Coinbase target is `mineraddress=t1eFjPnpqZgoM7QWrvLN6P1qC1Df65dBAXT` in the operator `zero.conf` (startup-only; node was restarted once to pick it up). `gen=1` is **not** persisted; hashing stops on `setgenerate false` or process exit.

| Field | Value |
|-------|-------|
| Process CPU | ~97% of one core |
| RSS | ~1 GiB |
| `sample` physical footprint | 7.8G (peak 12.1G) |
| `localsolps` | 0.028 |
| `networksolps` | 1124 |
| difficulty | ~4200 |
| tip | 2522173 (2522133 when hashing started) |
| peers | 16 |
| `proof-of-work found` | none |

One (192,7) `OptimisedSolve` is ~50 s on this host (`ops-validate.sh solveeq`). The network finds blocks faster than that, so a single CPU hasher is expected to lose. `debug.log` kept emitting `CreateNewBlock` / `Running ZeroMiner` on each new tip or mempool change (coinbase-only templates, up to 12 tx). That is stale-work rebuild, not a crash.

Operator conf also has Insight flags (`experimentalfeatures=1`, `insightexplorer=1`), `rpcservertimeout=60`, `dbcache=2048`. Do not copy `rpcpassword` into this note.

## How to read the percents

32 threads were sampled. Each has 50758 samples. Process-wide "Sort by top of stack, same collapsed" sums **all threads** (about 1.62M leaf samples). Idle syscalls dominate that table and are not miner work.

With `genproclimit=1`, process CPU is the `zcash-miner` thread. **% of miner thread** = leaf samples / 50758. That is also **% of process CPU**.

**Exclusive** is self time: the leaf of the stack. That is where the core actually was.

**Inclusive** is a call-graph node and its children. Do not add exclusive rows to inclusive rows. Do not add nested `std::__introsort` counts: the same recursive sort appears at many depths.

The collapsed exclusive table omits functions with fewer than 5 samples. Sum of listed leaves is 1624103 vs 32 * 50758 = 1624256.

macOS `sample` DWARF noise ("Attempt to set cursor outside bounds" on `.a` members) is symbolication, not a miner bug.

## Threads

32 threads, each 50758 samples:

| Count | Name |
|------:|------|
| 1 | main (`DispatchQueue_1`) |
| 13 | `zcash-scriptch` |
| 1 | `zcash-scheduler` |
| 1 | `zcash-http` |
| 6 | `zcash-httpworker` |
| 2 | unnamed |
| 1 | `zero-obfuscation` |
| 1 | `zcash-txnotify` |
| 1 | `zcash-net` |
| 1 | `zcash-addcon` |
| 1 | `zcash-opencon` |
| 1 | `zcash-msghand` |
| 1 | `zcash-wallet` |
| 1 | `zcash-miner` |

Main thread: ~99.6% in `MilliSleep` / `__psynch_cvwait`. Script, HTTP, net, wallet, and scheduler threads are the same wait syscalls. They do not show as compute in this window.

`zcash-miner` spent 50750 / 50758 samples in `BitcoinMiner` -> `EhOptimisedSolve`. That is 99.98% of the hasher thread.

## Exclusive CPU by function

Leaf samples from the process-wide collapsed table, reported as percent of the miner thread (50758). Sapling/pairing leaves are other threads leaking into that table (~1.7% of 50758); they are not miner work.

Busy exclusive leaves totaled 52827; wait exclusive leaves totaled 1571276.

| Function | Samples | % of miner / process CPU |
|----------|--------:|-------------------------:|
| `_platform_memcmp` | 13756 | 27.1 |
| `blake2b_compress_ref` | 12769 | 25.2 |
| `std::__partition<TruncatedStepRow<70>>` | 7569 | 14.9 |
| `_platform_memmove` | 3663 | 7.2 |
| `memcmp` (dyld stub) | 3070 | 6.1 |
| `std::__partition<FullStepRow<518>>` | 2210 | 4.4 |
| `ExpandArray` | 2003 | 4.0 |
| `Equihash<192,7>::OptimisedSolve` (self) | 1109 | 2.2 |
| `TruncatedStepRow<70>` ctor | 810 | 1.6 |
| `std::__introsort<TruncatedStepRow<70>>` (self) | 729 | 1.4 |
| `CollideBranches<518>` | 366 | 0.7 |
| `_platform_memset` | 357 | 0.7 |
| `std::__introsort<FullStepRow<518>>` (self) | 345 | 0.7 |
| `vector<TruncatedStepRow<70>>::insert` | 325 | 0.6 |
| `bls12_381::Fr::mul_assign` | 402 | 0.8 |
| `bls12_381::Fr::square` | 310 | 0.6 |
| `_pthread_mutex_droplock` | 260 | 0.5 |
| `memcpy` (dyld stub) | 259 | 0.5 |
| `memmove` (dyld stub) | 199 | 0.4 |
| `blake2b_update` | 179 | 0.4 |
| `pthread_mutex_lock` | 175 | 0.3 |
| `std::__sort3<TruncatedStepRow<70>>` | 138 | 0.3 |
| `pthread_mutex_unlock` | 112 | 0.2 |
| `memset_s` | 111 | 0.2 |
| `CTxIn::CTxIn` | 108 | 0.2 |
| `BitcoinMiner` cancel check | 59 | 0.1 |

`TruncatedStepRow<70>` is the Equihash truncated-row sort. `FullStepRow<518>` is the full-row sort. Those sizes are (192,7) solver layout, not (48,5).

### Exclusive, grouped

| Work | Samples | % of miner |
|------|--------:|-----------:|
| `memcmp` / `memmove` / `memset` | 21184 | 41.7 |
| BLAKE2b (`blake2b_compress_ref` + `blake2b_update`) | 14162 | 27.9 |
| Equihash partition/compare | 9779 | 19.3 |
| `ExpandArray` | 2003 | 4.0 |
| other compute | 1997 | 3.9 |
| Equihash introsort (self, not callees) | 1265 | 2.5 |
| row ctor / vector insert | 1149 | 2.3 |
| sapling/pairing (other threads) | 863 | 1.7 |
| `CollideBranches<518>` | 366 | 0.7 |
| solver cancel check | 59 | 0.1 |

Almost all memcmp/partition time is Equihash sort of 70-byte truncated rows, then 518-byte full rows.

## Inclusive CPU, miner thread

Time in the function and its callees, using the **maximum** call-graph node count for that name (outermost recursive sort). `Equihash<192,7>::OptimisedSolve` is split across many `+offset` sites (24106, 9043, 6089, 4594, ...); 47.5% is the largest single node, not total solver time. Total solver time is `EhOptimisedSolve` at 99.98%.

| Function | Inclusive samples | % of miner |
|----------|------------------:|-----------:|
| `thread_start` / `_pthread_start` / `thread_proxy` | 50758 | 100.00 |
| `BitcoinMiner` | 50750 | 99.98 |
| `EhOptimisedSolve` | 50750 | 99.98 |
| `Equihash<192,7>::OptimisedSolve` (largest node) | 24106 | 47.5 |
| `std::__introsort<TruncatedStepRow<70>>` | 22457 | 44.2 |
| `std::__introsort<FullStepRow<518>>` | 5467 | 10.8 |
| `blake2b_final` (one call-site cluster) | 4358 | 8.6 |
| `ExpandArray` | 1311 | 2.6 |
| `TruncatedStepRow<70>` ctor | 787 | 1.6 |
| `std::__partition<TruncatedStepRow<70>>` (one node) | 747 | 1.5 |
| `CollideBranches<518>` | 366 | 0.7 |
| `vector<TruncatedStepRow<70>>::insert` | 325 | 0.6 |
| cancel check | 131 | 0.3 |

Do not add 47.5% + 44.2%. The truncated-row sort sits under `OptimisedSolve`. BLAKE2b also appears as siblings at other offsets.

## Process-wide wait leaves

These are summed across all 32 threads. They are not miner exclusive time.

| Leaf | Samples |
|------|--------:|
| `__psynch_cvwait` | 1411950 |
| `kevent` | 50757 |
| `__select` | 50315 |
| `__semwait_signal` | 49035 |
| `__psynch_mutexwait` | 4633 |
| `__gettimeofday` | 2089 |
| `mach_msg2_trap` | 1720 |

`__psynch_mutexwait` (4633) and `__gettimeofday` (2089) are blocking, not Equihash arithmetic. A slice of `gettimeofday` is the solver cancel check.

## Findings

1. Live CPU mining on this node is one core in `zcash-miner`, inside Equihash (192,7) `OptimisedSolve`. Other threads are idle.
2. That core's exclusive time is Equihash row sort/compare (~61% if memcmp/memmove/memset + partition + introsort self + row ctor are taken together) and BLAKE2b compress (~28%).
3. `localsolps` ~0.028 vs `networksolps` ~1124. No block found in the ~57 min window. Expected: ~50 s per solve vs a network that moves the tip many times per minute.
4. Tip advanced 2522133 -> 2522173 during hashing. Each new tip rebuilds the template (`CreateNewBlock` / `Running ZeroMiner`).
5. `ops-validate.sh mine` is not this workload. `contrib/perf/` was not used.
6. Four 60 s captures at 5 min start-to-start (07:57-08:13) match the 01:29 picture: hasher thread is entirely `EhOptimisedSolve`. Exclusive mix shifts (blake2b 12-28%, memcmp 42-53%) with solver round; RSS also swings 2.5-5.4 GiB across the four windows.

## Files

| Path | What |
|------|------|
| `mine/zero-mine-profile.md` | This note |
| `mine/zerod-mine-sample-now.txt` | 60 s `sample`, 2026-08-18 01:29:53 -0700 (649K) |
| `mine/zerod-mine-sample-1.txt` | 60 s `sample`, 2026-08-18 07:57:54 -0700 (709K) |
| `mine/zerod-mine-sample-2.txt` | 60 s `sample`, 2026-08-18 08:02:54 -0700 (547K) |
| `mine/zerod-mine-sample-3.txt` | 60 s `sample`, 2026-08-18 08:07:54 -0700 (585K) |
| `mine/zerod-mine-sample-4.txt` | 60 s `sample`, 2026-08-18 08:12:54 -0700 (564K) |
