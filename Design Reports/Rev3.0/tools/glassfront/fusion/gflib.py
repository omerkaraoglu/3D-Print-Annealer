"""gflib - helpers shared by the numbered Fusion scripts of the Rev3.0 glass-front carrier frame ("Frame GF").

Copied and adapted from Design Reports/Rev3.0/tools/frame_v2/fusion/fv2lib.py (that file is NOT edited).
Imported by every NN_*.py script (sys.path + importlib.reload), so the executed code = script + this module.

Conventions (as frame v2)
  * model X = KiCad abs x, model Y = -(KiCad abs y), Z = 0 at the physical PCB back, -Z towards the oven front.
  * Fusion API lengths are cm; everything here takes mm and converts.
  * every plan dimension is driven by a user-parameter EXPRESSION typed in KiCad abs coordinates (x, y down).
  * differences to fv2lib:
      - the frame lives in its own component 'Frame GF' (one body 'Frame GF'); user parameters stay at document
        level; sketches, planes and features are created in the component.
      - sketch dimensions are measured from a FIXED reference point at abs (-100, -100) in every sketch (not from
        the sketch origin), so a dimension never changes sign when a point crosses x = 0 or y = 0 (the flange and
        the fastener lines lie at negative abs coordinates).
      - rotated geometry (radial stadium slots, 45 deg tube ribs) is fully dimensioned by expressions
        (point coordinates + tangency), no fixed sketch geometry.
  * TAPER_SHRINK is the extrude taper sign that makes a profile SHRINK along the extrude direction (fv2 found -1;
    02 checks it again on the first extrude).
"""
import json
import math
import os
import time

import adsk.core
import adsk.fusion

REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
GF_DIR = os.path.join(REPO, "Design Reports", "Rev3.0", "tools", "glassfront", "fusion")
MECH = os.path.join(REPO, "Mechanical", "Rev3.0_GlassFront")
MASTER = os.path.join(MECH, "Rev3.0_GlassFront_params.json")
SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
LOG = os.path.join(SCR, "fusion_log.txt")
PROJECT_ID = "a.YnVzaW5lc3M6ZWxla3Ryb21hZyMyMDI2MDMyNTEwNjk5OTY2MDE"     # hub1 > Oven
FOLDER = "Rev3.0 OVEN CONTROLLER"
DOC_NAME = "Rev3.0 GlassFront"
COMP_NAME = "Frame GF"
BODY_NAME = "Frame GF"
TAG_GROUP, TAG_NAME = "gf", "doc"
TAPER_SHRINK = -1
REF_X, REF_Y = -100.0, -100.0       # abs KiCad (x, y down) of the fixed dimension reference point of every sketch


def log(msg):
    os.makedirs(SCR, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + str(msg) + "\n")


def app():
    return adsk.core.Application.get()


def des():
    return adsk.fusion.Design.cast(app().activeProduct)


def check_doc():
    """raise unless the ACTIVE document carries gf/doc == 'Rev3.0 GlassFront'"""
    d = des()
    a = d.attributes.itemByName(TAG_GROUP, TAG_NAME) if d else None
    if a is None or a.value != DOC_NAME:
        raise RuntimeError("active document %r is not %r (gf/doc attribute) - refusing to run" % (
            app().activeDocument.name if app().activeDocument else None, DOC_NAME))
    return d


def gf_folder():
    proj = None
    for i in range(app().data.dataProjects.count):
        p = app().data.dataProjects.item(i)
        if p.id == PROJECT_ID:
            proj = p
    if proj is None:
        raise RuntimeError("project Oven not found")
    rf = proj.rootFolder
    for i in range(rf.dataFolders.count):
        if rf.dataFolders.item(i).name == FOLDER:
            return rf.dataFolders.item(i)
    raise RuntimeError("folder %s not found" % FOLDER)


def root():
    return des().rootComponent


def occ():
    r = root()
    for i in range(r.occurrences.count):
        o = r.occurrences.item(i)
        if o.component.name == COMP_NAME:
            return o
    raise RuntimeError("no component " + COMP_NAME)


def comp():
    return occ().component


def VI(expr):
    """ValueInput from an expression string or a float in mm"""
    if isinstance(expr, str):
        return adsk.core.ValueInput.createByString(expr)
    return adsk.core.ValueInput.createByReal(expr / 10.0)


def ev(expr, unit="mm"):
    um = des().unitsManager
    v = um.evaluateExpression(expr, unit)
    if unit == "mm":
        return v * 10.0
    if unit == "deg":
        return math.degrees(v)
    return v


def P(name):
    p = des().userParameters.itemByName(name)
    if p is None:
        raise RuntimeError("no parameter " + name)
    if p.unit == "mm":
        return p.value * 10.0
    if p.unit == "deg":
        return math.degrees(p.value)
    return p.value


def set_param(name, expr, unit, comment):
    ups = des().userParameters
    p = ups.itemByName(name)
    if p is None:
        p = ups.add(name, adsk.core.ValueInput.createByString(expr), unit, comment)
    else:
        p.expression = expr
        p.comment = comment
    return p


def plane(name, c=None):
    c = c or comp()
    cps = c.constructionPlanes
    for i in range(cps.count):
        if cps.item(i).name == name:
            return cps.item(i)
    raise RuntimeError("no plane " + name)


def offset_plane(name, expr, c=None):
    c = c or comp()
    cps = c.constructionPlanes
    for i in range(cps.count):
        if cps.item(i).name == name:
            return cps.item(i)
    pi = cps.createInput()
    pi.setByOffset(c.xYConstructionPlane, VI(expr))
    pl = cps.add(pi)
    pl.name = name
    return pl


