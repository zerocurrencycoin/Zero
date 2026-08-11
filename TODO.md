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

1. **Stable subsidy arithmetic** -- integer founders helper (`subsidy * 75 / 1000`); see Full descriptions and **ZERO_COIN.md**.
2. **WAL-GETALLDATA-W5** -- tip poll split (balances vs History); revisit after current getalldata soak.
3. **TST-01** remainder / **TST-05** / **TST-03** / **TST-09** notify half -- harness gaps in Full descriptions.
4. Release / docs track -- Linux release validation, supply review (~20M ZER target).
5. Postponed bucket: see **Pending** (not scheduled).

---

## Active

- Node setup and maintenance docs: keep user-facing instructions accurate
- Chain bootstrap: end-user import path (`-loadblock` / auto-import); linearize in `contrib/linearize/`
- Total supply discrepancy: arithmetic vs ~20M ZER target
- **Stable subsidy arithmetic** (implementation)
- RPC coverage matrix: `RPCs.csv` vs harness depth
- **TST-01** -- exclusive getalldata + Ext `getalldata_scenario` working; under development: `getsupply` / `zs_*` / sapling depth
- **TST-03** -- `zeronodestats` + zeronode/budget subcmds; arg validation
- **TST-05** -- genesis (192,7) indices + (48,5) KATs for miner tests
- **TST-09** -- alertnotify working; `-blocknotify` / `-walletnotify` open
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
- P2P logging after zn dispatch -- postponed
- Params archival / Windows hardening / branch-id CI / OpenSSL 3 / SwiftTX strip / Debian packaging

---

## Completed (summary)

- WAL-WTXORDERED + Assure-4; getalldata S4--S8 + W2/W3 exclusive; `getalldata_scenario` Ext
- Founders regtest window + `founders_window.py`; Tier B wallet Sapling port
- ZERO_COIN consolidation; shell-notify compile gate; LevelDB `max_open_files`; reindex markers/resume
- Insight-oriented Tier B scripts promoted when green; longpoll funded-node pin; workqueue 503 + once-per-episode WARNING
- Harness exit-code / getchaintips / zeronode null guards

---

## Full descriptions

### Stable subsidy arithmetic

Replace `double`×`COIN` and `* 0.075` / `* 7.5 / 100` mixes with integer zats: base **10.8 ZER** as integer zats; founders **`subsidy * 75 / 1000`** via one helper used by miner, validate, GBT, and metrics. Schedule: **ZERO_COIN.md**. Touch sites include `GetBlockSubsidy`, founders checks in `main.cpp` / zeronode payments / budget / `getblocksubsidy` / metrics, and matching tests.

### WAL-WTXORDERED / const policy

**Done:** Incremental `wtxOrdered`; Assure-4. Continue const conversion on wallet-tx **read** paths. Line-by-line Zcash `wtxOrdered` type match stays with postponed **WAL-RPC-ACCOUNTS**.

### Helpers design (`getalldata`)

One parse/filter path for day window, `nCount`, watchonly, and datatype gates (`rpczerowallet`). `IsGetAllDataTxTooOld` shipped; remaining helpers listed under Pending **WAL-GETALLDATA-HELPERS**.

### WAL-GETALLDATA-ARG2-DEFAULT (postponed)

When arg2 omitted, today ~30y window. Proposed default **2** (7 days). Release-note risk for scripts that omitted arg2.

### WAL-GETALLDATA-W5

Split tip poll: balances (datatype **1**) on timer; full History on user action or every Nth tick. Complementary to soft **-34** coalesce. Revisit after soak; decide before W6.

### WAL-GETALLDATA-CACHE (W6) / W1 / W4

In-process tip+dirty cache (after W5). W1: merge History key insert into balance walk. W4: IVK decrypt review.

### WAL-GETALLDATA-LEGACY-SCOPE

Keep RPC; do not grow kitchen-sink without datatype gates. Do not undo S4--S8 / W2 / const walks without replacement.

### TST-01 / `getalldata_scenario`

Exclusive Boost: empty-wallet gates. Ext scenario: populated wallet. Further: `getsupply` / `zs_*`.

### OPS-TOR-COMPILE-OUT (postponed)

Optional compile-out of Tor control. Runtime onion already off by default. Do not couple to I2P.

### OPS-I2P (postponed)

Track ecosystem only. No Zero implementation in this stage.

### Upstream PR ideas (node)

| Candidate | Note |
|-----------|------|
| Longpoll funded-node pin | Zero Ext already pins; useful upstream pattern |
| Work-queue reject logging | Zero: **503** + WARNING once per full episode |
