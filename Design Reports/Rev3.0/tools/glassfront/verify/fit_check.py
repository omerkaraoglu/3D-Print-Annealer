"""D. Fit of the frame STEP against an assembly built independently from the params (simple solids) and against the
real board (kicad-cli STEP with every model; DS1 panel incl. its folded tails moved with the panel to Z_PANEL_BACK).

  <venv>\\Scripts\\python.exe fit_check.py [--frame f.step] [--params p.json] [--board b.step]

Built here from the params only (glass_t as frozen): glass (rounded rectangle, no arris), LOCA, panel envelope,
Formex (panel - 0.5/side, R1, v2), bead ring (0.9..4.9 inside the glass edge, Z_GLASS_BACK..Z_LAND), 4 VHB strips
(s 3.9..15.9, compressed to t_gap), oven sheet with the cut-out, M4 x 16 studs on the sheet back (S4: F1-F4, S8:
F1-F8), S8 spacers (GF-1.1: DIN 988 6 x 12 x 1.0 shim; GF-1.0: DIN 9021 M4 12 x 1.0) at F5-F8, CD weld-stud base
flange dia 5.7 x 1.4 (GF-1.1), DIN 9021 M4 washers + ISO 10511 M4 nylocs (AF 7, h 5.0) on the
tube tops, R4 rivets (dia 4.8 body, head dia 10 x 1.5 on the sheet front, DIN 9021 M5 15 x 1.2 backing washer,
blind-side envelope ASSUMED dia 12 x 10 mm).
Checks: gaps glass-lip (g2) and lip-sheet (g1) all round and at the corners, 20 / -20 / +70 C (+50 C sheet),
CLTE frame 50 (design) / 70 (bound) ppm/K, glass 9, steel 12, about the glass centre (radial slots); flush plane;
bead and pips; panel vs clearance pocket and Formex; print window vs AA and the CTP view area; FPC tails vs frame /
glass / bead / tail pocket (>= 1.5 to the frame); frame vs every component model and the PCB; v2 electrical checks
(Z 0 contact faces vs B.Cu pads >= 1.0, mains creepage >= 6.4, clearance >= 4.0, lead protrusions vs Formex,
nothing above Z 0 inside the board outline + 1); tool access (dia-12 socket) at F1-F8 vs board and frame; washer
bearing; rivet blind side and grip.
Output: out/fitcheck.json, out/fitcheck.txt
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

import vcommon as C

EXACT_BELOW = 5.0
TAIL_MIN = 1.5
TOOL_D = 12.0
TOOL_TOP = 45.0
TOOL_BELOW_TOP = 0.5
TOOL_WARN = 1.0
ABOVE_PCB_MARGIN = 1.0
CREEPAGE_REQ, CLEARANCE_REQ = 6.4, 4.0
PAD_CLR = 1.0
FORMEX_INSET, FORMEX_R = 0.5, 1.0          # v2 sheet (Formex) = panel outline - 0.5 / side, R1
STUD_D, STUD_L = 4.0, 16.0                 # M4 x 16 CD weld stud
WASHER_M4 = (12.0, 4.3, 1.0)               # DIN 9021 M4: OD, ID, t
WASHER_M5 = (15.0, 5.3, 1.2)               # DIN 9021 M5
NUT_AC, NUT_H = 8.08, 5.0                  # ISO 10511 M4: across corners (AF 7), height (envelope cylinder)
RIVET_D, RIVET_HEAD = 4.8, (10.0, 1.5)     # dia 4.8, dome head dia 10 x 1.5 proud (concept 4.6: 1.5-2.0)
RIVET_BLIND = (12.0, 10.0)                 # ASSUMED blind-side envelope: dia 12, 10 mm beyond the backing washer
WELD_FLANGE = (5.7, 1.4)                   # ISO 13918 PT M4 CD weld stud base flange, worst case of dia 5.3-5.7 x 0.7-1.4 (params)
WELD_FLANGE_MIN_D = 5.3                    # smallest flange: most play of the S8 shim on it
SHIM_S8 = (12.0, 6.0, 1.0)                 # DIN 988 6 x 12 x 1.0 (GF-1.1 S8 spacer): OD, ID, t
SLOT_DRAFT = 0.5                           # deg, slot walls (verified in A)
ALPHA = {"glass": 9e-6, "steel": 12e-6, "frame_design": 50e-6, "frame_bound": 70e-6}
T_ASM = 20.0


# ----------------------------------------------------------------------------------------------- assembly
def build(G):
    L = G.L
    gx0, gx1, gy0, gy1, gR = G.GLASS
    P = {}
    P["glass"] = C.prism(gx0, gx1, gy0, gy1, L["Z_GLASS_FRONT"], L["Z_GLASS_BACK"], r=gR)
    px0, px1, py0, py1 = G.PANEL
    P["loca"] = C.prism(px0, px1, py0, py1, L["Z_GLASS_BACK"], L["Z_CTP_FRONT"], r=0.5)
    P["panel_env"] = C.prism(px0, px1, py0, py1, L["Z_CTP_FRONT"], L["Z_PANEL_BACK"])
    P["formex"] = C.prism(px0 + FORMEX_INSET, px1 - FORMEX_INSET, py0 + FORMEX_INSET, py1 - FORMEX_INSET,
                          L["Z_FORMEX_FRONT"], L["Z_SEAT"], r=FORMEX_R)
    bo, bi = G.bead_edge, G.bead_edge + G.bead_w
    P["bead"] = C.ring((gx0 + bo, gx1 - bo, gy0 + bo, gy1 - bo, gR - bo),
                       (gx0 + bi, gx1 - bi, gy0 + bi, gy1 - bi, max(gR - bi, 0.3)), L["Z_GLASS_BACK"], L["Z_LAND"])
    # VHB strips: s 3.9 .. 15.9, compressed between the flange front and the sheet back
    s0, s1 = G.t_gap * 0 + 3.9, 15.9
    lt, ls = 183.48, 145.83
    cx, cy = G.GC
    zt0, zt1 = L["Z_SHEET_BACK"], L["Z_FLANGE_FRONT"]
    P["tape_top"] = C.prism(cx - lt / 2, cx + lt / 2, gy0 - s1, gy0 - s0, zt0, zt1)
    P["tape_bottom"] = C.prism(cx - lt / 2, cx + lt / 2, gy1 + s0, gy1 + s1, zt0, zt1)
    P["tape_left"] = C.prism(gx0 - s1, gx0 - s0, cy - ls / 2, cy + ls / 2, zt0, zt1)
    P["tape_right"] = C.prism(gx1 + s0, gx1 + s1, cy - ls / 2, cy + ls / 2, zt0, zt1)
    # oven sheet patch with the cut-out (no stud holes for S4/S8; R4 holes separately)
    fx0, fx1, fy0, fy1, _ = G.FLANGE
    cut = G.CUT
    sheet = C.prism(fx0 - 15, fx1 + 15, fy0 - 15, fy1 + 15, L["Z_GLASS_FRONT"], L["Z_SHEET_BACK"], r=5.0)
    sheet = sheet.cut(C.prism(cut[0], cut[1], cut[2], cut[3], L["Z_GLASS_FRONT"] - 1, L["Z_SHEET_BACK"] + 1, r=cut[4]))
    P["sheet"] = sheet
    return P


def hardware(G, variant):
    L = G.L
    out = {}
    names = G.stud_names(variant)
    for n in names:
        x, y = G.fxy(n)
        if variant in ("S4", "S8"):
            zs = L["Z_SHEET_BACK"]
            if G.cb:    # GF-1.1: CD weld stud with its base flange (worst case dia 5.7 x 1.4) in the counterbore
                out["stud flange " + n] = C.cyl(x, y, zs, zs + WELD_FLANGE[1], WELD_FLANGE[0])
                out["stud " + n] = C.cyl(x, y, zs + WELD_FLANGE[1], zs + STUD_L, STUD_D)
            else:
                out["stud " + n] = C.cyl(x, y, zs, zs + STUD_L, STUD_D)
            out["washer " + n] = C.tube(x, y, L["Z_TUBE_TOP"], L["Z_TUBE_TOP"] + WASHER_M4[2], WASHER_M4[0], WASHER_M4[1])
            zn = L["Z_TUBE_TOP"] + WASHER_M4[2]
            out["nut " + n] = C.tube(x, y, zn, zn + NUT_H, NUT_AC, 4.0)
            if variant == "S8" and n in ("F5", "F6", "F7", "F8"):
                sp = SHIM_S8 if G.cb else (WASHER_M4[0], WASHER_M4[1], 1.0)
                out["spacer " + n] = C.tube(x, y, L["Z_SHEET_BACK"], L["Z_FLANGE_FRONT"], sp[0], sp[1])
        else:   # R4 rivet
            out["rivet " + n] = C.cyl(x, y, L["Z_GLASS_FRONT"], L["Z_TUBE_TOP"] + WASHER_M5[2], RIVET_D)
            out["rivet head " + n] = C.cyl(x, y, L["Z_GLASS_FRONT"] - RIVET_HEAD[1], L["Z_GLASS_FRONT"], RIVET_HEAD[0])
            out["backing washer " + n] = C.tube(x, y, L["Z_TUBE_TOP"], L["Z_TUBE_TOP"] + WASHER_M5[2], WASHER_M5[0], WASHER_M5[1])
            zb = L["Z_TUBE_TOP"] + WASHER_M5[2]
            out["rivet blind side " + n] = C.cyl(x, y, zb, zb + RIVET_BLIND[1], RIVET_BLIND[0])
    return out


# ----------------------------------------------------------------------------------------------- GF-1.1 fastener seats
def _slot_hw_front(G, n):
    """slot half-width at its front end (the counterbore floor in GF-1.1), from the verified 0.5 deg draft"""
    zfront = G.cb_floor_z(n) if G.cb else (G.L["Z_SHEET_BACK"] if n in ("F1", "F2", "F3", "F4") else G.L["Z_FLANGE_FRONT"])
    return G.slot_w / 2 + (zfront - G.L["Z_FLANGE_FRONT"]) * math.tan(math.radians(SLOT_DRAFT))


def _positions(G, n, body_r):
    """centre + extreme positions of a round body of radius body_r in the slot: (label, a along, b across)"""
    hw = _slot_hw_front(G, n)
    d = hw - body_r - 1e-4
    seg = (G.slot_l - G.slot_w) / 2
    return [("centred", 0.0, 0.0), ("across +", 0.0, d), ("across -", 0.0, -d), ("along + (slot end)", seg + d, 0.0),
            ("along - (slot end)", -seg - d, 0.0), ("end + across", seg, d), ("end - across", -seg, -d)], d


def _xy(G, n, a, b):
    x, y = G.fxy(n)
    u = G.slot_axis(n)
    h = math.hypot(*u)
    u = (u[0] / h, u[1] / h)
    v = (-u[1], u[0])
    return x + a * u[0] + b * v[0], y + a * u[1] + b * v[1]


def _cb_face_groups(fr, G, n):
    """counterbore walls / floor-round / floor faces of fastener n"""
    x, y = G.fxy(n)
    zo, zf = G.cb_open_z(n), G.cb_floor_z(n)
    walls, rounds, floor = [], [], []
    for f in fr.Faces():
        bb = f.BoundingBox()
        c = f.Center()
        if math.hypot(c.x - x, -c.y - y) > 5.5 or bb.zmin < zo - 0.01 or bb.zmax > zf + 0.01:
            continue
        a = C.axis_z_feature(f)
        if a and a[3] > 4.5:
            continue
        if C.is_plane_z(f):
            if abs(bb.zmin - zf) < 0.005:
                floor.append(f)
        elif bb.zmin >= zf - 0.35:
            rounds.append(f)
        else:
            walls.append(f)
    return walls, rounds, floor


def stud_seat_study(ctx, rows):
    """CD weld stud: base flange dia 5.7 x 1.4 (worst) on the sheet back, shank dia 4 - centred and at every extreme
    the slot allows (shank against the slot wall across, at the slot end along, and both); distances from the flange
    to the counterbore wall, floor round and floor, and the shank / flange overlap with the frame"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    zs = L["Z_SHEET_BACK"]
    res = {}
    for grp, names in (("F1-F4", ("F1", "F2", "F3", "F4")), ("F5-F8", ("F5", "F6", "F7", "F8"))):
        best = {"wall": (1e9, None), "floor round": (1e9, None), "floor": (1e9, None), "any": (1e9, None)}
        ov_max = 0.0
        per = []
        for n in names:
            walls, rounds, floor = _cb_face_groups(fr, G, n)
            gcomp = {"wall": cq.Compound.makeCompound(walls) if walls else None,
                     "floor round": cq.Compound.makeCompound(rounds) if rounds else None,
                     "floor": cq.Compound.makeCompound(floor) if floor else None}
            pos, d = _positions(G, n, STUD_D / 2)
            for lab, a, b in pos:
                px, py = _xy(G, n, a, b)
                fl = C.cyl(px, py, zs, zs + WELD_FLANGE[1], WELD_FLANGE[0])
                sh = C.cyl(px, py, zs + WELD_FLANGE[1], zs + STUD_L, STUD_D)
                ov = C.common_vol(fr, fl) + C.common_vol(fr, sh)
                ov_max = max(ov_max, ov)
                rec = {"stud": n, "position": lab, "offset_along": round(a, 4), "offset_across": round(b, 4), "overlap_mm3": round(ov, 5)}
                for k, comp in gcomp.items():
                    if comp is None:
                        continue
                    dd = C.dist(cq.Shape.cast(fl.wrapped), comp)
                    rec[k] = round(dd, 4)
                    if dd < best[k][0]:
                        best[k] = (dd, "%s %s" % (n, lab))
                dany = C.dist(fr, fl)
                rec["flange_to_frame"] = round(dany, 4)
                if dany < best["any"][0]:
                    best["any"] = (dany, "%s %s" % (n, lab))
                per.append(rec)
        res[grp] = {"min": {k: (round(v[0], 4), v[1]) for k, v in best.items()}, "max_overlap_mm3": ov_max,
                    "max_offset_from_slot_segment": round(d, 4), "positions": per}
        m = res[grp]["min"]
        rows.append(("stud seat", "%s CD weld stud flange %.1f x %.1f: min to counterbore wall / floor round / floor (7 positions each)" % (
            grp, WELD_FLANGE[0], WELD_FLANGE[1]), "%.3f (%s) / %.3f (%s) / %.3f" % (m["wall"][0], m["wall"][1], m["floor round"][0],
                                                                               m["floor round"][1], m["floor"][0]),
            "> 0 (no contact)", "PASS" if min(m["wall"][0], m["floor round"][0], m["floor"][0]) > 0 and ov_max < 1e-4 else "FAIL",
            "shank dia 4 against the slot wall: offset %.3f from the slot centre line; overlap with the frame %.5f mm3" % (d, ov_max)))
    return res


