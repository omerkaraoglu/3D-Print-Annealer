"""C_rf step 6 (v2, after review) - radiated emission 30-1000 MHz with a SELF-CONSISTENT, LOSSY common-mode excitation.

Why v2: v1 impressed V_src = j w L'_ret * (FPC current moment) as an ideal voltage source on a lossless MoM structure.
At the panel/PCB resonance that drew more power than the SSD1963 drivers can deliver (reviewer's energy check).
v2 couples the two circuits both ways (reciprocal mutual M = L'_ret * l_FPC between every RGB/PCLK DM loop and the CM loop):
    DM, each line k:  V_oc,k = Z_k I_k + j w M_k I_cm        (Z_k = driver + RN + line + FPC + panel input, from SPICE: Z_k = V_oc/I_k)
    CM loop:          0     = j w sum M_k I_k + (Z_s + R_loss) I_cm   (Z_s = MoM gap impedance of the structure, complex)
 -> I_cm = j w M I_0 / (Z_s + R_loss + w^2 sum M_k^2 Y_k)   with I_0 the unperturbed (SPICE) FPC current and Y_k = I_k/V_oc,k.
Y is the FPC-averaged DM current per volt of EMF distributed along the FPC (c4c_ydist.py, passive, Re >= 0).
The reflected term w^2 M^2 Y loads the CM resonance with the driver/RN/line resistance; R_loss adds conductor/panel loss.
Loss band: the structure's own (radiation + CMAD + HLK resistor) Q is read from a dense MoM sweep of the 170-180 MHz mode;
R_loss is set so the unloaded Q is 30 / 10 / 3 (nominal = 10). Physical estimates for the reviewer: FPC return conductors
(4 strips 0.25 mm x 18 um, 88 mm, skin effect) ~0.12 ohm, steel panel frame surface resistance ~0.1 ohm/sq at 175 MHz,
LCD/backlight internal structures unknown -> the band brackets them.
Power balance printed per harmonic: P_in(structure) = 0.5 |I_cm|^2 Re(Z_s) <= P_avail = N |V_oc|^2 / (8 (R_out + R_s)).
The ceiling line on the plot is the field all of P_avail would give from a 2.15 dBi radiator: E = sqrt(30 * 1.64 * P) / r.
Other mechanisms unchanged from v1: DM board loops (m = moment x h_eff), DM FPC (folded, factor 0.24), +5V island cavity
(upper estimate), 8080 / converters / crystal DM.
Limits: EN 55014-1:2017+A11:2020 Table 9 PDF p.38 (FAR 3 m 42->35 / 42; SAC 10 m 30 / 37 dBuV/m), Annex ZZ (no 80/80).
Outputs: results.json["emission"], plots/emission_far3m.png, emission_structure_transfer.png, emission_power_balance.png
"""
import json, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from c0_common import *

R = load_results()
SC = R["spice_chain"]; CM = R["cm_structure"]; I2D = R["inductance2d"]; LAY = R["layout"]; PDN = R["pdn"]
fq = np.array(CM["freqs_MHz"]) * 1e6
PCLK = 33.30e6
r3 = 3.0
ELL = (67.65 + 20.0) * 1e-3           # FPC tail (spec 12.9) + panel-internal routing (assumed), as in c4
FOLD = 0.24
QBAND = (30.0, 10.0, 3.0)
QNOM = 10.0


def cplx(lst):
    a = np.array(lst, dtype=float)
    return a[:, 0] * np.exp(1j * a[:, 1])


def loopE(m, f, r=r3):
    k = 2 * np.pi * f / C0
    return ETA0 * k ** 2 * np.abs(m) / (4 * np.pi * r) * np.sqrt(1 + 1 / (k * r) ** 2)


def dBuV(x):
    return dB(x) + 120


def cinterp(f, fx, z):
    """complex interpolation (real/imag) ignoring NaN; NaN outside the solved range"""
    ok = ~np.isnan(z)
    fx, z = fx[ok], z[ok]
    out = np.interp(f, fx, z.real) + 1j * np.interp(f, fx, z.imag)
    return np.where((np.asarray(f) >= fx.min() * 0.999) & (np.asarray(f) <= fx.max() * 1.001), out, np.nan)


def arr(lst):
    return np.array([np.nan if x is None else x for x in lst], float)


