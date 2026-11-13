"""Helpers shared by the numbered Fusion scripts of the Rev3.0 carrier frame v2.

Imported by every NN_*.py script (sys.path + importlib.reload), so the executed code = script + this module.
Conventions
  * model X = KiCad abs x, model Y = -(KiCad abs y), Z = 0 at the physical PCB back, +Z = component side.
  * Fusion API lengths are cm; everything here takes mm and converts.
  * plan dimensions are driven by user-parameter EXPRESSIONS (strings) in KiCad abs coordinates (y down);
    the sketch dimension from the sketch origin to a line at Y = -y has the value y.
  * TAPER_SHRINK is the extrude taper sign that makes a profile SHRINK along the extrude direction
    (found by 02_body_flange.py: Fusion's positive taper angle grows the profile? -> checked and logged).
"""
import math
import os
import time

import adsk.core
import adsk.fusion

LOG = (r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\62ff0a1a-4475-4c41-9c45-d7dae40b64a5"
       r"\scratchpad\cad\fusion_log.txt")
REPO = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer"
MECH = os.path.join(REPO, "Mechanical", "Rev3.0_Frame")
DOC_NAME = "Rev3.0 Frame v2"
BODY_NAME = "Frame v2"
TAPER_SHRINK = -1   # confirmed by 02_body_flange.py (see log): '-draft' shrinks the section along the extrude

# 26 PCB support ribs from v1 (frame.py support_ribs(), v1_geometry.json ribs_x0_x1_y0_y1_side_abs), abs KiCad.
# Kept EXACTLY; v2 only lengthens the outer end 0.5 mm into the wall (rib_bury) so the drafted rib end is buried.
RIBS = [
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


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + str(msg) + "\n")


def app():
    return adsk.core.Application.get()


def des():
    return adsk.fusion.Design.cast(app().activeProduct)


def mark_doc(tag):
    """tag the active design so later scripts can verify they run in the right document"""
    des().attributes.add("fv2", "doc", tag)


def check_doc(tag=None):
    """raise unless the ACTIVE document is one of ours (attribute fv2/doc == tag)"""
    tag = tag or DOC_NAME
    d = des()
    a = d.attributes.itemByName("fv2", "doc") if d else None
    if a is None or a.value != tag:
        raise RuntimeError("active document %r is not %r - refusing to run" % (app().activeDocument.name, tag))
    return d


def root():
    return des().rootComponent


def VI(expr):
    """ValueInput from an expression string (mm / deg / unitless as given) or a float in mm."""
    if isinstance(expr, str):
        return adsk.core.ValueInput.createByString(expr)
    return adsk.core.ValueInput.createByReal(expr / 10.0)


def ev(expr, unit="mm"):
    """evaluate an expression -> mm (lengths) or deg (angles)"""
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
    u = p.unit
    if u == "mm":
        return p.value * 10.0
    if u == "deg":
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


def plane(name):
    cps = root().constructionPlanes
    for i in range(cps.count):
        if cps.item(i).name == name:
            return cps.item(i)
    raise RuntimeError("no plane " + name)


def offset_plane(name, expr):
    try:
        return plane(name)
    except RuntimeError:
        pass
    cps = root().constructionPlanes
    pi = cps.createInput()
    pi.setByOffset(root().xYConstructionPlane, VI(expr))
    pl = cps.add(pi)
    pl.name = name
    return pl


def body():
    r = root()
    for i in range(r.bRepBodies.count):
        b = r.bRepBodies.item(i)
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


def new_sketch(name, plane_name):
    """sketch on a named plane; the sketch is named '<name> sketch' (features carry the plain name)"""
    sk = root().sketches.add(plane(plane_name) if isinstance(plane_name, str) else plane_name)
    sk.name = name if name.endswith("sketch") else name + " sketch"
    sk.isComputeDeferred = True
    return sk


