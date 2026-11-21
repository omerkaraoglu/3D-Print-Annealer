"""Earthed-oven study - radiated emission 30-1000 MHz (EN 55014-1 Table 9, PDF p.38; FAR 3 m and SAC 10 m, rms vs QP limit)
for the decided design (RN1-RN7 150 ohm, 2 x 100 nF at the J10 via field, no Y1) inside the earthed oven body, without and
with the bonding concepts, with and without the FPC ferrite.

Method = the reviewed v2 method of ../../emc_tests/C_rf/c6_emission.py (read-only data from its results.json):
 I_cm = j w M I_0 / (Z_s + R_loss + w^2 (M_d^2 Y_d + M_p^2 Y_p)) with the passive distributed-EMF admittances (c4c, RN 150 ohm),
 Z_s = complex MoM gap impedance of each earthed configuration (e5), E = (E per volt) x |Z_s| x |I_cm| / sqrt(2) (rms),
 power balance P_in = 0.5 |I_cm|^2 Re Z_s <= P_avail = N |V_oc|^2 / (8 (30 + 150) ohm) checked per harmonic.
Loss band: the physical series loss resistances of the v2 issue (0 / 0.85 / 9.13 ohm = unloaded-Q 13 / 10 / 3 of the free-space
structure), nominal 0.85 ohm. Ferrite (owner's fix set): 150 ohm flat ferrite on the FPC as a series CM impedance at the gap
(R = 150 * min(1, f/100 MHz) + j w 0.3 uH / (1 + (f/30 MHz)^2), ASSUMED part model as in v2).
Other terms: DM board loops, DM FPC (folded x0.24), +5V island cavity with 2 x 100 nF (c7b), unchanged from v2.
Unearthed reference = the same post-processing on the v2 free-space structure ('nominal', 'bond_6pt', 'bond_perimeter').
Outputs: results.json["emission_earthed"], plots/emission_earthed_*.png"""
import json, math, glob
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from e0_common import *

O = old()
SC, I2D, PDN, EM = O["spice_chain"], O["inductance2d"], O["pdn"], O["emission"]
CMo = O["cm_structure"]
fq_old = np.array(CMo["freqs_MHz"]) * 1e6
ELL = (67.65 + 20.0) * 1e-3
FOLD = 0.24
RS = 100          # fitted value (decided 2026-11-21; no 150 ohm array stocked); 150 ohm shown for comparison
M_d, M_p, M_s = EM["M_nH"]["data_in_phase"] * 1e-9, EM["M_nH"]["pclk"] * 1e-9, EM["M_nH"]["single"] * 1e-9
RL = {"Q13 (no added loss)": 0.0, "Q10 (nominal)": EM["mode"]["R_loss_added_ohm"]["10.0"], "Q3": EM["mode"]["R_loss_added_ohm"]["3.0"]}
h_eff = I2D["board_ribbon"]["h_eff_mm_all"] * 1e-3
d_data = I2D["fpc_tft"]["all 24 data in phase, returns GND 3/29/36 + VDD 4"]["moment_mm_per_A_total"] * 1e-3
d_pclk = I2D["fpc_tft"]["PCLK (pin 30) alone, returns GND + VDD"]["moment_mm_per_A_total"] * 1e-3
r3 = 3.0
PCLK = 33.30e6


def cplx(lst):
    a = np.array(lst, float); return a[:, 0] * np.exp(1j * a[:, 1])


def dBuV(x):
    return dB(x) + 120


def loopE(m, f, r=r3):
    k = 2 * np.pi * f / C0
    return ETA0 * k ** 2 * np.abs(m) / (4 * np.pi * r) * np.sqrt(1 + 1 / (k * r) ** 2)


YDALL = dict(SC["Ydist"]); YDALL.update(load_results()["Ydist_Rs100"])


def _yd(key, mult=1.0):
    d = YDALL[key]; fy = np.array(d["f_MHz"]) * 1e6
    y = (np.maximum(np.array(d["re"]), 0) + 1j * np.array(d["im"])) * mult
    return lambda f: np.interp(f, fy, y.real) + 1j * np.interp(f, fy, y.imag)
