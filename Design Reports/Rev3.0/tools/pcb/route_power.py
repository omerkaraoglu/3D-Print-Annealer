"""Hand routing of the "power" region (buck TPS562201, MIC2288 backlight boost + pi-filter, HLK-10M05 DC pins, +5V net).
Idempotent: builds every track/via from scratch and writes tracks_power.json.  Local board mm (handroute.py convention).

Layer plan
  F.Cu : everything local (switch loops, decoupling, pi-filter, damper, sense lines, +5V K1.2 -> D5.1).
  B.Cu : crossings only - the VLED pair to J10 (pins 1/2 are on the back, at x 52.8/53.3 on the placed board),
         BL_EN (U11.4 -> R127/R128 next to the SSD1963, north of the boost so it never crosses BL_FB),
         BL_FB (R126 -> U11.3 under the SW barrier, In1 GND between it and the switch node),
         +5V relay feed (island via -> K1.2 THT pad, passes under the slow signal bundle at y 57-60).
Planes: In1 GND, In2 3V3 with the +5V island (x 98..140, y 64..98 on the placed board; the brief says 108..140 -
        every +5V via here is at x >= 109 and every +3V3 via at x <= 97 or y <= 63.3, so both definitions work).
"""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from handroute import Router

R = Router("geom.json")
P = R.pad
def pad_on(ref, net):                                       # pad of 'ref' carrying 'net' (pad numbers / rotations change between board revisions)
    return [n for (n, nt, x, y) in R.pads_of(ref) if nt == net][0]

# widths
W5 = 1.0; W5W = 1.5; WSW = 1.0; WLED = 0.6; WSIG = 0.25; WGND = 0.4; WNECK = 0.3
VP = dict(d=0.9, drill=0.45)      # power via
VS = dict(d=0.6, drill=0.3)       # signal / GND via

def T(net, layer, pts, w): R.track(net, layer, pts, w)
def V(net, x, y, v=VS): R.via(net, x, y, **v)
def gnd_via(pad, vx, vy, mid=None):
    """GND pad -> own 0.6/0.3 via with a 0.4 mm stub (optional 45-degree knee 'mid')"""
    pts = [P(*pad)] + ([mid] if mid else []) + [(vx, vy)]
    T("GND", "F", pts, WGND); V("GND", vx, vy)

# =====================================================================================================
# +5V : PSU pin -> C2 -> island vias; island -> buck input, boost pi-filter input, relay coil
# =====================================================================================================
N5 = "+5V"
ps4 = P("PS1", "4"); c2p = P("C2", "1")                    # (134.8, 87.5), (125.5, 90.0)
T(N5, "F", [ps4, (127.5, 87.5), (125.5, 89.5), c2p], W5W)
for x in (132.6, 131.3, 130.0):                            # 3 x 0.9/0.45 into the In2 +5V island at the PSU pin
    V(N5, x, 87.5, VP)

# buck input: C330.1 / C331.1 bar, two island vias, VIN pin 3 (EN pin 5 gets its own via)
c330 = P("C330", "1"); c331 = P("C331", "1")              # (110.5, 75.95), (113.5, 75.95)
T(N5, "F", [c330, (112.0, 75.95), c331], W5)
for (x, y) in (c330, c331):
    T(N5, "F", [(x, y), (x, 77.6)], W5); V(N5, x, 77.6, VP)
u30_3 = P("U30", "3")                                      # (110.863, 70.95)
kv = (112.0, u30_3[1] + (112.0 - u30_3[0]))
T(N5, "F", [(112.0, 75.95), kv], W5)
T(N5, "F", [kv, u30_3], 0.8)       # 0.8 at the 0.95 mm pitch pin (0.25 to the SW pin)
u30_5 = P("U30", "5")                                      # (113.137, 70.0) EN tied to VIN
T(N5, "F", [u30_5, (114.75, 70.0)], 0.5); V(N5, 114.75, 70.0, VP)

# boost pi-filter input: L12.2 -> C127.1, two island vias
l12b = P("L12", "2"); c127 = P("C127", "1")                # (117.625, 82.5), (120, 83.95)
T(N5, "F", [l12b, (l12b[0], c127[1] - 0.5), (l12b[0] + 0.5, c127[1]), c127], W5)
T(N5, "F", [c127, (121.6, c127[1])], W5); V(N5, 121.6, c127[1], VP)
T(N5, "F", [c127, (c127[0], 85.55)], W5); V(N5, c127[0], 85.55, VP)

