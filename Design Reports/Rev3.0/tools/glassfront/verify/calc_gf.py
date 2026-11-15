"""E. Numbers the concept relies on, measured on the STEP: ring section properties (mid-top, mid-side, mid-bottom,
near a corner; I about the in-plane axis along the edge through the section centroid, as concept_calc.ring_section
does), the concept's push grillage re-run with the measured I, bead area, volume and mass.

  <venv>\\Scripts\\python.exe calc_gf.py [--frame f.step]

The grillage is driven by executing concept_calc.py's own source up to (not including) its section 8 in a private
namespace (that part only reads files; its section 9, which writes the master params file, is never executed), then
replacing SEC[glass_t]['I'] / ['c'] by the measured values and calling its grillage() again.
Output: the "calc" dict (calc.json) and calc.md.
"""
import contextlib
import io
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

RHO = 1.36      # g/cm3 PA6-GF30 FR (v2 value)


def face_props(faces, axis):
    """area, centroid Z and I about the axis through the centroid parallel to the section plane's horizontal
    direction: integral of (z - zc)^2 dA; plus the in-plane coordinate range. faces lie in the plane x = c (axis 'x')
    or y = c (axis 'y')."""
    A = Sz = 0.0
    parts = []
    for f in faces:
        g = GProp_GProps()
        BRepGProp.SurfaceProperties_s(f.wrapped, g)
        a = g.Mass()
        c = g.CentreOfMass()
        M = g.MatrixOfInertia()       # about the face's centre of mass
        # for a face in the plane x = const: Ixx = int(y^2 + z^2), Iyy = int(x^2 + z^2) = int z^2 (x = 0 about the centroid)
        # for a face in y = const: Ixx = int(y^2 + z^2) = int z^2
        Izz_own = M.Value(2, 2) if axis == "x" else M.Value(1, 1)
        parts.append((a, c.Z(), Izz_own))
        A += a
        Sz += a * c.Z()
    zc = Sz / A
    I = sum(Io + a * (z - zc) ** 2 for a, z, Io in parts)
    return A, zc, I


def diag_section(fr, origin_abs, u_abs, t_keep):
    """section by the vertical plane through origin_abs containing the plan direction u_abs (abs, y down); I about
    the in-plane horizontal axis through the centroid = a.M.a with a = the in-plane horizontal unit vector"""
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


def ring_section(fr, axis, value, keep):
    """faces of the section by x = value (axis 'x', keep(y_abs_lo, y_abs_hi)) or y = value"""
    sec = C.plane_section(fr, axis, value if axis == "x" else -value)
    faces = []
    for f in sec.Faces():
        bb = f.BoundingBox()
        lo, hi = (-bb.ymax, -bb.ymin) if axis == "x" else (bb.xmin, bb.xmax)
        if keep(lo, hi):
            faces.append(f)
    if not faces:
        return {"A_mm2": None, "zc": None, "I_mm4": None, "faces": 0, "z_range": None, "c_mm": None,
                "note": "no section face passed the filter"}
    A, zc, I = face_props(faces, axis)
    zmin = min(f.BoundingBox().zmin for f in faces)
    zmax = max(f.BoundingBox().zmax for f in faces)
    return {"A_mm2": round(A, 2), "zc": round(zc, 3), "I_mm4": round(I, 1), "faces": len(faces),
            "z_range": [round(zmin, 3), round(zmax, 3)], "c_mm": round(max(abs(zmin - zc), abs(zmax - zc)), 3)}


def concept_namespace():
    src = open(C.CONCEPT_CALC, encoding="utf8").read()
    cut = src.index('hdr("8. GLASS STRESS')
    ns = {"__file__": C.CONCEPT_CALC, "__name__": "concept_calc_partial"}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(compile(src[:cut], C.CONCEPT_CALC, "exec"), ns)
    return ns, buf.getvalue()


