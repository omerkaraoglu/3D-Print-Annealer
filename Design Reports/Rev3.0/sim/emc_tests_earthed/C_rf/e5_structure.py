"""Earthed-oven study - thin-wire MoM model of the controller INSIDE an earthed steel oven body, and the bonding concepts.

Geometry (metres, same frame as ../../emc_tests/C_rf/c5_cm_structure.py: origin board centre, y up, z towards the user):
  PCB SELV ground grid (z 0), panel metal grid (z 6.4 mm), TFT FPC return wire with the CM source (delta gap at the U-bottom),
  mains band + HLK barrier 50 pF (no Y1) - all as in c5 (read-only import).
  Oven body (ASSUMED geometry, the owner's statement only says "chassis and sheet metals are earthed"): steel box
  0.40 x 0.40 x 0.40 m, front face = the steel front sheet at z = +12 mm (frame stack: panel back -5.0, glass front -10.3 mm
  relative to the PCB back in the frame document's Z, i.e. the sheet ~6 mm in front of the panel back), wire grid 0.1 m on
  the back/sides, refined on the front around the panel opening: the opening is the panel outline (164.9 x 100 mm).
  Protective earth: 3-core cord leaves the back face at (0.1, -0.1, -0.388) (inlet), PE bonded to the body there; the cord is
  one CM conductor going back 0.1 m then down 0.8 m to the floor/CMAD (EN 55014-1 5.3.4.3.2), then the tapered resistive
  CMAD section. L/N run inside from J3 to the inlet and meet the cord through 100 ohm (L/N-vs-PE line mode, ASSUMED).
  Heater: lead 0.25 m into the body + 0.3 m element along x (open). Fan: lead 0.2 m (open). Thermocouple: J20 -> through the
  CM input impedance of the front end (2 x [TVS 35 pF || (1 kohm + 10 nF)]) -> 0.48 m lead -> probe ring bolted to the bottom
  wall node (-0.1, -0.2, -0.288): grounded junction (galvanic) or insulated junction (20 pF).
Bonding concepts (contacts = short wires; optional lumped contact inductance):
  i   panel frame <-> PCB ground, 6 / 19 points (the c5 lists)
  ii  panel frame <-> front sheet, 12 points (4 top, 4 bottom, 2 left, 2 right) - no PCB-ground connection
  iii PCB ground <-> sheet at the SELV screw ears (1: H6, 4: H5 H6 H7 H8, 9: H1 H5-H9 + 3 bottom-edge contacts) + concept ii
  iv  PCB ground <-> sheet only (same 1 / 4 / 9 points)
  The mains-band ears H2 H3 H4 cannot carry a SELV bond (creepage), hence max 6 ears + 3 edge contacts.
Runs: emission transfer at k x 16.65 MHz (k = 2..60), FAR 3 m (36 az x 3 heights) and SAC 10 m (image, 1-4 m scan); complex
gap impedance stored for the self-consistent post-processing (e6). Optional receive mode (3 V/m plane waves, 10 incidences,
lossy gap load from the v2 issue) at 20 frequencies 80-1000 MHz.
usage: python e5_structure.py <config> [<config> ...]   (each config -> EWORK/<config>.npz)"""
import math, os, sys, time, json
import numpy as np
from e0_common import *
import c5_cm_structure as c5
from c5_cm_structure import P, selv, XG, YG_PCB, YG_PAN, XG_PAN, A_GRID, e_measured, sac10, OBS3
from mom import Wires

BOX = (-0.2, 0.2, -0.2, 0.2, -0.388, 0.012)
INLET = (0.1, -0.1, -0.388)
PANEL_X = (20.02, 184.9)       # abs mm
PANEL_Y = (19.0, 119.0)
EARS = {"H1": (30.0, 14.2), "H5": (189.8, 109.0), "H6": (175.0, 123.8), "H7": (30.0, 123.8), "H8": (15.2, 109.0), "H9": (15.2, 30.0)}
EAR_PCB = {"H1": (26.5, 20.5), "H5": (183.5, 112.0), "H6": (170.0, 118.5), "H7": (26.5, 118.5), "H8": (20.5, 112.0), "H9": (20.5, 35.0)}
EDGE3 = [(85.0, 118.5), (113.5, 118.5), (142.0, 118.5)]
PANEL_SHEET_PTS = [(x, 119.0) for x in (41, 85, 128, 170)] + [(x, 19.0) for x in (41, 85, 128, 170)] + \
                  [(20.02, y) for y in (50, 95)] + [(184.9, y) for y in (50, 95)]


