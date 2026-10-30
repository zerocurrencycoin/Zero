![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/Zero%20Twitter.jpg?raw=true)

[ZERO](https://zerocurrency.io) - [Latest Release](https://github.com/zerocurrencycoin/Zero/releases/)

### •LAUNCH DATE: 2017-02-19

GENESIS BLOCK - 19th Feb 2017 10:26:40 UTC - `068cbb5db6bc11be5b93479ea4df41fa7e012e92ca8603c315f9b1a2202205c6`

------------------------------------------

❓ What is ZERO?
--------------

[ZERO](https://zerocurrency.io) is a privacy-focused cryptocurrency and transaction platform in the Zcash family.

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/) offers strong payment confidentiality while maintaining a decentralised network on a public blockchain.

[ZERO](https://github.com/zerocurrencycoin/Zero) combines Bitcoin-style security with Zerocash-style shielded privacy. Transparent (t-addr) and shielded (z-addr) payments coexist; privacy is optional, not mandatory.

This repository is the **full node** (`zerod`, `zero-cli`, `zero-tx`). It downloads and stores the history of ZERO transactions; the size of a synced node is in BUILD_ZERO "Paths".

Wallets and exchanges are listed on [zerocurrency.io](https://zerocurrency.io); verify tickers on official channels only. Documents for each reader: [Documentation](#-documentation).

------------------------------------------

![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/Zero%20Full%20Logo%20Long%20Black.png?raw=true)


💫 ZERO CORE FEATURES
-------------------

### •FAST TX & ZERO TX COST

### •NO ICO & NO PREMINE

### •SECURE

### •ASIC RESISTANT

### •SHIELDED TRANSACTIONS

### •UNIQUE ALGORITHM

### •DECENTRALIZED PAYMENTS

Zero launched on 2017-02-19 with no premine. The block subsidy started at 10 ZER, became 10.8 ZER at height 412,300, where the 7.5% development fee begins, and halves every 800,000 blocks: after the third halving, at height 2,400,000 in 2026, it is 1.35 ZER. Maximum supply is 16,950,149.896 ZER. Emission, fee, zeronode shares, and consensus parameters: [ZERO_COIN.md](ZERO_COIN.md).

------------------------------------------

❓ Is Zero Legal?
-------------------
Zero is legal in most jurisdictions, but some nation states restrict or ban cryptocurrency use. Regulations vary; research your local law before participating.

❓ Why Trust Zero?
-------------------
Zero aims at decentralisation, open source, and peer-to-peer operation, with privacy as a core design goal. Trust rests on open review of the code and cryptography, not on a single vendor.

--------------

[Zero](https://zero.directory/) implements the Zerocash protocol family. More technical detail: [Zcash Protocol Specification](https://zips.z.cash/protocol/protocol.pdf).

![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/algo%20zer%20improv.jfif)

------------------------------------------


📣 Announcements
-----------------
https://bitcointalk.org/index.php?topic=1796036.0

https://bitcointalk.org/index.php?topic=3310714.0


🔒 Security Warnings
-----------------
See important security warnings on the
[Security Information page](https://z.cash/support/security/).

**Zero is experimental and a work in progress.** Use it at your own risk.

A mainnet node shuts down at the deprecation height built into its release and warns 4 weeks of blocks before it; `getdeprecationinfo` reports the height (`deprecationheight`). The height is `APPROX_RELEASE_HEIGHT` plus 520 weeks of blocks (`src/deprecation.h`).


📚 Documentation
----------------

Documents written for Zero. Tools under `contrib/` are indexed in `contrib/README.md`, with their own READMEs beside them; documents under `depends/`, `src/test/`, and the vendored subtrees are upstream's; generated data files are described where they are used.

| Document | Readers | Purpose |
|----------|---------|---------|
| [README.md](README.md) | Everyone | Front page, chain summary, build and run, this document map |
| [ZERO_COIN.md](ZERO_COIN.md) | Miners, pools, exchanges, integrators | Chain economics, consensus parameters, addresses |
| [BUILD_ZERO.md](BUILD_ZERO.md) | Builders, operators, maintainers | Build, configure, operate (recovery, clock, chain diagnostics), and release on Linux, macOS, and Windows |
| [TEST_ZERO.md](TEST_ZERO.md) | Contributors, maintainers | Test runs, tiers, held scripts, release bar, operational checks |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributors | Change workflow, review terms, coding rules that bind every change |
| [TODO.md](TODO.md) | Contributors, maintainers | Release steps and open work for the full node |
| [AGENTS.md](AGENTS.md) | Agents and humans editing the tree | Scope, git, shell, file, code, and documentation rules |
| `doc/man/` | Operators (after install) | `zerod`, `zero-cli`, `zero-tx` manuals |
| `doc/release-notes/` | Operators, miners, pools, integrators | Changes per release |
| [doc/zeronodes.md](doc/zeronodes.md) | Maintainers | Zeronode, spork, SwiftTX, and budget implementation |
| `doc/Options.csv`, `doc/RPCs.csv`, `doc/Reindex_Rescan.csv` | Maintainers | Options and RPCs in Zero and the reference projects, with dispositions; code references and coverage of the reindex and rescan options; written or checked by `contrib/tools/` |
| [contrib/README.md](contrib/README.md) | Operators, contributors, maintainers | Index of the `contrib` tools and samples |
| [contrib/conf-templates/README.md](contrib/conf-templates/README.md) | Operators | The `zero.conf` templates of `contrib/zero-conf.sh` |
| [qa/rpc-tests/README.md](qa/rpc-tests/README.md) | Contributors | Running one RPC test script outside the runner; framework options |

🔧 Building
--------

### Build and run

Linux, after the packages in BUILD_ZERO "Linux":

```bash
git clone https://github.com/zerocurrencycoin/Zero.git && cd Zero
./zcutil/fetch-params.sh && ./zcutil/build.sh -j$(nproc)
./contrib/run-tests.sh --strict
mkdir -p ~/.zero && touch ~/.zero/zero.conf && ./src/zerod -daemon
./src/zero-cli getblockchaininfo
```

Windows binaries are cross-built on that Linux host after MXE (BUILD_ZERO "Windows"):

```bash
./zcutil/build.sh -win
```

macOS: BUILD_ZERO "macOS". Configuration beyond the empty `zero.conf`: BUILD_ZERO "Configuration". Tests: TEST_ZERO.

### Optional CPU mining

Mainnet CPU mining is Equihash **(192,7)** on a synced node with peers, a wallet or `-mineraddress`, and `ENABLE_MINING`. Set `equihashsolver=tromp` in `zero.conf` before starting the node (template `prod` sets it); the `default` solver is several times slower. Each mining thread holds one solver's memory: 3.25 GiB for tromp, about 4 GiB for `default`. Keep threads times that size well below physical memory: `genproclimit=-1` starts one thread per core; past physical memory the node swaps, stops answering RPC, and `setgenerate false` and `stop` wait for every solver round to finish. Without restart:

```bash
./src/zero-cli setgenerate true 1
./src/zero-cli getmininginfo
./src/zero-cli setgenerate false
```

`getmininginfo` shows `"generate": true`, and after the first solve a non-zero `localsolps`: solutions per second over all mining time since the node started. `debug.log` shows `ZeroMiner started` and `Running ZeroMiner`. The miner waits while there are no peers or the node is in initial block download. Finding a mainnet block at current difficulty is not expected. To mine after a restart, set `gen=1` in `zero.conf`.

🔩 Running Zero
--------------------

**Help and man pages**

| How | What |
|-----|------|
| `./src/zerod -help` | Option list from the binary |
| `./src/zero-cli -help` | CLI client options |
| `./src/zero-tx -help` | Transaction utility options |
| `man zerod` / `man zero-cli` / `man zero-tx` | The manuals in `doc/man/`, after an install that includes them |

The wallet is created on first start as **`wallet.zero`** in the data directory. [Back up your wallet](https://github.com/zerocurrencycoin/Zero/wiki/Wallet-Backup) often.

Usage is similar to other Zcash-family nodes. Background: [Zcash Basics](https://zcash.readthedocs.io/en/latest/rtd_pages/basics.html).

### Block explorer

Public transparent address, block, and transaction search on mainnet: [https://insight.zeromachine.io/](https://insight.zeromachine.io/)

### Data directory

Data directory and proving-parameter paths per platform: BUILD_ZERO "Paths".
