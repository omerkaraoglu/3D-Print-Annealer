"""Hand routing of the "display" region (ESP32 -> SSD1963 8080 bus, SSD1963 U10 fan-out, RGB fan-in to J10, 1.2 V rail,
U10/U31 decoupling).  Idempotent: rebuilds everything and writes tracks_display.json.  Local board mm.
Stages: U10 power fan-out -> 8080 bus -> RGB/sync fan-in -> 1V2 + decoupling.  Run:  python route_display.py [--check]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disp_lib import DR, length, BUS

import json as _j0
_SCR = os.path.dirname(os.path.abspath(__file__))
_j0.dump([t for t in _j0.load(open(os.path.join(_SCR, "tracks_signals.json"))) if t["net"] != "LCD_RST"], open(os.path.join(_SCR, "_signals_noRST.json"), "w"))
R = DR()
P = R.pad
D = "/Display/"
WS = 0.25                      # signal / bus width
V6 = dict(d=0.6, drill=0.3)
LOG = []

# ------------------------------------------------------------------ U10 geometry
IN_L, IN_T, IN_R, IN_B = 51.075, 63.075, 64.925, 76.925       # pad inner ends
def side(n):
    n = int(n)
    return "L" if n <= 32 else "Bo" if n <= 64 else "Ri" if n <= 96 else "T"
def sval(n):
    x, y = P("U10", n); return y if side(n) in ("L", "Ri") else x
def ipt(sd, s, d):
    """point at coordinate s along a side, inset d from the pad inner end"""
    return {"L": (IN_L + d, s), "Ri": (IN_R - d, s), "T": (s, IN_T + d), "Bo": (s, IN_B - d)}[sd]
CORNER = {1, 32, 33, 64, 65, 96, 97, 128}
u10 = {str(n): R.padinfo("U10", n)["net"] for n in range(1, 129)}

# ------------------------------------------------------------------ stage 1: power pins -> vias, 1V2 ring on B.Cu
# every GND/3V3/1V2 pin: inward 0.25 stub to a 0.6/0.3 via (rows at inset 2.3/3.2/4.1, greedy, 0.13 mm escape rule) or a
# short join to a same-net neighbour's stub; 1V2 vias are tied by a B.Cu ring at inset 1.4 (under the pad inner ends).
SIGPINS = [n for n, net in u10.items() if net.startswith(D) and net not in (D + "SSD_RD",)]
for n in SIGPINS:                       # reserve the first 1.2 mm of every signal escape (removed after stage 1)
    R.obs["F"].append((__import__("shapely.geometry", fromlist=["x"]).LineString([P("U10", n), ipt(side(n), sval(n), -1.3)]).buffer(0.125), "<rsv>"))
from shapely.geometry import LineString as _LS
for cx, cy, ux, uy in ((IN_L, IN_T, 1, 1), (IN_R, IN_T, -1, 1), (IN_L, IN_B, 1, -1), (IN_R, IN_B, -1, -1)):
    R.obs["F"].append((_LS([(cx, cy), (cx + 5 * ux, cy + 5 * uy)]), "<bis>"))     # corner bisectors: no stub crosses them
VIA_AT = {}
OUTWARD_GND = {"2", "3", "5", "13", "15", "17", "19", "20", "26"}      # left column GND pins -> vias just outside the pads
ROWA = 2.3
def spread(ss, lo, hi, gap=0.8):
    t = list(ss)
    for i in range(len(t)): t[i] = max(t[i], lo, (t[i - 1] + gap) if i else lo)
    for i in range(len(t) - 1, -1, -1): t[i] = min(t[i], hi, (t[i + 1] - gap) if i < len(t) - 1 else hi)
    for i in range(len(t)): t[i] = max(t[i], (t[i - 1] + gap) if i else lo)
    return [round(v, 3) for v in t]
SIDE_LO = {"L": IN_T, "Ri": IN_T, "T": IN_L, "Bo": IN_L}; SIDE_HI = {"L": IN_B, "Ri": IN_B, "T": IN_R, "Bo": IN_R}
EXTRA = {}                                  # side -> extra (s, d) slots reserved for signal vias (filled later)
def inward_via(n, net, rows=(2.3, 2.7, 3.1, 3.5, 3.9, 4.3)):
    """fallback: pad -> straight to inset e -> 45 deg shift dl -> straight to a via at inset d"""
    sd, s = side(n), sval(n); cands = []
    for d in rows:
        for k in range(-12, 13):
            dl = 0.2 * k
            for e in (0.35, 0.55, 0.75, 0.95, 1.15):
                if e + abs(dl) <= d + 1e-9 and (dl or e == 0.35): cands.append((d + 0.6 * abs(dl), d, dl, e))
    for _, d, dl, e in sorted(cands):
        vp = ipt(sd, s + dl, d)
        pts = [P("U10", n), vp] if not dl else [P("U10", n), ipt(sd, s, e), ipt(sd, s + dl, e + abs(dl)), vp]
        if R.try_via(net, *vp, esc=True) and R.try_track(net, "F", pts, WS, esc=True):
            R.track(net, "F", pts, WS); R.via(net, *vp, **V6); VIA_AT[n] = (d, dl, vp, e if dl else d); return True
    return False
def join_neighbour(n, net):
    sd, s = side(n), sval(n)
    for m in (int(n) - 1, int(n) + 1, int(n) - 2, int(n) + 2):
        if str(m) in VIA_AT and u10[str(m)] == net and side(m) == sd:
            sm = sval(m); d, dl, vp, em = VIA_AT[str(m)]
            for e in (0.35, 0.55, 0.75):
                q = e + abs(sm - s)
                pts = [P("U10", n), ipt(sd, s, e), ipt(sd, sm, q)]
                if q <= em - 0.05:
                    if R.try_track(net, "F", pts, WS, esc=True):
                        R.track(net, "F", pts, WS); VIA_AT[n] = VIA_AT[str(m)]; return True
    return False
def plan_side(sd, pins, d=ROWA):
    lo, hi = SIDE_LO[sd] + d + 0.62, SIDE_HI[sd] - d - 0.62
    pins = sorted(pins, key=sval); t = spread([sval(n) for n in pins], lo, hi)
    neg = [n for n, tt in zip(pins, t) if tt < sval(n) - 1e-6]; pos = [n for n, tt in zip(pins, t) if tt > sval(n) + 1e-6]
    e = {}; sv = {round(sval(n), 2): n for n in pins}
    for n in neg:
        p = sv.get(round(sval(n) - 0.4, 2)); e[n] = e[p] + 0.2 if p in e and p in neg else 0.35
    for n in reversed(pos):
        p = sv.get(round(sval(n) + 0.4, 2)); e[n] = e[p] + 0.2 if p in e and p in pos else 0.35
    bad = []
    for n, tt in zip(pins, t):
        net = u10[n]; s0 = sval(n); dl = tt - s0; vp = ipt(sd, tt, d)
        pts = [P("U10", n), vp] if abs(dl) < 1e-6 else [P("U10", n), ipt(sd, s0, e[n]), ipt(sd, tt, e[n] + abs(dl)), vp]
        if abs(dl) > 1e-6 and e[n] + abs(dl) > d: bad.append(n); continue
        if R.try_via(net, *vp, esc=True) and R.try_track(net, "F", pts, WS, esc=True):
            R.track(net, "F", pts, WS); R.via(net, *vp, **V6); VIA_AT[n] = (d, dl, vp, e[n] if abs(dl) > 1e-6 else d)
        else: bad.append(n)
    return bad
# left column: GND pins 2/3, 5, 15, 17, 19/20, 26 go OUT to vias at x 48.8 (the inner via ring has 11 slots on that side)
OUT_L = {"2": (48.8, 64.4), "3": (48.8, 64.4), "5": (48.8, 65.62), "15": (48.8, 69.68), "17": (48.8, 70.48),
         "19": (48.8, 71.28), "20": (48.8, 71.28), "26": (48.8, 73.8)}
OUT_X = {"124": (53.0, 60.95), "58": (61.6, 79.45), "94": (67.5, 64.3)}   # single outward vias (inner ring full on that side)
CAP_FED = {"97", "100"}                                                     # 3V3 corner/top pins fed through C116 / C115 (stage 4)
OUTWARD_GND = set(OUT_L) | set(OUT_X) | CAP_FED
FAILED = []
for sd in ("L", "Bo", "Ri", "T"):
    pins = [n for n, net in u10.items() if side(n) == sd and net in ("GND", "+3V3", "+1V2") and int(n) not in CORNER and n not in OUTWARD_GND]
    FAILED += plan_side(sd, pins)
for n, (vx, vy) in OUT_L.items():
    s0 = sval(n); dy = vy - s0
    pts = [P("U10", n), (vx + abs(dy), s0), (vx, vy)] if abs(dy) > 1e-6 else [P("U10", n), (vx, vy)]
    R.track("GND", "F", pts, WS)
for v in sorted(set(OUT_L.values())): R.via("GND", *v, **V6)
for n, (vx, vy) in OUT_X.items():
    (px, py), sd = P("U10", n), side(n)
    knee = (px, vy + (0.4 if sd == "T" else -0.4)) if sd in ("T", "Bo") else (vx - 0.4 if vx > px else vx + 0.4, py)
    pts = [(px, py), knee, (vx, vy)] if abs((vx - px) if sd in ("T", "Bo") else (vy - py)) > 1e-6 else [(px, py), (vx, vy)]
    if sd in ("T", "Bo") and abs(vx - px) > 1e-6: pts = [(px, py), (px, vy + (abs(vx - px) if sd == "T" else -abs(vx - px))), (vx, vy)]
    if sd == "Ri": pts = [(px, py), (vx, vy)] if abs(vy - py) < 1e-6 else [(px, py), (vx - abs(vy - py), py), (vx, vy)]
    R.track(u10[n], "F", pts, WS); R.via(u10[n], vx, vy, **V6)
R.obs["F"].remove_tag("<bis>")
# corner pins (pad centres are now outside the shrunk 1.2 mm keep-out squares): 1 and 33 outward, the rest inward
R.track("+1V2", "F", [P("U10", 1), (49.6, 63.8), (48.8, 63.0)], WS); R.via("+1V2", 48.8, 63.0, **V6)
R.track("GND", "F", [P("U10", 33), (51.8, 78.32), (49.92, 80.2)], WS); R.via("GND", 49.92, 80.2, **V6)   # 33 -> C113.2
R.track("GND", "F", [P("U10", 65), (66.2, 76.2), (65.9, 76.5), (65.9, 78.6)], WS); R.via("GND", 65.9, 78.6, **V6)   # 65 outward (S)
for n in ("128", "32", "64", "96"):
    if not inward_via(n, u10[n], (1.6, 1.9, 2.3, 2.7, 3.1)): FAILED.append(n)
FAILED = [n for n in FAILED if not (join_neighbour(n, u10[n]) or inward_via(n, u10[n]))]
R.obs["F"].remove_tag("<rsv>")
LOG.append("U10 power pins without via: %s" % FAILED)

# ------------------------------------------------------------------ ESP32 pin -> 33R source resistors (straight 1.4 mm stubs)
for ref, pin in (("R110", 27), ("R111", 28), ("R118", 29), ("R112", 30), ("R113", 31), ("R114", 33), ("R115", 36), ("R116", 37),
                 ("R117", 10), ("R120", 11), ("R119", 12), ("R121", 13)):
    (px, py), (rx, ry) = P("U3", pin), P(ref, "1")
    R.track(R.padinfo(ref, "1")["net"], "F", [(px, py), (px, ry)], WS)     # resistor sits 0.01 mm off the pin axis


# ================================================================== stage 2: 8080 bus (planar after the GPIO remap)
from shapely.geometry import LineString as _LS2
def offs(pts, d):
    """parallel copy of a 0/45/90 polyline; d > 0 = west/north side for paths heading south/east (y-down screen)"""
    return [(round(x, 4), round(y, 4)) for x, y in _LS2(pts).offset_curve(d, join_style="mitre", mitre_limit=10).coords]
def ch(p, q, c=0.5):
    """two points of a chamfered 90 deg corner at q coming from p's direction (helper for hand-written paths)"""
    return q
