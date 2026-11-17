"""D. Fit of the frame STEP against an assembly built independently from the params (simple solids) and against the
real board (kicad-cli STEP with every model; DS1 panel moved with the panel to Z_PANEL_BACK).

  <venv>\\Scripts\\python.exe fit_check.py [--frame f.step] [--params p.json] [--board b.step]

Built here from the params only (glass_t as frozen): glass (rounded rectangle, no arris), LOCA, panel envelope,
Formex (panel - 0.5/side, R1, v2), bead ring (0.9..4.9 inside the glass edge, Z_GLASS_BACK..Z_LAND), 4 VHB strips
(tape_and_gasket.tape_s / strip_lengths, compressed to t_gap), oven sheet with the cut-out, S4: M4 x 16 CD weld studs on the
sheet back with the weld-flange + collar envelope dia 5.8 x 1.4 (GF-2.0 stud spec; the GF-1.1 run used the clean flange
5.7 x 1.4, also kept), DIN 9021 M4 washers + ISO 10511 M4 nylocs (AF 7, h 5.0); R4: dia 4.8 rivets with the large-flange
head dia 14 x 1.6 (R1.4 edge) on the sheet front, DIN 9021 M5 15 x 1.2 backing washer, blind-side envelope ASSUMED dia 12 x 10.
GF-2.0: S8 withdrawn (no F5-F8). The FPC tails are built here on the GF-2.0 route (tails_gf2.py, from the params polylines;
tolerance cases from my own route generator) - the DS1 model's own tail bodies carry the GF-1.1 route and are NOT used for
the tail clearances (they are reported separately).
Checks: gaps glass-lip (g2) and lip-sheet (g1) all round and at the corners, 20 / -20 / +70 C (+50 C sheet), CLTE frame
50 (design) / 70 (bound) ppm/K, glass 9, steel 12, about the glass centre; flush plane; bead and pips; panel vs clearance
pocket and Formex; print window vs AA and the CTP view area; FPC tails vs every frame feature / glass print / bond / bead /
Formex / panel / PCB and its parts (nominal and tolerance cases); connector entry (J10 / J11) model check; frame vs every
component model and the PCB; v2 electrical checks; tool access (dia-12 socket) at F1-F4; washer bearing; stud seats at the
centred, +-0.3 and slot-limit positions; rivet head support, backing washer, blind side and grip.
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
import tails_gf2 as TG

EXACT_BELOW = 5.0
TAIL_MIN = 1.5                             # GF-1.1 criterion tails -> frame (v1 LOOP_CLR); GF-2.0 bend-gap budget see tails rows
TAIL_BRIDGE_WC = 0.45                      # GF-2.0 concept / params g_bend budget: tail surface -> bridge pocket face, worst case
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
RIVET_D = 4.8
RIVET_HEAD = (14.0, 1.6, 1.4)              # GF-2.0 / GF-1.1 round 3: large-flange head dia 14, 1.6 high, R1.4 edge (params hardware.rivet)
RIVET_HEAD_GF11_RUN = 10.0                 # the dia-10 head of the GF-1.1 independent run (comparison only)
RIVET_BLIND = (12.0, 10.0)                 # ASSUMED blind-side envelope: dia 12, 10 mm beyond the backing washer
WELD_ENV = (5.8, 1.4)                      # GF-2.0 stud spec: flange + weld collar + flash within dia 5.8 x 1.4 (params hardware.stud)
WELD_FLANGE_GF11 = (5.7, 1.4)              # clean ISO 13918 PT flange, worst case (the GF-1.1 run)
STUD_POS_TOL = 0.3                         # stud axis +-0.3 to its nominal position (drawing_tolerances.sheet.stud_position_tol)
SLOT_DRAFT = 0.5                           # deg, slot walls (verified in A)
ALPHA = {"glass": 9e-6, "steel": 12e-6, "frame_design": 50e-6, "frame_bound": 70e-6}
T_ASM = 20.0
T1 = math.tan(math.radians(1.0))


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
    # VHB strips: s tape_s, compressed between the flange front and the sheet back; lengths from the params
    s0, s1 = G.tape_s
    lt, ls = G.strip_lengths["top_bottom"], G.strip_lengths["sides"]
    cx, cy = G.GC
    zt0, zt1 = L["Z_SHEET_BACK"], L["Z_FLANGE_FRONT"]
    P["tape_top"] = C.prism(cx - lt / 2, cx + lt / 2, gy0 - s1, gy0 - s0, zt0, zt1)
    P["tape_bottom"] = C.prism(cx - lt / 2, cx + lt / 2, gy1 + s0, gy1 + s1, zt0, zt1)
    P["tape_left"] = C.prism(gx0 - s1, gx0 - s0, cy - ls / 2, cy + ls / 2, zt0, zt1)
    P["tape_right"] = C.prism(gx1 + s0, gx1 + s1, cy - ls / 2, cy + ls / 2, zt0, zt1)
    # oven sheet patch with the cut-out (no stud holes for S4; R4 holes separately)
    fx0, fx1, fy0, fy1, _ = G.FLANGE
    cut = G.CUT
    sheet = C.prism(fx0 - 15, fx1 + 15, fy0 - 15, fy1 + 15, L["Z_GLASS_FRONT"], L["Z_SHEET_BACK"], r=5.0)
    sheet = sheet.cut(C.prism(cut[0], cut[1], cut[2], cut[3], L["Z_GLASS_FRONT"] - 1, L["Z_SHEET_BACK"] + 1, r=cut[4]))
    P["sheet"] = sheet
    return P


def rivet_head(x, y, z_top):
    """large-flange head dia 14 x 1.6 with an R1.4 edge, its flat underside at z_top (the sheet front), towards -Z"""
    d, h, r = RIVET_HEAD
    s = cq.Workplane("XY", origin=(0, 0, z_top - h)).center(x, -y).circle(d / 2).extrude(h)
    try:
        s = s.faces("<Z").edges().fillet(min(r, h - 0.01))
    except Exception:
        pass
    return s.val()


def hardware(G, variant):
    L = G.L
    out = {}
    for n in G.stud_names(variant):
        x, y = G.fxy(n)
        if variant in ("S4", "S8"):
            zs = L["Z_SHEET_BACK"]
            if G.cb:    # CD weld stud with its flange + collar envelope in the counterbore
                out["stud flange " + n] = C.cyl(x, y, zs, zs + WELD_ENV[1], WELD_ENV[0])
                out["stud " + n] = C.cyl(x, y, zs + WELD_ENV[1], zs + STUD_L, STUD_D)
            else:
                out["stud " + n] = C.cyl(x, y, zs, zs + STUD_L, STUD_D)
            out["washer " + n] = C.tube(x, y, L["Z_TUBE_TOP"], L["Z_TUBE_TOP"] + WASHER_M4[2], WASHER_M4[0], WASHER_M4[1])
            zn = L["Z_TUBE_TOP"] + WASHER_M4[2]
            out["nut " + n] = C.tube(x, y, zn, zn + NUT_H, NUT_AC, 4.0)
        else:   # R4 rivet
            out["rivet " + n] = C.cyl(x, y, L["Z_GLASS_FRONT"], L["Z_TUBE_TOP"] + WASHER_M5[2], RIVET_D)
            out["rivet head " + n] = rivet_head(x, y, L["Z_GLASS_FRONT"])
            out["backing washer " + n] = C.tube(x, y, L["Z_TUBE_TOP"], L["Z_TUBE_TOP"] + WASHER_M5[2], WASHER_M5[0], WASHER_M5[1])
            zb = L["Z_TUBE_TOP"] + WASHER_M5[2]
            out["rivet blind side " + n] = C.cyl(x, y, zb, zb + RIVET_BLIND[1], RIVET_BLIND[0])
    return out


# ----------------------------------------------------------------------------------------------- fastener seats
def _slot_hw_front(G, n):
    """slot half-width at its front end (the counterbore floor), from the verified 0.5 deg draft"""
    zfront = G.cb_floor_z(n) if G.cb else (G.L["Z_SHEET_BACK"] if n in ("F1", "F2", "F3", "F4") else G.L["Z_FLANGE_FRONT"])
    return G.slot_w / 2 + (zfront - G.L["Z_FLANGE_FRONT"]) * math.tan(math.radians(SLOT_DRAFT))


def _positions(G, n, body_r):
    """centre + extreme positions of a round body of radius body_r in the slot: (label, a along, b across)"""
    hw = _slot_hw_front(G, n)
    d = hw - body_r - 1e-4
    seg = (G.slot_l - G.slot_w) / 2
    return [("centred", 0.0, 0.0), ("across +", 0.0, d), ("across -", 0.0, -d), ("along + (slot end)", seg + d, 0.0),
            ("along - (slot end)", -seg - d, 0.0), ("end + across", seg, d), ("end - across", -seg, -d)], d


def _tol_positions(r=STUD_POS_TOL):
    """the stud axis at its tolerance limit (+-0.3) in 8 directions (a along the slot, b across)"""
    out = [("centred", 0.0, 0.0)]
    for k in range(8):
        a = math.radians(45 * k)
        lab = {0: "+0.3 along", 2: "+0.3 across", 4: "-0.3 along", 6: "-0.3 across"}.get(k, "0.3 diagonal %d deg" % (45 * k))
        out.append((lab, r * math.cos(a), r * math.sin(a)))
    return out


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
    """CD weld stud in the F1-F4 counterbores: the envelope (flange + collar + flash) dia 5.8 x 1.4 (GF-2.0 spec) and the clean
    flange dia 5.7 x 1.4 (GF-1.1 run) on the sheet back, shank dia 4: centred, at +-0.3 (8 directions, the position
    tolerance) and at the 7 slot-limit positions (shank against the slot wall / slot end, the GF-1.1 criterion); distances to
    the counterbore wall, floor round and floor, overlap with the frame"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    zs = L["Z_SHEET_BACK"]
    res = {}
    names = [n for n in ("F1", "F2", "F3", "F4") if n in G.fast]
    groups = {n: _cb_face_groups(fr, G, n) for n in names}
    for env_lab, env in (("dia %.1f x %.1f (GF-2.0 envelope)" % WELD_ENV, WELD_ENV), ("dia %.1f x %.1f (clean flange, GF-1.1 run)" % WELD_FLANGE_GF11, WELD_FLANGE_GF11)):
        for set_lab, posf in (("centred and +-%.1f" % STUD_POS_TOL, lambda n: (_tol_positions(), STUD_POS_TOL)),
                              ("slot limits (7 positions, GF-1.1 criterion)", lambda n: _positions(G, n, STUD_D / 2))):
            best = {"wall": (1e9, None), "floor round": (1e9, None), "floor": (1e9, None), "any": (1e9, None)}
            ov_max = 0.0
            per = []
            for n in names:
                walls, rounds, floor = groups[n]
                gcomp = {"wall": cq.Compound.makeCompound(walls) if walls else None,
                         "floor round": cq.Compound.makeCompound(rounds) if rounds else None,
                         "floor": cq.Compound.makeCompound(floor) if floor else None}
                pos, d = posf(n)
                for lab, a, b in pos:
                    px, py = _xy(G, n, a, b)
                    fl = C.cyl(px, py, zs, zs + env[1], env[0])
                    sh = C.cyl(px, py, zs + env[1], zs + STUD_L, STUD_D)
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
                    dsh = C.dist(fr, sh)
                    rec["shank_to_frame"] = round(dsh, 4)
                    if dsh < best["any"][0]:
                        best["any"] = (dsh, "%s %s" % (n, lab))
                    per.append(rec)
            key = "%s | %s" % (env_lab, set_lab)
            res[key] = {"min": {k: (round(v[0], 4), v[1]) for k, v in best.items()}, "max_overlap_mm3": ov_max, "positions": per}
            m = res[key]["min"]
            rows.append(("stud seat", "F1-F4 weld stud %s, %s: min to counterbore wall / floor round / floor; shank to frame" % (env_lab, set_lab),
                         "%.3f (%s) / %.3f (%s) / %.3f; shank %.3f" % (m["wall"][0], m["wall"][1], m["floor round"][0], m["floor round"][1],
                                                                    m["floor"][0], m["any"][0]),
                         "> 0 (no contact)", "PASS" if min(m["wall"][0], m["floor round"][0], m["floor"][0]) > 0 and ov_max < 1e-4 else "FAIL",
                         "overlap with the frame %.5f mm3" % ov_max))
    return res


