"""DRC with schematic parity of a board inside a project directory that also holds the sheets, the rules and the lib tables.
Usage: drc_par.py project_dir/3dFilamentDryer.kicad_pcb out.json [refill]"""
import subprocess, sys, json, collections
CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
src, rep = sys.argv[1], sys.argv[2]
extra = ["--refill-zones"] if "refill" in sys.argv[3:] else []
subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "--units", "mm", "--schematic-parity", "--all-track-errors", "-o", rep, src] + extra, capture_output=True)
d = json.load(open(rep, encoding="utf-8"))
v = d["violations"]; u = d["unconnected_items"]; p = d.get("schematic_parity", [])
print("errors %d warnings %d unconnected %d parity %d" % (sum(1 for x in v if x["severity"] == "error"), sum(1 for x in v if x["severity"] == "warning"), len(u), len(p)))
print("  violations:", dict(collections.Counter((x["severity"], x["type"]) for x in v)))
print("  parity:", dict(collections.Counter(x["type"] for x in p)))
