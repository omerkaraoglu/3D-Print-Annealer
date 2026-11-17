"""B. Mouldability of the frame STEP, pull along Z, two-plate tool (no slides, no lifters).

  <venv>\\Scripts\\python.exe mould_check.py [--frame f.step] [--params p.json]

1. SLIVERS (owner's rule): 2A/P < 0.3 mm or area < 0.5 mm2; split into design faces and fillet blend patches.
2. DRAFT: every face classified against the pull Z; flagged = planes within 0.25 deg of Z, cylinders with their
   axis on Z, cones < 0.25 deg, other surfaces whose sampled normals give < 0.25 deg; flagged faces identified.
3. UNDERCUT, proven by rays (no assumption):
   a) column test - vertical rays on a 0.25 mm grid over the whole part (VTK OBB tree on a 0.005 mm mesh); every
      ray must cross the material in ONE interval (two intervals = air trapped between material above and below =
      a feature no single-pull two-plate tool can form);
   b) face visibility - points on every face (mesh triangle centroids, offset 0.02 mm along the outward normal)
      must see free space along the pull direction their normal faces (+Z faces towards +Z = moving half B,
      -Z faces towards -Z = fixed half A; vertical faces: either). Occluded points are undercuts.
   c) parting: the A/B split that (b) produces is compared with the stated parting line (flange outline in the
      flange-front plane): the flange outer edge must be visible from +Z (B) and every face in front of the
      flange-front plane from -Z (A).
4. THIN WALL / THIN GAP: plan sections at the lip, the seat ring and pads, the step wall + flange, the pips, the
   land plate, the tubes and tube ribs, the corner cells, the shelf and the PCB plane, plus vertical sections
   (mid-top, mid-side, chin, F1 slot axis); rasterised at 0.05 mm; local thickness = largest inscribed disc (v2
   method). Walls < 1.0 mm are listed (the lip is 1.0 by design); gaps < 1.0 mm are knife-edge tool steel.
5. THICK SECTIONS: the solid is voxelised at 0.2 mm (vtkPolyDataToImageStencil) and the 3D distance transform
   gives the largest inscribed sphere at every point; spots thicker than 2 x the 2.5 nominal wall (sphere dia
   > 5.0) are sink / void risks, listed with coordinates; plan map PNG (max sphere dia over Z).
Output: the "mould" block of out/cadcheck.json, renders/verify/Thickness_map.png
"""
import math
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepTools import BRepTools

import vcommon as C

SLIVER_W, SLIVER_A = 0.3, 0.5
BLEND_R = 1.0
BLEND_BBOX = 1.5
DRAFT_MIN = 0.25
THIN_MIN = 1.0
RES = 0.05
COMP_AREA, COMP_EXT = 0.10, 1.0
SLOT_FILL = 0.6
PROBE_SHIFT = 0.013
THICK_VOX = 0.2
THICK_LIMIT = 5.0           # 2 x 2.5 nominal wall


# --------------------------------------------------------------------------------------- 1. slivers
def blend_class(f):
    ad = BRepAdaptor_Surface(f.wrapped)
    gt = f.geomType()
    bb = f.BoundingBox()
    big = max(bb.xlen, bb.ylen, bb.zlen)
    if gt == "SPHERE" and ad.Sphere().Radius() <= BLEND_R:
        return "fillet blend: sphere r %.2f" % ad.Sphere().Radius()
    if gt == "TORUS" and ad.Torus().MinorRadius() <= BLEND_R:
        return "fillet blend: torus r %.2f" % ad.Torus().MinorRadius()
    if gt in ("BSPLINE", "CYLINDER", "BEZIER") and big <= BLEND_BBOX:
        return "fillet blend: %s patch %.2f mm" % (gt.lower(), big)
    return "design face"


