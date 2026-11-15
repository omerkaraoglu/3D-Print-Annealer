"""64 - stage 3, lead round 3 (frame FROZEN: no frame feature is touched; a frame fingerprint is taken before and after
and the script raises if it differs). Hardware bodies of the hidden variants only:
  A. R4: large-flange blind rivet dia 4.8 with a dia-14 head (DIN 7337 large-flange type 'K14'): riv_head_d 10 -> 14,
     riv_head_k kept 1.6 (edge round riv_head_k - 0.2 = 1.4 as before); sheet hole riv_hole 5.2 unchanged.
  B. S8: DIN 988 7 x 13 x 1.0 shim: spacer_id 6.0 -> 7.0, spacer_od 12 -> 13; bodies renamed 'Spacer DIN 988 7x13x1.0 Fk'.
Measurements (read-only, temporary BReps) -> gf11\\round3_hardware.json:
  * pad face area under the head (dia riv_head_d, and dia 10 for reference) at F1-F4: frame material in a 0.01 slab
    behind Z_SHEET_BACK inside the head circle
  * head edge to the sheet cut-out (R4 sheet body) and d_cut_out_edge of F1-F8 (stud axis at the sheet front to the
    nearest cut-out face, from the face geometry of the S4 sheet body)
  * S8 shim: contact area on the flange front (shim shifted 0.02 back, intersected with the frame / 0.02), contact on the
    sheet, nearest vertical frame faces in the 1.0 gap layer outside the shim (seat ring / flange edge), shim edge vs the
    tape band s_tape_in..s_tape_out
  * clearance pocket outline at the land (Z_LAND + 0.01) vs at Z_SEAT (Z_SEAT - 0.01), bead inner outline (Z_LAND - 0.01)
  * Formex sheet body: plan bbox, corner radius, Z range"""
import hashlib
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

C = "GF-1.1 round 3: "
NEW = {"riv_head_d": ("14 mm", C + "R4 large-flange blind rivet dia 4.8, head dia 14 (DIN 7337 large-flange type K14; was "
                                  "the dia-10 dome head)"),
       "riv_head_k": ("1.6 mm", C + "R4 head height used 1.6 (K14 heads about 1.5-2.0 proud; edge round riv_head_k - 0.2)"),
       "spacer_id": ("7.0 mm", C + "S8 shim DIN 988 7 x 13 x 1.0 bore (clears a weld collar on the 5.3-5.7 flange; "
                                 "was 6 x 12)"),
       "spacer_od": ("13 mm", C + "S8 shim DIN 988 7 x 13 x 1.0 OD")}
ST = adsk.core.SurfaceTypes
TB = adsk.fusion.TemporaryBRepManager.get()
INTER = adsk.fusion.BooleanTypes.IntersectionBooleanType


def fingerprint(b):
    areas = sorted(round(b.faces.item(i).area * 100, 6) for i in range(b.faces.count))
    bb = b.boundingBox
    return {"volume_cm3": round(b.volume, 7), "area_mm2": round(b.area * 100, 5), "faces": b.faces.count,
            "edges": b.edges.count,
            "bbox": [round(v * 10, 5) for v in (bb.minPoint.x, bb.maxPoint.x, bb.minPoint.y, bb.maxPoint.y,
                                                bb.minPoint.z, bb.maxPoint.z)],
            "face_area_hash": hashlib.sha256(json.dumps(areas).encode()).hexdigest()[:16]}


def slab_area(fr, x, y, r, z0, dz=0.01):
    cyl = TB.createCylinderOrCone(adsk.core.Point3D.create(x / 10, -y / 10, z0 / 10), r / 10,
                                  adsk.core.Point3D.create(x / 10, -y / 10, (z0 + dz) / 10), r / 10)
    a = TB.copy(fr)
    if not TB.booleanOperation(a, cyl, INTER):
        return None
    return round(a.volume * 1000 / dz, 2)


def shifted_contact(part, fr, dz_mm):
    a = TB.copy(part)
    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(0, 0, dz_mm / 10)
    TB.transform(a, m)
    if not TB.booleanOperation(a, TB.copy(fr), INTER):
        return None
    return round(a.volume * 1000 / abs(dz_mm), 2)


