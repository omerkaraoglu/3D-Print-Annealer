"""03 - the front-of-panel structure (everything here is new GF geometry, master JSON plan rectangles):
  'Flange plate'                  flange outline (fl_*, R flange_R) on the Z_FLANGE_FRONT plane, +Z to Z_FLANGE_BACK,
                                  1 deg draft shrinking to the back (B side; parting line on its outline at the
                                  flange front). NEW BODY 'Frame GF' in component 'Frame GF'. Full plate (one
                                  profile): the recess / pocket cuts remove it inside.
  'Land plate + step wall (back)' glass outline + s_ring_b (= s_ring at the flange back) on the Z_FLANGE_FRONT plane,
                                  +Z to Z_STEPWALL_BACK, 1 deg shrinking: land plate + back part of the step wall
                                  (solid disc; the glass recess cut leaves the land plate behind Z_LAND).
  'Seat ring (step wall front)'   glass + s_ring (R8.9) on the Z_FLANGE_FRONT plane, -Z by t_gap to Z_SHEET_BACK,
                                  1 deg shrinking to the front (A side) = seat-ring outer face s 2.9 at its root.
  'Lip'                           glass + s_lip_out (R7.4) on the Z_SHEET_BACK plane (lip root), -Z by t_sheet to
                                  Z_GLASS_FRONT, 1 deg shrinking to the front (A side).
  'Corner pads F1-F4'             dia pad_d at F1..F4 on the Z_FLANGE_FRONT plane, -Z by t_gap to Z_SHEET_BACK,
                                  1 deg shrinking to the front (A side, hard stops).
The step wall is therefore one continuous solid from Z_SHEET_BACK to Z_STEPWALL_BACK at every glass_t.
All distances stay > 0 for every valid parameter set (no zero-length extrude at the level snap).
Also checks the sketch frame of a component plane and the taper sign (TAPER_SHRINK).
Expects: 02 done.
"""
import importlib
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)


def face_x_at(b, z_mm):
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
    L.check_doc()
    L.log("=== 03 start")
    uc = {}
    sk = L.new_sketch("Flange plate", "Z_FLANGE_FRONT plane")
    p = sk.sketchToModelSpace(adsk.core.Point3D.create(1, 1, 0))
    if abs(p.x - 1) > 1e-9 or abs(p.y - 1) > 1e-9 or abs(p.z * 10 - L.P("Z_FLANGE_FRONT")) > 1e-6:
        raise RuntimeError("sketch axes / plane not as expected: %r" % ((p.x, p.y, p.z),))
    L.rrect(sk, "fl_x0", "fl_x1", "fl_y0", "fl_y1", "flange_R")
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    f = L.extrude(pr, "new", "Z_FLANGE_BACK - Z_FLANGE_FRONT", +1, L.shrink(), "Flange plate")
    b = f.bodies.item(0)
    b.name = L.BODY_NAME
    xmax = face_x_at(b, L.P("Z_FLANGE_BACK"))
    L.log("03 flange back face xmax %.4f (fl_x1 %.4f), taper '%s'" % (xmax, L.P("fl_x1"), L.shrink()))
    if xmax is None or xmax > L.P("fl_x1") - 1e-4:
        raise RuntimeError("taper sign: flange back xmax %r not inside fl_x1 - fix gflib.TAPER_SHRINK" % xmax)

    sk = L.new_sketch("Land plate + step wall (back)", "Z_FLANGE_FRONT plane")
    L.grect(sk, "s_ring_b")
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_STEPWALL_BACK - Z_FLANGE_FRONT", +1, L.shrink(), "Land plate + step wall (back)", b)

    sk = L.new_sketch("Seat ring (step wall front)", "Z_FLANGE_FRONT plane")
    L.grect(sk, "s_ring")
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_FLANGE_FRONT - Z_SHEET_BACK", -1, L.shrink(), "Seat ring (step wall front)", b)

    sk = L.new_sketch("Lip", "Z_SHEET_BACK plane")
    L.grect(sk, "s_lip_out")
    pr = L.solve(sk, 1)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_SHEET_BACK - Z_GLASS_FRONT", -1, L.shrink(), "Lip", b)

    sk = L.new_sketch("Corner pads F1-F4", "Z_FLANGE_FRONT plane")
    for k in (1, 2, 3, 4):
        L.circle(sk, "f%d_x" % k, "f%d_y" % k, "pad_d")
    pr = L.solve(sk, 4)
    uc[sk.name] = L.under_constrained(sk)
    L.extrude(pr, "join", "Z_FLANGE_FRONT - Z_SHEET_BACK", -1, L.shrink(), "Corner pads F1-F4", b)

    n, bad = L.timeline_health()
    L.log("03 %s; under-constrained curves %s; timeline %d unhealthy %s" % (L.body_stats(), uc, n, bad))
    L.show_iso()
    print(L.body_stats(), uc, n, bad)
