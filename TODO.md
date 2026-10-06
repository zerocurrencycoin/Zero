# TODO

Open follow-ups for the Zero full node (`zerod`).

---

## Tracking rules

This section is the single source for tracking IDs and statuses; other documents follow it.

**IDs.** `PREFIX-NN` or `PREFIX-NAME`, assigned once and never reused. The prefix names the subject:

| Prefix | Subject |
|--------|---------|
| **CON-*** | Consensus and engineering invariants |
| **RPC-*** | RPC surface: support levels, server handling and parameters, RPC families |
| **WAL-*** | Wallet internals |
| **OPS-*** | Operations: database, notify, configuration, build surface |
| **REL-*** | Release and packaging |
| **DOC-*** | Documentation |
| **TST-*** | Tests and gate work |
| **EXT-*** | Extended harness |

Maintainer documents define further prefixes for upstream catalogs and internal work; they use the same rules. A large item may list sub-steps cited as `ID step`, for example `RPC-03 W5`.

**One definition.** An item is described in one place: here, as a one-line entry with an optional Full description, or in the maintainer document that owns it. Everywhere else, cite the ID.

**Status is the section.**

- **Ordered next** -- the next steps, in order; at most five.
- **Active** -- in progress or scheduled.
- **Research** -- needs study, experiments, a documented plan, and validation design before it can be scheduled.
- **Pending** -- accepted, not scheduled; grouped by subject. A short status note (postponed, does not gate a release, decide after X) is allowed.
- **Done** -- remove the entry. The outcome lives in the code, the documentation of the behavior, and the release notes; no completed-items lists.

**Upstream candidates.** Catalog rows record a decision: Port, Implement, Review, Hold, Defer, Skip, Reject, or Keep current.

---

## Ordered next

1. **RPC-03 W5** -- getalldata poll cost: measure datatype 1 (balances) against datatype 0 (balances and History) on a large wallet; publish the recommended client poll cadence.
2. **TST-07** -- Zero RPC depth: shielded outputs and filter types for the zs_* RPCs, `getsupply` values against the emission schedule, Sapling witness RPCs, mined-transaction History in `getalldata`.
3. Release track -- Linux `--strict` + `--suite` at the tag commit; signing and checksums per **REL-01**. Receipts: **`.build/`** via `zcutil/check-setup.sh` and `zcutil/check-release.sh`. Ops smoke: **TEST_ZERO.md** section 8.
4. Postponed bucket: see **Pending** (not scheduled).

---

## Active

RPC:

- **RPC-01** -- support levels: one disposition per RPC (supported, deprecated, hidden, compiled out, removed) with its test depth, from `RPCs.csv`; includes the legacy accounts RPCs (product decision; matching Zcash `wtxOrdered` types line by line) and the Sprout RPCs

Documentation and tests:

- Node setup docs: operator runbook in BUILD_ZERO
- Chain bootstrap: end-user import path (`-loadblock` / auto-import); linearize in `contrib/linearize/`
- Fuzz harness setup (**TST-06**)
- **DOC-CONVENTIONS** -- adopt the documentation and comment rules into the agent and contributor instruction files

Release and operations:

- macOS datadir: prefer `Application Support/zero/` for the wallet
- **REL-01** -- release signing and checksums: per-platform signing still to be decided; signing keys and GPG fingerprint; first real `release-linux.sh`, signed and notarized `release-macos.sh`, and MXE `release-win.sh` runs. Procedure: BUILD_ZERO sections 2.5-2.6
- **REL-06** -- review commit squashing before the master merge and deletion of local and remote branches (separate review)
- **OPS-CONF-UNIFY** -- one description per `zero.conf` field, consistent with parsed options, help text, `Options.csv`, man pages, conf templates, and samples; one canonical sample
- **OPS-TOOLCHAIN-MATRIX** -- verify per-OS toolchain versions (GCC, Rust, Python, autotools) for each supported build OS, record them in BUILD_ZERO, and check them in `zcutil/check-setup.sh`

---

## Pending

Consensus:

- Supply review -- emission arithmetic vs the ~20M ZER target; postponed, does not gate a release

RPC:

- **RPC-03** -- getalldata family; steps W6, W1, W4, helpers, address keys, scope (Full descriptions) -- after W5

Wallet:

- WAL-CONST -- continue const conversion on wallet-tx read paths
- WAL-LOCKEDPOOL -- LockedPool / `getmemoryinfo`

Node operation:

- OPS-REINDEX remainder -- refuse / `-reindexforce`; skip-wallet below H
- OPS-CACHE-METRICS -- tunable cache metrics
- OPS-TXINDEX-DEFAULT / OPS-AT-HEIGHT
- OPS-TOR-COMPILE-OUT -- optional `--disable-tor`
- OPS-DEBUGLOG-TIMING -- filter/process `debug.log` timing tooling

