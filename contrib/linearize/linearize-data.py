#!/usr/bin/env python3
#
# linearize-data.py: Construct a linear, no-fork version of the chain.
#
# Copyright (c) 2013-2014 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or https://www.opensource.org/licenses/mit-license.php .
#
# Zero: block files use CBlockHeader + nSolution (Equihash), not Bitcoin's
# 80-byte header. Block hash matches SerializeHash(CBlockHeader) / getblockhash.


import struct
import re
import os
import os.path
import sys
import hashlib
import datetime
import time
from collections import namedtuple

settings = {}

# CBlockHeader field layout (serialize order); nTime at byte 100.
ZERO_HEADER_NTIME_OFF = 4 + 32 + 32 + 32


def read_compact_size(data, off):
	ch = data[off]
	off += 1
	if ch < 253:
		return ch, off
	if ch == 253:
		return struct.unpack_from('<H', data, off)[0], off + 2
	if ch == 254:
		return struct.unpack_from('<I', data, off)[0], off + 4
	return struct.unpack_from('<Q', data, off)[0], off + 8


def header_serialize_bytes(payload):
	"""Bytes serialized for CBlockHeader::GetHash (header fields through nSolution)."""
	off = 0
	start = off
	off += 4 + 32 + 32 + 32 + 4 + 4 + 32
	sol_len, off_after = read_compact_size(payload, off)
	off = off_after + sol_len
	return payload[start:off]


def block_hash_hex(payload):
	"""Match zerod getblockhash / SerializeHash(CBlockHeader)."""
	hdr = header_serialize_bytes(payload)
	digest = hashlib.sha256(hashlib.sha256(hdr).digest()).digest()
	return digest[::-1].hex()


def get_blk_dt(payload):
	members = struct.unpack("<I", payload[ZERO_HEADER_NTIME_OFF:ZERO_HEADER_NTIME_OFF + 4])
	nTime = members[0]
	dt = datetime.datetime.fromtimestamp(nTime)
	dt_ym = datetime.datetime(dt.year, dt.month, 1)
	return (dt_ym, nTime)


def get_block_hashes(settings):
	blkindex = []
	with open(settings['hashlist'], "r") as f:
		for line in f:
			line = line.rstrip()
			blkindex.append(line)

	print("Read " + str(len(blkindex)) + " hashes")

	return blkindex


def mkblockmap(blkindex):
	blkmap = {}
	for height, hash in enumerate(blkindex):
		blkmap[hash] = height
	return blkmap

# Block extent on disk (payload only; inhdr stored separately)
BlockExtent = namedtuple('BlockExtent', ['fn', 'offset', 'inhdr', 'size'])


