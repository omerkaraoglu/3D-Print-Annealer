"""Earthed-oven study - RF field immunity 80-1000 MHz, 3 V/m rms, 1 kHz 80 % AM (EN 55014-2 5.5 Table 11, PDF p.20; set-up of
IEC 61000-4-3 NOT READ): induced currents from the e5 receive-mode runs (10 plane-wave incidences, lossy FPC gap with the
driver loading, earthed body, probe grounded / insulated, bonding concepts i-19, ii, iii-9, iv-9).
Thermocouple: CM current at J20 -> ADC pins with the per-ampere transfer of ../../emc_tests/C_rf (tc_transfer.json, worst
tolerance corner), rectification bound EMIRR 20 dB / realistic 50 dB (as before). Display inputs: V = w L'_ret,line l I_FPC
(peak with AM) vs the ~0.99 V logic margin (panel VIL 0.3 VDD, datasheet p.6).
Outputs: results.json["radiated_immunity_earthed"]"""
import json, math, glob
import numpy as np
from e0_common import *

O = old()
tr = json.load(open(os.path.join(WORK, "tc_transfer.json")))["corner1"]
Lline = O["inductance2d"]["fpc_tft"]["G3 (pin 16) alone, returns GND + VDD"]["L_ret_nH_per_mm_per_A_total"] * 1e-6
PK = math.sqrt(2) * 1.8
res = {"model": __doc__.split("\n")[0], "cases": {}}
for fn in sorted(glob.glob(os.path.join(EWORK, "E_*.npz"))):
    d = np.load(fn, allow_pickle=True)["d"].item()
    if "rx" not in d:
        continue
    rx = d["rx"]; f = np.array(rx["f"])
    It = np.array(rx["tc_in"]) * PK
    vdm = np.interp(f / 1e6, tr["f_MHz"], tr["Vdm_per_A"]) * It
    vcm = np.interp(f / 1e6, tr["f_MHz"], tr["Vcm_per_A"]) * It
    vj = np.interp(f / 1e6, tr["f_MHz"], tr["VJ_per_A"]) * It
    dTw = (vdm ** 2 + vcm ** 2) / (0.1 * 10) * 1.32 / 41e-6
    dTr = (vdm ** 2 + 0.1 * vcm ** 2) / (0.1 * 10 ** 2.5) * 1.32 / 41e-6
    vpan = 2 * np.pi * f * Lline * 0.08765 * np.array(rx["fpc"]) * PK
    i = int(np.argmax(vpan))
    res["cases"][os.path.basename(fn)[:-4]] = {"I_tc_in_mA_rms_max": float(np.max(rx["tc_in"]) * 1e3), "I_fpc_mA_rms_max": float(np.max(rx["fpc"]) * 1e3),
                                              "I_mains_cord_mA_rms_max": float(np.max(rx["mains"]) * 1e3),
                                              "TC_dT_bound_degC": float(dTw.max()), "TC_dT_realistic_degC": float(dTr.max()), "VJ20_Vpk_max": float(vj.max()),
                                              "display_input_Vpk_max": float(vpan[i]), "at_MHz": float(f[i] / 1e6),
                                              "display_margin_dB_vs_0.99V": float(20 * np.log10(0.99 / vpan[i]))}
save_section("radiated_immunity_earthed", rnd(res, 4))
for k, v in res["cases"].items():
    print(k, {kk: round(vv, 4) for kk, vv in v.items()})
