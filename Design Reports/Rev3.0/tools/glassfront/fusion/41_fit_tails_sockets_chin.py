"""41 - stage 2, Part C (READ-ONLY): tails, sockets, chin, lead tips.
  TAILS (DS1 tft_tail_5 / ctp_tail_7 / fingers): distance to every frame face within 8 mm (face centroid, normal,
    owner feature), to the glass, the print and the bead - for the model position (rigid shift ds1_dz, the legs on
    the panel are right) AND for a temporary copy moved back by -ds1_dz (the v2 position = where the return legs and
    fingers really are, since the U-loops take up the 0.8)
  FINGERS: intersection volume with the board bodies within 3 mm (J10 / J11 / PCB) in the model position (artefact
    of the rigid shift) and in the v2 position
  SOCKETS: every dia-12 socket vs every board body whose bbox comes within 40 mm (true nearest per socket)
  CHIN: glass + print cut to y > panel_y1 (temporary box): distance to the frame, the tails, the bond, the bead
  Q1: lead tips vs the Formex sheet and the LCM back (untrimmed model)
Writes scratchpad fit_tails.json."""
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

TB = adsk.fusion.TemporaryBRepManager.get()


def moved(b, dz_mm):
    t = TB.copy(b)
    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(0, 0, dz_mm / 10.0)
    TB.transform(t, m)
    return t


def tmp_min(a, b):
    """min distance between two temporary / real bodies (measureManager accepts BRepBody)"""
    return L.min_dist_mm(a, b)


def face_rows(tail, fr, owners, lim=8.0):
    tb = tail.boundingBox
    rows = []
    for i in range(fr.faces.count):
        f = fr.faces.item(i)
        bb = f.boundingBox
        g = [max(bb.minPoint.x - tb.maxPoint.x, tb.minPoint.x - bb.maxPoint.x, 0),
             max(bb.minPoint.y - tb.maxPoint.y, tb.minPoint.y - bb.maxPoint.y, 0),
             max(bb.minPoint.z - tb.maxPoint.z, tb.minPoint.z - bb.maxPoint.z, 0)]
        if math.sqrt(sum(v * v for v in g)) * 10 > lim:
            continue
        d, p1, p2 = L.min_dist_mm(tail, f)
        c = f.centroid
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        rows.append({"d_mm": round(d, 4), "p_tail": L.pt_abs(p1), "p_frame": L.pt_abs(p2),
                     "face_centroid": L.pt_abs(c), "normal": [round(n.x, 3), round(-n.y, 3), round(n.z, 3)],
                     "type": f.geometry.surfaceType, "area_mm2": round(f.area * 100, 2),
                     "owner": owners.get(f.nativeObject.tempId if f.nativeObject else f.tempId)})
    rows.sort(key=lambda r: r["d_mm"])
    return rows


