"""70 - stage 4 (GF-2.0): FPC tail solids on the bent-back route, for the fit checks (concept_gf2.md sec. 2).
Component 'Tails GF-2.0 (bent-back route)' (new, under the root):
  centre line = tail_route.<TFT|CTP>.centreline_yZ of ../concept/concept_gf2_params.json (abs y, Z; glass-independent),
  thickness tail_t 0.30 (band +-0.15 normal to the centre line), developed length v from the panel edge (y 119.00);
  x extent per v segment = the developed outline of the tail (OUTLINE below; concept_gf2_calc_out.txt, checked against
  the DS1 tail bodies by diag_gf20_old_tail_widths.py):
    TFT v 0-7 x 84.02-122.62 (bonded width), v 7-31 x 84.02-165.90 (L-shaped wide part), v 31-L x 145.40-165.90
    CTP v 0-9.5 x 40.72-75.82, v 9.5-34 x 50.92-70.62, v 34-L x 58.27-61.77
  one sketch per segment on a YZ-parallel plane at its x0, extruded to x1 (new body), segments of a tail combined.
  Bodies 'TFT tail GF-2.0 (bent back)' / 'CTP tail GF-2.0 (bent back)'.
The GF-1.1 / DS1 tail bodies (tft_tail_5, tft_fingers_6, ctp_tail_7, ctp_fingers_8: flat front leg + U-loop, rigid
DS1 shift) are hidden and renamed 'GF-1.1 reference - ... (old flat route, hidden)'; they stay in the board import.
Refuses to run twice."""
import importlib
import json
import math
import os
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
import gfasm as A
importlib.reload(A)

CONCEPT = os.path.join(L.REPO, "Design Reports", "Rev3.0", "tools", "glassfront", "concept", "concept_gf2_params.json")
OUTLINE = {"TFT": [(0.0, 7.0, 84.02, 122.62), (7.0, 31.0, 84.02, 165.90), (31.0, None, 145.40, 165.90)],
           "CTP": [(0.0, 9.5, 40.72, 75.82), (9.5, 34.0, 50.92, 70.62), (34.0, None, 58.27, 61.77)]}
BODY = {"TFT": "TFT tail GF-2.0 (bent back)", "CTP": "CTP tail GF-2.0 (bent back)"}
OLD = ["tft_tail_5", "tft_fingers_6", "ctp_tail_7", "ctp_fingers_8"]
HALF_T = 0.15


