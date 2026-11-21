"""C_rf step 3 - 2D magneto-quasi-static partial-inductance solver (cross-sections) for the return-path physics.

Why: the two drivers of common-mode current are the voltage drops along the return conductors of a DM circuit
(Hockanson et al., IEEE T-EMC 38(4) 1996, "current-driven" mechanism - public source, not a standard):
  V_cm = j*w * L'_ret * l * I_dm,   L'_ret = A_ret / I   (A = z-directed vector potential of the cross-section current
distribution, referenced to infinity; for a net-zero current set it is unique). L'_ret is the share of the loop flux that
wraps around the return conductor - the part that drives the attached structures against each other.

Model: every conductor (trace, plane, FPC strip) is meshed into thin rectangular filaments over its cross-section with the
current crowded towards the surfaces (high-frequency limit, skin depth << t is mimicked by meshing the perimeter only).
Filament mutual inductance per unit length L_ij = -(mu0/2pi) ln(d_ij), self = -(mu0/2pi) ln(GMD), GMD = 0.2235 (w + t).
Each conductor is an equipotential (equal dV/dz over its filaments); return conductors listed together are shorted at both
ends (equal dV/dz across the group); signal conductors carry their prescribed currents. Saddle-point solve.

Validation (in results): two-wire line vs (mu0/pi) acosh(D/2a); microstrip loop inductance vs Hammerstad/Wheeler (air)
L' = Z0_air / c; microstrip over an increasingly wide plane -> L'_ret -> 0 (the plane wraps all flux).
Outputs: results.json["inductance2d"]
"""
import math
import numpy as np
from c0_common import *


def mesh_rect(xc, yc, w, t, nw, nt=2, shell=True):
    """Filaments of a rectangular conductor; with shell=True only the perimeter row/columns (HF current crowding)."""
    xs = xc - w / 2 + (np.arange(nw) + 0.5) * w / nw
    ys = yc - t / 2 + (np.arange(nt) + 0.5) * t / nt
    fw, ft = w / nw, t / nt
    pts = [(x, y) for x in xs for y in ys]
    if shell and nt > 2:
        pts = [(x, y) for x in xs for y in ys if (y == ys[0] or y == ys[-1] or x == xs[0] or x == xs[-1])]
    return np.array(pts), 0.2235 * (fw + ft)


class XS:
    """A cross-section: list of conductors, each (name, filaments(N,2), gmd)."""

    def __init__(self):
        self.cond = []

    def add(self, name, pts, gmd):
        self.cond.append((name, np.asarray(pts, float), gmd))

    def solve(self, currents, returns):
        """currents: {name: I} for driven signal conductors; returns: list of names forming one shorted return group
        (total return current = -sum(currents)). Conductors in neither set are floating (net current 0, equipotential).
        Returns dict: filament currents, conductor dV/dz (= A, V*s/m per A of jw), loop L', L'_ret, dipole moment."""
        P = np.vstack([c[1] for c in self.cond])
        gmd = np.concatenate([np.full(len(c[1]), c[2]) for c in self.cond])
        owner = np.concatenate([np.full(len(c[1]), k) for k, c in enumerate(self.cond)])
        N = len(P)
        d = np.hypot(P[:, None, 0] - P[None, :, 0], P[:, None, 1] - P[None, :, 1])
        np.fill_diagonal(d, 1.0)
        L = -MU0 / (2 * math.pi) * np.log(d)
        np.fill_diagonal(L, -MU0 / (2 * math.pi) * np.log(gmd))
        names = [c[0] for c in self.cond]
        # unknowns: filament currents (N) + one potential per "group" (each driven conductor its own, the return group one,
        # each floating conductor its own)
        groups = []
        for k, n in enumerate(names):
            if n in currents:
                groups.append(("sig", [k], currents[n]))
            elif n not in returns:
                groups.append(("float", [k], 0.0))
        groups.append(("ret", [names.index(r) for r in returns], -sum(currents.values())))
        G = len(groups)
        A = np.zeros((N + G, N + G))
        b = np.zeros(N + G)
        A[:N, :N] = L
        for g, (kind, ks, Itot) in enumerate(groups):
            m = np.isin(owner, ks)
            A[:N, N + g][m] = -1.0
            A[N + g, :N][m] = 1.0
            b[N + g] = Itot
        sol = np.linalg.solve(A, b)
        I = sol[:N]
        V = {}
        for g, (kind, ks, Itot) in enumerate(groups):
            for k in ks:
                V[names[k]] = sol[N + g]
        Itot_sig = sum(abs(v) for v in currents.values())
        mom = np.array([np.sum(I * P[:, 0]), np.sum(I * P[:, 1])])
        return {"I": I, "P": P, "owner": owner, "V": V, "names": names, "moment": mom, "Isig": Itot_sig}


