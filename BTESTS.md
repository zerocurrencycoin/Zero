# BTESTS.md

## Overview

This document summarizes the testing infrastructure in the Bitcoin Core codebase. The project uses a layered approach, including unit, functional, system, validation, fuzz, and benchmark tests. These ensure correctness, stability, and security across all components, from low-level data structures to full-node behavior.

---

## Test Categories

### ✅ Unit Tests

- **Location**: `src/test/`
- **Framework**: Boost Test
- **Purpose**: Validate logic of individual classes/functions in isolation.
- **Examples**:
  - `arith_uint256_tests.cpp` – Large integer math
  - `script_tests.cpp` – Bitcoin Script interpreter
  - `crypto_tests.cpp` – Hashing, signing, and ECDSA logic
  - `validation_tests.cpp` – Mempool policy and consensus rules

---

### ✅ Functional Tests

- **Location**: `test/functional/`
- **Framework**: Python test framework (via RPC and regtest nodes)
- **Purpose**: Simulate real-world usage via the RPC interface and test full-node behavior.
- **Examples**:
  - `wallet_basic.py` – Wallet send/receive
  - `mempool_limit.py` – Mempool size policies
  - `p2p_invalid_tx.py` – Transaction validation and rejection
  - `rpc_blockchain.py` – Blockchain query and RPC correctness

---

### ✅ System / Integration Tests

- **Location**: `test/functional/`
- **Purpose**: Validate coordination between components (e.g., wallet, consensus, networking).
- **Examples**:
  - `feature_block.py` – Mining, block validation
  - `feature_notifications.py` – Block and tx notification hooks
  - `rpc_rawtransaction.py` – Transaction lifecycle via RPC

---

### ✅ Validation Tests

- **Location**: `src/test/`, `test/functional/`
- **Purpose**: Verify strict consensus rules and block/transaction acceptance.
- **Examples**:
  - `p2p_invalid_block.py` – Malformed block rejection
  - `script_tests.cpp` – Edge case script validation
  - `validation_tests.cpp` – Accept/reject logic in mempool and consensus

---

### ✅ Fuzz Tests

- **Location**: `src/test/fuzz/`
- **Tools**: libFuzzer or AFL
- **Purpose**: Feed randomized inputs to critical components to find crashes and vulnerabilities.
- **Examples**:
  - `tx_pool.cpp` – Transaction mempool fuzzing
  - `script_assets.cpp` – Bitcoin Script fuzzing
  - `crypto_hash.cpp` – Fuzz hash function behavior

---

### ✅ Benchmark Tests

- **Location**: `src/bench/`
- **Purpose**: Measure performance of key components.
- **Examples**:
  - `bench/crypto_hash.cpp` – Hashing speed
  - `bench/mempool.cpp` – Mempool update throughput
  - `bench/script.cpp` – Script evaluation performance

---

## Summary Table

| Type               | Location              | Language | Focus                                  |
|--------------------|------------------------|----------|-----------------------------------------|
| Unit Tests         | `src/test/`           | C++      | Core logic, script, mempool, crypto     |
| Functional Tests   | `test/functional/`    | Python   | RPC operations, mining, wallet          |
| System Tests       | `test/functional/`    | Python   | Full-node integration, multi-node       |
| Validation Tests   | `src/test/`, `test/`  | Mixed    | Block/tx acceptance, consensus rules    |
| Fuzz Tests         | `src/test/fuzz/`      | C++      | Randomized crash/edge testing           |
| Benchmarks         | `src/bench/`          | C++      | Performance analysis                    |

---

## Running Tests

### Unit Tests
```bash
src/test/test_bitcoin
```

### Functional Tests
```bash
test/functional/test_runner.py <test_file.py>
```

### Fuzz Tests (example with libFuzzer)
```bash
src/test/fuzz/tx_pool
```

### Benchmarks
```bash
src/bench/bench_bitcoin
```

---

## Notes

- Functional tests use a custom Python framework that spawns and manages `bitcoind` nodes in **regtest** mode.
- Bitcoin Core testing focuses on correctness, determinism, and regression safety. Consensus-critical code is tested heavily both in isolation and through full-node simulations.
