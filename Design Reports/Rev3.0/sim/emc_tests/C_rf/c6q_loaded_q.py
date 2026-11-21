"""C_rf (v2) - loaded Q of the panel/PCB mode: Q_L = w0 X'(w0) / (2 (R_struct + R_loss + Re Z_refl(w0))) -> results.json["emission"]["mode"]"""
import numpy as np
from c0_common import *
src = open(os.path.join(HERE, "c6_emission.py"), encoding="utf-8").read().split("res = {")[0]
exec(src)
zr = Zrefl(fdn[i0])
QL = {str(Q): float(w0 * dXdw / (2 * (Rrad + Rloss[Q] + zr.real))) for Q in QBAND}
e = load_results()["emission"]
e["mode"]["Z_reflected_driver_at_f0_ohm"] = [round(float(zr.real), 3), round(float(zr.imag), 3)]
e["mode"]["Q_loaded_(unloaded 30/10/3)"] = {k: round(v, 2) for k, v in QL.items()}
save_section("emission", e)
print(zr, QL)
