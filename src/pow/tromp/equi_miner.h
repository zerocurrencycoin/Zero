// Equihash solver
// Copyright (c) 2016 John Tromp, The Zcash developers

// Fix N, K, such that n = N/(k+1) is integer
// Fix M = 2^{n+1} hashes each of length N bits,
// H_0, ... , H_{M-1}, generated from (n+1)-bit indices.
// Problem: find binary tree on 2^K distinct indices,
// for which the exclusive-or of leaf hashes is all 0s.
// Additionally, it should satisfy the Wagner conditions:
// for each height i subtree, the exclusive-or
// of its 2^i corresponding hashes starts with i*n 0 bits,
// and for i>0 the leftmost leaf of its left subtree
// is less than the leftmost leaf of its right subtree

// The algorithm below solves this by maintaining the trees
// in a graph of K layers, each split into buckets
// with buckets indexed by the first n-RESTBITS bits following
// the i*n 0s, each bucket having 4 * 2^RESTBITS slots,
// twice the number of subtrees expected to land there.

#include "pow/tromp/equi.h"
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <assert.h>

typedef uint16_t u16;
typedef uint64_t u64;

// EQUIHASH_TROMP_THREADED enables the multi-threaded solver: worker threads,
// the round barrier, and the atomic slot/solution counters those threads
// require. The three are one feature and must move together -- threads without
// atomics hand two workers the same slot; atomics without threads pay for a
// capability nothing uses.
//
// miner.cpp constructs equi eq(1) (single-threaded), so this is OFF. Define it
// in the same change that passes nthreads > 1, never separately.
#ifdef EQUIHASH_TROMP_THREADED
#include <atomic>
typedef std::atomic<u32> au32;
#else
typedef u32 au32;
#endif

#ifndef RESTBITS
#define RESTBITS	4
#endif

// 2_log of number of buckets
#define BUCKBITS (DIGITBITS-RESTBITS)

#ifndef SAVEMEM
#if RESTBITS <= 7
// Can't save memory in such small buckets. Expected occupancy is NSLOTS/2, and
// at these sizes the per-bucket variance is too large to under-allocate: a
// bucket that overruns drops rows (bfull) and silently loses solutions.
// Upstream wrote `RESTBITS == 4` here; the bound is the sample count, not the
// exact value, so 5..7 belong on this arm too rather than leaving SAVEMEM
// undefined (which fails to compile at NSLOTS).
#define SAVEMEM 1
#else
// take advantage of law of large numbers (sum of 2^8 random numbers)
// this reduces (200,9) memory to under 144MB, with negligible discarding
#define SAVEMEM 9/14
#endif
#endif

// number of buckets
static const u32 NBUCKETS = 1<<BUCKBITS;
// 2_log of number of slots per bucket
static const u32 SLOTBITS = RESTBITS+1+1;
static const u32 SLOTRANGE = 1<<SLOTBITS;
// number of slots per bucket
static const u32 NSLOTS = SLOTRANGE * SAVEMEM;
// number of per-xhash slots
static const u32 XFULL = 16;
// SLOTBITS mask
static const u32 SLOTMASK = SLOTRANGE-1;
// number of possible values of xhash (rest of n) bits
static const u32 NRESTS = 1<<RESTBITS;
// number of blocks of hashes extracted from single 512 bit blake2b output
static const u32 NBLOCKS = (NHASHES+HASHESPERBLAKE-1)/HASHESPERBLAKE;
// nothing larger found in 100000 runs
static const u32 MAXSOLS = 8;

// tree node identifying its children as two different slots in
// a bucket on previous layer with the same rest bits (x-tra hash)
//
// tree_t is the packed field. It must hold BUCKBITS + 2*SLOTBITS bits. That
// sum has a closed form -- the RESTBITS terms do NOT cancel:
//
//   (DIGITBITS - RB) + 2*(RB + 2) = DIGITBITS + RB + 4
//
// so the tag grows one bit per RESTBITS step. At (192,7) that is 28 + RB:
// exactly 32 at RB 4, and 33 at RB 5 -- it overflows u32 AT 5, not above 6.
// At (200,9) it is 24 + RB, fitting u32 through RB 8, which is why upstream
// ships RESTBITS 4/8/9 arms there and only 4 here: Zero's DIGITBITS is 24 to
// (200,9)'s 20, costing four bits of tag headroom at equal RESTBITS.
//
// Widening tree_t to u64 used to corrupt the heap: alloctrees() laid the
// per-round arrays out with `(bucket0 *)(heap0 + r/2)` where heap0 was u32*,
// hard-coding sizeof(tree) == 4. heap0/heap1 are now tree*, so that arithmetic
// carries the right unit, and SLOTPAD0/SLOTPAD1 buy the extra room the final
// round needs. Build the u64 layout with -DEQUIHASH_TREE_T64.
//
// Note the tag width is not the only constraint on raising RESTBITS: getxhash0,
// getxhash1 and the bucketid extraction are all #if-gated on (WN, RESTBITS) and
// #error on unhandled combinations. See contrib/perf/equ/SOLVER.md S2.3.
//
// The static_assert below enforces the fit, replacing upstream's
// "#error tree doesnt fit in 32 bits".
// EQUIHASH_TREE_T64 builds the experimental u64-tag layout. Default stays u32:
// the shipped (192,7) RESTBITS-4 config needs exactly 32 bits, and the wider
// tag costs 1.38x heap (3.25 -> 4.50 GiB). Only useful as groundwork for
// RESTBITS >= 5, where the tag no longer fits 32 bits.
#ifdef EQUIHASH_TREE_T64
typedef u64 tree_t;
#else
typedef u32 tree_t;
#endif

