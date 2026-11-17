"""78 - stage 4 (GF-2.0), READ-ONLY fit checks among the frame and the assembly part bodies (39 adapted, no S8):
  * frame vs every part body of every variant (S4, R4 hidden bodies, socket check cylinders, GF-2.0 tail solids):
    min distance (measureMinimumDistance) + intersection volume when touching (temporary BReps)
  * every pair of part bodies whose bounding boxes come within 0.5 mm (check cylinders excluded)
  * flush plane (glass front / lip top / sheet front Z), pip tops -> glass, layer Z ranges
  * g2: every glass edge face (4 sides, 4 corners) -> frame; g1: every cut-out face of both sheet bodies -> frame
  * bead: face area at Z_LAND (8 pip holes excluded by the body), width / thickness
  * VHB strips: area, strip-end -> corner-pad distance (F1-F4), strip -> frame
Writes %TEMP%\\rev3_glassfront\\gf20\\fit_parts.json."""
import importlib
import math
import sys
import time

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
import gfasm as A
importlib.reload(A)
DUMP = globals().get("DUMP") or "gf20"          # stage-5 runs set DUMP = "gf21" (dump sub-folder)


def faces_at(b, z_mm, sign, near=None, r=None):
    out = []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if abs(n.z) < 0.9999 or n.z * sign < 0 or abs(f.pointOnFace.z * 10 - z_mm) > 1e-3:
            continue
        if near is not None:
            c = f.centroid
            if math.hypot(c.x * 10 - near[0], -c.y * 10 - near[1]) > r:
                continue
        out.append(f)
    return out


def side_faces(b, zlo, zhi):
    """faces of b that are vertical-ish (|n.z| < 0.1) and lie within zlo..zhi: planar sides + cylindrical corners"""
    out = []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        bb = f.boundingBox
        if bb.minPoint.z * 10 < zlo - 1e-3 or bb.maxPoint.z * 10 > zhi + 1e-3:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if abs(n.z) > 0.1:
            continue
        out.append(f)
    return out


def zr(b):
    bb = L.bbox_mm(b)
    return [bb[4], bb[5]]


def lip_faces(fr):
    """the frame's vertical-ish faces in the lip zone (Z_GLASS_FRONT .. Z_SHEET_BACK): lip inner and outer faces"""
    zlo, zhi = L.P("Z_GLASS_FRONT"), L.P("Z_SHEET_BACK")
    col = adsk.core.ObjectCollection.create()
    out = []
    for i in range(fr.faces.count):
        f = fr.faces.item(i)
        bb = f.boundingBox
        if bb.minPoint.z * 10 < zlo - 1e-3 or bb.maxPoint.z * 10 > zhi + 1e-3:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if abs(n.z) > 0.1:
            continue
        out.append(f)
    return out


def ray_gap(b, x0, y0, z, ux, uy, smax=3.0, tol=0.0002):
    """distance from (x0, y0) (abs, y down) along (ux, uy) at height z to the first point inside body b (bisection on
    point containment after a 0.01 march); None if nothing within smax"""
    def inside(s):
        p = adsk.core.Point3D.create((x0 + s * ux) / 10.0, -(y0 + s * uy) / 10.0, z / 10.0)
        return b.pointContainment(p) == adsk.fusion.PointContainment.PointInsidePointContainment
    s = 0.0
    while s <= smax and not inside(s):
        s += 0.01
    if s > smax:
        return None
    lo, hi = max(0.0, s - 0.01), s
    while hi - lo > tol:
        m = (lo + hi) / 2
        if inside(m):
            hi = m
        else:
            lo = m
    return round((lo + hi) / 2, 4)


def rect_rays(b, x0, x1, y0, y1, r, zs, outward):
    """gaps from a rounded rectangle (abs) to body b at the 4 side midpoints and the 4 corner 45 deg points; outward
    = +1 rays go away from the rectangle centre (glass edge -> lip inner face), -1 towards it (cut-out -> lip outer)"""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    c45 = math.cos(math.radians(45))
    pts = {"left": (x0, cy, -1, 0), "right": (x1, cy, 1, 0), "top": (cx, y0, 0, -1), "bottom": (cx, y1, 0, 1)}
    for nm, ccx, ccy, sx, sy in (("corner top-left", x0 + r, y0 + r, -1, -1), ("corner top-right", x1 - r, y0 + r, 1, -1),
                                 ("corner bottom-right", x1 - r, y1 - r, 1, 1),
                                 ("corner bottom-left", x0 + r, y1 - r, -1, 1)):
        pts[nm] = (ccx + sx * r * c45, ccy + sy * r * c45, sx * c45, sy * c45)
    out = {}
    for nm, (px, py, ux, uy) in pts.items():
        out[nm] = {"%.3f" % z: ray_gap(b, px, py, z, outward * ux, outward * uy) for z in zs}
    return out


