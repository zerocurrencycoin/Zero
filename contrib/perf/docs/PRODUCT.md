# Product changes identified by perf work

Node-code changes this investigation found. They cannot be made from ZeroPerf
(`POLICY.md` S7); each is specified here with its evidence and reviewed in
Zero400.

Items and their state are in `TASKS.md` under Product handoff. This file holds
the evidence: what was found, in which source, and what the alternatives are.

### P1. Proof-verification counters

Sprout JoinSplit verification runs in `CheckBlock`, 67 lines before the first
timer starts; Sapling spend/output verification runs in `ContextualCheckBlock`,
outside `ConnectTip` entirely. The largest post-Sapling cost is therefore
invisible to `-debug=bench`, and a phase summary built from today's counters
would omit **88-91% of post-Sapling cost while appearing complete**.

Placement caution: `ContextualCheckTransaction` is also called from
`AcceptToMemoryPool`, so a naive counter conflates mempool admission with block
validation. Keep them separate -- mempool proof cost is worth knowing on its
own.

**Why it is still open for ZeroPerf:** without it, no phase attribution of a
post-Sapling reindex can be complete, so C2 and C4 both inherit the gap.

### P4. The witness RPC gate is inconsistent, and the family disagrees about it

`rpc/server.cpp` refuses two RPCs while witnesses are unbuilt:

```cpp
if (!initWitnessesBuilt && (pcmd->name == "z_sendmany" || pcmd->name == "getalldata"))
```

**`z_shieldcoinbase` and `z_mergetoaddress` also spend shielded notes** --
`asyncrpcoperation_mergetoaddress.cpp` calls `GetSaplingNoteWitnesses`
directly -- and are not gated. Two RPCs on that path are refused with a clear
error; two others proceed against a cache being rebuilt underneath them.

**What the family does** [Verified, sources under the ZK reference tree]:

| Project | Gate | RPCs gated |
|---------|------|-----------|
| Zcash | none | -- ; `GetSaplingNoteWitnesses` returns **`bool`** and the caller handles a miss |
| Ycash | `YCASH_WR`, the origin of this design | `z_sendmany` only |
| TENT | inherited from Ycash | `z_sendmany` only |
| Pirate, Hush, Zclassic | none | -- |
| **Zero** | inherited, then extended | `z_sendmany` **and `getalldata`** |

So the gate is a Ycash invention, and Zero is the only fork that has widened
it. Nobody gates the shield/merge path, which suggests the omission is
inherited rather than reasoned.

**The upstream alternative is structural.** Zcash commit `99e41f36c`,
"Gracefully handle Get(Sprout/Sapling)NoteWitnesses failure" (2022-05), changed
both getters from `void` to `bool` and made every caller raise
`RPC_WALLET_ERROR "Insufficient Sapling witnesses."` on false. Zero, Hush and
Zclassic still carry the `void` shape, which cannot report a miss -- which is
why a gate was needed to stand in for it.

Both versions take `LOCK(cs_wallet)`; the locking is identical and is not the
difference.

**Zero's 8 call sites, audited.** The return value is unavailable, so each
caller must inspect the per-note `boost::optional`. Most do:

| Site | Handling |
|------|----------|
| `sendmany.cpp:425` (Sapling) | `if (!witnesses[i]) throw` -- guarded |
| `mergetoaddress.cpp:323` (Sapling) | `if (!witnesses[i]) throw` -- guarded |
| `saplingconsolidation.cpp:157` (Sapling) | `if (!witnesses[i]) break` + log -- guarded |
| `sendmany.cpp:1024`, `mergetoaddress.cpp:746` (Sprout) | passed to `perform_joinsplit`, which throws on an empty optional -- guarded, indirectly |
| `sendmany.cpp:546`, `mergetoaddress.cpp:446` (Sprout) | stored in a map, validated at use -- guarded, indirectly |
| **`saplingmigration.cpp:143` (Sprout)** | **`vInputWitnesses[0].get()` with no check** |