struct tree {
  tree_t bid_s0_s1; // manual bitfields

  tree(const u32 idx) {
    bid_s0_s1 = idx;
  }
  tree(const u32 bid, const u32 s0, const u32 s1) {
    // Cast BEFORE shifting: (bid << SLOTBITS) in u32 truncates silently once
    // BUCKBITS + SLOTBITS exceeds 32, and the result would then be widened
    // after the damage. This is the one place a width change goes wrong
    // invisibly.
    bid_s0_s1 = (((tree_t)bid << SLOTBITS) | s0) << SLOTBITS | s1;
  }
  u32 getindex() const {
    return (u32)bid_s0_s1;
  }
  u32 bucketid() const {
    return (u32)(bid_s0_s1 >> (2 * SLOTBITS));
  }
  u32 slotid0() const {
    return (u32)((bid_s0_s1 >> SLOTBITS) & SLOTMASK);
  }
  u32 slotid1() const {
    return (u32)(bid_s0_s1 & SLOTMASK);
  }
};

static_assert(BUCKBITS + 2 * SLOTBITS <= 8 * sizeof(tree_t),
              "tree tag does not fit tree_t: raise tree_t or lower RESTBITS");

union hashunit {
  u32 word;
  uchar bytes[sizeof(u32)];
};

#define WORDS(bits)	((bits + 31) / 32)
#define HASHWORDS0 WORDS(WN - DIGITBITS + RESTBITS)
#define HASHWORDS1 WORDS(WN - 2*DIGITBITS + RESTBITS)

// Slot padding, in 4-byte hash units, added to the hash array.
//
// The slot must hold, at the LAST round it participates in, one tree word per
// round so far PLUS the residual hash. Natural size satisfies that with a u32
// tag but not a u64 one (see the static_asserts in alloctrees). SLOTPAD0 /
// SLOTPAD1 buy the shortfall explicitly, so the requirement is a number in one
// place rather than a property of struct padding.
//
// Sized from the same inequality alloctrees asserts, so raising sizeof(tree)
// re-derives them instead of silently overflowing. Both are 0 for a u32 tag,
// which keeps the shipped layout byte-identical.
#define SLOT_NEED0 (((WK + 1) / 2) * sizeof(tree) + 4)
#define SLOT_NEED1 (((WK) / 2) * sizeof(tree) + 4)
#define SLOT_NAT0  (sizeof(tree) + HASHWORDS0 * 4)
#define SLOT_NAT1  (sizeof(tree) + HASHWORDS1 * 4)
#define SLOTPAD0 (SLOT_NEED0 > SLOT_NAT0 ? (SLOT_NEED0 - SLOT_NAT0 + 3) / 4 : 0)
#define SLOTPAD1 (SLOT_NEED1 > SLOT_NAT1 ? (SLOT_NEED1 - SLOT_NAT1 + 3) / 4 : 0)

struct slot0 {
  tree attr;
  hashunit hash[HASHWORDS0 + SLOTPAD0];
};

struct slot1 {
  tree attr;
  hashunit hash[HASHWORDS1 + SLOTPAD1];
};

// The slot is the unit the heaps are sized in, so its size is the memory
// story. alignof(tree) propagates: widening tree_t to u64 gives slot1 an
// 8-byte alignment over a 28-byte payload, so it pads to 32 -- a jump of 8,
// not 4. Assert the expected sizes rather than discover a silent regression
// in a memory measurement.
static_assert(sizeof(slot0) == sizeof(tree)
                               + (HASHWORDS0 + SLOTPAD0) * sizeof(hashunit)
                               + (sizeof(tree) - ((HASHWORDS0 + SLOTPAD0) * sizeof(hashunit)) % sizeof(tree)) % sizeof(tree),
              "slot0 size unexpected: check tree_t width and padding");
