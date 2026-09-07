# Documentation map

What each document is for, what belongs in it, and what does not. This is the
authority on placement: when two documents could hold something, this file
decides.

Each document restates its own rule in a sentence or two of its own prose. That
restatement is a convenience for someone already reading it; **this map is
normative** and the restatement follows it.

## 1. How placement is decided

Three questions, asked in order:

1. **Is it a task, an issue or a state?** Then `docs/TASKS.md`, and nowhere
   else. A task id appears in exactly one file.
2. **Does a subject own it?** Then that subject's document, whatever produced
   the material.
3. **Otherwise:** the document whose inclusion rule below covers it.

**Non-owners cite; they do not restate.** Another document may name a subject
and link to its owner. It may not carry that subject's findings, numbers or
status. A figure lives in `Measures.md` under an `M-*` id and is cited, never
copied.

## 2. The documents

### Findings -- durable, subject-owned

| Document | Answers | In | Out |
|---|---|---|---|
| `Perf.md` | Where does ConnectBlock time go, and what changed it? | CPU breakdown by bucket, disk I/O, the Merkle-root latch, memory profile, `AddToBlockIndex`. Performance aspects of any subject, including Equihash **verification cost during sync** | Task state. Solver internals. Anything about hashing kernels. Wallet witness mechanics |
| `PerfGroth.md` | What does Sapling Groth16 cost, and what would batching buy? | Proof-verification cost, batch-verification headroom, ecosystem status | Non-Groth findings; scheduling |
| `docs/HASHLIBS.md` | Which library computes which hash, and what does the choice cost? | The uniblake/libsodium division, access-pattern ratios, the general shape of the result | Kernel internals (uniblake's). Equihash solving |
| `equ/` | Equihash: which solver, how it works, how it is measured, what to build | **All** solver and Equihash-subject material: internals, lineage, method, plans, solve findings | ConnectBlock-side verification cost, which is a sync finding |
| `docs/SODIUM_SURVEY.md` | Which libsodium, and why that one? | Version survey, peer comparison, the 1.0.22 evidence and decision | Hashing performance, which is `HASHLIBS.md` |
| `docs/CROSSPROJECT.md` | How do two projects record results that can be compared? | Store design across projects, measurement practice, the oracle-provenance rules | Either project's own findings |
| `PerfPlatforms.md`, `PerfTimers.md`, `Stores.md` | Platform, timing and storage specifics | Their named subject | Everything else |
| `docs/WITNESS.md` *(planned)* | What does wallet witness build/rebuild cost? | Witness bottleneck, NOTEIDX, rebuild paths | Sync-side findings that are not wallet-specific |
| `docs/OPS.md` *(planned)* | Reorg, opt-in ship, RPC and load behaviour | That material, from `Perf.md` S0.16 | Measurement method |
| `docs/PRODUCT.md` | What node-code changes did perf work identify? | The evidence for each product item | Their state, which is `TASKS.md` |
| `mine/*.md` | What did this capture show? | Point-in-time capture records, kept as written (`POLICY.md` S5) | Anything durable; update by adding a new note |

### Tasks -- transient

| Document | Answers | In | Out |
|---|---|---|---|
| `docs/TASKS.md` | What is open, blocked, postponed or done? | Every task id and its state, briefly. One line per item, naming its subject and linking to the owner | **Exposition.** No findings, no derivations, no code paths, no numbers beyond an item's own state |

`TASKS.md` may mention a subject; it may not explain one.

### Reference -- durable, mechanical

| Document | Answers | In | Out |
|---|---|---|---|
| `README.md` | How do I invoke this tool? | Per-tool invocation, env vars, per-tool caveats | Findings; task state |
| `docs/HOWTO.md` | How do I take a measurement and read it? | Workflow, the tool index, traps | Per-tool detail (`README.md` has it) |
| `Measures.md` | What is the number, and what is it bound to? | The `M-*` registry, metric vocabulary, comparability rules | Narrative. Every other document cites `M-*` rather than restating |
| `docs/SCHEMA.md`, `recbench/RecBench.md` | What is a row, and how is it stored? | Row shape, identity, store topology | Measurement results |
| `docs/POLICY.md` | What are the rules, and who owns what? | Lab discipline, ownership, retention, ASCII policy | Anything specific to one subject |
| `docs/STRUCTURE.md` | Why is the tree partitioned this way, and what remains? | The concentration measurements, the rules, the repartition sequence | The work itself |
| `docs/MAP.md` | Where does this belong? | This file | Anything else |

## 3. The rules that keep it this way

Each was broken before it was written down.

1. **One subject, one owner.** Measured target: no subject has more than 20%
   of its mentions outside its owner.
2. **One task id, one file.** Two records diverge; one stayed "postponed" for
   days after the question was closed.
3. **Numbers live in `Measures.md`** under an `M-*` id, cited elsewhere.
4. **A document with no inclusion rule accretes.** Every document states one --
   that is what the In/Out columns above are.
5. **Point-in-time notes are archived, not updated** (`POLICY.md` S5).
6. **Superseded material moves to `ZK/OLD/SAVE/<date>-<topic>/`** with a
   manifest entry, never deleted silently.

7. **A rule enforced by a script is not restated in prose.** The script list is
   the authority; documents cite it. `qa/zcash/test_filters.sh` excludes the
   held gtest by name, so no perf document needs to name it -- it was named in
   7 files, which is 7 places to update when the exclusion changes.

## 4. Checking it

Both rules in S3 are mechanically checkable and should become `lint-perf.sh`
checks (`TASKS.md` T4e):

```bash
# subject concentration: share of mentions inside the owner
rg -c 'Equihash|equihash' contrib/perf/equ/ | awk -F: '{n+=$2} END{print n}'

# task ids appearing in more than one file
rg -o '\b(G\d[a-z]?|P\d|TST-\d+|D\d)\b' contrib/perf --no-filename | sort -u
```