def rivet_study(ctx, rows):
    """R4: dia 4.8 rivet in the F1-F4 slots - body vs frame at the extremes, head (dia 10) support on the pad face round
    the counterbore, and the DIN 9021 M5 backing washer (15 / 5.3) on the cored tube top (seat / outer skin)"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    out = []
    pads = C.faces_at_z(fr, L["Z_SHEET_BACK"], -1, tol=0.005)
    tops = C.faces_at_z(fr, L["Z_TUBE_TOP"], +1, tol=0.005)
    for n in ("F1", "F2", "F3", "F4"):
        x, y = G.fxy(n)
        pad = [f for f in pads if math.hypot(f.Center().x - x, -f.Center().y - y) < 3]
        # [seat (inside the groove), outer skin (outside it)] told apart by their outer radius, not by area
        top = sorted([f for f in tops if math.hypot(f.Center().x - x, -f.Center().y - y) < 3],
                     key=lambda f: max(f.BoundingBox().xlen, f.BoundingBox().ylen))
        pos, d = _positions(G, n, RIVET_D / 2)
        for lab, a, b in pos:
            px, py = _xy(G, n, a, b)
            body = C.cyl(px, py, L["Z_GLASS_FRONT"], L["Z_TUBE_TOP"] + WASHER_M5[2], RIVET_D)
            ov = C.common_vol(fr, body)
            head = C.cyl(px, py, L["Z_SHEET_BACK"] - 0.5, L["Z_SHEET_BACK"] + 0.5, RIVET_HEAD[0])
            sup = sum(ff.Area() for f in pad for ff in C.common_shape(f, head).Faces())
            ann = C.tube(px, py, L["Z_TUBE_TOP"] - 0.5, L["Z_TUBE_TOP"] + 0.5, WASHER_M5[0], WASHER_M5[1])
            a_faces = [sum(ff.Area() for ff in C.common_shape(f, ann).Faces()) for f in top]
            # head rim over the counterbore: fraction of the head circle (r 5) lying over the counterbore opening
            pts_rim = [(px + 5.0 * math.cos(t), py + 5.0 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 180, endpoint=False)]
            rim_over = (sum(1 for qx, qy in pts_rim if _in_stadium(G, n, qx, qy, float(G.cb["cb_w"]) / 2,
                                                                   (float(G.cb["cb_l"]) - float(G.cb["cb_w"])) / 2)) / len(pts_rim)) if G.cb else 0.0
            out.append({"stud": n, "position": lab, "overlap_mm3": round(ov, 5), "head_support_mm2": round(sup, 2),
                        "head_rim_over_counterbore": round(rim_over, 3),
                        "m5_washer_on_seat_mm2": round(a_faces[0], 2) if a_faces else None,
                        "m5_washer_on_outer_skin_mm2": round(a_faces[1], 2) if len(a_faces) > 1 else None})
    smin = min(out, key=lambda r: r["head_support_mm2"])
    rows.append(("rivet", "R4 rivet dia 4.8 in the F1-F4 slots at 7 positions: overlap with the frame", "%.5f mm3 max" % max(r["overlap_mm3"] for r in out),
                 "0", "PASS" if max(r["overlap_mm3"] for r in out) < 1e-4 else "FAIL", "offset up to %.3f from the slot centre line" % d))
    if G.cb:
        cent = [r for r in out if r["position"] == "centred"][0]
        rows.append(("rivet", "R4 rivet head dia 10: pad face under it (sheet clamped against the pad) centred / worst",
                     "%.1f / %.1f mm2 (%s); rim over the counterbore %.0f %% centred" % (
                         cent["head_support_mm2"], smin["head_support_mm2"], smin["position"], 100 * cent["head_rim_over_counterbore"]),
                     "INFO (GF-1.0: %.1f)" % (math.pi * 25 - math.pi * (5.2 / 2) ** 2), "INFO",
                     "inside the counterbore (7.4 x 9.0) the 1.0 sheet is unsupported under the head: the setting load bends it into the counterbore"))
        sk = [r["m5_washer_on_outer_skin_mm2"] or 0 for r in out]
        se = [r["m5_washer_on_seat_mm2"] or 0 for r in out]
        rows.append(("rivet", "DIN 9021 M5 backing washer (15/5.3) on the cored tube top: seat area / on the outer skin (bridging)",
                     "seat %.1f..%.1f mm2, outer skin %.1f..%.1f mm2 (centred %.1f)" % (min(se), max(se), min(sk), max(sk), cent["m5_washer_on_outer_skin_mm2"] or 0),
                     "seat carries it; bridging claimed", "INFO",
                     "washer OD r 7.5 = groove outer radius at the top: centred it only reaches the groove edge (no bridge); offset it bridges on one side"))
    return out


def _in_stadium(G, n, qx, qy, half_w, half_seg):
    x, y = G.fxy(n)
    u = G.slot_axis(n)
    h = math.hypot(*u)
    u = (u[0] / h, u[1] / h)
    a = (qx - x) * u[0] + (qy - y) * u[1]
    b = -(qx - x) * u[1] + (qy - y) * u[0]
    a = max(-half_seg, min(half_seg, a)) - a
    return math.hypot(a, b) < half_w


def washer_shim_study(ctx, rows):
    """DIN 9021 M4 washer on the cored tube top at the stud extremes; DIN 988 S8 shim (6/12/1.0) bearing on the flange
    front round the F5-F8 counterbore at the stud extremes (shim shifted 0.15 more on its 6.0 bore round the 5.7 flange)"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    tops = C.faces_at_z(fr, L["Z_TUBE_TOP"], +1, tol=0.005)
    fronts = C.faces_at_z(fr, L["Z_FLANGE_FRONT"], -1, tol=0.005)
    wrows, srows = [], []
    for n in G.stud_names("S8"):
        x, y = G.fxy(n)
        top = [f for f in tops if math.hypot(f.Center().x - x, -f.Center().y - y) < 3]
        pos, d = _positions(G, n, STUD_D / 2)
        for lab, a, b in pos:
            px, py = _xy(G, n, a, b)
            ann = C.tube(px, py, L["Z_TUBE_TOP"] - 0.5, L["Z_TUBE_TOP"] + 0.5, WASHER_M4[0], WASHER_M4[1])
            wrows.append({"stud": n, "position": lab, "area_mm2": round(sum(ff.Area() for f in top for ff in C.common_shape(f, ann).Faces()), 2)})
        if n in ("F5", "F6", "F7", "F8") and G.cb:
            play = (SHIM_S8[1] - WELD_FLANGE_MIN_D) / 2      # smallest flange = most shim play (worst for the bearing)
            for lab, a, b in pos:
                # shim pushed a further 'play' outwards along the stud's offset direction (worst for the bearing)
                hh = math.hypot(a, b)
                aa, bb = (a + play * a / hh, b + play * b / hh) if hh > 1e-9 else (a, b)
                px, py = _xy(G, n, aa, bb)
                ann = C.tube(px, py, L["Z_FLANGE_FRONT"] - 0.5, L["Z_FLANGE_FRONT"] + 0.5, SHIM_S8[0], SHIM_S8[1])
                ar = sum(ff.Area() for f in fronts for ff in C.common_shape(f, ann).Faces())
                srows.append({"stud": n, "position": lab, "area_mm2": round(ar, 2)})
    # a realistic offset: stud position +-0.2 (welding template) and slot position +-0.1 (RSS ~0.22) + differential
    # expansion along the radial slot (frame 50-70 ppm vs steel, +70 / -20 C: ~0.2 at F5-F8 .. ~0.4 at F1-F4) ~ 0.6
    n0 = G.stud_names("S8")[0]
    x0_, y0_ = G.fxy(n0)
    top0 = [f for f in tops if math.hypot(f.Center().x - x0_, -f.Center().y - y0_) < 3]
    px, py = _xy(G, n0, 0.6, 0.0)
    ann = C.tube(px, py, L["Z_TUBE_TOP"] - 0.5, L["Z_TUBE_TOP"] + 0.5, WASHER_M4[0], WASHER_M4[1])
    a05 = sum(ff.Area() for f in top0 for ff in C.common_shape(f, ann).Faces())
    wrows.append({"stud": n0, "position": "along 0.6 (realistic)", "area_mm2": round(a05, 2)})
    wmin = min(wrows, key=lambda r: r["area_mm2"])
    wcen = min(r["area_mm2"] for r in wrows if r["position"] == "centred")
    rows.append(("hardware", "DIN 9021 M4 washer (12/4.3) on the cored tube tops: centred / worst stud position",
                 "%.1f / %.1f mm2 (%s %s) -> %.1f / %.1f MPa at 500 N" % (wcen, wmin["area_mm2"], wmin["stud"], wmin["position"],
                                                                           500 / wcen, 500 / wmin["area_mm2"]),
                 ">= 80 (params, centred); creep limit 15 MPa", "PASS" if wcen >= 80 - 0.5 and 500 / wmin["area_mm2"] < 15 else "FAIL",
                 "off-centre the washer overhangs the coring groove (r 6.2-7.5); at a realistic ~0.6 along the slot (tolerances + expansion) %.1f mm2 (%.1f MPa)" % (
                     a05, 500 / a05)))
    if srows:
        smin = min(srows, key=lambda r: r["area_mm2"])
        scen = min(r["area_mm2"] for r in srows if r["position"] == "centred")
        rows.append(("hardware", "S8 shim DIN 988 6x12x1.0 on the flange front round the F5-F8 counterbore: centred / worst",
                     "%.1f / %.1f mm2 (%s %s)" % (scen, smin["area_mm2"], smin["stud"], smin["position"]),
                     "> 0, ring all round", "PASS" if smin["area_mm2"] > 10 else "FAIL",
                     "worst = stud at the slot extreme and the shim a further %.2f off on its bore (flange dia %.1f); with the "
                     "dia-%.1f flange the shim bore leaves %.2f radial for weld flash" % (
                         (SHIM_S8[1] - WELD_FLANGE_MIN_D) / 2, WELD_FLANGE_MIN_D, WELD_FLANGE[0], (SHIM_S8[1] - WELD_FLANGE[0]) / 2)))
    return {"washer": wrows, "shim": srows}