// The padding must actually close the gap it exists to close.
static_assert(SLOT_NEED0 <= sizeof(slot0), "SLOTPAD0 too small");
static_assert(SLOT_NEED1 <= sizeof(slot1), "SLOTPAD1 too small");
static_assert(sizeof(slot0) % alignof(tree) == 0, "slot0 not tree-aligned");
static_assert(sizeof(slot1) % alignof(tree) == 0, "slot1 not tree-aligned");

// a bucket is NSLOTS treenodes
typedef slot0 bucket0[NSLOTS];
typedef slot1 bucket1[NSLOTS];
// the N-bit hash consists of K+1 n-bit "digits"
// each of which corresponds to a layer of NBUCKETS buckets
typedef bucket0 digit0[NBUCKETS];
typedef bucket1 digit1[NBUCKETS];

// size (in bytes) of hash in round 0 <= r < WK
u32 hashsize(const u32 r) {
  const u32 hashbits = WN - (r+1) * DIGITBITS + RESTBITS;
  return (hashbits + 7) / 8;
}

u32 hashwords(u32 bytes) {
  return (bytes + 3) / 4;
}

// manages hash and tree data
//
// Heap layout (xenoncat's, via tromp): a slot at round r is
//     [tree_0][tree_2]...[tree_r][remaining hash words]
// so each successive even round PREPENDS one tree word, occupying space the
// shortening hash has vacated. trees0[r/2] therefore begins r/2 TREE WORDS
// into the heap -- not r/2 machine words, and not r/2 bytes.
//
// The heap pointers are typed `tree *` so that pointer arithmetic carries the
// unit. Typing them `u32 *` (as upstream does) silently hard-codes
// sizeof(tree) == 4 and corrupts the layout the moment the tag widens.
struct htalloc {
  tree *heap0;
  tree *heap1;
  bucket0 *trees0[(WK+1)/2];
  bucket1 *trees1[WK/2];
  u32 alloced;
  htalloc() {
    alloced = 0;
  }
  void alloctrees() {
// optimize xenoncat's fixed memory layout, avoiding any waste
// digit  trees  hashes  trees hashes
// 0      0 A A A A A A   . . . . . .
// 1      0 A A A A A A   1 B B B B B
// 2      0 2 C C C C C   1 B B B B B
// 3      0 2 C C C C C   1 3 D D D D
// 4      0 2 4 E E E E   1 3 D D D D
// 5      0 2 4 E E E E   1 3 5 F F F
// 6      0 2 4 6 . G G   1 3 5 F F F
// 7      0 2 4 6 . G G   1 3 5 7 H H
// 8      0 2 4 6 8 . I   1 3 5 7 H H
    assert(DIGITBITS >= 16); // ensures hashes shorten by 1 unit every 2 digits
    // Each slot must be able to hold one tree word per even (resp. odd) round
    // ahead of its hash, or the prepend walks past the slot.
    // Per-round capacity, which is far tighter than "enough room for all the
    // tree words". At round r a slot holds (r/2+1) tree words PLUS the hash
    // still in flight, and the hash only shrinks by one 4-byte unit every two
    // rounds -- so the binding case is the LAST round, not the total.
    // At (192,7) with a u32 tag, round 6 needs 4*4 + 4 = 20 B of a 28 B slot.
    // With a u64 tag it needs 4*8 + 4 = 36 B of a 32 B slot: overflow, and the
    // solver emits solutions that do not verify rather than crashing.
    static_assert(((WK + 1) / 2) * sizeof(tree) + 4 <= sizeof(slot0),
                  "slot0 overflows at the final even round: tree words plus "
                  "residual hash exceed the slot");
    static_assert((WK / 2) * sizeof(tree) + 4 <= sizeof(slot1),
                  "slot1 overflows at the final odd round");
    heap0 = static_cast<tree *>(alloc(1, sizeof(digit0)));
    heap1 = static_cast<tree *>(alloc(1, sizeof(digit1)));
    for (int r = 0; r < WK; r++)
      if ((r & 1) == 0)
        trees0[r/2] = reinterpret_cast<bucket0 *>(heap0 + r/2);  // r/2 tree words in
      else
        trees1[r/2] = reinterpret_cast<bucket1 *>(heap1 + r/2);
  }
  void dealloctrees() {
    free(heap0);
    free(heap1);
  }
  void *alloc(const u32 n, const u32 sz) {
    void *mem  = calloc(n, sz);
    assert(mem);
    alloced += n * sz;
    return mem;
  }
};

