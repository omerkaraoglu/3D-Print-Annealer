import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
want = ("B2", "B3", "PCLK", "HSYNC", "VSYNC", "DE")
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        n = t.GetNetname()
        if any(n.endswith("/" + w) or n.endswith("/" + w + "_T") for w in want) or n in ("+5V",):
            p = t.GetPosition(); print("via", n, round(pcbnew.ToMM(p.x), 2), round(pcbnew.ToMM(p.y), 2))
# zones: In2 +5V island bbox
for z in b.Zones():
    if z.GetNetname() == "+5V":
        bb = z.GetBoundingBox(); print("zone +5V", z.GetLayerName(), [round(pcbnew.ToMM(v), 1) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())])
