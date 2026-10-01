# Peer and RPC operations

Notes for Zero mainnet node on macOS (Zero400 `v4.0.1`). Assessed 2026-06-10 from `zero.conf`, `debug.log`, DNS lookups, RPC, and `src/{addrman,net,main}.cpp`.

---

## Paths

| Item | Location |
|------|----------|
| Data directory | `~/Library/Application Support/zero/` |
| Config | `~/Library/Application Support/zero/zero.conf` |
| Debug log | `~/Library/Application Support/zero/debug.log` |
| Peer address DB | `~/Library/Application Support/zero/peers.dat` |
| Binaries (dev tree) | `~/Work/ZK/Zero400/src/zerod`, `zero-cli` |

---

## Default ports (mainnet)

| Service | Port | Config key |
|---------|------|------------|
| P2P | **23801** | `port` (default from `chainparams.cpp`) |
| RPC | **23811** | `rpcport` (default from `chainparamsbase.cpp`) |

Testnet: P2P 23802, RPC 23812. Regtest: P2P 23803, RPC 23813.

---

## Current `zero.conf` (assessed)

```ini
testnet=0
listen=1
server=1

rpcuser=MacZero
rpcpassword=<see zero.conf; not duplicated here>
rpcport=23811
rpcbind=127.0.0.1
rpcallowip=127.0.0.1
```

Not in file (session usage): `logips=1` (may be passed on command line: `./src/zerod -logips`).

---

## Discovery flow: assessed results

### Startup timeline (2026-06-10 03:15 UTC)

Quoted log lines in order:

```
2026-06-10 03:15:29 Bound to [::]:23801
2026-06-10 03:15:29 Bound to 0.0.0.0:23801
2026-06-10 03:15:44 init message: Loading addresses...
2026-06-10 03:15:44 Loaded 3073 addresses from peers.dat  3ms
2026-06-10 03:15:55 Loading addresses from DNS seeds (could take a while)
2026-06-10 03:15:56 10 addresses found from DNS seeds
```

Interpretation:

| Step | Time offset | What happened |
|------|-------------|---------------|
| P2P bind | T+0s | Dual-stack listen on 23801 (`::` and `0.0.0.0`). |
| `peers.dat` load | T+15s | 3073 addresses restored into in-memory `addrman` in 3 ms. |
| DNS wait | T+11s after load thread starts | `ThreadDNSAddressSeed` sleeps 11 s because `addrman` was non-empty. |
| DNS query | T+26s | Fewer than 2 outbound peers at checkpoint -> DNS runs. |
| DNS result | T+27s | 10 A records added (one per seed hostname). |
| First peer | T+27s | Outbound dials from `addrman.Select()` begin; version messages follow. |

DNS was **not** skipped (`P2P peers available. Skipped DNS seeding.` did not appear) because outbound count was below 2 at the 11-second checkpoint.

### DNS seed outcomes (live `dig`, 2026-06-10)

Ten hostnames from `chainparams.cpp`; each returned one IPv4 A record:

| Seed hostname | A record |
|---------------|----------|
| seed0.zerocurrency.io | 149.248.60.120 |
| seed1.zerocurrency.io | 167.86.88.253 |
| seed2.zerocurrency.io | 207.180.237.72 |
| seed3.zerocurrency.io | 173.249.16.58 |
| seed4.zerocurrency.io | 207.180.207.83 |
| seed5.zerocurrency.io | 154.38.165.9 |
| seed6.zerocurrency.io | 161.97.126.25 |
| seed7.zerocurrency.io | 194.163.167.12 |
| seed8.zerocurrency.io | 167.86.124.232 |
| seed9.zerocurrency.io | 62.171.184.206 |

Code path (`ThreadDNSAddressSeed` in `net.cpp`):

- Looks up each seed hostname (`LookupHost`).
- For each IP, builds `CAddress` on port 23801.
- Sets `nTime` to a **random age between 3 and 7 days** (`GetTime() - 3*nOneDay - GetRand(4*nOneDay)`), so DNS entries are not treated as brand-new gossip.
- Records source as the seed name (`CNetAddr(seed.name, true)`).
- Adds all via `addrman.Add(vAdd, ...)`.

