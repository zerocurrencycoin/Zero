# TODO

Open follow-ups for the Zero full node (`zerod`).

---

## Tracking rules

This section is the single source for tracking IDs and statuses; other documents follow it.

**IDs.** `PREFIX-NN` or `PREFIX-NAME`, assigned once and never reused. The prefix names the subject:

| Prefix | Subject |
|--------|---------|
| **CON-*** | Consensus and engineering invariants |
| **WAL-*** | Wallet and RPC |
| **OPS-*** | Operations: database, notify, configuration, build surface |
| **REL-*** | Release and packaging |
| **DOC-*** | Documentation |
| **TST-*** | Tests and gate work |
| **EXT-*** | Extended harness |

Maintainer documents define further prefixes for upstream catalogs and internal work; they use the same rules.

**One definition.** An item is described in one place: here, as a one-line entry with an optional Full description, or in the maintainer document that owns it. Everywhere else, cite the ID.

**Status is the section.**

- **Ordered next** -- the next steps, in order; at most five.
- **Active** -- in progress or scheduled.
- **Pending** -- accepted, not scheduled; grouped by subject. A short status note (postponed, does not gate a release, decide after X) is allowed.
- **Done** -- remove the entry. The outcome lives in the code, the documentation of the behavior, and the release notes; no completed-items lists.

**Upstream candidates.** Catalog rows record a decision: Port, Implement, Review, Hold, Defer, Skip, Reject, or Keep current.

---

## Ordered next

1. **WAL-GETALLDATA-W5** -- tip poll split (balances vs History); decide after the current getalldata soak.
2. **TST-01** remainder -- `zs_*`, `getsupply`, Sapling witness RPC scenarios; mined-tx History depth for `getalldata`.
3. Release track -- Linux `--strict` + `--suite` at the tag commit; signing and checksums per **REL-01**. Receipts: **`.build/`** via `zcutil/check-setup.sh` and `zcutil/check-release.sh`. Ops smoke: **TEST_ZERO.md** section 8.
4. Postponed bucket: see **Pending** (not scheduled).

---

## Active

- Node setup docs: operator runbook in BUILD_ZERO
- Chain bootstrap: end-user import path (`-loadblock` / auto-import); linearize in `contrib/linearize/`
- RPC coverage matrix: `RPCs.csv` vs harness depth
- **TST-01** -- exclusive `getalldata` and Ext `getalldata_scenario` working; open: `getsupply` / `zs_*` / Sapling witness depth
- macOS datadir: prefer `Application Support/zero/` for the wallet
- Fuzz harness setup (**TST-06**)
- **DOC-CONVENTIONS** -- adopt the documentation and comment rules into the agent and contributor instruction files
- **REL-06** -- review commit squashing before the master merge and deletion of local and remote branches (separate review)
- **REL-08** -- fixed seed lists for mainnet and testnet (`contrib/seeds`, `chainparamsseeds.h`)
- **REL-01** -- release signing and checksums: signing keys and GPG fingerprint; first real `release-linux.sh`, signed and notarized `release-macos.sh`, and MXE `release-win.sh` runs. Procedure: BUILD_ZERO sections 2.5-2.6
- **CON-04** -- chain safety: deep-reorg shutdown, heavier-invalid-chain and block-rate warnings, end-of-support height; observability, tests, recovery runbook, policy decisions
- **REL-03** -- `fetch-params.sh` downloads the Sprout and Sapling parameter files from the Zcash server (`download.z.cash`); verify names and URLs, and keep a Zero-controlled copy with checksums
- **REL-09** -- release check that `configure.ac` version matches the release tag
- **OPS-CONF-UNIFY** -- one description per `zero.conf` field, consistent with parsed options, help text, `Options.csv`, man pages, conf templates, and samples; one canonical sample
- **OPS-TOOLCHAIN-MATRIX** -- verify per-OS toolchain versions (GCC, Rust, Python, autotools) for each supported build OS, record them in BUILD_ZERO, and check them in `zcutil/check-setup.sh`

---

## Pending

Consensus:

- Supply review -- emission arithmetic vs the ~20M ZER target; postponed, does not gate a release

Wallet and RPC:

