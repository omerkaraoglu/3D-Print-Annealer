"""SATOZ SAT070AT40D21Y0-35100T071KN - 7" 800 x 480 TFT (EK9713) + GT911 CTP
(Fannal CT0476 / FN070A133), with the two FPC tails folded around the PCB's
bottom edge onto the PCB top side.

Sources (Datasheets/SAT070AT40D21Y0-35100T071KN (7in TFT + GT911 CTP).pdf):
  * SAT spec V.2 sheet 16/18 "6. Mechanical Drawing" (LCM, 2018-04-26):
      LCM outline 164.90 x 100.00 +-0.3, thickness 3.34 +-0.3,
      bezel open 156.80 x 89.10, A.A. 154.08 x 85.92;
      front view: bezel open 2.70 / A.A. 4.03 from the left end,
                  bezel open 3.75 / A.A. 4.87 from the top edge;
      40-pin tail: 67.65 beyond the bottom edge, finger zone 20.50 wide starting
      19.02 from the left end (front view), 0.5 pitch; the tail is an L:
      bonded on the bottom edge between ~62.3 and ~100.9 from the left end,
      wide (19.02..100.9) up to ~31 mm out, then 20.5 mm wide to the end.
  * Fannal drawing CT0476-V2.0 (CTP, sheet p.27 of the PDF):
      cover glass 164.9 x 100 +-0.15 (= LCM outline), cover VA 155.08 x 86.92,
      VA 3.53 from the left end and 8.85 from the bottom edge,
      stack 1.98 (cover 0.7 + OCA 0.175 + sensor 0.7 + PU tape 0.4),
      6-pin tail 50 +-0.5 beyond the bottom edge, finger centre 40 +-0.5 from the
      RIGHT end (front view), 0.5 pitch, fingers 2.5 wide, tail end 3.5 wide.
ESTIMATED (read off the drawings by scale, no dimension given): the TFT tail's
L-shape corners (62.3 / 100.9 / 7 / 31 mm), the CTP flap outline
(20.7..55.8 / 30.9..50.6 / 38.25..41.75 at 0..9.5 / 9.5..34 / 34..50 mm),
the heights at which the tails leave the panel (TFT 2.6, CTP 3.9 above the
panel back) and the connector entry heights (0.8 / 0.6 above the PCB top).

Model frame (= footprint frame of Rev3:TFT7_SAT070AT40D21_Mech):
  origin = centre of the 164.9 x 100 outline, X/Y as in the FRONT view
  (Y up = panel top edge), Z = 0 at the PCB BACK surface, +Z towards the cover
  glass. The footprint sits on the PCB's B side, so KiCad mirrors X and points
  +Z away from the PCB back; the PCB occupies model z -1.6..0.
  Round 2 (owner decision): the frame holds the panel STANDOFF = 5.0 mm off the
  PCB back (spacer), so the panel back is at model z = STANDOFF and the panel
  occupies z 5.00..10.32; the stand-off is baked into the geometry, the
  footprint's (model ...) offset stays 0 0 0. The tails hang down past the bottom edge, U-turn around it
  and run up the PCB top side (model z = -1.6 - entry height) into J10 / J11.
  The excess tail length is taken up by the U-loop below the board edge
  (hang length h, computed from the connector positions).
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

# ------------------------------------------------------------ panel data
L_OUT, H_OUT = 164.90, 100.00
T_LCM = 3.34
T_PU, T_SENSOR, T_OCA, T_COVER = 0.4, 0.7, 0.175, 0.7
AA = (4.03, 4.87, 154.08, 85.92)           # left, top, w, h  (front view)
BEZEL = (2.70, 3.75, 156.80, 89.10)
VA = (3.53, 100.0 - 8.85 - 86.92, 155.08, 86.92)

# ------------------------------------------------------------ board / connector data
PCB_T = 1.6
STANDOFF = 5.0                               # gap PCB back -> panel back (frame spacer), mm
BOARD = (20.0, 20.0, 184.0, 119.0)          # Edge.Cuts bbox, absolute mm
J10 = (155.65, 112.0)                        # absolute, F side, rot 0 (footprint origin)
J11 = (60.02, 112.4)                         # round 2: moved onto the CTP finger centre
J10_ENTRY_Y, J10_DEPTH_IN = 2.875, 4.0       # FPC entry face at +y of the footprint, insertion depth
J11_ENTRY_Y, J11_DEPTH_IN = 2.05, 3.0
J10_ENTRY_H, J11_ENTRY_H = 0.8, 0.6          # FPC centre above the PCB top (estimated)
TAIL_T = 0.3                                 # FPC + PI (CTP drawing: 0.3 +-0.05)

# tail outlines: list of (v0, v1, u0, u1), u measured from the reference end in the front view
TFT_TAIL = {"ref": "left", "len": 67.65, "z_exit": 2.6,
            "segs": [(0.0, 7.0, 62.3, 100.9), (7.0, 31.0, 19.02, 100.9), (31.0, 67.65, 19.02, 39.52)],
            "finger_u": (19.02 + 39.52) / 2, "finger_len": 3.5}
CTP_TAIL = {"ref": "right", "len": 50.0, "z_exit": 3.9,
            "segs": [(0.0, 9.5, 20.7, 55.8), (9.5, 34.0, 30.9, 50.6), (34.0, 50.0, 38.25, 41.75)],
            "finger_u": 40.0, "finger_len": 3.0}


def panel_x_from_j10():
    """Panel placement: TFT finger centre over J10's centre; bottom edge flush with the PCB's."""
    u = TFT_TAIL["finger_u"]                         # from the front-view left end
    back_x_from_left = L_OUT - u                     # back view (= PCB top view) mirrors X
    left_abs = J10[0] - back_x_from_left
    cx = left_abs + L_OUT / 2
    cy = BOARD[3] - H_OUT / 2
    return cx, cy


CX, CY = panel_x_from_j10()


def abs_to_model(x, y):
    """Absolute board coordinates (top view, y down) -> display model frame (front view)."""
    return -(x - CX), -(y - CY)


def u_to_X(tail, u):
    return -L_OUT / 2 + u if tail["ref"] == "left" else L_OUT / 2 - u


def z_exit(tail):
    """Height (model z) at which the tail leaves the panel: exit height above the panel back + stand-off."""
    return STANDOFF + tail["z_exit"]


def tail_geometry(tail, conn, entry_y, depth_in, entry_h):
    """Solve the hang length so that the tail end sits depth_in inside the connector."""
    z_ret = -PCB_T - entry_h
    r = (z_exit(tail) - z_ret) / 2
    y_edge = -H_OUT / 2
    _, y_end = abs_to_model(conn[0], conn[1] + entry_y - depth_in)
    run_on_board = y_end - y_edge                    # length of the return leg above the board edge
    h = (tail["len"] - math.pi * r - run_on_board) / 2
    return {"z_ret": z_ret, "r": r, "h": h, "y_end": y_end, "y_edge": y_edge}


def path_point(g, tail, s):
    """Point (Y, Z) and tangent angle at arc length s along the tail."""
    h, r, ye = g["h"], g["r"], g["y_edge"]
    if s <= h:
        return ye - s, z_exit(tail)
    if s <= h + math.pi * r:
        phi = (s - h) / r
        yc, zc = ye - h, (z_exit(tail) + g["z_ret"]) / 2
        return yc - r * math.sin(phi), zc + r * math.cos(phi)
    return ye - h + (s - h - math.pi * r), g["z_ret"]


def slab(g, tail, s0, s1, u0, u1, t=TAIL_T):
    y0, z0 = path_point(g, tail, s0)
    y1, z1 = path_point(g, tail, s1)
    ln = math.hypot(y1 - y0, z1 - z0)
    if ln < 1e-6:
        return None
    ang = math.degrees(math.atan2(z1 - z0, y1 - y0))
    xa, xb = sorted((u_to_X(tail, u0), u_to_X(tail, u1)))
    s = (cq.Workplane("XY").box(xb - xa, ln + 0.02, t)
         .rotate((0, 0, 0), (1, 0, 0), ang)
         .translate(((xa + xb) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))
    return s


def build_tail(tail, g, nbend=18):
    br = {0.0, tail["len"], g["h"], g["h"] + math.pi * g["r"], tail["len"] - tail["finger_len"]}
    for v0, v1, _, _ in tail["segs"]:
        br |= {v0, v1}
    for k in range(1, nbend):
        br.add(g["h"] + math.pi * g["r"] * k / nbend)
    br = sorted(b for b in br if 0 <= b <= tail["len"])
    body, fingers = None, None
    for s0, s1 in zip(br[:-1], br[1:]):
        mid = (s0 + s1) / 2
        seg = [sg for sg in tail["segs"] if sg[0] <= mid <= sg[1]][0]
        if mid > tail["len"] - tail["finger_len"]:
            f = slab(g, tail, s0, s1, tail["finger_u"] - 10.0 if tail is TFT_TAIL else tail["finger_u"] - 1.25,
                     tail["finger_u"] + 10.0 if tail is TFT_TAIL else tail["finger_u"] + 1.25, TAIL_T + 0.04)
            fingers = f if fingers is None else fingers.union(f)
        sb = slab(g, tail, s0, s1, seg[2], seg[3])
        if sb is not None:
            body = sb if body is None else body.union(sb)
    return body, fingers


def rect_frame(x0, y0, x1, y1, ix0, iy0, ix1, iy1, z0, z1):
    return box(x0, x1, y0, y1, z0, z1).cut(box(ix0, ix1, iy0, iy1, z0 - 0.1, z1 + 0.1))


def fv_rect(r):
    """front-view rect (left, top, w, h from the outline's top-left) -> model X0,Y0,X1,Y1."""
    l, t, w, h = r
    return -L_OUT / 2 + l, H_OUT / 2 - t - h, -L_OUT / 2 + l + w, H_OUT / 2 - t


def build():
    m = Model("TFT7_SAT070AT40D21", None, "SATOZ SAT070AT40D21Y0-35100T071KN 7in TFT + CTP, tails folded")
    hx, hy = L_OUT / 2, H_OUT / 2
    m.add("lcm", box(-hx, hx, -hy, hy, STANDOFF, STANDOFF + T_LCM), "steel")
    va = fv_rect(VA)
    z = STANDOFF + T_LCM
    m.add("pu_tape", rect_frame(-hx, -hy, hx, hy, *va, z, z + T_PU), "black"); z += T_PU
    m.add("sensor", box(-hx, hx, -hy, hy, z, z + T_SENSOR + T_OCA), "glass"); z += T_SENSOR + T_OCA
    m.add("cover_print", rect_frame(-hx, -hy, hx, hy, *va, z, z + T_COVER), "black")
    m.add("cover_va", box(va[0], va[2], va[1], va[3], z, z + T_COVER), "screen")
    geo = {}
    for name, tail, conn, ey, dpt, eh in (("tft", TFT_TAIL, J10, J10_ENTRY_Y, J10_DEPTH_IN, J10_ENTRY_H),
                                          ("ctp", CTP_TAIL, J11, J11_ENTRY_Y, J11_DEPTH_IN, J11_ENTRY_H)):
        g = tail_geometry(tail, conn, ey, dpt, eh)
        body, fingers = build_tail(tail, g)
        m.add(name + "_tail", body, "polyimide")
        if fingers is not None:
            m.add(name + "_fingers", fingers, "gold")
        jx, jy = abs_to_model(*conn)
        geo[name] = {"hang_h": round(g["h"], 2), "loop_bottom_below_board_edge": round(g["h"] + g["r"], 2),
                     "bend_r": round(g["r"], 2), "z_return": round(g["z_ret"], 2),
                     "z_exit": round(z_exit(tail), 2), "standoff": STANDOFF,
                     "finger_centre_X": round(u_to_X(tail, tail["finger_u"]), 3),
                     "connector_centre_X": round(jx, 3), "connector_centre_Y": round(jy, 3),
                     "lateral_offset_finger_minus_connector": round(u_to_X(tail, tail["finger_u"]) - jx, 3),
                     "tail_end_Y": round(g["y_end"], 3)}
    m.geo = geo
    return m


def board_lines():
    """Board outline (top and bottom faces) and mounting holes in the model frame, for renders."""
    x0, y0, x1, y1 = BOARD
    pts = [abs_to_model(x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0))]
    lines = []
    for zz in (0.0, -PCB_T):
        lines.append([(p[0], p[1], zz) for p in pts])
    return lines