# relay coil (K1 at (70,48) rot 90: coil pad K1.2 (76.05,46.05), COM (70,48) = LINE; D5 rot 180: D5.1 (+5V) at (88.15,57.5)).
# Island via -> B.Cu under the y 57-60 signal bundle -> via just above D5.1 (short F.Cu stub) -> B.Cu along y 55.75 ->
# K1.2 THT pad from below (x 76.05, 4.05 mm from the COM pad).  Net-(D5-A) (K1.5 -> Q4.3/D5.2) stays on F.Cu above it.
k1c = P("K1", pad_on("K1", N5)); d5k = P("D5", pad_on("D5", N5))
yr = 55.75                                                  # B.Cu level of the coil feed / D5.1 via
V(N5, 109.5, 65.0, VP)
T(N5, "B", [(109.5, 65.0), (105.5, 61.0), (d5k[0] + 61.0 - yr, 61.0), (d5k[0], yr)], W5)
V(N5, d5k[0], yr, VP); T(N5, "F", [(d5k[0], yr), d5k], W5)
T(N5, "B", [(d5k[0], yr), (k1c[0] + 2.0, yr), (k1c[0], yr - 2.0), k1c], W5)

# =====================================================================================================
# Buck TPS562201
# =====================================================================================================
u30_1 = P("U30", "1"); u30_2 = P("U30", "2"); u30_4 = P("U30", "4"); u30_6 = P("U30", "6")
l30a = P("L30", "1"); l30b = P("L30", "2")                 # SW (107.875,70.5), 3V3 (103.125,70.5)
c332bst = P("C332", "1"); c332sw = P("C332", "2")          # (112.48,67.2), (111.52,67.2)
SW = "/Power/BUCK_SW"
J = (109.75, 70.0)                                          # SW junction just outside the pin row
T(SW, "F", [u30_2, J], 0.6)                                 # pin neck
T(SW, "F", [J, (108.375, 70.0), l30a], WSW)
T(SW, "F", [c332sw, (110.32, 67.2), (109.75, 67.77), J], 0.4)     # bootstrap cap to SW, left of the GND pin
T("/Power/BUCK_BST", "F", [c332bst, (c332bst[0], 68.55 - (u30_6[0] - c332bst[0])), (u30_6[0], 68.55), u30_6], 0.4)
gnd_via(("U30", "1"), u30_1[0], 68.15)                      # IC GND via between the pin and C332
# feedback, right side only (SW is on the left)
FB = "/Power/BUCK_FB"
r330fb = P("R330", "2"); r331fb = P("R331", "1")           # (117.01,68.5), (115.99,71.5)
T(FB, "F", [u30_4, (115.44, 70.95), r331fb], WSIG)
T(FB, "F", [r330fb, (117.01, 69.48), (115.99, 70.5), r331fb], WSIG)
gnd_via(("R331", "2"), 117.95, 71.5)
r330top = P("R330", "1")                                   # +3V3 sense: via into the In2 3V3 plane above the island
T("+3V3", "F", [r330top, (r330top[0], 63.0)], WSIG); V("+3V3", r330top[0], 63.0)
# input-cap GND vias (right under the caps, same In1 area as U30 GND)
gnd_via(("C330", "2"), 110.5, 72.75)
gnd_via(("C331", "2"), 113.5, 72.75)
# output: L30.2 -> between the cap GND pads -> C333.1/C334.1 bar -> 3 x 0.9 vias into the 3V3 plane (x < 98)
c333 = P("C333", "1"); c334 = P("C334", "1")               # (101,77.45), (104,77.45)
T("+3V3", "F", [l30b, (102.5, 71.125), (102.5, 77.45)], W5)
T("+3V3", "F", [c333, (102.5, 77.45), c334], W5)
T("+3V3", "F", [c333, (97.0, 77.45), (95.8, 77.45), (94.6, 77.45)], W5)
for x in (97.0, 95.8, 94.6):
    V("+3V3", x, 77.45, VP)
gnd_via(("C333", "2"), 99.95, 75.55)
gnd_via(("C334", "2"), 105.05, 75.55)

