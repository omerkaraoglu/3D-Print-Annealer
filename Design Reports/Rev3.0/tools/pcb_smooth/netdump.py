"""List pads and track items of given nets. Usage: netdump.py board net1 [net2 ...]"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; O = 20
for n in sys.argv[2:]:
    print("== net", n, "class", b.FindNet(n).GetNetClassName() if b.FindNet(n) else None)
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == n:
                q = p.GetPosition(); s = p.GetSize(pcbnew.F_Cu)
                print("  pad %s.%s (%.3f,%.3f) size %.2fx%.2f drill %.2f shape %s" % (fp.GetReference(), p.GetNumber(), mm(q.x)-O, mm(q.y)-O, mm(s.x), mm(s.y), mm(p.GetDrillSize().x), p.GetShapeStr() if hasattr(p,'GetShapeStr') else p.GetShape(pcbnew.F_Cu)))
    for t in b.GetTracks():
        if t.GetNetname() == n:
            s, e = t.GetStart(), t.GetEnd()
            print("  %s %s (%.3f,%.3f)-(%.3f,%.3f) w %.2f" % (t.GetClass(), b.GetLayerName(t.GetLayer()), mm(s.x)-O, mm(s.y)-O, mm(e.x)-O, mm(e.y)-O, mm(t.GetWidth(pcbnew.F_Cu) if t.GetClass() == 'PCB_VIA' else t.GetWidth())))
