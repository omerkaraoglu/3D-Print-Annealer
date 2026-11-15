"""24 - READ-ONLY dimension check of the built body against the master JSON: material transitions found by
point-containment bisection (1e-4 mm) along probe lines, compared with the expected values (draft offsets
included), plus the flat-face levels. -> scratchpad dimcheck.json."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

IN = adsk.fusion.PointContainment.PointInsidePointContainment


def inside(b, x, y, z):
    return b.pointContainment(adsk.core.Point3D.create(x / 10.0, -y / 10.0, z / 10.0)) == IN


def transitions(b, p0, p1, z, step=0.05):
    """material boundaries along the segment p0 -> p1 (abs x, y-down) at height z: list of t (mm from p0)"""
    L_ = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    ux, uy = (p1[0] - p0[0]) / L_, (p1[1] - p0[1]) / L_
    n = int(L_ / step)
    out = []
    prev = inside(b, p0[0], p0[1], z)
    for k in range(1, n + 1):
        t = k * L_ / n
        cur = inside(b, p0[0] + ux * t, p0[1] + uy * t, z)
        if cur != prev:
            a, c = t - L_ / n, t
            while c - a > 1e-4:
                m = (a + c) / 2
                if inside(b, p0[0] + ux * m, p0[1] + uy * m, z) == prev:
                    a = m
                else:
                    c = m
            out.append(round((a + c) / 2, 4))
        prev = cur
    return out


def run(_context: str):
    L.check_doc()
    b = L.body()
    k = math.tan(math.radians(L.P("draft")))
    kl = math.tan(math.radians(L.P("draft_loc")))
    P = L.P
    gx0 = P("glass_x0")
    res = {"probes": []}

    def probe(name, p0, p1, z, expect):
        t = transitions(b, p0, p1, z)
        L_ = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        ux, uy = (p1[0] - p0[0]) / L_, (p1[1] - p0[1]) / L_
        pts = [round(p0[0] + ux * s, 4) if abs(ux) > 0.5 else round(p0[1] + uy * s, 4) for s in t]
        res["probes"].append({"name": name, "z": round(z, 4), "found": pts, "expected": [round(e, 4) for e in expect],
                              "max_dev": round(max(abs(a - e) for a, e in zip(pts, expect)), 4)
                              if len(pts) == len(expect) else "count %d vs %d" % (len(pts), len(expect))})

    y = 60.0
    zgf, zsb, zff, zfb, zl = P("Z_GLASS_FRONT"), P("Z_SHEET_BACK"), P("Z_FLANGE_FRONT"), P("Z_FLANGE_BACK"), P("Z_LAND")
    # lip at mid height: outer face (lip_out at the root), inner face (lip_in at the top)
    z = zgf + 0.5
    probe("lip (left side, y 60): outer / inner face", (5.0, y), (16.0, y), z,
          [gx0 - P("s_lip_out") + (zsb - z) * k, gx0 - P("s_lip_in") + (z - zgf) * k])
    z = zsb + 0.3
    probe("seat ring + step wall (y 60): outer face / recess wall", (5.0, y), (16.0, y), z,
          [gx0 - P("s_ring") + (zff - z) * k, gx0 - P("s_lip_in") + (z - zgf) * k])
    z = zff + 0.3
    probe("flange front zone (y 60): flange edge / recess wall", (-12.0, y), (16.0, y), z,
          [P("fl_x0") + (z - zff) * k, gx0 - P("s_lip_in") + (z - zgf) * k])
    z = zl + 0.3
    probe("land plate zone (y 60): flange edge / clearance pocket face", (-12.0, y), (25.0, y), z,
          [P("fl_x0") + (z - zff) * k, P("pocket_x0") - (P("Z_SEAT") - z) * k])
    z = (zfb + P("Z_STEPWALL_BACK")) / 2
    probe("step wall back zone (y 60): step-wall B face / pocket face", (5.0, y), (25.0, y), z,
          [gx0 - P("s_ring") + (z - zfb) * k, P("pocket_x0") - (P("Z_SEAT") - z) * k])
    # slots at the flange front (F8 along x, across y; F1 along its radial axis)
    z = zff + 0.01
    f8x, f8y = P("f8_x"), P("f8_y")
    probe("F8 slot length at the flange front (along x)", (f8x - 6, f8y), (f8x + 6, f8y), z,
          [f8x - P("slot_l") / 2 + 0.01 * kl, f8x + P("slot_l") / 2 - 0.01 * kl])
    probe("F8 slot width at the flange front (along y)", (f8x, f8y - 6), (f8x, f8y + 6), z,
          [f8y - P("slot_w") / 2 + 0.01 * kl, f8y + P("slot_w") / 2 - 0.01 * kl])
    f1x, f1y, ux, uy = P("f1_x"), P("f1_y"), P("f1_ux"), P("f1_uy")
    probe("F1 slot length along its radial axis (t from -6)", (f1x - 6 * ux, f1y - 6 * uy), (f1x + 6 * ux, f1y + 6 * uy),
          z, [f1x + (-P("slot_l") / 2) * ux, f1x + (P("slot_l") / 2) * ux])
    # tail pocket at the land, mid x
    z = zl + 0.05
    probe("tail pocket bottom face at the land (x 103.85; the top side opens into the clearance pocket)",
          (103.85, 110.0), (103.85, 152.0), z, [P("tr_y1") + 0.05 * k])
    # flat face levels
    lv = {}
    for i in range(b.faces.count):
        f = b.faces.item(i)
        if f.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        if abs(n.z) < 0.99999:
            continue
        key = "%+.3f %s" % (f.boundingBox.minPoint.z * 10, "+Z" if n.z > 0 else "-Z")
        lv[key] = round(lv.get(key, 0) + f.area * 100, 2)
    res["flat_face_levels_mm2"] = lv
    p = L.dump(res, "dimcheck.json")
    for r in res["probes"]:
        print(r["name"], r["found"], r["expected"], r["max_dev"])
    print(sorted(lv.items()))