def run(ctx, log=C.log):
    t0 = time.time()
    G, fr = ctx.G, ctx.frame
    L = G.L
    out = {}
    # ---- choose clean section positions (away from ribs, bosses, pips, fasteners)
    secs = {
        "mid-top (x 80)": ("x", 80.0, lambda lo, hi: hi < 40),
        "mid-top through F5 (x 103.85)": ("x", 103.85, lambda lo, hi: hi < 40),
        "mid-side left (y 60)": ("y", 60.0, lambda lo, hi: hi < 40),
        "mid-side right (y 60)": ("y", 60.0, lambda lo, hi: lo > 170),
        "mid-bottom over the tail pocket (x 80), beam + land plate + flange": ("x", 80.0, lambda lo, hi: lo > 140),
        "mid-bottom (x 80) incl. the free shelf strip": ("x", 80.0, lambda lo, hi: lo > 110),
        "near the top-left corner (x 23, past the corner arc and the side shelf)": ("x", 23.0, lambda lo, hi: hi < 40),
        "bottom beside the tail pocket, corner cell (x 25)": ("x", 25.0, lambda lo, hi: lo > 110),
    }
    res = {}
    for name, (ax, v, keep) in secs.items():
        res[name] = ring_section(fr, ax, v, keep)
    gcx, gcy = G.GLASS[0] + G.GLASS[4], G.GLASS[2] + G.GLASS[4]
    u = G.slot_axis("F1")
    res["corner apex: diagonal plane through F1 and the glass corner (incl. pad, tube, rib)"] = diag_section(
        fr, G.fxy("F1"), u, (-12.0, 32.0))
    for name in res:
        log("    %-62s A %7.1f  zc %7.3f  I %7.0f mm4" % (name[:62], res[name]["A_mm2"], res[name]["zc"], res[name]["I_mm4"]))
    out["sections"] = res
    # ---- concept grillage with the measured I
    log("[E] concept grillage (concept_calc.py sections 1-7 executed read-only)")
    ns, txt = concept_namespace()
    tg = G.glass_t
    sec0 = dict(ns["SEC"][tg])
    out["concept_ring_section"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in sec0.items() if k != "rects"}
    loads = ns["LOADS"]
    S4 = ns["S4"]
    base = ns["grillage"](tg, supports=S4, vhb=True, loads=[p for _, p in loads])
    # the smallest measured I all round (the F5 / F7 slot section governs in GF-1.1), applied to the whole ring (conservative)
    Imeas = {"min of mid-top / F5 slot / mid-side / near corner": min(res["mid-top (x 80)"]["I_mm4"], res["mid-side left (y 60)"]["I_mm4"],
                                                         res["mid-side right (y 60)"]["I_mm4"],
                                                         res["near the top-left corner (x 23, past the corner arc and the side shelf)"]["I_mm4"],
                                                         res["mid-top through F5 (x 103.85)"]["I_mm4"]),
             "mid-top (x 80)": res["mid-top (x 80)"]["I_mm4"], "mid-side left (y 60)": res["mid-side left (y 60)"]["I_mm4"]}
    runs = {"concept (I %.0f)" % sec0["I"]: base}
    cvals = {"concept (I %.0f)" % sec0["I"]: sec0["c"]}
    for lab, Iv in Imeas.items():
        r = res["mid-top (x 80)"] if lab.startswith("mid-top") else res["mid-side left (y 60)"]
        ns["SEC"][tg] = dict(sec0, I=Iv, c=max(sec0["c"], r["c_mm"]))
        runs["measured %s (I %.0f)" % (lab, Iv)] = ns["grillage"](tg, supports=S4, vhb=True, loads=[p for _, p in loads])
        cvals["measured %s (I %.0f)" % (lab, Iv)] = ns["SEC"][tg]["c"]
    ns["SEC"][tg] = sec0
    tab = []
    for lab, rr in runs.items():
        for (ln, _), r in zip(loads, rr):
            tab.append({"run": lab, "load_point": ln, "w_5N_um": round(r["w"] * 5000, 1), "w_50N_mm": round(r["w"] * 50, 4),
                        "lip_line_50N_mm": round(r["w_perim"] * 50, 4), "glass_250N_MPa": round(r["sig_g"] * 250, 1),
                        "ring_250N_MPa": round(r["sig_r"] * 250, 1), "stud_250N_N": round(r["R"] * 250, 0)})
    out["grillage"] = {"glass_t": tg, "config": "S4/R4: 4 corner studs + VHB (concept 5.4 recommended row)", "rows": tab,
                       "c_used": cvals,
                       "note": "only I (and the outer-fibre distance c) of the ring replaced; J, the corner links, VHB and E as the concept"}
    # ---- bead area (from the params geometry) and land available on the STEP
    gx0, gx1, gy0, gy1, gR = G.GLASS
    def rr_area(i):
        w, h, r = (gx1 - gx0) - 2 * i, (gy1 - gy0) - 2 * i, max(gR - i, 0.0)
        return w * h - (4 - math.pi) * r * r
    bead_area = rr_area(G.bead_edge) - rr_area(G.bead_edge + G.bead_w)
    out["bead"] = {"area_mm2": round(bead_area, 1), "concept_mm2": 2510.0, "glass_R": G.GLASS[4],
                   "pip_area_inside_mm2": round(8 * math.pi * (G.pip_d / 2) ** 2, 2),
                   "land_face_area_step_mm2": round(sum(f.Area() for f in C.faces_at_z(fr, L["Z_LAND"], -1, tol=0.005)), 1)}
    # ---- volume and mass
    fi = ctx.frame_info
    out["volume"] = {"volume_cm3": round(fi["volume_mm3"] / 1000, 3), "mass_g": round(fi["volume_mm3"] / 1000 * RHO, 1),
                     "density_g_cm3": RHO, "concept_estimate": "~70 cm3 / ~95 g", "v2": "55.06 cm3 / 74.9 g"}
    out["seconds"] = round(time.time() - t0, 1)
    return out


