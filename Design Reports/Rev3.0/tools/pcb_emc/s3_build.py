"""Stage 3b (KiCad python): K1 = Relay_THT:Relay_SPST_Schrack-RT1-16A-FormA_RM5mm and D6 into the mains band, by
explicit track lists (0/45/90 deg, ends at pad centres; corners get tangent arcs from pcb_smooth/fillet.py, drops from
teardrops.py in the touched boxes). Local mm = KiCad mm - 20.

K1: rotated +90 deg, pad A1 at (72.75, 52.0): coil A1 (72.75, 52.0) Net-(D5-A), A2 (65.25, 52.0) +5V (south, low-voltage
side of the new boundary notch); 11 (LINE_FUSED) at y 31.70 and 14 (Net-(J4-Pin_1)) at y 26.66, x 65.25 / 72.75.
  LINE_FUSED F.Cu 2.5 (MainsHeater): L40.2 (68.55, 15.1) -> (59.75, 23.9) -> (59.75, 29.2) -> (62.25, 31.7) -> 11 -> 11
  fan Net-(J4-Pin_1) B.Cu 2.5 (F3-limited fault, see stage-3 notes): J4.1 (49.9, 3.5) -> (49.9, 14.0) -> (53.4, 17.5)
      -> (53.4, 23.26) -> (56.8, 26.66) -> 14 -> 14
  +5V B.Cu 1.0: (82.6, 55.75) -> (81.45, 54.6) -> (66.3, 54.6) -> (65.25, 53.55) -> A2;  Net-(D5-A) F.Cu 0.3: A1 -> (72.75, 54.45)
      -> (73.6, 55.3) -> (82.08, 55.3)
  removed: the old K1 footprint and every track of its five pads (LINE_FUSED trunk under L40, the fan route east of
  J4.1, the +5V and Net-(D5-A) coil feeds north of y 55.3), teardrops in the touched boxes
D6 (bidirectional TVS, no polarity mark - the library footprint's cathode band is removed): pad 1 (94.0, 13.2) on the
  LINE_FILT trunk (split, 0.4 mm stub), pad 2 (109.24, 13.2) to the /Q1_A1 trunk at x 108 (split at y 13.2, 2.5 mm stub);
  the row sits 0.4 mm below the trunk so pad 2 keeps 2.5 mm from the NEUT B.Cu run at y 8.5;
  PSU_L re-routed at x 114.5 so it keeps >= 2.5 mm from pad 2: L1.4 (120, 5) -> (117, 5) -> (114.5, 7.5) -> (114.5, 18.8)
  -> F1.2 (112.9, 20.4)
Rule areas: 'mains: no inner copper' gets the notch x 61.5-77.0, y 45.0-56.0 (coil pins and feeds on the LV side);
  'k1_pins' (old relay pin-pitch area) deleted. Cmts.User boundary redrawn with the same notch.
Usage: s3_build.py in.kicad_pcb sch_netlist.xml out.kicad_pcb regions.json"""
import json, math, sys
import xml.etree.ElementTree as ET
import pcbnew
sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth")
from common import V, L, close, mm, add_track  # noqa: E402

src, netxml, dst, regfile = sys.argv[1:5]
b = pcbnew.LoadBoard(src)
KEEP, log = [], []
FPLIB = r"C:/Program Files/KiCad/10.0/share/kicad/footprints/Relay_THT.pretty"
FPNAME = "Relay_SPST_Schrack-RT1-16A-FormA_RM5mm"
REGIONS = {"k1": (55.0, 13.0, 80.5, 58.0), "fan": (47.0, 1.5, 75.0, 29.5), "d6": (87.0, 2.0, 121.5, 22.5)}
json.dump(REGIONS, open(regfile, "w"), indent=1)
F, B = pcbnew.F_Cu, pcbnew.B_Cu


def pts(t):
    if t.GetClass() == "PCB_ARC":
        return [L(t.GetStart()), L(t.GetMid()), L(t.GetEnd())]
    return [L(t.GetStart()), L(t.GetEnd())]


def remove_tracks(net, pred, why):
    n = 0
    for t in list(b.GetTracks()):
        if t.GetClass() == "PCB_VIA" or t.GetNetname() != net:
            continue
        if pred(t, pts(t)):
            b.Remove(t); KEEP.append(t); n += 1
    log.append("removed %d %s tracks (%s)" % (n, net, why))
    return n


