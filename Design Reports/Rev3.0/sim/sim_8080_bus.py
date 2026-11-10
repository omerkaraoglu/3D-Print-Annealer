"""(a) ESP32 -> SSD1963 8080 data / WR# line: series termination study.

Driver : PULSE 0 -> 3.3 V, tr = tf = 1.5 ns, behind Rout = 35 ohm (ESP32 at 20 mA drive setting)
Series : Rs in {0, 22, 33, 47} ohm at the driver
Line   : lossless T-line, Z0 in {55, 105, 130} ohm, TD = 60 mm * 6.5 ps/mm = 390 ps
Load   : SSD1963 input 8 pF || 1 Mohm
Engine : ngspice 46 shared lib (KiCad 10) via PySpice 1.5
"""
import json, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from ngspice_helper import run_netlist, spectrum

HERE = Path(__file__).resolve().parent
PLOTS = HERE / "plots"
VDD = 3.3; VIH = 0.8 * VDD; VIL = 0.2 * VDD
TD_PS = 60 * 6.5
RS_LIST = [0, 22, 33, 47]
Z0_LIST = [55, 105, 130]
T_RISE = 5e-9     # rising edge starts at 5 ns; high for 22.5 ns (45 % duty, so that the 5th/10th/15th
T_FALL = 27.5e-9  # harmonics at 100/200/300 MHz are not nulled by the duty-cycle sinc); falling edge at 27.5 ns
PERIOD = 50e-9

def netlist(Rs, Z0, stop, step, Cextra=0):
    rs = max(Rs, 1e-3)
    return f"""8080 line Rs={Rs} Z0={Z0}
V1 drv 0 PULSE(0 {VDD} {T_RISE} 1.5n 1.5n 21n {PERIOD})
Rout drv a 35
Rs a b {rs}
T1 b 0 c 0 Z0={Z0} TD={TD_PS}p
Cl c 0 {8 + Cextra}p
Rl c 0 1Meg
.tran {step} {stop} 0 {step}
.end
"""

def _after_first_extremum(v, start, rising=True):
    """Index of the first local max (rising) / min (falling) after 'start'; None if monotonic."""
    for i in range(start, len(v) - 1):
        if rising and v[i + 1] < v[i] - 2e-4:
            return i
        if not rising and v[i + 1] > v[i] + 2e-4:
            return i
    return None

def metrics(t, vc):
    # rising edge window: 5 .. 27.5 ns ; falling edge window: 27.5 .. 50 ns
    m_r = (t >= T_RISE) & (t < T_FALL)
    m_f = (t >= T_FALL) & (t < T_FALL + 22e-9)
    vr, tr_ = vc[m_r], t[m_r]
    vf = vc[m_f]
    overshoot = vr.max() - VDD
    # ring-back: lowest point after the FIRST PEAK that follows the VIH crossing (before the falling edge)
    idx = np.argmax(vr >= VIH) if np.any(vr >= VIH) else None
    if idx is None:
        ringback_min = float("nan"); t_vih = float("nan")
    else:
        ip = _after_first_extremum(vr, idx, rising=True)
        ringback_min = vr[ip:].min() if ip is not None else vr[-1]
        t_vih = tr_[idx] - T_RISE
    # 10-90 % rise time at the receiver
    i10 = np.argmax(vr >= 0.1 * VDD); i90 = np.argmax(vr >= 0.9 * VDD)
    t10_90 = tr_[i90] - tr_[i10]
    undershoot = vf.min()
    idxf = np.argmax(vf <= VIL) if np.any(vf <= VIL) else None
    if idxf is None:
        ringback_max = float("nan")
    else:
        ipf = _after_first_extremum(vf, idxf, rising=False)
        ringback_max = vf[ipf:].max() if ipf is not None else vf[-1]
    return dict(overshoot_V=round(float(overshoot), 3), peak_V=round(float(vr.max()), 3),
                ringback_min_V=round(float(ringback_min), 3), VIH_margin_V=round(float(ringback_min - VIH), 3),
                t_to_VIH_ns=round(float(t_vih * 1e9), 2), t10_90_ns=round(float(t10_90), 2) if False else round(float(t10_90 * 1e9), 2),
                undershoot_V=round(float(undershoot), 3), ringback_max_low_V=round(float(ringback_max), 3),
                VIL_margin_V=round(float(VIL - ringback_max), 3),
                meets_VIH_VIL=bool(ringback_min > VIH and ringback_max < VIL),
                peak_within_abs_max=bool(vr.max() < VDD + 0.5 and undershoot > -0.5))

