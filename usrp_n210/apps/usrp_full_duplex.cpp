#include "apps/full_duplex_run_config.hpp"
#include "usrp/device.hpp"
#include "usrp/rx_stream.hpp"
#include "usrp/tx_stream.hpp"

#include <atomic>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <thread>
#include <vector>

static uintmax_t safe_filesize(const std::string& path) {
    std::error_code ec;
    auto sz = std::filesystem::file_size(path, ec);
    return ec ? 0 : sz;
}

static std::string timestamp_utc_like() {
    using namespace std::chrono;
    auto now = system_clock::now();
    auto t = system_clock::to_time_t(now);
    std::tm tm{};
#if defined(_WIN32)
    gmtime_s(&tm, &t);
#else
    gmtime_r(&t, &tm);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y%m%d_%H%M%S");
    return oss.str();
}

static std::string format_rate_tag(double sample_rate_sps) {
    const double rate_msps = sample_rate_sps / 1e6;
    std::ostringstream oss;
    oss << std::fixed
        << std::setprecision((rate_msps == std::floor(rate_msps)) ? 0 : 1)
        << rate_msps << "msps";
    return oss.str();
}

static std::string format_duration_tag(double tx_seconds) {
    const auto rounded_seconds = static_cast<long long>(std::llround(tx_seconds));
    return std::to_string(rounded_seconds) + "s";
}

static std::string build_run_tag(const app::FullDuplexRunConfig& cfg) {
    std::ostringstream oss;
    oss << "Fc" << static_cast<int>(cfg.tx_center_freq_hz / 1e6)
        << "_Fb" << static_cast<int>(cfg.tx_tone_freq_hz / 1e3)
        << "_" << cfg.experiment_name;
    return oss.str();
}

static std::string last_path_component(const std::filesystem::path& path) {
    for (auto it = path.end(); it != path.begin();) {
        --it;
        const std::string part = it->string();
        if (!part.empty() && part != "/" && part != "." && part != "\\") {
            return part;
        }
    }
    return "";
}

static std::filesystem::path output_dir_manifest_ref(const std::filesystem::path& output_dir) {
    const auto normalized_output_dir = output_dir.lexically_normal();
    std::filesystem::path server_mount_relative;
    bool after_server_mount = false;

    for (const auto& part_path : normalized_output_dir) {
        const std::string part = part_path.string();
        if (part.empty() || part == "/" || part == "." || part == "\\") {
            continue;
        }
        if (part == "server_mount") {
            server_mount_relative.clear();
            after_server_mount = true;
            continue;
        }
        if (after_server_mount) {
            server_mount_relative /= part_path;
        }
    }

    if (!server_mount_relative.empty()) {
        return server_mount_relative;
    }
    if (normalized_output_dir.is_relative()) {
        return normalized_output_dir;
    }

    return last_path_component(normalized_output_dir);
}

static std::string manifest_file_ref(
    const std::filesystem::path& output_dir,
    const std::string& full_path
) {
    const auto dir_name = output_dir_manifest_ref(output_dir).generic_string();
    const auto file_name = std::filesystem::path(full_path).filename().string();
    if (dir_name.empty()) {
        return file_name;
    }
    return dir_name + "/" + file_name;
}

static std::string manifest_dir_ref(const std::filesystem::path& output_dir) {
    return output_dir_manifest_ref(output_dir).generic_string();
}

static std::string json_escape(const std::string& input) {
    std::ostringstream oss;
    for (const char c : input) {
        switch (c) {
        case '\\': oss << "\\\\"; break;
        case '"': oss << "\\\""; break;
        case '\n': oss << "\\n"; break;
        case '\r': oss << "\\r"; break;
        case '\t': oss << "\\t"; break;
        default: oss << c; break;
        }
    }
    return oss.str();
}

