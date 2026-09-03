# Policy

Rules for perf work: what is enforced, what is convention, who owns what, and
how to clean up without destroying evidence.

---

## 1. Status vocabulary

Two parallel status structures. They answer different questions and are not
interchangeable.

### 1.1 Kanban -- the work-flow axis

Where an item sits in the flow of work:

**ToDo -> InProgress -> InTest -> Finished**

**The project owner defines what these mean**, including the entry and exit
criteria for `InTest`. They are not redefined here, and this document does not
assert a test standard on the owner's behalf.

### 1.2 Disposition -- the tracking axis

Whether an item is live at all, and why not if it is not. Ordered:

| Disposition | Meaning |
|-------------|---------|
| **Open** | Live and progressing |
| **Blocked** | Live, cannot advance; blocker named |
| **Finished** | Complete |
| **Postponed** | Live, waiting on a person's decision |
| **Aside** | Not doing; reason recorded, kept so it is not re-proposed |

### 1.3 "Finished", not "Done"

The terminal state is **Finished**. `Done` is not used: it reads as "I stopped
working on it" rather than "this is complete".

---

## 2. Documentation rules

From `AGENTS.md`, which governs the whole tree:

- **Full node only.** Zerowallet is out of scope.
- **No emojis or decorative Unicode** in any document except the root
  `README.md`. Use `--` not em-dash, `->` not arrow, `"` not curly quotes,
  `...` not ellipsis.
- **No parenthetical asides in headings.**
- Direct, concise, factual. No superlatives without evidence.
- **Do not remove, overwrite, or add files without explicit confirmation.**

Plus, for this directory:

- **One subject per document.** A new file needs a stated reason and
  confirmation.
- **Numbers live in one place** and are cited by `M-*` id, never restated.
- **Point-in-time notes are archived, not updated** (S5).

### 2.1 What enforces what

The recurring failure here is a rule that is written down and enforced by
nothing. Four have drifted that way. Current state:

| Rule | Enforcement | State |
|------|-------------|--------|
| ASCII only | `fix_ascii.py`, `lint-perf.sh` | **Enforced** -- `unicode-docs` is in the default `CHECKS` (`lint-perf.sh:107`); backlog cleared, 0/0 |

### ASCII policy: what the checker tolerates, and why

`fix_ascii.py` splits non-ASCII into four classes rather than rewriting
everything, because two of them must not be rewritten:

| Setting | Contents | Why |
|---------|----------|-----|
| `REPLACE` | em/en dash, arrows, curly quotes, ellipsis, middle dot, bullet, multiplication sign, almost-equal, NBSP | An exact ASCII equivalent exists; `--fix` rewrites these |
| `FLAG_ONLY_RANGES` | emoji and pictographs, misc symbols and dingbats, variation selectors | No safe equivalent. Reported for a human, never auto-rewritten |
| `TOLERATED` | section sign | Conventional section notation in these documents, not decoration |
| `SKIP_PATH` | vendored source, `depends/`, captured data under `mine/` and `dis-nodes.txt` | Captures preserve what was captured; normalising them corrupts the record |
| `EXEMPT` | `README.md` in any directory | `AGENTS.md` exempts it |

**Node source is deliberately not normalised.** Three classes were audited and
kept:

- **Mathematical and spec notation** -- Groth16 proof elements in
  `zcash/JoinSplit.hpp`, ZIP-208 notation in `consensus/params.cpp`. These tie
  the code to the protocol spec; ASCII substitutes lose that.
- **Quoted data** -- `wallet/paymentdisclosure.h` renders byte `0xFF` as a
  literal. Rewriting it makes the comment factually wrong.
- **Inherited curly apostrophes** -- an NDSS citation in `equihash.cpp` and two
  verbatim-Zcash strings in `rpcwallet.cpp`. Those two are **RPC help text**,
  not comments: they reach operator terminals, so changing them is a product
  decision, not a lint fix.