def body():
    c = comp()
    for i in range(c.bRepBodies.count):
        b = c.bRepBodies.item(i)
        if b.name == BODY_NAME:
            return b
    return None


def feature(name):
    tl = des().timeline
    for i in range(tl.count):
        it = tl.item(i)
        if it.name == name:
            return it.entity
    return None


def P3(x_abs, y_abs):
    """abs KiCad (x, y down) mm -> sketch Point3D (cm) on an XY-parallel plane"""
    return adsk.core.Point3D.create(x_abs / 10.0, -y_abs / 10.0, 0)


def new_sketch(name, plane_name):
    c = comp()
    sk = c.sketches.add(plane(plane_name) if isinstance(plane_name, str) else plane_name)
    sk.name = name if name.endswith("sketch") else name + " sketch"
    sk.isComputeDeferred = True
    ref_point(sk)
    return sk


def ref_point(sk):
    for i in range(sk.sketchPoints.count):
        p = sk.sketchPoints.item(i)
        g = p.geometry
        if p.isFixed and abs(g.x - REF_X / 10.0) < 1e-9 and abs(g.y + REF_Y / 10.0) < 1e-9:
            return p
    p = sk.sketchPoints.add(P3(REF_X, REF_Y))
    p.isFixed = True
    return p


def _expr_x(expr):
    return "( %s ) + %g mm" % (expr, -REF_X)


def _expr_y(expr):
    return "( %s ) + %g mm" % (expr, -REF_Y)


def _dim_x(sk, pt, expr, ty):
    """horizontal distance reference point -> pt = x_abs + 100 (always > 0)"""
    d = sk.sketchDimensions.addDistanceDimension(
        ref_point(sk), pt, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
        adsk.core.Point3D.create(pt.geometry.x, ty, 0))
    if isinstance(expr, str):
        d.parameter.expression = _expr_x(expr)
    elif expr is not None:
        d.parameter.value = (expr - REF_X) / 10.0
    return d


def _dim_y(sk, pt, expr, tx):
    """vertical distance reference point -> pt = y_abs + 100 (always > 0)"""
    d = sk.sketchDimensions.addDistanceDimension(
        ref_point(sk), pt, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
        adsk.core.Point3D.create(tx, pt.geometry.y, 0))
    if isinstance(expr, str):
        d.parameter.expression = _expr_y(expr)
    elif expr is not None:
        d.parameter.value = (expr - REF_Y) / 10.0
    return d


def _num(e):
    return ev(e) if isinstance(e, str) else e


def rrect(sk, x0e, x1e, y0e, y1e, re=None, corners="all", dims=True):
    """Rounded rectangle, abs KiCad coords given as expressions (or numbers, mm).
    corners: 'all' or a subset of {'tl','tr','bl','br'} (t = small y = top of the board).
    Returns the 4 lines (left, right, top, bottom)."""
    x0, x1, y0, y1 = _num(x0e), _num(x1e), _num(y0e), _num(y1e)
    L = sk.sketchCurves.sketchLines
    tl, tr, br, bl = P3(x0, y0), P3(x1, y0), P3(x1, y1), P3(x0, y1)
    top = L.addByTwoPoints(tl, tr)
    right = L.addByTwoPoints(top.endSketchPoint, br)
    bot = L.addByTwoPoints(right.endSketchPoint, bl)
    left = L.addByTwoPoints(bot.endSketchPoint, top.startSketchPoint)
    gc = sk.geometricConstraints
    gc.addHorizontal(top)
    gc.addHorizontal(bot)
    gc.addVertical(left)
    gc.addVertical(right)
    if re is not None:
        r = _num(re)
        want = {"tl", "tr", "bl", "br"} if corners == "all" else set(corners)
        A = sk.sketchCurves.sketchArcs
        arcs = []
        pairs = {"tl": (left, top, (x0, y0)), "tr": (top, right, (x1, y0)), "br": (right, bot, (x1, y1)),
                 "bl": (bot, left, (x0, y1))}
        for k in ("tl", "tr", "br", "bl"):
            if k not in want:
                continue
            a, b, (cx, cy) = pairs[k]

            def near(line, cxx, cyy):
                if line in (top, bot):
                    return P3(cxx + (2 * r if cxx == x0 else -2 * r), cyy)
                return P3(cxx, cyy + (2 * r if cyy == y0 else -2 * r))
            arc = A.addFillet(a, near(a, cx, cy), b, near(b, cx, cy), r / 10.0)
            arcs.append(arc)
        if dims and isinstance(re, str):
            for arc in arcs:
                c = arc.centerSketchPoint.geometry
                m = arc.startSketchPoint.geometry
                tp = adsk.core.Point3D.create(c.x + 1.5 * (m.x - c.x) + 0.05, c.y + 1.5 * (m.y - c.y) + 0.05, 0)
                d = sk.sketchDimensions.addRadialDimension(arc, tp)
                d.parameter.expression = re
    if dims:
        ty = -(y0 - 3) / 10.0
        tx = (x0 - 3) / 10.0
        def sp(ln):
            return ln.startSketchPoint if ln.startSketchPoint.isValid else ln.endSketchPoint
        _dim_x(sk, sp(left), x0e, ty)
        _dim_x(sk, sp(right), x1e, ty)
        _dim_y(sk, sp(top), y0e, tx)
        _dim_y(sk, sp(bot), y1e, tx)
    return left, right, top, bot


def grect(sk, s_expr, plane_note=""):
    """glass-offset outline: the glass rectangle (glass_x0..glass_y1, R_glass) offset outward by s (expression)"""
    s = "( %s )" % s_expr
    return rrect(sk, "glass_x0 - %s" % s, "glass_x1 + %s" % s, "glass_y0 - %s" % s, "glass_y1 + %s" % s,
                 "R_glass + %s" % s)


