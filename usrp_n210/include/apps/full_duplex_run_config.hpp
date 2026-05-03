#pragma once

#include <cstddef>
#include <filesystem>
#include <string>
#include <vector>

namespace app {

struct FullDuplexRunConfig {
    // Experiment labeling and output
    std::filesystem::path output_dir = "/home/risc/ram/server_mount/May03/";
    std::string experiment_name = "test_static";

    // RF / waveform
    double sample_rate_sps = 5e6;
    double tx_center_freq_hz = 900e6;
    double rx_center_freq_hz = 900e6;
    double tx_tone_freq_hz = 10e3;
    double tx_amplitude = 0.4;

    // Timing
    double tx_seconds = 3.0;
    double rx_extra_seconds = 0.5;
    double settle_seconds = 0.02;

    // Device
    std::string device_args =
        "addr=192.168.10.2,"
        "recv_frame_size=8192,num_recv_frames=256,"
        "send_frame_size=8192,num_send_frames=256";
    std::string clock_source = "internal";
    std::string time_source = "none";
    std::vector<size_t> channels = {0};

    // Front-end
    double tx_gain_db = 32.0;
    std::string tx_ant = "TX/RX";
    double rx_gain_db = 8.0;
    std::string rx_ant = "RX2";
    bool rx_enable_dc_offset = true;
    bool rx_enable_iq_balance = true;

    // Streaming
    double rx_timeout_s = 0.2;
    double tx_send_timeout_s = 0.2;
    size_t queue_capacity_blocks = 256;
    size_t block_samps = 0; // 0 => choose automatically from sample rate
    bool write_rx_event_csv = false;
    bool write_full_rx_metadata = false;
    size_t iq_file_buffer_bytes = 8 * 1024 * 1024;
    size_t meta_file_buffer_bytes = 1 * 1024 * 1024;
};

inline FullDuplexRunConfig default_full_duplex_run_config() {
    return FullDuplexRunConfig{};
}

inline double rx_capture_seconds(const FullDuplexRunConfig& cfg) {
    return cfg.tx_seconds + cfg.rx_extra_seconds;
}

inline size_t default_block_samps_for_rate(double sample_rate_sps) {
    if (sample_rate_sps <= 1e6) return 65536;
    if (sample_rate_sps <= 5e6) return 131072;
    return 262144;
}

} // namespace app