def P3(x_abs, y_abs):
    """abs KiCad (x, y down) in mm -> sketch Point3D (cm) for a sketch on an XY-parallel plane"""
    return adsk.core.Point3D.create(x_abs / 10.0, -y_abs / 10.0, 0)


def _dim_x(sk, pt, expr, ty):
    d = sk.sketchDimensions.addDistanceDimension(
        sk.originPoint, pt, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
        adsk.core.Point3D.create(pt.geometry.x, ty, 0))
    if expr is not None:
        # a distance dimension is never negative: a point left of the origin gets -( expr ) (fixed 2026-11-13,
        # the oven-sheet patch outline starts at x -17.73 and was flipped to +17.73 before this fix)
        d.parameter.expression = expr if ev(expr) >= 0 else "-( %s )" % expr
    return d


def _dim_y(sk, pt, expr, tx):
    d = sk.sketchDimensions.addDistanceDimension(
        sk.originPoint, pt, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation,
        adsk.core.Point3D.create(tx, pt.geometry.y, 0))
    if expr is not None:
        d.parameter.expression = expr if ev(expr) >= 0 else "-( %s )" % expr   # abs y above the origin
    return d


def rrect(sk, x0e, x1e, y0e, y1e, re=None, corners="all", dims=True):
    """Rounded rectangle in abs KiCad coords given as expressions (or numbers, mm).
    corners: 'all' or a subset of {'tl','tr','bl','br'} (t = small y = top of the board).
    Returns the 4 lines (left, right, top, bottom)."""
    x0 = ev(x0e) if isinstance(x0e, str) else x0e
    x1 = ev(x1e) if isinstance(x1e, str) else x1e
    y0 = ev(y0e) if isinstance(y0e, str) else y0e
    y1 = ev(y1e) if isinstance(y1e, str) else y1e
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
        r = ev(re) if isinstance(re, str) else re
        want = {"tl", "tr", "bl", "br"} if corners == "all" else set(corners)
        A = sk.sketchCurves.sketchArcs
        arcs = []
        pairs = {"tl": (left, top, (x0, y0)), "tr": (top, right, (x1, y0)), "br": (right, bot, (x1, y1)),
                 "bl": (bot, left, (x0, y1))}
        for k in ("tl", "tr", "br", "bl"):
            if k not in want:
                continue
            a, b, (cx, cy) = pairs[k]
            pa = P3(cx + (r if a in (top, bot) else 0) * (1 if k in ("tl", "bl") else -1),
                    cy + (r if a in (left, right) else 0) * (1 if k in ("tl", "tr") else -1))
            # points slightly away from the corner on each line
            def near(line, cxx, cyy):
                if line in (top, bot):
                    return P3(cxx + (2 * r if cxx == x0 else -2 * r), cyy)
                return P3(cxx, cyy + (2 * r if cyy == y0 else -2 * r))
            arc = A.addFillet(a, near(a, cx, cy), b, near(b, cx, cy), r / 10.0)
            arcs.append(arc)
        if dims and arcs and isinstance(re, str):
            for arc in arcs:
                if arc.geometry is None:
                    continue
                c = arc.centerSketchPoint.geometry
                m = arc.startSketchPoint.geometry
                tp = adsk.core.Point3D.create(c.x + 1.5 * (m.x - c.x) + 0.05, c.y + 1.5 * (m.y - c.y) + 0.05, 0)
                d = sk.sketchDimensions.addRadialDimension(arc, tp)
                d.parameter.expression = re
    if dims:
        ty = -(y0 - 3) / 10.0
        tx = (x0 - 3) / 10.0
        _dim_x(sk, left.startSketchPoint if left.startSketchPoint.isValid else left.endSketchPoint,
               x0e if isinstance(x0e, str) else None, ty)
        _dim_x(sk, right.startSketchPoint if right.startSketchPoint.isValid else right.endSketchPoint,
               x1e if isinstance(x1e, str) else None, ty)
        _dim_y(sk, top.startSketchPoint if top.startSketchPoint.isValid else top.endSketchPoint,
               y0e if isinstance(y0e, str) else None, tx)
        _dim_y(sk, bot.startSketchPoint if bot.startSketchPoint.isValid else bot.endSketchPoint,
               y1e if isinstance(y1e, str) else None, tx)
    return left, right, top, bot


