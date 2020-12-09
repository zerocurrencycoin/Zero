![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/zero%203d%20mountain.png?raw=true)

[ZERO](https://zerocurrency.io) - [Draco:3.2.0](https://github.com/zerocurrencycoin/Zero/releases/tag/v3.2.0)

||FAST|| ||DECENTRALISED|| ||ANONYMOUS|| ||SECURE|| ||ASIC RESISTANT|| ||SCARCE|| - LAUNCH DATE: 2017-02-19

GENESIS BLOCK - 19th Feb 2017 11:26:40 - 068cbb5db6bc11be5b93479ea4df41fa7e012e92ca8603c315f9b1a2202205c6

Download [ZERO - Latest Version - Draco:3.2.0](https://github.com/zerocurrencycoin/Zero/releases/tag/v3.2.0)

------------------------------------------

❓ What is ZERO?
--------------

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/tag/v3.2.0) is a revolutionary cryptocurrency and transaction platform based on Zcash.

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/tag/v3.2.0) offers total payment confidentiality, while still maintaining a decentralised network using a public blockchain.

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/tag/v3.2.0) combines Bitcoin’s security with Zcash’s anonymity and privacy.

[ZERO](https://github.com/zerocurrencycoin/Zero/releases/tag/v3.2.0) stands out from the competition as a fully working product that has already
implemented a set of special features not found in any other cryptocurrency.

Our main focus as a team and community is to remain as transparent as we can possibly be and to maintain an interactive relationship with everyone involved. We are fully open about the project, listening to all suggestions from investors, miners and supporters.

This software is the [ZERO](https://github.com/zerocurrencycoin/Zero/releases/tag/v3.2.0) node. It downloads and stores the entire history of ZERO's transactions, about 1.2GB at this point.
Depending on the speed of your computer and network connection, the synchronization process could take several hours.

------------------------------------------

![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/zero-logo-shade-black_256x256.png)


💫 ZERO CORE FEATURES
-------------------

||ZERO COST||
--------------
Zero’s transaction fees are 0.0001 ZER, when the networks capacity is high. When Zero’s network is below full capacity the fee reduces to 0.


||NO PREMINE||
--------------
0% advantage for early adopters. No Pre-Mined Zero, therefore people that buy or mine today have no disadvantages.


||SECURE||
----------------------------
Zero implements zk-SNARKs, a state of the art privacy technology pioneered by cryptographers at Zcash, with substantial security guarantees, according to a consensus of a significant number of nonbiased experts in the field.


||ASIC RESISTANT||
----------------------------
Zero is ASIC resistant due to increased difficulty settings (192/7) in its Equihash algorithm implementation, keeping specialized mining hardware away.


||SHIELDED TRANSACTIONS||
----------------------------
Zero has a feature called shielded transactions that ensures full anonymity when sending funds.


||HIGH MINING PROFITABILITY||
------------------------------------------
Zero uses an alternative set of parameters taken from the equihash algorithm, this needs atleast 4GB/8GB of RAM. Zero is one of the most profitable cryptocurrency’s to mine.


||DECENTRALISED PAYMENTS||
----------------------------
Zero is founded on a decentralised platform, there are no borders. Zero facilitates lightning fast and anonymous money transfers worldwide, without any restrictions or interference from 3rd parties.


||INFLATION||
--------------
Zero has a low inflation that decreases over time, with a stable supply of 3888 ZER per day, after our first halving.
Total supply of ZER will be a very low 17,000,000 coins.

------------------------------------------

![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/tech%20improv%20zero.jfif)

[Zero](https://z.cash/) is an implementation of the "Zerocash" protocol.
Based on Bitcoin's code, Zero intends to offer a far higher standard of privacy
through a sophisticated zero-knowledge proving scheme that preserves
confidentiality of transaction metadata. More technical details are available
in our [Protocol Specification](https://github.com/zcash/zips/raw/master/protocol/protocol.pdf).

![alt text](https://github.com/zerocurrencycoin/Zero/blob/master/art/algo%20zer%20improv.jfif)

------------------------------------------


🔢 Development Fund Breakdown
------------------------------------------
0.405 ZER / Block, 291.6 ZER / Day (~7.5%)


📄 White Paper - Extended
-----------------------

http://docdro.id/n9j4sJr


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
'disabledeprecation' flag has been removed. Old nodes will automatically be shut down and must be upgraded upon reaching the deprecation block height, which will occur approximately 26 weeks (6/26/2021) from the release of v3.2.0.


🔧 Building
--------
Currently only Linux build is officially supported.  8GB RAM is recommended.

### Install packages (needs to be done only once)
```
sudo apt-get install \
      build-essential pkg-config libc6-dev m4 g++-multilib \
      autoconf libtool ncurses-dev unzip git python python-zmq \
      zlib1g-dev wget bsdmainutils automake cmake curl
```

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
To use the full node RPC interface
```
echo "rpcuser=<YOUR_USER_NAME>" > ~/.zero/zero.conf
echo "rpcpassword=`head -c 32 /dev/urandom | base64`" >> ~/.zero/zero.conf
echo "rpcport=23801" >> ~/.zero/zero.conf
```

#### Enable CPU mining (optional)
```
echo 'gen=1' >> ~/.zero/zero.conf
echo "genproclimit=1" >> ~/.zero/zero.conf
echo 'equihashsolver=tromp' >> ~/.zero/zero.conf
```

An earlier sample of zero.conf
```
./contrib/zero.conf
```
A sample demonstrating many command line options
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
For license information see the file [COPYING](COPYING).