def loc(xa, ya, zm=None):
    p = P(xa, ya, 0.0)
    return (p[0], p[1], zm if zm is not None else 0.0)


def front_sheet(w):
    z = BOX[5]
    xs = {BOX[0], BOX[1], -0.15, 0.15, -0.1, 0.0, 0.1}
    ys = {BOX[2], BOX[3], -0.15, 0.15, -0.1, 0.0, 0.1}
    for xa in PANEL_X + (41, 85, 113.5, 128, 142, 170) + tuple(e[0] for e in EARS.values()):
        xs.add(P(xa, 0)[0])
    for ya in PANEL_Y + (50, 95) + tuple(e[1] for e in EARS.values()):
        ys.add(P(0, ya)[1])
    xs, ys = sorted(xs), sorted(ys)
    xl, xr = sorted((P(PANEL_X[0], 0)[0], P(PANEL_X[1], 0)[0]))
    yb, yt = sorted((P(0, PANEL_Y[1])[1], P(0, PANEL_Y[0])[1]))
    inside = lambda x, y: (xl + 1e-6 < x < xr - 1e-6) and (yb + 1e-6 < y < yt - 1e-6)
    for y in ys:
        for x0, x1 in zip(xs[:-1], xs[1:]):
            if not inside((x0 + x1) / 2, y):
                w.line((x0, y, z), (x1, y, z), 1, 1.5e-3, "sheet")
    for x in xs:
        for y0, y1 in zip(ys[:-1], ys[1:]):
            if not inside(x, (y0 + y1) / 2):
                w.line((x, y0, z), (x, y1, z), 1, 1.5e-3, "sheet")


def box_rest(w):
    g = np.linspace(-0.2, 0.2, 5); gz = np.linspace(BOX[5], BOX[4], 5)
    zb = BOX[4]
    for v in g:                                           # back face
        for a0, a1 in zip(g[:-1], g[1:]):
            w.line((a0, v, zb), (a1, v, zb), 1, 2e-3, "box"); w.line((v, a0, zb), (v, a1, zb), 1, 2e-3, "box")
    for xf in (g[0], g[-1]):                              # left/right faces
        for v in g:
            for z0, z1 in zip(gz[:-1], gz[1:]):
                w.line((xf, v, z0), (xf, v, z1), 1, 2e-3, "box")
        for zv in gz[1:-1]:
            for a0, a1 in zip(g[:-1], g[1:]):
                w.line((xf, a0, zv), (xf, a1, zv), 1, 2e-3, "box")
    for yf in (g[0], g[-1]):                              # top/bottom faces
        for v in g[1:-1]:
            for z0, z1 in zip(gz[:-1], gz[1:]):
                w.line((v, yf, z0), (v, yf, z1), 1, 2e-3, "box")
        for zv in gz[1:-1]:
            for a0, a1 in zip(g[:-1], g[1:]):
                w.line((a0, yf, zv), (a1, yf, zv), 1, 2e-3, "box")


