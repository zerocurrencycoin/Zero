# Codebase cleanup: inert, unused and misnamed inherited material

**Draft for Zero400. Nothing removed.** Inventory taken 2026-09-10.
Items are grouped by what makes them safe or unsafe to touch, because
"inherited" alone does not decide it.

## 1. Inert: present, Bitcoin-named, not referenced by the build

None of these directories appear in `Makefile.am`, so they are neither
compiled nor installed. They ship in a source tarball and nowhere else.

| Path | What | Names it uses |
|------|------|---------------|
| `contrib/init/` (6 files) | systemd / upstart / openrc unit samples | `bitcoind`, `/etc/bitcoin/bitcoin.conf`, `BITCOIND_CONFIGFILE` |
| `contrib/spendfrom/` (3 files) | standalone spend helper, Python 2 era | `bitcoin.conf` in `--help` text |
| `contrib/qos/` (2 files) | traffic-shaping sample | Bitcoin ports and naming |
| `contrib/macdeploy/` (11 files) | macOS bundle tooling | mixed |

**`bitcoin.conf` specifically.** Zero reads **`zero.conf`**
(`util.cpp:612`, and `missing_zcash_conf` at `util.h:146` throws
"Missing zero.conf"). Every `bitcoin.conf` mention in the tree is inside the
files above -- documentation strings in samples nothing runs. They are
**cosmetically wrong and functionally inert**: an operator who copies
`contrib/init/bitcoind.service` verbatim gets a unit that points at a
non-existent binary and a config path Zero never reads, so it fails loudly
rather than silently.

**Recommendation: rename or delete as a set, not piecemeal.** Either
- **delete** `contrib/init`, `contrib/spendfrom`, `contrib/qos` -- nothing
  references them, and a stale init script is worse than none; or
- **rename and fix** to `zerod.service` etc. if packaging is wanted.

Deciding one file at a time produces a directory half-converted, which is
harder to reason about than either end state. **This is a Zero400 call.**

## 2. Misnamed but correct -- do not change

| Name | Why it stays |
|------|--------------|
| `~/.zcash-params` | Exactly the Zcash parameter content, shared across the ecosystem; the name persists by design |
| `qa/zcash/` | Real directory; legacy naming in tests is fine |
| `wallet.zero` | **A Zero feature**, not a legacy artifact |
| `zcash-loadblk`, `zcash-scriptch` | Actual thread names in the binary |
| `missing_zcash_conf` (`util.h:146`) | Exception *type* name; the message it throws already says `zero.conf`. Cosmetic only |

## 3. Fixed

`contrib/perf/performance-measurements.sh:86,116` wrote `$DATADIR/zcash.conf`;
Zero requires `zero.conf`, so no node started and **the script exited 0**.
Fixed 2026-09-10. This was the only *functional* naming defect found.

`zcash_rpc*` shell functions in the same script are internal helper names that
invoke `./src/zero-cli`. They are **not necessary** -- renaming them to
`zero_rpc*` would be accurate and harmless -- but they are also not wrong in
effect. Low priority; do it when the file is next edited for another reason.

## 4. Duplicated code, not inert -- tracked separately

The tromp solver driver is written twice: `miner.cpp:668-700` and
`src/test/equihash_tests.cpp:414-450`. See **P11**.
