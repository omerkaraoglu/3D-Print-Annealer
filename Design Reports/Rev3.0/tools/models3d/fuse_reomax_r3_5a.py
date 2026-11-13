"""F1, F3 - two Reomax R3-5A fuse clips with a 5 x 20 mm cartridge fuse,
on KiCad's Fuseholder_Clip-5x20mm_Littelfuse_445-030 footprint.

KiCad 10 ships no 3D model for that footprint (the referenced
Fuseholder_Clip-5x20mm_Littelfuse_445-030_...step does not exist in the
library), so this model replaces it.
Source: Reomax drawing "REOMAX R3-5A" (Datasheets/REOMAX R3-5A ... .pdf, 2013-08-05):
  clip height 9.5 above the board, width across the fuse 6.5, length along the
  fuse 4.8, legs 0.4 x 1.2, 5.6 +-0.5 apart (outer), 3.5 +-0.5 below the board,
  material 0.4 brass, cradle for a 5.2 mm cap.
5 x 20 fuse: IEC 60127 cartridge, caps dia 5.2 x 6, glass dia 5.0, length 20.
Footprint: clip legs on (0,0)/(5.2,0) and (15.3,0)/(20.5,0); fuse centred at x 10.25.
ESTIMATED: fuse axis height 6.3 (read off the clip drawing), arms drawn straight.
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

CLIP_H, CLIP_W, CLIP_L, T = 9.5, 6.5, 4.8, 0.4
LEG_W, LEG_L, LEG_P = 1.2, 3.5, 5.2
AXIS_Z = 6.3


def clip(m, xc, num):
    m.add("clip_base", box(xc - CLIP_L / 2, xc + CLIP_L / 2, -CLIP_W / 2 + 0.6, CLIP_W / 2 - 0.6, 0, T), "tin")
    for sy in (-1, 1):
        y_in = sy * 2.6
        m.add("clip_arm", box(xc - CLIP_L / 2, xc + CLIP_L / 2, min(y_in, y_in + sy * T), max(y_in, y_in + sy * T),
                              T, CLIP_H), "tin")
        m.add("clip_foot", box(xc - CLIP_L / 2, xc + CLIP_L / 2, min(sy * (CLIP_W / 2 - 0.6), y_in),
                               max(sy * (CLIP_W / 2 - 0.6), y_in), 0, T), "tin")
    for sx in (-1, 1):
        xl = xc + sx * LEG_P / 2
        m.pin(num, box(xl - T / 2, xl + T / 2, -LEG_W / 2, LEG_W / 2, -LEG_L, T), "tin")


def build():
    m = Model("Fuse_Reomax_R3-5A_Clips_5x20mm_P20.50x5.20mm", 
              "Fuse:Fuseholder_Clip-5x20mm_Littelfuse_445-030_Inline_P20.50x5.20mm_D1.30mm_Horizontal",
              "2 x Reomax R3-5A clips + 5x20 mm fuse")
    clip(m, 2.6, "1")
    clip(m, 17.9, "2")
    xc = 10.25
    fz = lambda x0, x1, d: (cq.Workplane("YZ").workplane(offset=x0).center(0, AXIS_Z).circle(d / 2).extrude(x1 - x0))
    m.add("cap1", fz(xc - 10, xc - 4, 5.2), "steel")
    m.add("cap2", fz(xc + 4, xc + 10, 5.2), "steel")
    m.add("glass", fz(xc - 4, xc + 4, 5.0), "glass")
    m.add("element", fz(xc - 4, xc + 4, 0.4), "tin")
    return m


if __name__ == "__main__":
    run(build())
