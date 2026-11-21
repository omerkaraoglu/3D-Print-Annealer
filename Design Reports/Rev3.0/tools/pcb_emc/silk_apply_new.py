"""Write the designators chosen by silk_new.py into the footprints' Reference fields (F.SilkS, centred, not mirrored).
Usage: silk_apply_new.py in.kicad_pcb placement.json out.kicad_pcb"""
import sys, json, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); P = json.load(open(sys.argv[2]))
HIDE_VALUE = {"C9", "C134", "C135", "R4", "D6", "RV3"}      # values stay hidden on this board (only DS1's is shown)
for fp in b.GetFootprints():
    r = fp.GetReference()
    if r in HIDE_VALUE:
        fp.Value().SetVisible(False)
    if r not in P or P[r] is None:
        continue
    c = P[r]; h, w, t = c["size"]
    f = fp.Reference()
    f.SetLayer(pcbnew.F_SilkS); f.SetVisible(True); f.SetMirrored(False)
    f.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(w), pcbnew.FromMM(h))); f.SetTextThickness(pcbnew.FromMM(t))
    f.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); f.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    f.SetKeepUpright(False)
    f.SetTextAngleDegrees(c["ang"])
    f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(c["centre"][0]), pcbnew.FromMM(c["centre"][1])))
    print(r, c["style"], c["ang"], [round(v - 20, 3) for v in c["centre"]], "(local)")
pcbnew.SaveBoard(sys.argv[3], b)
