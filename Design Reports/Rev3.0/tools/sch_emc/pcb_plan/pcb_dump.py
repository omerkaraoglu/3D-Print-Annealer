import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1])
want = sys.argv[2].split(',')
out = {}
for fp in b.GetFootprints():
    r = fp.GetReference()
    if want != ['*'] and r not in want:
        continue
    p = fp.GetPosition(); bb = fp.GetCourtyard(pcbnew.F_CrtYd) if hasattr(fp,'GetCourtyard') else None
    box = fp.GetBoundingBox(False, False)
    pads = [(pd.GetNumber(), pd.GetNetname(), round(pcbnew.ToMM(pd.GetPosition().x),2), round(pcbnew.ToMM(pd.GetPosition().y),2), round(pcbnew.ToMM(pd.GetSize().x),2), round(pcbnew.ToMM(pd.GetSize().y),2)) for pd in fp.Pads()]
    out[r] = dict(val=fp.GetValue(), fp=str(fp.GetFPID().GetLibItemName()), x=round(pcbnew.ToMM(p.x),2), y=round(pcbnew.ToMM(p.y),2), rot=fp.GetOrientationDegrees(),
                  layer=fp.GetLayerName(), bbox=[round(pcbnew.ToMM(v),2) for v in (box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom())], pads=pads,
                  fields={f.GetName(): f.GetText() for f in fp.GetFields()})
json.dump(out, open(sys.argv[3], 'w'), indent=1)
o = b.GetBoardEdgesBoundingBox(); print('edges', [round(pcbnew.ToMM(v),2) for v in (o.GetLeft(), o.GetTop(), o.GetRight(), o.GetBottom())])
