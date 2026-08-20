# contrib/perf/docs

The perf documentation set. **One subject per document**, plus a front door.
If something does not fit one of them, it does not get a new file -- it gets a
section.

## The set

| # | Document | Answers | Read when |
|---|----------|---------|-----------|
| 0 | [OVERVIEW.md](OVERVIEW.md) | What is this effort, and where do I go? | **Start here** |
| 1 | [HOWTO.md](HOWTO.md) | How do I take a measurement and read it? | Running anything |
| 2 | [FINDINGS.md](FINDINGS.md) | What do we know, and how confident are we? | Deciding what to work on |
| 3 | [SCHEMA.md](SCHEMA.md) | How is a result recorded so it aggregates? | Writing or reading a ledger |
| 4 | [TASKS.md](TASKS.md) | What is open, in what order? | Picking up work |
| 5 | [POLICY.md](POLICY.md) | What are the rules, and what enforces them? | Editing docs or lab runs |
| 6 | [NOTES.md](NOTES.md) | What did we evaluate once, at a point in time? | Wondering why a frozen note exists |

`OVERVIEW.md` is the front door and is linkable from the repo root: it states
the problem, the goals and the routing, and does not churn as findings change.

## Status

**Complete.** All eight documents are written. This set replaces the accumulated documents in
`contrib/perf/`, which grew past the point where the set could be reviewed as a
whole.

Scope, source disposition and progress: **[MIGRATION.md](MIGRATION.md)**. Until
a topic is marked pulled in, the old file remains authoritative. Nothing is
deleted until its content has a home here and the move is confirmed.

## Rules for this directory

1. **Seven files** (six subjects plus the overview front door). An eighth
   needs a stated reason and confirmation.
2. **One subject per file**, named by the reader's question, not by
   investigation order.
3. **Numbers live in one place.** A figure appears in `SCHEMA.md`-governed
   ledgers and is cited by id elsewhere -- never restated.
4. **Point-in-time notes go to `NOTES.md`**, dated and version-stamped, and
   are not updated by default. Volatile status is **not** filed there -- it
   belongs in `TASKS.md` (what is open) or `FINDINGS.md` S1 (what the latest
   work established).
5. **ASCII only** (`POLICY.md`), enforced by `lint-perf.sh`.
