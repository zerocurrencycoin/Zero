concept![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/Zero%20Twitter.jpg?raw=true)

[ZERO](https://zerocurrency.io) - [Latest Release](https://github.com/zerocurrencycoin/Zero/releases/)

### •LAUNCH DATE: 2017-02-19

GENESIS BLOCK - 19th Feb 2017 11:26:40 - `068cbb5db6bc11be5b93479ea4df41fa7e012e92ca8603c315f9b1a2202205c6`

------------------------------------------

❓ What is ZERO?
--------------

[ZERO](https://zerocurrency.io) is a privacy-focused cryptocurrency and transaction platform in the Zcash family.

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/) offers strong payment confidentiality while maintaining a decentralised network on a public blockchain.

[ZERO](https://github.com/zerocurrencycoin/Zero) combines Bitcoin-style security with Zerocash-style shielded privacy. Transparent (t-addr) and shielded (z-addr) payments coexist; privacy is optional, not mandatory.

This repository is the **full node** (`zerod`, `zero-cli`, `zero-tx`). It downloads and stores the history of ZERO transactions. Sync time depends on your computer and network; plan for a substantial first sync.

**Who should read what**

| I want to... | Start here |
|------------|------------|
| **Trade or hold** | Wallets and exchanges from [zerocurrency.io](https://zerocurrency.io); verify tickers on official channels only. |
| **Mine** | Equihash **(192,7)** -- Zero's PoW (Zcash mainnet uses **(200,9)**). `gen=0` is the operator default. |
| **Run a node** | [Quick start](#-building) below, then [BUILD_ZERO.md](BUILD_ZERO.md). |
| **Understand economics** | [ZERO_COIN.md](ZERO_COIN.md) (emission, halvings, founders, zeronodes). |
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

Zero uses Equihash **(192, 7)**, which typically needs a GPU with about **8 GB** of RAM for meaningful mining.

Chain facts (authoritative detail in [ZERO_COIN.md](ZERO_COIN.md)):

| Topic | Summary |
|--------|---------|
| **Emission** | Block subsidy with halvings every **800,000** blocks (pre-Blossom); target supply on the order of **~20M ZER**. |
| **Fee-start** | Height **412,300** -- base subsidy **10 -> 10.8 ZER**; founders carve begins. |
| **Halvings** | **800k** (2020), **1.6M** (2023), **2.4M** (2026); next **3.2M**. |
| **Founders** | **7.5%** of block subsidy while eligible (through height **7,999,999**). |
| **Zeronodes** | **20-40%** of block value by height tier when sporks enable payments. |

------------------------------------------

❓ Is Zero Legal?
-------------------
Zero is legal in most jurisdictions, but some nation states restrict or ban cryptocurrency use. Regulations vary; research your local law before participating.

❓ Why Trust Zero?
-------------------
Zero aims at decentralisation, open source, and peer-to-peer operation, with privacy as a core design goal. Trust rests on open review of the code and cryptography, not on a single vendor.

--------------

[Zero](https://zero.directory/) implements the Zerocash protocol family. More technical detail: [Zcash Protocol Specification](https://github.com/zcash/zips/raw/master/protocol/protocol.pdf).

![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/algo%20zer%20improv.jfif)

------------------------------------------


🔢 Development Fund
------------------------------------------
**7.5%** of block subsidy in eligible heights. See [ZERO_COIN.md -- Founders reward](ZERO_COIN.md#founders-reward-75).


📣 Announcements
-----------------
https://bitcointalk.org/index.php?topic=1796036.0

https://bitcointalk.org/index.php?topic=3310714.0


🔒 Security Warnings
-----------------
See important security warnings on the
[Security Information page](https://z.cash/support/security/).

**Zero is experimental and a work in progress.** Use it at your own risk.

Automatic node deprecation (mainnet) is configured on a **~10 year** window from the release baseline (`WEEKS_UNTIL_DEPRECATION` in `src/deprecation.h`). Query live values with `getdeprecationinfo`. This is **not** a near-term operator concern for current releases.


📚 Documentation
----------------

**Ship set** (product distribution / public docs). Cross-links among these files only.

| Document | Readers | Purpose |
|----------|---------|---------|
| [README.md](README.md) | Everyone | Front page, quick start, links |
| [ZERO_COIN.md](ZERO_COIN.md) | Miners, exchanges, operators, integrators | Chain economics, addresses, glossary |
| [BUILD_ZERO.md](BUILD_ZERO.md) | Builders | Linux / macOS / Windows build and troubleshooting |
| [TEST_ZERO.md](TEST_ZERO.md) | Contributors | Validation runbook and working inventory |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributors | Patch and review expectations |
| [TODO.md](TODO.md) | Contributors / maintainers | Open follow-ups for the full node |
| [AGENTS.md](AGENTS.md) | Agents and humans editing the tree | Scope and documentation rules |
| `doc/man/` | Operators (after install) | `zerod`, `zero-cli`, `zero-tx` manuals |

```
                    README
                       │
        ┌──────────────┼──────────────┬────────────┐
        ▼              ▼              ▼            ▼
   BUILD_ZERO     TEST_ZERO     CONTRIBUTING    AGENTS
        │              │              │
        └──────────────┴──────────────┘
                       │
                       ▼
                     TODO
                       ▼
                   ZERO_COIN.md
             (chain + node reference)
```


🔧 Building
--------

### Quick start on Linux

```bash
sudo apt install build-essential pkg-config libc6-dev m4 g++-multilib autoconf libtool ncurses-dev unzip git python3 python3-zmq zlib1g-dev wget bsdmainutils automake cmake curl
git clone https://github.com/zerocurrencycoin/Zero.git && cd Zero
./zcutil/fetch-params.sh
./zcutil/build.sh
./src/zerod -daemon
```

macOS and Windows: see [BUILD_ZERO.md](BUILD_ZERO.md).

### Operator checks

Config, then an isolated lab cycle under `/tmp` (not the live datadir):

```bash
./contrib/zero-conf.sh prod -dir ~/.zero
./contrib/ops-validate.sh smoke
```

`smoke` is cold start + restart. `./contrib/ops-validate.sh short` adds Equihash KATs and `verifyeq`. Timed (192,7) solves are `solveeq` (default 1; pass N). Isolated regtest `generate` is `mine` (not mainnet). Load soaks (`reindex`, `bootstrap`, `copy`) stay separate. If a leftover `zerod` or RPC port is in the way, stop it or pass `--force`.

From-source merge check: `./contrib/run-tests.sh --strict`. Maintainer inventory: [TEST_ZERO.md](TEST_ZERO.md).

### Data directory (`zero.conf`, wallet, chain)

Canonical defaults (`GetDefaultDataDir()` / `ZC_GetBaseParamsDir()` in `src/util.cpp`):

| Platform | Data directory | Proving params |
|----------|----------------|----------------|
| **Linux** | `~/.zero` | `~/.zcash-params` |
| **macOS** | `~/Library/Application Support/zero` | `~/Library/Application Support/ZcashParams` |
| **Windows** | `%APPDATA%\zero` (e.g. `C:\Users\USERNAME\AppData\Roaming\zero`) | `%APPDATA%\ZcashParams` (sibling of `zero`, **not** under it) |

Replace **`USERNAME`** with your login. Override datadir with `-datadir=<path>`. Wallet file: **`wallet.zero`** inside the datadir.

**Linux** -- create config (or `./contrib/zero-conf.sh prod -dir ~/.zero`):

```bash
mkdir -p ~/.zero
echo "server=1" > ~/.zero/zero.conf
echo "rpcuser=YOUR_NAME" >> ~/.zero/zero.conf
echo "rpcpassword=$(head -c 32 /dev/urandom | base64)" >> ~/.zero/zero.conf
echo "rpcport=23811" >> ~/.zero/zero.conf
```

**macOS**:

```bash
mkdir -p "$HOME/Library/Application Support/zero"
echo "server=1" > "$HOME/Library/Application Support/zero/zero.conf"
```

**Windows** (PowerShell):

```powershell
mkdir $env:APPDATA\zero
echo server=1 > $env:APPDATA\zero\zero.conf
```

### Full node RPC (Linux)

With `server=1` and RPC credentials in `zero.conf`:

```bash
./src/zero-cli getblockchaininfo
./src/zero-cli help
```

### Optional CPU mining

Template **prod** ships `gen=0`. Isolated tests (`ops-validate.sh mine`, Boost `miner_tests`) are **regtest (48,5)** and do not mine the live chain. Mainnet CPU mining is Equihash **(192,7)** on a synced node with peers, a wallet or `-mineraddress`, and `ENABLE_MINING`.

Without restart, on the operator node:

```bash
./src/zero-cli setgenerate true 1
./src/zero-cli getmininginfo
./src/zero-cli setgenerate false
```

`getmininginfo` should show `"generate": true` and a non-zero `localsolps` once the solver is running. `debug.log` should contain `Using Equihash solver` and `Running ZeroMiner`. The miner waits if there are no peers or the node is still in initial block download. Finding a mainnet block at current difficulty is not expected.

To persist across restart, set `gen=1` and `genproclimit=1` in `zero.conf` (already present as `gen=0` / `genproclimit=1` / `equihashsolver=tromp` in the prod template). Use `setgenerate false` or `gen=0` to stop.

### Config samples

`./contrib/zero-conf.sh` writes `contrib/conf-templates/` (default **prod**, `/tmp/zero.conf`, generated `rpcpassword`). In-tree samples: `./contrib/zero.conf`, `./contrib/debian/examples/zero.conf`.

🔩 Running Zero
--------------------
After building, binaries are in `./src`. Run the daemon in the background:

```
./src/zerod -daemon
```

**Help and man pages**

| How | What |
|-----|------|
| `./src/zerod -help` | Built-in option list (always available from the binary) |
| `./src/zero-cli -help` | CLI client options |
| `./src/zero-tx -help` | Transaction utility options |
| `man zerod` / `man zero-cli` / `man zero-tx` | Same material as installed manuals under **`doc/man/`** (after `make install` or packaging that installs man pages) |

During development from a build tree, prefer **`-help`**. After a system install that includes man pages, **`man zerod`** is the usual operator path.

Your wallet is created on first run as **`wallet.zero`** in the data directory (see table above). [Backup your wallet](https://github.com/zerocurrencycoin/Zero/wiki/Wallet-Backup) often.

Usage is similar to other Zcash-family nodes. Background: [Zcash Basics](https://zcash.readthedocs.io/en/latest/rtd_pages/basics.html).

### Block explorer
Public transparent address / block / transaction search.

Mainnet: [https://insight.zeromachine.io/](https://insight.zeromachine.io/)

---

Note: This repository builds the full node only. The Qt Desktop Wallet (**zerowallet**) is a separate application.

