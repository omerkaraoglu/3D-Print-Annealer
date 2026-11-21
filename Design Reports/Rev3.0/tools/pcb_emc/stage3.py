"""PCB round of the EMC-fix changes (2026-11-21), stage 3: the mains band - K1 (TE RZ03-1A4-D005 / Hongfa HF115FD on
Relay_THT:Relay_SPST_Schrack-RT1-16A-FormA_RM5mm) and D6 (1.5KE440CA); then RV3 (Thinking TVR10471KSY) across the K1 contact
(owner's decision after the surge re-simulation): s4_build.py places it west of the contact pins and moves LINE_FUSED
round the east side of the relay. (No LINE_FUSED-NEUT site existed: s3_rv3search.py; contact-position search:
s4_rv3search.py.)

House method: explicit track lists (0/45/90 deg, ends at pad centres), tangent arcs by pcb_smooth/fillet.py, curved
teardrops by pcb_smooth/teardrops.py in the touched boxes, zones filled with the project rules (pcb_smooth/fill.py),
designators by the silk_refdes method (silk_new.py / silk_apply_new.py). No relay exception is left in the rules.

    python stage3.py <work_dir> <board_in> <sch_netlist.xml> <project_dir_with_rules>

Steps (KiCad python = C:/Program Files/KiCad/10.0/bin/python.exe for the pcbnew steps):
  1  s3_rules.py     .kicad_pro / .kicad_dru without the K1 exceptions (into <work>/rules)
  2  s3_build.py     K1 footprint + LINE_FUSED / fan / coil-feed routes, D6 + LINE_FILT / /Q1_A1 stubs, PSU_L moved,
                     'mains: no inner copper' and Cmts.User boundary notched (x 61.5-77.0, y 45-56), k1_pins deleted
  3  fillet.py, teardrops.py (regions.json), fill.py
  4  refdes_geom.py + silk_new.py "K1,D6,L40" + silk_apply_new.py; K1 value hidden
  5  s3_d6mark.py    D6 bidirectional: "K" texts removed, pad 1 round (cathode band removed in step 2); fill again
  5b s4_build.py    RV3 + re-routes; fillet.py, teardrops.py (region 47,12,82,35), fill.py; silk_new.py "RV3"
  6  checks: drc_par.py (as saved / refill), conn_sch.py, corner_check.py, in1_web_check.py, s3_mains_check.py (no
     relay exception, notched LV polygon, tall-part gap table), s3_barrier.py (coil / contact distances per layer),
     render_crops.py (30 px/mm)
Helpers: s3_k1check.py (relay site check), s3_rv3search.py (RV3 site + reachability search, --asis on a routed board).
"""
import json, os, subprocess, sys

KP = r"C:/Program Files/KiCad/10.0/bin/python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
SM = os.path.join(os.path.dirname(HERE), "pcb_smooth")
SR = os.path.join(os.path.dirname(HERE), "silk_refdes")


def run(*a):
    print(">", " ".join(os.path.basename(str(x)) for x in a[:3]))
    subprocess.run([str(x) for x in a], check=True)


def main(work, brd, netxml, proj):
    P = lambda n: os.path.join(work, n)
    os.makedirs(P("rules"), exist_ok=True)
    run(sys.executable, os.path.join(HERE, "s3_rules.py"), proj, P("rules"))
    run(KP, os.path.join(HERE, "s3_build.py"), brd, netxml, P("s3a.kicad_pcb"), P("regions.json"))
    run(KP, os.path.join(SM, "fillet.py"), P("s3a.kicad_pcb"), P("s3b.kicad_pcb"), P("s3b_corners.json"))
    reg = ["region=%s" % ",".join(str(v) for v in b) for b in json.load(open(P("regions.json"))).values()]
    run(KP, os.path.join(SM, "teardrops.py"), P("s3b.kicad_pcb"), P("s3c.kicad_pcb"), P("s3c_td.json"), *reg)
    run(KP, os.path.join(SM, "fill.py"), P("s3c.kicad_pcb"), P("s3d.kicad_pcb"), P("rules"))
    run(KP, os.path.join(SR, "refdes_geom.py"), P("s3d.kicad_pcb"), P("geom_silk.json"))
    run(sys.executable, os.path.join(HERE, "silk_new.py"), P("geom_silk.json"), "K1,D6,L40", P("silk_new.json"))
    run(KP, os.path.join(HERE, "silk_apply_new.py"), P("s3d.kicad_pcb"), P("silk_new.json"), P("s3e.kicad_pcb"))
    run(KP, "-c", "import pcbnew; b=pcbnew.LoadBoard(r'%s'); b.FindFootprintByReference('K1').Value().SetVisible(False); pcbnew.SaveBoard(r'%s', b)" % (P("s3e.kicad_pcb"), P("s3e.kicad_pcb")))
    run(KP, os.path.join(HERE, "s3_d6mark.py"), P("s3e.kicad_pcb"), P("s3f0.kicad_pcb"))
    run(KP, os.path.join(SM, "fill.py"), P("s3f0.kicad_pcb"), P("s3f.kicad_pcb"), P("rules"))
    print("stage-3 board:", P("s3f.kicad_pcb"))


if __name__ == "__main__":
    main(*sys.argv[1:5])