`found` counts resolved IPs (10 here = one IP per seed). No AAAA records were returned for seed0 in this check; IPv6 seeds would be added the same way if present.

### Outbound dial failures (normal)

After DNS, `ThreadOpenConnections` selects addresses from `addrman` and dials. Failed attempts are logged:

```
connect() to 120.28.252.102:23801 failed after select(): Connection refused (61)
connect() to 151.252.67.236:23801 failed after select(): No route to host (65)
connect() to [2a02:a03f:62f8:f900:8112:d6ae:62a0:554d]:23801 failed after select(): Network is unreachable (51)
```

Each failure calls `addrman.Attempt()` (increments `nAttempts`, updates `nLastTry`). Addresses are not deleted on a single refused connection.

### Version messages after connections (with `logips=1`)

```
receive version message: /Ambrym:3.3.1/: version 170009, blocks=2469658, us=107.135.67.9:62731, peer=2, peeraddr=129.213.203.57:23801
receive version message: /Gaua:4.0.0/: version 170009, blocks=2454996, us=[2600:1700:47d0:7660:7d07:4f3a:d025:92c1]:62754, peer=6, peeraddr=[2401:d002:2b09:7f1e:be24:11ff:fe37:8c23]:23801
```

Field glossary:

| Field | Meaning |
|-------|---------|
| `/Ambrym:3.3.1/` (`cleanSubVer`) | Remote user agent string (sanitized for logs/RPC). |
| `version 170009` | P2P protocol version (`nVersion`). Must meet current epoch minimum or peer is disconnected. |
| `blocks=2469658` | Peer's claimed chain height at handshake (`nStartingHeight`). |
| `us=107.135.67.9:62731` | Address **this node told the peer** it sees (`addrMe` from their `version` message). Ephemeral source port on our side. Alternates between IPv4 NAT address and IPv6 local depending on path. |
| `peer=2` | Internal node id (`CNode::id`), not an IP. |
| `peeraddr=129.213.203.57:23801` | Remote socket address (only when `logips=1`). This is the peer we connected to. |

After successful handshake, `addrman.Good(pfrom->addr)` marks the peer as reachable and may move it from "new" to "tried" tables.

### `getaddr` on inbound (not applicable here)

Outbound-only nodes ignore inbound `getaddr` requests (fingerprinting mitigation in `main.cpp`). This node had 0 inbound peers, so it only **received** `addr` gossip and did not serve `getaddr` responses to the Internet.

---

## `peers.dat` structure

### File wrapper (`CAddrDB` in `net.cpp`)

On disk, `peers.dat` is not raw `addrman` alone:

1. 4-byte network `MessageStart` magic
2. Serialized `CAddrMan` blob
3. Trailing `uint256` checksum (hash of preceding bytes)

Write is atomic: serialize to `peers.dat.XXXX`, then rename over `peers.dat`.

Assessed file: **214,478 bytes** (~210 KiB), modified 2026-06-09 20:49. Format allows up to ~1.5 MiB (`addrman.h` comment).

### Serialized `CAddrMan` contents (`addrman.h`)

| Field | Purpose |
|-------|---------|
| `nVersion` (1) | Format version |
| `nKey` (32 bytes) | Secret key for bucket placement (prevents predictable bucketing) |
| `nNew` | Count of entries in "new" table |
| `nTried` | Count of entries in "tried" table |
| New-bucket index structure | Which addresses sit in which of 1024 x 64 "new" slots |
| Per-entry `CAddrInfo` records | See below |

Not stored on disk (rebuilt in memory): `nLastTry`, `nRefCount`, `fInTried`, `nRandomPos`, `vRandom` ordering.

### Per-address record (`CAddrInfo`)

Extends `CAddress`:

