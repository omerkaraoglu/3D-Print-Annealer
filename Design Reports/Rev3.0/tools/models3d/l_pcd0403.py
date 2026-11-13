"""L11, L12 - Viking PCD0403 unshielded SMD drum inductor.

Source: Viking PCD Series data sheet REV.C2 (08-Jan-2018), dimension table:
  PCD0403  A 4.5+-0.3 (across the rounded corners)  B 4.0+-0.3  C 3.2+-0.3
  pad layout H 4.50, I 1.75, J 1.5  (pads 1.75 x 4.5, gap 1.5 -> pad centres +-1.625)
Shape: two ferrite flanges (rounded square B x B, corner radius chosen so that
the diagonal equals A), drum + copper winding between, two silver terminals
under the bottom flange. Height = C (3.2 nominal).
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

A, B, C = 4.5, 4.0, 3.2
PAD_X = (1.5 + 1.75) / 2          # 1.625 = J/2 + I/2
T_TERM = 0.15
FLANGE = 0.55


def rsquare(s, r, z0, z1):
    return (cq.Workplane("XY").workplane(offset=z0).rect(s, s).extrude(z1 - z0)
            .edges("|Z").fillet(r))


def build():
    m = Model("L_Viking_PCD0403", "Rev3:L_Viking_PCD0403",
              "Viking PCD0403 4.5x4.0x3.2 mm (A x B x C), REV.C2")
    r = (B * math.sqrt(2) - A) / (2 * (math.sqrt(2) - 1))   # diagonal of rounded square = A
    z0 = T_TERM
    m.add("flange_bottom", rsquare(B, r, z0, z0 + FLANGE), "ferrite")
    m.add("flange_top", rsquare(B, r, C - FLANGE, C), "ferrite")
    m.add("winding", cyl(0, 0, z0 + FLANGE, C - FLANGE, B - 0.5), "copper")
    for num, sx in (("1", -1), ("2", 1)):
        m.pin(num, box(sx * PAD_X - 0.35, sx * PAD_X + 0.35, -1.3, 1.3, 0, T_TERM), "tin")
    return m


if __name__ == "__main__":
    run(build())
