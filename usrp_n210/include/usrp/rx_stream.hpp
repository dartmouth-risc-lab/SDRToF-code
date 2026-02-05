#pragma once

#include "usrp/device.hpp"
#include "usrp/types.hpp"
#include "util/bounded_queue.hpp"

#include <uhd/stream.hpp>
#include <uhd/types/metadata.hpp>

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <string>
#include <thread>
#include <vector>

namespace usrp {

// A single block handed from RX thread -> writer thread.
// iq is preallocated to cfg.block_samps (not spb_). nsamps indicates valid prefix.
struct RxBlock {
    uint64_t seq = 0;
    size_t   nsamps = 0;
    std::vector<sc16> iq;

    // Metadata snapshot (last recv in this block)
    bool    has_time = false;
    int64_t time_full = 0;     // seconds
    double  time_frac = 0.0;   // fractional seconds
    int     err_code = 0;      // uhd::rx_metadata_t::error_code value
};

struct RxStats {
    uint64_t blocks = 0;
    uint64_t samps  = 0;
    uint64_t overflows = 0;
    uint64_t timeouts  = 0;
    uint64_t other_err = 0;

    // Extra: number of metadata rows written (error-only or full)
    uint64_t meta_rows = 0;
};

struct RxCaptureConfig {
    std::string rx_cpu_format = "sc16"; // host memory format
    std::string rx_otw_format = "sc16"; // on-the-wire format

    double timeout_s = 0.2;
    bool one_packet = false;

    // queue depth in blocks (bounded)
    size_t queue_capacity_blocks = 256;

    // capture duration
    double capture_seconds = 5.0;

    // Block sizing (BIG performance knob):
    // This is the number of complex samples per block enqueued to the writer.
    // Recommended:
    //   1 MSps  ->  65536
    //   5-10 MSps -> 131072 or 262144 (watch RAM)
    size_t block_samps = 131072;

    // output
    std::string iq_path = "rx_iq_sc16.bin";
    std::string meta_path = "rx_meta.csv";

    // Metadata policy:
    // - If false (default): write metadata only on errors (overflow/timeout/other)
    // - If true: write one metadata row per block (still much less than per-packet)
    bool write_full_metadata = false;

    // Stream/file buffering
    size_t iq_file_buffer_bytes   = 8 * 1024 * 1024;  // 8 MB
    size_t meta_file_buffer_bytes = 1 * 1024 * 1024;  // 1 MB

    // Optional front-end cleanup
    // Discard initial samples to allow analog chain to settle
    size_t discard_samps = 0;
};

class RxCapture {
public:
    RxCapture(Device& dev, const RxCaptureConfig& cfg);

    // Runs capture (starts threads, blocks until done)
    RxStats run();

    const RxStats& stats() const { return stats_; }

private:
    void rx_thread_fn_();
    void writer_thread_fn_();

    // helper
    static bool is_error_code_(uhd::rx_metadata_t::error_code_t ec);

    Device& dev_;
    RxCaptureConfig cfg_;

    uhd::rx_streamer::sptr rx_stream_;
    size_t spb_ = 0;

    // Pointer queues (fast): only move 8-byte pointers
    util::BoundedQueue<std::unique_ptr<RxBlock>> q_;
    util::BoundedQueue<std::unique_ptr<RxBlock>> free_q_;

    std::thread rx_thread_;
    std::thread writer_thread_;
    std::atomic<bool> running_{false};

    std::atomic<uint64_t> seq_{0};
    RxStats stats_{};
};

} // namespace usrp
