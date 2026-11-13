"""Task 5: copper pours.  For every copper zone (net != '', not a rule area):
- corner smoothing = fillet, radius 1.0 mm (0.5 mm for the +5V island, whose lobe is 15 mm wide with 1 mm steps),
- minimum thickness 0.5 mm on the outer GND pours (removes necks / slivers < 0.5 mm), 0.25 mm on the inner planes;
  thermal relief / clearance unchanged,
- outline: the SELV pours stopped at x = 161 (a 3 mm copper-free strip along the right edge left over from the
  pass-1 161 mm board); they now follow the board outline at the 0.5 mm edge inset (x = 163.5).  The board corners
  (R 3) and the ears are followed by the fill through the 0.5 mm edge clearance, so the outline keeps straight edges.
Rule areas (keep-outs, DRC rule areas, antenna) are not touched.  Fills all zones and saves.
Usage: t5_zones.py in.kicad_pcb out.kicad_pcb"""
import sys, pcbnew
from common import *
b = pcbnew.LoadBoard(sys.argv[1])
SMOOTH = {'+5V': 0.5}
for z in b.Zones():
    if z.GetIsRuleArea() or not z.GetNetname():
        continue
    o = z.Outline()
    moved = 0
    for i in range(o.TotalVertices()):
        p = L(o.CVertex(i))
        if abs(p[0] - 161.0) < 1e-6:
            o.SetVertex(i, V(163.5, p[1])); moved += 1
    z.SetCornerSmoothingType(pcbnew.ZONE_SETTINGS.SMOOTHING_FILLET)
    z.SetCornerRadius(pcbnew.FromMM(SMOOTH.get(z.GetNetname(), 1.0)))
    # outer GND pours: 0.5 mm minimum width, so the filler itself drops every neck / sliver / spike narrower than
    # 0.5 mm (the copper they carried is re-tied by the stitching vias of task 6); the solid inner planes keep 0.25 mm
    z.SetMinThickness(pcbnew.FromMM(0.5 if z.GetFirstLayer() in (pcbnew.F_Cu, pcbnew.B_Cu) else 0.25))
    # (island removal: switched to 'always' by stitch_apply.py once the islands have their stitching vias)
    z.SetNeedRefill(True)
    print("%-6s %-16s layer %-5s vertices %d moved %d smoothing fillet %.1f minth %.2f" % (
        z.GetNetname(), z.GetZoneName(), b.GetLayerName(z.GetFirstLayer()), o.TotalVertices(), moved,
        mm(z.GetCornerRadius()), mm(z.GetMinThickness())))
# filled separately by fill.py (needs the project rules)
pcbnew.SaveBoard(sys.argv[2], b)
print("saved", sys.argv[2])