Lret_data = I2D["fpc_tft"]["all 24 data in phase, returns GND 3/29/36 + VDD 4"]["L_ret_nH_per_mm_per_A_total"] * 1e-6
Lret_pclk = I2D["fpc_tft"]["PCLK (pin 30) alone, returns GND + VDD"]["L_ret_nH_per_mm_per_A_total"] * 1e-6
Lret_single = np.mean([I2D["fpc_tft"][k]["L_ret_nH_per_mm_per_A_total"] for k in ("G3 (pin 16) alone, returns GND + VDD", "B7 (pin 28) alone, returns GND + VDD")]) * 1e-6
M_d, M_p, M_s = Lret_data * ELL, Lret_pclk * ELL, Lret_single * ELL
d_data = I2D["fpc_tft"]["all 24 data in phase, returns GND 3/29/36 + VDD 4"]["moment_mm_per_A_total"] * 1e-3
d_pclk = I2D["fpc_tft"]["PCLK (pin 30) alone, returns GND + VDD"]["moment_mm_per_A_total"] * 1e-3
h_eff = I2D["board_ribbon"]["h_eff_mm_all"] * 1e-3
CFGS = [k for k in CM if k not in ("freqs_MHz", "configs", "assumptions") and not k.endswith("_dense")]
ENV_CFGS = [c for c in CFGS if c in ("nominal", "tc_0.5m", "tc_1.5m", "tc_2.0m", "heater_0.3m", "heater_1.0m", "Ciso_20pF", "Ciso_100pF", "mains_no_cmad_1.5m")]


# ---------------- structure ---------------------------------------------------------------------------------------
def Zs(cfg, f):
    ig = arr(CM[cfg]["Igap_re"]) + 1j * arr(CM[cfg]["Igap_im"])
    return 1 / cinterp(f, fq, ig)


def Epa(cfg, f, which="E3"):
    """field (V/m) per ampere of CM current at the FPC gap = (E per volt) * |Z_s|"""
    e = 10 ** ((arr(CM[cfg][which + "_dBuV_per_V"]) - 120) / 20)
    ok = ~np.isnan(e)
    epv = np.interp(f, fq[ok], e[ok])
    return epv * np.abs(Zs(cfg, f))


def Cpa(cfg, cable, f):
    c = arr(CM[cfg]["cable_max_mA_per_V"][cable]) * 1e-3
    ok = ~np.isnan(c)
    return np.interp(f, fq[ok], c[ok]) * np.abs(Zs(cfg, f))


# ---------------- loss band from the dense sweep of the panel/PCB mode --------------------------------------------
D = CM["nominal_dense"]
fdn = np.array(D["f_MHz"]) * 1e6
Zd = 1 / (np.array(D["Igap_re"]) + 1j * np.array(D["Igap_im"]))
i0 = int(np.argmax(np.abs(1 / Zd)))
w0 = 2 * np.pi * fdn[i0]
dXdw = np.gradient(Zd.imag, 2 * np.pi * fdn)[i0]
Rrad = float(Zd.real[i0])
Q_struct = float(w0 * dXdw / (2 * Rrad))
Rloss = {Q: max(0.0, w0 * dXdw / (2 * Q) - Rrad) for Q in QBAND}
Rloss[float("inf")] = 0.0
modeinfo = {"f0_MHz": round(fdn[i0] / 1e6, 1), "R_struct_ohm": round(Rrad, 3), "dX_dw_nH": round(dXdw * 1e9, 2),
            "Q_struct_unloaded(radiation+CMAD+HLK R)": round(Q_struct, 1), "R_loss_added_ohm": {str(k): round(v, 3) for k, v in Rloss.items()},
            "physical_loss_estimates_ohm": {"FPC return strips (4 x 0.25 mm x 18 um x 88 mm, skin)": 0.12,
                                            "steel panel frame, Rs ~0.1 ohm/sq over ~1-2 squares": "0.1-0.2", "LCD/backlight internals": "unknown"}}

# ---------------- driver-side admittances (from SPICE, same time origin as V_oc) ------------------------------------
def Y_of(d, n_lines=1):
    f = np.array(d["f_MHz"]) * 1e6
    I0 = cplx(d["fpc_moment_Am"]) / ELL
    V = cplx(d["V_oc_V"])
    ok = np.abs(V) > 1e-4
    return f[ok], (I0[ok] / V[ok]), f, I0, V


def Yfun(d):
    fy, y, *_ = Y_of(d)
    return lambda f: cinterp(f, fy, y)


YDIST = SC["Ydist"]


