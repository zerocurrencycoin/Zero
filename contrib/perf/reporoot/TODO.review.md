# `TODO.md`: items to move to the perf tree

Draft for Zero. Compared against Zero `72e421e41` and its working tree. The
earlier proposals are applied: one set of tracking rules, the
`WAL-GETALLDATA` ordering with W5 first, TST-03 and TST-05 closed, TST-09
covered by `DeprecationTest`, and the `getalldata` argument 2 default of 7
days with its release note.

Three Pending items ask a measurement question, not for a code change. Each
belongs in this tree's register, and `TODO.md` keeps none of them:

| Item | Why it is a measurement | Here |
|------|-------------------------|------|
| `WAL-GETALLDATA` W4, IVK decrypt review | Asks whether the decrypt is hot; no measurement exists | A `getalldata` profile on the fat wallet, alongside A9 |
| `OPS-CACHE-METRICS` | Instrumentation to answer a cache-sizing question | `Measures.md` M-CACHE-*; `measure_dbcache_utxo.py` |
| `OPS-DEBUGLOG-TIMING` | Timing extraction from `debug.log` | Done: `extract_measures.py`, `stall_check.py`, `debuglog.py`. Delete the item |
