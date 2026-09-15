# Bringing the satellite repos into zerocurrencycoin

**Proposal, 2026-09-09. Nothing executed.** Every step below is reversible and
none runs without instruction.

## 1. What was found, with credentials

Checked with the local `gh` login (account `wkarshat`, keyring):

| Repo | Current remote | Owner today |
|------|----------------|-------------|
| `uniblake` | `github.com/wkarshat/uniblake` | personal |
| `uniblake-rs` | `github.com/wkarshat/uniblake-rs` | personal |
| `Zebro` | `github.com/tearodactyl/zebro` | tearodactyl |
| `Requihash` | `github.com/tearodactyl/requihash` | tearodactyl |
| `insight` | `github.com/tearodactyl/insight` | tearodactyl |
| `linearize` | none -- **not a git repo** | local only |

**Two facts that shape the plan:**

1. **`tearodactyl` is a User account, not an organisation** (`gh api
   users/tearodactyl` returns `"type": "User"`). So "into zerocurrencycoin as
   tearodactyl" cannot mean an org-to-org move. It means either transferring
   repos from the `tearodactyl` user to the `zerocurrencycoin` org, or adding
   `tearodactyl` to that org and moving the repos under it.
2. **The local token cannot read org membership.** `gh api
   orgs/zerocurrencycoin/memberships/wkarshat` returns 404 and the
   `members_can_create_repositories` query needs the `admin:org` scope, which
   the token lacks. `zerocurrencycoin` itself is readable, so the account has
   repo access without visible org membership.

**Consequence: the migration cannot be assessed further, let alone executed,
from this machine's current credentials.** Anything below that touches
GitHub needs either a token refresh (`gh auth refresh -h github.com -s
admin:org`) or an org owner acting directly.

## 2. What each repo is, and whether it should move

| Repo | Relationship to Zero | Recommendation |
|------|---------------------|----------------|
| `uniblake` | **Load-bearing.** Linked into `zerod`; supplies the Equihash blake2b path (2.03x, `c9bbe6ad9`). A Zero build depends on it | **Move first.** A consensus-adjacent dependency on a personal account is the single largest supply-chain exposure in the set |
| `uniblake-rs` | Rust sibling; not currently linked into the node | Move with `uniblake`, same reasoning, lower urgency |
| `Requihash` | Research fork behind two Equihash findings that did **not** transfer | Move or archive. It is cited in `equ/FINDINGS.md`, so it should not simply vanish |
| `Zebro` | Zebra-lineage exploration | Move or archive; not on any build path |
| `insight` | Block explorer; Zero-specific | Move -- it is a user-facing Zero service |
| `linearize` | **Not a git repo.** Also vendored at `contrib/linearize/` | Do **not** create a repo. Either keep it vendored or initialise it, not both |

## 2a. State of each working tree, 2026-09-09

| Repo | Branch | Commits | Uncommitted | Last commit |
|------|--------|--------:|------------:|-------------|
| `uniblake` | main | 43 | **6** | 2026-09-03 |
| `uniblake-rs` | main | 4 | 0 | 2026-09-01 |
| `Requihash` | main | 30 | **7** | 2026-09-01 |
| `Zebro` | main | 16 | 3 | 2026-07-15 |
| `insight` | main | 25 | 1 | 2026-07-23 |

**Blocking finding: ZeroPerf cites two files that are not committed anywhere.**

`uniblake/docs/NEON.md` and `uniblake/docs/PATTERNS.md` are **untracked** in
the uniblake working tree, and three tracked ZeroPerf documents cite them as
the owning source:

| Citing document | Cites |
|---|---|
| `Perf.md:1056` | `uniblake/docs/PATTERNS.md` -- the pattern taxonomy behind the 2.03x result |
| `equ/VENDORED.md:467` | `uniblake/docs/NEON.md` -- the vector-kernel figures |
| `docs/TASKS.md:977` | `uniblake/docs/NEON.md` -- named as subject owner for kernel results |

So a citation that `POLICY.md` treats as authoritative resolves to a file that
exists on one machine and in no repository. `uniblake/measurements.tsv` --
the provenance-carrying ledger those figures come from -- is also modified and
uncommitted.

**This must be fixed before any transfer**, and it is worth fixing even if the
transfer never happens: committing costs nothing and the citations are already
load-bearing. **Recommend: commit uniblake's docs and `measurements.tsv`
first, as its own step, independent of Phase 0.**

## 3. Recommended sequence

**Phase -1 -- commit what is cited.** `uniblake` `docs/NEON.md`,
`docs/PATTERNS.md`, `measurements.tsv`. Blocks nothing else, fixes a live
provenance break, and is the owner's to run. Do this first regardless of every
decision below.

**Phase 0 -- decide the destination shape.** Owner's call, blocks everything:
transfer to the `zerocurrencycoin` org directly, or bring `tearodactyl` into
the org and keep repos under it. Recommend **transfer to the org**: it makes
ownership survive any individual account, which is the point of the exercise.

**Phase 1 -- credentials.** `gh auth refresh -h github.com -s admin:org`, then
re-check membership and `members_can_create_repositories`. Without this, Phase
2 cannot be verified even if it succeeds.

**Phase 2 -- `uniblake` first, as the template.**
1. Confirm the current remote is authoritative and nothing local is unpushed.
2. Transfer via GitHub (`Settings -> Transfer ownership`), which **preserves
   issues, stars and redirects** -- a delete-and-recreate does not.
3. Update the sibling-resolution in Zero's build. `uniblake` resolves "to the
   checkout beside this tree with no configuration" (`TASKS.md` B2a-b), so a
   move must not break local builds -- verify with a clean build before and
   after.
4. Re-run `contrib/perf/validate.sh` and one Equihash KAT to confirm the
   linked library still produces identical hashes.

**Phase 3 -- the rest**, in order `uniblake-rs`, `insight`, `Requihash`,
`Zebro`. None is on a build path, so each is a transfer plus a remote update.

**Phase 4 -- backups and intermediates.** Snapshots, `test-logs/archives/`,
packed chain snaps and `bootstrap.dat` copies are **not** repo material: they
are large, regenerable or chain-derived. Recommend a release-asset or object
store, not a git repo. `POLICY.md` S6.4 already marks `archives/` as never
reclaimed, so the retention rule exists; only the location would change.

## 4. What must not happen

- **No force-push, no history rewrite, no delete-and-recreate.** Transfer
  preserves redirects; recreation breaks every existing clone and any
  `depends/` pin that resolves by URL.
- **No move of a build-path dependency without a build check either side.**
  `uniblake` is linked into `zerod`.
- **No secrets or host paths carried across.** `POLICY.md` S7.2 and S7.3 apply
  to the new location unchanged.
- **Nothing executed on the owner's behalf.** Repo transfer is irreversible
  from this side and outward-facing; it needs the owner to run it or to say
  explicitly to proceed.

## 5. Status

**Blocked on Phase 0 (a decision) and Phase 1 (a token scope).** No GitHub
state has been modified.
