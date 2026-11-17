"""Rev3.0 glass front, revision GF-2.0 concept (equal borders, tails bent back) - calculations.

Run from this folder (numpy + matplotlib; the CadQuery venv has both; -B = no byte-code written):
    <cqenv>\\Scripts\\python.exe -B concept_gf2_calc.py
Reads (read only):
    Mechanical/Rev3.0_GlassFront/Rev3.0_GlassFront_params.json   GF-1.1 master (never written by this script)
    concept_gf2_measured.json                                       models measured by concept_gf2_measure.py
    Design Reports/Rev3.0/tools/frame_v2/out/board_geom.json        board outline, courtyards (as concept_calc.py)
Writes (this folder only):
    concept_gf2_calc_out.txt     run log (everything printed)
    concept_gf2_params.json      proposed GF-2.0 values (changed + new) - a PROPOSAL, the CAD agent edits the master
    concept_gf2_section_bottom.png, concept_gf2_bend_zoom.png, concept_gf2_plan_bottom.png

concept_calc.py is NOT imported: importing it would re-run it and overwrite the GF-1.1 master with GF-1.0 values.
Its grillage, ring-section, impact and fastener-rule code is copied here (marked "port") and checked against its own
GF-1.1 output first (section 5.0), so the GF-2.0 numbers are comparable.

Coordinates as the master: X = KiCad abs x, y = KiCad abs y (down), Z = 0 at the PCB back, -Z to the front.
Tags in the output: [M] measured from a model in the repo, [C] calculated here, [A] assumed, [E] estimated in the
panel model (read off the drawing by scale), [G] GF-1.1 master value.
"""
import sys
sys.dont_write_bytecode = True
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
MASTER = os.path.join(ROOT, "Mechanical", "Rev3.0_GlassFront", "Rev3.0_GlassFront_params.json")
MEAS = os.path.join(HERE, "concept_gf2_measured.json")
BOARD = os.path.join(ROOT, "Design Reports", "Rev3.0", "tools", "frame_v2", "out", "board_geom.json")
OUT_TXT = os.path.join(HERE, "concept_gf2_calc_out.txt")
OUT_PAR = os.path.join(HERE, "concept_gf2_params.json")
_LOG = []


def out(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    _LOG.append(s)


def hdr(t):
    out("\n" + "=" * 110 + "\n" + t + "\n" + "=" * 110)


def r4(v):
    return round(float(v), 4) if isinstance(v, (float, np.floating)) else v


# =====================================================================================================================
# 1. INPUTS
# =====================================================================================================================
M = json.load(open(MASTER, encoding="utf8"))
DRV = {p["name"]: p["value"] for p in M["driving_parameters"]}
CO = {p["name"]: p["value"] for p in M["carried_over_from_v2"]}
RECT = {r["name"]: r for r in M["plan_rectangles"]}
LVALL = {float(k): v for k, v in M["derived_levels"]["evaluated_by_glass_t"].items()}
MEA = json.load(open(MEAS))
BRD = json.load(open(BOARD))
TG_LIST = [1.1, 2.0, 3.0, 4.0]
TG = float(DRV["glass_t"])
GLASS_TYPES = {float(k): v for k, v in next(p for p in M["driving_parameters"] if p["name"] == "glass_t")["types"].items()}

E_G, NU_G, RHO_G = 70000.0, 0.22, 2.5e-3          # [A] concept sec. 9
E_F, NU_F = 3500.0, 0.35                           # [A] PA6-GF30, concept sec. 9
ALPHA_G, ALPHA_S = 9e-6, 12e-6
ALPHA_F = {"flow 30": 30e-6, "design 50": 50e-6, "bound 70": 70e-6}
WALL = CO["wall"]
g2, lip_w, g1, seat_w = DRV["g2"], DRV["lip_w"], DRV["g1"], DRV["seat_ring_w"]
bead_w, bead_edge, bead_pocket_min = DRV["bead_w"], DRV["bead_edge"], DRV["bead_pocket_min"]
fast_off, fl_beyond, fl_R, fl_t = DRV["fast_off"], DRV["flange_beyond_glass"], DRV["flange_R"], DRV["flange_t"]
pad_d, tape_w, tape_margin, t_gap = DRV["pad_d"], DRV["tape_w"], DRV["tape_margin"], DRV["t_gap"]
pocket_clr, R_glass, R_cut, R_frame = DRV["pocket_clr"], DRV["R_glass"], DRV["R_cut"], DRV["R_frame"]
t_bond, t_opt, g_bs = DRV["t_bond"], DRV["t_opt"], DRV["g_bs"]
PANEL = (CO["panel_x0"], CO["panel_x1"], CO["panel_y0"], CO["panel_y1"])
POCKET = (RECT["pocket"]["x0"], RECT["pocket"]["x1"], RECT["pocket"]["y0"], RECT["pocket"]["y1"])
W = tuple(RECT["print_window"][k] for k in ("x0", "x1", "y0", "y1"))
TP11 = tuple(RECT["tail_pocket"][k] for k in ("x0", "x1", "y0", "y1"))      # GF-1.1 tail pocket at the land
HOLES = {f"H{i}": (CO[f"h{i}_x"], CO[f"h{i}_y"]) for i in range(1, 10)}
OUTLINE = BRD["outline"][0]
FPS = {f["ref"]: f for f in BRD["fps"]}
s_tape0 = g2 + lip_w + seat_w + tape_margin          # 3.9
s_tape1 = s_tape0 + tape_w                           # 15.9


def LV(tg):
    return {k: float(v) for k, v in LVALL[tg].items()}


hdr("1. INPUTS (GF-1.1 master %s)" % M["revision"][:6])
L3 = LV(3.0)
out("  levels glass 3.0 [G]:", ", ".join("%s %+.2f" % (k, v) for k, v in L3.items() if k.startswith("Z_") and k not in ("Z_TROUGH_TOP", "Z_PCB")))
out("  panel outline [G/M] x %.2f-%.2f y %.2f-%.2f; print window [G] x %.2f-%.2f y %.2f-%.2f" % (PANEL + W))
out("  measured [M]: frame STEP sha256 %s..., board STEP %s" % (MEA["frame_step"]["sha256"][:12], os.path.basename(MEA["board_step"]["file"])))
pcb_y = MEA["pcb_bottom_edge"]["103.85"]["y_max"]
out("  PCB bottom edge between the ears [M]: y %.3f at x 45 / 60 / 103.85 / 140 / 160 (all %s); PCB Z %s (STEP, no copper)"
    % (pcb_y, sorted({v['y_max'] for v in MEA['pcb_bottom_edge'].values()}), MEA["pcb_bottom_edge"]["103.85"]["Z"]))
bk = [c for c in MEA["components_bottom_zone"] if c["bbox"]["z"][0] < -0.01]
out("  board parts reaching in front of the PCB back in the bottom zone (y > 100, x 30-175) [M]: %s"
    % (", ".join("%s (x %s, y %s, Z %s)" % (c["ref"], c["bbox"]["x"], c["bbox"]["y"], c["bbox"]["z"]) for c in bk) or "none"))
shelf_end = MEA["frame_probe"]["103.85"]["y_crossings_at_Z"]["-3.0"]
out("  GF-1.1 frame at x 103.85 [M]: at Z -3 boundaries at y %s (shelf 116.43-118.97, beam 147.83-150.07); "
    "at Z -10 first frame face at y %.3f (tail-pocket bottom face)" % (shelf_end, MEA["frame_probe"]["103.85"]["y_crossings_at_Z"]["-10.0"][0]))
BEAM_IN, BEAM_OUT = 147.70, 150.20                  # [G/M] tail-pocket bottom face / frame bottom outer wall (2.5 wall, 1 deg)
SHELF_END_Y = 118.97                                # [M] shelf end over the tail span

# =====================================================================================================================
# 2. TAILS - real geometry and the bent-back route
# =====================================================================================================================
hdr("2. FPC TAILS: data, GF-1.1 route check, GF-2.0 bent-back route")
ds = MEA["ds1"]
TAILS = {
    "TFT": dict(part="tft_tail_5", L=67.65, Z_e=L3["Z_TAIL_TFT_EXIT"], t=0.30, x_exit=(84.02, 122.62),
                x_env=tuple(ds["tft_tail_5"]["bbox"]["x"]), y_end=112.0 + 2.875 - 4.0, Z_ret=1.6 + 0.8,
                conn="J10 (155.65, 112.0), entry face y 114.875, insertion 4.0", src_len="SAT sheet 16: 67.65 beyond the bottom edge [DS]"),
    "CTP": dict(part="ctp_tail_7", L=50.0, Z_e=L3["Z_TAIL_CTP_EXIT"], t=0.30, x_exit=(40.72, 75.82),
                x_env=tuple(ds["ctp_tail_7"]["bbox"]["x"]), y_end=112.4 + 2.05 - 3.0, Z_ret=1.6 + 0.6,
                conn="J11 (60.02, 112.4), entry face y 114.45, insertion 3.0", src_len="Fannal CT0476: 50 +-0.5 [DS]"),
}
for n, T in TAILS.items():
    m = ds[T["part"]]
    out("  %s tail: developed length %.2f (%s); exit at the panel edge y %.2f [M], width x %.2f-%.2f (%.2f) [M: section y 119.2 / model segs],"
        " envelope x %.2f-%.2f [M]; exit centre Z %.2f [E: panel model, %s above the panel back]; thickness %.2f [E: CTP drawing 0.3+-0.05, used for both];"
        " return leg Z %.2f (PCB top 1.6 + entry height [E]); %s"
        % (n, T["L"], T["src_len"], PANEL[3], T["x_exit"][0], T["x_exit"][1], T["x_exit"][1] - T["x_exit"][0], T["x_env"][0], T["x_env"][1],
           T["Z_e"], {"TFT": 2.6, "CTP": 3.9}[n], T["t"], T["Z_ret"], T["conn"]))
out("  TFT tail outline [E]: v 0-7 x 84.02-122.62 (bonded width), v 7-31 x 84.02-165.90 (L-shaped wide part), v 31-67.65 x 145.40-165.90; "
    "CTP: v 0-9.5 x 40.72-75.82, 9.5-34 x 50.92-70.62, 34-50 x 58.27-61.77 (steel stiffener on the finger end, back side)")
gap_tails = TAILS["TFT"]["x_exit"][0] - TAILS["CTP"]["x_exit"][1]
out("  gap between the two tails (CTP x1 75.82 -> TFT x0 84.02): %.2f; with 1.5 clearance each side a support could be %.2f wide (x %.2f-%.2f)"
    % (gap_tails, gap_tails - 3.0, TAILS["CTP"]["x_exit"][1] + 1.5, TAILS["TFT"]["x_exit"][0] - 1.5))


def old_route(T, Z_back_shift=0.0, ret_shift=0.0):
    """GF-1.1 / v2 route: flat leg at Z_e from the panel edge, semicircle to Z_ret, return leg to the connector"""
    Ze = T["Z_e"] + Z_back_shift
    r = (T["Z_ret"] + ret_shift - Ze) / 2
    run = PANEL[3] - T["y_end"]
    h = (T["L"] - math.pi * r - run) / 2
    return dict(r=r, h=h, y_c=PANEL[3] + h, y_bot=PANEL[3] + h + r)


for n, T in TAILS.items():
    v2 = old_route(T, Z_back_shift=0.80)            # v2 stand-off 5.0: exit 0.80 further back
    o = old_route(T)
    meas_bot = ds[T["part"]]["bbox"]["y"][1]
    out("  check of the length model [C vs M]: %s at the v2 stand-off r %.2f, loop bottom (outer surface) %.3f; DS1 STEP bbox y max %.3f (diff %+.3f) -> model ok"
        % (n, v2["r"], v2["y_bot"] + T["t"] / 2, meas_bot, v2["y_bot"] + T["t"] / 2 - meas_bot))
    out("     GF-1.1 route (panel back -5.80): flat leg %.2f at Z %.2f, U radius %.2f, loop bottom %.2f (outer %.2f)" % (o["h"], T["Z_e"], o["r"], o["y_bot"], o["y_bot"] + T["t"] / 2))

# ---------------------------------------------------------------------------------------- bend assumptions
L0 = 0.5            # [A] straight run beyond the panel edge face before the first bend (no-bend zone)
R_IN = 1.5          # [A] minimum INNER bend radius, static one-time bend (>= 6 x a <= 0.25 body; 5 x the conservative 0.30)
TT = 0.30           # [E] tail thickness used for clearances
RC = R_IN + TT / 2  # centreline radius 1.65
C_PF = 0.45         # [A] tail outer surface -> bridge pocket face, worst case (after the panel tolerance)
D_PANEL = 0.25      # [A] panel bottom edge towards the bridge: AA->outline 0.2 (concept sec. 9) + J1 alignment 0.1 + J2 0.05, RSS
NOSE_R = 1.5        # [A] round on the bridge's back-inner edge >= R_IN: a taut tail cannot be bent tighter than R1.5
G_BEND = L0 + R_IN + TT + C_PF + D_PANEL
out("\n  bend assumptions: straight %.2f beyond the edge face [A], inner radius >= %.2f [A] (centreline %.2f), tail %.2f [E], clearance to the pocket face"
    " %.2f worst case [A], panel edge position %.2f [A] -> bend gap g_bend = %.2f + %.2f + %.2f + %.2f + %.2f = %.2f"
    % (L0, R_IN, RC, TT, C_PF, D_PANEL, L0, R_IN, TT, C_PF, D_PANEL, G_BEND))
out("  why R_in 1.5: IPC-2223 static (bend-to-install) single-sided flex >= 6 x total thickness (3-6 x in some sources, 12 x double-sided);"
    " the 0.30 in the model is the ZIF finger thickness (with stiffener) - the bending body of a single-sided display FPC is typically"
    " 0.10-0.15 [A], so R_in 1.5 = 10-15 x that and 5 x the conservative 0.30. CTP spec (Fannal) qualifies the tail for 'tail bending 90 deg,"
    " 10 times left & right' and 'tail peeling 500 g/cm at 90 deg' [DS]. A double-sided 0.30 tail would need 12 x 0.3 = 3.6 (then g_bend 5.1).")
G_BEND = round(G_BEND, 2)
Y_PF = PANEL[3] + G_BEND                            # bridge pocket face (inner face) over the tail span
out("  -> bridge inner (pocket) face over the tail span at y %.2f (panel edge %.2f + %.2f); nose R%.1f on its back-inner edge" % (Y_PF, PANEL[3], G_BEND, NOSE_R))


def new_route(T, Z_leg, l0=L0, rc1=RC, rc2=RC, y_edge=None, L=None, Ze=None, n_arc=40):
    """bent-back route: straight l0, arc rc1 towards +Z, straight, arc rc2 back to +y, front leg at Z_leg, U-loop, return leg.
    Returns the centreline polyline (y, Z) and the lengths."""
    y_edge = PANEL[3] if y_edge is None else y_edge
    L = T["L"] if L is None else L
    Ze = T["Z_e"] if Ze is None else Ze
    dZ = Z_leg - Ze
    pts = [(y_edge, Ze), (y_edge + l0, Ze)]
    if dZ >= rc1 + rc2 - 1e-9:                       # two 90 deg arcs + vertical straight
        th = math.pi / 2
        vert = dZ - rc1 - rc2
    else:                                            # S with two arcs of angle th
        th = math.acos(1 - dZ / (rc1 + rc2))
        vert = 0.0
    c1 = (y_edge + l0, Ze + rc1)
    for k in range(1, n_arc + 1):
        ph = th * k / n_arc
        pts.append((c1[0] + rc1 * math.sin(ph), c1[1] - rc1 * math.cos(ph)))
    p = pts[-1]
    if vert > 0:
        pts.append((p[0], p[1] + vert))
        p = pts[-1]
    # second arc: tangent direction at p is (cos(90-th)...) ; centre on the +y side
    ang0 = th                                        # current heading measured from +y towards +Z
    c2 = (p[0] + rc2 * math.sin(ang0), p[1] - rc2 * math.cos(ang0))
    for k in range(1, n_arc + 1):
        ph = ang0 - ang0 * k / n_arc
        pts.append((c2[0] - rc2 * math.sin(ph), c2[1] + rc2 * math.cos(ph)))
    y_s, Z_s = pts[-1]
    l_s = l0 + (rc1 + rc2) * th + vert
    r = (T["Z_ret"] - Z_leg) / 2
    # L = l_s + (y_c - y_s) + pi r + (y_c - y_end)
    y_c = (L - l_s - math.pi * r + y_s + T["y_end"]) / 2
    front = y_c - y_s
    pts.append((y_c, Z_leg))
    zc = Z_leg + r
    for k in range(1, 2 * n_arc + 1):
        ph = math.pi * k / (2 * n_arc)
        pts.append((y_c + r * math.sin(ph), zc - r * math.cos(ph)))
    pts.append((T["y_end"], T["Z_ret"]))
    return dict(pts=np.array(pts), theta_deg=math.degrees(th), vert=vert, l_s=l_s, y_s=y_s, Z_s=Z_s, r=r, y_c=y_c, front=front,
                y_bot=y_c + r, v_s_end=l_s, v_loop=(l_s + front, l_s + front + math.pi * r), Z_leg=Z_leg)


Z_LEG = round(TAILS["TFT"]["Z_e"] + 2 * RC, 2)      # TFT: exactly two 90-deg bends; CTP: same Z with a short vertical straight
out("  front legs of both tails at Z_leg = Z_TAIL_TFT_EXIT + 2 x %.2f = %.2f (behind the bridge; the frame has no feature at this Z)" % (RC, Z_LEG))
ROUTE = {n: new_route(T, Z_LEG) for n, T in TAILS.items()}
for n, R_ in ROUTE.items():
    T = TAILS[n]
    o = old_route(T)
    out("  %s GF-2.0 route [C]: straight %.2f, arc R%.2f (centre line) %.1f deg, vertical straight %.2f, arc R%.2f back, S ends at y %.2f Z %.2f (tail v %.2f);"
        " front leg %.2f at Z %.2f; U-loop R %.2f (GF-1.1 %.2f) centre y %.2f; loop bottom %.2f, outer %.2f (GF-1.1 %.2f) ; loop on tail v %.1f-%.1f"
        % (n, L0, RC, R_["theta_deg"], R_["vert"], RC, R_["y_s"], R_["Z_s"], R_["v_s_end"], R_["front"], R_["Z_leg"], R_["r"], o["r"], R_["y_c"],
           R_["y_bot"], R_["y_bot"] + T["t"] / 2, o["y_bot"] + T["t"] / 2, R_["v_loop"][0], R_["v_loop"][1]))
out("  TFT S-bend lies on v 0.5-%.2f (< 7.0, the narrow bonded-width part, x 84.02-122.62); CTP S-bend on v 0.5-%.2f (< 9.5, the 35.1-wide first segment)"
    % (ROUTE["TFT"]["v_s_end"], ROUTE["CTP"]["v_s_end"]))


# ------------------------------------------------------------------------------- section polygons (y, Z) at the bottom
def frame_bottom_polygon(tg, glass_y1, y_pf=Y_PF, nose=NOSE_R, y_out=BEAM_OUT, y_in=BEAM_IN, n=24):
    """GF-2.0 bottom section over the tail span (bridge + flange plate + bottom wall), one closed polygon (y, Z)"""
    Z = LV(tg)
    ZFB = Z["Z_FLANGE_BACK"]
    yr = glass_y1 + g2                                       # recess wall at the lip top
    P = [(y_pf, Z["Z_LAND"]), (yr, Z["Z_LAND"]), (yr, Z["Z_GLASS_FRONT"]), (yr + lip_w, Z["Z_GLASS_FRONT"]),
         (yr + lip_w, Z["Z_SHEET_BACK"]), (glass_y1 + g2 + 2.5, Z["Z_SHEET_BACK"]), (glass_y1 + g2 + 2.5, Z["Z_FLANGE_FRONT"]),
         (y_out, Z["Z_FLANGE_FRONT"]), (y_out, Z["Z_TROUGH_TOP"]), (y_in, Z["Z_TROUGH_TOP"]), (y_in, ZFB)]
    if abs(ZFB - Z["Z_STEPWALL_BACK"]) > 1e-6:          # flange back in front of the step-wall back: floor steps at s 2.9
        P += [(glass_y1 + g2 + 2.5, ZFB), (glass_y1 + g2 + 2.5, Z["Z_STEPWALL_BACK"])]
    P += [(y_pf + nose, Z["Z_LANDPLATE_BACK"])]
    cy, cz = y_pf + nose, Z["Z_LANDPLATE_BACK"] - nose
    for k in range(1, n):
        ph = math.pi / 2 * k / n
        P.append((cy - nose * math.sin(ph), cz + nose * math.cos(ph)))
    P += [(y_pf, Z["Z_LANDPLATE_BACK"] - nose)]
    return np.array(P)


def others_polygons(tg, glass_y1):
    """glass, bead, panel layers, Formex, shelf end, PCB, sheet (y, Z) for clearance checks and the figures"""
    Z = LV(tg)
    return {
        "glass": np.array([(100, Z["Z_GLASS_FRONT"]), (glass_y1, Z["Z_GLASS_FRONT"]), (glass_y1, Z["Z_GLASS_BACK"]), (100, Z["Z_GLASS_BACK"])]),
        "panel (CTP+LCM)": np.array([(100, Z["Z_CTP_FRONT"]), (PANEL[3], Z["Z_CTP_FRONT"]), (PANEL[3], Z["Z_PANEL_BACK"]), (100, Z["Z_PANEL_BACK"])]),
        "Formex": np.array([(100, Z["Z_FORMEX_FRONT"]), (118.5, Z["Z_FORMEX_FRONT"]), (118.5, Z["Z_SEAT"]), (100, Z["Z_SEAT"])]),
        "shelf end": np.array([(116.43, Z["Z_SEAT"]), (SHELF_END_Y, Z["Z_SEAT"]), (SHELF_END_Y, Z["Z_SHELF_BACK"]), (116.43, Z["Z_SHELF_BACK"])]),
        "PCB": np.array([(100, 0.0), (pcb_y, 0.0), (pcb_y, 1.6), (100, 1.6)]),
    }


def seg_dist(P, A, B):
    """distance from points P (n,2) to segments A-B (m,2) -> (n,) min"""
    AB = B - A
    L2 = np.maximum((AB ** 2).sum(1), 1e-12)
    t = np.clip(((P[:, None, :] - A[None]) * AB[None]).sum(2) / L2[None], 0, 1)
    Q = A[None] + t[..., None] * AB[None]
    return np.sqrt(((P[:, None, :] - Q) ** 2).sum(2)).min(1)


def densify(pts, step=0.02):
    out_ = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n_ = max(1, int(math.ceil(np.hypot(*(b - a)) / step)))
        for k in range(1, n_ + 1):
            out_.append(a + (b - a) * k / n_)
    return np.array(out_)


def inside(P, poly):
    """even-odd point in polygon"""
    x, y = P[:, 0], P[:, 1]
    res = np.zeros(len(P), bool)
    pv = poly
    for (x1, y1), (x2, y2) in zip(pv, np.roll(pv, -1, axis=0)):
        cond = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / np.where(y2 - y1 == 0, 1e-12, y2 - y1) + x1)
        res ^= cond
    return res


