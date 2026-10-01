# Satellite repositories into `zerocurrencycoin`

Proposal for the owner. Nothing executed; a repository transfer is
outward-facing and is run by the owner.

## Repositories

| Repo | Remote | Relation to Zero | Proposal |
|------|--------|------------------|----------|
| `uniblake` | `wkarshat/uniblake` | Linked into `zerod`; the Equihash blake2b path | Move first: a build dependency on a personal account |
| `uniblake-rs` | `wkarshat/uniblake-rs` | Rust sibling, not linked | Move with `uniblake` |
| `insight` | `tearodactyl/insight` | Zero block explorer | Move |
| `Requihash` | `tearodactyl/requihash` | Research fork cited by `equ/` | Move or archive; do not delete |
| `Zebro` | `tearodactyl/zebro` | Zebra-lineage exploration, no build path | Move or archive |
| `linearize` | none; not a git repository | Also vendored at `contrib/linearize/` | Keep vendored; do not create a repository |

`tearodactyl` is a user account, not an organisation, so the move is a
transfer from that user to the `zerocurrencycoin` organisation. The local
`gh` token lacks `admin:org` and cannot read organisation membership.

## Blocking: cited files that are not committed

`uniblake/docs/NEON.md` and `uniblake/docs/PATTERNS.md` are untracked in the
uniblake working tree, and `equ/VENDORED.md` cites `NEON.md` as the owner of
the vector-kernel figures. Commit them, and uniblake's other uncommitted
changes, before any transfer. This is worth doing even if no transfer
happens.

## Sequence

1. Commit what is cited (owner, in uniblake).
2. Decide the destination: transfer to the organisation (recommended:
   ownership then survives any one account).
3. `gh auth refresh -h github.com -s admin:org`; confirm membership.
4. Transfer `uniblake` with GitHub's transfer, which keeps redirects. Clean
   build of `zerod` and `contrib/perf/validate.sh` before and after; one
   Equihash KAT must produce identical hashes.
5. Transfer the rest: `uniblake-rs`, `insight`, `Requihash`, `Zebro`.

Never: force-push, history rewrite, or delete-and-recreate. Snapshots,
archives and `bootstrap.dat` copies are not repository material; they go to
release assets or an object store.
