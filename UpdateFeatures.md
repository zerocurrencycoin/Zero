# UpdateFeatures

In-repo **design choices** that diverge from upstream Zcash or affect behavior. Dependency versions: **UpdateBuild.md §1**. Tests and harness limits: **UpdateTests.md**.

---

## 1. Shielded witness path

**Upstream (Zcash and several forks):** Per-block **`IncrementNoteWitnesses`** from **`ChainTip`**—takes Merkle frontiers from the caller, no **`ReadBlockFromDisk`** / **`pcoinsTip`** inside the wallet.

**Zero:** **`VerifyAndSetInitialWitness`** validates or rebuilds a note’s witness from disk; **`BuildWitnessCache`** walks the chain forward with optional **`pblockIn`** to avoid disk read when the caller already has the block. Goals: recovery from arbitrary heights and IBD-heavy wallets; cost is coupling to **`pcoinsTip`**, **`ReadBlockFromDisk`**, and chain views.

**Production fixes applied:** Null checks for **`pprev`** / **`pcoinsTip`**, optional **`pblockIn`**, nullifier guards, **`nWitnessCacheSize`** reset in **`ClearNoteWitnessCache`**. Implementation: **`src/wallet/wallet.cpp`**, **`wallet.h`**.

**Tradeoff:** Stronger runtime coupling and harder unit testing than the incremental API. **UpdateTests.md** documents GTest exclusions and harness gaps for witness-heavy cases.

---

## 2. Equihash hash state API

Zcash v6+ moved **`eh_HashState`** to a Rust/CXX bridge. Zero keeps the **libsodium C** **`crypto_generichash_blake2b_state`** API used across other Equihash forks. Adopting the Rust wrapper would require the matching **`rustcxx`** stack and **`librustzcash`** alignment—out of scope unless the whole PoW stack is ported.

---

## 3. Branding strings

User-visible strings should read **ZERO** where the product is shown (RPC errors, logs, deprecation text). Residual **Zcash** / **Bitcoin** names in tests or build metadata are cleaned when those files are touched; not a consensus issue.
