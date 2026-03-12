# GNU Radio Software Setup

## Installation

1. **Install GNU Radio**
    ```bash
    sudo apt install gnuradio gnuradio-dev
    ```

2. **Install UHD (USRP Hardware Driver)**
    ```bash
    sudo apt install uhd uhd-host
    ```

3. **Install Python Dependencies**
    ```bash
    pip install numpy matplotlib scipy
    ```

## Running the Code

1. **Navigate to the directory**
    ```bash
    cd /home/...    ```

2. **Run your GNU Radio script**
    ```bash
    python your_script.py
    ```

3. **Or use GNU Radio Companion (GUI)**
    ```bash
    gnuradio-companion
    ```

## Prerequisites

- Python 3.7+
- USRP hardware connected via USB or ethernet 
- Linux-based OS (Ubuntu recommended)

## Troubleshooting

- Ensure USRP is detected: `uhd_find_devices`
- Check permissions: `sudo usermod -a -G usrp $USER`
- Reboot after driver installation