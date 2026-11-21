"""Stage 2b (KiCad python): apply plan.json from s2_plan.py to the board.
  - BP1..BPn = Rev3:LandingPad_GND_Bare6.0x5.0mm_Cu8.0x7.0mm, flipped to B.Cu (left/right), pad net GND, attributes
    board_only / exclude_from_bom / exclude_from_pos_files from the footprint (no schematic symbol: like H1-H9 and DS1,
    board-only footprints are left out of the parity check, so no parity item is created)
  - Reference "BPn" on B.SilkS at the planned spot, 0.8 / 0.7 / 0.10, mirrored (flip), Value hidden
  - stitching vias taken out by UUID (kept in KEEP: a removed item whose proxy is collected corrupts the board in 10.0.1)
  - new GND vias 0.6 / 0.3, through, free (as the house stitching vias)
Usage: s2_build.py in.kicad_pcb plan.json Rev3.pretty-dir out.kicad_pcb"""
import json, sys
import pcbnew
sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth")
from common import V, L  # noqa: E402

src, planf, libdir, dst = sys.argv[1:5]
NAME = "LandingPad_GND_Bare6.0x5.0mm_Cu8.0x7.0mm"
b = pcbnew.LoadBoard(src)
plan = json.load(open(planf))
gnd = b.FindNet("GND")
KEEP = []
rm = set(r["uuid"] for r in plan["removed"])
n_rm = 0
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA" and t.m_Uuid.AsString() in rm:
        assert t.GetNetname() == "GND" and t.GetIsFree()
        b.Remove(t); KEEP.append(t); n_rm += 1
assert n_rm == len(rm), (n_rm, len(rm))
for x, y in plan["added"]:
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y)); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); v.SetIsFree(True); b.Add(v)
for p in plan["pads"]:
    fp = pcbnew.FootprintLoad(libdir, NAME)
    fp.SetFPID(pcbnew.LIB_ID("Rev3", NAME))
    fp.SetReference(p["ref"]); fp.SetValue("LandingPad_GND")
    fp.SetPosition(V(p["x"], p["y"]))
    b.Add(fp)
    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for pad in fp.Pads():
        pad.SetNet(gnd)
    r = fp.Reference()
    r.SetVisible(True)
    r.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.7), pcbnew.FromMM(0.8))); r.SetTextThickness(pcbnew.FromMM(0.1))
    lx, ly, ang = p["label"]
    r.SetTextAngleDegrees(ang); r.SetPosition(V(lx, ly))
    fp.Value().SetVisible(False)
    assert fp.IsFlipped() and r.GetLayer() == pcbnew.B_SilkS, (p["ref"], b.GetLayerName(r.GetLayer()))
pcbnew.SaveBoard(dst, b)
print("removed vias %d, added vias %d, pads %d -> %s" % (n_rm, len(plan["added"]), len(plan["pads"]), dst))
