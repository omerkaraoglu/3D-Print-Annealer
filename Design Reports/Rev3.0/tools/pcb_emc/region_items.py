import pcbnew, sys
sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth")
from common import *
b = pcbnew.LoadBoard(sys.argv[1]); x0, y0, x1, y1 = map(float, sys.argv[2].split(","))
nets = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else None
def inb(p): return x0 <= p[0] <= x1 and y0 <= p[1] <= y1
for t in b.Tracks():
    s, e = L(t.GetStart()), L(t.GetEnd())
    if (inb(s) or inb(e)) and (not nets or t.GetNetname() in nets):
        print(t.GetClass()[4:], t.GetNetname(), t.GetLayerName(), [round(v, 3) for v in s], [round(v, 3) for v in e], (round(mm(t.GetWidth(pcbnew.F_Cu)), 3) if t.GetClass() == "PCB_VIA" else round(mm(t.GetWidth()), 3)), (round(mm(t.GetDrill()), 2) if t.GetClass() == "PCB_VIA" else ""))
for fp in b.GetFootprints():
    p = L(fp.GetPosition())
    if inb(p): print("FP", fp.GetReference(), [round(v, 2) for v in p], fp.GetOrientationDegrees())
for z in b.Zones():
    if z.GetZoneName().startswith("$teardrop"):
        bb = z.GetBoundingBox(); c = L(bb.GetCenter())
        if inb(c): print("TD", z.GetNetname(), z.GetLayerName(), [round(v, 2) for v in c])