def microstrip_xs(w, t, h, Wp, tp=35e-6, x_off=0.0, ns=8, npl=400, pl_span=None):
    xs = XS()
    p, g = mesh_rect(x_off, h + t / 2, w, t, ns, 2)
    xs.add("sig", p, g)
    p, g = mesh_rect(0.0, -tp / 2, Wp, tp, npl, 2)
    xs.add("plane", p, g)
    return xs


def hammerstad_air(w, h, t=0.0):
    """Z0 of a microstrip in air (er = 1), Hammerstad-Jensen with Wheeler's thickness correction."""
    if t > 0:
        w = w + t / math.pi * (1 + math.log(4 * math.e / math.sqrt((t / h) ** 2 + (1 / math.pi / (w / t + 1.1)) ** 2)))
    u = w / h
    f = 6 + (2 * math.pi - 6) * math.exp(-(30.666 / u) ** 0.7528)
    return 60 * math.log(f / u + math.sqrt(1 + (2 / u) ** 2))


def hammerstad(w, h, er, t=0.0):
    z_air = hammerstad_air(w, h, t)
    u = w / h
    a = 1 + 1 / 49 * math.log((u ** 4 + (u / 52) ** 2) / (u ** 4 + 0.432)) + 1 / 18.7 * math.log(1 + (u / 18.1) ** 3)
    bb = 0.564 * ((er - 0.9) / (er + 3)) ** 0.053
    eeff = (er + 1) / 2 + (er - 1) / 2 * (1 + 10 / u) ** (-a * bb)
    return z_air / math.sqrt(eeff), eeff


