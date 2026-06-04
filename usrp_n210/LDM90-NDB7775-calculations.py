#!/usr/bin/env python3
# RF Vpp Calculator (pint REQUIRED) — Esc and Q/q to quit
# Adds "Laser Diode" section with Max diode current (mA), default 400 mA, locked by default.
# Enforces that RF swing never exceeds the diode max: Ibias + Ipk <= I_LD_max.

import sys
import math
import tkinter as tk
from tkinter import ttk, messagebox

# ----- Require pint -----
try:
    from pint import UnitRegistry
except Exception:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "Missing dependency: pint",
        "This app requires the 'pint' package for unit-aware calculations.\n\n"
        "Install it with:\n\n pip install pint\n\n"
        "Then re-run the program."
    )
    sys.exit(1)

ureg = UnitRegistry()
Q_ = ureg.Quantity

APP_TITLE = "RF Vpp for Laser Modulation (AC-coupled RF Port, pint required)"

DEFAULTS = {
    "imin_mA": 140.0,
    "imax_mA": 200.0,
    "r_ohm": 50.0,
    "p_lim_mw": 200.0,  # mW
    "ld_max_mA": 400.0,  # Laser diode absolute max current
}

HELP_TEXT = (
    "Assumes the RF input is AC-coupled via a bias-tee (no DC offset passes). "
    "Set the DC bias (midpoint) on your laser current driver. "
    "Set the signal generator to a sine in 50 Ω output mode with the shown Vpp and 0 V offset."
)


