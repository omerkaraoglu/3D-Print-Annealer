import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1])
segs = []
for d in b.GetDrawings():
    if d.GetLayerName() == "User.Comments" and d.GetClass() in ("PCB_SHAPE",):
        s, e = d.GetStart(), d.GetEnd()
        segs.append([round(pcbnew.ToMM(v), 2) for v in (s.x, s.y, e.x, e.y)] + [d.GetShapeStr()])
json.dump(segs, open("cmts.json", "w"))
for s in segs[:80]: print(s)
