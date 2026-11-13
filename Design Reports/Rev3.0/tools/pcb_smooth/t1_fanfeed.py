"""Task 1: K1.1 (fan relay COM) from LINE_FILT to LINE_FUSED.
- K1.1 pad net -> LINE_FUSED
- delete the LINE_FILT copper that only fed K1.1: (70.5,18)-(70.5,47.5)-(70,48)
- LINE_FILT west branch (L40.1 -> C40.1 -> C1 -> RV1) leaves the F.Cu y=18 bus between L40.1 and C40 and runs on B.Cu
  (1.0 mm, same width as before, THT pads L40.1 and C40.1 are the layer change; no vias) so that F.Cu is free for
- the new LINE_FUSED feed, 2.5 mm F.Cu: L40.2 (68.55,15.1) -> (70,16.55) -> (70,43.5) [collinear with the F3->L40 trunk],
  then 1.6 mm (70,43.5) -> K1.1 (70,48) (final pass: neck at the coil pins).
Usage: t1_fanfeed.py in.kicad_pcb out.kicad_pcb"""
import sys, pcbnew
from common import *
NECK_Y = 43.5
b = pcbnew.LoadBoard(sys.argv[1])
F, B = pcbnew.F_Cu, pcbnew.B_Cu
k1 = b.FindFootprintByReference('K1')
pad = [p for p in k1.Pads() if p.GetNumber() == '1'][0]
pad.SetNet(b.FindNet('LINE_FUSED'))
dele = [((70.5, 18), (70.5, 47.5)), ((70.5, 47.5), (70, 48)),           # K1.1 drop
        ((76.05, 15.1), (73.15, 18)), ((73.15, 18), (70.5, 18)), ((70.5, 18), (63.5, 18)),  # bus east part
        ((63.5, 18), (60.75, 15.25)), ((60.75, 15.25), (60.75, 13)), ((63.5, 18), (51.6, 18))]
rm = []
for p, q in dele:
    ts = find_tracks(b, 'LINE_FILT', p, q, F)
    assert len(ts) == 1, (p, q, len(ts))
    rm.append(ts[0])
for t in rm: b.Remove(t)
# LINE_FILT: C40.1 -> C1 branch on F.Cu, re-drawn without the dog-leg
add_track(b, 'LINE_FILT', F, [(60.75, 13), (60.75, 16), (58.75, 18), (51.6, 18)], 1.0)
# LINE_FILT: L40.1 -> C40.1 on B.Cu (1.0 mm), 2.7 mm from the NEUT B.Cu run at y 8.5, 1.2 mm from L40.2 (L-chain rule 1.0)
add_track(b, 'LINE_FILT', B, [(76.05, 15.1), (73.15, 12.2), (61.55, 12.2), (60.75, 13.0)], 1.0)
# LINE_FUSED feed to K1.1, 2.5 mm F.Cu (heater-trunk width, only F3 8 A protects it)
# (final pass, O3) necked to 1.6 mm over the last 4.5 mm (3.0 mm outside the K1.1 pad) so the copper keeps >= 3.8 mm from
# the coil pads K1.2 / K1.5; the 2.5 -> 1.6 mm step gets a KiCad track-to-track teardrop (teardrops.py)
add_track(b, 'LINE_FUSED', F, [(68.55, 15.1), (70, 16.55), (70, NECK_Y)], 2.5)
add_track(b, 'LINE_FUSED', F, [(70, NECK_Y), (70, 48)], 1.6)
pcbnew.SaveBoard(sys.argv[2], b)
print("saved", sys.argv[2])
