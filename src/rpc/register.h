// Copyright (c) 2009-2016 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php .

#ifndef BITCOIN_RPCREGISTER_H
#define BITCOIN_RPCREGISTER_H

/** These are in one header file to avoid creating tons of single-function
 * headers for everything under src/rpc/ */
class CRPCTable;

/** Register block chain RPC commands */
void RegisterBlockchainRPCCommands(CRPCTable &tableRPC);
/** Register P2P networking RPC commands */
void RegisterNetRPCCommands(CRPCTable &tableRPC);
/** Register miscellaneous RPC commands */
void RegisterMiscRPCCommands(CRPCTable &tableRPC);
/** Register mining RPC commands */
void RegisterMiningRPCCommands(CRPCTable &tableRPC);
/** Register raw transaction RPC commands */
void RegisterRawTransactionRPCCommands(CRPCTable &tableRPC);
/**Register Zeronode Commands */
void RegisterZeronodeRPCCommands(CRPCTable &tableRPC);
/** Register Wallet RPC commands */
#ifdef ENABLE_WALLET
void RegisterWalletRPCCommands(CRPCTable &tableRPC);
#else
inline void RegisterWalletRPCCommands(CRPCTable &tableRPC) {}
#endif
/**Register Budget Commands */
void RegisterBudgetRPCCommands(CRPCTable &tableRPC);
/** Register Spork RPC commands */
void RegisterSporkRPCCommands(CRPCTable &tableRPC);
/** Register Experimental RPC commands */
#ifdef ENABLE_WALLET
void RegisterZeroExclusiveRPCCommands(CRPCTable &tableRPC);
void RegisterZeroExperimentalRPCCommands(CRPCTable &tableRPC);
#else
inline void RegisterZeroExclusiveRPCCommands(CRPCTable &tableRPC) {}
inline void RegisterZeroExperimentalRPCCommands(CRPCTable &tableRPC) {}
#endif

static inline void RegisterAllCoreRPCCommands(CRPCTable &tableRPC)
{
    RegisterBlockchainRPCCommands(tableRPC);
    RegisterNetRPCCommands(tableRPC);
    RegisterMiscRPCCommands(tableRPC);
    RegisterMiningRPCCommands(tableRPC);
    RegisterRawTransactionRPCCommands(tableRPC);
    RegisterZeronodeRPCCommands(tableRPC);
    RegisterBudgetRPCCommands(tableRPC);
    RegisterSporkRPCCommands(tableRPC);
#ifdef ENABLE_WALLET
    RegisterZeroExclusiveRPCCommands(tableRPC);
    RegisterZeroExperimentalRPCCommands(tableRPC);
#endif
}

#endif
