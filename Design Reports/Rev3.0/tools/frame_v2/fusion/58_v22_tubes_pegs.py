"""58 - v2.2 (coordinator, CadQuery cross-check):
  A. stud_boss_h is now the tube height above the FLANGE BACK: Z_STUD_TOP = Z_FLANGE_BACK + stud_boss_h = -3.52
     (washer/nut seat); 'Stud FHn tube' extrudes stud_boss_h + flange_t down from Z_STUD_TOP (buried in the flange),
     'Stud FHn rib' runs the full tube height (stud_boss_h from the flange back). Stack 7.5 frame + 1.0 washer +
     5 nyloc = 13.5 from the sheet -> PEM FH-M4-18.
  B. pegs P1/P2 moved to the side flanges on the stud lines at mid-height: peg1 = (stud_xl, datum_y), peg2 =
     (stud_xr, datum_y), front face of the flange (Z_FRONT), same 3 x 0.8, 0.5 deg; new parameters datum_x =
     (peg1_x + peg2_x) / 2 = 102.47, datum_y = 69.5. The old cell-floor pegs disappear (same feature, moved).
  The ten axis-aligned 'Stud FHn slot' cuts (+ sketches) are deleted; 59 cuts the radial slots.
Expects: frame v5 active."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)


def run(_context: str):
    L.check_doc()
    L.log("=== 58 start")
    L.set_param("stud_boss_h", "5 mm", "mm", "v2.2: stud tube height ABOVE THE FLANGE BACK (tube top = washer/nut seat); "
                "stack 7.5 + washer 1.0 + nyloc 5 = 13.5 -> PEM FH-M4-18")
    L.set_param("Z_STUD_TOP", "Z_FLANGE_BACK + stud_boss_h", "mm", "v2.2: stud tube top = DIN 9021 washer seat")
    L.set_param("datum_y", "69.5 mm", "mm", "v2.2 thermal datum y (abs, y down): side pegs at mid-height")
    L.set_param("peg1_x", "stud_xl", "mm", "v2.2 peg P1 on the left flange, on the stud line")
    L.set_param("peg1_y", "datum_y", "mm", "v2.2 peg P1 y abs")
    L.set_param("peg2_x", "stud_xr", "mm", "v2.2 peg P2 on the right flange, on the stud line")
    L.set_param("peg2_y", "datum_y", "mm", "v2.2 peg P2 y abs")
    L.set_param("datum_x", "( peg1_x + peg2_x ) / 2", "mm", "v2.2 thermal datum x = peg midpoint (102.47)")
    for name, side, xe, ye in L.STUDS:
        t = adsk.fusion.ExtrudeFeature.cast(L.feature("Stud %s tube" % name))
        adsk.fusion.DistanceExtentDefinition.cast(t.extentOne).distance.expression = "stud_boss_h + flange_t"
        r = adsk.fusion.ExtrudeFeature.cast(L.feature("Stud %s rib" % name))
        adsk.fusion.DistanceExtentDefinition.cast(r.extentOne).distance.expression = "stud_boss_h"
    tl = L.des().timeline
    gone = 0
    for i in range(tl.count - 1, -1, -1):
        it = tl.item(i)
        if it.name.startswith("Stud FH") and it.name.endswith("slot"):
            it.entity.deleteMe()
            gone += 1
    for name, side, xe, ye in L.STUDS:
        sk = L.root().sketches.itemByName("Stud %s slot sketch" % name)
        if sk is not None:
            sk.deleteMe()
    n, bad = L.timeline_health()
    L.log("58 %s; Z_STUD_TOP %.3f; pegs (%.3f %.3f) (%.3f %.3f); datum (%.3f %.3f); deleted %d slot items; "
          "timeline %d unhealthy %s" % (L.body_stats(), L.P("Z_STUD_TOP"), L.P("peg1_x"), L.P("peg1_y"), L.P("peg2_x"),
                                       L.P("peg2_y"), L.P("datum_x"), L.P("datum_y"), gone, n, bad))
    L.show_iso()
    print(L.body_stats(), L.P("Z_STUD_TOP"), L.P("datum_x"), gone, n, bad)
