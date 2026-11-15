"""63 - stage 3 follow-up (GF-1.1, lead round 2), measurement only (everything restored):
(a) worst-case weld flange 5.7 x 1.4 (stud_fl_d / stud_fl_k set temporarily) with ONE stud at its extreme positions:
    the stud occurrence ('Weld studs S4 F1-F4' for F1, 'Weld studs S8 F5-F8 (hidden)' for F5) is moved in plan by a
    temporary transform (pending position change, reverted with Snapshots.revertPendingSnapshot()). For each direction
    (along the slot axis +/- = slot ends, across +/- = slot walls, 30 / 60 deg = end arcs) the offset is found by
    bisection until the SHANK is 0.002 from the frame (= stud against the slot wall); then the real minimum distances
    of the FLANGE faces (Ø stud_fl_d side, top annulus) to the counterbore walls, the floor round and the floor are
    measured face by face (measureMinimumDistance).
(b) VHB tape (S4) over the F5-F8 openings: per position, tape footprint in a 20 x 20 box round Fk minus its contact
    with the flange front (tape piece shifted 0.02 back, intersected with the frame / 0.02) = tape area over air;
    compared with the GF-1.0 slot (stadium 5.4 x 7.0) and the 7.2 x 8.8 counterbore at the flange-front plane.
-> gf11\\extreme_stud_tape.json"""
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

STUDS = [(1, "Weld studs S4 F1-F4", "cb_floor"), (5, "Weld studs S8 F5-F8 (hidden)", "cb_floor_mid")]
DIRS = [("along + (slot end)", 0), ("along - (slot end)", 180), ("across + (slot wall)", 90),
        ("across - (slot wall)", 270), ("end arc 30 deg", 30), ("end arc 60 deg", 60)]
ST = adsk.core.SurfaceTypes


def stadium_area(w, l):
    return w * (l - w) + math.pi * w * w / 4


def stud_faces(b):
    rf, rs = L.P("stud_fl_d") / 2, L.P("stud_d") / 2
    zt = L.P("Z_SHEET_BACK") + L.P("stud_fl_k")
    fl, sh = [], []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        g = f.geometry
        if g.surfaceType == ST.CylinderSurfaceType:
            if abs(g.radius * 10 - rf) < 1e-3:
                fl.append(f)
            elif abs(g.radius * 10 - rs) < 1e-3:
                sh.append(f)
        elif g.surfaceType == ST.PlaneSurfaceType and abs(f.pointOnFace.z * 10 - zt) < 1e-4:
            fl.append(f)
    return fl, sh


def cb_faces(fr, x, y, floor):
    """frame faces of the counterbore at (x, y): walls, floor round, floor (by plan distance and Z band)"""
    zs = L.P("Z_SHEET_BACK")
    zf = zs + floor
    out = {"wall": [], "floor_round": [], "floor": []}
    for i in range(fr.faces.count):
        f = fr.faces.item(i)
        bb = f.boundingBox
        cx, cy = (bb.minPoint.x + bb.maxPoint.x) * 5, -(bb.minPoint.y + bb.maxPoint.y) * 5
        if math.hypot(cx - x, cy - y) > 5.5:
            continue
        z0, z1 = bb.minPoint.z * 10, bb.maxPoint.z * 10
        if z0 < zs - 1e-3 or z1 > zf + 1e-3:
            continue
        t = f.geometry.surfaceType
        if t == ST.PlaneSurfaceType and abs(z1 - z0) < 1e-4 and abs(z0 - zf) < 1e-3:
            out["floor"].append(f)
        elif z0 > zf - L.P("cb_r") - 1e-3:
            out["floor_round"].append(f)
        elif z1 - z0 > 0.2:
            out["wall"].append(f)
    return out


def dmin(fs1, fs2):
    best = None
    for a in fs1:
        for b in fs2:
            d, p1, p2 = L.min_dist_mm(a, b)
            if best is None or d < best[0]:
                best = (d, p1, p2)
    return None if best is None else {"d_mm": round(best[0], 4), "p_stud": L.pt_abs(best[1]),
                                      "p_frame": L.pt_abs(best[2])}


def shank_gap(sh, fr):
    return min(L.min_dist_mm(f, fr)[0] for f in sh)


def move(o, dx, dy):
    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(dx / 10.0, -dy / 10.0, 0)
    o.transform2 = m


def extreme(o, b, fr, fx, fy, ux, uy, floor):
    fl, sh = stud_faces(b)
    cbf = cb_faces(fr, fx, fy, floor)
    res = {"faces": {k: len(v) for k, v in cbf.items()}, "flange_faces": len(fl), "shank_faces": len(sh)}
    move(o, 0, 0)
    res["centred"] = {g: dmin(fl, cbf[g]) for g in cbf}
    res["centred"]["shank_to_frame"] = round(shank_gap(sh, fr), 4)
    for name, ang in DIRS:
        a = math.radians(ang)
        dx = ux * math.cos(a) - uy * math.sin(a)
        dy = uy * math.cos(a) + ux * math.sin(a)
        lo, hi = 0.0, 2.2
        for _ in range(14):
            mid = (lo + hi) / 2
            move(o, mid * dx, mid * dy)
            if shank_gap(sh, fr) >= 0.002:
                lo = mid
            else:
                hi = mid
        move(o, lo * dx, lo * dy)
        r = {"offset_mm": round(lo, 4), "shank_to_frame": round(shank_gap(sh, fr), 4),
             "stud_frame_overlap_mm3": L.overlap_volume_mm3(b, fr)}
        for g in cbf:
            r["flange_to_" + g] = dmin(fl, cbf[g])
        res[name] = r
    move(o, 0, 0)
    return res


