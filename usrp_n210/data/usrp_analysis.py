#!/usr/bin/env python3
import os
import numpy as np
import matplotlib.pyplot as plt

# -----------------------
# Files (USRP capture)
# -----------------------
# Set this to your loopback_full_duplex output directory
dir = "/home/risc/ram/USRP/usrp_software/usrp_n210/data/usrp_runs/"  # change as needed

iq_file   = os.path.join(dir, "rx_iq_sc16_5msps.bin")
meta_csv  = os.path.join(dir, "rx_meta_5msps.csv")

fs = 1.0e6  # Hz (RX sample rate)
# -----------------------
# Analysis settings
# -----------------------
seconds_to_plot = 35.     # time-domain plot window (seconds)
skip_seconds    = 1.01     # skip initial transient (seconds)
max_samples     = None     # limit complex samples after conversion

# DDC settings
remove_dc_after_ddc = False
use_estimated_fb    = False

# If you know your injected tone:
fb = 100e3          # Hz (TX baseband tone)

# Plotting
plotRawIQ_constln = False
plotIQ_time       = False
plotDDC_IQ        = False
plot_phase        = True

avg_N = 2500

# -----------------------
# Load metadata (CSV from UHD)
# -----------------------
def load_meta_csv(meta_csv_path):
    """
    Reads CSV with columns:
      seq,nsamps,has_time,time_full,time_frac,err_code
    Returns dict with arrays and some convenience counts.
    """
    data = np.genfromtxt(meta_csv_path, delimiter=",", names=True, dtype=None, encoding=None)
    meta = {
        "seq": data["seq"].astype(np.int64),
        "nsamps": data["nsamps"].astype(np.int64),
        "has_time": data["has_time"].astype(np.int64),
        "time_full": data["time_full"].astype(np.int64),
        "time_frac": data["time_frac"].astype(np.float64),
        "err_code": data["err_code"].astype(np.int64),
    }
    meta["num_blocks"] = meta["seq"].size
    meta["total_samps_logged"] = int(np.sum(meta["nsamps"]))
    meta["num_err"] = int(np.sum(meta["err_code"] != 0))
    return meta


meta_blocks = load_meta_csv(meta_csv)

print(f"Meta blocks: {meta_blocks['num_blocks']}, total_samps_logged={meta_blocks['total_samps_logged']}, nonzero_err_blocks={meta_blocks['num_err']}")
# -----------------------
# Helper: robust IQ loader (USRP sc16)
# -----------------------
def load_usrp_sc16_as_complex64(iq_file_path, max_samples=None, normalize=True):
    """
    UHD sc16: interleaved int16 IQ: [I0,Q0,I1,Q1,...]
    Returns complex64 normalized to ~[-1,1) if normalize=True
    """
    raw = np.fromfile(iq_file_path, dtype=np.int16)
    if raw.size < 2:
        raise ValueError("File too short to contain IQ data.")
    if raw.size % 2 != 0:
        raw = raw[:-1]
    iq = raw.reshape(-1, 2)
    I = iq[:, 0].astype(np.float32)
    Q = iq[:, 1].astype(np.float32)

    if normalize:
        x = (I + 1j * Q) / 32768.0
    else:
        x = (I + 1j * Q)

    x = x.astype(np.complex64)
    if max_samples is not None:
        x = x[:max_samples]
    return x

# -----------------------
# Load IQ
# -----------------------
x = load_usrp_sc16_as_complex64(iq_file, max_samples=max_samples, normalize=True)
N0 = len(x)
print(f"Loaded {N0} complex samples ({N0/fs:.3f} s) from {iq_file}")

# Sanity: compare file samples vs metadata sum (should match closely)
if meta_blocks["total_samps_logged"] > 0:
    diff = N0 - meta_blocks["total_samps_logged"]
    print(f"Sample count CHECK: file - meta_sum = {diff} samples")
    # Small differences can happen if you ever changed writer logic; large differences = mismatch

# -----------------------
# Skip initial transient
# -----------------------
skip = int(skip_seconds * fs)
if skip >= N0:
    raise ValueError("skip_seconds is too large for the file length.")
x = x[skip:]
N = len(x)

# -----------------------
# Plot raw I/Q (time domain)
# -----------------------
M = int(seconds_to_plot * fs)
M = min(M, N)
t = np.arange(M) / fs

if plotIQ_time:
    plt.figure(figsize=(6, 4))
    plt.plot(t * 1e3, np.real(x[:M]), label="I (real)", linewidth=1.0)
    plt.plot(t * 1e3, np.imag(x[:M]), label="Q (imag)", linewidth=1.0)
    plt.xlabel("Time (ms)")
    plt.ylabel("Amplitude (norm)")
    plt.title("USRP Raw RX IQ")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

if plotRawIQ_constln:
    plt.figure(figsize=(5, 5))
    plt.scatter(np.real(x[:M]), np.imag(x[:M]), s=4, alpha=0.5)
    plt.xlabel("I")
    plt.ylabel("Q")
    plt.title("USRP Raw IQ Constellation")
    plt.grid(True, alpha=0.3)
    plt.axis("equal")
    plt.tight_layout()
    plt.show()

# -----------------------
# Digital downconversion (wipe off fb -> DC)
# -----------------------
n = np.arange(N, dtype=np.float64)
lo = np.exp(-1j * 2.0 * np.pi * fb * n / fs).astype(np.complex64)
y = x * lo

if remove_dc_after_ddc:
    y = y - np.mean(y)

# # -----------------------
# # Simple sample averaging (your exact Lime structure)
# # -----------------------
# avg_N = int(avg_N)
# if avg_N < 1:
#     avg_N = 1

# L = (len(y) // avg_N) * avg_N
# y2 = y[:L]
# y_avg = y2.reshape(-1, avg_N).mean(axis=1)
# fs_avg = fs / avg_N

# phi_avg = np.unwrap(np.angle(y_avg))
# M_ = int(seconds_to_plot * fs_avg)
# M_ = min(M_, len(phi_avg))
# t_avg = np.arange(M_) / fs_avg

# For reporting “raw DDC phase” 
phi_ddc = np.angle(y[:M])
phi_mean = float(np.mean(phi_ddc))
phi_std  = float(np.std(phi_ddc))

if plot_phase:
    plt.figure(figsize=(6, 4))
    plt.plot(t[:][::avg_N] * 1e3, phi_ddc[:][::avg_N], label="Averaged phase", linewidth=1.0)
    plt.xlabel("Time (ms)")
    plt.ylabel("Phase (rad)")
    plt.title("USRP Phase after DDC (expect ~constant + noise)")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

if plotDDC_IQ:
    plt.figure(figsize=(5, 5))
    plt.scatter(np.real(y[:M]), np.imag(y[:M]), s=4, alpha=0.5)
    plt.xlabel("I")
    plt.ylabel("Q")
    plt.title("USRP Downconverted IQ Constellation")
    plt.grid(True, alpha=0.3)
    plt.axis("equal")
    plt.tight_layout()
    plt.show()
