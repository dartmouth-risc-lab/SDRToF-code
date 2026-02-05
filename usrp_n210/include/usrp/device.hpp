#pragma once

#include <uhd/usrp/multi_usrp.hpp>
#include <uhd/types/tune_request.hpp>

#include <memory>
#include <string>
#include <vector>

namespace usrp {

struct ChannelConfig {
    double rate_sps = 1e6;
    double freq_hz  = 100e6;
    double gain_db  = 0.0;
    std::string ant = "";      // e.g. "RX2" or "TX/RX" (optional; depends on dboard)
    double bw_hz    = 0.0;     // 0 = leave default
    bool enable_iq_balance = true;  // enable UHD automatic IQ balance (RX only)
    bool enable_dc_offset  = true;  // enable UHD automatic DC offset (RX only)
};

struct DeviceConfig {
    std::string device_args = "addr=192.168.10.2"; // UHD device args
    std::string clock_source = "internal";         // "internal", "external", "gpsdo"
    std::string time_source  = "none";         // "internal", "external", "gpsdo"
    std::vector<size_t> channels = {0};            // N210 single dboard => {0}
    ChannelConfig rx;
    ChannelConfig tx;
};

class Device {
public:
    explicit Device(const DeviceConfig& cfg);

    // Access underlying UHD handle (for advanced uses)
    uhd::usrp::multi_usrp::sptr handle() { return usrp_; }

    // Convenience getters
    const DeviceConfig& cfg() const { return cfg_; }
    std::string pp_string() const;

    // Re-apply config if you change fields later
    void apply_rx_config();
    void apply_tx_config();

private:
    void apply_clock_and_time_();
    void apply_common_();

    DeviceConfig cfg_;
    uhd::usrp::multi_usrp::sptr usrp_;
};

} // namespace usrp
