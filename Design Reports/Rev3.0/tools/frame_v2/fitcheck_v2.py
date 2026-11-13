"""Fit check of the carrier frame (read from a STEP) against the real Rev3.0 board, the panel with its folded
tails, the Formex sheet, the gasket and the oven-sheet patch - v1 fitcheck.py with the frame imported.

  <venv>/Scripts/python.exe fitcheck_v2.py [--v1] [--frame f.step] [--params p.json] [--board b.step]

3D (BRepExtrema distances + common volumes):
  * every component model (145; Q1 leads trimmed to 2.5 mm), the PCB body (0.08 expected = copper + mask
    missing from the KiCad export), panel parts, tails (>= 1.5), Formex sheet, gasket, oven-sheet patch
  * lead protrusions vs the Formex sheet
  * TOOL ACCESS: per stud hole a dia-12 socket cylinder from 0.5 below the stud-tube top to Z +45 vs every board
    solid (centred on the hole / slot centre)
  * WASHER / SOCKET vs FRAME: a dia-12 cylinder from each stud tube top up to Z +45 must not touch the frame
    (DIN 9021 washer flat on the tube top, nut and socket free)
  * NOTHING ABOVE THE PCB: frame volume above Z 0 inside the board outline + 1 mm must be 0
PLAN (2D, from the STEP itself):
  * contact patches = planar faces of the frame at Z = 0 (+-0.01) facing +Z (rib tops, boss tops, wall top):
    distance to every B.Cu pad polygon (>= PAD_CLR) and to mains copper (creepage / clearance, v1 formula)
  * the same on the footprint = frame section at Z_SHELF_BACK + 0.02 (rib bases incl. root fillets; v1's nominal
    rib rectangles) - INFORMATIONAL; the governing numbers are the Z 0 patches and the 3D distance from the frame
    to the component model of the nearest pad (leads, solder wire)
Output: out/fitcheck.json, out/fitcheck.txt (table).
"""
import math
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.spatial import cKDTree
from matplotlib.path import Path as MPath
import cadquery as cq

import common_v2 as C

EXACT_BELOW = 5.0        # mm: frame distances below this are exact (BRepExtrema on the frame faces near the part);
                         # above it the sampled surface distance is reported, flagged approx (error < 0.5 mm)
TOOL_EXACT_BELOW = 2.0   # mm: same for the tool-access socket (exact near the 1.0 warning level)
TOOL_SKIP = 5.0          # mm: board items whose bbox is further than this from the socket are not sampled
TAIL_MIN = 1.5           # FPC tails to frame
TOOL_D = 12.0            # socket for an M4 nyloc nut on a DIN 9021 washer (washer OD 12, socket OD ~10-12)
TOOL_Z = (-6.5, 45.0)    # socket cylinder Z range if the stud-tube top is unknown (v1 brief)
TOOL_BELOW_TOP = 0.5     # the socket cylinder starts this far below the stud-tube top (washer seat)
TOOL_TOP = 45.0          # ... and ends well above the tallest component
TOOL_WARN = 1.0          # socket to any board solid: warn below this
ABOVE_PCB_MARGIN = 1.0   # nothing of the frame above Z 0 within the board outline + this
CREEPAGE_REQ, CLEARANCE_REQ = 6.4, 4.0   # mm, v1 plan_checks (reinforced, 250 V, PD2, material group IIIa)
FOOTPRINT_DZ = 0.02      # footprint section height above the shelf back face


