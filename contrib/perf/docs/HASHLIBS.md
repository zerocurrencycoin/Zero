# Which library does what: uniblake and libsodium in Zero

Zero links both. They are not alternatives competing for the same job -- each
owns a distinct set of functions, and one call path moved from the second to
the first. This document states the division, the measured difference where
they overlap, and why the overlap is narrower than it looks.

Numbers measured 2026-09-05 on Apple M4 Pro, macOS 26.3, arm64, against
**libsodium 1.0.22** built `-O3` static; harness compiled `-O2`, matching
Zero's own build (`depends/hosts/darwin.mk:11`).

## 1. The division of labour

**uniblake owns Equihash hashing** -- the prefix-state wrapper
(`crypto/eh_hashstate.h`), the Equihash core, both tromp solver headers, block
validation via `pow.cpp`, mining, benchmarks and three test files.

**libsodium owns everything else** -- Ed25519 for JoinSplit signatures, AEAD
for note encryption, scalar multiplication, entropy, library init, **and
blake2b in the seven files that did not move.**

Both libraries therefore compute blake2b, on different data: Equihash headers
through uniblake, transaction and note hashing through libsodium. Neither is a
drop-in for the other's remaining scope without a migration. The per-file
counts are in S1.4 and are not repeated here.

## 1.4 Full library inventory

Counted from source 2026-09-08, excluding `.deps/`, vendored `secp256k1`,
`univalue`, `leveldb` and `snark`. This is the whole cryptographic dependency
surface; nothing below is restated elsewhere.

### libsodium: 15 functions, 4 subsystems

libsodium is a **general-purpose cryptographic library**, and Zero uses it as
one: blake2b is a minority of its call sites.

| Subsystem | Functions | Calls | Where | Replaceable? |
|---|---|--:|---|---|
| **Ed25519 signatures** | `crypto_sign_detached`, `crypto_sign_verify_detached`, `crypto_sign_keypair`, `crypto_sign` | 48 | `crypto/common.h`, `main.cpp`, `transaction_builder.cpp`, `wallet/*`, tests | **No.** Consensus: JoinSplit signature validation |
| **blake2b hashing** | `crypto_generichash_blake2b_{init_salt_personal,update,final,salt_personal}`, `_state` | 20 | 7 files, below | In principle; see S4 |
| **AEAD** | `crypto_aead_chacha20poly1305_ietf_{encrypt,decrypt}` | 8 | `zcash/NoteEncryption.cpp` | **No.** Note encryption |
| **Scalar mult / entropy / init** | `crypto_scalarmult`, `crypto_scalarmult_base`, `randombytes_buf`, `sodium_init` | 17 | `zcash/NoteEncryption.cpp`, `random.cpp`, `crypto/common.h` | **No** |

**93 calls total; 20 are blake2b.** Removing blake2b would not remove the
dependency -- Ed25519, AEAD and entropy keep it, and they are consensus code.

### libsodium blake2b: the 7 files that did not move

| File | Calls | What it hashes | Call shape |
|---|--:|---|---|
| `zcash/prf.cpp` | 9 | Sprout PRF outputs | one-shot, per note |
| `zcash/address/zip32.cpp` | 6 | Key derivation | one-shot, per derivation |
| `zcash/NoteEncryption.cpp` | 6 | Note encryption KDF | one-shot, per note |
| `script/interpreter.cpp` | 6 | ZIP-143 personalization | constants + one-shot |
| `hash.h` (`CBLAKE2bWriter`) | 4 | **Sighash and tx hashing** | streaming, per transaction |
| `zcash/JoinSplit.cpp` | 2 | JoinSplit hashing | one-shot |
| `zcash/address/sapling.cpp` | 1 | Address derivation | one-shot |

`CBLAKE2bWriter` is the only high-volume site -- every transaction in every
block. The rest run per note, per address or per derivation.

### uniblake: 18 calls, 10 files, one subsystem

| Layer | Files | Calls |
|---|---|--:|
| State wrapper | `crypto/eh_hashstate.h` | 6 |
| Equihash core | `crypto/equihash.cpp`, `.h` | 4 |
| Block validation | `pow.cpp` | via `EhPrefixState` |
| Mining | `miner.cpp`, `rpc/mining.cpp` | 2 |
| Tromp solver | `pow/tromp/equi.h`, `equi_miner.h` | 2 |
| Benchmarks and tests | `zcbenchmarks.cpp`, `gtest/test_equihash.cpp`, `test/miner_tests.cpp` | 4 |