YD = {rs: _yd(f"data_in_phase_Rs{rs}", 24) for rs in (100, 150)}
YP = {rs: _yd(f"pclk_Rs{rs}") for rs in (100, 150)}


def zref(f, rs=RS):
    w = 2 * np.pi * f
    return w ** 2 * (M_d ** 2 * YD[rs](f) + M_p ** 2 * YP[rs](f))


def zfer(f):
    return 150.0 * np.minimum(1.0, f / 100e6) + 1j * 2 * np.pi * f * 0.3e-6 / (1 + (f / 30e6) ** 2)


# ---------------- structures -------------------------------------------------------------------------------------
class Struct:
    def __init__(self, f, igap, e3, e10, cables):
        self.f, self.ig, self.e3, self.e10, self.cab = np.asarray(f), np.asarray(igap, complex), np.asarray(e3), np.asarray(e10), cables

    def at(self, arr, f, cplx_=False):
        if cplx_:
            return np.interp(f, self.f, arr.real) + 1j * np.interp(f, self.f, arr.imag)
        return np.interp(f, self.f, arr)

    def Zs(self, f):
        return 1 / self.at(self.ig, f, True)

    def Epa(self, f, which="E3"):
        return self.at(self.e3 if which == "E3" else self.e10, f) * np.abs(self.Zs(f))


S = {}
for fn in glob.glob(os.path.join(EWORK, "E_*.npz")):
    d = np.load(fn, allow_pickle=True)["d"].item()
    S[os.path.basename(fn)[:-4]] = Struct(d["f"], d["Igap"], d["E3"], d["E10"], d["cable_max"])
for k in ("nominal", "bond_6pt", "bond_perimeter"):          # unearthed v2 structures (free space), same post-processing
    c = CMo[k]
    ig = np.array([np.nan if x is None else x for x in c["Igap_re"]], float) + 1j * np.array([np.nan if x is None else x for x in c["Igap_im"]], float)
    e3 = 10 ** ((np.array(c["E3_dBuV_per_V"], float) - 120) / 20)
    e10 = 10 ** ((np.array(c["E10_dBuV_per_V"], float) - 120) / 20) if c.get("E10_dBuV_per_V") else e3 * np.nan
    S["U_" + k] = Struct(fq_old, ig, e3, e10, {})


def mech(kind, st, rl, ferrite=False, which="E3", rs=RS):
    if kind == "worst":
        d = SC["rgb_worst_in_phase"][f"Rs{rs} Rout30 tr1.5 Cin5"]; N = 24; M = M_d
    elif kind == "pclk":
        d = SC[f"pclk_rs{rs}"]; N = 1; M = M_p
    else:
        d = SC["rgb_single_line_isolated"]; N = 24; M = M_s
    f = np.array(d["f_MHz"]) * 1e6
    mf = cplx(d["fpc_moment_Am"]); V = cplx(d["V_oc_V"])
    if kind == "typical":
        ok = np.abs(V) > 1e-4
        f, mf, V = f[ok], np.abs(mf[ok]), V[ok]
        Tb = 1 / PCLK; p = 0.1; r_ = 1 - 2 * p
        S1 = 2 * (1.65 ** 2) * Tb * np.sinc(f * Tb) ** 2 * (1 - r_ ** 2) / (1 - 2 * r_ * np.cos(2 * np.pi * f * Tb) + r_ ** 2)
        Vrbw = np.sqrt(S1 * 120e3) * math.sqrt(2)
        mf = mf / np.abs(V) * Vrbw * math.sqrt(24); V = Vrbw
    sel = (f >= 30e6) & (f <= 1000e6) & (np.abs(V) > 1e-6)
    f, mf, V = f[sel], mf[sel], V[sel]
    w = 2 * np.pi * f
    Zs = st.Zs(f)
    Zt = Zs + rl + zref(f, rs) + (zfer(f) if ferrite else 0)
    Icm = 1j * w * M * (mf / ELL) / Zt
    out = {"f": f, "CM-FPC": st.Epa(f, which) * np.abs(Icm) / math.sqrt(2), "P_in": 0.5 * np.abs(Icm) ** 2 * Zs.real,
           "P_avail": N * np.abs(V) ** 2 / (8 * (30.0 + (rs if kind != "typical" else 33.0)))}
    if kind == "pclk":
        m1 = cplx(d["board_seg1_moment_Am"])[sel]; m2 = cplx(d["board_seg2_moment_Am"])[sel]
        out["DM-board"] = loopE((m1 + m2) * h_eff, f) / math.sqrt(2)
        out["DM-FPC"] = loopE(cplx(d["fpc_moment_Am"])[sel] * d_pclk * FOLD, f) / math.sqrt(2)
        z = PDN["5V"]["Z_J10_complex_with_2x100nF"]
        Zj = np.interp(f, np.array(z["f_MHz"]) * 1e6, np.abs(np.array(z["re"]) + 1j * np.array(z["im"])))
        Iret = np.abs(m2) / (O["layout"]["nets"]["RGB:PCLK"]["len_mm"] * 1e-3 * 0.35)
        out["CAV-5V"] = (w / C0) * Zj * Iret * 0.028 / (2 * np.pi * r3) / math.sqrt(2)
    elif kind == "worst":
        m1 = cplx(d["board_seg1_moment_Am"])[sel]; m2 = cplx(d["board_seg2_moment_Am"])[sel]
        out["DM-board"] = loopE((m1 + m2) * h_eff, f) / math.sqrt(2)
        out["DM-FPC"] = loopE(cplx(d["fpc_moment_Am"])[sel] * d_data * FOLD, f) / math.sqrt(2)
    else:
        out["DM-FPC"] = loopE(mf * 1.3e-3 * FOLD, f) / math.sqrt(2)
    return out


