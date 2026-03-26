// Copyright 2026 Zero Developers
// Distributed under the MIT/X11 software license, see the accompanying
// file COPYING or http://www.opensource.org/licenses/mit-license.php.

/**
 * @file zeronode-wallet-interface.cpp
 * @brief Implementation of wallet abstraction interface for zeronode operations
 * 
 * This file provides the concrete implementation of the zeronode wallet interface,
 * bridging zeronode functionality with wallet operations in a clean, decoupled manner.
 * 
 * The implementation handles two build scenarios:
 * 1. Wallet-enabled builds: Forward calls to pwalletMain with proper error handling
 * 2. Wallet-disabled builds: Handled by stub class (header-only implementation)
 */

#include "zeronode/zeronode-wallet-interface.h"

#ifdef ENABLE_WALLET
#include "wallet/wallet.h"
#include "wallet/walletdb.h"
#include "init.h"

// ======================== CONCRETE WALLET IMPLEMENTATION ========================
//
// All methods in this implementation follow the same pattern:
// 1. Check if pwalletMain is available (null check)
// 2. Forward the call to the actual wallet method
// 3. Return appropriate error state if wallet unavailable
//
// Thread Safety: These methods inherit thread safety characteristics from
// the underlying wallet implementation. Most operations require the caller
// to hold the wallet's critical section lock.
bool CZeronodeWalletInterface::IsLocked() const
{
    // Return locked state if wallet unavailable - safe default for security
    if (!pwalletMain) return true;
    return pwalletMain->IsLocked();
}

CAmount CZeronodeWalletInterface::GetBalance() const
{
    // Return zero balance if wallet unavailable - safe default
    if (!pwalletMain) return 0;
    return pwalletMain->GetBalance();
}

bool CZeronodeWalletInterface::IsAvailable() const
{
    // Simple null check - primary availability indicator for all operations
    return pwalletMain != nullptr;
}

int64_t CZeronodeWalletInterface::NullifierCount() const
{
    // Return zero count if wallet unavailable - used for blockchain statistics
    if (!pwalletMain) return 0;
    return pwalletMain->NullifierCount();
}

bool CZeronodeWalletInterface::GetKey(const CKeyID& keyID, CKey& key) const
{
    // Security-critical: Always fail if wallet unavailable
    if (!pwalletMain) return false;
    return pwalletMain->GetKey(keyID, key);
}

bool CZeronodeWalletInterface::GetZeronodeVinAndKeys(CTxIn& txin, CPubKey& pubKeyCollateralAddress, 
                                                    CKey& keyCollateralAddress, std::string& strTxHash, 
                                                    std::string& strOutputIndex)
{
    // Zeronode-specific operation: Find suitable 1000 ZERO collateral and extract keys
    if (!pwalletMain) return false;
    return pwalletMain->GetZeronodeVinAndKeys(txin, pubKeyCollateralAddress, keyCollateralAddress, strTxHash, strOutputIndex);
}

void CZeronodeWalletInterface::LockCoin(COutPoint& output)
{
    // Safe to call with null wallet - becomes no-op
    if (pwalletMain) {
        pwalletMain->LockCoin(output);
    }
}

void CZeronodeWalletInterface::UnlockCoin(COutPoint& output)
{
    // Safe to call with null wallet - becomes no-op
    if (pwalletMain) {
        pwalletMain->UnlockCoin(output);
    }
}

void CZeronodeWalletInterface::AvailableCoins(std::vector<COutput>& vCoins)
{
    // Safe to call with null wallet - leaves vector empty (no available coins)
    if (pwalletMain) {
        pwalletMain->AvailableCoins(vCoins);
    }
}

bool CZeronodeWalletInterface::GetBudgetSystemCollateralTX(CWalletTx& wtx, uint256 hash, bool useIX)
{
    // Budget operations require wallet - fail safely if unavailable
    if (!pwalletMain) return false;
    return pwalletMain->GetBudgetSystemCollateralTX(wtx, hash, useIX);
}

