"""C_rf step 7 - PDN impedance sweeps for +3V3 (In2 plane over In1), +5V (In2 island over In1) and +1V2 (trace ring).

Plane pairs: rectangular cavity model (Okoshi; Lei et al. IEEE T-ADVP 1999 - public, not a standard):
  Z_ij = j w mu d/(a b) sum_mn eps_m^2 eps_n^2 / (k_mn^2 - k^2) cos(kx xi) cos(ky yi) cos(kx xj) cos(ky yj) sinc(kx wx/2) sinc(ky wy/2)
  k^2 = w^2 mu eps0 er (1 - j(tan_d + delta_s/d)), d = 1.0 mm core (spec 12.1: In1-In2 = the 1.0 mm core), er 4.4, tan_d 0.02.
  3V3 plane: bounding rectangle of the real In2 fill scaled to its real area (c2: 6224 mm2); +5V island: 77 x 28 mm main part
  (x 90..167, y 90..118 abs) + the 15 x 21 mm lobe to PS1/C2 as a 1.8 nH series inductance (mu0 d * length/width).
Capacitors: values from the CURRENT schematic (sch_values.json, 2026-11-13), positions from the board; ESL by package
  (0402 0.35, 0603 0.45, 0805 0.6 nH), ESR (100 nF 30 mOhm, 1 uF 10 mOhm, 10/22 uF 5 mOhm, electrolytic C2 0.15 Ohm / 5 nH),
  DC-bias derating at the rail voltage (X7R 0402 -10 %, X5R 0805 10 uF @3.3 V -35 %, @5 V -50 %, 22 uF 16 V @3.3 V -40 %) -
  all typical MLCC vendor curves, ASSUMED. Mounting: via to In2 (1.2 mm) 0.45 nH + GND via (0.2 mm) 0.07 nH + pad/trace 0.25 nH.
VRM: TPS562201 output modelled as 5 mOhm + 40 nH (loop crossover ~50 kHz, ASSUMED); HLK-10M05 output 50 mOhm + 1 uH; LD1117
  output 50 mOhm + 0.5 uH (ASSUMED).
Target impedance Z_t = V * tol / dI: 3V3 3.3*5 %/0.5 A = 0.33 Ohm (ESP32 Wi-Fi TX burst); 5V 5*5 %/0.5 A = 0.5 Ohm;
  1V2 1.2*5 %/0.06 A = 1.0 Ohm (SSD1963 core current, spec 7). Required up to ~ the IC-package corner, here judged to 100 MHz;
  above that the package / on-die capacitance takes over and the board plane only matters for cavity resonances.
Outputs: results.json["pdn"], plots/pdn_*.png
"""
import json, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from c0_common import *

G = json.load(open(GEOM))
SCH = json.load(open(os.path.join(WORK, "sch_values.json")))
LAY = load_results()["layout"]
PADS = G["pads"]
f = np.geomspace(1e5, 1.5e9, 900)
w = 2 * np.pi * f


def parse_C(val):
    v = val.split()[0].replace("u", "e-6").replace("n", "e-9").replace("p", "e-12").replace("F", "")
    return float(v)


def cap_model(ref, rail_v):
    val, mpn, _ = SCH[ref]
    C = parse_C(val)
    fp = [x for x in G["footprints"] if x["ref"] == ref][0]["fpid"]
    pkg = "0402" if "0402" in fp else "0603" if "0603" in fp else "0805" if "0805" in fp else "THT"
    esl = {"0402": 0.35e-9, "0603": 0.45e-9, "0805": 0.6e-9, "THT": 5e-9}[pkg]
    if pkg == "THT":
        esr = 0.15
    else:
        esr = 0.03 if C < 0.5e-6 else 0.01 if C < 5e-6 else 0.005
    der = 1.0
    if "X5R" in val or "X7R" in val:
        if C >= 20e-6:
            der = 0.6
        elif C >= 5e-6:
            der = 0.65 if rail_v < 4 else 0.5
        elif C >= 0.5e-6:
            der = 0.8
        else:
            der = 0.9
    p = [q for q in PADS if q["ref"] == ref and q["net"] != "GND"][0]
    return {"ref": ref, "val": val, "C": C * der, "ESL": esl, "ESR": esr, "Lmount": 0.77e-9, "x": p["x"], "y": p["y"], "pkg": pkg}


