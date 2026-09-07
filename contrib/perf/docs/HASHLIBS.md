# Which library does what: uniblake and libsodium in Zero

Zero links both. They are not alternatives competing for the same job -- each
owns a distinct set of functions, and one call path moved from the second to
the first. This document states the division, the measured difference where
they overlap, and why the overlap is narrower than it looks.

Numbers measured 2026-09-05 on Apple M4 Pro, macOS 26.3, arm64, against
**libsodium 1.0.22** built `-O3` static; harness compiled `-O2`, matching
Zero's own build (`depends/hosts/darwin.mk:11`).

## 1. The division of labour

### uniblake owns: Equihash hashing

| Site | File |
|---|---|
| Prefix-state wrapper | `crypto/eh_hashstate.h` |
| `InitialiseState`, `GenerateHash` | `crypto/equihash.cpp` |
| Solver hashing | `pow/tromp/equi.h`, `pow/tromp/equi_miner.h` |
| Block validation | `pow.cpp` (`CheckEquihashSolution`) |
| Mining | `miner.cpp`, `rpc/mining.cpp` |
| Benchmarks and tests | `zcbenchmarks.cpp`, `gtest/test_equihash.cpp`, `test/equihash_tests.cpp`, `test/miner_tests.cpp` |

**Twelve files.** The functions are `ub_init_personal`, `ub_update`,
`ub_hash_tail`, `ub_copy`, `ub_state_size`/`ub_state_align`.

### libsodium owns: everything else

| Function | Sites | Purpose |
|---|---|---|
| `crypto_sign_detached` / `_verify_detached` / `_keypair` | `crypto/common.h`, `main.cpp`, `gtest/test_checktransaction.cpp`, `test/sighash_tests.cpp` | **Ed25519** -- JoinSplit signatures. Consensus-critical |
| `randombytes_buf` | `random.cpp`, `test/equihash_tests.cpp` | Entropy |
| `sodium_init` | `crypto/common.h` | Library init |
| `crypto_generichash_blake2b_*` | 7 files, below | **blake2b that has NOT moved** |

### blake2b still on libsodium

| File | Uses | What it hashes |
|---|--:|---|
| `zcash/prf.cpp` | 9 | PRF outputs (Sprout) |
| `zcash/address/zip32.cpp` | 6 | Key derivation |
| `zcash/NoteEncryption.cpp` | 6 | Note encryption KDF |
| `zcash/JoinSplit.cpp` | 2 | JoinSplit hashing |
| `zcash/address/sapling.cpp` | 1 | Address derivation |
| `hash.h` | 4 | **`CBLAKE2bWriter`** -- sighash and tx hashing |
| `script/interpreter.cpp` | -- | ZIP-143 personalization constants |

**`CBLAKE2bWriter` is the significant one:** it runs on every transaction in
every block, so it is the largest remaining blake2b consumer by call volume.

**Both libraries therefore compute blake2b, on different data.** Equihash
headers go through uniblake; transaction and note hashing goes through
libsodium. They are not redundant, and neither is a drop-in for the other's
remaining scope without a migration.

## 2. Where they overlap, the difference depends on the access pattern

Both implement BLAKE2b. Their measured difference is **not** a constant factor
-- it is a function of how the digests are requested.

| Pattern | libsodium | uniblake | ratio |
|---|--:|--:|--:|
| Short digest over a shared 140B prefix (streaming) | 168.1 ns | 83.0 ns | **2.03x** |
| Shared prefix, run of counters (`ub_hash_n`) | 168.1 ns | 86.1 ns | 1.95x |
| Shared prefix, single tail (`ub_hash_n`, n=1) | 168.1 ns | 92.3 ns | 1.82x |
| Leaf, 2 threads | 169.0 ns | 41.6 ns | 4.06x |
| Bulk, 1 KiB | 1625 MB/s | 1656 MB/s | 1.02x |
| Bulk, 16 KiB | 1662 MB/s | 1675 MB/s | 1.01x |
| Bulk, 1 MiB | 1670 MB/s | 1685 MB/s | 1.01x |
| Bulk, 16 MiB | 1659 MB/s | 1683 MB/s | 1.01x |

**Read the two ends together.** On bulk data the two are within 1-2% -- the
compression function itself is not meaningfully faster. On short digests over
a repeated prefix, uniblake is 2x. The entire advantage is in **not re-absorbing
the prefix**: `ub_hash_tail` keeps the prefix state and appends only the
trailing bytes, where libsodium's streaming API re-initialises and re-absorbs
the 140-byte prefix on every call.

