"""diag - which constraint set makes a fully defined, expression-driven stadium? (13's first run failed at the second
radial dimension: VCS_SKETCH_SOLVING_FAILED.) Builds one F1 stadium per variant in a throw-away sketch, reports
the fully-constrained state, then deletes the sketch."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

H = "( slot_l - slot_w ) / 2"


def build(sk, variant):
    k = 1
    ax, ay = "f%d_x - %s * f%d_ux" % (k, H, k), "f%d_y - %s * f%d_uy" % (k, H, k)
    bx, by = "f%d_x + %s * f%d_ux" % (k, H, k), "f%d_y + %s * f%d_uy" % (k, H, k)
    xa, ya, xb, yb, r = L.ev(ax), L.ev(ay), L.ev(bx), L.ev(by), L.ev("slot_w / 2")
    ca = L.point(sk, ax, ay)
    cb = L.point(sk, bx, by)
    Xa, Ya, Xb, Yb = xa, -ya, xb, -yb
    d = math.hypot(Xb - Xa, Yb - Ya)
    ux, uy = (Xb - Xa) / d, (Yb - Ya) / d
    nx, ny = -uy, ux
    A = sk.sketchCurves.sketchArcs
    p1 = adsk.core.Point3D.create((Xa + r * nx) / 10.0, (Ya + r * ny) / 10.0, 0)
    p3 = adsk.core.Point3D.create((Xb - r * nx) / 10.0, (Yb - r * ny) / 10.0, 0)
    arc_a = A.addByCenterStartSweep(ca, p1, math.pi)
    arc_b = A.addByCenterStartSweep(cb, p3, math.pi)
    Ls = sk.sketchCurves.sketchLines
    l1 = Ls.addByTwoPoints(arc_a.startSketchPoint, arc_b.endSketchPoint)
    l2 = Ls.addByTwoPoints(arc_b.startSketchPoint, arc_a.endSketchPoint)
    gc = sk.geometricConstraints
    if variant == "tangent4+radius+equal":
        for ln in (l1, l2):
            gc.addTangent(ln, arc_a)
            gc.addTangent(ln, arc_b)
        dd = sk.sketchDimensions.addRadialDimension(arc_a, adsk.core.Point3D.create(Xa / 10 + 0.05, Ya / 10, 0))
        dd.parameter.expression = "slot_w / 2"
        gc.addEqual(arc_a, arc_b)
    elif variant == "tangent4+radius":
        for ln in (l1, l2):
            gc.addTangent(ln, arc_a)
            gc.addTangent(ln, arc_b)
        dd = sk.sketchDimensions.addRadialDimension(arc_a, adsk.core.Point3D.create(Xa / 10 + 0.05, Ya / 10, 0))
        dd.parameter.expression = "slot_w / 2"
    elif variant == "tangent3+radius2":
        gc.addTangent(l1, arc_a)
        gc.addTangent(l1, arc_b)
        gc.addTangent(l2, arc_a)
        for arc, X, Y in ((arc_a, Xa, Ya), (arc_b, Xb, Yb)):
            dd = sk.sketchDimensions.addRadialDimension(arc, adsk.core.Point3D.create(X / 10 + 0.05, Y / 10, 0))
            dd.parameter.expression = "slot_w / 2"
    curves = [arc_a, arc_b, l1, l2]
    return [c.isFullyConstrained for c in curves]


def build2(sk, variant):
    """arc centres created as Point3D and dimensioned DIRECTLY (arc.centerSketchPoint), as gflib.circle does"""
    k = 1
    ax, ay = "f%d_x - %s * f%d_ux" % (k, H, k), "f%d_y - %s * f%d_uy" % (k, H, k)
    bx, by = "f%d_x + %s * f%d_ux" % (k, H, k), "f%d_y + %s * f%d_uy" % (k, H, k)
    xa, ya, xb, yb, r = L.ev(ax), L.ev(ay), L.ev(bx), L.ev(by), L.ev("slot_w / 2")
    Xa, Ya, Xb, Yb = xa, -ya, xb, -yb
    d = math.hypot(Xb - Xa, Yb - Ya)
    ux, uy = (Xb - Xa) / d, (Yb - Ya) / d
    nx, ny = -uy, ux
    A = sk.sketchCurves.sketchArcs
    j1, j2 = L._jit(), L._jit()
    arc_a = A.addByCenterStartSweep(adsk.core.Point3D.create(Xa / 10 + j1, Ya / 10 - j1, 0),
                                    adsk.core.Point3D.create((Xa + r * nx) / 10.0, (Ya + r * ny) / 10.0, 0), math.pi)
    arc_b = A.addByCenterStartSweep(adsk.core.Point3D.create(Xb / 10 + j2, Yb / 10 - j2, 0),
                                    adsk.core.Point3D.create((Xb - r * nx) / 10.0, (Yb - r * ny) / 10.0, 0), math.pi)
    Ls = sk.sketchCurves.sketchLines
    l1 = Ls.addByTwoPoints(arc_a.startSketchPoint, arc_b.endSketchPoint)
    l2 = Ls.addByTwoPoints(arc_b.startSketchPoint, arc_a.endSketchPoint)
    gc = sk.geometricConstraints
    for ln in (l1, l2):
        gc.addTangent(ln, arc_a)
        gc.addTangent(ln, arc_b)
    L._dim_x(sk, arc_a.centerSketchPoint, ax, (Ya - 8) / 10)
    L._dim_y(sk, arc_a.centerSketchPoint, ay, (Xa - 8) / 10)
    L._dim_x(sk, arc_b.centerSketchPoint, bx, (Yb - 8) / 10)
    L._dim_y(sk, arc_b.centerSketchPoint, by, (Xb - 8) / 10)
    dd = sk.sketchDimensions.addRadialDimension(arc_a, adsk.core.Point3D.create(Xa / 10 + 0.05, Ya / 10, 0))
    dd.parameter.expression = "slot_w / 2"
    if variant == "direct+radius2":
        dd = sk.sketchDimensions.addRadialDimension(arc_b, adsk.core.Point3D.create(Xb / 10 + 0.05, Yb / 10, 0))
        dd.parameter.expression = "slot_w / 2"
    elif variant == "direct+equal":
        gc.addEqual(arc_a, arc_b)
    same = (arc_a.centerSketchPoint.geometry.distanceTo(adsk.core.Point3D.create(Xa / 10, Ya / 10, 0)) * 10)
    return [c.isFullyConstrained for c in (arc_a, arc_b, l1, l2)] + [round(same, 6)]


def run(_context: str):
    L.check_doc()
    out = []
    for v in ("tangent4+radius", "tangent4+radius+equal", "tangent3+radius2"):
        sk = L.new_sketch("diag stadium " + v, "Z_FLANGE_FRONT plane")
        sk.isComputeDeferred = False
        fc = build(sk, v)
        out.append((v, fc, sk.profiles.count))
        sk.deleteMe()
    print(out)