_JIT = [0]


def _jit():
    """tiny unique offset (cm) for new free points (fv2lib: Fusion refuses a second dimension on a free point whose
    coordinate EXACTLY equals another free point's); the dimension expression then moves the point exactly."""
    _JIT[0] += 1
    return (_JIT[0] % 89 + 1) * 1e-5


def point(sk, xe, ye, dims=True):
    x, y = _num(xe), _num(ye)
    j = _jit()
    p = sk.sketchPoints.add(adsk.core.Point3D.create(x / 10.0 + j, -y / 10.0 - 1.3 * j, 0))
    if dims:
        _dim_x(sk, p, xe, -(y - 2) / 10.0)
        _dim_y(sk, p, ye, (x - 2) / 10.0)
    return p


def circle(sk, xe, ye, de, dims=True):
    x, y, d = _num(xe), _num(ye), _num(de)
    j = _jit() if dims else 0.0
    c = sk.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(x / 10.0 + j, -y / 10.0 - j, 0), d / 20.0)
    if dims:
        dd = sk.sketchDimensions.addDiameterDimension(c, P3(x + d, y - d))
        if isinstance(de, str):
            dd.parameter.expression = de
        _dim_x(sk, c.centerSketchPoint, xe, -(y - d - 2) / 10.0)
        _dim_y(sk, c.centerSketchPoint, ye, (x - d - 2) / 10.0)
    return c


def poly4(sk, corners):
    """closed quadrilateral through 4 corners given as (x expr, y expr); every corner dimensioned (8 dims = fully
    defined, no geometric constraints)."""
    pts = [point(sk, xe, ye) for xe, ye in corners]
    L = sk.sketchCurves.sketchLines
    lines = []
    for k in range(4):
        lines.append(L.addByTwoPoints(pts[k], pts[(k + 1) % 4]))
    return lines


def stadium(sk, ax, ay, bx, by, re):
    """closed stadium (two half circles of radius re round the centres A, B + two tangent lines), fully driven by
    expressions: the ARC CENTRE POINTS dimensioned directly (4 dims), 4 tangency constraints, radius dim on one arc
    and an equal constraint (diag_stadium_probe: separate centre points + two radius dims failed to solve)."""
    xa, ya, xb, yb, r = _num(ax), _num(ay), _num(bx), _num(by), _num(re)
    # sketch frame (Y = -y): u from A to B, n = u rotated +90 deg (CCW)
    Xa, Ya, Xb, Yb = xa, -ya, xb, -yb
    L_ = math.hypot(Xb - Xa, Yb - Ya)
    ux, uy = (Xb - Xa) / L_, (Yb - Ya) / L_
    nx, ny = -uy, ux
    A = sk.sketchCurves.sketchArcs
    j1, j2 = _jit(), _jit()
    arc_a = A.addByCenterStartSweep(adsk.core.Point3D.create(Xa / 10.0 + j1, Ya / 10.0 - j1, 0),
                                    adsk.core.Point3D.create((Xa + r * nx) / 10.0, (Ya + r * ny) / 10.0, 0),
                                    math.pi)                 # +n -> -u -> -n (CCW) round A
    arc_b = A.addByCenterStartSweep(adsk.core.Point3D.create(Xb / 10.0 + j2, Yb / 10.0 - j2, 0),
                                    adsk.core.Point3D.create((Xb - r * nx) / 10.0, (Yb - r * ny) / 10.0, 0),
                                    math.pi)                 # -n -> +u -> +n (CCW) round B
    Ls = sk.sketchCurves.sketchLines
    l1 = Ls.addByTwoPoints(arc_a.startSketchPoint, arc_b.endSketchPoint)    # +n side
    l2 = Ls.addByTwoPoints(arc_b.startSketchPoint, arc_a.endSketchPoint)    # -n side
    gc = sk.geometricConstraints
    for ln in (l1, l2):
        gc.addTangent(ln, arc_a)
        gc.addTangent(ln, arc_b)
    _dim_x(sk, arc_a.centerSketchPoint, ax, (Ya - 8) / 10.0)
    _dim_y(sk, arc_a.centerSketchPoint, ay, (Xa - 8) / 10.0)
    _dim_x(sk, arc_b.centerSketchPoint, bx, (Yb - 8) / 10.0)
    _dim_y(sk, arc_b.centerSketchPoint, by, (Xb - 8) / 10.0)
    d = sk.sketchDimensions.addRadialDimension(arc_a, adsk.core.Point3D.create(Xa / 10.0 + 0.05, Ya / 10.0, 0))
    d.parameter.expression = re if isinstance(re, str) else "%g mm" % re
    gc.addEqual(arc_a, arc_b)
    return arc_a, arc_b, l1, l2


def prof_info(p):
    bb = p.boundingBox
    a = p.areaProperties(adsk.fusion.CalculationAccuracy.MediumCalculationAccuracy).area * 100.0
    return a, (bb.minPoint.x * 10, bb.maxPoint.x * 10, -bb.maxPoint.y * 10, -bb.minPoint.y * 10)


def pick_profiles(sk, pred=None):
    out = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        p = sk.profiles.item(i)
        if pred is None:
            out.add(p)
            continue
        a, bb = prof_info(p)
        if pred(a, bb):
            out.add(p)
    return out


def solve(sk, n=None):
    """end deferred compute, check full constraint, return all profiles (optionally check their number)"""
    sk.isComputeDeferred = False
    pr = pick_profiles(sk)
    if n is not None and pr.count != n:
        raise RuntimeError("%s: %d profiles, expected %d" % (sk.name, pr.count, n))
    return pr


