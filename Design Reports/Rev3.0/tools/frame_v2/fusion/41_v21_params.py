"""41 - v2.1 parameter changes (coordinator review items 1-4):
  * symmetric flange / stud lines: fl_x0 = outer_x0 - flange_w, stud_xl = outer_x0 - stud_offset; the left-side
    parameters stud_offset_l / flange_w_l are deleted (socket rule is now >= 6.5 from the PCB outline and
    >= 11.0 from H1..H9; the left board edge at x 20.0 gives 10.23)
  * new stud_slot = 0.8 (stud holes become 4.5 x 5.3 stadium slots along the edge), tail_wall_step_y = 129.0
  * 'Tail wall block sketch': the end line is placed so the step face is at tail_wall_step_y AT Z_PCB
    (tail_wall_step_y - (Z_PCB - Z_FRONT) * tan(draft) at Z_FRONT); the v2.0 parameter tail_wall_y0 is deleted
  * 'Window' cut reaches Z_PCB + 1 (it now trims the extended support ribs, which are inserted before it)
  * stud positions fh1..fh10 = fv2lib.STUDS (new symmetric 10-hole pattern)
Expects: 40 done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

OLD_TAIL = "pocket_y1 - ( Z_SHELF_BACK - Z_FRONT ) * tan(draft)"
NEW_TAIL = "tail_wall_step_y - ( Z_PCB - Z_FRONT ) * tan(draft)"
SIDE = {"T": "top edge, slot along X", "R": "right edge, slot along Y", "B": "bottom edge, slot along X",
        "L": "left edge, slot along Y"}


def run(_context: str):
    L.check_doc()
    L.log("=== 41 start")
    ups = L.des().userParameters
    L.set_param("fl_x0", "outer_x0 - flange_w", "mm", "flange outline left at Z_FRONT (v2.1 symmetric)")
    L.set_param("stud_xl", "outer_x0 - stud_offset", "mm", "left stud line x (v2.1 symmetric)")
    for n in ("stud_offset_l", "flange_w_l"):
        p = ups.itemByName(n)
        if p is not None:
            if not p.deleteMe():
                raise RuntimeError("could not delete " + n)
    L.set_param("stud_slot", "0.8 mm", "mm",
                "v2.1 stud slot: hole = stadium stud_hole x (stud_hole + stud_slot) along the edge (thermal growth "
                "PA6-GF30 vs steel 0.3-0.5 mm over the pattern at dT 40-60 K)")
    L.set_param("tail_wall_step_y", "129.0 mm", "mm",
                "v2.1: tail-pocket side walls stay at Z_PCB for y < this (at Z_PCB) and rise to Z_TROUGH_TOP beyond "
                "(H6/H7 ear rounds end at y 128.3)")
    sk = L.root().sketches.itemByName("Tail wall block sketch")
    hit = 0
    for i in range(sk.sketchDimensions.count):
        d = sk.sketchDimensions.item(i)
        if d.parameter is not None and d.parameter.expression.replace(" ", "") == OLD_TAIL.replace(" ", ""):
            d.parameter.expression = NEW_TAIL
            hit += 1
    if hit != 1:
        raise RuntimeError("tail wall dimension not found (%d)" % hit)
    p = ups.itemByName("tail_wall_y0")
    if p is not None:
        p.deleteMe()
    win = adsk.fusion.ExtrudeFeature.cast(L.feature("Window"))
    adsk.fusion.DistanceExtentDefinition.cast(win.extentOne).distance.expression = "Z_PCB - Z_SEAT + 1 mm"
    for name, side, xe, ye in L.STUDS:
        n = name.lower()
        L.set_param(n + "_x", xe, "mm", "stud slot %s x abs (KiCad), %s; hole_pattern_calc.py v2.1" % (name, SIDE[side]))
        L.set_param(n + "_y", ye, "mm", "stud slot %s y abs (KiCad, y down), %s" % (name, SIDE[side]))
    n, bad = L.timeline_health()
    L.log("41 %s; timeline %d unhealthy %s; fl_x0 %.3f stud_xl %.3f" % (L.body_stats(), n, bad, L.P("fl_x0"),
                                                                       L.P("stud_xl")))
    L.show_iso()
    print(L.body_stats(), n, bad, L.P("fl_x0"), L.P("stud_xl"))
