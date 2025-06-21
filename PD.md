# Cryptocurrency Budget Systems, SwiftTX, and Masternode Technologies

## Overview

This document contains comprehensive information about budget systems, SwiftTX instant transaction technology, and masternode implementations across Dash, PIVX, and Zero cryptocurrencies.

## Budget Systems

### Dash Budget System

**Current Implementation:**
- **Treasury Allocation:** 10% of block rewards go to treasury system
- **Distribution:** Monthly superblocks distribute treasury funds (every ~30.29 days)
- **Proposal Fee:** 5 DASH fee required to submit proposals
- **Approval Threshold:** >10% of masternode network approval required
- **Voting Formula:** (YES votes - NO votes) > (Total Masternodes / 10)

**Implementation Files:**
- `src/governance/governance.cpp` - Main governance system implementation
- `src/governance/governance-vote.cpp` - Voting mechanism implementation
- `src/governance/governance-object.cpp` - Governance object management
- `src/masternode-budget.cpp` - Legacy budget system (v0.12.0.x)
- `src/masternode-budget.h` - Legacy budget system header
- `/doc/masternode-budget.md` - Budget system documentation

**Features:**
- Separate `proposal-generator` repository for creating governance proposals
- Integration with insight-api for blockchain queries
- External monitoring tools like DashCentral for budget tracking
- Over 758 treasury proposals processed as of recent data

### PIVX Budget System

**Current Implementation:**
- **Treasury Allocation:** 10% of block rewards (0.5 PIV per ~60 seconds)
- **Monthly Budget:** 432,000 PIV per month
- **Proposal Fee:** 50 PIV to submit proposals
- **Approval Threshold:** 10% of masternode votes to pass
- **DAO Structure:** Operates as a Decentralized Autonomous Organization

**Budget Process:**
1. **Prepare:** Create special transaction destroying coins for proposal
2. **Submit:** Propagate transaction to network peers
3. **Voting:** Lobby for masternode votes
4. **Budget Selection:** Achieve 10% masternode network approval
5. **Finalization:** Compile winning proposals into final budget
6. **Payment:** Execute approved budget payments

**Implementation Files:**
- `src/budget/budgetmanager.h` - Budget manager header
- `src/masternode-payments.cpp` - Masternode payment system with budget integration
- `src/masternode-sync.cpp` - Masternode sync with budget synchronization
- `src/spork.cpp` - Contains budget-related spork controls
- `doc/masternode-budget.md` - Budget system documentation

**Governance Evolution:**
- Moving toward "Community Designed Governance"
- Plans to distribute voting power among all PIVX owners, not just masternode operators
- Current system requires 10,000 PIV for masternode operation and voting rights

### Zero Budget System

**Implementation:**
- **Proposal Fee:** 50 COIN (PROPOSAL_FEE_TX = 50 COIN)
- **Budget Fee:** 50 COIN (BUDGET_FEE_TX = 50 COIN)
- **Voting System:** Zeronode-based voting with YES/NO/ABSTAIN options
- **Budget Cycles:** Automatic budget payment cycles with block-based scheduling

**Implementation Files:**
- `/src/zeronode/budget.h` - Budget system class definitions
- `/src/zeronode/budget.cpp` - Main budget system implementation
- `/src/rpc/zeronode-budget.cpp` - RPC interface for budget system

**Key Classes:**
- `CBudgetManager` - Managing all budget proposals
- `CBudgetProposal` and `CFinalizedBudget` - Proposal classes
- `CBudgetVote` and `CFinalizedBudgetVote` - Voting mechanisms
- `CBudgetDB` - Budget database management

## SwiftTX Technology

### Overview

SwiftTX is an instant transaction system that provides near-instantaneous transaction confirmations through masternode consensus. Originally developed by PIVX, inspired by Dash's InstantSend technology.

### Technical Implementation

**Security Model:**
- **Required Signatures:** 6 out of 10 masternode signatures
- **Mathematical Security:** `(1000/2150.0)^10 = 0.00047382219560689856`
- **Attack Resistance:** At 15 signatures, 1/2 of masternode network would need compromise

**How SwiftTX Works:**
1. **Transaction Locking:** Broadcasts "ix" message instead of regular "tx"
2. **Masternode Consensus:** Top-ranked masternodes vote on transaction validity
3. **Signature Collection:** Requires 6 out of 10 masternode signatures for lock completion
4. **Input Locking:** Locks transaction inputs to prevent double-spending
5. **Network Propagation:** Distributes consensus votes via "txlvote" messages

### Implementation Files

**Zero Cryptocurrency (Most Complete):**
- `/src/zeronode/swifttx.h` - SwiftTX class definitions and prototypes
- `/src/zeronode/swifttx.cpp` - Core SwiftTX instant transaction logic
- `/src/zeronode/spork.h` - Network activation control (SPORK_2_SWIFTTX)
- `/src/zeronode/spork.cpp` - Spork system implementation
- `/src/zeronode/zeronode-wallet-interface.h` - Wallet abstraction interface
- `/src/main.cpp` - Contains `ProcessMessageSwiftTX()` call
- `/src/wallet/wallet.cpp` - Wallet integration for SwiftTX transactions
- `/src/net.cpp` - Network layer support for "ix" message propagation

**PIVX (Original Implementation):**
- `src/swifttx.h` and `src/swifttx.cpp` - Core SwiftTX implementation
- `doc/swifttx.md` - SwiftTX documentation