def cutout_faces(sheet):
    """vertical faces of the sheet cut-out (inside the cut-out rectangle + 1, no rivet holes)"""
    x0, x1, y0, y1 = [L.ev(e) for e in ("glass_x0 - s_cut", "glass_x1 + s_cut", "glass_y0 - s_cut", "glass_y1 + s_cut")]
    out = []
    for i in range(sheet.faces.count):
        f = sheet.faces.item(i)
        g = f.geometry
        bb = f.boundingBox
        if abs(bb.maxPoint.z - bb.minPoint.z) < 1e-6:
            continue
        if g.surfaceType == ST.CylinderSurfaceType and abs(g.radius * 10 - L.P("riv_hole") / 2) < 1e-3:
            continue
        bx0, bx1, by0, by1 = bb.minPoint.x * 10, bb.maxPoint.x * 10, -bb.maxPoint.y * 10, -bb.minPoint.y * 10
        if bx0 > x0 - 1 and bx1 < x1 + 1 and by0 > y0 - 1 and by1 < y1 + 1:
            out.append(f)
    return out


def dist_point_face(px, py, f):
    """plan distance from (px, py abs) to a vertical cut-out face (cylinder corner or plane), from its geometry"""
    g = f.geometry
    bb = f.boundingBox
    if g.surfaceType == ST.CylinderSurfaceType:
        cx, cy = g.origin.x * 10, -g.origin.y * 10
        d = math.hypot(px - cx, py - cy)
        # foot point must lie on the face (inside its plan bbox)
        fx, fy = cx + (px - cx) / d * g.radius * 10, cy + (py - cy) / d * g.radius * 10
        inside = (bb.minPoint.x * 10 - 1e-3 <= fx <= bb.maxPoint.x * 10 + 1e-3 and
                  -bb.maxPoint.y * 10 - 1e-3 <= fy <= -bb.minPoint.y * 10 + 1e-3)
        return (abs(d - g.radius * 10), "corner R%.3f" % (g.radius * 10)) if inside else (None, None)
    if g.surfaceType == ST.PlaneSurfaceType:
        n = g.normal
        o = g.origin
        sd = ((px / 10 - o.x) * n.x + (-py / 10 - o.y) * n.y) * 10          # signed, mm, plan (n.z ~ 0)
        fx, fy_m = px - sd * n.x, -py - sd * n.y                            # foot point (model x, model y)
        inside = (bb.minPoint.x * 10 - 1e-3 <= fx <= bb.maxPoint.x * 10 + 1e-3 and
                  bb.minPoint.y * 10 - 1e-3 <= fy_m <= bb.maxPoint.y * 10 + 1e-3)
        return (abs(sd), "straight edge") if inside else (None, None)
    return None, None


def d_cut_out(sheet, x, y):
    best = None
    for f in cutout_faces(sheet):
        d, what = dist_point_face(x, y, f)
        if d is not None and (best is None or d < best[0]):
            best = (d, what)
    return best


def vertical_faces_near(fr, x, y, zlo, zhi, rmin, rmax):
    out = []
    for i in range(fr.faces.count):
        f = fr.faces.item(i)
        bb = f.boundingBox
        z0, z1 = bb.minPoint.z * 10, bb.maxPoint.z * 10
        if z1 - z0 < 1e-4 or z1 < zlo - 1e-3 or z0 > zhi + 1e-3:
            continue
        cx, cy = (bb.minPoint.x + bb.maxPoint.x) * 5, -(bb.minPoint.y + bb.maxPoint.y) * 5
        # plan distance of the face bbox to the axis
        dx = max(bb.minPoint.x * 10 - x, 0, x - bb.maxPoint.x * 10)
        dy = max(-bb.maxPoint.y * 10 - y, 0, y + bb.minPoint.y * 10)
        far = max(abs(bb.minPoint.x * 10 - x), abs(bb.maxPoint.x * 10 - x), abs(-bb.minPoint.y * 10 - y),
                  abs(-bb.maxPoint.y * 10 - y))
        if math.hypot(dx, dy) > rmax or far < rmin:
            continue
        out.append(f)
    return out


