"""C_rf step 10 (cross-scope, for scope B's Y1 proposal and scope A's threshold column) - SELV-ground noise voltage below
30 MHz versus the open-circuit SELV-GND-to-reference-plane voltage that just reaches the EN 55014-1 Table 5 AV mains limit
through Y1 1 nF (scope A's column; QP thresholds 10 dB higher above 0.5 MHz; without Y1 the thresholds are 25-35 dB higher).

Open-circuit SELV noise sources (Thevenin voltage of the SELV ground against the reference plane):
  voltage-driven switch nodes - V_oc = V_sw(f) * k, k = coupling of the switch-node conductor to the outside relative to the
    SELV structure's: BOUND k = A_sw / A_board (all copper and the inductor face at SW potential, area ratio, no shielding by
    In1); REALISTIC k = A_inductor_face_at_SW / A_board (flush copper 0.2 mm over In1 keeps its field in the dielectric;
    semi-shielded L30 face -6 dB). Spectra: trapezoids, buck 5 V / 580 kHz / D 0.66 / 5 ns, boost 10 V / 1.2 MHz / D 0.5 /
    5 ns (datasheet frequencies TPS562201 p.1, MIC2288; swings and edges ASSUMED). Areas from c2 (copper) + footprints.
  crystal 10 MHz (1.5 V swing, 5 ns), same coupling rule with the XTAL copper (no elevated body -> realistic -30 dB).
  current-driven plane voltage of the 8080 bus (15 MHz WR) and the board RGB ribbon: V = w L'_ret I (c3: 1.37 pH/mm per A).
  FPC panel-PCB source (c6 V_src) at the data fundamental 16.65 MHz (worst pattern) and the typical broadband content:
    SELV open-circuit share 0.5 x V_src (panel and PCB each ~half of the structure's capacitance to the plane - ASSUMED).
  backlight PWM 26 kHz LED-current edges: current-driven over the +5V island, negligible (< 20 dBuV) - shown for completeness.
Uncertainty +-10 dB on the coupling factors. Outputs: results.json["cross_scope_conducted_Y1"], plots/y1_conducted.png
"""
import json, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from c0_common import *

R = load_results()
LAY = R["layout"]; SC = R["spice_chain"]; I2D = R["inductance2d"]
FA = np.array([0.15, 0.3, 0.58, 1.2, 2.4, 3.6, 5, 10, 20, 30]) * 1e6
THR = np.array([90.0, 73.3, 60.6, 54.0, 49.2, 47.3, 46.7, 57.2, 64.9, 69.3])     # scope A, dBuV open-circuit, AV, with Y1 1 nF


def thr(f):
    return np.interp(np.log10(f), np.log10(FA), THR)


def trap_lines(A, f0, d, tr, fmax=30e6):
    n = np.arange(1, int(fmax / f0) + 1)
    f = n * f0
    return f, 2 * A * d * np.abs(np.sinc(n * d)) * np.abs(np.sinc(f * tr))


Aboard = LAY["plane_areas"]["board_mm2"]
cu = LAY["noisy_copper_area"]
src = {}
A_buck_bound = cu["/Power/BUCK_SW"]["total_mm2"] + 18.0          # + half of the 6 x 6 mm L30 face at SW potential
A_buck_real = 9.0                                                 # semi-shielded L30: half face, -6 dB
A_boost_bound = cu["/Display/BL_SW"]["total_mm2"] + 8.0           # + half of the 4 x 4 mm L11 face
A_boost_real = 8.0
A_x_bound = cu["/Display/XTAL_IN"]["total_mm2"] + cu["/Display/XTAL_OUT"]["total_mm2"]
for name, (A, f0, d, tr, kb, kr) in {"buck SW 580 kHz": (5.0, 580e3, 0.66, 5e-9, A_buck_bound / Aboard, A_buck_real / Aboard),
                                      "boost SW 1.2 MHz": (10.0, 1.2e6, 0.5, 5e-9, A_boost_bound / Aboard, A_boost_real / Aboard),
                                      "crystal 10 MHz": (1.5, 10e6, 0.5, 5e-9, A_x_bound / Aboard, A_x_bound / Aboard * 10 ** (-30 / 20))}.items():
    f, a = trap_lines(A, f0, d, tr)
    src[name] = {"f": f, "bound": a * kb, "real": a * kr, "k_bound": kb, "k_real": kr}
