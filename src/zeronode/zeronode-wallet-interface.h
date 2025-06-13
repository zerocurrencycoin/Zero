// Copyright (c) 2017-2018 The Zero developers
// Distributed under the MIT/X11 software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

#ifndef ZERONODE_WALLET_INTERFACE_H
#define ZERONODE_WALLET_INTERFACE_H

#include "amount.h"
#include "key.h"
#include "primitives/transaction.h"
#include "sync.h"

#include <vector>

class COutPoint;
class CWalletTx;

#ifdef ENABLE_WALLET
#include "wallet/wallet.h"
#else
// Forward declaration for wallet-disabled builds
class COutput {
public:
    COutput() {}
};
#endif

/**
 * @file zeronode-wallet-interface.h
 * @brief Wallet abstraction interface for zeronode functionality
 * 
 * ARCHITECTURAL OVERVIEW
 * =====================
 * 
 * This interface solves the architectural coupling problem between zeronodes 
 * (masternodes) and wallet functionality in Zero Currency. Previously, zeronode 
 * code directly accessed wallet functions through pwalletMain, creating:
 * 
 * 1. Tight coupling - zeronode code couldn't work without wallet
 * 2. Build complexity - wallet-disabled builds required extensive #ifdef guards
 * 3. Testing difficulties - mocking wallet behavior was complex
 * 4. Code maintenance - wallet changes broke zeronode functionality
 * 
 * DESIGN PATTERN
 * ==============
 * 
 * Uses the Strategy pattern with two implementations:
 * - CZeronodeWalletInterface: Real wallet operations (wallet-enabled builds)
 * - CZeronodeWalletStub: Safe no-op operations (wallet-disabled builds)
 * 
 * WALLET-ZERONODE INTERACTION FLOW
 * ===============================
 * 
 * 1. Zeronode Registration:
 *    zeronode -> GetZeronodeVinAndKeys() -> wallet finds collateral UTXO
 *    
 * 2. Payment Processing:
 *    zeronode -> GetBudgetSystemCollateralTX() -> wallet creates payment tx
 *    zeronode -> CommitTransaction() -> wallet broadcasts to network
 *    
 * 3. Coin Management:
 *    zeronode -> LockCoin() -> wallet reserves UTXOs for zeronode use
 *    zeronode -> AvailableCoins() -> wallet lists spendable outputs
 *    
 * 4. State Queries:
 *    RPC/zeronode -> IsLocked() -> check if wallet can sign transactions
 *    RPC/zeronode -> GetBalance() -> verify sufficient funds for operations
 *    blockchain RPC -> NullifierCount() -> get shielded transaction statistics
 * 
 * USAGE PATTERNS
 * ==============
 * 
 * Basic Usage:
 * ```cpp
 * // Always check availability first
 * if (!g_zeronodeWallet || !g_zeronodeWallet->IsAvailable()) {
 *     LogPrint("zeronode", "Wallet not available for zeronode operations\n");
 *     return false;
 * }
 * 
 * // Perform wallet operation
 * if (g_zeronodeWallet->IsLocked()) {
 *     LogPrint("zeronode", "Wallet is locked, cannot sign transactions\n");
 *     return false;
 * }
 * ```
 * 
 * Thread-Safe Usage:
 * ```cpp
 * // Lock wallet's critical section for thread safety
 * {
 *     LOCK(g_zeronodeWallet->GetCS());
 *     // Perform multiple related operations atomically
 *     g_zeronodeWallet->LockCoin(output);
 *     // ... other operations
 * }
 * ```
 * 
 * INITIALIZATION
 * ==============
 * 
 * The interface must be initialized early in the application lifecycle:
 * 1. Called from init.cpp after wallet initialization
 * 2. Creates appropriate implementation based on ENABLE_WALLET
 * 3. Sets global g_zeronodeWallet instance
 * 
 * FUTURE IMPROVEMENTS
 * ==================
 * 
 * 1. Error Handling Enhancement:
 *    - Add specific error codes instead of boolean returns
 *    - Implement ZeronodeWalletError enum for detailed error reporting
 *    - Add GetLastError() method for error diagnostics
 * 
 * 2. Async Operations:
 *    - Add async transaction broadcasting with callbacks
 *    - Implement progress reporting for long operations
 *    - Add cancellation support for slow wallet operations
 * 
 * 3. Enhanced Abstraction:
 *    - Add wallet event notifications (new transactions, balance changes)
 *    - Implement wallet capability discovery (HD wallet, hardware wallet)
 *    - Add batch operations for improved performance
 * 
 * 4. Testing Infrastructure:
 *    - Create MockZeronodeWallet for unit testing
 *    - Add wallet state simulation capabilities
 *    - Implement deterministic test fixtures
 * 
 * 5. Performance Optimization:
 *    - Cache frequently accessed wallet state
 *    - Add bulk coin availability queries
 *    - Optimize critical section usage
 * 
 * 6. Security Enhancements:
 *    - Add operation audit logging
 *    - Implement wallet operation rate limiting
 *    - Add secure memory handling for keys
 */
