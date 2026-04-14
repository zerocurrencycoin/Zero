# TODO

Status and tracked work items for the Zero node.

---

## Active

- README rewrite: merge README0.md in
- Node setup and maintenance docs: validate all user-facing instructions
- Release signing: establish checksum and signing procedure.
- Chain bootstrap: document snapshot sourcing and verification.
- macOS developer signing (codesign + notarization).
- Total supply discrepancy: review arithmetic vs project target of some 20M ZER.
- Consensus integer math: replace `double`/`COIN` mixes in subsidy and founders paths.
- zero_exclusive RPC param validation
- Zeronode/budget subcmd validation
- GTest fixes: CachedWitnesses, CDB::Rewrite
- Equihash (192,7) test vectors
- Fuzz harness setup

## Pending

- Params archival: audit `fetch-params.sh` file names and URLs.
- Build validation: Windows hardening flag gap identified
- Branch id posture: CI guard for duplicate `nBranchId` (Sapling/Cosmos share `0x7361707a`).
- getrawtransaction size/fees
- Partition and wallet tests
- OpenSSL: remain on 1.1.1w until audited 3.x or removal.
- SwiftTX removal: strip unused instant-confirmation code and hidden options.
- Release branch cleanup: fifteen branches redundant with tags.
- Debian packaging: confirm `build-debian-package.sh` superseded by `release-linux.sh`.
- GitHub org cleanup: archive ~37 obsolete repos; retire wiki Node Setup page.

## Completed

- ZERO_COIN.md: chain economics consolidated.
- `rescan_import.py` executable bit.
- `run-tests.sh` background jobs: child exit codes corrected.
- `getchaintips` RPC test: split topology, CHAIN_BOOTSTRAP.
- Zeronode null guard: `CheckInputsAndAdd`.
- Iterator bug: `zeronodeman.cpp` erase order.
- `throw new std::runtime_error` removed from 5 sites.
- chainActive[] null deref: all sites guarded.
- zcrawreceive: legacy Sprout, no action needed.
- Rust: system default on all platforms; 1.32.0 legacy/CI only.
- librustzcash: pinned, consensus-linked, no upgrade without new NU.
- Proton/AMQP: disabled, duplicates ZMQ, not productized.
- Tag typos corrected (`v3.3.1`).
- `-port` help text: was Zcash defaults; fixed to 23801/23802.
- Stale code comments: `~/.zcash` -> `~/.zero`; collateral `1000` -> `10000`.
- Zeronode: `chainActive` negative height / reorg edge cases in SwiftTX and input-age cache.
- Decorative Unicode stripped from docs.

---

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidelines.
