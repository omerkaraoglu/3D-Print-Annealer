"""Display region, layout pass 2 (Rev3.0).  Hand routing of: U10 SSD1963 power fan-out + decoupling (pass-1 stage 1, unchanged),
ESP32 -> SSD1963 8080 bus (pass-1 stage 2, unchanged), RGB/sync fan-in U10 -> J10 (new: J10 at (135.65, 94.6) B.Cu),
U31 LD1117-1.2 + 1V2 feed, J10 companions (TFT_VDD, GND), BL_PWM/BL_EN stubs at R128/R127, J11 touch block (I2C, TP_INT,
TP_VDD, LCD_RST).  Idempotent: rebuilds everything and writes tracks_display.json.  Local board mm.
Run:  python route_display.py [--check]            (needs geom_display.json / rev3_placed_display.kicad_pcb, see PASS2_BRIEF.md)"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from disp_lib import DR, length, BUS
_SCR = os.path.dirname(os.path.abspath(__file__))
def _newer(fn, t0=1794394800):      # 2026-11-11 14:00 local: other regions' pass-2 track files only (pass-1 copies are stale)
    p = os.path.join(_SCR, fn); return os.path.exists(p) and os.path.getmtime(p) > t0
XTRA = ["tracks_signals.json"] + [f for f in ("tracks_power.json", "tracks_mains.json") if _newer(f)]
ASSUME = "--assume" in sys.argv     # develop against the private build with the requested moves of other regions' parts
R = DR(extra=XTRA, geom="geom_display_assume.json" if ASSUME else "geom_display.json",
       placed="rev3_placed_display_assume.kicad_pcb" if ASSUME else "rev3_placed_display.kicad_pcb")
P = R.pad
D = "/Display/"
WS = 0.25                      # signal / bus width
V6 = dict(d=0.6, drill=0.3)
LOG = ["extra track files: %s" % XTRA]
D = "/Display/"
WS = 0.25                      # signal / bus width
V6 = dict(d=0.6, drill=0.3)

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
OUT_X = {"124": (53.0, 60.95), "58": (61.5, 79.5), "94": (67.5, 64.3)}   # pass 2: 58 moved 0.1 W (B0 escape)   # single outward vias (inner ring full on that side)
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
R.track("GND", "F", [P("U10", 65), (66.2, 76.2), (66.5, 76.5)], WS); R.via("GND", 66.5, 76.5, **V6)   # 65 outward (pass 2: SE corner pocket)
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



# ---- pass-1 stage 4a/4b (U10 crystal + decoupling, unchanged) and the 1.2 V B.Cu ring (unchanged); U31 is re-done in stage 4 (pass 2)
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


# LCD_RST (now module pin 28 / R111) to the touch connector J11.6: under the module on B.Cu, across the signals' B band on F,
# then the former signals corridor (B.Cu y 59.3, x 41.75 column, y 95.85 under J10/J11) into J11.6
NR = "LCD_RST"; p28 = P("U3", 28); j6 = P("J11", 6)
R.track(NR, "F", [p28, (p28[0], 42.85)], WS); R.via(NR, p28[0], 42.85, **V6)
R.track(NR, "B", [(p28[0], 42.85), (27.75, 42.85), (28.3, 43.4), (28.3, 55.6)], WS); R.via(NR, 28.3, 55.6, **V6)
R.track(NR, "F", [(28.3, 55.6), (28.3, 59.6)], WS); R.via(NR, 28.3, 59.6, **V6)
R.track(NR, "B", [(28.3, 59.6), (28.6, 59.3)], WS)        # pass 2: continues in stage 6 (J11 now at (40.3, 94.6))
def gnd_near(net_xy, cands):
    for gx, gy in cands:
        if R.try_via("GND", gx, gy):
            R.via("GND", gx, gy, **V6); return (gx, gy)
    LOG.append("no GND return via near %s" % (net_xy,)); return None
for vxy, cands in (((p28[0], 42.85), [(21.6, 43.5), (19.8, 43.5), (20.69, 43.9)]), ((28.3, 59.6), [(27.3, 59.9), (27.2, 60.6), (28.3, 60.6)])):
    gnd_near(vxy, cands)

STAGE12_END = len(R.items)

# ================================================================== stage 3a (pass 2): RGB/sync escape from U10 and the NE sweep into the corridor
# Corridor (heading east) rows north -> south, 0.4 mm pitch from y 60.65 (0.75 below the signals agent's /ZCD at y 59.9):
CORR = ["B2", "B3", "R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "G0", "G1", "G2", "G3",
        "G4", "G5", "G6", "G7", "B0", "DE", "PCLK", "HSYNC", "VSYNC", "B1", "B4", "B5", "B6", "B7"]
PIN = {"B2": 86, "B3": 85, "R0": 81, "R1": 80, "R2": 79, "R3": 78, "R4": 77, "R5": 76, "R6": 72, "R7": 71, "G0": 70, "G1": 69,
       "G2": 68, "G3": 67, "G4": 63, "G5": 62, "G6": 61, "G7": 60, "B0": 59, "DE": 49, "PCLK": 45, "HSYNC": 44, "VSYNC": 43,
       "B1": 35, "B4": 31, "B5": 30, "B6": 29, "B7": 28}
Y0C, PC = 60.65, 0.4
YC = {nm: round(Y0C + PC * k, 4) for k, nm in enumerate(CORR)}
C0 = 136.05                                     # x + y of B2's NE diagonal; every next line +0.4*sqrt(2) (0.4 mm pitch at 45 deg)
CK = {nm: C0 + PC * math.sqrt(2) * k for k, nm in enumerate(CORR)}
YR0 = 79.0                                      # rows under U10 for the bottom/left group (G4 first, 0.4 pitch)
YR = {nm: round(YR0 + PC * (k - 14), 4) for k, nm in enumerate(CORR) if k >= 14}
LCOL = {"B4": (49.26, 0.25), "B5": (48.84, 0.5), "B6": (48.42, 0.5), "B7": (48.0, 0.5)}   # left column: down the cap row (pass 1)
ESC = {}                                         # net short name -> list of points from the pad to the corridor row (x_end, y)
for k, nm in enumerate(CORR):
    px, py = P("U10", PIN[nm]); c = CK[nm]; yc = YC[nm]
    if k < 14:                                   # right column: east, NE diagonal, east
        pts = [(px, py), (round(c - py, 4), py), (round(c - yc, 4), yc)]
    elif nm in LCOL:                             # left column: west, down the cap row, east under U10, NE
        cx, c0 = LCOL[nm]; yr = YR[nm]
        pts = [(px, py), (cx + c0, py), (cx, py + c0), (cx, yr - 0.5), (cx + 0.5, yr), (round(c - yr, 4), yr), (round(c - yc, 4), yc)]
    else:                                        # bottom row: south, east under U10, NE
        yr = YR[nm]
        pts = [(px, py), (px, yr - 0.5), (px + 0.5, yr), (round(c - yr, 4), yr), (round(c - yc, 4), yc)]
    ESC[nm] = pts
# BL_PWM (pin 51) sits inside the bundle (between DE and B0): short stub to a via in the pocket, B.Cu under the bundle to R128
R.track(D + "BL_PWM", "F", [P("U10", 51), (59.0, 79.2), (59.4, 79.6)], WS); R.via(D + "BL_PWM", 59.4, 79.6, **V6)

STAGE3A_END = len(R.items)

# ================================================================== stage 3b (pass 2): corridor -> down-leg -> via field -> B.Cu rows -> J10
# Via field west of PS1 (x ~100.6..121, y ~78..93.5): every line except B2/B3 changes F -> B once here (crossbar: F columns come
# down from the corridor, B rows leave east in J10 order).  GND return vias sit in the pockets of the wider column gaps.
# J10 entry on B.Cu: R0..G6 rows pass north of PS1's +5V pin (134.8, 87.5) and drop into their pads; G7/B0/B1 go down the pin's
# west side and run under it; the syncs drop west of it; B4..B7 run along the south strip (y 95.6..96.8) into the pads' south
# ends; B2/B3 stay on F to vias just south of their pads (B stubs into the pad south ends).
FCOLS = ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "B0",
         "DE", "PCLK", "HSYNC", "VSYNC", "B1", "B4", "B5", "B6", "B7"]                 # F columns east -> west
FROW = {nm: i for i, nm in enumerate(FCOLS[:17])}
FROW.update({"B1": 17, "PCLK": 18, "HSYNC": 19, "VSYNC": 20, "DE": 21, "B7": 22, "B6": 23, "B5": 24, "B4": 25})
YF0, PF = 78.2, 0.6                                                    # field rows (via y), 0.6 pitch
GAPW = 1.25                                                            # column gap that leaves a GND pocket
GAPS = [0.6 if (i % 3) != 1 else GAPW for i in range(len(FCOLS) - 1)]  # east -> west gaps between consecutive columns
GAPS = FIELD_GAPS if "FIELD_GAPS" in globals() else GAPS
XB7 = 100.75                                                           # west-most column (1 mm from R123's courtyard)
XCOL = {}
x = XB7
for i in range(len(FCOLS) - 1, -1, -1):
    XCOL[FCOLS[i]] = round(x, 4)
    if i: x += GAPS[i - 1]
X0F = XCOL["R0"]
XCOL["B3"], XCOL["B2"] = round(X0F + 0.6, 4), round(X0F + 1.0, 4)      # F-through lines east of the field
YFR = {nm: round(YF0 + PF * r, 4) for nm, r in FROW.items()}
TROW = {nm: round(80.3 + 0.4 * r, 4) for nm, r in FROW.items() if r <= 21}   # B rows at J10 (0.4 pitch)
CP0 = 52.04                                                            # x - y of B2's SE diagonal (0.75 off the /ZCD diagonal)
CPK = {nm: CP0 - PC * math.sqrt(2) * k for k, nm in enumerate(CORR)}
def fpath(nm, yend):
    """corridor row east -> (SE diagonal) -> south to yend on the line's column"""
    k = CORR.index(nm); yk = YC[nm]; xc = XCOL[nm]; c = CPK[nm]; sk = c + yk
    pts = list(ESC[nm])
    if xc > sk + 0.5:
        pts += [(round(sk, 4), yk), (xc, round(xc - c, 4)), (xc, yend)]
    else:
        pts += [(round(xc - 0.5, 4), yk), (xc, round(yk + 0.5, 4)), (xc, yend)]
    return pts
