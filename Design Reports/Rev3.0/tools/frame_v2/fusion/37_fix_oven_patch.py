"""37 - FIX: rebuild the 'Oven sheet patch' component. Its outline starts at negative abs coordinates
(x -17.73, y -17.75); fv2lib's origin dimensions could not hold a negative expression, so Fusion flipped those two
edges to +17.73 / +17.75 (patch shifted vs the frame, seen in the iso-front screenshot). fv2lib._dim_x/_dim_y now
write -( expr ) for points on the negative side. Same geometry recipe as 32.
Expects: 32..36a done."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

ASM = "Rev3.0 Frame v2 fit assembly"
PARAMS = [  # copied from the frame document 'Rev3.0 Frame v2' (same names), plus assembly-only ones
    ("board_dz", "0.08 mm", "KiCad STEP has no copper/mask: board occurrence moved +0.08 so the PCB back is at Z 0"),
    ("Z_FRONT", "-11.02 mm", "frame Z_FRONT (copied)"), ("Z_GLASS", "-10.32 mm", "frame Z_GLASS (copied)"),
    ("Z_PANEL_BACK", "-5.0 mm", "frame Z_PANEL_BACK (copied)"), ("Z_SEAT", "-4.6 mm", "frame Z_SEAT (copied)"),
    ("oven_sheet_t", "1.0 mm", "frame oven_sheet_t (copied)"),
    ("panel_x0", "20.02 mm", "copied"), ("panel_x1", "184.92 mm", "copied"), ("panel_y0", "19.00 mm", "copied"),
    ("panel_y1", "119.00 mm", "copied"), ("va_x0", "26.31 mm", "copied"), ("va_x1", "181.39 mm", "copied"),
    ("va_y0", "23.23 mm", "copied"), ("va_y1", "110.15 mm", "copied"),
    ("fl_x0", "2.27 mm", "frame flange outline (copied)"), ("fl_x1", "201.67 mm", "copied"),
    ("fl_y0", "2.25 mm", "copied"), ("fl_y1", "167.70 mm", "copied"), ("flange_r", "12 mm", "copied"),
    ("sheet_inset", "0.5 mm", "Formex sheet = panel outline - this per side (v1 SHEET_INSET)"),
    ("gasket_out_inset", "0.3 mm", "gasket outer = glass outline - this (v1)"),
    ("gasket_in_margin", "1.0 mm", "gasket inner = VA + this (v1)"),
    ("cutout_margin", "0.5 mm", "oven-sheet window = VA + this (v1)"), ("patch_margin", "20 mm", "patch = flange + this"),
    ("sheet_stud_hole", "4.3 mm", "stud holes in the oven-sheet patch (brief)"),
    ("sheet_peg_hole", "3.2 mm", "peg holes in the oven-sheet patch"),
    ("peg1_x", "32.5 mm", "copied"), ("peg1_y", "146.0 mm", "copied"), ("peg2_x", "172.5 mm", "copied"),
    ("peg2_y", "146.0 mm", "copied"),
]
STUDXY = [(49.0, 8.75), (108.0, 8.75), (159.0, 8.75), (195.17, 44.75), (195.17, 94.25), (168.0, 161.2),
          (102.0, 161.2), (36.0, 161.2), (8.77, 94.25), (8.77, 44.75)]


def comp_sketch(comp, name, z_expr):
    cps = comp.constructionPlanes
    pi = cps.createInput()
    pi.setByOffset(comp.xYConstructionPlane, L.VI(z_expr))
    pl = cps.add(pi)
    pl.name = name + " plane"
    pl.isLightBulbOn = False
    sk = comp.sketches.add(pl)
    sk.name = name + " sketch"
    return sk


def comp_extrude(comp, prof, dist_expr, direction, name):
    ex = comp.features.extrudeFeatures
    ei = ex.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(L.VI(dist_expr)),
                        adsk.fusion.ExtentDirections.PositiveExtentDirection if direction > 0
                        else adsk.fusion.ExtentDirections.NegativeExtentDirection)
    f = ex.add(ei)
    f.name = name
    f.bodies.item(0).name = name
    return f.bodies.item(0)


def run(_context: str):
    L.check_doc(ASM)
    root = L.root()
    L.log("=== 37 start")
    for i in range(root.occurrences.count - 1, -1, -1):
        o = root.occurrences.item(i)
        if o.component.name == "Oven sheet patch":
            o.deleteMe()
            L.log("37 deleted the flipped oven-sheet patch")
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    c = occ.component
    c.name = "Oven sheet patch"
    sk = comp_sketch(c, "Oven sheet patch", "Z_FRONT")
    L.rrect(sk, "fl_x0 - patch_margin", "fl_x1 + patch_margin", "fl_y0 - patch_margin", "fl_y1 + patch_margin",
            "flange_r + patch_margin")
    L.rrect(sk, "va_x0 - cutout_margin", "va_x1 + cutout_margin", "va_y0 - cutout_margin", "va_y1 + cutout_margin",
            "1 mm")
    for k in range(1, 11):
        L.circle(sk, "fh%d_x" % k, "fh%d_y" % k, "sheet_stud_hole")
    L.circle(sk, "peg1_x", "peg1_y", "sheet_peg_hole")
    L.circle(sk, "peg2_x", "peg2_y", "sheet_peg_hole")
    big = max((sk.profiles.item(i) for i in range(sk.profiles.count)), key=lambda p: p.areaProperties().area)
    b = comp_extrude(c, big, "oven_sheet_t", -1, "Oven sheet patch")
    L.set_appearance(b, "Steel - Satin")
    bb = L.bbox_mm(b)
    L.log("37 patch %.3f cm3 bbox %s" % (b.physicalProperties.volume, bb))
    L.show_iso()
    print(b.physicalProperties.volume, bb)