def clearance(route_pts, poly, half_t):
    """min surface clearance tail -> polygon (negative = overlap)"""
    P = densify(route_pts)
    poly_c = np.vstack([poly, poly[:1]])
    d = seg_dist(P, poly_c[:-1], poly_c[1:]) - half_t
    ins = inside(P, poly)
    return float(np.where(ins, -d - 2 * half_t, d).min()), P[int(np.argmin(np.where(ins, -1e9, d)))]


B_REC = 18.5            # recommended border (section 3 derives it)
GLASS_Y1_REC = W[3] + B_REC
CLR = {}
out("\n  clearances of the GF-2.0 route (surface to surface) [C], border %.1f, nominal and worst case:" % B_REC)
out("  %-5s %-6s %-44s %8s %s" % ("tail", "glass", "to", "nominal", "where (y, Z)"))
for n, T in TAILS.items():
    for tg in TG_LIST:
        fr = frame_bottom_polygon(tg, GLASS_Y1_REC)
        c, w = clearance(ROUTE[n]["pts"], fr, T["t"] / 2)
        CLR[(n, tg, "frame bridge")] = c
        out("  %-5s %-6s %-44s %8.2f (%.2f, %.2f)" % (n, tg, "frame (bridge nose / pocket face / floor / wall)", c, w[0], w[1]))
    Zl3 = LV(3.0)
    oth = others_polygons(3.0, GLASS_Y1_REC)
    obst = {"glass back (at the exit)": oth["glass"],
            "panel edge face above the exit + back corner": np.array([(117.0, T["Z_e"] + 0.6), (PANEL[3], T["Z_e"] + 0.6), (PANEL[3], Zl3["Z_PANEL_BACK"]), (117.0, Zl3["Z_PANEL_BACK"])]),
            "Formex": oth["Formex"], "shelf end (y 118.97)": oth["shelf end"],
            "PCB (return leg over its edge, unchanged)": oth["PCB"]}
    for k, pg in obst.items():
        c, w = clearance(ROUTE[n]["pts"], pg, T["t"] / 2)
        CLR[(n, 3.0, k)] = c
        out("  %-5s %-6s %-44s %8.2f (%.2f, %.2f)" % (n, 3.0, k, c, w[0], w[1]))
# worst cases: panel edge +D_PANEL towards the bridge, exit Z +-0.3 [E], tail length +-0.5, inner radius as built
out("\n  tolerance cases (glass 3.0, border %.1f) [C]:" % B_REC)
WC_ROWS = []
for n, T in TAILS.items():
    fr = frame_bottom_polygon(3.0, GLASS_Y1_REC)
    for lab, kw in (("nominal", {}), ("panel edge +0.25 (towards the bridge)", dict(y_edge=PANEL[3] + D_PANEL)),
                    ("panel edge +0.35 (WC)", dict(y_edge=PANEL[3] + 0.35)),
                    ("exit Z +0.30 (further back)", dict(Ze=T["Z_e"] + 0.3)), ("exit Z -0.30 (towards the glass)", dict(Ze=T["Z_e"] - 0.3)),
                    ("length +0.5", dict(L=T["L"] + 0.5)), ("length -0.5", dict(L=T["L"] - 0.5)),
                    ("straight 1.0 instead of 0.5", dict(l0=1.0)), ("R_in 1.8 (6 x 0.30)", dict(rc1=1.95, rc2=1.95))):
        R_ = new_route(T, Z_LEG if "Ze" not in kw else max(Z_LEG, kw["Ze"] + 2 * kw.get("rc1", RC)), **kw)
        c, w = clearance(R_["pts"], fr, T["t"] / 2)
        cg, _ = clearance(R_["pts"], others_polygons(3.0, GLASS_Y1_REC)["glass"], T["t"] / 2)
        pb = BEAM_IN - (R_["y_bot"] + T["t"] / 2)
        WC_ROWS.append((n, lab, c, cg, pb, R_["r"]))
        out("  %-4s %-38s to the bridge %5.2f | to the glass back %5.2f | loop bottom %7.2f -> pocket bottom face %.2f | U R %.2f"
            % (n, lab, c, cg, R_["y_bot"] + T["t"] / 2, pb, R_["r"]))
for n, T in TAILS.items():
    xe = T["x_env"]
    out("  %s envelope x %.2f-%.2f vs tail-pocket side walls %.1f / %.1f: %.2f / %.2f (unchanged from GF-1.1)"
        % (n, xe[0], xe[1], TP11[0], TP11[1], xe[0] - TP11[0], TP11[1] - xe[1]))
