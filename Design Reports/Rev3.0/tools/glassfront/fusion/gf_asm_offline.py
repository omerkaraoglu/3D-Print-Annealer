"""Stage 2 offline analysis (plain Python + shapely) of the dumps written by the 39-43 Fusion scripts into
%TEMP%\\rev3_glassfront. Usage: python gf_asm_offline.py [board|gaps|bearing|wires|all]
  board    fit_board.json (40)  -> board bodies mapped to KiCad refs (bbox centre in the courtyard / nearest
                                   footprint of board_geom.json), frame overlaps / nearest parts, DS1 sub-parts vs
                                   frame / glass / print / bead / bond / Formex, sockets vs board, Formex vs lead tips
  gaps     sections_asm.json (41) -> g2 glass edge -> recess wall, g1 lip outer face -> sheet cut-out, panel ->
                                   pocket faces, per side + corners, at several Z
  bearing  sections_asm.json      -> washer / backing-washer bearing area on the tube tops (annulus minus slot)
  wires    fit_board.json + board_geom -> nuts / sockets / studs vs the J20 / J2 wire corridors (plan) and models (3D)
Writes offline_asm_<check>.json next to the dumps and prints a summary."""
import json
import math
import os
import sys

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

SCR = r"C:\Users\lenovo\AppData\Local\Temp\rev3_glassfront"
BOARD = (r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame\out"
         r"\board_geom.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gf_offline_checks import level_material   # noqa: E402  (same loop -> polygon conversion as stage 1)


def load(n):
    return json.load(open(os.path.join(SCR, n)))


def dump(obj, n):
    json.dump(obj, open(os.path.join(SCR, n), "w"), indent=1)


def fp_index():
    g = json.load(open(BOARD))
    return g, [f for f in g["fps"]]


def ref_of(r, fps):
    """KiCad reference of a board body: DS1 sub-part, PCB, or the footprint whose courtyard holds the bbox centre
    (else the nearest footprint origin)"""
    if r["ds1"]:
        return "DS1." + r["ds1"]
    bb = r["bbox"]
    cx, cy = (bb[0] + bb[1]) / 2, (bb[2] + bb[3]) / 2
    if bb[1] - bb[0] > 150 and bb[3] - bb[2] > 100:
        return "PCB"
    best, bd = None, 1e9
    for f in fps:
        c = f.get("crtyd")
        if c and c[0] <= cx <= c[2] and c[1] <= cy <= c[3]:
            a = (c[2] - c[0]) * (c[3] - c[1])
            if a < bd:
                best, bd = f["ref"], a
    if best:
        return best
    return min(fps, key=lambda f: math.hypot(f["x"] - cx, f["y"] - cy))["ref"] + "?"


def check_board():
    d = load("fit_board.json")
    g, fps = fp_index()
    rows = []
    for r in d["results"]:
        r["ref"] = ref_of(r, fps)
        rows.append(r)
    out = {"n_bodies": len(rows)}
    fo = [r for r in rows if r["frame"]["d_mm"] < 0.001]
    out["frame_touching"] = [{"ref": r["ref"], "path": r["path"], "d": r["frame"]["d_mm"],
                              "overlap_mm3": r["frame"].get("overlap_mm3"), "p": r["frame"]["p1"]} for r in fo]
    srt = sorted(rows, key=lambda r: r["frame"]["d_mm"])
    out["frame_nearest_25"] = [{"ref": r["ref"], "d_mm": r["frame"]["d_mm"], "p_frame": r["frame"]["p1"],
                                "p_body": r["frame"]["p2"], "bbox": r["bbox"]} for r in srt[:25]]
    # DS1
    ds = {}
    for r in rows:
        if not r["ds1"]:
            continue
        e = {"bbox": r["bbox"], "frame": r["frame"]}
        for q in r["parts"]:
            e[q["part"]] = {k: q[k] for k in ("d_mm", "p1", "p2", "overlap_mm3") if k in q}
        ds[r["ds1"]] = e
    out["ds1"] = ds
    # parts vs board (non-DS1) touching or within 3
    pv = {}
    for r in rows:
        for q in r["parts"]:
            if q["d_mm"] < 3.0:
                pv.setdefault(q["part"], []).append({"ref": r["ref"], "d_mm": q["d_mm"],
                                                     "overlap_mm3": q.get("overlap_mm3"), "p_part": q["p1"],
                                                     "p_body": q["p2"], "variant": q["variant"]})
    for k in pv:
        pv[k].sort(key=lambda e: e["d_mm"])
    out["parts_within_3mm_of_board_bodies"] = pv
    # sockets: nearest board body per socket (all measured within 6 mm in bbox; else > 6)
    so = {}
    for r in rows:
        for q in r["parts"]:
            if q["variant"] == "check":
                s = q["part"].split(" / ")[1]
                if s not in so or q["d_mm"] < so[s]["d_mm"]:
                    so[s] = {"ref": r["ref"], "d_mm": q["d_mm"], "p_body": q["p2"]}
    out["sockets_nearest_board_body"] = so
    # Formex vs bodies reaching below Z -1 (lead tips)
    fx = []
    for r in rows:
        if r["bbox"][4] > -1.0 or r["ds1"]:
            continue
        q = [q for q in r["parts"] if q["part"].startswith("Formex")]
        fx.append({"ref": r["ref"], "zmin": r["bbox"][4], "d_formex": q[0]["d_mm"] if q else ">6 (bbox)",
                   "overlap_mm3": q[0].get("overlap_mm3") if q else None})
    out["formex_vs_lead_tips"] = sorted(fx, key=lambda e: e["d_formex"] if isinstance(e["d_formex"], float) else 99)
    # above Z 0 nothing of the frame inside the board: from stage 1 offline_abovez (23), unchanged
    dump(out, "offline_asm_board.json")
    print("bodies", len(rows), "frame touching", [(e["ref"], e["d"], e["overlap_mm3"]) for e in out["frame_touching"]])
    print("frame nearest:")
    for e in out["frame_nearest_25"][:25]:
        print("   %-26s %.4f frame %s body %s" % (e["ref"], e["d_mm"], e["p_frame"], e["p_body"]))
    print("DS1:")
    for k, e in ds.items():
        print("  ", k, "frame %.4f" % e["frame"]["d_mm"], e["frame"].get("overlap_mm3"),
              {kk: (v["d_mm"], v.get("overlap_mm3")) for kk, v in e.items() if kk not in ("bbox", "frame")})
    print("sockets:", so)
    print("Formex vs lead tips:", out["formex_vs_lead_tips"][:12])
    print("parts within 3 mm of board bodies:")
    for k, v in pv.items():
        print("  ", k, [(e["ref"], e["d_mm"], e["overlap_mm3"]) for e in v[:8]])
    return out


def poly_at(rec):
    return level_material(rec)


def side_stats(pts, dists, x0, x1, y0, y1, R):
    """split boundary samples of a rounded rectangle into sides / corners; min / max per group"""
    grp = {}
    for (x, y), d in zip(pts, dists):
        if x < x0 + R and y < y0 + R:
            k = "corner top-left (abs)"
        elif x > x1 - R and y < y0 + R:
            k = "corner top-right (abs)"
        elif x > x1 - R and y > y1 - R:
            k = "corner bottom-right (abs)"
        elif x < x0 + R and y > y1 - R:
            k = "corner bottom-left (abs)"
        elif abs(y - y0) < 0.6:
            k = "top"
        elif abs(y - y1) < 0.6:
            k = "bottom"
        elif abs(x - x0) < 0.6:
            k = "left (abs)"
        else:
            k = "right (abs)"
        g = grp.setdefault(k, [1e9, -1e9])
        g[0], g[1] = min(g[0], d), max(g[1], d)
    return {k: [round(v[0], 4), round(v[1], 4)] for k, v in grp.items()}


def boundary_samples(poly, step=0.25):
    ring = poly.exterior
    n = max(8, int(ring.length / step))
    return [ring.interpolate(i * ring.length / n) for i in range(n)]


def check_gaps():
    d = load("sections_asm.json")
    p = d["params"]
    out = {"levels": []}
    for z, rec in sorted(d["levels"].items(), key=lambda kv: float(kv[0])):
        z = float(z)
        lv = {"z": z}
        fr = poly_at(rec["Frame GF"]) if rec.get("Frame GF") else None
        if rec.get("Glass") and fr is not None:
            gl = poly_at(rec["Glass"])
            gl = max(gl.geoms, key=lambda g: g.area) if hasattr(gl, "geoms") else gl
            pts = boundary_samples(gl)
            ds = [fr.distance(q) for q in pts]
            lv["g2_glass_edge_to_frame"] = {"min": round(min(ds), 4), "max": round(max(ds), 4),
                                            "by_side": side_stats([(q.x, q.y) for q in pts], ds, *p["glass"])}
        if rec.get("Oven sheet") and fr is not None:
            sh = poly_at(rec["Oven sheet"])
            sh = max(sh.geoms, key=lambda g: g.area) if hasattr(sh, "geoms") else sh
            hole = max((Polygon(i) for i in sh.interiors), key=lambda h: h.area)
            pts = boundary_samples(hole)
            ds = [fr.distance(q) for q in pts]
            lv["g1_cutout_edge_to_frame"] = {"min": round(min(ds), 4), "max": round(max(ds), 4),
                                             "by_side": side_stats([(q.x, q.y) for q in pts], ds, *p["cut"])}
        for k in [k for k in rec if k.startswith("DS1.")]:
            if fr is None or not rec[k]:
                continue
            pa = poly_at(rec[k])
            pa = max(pa.geoms, key=lambda g: g.area) if hasattr(pa, "geoms") else pa
            pts = boundary_samples(pa)
            ds = [fr.distance(q) for q in pts]
            lv[k + "_to_frame"] = {"min": round(min(ds), 4), "max": round(max(ds), 4),
                                   "by_side": side_stats([(q.x, q.y) for q in pts], ds, *p["panel"])}
        out["levels"].append(lv)
    dump(out, "offline_asm_gaps.json")
    for lv in out["levels"]:
        print("z", lv["z"])
        for k, v in lv.items():
            if k != "z":
                print("   %-40s min %.4f max %.4f %s" % (k, v["min"], v["max"], v["by_side"]))
    return out


def check_bearing():
    d = load("sections_asm.json")
    p = d["params"]
    out = {}
    for z, rec in d["levels"].items():
        if not rec.get("tube_top_level"):
            continue
        fr = poly_at(rec["Frame GF"])
        for k, (x, y) in p["fasteners"].items():
            for nm, od, idd in (("DIN 9021 M4 (S4/S8)", p["w4"][0], p["w4"][1]),
                                ("DIN 9021 M5 (R4)", p["w5"][0], p["w5"][1])):
                if nm.startswith("DIN 9021 M5") and k not in ("F1", "F2", "F3", "F4"):
                    continue
                ann = Point(x, y).buffer(od / 2, quad_segs=64).difference(Point(x, y).buffer(idd / 2, quad_segs=64))
                c = ann.intersection(fr)
                tube = fr.intersection(Point(x, y).buffer(9.5, quad_segs=64))
                # rim: washer edge beyond the slot's far end along the slot axis (nominal stud at the slot centre)
                out.setdefault(k, {})[nm] = {"washer_area_mm2": round(ann.area, 2), "bearing_mm2": round(c.area, 2),
                                             "bearing_fraction": round(c.area / ann.area, 4),
                                             "tube_top_area_mm2": round(tube.area, 2)}
    dump(out, "offline_asm_bearing.json")
    for k, v in sorted(out.items()):
        print(k, v)
    return out


def check_wires():
    g = json.load(open(BOARD))
    fps = {f["ref"]: f for f in g["fps"]}
    j20, j2 = fps["J20"]["crtyd"], fps["J2"]["crtyd"]
    corr = {"J20 wires (exit -x)": box(-1e3, j20[1] - 2.0, j20[2], j20[3] + 2.0),
            "J2 cable (exit -x)": box(-1e3, j2[1] - 2.0, j2[2], j2[3] + 2.0)}
    p = load("sections_asm.json")["params"]
    d = load("fit_board.json")
    _, fpl = fp_index()
    out = {"corridors": {k: list(v.bounds) for k, v in corr.items()}, "plan": {}, "models_3d": {}}
    nut_rc = p["nut_s"] / math.sqrt(3)
    for k, (x, y) in p["fasteners"].items():
        out["plan"][k] = {cn: {"stud_axis": round(c.distance(Point(x, y)), 3),
                               "nut_corner_circle": round(max(0.0, c.distance(Point(x, y)) - nut_rc), 3),
                               "socket_dia12": round(max(0.0, c.distance(Point(x, y)) - 6.0), 3)}
                          for cn, c in corr.items()}
    for r in d["results"]:
        ref = ref_of(r, fpl)
        if ref not in ("J20", "J2"):
            continue
        for q in r["parts"]:
            if q["variant"] in ("S4", "S8", "check", "R4") and ("nut" in q["part"].lower() or "stud" in q["part"].lower()
                                                               or "socket" in q["part"] or "rivet" in q["part"].lower()):
                out["models_3d"].setdefault(ref, []).append((q["part"], q["d_mm"]))
    dump(out, "offline_asm_wires.json")
    print(json.dumps(out, indent=1)[:4000])
    return out


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("board", "all"):
        check_board()
    if what in ("gaps", "all"):
        check_gaps()
    if what in ("bearing", "all"):
        check_bearing()
    if what in ("wires", "all"):
        check_wires()