def _yd(key, mult=1.0):
    d = YDIST[key]
    fy = np.array(d["f_MHz"]) * 1e6
    y = (np.maximum(np.array(d["re"]), 0.0) + 1j * np.array(d["im"])) * mult     # passive: Re >= 0 (tiny negative = quadrature noise)
    return lambda f: np.interp(f, fy, y.real) + 1j * np.interp(f, fy, y.imag)


YD = {33: _yd("data_in_phase_Rs33", 24), 150: _yd("data_in_phase_Rs150", 24)}
YP = {33: _yd("pclk_Rs33"), 150: _yd("pclk_Rs150")}


def Zrefl(f, rs=33):
    """reflected impedance of the 24 data loops (in-phase mode) and the PCLK loop: w^2 (M_d^2 Y_d + M_p^2 Y_p), Y = Y_dist (c4c)"""
    w = 2 * np.pi * f
    return w ** 2 * (M_d ** 2 * YD[rs](f) + M_p ** 2 * YP[rs](f))


def cm_solve(cfg, f, I0, M, Q, rs=33, self_consistent=True):
    w = 2 * np.pi * f
    Z = Zs(cfg, f)
    Zt = Z + Rloss[Q] + (Zrefl(f, rs) if self_consistent else 0)
    Icm = 1j * w * M * I0 / Zt
    return Icm, 0.5 * np.abs(Icm) ** 2 * Z.real


def mech(kind, cfg="nominal", Q=QNOM, key=None, zkey="Z_J10_complex", rs=33.0, self_consistent=True, which="E3"):
    if kind == "worst":
        lab = key or "nominal Rout30 tr1.5 Cin5"
        d = SC["rgb_worst_in_phase"][lab]
        f = np.array(d["f_MHz"]) * 1e6
        mf = cplx(d["fpc_moment_Am"]); m1 = cplx(d["board_seg1_moment_Am"]); m2 = cplx(d["board_seg2_moment_Am"])
        V = cplx(d["V_oc_V"]); N = 24
        Icm, Pin = cm_solve(cfg, f, mf / ELL, M_d, Q, rs, self_consistent)
        out = {"f": f, "DM-board": loopE((m1 + m2) * h_eff, f), "DM-FPC": loopE(mf * d_data * FOLD, f)}
    elif kind == "pclk":
        key = key or "pclk"
        d = SC[key]
        f = np.array(d["f_MHz"]) * 1e6
        mf = cplx(d["fpc_moment_Am"]); m1 = cplx(d["board_seg1_moment_Am"]); m2 = cplx(d["board_seg2_moment_Am"])
        V = cplx(d["V_oc_V"]); N = 1
        Icm, Pin = cm_solve(cfg, f, mf / ELL, M_p, Q, rs, self_consistent)
        out = {"f": f, "DM-board": loopE((m1 + m2) * h_eff, f), "DM-FPC": loopE(mf * d_pclk * FOLD, f)}
        z = PDN["5V"][zkey]
        Zj = np.interp(f, np.array(z["f_MHz"]) * 1e6, np.abs(np.array(z["re"]) + 1j * np.array(z["im"])))
        Iret = np.abs(m2) / (LAY["nets"]["RGB:PCLK"]["len_mm"] * 1e-3 * 0.35)
        out["CAV-5V"] = (2 * np.pi * f / C0) * Zj * Iret * 0.028 / (2 * np.pi * r3)
    else:     # typical UI content: 24 independent random NRZ lines (toggle probability 0.1 per pixel), 120 kHz RBW
        d = SC["rgb_single_line_isolated"]
        f = np.array(d["f_MHz"]) * 1e6
        mf = np.abs(cplx(d["fpc_moment_Am"])); V = cplx(d["V_oc_V"])
        ok = np.abs(V) > 1e-4
        f, mf, V = f[ok], mf[ok], V[ok]
        H = mf / np.abs(V)
        Tb = 1 / PCLK; p = 0.1; r_ = 1 - 2 * p
        S1 = 2 * (1.65 ** 2) * Tb * np.sinc(f * Tb) ** 2 * (1 - r_ ** 2) / (1 - 2 * r_ * np.cos(2 * np.pi * f * Tb) + r_ ** 2)
        Vrbw = np.sqrt(S1 * 120e3) * math.sqrt(2)
        mom = H * Vrbw * math.sqrt(24)
        Icm, Pin = cm_solve(cfg, f, mom / ELL, M_s, Q, 33, self_consistent)
        V = Vrbw; N = 24
        out = {"f": f, "DM-FPC": loopE(mom * 1.3e-3 * FOLD, f)}
    Rsrc = 30.0 + rs
    out["CM-FPC"] = Epa(cfg, f, which) * np.abs(Icm)
    for k_ in ("CM-FPC", "DM-board", "DM-FPC", "CAV-5V"):          # phasors are PEAK amplitudes -> rms fields for the QP limit
        if k_ in out:
            out[k_] = out[k_] / math.sqrt(2)
    out["Icm"] = Icm; out["P_in"] = Pin
    out["P_avail"] = N * np.abs(V) ** 2 / (8 * Rsrc)
    out["E_ceiling"] = np.sqrt(30 * 1.64 * out["P_avail"]) / r3
    out["cfg"] = cfg
    return out


