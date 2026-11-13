"""HS1 - Fischer Elektronik SK 409 63,5 STC extruded PCB heatsink (heatsink only).

Source: Fischer data sheet "SK 409 63,5 STC" (fischerelektronik.de, saved as
Datasheets/Heatsink - Fischerelektronik - SK 409 63,5.pdf):
  profile width 45, height 12.7, plate thickness 3, length 63.5 (standing),
  26.2 clear width between the two fin groups, TO-220 hole dia 2.8 at 18.3
  above the board (P), solder pins (STC) dia 2.3 max, 4.5 max below the
  bottom face, pin spacing 35.5; black anodised.
Footprint frame: plate centred at the origin in the XZ plane (y -1.5..1.5),
TO-220 side +y (footprint) = -Y (model); fin groups x +-(13.1..22.5),
y +-6.35.
ESTIMATED: the exact fin fan geometry (4 + 4 fins per group, 1.2 mm thick,
radiating from the pin hub) and no clip slots / bottom notch (the drawing
shows them only partially). The envelope 45 x 12.7 x 63.5 is exact.
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

W, DEPTH, PLATE, L = 45.0, 12.7, 3.0, 63.5
GAP = 26.2
PIN_P, PIN_D, PIN_L = 35.5, 2.3, 4.5
HOLE_D, HOLE_Z = 2.8, 18.3
FIN_T = 1.2


def fin_group(sx):
    """2D fin fan for one side, returned as an extruded solid (z 0..L)."""
    hx, hy = sx * PIN_P / 2, 0.0
    sk = cq.Workplane("XY")
    solids = [box(sx * GAP / 2 if sx > 0 else -W / 2, W / 2 if sx > 0 else -GAP / 2, -PLATE / 2, PLATE / 2, 0, L),
              cyl(hx, hy, 0, L, 4.6)]
    ends_x = [13.6, 16.3, 19.0, 21.7]
    for sy in (-1, 1):
        for ex in ends_x:
            ex_s, ey = sx * ex, sy * (DEPTH / 2 - 0.4)
            dx, dy = ex_s - hx, ey - hy
            ln = math.hypot(dx, dy)
            ang = math.degrees(math.atan2(dy, dx))
            f = (cq.Workplane("XY").box(ln, FIN_T, L).translate((ln / 2, 0, L / 2))
                 .rotate((0, 0, 0), (0, 0, 1), ang).translate((hx, hy, 0)))
            solids.append(f)
        # outer flat fin closing the group
        solids.append(box(sx * (W / 2 - FIN_T) if sx > 0 else -W / 2, W / 2 if sx > 0 else -W / 2 + FIN_T,
                          sy * 1.0 if sy > 0 else -4.6, sy * 4.6 if sy > 0 else -1.0, 0, L))
    g = solids[0]
    for s in solids[1:]:
        g = g.union(s)
    lim = box(sx * GAP / 2 if sx > 0 else -W / 2, W / 2 if sx > 0 else -GAP / 2, -DEPTH / 2, DEPTH / 2, 0, L)
    return g.intersect(lim)


def build():
    m = Model("Heatsink_Fischer_SK409_63.5_STC", "Rev3:Heatsink_Fischer_SK409_63.5_STC",
              "Fischer SK 409 63,5 STC 45 x 12.7 x 63.5 mm, pins dia 2.3 at 35.5")
    plate = box(-GAP / 2 - 0.5, GAP / 2 + 0.5, -PLATE / 2, PLATE / 2, 0, L)
    hole = (cq.Workplane("XZ").center(0, HOLE_Z).circle(HOLE_D / 2).extrude(5, both=True))
    body = plate.union(fin_group(1)).union(fin_group(-1)).cut(hole)
    m.add("profile", body, "alu_black")
    for num, sx in (("1", -1), ("2", 1)):
        m.pin(num, cyl(sx * PIN_P / 2, 0, -PIN_L, 0.0, PIN_D), "tin")
    return m


if __name__ == "__main__":
    run(build(), render_views=("iso", "top", "iso2"))
