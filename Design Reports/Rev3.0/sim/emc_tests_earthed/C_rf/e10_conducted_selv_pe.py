"""Earthed-oven study - conducted consequence (150 kHz - 30 MHz) of tying SELV ground to PE (bonding concepts iii/iv), replacing
the void Y1 check. Small MNA circuit (numpy), common mode only.

Set-up (conducted, EN 55014-1 4.3.3 / Table 5 PDF p.36; AMN details NOT read from CISPR 16-1-2 - public description):
  AMN: L and N each 50 ohm || 50 uH to the reference ground (RGP); for the CM sum both lines in parallel -> 25 ohm || 25 uH;
  PE of the AMN bonded to the RGP. Cord 1 m: L/N CM 0.4 uH, PE 0.8 uH (ASSUMED).
Nodes: 0 = RGP, M = L/N (CM, tied by the X capacitors), OV = earthed oven body, SG = SELV ground (PCB), PAN = panel metal,
SW = a noise source node.
  M-SG: HLK barrier 50 pF (unknown, ASSUMED; no Y1 any more) ; M-OV: heater element / internal wiring 150 pF ; M-0: 5 pF
  OV-0: PE (0.8 uH) for the earthed oven, or 50 pF (floating oven, the old class-II assumption)
  SG-OV: PCB/panel to the steel front sheet 30 pF (frame gap) + thermocouple path (grounded junction: 1 uH lead + the front-end
         CM input impedance 2 x [TVS 35 pF || (1 k + 10 nF)]; insulated: + 20 pF in series)
  SG-PAN: FPC ground return 40 nH ; PAN-OV 15 pF (panel bezel to the sheet) ; SG-0 10 pF, PAN-0 5 pF (through the opening)
  bonding: iv-1 SG-OV 15 nH ; iv-4 6 nH ; iv-9 3 nH (strap + contact, ASSUMED) ; ii PAN-OV 10 nH ; iii = iv + ii.
Noise sources (voltage-driven, Thevenin): switch nodes and crystal couple to M and to OV through small capacitances
  (realistic / bound): buck SW (5 V, 580 kHz, D 0.66, 5 ns) and boost SW (10 V, 1.2 MHz, D 0.5, 5 ns): C_SW-M 0.005 / 0.03 pF,
  C_SW-OV 0.004 / 0.02 pF (inductor bodies 20-40 mm from the mains wiring and the body, ASSUMED); crystal 10 MHz 1.5 V
  0.0005 / 0.003 pF. FPC source between PAN and SG at the 16.65 MHz data fundamental (worst pattern, RN 150) from the SPICE chain.
Result: CM current into the AMN -> line voltage (dBuV) vs Table 5 AV limit (QP limit 10 dB higher above 0.5 MHz).
Outputs: results.json["conducted_selv_pe"], plots/conducted_selv_pe.png"""
import json, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from e0_common import *

NODES = ["M", "OV", "SG", "PAN", "SW"]
IDX = {n: i for i, n in enumerate(NODES)}


def zC(C):
    return lambda w: 1 / (1j * w * C)


def zL(L, R=0.0):
    return lambda w: 1j * w * L + R


def zin_tc(w):
    leg = 1 / (1j * w * 35e-12 + 1 / (1000 + 1 / (1j * w * 10e-9)))
    return leg / 2


def solve(f, branches, src_nodes, Vsrc):
    """branches: list (n1, n2, zfun); a voltage source Vsrc between src_nodes (plus, minus). Returns node voltages."""
    w = 2 * math.pi * f
    N = len(NODES)
    Y = np.zeros((N + 1, N + 1), complex)
    for a, b, z in branches:
        y = 1 / z(w)
        ia = IDX.get(a); ib = IDX.get(b)
        if ia is not None: Y[ia, ia] += y
        if ib is not None: Y[ib, ib] += y
        if ia is not None and ib is not None:
            Y[ia, ib] -= y; Y[ib, ia] -= y
    p, m = src_nodes
    Y[IDX[p], N] += 1; Y[N, IDX[p]] += 1
    if m != "0":
        Y[IDX[m], N] -= 1; Y[N, IDX[m]] -= 1
    rhs = np.zeros(N + 1, complex); rhs[N] = Vsrc
    return np.linalg.solve(Y, rhs)