def zcap(c, f):
    w = 2 * np.pi * f
    return c["ESR"] + 1j * w * (c["ESL"] + c["Lmount"]) + 1 / (1j * w * c["C"])


def cavity_Z(ports, a, b, x0, y0, f, d=1.0e-3, er=4.4, tand=0.02, M=40, N=40, wport=1.0e-3):
    """Z matrix (n_ports x n_ports x nf) of a rectangular plane pair; ports [(x_mm, y_mm)] in abs board coordinates."""
    xs = np.array([(p[0] - x0) * 1e-3 for p in ports]); ys = np.array([(p[1] - y0) * 1e-3 for p in ports])
    m = np.arange(M); n = np.arange(N)
    kx = m * np.pi / a; ky = n * np.pi / b
    em = np.where(m == 0, 1.0, 2.0); en = np.where(n == 0, 1.0, 2.0)
    cx = np.cos(kx[None, :] * xs[:, None]) * np.sinc(kx * wport / 2 / np.pi)[None, :]       # (P, M)
    cy = np.cos(ky[None, :] * ys[:, None]) * np.sinc(ky * wport / 2 / np.pi)[None, :]       # (P, N)
    kmn2 = kx[:, None] ** 2 + ky[None, :] ** 2
    out = np.zeros((len(ports), len(ports), len(f)), complex)
    for i, fi in enumerate(f):
        wi = 2 * np.pi * fi
        ds = math.sqrt(2 / (wi * MU0 * 5.8e7))
        k2 = wi ** 2 * MU0 * EPS0 * er * (1 - 1j * (tand + ds / d))
        T = (em[:, None] * en[None, :]) / (kmn2 - k2)                                         # (M, N)
        Zp = 1j * wi * MU0 * d / (a * b) * np.einsum("pm,qm,mn,pn,qn->pq", cx, cx, T, cy, cy, optimize=True)
        out[:, :, i] = Zp
    return out


def loaded_port(Zm, loads, ic=0):
    """input impedance at port `ic` with series-impedance loads (dict port -> Z(f) array) at other ports."""
    nf = Zm.shape[2]
    zin = np.zeros(nf, complex)
    lp = sorted(loads)
    for i in range(nf):
        Zcc = Zm[np.ix_(lp, lp, [i])][:, :, 0] + np.diag([loads[p][i] for p in lp])
        z0c = Zm[ic, lp, i]
        zc0 = Zm[lp, ic, i]
        zin[i] = Zm[ic, ic, i] - z0c @ np.linalg.solve(Zcc, zc0)
    return zin


res = {"model": __doc__.split("\n")[0]}
fig, axs = plt.subplots(1, 3, figsize=(16, 5))

# ------------------------------- +3V3 -----------------------------------------------------------------------------
bb = LAY["plane_areas"]["In2_3V3_bbox"]
A33 = LAY["plane_areas"]["In2_3V3_mm2"]
a33 = (bb[1] - bb[0]) * 1e-3
b33 = A33 / (bb[1] - bb[0]) * 1e-3          # equal-area rectangle along the long side
y0_33 = bb[2] + ((bb[3] - bb[2]) - b33 * 1e3) / 2
caps33 = [cap_model(c.split()[0], 3.3) for c in LAY["caps_by_net"]["+3V3"]]
ic_ports = {"U10 VDDIO (pin 84/95 side)": (85.66, 88.6), "U3 ESP32 3V3 (pin 2)": (29.26, 78.75), "U20 ADS1115 VDD": (51.7, 102.5)}
res3 = {"plane_rect_mm": [a33 * 1e3, b33 * 1e3], "C_plane_nF": EPS0 * 4.4 * A33 * 1e-6 / 1e-3 * 1e9, "caps": [(c["ref"], c["val"], round(c["C"] * 1e6, 4)) for c in caps33]}
vrm_port = (93.3, 116.95)
for icname, icp in ic_ports.items():
    ports = [icp] + [(c["x"], c["y"]) for c in caps33] + [vrm_port]
    ports_c = [(min(max(p[0], bb[0]), bb[1]), min(max(p[1], y0_33), y0_33 + b33 * 1e3)) for p in ports]
    Zm = cavity_Z(ports_c, a33, b33, bb[0], y0_33, f)
    loads = {k + 1: zcap(c, f) for k, c in enumerate(caps33)}
    loads[len(ports) - 1] = 0.005 + 1j * w * 40e-9
    zin = loaded_port(Zm, loads) + 1j * w * 0.5e-9                   # IC pin via + pad
    bare = Zm[0, 0, :]
    tgt = 0.33
    over = f[(np.abs(zin) > tgt) & (f < 100e6)]
    # anti-resonances: local maxima of |Z|
    mag = np.abs(zin)
    pk = [i for i in range(1, len(f) - 1) if mag[i] > mag[i - 1] and mag[i] > mag[i + 1] and mag[i] > 0.1]
    res3[icname] = {"Z_at_MHz": {str(fx): round(float(np.interp(fx * 1e6, f, mag)), 4) for fx in (0.58, 1, 10, 33.3, 100, 300, 500, 1000)},
                    "first_freq_above_target_MHz": round(float(over[0] / 1e6), 2) if len(over) else None,
                    "anti_resonances": [(round(float(f[i] / 1e6), 1), round(float(mag[i]), 3)) for i in pk][:8],
                    "bare_plane_first_resonance_MHz": round(float(f[np.argmax(np.abs(bare) * (f > 100e6))] / 1e6), 1)}
    axs[0].loglog(f / 1e6, mag, label=icname)
