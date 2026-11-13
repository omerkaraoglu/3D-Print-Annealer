"""Round 3, task 2: no holes inside the board.
- deletes the four old M3 holes under the panel, local (4, 4), (4, 95), (97, 95.5), (160, 95), and their 9.4 mm
  'M3 washer keep-out' rule areas on all four copper layers (16 areas), so the pours close over them
- adds four ears in the style of the five existing ones (9 mm tab, full-round end R 4.5, R 1 fillets to the edge,
  `MountingHole:MountingHole_3.2mm_M3`, copies of the washer keep-outs on all four copper layers, board-only, excluded
  from BOM and position files):
    left edge   hole centres x = -LEFT_OFF   at y = 10, 89      (mirror of the right ears)
    bottom edge hole centres y = 99 + BOTTOM_OFF at x = 10, 155 (clear of the CTP / TFT tail loops)
  The panel is flush with the PCB on the left and bottom (abs x 20.02 / y 119.00), so 4.8 mm puts the washer keep-out
  0.1 mm outside the panel, as on the top / right ears (5.8 mm there because the panel overhangs by 1.0 / 0.92 mm).
- redraws Edge.Cuts with t23_outline.outline() (ears on all four edges)
- renumbers the nine holes H1..H9 clockwise from the top-left (top ears left -> right, right ears top -> bottom,
  bottom ears right -> left, left ears bottom -> top)
- removes free GND stitching vias in the J11 area that collide with the round-3 copper (< 0.3 mm edge gap to any pad /
  track / via of another item, or < 1.35 mm from a round-3 via); stitch_plan.py refills the gaps afterwards (the new
  washer keep-outs lie outside the board outline, so no via can sit in them)
Usage: r3_holes.py in.kicad_pcb out.kicad_pcb"""
import sys, math, pcbnew
from common import *
import t23_outline as T
LEFT_OFF = 4.8
BOTTOM_OFF = 4.8
LEFT_EARS = [10.0, 89.0]
BOTTOM_EARS = [10.0, 155.0]
OLD = [(4.0, 4.0), (4.0, 95.0), (97.0, 95.5), (160.0, 95.0)]
b = pcbnew.LoadBoard(sys.argv[1])
KEEP = []
holes = [f for f in b.GetFootprints() if 'MountingHole_3.2mm_M3' in str(f.GetFPID().GetUniStringLibItemName())]
assert len(holes) == 9, len(holes)
kz = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName() == 'M3 washer keep-out']
assert len(kz) == 36, len(kz)
# template: the keep-outs of the top-left ear hole (10, -5.8)
tmpl_fp = [f for f in holes if close(L(f.GetPosition()), (10.0, -5.8))][0]
tmpl_k = [z for z in kz if close(L(z.GetBoundingBox().Centre()), (10.0, -5.8), 0.1)]
assert len(tmpl_k) == 4, len(tmpl_k)
n_fp = n_k = 0
for f in holes:
    p = L(f.GetPosition())
    if any(close(p, o, 0.01) for o in OLD):
        b.Remove(f); KEEP.append(f); n_fp += 1
for z in kz:
    c = L(z.GetBoundingBox().Centre())
    if any(close(c, o, 0.1) for o in OLD):
        b.Remove(z); KEEP.append(z); n_k += 1
print("removed holes", n_fp, "keep-out areas", n_k)
assert n_fp == 4 and n_k == 16
new = [(-LEFT_OFF, y) for y in LEFT_EARS] + [(x, T.H + BOTTOM_OFF) for x in BOTTOM_EARS]
for (x, y) in new:
    f = tmpl_fp.Duplicate(False)
    f = pcbnew.Cast_to_FOOTPRINT(f) if not isinstance(f, pcbnew.FOOTPRINT) else f
    f.SetPosition(V(x, y)); f.SetReference('Hnew')
    f.SetBoardOnly(True); f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
    b.Add(f); KEEP.append(f)
    for z in tmpl_k:
        z2 = z.Duplicate(); z2 = pcbnew.Cast_to_ZONE(z2) if not isinstance(z2, pcbnew.ZONE) else z2
        z2.Move(V(x, y) - V(10.0, -5.8))
        b.Add(z2); KEEP.append(z2)
