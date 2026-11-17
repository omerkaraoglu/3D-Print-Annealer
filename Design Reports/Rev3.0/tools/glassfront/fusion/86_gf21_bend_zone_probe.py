"""86 - stage 5 (GF-2.1), derivation probe (parameters set temporarily, then restored; nothing saved):
for each (border, g_bend) in CASES the whole design is recomputed and, CAD-side,
  * tail -> frame minimum (both tails; the closest feature is the bridge nose) for the tail at its nominal position,
    moved towards the bridge by the panel-position tolerance 0.308 (RSS) and 0.60 (WC), and an approximate full worst
    case (+0.60 in y, exit height +-0.3 as a rigid Z shift of the tail, tail 0.35 instead of 0.30 = 0.025 off the
    measured distance on the nose side) - tail_clearance_criteria.bend_zone of the master
  * bead inner edge -> land break edge on the land plane (Z_LAND) and at Z_LAND + 0.01 (the verification's probe), and
    -> bridge pocket face, from rays through the frame body at x 60 and x 130 (bead edge = glass_y1 - bead_edge -
    bead_w, the modelled bead body's inner edge, checked)
Writes gf21/bend_zone_probe.json. Restores border / g_bend to their values before the run (checked)."""
import importlib
import json
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
import gfasm as A
importlib.reload(A)

TB = adsk.fusion.TemporaryBRepManager.get()
CASES = globals().get("CASES") or [(18.5, 3.00), (19.0, 3.23), (19.0, 3.20), (19.0, 3.26)]
OUT = os.path.join(L.SCR, "gf21")


def moved(b, dy_abs, dz=0.0):
    t = TB.copy(b)
    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(0, -dy_abs / 10.0, dz / 10.0)
    TB.transform(t, m)
    return t


def exit_dist(b, x, y0, z, uy, smax=3.0, tol=0.0002):
    """from (x, y0, z) INSIDE body b along y direction uy: distance to the first point outside"""
    def inside(s):
        p = adsk.core.Point3D.create(x / 10.0, -(y0 + s * uy) / 10.0, z / 10.0)
        return b.pointContainment(p) == adsk.fusion.PointContainment.PointInsidePointContainment
    if not inside(0.0):
        return None
    s = 0.0
    while s <= smax and inside(s):
        s += 0.01
    lo, hi = s - 0.01, s
    while hi - lo > tol:
        m = (lo + hi) / 2
        if inside(m):
            lo = m
        else:
            hi = m
    return round((lo + hi) / 2, 4)


def measure(fr, tails):
    res = {"params": {k: round(L.P(k), 4) for k in ("border", "g_bend", "glass_y1", "bend_y1", "land_break")}}
    zl = L.P("Z_LAND")
    yb = L.P("glass_y1") - L.P("bead_edge") - L.P("bead_w")
    res["bead_inner_edge_y"] = round(yb, 4)
    bead = A.part("Bead", "Bead (4.0 x t_bond)")
    res["bead_body_inner_edge_y_max_over_tail_span"] = None
    bb = []
    for x in (60.0, 130.0):
        d0 = exit_dist(fr, x, yb, zl + 0.0005, -1)          # on the land plane (just inside the material)
        d1 = exit_dist(fr, x, yb, zl + 0.01, -1)
        dface = exit_dist(fr, x, yb, zl + L.P("land_break") + 0.05, -1)
        bb.append({"x": x, "to_break_edge_land_plane": d0, "to_break_at_Z_LAND+0.01": d1, "to_pocket_face_above_break": dface})
    res["bead_to_break"] = bb
    res["bead_to_break_formula_land_plane"] = round(yb - L.P("bend_y1") - L.P("land_break"), 4)
    res["bead_to_face_formula"] = round(yb - L.P("bend_y1"), 4)
    res["tails"] = {}
    for nm, t in tails:
        e = {}
        for key, dy, dz, dt in (("nominal", 0, 0, 0), ("panel_RSS_0.308", 0.308, 0, 0), ("panel_WC_0.60", 0.60, 0, 0),
                                ("full_WC_exitZ+0.3", 0.60, 0.3, 0.025), ("full_WC_exitZ-0.3", 0.60, -0.3, 0.025)):
            tt = moved(t, dy, dz) if (dy or dz) else t
            d, p1, p2 = L.min_dist_mm(tt, fr)
            e[key] = {"d_mm": round(d - dt, 4), "p_frame": L.pt_abs(p2)}
        e["full_WC_min"] = min(e["full_WC_exitZ+0.3"]["d_mm"], e["full_WC_exitZ-0.3"]["d_mm"])
        res["tails"][nm[:3]] = e
    return res


def run(_context: str):
    d = L.check_doc()
    ups = d.userParameters
    keep = {k: ups.itemByName(k).expression for k in ("border", "g_bend")}
    fr = A.frame()
    tails = A.tails()
    out = []
    try:
        for border, gb in CASES:
            ups.itemByName("border").expression = "%.3f mm" % border
            ups.itemByName("g_bend").expression = "%.3f mm" % gb
            d.computeAll()
            n, bad = L.timeline_health()
            r = measure(A.frame(), tails)
            r["healthy"] = not bad
            out.append(r)
    finally:
        for k, v in keep.items():
            ups.itemByName(k).expression = v
        d.computeAll()
    for k, v in keep.items():
        if ups.itemByName(k).expression != v:
            raise RuntimeError("not restored " + k)
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, globals().get("OUTNAME") or "bend_zone_probe.json"), "w"), indent=1)
    for r in out:
        print(r["params"], "healthy", r["healthy"], "bead->break", r["bead_to_break_formula_land_plane"],
              [(q["x"], q["to_break_edge_land_plane"], q["to_break_at_Z_LAND+0.01"], q["to_pocket_face_above_break"])
               for q in r["bead_to_break"]])
        for nm, e in r["tails"].items():
            print("   ", nm, {k: v["d_mm"] for k, v in e.items() if isinstance(v, dict)}, "full WC", e["full_WC_min"])
