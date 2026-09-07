# libsodium across the Zcash family, and Zero's position

Survey of `~/Work/ZK/ZKs` archival repos plus the upstream release timeline,
taken 2026-09-05. Companion to `CROSSPROJECT.md` S5, which covers the pin
itself.

## 1. Peers, for context

Cross-repo comparison lives in `ZK/ZKs/Comparison.md` S9. In short: Zero at
1.0.21 was ahead of every peer surveyed (Zcash 1.0.20, others 1.0.18), and
Zcash has moved blake2b out of libsodium into Rust entirely -- which is the
precedent for Zero's own uniblake work.

## 3. Release timeline against Zero's work

| Date | Event |
|---|---|
| 2024-05-24 | libsodium 1.0.20 released -- what Zcash still pins |
| 2026-01-06 | libsodium **1.0.21** released -- Zero's current pin |
| 2026-04-08 | libsodium **1.0.22** released |
| 2026-08-18 | Zero `ab6c14ad6` -- perffdcache block-read fix |
| **2026-09-01** | Zero `efa3aadae` -- adds `_cflags_release=-O3` to `libsodium.mk` |
| 2026-09-02 | Zero `c9bbe6ad9` -- Equihash hashes through uniblake (B1) |
| 2026-09-03 | Zero `c2762edd5` -- Linux build with uniblake |

**1.0.22 had been available for five months** when `libsodium.mk` was edited
on 2026-09-01. That edit added an `-O3` override and left the version alone.

The likely reading: attention at that moment was on **tuning libsodium as a
benchmark oracle** for the uniblake comparison landing the next day, not on
tracking upstream. The `-O3` line and the uniblake port are one day apart.
Nothing indicates 1.0.22 was evaluated and rejected; it appears simply not to
have been considered.

## 4. What 1.0.22 actually brings

From the upstream ChangeLog:

- **New:** ML-KEM768 and X-Wing post-quantum KEMs; SHA-3
  (`crypto_hash_sha3256/512`).
- **Performance:** NEON Argon2 on ARM; ARM SHA3 instructions; WebAssembly SIMD
  Argon2; improved MSVC builds.
- **Fixes:** GCC on aarch64 and gcc 4.x; aes256-gcm on aarch64 for non-clang;
  VS2026 compatibility; `hmacsha256/512_init` accept NULL keys.

**None of it touches Zero's paths.** Zero uses no Argon2, no SHA-3, no KEM, and
builds with clang on aarch64. No security fix is listed.

Source-diff confirmation (`CROSSPROJECT.md` S4): 239 files differ only by
`LCOV_EXCL_LINE` comments; 54 have substantive changes, none in blake2b or
ed25519.

## 5. Measured: ZeroPerf rebuilt and retested at 1.0.22

ZeroPerf was rebuilt against 1.0.22 and re-benchmarked. **Zero400 was not
touched** and remains at 1.0.21.

The C++ source is identical between the two builds: the only commit between
them is `74b2f55ab` "perf docs", which changes no file under `src/`, and the
working tree's `src/` was clean. libsodium version is the only variable.

### 5.1 Reindex throughput

Tiny snap, 0-187417, `-reindex -disablewallet`, same machine.

| Build | blk/s | wall | machine load at start |
|---|--:|--:|--:|
| 1.0.21 control | 1358.09 | 138.0 s | idle |
| 1.0.21 control | 1348.32 | 139.0 s | idle |
| 1.0.22 | 1388.27 | 135.0 s | idle |
| 1.0.22 | 1368.01 | 137.0 s | idle |
| 1.0.22 | ~~1156.90~~ | 162.0 s | **3.48 -- contended, excluded** |

Idle runs only:

| Build | n | mean blk/s | sd | range |
|---|--:|--:|--:|---|
| 1.0.21 | 2 | 1353.20 | 6.91 | 1348.32 - 1358.09 |
| 1.0.22 | 2 | 1378.14 | 14.33 | 1368.01 - 1388.27 |

**Delta +24.9 blk/s, +1.84%, and the two ranges do not overlap.**

### The +1.84%: overstated, and not worth the attention it got

An earlier revision of this document called the +1.84% "real but not a blake2b
effect" and offered binary layout as the explanation. **Both halves deserve
less confidence than that wording gave them.**

The arithmetic, laid out:

| | mean | spread across its own runs |
|---|--:|--:|
| 1.0.21, n=2 | 1353.20 | 9.77 blk/s (0.72%) |
| 1.0.22, n=2 | 1378.14 | 20.26 blk/s (1.47%) |
| gap | 24.94 (1.84%) | |

**The 1.0.22 spread alone is 20.26 blk/s against a 24.94 gap, at n=2 per
side.** Non-overlapping ranges from two points each is not evidence of a 1.8%
effect; one further run on either side could erase it. The correct statement is
that **no difference was established**, not that a small one was found.

*Why it was written up at all.* Because the mechanism looked interesting: the
1.0.22 archive is 703952 bytes against 1.0.21's 567912, 24% larger from ML-KEM,
X-Wing and SHA-3 code Zero never calls, and linking a larger archive does move
Zero's own code. Layout effects of a few percent are real and well documented.
But "a plausible mechanism exists" is not evidence that this mechanism operated
here, and chasing a sub-2% delta on n=2 is exactly the kind of measurement this
lab's own policy warns against.

*What would settle it, if it ever mattered:* relink the **same** libsodium
version several times and see whether the number moves on its own. If a
relink-only rebuild swings 1-2%, layout is confirmed as the noise floor and no
libsodium comparison below that threshold means anything. That experiment is
cheap and has not been run.

