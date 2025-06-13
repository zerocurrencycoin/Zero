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
Zero has a low emission and the inflation degrades over time quickly. Stable supply is 3888 ZER, after first halfing.

------------------------------------------

[Zero](https://zero.directory/) is an implementation of the "Zerocash" protocol.
Based on Bitcoin's code, Zero intends to offer a far higher standard of privacy
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
Disabledeprecation flag has been removed. Nodes running release 3.3.1 will automatically shut down in ten years (June 2032).


🔧 Building
--------

### **📚 Build Documentation**

For comprehensive build instructions, see our detailed documentation:

- **[BUILD.md](BUILD.md)** - Complete build guide for all platforms (Linux, macOS, Windows)
- **[BUILD_COMPATIBILITY.md](BUILD_COMPATIBILITY.md)** - GCC compatibility notes and fixes
- **[TODO.md](TODO.md)** - Implementation status and architectural improvements  
- **[ZERONODE_WALLET_INTERFACE.md](ZERONODE_WALLET_INTERFACE.md)** - Architecture documentation

### **⚡ Quick Start (Linux)**

**System Requirements:** 8GB RAM recommended, GCC 7.0+

**Install packages (one-time setup):**
```bash
sudo apt-get install \
      build-essential pkg-config libc6-dev m4 g++-multilib \
      autoconf libtool ncurses-dev unzip git python3 python3-zmq \
      zlib1g-dev wget bsdmainutils automake cmake curl
```

**Note:** For detailed instructions including Windows builds, GPU dependencies, and troubleshooting, see **[BUILD.md](BUILD.md)**.

### Obtain the ZERO software from GitHub
```
git clone https://github.com/zerocurrencycoin/zero.git
cd zero
git checkout master
```

### Download cryptographic keys (needs to be done only once)
```
./zcutil/fetch-params.sh
```

### Build the source code to produce binary executables:
```
./zcutil/build.sh -j$(nproc)
```
On a typical laptop -j2 works fine, while retaining some UI interactivity

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

### Enable CPU mining (optional)
```
echo 'gen=1' >> ~/.zero/zero.conf
echo "genproclimit=1" >> ~/.zero/zero.conf
echo 'equihashsolver=tromp' >> ~/.zero/zero.conf
```

### An earlier sample of zero.conf
```
./contrib/zero.conf
```
### A sample demonstrating many command line options
```
./contrib/debian/examples/zero.conf
```

🔩 Running Zero
--------------------
After successfully building, the Zero binaries are stored in `./src`. The two important binaries are `zerod` and `zero-cli`.
To run zerod in the background
```
./zerod --daemon
``` 
To see command line options (also available in zero.conf file)
```
./zerod -?
``` 
Your wallet will be created (on first zerod run) in: ~/.zero/wallet.zero
Please, [backup your wallet](https://github.com/zerocurrencycoin/Zero/wiki/Wallet-Backup) often and keep it safe and secret.

The usage is currently very similar to Zcash. For more information see the [Zcash User Guide](https://github.com/zcash/zcash/wiki/1.0-User-Guide#running-zcash).

📜 License
-------
