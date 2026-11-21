"""Pad-net map of a board against the schematic netlist (xml): every schematic pin on a footprint pad with the same
net name (KiCad's {slash} escape normalised), every board pad accounted for; plus pcbnew's unconnected count.
Usage: conn_sch.py board.kicad_pcb sch.xml"""
import sys, xml.etree.ElementTree as ET, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); b.BuildConnectivity()
r = ET.parse(sys.argv[2]).getroot()
sch = {}
for n in r.find("nets"):
    for nd in n.findall("node"):
        sch[(nd.get("ref"), nd.get("pin"))] = n.get("name").replace("{slash}", "/")
brd = {}
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNumber():
            brd[(fp.GetReference(), p.GetNumber())] = p.GetNetname().replace("{slash}", "/")
miss = [k for k in sch if k not in brd]
extra = [k for k in brd if k not in sch and brd[k]]
diff = [(k, brd[k], sch[k]) for k in sch if k in brd and brd[k] != sch[k] and not (sch[k].startswith("unconnected-") and brd[k].startswith("unconnected-"))]
print("schematic pins %d, board pads %d | missing on board %d %s | board pads with a net but no pin %d %s | net differences %d %s"
      % (len(sch), len(brd), len(miss), sorted(miss)[:10], len(extra), sorted(extra)[:10], len(diff), diff[:10]))
print("unconnected (pcbnew connectivity):", b.GetConnectivity().GetUnconnectedCount(True))