def run(_context: str):
    d = L.check_doc()
    fr = A.frame()
    fp0 = fingerprint(L.body())
    ups = d.userParameters
    old = {}
    for n, (expr, cm) in NEW.items():
        p = ups.itemByName(n)
        old[n] = p.expression
        p.expression = expr
        p.comment = cm
    d.computeAll()
    c8 = L.occ_by_comp("Washers, nuts, spacers S8 F5-F8 (hidden)").component
    ren = 0
    for i in range(c8.bRepBodies.count):
        b = c8.bRepBodies.item(i)
        if b.name.startswith("Spacer DIN 988 6x12x1.0"):
            b.name = b.name.replace("Spacer DIN 988 6x12x1.0", "Spacer DIN 988 7x13x1.0")
            ren += 1
    n, bad = L.timeline_health()
    fp1 = fingerprint(L.body())
    if fp0 != fp1:
        raise RuntimeError("FRAME CHANGED: %s -> %s" % (fp0, fp1))
    out = {"params_old": old, "params_new": {k: v[0] for k, v in NEW.items()}, "spacers_renamed": ren,
           "timeline": [n, bad], "frame_fingerprint (unchanged)": fp1}
    # ---------------------------------------------------------------- A. R4
    zs = L.P("Z_SHEET_BACK")
    sheet_r4 = A.part("Oven sheet", "Oven sheet R4 (rivet holes)")
    sheet_s4 = A.part("Oven sheet", "Oven sheet S4/S8 (no holes)")
    r4 = {}
    for k in (1, 2, 3, 4):
        x, y = L.P("f%d_x" % k), L.P("f%d_y" % k)
        riv = A.part("Rivets R4 F1-F4 (hidden)", "Blind rivet 4.8 F%d" % k)
        heads = [riv.faces.item(i) for i in range(riv.faces.count)
                 if riv.faces.item(i).geometry.surfaceType == ST.CylinderSurfaceType and
                 abs(riv.faces.item(i).geometry.radius * 10 - L.P("riv_head_d") / 2) < 1e-3]
        corner = [f for f in cutout_faces(sheet_r4) if f.geometry.surfaceType == ST.CylinderSurfaceType]
        dm = min((L.min_dist_mm(h, f) for h in heads for f in corner), key=lambda t: t[0]) if heads and corner else None
        dc = d_cut_out(sheet_r4, x, y)
        r4["F%d" % k] = {
            "pad_face_under_head_dia14_mm2": slab_area(fr, x, y, L.P("riv_head_d") / 2, zs),
            "pad_face_under_head_dia10_mm2 (old head)": slab_area(fr, x, y, 5.0, zs),
            "pad_face_total_mm2": slab_area(fr, x, y, 9.5, zs),
            "head_edge_to_cut_out_corner_measured": None if dm is None else {"d_mm": round(dm[0], 4),
                                                                              "p_head": L.pt_abs(dm[1]),
                                                                              "p_sheet": L.pt_abs(dm[2])},
            "axis_to_cut_out_edge": round(dc[0], 4), "nearest": dc[1],
            "head_faces_found": len(heads), "rivet_bbox_z": [round(riv.boundingBox.minPoint.z * 10, 3),
                                                             round(riv.boundingBox.maxPoint.z * 10, 3)]}
    out["R4"] = r4
    out["d_cut_out_edge"] = {}
    for k in range(1, 9):
        dc = d_cut_out(sheet_s4, L.P("f%d_x" % k), L.P("f%d_y" % k))
        out["d_cut_out_edge"]["F%d" % k] = [round(dc[0], 4), dc[1]]
    # ---------------------------------------------------------------- B. S8
    s8 = {}
    zf = L.P("Z_FLANGE_FRONT")
    for k in (5, 6, 7, 8):
        x, y = L.P("f%d_x" % k), L.P("f%d_y" % k)
        sp = A.part("Washers, nuts, spacers S8 F5-F8 (hidden)", "Spacer DIN 988 7x13x1.0 F%d" % k)
        od = [sp.faces.item(i) for i in range(sp.faces.count)
              if sp.faces.item(i).geometry.surfaceType == ST.CylinderSurfaceType and
              abs(sp.faces.item(i).geometry.radius * 10 - L.P("spacer_od") / 2) < 1e-3]
        near = vertical_faces_near(fr, x, y, zs, zf, L.P("spacer_od") / 2 - 0.5, 14.0)
        rows = []
        for f in near:
            dd, p1, p2 = L.min_dist_mm(od[0], f)
            g = f.geometry
            rows.append({"d_mm": round(dd, 4), "type": g.surfaceType, "p_frame": L.pt_abs(p2),
                         "z": [round(f.boundingBox.minPoint.z * 10, 3), round(f.boundingBox.maxPoint.z * 10, 3)]})
        rows.sort(key=lambda r: r["d_mm"])
        s8["F%d" % k] = {"contact_on_flange_front_mm2": shifted_contact(sp, fr, 0.02),
                         "contact_on_sheet_mm2": shifted_contact(sp, sheet_s4, -0.02),
                         "annulus_mm2": round(math.pi * ((L.P("spacer_od") / 2) ** 2 - (L.P("spacer_id") / 2) ** 2), 2),
                         "nearest_vertical_frame_faces_in_gap_layer": rows[:4]}
    s = L.P("fast_off")
    s8["band"] = {"shim_s_range": [round(s - L.P("spacer_od") / 2, 3), round(s + L.P("spacer_od") / 2, 3)],
                  "tape_band_s": [L.P("s_tape_in"), L.P("s_tape_out")], "fast_off": s,
                  "length_of_band_taken_per_position": L.P("spacer_od")}
    out["S8"] = s8
    # ---------------------------------------------------------------- pocket at the land / seat, bead, Formex
    p47 = os.path.join(L.GF_DIR, "47_asm_docinfo.py")
    ns = {"__name__": "gf_47_lib", "__file__": p47}
    exec(compile(open(p47, encoding="utf-8").read(), p47, "exec"), ns)
    lb = ns["loops_bbox"]

    def pocket_loop(z):
        loops = [l["bbox_abs"] for l in lb(L.body(), z) if not l["outer"]]
        return min(loops, key=lambda bb: abs(bb[0] - 19.2) + abs(bb[1] - 185.7) + abs(bb[2] - 18.2) +
                   abs(bb[3] - 119.8))
    bead = A.part("Bead", "Bead (4.0 x t_bond)")
    bl = [l["bbox_abs"] for l in lb(bead, L.P("Z_LAND") - 0.01) if not l["outer"]]
    bead_in = max(bl, key=lambda bb: (bb[1] - bb[0]) * (bb[3] - bb[2]))
    pl = pocket_loop(L.P("Z_LAND") + 0.01)
    ps = pocket_loop(L.P("Z_SEAT") - 0.01)
    out["pocket"] = {"at_land_Z+0.01": pl, "at_seat_Z-0.01": ps,
                     "per_side_larger_at_land": [round(ps[0] - pl[0], 4), round(pl[1] - ps[1], 4),
                                                 round(ps[2] - pl[2], 4), round(pl[3] - ps[3], 4)],
                     "bead_inner_bbox": bead_in,
                     "bead_to_pocket_at_land [left, right, top]": [round(pl[0] - bead_in[0], 4),
                                                                   round(bead_in[1] - pl[1], 4),
                                                                   round(pl[2] - bead_in[2], 4)],
                     "bead_to_pocket_at_seat [left, right, top]": [round(ps[0] - bead_in[0], 4),
                                                                   round(bead_in[1] - ps[1], 4),
                                                                   round(ps[2] - bead_in[2], 4)]}
    fx = A.part("Formex sheet", "Formex sheet")
    bb = fx.boundingBox
    radii = sorted(set(round(fx.faces.item(i).geometry.radius * 10, 4) for i in range(fx.faces.count)
                       if fx.faces.item(i).geometry.surfaceType == ST.CylinderSurfaceType))
    out["formex"] = {"x0": round(bb.minPoint.x * 10, 4), "x1": round(bb.maxPoint.x * 10, 4),
                     "y0": round(-bb.maxPoint.y * 10, 4), "y1": round(-bb.minPoint.y * 10, 4),
                     "z": [round(bb.minPoint.z * 10, 4), round(bb.maxPoint.z * 10, 4)], "corner_R": radii,
                     "volume_mm3": round(fx.volume * 1000, 2), "faces": fx.faces.count}
    p = os.path.join(L.SCR, "gf11", "round3_hardware.json")
    json.dump(out, open(p, "w"), indent=1)
    L.log("64 round 3: %s -> %s, spacers renamed %d, timeline %d %s, frame unchanged %s" %
          (old, out["params_new"], ren, n, bad, fp1))
    print(p, old, ren, n, bad)