axs[0].axhline(0.33, color="k", ls="--", label="target 0.33 ohm (5 %, 0.5 A)")
axs[0].set_title("+3V3 PDN (In2 plane, 1.0 mm core over In1) at IC ports"); axs[0].set_xlabel("MHz"); axs[0].set_ylabel("|Z| ohm")
axs[0].grid(True, which="both", alpha=.3); axs[0].legend(fontsize=7)
res["3V3"] = res3

# ------------------------------- +5V island ------------------------------------------------------------------------
a5, b5, x05, y05 = 77e-3, 28e-3, 90.0, 90.0
caps5 = [cap_model(c.split()[0], 5.0) for c in LAY["caps_by_net"]["+5V"]]
ports5 = {"U30 VIN": (101.66, 110.45), "L12/C127 pi input": (92.4, 104.25), "J10 via field (RGB B.Cu return)": (150.0, 108.0), "lobe (C2/PS1) entry": (154.8, 90.0)}
plist = list(ports5.values()) + [(c["x"], min(max(c["y"], 90.0), 118.0)) for c in caps5 if c["ref"] != "C2"]
Zm5 = cavity_Z(plist, a5, b5, x05, y05, f)
c2 = cap_model("C2", 5.0)
lobe = 1j * w * 1.8e-9
zc2 = zcap(c2, f); zps = 0.05 + 1j * w * 1e-6
z_lobe = lobe + 1 / (1 / zc2 + 1 / zps)
loads5 = {3: z_lobe}
k0 = len(ports5)
for k, c in enumerate([c for c in caps5 if c["ref"] != "C2"]):
    loads5[k0 + k] = zcap(c, f)
res5 = {"rect_mm": [77, 28], "C_plane_nF": EPS0 * 4.4 * a5 * b5 / 1e-3 * 1e9, "caps": [(c["ref"], c["val"], round(c["C"] * 1e6, 4)) for c in caps5]}
for idx, nm in enumerate(ports5):
    if idx == 3:
        continue
    zin = loaded_port(Zm5, loads5, ic=idx)
    mag = np.abs(zin)
    pk = [i for i in range(1, len(f) - 1) if mag[i] > mag[i - 1] and mag[i] > mag[i + 1] and mag[i] > 0.1]
    over = f[(mag > 0.5) & (f < 100e6)]
    res5[nm] = {"Z_at_MHz": {str(fx): round(float(np.interp(fx * 1e6, f, mag)), 4) for fx in (0.58, 1.2, 10, 33.3, 100, 300, 500, 1000)},
                "first_freq_above_target_MHz": round(float(over[0] / 1e6), 2) if len(over) else None,
                "anti_resonances": [(round(float(f[i] / 1e6), 1), round(float(mag[i]), 3)) for i in pk][:8]}
    axs[1].loglog(f / 1e6, mag, label=nm)
    if nm.startswith("J10"):
        res5["Z_J10_complex"] = {"f_MHz": (f[::9] / 1e6).round(3).tolist(), "re": zin.real[::9].round(4).tolist(), "im": zin.imag[::9].round(4).tolist()}
