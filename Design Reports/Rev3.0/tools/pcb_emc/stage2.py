"""PCB round of the EMC-fix changes (2026-11-21), stage 2: bare GND landing pads on B.Cu for the display panel bond.

18 pads BP1..BP18 = Rev3:LandingPad_GND_Bare6.0x5.0mm_Cu8.0x7.0mm (copper 8.0 x 7.0, mask opening 6.0 x 5.0 = bare ENIG
landing area, no paste, solid zone connection, board-only / not in BOM / not in position files), flipped to B.Cu, net GND,
each tied to In1 by 5-8 GND vias 0.6/0.3 on the 1.0 mm masked rim (none in the bare area; free stitching vias under
the pads were taken out). Board-only footprints are left out of the schematic parity check, exactly like H1-H9 and DS1,
so they need no symbol. Labels "BPn" on B.SilkS (house S style 0.8 / 0.7 / 0.10).

House rules kept: no tracks moved (all 18 sites are free of foreign B.Cu copper), vias placed with the stitching rules
of pcb_smooth/stitch_plan.py (`why`), zones filled with the project rules (pcb_smooth/fill.py).

    python stage2.py <work_dir> <board_in> <Rev3.pretty> <rules_dir> <frame_v2_params.json>

Steps (KiCad python = C:/Program Files/KiCad/10.0/bin/python.exe for the pcbnew steps):
  1  geo_full.py (this folder), pcb_smooth/geom_export.py, a via list with the free flag (s2_build's companion
     export in s2_plan's docstring) -> geometry JSONs
  2  s2_sites.py  feasibility scan of pad centres (hard limits of the brief) - used to choose the 18 sites in s2_plan.PADS
  3  s2_plan.py   per pad: stitching vias out, rim vias in (house stitching rules), label spot -> plan.json
  4  s2_build.py  footprints, vias, labels on the board
  5  pcb_smooth/fill.py
  6  s2_table.py  pad table (centres, via count, partial inductance of the via group, nearest mains copper, frame side)
     s2_render.py back-side overview (mirrored, numbered); render_crops.py 30 px/mm crops of every pad
     s2_free.py   stage-3 notes: X2 / RC site search near J4 / K1 and the M3 ring-lug earth-bond site near J20
  7  drc_par.py (as saved and refilled), conn_sch.py, pcb/in1_web_check.py, pcb_smooth/corner_check.py, mains2_check.py
"""
import os, subprocess, sys

KP = r"C:/Program Files/KiCad/10.0/bin/python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
SM = os.path.join(os.path.dirname(HERE), "pcb_smooth")
VIAS = r'''import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1]); out = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        out.append([round(pcbnew.ToMM(p.x) - 20, 4), round(pcbnew.ToMM(p.y) - 20, 4), t.GetNetname(), bool(t.GetIsFree()), t.m_Uuid.AsString()])
json.dump(out, open(sys.argv[2], "w"))
'''


def run(*a):
    print(">", " ".join(os.path.basename(str(x)) for x in a[:3]))
    subprocess.run([str(x) for x in a], check=True)


def main(work, brd, lib, rules, fparams):
    os.makedirs(work, exist_ok=True)
    P = lambda n: os.path.join(work, n)
    run(KP, os.path.join(HERE, "geo_full.py"), brd, P("geo.json"))
    run(KP, os.path.join(SM, "geom_export.py"), brd, P("gx.json"))
    open(P("vias_export.py"), "w").write(VIAS)
    run(KP, P("vias_export.py"), brd, P("vias.json"))
    run(sys.executable, os.path.join(HERE, "s2_plan.py"), P("gx.json"), P("vias.json"), P("geo.json"), P("plan.json"))
    run(KP, os.path.join(HERE, "s2_build.py"), brd, P("plan.json"), lib, P("s2a.kicad_pcb"))
    run(KP, os.path.join(SM, "fill.py"), P("s2a.kicad_pcb"), P("s2b.kicad_pcb"), rules)
    run(sys.executable, os.path.join(HERE, "s2_table.py"), P("plan.json"), P("geo.json"), fparams)
    run(sys.executable, os.path.join(HERE, "s2_render.py"), P("s2b.kicad_pcb"), P("plan.json"), P("back_overview.png"), "10", "lug=7.0,92.5")
    print("stage-2 board:", P("s2b.kicad_pcb"))


if __name__ == "__main__":
    main(*sys.argv[1:6])
