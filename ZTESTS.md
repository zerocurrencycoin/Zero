# BZTESTS.md

## Overview

This document outlines the structure and scope of the test suites included in the Zcash codebase. Zcash inherits much of Bitcoin Core’s testing architecture but extends it to support its privacy features, zero-knowledge proofs (zk-SNARKs), and shielded transaction protocols (Sprout, Sapling, Orchard).

---

## Test Categories

### ✅ Unit Tests

- **Location**: `src/test/`
- **Framework**: Boost Test
- **Purpose**: Validate logic of core components (e.g., serialization, arithmetic, note handling).
- **Examples**:
  - `coins_tests.cpp` – UTXO set logic
  - `merkletree_tests.cpp` – Incremental Merkle trees
  - `sapling_note_tests.cpp` – Shielded note cryptography
  - `transaction_tests.cpp` – Transaction structure and validity

---

### ✅ Functional Tests

- **Location**: `qa/rpc-tests/`
- **Framework**: Python-based regtest suite
- **Purpose**: End-to-end validation via RPC (wallet, mining, shielding, sending).
- **Examples**:
  - `wallet_sapling.py` – Sapling wallet send/receive
  - `z_sendmany.py` – Batch shielded transfers
  - `shield_coinbase.py` – Shielding of coinbase outputs
  - `mergetoaddress.py` – Consolidation of funds

---

### ✅ Integration / System Tests

- **Location**: `qa/rpc-tests/`
- **Purpose**: Test node interactions across networking, mempool, wallet, and consensus.
- **Examples**:
  - `network_shielded.py` – Shielded transaction propagation
  - `sighash.py` – Signature hashing and replay protection

---

### ✅ Validation Tests

- **Location**: `src/test/`, `qa/rpc-tests/`
- **Purpose**: Verify transaction/block validity and consensus rules.
- **Examples**:
  - `transaction_builder_tests.cpp` – Sapling tx validation
  - `valid_block.py` – Invalid block rejection
  - `joinsplit_tests.cpp` – Sprout JoinSplit integrity

---

### ✅ zk-SNARK & Cryptographic Tests

- **Location**: `src/test/`, `src/zcash/`
- **Purpose**: Test cryptographic components powering privacy features.
- **Examples**:
  - `sapling_note_tests.cpp` – Note encryption/decryption
  - `incrementalmerkletree_tests.cpp` – Tree integrity
  - `joinsplit_tests.cpp` – Zero-knowledge proof generation/verification

---

### ✅ Fuzz Tests

- **Location**: (Limited / Not fully integrated)
- **Purpose**: Randomized input testing for robustness, often manually configured.
- **Note**: Developers may use external tools (e.g., libFuzzer) for zk-SNARK components.

---

### ✅ Benchmark Tests

- **Location**: `src/bench/` or variant
- **Purpose**: Performance analysis of shielded proof generation, note handling, hashing.
- **Examples**:
  - zk-Proof time
  - Note commitment tree updates
  - Sighash computation

---

## Summary Table

| Type               | Location            | Language | Focus                                   |
|--------------------|---------------------|----------|------------------------------------------|
| Unit Tests         | `src/test/`         | C++      | Core logic, Merkle trees, notes          |
| Functional Tests   | `qa/rpc-tests/`     | Python   | RPC wallet/shielding operations          |
| System Tests       | `qa/rpc-tests/`     | Python   | Multi-node, networked integration        |
| Validation Tests   | `src/test/`, `qa/`  | Mixed    | Consensus and tx/block validity          |
| zk/crypto Tests    | `src/zcash/`        | C++      | Sprout/Sapling proof correctness         |
| Fuzz Tests         | (optional/manual)   | C++      | Randomized test of critical functions    |
| Benchmarks         | `src/bench/`        | C++      | Performance of key Zcash operations      |

---

## Notes

- Run functional tests via:  
  ```bash
  ./qa/zcash/full_test_suite.py
  ```
- Unit tests (C++) via:  
  ```bash
  src/test/test_bitcoin
  ```
- Many tests are inherited or adapted from Bitcoin Core but modified to support shielded protocols.
