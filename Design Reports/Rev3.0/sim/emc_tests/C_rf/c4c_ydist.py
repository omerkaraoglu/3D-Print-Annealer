"""C_rf step 4c (v2, review) - admittance of the RGB/PCLK DM circuits to the back-EMF the CM current induces along the FPC.

The CM current I_cm in the FPC returns induces j w L'_ret I_cm per unit length in every signal loop (reciprocal to the forward
coupling V_cm = j w L'_ret * moment). The reflected impedance in the CM loop is therefore w^2 M^2 Y_dist, where Y_dist is the
FPC-averaged DM current per volt of EMF distributed UNIFORMLY along the FPC - not I_fpc/V_oc of the driver (which turns
negative-real above the in-phase FPC resonance and gave a non-physical negative reflected resistance in the first v2 pass).
Y_dist is a passive self-admittance: Re(Y_dist) >= 0 is checked.
AC analysis of the c4 chain (LC ladders, lengths from the layout): driver = R_out to ground, 4 FPC sections each with a
series EMF of 0.25 V; average of the 5 FPC section currents. Cases: in-phase data line (B7 and G3 lengths, FPC in-phase mode)
and PCLK (isolated mode), RN 33 and 150 ohm.
Outputs: results.json["spice_chain"]["Ydist"]"""
import json, math
import numpy as np
from c0_common import *
src = open(os.path.join(HERE, "c4_spice_chain.py"), encoding="utf-8").read().split('out = {"assumptions"')[0]
exec(src)
_G = json.load(open(GEOM)); LEN = {}
for _t in _G["tracks"]:
    LEN[_t["net"]] = LEN.get(_t["net"], 0.0) + _t["len"]
L12 = lambda nm: (LEN["/Display/%s_T" % nm], LEN["/Display/%s" % nm])


def ydist(L1, L2, Zb, ps, Zf, Rs, Rout=30, Cin=5):
    n = chain_netlist(L1, L2, 1 / PCLK, 0.5, 1.5e-9, Rout, Zb, ps, Zf, Cin, Rs=Rs)
    lines = []
    for ln in n.splitlines():
        if ln.startswith("V1 "):
            ln = "V1 drv 0 DC 0"
        elif ln.startswith("Vpc") and ln.split()[0] in ("Vpc0", "Vpc1", "Vpc2", "Vpc3"):
            p = ln.split()
            ln = f"{p[0]} {p[1]} {p[2]} DC 0 AC 0.25"
        elif ln.startswith(".tran"):
            ln = ".ac dec 60 10Meg 1.5G"
        lines.append(ln)
    v = ng.run_netlist("\n".join(lines) + "\n")
    f = np.real(v["frequency"])
    I = np.array([v[f"vpc{i}#branch"] for i in range(5)])
    Iavg = np.trapezoid(I, axis=0) / 4
    return f, -Iavg


out = {}
for tag, (Zb, ps, Zf) in {"data_in_phase": (Z_EVEN, PS_MM(ER_PP), L_FPC_EVEN * V_FPC), "pclk": (Z_ISO, PS_MM(EEFF_ISO), L_FPC_ISO * V_FPC)}.items():
    for Rs in (33.0, 150.0):
        if tag == "data_in_phase":
            ys = [ydist(*L12(nm), Zb, ps, Zf, Rs)[1] for nm in ("B7", "G3", "R0")]
            f = ydist(*L12("B7"), Zb, ps, Zf, Rs)[0]
            y = np.mean(ys, axis=0)
        else:
            f, y = ydist(*L12("PCLK"), Zb, ps, Zf, Rs)
        out[f"{tag}_Rs{int(Rs)}"] = {"f_MHz": (f / 1e6).round(4).tolist(), "re": y.real.tolist(), "im": y.imag.tolist(),
                                     "min_re": float(y.real.min())}
        print(tag, Rs, "min Re(Y) %.4g S" % y.real.min(), "|Y| at 166.5 MHz %.4g" % abs(np.interp(166.5e6, f, y.real) + 1j * np.interp(166.5e6, f, y.imag)))
SCd = load_results()["spice_chain"]
SCd["Ydist"] = out
save_section("spice_chain", SCd)