typedef au32 bsizes[NBUCKETS];

u32 min(const u32 a, const u32 b) {
  return a < b ? a : b;
}

struct equi {
  crypto_generichash_blake2b_state blake_ctx;
  htalloc hta;
  bsizes *nslots; // PUT IN BUCKET STRUCT
  proof *sols;
  au32 nsols;
  u32 nthreads;
  u32 xfull;
  u32 hfull;
  u32 bfull;
#ifdef EQUIHASH_TROMP_THREADED
  pthread_barrier_t barry;
#endif
  equi(const u32 n_threads) {
    assert(sizeof(hashunit) == 4);
    nthreads = n_threads;
#ifdef EQUIHASH_TROMP_THREADED
    const int err = pthread_barrier_init(&barry, NULL, nthreads);
    assert(!err);
#else
    // Single-threaded build: the digit loops stride by nthreads, so anything
    // other than 1 would silently skip work.
    assert(nthreads == 1);
#endif
    hta.alloctrees();
    nslots = (bsizes *)hta.alloc(2 * NBUCKETS, sizeof(au32));
    sols   =  (proof *)hta.alloc(MAXSOLS, sizeof(proof));
  }
  ~equi() {
    hta.dealloctrees();
    free(nslots);
    free(sols);
  }
  void setstate(const crypto_generichash_blake2b_state *ctx) {
    blake_ctx = *ctx;
    memset(nslots, 0, NBUCKETS * sizeof(au32)); // only nslots[0] needs zeroing
    nsols = 0;
  }
  u32 getslot(const u32 r, const u32 bucketi) {
#ifdef EQUIHASH_TROMP_THREADED
    return std::atomic_fetch_add_explicit(&nslots[r&1][bucketi], 1U, std::memory_order_relaxed);
#else
    return nslots[r&1][bucketi]++;
#endif
  }
  u32 getnslots(const u32 r, const u32 bid) { // SHOULD BE METHOD IN BUCKET STRUCT
    au32 &nslot = nslots[r&1][bid];
    const u32 n = min(nslot, NSLOTS);
    nslot = 0;
    return n;
  }
  void orderindices(u32 *indices, u32 size) {
    if (indices[0] > indices[size]) {
      for (u32 i=0; i < size; i++) {
        const u32 tmp = indices[i];
        indices[i] = indices[size+i];
        indices[size+i] = tmp;
      }
    }
  }
  void listindices0(u32 r, const tree t, u32 *indices) {
    if (r == 0) {
      *indices = t.getindex();
      return;
    }
    const bucket1 &buck = hta.trees1[--r/2][t.bucketid()];
    const u32 size = 1 << r;
    u32 *indices1 = indices + size;
    listindices1(r, buck[t.slotid0()].attr, indices);
    listindices1(r, buck[t.slotid1()].attr, indices1);
    orderindices(indices, size);
  }
  void listindices1(u32 r, const tree t, u32 *indices) {
    const bucket0 &buck = hta.trees0[--r/2][t.bucketid()];
    const u32 size = 1 << r;
    u32 *indices1 = indices + size;
    listindices0(r, buck[t.slotid0()].attr, indices);
    listindices0(r, buck[t.slotid1()].attr, indices1);
    orderindices(indices, size);
  }
  void candidate(const tree t) {
    proof prf;
    listindices1(WK, t, prf); // assume WK odd
    qsort(prf, PROOFSIZE, sizeof(u32), &compu32);
    for (u32 i=1; i<PROOFSIZE; i++)
      if (prf[i] <= prf[i-1])
        return;
#ifdef EQUIHASH_TROMP_THREADED
    u32 soli = std::atomic_fetch_add_explicit(&nsols, 1U, std::memory_order_relaxed);
#else
    u32 soli = nsols++;
#endif
    if (soli < MAXSOLS)
      listindices1(WK, t, sols[soli]); // assume WK odd
  }
  void showbsizes(u32 r) {
#if defined(HIST) || defined(SPARK) || defined(LOGSPARK)
    u32 binsizes[65];
    memset(binsizes, 0, 65 * sizeof(u32));
    for (u32 bucketid = 0; bucketid < NBUCKETS; bucketid++) {
      u32 bsize = min(nslots[r&1][bucketid], NSLOTS) >> (SLOTBITS-6);
      binsizes[bsize]++;
    }
    for (u32 i=0; i < 65; i++) {
#ifdef HIST
//      printf(" %d:%d", i, binsizes[i]);
#else
#ifdef SPARK
      u32 sparks = binsizes[i] / SPARKSCALE;
#else
      u32 sparks = 0;
      for (u32 bs = binsizes[i]; bs; bs >>= 1) sparks++;
      sparks = sparks * 7 / SPARKSCALE;
#endif
//      printf("\342\226%c", '\201' + sparks);
#endif
    }
//    printf("\n");
#endif
  }

