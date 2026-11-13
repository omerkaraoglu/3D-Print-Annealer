"""56 - (v2.1 final copy of 50: hole shift FH1 43.5, FH2 103.5, sides 40.5 / 98.5) fit assembly update:
  * linked frame -> latest version (DocumentReference.getLatestVersion)
  * assembly parameters copied from the frame: fl_x0 3.27 (symmetric flange), fh1..fh10 = new pattern; the
    'Oven sheet patch' sketch is parametric, so outline and its round dia 4.3 stud holes follow
  * hidden check component 'Check - socket cylinders (hidden)' rebuilt: per stud a dia-12 socket cylinder
    Z -6.5 .. +45 ('socket FHn', vs the board incl. DS1) and one from just above the tube top Z_STUD_TOP + 0.01
    .. +45 ('socket above tube FHn', vs the frame's own wall / bosses)
Expects: frame v2.1 saved (47); assembly active."""
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
Z_STUD_TOP = -6.02


def run(_context: str):
    app = adsk.core.Application.get()
    L.check_doc(ASM)
    L.log("=== 56 start")
    refs = app.activeDocument.documentReferences
    upd = []
    for i in range(refs.count):
        r = refs.item(i)
        if r.isOutOfDate:
            upd.append((r.dataFile.name, r.version, r.getLatestVersion()))
    L.set_param("fl_x0", "3.27 mm", "mm", "frame flange outline left (copied, v2.1 symmetric)")
    for k, (x, y) in enumerate(STUDXY, 1):
        L.set_param("fh%d_x" % k, "%.6f mm" % x, "mm", "stud slot FH%d x abs (copied from the frame v2.1)" % k)
        L.set_param("fh%d_y" % k, "%.6f mm" % y, "mm", "stud slot FH%d y abs (copied)" % k)
    root = L.root()
    for i in range(root.occurrences.count - 1, -1, -1):
        if root.occurrences.item(i).component.name == CYL:
            root.occurrences.item(i).deleteMe()
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = CYL
    tb = adsk.fusion.TemporaryBRepManager.get()
    bf = occ.component.features.baseFeatures.add()
    bf.startEdit()
    for k, (x, y) in enumerate(STUDXY, 1):
        for name, z0 in (("socket FH%d" % k, -0.65), ("socket above tube FH%d" % k, (Z_STUD_TOP + 0.01) / 10)):
            c = tb.createCylinderOrCone(adsk.core.Point3D.create(x / 10, -y / 10, z0), 0.6,
                                        adsk.core.Point3D.create(x / 10, -y / 10, 4.5), 0.6)
            nb = occ.component.bRepBodies.add(c, bf)
            nb.name = name
    bf.finishEdit()
    occ.isLightBulbOn = False
    patch = L.part_body("Oven sheet patch")
    L.log("56 refs updated %s; patch bbox %s %.3f cm3; cylinders %d" % (upd, L.bbox_mm(patch),
          patch.physicalProperties.volume, occ.bRepBodies.count))
    L.show_iso()
    print(upd, L.bbox_mm(patch), occ.bRepBodies.count)
