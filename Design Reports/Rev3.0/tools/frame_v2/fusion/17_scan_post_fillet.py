"""17 - READ-ONLY global scans AFTER the root fillets (same code as 13) + thin-strip scan + census of the
concave roots left unfilleted.

13 text follows: global scans of body 'Frame v2' (run with readOnly: true). Writes
scratchpad/cad/scan_<TAG>.json and a summary line to the log.

Sliver scan (owner's cadcheck rule): every face, area (mm2), perimeter (sum of edge lengths), 2A/P (mm);
bbox thinness = smallest bbox dimension, or for planar faces the smaller of the two in-plane dimensions
(a planar face has zero extent along its normal). Offending: area < 0.5 mm2 or 2A/P < 0.3 mm.

Draft scan: every face classified as
  flat_perp_Z (planar, |n.z| > 0.99999)      -> also checked: outward -Z faces only at Z_FRONT / Z_SEAT / peg tips,
                                                 outward +Z faces only at the known B-side levels
  planar_drafted (angle to the pull axis, side A = outward n.z < 0, B = n.z > 0)
  planar_UNDRAFTED (|n.z| < sin 0.25 deg)    -> FLAG
  cone (half angle, axis || Z), cylinder_axis_Z (= undrafted) -> FLAG, torus / other (fillets)
plus: A-side drafted faces reaching above Z_SEAT -> FLAG (the A core ends at the shelf front face).
"""
import importlib
import json
import math
import sys

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\frame_v2\fusion")
import fv2lib as L
importlib.reload(L)

TAG = "post_fillet"
OUT = (r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\62ff0a1a-4475-4c41-9c45-d7dae40b64a5"
       r"\scratchpad\cad\scan_%s.json")


def run(_context: str):
    L.check_doc()
    b = L.body()
    zf, zs, zsb, zp = L.P("Z_FRONT"), L.P("Z_SEAT"), L.P("Z_SHELF_BACK"), L.P("Z_PCB")
    minus_ok = [zf, zs, zf - L.P("peg_h")]
    plus_ok = [zp, zsb, L.P("Z_STUD_TOP"), L.P("Z_CELL_FLOOR"), L.P("Z_CELL_RIB_TOP"), L.P("Z_FLANGE_BACK"),
               L.P("Z_TROUGH_TOP"), zf + L.P("pilot_floor"), zp - L.P("cbore_h")]
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
        P = sum(f.edges.item(k).length for k in range(f.edges.count)) * 10.0
        r2 = 2 * A / P if P > 0 else 0.0
        c = f.centroid
        cen = [round(c.x * 10, 3), round(-c.y * 10, 3), round(c.z * 10, 3)]   # abs KiCad x, y-down, Z
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
    pp = b.physicalProperties
    bbx = b.boundingBox
    res = {"tag": TAG, "faces": b.faces.count, "volume_cm3": round(pp.volume, 4),
           "mass_g_at_1.36": round(pp.volume * 1.36, 2),
           "bbox_abs": {"x": [round(bbx.minPoint.x * 10, 3), round(bbx.maxPoint.x * 10, 3)],
                        "y_down": [round(-bbx.maxPoint.y * 10, 3), round(-bbx.minPoint.y * 10, 3)],
                        "z": [round(bbx.minPoint.z * 10, 3), round(bbx.maxPoint.z * 10, 3)]},
           "timeline_count": n_tl, "timeline_unhealthy": bad, "counts": counts,
           "slivers": slivers, "flags": flags,
           "min_area": min(f["area"] for f in faces), "min_2a_p": min(f["two_a_over_p"] for f in faces),
           "draft_values_planar": sorted(set(f.get("draft_deg") for f in faces if "draft_deg" in f)),
           "cone_half_angles": sorted(set(f.get("half_angle_deg") for f in faces if "half_angle_deg" in f)),
           "face_list": faces}
    ts = L.thin_strips(b)
    res["thin_strips_lt_1mm"] = [{"face": t[0], "width_mm": t[1], "overlap_mm": t[2], "mid_abs_approx": t[3]}
                                 for t in ts]
    rem = []
    for g, e, m, z, o in L.root_edges2(0.9):
        rem.append({"group": g, "rib_free_end": bool(L.rib_end_edge(e, m, z)), "mid_abs": [round(m[0], 3),
                    round(-m[1], 3), round(m[2], 3)], "z": [round(z[0], 3), round(z[1], 3)],
                    "len_mm": round(e.length * 10, 3), "owners": list(o)})
    res["unfilleted_concave_roots"] = rem
    json.dump(res, open(OUT % TAG, "w"), indent=1)
    L.log("13 scan %s: faces %d, slivers %d, flags %d, counts %s, min area %.4f, min 2A/P %.4f" % (
        TAG, b.faces.count, len(slivers), len(flags), counts, res["min_area"], res["min_2a_p"]))
    print("faces", b.faces.count, "slivers", len(slivers), "flags", len(flags), counts, "thin strips", len(ts),
          "unfilleted roots", len(rem), sum(1 for r in rem if r["rib_free_end"]))
