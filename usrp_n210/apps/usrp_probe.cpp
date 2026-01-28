#include "usrp/device.hpp"
#include <iostream>

int main() {
    try {
        usrp::DeviceConfig cfg;
        cfg.device_args = "addr=192.168.10.2";
        cfg.channels = {0};

        // Safe starter settings
        cfg.tx.rate_sps = 1e6;
        cfg.rx.rate_sps = 1e6;
        cfg.tx.freq_hz  = 100e6;
        cfg.rx.freq_hz  = 100e6;

        cfg.tx.gain_db = 5.0;
        cfg.rx.gain_db = 20.0;

        // For N210 typical mapping:
        // RF1 = "TX/RX", RF2 = "RX2"
        cfg.tx.ant = "TX/RX";
        cfg.rx.ant = "RX2";

        usrp::Device dev(cfg);
        std::cout << dev.pp_string() << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FATAL: " << e.what() << "\n";
        return 1;
    }
}