def rivet_study(ctx, rows):
    """R4: dia 4.8 rivet in the F1-F4 slots (centred, +-0.3, slot limits): body vs frame, head dia 14 support on the pad face
    round the counterbore (the sheet is clamped between head and pad), head edge vs the cut-out, and the DIN 9021 M5 backing
    washer (15 / 5.3) on the cored tube top"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    out = []
    pads = C.faces_at_z(fr, L["Z_SHEET_BACK"], -1, tol=0.005)
    tops = C.faces_at_z(fr, L["Z_TUBE_TOP"], +1, tol=0.005)
    cut_pts = C.densify(C.rrect_wire_pts(*G.CUT, n=60), 0.05)
    for n in [k for k in ("F1", "F2", "F3", "F4") if k in G.fast]:
        x, y = G.fxy(n)
        pad = [f for f in pads if math.hypot(f.Center().x - x, -f.Center().y - y) < 3]
        top = sorted([f for f in tops if math.hypot(f.Center().x - x, -f.Center().y - y) < 3],
                     key=lambda f: max(f.BoundingBox().xlen, f.BoundingBox().ylen))
        slot_pos, d = _positions(G, n, RIVET_D / 2)
        for lab, a, b in _tol_positions() + [p for p in slot_pos if p[0] != "centred"]:
            px, py = _xy(G, n, a, b)
            body = C.cyl(px, py, L["Z_GLASS_FRONT"], L["Z_TUBE_TOP"] + WASHER_M5[2], RIVET_D)
            ov = C.common_vol(fr, body)
            sup = {}
            for hd in (RIVET_HEAD[0], RIVET_HEAD_GF11_RUN):
                head = C.cyl(px, py, L["Z_SHEET_BACK"] - 0.5, L["Z_SHEET_BACK"] + 0.5, hd)
                sup[hd] = sum(ff.Area() for f in pad for ff in C.common_shape(f, head).Faces())
            ann = C.tube(px, py, L["Z_TUBE_TOP"] - 0.5, L["Z_TUBE_TOP"] + 0.5, WASHER_M5[0], WASHER_M5[1])
            a_faces = [sum(ff.Area() for ff in C.common_shape(f, ann).Faces()) for f in top]
            edge = float(np.min(np.hypot(cut_pts[:, 0] - px, cut_pts[:, 1] - py))) - RIVET_HEAD[0] / 2
            out.append({"stud": n, "position": lab, "set": "slot limit" if (lab, a, b) in slot_pos else "tolerance",
                        "overlap_mm3": round(ov, 5), "head14_support_mm2": round(sup[RIVET_HEAD[0]], 2),
                        "head10_support_mm2": round(sup[RIVET_HEAD_GF11_RUN], 2), "head14_edge_to_cutout": round(edge, 3),
                        "m5_washer_on_seat_mm2": round(a_faces[0], 2) if a_faces else None,
                        "m5_washer_on_outer_skin_mm2": round(a_faces[1], 2) if len(a_faces) > 1 else None})
    tol = [r for r in out if r["set"] == "tolerance"]
    rows.append(("rivet", "R4 rivet dia 4.8 in the F1-F4 slots (centred, +-0.3, slot limits): overlap with the frame",
                 "%.5f mm3 max" % max(r["overlap_mm3"] for r in out), "0", "PASS" if max(r["overlap_mm3"] for r in out) < 1e-4 else "FAIL",
                 "slot-limit offset up to %.3f from the slot centre line" % _positions(G, "F1", RIVET_D / 2)[1]))
    cent = [r for r in out if r["position"] == "centred"]
    smin = min(tol, key=lambda r: r["head14_support_mm2"])
    rows.append(("rivet", "R4 head dia 14: pad face under it, centred / worst within +-0.3 (sheet clamped against the pad)",
                 "%.1f / %.1f mm2 (%s %s); dia-10 head (GF-1.1 run) %.1f" % (min(r["head14_support_mm2"] for r in cent), smin["head14_support_mm2"],
                                                                            smin["stud"], smin["position"], min(r["head10_support_mm2"] for r in cent)),
                 "params R4: 99.1", "PASS" if abs(min(r["head14_support_mm2"] for r in cent) - 99.1) < 0.5 else "FAIL",
                 "inside the 7.4 x 9.0 counterbore the 1.0 sheet is unsupported under the head"))
    rows.append(("rivet", "R4 head dia 14: edge -> sheet cut-out (centred / min within +-0.3)",
                 "%.3f / %.3f" % (min(r["head14_edge_to_cutout"] for r in cent), min(r["head14_edge_to_cutout"] for r in tol)),
                 "params 9.14 (> 0: head off the cut-out)", "PASS" if min(r["head14_edge_to_cutout"] for r in tol) > 0 else "FAIL", ""))
    if G.cb:
        sk = [r["m5_washer_on_outer_skin_mm2"] or 0 for r in out]
        se = [r["m5_washer_on_seat_mm2"] or 0 for r in out]
        rows.append(("rivet", "DIN 9021 M5 backing washer (15/5.3) on the cored tube top: seat area / on the outer skin (bridging)",
                     "seat %.1f..%.1f mm2, outer skin %.1f..%.1f mm2 (centred seat %.1f)" % (min(se), max(se), min(sk), max(sk), cent[0]["m5_washer_on_seat_mm2"] or 0),
                     "params 88.34 centred", "INFO",
                     "washer OD r 7.5 = groove outer radius at the top: centred it only reaches the groove edge (no bridge)"))
    return out


def washer_study(ctx, rows):
    """DIN 9021 M4 washer on the cored tube top: centred, +-0.3, slot limits and a realistic 0.6 along the slot"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    tops = C.faces_at_z(fr, L["Z_TUBE_TOP"], +1, tol=0.005)
    wrows = []
    for n in G.stud_names("S4"):
        x, y = G.fxy(n)
        top = [f for f in tops if math.hypot(f.Center().x - x, -f.Center().y - y) < 3]
        slot_pos, d = _positions(G, n, STUD_D / 2)
        for lab, a, b in _tol_positions() + [p for p in slot_pos if p[0] != "centred"] + [("along 0.6 (realistic)", 0.6, 0.0)]:
            px, py = _xy(G, n, a, b)
            ann = C.tube(px, py, L["Z_TUBE_TOP"] - 0.5, L["Z_TUBE_TOP"] + 0.5, WASHER_M4[0], WASHER_M4[1])
            wrows.append({"stud": n, "position": lab, "set": "slot limit" if (lab, a, b) in slot_pos else
                          ("realistic" if lab.startswith("along 0.6") else "tolerance"),
                          "area_mm2": round(sum(ff.Area() for f in top for ff in C.common_shape(f, ann).Faces()), 2)})
    wmin = min(wrows, key=lambda r: r["area_mm2"])
    wcen = min(r["area_mm2"] for r in wrows if r["position"] == "centred")
    wtol = min(r["area_mm2"] for r in wrows if r["set"] == "tolerance")
    w06 = min(r["area_mm2"] for r in wrows if r["position"].startswith("along 0.6"))
    rows.append(("hardware", "DIN 9021 M4 washer (12/4.3) on the cored tube tops: centred / worst stud position (slot limit)",
                 "%.1f / %.1f mm2 (%s %s) -> %.1f / %.1f MPa at 500 N" % (wcen, wmin["area_mm2"], wmin["stud"], wmin["position"],
                                                                           500 / wcen, 500 / wmin["area_mm2"]),
                 ">= 80 (params, centred); creep limit 15 MPa", "PASS" if wcen >= 80 - 0.5 and 500 / wmin["area_mm2"] < 15 else "FAIL",
                 "within +-0.3: %.1f mm2 (params washer_M4_min_tol0.3 80.0); at 0.6 along the slot %.1f mm2 (%.1f MPa)" % (wtol, w06, 500 / w06)))
    return {"washer": wrows}


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


