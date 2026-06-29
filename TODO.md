# TODO

Status and tracked work items for the Zero node.

---

## Active

- README rewrite: merge README0.md in
- Node setup and maintenance docs: validate all user-facing instructions
- Release signing: establish checksum and signing procedure.
- Chain bootstrap: document end-user import path (`-loadblock` / auto-import); linearize tool fixed in **`contrib/linearize/`** (commit **`f66b8b52b`**).
- macOS developer signing (codesign + notarization).
- Total supply discrepancy: review arithmetic vs project target of some 20M ZER.
- Consensus integer math: replace `double`/`COIN` mixes in subsidy and founders paths.
- zero_exclusive RPC param validation
- Zeronode/budget subcmd validation
- GTest fixes done 2026-06-09: **`CachedWitnesses*`** ported (harness merkle/commitment roots; Zero decrement semantics) except **`CleanIndex`** (needs coins-view harness); **`WriteCryptedSaplingZkey*`** / **`rpc_wallet_encrypted_wallet_sapzkeys`** encrypt-hang class fixed (wallet-DB re-entry deadlock in `AddCryptedSaplingSpendingKey`) -- back in default gate
- Equihash (192,7) test vectors
- Fuzz harness setup

## Pending

- Linux RC validation (lazu **`ZeroLinux`**): rebuild on **`zero-400names`**, run **`./contrib/run-tests.sh --strict`** (optional **`--suite`**). Blocked on disk headroom (~97% full, ~4 GB free).
- ~~**`blockchain.py` vs cache:**~~ done 2026-06-09: `gettxoutsetinfo` expectations now derived from actual tip via regtest subsidy schedule; passes at fresh (200) and warm (725) cache.
- P2P logging (postponed): remove misleading `Unknown command` log after zeronode extension dispatch (`src/main.cpp` ~7025-7033). Valid commands (`znp`, `znb`, `znget`, `dseg`, spork, etc.) are handled in `znodeman` / budget / payments subsystems but still log when `-debug=net`. See **`ZeroNodeDev.md`** section **9**; `notfound` already has a no-log exception.
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
- Legacy Proton build off by default (`NO_PROTON=1`); optional `src/amqp/` -- use ZMQ for pub/sub instead.
- Tag typos corrected (`v3.3.1`).
- `-port` help text: was Zcash defaults; fixed to 23801/23802.
- Stale code comments: `~/.zcash` -> `~/.zero`; collateral `1000` -> `10000`.
- Zeronode: `chainActive` negative height / reorg edge cases in SwiftTX and input-age cache.
- Decorative Unicode stripped from docs.

---

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidelines.
