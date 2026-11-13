"""32 - fit assembly: (a) move the board occurrence +0.08 mm in Z (KiCad's STEP omits copper + mask, so the
physical PCB back lands on Z 0) and capture the position; (b) assembly user parameters (copied from the frame
document, comments say so); (c) three local components:
  'Formex sheet'          panel outline - sheet_inset per side, R1, Z_PANEL_BACK..Z_SEAT        (grey)
  'Gasket (compressed)'   outer = panel outline - 0.3, inner = VA + 1.0, R1, Z_FRONT..Z_GLASS    (red translucent)
  'Oven sheet patch'      flange outline + 20 (R flange_r + 20), oven_sheet_t in front of Z_FRONT, window
                          VA + 0.5 R1, dia 4.3 stud holes at FH1..FH10, dia 3.2 peg holes at P1/P2 (steel)
(d) appearances: PCB body green if it is not coloured by the STEP.
Expects: 31 import finished."""
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
    des = L.des()
    root = L.root()
    L.log("=== 32 start")
    for n, e, c in PARAMS:
        L.set_param(n, e, "mm", c)
    for k, (x, y) in enumerate(STUDXY, 1):
        L.set_param("fh%d_x" % k, "%.6f mm" % x, "mm", "stud hole FH%d x abs (copied from the frame)" % k)
        L.set_param("fh%d_y" % k, "%.6f mm" % y, "mm", "stud hole FH%d y abs (copied)" % k)
    # (a) board shift
    bocc = [root.occurrences.item(i) for i in range(root.occurrences.count)
            if root.occurrences.item(i).component.name == "Rev3.0 PCB full (KiCad STEP)"][0]
    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(0, 0, L.P("board_dz") / 10.0)
    bocc.transform2 = m
    if des.snapshots.hasPendingSnapshot:
        des.snapshots.add()
    L.log("32 board occurrence z offset now %.4f mm" % (bocc.transform2.translation.z * 10))
    # (c) parts
    parts = {}
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    c = occ.component
    c.name = "Formex sheet"
    sk = comp_sketch(c, "Formex sheet", "Z_PANEL_BACK")
    L.rrect(sk, "panel_x0 + sheet_inset", "panel_x1 - sheet_inset", "panel_y0 + sheet_inset", "panel_y1 - sheet_inset",
            "1 mm")
    parts["Formex sheet"] = comp_extrude(c, sk.profiles.item(0), "Z_SEAT - Z_PANEL_BACK", +1, "Formex sheet")
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    c = occ.component
    c.name = "Gasket (compressed)"
    sk = comp_sketch(c, "Gasket", "Z_FRONT")
    L.rrect(sk, "panel_x0 + gasket_out_inset", "panel_x1 - gasket_out_inset", "panel_y0 + gasket_out_inset",
            "panel_y1 - gasket_out_inset", "1 mm")
    L.rrect(sk, "va_x0 - gasket_in_margin", "va_x1 + gasket_in_margin", "va_y0 - gasket_in_margin",
            "va_y1 + gasket_in_margin", "1 mm")
    ring = [sk.profiles.item(i) for i in range(sk.profiles.count) if sk.profiles.item(i).profileLoops.count == 2]
    parts["Gasket (compressed)"] = comp_extrude(c, ring[0], "Z_GLASS - Z_FRONT", +1, "Gasket (compressed)")
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
    big = max((sk.profiles.item(i) for i in range(sk.profiles.count)),
              key=lambda p: p.areaProperties().area)
    parts["Oven sheet patch"] = comp_extrude(c, big, "oven_sheet_t", -1, "Oven sheet patch")
    # appearances
    L.set_appearance(parts["Formex sheet"], "Plastic - Matte (Gray)")
    L.set_appearance(parts["Gasket (compressed)"], "Plastic - Translucent Matte (Red)")
    L.set_appearance(parts["Oven sheet patch"], "Steel - Satin")
    msg = []
    for n, b in parts.items():
        bb = b.boundingBox
        msg.append("%s %.3f cm3 z %.3f..%.3f" % (n, b.physicalProperties.volume, bb.minPoint.z * 10, bb.maxPoint.z * 10))
    L.log("32 parts: " + "; ".join(msg))
    L.show_iso()
    print(msg)
