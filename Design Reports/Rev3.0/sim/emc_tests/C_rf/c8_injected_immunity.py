"""C_rf step 8 - injected RF immunity (EN 55014-2:2015 5.4, cat. IV: 0.15-80 MHz, 1 kHz 80 % AM, 150 ohm;
Table 10 a.c. power port 3 V; Table 8 signal ports 1 V only if the cable can exceed 3 m - PDF p.19-20) - ngspice AC model.

Set-up (IEC 61000-4-6, NOT read from the standard - public description): EUT on a 0.1 m insulating support over the
reference ground plane (RGP); CDN = EMF U0 behind 150 ohm; "test level" = unmodulated open-circuit EMF; with 80 % AM the
peak envelope is 1.8 x U0 x sqrt(2).
Common-mode network (all to RGP = node 0; values ASSUMED unless marked, swept in the corners):
  mains CM conductor M (L+N tied by the X capacitors C40/C1): CDN -> 0.3 uH cable -> M; M-RGP 20 pF; M-SELV: HLK-10M05
  barrier 47 pF (20..100) + 5 pF board stray; heater element to oven body OV 150 pF (50..300); OV-RGP 50 pF; SELV-RGP 15 pF;
  panel metal / PCB to the steel front sheet (= OV) 30 pF.
  Thermocouple TC1 = WRNT-02 "M6 ring tip, 1 m" (schematic): ring screwed to the oven steel -> case G (grounded junction,
  galvanic OV->junction) or case I (insulated junction, 50 pF). Lead: 2 x 1.2 uH, k = 0.95, 1.4 / 0.6 ohm (chromel/alumel).
Input network (schematic Rev3_Thermocouple, values of 2026-11-13): per leg TVS PESD5V0S1BA (35 pF, ASSUMED +-10 %) and
  10 MOhm bias at the terminal, R220/R221 1 kOhm 0.1 % (+0.05 pF), C221/C222 10 nF X7R +-10 % (CL10B103KB8NNNC - NOT the
  C0G 1 % of spec 6), ESL 0.45 + via 0.25 nH, C220 100 nF X7R across (ESL 0.7 nH), ADS1115 input 5 pF/pin (ASSUMED);
  traces 21 + 12.5 mm at 0.36 nH/mm (c2 lengths); cap GND vias 7 mm either side of the U20 GND pin (c2), plane L 20 pH
  +-50 % mismatch.
Rectification -> temperature: (a) worst-case bound: square-law with EMIRR 20 dB (TI SBOA128 definition
  EMIRR = 20 log(Vrf_pk^2 / (100 mV * dVos)), public source), CM weighted 1:1; (b) realistic: EMIRR 40 dB, CM weighted 0.1.
  AM factor (1 + m^2/2) = 1.32 on the DC term; the 1 kHz term is rejected by the 16 SPS sinc (|sinc| <= 1/(pi*1000/16) = -46 dB)
  and the firmware median-5 + EMA(0.1) passes a DC shift unchanged. Type K Seebeck 41 uV/K.
Criterion A tolerance: the spec has none -> PROPOSED 0.5 degC (the old assessment's control resolution), flagged.
Outputs: results.json["injected"], plots/inj_*.png ; transfer functions per ampere at J20 (for c9 radiated).
"""
import json, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from c0_common import *

ng = spice()
SEEBECK = 41e-6
TOL_C = 0.5


