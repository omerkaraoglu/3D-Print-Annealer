"""v2.1 support-rib extension check (coordinator item 4).

Each of the 26 v1 support ribs (frame.py support_ribs(), same x/y position and width) gets its free end(s)
extended so the end is trimmed by the cut that bounds it: the inner end runs to the shelf edge (seat_w inside
the panel outline: the Window cut trims it flush on the drafted window face); the outer end of the six ribs over
the tail pocket runs to the shelf end (panel bottom edge, y 119.0: the Tail-pocket cut trims it). A rib keeps
its v1 length when the extended rectangle comes closer than 1.0 mm to any B.Cu pad polygon (same 2D test as
v1 fitcheck.plan_checks: distance from the rib rectangle to the pad polygon points).
Also recomputes the mains copper -> frame contact distance and the creepage / clearance of v1's method for the
final rib set (the shelf land beyond the rib end, SEAT_W - PCB_RIM_W, becomes 0 for extended ribs).

Writes rib_pad_result.json next to this file.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GEOM = os.path.join(HERE, "out", "board_geom.json")
import importlib.util
spec = importlib.util.spec_from_file_location("fv2lib_ribs", os.path.join(HERE, "fusion", "fv2lib.py"))

PANEL = (20.02, 184.92, 19.00, 119.00)
POCKET_CLR, SEAT_W, PCB_RIM_W, RIB_BURY = 0.25, 2.6, 2.1, 0.5
SHEET_INSET, SHELF_T = 0.5, 2.5
Z_PCB, Z_SEAT, Z_SHELF_BACK = 0.0, -4.6, -2.1
TR_X0, TR_X1 = 39.2, 167.4
PAD_MIN = 1.0
HOLES = {"H1": (30.0, 14.2), "H2": (93.0, 14.2), "H3": (174.0, 14.2), "H4": (189.8, 30.0), "H5": (189.8, 109.0),
         "H6": (175.0, 123.8), "H7": (30.0, 123.8), "H8": (15.2, 109.0), "H9": (15.2, 30.0)}
BOSS_OD = 8.0
# v1 ribs (x0, x1, y0, y1, side) - same list as fusion/fv2lib.RIBS
RIBS = [
    (27.27, 28.77, 18.65, 21.1, "T"), (48.54142857142857, 50.04142857142857, 18.65, 21.1, "T"),
    (65.56285714285714, 67.06285714285714, 18.65, 21.1, "T"), (91.0842857142857, 92.5842857142857, 18.65, 21.1, "T"),
    (110.10571428571427, 111.60571428571427, 18.65, 21.1, "T"),
    (133.62714285714284, 135.12714285714284, 18.65, 21.1, "T"),
    (154.89857142857142, 156.39857142857142, 18.65, 21.1, "T"), (176.17, 177.67, 18.65, 21.1, "T"),
    (27.27, 28.77, 116.9, 119.35, "B"), (48.54142857142857, 50.04142857142857, 116.9, 118.5, "B"),
    (69.81285714285714, 71.31285714285714, 116.9, 118.5, "B"), (91.0842857142857, 92.5842857142857, 116.9, 118.5, "B"),
    (112.35571428571428, 113.85571428571428, 116.9, 118.5, "B"),
    (133.62714285714284, 135.12714285714284, 116.9, 118.5, "B"),
    (154.89857142857142, 156.39857142857142, 116.9, 118.5, "B"), (176.17, 177.67, 116.9, 119.35, "B"),
    (19.67, 22.12, 26.25, 27.75, "L"), (19.67, 22.12, 47.25, 48.75, "L"), (19.67, 22.12, 68.25, 69.75, "L"),
    (19.67, 22.12, 89.25, 90.75, "L"), (19.67, 22.12, 110.25, 111.75, "L"),
    (182.82, 185.27, 26.25, 27.75, "R"), (182.82, 185.27, 47.25, 48.75, "R"), (182.82, 185.27, 68.25, 69.75, "R"),
    (182.82, 185.27, 89.25, 90.75, "R"), (182.82, 185.27, 110.25, 111.75, "R"),
]


def rect_pt(px, py, r):
    x0, x1, y0, y1 = r
    return math.hypot(max(x0 - px, 0, px - x1), max(y0 - py, 0, py - y1))


def v1_full(r):
    """v1 rectangle with the wall end buried rib_bury (as built in v2.0)"""
    x0, x1, y0, y1, s = r
    px0, px1, py0, py1 = PANEL[0] - POCKET_CLR, PANEL[1] + POCKET_CLR, PANEL[2] - POCKET_CLR, PANEL[3] + POCKET_CLR
    if s == "T":
        y0 = py0 - RIB_BURY
    elif s == "B" and y1 > py1:
        y1 = py1 + RIB_BURY
    elif s == "L":
        x0 = px0 - RIB_BURY
    elif s == "R":
        x1 = px1 + RIB_BURY
    return [x0, x1, y0, y1]


def extended(r):
    """plan rectangle reaching the shelf edge (and the shelf end over the tail pocket)"""
    x0, x1, y0, y1 = v1_full(r)
    s = r[4]
    if s == "T":
        y1 = PANEL[2] + SEAT_W
    elif s == "B":
        y0 = PANEL[3] - SEAT_W
        if TR_X0 < x0 and x1 < TR_X1:
            y1 = PANEL[3]                      # over the tail pocket: to the shelf end (panel bottom edge)
    elif s == "L":
        x1 = PANEL[0] + SEAT_W
    elif s == "R":
        x0 = PANEL[1] - SEAT_W
    return [x0, x1, y0, y1]


def main():
    d = json.load(open(GEOM))
    pads = [("%s.%s" % (p["ref"], p["num"]), p["mains"], [q for poly in p["poly"] for q in poly])
            for p in d["pads"] if p["on_bcu"] and p["attr"] != "NPTH" and p["poly"]]
    rows, final = [], []
    for k, r in enumerate(RIBS):
        ext = extended(r)
        v1 = v1_full(r)
        dmin, who = min((min(rect_pt(px, py, ext) for px, py in pts), n) for n, m, pts in pads)
        dv1, whov1 = min((min(rect_pt(px, py, v1) for px, py in pts), n) for n, m, pts in pads)
        use_ext = dmin >= PAD_MIN
        rect = ext if use_ext else v1
        final.append(rect + [r[4]])
        reach = {"T": rect[3] - PANEL[2], "B": PANEL[3] - rect[2], "L": rect[1] - PANEL[0], "R": PANEL[1] - rect[0]}[r[4]]
        rows.append({"rib": k + 1, "side": r[4], "x0": round(rect[0], 4), "x1": round(rect[1], 4),
                     "y0": round(rect[2], 4), "y1": round(rect[3], 4), "extended": use_ext,
                     "reach_inside_panel_outline_mm": round(reach, 3),
                     "tail_pocket_end_to_shelf_end": bool(use_ext and r[4] == "B" and TR_X0 < rect[0] and rect[1] < TR_X1),
                     "pad_min_extended_mm": round(dmin, 3), "pad_extended": who,
                     "pad_min_v1_mm": round(dv1, 3), "pad_v1": whov1})
    # minimum over the final set
    best = min((min(rect_pt(px, py, f[:4]) for px, py in pts), n, i + 1)
               for n, m, pts in pads for i, f in enumerate(final))
    # mains copper -> frame contact (ribs + bosses), v1 method
    mains_pts = [(n, pts) for n, m, pts in pads if m]
    for mm in d["mains_bcu"]:
        mains_pts.append((mm["net"] + " " + mm["kind"], [q for poly in mm["poly"] for q in poly]))
    mbest = (1e9, None, None)
    for name, pts in mains_pts:
        for i, f in enumerate(final):
            v = min(rect_pt(px, py, f[:4]) for px, py in pts)
            if v < mbest[0]:
                mbest = (v, name, "rib %d (%s, %s)" % (i + 1, f[4], "extended" if rows[i]["extended"] else "v1"))
        for h, (hx, hy) in HOLES.items():
            v = min(math.hypot(px - hx, py - hy) for px, py in pts) - BOSS_OD / 2
            if v < mbest[0]:
                mbest = (v, name, "boss " + h)
    land = 0.0 if "extended" in (mbest[2] or "") else SEAT_W - PCB_RIM_W
    creep = mbest[0] + (Z_PCB - Z_SHELF_BACK) + land + SHELF_T + (SEAT_W - SHEET_INSET)
    worst = 1e9
    for name, pts in mains_pts:
        for px, py in pts:
            e = min(px - PANEL[0], PANEL[1] - px, py - PANEL[2], PANEL[3] - py)
            if e < 0 or e > 15:
                continue
            worst = min(worst, math.hypot(abs(e - SEAT_W), Z_PCB - Z_SEAT) + (SEAT_W - SHEET_INSET))
    out = {"pad_min_required_mm": PAD_MIN, "ribs": rows,
           "kept_v1_length": [r["rib"] for r in rows if not r["extended"]],
           "rib_to_pad_min_mm": round(best[0], 3), "rib_to_pad_min_pad": best[1], "rib_to_pad_min_rib": best[2],
           "mains_to_frame_contact_min_mm": round(mbest[0], 3), "mains_to_frame_contact": [mbest[1], mbest[2]],
           "creepage_mains_to_panel_mm": round(creep, 2), "creepage_req_mm": 6.4,
           "clearance_mains_to_panel_mm": round(worst, 2), "clearance_req_mm": 4.0,
           "note": "creepage = d(mains copper, contact) + rib side 2.1 + shelf land beyond the rib end "
                   "(0 when the nearest rib is extended, 0.5 for a v1-length rib) + shelf inner face 2.5 + "
                   "shelf/sheet interface 2.1"}
    json.dump(out, open(os.path.join(HERE, "rib_pad_result.json"), "w"), indent=1)
    for r in rows:
        print("rib %2d %s ext %-5s reach %.2f  pad ext %.3f (%s)  v1 %.3f (%s)" % (
            r["rib"], r["side"], r["extended"], r["reach_inside_panel_outline_mm"], r["pad_min_extended_mm"],
            r["pad_extended"], r["pad_min_v1_mm"], r["pad_v1"]))
    print("kept v1:", out["kept_v1_length"], "| min rib-pad %.3f %s (rib %d)" % best,
          "| mains->contact %.3f %s %s" % mbest, "| creepage %.2f clearance %.2f" % (creep, worst))


if __name__ == "__main__":
    main()
