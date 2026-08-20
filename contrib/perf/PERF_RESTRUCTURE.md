# Proposal: restructuring Perf.md

Not applied. Perf.md is 1871 lines and the single most-cited document here;
restructuring it is a deliberate act, not a cleanup to slip in.

## What is wrong, measured

| Symptom | Evidence |
|---------|----------|
| Section 0 is the document | Lines 11-1370 = **73%** of the file sits under "0. Status at a glance", before section 1 "Scope and method" begins |
| 21 subsections under one heading | 0.0, 0.1, 0.1a, 0.2, 0.2a, 0.2b, 0.3 ... 0.16 -- numbering already broke (no 0.10) |
| Status language repeats | "Postponed" 22x, "Hold" 23x, plus "Priority", "next step", "Not-done", "open work menu" -- at least 7 subsections are all the same genre: what is not being done |
| One topic scattered | Groth16 is discussed substantively in **8 separate sections** (0.0, 0.1a, 0.2, 0.13, 0.15, 2, 6, 7) |
| Narrative and reference interleaved | 95 headings and 550 table rows in one file; a reader wanting the CPU numbers must pass the decision story, and vice versa |

The cause is accretion: each investigation appended a status subsection rather
than updating one. That is normal and the content is good -- the *shape* is
what has failed.

## Proposed structure

Split by **reader intent**, which is stable, rather than by investigation
order, which is not.

```
Perf.md                     narrative: what we learned and why it matters
  1  Findings              the durable results, one place per topic
  2  Method                how these were measured, reproduction
  3  Open decisions        things awaiting a person
  4  Not doing             set aside, with the reason

Measures.md                 (unchanged) every number, bound to an M-* id
BENCHMARKING.md             (new) how to run and read a measurement
PerfDoc.md                  (unchanged) ownership, discipline, build flags
STATUS.md                   (new) the volatile layer: what is in flight now
```

### Why a separate STATUS.md

The 7-ish status subsections churn on every session; the findings do not.
Mixing them forces a rewrite of a 1871-line document to record "G2 is next",
and makes the durable content look stale when it is not. STATUS.md would be
short, dated, and disposable.

### Section 1, Findings -- one section per topic, not per investigation

Merge the 8 Groth16 locations into one, likewise disk, Equihash, memory:

| Topic | Currently | Would become |
|-------|-----------|--------------|
| Groth16 cost and headroom | 0.0, 0.1a, 0.2, 0.13, 0.15, 2, 6, 7 | 1.1 Groth16 |
| Disk I/O | 3, parts of 0.13 | 1.2 Disk |
| Equihash / blake2b | 5, parts of 2 | 1.3 Equihash |
| Merkle latch | 4 | 1.4 Tree and anchor |
| Memory | 7, 8 | 1.5 Memory |
| Wallet / witness | 0.11, 0.12, 0.14 | 1.6 Wallet |

Each subsection: **what was measured, what it means, what follows**. Numbers
cited by `M-*` id, not restated -- Measures.md owns them.

### What to cut outright

- Duplicate restatements of the same figure in different sections. The 48-55%
  Groth16 number appears in at least four places with slightly different
  framing; one place, cited elsewhere.
- Sub-subsections that exist only to say something is postponed. One "Not
  doing" table with a reason column replaces them.
- The section index (0.7) -- a table of contents inside a document that has
  headings is maintenance debt.
- Lab-facts blocks that duplicate `PerfDoc.md` lab materials.

## Cost and risk

Roughly a day of careful editing. The risk is losing a hard-won caveat while
merging -- for example the note that jubjub `Point::add` appears in both tree
and proof paths, which is why bucket order matters. Mitigation: mechanical
diff of all `M-*` ids and all "do not" / "keep after" warnings before and after,
so nothing normative is dropped.

## Recommendation

Do the split when Groth16 A-vs-B is decided, not before. That decision will
rewrite 0.0/0.1a/0.6a anyway, and restructuring around a pending decision means
doing it twice.
