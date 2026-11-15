"""60 - stage 3 (GF-1.1), READ-ONLY: the H6 boss / pilot must stay exactly as is (item 3). Measures every cone face
coaxial with the ear holes H1-H9 and the pilot floor levels on the current frame body with 22's coax_cones /
pilot_floor (22 is exec'd without running it, so nothing is imported) and compares them with the GF-1.0 + Part A
values of stage 2 (carry_measure.json 'gf_cones', 14:18, the run after the Part A fix).
-> gf11\\boss_pilot_check.json. Nothing in the document is changed."""
import importlib
import json
import os
import sys

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def run(_context: str):
    d = L.check_doc()
    p22 = os.path.join(L.GF_DIR, "22_carryover_vs_v2_step.py")
    ns = {"__name__": "gf_22_lib", "__file__": p22}
    exec(compile(open(p22, encoding="utf-8").read(), p22, "exec"), ns)
    ref = json.load(open(os.path.join(L.SCR, "carry_measure.json")))["bosses"]
    gf = L.body()
    out = {"reference": "carry_measure.json (stage 2 Part A, GF-1.0 frame)", "bosses": {}, "differences": []}
    for i in range(1, 10):
        nm = "H%d" % i
        x, y = L.P("h%d_x" % i), L.P("h%d_y" % i)
        now = {"cones": ns["coax_cones"](gf, x, y), "pilot_floor_z": ns["pilot_floor"](gf, x, y)}
        old = {"cones": ref[nm]["gf_cones"], "pilot_floor_z": ref[nm]["gf_pilot_floor_z"]}
        out["bosses"][nm] = {"xy": [x, y], "now": now, "stage2": old}
        if now != old:
            out["differences"].append(nm)
    out["modified_flag_after"] = d.parentDocument.isModified if hasattr(d, "parentDocument") else None
    p = os.path.join(L.SCR, "gf11", "boss_pilot_check.json")
    json.dump(out, open(p, "w"), indent=1)
    L.log("60 boss / pilot check: differences %s" % out["differences"])
    print(p, "differences", out["differences"])
