# Equihash known-answer vectors (TST-05 / BENCH-MINE)

Preserved for reuse by `src/test/equihash_tests.cpp` and lab dumps.
Repo-root copies of the same basenames are also accepted (UpdateZero cites
`1927EQ.txt` at repo root).

## Files

| File | Params | Network | What |
|------|--------|---------|------|
| `1927EQ.txt` | (192,7) | mainnet | Genesis header indices (128 `uint32_t`) + `nNonce` / `nSolution_hex`; `roundtrip_ok: true` |
| `1927EQ_h1.hex` | (192,7) | mainnet | Full serialized **height-1** block hex (header+coinbase); hash `083470bd…` |

## Forms

- **Header form (Zero mainnet):** `I = CEquihashInput(header) || nNonce` then `EhIsValidSolution` / `CheckEquihashSolution` (`pow.cpp`).
- **Regtest (48,5):** no separate file; tests use `Params().GenesisBlock()` and optional `BasicSolve`/`OptimisedSolve` on that header state (`solver_testvectors_48_5`).

## Regenerate

```bash
# Genesis index dump (writes path from env):
DUMP_1927EQ=./contrib/perf/kats/1927EQ.txt \
  ./src/test/test_bitcoin --run_test=equihash_tests/dump_mainnet_genesis_192_7_indices

# Height-1 block hex (from a disposable blk*.dat parse or RPC getblock false):
# write raw block bytes as hex to 1927EQ_h1.hex (one line).
```

## Tests that consume these

- `validator_testvectors_192_7` -- indices <-> genesis `nSolution`; corrupt swap fails
- `validator_testvectors_192_7_h1` -- deserialize hex; `CheckEquihashSolution`; index round-trip
- `validator_testvectors_48_5` / `solver_testvectors_48_5` -- regtest genesis (in-tree, no file)

Acceptance: `--run_test=equihash_tests` green; no algorithm changes.

**Queue:** archive **done**. Further adapt/extra validate tests **postponed (G9)**.
Catalogued in Measures §3.2b.
