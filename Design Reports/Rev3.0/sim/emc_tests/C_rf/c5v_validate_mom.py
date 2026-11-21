"""C_rf - validation of the thin-wire MoM (mom.py) against known cases, stored in results.json["mom_validation"].
1) half-wave dipole, L = 0.5 m, a = 1 mm (L/a = 500) at 300 MHz: King/NEC reference Zin ~ 82-85 + j44-46 ohm
   (thin-dipole theory 73 + j42.5 in the zero-radius limit; Omega = 2 ln(2L/a) = 13.8) - convergence with 20/40/80 segments
2) short dipole 0.1 m at 30 MHz: far/near field at 3 m broadside vs the Hertzian dipole with triangular current
3) image theory: vertical short dipole 1 m over a PEC plane, field at 10 m on the plane vs 2x free space (low elevation)."""
import math, numpy as np
from c0_common import *
from mom import Wires

out = {}
rows = []
for nseg in (20, 40, 80):
    w = Wires(); w.line((0, -0.25, 0), (0, 0.25, 0), nseg, 1e-3); w.finalize()
    b = w.basis_at(w.nearest_node((0, 0, 0)))
    Z = w.Z(300e6); V = np.zeros(w.nb, complex); V[b] = 1
    I = np.linalg.solve(Z, V)
    zin = 1 / I[b]
    rows.append({"segments": nseg, "Zin_re": float(zin.real), "Zin_im": float(zin.imag)})
out["half_wave_dipole_300MHz"] = rnd(rows, 2)
w = Wires(); w.line((0, -0.05, 0), (0, 0.05, 0), 10, 0.5e-3); w.finalize()
b = w.basis_at(w.nearest_node((0, 0, 0))); f = 30e6
Z = w.Z(f); V = np.zeros(w.nb, complex); V[b] = 1; I = np.linalg.solve(Z, V)
E = w.fields(I, f, np.array([[3.0, 0, 0]]))
k = 2 * math.pi * f / C0; p = I[b] * 0.1 / 2
Eth = abs(1j * ETA0 * k * p / (4 * math.pi * 3.0) * np.sqrt((1 - 1 / (k * 3) ** 2) ** 2 + (1 / (k * 3)) ** 2))
out["short_dipole_30MHz_3m_dB_vs_hertzian"] = round(float(20 * np.log10(abs(E[0, 1]) / Eth)), 2)
Eimg = w.fields(I, f, np.array([[10.0, -1.0, 0]]), image_z=-1.0)
Efs = w.fields(I, f, np.array([[10.0, -1.0, 0]]))
out["image_vertical_dipole_on_plane_ratio_dB"] = round(float(20 * np.log10(abs(Eimg[0, 1]) / abs(Efs[0, 1]))), 2)
out["image_expected_dB"] = 6.02
save_section("mom_validation", out)
print(out)
