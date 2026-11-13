"""Dump pad positions of every footprint we model to pads.json.

Run with KiCad's Python (read-only):
  "C:\Program Files\KiCad\10.0\bin\python.exe" dump_pads.py
Coordinates are KiCad footprint coordinates (mm, y down).
"""
import json, os, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
REV3 = os.path.normpath(os.path.join(HERE, r"..\..\..\..\KiCad\ComponentsLibrary\User Created\Rev3\Rev3.pretty"))
KILIB = r"C:\Program Files\KiCad\10.0\share\kicad\footprints"

FOOTPRINTS = {
    "Rev3:L_Radial_CoreMaster_RC1415U": REV3,
    "Rev3:L_CoreMaster_SRI0605B": REV3,
    "Rev3:L_Viking_PCD0403": REV3,
    "Rev3:LFU09V-103": REV3,
    "Rev3:Heatsink_Fischer_SK409_63.5_STC": REV3,
    "Rev3:Connfly_DS1020-09-40VBT1B_1x40_P0.5mm_Horizontal_TopSide": REV3,
    "Rev3:Connfly_DS1020-09-40VBT1A_1x40_P0.5mm_Horizontal": REV3,
    "Rev3:Connfly_DS1020-09-06VBT1A_1x06_P0.5mm_Horizontal": REV3,
    "Rev3:KLS_L-KLS1-242D-1.2-06-T-U-R_1x06_P0.5mm_Horizontal_TopSide": REV3,
    "Rev3:TerminalBlock_DEGSON_DG127H-5.08-02P": REV3,
    "Rev3:C_Rect_L32.0mm_W9.0mm_P27.50mm_X2": REV3,
    "Fuse:Fuseholder_Clip-5x20mm_Littelfuse_445-030_Inline_P20.50x5.20mm_D1.30mm_Horizontal": os.path.join(KILIB, "Fuse.pretty"),
    "Connector_Wire:SolderWire-1.5sqmm_1x02_P7.8mm_D1.7mm_OD3.9mm": os.path.join(KILIB, "Connector_Wire.pretty"),
    "Connector_Wire:SolderWire-0.75sqmm_1x02_P7mm_D1.25mm_OD3.5mm": os.path.join(KILIB, "Connector_Wire.pretty"),
}

M = pcbnew.ToMM
out = {}
for fpid, lib in FOOTPRINTS.items():
    fp = pcbnew.FootprintLoad(lib, fpid.split(":", 1)[1])
    pads = []
    for p in fp.Pads():
        s = p.GetSize(pcbnew.F_Cu)
        pads.append({"num": p.GetNumber(), "x": round(M(p.GetPosition().x), 4), "y": round(M(p.GetPosition().y), 4),
                     "w": round(M(s.x), 4), "h": round(M(s.y), 4), "drill": round(M(p.GetDrillSize().x), 4),
                     "smd": p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD})
    out[fpid] = {"pads": pads, "models": [m.m_Filename for m in fp.Models()]}
json.dump(out, open(os.path.join(HERE, "pads.json"), "w"), indent=1)
print("wrote", len(out), "footprints")
