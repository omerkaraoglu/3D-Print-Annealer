"""Round 3, task 3: the owner's 5 mm spacer between the PCB back and the panel is baked into the panel model by the 3D
toolchain.  If `tools/models3d/models.json` -> mechanical -> DS1 carries a non-zero (or changed) model offset /
rotation / scale, apply it to DS1's model on the board; otherwise leave DS1 untouched (and say so).
Usage: r3_ds1.py in.kicad_pcb out.kicad_pcb models.json"""
import sys, json, shutil, pcbnew
from common import *
M = json.load(open(sys.argv[3], encoding='utf-8'))['mechanical']['DS1']
b = pcbnew.LoadBoard(sys.argv[1])
fp = b.FindFootprintByReference('DS1')
ms = fp.Models()
assert len(ms) == 1
m = ms[0]
cur = dict(model=m.m_Filename, offset=[m.m_Offset.x, m.m_Offset.y, m.m_Offset.z], rotate=[m.m_Rotation.x, m.m_Rotation.y, m.m_Rotation.z],
           scale=[m.m_Scale.x, m.m_Scale.y, m.m_Scale.z])
want = dict(model=M['model'], offset=[float(v) for v in M['offset']], rotate=[float(v) for v in M['rotate']], scale=[float(v) for v in M['scale']])
same = cur['model'] == want['model'] and all(abs(a - c) < 1e-6 for k in ('offset', 'rotate', 'scale') for a, c in zip(cur[k], want[k]))
print("DS1 model on the board:", cur)
print("models.json mechanical:", want)
if same:
    shutil.copy(sys.argv[1], sys.argv[2])
    print("unchanged: DS1 left as it is")
else:
    m.m_Filename = want['model']
    m.m_Offset = pcbnew.VECTOR3D(*want['offset']); m.m_Rotation = pcbnew.VECTOR3D(*want['rotate']); m.m_Scale = pcbnew.VECTOR3D(*want['scale'])
    pcbnew.SaveBoard(sys.argv[2], b)
    print("DS1 model updated")
