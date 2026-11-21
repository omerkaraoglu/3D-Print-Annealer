"""D6 is a bidirectional TVS: remove the library footprint's polarity marks (the "K" texts on F.SilkS / F.Fab; the
cathode band lines are removed in s3_build.py) and give pad 1 the round shape of pad 2.
Usage: s3_d6mark.py in.kicad_pcb out.kicad_pcb"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); d6 = b.FindFootprintByReference("D6"); KEEP = []
for g in list(d6.GraphicalItems()):
    if g.GetClass() == "PCB_TEXT" and g.GetText() == "K":
        d6.Remove(g); KEEP.append(g); print("removed K text on", b.GetLayerName(g.GetLayer()))
p1 = [p for p in d6.Pads() if p.GetNumber() == "1"][0]; p2 = [p for p in d6.Pads() if p.GetNumber() == "2"][0]
p1.SetShape(pcbnew.PADSTACK.ALL_LAYERS, pcbnew.PAD_SHAPE_CIRCLE); p1.SetSize(pcbnew.PADSTACK.ALL_LAYERS, p2.GetSize(pcbnew.F_Cu))
print("pad 1 -> shape", p1.GetShape(pcbnew.F_Cu), "size", pcbnew.ToMM(p1.GetSize(pcbnew.F_Cu).x))
pcbnew.SaveBoard(sys.argv[2], b)
