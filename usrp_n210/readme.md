# USRP N210 Software Build Instructions

## Prerequisites
- GCC compiler or compatible toolchain
- CMake 3.10+
- UHD (USRP Hardware Driver) development libraries
- Boost libraries

## Building

### 1. Clone the repository
This is a future step. Directly head to step 2 if building from this code. 
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
- Refer to UHD documentation for hardware-specific issues

## Support
For additional help, visit the [UHD GitHub repository](https://github.com/EttusResearch/uhd)