results = {"settings": dict(VIH=VIH, VIL=VIL, TD_ps=TD_PS, Rout=35, tr_ns=1.5, Cload_pF=8), "transient": {}, "fft": {}}
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
for ax, Z0 in zip(axes, Z0_LIST):
    for Rs in RS_LIST:
        d = run_netlist(netlist(Rs, Z0, "60n", "2p"))
        t = d["time"]; vc = d["v(c)"]
        m = metrics(t, vc)
        results["transient"][f"Z0_{Z0}_Rs_{Rs}"] = m
        print(f"Z0={Z0:4d} Rs={Rs:2d}: {m}")
        ax.plot(t * 1e9, vc, label=f"Rs = {Rs} ohm")
    ax.axhline(VIH, color="k", ls="--", lw=0.7); ax.axhline(VIL, color="k", ls="--", lw=0.7)
    ax.axhline(VDD, color="grey", ls=":", lw=0.6); ax.axhline(0, color="grey", ls=":", lw=0.6)
    ax.text(41, VIH + 0.05, "VIH = 2.64 V", fontsize=7); ax.text(41, VIL + 0.05, "VIL = 0.66 V", fontsize=7)
    ax.set_xlim(0, 40); ax.set_title(f"Receiver V(c), Z0 = {Z0} ohm, TD = {TD_PS:.0f} ps"); ax.grid(alpha=0.3)
    ax.set_xlabel("time (ns)"); ax.legend(fontsize=8)
axes[0].set_ylabel("V (V)")
plt.tight_layout(); plt.savefig(PLOTS / "bus_receiver_waveforms.png", dpi=130); plt.close()

# --- zoom on the rising edge for Z0 = 105 and 130
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, Z0 in zip(axes, (105, 130)):
    for Rs in RS_LIST:
        d = run_netlist(netlist(Rs, Z0, "20n", "2p"))
        ax.plot(d["time"] * 1e9, d["v(c)"], label=f"Rs = {Rs}")
    ax.axhline(VIH, color="k", ls="--", lw=0.7); ax.axhline(VDD, color="grey", ls=":", lw=0.6)
    ax.set_xlim(4, 14); ax.set_ylim(-0.2, 4.6); ax.grid(alpha=0.3); ax.set_xlabel("time (ns)")
    ax.set_title(f"Rising edge detail, Z0 = {Z0} ohm"); ax.legend(fontsize=8)
axes[0].set_ylabel("V (V)")
plt.tight_layout(); plt.savefig(PLOTS / "bus_rising_edge_zoom.png", dpi=130); plt.close()

# --- option: Rs = 33 plus 22 pF at the receiver (deliberate edge slowing), Z0 = 105
for Z0 in (105, 55):
    d = run_netlist(netlist(33, Z0, "60n", "2p", Cextra=22))
    m = metrics(d["time"], d["v(c)"])
    results["transient"][f"Z0_{Z0}_Rs_33_plus22pF"] = m
    print(f"Z0={Z0} Rs=33 + 22 pF: {m}")

# --- FFT of the driver current (20 periods, 1 us, uniform 5 ps grid, Hann window)
DT = 5e-12
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
for ax, Z0 in zip(axes, (105, 55)):
    spec = {}
    for Rs in (0, 22, 33, 47, "33+22pF"):
        if Rs == "33+22pF":
            d = run_netlist(netlist(33, Z0, "1u", "5p", Cextra=22))
        else:
            d = run_netlist(netlist(Rs, Z0, "1u", "5p"))
        t = d["time"]; i = d["v1#branch"]
        f, amp = spectrum(t, i, DT)
        spec[Rs] = (f, amp)
        ax.semilogx(f / 1e6, 20 * np.log10(np.maximum(amp, 1e-12) / 1e-6), lw=0.8, label=f"Rs = {Rs}")
    # pick harmonics (bins at multiples of 20 MHz; resolution 1 MHz)
    res = {}
    for Rs, (f, amp) in spec.items():
        res[Rs] = {}
        for fh in (20, 60, 100, 140, 180, 200, 220, 300, 500):
            k = int(round(fh * 1e6 / (f[1] - f[0])))
            # take the max over +-2 bins to be robust against leakage
            a = amp[max(k - 2, 0):k + 3].max()
            res[Rs][f"{fh}MHz_dBuA"] = round(20 * math.log10(max(a, 1e-12) / 1e-6), 1)
    results["fft"][f"Z0_{Z0}"] = res
    for fh in (100, 200, 300):
        for Rs in (22, 33, 47, "33+22pF"):
            results["fft"][f"Z0_{Z0}"][f"reduction_Rs{Rs}_vs_0_at_{fh}MHz_dB"] = round(
                res[0][f"{fh}MHz_dBuA"] - res[Rs][f"{fh}MHz_dBuA"], 1)
    print(f"Z0={Z0} FFT:", json.dumps(results["fft"][f"Z0_{Z0}"], indent=0))
    for fh in (100, 200, 300):
        ax.axvline(fh, color="grey", ls=":", lw=0.6)
    ax.set_xlim(10, 1000); ax.set_ylim(0, 110); ax.grid(True, which="both", alpha=0.3)
    ax.set_xlabel("frequency (MHz)"); ax.set_ylabel("driver current (dBuA, peak)")
    ax.set_title(f"Driver-current spectrum, Z0 = {Z0} ohm (20 MHz, 45 % duty)"); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(PLOTS / "bus_driver_current_fft.png", dpi=130); plt.close()

with open(HERE / "results_8080_bus.json", "w") as fh:
    json.dump(results, fh, indent=1)
print("written results_8080_bus.json")
