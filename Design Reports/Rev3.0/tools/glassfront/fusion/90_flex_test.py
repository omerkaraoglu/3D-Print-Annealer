"""90 - flex test (mandatory, brief requirement 3): set each case's parameters, recompute, record timeline health,
body count, lumps, volume, faces, bbox and the derived levels; then return EVERY parameter to its default.
Cases: glass_t 2.0, 4.0, 1.1 (level snap is automatic: snap_keep), t_sheet 0.8, 1.5, t_opt 1.0, then default.
Writes scratchpad flex_<TAG>.json. TAG is the module global below.
Expects: the model built (any stage). Leaves: all parameters at their defaults (checked)."""
import importlib
import json
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

TAG = "final"
DEFAULTS = {"glass_t": "3.0 mm", "t_sheet": "1.0 mm", "t_opt": "0.3 mm"}
CASES = [("glass_t 2.0", {"glass_t": "2.0 mm"}), ("glass_t 4.0", {"glass_t": "4.0 mm"}),
         ("glass_t 1.1 (snap)", {"glass_t": "1.1 mm"}), ("t_sheet 0.8", {"t_sheet": "0.8 mm"}),
         ("t_sheet 1.5", {"t_sheet": "1.5 mm"}), ("t_opt 1.0", {"t_opt": "1.0 mm"}), ("default (glass 3.0)", {})]
LEVELS = ["Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_LAND", "Z_PIP_TOP",
          "Z_LANDPLATE_BACK", "Z_STEPWALL_BACK", "Z_TUBE_TOP", "Z_TRIB_TOP", "snap_keep"]


def state(name):
    d = L.des()
    d.computeAll()
    n, bad = L.timeline_health()
    c = L.comp()
    bodies = [c.bRepBodies.item(i) for i in range(c.bRepBodies.count)]
    b = L.body()
    rec = {"case": name, "params": {k: d.userParameters.itemByName(k).expression for k in DEFAULTS},
           "levels": {k: round(L.P(k), 4) for k in LEVELS},
           "timeline_count": n, "timeline_unhealthy": bad, "healthy": not bad,
           "bodies_in_component": len(bodies), "bodies_in_design": L.bodies_in_design()}
    if b is not None:
        rec.update(L.body_dict(b))
        roots = {}
        for g, e, m, z, o in L.root_edges(0.9):
            roots[g] = roots.get(g, 0) + 1
        rec["unfilleted_concave_roots_by_group"] = roots     # plane/cone roots only (fillet coverage per state)
    return rec


def run(_context: str):
    L.check_doc()
    L.log("=== 90 flex %s start" % TAG)
    ups = L.des().userParameters
    out = []
    for name, sets in CASES:
        for k, v in DEFAULTS.items():
            ups.itemByName(k).expression = sets.get(k, v)
        rec = state(name)
        out.append(rec)
        L.log("90 %s: healthy %s, bodies %d, %s" % (name, rec["healthy"], rec["bodies_in_component"],
                                                   L.body_stats()))
    for k, v in DEFAULTS.items():
        if ups.itemByName(k).expression.replace(" ", "") != v.replace(" ", ""):
            raise RuntimeError("parameter %s not back at its default" % k)
    p = L.dump(out, "flex_%s.json" % TAG)
    for r in out:
        print(r["case"], "healthy" if r["healthy"] else "UNHEALTHY %s" % r["timeline_unhealthy"],
              r["bodies_in_component"], r.get("lumps"), r.get("volume_cm3"), r.get("faces"),
              r.get("bbox_abs", {}).get("z"), r.get("unfilleted_concave_roots_by_group"))
    print(p)
