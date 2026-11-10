import pcbnew, sys, itertools
b = pcbnew.LoadBoard(sys.argv[1])
fps = [f for f in b.GetFootprints()]
def crt(f):
    poly = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
    if poly.OutlineCount() == 0: return None
    bb = poly.BBox(); return (bb.GetLeft()/1e6, bb.GetTop()/1e6, bb.GetRight()/1e6, bb.GetBottom()/1e6, poly)
info = {f.GetReference(): crt(f) for f in fps}
n = 0
for a, c in itertools.combinations(fps, 2):
    ia, ic = info[a.GetReference()], info[c.GetReference()]
    if not ia or not ic: continue
    if a.IsFlipped() != c.IsFlipped(): continue
    if ia[0] < ic[2] and ic[0] < ia[2] and ia[1] < ic[3] and ic[1] < ia[3]:
        pa = pcbnew.SHAPE_POLY_SET(ia[4]); pa.BooleanIntersection(ic[4])
        if pa.OutlineCount():
            n += 1; print("OVERLAP", a.GetReference(), c.GetReference(), "bb", [round(v-20,1) for v in ia[:4]], [round(v-20,1) for v in ic[:4]])
# board edge check
for f in fps:
    i = info[f.GetReference()]
    if i and (i[0] < 20.0 or i[1] < 20.0 or i[2] > 184.0 or i[3] > 119.0): print("OFFBOARD", f.GetReference(), [round(v-20,1) for v in i[:4]])
print("overlaps:", n)
