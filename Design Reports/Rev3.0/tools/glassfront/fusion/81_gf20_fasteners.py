"""81 - stage 4 (GF-2.0), READ-ONLY fastener checks at F1-F4 with temporary BReps (no design change; 62-64 adapted):
  * S4 weld stud: flange incl. weld collar / flash ENVELOPE dia 5.8 x 1.4 on the sheet back + M4 shank dia 4.0, at the
    centred position, at +-0.3 (stud_position_tol) in 8 directions (along / across the slot axis and the diagonals) and
    at the extreme positions where the shank touches the slot wall / end (bisection along 8 directions):
    min distance to the frame (with the frame face type / Z at the closest point), intersection volume (must be 0)
  * DIN 9021 M4 washer (12 x 4.3) bearing area on the tube top (annulus sliced 0.01 below Z_TUBE_TOP), centred, +-0.3,
    0.6 along / 0.7 across (GF-1.1 reference offsets) and at the shank-limited slot end
  * R4: dia 4.8 rivet shank vs the slot at the same positions; pad face under the dia-14 head (sliced 0.01 behind the
    pad top) centred and +-0.3; head edge -> cut-out corner arc; DIN 9021 M5 (15 x 5.3) backing washer on the tube top
Writes %TEMP%\\rev3_glassfront\\gf20\\fasteners.json."""
import importlib
import math
import sys
import time

import adsk.core
import adsk.fusion

sys.path.insert(0, r"C:\Users\lenovo\Documents\Projects\3D Printer Filament Dryer\Design Reports\Rev3.0\tools\glassfront\fusion")
import gflib as L
importlib.reload(L)
import gfasm as A
importlib.reload(A)
DUMP = globals().get("DUMP") or "gf20"          # stage-5 runs set DUMP = "gf21" (dump sub-folder)

TB = adsk.fusion.TemporaryBRepManager.get()
ENV_D, ENV_K = 5.8, 1.4
TOL = 0.3


def cyl(x, y, z0, z1, d, d_in=None):
    p0 = adsk.core.Point3D.create(x / 10.0, -y / 10.0, z0 / 10.0)
    p1 = adsk.core.Point3D.create(x / 10.0, -y / 10.0, z1 / 10.0)
    c = TB.createCylinderOrCone(p0, d / 20.0, p1, d / 20.0)
    if d_in:
        h = TB.createCylinderOrCone(p0, d_in / 20.0, p1, d_in / 20.0)
        TB.booleanOperation(c, h, adsk.fusion.BooleanTypes.DifferenceBooleanType)
    return c


def inter_vol(fr, t):
    a = TB.copy(fr)
    ok = TB.booleanOperation(a, TB.copy(t), adsk.fusion.BooleanTypes.IntersectionBooleanType)
    return a.volume * 1000.0 if ok else None


def dirs(k):
    ux, uy = L.P("f%d_ux" % k), L.P("f%d_uy" % k)
    nx, ny = -uy, ux
    c = math.cos(math.radians(45))
    return {"+along (to glass)": (ux, uy), "-along": (-ux, -uy), "+across": (nx, ny), "-across": (-nx, -ny),
            "+along+across": (c * (ux + nx), c * (uy + ny)), "+along-across": (c * (ux - nx), c * (uy - ny)),
            "-along+across": (c * (-ux + nx), c * (-uy + ny)), "-along-across": (c * (-ux - nx), c * (-uy - ny))}


def stud(fr, x, y):
    zs = L.P("Z_SHEET_BACK")
    fl = cyl(x, y, zs, zs + ENV_K, ENV_D)
    sh = cyl(x, y, zs, zs + L.P("stud_l"), L.P("stud_d"))
    d1, p1, p2 = L.min_dist_mm(fl, fr)
    d2, q1, q2 = L.min_dist_mm(sh, fr)
    zf = L.pt_abs(p2)[2]
    where = "floor" if abs(zf - (zs + L.P("cb_floor"))) < 0.005 else ("floor round" if zf > zs + L.P("cb_floor") - L.P("cb_r") - 0.005 else "wall")
    return {"flange_env_d_mm": round(d1, 4), "flange_closest_frame_pt": L.pt_abs(p2), "flange_closest_at": where,
            "flange_overlap_mm3": round(inter_vol(fr, fl), 5) if d1 < 0.001 else 0.0,
            "shank_d_mm": round(d2, 4), "shank_closest_frame_pt": L.pt_abs(q2)}


