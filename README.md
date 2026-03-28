![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/Zero%20Twitter.jpg?raw=true)

[ZERO](https://zerocurrency.io) - [Latest Release](https://github.com/zerocurrencycoin/Zero/releases/)

### •LAUNCH DATE: 2017-02-19

GENESIS BLOCK - 19th Feb 2017 11:26:40 - 068cbb5db6bc11be5b93479ea4df41fa7e012e92ca8603c315f9b1a2202205c6

------------------------------------------

❓ What is ZERO?
--------------

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/) is a revolutionary cryptocurrency and transaction platform based on Zcash.

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/) offers total payment confidentiality, while still maintaining a decentralised network using a public blockchain.

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/) combines Bitcoin’s security with Zcash’s anonymity and privacy.

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/) stands out from the competition as a fully working product that has already
implemented a set of special features not found in any other cryptocurrency.

Our main focus as a team and community is to remain as transparent as we can possibly be and to maintain an interactive relationship with everyone involved. We are fully open about the project, listening to all suggestions from investors, miners and supporters.

This software is the [ZERO](https://github.com/zerocurrencycoin/Zero/releases/) node. It downloads and stores the entire history of ZERO's transactions, about 2GB at this point.
Depending on the speed of your computer and network connection, the synchronization process could take several hours.

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

||VERY HIGH MINING PROFITABILITY||
------------------------------------------
Zero uses an alternative set of parameters for the Equihash algorithm, which require a GPU with 8GB of RAM. Zero is often one of the most profitable cryptocurrencies to mine.


❓ Is Zero Legal?
-------------------
Zero is legal in most jurisdictions in the world but there are a small number of nation states that have banned its use, such as Ecuador. Wikipedia has a great guide on how Crypto is treated in all countries around the world and explains regulatory policies surrounding it. Regulations vary from one border to the next so you should always research your location’s laws before participating in the network.

❓ Why Trust Zero?
-------------------
Zero is a network operating by the three fundamental principles of technological freedom: Decentralization, Open Source code and true Peer-to-Peer technology. With Privacy being a fundamental human right. Zero’s trust is based on the subjective valuations of human faith in mathematical algorithms, encryption and numbers. With the three pillars of technological principles Zero’s Blockchain is a peer-reviewed system of integrity.

--------------
Zero has a low emission and the inflation degrades over time quickly. Total is under 20M ZERD.

Zero supports both transparent (T) and shielded (Z) addresses.  Privacy is optional, not mandatory.
------------------------------------------

[Zero](https://zero.directory/) is an implementation of the "Zerocash" protocol.
Based on Bitcoin and Zcash code, Zero intends to offer a far higher standard of privacy
through a sophisticated zero-knowledge proving scheme that preserves
confidentiality of transaction metadata. More technical details are available
in the [Protocol Specification](https://github.com/zcash/zips/raw/master/protocol/protocol.pdf).

![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/algo%20zer%20improv.jfif)

------------------------------------------


🔢 Development Fund Breakdown (Per Block Pre-Halfing)
------------------------------------------
0.405 ZER / Block, 291.6 ZER / Day (~7.5%)



📄 White Paper
-----------------------

**** Under Construction

📣 Announcements
-----------------
https://bitcointalk.org/index.php?topic=1796036.0

https://bitcointalk.org/index.php?topic=3310714.0


🔒 Security Warnings
-----------------
See important security warnings on the
[Security Information page](https://z.cash/support/security/).

**Zero is experimental and a work in progress.** Use it at your own risk.

📒 Deprecation Policy
------------------
Disabledeprecation flag has been removed. Nodes running release 4.0.x will automatically shut down in ten years (June 2032).


📚 Documentation
----------------

**Map vs editors:** The table below is the **full** in-repo documentation index (purpose and focus). **[AGENTS.md](AGENTS.md)** defines a **definitive user-facing** subset for builders, operators, and contributors—narrower than this map.

**README0.md** is intentionally **omitted**: temporary working draft for README reshaping, not canonical.

```
                    README
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   BUILD_ZERO     TEST_ZERO     CONTRIBUTING
        │              │              │
        └──────────────┴──────────────┘
                        │
                        ▼
                      TODO
        ┌────────────────┴────────────────┐
        ▼                                 ▼
   ZERO_COIN.md                     Subsidy.md
   (+ ZeroCoin outline)             (split / retire)
```

| Document | Purpose | Focus |
|----------|---------|-------|
| [README.md](README.md) | Project front page; links and quick start | What Zero is, where to build, contribute, and read deeper docs |
| [BUILD_ZERO.md](BUILD_ZERO.md) | Build and platform guide | Linux, macOS ARM64, Windows, depends, troubleshooting, release-style artifacts |
| [TEST_ZERO.md](TEST_ZERO.md) | Validation runbook for **builders and contributors** | How to run tests, tiers, flags, wrappers, script lists, fork-specific expectations (e.g. 720 maturity) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution workflow | Patches, review, coding expectations |
| [TODO.md](TODO.md) | Checklist and follow-ups | Implementation status, doc debt, small tracked tasks |
| [ZERO_COIN.md](ZERO_COIN.md) | **User-facing** chain and node reference | Observable behavior, events, operations; **Glossary** and **References**; body grows from **[ZeroCoin.md](ZeroCoin.md)** outline and **Subsidy** split |
| [ZeroCoin.md](ZeroCoin.md) | **Outline** toward **ZERO_COIN** | Section checklist and maintenance notes until merged into **ZERO_COIN.md** |
| [Subsidy.md](Subsidy.md) | **Legacy** technical reference | Subsidy math, halving, founders, zeronode split, supply notes; content is **being split** into user-facing docs (e.g. **ZERO_COIN.md**) and other homes, then **retired**—prefer the map targets over new edits here when possible |
| [Zeronode_wallet.md](Zeronode_wallet.md) | Wallet integration note | `CZeronodeWalletInterface`, wallet-optional builds, coverage notes for zeronode↔wallet |
| `doc/man/` | Shipped CLI manuals | `zerod`, `zero-cli`, `zero-tx` options and behavior |


🔧 Building
--------

**User types:** New to Zero? Run the Quick Start below. Building on macOS or Windows? See [BUILD_ZERO.md](BUILD_ZERO.md). Want to contribute? See [CONTRIBUTING.md](CONTRIBUTING.md).

### Quick start on Linux

```bash
sudo apt install build-essential pkg-config libc6-dev m4 g++-multilib autoconf libtool ncurses-dev unzip git python3 python3-zmq zlib1g-dev wget bsdmainutils automake cmake curl
git clone https://github.com/zerocurrencycoin/Zero.git && cd Zero
./zcutil/fetch-params.sh
./zcutil/build.sh
./src/zerod -daemon
```

macOS and Windows: see [BUILD_ZERO.md](BUILD_ZERO.md).

### Create a Zero configuration file
```
mkdir -p ~/.zero
echo "server=1" > ~/.zero/zero.conf
```
### To use the full node RPC interface
```
echo "rpcuser=<YOUR_USER_NAME>" > ~/.zero/zero.conf
echo "rpcpassword=`head -c 32 /dev/urandom | base64`" >> ~/.zero/zero.conf
echo "rpcport=23801" >> ~/.zero/zero.conf
```

### Optional CPU mining
```
echo 'gen=1' >> ~/.zero/zero.conf
echo "genproclimit=1" >> ~/.zero/zero.conf
echo 'equihashsolver=tromp' >> ~/.zero/zero.conf
```

### Earlier zero.conf sample
```
./contrib/zero.conf
```
### zero.conf sample with many options
```
./contrib/debian/examples/zero.conf
```

🔩 Running Zero
--------------------
After building, binaries are in `./src`. Run the daemon in the background:

```
./src/zerod -daemon
```

Command-line options: `./src/zerod -help` (or set in zero.conf).

Your wallet is created on first run in `~/.zero/wallet.zero`. [Backup your wallet](https://github.com/zerocurrencycoin/Zero/wiki/Wallet-Backup) often.

The usage is currently very similar to Zcash. For more information see the [Zcash User Guide](https://github.com/zcash/zcash/wiki/1.0-User-Guide#running-zcash).

