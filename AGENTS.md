# Agent Instructions - Zero Node

**Start:** [README.md](README.md).

## Scope

Full node only. Zerowallet out of scope.

## Git

No `Co-authored-by:` or attribution trailers.

## Files

Do not remove, destructively overwrite, or add files without explicit user confirmation.

## Communication

Direct, concise, factual. Avoid hype and vague breadth ("comprehensive", "all platforms"). Restrained acknowledgment; technical detail is fine. Skip long generic apologies. Acknowledge errors briefly; focus on fixes.

## Lab / long runs

Do not start a batch of trials or tests where **each trial is expected to take more than 20 minutes**, unless each trial can be **restarted individually** (separate invocation, separate scratch/out dir, append-only ledger, no "all n trials or nothing" driver). Prefer one long trial per command, or a driver that resumes from the next unfinished trial index. Short campaigns under ~20 min/trial may still batch.
Make specific and actionable, include scope and bounds. No superlatives without evidence.

**Headings:** No parenthetical asides in `#`-`######` titles. Put the aside on the first line under the heading, or fold it into a short introductory paragraph. Bad: `### 0.8 Signals (updated)`. Good: `### 0.8 Signals` then a one-line status under it.

**History:** Do not accumulate dated incremental-fix narrative ("fixed X on DATE, then Y, then Z"). Prefer the settled current state. Keep path-dependent rationale only when the decision still depends on what was tried and rejected. Session changelogs and "reminders that we did the thing on DATE" belong in git history, not living docs. Campaign IDs and measure timestamps in **Measures.md** tables are fine; prose status sections are not a diary.

**Typography:** **No emojis or decorative Unicode** in any document except `README.md`. Use ASCII equivalents: `--` not em-dash, `->` not arrow, `"` not curly quotes, `...` not ellipsis.

**Estimates:** Do not invent or refine calendar time estimates (days/weeks) without measured evidence. Prefer qualitative effort bands (S/M/L) or named work packages.
