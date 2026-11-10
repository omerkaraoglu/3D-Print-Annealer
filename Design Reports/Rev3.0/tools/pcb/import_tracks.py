"""Add routed tracks/vias (JSON from the router) to a board and save."""
import pcbnew, json, sys
src, trk, out = sys.argv[1], sys.argv[2], sys.argv[3]
b = pcbnew.LoadBoard(src)
L = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
data = json.load(open(trk))
n = 0
for t in data:
    net = b.FindNet(t["net"])
    if t["via"]:
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I_MM(t["x"], t["y"]))
        v.SetWidth(pcbnew.FromMM(t["d"])); v.SetDrill(pcbnew.FromMM(t["drill"]))
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        if net: v.SetNet(net)
        b.Add(v)
    else:
        s = pcbnew.PCB_TRACK(b); s.SetStart(pcbnew.VECTOR2I_MM(t["x1"], t["y1"])); s.SetEnd(pcbnew.VECTOR2I_MM(t["x2"], t["y2"]))
        s.SetWidth(pcbnew.FromMM(t["w"])); s.SetLayer(L[t["layer"]])
        if net: s.SetNet(net)
        b.Add(s)
    n += 1
pcbnew.SaveBoard(out, b)
print("added", n, "items ->", out)