def combine(m, keys):
    pw = np.sqrt(np.nansum([np.abs(m[k]) ** 2 for k in keys], axis=0))
    mg = np.nansum([np.abs(m[k]) for k in keys], axis=0)
    return pw, mg


KEYS = ("CM-FPC", "DM-board", "DM-FPC", "CAV-5V")


def band_table(kind, cfg="nominal", env=True, lim=lim_far3m, which="E3", **kw):
    """rows per harmonic: nominal (Q 10), band low (Q 30... i.e. strongest loss Q 3) / high (Q 30, envelope of configs)"""
    mn = mech(kind, cfg, QNOM, which=which, **kw)
    lo = mech(kind, cfg, 3.0, which=which, **kw)
    hi = [mech(kind, cfg, 30.0, which=which, **kw)]
    if env:
        hi += [mech(kind, c, 30.0, which=which, **kw) for c in ENV_CFGS if c != cfg]
    f = mn["f"]
    keys = [k for k in KEYS if k in mn]
    pn, _ = combine(mn, keys); pl, _ = combine(lo, keys)
    ph = np.nanmax([combine(h, keys)[1] for h in hi], axis=0)
    rows = []
    for i in np.where((f >= 30e6) & (f <= 1000e6) & (pn > 1e-9))[0]:
        L = float(lim(f[i]))
        rows.append({"f_MHz": round(f[i] / 1e6, 2), "E_nom_Q10": round(float(dBuV(pn[i])), 1), "E_low_Q3": round(float(dBuV(pl[i])), 1),
                     "E_high_Q30_env": round(float(dBuV(ph[i])), 1), "limit": round(L, 1),
                     "margin_nom": round(L - float(dBuV(pn[i])), 1), "margin_high": round(L - float(dBuV(ph[i])), 1),
                     "dominant": max(keys, key=lambda k: np.nan_to_num(np.abs(mn[k][i]))),
                     **{k: round(float(dBuV(mn[k][i])), 1) for k in keys}})
    return rows


def worst(rows, key="margin_nom"):
    rows = [r for r in rows if r[key] == r[key]]
    return min(rows, key=lambda r: r[key]) if rows else None


res = {"model": __doc__.split("\n")[0], "limits": CITE["table9"], "mode": modeinfo, "Q_band": list(QBAND), "Q_nominal": QNOM,
       "M_nH": {"data_in_phase": M_d * 1e9, "pclk": M_p * 1e9, "single": M_s * 1e9}}

# ---------------- power balance (reviewer item 1) -------------------------------------------------------------------
pb = []
for kind in ("worst", "pclk"):
    old = mech(kind, "nominal", float("inf"), self_consistent=False)
    sc = mech(kind, "nominal", float("inf"))
    q10 = mech(kind, "nominal", 10.0); q3 = mech(kind, "nominal", 3.0); q30 = mech(kind, "nominal", 30.0)
    for i in np.where((old["f"] >= 30e6) & (old["f"] <= 1000e6) & (old["P_avail"] > 1e-12))[0]:
        pb.append({"source": "24 data lines in phase" if kind == "worst" else "PCLK", "f_MHz": round(old["f"][i] / 1e6, 2),
                   "P_avail_uW": round(float(old["P_avail"][i] * 1e6), 3),
                   "P_in_v1_ideal_source_lossless_uW": round(float(old["P_in"][i] * 1e6), 3),
                   "P_in_self_consistent_lossless_uW": round(float(sc["P_in"][i] * 1e6), 3),
                   "P_in_Q30_uW": round(float(q30["P_in"][i] * 1e6), 3), "P_in_Q10_uW": round(float(q10["P_in"][i] * 1e6), 3), "P_in_Q3_uW": round(float(q3["P_in"][i] * 1e6), 3),
                   "ratio_Q10_to_avail_dB": round(float(10 * np.log10(max(q10["P_in"][i], 1e-30) / old["P_avail"][i])), 1),
                   "E_ceiling_dBuVm(2.15dBi)": round(float(dBuV(old["E_ceiling"][i])), 1), "E_Q10_dBuVm_rms": round(float(dBuV(q10["CM-FPC"][i])), 1)})
