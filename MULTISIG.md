# Zero Cryptocurrency Multisig Implementation Guide

## Overview

Zero cryptocurrency implements comprehensive multisig (multi-signature) functionality that is fully compatible with Bitcoin's proven multisig system. This allows multiple parties to control funds together, requiring a specified number of signatures to authorize transactions.

## Core Implementation

### Script Types Supported

1. **Bare Multisig**: Direct multisig scripts (`OP_M pubkey1 pubkey2 ... pubkeyN OP_N OP_CHECKMULTISIG`)
2. **P2SH Multisig**: Pay-to-Script-Hash wrapped multisig (recommended for privacy and lower fees)

### Key Limits and Constraints

- **Standard Multisig**: Up to 3-of-N for network relay (standardness rules)
- **RPC Limits**: Maximum 16 keys in `createmultisig` and `addmultisigaddress` commands
- **Protocol Maximum**: 20 keys/signatures maximum in `OP_CHECKMULTISIG`
- **Minimum Required**: At least 1 signature required, up to total number of keys

## RPC Commands

### 1. `createmultisig nrequired ["key",...]`

Creates a multisig address without adding it to the wallet.

**Parameters:**
- `nrequired`: Number of signatures required (1 to total keys)
- `keys`: Array of Zero addresses or hex-encoded public keys

**Returns:**
```json
{
  "address": "t3abc123...",     // The P2SH multisig address
  "redeemScript": "5321..."     // Hex-encoded redeem script
}
```

**Example:**
```bash
# Create 2-of-3 multisig
zero-cli createmultisig 2 '["t1abc123...", "t1def456...", "t1ghi789..."]'
```

### 2. `addmultisigaddress nrequired ["key",...] [account]`

Creates a multisig address and adds it to the wallet for tracking.

**Parameters:**
- `nrequired`: Number of signatures required
- `keys`: Array of Zero addresses or hex-encoded public keys  
- `account`: Optional account name (must be empty string `""` if provided)

**Returns:**
```
"t3abc123..."  // The P2SH multisig address
```

**Example:**
```bash
# Create and track 2-of-3 multisig in wallet
zero-cli addmultisigaddress 2 '["t1abc123...", "t1def456...", "t1ghi789..."]'
```

## Wallet Integration

### Address Management

- **Script Storage**: Multisig redeem scripts stored in wallet's script store
- **Address Book**: Multisig addresses added to address book for tracking
- **Ownership Model**: Wallet considers multisig "spendable" only if it owns ALL required private keys
- **Watch-Only Support**: Can track multisig addresses without owning all keys

### Balance Tracking

```bash
# Check balance including multisig addresses
zero-cli getbalance

# List multisig addresses
zero-cli listaddressgroupings
```

## Transaction Creation and Signing

### Complete Workflow

#### Step 1: Create Multisig Address
```bash
# Generate 2-of-3 multisig
RESULT=$(zero-cli createmultisig 2 '["pubkey1", "pubkey2", "pubkey3"]')
ADDRESS=$(echo $RESULT | jq -r '.address')
REDEEMSCRIPT=$(echo $RESULT | jq -r '.redeemScript')
```

#### Step 2: Fund the Multisig Address
```bash
# Send funds to the multisig address
zero-cli sendtoaddress $ADDRESS 10.0
```

#### Step 3: Create Spending Transaction
```bash
# Get UTXO to spend
UTXO=$(zero-cli listunspent 1 999999 "[\"$ADDRESS\"]")
TXID=$(echo $UTXO | jq -r '.[0].txid')
VOUT=$(echo $UTXO | jq -r '.[0].vout')
AMOUNT=$(echo $UTXO | jq -r '.[0].amount')

# Create raw transaction
RAWTX=$(zero-cli createrawtransaction \
  "[{\"txid\":\"$TXID\", \"vout\":$VOUT}]" \
  "{\"t1destination...\": 9.999}")
```

#### Step 4: Sign Transaction (Partial)
```bash
# First signature (requires redeemScript)
PARTIALLY_SIGNED=$(zero-cli signrawtransaction $RAWTX \
  "[{\"txid\":\"$TXID\", \"vout\":$VOUT, \"scriptPubKey\":\"...\", \"redeemScript\":\"$REDEEMSCRIPT\"}]")

PARTIAL_TX=$(echo $PARTIALLY_SIGNED | jq -r '.hex')
```

#### Step 5: Complete Signing
```bash
# Second signature (on different wallet with second key)
FULLY_SIGNED=$(zero-cli signrawtransaction $PARTIAL_TX \
  "[{\"txid\":\"$TXID\", \"vout\":$VOUT, \"scriptPubKey\":\"...\", \"redeemScript\":\"$REDEEMSCRIPT\"}]")

FINAL_TX=$(echo $FULLY_SIGNED | jq -r '.hex')
COMPLETE=$(echo $FULLY_SIGNED | jq -r '.complete')
```

#### Step 6: Broadcast Transaction
```bash
# Only broadcast if signing is complete
if [ "$COMPLETE" = "true" ]; then
  zero-cli sendrawtransaction $FINAL_TX
else
  echo "Transaction needs more signatures"
fi
```

