# Building Zero on Raspberry Pi 5

This guide is for building Zero cryptocurrency on Raspberry Pi 5 with 64-bit Raspberry Pi OS.

## System Requirements

- **Raspberry Pi 5** (ARM64/aarch64)
- **2GB+ RAM** (4GB or 8GB recommended)
- **20GB+ free disk space**
- **64-bit Raspberry Pi OS**
- **Active swap** (important for 2GB models)

## Important Notes for Raspberry Pi

⚠️ **Memory Considerations:**
- With 2GB RAM, the build process will be slow and may use swap heavily
- The optimized build script uses only `-j2` (2 parallel jobs) to avoid out-of-memory errors
- Build time: **3-6 hours** depending on Pi model and memory
- Consider increasing swap if you encounter memory issues

⚠️ **Thermal Management:**
- Long compilation will heat up your Pi
- Ensure adequate cooling (heatsink or active cooling recommended)
- Monitor temperature: `vcgencmd measure_temp`

## One-Time Setup

### 1. Install Build Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential pkg-config libc6-dev m4 \
    autoconf libtool ncurses-dev unzip git python3 \
    zlib1g-dev wget bsdmainutils automake cmake curl \
    libboost-all-dev libevent-dev libsodium-dev \
    libzmq3-dev libutfcpp-dev
```

### 2. Install Rust (Required for librustzcash)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
rustup install 1.70.0
rustup default 1.70.0
```

### 3. Download Cryptographic Parameters

```bash
cd /path/to/zero
./zcutil/fetch-params.sh
```

This downloads the zkSNARK parameters (about 1.7GB). Do this only once.

## Building Zero

### Step 1: Build Berkeley DB 6.2.32 (Required for Wallet)

Zero requires Berkeley DB 6.2 for wallet support:

```bash
cd /path/to/zero
./zcutil/build-bdb.sh
```

This takes about 10-15 minutes and builds BDB to `./db6/`

### Step 2: Build Zero with Wallet Support

Use the automated Raspberry Pi build script:

```bash
./zcutil/build-rpi-wallet-v2.sh
```

This will:
- Verify Berkeley DB 6.2.32 installation
- Install required system packages (libutfcpp-dev)
- Apply source code fixes for modern compilers
- Extract and build librustzcash with Rust 1.70.0
- Configure Zero with wallet support enabled
- Build all binaries (zerod, zero-cli, zero-tx)
- Use only 2 parallel jobs to conserve memory
- Optimize for Cortex-A76 CPU (Raspberry Pi 5)

**Estimated time:** 3-6 hours on Pi 5 with 2GB RAM

### Alternative: Build Without Dependencies

If you already have all dependencies and just need to rebuild:

```bash
make clean
make -j2
```

## Monitoring the Build

### In Another Terminal

Monitor memory usage:
```bash
watch -n 5 free -h
```

Monitor temperature:
```bash
watch -n 5 vcgencmd measure_temp
```

Monitor CPU usage:
```bash
htop
```

## If Build Fails

### Out of Memory Errors

If you see errors like "c++: fatal error: Killed signal terminated program cc1plus":

1. **Increase swap space:**
```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE=2048 to CONF_SWAPSIZE=4096
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

2. **Reduce parallel jobs in build script:**
Edit `zcutil/build-rpi-wallet-v2.sh` and change `make -j2` to `make -j1`

3. **Close other applications** to free up memory

### Missing Dependencies

If you see "fatal error: utf8.h: No such file or directory":
```bash
sudo apt-get install -y libutfcpp-dev
```

The build script should handle this automatically, but install manually if needed.

### Rust Version Issues

The build requires Rust 1.70.0 specifically for librustzcash compatibility:
```bash
rustup install 1.70.0
rustup default 1.70.0
source ~/.cargo/env
```

### Clean and Rebuild

If something goes wrong:
```bash
make clean
./zcutil/build-rpi-wallet-v2.sh
```

Complete clean (including Berkeley DB):
```bash
rm -rf db6/ db-6.2.32/
./zcutil/build-bdb.sh
./zcutil/build-rpi-wallet-v2.sh
```

## After Successful Build

The compiled binaries will be in `./src/`:
- `zerod` - Zero daemon (full node)
- `zero-cli` - Command-line interface
- `zero-tx` - Transaction creation utility

### Test the Build

```bash
./src/zerod --version
./src/zero-cli --version
./src/zero-tx --version
```

### Install System-Wide (Optional)

```bash
sudo make install
```

This installs binaries to `/usr/local/bin/`

## Running Zero

### Create Configuration

```bash
mkdir -p ~/.zero
cat > ~/.zero/zero.conf <<EOF
server=1
rpcuser=zerorpc
rpcpassword=$(head -c 32 /dev/urandom | base64)
rpcport=23801
# Use less memory on Pi
dbcache=100
maxmempool=50
EOF
```

### Start the Daemon

```bash
./src/zerod --daemon
```

### Check Status

```bash
./src/zero-cli getinfo
./src/zero-cli getblockchaininfo
```

### Stop the Daemon

```bash
./src/zero-cli stop
```

## Performance Tips for Raspberry Pi

1. **Use external SSD/USB drive** for blockchain data (faster than SD card)
2. **Increase dbcache** if you have 4GB+ RAM (edit zero.conf)
3. **Run zerod with nice priority** to keep system responsive:
   ```bash
   nice -n 10 ./src/zerod --daemon
   ```
4. **Monitor disk space** - blockchain grows over time
5. **Use cooling** - crypto operations generate heat

## Troubleshooting

### "configure: error: libsodium not found"
The build script installs this via apt. If you see this error:
```bash
sudo apt-get install -y libsodium-dev
```

### "fatal error: librustzcash.h: No such file or directory"
The librustzcash build failed or wasn't installed. Check:
```bash
ls -la src/rust/lib/librustzcash.a
ls -la src/rust/include/librustzcash.h
```

If missing, rebuild librustzcash manually:
```bash
cd depends/work/build/aarch64-unknown-linux-gnu/librustzcash/0.1-af991e044ee
source ~/.cargo/env
cargo build --release
```

### Wallet Not Enabled
If wallet commands don't work, verify BDB is installed:
```bash
ls -la db6/lib/libdb_cxx.a
```

If missing, run `./zcutil/build-bdb.sh` first.

### Slow Blockchain Sync
Initial sync can take days on Pi. Be patient. You can:
- Use `getblockchaininfo` to monitor progress
- Consider using bootstrap.dat if available
- Ensure good internet connection

### High Temperature
If Pi throttles due to heat:
- Add heatsinks or cooling fan
- Reduce parallel jobs: `-j1` instead of `-j2`
- Run builds during cooler times of day

## Architecture Details

- **Target:** aarch64-unknown-linux-gnu (ARM64)
- **CPU Optimizations:** `-mcpu=cortex-a76` (Raspberry Pi 5)
- **Parallel Jobs:** 2 (for 2GB RAM models)
- **Wallet Support:** Enabled with Berkeley DB 6.2.32
- **Rust Version:** 1.70.0 (for librustzcash compatibility)
- **Compiler Fixes Applied:**
  - Added `boost::placeholders` namespace for Boost 1.83+
  - Added `<deque>` header for std::deque
  - Added `<stdexcept>` header for std::invalid_argument

## Getting Help

- Zero GitHub: https://github.com/zerocurrencycoin/zero
- This build tested on: Raspberry Pi 5 (2GB), Raspberry Pi OS 64-bit (Debian Trixie, kernel 6.6)
- GCC 14.2.0, Boost 1.83, Rust 1.70.0
