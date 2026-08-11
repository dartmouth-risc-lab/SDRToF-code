# USRP N210 Software Build Instructions

## Prerequisites
- GCC compiler or compatible toolchain
- CMake 3.10+
- UHD (USRP Hardware Driver) development libraries
- Boost libraries

## Connect USRP Device via Ethernet

1. **Find your host's network interfaces:**
```bash
   ip addr show
```
   Identify the interface connected to the USRP (e.g. `enx00e04c156708` for a USB-to-Ethernet adapter).

2. **Check for a stale/conflicting IP and clear it if needed:**
```bash
   sudo ip addr flush dev <interface_name>
```

3. **Assign a static IP on the same subnet as the device.**
   Your USRP N210 is configured at `192.168.10.3`, so assign your host a different address on the same subnet (do not use `.3`):
```bash
   sudo ip addr add 192.168.10.1/24 dev <interface_name>
   sudo ip link set <interface_name> up
```
   > **Note:** This IP assignment is not persistent across reboots. You'll need to reapply it each time the machine restarts, or configure it permanently via netplan/NetworkManager.

4. **Verify the interface is up and correctly addressed:**
```bash
   ip addr show <interface_name>
```
   Confirm `inet 192.168.10.1/24` appears and the state is `UP`/`LOWER_UP`.

5. **Ping the device directly:**
```bash
   ping 192.168.10.3
```

6. **Run device discovery with the explicit address:**
```bash
   uhd_find_devices --args="addr=192.168.10.3"
```
   If connected, the terminal should read:
   
--------------------------------------------------
-- UHD Device 0
--------------------------------------------------
Device Address:
    serial: 30FC71F
    addr: 192.168.10.3
    name: 
    type: usrp2
    
    
> Since this device isn't at UHD's default address, always pass `addr=192.168.10.3` explicitly to UHD tools (`uhd_usrp_probe`, `rx_samples_to_file`, GNU Radio's UHD source block, etc.).

## Building

### 1. Clone the repository
```bash
git clone <repository-url>
cd usrp_n210
```

### 2. Create build directory
```bash
mkdir build && cd build
```

### 3. Configure and compile
```bash
cmake ..
make
```

### 4. Install (optional)
```bash
sudo make install
```

### Run
```bash
make -j && ./usrp_full_duplex
```

## Dependencies Installation

### Ubuntu/Debian
```bash
sudo apt-get install libuhd-dev libboost-all-dev cmake
```

### macOS
```bash
brew install uhd boost cmake
```

## Troubleshooting
- Ensure UHD is properly installed: `uhd_usrp_probe`
- Check CMake output for missing dependencies
- If `uhd_find_devices` reports "No UHD Devices Found," recheck steps 2–5 above — a missing IP assignment on the host interface is the most common cause
- Refer to UHD documentation for hardware-specific issues

## Support
For additional help, visit the [UHD GitHub repository](https://github.com/EttusResearch/uhd)