class IZeronodeWalletInterface
{
public:
    virtual ~IZeronodeWalletInterface() {}
    
    // ======================== WALLET STATE QUERIES ========================
    
    /**
     * @brief Check if wallet is locked for spending operations
     * @return true if wallet is locked/encrypted and requires passphrase, or wallet unavailable
     * @return false if wallet is unlocked and ready for signing transactions
     * 
     * Used by: Zeronode activation, payment broadcasting, any operation requiring private keys
     * Thread-safe: Yes (read-only operation)
     */
    virtual bool IsLocked() const = 0;
    
    /**
     * @brief Get current confirmed wallet balance
     * @return Total confirmed balance in satoshis, 0 if wallet unavailable
     * 
     * Used by: Zeronode collateral verification, budget proposals, balance checks
     * Thread-safe: Yes (read-only operation)
     * Note: Does not include unconfirmed or immature coinbase transactions
     */
    virtual CAmount GetBalance() const = 0;
    
    /**
     * @brief Check if wallet is available and initialized
     * @return true if wallet exists and is ready for operations
     * @return false if wallet-disabled build or wallet failed to initialize
     * 
     * Used by: All zeronode operations as availability guard
     * Thread-safe: Yes (simple pointer check)
     * Critical: Always check this before any other wallet operations
     */
    virtual bool IsAvailable() const = 0;
    
    /**
     * @brief Get count of shielded transaction nullifiers in wallet
     * @return Number of nullifiers, 0 if wallet unavailable or no shielded transactions
     * 
     * Used by: Blockchain RPC for shielded transaction statistics
     * Thread-safe: Yes (read-only operation)
     * Note: Used for calculating anonymity set size and shielded pool statistics
     */
    virtual int64_t NullifierCount() const = 0;
    
    // ======================== KEY MANAGEMENT ========================
    
    /**
     * @brief Retrieve private key for given key ID
     * @param keyID The key identifier to look up
     * @param key Output parameter to store the retrieved private key
     * @return true if key found and wallet unlocked, false otherwise
     * 
     * Used by: Zeronode signing operations, message signing
     * Thread-safe: Requires wallet critical section lock
     * Security: Sensitive operation - key material in memory
     */
    virtual bool GetKey(const CKeyID& keyID, CKey& key) const = 0;
    
    /**
     * @brief Get zeronode collateral transaction input and associated keys
     * @param txin Output parameter for the collateral transaction input
     * @param pubKeyCollateralAddress Output parameter for collateral public key
     * @param keyCollateralAddress Output parameter for collateral private key
     * @param strTxHash Output parameter for collateral transaction hash string
     * @param strOutputIndex Output parameter for collateral output index string
     * @return true if suitable collateral found and keys retrieved, false otherwise
     * 
     * Used by: Zeronode registration and activation
     * Thread-safe: Requires wallet critical section lock
     * Requirements: Exactly 1000 ZERO UTXO for collateral, wallet unlocked
     */
    virtual bool GetZeronodeVinAndKeys(CTxIn& txin, CPubKey& pubKeyCollateralAddress, 
                                      CKey& keyCollateralAddress, std::string& strTxHash, 
                                      std::string& strOutputIndex) = 0;
    
    // ======================== COIN MANAGEMENT ========================
    
    /**
     * @brief Lock a UTXO to prevent spending by regular transactions
     * @param output The outpoint (txid + vout) to lock
     * 
     * Used by: Zeronode collateral protection, budget proposal creation
     * Thread-safe: Requires wallet critical section lock
     * Effect: Locked UTXOs won't appear in AvailableCoins() or automatic coin selection
     */
    virtual void LockCoin(COutPoint& output) = 0;
    
    /**
     * @brief Unlock a previously locked UTXO
     * @param output The outpoint (txid + vout) to unlock
     * 
     * Used by: Zeronode deactivation, budget proposal cleanup
     * Thread-safe: Requires wallet critical section lock
     * Effect: UTXO becomes available for spending again
     */
    virtual void UnlockCoin(COutPoint& output) = 0;
    