_JIT = [0]


def _jit():
    """tiny unique offset (cm) for new free points: Fusion refuses a second origin dimension on a free point whose
    coordinate EXACTLY equals another free point's (VCS_SKETCH_OVER_CONSTRAINTS); the dimension expression then
    moves the point to its exact value."""
    _JIT[0] += 1
    return (_JIT[0] % 89 + 1) * 1e-5


def circle(sk, xe, ye, de, dims=True):
    x = ev(xe) if isinstance(xe, str) else xe
    y = ev(ye) if isinstance(ye, str) else ye
    d = ev(de) if isinstance(de, str) else de
    j = _jit() if dims else 0.0
    c = sk.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(x / 10.0 + j, -y / 10.0 - j, 0), d / 20.0)
    if dims:
        dd = sk.sketchDimensions.addDiameterDimension(c, P3(x + d, y - d))
        if isinstance(de, str):
            dd.parameter.expression = de
        dx = _dim_x(sk, c.centerSketchPoint, xe if isinstance(xe, str) else None, -(y - d - 2) / 10.0)
        dy = _dim_y(sk, c.centerSketchPoint, ye if isinstance(ye, str) else None, (x - d - 2) / 10.0)
        if not isinstance(xe, str):
            dx.parameter.value = x / 10.0
        if not isinstance(ye, str):
            dy.parameter.value = y / 10.0
    return c


def fix_all(sk):
    for i in range(sk.sketchCurves.count):
        sk.sketchCurves.item(i).isFixed = True


def prof_info(p):
    bb = p.boundingBox
    a = p.areaProperties(adsk.fusion.CalculationAccuracy.MediumCalculationAccuracy).area * 100.0
    return a, (bb.minPoint.x * 10, bb.maxPoint.x * 10, -bb.maxPoint.y * 10, -bb.minPoint.y * 10)


def pick_profiles(sk, pred):
    """profiles whose (area mm2, abs bbox x0 x1 y0 y1) satisfy pred"""
    out = adsk.core.ObjectCollection.create()
    for i in range(sk.profiles.count):
        p = sk.profiles.item(i)
        a, bb = prof_info(p)
        if pred(a, bb):
            out.add(p)
    return out


def bbox_close(bb, ref, tol=0.05):
    return all(abs(a - b) <= tol for a, b in zip(bb, ref))


def extrude(profiles, op, dist_expr, direction=1, taper_expr=None, name=None, target_body=None):
    """op: 'new' | 'join' | 'cut'. direction +1 = along the sketch normal (+Z for XY planes)."""
    ops = {"new": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
           "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
           "cut": adsk.fusion.FeatureOperations.CutFeatureOperation}
    ex = root().features.extrudeFeatures
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
        log("show_iso: no active viewport (window busy?) - camera not set")
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
        if it.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
            bad.append((i, it.name, it.errorOrWarningMessage))
    return tl.count, bad


def body_stats(b=None):
    b = b or body()
    if b is None:
        return "no body"
    pp = b.physicalProperties
    bb = b.boundingBox
    return "vol %.3f cm3, faces %d, bbox X %.3f..%.3f Y %.3f..%.3f Z %.3f..%.3f" % (
        pp.volume, b.faces.count, bb.minPoint.x * 10, bb.maxPoint.x * 10, bb.minPoint.y * 10,
        bb.maxPoint.y * 10, bb.minPoint.z * 10, bb.maxPoint.z * 10)


