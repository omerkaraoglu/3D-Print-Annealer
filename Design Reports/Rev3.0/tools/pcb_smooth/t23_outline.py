"""Tasks 2 + 3: screw ears with M3 holes on the top and right edges, R3 board corners, fillets where the ears meet the
edge, round-ended creepage slot.  Replaces every Edge.Cuts item drawn on the board (not footprint graphics).
Usage: t23_outline.py in.kicad_pcb out.kicad_pcb"""
import sys, math, pcbnew
from common import *
W, H = 164.0, 99.0
RC = 3.0          # board corner radius
EAR_W = 9.0       # tab width, full-round end (radius 4.5)
EAR_OFF = 5.8     # right ears: 9.4 mm washer keep-out (r 4.7) ends 0.18 mm outside the panel edge (abs x 184.92)
EAR_OFF_TOP = 5.8 # top ears: keep-out ends 0.1 mm outside the panel edge (abs y 19.00)
RF = 1.0          # fillet where a tab meets the edge
TOP_EARS = [10.0, 73.0, 154.0]     # x of the hole centres, top edge (hole y = -5)
RIGHT_EARS = [10.0, 89.0]          # y of the hole centres, right edge (hole x = 169)
SLOT = (101.5, 125.0, 50.6, 51.8)  # the two overlapping 1.2 x 12 mm slots under U5 / U1 -> one stadium (same extremes)

b = pcbnew.LoadBoard(sys.argv[1])
KEEP = []
# --- M3 holes on the ears + washer keep-outs (copies of the pass-4 'M3 washer keep-out' rule areas, all four Cu layers)
tmpl = [f for f in b.GetFootprints() if f.GetReference() == 'H'][0]
kz = [z for z in b.Zones() if z.GetZoneName() == 'M3 washer keep-out']
# template keep-outs of the hole at (4,4): one per layer
k44 = [z for z in kz if abs(L(z.GetBoundingBox().Centre())[0] - 4) < 0.1 and abs(L(z.GetBoundingBox().Centre())[1] - 4) < 0.1]
assert len(k44) == 4, len(k44)
holes = [(x, -EAR_OFF_TOP) for x in TOP_EARS] + [(W + EAR_OFF, y) for y in RIGHT_EARS]
n = 5
for (x, y) in holes:
    f = tmpl.Duplicate(False)
    f = pcbnew.Cast_to_FOOTPRINT(f) if not isinstance(f, pcbnew.FOOTPRINT) else f
    f.SetPosition(V(x, y)); f.SetReference('H%d' % n)
    f.SetFPID(pcbnew.LIB_ID('MountingHole', 'MountingHole_3.2mm_M3'))
    b.Add(f); KEEP.append(f); n += 1
    for z in k44:
        z2 = z.Duplicate(); z2 = pcbnew.Cast_to_ZONE(z2) if not isinstance(z2, pcbnew.ZONE) else z2
        c = z.GetBoundingBox().Centre(); z2.Move(V(x, y) - c)
        b.Add(z2); KEEP.append(z2)
for d in [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
    b.Remove(d); KEEP.append(d)

def seg(p, q):
    s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*p)); s.SetEnd(V(*q))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1)); b.Add(s); KEEP.append(s)
def arc(p, m, q):
    s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_ARC); s.SetArcGeometry(V(*p), V(*m), V(*q))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1)); b.Add(s); KEEP.append(s)
def amid(c, r, a0, a1):  # mid point of arc around c from angle a0 to a1 (deg, y down)
    a = math.radians((a0 + a1) / 2); return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
def apt(c, r, a):
    a = math.radians(a); return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
k = math.sqrt(0.5)
# --- walk clockwise in screen coordinates (y down) starting at the top-left corner arc end
path = []  # list of ('L', p, q) / ('A', p, m, q)
cur = (RC, 0.0)
def line_to(q):
    global cur
    if abs(q[0] - cur[0]) > 1e-6 or abs(q[1] - cur[1]) > 1e-6: path.append(('L', cur, q))
    cur = q
def arc_to(m, q):
    global cur
    path.append(('A', cur, m, q)); cur = q
h = EAR_W / 2
# top edge, left -> right, ears outward (y negative)
for x in TOP_EARS:
    line_to((x - h - RF, 0.0))
    c = (x - h - RF, -RF); arc_to(apt(c, RF, 45), (x - h, -RF))              # concave fillet, edge -> tab side
    line_to((x - h, -EAR_OFF_TOP))
    arc_to((x, -EAR_OFF_TOP - h), (x + h, -EAR_OFF_TOP))                           # full-round end
    line_to((x + h, -RF))
    c = (x + h + RF, -RF); arc_to(apt(c, RF, 135), (x + h + RF, 0.0))      # fillet back onto the edge
line_to((W - RC, 0.0))
arc_to(apt((W - RC, RC), RC, -45), (W, RC))
# right edge, top -> bottom, ears outward (x > W)
for y in RIGHT_EARS:
    line_to((W, y - h - RF))
    c = (W + RF, y - h - RF); arc_to(apt(c, RF, 135), (W + RF, y - h))
    line_to((W + EAR_OFF, y - h))
    arc_to((W + EAR_OFF + h, y), (W + EAR_OFF, y + h))
    line_to((W + RF, y + h))
    c = (W + RF, y + h + RF); arc_to(apt(c, RF, -135), (W, y + h + RF))
line_to((W, H - RC))
arc_to(apt((W - RC, H - RC), RC, 45), (W - RC, H))
line_to((RC, H))
arc_to(apt((RC, H - RC), RC, 135), (0.0, H - RC))
line_to((0.0, RC))
arc_to(apt((RC, RC), RC, -135), (RC, 0.0))
for it in path:
    if it[0] == 'L': seg(it[1], it[2])
    else: arc(it[1], it[2], it[3])
# slot: stadium with the old extremes
x0, x1, y0, y1 = SLOT; r = (y1 - y0) / 2; yc = (y0 + y1) / 2
seg((x0 + r, y0), (x1 - r, y0)); arc((x1 - r, y0), (x1, yc), (x1 - r, y1))
seg((x1 - r, y1), (x0 + r, y1)); arc((x0 + r, y1), (x0, yc), (x0 + r, y0))

pcbnew.SaveBoard(sys.argv[2], b)
print("edge items", len(path) + 4, "holes", holes)