VIAS = {}
FIELD = FCOLS[:22]                                                     # B4..B7 pass the field on F (south-band vias)
for nm in FIELD:
    R.track(D + nm, "F", fpath(nm, YFR[nm]), WS); R.via(D + nm, XCOL[nm], YFR[nm], **V6); VIAS[nm] = (XCOL[nm], YFR[nm])

# ---- B rows east from the field, 45 deg jog to the J10 row pitch (0.4) east of the F-through columns
XJ = round(X0F + 1.6, 4)
def jog(y0, y1, x0):
    """horizontal at y0 from x0 to XJ, then 45 deg to y1, return points"""
    if abs(y1 - y0) < 1e-6: return [(XJ, y0)]
    return [(XJ, y0), (round(XJ + abs(y1 - y0), 4), y1)]
JX = {}                                                                  # J10 pad x per short name
for n, net, xx, yy in R.pads_of("J10"):
    if net.startswith(D): JX[net.split("/")[-1]] = xx
JY = 91.725
BR = {}
for nm, r in FROW.items():
    if r > 21: continue
    vx, vy = VIAS[nm]; t = TROW[nm]
    BR[nm] = [(vx, vy)] + jog(vy, t, vx)
# R0..G6: east above the pin, drop into the pads
for nm in FCOLS[:15]:
    xp = JX[nm]; t = TROW[nm]
    BR[nm] += [(round(xp - 0.5, 4), t), (xp, round(t + 0.5, 4)), (xp, JY)]