# ------------------------------------------------------------------------------------------- 3D checks
def components(ctx, idx, log=C.log):
    fr = ctx.frame
    sh = ctx.aux["sheet"]
    comp_rows, panel_rows, lead_rows = [], [], []
    pcb = None
    for ref, part, s in ctx.items:
        if ref == "PCB":
            pcb = s
            continue
        if ref == "DS1":
            dd, approx, ov = idx.distance(s, EXACT_BELOW)
            panel_rows.append({"part": part, "min_dist": round(dd, 3), "overlap_mm3": round(ov, 4),
                               "to_sheet": round(C.dist(sh, s), 3), "approx": approx})
            continue
        s_chk, trimmed = s, False
        if ref == "Q1":
            s_chk, trimmed = C.trim_below(s, -C.Q1_TRIM), True
        dd, approx, ov = idx.distance(s_chk, EXACT_BELOW)
        zmin = s_chk.BoundingBox().zmin
        comp_rows.append({"ref": ref, "part": part, "min_dist": round(dd, 3), "overlap_mm3": round(ov, 4),
                          "zmin": round(zmin, 2), "q1_trimmed": trimmed, "approx": approx})
        if zmin < -0.05:
            lead_rows.append({"ref": ref, "protrusion": round(-zmin, 2), "gap_to_sheet": round(C.dist(sh, s_chk), 2),
                              "gap_to_frame": round(dd, 2), "gap_to_frame_approx": approx,
                              "untrimmed_protrusion": round(-s.BoundingBox().zmin, 2) if trimmed else None})
    comp_rows.sort(key=lambda r: r["min_dist"])
    lead_rows.sort(key=lambda r: r["gap_to_sheet"])
    pcb_d, _, pcb_ov = idx.distance(pcb, EXACT_BELOW)
    tails = [r for r in panel_rows if r["part"].startswith(C.PANEL_TAIL_PARTS)]
    body = [r for r in panel_rows if not r["part"].startswith(C.PANEL_TAIL_PARTS)]
    gas, oven = ctx.aux["gasket"], ctx.aux["oven"]
    log("    components %d, panel parts %d, tails %d" % (len(comp_rows), len(body), len(tails)))
    return {
        "board_dz": C.BOARD_DZ, "components_checked": len(comp_rows),
        "component_overlaps": [r for r in comp_rows if r["overlap_mm3"] > 1e-4],
        "closest_components": comp_rows[:12],
        "components_all": [{"ref": r["ref"], "min_dist": r["min_dist"], "approx": r["approx"]} for r in comp_rows],
        "pcb_body": {"min_dist": round(pcb_d, 3), "overlap_mm3": round(pcb_ov, 4),
                     "note": "0.08 = copper + mask not in the KiCad export: physical contact at the Z 0 patches"},
        "panel_parts": body, "tails": tails,
        "tail_min_dist": min(r["min_dist"] for r in tails) if tails else None,
        "panel_min_dist": min(r["min_dist"] for r in body) if body else None,
        "panel_overlap_mm3": round(sum(r["overlap_mm3"] for r in body), 4),
        "tail_overlap_mm3": round(sum(r["overlap_mm3"] for r in tails), 4),
        "lead_protrusions": lead_rows,
        "sheet_vs_frame": {"min_dist": round(C.dist(fr, sh), 3), "overlap_mm3": round(C.common_vol(fr, sh), 4)},
        "gasket_vs_frame": {"min_dist": round(C.dist(fr, gas), 3), "overlap_mm3": round(C.common_vol(fr, gas), 4)},
        "oven_sheet_vs_frame": {"min_dist": round(C.dist(fr, oven), 3), "overlap_mm3": round(C.common_vol(fr, oven), 4)},
    }


def tool_access(ctx, log=C.log):
    """dia-12 socket over every stud, Z -6.5..+45, vs every board solid (PCB, components, panel)"""
    D = ctx.D
    rows = []
    z0 = D.Z_STUD_TOP - TOOL_BELOW_TOP if D.Z_STUD_TOP is not None else TOOL_Z[0]
    zr = (round(z0, 3), TOOL_TOP)
    for n, (x, y) in D.STUDS.items():
        cyl = C.tube(x, y, zr[0], zr[1], TOOL_D).val()
        idx = C.DistIndex(cyl)
        best, overl = (1e9, None, False), []
        for ref, part, s in ctx.items:
            d, approx, v = idx.distance(s, TOOL_EXACT_BELOW, skip_beyond=TOOL_SKIP)
            if v > 1e-4:
                overl.append({"ref": ref, "part": part, "overlap_mm3": round(v, 3)})
            if d < best[0]:
                best = (d, "%s %s" % (ref, part) if ref == "DS1" else ref, approx)
        rows.append({"hole": n, "x": x, "y": y, "min_dist": round(best[0], 2), "closest": best[1],
                     "approx": best[2], "overlaps": overl, "ok": not overl, "warn": best[0] < TOOL_WARN})
    log("    tool access: min %.2f mm (%s)" % (min(r["min_dist"] for r in rows), min(rows, key=lambda r: r["min_dist"])["hole"]))
    return {"socket_d": TOOL_D, "z_range": zr, "warn_below_mm": TOOL_WARN, "holes": rows,
            "min_dist": min(r["min_dist"] for r in rows), "ok": all(r["ok"] for r in rows)}


