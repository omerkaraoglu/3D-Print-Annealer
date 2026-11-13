"""Write every track / arc (as chords) / via of a board in the track-JSON format of tools/pcb (KiCad coordinates, +20 mm),
so tools/pcb/mains2_check.py can test SELV copper against the mains pads.  Usage: tracks_json.py board out.json"""
import sys, json, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; out = []
for t in b.Tracks():
    n = t.GetNetname()
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition(); out.append(dict(net=n, via=True, x=mm(p.x), y=mm(p.y), d=mm(t.GetWidth(pcbnew.F_Cu))))
    elif t.GetClass() == 'PCB_ARC':
        import math
        c = t.GetCenter(); r = mm(t.GetRadius()); a0 = t.GetArcAngleStart().AsRadians(); da = t.GetAngle().AsRadians()
        k = max(2, int(abs(da) / 0.1)); pts = [(mm(c.x) + r * math.cos(a0 + da * i / k), mm(c.y) + r * math.sin(a0 + da * i / k)) for i in range(k + 1)]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            out.append(dict(net=n, via=False, x1=x1, y1=y1, x2=x2, y2=y2, w=mm(t.GetWidth())))
    else:
        s, e = t.GetStart(), t.GetEnd()
        out.append(dict(net=n, via=False, x1=mm(s.x), y1=mm(s.y), x2=mm(e.x), y2=mm(e.y), w=mm(t.GetWidth())))
json.dump(out, open(sys.argv[2], 'w')); print(len(out), "items")