def under_constrained(sk):
    """number of sketch curves (excluding the reference point) that are not fully constrained"""
    n = 0
    for i in range(sk.sketchCurves.count):
        cu = sk.sketchCurves.item(i)
        if not cu.isFullyConstrained and not cu.isConstruction:
            n += 1
    return n


def extrude(profiles, op, dist_expr, direction=1, taper_expr=None, name=None, target_body=None):
    """op: 'new' | 'join' | 'cut'. direction +1 = +Z for the XY-parallel sketch planes used here."""
    ops = {"new": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
           "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
           "cut": adsk.fusion.FeatureOperations.CutFeatureOperation}
    ex = comp().features.extrudeFeatures
    ei = ex.createInput(profiles, ops[op])
    ext = adsk.fusion.DistanceExtentDefinition.create(VI(dist_expr))
    dirn = (adsk.fusion.ExtentDirections.PositiveExtentDirection if direction > 0
            else adsk.fusion.ExtentDirections.NegativeExtentDirection)
    if taper_expr is None:
        ei.setOneSideExtent(ext, dirn)
    else:
        ei.setOneSideExtent(ext, dirn, VI(taper_expr))
    if target_body is not None and op != "new":
        ei.participantBodies = [target_body]
    f = ex.add(ei)
    if name:
        f.name = name
    return f


def shrink(angle_param="draft"):
    """taper expression that shrinks the section along the extrude direction"""
    return ("-" if TAPER_SHRINK < 0 else "") + angle_param


def grow(angle_param="draft"):
    return ("" if TAPER_SHRINK < 0 else "-") + angle_param


def show_iso():
    vp = app().activeViewport
    if vp is None:
        return
    cam = vp.camera
    cam.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
    cam.isFitView = True
    vp.camera = cam
    vp.refresh()


def timeline_health():
    tl = des().timeline
    bad = []
    for i in range(tl.count):
        it = tl.item(i)
        if it.isRolledBack:
            continue                      # health state 4 = rolled back (marker before it), not a defect
        if it.isGroup:                    # stage 2: a group reports state 5; check its members instead
            g = adsk.fusion.TimelineGroup.cast(it)
            for k in range(g.count if g else 0):
                m = g.item(k)
                if not m.isRolledBack and m.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
                    bad.append((i, "%s / %s" % (it.name, m.name), str(m.healthState), m.errorOrWarningMessage))
            continue
        if it.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
            bad.append((i, it.name, str(it.healthState), it.errorOrWarningMessage))
    return tl.count, bad


def body_stats(b=None):
    b = b or body()
    if b is None:
        return "no body"
    pp = b.physicalProperties
    bb = b.boundingBox
    return "vol %.4f cm3, faces %d, bbox X %.3f..%.3f Y %.3f..%.3f Z %.3f..%.3f" % (
        pp.volume, b.faces.count, bb.minPoint.x * 10, bb.maxPoint.x * 10, bb.minPoint.y * 10,
        bb.maxPoint.y * 10, bb.minPoint.z * 10, bb.maxPoint.z * 10)


def body_dict(b=None):
    b = b or body()
    pp = b.physicalProperties
    bb = b.boundingBox
    return {"volume_cm3": round(pp.volume, 4), "mass_g_at_1.36": round(pp.volume * 1.36, 2),
            "faces": b.faces.count, "edges": b.edges.count, "lumps": b.lumps.count, "shells": b.shells.count,
            "is_solid": b.isSolid,
            "bbox_abs": {"x": [round(bb.minPoint.x * 10, 3), round(bb.maxPoint.x * 10, 3)],
                         "y_down": [round(-bb.maxPoint.y * 10, 3), round(-bb.minPoint.y * 10, 3)],
                         "z": [round(bb.minPoint.z * 10, 3), round(bb.maxPoint.z * 10, 3)]}}


def bodies_in_design():
    n = 0
    for i in range(root().bRepBodies.count):
        n += 1
    for i in range(root().allOccurrences.count):
        n += root().allOccurrences.item(i).component.bRepBodies.count
    return n


def save_version(desc):
    doc = app().activeDocument
    ok = doc.save(desc)
    df = doc.dataFile
    log("SAVE '%s': returned %s, dataFile version %s" % (desc, ok, df.versionNumber if df else None))
    return ok, (df.versionNumber if df else None)


def shot(path, eye_dir, target_mm=None, up=(0, 1, 0), w=1600, h=1200, fit=True, extent_mm=None):
    """orthographic camera looking along -eye_dir at target (model mm), fit or fixed extent; PNG"""
    vp = app().activeViewport
    if vp is None:
        log("shot: no viewport for %s" % path)
        return False
    cam = vp.camera
    if target_mm is None:
        bb = body().boundingBox
        target_mm = ((bb.minPoint.x + bb.maxPoint.x) * 5, (bb.minPoint.y + bb.maxPoint.y) * 5,
                     (bb.minPoint.z + bb.maxPoint.z) * 5)
    t = adsk.core.Point3D.create(target_mm[0] / 10, target_mm[1] / 10, target_mm[2] / 10)
    L_ = math.sqrt(sum(c * c for c in eye_dir))
    d = 60.0
    e = adsk.core.Point3D.create(t.x + eye_dir[0] / L_ * d, t.y + eye_dir[1] / L_ * d, t.z + eye_dir[2] / L_ * d)
    cam.isSmoothTransition = False
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.eye = e
    cam.target = t
    cam.upVector = adsk.core.Vector3D.create(*up)
    if fit and extent_mm is None:
        cam.isFitView = True
    elif extent_mm is not None:
        cam.setExtents(extent_mm / 10.0, extent_mm / 10.0 * h / w)
    vp.camera = cam
    vp.refresh()
    if fit and extent_mm is None:
        vp.fit()
    ok = vp.saveAsImageFile(path, w, h)
    log("shot %s -> %s" % (path, ok))
    return ok