KEYS = ("CM-FPC", "DM-board", "DM-FPC", "CAV-5V")


def tot(m):
    return np.sqrt(np.nansum([np.abs(m[k]) ** 2 for k in KEYS if k in m], axis=0))


def row(kind, cfg, ferrite=False, which="E3", rs=RS):
    lim = lim_far3m if which == "E3" else lim_sac10m
    st = S[cfg]
    ms = {k: mech(kind, st, v, ferrite, which, rs) for k, v in RL.items()}
    f = ms["Q10 (nominal)"]["f"]
    E = {k: dBuV(tot(m)) for k, m in ms.items()}
    mar = {k: lim(f) - e for k, e in E.items()}
    i = int(np.nanargmin(mar["Q10 (nominal)"]))
    lo = float(np.nanmin(np.minimum(mar["Q13 (no added loss)"], mar["Q3"])))
    hi = float(np.nanmax([np.nanmin(mar["Q13 (no added loss)"]), np.nanmin(mar["Q3"])]))
    upper_margin = float(np.nanmin(np.minimum(np.minimum(mar["Q13 (no added loss)"], mar["Q3"]), mar["Q10 (nominal)"])))
    m10 = ms["Q10 (nominal)"]
    pb = float(np.nanmax(10 * np.log10(np.maximum(m10["P_in"], 1e-30) / m10["P_avail"])))
    dom = max([k for k in KEYS if k in m10], key=lambda k: np.nan_to_num(np.abs(m10[k][i])))
    return {"f_MHz": round(float(f[i] / 1e6), 2), "E_nom_dBuVm": round(float(E["Q10 (nominal)"][i]), 1), "limit": round(float(lim(f[i])), 1),
            "margin_nom_dB": round(float(mar["Q10 (nominal)"][i]), 1), "margin_upper_end_dB": round(upper_margin, 1),
            "margin_band_dB": [round(upper_margin, 1), round(float(np.nanmax([np.nanmin(m) for m in mar.values()])), 1)],
            "dominant": dom, "max_Pin_over_Pavail_dB": round(pb, 2)}


