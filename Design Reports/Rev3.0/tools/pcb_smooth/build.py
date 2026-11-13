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
Round 3 (2026-11-13, on s7 = the board committed as bd375c0; to start from the real board copy it to workdir/s7.kicad_pcb
and run with from_step 10):
10 r3_j11          J11 2.08 mm west + its escape re-routed, C226 / R227 / C225-via nudges          -> r1
11 r3_holes+fill   old holes H1..H4 and their keep-outs out, left / bottom ears, outline, H1..H9  -> r2
12 teardrops+fill  teardrops regenerated in the J11 area only (region=)                           -> r3
13 stitch          plan restricted to the J11 area and the four former hole areas + apply + fill  -> r4
14 r3_ds1          DS1 model offset from models.json if it changed (else a copy)                   -> r5
15 drc             kicad-cli DRC with the rules, zones as saved
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
# ---- round 3
R3_TD = "region=33.5,83.8,46.0,93.4"
R3_ST = ["region=33,83,49,95.5", "region=-1,-1,12,12", "region=-1,87,12,100", "region=89,87,105,100", "region=152,87,165,100"]
if start <= 10: run(KPY, "r3_j11.py", p("s7.kicad_pcb"), p("r1.kicad_pcb"))
if start <= 11:
    run(KPY, "r3_holes.py", p("r1.kicad_pcb"), p("r2u.kicad_pcb"))
    run(KPY, "fill.py", p("r2u.kicad_pcb"), p("r2.kicad_pcb"), R)
if start <= 12:
    run(KPY, "teardrops.py", p("r2.kicad_pcb"), p("r3u.kicad_pcb"), p("r3_td.json"), R3_TD)
    run(KPY, "fill.py", p("r3u.kicad_pcb"), p("r3.kicad_pcb"), R)
if start <= 13:
    run(KPY, "geom_export.py", p("r3.kicad_pcb"), p("r3_geom.json"))
    run(sys.executable, "stitch_plan.py", p("r3_geom.json"), p("stitch_r3.json"), *R3_ST)
    run(KPY, "stitch_apply.py", p("r3.kicad_pcb"), p("r4u.kicad_pcb"), p("stitch_r3.json"))
    run(KPY, "fill.py", p("r4u.kicad_pcb"), p("r4.kicad_pcb"), R)
if start <= 14: run(KPY, "r3_ds1.py", p("r4.kicad_pcb"), p("r5.kicad_pcb"), MODELS)
if start <= 15: run(KPY, "drc.py", p("r5.kicad_pcb"), R, "norefill", "40")