static void write_run_metadata_json(
    const std::string& path,
    const app::FullDuplexRunConfig& cfg,
    const usrp::DeviceConfig& dcfg,
    uhd::usrp::multi_usrp::sptr usrp,
    const std::string& iq_path,
    const std::string& rx_event_path,
    const usrp::TxStats& txs,
    const usrp::RxStats& rxs,
    uintmax_t iq_bytes,
    const std::string& started_utc,
    const std::string& finished_utc
) {
    std::ofstream meta_file(path);
    if (!meta_file) {
        throw std::runtime_error("Failed to open metadata json output file: " + path);
    }

    const double rx_seconds = app::rx_capture_seconds(cfg);
    const double captured_seconds = (cfg.sample_rate_sps > 0.0)
        ? static_cast<double>(rxs.samps) / cfg.sample_rate_sps
        : 0.0;
    const size_t block_samps = (cfg.block_samps == 0)
        ? app::default_block_samps_for_rate(cfg.sample_rate_sps)
        : cfg.block_samps;

    meta_file << "{\n";
    meta_file << "  \"run\": {\n";
    meta_file << "    \"experiment_name\": \"" << json_escape(cfg.experiment_name) << "\",\n";
    meta_file << "    \"started_utc\": \"" << started_utc << "\",\n";
    meta_file << "    \"finished_utc\": \"" << finished_utc << "\"\n";
    meta_file << "  },\n";
    meta_file << "  \"files\": {\n";
    meta_file << "    \"directory\": \"" << json_escape(manifest_dir_ref(cfg.output_dir)) << "\",\n";
    meta_file << "    \"iq_bin\": \"" << json_escape(manifest_file_ref(cfg.output_dir, iq_path)) << "\",\n";
    if (!rx_event_path.empty()) {
        meta_file << "    \"rx_events_csv\": \"" << json_escape(manifest_file_ref(cfg.output_dir, rx_event_path)) << "\",\n";
    } else {
        meta_file << "    \"rx_events_csv\": null,\n";
    }
    meta_file << "    \"metadata_json\": \"" << json_escape(manifest_file_ref(cfg.output_dir, path)) << "\"\n";
    meta_file << "  },\n";
    meta_file << "  \"requested\": {\n";
    meta_file << "    \"sample_rate_sps\": " << cfg.sample_rate_sps << ",\n";
    meta_file << "    \"tx_center_freq_hz\": " << cfg.tx_center_freq_hz << ",\n";
    meta_file << "    \"rx_center_freq_hz\": " << cfg.rx_center_freq_hz << ",\n";
    meta_file << "    \"tx_tone_freq_hz\": " << cfg.tx_tone_freq_hz << ",\n";
    meta_file << "    \"tx_gain_db\": " << cfg.tx_gain_db << ",\n";
    meta_file << "    \"rx_gain_db\": " << cfg.rx_gain_db << ",\n";
    meta_file << "    \"tx_amplitude\": " << cfg.tx_amplitude << ",\n";
    meta_file << "    \"tx_seconds\": " << cfg.tx_seconds << ",\n";
    meta_file << "    \"rx_capture_seconds\": " << rx_seconds << ",\n";
    meta_file << "    \"settle_seconds\": " << cfg.settle_seconds << ",\n";
    meta_file << "    \"block_samps\": " << block_samps << ",\n";
    meta_file << "    \"write_rx_event_csv\": " << (cfg.write_rx_event_csv ? "true" : "false") << ",\n";
    meta_file << "    \"write_full_rx_metadata\": " << (cfg.write_full_rx_metadata ? "true" : "false") << ",\n";
    meta_file << "    \"device_args\": \"" << json_escape(cfg.device_args) << "\",\n";
    meta_file << "    \"clock_source\": \"" << json_escape(cfg.clock_source) << "\",\n";
    meta_file << "    \"time_source\": \"" << json_escape(cfg.time_source) << "\",\n";
    meta_file << "    \"tx_ant\": \"" << json_escape(cfg.tx_ant) << "\",\n";
    meta_file << "    \"rx_ant\": \"" << json_escape(cfg.rx_ant) << "\"\n";
    meta_file << "  },\n";
    meta_file << "  \"applied\": {\n";
    meta_file << "    \"sample_rate_sps\": " << usrp->get_rx_rate() << ",\n";
    meta_file << "    \"tx_center_freq_hz\": " << usrp->get_tx_freq() << ",\n";
    meta_file << "    \"rx_center_freq_hz\": " << usrp->get_rx_freq() << ",\n";
    meta_file << "    \"tx_gain_db\": " << usrp->get_tx_gain() << ",\n";
    meta_file << "    \"rx_gain_db\": " << usrp->get_rx_gain() << ",\n";
    meta_file << "    \"tx_ant\": \"" << json_escape(dcfg.tx.ant) << "\",\n";
    meta_file << "    \"rx_ant\": \"" << json_escape(dcfg.rx.ant) << "\"\n";
    meta_file << "  },\n";
    meta_file << "  \"capture\": {\n";
    meta_file << "    \"iq_format\": \"sc16\",\n";
    meta_file << "    \"bytes_per_complex_sample\": 4,\n";
    meta_file << "    \"iq_file_bytes\": " << iq_bytes << ",\n";
    meta_file << "    \"rx_samples_written\": " << rxs.samps << ",\n";
    meta_file << "    \"estimated_rx_seconds_written\": " << captured_seconds << "\n";
    meta_file << "  },\n";
    meta_file << "  \"tx_stats\": {\n";
    meta_file << "    \"sends\": " << txs.sends << ",\n";
    meta_file << "    \"samples\": " << txs.samps << ",\n";
    meta_file << "    \"underflows\": " << txs.underflows << ",\n";
    meta_file << "    \"sequence_errors\": " << txs.seq_err << ",\n";
    meta_file << "    \"timeouts\": " << txs.timeouts << "\n";
    meta_file << "  },\n";
    meta_file << "  \"rx_stats\": {\n";
    meta_file << "    \"blocks\": " << rxs.blocks << ",\n";
    meta_file << "    \"samples\": " << rxs.samps << ",\n";
    meta_file << "    \"overflows\": " << rxs.overflows << ",\n";
    meta_file << "    \"timeouts\": " << rxs.timeouts << ",\n";
    meta_file << "    \"other_errors\": " << rxs.other_err << ",\n";
    meta_file << "    \"metadata_rows\": " << rxs.meta_rows << "\n";
    meta_file << "  }\n";
    meta_file << "}\n";
}

