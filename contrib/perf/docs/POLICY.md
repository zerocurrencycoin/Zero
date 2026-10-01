# Policy

Rules for perf work in this tree that no other document holds. General
documentation, comment and writing rules are Zero's: `AGENTS.md` and
`UpdateZero.md` DOC-CONVENTIONS. Rules this tree proposes for those are
`PLAN.md` Z5.

---

## Status

Each `PLAN.md` item carries two values. Reconciling them with Zero's
`TODO.md` lists is `PLAN.md` H3.

| Axis | Values | Question |
|------|--------|----------|
| Kanban | ToDo, InProgress, InTest, Finished | Where is the card |
| Disposition | Open, Blocked, Postponed, Aside, Fixed | Is the issue live, and if not, why |

The owner sets the entry and exit criteria for InTest. Blocked names its
blocker; Postponed names the decision or condition it waits on; Aside records
why the item is not done, so it is not proposed again. An item awaiting a
decision reads `decision:` in Disposition and states the options.

---

## Documents

- **One subject, one file, one owner.** The `README.md` documentation map is
  the only index; `docmap` gates it. Non-owners cite the owner; they do not
  restate it.
- **Task state lives in `PLAN.md` only.** A subject document holds no status
  section.
- **A value is stated once, in `Measures.md`, under an `M-*` id.** Other
  documents cite the id and restate the value only where the argument uses
  it. A specific `test-logs/` run is named only in `Measures.md` (as
  evidence) and in an open `PLAN.md` item. `PLAN.md` states a number only as
  a threshold or a decision option; tests and measures are rerun before an
  item closes.
- **Budgets.** About ten documents in `docs/`, each owning a module or
  subject. A consolidation whose diff is net-positive has failed. No
  meta-documentation: no migration plans, restructuring notes or
  per-directory indexes.
- **Point-in-time notes are archived, not updated.** Header:
  `> **Archived note.** Point-in-time evaluation, not maintained. Date, applies to (version or commit), superseded by.`
  Ask before editing one; a superseded note stays, marked.

### Enforcement

A rule with no check drifts. A check that cannot fail the build is a comment.

| Rule | Check | State |
|------|-------|-------|
| ASCII only | `fix_ascii.py`, `lint-perf.sh` `unicode-docs` | Enforced |
| Owned-scope lint clean | `lint-perf.sh` | Enforced |
| One map row per document | `check_docmap.py`, `docmap` | Enforced |
| Figures cited by `M-*`; no absolute paths | `check_citations.py`, `citations` | Enforced in `docs/`; wider scope is N12 |
| Runs named only in `Measures.md` and `PLAN.md` | `check_citations.py --runs`, `runs` | Ratchet |
| Table size and count; one owner per subject | `check_tables.py`, `check_concentration.py` | Ratchets |
| Values stated once | -- | Convention (D15) |
| One host per comparison; import idempotency | RecBench | Guard is N4 |

---

## Ownership

The repository root is read-only from this tree: no root file is edited,
added, removed or renamed here. Defects in Zero-owned documents go to
`PLAN.md` group Z.

| Tree | Owns |
|------|------|
| Zero | Code, tests, product documents (`README.md`, `TODO.md`, `TEST_ZERO.md`, `ZeroStruct.md`, `BUILD_ZERO.md`, `AtHeight.md`, `UpdateZero.md`). Source changes are reviewed there |
| ZeroPerf | `contrib/perf/`: the harness, these documents, a gated source layer |

| Identifier | Goes in | Tree |
|------------|---------|------|
| `M-*` | `Measures.md` | ZeroPerf |
| `OPS-*`, `WAL-*`, `FR-*`, `EXT-*`, `TST-*` status | `TODO.md` | Zero |
| `OPS-*`, `WAL-*`, `FR-*`, `INT-*` architecture | `ZeroStruct.md` | Zero |

Out of scope: zerowallet, Halo and Orchard, and Dev-fee or founders
material. Fat-wallet work uses out-of-tree `DevFeeWallets` material by
reference only, never by address or host path.

Automated rewrites write only inside `contrib/perf/` and confirm before
writing (`fix_ascii.py`).

---

## Code and build changes

A change proposed or made here is done when each step holds:

1. Every site found and changed, or stated as deliberately left.
2. Reachability stated: which builds and chains reach the code.
3. Built, and the changed path exercised on the binary; verified by artifact.
4. Pinned by a test that fails when the change is reverted.
5. Measurement bound to an `M-*` id with n and the pairing method.
6. Decision recorded: chosen, rejected, why.

Before changing inherited code, find its origin: `git log -S` here, then
across Zcash, Ycash, Hush3, Zclassic and Pirate. A construct shared by all of
them is upstream; its reason is usually in the originating commit, and
diverging needs a stated reason. Build, exercise and test logs for a
behaviour change go in `test-logs/<change>-<utc>/`.

---

## Lab discipline

- One trial per invocation; a campaign is a sequence of resumable
  invocations. A trial that cannot be restarted on its own may not run long.
- Every long-running producer -- launcher, subtest, agent -- writes evidence
  as it goes to `test-logs/<task>-<utc>/`: progress rows per poll, a result
  line per stage, an append-only findings file. A partial file is a result.
- Verify by artifact, not by exit status or a summary: check the completion
  marker and cross-check totals (`require_marker`, `require_counts_agree`).
- State n with every aggregate. A negative over few trials is not absence.
- Effort in bands (S, M, L, XL), not calendar estimates.
- Source `perflib.sh`; do not reimplement it. Run `perflib_selftest.sh` after
  changing it.

### Datadirs

Scratch is disposable; goldens are read-only. A launcher never writes to,
reindexes, rescans or loads blocks into a default datadir. `perflib.sh`
`dispose_datadir` applies `ZERO_PERF_DATADIR_POLICY` to an existing target:
`aside` (default; rename to `<path>.aside-<utc>`), `replace`, `keep`,
`external`.

- Production-datadir refusal runs before any policy, and its exit status is
  checked.
- `ZERO_PERF_ALLOW_LIVE_DATADIR=1` permits reading a live datadir only;
  destroying one also needs `ZERO_PERF_ALLOW_LIVE_DESTROY=1`.
- Protection covers every production datadir name on every platform
  (`zeropaths.py is_protected_datadir`), not the one `zerod` would use here
  (`default_datadir`).

### Run logging

A script that launches a node or produces a measurement writes
`<OUT_DIR>/<RUN_ID>-driver.log` through `perflib.sh` `log()`; `warn()` and
`die()` reach it too. `validate.sh` writes one `test-logs/validate-<utc>.log`
per run.

---

## Cleaning up

An artifact is reclaimed only if no result depends on it. `retention.py`
classifies and never deletes. Protected: named by a ledger row,
`test-logs/DATA_INDEX.md` or a perf document, or holding a distilled result
(`SUMMARY.txt`, `FINDINGS.md`, `*.tsv`, `*.csv`, `measures_*.md`,
`*.json`). Everything else is a candidate for review.

Reclaim by trimming raw capture inside a protected artifact once its
distilled result stands alone, not by deleting artifacts. Age is no guide:
the oldest captures are the most cited, and `/tmp` already took the raw runs.

Never reclaimed: `test-logs/archives/`, ledgers and their `.v2` companions,
`test-logs/DATA_INDEX.md`, `reindex-profile/bench-summaries/`, superseded
results (marked, not deleted).