- WAL-GETALLDATA-CACHE (W6), W1, W4, HELPERS -- after W5 / soak
- WAL-GETALLDATA-LEGACY-SCOPE -- which 2018--2020 surface can shrink
- WAL-CONST -- continue const conversion on wallet-tx read paths
- WAL-RPC-ACCOUNTS -- product decision required; includes matching Zcash `wtxOrdered` types line by line
- WAL-LOCKEDPOOL -- LockedPool / `getmemoryinfo`

Node operation:

- OPS-REINDEX remainder -- refuse / `-reindexforce`; skip-wallet below H
- OPS-CACHE-METRICS -- tunable cache metrics
- OPS-TXINDEX-DEFAULT / OPS-AT-HEIGHT
- OPS-TOR-COMPILE-OUT -- optional `--disable-tor`
- OPS-I2P -- ecosystem track only; no Zero implementation scheduled
- OPS-DEBUGLOG-TIMING -- filter/process `debug.log` timing tooling

Build, packaging, and release:

- OPS-LINUX-OTHER -- other Linux and Ubuntu versions; see Full descriptions
- OPS-MACOS-DEPLOY-TARGET -- export `MACOSX_DEPLOYMENT_TARGET` from the build system (libtool `-bind_at_load` warning)
- OPS-PRUNE-LOGS -- establish what `prune_logs` / `ZERO_LOG_KEEP` in `zcutil/fzero.sh` does, if anything, before documenting it
- OPS-MANPAGES -- man page naming and content: `doc/man/zcash-fetch-params.1` vs the shipped `zero-fetch-params`; pages match current `-help`; compare with current Zcash and parallel projects
- OPS-BASH-COMPLETION -- bash completion for `zerod`, `zero-cli`, `zero-tx`: `contrib/` files carry Zcash names and are not packaged; compare with current Zcash and parallel projects
- REL-05 -- inherited contrib and packaging tooling: `build-debian-package.sh` and `contrib/debian/`, `contrib/macdeploy/`, Proton AMQP (`src/amqp/`, `contrib/amqp/`), `contrib/ci-workers/`, `contrib/init/`, `contrib/zmq/`; keep, adapt, or remove each
- REL-07 -- Windows hardening: `build-win.sh` does not pass `--enable-hardening`

Tests:

- TST-SAPLING-ROOT -- `finalsaplingroot.py` (Bfail)
- TST-WITNESS-REINDEX -- witness rebuild / `CachedWitnessesCleanIndex` coverage
- EXT-INSIGHT-SUPERSET
- `txindex.py` -- promote after green

---

## Full descriptions

### getalldata helpers design

One parse/filter path for day window, `nCount`, watchonly, and datatype gates (`rpczerowallet`). `IsGetAllDataTxTooOld` is in tree; remaining helpers are Pending **WAL-GETALLDATA-HELPERS**.

### WAL-GETALLDATA-W5

Split the tip poll: balances (datatype **1**) on a timer; full History on user action or every Nth tick. Complements the soft **-34** coalesce. Decide before W6.

### WAL-GETALLDATA-CACHE W6, W1, W4

In-process tip+dirty cache (after W5). W1: merge History key insert into the balance walk. W4: IVK decrypt review.

### WAL-GETALLDATA-LEGACY-SCOPE

Keep the RPC; do not grow it without datatype gates. Do not remove the existing parameter gates, warmup and coalesce gates, work-queue handling, sort-key collision detection, or const wallet walks without a replacement.

### TST-01 / `getalldata_scenario`

Exclusive Boost covers empty-wallet gates; the Ext scenario covers a populated wallet. Next: `getsupply` / `zs_*`.

### OPS-LINUX-OTHER -- other Linux and Ubuntu versions

Main effort: build and cross-test on Ubuntu 24.04. Interoperability target: build and run on Ubuntu 18.04, 20.04, and 22.04, under the build-OS floor rule in BUILD_ZERO. Ubuntu 16.04 is out of scope. Other distributions are not assessed.

### OPS-TOR-COMPILE-OUT

Optional compile-out of Tor control. Runtime onion is already off by default. Do not couple to I2P.

### Upstream PR ideas

| Candidate | Note |
|-----------|------|
| Longpoll funded-node pin | Zero Ext already pins; useful upstream pattern |
| Work-queue reject logging | Zero: **503** + WARNING once per full episode |
