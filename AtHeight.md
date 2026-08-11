# Height-bounded sync, reindex, and bootstrap

**Status:** findings captured; implementation track **OPS-AT-HEIGHT** postponed (**TODO.md**).  
**Scope:** full node (`zerod`) only. Related: **ZeroStruct** §13.2 (reindex resume), §13.7 (bootstrap).  
**Numbers inventory:** short-snap walls and rates are catalogued in **[Measures.md](Measures.md)** (`M-RX-TINY`, `M-RX-SHORT`, …). **Benchmark / fix plans:** **Perf.md** §0.13; Measures §12.

---

## 1. What Zero has today

| Mechanism | Height-aware? | Role |
|-----------|---------------|------|
| Reindex resume markers `'L'` / `'H'` | `H` = tip after each **completed** `blk` file | Cursor is **file-based** (`L+1`), not "stop/resume at height H" |
| Trimmed `blocks/blk*.dat` (+ `rev*`) | Tip = end of last imported file | Offline partial chain; no peer required (`listen=0`, `maxconnections=0`) |
| `contrib/linearize` `min_height` / `max_height` | Yes | Build height-capped `bootstrap.dat` from a trusted RPC node |
| `bootstrap.dat` auto-import | Implicit (contents) | `ThreadImport` loads then renames to `bootstrap.dat.old` |
| `-loadblock=<file>` | Whole file | Extra blk import on startup |
| Trusted copy of `blocks/` / `chainstate/` / `blocks/index/` | Tip of source | Ops transplant; same `txindex` / insight flags required |

**Absent in Zero:** `-stopatheight` (or equivalent). Daemon does not exit when `chainActive` reaches a configured height.

---

## 2. Lab measurements (mainnet, 2026-07)

### Persistent archives (host; not in git)

**Canonical location only:** `~/Library/Application Support/zero/` (same dir as the full `chainblocks.tgz`). Extract into a dedicated lab datadir from that archive; do not duplicate the tarballs elsewhere.

| Artifact | Path under `Application Support/zero/` | Measured `-disablewallet -reindex` |
|----------|----------------------------------------|-------------------------------------|
| Full blocks+chainstate | `chainblocks.tgz` (~8.1 GiB) | Full tip ~8–10h class |
| Short `blk00000..002` | `chainblocks-short.tgz` (~342 MiB) | Tip **245992**, wall **~274s** |
| Tiny `blk00000..001` | `chainblocks-tiny.tgz` (~228 MiB) | Tip **187417**, wall **~198s** |

Each short/tiny archive embeds offline insight `zero.conf` + `README.txt`. Do **not** commit tarballs into Zero400.

#### Size vs duration (tiny vs short)

Measured `-disablewallet -reindex` on this host (rates = totals / wall seconds).

| | Tiny (2 blk) | Short (3 blk) | `blk00002` only (short − tiny) |
|--|--------------|---------------|--------------------------------|
| Archive | 228 MiB | 342 MiB | 114 MiB |
| Uncompressed `blk*.dat` | 256 MiB | 384 MiB | 128 MiB |
| Tip height | 187417 | 245992 | 58575 |
| Wall (2026-07 manual) | 198 s | 274 s | 76 s |
| **height/s** (2026-07) | **946.6** | **897.8** | **770.7** |
| Wall (2026-08-11b extractor) | **188 s** (`tiny-20260811T085328Z`) | **247 s** (`short-20260811T085646Z`) | **59 s** |
| **height/s** (2026-08-11b) | **996.9** | **995.9** | **992.8** |
| **archive MiB/s** | **1.15** | **1.25** | **1.50** |
| **blk MiB/s** | **1.29** | **1.40** | **1.68** |

Prefer **tiny** for most labs; **short** when a third completed file helps resume tests. Neither predicts tip reindex cost (see longhaul).

Use a disposable lab datadir (not the golden `Application Support/zero` tree) for tiny/short timed validation and for full-chain longhaul / resume.

**Networks:** same code paths on mainnet / testnet / regtest. **Data is not interchangeable** (magic, genesis, blk layout). Regtest remains the fast logic path (mine N blocks); short/tiny mainnet snaps are for mainnet-cost ConnectBlock behavior at low height.

---