SN = lambda n: D + "SSD_" + n
# top bundle: k = 0 (D0, inner/south row) .. 7 (D7, outer).  0.2 mm / 0.35 mm pitch past the resistors and R12, 0.25 / 0.45 after the turn
TOP = [("R110", "D0"), ("R111", "RST"), ("R118", "CS"), ("R112", "DC"), ("R113", "WR"), ("R114", "D5"), ("R115", "D6"), ("R116", "D7")]
CEN = [(33.0, 38.3), (33.0, 44.0), (43.0, 54.0), (60.0, 54.0)]          # centreline of line 0 (D0) for the wide part
DROP = {"RST": 52.2, "CS": 53.4, "DC": 53.85, "WR": 55.15, "D5": 56.6, "D6": 57.0, "D7": 57.4}
for k, (ref, fn) in enumerate(TOP):
    net = SN(fn); xr, yr = P(ref, "2")
    y0 = 37.875 - 0.35 * k; jx = 23.8 + 0.145 * k; X = 33.0 + 0.45 * k; y1 = y0 + 0.2
    c = 0.5
    narrow = [(xr, yr), (xr, y0 + c), (xr + c, y0), (jx, y0), (jx + 0.2, y1), (X - 0.5, y1), (X, y1 + 0.5)]
    R.track(net, "F", narrow, 0.2)
    wide = offs(CEN, -0.45 * k)
    wide[0] = (X, y1 + 0.5)
    if fn == "D0":
        tail = [wide[0], wide[1], wide[2], (45.1, wide[2][1]), (45.6, wide[2][1] + 0.5), (45.6, 65.7), (46.1, 66.2), P("U10", 7)]
    else:
        xd, yrow = DROP[fn], wide[2][1]
        tail = [wide[0], wide[1], wide[2], (xd - c, yrow), (xd, yrow + c)]
        pin = {"RST": 127, "CS": 123, "DC": 122, "WR": 120, "D5": 116, "D6": 115, "D7": 114}[fn]
        px, py = P("U10", pin)
        if abs(xd - px) < 1e-6: tail += [(px, py)]
        else:
            jy = {"CS": 59.6, "DC": 58.3, "WR": 59.6}[fn]       # 45 deg jog onto the pin axis below R124
            tail += [(xd, jy), (px, jy + abs(px - xd)), (px, py)]
    R.track(net, "F", tail, WS)