def side_gaps(faces, targets):
    """min distance of every planar side face to the target faces"""
    rows = []
    for f in faces:
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        best = None
        for t in targets:
            d, p1, p2 = L.min_dist_mm(f, t)
            if best is None or d < best[0]:
                best = (d, p1, p2)
        rows.append({"centroid": L.pt_abs(f.centroid), "d_min_mm": round(best[0], 4), "p_from": L.pt_abs(best[1]),
                     "p_to": L.pt_abs(best[2])})
    return rows


def corner_gaps(x0, x1, y0, y1, r, zs, targets):
    """gap at the 45 deg point of each corner arc of the rounded rectangle (abs coords, radius r) at heights zs"""
    rows = []
    c45 = math.cos(math.radians(45))
    for nm, cx, cy, sx, sy in (("top-left", x0 + r, y0 + r, -1, -1), ("top-right", x1 - r, y0 + r, 1, -1),
                               ("bottom-right", x1 - r, y1 - r, 1, 1), ("bottom-left", x0 + r, y1 - r, -1, 1)):
        best = None
        for z in zs:
            p = adsk.core.Point3D.create((cx + sx * r * c45) / 10.0, -(cy + sy * r * c45) / 10.0, z / 10.0)
            for t in targets:
                d, p1, p2 = L.min_dist_mm(p, t)
                if best is None or d < best[0]:
                    best = (d, z)
        rows.append({"corner": nm, "d_45deg_min_mm": round(best[0], 4), "at_z": round(best[1], 3)})
    return rows