def set_appearance(b, name, lib="Fusion Appearance Library"):
    d = des()
    ap = d.appearances.itemByName(name)
    if ap is None:
        src = app().materialLibraries.itemByName(lib).appearances.itemByName(name)
        ap = d.appearances.addByCopy(src, name)
    b.appearance = ap
    return ap


# ----------------------------------------------------------------------------------------- root-edge census
def face_owners():
    """tempId of every body face -> name of the extrude feature that created it"""
    owners = {}
    tl = des().timeline
    for i in range(tl.count):
        it = tl.item(i)
        if it.isRolledBack:
            continue
        f = adsk.fusion.ExtrudeFeature.cast(it.entity)
        if f is None or f.isSuppressed:
            continue
        fs = f.faces
        for k in range(fs.count):
            owners[fs.item(k).tempId] = f.name
    return owners


def _edge_info(b, e, dot_max, eps=0.005):
    """(concave?, midpoint mm (X, Y, Z), z-range mm) of a 2-face edge whose face normals |dot| <= dot_max"""
    if e.faces.count != 2:
        return False, None, None
    ev_ = e.evaluator
    ok, p0, p1 = ev_.getParameterExtents()
    ok, pm = ev_.getPointAtParameter((p0 + p1) / 2)
    f1, f2 = e.faces.item(0), e.faces.item(1)
    ok1, n1 = f1.evaluator.getNormalAtPoint(pm)
    ok2, n2 = f2.evaluator.getNormalAtPoint(pm)
    dot = n1.x * n2.x + n1.y * n2.y + n1.z * n2.z
    bb = e.boundingBox
    mid = (pm.x * 10, pm.y * 10, pm.z * 10)
    zr = (bb.minPoint.z * 10, bb.maxPoint.z * 10)
    if abs(dot) > dot_max:
        return False, mid, zr
    q = adsk.core.Point3D.create(pm.x + eps * (n1.x - n2.x), pm.y + eps * (n1.y - n2.y), pm.z + eps * (n1.z - n2.z))
    inside = b.pointContainment(q) == adsk.fusion.PointContainment.PointInsidePointContainment
    return inside, mid, zr


def _edge_convex(b, e, dot_max, eps=0.005):
    """True for a convex 2-face edge (material on the inside of both normals)"""
    if e.faces.count != 2:
        return False
    ev_ = e.evaluator
    ok, p0, p1 = ev_.getParameterExtents()
    ok, pm = ev_.getPointAtParameter((p0 + p1) / 2)
    f1, f2 = e.faces.item(0), e.faces.item(1)
    ok1, n1 = f1.evaluator.getNormalAtPoint(pm)
    ok2, n2 = f2.evaluator.getNormalAtPoint(pm)
    dot = n1.x * n2.x + n1.y * n2.y + n1.z * n2.z
    if abs(dot) > dot_max:
        return False
    q = adsk.core.Point3D.create(pm.x + eps * (n1.x + n2.x), pm.y + eps * (n1.y + n2.y), pm.z + eps * (n1.z + n2.z))
    return b.pointContainment(q) == adsk.fusion.PointContainment.PointOutsidePointContainment


def owner_group(o1, o2, mid, zr=None):
    s = {o1, o2}

    def has(prefix):
        return any(o and o.startswith(prefix) for o in s)
    if zr is not None and abs(zr[0]) < 1e-3 and abs(zr[1]) < 1e-3 and has("PCB support ribs"):
        # the Z 0 wall-top face is merged with the support-rib tops (owner = the rib feature, as in v2): its concave
        # edges are where the tail walls / bottom beam rise from the wall top
        return "tail walls to wall top"
    if has("Fastener slots"):
        return "fastener slots (excluded)"
    if has("PCB pilot"):
        return "pilots (excluded)"
    if has("Pips"):
        return "pip roots (sharp)"
    if has("Fastener tubes") or has("Tube ribs"):
        return "tubes + tube ribs"
    if has("PCB bosses"):
        cell = any(math.hypot(mid[0] - P(h + "_x"), mid[1] + P(h + "_y")) < 6 for h in ("h6", "h7"))
        return "PCB bosses in cells (H6 H7)" if cell else "PCB bosses on the walls"
    if has("Cell ribs") or has("Corner cells"):
        return "corner cells + cell ribs"
    if has("PCB support ribs"):
        return "PCB support ribs"
    if has("Corner pads"):
        return "pad roots (sharp, tape margin)"
    if has("Lip") and has("Seat ring"):
        return "lip root"
    if has("Seat ring") and (has("Flange plate") or has("Land plate")):
        return "seat ring root (sharp, tape margin)"       # flange front face merged with block B's front face
    if has("Land plate") and has("Flange plate"):
        return "step wall to flange back"
    if (has("Outer wall block") or has("Tail wall block")) and has("Land plate"):
        return "wall to land plate"
    if has("Glass recess"):
        return "land to recess wall"
    if has("Above-shelf space") or has("Window"):
        return "shelf back"
    if has("Clearance pocket"):
        return "shelf front (pocket)"
    if has("Divider rib"):                                   # GF-2.0 (stage 4, 68)
        return "divider rib (GF-2.0)"
    if has("Floor over the flange plate"):                   # GF-2.0 (stage 4, 68)
        return "floors over the flange (GF-2.0)"
    if has("Tail pocket"):
        return "tail pocket"
    if has("Tail wall block"):
        return "tail walls to wall top"
    return "other: %s / %s" % (o1, o2)