int main() {
    try {
        // Edit experiment settings in include/apps/full_duplex_run_config.hpp.
        const app::FullDuplexRunConfig cfg = app::default_full_duplex_run_config();
        const double rx_seconds = app::rx_capture_seconds(cfg);
        const size_t block_samps = (cfg.block_samps == 0)
            ? app::default_block_samps_for_rate(cfg.sample_rate_sps)
            : cfg.block_samps;
        const std::string tag = build_run_tag(cfg);
        const std::string started_utc = timestamp_utc_like();

        // Create unique run directory
        std::filesystem::path run_dir = cfg.output_dir;
        std::error_code ec;
        std::filesystem::create_directories(run_dir, ec);
        if (ec) throw std::runtime_error("Failed to create output dir: " + run_dir.string());

        const std::string fs_tag = format_rate_tag(cfg.sample_rate_sps) + "_" + tag;
        const std::string duration_tag = format_duration_tag(cfg.tx_seconds);

        // output paths
        const std::string iq_path =
            (cfg.output_dir / ("rx_iq_sc16_" + fs_tag + "_" + duration_tag + ".bin")).string();

        const std::string rx_event_path =
            (cfg.output_dir / ("rx_events_" + fs_tag + "_" + duration_tag + ".csv")).string();

        const std::string manifest_path =
            (cfg.output_dir / ("run_metadata_" + fs_tag + "_" + duration_tag + ".json")).string();

        // ---------------- Device config ----------------
        usrp::DeviceConfig dcfg;

        // N210/GigE tuning goes here (adjust recv_frame_size/num_recv_frames if needed)
        dcfg.device_args  = cfg.device_args;
        dcfg.clock_source = cfg.clock_source;
        dcfg.time_source  = cfg.time_source;
        dcfg.channels     = cfg.channels;

        // TX (RF1)
        dcfg.tx.rate_sps = cfg.sample_rate_sps;
        dcfg.tx.freq_hz  = cfg.tx_center_freq_hz;
        dcfg.tx.gain_db  = cfg.tx_gain_db;
        dcfg.tx.ant      = cfg.tx_ant;

        // RX (RF2)
        dcfg.rx.rate_sps = cfg.sample_rate_sps;
        dcfg.rx.freq_hz  = cfg.rx_center_freq_hz;
        dcfg.rx.gain_db  = cfg.rx_gain_db;
        dcfg.rx.ant      = cfg.rx_ant;
        dcfg.rx.enable_dc_offset = cfg.rx_enable_dc_offset;
        dcfg.rx.enable_iq_balance = cfg.rx_enable_iq_balance;

        usrp::Device dev(dcfg);
        std::cout << dev.pp_string() << "\n";


// ---------------- Force LO re-tune (apply calibration tables) ----------------
        auto usrp = dev.handle();

        std::cout << "Forcing RX/TX LO re-tune to apply calibration...\n";
        usrp->set_rx_freq(cfg.rx_center_freq_hz);
        usrp->set_tx_freq(cfg.tx_center_freq_hz);

// Optional but sometimes helpful on older UHD / N210:
std::this_thread::sleep_for(std::chrono::milliseconds(50));

        // ---------------- TX tone config ----------------
        usrp::TxToneConfig tcfg;
        tcfg.tone_hz    = cfg.tx_tone_freq_hz;
        tcfg.amplitude  = cfg.tx_amplitude;
        tcfg.tx_seconds = cfg.tx_seconds;
        tcfg.send_timeout_s = cfg.tx_send_timeout_s;
        tcfg.enable_async_monitor = true;

        usrp::TxTone txtone(dev, tcfg);

        // ---------------- RX capture config ----------------
        usrp::RxCaptureConfig rcfg;
        rcfg.capture_seconds = rx_seconds;
        rcfg.queue_capacity_blocks = cfg.queue_capacity_blocks;
        rcfg.timeout_s = cfg.rx_timeout_s;

        // Key high-rate knobs (match your upgraded rx_stream)
        rcfg.block_samps = block_samps;
        rcfg.write_full_metadata = cfg.write_full_rx_metadata;
        rcfg.iq_file_buffer_bytes = cfg.iq_file_buffer_bytes;
        rcfg.meta_file_buffer_bytes = cfg.meta_file_buffer_bytes;

        // Front-end cleanup (helps settling; adjust as needed)
        rcfg.discard_samps = static_cast<size_t>(cfg.settle_seconds * cfg.sample_rate_sps);

        rcfg.iq_path   = iq_path;
        rcfg.meta_path = cfg.write_rx_event_csv ? rx_event_path : std::string{};

        usrp::RxCapture rxcap(dev, rcfg);

        // ---------------- Live monitor: runtime + file growth ----------------
        std::atomic<bool> running{true};
        auto t0 = std::chrono::steady_clock::now();

        std::thread mon_thread([&](){
            using namespace std::chrono;
            while (running.load(std::memory_order_relaxed)) {
                auto now = steady_clock::now();
                double sec = duration<double>(now - t0).count();

                uintmax_t bytes = safe_filesize(rcfg.iq_path);
                double est_samps = bytes / 4.0;   // sc16 IQ = 4 bytes per complex sample
                double est_rx_sec = est_samps / cfg.sample_rate_sps;

                std::cout << "\r"
                          << std::fixed << std::setprecision(2)
                          << "t=" << sec << " s"
                          << " | rx_file=" << (bytes / 1e6) << " MB"
                          << " (~" << est_rx_sec << " s)"
                          << std::flush;

                std::this_thread::sleep_for(std::chrono::milliseconds(500));
            }
            std::cout << "\n";
        });

        // ---------------- Run full duplex ----------------
        std::cout << "Starting TX...\n";
        usrp::TxStats txs;
        std::thread tx_thread([&]() {
            txs = txtone.run();
            std::cout << "TX done:\n"
                      << "  sends=" << txs.sends
                      << " samps=" << txs.samps
                      << " underflows=" << txs.underflows
                      << " seq_err=" << txs.seq_err
                      << " timeouts=" << txs.timeouts << "\n";
        });

        std::this_thread::sleep_for(std::chrono::milliseconds(150));

        std::cout << "Starting RX...\n";
        auto rxs = rxcap.run();
        std::cout << "RX done:\n"
                  << "  blocks=" << rxs.blocks
                  << " samps=" << rxs.samps
                  << " overflows=" << rxs.overflows
                  << " timeouts=" << rxs.timeouts
                  << " other_err=" << rxs.other_err
                  << " meta_rows=" << rxs.meta_rows << "\n";

        tx_thread.join();

        running.store(false);
        mon_thread.join();

        const std::string finished_utc = timestamp_utc_like();
        const uintmax_t iq_bytes = safe_filesize(rcfg.iq_path);
        write_run_metadata_json(
            manifest_path,
            cfg,
            dcfg,
            usrp,
            iq_path,
            rx_event_path,
            txs,
            rxs,
            iq_bytes,
            started_utc,
            finished_utc
        );

        std::cout << "Wrote:\n"
                  << "  " << rcfg.iq_path << "\n"
                  << "  " << manifest_path << "\n";
        if (!rcfg.meta_path.empty()) {
            std::cout << "  " << rcfg.meta_path << "\n";
        }

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "FATAL: " << e.what() << "\n";
        return 1;
    }
}