Build, packaging, and release:

- REL-03 -- params mirror: verify file names and URLs of `fetch-params.sh`, record checksums, keep a Zero-controlled copy; postponed until after v4.1.0
- REL-08 -- fixed seed lists for mainnet and testnet (`contrib/seeds`, `chainparamsseeds.h`); postponed until after v4.1.0
- OPS-LINUX-OTHER -- other Linux and Ubuntu versions; see Full descriptions
- OPS-MACOS-DEPLOY-TARGET -- export `MACOSX_DEPLOYMENT_TARGET` from the build system (libtool `-bind_at_load` warning)
- OPS-PRUNE-LOGS -- establish what `prune_logs` / `ZERO_LOG_KEEP` in `zcutil/fzero.sh` does, if anything, before documenting it
- OPS-MANPAGES -- `zerod.1`, `zero-cli.1`, `zero-tx.1` are generated from `-help` by `contrib/devtools/gen-manpages.sh` (help2man); remaining: rename and rewrite `doc/man/zcash-fetch-params.1` for the shipped `zero-fetch-params`, and regenerate the pages at each release
- OPS-BASH-COMPLETION -- bash completion for `zerod`, `zero-cli`, `zero-tx`: `contrib/` files carry Zcash names and are not packaged; compare with current Zcash and parallel projects
- REL-05 -- inherited contrib and packaging tooling: `build-debian-package.sh` and `contrib/debian/`, `contrib/macdeploy/`, Proton AMQP (`src/amqp/`, `contrib/amqp/`), `contrib/ci-workers/`, `contrib/init/`, `contrib/zmq/`; keep, adapt, or remove each
- REL-07 -- Windows hardening: `build-win.sh` does not pass `--enable-hardening`

Tests:

- TST-SAPLING-ROOT -- `finalsaplingroot.py` (Bfail)
- TST-WITNESS-REINDEX -- witness rebuild / `CachedWitnessesCleanIndex` coverage
- EXT-INSIGHT-SUPERSET
- `txindex.py` -- promote after green
- RPC coverage matrix: `RPCs.csv` vs harness depth (feeds RPC-01)

---

## Full descriptions

### RPC-03 -- getalldata family

**Problem.** `getalldata` is the wallet client's single refresh call. Argument 1 (datatype) selects the payload: **0** addresses, balances, transactions, and chain info; **1** addresses, balances, and chain info; **2** transactions and chain info. Argument 2 is the day window (default 7 days), argument 3 the transaction count, argument 4 watch-only. Each call walks every wallet address and transaction (`mapWallet` plus the transaction archive), decrypts shielded notes, sorts history, and builds JSON; on wallets with long history that takes seconds, and clients poll every few seconds. In tree: the soft **-34** coalesce, the 7-day default window, const wallet walks, sort-key collision detection, and one parse/filter path for window, count, watch-only, and datatype (`IsGetAllDataTxTooOld`).

- **W5** -- the split itself (balances on a timer, History on user action or every Nth tick) is a client change, outside this repository. The desktop wallet polls every 30 s but calls `getalldata 0 2 50 true` (datatype 0, 7-day window, 50 transactions, watch-only) only when a new block arrives; no other known client uses the RPC, and the node keeps no per-datatype statistics. Node side: measure both datatypes on a wallet with many transactions and archived entries (wall time, `getalldata` -34 rate under a fixed poll interval), then document the cadence. Complements the soft **-34** coalesce. Decides whether W6 is needed.
- **W6** -- in-process tip and dirty cache, after W5. **W1**: merge History key insert into the balance walk. **W4**: IVK decrypt review.
- **Helpers** -- the remaining shared parse and filter helpers.
- **Address keys** -- key `addressBalances` by destination and encode once at JSON emit.
- **Scope** -- keep the RPC; do not grow it without datatype gates. Do not remove the existing parameter gates, warmup and coalesce gates, work-queue handling, sort-key collision detection, or const wallet walks without a replacement; decide which 2018--2020 surface can shrink.

### OPS-LINUX-OTHER -- other Linux and Ubuntu versions

Main effort: build and cross-test on Ubuntu 24.04. Interoperability target: build and run on Ubuntu 18.04, 20.04, and 22.04, under the build-OS floor rule in BUILD_ZERO. Ubuntu 16.04 is out of scope. Other distributions are not assessed.

### OPS-TOR-COMPILE-OUT

Optional compile-out of Tor control. Runtime onion is already off by default. Do not couple to I2P.

### Upstream PR ideas

| Candidate | Note |
|-----------|------|
| Longpoll funded-node pin | Zero Ext already pins; useful upstream pattern |
| Work-queue reject logging | Zero: **503** + WARNING once per full episode |