# G7 / B0 / B1: down the pin's west side, under the pin, into the pads
for nm, xd, yu in (("G7", 133.3, 89.3), ("B0", 132.9, 89.7), ("B1", 132.5, 90.1)):   # PS1.4 pad x 133.66..135.94, y 86.5..88.5
    xp = JX[nm]; t = TROW[nm]
    BR[nm] += [(round(xd - 0.5, 4), t), (xd, round(t + 0.5, 4)), (xd, round(yu - 0.5, 4)), (round(xd + 0.5, 4), yu),
               (round(xp - 0.5, 4), yu), (xp, round(yu + 0.5, 4)), (xp, JY)]
# syncs: drop west of the pin
for nm in ("PCLK", "HSYNC", "VSYNC", "DE"):
    xp = JX[nm]; t = TROW[nm]
    BR[nm] += [(round(xp - 0.5, 4), t), (xp, round(t + 0.5, 4)), (xp, JY)]
for nm, pts in BR.items():
    R.track(D + nm, "B", pts, WS)
# ---- B2..B7: F past the field, east under J10's pad row (F over the B.Cu pads, south of C2), south into a via row at
# y 94.2 just south of the pads (0.8 pitch), B.Cu stubs north into the pad south ends; GND return vias at y 95.05 between them
# (VLED pair on B.Cu at y >= 96.05 stays clear).  F rows north -> south B2..B7, the south-most turns first.
SROW = {"B2": 91.0, "B3": 91.4, "B4": 91.8, "B5": 92.2, "B6": 92.6, "B7": 93.0}
SVX = {"B7": 131.15, "B6": 131.95, "B5": 132.75, "B4": 133.55, "B3": 134.35, "B2": 135.15}
SVY = 94.2
for nm in ("B2", "B3", "B4", "B5", "B6", "B7"):
    xc = XCOL[nm]; yr = SROW[nm]; vx = SVX[nm]
    pts = fpath(nm, round(yr - 0.5, 4)) + [(round(xc + 0.5, 4), yr), (round(vx - 0.5, 4), yr), (vx, round(yr + 0.5, 4)), (vx, SVY)]
    R.track(D + nm, "F", pts, WS); R.via(D + nm, vx, SVY, **V6); VIAS[nm] = (vx, SVY)
    xp = JX[nm]; dj = xp - vx
    bp = [(vx, SVY), (vx, 93.6)]
    if abs(dj) > 1e-6: bp += [(xp, round(93.6 - abs(dj), 4))]
    R.track(D + nm, "B", bp + [(xp, JY)], WS)
