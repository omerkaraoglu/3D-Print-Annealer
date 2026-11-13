"""Dump every footprint of the Rev3.0 board (side, position, rotation, 3D model, pads + nets) to JSON.

Run with KiCad's Python (read-only: it loads a temporary COPY of the board, never the live file):
  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" dump_board_fps.py [board.kicad_pcb] [out.json]
"""
import json, os, shutil, sys, tempfile
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.normpath(os.path.join(HERE, r"..\..\..\..\KiCad\3dFilamentDryer\3dFilamentDryer.kicad_pcb"))
src = sys.argv[1] if len(sys.argv) > 1 else BOARD
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out", "board_fps.json")
tmpd = tempfile.mkdtemp()
tmp = os.path.join(tmpd, "board_copy.kicad_pcb")
shutil.copyfile(src, tmp)
b = pcbnew.LoadBoard(tmp)
M = pcbnew.ToMM
bb = b.GetBoardEdgesBoundingBox()
fps = []
for fp in b.GetFootprints():
    pads = [{"num": p.GetNumber(), "x": M(p.GetPosition().x), "y": M(p.GetPosition().y),
             "tht": p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH, "npth": p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
             "drill": M(p.GetDrillSize().x), "net": p.GetNetname()} for p in fp.Pads()]
    fps.append({"ref": fp.GetReference(), "fpid": fp.GetFPIDAsString(), "side": "B" if fp.IsFlipped() else "F",
                "x": M(fp.GetPosition().x), "y": M(fp.GetPosition().y), "rot": fp.GetOrientationDegrees(),
                "models": [{"file": m.m_Filename, "off": [m.m_Offset.x, m.m_Offset.y, m.m_Offset.z],
                            "rot": [m.m_Rotation.x, m.m_Rotation.y, m.m_Rotation.z],
                            "scale": [m.m_Scale.x, m.m_Scale.y, m.m_Scale.z], "show": m.m_Show} for m in fp.Models()],
                "pads": pads})
os.makedirs(os.path.dirname(dst), exist_ok=True)
json.dump({"board": src, "edge_bbox": [M(bb.GetX()), M(bb.GetY()), M(bb.GetRight()), M(bb.GetBottom())],
           "thickness": M(b.GetDesignSettings().GetBoardThickness()), "fps": fps}, open(dst, "w"), indent=1)
shutil.rmtree(tmpd, ignore_errors=True)
print("wrote", dst, "(%d footprints)" % len(fps))