**Resolved 2026-09-07, and more strongly than "unresolved".** The benchmark
reports wall time in whole seconds over a fixed 187417 blocks, so its output is
a discrete set: one second is ~9.8 blk/s, or **0.7%**. The +1.84% gap is 2.5
seconds of wall clock out of ~137 -- two to three quanta, from two samples per
side. With blake2b byte-identical between the versions and the compress kernel
compiling to identical assembly, the conclusion is **no difference**, measured
with an instrument too coarse to have shown one either way. Do not cite
+1.84%.

### The contended run

### The contended run

**The 1156.90 point is invalid, not a finding.** It ran while two libsodium
`depends` builds were competing for the same cores. Read alone it looks like a
15% regression, which is what it was almost reported as. The clean 1.0.22 run
is the *fastest* reindex measured on this machine to date.

That row is deliberately left in the store rather than retired. `--superseded`
asserts a corrected re-measurement of the same thing; this is a contaminated
run, which is a different claim, and RecBench has no marker for it. Deleting it
would remove the evidence that contention produces a 15% swing -- a bigger
effect than any libsodium version difference, and the reason lab runs must not
share a machine with builds.

### 5.2 Correctness

| Suite | 1.0.21 | 1.0.22 |
|---|---|---|
| gtest equihash / crypto / pow filter | 17/17 pass | 17/17 pass |
| gtest `WalletTests.*` | **fails** | **fails** |

The `WalletTests` sapling-witness assertion (`test_wallet.cpp:1630`, then an
abort in `GetSproutNoteWitnesses`, `wallet.cpp:2594`) fails **identically on
both**. It was verified by rebuilding the gtest binary against 1.0.21 and
re-running. **Pre-existing, unrelated to libsodium**, and worth filing
separately.

### 5.3 Micro-benchmark

`leaf.blake2b`, n=3 each, `-O3` static, same harness:

| Build | ns/digest | sd |
|---|--:|--:|
| 1.0.21 | 165.7 | 0.06 |
| 1.0.22 | 166.4 | 0.47 |

+0.42% -- noise, consistent with the compress kernel compiling to identical
assembly (`CROSSPROJECT.md` S4).

### 5.4 Verdict

**1.0.22 is operationally equivalent to 1.0.21 for Zero**, and safe to adopt:
identical test results including the same pre-existing failure, and blake2b
performance identical by construction.

On throughput, **no difference was established.** The observed +1.84% rests on
n=2 per side against a within-version spread of up to 1.47%, which is not
enough power to resolve it. Treat sub-2% differences on this benchmark as
noise until a relink-only experiment establishes the floor. The reasons to
upgrade remain the ones in S6.

## 6. Decision: ZeroPerf is on 1.0.22

**Switched 2026-09-05.** `depends/packages/libsodium.mk` pins 1.0.22 in
ZeroPerf; all lab binaries and benchmarks build against it, and
`contrib/perf/sodium_oracle.sh` supplies it as the benchmark oracle. **Zero400
remains on 1.0.21 and is not changed by this.**

Basis for the switch, all verified above:

- **Equivalent, not merely compatible.** blake2b and ed25519 differ only by
  `LCOV_EXCL_LINE` comments; the blake2b compress kernel compiles to
  byte-identical assembly. 239 of 293 source files differ only in comments.
- **Same test results**, including the same pre-existing `WalletTests`
  sapling-witness failure, which reproduces identically on 1.0.21 and is
  unrelated to libsodium.
- **No throughput difference established** (S5).
- 1.0.22 is the current release; the previous pin's stated reason was circular
  with zerowallet and technically empty.

What this does **not** claim: that 1.0.22 is faster. It is not, measurably.
The switch is currency and the removal of an unjustified pin.

**Standing rule for perf work:** measure against 1.0.22, and state the oracle's
provenance (built here / distro / bottle) alongside its version and flags. A
packaged build of the same version measured 13.2% slower on leaf
(`CROSSPROJECT.md` S4), which is larger than any difference between versions.

**Reference baseline on the standing build** (`campaign=tiny-baseline-sod122`):
tiny snap 0-187417, `-reindex -disablewallet`, 140.0 s, **1338.69 blk/s**. That
sits inside the 1348-1388 band every build measured today across both
libsodium versions, which is the practical statement of their equivalence: the
version is not resolvable above this benchmark's run-to-run spread.

## 7. Open: Zero400

ZeroPerf is settled (S6). **Zero400 remains on 1.0.21**, deliberately: this
tree does not change the product tree (`POLICY.md` S7), and a consensus-code
dependency bump is a decision for the tree that owns it.

What the product tree would need, none of it blocking:

| Step | Note |
|---|---|
| Bump `libsodium.mk` to 1.0.22 + hash | The hash is verified: `adbdd8f1...3349` |
| Drop the circular zerowallet comment | zerowallet shares no ABI with the node; RPC only |
| Rebuild zerowallet on 1.0.22 | It uses `crypto_secretbox` / sha256 / `randombytes` only, all long-stable |
| Run the product test suite | Expect the same pre-existing `WalletTests` failure, which is not libsodium's |

The evidence that this is low-risk is in S5: same tests, same results,
byte-identical blake2b and ed25519. There is no urgency -- no security fix is
listed in 1.0.22 -- and no measured performance reason. The reason to do it is
currency and removing a pin that justifies itself circularly.

Worth more than the version bump: **the seven files still on libsodium blake2b**
(`HASHLIBS.md` S1). Zcash removed blake2b from libsodium entirely, in Rust;
Zero has done it for Equihash, in C. But note `HASHLIBS.md` S4 -- those
remaining sites do not share Equihash's prefix-reuse shape, so they should not
be expected to yield 2x.
