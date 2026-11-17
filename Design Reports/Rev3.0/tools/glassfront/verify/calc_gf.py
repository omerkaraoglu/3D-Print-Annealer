"""E. Calculations the design relies on, with section properties measured on the STEP.

  <venv>\\Scripts\\python.exe calc_gf.py [--frame f.step]

1. Ring section properties on STEP sections (I about the in-plane axis along the edge, through the section centroid, as
   the concept's ring_section): mid-top, mid-sides, near a corner, the corner apex (diagonal through F1); GF-2.0 bottom: the
   bridge at x 60 (CTP), 103.85 / 150 (TFT) and at the divider rib, as 'channel' (bridge + flange plate + bottom wall) and
   'bridge only' (cut at the bottom-wall inner face y 147.7), and outside the tail span (x 24).
2. Push: the concept grillage (grillage_port.py, a validated COPY - concept_calc.py is never imported or run) with one ring
   section per edge; glass 1.1 / 2.0 / 3.0 / 4.0, both bottom bounds (channel / bridge only); concept rectangles, and the
   measured I at 3.0 (scaled by the measured / concept ratio at the other thicknesses). 50 N and 250 N.
3. 0.5 J impact (concept sec. 8 method): window centre and the unbonded strip over the bend gap (panel edge -> bead).
4. Bead: area, dead load, 250 N retention, shear at the temperature extremes with moisture, d_allow = t sqrt(2e + e^2).
5. Gaps g1 / g2 at -20 / +20 / +70 C, 50 / 70 ppm/K, with tolerances (from the fit check's STEP-lip measurement).
6. Tape: area, module dead load, 250 N, thermal shear; fastener loads (stud reactions, washer bearing, radial float).
7. Tolerance stack of the bend gap against the minimum tail clearance (fit check tail cases).
Output: the "calc" dict (calc.json) and calc.md.
"""
import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

import vcommon as C
import grillage_port as GP

RHO = 1.36      # g/cm3 PA6-GF30 FR (v2 value)
M_PANEL, M_REST = 200.0, 290.0      # g [A] concept_calc.py sec. 6: panel, PCB + parts etc.
TG_LIST = (1.1, 2.0, 3.0, 4.0)
T1 = math.tan(math.radians(1.0))


# ----------------------------------------------------------------------------------------------- section properties
def face_props(faces, axis):
    A = Sz = 0.0
    parts = []
    for f in faces:
        g = GProp_GProps()
        BRepGProp.SurfaceProperties_s(f.wrapped, g)
        a = g.Mass()
        c = g.CentreOfMass()
        M = g.MatrixOfInertia()
        Izz_own = M.Value(2, 2) if axis == "x" else M.Value(1, 1)
        parts.append((a, c.Z(), Izz_own))
        A += a
        Sz += a * c.Z()
    zc = Sz / A
    I = sum(Io + a * (z - zc) ** 2 for a, z, Io in parts)
    return A, zc, I


