"""Stage 1a: update the board from the schematic netlist (what "Update PCB from Schematic" would do), by script.

    "C:/Program Files/KiCad/10.0/bin/python.exe" s1_sync.py in.kicad_pcb schematic_netlist.xml out.kicad_pcb

- nets: every pad gets the schematic net of its pin; a board net whose pads all move to one schematic net is renamed
  (tracks, vias, zones follow), so the copper keeps its connectivity. Unused nets are removed.
- RV2 removed with its 0.3 mm LINE_FILT stub and its two teardrops; the Q1_A1 trunk segments that met at RV2's pad 2
  are merged into one straight segment.
- new footprints from the KiCad 10 libraries: C9, C134, C135 (C_0402_1005Metric), D6 (D_DO-201AD_P15.24mm_Horizontal),
  RV3 (RV_Disc_D15.5mm_W5mm_P7.5mm); D6 and RV3 parked off the board, unrouted (stage 3).
- R4: footprint R_0402 -> R_0603 (same reference, fields, net), new position (101.335, 57.5) local, 0 deg.
- C5 moved from (9.27, 61.4) to (123.617, 58.9) local, 0 deg (U6 supply pin, just outside the u1_pins rule area); C9 at (118.96, 61.975), 270 deg;
  C134 at (118.2, 73.1), 0 deg, north-east of the first via row; C135 at (120.9, 75.4), 0 deg, east of the
  second via row (south and west of the field are taken by the QR code and the RN arrays / RGB ribbon).
- fields on every footprint: Value, Datasheet, Description, MPN, Manufacturer from the schematic (hidden fields added
  where missing); the exclude-from-BOM attribute follows the symbol.
Local mm = KiCad mm - 20 (as in tools/pcb_smooth)."""
import sys
import xml.etree.ElementTree as ET
import pcbnew

sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth")
from common import V, L, close, mm  # noqa: E402

FPLIB = r"C:/Program Files/KiCad/10.0/share/kicad/footprints"
src, netxml, dst = sys.argv[1:4]
b = pcbnew.LoadBoard(src)
root = ET.parse(netxml).getroot()

# ------------------------------------------------------------------ schematic data
comp = {}
for c in root.find("components"):
    f = {x.get("name"): (x.text or "") for x in c.iter("field")}
    props = {p.get("name"): p.get("value") for p in c.iter("property")}
    comp[c.get("ref")] = dict(value=c.findtext("value") or "", fp=c.findtext("footprint") or "", fields=f, props=props,
                              datasheet=c.findtext("datasheet") or "")
pin_net = {}
for n in root.find("nets"):
    for nd in n.findall("node"):
        pin_net[(nd.get("ref"), nd.get("pin"))] = n.get("name")
log = []

# ------------------------------------------------------------------ RV2 out
fps = {fp.GetReference(): fp for fp in b.GetFootprints()}
rv2 = fps.pop("RV2")
pads_rv2 = [L(p.GetPosition()) for p in rv2.Pads()]
# note: BOARD.Remove() corrupts the swig proxies of this KiCad 10.0.1 build (later GetStart() returns untyped objects),
# so nothing is removed through pcbnew: the UUIDs go to DEL and sx_delete.delete_items() cuts them from the saved file
DEL = []
def uid(it):
    return it.m_Uuid.AsString()
def pick_zones(pred):
    out = [z for z in b.Zones() if pred(z)]
    return out
def pick_tracks(pred):
    out = [t for t in b.GetTracks() if pred(t)]
    return out
tdz = pick_zones(lambda z: z.IsTeardropArea() and any(z.Outline().Contains(V(*q)) for q in pads_rv2))
for z in tdz:
    DEL.append(uid(z)); log.append("RV2 teardrop removed")
del tdz
def is_stub(t):
    if t.GetClass() != "PCB_TRACK" or t.GetNetname() != "LINE_FILT":
        return False
    s_, e_ = L(t.GetStart()), L(t.GetEnd())
    return {(round(s_[0], 3), round(s_[1], 3)), (round(e_[0], 3), round(e_[1], 3))} == {(100.5, 12.8), (100.5, 12.5)}
stub = pick_tracks(is_stub)
for t in stub:
    DEL.append(uid(t)); log.append("RV2 LINE_FILT stub removed")
del stub
seg = pick_tracks(lambda t: t.GetClass() == "PCB_TRACK" and t.GetNetname() == "Net-(Q1-A1)"
                  and (close(L(t.GetStart()), (108.0, 13.9)) or close(L(t.GetEnd()), (108.0, 13.9))))
assert len(seg) == 2, seg
ends = []
for t in seg:
    for q in (L(t.GetStart()), L(t.GetEnd())):
        if not close(q, (108.0, 13.9)):
            ends.append(q)
w = seg[0].GetWidth()
for t in seg:
    DEL.append(uid(t))
t = pcbnew.PCB_TRACK(b); t.SetStart(V(*ends[0])); t.SetEnd(V(*ends[1])); t.SetWidth(w); t.SetLayer(pcbnew.F_Cu)
t.SetNet(b.FindNet("Net-(Q1-A1)")); b.Add(t)
log.append("Q1-A1 trunk merged %s-%s" % (ends[0], ends[1]))
DEL.append(uid(rv2)); log.append("RV2 removed")

# ------------------------------------------------------------------ R4 footprint swap, C5 move
def load(lib, name):
    f = pcbnew.FootprintLoad(FPLIB + "/" + lib + ".pretty", name)
    assert f is not None, (lib, name)
    f.SetFPID(pcbnew.LIB_ID(lib, name))
    return f

