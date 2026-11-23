"""Stage 5b (KiCad python): the ground-to-earth bond J5 on the board.
  - J5 = Rev3:EarthBond_M3_Pad7.0mm_Drill3.2mm on F.Cu (lug side = component side; front mask opening 7.1, back mask
    opening 5.6 as a B.Mask circle of the footprint, see stage5_footprint.py), pad net GND, at the position reserved
    in spec 12.12.7 (local 7.0, 92.5 = abs 27.0, 112.5), rotation 0; value "PE bond" (hidden), Description as the symbol
  - free GND stitching vias whose copper would lie inside the pad or under the washer envelope (centre closer than
    pad radius 3.5 + via radius 0.3 + 0.25 mm) are taken out (kept in KEEP: a removed item whose proxy is collected
    corrupts the board in 10.0.1); the plated 3.2 mm barrel of the pad replaces them as the F / In1 / B tie
  - the reference is placed afterwards by the silk_refdes method (stage5.py: refdes_geom.py + silk_new.py J5)
Usage: stage5_build.py in.kicad_pcb Rev3.pretty-dir out.kicad_pcb [x y]"""
import math
import sys

import pcbnew

sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth")
from common import V, L  # noqa: E402

src, libdir, dst = sys.argv[1:4]
X, Y = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (7.0, 92.5)
NAME = "EarthBond_M3_Pad7.0mm_Drill3.2mm"
DESC = ("Single-point bond of the low-voltage ground (GND) to the earthed oven chassis (PE): 7.0 mm plated pad for an M3 "
        "screw, ring-lug lead to the chassis stud FH9 (board copper, not a purchased part)")
b = pcbnew.LoadBoard(src)
assert b.FindFootprintByReference("J5") is None
gnd = b.FindNet("GND")
KEEP = []
for t in list(b.GetTracks()):
    if t.GetClass() != "PCB_VIA":
        continue
    x, y = L(t.GetPosition())
    d = math.hypot(x - X, y - Y)
    if d < 3.5 + pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.25:
        assert t.GetNetname() == "GND" and t.GetIsFree(), (x, y, t.GetNetname())
        print("via removed (%.3f, %.3f) d %.2f" % (x, y, d))
        b.Remove(t)
        KEEP.append(t)
fp = pcbnew.FootprintLoad(libdir, NAME)
fp.SetFPID(pcbnew.LIB_ID("Rev3", NAME))
fp.SetReference("J5")
fp.SetValue("PE bond")
fp.SetPosition(V(X, Y))
b.Add(fp)
fp.SetField("Description", DESC)
fp.SetField("Datasheet", "")
for pad in fp.Pads():
    pad.SetNet(gnd)
fp.Value().SetVisible(False)
r = fp.Reference()
r.SetVisible(True)
pcbnew.SaveBoard(dst, b)
print("J5 at local (%.2f, %.2f) = abs (%.2f, %.2f), %s, removed vias %d -> %s" % (X, Y, X + 20, Y + 20, b.GetLayerName(fp.GetLayer()), len(KEEP), dst))