def washer_clearance(ctx, idx, log=C.log):
    """DIN 9021 washer (dia 12) + nut + socket over every stud as one dia-12 cylinder from the tube top (+0.005) up
    to Z +45, vs the FRAME: it must not overlap (the washer has to sit flat on the tube top only)"""
    D = ctx.D
    rows = []
    for n, (x, y) in D.STUDS.items():
        z0 = D.Z_STUD_TOP
        top = None
        for f in C.faces_at_z(ctx.frame, z0, +1, tol=0.05) if z0 is not None else []:
            for w in f.innerWires():
                wb = w.BoundingBox()
                if math.hypot((wb.xmin + wb.xmax) / 2 - x, -(wb.ymin + wb.ymax) / 2 - y) < 0.1:
                    top = f.BoundingBox().zmax
        z = top if top is not None else z0
        cyl = C.tube(x, y, z + 0.005, TOOL_TOP, TOOL_D).val()
        d, approx, v = idx.distance(cyl, TOOL_EXACT_BELOW)
        rows.append({"hole": n, "tube_top_z": round(z, 3), "min_dist": round(d, 3), "overlap_mm3": round(v, 3),
                     "ok": v < 1e-3, "approx": approx})
    bad = [r["hole"] for r in rows if not r["ok"]]
    log("    washer/socket vs frame: %s" % ("clear" if not bad else "OVERLAP at " + ", ".join(bad)))
    return {"washer_d": TOOL_D, "holes": rows, "overlapping": bad, "ok": not bad,
            "min_dist": min(r["min_dist"] for r in rows)}


def nothing_above_pcb(ctx, geom):
    """frame volume above Z 0 inside the board outline (+ ABOVE_PCB_MARGIN, and + 0), and the plan gap between
    frame material above Z 0 and the board edge. Board outline = largest Edge.Cuts polygon (filled)."""
    outl = np.array(max(geom["outline"], key=lambda o: len(o)))
    w = cq.Wire.makePolygon([cq.Vector(x, C.Yc(y), 0) for x, y in outl], close=True)
    res = {"margin_mm": ABOVE_PCB_MARGIN}
    for tag, m in (("volume_mm3", ABOVE_PCB_MARGIN), ("volume_inside_outline_mm3", 0.0)):
        wo = w.offset2D(m, "arc")[0] if m > 0 else w
        region = cq.Solid.extrudeLinear(cq.Face.makeFromWires(wo), cq.Vector(0, 0, 60.0))
        com = C.common_shape(ctx.frame, region)
        vol = sum(abs(x.Volume()) for x in com.Solids()) if com.Solids() else 0.0
        res[tag] = round(vol, 4)
        if tag == "volume_mm3" and com.Solids():
            bb = C.optimal_bbox(com)
            res["bbox_abs"] = [round(bb[0], 2), round(bb[1], 2), round(-bb[3], 2), round(-bb[2], 2), round(bb[4], 3),
                               round(bb[5], 3)]
    res["ok"] = res["volume_mm3"] < 1e-3
    fb = C.optimal_bbox(ctx.frame)
    res["frame_zmax"] = round(fb[5], 3)
    sec = C.plane_section(ctx.frame, "z", C.Z_TOL * 2) if fb[5] > C.Z_TOL * 2 else None
    if sec is not None:
        pts = np.vstack([C.densify(l, 0.05) for f in sec.Faces() for l in C.face_loops_abs(f)])
        op = C.densify(outl, 0.05)
        dd, ii = cKDTree(op).query(pts)
        k = int(np.argmin(dd))
        inside = MPath(outl).contains_points(pts).any()
        res["plan_gap_above_z0_to_board_edge_mm"] = 0.0 if inside else round(float(dd[k]), 3)
        res["plan_gap_at_abs"] = [round(float(pts[k][0]), 2), round(float(pts[k][1]), 2)]
    return res


# ------------------------------------------------------------------------------------------- plan checks
class Region:
    """a planar region (outer loop + holes) in KiCad abs (x, y down), with a KD-tree of its boundary"""

    def __init__(self, loops, label, step=0.05):
        self.loops = loops
        self.label = label
        self.paths = [MPath(l) for l in loops]
        self.pts = np.vstack([C.densify(l, step) for l in loops])
        self.tree = cKDTree(self.pts)
        allp = np.vstack(loops)
        self.bbox = (allp[:, 0].min(), allp[:, 0].max(), allp[:, 1].min(), allp[:, 1].max())

    def contains(self, pts):
        inside = self.paths[0].contains_points(pts)
        for h in self.paths[1:]:
            inside &= ~h.contains_points(pts)
        return inside


