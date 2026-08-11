// Copyright 2026 Zero Developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php.

#include <gtest/gtest.h>

#include "primitives/transaction.h"
#include "uint256.h"
#include "util.h"
#include "zeronode/activezeronode.h"
#include "zeronode/obfuscation.h"
#include "zeronode/zeronode-sync.h"
#include "zeronode/zeronode-wallet-interface.h"

#include <map>
#include <set>
#include <string>
#include <vector>

class MockZeronodeWallet : public IZeronodeWalletInterface
{
public:
    bool locked = false;
    bool available = true;
    CAmount balance = 0;
    bool vinOk = false;
    bool commitOk = false;
    bool budgetOk = false;
    bool updated = false;

    std::vector<std::string> calls;
    std::set<COutPoint> lockedCoins;
    std::map<uint256, int> requestCount;
    CTxIn vin;
    CCriticalSection cs;

    bool IsLocked() const override { return locked; }
    CAmount GetBalance() const override { return balance; }
    bool IsAvailable() const override { return available; }
    int64_t NullifierCount() const override { return 0; }

    bool GetKey(const CKeyID& keyID, CKey& key) const override
    {
        (void)keyID;
        (void)key;
        return false;
    }
    bool GetZeronodeVinAndKeys(CTxIn& txin, CPubKey& pubKeyCollateralAddress,
                               CKey& keyCollateralAddress, std::string& strTxHash,
                               std::string& strOutputIndex) override
    {
        (void)pubKeyCollateralAddress;
        (void)keyCollateralAddress;
        calls.push_back("GetZeronodeVinAndKeys");
        if (!vinOk) return false;
        txin = vin;
        strTxHash = vin.prevout.hash.ToString();
        strOutputIndex = std::to_string(vin.prevout.n);
        return true;
    }

    void LockCoin(COutPoint& output) override
    {
        calls.push_back("LockCoin");
        lockedCoins.insert(output);
    }
    void UnlockCoin(COutPoint& output) override
    {
        calls.push_back("UnlockCoin");
        lockedCoins.erase(output);
    }
    void AvailableCoins(std::vector<COutput>& vCoins) override
    {
        calls.push_back("AvailableCoins");
        vCoins.clear();
    }

    bool GetBudgetSystemCollateralTX(CWalletTx& wtx, uint256 hash, bool useIX) override
    {
        (void)wtx;
        (void)hash;
        (void)useIX;
        calls.push_back("GetBudgetSystemCollateralTX");
        return budgetOk;
    }
    bool CommitTransaction(CWalletTx& wtx, void* reservekey, const std::string& strCommand) override
    {
        (void)wtx;
        (void)reservekey;
        calls.push_back(std::string("CommitTransaction:") + strCommand);
        return commitOk;
    }

    void Lock() override
    {
        calls.push_back("Lock");
        locked = true;
    }
    bool UpdatedTransaction(const uint256& hash) override
    {
        (void)hash;
        calls.push_back("UpdatedTransaction");
        return updated;
    }
    void IncrementRequestCount(const uint256& hash) override
    {
        calls.push_back("IncrementRequestCount");
        requestCount[hash]++;
    }
    int GetRequestCount(const uint256& hash) const override
    {
        auto it = requestCount.find(hash);
        return it == requestCount.end() ? 0 : it->second;
    }
    CCriticalSection& GetCS() override { return cs; }
};

class SwapZeronodeWallet
{
    IZeronodeWalletInterface* prev;
public:
    explicit SwapZeronodeWallet(IZeronodeWalletInterface* w)
        : prev(g_zeronodeWallet)
    {
        g_zeronodeWallet = w;
    }
    ~SwapZeronodeWallet() { g_zeronodeWallet = prev; }
};