for gx in (131.55, 133.15, 134.75):
    R.via("GND", gx, 95.05, **V6)

# ---- GND return vias: every RGB/sync signal via gets a GND via within 1.5 mm (greedy: the candidate covering most open vias)
def gnd_vias_all():
    out = [(o[0].centroid.x, o[0].centroid.y) for o in R.obs["F"] if o[1] == "GND" and o[0].geom_type == "Polygon" and abs(o[0].area - 0.2826) < 0.01]
    return out
def place_return_vias(sigvias, rmax=1.5):
    open_ = {nm: v for nm, v in sigvias.items() if not any(math.hypot(gx - v[0], gy - v[1]) <= rmax for gx, gy in gnd_vias_all())}
    while open_:
        gl = gnd_vias_all(); best = None
        for nm, (x0, y0) in open_.items():
            for r in [0.8 + 0.05 * i for i in range(15)]:
                for a in range(0, 360, 6):
                    gx, gy = round(x0 + r * math.cos(math.radians(a)), 3), round(y0 + r * math.sin(math.radians(a)), 3)
                    if any(math.hypot(gx - qx, gy - qy) < 0.8 for qx, qy in gl): continue
                    if 97.1 <= gx <= 105.0 and gy >= 89.0: continue            # VLED B.Cu corridor (power agent)
                    if gy > 95.1: continue                                     # VLED pair along y >= 95.4 on B.Cu
                    if not R.try_via("GND", gx, gy): continue
                    cov = [n for n, (vx, vy) in open_.items() if math.hypot(gx - vx, gy - vy) <= rmax]
                    sc = (len(cov), -r)
                    if best is None or sc > best[0]: best = (sc, gx, gy, cov)
        if best is None: break
        _, gx, gy, cov = best
        R.via("GND", gx, gy, **V6)
        for n in cov: open_.pop(n)
    return open_