# RD pull-up: R124.2 (bottom pad after the 180 deg rotation) straight down to pin 121, R124.1 -> 3V3 via above (clear of the B.Cu band)
rx, ry = P("R124", "2"); px, py = P("U10", 121)
R.track(SN("RD"), "F", [(rx, ry), (rx, 57.6), (px, 57.6 + abs(px - rx)), (px, py)], WS)
r1 = P("R124", "1"); R.track("+3V3", "F", [r1, (r1[0], 55.3)], WS); R.via("+3V3", r1[0], 55.3, **V6)
# bottom bundle: R121 (D1) R119 (D2) R120 (D3) R117 (D4) -> left column pins 8..11 from the west
BOT = [("R121", "D1", 8), ("R119", "D2", 9), ("R120", "D3", 10), ("R117", "D4", 11)]
for k, (ref, fn, pin) in enumerate(BOT):
    net = SN(fn); xr, yr = P(ref, "2"); row = 62.75 + 0.45 * k
    px, py = P("U10", pin); sx = 35.0 - 0.12 * k; dlt = py - row
    pts = [(xr, yr), (xr, row - 0.5), (xr + 0.5, row), (sx, row), (sx + dlt, py), (px, py)]
    R.track(net, "F", pts, WS)


# LCD_RST (now module pin 28 / R111) to the touch connector J11.6: under the module on B.Cu, across the signals' B band on F,
# then the former signals corridor (B.Cu y 59.3, x 41.75 column, y 95.85 under J10/J11) into J11.6
NR = "LCD_RST"; p28 = P("U3", 28); j6 = P("J11", 6)
R.track(NR, "F", [p28, (p28[0], 42.85)], WS); R.via(NR, p28[0], 42.85, **V6)
R.track(NR, "B", [(p28[0], 42.85), (27.75, 42.85), (28.3, 43.4), (28.3, 55.6)], WS); R.via(NR, 28.3, 55.6, **V6)
R.track(NR, "F", [(28.3, 55.6), (28.3, 59.6)], WS); R.via(NR, 28.3, 59.6, **V6)
R.track(NR, "B", [(28.3, 59.6), (28.6, 59.3), (41.25, 59.3), (41.75, 59.8), (41.75, 95.35), (42.25, 95.85), (j6[0] - 0.5, 95.85),
                  (j6[0], 95.35), j6], WS)
