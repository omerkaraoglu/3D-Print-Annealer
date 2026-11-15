"""33 - stage 2, Part A: per flex case (as 90), the sliver rule on every face (area < 0.5 mm2 or 2A/P < 0.3) split
into design faces (plane / cone / cylinder) and fillet blends (sphere / torus / NURBS), the faces of the two rule
fillets and the edge-set cell fillet, and the faces near the H6 / H7 cell corners; parameters restored to defaults.
Writes scratchpad flex_slivers_partA.json."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

DEFAULTS = {"glass_t": "3.0 mm", "t_sheet": "1.0 mm", "t_opt": "0.3 mm"}
CASES = [("glass_t 2.0", {"glass_t": "2.0 mm"}), ("glass_t 4.0", {"glass_t": "4.0 mm"}),
         ("glass_t 1.1 (snap)", {"glass_t": "1.1 mm"}), ("t_sheet 0.8", {"t_sheet": "0.8 mm"}),
         ("t_sheet 1.5", {"t_sheet": "1.5 mm"}), ("t_opt 1.0", {"t_opt": "1.0 mm"}), ("default (glass 3.0)", {})]
FILLETS = ["Root fillets R0.5 - wall + step wall to plates (rule)",
           "Root fillets R0.5 - fastener tubes + tube ribs (rule)",
           "Root fillets R0.5 - corner cells + cell ribs + cell bosses"]
DESIGN = (adsk.core.SurfaceTypes.PlaneSurfaceType, adsk.core.SurfaceTypes.ConeSurfaceType,
          adsk.core.SurfaceTypes.CylinderSurfaceType)


def state(name):
    d = L.des()
    d.computeAll()
    b = L.body()
    n, bad = L.timeline_health()
    sl_design, sl_blend, corner = [], 0, []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        A = f.area * 100
        Pm = sum(f.edges.item(k).length for k in range(f.edges.count)) * 10
        r2 = 2 * A / Pm if Pm else 0
        c = f.centroid
        x, y = c.x * 10, -c.y * 10
        st = f.geometry.surfaceType
        if A < 0.5 or r2 < 0.3:
            if st in DESIGN:
                sl_design.append({"i": i, "type": st, "area": round(A, 4), "2a_p": round(r2, 4),
                                  "c": [round(x, 3), round(y, 3), round(c.z * 10, 3)]})
            else:
                sl_blend += 1
        for h in ("h6", "h7"):
            if math.hypot(x - L.P(h + "_x"), y - L.P(h + "_y")) < 7.5 and L.P("Z_LANDPLATE_BACK") - 0.01 < c.z * 10 < 0.01:
                corner.append({"h": h, "type": st, "area": round(A, 3), "2a_p": round(r2, 3)})
    fil = {}
    for nm in FILLETS:
        f = L.feature(nm)
        fil[nm] = f.faces.count if f else None
    return {"case": name, "healthy": not bad, "unhealthy": bad, "faces": b.faces.count, "lumps": b.lumps.count,
            "volume_cm3": round(b.volume, 4), "Z_LANDPLATE_BACK": L.P("Z_LANDPLATE_BACK"),
            "h6_fill_y": round(L.P("h6_fill_y"), 4), "design_face_slivers": sl_design, "blend_slivers": sl_blend,
            "fillet_faces": fil, "cell_corner_min_2a_p_design": min(
                [c["2a_p"] for c in corner if c["type"] in DESIGN] or [None]),
            "cell_corner_faces": len(corner)}


def run(_context: str):
    L.check_doc()
    ups = L.des().userParameters
    out = []
    for name, sets in CASES:
        for k, v in DEFAULTS.items():
            ups.itemByName(k).expression = sets.get(k, v)
        out.append(state(name))
    for k, v in DEFAULTS.items():
        if ups.itemByName(k).expression.replace(" ", "") != v.replace(" ", ""):
            raise RuntimeError("parameter %s not back at its default" % k)
    L.dump(out, "flex_slivers_partA.json")
    for r in out:
        print(r["case"], "healthy" if r["healthy"] else r["unhealthy"], r["faces"], r["volume_cm3"],
              "h6_fill_y", r["h6_fill_y"], "design slivers", r["design_face_slivers"], "blend slivers",
              r["blend_slivers"], "fillet faces", list(r["fillet_faces"].values()), "corner min 2A/P design",
              r["cell_corner_min_2a_p_design"])
