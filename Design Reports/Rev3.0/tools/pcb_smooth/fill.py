"""Fill all zones WITH the project rules (pcbnew only loads the .kicad_pro/.kicad_dru that sit next to the board under the
same name, so the board is copied into a scratch run directory together with the rules first) and save.
Usage: fill.py in.kicad_pcb out.kicad_pcb rulesdir"""
import sys, os, shutil, pcbnew
src, dst, rules = sys.argv[1:4]
d = os.path.join(os.path.dirname(os.path.abspath(dst)), "fillrun")
os.makedirs(d, exist_ok=True)
for ext in (".kicad_pro", ".kicad_dru"):
    shutil.copy(os.path.join(rules, "3dFilamentDryer" + ext), os.path.join(d, "3dFilamentDryer" + ext))
tmp = os.path.join(d, "3dFilamentDryer.kicad_pcb")
shutil.copy(src, tmp)
b = pcbnew.LoadBoard(tmp)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
filled = sum(1 for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() and z.IsFilled())
pcbnew.SaveBoard(dst, b)
print("filled", filled, "copper/teardrop zones ->", dst)
