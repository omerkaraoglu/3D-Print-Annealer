"""LV power region, layout pass 2 (Rev3.0): TPS562201 buck (U30), MIC2288 backlight boost (U11) + input pi filter + damper,
VLED pair to J10, +5V (PSU pin -> C2 -> In2 island -> buck/boost inputs, relay coil feed), +3V3 buck output into In2.
Idempotent: builds every track/via from scratch and writes tracks_power.json.  Local board mm (handroute.py convention).
Run:  python route_power.py [--check] [--stats]
Placement: placement_override_power.py (box x 70..100, y 71..98.5; boost/pi-filter north band, buck south band).

Layer plan
  F.Cu : switch loops, decoupling, pi filter, damper, FB/sense, VLED_P/N up to the pair vias at the boost output.
  B.Cu : the VLED pair (one 0.9/0.45 via each at the boost output, B.Cu all the way to J10 pins 1/2, entering them from the
         south under the connector body), BL_EN hop (U11.4 -> R127/R128), +5V relay-coil feed (island via -> under the RGB
         corridor -> D5.1 / K1.2 as in pass 1).
  In1 GND everywhere; In2 +5V island x 70..140, y 70..98 (every +5V via here is inside it), In2 3V3 outside it: the buck output
  reaches the 3V3 plane by two 0.9 vias at x 67.2/68.4 (west of the island) - the only copper of the block outside its box.
  Pass 4: PS1 sits at the top-right corner (+5V pin (134.8, 47.5)); C2 right under the pin on a 1.5 mm F.Cu bar with three
  island vias (section 7).  J10 is on F.Cu: the VLED pair comes up through two 0.6 vias under its body (section 5).
Inductor inner-layer keep-outs for build_board.py (8 x 8 / 6 x 6 as in pass 1, centred on the parts): L30 (72.3, 86.0, 80.3, 94.0),
  L11 (80.9, 78.35, 86.9, 84.35); no via of this script lies inside either.
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from handroute import Router

R = Router("geom_power.json", placed="rev3_placed_power.kicad_pcb")
P = R.pad
def pad_on(ref, net):
    return [n for (n, nt, x, y) in R.pads_of(ref) if nt == net][0]

W5 = 1.0; WSW = 1.0; WLED = 0.5; WNECK = 0.3; WSIG = 0.25; WGND = 0.4
VP = dict(d=0.9, drill=0.45)      # power via
VS = dict(d=0.6, drill=0.3)       # signal / GND via
def T(net, layer, pts, w): R.track(net, layer, pts, w)
def V(net, x, y, v=VS): R.via(net, x, y, **v)
def gnd_via(pad, vx, vy, mid=None):
    """GND pad -> own 0.6/0.3 via with a 0.4 mm stub (optional 45-degree knee 'mid')"""
    T("GND", "F", [P(*pad)] + ([mid] if mid else []) + [(vx, vy)], WGND); V("GND", vx, vy)
N5 = "+5V"; N33 = "+3V3"
SW = "/Power/BUCK_SW"; BST = "/Power/BUCK_BST"; FB = "/Power/BUCK_FB"
VIN = "/Display/BL_VIN"; BSW = "/Display/BL_SW"; DAMP = "/Display/BL_DAMP"; BFB = "/Display/BL_FB"; BEN = "/Display/BL_EN"
VLP = "/Display/VLED_P"; VLN = "/Display/VLED_N"

# =====================================================================================================================
# 1. MIC2288 boost core.  U11 rot 180 (EN/VIN west, SW/GND/FB east), L11 straight under it, D111 vertical east of it,
#    C125 east of D111.K.  Hot loop: U11.1 -> JB -> D111.A -> D111.K -> C125.1 -> C125.2 -> via -> In1 -> via -> U11.2.
# =====================================================================================================================
u11 = {n: P("U11", n) for n in "12345"}        # 1 SW (85.138,77.95) 2 GND (85.138,77.0) 3 FB (85.138,76.05) 4 EN (82.862,76.05) 5 VIN (82.862,77.95)
l11v = P("L11", "1"); l11s = P("L11", "2")      # BL_VIN (82.288,81.35), BL_SW (85.538,81.35)
d111k = P("D111", "1"); d111a = P("D111", "2")  # VLED_P (88.6,74.35), BL_SW (88.6,78.35)
c125 = P("C125", "1"); c125g = P("C125", "2")   # (91.6,74.35), (91.6,76.25)
JB = (l11s[0], d111a[1])                        # SW junction (85.538, 78.35), 45 deg off U11.1
T(BSW, "F", [u11["1"], JB], 0.6)                # pin neck (0.35 to the GND pin)
T(BSW, "F", [JB, d111a], WSW)
T(BSW, "F", [JB, l11s], WSW)
# U11 GND: east stub -> via between U11 and the D111 body ; C125 GND -> via on the other side of D111 (return under the diode)
GV1 = (86.4, u11["2"][1] - 0.4)
T("GND", "F", [u11["2"], (GV1[0] - 0.4, u11["2"][1]), GV1], WGND); V("GND", *GV1)
T("GND", "F", [c125g, (90.3, c125g[1])], WGND); V("GND", 90.3, c125g[1])
# output: D111.K -> C125.1 (1.0, hot loop) -> D114.K -> VLED_P via (the B.Cu pair starts here)
d114k = P("D114", pad_on("D114", VLP)); d114a = P("D114", pad_on("D114", "GND"))     # (94.2,74.35), (94.2,77.65)
PV = (95.6, d114k[1])                           # VLED_P via
T(VLP, "F", [d111k, c125], 1.0)
T(VLP, "F", [c125, d114k, PV], 0.6); V(VLP, PV[0], PV[1], VP)
gnd_via(("D114", pad_on("D114", "GND")), d114a[0], d114a[1] + 1.25)
# FB: U11.3 straight up to R126.1 (0R) ; Kelvin VLED_N from R122.1 along the box top (y 72.6) to R126.2
r126f = P("R126", "1"); r126n = P("R126", "2")  # (85.138,74.31), (85.138,73.29)
T(BFB, "F", [u11["3"], r126f], WSIG)
r122 = P("R122", "1"); r123 = P("R123", "1")    # VLED_N (96.5,79.088), (98.5,79.088)
YK = 72.6
T(VLN, "F", [r126n, (r126n[0] + (r126n[1] - YK), YK), (r122[0] - 0.5, YK), (r122[0], YK + 0.5), r122], WSIG)
# sense resistors: VLED_N bar with the pair via between the two VLED_N pads ; GND pads joined, two vias west of the pair
NV = (97.7, 77.7)                               # VLED_N via
T(VLN, "F", [r122, (NV[0], r122[1]), r123], WLED)
T(VLN, "F", [(NV[0], r122[1]), NV], WLED); V(VLN, NV[0], NV[1], VP)
r122g = P("R122", "2"); r123g = P("R123", "2")
T("GND", "F", [r123g, r122g], WLED)
gnd_via(("R122", "2"), r122g[0], r122g[1] + 1.35)
gnd_via(("R122", "2"), r122g[0] - 1.25, r122g[1])

# =====================================================================================================================
# 2. Pi filter + damper: +5V -> C127 -> L12 -> BL_VIN node (C124.1, U11.5, L11.1) ; damper R132 + C128 across BL_VIN east of
#    the core (the display agent's RGB sweep from under U10 into the corridor crosses the box's NW corner, x 70..80 / y 71..81)
# =====================================================================================================================
c124 = P("C124", "1"); c124g = P("C124", "2")   # (80.05,79.05), (80.05,80.95)
r132v = P("R132", "1"); r132d = P("R132", "2")  # BL_VIN (85.1375,86.0), BL_DAMP (88.0625,86.0)
c128d = P("C128", "1")                          # (90.8,86.0)
l12v = P("L12", "1"); l12p = P("L12", "2")      # BL_VIN (76.45,80.675), +5V (76.45,83.925)
c127 = P("C127", "1"); c127g = P("C127", "2")   # (72.4,84.25), (72.4,82.35)
T(VIN, "F", [l12v, (l12v[0] + (l12v[1] - c124[1]), c124[1]), c124], W5)
kx = c124[0] + (c124[1] - u11["5"][1])                   # 45 deg up to the VIN pin row
T(VIN, "F", [c124, (kx, u11["5"][1]), u11["5"]], W5)
T(VIN, "F", [u11["5"], (u11["5"][0], l11v[1] - (u11["5"][0] - l11v[0])), l11v], W5)
T(VIN, "F", [l11v, (l11v[0], r132v[1] - (r132v[0] - l11v[0])), r132v], W5)    # L11.1 bottom -> 45 deg -> damper R (under L11.2's pad end)
T(DAMP, "F", [r132d, c128d], 0.5)
gnd_via(("C124", "2"), c124g[0], c124g[1] + 1.35)
gnd_via(("C127", "2"), c127g[0] + 1.1, c127g[1])
c128g = P("C128", pad_on("C128", "GND"))
gnd_via(("C128", pad_on("C128", "GND")), c128g[0], c128g[1] + 1.9)
# +5V: C127.1 -> L12.2 bar (45 deg into the pad centre), two island vias under it (clear of the L30 inner keep-out, y < 86)
T(N5, "F", [c127, (l12p[0] - abs(c127[1] - l12p[1]), c127[1]), l12p], W5)
for x in (c127[0], 74.6):
    T(N5, "F", [(x, c127[1]), (x, 85.45)], W5); V(N5, x, 85.45, VP)

# =====================================================================================================================
# 3. Buck TPS562201 (pass-1 local geometry): U30 rot 0, L30 west, C330/C331 south, C332 north, FB divider south-east
# =====================================================================================================================
u30 = {n: P("U30", n) for n in "123456"}
X, Y = u30["2"][0] + 1.138, u30["2"][1]                  # U30 centre (82.8, 89.5)
l30s = P("L30", "1"); l30o = P("L30", "2")               # SW (78.675,90.0), 3V3 (73.925,90.0)
c332b = P("C332", "1"); c332s = P("C332", "2")           # (83.28,86.7), (82.32,86.7)
J = (X - 2.25, Y)
T(SW, "F", [u30["2"], J], 0.6)
T(SW, "F", [J, (l30s[0] + 0.5, Y), l30s], WSW)
T(SW, "F", [c332s, (X - 1.68, c332s[1]), (X - 2.25, c332s[1] + 0.57), J], 0.4)
T(BST, "F", [c332b, (c332b[0], u30["6"][1] - 0.5 - (u30["6"][0] - c332b[0])), (u30["6"][0], u30["6"][1] - 0.5), u30["6"]], 0.4)
gnd_via(("U30", "1"), u30["1"][0], u30["1"][1] - 0.9)
# input: C330.1/C331.1 bar -> up between the GND pads -> 45 deg into VIN (pin 3); two island vias under the bar ; EN -> own via
c330 = P("C330", "1"); c331 = P("C331", "1")             # (81.3,95.45), (84.3,95.45)
T(N5, "F", [c330, (X, c330[1]), c331], W5)
kv = (X, u30["3"][1] + (X - u30["3"][0]))
T(N5, "F", [(X, c330[1]), kv], W5)
T(N5, "F", [kv, u30["3"]], 0.8)
for (x, y) in (c330, c331):
    T(N5, "F", [(x, y), (x, 96.9)], W5); V(N5, x, 96.9, VP)
T(N5, "F", [u30["5"], (85.55, Y)], 0.5); V(N5, 85.55, Y, VP)
gnd_via(("C330", "2"), c330[0], 92.25)
gnd_via(("C331", "2"), c331[0], 92.25)
# feedback: U30.4 -> 45 deg -> R331.1 -> R330.2 ; R331.2 -> GND via ; R330.1 = 3V3 sense from C334.1 along the bottom edge
r331f = P("R331", "1"); r331g = P("R331", "2"); r330f = P("R330", "2"); r330s = P("R330", "1")
T(FB, "F", [u30["4"], (r331f[0] - (r331f[1] - u30["4"][1]), u30["4"][1]), r331f, r330f], WSIG)
gnd_via(("R331", "2"), r331g[0] + 1.15, r331g[1])
c333 = P("C333", "1"); c334 = P("C334", "1")             # (71.8,96.95), (74.8,96.95)
YS = 97.9
T(N33, "F", [r330s, (88.0, r330s[1] + 0.59), (88.0, YS - 0.6), (87.4, YS), (c334[0] + (YS - c334[1]), YS), c334], WSIG)
# output: L30.2 -> between the cap GND pads -> C333.1/C334.1 bar -> west to two 0.9 vias into the In2 3V3 plane (x < 70)
xo = 73.3
T(N33, "F", [l30o, (xo, l30o[1] + (l30o[0] - xo)), (xo, c333[1])], W5)
X33 = (66.6, 68.4)                                       # pass 4: 1.8 mm apart -> In1 anti-pads (0.7 radius) keep a 0.4 mm web
T(N33, "F", [c334, (xo, c333[1]), c333, (X33[0], c333[1])], W5)
for x in X33: V(N33, x, c333[1], VP)
gnd_via(("C333", "2"), P("C333", "2")[0] - 1.05, P("C333", "2")[1])
gnd_via(("C334", "2"), P("C334", "2")[0] + 1.05, P("C334", "2")[1])
R.save("tracks_power.json")                                   # stage save

# =====================================================================================================================
# 4. +5V relay-coil feed (K1.2 THT, D5.1): island via at the top of the box -> B.Cu north under the RGB corridor (the bundle
#    is on F.Cu there) -> the pass-1 coil route: via east of D5.1 (short F.Cu stub) and B.Cu along y 55.75 to K1.2 from below.
# =====================================================================================================================
k1c = P("K1", pad_on("K1", N5)); d5k = P("D5", pad_on("D5", N5))   # (76.05,46.05), (88.15,57.5)
yr = 55.75
RV = (82.6, 73.3)                                  # island via, between R132 and R126, clear of the Kelvin line
V(N5, RV[0], RV[1], VP)
T(N5, "B", [RV, (RV[0], yr)], W5)
# pass 4b: the D5 via sits east of the D5.1 pad (via edge y >= 57.05, 1 mm south of the "mains: no inner copper" edge y 56.0 at
# x 58..96, so its In1/In2 rings stay out of the band), F.Cu stub straight east from the pad, B.Cu 45 deg up to the y 55.75 run
DV = (round(d5k[0] + 1.45, 3), d5k[1])             # (89.6, 57.5)
V(N5, DV[0], DV[1], VP); T(N5, "F", [d5k, DV], W5)
T(N5, "B", [DV, (DV[0] - (DV[1] - yr), yr), (RV[0], yr)], W5)
T(N5, "B", [(RV[0], yr), (k1c[0] + 2.0, yr), (k1c[0], yr - 2.0), k1c], W5)
R.save("tracks_power.json")

# =====================================================================================================================
# 5. VLED pair on B.Cu (pass 4): P via (95.6, 74.35) / N via (97.7, 77.7) -> south along x 98.7 / 97.7 (east strip of the box)
#    -> 45 deg tangent past the mounting hole H (97, 95.5) whose 9.4 mm washer keep-out (r 4.7, all layers) the track edges clear
#    by >= 0.1 mm -> east along the bottom strip y 96.3 / 97.3 -> under J10 (now on F.Cu, pads at the body's north edge, pin 1
#    = VLED_N east) -> two 0.6/0.3 vias under the connector body south of pins 1/2 -> F.Cu necks straight north into the pads'
#    south ends.  The pads' north side (caps C129/C130/C131) and the south escapes of pins 3..40 (x <= 144.53) stay free.
# =====================================================================================================================
j1 = P("J10", pad_on("J10", VLN)); j2 = P("J10", pad_on("J10", VLP))   # pin 1 (145.4, 89.125), pin 2 (144.9, 89.125)
mp = max([R.padinfo("J10", n) for (n, nt, x, y) in R.pads_of("J10") if n == "MP"], key=lambda d: d["x"])   # east anchor
mpw, mpb = mp["x"] - mp["w"] / 2, mp["y"] + mp["h"] / 2  # its west edge / south edge (146.1, 92.625)
xP, xN = 98.7, 97.7
HX, HY, HR = 97.0, 95.5, 4.7 + WLED / 2 + 0.1           # hole centre, keep-off radius for the track centre line (washer r 4.7)
cN = HY - HX - HR * math.sqrt(2)                          # SE diagonal y = x + c tangent-clear of the hole (lower track)
cN = math.floor(cN * 100) / 100                           # -8.65
cP = cN - math.sqrt(2) * (WLED + 0.5)                     # parallel diagonal 1.0 mm away (upper track)
yPe, yNe = 96.3, 97.3                                     # east runs (bottom strip)
WN = 0.28                                                 # F.Cu necks at the 0.5 mm pitch pads (0.22 gap)
# J10 vias: N south-east of pin 1 below the anchor pad, P 1.42 mm further south-west (In1 anti-pad web >= 0.3 mm)
ya = mpb + 0.275                                          # N neck leaves pin 1's column below the anchor pad corner
NVJ = (round(j1[0] + 0.6, 3), round(ya + 0.6, 3))         # (146.0, 93.5)
PVJ = (round(j2[0] + 0.2, 3), round(NVJ[1] + 1.1, 3))     # (145.1, 94.6)
assert math.hypot(NVJ[0] - max(mpw, NVJ[0]), NVJ[1] - mpb) >= 0.3 + 0.25 and math.hypot(NVJ[0] - PVJ[0], NVJ[1] - PVJ[1]) >= 1.4
T(VLN, "F", [j1, (j1[0], ya), NVJ], WN); V(VLN, NVJ[0], NVJ[1], VS)
T(VLP, "F", [j2, (j2[0], PVJ[1] - 0.2), PVJ], WN); V(VLP, PVJ[0], PVJ[1], VS)
# B.Cu: P rises NE straight into its via; N on the parallel diagonal 1.0 mm outside, then north into its via
dP = yPe - PVJ[1]                                         # 1.7
assert dP >= 0.5, "J10 pads moved south: lower the east runs yPe / yNe or move the vias"
cPe = PVJ[0] + PVJ[1] + math.sqrt(2) * (WLED + 0.5)       # N's parallel NE diagonal x + y = cPe
T(VLP, "B", [PV, (xP - 0.45, PV[1]), (xP, PV[1] + 0.45), (xP, xP + cP), (yPe - cP, yPe), (PVJ[0] - dP, yPe), PVJ], WLED)
T(VLN, "B", [NV, (xN, xN + cN), (yNe - cN, yNe), (cPe - yNe, yNe), (NVJ[0], cPe - NVJ[0]), NVJ], WLED)
R.save("tracks_power.json")

# =====================================================================================================================
# 6. BL_EN: U11.4 -> F.Cu stub west -> via -> B.Cu -> via next to the BL_EN pad of R127/R128 (display agent's parts,
#    BL_EN pads facing this block) -> F.Cu stub.  The B.Cu run stays south of the U10 1V2 ring (y > 79 west of x 70).
# =====================================================================================================================
from shapely.geometry import Polygon, Point
_G = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "geom_power.json")))
_FPADS = [(Polygon([(x - 20, y - 20) for x, y in p["poly"]]), p["net"]) for p in _G["pads"] if "F" in p["layers"] and len(p["poly"]) > 2]
def via_clear(x, y, net, r=0.3, cl=0.25):
    return all(pg.distance(Point(x, y)) >= r + cl for pg, nt in _FPADS if nt != net)
EV = (81.6, u11["4"][1])
T(BEN, "F", [u11["4"], EV], WSIG); V(BEN, EV[0], EV[1])
ens = sorted([(math.hypot(P(r, n)[0] - EV[0], P(r, n)[1] - EV[1]), r, n) for r in ("R127", "R128") for n in "12"
              if R.padinfo(r, n)["net"] == BEN])
_, er, en = ens[0]
ex, ey = P(er, en)
oth = [P(er, m) for m in "12" if m != en][0]               # the resistor's other pad: the via goes on the far side of the BL_EN pad
ax, ay = ex - oth[0], ey - oth[1]; al = math.hypot(ax, ay); ax, ay = ax / al, ay / al
cands = [(ex + ax, ey + ay), (ex - ay, ey + ax), (ex + ay, ey - ax)]
cands = [c for c in cands if via_clear(c[0], c[1], BEN)] or cands
EVF = min(cands, key=lambda c: math.hypot(c[0] - EV[0], c[1] - EV[1]))
EVF = (round(EVF[0], 4), round(EVF[1], 4))
# B.Cu, orthogonal with 45 deg corners: west along the EN pin row, down the box's west edge (x 70.75, under C127/C128 whose
# F.Cu side is busy) to the via's row, west into the via.
pts = [EV]
dy = EVF[1] - EV[1]
if abs(dy) < 1e-6:                                         # via on the EN row: straight
    pts.append(EVF)
elif abs(dy) < 1.0:                                        # small offset: one 45 deg jog
    pts += [(EVF[0] + abs(dy), EV[1]), EVF]
else:                                                      # west, down/up a column xt (chamfer 0.5), west into the via
    xt = max(EVF[0] + 1.0, 70.75); c = 0.5 if dy > 0 else -0.5
    assert xt + 0.5 < EV[0], "BL_EN via too close to U11 for the orthogonal hop"
    pts += [(xt + 0.5, EV[1]), (xt, EV[1] + c), (xt, EVF[1] - c), (xt - 0.5, EVF[1]), EVF]
EVF = pts[-1]
T(BEN, "B", pts, WSIG); V(BEN, EVF[0], EVF[1]); T(BEN, "F", [EVF, (ex, ey)], WSIG)

R.save("tracks_power.json")

# =====================================================================================================================
# 7. +5V from the PSU (pass 4: PS1 at the top-right corner, +5V pin (134.8, 47.5)).  The In2 +5V lobe (x 130.5..147, y 48..70)
#    only reaches the pin's south edge (one thermal spoke), so: 1.5 mm F.Cu bar PS1.4 -> straight south -> C2.1 (220u bulk),
#    two 0.9/0.45 island vias on the bar 1.7 mm apart between the module body and the can (In1 anti-pad web 0.3 mm, 1.0 mm to
#    the pin's anti-pad); C2.1 itself is THT on the island (4 spokes), C2.2 (GND) THT on In1.  From the lobe the island carries
#    the current to the buck / boost inputs.
# =====================================================================================================================
ps5 = P("PS1", pad_on("PS1", N5)); c2p = P("C2", pad_on("C2", N5))     # (134.8, 47.5), (134.8, 55.8)
assert abs(ps5[0] - c2p[0]) < 1e-6
T(N5, "F", [ps5, c2p], 1.5)
for y in (50.6, 52.3):                                      # just south of the module body (y 50.0), outside C2's can (r 3.15)
    V(N5, ps5[0], y, VP)
R.save("tracks_power.json")

R.save("tracks_power.json")

MY = [N5, N33, SW, BST, FB, VIN, BSW, DAMP, BFB, BEN, VLP, VLN]
if __name__ == "__main__" and "--stats" in sys.argv:
    from collections import defaultdict
    L = defaultdict(float); nv = defaultdict(int)
    for it in R.items:
        if it["via"]: nv[it["net"]] += 1
        else: L[it["net"]] += math.hypot(it["x2"] - it["x1"], it["y2"] - it["y1"])
    for n in MY + ["GND"]:
        print("%-20s copper %6.1f mm  vias %d" % (n, L[n], nv[n]))
if __name__ == "__main__" and "--check" in sys.argv:
    # pass 4: the other regions' current track files as they are (display / mains are re-routed in parallel: file times printed)
    import time
    SCR = os.path.dirname(os.path.abspath(__file__))
    extra = [f for f in ("tracks_signals.json", "tracks_display.json", "tracks_mains.json") if os.path.exists(os.path.join(SCR, f))]
    for f in extra: print("extra %-22s %s" % (f, time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(os.path.join(SCR, f))))))
    R.check("tracks_power.json", nets=MY, extra_json=extra, out="check_power.kicad_pcb", show=60)