CFG_LABEL = {"U_nominal": "UNEARTHED (free space), no bonding", "U_bond_6pt": "UNEARTHED, i 6 pts", "U_bond_perimeter": "UNEARTHED, i 19 pts",
             "E_none_G": "EARTHED, no bonding, probe grounded", "E_none_I": "EARTHED, no bonding, probe insulated",
             "E_i6": "i panel-PCB 6 pts", "E_i19": "i panel-PCB 19 pts", "E_ii": "ii panel-sheet 12 pts",
             "E_iii1": "iii PCB-sheet 1 + panel-sheet", "E_iii4": "iii PCB-sheet 4 + panel-sheet", "E_iii9": "iii PCB-sheet 9 + panel-sheet",
             "E_iv1": "iv PCB-sheet 1", "E_iv4": "iv PCB-sheet 4", "E_iv9": "iv PCB-sheet 9",
             "E_i19_L10": "i 19 pts, 10 nH contacts", "E_ii_L10": "ii 12 pts, 10 nH contacts", "E_iii9_L10": "iii 9, 10 nH contacts"}
res = {"model": __doc__.split("\n")[0], "design_state": DESIGN, "loss_resistances_ohm": RL, "rows": {}}
for cfg in [c for c in CFG_LABEL if c in S]:
    r = {}
    for fer in (False, True):
        for which in ("E3", "E10"):
            if which == "E10" and np.all(np.isnan(S[cfg].e10)):
                continue
            for kind, lab in (("pclk", "PCLK"), ("typical", "typical UI"), ("worst", "worst pattern")):
                r[f"{lab} | {'FAR 3 m' if which == 'E3' else 'SAC 10 m'} | {'ferrite' if fer else 'no ferrite'}"] = row(kind, cfg, fer, which)
                if which == "E3" and kind != "typical":
                    r[f"{lab} | FAR 3 m | {'ferrite' if fer else 'no ferrite'} | RN 150 (comparison)"] = row(kind, cfg, fer, which, 150)
    res["rows"][CFG_LABEL[cfg]] = r
    print(CFG_LABEL[cfg], {k.replace(" | ", "/"): (v["margin_nom_dB"], v["margin_upper_end_dB"], v["f_MHz"]) for k, v in r.items() if "FAR" in k})
# earthing alone: delta vs unearthed for every row (same design state)
de = {}
if "E_none_G" in S:
    for k in res["rows"][CFG_LABEL["U_nominal"]]:
        if k in res["rows"][CFG_LABEL["E_none_G"]]:
            a, b = res["rows"][CFG_LABEL["U_nominal"]][k], res["rows"][CFG_LABEL["E_none_G"]][k]
            de[k] = {"unearthed_margin_nom": a["margin_nom_dB"], "earthed_margin_nom": b["margin_nom_dB"], "delta_nom_dB": round(b["margin_nom_dB"] - a["margin_nom_dB"], 1),
                     "unearthed_upper": a["margin_upper_end_dB"], "earthed_upper": b["margin_upper_end_dB"], "delta_upper_dB": round(b["margin_upper_end_dB"] - a["margin_upper_end_dB"], 1)}
res["earthing_alone_delta"] = de
# tolerable contact inductance (PCLK FAR, no ferrite and ferrite): margin at L ~ 2 nH (wire) and 10 nH, linear in dB vs L
tol = {}
for base, l10 in (("E_i19", "E_i19_L10"), ("E_ii", "E_ii_L10"), ("E_iii9", "E_iii9_L10")):
    if base in S and l10 in S:
        for fer in (False, True):
            k = f"PCLK | FAR 3 m | {'ferrite' if fer else 'no ferrite'}"
            m0 = res["rows"][CFG_LABEL[base]][k]["margin_upper_end_dB"]; m1 = res["rows"][CFG_LABEL[l10]][k]["margin_upper_end_dB"]
            slope = (m1 - m0) / 8.0
            Lt = 2.0 + (6.0 - m0) / slope if slope < 0 and m0 > 6 else None
            tol[f"{base} {'+ferrite' if fer else ''}"] = {"margin_at_~2nH": m0, "margin_at_10nH": m1, "dB_per_nH": round(slope, 2),
                                                          "contact_L_for_6dB_upper_nH": round(Lt, 1) if Lt else ("margin < 6 dB even at 2 nH" if m0 <= 6 else "insensitive")}
res["contact_inductance"] = tol
save_section("emission_earthed", res)
print(json.dumps(de, indent=0)[:2500]); print(json.dumps(tol, indent=0))
