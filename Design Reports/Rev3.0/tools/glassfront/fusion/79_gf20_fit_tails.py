"""79 - stage 4 (GF-2.0), READ-ONLY: clearances of the GF-2.0 tail solids (70, bent-back route).
  * tail vs frame: min distance to every frame face whose bbox comes within 8 mm; each face is classed by the
    location of its closest point (bridge pocket face / land break, bridge nose, bridge floor = land-plate back, step
    face, flange plate = pocket floor, divider rib, pocket side walls, pocket bottom face / bottom wall, slot front face
    / shelf end / support ribs, other) -> minimum per class; overall min; intersection volume (must be 0)
  * tail vs glass, glass print, bead, optical bond, Formex sheet
  * tail vs every board body (non-DS1) within 6 mm: min distance + intersection volume (J10 / J11 hold the finger
    ends: overlap there is the insertion, by design); tail vs the DS1 panel bodies (lcm, tapes, CTP sensor, cover)
    with the 0.5 straight at the exit cut off (the tail leaves the panel there)
  * the same frame classes with the tail moved +-0.35 in y (panel edge position towards / away from the bridge)
Writes %TEMP%\\rev3_glassfront\\gf20\\fit_tails.json."""
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

TB = adsk.fusion.TemporaryBRepManager.get()


def box(x0, x1, y0, y1, z0, z1):
    c = adsk.core.Point3D.create((x0 + x1) / 20.0, -(y0 + y1) / 20.0, (z0 + z1) / 20.0)
    ob = adsk.core.OrientedBoundingBox3D.create(c, adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
                                                (x1 - x0) / 10.0, (y1 - y0) / 10.0, (z1 - z0) / 10.0)
    return TB.createBox(ob)


def moved(b, dy_abs):
    t = TB.copy(b)
    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(0, -dy_abs / 10.0, 0)
    TB.transform(t, m)
    return t


def classify(p):
    x, y, z = p
    zlb, zfl, zl = L.P("Z_LANDPLATE_BACK"), L.P("Z_FLOOR_LOW"), L.P("Z_LAND")
    yb = L.P("bend_y1")
    ysw = L.P("glass_y1") + L.P("s_ring")
    if abs(x - L.P("div_x")) < L.P("div_t") / 2 + 0.8 and y > yb - 0.2:
        return "divider rib (incl. root fillets)"
    if (x < L.P("tr_x0") - L.P("tail_side_add") + 0.6 or x > L.P("tr_x1") + L.P("tail_side_add") - 0.6) and 118.5 < y < 148.5:
        return "pocket side walls"
    if y > L.P("tr_y1") - 0.6:
        return "pocket bottom face / bottom wall"
    if y < yb - 0.5:
        return "slot front face / shelf end / support ribs"
    if y < yb + 1.6 and z < zlb + 0.05:
        if z > zl + 1.0 - 0.05:
            return "bridge nose (R1.5)"
        return "bridge pocket face / land break"
    if abs(z - zlb) < 0.6 and y < ysw:
        return "bridge floor (land-plate back)"
    if ysw - 0.8 < y < ysw + 0.8 and zfl - 0.05 < z < zlb + 0.05:
        return "step face (step-wall back)"
    if abs(z - zfl) < 0.6:
        return "flange plate (pocket floor)"
    return "other"


