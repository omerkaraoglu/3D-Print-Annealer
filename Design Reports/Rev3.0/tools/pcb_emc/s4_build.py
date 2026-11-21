"""Stage 3c (KiCad python): RV3 across the K1 contact (owner's decision 2026-11-21): Thinking TVR10471KSY on
Varistor:RV_Disc_D12mm_W5.8mm_P7.5mm, rotated 90 deg, pad 1 (LINE_FUSED) at (57.65, 30.30), pad 2 (Net-(J4-Pin_1)) at
(60.35, 22.80), west of the relay; courtyard x 55.85-62.15, y 20.30-32.80 (K1's starts at x 62.2).
Because RV3 now sits where LINE_FUSED ran west of the relay, LINE_FUSED goes round the EAST side of K1:
  LINE_FUSED F.Cu 2.5: L40.2 (68.55, 15.1) -> (78.25, 24.8) -> (78.25, 29.2) -> (75.75, 31.7) -> 11 (72.75) -> 11 (65.25)
                       -> (59.05, 31.7) -> RV3.1 (57.65, 30.3)
  fan Net-(J4-Pin_1) B.Cu 2.5: (49.9, 11.525) -> (49.9, 14.0) -> (53.4, 17.5) -> (53.4, 19.9) -> (56.3, 22.8) -> RV3.2 (60.35, 22.8) -> (61.39, 22.8)
                       -> 14 (65.25, 26.66) -> 14 (72.75, 26.66)
Both branches carry the fan's fault current only through the fan (RV3 is in series with nothing else); a disc short is
in parallel with the contact, so the 2.5 mm width follows the fan-route reasoning (F3 limited). No mains vias.
Removed: the old LINE_FUSED trunk west of the relay and the fan route east of (53.4, 17.5), teardrops in the touched box.
Usage: s4_build.py in.kicad_pcb sch_netlist.xml out.kicad_pcb regions.json"""
import json, sys
import xml.etree.ElementTree as ET
import pcbnew
sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth")
from common import V, L, add_track  # noqa: E402

src, netxml, dst, regfile = sys.argv[1:5]
b = pcbnew.LoadBoard(src)
KEEP, log = [], []
REG = {"rv3": (47.0, 12.0, 82.0, 35.0)}
json.dump(REG, open(regfile, "w"), indent=1)
F, B = pcbnew.F_Cu, pcbnew.B_Cu
inside = lambda p, x0, y0, x1, y1: x0 <= p[0] <= x1 and y0 <= p[1] <= y1


def pts(t):
    return [L(t.GetStart()), L(t.GetMid()), L(t.GetEnd())] if t.GetClass() == "PCB_ARC" else [L(t.GetStart()), L(t.GetEnd())]


def remove_tracks(net, pred, why):
    n = 0
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_VIA" or t.GetNetname() != net:
            continue
        P = pts(t)
        if pred(P):
            b.Remove(t); KEEP.append(t); n += 1
    log.append("removed %d %s tracks (%s)" % (n, net, why))


between11 = lambda P: all(abs(p[1] - 31.7) < 0.01 and p[0] >= 65.2 for p in P)
remove_tracks("LINE_FUSED", lambda P: all(inside(p, 58.0, 15.05, 69.0, 32.0) for p in P) and not between11(P), "trunk west of the relay")
between14 = lambda P: all(abs(p[1] - 26.66) < 0.01 and p[0] >= 65.2 for p in P)
remove_tracks("Net-(J4-Pin_1)", lambda P: all(inside(p, 49.8, 11.4, 66.0, 27.0) for p in P) and not between14(P), "fan route below the J4.1 straight (arcs included)")
for z in list(b.Zones()):
    if z.IsTeardropArea() and inside(L(z.GetBoundingBox().GetCenter()), *REG["rv3"]):
        b.Remove(z); KEEP.append(z)
# RV3 footprint
old = b.FindFootprintByReference("RV3")
comps = {c.get("ref"): c for c in ET.parse(netxml).getroot().find("components")}
c = comps["RV3"]
new = pcbnew.FootprintLoad(r"C:/Program Files/KiCad/10.0/share/kicad/footprints/Varistor.pretty", "RV_Disc_D12mm_W5.8mm_P7.5mm")
new.SetFPID(pcbnew.LIB_ID("Varistor", "RV_Disc_D12mm_W5.8mm_P7.5mm"))
new.SetPath(old.GetPath()); new.SetReference("RV3"); new.SetValue(c.findtext("value"))
for name, val in {f.get("name"): (f.text or "") for f in c.iter("field")}.items():
    if name in ("Footprint",):
        continue
    had = new.HasField(name)
    new.SetField(name, val)
    if not had:
        fld = new.GetField(name); fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab); fld.SetPosition(new.GetPosition())
b.Remove(old); KEEP.append(old); b.Add(new)
new.SetOrientationDegrees(90); new.SetPosition(V(57.65, 30.30))
new.Value().SetVisible(False)
NETS = {"1": "LINE_FUSED", "2": "Net-(J4-Pin_1)"}
for p in new.Pads():
    p.SetNet(b.FindNet(NETS[p.GetNumber()]))
    log.append("RV3 pad %s %s at %s" % (p.GetNumber(), NETS[p.GetNumber()], tuple(round(v, 3) for v in L(p.GetPosition()))))
add_track(b, "LINE_FUSED", F, [(68.55, 15.1), (78.25, 24.8), (78.25, 29.2), (75.75, 31.7), (72.75, 31.7)], 2.5)
add_track(b, "LINE_FUSED", F, [(65.25, 31.7), (59.05, 31.7), (57.65, 30.3)], 2.5)
add_track(b, "Net-(J4-Pin_1)", B, [(49.9, 11.525), (49.9, 14.0), (53.4, 17.5), (53.4, 19.9), (56.3, 22.8), (60.35, 22.8), (61.39, 22.8), (65.25, 26.66)], 2.5)
pcbnew.SaveBoard(dst, b)
print("\n".join(log))
