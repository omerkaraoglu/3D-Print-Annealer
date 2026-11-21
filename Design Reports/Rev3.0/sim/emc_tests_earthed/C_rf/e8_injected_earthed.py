"""Earthed-oven study - injected RF immunity 0.15-80 MHz on the mains port of an EARTHED appliance (EN 55014-2:2015 5.4 Table 10,
3 V rms EMF, 1 kHz 80 % AM, 150 ohm, cat. IV criterion A - PDF p.20/23). Thermocouple (grounded / insulated junction),
ZCD node with the 1 nF C0G, and the SELV-PE bonding concepts. ngspice AC (KiCad 10 dll).

Set-up (IEC 61000-4-6, NOT READ - public description): EUT on a 0.1 m insulating support over the reference plane; a 3-wire
CDN (type M3) drives L, N and PE together from a 150 ohm common-mode source; cord to the CDN 0.3 m. For an earthed appliance
the PE in the cord is driven with L/N, so the whole oven body moves with the test voltage and the current returns to the
reference plane through the body's capacitance (and the SELV parts' capacitance seen through the front opening).
Network (to RGP = 0; values ASSUMED, corners swept): CDN -> 0.3 uH -> M (L/N CM) and -> 0.3 uH -> OV (body, via PE);
  OV-0 60 pF (0.4 m body at 0.1 m), M-0 5 pF, SG-0 10 pF; M-SG barrier 50 pF + 5 pF stray (no Y1); M-OV 150 pF (heater);
  SG-OV 30 pF (PCB/panel to the front sheet) ; thermocouple: grounded junction = galvanic OV-TJ, insulated = 20 pF;
  bonding SELV-PE (concepts iii/iv): SG-OV through 15 nH (1 point) / 3 nH (9 points); concept ii (panel-sheet): SG-OV via
  the FPC ground return 40 nH + 10 nH contact.
Front end, rectification model and criterion exactly as ../../emc_tests/C_rf/c8_injected_immunity.py (EMIRR 20 dB bound,
40 dB realistic; proposed criterion A 0.5 degC, owner to confirm).
Outputs: results.json["injected_earthed"], plots/inj_earthed.png"""
import json, math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from e0_common import *

ng = spice()
SEEBECK = 41e-6


def netlist(probe, bond, corner=1, f0=0.15e6, f1=80e6, pts=60):
    c = corner
    dC, dT, dR, dL = 0.10 * c, 0.10 * c, 0.001 * c, 0.5 * c
    s = ["inj earthed", "Vemf emf 0 DC 0 AC 1", "Rcdn emf cd 150", "Lcm cd M 0.3u", "Lpe cd OV 0.3u",
         "CMr M 0 5p", "COV OV 0 60p", "CSG SG 0 10p", "Ciso M SG 50p", "CMs M SG 5p", "Cho M OV 150p", "CSO SG OV 30p",
         "RdcS SG 0 1G", "RdcO OV 0 1G", "RdcM M 0 1G"]
    if bond == "iv-1 (SELV-PE 1 point)":
        s += ["Lb1 SG b1 15n", "Rb1 b1 OV 0.01"]
    elif bond == "iv-9 (SELV-PE 9 points)":
        s += ["Lb1 SG b1 3n", "Rb1 b1 OV 0.003"]
    elif bond == "ii (panel-sheet)":
        s += ["Lb1 SG b1 50n", "Rb1 b1 OV 0.1"]
    s += ["Rjct OV TJ 0.01"] if probe == "grounded" else ["Cjct OV TJ 20p"]
    s += ["L1 TJ tpw 1.2u", "L2 TJ tnw 1.2u", "K12 L1 L2 0.95", "Rw1 tpw TP 1.4", "Rw2 tnw TN 0.6"]
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


def dT_from(Vdm, Vcm, emirr, wcm):
    return (Vdm ** 2 + wcm * Vcm ** 2) / (0.1 * 10 ** (emirr / 20)) * 1.32 / SEEBECK


res = {"model": __doc__.split("\n")[0], "criterion_A_proposed_degC": 0.5, "cases": {}}
pk = 3.0 * math.sqrt(2) * 1.8
fig, ax = plt.subplots(1, 2, figsize=(13, 5))
for bond in ("none (earthed chassis only)", "ii (panel-sheet)", "iv-1 (SELV-PE 1 point)", "iv-9 (SELV-PE 9 points)"):
    for probe in ("grounded", "insulated"):
        v = ng.run_netlist(netlist(probe, bond))
        f = np.real(v["frequency"])
        vsg = v["v(sg)"]
        Vdm = np.abs(v["v(fp)"] - v["v(fn)"]) * pk
        Vcm = np.abs((v["v(fp)"] + v["v(fn)"]) / 2 - vsg) * pk
        VJ = np.abs((v["v(tp)"] + v["v(tn)"]) / 2 - vsg) * pk
        VMSG = np.abs(v["v(m)"] - vsg) * pk
        dTw, dTr = dT_from(Vdm, Vcm, 20, 1.0), dT_from(Vdm, Vcm, 40, 0.1)
        # ZCD node: H11AA1 collector / U6 input, 10 k pull-up, 8 pF + 1 nF C0G (decided), opto Cio 1 pF from the mains side
        zn = 1 / (1 / 10e3 + 1j * 2 * np.pi * f * (8e-12 + 1e-9))
        vz = VMSG * np.abs(zn / (zn + 1 / (1j * 2 * np.pi * f * 1e-12)))
        i = int(np.argmax(dTw))
        res["cases"][f"{bond} | probe {probe}"] = {"dT_worst_bound_degC": float(dTw.max()), "at_MHz": float(f[i] / 1e6),
                                                    "dT_realistic_degC": float(dTr.max()), "VJ20_cm_Vpk_max": float(VJ.max()),
                                                    "TVS_5V_margin_dB": float(20 * np.log10(5.0 / VJ.max())),
                                                    "mains_to_SELV_Vpk_max": float(VMSG.max()), "ZCD_node_Vpk_max(1 nF)": float(vz.max())}
        ax[0].loglog(f / 1e6, np.maximum(dTw, 1e-7), label=f"{bond[:18]} / {probe}")
        ax[1].loglog(f / 1e6, VJ, label=f"{bond[:18]} / {probe}")
ax[0].axhline(0.5, color="r", ls="--", label="proposed criterion A 0.5 degC"); ax[0].set_title("TC shift, worst bound (EMIRR 20 dB), 3 V Table 10, earthed")
ax[1].axhline(5.0, color="r", ls="--", label="TVS 5 V working"); ax[1].set_title("CM RF at J20 vs SELV GND")
for a in ax:
    a.set_xlabel("MHz"); a.grid(True, which="both", alpha=.3); a.legend(fontsize=6)
ax[0].set_ylabel("degC"); ax[1].set_ylabel("V pk")
fig.tight_layout(); fig.savefig(os.path.join(PLOTS, "inj_earthed.png"), dpi=150)
save_section("injected_earthed", rnd(res, 4))
for k, v in res["cases"].items():
    print(k, {kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()})