# pocket corner R1.5 vs the TFT loop corner
cc = (TP11[1] - DRV["trough_R"], BEAM_IN - DRV["trough_R"])
tc = (TAILS["TFT"]["x_env"][1], ROUTE["TFT"]["y_bot"] + 0.15)
d_side = TP11[1] - tc[0]
d_bot = BEAM_IN - tc[1]
d_arc = min(math.hypot(cc[0] + DRV["trough_R"] * math.cos(a) - tc[0], cc[1] + DRV["trough_R"] * math.sin(a) - tc[1]) for a in np.linspace(0, math.pi / 2, 91))
out("  TFT loop corner (%.2f, %.2f) in plan vs the R%.1f pocket corner: side wall %.2f, bottom face %.2f, corner arc %.2f (>= 1.5)"
    % (tc[0], tc[1], DRV["trough_R"], d_side, d_bot, d_arc))
out("  taut-tail case: the tail can only lie on the R%.1f nose -> centreline radius %.2f >= R_in + t/2 %.2f; on the pocket face it is straight." % (NOSE_R, NOSE_R + 0.15, RC))
out("  PCB back-side parts near the route: none [M] (only J20, x 21.9-30.6, y 97.5-107.6, reaches Z -1.87; far from the tails)")

# =====================================================================================================================
# 3. BORDER BUDGET
# =====================================================================================================================
hdr("3. BORDER BUDGET AT THE BOTTOM: window edge -> panel edge (bezel) + bend gap + land = border")
BEZEL = PANEL[3] - W[3]
LAND_NEED = bead_edge + bead_w + bead_pocket_min
out("  bottom bezel (window bottom %.2f -> panel bottom %.2f) = %.2f [G/M]; other sides window -> panel: top %.2f, abs left %.2f, abs right %.2f"
    % (W[3], PANEL[3], BEZEL, W[2] - PANEL[2], W[0] - PANEL[0], PANEL[1] - W[1]))
out("  full GF-1.1 bead needs a land of bead_edge %.1f + bead_w %.1f + bead_pocket_min %.1f = %.2f" % (bead_edge, bead_w, bead_pocket_min, LAND_NEED))
b_min = BEZEL + G_BEND + LAND_NEED
B_FULL = math.ceil(b_min * 2 - 1e-9) / 2
out("  smallest equal border with the full bead: %.2f + %.2f + %.2f = %.2f -> rounded up to 0.5: %.1f (reserve %.2f = largest g_bend %.2f that still fits)"
    % (BEZEL, G_BEND, LAND_NEED, b_min, B_FULL, B_FULL - b_min, B_FULL - BEZEL - LAND_NEED))
assert abs(B_FULL - B_REC) < 1e-9, (B_FULL, B_REC)
out("\n  %-7s %-9s %-11s %-30s %-11s %-12s %s" % ("border", "bot. land", "bead (0.9/1.0)", "bead area (4.0 elsewhere) mm2", "vs 2486.7", "glass", "verdict"))
BTAB = []
for b in (14.0, 15.0, 16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0):
    land_b = b - BEZEL - G_BEND
    wb = land_b - bead_edge - bead_pocket_min
    gW_, gH_ = (W[1] - W[0]) + 2 * b, (W[3] - W[2]) + 2 * b
    # bead centre-line rectangle; bottom bead width wb over the full bottom side (simplest: straight bottom bead)
    rw, rh = gW_ - 2 * (bead_edge + bead_w / 2), gH_ - 2 * (bead_edge + bead_w / 2)
    wbe = max(min(wb, bead_w), 0.0)
    A = (2 * rh + rw) * bead_w + rw * wbe
    A_mod = A * 2486.7 / 2510.0                          # concept formula 2510 vs modelled 2486.7 (corner shape)
    if wb < 0:
        v = "IMPOSSIBLE: no bead fits"
    elif wb < 2.0:
        v = "not sound (bead < 2.0)"
    elif wb < 3.0:
        v = "marginal (bead < 3.0)"
    elif wb < bead_w:
        v = "sound with a narrower bottom bead"
    else:
        v = "full bead (GF-1.1 margins)"
    BTAB.append(dict(border=b, land_bottom=round(land_b, 2), bead_bottom_max=round(wb, 2), bead_area_mm2=round(A_mod, 0), glass=[round(gW_, 2), round(gH_, 2)], verdict=v))
    out("  %-7.1f %-9.2f %-14.2f %-30.0f %-+11.1f %6.2f x %6.2f  %s" % (b, land_b, wb, A_mod, (A_mod / 2486.7 - 1) * 100, gW_, gH_, v))
out("  (bead area scaled from the concept formula to the modelled GF-1.1 value 2486.7 / 2510; at 14.0 even a zero-margin bead would be %.2f wide)" % (14.0 - BEZEL - G_BEND))
for b in (14.0,):
    out("  border 14.0: land %.2f after the bend gap; needed %.2f. Even with g_bend %.2f (straight 0.3, R_in 1.0, no clearance) the land is %.2f "
        "-> a 4.0 bead needs border >= %.2f; a sealed bottom at 14.0 would need g_bend <= %.2f, i.e. a tail bent at the edge face with no radius."
        % (14.0 - BEZEL - G_BEND, LAND_NEED, 0.3 + 1.0 + 0.3, 14.0 - BEZEL - 1.6, BEZEL + 1.6 + LAND_NEED, 14.0 - BEZEL - LAND_NEED))

# =====================================================================================================================
# 4. GF-2.0 PLAN GEOMETRY (recommended border, and 14.0 / 17.5 for comparison)
# =====================================================================================================================
hdr("4. GF-2.0 PLAN GEOMETRY")


def plan(b):
    GL = (W[0] - b, W[1] + b, W[2] - b, W[3] + b)
    gc = ((GL[0] + GL[1]) / 2, (GL[2] + GL[3]) / 2)
    ring = lambda off: (GL[0] - off, GL[1] + off, GL[2] - off, GL[3] + off)
    FL = ring(fast_off)
    fl = list(ring(fl_beyond))
    fl[3] = max(fl[3], BEAM_OUT)                       # the flange must reach the frame's bottom wall (tail pocket closed)
    return dict(b=b, GL=GL, gc=gc, gW=GL[1] - GL[0], gH=GL[3] - GL[2], FL=FL, FLANGE=tuple(fl),
                lip_in=ring(g2), lip_out=ring(g2 + lip_w), seat=ring(g2 + lip_w + seat_w), cut=ring(g2 + lip_w + g1),
                tape_in=ring(s_tape0), tape_out=ring(s_tape1),
                lands={"abs left (front-view right)": POCKET[0] - GL[0], "abs right (front-view left)": GL[1] - POCKET[1],
                       "top": POCKET[2] - GL[2], "bottom over the tail span (to the bridge pocket face)": GL[3] - Y_PF,
                       "bottom outside the tail span (x < 38.9, x > 167.7)": GL[3] - POCKET[3]})


PL = {b: plan(b) for b in (14.0, 17.5, B_REC)}
P = PL[B_REC]
GL, gc = P["GL"], P["gc"]
out("  border %.1f on all four sides -> GLASS x %.2f-%.2f y %.2f-%.2f (%.2f x %.2f), centre (%.3f, %.3f) = window centre (GF-1.1: 181.48 x 143.83, centre 103.85 / 82.085)"
    % (B_REC, GL[0], GL[1], GL[2], GL[3], P["gW"], P["gH"], gc[0], gc[1]))
for k in ("lip_in", "lip_out", "seat", "cut", "tape_in", "tape_out", "FL", "FLANGE"):
    r_ = P[k]
    out("  %-9s x %8.2f-%8.2f y %8.2f-%8.2f (%7.2f x %7.2f)" % (k, r_[0], r_[1], r_[2], r_[3], r_[1] - r_[0], r_[3] - r_[2]))
out("  flange bottom edge: glass + 21 would be y %.2f; the frame's bottom wall (tail pocket closed) ends at y %.2f -> flange to %.2f (%.2f below the cut-out; sides %.2f)"
    % (GL[3] + fl_beyond, BEAM_OUT, P["FLANGE"][3], P["FLANGE"][3] - P["cut"][3], fl_beyond - 1.8))
out("  lands (pocket face -> glass edge) and bead (0.9-4.9 inside the edge) to the pocket face:")
for k, v in P["lands"].items():
    out("    %-55s %6.2f -> bead to pocket %5.2f %s" % (k, v, v - bead_edge - bead_w, "OK" if v - bead_edge - bead_w >= bead_pocket_min - 1e-9 else "FAIL"))
for b in (14.0, 17.5):
    Q = PL[b]
    out("  (border %.1f: glass %.2f x %.2f, y1 %.2f, cut-out %.2f x %.2f, flange %.2f x %.2f; bottom land %.2f)" % (
        b, Q["gW"], Q["gH"], Q["GL"][3], Q["cut"][1] - Q["cut"][0], Q["cut"][3] - Q["cut"][2],
        Q["FLANGE"][1] - Q["FLANGE"][0], Q["FLANGE"][3] - Q["FLANGE"][2], Q["lands"]["bottom over the tail span (to the bridge pocket face)"]))
# pips (port): 8 on the bead centre line, 2 per side at +-1/4 of the side
s_bead = -(bead_edge + bead_w / 2)
PIPS = []
for fx in (-0.25, 0.25):
    PIPS += [(gc[0] + fx * P["gW"], GL[2] - s_bead), (gc[0] + fx * P["gW"], GL[3] + s_bead)]
for fy in (-0.25, 0.25):
    PIPS += [(GL[0] - s_bead, gc[1] + fy * P["gH"]), (GL[1] + s_bead, gc[1] + fy * P["gH"])]
out("  pips P1-P8 (same rule as GF-1.1):", ", ".join("P%d (%.2f, %.2f)" % (i, x, y) for i, (x, y) in enumerate(PIPS, 1)))
# logo zone
LOGO = (gc[0], (W[3] + GL[3]) / 2, 100.0, B_REC - 1.0 - 2.5)
out("  logo zone: centre (%.2f, %.2f), <= %.0f x %.1f (>= 1.0 from the window, >= 2.5 from the glass edge); at border 14.0 it would be <= 100 x 10.5"
    % LOGO)
# tape
A_tape = 2 * ((P["gW"] + 2) + (P["gH"] + 2)) * tape_w
out("  VHB strips: s %.1f-%.1f, top/bottom %.2f long, sides %.2f long, area %.0f mm2 (GF-1.1 7903); bottom strip at y %.2f-%.2f on the flange plate in front of the tail pocket"
    % (s_tape0, s_tape1, P["gW"] + 2, P["gH"] + 2, A_tape, GL[3] + s_tape0, GL[3] + s_tape1))
out("  flange below the bottom strip: y %.2f-%.2f (%.2f) - too narrow for a second 12 mm strip; none needed (section 5)" % (GL[3] + s_tape1, P["FLANGE"][3], P["FLANGE"][3] - GL[3] - s_tape1))
# print window unchanged; visible
out("  print window unchanged x %.2f-%.2f y %.2f-%.2f; visible module (cut-out) %.2f x %.2f (GF-1.1 185.08 x 147.43); overall flange %.2f x %.2f (GF-1.1 223.48 x 185.83)"
    % (W + (P["cut"][1] - P["cut"][0], P["cut"][3] - P["cut"][2], P["FLANGE"][1] - P["FLANGE"][0], P["FLANGE"][3] - P["FLANGE"][2])))

# ------------------------------------------------------------------------------------------------ fasteners (port of concept 4a)
hdr("4a. FASTENERS F1-F8 at the GF-2.0 glass (rules as concept 4a)")