# ----------------------------------------------------------------------------------------------- gaps
def s_rrect(rect, x, y):
    """signed distance outward from a rounded rectangle (x0, x1, y0, y1, R)"""
    x0, x1, y0, y1, R = rect
    R = R or 0.0
    cx = min(max(x, x0 + R), x1 - R)
    cy = min(max(y, y0 + R), y1 - R)
    dx, dy = x - cx, y - cy
    if (x0 + R <= x <= x1 - R) or (y0 + R <= y <= y1 - R):
        return max(x0 - x, x - x1, y0 - y, y - y1)
    return math.hypot(dx, dy) - R


def rrect_pts(rect, step=0.05):
    x0, x1, y0, y1, R = rect
    return C.densify(C.rrect_wire_pts(x0, x1, y0, y1, R, n=60), step)


def thermal_shift(G, pts_outline, normal_pts, alpha_a, dT_a, alpha_b, dT_b):
    """change of the gap between outline A (inside, e.g. glass) and outline B (outside, e.g. lip) at each point:
    B grows by alpha_b dT_b about the glass centre, A by alpha_a dT_a -> gap change = (alpha_b dT_b - alpha_a dT_a) (P.n)"""
    cx, cy = G.GC
    d = (alpha_b * dT_b - alpha_a * dT_a)
    return d * np.einsum("ij,ij->i", pts_outline - np.array([cx, cy]), normal_pts)


def outward_normals(rect, P):
    x0, x1, y0, y1, R = rect
    out = []
    for x, y in P:
        cx = min(max(x, x0 + R), x1 - R)
        cy = min(max(y, y0 + R), y1 - R)
        dx, dy = x - cx, y - cy
        h = math.hypot(dx, dy)
        if h < 1e-9:
            if min(abs(x - x0), abs(x - x1)) < min(abs(y - y0), abs(y - y1)):
                out.append((-1.0 if abs(x - x0) < abs(x - x1) else 1.0, 0.0))
            else:
                out.append((0.0, -1.0 if abs(y - y0) < abs(y - y1) else 1.0))
        else:
            out.append((dx / h, dy / h))
    return np.array(out)


