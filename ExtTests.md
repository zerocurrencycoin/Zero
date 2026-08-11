# ExtTests -- Extended harness notes (maintainer)

Working inventory and contributor commands live in **TEST_ZERO.md**. This file holds **current** extended coverage notes, design decisions, and gaps that are not part of the public runbook.

**Scripts win.** Tier membership is only in `qa/pull-tester/rpc-tests.sh`.

---

## 1. Interpreting results (shared with public runbook)

- Without **`--strict`**, `run-tests.sh` may print **WARNING** and still exit **0**. With **`--strict`**, any failed step exits **1**.
- **`skip_test`** exit **0** is a skip, not a pass.

| Signal | Meaning |
|--------|---------|
| **`PASS: <step>`** | Subprocess exited **0** |
| **`FAIL: <step>`** | Non-zero; see **`test-logs/`** |
| **`WARNING: one or more steps failed`** | Failures occurred; exit **0** unless **`--strict`** |

---

## 2. Design decisions (pervasive)

### Maturity and clean chain

- Regtest **`COINBASE_MATURITY = 720`** (not Bitcoin 100). Prefer **`initialize_chain_clean`** plus explicit mine helpers when porting wallet scripts that assume short maturity.
- Tip-200 warm cache scripts often need relative heights or a clean chain + `generate(200)` rather than hard-coded tip assumptions.

### Promote rule

A basename that exits **0** when run alone is **not** in the contributor gate until it is moved into a pass array in `rpc-tests.sh`, CSV regenerated, and **TEST_ZERO** §3 updated in the same change set. Hold reasons: **TEST_ZERO** §5.

### Layer roles

| Layer | Role |
|-------|------|
| Exclusive Boost | Empty-wallet RPC gates |
| Ext / Tier B scenarios | Populated wallet / multi-node |
| GTest | Wallet and unit paths |

---

## 3. `CachedWitnessesCleanIndex` (GTest)

**Current state:** Excluded from the working gate (`qa/zcash/test_filters.sh`). Run alone via `--fail` or `--gtest_filter=WalletTests.CachedWitnessesCleanIndex`.

**Notes:**

- Not a tier-membership bug: the case needs a reindex-style harness the default wallet fixture does not provide.
- Separate concern: harden `GetSproutNoteWitnesses` / `GetSaplingNoteWitnesses` against corrupt/empty witness caches (avoid OOB on missing witnesses).
- Tracking: **TST-WITNESS-REINDEX** / **WitnessReindex.md** when that hub is active.

---

## 4. Equihash and mining tests

**Facts:**

- Mainnet PoW is **(192,7)**; regtest uses **(48,5)** for fast tests.
- Boost **`equihash_tests`**: mainnet genesis **(192,7)** (valid + corrupt `nSolution`), `1927EQ.txt` / `1927EQ_h1.hex`, regtest **(48,5)**. Dispatch throws on other `n,k`.
- Boost **`miner_tests`**: in-process `CreateNewBlock` + (48,5) solve + `ProcessNewBlock` (`ENABLE_MINING`). No frozen `blockinfo[]`.
- Timed verify/solve: `contrib/ops-validate.sh verifyeq` / `solveeq` (optional N). Isolated regtest `generate`: `contrib/ops-validate.sh mine`. Operator mainnet CPU miner is `setgenerate` / `gen=1` (TEST_ZERO §8.5), not `mine`.
- Python Equihash in `qa/` is not authoritative and not a (192,7) solver. `zcash_person` is ZcashPoW; node `InitialiseState` is ZERO_PoW.

Do not "adjust" failing vectors by changing mainnet Equihash parameters.

---

## 5. External interfaces (RPC / REST / indexes)

**Current working coverage (Tier B pass):** `addressindex`, `spentindex`, `timestampindex`, `getrawtransaction_insight`, `rest` -- explorer-oriented fixtures.

**Still under development (Bfail / Efail):** see **TEST_ZERO** §6. Notable gaps:

| Area | Status |
|------|--------|
| Pure `-txindex` (`txindex.py`) | Bfail Debug; promote after green |
| Shielded `z_*` depth | Mostly covered; a few high-value holes remain in Bfail |
| Zeronode RPC arg validation | Tracked as **TST-03** |
| Config / CLI surface parity | No automated check |

Insight / explorer **host** install is out of scope for this tree.

---

## 6. Founders window (regtest)

Regtest founders window uses **`REGTEST_FOUNDERS_START` / `STOP`** (see `chainparams`). Helpers in the Python harness (`block_subsidy`, `founders_share`, `mine_until_mature`, `assert_raises_message`, …) support subsidy and founders shape checks. **`founders_window.py`** is on Tier B pass when present in the inventory CSV.

---

## 7. From former TEST_ZERO deep reference (retained)

Keep these as standing notes; do not reintroduce dated run diaries into **TEST_ZERO**:

- **RPC harness cache:** `<repo>/cache/` is gitignored; safe to delete; Tier A rebuilds toward maturity **725**.
- **Parallel Tier A (`--jobs>1`):** optional throughput; keep serial for merge gates.
- **`--all` wall time:** re-record when the working RPC count changes; do not treat old walls as product truth.
- **Coinbase maturity / mining acceleration:** prefer explicit mine plans over tip-relative assumptions when Blossom or fee-start heights matter on regtest.

When adding new investigations, record **current state and next action** only -- move process narrative and dated PASS/FAIL diaries out of public docs.
