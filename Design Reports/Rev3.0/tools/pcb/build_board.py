"""Build the Rev3.0 PCB (placement, outline, planes, keep-outs) from the netlist. Routing is done by route.py."""
import sys, os, re, importlib
SCR = r"C:\Users\lenovo\AppData\Local\Temp\claude\dad0af2289ad5142\c8708701-d586-4d89-8e7b-a64a4af1e14d\scratchpad"
sys.path.insert(0, SCR)
import pcbnew
from pcbnew import VECTOR2I, VECTOR2I_MM, FromMM
from sx import parse, find, first
import placement; importlib.reload(placement)
from placement import P, W, H, OX, OY

STD = "C:/Program Files/KiCad/10.0/share/kicad/footprints/"
REV3 = "C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/ComponentsLibrary/User Created/Rev3/Rev3.pretty"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SCR, "rev3_placed.kicad_pcb")

def mm(x, y): return VECTOR2I_MM(OX + x, OY + y)

d = parse(open(os.path.join(SCR, "rev3.net"), encoding="utf-8").read())
comps = find(first(d, 'components'), 'comp')
nets = find(first(d, 'nets'), 'net')

board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
board.SetLayerName(pcbnew.In1_Cu, "GND"); board.SetLayerName(pcbnew.In2_Cu, "PWR")
ds = board.GetDesignSettings()
for attr, val in (('m_TrackMinWidth',0.15),('m_ViasMinSize',0.5),('m_MinThroughDrill',0.3),('m_MinClearance',0.15),
                  ('m_CopperEdgeClearance',0.5),('m_HoleClearance',0.25),('m_ViasMinAnnularWidth',0.1),('m_HoleToHoleMin',0.5)):
    if hasattr(ds, attr): setattr(ds, attr, FromMM(val))
    else: print('no attr', attr)
ds.m_SolderMaskExpansion = FromMM(0.05)

# nets
netinfo = board.GetNetInfo()
netmap = {}
for n in nets:
    name = first(n, 'name')[1].replace('{slash}', '/')
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni); netmap[name] = ni
pinnet = {}
for n in nets:
    name = first(n, 'name')[1].replace('{slash}', '/')
    for node in find(n, 'node'):
        pinnet[(first(node, 'ref')[1], first(node, 'pin')[1])] = name

# footprints
missing = []
for c in comps:
    ref = first(c, 'ref')[1]; val = first(c, 'value')[1]
    fpf = first(c, 'footprint')
    if not fpf or not fpf[1]:
        print("no footprint:", ref); continue
    lib, name = fpf[1].split(":")
    path = REV3 if lib == "Rev3" else STD + lib + ".pretty"
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None: print("MISSING", ref, fpf[1]); missing.append(ref); continue
    fp.SetReference(ref); fp.SetValue(val)
    fp.SetFPIDAsString(fpf[1])
    board.Add(fp)
    if ref not in P:
        print("UNPLACED", ref); P[ref] = (5 + 4 * (len(missing)), -10, 0, 'F'); missing.append(ref)
    x, y, rot, side = P[ref]
    fp.SetPosition(mm(x, y))
    if side == 'B':
        fp.Flip(mm(x, y), False)
    fp.SetOrientationDegrees(rot + (180 if side == 'B' else 0))   # Flip() leaves the part rotated 180: pads stay on the interior side, pin 1 on the right
    for pad in fp.Pads():
        key = (ref, pad.GetNumber())
        if key in pinnet:
            pad.SetNet(netmap[pinnet[key]])
    # tidy reference text: smaller, above the part
    r = fp.Reference(); r.SetTextSize(VECTOR2I(FromMM(0.7), FromMM(0.7))); r.SetTextThickness(FromMM(0.12))
    v = fp.Value(); v.SetVisible(False)

# ---------- outline ----------
def shape_rect(x1, y1, x2, y2, layer, width=0.1):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetStart(mm(x1, y1)); s.SetEnd(mm(x2, y2))
    s.SetLayer(layer); s.SetWidth(FromMM(width)); board.Add(s); return s
