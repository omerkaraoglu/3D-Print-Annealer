"""L40 - Core Master RC1415U-101K radial drum choke (100 uH, 5 A).

Source: Core Master approval drawing for the RC1415U series (RC1415U-301K copy
on the Ozdisan CDN, quoted via web search: A 16.5 max, B 17.0 max, C 15.0+-3.0,
D 7.5 ref, E 0.8 ref) and spec HX8817022 quoted in the footprint (D16.5 x H17,
P7.5, 1.0 mm leads for the 5 A -101K).  A = diameter, B = height, C = lead
length (the leads are cut to 3.5 mm below the board here), D = pitch.
Shape: ferrite drum (two flanges) with the copper winding visible between them.
ESTIMATED: flange thickness (2 mm) and winding diameter.
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

D, H, P, LEAD = 16.5, 17.0, 7.5, 1.0
STANDOFF = 0.5


def build():
    m = Model("L_Radial_CoreMaster_RC1415U", "Rev3:L_Radial_CoreMaster_RC1415U",
              "Core Master RC1415U D16.5 x H17, P7.5")
    m.add("flange_bottom", cyl(0, 0, STANDOFF, STANDOFF + 2.0, D), "ferrite")
    m.add("flange_top", cyl(0, 0, H - 2.0, H, D), "ferrite")
    m.add("winding", cyl(0, 0, STANDOFF + 2.0, H - 2.0, D - 1.2), "copper")
    for num, sx in (("1", -1), ("2", 1)):
        m.pin(num, cyl(sx * P / 2, 0, -3.5, STANDOFF + 0.5, LEAD), "copper")
    return m


if __name__ == "__main__":
    run(build())
