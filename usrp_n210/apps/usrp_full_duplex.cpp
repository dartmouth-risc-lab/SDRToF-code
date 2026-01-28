#include "usrp/device.hpp"
#include "usrp/rx_stream.hpp"
#include "usrp/tx_stream.hpp"

#include <atomic>
#include <chrono>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <thread>

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

int main() {
    try {
        // -------------------- Run parameters (edit here) --------------------
        const double Fs = 1e6;     // sample rate (try 1e6, 5e6, 10e6)
        const double Fc = 100e6;    // RF LO
        const double fb = 100e3;    // TX baseband tone
        const double tx_seconds = 45.0;
        const double rx_seconds = tx_seconds + 0.5;

        // Output base directory
        const std::filesystem::path out_dir = "/home/risc/ram/USRP/usrp_software/usrp_n210/data/usrp_runs/";
        const std::string tag = "loopback"; // any label you want in filenames
        // --------------------------------------------------------------------

        // Create unique run directory
        // const std::string stamp = timestamp_utc_like();
        std::string stamp = ""; 
        // const std::filesystem::path run_dir = out_dir / (stamp + "_" + tag);
        std::filesystem::path run_dir = out_dir; 
        std::error_code ec;
        std::filesystem::create_directories(run_dir, ec);
        if (ec) throw std::runtime_error("Failed to create output dir: " + run_dir.string());

        const double Fs_msps = Fs / 1e6;
        std::ostringstream fs_tag;

        fs_tag << std::fixed << std::setprecision(
            (Fs_msps == std::floor(Fs_msps)) ? 0 : 1
         )
       << Fs_msps << "msps";
        
       // output paths
        const std::string iq_path =
            (out_dir / ("rx_iq_sc16_" + fs_tag.str() + ".bin")).string();

        const std::string meta_path =
            (out_dir / ("rx_meta_" + fs_tag.str() + ".csv")).string();


        // ---------------- Device config ----------------
        usrp::DeviceConfig dcfg;

        // N210/GigE tuning goes here (adjust recv_frame_size/num_recv_frames if needed)
        dcfg.device_args  =
            "addr=192.168.10.2,"
            "recv_frame_size=8192,num_recv_frames=256,"
            "send_frame_size=8192,num_send_frames=256";

        dcfg.clock_source = "internal";
        dcfg.time_source  = "none";
        dcfg.channels     = {0};

        // TX (RF1)
        dcfg.tx.rate_sps = Fs;
        dcfg.tx.freq_hz  = Fc;
        dcfg.tx.gain_db  = 5.0;
        dcfg.tx.ant      = "TX/RX";

        // RX (RF2)
        dcfg.rx.rate_sps = Fs;
        dcfg.rx.freq_hz  = Fc;
        dcfg.rx.gain_db  = 15.0;
        dcfg.rx.ant      = "RX2";

        usrp::Device dev(dcfg);
        std::cout << dev.pp_string() << "\n";

        // ---------------- TX tone config ----------------
        usrp::TxToneConfig tcfg;
        tcfg.tone_hz    = fb;
        tcfg.amplitude  = 0.2;
        tcfg.tx_seconds = tx_seconds;
        tcfg.enable_async_monitor = true;

        usrp::TxTone txtone(dev, tcfg);

        // ---------------- RX capture config ----------------
        usrp::RxCaptureConfig rcfg;
        rcfg.capture_seconds = rx_seconds;
        rcfg.queue_capacity_blocks = 256;

        // Key high-rate knobs (match your upgraded rx_stream)
        rcfg.block_samps = (Fs <= 1e6) ? 65536 : (Fs <= 5e6 ? 131072 : 262144);
        rcfg.write_full_metadata = false;                 // error-only rows
        rcfg.iq_file_buffer_bytes = 8 * 1024 * 1024;      // 8MB
        rcfg.meta_file_buffer_bytes = 1 * 1024 * 1024;    // 1MB

        rcfg.iq_path   = iq_path;
        rcfg.meta_path = meta_path;

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
                double est_rx_sec = est_samps / Fs;

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
        std::thread tx_thread([&]() {
            auto txs = txtone.run();
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

        std::cout << "Wrote:\n"
                  << "  " << rcfg.iq_path << "\n"
                  << "  " << rcfg.meta_path << "\n";

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "FATAL: " << e.what() << "\n";
        return 1;
    }
}
