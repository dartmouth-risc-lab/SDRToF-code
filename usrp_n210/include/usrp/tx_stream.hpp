#pragma once

#include "usrp/device.hpp"
#include "usrp/types.hpp"

#include <uhd/stream.hpp>
#include <uhd/types/metadata.hpp>

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>
#include <thread>
#include <vector>

namespace usrp {

struct TxStats {
    uint64_t sends = 0;
    uint64_t samps = 0;
    uint64_t underflows = 0;
    uint64_t seq_err = 0;
    uint64_t timeouts = 0;
};

struct TxToneConfig {
    // streaming formats
    std::string tx_cpu_format = "sc16";
    std::string tx_otw_format = "sc16";

    // tone
    double tone_hz = 100e3;     // baseband +fb
    double amplitude = 0.2;     // fraction of full-scale int16 (0..1)

    // run time
    double tx_seconds = 5.0;

    // timeouts
    double send_timeout_s = 0.2;

    // async monitoring (underflows)
    bool enable_async_monitor = true;

    // device args (optional override): mostly keep using DeviceConfig
};

class TxTone {
public:
    TxTone(Device& dev, const TxToneConfig& cfg);

    // Run TX (blocks until done)
    TxStats run();

    const TxStats& stats() const { return stats_; }

private:

    void tx_thread_fn_();
    void async_thread_fn_();

    Device& dev_;
    TxToneConfig cfg_;

    uhd::tx_streamer::sptr tx_stream_;
    uhd::async_metadata_t async_md_;

    size_t spb_ = 0;
    std::vector<sc16> tone_buf_;

    double phase_ = 0.0;
    double dphi_  = 0.0;

    std::thread tx_thread_;
    std::thread async_thread_;
    std::atomic<bool> running_{false};
    
    TxStats stats_{};
};

} // namespace usrp