def classify_face(f):
    """stage 5: class of a frame face from its own geometry (type, normal, position), so that a face is never named
    after the place of its closest point (the GF-2.0 point classes mixed the flat pocket face into the nose class)"""
    g = f.geometry
    st = g.surfaceType
    c = f.centroid
    cx, cy, cz = c.x * 10, -c.y * 10, c.z * 10
    ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
    nx, ny, nz = n.x, -n.y, n.z
    zl, zlb, zfl = L.P("Z_LAND"), L.P("Z_LANDPLATE_BACK"), L.P("Z_FLOOR_LOW")
    yb, ysw = L.P("bend_y1"), L.P("glass_y1") + L.P("s_ring")
    dvx = L.P("div_x")
    walls = (L.P("tr_x0") - L.P("tail_side_add"), L.P("tr_x1") + L.P("tail_side_add"))
    if any(math.hypot(cx - L.P("pip%d_x" % k), cy - L.P("pip%d_y" % k)) < 1.2 for k in range(1, 9)):
        return "pips"
    if st == adsk.core.SurfaceTypes.PlaneSurfaceType:
        if abs(nz) > 0.999:
            for nm, zz in (("land-plate back (bridge floor)", zlb), ("flange plate (pocket floor)", zfl),
                           ("land (bead face, Z_LAND)", zl), ("trough top Z_TROUGH_TOP", L.P("Z_TROUGH_TOP")),
                           ("tops at Z_PCB", L.P("Z_PCB"))):
                if abs(cz - zz) < 0.01:
                    return nm
            return "other horizontal"
        if abs(nx) > 0.95:
            if abs(cx - dvx) < 3.0:
                return "divider rib (sides)"
            if min(abs(cx - w) for w in walls) < 0.8:
                return "tail-pocket side walls"
            return "other"
        if abs(ny) > 0.95:
            if abs(cy - yb) < 0.25 and cz < zlb + 0.05:
                return "bridge pocket face (flat)"
            if abs(cy - yb) < 0.5:
                return "bridge pocket face plane above the bridge (rib front)"
            if abs(cy - ysw) < 0.4:
                return "step face (step-wall back)"
            if abs(cy - L.P("tr_y1")) < 0.5:
                return "pocket bottom face / bottom wall"
            if cy < yb - 0.5:
                return "slot front face / shelf end"
            if abs(cx - dvx) < 3.0:
                return "divider rib (ends)"
            return "other"
        if 0.4 < abs(nz) < 0.9 and abs(cy - yb - L.P("land_break") / 2) < 0.4:
            return "land break 0.3 x 45"
        return "other"
    r = getattr(g, "radius", None) if st in (adsk.core.SurfaceTypes.CylinderSurfaceType,
                                             adsk.core.SurfaceTypes.SphereSurfaceType) else None
    if st == adsk.core.SurfaceTypes.CylinderSurfaceType and r is not None and abs(r * 10 - L.P("bend_nose_R")) < 0.01:
        return "bridge nose R1.5"
    if st == adsk.core.SurfaceTypes.TorusSurfaceType or (r is not None and abs(r * 10 - L.P("fillet_root")) < 0.01):
        return "divider rib roots" if abs(cx - dvx) < 3.0 else "root rounds R0.5"
    return "other"


def frame_classes(tail, fr):
    tb = tail.boundingBox
    out = {}
    for i in range(fr.faces.count):
        f = fr.faces.item(i)
        bb = f.boundingBox
        g = [max(bb.minPoint.x - tb.maxPoint.x, tb.minPoint.x - bb.maxPoint.x, 0),
             max(bb.minPoint.y - tb.maxPoint.y, tb.minPoint.y - bb.maxPoint.y, 0),
             max(bb.minPoint.z - tb.maxPoint.z, tb.minPoint.z - bb.maxPoint.z, 0)]
        if math.sqrt(sum(v * v for v in g)) * 10 > 8.0:
            continue
        d, p1, p2 = L.min_dist_mm(tail, f)
        cl = classify_face(f) if globals().get("FACE_CLASSES", True) else classify(L.pt_abs(p2))
        if cl not in out or d < out[cl]["d_mm"]:
            out[cl] = {"d_mm": round(d, 4), "p_tail": L.pt_abs(p1), "p_frame": L.pt_abs(p2),
                       "face_type": f.geometry.surfaceType, "face_area_mm2": round(f.area * 100, 3)}
    return out


