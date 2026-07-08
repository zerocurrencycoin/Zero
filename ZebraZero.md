# Zebra to Zero -- port suggestions

## 1. Purpose and role

**Purpose:** What Zero could adopt from **Zebra** (`zebrad`) and related stacks (YEC fork, CipherScan reference) -- sidecar validation, verifier lessons, post-Insight architecture study. **Not** a rewrite of zerod in Rust.

**Include:** Port strategies A-D; Orchard/NU6.2 lessons; Sprout CVE posture; YEC/`ycash-zebra` facts; CipherScan layer table for ZEC.

**Exclude:** zerod datadir and use-case flags (**`Runtime.md`**); ecosystem compare (**`ZKNodes.md`**); TNT/ZND zeronode ports (**`ZeroNodeDev.md`**).

Developer documents in **UpdateZero.md** section **1**, **Documentation map**.

Clone paths: `~/Work/ZK/ZKs/zebra`, `~/Work/ZK/ZKs/ycash-zebra`. Index: **`ZKRepos.md`**. CVE timeline: **`ZcashFixes.md`**.

---

## 2. What Zebra is

| Property | Zebra | Zero |
|----------|-------|------|
| Language | Rust (workspace crates) | C++14 |
| Wallet | None | Full wallet + zeronode |
| Consensus top | `zebra-consensus`, `zebra-chain` | `main.cpp`, `consensus/` |
| Proof verify | `librustzcash` + `halo2` in `zebra-consensus` | `libzcash`, `librustzcash_sprout_verify`, Sapling crates |
| Orchard | NU6.2 dual verifying keys | **Not implemented** |
| P2P | `zebra-network` | `net.cpp` (zcashd lineage) |

Zebra is an alternate **full-node validator**, not a drop-in replacement for `zerod` + wallet + zeronode RPC.

---

## 3. Realistic port strategies (ordered)

### A. Sidecar validator (lowest risk)

Run **zebrad** beside Zero for cross-checking on **Zcash** (not ZER chain):

- Compare tip hash / value pools after zcash security releases
- Zero keeps wallet/zeronode; Zebra validates ZEC only

**Effort:** ops + monitoring. **No Zero code merge.**

### B. Cherry-pick verification architecture (medium)

Zero already uses `ProofVerifier::Strict()` on connect. Adopt **Zebra-style explicit verifier routing** without Rust:

- Height -> Sprout/Sapling verify policy table (mirrors `verifier_for(network_upgrade)` in **`ZcashFixes.md`** Part 1.4)
- Pin Groth16 params hash in release notes
- Regression tests that fail if ConnectBlock skips JoinSplit verify

**Files:** `main.cpp`, `qa/rpc-tests/` sprout/turnstile tests.

### C. Rust FFI proof crate (high)

Extract `zebra-consensus` verify into a shared `.so` called from Zero. Defer unless Orchard is on the roadmap.

### D. Full node rewrite (not recommended)

Replacing `zerod` with Zebra loses wallet, zeronode, Insight hooks, and qa harness.

---

## 4. Orchard / NU6.2 lessons (if Zero ever adds Orchard)

Zebra 4.5.3 + 5.0.0 sequence:

1. Emergency disable Orchard actions at consensus height
2. NU hard fork with new **pinned verifying key**
3. **Dual keys** for historical sync (`VERIFYING_KEY_PRE_NU6_2` / `POST_NU6_2`)
4. Strict Orchard proof length rule

Zero has no NU5 in `consensus/upgrades.cpp`. Study on **Zcash** `zebrad` + **`ZcashFixes.md`**, not assetchain testnets.

---

## 5. Sprout CVE posture (Zero-specific win)

Zebra was never affected by Sprout `fChecked` (CVE-2026-35679). Zero is also unaffected. **Do not port `fChecked` from upstream zcashd.**

Process: subscribe to ZFND/ZODL releases; diff `ConnectBlock` on each zcashd security tag. Sprout sunset plan: **`ZcashFixes.md`** Part 3.

