#include "usrp/device.hpp"

#include <uhd/utils/thread.hpp>
#include <uhd/exception.hpp>

#include <sstream>
#include <stdexcept>

namespace usrp {

static inline void require(bool cond, const std::string& msg) {
    if (!cond) throw std::runtime_error(msg);
}

Device::Device(const DeviceConfig& cfg) : cfg_(cfg) {
    uhd::set_thread_priority_safe();

    // Create device
    usrp_ = uhd::usrp::multi_usrp::make(cfg_.device_args);
    require(usrp_ != nullptr, "Failed to create UHD multi_usrp");

    apply_clock_and_time_();
    apply_common_();
    apply_tx_config();
    apply_rx_config();
}

void Device::apply_clock_and_time_() {
    // Clock/time sources
    usrp_->set_clock_source(cfg_.clock_source);
    usrp_->set_time_source(cfg_.time_source);

    // For “single-box” experiments, set time to zero now (no PPS required)
    usrp_->set_time_now(uhd::time_spec_t(0.0));
}

void Device::apply_common_() {
    // Validate channels
    require(!cfg_.channels.empty(), "No channels configured");
    for (auto ch : cfg_.channels) {
        // N210 with single dboard usually supports ch=0 only
        // We won't hard-fail here; UHD will error if invalid.
        (void)ch;
    }
}

void Device::apply_tx_config() {
    for (auto ch : cfg_.channels) {
        usrp_->set_tx_rate(cfg_.tx.rate_sps, ch);

        uhd::tune_request_t tr(cfg_.tx.freq_hz);
        usrp_->set_tx_freq(tr, ch);

        usrp_->set_tx_gain(cfg_.tx.gain_db, ch);

        if (!cfg_.tx.ant.empty()) usrp_->set_tx_antenna(cfg_.tx.ant, ch);
        if (cfg_.tx.bw_hz > 0.0) usrp_->set_tx_bandwidth(cfg_.tx.bw_hz, ch);
    }
}

void Device::apply_rx_config() {
    for (auto ch : cfg_.channels) {
        usrp_->set_rx_rate(cfg_.rx.rate_sps, ch);

        uhd::tune_request_t tr(cfg_.rx.freq_hz);
        usrp_->set_rx_freq(tr, ch);

        usrp_->set_rx_gain(cfg_.rx.gain_db, ch);

        if (!cfg_.rx.ant.empty()) usrp_->set_rx_antenna(cfg_.rx.ant, ch);
        if (cfg_.rx.bw_hz > 0.0) usrp_->set_rx_bandwidth(cfg_.rx.bw_hz, ch);

        // Standard UHD front-end corrections
        usrp_->set_rx_dc_offset(cfg_.rx.enable_dc_offset, ch);
        usrp_->set_rx_iq_balance(cfg_.rx.enable_iq_balance, ch);
    }
}

std::string Device::pp_string() const {
    std::ostringstream ss;
    ss << "Device args: " << cfg_.device_args << "\n"
       << "Clock source: " << cfg_.clock_source << "\n"
       << "Time source : " << cfg_.time_source << "\n";

    ss << "Channels: ";
    for (auto ch : cfg_.channels) ss << ch << " ";
    ss << "\n";

    ss << "TX: rate=" << cfg_.tx.rate_sps
       << " Hz, freq=" << cfg_.tx.freq_hz
       << " Hz, gain=" << cfg_.tx.gain_db
       << " dB, ant=" << (cfg_.tx.ant.empty() ? "(default)" : cfg_.tx.ant)
       << "\n";

    ss << "RX: rate=" << cfg_.rx.rate_sps
       << " Hz, freq=" << cfg_.rx.freq_hz
       << " Hz, gain=" << cfg_.rx.gain_db
       << " dB, ant=" << (cfg_.rx.ant.empty() ? "(default)" : cfg_.rx.ant)
       << " dc_offset=" << (cfg_.rx.enable_dc_offset ? "auto" : "off")
       << " iq_balance=" << (cfg_.rx.enable_iq_balance ? "auto" : "off")
       << "\n";

    // UHD’s own pretty printer (often helpful)
    ss << "\nUHD device:\n" << usrp_->get_pp_string() << "\n";
    return ss.str();
}

} // namespace usrp