def diag_section(fr, origin_abs, u_abs, t_keep):
    x0, y0 = origin_abs
    a = np.array([u_abs[0], -u_abs[1], 0.0]); a /= np.linalg.norm(a)
    n = (a[1], -a[0], 0.0)
    sec = C.general_section(fr, (x0, -y0, 0.0), n)
    A = Sz = 0.0
    parts = []
    zmin, zmax = 1e9, -1e9
    for f in sec.Faces():
        c = f.Center()
        t = (c.x - x0) * a[0] + (c.y + y0) * a[1]
        if not (t_keep[0] < t < t_keep[1]):
            continue
        g = GProp_GProps()
        BRepGProp.SurfaceProperties_s(f.wrapped, g)
        M = g.MatrixOfInertia()
        Mm = np.array([[M.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])
        parts.append((g.Mass(), g.CentreOfMass().Z(), float(a @ Mm @ a)))
        A += g.Mass(); Sz += g.Mass() * g.CentreOfMass().Z()
        bb = f.BoundingBox(); zmin = min(zmin, bb.zmin); zmax = max(zmax, bb.zmax)
    zc = Sz / A
    I = sum(Io + m * (z - zc) ** 2 for m, z, Io in parts)
    return {"A_mm2": round(A, 2), "zc": round(zc, 3), "I_mm4": round(I, 1), "faces": len(parts),
            "z_range": [round(zmin, 3), round(zmax, 3)], "c_mm": round(max(abs(zmin - zc), abs(zmax - zc)), 3)}


def ring_section(fr, axis, value, keep, clip=None):
    """faces of the section by x = value (axis 'x', keep(y_abs_lo, y_abs_hi)) or y = value; clip = (lo, hi) in the in-plane
    horizontal coordinate (abs y for 'x', x for 'y') cuts the faces with a box"""
    sec = C.plane_section(fr, axis, value if axis == "x" else -value)
    faces = []
    for f in sec.Faces():
        bb = f.BoundingBox()
        lo, hi = (-bb.ymax, -bb.ymin) if axis == "x" else (bb.xmin, bb.xmax)
        if keep(lo, hi):
            if clip:
                if axis == "x":
                    b = C.box(value - 1, value + 1, -clip[1], -clip[0], -30, 30)
                else:
                    b = C.box(clip[0], clip[1], -value - 1, -value + 1, -30, 30)
                faces += C.common_shape(f, b).Faces()
            else:
                faces.append(f)
    if not faces:
        return {"A_mm2": None, "zc": None, "I_mm4": None, "faces": 0, "z_range": None, "c_mm": None,
                "note": "no section face passed the filter"}
    A, zc, I = face_props(faces, axis)
    zmin = min(f.BoundingBox().zmin for f in faces)
    zmax = max(f.BoundingBox().zmax for f in faces)
    return {"A_mm2": round(A, 2), "zc": round(zc, 3), "I_mm4": round(I, 1), "faces": len(faces),
            "z_range": [round(zmin, 3), round(zmax, 3)], "c_mm": round(max(abs(zmin - zc), abs(zmax - zc)), 3)}


# ----------------------------------------------------------------------------------------------- grillage set-up
def char_strength(G, tg):
    gt = next(p for p in G.raw["driving_parameters"] if p["name"] == "glass_t")
    return float(gt["types"]["%.1f" % tg]["char_strength_MPa"])


def levels(G, tg):
    lv = G.raw["derived_levels"]["evaluated_by_glass_t"]
    key = next(k for k in lv if abs(float(k) - tg) < 1e-6)
    return {k: float(v) for k, v in lv[key].items()}


def lands(G):
    d = {}
    for r in G.lands:
        n = r["name"]
        if n.startswith("bottom (over"):          # GF-1.1 file
            d["bottom"] = r["value"]
        if n.startswith("abs left"):
            d["left"] = r["value"]
        elif n.startswith("abs right"):
            d["right"] = r["value"]
        elif n.startswith("top"):
            d["top"] = r["value"]
        elif n.startswith("bottom over"):
            d["bottom"] = r["value"]
        elif n.startswith("bottom outside"):
            d["bottom_outside"] = r["value"]
    return d


def concept_sections(G, tg, bottom):
    Zl = levels(G, tg)
    ld = lands(G)
    gy1 = G.GLASS[3]
    S = {"top": GP.section_props(GP.ring_rects(Zl, ld["top"])), "left": GP.section_props(GP.ring_rects(Zl, ld["left"])),
         "right": GP.section_props(GP.ring_rects(Zl, ld["right"]))}
    beam = (G.TAIL[3] - gy1, G.TAIL[3] + G.WALL - gy1)
    if bottom == "channel":
        S["bottom"] = GP.section_props(GP.ring_rects(Zl, ld["bottom"], kind="bridge", beam=beam))
    else:
        S["bottom"] = GP.section_props(GP.ring_rects(Zl, ld["bottom"], kind="bridge"))
    return S


def validate_port(log):
    """the copied grillage reproduces the GF-1.1 concept numbers (concept_gf2_calc.py sec. 5.0, concept_calc_out.txt)"""
    G11 = C.GF(C.GF11_PARAMS)
    GP.setup(G11)
    L3 = levels(G11, 3.0)
    gl = G11.GLASS[:4]
    fl = G11.FLINE[:4]
    gc = ((gl[0] + gl[1]) / 2, (gl[2] + gl[3]) / 2)
    pw = G11.PRINT
    wc = ((pw[0] + pw[1]) / 2, (pw[2] + pw[3]) / 2)
    logo = (pw[3] + gl[3]) / 2
    sec = GP.section_props(GP.ring_rects(L3, 6.11))
    loads = [wc, (gc[0], gl[2]), (gl[0], gc[1]), (gc[0], logo), (gc[0], gl[3])]
    sup = [G11.fxy(n) for n in ("F1", "F2", "F3", "F4")]
    r = GP.grillage(gl, fl, {e: sec for e in ("top", "bottom", "left", "right")}, 3.0, supports=sup, vhb=True, loads=loads,
                    extra_ys=(wc[1], gc[1], logo, G11.PANEL[3]))
    got = [round(x["w"] * 50, 4) for x in r]
    ref = [0.139, 0.067, 0.066, 0.092, 0.067]
    ok = all(abs(a - b) < 0.0015 for a, b in zip(got, ref))
    log("    port validation (GF-1.1 S4, glass 3.0, I %.0f): %s vs concept %s -> %s" % (sec["I"], got, ref, "ok" if ok else "MISMATCH"))
    return {"I_GF11_concept": round(sec["I"], 1), "w50_mm": got, "concept_w50_mm": ref, "ok": ok}


def prev_release(ctx):
    """the previous release's own verification numbers (archived out/<PREV_TAG>/calc.json), for the 'previous' columns"""
    p = os.path.join(ctx.outdir, C.PREV_TAG, "calc.json")
    out = {"tag": C.PREV_TAG, "source": p if os.path.exists(p) else None}
    if not out["source"]:
        return out
    c = json.load(open(p))
    rows = c["grillage"]["rows"]
    def w(bottom, tg, lp, k="w_50N_mm"):
        return next((r[k] for r in rows if r["bottom"] == bottom and r["glass_t"] == tg and r["I_source"].startswith("measured")
                     and r["load_point"] == lp), None)
    tgs = sorted({r["glass_t"] for r in rows})
    out.update({
        "bead_area_mm2": c["bead"]["area_mm2"], "r_bead_corner_mm": c["bead"]["r_bead_corner_mm"],
        "bead_dead_load_kPa": c["bead"]["dead_load_kPa"], "bead_pull_250N_MPa": c["bead"]["pull_250N_MPa"],
        "bead_shear_bound_moisture_d_mm": next(s["d_mm"] for s in c["bead"]["shear"] if s["case"] == "bound + 0.3 % moisture, +70 C"),
        "tape_area_mm2": c["tape_fasteners"]["tape_area_mm2"], "tape_dead_load_kPa": c["tape_fasteners"]["tape_dead_load_kPa"],
        "tape_250N_kPa": c["tape_fasteners"]["tape_250N_kPa"], "tape_thermal_shear_pct_50_70": c["tape_fasteners"]["tape_thermal_shear_pct_50_70"],
        "volume": "%.3f cm3 / %.1f g" % (c["volume"]["volume_cm3"], c["volume"]["mass_g"]),
        "push_50N_window_centre_mm": {"%.1f" % t: w("channel", t, "window centre") for t in tgs},
        "push_50N_lip_line_max_mm": {"%.1f" % t: max(r["lip_line_50N_mm"] for r in rows if r["glass_t"] == t and r["I_source"].startswith("measured")
                                                     and r["load_point"] != "window centre") for t in tgs},
        "glass_250N_max_MPa": {"%.1f" % t: max(r["glass_250N_MPa"] for r in rows if r["glass_t"] == t and r["I_source"].startswith("measured"))
                               for t in tgs},
        "impact_SF_centre": {k.split()[-1]: v["window_centre"]["SF"] for k, v in c["impact_0p5J"].items() if k.startswith("channel")},
        "impact_SF_strip_whole_border": {k.split()[-1]: v["bend_gap_strip_whole_border_free"]["SF"] for k, v in c["impact_0p5J"].items()
                                         if k.startswith("channel")}})
    return out


# ----------------------------------------------------------------------------------------------- run
def run(ctx, log=C.log, fit=None):
    t0 = time.time()
    G, fr = ctx.G, ctx.frame
    L = G.L
    out = {}
    out["previous_release"] = PR = prev_release(ctx)
    # ---------------- 1. sections
    secs = {
        "mid-top (x 80)": ("x", 80.0, lambda lo, hi: hi < 40, None),
        "mid-top (x 103.85, no F5 at GF-2.0)": ("x", G.GC[0], lambda lo, hi: hi < 40, None),
        "mid-side left (y 60)": ("y", 60.0, lambda lo, hi: hi < 40, None),
        "mid-side right (y 60)": ("y", 60.0, lambda lo, hi: lo > 170, None),
        "near the top-left corner (x 23, past the corner arc and the side shelf)": ("x", 23.0, lambda lo, hi: hi < 40, None),
    }
    if G.gf2:
        for lab, x in (("CTP compartment x 60", 60.0), ("TFT compartment x 103.85", G.GC[0]), ("TFT wide part x 150", 150.0)):
            secs["bottom bridge %s: channel (bridge + flange plate + bottom wall)" % lab] = ("x", x, lambda lo, hi: hi > 119.5, (119.5, 152.0))
            secs["bottom bridge %s: bridge only (cut at the bottom-wall inner face y %.1f)" % (lab, G.TAIL[3])] = (
                "x", x, lambda lo, hi: hi > 119.5, (119.5, G.TAIL[3]))
        secs["bottom at the divider rib x %.2f: channel incl. the rib" % G.div_x] = ("x", G.div_x, lambda lo, hi: hi > 119.5, (119.5, 152.0))
        secs["bottom outside the tail span x 24 (corner cell, land %.2f)" % next(
            r["value"] for r in G.lands if r["name"] == "bottom outside the tail span")] = ("x", 24.0, lambda lo, hi: hi > 110, (110.0, 152.0))
    res = {}
    for name, (ax, v, keep, clip) in secs.items():
        res[name] = ring_section(fr, ax, v, keep, clip)
    res["corner apex: diagonal plane through F1 and the glass corner (incl. pad, tube, rib)"] = diag_section(fr, G.fxy("F1"), G.slot_axis("F1"), (-12.0, 32.0))
    for name in res:
        log("    %-82s A %7.1f  zc %7.3f  I %7.0f mm4" % (name[:82], res[name]["A_mm2"] or 0, res[name]["zc"] or 0, res[name]["I_mm4"] or 0))
    out["sections"] = res
    # ---------------- 2. grillage
    log("[E] grillage port: validation against the GF-1.1 concept")
    out["port_validation"] = validate_port(log)
    GP.setup(G)
    gl = G.GLASS[:4]
    fl = G.FLINE[:4]
    gc = G.GC
    pw = G.PRINT
    wc = ((pw[0] + pw[1]) / 2, (pw[2] + pw[3]) / 2)
    y_gap = (G.PANEL[3] + G.BRIDGE[2]) / 2
    LOADS = [("window centre", wc), ("glass top edge, mid", (gc[0], gl[2])), ("glass side edge, mid", (gl[0], gc[1])),
             ("bottom border over the bend gap", (gc[0], y_gap)), ("glass bottom edge, mid", (gc[0], gl[3])),
             ("bottom edge over the CTP tail (x 58)", (58.0, gl[3]))]
    XY = (wc[1], gc[1], y_gap, G.PANEL[3])
    sup = [G.fxy(n) for n in G.stud_names("S4")]
    S3c, S3b = concept_sections(G, 3.0, "channel"), concept_sections(G, 3.0, "bridge")
    meas = {"top": res["mid-top (x 80)"], "left": res["mid-side left (y 60)"], "right": res["mid-side right (y 60)"],
            "bottom channel": res["bottom bridge CTP compartment x 60: channel (bridge + flange plate + bottom wall)"],
            "bottom bridge": res["bottom bridge CTP compartment x 60: bridge only (cut at the bottom-wall inner face y %.1f)" % G.TAIL[3]]}
    ratio = {"top": meas["top"]["I_mm4"] / S3c["top"]["I"], "left": meas["left"]["I_mm4"] / S3c["left"]["I"],
             "right": meas["right"]["I_mm4"] / S3c["right"]["I"],
             "channel": meas["bottom channel"]["I_mm4"] / S3c["bottom"]["I"], "bridge": meas["bottom bridge"]["I_mm4"] / S3b["bottom"]["I"]}
    out["concept_sections_3.0"] = {"channel": {k: {kk: round(vv, 3) for kk, vv in v.items() if kk != "rects"} for k, v in S3c.items()},
                                   "bridge_bottom": {kk: round(vv, 3) for kk, vv in S3b["bottom"].items() if kk != "rects"}}
    out["measured_over_concept_I"] = {k: round(v, 3) for k, v in ratio.items()}
    tab = []
    for bottom in ("channel", "bridge"):
        for tg in TG_LIST:
            Sc = concept_sections(G, tg, bottom)
            for src in ("concept rectangles", "measured I (3.0 STEP; scaled at other t)"):
                S = {k: dict(v) for k, v in Sc.items()}
                if src.startswith("measured"):
                    for e in ("top", "left", "right"):
                        S[e]["I"] = Sc[e]["I"] * ratio[e]
                        if tg == 3.0:
                            S[e]["c"] = max(Sc[e]["c"], meas[e]["c_mm"])
                    S["bottom"]["I"] = Sc["bottom"]["I"] * ratio[bottom]
                    if tg == 3.0:
                        S["bottom"]["c"] = max(Sc["bottom"]["c"], meas["bottom " + bottom]["c_mm"])
                r = GP.grillage(gl, fl, S, tg, supports=sup, vhb=True, loads=[p for _, p in LOADS], extra_ys=XY)
                char = char_strength(G, tg)
                for (ln, _), rr in zip(LOADS, r):
                    tab.append({"bottom": bottom, "glass_t": tg, "I_source": src, "load_point": ln, "w_5N_um": round(rr["w"] * 5000, 1),
                                "w_50N_mm": round(rr["w"] * 50, 4), "lip_line_50N_mm": round(rr["w_perim"] * 50, 4),
                                "bottom_edge_50N_mm": round(rr["w_bottom"] * 50, 4), "glass_250N_MPa": round(rr["sig_g"] * 250, 1),
                                "glass_SF_250N": round(char / max(rr["sig_g"] * 250, 1e-9), 2), "ring_250N_MPa": round(rr["sig_r"] * 250, 1),
                                "stud_250N_N": round(rr["R"] * 250, 0), "_k_N_per_mm": 1.0 / rr["w"]})
    out["grillage"] = {"config": "S4/R4: 4 corner studs + VHB, %s" % ", ".join("%s %s" % (n, G.fxy(n)) for n in G.stud_names("S4")),
                       "rows": [{k: v for k, v in r.items() if not k.startswith("_")} for r in tab],
                       "note": "one ring section per edge; J and the corner links as the concept; glass characteristic strength per glass_t "
                               "from the params (1.1/2.0 CS 250 MPa, 3.0/4.0 tempered 120 MPa); no panel / LOCA / PCB credit"}
    out["concept_estimates_in_params"] = G.raw["checks"].get("push_50N_glass3.0_concept_estimate_mm")
    out["GF11_values"] = G.raw["checks"].get("GF-1.1_values_superseded")
    # ---------------- 3. impact 0.5 J
    a_disp = 0.5 * min(G.POCKET[1] - G.POCKET[0], G.POCKET[3] - G.POCKET[2])
    b_free = (gl[3] - G.bead_edge - G.bead_w) - G.PANEL[3]
    gW, gH = gl[1] - gl[0], gl[3] - gl[2]
    imp = {}
    for bottom in ("channel", "bridge"):
        for tg in TG_LIST:
            char = char_strength(G, tg)
            rows_t = {r["load_point"]: r for r in tab if r["bottom"] == bottom and r["glass_t"] == tg and r["I_source"].startswith("measured")}
            D_g = GP.E_G * tg ** 3 / (12 * (1 - GP.NU_G ** 2))
            mg = (gW * gH - (4 - math.pi) * G.R_glass ** 2) * tg * GP.RHO_G
            mm = 0.25 * (mg + M_PANEL) / 1000
            k_c = rows_t["window centre"]["_k_N_per_mm"]
            ic = GP.impact(k_c, mm, tg, a_disp)
            k_glob = rows_t["bottom border over the bend gap"]["_k_N_per_mm"]
            k_loc = D_g / (0.0169 * b_free ** 2)
            k_ser = 1 / (1 / k_glob + 1 / k_loc)
            ib = GP.impact(k_ser, mm, tg, 0.6 * G.border)
            is_ = GP.impact(k_ser, mm, tg, 0.6 * b_free)
            imp["%s %.1f" % (bottom, tg)] = {"glass_mass_g": round(mg, 1), "char_MPa": char,
                                             "window_centre": {"F_N": round(ic["mass"][0], 1), "sigma_MPa": round(ic["mass"][1], 1), "SF": round(char / ic["mass"][1], 2),
                                                               "SF_all_0p5J": round(char / ic["bound"][1], 2)},
                                             "bend_gap_strip_whole_border_free": {"sigma_MPa": round(ib["mass"][1], 1), "SF": round(char / ib["mass"][1], 2)},
                                             "bend_gap_strip_only": {"sigma_MPa": round(is_["mass"][1], 1), "SF": round(char / is_["mass"][1], 2)},
                                             "strip_width_mm": round(b_free, 3), "k_local": round(k_loc, 0), "k_global": round(k_glob, 0)}
    out["impact_0p5J"] = imp
    # ---------------- 4. bead
    gx0, gx1, gy0, gy1, gR = G.GLASS
    def rr_area(i):
        w, h, r = (gx1 - gx0) - 2 * i, (gy1 - gy0) - 2 * i, max(gR - i, 0.0)
        return w * h - (4 - math.pi) * r * r
    bead_area = rr_area(G.bead_edge) - rr_area(G.bead_edge + G.bead_w)
    mg3 = (gW * gH - (4 - math.pi) * G.R_glass ** 2) * 3.0 * GP.RHO_G
    r_bead = math.hypot((gW - 2 * (G.bead_edge + G.bead_w / 2)) / 2, (gH - 2 * (G.bead_edge + G.bead_w / 2)) / 2)
    def d_allow(t, e):
        return t * math.sqrt(2 * e + e * e)
    def eq_ext(d, t):
        return math.sqrt(1 + (d / t) ** 2) - 1
    shear = []
    for lab, a_f, dT, moist in (("design 50 ppm/K, +70 C", 50e-6, 50, 0.0), ("bound 70 ppm/K, +70 C", 70e-6, 50, 0.0),
                                ("design 50 ppm/K, -20 C", 50e-6, -40, 0.0), ("bound 70 ppm/K, -20 C", 70e-6, -40, 0.0),
                                ("design + 0.1 % moisture, +70 C", 50e-6, 50, 0.001), ("bound + 0.3 % moisture, +70 C", 70e-6, 50, 0.003)):
        d = abs((a_f - 9e-6) * dT * r_bead + moist * r_bead)
        shear.append({"case": lab, "d_mm": round(d, 3), "eq_ext_t0.73": round(eq_ext(d, 0.73), 3), "eq_ext_t1.0": round(eq_ext(d, 1.0), 3),
                      "class50_t0.73_allow": round(d_allow(0.73, 0.5), 3), "class25_t0.73_allow": round(d_allow(0.73, 0.25), 3),
                      "class50_t1.0_allow": round(d_allow(1.0, 0.5), 3), "class25_t1.0_allow": round(d_allow(1.0, 0.25), 3),
                      "ok_class50_t0.73": d <= d_allow(0.73, 0.5), "ok_class25_t1.0": d <= d_allow(1.0, 0.25)})
    out["bead"] = {"area_mm2": round(bead_area, 1), "params_bead_area": next(b["value"] for b in G.raw["bead"] if b["name"] == "bead_area"),
                   "prev_area_mm2": PR.get("bead_area_mm2"), "pip_area_inside_mm2": round(len(G.pips) * math.pi * (G.pip_d / 2) ** 2, 2),
                   "land_face_area_step_mm2": round(sum(f.Area() for f in C.faces_at_z(fr, L["Z_LAND"], -1, tol=0.005)), 1),
                   "glass_mass_3.0_g": round(mg3, 1), "dead_load_glass_panel_N": round((mg3 + M_PANEL) * 9.81e-3, 3),
                   "dead_load_kPa": round((mg3 + M_PANEL) * 9.81e-3 / bead_area * 1e3, 3), "pull_250N_MPa": round(250 / bead_area, 4),
                   "r_bead_corner_mm": round(r_bead, 2), "prev_r_bead_corner_mm": PR.get("r_bead_corner_mm"), "shear": shear}
    # ---------------- 5. gaps (from the fit check's STEP lip and tolerance cases)
    if fit is None and os.path.exists(ctx.out("fitcheck.json")):
        fit = json.load(open(ctx.out("fitcheck.json")))
    if fit:
        tt = fit["gaps"]["tolerance_thermal"]
        gtab = {}
        for tag in ("g2", "g1"):
            for tname, cs in tt[tag].items():
                gtab.setdefault(tag, {})[tname] = {k: v for k, v in cs.items()}
        out["gaps_table"] = gtab
    # concept formula (nominal per side) for this glass and the previous release's - the change the larger glass makes
    th = {}
    Gp = C.GF(C.PREV_PARAMS)
    cur, prv = str(G.revision).split(" ")[0], C.PREV_TAG
    for an, af in (("50 ppm/K", 50e-6), ("70 ppm/K", 70e-6)):
        for tn, (dtf, dts) in (("-20 C", (-40, -40)), ("+70 C frame / +50 C sheet", (50, 30))):
            v = {}
            for tag, GG in ((cur, G), (prv, Gp)):
                w2, h2 = (GG.GLASS[1] - GG.GLASS[0]) / 2, (GG.GLASS[3] - GG.GLASS[2]) / 2
                d2 = min((af - 9e-6) * dtf * h for h in (w2, h2))
                d1 = min(-(af * dtf - 12e-6 * dts) * h for h in (w2 + GG.g2 + GG.lip_w, h2 + GG.g2 + GG.lip_w))
                v[tag] = (round(G.g2 + d2, 4), round(G.g1 + d1, 4))
            th["%s, %s" % (an, tn)] = {"%s g2 / g1" % cur: v[cur], "%s g2 / g1" % prv: v[prv],
                                       "change g2 / g1": (round(v[cur][0] - v[prv][0], 4), round(v[cur][1] - v[prv][1], 4))}
    out["gaps_formula"] = th
    # ---------------- 6. tape and fasteners
    lt, ls = G.strip_lengths["top_bottom"], G.strip_lengths["sides"]
    A_tape = 2 * lt * G.tape_w + 2 * ls * G.tape_w
    m_frame = ctx.frame_info["volume_mm3"] / 1000 * RHO
    W_mod = (mg3 + M_PANEL + m_frame + M_REST) * 9.81e-3
    r_tape = math.hypot(gW / 2 + G.tape_s[1], gH / 2 + G.tape_s[1])
    r_stud = max(math.hypot(G.fxy(n)[0] - gc[0], G.fxy(n)[1] - gc[1]) for n in G.stud_names("S4"))
    studs = [r for r in tab if r["glass_t"] == 3.0 and r["I_source"].startswith("measured")]
    out["tape_fasteners"] = {"tape_area_mm2": round(A_tape, 1), "prev_tape_area_mm2": PR.get("tape_area_mm2"),
                             "module_mass_g": {"glass_3.0": round(mg3, 1), "panel [A]": M_PANEL, "frame (STEP x 1.36)": round(m_frame, 1), "PCB etc. [A]": M_REST},
                             "module_dead_load_N": round(W_mod, 2), "tape_dead_load_kPa": round(W_mod / A_tape * 1e3, 3),
                             "tape_250N_kPa": round(250 / A_tape * 1e3, 1),
                             "r_tape_corner_mm": round(r_tape, 1),
                             "tape_thermal_shear_pct_50_70": [round((50e-6 * 50 - 12e-6 * 30) * r_tape / G.t_gap * 100, 1),
                                                              round((70e-6 * 50 - 12e-6 * 30) * r_tape / G.t_gap * 100, 1)],
                             "stud_r_from_glass_centre": round(r_stud, 2),
                             "stud_radial_move_mm_50_70": [round((50e-6 - 12e-6) * 50 * r_stud, 3), round((70e-6 - 12e-6) * 50 * r_stud, 3)],
                             "stud_float_along_slot_mm": round((G.slot_l - 4.0) / 2 - 0.3, 3),
                             "stud_reaction_250N_max_N": max(r["stud_250N_N"] for r in studs),
                             "washer_M4_500N_MPa": None}
    if fit and fit.get("washer"):
        w = fit["washer"]["washer"]
        cen = min(r["area_mm2"] for r in w if r["position"] == "centred")
        wmin = min(r["area_mm2"] for r in w)
        out["tape_fasteners"]["washer_M4_500N_MPa"] = [round(500 / cen, 2), round(500 / wmin, 2)]
    # ---------------- 7. bend-gap tolerance stack
    stack = {}
    if fit and fit.get("tails"):
        cs = fit["tails"]["cases"]
        def fm(case, n):
            return cs[case][n]["frame_min"]
        def cls(case, n, k):
            return cs[case][n]["frame_by_class"].get(k, {}).get("min")
        nomk = "nominal (params polylines)"
        import tails_gf2 as TG_
        bridge_keys = TG_.BEND_KEYS + (TG_.K_LPB,)
        for n in ("TFT", "CTP"):
            c_nom = min(cls(nomk, n, k) for k in bridge_keys)
            c_p = min(cls("panel edge +0.35 (towards the bridge)", n, k) for k in bridge_keys)
            sens = (c_nom - c_p) / 0.35
            dz = max(c_nom - min(cls("exit Z +0.3 (towards the PCB)", n, k) for k in bridge_keys),
                     c_nom - min(cls("exit Z -0.3 (towards the glass)", n, k) for k in bridge_keys), 0.0)
            # panel edge position relative to the bridge face [A unless noted]
            contrib = {"panel outline vs AA (DS, concept 0.2)": 0.20, "J1: AA aligned to the print window (concept 0.1)": 0.10,
                       "print window vs glass edge (params drawing_tolerances.print 'print-to-edge +-0.2')": 0.20,
                       "J2: glass centred in the recess (graded shims, design doc 9.3)": 0.05,
                       "frame: bridge face (B core) vs recess wall (A core), core shift [A]": 0.05}
            wc_pos = sum(contrib.values())
            rss_pos = math.sqrt(sum(v * v for v in contrib.values()))
            t_tol = 0.05
            c_wc = c_nom - sens * wc_pos - t_tol - dz
            c_rss = c_nom - math.sqrt((sens * rss_pos) ** 2 + t_tol ** 2 + dz ** 2)
            c_concept = c_nom - sens * 0.35 - t_tol
            stack[n] = {"nominal_min_to_bridge_mm": round(c_nom, 4), "at_panel_edge_+0.35": round(c_p, 4),
                        "sensitivity_per_mm_panel_shift": round(sens, 3), "exit_Z_+-0.3_loss": round(dz, 4),
                        "panel_position_contributors_mm": contrib, "panel_position_WC": round(wc_pos, 3), "panel_position_RSS": round(rss_pos, 3),
                        "concept_panel_position_WC_RSS": [0.35, 0.25], "tail_thickness_tol": t_tol,
                        "clearance_WC_all_contributors": round(c_wc, 3), "clearance_RSS": round(c_rss, 3),
                        "clearance_concept_budget (panel 0.35 WC + tail 0.05)": round(c_concept, 3),
                        "worst_tolerance_case_fit": round(min(fm(c, n) for c in cs), 4)}
    out["bend_gap_stack"] = stack
    # bend-zone criterion (params tail_clearance_criteria.bend_zone), measured directly in 3D by the fit check, and the
    # concept's g_bend budget with the corrected position term
    import tails_gf2 as TG
    bc = TG.bend_zone_criterion(G)
    bz = (fit or {}).get("tails", {}).get("bend_zone")
    l0, rin, tt = float(G.tail_straight_l0 or 0.5), float(G.tail_R_in_min or 1.5), float(G.tail_t or 0.3)
    bezel = G.PANEL[3] - G.PRINT[3]
    # land needed by A1 as it is measured: bead_pocket_min to the land-break edge on the land plane, i.e. bead_edge + bead_w +
    # bead_pocket_min + land_break from the glass edge to the bridge pocket face (the GF-2.0 budget used 5.9 to the face)
    land_min_face = G.bead_edge + G.bead_w + float(G.bead_pocket_min or 1.0)
    land_min = land_min_face + float(G.land_break or 0.0)
    g_max = G.border - bezel - land_min
    budget = l0 + rin + tt + bc["min_at_RSS"] + bc["rss"]
    out["bend_zone_criterion"] = {"criterion": bc, "measured_3D": bz,
                                  "g_bend_budget": {"formula": "l0 %.2f + R_in %.2f + t %.2f + clearance %.2f + panel position RSS %.3f" % (l0, rin, tt, bc["min_at_RSS"], bc["rss"]),
                                                    "sum": round(budget, 3), "modelled_g_bend": G.g_bend, "limit_for_border": round(g_max, 3),
                                                    "border": G.border, "bezel": round(bezel, 2), "land_min": round(land_min, 3),
                                                    "land_min_note": "bead_edge %.1f + bead_w %.1f + bead_pocket_min %.1f to the break edge + land_break %.2f "
                                                                     "(the GF-2.0 budget used %.1f, i.e. A1 to the pocket face)" % (
                                                                         G.bead_edge, G.bead_w, float(G.bead_pocket_min or 1.0), float(G.land_break or 0.0), land_min_face),
                                                    "limit_for_border_with_land_to_face": round(G.border - bezel - land_min_face, 3),
                                                    "reserve_to_limit": round(g_max - budget, 3),
                                                    "modelled_g_bend_vs_budget": round(G.g_bend - budget, 3),
                                                    "modelled_g_bend_vs_limit": round(g_max - G.g_bend, 3),
                                                    "concept_position_term": 0.25}}
    if bz:
        need = {}
        for n, v in bz.items():
            slope = (v["RSS"] - v["WC_panel_only"]) / max(bc["wc"] - bc["rss"], 1e-9)
            need[n] = {"slope_per_mm": round(slope, 3),
                       "g_bend_for_0.45_at_WC_all_contributors": round(G.g_bend + (0.45 - v["WC"]) / slope, 3),
                       "g_bend_for_0.45_at_WC_panel_position_only": round(G.g_bend + (0.45 - v["WC_panel_only"]) / slope, 3),
                       "g_bend_for_0.45_at_RSS": round(G.g_bend + (0.45 - v["RSS"]) / slope, 3)}
        out["bend_zone_criterion"]["g_bend_needed_for_concept_0.45_at_WC"] = need
    # ---------------- 8. volume and mass
    fi = ctx.frame_info
    out["volume"] = {"volume_cm3": round(fi["volume_mm3"] / 1000, 3), "mass_g": round(fi["volume_mm3"] / 1000 * RHO, 1),
                     "density_g_cm3": RHO,
                     "params_as_modelled": G.raw.get("as_modelled_%s" % str(G.revision).split(" ")[0], {}).get("frame_volume_cm3"),
                     "prev": "%s %s" % (PR["tag"], PR.get("volume")), "v2": "55.06 cm3 / 74.9 g"}
    out["seconds"] = round(time.time() - t0, 1)
    return out


def markdown(calc, frame_info):
    Lm = []
    Lm.append("# Glass-front frame - calculations with section properties measured on the STEP\n")
    Lm.append("STEP: `%s` (%s, %d bytes, sha256 %s)\n" % (os.path.basename(frame_info["file"]), frame_info["mtime"],
                                                        frame_info["bytes"], frame_info["sha256"][:16]))
    Lm.append("Tags: [M] measured on the STEP, [C] calculated (grillage / formulae), [A] assumed.\n")
    pv = calc["port_validation"]
    Lm.append("Grillage: a copy of the concept's port (`grillage_port.py`); concept_calc.py is not imported or run. Validation against "
              "the GF-1.1 concept (S4, glass 3.0): %s vs %s mm at 50 N -> %s.\n" % (pv["w50_mm"], pv["concept_w50_mm"], "ok" if pv["ok"] else "MISMATCH"))
    Lm.append("## 1. Ring section properties [M]\n")
    Lm.append("| section | A mm2 | centroid Z | I mm4 | c mm | Z range |")
    Lm.append("|---|---|---|---|---|---|")
    for k, v in calc["sections"].items():
        if v.get("I_mm4") is None:
            Lm.append("| %s | - | - | - | - | - |" % k)
            continue
        Lm.append("| %s | %.1f | %.3f | %.0f | %.2f | %.2f .. %.2f |" % (k, v["A_mm2"], v["zc"], v["I_mm4"], v["c_mm"], v["z_range"][0], v["z_range"][1]))
    cs = calc["concept_sections_3.0"]
    Lm.append("\nConcept rectangles at glass 3.0 [C]: top %.0f, left %.0f, right %.0f, bottom channel %.0f, bottom bridge only %.0f mm4; "
              "measured / concept: %s\n" % (cs["channel"]["top"]["I"], cs["channel"]["left"]["I"], cs["channel"]["right"]["I"],
                                           cs["channel"]["bottom"]["I"], cs["bridge_bottom"]["I"], calc["measured_over_concept_I"]))
    Lm.append("## 2. Push (S4 / R4: 4 corner studs + VHB) [C]\n")
    Lm.append("| bottom | glass | I | load point | w 50 N mm | lip line 50 N | bottom edge 50 N | glass 250 N MPa | SF | ring 250 N | stud 250 N |")
    Lm.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in calc["grillage"]["rows"]:
        Lm.append("| %s | %.1f | %s | %s | %.4f | %.4f | %.4f | %.1f | %.2f | %.1f | %.0f |" % (
            r["bottom"], r["glass_t"], "meas." if r["I_source"].startswith("measured") else "concept", r["load_point"], r["w_50N_mm"],
            r["lip_line_50N_mm"], r["bottom_edge_50N_mm"], r["glass_250N_MPa"], r["glass_SF_250N"], r["ring_250N_MPa"], r["stud_250N_N"]))
    Lm.append("\n%s\n" % calc["grillage"]["note"])
    Lm.append("## 3. 0.5 J impact (concept method, estimates) [C]\n")
    Lm.append("| bottom bound / glass | glass g | window centre SF | bend-gap strip, whole border free SF | strip only SF |")
    Lm.append("|---|---|---|---|---|")
    for k, v in calc["impact_0p5J"].items():
        Lm.append("| %s | %.0f | %.2f | %.2f | %.2f |" % (k, v["glass_mass_g"], v["window_centre"]["SF"], v["bend_gap_strip_whole_border_free"]["SF"],
                                                     v["bend_gap_strip_only"]["SF"]))
    b = calc["bead"]
    Lm.append("\n## 4. Bead [C]\n")
    PR = calc.get("previous_release") or {}
    Lm.append("- area %.1f mm2 (params %s; %s %s); dead load %.2f N -> %.2f kPa; 250 N pull %.3f MPa mean" % (
        b["area_mm2"], b["params_bead_area"], PR.get("tag"), b.get("prev_area_mm2"), b["dead_load_glass_panel_N"], b["dead_load_kPa"], b["pull_250N_MPa"]))
    Lm.append("- bead corner radius from the glass centre %.2f (%s %s)\n" % (b["r_bead_corner_mm"], PR.get("tag"), b.get("prev_r_bead_corner_mm")))
    Lm.append("| case | d mm | ext. at t 0.73 | ext. at t 1.0 | allow class 50 t 0.73 | allow class 25 t 1.0 |")
    Lm.append("|---|---|---|---|---|---|")
    for s in b["shear"]:
        Lm.append("| %s | %.3f | %.1f %% | %.1f %% | %.3f | %.3f |" % (s["case"], s["d_mm"], 100 * s["eq_ext_t0.73"], 100 * s["eq_ext_t1.0"],
                                                                s["class50_t0.73_allow"], s["class25_t1.0_allow"]))
    if calc.get("gaps_table"):
        Lm.append("\n## 5. Gaps (STEP lip, params glass / cut-out; sides / corner min / diagonal) [M + C]\n")
        for tag, tt in calc["gaps_table"].items():
            Lm.append("| %s | %s |" % (tag, " | ".join(list(next(iter(tt.values())).keys()))))
            Lm.append("|---|%s" % "---|" * len(next(iter(tt.values()))))
            for tname, cs_ in tt.items():
                Lm.append("| %s | %s |" % (tname, " | ".join("%.3f / %.3f / %.3f" % (v["sides_min"], v["corners_min"], v["diagonal"]) for v in cs_.values())))
            Lm.append("")
    Lm.append("Formula (nominal per side), this release vs %s: %s\n" % (PR.get("tag"), json.dumps(calc["gaps_formula"])))
    tf = calc["tape_fasteners"]
    Lm.append("## 6. Tape and fasteners [C]\n")
    Lm.append("- tape %.1f mm2 (%s %s); module %.2f N -> %.2f kPa; 250 N -> %.1f kPa; thermal shear %s %% of the 1.0 gap (50 / 70 ppm)" % (
        tf["tape_area_mm2"], PR.get("tag"), tf.get("prev_tape_area_mm2"), tf["module_dead_load_N"], tf["tape_dead_load_kPa"], tf["tape_250N_kPa"],
        tf["tape_thermal_shear_pct_50_70"]))
    Lm.append("- studs at r %.2f: radial move %s mm (50 / 70 ppm, +70 / +50 C) vs float %.2f; stud reaction at 250 N max %.0f N; M4 washer at 500 N %s MPa\n" % (
        tf["stud_r_from_glass_centre"], tf["stud_radial_move_mm_50_70"], tf["stud_float_along_slot_mm"], tf["stud_reaction_250N_max_N"], tf["washer_M4_500N_MPa"]))
    bzc = calc.get("bend_zone_criterion")
    if bzc and bzc.get("measured_3D"):
        c = bzc["criterion"]
        gb = bzc["g_bend_budget"]
        Lm.append("## 7. Bend zone (nose, pocket face, break): criterion and measured clearances [M + C + A]\n")
        Lm.append("Criterion (params `tail_clearance_criteria.bend_zone`): >= %.2f with the panel at its RSS position "
                  "(+%.3f), > %.1f at the worst case (panel +%.2f, exit Z +-%.1f, tail +%.2f); the concept's intent: >= 0.45 at the full "
                  "worst case. Panel position contributors: %s.\n" % (
                      c["min_at_RSS"], c["rss"], c["min_at_WC"], c["wc"], c["exit_Z_tol"], c["tail_t_tol"],
                      (calc.get("bend_gap_stack") or {}).get("CTP", {}).get("panel_position_contributors_mm")))
        Lm.append("| tail | nominal | panel at RSS | WC (all) | WC (panel position only) | WC with print-to-edge +-0.1 | feature |")
        Lm.append("|---|---|---|---|---|---|---|")
        for n, v in bzc["measured_3D"].items():
            Lm.append("| %s | %.3f | %.3f | %.3f | %.3f | %.3f | %s |" % (n, v["nominal"], v["RSS"], v["WC"], v["WC_panel_only"], v["WC_print_0.1"], v["feature"]))
        Lm.append("\ng_bend budget (concept form): %s = **%.3f** (modelled %.2f, %+.3f); border %.1f holds up to g_bend %.3f (bezel %.2f + land %.2f = "
                  "%s) -> reserve of the budget **%.3f**, of the modelled g_bend %.3f (with the land to the face, as at GF-2.0: limit %.3f).\n" % (
                      gb["formula"], gb["sum"], gb["modelled_g_bend"], gb["modelled_g_bend_vs_budget"], gb["border"], gb["limit_for_border"],
                      gb["bezel"], gb["land_min"], gb["land_min_note"], gb["reserve_to_limit"], gb["modelled_g_bend_vs_limit"],
                      gb["limit_for_border_with_land_to_face"]))
        if bzc.get("g_bend_needed_for_concept_0.45_at_WC"):
            Lm.append("g_bend at which the bend-zone clearance would be exactly 0.45 (linear, slope from the RSS / panel-WC cases): %s\n" % json.dumps(
                bzc["g_bend_needed_for_concept_0.45_at_WC"]))
    if calc.get("bend_gap_stack"):
        Lm.append("## 7b. Bend-gap tolerance stack, linear estimate from the panel +0.35 case [C + A]\n")
        for n, s in calc["bend_gap_stack"].items():
            Lm.append("- %s: nominal %.3f to the bridge; sensitivity %.2f per mm of panel shift; panel position WC %.2f / RSS %.2f "
                      "(concept 0.35 / 0.25); exit Z +-0.3 costs %.3f -> clearance WC %.3f, RSS %.3f (concept budget %.3f)" % (
                          n, s["nominal_min_to_bridge_mm"], s["sensitivity_per_mm_panel_shift"], s["panel_position_WC"], s["panel_position_RSS"],
                          s["exit_Z_+-0.3_loss"], s["clearance_WC_all_contributors"], s["clearance_RSS"], s["clearance_concept_budget (panel 0.35 WC + tail 0.05)"]))
        Lm.append("")
    v = calc["volume"]
    Lm.append("## 8. Volume and mass [M]\n")
    Lm.append("- STEP volume **%.3f cm3**, mass **%.1f g** at %.2f g/cm3 (params as modelled %s; %s; v2 %s)\n" % (
        v["volume_cm3"], v["mass_g"], v["density_g_cm3"], v["params_as_modelled"], v.get("prev"), v["v2"]))
    return "\n".join(Lm)


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    _ = ctx.frame
    c = run(ctx)
    C.dump(c, ctx.out("calc.json"))
    open(ctx.out("calc.md"), "w", encoding="utf8").write(markdown(c, ctx.frame_info))
    print(markdown(c, ctx.frame_info))