# stud-hole pattern (hole_pattern_calc.py PATTERN): name -> (side, x expression, y expression), abs KiCad
STUDS = [   # v2.1 final (socket rule 6.5 / 11.0, symmetric offsets, socket >= 1.5 from the PCB bosses)
    ("FH1", "T", "43.5 mm", "stud_yt"), ("FH2", "T", "103.5 mm", "stud_yt"), ("FH3", "T", "162 mm", "stud_yt"),
    ("FH4", "R", "stud_xr", "40.5 mm"), ("FH5", "R", "stud_xr", "98.5 mm"),
    ("FH6", "B", "171 mm", "stud_yb"), ("FH7", "B", "102.5 mm", "stud_yb"), ("FH8", "B", "34 mm", "stud_yb"),
    ("FH9", "L", "stud_xl", "98.5 mm"), ("FH10", "L", "stud_xl", "40.5 mm"),
]


def save_version(desc):
    """save a new version of the ACTIVE (checked) document with a one-line description"""
    doc = app().activeDocument
    ok = doc.save(desc)
    df = doc.dataFile
    log("SAVE '%s': returned %s, dataFile version %s" % (desc, ok, df.versionNumber if df else None))
    return ok, (df.versionNumber if df else None)


def shot(path, eye_dir, target_mm=None, up=(0, 1, 0), w=1600, h=1200, fit=True, extent_mm=None):
    """camera looking along -eye_dir at target (mm, model coords), fit or fixed extent, save PNG"""
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


# ------------------------------------------------------------------------------------------- fillet edge census
def _edge_info(b, e, eps=0.005):
    """(is_concave_60_120, midpoint mm (X, Y, Z), z-range mm) for a 2-face edge; eps in cm"""
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
    if abs(dot) > 0.5:
        return False, mid, zr
    q = adsk.core.Point3D.create(pm.x + eps * (n1.x - n2.x), pm.y + eps * (n1.y - n2.y), pm.z + eps * (n1.z - n2.z))
    inside = b.pointContainment(q) == adsk.fusion.PointContainment.PointInsidePointContainment
    return inside, mid, zr


def root_edges():
    """all concave 60..120 deg edges of the body that are mould-root corners, labelled by group.
    Excluded: pilot / relief / stud holes, pegs (must enter the sheet holes), anything below Z_FRONT."""
    b = body()
    zf, zs, zsb, zp = P("Z_FRONT"), P("Z_SEAT"), P("Z_SHELF_BACK"), P("Z_PCB")
    zfb, zcf, zcr = P("Z_FLANGE_BACK"), P("Z_CELL_FLOOR"), P("Z_CELL_RIB_TOP")
    studs = [(P(n.lower() + "_x"), -P(n.lower() + "_y")) for n, _, _, _ in STUDS]
    holes = [(P("h%d_x" % i), -P("h%d_y" % i)) for i in range(1, 10)]
    cells = [(P("pocket_x0") - 0.6, P("tr_x0") - P("wall") + 0.1), (P("tr_x1") + P("wall") - 0.1, P("pocket_x1") + 0.6)]
    pegs = [(P("peg1_x"), -P("peg1_y")), (P("peg2_x"), -P("peg2_y"))]
    orig = (adsk.core.SurfaceTypes.PlaneSurfaceType, adsk.core.SurfaceTypes.ConeSurfaceType)
    cy0, cy1 = -P("tr_y1") - 0.6, -(P("pocket_y1") + P("wall")) + 0.6
    out = []
    for i in range(b.edges.count):
        e = b.edges.item(i)
        if e.faces.count != 2 or any(e.faces.item(k).geometry.surfaceType not in orig for k in range(2)):
            continue                                                     # only original plane/cone geometry
        conc, mid, zr = _edge_info(b, e)
        if not conc:
            continue
        x, y, z = mid
        if zr[0] < zf - 1e-4:
            continue                                                     # pegs
        if abs(zr[1] - zf) < 1e-3 and any(math.hypot(x - px, y - py) < P("peg_d") / 2 + 0.5 for px, py in pegs):
            continue                                                     # peg roots (pegs enter the sheet holes)
        if any(math.hypot(x - hx, y - hy) < P("cbore_d") / 2 + 0.2 for hx, hy in holes):
            continue                                                     # pilots / reliefs
        if any(math.hypot(x - sx, y - sy) < P("stud_hole") / 2 + 0.3 for sx, sy in studs):
            continue                                                     # stud holes (none expected)
        if any(math.hypot(x - sx, y - sy) < 9.5 for sx, sy in studs):
            g = "stud tubes + ribs"
        elif any(math.hypot(x - hx, y - hy) < 5.0 for hx, hy in holes):
            g = "PCB bosses"
        elif any(a <= x <= c for a, c in cells) and cy0 <= y <= cy1 and zcf - 1e-3 <= zr[0] and zr[1] <= zcr + 1e-3:
            g = "corner cells + cell ribs"
        elif abs(zr[0] - zfb) < 1e-3 and abs(zr[1] - zfb) < 1e-3:
            g = "wall to flange"
        elif zr[0] >= zsb - 1e-3 and zr[1] <= zp + 1e-3:
            g = "PCB support ribs + shelf back"
        elif abs(zr[0] - zs) < 1e-3 and abs(zr[1] - zs) < 1e-3:
            g = "shelf front (pocket)"
        elif abs(zr[0] - zs) < 1e-3 and abs(zr[1] - zsb) < 1e-3 and min(abs(x - P("tr_x0")), abs(x - P("tr_x1"))) < 0.5:
            g = "tail pocket shelf end"
        else:
            g = "other"
        out.append((g, e, mid, zr))
    return out


