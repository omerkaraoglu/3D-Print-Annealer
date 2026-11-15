"""22 - carried-over geometry check against frame v2 (brief requirement 5): imports
Mechanical/Rev3.0_Frame/Rev3.0_Frame_v2.step into a TEMPORARY occurrence of this document, measures the same
features on both bodies, writes scratchpad carry_measure.json + carry_sections.json, then DELETES the temporary
occurrence again (checked: timeline count and component list restored). Nothing is saved while it exists.
Measured on both bodies:
  * every cone face coaxial with an ear hole H1-H9: radius at its top / bottom, half angle, Z range
    (boss dia 8.0 at Z 0, pilot 2.4 at Z 0 + 0.5 deg, relief 3.2 x 0.5) + the pilot floor level
  * flat faces at Z_SEAT / Z_SHELF_BACK / Z_PCB / Z_TROUGH_TOP (levels present)
  * plan sections at Z -1.0 (support ribs, walls, bosses above their root fillets), -3.35 (shelf / window),
    +2.0 (tail-pocket walls above Z 0) with comparison boxes (offline: gf_offline_checks.py carry)."""
import importlib
import json
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

V2_STEP = r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Mechanical\Rev3.0_Frame\Rev3.0_Frame_v2.step"
EARS = [("H%d" % i, "h%d_x" % i, "h%d_y" % i) for i in range(1, 10)]
ZS = [-1.0, -3.35, 2.0]


def coax_cones(b, x, y):
    out = []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        g = f.geometry
        if g.surfaceType != adsk.core.SurfaceTypes.ConeSurfaceType:
            continue
        o, ax = g.origin, g.axis
        if abs(abs(ax.z) / ax.length - 1) > 1e-6 or math.hypot(o.x * 10 - x, o.y * 10 + y) > 0.02:
            continue
        pts = []
        for k in range(f.edges.count):
            e = f.edges.item(k)
            ev = e.evaluator
            ok, p0, p1 = ev.getParameterExtents()
            ok, st = ev.getStrokes(p0, p1, 0.0002)
            for p in (st if ok else []):
                pts.append((p.z * 10, math.hypot(p.x * 10 - x, p.y * 10 + y)))
        if not pts:
            continue
        zt, zb = max(p[0] for p in pts), min(p[0] for p in pts)
        rt = [p[1] for p in pts if abs(p[0] - zt) < 1e-4]
        rb = [p[1] for p in pts if abs(p[0] - zb) < 1e-4]
        out.append({"half_angle_deg": round(math.degrees(g.halfAngle), 4), "z_top": round(zt, 4), "z_bot": round(zb, 4),
                    "r_top_max": round(max(rt), 4), "r_top_min": round(min(rt), 4), "r_bot_max": round(max(rb), 4)})
    return sorted(out, key=lambda c: c["r_top_max"])


def pilot_floor(b, x, y):
    zs = []
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        bb = f.boundingBox
        cx, cy = (bb.minPoint.x + bb.maxPoint.x) * 5, -(bb.minPoint.y + bb.maxPoint.y) * 5
        if math.hypot(cx - x, cy - y) < 0.05 and (bb.maxPoint.x - bb.minPoint.x) * 10 < 3.0 and \
                abs(bb.maxPoint.z - bb.minPoint.z) < 1e-6:
            zs.append(round(bb.minPoint.z * 10, 4))
    return sorted(zs)


def flat_levels(b):
    lv = {}
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if abs(n.z) < 0.99999:
            continue
        z = round(f.boundingBox.minPoint.z * 10, 3)
        key = "%+.3f %s" % (z, "+Z" if n.z > 0 else "-Z")
        lv[key] = round(lv.get(key, 0) + f.area * 100, 2)
    return lv


def section(b, z_mm):
    ns = {"__name__": "gf_21"}
    P = L.GF_DIR + r"\21_sections_dump.py"
    exec(compile(open(P, encoding="utf-8").read(), P, "exec"), ns)
    return ns["section"](b, z_mm)