def gnd_near(net_xy, cands):
    for gx, gy in cands:
        if R.try_via("GND", gx, gy):
            R.via("GND", gx, gy, **V6); return (gx, gy)
    LOG.append("no GND return via near %s" % (net_xy,)); return None
for vxy, cands in (((p28[0], 42.85), [(21.6, 43.5), (19.8, 43.5), (20.69, 43.9)]), ((28.3, 59.6), [(27.3, 59.9), (27.2, 60.6), (28.3, 60.6)])):
    gnd_near(vxy, cands)


# ================================================================== stage 3: RGB / sync fan-in to J10 (B.Cu pads, pin 1 on the right)
def JP(net): return [P("J10", n) for n, nt, x, y in R.pads_of("J10") if nt == net][0]
def fan_via(net, start, dirv, cands, esc=True):
    """F stub start -> straight along dirv to e -> 45 deg to the via (vx, vy) -> via.  cands: list of (vx, vy) tried in order"""
    sx, sy = start; ux, uy = dirv
    for vx, vy in cands:
        along = (vx - sx) * ux + (vy - sy) * uy; side_ = (vx - sx) * uy + (vy - sy) * ux
        if along < abs(side_) + 0.3: continue
        e = along - abs(side_)
        mid = (sx + ux * e, sy + uy * e)
        pts = [start, mid, (vx, vy)] if abs(side_) > 1e-6 else [start, (vx, vy)]
        if R.try_via(net, vx, vy, esc=esc) and R.try_track(net, "F", pts, WS, esc=esc):
            R.track(net, "F", pts, WS); R.via(net, vx, vy, **V6); return (vx, vy)
    LOG.append("fan_via failed: " + net); return None
RV = {}
# right column (B-long): G3..G0, R7..R0 escape east; vias on a staircase (x step 0.66, via 0.2 below its pin row) so every
# escape passes 0.6 above the previous via; B.Cu: straight down to y 80.3, one 45 deg run SW, straight into the pad
RC = [(67, "G3"), (68, "G2"), (69, "G1"), (70, "G0"), (71, "R7"), (72, "R6"), (76, "R5"), (77, "R4"), (78, "R3"), (79, "R2"), (80, "R1"), (81, "R0")]
YS = 79.9
for k, (pin, nm) in enumerate(RC):
    (px, py), vx = P("U10", pin), 66.9 + 0.66 * k
    vy = py + 0.2
    R.track(D + nm, "F", [(px, py), (vx - 0.2, py), (vx, vy)], WS); R.via(D + nm, vx, vy, **V6); RV[nm] = (vx, vy)
    jx, jy = JP(D + nm)
    R.track(D + nm, "B", [(vx, vy), (vx, YS), (jx, YS + vx - jx), (jx, jy)], WS)