def fillet_group(group, feat_name):
    """one FilletFeature R fillet_root on every root edge of the group (rolling-ball corners)"""
    es = [e for g, e, m, z in root_edges() if g == group]
    if not es:
        log("fillet %s: no edges" % group)
        return None, 0
    coll = adsk.core.ObjectCollection.create()
    for e in es:
        coll.add(e)
    ff = root().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(coll, VI("fillet_root"), False)
    fi.isRollingBallCorner = True
    f = ff.add(fi)
    f.name = feat_name
    log("fillet %s: %d edges -> %s; %s" % (group, len(es), f.name, body_stats()))
    return f, len(es)


def face_owners():
    """tempId of every face of the body -> name of the extrude feature that created it"""
    owners = {}
    tl = des().timeline
    for i in range(tl.count):
        ent = tl.item(i).entity
        f = adsk.fusion.ExtrudeFeature.cast(ent)
        if f is None or f.isSuppressed:
            continue
        fs = f.faces
        for k in range(fs.count):
            owners[fs.item(k).tempId] = f.name
    return owners


def owner_group(o1, o2, mid):
    """root-edge group from the two creating features (names) of its faces"""
    s = {o1, o2}
    def has(prefix):
        return any(o and o.startswith(prefix) for o in s)
    if has("Stud "):
        return "stud tubes + ribs"
    if has("PCB bosses"):
        cell = any(math.hypot(mid[0] - P(h + "_x"), mid[1] + P(h + "_y")) < 6 for h in ("h6", "h7"))
        return "PCB bosses in cells (H6 H7)" if cell else "PCB bosses on the walls"
    if has("Cell ribs"):
        return "corner cells + cell ribs"
    if has("PCB support ribs"):
        return "PCB support ribs"
    if has("Corner cells"):
        return "corner cells + cell ribs"
    if has("Flange plate"):
        return "wall to flange"
    if has("Above-shelf space") or has("Window"):
        return "shelf back"
    if has("Panel pocket"):
        return "shelf front (pocket)"
    if has("Tail pocket"):
        return "tail pocket"
    if has("Tail wall block"):
        return "tail walls to wall top"          # v2.1: Z 0 wall top owned by the body block
    return "other: %s / %s" % (o1, o2)