def gaps(ctx, rows):
    G, fr = ctx.G, ctx.frame
    L = G.L
    res = {}
    # lip loops from the STEP at three heights: just behind the top rounds, mid, just above the root fillet
    heights = {"front (Z_GLASS_FRONT + 0.32, below the R0.3 rounds)": L["Z_GLASS_FRONT"] + 0.32,
               "mid-lip": (L["Z_GLASS_FRONT"] + L["Z_SHEET_BACK"]) / 2,
               "root (Z_SHEET_BACK - 0.21, above the R0.2 root)": L["Z_SHEET_BACK"] - 0.21}
    glass_pts = rrect_pts(G.GLASS)
    cut_pts = rrect_pts(G.CUT)
    n_glass = outward_normals(G.GLASS, glass_pts)
    n_cut = outward_normals(G.CUT, cut_pts)
    is_corner_g = np.array([not ((G.GLASS[0] + G.GLASS[4] <= x <= G.GLASS[1] - G.GLASS[4]) or
                                 (G.GLASS[2] + G.GLASS[4] <= y <= G.GLASS[3] - G.GLASS[4])) for x, y in glass_pts])
    is_corner_c = np.array([not ((G.CUT[0] + G.CUT[4] <= x <= G.CUT[1] - G.CUT[4]) or
                                 (G.CUT[2] + G.CUT[4] <= y <= G.CUT[3] - G.CUT[4])) for x, y in cut_pts])
    meas = {}
    meas_loops = {}
    for hn, z in heights.items():
        loops = C.plan_loops(fr, z)
        # lip inner loop = the inner loop of the face that contains the lip; lip outer = its outer loop
        lipface = None
        for l in loops:
            if l["outer"] and np.ptp(l["pts"][:, 0]) > 180 and np.ptp(l["pts"][:, 0]) < 186:
                lipface = l["face"]
        inner = [l["pts"] for l in loops if l["face"] == lipface and not l["outer"]]
        outer = [l["pts"] for l in loops if l["face"] == lipface and l["outer"]]
        if not inner or not outer:
            continue
        ti, to = cKDTree(C.densify(inner[0], 0.02)), cKDTree(C.densify(outer[0], 0.02))
        g2 = ti.query(glass_pts)[0]
        g1 = to.query(cut_pts)[0]
        meas[hn] = (g2, g1)
        meas_loops[hn] = (inner[0], outer[0])
        fi_ = C.rrect_fit(inner[0], G.LIP_IN)
        fo_ = C.rrect_fit(outer[0], G.LIP_OUT)
        res.setdefault("corner_radii", {})[hn] = {
            "lip_inner_R": {k: round(c["R"], 4) for k, c in fi_["corners"].items()},
            "lip_outer_R": {k: round(c["R"], 4) for k, c in fo_["corners"].items()},
            "lip_inner_centre_offset": {k: round(math.hypot(c["cx"] - (G.LIP_IN[0] + G.LIP_IN[4] if k in ("TL", "BL") else G.LIP_IN[1] - G.LIP_IN[4]),
                                                            c["cy"] - (G.LIP_IN[2] + G.LIP_IN[4] if k in ("TL", "TR") else G.LIP_IN[3] - G.LIP_IN[4])), 4)
                                        for k, c in fi_["corners"].items()},
            "params": {"glass_R": G.GLASS[4], "lip_in_R": G.LIP_IN[4], "lip_out_R": G.LIP_OUT[4], "cut_R": G.CUT[4]}}
        res[hn] = {"z": round(z, 3),
                   "g2_sides_min_max": [round(float(g2[~is_corner_g].min()), 4), round(float(g2[~is_corner_g].max()), 4)],
                   "g2_corners_min_max": [round(float(g2[is_corner_g].min()), 4), round(float(g2[is_corner_g].max()), 4)],
                   "g1_sides_min_max": [round(float(g1[~is_corner_c].min()), 4), round(float(g1[~is_corner_c].max()), 4)],
                   "g1_corners_min_max": [round(float(g1[is_corner_c].min()), 4), round(float(g1[is_corner_c].max()), 4)]}
    hf = list(heights)[0]
    hr = list(heights)[2]
    g2f, g1f = meas[hf]
    g2r, g1r = meas[hr]
    sides_ok = abs(g2f[~is_corner_g].min() - G.g2) < 0.012 and abs(g2f[~is_corner_g].max() - G.g2) < 0.012
    rows.append(("gaps", "g2 glass -> lip inner face, 20 C, 0.32 behind the flush plane: sides / corners",
                 "%.3f..%.3f / %.3f..%.3f" % (g2f[~is_corner_g].min(), g2f[~is_corner_g].max(), g2f[is_corner_g].min(), g2f[is_corner_g].max()),
                 "0.40 sides, >= 0.40 corners", "PASS" if sides_ok and g2f[is_corner_g].min() > G.g2 - 0.012 else "FAIL",
                 "at the flush plane add 0.32 x tan(1 deg) = 0.006"))
    rows.append(("gaps", "g1 lip outer face -> cut-out, 20 C, 0.32 behind the flush plane: sides / corners",
                 "%.3f..%.3f / %.3f..%.3f" % (g1f[~is_corner_c].min(), g1f[~is_corner_c].max(), g1f[is_corner_c].min(), g1f[is_corner_c].max()),
                 "0.4175 sides at the flush plane, >= corners", "INFO", ""))
    cr = res["corner_radii"][hf]
    concentric = abs(G.GLASS[4] + G.g2 - G.LIP_IN[4]) < 1e-6 and abs(G.CUT[4] - G.g1 - G.LIP_OUT[4]) < 1e-6
    rows.append(("gaps", "corner radii (STEP, Z %.2f): lip inner / lip outer; params glass R%.2f, cut-out R%.2f" % (
        heights[hf], G.GLASS[4], G.CUT[4]),
        "inner %.4f..%.4f, outer %.4f..%.4f, centres on R_frame %.2f corners (offset <= %.4f)" % (
            min(cr["lip_inner_R"].values()), max(cr["lip_inner_R"].values()), min(cr["lip_outer_R"].values()),
            max(cr["lip_outer_R"].values()), G.R_frame, max(cr["lip_inner_centre_offset"].values())),
        "%.4f / %.4f at this Z (lip_in R%.1f at the top, lip_out R%.1f at the root, 1 deg)" % (
            G.LIP_IN[4] - math.tan(math.radians(1)) * (heights[hf] - L["Z_GLASS_FRONT"]),
            G.LIP_OUT[4] - math.tan(math.radians(1)) * (L["Z_SHEET_BACK"] - heights[hf]), G.LIP_IN[4], G.LIP_OUT[4]),
        "PASS" if abs(min(cr["lip_inner_R"].values()) - (G.LIP_IN[4] - math.tan(math.radians(1)) * (heights[hf] - L["Z_GLASS_FRONT"]))) < 0.01 else "FAIL",
        ("concentric corners: corner gaps = side gaps" if concentric else
         "glass / cut-out corners NOT concentric with the lip (GF-1.1): the corner gaps open towards the diagonal")))
    rows.append(("gaps", "g1 lip outer face -> sheet cut-out, 20 C, at the flush plane / at the lip root",
                 "%.3f..%.3f / %.3f..%.3f" % (g1f.min(), g1f.max(), g1r.min(), g1r.max()), "0.4175 / 0.40 (as designed)", "INFO",
                 "lip_out is at the root, so the visible g1 at the front is 0.40 + 1 x tan(1deg) = 0.417 on the straight edges"))
    # ---- tolerance cases (glass: outline +-0.2 per side, corner R +-0.2 = the GF-1.1 glass drawing; cut-out: +-0.1, R +-0.1
    #      laser; lip: 0.04 frame position) and the thermal cases, at the flush-plane-near section hf
    ti_lip = cKDTree(C.densify(meas_loops[hf][0], 0.02))
    to_lip = cKDTree(C.densify(meas_loops[hf][1], 0.02))
    gx0, gx1, gy0, gy1, gR = G.GLASS
    cx0, cx1, cy0, cy1, cR = G.CUT
    g_cases = {"nominal": ((gx0, gx1, gy0, gy1, gR), 0.0),
               "glass profile +0.2 (offset outline)": ((gx0 - 0.2, gx1 + 0.2, gy0 - 0.2, gy1 + 0.2, gR + 0.2), 0.0),
               "glass +0.2/side and R -0.2 (size + radius tolerances)": ((gx0 - 0.2, gx1 + 0.2, gy0 - 0.2, gy1 + 0.2, gR - 0.2), 0.0),
               "glass nominal size, R -0.2": ((gx0, gx1, gy0, gy1, gR - 0.2), 0.0),
               # alternative drawing callout (proposal): R +0.2/-0, worst = size +0.2 with R at its minimum (nominal)
               "glass +0.2/side, R nominal (R +0.2/-0 callout)": ((gx0 - 0.2, gx1 + 0.2, gy0 - 0.2, gy1 + 0.2, gR), 0.0)}
    c_cases = {"nominal": ((cx0, cx1, cy0, cy1, cR), 0.0),
               "cut-out profile -0.1, lip +0.04": ((cx0 + 0.1, cx1 - 0.1, cy0 + 0.1, cy1 - 0.1, cR - 0.1), 0.04),
               "cut-out -0.1/side and R +0.1, lip +0.04": ((cx0 + 0.1, cx1 - 0.1, cy0 + 0.1, cy1 - 0.1, cR + 0.1), 0.04),
               # alternative callout (proposal): R +0/-0.2, worst = size -0.1 with R at its maximum (nominal)
               "cut-out -0.1/side, R nominal (R +0/-0.2 callout), lip +0.04": ((cx0 + 0.1, cx1 - 0.1, cy0 + 0.1, cy1 - 0.1, cR), 0.04)}
    temps = [("20 C", None, 0.0, 0.0, 0.0)] + [
        ("%s, %d ppm" % (case, round(ALPHA[fa] * 1e6)), fa, dTf, dTg, dTs)
        for fa in ("frame_design", "frame_bound")
        for case, dTf, dTg, dTs in (("-20 C", -40.0, -40.0, -40.0), ("+70 C frame/glass, +50 C sheet", 50.0, 50.0, 30.0))]
    def corner_masks(rect, P):
        x0, x1, y0, y1, Rr = rect
        cm = np.array([not ((x0 + Rr <= x <= x1 - Rr) or (y0 + Rr <= y <= y1 - Rr)) for x, y in P])
        cxs = np.where(P[:, 0] < (x0 + x1) / 2, x0 + Rr, x1 - Rr)
        cys = np.where(P[:, 1] < (y0 + y1) / 2, y0 + Rr, y1 - Rr)
        ang = np.degrees(np.arctan2(np.abs(P[:, 1] - cys), np.abs(P[:, 0] - cxs)))
        diag = cm & (np.abs(ang - 45.0) < 3.0)
        return cm, diag
    table = {"g2": {}, "g1": {}}
    for tag, cases, tree, alpha_other in (("g2", g_cases, ti_lip, "glass"), ("g1", c_cases, to_lip, "steel")):
        for cname, (rect, lipt) in cases.items():
            P = rrect_pts(rect)
            Nn = outward_normals(rect, P)
            cm, dg = corner_masks(rect, P)
            g0 = tree.query(P)[0] - lipt
            for tname, fa, dTf, dTg, dTs in temps:
                if fa is None:
                    gg = g0
                elif tag == "g2":
                    gg = g0 + thermal_shift(G, P, Nn, ALPHA["glass"], dTg, ALPHA[fa], dTf)
                else:
                    gg = g0 - thermal_shift(G, P, Nn, ALPHA["steel"], dTs, ALPHA[fa], dTf)
                table[tag].setdefault(tname, {})[cname] = {"sides_min": round(float(gg[~cm].min()), 3),
                                                           "corners_min": round(float(gg[cm].min()), 3),
                                                           "diagonal": round(float(gg[dg].mean()), 3)}
    res["tolerance_thermal"] = table
    for tag in ("g2", "g1"):
        for tname, cs_ in table[tag].items():
            nomv = cs_["nominal"]
            worst = min(cs_.items(), key=lambda kv: min(kv[1]["sides_min"], kv[1]["corners_min"]))
            wv = min(worst[1]["sides_min"], worst[1]["corners_min"])
            rows.append(("gaps", "%s at %s: sides / corner min / corner diagonal (nominal); worst tolerance case" % (tag, tname),
                         "%.3f / %.3f / %.3f; WC %.3f" % (nomv["sides_min"], nomv["corners_min"], nomv["diagonal"], wv),
                         "> 0 nominal (WC info)", "PASS" if min(nomv["sides_min"], nomv["corners_min"]) > 0 else "FAIL",
                         "WC case: %s (%s)" % (worst[0], "; ".join("%s %.3f/%.3f" % (k[:28], v["sides_min"], v["corners_min"])
                                                                for k, v in cs_.items() if k != "nominal"))))
    res["at_20C"] = {k: v for k, v in res.items() if k not in ("tolerance_thermal",)}
    return res


