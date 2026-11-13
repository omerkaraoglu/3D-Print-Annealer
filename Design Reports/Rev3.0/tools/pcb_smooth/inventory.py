"""Inventory of a board: layers, outline, zones, holes, track/via/arc counts. Usage: inventory.py board.kicad_pcb"""
import sys, pcbnew
from collections import Counter
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
O = 20.0
print("layers:", [(b.GetLayerName(l), l) for l in b.GetEnabledLayers().CuStack()])
c = Counter(); vn = Counter()
for t in b.GetTracks():
    c[t.GetClass()] += 1
    if t.GetClass() == 'PCB_VIA':
        vn[t.GetNetname()] += 1
print(c); print("vias by net:", vn.most_common(12))
print("Edge.Cuts:")
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        s, e = d.GetStart(), d.GetEnd()
        print("  ", d.GetShapeStr(), round(mm(s.x)-O,3), round(mm(s.y)-O,3), round(mm(e.x)-O,3), round(mm(e.y)-O,3))
for fp in b.GetFootprints():
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.Edge_Cuts:
            print("  fp edge", fp.GetReference(), g.GetShapeStr(), round(mm(g.GetStart().x)-O,2), round(mm(g.GetStart().y)-O,2), round(mm(g.GetEnd().x)-O,2), round(mm(g.GetEnd().y)-O,2))
print("zones:")
for z in b.Zones():
    bb = z.GetBoundingBox()
    lay = ",".join(b.GetLayerName(l) for l in z.GetLayerSet().Seq())
    print("  %-28s %-14s ka=%d prio=%d corners=%d smooth=%d r=%.2f minth=%.2f clr=%.2f bbox=(%.1f,%.1f)-(%.1f,%.1f) %s" % (
        z.GetNetname() or '-', z.GetZoneName()[:14], z.GetIsRuleArea(), z.GetAssignedPriority(), z.GetNumCorners(),
        z.GetCornerSmoothingType(), mm(z.GetCornerRadius()), mm(z.GetMinThickness()), mm(z.GetLocalClearance() or 0) if hasattr(z,'GetLocalClearance') else -1,
        mm(bb.GetLeft())-O, mm(bb.GetTop())-O, mm(bb.GetRight())-O, mm(bb.GetBottom())-O, lay))
print("holes / H refs:")
for fp in b.GetFootprints():
    if fp.GetReference().startswith('H') or 'Mounting' in str(fp.GetFPID().GetUniStringLibId()):
        p = fp.GetPosition(); print("  ", fp.GetReference(), str(fp.GetFPID().GetUniStringLibId()), round(mm(p.x)-O,3), round(mm(p.y)-O,3))
print("footprints:", len(b.GetFootprints()))