**The risk is one site, and it is not hypothetical.** `boost::optional::get()`
on an empty optional is undefined behaviour, not an exception -- so a Sprout
note whose witness is missing crashes the node rather than failing the
migration. Sapling migration runs unattended on a timer, so this is the one
path where nobody is watching. The Zcash fix changed exactly this file among
its six.

**How Zcash handles its own returns**, all three production sites checked:

Three sites already handle a false return: `wallet_tx_builder.cpp:966`
(Sapling) and `:1079` (Sprout) return
`TransactionBuilderResult("Insufficient ... witnesses.")`, and
`asyncrpcoperation_saplingmigration.cpp:151` throws
`JSONRPCError(RPC_WALLET_ERROR, ...)`.

The migration site then calls `vInputWitnesses[0].value()` -- *after* the
guard. That is the same call Zero makes at its line 143 with no guard in
front of it. Zcash also consolidated eight call sites into three by routing
spends through `wallet_tx_builder`, so there are fewer places to get it wrong.

**The family, and when each last moved** [Verified, sources under the ZK
reference tree]:

| Project | Signature | Migration site | File last touched |
|---------|-----------|----------------|-------------------|
| **Zcash** | `bool`, both getters | guarded, then `.value()` | fix 2022-05-05, shipped v5.0.0 |
| **Zero** | `void` | **`.get()`, unguarded** | 2019-12-06, "Pull up to Zcash 2.0.6" |
| **TENT** | `void` | **`.get()`, unguarded** | 2020-08-01 |
| **Ycash** | `void` | **`.value()`, unguarded** | v4.4 line; local clone is a squashed snapshot, so no per-file dates |
| Pirate, Hush, Zclassic | `void` | no `saplingmigration.cpp` | -- |

The unguarded call is **inherited from pre-2022 Zcash**, not a Zero mistake --
TENT and Ycash carry it identically, from the same ancestor. Ycash is on the
Zcash 4.x line (`CLIENT_VERSION 4.4`), so it predates the fix rather than
having declined it; the local clone is a single squashed import, so its file
dates say when the snapshot was taken, not when the code was written. Only
Zcash's own date is authoritative here.

Pirate, Hush and Zclassic dropped Sprout migration entirely, which removes the
worst site without addressing the pattern.

**What can be borrowed, and what cannot.**

Zcash's three sites are the product of two separate changes. The signature fix
(`99e41f36c`, 2022-05-05) is small -- in `wallet.cpp` it is only
`void` -> `bool`, four `assert(it != end)` turned into `if (it == end) return
false`, and two `return true`. **That part does not port**: those asserts guard
a confirmations walk (`for (int i = 1; i < confirmations; i++) ++it;`) that
Zero does not have. Zero takes `witnesses.front()` and has no `confirmations`
parameter, so it has no `it == end` case. Its only assert is the anchor
comparison, which Zcash kept.

The consolidation to three sites is a **different, later change**:
`wallet_tx_builder.cpp` (`78e76f133`, 2022-05-24), ~1,600 lines introducing a
two-stage build with `TransactionBuilderResult` and `InsufficientFundsError`,
and 72 Orchard references. Zero has no Orchard. **Not liftable**, and the site
count is a consequence of that architecture, not a thing to copy on its own.

**What is immediately available** is neither: add the guard Zero is missing at
`saplingmigration.cpp:143`. Zcash's own migration site does exactly this, and
it is two lines --

```cpp
if (!vInputWitnesses[0]) {
    throw JSONRPCError(RPC_WALLET_ERROR, "Insufficient Sprout witnesses.");
}
```

-- which turns undefined behaviour into the error every other Zero call site
already raises. Changing the signature can follow later, or not at all; the
crash does not wait for it.