# ----------------------------------------------------------------------------------------------- other params-only checks
def plan_checks_params(ctx, rows):
    G = ctx.G
    L = G.L
    out = {}
    aa, pw, va = G.AA, G.PRINT, G.VA
    ins = [pw[0] - aa[0], aa[1] - pw[1], pw[2] - aa[2], aa[3] - pw[3]]
    rows.append(("print", "print window inside the active area (per side l/r/t/b)", " / ".join("%.2f" % v for v in ins), "0.30",
                 "PASS" if all(abs(v - G.drv["print_inset"]) < 0.005 for v in ins) else "FAIL", "AA from the panel DS, window R0.5"))
    insv = [pw[0] - va[0], va[1] - pw[1], pw[2] - va[2], va[3] - pw[3]]
    rows.append(("print", "print window inside the CTP cover-lens view area (l/r/t/b)", " / ".join("%.2f" % v for v in insv),
                 "> 0 (window hides the CTP print edge)", "PASS" if min(insv) > 0 else "FAIL", ""))
    out["print_inset_aa"], out["print_inset_va"] = ins, insv
    # flush plane
    rows.append(("flush", "glass front / lip top / sheet front", "%.2f / %.2f / %.2f" % (
        L["Z_GLASS_FRONT"], C.optimal_bbox(ctx.frame)[4], L["Z_SHEET_BACK"] - G.t_sheet), "one plane", "PASS"
        if abs(C.optimal_bbox(ctx.frame)[4] - L["Z_GLASS_FRONT"]) < 0.005 else "FAIL",
        "sheet seated on the seat ring at Z_SHEET_BACK; glass set on the lip plane by the jig"))
    return out


# ----------------------------------------------------------------------------------------------- 3D
def components(ctx, idx, A, rows, log=C.log):
    fr = ctx.frame
    comp_rows, panel_rows, lead_rows = [], [], []
    pcb = None
    formex = A["formex"]
    glass, bead = A["glass"], A["bead"]
    for ref, part, s in ctx.items:
        if ref == "PCB":
            pcb = s
            continue
        if ref == "DS1":
            dd, approx, ov, pf, po = idx.distance(s, EXACT_BELOW, points=True)
            row = {"part": part, "min_dist": round(dd, 3), "overlap_mm3": round(ov, 4), "approx": approx,
                   "at_abs": [round(po[0], 2), round(-po[1], 2), round(po[2], 2)] if po else None,
                   "to_formex": round(C.dist(formex, s), 3)}
            if part.startswith(C.PANEL_TAIL_PARTS):
                row["to_glass"] = round(C.dist(glass, s), 3)
                row["to_bead"] = round(C.dist(bead, s), 3)
            panel_rows.append(row)
            continue
        s_chk, trimmed = s, False
        if ref == "Q1":
            s_chk, trimmed = C.trim_below(s, -C.Q1_TRIM), True
        dd, approx, ov = idx.distance(s_chk, EXACT_BELOW)
        zmin = s_chk.BoundingBox().zmin
        comp_rows.append({"ref": ref, "part": part, "min_dist": round(dd, 3), "overlap_mm3": round(ov, 4),
                          "zmin": round(zmin, 2), "q1_trimmed": trimmed, "approx": approx})
        if zmin < -0.05:
            lead_rows.append({"ref": ref, "protrusion": round(-zmin, 2), "gap_to_formex": round(C.dist(formex, s_chk), 3),
                              "gap_to_frame": round(dd, 2)})
    comp_rows.sort(key=lambda r: r["min_dist"])
    lead_rows.sort(key=lambda r: r["gap_to_formex"])
    pcb_d, _, pcb_ov = idx.distance(pcb, EXACT_BELOW)
    tails = [r for r in panel_rows if r["part"].startswith(C.PANEL_TAIL_PARTS)]
    body = [r for r in panel_rows if not r["part"].startswith(C.PANEL_TAIL_PARTS)]
    log("    components %d, panel parts %d, tails %d" % (len(comp_rows), len(body), len(tails)))
    return {"components_checked": len(comp_rows), "component_overlaps": [r for r in comp_rows if r["overlap_mm3"] > 1e-4],
            "closest_components": comp_rows[:15],
            "components_all": [{"ref": r["ref"], "min_dist": r["min_dist"], "approx": r["approx"]} for r in comp_rows],
            "pcb_body": {"min_dist": round(pcb_d, 3), "overlap_mm3": round(pcb_ov, 4)},
            "panel_parts": body, "tails": tails, "lead_protrusions": lead_rows}


TAIL_SPLIT_Z = -2.1     # tails: below this they follow the panel (moved), above it they are held by J10/J11 (unmoved)


def tails_unmoved(ctx, idx):
    """the tails are glued to the panel at one end and clamped in J10/J11 on the PCB at the other, so a rigid shift
    with the panel is right only for the panel-side legs. Three cases per tail: unmoved (v2 position), moved, and the
    split model: moved part below TAIL_SPLIT_Z (shelf back) + unmoved part above it."""
    items = C.board_items(ctx.board_path, C.BOARD_DZ, 0.0)
    moved = {p: s for r, p, s in ctx.items if r == "DS1" and p.startswith(C.PANEL_TAIL_PARTS)}
    big = 500.0
    out = []
    for ref, part, s in items:
        if ref == "DS1" and part.startswith(C.PANEL_TAIL_PARTS):
            dd, approx, ov, pf, po = idx.distance(s, EXACT_BELOW, points=True)
            row = {"part": part, "unmoved_min_dist": round(dd, 3), "unmoved_at_abs": [round(po[0], 2), round(-po[1], 2), round(po[2], 2)] if po else None}
            lo = C.common_shape(moved[part], C.box(-big, big, -big, big, -big, TAIL_SPLIT_Z))
            hi = C.common_shape(s, C.box(-big, big, -big, big, TAIL_SPLIT_Z, big))
            ds = []
            for tag, piece in (("panel side (moved, Z < %.1f)" % TAIL_SPLIT_Z, lo), ("connector side (unmoved, Z > %.1f)" % TAIL_SPLIT_Z, hi)):
                if piece.Solids():
                    d2, ap2, ov2, pf2, po2 = idx.distance(piece, EXACT_BELOW, points=True)
                    ds.append((d2, tag, po2))
            if ds:
                d2, tag, po2 = min(ds, key=lambda q: q[0])
                row.update({"split_min_dist": round(d2, 3), "split_where": tag,
                            "split_at_abs": [round(po2[0], 2), round(-po2[1], 2), round(po2[2], 2)] if po2 else None})
            out.append(row)
    return out


def assembly_vs_frame(ctx, idx, A, HW, rows):
    fr = ctx.frame
    G = ctx.G
    out = {}
    for k in ("glass", "loca", "panel_env", "formex", "bead", "tape_top", "tape_bottom", "tape_left", "tape_right", "sheet"):
        s = cq.Shape.cast(A[k].wrapped) if hasattr(A[k], "wrapped") else A[k]
        d = C.dist(fr, s)
        v = C.common_vol(fr, s)
        out[k] = {"min_dist": round(d, 4), "overlap_mm3": round(v, 4)}
    for variant, hw in HW.items():
        for k, s in hw.items():
            d = C.dist(fr, s)
            v = C.common_vol(fr, s)
            out["%s %s" % (variant, k)] = {"min_dist": round(d, 4), "overlap_mm3": round(v, 4)}
    return out


