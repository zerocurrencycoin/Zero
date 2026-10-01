// Copyright (c) 2009-2010 Satoshi Nakamoto
// Copyright (c) 2009-2014 The Bitcoin Core developers
// Distributed under the MIT software license, see the accompanying
// file COPYING or https://www.opensource.org/licenses/mit-license.php .

#ifndef BITCOIN_POW_H
#define BITCOIN_POW_H

#if defined(HAVE_CONFIG_H)
#include "config/bitcoin-config.h"
#endif

#include "consensus/params.h"

#include <stdint.h>

class CBlockHeader;
class CBlockIndex;
class CChainParams;
class uint256;
class arith_uint256;

unsigned int GetNextWorkRequired(const CBlockIndex* pindexLast, const CBlockHeader *pblock, const Consensus::Params&);
unsigned int CalculateNextWorkRequired(arith_uint256 bnAvg,
                                       int64_t nLastBlockTime, int64_t nFirstBlockTime,
                                       const Consensus::Params&,
                                       int nextHeight);

/** Check whether the Equihash solution in a block header is valid */
bool CheckEquihashSolution(const CBlockHeader *pblock, const Consensus::Params&);

#ifdef ZERO_PERF
// P13: Equihash verification calls and time, split by the caller that asked.
// A caller tags the current thread with PerfEqSiteScope; CheckEquihashSolution
// records under whatever tag is active. Untagged calls count as OTHER.
enum PerfEqSite {
    PERF_EQ_OTHER,
    PERF_EQ_PROCESS_NEW_BLOCK,
    PERF_EQ_ACCEPT_HEADER,
    PERF_EQ_ACCEPT_BLOCK,
    PERF_EQ_READ_DISK,
    PERF_EQ_CONNECT,
    PERF_EQ_TEST_VALIDITY,
    PERF_EQ_NSITES
};

class PerfEqSiteScope {
public:
    explicit PerfEqSiteScope(PerfEqSite site);
    ~PerfEqSiteScope();
private:
    PerfEqSite prev;
};

/** Log cumulative per-site counts: "PerfEquihash: height=N site=calls/us ..." */
void LogPerfEquihash(int nHeight);
#endif

/** Check whether a block hash satisfies the proof-of-work requirement specified by nBits */
bool CheckProofOfWork(uint256 hash, unsigned int nBits, const Consensus::Params&);
arith_uint256 GetBlockProof(const CBlockIndex& block);

/** Return the time it would take to redo the work difference between from and to, assuming the current hashrate corresponds to the difficulty at tip, in seconds. */
int64_t GetBlockProofEquivalentTime(const CBlockIndex& to, const CBlockIndex& from, const CBlockIndex& tip, const Consensus::Params&);

#endif // BITCOIN_POW_H