def root_edges(dot_max=0.9, owners=None):
    """all concave edges between two original plane / cone faces of the body, labelled by owner group:
    [(group, edge, mid (model mm), zrange, (owner1, owner2))]"""
    b = body()
    owners = owners or face_owners()
    orig = (adsk.core.SurfaceTypes.PlaneSurfaceType, adsk.core.SurfaceTypes.ConeSurfaceType)
    out = []
    for i in range(b.edges.count):
        e = b.edges.item(i)
        if e.faces.count != 2 or any(e.faces.item(k).geometry.surfaceType not in orig for k in range(2)):
            continue
        conc, mid, zr = _edge_info(b, e, dot_max)
        if not conc:
            continue
        o1, o2 = owners.get(e.faces.item(0).tempId), owners.get(e.faces.item(1).tempId)
        out.append((owner_group(o1, o2, mid, zr), e, mid, zr, (o1, o2)))
    return out


def runs_into_tail(e):
    """shelf-back / wall edge on the bottom pocket wall that ends at the tail-pocket side face (v2: an R0.5 run-out
    rolls across the shelf end there; left sharp as in v2, corners 3 and 4)"""
    k = math.tan(math.radians(P("draft")))
    xs = (P("tr_x0") - (P("Z_SHELF_BACK") - P("Z_LAND")) * k, P("tr_x1") + (P("Z_SHELF_BACK") - P("Z_LAND")) * k)
    bb = e.boundingBox
    at_bottom = abs(-bb.maxPoint.y * 10 - P("pocket_y1")) < 0.5
    return at_bottom and any(bb.minPoint.x * 10 - 0.3 <= xx <= bb.maxPoint.x * 10 + 0.3 for xx in xs)


EDGE_SETS = {
    "PCB bosses on the walls": lambda g, e, m, z: g == "PCB bosses on the walls",
    "corner cells + cell ribs + cell bosses": lambda g, e, m, z: g in ("PCB bosses in cells (H6 H7)",
                                                                        "corner cells + cell ribs"),
    "PCB support rib sides": lambda g, e, m, z: g == "PCB support ribs",
    "shelf back (not into the tail pocket)": lambda g, e, m, z: g == "shelf back" and not runs_into_tail(e),
    "shelf front (pocket)": lambda g, e, m, z: g == "shelf front (pocket)",
    "tail walls to wall top": lambda g, e, m, z: g == "tail walls to wall top",
    "land to recess wall": lambda g, e, m, z: g == "land to recess wall",
    "lip root": lambda g, e, m, z: g == "lip root",
}


def fillet_set(set_name, radius="fillet_root"):
    """FilletFeature on the current edges of EDGE_SETS[set_name] (root_edges re-collected)"""
    sel = EDGE_SETS[set_name]
    es = [e for g, e, m, z, o in root_edges(0.9) if sel(g, e, m, z)]
    if not es:
        log("fillet set %s: no edges" % set_name)
        return None, 0
    nm = ("Root fillets R0.5 - " if radius == "fillet_root" else "Root fillets %s - " % radius) + set_name
    return fillet_edges(es, radius, nm), len(es)


def rule_fillet(name, kind, one, two=None, radius="fillet_root"):
    """rule fillet (fillets only = concave edges): kind 'all' (all edges of the features in one) or 'between'"""
    ff = comp().features.filletFeatures
    ri = ff.createRuleFilletInput()
    if kind == "all":
        ok = ri.setByAllEdges([feature(n) for n in one])
    else:
        ok = ri.setByBetweenFacesOrFeatures([feature(n) for n in one], [feature(n) for n in two])
    if not ok:
        raise RuntimeError("rule fillet %s: set definition failed" % name)
    ri.radius = VI(radius)
    ri.topologyType = adsk.fusion.RuleFilletTopologyTypes.FilletsOnlyRuleFilletTopologyType
    ri.isRollingBallCorner = True
    f = ff.addRuleFillet(ri)
    f.name = name
    log("rule fillet '%s': %d faces; %s" % (name, f.faces.count, body_stats()))
    return f


# 26 PCB support ribs (v1 frame.py / fv2lib.RIBS): x0, x1, y0, y1, side; GF keeps position and width, the wall end is
# buried rib_bury into the (moved) pocket wall and the free end runs rib_overshoot past the cut that trims it
# (fv2lib.rib_rects_v21 with rib_pad_result.json kept_v1_length = []).
RIBS_V1 = [
    (27.27, 28.77, 18.65, 21.1, "T"), (48.54142857142857, 50.04142857142857, 18.65, 21.1, "T"),
    (65.56285714285714, 67.06285714285714, 18.65, 21.1, "T"), (91.0842857142857, 92.5842857142857, 18.65, 21.1, "T"),
    (110.10571428571427, 111.60571428571427, 18.65, 21.1, "T"),
    (133.62714285714284, 135.12714285714284, 18.65, 21.1, "T"),
    (154.89857142857142, 156.39857142857142, 18.65, 21.1, "T"), (176.17, 177.67, 18.65, 21.1, "T"),
    (27.27, 28.77, 116.9, 119.35, "B"), (48.54142857142857, 50.04142857142857, 116.9, 118.5, "B"),
    (69.81285714285714, 71.31285714285714, 116.9, 118.5, "B"), (91.0842857142857, 92.5842857142857, 116.9, 118.5, "B"),
    (112.35571428571428, 113.85571428571428, 116.9, 118.5, "B"),
    (133.62714285714284, 135.12714285714284, 116.9, 118.5, "B"),
    (154.89857142857142, 156.39857142857142, 116.9, 118.5, "B"), (176.17, 177.67, 116.9, 119.35, "B"),
    (19.67, 22.12, 26.25, 27.75, "L"), (19.67, 22.12, 47.25, 48.75, "L"), (19.67, 22.12, 68.25, 69.75, "L"),
    (19.67, 22.12, 89.25, 90.75, "L"), (19.67, 22.12, 110.25, 111.75, "L"),
    (182.82, 185.27, 26.25, 27.75, "R"), (182.82, 185.27, 47.25, 48.75, "R"), (182.82, 185.27, 68.25, 69.75, "R"),
    (182.82, 185.27, 89.25, 90.75, "R"), (182.82, 185.27, 110.25, 111.75, "R"),
]