  struct htlayout {
    htalloc hta;
    u32 prevhashunits;
    u32 nexthashunits;
    u32 dunits;
    u32 prevbo;
    u32 nextbo;
  
    htlayout(equi *eq, u32 r): hta(eq->hta), prevhashunits(0), dunits(0) {
      u32 nexthashbytes = hashsize(r);
      nexthashunits = hashwords(nexthashbytes);
      prevbo = 0;
      nextbo = nexthashunits * sizeof(hashunit) - nexthashbytes; // 0-3
      if (r) {
        u32 prevhashbytes = hashsize(r-1);
        prevhashunits = hashwords(prevhashbytes);
        prevbo = prevhashunits * sizeof(hashunit) - prevhashbytes; // 0-3
        dunits = prevhashunits - nexthashunits;
      }
    }
    u32 getxhash0(const slot0* pslot) const {
#if WN == 200 && RESTBITS == 4
      return pslot->hash->bytes[prevbo] >> 4;
#elif WN == 200 && RESTBITS == 8
      return (pslot->hash->bytes[prevbo] & 0xf) << 4 | pslot->hash->bytes[prevbo+1] >> 4;
#elif WN == 200 && RESTBITS == 9
      return (pslot->hash->bytes[prevbo] & 0x1f) << 4 | pslot->hash->bytes[prevbo+1] >> 4;
#elif (WN == 144 || WN == 192) && RESTBITS <= 8
      // DIGITBITS is 24 here, a whole number of bytes, so each round strips an
      // exact byte count and the residual stays byte-aligned. The RESTBITS are
      // therefore the low bits of a SINGLE byte -- no straddle, no shift, for
      // any RESTBITS up to 8. Contrast (200,9), where DIGITBITS 20 puts the
      // field across a byte boundary and forces the two-byte arms above.
      return pslot->hash->bytes[prevbo] & ((1u << RESTBITS) - 1);
#else
#error non implemented
#endif
    }
    u32 getxhash1(const slot1* pslot) const {
#if WN == 200 && RESTBITS == 4
      return pslot->hash->bytes[prevbo] & 0xf;
#elif WN == 200 && RESTBITS == 8
      return pslot->hash->bytes[prevbo];
#elif WN == 200 && RESTBITS == 9
      return (pslot->hash->bytes[prevbo]&1) << 8 | pslot->hash->bytes[prevbo+1];
#elif (WN == 144 || WN == 192) && RESTBITS <= 8
      return pslot->hash->bytes[prevbo] & ((1u << RESTBITS) - 1);
#else
#error non implemented
#endif
    }
    bool equal(const hashunit *hash0, const hashunit *hash1) const {
      return hash0[prevhashunits-1].word == hash1[prevhashunits-1].word;
    }
  };

  // Second-stage grouping: within one bucket, group slots by their RESTBITS
  // "x-hash" so only same-xhash pairs are XORed.
  //
  // This is the LINKING form (upstream tromp fc72754, 2016-10-27, from a
  // suggestion by judge Solardiz): xhashslots[xh] holds the head of a list and
  // nextxhashslot[] chains the rest, most-recent first. It replaces a
  // xhashslots[NRESTS][XFULL] array-per-xhash, which had two drawbacks:
  //   - clear() touched NRESTS*XFULL entries per bucket instead of
  //     NRESTS+NSLOTS;
  //   - a bucket whose xhash list exceeded XFULL dropped the excess pairs
  //     (counted in xfull), losing potential solutions.
  // A chain has no per-xhash capacity, so the XFULL overflow class disappears.
  // addslot() keeps its bool return -- now always true -- so the callers'
  // overflow branches stay in place for the array form and for any future
  // capacity-bounded variant.
  struct collisiondata {

// xslot indexes a slot within a bucket and must also represent the all-ones
// nil sentinel, so it needs NSLOTS < 2^bits -- strictly less, not <=.
// NSLOTS is 2^(RESTBITS+2), so uchar (nil=255) holds RESTBITS <= 5 and clashes
// at 6, where NSLOTS is exactly 256. Upstream's `<= 6` was off by one; the
// static_assert below caught it.
#if RESTBITS <= 5
    typedef uchar xslot;
#else
    typedef u16 xslot;
#endif
    // xnil is the all-ones sentinel, so it must not be a reachable slot index.
    // Assert rather than rely on the #if above staying in sync with NSLOTS.
    static const xslot xnil = ~(xslot)0;
    static_assert(NSLOTS <= (size_t)xnil,
                  "xslot too narrow: NSLOTS must be < the all-ones sentinel");
    xslot xhashslots[NRESTS];     // head slot of each xhash list, or xnil
    xslot nextxhashslot[NSLOTS];  // next slot in the same list, or xnil
    xslot nextslot;               // cursor for the current walk
    u32 s0;