# bottom row (B-long): B0, G7..G4 fan out 45 deg (east-most turns first), vias in two staggered rows, B.Cu 45 deg into the pads
BR = [(59, "B0", 62.35, 80.85, 80.04), (60, "G7", 63.0, 80.055, 79.655), (61, "G6", 63.65, 80.6, 79.27), (62, "G5", 64.3, 79.785, 78.885), (63, "G4", 64.95, 80.5, 78.5)]
for pin, nm, vx, vy, t in BR:
    px, py = P("U10", pin); de = t + vx - px
    R.track(D + nm, "F", [(px, py), (px, t), (vx, de)] + ([(vx, vy)] if vy > de + 1e-6 else []), WS); R.via(D + nm, vx, vy, **V6); RV[nm] = (vx, vy)
    jx, jy = JP(D + nm)
    R.track(D + nm, "B", [(vx, vy), (vx, 81.2), (jx, 81.2 + vx - jx), (jx, jy)], WS)
# syncs (B-long): fanned stubs to three vias under the bottom row, B.Cu straight down then one 45 deg run into the pads
for pin, nm, pts, yd in ((43, "VSYNC", [(55.8, 78.5), (55.3, 79.0), (55.3, 79.4)], 86.3), (44, "HSYNC", [(56.2, 80.3)], 86.0),
                         (45, "PCLK", [(56.6, 78.5), (57.1, 79.0), (57.1, 79.4)], 79.4)):
    st = P("U10", pin); vx, vy = pts[-1]
    R.track(D + nm, "F", [st] + pts, WS); R.via(D + nm, vx, vy, **V6); RV[nm] = (vx, vy)
    jx, jy = JP(D + nm); R.track(D + nm, "B", [(vx, vy), (vx, yd), (jx, yd + jx - vx), (jx, jy)], WS)
# DE: F down and west under the sync vias, via west of VSYNC, B.Cu into pad 34 (west of VSYNC)
st = P("U10", 49); R.track(D + "DE", "F", [st, (58.2, 78.6), (58.6, 79.0), (58.6, 81.1), (58.1, 81.6), (54.6, 81.6)], WS); R.via(D + "DE", 54.6, 81.6, **V6); RV["DE"] = (54.6, 81.6)
jx, jy = JP(D + "DE"); R.track(D + "DE", "B", [(54.6, 81.6), (54.6, 86.5), (jx, 86.5 + jx - 54.6), (jx, jy)], WS)
# left column B7..B4 + B1 (F): west, down the cap row (0.42 mm pitch between C120/C121 and C113), east under the syncs/DE,
# vias on a staircase just before the pads, B.Cu into pads 28..25 and 22
LC = [(31, "B4", 49.26, 82.75, 60.5, 83.55), (30, "B5", 48.84, 83.2, 59.85, 84.05), (29, "B6", 48.42, 83.65, 59.2, 84.5), (28, "B7", 48.0, 84.1, 58.55, 85.0)]
for pin, nm, cx, row, vx, vy in LC:
    px, py = P("U10", pin)
    c0 = 0.25 if nm == "B4" else 0.5          # B4 turns next to pin 32's pad
    R.track(D + nm, "F", [(px, py), (cx + c0, py), (cx, py + c0), (cx, row - 0.5), (cx + 0.5, row), (vx - 0.5, row), (vx, row + 0.5), (vx, vy)], WS)
    R.via(D + nm, vx, vy, **V6); RV[nm] = (vx, vy)
    jx, jy = JP(D + nm); yj = vy + 1.15 if nm == "B4" else vy
    R.track(D + nm, "B", [(vx, vy), (vx, yj), (jx, yj + abs(jx - vx)), (jx, jy)], WS)
px, py = P("U10", 35)
R.track(D + "B1", "F", [(px, py), (px, 81.8), (px + 0.5, 82.3), (61.1, 82.3), (61.6, 82.8), (61.6, 83.1)], WS); R.via(D + "B1", 61.6, 83.1, **V6); RV["B1"] = (61.6, 83.1)
jx, jy = JP(D + "B1"); R.track(D + "B1", "B", [(61.6, 83.1), (61.6, 88.0), (jx, 88.2), (jx, jy)], WS)

# B3/B2 (pins 85/86, top of the right column): F around the east of the staircase, west under R128/R127, vias BELOW the
# J10 pads (B.Cu stub up into the pad's outer end) - their neighbours B4/B1 arrive from the north
for pin, nm, cx, row, dx, vx in ((85, "B3", 74.98, 85.3, 60.55, 60.55), (86, "B2", 75.43, 85.75, 61.55, 61.55)):
    px, py = P("U10", pin); jx, jy = JP(D + nm)
    R.track(D + nm, "F", [(px, py), (cx - 0.5, py), (cx, py + 0.5), (cx, row - 0.5), (cx - 0.5, row), (dx + 0.5, row), (dx, row + 0.5), (dx, 93.55)], WS)
    R.via(D + nm, vx, 93.55, **V6); RV[nm] = (vx, 93.55)
    R.track(D + nm, "B", [(vx, 93.55), (jx, 93.55 - abs(jx - vx)), (jx, jy)], WS)
