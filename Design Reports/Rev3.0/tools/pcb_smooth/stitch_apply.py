"""Add the planned GND stitching vias (0.6 / 0.3 mm through, net GND) to a board.  Usage: stitch_apply.py in out plan.json"""
import sys, json, pcbnew
from common import *
b = pcbnew.LoadBoard(sys.argv[1])
plan = json.load(open(sys.argv[3]))
gnd = b.FindNet('GND')
KEEP = []
for x, y, kind in plan['vias']:
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(pcbnew.F_Cu, pcbnew.FromMM(0.6)) if hasattr(v, 'SetWidth') else None
    v.SetDrill(pcbnew.FromMM(0.3)); v.SetNet(gnd); v.SetIsFree(True)   # free via: keeps GND, never re-netted from a zone
    b.Add(v); KEEP.append(v)
# outer GND pours: remove every island that is still unconnected after stitching (was: keep islands > 9 mm2)
for z in b.Zones():
    if not z.GetIsRuleArea() and z.GetNetname() == 'GND' and z.GetFirstLayer() in (pcbnew.F_Cu, pcbnew.B_Cu) and not z.IsTeardropArea():
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.SaveBoard(sys.argv[2], b)
print("added", len(plan['vias']), "GND vias")