def amn_z(w):
    return 1 / (1 / 25.0 + 1 / (1j * w * 25e-6))


def network(case, probe="grounded", cswm=0.005e-12, cswo=0.004e-12, src="SW"):
    br = [("M", "0", lambda w: amn_z(w) + 1j * w * 0.4e-6), ("M", "0", zC(5e-12)), ("M", "SG", zC(50e-12)), ("M", "OV", zC(150e-12)),
          ("SG", "PAN", zL(40e-9, 0.1)), ("PAN", "OV", zC(15e-12)), ("SG", "0", zC(10e-12)), ("PAN", "0", zC(5e-12)),
          ("SG", "OV", zC(30e-12)), ("SW", "M", zC(cswm)), ("SW", "OV", zC(cswo))]
    if case == "floating (old class II assumption)":
        br.append(("OV", "0", zC(50e-12)))
    else:
        br.append(("OV", "0", zL(0.8e-6, 0.05)))
    tc = (lambda w: 1j * w * 1e-6 + zin_tc(w)) if probe == "grounded" else (lambda w: 1j * w * 1e-6 + zin_tc(w) + 1 / (1j * w * 20e-12))
    br.append(("SG", "OV", tc))
    bonds = {"iv-1 (SELV-PE 1 point)": [("SG", "OV", zL(15e-9, 0.01))], "iv-4": [("SG", "OV", zL(6e-9, 0.005))], "iv-9": [("SG", "OV", zL(3e-9, 0.003))],
             "ii (panel-sheet)": [("PAN", "OV", zL(10e-9, 0.01))], "iii-9 (iv-9 + ii)": [("SG", "OV", zL(3e-9, 0.003)), ("PAN", "OV", zL(10e-9, 0.01))]}
    br += bonds.get(case, [])
    return br


def trap_lines(A, f0, d, tr, fmax=30e6):
    n = np.arange(1, int(fmax / f0) + 1)
    f = n * f0
    return f, 2 * A * d * np.abs(np.sinc(n * d)) * np.abs(np.sinc(f * tr))


def lim_av(f):
    f = np.asarray(f, float)
    return np.where(f < 0.5e6, 56 - 10 * np.log10(f / 0.15e6) / np.log10(0.5 / 0.15), np.where(f <= 5e6, 46.0, 50.0))


O = old()
SCd = O["spice_chain"]
d = SCd["rgb_worst_in_phase"]["Rs150 Rout30 tr1.5 Cin5"]
mf = np.array(d["fpc_moment_Am"]); f_d = np.array(d["f_MHz"]) * 1e6
Lret = O["inductance2d"]["fpc_tft"]["all 24 data in phase, returns GND 3/29/36 + VDD 4"]["L_ret_nH_per_mm_per_A_total"] * 1e-6
Vfpc = 2 * np.pi * f_d[0] * Lret * mf[0, 0]          # 16.65 MHz fundamental, peak
SOURCES = {"buck SW 580 kHz": trap_lines(5.0, 580e3, 0.66, 5e-9), "boost SW 1.2 MHz": trap_lines(10.0, 1.2e6, 0.5, 5e-9),
           "crystal 10 MHz": trap_lines(1.5, 10e6, 0.5, 5e-9)}
