"""C_rf step 7b (review follow-up) - +5V island impedance at the J10 re-sort via field for capacitor options.

Question: is the ~63 MHz peak that appears with 2 x 1 nF at the via field real, or an artefact of putting the capacitor at the
port that is measured? Check: (a) caps exactly at the measured port (as in c7), (b) caps at their own ports 2.5 mm away (real
0402 placement next to the vias), each with ESL 0.35 nH + mounting 0.77 nH (via to In2 0.45 + GND via 0.07 + pad/trace 0.25 nH)
-> a real anti-resonance shows in both; an artefact only in (a). Also reported: Z at U30 VIN and the L12/C127 pi input.
Options: none, 2 x 1 nF, 100 nF + 1 nF, 10 nF + 1 nF, 2 x 10 nF, 2 x 100 nF, 2 x (1 nF + 2.2 ohm), 2 x (10 nF + 1 ohm),
100 nF + (1 nF + 2.2 ohm). Target: <= 0.5 ohm below 300 MHz where possible, no new peak above it, 498.5 MHz stub removed.
Outputs: results.json["pdn"]["5V"]["J10_cap_options"], ["Z_J10_complex_with_<option>"], plots/pdn_j10_cap_options.png"""
import json, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from c0_common import *
src = open(os.path.join(HERE, "c7_pdn.py"), encoding="utf-8").read().split("# ------------------------------- +1V2")[0]
exec(src)                                   # builds the 3V3 and +5V island models exactly as c7 (f, Zm5, loads5, cavity_Z, zcap, ...)

def cap(C, R=0.0, n=1, esl=0.35e-9, esr=None):
    c = {"C": C, "ESL": esl, "ESR": (esr if esr is not None else (0.05 if C < 5e-9 else 0.03 if C < 0.5e-6 else 0.01)) + R, "Lmount": 0.77e-9}
    return c
OPTS = {"none": [], "2 x 1 nF": [cap(1e-9), cap(1e-9)], "100 nF + 1 nF": [cap(100e-9), cap(1e-9)], "10 nF + 1 nF": [cap(10e-9), cap(1e-9)],
        "2 x 10 nF": [cap(10e-9), cap(10e-9)], "2 x 100 nF": [cap(100e-9), cap(100e-9)],
        "2 x (1 nF + 2.2 ohm)": [cap(1e-9, 2.2), cap(1e-9, 2.2)], "2 x (10 nF + 1 ohm)": [cap(10e-9, 1.0), cap(10e-9, 1.0)],
        "100 nF + (1 nF + 2.2 ohm)": [cap(100e-9), cap(1e-9, 2.2)]}
J10 = (150.0, 108.0)
# separate-port geometry: caps 2.5 mm either side of the via-field port
base_ports = list(ports5.values()) + [(c["x"], min(max(c["y"], 90.0), 118.0)) for c in caps5 if c["ref"] != "C2"]
sep_ports = base_ports + [(J10[0] - 2.5, J10[1]), (J10[0] + 2.5, J10[1])]
Zsep = cavity_Z(sep_ports, a5, b5, x05, y05, f)
n0 = len(base_ports)
FX = (33.3, 63.0, 66.6, 99.9, 150.0, 166.5, 233.1, 300.0, 498.5)
out = {}
fig, ax = plt.subplots(1, 2, figsize=(14, 5))
for name, cl in OPTS.items():
    # (a) at the measured port (c7 method)
    la = dict(loads5)
    if cl:
        y = sum(1 / zcap(c, f) for c in cl)
        la[2] = 1 / y
    za = loaded_port(Zm5, la, ic=2) if cl else loaded_port(Zm5, loads5, ic=2)
    # (b) at their own ports 2.5 mm away
    lb = dict(loads5)
    for k, c in enumerate(cl):
        lb[n0 + k] = zcap(c, f)
    zb = loaded_port(Zsep, lb, ic=2)
    zu = loaded_port(Zsep, lb, ic=0)          # U30 VIN
    zp = loaded_port(Zsep, lb, ic=1)          # L12/C127 pi input
    mb = np.abs(zb)
    below = (f >= 1e6) & (f <= 300e6)
    pk = [i for i in range(1, len(f) - 1) if mb[i] > mb[i - 1] and mb[i] > mb[i + 1] and 1e6 < f[i] < 1.2e9]
    out[name] = {"Z_J10_at_MHz(caps at measured port)": {str(x): round(float(np.interp(x * 1e6, f, np.abs(za))), 3) for x in FX},
                 "Z_J10_at_MHz(caps 2.5 mm away)": {str(x): round(float(np.interp(x * 1e6, f, mb)), 3) for x in FX},
                 "Z_U30_VIN_at_MHz": {str(x): round(float(np.interp(x * 1e6, f, np.abs(zu))), 3) for x in FX},
                 "Z_L12_C127_at_MHz": {str(x): round(float(np.interp(x * 1e6, f, np.abs(zp))), 3) for x in FX},
                 "max_Z_J10_1-300MHz": round(float(mb[below].max()), 3), "at_MHz": round(float(f[below][np.argmax(mb[below])] / 1e6), 1),
                 "peaks_J10": [(round(float(f[i] / 1e6), 1), round(float(mb[i]), 2)) for i in pk][:6]}
    if name in ("none", "2 x 1 nF", "100 nF + 1 nF", "10 nF + 1 nF", "2 x (10 nF + 1 ohm)", "100 nF + (1 nF + 2.2 ohm)"):
        ax[0].loglog(f / 1e6, mb, label=name)
    ax[1].loglog(f / 1e6, np.abs(za), ls="--" if name == "2 x 1 nF" else "-", lw=0.8, label=name + " (at port)") if name in ("2 x 1 nF",) else None
    if name == "2 x 1 nF":
        ax[1].loglog(f / 1e6, mb, label="2 x 1 nF (2.5 mm away)")
    key = "Z_J10_complex_with_" + name.replace(" ", "").replace("(", "").replace(")", "").replace("+", "p")
    res5[key] = {"f_MHz": (f[::9] / 1e6).round(3).tolist(), "re": zb.real[::9].round(4).tolist(), "im": zb.imag[::9].round(4).tolist()}
    out[name]["zkey"] = key
for a in ax:
    a.axhline(0.5, color="k", ls=":", label="0.5 ohm target"); a.set_xlabel("MHz"); a.set_ylabel("|Z| ohm"); a.grid(True, which="both", alpha=.3); a.set_xlim(1, 1500)
    for x in (33.3, 66.6, 99.9, 166.5, 499.5):
        a.axvline(x, color="grey", lw=0.5)
ax[0].set_title("+5V island at the J10 via field: capacitor options (caps 2.5 mm from the vias)"); ax[0].legend(fontsize=7)
ax[1].set_title("2 x 1 nF: at the measured port vs 2.5 mm away (artefact check)"); ax[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "pdn_j10_cap_options.png"), dpi=150)
P = load_results()["pdn"]
P["5V"].update({k: v for k, v in res5.items() if k.startswith("Z_J10_complex_with_")})
P["5V"]["J10_cap_options"] = out
save_section("pdn", P)
for k, v in out.items():
    print(k, "| at port:", v["Z_J10_at_MHz(caps at measured port)"], "\n   2.5 mm:", v["Z_J10_at_MHz(caps 2.5 mm away)"], "max<=300", v["max_Z_J10_1-300MHz"], v["at_MHz"], v["peaks_J10"])