for i, g in enumerate(GAPS[:21]):                                      # pockets of the wide column gaps (cover 3 vias each)
    if g < 1.2: continue
    e, w = FCOLS[i], FCOLS[i + 1]
    for d in (0.5, 0.6, 0.7, 0.8, 0.9):
        gx, gy = round((XCOL[e] + XCOL[w]) / 2, 3), round(YFR[e] - d, 3)
        if R.try_via("GND", gx, gy) and all(math.hypot(gx - qx, gy - qy) >= 0.8 for qx, qy in gnd_vias_all()):
            R.via("GND", gx, gy, **V6); break
MISS = place_return_vias(VIAS)
LOG.append("RGB/sync signal vias: %d, without GND via within 1.5 mm: %s" % (len(VIAS), sorted(MISS)))

STAGE3B_END = len(R.items)
# ================================================================== stage 4 (pass 2): U31 LD1117-1.2 group, BL_PWM crossing, BL_EN link
tab, p2c = P("U31", "2"), (59.8, 92.15)                                  # geom keeps the tab for pad "2"; the centre pin is at y 92.15
R.track("+1V2", "F", [p2c, (59.8, 86.85)], 0.5)                          # centre pin 2 -> tab under the body
R.track("+1V2", "F", [tab, (57.195, tab[1])], 0.5); R.via("+1V2", 57.195, tab[1], **V6)
R.track("+1V2", "B", [(57.195, tab[1]), (57.195, 74.625)], 0.4)          # straight up to pin 46's inner 1V2 via (B ring)
c = P("C337", "1"); R.track("+1V2", "F", [tab, c], 0.5)
c = P("C337", "2"); R.track("GND", "F", [c, (66.6, c[1])], 0.4); R.via("GND", 66.6, c[1], **V6)
c = P("C336", "1"); R.track("+1V2", "F", [p2c, (59.8, 94.05), (c[0], 95.0)], 0.5)
c = P("C336", "2"); R.track("GND", "F", [c, (61.75, c[1])], 0.4); R.via("GND", 61.75, c[1], **V6)
g = P("U31", "1"); R.track("GND", "F", [g, (g[0], 94.2)], 0.5); R.via("GND", g[0], 94.2, **V6)
i3, c5 = P("U31", "3"), P("C335", "1")
R.track("+3V3", "F", [i3, (round(c5[0] - (c5[1] - i3[1]), 4), i3[1]), c5], 0.5)
R.track("+3V3", "F", [c5, (c5[0], 94.45)], 0.5); R.via("+3V3", c5[0], 94.45, **V6)
c = P("C335", "2"); R.track("GND", "F", [c, (c[0], 94.45)], 0.4); R.via("GND", c[0], 94.45, **V6)
# BL_PWM: pocket via (59.4, 79.6) -> B.Cu under the RGB rows -> via -> R128.1; BL_EN: R128.2 -> R127.1 (the power agent brings
# BL_EN from U11.4 on B.Cu to the via at (66.6, 89.91) and F to R128.2); R127.2 -> GND via
r1 = P("R128", "1")
R.track(D + "BL_PWM", "B", [(59.4, 79.6), (59.4, 83.0), (64.4, 88.0)], WS); R.via(D + "BL_PWM", 64.4, 88.0, **V6)
R.track(D + "BL_PWM", "F", [(64.4, 88.0), (round(r1[0] - (r1[1] - 88.0), 4), 88.0), r1], WS)
R.track(D + "BL_EN", "F", [P("R128", "2"), P("R127", "1")], WS)
g = P("R127", "2"); R.track("GND", "F", [g, (66.55, g[1])], 0.4); R.via("GND", 66.55, g[1], **V6)