path = T.outline(b, KEEP, top=T.TOP_EARS, right=T.RIGHT_EARS, bottom=BOTTOM_EARS, left=LEFT_EARS,
                 off_top=T.EAR_OFF_TOP, off_right=T.EAR_OFF, off_bottom=BOTTOM_OFF, off_left=LEFT_OFF)
print("Edge.Cuts: outline %d items (%d lines, %d arcs) + slot 4" % (len(path), sum(1 for p in path if p[0] == 'L'), sum(1 for p in path if p[0] == 'A')))
# clockwise numbering from the top-left
order = ([(x, -T.EAR_OFF_TOP) for x in sorted(T.TOP_EARS)] + [(T.W + T.EAR_OFF, y) for y in sorted(T.RIGHT_EARS)] +
         [(x, T.H + BOTTOM_OFF) for x in sorted(BOTTOM_EARS, reverse=True)] + [(-LEFT_OFF, y) for y in sorted(LEFT_EARS, reverse=True)])
hs = [f for f in b.GetFootprints() if 'MountingHole_3.2mm_M3' in str(f.GetFPID().GetUniStringLibItemName())]
assert len(hs) == 9
for f in hs:
    p = L(f.GetPosition())
    i = [k for k, o in enumerate(order) if close(p, o, 0.01)]
    assert len(i) == 1, p
    f.SetReference('H%d' % (i[0] + 1))
    f.SetBoardOnly(True); f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
for f in sorted(hs, key=lambda f: int(f.GetReference()[1:])):
    p = L(f.GetPosition())
    print("  %-3s local (%7.2f, %6.2f)  abs (%7.2f, %6.2f)" % (f.GetReference(), p[0], p[1], p[0] + 20, p[1] + 20))
# free GND stitching vias that now collide with other copper
CLR = pcbnew.FromMM(0.3)
copper = []
for fp in b.GetFootprints():
    for p in fp.Pads():
        copper.append(p)
for t in b.Tracks():
    copper.append(t)
washers = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName() == 'M3 washer keep-out']
drop = []
for v in [t for t in b.Tracks() if t.GetClass() == 'PCB_VIA' and t.GetIsFree() and t.GetNetname() == 'GND']:
    pv = L(v.GetPosition())
    if not (33.0 <= pv[0] <= 49.0 and 83.0 <= pv[1] <= 95.5):
        continue   # only the J11 area changed copper (elsewhere the planner's own clearances still hold)
    vs = v.GetEffectiveShape(pcbnew.F_Cu)
    hit = None
    for it in copper:
        if it is v or it.m_Uuid.AsString() == v.m_Uuid.AsString():
            continue
        if it.GetClass() == 'PCB_VIA' and it.GetNetname() == 'GND':
            continue   # GND via spacing is the planner's business (1.35 mm); round-3 vias are checked below
        lay = pcbnew.F_Cu if it.IsOnLayer(pcbnew.F_Cu) else (pcbnew.B_Cu if it.IsOnLayer(pcbnew.B_Cu) else None)
        if lay is None:
            continue
        bb = it.GetBoundingBox(); bb.Inflate(pcbnew.FromMM(1.0))
        if not bb.Contains(v.GetPosition()):
            continue
        if vs.Collide(it.GetEffectiveShape(lay), CLR):
            hit = it; break
    if hit is not None:
        drop.append((L(v.GetPosition()), hit if hit == 'washer' else '%s %s' % (hit.GetClass(), hit.GetParentFootprint().GetReference() if hit.GetClass() == 'PAD' else hit.GetNetname())))
        b.Remove(v); KEEP.append(v)
# round-3 vias near other GND vias (< 1.35 mm centres): drop the free one
r3v = [(40.52, 91.7), (41.77, 92.4), (38.0, 86.1), (34.95, 89.25), (34.13, 87.35)]
for v in [t for t in b.Tracks() if t.GetClass() == 'PCB_VIA' and t.GetIsFree() and t.GetNetname() == 'GND']:
    p = L(v.GetPosition())
    if any(math.hypot(p[0] - q[0], p[1] - q[1]) < 1.35 and not close(p, q, 0.01) for q in r3v):
        drop.append((p, 'spacing to a round-3 via')); b.Remove(v); KEEP.append(v)
print("free GND stitching vias removed:", len(drop))
for p, why in drop:
    print("   (%.3f, %.3f) %s" % (p[0], p[1], why))
pcbnew.SaveBoard(sys.argv[2], b)
print("saved", sys.argv[2])
