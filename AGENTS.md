# Agent Instructions - Zero Node

## General

- **Git:** No `Co-authored-by:` or attribution trailers.
- **Files:** No removal, destructive overwrite, or new file without explicit user confirmation.
- **Shell:** Run commands and scripts with bash (`bash -c`, `bash -s <<'EOF'`, `#!/usr/bin/env bash`); zsh does not split an unquoted variable into words. Redirect `zerod -daemon` output to a file; a pipe or captured output blocks until the node stops.
- **Comments:** State current behavior and why: tricky implementation details and special considerations. No tracking IDs (including upstream PR and issue numbers), status notes, change history, or references to documents in code, tests, scripts, or help text; a fix's history belongs in the commit message and release notes. Code imported from another project keeps its text.
- **Documents:** One home per fact: merge into the existing section, delete copies, and remove moved content from its source. Every sentence states a fact, a decision, or an action. Decisions and their status live in the project's documents. No parentheticals in headings. Cite code by file, function, and search token, never by line number.

## Zero node

- **Start:** README.md. Full node only; Zerowallet is a separate repository.
- **Vendored subtrees:** `src/leveldb`, `src/secp256k1`, `src/univalue` stay identical to upstream except changes required to build or run; no comments there; record each change in CONTRIBUTING "Vendored subtrees".
- **Test ports:** A mainnet `zerod` may run on the host on P2P 23801 and RPC 23811; test configurations use other ports.
- **Documents:** ASCII outside README.md (`--`, `->`, `"`, `...`). Document lists and links only in the README documentation map. A cross-document reference names a subsection needed to follow or implement, never a whole document. Group by subject and order sections so reading in sequence needs no back-reference. Classify a document (reference record, plan, operator guide) before restructuring it.