# ================================================================== stage 5 (pass 2): J10 GND pins, TFT_VDD
for pin, path, v in (("36", [(127.9, 89.9)], (127.9, 89.9)), ("29", [(131.4, 90.1), (131.75, 89.75)], (131.75, 89.75)),
                     ("3", [(144.4, 89.8), (144.6, 89.6)], (144.6, 89.6))):
    R.track("GND", "B", [P("J10", pin)] + path, WS); R.via("GND", v[0], v[1], **V6)
TV = D + "TFT_VDD"; VT = (143.6, 93.75)
R.via(TV, VT[0], VT[1], d=0.9, drill=0.45)
R.track(TV, "B", [VT, (143.9, 93.45), P("J10", "4")], 0.3)
R.track(TV, "F", [P("C122", "1"), (140.8, 93.75), VT, (147.3, 93.75), P("R125", "2")], 0.6)
R.track(TV, "F", [P("C123", "1"), (142.6, 93.75)], 0.6)
c = P("C123", "2"); R.track("GND", "F", [c, (141.85, c[1])], 0.4); R.via("GND", 141.85, c[1], **V6)
c = P("C122", "2"); R.track("GND", "F", [c, (140.2, c[1]), (139.6, 94.95)], 0.4); R.via("GND", 139.6, 94.95, **V6)
c = P("R125", "1"); R.track("+3V3", "F", [c, (round(c[0] + 96.0 - c[1], 4), 96.0), (148.5, 96.0)], 0.4); R.via("+3V3", 148.5, 96.0, **V6)

# ================================================================== stage 6 (pass 2): J11 touch block, I2C, TP_INT, LCD_RST
# pass-1 signals geometry ESP32 -> pull-ups -> U20 kept (I2C top vias (31.45, 60.75) / (30.7, 60.0), U20 vias (32.85, 77.1) /
# (30.7, 78.6)); the J11 branches leave the top vias on B.Cu as in pass 1 and come down x 40.25 / 41.0 next to TP_INT (39.5)
# and LCD_RST (41.75); at y 83.3 the four columns jog SE to x 45.25..47.5, pass east of J11's mounting pad and enter the pad
# south ends from rows y 96.0..97.2 (this turns the column order into J11's pin order).
SD, SC = "I2C_SDA", "I2C_SCL"
R.track(SD, "F", [(23.23, 41.25), (23.23, 41.75), (23.98, 42.5), (28.99, 42.5), (28.99, 42.7), (29.49, 43.2), (30.95, 43.2), (31.45, 43.7), (31.45, 60.75)], WS)
R.via(SD, 31.45, 60.75, **V6)
R.track(SD, "B", [(31.45, 60.75), (31.45, 75.7), (32.85, 77.1)], WS); R.via(SD, 32.85, 77.1, **V6)
R.track(SD, "F", [(32.85, 77.1), (32.85, 81.6), (32.45, 82.0), (31.7, 82.0)], WS)
R.track(SC, "F", [(25.75, 45.555), (28.945, 45.555), (28.99, 45.6), (28.99, 45.8), (29.49, 46.3), (30.2, 46.3), (30.7, 46.8), (30.7, 60.0)], WS)
R.via(SC, 30.7, 60.0, **V6)
R.track(SC, "B", [(30.7, 60.0), (30.7, 78.6)], WS); R.via(SC, 30.7, 78.6, **V6)
R.track(SC, "F", [(30.7, 78.6), (30.7, 81.0), (31.2, 81.5), (31.7, 81.5)], WS)
TI = "TP_INT"
R.track(TI, "F", [(16.88, 58.75), (16.88, 65.1), (17.63, 65.85), (32.6, 65.85)], WS); R.via(TI, 32.6, 65.85, **V6)
YS4 = 83.3
DJ = {TI: 5.75, "I2C_SDA": 5.75, "I2C_SCL": 6.3, "LCD_RST": 6.3}   # 1.3 mm gap SDA|SCL after the jog: GND return via
J11C = {TI: (39.5, 96.0, "3"), SD: (40.25, 96.45, "4"), SC: (41.0, 96.9, "5"), "LCD_RST": (41.75, 97.35, "6")}   # 0.45 pitch (Default class)
HEAD = {TI: [(32.6, 65.85), (39.0, 65.85), (39.5, 66.35)], SD: [(31.45, 60.75), (39.75, 60.75), (40.25, 61.25)],
        SC: [(30.7, 60.0), (40.5, 60.0), (41.0, 60.5)], "LCD_RST": [(28.6, 59.3), (41.25, 59.3), (41.75, 59.8)]}