res["power_balance"] = pb
res["power_balance_check"] = {"max_P_in/P_avail_dB_self_consistent_lossless": round(max(10 * np.log10(max(r["P_in_self_consistent_lossless_uW"], 1e-30) / r["P_avail_uW"]) for r in pb), 2),
                              "max_P_in/P_avail_dB_Q10": round(max(r["ratio_Q10_to_avail_dB"] for r in pb), 2),
                              "max_P_in/P_avail_dB_v1_ideal_source": round(max(10 * np.log10(max(r["P_in_v1_ideal_source_lossless_uW"], 1e-30) / r["P_avail_uW"]) for r in pb), 2)}
for r in pb:
    if r["f_MHz"] in (116.55, 166.5, 183.15, 99.9, 233.1):
        print(r)
print(res["power_balance_check"], modeinfo)

# ---------------- lumped cross-check of the panel/PCB mode (reviewer item 1c) ---------------------------------------
A = 0.164 * 0.099
C5 = EPS0 * A / 5e-3; C64 = EPS0 * A / 6.4e-3
L_impl = 1 / (w0 ** 2 * C5)
# independent L: FPC return bundle (4 strips spread over 17 mm -> GMD radius ~4 mm) along the 75 mm U-path + plate spreading
lfp = 0.075; req = 4e-3
L_fpc = MU0 * lfp / (2 * np.pi) * (np.log(2 * lfp / req) - 1)
L_pl = MU0 * 6.4e-3 * 0.099 / 0.164
f_lumped = [1 / (2 * np.pi * math.sqrt((L_fpc + L_pl) * C)) for C in (C5, C64)]
Cself = 8 * EPS0 * math.sqrt(A / np.pi)
cab = {c: np.array(D["cable_max_mA_per_V"][c])[i0] * 1e-3 for c in D["cable_max_mA_per_V"] if c != "fpc"}
I_mom = max(cab.values())
I_lumped = Q_struct * w0 * Cself      # A per V of source: V_gap = Q V_src, I_cm ~ w C_self,panel V_gap
res["lumped_check"] = {"C_plates_5mm_pF": C5 * 1e12, "C_plates_6.4mm_pF": C64 * 1e12, "L_fpc_partial_nH": L_fpc * 1e9, "L_plates_nH": L_pl * 1e9,
                       "f0_lumped_MHz(5mm, 6.4mm)": [x / 1e6 for x in f_lumped], "f0_MoM_MHz": fdn[i0] / 1e6, "L_implied_by_MoM_f0_and_C5_nH": L_impl * 1e9,
                       "C_self_panel_pF": Cself * 1e12, "Q_struct": Q_struct, "cable_CM_A_per_V_lumped": I_lumped, "cable_CM_A_per_V_MoM_max": I_mom,
                       "MoM_vs_lumped_dB": float(20 * np.log10(I_mom / I_lumped)), "cables_at_f0_A_per_V": cab}
print(res["lumped_check"])

# ---------------- verdict rows (reviewer item 3) --------------------------------------------------------------------
TAB = {"PCLK": band_table("pclk"), "typical UI": band_table("typical"), "worst pattern": band_table("worst")}
res["tables"] = TAB
res["worst_rows"] = {k: worst(v) for k, v in TAB.items()}
res["worst_rows_upper"] = {k: worst(v, "margin_high") for k, v in TAB.items()}
# SAC 10 m (structure E10 only for nominal / bond configs)
sac = {}
for k, kind in (("PCLK", "pclk"), ("worst pattern", "worst"), ("typical UI", "typical")):
    for cfg in ("nominal", "bond_6pt", "bond_perimeter"):
        if cfg in CM and CM[cfg].get("E10_dBuV_per_V"):
            rows = band_table(kind, cfg, env=False, lim=lim_sac10m, which="E10")
            sac[f"{k} | {cfg}"] = worst(rows)