def shape_line(x1, y1, x2, y2, layer, width=0.1):
    s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(mm(x1, y1)); s.SetEnd(mm(x2, y2))
    s.SetLayer(layer); s.SetWidth(FromMM(width)); board.Add(s); return s
def shape_text(txt, x, y, layer, size=1.5, rot=0):
    t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetPosition(mm(x, y)); t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size))); t.SetTextThickness(FromMM(size * 0.15))
    t.SetTextAngleDegrees(rot); board.Add(t); return t

R = 2.0  # corner radius -> approximate with lines + arcs
def outline_poly(pts, layer=pcbnew.Edge_Cuts):
    for i in range(len(pts)):
        x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
        shape_line(x1, y1, x2, y2, layer, 0.1)
outline_poly([(0, 0), (W, 0), (W, H), (0, H)])
# isolation slots under the optocouplers (between the pin rows) and along the LV/mains boundary near K1
SLOTS = [(101.5, 50.6, 113.5, 51.8),     # U5: mains pins y=47.38, SELV pins y=55
         (113.0, 50.6, 125.0, 51.8),     # U1: mains pins y=47.38, SELV pins y=55
         ]
for (x1, y1, x2, y2) in SLOTS:
    outline_poly([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])

# mounting holes (M3, NPTH 3.2 mm with 6.4 mm copper keep-out)
HOLES = [(4, 4), (4, 95), (160, 95), (97, 95.5)]
for (hx, hy) in HOLES:
    fp = pcbnew.FootprintLoad(STD + "MountingHole.pretty", "MountingHole_3.2mm_M3")
    fp.SetReference("H"); fp.SetPosition(mm(hx, hy)); fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    board.Add(fp)

# ---------- zones ----------
def add_zone(net, layer, pts, priority=0, name="", keepout=None, fill=True, min_th=0.25):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    if net: z.SetNet(netmap[net])
    z.SetAssignedPriority(priority); z.SetZoneName(name)
    z.SetMinThickness(FromMM(min_th)); z.SetLocalClearance(FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(FromMM(0.3)); z.SetThermalReliefSpokeWidth(FromMM(0.4))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA); z.SetMinIslandArea(FromMM(3) * FromMM(3))
    if keepout is not None:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowZoneFills('zones' in keepout); z.SetDoNotAllowTracks('tracks' in keepout)
        z.SetDoNotAllowVias('vias' in keepout); z.SetDoNotAllowPads('pads' in keepout); z.SetDoNotAllowFootprints('fp' in keepout)
    for (x, y) in pts: z.AppendCorner(mm(x, y), -1)
    board.Add(z); return z

LV = [(0.5, 0.5), (25.5, 0.5), (25.5, 35.5), (52.0, 35.5), (52.0, 38.8), (58.0, 39.81), (58.0, 56.0), (96.0, 56.0), (96.0, 54.8), (126.0, 54.8), (130.0, 55.5), (130.0, 60.0), (161.0, 60.0), (161.0, 98.5), (0.5, 98.5)]   # SELV copper region (pass 2: y 60 under the PSU body, was 80)
# inner planes: GND on In1, 3V3 on In2 (+1V2 island under U10)
add_zone("GND", pcbnew.In1_Cu, LV, 0, "GND plane")
add_zone("+3V3", pcbnew.In2_Cu, LV, 0, "3V3 plane")
# 5 V pour on In2 near the PSU output / buck / boost input
add_zone("+5V", pcbnew.In2_Cu, [(70, 70), (147, 70), (147, 98), (70, 98)], 1, "5V island")   # pass 2: LV power block x 70..100, y 71..98.5 + PSI DC pins
# outer-layer GND pours over the SELV region (crystal guard, thermal), hatched not needed
add_zone("GND", pcbnew.F_Cu, LV, 0, "GND top pour", min_th=0.25)
add_zone("GND", pcbnew.B_Cu, LV, 0, "GND bottom pour", min_th=0.25)

