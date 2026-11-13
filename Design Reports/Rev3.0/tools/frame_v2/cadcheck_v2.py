"""CAD / mouldability checks of the frame STEP (no board needed).

  <venv>/Scripts/python.exe cadcheck_v2.py [--v1] [--frame f.step] [--params p.json]

1. SLIVERS (owner's Battery Sentinel cadcheck rule): faces with 2A/P < 0.3 mm or area < 0.5 mm2 -> FAIL.
   Info: planar faces whose in-plane bbox minor extent (the smallest bbox extent dropped: it is the face's
   out-of-plane thickness, 0 for axis-aligned faces) is < 0.3 mm (narrow strips that 2A/P may not flag).
2. DRAFT (pull = Z): every face classified. Flagged: planes parallel to Z (draft < 0.25 deg), cylinders with
   their axis parallel to Z (all should be drafted cones; holes cored by pins included), cones with a
   semi-angle < 0.25 deg, other surfaces whose sampled normals give < 0.25 deg. Each flagged face is listed with
   its centroid (KiCad abs) and identified against the stud / PCB-hole / peg tables.
3. THIN-WALL PROBE: plan sections at Z_FRONT + 1.25, Z -6, Z -3, Z -0.5 (shifted +0.013 if a horizontal face
   of the frame lies exactly there), rasterised at 0.05 mm. Local thickness = diameter of the largest disc that
   fits inside the material (or inside the gap) and covers the point (morphological opening, scipy EDT). Material
   and gap regions thinner than 1.0 mm are reported as components (centre, max width, length, area). A component
   that fills its length x width box (fill >= 0.6, length >= 2 x width) is a parallel-sided thin wall or slot
   (FAIL); a wedge (fill < 0.6) is a V-notch: a sharp corner tapering to 0, e.g. a boss bulging out of a wall
   face or two rounded outlines meeting (knife-edge tool steel; fixed by a root fillet) - listed, not failed.
   (The brief asked for 0.5 mm grid sampling with run lengths; scan-line runs mis-read oblique chords through
   round holes as thin gaps, so the inscribed-disc measure on a finer grid is used.)
4. FLANGE FACE: all -Z faces at Z_FRONT (bbox, area); nothing of the frame below Z_FRONT except the pegs;
   -Z faces recessed by < 0.2 mm (near-coplanar steps) listed.
5. FEATURES vs PARAMS: stud holes, stud tubes (OD, top Z, washer bearing area), PCB pilots, bosses and pegs
   found in the STEP at the params' positions (abs), with measured diameters.
Output: out/cadcheck.json
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

import common_v2 as C

SLIVER_W, SLIVER_A = 0.3, 0.5     # owner's rule
BLEND_R = 1.0                     # sphere / torus faces up to this radius are root-fillet corner blends
BLEND_BBOX = 1.5                  # B-spline / cylinder patches no larger than this are fillet corner blends
DRAFT_MIN = 0.25                  # deg: below this a face counts as undrafted
THIN_MIN = 1.0                    # mm: thinnest wall / gap reported
RES = 0.05                        # mm raster pixel of the thin-wall probe (the brief's 0.5 mm grid, refined)
COMP_AREA, COMP_EXT = 0.10, 1.0   # thin components smaller than this are sharp-corner specks, not walls / slots
SLOT_FILL = 0.6                   # area / (length x width) above this: parallel-sided (slot / wall), else a wedge
PROBE_SHIFT = 0.013               # mm, applied when a probe plane coincides with a horizontal face
WASHER_OD = 12.0                  # DIN 9021 M4


# --------------------------------------------------------------------------------------- 1. slivers
def slivers(shape):
    bad, narrow = [], []
    for f in shape.Faces():
        a = f.Area()
        p = sum(e.Length() for e in f.Edges())
        w = 2 * a / p if p > 0 else 0
        c = f.Center()
        if a < SLIVER_A or w < SLIVER_W:
            bad.append({"type": f.geomType(), "area": round(a, 3), "2A/P": round(w, 3),
                        "at_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)], "class": blend_class(f)})
        if f.geomType() == "PLANE":
            bb = f.BoundingBox()
            ext = sorted([bb.xlen, bb.ylen, bb.zlen])
            if ext[1] < SLIVER_W:
                narrow.append({"area": round(a, 3), "minor_extent": round(ext[1], 3), "2A/P": round(w, 3),
                               "at_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)]})
    other = [b for b in bad if not b["class"].startswith("fillet blend")]
    by_class = {}
    for b in bad:
        by_class[b["class"]] = by_class.get(b["class"], 0) + 1
    return {"faces": len(shape.Faces()), "slivers": bad, "by_class": by_class,
            "slivers_not_fillet_blends": len(other), "planar_narrow_extent": narrow,
            "rule": "2A/P < %.1f mm or area < %.1f mm2" % (SLIVER_W, SLIVER_A), "ok": not bad,
            "ok_excluding_fillet_blends": not other}


def blend_class(f):
    """small curved faces that are the corner patches of root fillets (sphere / torus of radius <= BLEND_R, or a
    B-spline / cylinder patch no larger than BLEND_BBOX) vs anything else"""
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
    return "sliver"


# --------------------------------------------------------------------------------------- 2. draft
def identify(D, x, y, r):
    """x, y abs; which named feature has its axis here"""
    for n in D.STUDS:
        if any(math.hypot(x - cx, y - cy) < 0.15 for cx, cy in D.hole_arc_centres(n)):
            return "stud %s%s" % (n, " (slot end)" if n in D.SLOTS else "")
    for tab, lab in ((D.STUDS, "stud"), (D.HOLES, "PCB hole"), (D.PEGS, "peg")):
        for n, (hx, hy) in tab.items():
            if math.hypot(x - hx, y - hy) < 0.15:
                return "%s %s" % (lab, n)
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


def draft(shape, D):
    counts, flagged, cones = {}, [], {}
    for f in shape.Faces():
        gt = f.geomType()
        c = f.Center()
        bb = f.BoundingBox()
        base = {"type": gt, "area": round(f.Area(), 3), "at_abs": [round(c.x, 2), round(-c.y, 2), round(c.z, 2)],
                "z": [round(bb.zmin, 3), round(bb.zmax, 3)]}
        if gt == "PLANE":
            nz = abs(f.normalAt().z)
            if nz > 0.9999:
                k = "plane horizontal"
            else:
                a = math.degrees(math.asin(min(1.0, nz)))
                k = "plane drafted"
                if a < DRAFT_MIN:
                    k = "plane parallel to Z"
                    flagged.append(dict(base, why="planar wall without draft", draft_deg=round(a, 3)))
        elif gt in ("CYLINDER", "CONE"):
            ax = C.axis_z_feature(f)
            if ax:
                kind, cx, cy, r, z0, z1, semi = ax
                who = identify(D, cx, -cy, r)
                if gt == "CYLINDER":
                    k = "cylinder axis Z"
                    flagged.append(dict(base, why="cylinder parallel to the pull (no draft)", r=round(r, 3),
                                        axis_abs=[round(cx, 3), round(-cy, 3)], feature=who))
                else:
                    k = "cone axis Z"
                    cones[round(abs(semi), 2)] = cones.get(round(abs(semi), 2), 0) + 1
                    if abs(semi) < DRAFT_MIN:
                        flagged.append(dict(base, why="cone with < %.2f deg" % DRAFT_MIN, semi_deg=round(semi, 3),
                                            r=round(r, 3), axis_abs=[round(cx, 3), round(-cy, 3)], feature=who))
            else:
                a = sampled_draft(f)
                k = "%s other axis" % gt.lower()
                if a < DRAFT_MIN:
                    flagged.append(dict(base, why="%s (axis not Z) with sampled draft %.2f deg" % (gt.lower(), a)))
        else:
            a = sampled_draft(f)
            k = gt.lower()
            if a < DRAFT_MIN and gt in ("SPHERE", "TORUS") and blend_class(f).startswith("fillet blend"):
                k = gt.lower() + " fillet blend (sampled normals pass the vertical, not a draft error)"
            elif a < DRAFT_MIN:
                flagged.append(dict(base, why="%s with sampled draft %.2f deg" % (gt.lower(), a), draft_deg=round(a, 3)))
        counts[k] = counts.get(k, 0) + 1
    by_why = {}
    for fl in flagged:
        key = fl["why"] + (" - " + fl["feature"].split()[0] if fl.get("feature") else "")
        by_why[key] = by_why.get(key, 0) + 1
    return {"counts": counts, "cone_semi_angles_deg": dict(sorted(cones.items())), "flagged": flagged,
            "flagged_summary": by_why, "draft_min_deg": DRAFT_MIN}


# --------------------------------------------------------------------------------------- 3. thin walls
def section_raster(shape, z, pad=2.0):
    """plan section at z rasterised (RES mm pixels, KiCad abs, row = y down): (material bool array, x0, y0)"""
    from PIL import Image, ImageDraw
    sec = C.plane_section(shape, "z", z)
    if sec is None:
        return None
    faces = [C.face_loops_abs(f, 0.002) for f in sec.Faces()]
    allp = np.vstack([l for loops in faces for l in loops])
    x0, y0 = allp[:, 0].min() - pad, allp[:, 1].min() - pad
    w = int(math.ceil((allp[:, 0].max() + pad - x0) / RES))
    h = int(math.ceil((allp[:, 1].max() + pad - y0) / RES))
    img = Image.new("1", (w, h), 0)
    dr = ImageDraw.Draw(img)
    for loops in faces:
        dr.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in loops[0]], fill=1)
        for hole in loops[1:]:
            dr.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in hole], fill=0)
    return np.array(img, dtype=bool), x0, y0


def narrow(region, r):
    """pixels of `region` not covered by any disc of radius r lying inside it (= local thickness < 2r)"""
    from scipy import ndimage
    edt = ndimage.distance_transform_edt(region, sampling=RES)
    core = edt > r
    opened = ndimage.distance_transform_edt(~core, sampling=RES) <= r
    return region & ~opened, edt


def components(mask, edt, x0, y0, kind):
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
        fill = area / max(ext * width, 1e-9)        # ~1 for a parallel-sided wall / slot, ~0.5 or less for a wedge
        is_slot = fill >= SLOT_FILL and ext >= 2 * width
        cls = ("%s thinner than %.1f" % ("wall" if kind == "wall" else "slot", THIN_MIN) if is_slot else
               "V-notch / sharp %s corner (wedge tapering to 0)" % ("convex" if kind == "wall" else "re-entrant"))
        out.append({"at_abs": [round(cx, 2), round(cy, 2)], "width_max": round(width, 3), "length": round(ext, 2),
                    "area_mm2": round(area, 3), "fill_ratio": round(fill, 2), "class": cls})
    return sorted(out, key=lambda r: r["width_max"]), small


def thin_walls(shape, D):
    planes = [("Z_FRONT+1.25", D.Z_FRONT + 1.25), ("Z-6", -6.0), ("Z-3", -3.0), ("Z-0.5", -0.5)]
    horiz = sorted({round(f.BoundingBox().zmin, 4) for f in shape.Faces()
                    if f.geomType() == "PLANE" and abs(f.normalAt().z) > 0.9999})
    res = []
    for name, z in planes:
        shifted = any(abs(z - h) < 0.005 for h in horiz)
        zz = z + PROBE_SHIFT if shifted else z
        r = section_raster(shape, zz)
        if r is None:
            res.append({"plane": name, "z": zz, "empty": True})
            continue
        mat, x0, y0 = r
        tw, edt_m = narrow(mat, THIN_MIN / 2)
        tg, edt_g = narrow(~mat, THIN_MIN / 2)
        walls, ws = components(tw, edt_m, x0, y0, "wall")
        gaps, gs = components(tg, edt_g, x0, y0, "gap")
        res.append({"plane": name, "z": round(zz, 3), "shifted": shifted,
                    "material_mm2": round(mat.sum() * RES * RES, 1),
                    "thin_walls": walls, "thin_gaps": gaps,
                    "slots_or_walls": [g for g in walls + gaps if not g["class"].startswith("V-notch")],
                    "v_notches": len([g for g in walls + gaps if g["class"].startswith("V-notch")]),
                    "ignored_corner_specks": {"wall": ws, "gap": gs}})
    ok = all(not p.get("slots_or_walls") for p in res)
    return {"min_mm": THIN_MIN, "raster_mm": RES, "planes": res, "ok": ok,
            "method": "plan section rasterised at %.2f mm; local thickness = largest inscribed disc (opening with a "
                      "dia-%.1f disc, scipy EDT) for material and for the gaps; components < %.2f mm2 or < %.1f mm "
                      "long (sharp-corner specks) ignored" % (RES, THIN_MIN, COMP_AREA, COMP_EXT)}


# --------------------------------------------------------------------------------------- 4. flange face
def flange_face(shape, D):
    zf = D.Z_FRONT
    faces = C.faces_at_z(shape, zf, -1)
    rows = []
    for f in faces:
        bb = f.BoundingBox()
        rows.append({"area_mm2": round(f.Area(), 2), "holes": len(f.innerWires()),
                     "bbox_abs": [round(bb.xmin, 2), round(bb.xmax, 2), round(-bb.ymax, 2), round(-bb.ymin, 2)]})
    near = []
    for f in shape.Faces():
        if f.geomType() != "PLANE" or f.normalAt().z > -0.9999:
            continue
        z = f.BoundingBox().zmin
        if zf + C.Z_TOL < z < zf + 0.2:
            c = f.Center()
            near.append({"z": round(z, 4), "area": round(f.Area(), 3), "at_abs": [round(c.x, 2), round(-c.y, 2)]})
    bb = C.optimal_bbox(shape)
    below = C.common_shape(shape, C.box(bb[0] - 1, bb[1] + 1, bb[2] - 1, bb[3] + 1, bb[4] - 1, zf - 0.002))
    proud = []
    for s in below.Solids():
        sb = C.optimal_bbox(s)
        cx, cy = (sb[0] + sb[1]) / 2, -(sb[2] + sb[3]) / 2
        peg = next((n for n, (px, py) in D.PEGS.items() if math.hypot(cx - px, cy - py) < 0.3), None)
        proud.append({"centre_abs": [round(cx, 2), round(cy, 2)], "size": [round(sb[1] - sb[0], 3), round(sb[3] - sb[2], 3)],
                      "depth_below_Z_FRONT": round(zf - sb[4], 3), "volume_mm3": round(s.Volume(), 3), "peg": peg})
    pegs_found = sorted(p["peg"] for p in proud if p["peg"])
    others = [p for p in proud if not p["peg"]]
    zmin_body = min((C.optimal_bbox(f)[4] for f in shape.Faces()
                     if not any(math.hypot(f.Center().x - px, -f.Center().y - py) < D.PEG_D for px, py in D.PEGS.values())),
                    default=bb[4])
    return {"z_front": zf, "faces": rows, "total_area_mm2": round(sum(r["area_mm2"] for r in rows), 1),
            "near_coplanar_recesses": near, "proud_below_front": proud, "pegs_found": pegs_found,
            "unexpected_proud": others, "zmin_without_pegs": round(zmin_body, 4),
            "ok": bool(rows) and not others and abs(zmin_body - zf) < C.Z_TOL}


# --------------------------------------------------------------------------------------- 5. features
def features(shape, D):
    cyl = []
    for f in shape.Faces():
        ax = C.axis_z_feature(f)
        if ax:
            kind, cx, cy, r, z0, z1, semi = ax
            cyl.append({"kind": kind, "x": cx, "y": -cy, "r": r, "z0": z0, "z1": z1, "semi": semi, "face": f})

    def near(x, y, r_nom, tol_r, tol_xy=0.1):
        c = [k for k in cyl if math.hypot(k["x"] - x, k["y"] - y) < tol_xy and abs(k["r"] - r_nom) < tol_r]
        return c

    def fmt(c):
        return {"kind": c["kind"], "dia_mid": round(2 * c["r"], 3), "z": [round(c["z0"], 3), round(c["z1"], 3)],
                "semi_deg": round(c["semi"], 3), "axis_abs": [round(c["x"], 3), round(c["y"], 3)]}
    tops = [f for f in shape.Faces() if f.geomType() == "PLANE" and f.normalAt().z > 0.9999]
    studs = []
    for n, (x, y) in D.STUDS.items():
        h = [c for cx, cy in D.hole_arc_centres(n) for c in near(cx, cy, D.STUD_HOLE_D / 2, 0.2)]
        t = near(x, y, D.STUD_OD / 2, 0.8, 0.2)
        row = {"name": n, "x": x, "y": y, "hole": [fmt(c) for c in h], "tube": [fmt(c) for c in t]}
        if n in D.SLOTS:
            row["slot"] = {"axis": D.SLOTS[n]["axis"], "len": D.SLOTS[n]["len"], "w": D.SLOTS[n]["w"],
                           "ends_found": len(h)}
        # tube top: highest +Z planar face with a hole edge (round or slot) centred on this stud
        best = None
        for f in tops:
            for w in f.innerWires():
                wb = w.BoundingBox()
                hmin = min(wb.xmax - wb.xmin, wb.ymax - wb.ymin) / 2      # half the smaller bbox extent:
                lmax = D.SLOTS[n]["len"] if n in D.SLOTS else D.STUD_HOLE_D  # W/2 (round, axis-aligned slot) up to
                if math.hypot((wb.xmin + wb.xmax) / 2 - x, -(wb.ymin + wb.ymax) / 2 - y) < 0.1 and \
                        D.STUD_HOLE_D / 2 - 0.2 < hmin < lmax / 2 + 0.2:            # ~L/2 (slot at 45 deg)
                    z = f.BoundingBox().zmax
                    if best is None or z > best[0]:
                        best = (z, f)
        if best:
            z, f = best
            disc = C.tube(x, y, z - 1, z + 1, WASHER_OD).val()
            a = sum(ff.Area() for ff in C.common_shape(f, disc).Faces())
            row["top_z"] = round(z, 3)
            row["washer_bearing_area_mm2"] = round(a, 2)
            row["top_face_area_mm2"] = round(f.Area(), 2)
        row["found"] = bool(h) and best is not None
        studs.append(row)
    holes = []
    for n, (x, y) in D.HOLES.items():
        p = near(x, y, D.PILOT_D / 2, 0.15)
        b = near(x, y, D.BOSS_OD / 2, 0.6, 0.2)
        holes.append({"name": n, "pilot": [fmt(c) for c in p], "boss": [fmt(c) for c in b],
                      "found": bool(p) and bool(b)})
    pegs = []
    for n, (x, y) in D.PEGS.items():
        p = near(x, y, D.PEG_D / 2, 0.2)
        pegs.append({"name": n, "peg": [fmt(c) for c in p], "found": bool(p)})
    named = [(x, y) for tab in (D.STUDS, D.HOLES, D.PEGS) for x, y in tab.values()]
    unmatched = [fmt(c) for c in cyl if c["r"] < 3.0 and not any(math.hypot(c["x"] - x, c["y"] - y) < 0.2 for x, y in named)]
    tz = [s["top_z"] for s in studs if "top_z" in s]
    return {"studs": studs, "pcb_holes": holes, "pegs": pegs, "unmatched_small_axial_faces": unmatched[:30],
            "stud_top_z_measured": sorted(set(tz)), "stud_top_z_params": D.Z_STUD_TOP,
            "ok": all(s["found"] for s in studs) and all(h["found"] for h in holes) and all(p["found"] for p in pegs)}


def run(ctx, log=C.log):
    t0 = time.time()
    fr, D = ctx.frame, ctx.D
    res = {"frame": ctx.frame_path, "frame_info": ctx.frame_info}
    log("[cad] slivers")
    res["slivers"] = slivers(fr)
    log("    %d of %d faces (%s)" % (len(res["slivers"]["slivers"]), res["slivers"]["faces"], res["slivers"]["by_class"]))
    log("[cad] draft")
    res["draft"] = draft(fr, D)
    log("    flagged: %s" % res["draft"]["flagged_summary"])
    log("[cad] thin-wall probe")
    res["thin"] = thin_walls(fr, D)
    for p in res["thin"]["planes"]:
        log("    %-13s z %7.3f  thin walls %d, thin gaps %d (V-notches %d, slots/walls < %.1f: %d)" % (
            p["plane"], p["z"], len(p.get("thin_walls", [])), len(p.get("thin_gaps", [])),
            sum(g["class"].startswith("V-notch") for g in p.get("thin_walls", []) + p.get("thin_gaps", [])),
            THIN_MIN, len(p.get("slots_or_walls", []))))
    log("[cad] flange face")
    res["flange_face"] = flange_face(fr, D)
    log("    %d faces at Z_FRONT, %.0f mm2; proud: pegs %s, other %d" % (
        len(res["flange_face"]["faces"]), res["flange_face"]["total_area_mm2"], res["flange_face"]["pegs_found"],
        len(res["flange_face"]["unexpected_proud"])))
    log("[cad] features vs params")
    res["features"] = features(fr, D)
    log("    studs found %d/%d, PCB holes %d/%d, pegs %d/%d, stud top Z %s" % (
        sum(s["found"] for s in res["features"]["studs"]), len(D.STUDS),
        sum(h["found"] for h in res["features"]["pcb_holes"]), len(D.HOLES),
        sum(p["found"] for p in res["features"]["pegs"]), len(D.PEGS), res["features"]["stud_top_z_measured"]))
    fi = ctx.frame_info
    res["body_ok"] = fi["valid"] and fi["single_solid"]
    res["seconds"] = round(time.time() - t0, 1)
    C.dump(res, ctx.out("cadcheck.json"))
    return res


if __name__ == "__main__":
    run(C.Context(sys.argv[1:]))
