# Gated RPC entry points: current state and the expansion plan

**Draft for the Zero400 tree. Not applied.** Verified against `src/` at
`a2a691fb3`, 2026-09-09.

## 1. Correction to the premise

The plan was described as "increase the number of gated RPCs from 2 to 4".
**Only one RPC is gated today.**

| Fact | Evidence |
|------|----------|
| One gate instantiation in the tree | `CGetAllDataInFlightGuard inFlightGuard;` at `rpczerowallet.cpp:2073`, inside `getalldata` only |
| One success marker | `MarkGetAllDataSuccess()` at `:2573` |
| `-34` is documented as `getalldata`-specific | `rpc/protocol.h:81`, `init.cpp:572` |

So the work is **1 -> 4**, not 2 -> 4, and the first step is generalising a
mechanism currently written for one caller.

## 2. What the gate does

Two independent protections in one RAII guard (`rpczerowallet.cpp:62-90`):

- **In-flight exclusion.** A second concurrent call throws `-34` rather than
  starting a second full wallet walk.
- **Time coalesce.** A call within `-rpcdatacontinue` seconds (default 20) of
  the last *success* throws `-34`, so a polling client keeps its last result
  instead of forcing a rewalk.

`-34` is soft by design: the client keeps what it has. That is what makes it
safe to apply to read-only reporting RPCs and unsafe to apply to anything with
side effects.

## 3. Candidates, and which should be gated

The Zero-unique wallet reporting surface in `rpczerowallet.cpp`:

| RPC | Line | Walks the wallet? | Gate it? |
|-----|-----:|-------------------|----------|
| `getalldata` | 2037 | Yes -- the whole point of the gate | **Already gated** |
| `zs_listtransactions` | 813 | Yes, full `mapWallet` walk | **Yes** |
| `zs_listreceivedbyaddress` | 1477 | Yes | **Yes** |
| `zs_listsentbyaddress` | 1753 | Yes | Candidate; lower traffic |
| `zs_listspentbyaddress` | 1201 | Yes | Candidate; lower traffic |
| `zs_gettransaction` | 1089 | **No** -- single txid lookup | **No.** Nothing to coalesce |
| `getsupply` | 2577 | No -- chain aggregate | **No** |

**Recommended set of four:** `getalldata` (existing) plus
`zs_listtransactions`, `zs_listreceivedbyaddress`, and one of the two
`zs_list*byaddress` pair -- chosen by which a wallet UI actually polls.

**Justification for the shape, not just the count.** The gate earns its place
where a client *polls* an expensive full-wallet walk. `zs_gettransaction` is a
point lookup, so gating it would return `-34` for a cheap call and break a
legitimate access pattern. Gating by cost, not by file membership.

## 4. Two designs

### Option A -- one guard per RPC, independent state

Each gated RPC gets its own in-flight flag and last-success timestamp.

- **Pro:** a slow `getalldata` never blocks `zs_listtransactions`; each RPC's
  coalesce window is its own.
- **Con:** four copies of the state; four places to get the RAII wrong; and it
  does not stop four *different* polls from each starting a wallet walk, which
  is the load the gate exists to bound.

### Option B -- one shared gate, keyed by RPC name (recommended)

One `cs` and a small map from RPC name to `{inFlight, lastSuccess}`, with a
single `CWalletWalkGuard(const std::string& rpcName)`.

- **Pro:** one implementation, one place to fix; adding the fifth RPC is a
  one-line registration; per-RPC coalesce windows are preserved because the
  state is per-key.
- **Con:** one lock covers registration for all of them -- negligible, since it
  is held only to read and set two fields, never across the walk itself.
- **This is the upstream-shaped answer**, matching how the current guard
  already separates "acquire" from "mark success", and it is what the
  "combining through some helper" note intended.

**Recommendation: B.** The mechanism is already RAII and already separates
acquire from mark; keying it is a smaller change than writing three more
copies, and it makes the count a configuration rather than a code change.

**Open sub-question for the owner:** should the four share **one** in-flight
slot (any wallet walk excludes any other) or **one per RPC**? Sharing bounds
total wallet load, which is the real resource; per-RPC is friendlier to a UI
that legitimately wants two different views. **Recommend per-RPC in-flight
plus a shared concurrency cap of 1** if that proves insufficient under load --
but start per-RPC, because it cannot break an existing client.

## 5. Steps

| # | Step | Note |
|---|------|------|
| 1 | Generalise the guard to `CWalletWalkGuard(name)` with per-name state | No behaviour change for `getalldata` |
| 2 | Re-point `getalldata` at it; confirm `rpc_zero_exclusive_tests` still passes | The existing tests are the regression net (`:205`, `:222`) |
| 3 | Add `zs_listtransactions`, `zs_listreceivedbyaddress`, + one | One line each |
| 4 | Extend `-rpcdatacontinue` help to say it now covers the set | `init.cpp:572` currently names `getalldata` only |
| 5 | Update `rpc/protocol.h:81` comment | Same reason |
| 6 | Add a test per newly gated RPC, mirroring the two existing `-34` assertions | Without this the gate is unpinned, as the solver default was |

**Effort: S-M.** No new mechanism, one generalisation and three registrations.
