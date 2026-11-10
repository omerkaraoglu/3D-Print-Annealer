"""Merge the four regions' track files, import on the placed board, finalize (stackup/title), DRC, renders, metrics."""
import json, subprocess, sys, os
SCR = os.path.dirname(os.path.abspath(__file__))
KIPY = r"C:/Program Files/KiCad/10.0/bin/python.exe"
files = ["tracks_display.json", "tracks_signals.json", "tracks_power.json", "tracks_mains.json"]
merged = []
for f in files:
    p = os.path.join(SCR, f)
    if os.path.exists(p):
        d = json.load(open(p)); merged += d; print(f, len(d))
    else: print("MISSING", f)
json.dump(merged, open(os.path.join(SCR, "tracks_all.json"), "w"))
subprocess.run([KIPY, os.path.join(SCR, "import_tracks.py"), os.path.join(SCR, "rev3_placed.kicad_pcb"), os.path.join(SCR, "tracks_all.json"), os.path.join(SCR, "rev3_routed.kicad_pcb")], check=True)
subprocess.run([sys.executable, os.path.join(SCR, "finalize_board.py"), os.path.join(SCR, "rev3_routed.kicad_pcb"), os.path.join(SCR, "rev3_final.kicad_pcb")], check=True)
r = subprocess.run([sys.executable, os.path.join(SCR, "drc_run.py"), os.path.join(SCR, "rev3_final.kicad_pcb"), "40"], capture_output=True, text=True)
print(r.stdout)
# NOTE: zones are filled by deliver.py after the copy into the project (the fill needs the project's .kicad_dru rules,
# which pcbnew only loads for a board that carries the project's name).
subprocess.run([sys.executable, os.path.join(SCR, "metrics.py"), os.path.join(SCR, "tracks_all.json")])
