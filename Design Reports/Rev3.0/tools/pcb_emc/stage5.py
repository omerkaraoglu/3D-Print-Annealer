"""PCB / schematic round of 2026-11-23, stage 5: the single-point ground-to-earth bond J5 (owner's decision "put the
earth connection on the board"; position reserved in spec 12.12.7: local (7.0, 92.5), next to BP16, chassis stud FH9
about 22 mm away).

    python stage5.py <work_dir> <project_dir>

<project_dir> is a COPY of KiCad/3dFilamentDryer whose ../ComponentsLibrary/User Created/Rev3/Rev3.pretty receives the
footprint (fp-lib-table: ${KIPRJMOD}/../ComponentsLibrary/...). Never run inside the real folder (kicad-cli / pcbnew leave
~*.lck files); copy the results back after the checks.

Steps (KiCad python = C:/Program Files/KiCad/10.0/bin/python.exe for the pcbnew steps):
  1  stage5_footprint.py          Rev3:EarthBond_M3_Pad7.0mm_Drill3.2mm into Rev3.pretty (copper 7.0 all layers, front
                                  mask opening 7.1, back mask opening 5.6 = B.Mask circle: 1.0 mm to the frame ribs)
  2  ../sch_emc/stage5_j5.py      J5 'PE bond' (Connector:Conn_01x01_Pin, in_bom no, in_pos_files no) on GND, Thermocouple
                                  sheet, with its note
  3  stage5_build.py              J5 on F.Cu at (7.0, 92.5), net GND; 2 free GND stitching vias inside the pad removed
  4  silk_refdes/refdes_geom.py + silk_new.py "J5" + silk_apply_new.py   designator by the house method; the raster
                                  has no via holes, so clear_via_holes() slides the text along x until it keeps 0.30 mm
                                  from every via hole (here 0.80 mm west: the bottom via fence at y 97.367)
  5  pcb_smooth/fill.py           zones filled with the project rules (the pad is solid on F.Cu, In1, B.Cu; the 3V3 plane
                                  on In2 clears it)
  6  checks (stage5_check.py): DRC with parity as saved and refilled, ERC, pad/net map, solid-connection and anti-pad
     test, distances (mains, J20, BP16, other-net copper, frame features), renders (stage5_render.py)
No track is added or moved; no rule is changed.
"""
import json
import os
import shutil
import subprocess
import sys

KP = r"C:/Program Files/KiCad/10.0/bin/python.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
SM = os.path.join(TOOLS, "pcb_smooth")
SR = os.path.join(TOOLS, "silk_refdes")


VIAS = r'''import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1]); out = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        out.append([pcbnew.ToMM(p.x), pcbnew.ToMM(p.y), pcbnew.ToMM(t.GetDrillValue())])
json.dump(out, open(sys.argv[2], "w"))
'''


def run(*a):
    print(">", " ".join(os.path.basename(str(x)) for x in a[:3]))
    subprocess.run([str(x) for x in a], check=True)


def clear_via_holes(placef, viaf, ref="J5", clr=0.30):
    """silk_new's obstacle raster has no via holes (tented vias): slide the chosen designator along x, by the smallest
    amount, until its ink box keeps the house hole clearance (0.30 mm, silk_refdes clr_hole) from every via hole."""
    pl = json.load(open(placef)); vias = json.load(open(viaf))
    c = pl[ref]; x0, y0, x1, y1 = c["rect"]

    def bad(dx):
        for vx, vy, dr in vias:
            r = dr / 2 + clr
            if x0 + dx - r < vx < x1 + dx + r and y0 - r < vy < y1 + r:
                cx = min(max(vx, x0 + dx), x1 + dx); cy = min(max(vy, y0), y1)
                if (vx - cx) ** 2 + (vy - cy) ** 2 < r * r:
                    return True
        return False
    for k in range(0, 41):
        for dx in ((0.05 * k, -0.05 * k) if k else (0.0,)):
            if not bad(dx):
                if dx:
                    c["rect"] = [x0 + dx, y0, x1 + dx, y1]
                    c["centre"] = [c["centre"][0] + dx, c["centre"][1]]
                    c["via_shift"] = dx
                    json.dump(pl, open(placef, "w"), indent=1)
                print("%s designator shifted %.2f mm in x to clear via holes by %.2f mm" % (ref, dx, clr))
                return dx
    raise SystemExit("no via-clear shift within 2 mm")


def main(work, proj):
    os.makedirs(work, exist_ok=True)
    P = lambda n: os.path.join(work, n)
    lib = os.path.normpath(os.path.join(proj, "..", "ComponentsLibrary", "User Created", "Rev3", "Rev3.pretty"))
    brd = os.path.join(proj, "3dFilamentDryer.kicad_pcb")
    run(sys.executable, os.path.join(HERE, "stage5_footprint.py"), lib)
    run(sys.executable, "-I", os.path.join(TOOLS, "sch_emc", "stage5_j5.py"), proj)
    run(KP, os.path.join(HERE, "stage5_build.py"), brd, lib, P("s5a.kicad_pcb"))
    run(KP, os.path.join(SR, "refdes_geom.py"), P("s5a.kicad_pcb"), P("geom_silk.json"))
    run(sys.executable, os.path.join(HERE, "silk_new.py"), P("geom_silk.json"), "J5", P("silk_new.json"))
    open(P("vias_export.py"), "w").write(VIAS)
    run(KP, P("vias_export.py"), P("s5a.kicad_pcb"), P("vias_abs.json"))
    clear_via_holes(P("silk_new.json"), P("vias_abs.json"))
    run(KP, os.path.join(HERE, "silk_apply_new.py"), P("s5a.kicad_pcb"), P("silk_new.json"), P("s5b.kicad_pcb"))
    run(KP, os.path.join(SM, "fill.py"), P("s5b.kicad_pcb"), P("s5c.kicad_pcb"), proj)
    shutil.copyfile(P("s5c.kicad_pcb"), brd)
    print("stage-5 board:", brd)


if __name__ == "__main__":
    main(*sys.argv[1:3])
