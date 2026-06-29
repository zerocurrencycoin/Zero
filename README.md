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

Zero uses an alternative set of parameters for the Equihash algorithm (192, 7), which require a GPU with 8GB of RAM.


❓ Is Zero Legal?
-------------------
Zero is legal in most jurisdictions in the world but there are a small number of nation states that have banned its use, such as Ecuador. Wikipedia has a great guide on how Crypto is treated in all countries around the world and explains regulatory policies surrounding it. Regulations vary from one border to the next so you should always research your location’s laws before participating in the network.

❓ Why Trust Zero?
-------------------
Zero is a network operating by the three fundamental principles of technological freedom: Decentralization, Open Source code and true Peer-to-Peer technology. With Privacy being a fundamental human right. Zero’s trust is based on the subjective valuations of human faith in mathematical algorithms, encryption and numbers. With the three pillars of technological principles Zero’s Blockchain is a peer-reviewed system of integrity.

--------------
Zero has a low emission rate that degrades over time. See [ZERO_COIN.md — Total supply](ZERO_COIN.md#total-supply-and-max_money).

Zero supports both transparent (T) and shielded (Z) addresses.  Privacy is optional, not mandatory.
------------------------------------------

[Zero](https://zero.directory/) is an implementation of the "Zerocash" protocol.
Based on Bitcoin and Zcash code, Zero intends to offer a far higher standard of privacy
through a sophisticated zero-knowledge proving scheme that preserves
confidentiality of transaction metadata. More technical details are available
in the [Protocol Specification](https://github.com/zcash/zips/raw/master/protocol/protocol.pdf).

![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/algo%20zer%20improv.jfif)

------------------------------------------


🔢 Development Fund
------------------------------------------
7.5% of block subsidy in eligible heights. See [ZERO_COIN.md -- Founders reward](ZERO_COIN.md#founders-reward-75).



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
                        ▼
                   ZERO_COIN.md
                (chain + node reference)
```

| Document | Purpose | Focus |
|----------|---------|-------|
| [README.md](README.md) | Project front page; links and quick start | What Zero is, where to build, contribute, and read deeper docs |
| [BUILD_ZERO.md](BUILD_ZERO.md) | Build and platform guide | Linux, macOS ARM64, Windows, depends, troubleshooting, release-style artifacts |
| [TEST_ZERO.md](TEST_ZERO.md) | Validation runbook | Runners, modes, Tier A gate, pass-only filters, known failures, 720 maturity |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution workflow | Patches, review, coding expectations |
| [TODO.md](TODO.md) | Checklist and follow-ups | Implementation status, doc debt, small tracked tasks |
| [ZERO_COIN.md](ZERO_COIN.md) | **User-facing** chain and node reference | Observable behavior, events, operations; **Glossary** and **References**; emission, halving, founders, zeronodes, addresses |
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

### Data directory (`zero.conf`, wallet, chain)

Canonical defaults (`GetDefaultDataDir()` in `src/util.cpp`):

| Platform | Data directory | Proving params |
|----------|----------------|----------------|
| **Linux** | `~/.zero` | `~/.zcash-params` |
| **macOS** | `/Users/USERNAME/Library/Application Support/zero` | `/Users/USERNAME/Library/Application Support/ZcashParams` |
| **Windows** | `C:\Users\USERNAME\AppData\Roaming\zero` | `C:\Users\USERNAME\AppData\Roaming\zero\ZcashParams` |

Replace **`USERNAME`** with your login. Override with `-datadir=<path>`. Wallet: **`wallet.zero`** inside the datadir.

**Linux** -- create config:

```bash
mkdir -p ~/.zero
echo "server=1" > ~/.zero/zero.conf
echo "rpcuser=YOUR_NAME" >> ~/.zero/zero.conf
echo "rpcpassword=$(head -c 32 /dev/urandom | base64)" >> ~/.zero/zero.conf
echo "rpcport=23801" >> ~/.zero/zero.conf
```

**macOS**:

```bash
mkdir -p "/Users/$(whoami)/Library/Application Support/zero"
echo "server=1" > "/Users/$(whoami)/Library/Application Support/zero/zero.conf"
# Or explicit override:
# ./src/zerod -datadir="$HOME/.zero" -daemon
```

**Windows** (PowerShell):

```powershell
mkdir $env:APPDATA\zero
echo server=1 > $env:APPDATA\zero\zero.conf
# Expanded: C:\Users\USERNAME\AppData\Roaming\zero\zero.conf
```

### To use the full node RPC interface (Linux)

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

Your wallet is created on first run as **`wallet.zero`** in the data directory (see table above). [Backup your wallet](https://github.com/zerocurrencycoin/Zero/wiki/Wallet-Backup) often.

The usage is currently very similar to Zcash. For more information see the [Zcash User Guide](https://github.com/zcash/zcash/wiki/1.0-User-Guide#running-zcash).

