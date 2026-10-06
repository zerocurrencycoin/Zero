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

## Documentation

Make specific and actionable, include scope and bounds. No superlatives without evidence. No parenthetical asides in `#`-`######` headings; move them to the first line under the heading or integrate into a short introductory paragraph. **No emojis or decorative Unicode** in any document except `README.md`. Use ASCII equivalents: `--` not em-dash, `->` not arrow, `"` not curly quotes, `...` not ellipsis.

**No filler.** Every sentence states a fact, a decision, or an action. Cut generic, non-committal, conversational text that a reader cannot act on: vague hedges ("may need attention", "should be fine", "if needed"), feel-good assessment ("works well", "robust", "recorded here in full"), and fill-in placeholders ("at freeze: add items"). Status on a tracking item (postponed, not scheduled, does not gate a release, decide after X) is a fact and stays.

**Partitioning.** One home per fact. Group content by subject and module; combine overlapping sections; split sections that mix topics; delete redundant copies instead of cross-referencing them; when content moves, remove it from the source. Order sections so that reading in sequence needs no back-references. Classify a document (reference record, plan, operator guide) before restructuring it.

**References.** Document lists and link collections appear only in the documentation maps: README for public documents, UpdateZero section 1 for internal ones. Inside a document, section order and, when needed, a table of contents replace pointers. A cross-document reference is allowed only to a specific subsection whose content is needed to follow the discussion or to implement; never to a whole document, and not next to a tracking ID, which identifies itself. Cite code by file, function, and a search token, never by line number.
