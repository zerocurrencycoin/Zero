# blocktools.py - utilities for manipulating blocks and transactions
#
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .
#

from mininode import CBlock, CTransaction, CTxIn, CTxOut, COutPoint
from script import CScript, OP_0, OP_EQUAL, OP_HASH160

# Create a block (with regtest difficulty)
def create_block(hashprev, coinbase, nTime=None, nBits=None, hashFinalSaplingRoot=None):
    block = CBlock()
    if nTime is None:
        import time
        block.nTime = int(time.time()+600)
    else:
        block.nTime = nTime
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
        r.append(chr(absvalue & 0xff))
        absvalue >>= 8
    if r[-1] & 0x80:
        r.append(0x80 if neg else 0)
    elif neg:
        r[-1] |= 0x80
    return r

counter=1
# Zero regtest: 10 ZER base, halving every 150 blocks, 7.5% founder from block 5000
COIN = 100000000
ZERO_REGTEST_FEE_START = 5000
ZERO_REGTEST_HALVING = 150

# Create an anyone-can-spend coinbase transaction, assuming no miner fees
def create_coinbase(heightAdjust = 0):
    global counter
    height = counter + heightAdjust
    coinbase = CTransaction()
    coinbase.vin.append(CTxIn(COutPoint(0, 0xffffffff), 
                CScript([height, OP_0]), 0xffffffff))
    counter += 1
    coinbaseoutput = CTxOut()
    nSubsidy = int(10 * COIN)  # Zero: 10 ZER pre-fee
    halvings = int(height / ZERO_REGTEST_HALVING)
    coinbaseoutput.nValue = nSubsidy >> halvings
    coinbaseoutput.scriptPubKey = ""
    coinbase.vout = [ coinbaseoutput ]
    if height >= ZERO_REGTEST_FEE_START and halvings < 64:
        froutput = CTxOut()
        froutput.nValue = int(coinbaseoutput.nValue * 7.5 / 100)  # 7.5% founder
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
    tx.vout.append(CTxOut(value, ""))
    tx.calc_sha256()
    return tx
