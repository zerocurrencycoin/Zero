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
    zlib1g-dev wget bsdmainutils automake cmake curl
```

### 2. Download Cryptographic Parameters

```bash
cd ~/gcc-projects/zero
./zcutil/fetch-params.sh
```

This downloads the zkSNARK parameters (about 1.7GB). Do this only once.

## Building Zero

### Quick Build (Recommended for Pi)

Use the optimized Raspberry Pi build script:

```bash
cd ~/gcc-projects/zero
./zcutil/build-rpi.sh
```

This will:
- Automatically detect ARM64 architecture
- Use only 2 parallel jobs to conserve memory
- Disable tests and benchmarks by default (to save time/memory)
- Optimize for Cortex-A76 CPU (Raspberry Pi 5)
- Build dependencies and Zero binaries

**Estimated time:** 3-6 hours on Pi 5 with 2GB RAM

### Build with Tests (Not Recommended for 2GB Pi)

If you have 4GB+ RAM and want to build tests:

```bash
./zcutil/build-rpi.sh --with-tests
```

### Build Without Mining Support

To save some compilation time and binary size:

```bash
./zcutil/build-rpi.sh --disable-mining
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

2. **Try building with just 1 job:**
```bash
./zcutil/build-rpi.sh -j1
```

3. **Close other applications** to free up memory

### Clean and Rebuild

If something goes wrong:
```bash
make clean  # Clean previous build
./zcutil/build-rpi.sh  # Start fresh
```

Complete clean (including dependencies):
```bash
make -C depends clean
make clean
./zcutil/build-rpi.sh
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
The build script builds this dependency automatically. If you see this, dependencies didn't build correctly. Try:
```bash
make -C depends clean
./zcutil/build-rpi.sh
```

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

- **Target:** aarch64-unknown-linux-gnu
- **CPU Optimizations:** `-mcpu=cortex-a76 -mtune=cortex-a76`
- **Parallel Jobs:** 2 (for 2GB RAM models)
- **Tests/Benchmarks:** Disabled by default

## Getting Help

- Zero GitHub: https://github.com/zerocurrencycoin/zero
- Zero Discord/Community: Check zero website
- This build tested on: Raspberry Pi 5 (2GB), Raspberry Pi OS 64-bit (Debian Trixie)