| Field | Serialized | Meaning |
|-------|------------|---------|
| IP + port | yes | `CService` endpoint |
| `nServices` | yes | Capability flags (`NODE_NETWORK`, etc.) |
| `nTime` | yes | When we last heard about this address |
| `source` | yes | Who told us (peer IP or DNS seed name) |
| `nLastSuccess` | yes | Last successful connection timestamp (0 = never) |
| `nAttempts` | yes | Failed connection attempts since last success |
| `nLastTry` | no (RAM) | Last dial attempt time |
| `nRefCount` | no | How many "new" buckets reference this entry (max 8) |
| `fInTried` | no | Whether in "tried" table |

### Two-table bucket model

From `addrman.h` design comment:

- **New table:** 1024 buckets x 64 entries = 65,536 slots. Addresses not yet proven reachable. Bucket placement depends on **source** /16 group to limit attacker fill.
- **Tried table:** 256 buckets x 64 entries = 16,384 slots. Addresses we have connected to successfully. Eviction from tried moves entry back to new.
- One address can appear in up to **8** new buckets (increasing selection weight for frequently seen addresses).

**3073 unique addresses** is well below capacity (~4.7% of new slots). Typical for a node that has run for weeks and accumulated gossip.

### Why maintain thousands of addresses

1. **Only 8-16 outbound connections** are active (`MAX_OUTBOUND_CONNECTIONS = 16`), but most candidate IPs are offline, firewalled, or on non-default ports. A large pool is required to keep finding reachable peers.
2. **Eclipse resistance:** Bucket hashing by source /16 and random `nKey` limits one adversary from filling all slots.
3. **Geographic and network diversity:** `ThreadOpenConnections` allows only **one outbound per /16 group** (`setConnected.insert(pnode->addr.GetGroup())`), so many addresses across groups are needed.
4. **Rotation:** Stale or dead entries are dropped; fresh gossip continuously replenishes the pool.

### Drop and eviction policy (`IsTerrible` in `addrman.cpp`)

An address is removed when **all** of:

- Not attempted in the last 60 seconds, AND
- Any of:
  - `nTime` more than **30 days** old (`ADDRMAN_HORIZON_DAYS`)
  - `nTime` impossibly in the future (>10 min ahead)
  - **3+ attempts** with zero successful connection (`ADDRMAN_RETRIES`)
  - **10+ failures** with no success in **7+ days** (`ADDRMAN_MAX_FAILURES` / `ADDRMAN_MIN_FAIL_DAYS`)

Bucket-full eviction (before `IsTerrible`): adding to a full bucket removes a random existing entry biased toward older entries.

Selection deprioritization (`GetChance`): recent attempt within 10 minutes -> 1% weight; each failed attempt multiplies chance by 0.66 (capped at 8 attempts).

### Persistence schedule

- Flush every **900 s** (15 min) via scheduler (`DumpAddresses`).
- Flush on graceful shutdown (`StopNode`).
- Flush lines use `LogPrint("net", ...)` and may not appear in `debug.log` unless `debug=net`.

---

## Active connection policy

Separate from `addrman`: each **connected peer** is a `CNode` with runtime state exposed via `getpeerinfo`.

### Connection limits

| Parameter | Default | Source |
|-----------|---------|--------|
| `maxconnections` | 125 | `DEFAULT_MAX_PEER_CONNECTIONS` |
| Max outbound | 16 | `MAX_OUTBOUND_CONNECTIONS` in `net.cpp` |
| Max inbound | `maxconnections - 16` | ~109 at default |
| Connect timeout | 5000 ms | `DEFAULT_CONNECT_TIMEOUT` |
| Outbound selection | 1 peer per /16 | `ThreadOpenConnections` |

### Outbound selection loop

Every 500 ms, `ThreadOpenConnections`:

1. Waits for outbound semaphore slot.
2. If `addrman` empty for 60+ s, adds **fixed seeds** once (`convertSeed6(Params().FixedSeeds())`).
3. Calls `addrman.Select()` up to 100 times, skipping:
   - Invalid or local addresses
   - Already-connected /16 groups
   - Non-default ports (until 50 tries)
   - Recently tried nodes (within 600 s, until 30 tries)
4. On TCP success: `addrman.Attempt()` at dial; `addrman.Good()` after valid `version`.
5. On TCP failure: `addrman.Attempt()` only.

### When connections end