res["sac10"] = sac
# cable budget (nominal structure, Q 10 nominal, band Q3..Q30)
bud = {}
for cable in ("mains_cable", "heater", "fan", "tc"):
    rows = []
    for fx in (99.9e6, 166.5e6, 233.1e6, 299.7e6, 499.5e6):
        e_per_A = Epa("nominal", fx) / Cpa("nominal", cable, fx)      # V/m per A on that cable
        Ilim = 10 ** ((lim_far3m(fx) - 120) / 20) / e_per_A
        est = {}
        for Q in (QNOM, 3.0, 30.0):
            m = mech("pclk", "nominal", Q)
            j = int(np.argmin(np.abs(m["f"] - fx)))
            est[Q] = float(np.abs(m["Icm"][j]) * Cpa("nominal", cable, fx)) / math.sqrt(2)      # rms
        rows.append({"f_MHz": round(fx / 1e6, 1), "I_at_limit_uA": round(float(Ilim * 1e6), 2), "I_est_PCLK_Q10_uA": round(est[QNOM] * 1e6, 2),
                     "band_uA(Q3..Q30)": [round(est[3.0] * 1e6, 2), round(est[30.0] * 1e6, 2)]})
    bud[cable] = rows
res["cable_budget"] = bud
# disturbance power (indicative, method a): |I_mains|^2 * 100 ohm vs Table 7
dp = {}
for k, kind in (("PCLK", "pclk"), ("worst pattern", "worst")):
    m = mech(kind, "nominal", QNOM)
    f = m["f"]; sel = (f >= 30e6) & (f <= 300e6) & (m["P_avail"] > 1e-12)
    I = np.abs(m["Icm"][sel]) * Cpa("nominal", "mains_cable", f[sel]) / math.sqrt(2)     # rms
    P = 10 * np.log10(np.maximum(I ** 2 * 100, 1e-30) / 1e-12)
    mar = lim_power_qp(f[sel]) - P
    i = int(np.nanargmin(mar))
    dp[k] = {"worst_margin_dB": round(float(mar[i]), 1), "at_MHz": round(float(f[sel][i] / 1e6), 2), "P_dBpW": round(float(P[i]), 1)}
res["disturbance_power_indicative"] = dp

# ---------------- other sources (unchanged, accepted) ---------------------------------------------------------------
d = SC["bus_8080_WR"]; fwr = np.array(d["f_MHz"]) * 1e6; E_wr = loopE(cplx(d["moment_Am"]) * h_eff, fwr)
d = SC["bus_8080_data8_in_phase"]; fb = np.array(d["f_MHz"]) * 1e6; E_bus = loopE(cplx(d["moment_Am"]) * h_eff, fb)
loops = LAY["hot_loops"]
def trap(I, f0, duty, tr, f):
    n = np.round(f / f0)
    return 2 * I * duty * np.abs(np.sinc(n * duty)) * np.abs(np.sinc(f * tr))
fconv = np.geomspace(30e6, 1000e6, 200)
la = lambda k: (loops[k]["planar_area_mm2"] + loops[k]["vertical_area_if_return_in_In1_mm2"]) * 1e-6
E_buck = loopE(trap(0.9, 580e3, 0.66, 5e-9, fconv) * la("buck input loop C330-U30(VIN,GND)"), fconv)
E_boost = loopE(trap(0.45, 1.2e6, 0.55, 5e-9, fconv) * la("boost switching loop U11SW-D111-C125-U11GND"), fconv)
E_xtal = loopE(trap(2 * math.pi * 10e6 * 27e-12 * 1.5, 10e6, 0.5, 5e-9, fconv) * la("crystal loop Y10-C110-C111"), fconv)
res["other_sources_min_margin_dB"] = {k: round(float(np.min(lim_far3m(ff) - dBuV(e / math.sqrt(2)))), 1) for k, ff, e in
                                      (("8080 WR", fwr[fwr >= 30e6], E_wr[fwr >= 30e6]), ("8080 data", fb[fb >= 30e6], E_bus[fb >= 30e6]),
                                       ("buck", fconv, E_buck), ("boost", fconv, E_boost), ("crystal", fconv, E_xtal))}

# ---------------- proposals (reviewer item 3) ------------------------------------------------------------------------
P = {}
def prow(kind, cfg, **kw):
    rows = band_table(kind, cfg, env=False, **kw)
    return {"nominal": worst(rows), "upper": worst(rows, "margin_high")}
for cfg in ("bond_6pt", "bond_perimeter", "ferrite_fpc_150", "bond_perimeter_ferrite", "frame_floating"):
    if cfg in CM:
        P[cfg] = {k: prow(kind, cfg) for k, kind in (("PCLK", "pclk"), ("typical UI", "typical"), ("worst pattern", "worst"))}
