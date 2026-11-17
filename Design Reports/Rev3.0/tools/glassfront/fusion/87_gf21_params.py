"""87 - stage 5 (GF-2.1): the rebuild is driven by the user parameters only (master gf21_params_update.py):
  border 18.5 -> 19.0, g_bend 3.00 -> 3.23 (bend_y1 122.23, bottom land 6.26),
  logo_cy = ( pw_y1 + 1 mm + glass_y1 - 2.5 mm ) / 2 (zone centred between window + 1.0 and glass edge - 2.5: 118.24;
  was the border centre), and the value comments that quote numbers. Everything else follows (flex-tested at GF-2.0
  for border 17.5 / 20.5 and g_bend 5.1). The tail solids (70) are a fixed route and are NOT changed.
Then: health, frame body, key values. Refuses unless border is 18.5 (runs once)."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

G = "GF-2.1: "
CHANGE = [
    ("border", "19.0 mm", G + "print-window edge -> glass edge on ALL FOUR sides (owner decision; GF-2.0 18.5); the one driving "
     "value of the glass outline; bottom: bezel 9.51 + g_bend 3.23 + land 6.26"),
    ("g_bend", "3.23 mm", G + "DRIVING bend gap: panel bottom edge -> bridge pocket face over the tail span (122.23 at Z_LAND); "
     "3.23 = smallest 0.01 step with CTP tail -> nose >= 0.45 at the full worst case (GF-2.0 3.00: 0.239)"),
    ("logo_cy", "( pw_y1 + 1 mm + glass_y1 - 2.5 mm ) / 2", G + "logo zone centre y, centred between window y1 + 1.0 and "
     "glass y1 - 2.5 (118.24)"),
    ("glass_x0", None, "glass left (8.11)"), ("glass_x1", None, "glass right (199.59)"), ("glass_y0", None, "glass top (5.17)"),
    ("glass_y1", None, G + "glass bottom edge abs y = pw_y1 + border (128.49), derived"),
    ("f_x0", None, "left fastener line x (-2.89)"), ("f_x1", None, "right fastener line x (210.59)"),
    ("f_y0", None, "top fastener line y (-5.83)"), ("f_y1", None, "bottom fastener line y (139.49)"),
    ("fl_x0", None, "flange outline left (-12.89)"), ("fl_x1", None, "flange outline right (220.59)"),
    ("fl_y0", None, "flange outline top (-15.83)"),
    ("bend_y1", None, G + "bridge pocket face (back face of the bend-gap slot) abs y at Z_LAND over the tail span (122.23), "
     "1 deg widening to the back"),
]


def run(_context: str):
    d = L.check_doc()
    L.log("=== 87 start")
    ups = d.userParameters
    if abs(L.P("border") - 18.5) > 1e-9:
        raise RuntimeError("87: border is not 18.5 (already applied?)")
    old = {nm: (ups.itemByName(nm).expression, round(L.P(nm), 4)) for nm, e, c in CHANGE}
    for nm, e, c in CHANGE:
        p = ups.itemByName(nm)
        if e is not None:
            p.expression = e
        p.comment = c
    d.computeAll()
    n, bad = L.timeline_health()
    res = {"old": old, "new": {nm: (ups.itemByName(nm).expression, round(L.P(nm), 4)) for nm, e, c in CHANGE},
           "key": {k: round(L.P(k), 4) for k in ("glass_y1", "bend_y1", "fl_y1", "f_x0", "f_y1", "pip2_y", "pip1_x", "logo_cy",
                                                  "gc_y", "Z_FLOOR_LOW")},
           "timeline": n, "unhealthy": bad, "frame": L.body_dict(), "bodies_in_component": L.comp().bRepBodies.count}
    L.dump(res, "gf21/87_params.json")
    L.log("87 %s" % res)
    if bad:
        raise RuntimeError("unhealthy %s" % bad)
    print(res)
