"""20 - READ-ONLY v2-style scans of body 'Frame GF' (copy of frame_v2/fusion/60_scan_v22.py with the GF levels):
  * sliver rule (owner's cadcheck rule): area < 0.5 mm2 or 2A/P < 0.3 mm -> listed (fillet blend patches expected)
  * draft / undercut classification of every face:
      flat_perp_Z (|n.z| > 0.99999): side A (faces -Z) only at Z_GLASS_FRONT / Z_SHEET_BACK / Z_FLANGE_FRONT /
          Z_LAND / Z_PIP_TOP / Z_SEAT; side B (faces +Z) only at Z_PCB / Z_SHELF_BACK / Z_TUBE_TOP / Z_TRIB_TOP /
          Z_STEPWALL_BACK (= land-plate back = cell floors) / Z_CELL_RIB_TOP / Z_FLANGE_BACK / Z_TROUGH_TOP /
          pilot floors / relief floors -> else FLAG
      planar_drafted (angle to the pull axis, side A = n.z < 0, B = n.z > 0), planar_UNDRAFTED (< 0.25 deg) -> FLAG
      cone (half angle), cone_tilted, cylinder_axis_Z_UNDRAFTED -> FLAG, torus / other (fillets)
      A-side drafted faces reaching above Z_SEAT -> FLAG (the A core ends at the shelf front, as v2)
  * thin-strip scan (gflib.thin_strips: parallel straight edges < 1.0 mm apart on one planar face)
  * census of the concave roots left unfilleted (gflib.root_edges, grouped)
Writes scratchpad scan_<TAG>.json."""
import importlib
import json
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)

TAG = "final"