That is why the win is architectural, not arithmetic, and why it appears in
Equihash specifically: `GenerateHash` is called `2^K = 128` times per block
header, each time over the *same* prefix with a different 4-byte index.

**The 2x comes from the prefix state, not from vectorisation.** Disassembling
`_ub_compress` in the built `zerod` shows general-purpose registers only
(`x8`, `x9`, `x20`) -- a scalar compression function, the same class of code
libsodium runs here. The two libraries compress at the same speed (the 1.01x
bulk row proves it); what differs is how many times each compresses the
prefix.

## 2.1 Why this pattern is worth a library, generally

The result is not about Equihash, or about hashing block headers. It is about a
shape that recurs wherever a hash is computed over **a long constant followed by
a short variable**:

    H(P || x)   for many x, with P fixed and |P| >> |x|

A streaming hash API forces the caller to absorb `P` again for every `x`. If
`P` is 140 bytes and `x` is 4, that is three compression-function blocks of
work to produce a digest whose input varied by four bytes. Keeping the state
*after* `P` and cloning it per `x` reduces that to one block. The measured
ratio -- 2.03x here -- is the ratio of compression-function blocks, and it is
predictable rather than empirical. BLAKE2b compresses 128 bytes at a time:

    libsodium   ceil((140 + 4) / 128) = 2 blocks per digest
    uniblake    2 - (140 / 128)       = 1 block per digest
    predicted   2.00x        measured 2.03x

The model matching to within 1.5% is the evidence that this, and not
instruction-level speed, is the whole effect. It also says exactly when the
technique stops paying: the ratio rises with prefix length and falls to 1.0x as
the tail grows past the prefix.

Where the shape appears, in general:

| Setting | Fixed prefix | Varying tail |
|---|---|---|
| Keyed derivation / KDF trees | context, salt, domain label | index or counter |
| Content-addressed chunking | file or manifest header | chunk index |
| Merkle and hash-tree construction | domain-separation tag | node payload |
| Deduplication indexes | namespace prefix | record key |
| Rendezvous / consistent hashing | node identifier | key being placed |
| Log or ledger commitments | epoch header | entry |
| PRNG expansion from a seed | seed and personalization | counter |
| Any `H(domain_sep || item)` loop | the separator | the item |

The last row is the common case: **domain separation is a fixed prefix by
construction.** Any codebase that hashes `H(tag || value)` in a loop -- and most
protocol code does -- is paying the same avoidable cost, in proportion to how
long the tag is relative to the value.

Two conditions decide whether the technique pays:

1. **The prefix must be genuinely constant across the batch.** If it changes per
   item there is no state to reuse.
2. **The prefix must be long relative to the tail.** At `|P| ~ |x|` the saving
   is small; the bulk rows in S2 are the limiting case, where the prefix is a
   negligible fraction and the two libraries converge to within 1-2%.

This is a *library ergonomics* result as much as a performance one. The saving
requires an API that exposes "clone the state after the prefix"
(`ub_hash_tail`, `ub_hash_n`); a conventional `init/update/final` interface can
express it only by copying an opaque state the caller is not supposed to know
the size of, which is exactly what `eh_hashstate.h` had to wrap. **The cost is
not in the hash -- it is in the interface not admitting the pattern.**

## 3. What this corrects in Perf.md S5

`Perf.md` S5 diagnosed Equihash's CPU share as libsodium running an
unaccelerated scalar compression function on aarch64, and recommended
replacing the hashing at this one call site rather than patching libsodium's
dispatcher.

**That recommendation was executed, via uniblake** (`c9bbe6ad9`, 2026-09-02),
and the structural half of the diagnosis was right: the fix belonged at the
call site. But the win did **not** come from a faster compression function.
Both libraries compress at the same rate here (1.01x on bulk). It came from
calling the compression function **half as often** -- see S2.

S5's conclusion that a **libsodium version bump cannot fix this** is confirmed
independently: blake2b is byte-identical between 1.0.21 and 1.0.22
(`SODIUM_SURVEY.md` S5).

## 4. Scope of the remaining opportunity

uniblake's 2x applies to the prefix-reuse pattern. Of the seven files still on
libsodium blake2b, only `CBLAKE2bWriter` has comparable call volume -- and its
pattern is *not* prefix-reuse: each transaction hash is a fresh personalized
state over different data, which is the 1.01x bulk case, not the 2.03x case.

**So migrating the remaining call sites should not be expected to yield 2x.**
It is a correctness-risk change to consensus-critical code with a likely
low-single-digit payoff. Measure the pattern before assuming the ratio.

The honest summary: **uniblake solved the Equihash hashing pattern, and that
pattern does not recur elsewhere in Zero.**
