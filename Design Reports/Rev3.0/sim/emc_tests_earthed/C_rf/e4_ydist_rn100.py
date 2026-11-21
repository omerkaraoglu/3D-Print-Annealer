"""Earthed-oven study - passive distributed-EMF admittance Y_dist of the RGB/PCLK DM circuits for RN1-RN7 = 100 ohm (the fitted
value, decided 2026-11-21), computed exactly like ../../emc_tests/C_rf/c4c_ydist.py (whose source is executed read-only).
Output: results.json["Ydist_Rs100"]"""
import json, math
import numpy as np
from e0_common import *

src = open(os.path.join(OLD, "c4c_ydist.py"), encoding="utf-8").read()
head = src.split("out = {}")[0]
ns = {"__file__": os.path.join(OLD, "c4c_ydist.py")}
cwd = os.getcwd(); os.chdir(OLD)
try:
    exec(head, ns)
finally:
    os.chdir(cwd)
ydist, L12 = ns["ydist"], ns["L12"]
out = {}
Zb, ps, Zf = ns["Z_EVEN"], ns["PS_MM"](ns["ER_PP"]), ns["L_FPC_EVEN"] * ns["V_FPC"]
ys = [ydist(*L12(nm), Zb, ps, Zf, 100.0)[1] for nm in ("B7", "G3", "R0")]
f = ydist(*L12("B7"), Zb, ps, Zf, 100.0)[0]
y = np.mean(ys, axis=0)
out["data_in_phase_Rs100"] = {"f_MHz": (f / 1e6).tolist(), "re": y.real.tolist(), "im": y.imag.tolist()}
f, y = ydist(*L12("PCLK"), ns["Z_ISO"], ns["PS_MM"](ns["EEFF_ISO"]), ns["L_FPC_ISO"] * ns["V_FPC"], 100.0)
out["pclk_Rs100"] = {"f_MHz": (f / 1e6).tolist(), "re": y.real.tolist(), "im": y.imag.tolist()}
save_section("Ydist_Rs100", out)
print({k: float(np.min(v["re"])) for k, v in out.items()})
