import pcbnew, sys
sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth")
from common import *
b = pcbnew.LoadBoard(sys.argv[1])
refs = sys.argv[2].split(",")
pads = {}
for fp in b.GetFootprints():
    if fp.GetReference() in refs:
        print(fp.GetReference(), fp.GetFPIDAsString(), "pos", L(fp.GetPosition()), "rot", fp.GetOrientationDegrees(), "path", fp.GetPath().AsString(), "layer", fp.GetLayerName())
        print("   fields", [(f.GetName(), f.GetText()[:40], f.IsVisible()) for f in fp.GetFields()])
        print("   sheet", fp.GetSheetname(), fp.GetSheetfile(), "attrs", fp.GetAttributes())
        for p in fp.Pads():
            pads[(fp.GetReference(), p.GetNumber())] = L(p.GetPosition())
            print("   pad", p.GetNumber(), p.GetNetname(), [round(v, 3) for v in L(p.GetPosition())])
for t in b.Tracks():
    s, e = L(t.GetStart()), L(t.GetEnd())
    for (r, n), q in pads.items():
        if close(s, q, 0.05) or close(e, q, 0.05) or (t.GetClass() == "PCB_VIA" and close(s, q, 1.5)):
            print("   item", t.GetClass(), t.GetNetname(), t.GetLayerName(), [round(v, 3) for v in s], [round(v, 3) for v in e], round(mm(t.GetWidth()), 3) if t.GetClass() != "PCB_VIA" else "", "@", r, n)