def regions_from_faces(faces, label):
    out = []
    for i, f in enumerate(faces):
        loops = C.face_loops_abs(f)
        if loops:
            r = Region(loops, "%s#%d" % (label, i))
            r.area = f.Area()
            out.append(r)
    return out


def copper_sets(geom):
    """B.Cu pads (non-NPTH) and mains copper (mains pads on B.Cu + mains tracks/zones on B.Cu), as polygons"""
    pads, mains = [], []
    for p in geom["pads"]:
        if not p["on_bcu"] or p["attr"] == "NPTH" or not p["poly"]:
            continue
        polys = [np.array(q) for q in p["poly"] if len(q) >= 3]
        item = ("%s.%s" % (p["ref"], p["num"]), polys)
        pads.append(item)
        if p["mains"]:
            mains.append(item)
    for m in geom["mains_bcu"]:
        polys = [np.array(q) for q in m["poly"] if len(q) >= 3]
        if polys:
            mains.append(("%s %s" % (m["net"], m["kind"]), polys))
    return pads, mains


def classify_point(D, x, y):
    for h, (hx, hy) in D.HOLES.items():
        if math.hypot(x - hx, y - hy) <= D.BOSS_OD / 2 + 0.3:
            return "boss " + h
    px0, px1, py0, py1 = D.POCKET
    if px0 < x < px1 and py0 < y < py1:
        return "rib"
    return "wall"


def kind_trees(D, regions):
    """KD-trees of the regions' boundary points split by feature: boss (within BOSS_OD/2 + 0.3 of a PCB hole),
    rib (inside the panel pocket line), wall (the rest)"""
    P = np.vstack([r.pts for r in regions])
    H = np.array(list(D.HOLES.values()))
    dh = np.min(np.hypot(P[:, None, 0] - H[None, :, 0], P[:, None, 1] - H[None, :, 1]), axis=1)
    px0, px1, py0, py1 = D.POCKET
    inpk = (P[:, 0] > px0) & (P[:, 0] < px1) & (P[:, 1] > py0) & (P[:, 1] < py1)
    kind = np.where(dh <= D.BOSS_OD / 2 + 0.3, "boss", np.where(inpk, "rib", "wall"))
    return {k: cKDTree(P[kind == k]) for k in ("boss", "rib", "wall") if (kind == k).any()}


def poly_to_regions(name, polys, regions, D):
    """min distance from a copper item (list of polygons) to the regions, with the closest frame point"""
    best = (1e9, None, None)
    for poly in polys:
        pp = C.densify(poly, 0.05)
        pb = (pp[:, 0].min(), pp[:, 0].max(), pp[:, 1].min(), pp[:, 1].max())
        mpath = MPath(poly)
        for r in regions:
            gx = max(r.bbox[0] - pb[1], pb[0] - r.bbox[1], 0)
            gy = max(r.bbox[2] - pb[3], pb[2] - r.bbox[3], 0)
            if math.hypot(gx, gy) > best[0]:
                continue
            if r.contains(pp).any() or mpath.contains_points(r.pts).any():
                d, j = 0.0, None
                q = pp[r.contains(pp)][0] if r.contains(pp).any() else r.pts[mpath.contains_points(r.pts)][0]
            else:
                dd, ii = r.tree.query(pp)
                k = int(np.argmin(dd))
                d, q = float(dd[k]), r.pts[ii[k]]
            if d < best[0]:
                best = (d, r.label, (float(q[0]), float(q[1])))
    kind = classify_point(D, *best[2]) if best[2] else None
    return best[0], best[1], best[2], kind


def local_reach(D, q, reach_tree, reach_pts):
    """depth inside the panel outline reached by the frame footprint (rib bases) within 3 mm of the frame point q
    (abs): the rib's own reach where the creepage path leaves it (handles per-rib reach and flush ribs)"""
    if q is None or reach_tree is None:
        return D.PCB_RIM_W, "PCB_RIM_W"
    idx = reach_tree.query_ball_point(q, 3.0)
    if not idx:
        return D.PCB_RIM_W, "PCB_RIM_W"
    P = reach_pts[idx]
    e = np.minimum.reduce([P[:, 0] - D.PX0, D.PX1 - P[:, 0], P[:, 1] - D.PY0, D.PY1 - P[:, 1]])
    return float(min(max(e.max(), 0.0), D.SEAT_W)), "measured on the footprint"