TEST(ZeronodeWalletMock, RecordsLockAndRequestCount)
{
    MockZeronodeWallet mock;
    SwapZeronodeWallet swap(&mock);
    COutPoint out(uint256S("01"), 0);
    {
        LOCK(g_zeronodeWallet->GetCS());
        g_zeronodeWallet->LockCoin(out);
        g_zeronodeWallet->UnlockCoin(out);
    }
    uint256 h = uint256S("02");
    EXPECT_EQ(0, g_zeronodeWallet->GetRequestCount(h));
    g_zeronodeWallet->IncrementRequestCount(h);
    g_zeronodeWallet->IncrementRequestCount(h);
    EXPECT_EQ(2, g_zeronodeWallet->GetRequestCount(h));
    ASSERT_EQ(mock.calls.size(), 4u);
    EXPECT_EQ(mock.calls[0], "LockCoin");
    EXPECT_EQ(mock.calls[1], "UnlockCoin");
    EXPECT_EQ(mock.calls[2], "IncrementRequestCount");
    EXPECT_EQ(mock.calls[3], "IncrementRequestCount");
}

TEST(ZeronodeWalletMock, ForceVinAndKeys)
{
    MockZeronodeWallet mock;
    mock.vinOk = true;
    mock.vin = CTxIn(uint256S("aa"), 1);
    SwapZeronodeWallet swap(&mock);
    CTxIn txin;
    CPubKey pub;
    CKey key;
    std::string hash, idx;
    EXPECT_TRUE(g_zeronodeWallet->GetZeronodeVinAndKeys(txin, pub, key, hash, idx));
    EXPECT_EQ(txin.prevout.n, 1u);
    EXPECT_EQ(idx, "1");
}

TEST(ZeronodeWalletMock, ManageStatusWalletUnavailable)
{
    MockZeronodeWallet mock;
    mock.available = false;
    SwapZeronodeWallet swap(&mock);
    const bool savedZN = fZeroNode;
    const int savedSync = zeronodeSync.RequestedZeronodeAssets;
    const int savedStatus = activeZeronode.status;
    fZeroNode = true;
    zeronodeSync.RequestedZeronodeAssets = ZERONODE_SYNC_FINISHED;
    activeZeronode.status = ACTIVE_ZERONODE_INITIAL;
    activeZeronode.ManageStatus();
    EXPECT_EQ(activeZeronode.status, ACTIVE_ZERONODE_NOT_CAPABLE);
    EXPECT_EQ(activeZeronode.notCapableReason, "Wallet not available.");
    fZeroNode = savedZN;
    zeronodeSync.RequestedZeronodeAssets = savedSync;
    activeZeronode.status = savedStatus;
}

TEST(ZeronodeWalletMock, ManageStatusLockedAndZeroBalance)
{
    MockZeronodeWallet mock;
    mock.available = true;
    mock.locked = true;
    mock.balance = 0;
    SwapZeronodeWallet swap(&mock);
    const bool savedZN = fZeroNode;
    const int savedSync = zeronodeSync.RequestedZeronodeAssets;
    const int savedStatus = activeZeronode.status;
    fZeroNode = true;
    zeronodeSync.RequestedZeronodeAssets = ZERONODE_SYNC_FINISHED;
    activeZeronode.status = ACTIVE_ZERONODE_INITIAL;
    activeZeronode.ManageStatus();
    EXPECT_EQ(activeZeronode.notCapableReason, "Wallet is locked.");

    mock.locked = false;
    activeZeronode.status = ACTIVE_ZERONODE_INITIAL;
    activeZeronode.ManageStatus();
    EXPECT_EQ(activeZeronode.notCapableReason, "Hot node, waiting for remote activation.");

    fZeroNode = savedZN;
    zeronodeSync.RequestedZeronodeAssets = savedSync;
    activeZeronode.status = savedStatus;
}

TEST(ZeronodeWalletMock, SelectCoinsCallsAvailableCoins)
{
    MockZeronodeWallet mock;
    SwapZeronodeWallet swap(&mock);
    std::vector<COutput> coins = activeZeronode.SelectCoinsZeronode();
    EXPECT_TRUE(coins.empty());
    ASSERT_FALSE(mock.calls.empty());
    EXPECT_EQ(mock.calls.back(), "AvailableCoins");
}
