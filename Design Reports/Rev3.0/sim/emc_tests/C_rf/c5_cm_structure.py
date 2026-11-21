"""C_rf step 5 - the EUT as an antenna: thin-wire MoM model of PCB ground + panel metal + FPC + attached conductors.

Geometry (metres; origin at the board centre abs (102, 69.5) mm; x right, y UP (= -KiCad y), z towards the user):
  - PCB SELV ground (In1 + pours): wire grid over the region where In1 copper exists (c2 raster), z = 0
  - panel metal back (SAT070AT40D21 LCM, 164.9 x 100 mm, abs x 20..185, y 19..119), z = +6.4 mm
    (B.Cu at +1.36 mm, 5 mm frame spacer, spec 12.8 round 3); ASSUMED connected to the panel ground
  - TFT FPC return (3 GND + VDD strips) as one wire J10 -> down 35 mm on the component side -> U-turn -> up to the panel
    bottom edge (spec 12.9: 67.65 mm tail, U-loop ~28 mm below the edge); the CM source is a delta gap in this wire
  - mains-side copper (L/N/heater/fan network, one CM conductor since X-caps tie L and N) as a wire along the mains band,
    tied to SELV ground only through the HLK-10M05 barrier capacitance C_iso (ASSUMED 47 pF, swept 20..100 pF; Hi-Link does
    not publish it) at PS1, plus the geometric stray capacitance the MoM sees
  - attached conductors: mains cable (J3: 0.3 m inside the appliance, then vertically down 0.8 m to the floor/CMAD per
    EN 55014-1 5.3.4.3.2 PDF p.47, then a tapered resistive section emulating the CMAD), heater leads (R1 pads) 0.6 m,
    fan leads (J4) 0.4 m, thermocouple lead (J20) 1.0 m - internal leads run into the oven (-z), lengths ASSUMED and swept.
  - NOT modelled: the oven's steel front sheet and body (floating, class II), the HS1 heatsink, dielectric, the CTP FPC.
Outputs (transfer functions per 1 V source): E_max at 3 m (FAR, free space) and on a 10 m SAC with height scan,
CM current at each cable root and its maximum along the cable -> work folder npz + results.json["cm_structure"].
"""
import json, math, time, sys
import numpy as np
from PIL import Image, ImageDraw
from c0_common import *
from mom import Wires

ORG = (102.0, 69.5)


def P(xa, ya, zmm=0.0):
    return ((xa - ORG[0]) / 1000.0, -(ya - ORG[1]) / 1000.0, zmm / 1000.0)


# --- SELV region mask from the In1 fill ------------------------------------------------------------------------
G = json.load(open(GEOM))
In1 = [z for z in G["zones"] if z["name"] == "GND plane"][0]["fills"]["In1.Cu"]
RES = 0.25
img = Image.new("1", (int(200 / RES), int(140 / RES)), 0)
d = ImageDraw.Draw(img)
for p in In1:
    d.polygon([(x / RES, y / RES) for x, y in p["outline"]], fill=1)
mask = np.array(img, bool)


def selv(xa, ya):
    # treat a point as on the plane if In1 copper exists within 2 mm (anti-pads ignored)
    i, j = int(ya / RES), int(xa / RES)
    r = int(2 / RES)
    return mask[max(0, i - r):i + r + 1, max(0, j - r):j + r + 1].any()


XG = [20.5, 26.5, 41, 56, 70, 85, 100, 113.5, 128, 142, 155.7, 170, 183.5]
YG_PCB = [20.5, 35, 50, 60, 68, 76, 90, 102.5, 112, 118.5]
YG_PAN = [19, 35, 50, 65, 80, 95, 108, 119]
XG_PAN = [20.02, 26.5, 41, 56, 70, 85, 100, 113.5, 128, 142, 155.7, 170, 184.9]
A_GRID = 1.5e-3


