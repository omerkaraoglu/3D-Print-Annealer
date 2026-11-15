"""09 - READ-ONLY census of the concave root edges (plane / cone faces, |n1.n2| <= 0.9) grouped by the creating
features of their two faces (gflib.owner_group) -> scratchpad root_census_<TAG>.json + summary print.
Run with readOnly: true. TAG from the _context-independent global below (edit when re-running)."""
import importlib
import json
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

TAG = "pre_fillet"


def run(_context: str):
    L.check_doc()
    res = {}
    for g, e, m, z, o in L.root_edges(0.9):
        res.setdefault(g, []).append({"mid_abs": [round(m[0], 3), round(-m[1], 3), round(m[2], 3)],
                                      "z": [round(z[0], 3), round(z[1], 3)], "len": round(e.length * 10, 3),
                                      "owners": list(o)})
    p = L.dump(res, "root_census_%s.json" % TAG)
    summ = {g: len(v) for g, v in res.items()}
    print(p, json.dumps(summ, indent=0))