### Technical Constants

```cpp
#define SWIFTTX_SIGNATURES_REQUIRED 6    // Minimum signatures needed
#define SWIFTTX_SIGNATURES_TOTAL 10      // Total masternode participants
```

### Core Classes

- `CConsensusVote` - Individual masternode vote on transaction
- `CTransactionLock` - Container for transaction and its consensus votes
- `CSporkMessage` - Network-wide feature control system

### Protocol Messages

- **"ix"** - Instant transaction request (instead of "tx")
- **"txlvote"** - Masternode consensus vote
- **MSG_TXLOCK_REQUEST** - Transaction lock request inventory type
- **MSG_TXLOCK_VOTE** - Vote message inventory type

## Masternode Technology

### Dash Masternodes

**Requirements:**
- **Collateral:** 1,000 DASH
- **Functions:** InstantSend, governance voting, treasury system
- **Evolution:** Uses Long-Living Masternode Quorums (LLMQ) since v0.14
- **Modern InstantSend:** LLMQ-based technology where transactions are locked within quorums

**Historical Timeline:**
- **2015:** InstantSend introduced as key innovation
- **2017:** Major security exploit discovered, temporary suspension until fixes
- **Dash Core 0.14:** Introduction of LLMQ foundation
- **Dash Core 0.15 (2019):** Complete removal of legacy InstantSend system

### PIVX Masternodes

**Requirements:**
- **Collateral:** 10,000 PIV
- **Functions:** SwiftTX consensus, governance voting, budget management
- **Status:** Active and integral to network security and governance
- **Voting Power:** Currently limited to masternode operators (evolving)

### Zero Zeronodes

**Requirements:**
- **Collateral:** Specific amount (implementation-dependent)
- **Functions:** SwiftTX consensus, budget voting, network security
- **Rewards:** 25% of block rewards go to zeronodes
- **Development Fund:** 7% of block rewards go to development fund

**Implementation Files:**
- `/src/zeronode/zeronode.h` - Zeronode class definitions
- `/src/zeronode/zeronode.cpp` - Zeronode implementation
- `/src/zeronode/zeronodeman.h` - Zeronode manager
- `/src/zeronode/zeronodeman.cpp` - Zeronode manager implementation
- `/src/zeronode/activezeronode.h` - Active zeronode management
- `/src/zeronode/activezeronode.cpp` - Active zeronode implementation
- `/src/zeronode/zeronode-sync.h` - Zeronode synchronization
- `/src/zeronode/zeronode-sync.cpp` - Zeronode sync implementation
- `/src/rpc/zeronode.cpp` - Zeronode RPC interface

## Project Relationships

### PIVX-Dash Relationship

- **PIVX** is a legitimate fork of **Dash v0.12.0.x**
- PIVX openly acknowledges being forked from Dash
- Implements budget systems and SwiftTX legitimately through this fork relationship
- Transparent and acknowledged relationship, not code theft

### Zero Cryptocurrency

- **Origin:** Zcash fork focusing on privacy through zk-SNARKs
- **Launch Date:** February 19, 2017
- **Technology Base:** Uses zk-SNARKs for privacy (Zcash technology)
- **Mining Algorithm:** Custom Equihash 192/7 implementation
- **Privacy Features:** T-addresses (transparent) and Z-addresses (private)
- **Budget/SwiftTX:** Independent implementations inspired by Dash/PIVX concepts

### InstantSend vs SwiftTX

- **InstantSend:** Dash's original instant transaction technology
- **SwiftTX:** PIVX's implementation inspired by InstantSend
- **Evolution:** Dash moved to LLMQ-based InstantSend, PIVX maintained SwiftTX approach
- **Current Status:** Both systems active but use different technical approaches

## Key Technical Differences

### Transaction Speed
- **Dash InstantSend:** LLMQ-based, nearly all transactions automatically receive locks
- **PIVX SwiftTX:** Masternode consensus-based, confirmed within seconds
- **Zero SwiftTX:** 6/10 zeronode signature requirement for instant confirmation

### Governance Models
- **Dash:** Advanced governance object system with multiple proposal types
- **PIVX:** DAO implementation with plans for community-wide voting
- **Zero:** Traditional masternode-based voting with budget proposals

### Security Approaches
- **Dash:** LLMQ provides scalable security through quorum rotation
- **PIVX/Zero:** Fixed masternode consensus with mathematical security guarantees

## Development Status (2024)

### Active Development
- **Dash:** Continuously maintained with regular updates
- **PIVX:** Active development, Core v5.6.0 released in 2024
- **Zero:** Repository available with complete implementation

### Deprecated Features
- **Dash:** Legacy InstantSend completely removed in v0.15
- **PIVX:** `autocombinerewards` RPC deprecated (removal planned for v6.0.0)
- **Zero:** No major deprecations identified

## Documentation and Resources

### Official Repositories
- **Dash:** https://github.com/dashpay/dash
- **PIVX:** https://github.com/PIVX-Project/PIVX
- **Zero:** Multiple repositories (zerodev2/zero, zerocurrencycoin/Zero)

### Key Documentation Files
- `doc/masternode-budget.md` - Budget system documentation
- `doc/swifttx.md` - SwiftTX technical documentation
- `doc/instantsend.md` - InstantSend documentation (Dash)

This document provides a comprehensive overview of the budget systems, instant transaction technologies, and masternode implementations across these three cryptocurrency projects, highlighting their relationships, technical differences, and current development status.