def cum_len(pts):
    v = [0.0]
    for i in range(1, len(pts)):
        v.append(v[-1] + math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
    return v


def interp(pts, v, s):
    for i in range(1, len(pts)):
        if v[i] >= s - 1e-12:
            t = (s - v[i - 1]) / (v[i] - v[i - 1]) if v[i] > v[i - 1] else 0.0
            return (pts[i - 1][0] + t * (pts[i][0] - pts[i - 1][0]), pts[i - 1][1] + t * (pts[i][1] - pts[i - 1][1])), i
    return pts[-1], len(pts) - 1


def band(pts, va, vb):
    """closed polygon (abs y, Z) of the 0.30 band along the centre line between developed lengths va and vb"""
    v = cum_len(pts)
    pa, ia = interp(pts, v, va)
    pb, ib = interp(pts, v, vb)
    seg = [pa] + [pts[i] for i in range(ia, ib) if va + 1e-6 < v[i] < vb - 1e-6] + [pb]
    left, right = [], []
    n = len(seg)
    for i in range(n):
        p0 = seg[max(i - 1, 0)]
        p1 = seg[min(i + 1, n - 1)]
        ty, tz = p1[0] - p0[0], p1[1] - p0[1]
        ln = math.hypot(ty, tz)
        ny, nz = -tz / ln, ty / ln
        left.append((seg[i][0] + HALF_T * ny, seg[i][1] + HALF_T * nz))
        right.append((seg[i][0] - HALF_T * ny, seg[i][1] - HALF_T * nz))
    return left + right[::-1]


def appearance_any(names):
    for nm in names:
        try:
            return L.appearance(nm)
        except Exception:
            continue
    return None


def run(_context: str):
    d = L.check_doc()
    L.log("=== 70 start")
    if L.occ_by_comp(A.TAIL_COMP, False) is not None:
        raise RuntimeError("70 already applied")
    route = json.load(open(CONCEPT, encoding="utf-8"))["tail_route"]
    o = L.new_comp(A.TAIL_COMP)
    c = o.component
    res = {}
    ap = appearance_any(["Plastic - Matte (Orange)", "Paint - Enamel Glossy (Orange)", "Plastic - Glossy (Orange)",
                         "Plastic - Matte (Yellow)"])
    for tail in ("TFT", "CTP"):
        pts = [tuple(p) for p in route[tail]["centreline_yZ"]]
        vtot = cum_len(pts)[-1]
        bodies = []
        segs = []
        for k, (va, vb, x0, x1) in enumerate(OUTLINE[tail]):
            vb = vtot if vb is None else vb
            poly = band(pts, va, vb)
            pi = c.constructionPlanes.createInput()
            pi.setByOffset(c.yZConstructionPlane, L.VI("%.4f mm" % x0))
            pl = c.constructionPlanes.add(pi)
            pl.name = "%s tail x %.2f" % (tail, x0)
            pl.isLightBulbOn = False
            sk = c.sketches.add(pl)
            sk.name = "%s tail v %.2f-%.2f sketch" % (tail, va, vb)
            sk.isComputeDeferred = True
            sp = [sk.modelToSketchSpace(adsk.core.Point3D.create(x0 / 10.0, -y / 10.0, z / 10.0)) for y, z in poly]
            lines = sk.sketchCurves.sketchLines
            ln = lines.addByTwoPoints(sp[0], sp[1])
            first, prev = ln.startSketchPoint, ln.endSketchPoint
            for i in range(2, len(sp)):
                ln = lines.addByTwoPoints(prev, sp[i])
                prev = ln.endSketchPoint
            lines.addByTwoPoints(prev, first)
            sk.isComputeDeferred = False
            if sk.profiles.count != 1:
                raise RuntimeError("%s seg %d: %d profiles" % (tail, k, sk.profiles.count))
            f = L.cextrude(c, sk.profiles.item(0), "new", "%.4f mm" % (x1 - x0), +1,
                           "%s tail v %.2f-%.2f" % (tail, va, vb))
            b = f.bodies.item(0)
            bb = b.boundingBox
            if abs(bb.minPoint.x * 10 - x0) > 0.01 or abs(bb.maxPoint.x * 10 - x1) > 0.01:
                raise RuntimeError("%s seg %d extruded the wrong way: x %.3f..%.3f" % (
                    tail, k, bb.minPoint.x * 10, bb.maxPoint.x * 10))
            bodies.append(b)
            segs.append({"v": [va, round(vb, 3)], "x": [x0, x1], "points": len(poly), "volume_mm3": round(b.volume * 1000, 3)})
        tools = adsk.core.ObjectCollection.create()
        for b in bodies[1:]:
            tools.add(b)
        ci = c.features.combineFeatures.createInput(bodies[0], tools)
        ci.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        cf = c.features.combineFeatures.add(ci)
        cf.name = "%s tail segments joined" % tail
        tb = cf.bodies.item(0)
        tb.name = BODY[tail]
        if ap is not None:
            tb.appearance = ap
        res[tail] = {"developed_length": round(vtot, 3), "segments": segs, "bbox": L.bbox_mm(tb),
                     "volume_mm3": round(tb.volume * 1000, 3), "lumps": tb.lumps.count}
    # old tails: hide + rename
    ren = {}
    for p, b in A.board():
        if not A.is_ds1(p):
            continue
        nm = A.ds1_part(p)
        if nm in OLD:
            nb = b.nativeObject if b.nativeObject else b
            old = nb.name
            try:
                nb.name = "GF-1.1 reference - %s (old flat route, hidden)" % nm
            except Exception as ex:
                ren[nm + " rename failed"] = str(ex)
            nb.isLightBulbOn = False
            ren[nm] = [old, nb.name, nb.isLightBulbOn]
    res["old_tails"] = ren
    n, bad = L.timeline_health()
    res.update({"timeline": n, "unhealthy": bad})
    L.dump(res, "gf20/70_tails.json")
    L.log("70 %s" % res)
    print(res)
