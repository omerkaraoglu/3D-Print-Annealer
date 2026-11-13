"""DRC-driven fillet loop: fillet.py -> drc.py (project rules, refill) -> shrink every corner whose arc or trimmed
segments appear in a clearance/creepage/unconnected/dangling item (x0.6, and to 0 = sharp once the radius would fall
below 0.2 mm) -> repeat until DRC has no new errors.
Usage (system python): fillet_loop.py in.kicad_pcb out.kicad_pcb rulesdir [maxit]"""
import json, subprocess, sys, os, shutil
KPY = r"C:/Program Files/KiCad/10.0/bin/python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
src, dst, rules = sys.argv[1:4]
maxit = int(sys.argv[4]) if len(sys.argv) > 4 else 8
base = os.path.splitext(dst)[0]
scalef = base + "_scale.json"
scale = json.load(open(scalef)) if os.path.exists(scalef) else {}
for it in range(maxit):
    json.dump(scale, open(scalef, "w"))
    r = subprocess.run([KPY, os.path.join(HERE, "fillet.py"), src, dst, base + "_corners.json", scalef], capture_output=True, text=True)
    print("it", it, r.stdout.strip().replace("\n", " | "))
    subprocess.run([KPY, os.path.join(HERE, "drc.py"), dst, rules, "0"], capture_output=True, text=True)
    d = json.load(open(base + "_drc.json", encoding="utf-8"))
    rep = json.load(open(base + "_corners.json"))
    umap = rep["uuid"]
    bad = [v for v in d["violations"] if v["severity"] == "error"] + d["unconnected_items"]
    bad += [v for v in d["violations"] if v["type"] == "track_dangling"]
    hit = set(); unmapped = []
    for v in bad:
        ks = [k for itm in v["items"] for k in umap.get(itm.get("uuid", ""), [])]
        if ks: hit.update(ks)
        else: unmapped.append((v["type"], v["description"][:80], [i["description"][:50] for i in v["items"]]))
    print("   errors %d, corners hit %d, unmapped %d" % (len(bad), len(hit), len(unmapped)))
    for u in unmapped[:10]: print("   UNMAPPED", u)
    if not hit:
        break
    got = {f["key"]: f["R"] for f in rep["filleted"]}
    for k in hit:
        f = got.get(k, 0.0) * 0.6
        scale[k] = f if f >= 0.2 else 0.0
json.dump(scale, open(scalef, "w"))