| Owned-scope lint clean | `lint-perf.sh` | Enforced, passing |
| Numbers cited by `M-*` | -- | **Convention only.** Proposed: `TASKS.md` A1c |
| Full node only | -- | **Convention only.** 475 lines of wallet UI docs present |
| One host per comparison | RecBench + aggregation guard | Helper exists; guard is `TASKS.md` A2f |
| Import idempotency | `fingerprint` | Enforced, but v1 omits platform/build -- `TASKS.md` A2e |

Backlog counts are regenerated into `contrib/perf/lint_backlog.json` rather
than restated in prose, so they cannot go stale.

---

## 3. Build feature classes

Not all compile-time flags mean the same thing, and treating them uniformly
produced a wrong result: an early bundle matcher classified this stock build as
`custom`. Defined in `RecBench bundles (`recbench/RecBench.md`)`:

| Class | Flags | Property | In bundle key |
|-------|-------|----------|---------------|
| **Architectural** | `ENABLE_ZMQ`, `ENABLE_PROTON` | Stable ecosystem choices, years old, effectively constant across scenarios | **No** |
| **Scenario** | `ENABLE_WALLET`, `ENABLE_MINING` | Compiled default **and** a runtime equivalent; vary between test batches | **Yes** |
| **Perf** | `ZERO_PERF`, `ZERO_FDCACHE` | Lab instrumentation, off in shipped builds | **Yes** |

**Why architectural flags are excluded from the key.** ZMQ has been a stable
choice across the Zcash family for years and does not vary between ZeroPerf
scenarios. Including it would mean a ZMQ-disabled build of an otherwise
identical configuration reads as an unrelated bundle, fragmenting a comparison
for no measurement reason. It is still *recorded* on every row.

**Why scenario flags are included, and recorded twice.** `ENABLE_WALLET` has
`-disablewallet`; `ENABLE_MINING` has `-gen` / `-genproclimit`. So the compiled
capability and the runtime state can disagree, and both matter:

- A wallet-capable binary run with `-disablewallet` still carries wallet code
  and its startup path.
- A binary built without wallet support cannot run one at all.

These are **different measurements** and must not collapse. Every row therefore
carries `features.effective`:

```json
"effective": {"wallet_built": true,  "wallet_active": false,
              "mining_built": true,  "mining_active": false}
```

`null` means unknown, never "off".

---

## 3.1 Existing datadirs: disposition policy

When a launcher targets a datadir that already exists, what happens is set by
`ZERO_PERF_DATADIR_POLICY` and implemented once in `perflib.sh`
(`dispose_datadir`). Before this, nine sites did an unconditional `rm -rf`.

| Policy | Behaviour |
|--------|-----------|
| **`aside`** | **Default.** Rename to `<path>.aside-<utc>`, then create a fresh tree. Nothing is lost |
| `replace` / `recreate` | Delete and recreate. **Destructive**; warns. Uses `rm -r`; `-f` only under `ZERO_PERF_FORCE=1` (scripts expose `--force`), so a permission error surfaces instead of being forced through |
| `keep` | Use in place. Warns that results may reflect prior state |
| `external` | Do not touch; the caller manages the tree |

**Why `aside` is the default.** A re-run must never silently destroy the
previous run's evidence -- that evidence is often the only record, since lab
scratch lives in `/tmp` and is reclaimed (S6). Set-aside costs disk; a lost
capture costs a re-run, or the result outright.

Three rules the implementation enforces:

- **Production-datadir refusal runs first**, before any policy.
  `ZERO_PERF_FORCE=1` controls only whether `rm` gets `-f`; it is not an
  authorisation to touch a production datadir.
- **Reading a live datadir and destroying one are separate permissions.**
  `ZERO_PERF_ALLOW_LIVE_DATADIR=1` permits a lab to *read* a live datadir. It
  does **not** permit `aside`, `replace` or `recreate` on one -- that needs
  `ZERO_PERF_ALLOW_LIVE_DESTROY=1` as well. The read override is routinely set
  for a whole session, so a destructive policy would otherwise run
  unchallenged; it deleted a datadir during development before this split.
