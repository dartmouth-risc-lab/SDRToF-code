#include "usrp/rx_stream.hpp"

#include <uhd/stream.hpp>
#include <uhd/types/stream_cmd.hpp>


#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>

namespace usrp {

static inline void require(bool cond, const std::string& msg) {
    if (!cond) throw std::runtime_error(msg);
}

bool RxCapture::is_error_code_(uhd::rx_metadata_t::error_code_t ec) {
    return ec != uhd::rx_metadata_t::ERROR_CODE_NONE;
}

RxCapture::RxCapture(Device& dev, const RxCaptureConfig& cfg)
    : dev_(dev)
    , cfg_(cfg)
    , q_(cfg.queue_capacity_blocks)
    , free_q_(cfg.queue_capacity_blocks)
{
    require(cfg_.block_samps > 0, "block_samps must be > 0");
    require(cfg_.queue_capacity_blocks > 0, "queue_capacity_blocks must be > 0");

    // Create RX streamer
    uhd::stream_args_t rx_args(cfg_.rx_cpu_format, cfg_.rx_otw_format);
    rx_args.channels = dev_.cfg().channels; // typically {0}

    rx_stream_ = dev_.handle()->get_rx_stream(rx_args);
    require(rx_stream_ != nullptr, "Failed to create RX streamer");

    spb_ = rx_stream_->get_max_num_samps();
    require(spb_ > 0, "RX streamer returned spb=0");

    // Prefill free-block pool with preallocated IQ buffers sized to block_samps
    for (size_t i = 0; i < cfg_.queue_capacity_blocks; i++) {
        auto blk = std::make_unique<RxBlock>();
        blk->iq.resize(cfg_.block_samps);
        blk->nsamps = 0;
        require(free_q_.push(std::move(blk)), "Failed to prefill free_q_");
    }
}

RxStats RxCapture::run() {
    running_.store(true);

    // Start continuous stream
    uhd::stream_cmd_t cmd(uhd::stream_cmd_t::STREAM_MODE_START_CONTINUOUS);
    cmd.stream_now = true;
    rx_stream_->issue_stream_cmd(cmd);

    writer_thread_ = std::thread(&RxCapture::writer_thread_fn_, this);
    rx_thread_     = std::thread(&RxCapture::rx_thread_fn_, this);

    rx_thread_.join();

    // Stop stream
    uhd::stream_cmd_t stop(uhd::stream_cmd_t::STREAM_MODE_STOP_CONTINUOUS);
    rx_stream_->issue_stream_cmd(stop);

    // Close producer->consumer queue so writer drains & exits
    q_.close();
    writer_thread_.join();

    // Close free pool (not strictly necessary once threads joined, but tidy)
    free_q_.close();

    running_.store(false);
    return stats_;
}

void RxCapture::rx_thread_fn_() {
    using clock = std::chrono::steady_clock;
    const auto t0 = clock::now();

    uhd::rx_metadata_t md;

    // Receive loop:
    // Fill one "big block" of cfg_.block_samps by calling recv() multiple times.
    while (true) {
        const double elapsed = std::chrono::duration<double>(clock::now() - t0).count();
        if (elapsed >= cfg_.capture_seconds) break;

        // Acquire a preallocated block
        auto free_item = free_q_.pop();
        if (!free_item.has_value()) break; // free pool closed unexpectedly
        auto blk = std::move(*free_item);

        blk->seq = seq_.fetch_add(1);
        blk->nsamps = 0;
        blk->has_time = false;
        blk->time_full = 0;
        blk->time_frac = 0.0;
        blk->err_code = 0;

        // Fill up to block_samps samples
        while (blk->nsamps < cfg_.block_samps) {
            const double elapsed2 = std::chrono::duration<double>(clock::now() - t0).count();
            if (elapsed2 >= cfg_.capture_seconds) break;

            const size_t remaining = cfg_.block_samps - blk->nsamps;
            const size_t want = (remaining < spb_) ? remaining : spb_;

            // Receive directly into block buffer at offset
            const size_t nrecv = rx_stream_->recv(
                blk->iq.data() + blk->nsamps,
                want,
                md,
                cfg_.timeout_s,
                cfg_.one_packet
            );

            // Update stats and record last metadata snapshot for this block
            blk->nsamps += nrecv;

            blk->has_time  = md.has_time_spec;
            blk->time_full = static_cast<int64_t>(md.time_spec.get_full_secs());
            blk->time_frac = md.time_spec.get_frac_secs();
            blk->err_code  = static_cast<int>(md.error_code);

            // Count errors (per recv call)
            if (md.error_code == uhd::rx_metadata_t::ERROR_CODE_OVERFLOW) {
                stats_.overflows++;
            } else if (md.error_code == uhd::rx_metadata_t::ERROR_CODE_TIMEOUT) {
                stats_.timeouts++;
            } else if (md.error_code != uhd::rx_metadata_t::ERROR_CODE_NONE) {
                stats_.other_err++;
            }

            // On severe errors you may choose to break. For now, continue.
            // If recv() returns 0 repeatedly due to timeouts, elapsed will stop it.
        }

        // Update aggregate stats per block
        stats_.blocks++;
        stats_.samps += blk->nsamps;

        // Push block to writer (even if nsamps==0, to preserve timing/error logging)
        if (!q_.push(std::move(blk))) break; // queue closed
    }
}

void RxCapture::writer_thread_fn_() {
    std::ofstream iq_file(cfg_.iq_path, std::ios::binary);
    if (!iq_file) throw std::runtime_error("Failed to open IQ output file: " + cfg_.iq_path);

    std::ofstream meta_file(cfg_.meta_path);
    if (!meta_file) throw std::runtime_error("Failed to open meta output file: " + cfg_.meta_path);

    // Increase std::ofstream internal buffering (reduces syscall overhead)
    std::vector<char> iq_buf(cfg_.iq_file_buffer_bytes);
    if (!iq_buf.empty()) {
        iq_file.rdbuf()->pubsetbuf(iq_buf.data(), static_cast<std::streamsize>(iq_buf.size()));
    }

    std::vector<char> meta_buf(cfg_.meta_file_buffer_bytes);
    if (!meta_buf.empty()) {
        meta_file.rdbuf()->pubsetbuf(meta_buf.data(), static_cast<std::streamsize>(meta_buf.size()));
    }

    // Metadata: either error-only rows (default) or one row per block.
    meta_file << "seq,nsamps,has_time,time_full,time_frac,err_code\n";

    // Front-end cleanup state
    uint64_t discard_left = cfg_.discard_samps;

    while (true) {
        auto item = q_.pop();
        if (!item.has_value()) break; // closed+empty

        auto blk = std::move(*item);

        // Discard initial samples, then write remaining IQ payload
        if (blk->nsamps > 0) {
            size_t start = 0;
            if (discard_left > 0) {
                const size_t drop = std::min<uint64_t>(discard_left, blk->nsamps);
                discard_left -= drop;
                start = drop;
            }
            const size_t out = blk->nsamps - start;
            if (out > 0) {
                iq_file.write(reinterpret_cast<const char*>(blk->iq.data() + start),
                              static_cast<std::streamsize>(out * sizeof(sc16)));
            }
        }

        const bool err_row = is_error_code_(
            static_cast<uhd::rx_metadata_t::error_code_t>(blk->err_code)
        );

        if (cfg_.write_full_metadata || err_row) {
            meta_file << blk->seq << ","
                      << blk->nsamps << ","
                      << (blk->has_time ? 1 : 0) << ","
                      << blk->time_full << ","
                      << blk->time_frac << ","
                      << blk->err_code << "\n";
            stats_.meta_rows++;
        }

        // Recycle block back to free pool
        blk->nsamps = 0;
        blk->has_time = false;
        blk->err_code = 0;

        // If for some reason free_q_ is closed/full, drop it (shouldn't happen in normal run)
        (void)free_q_.push(std::move(blk));
    }

    iq_file.flush();
    meta_file.flush();
}

} // namespace usrp
