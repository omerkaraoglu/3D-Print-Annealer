import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1]); out = []
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.F_SilkS:
        bb = d.GetBoundingBox(); out.append([pcbnew.ToMM(bb.GetLeft()) - 20, pcbnew.ToMM(bb.GetTop()) - 20, pcbnew.ToMM(bb.GetRight()) - 20, pcbnew.ToMM(bb.GetBottom()) - 20, d.GetClass()])
json.dump(out, open(sys.argv[2], "w")); print(len(out))