- **Protection is platform-independent.** Every plausible production datadir
  name is gated on every host: `~/.zero`, `~/zero`,
  `~/Library/Application Support/{zero,Zero}`, `%APPDATA%\zero`, and the
  contents of each. A `~/.zero` on macOS is not what `zerod` would create
  there, but it is very plausibly a real datadir copied from a Linux machine --
  and the incident this guards against was **an attempt to delete a production
  datadir**, not a mis-mapped path.
- **The guard's exit status is checked.** `refuse_live_datadir` reports by exit
  status; ignoring it moved a directory during development. `perflib.sh` now
  fails closed, and the self-test asserts it.

**Two questions, two functions** (`zeropaths.py`) -- conflating them is a bug
in either direction:

| Question | Function | Breadth |
|----------|----------|---------|
| Which datadir would `zerod` use here? | `default_datadir()` | one path, this platform |
| Might this be somebody's real datadir? | `is_protected_datadir()` | every name, every platform |

Destructive guards use the second. Using the first would have left a
production `~/.zero` unprotected on macOS.

---

## 3.2 Run logging

Any script that **launches a node or produces a measurement** writes a durable
log, keyed by `RUN_ID` alongside its artifacts. Set `DRIVER_LOG` and
`perflib.sh`'s `log()` tees to it.

| Script kind | Log |
|-------------|-----|
| Node launchers and measurement drivers | `<OUT_DIR>/<RUN_ID>-driver.log` (or `driver.log`) |
| The regression gate | `test-logs/validate-<utc>.log`, one per run |
| Short helpers and one-shot utilities | stdout is sufficient |

Two rules, each of which failed in practice before being written down:

- **`warn()` and `die()` go to the log as well as stderr.** They used to go to
  stderr only, so a failed run left a driver log showing normal progress and no
  error -- the operator saw the failure on the terminal and the archived log
  did not record it.
- **A result that exists only on a terminal cannot be cited.** A backgrounded
  or piped run kept its measures and lost every decision that produced them:
  which datadir policy applied, what was unpacked, whether the ledger append
  succeeded. `validate.sh` logs per run rather than to one file, so a failure
  is not overwritten by the next green run.

---

## 4. Lab discipline

- **No unrestartable long batches.** Do not start a batch where each trial
  exceeds ~20 minutes unless each can be restarted individually.
- **One trial per invocation.** A campaign is a sequence of resumable
  invocations, not one long process.
- **Scratch is disposable; goldens are read-only.** Never mutate an original.
- **Never use the default datadir as a writable lab datadir**, and never launch
  `-reindex` / `-rescan` / `-loadblock` against it. Guard:
  `datadir_guard.sh`. Override only via `ZERO_PERF_ALLOW_LIVE_DATADIR=1`.
- **Effort in bands (S/M/L/XL)**, never calendar estimates without measured
  evidence.

---

## 5. Archiving point-in-time notes

Research notes and evaluations of a specific version at a specific time are
kept as they were. They are **not** folded into the durable set and **not
updated by default**.

Header every archived note:

```
> **Archived note.** Point-in-time evaluation, not maintained.
> Date: 2026-06-08. Applies to: v4.0.1 / <commit or "unknown">.
> Superseded by: <doc, or "nothing">. Ask before updating.
```

- **Ask before updating.** The usual right answer is a new dated note, not an
  edit that destroys the record of what was believed then.
- **Date and version are mandatory.** Where unknown, estimate and mark it
  (`date_confidence: estimated`). An estimate with a marker beats an absence,
  and beats a precise-looking fabrication.
- **Superseded notes stay**, marked. Do not delete.

---

## 6. Cleaning up large test configurations

Lab runs leave large trees behind -- `test-logs/` is ~101 MB across 39
artifacts. The tempting cleanup ("delete anything older than N days") destroys
the evidence behind published numbers, because **age does not correlate with
value**: the oldest captures here are the most cited.

### 6.0 Where the disposable material actually is

