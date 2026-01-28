#include "usrp/device.hpp"
#include "usrp/tx_stream.hpp"

#include <iostream>

int main() {
    try {
        usrp::DeviceConfig dcfg;
        dcfg.device_args = "addr=192.168.10.2";
        dcfg.clock_source = "internal";
        dcfg.time_source  = "none";
        dcfg.channels = {0};

        // TX settings
        dcfg.tx.rate_sps = 1e6;
        dcfg.tx.freq_hz  = 100e6;  // Fc
        dcfg.tx.gain_db  = 5.0;
        dcfg.tx.ant      = "TX/RX";

        // RX settings not used here, but keep valid
        dcfg.rx.rate_sps = 1e6;
        dcfg.rx.freq_hz  = 100e6;
        dcfg.rx.gain_db  = 0.0;
        dcfg.rx.ant      = "RX2";

        usrp::Device dev(dcfg);

        usrp::TxToneConfig tcfg;
        tcfg.tone_hz    = 100e3;   // +fb
        tcfg.amplitude  = 0.2;     // 20% FS
        tcfg.tx_seconds = 5.0;

        usrp::TxTone tx(dev, tcfg);
        auto stats = tx.run();

        std::cout << "TX done:\n"
                  << "  sends      = " << stats.sends << "\n"
                  << "  samples    = " << stats.samps << "\n"
                  << "  underflows = " << stats.underflows << "\n"
                  << "  seq_err    = " << stats.seq_err << "\n"
                  << "  timeouts   = " << stats.timeouts << "\n";

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FATAL: " << e.what() << "\n";
        return 1;
    }
}
