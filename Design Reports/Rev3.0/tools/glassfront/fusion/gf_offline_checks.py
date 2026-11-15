"""Offline checks (plain Python + shapely, run outside Fusion) on the dumps written by the Fusion scripts into
%TEMP%\\rev3_glassfront:
  thin   sections_gf.json (21)       -> inscribed-disc probe per plan section: material thinner than 1.0 mm
                                        (opening by a 1.0 disc) and gaps narrower than 1.0 mm (closing by a 1.0 disc);
                                        components below 0.10 mm2 are corner specks (as v2 cadcheck)
  abovez above_z0.json (23)          -> distance of all frame material above Z 0 to the KiCad board outline
                                        (Design Reports/Rev3.0/tools/frame/out/board_geom.json, ears included)
  carry  carry_sections.json (22)    -> GF vs v2 STEP plan sections in the carried-over regions (XOR areas)
Usage: python gf_offline_checks.py [thin|abovez|carry|all]   -> writes offline_<check>.json next to the dumps."""
import json
import os
import sys

from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import polygonize, unary_union

SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
BOARD = (r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame\out"
         r"\board_geom.json")
THIN = 1.0
SPECK = 0.10


def chain_ring(edges, tol=0.02):
    """order the sampled edges of one loop end to end (endpoint tolerance tol mm) -> closed ring point list"""
    rest = [list(map(tuple, e)) for e in edges if len(e) >= 2]
    if not rest:
        return None
    ring = rest.pop(0)
    while rest:
        end = ring[-1]
        best, k_best, rev = None, None, False
        for k, e in enumerate(rest):
            for r_, p in ((False, e[0]), (True, e[-1])):
                dd = (p[0] - end[0]) ** 2 + (p[1] - end[1]) ** 2
                if best is None or dd < best:
                    best, k_best, rev = dd, k, r_
        if best > tol * tol:
            return None
        e = rest.pop(k_best)
        ring += (e[::-1] if rev else e)[1:]
    return ring


def loop_polygon(edges):
    ring = chain_ring(edges)
    if ring is not None and len(ring) >= 4:
        p = Polygon(ring)
        if not p.is_valid:
            p = p.buffer(0)
        if p.area > 0:
            return p
    segs = []
    for pts in edges:
        for a, b in zip(pts[:-1], pts[1:]):
            if a != b:
                segs.append(LineString([a, b]))
    polys = list(polygonize(unary_union(segs)))
    if not polys:
        return None
    return unary_union(polys)


def level_material(faces):
    parts = []
    for f in faces:
        outer, inner = None, []
        for lp in f["loops"]:
            p = loop_polygon(lp["edges"])
            if p is None:
                continue
            if lp["outer"]:
                outer = p
            else:
                inner.append(p)
        if outer is None:
            continue
        parts.append(outer.difference(unary_union(inner)) if inner else outer)
    return unary_union(parts)


def comps(geom):
    if geom.is_empty:
        return []
    gs = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    out = []
    for g in gs:
        if g.area < SPECK:
            continue
        x0, y0, x1, y1 = g.bounds
        ext = max(x1 - x0, y1 - y0)
        if ext < 1.0:
            continue
        # width estimate: area / length of the longer bbox side (parallel-sided strips)
        out.append({"centroid_abs": [round(g.centroid.x, 3), round(g.centroid.y, 3)], "area_mm2": round(g.area, 4),
                    "bbox": [round(v, 3) for v in (x0, y0, x1, y1)], "width_est_mm": round(g.area / ext, 3),
                    "length_mm": round(ext, 3)})
    return out


def check_thin():
    d = json.load(open(os.path.join(SCR, "sections_gf.json")))
    res = {"method": "plan sections (Fusion planeIntersection, chord tol 0.005); thin wall = material - opening by a "
                     "disc of dia %.1f; thin gap = closing by the same disc - material; components < %.2f mm2 or "
                     "< 1.0 mm long ignored (corner specks)" % (THIN, SPECK), "levels": []}
    for z, faces in sorted(d["levels"].items(), key=lambda kv: float(kv[0])):
        m = level_material(faces)
        r = THIN / 2
        opened = m.buffer(-r, quad_segs=32).buffer(r, quad_segs=32)
        thin = m.difference(opened)
        closed = m.buffer(r, quad_segs=32).buffer(-r, quad_segs=32)
        gaps = closed.difference(m)
        res["levels"].append({"z": float(z), "material_area_mm2": round(m.area, 2), "thin_walls": comps(thin),
                              "thin_gaps": comps(gaps)})
    json.dump(res, open(os.path.join(SCR, "offline_thin.json"), "w"), indent=1)
    for lv in res["levels"]:
        print("z %7.3f area %9.1f  thin walls %d  thin gaps %d" % (lv["z"], lv["material_area_mm2"],
                                                                  len(lv["thin_walls"]), len(lv["thin_gaps"])))
        for t in lv["thin_walls"]:
            print("     wall", t)
        for t in lv["thin_gaps"]:
            print("     gap ", t)
    return res


def board_outline():
    g = json.load(open(BOARD))
    polys = [Polygon(p) for p in g["outline"]]
    return max(polys, key=lambda p: p.area)


def check_abovez():
    d = json.load(open(os.path.join(SCR, "above_z0.json")))
    poly = board_outline()
    grown = poly.buffer(1.0)
    pts = [Point(p[0], p[1]) for p in d["points"] if p[2] > 1e-4]
    inside = sum(1 for p in pts if grown.contains(p))
    dmin = min((poly.exterior.distance(p) if not poly.contains(p) else -poly.exterior.distance(p)) for p in pts)
    res = {"volume_above_Z0_mm3": d["volume_mm3"], "lumps": d["lumps"], "bbox_abs": d["bbox_abs"],
           "points": len(pts), "points_inside_outline_plus_1mm": inside,
           "min_distance_to_pcb_outline_mm": round(dmin, 3),
           "volume_inside_outline_plus_1mm_mm3": 0.0 if inside == 0 and dmin > 1.0 else None,
           "board_outline_bbox": [round(v, 3) for v in poly.bounds]}
    json.dump(res, open(os.path.join(SCR, "offline_abovez.json"), "w"), indent=1)
    print(res)
    return res


def check_carry():
    d = json.load(open(os.path.join(SCR, "carry_sections.json")))
    out = {"levels": []}
    for z, rec in sorted(d["levels"].items(), key=lambda kv: float(kv[0])):
        gf = level_material(rec["gf"])
        v2 = level_material(rec["v2"])
        rows = []
        for name, bx in rec["boxes"]:
            B = box(*bx)
            a, b = gf.intersection(B), v2.intersection(B)
            x = a.symmetric_difference(b)
            rows.append({"region": name, "box": bx, "gf_area": round(a.area, 4), "v2_area": round(b.area, 4),
                         "xor_area_mm2": round(x.area, 4)})
        out["levels"].append({"z": float(z), "regions": rows})
    json.dump(out, open(os.path.join(SCR, "offline_carry.json"), "w"), indent=1)
    for lv in out["levels"]:
        print("z", lv["z"])
        for r in lv["regions"]:
            print("   %-40s gf %9.4f v2 %9.4f xor %8.4f" % (r["region"], r["gf_area"], r["v2_area"], r["xor_area_mm2"]))
    return out


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("thin", "all"):
        check_thin()
    if what in ("abovez", "all"):
        check_abovez()
    if what in ("carry",):
        check_carry()