def build(cfg):
    w = Wires(tol=1e-7)
    segl = 0.016
    # PCB grid (SELV only)
    for ya in YG_PCB:
        for x0, x1 in zip(XG[:-1], XG[1:]):
            if selv(x0, ya) and selv(x1, ya) and selv((x0 + x1) / 2, ya):
                w.line(P(x0, ya), P(x1, ya), 1, A_GRID, "pcb")
    for xa in XG:
        for y0, y1 in zip(YG_PCB[:-1], YG_PCB[1:]):
            if selv(xa, y0) and selv(xa, y1) and selv(xa, (y0 + y1) / 2):
                w.line(P(xa, y0), P(xa, y1), 1, A_GRID, "pcb")
    if cfg.get("panel", True):
        for ya in YG_PAN:
            for x0, x1 in zip(XG_PAN[:-1], XG_PAN[1:]):
                w.line(P(x0, ya, 6.4), P(x1, ya, 6.4), 1, A_GRID, "panel")
        for xa in XG_PAN:
            for y0, y1 in zip(YG_PAN[:-1], YG_PAN[1:]):
                w.line(P(xa, y0, 6.4), P(xa, y1, 6.4), 1, A_GRID, "panel")
        # FPC return: J10 (155.7, 112) on the PCB grid -> down to y 147 at z -1 -> U-turn -> up to the panel edge (155.7, 119, 6.4)
        fpc = [P(155.7, 112, 0), P(155.7, 112, -1.0), P(155.7, 130, -1.0), P(155.7, 147, -1.0), P(155.7, 150, 2.7),
               P(155.7, 147, 6.4), P(155.7, 133, 6.4), P(155.7, 119, 6.4)]
        if cfg.get("frame_floating"):
            # panel GND = the panel's source-driver PCB strip (x 20..185, y 112..119) at z 3.2 mm, NOT connected to the metal
            # frame grid (z 6.4 mm), which floats; indicative geometry (thin-wire spacing 3.2 mm, radius 0.5 mm)
            for ya in (112.0, 119.0):
                for x0, x1 in zip(XG_PAN[:-1], XG_PAN[1:]):
                    w.line(P(x0, ya, 3.2), P(x1, ya, 3.2), 1, 0.5e-3, "panel_gnd")
            for xa in XG_PAN:
                w.line(P(xa, 112.0, 3.2), P(xa, 119.0, 3.2), 1, 0.5e-3, "panel_gnd")
            fpc = fpc[:5] + [P(155.7, 147, 3.2), P(155.7, 133, 3.2), P(155.7, 119, 3.2)]
        w.polyline(fpc, 0.009, 1.0e-3, "fpc")
        have = np.array(w.nodes)
        def exists(p_):
            return np.min(np.linalg.norm(have - np.array(p_), axis=1)) < 1e-6
        nb_ok = 0
        for (xp, yp), (xq, yq) in cfg.get("bonds", []):   # proposal: panel frame bonded to PCB ground (spring/strap); PCB grid node -> panel grid node
            if exists(P(xp, yp, 0)) and exists(P(xq, yq, 6.4)):
                w.polyline([P(xp, yp, 0), P(xq, yq, 6.4)], 0.01, 1.0e-3, "bond"); nb_ok += 1
        w.n_bonds = nb_ok
    # mains-side conductor network (one CM wire) + HLK barrier
    if cfg.get("mains", True):
        band = [P(60, 30), P(70, 28), P(85, 28), P(107, 28), P(125, 28), P(128, 28), P(150, 28), P(166, 28)]
        w.polyline(band, segl, 1.0e-3, "mains_band")
        w.polyline([P(125, 28), P(125, 50)], segl, 1.0e-3, "mains_band")       # triac branch
        hl = w.polyline([P(166, 28), P(170, 40), P(170, 60)], 0.008, 1.5e-3, "hlk")
        w.hlk_node = P(170, 44.0)
        # cables
        def cable(root, lz, extra, tag):
            pts = [P(*root, 0), P(*root, -lz * 1000)]
            for e in extra:
                pts.append(e(pts[-1]))
            return w.polyline(pts, 0.04, 2.0e-3, tag)
        if cfg.get("mains_cable", True):
            down = cfg.get("mains_down", 0.8)
            cable((107, 28), 0.3, [lambda p: (p[0], p[1] - down, p[2])], "mains_cable")
            if cfg.get("cmad", True):
                last = np.array(w.P_last) if hasattr(w, "P_last") else None
                end = (P(107, 28)[0], P(107, 28)[1] - down, -0.3)
                w.polyline([end, (end[0], end[1] - 0.6, end[2])], 0.04, 2.0e-3, "cmad")
        if cfg.get("heater", 0.6):
            cable((128, 28), cfg.get("heater", 0.6), [], "heater")
        if cfg.get("fan", 0.4):
            cable((70, 28), cfg.get("fan", 0.4), [], "fan")
    if cfg.get("oven"):
        # cross-scope (scope A/B): floating steel oven body, 0.4 m cube wire grid (0.1 m mesh), front face = the steel front sheet
        # at z = +12 mm with the panel window (156 x 88 mm) open. Indicative only: 0.1 m mesh = lambda/10 at 300 MHz.
        g = np.linspace(-0.2, 0.2, 5); gz = np.linspace(0.012, -0.388, 5)
        def add(a, b):
            m = (np.array(a) + np.array(b)) / 2
            if abs(m[2] - 0.012) < 1e-6 and abs(m[0]) < 0.083 and abs(m[1]) < 0.049:
                return
            w.line(a, b, 2, 2.0e-3, "oven")
        for zf in (gz[0], gz[-1]):
            for v in g:
                for a0, a1 in zip(g[:-1], g[1:]):
                    add((a0, v, zf), (a1, v, zf)); add((v, a0, zf), (v, a1, zf))
        for xf in (g[0], g[-1]):
            for v in g:
                for z0, z1 in zip(gz[:-1], gz[1:]):
                    add((xf, v, z0), (xf, v, z1))
            for zv in gz[1:-1]:
                for a0, a1 in zip(g[:-1], g[1:]):
                    add((xf, a0, zv), (xf, a1, zv))
        for yf in (g[0], g[-1]):
            for v in g[1:-1]:
                for z0, z1 in zip(gz[:-1], gz[1:]):
                    add((v, yf, z0), (v, yf, z1))
            for zv in gz[1:-1]:
                for a0, a1 in zip(g[1:-2], g[2:-1]):
                    add((a0, yf, zv), (a1, yf, zv))
                add((g[0], yf, zv), (g[1], yf, zv)); add((g[-2], yf, zv), (g[-1], yf, zv))
    if cfg.get("tc_chassis"):
        # thermocouple lead J20 -> into the oven -> probe ring on the bottom wall node (-0.1, -0.2, -0.288)
        j = P(26.5, 102.5, 0)
        pts = [j, (j[0], j[1], -0.288), (-0.1, j[1], -0.288), (-0.1, -0.19, -0.288)]
        w.polyline(pts, 0.04, 2.0e-3, "tc")
        w.polyline([(-0.1, -0.19, -0.288), (-0.1, -0.2, -0.288)], 0.01, 2.0e-3, "tc_probe")
        w.probe_node = (-0.1, -0.19, -0.288)
    elif cfg.get("tc", 1.0):
        w.polyline([P(26.5, 102.5, 0), P(26.5, 102.5, -cfg.get("tc", 1.0) * 1000)], 0.04, 2.0e-3, "tc")
    w.finalize()
    return w


