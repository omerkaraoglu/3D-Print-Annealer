"""List pads/tracks/vias inside a local-coordinate box. Usage: region.py board x0 y0 x1 y1 [layerfilter]"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; O = 20
x0, y0, x1, y1 = map(float, sys.argv[2:6]); lf = sys.argv[6] if len(sys.argv) > 6 else None
inb = lambda x, y: x0 <= x <= x1 and y0 <= y <= y1
for fp in b.GetFootprints():
    for p in fp.Pads():
        q = p.GetPosition(); x, y = mm(q.x)-O, mm(q.y)-O
        if inb(x, y):
            s = p.GetSize(pcbnew.F_Cu)
            print("pad %-5s.%-3s (%.2f,%.2f) %.2fx%.2f drill %.2f %-20s %s" % (fp.GetReference(), p.GetNumber(), x, y, mm(s.x), mm(s.y), mm(p.GetDrillSize().x), p.GetNetname()[:20], "THT" if p.GetDrillSize().x else b.GetLayerName(p.GetLayer())))
for t in b.GetTracks():
    s, e = t.GetStart(), t.GetEnd(); a = (mm(s.x)-O, mm(s.y)-O); c = (mm(e.x)-O, mm(e.y)-O)
    if (inb(*a) or inb(*c)) and (lf is None or b.GetLayerName(t.GetLayer()) == lf or t.GetClass() == 'PCB_VIA'):
        print("%s %s (%.2f,%.2f)-(%.2f,%.2f) w %.2f %s" % (t.GetClass()[4:], b.GetLayerName(t.GetLayer()), a[0], a[1], c[0], c[1], mm(t.GetWidth(pcbnew.F_Cu) if t.GetClass() == 'PCB_VIA' else t.GetWidth()), t.GetNetname()))