def build(cfg):
    w = Wires(tol=1e-7)
    for ya in YG_PCB:
        for x0, x1 in zip(XG[:-1], XG[1:]):
            if selv(x0, ya) and selv(x1, ya) and selv((x0 + x1) / 2, ya):
                w.line(P(x0, ya), P(x1, ya), 1, A_GRID, "pcb")
    for xa in XG:
        for y0, y1 in zip(YG_PCB[:-1], YG_PCB[1:]):
            if selv(xa, y0) and selv(xa, y1) and selv(xa, (y0 + y1) / 2):
                w.line(P(xa, y0), P(xa, y1), 1, A_GRID, "pcb")
    for ya in YG_PAN:
        for x0, x1 in zip(XG_PAN[:-1], XG_PAN[1:]):
            w.line(P(x0, ya, 6.4), P(x1, ya, 6.4), 1, A_GRID, "panel")
    for xa in XG_PAN:
        for y0, y1 in zip(YG_PAN[:-1], YG_PAN[1:]):
            w.line(P(xa, y0, 6.4), P(xa, y1, 6.4), 1, A_GRID, "panel")
    fpc = [P(155.7, 112, 0), P(155.7, 112, -1.0), P(155.7, 130, -1.0), P(155.7, 147, -1.0), P(155.7, 150, 2.7),
           P(155.7, 147, 6.4), P(155.7, 133, 6.4), P(155.7, 119, 6.4)]
    w.polyline(fpc, 0.009, 1.0e-3, "fpc")
    # mains band + HLK barrier
    band = [P(60, 30), P(70, 28), P(85, 28), P(107, 28), P(125, 28), P(128, 28), P(150, 28), P(166, 28)]
    w.polyline(band, 0.016, 1.0e-3, "mains_band")
    w.polyline([P(125, 28), P(125, 50)], 0.016, 1.0e-3, "mains_band")
    w.polyline([P(166, 28), P(170, 40), P(170, 60)], 0.008, 1.5e-3, "hlk")
    w.hlk_node = P(170, 44.0)
    # earthed body
    front_sheet(w); box_rest(w)
    # cord (3-core, one CM conductor) from the inlet: back 0.1 m, down 0.8 m, CMAD section 0.6 m
    c0 = INLET; c1 = (c0[0], c0[1], c0[2] - 0.1); c2 = (c1[0], c1[1] - 0.8, c1[2]); c3 = (c2[0], c2[1] - 0.6, c2[2])
    w.polyline([c0, c1, c2], 0.04, 2e-3, "mains_cable")
    w.polyline([c2, c3], 0.04, 2e-3, "cmad")
    # L/N inside: J3 -> inlet, with the L/N-vs-PE line-mode impedance as a series load near the inlet
    j3 = P(107, 28, 0)
    w.polyline([j3, (j3[0], j3[1], -0.25), (0.1, -0.1, -0.25), (0.1, -0.1, -0.37), INLET], 0.04, 1.5e-3, "LN_inside")
    w.ln_load_node = (0.1, -0.1, -0.37)
    # heater and fan inside the body
    h0 = P(128, 28, 0); w.polyline([h0, (h0[0], h0[1], -0.25), (h0[0] - 0.15, h0[1], -0.25), (h0[0] - 0.15, h0[1] - 0.2, -0.25)], 0.04, 2e-3, "heater")
    f0 = P(70, 28, 0); w.polyline([f0, (f0[0], f0[1], -0.2)], 0.04, 2e-3, "fan")
    # thermocouple: J20 -> 10 mm -> input-network load -> lead -> probe on the bottom wall
    j = P(26.5, 102.5, 0)
    jq = (j[0], j[1], -0.010)
    w.polyline([j, jq], 0.005, 1.5e-3, "tc_in")
    w.polyline([jq, (j[0], j[1], -0.288), (-0.1, j[1], -0.288), (-0.1, -0.19, -0.288)], 0.04, 2e-3, "tc")
    w.polyline([(-0.1, -0.19, -0.288), (-0.1, -0.2, -0.288)], 0.005, 2e-3, "tc_probe")
    w.tc_in_node = (j[0], j[1], -0.005)
    w.probe_node = (-0.1, -0.195, -0.288)
    # bonding concepts
    nb = 0
    def bond(pa, pb, tag):
        nonlocal nb
        w.polyline([pa, ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2, (pa[2] + pb[2]) / 2), pb], 1.0, 1.0e-3, tag); nb += 1
    for (pp, qq) in cfg.get("panel_pcb", []):
        bond(P(*pp, 0), P(*qq, 6.4), "bond_panel_pcb")
    if cfg.get("panel_sheet"):
        for (xa, ya) in PANEL_SHEET_PTS:
            bond(P(xa, ya, 6.4), P(xa, ya, BOX[5] * 1000), "bond_panel_sheet")
    for ear in cfg.get("pcb_sheet_ears", []):
        bond(P(*EAR_PCB[ear], 0), P(*EARS[ear], BOX[5] * 1000), "bond_pcb_sheet")
    for (xa, ya) in (EDGE3 if cfg.get("pcb_sheet_edge3") else []):
        bond(P(xa, ya, 0), P(xa, 119.0, BOX[5] * 1000), "bond_pcb_sheet")
    w.n_bonds = nb
    w.finalize()
    return w