bool CZeronodeWalletInterface::CommitTransaction(CWalletTx& wtx, void* reservekey, const std::string& strCommand)
{
    // Transaction broadcasting requires wallet - fail safely if unavailable
    if (!pwalletMain) return false;
    
    // Handle optional reserve key parameter - different wallet API signatures
    if (reservekey) {
        // Cast void* back to CReserveKey* - type erasure for header independence
        CReserveKey* rkey = static_cast<CReserveKey*>(reservekey);
        return pwalletMain->CommitTransaction(wtx, *rkey, strCommand);
    } else {
        // No reserve key provided - use boost::optional for API compatibility
        boost::optional<CReserveKey&> noReserve;
        return pwalletMain->CommitTransaction(wtx, noReserve, strCommand);
    }
}

void CZeronodeWalletInterface::Lock()
{
    if (pwalletMain) {
        pwalletMain->Lock();
    }
}

bool CZeronodeWalletInterface::UpdatedTransaction(const uint256& hash)
{
    if (pwalletMain) {
        return pwalletMain->UpdatedTransaction(hash);
    }
    return false;
}

void CZeronodeWalletInterface::IncrementRequestCount(const uint256& hash)
{
    if (pwalletMain) {
        if (pwalletMain->mapRequestCount.count(hash)) {
            pwalletMain->mapRequestCount[hash]++;
        } else {
            pwalletMain->mapRequestCount[hash] = 1;
        }
    }
}

int CZeronodeWalletInterface::GetRequestCount(const uint256& hash) const
{
    if (pwalletMain && pwalletMain->mapRequestCount.count(hash)) {
        return pwalletMain->mapRequestCount[hash];
    }
    return 0;
}

CCriticalSection& CZeronodeWalletInterface::GetCS()
{
    // Prefer wallet's actual critical section for proper synchronization
    if (pwalletMain) {
        return pwalletMain->cs_wallet;
    }
    // Fallback: Return static dummy critical section if wallet unavailable
    // This allows thread-safe code patterns to work even without wallet
    static CCriticalSection stubCS;
    return stubCS;
}

#endif

// ======================== GLOBAL INTERFACE MANAGEMENT ========================

/**
 * @brief Global wallet interface instance
 * 
 * This pointer is the single point of access to wallet functionality throughout
 * the zeronode subsystem. It's initialized once during application startup and
 * remains valid for the entire application lifetime.
 * 
 * Implementation Details:
 * - Set to CZeronodeWalletInterface in wallet-enabled builds
 * - Set to CZeronodeWalletStub in wallet-disabled builds
 * - Thread-safe to read after initialization
 * - Never modified after InitZeronodeWalletInterface() completes
 */
IZeronodeWalletInterface* g_zeronodeWallet = nullptr;

/**
 * @brief Initialize the global wallet interface instance
 * 
 * This function is the single initialization point for the wallet interface system.
 * It determines the appropriate implementation based on compile-time configuration
 * and creates the global instance.
 * 
 * Initialization Logic:
 * 1. Check ENABLE_WALLET preprocessor definition
 * 2. Create appropriate implementation (real wallet or stub)
 * 3. Assign to global g_zeronodeWallet pointer
 * 
 * Error Handling:
 * - No explicit error handling needed - constructors are simple
 * - Memory allocation failures would terminate application (standard behavior)
 * 
 * Call Site: init.cpp during application initialization sequence
 * Call Frequency: Exactly once per application lifetime
 * Thread Safety: Must be called from main thread only, before any zeronode operations
 */
void InitZeronodeWalletInterface()
{
#ifdef ENABLE_WALLET
    // Create real wallet interface - forwards calls to pwalletMain
    g_zeronodeWallet = new CZeronodeWalletInterface();
#else
    // Create stub interface - safe no-op operations for wallet-disabled builds
    g_zeronodeWallet = new CZeronodeWalletStub();
#endif
}