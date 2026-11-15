"""C. Carried-over geometry: everything of the GF frame at Z >= Z_FORMEX_FRONT (-5.0) must equal frame v2 except
where the params say otherwise.

  <venv>\\Scripts\\python.exe carryover.py [--frame f.step] [--v2 v2.step]

Method. OCC booleans between the two STEPs fail (they share most faces: GF - v2 returns all of GF with any fuzzy /
glue option - tested), so the difference is measured with vertical rays instead, which is exact where it matters:
  1. mesh pass: VTK OBB trees of both solids (0.005 mm mesh), vertical rays on a 0.25 mm grid; per column the
     material intervals clipped to Z >= -5.0 are compared (lengths of GF-only and v2-only material);
  2. exact pass: every column whose mesh difference exceeds 0.01 mm is re-measured with the exact OCC line probe
     on both B-reps (removes mesh chord noise on drafted cones);
  3. columns with an exact difference > 0.005 mm are labelled into connected regions (8-neighbour); each region:
     volume (sum of length x 0.25^2), plan bbox, Z range, explanation from the params:
       * clearance pocket 0.8 (v2 0.25): the pocket wall moved 0.55 outwards; rib wall ends; shelf-front strip;
       * tail pocket bottom 147.70 / R1.5 (v2 151.2 / R5): bottom beam (and the corner-cell bottom walls) moved;
       * v2 stud tubes FH1-FH10 replaced by F1-F8;
       * anything else: UNEXPLAINED.
Plus wall probes (exact) on both STEPs: how far each wall face moved.
"""
import json
import math
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import vcommon as C

STEP = 0.25
MESH_THR = 0.01
EXACT_THR = 0.005


def v2_studs():
    d = json.load(open(C.V2_PARAMS))
    return {s["name"]: (s["x_abs"], s["y_abs_down"]) for s in d["stud_holes"]}


def iv_len(iv):
    return sum(b - a for a, b in iv)


def iv_and(A, B):
    out = []
    for a0, a1 in A:
        for b0, b1 in B:
            lo, hi = max(a0, b0), min(a1, b1)
            if hi > lo:
                out.append((lo, hi))
    return out


def clip(iv, z0):
    return [(max(a, z0), b) for a, b in iv if b > z0]


def mesh_intervals(obb, pts, X, Y, za, zb):
    pts.Reset()
    obb.IntersectWithLine((X, Y, za), (X, Y, zb), pts, None)
    n = pts.GetNumberOfPoints()
    zz = sorted(pts.GetPoint(i)[2] for i in range(n))
    u = []
    for z in zz:
        if not u or z - u[-1] > 1e-5:
            u.append(z)
    if len(u) % 2:
        return None
    return [(u[i], u[i + 1]) for i in range(0, len(u), 2)]