Test environments run out of **`/tmp`** by design -- `tiny_baseline.sh` defaults
`LAB=/tmp/zero-lab-<snap>-baseline-$$`, and lab datadirs are explicitly
disposable. That is the cleanup surface: `/tmp` is reclaimed by the OS and
nothing there is a record.

The consequence for `test-logs/` is the opposite of what a disk-space instinct
suggests: **what survived the scratch tree is, by construction, the part
somebody chose to keep.** The raw run it came from is usually already gone.

### 6.1 The rule

**An artifact may be reclaimed only if no result depends on it.** Established
by `contrib/perf/retention.py`, which never deletes -- it classifies.

An artifact is **PROTECTED** if any hold:

1. A ledger row names it (`cpu_ledger` `source`, `ledger` `notes`).
2. `test-logs/DATA_INDEX.md` names it.
3. Any perf document names it -- an `M-*` measure's evidence.
4. It contains a distilled result: `SUMMARY.txt`, `FINDINGS.md`, `*.tsv`,
   `*.csv`, `measures_*.md`, `*.json`.

Everything else is a **CANDIDATE** -- reviewable, not automatically doomed.

```bash
contrib/perf/retention.py              # report with reasons
contrib/perf/retention.py --candidates # only reclaimable
contrib/perf/retention.py --script     # emit commands to READ, not pipe to sh
```

Current state: **39 protected, 0 candidates.** Nothing is safely deletable
wholesale today.

### 6.2 Trim inside an artifact, keep the result

The useful reclamation is not deleting artifacts but **trimming regenerable
raw capture data from artifacts whose summaries are the actual record**:
`.trace`, `.xml`, `.tar.gz`, `.tgz`. Currently **32 MB** of such bulk sits
inside protected artifacts.

Before trimming, confirm the distilled result is present and self-sufficient --
that a reader can still reach the cited number without the raw capture. If the
raw data is the only evidence for a published figure, it is not bulk, it is the
record.

### 6.3 The failure this guards against

While building the classifier, `test-logs/archives/` (31.9 MB) was flagged as a
deletable candidate. It is in fact the evidence archive for **M-WAL-SYNC-FAT** --
cited by `Measures.md` and `Perf.md`, but written as `archives/...tar.gz`
without a `test-logs/` prefix, so a path-prefixed scan missed it.

The classifier now scans every perf document for bare artifact names, and its
self-test asserts `archives/` stays protected. **The lesson is the general
one: an automated "safe to delete" answer is only as good as its citation
scan**, so the tool defaults to protecting and prints reasons for review rather
than executing.

### 6.4 What is never reclaimed

**`test-logs/archives/` is never deleted, under any circumstance.** Not by age,
not by size, not by an absent citation. It holds packed evidence whose scratch
tree lived in `/tmp` and is long gone, so the tarball is frequently the **only
surviving copy** -- for example the fat-wallet run behind `M-WAL-SYNC-FAT`
(~33 MB). `retention.py` hard-codes it as never-reclaimable, independent of the
citation scan, and excludes it from bulk-trim suggestions. A self-test asserts
it stays protected even with no citations at all.

Also never reclaimed:

- Ledgers (`ledger.jsonl`, `cpu_ledger.jsonl`) and their `.v2` companions.
- `test-logs/DATA_INDEX.md`.
- Anything under `reindex-profile/bench-summaries/`.
- Superseded results -- marked, not deleted.

---

## 7. Ownership

| Tree | Owns |
|------|------|
| **Zero400** | Authoritative code, tests, and product documents (`README.md`, `TODO.md`, `TEST_ZERO.md`, `ZeroStruct.md`, `BUILD_ZERO.md`). Changes to `src/` are reviewed there |
| **ZeroPerf** | `contrib/perf/` -- the harness, these documents, and a gated source layer |

Perf work that needs a product change is **specified here and reviewed in
Zero400**. Do not restructure Zero400-owned documents from this tree: it
contradicts ownership and creates merge conflicts against the tree that owns
them.

### 7.1 Routing by identifier

Which document owns which prefix. Put an item where its prefix says, rather
than where it was discovered.