**uniblake is not a general-purpose library and does not try to be.** It
implements blake2b only, and its API is shaped for one access pattern: many
short digests over a shared prefix (S2). That is why it covers one Zero
subsystem completely and none of the others -- the others do not have that
shape.

### librustzcash: 31 of 32 exported functions used

| Group | Functions | Calls |
|---|---|--:|
| Sapling proving / verifying | `sapling_{proving,verification}_ctx_{init,free}`, `sapling_{spend,output}_proof`, `sapling_check_{spend,output}`, `sapling_final_check`, `sapling_{spend,binding}_sig` | 33 |
| Sapling key and note math | `sapling_ka_{agree,derivepublic}`, `sapling_compute_{cm,nf}`, `sapling_generate_r`, `crh_ivk`, `ivk_to_pkd`, `nsk_to_nk`, `check_diversifier`, `to_scalar` | 20 |
| ZIP-32 derivation | `zip32_xsk_{master,derive}`, `zip32_xfvk_{derive,address}` | 4 |
| Sprout | `sprout_{prove,verify}` | 2 |
| Merkle tree | `merkle_hash`, `tree_uncommitted` | 3 |
| Parameters | `init_zksnark_params` | 3 |

**Not used: `librustzcash_eh_isvalid`** -- the Rust Equihash validator, the one
export Zero declines. Zero validates Equihash in C++
(`Equihash<N,K>::IsValidSolution`) through uniblake, which is why S3's
migration mattered and why the Rust path is dead weight in the linked archive.

### Three blake2b implementations are linked into one binary

`nm src/zerod` finds all three:

| Implementation | Reached via | Used for |
|---|---|---|
| libsodium's | direct calls | the 7 files above |
| `blake2_rfc` (Rust) | inside `librustzcash.a` | librustzcash's internals; no Zero call site |
| uniblake | direct calls | Equihash hashing |

This is not waste to be cleaned up casually: each arrives with a dependency
that is used for something else. It is worth knowing when reading a profile --
a `blake2b` frame may belong to any of the three, and only the symbol name
distinguishes them.

## 1.5 Open research: where else the cryptographic surface could give

Not scoped, not measured, not scheduled. Recorded so the questions are asked
once rather than rediscovered. Each needs a measurement before it needs a
design.

### A. The non-blake2b libsodium surface

73 of Zero's 93 libsodium calls are not blake2b (S1.4) and none has been
profiled. The questions, in order of likely payoff:

| Function group | Calls | Question |
|---|--:|---|
| `crypto_sign_verify_detached` | 16 | Every JoinSplit signature. Batch verification exists for Ed25519 (`ed25519-dalek` batch API, ~2x at n>=8). Does Zero ever verify more than one at a time? |
| `crypto_sign_detached` / `_keypair` | 30 | Mostly wallet and test paths. Likely cold; confirm before spending anything |
| `crypto_aead_chacha20poly1305_ietf_*` | 8 | Per shielded output. libsodium picks a SIMD backend at runtime -- is the aarch64 path taken here, or is this a second instance of the blake2b situation? |
| `crypto_scalarmult` | 3 | Per note decryption. Curve25519; a fixed-base variant may apply to `_base` |
| `randombytes_buf` | 12 | Entropy source. Correctness-critical, not a speed target |

**The first question to answer is whether any of this is hot.** The reindex
profile attributes 57.5% to anchor computation, 20.5% to disk, 16.5% to
Equihash and 5.6% to Groth16 -- leaving little room, which suggests the answer
is "no" for sync and "possibly" for wallet operations that were never profiled.

### B. librustzcash / librustcrypto

Zero pins a 2018 commit of a crate that no longer exists upstream
(`../PerfGroth.md`). Any optimisation here is downstream of that decision:
current upstream has years of arithmetic improvements in `bls12_381` and
`bellman`, none of which reach Zero. **Do not scope micro-optimisation of the
pinned code** -- the same effort spent on the dependency question returns more.

### C. `CBLAKE2bWriter` and the four one-shot sites

