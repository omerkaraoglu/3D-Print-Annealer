"""PCB round of the EMC-fix changes (2026-11-21), stage 1: synchronise with the schematic, low-voltage side.

Rules of the house (tools/pcb/README.md, tools/pcb_smooth/README.md, tools/silk_refdes/README.md): no autorouter; every
track from an explicit list (0/45/90 deg, ends at pad centres), tangent-arc corners by pcb_smooth/fillet.py, curved
teardrops by pcb_smooth/teardrops.py (only in the touched boxes), zones filled with the project rules by
pcb_smooth/fill.py, designators by the silk_refdes method (silk_new.py: refdes_place's raster, candidates, ownership).

    python stage1.py <work_dir> <project_dir> <schematic_netlist.xml> <rules_dir>

work_dir     scratch folder (st/ is created there)
project_dir  a copy of KiCad/3dFilamentDryer with ../ComponentsLibrary next to it (kicad-cli parity needs the sheets)
rules_dir    3dFilamentDryer.kicad_pro / .kicad_dru to use: the .kicad_pro of commit bd375c0 (the HEAD copy since
             76f5b79 is a stale one written by an open KiCad: no Bus pattern for the *_T nets, no ZCD_L/N class; DRC
             with it shows 513 false errors) plus "/Q1_A1" in the MainsHeater patterns; the .kicad_dru with /Q1_A1 and
             /ZCD_RAW in place of Net-(Q1-A1) / Net-(R8-Pad2).

Steps (KiCad python = C:/Program Files/KiCad/10.0/bin/python.exe):
  1  s1_sync.py      board update from the schematic: RV2 out, C9 / C134 / C135 / D6 / RV3 in (D6, RV3 parked off the
                     board for stage 3), R4 -> 0603, C5 moved, net renames, every field (Value, Datasheet, Description,
                     MPN, Manufacturer and the other symbol fields), BOM attribute
  2  s1_route.py     the copper: old C5 site cleaned, C9 / C5 / R4 / C134 / C135 tracks and vias, teardrops in the
                     touched boxes deleted (regions.json)
  3  fillet.py       tangent arcs at the new corners (pcb_smooth)
  4  teardrops.py    drops regenerated in the touched boxes (pcb_smooth, region=...)
  5  fill.py         zones filled with the rules (pcb_smooth)
  6  refdes_geom.py + silk_new.py + silk_apply_new.py   designators of C9, C5, R4, C134, C135; values hidden
  7  drc_par.py      DRC --schematic-parity as saved and with --refill-zones; conn_sch.py (pads vs schematic);
                     corner_check.py, in1_web_check.py, mains2_check.py (copy with /Q1_A1 as a mains net),
                     render_crops.py (40 px/mm)
Helpers: cap_search.py (sites for C134/C135: 0402 + dog-bone vias, clearances, via spacing, courtyards, no part under
board silk such as the QR code), geo_full.py, silk_boxes.py, region_items.py, probe.py, areas.py, sx_delete.py.
"""
import os
import subprocess
import sys

KP = r"C:/Program Files/KiCad/10.0/bin/python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
SM = os.path.join(TOOLS, "pcb_smooth")
SR = os.path.join(TOOLS, "silk_refdes")


def run(*a):
    print(">", " ".join(os.path.basename(str(x)) for x in a[:3]))
    subprocess.run([str(x) for x in a], check=True)


def main(work, proj, netxml, rules):
    st = os.path.join(work, "st"); os.makedirs(st, exist_ok=True)
    P = lambda n: os.path.join(st, n)
    brd = os.path.join(proj, "3dFilamentDryer.kicad_pcb")
    run(KP, os.path.join(HERE, "s1_sync.py"), brd, netxml, P("s1a.kicad_pcb"))
    run(KP, os.path.join(HERE, "s1_route.py"), P("s1a.kicad_pcb"), P("s1b.kicad_pcb"), P("regions.json"))
    run(KP, os.path.join(SM, "fillet.py"), P("s1b.kicad_pcb"), P("s1c.kicad_pcb"), P("s1c_corners.json"))
    import json
    reg = ["region=%s" % ",".join(str(v) for v in b) for b in json.load(open(P("regions.json"))).values()]
    run(KP, os.path.join(SM, "teardrops.py"), P("s1c.kicad_pcb"), P("s1d.kicad_pcb"), P("s1d_td.json"), *reg)
    run(KP, os.path.join(SM, "fill.py"), P("s1d.kicad_pcb"), P("s1e.kicad_pcb"), rules)
    run(KP, os.path.join(SR, "refdes_geom.py"), P("s1e.kicad_pcb"), P("geom_silk.json"))
    run(sys.executable, os.path.join(HERE, "silk_new.py"), P("geom_silk.json"), "C9,C5,R4,C134,C135", P("silk_new.json"))
    run(KP, os.path.join(HERE, "silk_apply_new.py"), P("s1e.kicad_pcb"), P("silk_new.json"), P("s1f.kicad_pcb"))
    print("stage-1 board:", P("s1f.kicad_pcb"))


if __name__ == "__main__":
    main(*sys.argv[1:5])