def setup_loads(w, cfg):
    """returns (source basis index, dict basis -> Z(f) callable)."""
    loads = {}
    if cfg.get("panel", True):
        fpc_segs = [i for i, t in enumerate(w.tags) if t == "fpc"]
        mids = w.mid[fpc_segs]
        tgt = np.array(P(155.7, 150, 2.7))
        nd = w.nearest_node(tgt)
        src = w.basis_at(nd)
        if cfg.get("fpc_ferrite"):          # proposal: flat ferrite core on the TFT FPC = series CM impedance (R + jX, ASSUMED)
            Rf = cfg["fpc_ferrite"]
            loads[src] = lambda f, Rf=Rf: Rf * min(1.0, f / 100e6) + 1j * 2 * math.pi * f * 0.3e-6 / (1 + (f / 30e6) ** 2)
        if cfg.get("gap_load"):             # v2: series loss + reflected driver impedance at the FPC gap (receive-mode runs, c9)
            gl = cfg["gap_load"]
            prev = loads.get(src)
            loads[src] = (lambda f, gl=gl, prev=prev: gl(f) + (prev(f) if prev else 0))
    else:
        src = None
    if cfg.get("mains", True):
        nd = w.nearest_node(w.hlk_node)
        b = w.basis_at(nd)
        C = cfg.get("Ciso", 47e-12)
        Y1 = cfg.get("Y1", 0.0)                 # cross-scope (B): Y1 SELV GND -> NEUT next to PS1, in parallel with the barrier
        if Y1:
            Lesl = 8e-9                          # Y1 disc + leads (ASSUMED)
            loads[b] = lambda f, C=C, Y1=Y1, L=Lesl: 1 / (1j * 2 * math.pi * f * C + 1 / (1 / (1j * 2 * math.pi * f * Y1) + 1j * 2 * math.pi * f * L + 0.1))
        else:
            loads[b] = lambda f, C=C: 1 / (1j * 2 * math.pi * f * C) + 0.5
        if cfg.get("mains_cable", True) and cfg.get("cmad", True):
            cm = [i for i, t in enumerate(w.tags) if t == "cmad"]
            for k, s in enumerate(cm[:-1]):
                nd = w.S[s][1]
                try:
                    bb = w.basis_at(nd)
                except KeyError:
                    continue
                R = 12.0 * (1 + k) ** 1.3          # tapered loading, ~ 150-250 ohm total like a CMAD/absorber (ASSUMED)
                loads[bb] = lambda f, R=R: R
    if cfg.get("tc_chassis") == "20pF":
        b = w.basis_at(w.nearest_node(w.probe_node))
        loads[b] = lambda f: 1 / (1j * 2 * math.pi * f * 20e-12)
    return src, loads


