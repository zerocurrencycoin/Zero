# ReleaseNotes401 -- v4.0.1 release notes (draft contract + outline)

**Status:** Draft. Intended to become the **GitHub Release** body for **v4.0.1** and, if kept in-tree, a short public file in the ship set. Not a substitute for README / BUILD_ZERO / TEST_ZERO / ZERO_COIN.

**Tag / tip (this tree):** `v4.0.1` / `fe59146a3` (detached or `testfix-401`). Fill **Highlights** and **Upgrade** from the merge set before GA; do not paste git log.

---

## 1. Audience

| Audience | What they need from this file | What they should open instead |
|----------|-------------------------------|-------------------------------|
| **Node operators** (upgrade in place) | Breaking changes, required conf/flags, downtime, verify steps | BUILD_ZERO for rebuild; man/`-help` for options |
| **Miners / pools** | Coinbase / subsidy / zeronode behavior **deltas only** | ZERO_COIN for full schedule and addresses |
| **Exchanges / integrators** | RPC/API deltas, branch-id / NU notes if any, supply narrative pointers | ZERO_COIN glossary + economics; RPC help |
| **Contributors** | Gate command reminder; “docs moved” one-liners | TEST_ZERO inventory; TODO open items |
| **Not this file** | Insight host install, DevFee ops, Perf campaigns, cherry-pick hubs | Maintainer trees only |

One page for humans reading a **release**. Standing reference stays in the ship docs.

---

## 2. Format

Keep the published note **short** (target: screenful to ~2 pages). Fixed section order:

```text
# Zero v4.0.1

One-paragraph summary (what this release is).

## Highlights
- Bullet deltas operators care about (behavior, RPC, wallet, build).

## Upgrade notes
- From previous public tag: required actions, incompatibilities, datadir/wallet.

## Compatibility
- Platforms / build OS floor (pointer to BUILD_ZERO; no host names).
- Deprecation: pointer to README / getdeprecationinfo (no height paste that goes stale).

## Documentation
- Ship-set map (one table or bullets) -- names + one-line purpose only.

## Known limitations
- Honest, short; link TODO only for contributor follow-ups.

## Verify download (when signing ships)

RC still records hashes/signatures as present or **explicitly missing** (TEST_ZERO §8). Omit this section from the GitHub paste until REL-SIGNING lands; do not ship without recording the gap.
```

**Style:** Factual, dated only for the **release day**. No emoji requirement; match README tone if pasted to GitHub. ASCII punctuation per AGENTS for in-tree copy.

**GitHub Release:** Same body as this file’s published sections (omit this contract preamble §1–3 when pasting).

---

## 3. Inclusion rules (avoid duplication)

### Include here

| Include | Rule |
|---------|------|
| **Delta only** | Changed since last public release (or “first curated 4.0.x note”). |
| **Operator action** | Must upgrade / migrate / set flag / rebuild params. |
| **User-visible behavior** | RPC result shape, soft errors, wallet file name, default ports if changed. |
| **Doc ship-set change** | “Public docs are now README, ZERO_COIN, BUILD_ZERO, TEST_ZERO, …” one list. |
| **Known breakage** | Something that will bite upgrades (with workaround one-liner). |

### Exclude here (owning doc)

| Exclude | Owner |
|---------|--------|
| Full emission / halving tables, address lists | **ZERO_COIN** |
| Build dependency lists, platform how-to, depends troubleshooting | **BUILD_ZERO** |
| Tier A/B inventory, `--strict` runbook, harness design | **TEST_ZERO** |
| Open engineering backlog | **TODO** |
| Structures, caches, Insight backend flags, ABI matrices | Maintainer docs (not linked from public RN) |
| Commit lists, PR archaeology, dated lab tips | Never |
| Tip height / live supply snapshots | Never (transient) |
| Signing procedure detail | Omit until published; then short verify steps only |

### Anti-duplication rule

> If a paragraph would still be true for **v4.0.2** without edits, it belongs in a standing ship doc, not in ReleaseNotes401.

Release notes may **point** (“see ZERO_COIN -- Halving calendar”) but must not **copy** the table.

When a standing doc absorbs a fact that was only in RN, **delete** it from RN on the next release (or leave a one-line “moved to …”).

---

## 4. Relation to the public ship set

| File | Role vs ReleaseNotes401 |
|------|-------------------------|
| **README** | Always-current front door; RN is version-scoped |
| **ZERO_COIN** | Economics truth |
| **BUILD_ZERO** | How to build |
| **TEST_ZERO** | How to validate |
| **TODO** | What’s still open |
| **ReleaseNotes401** | What changed in **this** release |

Optional: add one README row under Documentation for “Latest release notes” pointing at the GitHub Release (prefer URL) or this file if kept in-tree.

**Do not** put ReleaseNotes401 in the maintainer-only hold set if it ships with GA; keep it free of UpdateZero / ExtTests / host paths.

---

## 5. v4.0.1 outline (fill before GA; stubs only)

### Summary

Zero **v4.0.1** full node (`zerod`, `zero-cli`, `zero-tx`): curated docs ship set, harness and wallet/RPC hardening, build/script fixes. *(Rewrite one sentence at freeze.)*

### Highlights (candidates -- confirm against merge set)

- Public documentation ship set: README, ZERO_COIN, BUILD_ZERO, TEST_ZERO, CONTRIBUTING, TODO, AGENTS, `doc/man/` (maintainer planning docs held back from GA merge as applicable).
- Contributor gate: `./contrib/run-tests.sh --strict` (see TEST_ZERO).
- Regtest founders window and related harness coverage (see TEST_ZERO / ZERO_COIN for economics; no tip stats).
- Wallet/RPC soft-path and getalldata-related hardening *(list only user-visible items at freeze)*.
- Build/logging script fixes (`zcutil` init_logging, Linux test script fixes) *(operator-relevant only)*.

### Upgrade notes

- Build from tag with BUILD_ZERO; fetch params as usual.
- Wallet file remains **`wallet.zero`**; back up before upgrade.
- *(Add any conf flag or RPC breaks discovered at freeze.)*

### Compatibility

- Build OS sets the binary glibc/libstdc++ floor; see BUILD_ZERO.
- Automatic deprecation: long window; `getdeprecationinfo` / README -- not a near-term halt.

### Documentation

Point at the ship-set table in README (do not paste ZERO_COIN tables).

### Known limitations

- Release signing / notarization procedure not published yet *(internal REL-SIGNING)*. Produce checksums/signatures during release prep; unsigned CI is not a release.
- *(Pull 2–4 items from TODO that affect operators; no Zerowallet / Insight host.)*

---

## 6. Maintenance

| Event | Action |
|-------|--------|
| **GA freeze** | Fill §5; strip this file’s §1–3 contract into UpdateZero or delete preamble from the GitHub paste |
| **Next release** | New `ReleaseNotesNNN.md` or `doc/release-notes/4.0.2.md`; do not grow 401 forever |
| **Fact moves to ZERO_COIN/BUILD** | Remove from RN; leave pointer once |

**Owner:** release manager. **Reviewers:** anyone owning ship docs accuracy.