def slivers(shape):
    bad, narrow = [], []
    for f in shape.Faces():
        a = f.Area()
        p = sum(e.Length() for e in f.Edges())
        w = 2 * a / p if p > 0 else 0
        c = f.Center()
        if a < SLIVER_A or w < SLIVER_W:
            bad.append({"type": f.geomType(), "area": round(a, 4), "2A/P": round(w, 4),
                        "at_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)], "class": blend_class(f)})
        if f.geomType() == "PLANE":
            bb = f.BoundingBox()
            ext = sorted([bb.xlen, bb.ylen, bb.zlen])
            if ext[1] < SLIVER_W:
                narrow.append({"area": round(a, 3), "minor_extent": round(ext[1], 3), "2A/P": round(w, 3),
                               "at_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)]})
    design = [b for b in bad if b["class"] == "design face"]
    by_class = {}
    for b in bad:
        k = b["class"].split(":")[0] + (":" + b["class"].split(":")[1].split()[0] if ":" in b["class"] else "")
        by_class[k] = by_class.get(k, 0) + 1
    return {"faces": len(shape.Faces()), "rule": "2A/P < %.1f mm or area < %.1f mm2" % (SLIVER_W, SLIVER_A),
            "hits": len(bad), "design_face_slivers": design, "fillet_blend_slivers": len(bad) - len(design),
            "by_class": by_class, "all": bad, "planar_narrow_extent": narrow,
            "max_blend_area": max((b["area"] for b in bad if b["class"] != "design face"), default=0.0),
            "ok": not bad, "ok_excluding_fillet_blends": not design}


# --------------------------------------------------------------------------------------- 2. draft
def identify(G, x, y):
    for n in G.fast:
        fx, fy = G.fxy(n)
        if math.hypot(x - fx, y - fy) < 4.5:
            return "fastener " + n
    for n, (hx, hy) in G.HOLES.items():
        if math.hypot(x - hx, y - hy) < 0.2:
            return "PCB hole " + n
    for n, (px, py) in G.pips.items():
        if math.hypot(x - px, y - py) < 0.2:
            return n
    return ""


def sampled_draft(face, n=7):
    ad = BRepAdaptor_Surface(face.wrapped)
    u0, u1, v0, v1 = BRepTools.UVBounds_s(face.wrapped)
    best = 90.0
    for i in range(n):
        for j in range(n):
            u = u0 + (u1 - u0) * (i + 0.5) / n
            v = v0 + (v1 - v0) * (j + 0.5) / n
            pr = BRepLProp_SLProps(ad, u, v, 1, 1e-6)
            if not pr.IsNormalDefined():
                continue
            nz = abs(pr.Normal().Z())
            if nz > 0.9999:
                continue
            best = min(best, math.degrees(math.asin(min(1.0, nz))))
    return best


def draft(shape, G):
    counts, flagged, cones, planes = {}, [], {}, {}
    per_face = []           # (face index, draft deg or None = horizontal / blend, class) for the draft map
    for fi_, f in enumerate(shape.Faces()):
        gt = f.geomType()
        c = f.Center()
        bb = f.BoundingBox()
        base = {"type": gt, "area": round(f.Area(), 3), "at_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)],
                "z": [round(bb.zmin, 3), round(bb.zmax, 3)]}
        nflag = len(flagged)
        dval = None
        if gt == "PLANE":
            nz = abs(f.normalAt().z)
            if nz > 0.9999:
                k = "plane horizontal"
            else:
                a = math.degrees(math.asin(min(1.0, nz)))
                dval = a
                planes[round(a, 2)] = planes.get(round(a, 2), 0) + 1
                k = "plane drafted"
                if a < DRAFT_MIN:
                    k = "plane parallel to Z"
                    flagged.append(dict(base, why="planar wall without draft", draft_deg=round(a, 3),
                                        feature=identify(G, c.x, -c.y)))
        elif gt in ("CYLINDER", "CONE"):
            ax = C.axis_z_feature(f)
            if ax:
                kind, cx, cy, r, z0, z1, semi, _ = ax
                who = identify(G, cx, -cy)
                if gt == "CYLINDER":
                    k = "cylinder axis Z"
                    dval = 0.0
                    flagged.append(dict(base, why="cylinder parallel to the pull (no draft)", r=round(r, 3),
                                        axis_abs=[round(cx, 3), round(-cy, 3)], feature=who))
                else:
                    k = "cone axis Z"
                    dval = abs(semi)
                    cones[round(abs(semi), 2)] = cones.get(round(abs(semi), 2), 0) + 1
                    if abs(semi) < DRAFT_MIN:
                        flagged.append(dict(base, why="cone < %.2f deg" % DRAFT_MIN, semi_deg=round(semi, 3),
                                            axis_abs=[round(cx, 3), round(-cy, 3)], feature=who))
            else:
                a = sampled_draft(f)
                dval = a
                k = "%s, axis not Z (fillet / round)" % gt.lower()
                if a < DRAFT_MIN:
                    flagged.append(dict(base, why="%s (axis not Z), sampled draft %.2f deg" % (gt.lower(), a)))
        else:
            a = sampled_draft(f)
            dval = a
            k = gt.lower()
            if a < DRAFT_MIN and gt in ("SPHERE", "TORUS") and blend_class(f).startswith("fillet blend"):
                k = gt.lower() + " fillet blend (normals pass through vertical; not a draft error)"
                dval = None
            elif a < DRAFT_MIN:
                flagged.append(dict(base, why="%s, sampled draft %.2f deg" % (gt.lower(), a), draft_deg=round(a, 3)))
        counts[k] = counts.get(k, 0) + 1
        per_face.append((fi_, None if dval is None else round(float(dval), 3), k, len(flagged) > nflag))
    by_why = {}
    for fl in flagged:
        key = fl["why"] + (" - " + fl["feature"] if fl.get("feature") else "")
        by_why[key] = by_why.get(key, 0) + 1
    return {"counts": counts, "cone_semi_angles_deg": dict(sorted(cones.items())),
            "drafted_plane_angles_deg": dict(sorted(planes.items())), "flagged": flagged, "flagged_summary": by_why,
            "draft_min_deg": DRAFT_MIN, "ok": not flagged, "per_face": per_face}


# --------------------------------------------------------------------------------------- 3. undercut (rays)
def vtk_mesh(shape, tol=0.005, ang=0.1):
    import vtk
    vtk.vtkObject.GlobalWarningDisplayOff()        # OBB-tree Jacobi warnings on degenerate cells: harmless
    try:
        vtk.vtkLogger.SetStderrVerbosity(vtk.vtkLogger.VERBOSITY_ERROR)
    except Exception:
        pass
    pd = shape.toVtkPolyData(tol, ang, True)
    tri = vtk.vtkTriangleFilter(); tri.SetInputData(pd); tri.Update()
    obb = vtk.vtkOBBTree(); obb.SetDataSet(tri.GetOutput()); obb.BuildLocator()
    return tri.GetOutput(), obb


def column_test(shape, step=0.25):
    """vertical rays on a grid: number of material intervals per column"""
    import vtk
    pd, obb = vtk_mesh(shape)
    x0, x1, Y0, Y1, z0, z1 = C.optimal_bbox(shape)
    xs = np.arange(x0 + step / 2, x1, step)
    Ys = np.arange(Y0 + step / 2, Y1, step)
    pts = vtk.vtkPoints()
    ids = vtk.vtkIdList()
    multi = []
    n_rays = 0
    za, zb = z0 - 5, z1 + 5
    for X in xs:
        for Y in Ys:
            n_rays += 1
            pts.Reset()
            r = obb.IntersectWithLine((X, Y, za), (X, Y, zb), pts, None)
            n = pts.GetNumberOfPoints()
            if n < 3:
                continue
            zz = sorted(pts.GetPoint(i)[2] for i in range(n))
            u = [zz[0]]
            for z in zz[1:]:
                if z - u[-1] > 1e-4:
                    u.append(z)
            if len(u) >= 3:
                # classify the spans by midpoint with the OCC solid (exact) to count material intervals
                multi.append((X, Y, u))
    # exact recheck of the candidate columns with the OCC probe
    P = C.Probe(shape)
    bad = []
    for X, Y, u in multi:
        iv = P.z_intervals(X, -Y)
        iv = [(a, b) for a, b in iv if b - a > 1e-4]
        if len(iv) >= 2:
            gaps = [(iv[k][1], iv[k + 1][0]) for k in range(len(iv) - 1)]
            bad.append({"x": round(X, 3), "y_abs": round(-Y, 3), "intervals": [(round(a, 4), round(b, 4)) for a, b in iv],
                        "trapped_air_z": [(round(a, 4), round(b, 4)) for a, b in gaps]})
    return {"grid_mm": step, "rays": n_rays, "candidates_mesh": len(multi), "multi_interval_columns": bad,
            "clusters": cluster_xy(bad), "ok": not bad}


def cluster_xy(rows, d=2.0):
    cl = []
    for r in rows:
        for c in cl:
            if math.hypot(c["x"] - r["x"], c["y_abs"] - r["y_abs"]) < d + c["r"]:
                c["n"] += 1
                c["pts"].append((r["x"], r["y_abs"]))
                xs = [p[0] for p in c["pts"]]; ys = [p[1] for p in c["pts"]]
                c["x"], c["y_abs"] = float(np.mean(xs)), float(np.mean(ys))
                c["r"] = float(max(np.ptp(xs), np.ptp(ys)) / 2)
                break
        else:
            cl.append({"x": r["x"], "y_abs": r["y_abs"], "n": 1, "r": 0.0, "pts": [(r["x"], r["y_abs"])],
                       "example": r})
    for c in cl:
        c["bbox_abs"] = [round(min(p[0] for p in c["pts"]), 2), round(max(p[0] for p in c["pts"]), 2),
                         round(min(p[1] for p in c["pts"]), 2), round(max(p[1] for p in c["pts"]), 2)]
        del c["pts"]
    return cl


def visibility(shape, G, max_per_face=60, off=0.02):
    """per face: sample points (mesh triangle centroids) must see free space along the pull direction their
    normal faces; vertical faces need one free direction"""
    import vtk
    pd_all, obb = vtk_mesh(shape)
    probe = C.Probe(shape)
    x0, x1, Y0, Y1, z0, z1 = C.optimal_bbox(shape)
    pts = vtk.vtkPoints()
    rows = []
    split_faces = []
    face_side = []
    sideA = sideB = both = 0
    zff = G.L["Z_FLANGE_FRONT"]
    parting_viol = []
    for fi, f in enumerate(shape.Faces()):
        vs, ts = f.tessellate(0.01, 0.2)
        if not ts:
            continue
        V = np.array([[v.x, v.y, v.z] for v in vs])
        T = np.array(ts)
        cen = V[T].mean(axis=1)
        nrm = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        ln = np.linalg.norm(nrm, axis=1)
        keep = ln > 1e-12
        cen, nrm, ln = cen[keep], nrm[keep], ln[keep]
        nrm = nrm / ln[:, None]
        if len(cen) > max_per_face:
            sel = np.linspace(0, len(cen) - 1, max_per_face).astype(int)
            cen, nrm = cen[sel], nrm[sel]
        occl, nvert, nA, nB = [], 0, 0, 0
        for p, n in zip(cen, nrm):
            # exact surface normal at the sample (mesh facet normals tilt on drafted cones and blends), then the
            # outward side decided by the exact solid classifier (face orientation not trusted)
            try:
                ne = f.normalAt(cq.Vector(*p))
                ne = np.array([ne.x, ne.y, ne.z])
                if np.linalg.norm(ne) > 0.5:
                    n = ne / np.linalg.norm(ne) * (1 if ne @ n >= 0 else -1)
            except Exception:
                pass
            # outward side: point-in-solid by the exact vertical line probe (transition parity; the OCC solid
            # classifier costs ~80 ms per call on this model)
            def inside(qq):
                iv = probe.intervals_fast((float(qq[0]), float(qq[1]), 0.0), (0.0, 0.0, 1.0), -1000.0, 1000.0)
                return any(a < qq[2] < b for a, b in iv)
            q = p + off * n
            if inside(q):
                n = -n
                q = p + off * n
                if inside(q):
                    continue            # sample in a sliver thinner than 2 x off: no outward side
            p = q - off * n
            dirs = []
            if n[2] > 2e-3:
                dirs = [+1]
            elif n[2] < -2e-3:
                dirs = [-1]
            else:
                dirs = [+1, -1]
                nvert += 1
            free = []
            for d in dirs:
                pts.Reset()
                end = (q[0], q[1], (z1 + 5) if d > 0 else (z0 - 5))
                obb.IntersectWithLine(tuple(q), end, pts, None)
                fr_ = pts.GetNumberOfPoints() == 0
                if not fr_:     # mesh says blocked: confirm on the exact B-rep (OCC line probe from q along the pull)
                    iv = probe.intervals_fast(tuple(q), (0.0, 0.0, float(d)), 1e-4, 60.0)
                    fr_ = not [(a, b) for a, b in iv if b - a > 1e-4]
                free.append(fr_)
            if not any(free):
                occl.append([round(p[0], 3), round(-p[1], 3), round(p[2], 3), round(float(n[2]), 4)])
            else:
                if n[2] < -1e-3 or (len(dirs) == 2 and free[1] and not free[0]):
                    nA += 1
                else:
                    nB += 1
        c = f.Center()
        side = "A (-Z)" if nA and not nB else ("B (+Z)" if nB and not nA else "A+B (split)")
        bb = f.BoundingBox()
        face_side.append((fi, side, nA, nB, len(occl)))
        if side == "A (-Z)":
            sideA += 1
        elif side == "B (+Z)":
            sideB += 1
        else:
            both += 1
            split_faces.append({"face": fi, "type": f.geomType(), "area": round(f.Area(), 3),
                                "centre_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)],
                                "z": [round(bb.zmin, 3), round(bb.zmax, 3)], "A_pts": nA, "B_pts": nB})
        if occl:
            rows.append({"face": fi, "type": f.geomType(), "area": round(f.Area(), 3),
                         "centre_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)], "z": [round(bb.zmin, 3), round(bb.zmax, 3)],
                         "occluded_points": len(occl), "of": len(cen), "examples": occl[:4]})
        # parting consistency: faces wholly in front of the flange-front plane must be A-side
        if bb.zmax < zff - 1e-3 and nB:
            parting_viol.append({"face": fi, "why": "face in front of the flange-front plane formed from +Z",
                                 "centre_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)]})
    # the flange outer edge faces: lie at the flange outline, between flange front and back -> must be B-side
    return {"faces_A": sideA, "faces_B": sideB, "faces_split": both, "split_faces": split_faces, "occluded_faces": rows,
            "parting_violations": parting_viol, "offset_mm": off, "ok": not rows and not parting_viol, "face_side": face_side}


def flange_edge_side(shape, G, P):
    """the flange outline (parting line) must be released by B: its edge face visible from +Z, i.e. the flange is
    widest at the flange-front plane. Checked by horizontal probes at 3 heights on the 4 sides."""
    L = G.L
    out = []
    for edge, along in (("top", 60.0), ("bottom", 60.0), ("left", 40.0), ("right", 40.0)):
        ss = []
        for z in (L["Z_FLANGE_FRONT"] + 0.05, (L["Z_FLANGE_FRONT"] + L["Z_FLANGE_BACK"]) / 2, L["Z_FLANGE_BACK"] - 0.05):
            iv = P.s_boundaries(edge, along, z, -40, 40, G)
            ss.append(max(b for a, b in iv))
        out.append({"edge": edge, "s_front_mid_back": [round(s, 4) for s in ss], "widest_at_front": ss[0] > ss[1] > ss[2]})
    return {"rows": out, "ok": all(r["widest_at_front"] for r in out)}


# --------------------------------------------------------------------------------------- 4. thin walls / gaps
def raster_loops(loop_list, res=RES, pad=2.0):
    from PIL import Image, ImageDraw
    allp = np.vstack([l for loops in loop_list for l in loops])
    x0, y0 = allp[:, 0].min() - pad, allp[:, 1].min() - pad
    w = int(math.ceil((allp[:, 0].max() + pad - x0) / res))
    h = int(math.ceil((allp[:, 1].max() + pad - y0) / res))
    img = Image.new("1", (w, h), 0)
    dr = ImageDraw.Draw(img)
    for loops in loop_list:
        dr.polygon([((x - x0) / res, (y - y0) / res) for x, y in loops[0]], fill=1)
        for hole in loops[1:]:
            dr.polygon([((x - x0) / res, (y - y0) / res) for x, y in hole], fill=0)
    return np.array(img, dtype=bool), x0, y0


def narrow(region, r):
    from scipy import ndimage
    edt = ndimage.distance_transform_edt(region, sampling=RES)
    core = edt > r
    opened = ndimage.distance_transform_edt(~core, sampling=RES) <= r
    return region & ~opened, edt


def components(mask, edt, x0, y0, kind, coord):
    from scipy import ndimage
    lab, n = ndimage.label(mask)
    out, small = [], 0
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        m = lab[sl] == i
        area = m.sum() * RES * RES
        ext = math.hypot((sl[0].stop - sl[0].start), (sl[1].stop - sl[1].start)) * RES
        if area < COMP_AREA or ext < COMP_EXT:
            small += 1
            continue
        width = 2 * edt[sl][m].max()
        rows, cols = np.nonzero(m)
        cx, cy = x0 + (cols.mean() + sl[1].start + 0.5) * RES, y0 + (rows.mean() + sl[0].start + 0.5) * RES
        fill = area / max(ext * width, 1e-9)
        is_slot = fill >= SLOT_FILL and ext >= 2 * width
        cls = ("%s thinner than %.1f" % ("wall" if kind == "wall" else "gap (knife-edge steel)", THIN_MIN) if is_slot else
               "V-notch / sharp %s corner (wedge to 0)" % ("convex" if kind == "wall" else "re-entrant"))
        out.append({"at": [round(cx, 2), round(cy, 2)], "coord": coord, "width_max": round(width, 3), "length": round(ext, 2),
                    "area_mm2": round(area, 3), "fill_ratio": round(fill, 2), "class": cls})
    return sorted(out, key=lambda r: r["width_max"]), small


def s_glass(G, x, y):
    """signed distance outward from the glass outline (rounded rectangle, R_glass)"""
    gx0, gx1, gy0, gy1, R = G.GLASS
    cx = min(max(x, gx0 + R), gx1 - R)
    cy = min(max(y, gy0 + R), gy1 - R)
    dx, dy = x - cx, y - cy
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        return -min(x - gx0, gx1 - x, y - gy0, gy1 - y)
    d = math.hypot(dx, dy)
    if (gx0 + R <= x <= gx1 - R) or (gy0 + R <= y <= gy1 - R):
        return max(gx0 - x, x - gx1, gy0 - y, y - gy1)
    return d - R


def classify_thin(G, plane, row):
    """name what a thin wall / gap is (lip by design, etc.)"""
    if plane["kind"] != "plan":
        return ""
    x, y = row["at"]
    s = s_glass(G, x, y)
    z = plane["z"]
    if z < G.L["Z_SHEET_BACK"] and 0.3 < s < 1.5 and row["class"].startswith("wall"):
        return "the lip (1.0 by design)"
    if G.h6 and z > -1.0 and 167.5 < x < 169.5 and 122 < y < 130 and row["class"].startswith("wall"):
        return "H6 tail wall (%.1f at Z_PCB by design, corner_cell_H6.h6_wall_min)" % float(G.h6.get("h6_wall_min", 1.1))
    return ""


def acute_corners(loop_list, max_deg=60.0, step=0.05, k=3):
    """sharp corners of a planar section: at every resampled boundary point the angle between the chords to the
    points 0.15 mm before and after it; below max_deg the corner is acute. The side inside the angle decides what is
    sharp: material -> a sharp plastic edge; air -> a knife edge of tool steel (the tool fills the air)."""
    from matplotlib.path import Path as MPath
    out = []
    for loops in loop_list:
        paths = [MPath(l) for l in loops]
        def inside(q):
            r = paths[0].contains_point(q)
            for h in paths[1:]:
                r = r and not h.contains_point(q)
            return r
        for l in loops:
            P = C.densify(l, step)
            if len(P) < 4 * k:
                continue
            a = np.roll(P, k, axis=0) - P
            b = np.roll(P, -k, axis=0) - P
            na, nb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
            ok = (na > 1e-9) & (nb > 1e-9)
            cosv = np.where(ok, np.einsum("ij,ij->i", a, b) / np.maximum(na * nb, 1e-12), -1.0)
            ang = np.degrees(np.arccos(np.clip(cosv, -1, 1)))
            idx = np.nonzero(ang < max_deg)[0]
            used = []
            for i in idx[np.argsort(ang[idx])]:
                if any(np.hypot(*(P[i] - P[j])) < 0.5 for j in used):
                    continue
                used.append(i)
                bis = a[i] / na[i] + b[i] / nb[i]
                bn = np.linalg.norm(bis)
                if bn < 1e-9:
                    continue
                q = P[i] + 0.02 * bis / bn
                side = "material" if inside(q) else "air"
                out.append({"at": [round(float(P[i][0]), 3), round(float(P[i][1]), 3)], "angle_deg": round(float(ang[i]), 1),
                            "inside_the_angle": side,
                            "meaning": "knife edge of tool steel" if side == "air" else "sharp plastic edge"})
    return out


def thin_probe(shape, G):
    L = G.L
    planes = [("lip", L["Z_GLASS_FRONT"] + 0.5), ("seat ring + pads", (L["Z_SHEET_BACK"] + L["Z_FLANGE_FRONT"]) / 2),
              ("flange + step wall", L["Z_FLANGE_FRONT"] + 1.0), ("pips", (L["Z_PIP_TOP"] + L["Z_LAND"]) / 2),
              ("land plate + flange", (L["Z_LAND"] + L["Z_FLANGE_BACK"]) / 2), ("tubes + tube ribs", L["Z_FLANGE_BACK"] + 1.0),
              ("tubes above the land plate", (L["Z_LANDPLATE_BACK"] + L["Z_TUBE_TOP"]) / 2), ("corner cells", -6.0),
              ("cells / pocket wall", -5.2), ("shelf + walls", -3.0), ("ribs below the PCB", -0.5), ("tail walls", 2.0)]
    if G.cb:      # GF-1.1 counterbores
        planes += [("F1-F4 counterbores in the pads", L["Z_SHEET_BACK"] + 0.8),
                   ("F1-F4 counterbore floor rounds", G.cb_floor_z("F1") - 0.15)]
        if G.cb_floor_z("F5") is not None:
            planes += [("F5-F8 counterbores", L["Z_FLANGE_FRONT"] + 0.5),
                       ("F5-F8 counterbore floor rounds", G.cb_floor_z("F5") - 0.15)]
    if G.gf2:     # GF-2.0 bridge, slot, rib, floor
        planes += [("bridge: land break / slot at the land", L["Z_LAND"] + 0.15),
                   ("bridge: pocket face above the break", L["Z_LAND"] + 0.6),
                   ("bridge: nose + rib roots", L["Z_LANDPLATE_BACK"] - 0.4),
                   ("tail-pocket floor + rib + cell walls", L.get("Z_FLOOR_LOW", L["Z_FLANGE_BACK"]) + 0.3),
                   ("rib + tail walls + bottom wall above the PCB plane", 1.0)]
    if G.core:    # GF-1.1 coring grooves
        zf = L["Z_TUBE_TOP"] - float(G.core["core_depth"])
        planes += [("groove floor rounds", zf + 0.2), ("grooves, mid depth", zf + 1.6), ("grooves near the tube top", L["Z_TUBE_TOP"] - 0.1)]
    horiz = sorted({round(f.BoundingBox().zmin, 4) for f in shape.Faces() if C.is_plane_z(f)})
    res = []
    for name, z in planes:
        zz = z + PROBE_SHIFT if any(abs(z - h) < 0.005 for h in horiz) else z
        sec = C.plane_section(shape, "z", zz)
        if sec is None:
            continue
        loops = [C.face_loops_abs(f, 0.002) for f in sec.Faces()]
        ev = _thin_eval(G, {"kind": "plan", "name": name, "z": round(zz, 3)}, loops, "x, y_abs")
        ev["acute_corners"] = acute_corners(loops)
        res.append(ev)
    # vertical sections: horizontal coordinate h and Z (rasterised as (h, z))
    gx0, gx1, gy0, gy1 = G.GLASS[:4]
    if G.gf2:
        vs = [("mid-top x 80", "x", 80.0, (-18, 26)), ("mid-side y 60", "y", 60.0, (-14, 30)),
              ("bridge, CTP compartment x 60 (bottom)", "x", 60.0, (110, 152)),
              ("divider rib x 79.92 (bottom)", "x", G.div_x, (110, 152)),
              ("bridge, TFT compartment x 103.85 (bottom)", "x", G.GC[0], (110, 152)),
              ("bridge, TFT wide part x 150 (bottom)", "x", 150.0, (110, 152)),
              ("bottom outside the tail span x 24 (H7 cell)", "x", 24.0, (110, 152)),
              ("right side y 100", "y", 100.0, (178, 222)), ("mid-side left y 66.83 (old F8 line)", "y", G.GC[1], (-14, 30)),
              ("H6 cell x 168.3", "x", 168.3, (115, 152)), ("across the rib y 135", "y", 135.0, (70, 90))]
    else:
        vs = [("mid-top x 80", "x", 80.0, (-12, 26)), ("mid-side y 60", "y", 60.0, (-9, 30)),
              ("chin x 103.85 (bottom)", "x", 103.85, (110, 177)), ("right side y 100", "y", 100.0, (178, 216)),
              ("F5 slot axis x 103.85 (top)", "x", 103.85, (-12, 26)), ("F8 slot axis y 82.085 (left)", "y", 82.085, (-9, 30)),
              ("F5 across the slot y 0.0 (top)", "y", 0.0, (90, 118)), ("H6 cell x 168.3", "x", 168.3, (115, 152))]
    for name, axis, val, lim in vs:
        sec = C.plane_section(shape, axis, -val if axis == "y" else val)
        if sec is None:
            continue
        loops = []
        for f in sec.Faces():
            ll = []
            for l in C.face_loops_3d(f, 0.002):
                h = -l[:, 1] if axis == "x" else l[:, 0]
                ll.append(np.column_stack([h, l[:, 2]]))
            if np.max(ll[0][:, 0]) < lim[0] or np.min(ll[0][:, 0]) > lim[1]:
                continue
            loops.append(ll)
        if loops:
            res.append(_thin_eval(G, {"kind": "vertical", "name": name, "z": None}, loops,
                                  "y_abs, Z" if axis == "x" else "x, Z"))
    # slot-axis section through F1
    x, y = G.fxy("F1")
    u = G.slot_axis("F1")
    sec = C.general_section(shape, (x, -y, 0.0), (-u[1], -u[0], 0.0))
    if sec is not None:
        loops = []
        for f in sec.Faces():
            ll = []
            for l in C.face_loops_3d(f, 0.002):
                t = (l[:, 0] - x) * u[0] + (-l[:, 1] - y) * u[1]
                ll.append(np.column_stack([t, l[:, 2]]))
            if np.min(ll[0][:, 0]) > 40:
                continue
            loops.append(ll)
        if loops:
            res.append(_thin_eval(G, {"kind": "vertical", "name": "F1 slot axis (t from F1 towards the glass centre)", "z": None},
                                  loops, "t, Z"))
    thin_walls = [dict(r, plane=p["name"]) for p in res for r in p["slots_or_walls"] if r["class"].startswith("wall")]
    thin_gaps = [dict(r, plane=p["name"]) for p in res for r in p["slots_or_walls"] if r["class"].startswith("gap")]
    undesigned = [r for r in thin_walls if not r.get("what")] + thin_gaps
    knives = [dict(c, plane=p["name"], z=p["z"]) for p in res for c in p.get("acute_corners", []) if c["inside_the_angle"] == "air"]
    sharp = [dict(c, plane=p["name"], z=p["z"]) for p in res for c in p.get("acute_corners", []) if c["inside_the_angle"] == "material"]
    w12 = [dict(r, plane=p["name"], z=p["z"]) for p in res for r in p.get("walls_lt_1p2", [])]
    return {"min_mm": THIN_MIN, "raster_mm": RES, "planes": res, "thin_walls": thin_walls, "thin_gaps": thin_gaps,
            "not_by_design": undesigned, "steel_knife_edges": knives, "sharp_plastic_edges": sharp,
            "acute_limit_deg": 60.0, "ok": not undesigned and not knives,
            "walls_lt_1p2": w12, "list_limit_mm": THIN_LIST}


THIN_LIST = 1.2            # GF-2.0 brief: list every wall < 1.2 with its location (INFO; the criterion stays < 1.0)


def _thin_eval(G, plane, loops, coord):
    mat, x0, y0 = raster_loops(loops)
    tw, edt_m = narrow(mat, THIN_MIN / 2)
    tg, edt_g = narrow(~mat, THIN_MIN / 2)
    walls, ws = components(tw, edt_m, x0, y0, "wall", coord)
    gaps, gs = components(tg, edt_g, x0, y0, "gap", coord)
    for r in walls + gaps:
        w = classify_thin(G, plane, r)
        if w:
            r["what"] = w
    tw12, edt12 = narrow(mat, THIN_LIST / 2)
    w12, _ = components(tw12, edt12, x0, y0, "wall", coord)
    w12 = [r for r in w12 if r["class"].startswith("wall")]
    for r in w12:
        w = classify_thin(G, plane, r)
        if w:
            r["what"] = w
    return dict(plane, material_mm2=round(mat.sum() * RES * RES, 1), thin_walls=walls, thin_gaps=gaps,
                slots_or_walls=[g for g in walls + gaps if not g["class"].startswith("V-notch")],
                v_notches=[g for g in walls + gaps if g["class"].startswith("V-notch")],
                walls_lt_1p2=w12, ignored_specks={"wall": ws, "gap": gs})


# --------------------------------------------------------------------------------------- 5. thick sections
def voxelise(shape, vox=THICK_VOX, pad=1.0):
    import vtk
    from vtk.util import numpy_support as ns
    pd = shape.toVtkPolyData(0.01, 0.1, True)
    tri = vtk.vtkTriangleFilter(); tri.SetInputData(pd); tri.Update()
    x0, x1, Y0, Y1, z0, z1 = C.optimal_bbox(shape)
    org = (x0 - pad, Y0 - pad, z0 - pad)
    dims = (int(math.ceil((x1 - x0 + 2 * pad) / vox)) + 1, int(math.ceil((Y1 - Y0 + 2 * pad) / vox)) + 1,
            int(math.ceil((z1 - z0 + 2 * pad) / vox)) + 1)
    img = vtk.vtkImageData()
    img.SetOrigin(*org); img.SetSpacing(vox, vox, vox); img.SetDimensions(*dims)
    img.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
    ns.vtk_to_numpy(img.GetPointData().GetScalars())[:] = 1
    st = vtk.vtkPolyDataToImageStencil()
    st.SetInputData(tri.GetOutput())
    st.SetOutputOrigin(*org); st.SetOutputSpacing(vox, vox, vox); st.SetOutputWholeExtent(img.GetExtent())
    st.Update()
    cs = vtk.vtkImageStencil(); cs.SetInputData(img); cs.SetStencilConnection(st.GetOutputPort())
    cs.ReverseStencilOff(); cs.SetBackgroundValue(0); cs.Update()
    arr = ns.vtk_to_numpy(cs.GetOutput().GetPointData().GetScalars()).reshape(dims[2], dims[1], dims[0])
    return arr.astype(bool), org, vox      # [z, y, x]


def thick_sections(shape, G, imgdir, vox=THICK_VOX, limit=THICK_LIMIT):
    from scipy import ndimage
    vol, org, vox = voxelise(shape, vox)
    nz, ny, nx = vol.shape
    edt = np.zeros(vol.shape, np.float32)
    tile, ov = 300, 40              # x tiles with overlap (memory)
    for i0 in range(0, nx, tile):
        a, b = max(0, i0 - ov), min(nx, i0 + tile + ov)
        e = ndimage.distance_transform_edt(vol[:, :, a:b], sampling=vox).astype(np.float32)
        edt[:, :, i0:min(nx, i0 + tile)] = e[:, :, i0 - a:i0 - a + min(tile, nx - i0)]
    # local thickness (inscribed sphere dia) is 2 x the EDT maximum along the medial axis; spots = EDT maxima
    dia = 2 * edt
    vfrac = vol.sum() * vox ** 3
    # clusters of medial points thicker than the limit
    mx = ndimage.maximum_filter(edt, size=5)
    peaks = (edt == mx) & (dia > limit)
    lab, n = ndimage.label(ndimage.binary_dilation(dia > limit, iterations=1) & vol)
    spots = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        m = lab[sl] == i
        sub = np.where(m, dia[sl], 0)
        k = np.unravel_index(np.argmax(sub), sub.shape)
        zi, yi, xi = k[0] + sl[0].start, k[1] + sl[1].start, k[2] + sl[2].start
        X, Y, Z = org[0] + xi * vox, org[1] + yi * vox, org[2] + zi * vox
        spots.append({"max_sphere_dia": round(float(dia[zi, yi, xi]), 2), "at_abs": [round(float(X), 2), round(float(-Y), 2), round(float(Z), 2)],
                      "extent_abs": [round(org[0] + sl[2].start * vox, 1), round(org[0] + sl[2].stop * vox, 1),
                                     round(-(org[1] + sl[1].stop * vox), 1), round(-(org[1] + sl[1].start * vox), 1),
                                     round(org[2] + sl[0].start * vox, 1), round(org[2] + sl[0].stop * vox, 1)],
                      "voxels": int(m.sum())})
    spots.sort(key=lambda s: -s["max_sphere_dia"])
    for s in spots:
        s["what"] = name_spot(G, s["at_abs"])
    # top local maxima regardless of the limit (separated by >= 4 mm), for the record
    cand = np.argwhere(peaks | ((edt == mx) & (dia > 3.0)))
    vals = dia[tuple(cand.T)] if len(cand) else np.array([])
    order = np.argsort(-vals)
    top = []
    for k in order:
        zi, yi, xi = cand[k]
        X, Y, Z = org[0] + xi * vox, org[1] + yi * vox, org[2] + zi * vox
        if any(math.hypot(X - t["_X"], Y - t["_Y"]) < 4.0 for t in top):
            continue
        top.append({"_X": X, "_Y": Y, "max_sphere_dia": round(float(vals[k]), 2), "at_abs": [round(float(X), 2), round(float(-Y), 2), round(float(Z), 2)],
                    "what": name_spot(G, [X, -Y, Z])})
        if len(top) >= 12:
            break
    for t in top:
        del t["_X"], t["_Y"]
    # plan map: max sphere dia over Z
    pm = dia.max(axis=0)          # [y, x] (model Y up)
    path = None
    if imgdir:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(15, 12.5))
        # pm row 0 = model Y min = abs y max; flip so row 0 = abs y min, drawn at the top (y abs grows downwards)
        y_abs_min, y_abs_max = -(org[1] + ny * vox), -org[1]
        ext = (org[0], org[0] + nx * vox, y_abs_max, y_abs_min)          # left, right, bottom, top
        im = ax.imshow(np.where(pm > 0, pm, np.nan)[::-1, :], extent=ext, origin="upper", cmap="turbo", vmin=0, vmax=7)
        cb = fig.colorbar(im, ax=ax, shrink=0.7); cb.set_label("largest inscribed sphere dia through the thickness, mm")
        for s in (spots if spots else top)[:12]:
            ax.plot(s["at_abs"][0], s["at_abs"][1], "wo", ms=9, mec="k")
            ax.annotate("%.1f" % s["max_sphere_dia"], (s["at_abs"][0], s["at_abs"][1]), xytext=(6, 6),
                        textcoords="offset points", fontsize=10, color="k",
                        bbox=dict(boxstyle="round,pad=0.15", fc="w", ec="none", alpha=0.8))
        ax.set_xlabel("x abs (mm)"); ax.set_ylabel("y abs (mm, down)")
        ax.set_title("Glass-front frame - wall thickness map (voxel %.1f mm, 3D distance transform): max inscribed sphere "
                     "dia over Z\nnominal wall 2.5; > %.1f (2 x nominal) = sink / void risk (white dots: %s)" % (
                         vox, limit, "spots over the limit" if spots else "largest local values, none over the limit"),
                     fontsize=12)
        ax.set_aspect("equal")
        path = os.path.join(imgdir, "Thickness_map_%s.png" % str(G.revision).split(" ")[0])
        fig.savefig(path, dpi=110, bbox_inches="tight")
        plt.close(fig)
    return {"voxel_mm": vox, "limit_dia_mm": limit, "voxel_volume_mm3": round(float(vfrac), 1),
            "max_sphere_dia": round(float(dia.max()), 2), "spots_over_limit": spots, "top_spots": top, "map_png": path,
            "ok": not spots,
            "method": "VTK stencil voxelisation (%.1f mm) + scipy 3D EDT; sphere dia = 2 x EDT (+-%.1f mm)" % (vox, vox)}


def name_spot(G, p):
    x, y, z = p
    for n in G.fast:
        fx, fy = G.fxy(n)
        if math.hypot(x - fx, y - fy) < 10.5:
            return "fastener %s (%s + flange + tube)" % (n, "pad" if n in ("F1", "F2", "F3", "F4") else "no pad")
    for n, (hx, hy) in G.HOLES.items():
        if math.hypot(x - hx, y - hy) < 5:
            return "PCB boss " + n
    gx0, gx1, gy0, gy1 = G.GLASS[:4]
    if G.gf2 and G.TAIL[0] < x < G.TAIL[1]:
        if abs(x - G.div_x) < 3 and y > G.BRIDGE[2]:
            return "divider rib (y %.1f)" % y
        if G.BRIDGE[2] <= y <= G.BRIDGE[3] + 0.6:
            return "bridge: land plate / step wall / flange plate (y %.1f)" % y
        if y > G.TAIL[3] - 0.6:
            return "bottom wall (y %.1f)" % y
        if y > G.BRIDGE[3]:
            return "tail-pocket floor = flange plate (y %.1f)" % y
    s = max(gx0 - x, x - gx1, gy0 - y, y - gy1)
    if -1 < s < 4:
        return "step wall / flange / land-plate junction (s %.1f)" % s
    if y > 119 and (x < 40 or x > 167):
        return "corner cell region"
    return "s %.1f" % s


# --------------------------------------------------------------------------------------- 5b. sharp inside corners
def sharp_inside_edges(shape, G, min_angle=5.0, eps=0.02):
    """every edge between two faces: at its midpoint, the outward normals n1, n2 and the in-face direction d1 of face 1 away
    from the edge (the sign of e x n1 chosen so that p + eps d1 lies on face 1). Concave (inside corner) when d1 . n2 > 0;
    sharp when the normals differ by more than min_angle deg (a tangent fillet edge has n1 = n2). Grouped by feature."""
    from OCP.BRep import BRep_Tool
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopoDS import TopoDS
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
    from OCP.gp import gp_Pnt
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    mp = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape.wrapped, TopAbs_EDGE, TopAbs_FACE, mp)
    out = []
    n_conc = 0
    for i in range(1, mp.Extent() + 1):
        e = TopoDS.Edge_s(mp.FindKey(i))
        fl = mp.FindFromIndex(i)
        if fl.Size() != 2:
            continue
        it = iter([cq.Face(TopoDS.Face_s(f)) for f in fl])
        f1, f2 = next(it), next(it)
        if f1.isSame(f2):
            continue                                   # seam edge
        c = BRepAdaptor_Curve(e)
        tm = 0.5 * (c.FirstParameter() + c.LastParameter())
        p = c.Value(tm)
        from OCP.gp import gp_Vec as _V
        v = _V(); pp = p
        c.D1(tm, pp, v)
        if v.Magnitude() < 1e-9:
            continue
        ev = np.array([v.X(), v.Y(), v.Z()]); ev /= np.linalg.norm(ev)
        P0 = np.array([p.X(), p.Y(), p.Z()])
        try:
            n1 = f1.normalAt(cq.Vector(*P0)); n2 = f2.normalAt(cq.Vector(*P0))
        except Exception:
            continue
        n1 = np.array([n1.x, n1.y, n1.z]); n2 = np.array([n2.x, n2.y, n2.z])
        ang = math.degrees(math.acos(max(-1.0, min(1.0, float(n1 @ n2)))))
        if ang < min_angle:
            continue
        d1 = np.cross(ev, n1); d1 /= np.linalg.norm(d1)
        def dface(q):
            vx = BRepBuilderAPI_MakeVertex(gp_Pnt(*q)).Vertex()
            dd = BRepExtrema_DistShapeShape(vx, f1.wrapped); dd.Perform()
            return dd.Value()
        if dface(P0 + eps * d1) > dface(P0 - eps * d1):
            d1 = -d1
        if float(d1 @ n2) <= 1e-3:
            continue                                   # convex edge
        n_conc += 1
        x, y, z = P0[0], -P0[1], P0[2]
        L = BRepAdaptor_Curve(e)
        out.append({"at_abs": [round(x, 2), round(y, 2), round(z, 2)], "angle_between_normals_deg": round(ang, 1),
                    "faces": [f1.geomType(), f2.geomType()], "length_mm": round(cq.Edge(e).Length(), 3), "what": _name_edge(G, x, y, z)})
    groups = {}
    for r in out:
        g = groups.setdefault(r["what"], {"edges": 0, "length_mm": 0.0, "example": r["at_abs"]})
        g["edges"] += 1
        g["length_mm"] = round(g["length_mm"] + r["length_mm"], 2)
    return {"sharp_concave_edges": len(out), "groups": groups, "edges": out, "min_angle_deg": min_angle,
            "method": "edge midpoint normals + in-face direction (BRepExtrema), concave if d1.n2 > 0, sharp if the normals differ > %.0f deg" % min_angle}


def _name_edge(G, x, y, z):
    L = G.L
    for n, (px, py) in G.pips.items():
        if math.hypot(x - px, y - py) < 1.0:
            return "pip roots on the land"
    for n in G.fast:
        fx, fy = G.fxy(n)
        r = math.hypot(x - fx, y - fy)
        if r < 10.5:
            if abs(z - L["Z_FLANGE_FRONT"]) < 0.02:
                return "corner-pad roots on the flange front (F1-F4)"
            if G.cb and abs(z - G.cb_floor_z(n)) < 0.35:
                return "counterbore floor / slot edge (F1-F4)"
            return "fastener %s (tube / groove / slot)" % n
    for n, (hx, hy) in G.HOLES.items():
        if math.hypot(x - hx, y - hy) < 4.5:
            return "PCB boss %s (pilot / relief floors)" % n
    if abs(z - L["Z_FLANGE_FRONT"]) < 0.02:
        return "seat-ring / step-wall root on the flange front"
    if abs(z - L["Z_SHELF_BACK"]) < 0.02 or abs(z - L["Z_SEAT"]) < 0.02:
        return "shelf roots (Z_SEAT / Z_SHELF_BACK)"
    if abs(z - L["Z_LAND"]) < 0.02:
        return "land roots (Z_LAND)"
    if G.gf2 and G.TAIL[0] - 1 < x < G.TAIL[1] + 1 and y > 118.5:
        return "tail pocket / bend-gap slot / bridge (y %.1f, Z %.1f)" % (y, z)
    return "other (x %.0f, y %.0f, Z %.1f)" % (x, y, z)


# --------------------------------------------------------------------------------------- 6. GF-2.0 bridge / bend-gap slot
def bridge_mould(shape, G, vis, P):
    """GF-2.0: which tool half forms each face of the bend-gap slot and the bridge (from the visibility test), the A/B
    shut-off the slot needs (measured end points, steel angles of three shut-off options), and the bridge's material
    paths (section areas, member thicknesses)."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    L = G.L
    T1 = math.tan(math.radians(1.0))
    side = {fi: (s, a, b, o) for fi, s, a, b, o in vis.get("face_side", [])}
    zl, zlb, zs = L["Z_LAND"], L["Z_LANDPLATE_BACK"], L["Z_SEAT"]
    y_pf, brk, nR = G.BRIDGE[2], float(G.land_break), float(G.bend_nose_R)
    x0s, x1s = G.SLOT[0], G.SLOT[1]
    faces = []
    for i, f in enumerate(shape.Faces()):
        bb = f.BoundingBox()
        ya0, ya1 = -bb.ymax, -bb.ymin
        if bb.xmax < x0s - 1.0 or bb.xmin > x1s + 1.0 or ya1 < 118.6 or ya0 > 124.2 or bb.zmin > 0.6 or bb.zmax < zl - 0.01:
            continue
        gt = f.geomType()
        c = f.Center()
        n = f.normalAt() if gt == "PLANE" else None
        what = "other"
        if gt == "CYLINDER" and abs(BRepAdaptor_Surface(f.wrapped).Cylinder().Radius() - nR) < 0.01:
            what = "nose R%.1f" % nR
        elif gt == "PLANE" and 0.6 < abs(n.z) < 0.8:
            what = "land break 0.3 x 45"
        elif gt == "PLANE" and n.y > 0.99 and abs(ya0 - y_pf) < 0.25:
            what = "bridge pocket face (+ rib front)"
        elif gt == "PLANE" and n.y < -0.99 and ya1 < 119.2:
            what = "shelf end = slot front face"
        elif gt == "PLANE" and abs(n.x) > 0.99:
            what = "slot end / tail-pocket side wall / rib side"
        elif gt == "PLANE" and abs(n.z) > 0.999:
            what = "horizontal (%s, Z %.2f)" % ("+Z" if n.z > 0 else "-Z", c.z)
        elif gt in ("CYLINDER", "BSPLINE", "TORUS", "SPHERE", "CONE"):
            what = "round / blend (%s)" % gt.lower()
        s, nA, nB, occ = side.get(i, ("?", 0, 0, 0))
        faces.append({"face": i, "what": what, "type": gt, "side": s, "A_pts": nA, "B_pts": nB, "occluded_pts": occ,
                      "area": round(f.Area(), 3), "centre_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)],
                      "bbox_abs": [round(bb.xmin, 2), round(bb.xmax, 2), round(ya0, 3), round(ya1, 3), round(bb.zmin, 3), round(bb.zmax, 3)]})
    by_what = {}
    for r in faces:
        k = r["what"].split(" (")[0] if r["what"].startswith(("horizontal", "round")) else r["what"]
        d = by_what.setdefault(k, {"faces": 0, "sides": {}, "occluded_pts": 0})
        d["faces"] += 1
        d["sides"][r["side"]] = d["sides"].get(r["side"], 0) + 1
        d["occluded_pts"] += r["occluded_pts"]
    # shut-off end points measured in the y-Z section (x 60 and x 130)
    shut = []
    for x in (60.0, 130.0):
        iv = P.y_intervals(x, zl + brk + 0.002)
        y_pb = next((a for a, b in iv if 120.5 < a < 124.0), None)            # chamfer top = A/B parting on the bridge side
        iv = P.y_intervals(x, zs + 0.01)
        y_pf_front = next((b for a, b in iv if 117.0 < b < 120.0), None)      # shelf corner = A/B parting on the front side
        if y_pb is None or y_pf_front is None:
            continue
        z_pb = zl + brk
        run_, rise = y_pb - y_pf_front, zs - z_pb
        # straight shut-off PF-PB: B steel wedge at PB between the pocket face (up, 1 deg) and the shut-off line
        a_face = math.degrees(math.atan2(1.0, T1))                       # direction of the pocket face going +Z (from +y axis)
        a_shut = math.degrees(math.atan2(rise, -run_))                    # direction PB -> PF
        b_wedge_straight = a_shut - a_face
        a_chamfer = math.degrees(math.atan2(-brk, brk))                   # chamfer going down from PB to the land (-45 deg)
        shut.append({"x": x, "PB_chamfer_top_yZ": [round(y_pb, 4), round(z_pb, 4)], "PF_shelf_corner_yZ": [round(y_pf_front, 4), zs],
                     "rise_mm": round(rise, 3), "run_mm": round(run_, 3),
                     "max_shutoff_angle_from_pull_deg": round(math.degrees(math.atan2(run_, rise)), 1),
                     "option_straight_PF_PB": {"B_steel_wedge_at_PB_deg": round(b_wedge_straight, 1),
                                               "A_steel_at_PB_deg": round(360 + a_chamfer - a_shut, 1)},
                     "option_stepped (flat at the chamfer top, then along y %.2f up to Z_SEAT)" % y_pf_front: {
                         "B_steel_at_PB_deg": round(180.0 - a_face, 1), "A_steel_at_PB_deg": round(180.0 + a_chamfer, 1),
                         "A_ledge_mm": [round(run_, 3), round(brk, 3)], "telescopic_shutoff_height_mm": round(rise, 3)},
                     "option_flat_at_Z_LAND (GF-2.0 release cad_rules wording)": "the 45 deg break faces -Z: it would be an undercut for the B core "
                                                                   "and the B steel would end in a 45 deg knife edge along the slot"})
    # material paths of the bridge (section at x 60, 130 and the rib)
    secs = {}
    for x in (60.0, 130.0, float(G.div_x)):
        sec = C.plane_section(shape, "x", x)
        tot = br = 0.0
        if sec is not None:
            for f in sec.Faces():
                bb = f.BoundingBox()
                if -bb.ymax < 119.5 or -bb.ymin > 152:
                    continue
                tot += f.Area()
                cut = C.common_shape(f, C.box(x - 1, x + 1, -(G.TAIL[3] - 0.01), -(G.BRIDGE[2] - 0.5), -20, 10))
                br += sum(ff.Area() for ff in cut.Faces())
        secs["x %.2f" % x] = {"section_y_gt_119.5_mm2": round(tot, 2), "bridge_plus_flange_plate_to_y_147.7_mm2": round(br, 2)}
    members = {}
    for lab, x, y in (("land plate (bridge)", 60.0, 125.6), ("flange plate (pocket floor)", 60.0, 140.0), ("bottom wall", 60.0, 149.0)):
        iv = P.z_intervals(x, y)
        members[lab] = round(iv[0][1] - iv[0][0], 3) if iv else None
    iv = P.y_intervals(60.0, -11.0)
    members["step wall + land plate at Z -11.0 (y extent)"] = [(round(a, 3), round(b, 3)) for a, b in iv if b > 120][:2]
    occl_bridge = sum(r["occluded_pts"] for r in faces)
    return {"faces": faces, "by_feature": by_what, "shut_off": shut, "sections": secs, "member_thickness_mm": members,
            "occluded_points_in_zone": occl_bridge,
            "feed_note": "the bend-gap slot cuts the bridge off the shelf / pocket wall over 128.8: the land plate is fed only from the "
                         "step wall + flange plate along its whole length (one 2.5 body), from the corner regions at its ends and "
                         "through the divider rib; no member on these paths is thinner than the 2.5 wall (measured above). Gate "
                         "position and fill are not known here (fill / warp simulation not done)."}


def run(ctx, log=C.log):
    t0 = time.time()
    fr, G = ctx.frame, ctx.G
    P = C.Probe(fr)
    res = {}
    log("[B] slivers")
    res["slivers"] = slivers(fr)
    log("    %d hits: design faces %d, fillet blends %d" % (res["slivers"]["hits"], len(res["slivers"]["design_face_slivers"]),
                                                          res["slivers"]["fillet_blend_slivers"]))
    log("[B] draft")
    res["draft"] = draft(fr, G)
    log("    flagged %d: %s" % (len(res["draft"]["flagged"]), res["draft"]["flagged_summary"]))
    log("[B] undercut: column rays")
    res["columns"] = column_test(fr)
    log("    %d rays, multi-interval columns %d" % (res["columns"]["rays"], len(res["columns"]["multi_interval_columns"])))
    log("[B] undercut: face visibility")
    res["visibility"] = visibility(fr, G)
    log("    A %d / B %d / split %d faces; occluded faces %d; parting violations %d" % (
        res["visibility"]["faces_A"], res["visibility"]["faces_B"], res["visibility"]["faces_split"],
        len(res["visibility"]["occluded_faces"]), len(res["visibility"]["parting_violations"])))
    res["flange_edge"] = flange_edge_side(fr, G, P)
    log("[B] thin walls / gaps")
    res["thin"] = thin_probe(fr, G)
    log("    thin walls %d (not lip: %d), thin gaps %d" % (len(res["thin"]["thin_walls"]),
                                                          len([r for r in res["thin"]["thin_walls"] if not r.get("what")]),
                                                          len(res["thin"]["thin_gaps"])))
    log("[B] thick sections (voxel EDT)")
    res["thick"] = thick_sections(fr, G, ctx.imgdir if ctx.render else None)
    log("    max sphere dia %.2f, spots > %.1f: %d" % (res["thick"]["max_sphere_dia"], THICK_LIMIT, len(res["thick"]["spots_over_limit"])))
    log("[B] sharp inside corners (concave edges without a round)")
    res["sharp_inside"] = sharp_inside_edges(fr, G)
    log("    %d sharp concave edges" % res["sharp_inside"]["sharp_concave_edges"])
    if G.gf2:
        log("[B] GF-2.0 bridge / bend-gap slot: tool halves, shut-off, material paths")
        res["bridge"] = bridge_mould(fr, G, res["visibility"], P)
        log("    zone faces %d; by feature %s" % (len(res["bridge"]["faces"]), {k: v["sides"] for k, v in res["bridge"]["by_feature"].items()}))
    if ctx.render:
        try:
            import render_gf
            res["draft_map_png"] = render_gf.draft_map(ctx, res["draft"]["per_face"])
        except Exception as e:      # the map is an image only; the draft verdict does not depend on it
            res["draft_map_png"] = "failed: %r" % (e,)
    res["seconds"] = round(time.time() - t0, 1)
    return res


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    r = run(ctx)
    C.dump(r, ctx.out("mould_only.json"))