def plan_set(D, regions, pads, mains, reach_regions=None):
    """pads and mains copper vs one set of frame regions"""
    rows = []
    for name, polys in pads:
        d, lab, q, kind = poly_to_regions(name, polys, regions, D)
        rows.append({"pad": name, "dist": round(d, 3), "kind": kind, "at": [round(v, 2) for v in q] if q else None})
    rows.sort(key=lambda r: r["dist"])
    by_kind = {}
    for k, tree in kind_trees(D, regions).items():
        best = (1e9, None)
        for name, polys in pads:
            pp = np.vstack([C.densify(q, 0.05) for q in polys])
            d = float(tree.query(pp)[0].min())
            if d < best[0]:
                best = (d, name)
        by_kind[k] = (best[0], best[1], k)
    mbest = (1e9, None, None, None)
    for name, polys in mains:
        d, lab, q, kind = poly_to_regions(name, polys, regions, D)
        if d < mbest[0]:
            mbest = (d, name, kind, q)
    rp = np.vstack([r.pts for r in reach_regions]) if reach_regions else None
    reach, src = local_reach(D, mbest[3], cKDTree(rp) if rp is not None else None, rp)
    tail = (D.Z_PCB - D.Z_SHELF_BACK) + (D.SEAT_W - reach) + D.SHELF_T + (D.SEAT_W - D.SHEET_INSET)
    return {"pad_min": [round(rows[0]["dist"], 2), rows[0]["pad"], rows[0]["kind"]] if rows else None,
            "pad_min_by_kind": {k: [round(v[0], 2), v[1], v[2]] for k, v in by_kind.items()},
            "closest_pads": rows[:8],
            "pad_ok": (rows[0]["dist"] >= D.PAD_CLR) if rows else True,
            "mains_to_frame_min": [round(mbest[0], 2), mbest[1], mbest[2]],
            "creepage_tail_mm": round(tail, 2), "rib_reach_at_contact_mm": round(reach, 3), "rib_reach_source": src,
            "mains_contact_point_abs": [round(v, 2) for v in mbest[3]] if mbest[3] else None,
            "creepage_mains_to_panel_mm": round(mbest[0] + tail, 2)}


def clearance_mains(D, mains):
    """air clearance mains copper -> round the shelf inner corner -> shelf/sheet interface (v1 formula)"""
    worst = (1e9, None)
    for name, polys in mains:
        for poly in polys:
            for px, py in C.densify(poly, 0.05):
                e = min(px - D.PX0, D.PX1 - px, py - D.PY0, D.PY1 - py)   # depth inside the panel outline
                if e < 0 or e > 15:
                    continue
                c = math.hypot(abs(e - D.SEAT_W), D.Z_PCB - D.Z_SEAT) + (D.SEAT_W - D.SHEET_INSET)
                if c < worst[0]:
                    worst = (c, name)
    return worst


def plan_checks(ctx, geom, log=C.log, comps=None):
    D, fr = ctx.D, ctx.frame
    pads, mains = copper_sets(geom)
    faces = C.faces_at_z(fr, D.Z_PCB, +1)
    contact = regions_from_faces(faces, "Z0")
    patches = []
    for r in contact:
        patches.append({"id": r.label, "area_mm2": round(r.area, 2),
                        "bbox_abs": [round(v, 2) for v in r.bbox], "holes": len(r.loops) - 1})
    zf = D.Z_SHELF_BACK + FOOTPRINT_DZ
    sec = C.plane_section(fr, "z", zf)
    foot = regions_from_faces(sec.Faces(), "FP") if sec else []
    res = {"pad_clr_req": D.PAD_CLR, "creepage_req_mm": CREEPAGE_REQ, "clearance_req_mm": CLEARANCE_REQ,
           "contact_patches": patches, "contact_faces": len(contact),
           "contact": plan_set(D, contact, pads, mains, foot),
           "footprint_z": round(zf, 3), "footprint_faces": len(foot),
           "footprint": plan_set(D, foot, pads, mains, foot),
           "pads_checked": len(pads), "mains_items": len(mains)}
    cl = clearance_mains(D, mains)
    res["clearance_mains_to_panel_mm"] = round(cl[0], 2)
    res["clearance_worst_item"] = cl[1]
    c, f = res["contact"], res["footprint"]
    f["informational"] = True       # the pad rule applies to the Z 0 contact patches; the rib base is 2 mm below
    gov = {}
    if comps:                       # 3D: frame -> component model of the nearest pads (leads, solder wire, fillets)
        dmap = {}
        for r in comps:
            dmap[r["ref"]] = min(dmap.get(r["ref"], 1e9), r["min_dist"])
        for tag, st in (("contact", c), ("footprint", f)):
            ref = st["pad_min"][1].split(".")[0] if st.get("pad_min") else None
            if ref in dmap:
                gov[tag] = {"pad": st["pad_min"][1], "component": ref, "min_dist_3d": dmap[ref]}
    res["governing_3d"] = gov
    g3 = min((v["min_dist_3d"] for v in gov.values()), default=None)
    res["governing_3d_min"] = g3
    res["ok"] = (c["pad_ok"] and c["creepage_mains_to_panel_mm"] >= CREEPAGE_REQ and cl[0] >= CLEARANCE_REQ
                 and (g3 is None or g3 >= D.PAD_CLR))
    log("    plan: %d contact patches, pads min %s; footprint pads min %s" % (len(contact), c["pad_min"], f["pad_min"]))
    return res


