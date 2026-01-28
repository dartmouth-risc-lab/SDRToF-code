// src/usrp/tx_stream.cpp
#include "usrp/tx_stream.hpp"

#include <chrono>
#include <cmath>
#include <iostream>
#include <stdexcept>

namespace usrp {

static inline void require(bool cond, const std::string& msg) {
    if (!cond) throw std::runtime_error(msg);
}

TxTone::TxTone(Device& dev, const TxToneConfig& cfg)
    : dev_(dev), cfg_(cfg)
{
    // Create TX streamer
    uhd::stream_args_t tx_args(cfg_.tx_cpu_format, cfg_.tx_otw_format);
    tx_args.channels = dev_.cfg().channels; // typically {0}

    tx_stream_ = dev_.handle()->get_tx_stream(tx_args);
    require(tx_stream_ != nullptr, "Failed to create TX streamer");

    spb_ = tx_stream_->get_max_num_samps();
    require(spb_ > 0, "TX streamer returned spb=0");

    // Allocate buffer; we will fill it on-the-fly with continuous phase
    tone_buf_.resize(spb_);

    const double Fs = dev_.cfg().tx.rate_sps;
    require(Fs > 0.0, "TX rate_sps must be > 0");

    dphi_ = 2.0 * M_PI * cfg_.tone_hz / Fs;
    phase_ = 0.0;

    // Helpful debug line (optional)
    // std::cerr << "[TX] spb=" << spb_ << " Fs=" << Fs << " tone_hz=" << cfg_.tone_hz << "\n";
}

TxStats TxTone::run() {
    running_.store(true);

    // Async monitor thread (detects underflows)
    if (cfg_.enable_async_monitor) {
        async_thread_ = std::thread(&TxTone::async_thread_fn_, this);
    }

    tx_thread_ = std::thread(&TxTone::tx_thread_fn_, this);
    tx_thread_.join();

    running_.store(false);
    if (cfg_.enable_async_monitor) async_thread_.join();

    return stats_;
}

void TxTone::tx_thread_fn_() {
    using clock = std::chrono::steady_clock;
    const auto t0 = clock::now();

    uhd::tx_metadata_t md;
    md.start_of_burst = true;
    md.end_of_burst   = false;
    md.has_time_spec  = false;  // stream-now (no PPS)

    const double A = std::max(0.0, std::min(1.0, cfg_.amplitude)) * 32767.0;

    while (true) {
        const double elapsed = std::chrono::duration<double>(clock::now() - t0).count();
        if (elapsed >= cfg_.tx_seconds) break;

        // Fill buffer with continuous-phase tone
        for (size_t n = 0; n < tone_buf_.size(); n++) {
            const double i = A * std::cos(phase_);
            const double q = A * std::sin(phase_);
            tone_buf_[n] = sc16(int16_t(std::lrint(i)), int16_t(std::lrint(q)));

            phase_ += dphi_;
            // Robust wrapping
            while (phase_ >  M_PI) phase_ -= 2.0 * M_PI;
            while (phase_ < -M_PI) phase_ += 2.0 * M_PI;
        }

        const size_t sent = tx_stream_->send(
            tone_buf_.data(), tone_buf_.size(), md, cfg_.send_timeout_s
        );
        md.start_of_burst = false;

        stats_.sends++;
        stats_.samps += sent;

        if (sent == 0) stats_.timeouts++;
        // If you ever see partial sends, note it (rare in steady streaming)
        // if (sent != tone_buf_.size()) std::cerr << "[TX] partial send: " << sent << "/" << tone_buf_.size() << "\n";
    }

    // End burst cleanly
    uhd::tx_metadata_t eob;
    eob.start_of_burst = false;
    eob.end_of_burst   = true;
    eob.has_time_spec  = false;

    // UHD 4.2: don't pass nullptr to send(). Use a valid buffer.
    sc16 dummy(0, 0);
    tx_stream_->send(&dummy, 1, eob, cfg_.send_timeout_s);
}

void TxTone::async_thread_fn_() {
    // Underflow reports come through async messages
    while (running_.load()) {
        bool ok = tx_stream_->recv_async_msg(async_md_, 0.2);
        if (!ok) continue;

        if (async_md_.event_code == uhd::async_metadata_t::EVENT_CODE_UNDERFLOW ||
            async_md_.event_code == uhd::async_metadata_t::EVENT_CODE_UNDERFLOW_IN_PACKET) {
            stats_.underflows++;
        } else if (async_md_.event_code == uhd::async_metadata_t::EVENT_CODE_SEQ_ERROR) {
            stats_.seq_err++;
        }
    }
}

} // namespace usrp