    void clear() {
      memset(xhashslots, xnil, NRESTS * sizeof(xslot));
      memset(nextxhashslot, xnil, NSLOTS * sizeof(xslot));
    }
    bool addslot(u32 s1, u32 xh) {
      nextslot = xhashslots[xh];
      nextxhashslot[s1] = nextslot;
      xhashslots[xh] = (xslot)s1;
      return true;
    }
    bool nextcollision() const {
      return nextslot != xnil;
    }
    u32 slot() {
      const u32 ns = (u32)nextslot;
      nextslot = nextxhashslot[ns];
      return ns;
    }
  };

  void digit0(const u32 id) {
    uchar hash[HASHOUT];
    crypto_generichash_blake2b_state state;
    htlayout htl(this, 0);
    const u32 hashbytes = hashsize(0);
    for (u32 block = id; block < NBLOCKS; block += nthreads) {
      state = blake_ctx;
      u32 leb = htole32(block);
      crypto_generichash_blake2b_update(&state, (uchar *)&leb, sizeof(u32));
      crypto_generichash_blake2b_final(&state, hash, HASHOUT);
      for (u32 i = 0; i<HASHESPERBLAKE; i++) {
        const uchar *ph = hash + i * WN/8;
#if BUCKBITS == 16 && RESTBITS == 4
        const u32 bucketid = ((u32)ph[0] << 8) | ph[1];
#elif BUCKBITS == 12 && RESTBITS == 8
        const u32 bucketid = ((u32)ph[0] << 4) | ph[1] >> 4;
#elif BUCKBITS == 11 && RESTBITS == 9
        const u32 bucketid = ((u32)ph[0] << 3) | ph[1] >> 5;
#elif BUCKBITS == 20 && RESTBITS == 4
        const u32 bucketid = ((((u32)ph[0] << 8) | ph[1]) << 4) | ph[2] >> 4;
#elif BUCKBITS == 12 && RESTBITS == 4
        const u32 bucketid = ((u32)ph[0] << 4) | ph[1] >> 4;
        const u32 xhash = ph[1] & 0xf;
#elif BUCKBITS <= 24
        // General form: bucketid is simply the top BUCKBITS bits of the hash.
        // Read ceil(BUCKBITS/8)+1 bytes big-endian and shift the surplus off
        // the bottom. Verified to reproduce every specific arm above bit-for-
        // bit, so those remain only as hand-tuned equivalents.
        const u32 BUCKET_BYTES = (BUCKBITS + 7) / 8 + 1;
        u32 bucketid = 0;
        for (u32 bi = 0; bi < BUCKET_BYTES; bi++)
          bucketid = (bucketid << 8) | ph[bi];
        bucketid >>= 8 * BUCKET_BYTES - BUCKBITS;
#else
#error not implemented
#endif
        const u32 slot = getslot(0, bucketid);
        if (slot >= NSLOTS) {
          bfull++;
          continue;
        }
        slot0 &s = hta.trees0[0][bucketid][slot];
        s.attr = tree(block * HASHESPERBLAKE + i);
        memcpy(s.hash->bytes+htl.nextbo, ph+WN/8-hashbytes, hashbytes);
      }
    }
  }
  