| Trigger | Log / behavior |
|---------|----------------|
| Graceful peer close | `socket closed` (`LogPrint net`) |
| Send idle 20 min | `socket sending timeout: Ns` (`TIMEOUT_INTERVAL`) |
| Recv idle 20 min | `socket receive timeout: Ns` |
| Ping timeout 20 min | `ping timeout: Ns` |
| No traffic in first 60 s | `socket no message in first 60 seconds` |
| Obsolete protocol version | `peer=N using obsolete version X; disconnecting` |
| `Misbehaving` score >= `banscore` (default 100) | `BAN THRESHOLD EXCEEDED`; ban + disconnect |
| Inbound slot full | `AttemptToEvictConnection` or drop new connection |
| Manual `disconnectnode` RPC | Sets `fDisconnect` |
| `-connect` / `-seednode` one-shot | `fOneShot` -> disconnect after `addr` |

Inbound eviction (`AttemptToEvictConnection`) protects, in order:

1. Whitelisted / manual / localhost / recent blocks-relay-only
2. 4 peers with lowest ping
3. 8 peers with best ping
4. Half with longest connection time
5. Then evicts youngest peer from the /16 group with most inbound connections

### Ban policy

- `banscore` default **100**; `bantime` default **86400** s (24 h).
- `Misbehaving()` increments score on protocol violations (oversized `addr`, bad `inv`, etc.).
- Banned IPs rejected at accept: `connection from X dropped (banned)`.

### Address gossip received (`addr` message)

When a connected peer sends `addr`:

- Max **1000** addresses per message; larger -> `Misbehaving(20)`.
- Timestamps clamped if bogus; future times set to ~5 days ago.
- Only **reachable** addresses stored (`IsReachable`).
- Added with **2-hour penalty** (`nTimePenalty = 2*60*60`) so gossip does not dominate tried table.
- Fresh addresses (last 10 min) may be relayed to 1-2 other peers.
- Inbound peers may request addresses via `getaddr`; response is up to **23%** of addrman or **2500** addresses (`ADDRMAN_GETADDR_MAX_PCT` / `ADDRMAN_GETADDR_MAX`).

### Per-connected-peer RPC fields (`getpeerinfo`)

| Field | Use for monitoring |
|-------|-------------------|
| `addr` | Remote IP:port |
| `addrlocal` | Local endpoint seen by peer |
| `conntime` | Connection start (epoch seconds) |
| `lastsend` / `lastrecv` | Activity; stale -> disconnect risk |
| `pingtime` / `pingwait` | Latency and health |
| `bytessent` / `bytesrecv` | Throughput |
| `startingheight` | Peer chain tip at connect |
| `synced_headers` / `synced_blocks` | Sync progress with this peer |
| `inflight` | Block heights being fetched |
| `banscore` | Misbehavior accumulator |
| `subver` / `version` | Software identification |
| `inbound` | Direction (false = outbound for this node) |

---

## RPC configuration (summary)

`rpcbind=127.0.0.1` + `rpcallowip=127.0.0.1` -> single loopback bind on 23811. See prior session notes in code refs at bottom.

```bash
cd ~/Work/ZK/Zero400
./src/zero-cli -rpcport=23811 getpeerinfo
./src/zero-cli -rpcport=23811 getnetworkinfo
./src/zero-cli -rpcport=23811 getconnectioncount
```

---

## Tools to track peer discovery and analyze peers

### On-node (no extra software)

| Method | What it gives | Limitations |
|--------|---------------|-------------|
| `getpeerinfo` | Live connections, ping, bytes, sync state | Connected peers only; no addrman |
| `getnetworkinfo` | Connection counts, network active, relay fee | No per-address geography |
| `debug.log` + `logips=1` | Handshake IPs, DNS load, dial failures | No structured metrics; verbose |
| `contrib/perf/stall_check.py` | UpdateTip gaps, timeout bursts, clock warn | `--datadir` / `--log` / `--rotated` (debuglog.py) |
| `contrib/perf/extract_measures.py` | Marker durations / height_per_s | Same path spec; `--env insight\|wallet` to cite |
| `debug=net` | Addr add/select detail (`LogPrint addrman`) | Very noisy; not for production |
| `peers.dat` size + mtime | Persistence health | Opaque binary; no field visibility |

