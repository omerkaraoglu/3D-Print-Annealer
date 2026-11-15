"""36b - stage 2, Part B (migration, run once after the first 36): the first build had the weld studs and the washers
+ nuts of a variant in ONE component ('Fasteners S4 F1-F4', 'Fasteners S8 F5-F8 (hidden)'), so an exploded view could
not keep the studs on the sheet. This deletes those two occurrences (their components and features go with them) and
re-creates them with the (edited) 36 functions as four components:
  'Weld studs S4 F1-F4', 'Washers + nyloc nuts S4 F1-F4' (visible),
  'Weld studs S8 F5-F8 (hidden)', 'Washers, nuts, spacers S8 F5-F8 (hidden)' (hidden).
Same parameters, same geometry. A clean rebuild runs the edited 36 directly and skips 36b."""
import importlib
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 36b start")
    p = os.path.join(L.GF_DIR, "36_asm_fasteners.py")
    ns = {"__name__": "gf_36"}
    exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns)
    for old in ("Fasteners S4 F1-F4", "Fasteners S8 F5-F8 (hidden)"):
        o = L.occ_by_comp(old, False)
        if o is not None:
            o.deleteMe()
    s, w, n = ns["studs_washers_nuts"](L.new_comp(ns["S4_STUDS"]).component, L.new_comp(ns["S4_NUTS"]).component,
                                       [1, 2, 3, 4], "S4")
    o8s, o = L.new_comp(ns["S8_STUDS"]), L.new_comp(ns["S8_NUTS"])
    c = o.component
    ks = [5, 6, 7, 8]
    s8, w8, n8 = ns["studs_washers_nuts"](o8s.component, c, ks, "S8")
    ps = L.cplane(c, "Z_SHEET_BACK (S8 spacers)", "Z_SHEET_BACK")
    f = L.cextrude(c, ns["circles"](c, "S8 spacers DIN 9021 M4", ps, ks, "w4_od", "w4_id"), "new", "t_gap", +1,
                   "S8 spacers DIN 9021 M4")
    sp = ns["name_bodies"](f, ks, "Spacer DIN 9021 M4 F%d", ns["STEEL"])
    o.isLightBulbOn = False
    o8s.isLightBulbOn = False
    nn, bad = L.timeline_health()
    r = L.root()
    names = [r.occurrences.item(i).name for i in range(r.occurrences.count)]
    L.log("36b done: %s; timeline %d unhealthy %s" % (names, nn, bad))
    print([b.name for b in s + w + n + s8 + w8 + n8 + sp], nn, bad, names)