def explain(G, reg, studs):
    x0, x1, y0, y1 = reg["bbox_abs"]
    z0, z1 = reg["z_range"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    tx0, tx1, ty0, ty1, _ = G.TAIL
    px0, px1, py0, py1, _ = G.POCKET
    inside_studs = [n for n, (sx, sy) in studs.items() if x0 - 1 < sx < x1 + 1 and y0 - 1 < sy < y1 + 1]
    fill = reg["columns"] * STEP * STEP / max((x1 - x0) * (y1 - y0), 1e-9)
    # 1. tail pocket / bottom beam (v2 151.2 / R5 -> GF 147.70 / R1.5); the v2 beam region also holds FH6-FH8
    if x0 < tx1 + 3 and x1 > tx0 - 3 and y1 > ty1 - 2.5 and (x1 - x0) > 20:
        s = "tail pocket bottom 147.70 / R1.5 (v2 151.2 / R5): bottom beam and side-wall ends moved 3.5 (params v2_superseded tr_y1, trough_r)"
        if reg["kind"] == "v2 only" and inside_studs:
            s += "; incl. the v2 stud tubes %s on the old beam (v2 mounting replaced)" % "/".join(inside_studs)
        return s
    # 1b. GF-1.1: tail-pocket side walls moved out (tail_side_add) - thin strips along x = tx0 / tx1
    tsa = float(G.drv.get("tail_side_add", 0.0) or 0.0)
    if tsa and (x1 - x0) < 1.5 and y0 > 117 and (abs((x0 + x1) / 2 - tx0) < 1.2 or abs((x0 + x1) / 2 - tx1) < 1.2):
        return "tail-pocket side wall moved out %.1f (params tail_side_add, GF-1.1): strip %s" % (
            tsa, "vacated" if reg["kind"] == "v2 only" else "added")
    # 1c. GF-1.1: H6 corner cell re-cored per params corner_cell_H6
    if G.h6 and x0 > 165.5 and x1 < 177.5 and y0 > 117 and y1 < 131.5:
        return "H6 corner cell re-cored per params corner_cell_H6 (GF-1.1: jogged wall, R%.1f corner)" % float(G.h6.get("h6_corner_r", 0))
    # 2. v2 stud tubes
    if reg["kind"] == "v2 only" and inside_studs and z1 < -3.4:
        return "v2 stud tube %s (to Z -3.52) - v2 mounting replaced by F1-F8 (params v2_superseded)" % "/".join(inside_studs)
    # 3. ring-shaped regions
    if (x1 - x0) > 150 and (y1 - y0) > 90 and z1 <= G.L["Z_SEAT"] + 0.05:
        return "shelf front between the v2 pocket line (panel + 0.25) and the GF pocket (panel + 0.8), Z -5.0..-4.6 (pocket_clr superseded)"
    if (x1 - x0) > 150 and (y1 - y0) > 90:
        return "pocket wall moved 0.55 outwards (pocket_clr 0.80 vs v2 0.25): strip vacated at the inner face / rib wall ends"
    # 4. thin strips (or thin L-shapes at a corner) along the wall: within -1.5 .. +3.5 of the GF pocket line
    #    (the corner cells' outer walls continue the side walls below the pocket)
    def near_wall_line(xa, xb, ya, yb):
        dxl = (px0 - 3.6 <= xa and xb <= px0 + 1.6)
        dxr = (px1 - 1.6 <= xa and xb <= px1 + 3.6)
        dyt = (py0 - 3.6 <= ya and yb <= py0 + 1.6)
        dyb = (py1 - 1.6 <= ya and yb <= py1 + 3.6)
        return dxl or dxr or dyt or dyb
    def near_corner(xa, xb, ya, yb):
        return any(abs(cx_ - (xa + xb) / 2) < 7 and abs(cy_ - (ya + yb) / 2) < 7 for cx_ in (px0, px1) for cy_ in (py0, py1))
    if (min(x1 - x0, y1 - y0) < 2.2 and near_wall_line(x0, x1, y0, y1)) or (fill < 0.35 and near_corner(x0, x1, y0, y1)):
        return "pocket wall moved 0.55 outwards with pocket_clr 0.80 (v2 0.25): %s" % (
            "strip added at the outer face (incl. the cell outer walls)" if reg["kind"] == "GF only" else
            "strip vacated at the inner face / rib wall ends")
    if y0 > 118 and (x1 < tx0 + 2 or x0 > tx1 - 2):
        if y1 > ty1 - 3:
            return "corner cell: bottom wall = bottom beam moved 3.5 with tr_y1 (and its inner wall moved 0.55)"
        return "corner-cell region (H6/H7) - NOT in v2_superseded (the H6/H7 cells were being reworked)"
    return "UNEXPLAINED by the params"


def run(ctx, log=C.log):
    import vtk
    from scipy import ndimage
    t0 = time.time()
    G = ctx.G
    zs = G.L["Z_FORMEX_FRONT"]
    gf, v2 = ctx.frame, ctx.v2
    _, og = __import__("mould_check").vtk_mesh(gf)
    _, ov = __import__("mould_check").vtk_mesh(v2)
    # plan extent of material above zs in either part
    xs_, ys_ = [], []
    for s in (gf, v2):
        sl = C.common_shape(s, C.box(-50, 260, -220, 50, zs, 20))
        bb = C.optimal_bbox(sl)
        xs_ += [bb[0], bb[1]]; ys_ += [bb[2], bb[3]]
    X = np.arange(min(xs_) - 0.5 + STEP / 2, max(xs_) + 0.5, STEP)
    Y = np.arange(min(ys_) - 0.5 + STEP / 2, max(ys_) + 0.5, STEP)
    za, zb = -30.0, 20.0
    pts = vtk.vtkPoints()
    dg = np.zeros((len(Y), len(X)), np.float32)     # GF-only length
    dv = np.zeros((len(Y), len(X)), np.float32)     # v2-only length
    zlo = np.full((len(Y), len(X)), np.nan, np.float32)
    zhi = np.full((len(Y), len(X)), np.nan, np.float32)
    cand = []
    # columns worth shooting: where either part has material in a plan section of the slab (dense Z list,
    # dilated by 2 cells); everywhere else both parts are empty above zs
    from PIL import Image, ImageDraw
    mask = np.zeros((len(Y), len(X)), bool)
    zlist = [zs + 0.01, -4.8, -4.61, -4.59, -4.3, -3.5, -2.6, -2.11, -2.09, -1.5, -0.6, -0.3, -0.01, 0.01, 1.0, 2.5, 4.0]
    for s in (gf, v2):
        for zq in zlist:
            sec = C.plane_section(s, "z", zq)
            if sec is None:
                continue
            img = Image.new("1", (len(X), len(Y)), 0)
            dr = ImageDraw.Draw(img)
            for f in sec.Faces():
                lps = C.face_loops_3d(f, 0.01)
                dr.polygon([((p[0] - X[0]) / STEP, (p[1] - Y[0]) / STEP) for p in lps[0]], fill=1, outline=1)
                for hl in lps[1:]:
                    dr.polygon([((p[0] - X[0]) / STEP, (p[1] - Y[0]) / STEP) for p in hl], fill=0, outline=1)
            mask |= np.array(img, dtype=bool)
    mask = ndimage.binary_dilation(mask, iterations=2)
    jj_, ii_ = np.nonzero(mask)
    log("[C] mesh pass: %d of %d columns (material in the slab +-2 cells)" % (len(jj_), len(X) * len(Y)))
    for j, i in zip(jj_, ii_):
        Yv, Xv = Y[j], X[i]
        if True:
            a = mesh_intervals(og, pts, Xv, Yv, za, zb)
            b = mesh_intervals(ov, pts, Xv, Yv, za, zb)
            if a is None or b is None:
                cand.append((j, i))
                continue
            a, b = clip(a, zs), clip(b, zs)
            if not a and not b:
                continue
            inter = iv_len(iv_and(a, b))
            if iv_len(a) - inter > MESH_THR or iv_len(b) - inter > MESH_THR:
                cand.append((j, i))
    log("    candidates for the exact pass: %d" % len(cand))
    Pg, Pv = C.Probe(gf), C.Probe(v2)
    for j, i in cand:
        Xv, Yv = X[i], Y[j]
        a = clip(Pg.z_intervals_fast(Xv, -Yv), zs)
        b = clip(Pv.z_intervals_fast(Xv, -Yv), zs)
        inter = iv_and(a, b)
        li = iv_len(inter)
        g_only, v_only = iv_len(a) - li, iv_len(b) - li
        if g_only > EXACT_THR:
            dg[j, i] = g_only
        if v_only > EXACT_THR:
            dv[j, i] = v_only
        if g_only > EXACT_THR or v_only > EXACT_THR:
            ends = [z for iv in (a, b) for p in iv for z in p if not any(abs(z - q) < 1e-4 for r in inter for q in r)]
            if ends:
                zlo[j, i], zhi[j, i] = min(ends), max(ends)
    cell = STEP * STEP
    regions = []
    studs = v2_studs()
    for kind, arr in (("GF only", dg), ("v2 only", dv)):
        lab, n = ndimage.label(arr > 0, structure=np.ones((3, 3)))
        for k, sl in enumerate(ndimage.find_objects(lab), start=1):
            m = lab[sl] == k
            vol = float(arr[sl][m].sum() * cell)
            jj, ii = np.nonzero(m)
            xa, xb = X[sl[1].start + ii.min()] - STEP / 2, X[sl[1].start + ii.max()] + STEP / 2
            Ya, Yb = Y[sl[0].start + jj.min()] - STEP / 2, Y[sl[0].start + jj.max()] + STEP / 2
            zl = np.nanmin(zlo[sl][m]) if np.isfinite(zlo[sl][m]).any() else None
            zh = np.nanmax(zhi[sl][m]) if np.isfinite(zhi[sl][m]).any() else None
            reg = {"kind": kind, "volume_mm3": round(vol, 3), "columns": int(m.sum()),
                   "bbox_abs": [round(xa, 2), round(xb, 2), round(-Yb, 2), round(-Ya, 2)],
                   "z_range": [None if zl is None else round(float(zl), 3), None if zh is None else round(float(zh), 3)],
                   "max_length_mm": round(float(arr[sl][m].max()), 3)}
            reg["explained_by"] = explain(G, reg, studs)
            regions.append(reg)
    regions.sort(key=lambda r: -r["volume_mm3"])
    tiny = [r for r in regions if r["volume_mm3"] < 0.05]
    big = [r for r in regions if r["volume_mm3"] >= 0.05]
    by = {}
    for r in big:
        k = r["explained_by"].split(":")[0].split(" (")[0]
        by.setdefault(k, {"GF only": 0.0, "v2 only": 0.0, "regions": 0})
        by[k][r["kind"]] += r["volume_mm3"]
        by[k]["regions"] += 1
    out = {"slab_z_min": zs, "grid_mm": STEP, "columns": int(len(X) * len(Y)), "exact_columns": len(cand),
           "gf_only_mm3": round(float(dg.sum() * cell), 2), "v2_only_mm3": round(float(dv.sum() * cell), 2),
           "regions": big, "tiny_regions": len(tiny), "tiny_regions_mm3": round(sum(r["volume_mm3"] for r in tiny), 3),
           "tiny_examples": tiny[:10],
           "by_explanation": {k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in by.items()},
           "unexplained_mm3": round(sum(r["volume_mm3"] for r in big if r["explained_by"].startswith(("UNEXPLAINED", "corner-cell"))), 3),
           "method": "vertical rays, mesh pass + exact OCC pass on differing columns (OCC booleans fail on these two models)"}
    # slab volumes (exact, OCC common with a box)
    for tag, s in (("gf", gf), ("v2", v2)):
        sl = C.common_shape(s, C.box(-50, 260, -220, 50, zs, 20))
        out[tag + "_slab_volume_mm3"] = round(sum(x.Volume() for x in sl.Solids()), 2)
    out["balance_check_mm3"] = round((out["gf_only_mm3"] - out["v2_only_mm3"]) - (out["gf_slab_volume_mm3"] - out["v2_slab_volume_mm3"]), 2)
    log("    GF-only %.1f mm3, v2-only %.1f mm3 (balance vs exact slab volumes %.2f); regions %d (+%d tiny)" % (
        out["gf_only_mm3"], out["v2_only_mm3"], out["balance_check_mm3"], len(big), len(tiny)))
    # wall probes: how far each wall face moved (exact)
    walls = []
    for edge, along in (("top", 80.0), ("left", 60.0), ("right", 60.0), ("bottom-left cell, x 25", 25.0)):
        for z in (-4.8, -1.0, -0.01):
            row = {"edge": edge, "along": along, "z": z}
            for tag, PP in (("gf", Pg), ("v2", Pv)):
                if edge.startswith(("top", "bottom")):
                    iv = PP.y_intervals(along, z)
                    pick = [(a, b) for a, b in iv if (a < 20 if edge == "top" else 117 < a < 125) and b - a < 6.5]
                else:
                    iv = PP.x_intervals(along, z)
                    pick = [(a, b) for a, b in iv if (a < 24 if edge == "left" else b > 181) and b - a < 6.5]
                row[tag] = [(round(a, 4), round(b, 4)) for a, b in pick]
            if row["gf"] and row["v2"]:
                g, v = row["gf"][0], row["v2"][0]
                row["face_shifts_lo_hi"] = (round(g[0] - v[0], 4), round(g[1] - v[1], 4))
                row["thickness_gf_v2"] = (round(g[1] - g[0], 4), round(v[1] - v[0], 4))
            walls.append(row)
    out["wall_probes"] = walls
    out["ok"] = out["unexplained_mm3"] < 0.5
    out["seconds"] = round(time.time() - t0, 1)
    return out


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    r = run(ctx)
    C.dump(r, ctx.out("carry_only.json"))
    for s in r["regions"]:
        print(s)
    print(r["by_explanation"])
    for w in r["wall_probes"]:
        print(w)