def netlist(case, mode, corner, f0=0.15e6, f1=80e6, pts=60, Ciso=47e-12, Cho=150e-12, src_at="mains", iprobe=False, Y1=0.0):
    """mode 'mains': CDN on the mains port; 'tc': CDN/clamp on the thermocouple lead; 'iJ20': 1 A CM injected into J20."""
    c = corner
    dC = 0.10 * c; dT = 0.10 * c; dR = 0.001 * c; dL = 0.5 * c
    s = [f"inj {case} {mode}"]
    if mode == "mains":
        s += ["Vemf emf 0 DC 0 AC 1", "Rcdn emf m1 150", "Lcab m1 M 0.3u"]
    else:
        s += ["Rcdnm M 0 150"]                       # mains port terminated by its CDN (150 ohm) during the TC-port test
    if Y1:                                   # cross-scope (B): Y1 SELV GND -> NEUT at PS1, disc + leads 8 nH, 0.1 ohm (ASSUMED)
        s += [f"CY1 M y1a {Y1}", "LY1 y1a y1b 8n", "RY1 y1b SG 0.1"]
    s += ["CMr M 0 20p", f"Ciso M SG {Ciso}", "Riso SG SGx 0.01", "CMs M SG 5p", f"Cho M OV {Cho}", "COV OV 0 50p",
          "CSG SG 0 15p", "CSO SG OV 30p", "RdcS SG 0 1G", "RdcO OV 0 1G", "RdcM M 0 1G"]
    # thermocouple lead: junction node TJ; legs TP/TN
    if case == "G":
        s += ["Rjct OV TJ 0.01"]
    else:
        s += ["Cjct OV TJ 20p"]              # insulated junction: 20 pF probe-to-chassis (scope A figure)
    if mode == "tc":
        s += ["Vemf emf 0 DC 0 AC 1", "Rcdn emf tj1 150", "Ltc tj1 TJ 0.2u"]
    if mode == "iJ20":
        s += ["Iinj 0 TJ DC 0 AC 1"]                        # 1 A into the junction; lead -> board (transfer per ampere)
    s += ["L1 TJ tpw 1.2u", "L2 TJ tnw 1.2u", "K12 L1 L2 0.95", "Rw1 tpw TP 1.4", "Rw2 tnw TN 0.6"]
    # board input network
    Cp, Cn = 10e-9 * (1 + dC), 10e-9 * (1 - dC)
    Tp, Tn = 35e-12 * (1 + dT), 35e-12 * (1 - dT)
    Rp, Rn = 1e3 * (1 + dR), 1e3 * (1 - dR)
    s += [f"CtvsP TP SG {Tp}", f"CtvsN TN SG {Tn}", "RbP TP SG 10Meg", "RbN TN SG 10Meg",
          "LtP TP tp1 7.6n", "LtN TN tn1 7.6n", f"R220 tp1 fp0 {Rp}", f"R221 tn1 fn0 {Rn}", "CpR tp1 fp0 0.05p", "CpN tn1 fn0 0.05p",
          "LfP fp0 FP 4.5n", "LfN fn0 FN 4.5n",
          f"C221 FP c1 {Cp}", "Lc1 c1 g1 0.7n", f"Lg1 g1 SG {20e-12 * (1 + dL)}",
          f"C222 FN c2 {Cn}", "Lc2 c2 g2 0.7n", f"Lg2 g2 SG {20e-12 * (1 - dL)}",
          "C220 FP c3 100n", "Lc3 c3 FN 0.7n", "CinP FP SG 5p", "CinN FN SG 5p"]
    s += [f".ac dec {pts} {f0} {f1}", ".end"]
    return "\n".join(s) + "\n"


def sim(case, mode, corner, f1=80e6, **kw):
    v = ng.run_netlist(netlist(case, mode, corner, f1=f1, **kw))
    f = np.real(v["frequency"])
    vsg = v["v(sg)"]
    out = {"f": f,
           "Vdm": v["v(fp)"] - v["v(fn)"],
           "Vcm": (v["v(fp)"] + v["v(fn)"]) / 2 - vsg,
           "VJ": (v["v(tp)"] + v["v(tn)"]) / 2 - vsg,
           "VMSG": v["v(m)"] - vsg,
           "Isg": None}
    return out


def dT_from(Vdm_pk, Vcm_pk, emirr_dB, wcm):
    dv = (Vdm_pk ** 2 + wcm * Vcm_pk ** 2) / (0.1 * 10 ** (emirr_dB / 20)) * (1 + 0.8 ** 2 / 2)
    return dv / SEEBECK


res = {"model": __doc__.split("\n")[0], "criterion_A_proposed_degC": TOL_C, "AM_peak_factor": 1.8}
plt.figure(figsize=(12, 8))
ax1 = plt.subplot(2, 2, 1); ax2 = plt.subplot(2, 2, 2); ax3 = plt.subplot(2, 1, 2)
tests = {"mains port 3 V (Table 10)": ("mains", 3.0), "TC lead 1 V (Table 8, only if > 3 m)": ("tc", 1.0)}
for tname, (mode, U0) in tests.items():
    for case in ("G", "I"):
        for corner in (0, 1):
            for ciso, cho in ((47e-12, 150e-12), (100e-12, 300e-12), (20e-12, 50e-12)):
                r = sim(case, mode, corner, Ciso=ciso, Cho=cho)
                pk = U0 * math.sqrt(2) * 1.8
                Vdm, Vcm, VJ = np.abs(r["Vdm"]) * pk, np.abs(r["Vcm"]) * pk, np.abs(r["VJ"]) * pk
                dTw = dT_from(Vdm, Vcm, 20, 1.0)
                dTr = dT_from(Vdm, Vcm, 40, 0.1)
                key = f"{tname} | junction {'grounded' if case == 'G' else 'insulated'} | corner {'worst tol' if corner else 'nominal'} | Ciso {ciso*1e12:.0f}p Cheater-oven {cho*1e12:.0f}p"
                i = int(np.argmax(dTw)); j = int(np.argmax(VJ))
                res[key] = {"max_Vdm_ADC_mVpk": float(Vdm.max() * 1e3), "at_MHz": float(r["f"][int(np.argmax(Vdm))] / 1e6),
                            "max_Vcm_ADC_mVpk": float(Vcm.max() * 1e3), "max_VJ20_cm_Vpk": float(VJ.max()), "VJ20_at_MHz": float(r["f"][j] / 1e6),
                            "TVS_conducts(>5 V)": bool(VJ.max() > 5.0),
                            "dT_worst_bound_degC": float(dTw.max()), "dT_worst_at_MHz": float(r["f"][i] / 1e6),
                            "dT_realistic_degC": float(dTr.max()),
                            "alias_bound_degC_at_n*250kHz": float(np.interp([0.25e6, 0.5e6, 1e6, 2e6], r["f"], Vdm).max() / SEEBECK)}
                if ciso == 47e-12 and cho == 150e-12:
                    lab = f"{mode} {case} {'tol' if corner else 'nom'}"
                    ax1.loglog(r["f"] / 1e6, Vdm * 1e3, label=lab)
                    ax2.loglog(r["f"] / 1e6, VJ, label=lab)
                    ax3.loglog(r["f"] / 1e6, np.maximum(dTw, 1e-6), label=lab + " worst bound")
                    ax3.loglog(r["f"] / 1e6, np.maximum(dTr, 1e-6), ls=":", label=lab + " realistic")