  void digitodd(const u32 r, const u32 id) {
    htlayout htl(this, r);
    collisiondata cd;
    for (u32 bucketid=id; bucketid < NBUCKETS; bucketid += nthreads) {
      cd.clear();
      slot0 *buck = htl.hta.trees0[(r-1)/2][bucketid]; // optimize by updating previous buck?!
      u32 bsize = getnslots(r-1, bucketid);       // optimize by putting bucketsize with block?!
      for (u32 s1 = 0; s1 < bsize; s1++) {
        const slot0 *pslot1 = buck + s1;          // optimize by updating previous pslot1?!
        if (!cd.addslot(s1, htl.getxhash0(pslot1))) {
          xfull++;
          continue;
        }
        for (; cd.nextcollision(); ) {
          const u32 s0 = cd.slot();
          const slot0 *pslot0 = buck + s0;
          if (htl.equal(pslot0->hash, pslot1->hash)) {
            hfull++;
            continue;
          }
          u32 xorbucketid;
          const uchar *bytes0 = pslot0->hash->bytes, *bytes1 = pslot1->hash->bytes;
#if WN == 200 && BUCKBITS == 12 && RESTBITS == 8
          xorbucketid = (((u32)(bytes0[htl.prevbo+1] ^ bytes1[htl.prevbo+1]) & 0xf) << 8)
                             | (bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2]);
#elif WN == 200 && BUCKBITS == 11 && RESTBITS == 9
          xorbucketid = (((u32)(bytes0[htl.prevbo+1] ^ bytes1[htl.prevbo+1]) & 0xf) << 7)
                             | (bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2]) >> 1;
#elif WN == 144 && BUCKBITS == 20 && RESTBITS == 4
          xorbucketid = ((((u32)(bytes0[htl.prevbo+1] ^ bytes1[htl.prevbo+1]) << 8)
                              | (bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2])) << 4)
                              | (bytes0[htl.prevbo+3] ^ bytes1[htl.prevbo+3]) >> 4;
#elif WN == 96 && BUCKBITS == 12 && RESTBITS == 4
          xorbucketid = ((u32)(bytes0[htl.prevbo+1] ^ bytes1[htl.prevbo+1]) << 4)
                            | (bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2]) >> 4;
#elif WN == 192 && BUCKBITS == 20 && RESTBITS == 4
          xorbucketid = ((((u32)(bytes0[htl.prevbo+1] ^ bytes1[htl.prevbo+1]) << 8)
                              | (bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2])) << 4)
                              | (bytes0[htl.prevbo+3] ^ bytes1[htl.prevbo+3]) >> 4;
#elif (WN == 144 || WN == 192) && BUCKBITS <= 24
          // General form, mirroring the digit0 bucketid extraction: the next
          // bucket index is the top BUCKBITS bits of the XOR, starting one byte
          // past prevbo. Verified bit-for-bit against the specific arms above.
          {
            const u32 XB = (BUCKBITS + 7) / 8 + 1;
            u32 acc = 0;
            for (u32 xi = 0; xi < XB; xi++)
              acc = (acc << 8) | (u32)(bytes0[htl.prevbo+1+xi] ^ bytes1[htl.prevbo+1+xi]);
            xorbucketid = acc >> (8 * XB - BUCKBITS);
          }
#else
#error not implemented
#endif
          const u32 xorslot = getslot(r, xorbucketid);
          if (xorslot >= NSLOTS) {
            bfull++;
            continue;
          }
          slot1 &xs = htl.hta.trees1[r/2][xorbucketid][xorslot];
          xs.attr = tree(bucketid, s0, s1);
          for (u32 i=htl.dunits; i < htl.prevhashunits; i++)
            xs.hash[i-htl.dunits].word = pslot0->hash[i].word ^ pslot1->hash[i].word;
        }
      }
    }
  }
  
  void digiteven(const u32 r, const u32 id) {
    htlayout htl(this, r);
    collisiondata cd;
    for (u32 bucketid=id; bucketid < NBUCKETS; bucketid += nthreads) {
      cd.clear();
      slot1 *buck = htl.hta.trees1[(r-1)/2][bucketid]; // OPTIMIZE BY UPDATING PREVIOUS
      u32 bsize = getnslots(r-1, bucketid);
      for (u32 s1 = 0; s1 < bsize; s1++) {
        const slot1 *pslot1 = buck + s1;          // OPTIMIZE BY UPDATING PREVIOUS
        if (!cd.addslot(s1, htl.getxhash1(pslot1))) {
          xfull++;
          continue;
        }
        for (; cd.nextcollision(); ) {
          const u32 s0 = cd.slot();
          const slot1 *pslot0 = buck + s0;
          if (htl.equal(pslot0->hash, pslot1->hash)) {
            hfull++;
            continue;
          }
          u32 xorbucketid;
          const uchar *bytes0 = pslot0->hash->bytes, *bytes1 = pslot1->hash->bytes;
#if WN == 200 && BUCKBITS == 12 && RESTBITS == 8
          xorbucketid = ((u32)(bytes0[htl.prevbo+1] ^ bytes1[htl.prevbo+1]) << 4)
                            | (bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2]) >> 4;
#elif WN == 200 && BUCKBITS == 11 && RESTBITS == 9
          xorbucketid = ((u32)(bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2]) << 3)
                            | (bytes0[htl.prevbo+3] ^ bytes1[htl.prevbo+3]) >> 5;
#elif WN == 144 && BUCKBITS == 20 && RESTBITS == 4
          xorbucketid = ((((u32)(bytes0[htl.prevbo+1] ^ bytes1[htl.prevbo+1]) << 8)
                              | (bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2])) << 4)
                              | (bytes0[htl.prevbo+3] ^ bytes1[htl.prevbo+3]) >> 4;
#elif WN == 96 && BUCKBITS == 12 && RESTBITS == 4
          xorbucketid = ((u32)(bytes0[htl.prevbo+1] ^ bytes1[htl.prevbo+1]) << 4)
                            | (bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2]) >> 4;