class BlockDataCopier:
	def __init__(self, settings, blkindex, blkmap):
		self.settings = settings
		self.blkindex = blkindex
		self.blkmap = blkmap

		self.inFn = 0
		self.inF = None
		self.outFn = 0
		self.outsz = 0
		self.outF = None
		self.outFname = None
		self.blkCountIn = 0
		self.blkCountOut = 0

		self.lastDate = datetime.datetime(2000, 1, 1)
		self.highTS = 1408893517 - 315360000
		self.timestampSplit = False
		self.fileOutput = True
		self.setFileTime = False
		self.maxOutSz = settings['max_out_sz']
		if 'output' in settings:
			self.fileOutput = False
		if settings['file_timestamp'] != 0:
			self.setFileTime = True
		if settings['split_timestamp'] != 0:
			self.timestampSplit = True
		self.blockExtents = {}
		self.outOfOrderData = {}
		self.outOfOrderSize = 0

	def writeBlock(self, inhdr, payload):
		blockSizeOnDisk = len(inhdr) + len(payload)
		if not self.fileOutput and ((self.outsz + blockSizeOnDisk) > self.maxOutSz):
			self.outF.close()
			if self.setFileTime:
				os.utime(self.outFname, (int(time.time()), self.highTS))
			self.outF = None
			self.outFname = None
			self.outFn = self.outFn + 1
			self.outsz = 0

		(blkDate, blkTS) = get_blk_dt(payload)
		if self.timestampSplit and (blkDate > self.lastDate):
			hash_str = block_hash_hex(payload)
			print("New month " + blkDate.strftime("%Y-%m") + " @ " + hash_str)
			self.lastDate = blkDate
			if self.outF:
				self.outF.close()
				if self.setFileTime:
					os.utime(self.outFname, (int(time.time()), self.highTS))
				self.outF = None
				self.outFname = None
				self.outFn = self.outFn + 1
				self.outsz = 0

		if not self.outF:
			if self.fileOutput:
				self.outFname = self.settings['output_file']
			else:
				self.outFname = os.path.join(self.settings['output'], "blk%05d.dat" % self.outFn)
			print("Output file " + self.outFname)
			self.outF = open(self.outFname, "wb")

		self.outF.write(inhdr)
		self.outF.write(payload)
		self.outsz = self.outsz + blockSizeOnDisk

		self.blkCountOut = self.blkCountOut + 1
		if blkTS > self.highTS:
			self.highTS = blkTS

		if (self.blkCountOut % 1000) == 0:
			print('%i blocks scanned, %i blocks written (of %i, %.1f%% complete)' %
					(self.blkCountIn, self.blkCountOut, len(self.blkindex), 100.0 * self.blkCountOut / len(self.blkindex)))

	def inFileName(self, fn):
		return os.path.join(self.settings['input'], "blk%05d.dat" % fn)

	def fetchBlock(self, extent):
		with open(self.inFileName(extent.fn), "rb") as f:
			f.seek(extent.offset)
			return f.read(extent.size)

	def copyOneBlock(self):
		extent = self.blockExtents.pop(self.blkCountOut)
		if self.blkCountOut in self.outOfOrderData:
			payload = self.outOfOrderData.pop(self.blkCountOut)
			self.outOfOrderSize -= len(payload)
		else:
			payload = self.fetchBlock(extent)

		self.writeBlock(extent.inhdr, payload)

	def run(self):
		while self.blkCountOut < len(self.blkindex):
			if not self.inF:
				fname = self.inFileName(self.inFn)
				if not os.path.exists(fname):
					print("Premature end of block data (%i blocks written, expected %i)" %
						(self.blkCountOut, len(self.blkindex)))
					return
				print("Input file " + fname)
				self.inF = open(fname, "rb")

			inhdr = self.inF.read(8)
			if (not inhdr or (inhdr[0] == 0)):
				self.inF.close()
				self.inF = None
				self.inFn = self.inFn + 1
				continue

			inMagic = inhdr[:4]
			if (inMagic != self.settings['netmagic']):
				print("Invalid magic: " + inMagic.hex())
				return
			nsize = struct.unpack("<I", inhdr[4:])[0]
			payload_offset = self.inF.tell()
			payload = self.inF.read(nsize)
			if len(payload) != nsize:
				print("Truncated block in " + self.inFileName(self.inFn))
				return

			hash_str = block_hash_hex(payload)
			if hash_str not in self.blkmap:
				print("Skipping unknown block " + hash_str)
				continue

			blkHeight = self.blkmap[hash_str]
			self.blkCountIn += 1
			inExtent = BlockExtent(self.inFn, payload_offset, inhdr, nsize)

			if self.blkCountOut == blkHeight:
				self.writeBlock(inhdr, payload)

				while self.blkCountOut in self.blockExtents:
					self.copyOneBlock()

			else:
				self.blockExtents[blkHeight] = inExtent
				if self.outOfOrderSize < self.settings['out_of_order_cache_sz']:
					self.outOfOrderData[blkHeight] = payload
					self.outOfOrderSize += nsize

		print("Done (%i blocks written)" % (self.blkCountOut))


if __name__ == '__main__':
	if len(sys.argv) != 2:
		print("Usage: linearize-data.py CONFIG-FILE")
		sys.exit(1)

	with open(sys.argv[1]) as f:
		for line in f:
			m = re.search(r'^\s*#', line)
			if m:
				continue
			m = re.search(r'^(\w+)\s*=\s*(\S.*)$', line)
			if m is None:
				continue
			settings[m.group(1)] = m.group(2)

	if 'split_timestamp' not in settings and 'split_year' in settings:
		settings['split_timestamp'] = settings['split_year']

	if 'netmagic' not in settings:
		settings['netmagic'] = '5a45524f'
	if 'genesis' not in settings:
		settings['genesis'] = '068cbb5db6bc11be5b93479ea4df41fa7e012e92ca8603c315f9b1a2202205c6'
	if 'input' not in settings:
		settings['input'] = 'input'
	if 'hashlist' not in settings:
		settings['hashlist'] = 'hashlist.txt'
	if 'file_timestamp' not in settings:
		settings['file_timestamp'] = 0
	if 'split_timestamp' not in settings:
		settings['split_timestamp'] = 0
	if 'max_out_sz' not in settings:
		settings['max_out_sz'] = 1000 * 1000 * 1000
	if 'out_of_order_cache_sz' not in settings:
		settings['out_of_order_cache_sz'] = 100 * 1000 * 1000

	settings['max_out_sz'] = int(settings['max_out_sz'])
	settings['split_timestamp'] = int(settings['split_timestamp'])
	settings['file_timestamp'] = int(settings['file_timestamp'])
	settings['netmagic'] = bytes.fromhex(settings['netmagic'])
	settings['out_of_order_cache_sz'] = int(settings['out_of_order_cache_sz'])

	if 'output_file' not in settings and 'output' not in settings:
		print("Missing output file / directory")
		sys.exit(1)

	blkindex = get_block_hashes(settings)
	blkmap = mkblockmap(blkindex)

	if settings['genesis'] not in blkmap:
		print("Genesis block not found in hashlist")
	else:
		BlockDataCopier(settings, blkindex, blkmap).run()