    /**
     * @brief Get list of available (spendable) UTXOs
     * @param vCoins Output vector to store available coin outputs
     * 
     * Used by: Zeronode collateral discovery, budget proposal funding
     * Thread-safe: Requires wallet critical section lock
     * Note: Excludes locked coins, immature coinbase, and unconfirmed transactions
     */
    virtual void AvailableCoins(std::vector<COutput>& vCoins) = 0;
    
    // ======================== TRANSACTION OPERATIONS ========================
    
    /**
     * @brief Create collateral transaction for budget system proposals
     * @param wtx Output parameter for the created wallet transaction
     * @param hash The proposal hash this collateral is for
     * @param useIX Whether to use InstantX for faster confirmation
     * @return true if collateral transaction created successfully, false otherwise
     * 
     * Used by: Budget proposal submission
     * Thread-safe: Requires wallet critical section lock
     * Amount: Fixed collateral amount as defined by budget system rules
     */
    virtual bool GetBudgetSystemCollateralTX(CWalletTx& wtx, uint256 hash, bool useIX) = 0;
    
    /**
     * @brief Commit and broadcast a transaction to the network
     * @param wtx The wallet transaction to commit
     * @param reservekey Optional reserved key for change output (can be nullptr)
     * @param strCommand Description of the operation for logging
     * @return true if transaction committed and broadcast successfully, false otherwise
     * 
     * Used by: Budget proposals, zeronode payments, any transaction broadcasting
     * Thread-safe: Requires wallet critical section lock
     * Effect: Transaction added to wallet and broadcast to peers
     */
    virtual bool CommitTransaction(CWalletTx& wtx, void* reservekey, const std::string& strCommand) = 0;
    
    // ======================== WALLET CONTROL ========================
    
    /**
     * @brief Lock the wallet (requires passphrase to unlock)
     * 
     * Used by: Zeronode startup completion, security operations after sensitive operations
     * Thread-safe: Yes
     * Effect: Wallet becomes locked and requires passphrase for signing operations
     */
    virtual void Lock() = 0;
    
    /**
     * @brief Check if transaction was recently updated/confirmed
     * @param hash Transaction hash to check
     * @return true if transaction was recently updated or confirmed
     * 
     * Used by: SwiftTX confirmation tracking, transaction status monitoring
     * Thread-safe: Yes (read-only operation)
     */
    virtual bool UpdatedTransaction(const uint256& hash) = 0;
    
    /**
     * @brief Increment request count for transaction (anti-spam protection)
     * @param hash Transaction hash
     * 
     * Used by: SwiftTX request counting, duplicate request prevention
     * Thread-safe: Yes (atomic operation)
     * Effect: Increments internal counter for the given transaction hash
     */
    virtual void IncrementRequestCount(const uint256& hash) = 0;
    
    /**
     * @brief Get current request count for a transaction
     * @param hash Transaction hash
     * @return Number of requests made for this transaction
     * 
     * Used by: SwiftTX request tracking, spam detection
     * Thread-safe: Yes (read-only operation)
     */
    virtual int GetRequestCount(const uint256& hash) const = 0;
    
    // ======================== THREAD SAFETY ========================
    
    /**
     * @brief Get wallet's critical section for thread synchronization
     * @return Reference to wallet's critical section mutex
     * 
     * Used by: Multi-operation atomic sequences, thread-safe wallet access
     * Usage: LOCK(g_zeronodeWallet->GetCS()) before wallet operations
     * Note: Stub implementation returns a static dummy critical section
     */
    virtual CCriticalSection& GetCS() = 0;
};

#ifdef ENABLE_WALLET
/**
 * @brief Concrete implementation using actual wallet for wallet-enabled builds
 * 
 * This implementation forwards all calls to the global pwalletMain instance,
 * providing real wallet functionality to zeronode operations.
 * 
 * Initialization: Created by InitZeronodeWalletInterface() when ENABLE_WALLET is defined
 * Dependencies: Requires pwalletMain to be initialized before use
 * Thread Safety: Inherits thread safety from underlying wallet implementation
 */
class CZeronodeWalletInterface : public IZeronodeWalletInterface
{
public:
    bool IsLocked() const override;
    CAmount GetBalance() const override;
    bool IsAvailable() const override;
    int64_t NullifierCount() const override;
    
