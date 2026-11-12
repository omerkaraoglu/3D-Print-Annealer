"""Display region, layout pass 2 (Rev3.0).  Hand routing of: U10 SSD1963 power fan-out + decoupling (pass-1 stage 1, unchanged),
ESP32 -> SSD1963 8080 bus (pass-1 stage 2, unchanged), RGB/sync fan-in U10 -> J10 (new: J10 at (135.65, 94.6) B.Cu),
U31 LD1117-1.2 + 1V2 feed, J10 companions (TFT_VDD, GND), BL_PWM/BL_EN stubs at R128/R127, J11 touch block (I2C, TP_INT,
TP_VDD, LCD_RST).  Idempotent: rebuilds everything and writes tracks_display.json.  Local board mm.
Pass 2b (In1 anti-pad web rule, EMI rule 2 / IPC-2221C 9.1.4.1: non-GND via pitch >= 1.35 mm, GND/non-GND >= 1.10 mm):
  U10 1V2 pins tie to an F.Cu ring under the die (B.Cu ring removed), 3V3/GND keep one via per pin on LP-solved lanes
  (plan_lanes), pin 54 shares pin 58's outward via; down-leg field vias raised up their columns (RAISE) with pocket GND vias;
  sync columns PCLK|HSYNC 1.25 apart; J10 via field as a gable; LCD_RST / I2C_SDA vias nudged; C118 shares C121's via.
  Every via placed by a search (try_via) is checked against the web rule (disp_web.Web).
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
# pass 2b: In1 anti-pad web rule (EMI rule 2): every via placed by a search (try_via) must keep the GND-plane web >= 0.25 mm
from disp_web import Web, solve_lanes
WEBCHK = Web(R, XTRA)
_try_via0 = R.try_via
R.try_via = lambda net, x, y, d=0.6, esc=False: _try_via0(net, x, y, d, esc) and WEBCHK.ok(net, x, y, d)
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
    R.obs["F"].append((_LS([(cx, cy), (cx + 2.0 * ux, cy + 2.0 * uy)]), "<bis>"))     # corner bisectors: no stub crosses them
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
def plan_side(sd, pins, d=ROWA):          # pass 1 planner (0.8 mm via ring), superseded by plan_lanes in pass 2b; kept for reference
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
OUT_X54 = True     # pass 2b: pin 54 (3V3) leaves outward and shares pin 58's via (bottom side lane budget, see plan_lanes)
CAP_FED = {"97", "100"}                                                     # 3V3 corner/top pins fed through C116 / C115 (stage 4)
OUTWARD_GND = set(OUT_L) | set(OUT_X) | CAP_FED | {"54"}
# ---- pass 2b (In1 anti-pad web rule): per-pin vias for all three rails cannot keep 1.35 mm (non-GND) / 1.10 mm (GND/non-GND)
# along a 8 mm side (left side: 9 non-GND + 2 GND vias).  The 1V2 pins therefore tie to an F.Cu ring under the die (inset 3.0,
# chamfered) by straight stubs; only 3V3 and GND keep a per-pin via in one row at inset 2.3.  Lane positions along each side come
# from an LP (disp_web.solve_lanes): pin order kept, via/via pitch by net, 0.56 mm between a via and a stub passing it,
# per-corner margins so the end vias of two sides also keep the pitch.  Pin 46's stub continues to a 1V2 tie via (U31 feed, B.Cu).
RING = 3.0; RINGC = 0.5; RINGW = 0.4
RINGPTS = [(IN_L + RING, IN_T + RING + RINGC), (IN_L + RING + RINGC, IN_T + RING), (IN_R - RING - RINGC, IN_T + RING), (IN_R - RING, IN_T + RING + RINGC),
           (IN_R - RING, IN_B - RING - RINGC), (IN_R - RING - RINGC, IN_B - RING), (IN_L + RING + RINGC, IN_B - RING), (IN_L + RING, IN_B - RING - RINGC),
           (IN_L + RING, IN_T + RING + RINGC)]
TIE_IN = 4.3                                                                 # 1V2 tie via (pin 46 lane) inset
MARG = {("T", "lo"): 0.4, ("L", "lo"): 1.0, ("T", "hi"): 1.0, ("Ri", "lo"): 0.5, ("L", "hi"): 1.25, ("Bo", "lo"): 0.55, ("Bo", "hi"): 0.93, ("Ri", "hi"): 0.62}
STUB_AT = {}
def ring_hit(sd, t):
    from shapely.geometry import LineString as _L3, Point as _P3
    a, b = ipt(sd, t, 0.0), ipt(sd, t, 6.9)
    xs = _L3([a, b]).intersection(_L3(RINGPTS))
    if xs.geom_type == "Point": pts = [xs]
    elif xs.geom_type == "LineString": pts = [_P3(c) for c in xs.coords]          # lane on the ring side line: its nearer end
    else: pts = [g if g.geom_type == "Point" else _P3(g.coords[0]) for g in xs.geoms]
    p = min(pts, key=lambda q: _P3(a).distance(q))
    return (round(p.x, 4), round(p.y, 4))
def plan_lanes(sd, pins, d=ROWA):
    pins = sorted(pins, key=sval)
    kinds = [("sB" if n == "46" else "s") if u10[n] == "+1V2" else "v" + u10[n] for n in pins]
    lo, hi = SIDE_LO[sd] + d + MARG[(sd, "lo")], SIDE_HI[sd] - d - MARG[(sd, "hi")]
    t = solve_lanes([sval(n) for n in pins], kinds, lo, hi, SIDE_LO[sd] + RING, SIDE_HI[sd] - RING)
    if t is None: LOG.append("lane LP infeasible on side %s" % sd); return list(pins)
    neg = [n for n, tt in zip(pins, t) if tt < sval(n) - 1e-6]; pos = [n for n, tt in zip(pins, t) if tt > sval(n) + 1e-6]
    e = {}; sv = {round(sval(n), 2): n for n in pins}
    for n in neg:
        p = sv.get(round(sval(n) - 0.4, 2)); e[n] = e[p] + 0.2 if p in e and p in neg else 0.35
    for n in reversed(pos):
        p = sv.get(round(sval(n) + 0.4, 2)); e[n] = e[p] + 0.2 if p in e and p in pos else 0.35
    bad = []
    for n, tt, k in zip(pins, t, kinds):
        net = u10[n]; s0 = sval(n); dl = round(tt - s0, 4)
        head = [P("U10", n)] if abs(dl) < 1e-6 else [P("U10", n), ipt(sd, s0, e[n]), ipt(sd, tt, e[n] + abs(dl))]
        if k[0] == "v":
            vp = ipt(sd, tt, d); pts = head + [vp]
            if abs(dl) > 1e-6 and e[n] + abs(dl) > d - 0.05: bad.append(n); LOG.append("jog too deep pin %s" % n); continue
            if R.try_via(net, *vp, esc=True) and R.try_track(net, "F", pts, WS, esc=True):
                R.track(net, "F", pts, WS); R.via(net, *vp, **V6); VIA_AT[n] = (d, dl, vp, e[n] if abs(dl) > 1e-6 else d)
            else: bad.append(n); LOG.append("lane via blocked pin %s at %s" % (n, vp))
        else:
            end = ring_hit(sd, tt); pts = head + [end]
            if k == "sB": pts += [ipt(sd, tt, TIE_IN)]
            if R.try_track(net, "F", pts, WS, esc=True):
                R.track(net, "F", pts, WS); STUB_AT[n] = (tt, pts[-1])
            else: bad.append(n); LOG.append("1V2 stub blocked pin %s lane %.3f" % (n, tt))
    return bad
FAILED = []
for sd in ("L", "Bo", "Ri", "T"):
    pins = [n for n, net in u10.items() if side(n) == sd and net in ("GND", "+3V3", "+1V2") and int(n) not in CORNER and n not in OUTWARD_GND]
    FAILED += plan_lanes(sd, pins)
if OUT_X54:
    R.track("+3V3", "F", [P("U10", 54), (60.2, 78.7), (61.0, 79.5), (61.5, 79.5)], WS)
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
# 1.2 V ring (pass 2b): F.Cu under the die at inset 3.0 (chamfered), every inner 1V2 pin joins it by its stub (plan_lanes); the
# B.Cu side keeps the outside network (pin 1 / pin 32 / C117 / C118 / C120 / C121 on x 45.4) and the U31 feed into the tie via
R.track("+1V2", "F", RINGPTS, RINGW)
# bottom-right corner pin 64 via -> B.Cu west under the bottom pad ring -> the U31 feed lane (pin 46 lane)
v64 = VIA_AT["64"][2]; XT = STUB_AT["46"][0]; YT = IN_B - TIE_IN
R.via("+1V2", XT, YT, **V6)
R.track("+1V2", "B", [v64, (round(v64[0] - (76.0 - v64[1]), 4), 76.0), (XT, 76.0)], 0.3)
v32 = VIA_AT["32"][2]; c117v = (P("C117", "1")[0], 69.9)
R.track("+1V2", "B", [c117v, (45.4, 70.58), (45.4, VIA_AT["32"][2][1]), (45.4, 78.775), (45.4, 81.975)], 0.4)
c8 = P("C118", "1"); R.track("+1V2", "F", [c8, (round(c8[0] + 81.975 - c8[1], 4), 81.975), (46.15, 81.975)], 0.4)   # pass 2b: shares C121's via
R.track("+1V2", "B", [v32, (45.4, v32[1])], 0.4)
for ref, y in (("C120", 78.775), ("C121", 81.975)):
    c = P(ref, "1"); R.track("+1V2", "F", [c, (46.15, c[1])], 0.4); R.via("+1V2", 46.15, c[1], **V6); R.track("+1V2", "B", [(46.15, c[1]), (45.4, c[1])], 0.4)
    g = P(ref, "2"); R.track("GND", "F", [g, (46.2, g[1])], 0.4); R.via("GND", 46.2, g[1], **V6)
R.track("GND", "F", [P("C118", "2"), (46.2, P("C118", "2")[1]), (46.2, P("C121", "2")[1])], 0.4)


# LCD_RST (now module pin 28 / R111) to the touch connector J11.6: under the module on B.Cu, across the signals' B band on F,
# then the former signals corridor (B.Cu y 59.3, x 41.75 column, y 95.85 under J10/J11) into J11.6
NR = "LCD_RST"; p28 = P("U3", 28); j6 = P("J11", 6)
R.track(NR, "F", [p28, (p28[0], 42.85)], WS); R.via(NR, p28[0], 42.85, **V6)
R.track(NR, "B", [(p28[0], 42.85), (27.75, 42.85), (28.3, 43.4), (28.3, 55.15)], WS); R.via(NR, 28.3, 55.15, **V6)   # pass 2b: 0.45 N (web to the GND via at (27.3, 55.715))
R.track(NR, "F", [(28.3, 55.15), (28.3, 59.6)], WS); R.via(NR, 28.3, 59.6, **V6)
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
YC = {nm: round(Y0C + PC * k + (0.2 if k == 1 else 0.4 if k >= 2 else 0.0), 4) for k, nm in enumerate(CORR)}   # pass 4: B2|B3|R0 at 0.6 (in-row dive vias of B2/B3 under the /ZCD line at y 59.9)
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

# ================================================================== stage 3b (pass 4b): corridor -> 33R arrays -> re-sort zone -> J10 (top side)
# J10 is on F.Cu and the ribbon enters its pads from the north.  Lane check (p4_lanes.py): 59 crossings, 22 of 28 lines
# crossing-free (uncrossed R/B mapping: 187 / 13) -> B2, B3 and the four syncs change layer once each way (12 vias).
# pass 4b: RN1..RN7 are grouped in U10 order (schematic) and sit at the end of the corridor, the first place where a 0.5-mm-pitch
# 28-line band fits (between U10 and x 99.5 the corridor is boxed in by /ZCD at y 59.9 and the boost block: VLED_N y 72.6,
# +5V via (82.6, 73.3), R126 -> 11.8 mm < 13.75 mm).  Fan (x 99.6..106.6): 0.4 -> 0.5 mm and down to R0 = 64.4 (below /ZCD's
# descent at x 113..125); arrays in two staggered columns; then, on the panel side, the re-sort zone (x 111..119); then one 45-deg
# turn into the J10 pads (rows -> 0.4 mm perpendicular on the diagonal, R0's diagonal passes x 130 at y 70.2).
TN = lambda nm: D + nm + "_T"                         # controller side (U10 -> array pins 1-4)
PN = lambda nm: D + nm                                # panel side (array pins 5-8 -> J10)
JORD = ["R%d" % i for i in range(8)] + ["G%d" % i for i in range(8)] + ["B%d" % i for i in range(8)] + ["PCLK", "HSYNC", "VSYNC", "DE"]
YA = {nm: round(63.4 + 0.5 * k, 4) for k, nm in enumerate(CORR)}          # array rows (U10 order)
RNW, RNE = {}, {}                                                        # line -> array west (U10 side) / east (panel side) pad
for k in range(1, 8):
    for num, net, xx, yy in R.pads_of("RN%d" % k):
        nm = net.split("/")[-1]
        (RNW if nm.endswith("_T") else RNE)[nm.replace("_T", "")] = (xx, yy)
def jog(pts, xs, yto):
    """continue east from pts[-1] to xs, then 45 deg to yto"""
    x, y = pts[-1]; d = yto - y
    if abs(d) < 1e-6: return pts
    return pts + [(round(xs, 4), y), (round(xs + abs(d), 4), round(yto, 4))]
# ---- controller side: corridor -> fan (lower lines start 0.17 mm earlier) -> array west pad
for k, nm in enumerate(CORR):
    R.track(TN(nm), "F", jog(list(ESC[nm]), 103.85 - 0.17 * max(0, k - 2), YA[nm]) + [RNW[nm]], WS)
PATH = {nm: [RNE[nm]] for nm in CORR}                                    # panel-side paths start at the array east pads
VIAS = {}
# ---- zone 1: B2/B3 dive at the top edge (0.5 mm up-jog, vias west of /ZCD's descent) and come up between B1 and B4
BTOP = {"B2": ((113.0, 113.5, 62.9), [(113.5, 68.0), (117.6, 72.1)], (117.6, 76.65)),
        "B3": ((114.35, 114.85, 63.4), [(114.85, 67.5), (118.85, 71.5)], (118.85, 77.25))}
for nm, ((xj, xv, yv), mid, low) in BTOP.items():
    p = PATH[nm] + [(xj, YA[nm]), (xv, yv)]
    R.track(PN(nm), "F", p, WS); R.via(PN(nm), xv, yv, **V6)
    R.track(PN(nm), "B", [(xv, yv)] + mid + [low], WS); R.via(PN(nm), *low, **V6)
    PATH[nm] = [low]; VIAS[nm + "u"] = (xv, yv); VIAS[nm + "l"] = low
# ---- zone 2: lower band down (B1 1.15, B4..B7 3.45), syncs spread to 0.6 mm and dip under them in a via staircase
PATH["B1"] = jog(PATH["B1"], 111.2, 76.05)
for i, nm in enumerate(("B7", "B6", "B5", "B4")):
    PATH[nm] = jog(PATH[nm], 108.6 + 0.17 * i, round(YA[nm] + 3.45, 4))
SUP = {"VSYNC": (111.3, 116.85, 75.45), "HSYNC": (111.47, 115.6, 74.85), "PCLK": (111.64, 114.35, 74.25), "DE": (111.81, 113.1, 73.65)}
SLO = {"PCLK": 80.95, "HSYNC": 81.95, "VSYNC": 82.95, "DE": 84.2}
for nm, (xs, xu, yu) in SUP.items():
    p = jog(PATH[nm], xs, yu) + [(xu, yu)]
    R.track(PN(nm), "F", p, WS); R.via(PN(nm), xu, yu, **V6)
    R.track(PN(nm), "B", [(xu, yu), (xu, SLO[nm])], WS); R.via(PN(nm), xu, SLO[nm], **V6)
    PATH[nm] = [(xu, SLO[nm])]; VIAS[nm + "u"] = (xu, yu); VIAS[nm + "l"] = (xu, SLO[nm])
# ---- turn: each row east to its corner (c_j + y), 45 deg to its J10 pad column (c_j = 59.8 - 0.58 j, J10 order), down
JX = {}
for n, net, xx, yy in R.pads_of("J10"):
    if net.startswith(D): JX[net.split("/")[-1]] = xx
JY = 89.125
C0T, DCT = 59.8, 0.58
for j, nm in enumerate(JORD):
    c = C0T - DCT * j; y0 = PATH[nm][-1][1]; xp = JX[nm]
    R.track(PN(nm), "F", PATH[nm] + [(round(c + y0, 4), y0), (xp, round(xp - c, 4)), (xp, JY)], WS)
# ---- GND return vias of the twelve zone vias (In1 web: >= 1.1 mm from every signal via, <= 1.5 mm from its own)
ZGND = [(114.25, 73.025), (116.85, 74.2),                        # sync upper vias (DE+PCLK, HSYNC+VSYNC)
        (118.225, 75.425), (118.225, 78.2),                      # B2 / B3 lower vias (between their B.Cu columns)
        (113.725, 81.95), (114.975, 82.95)]                      # PCLK / HSYNC lower vias
for gx, gy in ZGND:
    if not R.try_via("GND", gx, gy): LOG.append("zone GND via (%.3f, %.3f) fails the checks" % (gx, gy))
    R.via("GND", gx, gy, **V6)
def gnd_vias_all():
    return [(o[0].centroid.x, o[0].centroid.y) for o in R.obs["F"] if o[1] == "GND" and o[0].geom_type == "Polygon" and abs(o[0].area - 0.2826) < 0.01]
def place_return_vias(sigvias, rmax=1.5):
    open_ = {nm: v for nm, v in sigvias.items() if not any(math.hypot(gx - v[0], gy - v[1]) <= rmax for gx, gy in gnd_vias_all())}
    while open_:
        gl = gnd_vias_all(); best = None
        for nm, (x0, y0) in open_.items():
            for r in [1.12 + 0.04 * i for i in range(10)]:
                for a in range(0, 360, 6):
                    gx, gy = round(x0 + r * math.cos(math.radians(a)), 3), round(y0 + r * math.sin(math.radians(a)), 3)
                    if any(math.hypot(gx - qx, gy - qy) < 0.8 for qx, qy in gl): continue
                    if not R.try_via("GND", gx, gy): continue
                    cov = [n for n, (vx, vy) in open_.items() if math.hypot(gx - vx, gy - vy) <= rmax]
                    sc = (len(cov), -r)
                    if best is None or sc > best[0]: best = (sc, gx, gy, cov)
        if best is None: break
        _, gx, gy, cov = best
        R.via("GND", gx, gy, **V6)
        for n in cov: open_.pop(n)
    return open_
MISS = place_return_vias(VIAS)
LOG.append("RGB/sync zone vias: %d, without GND via within 1.5 mm: %s" % (len(VIAS), sorted(MISS)))

STAGE3B_END = len(R.items)
# ================================================================== stage 4 (pass 2): U31 LD1117-1.2 group, BL_PWM crossing, BL_EN link
tab, p2c = P("U31", "2"), (59.8, 92.15)                                  # geom keeps the tab for pad "2"; the centre pin is at y 92.15
R.track("+1V2", "F", [p2c, (59.8, 86.85)], 0.5)                          # centre pin 2 -> tab under the body
R.track("+1V2", "F", [tab, (XT, tab[1])], 0.5); R.via("+1V2", XT, tab[1], **V6)
R.track("+1V2", "B", [(XT, tab[1]), (XT, YT)], 0.3)                      # pass 2b: straight up the pin-46 lane to the 1V2 tie via
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

# ================================================================== stage 5 (pass 4): J10 (top side) GND pins, RF caps, TFT_VDD
# GND pins 36 / 29 / 3: short F stubs south from the pad centres to GND vias under the connector body (pin 3's via steps west of
# the power agent's VLED_P neck at x 144.9).  VLED_N / VLED_P (pins 1 / 2, fed from the south by the power agent's under-body
# vias at (146.0, 93.5) / (145.1, 94.6)): north stubs and nested runs east at y 87.2 (N) / 86.24 (P) across C129 (100n P-N),
# C130 (1n P-GND), C131 (1n N-GND).  TFT_VDD (pin 4): straight north along x 143.9 through C132 (1n), C123 (100n), C122 (10u)
# to R125 (0R from +3V3, its +3V3 via outside the In2 +5V island).
for pin, path in (("36", [(127.9, 90.95)]), ("29", [(131.4, 90.95)]), ("3", [(144.4, 90.9), (144.0, 91.3)])):
    R.track("GND", "F", [P("J10", pin)] + path, WS); R.via("GND", path[-1][0], path[-1][1], **V6)
VN, VP, TV = D + "VLED_N", D + "VLED_P", D + "TFT_VDD"
WV = 0.28
R.track(VN, "F", [P("J10", "1"), (145.4, 87.2), P("C129", "2"), P("C131", "1")], WV)
R.track(VP, "F", [P("J10", "2"), (144.9, 86.24), P("C129", "1"), P("C130", "1")], WV)
c = P("C130", "2"); R.track("GND", "F", [c, (c[0], 84.45)], 0.4); R.via("GND", c[0], 84.45, **V6)
c = P("C131", "2"); R.track("GND", "F", [c, (c[0], 89.0)], 0.4); R.via("GND", c[0], 89.0, **V6)
R.track(TV, "F", [P("J10", "4"), (143.9, 85.4), (144.4, 84.9), P("C132", "1"), P("C123", "1"), P("C122", "1"), P("R125", "2")], 0.3)
for ref, gx in (("C132", 146.2), ("C123", 146.2), ("C122", 147.15)):
    c = P(ref, "2"); R.track("GND", "F", [c, (gx, c[1])], 0.4); R.via("GND", gx, c[1], **V6)
c = P("R125", "1"); R.track("+3V3", "F", [c, (148.6, c[1])], 0.4); R.via("+3V3", 148.6, c[1], **V6)   # In2 3V3 strip east of the +5V island

# ================================================================== stage 6 (pass 4): J11 (top side) touch block, I2C, TP_INT, LCD_RST
# pass-1 signals geometry ESP32 -> pull-ups -> U20 kept (I2C top vias / U20 vias); the J11 branches come down on B.Cu as in pass 2
# (x 39.5 TP_INT, 40.25 SDA, 41.0 SCL, 41.75 LCD_RST), jog 3.45 mm east at y 79.5 and end in a staircase of vias north of the pad
# row (LCD_RST shallowest / east ... TP_INT deepest / west, 1.3 mm steps): from each via one F.Cu row west and a 45-deg corner into
# its pad (the top-side pad order is the reverse of the B.Cu column order), and one F stub east to its TVS diode.
SD, SC, TI, LR = "I2C_SDA", "I2C_SCL", "TP_INT", "LCD_RST"
R.track(SD, "F", [(23.23, 41.25), (23.23, 41.75), (23.98, 42.5), (28.99, 42.5), (28.99, 42.7), (29.49, 43.2), (30.95, 43.2), (31.45, 43.7), (31.45, 61.15)], WS)
R.via(SD, 31.45, 61.15, **V6)                                        # pass 2b: 0.4 S of pass 1 (1.37 mm from the SCL via)
R.track(SD, "B", [(31.45, 61.15), (31.45, 75.7), (32.85, 77.1)], WS); R.via(SD, 32.85, 77.1, **V6)
R.track(SD, "F", [(32.85, 77.1), (32.85, 81.6), (32.45, 82.0), (31.7, 82.0)], WS)
R.track(SC, "F", [(25.75, 45.555), (28.945, 45.555), (28.99, 45.6), (28.99, 45.8), (29.49, 46.3), (30.2, 46.3), (30.7, 46.8), (30.7, 60.0)], WS)
R.via(SC, 30.7, 60.0, **V6)
R.track(SC, "B", [(30.7, 60.0), (30.7, 78.6)], WS); R.via(SC, 30.7, 78.6, **V6)
R.track(SC, "F", [(30.7, 78.6), (30.7, 81.0), (31.2, 81.5), (31.7, 81.5)], WS)
R.track(TI, "F", [(16.88, 58.75), (16.88, 65.1), (17.63, 65.85), (32.6, 65.85)], WS); R.via(TI, 32.6, 65.85, **V6)
HEAD = {TI: [(32.6, 65.85), (39.0, 65.85), (39.5, 66.35)], SD: [(31.45, 61.15), (31.85, 60.75), (39.75, 60.75), (40.25, 61.25)],
        SC: [(30.7, 60.0), (40.5, 60.0), (41.0, 60.5)], LR: [(28.6, 59.3), (41.25, 59.3), (41.75, 59.8)]}
COLX = {TI: 39.5, SD: 40.25, SC: 41.0, LR: 41.75}
JOGY, DJ = 79.5, 3.45
YV = {LR: 85.0, SC: 86.3, SD: 87.6, TI: 88.9}
TVS = {LR: "D116", SC: "D113", SD: "D112", TI: "D115"}
JPIN = {TI: "3", SD: "4", SC: "5", LR: "6"}
for net in (TI, SD, SC, LR):
    xc = COLX[net]; xv = round(xc + DJ, 4); yv = YV[net]
    R.track(net, "B", HEAD[net] + [(xc, JOGY), (xv, round(JOGY + DJ, 4)), (xv, yv)], WS); R.via(net, xv, yv, **V6)
    xp, yp = P("J11", JPIN[net])
    if net == TI: R.track(net, "F", [(xv, yv), (xp, round(yv + xv - xp, 4)), (xp, yp)], WS)        # SW 45 deg into the pad
    else: R.track(net, "F", [(xv, yv), (round(xp + 0.5, 4), yv), (xp, round(yv + 0.5, 4)), (xp, yp)], WS)
    d = TVS[net]; R.track(net, "F", [(xv, yv), P(d, "2")], WS)
    g = P(d, "1"); R.track("GND", "F", [g, (round(g[0] + 0.85, 4), g[1])], 0.4); R.via("GND", round(g[0] + 0.85, 4), g[1], **V6)
# J11 GND (pin 2) and TP_VDD (pin 1): south stubs under the body to vias; TP_VDD on B.Cu east to its trunk at x 47.0 (C133/C126/R129)
TPV = D + "TP_VDD"
R.track("GND", "F", [P("J11", "2"), (42.85, 91.45), (42.6, 91.7)], WS); R.via("GND", 42.6, 91.7, **V6)
R.track(TPV, "F", [P("J11", "1"), (43.35, 91.9), (43.85, 92.4)], WS); R.via(TPV, 43.85, 92.4, **V6)
R.track(TPV, "B", [(43.85, 92.4), (48.3, 92.4)], 0.3); R.via(TPV, 48.3, 92.4, **V6)
R.track(TPV, "F", [(48.3, 92.4), P("C133", "1"), P("C126", "1"), P("R129", "2")], 0.3)
for ref in ("C133", "C126"):
    c = P(ref, "2"); R.track("GND", "F", [c, (50.1, c[1])], 0.4); R.via("GND", 50.1, c[1], **V6)
c = P("R129", "1"); R.track("+3V3", "F", [c, (51.0, c[1])], 0.4); R.via("+3V3", 51.0, c[1], **V6)
SVIAS = {"%s@%d" % (t["net"], i): (t["x"] - 20, t["y"] - 20) for i, t in enumerate(R.items) if t["via"] and t["net"] in (SD, SC, TI, LR, TPV)}
MISS2 = place_return_vias(SVIAS)
LOG.append("I2C/TP_INT/LCD_RST/TP_VDD vias: %d, without GND via within 1.5 mm: %s" % (len(SVIAS), sorted(MISS2)))


# ================================================================== save / check
R.save("tracks_display.json")
for l in LOG: print(l)
MYNETS = sorted({t["net"] for t in R.items} - {"GND", "+3V3", "+5V"}) + ["I2C_SDA", "I2C_SCL", "TP_INT", D + "TP_VDD", D + "TFT_VDD", D + "BL_EN"]
if "--check" in sys.argv:
    R.check("tracks_display.json", nets=sorted(set(MYNETS)), extra_json=XTRA, out="check_display.kicad_pcb", show=40)
