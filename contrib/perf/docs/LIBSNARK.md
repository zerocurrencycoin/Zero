# libsnark in Zero: provenance, history, and current status

Established 2026-09-15 from the tree and from `ZKs/{zcash,zebra,pirate,hush3,zclassic,firo}`.

## Finding: it is dead code

**`src/snark/` is not built, not linked, and not included by anything.**

| Check | Result |
|-------|--------|
| Referenced in `src/Makefile.am` | **no** -- `codequery raw -n 'snark' src/Makefile.am configure.ac` returns no match |
| Object files produced | **0** -- `find src/snark -name '*.o'` is empty after a full build |
| `#include` from outside `src/snark/` | **none** |
| `namespace libsnark` used outside the tree | **none** |

It occupies **284 KB across 30 source files**, and it is a **stripped subset**:
only `algebra/`, `common/`, `gadgetlib1/`, `zk_proof_systems/` of the upstream
library.

## Provenance

- **Upstream:** libsnark by **SCIPR Lab and contributors**, MIT license
  (per the file headers, e.g. `common/utils.hpp`).
- **Entered Zero** as a git subtree: `f4d8cd127` (2017-08-02),
  *"Merge commit '51e448641d6cbcd582afa22cd8475f8c3086dad7' as 'src/snark'"*.
- **Last touched** 2017-10-11 (`78934c5e8` "Update libsnark LDLIBS",
  `f53394eb8`, `948f756e1`, `a18851f0d` "Migrate libsnark test code to Google
  Test"). **Nine years untouched.**

## What it was for, and what replaced it

libsnark implemented the **Sprout** zk-SNARK proving system (BCTV14 /
PGHR13 over alt_bn128). Sprout proofs were the original Zcash shielded
protocol.

**Sapling replaced it with Groth16 over BLS12-381, implemented in Rust
(`bellman`).** Once Sapling activated, the C++ proving system was no longer on
any live path -- Sprout proof *verification* moved to the Rust side as well,
which is why Zero's JoinSplit verification goes through
`joinsplit.Verify(*pzcashParams, ...)` into librustzcash rather than into
`src/snark/`.

## Ecosystem status

| Project | libsnark | Proof stack today |
|---------|----------|-------------------|
| **Zcash** | **removed** in `9ce0caf20` (2019-06-25, Jack Grigg), released **v2.1.0** | Rust: `bellman` / librustzcash, in-tree at `src/rust/` |
| **Zebra** | never had it | Rust: `bellman`, with a dedicated `groth16` component (`zebra-consensus/Cargo.toml`) |
| **Pirate** | removed | Rust, `src/rust/` |
| **Hush3** | removed | Rust |
| **Firo** | removed | own stack |
| **Zclassic** | **still present** | unmaintained |
| **Zero** | **still present, unbuilt** | librustzcash `06da3b9a` |

**Zero and Zclassic are the only two still carrying it**, and Zero does not
even compile it.

## Relevance to the concurrency work

The 2016 Zcash commit that disabled multi-worker async RPC (`008fccfa4`) gave
two reasons: *"until we can lock notes and also tune performance of libsnark
which by default uses multiple threads"*.

**The libsnark half of that rationale is void for Zero.** The library is not
built, so it cannot spawn threads. Whether the *Rust* proof path
(librustzcash / bellman) spawns threads is a **separate and still-open
question** (`THREADS.md` S4) -- and it is the one that actually matters, since
that is the code Zero runs.

This narrows the 2016 justification: of its two blockers, only **note locking**
(P9) still applies to Zero.

## Recommendation

**Delete `src/snark/`.** It is 284 KB of unbuilt, nine-year-stale, stripped
vendored code that upstream and three of four sibling forks have removed. It
is not a dependency, not a build input, and not referenced.

*Justification:* dead code carries review cost and implies a capability the
node does not have -- as it did here, where a 2016 commit message about
libsnark threading was taken at face value for a library that is not compiled.

**Counter-argument, stated fairly:** deleting vendored code is irreversible in
a way that keeping it is not, and `git log` already records it. If the concern
is provenance, a `src/snark/README.md` noting "unbuilt, retained for
historical reference, see Zcash `9ce0caf20`" costs nothing. **Either is
defensible; leaving it silent is not.**

**Owner: Zero400.** Tracked as **P19**.
