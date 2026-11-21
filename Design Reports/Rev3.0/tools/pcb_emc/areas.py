import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1])
for z in b.Zones():
    if z.GetIsRuleArea():
        bb = z.GetBoundingBox()
        o = z.Outline().Outline(0)
        print(z.GetZoneName() or "-", [round(pcbnew.ToMM(v) - 20, 2) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())], o.PointCount(),
              "tracks" if z.GetDoNotAllowTracks() else "", "vias" if z.GetDoNotAllowVias() else "", "fill" if z.GetDoNotAllowZoneFills() else "",
              [b.GetLayerName(l) for l in z.GetLayerSet().Seq()][:4])