## 3. Ecosystem stop-at-height

| Tree (local `ZKs/`) | `-stopatheight` |
|---------------------|-----------------|
| Bitcoin Core | Yes (debug/bench; stop after height) |
| BTCGPU | Yes (Core 0.15-era port) |
| Zero, Pirate, TENT, Zcash (`zcashd`), Hush, Flux | **No** hits in tree search |

Closest height controls elsewhere: Bitcoin **`assumeutxo` / `loadtxoutset`** (UTXO snapshot at a height) -- **not** in Zero. Bitcoin `-reindex-chainstate` also absent here.

---

## 4. Operator patterns without a daemon flag

1. **File truncate** -- keep `blk00000..N` only; `-reindex`; tip = last connectable block in those files.  
2. **Linearize cap** -- `max_height` -> `bootstrap.dat` into empty datadir (no `-reindex`).  
3. **External stop** -- harness watches `getblockcount` / debug.log `UpdateTip` then `zero-cli stop` (lab method).  
4. **Resume after stop** -- same index flags; no `-reindex`; start at `L+1` when valid; if `L+1` past last contiguous blk file, import ends and `'R'` clears (`Reindexing finished`).

Do **not** use sticky `reindex=` in conf. Prefer one-shot CLI `-reindex` and typically `-disablewallet` on explorer hosts.

---

## 4.1 Short snaps and resume -- step-by-step

**Goal:** cheap mainnet ConnectBlock / reindex / resume labs without the full tip. Semantics: **ZeroStruct** §13.2 (`L`/`H`/`R`).

### A. Unpack a short/tiny snap (once per lab dir)

```bash
# Canonical archives (macOS host example)
ZERO_HOME="$HOME/Library/Application Support/zero"
LAB="${LAB:-$TMPDIR/zero-lab-tiny-run}"   # or zero-lab-short-run; never the golden datadir
# Refuse running against the default user datadir
case "$(cd "$LAB" 2>/dev/null && pwd -P || echo "$LAB")" in
  "$ZERO_HOME"|"$HOME/Library/Application Support/Zero"|"$HOME/.zero")
    echo "ERROR: LAB must not be the default zero datadir" >&2; exit 1;;
esac
mkdir -p "$LAB"
# wipe lab only -- never the golden datadir
rm -rf "$LAB"/*
tar -xzf "$ZERO_HOME/chainblocks-tiny.tgz" -C "$LAB"   # or chainblocks-short.tgz
# Expect: blocks/blk*.dat (+ rev*), blocks/index/ or empty index, chainstate/, zero.conf, README.txt
```

Use a **dedicated** `zero.conf` in `$LAB` (snap may ship one). Required ideas:

- Same `txindex` / `insightexplorer` / `experimentalfeatures` as the archive was built with (mismatch forces wipe + full file replay).
- **No** `reindex=1` in conf.
- Lab: `listen=0`, `maxconnections=0`, prefer `disablewallet=1`.

### B. Fresh reindex of the snap (timed baseline)

```bash
cd /path/to/Zero400
./src/zerod -datadir="$LAB" -disablewallet -reindex -daemon
# Watch: grep -E 'Reindex source:|Reindex progress:|UpdateTip:|Reindexing finished' "$LAB/debug.log"
./src/zero-cli -datadir="$LAB" getblockcount   # tiny ~187417; short ~245992
./src/zero-cli -datadir="$LAB" stop
```

Expect log `Reindex source: -reindex argument` (or `DB_FLAG mismatch` if flags disagree). Progress lines after each completed `blk#####.dat`. Finish: `Reindexing finished`; `'R'` cleared; `L`/`H` kept as history.

### C. Resume after interrupt (the resume lab)

Interrupt only after at least one **completed** `blk#####.dat` so `L` advances (tiny: finish `blk00000` then stop in `blk00001`; short: same with three files). Stopping only mid-first-file leaves `L` unset/0 -- restart still looks like a short redo of file 0.