def rib_exprs(k):
    """plan expressions (x0, x1, y0, y1) of support rib k (1..26): rib<k>_a is the v1 position of its first edge
    (x0 for T/B ribs, y0 for L/R ribs), width = rib; ends per fv2lib.rib_rects_v21 (GF pocket_clr)."""
    x0, x1, y0, y1, side = RIBS_V1[k - 1]
    a = "rib%d_a" % k
    if side == "T":
        return (a, a + " + rib", "panel_y0 - pocket_clr - rib_bury", "panel_y0 + seat_w + rib_overshoot")
    if side == "L":
        return ("panel_x0 - pocket_clr - rib_bury", "panel_x0 + seat_w + rib_overshoot", a, a + " + rib")
    if side == "R":
        return ("panel_x1 - seat_w - rib_overshoot", "panel_x1 + pocket_clr + rib_bury", a, a + " + rib")
    # bottom: ribs 9 and 16 end in the bottom pocket wall; ribs 10..15 run over the tail pocket to the shelf end
    if y1 > 119.0:
        return (a, a + " + rib", "panel_y1 - seat_w - rib_overshoot", "panel_y1 + pocket_clr + rib_bury")
    return (a, a + " + rib", "panel_y1 - seat_w - rib_overshoot", "panel_y1 + rib_overshoot")


def rib_index(mid):
    """support rib index (1..26) an edge midpoint (model mm) belongs to, else None"""
    x, y = mid[0], -mid[1]
    for k in range(1, 27):
        ex = [ev(e) for e in rib_exprs(k)]
        if ex[0] - 0.7 <= x <= ex[1] + 0.7 and ex[2] - 0.7 <= y <= ex[3] + 0.7:
            return k
    return None


def thin_strips(b=None, dmax=1.0, min_overlap=0.2):
    """planar faces with two parallel, non-touching straight edges closer than dmax (mm) and overlapping by more than
    min_overlap: ledges, slots, thin wall tops hidden in merged faces (fv2lib copy).
    Returns [(face index, distance mm, overlap mm, midpoint abs (x, y_down, Z))]."""
    b = b or body()
    out = []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        lines = []
        for k in range(f.edges.count):
            e = f.edges.item(k)
            if isinstance(e.geometry, adsk.core.Line3D):
                lines.append((e, e.startVertex.geometry, e.endVertex.geometry))
        for a in range(len(lines)):
            ea, p1, q1 = lines[a]
            ux, uy, uz = q1.x - p1.x, q1.y - p1.y, q1.z - p1.z
            la = math.sqrt(ux * ux + uy * uy + uz * uz)
            if la < 1e-6:
                continue
            ux, uy, uz = ux / la, uy / la, uz / la
            for c in range(a + 1, len(lines)):
                ec, p2, q2 = lines[c]
                if ea.startVertex in (ec.startVertex, ec.endVertex) or ea.endVertex in (ec.startVertex, ec.endVertex):
                    continue
                vx, vy, vz = q2.x - p2.x, q2.y - p2.y, q2.z - p2.z
                lc = math.sqrt(vx * vx + vy * vy + vz * vz)
                if lc < 1e-6 or abs(abs(ux * vx + uy * vy + uz * vz) / lc - 1) > 1e-3:
                    continue
                wx, wy, wz = p2.x - p1.x, p2.y - p1.y, p2.z - p1.z
                t = wx * ux + wy * uy + wz * uz
                dx, dy, dz = wx - t * ux, wy - t * uy, wz - t * uz
                dist = math.sqrt(dx * dx + dy * dy + dz * dz) * 10
                if dist >= dmax or dist < 1e-6:
                    continue
                t2 = (q2.x - p1.x) * ux + (q2.y - p1.y) * uy + (q2.z - p1.z) * uz
                ov = (min(la, max(t, t2)) - max(0.0, min(t, t2))) * 10
                if ov > min_overlap:
                    m = ((p1.x + q1.x + p2.x + q2.x) * 2.5, -(p1.y + q1.y + p2.y + q2.y) * 2.5,
                         (p1.z + q1.z + p2.z + q2.z) * 2.5)
                    out.append((i, round(dist, 4), round(ov, 3), tuple(round(v, 3) for v in m)))
    return out


def fillet_edges(edges, radius_expr, name, rolling=True):
    coll = adsk.core.ObjectCollection.create()
    for e in edges:
        coll.add(e)
    ff = comp().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(coll, VI(radius_expr), False)
    fi.isRollingBallCorner = rolling
    f = ff.add(fi)
    f.name = name
    log("fillet '%s': %d edges, %s; %s" % (name, len(edges), radius_expr, body_stats()))
    return f