**On the throw.** Zcash's migration site throws where its two builder sites
return an error value, because it runs inside an async operation with no result
channel to return through. Zero is in the same position -- `saplingmigration`
is an `AsyncRPCOperation` -- and its sibling sites already throw
`JSONRPCError(RPC_WALLET_ERROR, "Missing witness for Sapling note")` from
`sendmany.cpp:430` and `mergetoaddress.cpp:328`. So throwing is both what
upstream does here and what this tree already does everywhere else; the one
unguarded site is the outlier, not the pattern.

**Getter internals across the family** [Verified, sources under the ZK
reference tree]. The confirmations walk is Zcash's alone:

| Chain | Witness selection | Guard | Anchor assert |
|---|---|---|---|
| Zcash | `cbegin()` + walk `confirmations` steps | `if (it == end) return false` x2 | kept |
| Zero, Ycash, TENT, Zclassic, Hush, Pirate | `witnesses.front()` | none -- `.front()` cannot fail once `size() > 0` is checked | kept |

So the clones are not missing a guard here: with `.front()` behind a
`size() > 0` test there is nothing to guard. The `it == end` returns exist
because Zcash walks to a *chosen depth* and can run off the end. That walk came
from `90fc0eaa4` (2022-05-04, "Add anchor depth parameter to Get*NoteWitnesses"),
one day before the graceful-handling commit -- the two are one piece of work.

**Zero still carries the TODO that change closed.** At
`saplingmigration.cpp:137-139`:

```
// Each migration transaction SHOULD specify an anchor at height N-10
// TODO: the above functionality (in comment) is not implemented in zcashd
```

Zcash implemented it and rewrote the comment to say so. Every clone kept the
TODO. The anchor-depth parameter is therefore the *substance* of the upstream
change; `bool` is the mechanism it needed.

**`std::optional` vs `boost::optional`.** Two chains migrated, four did not:

| Chain | `wallet.h` | Migration |
|---|---|---|
| Zcash | 83 `std::`, 0 `boost::` | scripted-diff `d8d091895`, 2020-10-21, 55 files |
| Ycash | 25 `std::` | inherited before forking |
| **Zero** | **21 `boost::`, 0 `std::`** | -- |
| TENT, Zclassic, Hush, Pirate | `boost::` only | -- |

Zero mandates **C++17** already (`configure.ac:65`,
`AX_CXX_COMPILE_STDCXX([17], [noext], [mandatory])`), so `std::optional` is
available today; nothing blocks this but the work.

Zcash's migration is a published, reproducible recipe -- six `sed` lines in the
commit message of `d8d091895`. Zero has **186 `boost::optional` references
across 44 files**.

**The recipe is incomplete for Zero, in a useful way.** `std::optional` has no
`.get()`; the sed does not rewrite it, so every `optional.get()` becomes a
**compile error**, not silent breakage:

```
error: no member named 'get' in 'std::optional<int>'
```

Zero has 164 `.get()` call sites to classify (most are `unique_ptr`/`shared_ptr`
and unaffected). Among them is `saplingmigration.cpp:143` -- the unguarded
dereference in this item. A boost-to-std migration would force that line to be
looked at, which is the strongest argument for doing it: the type system
surfaces the exact defect that has gone unnoticed in three chains since 2019.

**Two risks in the wider pattern:**

1. **Silence is indistinguishable from success.** A `void` getter that finds no
   witness returns having filled nothing; a caller that forgets the per-note
   check proceeds on garbage. The compiler cannot help -- there is no return
   value to ignore. With `bool` and `[[nodiscard]]`, it could.
2. **The anchor assert.** When two notes disagree,
   `assert(*rt == witnesses[i]->root())` aborts the node. Current Zcash still
   carries it, so it is inherited rather than a Zero defect -- but a crash is a
   crash, and it is the same assertion that fails in the held
   `WalletTests.CachedWitnessesCleanIndex` gtest.

Both still `assert(*rt == witnesses[i]->root())` on an anchor mismatch,
including current Zcash, so that abort is inherited and not a Zero defect.

**Recommendation, in order.** Four separable changes; each stands alone and
none blocks the next.