def root_edges2(dot_max=0.5):
    """like root_edges() but grouped by the creating features of the two faces"""
    b = body()
    zf = P("Z_FRONT")
    owners = face_owners()
    holes = [(P("h%d_x" % i), -P("h%d_y" % i)) for i in range(1, 10)]
    studs = [(P(n.lower() + "_x"), -P(n.lower() + "_y")) for n, _, _, _ in STUDS]
    pegs = [(P("peg1_x"), -P("peg1_y")), (P("peg2_x"), -P("peg2_y"))]
    orig = (adsk.core.SurfaceTypes.PlaneSurfaceType, adsk.core.SurfaceTypes.ConeSurfaceType)
    out = []
    for i in range(b.edges.count):
        e = b.edges.item(i)
        if e.faces.count != 2 or any(e.faces.item(k).geometry.surfaceType not in orig for k in range(2)):
            continue
        conc, mid, zr = _edge_info2(b, e, dot_max)
        if not conc:
            continue
        x, y, z = mid
        if zr[0] < zf - 1e-4:
            continue
        if abs(zr[1] - zf) < 1e-3 and any(math.hypot(x - px, y - py) < P("peg_d") / 2 + 0.5 for px, py in pegs):
            continue
        if any(math.hypot(x - hx, y - hy) < P("cbore_d") / 2 + 0.2 for hx, hy in holes):
            continue
        if any(math.hypot(x - sx, y - sy) < P("stud_hole") / 2 + 0.3 for sx, sy in studs):
            continue
        o1, o2 = owners.get(e.faces.item(0).tempId), owners.get(e.faces.item(1).tempId)
        out.append((owner_group(o1, o2, mid), e, mid, zr, (o1, o2)))
    return out


def _edge_info2(b, e, dot_max, eps=0.005):
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


def rib_end_edge(e, mid, zr):
    """True for the edge between a support rib's FREE END face and the shelf back face (perpendicular to the
    rib axis, at Z_SHELF_BACK); False for its side roots."""
    if abs(zr[0] - P("Z_SHELF_BACK")) > 1e-3 or abs(zr[1] - P("Z_SHELF_BACK")) > 1e-3:
        return False
    x, y = mid[0], -mid[1]
    for (x0, x1, y0, y1, side) in RIBS:
        if x0 - 0.7 <= x <= x1 + 0.7 and y0 - 0.7 <= y <= y1 + 0.7:
            bb = e.boundingBox
            dx, dy = bb.maxPoint.x - bb.minPoint.x, bb.maxPoint.y - bb.minPoint.y
            return (dx > dy) if side in "TB" else (dy > dx)
    return False


def rib_index(mid):
    """index into RIBS of the support rib an edge midpoint (model mm) belongs to, else None"""
    x, y = mid[0], -mid[1]
    for k, (x0, x1, y0, y1, side) in enumerate(RIBS):
        if x0 - 0.7 <= x <= x1 + 0.7 and y0 - 0.7 <= y <= y1 + 0.7:
            return k
    return None