# ------------------------------------------------------------------------------------------- report
def table(r):
    c3, pl, ta, ab = r["fit3d"], r["plan"], r["tool_access"], r["above_pcb"]
    L = []

    def row(check, result, limit, ok):
        L.append("%-46s %-44s %-14s %s" % (check, result, limit, "OK" if ok else "FAIL"))
    row("components (%d) overlapping" % c3["components_checked"], "%d" % len(c3["component_overlaps"]), "0",
        not c3["component_overlaps"])
    cc = c3["closest_components"][0]
    row("closest component", "%s %.3f mm" % (cc["ref"], cc["min_dist"]), "> 0", cc["min_dist"] > 0)
    row("PCB body", "%.3f mm, %.4f mm3" % (c3["pcb_body"]["min_dist"], c3["pcb_body"]["overlap_mm3"]), "0.08 / 0",
        abs(c3["pcb_body"]["min_dist"] - C.BOARD_DZ) < 0.005 and c3["pcb_body"]["overlap_mm3"] < 1e-4)
    row("panel parts", "min %.3f mm, %.4f mm3" % (c3["panel_min_dist"], c3["panel_overlap_mm3"]), "> 0 / 0",
        c3["panel_min_dist"] > 0 and c3["panel_overlap_mm3"] < 1e-4)
    row("FPC tails", "min %.3f mm" % c3["tail_min_dist"], ">= %.1f" % TAIL_MIN, c3["tail_min_dist"] >= TAIL_MIN)
    row("Formex sheet", "%.3f mm, %.4f mm3" % (c3["sheet_vs_frame"]["min_dist"], c3["sheet_vs_frame"]["overlap_mm3"]),
        "0 vol", c3["sheet_vs_frame"]["overlap_mm3"] < 1e-3)
    row("gasket", "%.3f mm, %.4f mm3" % (c3["gasket_vs_frame"]["min_dist"], c3["gasket_vs_frame"]["overlap_mm3"]),
        "0 vol", c3["gasket_vs_frame"]["overlap_mm3"] < 1e-3)
    row("oven-sheet patch", "%.3f mm, %.4f mm3" % (c3["oven_sheet_vs_frame"]["min_dist"],
                                                  c3["oven_sheet_vs_frame"]["overlap_mm3"]), "0 vol",
        c3["oven_sheet_vs_frame"]["overlap_mm3"] < 1e-3)
    lp = c3["lead_protrusions"][0] if c3["lead_protrusions"] else None
    if lp:
        row("lead protrusion -> Formex sheet (closest)", "%s %.2f -> gap %.2f mm" % (lp["ref"], lp["protrusion"],
                                                                                    lp["gap_to_sheet"]), "> 0",
            lp["gap_to_sheet"] > 0)
    for tag in ("contact", "footprint"):
        s = pl[tag]
        info = tag == "footprint"
        lab = "Z 0 contact patches" if tag == "contact" else "(info) rib-base footprint Z %.2f" % pl["footprint_z"]
        row("%s vs B.Cu pads" % lab, "%.2f mm at %s (%s)" % tuple(s["pad_min"]),
            ">= %.1f" % pl["pad_clr_req"] if not info else "info", True if info else s["pad_ok"])
        bk = s["pad_min_by_kind"]
        for k in ("rib", "boss", "wall"):
            if k in bk:
                row("  - %s" % k, "%.2f mm at %s (%s)" % tuple(bk[k]), "", True)
        row("%s: mains copper -> frame" % lab, "%.2f mm (%s)" % (s["mains_to_frame_min"][0], s["mains_to_frame_min"][1]),
            "", True)
        row("%s: creepage mains -> panel" % lab, "%.2f mm" % s["creepage_mains_to_panel_mm"],
            ">= %.1f" % pl["creepage_req_mm"] if not info else "info",
            True if info else s["creepage_mains_to_panel_mm"] >= pl["creepage_req_mm"])
    for tag, g in pl.get("governing_3d", {}).items():
        row("3D frame -> %s model (nearest pad %s, %s)" % (g["component"], g["pad"], tag), "%.3f mm" % g["min_dist_3d"],
            ">= %.1f" % pl["pad_clr_req"], g["min_dist_3d"] >= pl["pad_clr_req"])
    row("clearance mains -> panel", "%.2f mm (%s)" % (pl["clearance_mains_to_panel_mm"], pl["clearance_worst_item"]),
        ">= %.1f" % pl["clearance_req_mm"], pl["clearance_mains_to_panel_mm"] >= pl["clearance_req_mm"])
    worst = min(ta["holes"], key=lambda h: h["min_dist"])
    row("tool access dia %.0f Z %.2f..%.0f" % (ta["socket_d"], ta["z_range"][0], ta["z_range"][1]),
        "min %.2f mm at %s (%s)" % (worst["min_dist"], worst["hole"], worst["closest"]), "no overlap", ta["ok"])
    wv = r["washer_vs_frame"]
    row("washer dia %.0f + socket over each stud vs frame" % wv["washer_d"],
        ("clear (seat contact only)" if wv["min_dist"] < 0.01 else "clear (min %.2f mm)" % wv["min_dist"])
        if wv["ok"] else "OVERLAP at " + ", ".join(wv["overlapping"]),
        "no overlap", wv["ok"])
    row("nothing above Z 0 inside board + %.0f mm" % ab["margin_mm"], "%.4f mm3 (inside outline %.4f)" % (
        ab["volume_mm3"], ab["volume_inside_outline_mm3"]), "0", ab["ok"])
    if "plan_gap_above_z0_to_board_edge_mm" in ab:
        row("  frame above Z 0: plan gap to board edge", "%.3f mm at %s" % (ab["plan_gap_above_z0_to_board_edge_mm"],
                                                                         ab["plan_gap_at_abs"]),
            ">= %.1f" % ab["margin_mm"], ab["plan_gap_above_z0_to_board_edge_mm"] >= ab["margin_mm"])
    return "\n".join(L)


