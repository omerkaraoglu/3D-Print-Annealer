"""02 - outer body (v1 OUTER, R frame_r, Z_FRONT -> Z_PCB, 1 deg draft shrinking toward +Z) and the
continuous perimeter flange (fl_* outline R flange_r, Z_FRONT -> Z_FRONT + flange_t, outer edge 1 deg draft).
The flange is extruded as a full plate (one profile) so it merges with the body with no wedge at the
wall/flange junction; the later pocket/trough cuts remove it inside the body.

Expects: 01 done (params + planes), active document tagged fv2/doc.
Leaves: body 'Frame v2'; features 'Body (outer wall block)', 'Flange plate'. Checks the taper sign
(TAPER_SHRINK in fv2lib) on the body's top face. Closes the coordinator's unsaved viewing document
'Rev3.0 Frame v1 (reference, rejected ears)' WITHOUT saving (never activates anything).
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

VIEW_DOC = "Rev3.0 Frame v1 (reference, rejected ears)"


def top_face_xmax(b, z_mm):
    best = None
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        bb = f.boundingBox
        if abs(bb.minPoint.z * 10 - z_mm) < 1e-4 and abs(bb.maxPoint.z * 10 - z_mm) < 1e-4:
            x = bb.maxPoint.x * 10
            best = x if best is None else max(best, x)
    return best


def run(_context: str):
    app = adsk.core.Application.get()
    L.check_doc()
    L.log("=== 02 start")
    # sketch frame check
    sk = L.new_sketch("Body outline", "Z_FRONT plane")
    p = sk.sketchToModelSpace(adsk.core.Point3D.create(1, 1, 0))
    if abs(p.x - 1) > 1e-9 or abs(p.y - 1) > 1e-9:
        raise RuntimeError("sketch axes not aligned with model X/Y: %r" % ((p.x, p.y, p.z),))
    L.rrect(sk, "outer_x0", "outer_x1", "outer_y0", "outer_y1", "frame_r")
    sk.isComputeDeferred = False
    prof = L.pick_profiles(sk, lambda a, bb: True)
    if prof.count != 1:
        raise RuntimeError("body outline profiles: %d" % prof.count)
    f = L.extrude(prof, "new", "Z_PCB - Z_FRONT", +1, L.shrink(), "Body (outer wall block)")
    b = f.bodies.item(0)
    b.name = L.BODY_NAME
    xmax = top_face_xmax(b, 0.0)
    L.log("02 body top face xmax %.4f (outer_x1 %.4f) with taper '%s'" % (xmax, L.P("outer_x1"), L.shrink()))
    if xmax > L.P("outer_x1"):
        # taper sign is the other way round: flip this feature; fv2lib.TAPER_SHRINK must be edited to +1
        f.taperAngleOne.expression = "draft"
        xmax = top_face_xmax(b, 0.0)
        L.log("02 TAPER SIGN FLIPPED -> top face xmax %.4f; set fv2lib.TAPER_SHRINK = +1" % xmax)
        raise RuntimeError("taper sign convention is +; fix fv2lib.TAPER_SHRINK and rerun")
    # flange plate
    sk2 = L.new_sketch("Flange outline", "Z_FRONT plane")
    L.rrect(sk2, "fl_x0", "fl_x1", "fl_y0", "fl_y1", "flange_r")
    sk2.isComputeDeferred = False
    prof2 = L.pick_profiles(sk2, lambda a, bb: True)
    if prof2.count != 1:
        raise RuntimeError("flange outline profiles: %d" % prof2.count)
    L.extrude(prof2, "join", "flange_t", +1, L.shrink(), "Flange plate", b)
    L.log("02 " + L.body_stats())
    L.show_iso()
    # close the coordinator's viewing document without saving (no activation)
    for i in range(app.documents.count - 1, -1, -1):
        d = app.documents.item(i)
        if d.name == VIEW_DOC:
            d.close(False)
            L.log("02 closed viewing doc '%s' without saving" % VIEW_DOC)
    names = [app.documents.item(i).name for i in range(app.documents.count)]
    L.log("02 documents now: %s; active '%s'" % (names, app.activeDocument.name))
    print(L.body_stats(), names)