ax1.set_title("DM RF at the ADS1115 pins (peak, AM envelope)"); ax1.set_xlabel("MHz"); ax1.set_ylabel("mV pk"); ax1.grid(True, which="both", alpha=.3); ax1.legend(fontsize=6)
ax2.set_title("CM RF at J20 vs SELV GND (TVS 5 V working)"); ax2.set_xlabel("MHz"); ax2.set_ylabel("V pk"); ax2.axhline(5, color="r", ls="--"); ax2.grid(True, which="both", alpha=.3)
ax3.axhline(TOL_C, color="r", ls="--", label="proposed criterion A 0.5 degC"); ax3.set_xlabel("MHz"); ax3.set_ylabel("temperature shift, degC")
ax3.set_title("Rectified DC shift -> temperature error (EN 55014-2 Table 10 3 V / Table 8 1 V, 80 % AM)"); ax3.grid(True, which="both", alpha=.3); ax3.legend(fontsize=6, ncol=2)
plt.tight_layout(); plt.savefig(os.path.join(PLOTS, "inj_thermocouple.png"), dpi=150)

# transfer per ampere of CM current entering at the thermocouple junction (lead -> board), 0.15-1000 MHz (for c9)
tr = {}
for case in ("G",):
    for corner in (0, 1):
        r = sim(case, "iJ20", corner, f1=1000e6, pts=80)
        tr[f"corner{corner}"] = {"f_MHz": (r["f"] / 1e6).tolist(), "Vdm_per_A": np.abs(r["Vdm"]).tolist(), "Vcm_per_A": np.abs(r["Vcm"]).tolist(),
                                 "VJ_per_A": np.abs(r["VJ"]).tolist()}
json.dump(tr, open(os.path.join(WORK, "tc_transfer.json"), "w"))
res["tc_transfer_note"] = "per-ampere transfers J20 CM current -> ADC DM/CM saved to the work folder tc_transfer.json for c9"

# ---- ZCD Schmitt input (U6 pin 2, 10 k pull-up R8, H11AA1 collector): mains CM couples through the opto barrier
# H11AA1 input-output capacitance 0.5 pF typ / 1 pF ASSUMED (Isocom datasheet not in the project); node C 8 pF (U6 input + trace).
f = np.geomspace(0.15e6, 80e6, 200)
zcd = {}
r = sim("G", "mains", 0)
VM = np.interp(f, r["f"], np.abs(r["VMSG"])) * 3 * math.sqrt(2) * 1.8
for cio in (0.5e-12, 1.0e-12):
    zn = 1 / (1 / 10e3 + 1j * 2 * np.pi * f * 8e-12)
    vn = VM * np.abs(zn / (zn + 1 / (1j * 2 * np.pi * f * cio)))
    zcd[f"Cio {cio*1e12:.1f} pF"] = {"max_Vpk_at_U6_in": float(vn.max()), "at_MHz": float(f[np.argmax(vn)] / 1e6)}