    bool GetKey(const CKeyID& keyID, CKey& key) const override;
    bool GetZeronodeVinAndKeys(CTxIn& txin, CPubKey& pubKeyCollateralAddress, 
                              CKey& keyCollateralAddress, std::string& strTxHash, 
                              std::string& strOutputIndex) override;
    
    void LockCoin(COutPoint& output) override;
    void UnlockCoin(COutPoint& output) override;
    void AvailableCoins(std::vector<COutput>& vCoins) override;
    
    bool GetBudgetSystemCollateralTX(CWalletTx& wtx, uint256 hash, bool useIX) override;
    bool CommitTransaction(CWalletTx& wtx, void* reservekey, const std::string& strCommand) override;
    
    void Lock() override;
    bool UpdatedTransaction(const uint256& hash) override;
    void IncrementRequestCount(const uint256& hash) override;
    int GetRequestCount(const uint256& hash) const override;
    
    CCriticalSection& GetCS() override;
};

#else
/**
 * @brief Stub implementation for wallet-disabled builds
 * 
 * This implementation provides safe no-op behavior when wallet functionality
 * is not available or disabled at compile time. All operations return failure
 * states or safe defaults.
 * 
 * Behavior:
 * - State queries return "unavailable" states (locked=true, balance=0, available=false)
 * - Key operations return failure (false)
 * - Coin operations are no-ops (safe to call, do nothing)
 * - Transaction operations return failure (false)
 * - Critical section returns static dummy mutex for thread safety
 * 
 * Usage: Automatically used in wallet-disabled builds, allows zeronode code
 *        to compile and run safely without wallet support
 */
class CZeronodeWalletStub : public IZeronodeWalletInterface
{
public:
    bool IsLocked() const override { return true; }
    CAmount GetBalance() const override { return 0; }
    bool IsAvailable() const override { return false; }
    int64_t NullifierCount() const override { return 0; }
    
    bool GetKey(const CKeyID& keyID, CKey& key) const override { return false; }
    bool GetZeronodeVinAndKeys(CTxIn& txin, CPubKey& pubKeyCollateralAddress, 
                              CKey& keyCollateralAddress, std::string& strTxHash, 
                              std::string& strOutputIndex) override { return false; }
    
    void LockCoin(COutPoint& output) override {}
    void UnlockCoin(COutPoint& output) override {}
    void AvailableCoins(std::vector<COutput>& vCoins) override {}
    
    bool GetBudgetSystemCollateralTX(CWalletTx& wtx, uint256 hash, bool useIX) override { return false; }
    bool CommitTransaction(CWalletTx& wtx, void* reservekey, const std::string& strCommand) override { return false; }
    
    void Lock() override {}
    bool UpdatedTransaction(const uint256& hash) override { return false; }
    void IncrementRequestCount(const uint256& hash) override {}
    int GetRequestCount(const uint256& hash) const override { return 0; }
    
    CCriticalSection& GetCS() override { 
        static CCriticalSection stubCS;
        return stubCS; 
    }
};
#endif

/**
 * @brief Global wallet interface instance
 * 
 * This global pointer provides access to the wallet interface throughout
 * the zeronode subsystem. It points to either CZeronodeWalletInterface
 * or CZeronodeWalletStub depending on build configuration.
 * 
 * Initialization: Set by InitZeronodeWalletInterface() during startup
 * Lifetime: Valid for entire application lifetime after initialization
 * Thread Safety: Read-only after initialization, thread-safe to access
 * 
 * Usage Guidelines:
 * - Always check for nullptr before use
 * - Always call IsAvailable() before wallet operations
 * - Use GetCS() for multi-operation atomic sequences
 */
extern IZeronodeWalletInterface* g_zeronodeWallet;

/**
 * @brief Initialize the wallet interface based on build configuration
 * 
 * Creates and assigns the appropriate implementation to g_zeronodeWallet:
 * - ENABLE_WALLET defined: Creates CZeronodeWalletInterface (real wallet)
 * - ENABLE_WALLET not defined: Creates CZeronodeWalletStub (no-op implementation)
 * 
 * Call Requirements:
 * - Must be called exactly once during application startup
 * - Should be called after wallet initialization (if wallet enabled)
 * - Must be called before any zeronode operations
 * 
 * Location: Called from init.cpp in the initialization sequence
 * Thread Safety: Not thread-safe, must be called from main thread only
 */
void InitZeronodeWalletInterface();

#endif // ZERONODE_WALLET_INTERFACE_H