| # | Change | Effort | Why now |
|---|--------|--------|---------|
| 1 | Guard `saplingmigration.cpp:143` | 2 lines | **Landed.** Throws `RPC_WALLET_ERROR "Insufficient Sprout witnesses."`, matching Zcash's own migration site and this tree's six other call sites. Also guards `empty()`, which the upstream shape does not need |
| 2 | Widen the RPC gate to `z_shieldcoinbase` and `z_mergetoaddress` | S | **Landed.** Both now refused while witnesses are unbuilt |
| 3 | `boost::optional` -> `std::optional` | M | **P5** |
| 4 | Anchor-depth parameter + `bool` getters | L | **P6**, needs P5 |

Steps 1 and 2 landed and are this item. Steps 3 and 4 are larger than this
item's scope and are tracked as **P5** and **P6**; P6 subsumes step 2 by making
the gate unnecessary.

**Not recommended: porting `wallet_tx_builder.cpp`.** ~1,600 lines, 72 Orchard
references, and Zero has no Orchard. The three-call-site count is a property of
that architecture, not a target.

**The two directions previously stated**, retained for the record:

1. **Widen the gate** -- add `z_shieldcoinbase` and `z_mergetoaddress`.
   Smallest change, keeps the current design, still a name list that the next
   spend RPC will be omitted from.
2. **Adopt the upstream shape** -- make `GetSaplingNoteWitnesses` return
   `bool`, have callers handle a miss, and retire the `initWitnessesBuilt`
   gate. Larger, and it removes the class of bug rather than one instance.

(2) is what Zcash concluded after shipping (1)'s equivalent. Evidence for the
race this gate causes in tests: `qa/rpc-tests/wallet_witness_defer.py`
`z_sendmany_when_ready`.

**Tests pinning steps 1-2.** Each was verified to fail with the fix reverted,
not merely to pass with it:

Pinned by three tests: `WalletTests.GetSproutNoteWitnessesLeavesUnknownNotesUnset`
and its Sapling counterpart (an unknown note leaves its witness unset), and
`rpc_zero_exclusive_tests/rpc_getalldata_s5_witness_gate`, extended to
`z_shieldcoinbase` and `z_mergetoaddress`.

`sprout_sapling_migration.py` exercises the guarded path but is Tier B fail:
`get_coinbase_address` needs 720 blocks for a mature coinbase and the harness
generates 101. Verified to fail identically with the changes stashed, so it is
environmental and pre-existing.

**Ecosystem comparison** (project-neutral, no plan): `ZKs/Comparison.md` §5.7.

**Related, and cheap: the redundant coinbase filter.** `find_utxos`
(`asyncrpcoperation_sendmany.cpp`) passes `fAcceptCoinbase` to
`AvailableCoins` and then re-tests `isCoinbase && fAcceptCoinbase==false` in
the loop over the result. The second test is unreachable -- the first already
removed every coinbase output. Behaviour is unaffected; it is inherited, and
Zclassic, Hush, TENT and Pirate all carry it identically
(`ZKs/Comparison.md` S5.7).

**Ycash shows the fix worth copying.** It moved the loop's filters into the
callee -- `AvailableCoins` gained `fOnlySpendable`, `nMinDepth` and
`onlyFilterByDests` -- so the follow-up loop, and the redundant check with it,
disappears. Its call site also annotates every positional argument:

```
            fAcceptCoinbase,    // fIncludeCoinBase
```

That matters here: `fIncludeCoinBase` is the fifth of seven parameters, four of
them consecutive defaulted bools and pointers.

**Call sites, counted comparably** [Verified; an earlier count of 17 for Zero
was wrong -- it swept in the `zeronode` layer's own one-argument
`AvailableCoins(vCoins)`, which is a different method on a different
interface, plus its mock and its header comments]:

| Chain | Real `CWallet::AvailableCoins` calls | Where the extras are |
|---|--:|---|
| Zcash | 5 | -- |
| Ycash, Zclassic | 7 | -- |
| **Zero** | **9** | 4 in `rpcwallet`, 3 in `wallet.cpp`, 1 sendmany, 1 zeronode bridge |
| Hush | 11 | CryptoConditions (`cc/CCtx.cpp`) |
| TENT | 14 | darksend/obfuscation denominations in `wallet.cpp` |
| Pirate | 15 | CryptoConditions and Komodo interop |

Zero is mid-range, not the outlier. The larger counts track added subsystems
rather than sprawl: TENT's are denomination selection, Pirate's and Hush's are
CryptoConditions.

Two of Zero's calls (`rpcwallet.cpp:2429`, `3270` -- `listunspent` and
`z_listaddresses`, both reporting RPCs) omit the flag and take the `true`
default correctly but silently. Inserting a parameter before it would change
both with no compiler warning.

**"Zcash deleted the caller" was imprecise.** `asyncrpcoperation_sendmany.cpp`
still exists there; it is **215 lines against Zero's 1270**, and contains no
`find_utxos` and no `AvailableCoins` at all. The UTXO selection moved to
`wallet_tx_builder`, so all 5 remaining calls are in `rpcwallet.cpp` and
`wallet.cpp`. The async spend operations call it nowhere.

**Kanban: ToDo. Effort S (option 1) / M (option 2).** The unguarded
`saplingmigration.cpp:143` is separable from both and is the only part with a
crash behind it. The annotation of positional arguments is separable again, and
smaller still.

### P5. Migrate `boost::optional` to `std::optional`

Zcash did this in `d8d091895` (2020-10-21) as a **scripted-diff**: the six
`sed` lines are in its commit message and are reproducible. Zero already
mandates C++17 (`configure.ac:65`), so nothing blocks it but the work.

**Scope** [Measured, this tree]:

| Symbol | Count | Files |
|--------|------:|------:|
| `boost::optional` | 190 | 44 |
| `boost::none` | 119 | -- |
| `is_initialized()` | 3 | -- |
| `.get()` needing classification | 165 | -- |

The first three are mechanical. The `.get()` calls are not, and that is the
point: **`std::optional` has no `.get()`**, so the sed leaves each one as a
compile error rather than converting it silently. Most of the 165 are
`unique_ptr`/`shared_ptr` and unaffected; the rest have to be read and turned
into `.value()`, `*opt`, or a guard. Verified: `o.get()` on a
`std::optional<int>` is `error: no member named 'get'`.

**Why it is worth doing beyond tidiness.** `boost::optional::get()` on an unset
optional is undefined behaviour; `std::optional::value()` throws
`bad_optional_access`. The migration converts a class of silent corruption into
either a compile error (at migration time) or a catchable exception (at run
time). P4 step 1 fixed one instance of that class by hand; this finds the rest
by construction.

**Do it as its own commit**, touching nothing else, so the diff stays reviewable
as a mechanical transform plus a list of judged `.get()` sites.

**Sequencing: before P6.** Zcash's `bool` getters and its `std::optional`
migration are entangled in its own history; doing P6 on `boost::optional`
reproduces a shape upstream has already left.

**Kanban: ToDo. Effort M.** Product change, Zero400 review.

### P6. Anchor depth for shielded spends

Zero picks the witness at `.front()` -- the most recent -- so a shielded spend
anchors at the chain tip. `asyncrpcoperation_saplingmigration.cpp:137-139`
still carries the inherited comment saying it should not:

```
// Each migration transaction SHOULD specify an anchor at height N-10
// for each Sprout JoinSplit description
// TODO: the above functionality (in comment) is not implemented in zcashd
```