def markdown(calc, frame_info):
    L = []
    L.append("# Glass-front frame - numbers the concept relies on, measured on the STEP\n")
    L.append("STEP: `%s` (%s, %d bytes, sha256 %s)\n" % (os.path.basename(frame_info["file"]), frame_info["mtime"],
                                                       frame_info["bytes"], frame_info["sha256"][:16]))
    L.append("## Ring section properties (I about the in-plane axis along the edge, through the section centroid)\n")
    L.append("Concept 5.4 grillage: concept.md quotes I = 1174 mm4 (first-draft value); concept_calc.py with the GF-1.0 "
             "parameters computes I = %.0f mm4 (A %.1f mm2, centroid Z %.2f, c %.2f) on the glass edge for glass %.1f - "
             "that is the value its grillage uses and the reference below.\n" % (
        calc["concept_ring_section"]["I"], calc["concept_ring_section"]["A"], calc["concept_ring_section"]["zc"],
        calc["concept_ring_section"]["c"], calc["grillage"]["glass_t"]))
    L.append("| section | A mm2 | centroid Z | I mm4 | I / concept | c mm | Z range |")
    L.append("|---|---|---|---|---|---|---|")
    Ic = calc["concept_ring_section"]["I"]
    for k, v in calc["sections"].items():
        L.append("| %s | %.1f | %.3f | %.0f | %.2f | %.2f | %.2f .. %.2f |" % (k, v["A_mm2"], v["zc"], v["I_mm4"], v["I_mm4"] / Ic,
                                                                        v["c_mm"], v["z_range"][0], v["z_range"][1]))
    L.append("\n## Push grillage (concept_calc.grillage, S4/R4 + VHB, glass %.1f) with the measured I\n" % calc["grillage"]["glass_t"])
    L.append("| run | load point | w @ 5 N um | w @ 50 N mm | lip line @ 50 N mm | glass @ 250 N MPa | ring @ 250 N MPa | stud @ 250 N |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in calc["grillage"]["rows"]:
        L.append("| %s | %s | %.1f | %.4f | %.4f | %.1f | %.1f | %.0f |" % (r["run"], r["load_point"], r["w_5N_um"], r["w_50N_mm"],
                                                                          r["lip_line_50N_mm"], r["glass_250N_MPa"], r["ring_250N_MPa"], r["stud_250N_N"]))
    L.append("\n%s\n" % calc["grillage"]["note"])
    b = calc["bead"]
    L.append("## Bead and land\n")
    L.append("- bead ring 0.9..4.9 inside the glass edge (R%.2f glass corners): **%.1f mm2** (concept 2510)" % (b.get("glass_R", 6.0), b["area_mm2"]))
    L.append("- 8 pips inside the bead line: %.2f mm2 of pip footprint" % b["pip_area_inside_mm2"])
    L.append("- land face on the STEP (Z_LAND): %.1f mm2\n" % b["land_face_area_step_mm2"])
    v = calc["volume"]
    L.append("## Volume and mass\n")
    L.append("- STEP volume **%.3f cm3**, mass **%.1f g** at %.2f g/cm3 (concept estimate %s; v2 %s)\n" % (
        v["volume_cm3"], v["mass_g"], v["density_g_cm3"], v["concept_estimate"], v["v2"]))
    return "\n".join(L)


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    _ = ctx.frame
    c = run(ctx)
    C.dump(c, ctx.out("calc.json"))
    open(ctx.out("calc.md"), "w", encoding="utf8").write(markdown(c, ctx.frame_info))
    print(markdown(c, ctx.frame_info))