def zin_tc(f):
    wv = 2 * math.pi * f
    leg = 1 / (1j * wv * 35e-12 + 1 / (1000 + 1 / (1j * wv * 10e-9)))
    return leg / 2


def setup_loads(w, cfg):
    loads = {}
    src = w.basis_at(w.nearest_node(P(155.7, 150, 2.7)))
    if cfg.get("gap_load"):
        loads[src] = cfg["gap_load"]
    b = w.basis_at(w.nearest_node(w.hlk_node))
    loads[b] = lambda f: 1 / (1j * 2 * math.pi * f * 50e-12) + 0.5
    b = w.basis_at(w.nearest_node(w.ln_load_node))
    loads[b] = lambda f: cfg.get("Z_LN_PE", 100.0)
    b = w.basis_at(w.nearest_node(w.tc_in_node))
    loads[b] = zin_tc
    if cfg.get("probe") == "insulated":
        b = w.basis_at(w.nearest_node(w.probe_node))
        loads[b] = lambda f: 1 / (1j * 2 * math.pi * f * 20e-12)
    cm = [i for i, t in enumerate(w.tags) if t == "cmad"]
    for k, s in enumerate(cm[:-1]):
        try:
            bb = w.basis_at(w.S[s][1])
        except KeyError:
            continue
        loads[bb] = (lambda f, R=12.0 * (1 + k) ** 1.3: R)
    Lc = cfg.get("contact_L", 0.0)
    if Lc:
        tags = np.array(w.tags)
        for t in ("bond_panel_pcb", "bond_panel_sheet", "bond_pcb_sheet"):
            segs = np.where(tags == t)[0]
            for s in segs[::2]:                              # each bond = 2 segments; load at its middle node
                try:
                    bb = w.basis_at(w.S[s][1])
                except KeyError:
                    continue
                loads[bb] = (lambda f, L=Lc: 1j * 2 * math.pi * f * L)
    return src, loads


EXC = []
for kd, pols in (((0, 0, -1), ((1, 0, 0), (0, 1, 0))), ((0, 0, 1), ((1, 0, 0), (0, 1, 0))), ((1, 0, 0), ((0, 1, 0), (0, 0, 1))),
                 ((-1, 0, 0), ((0, 1, 0), (0, 0, 1))), ((0, -1, 0), ((1, 0, 0), (0, 0, 1)))):
    for p in pols:
        EXC.append((np.array(kd, float), np.array(p, float)))


def run(name, cfg, f_em, f_rx=None):
    w = build(cfg); src, loads = setup_loads(w, cfg)
    tags = np.array(w.tags)
    cab = [t for t in ("mains_cable", "heater", "fan", "tc", "fpc", "LN_inside", "bond_panel_pcb", "bond_panel_sheet", "bond_pcb_sheet") if (tags == t).any()]
    out = {"f": np.array(f_em), "E3": [], "E10": [], "Igap": [], "cable_max": {t: [] for t in cab}, "nseg": len(w.len), "nb": w.nb, "n_bonds": w.n_bonds}
    t0 = time.time()
    for f in f_em:
        Z = w.Z(f)
        for b, zf in loads.items():
            Z[b, b] += zf(f)
        V = np.zeros(w.nb, complex); V[src] = 1.0
        I = np.linalg.solve(Z, V)
        out["Igap"].append(complex(I[src]))
        out["E3"].append(e_measured(w.fields(I, f, OBS3), OBS3))
        out["E10"].append(sac10(w, I, f))
        c = w.seg_currents(I)
        for t in cab:
            out["cable_max"][t].append(float(np.abs(c[tags == t]).max()))
    if f_rx is not None:
        rx = {"f": np.array(f_rx), "tc_in": [], "fpc": [], "mains": []}
        tcs = np.where(tags == "tc_in")[0]
        for f in f_rx:
            Z = w.Z(f)
            for b, zf in loads.items():
                Z[b, b] += zf(f)
            Vp = np.stack([w.plane_wave_V(f, 3.0, p, k) for k, p in EXC], axis=1)
            I = np.linalg.solve(Z, Vp)
            m = {"tc_in": 0.0, "fpc": 0.0, "mains": 0.0}
            for j_ in range(I.shape[1]):
                c = w.seg_currents(I[:, j_])
                m["tc_in"] = max(m["tc_in"], float(np.abs(c[tcs]).max()))
                m["fpc"] = max(m["fpc"], float(np.abs(c[tags == "fpc"]).max()))
                m["mains"] = max(m["mains"], float(np.abs(c[tags == "mains_cable"]).max()))
            for k_ in m:
                rx[k_].append(m[k_])
        out["rx"] = rx
    print(name, "bonds", w.n_bonds, "nseg", len(w.len), "nb", w.nb, "%.0fs" % (time.time() - t0), flush=True)
    return out