def obs_points(r=3.0, heights=(-0.5, 0.0, 0.5), naz=36):
    pts = []
    for h in heights:
        for az in np.linspace(0, 2 * np.pi, naz, endpoint=False):
            pts.append((r * math.sin(az), h, r * math.cos(az)))
    return np.array(pts)


OBS3 = obs_points()


def e_measured(E, obs):
    """antenna reading: vertical (y) and horizontal (tangential in the x-z plane) components -> max |.|"""
    radial = obs.copy(); radial[:, 1] = 0
    radial /= np.linalg.norm(radial, axis=1)[:, None]
    hdir = np.cross(np.array([0, 1, 0]), radial)
    Ev = np.abs(E[:, 1]); Eh = np.abs((E * hdir).sum(1))
    return max(Ev.max(), Eh.max())


def sac10(w, I, f, eut_y=1.0):
    """10 m SAC: EUT centre 1.0 m above a PEC floor (table 0.8 m + board), antenna 1..4 m height scan, 8 azimuths."""
    best = 0.0
    for h in (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
        obs = []
        for az in np.linspace(0, 2 * np.pi, 8, endpoint=False):
            obs.append((10 * math.sin(az), h - eut_y, 10 * math.cos(az)))
        obs = np.array(obs)
        E = w.fields(I, f, obs, image_z=-eut_y)
        best = max(best, e_measured(E, obs))
    return best


def run(cfg, freqs, label, sac=False, want_cable=True):
    w = build(cfg)
    src, loads = setup_loads(w, cfg)
    tags = np.array(w.tags)
    out = {"f": freqs, "E3": [], "E10": [], "cables": {}, "nseg": len(w.len), "nb": w.nb, "Igap": []}
    cab_tags = [t for t in ("mains_cable", "heater", "fan", "tc", "fpc", "bond", "oven") if (tags == t).any()]
    for t in cab_tags:
        out["cables"][t] = {"root": [], "max": []}
    t0 = time.time()
    for f in freqs:
        if f > cfg.get("fmax", 2e9):                 # coarse-mesh configs are only solved up to their validity limit
            out["E3"].append(float("nan"))
            if sac:
                out["E10"].append(float("nan"))
            for t in cab_tags:
                out["cables"][t]["root"].append(float("nan")); out["cables"][t]["max"].append(float("nan"))
            out["Igap"].append(complex(float("nan"), float("nan")))
            continue
        Z = w.Z(f)
        for b, zf in loads.items():
            Z[b, b] += zf(f)
        V = np.zeros(w.nb, complex)
        V[src] = 1.0
        I = np.linalg.solve(Z, V)
        out["Igap"].append(complex(I[src]))          # gap current per volt -> Z_struct = 1 / Igap (complex)
        E = w.fields(I, f, OBS3)
        out["E3"].append(e_measured(E, OBS3))
        if sac:
            out["E10"].append(sac10(w, I, f))
        c = w.seg_currents(I)
        for t in cab_tags:
            segs = np.where(tags == t)[0]
            out["cables"][t]["root"].append(float(np.abs(c[segs[0], 0])))
            out["cables"][t]["max"].append(float(np.abs(c[segs]).max()))
    print(label, "bonds", getattr(w, "n_bonds", 0), "nseg", len(w.len), "nb", w.nb, "%.1fs" % (time.time() - t0), flush=True)
    return out


CONFIGS = {
    "nominal": {},
    "no_cables": {"mains": False, "tc": 0},
    "tc_0.5m": {"tc": 0.5}, "tc_1.5m": {"tc": 1.5}, "tc_2.0m": {"tc": 2.0},
    "heater_0.3m": {"heater": 0.3}, "heater_1.0m": {"heater": 1.0},
    "Ciso_20pF": {"Ciso": 20e-12}, "Ciso_100pF": {"Ciso": 100e-12},
    "mains_no_cmad_1.5m": {"cmad": False, "mains_down": 1.2},
    "ferrite_fpc_150": {"fpc_ferrite": 150.0},
    "Ciso_50pF": {"Ciso": 50e-12},
    "Y1_470pF": {"Ciso": 50e-12, "Y1": 470e-12}, "Y1_1nF": {"Ciso": 50e-12, "Y1": 1e-9}, "Y1_2.2nF": {"Ciso": 50e-12, "Y1": 2.2e-9},
    "barrier_2.2nF_noY1": {"Ciso": 2.2e-9},
    "oven_tc_bonded": {"oven": True, "tc_chassis": "bonded", "fmax": 400e6}, "oven_tc_20pF": {"oven": True, "tc_chassis": "20pF", "fmax": 400e6},
    "oven_tc_bonded_Y1_1nF": {"oven": True, "tc_chassis": "bonded", "Ciso": 50e-12, "Y1": 1e-9, "fmax": 400e6},
    "bond_perimeter": {"bonds": [((x, 118.5), (x, 119)) for x in (26.5, 41, 56, 70, 85, 100, 113.5, 128, 142, 155.7, 170)] +
                       [((26.5, 20.5), (26.5, 19)), ((41, 20.5), (41, 19))] +
                       [((183.5, 68), (184.9, 65)), ((183.5, 76), (184.9, 80)), ((183.5, 90), (184.9, 95)), ((183.5, 112), (184.9, 108))] +
                       [((20.5, 35), (20.02, 35)), ((20.5, 50), (20.02, 50)), ((20.5, 76), (20.02, 80)), ((20.5, 90), (20.02, 95)), ((20.5, 112), (20.02, 108))]},
    "bond_perimeter_ferrite": None,
    "bond_3pt": {"bonds": [((142, 118.5), (142, 119)), ((170, 118.5), (170, 119)), ((128, 118.5), (128, 119))]},
    "bond_6pt": {"bonds": [((100, 118.5), (100, 119)), ((128, 118.5), (128, 119)), ((142, 118.5), (142, 119)), ((170, 118.5), (170, 119)),
                           ((183.5, 90), (184.9, 95)), ((26.5, 118.5), (26.5, 119))]},
}

CONFIGS["bond_perimeter_ferrite"] = dict(CONFIGS["bond_perimeter"], fpc_ferrite=150.0)
CONFIGS["frame_floating"] = {"frame_floating": True}
CONFIGS["nominal_dense"] = {}

if __name__ == "__main__":
    fh = np.array([k * 16.65e6 for k in range(2, 61)])
    fsw = np.geomspace(30e6, 1000e6, 40)
    freqs = np.unique(np.concatenate([fh, fsw]))
    args = [a for a in sys.argv[1:] if not a.startswith("--out=")]
    outn = [a[6:] for a in sys.argv[1:] if a.startswith("--out=")]
    sel = args if sys.argv[1:] else list(CONFIGS)
    import glob
    npz = os.path.join(WORK, outn[0] if outn else "cm_structure_v2.npz")
    mine = {}
    for name in sel:
        fr = np.arange(120e6, 242e6, 2e6) if name.endswith("_dense") else freqs
        mine[name] = run(CONFIGS[name], fr, name, sac=(name in ("nominal", "bond_6pt", "bond_perimeter")))
        np.savez(npz, **{k: np.array(v, dtype=object) for k, v in mine.items()})
    # merge every v2 store (parallel runs write separate files); the lossless v1 store is not used any more
    store = {}
    for fn in sorted(glob.glob(os.path.join(WORK, "cm_structure_v2*.npz")), key=os.path.getmtime):
        d_ = np.load(fn, allow_pickle=True)
        store.update({k: d_[k].item() for k in d_.files})
    # summary to results.json
    summ = {"freqs_MHz": (freqs / 1e6).round(3).tolist(), "configs": {k: CONFIGS[k] for k in store}, "assumptions": __doc__.split("Geometry")[1][:1800]}
    for k, v in store.items():
        if k.endswith("_dense"):
            ig = np.array(v["Igap"], complex)
            summ[k] = {"f_MHz": (np.array(v["f"]) / 1e6).round(3).tolist(), "Igap_re": ig.real.tolist(), "Igap_im": ig.imag.tolist(),
                       "E3_dBuV_per_V": (dB(np.array(v["E3"])) + 120).round(2).tolist(),
                       "cable_max_mA_per_V": {t: (np.array(c["max"]) * 1e3).round(4).tolist() for t, c in v["cables"].items()}}
            continue
        ig = np.array(v.get("Igap", [np.nan] * len(freqs)), complex)
        E = np.array(v["E3"])
        summ[k] = {"nseg": v["nseg"], "E3_dBuV_per_V_max": float(dB(np.nanmax(E)) + 120), "at_MHz": float(freqs[int(np.nanargmax(E))] / 1e6),
                   "E3_dBuV_per_V": (dB(E) + 120).round(2).tolist(),
                   "E10_dBuV_per_V": (dB(np.array(v["E10"])) + 120).round(2).tolist() if v["E10"] else None,
                   "cable_root_mA_per_V": {t: (np.array(c["root"]) * 1e3).round(4).tolist() for t, c in v["cables"].items()},
                   "cable_max_mA_per_V": {t: (np.array(c["max"]) * 1e3).round(4).tolist() for t, c in v["cables"].items()},
                   "Igap_re": ig.real.tolist(), "Igap_im": ig.imag.tolist()}
    save_section("cm_structure", summ)