inside = lambda p, x0, y0, x1, y1: x0 <= p[0] <= x1 and y0 <= p[1] <= y1
# ---- old K1 copper -------------------------------------------------------------------------------------------------
remove_tracks("LINE_FUSED", lambda t, P: all(inside(p, 67.0, 15.05, 71.5, 48.5) for p in P), "trunk L40.2 -> old K1.1")
remove_tracks("Net-(J4-Pin_1)", lambda t, P: True, "whole fan route, redrawn at 2.5 mm")
remove_tracks("+5V", lambda t, P: all(inside(p, 75.5, 45.5, 82.61, 55.8) for p in P), "old coil feed and its stub west of x 82.6")
remove_tracks("Net-(D5-A)", lambda t, P: all(inside(p, 63.5, 45.5, 82.2, 55.4) for p in P), "old coil feed")
for z in list(b.Zones()):
    if z.IsTeardropArea():
        bb = z.GetBoundingBox(); c = L(bb.GetCenter())
        if any(inside(c, *r) for r in REGIONS.values()) or inside(c, 61.0, 28.0, 79.0, 56.0):
            b.Remove(z); KEEP.append(z)
# ---- K1 footprint --------------------------------------------------------------------------------------------------
old = b.FindFootprintByReference("K1")
path = old.GetPath()
comps = {c.get("ref"): c for c in ET.parse(netxml).getroot().find("components")}
k = comps["K1"]
new = pcbnew.FootprintLoad(FPLIB, FPNAME)
new.SetFPID(pcbnew.LIB_ID("Relay_THT", FPNAME))
new.SetPath(path)
new.SetReference("K1"); new.SetValue(k.findtext("value"))
b.Remove(old); KEEP.append(old)
b.Add(new)
new.SetOrientationDegrees(90)
new.SetPosition(V(72.75, 52.0))
fields = {f.get("name"): (f.text or "") for f in k.iter("field")}
for name in ("Datasheet", "Description", "MPN", "Manufacturer", "MPN2", "Manufacturer2"):
    had = new.HasField(name)
    new.SetField(name, fields[name])
    if not had:
        fld = new.GetField(name)
        fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab); fld.SetPosition(new.GetPosition())
NETS = {"A1": "Net-(D5-A)", "A2": "+5V", "11": "LINE_FUSED", "14": "Net-(J4-Pin_1)"}
for p in new.Pads():
    p.SetNet(b.FindNet(NETS[p.GetNumber()]))
    log.append("K1 pad %s %s at %s" % (p.GetNumber(), NETS[p.GetNumber()], tuple(round(v, 3) for v in L(p.GetPosition()))))
# ---- K1 tracks -------------------------------------------------------------------------------------------------------
add_track(b, "LINE_FUSED", F, [(68.55, 15.1), (59.75, 23.9), (59.75, 29.2), (62.25, 31.7), (65.25, 31.7), (72.75, 31.7)], 2.5)
add_track(b, "Net-(J4-Pin_1)", B, [(49.9, 3.5), (49.9, 14.0), (53.4, 17.5), (53.4, 23.26), (56.8, 26.66), (65.25, 26.66), (72.75, 26.66)], 2.5)
add_track(b, "+5V", B, [(82.6, 55.75), (81.45, 54.6), (66.3, 54.6), (65.25, 53.55), (65.25, 52.0)], 1.0)
add_track(b, "Net-(D5-A)", F, [(72.75, 52.0), (72.75, 54.45), (73.6, 55.3), (82.084, 55.3)], 0.3)
# ---- D6 ----------------------------------------------------------------------------------------------------------------
d6 = b.FindFootprintByReference("D6")
d6.SetOrientationDegrees(0)
p1 = [p for p in d6.Pads() if p.GetNumber() == "1"][0]
off = (L(d6.GetPosition())[0] - L(p1.GetPosition())[0], L(d6.GetPosition())[1] - L(p1.GetPosition())[1])
d6.SetPosition(V(94.0 + off[0], 13.2 + off[1]))
for p in d6.Pads():
    log.append("D6 pad %s %s at %s" % (p.GetNumber(), p.GetNetname(), tuple(round(v, 3) for v in L(p.GetPosition()))))