def dump(obj, name):
    os.makedirs(SCR, exist_ok=True)
    p = os.path.join(SCR, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    return p


# ===================================================================================================================
# stage 2 (assembly) helpers - appended; nothing above was changed
# ===================================================================================================================
BOARD_COMP = "Rev3.0 PCB full (KiCad STEP)"
CHECK_COMP = "Check - socket cylinders (hidden)"


def occ_by_comp(name, required=True):
    r = root()
    for i in range(r.occurrences.count):
        o = r.occurrences.item(i)
        if o.component.name == name:
            return o
    if required:
        raise RuntimeError("no occurrence of component " + name)
    return None


def new_comp(name):
    """new component under the root (identity transform -> component coords = model coords); refuses duplicates"""
    if occ_by_comp(name, False) is not None:
        raise RuntimeError("component %s exists already" % name)
    o = root().occurrences.addNewComponent(adsk.core.Matrix3D.create())
    o.component.name = name
    return o


def cplane(c, name, expr):
    """hidden offset plane in component c at Z = expr (model Z, component XY plane = model XY plane)"""
    cps = c.constructionPlanes
    for i in range(cps.count):
        if cps.item(i).name == name:
            return cps.item(i)
    pi = cps.createInput()
    pi.setByOffset(c.xYConstructionPlane, VI(expr))
    pl = cps.add(pi)
    pl.name = name
    pl.isLightBulbOn = False
    return pl


def csketch(c, name, pl):
    sk = c.sketches.add(pl)
    sk.name = name if name.endswith("sketch") else name + " sketch"
    sk.isComputeDeferred = True
    ref_point(sk)
    return sk


def cextrude(c, profiles, op, dist_expr, direction=1, name=None, target=None, body_name=None, taper_expr=None):
    ops = {"new": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
           "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
           "cut": adsk.fusion.FeatureOperations.CutFeatureOperation}
    ex = c.features.extrudeFeatures
    ei = ex.createInput(profiles, ops[op])
    ext = adsk.fusion.DistanceExtentDefinition.create(VI(dist_expr))
    dirn = (adsk.fusion.ExtentDirections.PositiveExtentDirection if direction > 0
            else adsk.fusion.ExtentDirections.NegativeExtentDirection)
    if taper_expr is None:
        ei.setOneSideExtent(ext, dirn)
    else:
        ei.setOneSideExtent(ext, dirn, VI(taper_expr))
    if target is not None and op != "new":
        ei.participantBodies = [target]
    f = ex.add(ei)
    if name:
        f.name = name
    if body_name and op == "new":
        f.bodies.item(0).name = body_name
    return f


def biggest_profile(sk):
    best, ba = None, -1
    for i in range(sk.profiles.count):
        p = sk.profiles.item(i)
        a = p.areaProperties(adsk.fusion.CalculationAccuracy.MediumCalculationAccuracy).area
        if a > ba:
            best, ba = p, a
    return best


def profiles_with_loops(sk, nloops):
    out = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        p = sk.profiles.item(i)
        if p.profileLoops.count == nloops:
            out.add(p)
    return out


def hexagon(sk, cxe, cye, se):
    """regular hexagon, across flats se (expression), two flats parallel to x, centre (cxe, cye) abs; every vertex
    dimensioned by an expression (fully defined, follows the parameters)"""
    pts = []
    for k in range(6):
        a = 60 * k
        pts.append(point(sk, "%s + %s / sqrt(3) * cos(%d deg)" % (cxe, se, a),
                         "%s - %s / sqrt(3) * sin(%d deg)" % (cye, se, a)))
    L_ = sk.sketchCurves.sketchLines
    return [L_.addByTwoPoints(pts[k], pts[(k + 1) % 6]) for k in range(6)]


def body_in(c, name):
    for i in range(c.bRepBodies.count):
        if c.bRepBodies.item(i).name == name:
            return c.bRepBodies.item(i)
    return None


def appearance(name, lib="Fusion Appearance Library"):
    d = des()
    ap = d.appearances.itemByName(name)
    if ap is None:
        src = app().materialLibraries.itemByName(lib).appearances.itemByName(name)
        ap = d.appearances.addByCopy(src, name)
    return ap


def bbox_mm(b):
    bb = b.boundingBox
    return [round(bb.minPoint.x * 10, 3), round(bb.maxPoint.x * 10, 3), round(-bb.maxPoint.y * 10, 3),
            round(-bb.minPoint.y * 10, 3), round(bb.minPoint.z * 10, 3), round(bb.maxPoint.z * 10, 3)]


def overlap_volume_mm3(b1, b2):
    """volume of the intersection of two (proxy) bodies, temporary BReps (mm3)"""
    tb = adsk.fusion.TemporaryBRepManager.get()
    a = tb.copy(b1)
    c = tb.copy(b2)
    ok = tb.booleanOperation(a, c, adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return a.volume * 1000.0 if ok else None


def min_dist_mm(e1, e2):
    r = app().measureManager.measureMinimumDistance(e1, e2)
    return r.value * 10.0, r.positionOne, r.positionTwo


def pt_abs(p):
    return [round(p.x * 10, 3), round(-p.y * 10, 3), round(p.z * 10, 3)]


def bodies_under(o):
    """[(path, body proxy)] of every body under occurrence o (all levels), deterministic order"""
    out = []
    for k in range(o.bRepBodies.count):
        out.append((o.fullPathName, o.bRepBodies.item(k)))
    stack = [o.childOccurrences.item(i) for i in range(o.childOccurrences.count)]
    while stack:
        x = stack.pop(0)
        for k in range(x.bRepBodies.count):
            out.append((x.fullPathName, x.bRepBodies.item(k)))
        stack += [x.childOccurrences.item(i) for i in range(x.childOccurrences.count)]
    return out