# BL_PWM (pin 51) -> R128.1 on F, under nothing but B.Cu lines
st = P("U10", 51); r1 = P("R128", "1")
R.track(D + "BL_PWM", "F", [st, (st[0], 78.6), (59.4, 79.0), (59.4, 81.1), (59.9, 81.6), (r1[0] - (r1[1] - 81.6), 81.6), r1], WS)

# J10 ground pins 36 / 29 / 3: vias below the pads (B.Cu stub to the outer pad end); TFT_VDD (pin 4) likewise from C123.1 on F
for pin, vx, vy in (("36", 54.55, 93.55), ("29", 58.55, 93.55), ("3", 71.55, 93.55)):
    jx, jy = P("J10", pin); R.via("GND", vx, vy, **V6); R.track("GND", "B", [(vx, vy), (jx, vy - abs(jx - vx)), (jx, jy)], 0.3)
TV = D + "TFT_VDD"; c123, c122, r125 = P("C123", "1"), P("C122", "1"), P("R125", "2"); j4 = P("J10", "4")
R.track(TV, "F", [c123, (c123[0], 94.4)], 0.6); R.via(TV, c123[0], 94.4, **V6)
R.track(TV, "B", [(c123[0], 94.4), (j4[0], 94.4 - abs(j4[0] - c123[0])), j4], 0.3)
R.track(TV, "F", [c123, (c123[0] + 0.5, c123[1]), (c123[0] + 0.5 + (c122[1] - c123[1]), c122[1]), c122], 0.6)
R.track(TV, "F", [r125, (73.96, r125[1]), (73.96, c122[1] - 0.45), (73.51, c122[1]), c122], 0.6)
c123g, c122g = P("C123", "2"), P("C122", "2")
R.track("GND", "F", [c123g, (c123g[0], 87.55), (71.05, 87.0), (71.05, 86.5)], 0.4); R.track("GND", "F", [c122g, (71.6, c122g[1]), (71.05, 87.0)], 0.4)
R.via("GND", 71.05, 86.5, **V6)
r1251 = P("R125", "1"); R.track("+3V3", "F", [r1251, (r1251[0], 90.5)], 0.4); R.via("+3V3", r1251[0], 90.5, **V6)
# return vias: a GND via within 1.5 mm of every bus/RGB signal via (searched on a ring, shared where possible)
import math as _m
def ret_vias(nets):
    sig = [t for t in R.items if t["via"] and t["net"] in nets]
    gnd = lambda: [(o[0].centroid.x, o[0].centroid.y) for o in R.obs["B"] if o[1] == "GND" and abs(o[0].area - 0.2826) < 0.01]   # GND vias (any region)
    miss = 0
    for t in sig:
        x, y = t["x"] - 20, t["y"] - 20
        if any(_m.hypot(gx - x, gy - y) <= 1.5 for gx, gy in gnd()): continue
        ok = False
        for r in (0.85, 0.95, 1.05, 1.15, 1.25, 1.35, 1.45):
            for a in range(0, 360, 5):
                gx, gy = round(x + r * _m.cos(_m.radians(a)), 3), round(y + r * _m.sin(_m.radians(a)), 3)
                if R.try_via("GND", gx, gy):
                    R.via("GND", gx, gy, **V6); ok = True; break
            if ok: break
        miss += not ok
        if not ok: LOG.append("  no return via at %s (%.2f, %.2f)" % (t["net"].split("/")[-1], x, y))
    LOG.append("return vias: %d signal vias without a GND via within 1.5 mm" % miss)
RGBN = {D + n for n in ["R%d" % i for i in range(8)] + ["G%d" % i for i in range(8)] + ["B%d" % i for i in range(8)] + ["PCLK", "HSYNC", "VSYNC", "DE"]}
R.via("GND", 57.0, 80.85, **V6)          # HSYNC / PCLK return via between their B.Cu lines
ret_vias(RGBN | {"LCD_RST"})


