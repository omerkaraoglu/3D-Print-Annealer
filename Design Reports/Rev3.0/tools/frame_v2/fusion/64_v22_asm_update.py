"""64 - v2.2 fit assembly update:
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


def run(_context: str):
    app = adsk.core.Application.get()
    L.check_doc(ASM)
    L.log("=== 64 start")
    refs = app.activeDocument.documentReferences
    upd = [(refs.item(i).dataFile.name, refs.item(i).version, refs.item(i).getLatestVersion())
           for i in range(refs.count) if refs.item(i).isOutOfDate]
    L.set_param("peg1_x", "9.77 mm", "mm", "v2.2 peg P1 x abs (left flange, copied from the frame)")
    L.set_param("peg1_y", "69.5 mm", "mm", "v2.2 peg P1 y abs (datum_y)")
    L.set_param("peg2_x", "195.17 mm", "mm", "v2.2 peg P2 x abs (right flange)")
    L.set_param("peg2_y", "69.5 mm", "mm", "v2.2 peg P2 y abs (datum_y)")
    L.set_param("sheet_peg_slot", "0.7 mm", "mm", "v2.2: P2 hole in the sheet = slot sheet_peg_hole x (sheet_peg_hole "
                "+ this) along X (peg-to-peg thermal growth)")
    root = L.root()
    for i in range(root.occurrences.count - 1, -1, -1):
        if root.occurrences.item(i).component.name in ("Oven sheet patch", CYL):
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
    L.circle(sk, "peg1_x", "peg1_y", "sheet_peg_hole")
    L.rrect(sk, "peg2_x - sheet_peg_slot / 2", "peg2_x + sheet_peg_slot / 2", "peg2_y - sheet_peg_hole / 2",
            "peg2_y + sheet_peg_hole / 2", None)
    L.circle(sk, "peg2_x - sheet_peg_slot / 2", "peg2_y", "sheet_peg_hole")
    L.circle(sk, "peg2_x + sheet_peg_slot / 2", "peg2_y", "sheet_peg_hole")
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
    cy = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    cy.component.name = CYL
    tb = adsk.fusion.TemporaryBRepManager.get()
    bf = cy.component.features.baseFeatures.add()
    bf.startEdit()
    for k, (x, y) in enumerate(STUDXY, 1):
        cb = tb.createCylinderOrCone(adsk.core.Point3D.create(x / 10, -y / 10, -0.40), 0.6,
                                     adsk.core.Point3D.create(x / 10, -y / 10, 4.5), 0.6)
        nb = cy.component.bRepBodies.add(cb, bf)
        nb.name = "socket FH%d" % k
    bf.finishEdit()
    cy.isLightBulbOn = False
    L.log("64 refs %s; patch %.3f cm3 bbox %s; inner loops %d" % (upd, pb.physicalProperties.volume, L.bbox_mm(pb),
                                                                 big.profileLoops.count - 1))
    L.show_iso()
    print(upd, pb.physicalProperties.volume, L.bbox_mm(pb), big.profileLoops.count - 1)