CASES = ["floating (old class II assumption)", "earthed, no bond", "ii (panel-sheet)", "iv-1 (SELV-PE 1 point)", "iv-4", "iv-9", "iii-9 (iv-9 + ii)"]
res = {"model": __doc__.split("\n")[0], "limit": "EN 55014-1 Table 5 col. 3 (AV), PDF p.36", "cases": {}}
fig, ax = plt.subplots(figsize=(11, 6))
ff = np.geomspace(0.15e6, 30e6, 300)
ax.semilogx(ff / 1e6, lim_av(ff), "k-", lw=2, label="Table 5 AV limit (mains port)")
for case in CASES:
    for probe in ("grounded", "insulated"):
        row = {}
        for sname, (fs, amp) in SOURCES.items():
            k = 0.1 if sname.startswith("crystal") else 1.0
            for bound, (cm, co) in (("realistic", (0.005e-12 * k, 0.004e-12 * k)), ("bound", (0.03e-12 * k, 0.02e-12 * k))):
                Vl = []
                for fx, a in zip(fs, amp):
                    v = solve(fx, network(case, probe, cm, co), ("SW", "SG"), a / math.sqrt(2))      # rms
                    Vm = v[IDX["M"]]
                    Icm = Vm / (amn_z(2 * math.pi * fx) + 1j * 2 * math.pi * fx * 0.4e-6)
                    Vl.append(abs(Icm * amn_z(2 * math.pi * fx)))
                Vl = np.array(Vl); sel = fs >= 0.15e6
                mar = lim_av(fs[sel]) - (dB(Vl[sel]) + 120)
                i = int(np.argmin(mar))
                row[f"{sname} ({bound})"] = {"worst_margin_dB": round(float(mar[i]), 1), "at_MHz": round(float(fs[sel][i] / 1e6), 3),
                                             "level_dBuV": round(float(dB(Vl[sel][i]) + 120), 1)}
                if probe == "grounded" and bound == "realistic" and sname.startswith("boost") and case in ("earthed, no bond", "iv-9", "floating (old class II assumption)"):
                    ax.semilogx(fs[sel] / 1e6, dB(Vl[sel]) + 120, ".", label=f"boost, {case}")
        # FPC panel source at 16.65 MHz
        v = solve(f_d[0], network(case, probe), ("PAN", "SG"), Vfpc / math.sqrt(2))
        Icm = v[IDX["M"]] / (amn_z(2 * math.pi * f_d[0]) + 1j * 2 * math.pi * f_d[0] * 0.4e-6)
        lev = float(dB(abs(Icm * amn_z(2 * math.pi * f_d[0]))) + 120)
        row["FPC panel source, worst pattern 16.65 MHz"] = {"level_dBuV": round(lev, 1), "worst_margin_dB": round(float(lim_av(f_d[0]) - lev), 1)}
        res["cases"][f"{case} | probe {probe}"] = row
ax.set_xlabel("MHz"); ax.set_ylabel("dBuV at the AMN (per line, AV)"); ax.grid(True, which="both", alpha=.3); ax.legend(fontsize=7)
ax.set_title("SELV noise to the mains port: earthed oven, with and without a deliberate SELV-PE bond (realistic coupling)")
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "conducted_selv_pe.png"), dpi=150)
# mapping onto scope A's Y1 threshold column: a direct SELV-PE bond replaces Y1 (1 nF) by the PE path (bond + 0.8 uH cord PE)
FA = np.array([0.15, 0.3, 0.58, 1.2, 2.4, 3.6, 5, 10, 20, 30]) * 1e6
THR = np.array([90.0, 73.3, 60.6, 54.0, 49.2, 47.3, 46.7, 57.2, 64.9, 69.3])
w = 2 * np.pi * FA
zy1 = 1 / (1j * w * 1e-9) + 1j * w * 8e-9 + 25.0
zpe = 1j * w * (0.8e-6 + 3e-9) + 25.0
res["scope_A_threshold_mapping_dBuV"] = {"note": "open-circuit SELV-to-reference noise that reaches the AV limit: Y1 column (scope A) shifted by 20 log |Z_Y1 path| / |Z_PE path| (cord PE 0.8 uH + bond 3 nH, AMN 25 ohm) - same source-impedance assumption as scope A's column",
                                         "f_MHz": (FA / 1e6).tolist(), "Y1_1nF": THR.tolist(), "SELV_PE_bond": (THR - 20 * np.log10(np.abs(zy1) / np.abs(zpe))).round(1).tolist()}
save_section("conducted_selv_pe", res)
for k, v in res["cases"].items():
    print(k, {kk: vv["worst_margin_dB"] for kk, vv in v.items()})
print(res["scope_A_threshold_mapping_dBuV"]["SELV_PE_bond"])
