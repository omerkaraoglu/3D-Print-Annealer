"""39 - stage 2, Part C (READ-ONLY): fit checks among the frame and the assembly parts (no board bodies):
  * frame vs every part body (all variants): min distance (measureMinimumDistance), intersection volume when touching
  * every pair of part bodies whose bounding boxes come within 0.5 mm (different variants included; the report
    interprets variant conflicts)
  * flush plane: Z of the glass front face, the lip top face(s) and the sheet front face
  * pips: frame pip-top face (Z_PIP_TOP) -> glass body, per pip
  * bead / tape / gap thicknesses from the bodies' faces; stud protrusion over the nut; rivet grip; washer seats
  * sockets: each dia-12 socket vs the frame (all faces, and faces rising above the washer top)
Writes scratchpad fit_parts.json."""
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


def zr(b):
    bb = L.bbox_mm(b)
    return [bb[4], bb[5]]


def run(_context: str):
    L.check_doc()
    t0 = time.time()
    fr = A.frame()
    P = A.parts()
    res = {"levels": {k: round(L.P(k), 4) for k in (
        "Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_FLANGE_BACK", "Z_GLASS_BACK", "Z_CTP_FRONT", "Z_LAND",
        "Z_PIP_TOP", "Z_TUBE_TOP", "Z_PANEL_BACK", "Z_FORMEX_FRONT", "Z_SEAT")}}
    # ---------------------------------------------------------------- frame vs parts
    fp = []
    for cn, bn, b, v in P:
        r = A.pair(fr, b)
        r.update({"comp": cn, "body": bn, "variant": v, "bbox": L.bbox_mm(b)})
        fp.append(r)
    res["frame_vs_parts"] = fp
    # ---------------------------------------------------------------- part pairs (bbox within 0.5)
    pp = []
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            c1, n1, b1, v1 = P[i]
            c2, n2, b2, v2 = P[j]
            if "check" in (v1, v2):
                continue
            if A.bbox_gap(b1, b2) > 0.5:
                continue
            r = A.pair(b1, b2)
            r.update({"a": "%s / %s" % (c1, n1), "b": "%s / %s" % (c2, n2), "variants": [v1, v2]})
            pp.append(r)
    res["part_pairs_within_0.5"] = pp
    # ---------------------------------------------------------------- flush plane
    glass = A.part("Glass", "Glass")
    sheet = A.part("Oven sheet", "Oven sheet S4/S8 (no holes)")
    zf = L.P("Z_GLASS_FRONT")
    lip = faces_at(fr, zf, -1)
    gfront = faces_at(glass, zf, -1)
    sfront = faces_at(sheet, zf, -1)
    res["flush"] = {"glass_front_faces": [(round(f.pointOnFace.z * 10, 5), round(f.area * 100, 2)) for f in gfront],
                    "lip_top_faces": [(round(f.pointOnFace.z * 10, 5), round(f.area * 100, 2)) for f in lip],
                    "sheet_front_faces": [(round(f.pointOnFace.z * 10, 5), round(f.area * 100, 2)) for f in sfront],
                    "glass_zmin": zr(glass)[0], "frame_zmin": zr(fr)[0], "sheet_zmin": zr(sheet)[0]}
    # ---------------------------------------------------------------- pips
    pips = []
    for k in range(1, 9):
        xy = (L.P("pip%d_x" % k), L.P("pip%d_y" % k))
        tops = faces_at(fr, L.P("Z_PIP_TOP"), -1, xy, 1.0)
        if not tops:
            pips.append({"pip": k, "top_face": None})
            continue
        d, p1, p2 = L.min_dist_mm(tops[0], glass)
        pips.append({"pip": k, "xy_abs": xy, "top_z": round(tops[0].pointOnFace.z * 10, 4),
                     "top_dia_mm": round(2 * math.sqrt(tops[0].area * 100 / math.pi), 4), "to_glass_mm": round(d, 4)})
    res["pips"] = pips
    # ---------------------------------------------------------------- layer thicknesses
    bead = A.part("Bead", "Bead (4.0 x t_bond)")
    bond = A.part("Optical bond", "Optical bond (t_opt)")
    formex = A.part("Formex sheet", "Formex sheet")
    flange_front = faces_at(fr, L.P("Z_FLANGE_FRONT"), -1)
    res["layers"] = {
        "glass_z": zr(glass), "print_z": zr(A.part("Glass", "Glass print (black, 0.02)")), "bond_z": zr(bond),
        "bead_z": zr(bead), "formex_z": zr(formex), "sheet_z": zr(sheet),
        "tape_z": {n: zr(b) for c, n, b, v in P if c == "VHB tape strips"},
        "flange_front_faces_z": sorted(set(round(f.pointOnFace.z * 10, 4) for f in flange_front)),
        "land_faces_z": sorted(set(round(f.pointOnFace.z * 10, 4) for f in faces_at(fr, L.P("Z_LAND"), -1)))}
    # ---------------------------------------------------------------- fasteners
    fx = {}
    for cn, bn, b, v in P:
        if cn.startswith(("Fasteners", "Rivets", "Weld studs", "Washers")):
            fx[bn + " [" + v + "]"] = {"z": zr(b), "bbox": L.bbox_mm(b)}
    res["fasteners"] = fx
    # ---------------------------------------------------------------- sockets vs frame
    wtop = L.P("Z_TUBE_TOP") + L.P("w4_t")
    so = []
    for cn, bn, b, v in P:
        if v != "check":
            continue
        r = A.pair(b, fr)
        best = None
        cb = b.boundingBox
        for i in range(fr.faces.count):
            f = fr.faces.item(i)
            bb = f.boundingBox
            if bb.maxPoint.z * 10 <= wtop + 1e-4:
                continue
            gx = max(bb.minPoint.x - cb.maxPoint.x, cb.minPoint.x - bb.maxPoint.x, 0) * 10
            gy = max(bb.minPoint.y - cb.maxPoint.y, cb.minPoint.y - bb.maxPoint.y, 0) * 10
            if math.hypot(gx, gy) > 10:
                continue
            d, p1, p2 = L.min_dist_mm(b, f)
            if best is None or d < best["d_mm"]:
                best = {"d_mm": round(d, 4), "p_frame": L.pt_abs(p2), "face_area_mm2": round(f.area * 100, 2)}
        so.append({"socket": bn, "vs_frame_all": r, "vs_frame_faces_above_washer_top": best})
    res["sockets_vs_frame"] = so
    res["seconds"] = round(time.time() - t0, 1)
    p = L.dump(res, "fit_parts.json")
    bad = [(r["comp"], r["body"], r["d_mm"], r.get("overlap_mm3")) for r in fp if r["d_mm"] < 0.001]
    print(p, res["seconds"], "frame contacts/overlaps:", bad)
    print("pairs within 0.5:", [(r["a"], r["b"], r["d_mm"], r.get("overlap_mm3")) for r in pp if r["d_mm"] < 0.001])
    print("flush", res["flush"])
    print("pips", [(q["pip"], q.get("to_glass_mm")) for q in pips])