Zero400 does **not** implement Bitcoin Core's `getrawaddrman` or `getaddrmaninfo` RPCs.

### External monitoring and analysis tools

#### [addrman.observer](https://addrman.observer/)

Visualizes `getrawaddrman` JSON dumps: bucket layout, source networks, address age, AS mapping (with asmap).

- **Positive:** Offline HTML; good for understanding addrman poisoning and source diversity.
- **Negative:** Requires `getrawaddrman` (not in Zero); Bitcoin Core 28+ with RPC enabled.

#### [peer-observer](https://github.com/0xb10c/peer-observer) (0xb10c)

Honeypot-oriented stack: eBPF/RPC extractors, Prometheus metrics, Grafana, connectivity checks on received `addr` messages.

- **Positive:** Real-time anomaly detection; tracks addrman growth rate; used in production research infra.
- **Negative:** Heavy setup (NATS, Prometheus, patched/tracepoint Core); aimed at Bitcoin Core forks with tracepoints; not drop-in for Zero without porting.

#### [Bitcoin-Core-Peer-Map](https://github.com/mbhillrn/Bitcoin-Core-Peer-Map)

Browser dashboard: world map, GeoIP, ISP/ASN diversity score, peer management GUI.

- **Positive:** Practical single-node view; offline MaxMind DB; diversity scoring.
- **Negative:** Bitcoin Core RPC assumptions; GeoIP accuracy varies; ASN diversity needs compatible `getpeerinfo` fields.

#### [Bitnodes](https://bitnodes.io/)

Public crawler estimating reachable nodes per network; ASN/country snapshots.

- **Positive:** Network-wide baseline; API for reachable-node counts.
- **Negative:** Measures **inbound-reachable** nodes; NAT-only nodes like this Mac are invisible; not a per-node addrman view.

#### GeoIP / ASN lookup (manual)

