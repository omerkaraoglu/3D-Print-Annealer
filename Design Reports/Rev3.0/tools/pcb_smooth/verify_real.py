"""Final verification on the real project files (reads only; reports go to the scratch folder).
Usage: verify_real.py board.kicad_pcb outdir"""
import subprocess, sys, json, collections, os
CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
for tag, extra in (("as_saved", []), ("refill", ["--refill-zones"])):
    rep = os.path.join(out, "drc_%s.json" % tag)
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--severity-all", "--units", "mm", "--all-track-errors", "-o", rep, src] + extra,
                   capture_output=True)
    d = json.load(open(rep, encoding="utf-8"))
    v = d["violations"]
    print("DRC %-8s errors %d warnings %d unconnected %d" % (tag, sum(1 for x in v if x["severity"] == "error"),
          sum(1 for x in v if x["severity"] == "warning"), len(d["unconnected_items"])))
    print("   ", dict(collections.Counter((x["severity"], x["type"]) for x in v)))