---

## 6. Network stack ideas

Features Zero lacks (study Bitcoin Core merges):

| Feature | In Zero? | Reference |
|---------|----------|-----------|
| BIP155 addrv2 | No | [BIP 155](https://github.com/bitcoin/bips/blob/master/bip-0155.mediawiki) |
| ASMap | No | Bitcoin Core `doc/asmap.md` |
| I2P SAM proxy | No | Bitcoin Core `-i2psam` |

---

## 7. Testing / CI patterns from Zebra

- Block replay tests after consensus changes
- Fuzz deserializers (no dedicated Zero fuzz targets in tree yet)
- Optional: regtest block from `zerod` vs pinned `zebrad` on Zcash testnet

---

## 8. Suggested execution order

1. Sidecar `zebrad` on **Zcash** mainnet (no Zero code change)
2. ConnectBlock JoinSplit verify regression test
3. Sprout sunset NU proposal (**`ZcashFixes.md`** Part 3)
4. Rust FFI only if Orchard approved

---

## 9. Ycash (YEC) and `ycash-zebra`

Ycash is the only zcash-lineage clone in this workspace that **ships a Zebra fork** for its own chain. Pirate, TENT, and Zero do **not** integrate Zebra code.

### 8.1 Clones

| Repo | Path | Upstream | Role |
|------|------|----------|------|
| Ycash Zebra | `~/Work/ZK/ZKs/ycash-zebra` | [ycashfoundation/zebra](https://github.com/ycashfoundation/zebra) | Rust full-node fork (tracks [ZcashFoundation/zebra](https://github.com/ZcashFoundation/zebra)) |
| Ycash zcashd | `~/Work/ZK/ZKs/ycash` | [ycashfoundation/ycash](https://github.com/ycashfoundation/ycash) | **Authoritative YEC consensus** until `ycash-zebra` params are verified |

```bash
cd ~/Work/ZK/ZKs
git clone --depth 1 https://github.com/ycashfoundation/zebra.git ycash-zebra
git clone --depth 1 https://github.com/ycashfoundation/ycash.git ycash
git -C ycash-zebra pull --ff-only
```

### 8.2 YEC chain facts (from `ycash` / foundation docs)

| Item | YEC | Zero (ZER) |
|------|-----|------------|
| Fork from Zcash | Block **570,000** (Jul 2019), `UPGRADE_YCASH` | Independent genesis Feb 2017 |
| Equihash | **192,7** (same N,K as Zero) | **192,7** |
| PoW personalization | `ZcashPoW` + little-endian 192,7 | Same family |
| Dev fund | **5%** perpetual -> Ycash Foundation | **7.5%** founders + zeronode 20--40% |
| Transparent HRP | `s1` (mainnet) | Zero t-address prefix |
| Sapling HRP | `ys` | Zero Sapling HRP |
| Sprout HRP | `yc` | Zero Sprout HRP |
| Replay protection | ZIP-200 style `UPGRADE_YCASH` branch ID | Own chain |
| Message start | Same bytes as Zcash pre-fork history (`0x24,0xe9,0x27,0x64` in `ycash/src/chainparams.cpp`) | Zero-specific |

Sources: [Ycash fork docs](https://www.ycash.xyz/docs/the_fork/), [mining pool notes](https://www.ycash.xyz/docs/mining_pool_setup/), `ycash/src/chainparams.cpp`, `ycash/src/consensus/upgrades.cpp`.

### 8.3 Ycash Rust stack (not in Zero tree)

Ycash moved explorer/wallet off Insight to:

| Component | Repo |
|-----------|------|
| Full node (Rust) | [ycashfoundation/zebra](https://github.com/ycashfoundation/zebra) |
| Light client gRPC | [ycashfoundation/lightwalletd](https://github.com/ycashfoundation/lightwalletd) |
| Rosetta API | [ycashfoundation/rosetta-bitcoin](https://github.com/ycashfoundation/rosetta-bitcoin) |
| Sapling crypto | `sapling-crypto-ycash`, `librustzcash` forks |
| Wallet / sync | `WebZjs`, `zwallet`, `zcash-sync` |

No shared C++ with Zero. Useful as a **reference architecture** for leaving zcashd + Insight, not as a code port source.

### 8.4 `ycash-zebra` vs ZFND `zebra`

Shallow clone (Jun 2026): `ycash-zebra` tip tracks upstream Zebra workspace layout (`zebrad`, `zebra-chain`, `zebra-consensus`, ...). Parameter files under `zebra-chain/src/parameters/` still read as **Zcash network** constants in the checked tree; YEC-specific activation and address prefixes live in **`ycash`** (`ycashd`) today.

**Before treating `ycash-zebra` as a YEC mainnet node:** diff `ycash-zebra/zebra-chain/src/parameters/` against `ycash/src/chainparams.cpp` and `consensus/upgrades.cpp` (570k fork, 192,7, HRPs, subsidy). Until that diff is clean, use **`ycashd`** as the live YEC node reference and **`ycash-zebra`** as an upstream-tracking fork to watch.

### 8.5 Relevance to Zero

| Topic | Lesson |
|-------|--------|
| Equihash 192,7 | YEC and Zero share PoW shape; Ycash did not adopt Pirate's Zawy RT_CST_RST |
| Node strategy | Ycash bet on **zebrad + lightwalletd**; Zero stays on **zerod + zeronode + Insight** |
| Sprout audit | Ycash preserved Sprout; high priority for zcashd security backports (see **`ZcashFixes.md`** Appendix) |
| Orchard | YEC zcashd path stops at Sapling-era upgrades in tree sampled; no Zero Orchard either |

Zero cannot run `ycash-zebra` against ZER chain without a full parameter port. Sidecar **`zebrad`** remains **Zcash-only** for security monitoring.

---

## 10. CipherScan (ZEC reference indexer)

[CipherScan](https://cipherscan.app) is a **Zcash mainnet** explorer and API stack, not a zerod module. Useful as a reference for post-Insight architecture on **ZEC**.

| Layer | Technology |
|-------|------------|
| Validator | **zebrad** (not zcashd) |
| Index | PostgreSQL (blocks, txs, transparent rich list, pool stats) |
| API | Express REST + WebSocket -- `https://api.mainnet.cipherscan.app/api/*` (public, no auth) |
| Light clients | Hosted **lightwalletd** gRPC (mainnet and testnet) |
| Frontend | Next.js; optional client-side WASM memo decrypt |

Open source: [Kenbak/cipherscan](https://github.com/Kenbak/cipherscan). Notable endpoints: `/api/rich-list` (transparent addresses only), `/api/privacy-stats`, `/api/tx/broadcast`.

### Relevance to Zero

| Topic | CipherScan | Zero |
|-------|------------|------|
| Chain | ZEC mainnet | ZER independent genesis |
| Node | zebrad required | zerod + optional `-insightexplorer` |
| Shielded search | Pool aggregates; no z-addr chain search | Same privacy limits on insight (t-addr only) |
| Rich list | PostgreSQL indexer | No in-tree PostgreSQL stack; optional `-insightexplorer` on zerod for t-addr APIs only |

Zero does **not** gain CipherScan by enabling flags. CipherScan is bound to **zebrad** on ZEC. Zero stays on **zerod** (wallet, zeronode, existing qa harness).

---

## References

| Resource | URL |
|----------|-----|
| Zebra book | https://zebra.zfnd.org/ |
| Zebra halo2 module | https://zebra.zfnd.org/internal/zebra_consensus/halo2/index.html |
| Zebra 4.5.3 / 5.0.0 | https://zfnd.org/zebra-4-5-3-and-5-0-0-emergency-soft-fork-and-nu6-2-activation/ |
| Ycash foundation | https://github.com/ycashfoundation |
| Ycash releases | https://github.com/ycashfoundation/ycash/releases |
| Zero upgrades (no Orchard) | `src/consensus/upgrades.cpp` |