`whois`, [ipinfo.io](https://ipinfo.io), [bgp.he.net](https://bgp.he.net), MaxMind GeoLite2.

- **Positive:** Quick region/ISP for any IP from `getpeerinfo` or logs.
- **Negative:** VPN/hosting mislabels; no latency; privacy if sending IPs to third-party APIs.

#### Prometheus + custom exporter

Poll `getpeerinfo` / `getconnectioncount` on an interval; chart in Grafana.

- **Positive:** Trend connection count, ping, bytes over time.
- **Negative:** Does not capture addrman internals without new RPCs; DIY maintenance.

### Practical recommendation for Zero today

1. Enable `logips=1`; grep `debug.log` for discovery events.
2. Script `getpeerinfo` -> CSV; enrich with offline GeoLite2 or `whois` for region/ASN.
3. Track `peers.dat` size and `Loaded N addresses` at each restart.
4. If porting Bitcoin RPCs: add `getrawaddrman` first, then use addrman.observer.

---

## Bitcoin Core and parallel projects: peer discovery state

Zero inherits **pre-ASMap Bitcoin addrman** (~Pieter Wuille design). Comparison with current upstream practice:

### Shared legacy behavior (Zero still has this)

| Mechanism | Zero | Bitcoin Core / Zcash ZIP 204 |
|-----------|------|------------------------------|
| `peers.dat` + `CAddrMan` buckets | yes | yes |
| DNS seeds if <2 peers after 11 s | yes | yes (Zcashd identical; Zebra always DNS) |
| Fixed seeds after 60 s empty addrman | yes | yes |
| `addr` / `getaddr` gossip | yes | yes |
| Outbound one-per-/16 | yes | yes (Bitcoin moving toward ASMap groups) |
| Inbound `getaddr` ignored | yes | yes |

### Bitcoin Core changes not in Zero (candidates to port)

| Change | Benefit | Reference |
|--------|---------|-----------|
| **ASMap** / ASN-based netgroups | Eclipse resistance across subnets of same hoster; embedded map in Core 31.0 | [Bitcoin Core 31.0](https://bitcoincore.org/en/releases/31.0/), Brink 2025 report |
| `getrawaddrman` / `getaddrmaninfo` RPC | Observability, addrman.observer, peer-observer metrics | bitcoin/bitcoin #30062 |
| Cap DNS seed IPs at **32 per seed** | Prevents one seed dominating addrman | bitcoin/bitcoin #29850 |
| Favor addrman over eager `seednode` fetch | Reduces restart fingerprinting and seed bias | bitcoin/bitcoin #29605 |
| **`addrv2`** message | Tor v3, I2P, CJDNS addresses in gossip | BIP 155 |
| Block-relay-only / outbound diversity | Reduce fingerprinting; separate block fetch from addr relay | post-0.19 Bitcoin P2P |
| AddrFetch connections for fixed seeds | Faster bootstrap without long-lived seed links | bitcoin/bitcoin #26114 |
| DNS seed shuffle / per-seed limits | Less predictable startup signaling | various 2024 net PRs |

### Zcash / Zebra

- [ZIP 204](https://zips.z.cash/zip-0204) documents the same DNS 11 s / 2-peer rule for zcashd.
- Zebra uses a persistent address cache and always DNS-seeds on startup (different policy).
- Zero uses `seed0..seed9.zerocurrency.io` (10 seeds) vs Zcash's four mainnet seeds.

### Suggestions for Zero (ordered by impact vs effort)

1. **Add `getaddrmaninfo` and `getrawaddrman` RPC** (port from Bitcoin Core). Unlocks addrman.observer and scripted diversity checks without log scraping.
2. **Limit DNS seed yield** to 32 IPs per hostname and shuffle seed query order. Reduces single-operator bias; matches 2024 Bitcoin hardening.
3. **Evaluate ASMap** for mainnet. Largest eclipse-defense gain; requires `ip_asn.map` maintenance or embedded map pipeline (significant effort).
4. **Document and test `-forcednsseed`** for recovery when `peers.dat` is corrupted but non-empty.
5. **Add `addnode` monitoring** to contributor docs: when to use vs letting addrman work.
6. **Consider `addrv2`** if Tor/I2P listening becomes a project goal; otherwise low priority.
7. **Defer Erlay** (set reconciliation); unrelated to discovery bootstrap.

---

## Issues encountered and resolution

| Issue | Cause | Resolution |
|-------|-------|------------|
| `Binding RPC on address 0.0.0.0 port 23811 failed` | `rpcallowip` without `rpcbind` on macOS dual-stack | Add `rpcbind=127.0.0.1` |
| 0 inbound peers | NAT; no port forward on 23801 | Expected; outbound sync OK |
| Many `connect() failed` lines | Dead addresses in addrman | Normal; drop policy eventually prunes |
| README `rpcport=23801` | Doc drift | Use **23811** for RPC |

---

## Code references (Zero400)

| Topic | File |
|-------|------|
| Addrman design and constants | `src/addrman.h`, `src/addrman.cpp` |
| `peers.dat` I/O | `src/net.cpp` `CAddrDB`, `DumpAddresses` |
| DNS seeds | `src/chainparams.cpp`, `src/net.cpp` `ThreadDNSAddressSeed` |
| Outbound connect | `src/net.cpp` `ThreadOpenConnections`, `ConnectNode` |
| Disconnect / timeout | `src/net.cpp` `ThreadSocketHandler`, `AttemptToEvictConnection` |
| `addr` / `getaddr` | `src/main.cpp` `ProcessMessage` |
| Version log line | `src/main.cpp` (~6263) |
| `getpeerinfo` | `src/rpc/net.cpp` |
| Misbehavior / ban | `src/main.cpp` `Misbehaving` |
| RPC bind | `src/httpserver.cpp` |

---

## Related docs

- `~/Work/ZK/Zero400/BUILD_ZERO.md` section 3 (datadir)
- [ZIP 204 P2P](https://zips.z.cash/zip-0204) (Zcash-family discovery spec)
- [Bitcoin P2P network guide](https://developer.bitcoin.org/devguide/p2p_network.html)