# ----------------------------------------------------------------------------------------------- tool / washer / rivet
def tool_access(ctx, idx, rows, log=C.log):
    G = ctx.G
    L = G.L
    res = []
    for n in G.stud_names("S8"):
        x, y = G.fxy(n)
        z0 = L["Z_TUBE_TOP"] - TOOL_BELOW_TOP
        cyl_ = C.cyl(x, y, z0, TOOL_TOP, TOOL_D)
        ix = C.DistIndex(cq.Shape.cast(cyl_.wrapped))
        best, overl = (1e9, None, False), []
        for ref, part, s in ctx.items:
            d, approx, v = ix.distance(s, 2.0, skip_beyond=5.0)
            if v > 1e-4:
                overl.append({"ref": ref, "part": part, "overlap_mm3": round(v, 3)})
            if d < best[0]:
                best = (d, ("%s %s" % (ref, part) if ref == "DS1" else ref) + (" (lower bound: bbox gap / sampled)" if approx else ""), approx)
        # vs the frame: from the washer seat (tube top + 0.005) upwards
        cf = C.cyl(x, y, L["Z_TUBE_TOP"] + 0.005, TOOL_TOP, TOOL_D)
        df = C.dist(ctx.frame, cf)
        vf = C.common_vol(ctx.frame, cf)
        res.append({"hole": n, "x": x, "y": y, "board_min_dist": round(best[0], 2), "closest": best[1], "board_overlaps": overl,
                    "frame_min_dist": round(df, 3), "frame_overlap_mm3": round(vf, 4)})
    log("    tool access: board min %.2f, frame min %.3f" % (min(r["board_min_dist"] for r in res), min(r["frame_min_dist"] for r in res)))
    return res


def nothing_above_pcb(ctx, geom):
    outl = np.array(max(geom["outline"], key=lambda o: len(o)))
    w = cq.Wire.makePolygon([cq.Vector(x, C.Yc(y), 0) for x, y in outl], close=True)
    res = {"margin_mm": ABOVE_PCB_MARGIN}
    for tag, m in (("volume_mm3", ABOVE_PCB_MARGIN), ("volume_inside_outline_mm3", 0.0)):
        wo = w.offset2D(m, "arc")[0] if m > 0 else w
        region = cq.Solid.extrudeLinear(cq.Face.makeFromWires(wo), cq.Vector(0, 0, 60.0))
        com = C.common_shape(ctx.frame, region)
        vol = sum(abs(x.Volume()) for x in com.Solids()) if com.Solids() else 0.0
        res[tag] = round(vol, 4)
    fb = C.optimal_bbox(ctx.frame)
    sec = C.plane_section(ctx.frame, "z", 0.02) if fb[5] > 0.02 else None
    if sec is not None:
        pts = np.vstack([C.densify(l, 0.05) for f in sec.Faces() for l in C.face_loops_abs(f)])
        op = C.densify(outl, 0.05)
        dd, ii = cKDTree(op).query(pts)
        k = int(np.argmin(dd))
        inside = MPath(outl).contains_points(pts).any()
        res["plan_gap_above_z0_to_board_edge_mm"] = 0.0 if inside else round(float(dd[k]), 3)
        res["plan_gap_at_abs"] = [round(float(pts[k][0]), 2), round(float(pts[k][1]), 2)]
    res["ok"] = res["volume_mm3"] < 1e-3
    return res


# ----------------------------------------------------------------------------------------------- plan (electrical), v2 method
class Region:
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


def classify_point(G, x, y):
    for h, (hx, hy) in G.HOLES.items():
        if math.hypot(x - hx, y - hy) <= G.BOSS_OD / 2 + 0.3:
            return "boss " + h
    px0, px1, py0, py1, _ = G.POCKET
    if px0 < x < px1 and py0 < y < py1:
        return "rib"
    return "wall"


def poly_to_regions(polys, regions, G):
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
                d = 0.0
                q = pp[r.contains(pp)][0] if r.contains(pp).any() else r.pts[mpath.contains_points(r.pts)][0]
            else:
                dd, ii = r.tree.query(pp)
                k = int(np.argmin(dd))
                d, q = float(dd[k]), r.pts[ii[k]]
            if d < best[0]:
                best = (d, r.label, (float(q[0]), float(q[1])))
    kind = classify_point(G, *best[2]) if best[2] else None
    return best[0], best[1], best[2], kind


def electrical(ctx, geom, comps, rows):
    G, fr = ctx.G, ctx.frame
    L = G.L
    pads, mains = copper_sets(geom)
    contact = regions_from_faces(C.faces_at_z(fr, L["Z_PCB"], +1), "Z0")
    prow = []
    for name, polys in pads:
        d, lab, q, kind = poly_to_regions(polys, contact, G)
        prow.append({"pad": name, "dist": round(d, 3), "kind": kind, "at": [round(v, 2) for v in q] if q else None})
    prow.sort(key=lambda r: r["dist"])
    by_kind = {}
    for r in prow:
        by_kind.setdefault(r["kind"].split()[0] if r["kind"] else "?", r)
    mbest = (1e9, None, None, None)
    for name, polys in mains:
        d, lab, q, kind = poly_to_regions(polys, contact, G)
        if d < mbest[0]:
            mbest = (d, name, kind, q)
    # rib reach at the mains contact point: measured on the footprint section at Z_SHELF_BACK + 0.02
    sec = C.plane_section(fr, "z", L["Z_SHELF_BACK"] + 0.02)
    foot = regions_from_faces(sec.Faces(), "FP") if sec else []
    reach = G.PCB_RIM_W
    if foot and mbest[3]:
        rp = np.vstack([r.pts for r in foot])
        idx = cKDTree(rp).query_ball_point(mbest[3], 3.0)
        if idx:
            Pp = rp[idx]
            px0, px1, py0, py1 = G.PANEL
            e = np.minimum.reduce([Pp[:, 0] - px0, px1 - Pp[:, 0], Pp[:, 1] - py0, py1 - Pp[:, 1]])
            reach = float(min(max(e.max(), 0.0), G.SEAT_W))
    # creepage (v2 formula; back-stop case = panel resting on the Formex as in v2):
    #   copper -> contact + rib side (Z_PCB - Z_SHELF_BACK) + shelf back (SEAT_W - reach) + shelf inner face (shelf_t)
    #   + shelf/Formex interface (SEAT_W - FORMEX_INSET)
    tail = (L["Z_PCB"] - L["Z_SHELF_BACK"]) + (G.SEAT_W - reach) + G.SHELF_T + (G.SEAT_W - FORMEX_INSET)
    creep = mbest[0] + tail
    # clearance: any air path from the PCB back (Z 0) to the panel metal back (Z_PANEL_BACK nominal; worst case the
    # panel on the Formex, Z_FORMEX_FRONT) is at least that depth; v1/v2 formula round the shelf corner as well
    worst = (1e9, None)
    px0, px1, py0, py1 = G.PANEL
    for name, polys in mains:
        for poly in polys:
            for qx, qy in C.densify(poly, 0.05):
                e = min(qx - px0, px1 - qx, qy - py0, py1 - qy)
                if e < 0 or e > 15:
                    continue
                c = math.hypot(abs(e - G.SEAT_W), L["Z_PCB"] - L["Z_SEAT"]) + (G.SEAT_W - FORMEX_INSET)
                if c < worst[0]:
                    worst = (c, name)
    gov = None
    if prow:
        ref = prow[0]["pad"].split(".")[0]
        d3 = min((r["min_dist"] for r in comps if r["ref"] == ref), default=None)
        gov = {"pad": prow[0]["pad"], "component": ref, "min_dist_3d": d3}
    res = {"contact_faces": len(contact), "pad_min": prow[0] if prow else None, "closest_pads": prow[:10],
           "pad_min_by_kind": by_kind, "mains_to_contact": [round(mbest[0], 3), mbest[1], mbest[2],
                                                            [round(v, 2) for v in mbest[3]] if mbest[3] else None],
           "rib_reach_at_contact": round(reach, 3), "creepage_tail_mm": round(tail, 3), "creepage_mm": round(creep, 3),
           "clearance_v2_formula_mm": round(worst[0], 3), "clearance_item": worst[1],
           "clearance_depth_bound_nominal_mm": round(L["Z_PCB"] - L["Z_PANEL_BACK"], 3),
           "clearance_depth_bound_backstop_mm": round(L["Z_PCB"] - L["Z_FORMEX_FRONT"], 3), "governing_3d": gov}
    return res


