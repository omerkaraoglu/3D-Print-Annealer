"""Copy a candidate board into the project dir under the project name (so the .kicad_pro/.kicad_dru apply), run DRC, summarise."""
import subprocess, sys, json, collections, shutil, os
SCR = r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\c8708701-d586-4d89-8e7b-a64a4af1e14d\scratchpad"
PRJ = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\KiCad\3dFilamentDryer"
src = sys.argv[1]
tmpname = "3dFilamentDryer_drctmp_%d" % os.getpid()
for ext in (".kicad_pro", ".kicad_dru"):
    shutil.copy(os.path.join(PRJ, "3dFilamentDryer" + ext), os.path.join(PRJ, tmpname + ext))
shutil.copy(src, os.path.join(PRJ, tmpname + ".kicad_pcb"))
rep = os.path.splitext(src)[0] + "_drc.json"
refill = [] if "norefill" in sys.argv else ["--refill-zones"]
subprocess.run([r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe", "pcb", "drc", "--format", "json", "--severity-error"] + refill +
               ["--all-track-errors", "-o", rep, os.path.join(PRJ, tmpname + ".kicad_pcb")], capture_output=True)
for ext in (".kicad_pro", ".kicad_dru", ".kicad_pcb", ".kicad_prl"):
    try: os.remove(os.path.join(PRJ, tmpname + ext))
    except FileNotFoundError: pass
d = json.load(open(rep, encoding="utf-8"))
viol = d.get("violations", []); unc = d.get("unconnected_items", [])
print("violations", len(viol), "unconnected", len(unc))
print(collections.Counter(v["type"] for v in viol))
N = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 25
for v in viol[:N]:
    its = [it.get("description", "")[:70] for it in v.get("items", [])][:2]
    pos = v.get("items", [{}])[0].get("pos", {})
    print(" %-22s %-75s %s @(%.1f,%.1f)" % (v["type"], v["description"][:75], its, pos.get("x", 0) - 20, pos.get("y", 0) - 20))
for u in unc[:N]:
    its = [it.get("description", "")[:60] for it in u.get("items", [])][:2]
    print(" UNC", its)