def run(_context: str):
    L.check_doc()
    t0 = time.time()
    fr = A.frame()
    owners = L.face_owners()
    glass = A.part("Glass", "Glass")
    prt = A.part("Glass", "Glass print (black, 0.02)")
    bead = A.part("Bead", "Bead (4.0 x t_bond)")
    bond = A.part("Optical bond", "Optical bond (t_opt)")
    formex = A.part("Formex sheet", "Formex sheet")
    bl = A.board()
    ds = {A.ds1_part(p): b for p, b in bl if A.is_ds1(p)}
    dz = L.P("ds1_dz")
    res = {"ds1_dz": dz, "tails": {}}
    for nm in ("tft_tail_5", "ctp_tail_7", "tft_fingers_6", "ctp_fingers_8"):
        b = ds[nm]
        e = {"bbox_model": L.bbox_mm(b)}
        for pos, body in (("model (rigid -0.80)", b), ("v2 position (+0.80 back)", moved(b, -dz))):
            q = {}
            if pos.startswith("model"):
                q["frame_faces"] = face_rows(b, fr, owners)[:14]
                q["frame_min"] = q["frame_faces"][0]["d_mm"] if q["frame_faces"] else None
            else:
                d, p1, p2 = tmp_min(body, fr)
                q["frame_min"] = round(d, 4)
                q["frame_min_points"] = [L.pt_abs(p1), L.pt_abs(p2)]
            for pn, pb in (("glass", glass), ("print", prt), ("bead", bead), ("bond", bond)):
                d, p1, p2 = tmp_min(body, pb)
                q[pn] = {"d_mm": round(d, 4), "p_tail": L.pt_abs(p1)}
            if "fingers" in nm:
                ov = []
                bt = body.boundingBox
                for p, ob in bl:
                    if A.is_ds1(p):
                        continue
                    if A.bbox_gap(ob, b) > 3.0:
                        continue
                    a = TB.copy(body)
                    c = TB.copy(ob)
                    ok = TB.booleanOperation(a, c, adsk.fusion.BooleanTypes.IntersectionBooleanType)
                    v = a.volume * 1000 if ok else None
                    if v and v > 1e-6:
                        ov.append({"path": p, "bbox": L.bbox_mm(ob), "overlap_mm3": round(v, 4)})
                q["overlaps_with_board_bodies"] = ov
            e[pos] = q
        res["tails"][nm] = e
    # ---------------------------------------------------------------- sockets vs board (true nearest)
    so = {}
    for cn, bn, sb, v in A.parts():
        if v != "check":
            continue
        best = None
        for p, ob in bl:
            if A.bbox_gap(sb, ob) > 40:
                continue
            d, p1, p2 = L.min_dist_mm(sb, ob)
            if best is None or d < best["d_mm"]:
                best = {"d_mm": round(d, 4), "path": p, "bbox": L.bbox_mm(ob), "p_body": L.pt_abs(p2)}
        so[bn] = best
    res["sockets_vs_board"] = so
    # ---------------------------------------------------------------- chin
    y0 = L.P("panel_y1")
    obb = adsk.core.OrientedBoundingBox3D.create(
        adsk.core.Point3D.create(10.385, -(y0 + 25.0) / 10.0, -1.3), adsk.core.Vector3D.create(1, 0, 0),
        adsk.core.Vector3D.create(0, 1, 0), 25.0, 5.0, 1.0)            # x -2..23 cm, y -(y0)..-(y0+50) mm, Z -1.8..-0.8 cm
    chin = {}
    for gn, gb in (("glass", glass), ("print", prt)):
        a = TB.copy(gb)
        TB.booleanOperation(a, TB.createBox(obb), adsk.fusion.BooleanTypes.IntersectionBooleanType)
        r = {"chin_bbox": [round(a.boundingBox.minPoint.x * 10, 3), round(a.boundingBox.maxPoint.x * 10, 3),
                           round(-a.boundingBox.maxPoint.y * 10, 3), round(-a.boundingBox.minPoint.y * 10, 3)]}
        for on, ob in (("frame", fr), ("tft_tail_5", ds["tft_tail_5"]), ("ctp_tail_7", ds["ctp_tail_7"]),
                       ("bead", bead), ("bond", bond), ("lcm_0", ds["lcm_0"]), ("cover_print_3", ds["cover_print_3"])):
            d, p1, p2 = L.min_dist_mm(a, ob)
            r[on] = {"d_mm": round(d, 4), "p_glass": L.pt_abs(p1), "p_other": L.pt_abs(p2)}
        chin[gn] = r
    res["chin"] = chin
    # ---------------------------------------------------------------- Q1 lead tips
    q1 = []
    for p, ob in bl:
        bb = L.bbox_mm(ob)
        if bb[4] < -5.0 and not A.is_ds1(p):
            r = {"path": p, "bbox": bb}
            for on, o2 in (("formex", formex), ("lcm_0", ds["lcm_0"])):
                d, p1, p2 = L.min_dist_mm(ob, o2)
                r[on] = round(d, 4)
                if d < 0.001:
                    r[on + "_overlap_mm3"] = round(L.overlap_volume_mm3(ob, o2), 4)
            q1.append(r)
    res["deep_leads"] = q1
    res["seconds"] = round(time.time() - t0, 1)
    p = L.dump(res, "fit_tails.json")
    print(p, res["seconds"])
    for nm, e in res["tails"].items():
        for pos in ("model (rigid -0.80)", "v2 position (+0.80 back)"):
            q = e[pos]
            print(nm, pos, "frame", q["frame_min"], {k: q[k]["d_mm"] for k in ("glass", "print", "bead", "bond")},
                  [(o["path"].split("+")[-1], o["overlap_mm3"]) for o in q.get("overlaps_with_board_bodies", [])])
    print("sockets", {k: (v["d_mm"], v["path"].split("+")[-1]) if v else None for k, v in so.items()})
    print("chin", {g: {k: v["d_mm"] for k, v in r.items() if isinstance(v, dict)} for g, r in chin.items()},
          chin["glass"]["chin_bbox"])
    print("deep leads", q1)
