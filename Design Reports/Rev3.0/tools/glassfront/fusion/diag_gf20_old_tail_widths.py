"""diag_gf20_old_tail_widths - READ-ONLY: x extent of the GF-1.1 / DS1 tail bodies (tft_tail_5, ctp_tail_7 and the
finger bodies) in thin slices along y, separately for the front leg (Z < -3) and the return leg (Z > 0), with the
developed length v of the old flat-and-loop route at each slice (front leg v = y - 119.0; return leg
v = leg + pi R + (y_c - y), loop centre / radius from the slice bboxes). Writes gf20/old_tail_widths.json."""
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

TB = adsk.fusion.TemporaryBRepManager.get()


def box(x0, x1, y0, y1, z0, z1):
    c = adsk.core.Point3D.create((x0 + x1) / 20.0, -(y0 + y1) / 20.0, (z0 + z1) / 20.0)
    ob = adsk.core.OrientedBoundingBox3D.create(c, adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
                                                (x1 - x0) / 10.0, (y1 - y0) / 10.0, (z1 - z0) / 10.0)
    return TB.createBox(ob)


def slice_x(b, y, z0, z1, dy=0.1):
    t = TB.copy(b)
    bx = box(0, 220, y - dy / 2, y + dy / 2, z0, z1)
    ok = TB.booleanOperation(t, bx, adsk.fusion.BooleanTypes.IntersectionBooleanType)
    if not ok or t.volume < 1e-9:
        return None
    bb = t.boundingBox
    return [round(bb.minPoint.x * 10, 3), round(bb.maxPoint.x * 10, 3), round(bb.minPoint.z * 10, 3),
            round(bb.maxPoint.z * 10, 3)]


def run(_context: str):
    L.check_doc()
    ds = {A.ds1_part(p): b for p, b in A.board() if A.is_ds1(p)}
    out = {}
    for nm in ("tft_tail_5", "ctp_tail_7", "tft_fingers_6", "ctp_fingers_8"):
        b = ds[nm]
        e = {"bbox": L.bbox_mm(b), "front_leg": {}, "return_leg": {}}
        bb = L.bbox_mm(b)
        y = math.floor(bb[2]) + 0.25
        while y < bb[3]:
            f = slice_x(b, y, -12, -3)
            r = slice_x(b, y, 0, 5)
            if f:
                e["front_leg"]["%.2f" % y] = f
            if r:
                e["return_leg"]["%.2f" % y] = r
            y += 0.5
        out[nm] = e
    p = os.path.join(L.SCR, "gf20", "old_tail_widths.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=0)
    print(p)