P["RN 150 ohm"] = {"PCLK": prow("pclk", "nominal", key="pclk_rs150", rs=150), "worst pattern": prow("worst", "nominal", key="Rs150 Rout30 tr1.5 Cin5", rs=150)}
P["2x1nF +5V at J10 vias"] = {"PCLK": prow("pclk", "nominal", zkey="Z_J10_complex_with_2x1nF")}
for cfg in ("bond_6pt", "bond_perimeter", "bond_perimeter_ferrite"):
    if cfg in CM:
        P[f"{cfg} + RN 150 + 2x1nF"] = {"PCLK": prow("pclk", cfg, key="pclk_rs150", rs=150, zkey="Z_J10_complex_with_2x1nF"),
                                        "typical UI": prow("typical", cfg),
                                        "worst pattern": prow("worst", cfg, key="Rs150 Rout30 tr1.5 Cin5", rs=150)}
# J10 via-field capacitor options (c7b: caps modelled 2.5 mm from the vias with 0402 ESL + via mounting)
CAPOPT = {"2x1nF": "Z_J10_complex_with_2x1nF", "2x100nF": "Z_J10_complex_with_2x100nF", "2x(10nF+1ohm)": "Z_J10_complex_with_2x10nFp1ohm",
          "100nF+(1nF+2.2ohm)": "Z_J10_complex_with_100nFp1nFp2.2ohm"}
for nm, zk in CAPOPT.items():
    if zk not in PDN["5V"]:
        continue
    P[f"J10 caps {nm} alone"] = {"PCLK": prow("pclk", "nominal", zkey=zk)}
    for cfg in ("bond_perimeter", "bond_perimeter_ferrite"):
        if cfg in CM:
            P[f"{cfg} + RN 150 + J10 caps {nm}"] = {"PCLK": prow("pclk", cfg, key="pclk_rs150", rs=150, zkey=zk)}
    # cavity term alone at the PCLK harmonics (to show what the cap choice does to that mechanism)
    mm = mech("pclk", "bond_perimeter_ferrite" if "bond_perimeter_ferrite" in CM else "nominal", QNOM, key="pclk_rs150", rs=150, zkey=zk)
    P[f"J10 caps {nm} alone"]["CAV-5V_dBuVm_at_MHz"] = {f"{x/1e6:.1f}": round(float(dBuV(mm["CAV-5V"][i])), 1) for i, x in enumerate(mm["f"])
                                                       if x <= 1e9 and mm["P_avail"][i] > 1e-12}
res["proposals"] = P
# cross-scope (Y1, oven) rows with the corrected model
xs = {}
for cfg in ("Y1_1nF", "oven_tc_bonded"):
    if cfg in CM:
        xs[cfg] = {k: prow(kind, cfg) for k, kind in (("PCLK", "pclk"), ("typical UI", "typical"))}
        Im = np.array([Cpa(cfg, "mains_cable", f) / max(Cpa("nominal", "mains_cable", f), 1e-30) for f in fq])
        xs[cfg]["mains_cord_current_per_gap_ampere_vs_nominal_dB"] = {"median": round(float(np.nanmedian(dB(Im))), 1), "max": round(float(np.nanmax(dB(Im))), 1)}
res["cross_scope_emission"] = xs
save_section("emission", rnd(res, 3))