def run(_context: str):
    L.check_doc()
    t0 = time.time()
    fr = A.frame()
    P = A.parts() + [(A.TAIL_COMP, n, b, "S4") for n, b in A.tails()]
    res = {"levels": {k: round(L.P(k), 4) for k in (
        "Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_GLASS_BACK", "Z_CTP_FRONT", "Z_LAND",
        "Z_PIP_TOP", "Z_TUBE_TOP", "Z_PANEL_BACK", "Z_FORMEX_FRONT", "Z_SEAT", "Z_FLOOR_LOW", "Z_LANDPLATE_BACK")}}
    fp = []
    for cn, bn, b, v in P:
        r = A.pair(fr, b)
        r.update({"comp": cn, "body": bn, "variant": v, "visible": b.isVisible, "bbox": L.bbox_mm(b)})
        fp.append(r)
    res["frame_vs_parts"] = fp
    pp = []
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            c1, n1, b1, v1 = P[i]
            c2, n2, b2, v2 = P[j]
            if "check" in (v1, v2) or A.bbox_gap(b1, b2) > 0.5:
                continue
            r = A.pair(b1, b2)
            r.update({"a": "%s / %s" % (c1, n1), "b": "%s / %s" % (c2, n2), "variants": [v1, v2]})
            pp.append(r)
    res["part_pairs_within_0.5"] = pp
    glass = A.part("Glass", "Glass")
    sheet = A.part("Oven sheet", "Oven sheet S4/S8 (no holes)")
    sheet_r4 = A.part("Oven sheet", "Oven sheet R4 (rivet holes)")
    zf = L.P("Z_GLASS_FRONT")
    res["flush"] = {"glass_front": sorted(set(round(f.pointOnFace.z * 10, 5) for f in faces_at(glass, zf, -1))),
                    "lip_top": sorted(set(round(f.pointOnFace.z * 10, 5) for f in faces_at(fr, zf, -1))),
                    "sheet_front": sorted(set(round(f.pointOnFace.z * 10, 5) for f in faces_at(sheet, zf, -1))),
                    "glass_zmin": zr(glass)[0], "frame_zmin": zr(fr)[0], "sheet_zmin": zr(sheet)[0]}
    pips = []
    for k in range(1, 9):
        xy = (L.P("pip%d_x" % k), L.P("pip%d_y" % k))
        tops = faces_at(fr, L.P("Z_PIP_TOP"), -1, xy, 1.0)
        if not tops:
            pips.append({"pip": k, "top_face": None})
            continue
        d, p1, p2 = L.min_dist_mm(tops[0], glass)
        pips.append({"pip": k, "xy_abs": [round(v, 4) for v in xy], "top_z": round(tops[0].pointOnFace.z * 10, 4),
                     "to_glass_mm": round(d, 4)})
    res["pips"] = pips
    # g2 glass edge faces -> frame, g1 cut-out faces -> frame
    gx0, gx1, gy0, gy1, rg = L.P("glass_x0"), L.P("glass_x1"), L.P("glass_y0"), L.P("glass_y1"), L.P("R_glass")
    zgf, zgb = L.P("Z_GLASS_FRONT"), L.P("Z_GLASS_BACK")
    za, zb = zgf + L.P("glass_arris"), zgb - L.P("glass_arris")
    zs2 = [zgf + 0.001, za, (za + zb) / 2, zb, zgb - 0.001]
    res["g2_glass_edge_to_lip"] = {
        "gaps": rect_rays(fr, gx0, gx1, gy0, gy1, rg, zs2, +1),
        "note": "ray from the nominal glass edge (rounded rectangle glass_*, R_glass) outward to the first frame "
                "material, at the side midpoints and the 45 deg corner points; Z = flush plane, the two arris ends, mid, "
                "glass back (the recess narrows 1 deg to the back)"}
    sc = L.P("s_cut")
    zss = L.P("Z_SHEET_BACK")
    zs1 = [zgf + 0.001, (zgf + zss) / 2, zss - 0.25]
    res["g1_cutout_to_lip"] = {
        "gaps": rect_rays(fr, gx0 - sc, gx1 + sc, gy0 - sc, gy1 + sc, L.P("R_cut"), zs1, -1),
        "note": "ray from the nominal sheet cut-out edge (glass + s_cut, R_cut) inward to the lip outer face, at the "
                "flush plane, mid sheet and 0.25 above the sheet back (above the R0.2 lip-root fillet)"}
    # bead
    bead = A.part("Bead", "Bead (4.0 x t_bond)")
    bf = faces_at(bead, L.P("Z_LAND"), +1) + faces_at(bead, L.P("Z_LAND"), -1)
    res["bead"] = {"faces_at_Z_LAND_mm2": [round(f.area * 100, 2) for f in bf], "bbox": L.bbox_mm(bead),
                   "z": zr(bead), "volume_mm3": round(bead.volume * 1000, 2)}
    # tape strips
    tapes = []
    pads = []
    for i in range(fr.faces.count):
        f = fr.faces.item(i)
        if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        bb = f.boundingBox
        if bb.minPoint.z * 10 < L.P("Z_SHEET_BACK") - 1e-3 or bb.maxPoint.z * 10 > L.P("Z_FLANGE_FRONT") + 1e-3:
            continue
        c = f.centroid
        k = min((1, 2, 3, 4), key=lambda q: math.hypot(c.x * 10 - L.P("f%d_x" % q), -c.y * 10 - L.P("f%d_y" % q)))
        if math.hypot(c.x * 10 - L.P("f%d_x" % k), -c.y * 10 - L.P("f%d_y" % k)) < 9.6:
            pads.append((k, f))
    for c_, n_, b_, v_ in P:
        if c_ != "VHB tape strips":
            continue
        tf = faces_at(b_, L.P("Z_SHEET_BACK"), -1)
        dmin = None
        for k, pf in pads:
            d, p1, p2 = L.min_dist_mm(b_, pf)
            if dmin is None or d < dmin[0]:
                dmin = (d, k)
        tapes.append({"strip": n_, "area_mm2": round(sum(f.area for f in tf) * 100, 2), "bbox": L.bbox_mm(b_),
                      "to_pad_mm": round(dmin[0], 4) if dmin else None, "pad": dmin[1] if dmin else None,
                      "to_frame": A.pair(fr, b_)})
    res["tape"] = {"strips": tapes, "total_area_mm2": round(sum(t["area_mm2"] for t in tapes), 2),
                   "pad_side_faces_found": len(pads)}
    res["seconds"] = round(time.time() - t0, 1)
    p = L.dump(res, DUMP + "/fit_parts.json")
    bad = [(r["comp"], r["body"], r["variant"], r["d_mm"], r.get("overlap_mm3")) for r in fp if r["d_mm"] < 0.001]
    print(p, res["seconds"], "frame contacts/overlaps:", bad)
    print("pairs touching:", [(r["a"], r["b"], r["d_mm"], r.get("overlap_mm3")) for r in pp if r["d_mm"] < 0.001])
    print("g2", res["g2_glass_edge_to_lip"]["gaps"])
    print("g1", res["g1_cutout_to_lip"]["gaps"])
    print("bead", res["bead"]["faces_at_Z_LAND_mm2"], "tape", res["tape"]["total_area_mm2"],
          [(t["strip"], t["area_mm2"], t["to_pad_mm"]) for t in tapes])
    print("pips", [(q["pip"], q.get("to_glass_mm")) for q in pips], "flush", res["flush"])