# 8080 bus current-driven
Lp = I2D["board_ribbon"]["L_ret_pH_per_mm_per_A_total"] * 1e-9          # H/m per A
d = SC["bus_8080_WR"]; f = np.array(d["f_MHz"]) * 1e6; m = np.array(d["moment_Am"])[:, 0]
d2 = SC["bus_8080_data8_in_phase"]; f2 = np.array(d2["f_MHz"]) * 1e6; m2 = np.array(d2["moment_Am"])[:, 0]
sel = f <= 30e6; sel2 = f2 <= 30e6
v_wr = 2 * np.pi * f[sel] * Lp * m[sel]; v_bus = 2 * np.pi * f2[sel2] * Lp * m2[sel2]
src["8080 bus plane voltage (WR + 8 data)"] = {"f": np.concatenate([f[sel], f2[sel2]]), "bound": np.concatenate([v_wr, v_bus]), "real": np.concatenate([v_wr, v_bus]) * 0.5}
# FPC source at 16.65 MHz (worst pattern) and typical content in 15-30 MHz
Lret_data = I2D["fpc_tft"]["all 24 data in phase, returns GND 3/29/36 + VDD 4"]["L_ret_nH_per_mm_per_A_total"] * 1e-6
w = SC["rgb_worst_in_phase"]["nominal Rout30 tr1.5 Cin5"]; fw = np.array(w["f_MHz"]) * 1e6; mw = np.array(w["fpc_moment_Am"])[:, 0]
selw = (fw <= 30e6) & (mw > 1e-12)
vfpc = 2 * np.pi * fw[selw] * Lret_data * mw[selw] * 0.5
src["FPC panel-PCB source, worst pattern (16.65 MHz)"] = {"f": fw[selw], "bound": vfpc, "real": vfpc}
p = SC["pclk"]; fp = np.array(p["f_MHz"]) * 1e6; mp = np.array(p["fpc_moment_Am"])[:, 0]
Lret_p = I2D["fpc_tft"]["PCLK (pin 30) alone, returns GND + VDD"]["L_ret_nH_per_mm_per_A_total"] * 1e-6
src["FPC PCLK (33.3 MHz, above the band)"] = {"f": fp[fp <= 30e6], "bound": np.zeros(0), "real": np.zeros(0)}
# backlight PWM: 0.138 A LED current steps at 26 kHz, ~10 us edges; L_ret of the VLED pair ~0.1 nH (pair over the island)
fb, ab = trap_lines(0.138, 26e3, 0.5, 10e-6, fmax=30e6)
selb = fb >= 150e3
src["backlight PWM 26 kHz (current-driven)"] = {"f": fb[selb], "bound": 2 * np.pi * fb[selb] * 0.1e-9 * ab[selb], "real": 2 * np.pi * fb[selb] * 0.1e-9 * ab[selb]}

out = {"model": __doc__.split("\n")[0], "scope_A_threshold_dBuV": dict(zip([f"{x/1e6:g}" for x in FA], THR.tolist())), "sources": {}}
fig, ax = plt.subplots(figsize=(11, 6))
ax.semilogx(FA / 1e6, THR, "k-o", lw=2, label="scope A: open-circuit SELV noise reaching the AV limit through Y1 1 nF")
ax.semilogx(FA / 1e6, THR + 30, "k--", label="same without Y1 (thresholds ~ +25..35 dB, +30 drawn)")
cols = iter(["r", "orange", "g", "b", "m", "c", "y"])
for name, s in src.items():
    if len(s["bound"]) == 0:
        out["sources"][name] = "no line below 30 MHz"
        continue
    fsel = (s["f"] >= 150e3) & (s["f"] <= 30e6)
    ff, b, r_ = s["f"][fsel], dB(s["bound"][fsel]) + 120, dB(s["real"][fsel]) + 120
    mb, mr = thr(ff) - b, thr(ff) - r_
    i, j = int(np.argmin(mb)), int(np.argmin(mr))
    per_point = {}
    for fa in FA:
        k = int(np.argmin(np.abs(np.log(ff / fa))))
        if abs(math.log(ff[k] / fa)) < 0.15:
            per_point[f"{fa/1e6:g} MHz"] = {"line_MHz": round(ff[k] / 1e6, 3), "realistic_dBuV": round(float(r_[k]), 1), "bound_dBuV": round(float(b[k]), 1),
                                           "margin_realistic_dB": round(float(mr[k]), 1), "margin_bound_dB": round(float(mb[k]), 1)}
    out["sources"][name] = {"worst_margin_realistic_dB": round(float(mr[j]), 1), "at_MHz": round(float(ff[j] / 1e6), 3),
                            "worst_margin_bound_dB": round(float(mb[i]), 1), "bound_at_MHz": round(float(ff[i] / 1e6), 3),
                            "margin_without_Y1_realistic_dB(+25..35)": [round(float(mr[j]) + 25, 1), round(float(mr[j]) + 35, 1)],
                            "at_scope_A_points": per_point, **({"k_bound": s["k_bound"], "k_real": s["k_real"]} if "k_bound" in s else {})}
    c = next(cols)
    ax.semilogx(ff / 1e6, r_, ".", color=c, label=name + " (realistic)")
    ax.semilogx(ff / 1e6, b, "_", color=c, ms=8, alpha=.6)
ax.set_xlabel("MHz"); ax.set_ylabel("dBuV (open-circuit SELV GND to reference plane)"); ax.set_xlim(0.15, 30); ax.grid(True, which="both", alpha=.3)
ax.set_title("Conducted path through Y1 (cross-scope): SELV ground-noise estimates vs scope A thresholds\n(dots realistic, dashes upper bound; harmonic lines)")
ax.legend(fontsize=7); fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "y1_conducted.png"), dpi=150)
save_section("cross_scope_conducted_Y1", rnd(out, 3))
print(json.dumps({k: (v if isinstance(v, str) else {kk: v[kk] for kk in ("worst_margin_realistic_dB", "at_MHz", "worst_margin_bound_dB", "bound_at_MHz")}) for k, v in out["sources"].items()}, indent=1))