PP6 = c5.CONFIGS["bond_6pt"]["bonds"]
PP19 = c5.CONFIGS["bond_perimeter"]["bonds"]
CONFIGS = {
    "E_none_G": {"probe": "grounded"},
    "E_none_I": {"probe": "insulated"},
    "E_i6": {"probe": "grounded", "panel_pcb": PP6},
    "E_i19": {"probe": "grounded", "panel_pcb": PP19},
    "E_ii": {"probe": "grounded", "panel_sheet": True},
    "E_iii1": {"probe": "grounded", "panel_sheet": True, "pcb_sheet_ears": ["H6"]},
    "E_iii4": {"probe": "grounded", "panel_sheet": True, "pcb_sheet_ears": ["H5", "H6", "H7", "H8"]},
    "E_iii9": {"probe": "grounded", "panel_sheet": True, "pcb_sheet_ears": ["H1", "H5", "H6", "H7", "H8", "H9"], "pcb_sheet_edge3": True},
    "E_iv1": {"probe": "grounded", "pcb_sheet_ears": ["H6"]},
    "E_iv4": {"probe": "grounded", "pcb_sheet_ears": ["H5", "H6", "H7", "H8"]},
    "E_iv9": {"probe": "grounded", "pcb_sheet_ears": ["H1", "H5", "H6", "H7", "H8", "H9"], "pcb_sheet_edge3": True},
    "E_i19_L10": {"probe": "grounded", "panel_pcb": PP19, "contact_L": 10e-9},
    "E_ii_L10": {"probe": "grounded", "panel_sheet": True, "contact_L": 10e-9},
    "E_iii9_L10": {"probe": "grounded", "panel_sheet": True, "pcb_sheet_ears": ["H1", "H5", "H6", "H7", "H8", "H9"], "pcb_sheet_edge3": True, "contact_L": 10e-9},
}
RX = {"E_none_G", "E_none_I", "E_i19", "E_ii", "E_iii9", "E_iv9"}
F_EM = np.array([k * 16.65e6 for k in range(2, 61)])
F_RX = np.geomspace(80e6, 1000e6, 20)

if __name__ == "__main__":
    # receive mode needs the v2 lossy gap load (R_loss Q10 + reflected driver impedance with RN 150 ohm), from the old results
    O = old()
    RL = O["emission"]["mode"]["R_loss_added_ohm"]["10.0"]
    Md, Mp = O["emission"]["M_nH"]["data_in_phase"] * 1e-9, O["emission"]["M_nH"]["pclk"] * 1e-9
    Y = O["spice_chain"]["Ydist"]
    def _y(k, m=1.0):
        d = Y[k]; return np.array(d["f_MHz"]) * 1e6, (np.maximum(np.array(d["re"]), 0) + 1j * np.array(d["im"])) * m
    fyd, yd = _y("data_in_phase_Rs150", 24); fyp, yp = _y("pclk_Rs150")
    zref = lambda f: (2 * math.pi * f) ** 2 * (Md ** 2 * (np.interp(f, fyd, yd.real) + 1j * np.interp(f, fyd, yd.imag)) +
                                               Mp ** 2 * (np.interp(f, fyp, yp.real) + 1j * np.interp(f, fyp, yp.imag)))
    for name in sys.argv[1:]:
        cfg = dict(CONFIGS[name])
        o = run(name, cfg, F_EM)
        if name in RX:
            cfg_rx = dict(cfg, gap_load=lambda f: RL + zref(f))
            o["rx"] = run(name + " (rx)", cfg_rx, [], F_RX)["rx"]
        np.savez(os.path.join(EWORK, name + ".npz"), d=np.array(o, dtype=object))