def run(ctx, log=C.log):
    t0 = time.time()
    geom = C.board_geom()
    log("[fit] 3D distances (%d board items)" % len(ctx.items))
    idx = C.DistIndex(ctx.frame)
    res = {"frame": ctx.frame_path, "board_step": ctx.board_path, "fit3d": components(ctx, idx, log)}
    log("[fit] tool access")
    res["tool_access"] = tool_access(ctx, log)
    res["washer_vs_frame"] = washer_clearance(ctx, idx, log)
    res["above_pcb"] = nothing_above_pcb(ctx, geom)
    log("[fit] plan checks")
    res["plan"] = plan_checks(ctx, geom, log, res["fit3d"]["components_all"])
    res["table"] = table(res)
    c3 = res["fit3d"]
    res["ok"] = bool(not c3["component_overlaps"] and c3["tail_min_dist"] >= TAIL_MIN and c3["panel_overlap_mm3"] < 1e-4
                     and c3["pcb_body"]["overlap_mm3"] < 1e-4 and c3["oven_sheet_vs_frame"]["overlap_mm3"] < 1e-3
                     and res["tool_access"]["ok"] and res["washer_vs_frame"]["ok"] and res["above_pcb"]["ok"]
                     and res["plan"]["ok"])
    res["seconds"] = round(time.time() - t0, 1)
    C.dump(res, ctx.out("fitcheck.json"))
    open(ctx.out("fitcheck.txt"), "w").write(res["table"] + "\n")
    log(res["table"])
    return res


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    run(ctx)