#elif WN == 192 && BUCKBITS == 20 && RESTBITS == 4
          xorbucketid = ((((u32)(bytes0[htl.prevbo+1] ^ bytes1[htl.prevbo+1]) << 8)
                              | (bytes0[htl.prevbo+2] ^ bytes1[htl.prevbo+2])) << 4)
                              | (bytes0[htl.prevbo+3] ^ bytes1[htl.prevbo+3]) >> 4;
#elif (WN == 144 || WN == 192) && BUCKBITS <= 24
          // General form, mirroring the digit0 bucketid extraction: the next
          // bucket index is the top BUCKBITS bits of the XOR, starting one byte
          // past prevbo. Verified bit-for-bit against the specific arms above.
          {
            const u32 XB = (BUCKBITS + 7) / 8 + 1;
            u32 acc = 0;
            for (u32 xi = 0; xi < XB; xi++)
              acc = (acc << 8) | (u32)(bytes0[htl.prevbo+1+xi] ^ bytes1[htl.prevbo+1+xi]);
            xorbucketid = acc >> (8 * XB - BUCKBITS);
          }
#else
#error not implemented
#endif
          const u32 xorslot = getslot(r, xorbucketid);
          if (xorslot >= NSLOTS) {
            bfull++;
            continue;
          }
          slot0 &xs = htl.hta.trees0[r/2][xorbucketid][xorslot];
          xs.attr = tree(bucketid, s0, s1);
          for (u32 i=htl.dunits; i < htl.prevhashunits; i++)
            xs.hash[i-htl.dunits].word = pslot0->hash[i].word ^ pslot1->hash[i].word;
        }
      }
    }
  }
  
  void digitK(const u32 id) {
    collisiondata cd;
    htlayout htl(this, WK);
u32 nc = 0;
    for (u32 bucketid = id; bucketid < NBUCKETS; bucketid += nthreads) {
      cd.clear();
      slot0 *buck = htl.hta.trees0[(WK-1)/2][bucketid];
      u32 bsize = getnslots(WK-1, bucketid);
      for (u32 s1 = 0; s1 < bsize; s1++) {
        const slot0 *pslot1 = buck + s1;
        if (!cd.addslot(s1, htl.getxhash0(pslot1))) // assume WK odd
          continue;
        for (; cd.nextcollision(); ) {
          const u32 s0 = cd.slot();
          if (htl.equal(buck[s0].hash, pslot1->hash))
nc++,       candidate(tree(bucketid, s0, s1));
        }
      }
    }
//printf(" %d candidates ", nc);
  }
};

#ifdef EQUIHASH_TROMP_THREADED
typedef struct {
  u32 id;
  pthread_t thread;
  equi *eq;
} thread_ctx;

void barrier(pthread_barrier_t *barry) {
  const int rc = pthread_barrier_wait(barry);
  if (rc != 0 && rc != PTHREAD_BARRIER_SERIAL_THREAD) {
//    printf("Could not wait on barrier\n");
    pthread_exit(NULL);
  }
}

void *worker(void *vp) {
  thread_ctx *tp = (thread_ctx *)vp;
  equi *eq = tp->eq;

  if (tp->id == 0)
//    printf("Digit 0\n");
  barrier(&eq->barry);
  eq->digit0(tp->id);
  barrier(&eq->barry);
  if (tp->id == 0) {
    eq->xfull = eq->bfull = eq->hfull = 0;
    eq->showbsizes(0);
  }
  barrier(&eq->barry);
  for (u32 r = 1; r < WK; r++) {
    if (tp->id == 0)
//      printf("Digit %d", r);
    barrier(&eq->barry);
    r&1 ? eq->digitodd(r, tp->id) : eq->digiteven(r, tp->id);
    barrier(&eq->barry);
    if (tp->id == 0) {
//      printf(" x%d b%d h%d\n", eq->xfull, eq->bfull, eq->hfull);
      eq->xfull = eq->bfull = eq->hfull = 0;
      eq->showbsizes(r);
    }
    barrier(&eq->barry);
  }
  if (tp->id == 0)
//    printf("Digit %d\n", WK);
  eq->digitK(tp->id);
  barrier(&eq->barry);
  pthread_exit(NULL);
  return 0;
}
#endif // EQUIHASH_TROMP_THREADED