## Security Features

### Script Validation
- **Strict DER Encoding**: Enforces proper signature format
- **Low S Values**: Prevents signature malleability attacks
- **Null Dummy**: Enforces dummy stack element in CHECKMULTISIG

### Key Management
- **Conservative Ownership**: Wallet only spends if it owns all required keys
- **Public Key Validation**: Validates all public keys during script creation
- **Address Validation**: Accepts both addresses and raw public keys

## Common Use Cases

### 1. Escrow Services (2-of-3)
**Scenario**: Buyer, seller, and trusted arbitrator
```bash
# Create escrow multisig
zero-cli createmultisig 2 '["buyer_pubkey", "seller_pubkey", "arbitrator_pubkey"]'
```

### 2. Corporate Treasury (3-of-5)
**Scenario**: Requires 3 executives out of 5 to authorize payments
```bash
# Create corporate multisig
zero-cli createmultisig 3 '["exec1_pubkey", "exec2_pubkey", "exec3_pubkey", "exec4_pubkey", "exec5_pubkey"]'
```

### 3. Personal Cold Storage (2-of-3)
**Scenario**: Hardware wallet, mobile wallet, paper backup
```bash
# Create personal security multisig
zero-cli createmultisig 2 '["hardware_pubkey", "mobile_pubkey", "paper_pubkey"]'
```

### 4. Joint Account (2-of-2)
**Scenario**: Both parties must agree to spend
```bash
# Create joint account
zero-cli createmultisig 2 '["party1_pubkey", "party2_pubkey"]'
```

## Best Practices

### Security Recommendations

1. **Use P2SH**: Always prefer P2SH-wrapped multisig for privacy and lower fees
2. **Backup Redeem Scripts**: Store redeem scripts securely - they're required for spending
3. **Test on Testnet**: Validate your multisig setup on testnet before mainnet use
4. **Hardware Wallets**: Use hardware wallets for key storage when possible
5. **Key Distribution**: Store keys in different physical locations/devices

### Operational Guidelines

1. **Verify Signatures**: Always verify all signatures before broadcasting
2. **Check Completeness**: Ensure transaction is fully signed before broadcast
3. **Fee Consideration**: Account for higher fees due to larger transaction sizes
4. **Documentation**: Document the purpose and signatories for each multisig

### Common Pitfalls to Avoid

1. **Lost Redeem Scripts**: Without the redeem script, funds are unrecoverable
2. **Insufficient Signatures**: Ensure you have access to enough keys
3. **Key Reuse**: Don't reuse the same keys across multiple multisig addresses
4. **Network Mismatch**: Ensure all keys are for the same network (mainnet/testnet)

## Technical Implementation Details

### Script Creation
```cpp
// C++ implementation
CScript GetScriptForMultisig(int nRequired, const std::vector<CPubKey>& keys)
{
    CScript result;
    result << CScript::EncodeOP_N(nRequired);
    for (const CPubKey& key : keys) {
        result << ToByteVector(key);
    }
    result << CScript::EncodeOP_N(keys.size()) << OP_CHECKMULTISIG;
    return result;
}
```

### P2SH Wrapping
```cpp
// Create P2SH address for multisig
CScript redeemScript = GetScriptForMultisig(nRequired, pubkeys);
CScriptID scriptID(redeemScript);
CTxDestination address = scriptID;
```

### Signature Verification
```cpp
// OP_CHECKMULTISIG implementation includes:
// - Public key and signature validation
// - Ordered key matching
// - Proper stack manipulation
// - Off-by-one bug workaround (dummy element)
```

## Testing

Zero includes comprehensive multisig tests:

- **Unit Tests**: `src/test/multisig_tests.cpp`
  - Tests 1-of-2, 2-of-2, and 2-of-3 scenarios
  - Validates script standardness
  - Tests signing and verification

- **RPC Tests**: `qa/rpc-tests/rawtransactions.py`
  - Tests multisig creation and spending
  - Validates partial signing workflows

- **Integration Tests**: Full end-to-end multisig scenarios

## Limitations and Considerations

### Network Relay Limits
- Only 1-of-N, 2-of-N, and 3-of-N multisig considered "standard"
- Larger multisig scripts may not propagate on the network
- Use P2SH to work around standardness restrictions

### Transaction Size
- Multisig transactions are larger than single-sig
- Higher fees required due to increased size
- Consider UTXO consolidation strategies

### Wallet Compatibility
- Ensure all participants use compatible wallet software
- Coordinate on transaction format and signing process
- Test interoperability before production use

## Zero-Specific Features

### Address Format
- Uses Zero's transparent address format (starts with 't1')
- Compatible with Zero's network protocol and consensus rules
- Supports all Zero network upgrades (Overwinter, Sapling, etc.)

### Integration with Zero Features
- Works with Zero's privacy features (can mix with shielded transactions)
- Compatible with Zero's mining and consensus mechanisms
- Integrated with Zero's RPC interface and wallet functionality

---

*This guide covers Zero's multisig implementation based on the current codebase. Always test on testnet before using on mainnet, and ensure you understand the security implications of multisig setups.*