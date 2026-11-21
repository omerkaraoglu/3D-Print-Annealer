import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1])
out = {"fps": {}, "tracks": []}
for fp in b.GetFootprints():
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    out["fps"][fp.GetReference()] = [pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]
for t in b.GetTracks():
    if t.GetClass() in ("PCB_TRACK", "PCB_ARC"):
        s, e = t.GetStart(), t.GetEnd()
        out["tracks"].append([pcbnew.ToMM(v) for v in (s.x, s.y, e.x, e.y, t.GetWidth())] + [t.GetNetname(), t.GetLayerName()])
json.dump(out, open(sys.argv[2], "w"))
print(len(out["fps"]), len(out["tracks"]))