# ---------------- plots ---------------------------------------------------------------------------------------------
ff = np.geomspace(30e6, 1000e6, 400)
fig, axs = plt.subplots(2, 1, figsize=(12, 10.5))
for ax, kind, title in ((axs[0], "pclk", "PCLK 33.3 MHz harmonics (always present) + typical UI content"),
                        (axs[1], "worst", "Worst display pattern (1-pixel stripes, 24 data lines in phase)")):
    ax.semilogx(ff / 1e6, lim_far3m(ff), "k-", lw=2, label="EN 55014-1 Table 9 FAR 3 m QP limit (PDF p.38)")
    ax.semilogx(ff / 1e6, lim_far3m(ff) - 6, "k:", lw=1, label="limit - 6 dB")
    mn = mech(kind, "nominal", QNOM); lo = mech(kind, "nominal", 3.0)
    hi = [mech(kind, c, 30.0) for c in ENV_CFGS]
    keys = [k for k in KEYS if k in mn]
    pn, _ = combine(mn, keys); pl, _ = combine(lo, keys); ph = np.nanmax([combine(h, keys)[1] for h in hi], axis=0)
    k_ = (mn["f"] >= 30e6) & (mn["f"] <= 1000e6) & (mn["P_avail"] > 1e-12)
    ax.semilogx(mn["f"][k_] / 1e6, dBuV(pn[k_]), "rs", label="nominal (Q 10, nominal cables)")
    ax.vlines(mn["f"][k_] / 1e6, dBuV(pl[k_]), dBuV(ph[k_]), colors="r", alpha=.45, lw=3, label="band: Q 3 ... Q 30 + cable/barrier envelope")
    ax.semilogx(mn["f"][k_] / 1e6, dBuV(mn["E_ceiling"][k_]), "kv", ms=5, mfc="none", label="ceiling: all available driver power radiated (2.15 dBi)")
    ax.semilogx(mn["f"][k_] / 1e6, dBuV(mn["DM-board"][k_]), "g^", ms=4, label="DM board traces")
    if kind == "pclk":
        ax.semilogx(mn["f"][k_] / 1e6, dBuV(mn["CAV-5V"][k_]), "c.", ms=5, label="+5V island cavity (upper est.)")
        ty = mech("typical", "nominal", QNOM)
        kt = ty["f"] >= 30e6
        ax.semilogx(ty["f"][kt] / 1e6, dBuV(np.sqrt(ty["CM-FPC"][kt] ** 2 + ty["DM-FPC"][kt] ** 2)), "b.", ms=4, label="typical UI data in 120 kHz (Q 10)")
        ax.semilogx(fconv / 1e6, dBuV(E_buck), "y-", lw=.8, label="buck loop"); ax.semilogx(fconv / 1e6, dBuV(E_boost), "-", color="orange", lw=.8, label="boost loop")
    ax.set_xlabel("MHz"); ax.set_ylabel("dBuV/m at 3 m (QP, FAR)"); ax.grid(True, which="both", alpha=.3); ax.set_title(title)
    ax.set_xlim(30, 1000); ax.set_ylim(-10, 110); ax.legend(fontsize=7, ncol=2)
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "emission_far3m.png"), dpi=150)
fig, ax = plt.subplots(figsize=(11, 5))
for kind, mk in (("worst", "o"), ("pclk", "s")):
    sel = [r for r in pb if r["source"].startswith("PCLK" if kind == "pclk" else "24")]
    f_ = [r["f_MHz"] for r in sel]
    ax.semilogy(f_, [r["P_avail_uW"] for r in sel], "k" + mk, mfc="none", label=f"{kind}: P_avail")
    ax.semilogy(f_, [max(r["P_in_v1_ideal_source_lossless_uW"], 1e-9) for r in sel], "r" + mk, ms=4, label=f"{kind}: v1 ideal source, lossless")
    ax.semilogy(f_, [max(r["P_in_Q10_uW"], 1e-9) for r in sel], "b" + mk, ms=4, label=f"{kind}: v2 self-consistent, Q 10")
ax.set_xscale("log"); ax.set_xlabel("MHz"); ax.set_ylabel("uW"); ax.set_ylim(1e-6, 1e5); ax.grid(True, which="both", alpha=.3); ax.legend(fontsize=7, ncol=3)
ax.set_title("Power balance per harmonic: power delivered to the CM structure vs available driver power")
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "emission_power_balance.png"), dpi=150)
fig, ax = plt.subplots(figsize=(11, 5))
for c in CFGS:
    ax.semilogx(fq / 1e6, arr(CM[c]["E3_dBuV_per_V"]), label=c, lw=2 if c in ("nominal", "bond_perimeter") else 0.8)
ax.set_xlabel("MHz"); ax.set_ylabel("dBuV/m at 3 m per 1 V at the FPC gap (lossless MoM)"); ax.grid(True, which="both", alpha=.3); ax.legend(fontsize=6, ncol=3)
ax.set_title("MoM structure transfer (before loss and driver loading)")
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "emission_structure_transfer.png"), dpi=150)
print(json.dumps(rnd(res["worst_rows"], 1), indent=0)); print(json.dumps(rnd(res["worst_rows_upper"], 1), indent=0))
print(json.dumps(rnd(res["sac10"], 1))); print(json.dumps(rnd(res["disturbance_power_indicative"], 1)))
for k, v in P.items():
    print(k, {kk: ((vv["nominal"]["f_MHz"], vv["nominal"]["E_nom_Q10"], vv["nominal"]["margin_nom"], vv["upper"]["margin_high"], vv["nominal"]["dominant"]) if vv and vv.get("nominal") else None) for kk, vv in v.items()})
print(json.dumps(rnd(xs, 1)))
