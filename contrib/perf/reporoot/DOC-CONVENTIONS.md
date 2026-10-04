# DOC-CONVENTIONS: replacement text

Draft for Zero. Replaces the DOC-CONVENTIONS entry in `UpdateZero.md`
section 7 "Documentation" (Zero `72e421e41`), from its bold lead line through
the *Streamlining* bullet. It keeps every existing rule, adds the rules this
tree used, and groups them as code, documents, and writing.

---

**DOC-CONVENTIONS -- Documentation and comment rules.** One rule set for Zero
repositories. Target: `AGENTS.md`, contributor instructions and the shared
agent configuration; until adopted there, guidance.

*Code*

- *Inline comments.* Explain why: invariants, cross-component constraints,
  consensus and locking requirements. No task ids, status, dates, measured
  figures, change history, personal paths, or references to planning
  documents.
- *Function and class documentation.* Doxygen `/** ... */` on interfaces and
  non-trivial functions: purpose, parameters, returns, preconditions, locking
  and thread safety, failure behavior; as long as the interface requires.
- *File headers.* Copyright and license; optionally a one-line purpose. No
  change logs.
- *Tests.* More latitude than production code: scenario, choice of heights
  and amounts, known failures, how to run. Python tests open with a
  docstring.
- *Scripts.* Shebang, copyright for Zero-authored scripts, one-line purpose.
  Scripts with options provide `usage()` behind `-h` / `--help` (Usage, Modes
  or commands, Options, Env) and the header refers to it; scripts without
  options state usage on one header line. The script, not a document, is the
  source for its invocation.
- *Upstream, vendored, ported code.* Keep original comments when moved or
  lightly edited; correct only factual errors; keep diffs minimal.

*Documents*

- *Public documents.* README is the public map. No references to internal
  documents or external files. ASCII, `##` headings, no parenthetical
  headings, repo-relative paths, current state only, no transient values.
- *Internal documents.* Section 1 of this file is the internal map. External
  documents by name, never by filesystem path; other Zero repositories by
  repo-relative path only when necessary. Transient counts only in section 7
  "Validation counts".
- *Reference records* (for example ZcashFixes). Keep comparisons, timelines
  and third-party detail; restructure for readers, do not cut. Verify claims
  and link sources inline and in a references section.
- *Structure.* One subject per document, one owner per subject; others cite
  the owner. A new document needs a subject no document owns. No
  meta-documents: no migration plans, restructuring notes or per-directory
  indexes. A consolidation that grows the set has failed. Status lives in the
  tracking file, not in findings.
- *References.* Cite a heading title, never a section number, and only where
  the reader must go to act. Never mention a deleted file; git holds it.
- *Values.* A measured value is stated once, in its register, under an id,
  with its provenance: commit or version and build features, not a date.
  Elsewhere cite the id; restate the value only where the argument uses it.

*Writing and editing*

- *Sizing.* Content drives length: what a reader needs to use, change, or
  validate the code or decision. No fixed line limits.
- *No filler.* Every sentence states a fact, a decision, or an action. Cut
  generic, non-committal, conversational text: vague hedges, feel-good
  assessment, fill-in placeholders. Tracking status (postponed, not
  scheduled, does not gate a release, decide after X) stays. Applies to
  documents, comments and help text.
- *Exposition.* Define a term at first use. Prose before any table that uses
  it; tables only for short parallel entries.
- *History.* Only where a decision's rationale depends on it. A past attempt
  stays as a list -- attempt, failure mode, closed or not -- and a failure is
  described by the step that went wrong.
- *Streamlining.* Classify a document before cutting it; move unique facts
  rather than delete them; verify done and open claims against the code.
- *Automated rewrites.* Report widely, write narrowly; confirm before
  writing. Never bulk-rewrite text that carries formulas.
- *Enforcement.* A rule names the check that enforces it, or is marked
  advisory.