# cathode band (silk / fab lines across the body near pad 1) removed: bidirectional part
for g in list(d6.GraphicalItems()):
    if g.GetClass() == "PCB_SHAPE" and g.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_Fab) and g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        s, e = L(g.GetStart()), L(g.GetEnd())
        if abs(s[0] - e[0]) < 0.01 and 95.0 < s[0] < 98.5:
            d6.Remove(g); KEEP.append(g); log.append("D6 band line removed x=%.2f %s" % (s[0], b.GetLayerName(g.GetLayer())))
# split LINE_FILT trunk at pad 1 and /Q1_A1 trunk at y 12.8
def split(net, a, c, at, w, layer):
    hit = [t for t in b.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() == net and
           ((close(L(t.GetStart()), a, 0.02) and close(L(t.GetEnd()), c, 0.02)) or (close(L(t.GetStart()), c, 0.02) and close(L(t.GetEnd()), a, 0.02)))]
    assert len(hit) == 1, (net, a, c, len(hit))
    b.Remove(hit[0]); KEEP.append(hit[0])
    add_track(b, net, layer, [a, at, c], w)
    log.append("split %s %s-%s at %s" % (net, a, c, at))
split("LINE_FILT", (89.0, 12.8), (100.5, 12.8), (94.0, 12.8), 2.5, F)
add_track(b, "LINE_FILT", F, [(94.0, 12.8), (94.0, 13.2)], 2.5)
split("/Q1_A1", (108.0, 25.5), (108.0, 3.5), (108.0, 13.2), 2.5, F)
add_track(b, "/Q1_A1", F, [(108.0, 13.2), (109.24, 13.2)], 2.5)
remove_tracks("PSU_L", lambda t, P: all(inside(p, 112.4, 4.4, 120.1, 20.5) for p in P) and not all(abs(p[1] - 20.4) < 0.01 for p in P), "L1.4 -> F1.2 path near D6.2")
add_track(b, "PSU_L", F, [(120.0, 5.0), (117.0, 5.0), (114.5, 7.5), (114.5, 18.8), (112.9, 20.4)], 1.0)
# ---- rule areas ---------------------------------------------------------------------------------------------------------
NOTCH = [(25.5, 0.5), (163.5, 0.5), (163.5, 40.0), (130.0, 40.0), (130.0, 55.5), (126.0, 54.8), (96.0, 54.8), (96.0, 56.0), (77.0, 56.0),
         (77.0, 45.0), (61.5, 45.0), (61.5, 56.0), (58.0, 56.0), (58.0, 39.81), (52.0, 38.8), (52.0, 35.5), (25.5, 35.5)]   # the band outline + notch
for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        continue
    if z.GetZoneName() == "k1_pins":
        b.Remove(z); KEEP.append(z); log.append("rule area k1_pins deleted")
    elif z.GetZoneName() == "mains: no inner copper":
        o = z.Outline(); o.RemoveAllContours(); o.NewOutline()
        for x, y in NOTCH:
            o.Append(pcbnew.FromMM(x + 20), pcbnew.FromMM(y + 20))
        log.append("rule area 'mains: no inner copper' notched (%s)" % ",".join(b.GetLayerName(l) for l in z.GetLayerSet().Seq()))
# ---- Cmts.User boundary ---------------------------------------------------------------------------------------------------
lay = b.GetLayerID("User.Comments")
w = None
for d in list(b.GetDrawings()):
    if d.GetClass() == "PCB_SHAPE" and d.GetLayer() == lay and d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        s, e = L(d.GetStart()), L(d.GetEnd())
        if {(round(s[0], 2), round(s[1], 2)), (round(e[0], 2), round(e[1], 2))} == {(58.0, 56.0), (96.0, 56.0)}:
            w = d.GetWidth(); b.Remove(d); KEEP.append(d)
assert w, "boundary segment (58,56)-(96,56) not found"
for a, c in zip([(58.0, 56.0), (61.5, 56.0), (61.5, 45.0), (77.0, 45.0), (77.0, 56.0)], [(61.5, 56.0), (61.5, 45.0), (77.0, 45.0), (77.0, 56.0), (96.0, 56.0)]):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*a)); s.SetEnd(V(*c)); s.SetWidth(w); s.SetLayer(lay); b.Add(s)
log.append("Cmts.User boundary: (58,56)-(61.5,56)-(61.5,45)-(77,45)-(77,56)-(96,56)")
pcbnew.SaveBoard(dst, b)
print("\n".join(log))
