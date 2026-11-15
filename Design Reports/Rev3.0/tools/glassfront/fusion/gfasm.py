"""gfasm - stage 2 assembly helpers (imported by the 39+ check / render scripts, next to gflib).
Body proxies in the root context, grouped by component; board bodies with their occurrence path."""
import importlib
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

PART_COMPS = ["Glass", "Optical bond", "Formex sheet", "Bead", "VHB tape strips", "Oven sheet", "Weld studs S4 F1-F4",
              "Washers + nyloc nuts S4 F1-F4", "Rivets R4 F1-F4 (hidden)", "Weld studs S8 F5-F8 (hidden)",
              "Washers, nuts, spacers S8 F5-F8 (hidden)", L.CHECK_COMP]
VARIANT = {"Rivets R4 F1-F4 (hidden)": "R4", "Weld studs S8 F5-F8 (hidden)": "S8",
           "Washers, nuts, spacers S8 F5-F8 (hidden)": "S8", L.CHECK_COMP: "check", "Oven sheet R4 (rivet holes)": "R4"}


def frame():
    o = L.occ_by_comp(L.COMP_NAME)
    return o.bRepBodies.item(0)


def parts():
    """[(component, body name, body proxy, variant)] variant = 'S4' (default assembly), 'R4', 'S8', 'check'"""
    out = []
    for cn in PART_COMPS:
        o = L.occ_by_comp(cn)
        for i in range(o.bRepBodies.count):
            b = o.bRepBodies.item(i)
            v = VARIANT.get(b.name, VARIANT.get(cn, "S4"))
            out.append((cn, b.name, b, v))
    return out


def part(cn, bn):
    o = L.occ_by_comp(cn)
    for i in range(o.bRepBodies.count):
        if o.bRepBodies.item(i).name == bn:
            return o.bRepBodies.item(i)
    raise RuntimeError("no body %s / %s" % (cn, bn))


def board():
    """[(path, body proxy)] every body under the board occurrence (root context)"""
    return L.bodies_under(L.occ_by_comp(L.BOARD_COMP))


def is_ds1(path):
    return "TFT7" in path


def ds1_part(path):
    """DS1 sub-part name from the occurrence path (lcm_0, pu_tape_1, sensor_2, cover_print_3, cover_va_4,
    tft_tail_5, tft_fingers_6, ctp_tail_7, ctp_fingers_8)"""
    return path.split("+")[-1].split(":")[0] if is_ds1(path) else None


def bbox_gap(b1, b2):
    a, c = b1.boundingBox, b2.boundingBox
    g = [max(a.minPoint.x - c.maxPoint.x, c.minPoint.x - a.maxPoint.x, 0),
         max(a.minPoint.y - c.maxPoint.y, c.minPoint.y - a.maxPoint.y, 0),
         max(a.minPoint.z - c.maxPoint.z, c.minPoint.z - a.maxPoint.z, 0)]
    return math.sqrt(sum(v * v for v in g)) * 10.0


def pair(b1, b2, with_overlap=True, tol=0.001):
    d, p1, p2 = L.min_dist_mm(b1, b2)
    r = {"d_mm": round(d, 4), "p1": L.pt_abs(p1), "p2": L.pt_abs(p2)}
    if with_overlap and d < tol:
        v = L.overlap_volume_mm3(b1, b2)
        r["overlap_mm3"] = round(v, 5) if v is not None else None
    return r
