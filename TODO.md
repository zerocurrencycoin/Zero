# TODO

Status and tracked work items for the Zero node.

---

## Active

- README rewrite: merge README.md and README0.md into one front page.
- Total supply discrepancy: review arithmetic vs project target of some 20M ZER.
- Consensus integer math: replace `double`/`COIN` mixes in subsidy and founders paths.
- Release signing: establish checksum and signing procedure.
- zero_exclusive RPC param validation (TST-01, contributor-ready).
- Zeronode/budget subcmd validation (TST-03).
- GTest fixes: CachedWitnesses, CDB::Rewrite (TST-04).
- Equihash (192,7) test vectors (TST-05, contributor-ready).
- Fuzz harness setup (TST-06, contributor-ready).
- Node setup and maintenance docs: validate all user-facing instructions (DOC-02).

## Pending

- macOS developer signing (codesign + notarization).
- Params archival: audit `fetch-params.sh` file names and URLs.
- Chain bootstrap: document snapshot sourcing and verification.
- Debian packaging: confirm `build-debian-package.sh` superseded by `release-linux.sh`.
- Release branch cleanup: fifteen branches redundant with tags.
- Build validation: Windows hardening flag gap identified; see UpdateZero REL-07.
- Branch id posture: CI guard for duplicate `nBranchId` (Sapling/Cosmos share `0x7361707a`).
- Partition and wallet tests (TST-07).
- GitHub org cleanup: archive ~37 obsolete repos; retire wiki Node Setup page.
- getrawtransaction size/fees (issue #70, contributor-ready).
- SwiftTX removal: strip unused instant-confirmation code and hidden options.
- OpenSSL: remain on 1.1.1w until audited 3.x or removal.

## Completed

- ZERO_COIN.md: chain economics consolidated.
- UpdateBuild / UpdateTests consolidated.
- `run-tests.sh` background jobs: child exit codes corrected.
- `getchaintips` RPC test: split topology, CHAIN_BOOTSTRAP.
- `rescan_import.py` executable bit.
- macOS system Rust: `RUST_USE_SYSTEM` in `rust.mk`.
- Zeronode null guard: `CheckInputsAndAdd`.
- Iterator bug: `zeronodeman.cpp` erase order.
- `throw new std::runtime_error` removed from 5 sites.
- Decorative Unicode stripped from docs.
- Tag typos corrected (`v3.3.1`).
- chainActive[] null deref: all sites guarded.
- Rust: system default on all platforms; 1.32.0 legacy/CI only.
- zcrawreceive: legacy Sprout, no action needed.
- librustzcash: pinned, consensus-linked, no upgrade without new NU.
- Proton/AMQP: disabled, duplicates ZMQ, not productized.
- `-port` help text: was Zcash defaults; fixed to 23801/23802.
- Stale code comments: `~/.zcash` -> `~/.zero`; collateral `1000` -> `10000`.

---

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidelines.
