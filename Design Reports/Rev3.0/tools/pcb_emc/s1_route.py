"""Stage 1b: hand-routed copper for the low-voltage changes (explicit track / via lists, 0/45/90 deg, ends at pad
centres; the corners get tangent arcs afterwards from tools/pcb_smooth/fillet.py, the drops from teardrops.py).

    "C:/Program Files/KiCad/10.0/bin/python.exe" s1_route.py in.kicad_pcb out.kicad_pcb regions.json

Removed items are kept in KEEP (a removed pcbnew item whose Python proxy is collected corrupts the board in 10.0.1).
Teardrop zones inside the touched boxes (regions.json, local mm) are deleted; teardrops.py regenerates them there.
Local mm = KiCad mm - 20."""
import json, sys
import pcbnew
sys.path.insert(0, r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/Design Reports/Rev3.0/tools/pcb_smooth")
from common import V, L, close, mm, add_track  # noqa: E402

src, dst, regfile = sys.argv[1:4]
b = pcbnew.LoadBoard(src)
KEEP = []
log = []
REGIONS = {
    "c5_old":  (7.4, 59.8, 10.2, 63.0),
    "u6":      (117.5, 57.8, 125.6, 63.2),
    "r4":      (98.8, 54.3, 106.0, 59.2),
    "c134":    (116.4, 72.4, 120.0, 73.8),
    "c135":    (119.1, 74.7, 122.7, 76.1),
}
json.dump(REGIONS, open(regfile, "w"), indent=1)


def kp(p):
    return (round(p[0], 3), round(p[1], 3))


def find(cls, net, a, c=None):
    out = []
    for t in b.GetTracks():
        if t.GetClass() != cls or t.GetNetname() != net:
            continue
        if cls == "PCB_VIA":
            if close(L(t.GetPosition()), a, 0.002):
                out.append(t)
            continue
        s, e = L(t.GetStart()), L(t.GetEnd())
        if (close(s, a, 0.002) and close(e, c, 0.002)) or (close(s, c, 0.002) and close(e, a, 0.002)):
            out.append(t)
    return out


def delete(cls, net, a, c=None):
    its = find(cls, net, a, c)
    assert len(its) == 1, (cls, net, a, c, len(its))
    b.Remove(its[0]); KEEP.append(its[0])
    log.append("del %s %s %s %s" % (cls[4:], net, a, c or ""))


def via(net, p, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(*p)); v.SetWidth(pcbnew.FromMM(d)); v.SetDrill(pcbnew.FromMM(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(b.FindNet(net)); b.Add(v)
    log.append("add via %s %s" % (net, p))


def track(net, pts, w=0.25, layer=pcbnew.F_Cu):
    add_track(b, net, layer, pts, w)
    log.append("add track %s %s w %.2f" % (net, pts, w))


# ---------------------------------------------------------------- old C5 site (ESP32 3V3 pin -> plane via stays)
delete("PCB_ARC", "GND", (9.27, 61.88), (8.331, 62.269))
delete("PCB_TRACK", "GND", (8.331, 62.269), (8.2, 62.4))
delete("PCB_VIA", "GND", (8.2, 62.4))
delete("PCB_TRACK", "+3V3", (9.26, 60.92), (9.27, 60.92))
delete("PCB_TRACK", "+3V3", (9.27, 60.92), (8.2, 60.92))
track("+3V3", [(9.26, 60.92), (8.2, 60.92)])

# ---------------------------------------------------------------- C9 at U6 input
delete("PCB_TRACK", "/ZCD_RAW", (118.96, 58.99), (118.96, 59.964))
delete("PCB_ARC", "/ZCD_RAW", (118.96, 59.964), (119.41, 61.05))
delete("PCB_ARC", "/ZCD_RAW", (119.41, 61.05), (120.496, 61.5))
delete("PCB_TRACK", "/ZCD_RAW", (120.496, 61.5), (120.863, 61.5))
track("/ZCD_RAW", [(118.96, 58.99), (118.96, 61.495)])
track("/ZCD_RAW", [(118.96, 61.495), (120.863, 61.5)])
track("GND", [(118.96, 62.455), (119.7, 62.45)])

# ---------------------------------------------------------------- C5 at U6 supply pin, own GND via
track("+3V3", [(123.137, 59.5), (123.137, 58.9)])
via("GND", (124.9, 58.9))
track("GND", [(124.097, 58.9), (124.9, 58.9)])

# ---------------------------------------------------------------- R4 0603 stubs
delete("PCB_TRACK", "/TRIG", (99.296, 58.714), (99.414, 58.596))
delete("PCB_ARC", "/TRIG", (99.414, 58.596), (100.828, 58.01))
delete("PCB_TRACK", "/TRIG", (100.828, 58.01), (101.0, 58.01))
track("/TRIG", [(99.296, 58.714), (100.51, 57.5)])
delete("PCB_TRACK", "Net-(R4-Pad2)", (101.0, 56.99), (102.404, 55.586))
delete("PCB_ARC", "Net-(R4-Pad2)", (102.404, 55.586), (103.818, 55.0))
delete("PCB_TRACK", "Net-(R4-Pad2)", (103.818, 55.0), (105.0, 55.0))
track("Net-(R4-Pad2)", [(102.16, 57.5), (102.16, 55.0), (105.0, 55.0)])

# ---------------------------------------------------------------- C134 / C135 at the J10 re-sort via field
via("+5V", (116.87, 73.1)); via("GND", (119.53, 73.1))
track("+5V", [(117.72, 73.1), (116.87, 73.1)], 0.4); track("GND", [(118.68, 73.1), (119.53, 73.1)], 0.4)
via("+5V", (119.57, 75.4)); via("GND", (122.23, 75.4))
track("+5V", [(120.42, 75.4), (119.57, 75.4)], 0.4); track("GND", [(121.38, 75.4), (122.23, 75.4)], 0.4)

# ---------------------------------------------------------------- teardrops in the touched boxes
gone = []
for z in b.Zones():
    if z.IsTeardropArea():
        c = L(z.GetBoundingBox().GetCenter())
        if any(r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[3] for r in REGIONS.values()):
            gone.append(z)
for z in gone:
    b.Remove(z); KEEP.append(z)
log.append("teardrops removed in the touched boxes: %d" % len(gone))
pcbnew.SaveBoard(dst, b)
print("\n".join(log))