def boxes():
    bx = []
    wall_v2 = {"T": 18.75, "B": 119.25, "L": 19.77, "R": 185.17}      # v2 pocket (wall inner face) at Z_SEAT
    for k in range(1, 27):
        x0, x1, y0, y1 = [L.ev(e) for e in L.rib_exprs(k)]
        side = L.RIBS_V1[k - 1][4]
        if side == "T":
            b_ = (x0 - 0.4, wall_v2["T"] + 0.4, x1 + 0.4, L.P("win_y0") - 0.4)
        elif side == "B":
            b_ = (x0 - 0.4, L.P("win_y1") + 0.4, x1 + 0.4, min(wall_v2["B"], L.P("panel_y1")) - 0.4)
        elif side == "L":
            b_ = (wall_v2["L"] + 0.4, y0 - 0.4, L.P("win_x0") - 0.4, y1 + 0.4)
        else:
            b_ = (L.P("win_x1") + 0.4, y0 - 0.4, wall_v2["R"] - 0.4, y1 + 0.4)
        bx.append(("support rib %d (%s)" % (k, side), [round(v, 4) for v in b_]))
    for name, xe, ye in EARS:
        x, y = L.P(xe), L.P(ye)
        bx.append(("pilot %s (dia 4 box)" % name, [x - 2, y - 2, x + 2, y + 2]))
    w = [L.P(n) for n in ("win_x0", "win_y0", "win_x1", "win_y1")]
    bx += [("window edge left", [w[0] - 0.5, w[1] + 2, w[0] + 0.5, w[3] - 2]),
           ("window edge right", [w[2] - 0.5, w[1] + 2, w[2] + 0.5, w[3] - 2]),
           ("window edge top", [w[0] + 2, w[1] - 0.5, w[2] - 2, w[1] + 0.5]),
           ("window edge bottom", [w[0] + 2, w[3] - 0.5, w[2] - 2, w[3] + 0.5]),
           ("tail wall left above Z0 (y 129.5..147)", [35.5, 129.5, 40.5, 147.0]),
           ("tail wall right above Z0 (y 129.5..147)", [166.0, 129.5, 171.0, 147.0])]
    return bx


def run(_context: str):
    L.check_doc()
    L.log("=== 22 start")
    d = L.des()
    r = L.root()
    tl = d.timeline
    n0, occ0 = tl.count, r.occurrences.count
    im = L.app().importManager
    opt = im.createSTEPImportOptions(V2_STEP)
    ok = im.importToTarget(opt, r)
    if not ok or r.occurrences.count != occ0 + 1:
        raise RuntimeError("STEP import failed (%s, occurrences %d)" % (ok, r.occurrences.count))
    tmp = r.occurrences.item(r.occurrences.count - 1)
    tmp_bodies = []
    for i in range(tmp.bRepBodies.count):
        tmp_bodies.append(tmp.bRepBodies.item(i))
    for j in range(tmp.childOccurrences.count):
        o = tmp.childOccurrences.item(j)
        for i in range(o.bRepBodies.count):
            tmp_bodies.append(o.bRepBodies.item(i))
    if len(tmp_bodies) != 1:
        raise RuntimeError("v2 STEP: %d bodies" % len(tmp_bodies))
    v2 = tmp_bodies[0]
    gf = L.body()
    meas = {"v2_step": V2_STEP, "v2_volume_cm3": round(v2.volume, 4), "gf_volume_cm3": round(gf.volume, 4), "bosses": {}}
    for name, xe, ye in EARS:
        x, y = L.P(xe), L.P(ye)
        meas["bosses"][name] = {"xy": [x, y], "gf_cones": coax_cones(gf, x, y), "v2_cones": coax_cones(v2, x, y),
                                "gf_pilot_floor_z": pilot_floor(gf, x, y), "v2_pilot_floor_z": pilot_floor(v2, x, y)}
    meas["flat_levels_gf"] = flat_levels(gf)
    meas["flat_levels_v2"] = flat_levels(v2)
    secs = {"levels": {}}
    bx = boxes()
    for z in ZS:
        secs["levels"]["%.3f" % z] = {"gf": section(gf, z), "v2": section(v2, z), "boxes": bx}
    L.dump(meas, "carry_measure.json")
    L.dump(secs, "carry_sections.json")
    # remove the temporary occurrence and its component
    tmp.deleteMe()
    n1, bad = L.timeline_health()
    comps = [d.allComponents.item(i).name for i in range(d.allComponents.count)]
    L.log("22 v2 vol %.4f gf vol %.4f; timeline %d -> %d (now %d), occurrences %d, components %s, unhealthy %s" % (
        meas["v2_volume_cm3"], meas["gf_volume_cm3"], n0, n0, n1, r.occurrences.count, comps, bad))
    print(meas["v2_volume_cm3"], meas["gf_volume_cm3"], n0, n1, r.occurrences.count, comps, bad)
