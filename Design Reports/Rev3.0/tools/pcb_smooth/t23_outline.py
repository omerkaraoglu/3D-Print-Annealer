"""Tasks 2 + 3: screw ears with M3 holes, R3 board corners, fillets where the ears meet the edge, round-ended creepage
slot.  Replaces every Edge.Cuts item drawn on the board (not footprint graphics).
Smoothing round (step 3 of build.py): ears on the top and right edges only (H5..H9).  Round 3 (r3_holes.py) calls
outline() again with ears on all four edges.
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


def apt(c, r, a):
    a = math.radians(a); return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def outline(b, KEEP, top=TOP_EARS, right=RIGHT_EARS, bottom=(), left=(), off_top=EAR_OFF_TOP, off_right=EAR_OFF,
            off_bottom=EAR_OFF, off_left=EAR_OFF):
    """Remove every board-level Edge.Cuts item and draw the outline: rounded rectangle W x H with ears.
    top / bottom: x of the hole centres; right / left: y of the hole centres; off_*: hole centre distance outside
    the edge.  Walk clockwise (screen coordinates, y down) from the top-left corner.  Returns the path items."""
    for d in [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
        b.Remove(d); KEEP.append(d)

    def seg(p, q):
        s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*p)); s.SetEnd(V(*q))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1)); b.Add(s); KEEP.append(s)

    def arc(p, m, q):
        s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_ARC); s.SetArcGeometry(V(*p), V(*m), V(*q))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1)); b.Add(s); KEEP.append(s)
    path = []
    st = dict(cur=(RC, 0.0))

    def line_to(q):
        c = st['cur']
        if abs(q[0] - c[0]) > 1e-6 or abs(q[1] - c[1]) > 1e-6: path.append(('L', c, q))
        st['cur'] = q

    def arc_to(m, q):
        path.append(('A', st['cur'], m, q)); st['cur'] = q
    h = EAR_W / 2
    k = math.sqrt(0.5)

    def ears(P, d, n, svals, off):
        """edge point P(s), walking direction d, outward normal n; one tab per s (tab centre s)"""
        E = lambda s, o=0.0: (P(s)[0] + n[0] * o, P(s)[1] + n[1] * o)
        for s in svals:
            line_to(E(s - h - RF))
            c = E(s - h - RF, RF)
            arc_to((c[0] + RF * k * (d[0] - n[0]), c[1] + RF * k * (d[1] - n[1])), E(s - h, RF))   # concave fillet, edge -> tab
            line_to(E(s - h, off))
            arc_to(E(s, off + h), E(s + h, off))                                                    # full-round end
            line_to(E(s + h, RF))
            c = E(s + h + RF, RF)
            arc_to((c[0] - RF * k * (d[0] + n[0]), c[1] - RF * k * (d[1] + n[1])), E(s + h + RF))  # fillet back onto the edge
    # top edge, left -> right, ears outward (y negative)
    ears(lambda s: (s, 0.0), (1, 0), (0, -1), sorted(top), off_top)
    line_to((W - RC, 0.0))
    arc_to(apt((W - RC, RC), RC, -45), (W, RC))
    # right edge, top -> bottom, ears outward (x > W)
    ears(lambda s: (W, s), (0, 1), (1, 0), sorted(right), off_right)
    line_to((W, H - RC))
    arc_to(apt((W - RC, H - RC), RC, 45), (W - RC, H))
    # bottom edge, right -> left, ears outward (y > H); parameter s = x
    for x in sorted(bottom, reverse=True):
        _bottom_ear(line_to, arc_to, x, off_bottom, h, k)
    line_to((RC, H))
    arc_to(apt((RC, H - RC), RC, 135), (0.0, H - RC))
    # left edge, bottom -> top, ears outward (x < 0)
    for y in sorted(left, reverse=True):
        _left_ear(line_to, arc_to, y, off_left, h, k)
    line_to((0.0, RC))
    arc_to(apt((RC, RC), RC, -135), (RC, 0.0))
    for it in path:
        if it[0] == 'L': seg(it[1], it[2])
        else: arc(it[1], it[2], it[3])
    # slot: stadium with the old extremes
    x0, x1, y0, y1 = SLOT; r = (y1 - y0) / 2; yc = (y0 + y1) / 2
    seg((x0 + r, y0), (x1 - r, y0)); arc((x1 - r, y0), (x1, yc), (x1 - r, y1))
    seg((x1 - r, y1), (x0 + r, y1)); arc((x0 + r, y1), (x0, yc), (x0 + r, y0))
    return path


def _bottom_ear(line_to, arc_to, x, off, h, k):
    """bottom edge walked right -> left (direction -x), outward normal +y"""
    line_to((x + h + RF, H))
    c = (x + h + RF, H + RF); arc_to((c[0] - RF * k, c[1] - RF * k), (x + h, H + RF))
    line_to((x + h, H + off))
    arc_to((x, H + off + h), (x - h, H + off))
    line_to((x - h, H + RF))
    c = (x - h - RF, H + RF); arc_to((c[0] + RF * k, c[1] - RF * k), (x - h - RF, H))


def _left_ear(line_to, arc_to, y, off, h, k):
    """left edge walked bottom -> top (direction -y), outward normal -x"""
    line_to((0.0, y + h + RF))
    c = (-RF, y + h + RF); arc_to((c[0] + RF * k, c[1] - RF * k), (-RF, y + h))
    line_to((-off, y + h))
    arc_to((-off - h, y), (-off, y - h))
    line_to((-RF, y - h))
    c = (-RF, y - h - RF); arc_to((c[0] + RF * k, c[1] + RF * k), (0.0, y - h - RF))


if __name__ == '__main__':
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
    path = outline(b, KEEP)
    pcbnew.SaveBoard(sys.argv[2], b)
    print("edge items", len(path) + 4, "holes", holes)
