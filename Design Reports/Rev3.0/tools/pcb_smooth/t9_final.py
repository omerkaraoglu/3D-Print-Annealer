"""Final pass, footprint-only edits (no copper):
- 3D models from Design Reports/Rev3.0/tools/models3d/models.json (each listed footprint's model list is replaced)
- DS1 = Rev3:TFT7_SAT070AT40D21_Mech, added on F at orientation 0 at its absolute position, then flipped left/right
  about its own position (B.Cu, orientation 180), attributes board_only / exclude_from_bom / exclude_from_pos_files
- the four old "H" holes renamed H1..H4 (left-top, left-bottom, bottom-middle, right-bottom); all nine holes board_only +
  exclude from BOM / position files
Usage: t9_final.py in.kicad_pcb out.kicad_pcb models.json fplibdir"""
import sys, json, pcbnew
from common import *
b = pcbnew.LoadBoard(sys.argv[1])
M = json.load(open(sys.argv[3], encoding='utf-8'))
KEEP = []


def model(d):
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = d['model']
    m.m_Offset = pcbnew.VECTOR3D(*map(float, d['offset']))
    m.m_Rotation = pcbnew.VECTOR3D(*map(float, d['rotate']))
    m.m_Scale = pcbnew.VECTOR3D(*map(float, d['scale']))
    m.m_Show = True
    return m


done = []
for ref, d in M.items():
    if ref in ('_note', 'mechanical'):
        continue
    fp = b.FindFootprintByReference(ref)
    assert fp is not None, ref
    ms = fp.Models()
    while len(ms):
        ms.pop()
    ms.push_back(model(d))
    done.append(ref)
print("models replaced:", len(done), done)
mech = M['mechanical']['DS1']
fp = pcbnew.FootprintLoad(sys.argv[4], mech['footprint'].split(':')[1])
fp.SetReference('DS1')
fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(mech['position_abs_mm'][0]), pcbnew.FromMM(mech['position_abs_mm'][1])))
fp.SetOrientationDegrees(0)
b.Add(fp); KEEP.append(fp)
fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
ms = fp.Models()
while len(ms):
    ms.pop()
ms.push_back(model(mech))
fp.SetBoardOnly(True); fp.SetExcludedFromBOM(True); fp.SetExcludedFromPosFiles(True)
bb = fp.GetBoundingBox(False, False) if hasattr(fp, 'GetBoundingBox') else None
print("DS1 layer %s orientation %.1f pos (%.2f, %.2f) abs, board_only %s bom-excl %s pos-excl %s pads %d" % (
    b.GetLayerName(fp.GetLayer()), fp.GetOrientationDegrees(), mm(fp.GetPosition().x), mm(fp.GetPosition().y),
    fp.IsBoardOnly(), fp.IsExcludedFromBOM(), fp.IsExcludedFromPosFiles(), len(fp.Pads())))
names = {(4.0, 4.0): 'H1', (4.0, 95.0): 'H2', (97.0, 95.5): 'H3', (160.0, 95.0): 'H4'}
for f in b.GetFootprints():
    if 'MountingHole_3.2mm_M3' not in str(f.GetFPID().GetUniStringLibItemName()):
        continue
    p = L(f.GetPosition()); k = (round(p[0], 2), round(p[1], 2))
    if k in names:
        f.SetReference(names[k])
    f.SetBoardOnly(True); f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
    print("hole %-3s local (%.1f, %.1f) abs (%.1f, %.1f) board_only %s" % (f.GetReference(), p[0], p[1], p[0] + 20, p[1] + 20, f.IsBoardOnly()))
pcbnew.SaveBoard(sys.argv[2], b)
print("saved", sys.argv[2])