def fit_check(m):
    """Render the panel with a PCB slab and J10/J11 models placed (scratch only, not exported)."""
    import importlib
    fc = Model("TFT7_fit_check_with_PCB_J10_J11", None)
    for lbl, s, c in m.shapes():
        fc.add(lbl, s, c)
    x0, y0, x1, y1 = BOARD
    (a, b), (c_, d) = abs_to_model(x0, y0), abs_to_model(x1, y1)
    fc.add("pcb", box(min(a, c_), max(a, c_), min(b, d), max(b, d), -PCB_T, 0), "green")
    conn = importlib.import_module("fpc_connectors").build_all()
    for cm, pos in ((conn[0], J10), (conn[3], J11)):
        tx, ty = abs_to_model(*pos)
        for lbl, s, c in cm.shapes():
            fc.add(lbl, s.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 180).translate(cq.Vector(tx, ty, -PCB_T)), c)
    return fc


if __name__ == "__main__":
    m = build()
    res = run(m, verify_pins=False, render_views=("iso", "top", "side"), extra_lines=board_lines())
    res["geo"] = m.geo
    res["panel_centre_abs"] = [round(CX, 3), round(CY, 3)]
    res["panel_outline_abs"] = [round(CX - L_OUT / 2, 3), round(CY - H_OUT / 2, 3), round(CX + L_OUT / 2, 3), round(CY + H_OUT / 2, 3)]
    fc = fit_check(m)
    res["fit_png_bottom_edge"] = render(fc, views=("iso2", "side"), fname="TFT7_fit_check_bottom_edge")
    import json
    json.dump(res, open(os.path.join(OUT_DIR, m.name + ".json"), "w"), indent=1)
    print(json.dumps({"geo": m.geo, "centre": res["panel_centre_abs"], "outline": res["panel_outline_abs"]}, indent=1))
