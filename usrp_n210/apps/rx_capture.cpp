#include "usrp/device.hpp"
#include "usrp/rx_stream.hpp"

#include <iostream>

int main() {
    try {
        usrp::DeviceConfig dcfg;
        dcfg.device_args = "addr=192.168.10.2";
        dcfg.clock_source = "internal";
        dcfg.time_source  = "none";
        dcfg.channels = {0};

        // Safe starter settings
        dcfg.rx.rate_sps = 1e6;
        dcfg.rx.freq_hz  = 100e6;
        dcfg.rx.gain_db  = 20.0;
        dcfg.rx.ant      = "RX2";

        // TX config unused in RX-only app but keep valid
        dcfg.tx.rate_sps = 1e6;
        dcfg.tx.freq_hz  = 100e6;
        dcfg.tx.gain_db  = 0.0;
        dcfg.tx.ant      = "TX/RX";

        usrp::Device dev(dcfg);

        usrp::RxCaptureConfig ccfg;
        ccfg.capture_seconds = 5.0;
        ccfg.queue_capacity_blocks = 128;
        ccfg.iq_path   = "rx_iq_sc16.bin";
        ccfg.meta_path = "rx_meta.csv";

        usrp::RxCapture cap(dev, ccfg);
        auto stats = cap.run();

        std::cout << "Capture done:\n"
                  << "  blocks     = " << stats.blocks << "\n"
                  << "  samples    = " << stats.samps << "\n"
                  << "  overflows  = " << stats.overflows << "\n"
                  << "  timeouts   = " << stats.timeouts << "\n"
                  << "  other_err  = " << stats.other_err << "\n";
        std::cout << "Wrote: " << ccfg.iq_path << " and " << ccfg.meta_path << "\n";
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "FATAL: " << e.what() << "\n";
        return 1;
    }
}
