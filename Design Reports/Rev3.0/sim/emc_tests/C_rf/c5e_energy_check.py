"""C_rf (v2, review) - energy check of the MoM structure itself: radiated power from a far-field sphere integral vs the power
delivered at the FPC gap (P_in = 0.5 Re(V I*)), and the directivity implied by the 3 m maximum field the emission model uses.
Results -> results.json["mom_energy_check"]. Fields are phasor PEAK values; the 3 m field is converted to rms for D."""
import math, numpy as np
from c0_common import *
import c5_cm_structure as c5

out = {}
for cfg_name in ("nominal",):
    cfg = c5.CONFIGS[cfg_name]
    w = c5.build(cfg); src, loads = c5.setup_loads(w, cfg)
    for f in (166.5e6, 183.15e6, 233.1e6, 382.95e6):
        Z = w.Z(f)
        for b, zf in loads.items():
            Z[b, b] += zf(f)
        V = np.zeros(w.nb, complex); V[src] = 1.0
        I = np.linalg.solve(Z, V)
        Pin = 0.5 * float(np.real(V[src] * np.conj(I[src])))
        # loads that dissipate (CMAD resistors, HLK 0.5 ohm): 0.5 |I_b|^2 Re(Z_load)
        Ploads = sum(0.5 * abs(I[b]) ** 2 * float(np.real(zf(f))) for b, zf in loads.items())
        r = 60.0
        th = np.linspace(0, np.pi, 37)[1:-1]; ph = np.linspace(0, 2 * np.pi, 72, endpoint=False)
        T, Ph = np.meshgrid(th, ph, indexing="ij")
        pts = np.stack([r * np.sin(T) * np.cos(Ph), r * np.cos(T), r * np.sin(T) * np.sin(Ph)], -1).reshape(-1, 3)
        E = w.fields(I, f, pts)
        Rh = pts / r
        Et = E - (E * Rh).sum(1)[:, None] * Rh                      # transverse part
        S = (np.abs(Et) ** 2).sum(1) / (2 * ETA0)
        dA = r ** 2 * np.sin(T).reshape(-1) * (th[1] - th[0]) * (ph[1] - ph[0])
        Prad = float((S * dA).sum())
        E3 = c5.e_measured(w.fields(I, f, c5.OBS3), c5.OBS3) / math.sqrt(2)     # rms
        D_impl = (E3 * 3.0) ** 2 / (30 * Prad)
        out[f"{cfg_name} {f/1e6:.2f} MHz"] = {"P_in_W_per_V2": Pin, "P_loads_W_per_V2": Ploads, "P_rad_sphere_W_per_V2": Prad,
                                               "P_rad/(P_in-P_loads)": Prad / max(Pin - Ploads, 1e-30), "max_E3m_rms_per_V": E3,
                                               "directivity_implied_by_3m_max_dBi": 10 * math.log10(D_impl)}
        print(f / 1e6, out[f"{cfg_name} {f/1e6:.2f} MHz"], flush=True)
save_section("mom_energy_check", rnd(out, 6))
