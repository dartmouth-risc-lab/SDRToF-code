import matplotlib.pyplot as plt
from scipy.signal import kaiserord, firwin, upfirdn, filtfilt, butter, sosfiltfilt, welch, detrend, lfilter
import numpy as np

# ==============================================================================
# 1. INSTRUMENT CONFIGURATION & PHYSICS
# ==============================================================================

def design_kaiser_lpf(fs, fp_hz, fsb_hz, attenuation_db=100):
    """
    Kaiser-window FIR LPF.
    fp_hz  : passband edge (Hz)
    fsb_hz : stopband edge (Hz) (must be > fp_hz)
    """
    nyq = 0.5 * fs
    if not (0 < fp_hz < fsb_hz < nyq):
        raise ValueError(f"Bad edges: fp={fp_hz}, fsb={fsb_hz}, nyq={nyq}")

    width = (fsb_hz - fp_hz) / nyq
    numtaps, beta = kaiserord(attenuation_db, width)
    if numtaps % 2 == 0:
        numtaps += 1

    # Place cutoff in the middle of the transition band
    fc = 0.5 * (fp_hz + fsb_hz)
    taps = firwin(numtaps, fc, fs=fs, window=("kaiser", beta))
    taps = taps / np.sum(taps)
    return taps



def decimate_stage_fir(x, fs_in, M, fp_keep_hz, attenuation_db=100, guard_frac=0.10):
    """
    FIR anti-alias + decimate by M.
    fp_keep_hz : content you want to preserve through this stage (Hz).
    guard_frac : fraction of new Nyquist reserved for transition band.
    """
    fs_out = fs_in / M
    nyq_out = 0.5 * fs_out

    # Passband edge: keep what we need, but never exceed something comfortable below nyq_out
    fp = min(fp_keep_hz, 0.45 * fs_out)

    # Stopband edge: new Nyquist (where aliasing starts)
    # Build a transition band that ends at nyq_out, starts at fp
    # If fp is too close to nyq_out, force a minimum transition using guard_frac
    min_fp = (1.0 - guard_frac) * nyq_out
    if fp > min_fp:
        fp = min_fp

    fsb = nyq_out

    taps = design_kaiser_lpf(fs_in, fp_hz=fp, fsb_hz=fsb, attenuation_db=attenuation_db)
    # taps = taps / np.sum(taps)

    # Polyphase-friendly decimation using upfirdn
    y = upfirdn(taps, x, up=1, down=M)

    # Trim FIR group delay in output-rate samples:
    gd_in = (len(taps) - 1) // 2
    gd_out = int(np.ceil(gd_in / M))
    if 2 * gd_out < len(y):
        y = y[gd_out:-gd_out]

    return y, fs_out, taps




def apply_decimation_chain(x, fs_in, factors, bw_meas_hz, attenuation_db=100):
    """
    Multi-stage decimation where each stage only preserves bw_meas_hz (plus margin),
    ensuring strong anti-aliasing without giant early filters.
    """
    cur_fs = fs_in
    y = x

    print(f"--- Decimation chain start: Fs={cur_fs/1e6:.3f} MSPS ---")
    for i, M in enumerate(factors, 1):
        # Keep slightly more than final BW so the last-stage spec FIR has room
        fp_keep = bw_meas_hz * 1.25

        y, next_fs, taps = decimate_stage_fir(
            y, fs_in=cur_fs, M=M, fp_keep_hz=fp_keep,
            attenuation_db=attenuation_db, guard_frac=0.10
        )

        # taps = taps / np.sum(taps)

        print(f"Stage {i}: /{M:>2} | {cur_fs/1e3:>9.1f} kHz -> {next_fs/1e3:>9.1f} kHz | taps={len(taps)}")
        cur_fs = next_fs

    print(f"--- Decimation chain end: Fs={cur_fs/1e3:.3f} kSPS ---")
    return y, cur_fs





def IQ_filter(SIG, FS_INPUT, FS_INSTRUMENT = 48e3, BW_MEASUREMENT =  25e3, HPF_CUTOFF = 70.0, LPF_TRANSITION_BW = 1e3,
              DECIM_FACTORS=[8,4,4]):

    fp_final = BW_MEASUREMENT # cutoff after the instrument bandwidth
    fsb_final = fp_final + LPF_TRANSITION_BW # fast transition


    y_complex = SIG

    # Physics constants
    C_LIGHT = 3e8
    # F_MOD   = fc + fb
    # K_RAD_TO_METER = C_LIGHT / (4 * np.pi * F_MOD)


    # ==============================================================================
    # 3. PROCESSING PIPELINE
    # ==============================================================================
    y_decim, fs_final = apply_decimation_chain(
        y_complex, FS_INPUT, DECIM_FACTORS, bw_meas_hz=BW_MEASUREMENT, attenuation_db=100)

    if abs(fs_final - FS_INSTRUMENT) > 1e-6:
        print(f"WARNING: fs_final={fs_final} Hz does not match FS_INSTRUMENT={FS_INSTRUMENT} Hz")

# Final "spec" LPF at final rate (strong, flexible)
# Choose a transition width that actually fits: at 78 kSPS, Nyquist=10 kHz
# So BW_MEASUREMENT must be atleast 20 kHz. 
    if fsb_final <= fp_final:
        raise ValueError("Final filter transition doesn't fit. Reduce BW_MEASUREMENT or FINAL_TRANS_HZ, or raise fs_final.")

    b_final = design_kaiser_lpf(fs_final, fp_hz=fp_final, fsb_hz=fsb_final, attenuation_db=120)
    b_final = b_final / np.sum(b_final)

     # Causal FIR filtering (embedded-friendly implementation).
    y_clean = lfilter(b_final, 1.0, y_decim)

    # Remove startup transient (zero initial conditions)
    gd_final = (len(b_final) - 1) // 2
    # print("gd_final: ", gd_final)

    trim = 10 * gd_final  # 2–4x is typical
    if trim < len(y_clean):
        y_clean = y_clean[trim:]

    return y_clean, fs_final