if __name__ == "__main__":
    out = {"method": __doc__.split("\n")[0], "validation": {}}
    # ---- validation 1: two-wire line, a = 0.25 mm, D = 2, 5, 10 mm (round wires meshed as 32 surface filaments)
    v1 = []
    for D in (2e-3, 5e-3, 10e-3):
        a = 0.25e-3
        xs = XS()
        ang = np.linspace(0, 2 * np.pi, 32, endpoint=False)
        seg = 2 * math.pi * a / 32
        for nm, x in (("s", -D / 2), ("r", D / 2)):
            xs.add(nm, np.c_[x + a * np.cos(ang), a * np.sin(ang)], 0.2235 * seg)
        s = xs.solve({"s": 1.0}, ["r"])
        Lnum = s["V"]["s"] - s["V"]["r"]
        Lth = MU0 / math.pi * math.acosh(D / (2 * a))
        v1.append({"D_mm": D * 1e3, "L_num_nH_per_mm": Lnum * 1e6, "L_theory_nH_per_mm": Lth * 1e6, "err_pct": 100 * (Lnum / Lth - 1)})
    out["validation"]["two_wire"] = rnd(v1, 4)
    # ---- validation 2: microstrip w=0.25, t=35 um, h=0.2 mm over a 60 mm plane: loop L' vs Z0_air/c
    w, t, h = 0.25e-3, 35e-6, 0.2e-3
    xs = microstrip_xs(w, t, h, 60e-3, npl=1200)
    s = xs.solve({"sig": 1.0}, ["plane"])
    Lloop = s["V"]["sig"] - s["V"]["plane"]
    z_air = hammerstad_air(w * 1e3, h * 1e3, t * 1e3)
    Lth = z_air / C0
    z0, eeff = hammerstad(0.25, 0.2, 4.4, 0.035)
    out["validation"]["microstrip_loop"] = rnd({"L_num_nH_per_mm": Lloop * 1e6, "L_from_Z0air_nH_per_mm": Lth * 1e6, "err_pct": 100 * (Lloop / Lth - 1),
                                                "Z0_er4.4_ohm": z0, "eeff": eeff, "Z0_air_ohm": z_air}, 4)
    # ---- the board: microstrip L'_ret vs plane width (convergence) and for the real ribbon geometry
    conv = []
    for Wp in (10e-3, 20e-3, 40e-3, 60e-3, 100e-3):
        xs = microstrip_xs(w, t, h, Wp, npl=int(Wp / 0.05e-3))
        s = xs.solve({"sig": 1.0}, ["plane"])
        conv.append({"plane_width_mm": Wp * 1e3, "L_ret_pH_per_mm": abs(s["V"]["plane"]) * 1e9, "L_loop_nH_per_mm": (s["V"]["sig"] - s["V"]["plane"]) * 1e6,
                     "h_eff_mm": abs(s["moment"][1]) * 1e3})
    out["microstrip_Lret_vs_plane_width"] = rnd(conv, 4)
    # ribbon of 28 lines at 0.5 mm pitch over a 62 mm wide In1 strip (corridor y 56..118), ribbon 25 mm from one plane edge
    Wp = 62e-3
    xs = XS()
    for k in range(28):
        p, g = mesh_rect(-Wp / 2 + 25e-3 + k * 0.5e-3, h + t / 2, w, t, 6, 2)
        xs.add("s%d" % k, p, g)
    p, g = mesh_rect(0, -17.5e-6, Wp, 35e-6, 1500, 2)
    xs.add("plane", p, g)
    s_all = xs.solve({"s%d" % k: 1.0 for k in range(28)}, ["plane"])
    s_one = xs.solve({"s0": 1.0}, ["plane"])
    out["board_ribbon"] = rnd({"L_ret_pH_per_mm_per_A_of_each_line_all28_in_phase": abs(s_all["V"]["plane"]) * 1e9 / 1.0,
                               "note": "V_plane per unit length for 28 A total (1 A per line): divide by 28 for per-ampere-of-total",
                               "L_ret_pH_per_mm_per_A_total": abs(s_all["V"]["plane"]) * 1e9 / 28,
                               "L_ret_pH_per_mm_single_line": abs(s_one["V"]["plane"]) * 1e9,
                               "h_eff_mm_all": abs(s_all["moment"][1]) / 28 * 1e3, "h_eff_mm_single": abs(s_one["moment"][1]) * 1e3}, 4)
    # ---- the TFT FPC: 40 strips, 0.5 mm pitch, w 0.25 mm, t 18 um (assumed), panel pinout (SAT070AT40D21 datasheet p.5):
    # 1 VLED-, 2 VLED+, 3 GND, 4 VDD, 5-12 R0-7, 13-20 G0-7, 21-28 B0-7, 29 GND, 30 PCLK, 31 NC, 32 HSYNC, 33 VSYNC, 34 DE,
    # 35 NC, 36 GND, 37-40 touch (unused). Returns: GND 3/29/36 + VDD 4 (decoupled at both ends); VLED as a sensitivity.
    def fpc(return_pins, active, cur=1.0, height_over_metal=None):
        xs = XS()
        for pin in range(1, 41):
            p, g = mesh_rect((pin - 20.5) * 0.5e-3, 0.0, 0.25e-3, 18e-6, 5, 2)
            xs.add("p%d" % pin, p, g)
        if height_over_metal:          # a large metal plane under the tail (panel back / PCB plane) as a floating conductor
            p, g = mesh_rect(0, -height_over_metal, 60e-3, 35e-6, 600, 2)
            xs.add("metal", p, g)
        return xs.solve({"p%d" % a: cur for a in active}, ["p%d" % r for r in return_pins])
    data = list(range(5, 29))
    cases = {}
    for nm, ret, act in (("all 24 data in phase, returns GND 3/29/36 + VDD 4", [3, 4, 29, 36], data),
                         ("all 24 data in phase, returns GND only", [3, 29, 36], data),
                         ("all 24 data in phase, returns GND + VDD + VLED 1/2", [1, 2, 3, 4, 29, 36], data),
                         ("PCLK (pin 30) alone, returns GND + VDD", [3, 4, 29, 36], [30]),
                         ("G3 (pin 16) alone, returns GND + VDD", [3, 4, 29, 36], [16]),
                         ("B7 (pin 28) alone, returns GND + VDD", [3, 4, 29, 36], [28])):
        s = fpc(ret, act)
        n = len(act)
        Vr = abs(s["V"]["p%d" % ret[0]])
        cases[nm] = {"n_active": n, "L_ret_nH_per_mm_per_A_total": Vr * 1e6 / n,
                     "loop_L_nH_per_mm_per_line": (abs(s["V"]["p%d" % act[0]] - s["V"]["p%d" % ret[0]])) * 1e6,
                     "moment_mm_per_A_total": float(np.hypot(*s["moment"])) * 1e3 / n,
                     "return_share": {("p%d" % r): float(s["I"][s["owner"] == s["names"].index("p%d" % r)].sum() / -n) for r in ret}}
    # with the panel metal 1 mm under the tail (the tail runs along the panel edge / PCB edge for part of its length)
    s = fpc([3, 4, 29, 36], data, height_over_metal=1.0e-3)
    cases["all 24 data in phase, GND+VDD, metal plane 1 mm below (floating)"] = {
        "L_ret_nH_per_mm_per_A_total": abs(s["V"]["p3"]) * 1e6 / 24, "moment_mm_per_A_total": float(np.hypot(*s["moment"])) * 1e3 / 24}
    out["fpc_tft"] = rnd(cases, 4)
    # ---- CTP FPC (6 pins: 1 VDD, 2 GND?, ...) - only I2C (400 kHz) and INT/RST: not an RF source; skipped.
    save_section("inductance2d", out)
    import json
    print(json.dumps(rnd(out, 4), indent=1)[:5000])
