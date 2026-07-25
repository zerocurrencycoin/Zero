# blocktools.py - utilities for manipulating blocks and transactions
#
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .
#

from test_framework.mininode import CBlock, CTransaction, CTxIn, CTxOut, COutPoint
from test_framework.script import CScript, OP_0, OP_EQUAL, OP_HASH160

# Create a block (with regtest difficulty)
def create_block(hashprev, coinbase, nTime=None, nBits=None, hashFinalSaplingRoot=None):
    block = CBlock()
    if nTime is None:
        import time
        block.nTime = int(time.time()+600)
    else:
        block.nTime = int(nTime)
    block.hashPrevBlock = hashprev
    if hashFinalSaplingRoot is not None:
        block.hashFinalSaplingRoot = hashFinalSaplingRoot
    if nBits is None:
        block.nBits = 0x200f0f0f # Will break after a difficulty adjustment...
    else:
        block.nBits = nBits
    block.vtx.append(coinbase)
    block.hashMerkleRoot = block.calc_merkle_root()
    block.calc_sha256()
    return block

def serialize_script_num(value):
    r = bytearray(0)
    if value == 0:
        return r
    neg = value < 0
    absvalue = -value if neg else value
    while (absvalue):
        r.append(absvalue & 0xff)
        absvalue >>= 8
    if r[-1] & 0x80:
        r.append(0x80 if neg else 0)
    elif neg:
        r[-1] |= 0x80
    return r

counter=1
# Zero regtest: match Consensus::REGTEST_FOUNDERS_* (util.py mirrors params.h)
from test_framework.util import (
    REGTEST_FOUNDERS_START,
    REGTEST_FOUNDERS_STOP,
    REGTEST_HALVING,
)
COIN = 100000000

# Create an anyone-can-spend coinbase transaction, assuming no miner fees
def create_coinbase(heightAdjust = 0):
    global counter
    height = counter + heightAdjust
    coinbase = CTransaction()
    coinbase.vin.append(CTxIn(COutPoint(0, 0xffffffff), 
                CScript([height, OP_0]), 0xffffffff))
    counter += 1
    coinbaseoutput = CTxOut()
    base = (108 * COIN // 10) if height >= REGTEST_FOUNDERS_START else (10 * COIN)
    halvings = int(height / REGTEST_HALVING)
    if halvings >= 64:
        coinbaseoutput.nValue = 0
    else:
        coinbaseoutput.nValue = base >> halvings
    coinbaseoutput.scriptPubKey = b""
    coinbase.vout = [ coinbaseoutput ]
    if (REGTEST_FOUNDERS_START <= height < REGTEST_FOUNDERS_STOP) and halvings < 64:
        froutput = CTxOut()
        froutput.nValue = coinbaseoutput.nValue * 75 // 1000  # 7.5% founder, integer
        fraddr = bytearray([0x67, 0x08, 0xe6, 0x67, 0x0d, 0xb0, 0xb9, 0x50,
                            0xda, 0xc6, 0x80, 0x31, 0x02, 0x5c, 0xc5, 0xb6,
                            0x32, 0x13, 0xa4, 0x91])  # regtest founder t2FwcEhFdNXuFMv1tcYwaBJtYVtMj8b1uTg
        froutput.scriptPubKey = CScript([OP_HASH160, fraddr, OP_EQUAL])
        coinbaseoutput.nValue -= froutput.nValue
        coinbase.vout = [ coinbaseoutput, froutput ]
    coinbase.calc_sha256()
    return coinbase

# Create a transaction with an anyone-can-spend output, that spends the
# nth output of prevtx.
def create_transaction(prevtx, n, sig, value):
    tx = CTransaction()
    assert(n < len(prevtx.vout))
    tx.vin.append(CTxIn(COutPoint(prevtx.sha256, n), sig, 0xffffffff))
    tx.vout.append(CTxOut(value, b""))
    tx.calc_sha256()
    return tx