# proposal: 2 x 1 nF C0G 0402 (+5V to GND) at the J10 re-sort via field (each 0.35 nH ESL + 0.77 nH mounting)
loads5p = dict(loads5)
cp = {"C": 1e-9, "ESL": 0.35e-9, "ESR": 0.05, "Lmount": 0.77e-9}
loads5p[2] = zcap(cp, f) / 2
zp = loaded_port(Zm5, loads5p, ic=2)
res5["Z_J10_complex_with_2x1nF"] = {"f_MHz": (f[::9] / 1e6).round(3).tolist(), "re": zp.real[::9].round(4).tolist(), "im": zp.imag[::9].round(4).tolist()}
res5["J10 with 2x1nF at the via field"] = {"Z_at_MHz": {str(fx): round(float(np.interp(fx * 1e6, f, np.abs(zp))), 4) for fx in (33.3, 100, 166.5, 300, 433, 500, 1000)}}
axs[1].loglog(f / 1e6, np.abs(zp), "k:", label="J10 via field + 2 x 1 nF (proposal)")
axs[1].axhline(0.5, color="k", ls="--", label="target 0.5 ohm")
axs[1].set_title("+5V island PDN (In2 over In1)"); axs[1].set_xlabel("MHz"); axs[1].grid(True, which="both", alpha=.3); axs[1].legend(fontsize=7)
res["5V"] = res5

# ------------------------------- +1V2 (trace net, lumped) ----------------------------------------------------------
caps12 = [cap_model(c.split()[0], 1.2) for c in LAY["caps_by_net"]["+1V2"]]
centre = (78.0, 90.0)          # U10 centre; 1V2 ring is local to U10
Y = np.zeros_like(f, complex)
rows = []
for c in caps12:
    dmm = math.hypot(c["x"] - centre[0], c["y"] - centre[1])
    Ltr = 0.36e-9 * dmm * 1.2 * 0.5      # 1V2 ring/trace: microstrip 0.36 nH/mm, half the distance (ring fed from both sides) - ASSUMED
    z = zcap(c, f) + 1j * w * Ltr
    Y += 1 / z
    rows.append((c["ref"], c["val"], round(dmm, 1), round(Ltr * 1e9, 2)))
zldo = 0.05 + 1j * w * 0.5e-6
Y += 1 / zldo
z12 = 1 / Y + 1j * w * 0.3e-9
mag = np.abs(z12)
pk = [i for i in range(1, len(f) - 1) if mag[i] > mag[i - 1] and mag[i] > mag[i + 1] and mag[i] > 0.1]
over = f[(mag > 1.0) & (f < 100e6)]
res["1V2"] = {"caps_ref_val_dist_mm_Ltrace_nH": rows,
              "Z_at_MHz": {str(fx): round(float(np.interp(fx * 1e6, f, mag)), 4) for fx in (0.1, 1, 10, 33.3, 100, 300, 1000)},
              "first_freq_above_target_MHz": round(float(over[0] / 1e6), 2) if len(over) else None,
              "anti_resonances": [(round(float(f[i] / 1e6), 1), round(float(mag[i]), 3)) for i in pk][:8]}
axs[2].loglog(f / 1e6, mag, label="U10 1V2 core node")
axs[2].axhline(1.0, color="k", ls="--", label="target 1.0 ohm")
axs[2].set_title("+1V2 (F.Cu ring + LD1117)"); axs[2].set_xlabel("MHz"); axs[2].grid(True, which="both", alpha=.3); axs[2].legend(fontsize=7)
for ax in axs:
    ax.set_xlim(0.1, 1500)
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "pdn_impedance.png"), dpi=150)
res["U6_74AHC1G14_note"] = "U6 (ZCD Schmitt trigger) has no local decoupling capacitor: nearest +3V3 capacitor C114 is 55.7 mm away (c2); only the In2 plane serves it"
save_section("pdn", res)
print(json.dumps(rnd(res, 3), indent=1, default=str)[:5000])