def seg_d(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy or 1e-12)))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def poly_d(p, pts):
    return min(seg_d(p, pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def rect_d(p, r):
    dx = max(r[0] - p[0], 0.0, p[0] - r[1]); dy = max(r[2] - p[1], 0.0, p[1] - r[3])
    return math.hypot(dx, dy)


def rrect_d(p, r, R):
    return rect_d(p, (r[0] + R, r[1] - R, r[2] + R, r[3] - R)) - R


def rrect_pts(r, R, n=60):
    x0, x1, y0, y1 = r[:4]
    pts = []
    for cx, cy, a0 in ((x1 - R, y0 + R, -90), (x1 - R, y1 - R, 0), (x0 + R, y1 - R, 90), (x0 + R, y0 + R, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
    return pts


def rrect_inner_d(p, r, R):
    """distance from a point inside a rounded rectangle (corner radius R) to its boundary"""
    return poly_d(p, rrect_pts(r, R))


J20, J2 = FPS["J20"]["crtyd"], FPS["J2"]["crtyd"]
CORR = [(-1e3, J20[2], J20[1] - 2.0, J20[3] + 2.0), (-1e3, J2[2], J2[1] - 2.0, J2[3] + 2.0)]
LOOPS = [(CO["loop_ctp_x0"], CO["loop_ctp_x1"], PANEL[3], CO["loop_ctp_y1"]), (CO["loop_tft_x0"], CO["loop_tft_x1"], PANEL[3], CO["loop_tft_y1"])]
TAILPOCKET = (TP11[0], TP11[1], PANEL[3], BEAM_IN)


def fasteners(Pp, F7=None):
    G_, FL_ = Pp["GL"], Pp["FL"]
    g_c = Pp["gc"]
    FA = {"F1": (FL_[0], FL_[2]), "F2": (FL_[1], FL_[2]), "F3": (FL_[1], FL_[3]), "F4": (FL_[0], FL_[3]),
          "F5": (g_c[0], FL_[2]), "F6": (FL_[1], g_c[1]), "F7": (g_c[0], FL_[3]) if F7 is None else F7, "F8": (FL_[0], g_c[1])}
    rows = []
    for n_, (x, y) in FA.items():
        ux, uy = g_c[0] - x, g_c[1] - y
        L_ = math.hypot(ux, uy)
        d_out = poly_d((x, y), OUTLINE)
        hn, hd = min(((h, math.hypot(x - hx, y - hy)) for h, (hx, hy) in HOLES.items()), key=lambda t: t[1])
        d_wire = min(rect_d((x, y), r) for r in CORR)
        d_tail = min([rect_d((x, y), r) for r in LOOPS] + [rect_d((x, y), TAILPOCKET)])
        d_boss = hd - pad_d / 2 - 4.0
        d_cut = rrect_d((x, y), Pp["cut"], R_cut)
        d_fl = rrect_inner_d((x, y), Pp["FLANGE"], fl_R)
        ok = d_out >= 6.5 and hd >= 11.0 and d_boss > 0 and d_cut >= 8.0 and d_tail >= 9.0 + 1.5 and d_fl - pad_d / 2 >= 1.0 - 0.01
        rows.append(dict(name=n_, x_abs=r4(x), y_abs_down=r4(y), slot_axis=[r4(ux / L_), r4(uy / L_)], slot_axis_deg=r4(math.degrees(math.atan2(uy, ux))),
                         r_from_glass_centre=r4(L_), d_board_outline_incl_ears=r4(d_out), nearest_ear_hole=hn, d_ear_hole=r4(hd),
                         d_J20_J2_wire_corridor=r4(d_wire), d_tail_pocket_or_loops=r4(d_tail), d_pcb_boss_edge_from_tube=r4(d_boss),
                         d_cut_out_edge=r4(d_cut), d_tube_edge_to_flange_edge=r4(d_fl - pad_d / 2), front_view_u=r4(-(x - g_c[0])),
                         front_view_v=r4(g_c[1] - y), ok=ok))
    return rows


FROWS = fasteners(P)
out("  %-4s %8s %8s %8s %7s %8s %9s %8s %8s %8s %8s %7s" % ("", "x", "y", "axis", "r_c", "outline", "ear hole", "J20/J2", "tails", "boss gap", "cut edge", "fl rim"))
for f in FROWS:
    out("  %-4s %8.2f %8.2f %8.2f %7.1f %8.2f %3s %5.2f %8.1f %8.1f %8.1f %8.2f %7.2f  %s" % (
        f["name"], f["x_abs"], f["y_abs_down"], f["slot_axis_deg"], f["r_from_glass_centre"], f["d_board_outline_incl_ears"], f["nearest_ear_hole"],
        f["d_ear_hole"], f["d_J20_J2_wire_corridor"], f["d_tail_pocket_or_loops"], f["d_pcb_boss_edge_from_tube"], f["d_cut_out_edge"],
        f["d_tube_edge_to_flange_edge"], "OK" if f["ok"] else "CONFLICT"))
out("  rules: outline >= 6.5 and ear hole >= 11.0 (socket), tube R9 clear of the PCB bosses (R4), >= 8.0 to the cut-out, tube R9 + 1.5 clear of the"
    " tail pocket / loops, tube edge >= 1.0 inside the flange edge")
F7 = next(f for f in FROWS if f["name"] == "F7")
out("  F7 at (%.2f, %.2f) lies %.1f inside the tail pocket (x 38.9-167.7, y 119.0-147.7), over the TFT loop (x 84.0-165.9, to y %.1f) -> cannot stay."
    % (F7["x_abs"], F7["y_abs_down"], BEAM_IN - F7["y_abs_down"], ROUTE["TFT"]["y_bot"] + 0.15))
F7TAB = (gc[0], BEAM_OUT + 1.5 + pad_d / 2)
out("  nearest legal F7 on the centre line: below the bottom wall, tube edge 1.5 from it -> (%.2f, %.2f), %.2f below the glass edge;"
    " needs a flange tab to y %.2f (+%.2f) and a stud %.1f below the cut-out edge" % (F7TAB[0], F7TAB[1], F7TAB[1] - GL[3], F7TAB[1] + 10, F7TAB[1] + 10 - P["FLANGE"][3], F7TAB[1] - P["cut"][3]))
# symmetry of the corner fasteners (R4 rivets visible)
c4 = [f for f in FROWS if f["name"] in ("F1", "F2", "F3", "F4")]
out("  corner fasteners in front view (u, v) about the glass centre: %s -> symmetric (|u| %.2f, |v| %.2f on all four); R4 head edge to the cut-out corner arc %.2f"
    % (", ".join("%s (%+.2f, %+.2f)" % (f["name"], f["front_view_u"], f["front_view_v"]) for f in c4), abs(c4[0]["front_view_u"]), abs(c4[0]["front_view_v"]),
       c4[0]["d_cut_out_edge"] - 7.0))

# =====================================================================================================================
# 5. RING SECTIONS AND GRILLAGE (port of concept_calc.py sec. 7)
# =====================================================================================================================
hdr("5. PUSH ON THE GLASS - grillage port (panel, LOCA, PCB stiffness NOT counted; frame E 3500; VHB E 1 MPa)")
D_fl = E_F * fl_t ** 3 / (12 * (1 - NU_F ** 2))
I_LINK = 2 * 109.8
G_F = E_F / (2 * (1 + NU_F))


def section_props(rects):
    A = sum((r[1] - r[0]) * (r[3] - r[2]) for r in rects)
    zc = sum((r[1] - r[0]) * (r[3] - r[2]) * (r[2] + r[3]) / 2 for r in rects) / A
    I = sum((r[1] - r[0]) * (r[3] - r[2]) ** 3 / 12 + (r[1] - r[0]) * (r[3] - r[2]) * ((r[2] + r[3]) / 2 - zc) ** 2 for r in rects)
    J = sum(max(r[1] - r[0], r[3] - r[2]) * min(r[1] - r[0], r[3] - r[2]) ** 3 / 3 for r in rects)
    zmin, zmax = min(r[2] for r in rects), max(r[3] for r in rects)
    return dict(A=A, zc=zc, I=I, J=J, c=max(abs(zmin - zc), abs(zmax - zc)), rects=rects)


def ring_rects(Zl, land, kind="side", s_fl_end=None, beam=None):
    """port of concept ring_section (kind 'side'); 'bridge' = no pocket wall / shelf (bend gap); beam = (s_in, s_out) adds the bottom wall"""
    s_pf = -land
    zfb = Zl["Z_STEPWALL_BACK"] if abs(Zl["Z_LANDPLATE_BACK"] - Zl["Z_FLANGE_BACK"]) < 0.5 else Zl["Z_FLANGE_BACK"]
    s_end = fl_beyond if s_fl_end is None else s_fl_end
    R_ = [(g2, g2 + lip_w, Zl["Z_GLASS_FRONT"], Zl["Z_SHEET_BACK"]),
          (g2, g2 + 2.5, Zl["Z_SHEET_BACK"], Zl["Z_STEPWALL_BACK"]),
          (g2 + 2.5, s_end, Zl["Z_FLANGE_FRONT"], zfb),
          (s_pf, g2, Zl["Z_LAND"], Zl["Z_LANDPLATE_BACK"])]
    if kind == "side":
        R_ += [(s_pf, s_pf + 2.5, Zl["Z_LANDPLATE_BACK"], 0.0),
               (s_pf - (CO["seat_w"] + pocket_clr), s_pf, Zl["Z_SEAT"], Zl["Z_SHELF_BACK"])]
    if beam is not None:
        R_ = [r for r in R_ if r[0] != g2 + 2.5] + [(g2 + 2.5, beam[0], Zl["Z_FLANGE_FRONT"], zfb),
                                                    (beam[0], beam[1], Zl["Z_FLANGE_FRONT"], Zl["Z_TROUGH_TOP"])]
    return R_


def band_shares(a, b, Lf):
    a1, b1 = min(a, Lf), min(b, Lf)
    s0 = (b1 - b1 ** 2 / (2 * Lf)) - (a1 - a1 ** 2 / (2 * Lf))
    return s0, (b - a) - s0


SH0, SH1 = band_shares(s_tape0, s_tape1, fast_off)


def beam_k(EI, GJ, Lx):
    k = np.zeros((6, 6))
    b = np.array([[12, 6 * Lx, -12, 6 * Lx], [6 * Lx, 4 * Lx * Lx, -6 * Lx, 2 * Lx * Lx], [-12, -6 * Lx, 12, -6 * Lx], [6 * Lx, 2 * Lx * Lx, -6 * Lx, 4 * Lx * Lx]])
    idx = [0, 1, 3, 4]
    k[np.ix_(idx, idx)] = EI / Lx ** 3 * b
    k[2, 2] = k[5, 5] = GJ / Lx
    k[2, 5] = k[5, 2] = -GJ / Lx
    return k


def tmat(c, s):
    T = np.zeros((6, 6))
    for o in (0, 3):
        T[o, o] = 1.0
        T[o + 1, o + 1], T[o + 1, o + 2] = c, s
        T[o + 2, o + 1], T[o + 2, o + 2] = -s, c
    return T


def grillage(GLr, FLr, SECE, t_g, supports, vhb=False, line_q=0.0, loads=(), extra_ys=(), E_vhb=1.0, extra_xs=(), tab=None, ribs=()):
    """port of concept grillage(); SECE = {'top','bottom','left','right'} ring sections (concept: one section for all).
    GF-2.0 additions: extra_xs (more grid lines), tab = (x0, x1, y1): a flange tab below the bottom fastener line, modelled
    as flange-plate strips (D_fl x width) only between x0 and x1, down to y1 (for an F7 below the bottom wall)."""
    gx0, gx1, gy0, gy1 = GLr
    gW_, gH_ = gx1 - gx0, gy1 - gy0
    D_g = E_G * t_g ** 3 / (12 * (1 - NU_G ** 2))
    fx0, fx1, fy0, fy1 = FLr
    xs = sorted({fx0, fx1, gx0, gx1} | {gx0 + gW_ * i / 16 for i in range(17)} | set(extra_xs) | (set(tab[:2]) if tab else set()))
    ys = sorted({fy0, fy1, gy0, gy1} | {gy0 + gH_ * i / 12 for i in range(13)} | set(extra_ys) | ({tab[2]} if tab else set()))
    xs = [x for i, x in enumerate(xs) if i == 0 or x - xs[i - 1] > 1.5]
    ys = [y for i, y in enumerate(ys) if i == 0 or y - ys[i - 1] > 1.5]
    assert gy1 in ys and gy0 in ys and gx0 in xs and gx1 in xs
    nx, ny = len(xs), len(ys)
    nid = lambda ix, iy: ix * ny + iy
    n = 3 * nx * ny
    K = np.zeros((n, n))
    elems = []

    def add_el(p, q, EI_g, EI_r, GJ, edge):
        (x1, y1), (x2, y2) = (xs[p // ny], ys[p % ny]), (xs[q // ny], ys[q % ny])
        Ln = math.hypot(x2 - x1, y2 - y1); c, s = (x2 - x1) / Ln, (y2 - y1) / Ln
        kl = beam_k(EI_g + EI_r, GJ, Ln); T = tmat(c, s)
        kg = T.T @ kl @ T
        dofs = [3 * p, 3 * p + 1, 3 * p + 2, 3 * q, 3 * q + 1, 3 * q + 2]
        K[np.ix_(dofs, dofs)] += kg
        elems.append((dofs, kl, T, EI_g, EI_r, edge))

    def trib(lines, i):
        lo = lines[i] - (lines[i] - lines[i - 1]) / 2 if i > 0 else lines[i]
        hi = lines[i] + (lines[i + 1] - lines[i]) / 2 if i < len(lines) - 1 else lines[i]
        return lo, hi

    for ix in range(nx):
        for iy in range(ny):
            for horiz in (True, False):
                if (horiz and ix == nx - 1) or ((not horiz) and iy == ny - 1):
                    continue
                p = nid(ix, iy); q = nid(ix + 1, iy) if horiz else nid(ix, iy + 1)
                if horiz:
                    xm, ym = (xs[ix] + xs[ix + 1]) / 2, ys[iy]; lo, hi = trib(ys, iy); ins = gx0 - 1e-9 <= xm <= gx1 + 1e-9
                    glo, ghi = gy0, gy1
                    edge = "top" if abs(ym - gy0) < 1e-6 else "bottom" if abs(ym - gy1) < 1e-6 else None
                else:
                    xm, ym = xs[ix], (ys[iy] + ys[iy + 1]) / 2; lo, hi = trib(xs, ix); ins = gy0 - 1e-9 <= ym <= gy1 + 1e-9
                    glo, ghi = gx0, gx1
                    edge = "left" if abs(xm - gx0) < 1e-6 else "right" if abs(xm - gx1) < 1e-6 else None
                if tab:                                                    # GF-2.0: flange beyond fy1 only inside the tab
                    tx0, tx1, _ = tab
                    if horiz:
                        in_tab = xs[ix] >= tx0 - 1e-6 and xs[ix + 1] <= tx1 + 1e-6
                        if ys[iy] > fy1 + 1e-6 and not in_tab:
                            continue
                        if abs(ys[iy] - fy1) < 1e-6 and not in_tab:
                            hi = fy1
                    elif ys[iy + 1] > fy1 + 1e-6:
                        if not (tx0 - 1e-6 <= xs[ix] <= tx1 + 1e-6):
                            continue
                        lo, hi = max(lo, tx0), min(hi, tx1)
                bg = max(0.0, min(hi, ghi) - max(lo, glo)) if ins else 0.0
                bf = (hi - lo) - bg
                se = SECE[edge] if (ins and edge) else None
                EI_r = E_F * se["I"] if se else 0.0
                GJ = D_g * (1 - NU_G) * bg + D_fl * (1 - NU_F) * bf + (G_F * se["J"] if se else 0.0)
                if not horiz:                                              # GF-2.0: ribs along y (divider between the tails)
                    for rx, ry0, ry1, rEI, rGJ in ribs:
                        if abs(xm - rx) < 1e-6 and ry0 - 1e-6 <= ym <= ry1 + 1e-6:
                            EI_r += rEI; GJ += rGJ
                add_el(p, q, D_g * bg, EI_r + D_fl * bf, GJ, edge if se else None)
    for (cx, cy), (gxc, gyc) in zip(((fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1)), ((gx0, gy0), (gx1, gy0), (gx1, gy1), (gx0, gy1))):
        p = nid(xs.index(cx), ys.index(cy)); q = nid(xs.index(gxc), ys.index(gyc))
        add_el(min(p, q), max(p, q), 0.0, E_F * I_LINK, G_F * 60.0, None)
    sup = []
    for (sx, sy) in supports:
        ix = min(range(nx), key=lambda i: abs(xs[i] - sx)); iy = min(range(ny), key=lambda i: abs(ys[i] - sy))
        p = nid(ix, iy); sup.append(p); K[3 * p, 3 * p] += 2.0e4
    band = {}
    for ix in range(nx):
        for iy in range(ny):
            x, y = xs[ix], ys[iy]; lx = trib(xs, ix); ly = trib(ys, iy); w0 = w1 = 0.0
            if abs(y - fy0) < 1e-6 or abs(y - fy1) < 1e-6:
                w1 += SH1 * (lx[1] - lx[0])
            if abs(x - fx0) < 1e-6 or abs(x - fx1) < 1e-6:
                w1 += SH1 * (ly[1] - ly[0])
            if (abs(y - gy0) < 1e-6 or abs(y - gy1) < 1e-6) and gx0 - 1e-6 <= x <= gx1 + 1e-6:
                w0 += SH0 * (min(lx[1], gx1) - max(lx[0], gx0))
            if (abs(x - gx0) < 1e-6 or abs(x - gx1) < 1e-6) and gy0 - 1e-6 <= y <= gy1 + 1e-6:
                w0 += SH0 * (min(ly[1], gy1) - max(ly[0], gy0))
            if w0 + w1 > 0:
                band[nid(ix, iy)] = w0 + w1
    if vhb:
        for p, a in band.items():
            K[3 * p, 3 * p] += E_vhb / t_gap * a
    rhs, lp = [], []
    for (lx_, ly_) in loads:
        ix = min(range(nx), key=lambda i: abs(xs[i] - lx_)); iy = min(range(ny), key=lambda i: abs(ys[i] - ly_))
        f = np.zeros(n); f[3 * nid(ix, iy)] = 1.0; rhs.append(f); lp.append(nid(ix, iy))
    if line_q:
        f = np.zeros(n)
        for p, a in band.items():
            f[3 * p] = line_q / tape_w * a
        rhs.append(f); lp.append(None)
    dz = np.nonzero(np.abs(np.diag(K)) < 1e-12)[0]                     # unconnected nodes outside a tab
    K[dz, dz] = 1.0
    U = np.linalg.solve(K, np.array(rhs).T).T
    perim = [nid(ix, iy) for ix in range(nx) for iy in range(ny)
             if ((abs(ys[iy] - gy0) < 1e-6 or abs(ys[iy] - gy1) < 1e-6) and gx0 - 1e-6 <= xs[ix] <= gx1 + 1e-6)
             or ((abs(xs[ix] - gx0) < 1e-6 or abs(xs[ix] - gx1) < 1e-6) and gy0 - 1e-6 <= ys[iy] <= gy1 + 1e-6)]
    perim_bot = [nid(ix, ys.index(gy1)) for ix in range(nx) if gx0 - 1e-6 <= xs[ix] <= gx1 + 1e-6]
    res = []
    for p_l, u in zip(lp, U):
        Mg = 0.0; sr = 0.0
        for dofs, kl, T, EIg, EIr, edge in elems:
            fl_ = kl @ (T @ u[dofs])
            Mx = max(abs(fl_[1]), abs(fl_[4])); tot = EIg + EIr
            if EIg > 0:
                Mg = max(Mg, Mx * D_g / tot)
            if edge:
                se = SECE[edge]
                sr = max(sr, Mx * (E_F * se["I"]) / tot * se["c"] / se["I"])
        res.append(dict(w=u[3 * p_l] if p_l is not None else None, w_perim=max(u[3 * p] for p in perim), w_bottom=max(u[3 * p] for p in perim_bot),
                        sig_g=6 * Mg / t_g ** 2, sig_r=sr, R=max(2.0e4 * u[3 * p] for p in sup)))
    return res


# ------------------------------------------------------------------------------------------- 5.0 validation vs GF-1.1
out("\n5.0 validation of the port against concept_calc_out.txt (GF-1.0/1.1 geometry, one ring section, land_min 6.11)")
GL11 = (RECT["glass"]["x0"], RECT["glass"]["x1"], RECT["glass"]["y0"], RECT["glass"]["y1"])
FL11 = tuple(RECT["fastener_line"][k] for k in ("x0", "x1", "y0", "y1"))
gc11 = ((GL11[0] + GL11[1]) / 2, (GL11[2] + GL11[3]) / 2)
wc = ((W[0] + W[1]) / 2, (W[2] + W[3]) / 2)
logo11 = (W[3] + GL11[3]) / 2
SEC11 = section_props(ring_rects(L3, 6.11))
out("  ring section GF-1.1 (glass 3.0): I %.0f mm4, J %.0f, centroid %.2f (concept: I 1222, J 216, -8.82)" % (SEC11["I"], SEC11["J"], SEC11["zc"]))
LOADS11 = [("window centre", wc), ("glass top edge, mid", (gc11[0], GL11[2])), ("glass side edge, mid", (GL11[0], gc11[1])),
           ("chin centre (over tail pocket)", (gc11[0], logo11)), ("glass bottom edge, mid", (gc11[0], GL11[3]))]
FA11 = {f["name"]: (f["x_abs"], f["y_abs_down"]) for f in M["fasteners"]["positions"]}
S4_11 = [FA11[k] for k in ("F1", "F2", "F3", "F4")]
S8_11 = [FA11[k] for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8")]
REF11 = {"S4": [0.139, 0.067, 0.066, 0.092, 0.067], "S8": [0.193, 0.127, 0.113, 0.153, 0.127], "studs": [0.436, 0.581, 0.391, 0.478, 0.581]}
VAL = {}
for lab, kw in (("S4", dict(supports=S4_11, vhb=True)), ("S8", dict(supports=S8_11)), ("studs", dict(supports=S4_11))):
    r = grillage(GL11, FL11, {e: SEC11 for e in ("top", "bottom", "left", "right")}, 3.0, loads=[p for _, p in LOADS11],
                 extra_ys=(wc[1], gc11[1], logo11, PANEL[3]), **kw)
    VAL[lab] = r
    out("  %-6s w@50N: %s | concept: %s | glass@250N %s MPa" % (lab, " ".join("%.3f" % (x["w"] * 50) for x in r), " ".join("%.3f" % v for v in REF11[lab]),
                                                               " ".join("%.1f" % (x["sig_g"] * 250) for x in r)))
    for x, v in zip(r, REF11[lab]):
        assert abs(x["w"] * 50 - v) < 0.0015, (lab, x["w"] * 50, v)
out("  -> port reproduces the concept within 0.001 mm at every load point (asserted)")
LIFT11 = grillage(GL11, FL11, {e: SEC11 for e in ("top", "bottom", "left", "right")}, 3.0, supports=S8_11, line_q=0.10,
                  extra_ys=(wc[1], gc11[1], logo11, PANEL[3]))[0]["w_perim"]
out("  S8 gasket 0.10 N/mm lift, GF-1.1: %.0f um (concept 39)" % (LIFT11 * 1000))

# ------------------------------------------------------------------------------------------- 5.1 GF-2.0 ring sections
out("\n5.1 GF-2.0 ring sections (glass 3.0) [C]")
LANDS_REC = P["lands"]
land_side = min(LANDS_REC["abs left (front-view right)"], LANDS_REC["abs right (front-view left)"])
land_top = LANDS_REC["top"]
land_bot = LANDS_REC["bottom over the tail span (to the bridge pocket face)"]
beam_s = (BEAM_IN - GL[3], BEAM_OUT - GL[3])


def secs_gf2(Zl, bottom="channel", Pp=P):
    GLp = Pp["GL"]
    lands = Pp["lands"]
    lb = lands["bottom over the tail span (to the bridge pocket face)"]
    bs = (BEAM_IN - GLp[3], BEAM_OUT - GLp[3])
    S = {"top": section_props(ring_rects(Zl, lands["top"])),
         "left": section_props(ring_rects(Zl, lands["abs left (front-view right)"])),
         "right": section_props(ring_rects(Zl, lands["abs right (front-view left)"]))}
    if bottom == "channel":
        S["bottom"] = section_props(ring_rects(Zl, lb, kind="bridge", beam=bs))
    elif bottom == "bridge":
        S["bottom"] = section_props(ring_rects(Zl, lb, kind="bridge"))
    else:
        S["bottom"] = section_props(ring_rects(Zl, 6.11))
    return S


for tg in TG_LIST:
    Zl = LV(tg)
    Sc, Sb = secs_gf2(Zl, "channel"), secs_gf2(Zl, "bridge")
    out("  glass %.1f: I top %.0f / left %.0f / right %.0f; bottom: bridge only %.0f (no pocket wall, no shelf: the bend gap cuts them), "
        "bridge + flange plate + bottom wall (channel) %.0f; GF-1.1 ring %.0f; J bottom %.0f / %.0f"
        % (tg, Sc["top"]["I"], Sc["left"]["I"], Sc["right"]["I"], Sb["bottom"]["I"], Sc["bottom"]["I"], section_props(ring_rects(Zl, 6.11))["I"],
           Sb["bottom"]["J"], Sc["bottom"]["J"]))

# ------------------------------------------------------------------------------------------- 5.2 GF-2.0 push cases
out("\n5.2 GF-2.0 push cases (border %.1f)" % B_REC)
FA2 = {f["name"]: (f["x_abs"], f["y_abs_down"]) for f in FROWS}
Y_GAPMID = (PANEL[3] + Y_PF) / 2
LOADS2 = [("window centre", wc), ("glass top edge, mid", (gc[0], GL[2])), ("glass side edge, mid", (GL[0], gc[1])),
          ("bottom border over the bend gap", (gc[0], Y_GAPMID)), ("glass bottom edge, mid", (gc[0], GL[3])),
          ("bottom edge over CTP tail (x 58)", (58.0, GL[3]))]
XY = (wc[1], gc[1], Y_GAPMID, PANEL[3])
S7 = [FA2[k] for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F8")]
F7AB = ((TP11[0] - pad_d / 2 - 1.5, P["FL"][3]), (TP11[1] + pad_d / 2 + 1.5, P["FL"][3]))
TAB = (F7TAB[0] - pad_d / 2 - 1.0, F7TAB[0] + pad_d / 2 + 1.0, F7TAB[1])
X_RIB = (TAILS["CTP"]["x_exit"][1] + TAILS["TFT"]["x_exit"][0]) / 2          # divider rib between the tails
RIB_T = 2.5
F7R = (X_RIB, F7TAB[1])                                                          # S8: F7 on a tab, at the rib
TABR = (X_RIB - pad_d / 2 - 1.0, X_RIB + pad_d / 2 + 1.0, F7TAB[1])


def rib_def(Zl):
    """divider rib x X_RIB, 2.5 thick, from the flange back to Z 0, with 6 mm of flange plate each side (T-section);
    runs from the glass bottom edge line over the tail pocket and the bottom wall to the F7 tube on the tab"""
    zfb = Zl["Z_STEPWALL_BACK"] if abs(Zl["Z_LANDPLATE_BACK"] - Zl["Z_FLANGE_BACK"]) < 0.5 else Zl["Z_FLANGE_BACK"]
    sp = section_props([(-RIB_T / 2, RIB_T / 2, zfb, 0.0), (-RIB_T / 2 - 6.0, RIB_T / 2 + 6.0, Zl["Z_FLANGE_FRONT"], zfb)])
    return [(X_RIB, GL[3], F7R[1], E_F * sp["I"], G_F * sp["J"])], sp


out("  divider rib option: x %.2f (%.1f thick; %.2f to the CTP tail edge %.2f and %.2f to the TFT tail edge %.2f), T-section I %.0f mm4 (glass 3.0);"
    " F7 moved to a tab below the bottom wall at (%.2f, %.2f)" % (X_RIB, RIB_T, X_RIB - RIB_T / 2 - TAILS["CTP"]["x_exit"][1], TAILS["CTP"]["x_exit"][1],
                                                                 TAILS["TFT"]["x_exit"][0] - X_RIB - RIB_T / 2, TAILS["TFT"]["x_exit"][0], rib_def(LV(3.0))[1]["I"], F7R[0], F7R[1]))
S8_ALL = [FA2[k] for k in ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8")]
CONF2 = [("S4/R4: 4 corner studs + VHB", lambda tg: dict(supports=[FA2[k] for k in ("F1", "F2", "F3", "F4")], vhb=True)),
         ("S4/R4 + divider rib", lambda tg: dict(supports=[FA2[k] for k in ("F1", "F2", "F3", "F4")], vhb=True, tab=TABR, ribs=rib_def(LV(tg))[0],
                                                 extra_xs=[X_RIB], extra_ys=XY + (BEAM_OUT,))),
         ("S8 with F7 dropped (7 studs)", lambda tg: dict(supports=S7)),
         ("S8 with F7 on a tab below the bottom wall", lambda tg: dict(supports=S7 + [F7TAB], tab=TAB)),
         ("S8 with F7a/F7b beside the tail pocket", lambda tg: dict(supports=S7 + list(F7AB), extra_xs=[p[0] for p in F7AB])),
         ("S8: divider rib + F7 on a tab at the rib", lambda tg: dict(supports=S7 + [F7R], tab=TABR, ribs=rib_def(LV(tg))[0], extra_xs=[X_RIB],
                                                                       extra_ys=XY + (BEAM_OUT,))),
         ("S8 with F7 on the fastener line (bound, not buildable)", lambda tg: dict(supports=S8_ALL)),
         ("reference: 4 corner studs only", lambda tg: dict(supports=[FA2[k] for k in ("F1", "F2", "F3", "F4")]))]
MAIN_CONF = ("S4/R4: 4 corner studs + VHB", "S8 with F7 dropped (7 studs)", "S8: divider rib + F7 on a tab at the rib")


def gargs(kwf, tg):
    a = dict(extra_ys=XY)
    a.update(kwf(tg))
    return a
for lab, (x, y) in (("F7a", F7AB[0]), ("F7b", F7AB[1])):
    hn, hd = min(((h, math.hypot(x - hx, y - hy)) for h, (hx, hy) in HOLES.items()), key=lambda t: t[1])
    out("  %s option at (%.2f, %.2f): board outline %.2f, %s %.2f, tail pocket %.2f, %.1f from %s; sits in the corner cell (cross rib y 139, cell walls -> rework)"
        % (lab, x, y, poly_d((x, y), OUTLINE), hn, hd, rect_d((x, y), TAILPOCKET), min(math.hypot(x - FA2[k][0], y - FA2[k][1]) for k in ("F3", "F4")), "F3/F4"))
out("  F7 tab option: tab x %.2f-%.2f down to y %.2f, stud at (%.2f, %.2f)" % (TAB[0], TAB[1], TAB[2] + 10, F7TAB[0], F7TAB[1]))
PUSH2 = {}
for bottom in ("channel", "bridge"):
    for tg in TG_LIST:
        S = secs_gf2(LV(tg), bottom)
        for name, kwf in CONF2:
            if name not in MAIN_CONF and tg != 3.0:
                continue
            if bottom == "bridge" and tg not in (3.0, 1.1):
                continue
            r = grillage(GL, P["FL"], S, tg, loads=[p for _, p in LOADS2], **gargs(kwf, tg))
            PUSH2[(bottom, tg, name)] = r
            out("\n  glass %.1f | bottom section: %-7s | %s" % (tg, bottom, name))
            out("    %-34s %8s %7s %12s %11s %10s %10s" % ("load point", "w@5N um", "w@50N", "lip line@50N", "glass@250N", "ring@250N", "stud@250N"))
            for (ln, _), rr in zip(LOADS2, r):
                out("    %-34s %8.0f %7.3f %12.3f %7.1f MPa %6.1f MPa %7.0f N" % (ln, rr["w"] * 5000, rr["w"] * 50, rr["w_perim"] * 50, rr["sig_g"] * 250, rr["sig_r"] * 250, rr["R"] * 250))
# GF-1.1 comparison table for the bottom edge
out("\n  bottom edge mid at 50 N, glass 3.0 [C]: GF-1.1 S4 %.3f / S8 %.3f / studs only %.3f (concept)" % (0.067, 0.127, 0.581))
for bottom in ("channel", "bridge"):
    for name, _ in CONF2:
        k = (bottom, 3.0, name)
        if k in PUSH2:
            rr = PUSH2[k][4]
            out("  GF-2.0 %-8s %-55s %.3f mm, glass %.0f MPa at 250 N (SF %.1f on 120)" % (bottom, name, rr["w"] * 50, rr["sig_g"] * 250, 120 / max(rr["sig_g"] * 250, 1e-9)))
# S8 gasket lift
out("\n  S8 foam gasket preload: lift of the lip line between studs (glass 3.0 / 1.1) [C]")
LIFT2 = {}
for tg in (3.0, 1.1):
    S = secs_gf2(LV(tg), "channel")
    for lab, cname in (("7 studs (F7 dropped)", "S8 with F7 dropped (7 studs)"),
                       ("8 studs, F7 on a tab", "S8 with F7 on a tab below the bottom wall"),
                       ("9 studs, F7a/F7b beside the pocket", "S8 with F7a/F7b beside the tail pocket"),
                       ("8 studs, divider rib + F7 at the rib", "S8: divider rib + F7 on a tab at the rib"),
                       ("8 studs (F7 on the line, bound)", "S8 with F7 on the fastener line (bound, not buildable)")):
        kwf = dict(CONF2)[cname]
        for q in (0.10, 0.36):
            rr = grillage(GL, P["FL"], S, tg, line_q=q, **gargs(kwf, tg))[0]
            LIFT2[(tg, lab, q)] = (rr["w_perim"], rr["w_bottom"])
            out("    glass %.1f %-32s q %.2f N/mm: max %4.0f um, bottom edge %4.0f um (GF-1.1 8 studs: %s um)"
                % (tg, lab, q, rr["w_perim"] * 1000, rr["w_bottom"] * 1000, {(3.0, 0.10): 39, (3.0, 0.36): 141, (1.1, 0.10): 73, (1.1, 0.36): 263}[(tg, q)]))

# =====================================================================================================================
# 6. GLASS STRENGTH / IMPACT, THERMAL, JOINTS
# =====================================================================================================================
hdr("6. GLASS STRENGTH AND IMPACT (port of concept sec. 8), THERMAL GAPS, JOINTS")
m_panel = 200.0


def sig_point(Pn, t, r0, a):
    rp = math.sqrt(1.6 * r0 ** 2 + t ** 2) - 0.675 * t if r0 < 0.5 * t else r0
    return 3 * Pn / (2 * math.pi * t ** 2) * ((1 + NU_G) * math.log(a / rp) + 1)


def impact(k, m_move, t, a):
    E_def = 0.5 * m_move / (0.25 + m_move)
    res = {}
    for lab, E in (("bound", 0.5), ("mass", E_def)):
        F = math.sqrt(2 * E * k * 1000)
        ah = (3 * F * 10 / (4 * 3400)) ** (1 / 3)
        res[lab] = (F, sig_point(F, t, ah, a), E)
    return res


a_disp = 0.5 * min(POCKET[1] - POCKET[0], POCKET[3] - POCKET[2])
b_free = (GL[3] - bead_edge - bead_w) - PANEL[3]           # panel edge -> bead inner edge: glass with nothing bonded behind
IMP = {}
for tg in TG_LIST:
    gname = GLASS_TYPES[tg]["type"]; lim = GLASS_TYPES[tg]["char_strength_MPa"]
    D_g = E_G * tg ** 3 / (12 * (1 - NU_G ** 2))
    mg = (P["gW"] * P["gH"] - (4 - math.pi) * R_glass ** 2) * tg * RHO_G
    mm = 0.25 * (mg + m_panel) / 1000
    rc = PUSH2[("channel", tg, CONF2[0][0])]
    imp_c = impact(1 / rc[0]["w"], mm, tg, a_disp)
    k_glob = 1 / rc[3]["w"]
    k_loc = D_g / (0.0169 * b_free ** 2)
    k_ser = 1 / (1 / k_glob + 1 / k_loc)
    imp_b = impact(k_ser, mm, tg, 0.6 * B_REC)                # conservative: the whole border as free radius (no LOCA credit)
    imp_s = impact(k_ser, mm, tg, 0.6 * b_free)               # the free strip over the bend gap only (concept's chin method)
    s250 = sig_point(250, tg, 5.0, a_disp)
    IMP[tg] = dict(sf_c=lim / imp_c["mass"][1], sf_b=lim / imp_b["mass"][1], sf_s=lim / imp_s["mass"][1], s250=s250, k_loc=k_loc, k_glob=k_glob, mg=mg)
    out("  %.1f %-34s (char. %.0f): glass %.0f g; 250 N centre %.1f MPa (no panel credit); 0.5 J window centre mass-ratio %.1f MPa SF %.2f"
        " (GF-1.1 %.2f); bottom border: free strip %.2f over the bend gap, k local %.0f / global %.0f N/mm, 0.5 J %.1f MPa SF %.2f with the whole"
        " border as free radius, %.1f MPa SF %.2f with the strip only (GF-1.1 chin SF %.2f)"
        % (tg, gname[:34], lim, mg, s250, imp_c["mass"][1], lim / imp_c["mass"][1], M["checks"]["impact_0p5J_SF_centre"][str(tg)], b_free, k_loc, k_glob,
           imp_b["mass"][1], lim / imp_b["mass"][1], imp_s["mass"][1], lim / imp_s["mass"][1], M["checks"]["impact_0p5J_SF_chin"][str(tg)]))
out("  the GF-1.1 'chin over the tail pocket' case (128.8 x 28.7 of glass with nothing behind) is gone: the only glass with nothing bonded"
    " behind it is the %.2f-wide strip over the bend gap (panel edge -> bead inner edge), locally ~%.0f x stiffer than the chin span."
    % (b_free, (28.7 / b_free) ** 2))

# thermal gaps (port of concept sec. 5)
out("\n  gaps over temperature, nominal per side (frame expands about the glass centre) [C]:")
TH = {}
for an, af in ALPHA_F.items():
    for tn, (dtf, dts) in {"-20 C": (-40, -40), "+70 frame / +50 sheet": (50, 30)}.items():
        vals = []
        for gw_, gh_ in ((P["gW"], P["gH"]), (GL11[1] - GL11[0], GL11[3] - GL11[2])):
            d2 = min((af - ALPHA_G) * dtf * h for h in (gw_ / 2, gh_ / 2))
            d1 = min(-(af * dtf - ALPHA_S * dts) * h for h in (gw_ / 2 + g2 + lip_w, gh_ / 2 + g2 + lip_w))
            vals.append((g2 + d2, g1 + d1))
        TH[(an, tn)] = vals[0]
        TH[("GF-1.1", an, tn)] = vals[1]
        out("    frame %-9s %-22s: g2 %.3f | g1 %.3f   (same formula for GF-1.1: g2 %.3f | g1 %.3f; change %+.3f / %+.3f)"
            % (an, tn, vals[0][0], vals[0][1], vals[1][0], vals[1][1], vals[0][0] - vals[1][0], vals[0][1] - vals[1][1]))
out("  -> the glass is 9.0 wider (half-width 95.24 vs 90.74): the x-direction gaps breathe 5 %% more; with the design-doc worst cases (g2 -0.027 cold with +-0.2 glass, g1 -0.018 hot,"
    " 70 ppm) shifted by the changes above: g2 about %.3f, g1 about %.3f (touch, harmless, same nature as GF-1.1)"
    % (-0.027 + TH[("bound 70", "-20 C")][0] - TH[("GF-1.1", "bound 70", "-20 C")][0],
       -0.018 + TH[("bound 70", "+70 frame / +50 sheet")][1] - TH[("GF-1.1", "bound 70", "+70 frame / +50 sheet")][1]))
r_bead = math.hypot((P["gW"] - 2 * 2.9) / 2, (P["gH"] - 2 * 2.9) / 2)
r_tape = math.hypot(P["gW"] / 2 + s_tape1, P["gH"] / 2 + s_tape1)
out("  bead corner radius from the centre %.1f (GF-1.1 111.7) -> thermal shear %.3f / %.3f mm at 50 / 70 ppm, +70 C (GF-1.1 0.229 / 0.341)"
    % (r_bead, (50e-6 - ALPHA_G) * 50 * r_bead, (70e-6 - ALPHA_G) * 50 * r_bead))
out("  tape outer corner %.1f (GF-1.1 138.1) -> %.3f / %.3f mm (%.0f / %.0f %% of the 1.0 gap)" % (
    r_tape, (50e-6 * 50 - ALPHA_S * 30) * r_tape, (70e-6 * 50 - ALPHA_S * 30) * r_tape, (50e-6 * 50 - ALPHA_S * 30) * r_tape * 100, (70e-6 * 50 - ALPHA_S * 30) * r_tape * 100))
rmax = max(f["r_from_glass_centre"] for f in FROWS if f["name"] != "F7")
out("  stud radial move at r %.1f: %.3f / %.3f mm (50 / 70 ppm) vs 1.15 float along the slot" % (rmax, (50e-6 - ALPHA_S) * 50 * rmax, (70e-6 - ALPHA_S) * 50 * rmax))
A_bead_c = 2 * ((P["gW"] - 5.8) + (P["gH"] - 5.8)) * bead_w
A_bead = A_bead_c * 2486.7 / 2510.0
mg3 = IMP[3.0]["mg"]
out("  bead area (concept formula) %.0f -> scaled to the GF-1.1 modelled shape %.0f mm2 (GF-1.1 2486.7, %+.1f %%); dead load glass 3.0 + panel %.2f N -> %.2f kPa;"
    " 250 N pull %.3f MPa mean (GF-1.1 0.100)" % (A_bead_c, A_bead, (A_bead / 2486.7 - 1) * 100, (mg3 + m_panel) * 9.81e-3, (mg3 + m_panel) * 9.81e-3 / A_bead * 1e3, 250 / A_bead))
out("  glass mass 3.0: %.0f g (GF-1.1 196 g)" % mg3)

# =====================================================================================================================
# 7. PROPOSED GF-2.0 PARAMETERS + FIGURES
# =====================================================================================================================
hdr("7. PROPOSED GF-2.0 NUMBERS (concept_gf2_params.json) AND FIGURES")
Z3 = LV(3.0)
tab = []


def row(name, old, new, reason, kind="changed"):
    tab.append({"name": name, "GF-1.1": old, "GF-2.0": r4(new) if not isinstance(new, (list, tuple, dict)) else new, "reason": reason, "kind": kind})


rr4 = lambda t: [r4(v) for v in t]
row("border", 14.0, B_REC, "equal on all four sides (owner); smallest 0.5 step that keeps the full GF-1.1 bead and margins at the bottom (sec. 3)")
row("glass_y1", 154.0, GL[3], "derived now: print_window y1 + border (no chin)", "changed (derived)")
row("plan_rectangles.glass", [13.11, 194.59, 10.17, 154.0], rr4(GL), "%.2f x %.2f, R6.25 unchanged" % (P["gW"], P["gH"]))
for k, nm in (("lip_in", "lip_in"), ("lip_out", "lip_out"), ("seat", "seat_ring_out"), ("cut", "cut"), ("tape_in", "tape_in"), ("tape_out", "tape_out"), ("FL", "fastener_line")):
    old = [RECT[nm][q] for q in ("x0", "x1", "y0", "y1")]
    row("plan_rectangles." + nm, old, rr4(P[k]), "same offset from the glass as GF-1.1")
row("plan_rectangles.flange", [-7.89, 215.59, -10.83, 175.0], rr4(P["FLANGE"]),
    "glass + 21 on top and sides; bottom edge = frame bottom wall outer face %.2f (glass + 21 = %.2f would cut the wall); R10 corners, bottom ones centred 10 inside the corner (not on F3/F4)" % (BEAM_OUT, GL[3] + 21))
row("flange_y1_bottom", None, P["FLANGE"][3], "NEW: flange bottom edge abs y = tail-pocket bottom face 147.70 + wall 2.5 (1 deg draft)", "new")
row("glass_centre (= cut-out = fastener-pattern centre)", [103.85, 82.085], rr4(gc), "equal borders: glass centre = window centre")
row("chin_border", 44.51, None, "removed (no chin)", "removed")
row("borders_top_left_right", 14.0, B_REC, "now all four sides")
row("lands (pocket face -> glass edge)", {"abs left": 6.11, "abs right": 8.87, "top": 8.03, "bottom": 6.30},
    {k.split(" (")[0] if "bottom" not in k else k: r4(v) for k, v in LANDS_REC.items()}, "the bead stays 0.9-4.9 inside the glass edge; the side/top land plates grow 4.5")
row("bead_to_pocket", {"abs left": 1.21, "abs right": 3.97, "top": 3.13, "bottom": 1.40},
    {k.split(" (")[0] if "bottom" not in k else k: r4(v - bead_edge - bead_w) for k, v in LANDS_REC.items()}, ">= 1.0 everywhere (bottom 1.09 is the governing one)")
row("g_bend", None, G_BEND, "NEW: bend gap panel bottom edge -> bridge pocket face over the tail span = straight 0.5 + R_in 1.5 + tail 0.3 + clearance 0.45 + panel position 0.25", "new")
row("bend_gap_y1 (bridge pocket face)", None, Y_PF, "NEW: abs y of the bridge inner face over x 38.9-167.7, from Z_LAND to the back (open slot y 119.0-%.2f)" % Y_PF, "new")
row("bend_nose_R", None, NOSE_R, "NEW: round on the bridge's back-inner edge (land plate back x pocket face) >= R_in, so a taut tail is never bent tighter", "new")
row("tail_R_in_min", None, R_IN, "NEW (assumption to confirm): minimum inner bend radius of both tails, static", "new")
row("tail_straight_l0", None, L0, "NEW (assumption to confirm): straight beyond the panel edge face before the first bend", "new")
row("Z_TAIL_LEG", None, "Z_TAIL_TFT_EXIT + 2 x (tail_R_in_min + 0.15) = %.2f at every glass_t" % Z_LEG, "NEW derived level: nominal front-leg centre of both tails (no frame feature at it)", "new")
row("Z_LOOP_FRONT", "Z_TAIL_CTP_EXIT - 0.15 (-9.85)", "Z_TAIL_CTP_EXIT - 0.15 (-9.85) at the exit only; front legs at Z_TAIL_LEG - 0.15 (%.2f)" % (Z_LEG - 0.15), "the CTP tail is this far forward only in the bend gap now")
row("tail_pocket", {"x": [38.9, 167.7], "y": [119.0, 147.7], "floor": "none (glass chin closes the front)"},
    {"x": [38.9, 167.7], "y": [119.0, 147.7], "floor": "bridge: land plate (y %.2f-%.2f), step wall, flange plate (y %.2f-147.7); open slot y 119.0-%.2f (bend gap, closed at the front by the glass)" % (Y_PF, GL[3] + 0.4, GL[3] + 2.9, Y_PF)},
    "x, bottom face 147.7 and trough_R 1.5 unchanged; the loops hang where they did")
row("bottom wall (beam)", "y 147.7-150.2, from the land (Z -10.42) to +4.05", "y 147.7-150.2, from Z_FLANGE_FRONT to Z_TROUGH_TOP = the frame's bottom outer wall, flush with the flange edge", "no glass land beyond the loops any more")
fx_new = {f["name"]: [f["x_abs"], f["y_abs_down"]] for f in FROWS}
row("fasteners F1-F6, F8", {f["name"]: [f["x_abs"], f["y_abs_down"]] for f in M["fasteners"]["positions"] if f["name"] != "F7"},
    {k: v for k, v in fx_new.items() if k != "F7"}, "glass corners / mid-sides + 11 as GF-1.1; F1-F4 symmetric about the glass (R4 heads visible)")
row("F7", [103.85, 165.0], "not at (%.2f, %.2f) any more: the tube would sit in the tail pocket over the TFT loop. S8 (if kept): F7 -> (%.2f, %.2f) on a"
    " flange tab x %.2f-%.2f to y %.2f, tied to the bridge by the divider rib; S4/R4: no F7" % (gc[0], P["FL"][3], F7R[0], F7R[1], TABR[0], TABR[1], TABR[2] + 10),
    "dropping F7 leaves 0.50 mm at 50 N and 164 um gasket lift at the bottom edge (S8); F7 alone on a tab at x 103.85: 0.41 / 133 um; rib + F7 at the rib: 0.20 / 70 um (sec. 5)")
row("divider_rib", None, {"x_centre": r4(X_RIB), "t": RIB_T, "y": [Y_PF, BEAM_IN], "Z": "floor (land-plate / flange back) -> Z_PCB for y < 129, -> Z_TROUGH_TOP for y >= 129",
                          "clearance_to_tails": r4(X_RIB - RIB_T / 2 - TAILS["CTP"]["x_exit"][1])},
    "NEW (recommended for all variants): the only place for a mid support (between the tails, 2.85 clear of each); ties the 128.8 bridge to the bottom wall"
    " in the middle (moulding flow / warp of the bridge's free inner edge), carries the S8 F7 tab; adds 0.005 mm stiffness for S4 - not needed for S4 strength", "new")
row("S8 variant", "8 studs F1-F8, foam gasket", "7 + F7' at the rib (8 studs) - NOT recommended at GF-2.0; S4 recommended, R4 alternative",
    "even with the rib the bottom edge moves 0.20 mm at 50 N (GF-1.1 S8 0.127, flushness limit 0.15) and the gasket lifts it 70 um (GF-1.1 39)")
row("pips", [list(p["value"]) for p in M["pips"] if p["name"].startswith("pip") and isinstance(p["value"], list)], [rr4(p) for p in PIPS], "same rule (bead centre line, +-1/4 of each side)")
row("logo_zone", {"centre": [103.85, 131.745], "w": 100, "h": 20}, {"centre": rr4(LOGO[:2]), "w": LOGO[2], "h": round(LOGO[3], 1)}, "bottom border, >= 1.0 from the window, >= 2.5 from the edge")
row("tape strip lengths", {"top_bottom": 183.48, "sides": 145.83}, {"top_bottom": r4(P["gW"] + 2), "sides": r4(P["gH"] + 2)}, "strips end 1.0 before the corner pads (same rule); area %.0f mm2" % A_tape)
row("bead_area", 2486.7, round(A_bead, 0), "estimate (concept formula scaled to the GF-1.1 modelled 2486.7); CAD to measure")
row("sheet cut_out", [11.31, 196.39, 8.37, 155.8], rr4(P["cut"]), "%.2f x %.2f, R7.55 unchanged" % (P["cut"][1] - P["cut"][0], P["cut"][3] - P["cut"][2]))
unchanged = ["glass_t and the valid set 1.1/2.0/3.0/4.0", "t_opt, t_bond, t_sheet, t_gap, g_bs", "print_inset and the print window", "R_glass 6.25, R_frame 6.0, R_cut 7.55",
             "g1, g2, lip_w, seat_ring_w", "pocket_clr 0.8 (outside the tail span)", "bead_w 4.0, bead_edge 0.9, bead_pocket_min 1.0", "fast_off 11, flange_beyond_glass 21 (top/sides), flange_R 10, flange_t 2.5",
             "slot, counterbore, pad, tube, coring, pip size", "all Z levels (derived_levels.expressions)", "tail_pocket x 38.9/167.7, bottom face 147.7, trough_R 1.5",
             "everything at Z >= Z_FORMEX_FRONT (Formex, shelf, ribs, bosses H1-H9, mains creepage)"]
INVALID = ["plan_points.chin_border, logo_zone (100 x 20 at y 131.745)", "lands, bead_area 2486.7, tape area 7903 / strip lengths, pips", "fasteners.positions (all d_* values; F7)",
           "checks.push_50N_*, impact_0p5J_SF_chin (case gone), impact_0p5J_SF_centre (glass mass changes)", "gaps over temperature (design doc 7.4 tables)",
           "as_modelled_GF-1.1 volume / mass / max inscribed sphere; the 84-pass verification; GF-D01..D50 drawings",
           "cad_rules[8] 'Tail pocket ... no floor (the glass chin closes the front)'; 'F5-F8 tube + slot always moulded' (F7 gone)",
           "tail checks: 1.83 / 1.763 to the pocket, 'tails vs glass print 1.565 / 2.865', TAIL_SPLIT_Z split model (tails are re-routed)",
           "J2 pin positions (F1-F4) and glass stops; the J1 glass stops", "sheet_variants cut_out and fastener table (front view u, v)", "design doc 2.2 (chin) and 7.8 chin rows"]
params = {
    "about": "Rev3.0 glass front GF-2.0 concept PROPOSAL (equal borders, FPC tails bent back). Changed and new values only; "
             "the CAD agent writes the master. Generated by concept_gf2_calc.py; study in concept_gf2.md.",
    "base_revision": M["revision"],
    "proposed_revision": "GF-2.0",
    "status": "concept, not frozen until the lead accepts it and the real-panel check (concept_gf2.md sec. 9) passes",
    "recommended_border": B_REC,
    "alternative_border_narrow_bottom_bead": {"border": 17.5, "bottom_bead_w": 3.0, "note": "sec. 3; only if the owner wants 1 mm less border"},
    "table": tab,
    "unchanged": unchanged,
    "gf11_values_invalidated": INVALID,
    "border_options": BTAB,
    "tail_route": {n: dict(L=T["L"], Z_exit=T["Z_e"], x_exit=T["x_exit"], straight=L0, R_inner=R_IN, R_centre=RC, theta_deg=r4(ROUTE[n]["theta_deg"]),
                           vertical=r4(ROUTE[n]["vert"]), Z_leg=Z_LEG, U_R=r4(ROUTE[n]["r"]), loop_bottom_outer=r4(ROUTE[n]["y_bot"] + T["t"] / 2),
                           S_end_y=r4(ROUTE[n]["y_s"]), clearance_to_bridge_nominal=r4(CLR[(n, 3.0, "frame bridge")]),
                           y_end=r4(T["y_end"]), Z_return=r4(T["Z_ret"]), thickness=T["t"],
                           centreline_yZ_note="nominal centre line (abs y, Z), glass-independent; sweep it over the tail outline in x for a fit check",
                           centreline_yZ=[[r4(a), r4(b)] for a, b in ROUTE[n]["pts"][::2]])
                   for n, T in TAILS.items()},
    "fasteners_gf2": FROWS,
    "F7_S8_at_rib": {"xy": rr4(F7R), "flange_tab": [r4(TABR[0]), r4(TABR[1]), r4(P["FLANGE"][3]), r4(TABR[2] + 10)], "tab_corner_R": 10.0},
    "push_50N_mm_glass_3.0_channel": {name: {ln: r4(rr["w"] * 50) for (ln, _), rr in zip(LOADS2, PUSH2[("channel", 3.0, name)])} for name, _ in CONF2},
    "glass_250N_MPa_glass_3.0_channel": {name: {ln: r4(rr["sig_g"] * 250) for (ln, _), rr in zip(LOADS2, PUSH2[("channel", 3.0, name)])} for name, _ in CONF2},
    "S8_gasket_lift_um": {"%s %s q%.2f" % (tg, lab, q): [round(v[0] * 1000), round(v[1] * 1000)] for (tg, lab, q), v in LIFT2.items()},
    "impact_SF_0p5J": {str(tg): {"window_centre": r4(IMP[tg]["sf_c"]), "bottom_border_whole_border_free": r4(IMP[tg]["sf_b"]),
                                 "bottom_border_strip_only": r4(IMP[tg]["sf_s"])} for tg in TG_LIST},
}
json.dump(params, open(OUT_PAR, "w"), indent=1)
out("  wrote %s (%d rows)" % (os.path.basename(OUT_PAR), len(tab)))
for t_ in tab:
    out("  %-44s %-40s -> %s" % (t_["name"][:44], json.dumps(t_["GF-1.1"])[:40], json.dumps(t_["GF-2.0"])[:110]))

# ------------------------------------------------------------------------------------------------ figures
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle

COL = dict(frame="#8c8c8c", glass="#9ecae1", panel="#fdae6b", pcb="#74c476", formex="#bcbddc", bead="#cb181d", tape="#fd8d3c", sheet="#525252",
           tft="#d95f02", ctp="#7570b3", old="#999999")


def draw_section(ax, tg=3.0, zoom=False):
    fr = frame_bottom_polygon(tg, GL[3])
    ax.add_patch(MPoly(fr, closed=True, fc=COL["frame"], ec="k", lw=0.6, label="frame GF-2.0 (bridge, flange plate, bottom wall)"))
    oth = others_polygons(tg, GL[3])
    Zl = LV(tg)
    ax.add_patch(MPoly(oth["glass"], closed=True, fc=COL["glass"], ec="k", lw=0.5, label="glass %.1f (printed back)" % tg))
    ax.add_patch(MPoly(oth["panel (CTP+LCM)"], closed=True, fc=COL["panel"], ec="k", lw=0.5, label="panel (CTP + LCM)"))
    ax.add_patch(Rectangle((100, Zl["Z_GLASS_BACK"]), PANEL[3] - 100, t_opt, fc="#c6dbef", ec="none"))
    ax.add_patch(MPoly(oth["Formex"], closed=True, fc=COL["formex"], ec="k", lw=0.4, label="Formex"))
    shelf = MEA["frame_sections_x"]["103.85"]
    for l in shelf:
        a = np.array(l)
        if a[:, 0].max() < 121 and a[:, 1].min() > -6:
            ax.add_patch(MPoly(a, closed=True, fc=COL["frame"], ec="k", lw=0.4))
    ax.add_patch(MPoly(oth["PCB"], closed=True, fc=COL["pcb"], ec="k", lw=0.5, label="PCB"))
    ax.add_patch(Rectangle((GL[3] - bead_edge - bead_w, Zl["Z_GLASS_BACK"]), bead_w, t_bond, fc=COL["bead"], ec="none", label="bead 4.0 x 1.0"))
    ax.add_patch(Rectangle((P["cut"][3], Zl["Z_GLASS_FRONT"]), 40, 1.0, fc=COL["sheet"], ec="none", label="oven sheet 1.0"))
    ax.add_patch(Rectangle((GL[3] + s_tape0, Zl["Z_SHEET_BACK"]), tape_w, t_gap, fc=COL["tape"], ec="none", label="VHB (S4/R4)"))
    for n, c in (("TFT", COL["tft"]), ("CTP", COL["ctp"])):
        p_ = ROUTE[n]["pts"]
        ax.plot(p_[:, 0], p_[:, 1], color=c, lw=2.0 if not zoom else 3.0, solid_capstyle="butt", label="%s tail, GF-2.0 route (projected)" % n)
        o = old_route(TAILS[n])
        yy = [PANEL[3], o["y_c"]] + [o["y_c"] + o["r"] * math.sin(t) for t in np.linspace(0, math.pi, 40)] + [TAILS[n]["y_end"]]
        zz = [TAILS[n]["Z_e"], TAILS[n]["Z_e"]] + [TAILS[n]["Z_e"] + o["r"] - o["r"] * math.cos(t) for t in np.linspace(0, math.pi, 40)] + [TAILS[n]["Z_ret"]]
        ax.plot(yy, zz, color=c, lw=0.8, ls=":", label="%s tail, GF-1.1 route" % n if not zoom else None)
    ax.set_aspect("equal")
    ax.set_xlabel("y abs (mm, down)  ->  outward / down")
    ax.set_ylabel("Z (mm)   front = -Z")
    ax.grid(True, lw=0.3, alpha=0.5)


fig, ax = plt.subplots(figsize=(19.5, 8.5))
draw_section(ax)
ax.set_xlim(104, 158); ax.set_ylim(-16.5, 6.5)
Zl = LV(3.0)
ya = -15.6
for (y0, y1, lab) in ((W[3], PANEL[3], "bezel %.2f" % BEZEL), (PANEL[3], Y_PF, "bend gap %.2f" % G_BEND), (Y_PF, GL[3], "land %.2f" % (GL[3] - Y_PF))):
    ax.annotate("", xy=(y0, ya), xytext=(y1, ya), arrowprops=dict(arrowstyle="<->", lw=0.8))
    ax.text((y0 + y1) / 2, ya - 0.55, lab, ha="center", va="top", fontsize=8)
ax.annotate("", xy=(W[3], ya + 1.6), xytext=(GL[3], ya + 1.6), arrowprops=dict(arrowstyle="<->", lw=0.8, color="b"))
ax.text((W[3] + GL[3]) / 2, ya + 1.75, "border %.1f (same on all four sides)" % B_REC, ha="center", va="bottom", fontsize=8, color="b")
ax.axvline(W[3], color="b", lw=0.6, ls="--"); ax.text(W[3] - 0.2, 5.6, "print window edge y %.2f" % W[3], ha="right", fontsize=7, color="b")
ax.text(BEAM_IN - 0.3, 4.4, "tail-pocket bottom face 147.7", ha="right", fontsize=7)
ax.text(GL[3] + 11, -9.4, "tail-pocket floor = flange plate (back Z %.2f)" % Zl["Z_FLANGE_BACK"], fontsize=7, ha="center")
ax.text(126.5, -7.3, "nose R%.1f" % NOSE_R, fontsize=7)
ax.text(Y_PF + 0.3, -12.3, "bend-gap slot (closed by the glass)", fontsize=7, rotation=0)
for n in ("TFT", "CTP"):
    ax.text(ROUTE[n]["y_bot"] + 0.4, ROUTE[n]["Z_leg"] + ROUTE[n]["r"], "%s U R%.2f\nbottom %.2f" % (n, ROUTE[n]["r"], ROUTE[n]["y_bot"] + 0.15), fontsize=7)
ax.set_title("GF-2.0 bottom edge, section at x 103.85 (frame), glass 3.0, border %.1f; tail routes projected onto the y-Z plane "
             "(TFT x 84.0-122.6 at the exit, CTP x 40.7-75.8); dotted = GF-1.1 routes" % B_REC, fontsize=9)
ax.legend(loc="upper left", bbox_to_anchor=(1.005, 1.0), fontsize=7, ncol=1)
plt.tight_layout()
f1 = os.path.join(HERE, "concept_gf2_section_bottom.png")
plt.savefig(f1, dpi=140); plt.close()

fig, axs = plt.subplots(1, 2, figsize=(17, 7.5), gridspec_kw=dict(width_ratios=[1.25, 1]))
ax = axs[0]
draw_section(ax, zoom=True)
ax.set_xlim(116.5, 131.5); ax.set_ylim(-15, -3.5)
for n, c in (("TFT", COL["tft"]), ("CTP", COL["ctp"])):
    ax.plot([PANEL[3]], [TAILS[n]["Z_e"]], "o", color=c, ms=4)
    ax.text(PANEL[3] - 0.15, TAILS[n]["Z_e"], "%s exit Z %.2f [E]" % (n, TAILS[n]["Z_e"]), ha="right", va="center", fontsize=7, color=c)
ax.annotate("", xy=(PANEL[3], -11.9), xytext=(Y_PF, -11.9), arrowprops=dict(arrowstyle="<->", lw=0.8))
ax.text((PANEL[3] + Y_PF) / 2, -12.0, "g_bend %.2f = 0.5 + 1.5 + 0.3 + 0.45 + 0.25" % G_BEND, ha="center", va="top", fontsize=7)
ax.text(119.6, -6.1, "straight 0.5, R_in 1.5 (centre line 1.65),\n90 deg back, straight, 90 deg out:\nfront legs at Z %.2f" % Z_LEG, fontsize=7)
ax.text(124.0, -10.0, "land %.2f\nbead 0.9-4.9 inside the edge\nbead -> pocket face %.2f" % (GL[3] - Y_PF, GL[3] - Y_PF - 4.9), fontsize=7)
ax.set_title("bend-gap zoom (glass 3.0): nominal tail-to-bridge clearance TFT %.2f / CTP %.2f, worst case (panel +0.25) see calc" %
             (CLR[("TFT", 3.0, "frame bridge")], CLR[("CTP", 3.0, "frame bridge")]), fontsize=9)
ax = axs[1]
bs = [r["border"] for r in BTAB]
ax.bar(bs, [max(r["bead_bottom_max"], 0) for r in BTAB], width=0.35, color=["#cb181d" if r["bead_bottom_max"] < 2 else "#fdae6b" if r["bead_bottom_max"] < 3 else "#a1d99b" if r["bead_bottom_max"] < 4 else "#31a354" for r in BTAB])
for r in BTAB:
    ax.text(r["border"], max(r["bead_bottom_max"], 0) + 0.08, "%.2f" % r["bead_bottom_max"], ha="center", fontsize=8)
ax.axhline(4.0, color="k", lw=0.8, ls="--"); ax.text(14.0, 4.05, "GF-1.1 bead 4.0", fontsize=8)
ax.axhline(3.0, color="k", lw=0.5, ls=":"); ax.text(14.0, 3.05, "3.0: narrowest bead I call sound", fontsize=8)
ax.set_xlabel("equal border on all four sides (mm)"); ax.set_ylabel("widest bottom bead that fits (mm), margins 0.9 / 1.0")
ax.set_title("border budget: bezel %.2f + bend gap %.2f + land (bead + 1.9) = border" % (BEZEL, G_BEND), fontsize=9)
ax.set_ylim(-0.6, 4.8); ax.grid(True, lw=0.3, axis="y")
plt.tight_layout()
f2 = os.path.join(HERE, "concept_gf2_bend_zoom.png")
plt.savefig(f2, dpi=140); plt.close()

# plan of the bottom zone in KiCad abs (x right = seen from the back; the front view is mirrored)
fig, ax = plt.subplots(figsize=(17, 8.2))


def rr(r_, **kw):
    ax.add_patch(Rectangle((r_[0], r_[2]), r_[1] - r_[0], r_[3] - r_[2], fill=False, **kw))


rr(P["FLANGE"], ec="k", lw=1.0, label="flange outline")
rr(P["cut"], ec=COL["sheet"], lw=1.0, ls="--", label="sheet cut-out")
rr(GL, ec="#08519c", lw=1.2, label="glass")
rr(W, ec="b", lw=0.6, ls=":", label="print window")
rr(PANEL, ec="#e6550d", lw=0.8, label="panel outline")
ax.add_patch(Rectangle((TP11[0], PANEL[3]), TP11[1] - TP11[0], BEAM_IN - PANEL[3], fc="#f0f0f0", ec="k", lw=0.6, label="tail pocket (closed at the front by the bridge)"))
ax.add_patch(Rectangle((TP11[0], PANEL[3]), TP11[1] - TP11[0], G_BEND, fc="#fee0d2", ec="r", lw=0.6, label="bend-gap slot (open front-to-back, glass in front)"))
ax.add_patch(Rectangle((TP11[0] - 20, BEAM_IN), TP11[1] - TP11[0] + 40, BEAM_OUT - BEAM_IN, fc=COL["frame"], ec="k", lw=0.4, label="bottom wall (y 147.7-150.2)"))
ax.add_patch(Rectangle((GL[0] + bead_edge, GL[3] - bead_edge - bead_w), P["gW"] - 2 * bead_edge, bead_w, fc=COL["bead"], ec="none", alpha=0.7, label="bead (bottom side)"))
ax.add_patch(Rectangle((GL[0] - 1, GL[3] + s_tape0), P["gW"] + 2, tape_w, fc=COL["tape"], ec="none", alpha=0.4, label="VHB bottom strip"))
for n, c in (("TFT", COL["tft"]), ("CTP", COL["ctp"])):
    x0, x1 = TAILS[n]["x_exit"]
    ax.add_patch(Rectangle((x0, PANEL[3]), x1 - x0, ROUTE[n]["y_s"] - PANEL[3], fc=c, alpha=0.6, ec="none"))
    xe = TAILS[n]["x_env"]
    ax.add_patch(Rectangle((xe[0], ROUTE[n]["y_s"]), xe[1] - xe[0], ROUTE[n]["y_bot"] + 0.15 - ROUTE[n]["y_s"], fc=c, alpha=0.25, ec=c, lw=0.6, label="%s S-bend (dark) / front leg + loop" % n))
for f in FROWS:
    if not 95 <= f["y_abs_down"] <= 175:
        continue
    col = "r" if f["name"] == "F7" else "k"
    ax.add_patch(plt.Circle((f["x_abs"], f["y_abs_down"]), 9, fill=False, ec=col, lw=0.8, ls="-" if f["name"] != "F7" else "--"))
    ax.text(f["x_abs"], f["y_abs_down"], f["name"] + (" (no room)" if f["name"] == "F7" else ""), ha="center", va="center", fontsize=8, color=col)
ax.add_patch(Rectangle((TABR[0], P["FLANGE"][3]), TABR[1] - TABR[0], TABR[2] + 10 - P["FLANGE"][3], fill=False, ec="0.4", lw=0.6, ls=":"))
ax.add_patch(plt.Circle(F7R, 9, fill=False, ec="0.4", lw=0.6, ls=":"))
ax.text(F7R[0], F7R[1], "F7' (S8 only)\non a tab", ha="center", va="center", fontsize=6, color="0.3")
ax.add_patch(Rectangle((X_RIB - RIB_T / 2, Y_PF), RIB_T, BEAM_IN - Y_PF, fc="k", ec="k", lw=0.4, label="divider rib x %.2f (recommended)" % X_RIB))
ol = np.array(OUTLINE)
ax.plot(ol[:, 0], ol[:, 1], color="g", lw=0.6, label="PCB outline incl. ears")
for h in ("H6", "H7"):
    ax.add_patch(plt.Circle(HOLES[h], 4, fill=False, ec="g", lw=0.6))
ax.set_xlim(-15, 223); ax.set_ylim(175, 95)
ax.set_aspect("equal"); ax.grid(True, lw=0.3, alpha=0.5)
ax.set_xlabel("x abs (KiCad; seen from the back, front view is mirrored)"); ax.set_ylabel("y abs (down)")
ax.set_title("GF-2.0 bottom zone in plan, border %.1f: glass %.2f x %.2f, cut-out %.2f x %.2f, flange %.2f x %.2f"
             % (B_REC, P["gW"], P["gH"], P["cut"][1] - P["cut"][0], P["cut"][3] - P["cut"][2], P["FLANGE"][1] - P["FLANGE"][0], P["FLANGE"][3] - P["FLANGE"][2]), fontsize=9)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), fontsize=7, ncol=4)
plt.tight_layout()
f3 = os.path.join(HERE, "concept_gf2_plan_bottom.png")
plt.savefig(f3, dpi=120); plt.close()
out("  wrote %s, %s, %s" % tuple(os.path.basename(f) for f in (f1, f2, f3)))
open(OUT_TXT, "w", encoding="utf8").write("\n".join(_LOG) + "\n")