```bash
# 1) Start a fresh reindex
./src/zerod -datadir="$LAB" -disablewallet -reindex -daemon

# 2) Wait until progress shows a completed file, then stop while the next file is in flight
#    Example: lastfile=0 appeared, then UpdateTip still climbing in blk00001
grep -E 'Reindex progress:|UpdateTip:' "$LAB/debug.log" | tail -20
./src/zero-cli -datadir="$LAB" stop

# 3) Restart WITHOUT -reindex and WITHOUT conf reindex=
./src/zerod -datadir="$LAB" -disablewallet -daemon
# First lines of the new session should show resume, not a wipe:
grep -E 'Reindex source:|LoadBlockIndex|Reindex progress:' "$LAB/debug.log" | tail -30
```

Expect:

| Check | Pass criteria |
|-------|----------------|
| Log | `Reindex source: resume (DB_REINDEX_FLAG present)` |
| Start file | Continues at **`L+1`** (redo starts after last **completed** file), not file 0 |
| Finish | Tip matches snap tip; `Reindexing finished` |
| Wrong flags | `DB_FLAG mismatch` -> wipe -> full replay from 0 (not a resume) |

If you pass `-reindex` again on restart, that is a **new wipe**, not a resume.

### D. Which archive for which lab

| Lab | Archive | Why |
|-----|---------|-----|
| Fast ConnectBlock / dbcache / FD | **tiny** (2 blk) | ~198s baseline |
| Resume across a completed file boundary | **short** (3 blk) | Third file gives a clearer `L` step |
| Full tip / longhaul | `chainblocks.tgz` into a dedicated lab datadir | Hours; optional rich monitor outside git |

### E. Common mistakes

1. Sticky `reindex=` in conf -- every restart wipes; loud warn only today.  
2. Changing insight/txindex between runs -- forces wipe.  
3. Expecting resume **at a height** -- cursor is **file** (`L`), `H` is tip after that file.  
4. Running labs on the golden `Application Support/zero` tree -- extract to `$LAB` only.  
5. Using short snaps for regtest logic tests -- use the RPC harness instead.

---

## 5. Tests: done vs appropriate next

| Layer | Status | Notes |
|-------|--------|-------|
| GTest `reindex_tests` | **Shipped** | Markers, `ReindexResumeStartFile` (incl. L+1 past last file), DB_FLAG insight/txindex round-trip (no live wipe) |
| Short-snap timed reindex | **Manual once** | Tip 245992 / ~274s; not CI (archive size) |
| Short-snap resume interrupt | **Appropriate manual** | Stop mid-`blk00001`, restart without `-reindex`, expect startfile redo; use persistent short tgz |
| Conf `reindex=` warn | Covered by **OPS-REINDEX-CONF** | Loud warn shipped; refuse/`-reindexforce` postponed with **OPS-REINDEX** remainder |
| Insight flip wipe | Lab-only | Destructive; short snap cheaper than full chain; do not run on golden |
| `-stopatheight` / height-stop harness | **OPS-AT-HEIGHT** postponed | No daemon flag today |
| Regtest logic | Prefer existing harness | Mine N blocks; do not use mainnet short snap |

**Not appropriate for default CI:** unpacking 342 MiB mainnet blks. Keep short-snap exercises as ops/manual under this doc.

## 6. Possible future work (postponed)

Tracked as **OPS-AT-HEIGHT**. Candidates if ever scheduled (pick one; do not invent all):

- Port Bitcoin-style `-stopatheight` for bench / short reindex runs (debug category).  
- Document-only: canonical short-snap + linearize `max_height` recipes (this file + ZeroStruct §13.7).  
- Optional: log rate / per-blk-file duration (instrumentation), still no height stop.

**Out of scope here:** OPS-REINDEX-SKIP (skip-wallet below H); skip-chain connect below H; assumeutxo.

---

## 7. Cross-links

- Reindex resume / DB_FLAG: **ZeroStruct** §13.1–13.2  
- Bootstrap generate/install: **ZeroStruct** §13.7  
- Fork index defaults: **`~/Work/ZK/ZKs/Comparison.md`** §12.6  
- Insight ops: **`~/Work/ZK/insight/InsightBlock.md`**  
- Tracking: **TODO.md** -- **OPS-AT-HEIGHT** (postponed)  
- Shielded `-reindex` coverage: **WitnessReindex.md** (**TST-WITNESS-REINDEX**); B1 `qa/rpc-tests/reindex_shielded.py` implemented