# SSD1963: block the four corner gaps of the pad ring on F.Cu so no signal trace crosses under the package
for (cx, cy) in ((51.0, 63.0), (65.0, 63.0), (51.0, 77.0), (65.0, 77.0)):
    add_zone(None, pcbnew.F_Cu, [(cx - 0.6, cy - 0.6), (cx + 0.6, cy - 0.6), (cx + 0.6, cy + 0.6), (cx - 0.6, cy + 0.6)], 10, "U10 corner", keepout="tracks vias")
# named rule areas (no restrictions) used by the DRC escape rule
for nm, (x1, y1, x2, y2) in (("u10_escape", (48.0, 60.0, 68.0, 80.0)), ("u20_escape", (25.5, 79.5, 33.6, 85.5)),
                             ("q1_fanout", (106.58, 35.3, 118.68, 43.3)), ("k1_pins", (60.5, 30.5, 79.5, 51.5)), ("u1_pins", (113.6, 42.5, 125.0, 58.5)), ("u5_pins", (101.5, 44.0, 113.4, 58.5))):
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu):
        add_zone(None, layer, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)], 0, nm, keepout="")
# keep-outs
# ESP32 antenna: no copper on any layer under/around the antenna (module top edge)
for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
    add_zone(None, layer, [(-1, 36), (7.6, 36), (7.6, 64), (-1, 64)], 10, "antenna keepout", keepout="zones tracks vias pads fp")
# no inner copper under the switching inductors
for (x1, y1, x2, y2) in [(72.3, 86.0, 80.3, 94.0), (80.9, 78.35, 86.9, 84.35)]:   # pass 2: L30, L11 (power agent)
    for layer in (pcbnew.In1_Cu, pcbnew.In2_Cu):
        add_zone(None, layer, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)], 10, "no inner Cu under inductor", keepout="zones tracks vias")
# the triac heatsink HS1 (Fischer SK 409 63,5 STC) carries its own F.Cu keep-out zones (fins + plate) in the footprint
# mains region: no inner copper at all, no SELV copper (annotated)
# pass 2: the corner under the PSU body is at y 60 (was 80) so the In2 3V3 plane reaches the strip east of the +5V island (R125);
# the nearest mains copper there is the PS1 AC pin row (y 45) and the AC/N track (y 49.2) -> >= 10 mm.
MAINS = [(25.5, 0.5), (163.5, 0.5), (163.5, 60.0), (130.0, 60.0), (130.0, 55.5), (126.0, 54.8), (96.0, 54.8), (96.0, 56.0), (58.0, 56.0), (58.0, 39.81), (52.0, 38.8), (52.0, 35.5), (25.5, 35.5)]
for layer in (pcbnew.In1_Cu, pcbnew.In2_Cu):
    add_zone(None, layer, MAINS, 10, "mains: no inner copper", keepout="zones tracks")
for k in range(len(MAINS) - 1):
    if k == 0: continue
    shape_line(MAINS[k][0], MAINS[k][1], MAINS[k + 1][0], MAINS[k + 1][1], pcbnew.Cmts_User, 0.3)
shape_line(MAINS[-1][0], MAINS[-1][1], MAINS[0][0], MAINS[0][1], pcbnew.Cmts_User, 0.3)
shape_text("MAINS 230 VAC AREA", 38, 2.6, pcbnew.Cmts_User, 0.8); shape_text("6.4 mm creepage to SELV (line)", 38, 4.4, pcbnew.Cmts_User, 0.8)

# silkscreen title
shape_text("READARK DRYER / ANNEALER", 144.5, 94.2, pcbnew.F_SilkS, 1.0); shape_text("Rev3.0  2026", 144.5, 96.2, pcbnew.F_SilkS, 1.0)
shape_text("K-TYPE TC", 6.5, 74.5, pcbnew.F_SilkS, 1.0)
shape_text("MAINS IN", 34, 7.5, pcbnew.F_SilkS, 0.8); shape_text("HEATER", 144, 7.5, pcbnew.F_SilkS, 0.8); shape_text("FAN", 97, 7.5, pcbnew.F_SilkS, 0.8)

pcbnew.SaveBoard(OUT, board)
print("saved", OUT, "footprints", len(list(board.GetFootprints())), "nets", board.GetNetCount(), "unplaced/missing", missing)