# =====================================================================================================
# MIC2288 boost + input pi-filter + damper
# =====================================================================================================
u11 = {n: P("U11", n) for n in "12345"}
l11a = P("L11", "1"); l11b = P("L11", "2")                 # BL_VIN (104.875,85), BL_SW (108.125,85)
d111a = P("D111", "1"); d111b = P("D111", "2")             # VLED_P (104.5,92), BL_SW (108.5,92)
c124 = P("C124", "1"); l12a = P("L12", "1")               # (112,82.45), (114.375,82.5)
r132a = P("R132", "1"); r132b = P("R132", "2")             # BL_VIN (106.037,80), BL_DAMP (108.963,80)
c128a = P("C128", "1")                                     # BL_DAMP (93.8,80)
VIN = "/Display/BL_VIN"
T(VIN, "F", [c124, (u11["5"][0], c124[1]), (l12a[0] - 0.05, c124[1]), l12a], W5)   # C124.1 -> L12.1
T(VIN, "F", [u11["5"], (u11["5"][0], c124[1])], 0.6)                              # VIN pin straight up to the bar
T(VIN, "F", [c124, (111.55, 82.0), (r132a[0], 82.0), (105.875, 82.0), (l11a[0], 83.0), l11a], W5)  # over L11.2 to L11.1
T(VIN, "F", [r132a, (r132a[0], 82.0)], W5)
# damper R132.2 -> C128.1 (the damper pad is on the far side of both parts; channel y = 78.65 between C333/C334 and R132/C128)
T("/Display/BL_DAMP", "F", [r132b, (r132b[0], 79.15), (r132b[0] - 0.5, 78.65), (c128a[0] + 0.5, 78.65), (c128a[0], 79.15), c128a], 0.5)
# switch node: U11.1 -> junction at x 108.5 -> L11.2 (up) and D111.2 (down)
BSW = "/Display/BL_SW"
JB = (108.5, u11["1"][1])
T(BSW, "F", [u11["1"], (109.9, JB[1])], 0.6)
T(BSW, "F", [(109.9, JB[1]), JB], WSW)
T(BSW, "F", [JB, (108.5, 85.375), l11b], WSW)
T(BSW, "F", [JB, d111b], WSW)
gnd_via(("U11", "2"), 109.65, 88.45, mid=(110.1, 88.0))
gnd_via(("C124", "2"), 110.9, 80.55)
gnd_via(("C127", "2"), 121.15, 82.05)
gnd_via(("C128", "2"), 98.2, 81.65)
# output: D111.1 -> C125.1 (hot loop, 1.0) ; D114 clamp (K on VLED_P, A on GND after the schematic fix) joins on the right
VP_ = "/Display/VLED_P"
c125 = P("C125", "1")                                       # (101.5,91.95)
d114k = P("D114", pad_on("D114", VP_))                      # (101.5,84.35) VLED_P
d114a = ("D114", pad_on("D114", "GND"))                     # (101.5,87.65) GND
T(VP_, "F", [c125, (102.9, 91.95), (d111a[0] - 0.05, 91.95), d111a], 1.0)
T(VP_, "F", [d114k, (102.3, d114k[1]), (102.9, d114k[1] + 0.6), (102.9, 91.95)], WLED)
# VLED_P leaves for J10 from the clamp pad: via right under D114.K, between its two pads
T(VP_, "F", [d114k, (d114k[0], 86.0)], WLED); V(VP_, d114k[0], 86.0, VP)
# D114.A and C125.2 share one GND via centred in the 1.07 mm gap between the two pads
yg = (P(*d114a)[1] + 0.6 + P("C125", "2")[1] - 0.725) / 2
T("GND", "F", [P(*d114a), (d114k[0], yg), P("C125", "2")], WGND); V("GND", d114k[0], yg)
# LED return: R122.1 / R123.1 joined on the left, VLED_N via on that link ; GND vias on the right
VN = "/Display/VLED_N"
r122 = P("R122", "1"); r123 = P("R123", "1")              # (97,86.9125), (97,90.9125)
yP, yN = 86.7, 87.8                                        # B.Cu pair levels (VLED_P above, VLED_N below)
T(VN, "F", [r122, (96.3, r122[1]), (95.6, r122[1] + 0.7), (95.6, yN), (95.6, r123[1])], WLED)
T(VN, "F", [r123, (95.6, r123[1])], WLED); V(VN, 95.6, yN, VP)
gnd_via(("R122", "2"), 98.2, P("R122", "2")[1])
gnd_via(("R123", "2"), 98.2, P("R123", "2")[1])
# FB sense: R126.2 (VLED_N side, R126 = 0R) over R126 to the top of the sense resistors (Kelvin at R122.1)
r126n = P("R126", "2"); r126f = P("R126", "1")            # (103.01,81.5), (101.99,81.5)
T(VN, "F", [r126n, (r126n[0], 81.0), (102.71, 80.7), (100.6, 80.7), (100.3, 81.0), (100.3, 86.0), (100.3 - (r122[1] - 86.0), r122[1]), r122], WSIG)
# BL_FB: R126.1 -> via under it -> B.Cu down x 103 (between the D114/C125 column and the L11 keep-out), under the SW node at y 89.3 -> U11.3
BFB = "/Display/BL_FB"
T(BFB, "F", [r126f, (r126f[0], 82.6)], WSIG); V(BFB, r126f[0], 82.6)
T(BFB, "B", [(r126f[0], 82.6), (103.0, 82.6 + 103.0 - r126f[0]), (103.0, 88.7), (103.6, 89.3), (u11["3"][0] - 0.65, 89.3), (u11["3"][0], 89.95)], WSIG)
V(BFB, u11["3"][0], 89.95); T(BFB, "F", [(u11["3"][0], 89.95), u11["3"]], WSIG)
# BL_EN: U11.4 -> via -> B.Cu north along x 114.4, west along y 79 -> via above R127 -> R127.1 -> R128.2
BEN = "/Display/BL_EN"
r127 = P("R127", "1"); r128 = P("R128", "2")              # (72.49,84), (70.01,84)
T(BEN, "F", [u11["4"], (114.4, u11["4"][1])], WSIG); V(BEN, 114.4, u11["4"][1])
T(BEN, "B", [(114.4, u11["4"][1]), (114.4, 79.6), (113.8, 79.0), (76.09, 79.0), (r127[0], 82.6)], WSIG)
V(BEN, r127[0], 82.6); T(BEN, "F", [(r127[0], 82.6), r127], WSIG)
T(BEN, "F", [r128, r127], WSIG)
gnd_via(("R127", "2"), 74.35, 84.0)
# VLED pair on B.Cu to J10 pins 1 (VLED_N, x 72.3) / 2 (VLED_P, x 71.8), pads at y 91.725 on the interior side.
# Pair at y 86.7 / 87.8 (1.1 mm pitch) so the B.Cu band y 88.3..91.1 above J11 stays free for its fan-in;
# x > 73 for y 88..92 except the two pad entries; 0.3 mm only at the 0.5 mm connector pitch.
j1 = P("J10", "1"); j2 = P("J10", "2")
xs = j1[0] + 1.0                                            # VLED_N drop column (73.3), 1.0 mm right of pad 1
T(VP_, "B", [(d114k[0], 86.0), (d114k[0] - (yP - 86.0), yP), (j2[0] + 1.0, yP)], WLED)
T(VP_, "B", [(j2[0] + 1.0, yP), (j2[0], yP + 1.0), j2], WNECK)
T(VN, "B", [(95.6, yN), (xs + 0.7, yN), (xs, yN + 0.7), (xs, j1[1] - 1.0)], WLED)
T(VN, "B", [(xs, j1[1] - 1.0), j1], WNECK)

R.save("tracks_power.json")

# ----------------------------------------------------------------------------------------------------- report
MY = ["+5V", "/Power/BUCK_SW", "/Power/BUCK_BST", "/Power/BUCK_FB", "+3V3", "/Display/BL_VIN", "/Display/BL_SW",
      "/Display/BL_DAMP", "/Display/BL_FB", "/Display/BL_EN", "/Display/VLED_P", "/Display/VLED_N"]
if __name__ == "__main__" and "--stats" in sys.argv:
    from collections import defaultdict
    L = defaultdict(float); nv = defaultdict(int)
    for it in R.items:
        if it["via"]: nv[it["net"]] += 1
        else: L[it["net"]] += math.hypot(it["x2"] - it["x1"], it["y2"] - it["y1"])
    for n in MY + ["GND"]:
        print("%-20s copper %6.1f mm  vias %d" % (n, L[n], nv[n]))
