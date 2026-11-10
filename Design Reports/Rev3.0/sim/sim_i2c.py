"""(b) I2C SCL rise time vs pull-up, Cb = 100 pF (and 50 pF), 400 kHz Fast-mode.

Driver: ideal open-drain switch (Ron = 50 ohm) toggling at 400 kHz, 50 % duty.
Rise time measured between 0.3*VDD and 0.7*VDD as defined by the I2C specification (limit 300 ns).
Engine: ngspice 46 shared lib (KiCad 10) via PySpice 1.5
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from ngspice_helper import run_netlist

HERE = Path(__file__).resolve().parent
PLOTS = HERE / "plots"
VDD = 3.3

def netlist(Rp, Cb):
    return f"""I2C SCL Rp={Rp} Cb={Cb}
Vdd vdd 0 {VDD}
Vctl ctl 0 PULSE(1 0 0 2n 2n 1.25u 2.5u)
S1 scl 0 ctl 0 SW
.model SW SW(Ron=50 Roff=1G Vt=0.5 Vh=0.05)
Rp vdd scl {Rp}
Cb scl 0 {Cb}p
.tran 1n 5u 0 1n
.end
"""

def rise_fall(t, v):
    # SCL is released at t = 0 and 2.5 us, pulled low at 1.25 us and 3.75 us. Use the 2nd cycle.
    m = (t >= 2.5e-6) & (t < 3.75e-6)
    tt, vv = t[m], v[m]
    i30 = np.argmax(vv >= 0.3 * VDD); i70 = np.argmax(vv >= 0.7 * VDD)
    tr = tt[i70] - tt[i30]
    m2 = (t >= 3.75e-6) & (t < 5.0e-6)
    tt2, vv2 = t[m2], v[m2]
    j70 = np.argmax(vv2 <= 0.7 * VDD); j30 = np.argmax(vv2 <= 0.3 * VDD)
    tf = tt2[j30] - tt2[j70]
    vol = vv2[-1]
    # time SCL spends above 0.7 VDD within the 1.25 us 'high' phase (spec tHIGH min = 0.6 us)
    t_high = tt[-1] - tt[i70]
    return tr, tf, vol, t_high

results = {}
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
for ax, Cb in zip(axes, (100, 50)):
    for Rp in (2200, 4700, 10000):
        d = run_netlist(netlist(Rp, Cb))
        t = d["time"]; v = d["v(scl)"]
        tr, tf, vol, th = rise_fall(t, v)
        results[f"Rp_{Rp}_Cb_{Cb}pF"] = dict(tr_30_70_ns=round(float(tr * 1e9), 1), tf_70_30_ns=round(float(tf * 1e9), 1),
                                             VOL_V=round(float(vol), 3), tHIGH_above_0p7VDD_ns=round(float(th * 1e9), 0),
                                             formula_tr_ns=round(0.8473 * Rp * Cb * 1e-12 * 1e9, 1),
                                             passes_300ns=bool(tr <= 300e-9),
                                             I_sink_mA=round(float((VDD - vol) / Rp * 1e3), 2))
        print(Rp, Cb, results[f"Rp_{Rp}_Cb_{Cb}pF"])
        ax.plot((t - 2.5e-6) * 1e9, v, label=f"Rp = {Rp/1e3:g} k, tr = {tr*1e9:.0f} ns")
    ax.axhline(0.3 * VDD, color="k", ls=":", lw=0.6); ax.axhline(0.7 * VDD, color="k", ls=":", lw=0.6)
    ax.axvline(300, color="r", ls="--", lw=0.8); ax.text(305, 0.2, "300 ns Fast-mode limit", color="r", fontsize=8)
    ax.set_xlim(-50, 1300); ax.set_xlabel("time from release (ns)"); ax.set_ylabel("V(SCL) (V)")
    ax.set_title(f"SCL rise, Cb = {Cb} pF, 400 kHz"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(PLOTS / "i2c_scl_rise.png", dpi=130); plt.close()
with open(HERE / "results_i2c.json", "w") as fh:
    json.dump(results, fh, indent=1)
print("written results_i2c.json")
