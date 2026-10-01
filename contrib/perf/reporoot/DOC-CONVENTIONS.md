# DOC-CONVENTIONS: proposed additions

Draft for Zero's `UpdateZero.md` DOC-CONVENTIONS, the one place for
documentation and comment rules. Each bullet is a rule DOC-CONVENTIONS does
not yet state; sources are this tree's former `POLICY.md` writing rules and
the `docstruct` Claude Code skill. Same bullet form as the existing section.

- *Provenance.* Identify a result by commit or version and build features,
  not by date.
- *Values.* State a measured value once, in its register, under an id; cite
  the id elsewhere. Restate the value only where the argument uses it.
- *References.* Cite a heading title, never a section number, and only where
  the reader must go to act. Never mention a deleted file; git holds it.
- *Failures.* Keep a past attempt only when it informs a decision, as a
  list: attempt, failure mode, closed or not. Describe a failure by the step
  that went wrong.
- *Structure.* A new document needs a subject no document owns. No
  meta-documents: no migration plans or per-directory indexes. A
  consolidation that grows the set has failed. Status lives in the work
  register, not in findings.
- *Exposition.* Define a term at first use. Prose before any table that
  uses it; tables only for short parallel entries.
- *Rules.* A rule names the check that enforces it, or says it is advisory.
- *Automated rewrites.* Report widely, write narrowly. Never bulk-rewrite
  text that carries formulas.
