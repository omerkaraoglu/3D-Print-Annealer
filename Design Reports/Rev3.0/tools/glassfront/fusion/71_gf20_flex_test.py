"""71 - stage 4 (GF-2.0) flex test: script 90 extended by the GF-2.0 driving values. Each case sets its parameters,
recomputes the WHOLE design, records timeline health (all components), frame body count / lumps / volume / faces /
bbox, the derived levels and the unfilleted plane/cone concave roots by group; then EVERY parameter returns to its
default (checked) and the default state is recomputed last.
Cases: glass_t 2.0 / 4.0 / 1.1 (level snap), t_sheet 0.8 / 1.5, t_opt 1.0, border 17.5, border 20.5,
border 20.5 + g_bend 5.1 (double-sided tail case of concept_gf2 2.1), default.
Module global TAG (runner may set it). Writes %TEMP%\\rev3_glassfront\\gf20\\flex_<TAG>.json."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
DUMP = globals().get("DUMP") or "gf20"          # stage-5 runs set DUMP = "gf21" (dump sub-folder)

TAG = globals().get("TAG") or "gf20"
DEFAULTS = globals().get("DEFAULTS") or {"glass_t": "3.0 mm", "t_sheet": "1.0 mm", "t_opt": "0.3 mm", "border": "18.5 mm", "g_bend": "3.0 mm"}
CASES = [("glass_t 2.0", {"glass_t": "2.0 mm"}), ("glass_t 4.0", {"glass_t": "4.0 mm"}),
         ("glass_t 1.1 (snap)", {"glass_t": "1.1 mm"}), ("t_sheet 0.8", {"t_sheet": "0.8 mm"}),
         ("t_sheet 1.5", {"t_sheet": "1.5 mm"}), ("t_opt 1.0", {"t_opt": "1.0 mm"}),
         ("border 17.5", {"border": "17.5 mm"}), ("border 20.5", {"border": "20.5 mm"}),
         ("border 20.5 + g_bend 5.1", {"border": "20.5 mm", "g_bend": "5.1 mm"}), ("default", {})]
CASES = globals().get("CASES_OVERRIDE") or CASES
LEVELS = ["Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_LAND", "Z_PIP_TOP",
          "Z_LANDPLATE_BACK", "Z_STEPWALL_BACK", "Z_TUBE_TOP", "Z_TRIB_TOP", "snap_keep", "glass_y1", "bend_y1",
          "fl_y1", "f_y1"]


def state(name):
    d = L.des()
    d.computeAll()
    n, bad = L.timeline_health()
    c = L.comp()
    b = L.body()
    rec = {"case": name, "params": {k: d.userParameters.itemByName(k).expression for k in DEFAULTS},
           "levels": {k: round(L.P(k), 4) for k in LEVELS},
           "timeline_count": n, "timeline_unhealthy": bad, "healthy": not bad,
           "bodies_in_component": c.bRepBodies.count, "bodies_in_design": L.bodies_in_design()}
    if b is not None:
        rec.update(L.body_dict(b))
        roots = {}
        for g, e, m, z, o in L.root_edges(0.9):
            roots[g] = roots.get(g, 0) + 1
        rec["unfilleted_concave_roots_by_group"] = roots
    return rec


def run(_context: str):
    L.check_doc()
    L.log("=== 71 flex %s start" % TAG)
    ups = L.des().userParameters
    out = []
    try:
        for name, sets in CASES:
            for k, v in DEFAULTS.items():
                ups.itemByName(k).expression = sets.get(k, v)
            rec = state(name)
            out.append(rec)
            L.log("71 %s: healthy %s, bodies %d, %s" % (name, rec["healthy"], rec["bodies_in_component"],
                                                       L.body_stats()))
    finally:
        for k, v in DEFAULTS.items():
            ups.itemByName(k).expression = v
        L.des().computeAll()
    for k, v in DEFAULTS.items():
        if ups.itemByName(k).expression.replace(" ", "") != v.replace(" ", ""):
            raise RuntimeError("parameter %s not back at its default" % k)
    p = L.dump(out, DUMP + "/flex_%s.json" % TAG)
    for r in out:
        print(r["case"], "healthy" if r["healthy"] else "UNHEALTHY %s" % r["timeline_unhealthy"],
              r["bodies_in_component"], r.get("lumps"), r.get("volume_cm3"), r.get("faces"),
              r.get("bbox_abs", {}).get("y_down"), r.get("unfilleted_concave_roots_by_group"))
    print(p)