def run(_context: str):
    L.check_doc()
    b = L.body()
    zs = L.P("Z_SEAT")
    minus_ok = [L.P(n) for n in ("Z_GLASS_FRONT", "Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_LAND", "Z_PIP_TOP", "Z_SEAT")]
    plus_ok = [L.P(n) for n in ("Z_PCB", "Z_SHELF_BACK", "Z_TUBE_TOP", "Z_TRIB_TOP", "Z_STEPWALL_BACK",
                                "Z_LANDPLATE_BACK", "Z_CELL_RIB_TOP", "Z_FLANGE_BACK", "Z_TROUGH_TOP")]
    plus_ok += [L.P("Z_LAND") + L.P("pilot_floor"), L.P("Z_PCB") - L.P("cbore_h")]
    faces, slivers, flags = [], [], []
    counts = {}
    s025 = math.sin(math.radians(0.25))
    for i in range(b.faces.count):
        f = b.faces.item(i)
        g = f.geometry
        st = g.surfaceType
        bb = f.boundingBox
        dims = sorted([(bb.maxPoint.x - bb.minPoint.x) * 10, (bb.maxPoint.y - bb.minPoint.y) * 10,
                       (bb.maxPoint.z - bb.minPoint.z) * 10])
        A = f.area * 100.0
        Pm = sum(f.edges.item(k).length for k in range(f.edges.count)) * 10.0
        r2 = 2 * A / Pm if Pm > 0 else 0.0
        c = f.centroid
        cen = [round(c.x * 10, 3), round(-c.y * 10, 3), round(c.z * 10, 3)]
        ok, n = f.evaluator.getNormalAtPoint(f.pointOnFace)
        nz = n.z
        rec = {"i": i, "type": "", "area": round(A, 4), "two_a_over_p": round(r2, 4), "centroid_abs": cen,
               "z": [round(bb.minPoint.z * 10, 4), round(bb.maxPoint.z * 10, 4)]}
        if st == adsk.core.SurfaceTypes.PlaneSurfaceType:
            thin = dims[1]
            if abs(nz) > 0.99999:
                rec["type"] = "flat_perp_Z"
                z = c.z * 10
                rec["side"] = "B" if nz > 0 else "A"
                ref = plus_ok if nz > 0 else minus_ok
                if min(abs(z - r) for r in ref) > 1e-3:
                    flags.append(dict(rec, why="horizontal face facing %s at an unexpected level" % (
                        "+Z" if nz > 0 else "-Z")))
            elif abs(nz) < s025:
                rec["type"] = "planar_UNDRAFTED"
                flags.append(dict(rec, why="planar face parallel to Z (no draft)"))
            else:
                rec["type"] = "planar_drafted"
                rec["draft_deg"] = round(math.degrees(math.asin(min(1.0, abs(nz)))), 4)
                rec["side"] = "B" if nz > 0 else "A"
        else:
            thin = dims[0]
            if st == adsk.core.SurfaceTypes.ConeSurfaceType:
                axis = g.axis
                par = abs(abs(axis.z) / axis.length - 1) < 1e-6
                rec["type"] = "cone" + ("" if par else "_tilted")
                rec["half_angle_deg"] = round(math.degrees(g.halfAngle), 4)
                rec["side"] = "B" if nz > 0 else "A"
                if not par:
                    flags.append(dict(rec, why="cone with a tilted axis"))
            elif st == adsk.core.SurfaceTypes.CylinderSurfaceType:
                axis = g.axis
                if abs(abs(axis.z) / axis.length - 1) < 1e-6:
                    rec["type"] = "cylinder_axis_Z_UNDRAFTED"
                    flags.append(dict(rec, why="cylinder with axis || Z (no draft)"))
                else:
                    rec["type"] = "cylinder_other"
            elif st == adsk.core.SurfaceTypes.TorusSurfaceType:
                rec["type"] = "torus"
            else:
                rec["type"] = "other_%d" % st
        if rec.get("side") == "A" and rec["type"] in ("planar_drafted", "cone") and rec["z"][1] > zs + 1e-3:
            flags.append(dict(rec, why="A-side (front-half) drafted face reaching above Z_SEAT"))
        rec["bbox_thin"] = round(thin, 4)
        if A < 0.5 or r2 < 0.3:
            slivers.append(rec)
        counts[rec["type"]] = counts.get(rec["type"], 0) + 1
        faces.append(rec)
    n_tl, bad = L.timeline_health()
    res = {"tag": TAG, "timeline_count": n_tl, "timeline_unhealthy": bad, "body": L.body_dict(b), "counts": counts,
           "slivers": slivers, "flags": flags,
           "min_area": min(f["area"] for f in faces), "min_2a_p": min(f["two_a_over_p"] for f in faces),
           "draft_values_planar": sorted(set(f.get("draft_deg") for f in faces if "draft_deg" in f)),
           "cone_half_angles": sorted(set(f.get("half_angle_deg") for f in faces if "half_angle_deg" in f)),
           "face_list": faces}
    ts = L.thin_strips(b)
    res["thin_strips_lt_1mm"] = [{"face": t[0], "width_mm": t[1], "overlap_mm": t[2], "mid_abs_approx": t[3]}
                                 for t in ts]
    rem = []
    for g, e, m, z, o in L.root_edges(0.9):
        rem.append({"group": g, "mid_abs": [round(m[0], 3), round(-m[1], 3), round(m[2], 3)],
                    "z": [round(z[0], 3), round(z[1], 3)], "len_mm": round(e.length * 10, 3), "owners": list(o)})
    res["unfilleted_concave_roots"] = rem
    p = L.dump(res, "scan_%s.json" % TAG)
    by = {}
    for r in rem:
        by[r["group"]] = by.get(r["group"], 0) + 1
    L.log("20 scan %s: faces %d, slivers %d, flags %d, counts %s, min area %.4f, min 2A/P %.4f, thin %d, roots %s" % (
        TAG, b.faces.count, len(slivers), len(flags), counts, res["min_area"], res["min_2a_p"], len(ts), by))
    print(p, "faces", b.faces.count, "slivers", len(slivers), "flags", len(flags), counts, "thin strips", len(ts),
          "unfilleted roots", by)
