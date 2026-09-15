# Changes made to the main tree from ZeroPerf

**Record of `src/` edits originating in this tree.** They are Zero400-owned
code (`POLICY.md` S7.1); this file exists so the product tree can review them
as a set rather than discovering them in a diff.

**Status: uncommitted in the ZeroPerf working tree**, 2026-09-10.

## 1. Equihash solver default: `default` -> `tromp`

| File | Change |
|------|--------|
| `src/miner.cpp:544` | `GetArg("-equihashsolver", "tromp")` + rationale comment |
| `src/miner.cpp:552` | **New parameter guard**: falls back to the reference solver when the chain is not (192,7) |
| `src/init.cpp:551` | Help text names both solvers and the real default |
| `src/metrics.cpp:258` | Reported default matches the effective one |
| `src/test/miner_tests.cpp` | New case `equihashsolver_default_and_param_guard` (+51 lines) |

Rationale, evidence and the mutation test:
`test-logs/tromp-default-20260909/FINDINGS.md`. **Needs a release note** --
this changes what every miner runs by default.

## 2. `generate` RPC solver messaging

`src/rpc/mining.cpp:218` -- `generate` calls `EhBasicSolveUncancellable`
directly and never consults `-equihashsolver`, but logged nothing, so the two
mining paths were silently inconsistent. Now logs in the same shape as
`BitcoinMiner`, stating that the flag does not apply.

## 3. P1 prototype: proof-verification counters

| File | Change |
|------|--------|
| `src/main.h` | `PerfProofCounters` struct + `LogPerfProofCounters()`, inside the existing `ZERO_PERF` block |
| `src/main.cpp` | `PerfProofTimer` RAII + `PERF_PROOF_TIMER()` macro; four call sites; logger called from `ConnectBlock` |

**Compiled out entirely without `ZERO_PERF`** -- verified: zero symbols and
zero format strings in the default object. Detail:
`test-logs/p1-proto-20260910/FINDINGS.md`.

## 4. Naming correction (test tooling, not `src/`)

`contrib/perf/performance-measurements.sh:86,116` wrote `$DATADIR/zcash.conf`;
Zero requires `zero.conf`. The node never started and **the script exited 0**.
Inherited filename from the Zcash original.

### Naming sweep, 2026-09-10

Searched `contrib/perf/`, `qa/`, `contrib/`, `zcutil/` for Zcash-era names that
are wrong for Zero:

| Pattern | Result |
|---------|--------|
| `zcash.conf` | **1 real bug**, fixed above. No others |
| `wallet.dat` (Zero uses `wallet.zero`) | none |
| `zcash-cli`, `zcashd` as binaries | none |
| `bitcoin.conf` | none |
| `~/.zcash-params` | **Correct, keep.** Zero shares Zcash's params directory; `zeropaths.py:39` and `README.md` both document it as the product default |
| `qa/zcash/` paths | **Correct, keep.** Real directory |
| `zcash_rpc*` shell function names in `performance-measurements.sh` | Cosmetic only -- internal function names, no behaviour. Left alone |
| `zcash-loadblk`, `zcash-scriptch` thread names | **Correct, keep.** Actual thread names in the binary |

**One functional defect in the whole tree**, and it was found by running the
tool rather than by reading it -- the script had been present and "passing"
for as long as it has existed.