def run(_context: str):
    L.check_doc()
    t0 = time.time()
    fr = A.frame()
    parts = {"glass": A.part("Glass", "Glass"), "glass print": A.part("Glass", "Glass print (black, 0.02)"),
             "bead": A.part("Bead", "Bead (4.0 x t_bond)"), "optical bond": A.part("Optical bond", "Optical bond (t_opt)"),
             "Formex sheet": A.part("Formex sheet", "Formex sheet")}
    bl = A.board()
    res = {"levels": {k: round(L.P(k), 4) for k in ("Z_LAND", "Z_LANDPLATE_BACK", "Z_FLOOR_LOW", "Z_GLASS_BACK",
                                                     "Z_PANEL_BACK", "Z_TAIL_LEG", "bend_y1", "glass_y1")},
           "tails": {}}
    for nm, tb in A.tails():
        tail = tb
        e = {"bbox": L.bbox_mm(tail), "volume_mm3": round(tail.volume * 1000, 3)}
        e["frame_overall"] = A.pair(fr, tail)
        e["frame_by_class"] = frame_classes(tail, fr)
        for dy in (+0.35, -0.35):
            t2 = moved(tail, dy)
            e["frame_by_class_panel_edge_%+.2f" % dy] = frame_classes(t2, fr)
            d, p1, p2 = L.min_dist_mm(t2, fr)
            e["frame_overall_panel_edge_%+.2f" % dy] = round(d, 4)
        e["parts"] = {}
        for pn, pb in parts.items():
            e["parts"][pn] = A.pair(tail, pb)
        # board bodies (non-DS1) within 6 mm
        near = []
        for path, ob in bl:
            if A.is_ds1(path) or not ob.isVisible:
                continue
            if A.bbox_gap(ob, tail) > 6.0:
                continue
            q = A.pair(tail, ob)
            q.update({"path": path, "bbox": L.bbox_mm(ob)})
            near.append(q)
        near.sort(key=lambda q: q["d_mm"])
        e["board_bodies_within_6"] = near
        # panel (DS1) bodies, tail without the 0.5 straight at the exit
        cuts = {}
        for key, ycut in (("beyond_straight_y119.5", L.P("panel_y1") + L.P("tail_straight_l0")),
                          ("beyond_y120.0", L.P("panel_y1") + 1.0)):
            cut = TB.copy(tail)
            rm = box(0, 220, 118.0, ycut, -12.0, -6.0)
            TB.booleanOperation(cut, rm, adsk.fusion.BooleanTypes.DifferenceBooleanType)
            cuts[key] = cut
        pan = []
        for path, ob in bl:
            if not A.is_ds1(path) or not ob.isVisible:
                continue
            part = A.ds1_part(path)
            if A.bbox_gap(ob, tail) > 6.0:
                continue
            row = {"ds1_part": part, "body": ob.name}
            for key, cut in cuts.items():
                d, p1, p2 = L.min_dist_mm(cut, ob)
                row[key] = {"d_mm": round(d, 4), "p_tail": L.pt_abs(p1), "p_panel": L.pt_abs(p2)}
            row["d_mm_beyond_straight"] = row["beyond_straight_y119.5"]["d_mm"]
            row["d_mm_beyond_y120"] = row["beyond_y120.0"]["d_mm"]
            pan.append(row)
        pan.sort(key=lambda q: q["d_mm_beyond_straight"])
        e["panel_ds1_bodies"] = pan
        res["tails"][nm] = e
    res["seconds"] = round(time.time() - t0, 1)
    p = L.dump(res, DUMP + "/fit_tails.json")
    print(p, res["seconds"])
    for nm, e in res["tails"].items():
        print(nm, "frame overall", e["frame_overall"]["d_mm"], e["frame_overall"].get("overlap_mm3"),
              {k: v["d_mm"] for k, v in sorted(e["frame_by_class"].items())})
        for dy in ("+0.35", "-0.35"):
            print("   panel edge %s:" % dy, e["frame_overall_panel_edge_%s" % dy],
                  {k: v["d_mm"] for k, v in sorted(e["frame_by_class_panel_edge_%s" % dy].items())})
        print("   parts", {k: (v["d_mm"], v.get("overlap_mm3")) for k, v in e["parts"].items()})
        print("   board", [(q["path"].split("+")[-1], q["d_mm"], q.get("overlap_mm3")) for q in e["board_bodies_within_6"][:8]])
        print("   panel", [(q["ds1_part"], q["d_mm_beyond_straight"], q["d_mm_beyond_y120"], q["beyond_y120.0"]["p_tail"],
                            q["beyond_y120.0"]["p_panel"]) for q in e["panel_ds1_bodies"][:6]])
