"""Run the whole smoothing round on a board (system python; calls KiCad's python for the pcbnew steps).
Usage: build.py original.kicad_pcb workdir rulesdir [from_step]
Steps (each writes workdir/sN.kicad_pcb):
 1 t1_fanfeed      K1.1 -> LINE_FUSED, LINE_FILT west branch to B.Cu, 2.5 mm LINE_FUSED feed      -> s1
 3 t23_outline     ears + M3 holes H5..H9 + washer keep-outs, R3 corners, round slot ends          -> s3
 4 fillet          tangent arcs at every bend (radius caps from s4_scale.json of the DRC loop)      -> s4
 5 t5_zones+fill   pour smoothing / min width / outline to the board edge, filled with the rules   -> s5
 6 teardrops+fill  KiCad teardrop zones (padvia / track_end)                                       -> s5t
 7 stitch          plan (shapely) + apply + fill                                                   -> s6
 8 t9_final        3D models, DS1 display envelope, hole names / attributes                         -> s7
 9 drc             kicad-cli DRC with the rules, zones as saved
"""
import subprocess, sys, os
KPY = r"C:/Program Files/KiCad/10.0/bin/python.exe"
H = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(H, "..", "models3d", "models.json")
FPLIB = os.path.join(H, "..", "..", "..", "..", "KiCad", "ComponentsLibrary", "User Created", "Rev3", "Rev3.pretty")
orig, W, R = sys.argv[1:4]
start = int(sys.argv[4]) if len(sys.argv) > 4 else 1
p = lambda n: os.path.join(W, n)


def run(py, *a):
    r = subprocess.run([py, os.path.join(H, a[0])] + list(a[1:]), capture_output=True, text=True)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "memory leak" not in l and "detected a memory" not in l)
    print("[%s] %s" % (a[0], out.strip()[-1500:]))
    if r.returncode:
        sys.exit("step %s failed" % a[0])


if start <= 1: run(KPY, "t1_fanfeed.py", orig, p("s1.kicad_pcb"))
if start <= 3: run(KPY, "t23_outline.py", p("s1.kicad_pcb"), p("s3.kicad_pcb"))
if start <= 4: run(KPY, "fillet.py", p("s3.kicad_pcb"), p("s4.kicad_pcb"), p("s4_corners.json"), p("s4_scale.json"))
if start <= 5:
    run(KPY, "t5_zones.py", p("s4.kicad_pcb"), p("s5u.kicad_pcb"))
    run(KPY, "fill.py", p("s5u.kicad_pcb"), p("s5.kicad_pcb"), R)
if start <= 6:
    td_skip = [p("td_skip.json")] if os.path.exists(p("td_skip.json")) else []
    run(KPY, "teardrops.py", p("s5.kicad_pcb"), p("s5tu.kicad_pcb"), p("s5t_td.json"), *td_skip)
    run(KPY, "fill.py", p("s5tu.kicad_pcb"), p("s5t.kicad_pcb"), R)
if start <= 7:
    run(KPY, "geom_export.py", p("s5t.kicad_pcb"), p("s5t_geom.json"))
    sk = [p("stitch_skip.json")] if os.path.exists(p("stitch_skip.json")) else []
    run(sys.executable, "stitch_plan.py", p("s5t_geom.json"), p("stitch.json"), *sk)
    run(KPY, "stitch_apply.py", p("s5t.kicad_pcb"), p("s6u.kicad_pcb"), p("stitch.json"))
    run(KPY, "fill.py", p("s6u.kicad_pcb"), p("s6.kicad_pcb"), R)
if start <= 8:
    run(KPY, "t9_final.py", p("s6.kicad_pcb"), p("s7.kicad_pcb"), MODELS, FPLIB)
if start <= 9:
    run(KPY, "drc.py", p("s7.kicad_pcb"), R, "norefill", "40")