def lip_face(G, loops):
    """the face of a plan section that is the lip ring: its outer loop is about as wide as lip_out"""
    w = G.LIP_OUT[1] - G.LIP_OUT[0]
    for l in loops:
        if l["outer"] and abs(np.ptp(l["pts"][:, 0]) - w) < 3.0:
            return l["face"]
    return None


def gaps(ctx, rows):
    G, fr = ctx.G, ctx.frame
    L = G.L
    res = {}
    heights = {"front (Z_GLASS_FRONT + 0.32, below the R0.3 rounds)": L["Z_GLASS_FRONT"] + 0.32,
               "mid-lip": (L["Z_GLASS_FRONT"] + L["Z_SHEET_BACK"]) / 2,
               "root (Z_SHEET_BACK - 0.21, above the R0.2 root)": L["Z_SHEET_BACK"] - 0.21}
    glass_pts = rrect_pts(G.GLASS)
    cut_pts = rrect_pts(G.CUT)
    is_corner_g = np.array([not ((G.GLASS[0] + G.GLASS[4] <= x <= G.GLASS[1] - G.GLASS[4]) or
                                 (G.GLASS[2] + G.GLASS[4] <= y <= G.GLASS[3] - G.GLASS[4])) for x, y in glass_pts])
    is_corner_c = np.array([not ((G.CUT[0] + G.CUT[4] <= x <= G.CUT[1] - G.CUT[4]) or
                                 (G.CUT[2] + G.CUT[4] <= y <= G.CUT[3] - G.CUT[4])) for x, y in cut_pts])
    meas, meas_loops = {}, {}
    for hn, z in heights.items():
        loops = C.plan_loops(fr, z)
        lf = lip_face(G, loops)
        inner = [l["pts"] for l in loops if l["face"] == lf and not l["outer"]]
        outer = [l["pts"] for l in loops if l["face"] == lf and l["outer"]]
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
    ti_lip = cKDTree(C.densify(meas_loops[hf][0], 0.02))
    to_lip = cKDTree(C.densify(meas_loops[hf][1], 0.02))
    gx0, gx1, gy0, gy1, gR = G.GLASS
    cx0, cx1, cy0, cy1, cR = G.CUT
    g_cases = {"nominal": ((gx0, gx1, gy0, gy1, gR), 0.0),
               "glass +0.1/side, R nominal (requested +-0.1, R +0.2/-0)": ((gx0 - 0.1, gx1 + 0.1, gy0 - 0.1, gy1 + 0.1, gR), 0.0),
               "glass profile +0.2 (offset outline)": ((gx0 - 0.2, gx1 + 0.2, gy0 - 0.2, gy1 + 0.2, gR + 0.2), 0.0),
               "glass +0.2/side and R -0.2 (size + radius tolerances)": ((gx0 - 0.2, gx1 + 0.2, gy0 - 0.2, gy1 + 0.2, gR - 0.2), 0.0),
               "glass nominal size, R -0.2": ((gx0, gx1, gy0, gy1, gR - 0.2), 0.0),
               "glass +0.2/side, R nominal (R +0.2/-0 callout)": ((gx0 - 0.2, gx1 + 0.2, gy0 - 0.2, gy1 + 0.2, gR), 0.0)}
    c_cases = {"nominal": ((cx0, cx1, cy0, cy1, cR), 0.0),
               "cut-out profile -0.1, lip +0.04": ((cx0 + 0.1, cx1 - 0.1, cy0 + 0.1, cy1 - 0.1, cR - 0.1), 0.04),
               "cut-out -0.1/side and R +0.1, lip +0.04": ((cx0 + 0.1, cx1 - 0.1, cy0 + 0.1, cy1 - 0.1, cR + 0.1), 0.04),
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
    for tag, cases, tree in (("g2", g_cases, ti_lip), ("g1", c_cases, to_lip)):
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
            # worst over the GF-1.1 case set (comparable rows); the new +0.1 glass case is reported in the note
            comp = {k: v for k, v in cs_.items() if not k.startswith("glass +0.1")}
            worst = min(comp.items(), key=lambda kv: min(kv[1]["sides_min"], kv[1]["corners_min"]))
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
    gx0, gx1, gy0, gy1 = G.GLASS[:4]
    brd = [pw[0] - gx0, gx1 - pw[1], pw[2] - gy0, gy1 - pw[3]]
    if G.border is not None:
        rows.append(("print", "border window edge -> glass edge (l/r/t/b), equal on all four sides", " / ".join("%.2f" % v for v in brd),
                     "%.2f (params border)" % G.border, "PASS" if all(abs(v - G.border) < 0.005 for v in brd) else "FAIL",
                     "glass %.2f x %.2f" % (gx1 - gx0, gy1 - gy0)))
        gc = ((gx0 + gx1) / 2, (gy0 + gy1) / 2)
        wc = ((pw[0] + pw[1]) / 2, (pw[2] + pw[3]) / 2)
        rows.append(("print", "glass centre = window centre = params glass_centre", "(%.3f, %.3f) / (%.3f, %.3f)" % (gc + wc),
                     "(%.2f, %.2f)" % G.GC, "PASS" if max(abs(gc[0] - G.GC[0]), abs(gc[1] - G.GC[1]), abs(wc[0] - G.GC[0]), abs(wc[1] - G.GC[1])) < 0.006 else "FAIL", ""))
    out["print_inset_aa"], out["print_inset_va"], out["borders"] = ins, insv, brd
    rows.append(("flush", "glass front / lip top / sheet front", "%.2f / %.2f / %.2f" % (
        L["Z_GLASS_FRONT"], C.optimal_bbox(ctx.frame)[4], L["Z_SHEET_BACK"] - G.t_sheet), "one plane", "PASS"
        if abs(C.optimal_bbox(ctx.frame)[4] - L["Z_GLASS_FRONT"]) < 0.005 else "FAIL",
        "sheet seated on the seat ring at Z_SHEET_BACK; glass set on the lip plane by the jig"))
    return out


# ----------------------------------------------------------------------------------------------- 3D
def components(ctx, idx, A, rows, log=C.log):
    fr = ctx.frame
    G = ctx.G
    comp_rows, panel_rows, lead_rows, old_tails = [], [], [], []
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
                old_tails.append(row)
            else:
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
    log("    components %d, panel parts %d, old DS1 tail bodies %d (not used for the GF-2.0 tail checks)" % (
        len(comp_rows), len(panel_rows), len(old_tails)))
    return {"components_checked": len(comp_rows), "component_overlaps": [r for r in comp_rows if r["overlap_mm3"] > 1e-4],
            "closest_components": comp_rows[:15],
            "components_all": [{"ref": r["ref"], "min_dist": r["min_dist"], "approx": r["approx"]} for r in comp_rows],
            "pcb_body": {"min_dist": round(pcb_d, 3), "overlap_mm3": round(pcb_ov, 4)},
            "panel_parts": panel_rows, "old_ds1_tail_bodies_GF11_route": old_tails, "lead_protrusions": lead_rows}


# ----------------------------------------------------------------------------------------------- GF-2.0 tails
def tails_study(ctx, A, rows, log=C.log):
    """tails built here on the GF-2.0 route: clearances to every frame feature class, glass print / glass / LOCA / bead /
    Formex / panel / sheet / tape, PCB body and every board model; nominal and the tolerance cases"""
    G, fr = ctx.G, ctx.frame
    L = G.L
    res = {"route_check": TG.compare_nominal(G)}
    groups = TG.classify_frame_faces(fr, G)
    # the land face (Z_LAND) is its own class (it sits under the 'other' rule otherwise)
    other = groups.pop("other", [])
    land = [f for f in other if C.is_plane_z(f, -1) and abs(f.BoundingBox().zmin - L["Z_LAND"]) < 0.005]
    groups[TG.K_LAND] = land
    rest = [f for f in other if f not in land]
    if rest:
        groups["other"] = rest
    res["frame_face_classes"] = {k: len(v) for k, v in groups.items()}
    board = [(r, p, s) for r, p, s in ctx.items if not (r == "DS1" and p.startswith(C.PANEL_TAIL_PARTS))]
    pcb = next(s for r, p, s in board if r == "PCB")
    panel = [s for r, p, s in board if r == "DS1"]
    asm = {"glass (printed back face = glass print)": [A["glass"]], "optical bond (LOCA)": [A["loca"]], "bead": [A["bead"]],
           "Formex": [A["formex"]], "oven sheet": [A["sheet"]], "VHB strips": [A[k] for k in ("tape_top", "tape_bottom", "tape_left", "tape_right")],
           "panel envelope (params)": [A["panel_env"]]}
    cases = TG.variant_routes(G)
    res["cases"] = {}
    for cname, routes in cases.items():
        nominal = cname.startswith("nominal")
        out = {}
        for n in ("TFT", "CTP"):
            P, tt = routes[n]
            sol = TG.tail_solids(G, n, P, t=tt)
            shapes = [s for _, s, _ in sol]
            t0 = time.time()
            r = {"volume_mm3": round(sum(s.Volume() for s in shapes), 2), "tail_t": tt,
                 "overlap_frame_mm3": round(sum(C.common_vol(fr, s) for s in shapes), 5), "frame_by_class": {}}
            for k, fs in groups.items():
                if not fs:
                    continue
                d, p1, p2 = TG.dist_min(fs, shapes)
                r["frame_by_class"][k] = {"min": round(d, 4), "at_frame_abs": [round(p1[0], 2), round(-p1[1], 2), round(p1[2], 2)] if p1 else None}
            kmin = min(r["frame_by_class"], key=lambda k: r["frame_by_class"][k]["min"])
            r["frame_min"] = r["frame_by_class"][kmin]["min"]
            r["frame_min_class"] = kmin
            if nominal or "panel" in cname or "exit" in cname:
                # panel edge cases: the panel (DS1 parts, envelope) and its LOCA move with the tail exit (J1 alignment); glass,
                # bead, Formex, sheet and frame stay
                import re as _re
                mdy = _re.search(r"panel edge ([+-][\d.]+)", cname)
                dyp = float(mdy.group(1)) if mdy else 0.0
                mv = (lambda s: s.translate(cq.Vector(0, -dyp, 0))) if dyp else (lambda s: s)
                asm_c = dict(asm)
                asm_c["optical bond (LOCA)"] = [mv(A["loca"])]
                asm_c["panel envelope (params)"] = [mv(A["panel_env"])]
                panel_c = [mv(s) for s in panel]
                for k, ss in asm_c.items():
                    d, p1, p2 = TG.dist_min(ss, shapes)
                    r.setdefault("assembly", {})[k] = {"min": round(d, 4), "at_abs": [round(p2[0], 2), round(-p2[1], 2), round(p2[2], 2)] if p2 else None}
                # panel parts: the tail leaves the panel edge face at v 0 (attached) -> clearance from the tail beyond the straight
                after = [s for _, s, _ in TG.tail_solids(G, n, P, t=tt, v_from=G.raw["tail_route"][n]["straight"])]
                d, p1, p2 = TG.dist_min(panel_c, after)
                r.setdefault("assembly", {})["panel (DS1 model) beyond the 0.5 straight"] = {
                    "min": round(d, 4), "at_abs": [round(p1[0], 2), round(-p1[1], 2), round(p1[2], 2)] if p1 else None}
                after2 = [s for _, s, _ in TG.tail_solids(G, n, P, t=tt, v_from=3.0)]
                d, p1, p2 = TG.dist_min(panel_c, after2)
                r["assembly"]["panel (DS1 model) beyond v 3.0 (after the first bend)"] = {"min": round(d, 4)}
                d, p1, p2 = TG.dist_min([mv(A["panel_env"])], after)
                r["assembly"]["panel envelope beyond the 0.5 straight"] = {"min": round(d, 4)}
                d, p1, p2 = TG.dist_min([pcb], shapes)
                r["pcb_body"] = {"min": round(d, 4), "at_abs": [round(p1[0], 2), round(-p1[1], 2), round(p1[2], 2)] if p1 else None,
                                 "overlap_mm3": round(sum(C.common_vol(pcb, s) for s in shapes), 4)}
                bb = cq.Compound.makeCompound(shapes).BoundingBox()
                parts = []
                for ref, part, s in board:
                    if ref in ("PCB", "DS1"):
                        continue
                    sb = s.BoundingBox()
                    gap = math.sqrt(max(bb.xmin - sb.xmax, sb.xmin - bb.xmax, 0) ** 2 + max(bb.ymin - sb.ymax, sb.ymin - bb.ymax, 0) ** 2 +
                                    max(bb.zmin - sb.zmax, sb.zmin - bb.zmax, 0) ** 2)
                    if gap > 6.0:
                        continue
                    d, p1, p2 = TG.dist_min([s], shapes)
                    ov = sum(C.common_vol(s, t) for t in shapes) if d < 1e-6 else 0.0
                    parts.append({"ref": ref, "part": part, "min": round(d, 4), "overlap_mm3": round(ov, 4),
                                  "at_abs": [round(p1[0], 2), round(-p1[1], 2), round(p1[2], 2)] if p1 else None})
                parts.sort(key=lambda q: q["min"])
                r["board_parts"] = parts[:12]
            r["seconds"] = round(time.time() - t0, 1)
            out[n] = r
        res["cases"][cname] = out
        log("    tails %-42s TFT frame %.3f (%s) | CTP frame %.3f (%s)" % (cname, out["TFT"]["frame_min"], out["TFT"]["frame_min_class"][:24],
                                                                        out["CTP"]["frame_min"], out["CTP"]["frame_min_class"][:24]))
    # ---- rows
    nom = res["cases"]["nominal (params polylines)"]
    rc = res["route_check"]
    rows.append(("tails", "GF-2.0 route: my route generator vs the params polylines (max deviation TFT / CTP); length vs L",
                 "%.4f / %.4f; %.3f / %.3f vs %.2f / %.2f" % (max(rc["TFT"]["max_dev_params_to_mine"], rc["TFT"]["max_dev_mine_to_params"]),
                                                              max(rc["CTP"]["max_dev_params_to_mine"], rc["CTP"]["max_dev_mine_to_params"]),
                                                              rc["TFT"]["length_params_polyline"], rc["CTP"]["length_params_polyline"], rc["TFT"]["L"], rc["CTP"]["L"]),
                 "< 0.01 (same route)", "PASS" if max(rc["TFT"]["max_dev_params_to_mine"], rc["CTP"]["max_dev_params_to_mine"],
                                                     rc["TFT"]["max_dev_mine_to_params"], rc["CTP"]["max_dev_mine_to_params"]) < 0.01 else "FAIL",
                 "U-loop R %.2f / %.2f, loop bottom (outer) %.3f / %.3f (params %.3f / %.3f)" % (
                     rc["TFT"]["U_R_mine"], rc["CTP"]["U_R_mine"], rc["TFT"]["loop_bottom_outer_mine"], rc["CTP"]["loop_bottom_outer_mine"],
                     rc["TFT"]["loop_bottom_outer_params"], rc["CTP"]["loop_bottom_outer_params"])))
    rows.append(("tails", "GF-2.0 tails (built here) vs frame: overlap", "TFT %.5f / CTP %.5f mm3" % (nom["TFT"]["overlap_frame_mm3"], nom["CTP"]["overlap_frame_mm3"]),
                 "0", "PASS" if max(nom["TFT"]["overlap_frame_mm3"], nom["CTP"]["overlap_frame_mm3"]) < 1e-4 else "FAIL", ""))
    # GF-2.0 criteria (params tail_clearance_criteria, lead decision 2026-11-16): loop_clr 1.5 for the loops and the tail-pocket
    # walls / rib / bottom wall / flange plate (everything except the bend zone); bend zone (nose, pocket face, break): >= 0.45
    # with the panel at its RSS position and > 0 at the worst case (panel WC, exit Z at either limit, tail at its upper thickness)
    bc = TG.bend_zone_criterion(G)
    bz = [k for k in bc["features"]]
    loop_clr = float(((G.raw.get("tail_clearance_criteria") or {}).get("loop_clr") or {}).get("value_mm", TAIL_MIN))
    def bmin(case, n):
        fb_ = res["cases"][case][n]["frame_by_class"]
        k_ = min((k for k in fb_ if k in bz), key=lambda k: fb_[k]["min"])
        return fb_[k_]["min"], k_
    k_rss = next(c for c in res["cases"] if c.startswith("bend-zone RSS"))
    k_wc = [c for c in res["cases"] if c.startswith("bend-zone WC: ")]
    k_wcp = next(c for c in res["cases"] if c.startswith("bend-zone WC, panel position only"))
    k_alt = [c for c in res["cases"] if c.startswith("alternative print-to-edge")]
    res["bend_zone"] = {}
    for n in ("TFT", "CTP"):
        fb = nom[n]["frame_by_class"]
        rest = {k: v["min"] for k, v in fb.items() if k not in bz}
        kr = min(rest, key=rest.get)
        rows.append(("tails", "%s tail vs frame outside the bend zone (U-loop, pocket walls / bottom wall, rib, flange plate, land-plate back, "
                              "slot ends), nominal" % n, "%.3f (%s)" % (rest[kr], kr), ">= %.1f (loop_clr, params tail_clearance_criteria)" % loop_clr,
                     "PASS" if rest[kr] >= loop_clr - 1e-3 else "FAIL",
                     "; ".join("%s %.3f" % (k, v) for k, v in sorted(rest.items(), key=lambda kv: kv[1]))))
        b0, k0 = bmin("nominal (params polylines)", n)
        br, kr_ = bmin(k_rss, n)
        bw = min((bmin(c, n) for c in k_wc), key=lambda q: q[0])
        bwp = bmin(k_wcp, n)
        ba = min((bmin(c, n) for c in k_alt), key=lambda q: q[0])
        res["bend_zone"][n] = {"nominal": b0, "RSS": br, "WC": bw[0], "WC_panel_only": bwp[0], "WC_print_0.1": ba[0], "feature": k0,
                               "panel_position_RSS": bc["rss"], "panel_position_WC": bc["wc"]}
        rows.append(("tails", "%s tail vs the bend zone (nose / pocket face / break): nominal; panel at its RSS position (+%.3f)" % (n, bc["rss"]),
                     "%.3f (%s); %.3f" % (b0, k0, br), ">= %.2f at the RSS position (params tail_clearance_criteria.bend_zone)" % bc["min_at_RSS"],
                     "PASS" if br >= bc["min_at_RSS"] - 1e-4 else "FAIL",
                     "panel position contributors %s mm (RSS %.3f, WC %.2f)" % (
                         list((G.raw.get("tail_clearance_criteria") or {}).get("bend_zone", {}).get("panel_position_contributors_mm", {}).values()), bc["rss"], bc["wc"])))
        rows.append(("tails", "%s tail vs the bend zone at the worst case (panel +%.2f, exit Z +-%.1f, tail %.2f)" % (n, bc["wc"], bc["exit_Z_tol"], 0.3 + bc["tail_t_tol"]),
                     "%.3f (%s)" % (bw[0], bw[1]), "> %.1f (no forced contact)" % bc["min_at_WC"], "PASS" if bw[0] > bc["min_at_WC"] else "FAIL",
                     "panel position only (WC +%.2f): %.3f; with print-to-edge +-0.1 (panel +%.2f, exit / tail worst): %.3f" % (
                         bc["wc"], bwp[0], bc["alt_print_tol_wc"], ba[0])))
        rows.append(("tails", "%s tail vs the bend zone at the full worst case: the concept's intent >= %.2f (GF-2.0 open finding 1)" % (n, TAIL_BRIDGE_WC),
                     "%.3f (%s)" % (bw[0], bw[1]), ">= %.2f (concept_gf2 2.1 budget clearance, held at the full worst case)" % TAIL_BRIDGE_WC,
                     "PASS" if bw[0] >= TAIL_BRIDGE_WC - 1e-4 else "FAIL",
                     "margin %+.3f; worst exit side %s; panel position only %.3f (margin %+.3f)" % (
                         bw[0] - TAIL_BRIDGE_WC, next((c for c in k_wc if abs(bmin(c, n)[0] - bw[0]) < 1e-9), "-").split("exit Z ")[-1],
                         bwp[0], bwp[0] - TAIL_BRIDGE_WC)))
    for n in ("TFT", "CTP"):
        wc = min(((c, res["cases"][c][n]["frame_min"], res["cases"][c][n]["frame_min_class"]) for c in res["cases"]), key=lambda t: t[1])
        rows.append(("tails", "%s tail vs frame, minimum over every route case (tolerances and the assumption cases l0 1.0, R_in 1.8, L +-0.5)" % n,
                     "%.3f (%s; %s)" % (wc[1], wc[0], wc[2]), "> 0 (no forced contact)", "PASS" if wc[1] > 0 else "FAIL",
                     "; ".join("%s %.3f" % (c[:30], res["cases"][c][n]["frame_min"]) for c in res["cases"])))
    for n in ("TFT", "CTP"):
        a = nom[n]["assembly"]
        rows.append(("tails", "%s tail vs glass print / glass / LOCA / bead / Formex / panel (beyond the 0.5 straight)" % n,
                     "%.3f / %.3f / %.3f / %.3f / %.3f / %.3f" % (a["glass (printed back face = glass print)"]["min"], a["glass (printed back face = glass print)"]["min"],
                                                                 a["optical bond (LOCA)"]["min"], a["bead"]["min"], a["Formex"]["min"],
                                                                 a["panel (DS1 model) beyond the 0.5 straight"]["min"]),
                     "> 0", "PASS" if min(v["min"] for k, v in a.items() if not k.startswith("panel")) > 0 else "FAIL",
                     "panel envelope (params) beyond the straight %.3f; oven sheet %.3f; VHB %.3f" % (
                         a["panel envelope beyond the 0.5 straight"]["min"], a["oven sheet"]["min"], a["VHB strips"]["min"])))
    for n in ("TFT", "CTP"):
        pb = nom[n]["pcb_body"]
        parts = nom[n]["board_parts"]
        ovp = [p for p in parts if p["overlap_mm3"] > 1e-4]
        rows.append(("tails", "%s tail vs PCB body (model, no copper / mask) / closest board model" % n,
                     "%.3f at %s / %s" % (pb["min"], pb["at_abs"], ", ".join("%s %.3f%s" % (p["ref"], p["min"], " (overlap %.3f mm3)" % p["overlap_mm3"] if p["overlap_mm3"] > 1e-4 else "")
                                                                             for p in parts[:4])),
                     "> 0 / no overlap", "PASS" if pb["min"] > 0 and not ovp else ("INFO" if ovp and all(p["ref"] in ("J10", "J11") for p in ovp) else "FAIL"),
                     "PCB model body top Z %.3f (copper + mask missing: physical top ~%.3f) -> physical clearance ~%.3f; overlaps with the connector "
                     "model at the tail end: see 'connector entry'" % (1.55, 1.635, pb["min"] - 0.085)))
    return res


def connector_entry(ctx, tails, rows, log=C.log):
    """J10 / J11: is the tail-end overlap with the connector model real or a model artefact? The connector model is cut in
    the y-Z plane at the tail's mid x: the free Z band of the model's entry opening (if any) vs the tail end (centre Z_return,
    thickness tail_t), how deep the opening goes, and the same overlap for the DS1 model's own finger bodies at their
    (unmoved) GF-1.1 / v2 position (the connector side of the GF-1.1 split model)."""
    G = ctx.G
    res = {}
    items0 = C.board_items(ctx.board_path, C.BOARD_DZ, 0.0)          # unmoved DS1 (GF-1.1 connector-side legs)
    conn = {r: s for r, p, s in ctx.items if r in ("J10", "J11")}
    for n, ref in (("TFT", "J10"), ("CTP", "J11")):
        T = G.raw["tail_route"][n]
        seg = T["outline_developed"][-1]
        xm = (seg[2] + seg[3]) / 2
        s = conn[ref]
        bb = s.BoundingBox()
        entry_y = -bb.ymin            # abs y of the entry face (largest abs y)
        sec = C.plane_section(s, "x", xm)
        band = []
        if sec is not None:
            loops = [l for f in sec.Faces() for l in C.face_loops_3d(f, 0.002)]
            paths = []
            for f in sec.Faces():
                ll = C.face_loops_3d(f, 0.002)
                paths.append([MPath(np.column_stack([-l[:, 1], l[:, 2]])) for l in ll])
            def inside(y, z):
                for ps in paths:
                    if ps[0].contains_point((y, z)) and not any(h.contains_point((y, z)) for h in ps[1:]):
                        return True
                return False
            for dy in (0.2, 0.6, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5):
                yq = entry_y - dy
                zs_ = np.arange(bb.zmin - 0.05, bb.zmax + 0.05, 0.01)
                m = np.array([inside(yq, z) for z in zs_])
                # free bands inside the connector's height (the model's FPC opening), and the one nearest the tail centre
                inner = (zs_ > bb.zmin + 0.02) & (zs_ < bb.zmax - 0.02)
                bands, st = [], None
                for z, v, ii in zip(zs_, m, inner):
                    if ii and not v and st is None:
                        st = z
                    if (v or not ii) and st is not None:
                        bands.append((round(st, 3), round(z, 3))); st = None
                near = min(bands, key=lambda b: abs((b[0] + b[1]) / 2 - T["Z_return"])) if bands else None
                band.append({"y": round(yq, 3), "depth": dy, "free_band_at_tail_Z": list(near) if near else None,
                             "all_free_bands": bands, "tail_Z_in_material": bool(m[int(np.argmin(np.abs(zs_ - T["Z_return"])))])})
        # overlaps: my tail (GF-2.0, last segment) and the DS1 fingers / tails at the unmoved position
        mine = [sh for lab, sh, sg in TG.tail_solids(G, n) if sg[0] >= 30.0]
        ov_mine = sum(C.common_vol(s, t) for t in mine)
        com = [C.common_shape(s, t) for t in mine]
        cb = [c.BoundingBox() for c in com if c.Solids()]
        ds1 = {p: sh for r, p, sh in items0 if r == "DS1" and p.startswith(C.PANEL_TAIL_PARTS)}
        old = {p: round(C.common_vol(s, sh), 4) for p, sh in ds1.items() if C.bb_gap(s, sh) < 0.01}
        res[ref] = {"tail": n, "x_section": xm, "connector_bbox_abs": [round(bb.xmin, 3), round(bb.xmax, 3), round(-bb.ymax, 3), round(-bb.ymin, 3),
                                                                       round(bb.zmin, 3), round(bb.zmax, 3)],
                    "entry_face_y": round(entry_y, 3), "tail_end_y": T["y_end"], "tail_Z_band": [T["Z_return"] - T["thickness"] / 2, T["Z_return"] + T["thickness"] / 2],
                    "opening_probe": band, "overlap_my_tail_mm3": round(ov_mine, 4),
                    "overlap_bbox_abs": [[round(b.xmin, 3), round(b.xmax, 3), round(-b.ymax, 3), round(-b.ymin, 3), round(b.zmin, 3), round(b.zmax, 3)] for b in cb],
                    "overlap_DS1_own_bodies_unmoved_GF11_mm3": old}
        log("    %s: my %s tail overlaps the model by %.4f mm3; DS1 own bodies (unmoved) %s" % (ref, n, ov_mine, old))
        tz = res[ref]["tail_Z_band"]
        fb = [b for b in band if b["free_band_at_tail_Z"]]
        rows.append(("connector entry", "%s (%s tail end): overlap of the tail with the connector model / DS1's own bodies at GF-1.1" % (ref, n),
                     "%.4f mm3 (bbox %s) / %s" % (ov_mine, res[ref]["overlap_bbox_abs"][:1], old),
                     "explained (inside the insertion opening) or 0", "INFO",
                     "model opening at the tail centre Z %.2f: %s; tail Z %.2f..%.2f, inserted to y %.3f from the entry face y %.3f" % (
                         T["Z_return"], "; ".join("dy %.1f: %s" % (b["depth"], b["free_band_at_tail_Z"] or "material") for b in band),
                         tz[0], tz[1], T["y_end"], entry_y)))
    return res


def assembly_vs_frame(ctx, idx, A, HW, rows):
    fr = ctx.frame
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


# ----------------------------------------------------------------------------------------------- tool / above PCB
def tool_access(ctx, idx, rows, log=C.log):
    G = ctx.G
    L = G.L
    res = []
    for n in G.stud_names("S4"):
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
    tail = (L["Z_PCB"] - L["Z_SHELF_BACK"]) + (G.SEAT_W - reach) + G.SHELF_T + (G.SEAT_W - FORMEX_INSET)
    creep = mbest[0] + tail
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
    _ = ctx.frame
    res = {"frame": ctx.frame_info}
    log("[D] build the assembly from the params")
    A = build(G)
    HW = {v: hardware(G, v) for v in G.variants}
    log("[D] gaps (STEP lip vs params glass / cut-out), thermal")
    res["gaps"] = gaps(ctx, rows)
    res["plan_params"] = plan_checks_params(ctx, rows)
    log("[D] assembly parts vs frame")
    idx = C.DistIndex(ctx.frame)
    res["assembly_vs_frame"] = av = assembly_vs_frame(ctx, idx, A, HW, rows)
    rows.append(("assembly", "glass vs frame (overlap / min gap)", "%.4f mm3 / %.3f" % (av["glass"]["overlap_mm3"], av["glass"]["min_dist"]),
                 "0 / ~0.33 (recess wall at the glass back)", "PASS" if av["glass"]["overlap_mm3"] < 1e-3 else "FAIL",
                 "glass modelled without arris"))
    pip_v = len(G.pips) * math.pi * G.pip_h / 3 * ((G.pip_d / 2) ** 2 + (G.pip_d / 2) * (G.pip_d / 2 - G.pip_h * math.tan(math.radians(1)))
                                                   + (G.pip_d / 2 - G.pip_h * math.tan(math.radians(1))) ** 2)
    rows.append(("assembly", "bead vs frame: common volume = the 8 pips (by design), bead on the land",
                 "%.3f mm3 (pips %.3f) / gap %.3f" % (av["bead"]["overlap_mm3"], pip_v, av["bead"]["min_dist"]),
                 "pips only / 0 (contact)", "PASS" if abs(av["bead"]["overlap_mm3"] - pip_v) < 0.05 and av["bead"]["min_dist"] < 1e-3 else "FAIL",
                 "bead 4.0 x 1.0 at 0.9..4.9 inside the glass edge; pips dia 1.5 x 0.5 on its centre line"))
    # bead inner edge -> pocket face (A1: >= 1.0), measured where the land ends (Z_LAND + 0.01), as GF-1.1
    Pp = C.Probe(ctx.frame)
    bd, bd_plane = {}, {}
    stations = (("top", 80.0), ("bottom over the bridge, CTP x 60", 60.0), ("bottom over the bridge, TFT x 130", 130.0),
                ("bottom outside the tail span x 24", 24.0), ("left", 60.0), ("right", 60.0)) if G.gf2 else \
               (("top", 80.0), ("bottom (beam)", 80.0), ("left", 60.0), ("right", 60.0))
    for edge, along in stations:
        e = edge.split()[0]
        iv = Pp.s_boundaries(e, along, L["Z_LAND"] + 0.01, -15, 1, G)
        s_pf = min(a for a, b in iv) if iv else None
        bd[edge] = None if s_pf is None else round(-(G.bead_edge + G.bead_w) - s_pf, 3)
    res["bead_to_pocket"] = bd
    lnd = {r["name"]: r for r in G.lands}
    lb_par = next((r["bead_to_pocket"] for r in G.lands if r["name"].startswith("bottom over the tail span")), None)
    rows.append(("assembly", "bead inner edge -> where the land ends at Z_LAND + 0.01 (%s)" % " / ".join(bd),
                 " / ".join("%.3f" % bd[k] for k in bd), ">= %.1f (A1, bead_pocket_min); params %s" % (
                     G.bead_pocket_min or 1.0, " / ".join("%.2f" % r["bead_to_pocket"] for r in G.lands)),
                 "PASS" if min(bd.values()) >= (G.bead_pocket_min or 1.0) else "FAIL",
                 "GF-1.1 method: the first frame face at Z_LAND + 0.01 inward of the bead. Over the bridge that is the %.1f x 45 land break "
                 "(the flat land ends %.1f before the pocket face; at Z_LAND + 0.01 the break reads 0.01 more than on the land plane, see "
                 "the land-plane row); params lands 'bottom over the tail span' bead_to_pocket %s is to the pocket-face plane" % (
                     G.land_break, G.land_break, lb_par)))
    if G.gf2:
        # the same margin to the pocket-face plane (break excluded), measured on the STEP
        ex = []
        for x in (60.0, 130.0):
            pts = []
            for z in np.linspace(L["Z_LAND"] + G.land_break + 0.04, L["Z_LANDPLATE_BACK"] - G.bend_nose_R - 0.03, 5):
                iv = Pp.y_intervals(x, float(z))
                a = next((a for a, b in iv if 120.5 < a < 125.0), None)
                if a is not None:
                    pts.append((float(z), a))
            Z_ = np.array([p[0] for p in pts]); Y_ = np.array([p[1] for p in pts])
            b_, a_ = np.polyfit(Z_, Y_, 1)
            ex.append((G.GLASS[3] - G.bead_edge - G.bead_w) - (a_ + b_ * L["Z_LAND"]))
        rows.append(("assembly", "bead inner edge -> bridge pocket face plane at Z_LAND (break excluded), x 60 / 130",
                     "%.3f / %.3f" % tuple(ex), ">= %.1f (A1)" % (G.bead_pocket_min or 1.0), "PASS" if min(ex) >= (G.bead_pocket_min or 1.0) else "FAIL",
                     "params lands 'bottom over the tail span' bead_to_pocket %s" % lb_par))
        res["bead_to_pocket_plane_bridge"] = ex
        # the A1 margin to the break edge ON the land plane: the 45 deg break face is probed 0.01 / 0.03 / 0.05 behind the land
        # and extrapolated to Z_LAND (exact for a plane); the break width / angle come out of the same fit
        lp = {}
        for x in (60.0, 130.0):
            pts = []
            for dz in (0.01, 0.03, 0.05, 0.10, 0.15):
                iv = Pp.y_intervals(x, L["Z_LAND"] + dz)
                a = next((a for a, b in iv if 120.5 < a < 125.0), None)
                if a is not None:
                    pts.append((dz, a))
            D_ = np.array([p[0] for p in pts]); Y_ = np.array([p[1] for p in pts])
            s_, y0_ = np.polyfit(D_, Y_, 1)
            lp[x] = {"break_edge_y_on_land_plane": round(float(y0_), 4), "break_slope_dy_per_dz": round(float(s_), 4),
                     "bead_to_break_edge_on_land_plane": round(float((G.GLASS[3] - G.bead_edge - G.bead_w) - y0_), 4),
                     "probe_points": [(round(d, 3), round(y, 4)) for d, y in pts]}
        res["bead_to_break_land_plane"] = lp
        m_lp = min(v["bead_to_break_edge_on_land_plane"] for v in lp.values())
        rows.append(("assembly", "bead inner edge -> land-break edge ON the land plane (break face probed behind the land, extrapolated "
                                 "to Z_LAND), x 60 / 130",
                     " / ".join("%.3f" % v["bead_to_break_edge_on_land_plane"] for v in lp.values()),
                     ">= %.1f (A1, bead_pocket_min, to the break edge)" % (G.bead_pocket_min or 1.0),
                     "PASS" if m_lp >= (G.bead_pocket_min or 1.0) - 1e-4 else "FAIL",
                     "margin %+.3f; break edge on the land plane y %s, break face slope dy/dz %s (45 deg = -1); bead inner edge y %.3f" % (
                         m_lp - (G.bead_pocket_min or 1.0), [v["break_edge_y_on_land_plane"] for v in lp.values()],
                         [v["break_slope_dy_per_dz"] for v in lp.values()], G.GLASS[3] - G.bead_edge - G.bead_w)))
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
        "GF-2.0: no F5-F8 slots under the strips"))
    rows.append(("assembly", "oven sheet vs frame (seat ring / pads at the sheet back, lip in the cut-out)",
                 "%.4f mm3 / %.3f" % (av["sheet"]["overlap_mm3"], av["sheet"]["min_dist"]), "0 / 0", "PASS"
                 if av["sheet"]["overlap_mm3"] < 1e-3 else "FAIL", ""))
    for variant in G.variants:
        ks = [k for k in av if k.startswith(variant + " ")]
        bad = [k for k in ks if av[k]["overlap_mm3"] > 1e-3]
        rows.append(("hardware", "%s hardware vs frame (%d parts)" % (variant, len(ks)), "overlaps: %s" % (", ".join(
            "%s %.3f" % (k[len(variant) + 1:], av[k]["overlap_mm3"]) for k in bad) or "none"), "none",
            "PASS" if not bad else "FAIL", "S4 with the weld-stud envelope dia %.1f x %.1f; R4 with the dia-14 head" % WELD_ENV))
    d_end = []
    for n in [k for k in ("F1", "F2", "F3", "F4") if k in G.fast]:
        fx, fy = G.fxy(n)
        for k in ("tape_top", "tape_bottom", "tape_left", "tape_right"):
            d_end.append(C.dist(cq.Shape.cast(A[k].wrapped), C.cyl(fx, fy, L["Z_SHEET_BACK"], L["Z_FLANGE_FRONT"], 18.0)))
    rows.append(("assembly", "VHB strip ends -> corner pads (dia 18)", "%.3f" % min(d_end), ">= 1.0 (tape_margin)",
                 "PASS" if min(d_end) >= 1.0 - 0.005 else "FAIL", "pad dia 18 at its base; the pad face is 17.965 (draft)"))
    # GF-2.0: VHB strip footprint fully on the flange-front face (no opening under the tape)
    fronts = C.faces_at_z(ctx.frame, L["Z_FLANGE_FRONT"], -1, tol=0.005)
    t_area, t_on = 0.0, 0.0
    for k in ("tape_top", "tape_bottom", "tape_left", "tape_right"):
        bb = A[k].BoundingBox()
        box = C.box(bb.xmin, bb.xmax, bb.ymin, bb.ymax, L["Z_FLANGE_FRONT"] - 0.5, L["Z_FLANGE_FRONT"] + 0.5)
        t_area += bb.xlen * bb.ylen
        t_on += sum(ff.Area() for f in fronts for ff in C.common_shape(f, box).Faces())
    t_par = 2 * (G.strip_lengths["top_bottom"] + G.strip_lengths["sides"]) * G.tape_w      # params strips x tape_w
    rows.append(("assembly", "VHB strips: area / area on the flange-front face (fully supported)", "%.1f / %.1f mm2" % (t_area, t_on),
                 "params strips %.1f; equal" % t_par, "PASS" if abs(t_area - t_on) < 0.5 and abs(t_area - t_par) < 1.0 else "FAIL",
                 "strips %.2f / %.2f long, s %.1f..%.1f" % (G.strip_lengths["top_bottom"], G.strip_lengths["sides"], G.tape_s[0], G.tape_s[1])))
    res["tape"] = {"area_mm2": round(t_area, 2), "on_flange_front_mm2": round(t_on, 2)}
    log("[D] board: 3D distances")
    comps = components(ctx, idx, A, rows)
    res["fit3d"] = comps
    if G.tail_route:
        log("[D] GF-2.0 tails (built here): nominal + tolerance cases")
        res["tails"] = tails_study(ctx, A, rows)
        res["connector_entry"] = connector_entry(ctx, res["tails"], rows)
    log("[D] tool access, washers, rivets")
    res["tool_access"] = tool_access(ctx, idx, rows)
    geom = C.board_geom()
    res["above_pcb"] = nothing_above_pcb(ctx, geom)
    log("[D] electrical (v2 method)")
    res["electrical"] = el = electrical(ctx, geom, comps["components_all"], rows)
    ptops = C.faces_at_z(ctx.frame, L["Z_PIP_TOP"], -1, tol=0.005)
    pz = min(f.BoundingBox().zmin for f in ptops) if ptops else None
    rows.append(("assembly", "pip tops -> glass back (nominal; WC from the params)", "%.3f (%d pip tops)" % (
        pz - L["Z_GLASS_BACK"], len(ptops)) if pz is not None else "no pips", "> 0 (params WC %.2f)" % G.raw["pips"][-1]["value"]["3.0"],
        "PASS" if pz is not None and pz - L["Z_GLASS_BACK"] > 0 else "FAIL", "pips never touch the glass; the bead sets the bond line"))
    C.log("[D] stud / rivet / washer seats")
    res["washer"] = washer_study(ctx, rows)
    if G.cb:
        res["stud_seat"] = stud_seat_study(ctx, rows)
    res["rivet_seat"] = rivet_study(ctx, rows)
    P = C.Probe(ctx.frame)
    x, y = G.fxy("F1")
    u = G.slot_axis("F1")
    iv = P.z_intervals(x - 4.0 * u[1], y + 4.0 * u[0])
    stack = iv[0][1] - iv[0][0] if iv else None
    grip = G.t_sheet + (stack or 0) + WASHER_M5[2]
    res["rivet"] = {"frame_stack_mm": stack, "grip_mm": grip}
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
    fmx = min(r["to_formex"] for r in pb)
    rows.append(("panel", "DS1 panel parts vs Formex", "%.3f" % fmx, "0.8 (g_bs)", "PASS" if fmx >= 0.79 else "FAIL", ""))
    ot = c3["old_ds1_tail_bodies_GF11_route"]
    if ot and G.tail_route:
        rows.append(("tails", "(reference) DS1 model's own tail bodies, GF-1.1 route, moved with the panel: vs the frame",
                     "min %.3f, overlap %.2f mm3" % (min(r["min_dist"] for r in ot), sum(r["overlap_mm3"] for r in ot)),
                     "not used (the route changed)", "INFO",
                     "; ".join("%s %.3f / %.2f mm3" % (r["part"], r["min_dist"], r["overlap_mm3"]) for r in ot)))
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
    rows.append(("tool", "dia-12 socket %s, Z_TUBE_TOP-0.5 .. +45, vs every board body" % "/".join(r["hole"] for r in ta), "min >= %.2f at %s (%s)" % (
        tw["board_min_dist"], tw["hole"], tw["closest"]), "no overlap (warn < 1.0)",
        "PASS" if not any(r["board_overlaps"] for r in ta) else "FAIL", "; ".join("%s %.1f" % (r["hole"], r["board_min_dist"]) for r in ta)))
    tf = min(ta, key=lambda r: r["frame_min_dist"])
    rows.append(("tool", "dia-12 washer + socket %s, tube top .. +45, vs frame" % "/".join(r["hole"] for r in ta), "min %.3f at %s, overlap %.4f" % (
        tf["frame_min_dist"], tf["hole"], sum(r["frame_overlap_mm3"] for r in ta)), "no overlap",
        "PASS" if sum(r["frame_overlap_mm3"] for r in ta) < 1e-3 else "FAIL", ""))
    blind = [k for k in av if k.startswith("R4 rivet blind side")]
    rows.append(("rivet", "R4 blind side envelope (dia %.0f x %.0f beyond the M5 washer) vs frame" % RIVET_BLIND,
                 "min %.3f, overlap %.4f" % (min(av[k]["min_dist"] for k in blind), sum(av[k]["overlap_mm3"] for k in blind)),
                 "no overlap", "PASS" if sum(av[k]["overlap_mm3"] for k in blind) < 1e-3 else "FAIL", "envelope ASSUMED (tri-fold / bulb)"))
    rows.append(("rivet", "R4 grip = sheet + frame stack at F1 (measured) + M5 washer", "%.2f (stack %.2f)" % (grip, stack or -1),
                 "8.2 (concept 11.4)", "PASS" if abs(grip - 8.2) < 0.01 else "FAIL", ""))
    res["rows"] = [{"group": g, "check": c, "measured": m, "required": r, "verdict": v, "note": n} for g, c, m, r, v, n in rows]
    res["counts"] = {v: sum(1 for r in res["rows"] if r["verdict"] == v) for v in ("PASS", "FAIL", "INFO")}
    res["seconds"] = round(time.time() - t0, 1)
    res["table"] = table(res["rows"])
    return res


def table(rows):
    L = ["%-15s %-78s %-60s %-36s %s" % ("group", "check", "measured", "required", "verdict"), "-" * 205]
    for r in rows:
        L.append("%-15s %-78s %-60s %-36s %s" % (r["group"], r["check"][:78], str(r["measured"])[:60], str(r["required"])[:36], r["verdict"]))
        if r["note"]:
            L.append("%-15s   note: %s" % ("", r["note"]))
    return "\n".join(L)


if __name__ == "__main__":
    ctx = C.Context(sys.argv[1:])
    r = run(ctx)
    C.dump(r, ctx.out("fitcheck.json"))
    open(ctx.out("fitcheck.txt"), "w", encoding="utf8").write(r["table"] + "\n")
    print(r["table"])