# ----------------------------------------------------------------------------------------------- report
def run(ctx, log=C.log):
    t0 = time.time()
    G = ctx.G
    L = G.L
    rows = []      # (group, check, measured, required, verdict, note)
    res = {"frame": ctx.frame_info if hasattr(ctx, "frame_info") else None}
    _ = ctx.frame
    res["frame"] = ctx.frame_info
    log("[D] build the assembly from the params")
    A = build(G)
    HW = {v: hardware(G, v) for v in ("S4", "S8", "R4")}
    log("[D] gaps (STEP lip vs params glass / cut-out), thermal")
    res["gaps"] = gaps(ctx, rows)
    res["plan_params"] = plan_checks_params(ctx, rows)
    log("[D] assembly parts vs frame")
    idx = C.DistIndex(ctx.frame)
    res["assembly_vs_frame"] = av = assembly_vs_frame(ctx, idx, A, HW, rows)
    # verdict rows for the assembly
    def ok_touch(k, expect="touch"):
        r = av[k]
        return r["overlap_mm3"] < 1e-3
    rows.append(("assembly", "glass vs frame (overlap / min gap)", "%.4f mm3 / %.3f" % (av["glass"]["overlap_mm3"], av["glass"]["min_dist"]),
                 "0 / ~0.33 (recess wall at the glass back)", "PASS" if av["glass"]["overlap_mm3"] < 1e-3 else "FAIL",
                 "glass modelled without arris"))
    # the 8 pips stand inside the bead line by design: the bead / frame common volume must be exactly the pips'
    pip_v = 8 * math.pi * G.pip_h / 3 * ((G.pip_d / 2) ** 2 + (G.pip_d / 2) * (G.pip_d / 2 - G.pip_h * math.tan(math.radians(1)))
                                         + (G.pip_d / 2 - G.pip_h * math.tan(math.radians(1))) ** 2)
    rows.append(("assembly", "bead vs frame: common volume = the 8 pips (by design), bead on the land",
                 "%.3f mm3 (pips %.3f) / gap %.3f" % (av["bead"]["overlap_mm3"], pip_v, av["bead"]["min_dist"]),
                 "pips only / 0 (contact)", "PASS" if abs(av["bead"]["overlap_mm3"] - pip_v) < 0.05 and av["bead"]["min_dist"] < 1e-3 else "FAIL",
                 "bead 4.0 x 1.0 at 0.9..4.9 inside the glass edge; pips dia 1.5 x 0.5 on its centre line"))
    # bead inner edge -> pocket face (A1: >= 1.0), measured on the STEP land at Z_LAND + 0.01 on the four edges
    Pp = C.Probe(ctx.frame)
    bd = {}
    for edge, along in (("top", 80.0), ("bottom (beam)", 80.0), ("left", 60.0), ("right", 60.0)):
        e = edge.split()[0]
        iv = Pp.s_boundaries(e, along, L["Z_LAND"] + 0.01, -15, 1, G)
        s_pf = min(a for a, b in iv) if iv else None
        bd[edge] = None if s_pf is None else round(-(G.bead_edge + G.bead_w) - s_pf, 3)
    res["bead_to_pocket"] = bd
    rows.append(("assembly", "bead inner edge -> pocket face at the land (top / bottom beam / left / right)",
                 " / ".join("%.3f" % bd[k] for k in bd), ">= 1.0 (A1); params 3.13 / 1.40 / 1.21 / 3.97",
                 "PASS" if min(bd.values()) >= 1.0 else "FAIL",
                 "the pocket face is drafted 1 deg open to the front, so at the land it is ~0.10 closer than the params' rectangle"))
    rows.append(("assembly", "panel envelope vs frame", "%.4f mm3 / %.3f" % (av["panel_env"]["overlap_mm3"], av["panel_env"]["min_dist"]),
                 ">= 0.8 (pocket_clr)", "PASS" if av["panel_env"]["min_dist"] >= G.pocket_clr - 0.005 else "FAIL",
                 "LCM 164.9 x 100 outline, Z_CTP_FRONT..Z_PANEL_BACK"))
    rows.append(("assembly", "LOCA vs frame", "%.4f mm3 / %.3f" % (av["loca"]["overlap_mm3"], av["loca"]["min_dist"]), "> 0",
                 "PASS" if av["loca"]["min_dist"] > 0 else "FAIL", ""))
    rows.append(("assembly", "Formex vs frame (bonded to the shelf front)", "%.4f mm3 / %.3f" % (av["formex"]["overlap_mm3"], av["formex"]["min_dist"]),
                 "0 / 0", "PASS" if av["formex"]["overlap_mm3"] < 1e-3 and av["formex"]["min_dist"] < 1e-3 else "FAIL", ""))
    rows.append(("assembly", "panel back -> Formex front (back-stop gap)", "%.2f" % (L["Z_FORMEX_FRONT"] - L["Z_PANEL_BACK"]),
                 "%.2f (g_bs); WC %s" % (G.g_bs, G.raw["checks"]["backstop_gap_wc"]["3.0"]), "PASS", "from the levels"))
    tp = [av[k] for k in ("tape_top", "tape_bottom", "tape_left", "tape_right")]
    rows.append(("assembly", "VHB strips vs frame (on the flange front)", "overlap %.4f mm3, min %.3f" % (
        sum(t["overlap_mm3"] for t in tp), min(t["min_dist"] for t in tp)), "0 / 0", "PASS" if sum(t["overlap_mm3"] for t in tp) < 1e-3 else "FAIL",
        "strips run over the F5-F8 slots by design"))
    rows.append(("assembly", "oven sheet vs frame (seat ring / pads at the sheet back, lip in the cut-out)",
                 "%.4f mm3 / %.3f" % (av["sheet"]["overlap_mm3"], av["sheet"]["min_dist"]), "0 / 0", "PASS"
                 if av["sheet"]["overlap_mm3"] < 1e-3 else "FAIL", ""))
    for variant in ("S4", "S8", "R4"):
        ks = [k for k in av if k.startswith(variant + " ")]
        bad = [k for k in ks if av[k]["overlap_mm3"] > 1e-3]
        rows.append(("hardware", "%s hardware vs frame (%d parts)" % (variant, len(ks)), "overlaps: %s" % (", ".join(
            "%s %.3f" % (k[len(variant) + 1:], av[k]["overlap_mm3"]) for k in bad) or "none"), "none",
            "PASS" if not bad else "FAIL", "studs through the slots, washers / spacers / rivet parts touching their seats"))
    # tape strip ends vs pads and seat ring (from the params + STEP)
    cx, cy = G.GC
    gx0, gx1, gy0, gy1, _ = G.GLASS
    d_end = []
    for n in ("F1", "F2", "F3", "F4"):
        fx, fy = G.fxy(n)
        for k in ("tape_top", "tape_bottom", "tape_left", "tape_right"):
            s = A[k]
            d_end.append(C.dist(cq.Shape.cast(s.wrapped), C.cyl(fx, fy, L["Z_SHEET_BACK"], L["Z_FLANGE_FRONT"], 18.0)))
    rows.append(("assembly", "VHB strip ends -> corner pads (dia 18)", "%.3f" % min(d_end), ">= 1.0 (tape_margin)",
                 "PASS" if min(d_end) >= 1.0 - 0.005 else "FAIL", "pad dia 18 at its base; the pad face is 17.965 (draft)"))
    # S4: VHB strip area with no flange front under it at F5-F8 (slot / counterbore opening), 14 x 12 window round each
    fronts = C.faces_at_z(ctx.frame, L["Z_FLANGE_FRONT"], -1, tol=0.005)
    t_open = {}
    for n in ("F5", "F6", "F7", "F8"):
        x, y = G.fxy(n)
        for k in ("tape_top", "tape_bottom", "tape_left", "tape_right"):
            bb = A[k].val().BoundingBox() if hasattr(A[k], "val") else A[k].BoundingBox()
            if bb.xmin - 1 <= x <= bb.xmax + 1 and bb.ymin - 1 <= -y <= bb.ymax + 1:
                wx0, wx1 = max(bb.xmin, x - 7.0), min(bb.xmax, x + 7.0)
                wy0, wy1 = max(-bb.ymax, y - 7.0), min(-bb.ymin, y + 7.0)
                box = C.prism(wx0, wx1, wy0, wy1, L["Z_FLANGE_FRONT"] - 0.5, L["Z_FLANGE_FRONT"] + 0.5)
                on = sum(ff.Area() for f in fronts for ff in C.common_shape(f, box).Faces())
                t_open[n] = (wx1 - wx0) * (wy1 - wy0) - on
    if t_open:
        tot_tape = 2 * 183.48 * 12.0 + 2 * 145.83 * 12.0
        rows.append(("assembly", "S4: VHB strip area over the F5-F8 slot / counterbore openings (no flange front under it)",
                     "%.2f mm2 each, %.1f of %.0f mm2 tape (%.1f %%)" % (max(t_open.values()), sum(t_open.values()), tot_tape,
                                                                       100 * sum(t_open.values()) / tot_tape),
                     "INFO (GF-1.0: slot only)", "INFO", "the 7.4 x 9.0 stadium at its opening (1 deg draft) under each strip"))
    log("[D] board: 3D distances")
    comps = components(ctx, idx, A, rows)
    res["fit3d"] = comps
    res["tails_unmoved"] = tails_unmoved(ctx, idx)
    log("[D] tool access, washers, rivets")
    res["tool_access"] = tool_access(ctx, idx, rows)
    geom = C.board_geom()
    res["above_pcb"] = nothing_above_pcb(ctx, geom)
    log("[D] electrical (v2 method)")
    res["electrical"] = el = electrical(ctx, geom, comps["components_all"], rows)
    # pips vs the glass back (nominal stack) and washer bearing on the tube tops (washer annulus on the STEP face)
    ptops = C.faces_at_z(ctx.frame, L["Z_PIP_TOP"], -1, tol=0.005)
    pz = min(f.BoundingBox().zmin for f in ptops) if ptops else None
    rows.append(("assembly", "pip tops -> glass back (nominal; WC from the params)", "%.3f (%d pip tops)" % (
        pz - L["Z_GLASS_BACK"], len(ptops)) if pz is not None else "no pips", "> 0 (params WC %.2f)" % G.raw["pips"][-1]["value"]["3.0"],
        "PASS" if pz is not None and pz - L["Z_GLASS_BACK"] > 0 else "FAIL", "pips never touch the glass; the bead sets the bond line"))
    C.log("[D] stud / rivet / washer / shim seats")
    res["washer_shim"] = washer_shim_study(ctx, rows)
    if G.cb:
        res["stud_seat"] = stud_seat_study(ctx, rows)
    res["rivet_seat"] = rivet_study(ctx, rows)
    # rivet grip: measured stack on the STEP at F1 beside the slot
    P = C.Probe(ctx.frame)
    x, y = G.fxy("F1")
    u = G.slot_axis("F1")
    iv = P.z_intervals(x - 4.0 * u[1], y + 4.0 * u[0])
    stack = iv[0][1] - iv[0][0] if iv else None
    grip = G.t_sheet + (stack or 0) + WASHER_M5[2]
    res["rivet"] = {"frame_stack_mm": stack, "grip_mm": grip}
    # ---------------- rows for the board / electrical / tool
    c3 = comps
    rows.append(("board", "component models overlapping the frame (%d)" % c3["components_checked"], "%d" % len(c3["component_overlaps"]),
                 "0", "PASS" if not c3["component_overlaps"] else "FAIL", ""))
    cc = c3["closest_components"][0]
    rows.append(("board", "closest component model", "%s %.3f" % (cc["ref"], cc["min_dist"]), "> 0", "PASS" if cc["min_dist"] > 0 else "FAIL",
                 "next: " + ", ".join("%s %.2f" % (r["ref"], r["min_dist"]) for r in c3["closest_components"][1:6])))
    rows.append(("board", "PCB body", "%.3f / %.4f mm3" % (c3["pcb_body"]["min_dist"], c3["pcb_body"]["overlap_mm3"]),
                 "0.08 (copper + mask) / 0", "PASS" if abs(c3["pcb_body"]["min_dist"] - C.BOARD_DZ) < 0.005 and c3["pcb_body"]["overlap_mm3"] < 1e-4 else "FAIL", ""))
    pb = c3["panel_parts"]
    pmin = min(pb, key=lambda r: r["min_dist"])
    rows.append(("panel", "DS1 panel parts (moved %.2f with the panel) vs frame" % ctx.panel_dz, "min %.3f (%s at %s), overlap %.4f mm3" % (
        pmin["min_dist"], pmin["part"], pmin["at_abs"], sum(r["overlap_mm3"] for r in pb)), ">= 0.8 (pocket) / 0",
        "PASS" if pmin["min_dist"] >= 0.8 - 0.01 and sum(r["overlap_mm3"] for r in pb) < 1e-4 else "FAIL", ""))
    fmx = min(r["to_formex"] for r in pb if not r["part"].startswith(C.PANEL_TAIL_PARTS))
    rows.append(("panel", "DS1 panel parts vs Formex", "%.3f" % fmx, "0.8 (g_bs)", "PASS" if fmx >= 0.79 else "FAIL", ""))
    tl = c3["tails"]
    tmin = min(tl, key=lambda r: r["min_dist"])
    tu = res["tails_unmoved"]
    spl = [r for r in tu if "split_min_dist" in r]
    smin = min(spl, key=lambda r: r["split_min_dist"]) if spl else None
    if smin:
        rows.append(("tails", "FPC tails vs frame - split model (panel legs moved %.2f, connector legs at J10/J11 unmoved)" % ctx.panel_dz,
                     "%.3f (%s, %s, at %s)" % (smin["split_min_dist"], smin["part"], smin["split_where"], smin["split_at_abs"]),
                     ">= %.1f" % TAIL_MIN, "PASS" if smin["split_min_dist"] >= TAIL_MIN - 1e-3 else "FAIL",
                     "all: " + ", ".join("%s %.3f" % (r["part"], r["split_min_dist"]) for r in spl)))
    rows.append(("tails", "FPC tails rigidly moved with the panel (bound) vs frame", "%.3f (%s at %s)" % (tmin["min_dist"], tmin["part"], tmin["at_abs"]),
                 ">= %.1f" % TAIL_MIN, "INFO",
                 "upper bound of the move: near J10/J11 the tails stay with the PCB; all: " + ", ".join("%s %.3f" % (r["part"], r["min_dist"]) for r in tl)))
    if tu:
        tumin = min(tu, key=lambda r: r["unmoved_min_dist"])
        rows.append(("tails", "FPC tails at the v2 position (not moved, bound) vs frame", "%.3f (%s at %s)" % (
            tumin["unmoved_min_dist"], tumin["part"], tumin["unmoved_at_abs"]), ">= %.1f" % TAIL_MIN, "INFO",
            "lower bound of the move; v2 measured TFT 1.557 / CTP 1.554"))
    rows.append(("tails", "FPC tails vs glass / bead", "%.3f / %.3f" % (min(r["to_glass"] for r in tl), min(r["to_bead"] for r in tl)),
                 "> 0 (info: >= 1.5 asked to the frame only)", "PASS" if min(r["to_glass"] for r in tl) > 0 and min(r["to_bead"] for r in tl) > 0 else "FAIL", ""))
    lp = c3["lead_protrusions"][0] if c3["lead_protrusions"] else None
    if lp:
        rows.append(("electrical", "lead protrusion -> Formex back (closest)", "%s %.2f below Z 0 -> gap %.3f" % (lp["ref"], lp["protrusion"], lp["gap_to_formex"]),
                     "> 0", "PASS" if lp["gap_to_formex"] > 0 else "FAIL",
                     "next: " + ", ".join("%s %.2f" % (r["ref"], r["gap_to_formex"]) for r in c3["lead_protrusions"][1:6])))
    pm = el["pad_min"]
    rows.append(("electrical", "Z 0 contact faces vs B.Cu pads", "%.3f at %s (%s)" % (pm["dist"], pm["pad"], pm["kind"]),
                 ">= %.1f" % PAD_CLR, "PASS" if pm["dist"] >= PAD_CLR else "FAIL",
                 "by kind: " + ", ".join("%s %.2f %s" % (k, v["dist"], v["pad"]) for k, v in el["pad_min_by_kind"].items())))
    if el["governing_3d"] and el["governing_3d"]["min_dist_3d"] is not None:
        g3 = el["governing_3d"]
        rows.append(("electrical", "3D frame -> model of the nearest pad (%s)" % g3["pad"], "%.3f" % g3["min_dist_3d"], ">= 1.0",
                     "PASS" if g3["min_dist_3d"] >= 1.0 else "FAIL", "leads / solder fillets in the model"))
    rows.append(("electrical", "mains creepage -> panel metal via the frame (back-stop case, v2 formula)",
                 "%.2f (copper->contact %.2f at %s + path %.2f)" % (el["creepage_mm"], el["mains_to_contact"][0], el["mains_to_contact"][1], el["creepage_tail_mm"]),
                 ">= %.1f" % CREEPAGE_REQ, "PASS" if el["creepage_mm"] >= CREEPAGE_REQ else "FAIL",
                 "nominal: the panel hangs on the glass and touches no frame face -> no surface path at all"))
    rows.append(("electrical", "mains clearance -> panel metal", "%.2f (v2 formula, %s); any path >= %.2f nominal / %.2f back-stop" % (
        el["clearance_v2_formula_mm"], el["clearance_item"], el["clearance_depth_bound_nominal_mm"], el["clearance_depth_bound_backstop_mm"]),
        ">= %.1f" % CLEARANCE_REQ, "PASS" if min(el["clearance_v2_formula_mm"], el["clearance_depth_bound_backstop_mm"]) >= CLEARANCE_REQ else "FAIL",
        "the panel back lies 5.8 (nominal) / 5.0 (bond failed) below the PCB back"))
    ab = res["above_pcb"]
    rows.append(("electrical", "frame volume above Z 0 inside the board outline + 1", "%.4f mm3 (inside outline %.4f)" % (
        ab["volume_mm3"], ab["volume_inside_outline_mm3"]), "0", "PASS" if ab["ok"] else "FAIL",
        "plan gap of frame material above Z 0 to the board edge %.3f at %s" % (ab.get("plan_gap_above_z0_to_board_edge_mm", -1), ab.get("plan_gap_at_abs"))))
    ta = res["tool_access"]
    tw = min(ta, key=lambda r: r["board_min_dist"])
    rows.append(("tool", "dia-12 socket F1-F8, Z_TUBE_TOP-0.5 .. +45, vs every board body", "min >= %.2f at %s (%s)" % (
        tw["board_min_dist"], tw["hole"], tw["closest"]), "no overlap (warn < 1.0)",
        "PASS" if not any(r["board_overlaps"] for r in ta) else "FAIL", "; ".join("%s %.1f" % (r["hole"], r["board_min_dist"]) for r in ta)))
    tf = min(ta, key=lambda r: r["frame_min_dist"])
    rows.append(("tool", "dia-12 washer + socket F1-F8, tube top .. +45, vs frame", "min %.3f at %s, overlap %.4f" % (
        tf["frame_min_dist"], tf["hole"], sum(r["frame_overlap_mm3"] for r in ta)), "no overlap",
        "PASS" if sum(r["frame_overlap_mm3"] for r in ta) < 1e-3 else "FAIL", ""))
    rv = av
    blind = [k for k in rv if k.startswith("R4 rivet blind side")]
    rows.append(("rivet", "R4 blind side envelope (dia %.0f x %.0f beyond the M5 washer) vs frame" % RIVET_BLIND,
                 "min %.3f, overlap %.4f" % (min(rv[k]["min_dist"] for k in blind), sum(rv[k]["overlap_mm3"] for k in blind)),
                 "no overlap", "PASS" if sum(rv[k]["overlap_mm3"] for k in blind) < 1e-3 else "FAIL", "envelope ASSUMED (tri-fold / bulb)"))
    rows.append(("rivet", "R4 grip = sheet + frame stack at F1 (measured) + M5 washer", "%.2f (stack %.2f)" % (grip, stack or -1),
                 "8.2 (concept 11.4)", "PASS" if abs(grip - 8.2) < 0.01 else "FAIL", ""))
    res["rows"] = [{"group": g, "check": c, "measured": m, "required": r, "verdict": v, "note": n} for g, c, m, r, v, n in rows]
    res["counts"] = {v: sum(1 for r in res["rows"] if r["verdict"] == v) for v in ("PASS", "FAIL", "INFO")}
    res["seconds"] = round(time.time() - t0, 1)
    res["table"] = table(res["rows"])
    return res


def table(rows):
    L = ["%-11s %-78s %-60s %-36s %s" % ("group", "check", "measured", "required", "verdict"), "-" * 200]
    for r in rows:
        L.append("%-11s %-78s %-60s %-36s %s" % (r["group"], r["check"][:78], str(r["measured"])[:60], str(r["required"])[:36], r["verdict"]))
        if r["note"]:
            L.append("%-11s   note: %s" % ("", r["note"]))
    return "\n".join(L)


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    r = run(ctx)
    C.dump(r, ctx.out("fitcheck.json"))
    open(ctx.out("fitcheck.txt"), "w").write(r["table"] + "\n")
    print(r["table"])