for net, (xc, yr, pin) in J11C.items():
    x2 = round(xc + DJ[net], 4); xp, yp = P("J11", pin)
    R.track(net, "B", HEAD[net] + [(xc, YS4), (x2, round(YS4 + DJ[net], 4)), (x2, round(yr - 0.5, 4)), (round(x2 - 0.5, 4), yr),
                                   (round(xp + 0.5, 4), yr), (xp, round(yr - 0.5, 4)), (xp, yp)], WS)
# TVS on SDA / SCL: vias on their columns, F stubs east to the diode pads; diode GND pads -> vias
for net, ref, vy in ((SD, "D112", 91.3), (SC, "D113", 93.4)):
    xc = J11C[net][0] + DJ[net]; R.via(net, xc, vy, **V6)
    R.track(net, "F", [(xc, vy), P(ref, "2")], WS)
    g = P(ref, "1"); R.track("GND", "F", [g, (g[0], round(vy - 1.0, 4))], 0.4); R.via("GND", g[0], round(vy - 1.0, 4), **V6)
# TP_VDD (J11.1) and GND (J11.2) from the north; R129 (3V3 -> TP_VDD), C126 at the via
TPV = D + "TP_VDD"
R.track(TPV, "B", [P("J11", "1"), (41.55, 90.2), (41.85, 89.9)], WS); R.via(TPV, 41.85, 89.9, **V6)
R.track(TPV, "F", [P("C126", "1"), (41.85, 89.9), (41.3, 89.35), P("R129", "2")], WS)
R.track("GND", "B", [P("J11", "2"), (41.05, 90.25), (40.5, 89.7)], WS); R.via("GND", 40.5, 89.7, **V6)
c = P("C126", "2"); R.track("GND", "F", [c, (c[0], 90.9)], 0.4); R.via("GND", c[0], 90.9, **V6)
c = P("R129", "1"); R.track("+3V3", "F", [c, (40.4, c[1])], 0.4); R.via("+3V3", 40.4, c[1], **V6)
R.via("GND", 46.65, 92.35, **V6)                                    # between the SDA and SCL columns
SVIAS = {"%s@%d" % (t["net"], i): (t["x"] - 20, t["y"] - 20) for i, t in enumerate(R.items) if t["via"] and t["net"] in (SD, SC, TI)}
MISS2 = place_return_vias(SVIAS)
LOG.append("I2C/TP_INT vias: %d, without GND via within 1.5 mm: %s" % (len(SVIAS), sorted(MISS2)))


# ================================================================== save / check
R.save("tracks_display.json")
for l in LOG: print(l)
MYNETS = sorted({t["net"] for t in R.items} - {"GND", "+3V3", "+5V"}) + ["I2C_SDA", "I2C_SCL", "TP_INT", D + "TP_VDD", D + "TFT_VDD", D + "BL_EN"]
if "--check" in sys.argv:
    R.check("tracks_display.json", nets=sorted(set(MYNETS)), extra_json=XTRA, out="check_display.kicad_pcb", show=40)