| Identifier | Goes in | Tree |
|------------|---------|------|
| `M-*` -- measure ids, campaign numbers | `../Measures.md` | ZeroPerf |
| `PERF-*` -- ConnectBlock optimization narrative | `FINDINGS.md`; numbers cited from `Measures.md` | ZeroPerf |
| `OPS-*` / `WAL-*` / `FR-*` / `EXT-*` -- status and task text | `TODO.md` | Zero400 |
| `OPS-*` / `WAL-*` / `FR-*` -- architecture | `ZeroStruct.md` | Zero400 |
| `OPS-AT-HEIGHT` | `AtHeight.md` procedure; status in `TODO.md` | Zero400 |
| `INT-*` | `ZeroStruct.md` S11.7 | Zero400 |
| `TST-*` -- test and gate work | `TEST_ZERO.md`, `TODO.md` | Zero400 |

**A number with no `M-*` binding is not yet a measure.** `Measures.md` owns
figures; everything else cites the id.

Zero400-owned documents this tree reads but does not edit: `TODO.md`,
`TEST_ZERO.md`, `ZeroStruct.md`, `AtHeight.md`, `BUILD_ZERO.md`,
`WitnessReindex.md`, `ExtTests.md`, `UpdateZero.md`.

### 7.2 Out of scope for this tree

**Dev-fee and founders material is project-internal.** Founders and DevFee
payee addresses, and address-ops scripts, stay out of this tree. Do **not** put
DevWallet handling, scripting, or host paths into `ZeroStruct.md`,
`TEST_ZERO.md`, `TODO.md`, `AtHeight.md`, `Measures.md`, or any other tracked
document.

Perf work touching fat-wallet behaviour uses out-of-tree `DevFeeWallets`
material **by reference only** -- never by copying addresses or host paths into
a tracked document.

Also out of scope: zerowallet (full node only), and Halo / Orchard (not Zero
consensus).

### 7.3 No absolute paths in tracked documents

Reference a document by **name alone** (`TENTZero.md`, `CDBRewrite.md`), a
sibling by repo-relative path (`contrib/perf/docs/TASKS.md`), and anything
outside the repo by name plus "(out of tree)" or a placeholder
(`<linearize>/bootstrap.dat`).

Never write `/Users/<name>/...` or `~/Work/...` into a tracked document. Such a
path is wrong for every reader but one, leaks a username into a public
repository, and breaks silently the moment a file moves -- as 11 references to
`TENTZero.md` did. For runtime paths that genuinely vary, use `$HOME` or an
env var the launchers already set.

Enforcement: none yet; candidate for `lint-perf.sh` alongside the citation
check (`TASKS.md` A1c).

### 7.4 Automated rewrites stay inside owned scope and confirm their blast radius

`fix_ascii.py --fix` writes only under `contrib/perf/`. Running it
tree-wide once rewrote eight Zero400-owned root documents, which this tree does
not own (S7), and its `U+00B7 -> '-'` mapping turned products into apparent
subtraction in a Groth16 pairing equation.

Two rules follow:

- **Report widely, write narrowly.** Scanning the whole tree is useful; writing
  to it is not this tree's call. `--any-path` exists as a deliberate override.
- **Never bulk-rewrite a document containing formulas.** The safe-substitution
  table is safe for prose, not for mathematics. Middle dot, minus sign and
  arrows all carry meaning there. Fix those by hand, per site.

Violations found in Zero400-owned files are **reported to that tree**, not
fixed here.

`fix_ascii.py --fix` now enforces three guards, each with an explicit
override so a deliberate operator is never blocked:

| Guard | Refuses | Override |
|-------|---------|----------|
| Scope | writing outside `contrib/perf/` | `--any-path` |
| Formula content | any file that looks mathematical | `--allow-formula-files` |
| Blast radius | rewriting more than 5 files | `--yes` |

Interactively it also lists the files and asks before writing. All three are
asserted in the tool's `--self-test` by behaviour -- creating real files and
checking they are byte-identical afterwards -- not by inspecting source text.