old = fps["R4"]
new = load("Resistor_SMD", "R_0603_1608Metric")
new.SetReference("R4"); new.SetValue(old.GetValue())
for fld in old.GetFields():
    if fld.GetName() not in ("Reference", "Value", "Footprint"):
        new.SetField(fld.GetName(), fld.GetText())
new.SetAttributes(old.GetAttributes())
b.Add(new)
new.SetOrientationDegrees(0); new.SetPosition(V(101.335, 57.5))
for p in new.Pads():
    p.SetNet(b.FindNet({"1": "/TRIG", "2": "Net-(R4-Pad2)"}[p.GetNumber()]))
DEL.append(uid(old)); fps["R4"] = new
log.append("R4 -> R_0603_1608Metric at (101.335, 57.5) 0 deg")

c5 = fps["C5"]
c5.SetOrientationDegrees(0); c5.SetPosition(V(123.617, 58.9))
log.append("C5 moved to (123.617, 58.9) 0 deg: pads %s" % [(p.GetNumber(), [round(v, 3) for v in L(p.GetPosition())]) for p in c5.Pads()])

# ------------------------------------------------------------------ new footprints
NEW = [("C9", "Capacitor_SMD", "C_0402_1005Metric", (118.96, 61.975), 270),
       ("C134", "Capacitor_SMD", "C_0402_1005Metric", (118.2, 73.1), 0),
       ("C135", "Capacitor_SMD", "C_0402_1005Metric", (120.9, 75.4), 0),
       ("D6", "Diode_THT", "D_DO-201AD_P15.24mm_Horizontal", (190.0, 20.0), 0),     # parked off the board (stage 3)
       ("RV3", "Varistor", "RV_Disc_D15.5mm_W5mm_P7.5mm", (190.0, 40.0), 0)]        # parked off the board (stage 3)
for ref, lib, name, pos, rot in NEW:
    f = load(lib, name)
    f.SetReference(ref)
    b.Add(f)
    f.SetOrientationDegrees(rot); f.SetPosition(V(*pos))
    fps[ref] = f
    log.append("%s added: %s:%s at %s rot %d" % (ref, lib, name, pos, rot))

# ------------------------------------------------------------------ pad nets and net renames
rename = {}
for ref, f in fps.items():
    if ref not in comp:
        continue
    for p in f.Pads():
        sn = pin_net.get((ref, p.GetNumber()))
        if sn is None:
            continue
        bn = p.GetNetname()
        if bn and bn != sn:
            rename.setdefault(bn, set()).add(sn)
for bn, sns in sorted(rename.items()):
    assert len(sns) == 1, (bn, sns)
newnets = {}
for bn, sns in sorted(rename.items()):
    sn = next(iter(sns))
    ni = b.FindNet(sn)
    if ni is None:
        ni = pcbnew.NETINFO_ITEM(b, sn); b.Add(ni)
    newnets[bn] = ni
moved = {k: 0 for k in newnets}
for t in b.GetTracks():
    if t.GetNetname() in newnets:
        moved[t.GetNetname()] += 1; t.SetNet(newnets[t.GetNetname()])
for z in b.Zones():
    if not z.GetIsRuleArea() and z.GetNetname() in newnets:
        moved[z.GetNetname()] += 1; z.SetNet(newnets[z.GetNetname()])
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() in newnets:
            p.SetNet(newnets[p.GetNetname()])
for bn, ni in newnets.items():
    log.append("net %s -> %s (%d tracks/vias/zones)" % (bn, ni.GetNetname(), moved[bn]))
# every pad of every schematic part: schematic net (new parts, R4)
for ref, f in fps.items():
    if ref not in comp:
        continue
    for p in f.Pads():
        sn = pin_net.get((ref, p.GetNumber()))
        if sn is not None and p.GetNetname() != sn:
            ni = b.FindNet(sn)
            if ni is None:
                ni = pcbnew.NETINFO_ITEM(b, sn); b.Add(ni)
            p.SetNet(ni)
            log.append("pad %s.%s -> %s" % (ref, p.GetNumber(), sn))

# ------------------------------------------------------------------ fields and attributes
nfield = 0
for ref, f in fps.items():
    c = comp.get(ref)
    if c is None:
        continue
    want = {"Value": c["value"], "Datasheet": c["fields"].get("Datasheet", c["datasheet"]) or "",
            "Description": c["fields"].get("Description", "")}
    for k, v in c["fields"].items():          # MPN, Manufacturer and every other symbol field (Sim.*, Panel, ...)
        if k not in ("Footprint", "Datasheet", "Description") and v:
            want[k] = v
    changed = []
    for k, v in want.items():
        if k == "Value":
            if f.GetValue() != v:
                f.SetValue(v); changed.append(k)
            continue
        if not f.HasField(k) or f.GetFieldText(k) != v:
            had = f.HasField(k)
            f.SetField(k, v)
            fld = f.GetField(k)
            if not had:
                fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab); fld.SetPosition(f.GetPosition())
            changed.append(k)
    attrs = f.GetAttributes()
    excl = "exclude_from_bom" in c["props"]
    na = (attrs | pcbnew.FP_EXCLUDE_FROM_BOM) if excl else (attrs & ~pcbnew.FP_EXCLUDE_FROM_BOM)
    if na != attrs:
        f.SetAttributes(na); changed.append("attr BOM")
    if changed:
        nfield += 1
        log.append("fields %s: %s" % (ref, ",".join(changed)))
pcbnew.SaveBoard(dst, b)
import sx_delete
n = sx_delete.delete_items(dst, DEL)
log.append("deleted %d items by uuid (%d requested)" % (n, len(DEL)))
print("\n".join(log))
print("footprints with field changes:", nfield)
