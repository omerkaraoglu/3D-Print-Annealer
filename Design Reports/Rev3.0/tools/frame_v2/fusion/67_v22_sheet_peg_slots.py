"""67 - v2.2 final (coordinator decision): BOTH oven-sheet peg holes become slots sheet_peg_hole x (sheet_peg_hole +
sheet_peg_slot) = 3.2 x 3.9 along X. The two X-slots fix the y = 69.5 line and the rotation; x is located by the stud
slots themselves (FH2/FH7 radial = Y-slots, 0.25 across-clearance in x), so the frame grows about the pattern centre
within +-0.25. Only the patch is rebuilt (frame v6 final, socket cylinders unchanged).
Original 64 docstring (geometry recipe):
  * linked frame -> latest version
  * assembly parameters: peg1 (9.77, 69.5), peg2 (195.17, 69.5) (copied from the frame), sheet_peg_slot = 0.7
  * 'Oven sheet patch' rebuilt: outline flange + 20, window VA + 0.5, ten round dia-4.3 stud holes, P1 round
    dia 3.2, P2 a 3.2 x 3.9 slot along X (peg-to-peg growth), oven_sheet_t in front of Z_FRONT
  * 'Check - socket cylinders (hidden)' rebuilt: dia-12 'socket FHn' from Z -4.0 to +45 (tube top is -3.52 now)
Expects: frame v6 saved; run with the assembly active."""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

ASM = "Rev3.0 Frame v2 fit assembly"
CYL = "Check - socket cylinders (hidden)"
STUDXY = [(43.5, 8.75), (103.5, 8.75), (162.0, 8.75), (195.17, 40.5), (195.17, 98.5), (171.0, 161.2),
          (102.5, 161.2), (34.0, 161.2), (9.77, 98.5), (9.77, 40.5)]


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


def peg_slot(sk, n):
    L.rrect(sk, "peg%d_x - sheet_peg_slot / 2" % n, "peg%d_x + sheet_peg_slot / 2" % n,
            "peg%d_y - sheet_peg_hole / 2" % n, "peg%d_y + sheet_peg_hole / 2" % n, None)
    L.circle(sk, "peg%d_x - sheet_peg_slot / 2" % n, "peg%d_y" % n, "sheet_peg_hole")
    L.circle(sk, "peg%d_x + sheet_peg_slot / 2" % n, "peg%d_y" % n, "sheet_peg_hole")


def run(_context: str):
    L.check_doc(ASM)
    L.log("=== 67 start")
    root = L.root()
    for i in range(root.occurrences.count - 1, -1, -1):
        if root.occurrences.item(i).component.name == "Oven sheet patch":
            root.occurrences.item(i).deleteMe()
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
    peg_slot(sk, 1)
    peg_slot(sk, 2)
    big = max((sk.profiles.item(i) for i in range(sk.profiles.count)), key=lambda p: p.areaProperties().area)
    ex = c.features.extrudeFeatures
    ei = ex.createInput(big, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ei.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(L.VI("oven_sheet_t")),
                        adsk.fusion.ExtentDirections.NegativeExtentDirection)
    fe = ex.add(ei)
    fe.name = "Oven sheet patch"
    pb = fe.bodies.item(0)
    pb.name = "Oven sheet patch"
    L.set_appearance(pb, "Steel - Satin")
    L.set_param("sheet_peg_slot", "0.7 mm", "mm", "v2.2 final: BOTH peg holes in the sheet = slots sheet_peg_hole x "
                "(sheet_peg_hole + this) along X")
    L.log("67 patch %.3f cm3 bbox %s; inner loops %d" % (pb.physicalProperties.volume, L.bbox_mm(pb),
                                                        big.profileLoops.count - 1))
    L.show_iso()
    print(pb.physicalProperties.volume, L.bbox_mm(pb), big.profileLoops.count - 1)