zcd["mains_to_SELV_CM_Vpk_max"] = float(VM.max())
zcd["threshold_margin"] = "74AHC1G14 @3.3 V: VT+ >= 1.0 V min ... the idle levels are 0 V (opto on) or 3.3 V (pull-up); a toggle needs > ~1 V pk on the node (TI datasheet thresholds, not in the project folder - ASSUMED typical)"
res["ZCD"] = zcd
# ---- other logic nets: CM current flows on the solid planes; a 0.2 mm microstrip couples I_cm * Z_transfer of the plane (< 0.1 ohm)
Isg = VM / (1 / (2 * np.pi * f * 47e-12))
res["logic_nets"] = {"max_CM_current_through_HLK_mA": float(Isg.max() * 1e3),
                     "plane_transfer_voltage_mV_at_20pH": float((Isg * 2 * np.pi * f * 20e-12).max() * 1e3),
                     "I2C/TP_INT/LCD_RST to the CTP FPC": "the CTP FPC carries no CM current in this test unless the touch glass couples to the RGP; GT911 behaviour NOT SIMULABLE",
                     "EN": "C6 = 1 uF (schematic 2026-11-13; the PCB still carries 100 nF in its value field) on a 10 k pull-up: RF on EN < 1 mV for the plane voltages above"}
# ---- cross-scope: Y1 (scope B) - thermocouple result with Y1 470 pF / 1 nF / 2.2 nF, both junction cases, worst tolerance
y1 = {}
for case in ("G", "I"):
    for Y in (0.0, 470e-12, 1e-9, 2.2e-9):
        for mode, U0 in (("mains", 3.0), ("tc", 1.0)):
            r = sim(case, mode, 1, Ciso=50e-12, Y1=Y)
            pk = U0 * math.sqrt(2) * 1.8
            Vdm, Vcm, VJ = np.abs(r["Vdm"]) * pk, np.abs(r["Vcm"]) * pk, np.abs(r["VJ"]) * pk
            dTw = dT_from(Vdm, Vcm, 20, 1.0); dTr = dT_from(Vdm, Vcm, 40, 0.1)
            y1[f"{mode} {U0:.0f} V | junction {'grounded' if case == 'G' else 'insulated 20 pF'} | barrier 50 pF | Y1 {Y*1e12:.0f} pF"] = {
                "dT_worst_bound_degC": float(dTw.max()), "at_MHz": float(r["f"][int(np.argmax(dTw))] / 1e6), "dT_realistic_degC": float(dTr.max()),
                "max_VJ20_cm_Vpk": float(VJ.max()), "max_Vdm_ADC_mVpk": float(Vdm.max() * 1e3), "max_VMSG_Vpk": float((np.abs(r["VMSG"]) * pk).max())}
res["cross_scope_Y1_thermocouple"] = y1
# ZCD node with scope B's 1 nF C0G from the H11AA1 collector / U6 input to GND
for cio in (0.5e-12, 1.0e-12):
    zn = 1 / (1 / 10e3 + 1j * 2 * np.pi * f * (8e-12 + 1e-9))
    vn = VM * np.abs(zn / (zn + 1 / (1j * 2 * np.pi * f * cio)))
    zcd[f"Cio {cio*1e12:.1f} pF + 1 nF C0G (scope B)"] = {"max_Vpk_at_U6_in": float(vn.max()), "at_MHz": float(f[np.argmax(vn)] / 1e6)}
r = sim("G", "mains", 1, Ciso=50e-12, Y1=1e-9)
VMy = np.interp(f, r["f"], np.abs(r["VMSG"])) * 3 * math.sqrt(2) * 1.8
for nm, cn in (("Y1 1 nF, no ZCD cap", 8e-12), ("Y1 1 nF + 1 nF C0G", 1.008e-9)):
    zn = 1 / (1 / 10e3 + 1j * 2 * np.pi * f * cn)
    vn = VMy * np.abs(zn / (zn + 1 / (1j * 2 * np.pi * f * 1e-12)))
    zcd[nm + " (Cio 1 pF)"] = {"max_Vpk_at_U6_in": float(vn.max()), "at_MHz": float(f[np.argmax(vn)] / 1e6), "mains_to_SELV_Vpk": float(VMy.max())}
res["ZCD"] = zcd
save_section("injected", res)
worst = {k: (round(v["dT_worst_bound_degC"], 3), round(v["dT_realistic_degC"], 4), round(v["max_VJ20_cm_Vpk"], 2), round(v["max_Vdm_ADC_mVpk"], 3), v["dT_worst_at_MHz"])
         for k, v in res.items() if isinstance(v, dict) and "dT_worst_bound_degC" in v}
for k, v in worst.items():
    print(v, k)
print(json.dumps(res["ZCD"], indent=0)); print(json.dumps({k: (round(v["dT_worst_bound_degC"], 3), round(v["dT_realistic_degC"], 4), round(v["max_VJ20_cm_Vpk"], 2), round(v["max_VMSG_Vpk"], 2)) for k, v in y1.items()}, indent=0))