def thin_strips(b=None, dmax=1.0, min_overlap=0.2):
    """planar faces with two parallel, non-touching straight edges closer than dmax (mm) and overlapping
    (projected) by more than min_overlap: ledges, slots, thin wall tops hidden inside big merged faces.
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
            g = e.geometry
            if isinstance(g, adsk.core.Line3D):
                p, q = e.startVertex.geometry, e.endVertex.geometry
                lines.append((e, p, q))
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
                s1, s2 = 0.0, la
                t1 = t
                t2 = (q2.x - p1.x) * ux + (q2.y - p1.y) * uy + (q2.z - p1.z) * uz
                ov = (min(s2, max(t1, t2)) - max(s1, min(t1, t2))) * 10
                if ov > min_overlap:
                    m = ((p1.x + q1.x + p2.x + q2.x) * 2.5, -(p1.y + q1.y + p2.y + q2.y) * 2.5,
                         (p1.z + q1.z + p2.z + q2.z) * 2.5)
                    out.append((i, round(dist, 4), round(ov, 3), tuple(round(v, 3) for v in m)))
    return out


FILLET_SETS = {
    "stud tubes + ribs": lambda g, e, m, z: g == "stud tubes + ribs",
    "PCB bosses on the walls": lambda g, e, m, z: g == "PCB bosses on the walls",
    "corner cells + cell ribs + cell bosses": lambda g, e, m, z: g in ("PCB bosses in cells (H6 H7)",
                                                                        "corner cells + cell ribs"),
    "PCB support rib sides": lambda g, e, m, z: (g == "PCB support ribs" and rib_index(m) is not None
                                                 and not rib_end_edge(e, m, z)),
    "shelf back": lambda g, e, m, z: g == "shelf back",
    "shelf back (not into the tail pocket)": lambda g, e, m, z: g == "shelf back" and not _runs_into_tail(e),
    "wall to flange": lambda g, e, m, z: g == "wall to flange",
    "shelf front (pocket)": lambda g, e, m, z: g == "shelf front (pocket)",
    "tail pocket shelf end": lambda g, e, m, z: g == "tail pocket",
    "tail walls to wall top": lambda g, e, m, z: (g == "tail walls to wall top" or
                                                  (g == "PCB support ribs" and rib_index(m) is None)),
}


def fillet_set(set_name, radius="fillet_root"):
    """FilletFeature 'Root fillets R0.5 - <set_name>' on the edges of FILLET_SETS[set_name] (root_edges2(0.9))"""
    sel = FILLET_SETS[set_name]
    es = [e for g, e, m, z, o in root_edges2(0.9) if sel(g, e, m, z)]
    if not es:
        log("fillet set %s: no edges" % set_name)
        return None, 0
    coll = adsk.core.ObjectCollection.create()
    for e in es:
        coll.add(e)
    ff = root().features.filletFeatures
    fi = ff.createInput()
    fi.edgeSetInputs.addConstantRadiusEdgeSet(coll, VI(radius), False)
    fi.isRollingBallCorner = True
    f = ff.add(fi)
    f.name = "Root fillets R0.5 - " + set_name if radius == "fillet_root" else "Root fillets %s - %s" % (radius, set_name)
    log("fillet set %s: %d edges -> %s; %s" % (set_name, len(es), f.name, body_stats()))
    return f, len(es)


def _runs_into_tail(e):
    """wall/shelf-back edge that ends at the tail-pocket side face (the shelf continues there as the free strip,
    so an R0.5 run-out rolls across the whole shelf end: 0.04 mm wedge found 2026-11-13)"""
    k = math.tan(math.radians(P("draft")))
    xs = (P("tr_x0") - (P("Z_SHELF_BACK") - P("Z_FRONT")) * k, P("tr_x1") + (P("Z_SHELF_BACK") - P("Z_FRONT")) * k)
    bb = e.boundingBox
    at_bottom = abs(-bb.maxPoint.y * 10 - P("pocket_y1")) < 0.5      # only the bottom (tail pocket) side
    return at_bottom and any(bb.minPoint.x * 10 - 0.3 <= xx <= bb.maxPoint.x * 10 + 0.3 for xx in xs)


def set_appearance(b, name, lib="Fusion Appearance Library"):
    """copy a library appearance into the design (if needed) and assign it in the same call"""
    d = des()
    ap = d.appearances.itemByName(name)
    if ap is None:
        src = app().materialLibraries.itemByName(lib).appearances.itemByName(name)
        ap = d.appearances.addByCopy(src, name)
    b.appearance = ap
    return ap


# ------------------------------------------------------------------------------------- fit-assembly helpers
SCR = (r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\62ff0a1a-4475-4c41-9c45-d7dae40b64a5"
       r"\scratchpad\cad")
BOARD_COMP = "Rev3.0 PCB full (KiCad STEP)"


def asm_bodies():
    """deterministic list of (path, top_ref, body proxy) for every body under the board occurrence"""
    r = root()
    board = [r.occurrences.item(i) for i in range(r.occurrences.count)
             if r.occurrences.item(i).component.name == BOARD_COMP][0]
    out = []
    for k in range(board.bRepBodies.count):
        out.append((board.name, "(board root)", board.bRepBodies.item(k)))
    occs = board.childOccurrences
    stack = [(occs.item(i), occs.item(i).name) for i in range(occs.count)]
    while stack:
        o, top = stack.pop(0)
        for k in range(o.bRepBodies.count):
            out.append((o.fullPathName, top, o.bRepBodies.item(k)))
        ch = o.childOccurrences
        for i in range(ch.count):
            stack.append((ch.item(i), top))
    return board, out


def frame_proxy():
    r = root()
    occ = [r.occurrences.item(i) for i in range(r.occurrences.count)
           if r.occurrences.item(i).component.name.startswith("Rev3.0 Frame v2")][0]
    return occ, occ.bRepBodies.item(0)


def part_body(comp_name):
    r = root()
    occ = [r.occurrences.item(i) for i in range(r.occurrences.count)
           if r.occurrences.item(i).component.name == comp_name][0]
    return occ.bRepBodies.item(0)


def bbox_mm(b):
    bb = b.boundingBox
    return [round(bb.minPoint.x * 10, 3), round(bb.maxPoint.x * 10, 3), round(-bb.maxPoint.y * 10, 3),
            round(-bb.minPoint.y * 10, 3), round(bb.minPoint.z * 10, 3), round(bb.maxPoint.z * 10, 3)]


def overlap_volume_mm3(b1, b2):
    """volume of the intersection of two (proxy) bodies, via temporary BReps (mm3)"""
    tb = adsk.fusion.TemporaryBRepManager.get()
    a = tb.copy(b1)
    c = tb.copy(b2)
    ok = tb.booleanOperation(a, c, adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return a.volume * 1000.0 if ok else None


def min_dist_mm(e1, e2):
    r = app().measureManager.measureMinimumDistance(e1, e2)
    return r.value * 10.0, r.positionOne, r.positionTwo


RIB_RESULT = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\rib_pad_result.json"


def rib_rects_v21(overshoot=0.5):
    """v2.1 support-rib plan rectangles (abs KiCad): v1 position and width, wall end buried rib_bury, free ends
    run `overshoot` past the cut that trims them (window edge = panel outline - seat_w; over the tail pocket the
    shelf end = panel bottom edge), unless rib_pad_check.py kept the rib at its v1 length (pad < 1.0 mm)."""
    import json as _json
    kept = set(_json.load(open(RIB_RESULT))["kept_v1_length"])
    px0, px1, py0, py1 = P("panel_x0"), P("panel_x1"), P("panel_y0"), P("panel_y1")
    cl, sw, bury = P("pocket_clr"), P("seat_w"), P("rib_bury")
    tx0, tx1 = P("tr_x0"), P("tr_x1")
    out = []
    for k, (x0, x1, y0, y1, side) in enumerate(RIBS, 1):
        if side == "T":
            y0 = py0 - cl - bury
        elif side == "B" and y1 > py1:
            y1 = py1 + cl + bury
        elif side == "L":
            x0 = px0 - cl - bury
        elif side == "R":
            x1 = px1 + cl + bury
        ext = k not in kept
        if ext:
            if side == "T":
                y1 = py0 + sw + overshoot
            elif side == "B":
                y0 = py1 - sw - overshoot
                if tx0 < x0 and x1 < tx1:
                    y1 = py1 + overshoot
            elif side == "L":
                x1 = px0 + sw + overshoot
            elif side == "R":
                x0 = px1 - sw - overshoot
        out.append((k, side, ext, x0, x1, y0, y1))
    return out