def shank_limit(fr, x, y, ux, uy, d_shank):
    """largest offset s along (ux, uy) at which a shank of d_shank still clears the frame (bisection)"""
    zs = L.P("Z_SHEET_BACK")

    def clear(s):
        sh = cyl(x + s * ux, y + s * uy, zs - 0.5, L.P("Z_TUBE_TOP") + 1.0, d_shank)
        d, p1, p2 = L.min_dist_mm(sh, fr)
        return d > 0.002
    lo, hi = 0.0, 2.0
    while hi - lo > 0.002:
        m = (lo + hi) / 2
        if clear(m):
            lo = m
        else:
            hi = m
    return lo


def slice_area(fr, x, y, z_face, side, od, idd):
    """area (mm2) of frame material in a 0.01 slice just inside the face at z_face (side +1: slice above, -1 below)
    under an annulus od / idd centred at (x, y)"""
    z0, z1 = (z_face, z_face + 0.01) if side > 0 else (z_face - 0.01, z_face)
    a = cyl(x, y, z0, z1, od, idd)
    v = inter_vol(fr, a)
    return round(v / 0.01, 2) if v is not None else None


def run(_context: str):
    L.check_doc()
    t0 = time.time()
    fr = A.frame()
    res = {"envelope": "flange incl. weld collar / flash dia %.1f x %.1f; stud_position_tol +-%.1f" % (ENV_D, ENV_K, TOL),
           "levels": {k: round(L.P(k), 4) for k in ("Z_SHEET_BACK", "Z_FLANGE_FRONT", "Z_TUBE_TOP")},
           "counterbore": {"cb_w": L.P("cb_w"), "cb_l": L.P("cb_l"), "cb_floor": L.P("cb_floor"), "cb_r": L.P("cb_r")},
           "F": {}}
    ztt = L.P("Z_TUBE_TOP")
    for k in (1, 2, 3, 4):
        fx, fy = L.P("f%d_x" % k), L.P("f%d_y" % k)
        e = {"xy": [round(fx, 4), round(fy, 4)], "slot_axis": [round(L.P("f%d_ux" % k), 4), round(L.P("f%d_uy" % k), 4)]}
        e["stud_centred"] = stud(fr, fx, fy)
        e["stud_tol"] = {}
        e["stud_extreme"] = {}
        e["rivet_shank_tol"] = {}
        e["washer_M4_bearing_mm2"] = {"centred": slice_area(fr, fx, fy, ztt, -1, L.P("w4_od"), L.P("w4_id"))}
        e["washer_M5_bearing_mm2"] = {"centred": slice_area(fr, fx, fy, ztt, -1, L.P("w5_od"), L.P("w5_id"))}
        e["R4_pad_face_under_head_mm2"] = {"centred": slice_area(fr, fx, fy, L.P("Z_SHEET_BACK"), +1, L.P("riv_head_d"),
                                                                   L.P("riv_hole"))}
        for nm, (ux, uy) in dirs(k).items():
            x, y = fx + TOL * ux, fy + TOL * uy
            e["stud_tol"][nm] = stud(fr, x, y)
            sh = cyl(x, y, L.P("Z_SHEET_BACK") - 0.5, ztt + 1.0, L.P("riv_d"))
            d, p1, p2 = L.min_dist_mm(sh, fr)
            e["rivet_shank_tol"][nm] = round(d, 4)
            e["washer_M4_bearing_mm2"]["0.3 " + nm] = slice_area(fr, x, y, ztt, -1, L.P("w4_od"), L.P("w4_id"))
            e["R4_pad_face_under_head_mm2"]["0.3 " + nm] = slice_area(fr, x, y, L.P("Z_SHEET_BACK"), +1,
                                                                      L.P("riv_head_d"), L.P("riv_hole"))
            s = shank_limit(fr, fx, fy, ux, uy, L.P("stud_d"))
            r = stud(fr, fx + (s - 0.002) * ux, fy + (s - 0.002) * uy)
            r["offset_mm"] = round(s, 4)
            e["stud_extreme"][nm] = r
        ux, uy = L.P("f%d_ux" % k), L.P("f%d_uy" % k)
        nx, ny = -uy, ux
        for nm, (ox, oy) in (("0.6 along", (0.6 * ux, 0.6 * uy)), ("0.7 across", (0.7 * nx, 0.7 * ny)),
                             ("slot end (shank limit)", (e["stud_extreme"]["+along (to glass)"]["offset_mm"] * ux,
                                                         e["stud_extreme"]["+along (to glass)"]["offset_mm"] * uy))):
            e["washer_M4_bearing_mm2"][nm] = slice_area(fr, fx + ox, fy + oy, ztt, -1, L.P("w4_od"), L.P("w4_id"))
        # R4 head edge -> cut-out corner arc (nominal), analytic
        sc, rc = L.P("s_cut"), L.P("R_cut")
        cx0, cx1, cy0, cy1 = L.P("glass_x0") - sc, L.P("glass_x1") + sc, L.P("glass_y0") - sc, L.P("glass_y1") + sc
        ccx = cx0 + rc if fx < L.P("gc_x") else cx1 - rc
        ccy = cy0 + rc if fy < L.P("gc_y") else cy1 - rc
        d_axis = math.hypot(fx - ccx, fy - ccy) - rc
        e["axis_to_cutout_corner_arc_mm"] = round(d_axis, 4)
        e["R4_head_edge_to_cutout_mm"] = round(d_axis - L.P("riv_head_d") / 2, 4)
        res["F"]["F%d" % k] = e
    # summary
    allc = [res["F"][f]["stud_centred"]["flange_env_d_mm"] for f in res["F"]]
    allt = [v["flange_env_d_mm"] for f in res["F"] for v in res["F"][f]["stud_tol"].values()]
    alle = [v["flange_env_d_mm"] for f in res["F"] for v in res["F"][f]["stud_extreme"].values()]
    sht = [v["shank_d_mm"] for f in res["F"] for v in res["F"][f]["stud_tol"].values()]
    rst = [v for f in res["F"] for v in res["F"][f]["rivet_shank_tol"].values()]
    ov = [v["flange_overlap_mm3"] for f in res["F"] for v in list(res["F"][f]["stud_tol"].values()) +
          list(res["F"][f]["stud_extreme"].values())]
    res["summary"] = {"flange_env_min_centred": min(allc), "flange_env_min_tol0.3": min(allt),
                      "flange_env_min_extreme": min(alle), "stud_shank_min_tol0.3": min(sht),
                      "rivet_shank_min_tol0.3": min(rst), "max_flange_overlap_mm3": max(ov),
                      "washer_M4_centred": [res["F"][f]["washer_M4_bearing_mm2"]["centred"] for f in res["F"]],
                      "washer_M4_min_tol0.3": min(v for f in res["F"] for kk, v in res["F"][f]["washer_M4_bearing_mm2"].items()
                                                  if kk.startswith("0.3")),
                      "washer_M5_centred": [res["F"][f]["washer_M5_bearing_mm2"]["centred"] for f in res["F"]],
                      "R4_pad_face_centred": [res["F"][f]["R4_pad_face_under_head_mm2"]["centred"] for f in res["F"]],
                      "R4_pad_face_min_tol0.3": min(v for f in res["F"] for kk, v in res["F"][f]["R4_pad_face_under_head_mm2"].items()
                                                    if kk.startswith("0.3")),
                      "R4_head_edge_to_cutout": [res["F"][f]["R4_head_edge_to_cutout_mm"] for f in res["F"]],
                      "extreme_offsets": {f: {kk: v["offset_mm"] for kk, v in res["F"][f]["stud_extreme"].items()}
                                          for f in res["F"]}}
    res["seconds"] = round(time.time() - t0, 1)
    p = L.dump(res, DUMP + "/fasteners.json")
    print(p, res["seconds"])
    for kk, v in res["summary"].items():
        print(kk, v)