def fmt(q, unit=None, digits=3):
    """Pretty-print a pint Quantity (or float) with optional unit coercion."""
    if isinstance(q, (int, float)):
        val = float(q)
        suffix = ""
    else:
        q = q.to(unit) if unit else q
        val = float(q.magnitude)
        suffix = f" {q.units}" if str(q.units) else ""

    if val == 0.0:
        s = "0"
    else:
        av = abs(val)
        if av >= 1e4 or av < 1e-2:
            s = f"{val:.2e}"
        else:
            s = f"{val:.{digits}f}".rstrip("0").rstrip(".")
    return s + suffix


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(760, 560)
        self._build_ui()
        self._bind_hotkeys()

    # --- Hotkeys: Esc and Q/q to quit ---
    def _bind_hotkeys(self):
        for seq in ("<Escape>", "q", "Q"):
            self.bind(seq, lambda e: self.destroy())

    def _build_ui(self):
        pad = 10
        main = ttk.Frame(self, padding=pad)
        main.pack(fill="both", expand=True)

        # Optional nicer theme if present
        style = ttk.Style(self)
        try:
            self.tk.call("source", "azure.tcl")
            style.theme_use("azure")
        except Exception:
            pass

        ttk.Label(main, text=APP_TITLE, font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(main, text=HELP_TEXT, wraplength=720).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(4, 10)
        )

        # ---- Inputs: desired current range ----
        inputs = ttk.LabelFrame(main, text="Desired Diode Current Range")
        inputs.grid(row=2, column=0, sticky="nsew", padx=(0, pad))

        self.imin = tk.DoubleVar(value=DEFAULTS["imin_mA"])
        self.imax = tk.DoubleVar(value=DEFAULTS["imax_mA"])

        def add_row(parent, r, label, var, unit):
            ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=8, pady=6)
            e = ttk.Entry(parent, textvariable=var, width=12, justify="right")
            e.grid(row=r, column=1, sticky="w")
            ttk.Label(parent, text=unit).grid(row=r, column=2, sticky="w", padx=(6, 8))
            return e

        add_row(inputs, 0, "Min diode current", self.imin, "mA")
        add_row(inputs, 1, "Max diode current", self.imax, "mA")

        ttk.Button(inputs, text="Calculate", command=self.calculate).grid(
            row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(8, 10)
        )

        # ---- LDM/RF params (locked by default) ----
        params = ttk.LabelFrame(main, text="LDM / RF Parameters")
        params.grid(row=2, column=1, sticky="nsew")

        self.r_ohm = tk.DoubleVar(value=DEFAULTS["r_ohm"])
        self.p_lim_mw = tk.DoubleVar(value=DEFAULTS["p_lim_mw"])

        self.ent_r = add_row(params, 0, "RF input impedance", self.r_ohm, "Ω")
        self.ent_plim = add_row(params, 1, "Max RF input power", self.p_lim_mw, "mW")

        # ---- Laser Diode params (locked by default) ----
        ld = ttk.LabelFrame(main, text="Laser Diode")
        ld.grid(row=2, column=2, sticky="nsew")

        self.ld_max_mA = tk.DoubleVar(value=DEFAULTS["ld_max_mA"])
        self.ent_ldmax = add_row(ld, 0, "Max diode current", self.ld_max_mA, "mA")

        # Gray out all parameter entries initially
        for w in (self.ent_r, self.ent_plim, self.ent_ldmax):
            w.configure(state="disabled")

        # One toggle button controls all grayed-out parameter sections
        self.edit_mode = False
        self.toggle_btn = ttk.Button(
            main, text="Edit LDM/RF & Laser Diode parameters", command=self.toggle_params
        )
        self.toggle_btn.grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(8, 10))

        # ---- Results ----
        results = ttk.LabelFrame(main, text="Results")
        results.grid(row=4, column=0, columnspan=3, sticky="nsew", pady=(4, 0))

        self.out_bias = ttk.Label(results, font=("Segoe UI", 11, "bold"))
        self.out_bias.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))

        self.out_gen = ttk.Label(results, justify="left")
        self.out_gen.grid(row=1, column=0, sticky="w", padx=8)

        self.out_vals = ttk.Label(results, justify="left")
        self.out_vals.grid(row=2, column=0, sticky="w", padx=8, pady=(6, 2))

        self.out_info = ttk.Label(results, justify="left", foreground="#374151")  # muted info
        self.out_info.grid(row=3, column=0, sticky="w", padx=8, pady=(2, 2))

        self.out_warn = ttk.Label(results, foreground="#c2410c", justify="left", wraplength=720)
        self.out_warn.grid(row=4, column=0, sticky="w", padx=8, pady=(6, 10))

        # Stretch layout
        for c in (0, 1, 2):
            main.grid_columnconfigure(c, weight=1)
        main.grid_rowconfigure(4, weight=1)

        self.calculate()

    def toggle_params(self):
        self.edit_mode = not self.edit_mode
        state = "normal" if self.edit_mode else "disabled"
        for w in (self.ent_r, self.ent_plim, self.ent_ldmax):
            w.configure(state=state)
        self.toggle_btn.config(
            text=("Lock parameters" if self.edit_mode else "Edit LDM/RF & Laser Diode parameters")
        )

    def calculate(self):
        try:
            imin_mA = float(self.imin.get())
            imax_mA = float(self.imax.get())
            R_ohm = float(self.r_ohm.get())
            Plim_mW = float(self.p_lim_mw.get())
            LDmax_mA = float(self.ld_max_mA.get())
        except Exception:
            messagebox.showerror("Input error", "Please enter valid numbers.")
            return

        if imax_mA < imin_mA:
            messagebox.showerror("Input error", "Max current must be ≥ min current.")
            return
        if R_ohm <= 0:
            messagebox.showerror("Input error", "Impedance must be > 0 Ω.")
            return
        if LDmax_mA <= 0:
            messagebox.showerror("Input error", "Laser diode max current must be > 0 mA.")
            return
        if imin_mA > LDmax_mA:
            messagebox.showerror(
                "Input error",
                "Requested minimum current exceeds the laser diode's max current."
            )
            return

        # ----- Unit-aware math with pint -----
        imin = Q_(max(0.0, imin_mA), "mA").to("A")  # clamp min to 0 mA
        imax_req = Q_(imax_mA, "mA").to("A")
        R = Q_(R_ohm, "ohm")
        Plim = Q_(Plim_mW, "mW").to("W")
        LDmax = Q_(LDmax_mA, "mA").to("A")

        # Enforce diode max on the requested max current
        imax_eff = imax_req
        ld_clamped = False
        if imax_req > LDmax:
            imax_eff = LDmax
            ld_clamped = True

        # Recompute midpoint/swing from imin and the EFFECTIVE (clamped) imax
        Ibias = (imax_eff + imin) / 2
        Ipk = (imax_eff - imin) / 2

        # (AC-coupled RF requires symmetric swing about bias; this keeps the user-requested MIN,
        # and reduces the swing if their MAX exceeds LD limit.)
        # Electrical values
        Vpk = Ipk * R
        Vpp = 2 * Vpk
        Vrms = Vpk / math.sqrt(2)
        P = (Vrms * Vrms) / R
        P_w = P.to("W").magnitude
        dBm = -math.inf if P_w <= 0 else 10.0 * math.log10(P_w / 1e-3)

        # ----- Outputs -----
        self.out_bias.config(text=f"Laser driver DC bias (midpoint): {fmt(Ibias, 'mA', 2)}")

        gen_lines = [
            "Signal generator (sine, 50 Ω output mode):",
            f" • Set Vpp = {fmt(Vpp, 'V', 3)}",
            f" • Set DC offset = 0 V (AC-coupled RF input)",
        ]
        self.out_gen.config(text="\n".join(gen_lines))

        # Info line: requested vs effective range
        req_line = f"Requested range: {fmt(imin, 'mA', 2)} → {fmt(imax_req, 'mA', 2)}"
        eff_line = f"Effective (enforced) range: {fmt(Ibias - Ipk, 'mA', 2)} → {fmt(Ibias + Ipk, 'mA', 2)}"
        self.out_info.config(text=f"{req_line}\n{eff_line}")

        swing = f"Current swing: ±{fmt(Ipk, 'mA', 2)}"
        voltages = f"Vpk = {fmt(Vpk, 'V', 3)}, Vrms = {fmt(Vrms, 'V', 3)}, Vpp = {fmt(Vpp, 'V', 3)}"
        power = f"RF power at input: {fmt(P, 'W', 4)} ({dBm:.2f} dBm) into {fmt(R, None, 2)}"
        self.out_vals.config(text="\n".join([swing, voltages, power]))

        # Warnings
        warns = []
        if ld_clamped:
            warns.append(
                f"Laser diode limit: Requested Imax exceeded {fmt(LDmax, 'mA', 2)} — "
                f"RF swing reduced so peak equals {fmt(imax_eff, 'mA', 2)}."
            )
        # Guard if min got clamped at 0
        if Q_(imin_mA, "mA") < Q_(0, "mA"):
            warns.append("Minimum current cannot be negative — clamped to 0 mA.")

        if Plim_mW > 0:
            P_mW = P.to("mW").magnitude
            if P_mW > Plim_mW:
                warns.append(f"RF power {P_mW:.1f} mW exceeds limit {Plim_mW:.1f} mW.")
            elif P_mW > 0.8 * Plim_mW:
                warns.append(f"RF power {P_mW:.1f} mW is close to the {Plim_mW:.1f} mW limit.")

        self.out_warn.config(text="\n".join(warns))


if __name__ == "__main__":
    App().mainloop()