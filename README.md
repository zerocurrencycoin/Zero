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

**Who should read what**

| I want to... | Start here |
|------------|------------|
| **Trade or hold** | Wallets and exchanges from [zerocurrency.io](https://zerocurrency.io); verify tickers on official channels only. |
| **Mine** | Equihash **(192,7)** -- Zero's PoW (Zcash mainnet uses **(200,9)**). `gen=0` is the operator default. |
| **Run a node** | [Quick start](#-building) below, then BUILD_ZERO "Configuration". |
| **Understand economics** | [ZERO_COIN.md](ZERO_COIN.md) (emission, halvings, development fee, zeronodes). |
| **Contribute** | [CONTRIBUTING.md](CONTRIBUTING.md) · [TEST_ZERO.md](TEST_ZERO.md) · [TODO.md](TODO.md) · [AGENTS.md](AGENTS.md). |

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

Chain facts (detail in [ZERO_COIN.md](ZERO_COIN.md)):

| Topic | Summary |
|--------|---------|
| **Emission** | Block subsidy halves every **800,000** blocks; maximum supply **16,950,149.896 ZER**. |
| **Fee-start** | Height **412,300** -- base subsidy **10 -> 10.8 ZER**; development fee begins. |
| **Halvings** | **800k** (2020), **1.6M** (2023), **2.4M** (2026); next **3.2M**. |
| **Development fee** | **7.5%** of block subsidy from fee-start through height **7,999,999**. |
| **Zeronodes** | **20-40%** of block value by height tier. |

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

Automatic node deprecation (mainnet) is configured on a **~10 year** window from the release baseline (`WEEKS_UNTIL_DEPRECATION` in `src/deprecation.h`). `getdeprecationinfo` reports the deprecation height.


📚 Documentation
----------------

| Document | Readers | Purpose |
|----------|---------|---------|
| [README.md](README.md) | Everyone | Front page, quick start, links |
| [ZERO_COIN.md](ZERO_COIN.md) | Miners, pools, exchanges, integrators | Chain economics, consensus parameters, addresses |
| [BUILD_ZERO.md](BUILD_ZERO.md) | Builders, operators, maintainers | Build, configure, and release on Linux, macOS, and Windows |
| [TEST_ZERO.md](TEST_ZERO.md) | Contributors, maintainers | Test runs, tiers, held scripts, release bar |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributors | Patch and review expectations |
| [TODO.md](TODO.md) | Contributors / maintainers | Open follow-ups for the full node |
| [AGENTS.md](AGENTS.md) | Agents and humans editing the tree | Scope and documentation rules |
| `doc/man/` | Operators (after install) | `zerod`, `zero-cli`, `zero-tx` manuals |
| `doc/release-notes/` | Operators, miners, pools, integrators | Changes per release |
| [doc/zeronodes.md](doc/zeronodes.md) | Maintainers | Zeronode, spork, SwiftTX, and budget implementation |
| [doc/mining-pools.md](doc/mining-pools.md) | Maintainers, pool operators | Coinbase behavior by pool, outreach asks |
| [doc/s-nomp-recipients.md](doc/s-nomp-recipients.md) | Pool operators | s-nomp empty reward recipient: cause, history, fix |

🔧 Building
--------

### Quick start on Linux

Install the packages listed in BUILD_ZERO "Build", then:

```bash
git clone https://github.com/zerocurrencycoin/Zero.git && cd Zero
./zcutil/fetch-params.sh
./zcutil/build.sh -j$(nproc)
mkdir -p ~/.zero && touch ~/.zero/zero.conf
./src/zerod -daemon
./src/zero-cli getblockchaininfo
```

An empty `zero.conf` is enough when `zero-cli` runs on the same host; other setups are in BUILD_ZERO "Configuration". macOS and Windows: BUILD_ZERO "Build".

### Operator checks

```bash
./contrib/ops-validate.sh smoke
```

Starts and restarts an isolated node under `/tmp`; the live data directory is not touched. The other checks are in TEST_ZERO "Operational checks".

### Optional CPU mining

Mainnet CPU mining is Equihash **(192,7)** on a synced node with peers, a wallet or `-mineraddress`, and `ENABLE_MINING`. Without restart:

```bash
./src/zero-cli setgenerate true 1
./src/zero-cli getmininginfo
./src/zero-cli setgenerate false
```

`getmininginfo` shows `"generate": true` and a non-zero `localsolps` once the solver runs; `debug.log` shows `Using Equihash solver` and `Running ZeroMiner`. The miner waits while there are no peers or the node is in initial block download. One solve takes about a minute; finding a mainnet block at current difficulty is not expected. To mine after a restart, set `gen=1` in `zero.conf`.

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

| Platform | Data directory | Proving params |
|----------|----------------|----------------|
| **Linux** | `~/.zero` | `~/.zcash-params` |
| **macOS** | `~/Library/Application Support/zero` | `~/Library/Application Support/ZcashParams` |
| **Windows** | `%APPDATA%\zero` | `%APPDATA%\ZcashParams` |

`-datadir=<path>` moves the data directory.

---

Note: This repository builds the full node only. The Qt Desktop Wallet (**zerowallet**) is a separate application.
