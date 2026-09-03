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

## Tools and verification

Read and edit files with the harness file tools: they fail loudly on a stale or
non-unique match, where an in-place `sed` silently edits the wrong line or
nothing at all. For structured extraction, a short Python block reviews better
than a chain of `sed` and `awk`.

Verify by running, and check the artifact the run produced -- not the exit code
of whatever wrapped it. A wrapper that declines to act, or a waiter that is
killed, exits 0 with no work done.

Shell work under `contrib/perf/` additionally follows `contrib/perf/docs/POLICY.md` S4.

## Documentation

Make specific and actionable, include scope and bounds. No superlatives without evidence. No parenthetical asides in `#`-`######` headings; move them to the first line under the heading or integrate into a short introductory paragraph. **No emojis or decorative Unicode** in any document except `README.md`. Use ASCII equivalents: `--` not em-dash, `->` not arrow, `"` not curly quotes, `...` not ellipsis.