# ================================================================== stage 4a: crystal, left-side decoupling
XI, XO = D + "XTAL_IN", D + "XTAL_OUT"
p22, p24 = P("U10", 22), P("U10", 24); y1, y3, y4, y2 = P("Y10", 1), P("Y10", 3), P("Y10", 4), P("Y10", 2)
R.track(XI, "F", [p22, (49.0, p22[1]), (49.0 - (p22[1] - y1[1]), y1[1]), (P("C110", "1")[0], y1[1]), y1], WS)
c110 = P("C110", "1"); R.track(XI, "F", [c110, (c110[0], y1[1])], WS)
R.track(XO, "F", [p24, (47.1, p24[1]), (46.6, p24[1] + 0.5), (46.6, 74.3), (46.1, 74.8), (P("C111", "1")[0], 74.8), (43.6, 74.8), (y3[0], 74.3), y3], WS)
c111 = P("C111", "1"); R.track(XO, "F", [c111, (c111[0], 74.8)], WS)
R.track("GND", "F", [y4, (44.95, y4[1]), (43.45, 72.35), (43.25, y2[1]), y2], WS);   # case ground pads tied through the centre
R.track("GND", "F", [y2, (y2[0], 70.9)], 0.4); R.via("GND", y2[0], 70.9, **V6)
c110g, c111g = P("C110", "2"), P("C111", "2")
R.track("GND", "F", [c110g, (48.64, c110g[1]), (48.8, 69.68)], 0.4)
R.track("GND", "F", [c111g, (c111g[0], 77.5)], 0.4); R.via("GND", c111g[0], 77.5, **V6)
# C112: 3V3 pad -> pin 4, GND pad -> the pin 2/3 outward via
c112, c112g, p4 = P("C112", "1"), P("C112", "2"), P("U10", 4)
R.track("+3V3", "F", [c112, (48.0, c112[1]), (48.0 + (c112[1] - p4[1]), p4[1]), p4], WS)
R.track("GND", "F", [c112g, (48.68, c112g[1]), (48.8, 64.4)], WS)
# C117 (1V2): pad -> pin 14 on F, plus a via that ties pin 1's outward 1V2 via on B.Cu; GND pad -> own via
c117, c117g, p14 = P("C117", "1"), P("C117", "2"), P("U10", 14)
R.track("+1V2", "F", [c117, (48.9, c117[1]), (48.9 + (p14[1] - c117[1]), p14[1]), p14], WS)
R.track("+1V2", "F", [c117, (c117[0], 69.9)], WS); R.via("+1V2", c117[0], 69.9, **V6)
R.track("+1V2", "B", [(48.8, 63.0), (46.6, 65.2), (46.6, 69.38), (c117[0], 69.9)], 0.4)
R.track("GND", "F", [c117g, (44.3, c117g[1])], 0.4); R.via("GND", 44.3, c117g[1], **V6)
# C113: GND pad -> pin 33's via (pad-to-pin), 3V3 pad -> own via (the pin 33 link sits between it and pin 34)
c113, c113g = P("C113", "1"), P("C113", "2")
R.track("GND", "F", [c113g, (c113g[0], 80.2)], 0.4)
p34 = P("U10", 34); R.track("+3V3", "F", [c113, (c113[0], 80.82), (p34[0], 80.82 - (p34[0] - c113[0])), p34], WS)


# ================================================================== stage 4b: top decoupling, C114, U31 + caps, 1.2 V feed and B.Cu ring
def lnk(net, pts, w=WS, via=None):
    R.track(net, "F", pts, w)
    if via: R.via(net, via[0], via[1], **V6)
c = P("C119", "1"); lnk("+1V2", [c, (c[0], 59.3), (59.0, 59.3 + 59.0 - c[0]), P("U10", 110)])
c = P("C119", "2"); lnk("GND", [c, (59.6, c[1]), (59.85, c[1] + 0.25), (59.85, 59.45)], 0.4, (59.85, 59.45))
c = P("C115", "1"); p = P("U10", 100); lnk("+3V3", [c, (c[0], 59.3), (p[0], 59.3 + p[0] - c[0]), p]); R.via("+3V3", 62.0, 59.3 + 62.0 - c[0], **V6)
c = P("C115", "2"); lnk("GND", [c, (62.5, c[1]), (62.9, c[1] + 0.4), (62.9, 59.4)], 0.4, (62.9, 59.4))
c = P("C116", "1"); p = P("U10", 97); lnk("+3V3", [c, (c[0], 60.35), (p[0], 60.35 + c[0] - p[0]), p]); R.via("+3V3", c[0], 59.95, **V6)
c = P("C116", "2"); lnk("GND", [c, (c[0], 59.95)], 0.4, (c[0], 59.95))
c = P("C114", "1"); p = P("U10", 95); lnk("+3V3", [c, (c[0], 63.35), (c[0] - 0.85, p[1]), p])
c = P("C114", "2"); lnk("GND", [c, (68.4, c[1])], 0.4, (68.4, c[1]))
# U31 LD1117-1.2: tab feeds pin 93 (0.5 mm, necked at the pad); C336/C337 on the tab; C335 on VIN; GND / 3V3 vias
tab = P("U31", "2"); p93 = P("U10", 93)
R.track("+1V2", "F", [tab, (tab[0], 65.75), (tab[0] - 0.75, p93[1]), (67.9, p93[1])], 0.5); R.track("+1V2", "F", [(67.9, p93[1]), p93], WS)
c6, c7 = P("C336", "1"), P("C337", "1")
R.track("+1V2", "F", [(83.15, 68.0), tab], 0.5)          # LD1117 pin 2 (OUT) to its tab (geom.json keeps only the tab for "2")
R.track("+1V2", "F", [c6, (c6[0], 70.8), (c6[0], tab[1] + 0.2), tab], 0.5); R.track("+1V2", "F", [c7, (c7[0], 72.4), (c7[0] - 1.6, 70.8), (c6[0], 70.8)], 0.5)
for ref, d in (("C336", (0, -1.4)), ("C337", (0, 1.0)), ("C335", (1.0, 0)), ("U31", None)):
    pass