`hash.h`'s `CBLAKE2bWriter` runs on every transaction in every block, and
`prf.cpp` / `zip32.cpp` / `NoteEncryption.cpp` / `interpreter.cpp` call blake2b
per note, per derivation and per sighash component (S1.4).

They stayed on libsodium for a structural reason, not an oversight: **uniblake's
API expresses one shape** -- clone a state after a shared prefix, append a short
tail -- and these sites do not have it. `CBLAKE2bWriter` streams arbitrary
serialized data through `init/update/final`; the one-shot sites hash a distinct
message each time under a personalization string.

**Two sub-questions, separable:**

1. *Is the personalization+one-shot pattern worth a uniblake entry point?*
   Those sites share a personalization block and differ only in the message.
   That is a **fixed 64-byte parameter block**, not a fixed message prefix, so
   the S2 saving does not apply -- but the `init_salt_personal` work is
   repeated per call and could be precomputed once per personalization.
   Measure `init_salt_personal` as a fraction of a short-message digest before
   designing anything.

2. *Does `CBLAKE2bWriter` need a streaming uniblake?* It would need
   `init/update/final` with no prefix reuse -- which is the 1.01x bulk case
   (S2), i.e. **no expected gain**. The case for it is uniformity, not speed,
   and uniformity is not worth touching consensus hashing for.

### D. Extending uniblake to the shape these sites need

The general form, if the measurements in C justify it:

    ub_init_personal(state, outlen, personal)   -- exists
    ub_clone(dst, src)                          -- exists as ub_copy
    ub_hash_tail(state, tail, n, out, outlen)   -- exists

What is missing is a **one-shot with precomputed personalization**:

    ub_param_init(param, outlen, salt, personal)   /* once per call site */
    ub_hash_param(param, msg, n, out, outlen)      /* per message */

This keeps uniblake's single-purpose character -- still only blake2b, still
about repeated work over a fixed element -- while covering the pattern that
currently forces libsodium. It is the same idea as the prefix state, applied to
the parameter block instead of the message.

**Prerequisite:** a measurement showing `init_salt_personal` is a non-trivial
share of these call sites. If it is 2% of a one-shot digest, this buys nothing
and the four files should stay on libsodium.

### E. A compatibility surface: `ubc_`

The design above still asks the caller to adopt uniblake's shape. A second and
probably better option is to stop asking.

**The bar for the remaining sites is not "beat libsodium by 2x". It is "match
libsodium, through one library instead of two."** Those sites have no prefix to
reuse; the specialised machinery that wins 2.03x on Equihash buys nothing
there, and carrying it into them adds risk to consensus hashing for no return.

So expose a **separate, deliberately plain API** -- `ubc_` for
*uniblake-compatible* -- that mirrors libsodium's generichash surface
one-for-one:

    ubc_init_salt_personal(state, outlen, key, keylen, salt, personal)
    ubc_update(state, in, inlen)
    ubc_final(state, out, outlen)
    ubc_hash(out, outlen, in, inlen, key, keylen)      /* one-shot */

Properties that make this worth doing where the optimised API is not:

| Property | Why it matters |
|---|---|
| **Drop-in shape** | `CBLAKE2bWriter` and the four one-shot sites change a symbol, not a structure. A mechanical, reviewable diff on consensus code |
| **Implementation is free to differ** | `ubc_` need not be the prefix-optimised core. It can be the plain compress loop, or share it, or wrap the same kernel -- the contract is the interface, not the internals |
| **Only obligation is parity** | It must be **at least as fast as libsodium** and produce identical digests. Neither is a high bar: the compression functions already match within 1-2% (S2) |
| **Retires a dependency edge, not the dependency** | libsodium stays for Ed25519, AEAD and entropy (S1.4). What goes is *blake2b arriving from two libraries* |

**What it does not promise.** No speedup. The honest pitch is uniformity and
one fewer hash implementation in the binary (three today, S1.4), which matters
for auditability and for reading a profile -- not for throughput.

**Sequence, if taken up:** define `ubc_` against libsodium's KATs; prove digest
identity on the Sprout and Sapling personalizations Zero uses; measure parity
on a one-shot and a streaming workload; only then convert call sites, one file
at a time, starting with the lowest-volume (`sapling.cpp`, 1 call) rather than
`hash.h`.

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