Zcash implemented it in `90fc0eaa4` (2022-05-04, "Add anchor depth parameter to
Get*NoteWitnesses") and rewrote the comment to describe the behaviour. Every
surveyed clone kept the TODO (`ZKs/Comparison.md` S5.7).

**What it involves:**

| Piece | Detail |
|-------|--------|
| Parameter | `unsigned int confirmations` on both `GetS*NoteWitnesses` |
| Walk | `cbegin()` then advance `confirmations - 1` steps instead of `.front()` |
| Failure | `if (it == end) return false` -- which is why the getters become `bool` |
| Config | Zcash exposes `-anchorconfirmations`, 1-100, `DEFAULT_ANCHOR_CONFIRMATIONS = 3` |

**Across the family** [Verified, `ZKs/Comparison.md` S5.7]: only Zcash has an
anchor-depth constant. Zero, Ycash, TENT, Zclassic, Hush and Pirate all select
`witnesses.front()`, and all `push_front` per block, so **every clone anchors
at the tip** -- depth 1 in Zcash's terms. The N-10 in the inherited comment was
never implemented anywhere; Zcash implemented the mechanism and chose **3**.

The witnesses a depth parameter would select are already retained --
`WITNESS_CACHE_SIZE = MAX_REORG_LENGTH + 1`, and `MAX_REORG_LENGTH = 99`
(`main.h:70`). Only the selection is missing, not the data.

**Why it matters beyond closing a TODO.** Anchoring at the tip means a spend's
anchor can be reorged away between construction and mining, which is what a
depth parameter exists to prevent. This is a correctness property, not a
cleanup, and it is independent of the crash P4 step 1 fixed.

**It subsumes P4 step 2.** With `bool` getters a miss is reportable at the call
site, so the `initWitnessesBuilt` RPC gate -- and the question of which RPC
names belong in it -- stops being necessary. Zcash has no such gate for exactly
this reason.

**Consensus check required before starting.** Changing which anchor a
transaction commits to changes the transaction. Whether that is safe for Zero
depends on its own activation history and is not answered by upstream's
choice.

**Kanban: ToDo. Effort L.** Product change, Zero400 review. Needs P5 first.

### P7. Coin-selection call clarity: adopt Ycash's shape, not TENT's

**Checked TENT first and it has nothing to take here.** Its
`CWallet::AvailableCoins` signature is byte-identical to Zero's, its
`find_utxos` carries the same redundant `isCoinbase && fAcceptCoinbase==false`
check, and it annotates no call site. Its extra call sites are darksend
denomination selection (`ONLY_DENOMINATED`,
`ONLY_NONDENOMINATED_NOT10000IFMN`) -- a subsystem Zero does not have, not a
better interface. TENT is worth reading for zeronode/masternode lineage
(`TENTZero.md`); for this it is a peer, not a source.

**The improvement is Ycash's**, and it is two separable pieces
(`ZKs/Comparison.md` S5.7):

| # | Change | Effort | Effect |
|---|--------|--------|--------|
| a | Annotate every positional argument at the call site | S | `fIncludeCoinBase` is the 5th of 7 parameters, 4 of them consecutive defaulted bools and pointers. A positional call cannot be read without counting |
| b | Move `find_utxos`'s post-filters into `AvailableCoins` -- spendability, min depth, destination set | M | The follow-up loop disappears, and the redundant coinbase check with it |

(a) is a comment change at 9 call sites, no behaviour, and it is the cheapest
item in this whole area. (b) is a real refactor but a bounded one: Ycash's
`AvailableCoins` grew `fOnlySpendable`, `nMinDepth` and `onlyFilterByDests`,
and its `find_utxos` became a single call plus a sort.

**Zcash solved the same problem by relocation**, moving selection into
`wallet_tx_builder` so no async operation calls `AvailableCoins` at all -- its
`asyncrpcoperation_sendmany.cpp` is 215 lines against Zero's 1270. That path is
not open here: the builder is heavily Orchard-dependent (P4).

**Kanban: ToDo. Effort S-M.** Product change, Zero400 review. (a) is
independent of everything else in P4-P6.

### P2. NOTEIDX staleness

The note index is invalidated more often than note membership changes. Defect,
cost and call sites: `FINDINGS.md` S3.1. Wallet code, so the fix needs product
review.

---

