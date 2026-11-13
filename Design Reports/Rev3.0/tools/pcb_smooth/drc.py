"""DRC of a candidate board with the project rules, in a scratch directory (never in the project folder).
Usage: drc.py board.kicad_pcb rulesdir [norefill] [N]   rulesdir holds 3dFilamentDryer.kicad_pro/.kicad_dru
Writes <board>_drc.json; prints counts by type/severity and the first N items (local coordinates)."""
import subprocess, sys, json, collections, shutil, os
src, rules = sys.argv[1], sys.argv[2]
d = os.path.join(os.path.dirname(os.path.abspath(src)), "drcrun_" + os.path.splitext(os.path.basename(src))[0])
os.makedirs(d, exist_ok=True)
for ext in (".kicad_pro", ".kicad_dru"):
    shutil.copy(os.path.join(rules, "3dFilamentDryer" + ext), os.path.join(d, "3dFilamentDryer" + ext))
shutil.copy(src, os.path.join(d, "3dFilamentDryer.kicad_pcb"))
rep = os.path.splitext(src)[0] + "_drc.json"
refill = [] if "norefill" in sys.argv else ["--refill-zones"]
r = subprocess.run([r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe", "pcb", "drc", "--format", "json", "--severity-all", "--units", "mm"] + refill +
               ["--all-track-errors", "-o", rep, os.path.join(d, "3dFilamentDryer.kicad_pcb")], capture_output=True, text=True)
dd = json.load(open(rep, encoding="utf-8"))
viol = dd.get("violations", []); unc = dd.get("unconnected_items", []); par = dd.get("schematic_parity", [])
print("violations", len(viol), "unconnected", len(unc))
print(collections.Counter((v["severity"], v["type"]) for v in viol))
N = int([a for a in sys.argv[3:] if a.isdigit()][0]) if any(a.isdigit() for a in sys.argv[3:]) else 30
for v in viol[:N]:
    its = [it.get("description", "")[:60] for it in v.get("items", [])][:2]
    pos = v.get("items", [{}])[0].get("pos", {})
    print(" %-8s %-20s %-60s %s @(%.2f,%.2f)" % (v["severity"][:4], v["type"], v["description"][:60], its, pos.get("x", 0) - 20, pos.get("y", 0) - 20))
for u in unc[:N]:
    its = [it.get("description", "")[:60] for it in u.get("items", [])][:2]
    print(" UNC", its)