def tape_over_air(fr, fx, fy):
    tb = adsk.fusion.TemporaryBRepManager.get()
    zs, zf = L.P("Z_SHEET_BACK"), L.P("Z_FLANGE_FRONT")
    c = adsk.core.Point3D.create(fx / 10, -fy / 10, (zs + zf) / 20)
    box = tb.createBox(adsk.core.OrientedBoundingBox3D.create(c, adsk.core.Vector3D.create(1, 0, 0),
                                                               adsk.core.Vector3D.create(0, 1, 0), 2.0, 2.0,
                                                               (zf - zs) / 10 + 0.02))
    foot = 0.0
    contact = 0.0
    for cn, bn, b, v in A.parts():
        if cn != "VHB tape strips":
            continue
        piece = tb.copy(b)
        if not tb.booleanOperation(piece, tb.copy(box), adsk.fusion.BooleanTypes.IntersectionBooleanType):
            continue
        if piece.volume <= 0:
            continue
        foot += piece.volume * 1000 / L.P("t_gap")
        sh = tb.copy(piece)
        m = adsk.core.Matrix3D.create()
        m.translation = adsk.core.Vector3D.create(0, 0, 0.002)
        tb.transform(sh, m)
        if tb.booleanOperation(sh, tb.copy(fr), adsk.fusion.BooleanTypes.IntersectionBooleanType):
            contact += sh.volume * 1000 / 0.02
    return round(foot, 2), round(contact, 2), round(foot - contact, 2)


def run(_context: str):
    d = L.check_doc()
    ups = d.userParameters
    fr = A.frame()
    out = {"flange": "%s x %s (temporary)" % (FL_D, FL_K), "cb": [L.P("cb_w"), L.P("cb_l")], "studs": {}}
    ups.itemByName("stud_fl_d").expression = "%s mm" % FL_D
    ups.itemByName("stud_fl_k").expression = "%s mm" % FL_K
    d.computeAll()
    try:
        for k, cn, fl in STUDS:
            o = L.occ_by_comp(cn)
            b = A.part(cn, "Weld stud M4x16 F%d" % k)
            ux, uy = L.P("f%d_ux" % k), L.P("f%d_uy" % k)
            out["studs"]["F%d" % k] = extreme(o, b, fr, L.P("f%d_x" % k), L.P("f%d_y" % k), ux, uy, L.P(fl))
            L.log("63 F%d done" % k)
    finally:
        if d.snapshots.hasPendingSnapshot:
            d.snapshots.revertPendingSnapshot()
        ups.itemByName("stud_fl_d").expression = "5.5 mm"
        ups.itemByName("stud_fl_k").expression = "0.7 mm"
        d.computeAll()
    zf_off = L.P("Z_FLANGE_FRONT") - L.P("Z_SHEET_BACK")
    t = math.tan(math.radians(L.P("draft")))
    tape = {}
    for k in ((5, 6, 7, 8) if TAPE else ()):
        foot, contact, air = tape_over_air(fr, L.P("f%d_x" % k), L.P("f%d_y" % k))
        tape["F%d" % k] = {"tape_footprint_in_box_mm2": foot, "bonded_mm2": contact, "over_air_mm2": air}
    if TAPE:
        tape["reference_at_flange_front"] = {
            "slot_5.4x7.0_GF-1.0_mm2": round(stadium_area(L.P("slot_w"), L.P("slot_l")), 2),
            "cb_7.2x8.8_mm2": round(stadium_area(7.2 - 2 * zf_off * t, 8.8 - 2 * zf_off * t), 2),
            "cb_now_mm2": round(stadium_area(L.P("cb_w") - 2 * zf_off * t, L.P("cb_l") - 2 * zf_off * t), 2)}
        tape["lost_vs_GF-1.0_total_mm2"] = round(sum(tape["F%d" % k]["over_air_mm2"] for k in (5, 6, 7, 8)) -
                                                 4 * tape["reference_at_flange_front"]["slot_5.4x7.0_GF-1.0_mm2"], 2)
        out["tape_F5-F8"] = tape
    out["after"] = {"pending": d.snapshots.hasPendingSnapshot, "stud_fl_d": L.P("stud_fl_d"),
                    "stud_fl_k": L.P("stud_fl_k"), "health": L.timeline_health()[1]}
    p = os.path.join(L.SCR, "gf11", OUT)
    json.dump(out, open(p, "w"), indent=1)
    L.log("63 written %s; after %s" % (p, out["after"]))
    print(p, out["after"])