c = P("C336", "2"); lnk("GND", [c, (c[0], 72.6)], 0.4, (c[0], 72.6))
c = P("C337", "2"); lnk("GND", [c, (c[0], 75.0)], 0.4, (c[0], 75.0))
c = P("C335", "2"); lnk("GND", [c, (84.675, c[1]), (83.15, c[1] + 1.525)], WS); lnk("GND", [c, (87.5, c[1])], 0.4, (87.5, c[1]))
u1, u3, c5 = P("U31", "1"), P("U31", "3"), P("C335", "1")
lnk("GND", [u1, (84.6, u1[1])], 0.4, (84.6, u1[1]))
lnk("+3V3", [c5, (84.675, c5[1]), u3])
R.track("+3V3", "F", [u3, (83.85, 65.0), (84.6, 65.0)], 0.4); R.via("+3V3", 84.6, 65.0, **V6)
# 1.2 V ring on B.Cu (inset 3.3) tied to every inner 1V2 via; outside 1V2 (pin 1, pin 32, caps) joins through C117 -> pin 14
RX0, RY0, RX1, RY1 = IN_L + 3.3, IN_T + 3.3, IN_R - 3.3, IN_B - 3.3
R.track("+1V2", "B", [(RX0, RY0), (RX1, RY0), (RX1, RY1), (RX0, RY1), (RX0, RY0)], 0.3)
for n, v in VIA_AT.items():
    if u10[n] != "+1V2" or int(n) in CORNER: continue
    vx, vy = v[2]; sd = side(n)
    if sd == "L": q = (RX0, min(max(vy, RY0), RY1))
    elif sd == "Ri": q = (RX1, min(max(vy, RY0), RY1))
    elif sd == "T": q = (min(max(vx, RX0), RX1), RY0)
    else: q = (min(max(vx, RX0), RX1), RY1)
    dx, dy = q[0] - vx, q[1] - vy
    if abs(abs(dx) - abs(dy)) < 1e-6 or abs(dx) < 1e-6 or abs(dy) < 1e-6: pts = [(vx, vy), q]
    elif abs(dx) > abs(dy): pts = [(vx, vy), (vx + (abs(dx) - abs(dy)) * (1 if dx > 0 else -1), vy), q]
    else: pts = [(vx, vy), (vx, vy + (abs(dy) - abs(dx)) * (1 if dy > 0 else -1)), q]
    if R.try_track("+1V2", "B", pts, 0.3, esc=True): R.track("+1V2", "B", pts, 0.3)
    else: LOG.append("1V2 ring stub blocked at pin %s" % n)
# bottom-right corner pin 64 via -> pin 56's via (B); bottom-left caps + pin 32 via -> C117's via (B)
v64, v56 = VIA_AT["64"][2], VIA_AT["56"][2]
R.track("+1V2", "B", [v64, (v56[0] + 0.3, v64[1]), (v56[0], v64[1] - 0.3), v56], 0.3)
v32 = VIA_AT["32"][2]; c117v = (P("C117", "1")[0], 69.9)
R.track("+1V2", "B", [c117v, (45.4, 70.58), (45.4, VIA_AT["32"][2][1]), (45.4, 78.775), (45.4, 81.975), (45.4, 82.6)], 0.4); R.via("+1V2", 45.4, 82.6, **V6)
R.track("+1V2", "F", [P("C118", "1"), (45.4, 82.6)], 0.4)
R.track("+1V2", "B", [v32, (45.4, v32[1])], 0.4)
for ref, y in (("C120", 78.775), ("C121", 81.975)):
    c = P(ref, "1"); R.track("+1V2", "F", [c, (46.15, c[1])], 0.4); R.via("+1V2", 46.15, c[1], **V6); R.track("+1V2", "B", [(46.15, c[1]), (45.4, c[1])], 0.4)
    g = P(ref, "2"); R.track("GND", "F", [g, (46.2, g[1])], 0.4); R.via("GND", 46.2, g[1], **V6)
R.track("GND", "F", [P("C118", "2"), (46.2, P("C118", "2")[1]), (46.2, P("C121", "2")[1])], 0.4)

# ================================================================== save / check
R.save("tracks_display.json")
for l in LOG: print(l)
MYNETS = sorted({t["net"] for t in R.items})
if "--check" in sys.argv:
    import json as _j      # the coordinator strips LCD_RST from tracks_signals.json (moved to module pin 28); check against a filtered copy
    _j.dump([t for t in _j.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracks_signals.json"))) if t["net"] != "LCD_RST"],
            open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_signals_noRST.json"), "w"))
    R.check("tracks_display.json", nets=MYNETS, extra_json=["tracks_power.json", "_signals_noRST.json", "tracks_mains.json"],
            out="check_display.kicad_pcb", show=25)
